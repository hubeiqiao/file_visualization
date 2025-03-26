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

# Global constants for Gemini - Using reduced token limit to avoid timeouts
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested
GEMINI_MAX_OUTPUT_TOKENS = 8192  # Reduced from 65536 to avoid timeouts
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
    Optimized for Vercel Edge Functions.
    """
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    
    try:
        start_time = time.time()
        data = request_data
        
        if not data:
            return {"error": "No data provided"}, 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        content = data.get('content')
        format_prompt = data.get('format_prompt', '')
        
        # Use parameters optimized to avoid timeouts
        max_tokens = GEMINI_MAX_OUTPUT_TOKENS  # Using reduced token limit
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
        
        # Configure generation parameters with reduced token count for faster processing
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # Use a very small content size to avoid timeouts
        max_content_length = 2000 if os.environ.get('VERCEL') else 100000
        truncated_content = content[:max_content_length]
        
        # Add format prompt if provided
        if format_prompt:
            truncated_content = f"{truncated_content}\n\n{format_prompt}"
        
        # Prepare content
        contents = [
            {
                "role": "user",
                "parts": [{"text": truncated_content}]
            }
        ]
        
        # Check elapsed time and use quick generation if we're approaching timeout
        elapsed_time = time.time() - start_time
        print(f"Setup time before generation: {elapsed_time:.2f} seconds")
        
        # Skip the initial lightweight generation to save time
        # Directly go for the main generation with optimized parameters
        
        # Generate content with very conservative parameters for Vercel
        try:
            print("Generating content with Gemini model")
            generation_start_time = time.time()
            
            # For Vercel, use very conservative settings
            if os.environ.get('VERCEL'):
                # Even more reduced parameters for Vercel to avoid timeouts
                edge_config = {
                    "max_output_tokens": 4096,  # Drastically reduced for faster response
                    "temperature": temperature,
                    "top_p": GEMINI_TOP_P,
                    "top_k": GEMINI_TOP_K
                }
                
                response = model.generate_content(
                    contents,
                    generation_config=edge_config
                )
            else:
                # For local environment, use the standard configuration
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
            generation_time = end_time - generation_start_time
            total_time = end_time - start_time
            print(f"Generation completed in {generation_time:.2f} seconds (total: {total_time:.2f}s)")
            
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
        
        except DeadlineExceeded as e:
            error_message = str(e)
            print(f"Deadline exceeded in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            
            # Try with minimal parameters for extremely fast response
            try:
                print("Attempting generation with minimal parameters after timeout")
                # Use absolute minimum parameters
                fallback_config = {
                    "max_output_tokens": 1024,  # Extremely small for fastest response
                    "temperature": 0.7,  # Lower temperature for more focused responses
                    "top_p": 0.9,
                    "top_k": 40
                }
                
                # Use a simplified prompt to generate faster
                simplified_contents = [
                    {
                        "role": "user",
                        "parts": [{
                            "text": f"Create a simple HTML page for this content (keep it brief): {truncated_content[:500]}"
                        }]
                    }
                ]
                
                fallback_response = model.generate_content(
                    simplified_contents,
                    generation_config=fallback_config
                )
                
                # Extract content from fallback
                fallback_html = ""
                if hasattr(fallback_response, 'text'):
                    fallback_html = fallback_response.text
                elif hasattr(fallback_response, 'parts') and fallback_response.parts:
                    for part in fallback_response.parts:
                        if hasattr(part, 'text'):
                            fallback_html += part.text
                
                if fallback_html:
                    print("Successfully generated content with fallback parameters")
                    return {
                        'html': fallback_html,
                        'model': GEMINI_MODEL,
                        'warning': 'Generated with reduced parameters due to timeout',
                        'usage': {
                            'input_tokens': int(len(truncated_content.split()) * 1.3),
                            'output_tokens': int(len(fallback_html.split()) * 1.3),
                            'total_tokens': int(len(truncated_content.split()) * 1.3) + int(len(fallback_html.split()) * 1.3),
                            'total_cost': 0.0
                        }
                    }, 200
            except Exception as fallback_error:
                print(f"Fallback generation also failed: {str(fallback_error)}")
                # Continue to return the default fallback HTML
            
            # Return an extremely simple fallback HTML with the content 
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
                    <p class="mt-4 text-sm text-gray-500">Note: This is a fallback visualization as the model processing timed out.</p>
                </div>
            </body>
            </html>
            """
            
            return {
                'html': fallback_html,
                'model': 'fallback',
                'error': 'The Gemini API request took too long to complete. Fallback visualization provided.',
                'usage': {
                    'input_tokens': len(truncated_content.split()),
                    'output_tokens': 0,
                    'total_tokens': len(truncated_content.split()),
                    'total_cost': 0.0
                }
            }, 200
            
        except Exception as e:
            error_message = str(e)
            print(f"Error in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            
            # Return a basic fallback HTML in case of any error
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
                    <h1 class="text-2xl font-bold mb-4 text-red-600">Error Processing Content</h1>
                    <div class="prose">
                        <pre class="bg-gray-100 p-4 rounded overflow-auto">{truncated_content[:300]}...</pre>
                    </div>
                    <p class="mt-4 text-sm text-gray-500">Error: {error_message}</p>
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
