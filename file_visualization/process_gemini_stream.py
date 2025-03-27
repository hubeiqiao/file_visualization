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
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"
GEMINI_MAX_OUTPUT_TOKENS = 65536
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

# System instruction - matching the one used for Claude
SYSTEM_INSTRUCTION = """I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.### Content Requirements* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.⠀Design Style* Follow a modern and minimalistic design inspired by Linear App.* Use a clear visual hierarchy to emphasize important content.* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.⠀Technical Specifications* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.* Implement a fully functional dark/light mode toggle, defaulting to the system setting.* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.⠀Responsive Design* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.* Optimize layout and typography for different screen sizes.* Ensure a smooth and intuitive touch experience on mobile devices.⠀Icons & Visual Elements* Use professional icon libraries like Font Awesome or Material Icons (via CDN).* Integrate illustrations or charts that best represent the content.* Avoid using emojis as primary icons.* Check if any icons cannot be loaded.⠀User Interaction & ExperienceEnhance the user experience with subtle micro-interactions:* Buttons should have slight enlargement and color transitions on hover.* Cards should feature soft shadows and border effects on hover.* Implement smooth scrolling effects throughout the page.* Content blocks should have an elegant fade-in animation on load.⠀Performance Optimization* Ensure fast page loading by avoiding large, unnecessary resources.* Use modern image formats (WebP) with proper compression.* Implement lazy loading for content-heavy pages.⠀Output Requirements* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.* Ensure the code meets W3C standards with no errors or warnings.* Maintain consistent design and functionality across different browsers.* Your output is only one HTML file, do not present any other notes on the HTML. Also, try your best to visualize the whole content.⠀Create the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.)."""

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
        
        # Prepare the prompt - direct content without additional text
        prompt = f"{content[:100000]}"
        
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
            "top_k": GEMINI_TOP_K,
            "response_mime_type": "text/plain"
        }
        
        try:
            # Combine system instruction and prompt
            full_prompt = f"{SYSTEM_INSTRUCTION}\n\nHere is the content to transform into a website:\n\n{prompt}"
            
            # Generate the stream response
            stream_response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
                stream=True
            )
            
            # Use GeminiStreamingResponse helper
            return GeminiStreamingResponse(
                stream_response=stream_response,
                session_id=request_id
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