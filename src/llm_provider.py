import os
import json
import httpx

from config import get_verbose

print(
    f"[llm_provider] Importing with CLIPROXY_API_KEY = {os.environ.get('CLIPROXY_API_KEY', 'NOT SET')}"
)

_API_KEY = "sk-dIMp6qoD0oWyMvswe"
_CLIPROXY_BASE = "http://localhost:8317/v1"
_selected_model: str | None = None


def _get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"
    return headers


def select_model(model: str) -> None:
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    return _selected_model


def _try_generate(prompt: str, model: str, timeout: float = 120.0) -> str | None:
    import time as _time

    for attempt in range(3):
        try:
            response = httpx.post(
                f"{_CLIPROXY_BASE}/chat/completions",
                headers=_get_headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content")
            if content:
                return content.strip()
            if attempt < 2:
                _time.sleep(2)
        except Exception as e:
            print(f"[llm_provider] Exception in _try_generate: {type(e).__name__}: {e}")
            if attempt < 2:
                _time.sleep(2)
    return None


def list_models() -> list[str]:
    """Return list of available models from the API"""
    try:
        response = httpx.get(
            f"{_CLIPROXY_BASE}/models",
            headers=_get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"[llm_provider] Failed to fetch models: {type(e).__name__}: {e}")
        # Fallback known models
        return ["kilo-auto/free", "gemma4", "llama3.1:8b", "mistral:7b"]


def generate_text(prompt: str, model_name: str = None) -> str:
    # PRIMARY: cliproxyapi kilo-auto/free
    primary = model_name or _selected_model or "kilo-auto/free"

    candidates = [primary]

    # FALLBACK: llama.cpp gemma4
    candidates.append("gemma4")

    last_error = None
    for model in candidates:
        result = _try_generate(prompt, model)
        if result is not None:
            if model != primary:
                print(f"[llm_provider] Fell back to {model} (primary: {primary})")
            return result
        last_error = model

    raise RuntimeError(
        f"All models failed (tried: {', '.join(candidates)}). "
        f"Last error from: {last_error}"
    )


# Public exports
__all__ = [
    "list_models",
    "select_model",
    "get_active_model",
    "generate_text"
]
