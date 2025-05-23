# Helper functions for server.py
import anthropic
import os
import json
import requests
import time
import uuid
import base64
import traceback

# Import Google Generative AI package
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI package not available. Some features may be limited.")

def create_anthropic_client(api_key):
    """Create an Anthropic client with the given API key."""
    print(f"Creating Anthropic client with API key: {api_key[:8]}...")
    
    # Check if API key is valid format
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    # Try to create the client with the standard approach first
    try:
        # Create client with only the essential parameter
        client = anthropic.Anthropic(api_key=api_key)
        
        # Test a simple call to verify the client works
        try:
            # Try a simple call that doesn't cost tokens
            client.count_tokens("Test")
            return client
        except Exception as e:
            print(f"Warning: Token counting failed but client might still work: {str(e)}")
            return client
            
    except Exception as e:
        print(f"Standard client creation failed: {str(e)}")
        
        # Try the fallback client approach
        try:
            print("Using custom Anthropic client implementation")
            return VercelCompatibleClient(api_key)
        except Exception as e2:
            print(f"Custom client also failed: {str(e2)}")
            raise Exception(f"Failed to create Anthropic client: {str(e)}")

def create_gemini_client(api_key):
    """Create a Google Gemini client with the given API key."""
    if not GEMINI_AVAILABLE:
        raise ImportError("Google Generative AI package is not installed. Please install it with 'pip install google-generativeai'.")
    
    print(f"Creating Google Gemini client with API key: {api_key[:8]}...")
    
    # Check if API key is valid format
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    try:
        # Configure the Gemini client
        genai.configure(api_key=api_key)
        
        # Create a simple wrapper class that provides the methods expected by the server
        class GeminiClient:
            def __init__(self):
                pass
                
            def get_model(self, model_name):
                """Create and return a GenerativeModel instance for the specified model."""
                try:
                    return genai.GenerativeModel(model_name)
                except Exception as e:
                    print(f"Error creating model {model_name}: {str(e)}")
                    raise
        
        # Create and return the client wrapper
        return GeminiClient()
            
    except Exception as e:
        print(f"Gemini client creation failed: {str(e)}")
        raise Exception(f"Failed to create Google Gemini client: {str(e)}")

class GeminiStreamingResponse:
    """
    Custom class to handle streaming responses from Google Gemini API.
    Provides compatibility with the server-sent events format used by the frontend.
    """
    def __init__(self, stream_response, session_id):
        self.stream_response = stream_response
        self.session_id = session_id
        self.text_chunks = []
        self.message_id = str(uuid.uuid4())
        self.chunk_count = 0
        self.accumulated_text = ""
        self.start_time = time.time()
        self.last_progress_time = time.time()
        self.timeout = 300  # Maximum time to wait for first chunk (seconds)
        self.progress_timeout = 100  # Maximum time to wait between chunks (seconds)
        self.response_complete = False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # If an exception occurred, we need to handle it
        if exc_type is not None:
            print(f"Exception in GeminiStreamingResponse: {exc_type} - {exc_val}")
            # If we have accumulated some text, generate a partial response
            if self.accumulated_text:
                print(f"Returning partial accumulated content ({len(self.accumulated_text)} chars)")
                return False  # Don't suppress the exception
        
        # If response didn't complete but we have content, mark as complete
        if not self.response_complete and self.accumulated_text:
            self.response_complete = True
            message = "Stream completed with partial content"
            print(message)
        
        return False  # Don't suppress exceptions
    
    def __iter__(self):
        return self
    
    def __next__(self):
        """
        Process the next chunk from the Gemini stream and yield formatted SSE events.
        Handles timeouts and converts Gemini response format to the expected SSE format.
        """
        # Check for initial timeout (no chunks received yet)
        if not self.text_chunks and time.time() - self.start_time > self.timeout:
            print(f"Timeout waiting for first chunk ({self.timeout}s)")
            # Yield a timeout error event
            event_data = {
                "type": "error",
                "error": f"Timeout waiting for response from Gemini API after {self.timeout} seconds.",
                "session_id": self.session_id
            }
            return format_stream_event("error", event_data)
        
        # Check for progress timeout (no new chunks recently)
        if self.text_chunks and time.time() - self.last_progress_time > self.progress_timeout:
            print(f"Timeout waiting for next chunk ({self.progress_timeout}s)")
            # If we have accumulated some content, mark the response as complete to return what we have
            if self.accumulated_text:
                self.response_complete = True
                event_data = {
                    "type": "status",
                    "message": "Timeout waiting for additional content from Gemini API. Returning partial response.",
                    "session_id": self.session_id
                }
                return format_stream_event("status", event_data)
            else:
                # No content received at all, return an error
                event_data = {
                    "type": "error",
                    "error": f"No content received from Gemini API after {self.progress_timeout} seconds.",
                    "session_id": self.session_id
                }
                return format_stream_event("error", event_data)
        
        try:
            # Get next chunk from stream
            chunk = next(self.stream_response)
            self.last_progress_time = time.time()
            self.chunk_count += 1
            
            # Extract text content from the chunk
            chunk_text = ""
            if hasattr(chunk, 'text'):
                chunk_text = chunk.text
            elif hasattr(chunk, 'parts') and chunk.parts:
                for part in chunk.parts:
                    if hasattr(part, 'text') and part.text:
                        chunk_text += part.text
            
            # Skip empty chunks
            if not chunk_text:
                if self.chunk_count % 10 == 0:
                    # Periodically send keepalive events
                    event_data = {
                        "type": "keepalive",
                        "timestamp": time.time(),
                        "session_id": self.session_id,
                        "chunk_count": self.chunk_count
                    }
                    return format_stream_event("keepalive", event_data)
                return self.__next__()  # Skip to next chunk
            
            # Store the chunk
            self.text_chunks.append(chunk_text)
            self.accumulated_text += chunk_text
            
            # Create content delta event
            event_data = {
                "type": "content_block_delta",
                "chunk_id": f"{self.message_id}_{self.chunk_count}",
                "delta": {
                    "text": chunk_text
                },
                "session_id": self.session_id,
                "chunk_count": self.chunk_count
            }
            
            # Every N chunks, send a keepalive event
            if self.chunk_count % 5 == 0:
                print(f"Processed {self.chunk_count} chunks from Gemini")
            
            return format_stream_event("content", event_data)
            
        except StopIteration:
            # Check if we received any content
            if not self.accumulated_text:
                print("No content received from Gemini API before StopIteration")
                error_data = {
                    "type": "error",
                    "error": "No content received from Gemini API. Please try again or check your API key.",
                    "session_id": self.session_id
                }
                return format_stream_event("error", error_data)
            
            # Stream is complete, send completion event
            print(f"Gemini stream complete, received {self.chunk_count} chunks")
            self.response_complete = True
            
            # Calculate token usage (approximate)
            input_prompt_length = 1000  # Placeholder
            output_length = len(self.accumulated_text)
            
            # Estimate token count (very rough estimate)
            input_tokens = input_prompt_length // 4
            output_tokens = output_length // 4
            
            # Calculate cost based on current Gemini 2.0 Flash pricing
            # $0.10 per million input tokens, $0.40 per million output tokens
            input_cost = (input_tokens / 1000000) * 0.10
            output_cost = (output_tokens / 1000000) * 0.40
            total_cost = input_cost + output_cost
            
            # Create completion event
            complete_data = {
                "type": "message_complete",
                "message_id": self.message_id,
                "chunk_id": f"{self.message_id}_{self.chunk_count}",
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "total_cost": total_cost
                },
                "html": self.accumulated_text,
                "session_id": self.session_id,
                "final_chunk_count": self.chunk_count
            }
            
            return format_stream_event("content", complete_data)
            
        except Exception as e:
            # Log the error
            error_message = str(e)
            print(f"Error processing Gemini stream chunk: {error_message}")
            
            # If we have any accumulated content, we'll mark as complete to return what we have
            if self.accumulated_text:
                self.response_complete = True
                print(f"Returning partial accumulated content ({len(self.accumulated_text)} chars)")
                
                # Send completion with partial content
                complete_data = {
                    "type": "message_complete",
                    "message_id": self.message_id,
                    "chunk_id": f"{self.message_id}_{self.chunk_count}",
                    "usage": {
                        "input_tokens": 1000,  # Placeholder estimate
                        "output_tokens": len(self.accumulated_text) // 4,
                        "total_tokens": 1000 + (len(self.accumulated_text) // 4)
                    },
                    "html": self.accumulated_text,
                    "session_id": self.session_id,
                    "final_chunk_count": self.chunk_count,
                    "partial": True,
                    "error": error_message
                }
                
                return format_stream_event("content", complete_data)
            else:
                # No accumulated content, return error
                error_data = {
                    "type": "error",
                    "error": f"Error in Gemini streaming: {error_message}",
                    "session_id": self.session_id
                }
                return format_stream_event("error", error_data)

# Special client class for Vercel that doesn't use the standard Anthropic library
class VercelCompatibleClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Add beta and messages namespaces for compatibility
        self.beta = self._BetaNamespace(self)
        self.messages = self._MessagesNamespace(self)
    
    def post(self, url, json=None, headers=None, timeout=None):
        """Send a POST request to the specified URL with the given JSON data."""
        _headers = dict(self.headers)
        if headers:
            _headers.update(headers)
        
        response = requests.post(
            url,
            json=json,
            headers=_headers,
            timeout=timeout or 300
        )
        return response
    
    def models(self):
        # Lightweight method to check if the API key is valid
        class ModelList:
            def __init__(self, client):
                self.client = client
                
            def list(self):
                response = requests.get(
                    f"{self.client.base_url}/models",
                    headers=self.client.headers
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise Exception(f"Authentication failed: {response.json().get('error', {}).get('message', 'Invalid API key')}")
                else:
                    raise Exception(f"Error {response.status_code}: {response.text}")
        
        return ModelList(self)
    
    def count_tokens(self, text):
        # Simple approximation (1 token ≈ 4 characters)
        return len(text) // 4
    
    # Beta namespace for streaming
    class _BetaNamespace:
        def __init__(self, client):
            self.client = client
            self.messages = self._MessagesStreamingNamespace(client)
    
        # Streaming messages namespace
        class _MessagesStreamingNamespace:
            def __init__(self, client):
                self.client = client
            
            def stream(self, model, max_tokens, temperature, system, messages, thinking=None, betas=None, beta=None):
                """
                Stream the response from the Anthropic API directly with improved timeout handling
                for Vercel environment. Uses a stateful approach that supports reconnection.
                """
                # Check if we're on Vercel - if so, we need to handle timeouts differently
                is_vercel = os.environ.get('VERCEL', False)
                
                # Generate a unique ID for this streaming session
                session_id = str(int(time.time())) + "-" + str(hash(str(messages)))[1:8]
                
                # Convert messages to API format
                formatted_messages = []
                for msg in messages:
                    formatted_message = {"role": msg["role"]}
                    
                    # Handle different content formats
                    if isinstance(msg["content"], list):
                        formatted_content = []
                        for content_item in msg["content"]:
                            if isinstance(content_item, dict) and "text" in content_item:
                                formatted_content.append({
                                    "type": "text", 
                                    "text": content_item["text"]
                                })
                            elif isinstance(content_item, dict) and "type" in content_item and "text" in content_item:
                                formatted_content.append(content_item)
                        formatted_message["content"] = formatted_content
                    else:
                        formatted_message["content"] = msg["content"]
                    
                    formatted_messages.append(formatted_message)
                
                # Prepare the payload
                payload = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "messages": formatted_messages,
                    "stream": True
                }
                
                # Add thinking parameter if provided
                if thinking:
                    # Handle both new and old thinking parameter formats
                    if isinstance(thinking, dict) and "type" in thinking and thinking["type"] == "enabled":
                        # New format with 'type' and 'budget_tokens'
                        payload["thinking"] = thinking
                    elif isinstance(thinking, dict) and "enabled" in thinking:
                        # Old format with just 'enabled'
                        payload["thinking"] = {
                            "type": "enabled",
                            "budget_tokens": thinking.get("budget_tokens", 32000)
                        }
                    else:
                        # Default to enabled with a budget
                        payload["thinking"] = {
                            "type": "enabled",
                            "budget_tokens": 32000
                        }
                
                # Add beta features if specified - Fixed to use the correct format
                # The Anthropic API expects beta features in the 'anthropic-beta' header
                headers = dict(self.client.headers)
                
                # Handle both beta and betas parameters
                if beta:
                    headers["anthropic-beta"] = beta
                elif betas and isinstance(betas, list) and len(betas) > 0:
                    headers["anthropic-beta"] = ",".join(betas)
                
                # For Vercel, reduce the expected response timeout and add retry mechanism
                if is_vercel:
                    # Add a shorter timeout for Vercel environment  
                    timeout = 120  # 2 minutes for Vercel environment
                else:
                    # For local environment, use a longer timeout
                    timeout = 300  # 5 minutes for local environment
                
                # Implement retry logic with exponential backoff
                max_retries = 5
                retry_count = 0
                base_delay = 2  # Start with a 2-second delay
                
                while retry_count < max_retries:
                    try:
                        # Make the API request to stream response
                        stream_response = requests.post(
                            f"{self.client.base_url}/messages",
                            headers=headers,
                            json=payload,
                            stream=True,
                            timeout=timeout
                        )
                        
                        if stream_response.status_code not in [200, 201]:
                            error_msg = None
                            # Handle error responses with retry logic
                            if stream_response.status_code == 529:  # Overloaded
                                retry_count += 1
                                retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                                print(f"API overloaded (529), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                                time.sleep(retry_delay)
                                continue
                            elif stream_response.status_code == 500:  # Internal server error
                                retry_count += 1
                                retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                                print(f"API internal error (500), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                                time.sleep(retry_delay)
                                continue
                            elif stream_response.status_code == 408:  # Timeout
                                retry_count += 1
                                retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                                print(f"API timeout (408), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                                time.sleep(retry_delay)
                                continue
                            
                            # If not a retriable error or we couldn't extract an error message
                            try:
                                error_text = next(stream_response.iter_lines()).decode('utf-8')
                                if error_text.startswith('data: '):
                                    error_json = json.loads(error_text[6:])
                                    error_msg = error_json.get('error', {}).get('message', error_text)
                                else:
                                    error_msg = error_text
                            except Exception:
                                error_msg = f"HTTP Error {stream_response.status_code}"
                            
                            raise Exception(f"API request failed: {error_msg}")
                        
                        # Return a streaming response wrapper that mimics the Anthropic client
                        # Add the session_id and is_vercel flags to help with timeout handling
                        return VercelStreamingResponse(stream_response, self.client, 
                                                     session_id=session_id,
                                                     is_vercel=is_vercel)
                        
                    except requests.exceptions.Timeout:
                        # If timeout occurs on Vercel, provide information for client reconnection
                        if is_vercel:
                            retry_count += 1
                            if retry_count >= max_retries:
                                raise Exception(f"Vercel timeout after {max_retries} retries - client should continue with session: {session_id}")
                            retry_delay = base_delay * (2 ** retry_count)
                            print(f"Vercel timeout, retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                        else:
                            retry_count += 1
                            if retry_count >= max_retries:
                                raise Exception(f"Request timed out after {max_retries} retries")
                            retry_delay = base_delay * (2 ** retry_count)
                            print(f"Request timed out, retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                            
                    except Exception as e:
                        # For network/connection errors, retry
                        if "connection" in str(e).lower() or "timeout" in str(e).lower():
                            retry_count += 1
                            if retry_count >= max_retries:
                                raise Exception(f"Connection error after {max_retries} retries: {str(e)}")
                            retry_delay = base_delay * (2 ** retry_count)
                            print(f"Connection error, retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise Exception(f"API request failed: {str(e)}")
                
                # If we've exhausted all retries
                raise Exception(f"API request failed after {max_retries} retries")
    
    # Regular messages namespace
    class _MessagesNamespace:
        def __init__(self, client):
            self.client = client
        
        def stream(self, model, max_tokens, temperature, system, messages, thinking=None, betas=None, beta=None):
            """
            Stream method that delegates to the beta streaming functionality.
            """
            return self.client.beta.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                thinking=thinking,
                betas=betas,
                beta=beta
            )
        
        def create(self, model, max_tokens, temperature, system, messages, thinking=None, betas=None, beta=None):
            """
            Create a message with the Anthropic API directly with retry logic for 529 overloaded errors.
            Implements exponential backoff for retries.
            """
            # Convert messages to API format
            formatted_messages = []
            for msg in messages:
                formatted_message = {"role": msg["role"]}
                
                # Handle different content formats
                if isinstance(msg["content"], list):
                    formatted_content = []
                    for content_item in msg["content"]:
                        if isinstance(content_item, dict) and "text" in content_item:
                            formatted_content.append({
                                "type": "text", 
                                "text": content_item["text"]
                            })
                        elif isinstance(content_item, dict) and "type" in content_item and "text" in content_item:
                            formatted_content.append(content_item)
                    formatted_message["content"] = formatted_content
                else:
                    formatted_message["content"] = msg["content"]
                
                formatted_messages.append(formatted_message)
            
            # Prepare the payload
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": formatted_messages
            }
            
            # Add thinking parameter if provided
            if thinking:
                # Handle both new and old thinking parameter formats
                if isinstance(thinking, dict) and "type" in thinking and thinking["type"] == "enabled":
                    # New format with 'type' and 'budget_tokens'
                    payload["thinking"] = thinking
                elif isinstance(thinking, dict) and "enabled" in thinking:
                    # Old format with just 'enabled'
                    payload["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": thinking.get("budget_tokens", 32000)
                    }
                else:
                    # Default to enabled with a budget
                    payload["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": 32000
                    }
            
            # Add beta features if specified
            headers = dict(self.client.headers)
            
            # Handle both beta and betas parameters
            if beta:
                headers["anthropic-beta"] = beta
            elif betas and isinstance(betas, list) and len(betas) > 0:
                headers["anthropic-beta"] = ",".join(betas)
            
            # Implement retry logic with exponential backoff
            max_retries = 5
            retry_count = 0
            base_delay = 2  # Start with a 2-second delay
            
            while retry_count < max_retries:
                try:
                    # Make the API request with a longer timeout for large requests
                    response = requests.post(
                        f"{self.client.base_url}/messages",
                        headers=headers,
                        json=payload,
                        timeout=900  # 15 minutes timeout for large requests
                    )
                    
                    # Check if we received a successful response
                    if response.status_code == 200:
                        # Parse the result
                        result = response.json()
                        
                        # Return a response wrapper that mimics the Anthropic client
                        return VercelMessageResponse(result)
                        
                    # Handle specific error codes with retries
                    elif response.status_code == 529:  # Overloaded
                        retry_count += 1
                        retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                        print(f"API overloaded (529), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                        
                    elif response.status_code == 500:  # Internal server error
                        retry_count += 1
                        retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                        print(f"API internal error (500), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                        
                    elif response.status_code == 408:  # Timeout
                        retry_count += 1
                        retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                        print(f"API timeout (408), retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    
                    else:
                        # Try to get detailed error message
                        try:
                            error_json = response.json()
                            error_msg = error_json.get('error', {}).get('message', f"HTTP {response.status_code}")
                        except Exception:
                            error_msg = f"HTTP Error {response.status_code}: {response.text[:100]}"
                        
                        raise Exception(f"API request failed: {error_msg}")
                        
                except requests.exceptions.Timeout:
                    retry_count += 1
                    retry_delay = base_delay * (2 ** retry_count)
                    print(f"Request timed out, retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                    
                except Exception as e:
                    # For other exceptions, retry a few times
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        retry_count += 1
                        retry_delay = base_delay * (2 ** retry_count)
                        print(f"Connection error, retrying in {retry_delay} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"API request failed: {str(e)}")
            
            # If we've exhausted all retries
            raise Exception(f"API request failed after {max_retries} retries")

# Wrapper for the streaming response
class VercelStreamingResponse:
    def __init__(self, stream_response, client, session_id=None, is_vercel=False):
        self.stream_response = stream_response
        self.client = client
        self.is_vercel = is_vercel
        self.session_id = session_id or str(uuid.uuid4())
        self.chunk_count = 0
        self.buffer = []
        self.buffer_limit = 10  # Maximum number of chunks to buffer
        self.last_error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __iter__(self):
        """
        Parse the Server-Sent Events (SSE) stream from Anthropic API and yield properly formatted chunks.
        """
        try:
            # Track chunk count for reconnection support
            self.chunk_count = 0
            accumulated_text = ""
            
            print(f"Starting to parse SSE stream for session {self.session_id}")
            
            # Parse the SSE stream line by line
            for line in self.stream_response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                    
                try:
                    # Parse SSE format: "data: {json}" or "event: event_type"
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str.strip() == '[DONE]':
                            # End of stream marker
                            break
                            
                        try:
                            # Parse JSON data
                            chunk_data = json.loads(data_str)
                            self.chunk_count += 1
                            
                            # Handle different types of events from Anthropic
                            event_type = chunk_data.get('type')
                            
                            if event_type == 'content_block_delta':
                                # This is actual content
                                delta = chunk_data.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    text = delta.get('text', '')
                                    accumulated_text += text
                                    
                                    # Create a delta chunk object similar to the real Anthropic client
                                    delta_obj = self._MessageDeltaChunk(self._DeltaObject(text))
                                    delta_obj.chunk_id = f"{self.session_id}_{self.chunk_count}"
                                    delta_obj.session_id = self.session_id
                                    delta_obj.chunk_count = self.chunk_count
                                    delta_obj.type = 'content_block_delta'
                                    
                                    yield delta_obj
                                    
                            elif event_type == 'content_block_start':
                                # Beginning of content block
                                print(f"Content block started for session {self.session_id}")
                                
                            elif event_type == 'content_block_stop':
                                # End of content block
                                print(f"Content block stopped for session {self.session_id}")
                                
                            elif event_type == 'message_start':
                                # Beginning of message
                                print(f"Message started for session {self.session_id}")
                                
                            elif event_type == 'message_delta':
                                # Message metadata updates
                                delta = chunk_data.get('delta', {})
                                if 'stop_reason' in delta:
                                    print(f"Message stopping: {delta['stop_reason']}")
                                    
                            elif event_type == 'message_stop':
                                # End of message - prepare completion
                                print(f"Message stopped for session {self.session_id}")
                                usage = chunk_data.get('usage', {})
                                
                                # Create completion event
                                completion = {
                                    "type": "message_complete",
                                    "id": self.session_id,
                                    "chunk_id": f"{self.session_id}_{self.chunk_count}",
                                    "session_id": self.session_id,
                                    "final_chunk_count": self.chunk_count,
                                    "usage": usage,
                                    "html": accumulated_text
                                }
                                
                                completion_obj = type('CompletionObject', (), completion)
                                yield completion_obj
                                break
                                
                            elif event_type == 'error':
                                # Handle errors
                                error_msg = chunk_data.get('error', {}).get('message', 'Unknown error')
                                print(f"Stream error for session {self.session_id}: {error_msg}")
                                error_obj = self._ErrorChunk(error_msg)
                                error_obj.session_id = self.session_id
                                yield error_obj
                                break
                                
                            # Send keepalive every 20 chunks to prevent timeout
                            if self.chunk_count % 20 == 0:
                                yield self._create_keepalive()
                                
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON in SSE data: {data_str[:100]}... Error: {str(e)}")
                            continue
                            
                    elif line.startswith('event: '):
                        # Event type line - just log it
                        event_type = line[7:]  # Remove "event: " prefix
                        print(f"SSE event type: {event_type}")
                        
                except Exception as e:
                    print(f"Error processing SSE line: {str(e)}")
                    continue
            
            # If we reach here without a proper completion, create one
            if accumulated_text:
                print(f"Stream completed naturally for session {self.session_id}")
                completion = {
                    "type": "message_complete",
                    "id": self.session_id,
                    "chunk_id": f"{self.session_id}_{self.chunk_count}",
                    "session_id": self.session_id,
                    "final_chunk_count": self.chunk_count,
                    "html": accumulated_text
                }
                
                completion_obj = type('CompletionObject', (), completion)
                yield completion_obj
            
        except Exception as e:
            # If there's a terminal error, send an error message
            print(f"Fatal stream error for session {self.session_id}: {str(e)}")
            error_obj = self._ErrorChunk(str(e))
            error_obj.session_id = self.session_id
            yield error_obj

    def _add_to_buffer(self, chunk):
        """Add a chunk to the reconnection buffer, maintaining max buffer size"""
        self.buffer.append(chunk)
        if len(self.buffer) > self.buffer_limit:
            self.buffer.pop(0)  # Remove oldest chunk
    
    def _create_keepalive(self):
        """Create a keepalive message to prevent timeout"""
        keepalive = {
            "type": "keepalive",
            "timestamp": time.time(),
            "session_id": self.session_id,
            "chunk_count": self.chunk_count
        }
        return type('KeepaliveObject', (), keepalive)

    # Helper classes to mimic Anthropic client objects
    class _ChunkObject:
        def __init__(self, type_name):
            self.type = type_name
    
    class _ContentDeltaChunk:
        def __init__(self, text):
            self.type = 'content_block_delta'
            self.delta = self._TextDelta(text)
        
        class _TextDelta:
            def __init__(self, text):
                self.text = text
    
    class _ThinkingObject:
        def __init__(self, content):
            self.content = content
    
    class _ThinkingUpdateChunk:
        def __init__(self, thinking):
            self.type = 'thinking_update'
            self.thinking = thinking
    
    class _DeltaObject:
        def __init__(self, text):
            self.content = text
            self.text = text
    
    class _MessageDeltaChunk:
        def __init__(self, delta):
            self.type = 'message_delta'
            self.delta = delta
    
    class _ReconnectSignal:
        def __init__(self, session_id, chunk_count):
            self.type = 'reconnect_signal'
            self.session_id = session_id
            self.chunk_count = chunk_count
    
    class _ErrorChunk:
        def __init__(self, error_message):
            self.type = 'error'
            self.error = error_message
    
    class _UsageInfo:
        def __init__(self, input_tokens, output_tokens, thinking_tokens):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.thinking_tokens = thinking_tokens

# Response object for non-streaming API calls
class VercelMessageResponse:
    def __init__(self, result):
        self.id = result.get('id')
        self.content = self._format_content(result.get('content', []))
        self.role = result.get('role', 'assistant')
        self.model = result.get('model')
        self.usage = self._UsageInfo(
            result.get('usage', {}).get('input_tokens', 0),
            result.get('usage', {}).get('output_tokens', 0),
            result.get('usage', {}).get('thinking_tokens', 0)
        )
    
    def _format_content(self, content):
        """Format the content to match how the original client would return it"""
        if isinstance(content, list):
            # For list-type content, transform to expected format
            formatted_content = []
            for item in content:
                if isinstance(item, dict) and 'type' in item and item['type'] == 'text':
                    formatted_content.append({'type': 'text', 'text': item.get('text', '')})
            return formatted_content
        elif isinstance(content, str):
            # For string content, wrap in a list with text object
            return [{'type': 'text', 'text': content}]
        else:
            # Default fallback
            return [{'type': 'text', 'text': str(content) if content else ''}]
    
    class _UsageInfo:
        def __init__(self, input_tokens, output_tokens, thinking_tokens):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.thinking_tokens = thinking_tokens 