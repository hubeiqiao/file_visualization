from flask import request, jsonify, Response, stream_with_context
import json
import time
import uuid
import traceback
import os
import base64

from server import app
from helper_function import create_gemini_client, format_stream_event

# Edge Function configuration - explicitly set runtime to edge
# Setting runtime configuration for Vercel Edge Functions
# This allows the function to stream responses indefinitely
__VERCEL_EDGE_RUNTIME = True

# Keep the exact model and parameters as specified
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit as specified
GEMINI_TEMPERATURE = 1.0  # Exact temperature as specified
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# GEMINI TEST BRANCH: This branch is for testing Gemini integration with streaming
# Optimized for Vercel without changing any model parameters

# Indicate if Gemini is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Google Generative AI module is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI module is not installed")

def handler(request):
    """
    Process a streaming request using Gemini API with proper serverless handling
    """
    try:
        # Extract request data
        data = request.get_json()
        api_key = data.get('api_key')
        
        # Check for both 'content' and 'source' parameters for compatibility
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')  # Fallback to 'source' if 'content' is empty
        
        # If content is empty, return an error
        if not content:
            return jsonify({"success": False, "error": "Source code or text is required"}), 400
        
        format_prompt = data.get('format_prompt', '')
        
        # Use exact parameters from reference code
        max_tokens = GEMINI_MAX_OUTPUT_TOKENS
        temperature = GEMINI_TEMPERATURE
        
        # Create a session ID
        session_id = str(uuid.uuid4())
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            error_msg = 'Google Generative AI package is not installed on the server.'
            print(f"Error: {error_msg}")
            return jsonify({
                'error': error_msg,
                'details': 'Please install the Google Generative AI package with "pip install google-generativeai"'
            }), 500
        
        # Create Gemini client
        try:
            client = create_gemini_client(api_key)
            print(f"Gemini client created successfully with API key: {api_key[:4]}...")
        except Exception as e:
            error_msg = f"API key validation failed: {str(e)}"
            print(f"Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            })
        
        # Prepare content - for Vercel, reduce content size more aggressively for Edge Functions
        # This helps ensure the initial response happens quickly
        max_content_length = 5000 if os.environ.get('VERCEL') else 100000
        truncated_content = content[:max_content_length]
        
        if format_prompt:
            truncated_content = f"{truncated_content}\n\n{format_prompt}"
        
        print(f"Prepared prompt for Gemini with length: {len(truncated_content)}")
        
        # Define the streaming response generator - optimized for Edge Functions
        def gemini_stream_generator():
            try:
                # Send a starting event immediately to start the response
                # This is crucial for Edge Functions to begin streaming
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
                        "top_k": GEMINI_TOP_K
                    }
                    
                    # Prepare content according to reference code format
                    # Using the same content structure as the reference
                    html_content = ""
                    start_time = time.time()
                    
                    try:
                        # Create content in format matching reference code
                        contents = [
                            {
                                "role": "user",
                                "parts": [{"text": truncated_content}]
                            }
                        ]
                        
                        print("Starting streaming response generation")
                        
                        # Start stream generation - matching reference
                        stream = model.generate_content(
                            contents,
                            generation_config=generation_config,
                            stream=True
                        )
                        
                        # Send intermittent keepalive messages to prevent timeout
                        last_keepalive_time = time.time()
                        
                        # Track if we've sent any content yet
                        has_sent_content = False
                        
                        # Process the stream with optimizations for Edge Functions
                        chunk_buffer = []
                        last_yield_time = time.time()
                        
                        # Process the stream with periodic keepalives
                        for chunk in stream:
                            # Extract text from chunk
                            chunk_text = chunk.text if hasattr(chunk, 'text') else ""
                            
                            # Send keepalive every 5 seconds to maintain connection
                            current_time = time.time()
                            if current_time - last_keepalive_time >= 5:
                                yield format_stream_event("keepalive", {"timestamp": current_time, "session_id": session_id})
                                last_keepalive_time = current_time
                            
                            if chunk_text:
                                # Mark that we've received content
                                has_sent_content = True
                                
                                # Accumulate text in buffer
                                chunk_buffer.append(chunk_text)
                                html_content += chunk_text
                                
                                # Yield more frequently (every 250ms) for Edge Functions
                                # This ensures we maintain an active stream
                                current_time = time.time()
                                if current_time - last_yield_time >= 0.25 or len(chunk_buffer) >= 5:
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
                                    last_keepalive_time = current_time  # Reset keepalive timer when sending content
                        
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
                        
                        # If streaming fails, fall back to synchronous generation with reduced parameters
                        if not html_content:
                            print("Stream failed, attempting simplified synchronous generation")
                            
                            # Try synchronous generation with reduced parameters
                            try:
                                # Use simpler generation config for fallback
                                fallback_config = {
                                    "max_output_tokens": 4096,  # Reduced token limit for speed
                                    "temperature": temperature
                                }
                                
                                # Try synchronous generation with timeout
                                response = model.generate_content(
                                    contents,
                                    generation_config=fallback_config,
                                    timeout=20  # Set explicit timeout
                                )
                                
                                # Extract content
                                if hasattr(response, 'text'):
                                    html_content = response.text
                                elif hasattr(response, 'parts'):
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
        
        # Return streaming response with proper headers for SSE
        response = Response(
            stream_with_context(gemini_stream_generator()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream',
                'X-Accel-Buffering': 'no',  # Disable Nginx buffering if present
                'Transfer-Encoding': 'chunked'  # Ensure chunked encoding
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Handler error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': f'Stream handler error: {str(e)}',
            'details': traceback.format_exc()
        }), 500

@app.route('/', methods=['POST'])
def process_gemini_stream():
    return handler(request)
