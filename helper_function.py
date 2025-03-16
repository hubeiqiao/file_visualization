# Helper functions for server.py
import anthropic
import os

def create_anthropic_client(api_key):
    """
    Create an Anthropic client that is compatible with both local and Vercel environments.
    This function uses a simpler approach that completely avoids the proxies parameter issue.
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
        
    try:
        # For newer versions of the anthropic library
        if hasattr(anthropic, 'Anthropic'):
            # Create client with only the essential parameter (no proxies)
            # Using a dictionary and **kwargs to avoid any parameter issues
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