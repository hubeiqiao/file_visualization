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

async def process_request(request_data: GeminiRequest):
    """
    Process a file using the Google Gemini API and return HTML.
    """
    print("\n==== API PROCESS GEMINI EDGE REQUEST RECEIVED ====")
    start_time = time.time()
    session_id = str(uuid.uuid4())
    
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
            return {
                "error": "Google Generative AI package is not installed on the server",
                "success": False
            }
        
        # Create Gemini client
        print(f"Creating Google Gemini client with API key: {api_key[:8]}...")
        
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
            return {
                "error": f"Failed to create Gemini client. Check your API key. Error: {error_message}",
                "success": False
            }
        
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
        
        print("Generating content with Gemini (non-streaming)")
        
        # Configure generation parameters
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": GEMINI_TOP_P,
            "top_k": GEMINI_TOP_K
        }
        
        try:
            # Generate content without streaming
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract content
            html_content = ""
            if hasattr(response, 'text'):
                html_content = response.text
            elif hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'text'):
                        html_content += part.text
            
            if not html_content:
                return {
                    "error": "No content generated",
                    "success": False
                }
                
            # Calculate generation time
            total_generation_time = time.time() - start_time
            
            # Calculate approximate token usage
            input_tokens = max(1, int(len(prompt.split()) * 1.3))
            output_tokens = max(1, int(len(html_content.split()) * 1.3))
            
            print(f"Generation completed in {total_generation_time:.2f}s")
            print(f"Generated content length: {len(html_content)} chars")
            print(f"Estimated tokens: Input={input_tokens}, Output={output_tokens}")
            
            # Return the generated HTML with usage info
            return {
                "html": html_content,
                "success": True,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "processing_time": total_generation_time
                }
            }
            
        except Exception as generation_error:
            error_message = str(generation_error)
            print(f"Error during generation: {error_message}")
            print(traceback.format_exc())
            return {
                "error": f"Generation failed: {error_message}",
                "success": False
            }
    
    except Exception as outer_error:
        error_message = str(outer_error)
        print(f"Outer error in process_request: {error_message}")
        print(traceback.format_exc())
        return {
            "error": f"Server error: {error_message}",
            "success": False
        }

@app.post("/api/gemini-edge")
async def gemini_endpoint(request: Request):
    try:
        # Parse request data
        request_json = await request.json()
        request_data = GeminiRequest(**request_json)
        
        # Process the request
        result = await process_request(request_data)
        
        # Check if there was an error
        if "error" in result and not result.get("success", False):
            # Return error with appropriate status code
            return Response(
                content=json.dumps(result),
                status_code=400 if "API key" in result["error"] else 500,
                media_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Return successful response
        return result
    except Exception as e:
        print(f"Error in endpoint: {str(e)}")
        print(traceback.format_exc())
        return Response(
            content=json.dumps({"error": f"Server error: {str(e)}", "success": False}),
            status_code=500,
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.options("/api/gemini-edge")
async def options_gemini():
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