from agno.models.anthropic import Claude
from agno.models.ollama import Ollama
from ..config.settings import settings

def get_agent_model():
    """Determines which LLM to use based on environment variables."""
    provider = settings.AGENT_MODEL_PROVIDER
    anthropic_api_key = settings.ANTHROPIC_API_KEY

    if provider == "ollama":
        ollama_model_id = settings.OLLAMA_MODEL_ID
        if not ollama_model_id:
            print("Warning: AGENT_MODEL_PROVIDER is 'ollama' but OLLAMA_MODEL_ID is not set. Defaulting to 'gemma:latest'. Please set OLLAMA_MODEL_ID.")
            ollama_model_id = "gemma:latest" # A common default, user should verify/change
        
        ollama_host = settings.OLLAMA_HOST # Optional host
        print(f"Using Ollama model: {ollama_model_id} on host: {ollama_host or 'default'}")
        if ollama_host:
            return Ollama(id=ollama_model_id, host=ollama_host)
        return Ollama(id=ollama_model_id)
    
    elif provider == "claude":
        if not anthropic_api_key:
            raise ValueError("AGENT_MODEL_PROVIDER is 'claude' but ANTHROPIC_API_KEY is not set.")
        # The user previously requested "claude-3-7-sonnet-20250219"
        # We can keep this specific model ID for Claude or make it configurable too.
        # For simplicity, using the last requested Claude model ID directly here.
        claude_model_id = settings.CLAUDE_MODEL_ID
        print(f"Using Claude model: {claude_model_id}")
        return Claude(id=claude_model_id, api_key=anthropic_api_key)
    
    else:
        raise ValueError(f"Unsupported AGENT_MODEL_PROVIDER: {provider}. Choose 'claude' or 'ollama'.") 