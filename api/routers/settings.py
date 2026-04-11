"""Settings router — GET/PUT config.json with masked keys."""

import os
import sys
import json

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter

from api.models import SettingsUpdate

router = APIRouter()

# Keys that should be masked when returned via GET
_SENSITIVE_KEYS = {
    "nanobanana2_api_key",
    "assembly_ai_api_key",
}

_CONFIG_PATH = os.path.join(_project_root, "config.json")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _mask_value(value: str) -> str:
    if not value or len(value) < 8:
        return "****" if value else ""
    return value[:4] + "****" + value[-4:]


@router.get("/settings")
async def get_settings():
    """Return current config with sensitive values masked."""
    config = _load_config()
    masked = {}
    for key, value in config.items():
        if key in _SENSITIVE_KEYS and isinstance(value, str) and value:
            masked[key] = _mask_value(value)
        else:
            masked[key] = value
    return masked


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    """Update config.json with provided values."""
    config = _load_config()
    updates = body.model_dump(exclude_none=True)
    config.update(updates)
    _save_config(config)
    return {"status": "updated", "fields": list(updates.keys())}
