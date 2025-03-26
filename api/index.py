from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import sys
import os
import traceback

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
            api_key = data.get('api_key', '')  # We'll ignore this now
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            # Always use a simple word-based token estimation
            # This avoids any issues with the Anthropic client in Vercel
            word_count = len(content.split())
            # More accurate estimation factors for Claude 3.7
            if word_count > 0:
                # Most text averages 1.3 tokens per word
                estimated_tokens = int(word_count * 1.3)
            else:
                # Handle empty content
                estimated_tokens = 0
                
            # Calculate estimated cost (Claude 3.7 input pricing)
            estimated_cost = (estimated_tokens / 1000000) * 3.0
            
            # Define total context window for Claude 3.7
            TOTAL_CONTEXT_WINDOW = 200000
            
            # Return the estimated tokens and cost
            return jsonify({
                'estimated_tokens': estimated_tokens,
                'estimated_cost': round(estimated_cost, 6),
                'max_safe_output_tokens': min(128000, TOTAL_CONTEXT_WINDOW - estimated_tokens - 5000)
            })
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error in analyze_tokens_route: {str(e)}\n{traceback_str}")
            return jsonify({
                "error": f"Error analyzing tokens: {str(e)}",
                "traceback": traceback_str
            }), 500
    
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

# Create a debug API endpoint for Vercel
def handler(request):
    try:
        debug_info = {
            "python_version": sys.version,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir(),
            "environment": "Vercel" if os.environ.get("VERCEL") else "Local",
            "environment_vars": {k: v for k, v in os.environ.items() if not k.startswith("AWS_") and not "KEY" in k.upper() and not "SECRET" in k.upper()},
            "sys_path": sys.path,
            "status": "healthy"
        }
        
        # Try to import key packages
        package_status = {}
        try:
            import flask
            package_status["flask"] = str(flask.__version__)
        except Exception as e:
            package_status["flask"] = f"Error: {str(e)}"
        
        try:
            import flask_cors
            package_status["flask_cors"] = str(flask_cors.__version__)
        except Exception as e:
            package_status["flask_cors"] = f"Error: {str(e)}"
            
        try:
            import anthropic
            package_status["anthropic"] = str(anthropic.__version__)
        except Exception as e:
            package_status["anthropic"] = f"Error: {str(e)}"
            
        try:
            import google.generativeai
            package_status["google_generativeai"] = "Imported successfully"
        except Exception as e:
            package_status["google_generativeai"] = f"Error: {str(e)}"
            
        try:
            import pydantic
            package_status["pydantic"] = str(pydantic.__version__)
        except Exception as e:
            package_status["pydantic"] = f"Error: {str(e)}"
                
        debug_info["package_status"] = package_status
        
        return Response(
            response=str(debug_info),
            status=200,
            mimetype="text/plain"
        )
    except Exception as e:
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        return Response(
            response=str(error_info),
            status=500,
            mimetype="text/plain"
        )

# This allows the file to be run directly
if __name__ == "__main__":
    if 'app' in locals():
        app.run(debug=True) 