import json
import time
import uuid
import traceback
import os
import sys
import base64
from http.server import BaseHTTPRequestHandler

# Format function as a fallback in case import fails
def format_stream_event(event_type, data=None):
    """
    Format data as a server-sent event (fallback implementation)
    """
    event = {"type": event_type}
    
    if data:
        event.update(data)
    
    # Format as SSE
    return f"event: {event_type}\ndata: {json.dumps(data if data else {})}\n\n"

# Try to import helper_function but provide fallbacks
try:
    # Add the parent directory to sys.path if needed
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    from helper_function import create_gemini_client
except ImportError:
    # Define fallback create_gemini_client if import fails
    def create_gemini_client(api_key):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        class GeminiClient:
            def __init__(self):
                pass
                
            def get_model(self, model_name):
                return genai.GenerativeModel(model_name)
        
        return GeminiClient()

# Edge Function configuration - explicitly set runtime to edge
# This enables streaming responses without timeout issues
__VERCEL_EDGE_RUNTIME = True  # Explicit Edge Runtime flag for Vercel Edge Functions
VERCEL_EDGE = True

# Keep the exact model and parameters as specified
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit as specified
GEMINI_TEMPERATURE = 1.0  # Exact temperature as specified
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# GEMINI TEST BRANCH: This branch is for testing Gemini integration with streaming
# Optimized for Vercel Edge Functions without changing any model parameters

# Indicate if Gemini is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Google Generative AI module is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI module is not installed")

# Create a handler class compatible with Vercel
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            # Read request body
            request_body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(request_body)
            
            # Process request and get stream generator immediately
            response_data, status_code, stream_generator = process_stream_request(data)
            
            # Set response headers
            self.send_response(status_code)
            
            # If we have a streaming response (most likely case)
            if stream_generator:
                # Set proper headers for Server-Sent Events (SSE)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'keep-alive')
                self.send_header('X-Accel-Buffering', 'no')
                self.send_header('Transfer-Encoding', 'chunked')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.end_headers()
                
                # Send initial response immediately to prevent initial timeout
                self.wfile.write(format_stream_event("stream_start", {"message": "Stream starting"}).encode('utf-8'))
                self.wfile.flush()
                
                # Send the streaming response
                try:
                    for event in stream_generator:
                        self.wfile.write(event.encode('utf-8'))
                        self.wfile.flush()  # Ensure data is sent immediately
                except Exception as e:
                    # Handle any streaming errors
                    error_event = format_stream_event("error", {
                        "error": f"Streaming error: {str(e)}",
                        "details": traceback.format_exc()
                    })
                    self.wfile.write(error_event.encode('utf-8'))
                    self.wfile.flush()
            else:
                # Regular JSON response for errors
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.end_headers()
                
                # Send the JSON response
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def process_stream_request(request_data):
    """
    Process a streaming request using Gemini API with proper Edge Function handling
    Compatible with the reference implementation for streaming
    """
    try:
        # Extract request data
        data = request_data
        api_key = data.get('api_key')
        
        # Check for both 'content' and 'source' parameters for compatibility
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')  # Fallback to 'source' if 'content' is empty
        
        # If content is empty, return an error
        if not content:
            return {"error": "Source code or text is required"}, 400, None
        
        format_prompt = data.get('format_prompt', '')
        
        # Use exact parameters from reference implementation
        max_tokens = GEMINI_MAX_OUTPUT_TOKENS
        temperature = GEMINI_TEMPERATURE
        
        # Create a session ID
        session_id = str(uuid.uuid4())
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            error_msg = 'Google Generative AI package is not installed on the server.'
            print(f"Error: {error_msg}")
            return {
                'error': error_msg,
                'details': 'Please install the Google Generative AI package with "pip install google-generativeai"'
            }, 500, None
        
        # Create Gemini client
        try:
            client = create_gemini_client(api_key)
            print(f"Gemini client created successfully with API key: {api_key[:4]}...")
        except Exception as e:
            error_msg = f"API key validation failed: {str(e)}"
            print(f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }, 401, None
        
        # For compatibility with reference code, don't truncate too much
        max_content_length = 100000
        truncated_content = content[:max_content_length]
        
        if format_prompt:
            truncated_content = f"{truncated_content}\n\n{format_prompt}"
        
        print(f"Prepared prompt for Gemini with length: {len(truncated_content)}")
        
        # Define the streaming response generator - optimized for Edge Functions
        def gemini_stream_generator():
            try:
                # Send a starting event immediately to start the response
                yield format_stream_event("stream_start", {"message": "Stream starting", "session_id": session_id})
                
                # Send a keepalive message right away to establish the stream
                yield format_stream_event("keepalive", {"message": "Connection established", "session_id": session_id})
                
                try:
                    # Get the model - using exact model from reference
                    model = client.get_model(GEMINI_MODEL)
                    print(f"Successfully retrieved Gemini model: {GEMINI_MODEL}")
                    
                    # Configure generation parameters - using exact params from reference
                    generation_config = {
                        "max_output_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": GEMINI_TOP_P,
                        "top_k": GEMINI_TOP_K,
                        "response_mime_type": "text/plain"
                    }
                    
                    # Prepare content in the same structure as reference implementation
                    html_content = ""
                    start_time = time.time()
                    
                    try:
                        # Create content in format matching reference implementation
                        contents = [
                            {
                                "role": "user",
                                "parts": [{"text": truncated_content}]
                            }
                        ]
                        
                        print("Starting streaming response generation")
                        
                        # Start stream generation with reference parameters - no timeout parameter
                        stream = model.generate_content(
                            contents,
                            generation_config=generation_config,
                            stream=True
                        )
                        
                        # Track timing for keepalives
                        last_keepalive_time = time.time()
                        last_yield_time = time.time()
                        has_sent_content = False
                        chunk_buffer = []
                        
                        # Process the stream with more frequent keepalives to prevent timeouts
                        for chunk in stream:
                            # Extract text from chunk
                            chunk_text = chunk.text if hasattr(chunk, 'text') else ""
                            
                            # Send intermittent keepalive messages to prevent timeout
                            # Edge Functions require some activity every few seconds
                            current_time = time.time()
                            if current_time - last_keepalive_time >= 3:  # Reduced from 5 to 3 seconds
                                yield format_stream_event("keepalive", {"timestamp": current_time, "session_id": session_id})
                                last_keepalive_time = current_time
                            
                            if chunk_text:
                                # Mark that we've received content
                                has_sent_content = True
                                
                                # Accumulate text in buffer
                                chunk_buffer.append(chunk_text)
                                html_content += chunk_text
                                
                                # Yield more frequently for Edge Functions
                                current_time = time.time()
                                if current_time - last_yield_time >= 0.2 or len(chunk_buffer) >= 3:  # More frequent updates
                                    # Send accumulated chunks
                                    combined_text = ''.join(chunk_buffer)
                                    yield format_stream_event("content", {
                                        "chunk": combined_text,
                                        "chunk_id": f"{session_id}_{len(html_content)}",
                                        "session_id": session_id
                                    })
                                    
                                    # Reset buffer and time
                                    chunk_buffer = []
                                    last_yield_time = current_time
                                    last_keepalive_time = current_time
                        
                        # Send any remaining chunks
                        if chunk_buffer:
                            combined_text = ''.join(chunk_buffer)
                            yield format_stream_event("content", {
                                "chunk": combined_text,
                                "chunk_id": f"{session_id}_final",
                                "session_id": session_id
                            })
                            
                        print(f"Stream completed, generated {len(html_content)} characters")
                        
                        # If no content was generated, provide fallback
                        if not has_sent_content or not html_content:
                            # Generate a simple fallback HTML
                            fallback_html = f"""
                            <!DOCTYPE html>
                            <html lang="en">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Content Visualization</title>
                                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                            </head>
                            <body class="bg-gray-100 p-4">
                                <div class="container mx-auto bg-white p-6 rounded shadow">
                                    <h1 class="text-2xl font-bold mb-4">Content Visualization</h1>
                                    <div class="prose">
                                        <pre class="bg-gray-100 p-4 rounded overflow-auto">{truncated_content[:500]}...</pre>
                                    </div>
                                    <p class="mt-4 text-sm text-gray-500">Note: No content was generated from the API.</p>
                                </div>
                            </body>
                            </html>
                            """
                            yield format_stream_event("content", {
                                "chunk": fallback_html,
                                "chunk_id": f"{session_id}_fallback",
                                "session_id": session_id
                            })
                            html_content = fallback_html
                            
                    except Exception as stream_error:
                        print(f"Streaming error: {str(stream_error)}")
                        # Send error information in the stream
                        yield format_stream_event("error", {
                            "error": str(stream_error),
                            "session_id": session_id
                        })
                        
                        # If streaming fails, fall back to synchronous generation
                        if not html_content:
                            print("Stream failed, attempting synchronous generation")
                            
                            # Try synchronous generation with timeout
                            try:
                                # Use same config as streamed version
                                response = model.generate_content(
                                    contents,
                                    generation_config=generation_config
                                )
                                
                                # Extract content
                                if hasattr(response, 'text'):
                                    html_content = response.text
                                elif hasattr(response, 'parts') and response.parts:
                                    for part in response.parts:
                                        if hasattr(part, 'text'):
                                            html_content += part.text
                                
                                # Send the entire content
                                if html_content:
                                    yield format_stream_event("content", {
                                        "chunk": html_content,
                                        "chunk_id": f"{session_id}_complete",
                                        "session_id": session_id
                                    })
                            except Exception as fallback_error:
                                print(f"Fallback generation also failed: {str(fallback_error)}")
                                # Generate a fallback HTML for complete failure
                                fallback_html = f"""
                                <!DOCTYPE html>
                                <html lang="en">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>Content Visualization</title>
                                    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                                </head>
                                <body class="bg-gray-100 p-4">
                                    <div class="container mx-auto bg-white p-6 rounded shadow">
                                        <h1 class="text-2xl font-bold mb-4">Content Visualization</h1>
                                        <div class="prose">
                                            <pre class="bg-gray-100 p-4 rounded overflow-auto">{truncated_content[:500]}...</pre>
                                        </div>
                                        <p class="mt-4 text-sm text-gray-500">Error: API generation failed. Please try again.</p>
                                    </div>
                                </body>
                                </html>
                                """
                                yield format_stream_event("content", {
                                    "chunk": fallback_html,
                                    "chunk_id": f"{session_id}_fallback",
                                    "session_id": session_id
                                })
                                html_content = fallback_html
                    
                    # Calculate approx stats
                    end_time = time.time()
                    generation_time = end_time - start_time
                    
                    input_tokens = max(1, int(len(truncated_content.split()) * 1.3))
                    output_tokens = max(1, int(len(html_content.split()) * 1.3))
                    
                    print(f"Generation completed in {generation_time:.2f}s")
                    
                    # Send completion event
                    yield format_stream_event("content", {
                        "type": "message_complete",
                        "chunk_id": f"{session_id}_complete",
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                            "total_cost": 0.0
                        },
                        "html": html_content,
                        "session_id": session_id
                    })
                    
                except Exception as generation_error:
                    print(f"Error generating content: {str(generation_error)}")
                    traceback.print_exc()
                    
                    # Generate fallback HTML for error case
                    fallback_html = f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Content Visualization</title>
                        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                    </head>
                    <body class="bg-gray-100 p-4">
                        <div class="container mx-auto bg-white p-6 rounded shadow">
                            <h1 class="text-2xl font-bold mb-4">Content Visualization</h1>
                            <div class="prose">
                                <pre class="bg-gray-100 p-4 rounded overflow-auto">{truncated_content[:500]}...</pre>
                            </div>
                            <p class="mt-4 text-sm text-gray-500">Error: {str(generation_error)}</p>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Return fallback HTML in case of error
                    yield format_stream_event("content", {
                        "chunk": fallback_html,
                        "chunk_id": f"{session_id}_error",
                        "session_id": session_id,
                        "error": str(generation_error)
                    })
                    
                    # Send error event
                    yield format_stream_event("error", {
                        "error": str(generation_error),
                        "session_id": session_id
                    })
                    
            except Exception as e:
                print(f"Stream generator error: {str(e)}")
                traceback.print_exc()
                
                # Always ensure we send some response
                yield format_stream_event("error", {
                    "error": str(e),
                    "session_id": session_id
                })
        
        # Return the generator for streaming
        return None, 200, gemini_stream_generator()
        
    except Exception as e:
        print(f"Handler error: {str(e)}")
        traceback.print_exc()
        return {
            'error': f'Stream handler error: {str(e)}',
            'details': traceback.format_exc()
        }, 500, None

# For local Flask development, keep this code but don't expose it to Vercel
if 'FLASK_APP' in os.environ or not os.environ.get('VERCEL'):
    from flask import Flask, request, Response, stream_with_context, jsonify
    
    # Try to import app from server if in development mode
    try:
        from server import app
        
        @app.route('/api/process-gemini-stream', methods=['POST'])
        def process_gemini_stream_endpoint():
            """Flask endpoint for streaming in development."""
            try:
                data = request.get_json()
                response_data, status_code, stream_generator = process_stream_request(data)
                
                # If streaming response
                if stream_generator:
                    return Response(
                        stream_with_context(stream_generator),
                        mimetype='text/event-stream',
                        headers={
                            'Cache-Control': 'no-cache',
                            'Connection': 'keep-alive',
                            'Content-Type': 'text/event-stream',
                            'X-Accel-Buffering': 'no'
                        }
                    )
                else:
                    # Return standard JSON response for errors
                    return jsonify(response_data), status_code
            except Exception as e:
                return jsonify({
                    'error': f'Server error: {str(e)}',
                    'details': traceback.format_exc()
                }), 500
    except ImportError:
        print("Warning: Could not import server.app, local development may not work properly")
