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

# Import helper functions but don't import server app
from helper_function import create_gemini_client, GEMINI_AVAILABLE

# Setting runtime configuration for Vercel Edge Functions
# This allows longer execution time and avoids timeout issues
VERCEL_EDGE = True

# Global constants for Gemini - Using exact model and parameters as specified
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit as specified
GEMINI_TEMPERATURE = 1.0  # Exact temperature as specified
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# GEMINI TEST BRANCH: This branch is for testing Gemini integration
# Keep all the optimizations for Vercel while maintaining the exact model parameters

# Try to import DeadlineExceeded exception
try:
    from google.api_core.exceptions import DeadlineExceeded
except ImportError:
    # Define a fallback if the import fails
    class DeadlineExceeded(Exception):
        pass

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

# Create a handler class compatible with Vercel
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            # Read request body
            request_body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(request_body)
            
            # Process request
            response_data, status_code = process_request(data)
            
            # Set response headers
            self.send_response(status_code)
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

def process_request(request_data):
    """
    Process a file using the Google Gemini API and return HTML.
    Compatible with the reference implementation.
    """
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    
    try:
        data = request_data
        
        if not data:
            return {"error": "No data provided"}, 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        content = data.get('content')
        format_prompt = data.get('format_prompt', '')
        
        # Use exactly the parameters from the reference implementation
        max_tokens = GEMINI_MAX_OUTPUT_TOKENS
        temperature = GEMINI_TEMPERATURE
        
        # Log request parameters (without sensitive data)
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content) if content else 0}")
        
        # Check if we have the required data
        if not api_key or not content:
            return {'error': 'API key and content are required'}, 400
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            return {
                'error': 'Google Generative AI package is not installed on the server.'
            }, 500
        
        # Use our helper function to create a Gemini client
        print(f"Creating Google Gemini client with API key: {api_key[:5]}...")
        client = create_gemini_client(api_key)
        
        # Get the model - use exactly the model from reference
        model = client.get_model(GEMINI_MODEL)
        
        # Configure generation parameters - use exactly the params from reference
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K,
            "response_mime_type": "text/plain"
        }
        
        # For compatibility with reference code, don't truncate too much
        max_content_length = 100000
        truncated_content = content[:max_content_length]
        
        # Add format prompt if provided
        if format_prompt:
            truncated_content = f"{truncated_content}\n\n{format_prompt}"
        
        # Prepare content in format matching reference implementation
        contents = [
            {
                "role": "user",
                "parts": [{"text": truncated_content}]
            }
        ]
        
        try:
            print("Generating content with Gemini model using reference parameters")
            start_time = time.time()
            
            # Generate content with reference parameters
            response = model.generate_content(
                contents,
                generation_config=generation_config
            )
            
            # Extract the content
            html_content = ""
            if hasattr(response, 'text'):
                html_content = response.text
            elif hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'text'):
                        html_content += part.text
            
            # Get usage stats (approximate since Gemini doesn't provide exact token counts)
            end_time = time.time()
            generation_time = end_time - start_time
            print(f"Generation completed in {generation_time:.2f} seconds")
            
            input_tokens = max(1, int(len(truncated_content.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Log response
            print(f"Successfully generated content with Gemini. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            # Return the response
            return {
                'html': html_content,
                'model': GEMINI_MODEL,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'total_cost': 0.0
                }
            }, 200
        
        except Exception as e:
            error_message = str(e)
            print(f"Error in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            
            # Return a simple fallback HTML with the content 
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
                    <p class="mt-4 text-sm text-gray-500">Note: This is a fallback visualization. Error: {error_message}</p>
                </div>
            </body>
            </html>
            """
            
            return {
                'html': fallback_html,
                'error': f'Server error: {error_message}',
                'details': traceback.format_exc()
            }, 200  # Return 200 with fallback HTML instead of 500
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in /api/process-gemini: {error_message}")
        print(traceback.format_exc())
        
        # Create a minimal fallback HTML that doesn't require API processing
        fallback_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error - Content Visualization</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-gray-100 p-4">
            <div class="container mx-auto bg-white p-6 rounded shadow">
                <h1 class="text-2xl font-bold mb-4 text-red-600">Server Error</h1>
                <p class="text-gray-700">We encountered an error processing your request.</p>
                <p class="mt-4 text-sm text-gray-500">Please try again with a smaller input or different content.</p>
            </div>
        </body>
        </html>
        """
        
        return {
            'html': fallback_html,
            'error': f'Server error: {error_message}',
            'details': traceback.format_exc()
        }, 200  # Return 200 with fallback HTML instead of 500

# For local Flask development, keep this code but don't expose it to Vercel
if 'FLASK_APP' in os.environ or not os.environ.get('VERCEL'):
    from server import app
    from flask import request, jsonify
    
    @app.route('/api/process-gemini', methods=['POST'])
    def process_gemini_endpoint():
        """Endpoint for local development with Flask."""
        try:
            data = request.get_json()
            response_data, status_code = process_request(data)
            return jsonify(response_data), status_code
        except Exception as e:
            return jsonify({
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }), 500
