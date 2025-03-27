from flask import Flask, request, jsonify, Response
import os
import sys
import json
import traceback
import time

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Constants
GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_MAX_OUTPUT_TOKENS = 128000
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# Import helper functions
try:
    from helper_function import create_gemini_client
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Google Generative AI module is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI module is not installed")

# System instruction
SYSTEM_INSTRUCTION = """
You are a web developer specialized in converting content into beautiful, accessible, responsive HTML with modern CSS.
Generate a single-page website from the given content.
"""

# Initialize Flask app
app = Flask(__name__)

def handler(request):
    """
    Handler function for both server.py and Vercel.
    """
    # Check HTTP method
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = Response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    # Get the data from the request
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided", "success": False}), 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        
        # Check for both 'content' and 'source' parameters for compatibility
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')  # Fallback to 'source' if 'content' is empty
        
        # If neither content nor source is provided, return an error
        if not content:
            return jsonify({"error": "Source code or text is required", "success": False}), 400
        
        # Extract other parameters with defaults
        format_prompt = data.get('format_prompt', '')
        max_tokens = int(data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(data.get('temperature', GEMINI_TEMPERATURE))
        
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content) if content else 0}")
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            return jsonify({
                "error": "Google Generative AI is not available on this server.",
                "details": "Please install the package with: pip install google-generativeai",
                "success": False
            }), 500
        
        # Create Gemini client
        try:
            # Configure the API
            genai.configure(api_key=api_key)
            print(f"Successfully configured Gemini client with API key: {api_key[:4]}...")
            
            # Get the model
            model = genai.GenerativeModel(GEMINI_MODEL)
            print(f"Successfully retrieved Gemini model: {GEMINI_MODEL}")
        except Exception as e:
            error_message = str(e)
            print(f"Failed to create Gemini client: {error_message}")
            return jsonify({
                "error": f"API key validation failed: {error_message}",
                "success": False
            }), 400
        
        # Prepare user message with content and additional prompt
        user_content = content
        if format_prompt:
            user_content = f"{user_content}\n\n{format_prompt}"
        
        # Create the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{user_content[:100000]}
"""
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # Generate content
        try:
            print("Generating content with Gemini (non-streaming)")
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract the HTML from the response using multiple methods
            html_content = ""
            
            try:
                # Try standard text attribute first
                if hasattr(response, 'text'):
                    html_content = response.text
                    print(f"Extracted content from text attribute: {len(html_content)} chars")
                # Then try parts
                elif hasattr(response, 'parts') and response.parts:
                    for part in response.parts:
                        if hasattr(part, 'text'):
                            html_content += part.text
                    print(f"Extracted content from parts: {len(html_content)} chars")
                # Then check candidates
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        html_content += part.text
                    print(f"Extracted content from candidates: {len(html_content)} chars")
                else:
                    # Last resort: try string conversion
                    html_content = str(response)
                    print(f"Extracted content using string conversion: {len(html_content)} chars")
            except Exception as extract_error:
                print(f"Error extracting content: {str(extract_error)}")
                # Try the resolve method as a fallback
                try:
                    if hasattr(response, 'resolve'):
                        resolved = response.resolve()
                        if hasattr(resolved, 'text'):
                            html_content = resolved.text
                            print(f"Extracted content through resolve: {len(html_content)} chars")
                except Exception as resolve_error:
                    print(f"Error resolving response: {str(resolve_error)}")
            
            # If we still don't have content, this is an error
            if not html_content:
                raise ValueError("Could not extract content from Gemini response")
            
            # Get usage stats (approximate since Gemini doesn't provide exact token counts)
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Log response
            print(f"Successfully generated HTML with Gemini. Input tokens: {input_tokens}, Output tokens: {output_tokens}, Length: {len(html_content)} chars")
            
            # Return the response
            return jsonify({
                "success": True,
                "html": html_content,
                "model": GEMINI_MODEL,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "total_cost": 0.0  # Gemini API is currently free
                }
            })
        
        except Exception as e:
            error_message = str(e)
            print(f"Error in Gemini generation: {error_message}")
            print(traceback.format_exc())
            return jsonify({
                "error": f"Generation error: {error_message}",
                "details": traceback.format_exc(),
                "success": False
            }), 500
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in request handler: {error_message}")
        print(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {error_message}",
            "details": traceback.format_exc(),
            "success": False
        }), 500

@app.route('/api/process-gemini', methods=['POST', 'OPTIONS'])
def process_gemini():
    """
    Process a request using Google Gemini API (non-streaming version).
    """
    return handler(request)

# For AWS Lambda and Vercel serverless functions
def vercel_handler(event, context):
    """Handler for Vercel serverless deployment"""
    # Avoid dot-env import issues in Vercel environment
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    
    # Create a mock request object to pass to handler
    class MockRequest:
        def __init__(self, event):
            self.event = event
            self.method = event.get('method', 'POST')
            self._json = json.loads(event.get('body', '{}')) if event.get('body') else {}
            
        def get_json(self):
            return self._json
    
    # Process the request with our handler function
    mock_request = MockRequest(event)
    result = handler(mock_request)
    
    # Return a response that Vercel can understand
    if isinstance(result, tuple):
        response_body, status_code = result
        if isinstance(response_body, Response):
            return {
                'statusCode': status_code,
                'body': response_body.get_data(as_text=True),
                'headers': dict(response_body.headers)
            }
        else:
            return {
                'statusCode': status_code,
                'body': json.dumps(response_body),
                'headers': {'Content-Type': 'application/json'}
            }
    else:
        # Handle direct Response objects
        if isinstance(result, Response):
            return {
                'statusCode': result.status_code,
                'body': result.get_data(as_text=True),
                'headers': dict(result.headers)
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps(result),
                'headers': {'Content-Type': 'application/json'}
            }

if __name__ == "__main__":
    # Run the Flask app for local development
    app.run(host="0.0.0.0", port=5053, debug=True) 