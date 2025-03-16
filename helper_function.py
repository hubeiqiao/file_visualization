# Helper functions for server.py
import anthropic
import os
import importlib
import inspect

# Updated to handle proxies issue in Vercel environment
def create_anthropic_client(api_key):
    """
    Create an Anthropic client that is compatible with both local and Vercel environments.
    This handles different versions of the Anthropic library and environment-specific issues.
    """
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    
    try:
        # Check if the Anthropic class is available
        if hasattr(anthropic, 'Anthropic'):
            # Get init signature to check parameters
            sig = inspect.signature(anthropic.Anthropic.__init__)
            params = sig.parameters
            
            # Create a dict with only the parameters the constructor accepts
            kwargs = {'api_key': api_key}
            
            # This is the key fix - remove 'proxies' if it would cause an error
            if 'proxies' not in params:
                # Create client without proxies parameter
                return anthropic.Anthropic(**kwargs)
            else:
                # Create client with proxies parameter if supported
                return anthropic.Anthropic(api_key=api_key)
        elif hasattr(anthropic, 'Client'):
            # Fall back to older Client class
            sig = inspect.signature(anthropic.Client.__init__)
            params = sig.parameters
            
            # Create a dict with only the parameters the constructor accepts
            kwargs = {'api_key': api_key}
            
            # Remove 'proxies' if it would cause an error
            if 'proxies' not in params:
                # Create client without proxies parameter
                return anthropic.Client(**kwargs)
            else:
                # Create client with proxies parameter if supported
                return anthropic.Client(api_key=api_key)
        else:
            # Try to import directly if neither class is available as attribute
            try:
                from anthropic import Anthropic
                return Anthropic(api_key=api_key)
            except ImportError:
                try:
                    from anthropic import Client
                    return Client(api_key=api_key)
                except ImportError:
                    raise Exception("Could not find Anthropic or Client class")
    except Exception as e:
        raise Exception(f"Failed to create Anthropic client: {str(e)}") 