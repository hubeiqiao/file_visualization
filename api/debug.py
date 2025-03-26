import sys
import os
import json
import traceback

def handler(event, context):
    """A simple debug endpoint that returns information about the serverless environment."""
    try:
        # Gather debug information
        debug_info = {
            "python_version": sys.version,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir(),
            "environment": "Vercel" if os.environ.get("VERCEL") else "Local",
            "environment_vars": {k: v for k, v in os.environ.items() 
                               if not k.startswith("AWS_") 
                               and not "KEY" in k.upper() 
                               and not "SECRET" in k.upper()},
            "sys_path": sys.path,
            "status": "healthy",
            "event": event
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
                
        debug_info["package_status"] = package_status
        
        # Return successful response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(debug_info)
        }
    except Exception as e:
        # Return error information
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(error_info)
        } 