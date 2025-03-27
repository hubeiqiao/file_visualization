import os
import sys
import json
import traceback
import time
import base64
from http.server import BaseHTTPRequestHandler

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from helper_function import create_gemini_client, GEMINI_AVAILABLE
except ImportError:
    # Define fallbacks if imports fail
    def create_gemini_client(api_key):
        return None
    GEMINI_AVAILABLE = False

# Setting runtime configuration for Vercel Edge Functions
__VERCEL_PYTHON_RUNTIME = "3.9"
__VERCEL_HANDLER = "handler"
__VERCEL_HANDLER_MEMORY = 1024
__VERCEL_HANDLER_MAXDURATION = 60

# Global constants for Gemini
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# Try to import DeadlineExceeded exception
try:
    from google.api_core.exceptions import DeadlineExceeded
except ImportError:
    # Define a fallback if the import fails
    class DeadlineExceeded(Exception):
        pass

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

def process_request(request_data):
    """
    Process a file using the Google Gemini API and return HTML.
    """
    # Get the data from the request
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    start_time = time.time()
    
    try:
        # Extract the API key and content
        api_key = request_data.get('api_key')
        content = request_data.get('content')
        source = request_data.get('source', '')
        format_prompt = request_data.get('format_prompt', '')
        max_tokens = int(request_data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(request_data.get('temperature', GEMINI_TEMPERATURE))
        
        # Use source if content is not provided
        if not content and source:
            content = source
        
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content) if content else 0}")
        
        # Check if we have the required data
        if not api_key or not content:
            return {
                'error': 'API key and content are required'
            }, 400
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            return {
                'error': 'Google Generative AI package is not installed on the server.'
            }, 500
        
        # Use our helper function to create a Gemini client
        client = create_gemini_client(api_key)
        if not client:
            return {
                'error': 'Failed to create Gemini client. Check your API key.'
            }, 400
        
        # Prepare user message with content and additional prompt
        user_content = content
        if format_prompt:
            user_content = f"{user_content}\n\n{format_prompt}"
        
        print("Creating Gemini model...")
        
        # Get the model
        model = client.get_model(GEMINI_MODEL)
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # Create the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{user_content}
"""
        
        # Generate content
        try:
            print("Generating content with Gemini (non-streaming)")
            generation_start_time = time.time()
            
            # Important: Remove the timeout parameter as it's not supported
            # and is causing the 504 Gateway Timeout errors
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Try to resolve the response first
            html_content = ""
            try:
                if hasattr(response, 'resolve'):
                    resolved = response.resolve()
                    if hasattr(resolved, 'text'):
                        html_content = resolved.text
                        print(f"Successfully resolved response: {len(html_content)} chars")
                    elif hasattr(resolved, 'parts') and resolved.parts:
                        html_content = resolved.parts[0].text
                        print(f"Successfully resolved response through parts: {len(html_content)} chars")
                elif hasattr(response, 'text'):
                    html_content = response.text
                    print(f"Got response.text directly: {len(html_content)} chars")
                elif hasattr(response, 'parts') and response.parts:
                    html_content = response.parts[0].text
                    print(f"Got response from parts directly: {len(html_content)} chars")
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        html_content = candidate.content.parts[0].text
                        print(f"Got response from candidates: {len(html_content)} chars")
            except Exception as resolve_error:
                print(f"Error resolving response: {str(resolve_error)}")
                print(traceback.format_exc())
            
            # If no content was extracted, try a different approach
            if not html_content:
                try:
                    # Try to get the text in different ways
                    html_content = str(response)
                    if html_content.startswith("<genai."):
                        # This is just the object representation, not actual content
                        html_content = ""
                except Exception as str_error:
                    print(f"Error converting response to string: {str(str_error)}")
            
            if not html_content:
                return {
                    'error': 'Failed to extract content from Gemini response'
                }, 500
            
            # Get usage stats (approximate since Gemini doesn't provide exact token counts)
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Log response
            print(f"Successfully generated HTML with Gemini in {total_time:.2f}s. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            # Return the response
            return {
                'html': html_content,
                'model': GEMINI_MODEL,
                'processing_time': total_time,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'total_cost': 0.0  # Gemini API is currently free
                }
            }, 200
        
        except DeadlineExceeded as e:
            total_time = time.time() - start_time
            error_message = f"Deadline exceeded after {total_time:.2f}s: {str(e)}"
            print(f"Deadline exceeded in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            return {
                'error': error_message,
                'details': traceback.format_exc()
            }, 504  # Return 504 Gateway Timeout status
        except Exception as e:
            total_time = time.time() - start_time
            error_message = f"Error after {total_time:.2f}s: {str(e)}"
            print(f"Error in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            return {
                'error': error_message,
                'details': traceback.format_exc()
            }, 500
    except Exception as outer_error:
        print(f"Unexpected error in process_request: {str(outer_error)}")
        print(traceback.format_exc())
        return {
            'error': f"Unexpected error: {str(outer_error)}",
            'details': traceback.format_exc()
        }, 500

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
                
            # Process the request
            response_data, status_code = process_request(request_data)
            
            # Send the response
            if 200 <= status_code < 300:
                self._send_response(status_code, response_data)
            else:
                self._send_error_response(status_code, response_data.get('error', 'Unknown error'))
            
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
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    
    @app.route('/api/process-gemini', methods=['POST'])
    def process_gemini():
        try:
            # Get request data
            request_data = request.get_json()
            if not request_data:
                return jsonify({'error': 'Invalid or missing JSON data'}), 400
                
            # Process the request
            response_data, status_code = process_request(request_data)
            
            # Return the response
            return jsonify(response_data), status_code
            
        except Exception as e:
            print(f"Error in Flask route: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }), 500
            
except ImportError:
    print("Flask is not available, local development API will not be available")
