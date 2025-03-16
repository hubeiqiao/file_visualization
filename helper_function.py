# Helper functions for server.py
import anthropic
import os
import json
import requests
import time

def create_anthropic_client(api_key):
    """
    Create an Anthropic client that is compatible with both local and Vercel environments.
    For Vercel, we use a completely different approach to avoid the proxies issue.
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    
    # Special handling for Vercel environment
    if is_vercel:
        return VercelCompatibleClient(api_key)
    
    # Local environment - use standard approach
    try:
        # For newer versions of the anthropic library
        if hasattr(anthropic, 'Anthropic'):
            # Create client with only the essential parameter (no proxies)
            kwargs = {"api_key": api_key}
            return anthropic.Anthropic(**kwargs)
        
        # For older versions of the anthropic library
        elif hasattr(anthropic, 'Client'):
            # Create client with only the essential parameter (no proxies)
            kwargs = {"api_key": api_key}
            return anthropic.Client(**kwargs)
        
        # Last resort fallbacks
        else:
            # Try to import classes directly
            try:
                # Try newer class
                from anthropic import Anthropic
                return Anthropic(api_key=api_key)
            except (ImportError, AttributeError):
                try:
                    # Try older class
                    from anthropic import Client
                    return Client(api_key=api_key)
                except (ImportError, AttributeError):
                    raise ImportError("Could not import Anthropic or Client class")
    except Exception as e:
        # Provide detailed error information
        if "proxies" in str(e):
            raise Exception(f"API client error: The Anthropic library version has a compatibility issue. Error: {str(e)}")
        elif "auth" in str(e).lower() or "key" in str(e).lower() or "invalid" in str(e).lower():
            raise Exception(f"API authentication failed: {str(e)}")
        else:
            raise Exception(f"Failed to create Anthropic client: {str(e)}")

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
            
            def stream(self, model, max_tokens, temperature, system, messages, thinking=None, betas=None):
                """
                Stream the response from the Anthropic API directly
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
                    "messages": formatted_messages,
                    "stream": True
                }
                
                # Add thinking if specified
                if thinking:
                    payload["thinking"] = thinking
                
                # Add beta features if specified - Fixed to use the correct format
                # The Anthropic API expects beta features to be in the 'anthropic-beta' header
                headers = dict(self.client.headers)
                if betas and isinstance(betas, list) and len(betas) > 0:
                    headers["anthropic-beta"] = ",".join(betas)
                
                # Make the API request to stream response
                stream_response = requests.post(
                    f"{self.client.base_url}/messages",
                    headers=headers,
                    json=payload,
                    stream=True
                )
                
                if stream_response.status_code != 200:
                    # Try to get error message
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
                return VercelStreamingResponse(stream_response, self.client)
    
    # Regular messages namespace
    class _MessagesNamespace:
        def __init__(self, client):
            self.client = client
        
        def create(self, model, max_tokens, temperature, system, messages, thinking=None, betas=None):
            """
            Create a message using the Anthropic API directly (non-streaming)
            """
            # Convert messages to API format (similar to streaming version)
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
            
            # Add thinking if specified
            if thinking:
                payload["thinking"] = thinking
                
            # Add beta features if specified - Fixed to use the correct format
            # The Anthropic API expects beta features to be in the 'anthropic-beta' header
            headers = dict(self.client.headers)
            if betas and isinstance(betas, list) and len(betas) > 0:
                headers["anthropic-beta"] = ",".join(betas)
            
            # Make the API request
            response = requests.post(
                f"{self.client.base_url}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                # Handle error
                try:
                    error_json = response.json()
                    error_msg = error_json.get('error', {}).get('message', response.text)
                except Exception:
                    error_msg = response.text
                
                raise Exception(f"API request failed: {error_msg}")
            
            # Parse the response
            result = response.json()
            
            # Create a response object that mimics the Anthropic client response
            return VercelMessageResponse(result)

# Wrapper for the streaming response
class VercelStreamingResponse:
    def __init__(self, stream_response, client):
        self.stream_response = stream_response
        self.client = client
        self.usage = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stream_response.close()
    
    def __iter__(self):
        """Iterator that parses SSE format and yields message chunks"""
        buffer = ""
        input_tokens = 0
        output_tokens = 0
        thinking_tokens = 0
        
        for line in self.stream_response.iter_lines():
            if not line:
                continue
                
            line_text = line.decode('utf-8')
            
            # Skip lines that don't start with 'data: '
            if not line_text.startswith('data: '):
                continue
                
            # Extract the JSON data
            data = line_text[6:]  # Remove 'data: ' prefix
            
            # Check for the [DONE] message
            if data == "[DONE]":
                # Create usage object at the end
                self.usage = self._UsageInfo(input_tokens, output_tokens, thinking_tokens)
                break
            
            try:
                # Parse the chunk JSON
                chunk = json.loads(data)
                
                # Extract any usage information
                if 'usage' in chunk:
                    if 'input_tokens' in chunk['usage']:
                        input_tokens = chunk['usage']['input_tokens']
                    if 'output_tokens' in chunk['usage']:
                        output_tokens = chunk['usage']['output_tokens']
                    if 'thinking_tokens' in chunk['usage'] or 'thinking' in chunk['usage']:
                        thinking_tokens = chunk['usage'].get('thinking_tokens', chunk['usage'].get('thinking', 0))
                
                # Create a compatible chunk object based on the event type
                if chunk.get('type') == 'message_start':
                    yield self._ChunkObject('message_start')
                elif chunk.get('type') == 'content_block_start':
                    yield self._ChunkObject('content_block_start')
                elif chunk.get('type') == 'content_block_delta':
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        yield self._ContentDeltaChunk(chunk['delta']['text'])
                elif chunk.get('type') == 'thinking_start':
                    yield self._ChunkObject('thinking_start')
                elif chunk.get('type') == 'thinking_update':
                    if 'thinking' in chunk and 'content' in chunk['thinking']:
                        thinking_obj = self._ThinkingObject(chunk['thinking']['content'])
                        yield self._ThinkingUpdateChunk(thinking_obj)
                elif chunk.get('type') == 'thinking_end':
                    yield self._ChunkObject('thinking_end')
                elif chunk.get('type') == 'message_delta':
                    content = ""
                    if 'delta' in chunk and 'content' in chunk['delta']:
                        content = chunk['delta']['content']
                    elif 'delta' in chunk and 'text' in chunk['delta']:
                        content = chunk['delta']['text']
                    
                    if content:
                        delta_obj = self._DeltaObject(content)
                        yield self._MessageDeltaChunk(delta_obj)
                elif chunk.get('type') == 'message_stop':
                    yield self._ChunkObject('message_stop')
                
            except json.JSONDecodeError:
                # Skip malformed chunks
                continue
    
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
            0  # Non-streaming doesn't support thinking tokens
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
            return content
    
    class _UsageInfo:
        def __init__(self, input_tokens, output_tokens, thinking_tokens):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.thinking_tokens = thinking_tokens 