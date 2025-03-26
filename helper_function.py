# Helper functions for server.py
import anthropic
import os
import json
import requests
import time
import uuid
import base64
import traceback

# Import Google Generative AI package
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI package not available. Some features may be limited.")

# Add GeminiStreamingResponse class
class GeminiStreamingResponse:
    """A class to format streaming responses from Gemini API"""
    
    def __init__(self, response_stream):
        self.response_stream = response_stream
        
    def __iter__(self):
        for chunk in self.response_stream:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text
            elif hasattr(chunk, 'parts') and chunk.parts:
                for part in chunk.parts:
                    if hasattr(part, 'text') and part.text:
                        yield part.text
                    
    def __next__(self):
        return next(self.response_stream)

def create_gemini_client(api_key):
    """Create a Google Gemini client with the given API key."""
    if not GEMINI_AVAILABLE:
        raise ImportError("Google Generative AI package is not installed. Please install it with 'pip install google-generativeai'.")
    
    print(f"Creating Google Gemini client with API key: {api_key[:8]}...")
    
    # Check if API key is valid format
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    try:
        # Configure the Gemini client with the API key
        genai.configure(api_key=api_key)
        
        # Create a simple wrapper class that provides the methods expected by the server
        class GeminiClient:
            def __init__(self):
                pass
                
            def get_model(self, model_name):
                """Create and return a GenerativeModel instance for the specified model."""
                try:
                    model = genai.GenerativeModel(model_name)
                    # Test that model is accessible
                    _ = model.count_tokens("Test")
                    return model
                except Exception as e:
                    print(f"Error creating model {model_name}: {str(e)}")
                    raise
        
        # Create and return the client wrapper
        return GeminiClient()
            
    except Exception as e:
        print(f"Gemini client creation failed: {str(e)}")
        raise Exception(f"Failed to create Google Gemini client: {str(e)}")

def format_stream_event(event_type, data=None):
    """
    Format data as a server-sent event
    """
    event = {"type": event_type}
    
    if data:
        event.update(data)
    
    # Format as SSE
    return f"event: {event_type}\ndata: {json.dumps(data if data else {})}\n\n"

# Special client class for Vercel that doesn't use the standard Anthropic library
class VercelCompatibleClient:
    """A special client class for Vercel deployments that doesn't use the standard Anthropic library."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def create_completion(self, prompt, max_tokens=None, temperature=None, stream=False):
        """Create a completion using the Anthropic API directly."""
        url = f"{self.base_url}/complete"
        
        data = {
            "prompt": prompt,
            "model": "claude-2",
            "stream": stream
        }
        
        if max_tokens is not None:
            data["max_tokens_to_sample"] = max_tokens
            
        if temperature is not None:
            data["temperature"] = temperature
        
        try:
            response = requests.post(url, headers=self.headers, json=data, stream=stream)
            response.raise_for_status()
            
            if stream:
                return response.iter_lines()
            else:
                return response.json()
                
        except Exception as e:
            print(f"Error in create_completion: {str(e)}")
            raise

def create_anthropic_client(api_key):
    """Create an Anthropic client with the given API key."""
    print(f"Creating Anthropic client with API key: {api_key[:8]}...")
    
    # Check if API key is valid format
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    # Try to create the client with the standard approach first
    try:
        # Create client with only the essential parameter
        client = anthropic.Anthropic(api_key=api_key)
        
        # Test the client by getting the available models
        try:
            models = client.models.list()
            print("Successfully validated Anthropic client with models API")
            return client
        except Exception as model_error:
            print(f"Could not validate client with models API: {str(model_error)}")
            # Fall through to try completion API
        
        # If models API fails, try a test completion
        try:
            response = client.messages.create(
                model="claude-2",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say hello"}]
            )
            print("Successfully validated Anthropic client with completion API")
            return client
        except Exception as completion_error:
            print(f"Could not validate client with completion API: {str(completion_error)}")
            # Fall through to Vercel-compatible client
            
    except Exception as e:
        print(f"Standard client creation failed: {str(e)}")
        # Fall through to try Vercel-compatible client
    
    # If standard client fails, try Vercel-compatible version
    try:
        print("Attempting to create Vercel-compatible client...")
        client = VercelCompatibleClient(api_key)
        
        # Test the client
        test_response = client.create_completion(
            prompt="\n\nHuman: Say hello\n\nAssistant: ",
            max_tokens=10
        )
        
        if test_response and "completion" in test_response:
            print("Successfully created Vercel-compatible client")
            return client
            
        raise Exception("Test completion failed to return expected response format")
        
    except Exception as e:
        print(f"Vercel-compatible client creation failed: {str(e)}")
        raise Exception(f"Failed to create Anthropic client: {str(e)}")

def encode_image_to_base64(image_path):
    """
    Encode an image file to base64 string
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return None 