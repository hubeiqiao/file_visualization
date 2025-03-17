from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import sys
import os
import traceback
import time
import uuid
import json

# Add the parent directory to the Python path so we can import from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from server.py
try:
    from server import app as flask_app, analyze_tokens
except Exception as e:
    # Create a simple app to show the import error
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        error_message = f"Error importing server.py: {str(e)}\n\nTraceback: {traceback.format_exc()}"
        return jsonify({"error": error_message}), 500
else:
    # For Vercel, we need to export the app properly
    app = flask_app
    
    # Add specific route for analyze-tokens to handle Vercel routing issues
    @app.route('/api/analyze-tokens', methods=['POST', 'OPTIONS'])
    def analyze_tokens_route():
        if request.method == 'OPTIONS':
            # Handle preflight requests
            response = app.make_default_options_response()
            response.headers.add('Access-Control-Allow-Methods', 'POST')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response
        
        # Get the data from the request
        try:
            # Import necessary functions
            import base64
            from flask import jsonify, request
            import os
            
            # Getting request data
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Get content from request
            content = data.get('content', '')
            file_type = data.get('file_type', 'txt')
            api_key = data.get('api_key', '')
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            # Forward to the analyze_tokens function
            result = analyze_tokens(content, file_type, api_key)
            return jsonify(result)
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error in analyze_tokens_route: {str(e)}\n{traceback_str}")
            return jsonify({
                "error": f"Error analyzing tokens: {str(e)}",
                "traceback": traceback_str
            }), 500
    
    # Add process-stream endpoint for Vercel
    @app.route('/api/process-stream', methods=['POST', 'OPTIONS'])
    def process_stream_route():
        if request.method == 'OPTIONS':
            # Handle preflight requests
            response = app.make_default_options_response()
            response.headers.add('Access-Control-Allow-Methods', 'POST')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response
            
        # Forward to the main process_stream function
        from server import process_stream
        return process_stream()
    
    # Add validate-key endpoint for Vercel
    @app.route('/api/validate-key', methods=['POST', 'OPTIONS'])
    def validate_key_route():
        if request.method == 'OPTIONS':
            # Handle preflight requests
            response = app.make_default_options_response()
            response.headers.add('Access-Control-Allow-Methods', 'POST')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response
            
        # Forward to the main validate_key function
        from server import validate_key
        return validate_key()
    
    # Add a catch-all error handler for debugging
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the stack trace
        traceback_str = traceback.format_exc()
        print(f"Unhandled exception: {str(e)}\n{traceback_str}")
        
        # Special handling for Anthropic client errors
        if "Anthropic" in str(e) and "proxies" in str(e):
            return jsonify({
                "error": "API key error: The current version of the Anthropic library is not compatible with this environment.",
                "detail": "Please try updating the library or contact the site administrator.",
                "traceback": traceback_str
            }), 500
        
        # Return JSON instead of HTML for HTTP errors
        return jsonify({
            "error": str(e),
            "traceback": traceback_str
        }), 500

    # Add diagnostic route to help troubleshoot Vercel environment issues
    @app.route('/api/diagnostics', methods=['GET'])
    def diagnostics():
        """Return information about the server environment for debugging."""
        try:
            import sys
            import platform
            import anthropic
            
            # Get environment variables (excluding sensitive data)
            env_vars = {k: v for k, v in os.environ.items() 
                       if not any(sensitive in k.lower() for sensitive in 
                                 ['key', 'secret', 'password', 'token', 'auth'])}
            
            # Check Anthropic library
            anthropic_version = getattr(anthropic, '__version__', 'unknown')
            anthropic_client_class = hasattr(anthropic, 'Client')
            anthropic_anthropic_class = hasattr(anthropic, 'Anthropic')
            
            return jsonify({
                'python_version': sys.version,
                'platform': platform.platform(),
                'is_vercel': bool(os.environ.get('VERCEL', False)),
                'anthropic_version': anthropic_version,
                'has_client_class': anthropic_client_class,
                'has_anthropic_class': anthropic_anthropic_class,
                'env_vars': env_vars
            })
        except Exception as e:
            import traceback
            return jsonify({
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500

# This allows the file to be run directly
if __name__ == "__main__":
    if 'app' in locals():
        app.run(debug=True)

# Create handler for Vercel serverless functions
def handler(environ, start_response):
    return flask_app(environ, start_response)

# Add explicit API routes for Vercel
@flask_app.route('/api/validate-key', methods=['POST'])
def validate_key():
    try:
        # Get API key from request
        data = request.get_json()
        if not data or 'api_key' not in data:
            return jsonify({"error": "Missing API key", "valid": False}), 400
        
        api_key = data['api_key']
        
        # Basic validation
        if not api_key.startswith('sk-'):
            return jsonify({"error": "Invalid API key format", "valid": False}), 400
        
        try:
            # Import inside function to avoid startup errors
            from anthropic import Anthropic
            
            # Initialize client
            client = Anthropic(api_key=api_key)
            
            # Test API key with a simple models list call
            try:
                models = client.models.list()
                return jsonify({
                    "valid": True,
                    "models": [model.id for model in models.data] if hasattr(models, 'data') else []
                })
            except Exception as e:
                # Handle API specific errors
                error_message = str(e)
                return jsonify({"error": error_message, "valid": False}), 400
                
        except ImportError:
            return jsonify({"error": "Failed to import Anthropic client", "valid": False}), 500
            
    except Exception as e:
        # Catch-all for any other errors
        return jsonify({"error": f"Error validating API key: {str(e)}", "valid": False}), 500

@flask_app.route('/api/analyze-tokens', methods=['POST'])
def analyze_tokens():
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        content = data.get('content', '')
        
        # Import here to avoid loading at module level
        from anthropic import Anthropic
        
        # Initialize the Anthropic client with the API key
        client = Anthropic(api_key=api_key)
        
        # Count tokens using Anthropic's API
        token_count = client.count_tokens(content)
        
        return jsonify({
            "token_count": token_count,
            "cost_estimate": token_count / 1000000 * 3.0, # $3 per million tokens for Claude
            "success": True
        })
    except Exception as e:
        error_message = str(e)
        return jsonify({
            "success": False,
            "error": f"Token analysis failed: {error_message}"
        })

@flask_app.route('/api/process-stream', methods=['POST'])
def process_stream():
    # Start time to track timeout
    start_time = time.time()
    MAX_EXECUTION_TIME = 50  # Leave some buffer before Vercel's 60s limit
    
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        # Check for both 'content' and 'source' parameters for compatibility
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')  # Fallback to 'source' if 'content' is empty
        
        # If both are empty, return an error
        if not content:
            return jsonify({"success": False, "error": "Source code or text is required"}), 400
            
        format_prompt = data.get('format_prompt', '')
        model = data.get('model', 'claude-3-7-sonnet-20250219')  # Using Claude 3.7
        max_tokens = int(data.get('max_tokens', 128000))
        temperature = float(data.get('temperature', 0.5))
        thinking_budget = int(data.get('thinking_budget', 32000))
        
        # Import necessary libraries
        from anthropic import Anthropic
        
        # Initialize the Anthropic client with the API key
        client = Anthropic(api_key=api_key)
        
        # Prepare system prompt and user content
        system_prompt = "I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.### Content Requirements* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.⠀Design Style* Follow a modern and minimalistic design inspired by Linear App.* Use a clear visual hierarchy to emphasize important content.* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.⠀Technical Specifications* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.* Implement a fully functional dark/light mode toggle, defaulting to the system setting.* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.⠀Responsive Design* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.* Optimize layout and typography for different screen sizes.* Ensure a smooth and intuitive touch experience on mobile devices.⠀Icons & Visual Elements* Use professional icon libraries like Font Awesome or Material Icons (via CDN).* Integrate illustrations or charts that best represent the content.* Avoid using emojis as primary icons.* Check if any icons cannot be loaded.⠀User Interaction & ExperienceEnhance the user experience with subtle micro-interactions:* Buttons should have slight enlargement and color transitions on hover.* Cards should feature soft shadows and border effects on hover.* Implement smooth scrolling effects throughout the page.* Content blocks should have an elegant fade-in animation on load.⠀Performance Optimization* Ensure fast page loading by avoiding large, unnecessary resources.* Use modern image formats (WebP) with proper compression.* Implement lazy loading for content-heavy pages.⠀Output Requirements* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.* Ensure the code meets W3C standards with no errors or warnings.* Maintain consistent design and functionality across different browsers.⠀Create the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.)."
        
        user_content = f"""
        {format_prompt}
        
        Here is the content to transform into a website:
        
        {content}
        """
        
        # Define a streaming response generator using beta stream for Claude 3.7
        def generate():
            # SSE headers
            yield "event: stream_start\n"
            yield f"data: {json.dumps({'message': 'Stream starting'})}\n\n"
            
            try:
                # Use Claude 3.7 with beta stream
                OUTPUT_128K_BETA = "output-128k-2025-02-19"
                
                with client.beta.messages.stream(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": user_content
                                }
                            ]
                        }
                    ],
                    thinking={
                        "type": "enabled",
                        "budget_tokens": thinking_budget
                    },
                    betas=[OUTPUT_128K_BETA],  # Using betas parameter instead of headers
                ) as stream:
                    message_id = str(uuid.uuid4())
                    generated_text = ""
                    
                    for chunk in stream:
                        # Check for timeout approaching
                        current_time = time.time()
                        if current_time - start_time > MAX_EXECUTION_TIME:
                            # Send a special timeout message with session info
                            timeout_msg = {
                                "type": "timeout",
                                "message": "Vercel timeout approaching, reconnect required",
                                "session_id": message_id,
                                "timestamp": current_time
                            }
                            yield f"data: {json.dumps(timeout_msg)}\n\n"
                            break
                            
                        # Handle thinking updates
                        if hasattr(chunk, "thinking") and chunk.thinking:
                            thinking_data = {
                                "type": "thinking_update",
                                "chunk_id": message_id,
                                "thinking": {
                                    "content": chunk.thinking.content if hasattr(chunk.thinking, "content") else "",
                                }
                            }
                            yield f"data: {json.dumps(thinking_data)}\n\n"
                            
                        # Handle content block deltas (the actual generated text)
                        if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                            content_data = {
                                "type": "content_block_delta",
                                "chunk_id": message_id,
                                "delta": {
                                    "text": chunk.delta.text
                                }
                            }
                            generated_text += chunk.delta.text
                            yield f"data: {json.dumps(content_data)}\n\n"
                    
                    # Message complete with usage stats
                    usage_data = None
                    if hasattr(stream, "usage"):
                        usage_data = {
                            "input_tokens": stream.usage.input_tokens if hasattr(stream.usage, "input_tokens") else 0,
                            "output_tokens": stream.usage.output_tokens if hasattr(stream.usage, "output_tokens") else 0,
                            "thinking_tokens": stream.usage.thinking_tokens if hasattr(stream.usage, "thinking_tokens") else 0
                        }
                            
                    complete_data = {
                        "type": "message_complete",
                        "message_id": message_id,
                        "chunk_id": message_id,
                        "usage": usage_data,
                        "html": generated_text
                    }
                    yield f"data: {json.dumps(complete_data)}\n\n"
                    
                    # End of stream event
                    yield "event: stream_end\n"
                    yield f"data: {json.dumps({'message': 'Stream complete'})}\n\n"
                    
            except Exception as e:
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        error_message = str(e)
        error_response = {
            "success": False,
            "error": f"Processing failed: {error_message}",
            "traceback": traceback.format_exc()
        }
        return jsonify(error_response)

# Keep the original /api/process endpoint for backward compatibility
@flask_app.route('/api/process', methods=['POST'])
def process():
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        # Check for both content and source parameters
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')
            
        # If both are empty, return an error
        if not content:
            return jsonify({"success": False, "error": "Source code or text is required"}), 400
            
        format_prompt = data.get('format_prompt', '')
        model = data.get('model', 'claude-3-7-sonnet-20250219')
        max_tokens = data.get('max_tokens', 100000)
        temperature = data.get('temperature', 0.5)
        thinking_budget = data.get('thinking_budget', 30)
        
        # Import here to avoid loading at module level
        from anthropic import Anthropic
        
        # Initialize the Anthropic client with the API key
        client = Anthropic(api_key=api_key)
        
        # Prepare system prompt and user message
        system_prompt = "I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.### Content Requirements* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.⠀Design Style* Follow a modern and minimalistic design inspired by Linear App.* Use a clear visual hierarchy to emphasize important content.* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.⠀Technical Specifications* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.* Implement a fully functional dark/light mode toggle, defaulting to the system setting.* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.⠀Responsive Design* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.* Optimize layout and typography for different screen sizes.* Ensure a smooth and intuitive touch experience on mobile devices.⠀Icons & Visual Elements* Use professional icon libraries like Font Awesome or Material Icons (via CDN).* Integrate illustrations or charts that best represent the content.* Avoid using emojis as primary icons.* Check if any icons cannot be loaded.⠀User Interaction & ExperienceEnhance the user experience with subtle micro-interactions:* Buttons should have slight enlargement and color transitions on hover.* Cards should feature soft shadows and border effects on hover.* Implement smooth scrolling effects throughout the page.* Content blocks should have an elegant fade-in animation on load.⠀Performance Optimization* Ensure fast page loading by avoiding large, unnecessary resources.* Use modern image formats (WebP) with proper compression.* Implement lazy loading for content-heavy pages.⠀Output Requirements* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.* Ensure the code meets W3C standards with no errors or warnings.* Maintain consistent design and functionality across different browsers.⠀Create the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.)."
        
        user_message = f"""
        {format_prompt}
        
        Here is the content to transform into a website:
        
        {content}
        """
        
        # Set up parameters with beta access for Claude 3.7
        OUTPUT_128K_BETA = "output-128k-2025-02-19"
        
        # Make the API call with beta parameters
        response = client.beta.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_message
                        }
                    ]
                }
            ],
            thinking={
                "type": "enabled",
                "budget_tokens": thinking_budget
            },
            betas=[OUTPUT_128K_BETA]
        )
        
        # Extract the content from the response
        html_content = ""
        if hasattr(response, 'content') and len(response.content) > 0:
            if hasattr(response.content[0], 'text'):
                html_content = response.content[0].text
        
        # Get usage stats
        usage_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0
        }
        
        if hasattr(response, 'usage'):
            if hasattr(response.usage, 'input_tokens'):
                usage_data["input_tokens"] = response.usage.input_tokens
            if hasattr(response.usage, 'output_tokens'):
                usage_data["output_tokens"] = response.usage.output_tokens
            if hasattr(response.usage, 'thinking_tokens'):
                usage_data["thinking_tokens"] = response.usage.thinking_tokens
        
        return jsonify({
            "html": html_content,
            "usage": usage_data,
            "success": True
        })
        
    except Exception as e:
        error_message = str(e)
        return jsonify({
            "success": False,
            "error": f"Processing failed: {error_message}"
        }) 