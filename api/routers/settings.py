"""Settings router — GET/PUT config from database."""

import os
import sys
import json
from dotenv import load_dotenv

_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load .env file
load_dotenv(os.path.join(_project_root, ".env"))

from fastapi import APIRouter

from api.models import SettingsUpdate

router = APIRouter()

# Keys that should be masked when returned via GET
_SENSITIVE_KEYS = {
    "assembly_ai_api_key",
}


def _load_config() -> dict:
    """Load config from database only."""
    from db import get_settings

    db_settings = get_settings()
    if not db_settings:
        return {}

    # Parse JSON values
    result = {}
    for k, v in db_settings.items():
        try:
            result[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            result[k] = v
    return result


def _save_config(config: dict) -> None:
    """Save config to database only."""
    from db import set_setting

    for key, value in config.items():
        if value is not None:
            if isinstance(value, (dict, list)):
                set_setting(key, json.dumps(value))
            else:
                set_setting(key, str(value))


# .env keys to expose via settings API
_ENV_KEYS = [
    "CLIPROXY_API_KEY",
    "CF_ACCOUNT_ID",
    "CF_API_TOKEN",
    "CF_WORKER_URL",
    "CF_WORKER_API_KEY",
    "POLLINATIONS_API_KEY",
    "PIXABAY_API_KEY",
    "ASSEMBLYAI_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "FIRECRAWL_API_KEY",
    "FIREFOX_PROFILE",
    "GEMINI_API_KEY",
]


def _mask_value(value: str) -> str:
    if not value or len(value) < 8:
        return "****" if value else ""
    return value[:4] + "****" + value[-4:]


@router.get("/settings")
async def get_settings():
    """Return current config with .env values and sensitive keys masked."""
    config = _load_config()

    # Merge with .env values
    result = dict(config)
    for key in _ENV_KEYS:
        value = os.environ.get(key, "")
        if value:
            result[key] = value

    # Mask sensitive values
    masked = {}
    for key, value in result.items():
        if key in _SENSITIVE_KEYS and isinstance(value, str) and value:
            masked[key] = _mask_value(value)
        else:
            masked[key] = value
    return masked


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    """Update config in database."""
    config = _load_config()
    updates = body.model_dump(exclude_none=True)
    config.update(updates)
    _save_config(config)
    return {"status": "updated", "fields": list(updates.keys())}


@router.get("/settings/models")
async def get_model_routing() -> dict:
    """Return available models per job type and current fallback chain."""
    import httpx

    config = _load_config()

    # Fetch models from cliproxy API
    available_models = []
    try:
        api_key = os.environ.get("CLIPROXY_API_KEY", "")
        base_url = config.get("llm_base_url", "http://localhost:8317")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        response = httpx.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
        if response.status_code == 200:
            data = response.json()
            available_models = [m["id"] for m in data.get("data", [])]
    except Exception as e:
        print(f"Failed to fetch models: {e}")
        available_models = []

    # Import default fallback chains from llm_provider.py MODEL_ROUTING
    try:
        from src.llm_provider import MODEL_ROUTING as _default_routing
    except Exception:
        _default_routing = {
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
                "kilo-auto/free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "bytedance-seed/dola-seed-2.0-pro:free",
                "arcee-ai/trinity-large-thinking:free",
            ],
            "title_desc": [
                "kilo-auto/free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "bytedance-seed/dola-seed-2.0-pro:free",
                "arcee-ai/trinity-large-thinking:free",
            ],
        }

    # Job names for display
    job_names = {
        "topic": "Topic Research",
        "script": "Script Generation",
        "seo_tags": "SEO Tags",
        "image_prompts": "Image Prompts",
        "title_desc": "Title/Description",
    }

    result = {}
    for job in job_names.keys():
        # Get stored fallback chain or use default from MODEL_ROUTING
        # Handle both list and JSON string formats
        stored_chain = config.get(f"model_{job}_fallback", [])
        if isinstance(stored_chain, str):
            try:
                stored_chain = json.loads(stored_chain)
            except (json.JSONDecodeError, TypeError):
                stored_chain = []
        fallback_chain = stored_chain if stored_chain else _default_routing.get(job, [])

        result[job] = {
            "display_name": job_names.get(job, job),
            "available_models": available_models,
            "fallback_chain": fallback_chain,
            "primary_model": config.get(
                f"model_{job}", fallback_chain[0] if fallback_chain else ""
            ),
        }

    return result
