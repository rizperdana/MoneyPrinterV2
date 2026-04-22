import os
import json
import httpx
import sys

from config import get_verbose

print(
    f"[llm_provider] Importing with CLIPROXY_API_KEY = {os.environ.get('CLIPROXY_API_KEY', 'NOT SET')}"
)

_API_KEY = os.environ.get("CLIPROXY_API_KEY", "")


def _get_llm_base_url() -> str:
    """Get LLM base URL from config with hardcoded fallback."""
    try:
        from config import get_llm_base_url
        return get_llm_base_url()
    except Exception:
        return "http://localhost:8317/v1"


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


def _try_generate(prompt: str, model: str, timeout: float = 180.0) -> str | None:
    import time as _time

    # Timer
    start_time = _time.time()
    spinner_idx = [0]
    spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def show_spinner(msg=""):
        elapsed = int(_time.time() - start_time)
        sys.stdout.write(
            f"\r[llm][{elapsed}s] {spinner_chars[spinner_idx[0] % 10]} {model[:20]} {msg}"
        )
        sys.stdout.flush()
        spinner_idx[0] += 1

    for attempt in range(2):
        try:
            show_spinner("calling API")
            response = httpx.post(
                f"{_get_llm_base_url()}/chat/completions",
                headers=_get_headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                # For large responses, try to extract JSON from the text
                text = response.text
                sys.stdout.write("\r" + " " * 70 + "\r")
                print(
                    f"[llm] ⚠️ Response not JSON ({len(text)} chars), trying to parse..."
                )
                # Try to find JSON in the response
                import re

                json_match = re.search(r"\{[\s\S]*\}", text)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                    except:
                        return None
                else:
                    return None

            if "choices" not in data:
                elapsed = int(_time.time() - start_time)
                sys.stdout.write("\r" + " " * 70 + "\r")
                print(f"[llm][{elapsed}s] ⚠️ No 'choices' in response")
                if attempt < 1:
                    _time.sleep(3)
                continue

            content = data["choices"][0]["message"].get("content")
            if content:
                elapsed = int(_time.time() - start_time)
                sys.stdout.write("\r" + " " * 70 + "\r")
                print(f"[llm][{elapsed}s] ✅ Done")
                return content.strip()
            elapsed = int(_time.time() - start_time)
            sys.stdout.write("\r" + " " * 70 + "\r")
            if attempt < 1:
                _time.sleep(3)
        except httpx.TimeoutException:
            elapsed = int(_time.time() - start_time)
            sys.stdout.write("\r" + " " * 70 + "\r")
            print(f"[llm][{elapsed}s] ⏱️ Timeout (attempt {attempt + 1}/2)")
            if attempt < 1:
                _time.sleep(3)
        except httpx.HTTPStatusError as e:
            elapsed = int(_time.time() - start_time)
            sys.stdout.write("\r" + " " * 70 + "\r")
            print(f"[llm][{elapsed}s] 🔴 HTTP {e.response.status_code}")
            if e.response.status_code in (502, 503, 504) and attempt < 1:
                _time.sleep(5)
            else:
                return None
        except Exception as e:
            elapsed = int(_time.time() - start_time)
            sys.stdout.write("\r" + " " * 70 + "\r")
            print(f"[llm][{elapsed}s] 🔴 {type(e).__name__}: {str(e)[:50]}")
            if attempt < 1:
                _time.sleep(3)
    elapsed = int(_time.time() - start_time)
    sys.stdout.write("\r" + " " * 70 + "\r")
    return None


def list_models() -> list[str]:
    """Return list of available models from the API"""
    try:
        response = httpx.get(
            f"{_get_llm_base_url()}/models", headers=_get_headers(), timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"[llm] Failed to fetch models: {e}")
        return ["kilo-auto/free", "gpt-4o-free", "gpt-4.1-free"]


def generate_text(prompt: str, model_name: str = None, job: str = None) -> str:
    primary = model_name or _selected_model or "kilo-auto/free"
    candidates = [primary]

    # Job-specific timeouts (seconds) — faster fail-over for slow models
    JOB_TIMEOUTS = {
        "image_prompts": 60.0,
    }
    timeout = JOB_TIMEOUTS.get(job, 180.0)

    # Add fallback models from config or default routing
    if job:
        fallback_chain = get_fallback_chain(job)
        for m in fallback_chain:
            if m != primary and m not in candidates:
                candidates.append(m)
    else:
        # Legacy: add fallback models from same job routing
        if model_name and model_name in MODEL_ROUTING.values():
            for j, models in MODEL_ROUTING.items():
                if primary in models:
                    for m in models:
                        if m != primary and m not in candidates:
                            candidates.append(m)
                    break

    # Ultimate fallbacks
    candidates.extend(["kilo-auto/free", "gpt-4o-free", "gpt-4.1-free"])

    print(f"[llm] Using model: {primary}")
    for model in candidates:
        result = _try_generate(prompt, model, timeout=timeout)
        if result is not None:
            if model != primary:
                print(f"[llm] ↩️ Fell back to: {model}")
            return result

    raise RuntimeError(f"All models failed (tried: {', '.join(candidates)})")


__all__ = [
    "list_models",
    "select_model",
    "get_active_model",
    "generate_text",
    "get_model_for_job",
    "get_fallback_chain",
    "JOBS",
]

JOBS = {
    "topic": "Topic Generation",
    "script": "Script Writing",
    "seo_tags": "SEO Tags",
    "image_prompts": "Image Prompts",
    "title_desc": "Title/Description",
}

MODEL_ROUTING = {
    # Priority: fast/reliable models first, slow/unreliable models last
    "topic": [
        "kilo-auto/free",
        "bytedance-seed/dola-seed-2.0-pro:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "arcee-ai/trinity-large-thinking:free",
    ],
    "script": [
        "kilo-auto/free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "bytedance-seed/dola-seed-2.0-pro:free",
        "arcee-ai/trinity-large-thinking:free",
    ],
    "seo_tags": [
        "kilo-auto/free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "bytedance-seed/dola-seed-2.0-pro:free",
        "arcee-ai/trinity-large-thinking:free",
    ],
    "image_prompts": [
        "gpt-4o-free",
        "kilo-auto/free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
    ],
    "title_desc": [
        "kilo-auto/free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "bytedance-seed/dola-seed-2.0-pro:free",
        "arcee-ai/trinity-large-thinking:free",
    ],
}


def get_model_for_job(job: str) -> str | None:
    """Get the configured model for a job from config, falling back to default routing."""
    # Try config.py first (reads from DB)
    try:
        from config import _get_config
        selected = _get_config(f"model_{job}")
        if selected:
            return selected
    except Exception:
        pass
    
    # Fall back to default routing
    models = MODEL_ROUTING.get(job)
    if models:
        return models[0]
    return None


def get_fallback_chain(job: str) -> list[str]:
    """Get the fallback chain for a job from config or default."""
    import json as _json
    
    # Try config.py first (reads from DB)
    try:
        from config import _get_config
        chain_key = f"model_{job}_fallback"
        stored = _get_config(chain_key)
        if stored:
            if isinstance(stored, list):
                return stored
            # If it's a JSON string, parse it
            if isinstance(stored, str):
                try:
                    return _json.loads(stored)
                except:
                    pass
    except Exception:
        pass
    
    # Return default chain from MODEL_ROUTING
    return MODEL_ROUTING.get(job, [])
