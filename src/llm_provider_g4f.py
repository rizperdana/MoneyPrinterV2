import os
import sys
from g4f.client import Client

# Set the environment variables for the openai provider to point to our cliproxy API
os.environ["OPENAI_API_BASE"] = "http://localhost:8317/v1"
os.environ["OPENAI_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

# Create a g4f client
client = Client()

# We'll keep the same interface as the original llm_provider.py
_selected_model: str | None = None

def _get_base_url() -> str:
    # This is not used anymore, but we keep it for compatibility
    return os.environ.get("OPENAI_API_BASE", "http://localhost:8317/v1")

def _get_headers() -> dict:
    # Not used with g4f client, but we keep it for compatibility
    return {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        "Content-Type": "application/json",
    }

def list_models() -> list[str]:
    """
    Lists all models available on the OpenAI-compatible server.
    We'll use the g4f client to fetch models? Actually, g4f client doesn't have a direct way to list models from a custom endpoint.
    We'll fall back to the original method using httpx, or we can return a static list.
    For simplicity, we'll use the original method from the cliproxy API.
    """
    import httpx
    base_url = _get_base_url()
    headers = _get_headers()
    response = httpx.get(f"{base_url}/models", headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return sorted(m["id"] for m in data.get("data", []))

def select_model(model: str) -> None:
    """
    Sets the model to use for all subsequent generate_text calls.
    """
    global _selected_model
    _selected_model = model

def get_active_model() -> str | None:
    """
    Returns the currently selected model, or None if none has been selected.
    """
    return _selected_model

def generate_text(prompt: str, model_name: str = None) -> str:
    """
    Generates text using the g4f client with our custom endpoint.
    """
    model = model_name or _selected_model
    if not model:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )
    
    # Use the g4f client to generate text
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        # We can set temperature, max_tokens, etc. if needed
        # For now, we'll use defaults
    )
    content = response.choices[0].message.content
    if content:
        return content.strip()
    else:
        raise RuntimeError("LLM returned empty content")

# If this file is run directly, test it
if __name__ == "__main__":
    # Test the functions
    print("Testing list_models...")
    try:
        models = list_models()
        print(f"Found {len(models)} models")
        if models:
            print(f"First model: {models[0]}")
            select_model(models[0])
            print(f"Selected model: {models[0]}")
            print("Testing generate_text...")
            resp = generate_text("Say hello in one word.")
            print(f"Response: {resp}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
