from flask import Flask, request, jsonify
import os
import sys
import json
import traceback
import time

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Constants
GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_MAX_OUTPUT_TOKENS = 128000
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# Import helper functions
try:
    from helper_function import create_gemini_client
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Google Generative AI module is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI module is not installed")

# System instruction
SYSTEM_INSTRUCTION = """
You are a web developer specialized in converting content into beautiful, accessible, responsive HTML with modern CSS.
Generate a single-page website from the given content.
"""

# Initialize Flask app
app = Flask(__name__)

def handler(request):
    """
    Process a file using the Google Gemini API and return HTML.
    """
    # Get the data from the request
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        content = data.get('content', '')
        format_prompt = data.get('format_prompt', '')
        max_tokens = int(data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(data.get('temperature', GEMINI_TEMPERATURE))
        
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content) if content else 0}")
        
        # Check if we have the required data
        if not api_key or not content:
            return jsonify({'error': 'API key and content are required'}), 400
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            return jsonify({
                'error': 'Google Generative AI package is not installed on the server.'
            }), 500
        
        # Use our helper function to create a Gemini client
        client = create_gemini_client(api_key)
        
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
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract the HTML from the response using multiple methods
            html_content = ""
            
            try:
                # Try standard text attribute first
                if hasattr(response, 'text'):
                    html_content = response.text
                    print(f"Extracted content from text attribute: {len(html_content)} chars")
                # Then try parts
                elif hasattr(response, 'parts') and response.parts:
                    for part in response.parts:
                        if hasattr(part, 'text'):
                            html_content += part.text
                    print(f"Extracted content from parts: {len(html_content)} chars")
                # Then check candidates
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        html_content += part.text
                    print(f"Extracted content from candidates: {len(html_content)} chars")
                else:
                    # Last resort: try string conversion
                    html_content = str(response)
                    print(f"Extracted content using string conversion: {len(html_content)} chars")
            except Exception as extract_error:
                print(f"Error extracting content: {str(extract_error)}")
                # Try the resolve method as a fallback
                try:
                    if hasattr(response, 'resolve'):
                        resolved = response.resolve()
                        if hasattr(resolved, 'text'):
                            html_content = resolved.text
                            print(f"Extracted content through resolve: {len(html_content)} chars")
                except Exception as resolve_error:
                    print(f"Error resolving response: {str(resolve_error)}")
            
            # If we still don't have content, this is an error
            if not html_content:
                raise ValueError("Could not extract content from Gemini response")
            
            # Get usage stats (approximate since Gemini doesn't provide exact token counts)
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Log response
            print(f"Successfully generated HTML with Gemini. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            # Return the response
            return jsonify({
                'html': html_content,
                'model': GEMINI_MODEL,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'total_cost': 0.0  # Gemini API is currently free
                }
            })
        
        except Exception as e:
            error_message = str(e)
            print(f"Error in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            return jsonify({
                'error': f'Server error: {error_message}',
                'details': traceback.format_exc()
            }), 500
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in /api/process-gemini: {error_message}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Server error: {error_message}',
            'details': traceback.format_exc()
        }), 500

@app.route('/api/process-gemini', methods=['POST'])
def process_gemini():
    """
    Process a request using Google Gemini API (non-streaming version).
    """
    try:
        # Get the request data
        data = request.get_json()
        
        # Extract the API key and content
        api_key = data.get('api_key')
        
        # Check for both 'content' and 'source' parameters for compatibility
        content = data.get('content', '')
        if not content:
            content = data.get('source', '')  # Fallback to 'source' if 'content' is empty
        
        # If neither content nor source is provided, return an error
        if not content:
            return jsonify({"success": False, "error": "Source code or text is required"}), 400
        
        # Extract other parameters with defaults
        format_prompt = data.get('format_prompt', '')
        max_tokens = int(data.get('max_tokens', GEMINI_MAX_OUTPUT_TOKENS))
        temperature = float(data.get('temperature', GEMINI_TEMPERATURE))
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Google Generative AI is not available on this server.",
                "details": "Please install the package with: pip install google-generativeai"
            }), 500
        
        # Create Gemini client
        try:
            client = create_gemini_client(api_key)
            print(f"Created Gemini client with API key: {api_key[:4]}...")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"API key validation failed: {str(e)}"
            }), 400
        
        # Prepare the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{content[:100000]}
"""
        
        if format_prompt:
            prompt += f"\n\n{format_prompt}"
        
        print(f"Prepared prompt for Gemini with length: {len(prompt)}")
        
        # Start timing the request
        start_time = time.time()
        
        try:
            # Get the model
            model = client.get_model(GEMINI_MODEL)
            
            # Set up generation config
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                "top_p": GEMINI_TOP_P,
                "top_k": GEMINI_TOP_K
            }
            
            # Generate content
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract the content
            html_content = ""
            
            # Try multiple methods to extract text from the response
            try:
                if hasattr(response, 'text'):
                    html_content = response.text
                    print(f"Extracted text from 'text' attribute: {len(html_content)} chars")
                elif hasattr(response, 'parts') and response.parts:
                    html_content = response.parts[0].text
                    print(f"Extracted text from 'parts' attribute: {len(html_content)} chars")
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        html_content += part.text
                    print(f"Extracted text from 'candidates' attribute: {len(html_content)} chars")
                else:
                    # Last resort: convert the entire response to string
                    html_content = str(response)
                    print(f"Extracted text using string conversion: {len(html_content)} chars")
            except Exception as text_error:
                print(f"Error extracting text: {str(text_error)}")
                try:
                    if hasattr(response, 'resolve'):
                        resolved = response.resolve()
                        if hasattr(resolved, 'text'):
                            html_content = resolved.text
                            print(f"Extracted text through resolve: {len(html_content)} chars")
                        elif hasattr(resolved, 'parts') and resolved.parts:
                            html_content = resolved.parts[0].text
                            print(f"Extracted text through resolve: {len(html_content)} chars")
                except Exception as resolve_error:
                    print(f"Error resolving response: {str(resolve_error)}")
            
            # Log length of content
            print(f"Extracted content length: {len(html_content)}")
            
            # If no content was extracted, raise an error
            if not html_content:
                raise ValueError("Could not extract content from Gemini response")
            
            # Calculate time taken
            end_time = time.time()
            time_taken = end_time - start_time
            
            # Calculate tokens used (approximate)
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            total_tokens = input_tokens + output_tokens
            
            # Return the result
            return jsonify({
                "success": True,
                "html": html_content,
                "stats": {
                    "time_taken": time_taken,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                }
            })
            
        except Exception as generate_error:
            error_message = str(generate_error)
            print(f"Error generating content: {error_message}")
            print(traceback.format_exc())
            
            return jsonify({
                "success": False,
                "error": f"Generation error: {error_message}",
                "details": traceback.format_exc()
            }), 500
            
    except Exception as request_error:
        error_message = str(request_error)
        print(f"Request error: {error_message}")
        print(traceback.format_exc())
        
        return jsonify({
            "success": False,
            "error": f"Request error: {error_message}",
            "details": traceback.format_exc()
        }), 500 