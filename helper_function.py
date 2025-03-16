# Helper functions for server.py
import anthropic
import os

# Updated to handle proxies issue in Vercel environment
def create_anthropic_client(api_key):
    """
    Create an Anthropic client that is compatible with both local and Vercel environments.
    This handles different versions of the Anthropic library and environment-specific issues.
    """
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL', False)
    
    # First try with explicit parameters to avoid proxies issue in Vercel
    if is_vercel:
        try:
            # For newer versions of the Anthropic library
            return anthropic.Anthropic(api_key=api_key)
        except TypeError as e:
            if 'proxies' in str(e):
                # Try to create a client without proxies for versions that don't handle it well
                try:
                    from anthropic import Anthropic
                    # Create client with bare minimum parameters
                    return Anthropic(api_key=api_key)
                except Exception:
                    # If that fails, try the old Client class
                    try:
                        from anthropic import Client
                        return Client(api_key=api_key)
                    except Exception:
                        raise Exception(f"Failed to create Anthropic client: {str(e)}. Please update the anthropic library.")
            else:
                raise
    else:
        # For local environment, try standard client creation
        try:
            # First try the newer Anthropic class
            try:
                return anthropic.Anthropic(api_key=api_key)
            except (AttributeError, ImportError):
                # Fall back to Client class for older versions
                return anthropic.Client(api_key=api_key)
        except Exception as e:
            raise Exception(f"Failed to initialize Anthropic client: {str(e)}") 