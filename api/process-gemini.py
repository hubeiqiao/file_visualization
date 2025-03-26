import os
import sys
import json
import traceback
import time

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from server import app
from helper_function import create_gemini_client, GEMINI_AVAILABLE
from flask import Flask, request, jsonify

# Global constants for Gemini
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested  # Make sure to use the latest model
GEMINI_MAX_OUTPUT_TOKENS = 128000
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64
GEMINI_TIMEOUT = 85  # Reduced from 300 to 85 seconds to work with Vercel's 90-second limit

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

def handler(request):
    """
    Process a file using the Google Gemini API and return HTML.
    """
    # Get the data from the request
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        content = data.get('content')
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
            generation_start_time = time.time()
            
            # Check if we're already close to the timeout
            elapsed_time = generation_start_time - start_time
            if elapsed_time > 5:  # If we've already used 5 seconds for setup
                print(f"Warning: {elapsed_time:.2f} seconds already elapsed before generation")
                # Adjust timeout to avoid Vercel timeout
                adjusted_timeout = max(60, GEMINI_TIMEOUT - elapsed_time - 5)  # 5 second buffer
            else:
                adjusted_timeout = GEMINI_TIMEOUT
                
            print(f"Using adjusted timeout of {adjusted_timeout:.2f} seconds")
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                timeout=adjusted_timeout
            )
            
            # Try to resolve the response first
            html_content = ""
            try:
                if hasattr(response, 'resolve'):
                    resolved = response.resolve()
                    if hasattr(resolved, 'text'):
                        html_content = resolved.text
                        print(f"Successfully resolved response: {len(html_content)} chars")
            except Exception as resolve_error:
                print(f"Error resolving response: {str(resolve_error)}")
            
            # If resolve didn't work, try other methods
            if not html_content:
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
                                if hasattr(candidate.content, 'parts'):
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
            
            # If we still don't have content, this is an error
            if not html_content:
                raise ValueError("Could not extract content from Gemini response")
            
            # Get usage stats (approximate since Gemini doesn't provide exact token counts)
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Log response
            print(f"Successfully generated HTML with Gemini in {total_time:.2f}s. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            # Return the response
            return jsonify({
                'html': html_content,
                'model': GEMINI_MODEL,
                'processing_time': total_time,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'total_cost': 0.0  # Gemini API is currently free
                }
            })
        
        except DeadlineExceeded as e:
            total_time = time.time() - start_time
            error_message = f"Deadline exceeded after {total_time:.2f}s: {str(e)}"
            print(f"Deadline exceeded in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            return jsonify({
                'error': error_message,
                'details': traceback.format_exc()
            }), 504  # Return 504 Gateway Timeout status
        except Exception as e:
            total_time = time.time() - start_time
            error_message = f"Error after {total_time:.2f}s: {str(e)}"
            print(f"Error in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            return jsonify({
                'error': error_message,
                'details': traceback.format_exc()
            }), 500
    
    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Server error after {total_time:.2f}s: {str(e)}"
        print(f"Error in /api/process-gemini: {error_message}")
        print(traceback.format_exc())
        return jsonify({
            'error': error_message,
            'details': traceback.format_exc()
        }), 500

@app.route('/', methods=['POST'])
def process_gemini():
    return handler(request) # Modified for Vercel deployment
# GEMINI TEST BRANCH: This branch is for testing Gemini integration
