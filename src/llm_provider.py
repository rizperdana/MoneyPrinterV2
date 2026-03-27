import os
import httpx

from config import get_ollama_base_url

_selected_model: str | None = None

_API_KEY = os.environ.get("CLIPROXY_API_KEY", "")


def _get_base_url() -> str:
    return get_ollama_base_url()


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }


def list_models() -> list[str]:
    """
    Lists all models available on the OpenAI-compatible server.

    Returns:
        models (list[str]): Sorted list of model names.
    """
    base_url = _get_base_url()
    response = httpx.get(f"{base_url}/models", headers=_get_headers(), timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return sorted(m["id"] for m in data.get("data", []))


def select_model(model: str) -> None:
    """
    Sets the model to use for all subsequent generate_text calls.

    Args:
        model (str): A model name (must be available on the server).
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
    Generates text using the OpenAI-compatible server.

    Args:
        prompt (str): User prompt
        model_name (str): Optional model name override

    Returns:
        response (str): Generated text
    """
    model = model_name or _selected_model
    if not model:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )

    import time as _time
    base_url = _get_base_url()
    for attempt in range(3):
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=_get_headers(),
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
        # Reasoning model may return None content on first attempt
        if attempt < 2:
            _time.sleep(2)
    raise RuntimeError("LLM returned empty content after 3 attempts")
