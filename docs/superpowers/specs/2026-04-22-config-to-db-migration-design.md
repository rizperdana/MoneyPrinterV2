# config.json → Database Migration Design

## Goal

Migrate all settings from `config.json` to SQLite database (`data/moneyprinter.db`). After migration, database is the single source of truth. `config.json` becomes a deprecated artifact (can be deleted or kept as untracked backup).

## Status: One-Way Migration

- DB = authoritative
- config.json = legacy, do not read from after migration
- No export from DB back to config.json

## Scope

All settings currently in `config.json` plus hardcoded values found in code.

### Config Keys (already in DB via import)

| Key | Type | Notes |
|-----|------|-------|
| `verbose` | bool | |
| `firefox_profile` | str | |
| `headless` | bool | |
| `llm_base_url` | str | |
| `llm_model` | str | |
| `twitter_language` | str | |
| `nanobanana2_api_base_url` | str | |
| `nanobanana2_api_key` | str | |
| `nanobanana2_model` | str | |
| `nanobanana2_aspect_ratio` | str | |
| `threads` | int | |
| `zip_url` | str | |
| `is_for_kids` | bool | |
| `google_maps_scraper` | str | |
| `email` | dict | JSON-serialized |
| `google_maps_scraper_niche` | str | |
| `scraper_timeout` | int | |
| `outreach_message_subject` | str | |
| `outreach_message_body_file` | str | |
| `stt_provider` | str | |
| `whisper_model` | str | |
| `whisper_device` | str | |
| `whisper_compute_type` | str | |
| `assembly_ai_api_key` | str | |
| `tts_voice` | str | |
| `font` | str | |
| `imagemagick_path` | str | |
| `script_sentence_length` | int | |
| `tiktok_username` | str | |
| `model_topic` | str | |
| `model_topic_fallback` | list | JSON-serialized |
| `model_script` | str | |
| `model_script_fallback` | list | JSON-serialized |
| `model_seo_tags` | str | |
| `model_seo_tags_fallback` | list | JSON-serialized |
| `model_image_prompts` | str | |
| `model_image_prompts_fallback` | list | JSON-serialized |
| `model_title_desc` | str | |
| `model_title_desc_fallback` | list | JSON-serialized |
| `CLIPROXY_API_KEY` | str | from env override |
| `images_per_video` | int | |
| `google_oauth` | dict | JSON-serialized |

### New Keys (currently hardcoded)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `youtube_schedule_times` | list | `["06:00", "12:00", "18:00"]` | YouTube upload schedule times |
| `twitter_schedule_times` | list | `["09:00", "15:00", "21:00"]` | Twitter posting schedule times |

## Architecture

### Config Layer (config.py)

Current behavior (broken):
```
_load_settings() → DB (if populated) → config.json fallback
```

New behavior:
```
_load_settings() → DB ONLY (no config.json fallback)
```

Remove `_config_json_fallback` entirely. Database is the only source.

### Fallback Behavior

When DB key is missing → use hardcoded Python defaults (not config.json).
Defaults are defined as module-level constants in `config.py` or `llm_provider.py`.
This provides safety for new installs without a config.json.

### JSON Serialization for Complex Types

Arrays/lists and dicts stored as JSON strings in DB.

`config.py:_get_config()` must deserialize JSON strings:
```python
import json

def _get_config(key: str, default=None):
    value = _load_settings().get(key, default)
    # Existing type conversions (bool, int, float)...
    # NEW: detect and deserialize JSON arrays/dicts
    if isinstance(value, str):
        if value.startswith("[") or value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
    return value
```

Same for `db.py:get_setting()`.

## Changes by File

### 1. `src/config.py`

**Remove:**
- `_config_json_fallback` global
- All `config.json` file reading in `_load_settings()`
- `import_config_to_db()` call (no longer needed after migration)

**Change `_load_settings()`:**
```python
def _load_settings() -> dict:
    """Load settings from DB only."""
    global _settings_cache
    if _settings_cache is None:
        try:
            from src.db import get_settings as _db_get_settings
            _settings_cache = _db_get_settings()
        except Exception:
            _settings_cache = {}
    return _settings_cache
```

**Add fallback defaults** as module constants:
```python
DEFAULT_YOUTUBE_SCHEDULE_TIMES = ["06:00", "12:00", "18:00"]
DEFAULT_TWITTER_SCHEDULE_TIMES = ["09:00", "15:00", "21:00"]
```

**Add JSON deserialization** to `_get_config()`.

**Add new config accessors:**
```python
def get_youtube_schedule_times() -> list:
    return _get_config("youtube_schedule_times", DEFAULT_YOUTUBE_SCHEDULE_TIMES)

def get_twitter_schedule_times() -> list:
    return _get_config("twitter_schedule_times", DEFAULT_TWITTER_SCHEDULE_TIMES)
```

### 2. `src/llm_provider.py`

**Remove hardcoded API key (line 12):**
- Do NOT store API key in code — use `os.environ.get("CLIPROXY_API_KEY")`

**Remove hardcoded base URL (line 13):**
- Use `config._get_config("llm_base_url")` instead

**Change `get_model_for_job()`:**
- Falls back to `MODEL_ROUTING[job][0]` when DB returns nothing
- This fallback is intentional — it's the safety net, not the primary path

**Keep `MODEL_ROUTING` dict** as hardcoded fallback defaults. These serve as last-resort safety nets.

### 3. `src/scheduler.py`

**Fix line 259** — remove direct `json.load(config.json)`:
```python
# OLD (line ~259):
with open(config_path) as f:
    config = json.load(f)
llm_model = config.get("llm_model", "xiaomi/mimo-v2-pro:free")

# NEW:
from config import _get_config
llm_model = _get_config("llm_model", "xiaomi/mimo-v2-pro:free")
```

**Use config accessors** for schedule times:
```python
from config import get_youtube_schedule_times, get_twitter_schedule_times
youtube_times = get_youtube_schedule_times()
twitter_times = get_twitter_schedule_times()
```

### 4. `src/classes/YouTube.py`

*(No changes needed — OAuth handles auth, no selenium/geckodriver)*

### 5. `src/db.py`

**Ensure JSON deserialization works for arrays/dicts** — values returned from `get_settings()` should be deserialized where needed.

**Add `get_setting_as_json()`** — explicitly deserialize if value looks like JSON, for cases where caller needs the parsed form.

### 6. `api/routers/settings.py`

**Remove hardcoded API key (line ~142) and base URL fallback:**
- Use `os.environ.get("CLIPROXY_API_KEY")` instead of hardcoded value
- Use `config._get_config("llm_base_url")` for base URL

### 7. `scripts/preflight_local.py`

**Remove direct `config.json` references:**
- Use `config._get_config("llm_base_url")` for URL check

### 8. `scripts/retry_pending_uploads.py`

**Remove `config.json` path reference** — already reads from config via config.py

## Migration Script

Create `scripts/migrate_config_to_db.py` that:

1. Reads existing `config.json` (if present)
2. Inserts all keys into DB `settings` table (overwriting existing)
3. Sets NEW keys (schedule times) with defaults
4. Prints summary of what was migrated
5. Can be run multiple times safely (idempotent via `ON CONFLICT` upserts)

```python
# Key behavior: sets defaults for new keys even if config.json doesn't have them
NEW_KEYS = {
    "youtube_schedule_times": json.dumps(["06:00", "12:00", "18:00"]),
    "twitter_schedule_times": json.dumps(["09:00", "15:00", "21:00"]),
}
```

## Verification

After migration, run:

```bash
python scripts/migrate_config_to_db.py
python scripts/preflight_local.py
python src/main.py  # smoke test
```

All settings should come from DB. `config.json` should never be read by any code path after the migration changes.

## Files to Modify

| File | Change |
|------|--------|
| `src/config.py` | Remove config.json fallback, add JSON deserialization, add new schedule time config accessors with defaults |
| `src/llm_provider.py` | Remove hardcoded API key and base URL, use config functions |
| `src/scheduler.py` | Remove direct json.load, use config functions |
| `src/db.py` | Ensure JSON deserialization works for arrays/dicts |
| `api/routers/settings.py` | Remove hardcoded API key and base URL |
| `scripts/preflight_local.py` | Use config functions instead of direct config.json |
| `scripts/migrate_config_to_db.py` | New migration script |

## Out of Scope

- `config.example.json` — keep as template for new users, but it should reference DB-only setup
- `.env` file handling — API keys remain in environment variables as already done
- Any new admin UI for settings — current DB is sufficient
- Selenium/geckodriver — OAuth handles authentication, no browser automation needed