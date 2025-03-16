# Helper functions for server.py
import anthropic
import os
import json
import requests

def create_anthropic_client(api_key):
    """
    Create an Anthropic client that is compatible with both local and Vercel environments.
    For Vercel, we use a completely different approach to avoid the proxies issue.
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    
    # Special handling for Vercel environment
    if is_vercel:
        return VercelCompatibleClient(api_key)
    
    # Local environment - use standard approach
    try:
        # For newer versions of the anthropic library
        if hasattr(anthropic, 'Anthropic'):
            # Create client with only the essential parameter (no proxies)
            kwargs = {"api_key": api_key}
            return anthropic.Anthropic(**kwargs)
        
        # For older versions of the anthropic library
        elif hasattr(anthropic, 'Client'):
            # Create client with only the essential parameter (no proxies)
            kwargs = {"api_key": api_key}
            return anthropic.Client(**kwargs)
        
        # Last resort fallbacks
        else:
            # Try to import classes directly
            try:
                # Try newer class
                from anthropic import Anthropic
                return Anthropic(api_key=api_key)
            except (ImportError, AttributeError):
                try:
                    # Try older class
                    from anthropic import Client
                    return Client(api_key=api_key)
                except (ImportError, AttributeError):
                    raise ImportError("Could not import Anthropic or Client class")
    except Exception as e:
        # Provide detailed error information
        if "proxies" in str(e):
            raise Exception(f"API client error: The Anthropic library version has a compatibility issue. Error: {str(e)}")
        elif "auth" in str(e).lower() or "key" in str(e).lower() or "invalid" in str(e).lower():
            raise Exception(f"API authentication failed: {str(e)}")
        else:
            raise Exception(f"Failed to create Anthropic client: {str(e)}")

# Special client class for Vercel that doesn't use the standard Anthropic library
class VercelCompatibleClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def models(self):
        # Lightweight method to check if the API key is valid
        class ModelList:
            def list(self):
                response = requests.get(
                    f"{self.base_url}/models",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise Exception(f"Authentication failed: {response.json().get('error', {}).get('message', 'Invalid API key')}")
                else:
                    raise Exception(f"Error {response.status_code}: {response.text}")
        
        return ModelList()
    
    def count_tokens(self, text):
        # Simple approximation (1 token ≈ 4 characters)
        return len(text) // 4 