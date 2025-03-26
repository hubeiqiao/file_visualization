from flask import request, jsonify, Response, stream_with_context
import json
import time
import uuid
import traceback

from server import app
from helper_function import create_gemini_client, format_stream_event

# Global constants for Gemini
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"
GEMINI_MAX_OUTPUT_TOKENS = 128000
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# Indicate if Gemini is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Google Generative AI module is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI module is not installed")

# System instruction for Gemini
SYSTEM_INSTRUCTION = """You are a web developer tasked with turning content into a beautiful, responsive website. 
Create valid, semantic HTML with embedded CSS (using Tailwind CSS) that transforms the provided content into a well-structured, modern-looking website.

Follow these guidelines:
1. Use Tailwind CSS for styling (via CDN) and create a beautiful, responsive design
2. Structure the content logically with appropriate HTML5 semantic elements
3. Make the website responsive across all device sizes
4. Include dark mode support with a toggle button
5. For code blocks, use proper syntax highlighting
6. Ensure accessibility by using appropriate ARIA attributes and semantics
7. Add subtle animations where appropriate
8. Include a navigation system if the content has distinct sections
9. Avoid using external JavaScript libraries other than Tailwind
10. Only generate HTML, CSS, and minimal JavaScript - no backend code or server setup

Return ONLY the complete HTML document with no explanations. The HTML should be ready to use as a standalone file."""

# In-memory session cache for handling reconnections
session_cache = {}

def handler(request):
    """
    Process a streaming request using Gemini API - no actual streaming for reliability.
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
        max_tokens = int(data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(data.get('temperature', GEMINI_TEMPERATURE))
        
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
        
        # Prepare prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{content[:100000]}
"""
        
        if format_prompt:
            prompt += f"\n\n{format_prompt}"
        
        print(f"Prepared prompt for Gemini with length: {len(prompt)}")
        
        # Define the streaming response generator
        def gemini_stream_generator():
            try:
                # Send a starting event
                yield format_stream_event("stream_start", {"message": "Stream starting", "session_id": session_id})
                
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
                    
                    # Generate content using non-streaming approach
                    start_time = time.time()
                    html_content = None
                    
                    # Try to generate content
                    try:
                        print("Using non-streaming approach for reliability")
                        
                        # Generate the content
                        response = model.generate_content(
                            prompt,
                            generation_config=generation_config,
                            stream=False
                        )
                        
                        # Wait a moment for the response to be ready
                        time.sleep(0.5)
                        
                        # Try to get resolved text
                        try:
                            resolved = response.resolve()
                            html_content = resolved.text
                            print(f"Successfully resolved response with length: {len(html_content)}")
                        except Exception as e:
                            print(f"Could not resolve response: {str(e)}")
                        
                        # If resolve didn't work, try direct access
                        if not html_content:
                            try:
                                html_content = response.text
                                print(f"Got content directly from text attribute: {len(html_content)}")
                            except Exception as e:
                                print(f"Could not get text attribute: {str(e)}")
                        
                        # If still no content, try parts
                        if not html_content:
                            try:
                                if hasattr(response, 'parts') and response.parts:
                                    html_content = ''.join(part.text for part in response.parts if hasattr(part, 'text'))
                                    print(f"Got content from parts: {len(html_content)}")
                            except Exception as e:
                                print(f"Could not get parts: {str(e)}")
                        
                        # If still no content, try candidates
                        if not html_content:
                            try:
                                if hasattr(response, 'candidates') and response.candidates:
                                    for candidate in response.candidates:
                                        if hasattr(candidate, 'content') and candidate.content:
                                            if hasattr(candidate.content, 'parts'):
                                                for part in candidate.content.parts:
                                                    if hasattr(part, 'text'):
                                                        html_content = (html_content or '') + part.text
                                    print(f"Got content from candidates: {len(html_content) if html_content else 0}")
                            except Exception as e:
                                print(f"Could not get candidates: {str(e)}")
                                
                        # Last resort: use string conversion but check it's not an error message
                        if not html_content:
                            try:
                                raw_content = str(response)
                                if not raw_content.startswith('<') and '<!DOCTYPE html>' in raw_content:
                                    html_content = raw_content
                                    print(f"Got content from string conversion: {len(html_content)}")
                            except Exception as e:
                                print(f"Could not convert to string: {str(e)}")
                        
                        # Check if we have content
                        if not html_content:
                            print("Failed to extract any content from Gemini response")
                            yield format_stream_event("error", {
                                "type": "error",
                                "error": "Could not extract content from Gemini response",
                                "session_id": session_id
                            })
                            return
                            
                        end_time = time.time()
                        generation_time = end_time - start_time
                        
                        # Calculate tokens (approximate)
                        input_tokens = max(1, int(len(prompt.split()) * 1.3))
                        output_tokens = max(1, int(len(html_content.split()) * 1.3))
                        
                        print(f"Successfully generated HTML with {output_tokens} tokens in {generation_time:.2f}s")
                        
                        # Send the completion event with the full HTML
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
                        
                        yield format_stream_event("error", {
                            "type": "error",
                            "error": f"Gemini generation error: {str(generation_error)}",
                            "details": traceback.format_exc(),
                            "session_id": session_id
                        })
                        
                except Exception as model_error:
                    print(f"Error getting model: {str(model_error)}")
                    traceback.print_exc()
                    
                    yield format_stream_event("error", {
                        "type": "error",
                        "error": f"Gemini model error: {str(model_error)}",
                        "details": traceback.format_exc(),
                        "session_id": session_id
                    })
                    
            except Exception as outer_error:
                print(f"Outer error in stream generator: {str(outer_error)}")
                traceback.print_exc()
                
                yield format_stream_event("error", {
                    "type": "error",
                    "error": f"Server error: {str(outer_error)}",
                    "details": traceback.format_exc(),
                    "session_id": session_id
                })
        
        # Return the stream response
        return Response(
            stream_with_context(gemini_stream_generator()),
            content_type='text/event-stream'
        )
        
    except Exception as request_error:
        # Handle errors in the outer request handler
        error_message = str(request_error)
        print(f"Error in request handler: {error_message}")
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": error_message,
            "details": traceback.format_exc()
        }), 500

@app.route('/', methods=['POST'])
def process_gemini_stream():
    return handler(request) 