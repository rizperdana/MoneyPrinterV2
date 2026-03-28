"""
Working LLM provider using g4f with a custom OpenAI-compatible endpoint.
This version uses the g4f client with the OpenAI provider by setting the
environment variables OPENAI_API_BASE and OPENAI_API_KEY.
However, note that the built-in OpenAI providers in g4f (like OpenaiAccount,
OpenaiChat) are designed for specific services and require authentication
har files or cookies. For a generic OpenAI-compatible endpoint, we can use
the 'custom' provider only if we have configured routes in config.yaml.
Since we do not have a config.yaml, we fall back to using the direct
httpx approach (see llm_provider.py) which is simpler and more reliable.

This file demonstrates how one would use g4f with a custom endpoint if
the necessary configuration were in place. For now, we keep the original
llm_provider.py as the working solution.
"""
import os
import sys
from g4f.client import Client

# Set the environment variables for the OpenAI-compatible endpoint
os.environ["OPENAI_API_BASE"] = "http://localhost:8317/v1"
os.environ["OPENAI_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

# Create a g4f client. Note: without proper provider configuration, the client
# will iterate through its list of providers and may fail due to missing
# authentication or cookies for services like OpenaiAccount, etc.
# We will not rely on this for the MoneyPrinterV2 pipeline; instead we use
# the direct httpx method in llm_provider.py.
client = Client()

# We keep the same interface as the original llm_provider.py for compatibility.
_selected_model: str | None = None

def _get_base_url() -> str:
    return os.environ.get("OPENAI_API_BASE", "http://localhost:8317/v1")

def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        "Content-Type": "application/json",
    }

def list_models() -> list[str]:
    """
    Lists all models available on the OpenAI-compatible server.
    We use the direct httpx method because g4f client does not provide a
    straightforward way to list models from a custom endpoint without
    authenticating to a specific service.
    """
    import httpx
    base_url = _get_base_url()
    headers = _get_headers()
    response = httpx.get(f"{base_url}/models", headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return sorted(m["id"] for m in data.get("data", []))

def select_model(model: str) -> None:
    global _selected_model
    _selected_model = model

def get_active_model() -> str | None:
    return _selected_model

def generate_text(prompt: str, model_name: str = None) -> str:
    """
    Generates text using the g4f client. This may fail if the provider
    requires authentication. For a reliable solution, use the direct
    httpx method as in llm_provider.py.
    """
    model = model_name or _selected_model
    if not model:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
        else:
            raise RuntimeError("LLM returned empty content")
    except Exception as e:
        # Fall back to direct httpx method if g4f fails
        import httpx
        base_url = _get_base_url()
        headers = _get_headers()
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"].get("content")
        if content:
            return content.strip()
        else:
            raise RuntimeError("LLM returned empty content after fallback")

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