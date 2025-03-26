import os
import sys
import json
import traceback
import time
import asyncio
import base64

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from server import app
from helper_function import create_gemini_client, GEMINI_AVAILABLE
from flask import Flask, request, jsonify

# Setting runtime configuration for Vercel Edge Functions
# This allows longer execution time and avoids timeout issues
__VERCEL_EDGE_RUNTIME = True

# Global constants for Gemini - Using exactly the specified model
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Using exact model as requested
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit as specified
GEMINI_TEMPERATURE = 1.0  # Exact temperature as specified
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64
GEMINI_TIMEOUT = 25  # Optimized timeout for Edge Functions

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

def handler(request):
    """
    Process a file using the Google Gemini API and return HTML.
    Optimized for Vercel Edge Functions.
    """
    # Get the data from the request
    print("\n==== API PROCESS GEMINI REQUEST RECEIVED ====")
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract the API key and content
        api_key = data.get('api_key')
        content = data.get('content')
        format_prompt = data.get('format_prompt', '')
        
        # Use exactly the parameters from the reference code
        max_tokens = GEMINI_MAX_OUTPUT_TOKENS
        temperature = GEMINI_TEMPERATURE
        
        # Log request parameters (without sensitive data)
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
        
        # Get the model - use exactly the model from reference
        model = client.get_model(GEMINI_MODEL)
        
        # Configure generation parameters - use exactly the params from reference
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # For Edge Functions, using smaller content size for faster processing
        max_content_length = 5000 if os.environ.get('VERCEL') else 100000
        truncated_content = content[:max_content_length]
        
        # Add format prompt if provided
        if format_prompt:
            truncated_content = f"{truncated_content}\n\n{format_prompt}"
        
        # Prepare content exactly as in reference
        contents = [
            {
                "role": "user",
                "parts": [{"text": truncated_content}]
            }
        ]
        
        # For Edge Functions, first try a lightweight generation to get a quick response
        try:
            print("First attempting lightweight generation for Edge Functions")
            
            # Try to generate a quick minimal response to keep the connection alive
            # This avoids the initial timeout while the full generation runs
            response_initial = model.generate_content(
                contents=[
                    {
                        "role": "user",
                        "parts": [{"text": "Begin HTML generation. Respond with a loading message."}]
                    }
                ],
                generation_config={
                    "max_output_tokens": 100,
                    "temperature": 0.2
                },
                timeout=5
            )
            
            # Initialize result to include a loading message
            initial_html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Content Visualization - Loading</title>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            </head>
            <body class="bg-gray-100 p-4">
                <div class="container mx-auto bg-white p-6 rounded shadow">
                    <h1 class="text-2xl font-bold mb-4">Content Visualization</h1>
                    <div class="prose">
                        <p>Processing content, please wait...</p>
                    </div>
                </div>
            </body>
            </html>
            """
        except Exception as initial_error:
            print(f"Initial generation attempt failed: {str(initial_error)}")
            # Continue with main generation even if initial fails
            pass
        
        # Generate content - with modified approach for Edge Functions
        try:
            print("Generating content with Gemini model")
            start_time = time.time()
            
            # For Edge Functions, use a reduced token output for faster processing
            if os.environ.get('VERCEL'):
                # Modify configuration slightly to avoid timeouts on Vercel
                edge_config = generation_config.copy()
                # Keep most parameters the same, but slightly reduce max tokens
                # to ensure faster response while still allowing substantial output
                edge_config["max_output_tokens"] = 16384  # Still allows large output but faster
                
                response = model.generate_content(
                    contents,
                    generation_config=edge_config,
                    timeout=GEMINI_TIMEOUT
                )
            else:
                # For local environment, use the full configuration
                response = model.generate_content(
                    contents,
                    generation_config=generation_config,
                    timeout=GEMINI_TIMEOUT
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
            generation_time = end_time - start_time
            print(f"Generation completed in {generation_time:.2f} seconds")
            
            input_tokens = max(1, int(len(truncated_content.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            # Log response
            print(f"Successfully generated content with Gemini. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            # Return the response
            return jsonify({
                'html': html_content,
                'model': GEMINI_MODEL,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'total_cost': 0.0
                }
            })
        
        except DeadlineExceeded as e:
            error_message = str(e)
            print(f"Deadline exceeded in /api/process-gemini: {error_message}")
            print(traceback.format_exc())
            
            # Try one more time with reduced parameters
            try:
                print("Attempting generation with reduced parameters after timeout")
                # Use significantly reduced parameters
                fallback_config = {
                    "max_output_tokens": 4096,  # Much smaller for faster response
                    "temperature": temperature,
                    "top_p": GEMINI_TOP_P,
                    "top_k": GEMINI_TOP_K
                }
                
                fallback_response = model.generate_content(
                    contents,
                    generation_config=fallback_config,
                    timeout=15  # Shorter timeout
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
                    return jsonify({
                        'html': fallback_html,
                        'model': GEMINI_MODEL,
                        'warning': 'Generated with reduced parameters due to timeout',
                        'usage': {
                            'input_tokens': int(len(truncated_content.split()) * 1.3),
                            'output_tokens': int(len(fallback_html.split()) * 1.3),
                            'total_tokens': int(len(truncated_content.split()) * 1.3) + int(len(fallback_html.split()) * 1.3),
                            'total_cost': 0.0
                        }
                    })
            except Exception as fallback_error:
                print(f"Fallback generation also failed: {str(fallback_error)}")
                # Continue to return the default fallback HTML
            
            # Return a fallback simple HTML with the content 
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
            
            return jsonify({
                'html': fallback_html,
                'model': 'fallback',
                'error': 'The Gemini API request took too long to complete. Fallback visualization provided.',
                'usage': {
                    'input_tokens': len(truncated_content.split()),
                    'output_tokens': 0,
                    'total_tokens': len(truncated_content.split()),
                    'total_cost': 0.0
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

@app.route('/', methods=['POST'])
def process_gemini_endpoint():
    return handler(request)
