import os
import json
import httpx

from config import get_ollama_base_url, get_verbose

print(
    f"[llm_provider] Importing with CLIPROXY_API_KEY = {os.environ.get('CLIPROXY_API_KEY', 'NOT SET')}"
)

_API_KEY = os.environ.get("CLIPROXY_API_KEY", "")
_fallback_models: list[str] = []
_selected_model: str | None = None


def _get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"
    return headers


def _get_base_url() -> str:
    return get_ollama_base_url()


def _get_fallback_models() -> list[str]:
    global _fallback_models
    if _fallback_models:
        return _fallback_models
    try:
        with open(os.path.join(ROOT_DIR, "config.json"), "r") as f:
            cfg = json.load(f)
        _fallback_models = cfg.get("ollama_fallback_models", [])
    except Exception:
        _fallback_models = []
    return _fallback_models


def list_models() -> list[str]:
    base_url = _get_base_url()
    response = httpx.get(f"{base_url}/v1/models", headers=_get_headers(), timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return sorted(m["id"] for m in data.get("data", []))


def select_model(model: str) -> None:
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    return _selected_model


def _try_generate(prompt: str, model: str, timeout: float = 120.0) -> str | None:
    import time as _time

    base_url = _get_base_url()
    for attempt in range(3):
        try:
            response = httpx.post(
                f"{base_url}/v1/chat/completions",
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


def generate_text(prompt: str, model_name: str = None) -> str:
    primary = model_name or _selected_model
    if not primary:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )

    candidates = [primary]
    for fb in _get_fallback_models():
        if fb not in candidates:
            candidates.append(fb)

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
