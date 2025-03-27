import json
import time
import uuid
import traceback
import os
import sys
import base64
from http.server import BaseHTTPRequestHandler

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Try to import helper functions
try:
    from helper_function import create_gemini_client, format_stream_event, GEMINI_AVAILABLE
except ImportError:
    # Define fallbacks if imports fail
    def create_gemini_client(api_key):
        return None
    
    def format_stream_event(event_type, data):
        """Format an event for server-sent events (SSE)."""
        return f"data: {json.dumps(data)}\n\n"
    
    GEMINI_AVAILABLE = False

# Setting runtime configuration for Vercel
__VERCEL_PYTHON_RUNTIME = "3.9"
__VERCEL_HANDLER_MEMORY = 1024
__VERCEL_HANDLER_MAXDURATION = 60

# Global constants for Gemini
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# System instruction for Gemini
SYSTEM_INSTRUCTION = """You are an expert web developer. Transform the provided content into a beautiful, modern, responsive HTML webpage with CSS.

The HTML should:
1. Use modern CSS and HTML5 features
2. Be fully responsive and mobile-friendly
3. Have an attractive, professional design
4. Implement good accessibility practices
5. Use semantic HTML elements properly
6. Have a clean, consistent layout
7. Not use any external JS libraries or CSS frameworks
8. Include all CSS inline in a <style> tag
9. Be complete and ready to render without external dependencies
10. Include engaging visual elements and a cohesive color scheme

Make sure the HTML is valid, self-contained, and will render properly in modern browsers."""

def process_stream_request(request_data):
    """
    Process a file using the Google Gemini API and return streaming HTML.
    """
    print("\n==== API PROCESS GEMINI STREAM REQUEST RECEIVED ====")
    start_time = time.time()
    session_id = str(uuid.uuid4())
    print(f"Generated session ID: {session_id}")
    
    try:
        # Extract request parameters
        api_key = request_data.get('api_key')
        content = request_data.get('content')
        source = request_data.get('source', '')
        format_prompt = request_data.get('format_prompt', '')
        max_tokens = int(request_data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(request_data.get('temperature', GEMINI_TEMPERATURE))
        
        # Use source if content is not provided (for backward compatibility)
        if not content and source:
            content = source
            
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content) if content else 0}")
        
        # Validate required fields
        if not api_key or not content:
            yield format_stream_event("error", {
                "error": "API key and content are required",
                "type": "error",
                "session_id": session_id
            })
            return
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            yield format_stream_event("error", {
                "error": "Google Generative AI package is not installed on the server",
                "type": "error",
                "session_id": session_id
            })
            return
        
        # Create Gemini client
        client = create_gemini_client(api_key)
        if not client:
            yield format_stream_event("error", {
                "error": "Failed to create Gemini client. Check your API key.",
                "type": "error",
                "session_id": session_id
            })
            return
        
        # Prepare content
        if format_prompt:
            content = f"{content}\n\n{format_prompt}"
        
        # Limit content length to avoid token limits
        content_limit = 100000  # Approximately 30k tokens
        if len(content) > content_limit:
            print(f"Content exceeds limit, truncating from {len(content)} to {content_limit} chars")
            content = content[:content_limit]
        
        # Create the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{content}
"""
        
        # Send start event
        yield format_stream_event("stream_start", {
            "message": "Stream starting",
            "session_id": session_id
        })
        
        # Generate stream events
        for event in gemini_stream_generator(client, prompt, max_tokens, temperature, session_id, start_time):
            yield event
            
    except Exception as e:
        # Handle any exception that might occur outside the generator
        print(f"Error in process_stream_request: {str(e)}")
        print(traceback.format_exc())
        yield format_stream_event("error", {
            "error": f"Server error: {str(e)}",
            "type": "error",
            "session_id": session_id
        })

def gemini_stream_generator(client, prompt, max_tokens, temperature, session_id, start_time):
    """Handle the Gemini streaming process and yield events"""
    try:
        # Get the model
        model = client.get_model(GEMINI_MODEL)
        print(f"Successfully retrieved Gemini model: {GEMINI_MODEL}")
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # Send status update
        yield format_stream_event("status", {
            "message": "Model loaded, starting generation",
            "session_id": session_id
        })
        
        # Keep track of chunks for keepalive purposes
        last_chunk_time = time.time()
        chunks_received = 0
        accumulated_content = ""
        
        # Try streaming generation
        try:
            print("Starting streaming generation with Gemini")
            
            # Generate content with streaming
            # Note: Removed timeout parameter as it's not supported and was causing errors
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            # Process the streaming response
            for chunk in response:
                # Update last chunk time
                current_time = time.time()
                chunks_received += 1
                
                # Extract text from the chunk
                chunk_text = ""
                try:
                    if hasattr(chunk, 'text'):
                        chunk_text = chunk.text
                    elif hasattr(chunk, 'parts') and chunk.parts:
                        for part in chunk.parts:
                            if hasattr(part, 'text'):
                                chunk_text += part.text
                except Exception as chunk_error:
                    print(f"Error extracting text from chunk: {str(chunk_error)}")
                    continue
                
                # Skip empty chunks
                if not chunk_text:
                    continue
                    
                # Add to accumulated content
                accumulated_content += chunk_text
                
                # Send content chunk
                yield format_stream_event("content_block_delta", {
                    "delta": {"text": chunk_text},
                    "type": "content_block_delta",
                    "session_id": session_id
                })
                
                # Send keepalive if needed (every 15 chunks or 5 seconds)
                if chunks_received % 15 == 0 or (current_time - last_chunk_time) > 5:
                    last_chunk_time = current_time
                    yield format_stream_event("keepalive", {
                        "type": "keepalive",
                        "session_id": session_id
                    })
            
            # Completed successfully
            total_generation_time = time.time() - start_time
            
            # Calculate approximate token usage
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(accumulated_content.split()) * 1.3))
            
            # Send completion event
            yield format_stream_event("message_complete", {
                "message": "Generation complete",
                "type": "message_complete",
                "html": accumulated_content,
                "session_id": session_id,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "processing_time": total_generation_time
                }
            })
            
            print(f"Streaming completed successfully in {total_generation_time:.2f}s")
            print(f"Generated content length: {len(accumulated_content)} chars")
            print(f"Estimated tokens: Input={input_tokens}, Output={output_tokens}")
            
        except Exception as stream_error:
            print(f"Error during streaming: {str(stream_error)}")
            print(traceback.format_exc())
            
            # If we have accumulated content, continue with it
            if accumulated_content:
                print(f"Using partial content from stream ({len(accumulated_content)} chars)")
                total_generation_time = time.time() - start_time
                
                # Calculate approximate token usage
                input_tokens = max(1, int(len(prompt.split()) * 1.3))
                output_tokens = max(1, int(len(accumulated_content.split()) * 1.3))
                
                # Send completion event with partial content
                yield format_stream_event("message_complete", {
                    "message": "Generation partially complete",
                    "type": "message_complete",
                    "html": accumulated_content,
                    "session_id": session_id,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "processing_time": total_generation_time
                    }
                })
            else:
                # Fallback to non-streaming as a last resort
                print("No content from streaming, trying non-streaming fallback")
                yield format_stream_event("status", {
                    "message": "Trying non-streaming fallback",
                    "session_id": session_id
                })
                
                try:
                    # Generate content without streaming
                    fallback_response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    # Extract content
                    fallback_html = ""
                    if hasattr(fallback_response, 'text'):
                        fallback_html = fallback_response.text
                    elif hasattr(fallback_response, 'parts') and fallback_response.parts:
                        for part in fallback_response.parts:
                            if hasattr(part, 'text'):
                                fallback_html += part.text
                    
                    if fallback_html:
                        total_generation_time = time.time() - start_time
                        
                        # Calculate approximate token usage
                        input_tokens = max(1, int(len(prompt.split()) * 1.3))
                        output_tokens = max(1, int(len(fallback_html.split()) * 1.3))
                        
                        # Send the fallback content
                        yield format_stream_event("content", {
                            "chunk": fallback_html,
                            "type": "content",
                            "session_id": session_id
                        })
                        
                        # Send completion event
                        yield format_stream_event("message_complete", {
                            "message": "Generation complete (fallback)",
                            "type": "message_complete",
                            "html": fallback_html,
                            "session_id": session_id,
                            "usage": {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                                "processing_time": total_generation_time
                            }
                        })
                        
                        print(f"Fallback generation completed in {total_generation_time:.2f}s")
                        print(f"Fallback content length: {len(fallback_html)} chars")
                    else:
                        raise ValueError("No content from non-streaming fallback")
                except Exception as fallback_error:
                    print(f"Fallback generation failed: {str(fallback_error)}")
                    print(traceback.format_exc())
                    yield format_stream_event("error", {
                        "error": f"Generation failed: {str(fallback_error)}",
                        "type": "error",
                        "session_id": session_id
                    })
    except Exception as outer_error:
        print(f"Outer error in Gemini stream generator: {str(outer_error)}")
        print(traceback.format_exc())
        yield format_stream_event("error", {
            "error": f"Server error: {str(outer_error)}",
            "type": "error",
            "session_id": session_id
        })

# Class-based handler for Vercel compatibility
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get content length from headers
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self._send_error_response(400, 'Empty request body')
                return
                
            # Read and parse request body
            request_body = self.rfile.read(content_length).decode('utf-8')
            try:
                request_data = json.loads(request_body)
            except json.JSONDecodeError as e:
                self._send_error_response(400, f'Invalid JSON in request body: {str(e)}')
                return
                
            # Validate request
            if not isinstance(request_data, dict):
                self._send_error_response(400, 'Request data must be a JSON object')
                return
                
            # Validate API key
            api_key = request_data.get('api_key')
            if not api_key or not isinstance(api_key, str) or len(api_key) < 10:
                self._send_error_response(400, 'Invalid API key')
                return
                
            # Validate content
            content = request_data.get('content')
            source = request_data.get('source')
            if (not content or not isinstance(content, str) or not content.strip()) and \
               (not source or not isinstance(source, str) or not source.strip()):
                self._send_error_response(400, 'Content or source must be provided')
                return
                
            # Process streaming request and return events as an array
            print("Processing streaming request...")
            events = list(process_stream_request(request_data))
            
            # Return a combined response with all events
            self._send_response(200, {
                'events': events,
                'success': True
            })
            
        except Exception as e:
            print(f"Error in handler: {str(e)}")
            print(traceback.format_exc())
            self._send_error_response(500, f'Server error: {str(e)}')
            
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
            
    def _send_response(self, status_code, data):
        """Helper method to send a JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        
    def _send_error_response(self, status_code, message):
        """Helper method to send an error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

# For local development using Flask
# This will be ignored when deployed to Vercel
try:
    from flask import Flask, request, Response, jsonify, stream_with_context
    
    app = Flask(__name__)
    
    @app.route('/api/process-gemini-stream', methods=['POST'])
    def process_gemini_stream():
        try:
            # Check for empty request
            content_length = request.headers.get('Content-Length', '0')
            if int(content_length) <= 0:
                return jsonify({
                    'error': 'Empty request body'
                }), 400
            
            # Parse request data
            try:
                request_data = request.get_json()
                if not request_data:
                    return jsonify({
                        'error': 'Invalid or missing JSON data'
                    }), 400
            except Exception as e:
                return jsonify({
                    'error': f'Invalid request: {str(e)}'
                }), 400
            
            # Stream the response
            return Response(
                stream_with_context(process_stream_request(request_data)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        except Exception as e:
            print(f"Error in Flask route: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'error': f"Unexpected error: {str(e)}",
                'details': traceback.format_exc()
            }), 500
except ImportError:
    print("Flask is not available, local development API will not be available")
