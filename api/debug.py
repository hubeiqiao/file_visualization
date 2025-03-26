from http.server import BaseHTTPRequestHandler
import sys
import os
import traceback
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(debug_info, indent=2, default=str).encode('utf-8'))
            
        except Exception as e:
            error_info = {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_info, indent=2).encode('utf-8')) 