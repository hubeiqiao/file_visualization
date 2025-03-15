from flask import Flask, Response, jsonify
from flask_cors import CORS
import sys
import os
import traceback

# Add the parent directory to the Python path so we can import from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from server.py
try:
    from server import app as flask_app
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

# This allows the file to be run directly
if __name__ == "__main__":
    if 'app' in locals():
        app.run(debug=True) 