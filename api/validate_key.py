from http.server import BaseHTTPRequestHandler
import json

def validate_api_key(api_key):
    """Simple validation of API key format"""
    if not api_key:
        return False, "API key is required"
    if not api_key.startswith('sk-ant'):
        return False, "API key format is invalid. It should start with 'sk-ant'"
    return True, "API key format is valid"

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length).decode('utf-8')
            
            # Parse JSON
            data = json.loads(request_body) if request_body else {}
            api_key = data.get('api_key', '')
            
            # Validate API key
            is_valid, message = validate_api_key(api_key)
            
            # Set response headers
            self.send_response(200 if is_valid else 400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Send response
            response = json.dumps({
                'valid': is_valid,
                'message': message
            })
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            # Handle errors
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({
                'valid': False,
                'message': f'Error validating API key: {str(e)}'
            })
            self.wfile.write(response.encode('utf-8'))
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
        self.wfile.write(b'')

# This is the entry point for Vercel
def handler(request, response):
    # Create a handler instance
    h = Handler()
    
    # Set request attributes
    h.path = request.get('path', '')
    h.headers = request.get('headers', {})
    h.method = request.get('method', 'POST')
    
    # Handle the request based on method
    if h.method == 'OPTIONS':
        h.do_OPTIONS()
    else:
        h.do_POST()
    
    # Return a simple success response
    return {
        'statusCode': 200,
        'body': json.dumps({'success': True})
    } 