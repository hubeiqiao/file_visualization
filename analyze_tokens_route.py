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
                    # If client creation or API call fails, use word-based estimation
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