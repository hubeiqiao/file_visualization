from flask import Flask, request, jsonify, Response
import os
import sys
import json
import traceback
import time
import uuid

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
    from helper_function import create_gemini_client, GeminiStreamingResponse
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
    Handler function that processes streaming requests for both server.py and Vercel.
    This can be called from server.py or directly by Vercel serverless functions.
    """
    print("\n==== API PROCESS GEMINI STREAM REQUEST RECEIVED ====")
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Check HTTP method
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = Response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    try:
        # Get the data from the request
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
        
        print(f"Processing Gemini stream request with max_tokens={max_tokens}, content_length={len(content)}")
        
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
            print(f"Created Gemini client with API key: {api_key[:4]}...")
        except Exception as e:
            error_message = str(e)
            print(f"Failed to create Gemini client: {error_message}")
            return jsonify({
                "error": f"API key validation failed: {error_message}",
                "success": False
            }), 400
        
        # Prepare the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{content[:100000]}
"""
        
        if format_prompt:
            prompt += f"\n\n{format_prompt}"
        
        print(f"Prepared prompt for Gemini with length: {len(prompt)}")
        
        # Get the model
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        try:
            # Use GeminiStreamingResponse helper
            return GeminiStreamingResponse(
                model=model,
                prompt=prompt,
                generation_config=generation_config,
                request_id=request_id,
                start_time=start_time
            ).stream_response()
        except Exception as generation_error:
            error_message = str(generation_error)
            print(f"Error in streaming generation: {error_message}")
            print(traceback.format_exc())
            
            return jsonify({
                "error": f"Generation error: {error_message}",
                "details": traceback.format_exc(),
                "success": False
            }), 500
            
    except Exception as e:
        error_message = str(e)
        print(f"Error in stream request: {error_message}")
        print(traceback.format_exc())
        
        return jsonify({
            "error": f"Server error: {error_message}",
            "details": traceback.format_exc(),
            "success": False
        }), 500

@app.route('/api/process-gemini-stream', methods=['POST', 'OPTIONS'])
def process_gemini_stream():
    """
    Process a streaming request using Google Gemini API.
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
        # Handle streaming responses or direct Response objects
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
    app.run(host="0.0.0.0", port=5054, debug=True) 