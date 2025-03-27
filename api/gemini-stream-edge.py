import os
import json
import time
import uuid
import traceback
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# Try to import Google Generative AI package
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI package not available")

# Set up FastAPI app for the Edge function
app = FastAPI()

# Add CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global constants for Gemini
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"  # Use the latest stable model
GEMINI_MAX_OUTPUT_TOKENS = 65536  # Full token limit
GEMINI_TEMPERATURE = 1.0
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 64

# System instruction for Gemini
SYSTEM_INSTRUCTION = """You are an expert web developer. Transform the provided content into a beautiful, modern, responsive HTML webpage with CSS.

The HTML should:
1. Use modern CSS and HTML5 features (like flexbox, CSS grid, and custom properties)
2. Be fully responsive and mobile-friendly
3. Have an attractive, professional design
4. Implement good accessibility practices
5. Use semantic HTML elements properly
6. Have a clean, consistent layout
7. Not use any external JS libraries or CSS frameworks
8. Include all CSS inline in a <style> tag
9. Be complete and ready to render without external dependencies
10. Include engaging visual elements and a cohesive color scheme

Make sure the HTML is valid, self-contained, and will render properly in modern browsers."""

# Pydantic model for request validation
class GeminiRequest(BaseModel):
    api_key: str = Field(..., description="Google Gemini API key")
    content: str = Field(..., description="Content to transform into HTML")
    source: Optional[str] = Field(None, description="Alternative content field (for compatibility)")
    format_prompt: Optional[str] = Field(None, description="Additional formatting instructions")
    max_tokens: Optional[int] = Field(GEMINI_MAX_OUTPUT_TOKENS, description="Maximum output tokens")
    temperature: Optional[float] = Field(GEMINI_TEMPERATURE, description="Temperature for generation")
    file_name: Optional[str] = Field(None, description="Name of uploaded file")
    file_content: Optional[str] = Field(None, description="Content of uploaded file")

def format_stream_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format an event for server-sent events (SSE)."""
    return f"data: {json.dumps(data)}\n\n"

async def process_stream_request(request_data: GeminiRequest):
    """Process a file using the Google Gemini API and return streaming HTML."""
    print("\n==== API PROCESS GEMINI STREAM EDGE REQUEST RECEIVED ====")
    start_time = time.time()
    session_id = str(uuid.uuid4())
    print(f"Generated session ID: {session_id}")
    
    events = []
    
    try:
        # Extract request parameters
        api_key = request_data.api_key
        content = request_data.content or request_data.source or ""
        format_prompt = request_data.format_prompt or ""
        max_tokens = request_data.max_tokens or GEMINI_MAX_OUTPUT_TOKENS
        temperature = request_data.temperature or GEMINI_TEMPERATURE
        
        print(f"Processing Gemini request with max_tokens={max_tokens}, content_length={len(content)}")
        
        # Check if Gemini is available
        if not GEMINI_AVAILABLE:
            events.append(format_stream_event("error", {
                "error": "Google Generative AI package is not installed on the server",
                "type": "error",
                "session_id": session_id
            }))
            return events
        
        # Create Gemini client
        try:
            # Configure the Gemini client
            genai.configure(api_key=api_key)
            print(f"Successfully configured Gemini client")
            
            # Get the model
            model = genai.GenerativeModel(GEMINI_MODEL)
            print(f"Successfully retrieved Gemini model: {GEMINI_MODEL}")
        except Exception as client_error:
            error_message = str(client_error)
            print(f"Failed to create Gemini client: {error_message}")
            events.append(format_stream_event("error", {
                "error": f"Failed to create Gemini client. Check your API key. Error: {error_message}",
                "type": "error",
                "session_id": session_id
            }))
            return events
        
        # Prepare content
        if format_prompt:
            content = f"{content}\n\n{format_prompt}"
        
        # Limit content length to avoid token limits
        content_limit = 100000  # Approximately 30k tokens
        if len(content) > content_limit:
            print(f"Content exceeds limit, truncating from {len(content)} to {content_limit} chars")
            content = content[:content_limit]
        
        # Create the prompt
        prompt = f"""
{SYSTEM_INSTRUCTION}

Here is the content to transform into a website:

{content}
"""
        
        # Send start event
        events.append(format_stream_event("stream_start", {
            "message": "Stream starting",
            "session_id": session_id
        }))
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        # Send status update
        events.append(format_stream_event("status", {
            "message": "Model loaded, starting generation",
            "session_id": session_id
        }))
        
        # Generate content with streaming
        print("Starting streaming generation with Gemini")
        
        # Variables to track streaming state
        chunks_received = 0
        accumulated_content = ""
        
        try:
            # Generate content with streaming
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            # Process the streaming response
            for chunk in response:
                chunks_received += 1
                
                # Extract text from the chunk
                chunk_text = ""
                try:
                    if hasattr(chunk, 'text'):
                        chunk_text = chunk.text
                    elif hasattr(chunk, 'parts') and chunk.parts:
                        for part in chunk.parts:
                            if hasattr(part, 'text'):
                                chunk_text += part.text
                except Exception as chunk_error:
                    print(f"Error extracting text from chunk: {str(chunk_error)}")
                    continue
                
                # Skip empty chunks
                if not chunk_text:
                    continue
                    
                # Add to accumulated content
                accumulated_content += chunk_text
                
                # Send content chunk
                events.append(format_stream_event("content_block_delta", {
                    "delta": {"text": chunk_text},
                    "type": "content_block_delta",
                    "session_id": session_id
                }))
                
                # Send keepalive every 15 chunks
                if chunks_received % 15 == 0:
                    events.append(format_stream_event("keepalive", {
                        "type": "keepalive",
                        "session_id": session_id
                    }))
            
            # Completed successfully
            total_generation_time = time.time() - start_time
            
            # Calculate approximate token usage
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(accumulated_content.split()) * 1.3))
            
            # Send completion event
            events.append(format_stream_event("message_complete", {
                "message": "Generation complete",
                "type": "message_complete",
                "html": accumulated_content,
                "session_id": session_id,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "processing_time": total_generation_time
                }
            }))
            
            print(f"Streaming completed successfully in {total_generation_time:.2f}s")
            print(f"Generated content length: {len(accumulated_content)} chars")
            
        except Exception as stream_error:
            print(f"Error during streaming: {str(stream_error)}")
            print(traceback.format_exc())
            
            # If we have accumulated content, continue with it
            if accumulated_content:
                print(f"Using partial content from stream ({len(accumulated_content)} chars)")
                total_generation_time = time.time() - start_time
                
                # Calculate approximate token usage
                input_tokens = max(1, int(len(prompt.split()) * 1.3))
                output_tokens = max(1, int(len(accumulated_content.split()) * 1.3))
                
                # Send completion event with partial content
                events.append(format_stream_event("message_complete", {
                    "message": "Generation partially complete",
                    "type": "message_complete",
                    "html": accumulated_content,
                    "session_id": session_id,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "processing_time": total_generation_time
                    }
                }))
            else:
                # Fallback to non-streaming as a last resort
                print("No content from streaming, trying non-streaming fallback")
                events.append(format_stream_event("status", {
                    "message": "Trying non-streaming fallback",
                    "session_id": session_id
                }))
                
                try:
                    # Generate content without streaming
                    fallback_response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    # Extract content
                    fallback_html = ""
                    if hasattr(fallback_response, 'text'):
                        fallback_html = fallback_response.text
                    elif hasattr(fallback_response, 'parts') and fallback_response.parts:
                        for part in fallback_response.parts:
                            if hasattr(part, 'text'):
                                fallback_html += part.text
                    
                    if fallback_html:
                        total_generation_time = time.time() - start_time
                        
                        # Calculate approximate token usage
                        input_tokens = max(1, int(len(prompt.split()) * 1.3))
                        output_tokens = max(1, int(len(fallback_html.split()) * 1.3))
                        
                        # Send the fallback content
                        events.append(format_stream_event("content", {
                            "chunk": fallback_html,
                            "type": "content",
                            "session_id": session_id
                        }))
                        
                        # Send completion event
                        events.append(format_stream_event("message_complete", {
                            "message": "Generation complete (fallback)",
                            "type": "message_complete",
                            "html": fallback_html,
                            "session_id": session_id,
                            "usage": {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                                "processing_time": total_generation_time
                            }
                        }))
                        
                        print(f"Fallback generation completed in {total_generation_time:.2f}s")
                    else:
                        events.append(format_stream_event("error", {
                            "error": "No content from non-streaming fallback",
                            "type": "error",
                            "session_id": session_id
                        }))
                except Exception as fallback_error:
                    print(f"Fallback generation failed: {str(fallback_error)}")
                    events.append(format_stream_event("error", {
                        "error": f"Generation failed: {str(fallback_error)}",
                        "type": "error",
                        "session_id": session_id
                    }))
    except Exception as outer_error:
        print(f"Outer error in process_stream_request: {str(outer_error)}")
        print(traceback.format_exc())
        events.append(format_stream_event("error", {
            "error": f"Server error: {str(outer_error)}",
            "type": "error",
            "session_id": session_id
        }))
    
    return events

@app.post("/api/gemini-stream-edge")
async def gemini_stream_endpoint(request: Request):
    try:
        # Parse request data
        request_json = await request.json()
        request_data = GeminiRequest(**request_json)
        
        # Process the request and get events
        events = await process_stream_request(request_data)
        
        # Return the events as a standard JSON response
        return {"events": events, "success": True}
    except Exception as e:
        print(f"Error in endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.options("/api/gemini-stream-edge")
async def options_gemini_stream():
    # Handle CORS preflight requests
    return Response(
        content="",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        }
    ) 