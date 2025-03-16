from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
from helper_function import create_anthropic_client
import anthropic
import json
import os
import re
import time
# Updated import to be compatible with different versions of the Anthropic library
try:
    from anthropic.types import TextBlock, MessageParam
except ImportError:
    # Fallback for newer versions of the Anthropic library
    # where these classes might have different names or locations
    TextBlock = dict
    MessageParam = dict
import uuid
import PyPDF2
import docx
import io
import base64
import random 
import socket
import argparse
import sys

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Claude 3.7 has a total context window of 200,000 tokens (input + output combined)
# We'll use this constant when estimating token usage
TOTAL_CONTEXT_WINDOW = 200000

# Maximum allowed tokens for Claude API input (leaving room for output)
# This should be dynamically adjusted based on requested max_tokens
MAX_INPUT_TOKENS = 195000  # Setting a bit lower than the actual limit to account for system prompt and overhead

# Default settings
DEFAULT_MAX_TOKENS = 128000
DEFAULT_THINKING_BUDGET = 32000

# Define beta parameter for 128K output
OUTPUT_128K_BETA = "output-128k-2025-02-19"

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Read the file content
        file_content = file.read()
        # Convert the file content to base64
        base64_file_content = base64.b64encode(file_content).decode('utf-8')
        # Create a response object
        response = {
            "file_name": file.filename,
            "file_content": base64_file_content
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    if not data or 'file_name' not in data or 'file_content' not in data:
        return jsonify({"error": "Missing file_name or file_content"}), 400

    file_name = data['file_name']
    file_content = data['file_content']

    try:
        # Convert base64 string back to bytes
        file_content_bytes = base64.b64decode(file_content)
        # Create a temporary file to save the uploaded file
        temp_file_path = f"/tmp/{file_name}"
        with open(temp_file_path, 'wb') as f:
            f.write(file_content_bytes)

        # Process the file
        processed_file_path = process_file(temp_file_path)

        # Read the processed file content
        with open(processed_file_path, 'rb') as f:
            processed_file_content = f.read()
        # Convert the processed file content to base64
        base64_processed_file_content = base64.b64encode(processed_file_content).decode('utf-8')

        # Create a response object
        response = {
            "file_name": file_name,
            "file_content": base64_processed_file_content
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def process_file(file_path):
    # Placeholder for file processing logic
    # This function should be implemented to process the file based on its type
    # and return the processed file path
    return file_path  # Placeholder return, actual implementation needed

@app.route('/api/validate-key', methods=['POST'])
def validate_key():
    api_key = request.json.get('api_key')
    
    if not api_key or not api_key.strip():
        return jsonify({'valid': False, 'message': 'API key is required'}), 400
    
    # Validate API key format (basic pattern check)
    if not api_key.startswith(('sk-ant-', 'sk-')):
        return jsonify({'valid': False, 'message': 'Invalid API key format. Key should start with sk-ant- or sk-'}), 400
    
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    
    try:
        # Create client - we have special handling for Vercel in the create_anthropic_client function
        client = create_anthropic_client(api_key)
        
        # Try to make a minimal API call to verify the key
        try:
            # Check if this is our special Vercel-compatible client
            if hasattr(client, 'models') and not hasattr(client, 'beta'):
                client.models.list()
            # Normal client checks
            elif hasattr(client, 'models') and hasattr(client.models, 'list'):
                client.models.list()
            elif hasattr(client, 'get_models'):
                client.get_models()
            elif hasattr(client, 'count_tokens'):
                client.count_tokens("Test message")
            
            # If we get here, the key works
            return jsonify({'valid': True, 'message': 'API key is valid'})
                
        except Exception as api_e:
            error_str = str(api_e)
            print(f"API test error: {error_str}")
            
            # Check for authentication errors
            if any(phrase in error_str.lower() for phrase in ['auth', 'key', 'invalid', '401', 'unauthorized']):
                print(f"API authentication failed: {error_str}")
                return jsonify({
                    'valid': False, 
                    'message': f'API authentication failed: {error_str}'
                }), 400
            else:
                # For other errors, assume the key might be valid but there's an API issue
                print(f"API call failed but key format is valid: {error_str}")
                return jsonify({
                    'valid': True,
                    'message': 'API key format is valid, but API test call failed. The key may still work for generation.'
                })
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_str = str(e)
        print(f"API key validation error: {error_str}\n{error_traceback}")
        
        # More detailed error handling
        if "proxies" in error_str:
            # This is the issue we're specifically trying to fix for Vercel
            print(f"Proxies error detected: {error_str}")
            if is_vercel:
                return jsonify({
                    'valid': False, 
                    'message': 'Unable to validate API key in this environment. Try using the key directly for generation.'
                }), 400
            else:
                return jsonify({
                    'valid': False, 
                    'message': 'API client configuration error. Please try using a newer Anthropic API key format.'
                }), 400
        else:
            return jsonify({
                'valid': False, 
                'message': f'Error validating API key: {error_str}'
            }), 400

@app.route('/api/process', methods=['POST'])
def process_file():
    # Get request parameters
    api_key = request.json.get('api_key')
    content = request.json.get('content')
    file_type = request.json.get('file_type', 'txt')  # Default to txt if not specified
    system_prompt = request.json.get('system_prompt')
    additional_prompt = request.json.get('additional_prompt', '')
    temperature = float(request.json.get('temperature', 1.0))
    max_tokens = int(request.json.get('max_tokens', DEFAULT_MAX_TOKENS))
    thinking_budget = int(request.json.get('thinking_budget', DEFAULT_THINKING_BUDGET))
    
    if not api_key or not content:
        return jsonify({'error': 'API key and content are required'}), 400
    
    try:
        # Use our helper function to create a compatible client
        client = create_anthropic_client(api_key)
        
        # Prepare user message with content and additional prompt
        user_content = content
        if additional_prompt:
            user_content = f"{additional_prompt}\n\nHere's the file content:\n\n{content}"
        
        # Define generate function for streaming
        def generate():
            input_tokens = 0
            output_tokens = 0
            thinking_tokens = 0
            start_time = time.time()
            
            # Define retry parameters
            max_retries = 5
            base_delay = 1  # Base delay in seconds
            
            for retry_attempt in range(max_retries + 1):
                try:
                    # Try to use streaming API with thinking enabled
                    try:
                        # Try the beta.messages.stream approach first (newer API)
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
                            betas=[OUTPUT_128K_BETA],
                        ) as stream:
                            # Stream the response
                            html_content = ""
                            
                            # Track thinking and response state
                            thinking_active = False
                            thinking_content = ""
                            response_html = ""
                            
                            for chunk in stream:
                                if hasattr(chunk, 'type') and chunk.type == 'thinking_start':
                                    thinking_active = True
                                    yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                                    
                                elif hasattr(chunk, 'type') and chunk.type == 'thinking_update':
                                    if hasattr(chunk, 'thinking') and hasattr(chunk.thinking, 'content'):
                                        thinking_content = chunk.thinking.content
                                        yield f"data: {json.dumps({'type': 'thinking_update', 'content': thinking_content})}\n\n"
                                    
                                elif hasattr(chunk, 'type') and chunk.type == 'thinking_end':
                                    thinking_active = False
                                    yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                                    
                                elif hasattr(chunk, 'type') and chunk.type == 'message_delta':
                                    # Get delta content
                                    delta_content = ""
                                    if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'content'):
                                        # Access content based on its structure
                                        if isinstance(chunk.delta.content, list):
                                            for item in chunk.delta.content:
                                                if hasattr(item, 'text'):
                                                    delta_content += item.text
                                                elif isinstance(item, dict) and 'text' in item:
                                                    delta_content += item['text']
                                        elif hasattr(chunk.delta.content, 'text'):
                                            delta_content = chunk.delta.content.text
                                        elif isinstance(chunk.delta.content, str):
                                            delta_content = chunk.delta.content
                                    
                                    # Add to HTML content
                                    html_content += delta_content
                                    response_html += delta_content
                                    
                                    # Stream the delta
                                    yield f"data: {json.dumps({'type': 'content', 'content': delta_content})}\n\n"
                            
                            # Get usage statistics at the end
                            if hasattr(stream, 'usage'):
                                input_tokens = getattr(stream.usage, 'input_tokens', 0)
                                output_tokens = getattr(stream.usage, 'output_tokens', 0)
                                thinking_tokens = 0
                                
                                # Try to get thinking tokens from different possible paths
                                if hasattr(stream.usage, 'thinking_tokens'):
                                    thinking_tokens = stream.usage.thinking_tokens
                                elif hasattr(stream.usage, 'thinking') and hasattr(stream.usage.thinking, 'tokens'):
                                    thinking_tokens = stream.usage.thinking.tokens
                                elif hasattr(stream.usage, 'thinking') and isinstance(stream.usage.thinking, int):
                                    thinking_tokens = stream.usage.thinking
                            else:
                                # Fallback estimation if usage data not available
                                input_tokens = len(user_content.split()) * 1.3  # Rough estimate
                                output_tokens = len(html_content.split()) * 1.3  # Rough estimate
                                thinking_tokens = thinking_budget / 2  # Rough estimate
                            
                            # Calculate total cost
                            input_cost = (input_tokens / 1000000) * 3  # $3 per million tokens
                            output_cost = (output_tokens / 1000000) * 15  # $15 per million tokens
                            thinking_cost = (thinking_tokens / 1000000) * 3  # $3 per million tokens
                            total_cost = input_cost + output_cost + thinking_cost
                            
                            # Send completion message with usage data
                            yield f"data: {json.dumps({'type': 'complete', 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'thinking_tokens': thinking_tokens, 'total_cost': total_cost}})}\n\n"
                    
                    except (AttributeError, TypeError) as e:
                        # Fallback to non-streaming API for older versions
                        print(f"Streaming API failed, falling back to non-streaming: {str(e)}")
                        yield f"data: {json.dumps({'type': 'info', 'message': 'Using non-streaming mode (older API version)'})}\n\n"
                        
                        # Try non-streaming API call
                        response = client.messages.create(
                            model="claude-3-7-sonnet-20250219",
                            max_tokens=max_tokens,
                            temperature=temperature,
                            system=system_prompt,
                            messages=[
                                {
                                    "role": "user",
                                    "content": user_content
                                }
                            ]
                        )
                        
                        # Extract content
                        html_content = ""
                        if hasattr(response, 'content'):
                            if isinstance(response.content, list):
                                for item in response.content:
                                    if hasattr(item, 'text'):
                                        html_content += item.text
                                    elif isinstance(item, dict) and 'text' in item:
                                        html_content += item['text']
                            elif hasattr(response.content, 'text'):
                                html_content = response.content.text
                            elif isinstance(response.content, str):
                                html_content = response.content
                        
                        # Send the entire content at once
                        yield f"data: {json.dumps({'type': 'content', 'content': html_content})}\n\n"
                        
                        # Get usage statistics
                        if hasattr(response, 'usage'):
                            input_tokens = getattr(response.usage, 'input_tokens', 0)
                            output_tokens = getattr(response.usage, 'output_tokens', 0)
                            thinking_tokens = 0
                        else:
                            # Fallback estimation if usage data not available
                            input_tokens = len(user_content.split()) * 1.3  # Rough estimate
                            output_tokens = len(html_content.split()) * 1.3  # Rough estimate
                            thinking_tokens = 0  # No thinking in non-streaming mode
                        
                        # Calculate total cost
                        input_cost = (input_tokens / 1000000) * 3  # $3 per million tokens
                        output_cost = (output_tokens / 1000000) * 15  # $15 per million tokens
                        thinking_cost = (thinking_tokens / 1000000) * 3  # $3 per million tokens
                        total_cost = input_cost + output_cost + thinking_cost
                        
                        # Send completion message with usage data
                        yield f"data: {json.dumps({'type': 'complete', 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'thinking_tokens': thinking_tokens, 'total_cost': total_cost}})}\n\n"
                    
                    # If we get here, we have successfully processed the request
                    break
                    
                except Exception as e:
                    error_message = str(e)
                    error_data = {}
                    
                    # Try to parse the error message if it's a JSON string
                    if "{" in error_message and "}" in error_message:
                        try:
                            error_json = error_message[error_message.find("{"):error_message.rfind("}")+1]
                            error_data = json.loads(error_json)
                        except:
                            pass
                    
                    # Check for overloaded error
                    if "Overloaded" in error_message or (error_data and error_data.get('error', {}).get('type') == 'overloaded_error') or error_message.startswith("Status code 529"):
                        # If it's not the last retry, implement exponential backoff
                        if retry_attempt < max_retries:
                            # Calculate delay with jitter
                            delay = base_delay * (2 ** retry_attempt) + random.uniform(0, 0.5)
                            print(f"Anthropic API overloaded. Retrying in {delay:.2f} seconds (attempt {retry_attempt + 1}/{max_retries})...")
                            
                            # Send a message to the client about the retry
                            yield f"data: {json.dumps({'type': 'info', 'message': f'Service is busy. Retrying in {int(delay)} seconds (attempt {retry_attempt + 1}/{max_retries})...'})}\n\n"
                            
                            time.sleep(delay)
                            continue
                    
                    # If we're here, either it's not an overloaded error or we've exhausted retries
                    print(f"Error in API call: {error_message}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'API call failed: {error_message}'})}\n\n"
                    break
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# PDF text extraction function
def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

# Word document text extraction function        
def extract_text_from_docx(docx_file):
    doc = docx.Document(io.BytesIO(docx_file))
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

@app.route('/api/analyze-tokens', methods=['POST'])
def analyze_tokens():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get content from request
        content = data.get('content', '')
        file_type = data.get('file_type', 'txt')
        api_key = data.get('api_key', '')  # Get API key if available
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        # Handle binary content (base64 encoded) for PDFs and documents
        try:
            if file_type in ['pdf', 'doc', 'docx']:
                # Try to decode base64 if it looks like base64
                try:
                    # Decode base64 to binary
                    binary_content = base64.b64decode(content)
                    
                    # Extract text based on file type
                    if file_type == 'pdf':
                        text_content = extract_text_from_pdf(binary_content)
                    elif file_type in ['doc', 'docx']:
                        text_content = extract_text_from_docx(binary_content)
                    else:
                        text_content = binary_content.decode('utf-8', errors='ignore')
                    
                    # Use the extracted text for analysis
                    content = text_content
                except Exception as e:
                    # Fall back to the original content if decoding fails
                    pass
            
            # Try to get a more accurate token count using the Anthropic API if API key is provided
            if api_key:
                try:
                    client = create_anthropic_client(api_key)
                    try:
                        # Try newer API version first (Anthropic v0.5+)
                        token_count = client.count_tokens(content)
                        estimated_tokens = token_count
                    except (AttributeError, TypeError):
                        try:
                            # Fall back to older API style if needed
                            token_count = client.count_tokens(content)
                            estimated_tokens = token_count
                        except Exception:
                            # If API token counting fails, fall back to estimation
                            word_count = len(content.split())
                            estimated_tokens = int(word_count * 1.3)
                except Exception as e:
                    # Fall back to word-based estimation if API fails
                    word_count = len(content.split())
                    estimated_tokens = int(word_count * 1.3)
            else:
                # No API key, use simple word-based estimation
                word_count = len(content.split())
                estimated_tokens = int(word_count * 1.3)
                
        except Exception as e:
            # Fall back to direct estimation
            word_count = len(content.split())
            estimated_tokens = int(word_count * 1.3)
        
        # Calculate estimated cost (as of current pricing)
        estimated_cost = (estimated_tokens / 1000000) * 3.0  # $3 per million tokens
        
        return jsonify({
            'estimated_tokens': estimated_tokens,
            'estimated_cost': round(estimated_cost, 6),
            'max_safe_output_tokens': min(128000, TOTAL_CONTEXT_WINDOW - estimated_tokens - 5000)
        })
    except Exception as e:
        return jsonify({"error": f"Error analyzing tokens: {str(e)}"}), 500

@app.route('/api/process-stream', methods=['POST'])
def process_stream():
    print("==== API PROCESS STREAM REQUEST RECEIVED ====")
    data = request.get_json()
    if not data:
        print("ERROR: No data provided in process-stream request")
        return jsonify({"error": "No data provided"}), 400
    
    # Get required data from request
    api_key = data.get('api_key')
    source = data.get('source', '')
    format_prompt = data.get('format_prompt', '')
    model = data.get('model', 'claude-3-7-sonnet-20250219')
    max_tokens = int(data.get('max_tokens', 128000))
    temperature = float(data.get('temperature', 1.0))
    thinking_budget = int(data.get('thinking_budget', 32000))
    session_id = data.get('session_id')  # For reconnections
    
    # Check if API key is provided
    if not api_key:
        print("ERROR: API key is missing in process-stream request")
        return jsonify({"error": "API key is required"}), 400
    
    # Check if source is provided
    if not source:
        print("ERROR: Source content is missing in process-stream request")
        return jsonify({"error": "Source code or text is required"}), 400
    
    print(f"Process stream request: model={model}, max_tokens={max_tokens}, source_length={len(source)}")
    
    # Check if this is a reconnection request
    is_reconnection = bool(session_id)
    if is_reconnection:
        print(f"This is a reconnection request with session_id: {session_id}")
    
    # Check if we're running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    if is_vercel:
        print("Running in Vercel environment")
    else:
        print("Running in local environment")
    
    try:
        # Create the Anthropic client
        print("Creating Anthropic client")
        client = create_anthropic_client(api_key)
        print("Anthropic client created successfully")
        
        # Set up a streaming response
        def generate():
            print("Starting generate function for streaming response")
            try:
                system_prompt = """You are an expert web developer and technical communicator.
Your task is to transform the provided content into a beautiful, readable HTML document.
Make the output visually appealing and well-structured for maximum readability.
                
Create a COMPLETE and SELF-CONTAINED HTML document that:
- Includes proper HTML5 doctype, head, meta tags, and body
- Has all CSS styles embedded directly in a <style> tag in the head
- Applies a clean, modern design that's easy to read
- Preserves code formatting with syntax highlighting where appropriate
- Renders mathematical notation properly if present
- Includes responsive design principles for mobile and desktop viewing
- Does NOT rely on any external CSS, JS, or image files
"""
                
                if format_prompt:
                    system_prompt += f"\n\nAdditional formatting instructions:\n{format_prompt}"
                
                # Define the messages
                messages = [
                    {"role": "user", "content": f"Please transform this content into a beautiful HTML page with CSS styling:\n\n{source}"}
                ]
                
                # Set up beta parameters for large output
                betas = ["output-128k-2025-02-19"]
                
                # Stream the response
                with client.beta.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    thinking={"enable": True, "max_tokens": thinking_budget},
                    betas=betas
                ) as stream:
                    # First, indicate the start of the streaming process
                    yield 'data: {"type": "start"}\n\n'
                    
                    # Stream the thinking response first
                    thinking_content = ""
                    for chunk in stream:
                        # Handle different types of response chunks
                        if chunk.type == 'thinking_start':
                            yield 'data: {"type": "thinking_start"}\n\n'
                        
                        elif chunk.type == 'thinking_update':
                            # Append thinking content
                            thinking_fragment = chunk.thinking.content
                            thinking_content += thinking_fragment
                            
                            # Stream thinking update
                            yield f'data: {{"type": "thinking_update", "content": {json.dumps(thinking_fragment)}}}\n\n'
                        
                        elif chunk.type == 'thinking_end':
                            yield 'data: {"type": "thinking_end"}\n\n'
                        
                        elif chunk.type == 'content_block_delta':
                            # For content, we stream HTML content
                            text_fragment = chunk.delta.text
                            
                            # Stream content update
                            yield f'data: {{"type": "content", "text": {json.dumps(text_fragment)}}}\n\n'
                            
                        elif chunk.type == 'error':
                            # Handle errors from our custom wrapper
                            error_msg = chunk.error
                            yield f'data: {{"type": "error", "error": {json.dumps(error_msg)}}}\n\n'
                            
                        elif chunk.type == 'reconnect_signal':
                            # Handle reconnection signals from our wrapper
                            session_id = chunk.session_id
                            chunk_count = chunk.chunk_count
                            yield f'data: {{"type": "reconnect", "session_id": "{session_id}", "chunk_count": {chunk_count}}}\n\n'
                            return  # End this stream to allow client to reconnect
                    
                    # When we're done, include the usage information
                    if stream.usage:
                        usage_data = {
                            'input_tokens': stream.usage.input_tokens,
                            'output_tokens': stream.usage.output_tokens,
                            'thinking_tokens': stream.usage.thinking_tokens,
                            'total_tokens': stream.usage.input_tokens + stream.usage.output_tokens + stream.usage.thinking_tokens
                        }
                        yield f'data: {{"type": "usage", "usage": {json.dumps(usage_data)}}}\n\n'
                    
                    # Signal the end of the stream
                    yield 'data: {"type": "end"}\n\n'
            
            except Exception as e:
                # Handle errors
                error_msg = str(e)
                print(f"Error in generate: {error_msg}")
                
                # Check if this is a timeout that requires client reconnection
                if is_vercel and "Vercel timeout - client should continue with session" in error_msg:
                    session_id = error_msg.split("session: ")[1]
                    yield f'data: {{"type": "reconnect", "session_id": "{session_id}", "error": "Vercel timeout"}}\n\n'
                else:
                    yield f'data: {{"type": "error", "error": {json.dumps(error_msg)}}}\n\n'
        
        # Return the streaming response
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        # Handle outer exceptions
        error_msg = str(e)
        print(f"Error in process_stream: {error_msg}")
        return jsonify({"error": f"Error processing request: {error_msg}"}), 500

# Add a simple test endpoint
@app.route('/api/test', methods=['GET', 'POST'])
def test_api():
    """Simple test endpoint to verify API connectivity"""
    if request.method == 'POST':
        data = request.get_json() or {}
        return jsonify({
            "status": "success", 
            "message": "API test endpoint is working",
            "received_data": data,
            "timestamp": time.time()
        })
    else:
        return jsonify({
            "status": "success", 
            "message": "API test endpoint is working", 
            "timestamp": time.time()
        })

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the Claude 3.7 File Visualizer server')
    parser.add_argument('--port', type=int, help='Port to run the server on')
    args = parser.parse_args()
    
    # Determine the port to use (priority: command-line arg > environment var > default)
    port = args.port or int(os.environ.get('PORT', 5001))
    
    print("Claude 3.7 File Visualizer starting...")
    
    # Check if the port is available
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('localhost', port))
        s.close()
    except socket.error:
        print(f"Port {port} is in use. Try using:")
        print(f"  python server.py --port={port+1}")
        print(f"  # or")
        print(f"  PORT={port+1} python server.py")
        print(f"  # or")
        print(f"  lsof -i :{port} | awk 'NR>1 {{print $2}}' | xargs kill -9 # to kill process using port {port}")
        sys.exit(1)
    
    # Start the server
    print(f"Server running at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)

# Important: Export the Flask app for Vercel
app