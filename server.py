# Try to catch any initialization errors for Vercel deployment
try:
    import sys
    import os
    import traceback
    
    # Print Python version and environment info for debugging
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Environment: {'Vercel' if os.environ.get('VERCEL') else 'Local'}")
    
    # Import required packages with error handling
    try:
        from flask import Flask, request, jsonify, Response, send_from_directory, stream_with_context
        print("Flask imported successfully")
    except ImportError as e:
        print(f"Error importing Flask: {e}")
        traceback.print_exc()
    
    try:
        import time
        import uuid
        import json
        import base64
        from flask_cors import CORS
        print("Basic modules imported successfully")
    except ImportError as e:
        print(f"Error importing basic modules: {e}")
        traceback.print_exc()
    
    try:
        from helper_function import create_anthropic_client, create_gemini_client, GeminiStreamingResponse, format_stream_event
        print("Helper functions imported successfully")
    except ImportError as e:
        print(f"Error importing helper_function: {e}")
        traceback.print_exc()
    
    # Initialize Flask app here
    app = Flask(__name__, static_folder='static')
    CORS(app)
    
    # Create session cache for streaming reconnection
    session_cache = {}
    
    # Constants
    # Claude Constants
    CLAUDE_MODEL = "claude-3-opus-20240229"
    CLAUDE_MAX_TOKENS = 100000
    CLAUDE_TEMPERATURE = 0.5
    CLAUDE_THINKING_TOKENS = 25000
    
    # Gemini Constants
    GEMINI_MODEL = "gemini-1.5-pro-latest"
    GEMINI_MAX_OUTPUT_TOKENS = 100000
    GEMINI_TEMPERATURE = 0.5
    GEMINI_TOP_P = 0.9
    GEMINI_TOP_K = 32
    
    print("Flask app initialized successfully")
    
except Exception as e:
    print(f"Initialization error: {e}")
    traceback.print_exc()

# System instructions for both models
SYSTEM_INSTRUCTION = """You are an expert web developer who specializes in transforming raw content into elegant, modern websites.

Your task is to generate a complete HTML file based on the provided content.

## Guidelines:
1. Create a single HTML file that encompasses all the content provided
2. Design should be modern, professional, and visually appealing
3. The design should be responsive and mobile-friendly
4. Organize the content logically and hierarchically
5. Use semantic HTML5 elements appropriately
6. Include all necessary CSS inline (no external files)
7. Add appropriate navigation and structure
8. Create appealing typography with good readability
9. Include appropriate spacing, padding, and margins
10. Use a color scheme that complements the content
11. Enhance with subtle animations where appropriate
12. If code appears in the content, format it properly
13. Font Awesome for icons is available as: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

## IMPORTANT:
- Generate only valid HTML that can be viewed directly in a browser
- Include ONLY the HTML file content, nothing else - no explanations, comments to the user, etc.
- The output should start with <!DOCTYPE html> and contain a complete webpage
- Do not include Markdown notation in your response
"""

@app.route('/api/process-stream', methods=['POST'])
def process_streaming():
    try:
        # Get request data
        data = request.get_json()
        api_key = data.get('api_key')
        content = data.get('content')
        format_prompt = data.get('format_prompt', '')
        max_tokens = data.get('max_tokens', 128000)
        temperature = data.get('temperature', 1.0)
        thinking_budget = data.get('thinking_budget', 32000)
        test_mode = data.get('test_mode', False)
        
        # Log request parameters (except content and API key)
        logging.info(f"Processing request with parameters: max_tokens={max_tokens}, temperature={temperature}, thinking_budget={thinking_budget}, test_mode={test_mode}")
        
        # Validate API key
        if not api_key:
            return jsonify({"error": "API key is required"}), 400
            
        if not is_valid_api_key(api_key):
            return jsonify({"error": "Invalid API key format"}), 400
        
        # Validate content
        if not content:
            return jsonify({"error": "Content is required"}), 400
            
        # Create response stream
        def generate():
            try:
                # Initialize timing
                start_time = time.time()
                
                # Send start event
                start_event = {
                    "type": "start",
                    "message_id": str(uuid.uuid4())
                }
                yield f"data: {json.dumps(start_event)}\n\n"
                
                # Extract text from file if needed
                file_content, file_type = extract_content(content)
                logging.info(f"Content extracted, type: {file_type}, length: {len(file_content)}")
                
                # Calculate token estimates
                input_tokens_estimate = estimate_tokens(file_content)
                logging.info(f"Estimated input tokens: {input_tokens_estimate}")
                
                # For test mode, use minimal API tokens but still make an actual API call
                system_message = ""
                prompt = ""
                
                if test_mode:
                    # In test mode, use a minimal prompt to verify API connectivity
                    # While still generating HTML (but with much less token usage)
                    system_message = "You are a file visualization assistant. Generate a simple HTML representation of the content."
                    prompt = f"""This is a TEST MODE request using minimal tokens.
                    
Generate a simple HTML visualization for a file of type: {file_type}.
Keep your response very short - limit to 100 tokens.

Example content: {file_content[:100]}...

Respond with valid HTML that displays a simple test visualization."""
                    
                    # Use Claude 3 Haiku for minimal token usage in test mode
                    model = "claude-3-haiku-20240307"
                    max_tokens = min(max_tokens, 100)  # Cap at 100 tokens in test mode
                    thinking_budget = 0  # No thinking in test mode
                    
                    # Send info event about test mode
                    info_event = {
                        "type": "info",
                        "message": "Test mode enabled: Using minimal tokens with Claude 3 Haiku"
                    }
                    yield f"data: {json.dumps(info_event)}\n\n"
                else:
                    # Normal mode - full processing
                    system_message = """You are an expert at creating beautiful HTML visualizations of file content. Your task is to create an HTML page that visualizes the content in a way that makes it easy to understand and navigate.

For code files, use syntax highlighting and proper indentation. For data, create appropriate visualizations like tables, charts, or other visual representations. For text, create a well-formatted document with proper structure and styling.

Your output should be a complete, self-contained HTML file that includes all necessary CSS and JavaScript. The HTML should be clean, valid, and render correctly in modern browsers. Make it visually appealing with a clean, modern design.

Ensure your visualization uses responsive design principles and looks good on different screen sizes. Use semantic HTML5 elements where appropriate.

The visualization should highlight the most important aspects of the content and make it easier to understand than the raw content would be."""

                    prompt = f"""Create an HTML visualization for the following content. 
                    
Additional instructions: {format_prompt}

CONTENT:
{file_content}

Please generate a complete, standalone HTML file that beautifully visualizes this content. Make it clean, modern, and easy to understand. Include any necessary CSS and JavaScript directly in the HTML file.

Don't comment on the content, just generate the HTML visualization.
"""
                    # Use Claude 3.7 Sonnet for full processing
                    model = "claude-3-7-sonnet-20250219"
                
                # Send the request to Anthropic API
                client = get_anthropic_client(api_key)
                if not client:
                    error_event = {
                        "type": "error",
                        "message": "Failed to create Anthropic client"
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    return
                
                # For normal mode, include thinking if requested
                thinking_messages = None
                if not test_mode and thinking_budget > 0:
                    # Signal thinking start
                    thinking_start_event = {
                        "type": "thinking_start"
                    }
                    yield f"data: {json.dumps(thinking_start_event)}\n\n"
                    
                    # Get thinking from Anthropic API
                    thinking_prompt = f"""Analyze the following content and think about how to create an effective HTML visualization for it. 
                    
Consider the content type, structure, and important patterns. How would you best represent this visually to make it easy to understand?

Think through the structure of your HTML, the CSS styling you'll use, and any JavaScript that might be helpful.

CONTENT:
{file_content}

First, identify the type of content and its key characteristics.
Then, outline the main components of your visualization.
Finally, describe the specific HTML elements, CSS styles, and JavaScript functions you would use.

Don't actually write the HTML yet, just think through your approach. Be specific and detailed in your thinking."""

                    try:
                        thinking_response = client.messages.create(
                            model=model,
                            max_tokens=thinking_budget,
                            temperature=temperature,
                            system=system_message,
                            messages=[
                                {"role": "user", "content": thinking_prompt}
                            ]
                        )
                        
                        thinking_content = thinking_response.content[0].text
                        thinking_tokens = {
                            "input": thinking_response.usage.input_tokens,
                            "output": thinking_response.usage.output_tokens
                        }
                        
                        # Signal thinking complete
                        thinking_end_event = {
                            "type": "thinking_end"
                        }
                        yield f"data: {json.dumps(thinking_end_event)}\n\n"
                        
                        # Set up thinking messages for main request
                        thinking_messages = [
                            {"role": "user", "content": thinking_prompt},
                            {"role": "assistant", "content": thinking_content}
                        ]
                        
                    except Exception as e:
                        logging.error(f"Thinking error: {str(e)}")
                        thinking_error_event = {
                            "type": "info",
                            "message": f"Thinking phase failed, continuing without thinking: {str(e)}"
                        }
                        yield f"data: {json.dumps(thinking_error_event)}\n\n"
                        thinking_messages = None
                
                try:
                    # Set up messages based on whether we have thinking
                    messages = []
                    if thinking_messages:
                        messages.extend(thinking_messages)
                    messages.append({"role": "user", "content": prompt})
                    
                    # Create the main request to Anthropic
                    response = client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_message,
                        messages=messages,
                        stream=True
                    )
                    
                    # Stream the response chunks
                    generated_html = ""
                    for chunk in response:
                        if chunk.type == "content_block_delta":
                            text = chunk.delta.text
                            generated_html += text
                            
                            # Send each chunk
                            chunk_event = {
                                "type": "chunk",
                                "content": text
                            }
                            yield f"data: {json.dumps(chunk_event)}\n\n"
                    
                    # Calculate elapsed time
                    elapsed_time = time.time() - start_time
                    
                    # Get token usage from the completed response
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    
                    # Get thinking tokens (if used)
                    thinking_tokens_count = 0
                    if thinking_messages:
                        thinking_tokens_count = thinking_tokens.get("input", 0) + thinking_tokens.get("output", 0)
                    
                    # Calculate total cost at $3 per million tokens for Claude 3.7 Sonnet
                    # If test mode, use Claude 3 Haiku rate ($1.25 per million)
                    rate_per_million = 1.25 if test_mode else 3.0
                    total_tokens = input_tokens + output_tokens + thinking_tokens_count
                    total_cost = (total_tokens / 1000000) * rate_per_million
                    
                    # Include usage information
                    usage_info = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "thinking_tokens": thinking_tokens_count,
                        "total_tokens": total_tokens,
                        "total_cost": total_cost,
                        "time_elapsed": elapsed_time,
                        "test_mode": test_mode,
                        "model": model
                    }
                    
                    # Save usage stats to file for persistence
                    try:
                        usage_file = "usage_stats.json"
                        # Create file if it doesn't exist
                        if not os.path.exists(usage_file):
                            with open(usage_file, "w") as f:
                                json.dump({"total_tokens": 0, "total_cost": 0.0, "requests": []}, f)
                        
                        # Read current stats
                        with open(usage_file, "r") as f:
                            stats = json.load(f)
                        
                        # Update stats
                        stats["total_tokens"] += total_tokens
                        stats["total_cost"] += total_cost
                        stats["requests"].append({
                            "timestamp": time.time(),
                            "tokens": total_tokens,
                            "cost": total_cost,
                            "model": model
                        })
                        
                        # Trim request history if it gets too long (keep last 100)
                        if len(stats["requests"]) > 100:
                            stats["requests"] = stats["requests"][-100:]
                        
                        # Write updated stats
                        with open(usage_file, "w") as f:
                            json.dump(stats, f)
                        
                        print(f"Updated usage stats: total tokens {stats['total_tokens']}, total cost ${stats['total_cost']:.4f}")
                    except Exception as e:
                        print(f"Error updating usage stats: {str(e)}")
                    
                    # Send completion event with HTML and usage info
                    complete_event = {
                        "type": "complete",
                        "html": generated_html,
                        "usage": usage_info
                    }
                    
                    yield f"data: {json.dumps(complete_event)}\n\n"
                    logging.info(f"Generation complete: {usage_info}")
                    
                except Exception as e:
                    logging.error(f"API request error: {str(e)}")
                    error_event = {
                        "type": "error",
                        "message": f"API request failed: {str(e)}"
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    
            except Exception as e:
                logging.error(f"Stream generation error: {str(e)}")
                error_event = {
                    "type": "error",
                    "message": f"Generation failed: {str(e)}"
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                
        # Return streaming response
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logging.error(f"Process stream error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/usage-stats', methods=['GET'])
def get_usage_stats():
    """
    Returns the current usage statistics from the usage_stats.json file
    """
    try:
        usage_file = "usage_stats.json"
        if not os.path.exists(usage_file):
            # If no stats file exists yet, return empty stats
            return jsonify({
                "total_tokens": 0,
                "total_cost": 0.0,
                "requests": []
            })
        
        with open(usage_file, "r") as f:
            stats = json.load(f)
        
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Error retrieving usage stats: {str(e)}")
        return jsonify({
            "error": f"Failed to retrieve usage statistics: {str(e)}",
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests": []
        }), 500

# Only keep one instance of the app.js route
@app.route('/app.js')
def serve_app_js():
    return send_from_directory('static', 'app.js', mimetype='application/javascript')

# Run with enhanced settings for larger content
run_simple(
    args.host, 
    port, 
    app, 
    use_reloader=not args.no_reload,
    use_debugger=args.debug,
    threaded=True,
    passthrough_errors=args.debug
)

# Important: Export the Flask app for Vercel
application = app 