# config.json → Database Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SQLite database the single source of truth for all settings. Remove all config.json reading. All code paths read from DB only.

**Architecture:** Remove `_config_json_fallback` from `config.py`. `_load_settings()` returns DB-only. Hardcoded Python defaults serve as fallback when DB key is absent. JSON arrays/dicts auto-deserialized from string storage.

**Tech Stack:** Python, SQLite (in-memory + file), JSON serialization

---

## File Map

| File | Role |
|------|------|
| `src/config.py` | Central config access — DB-only, JSON deserialization, schedule time accessors |
| `src/llm_provider.py` | LLM API calls — remove hardcoded key/URL, use config.py |
| `src/scheduler.py` | Scheduler — remove direct json.load(config.json), use config.py |
| `src/db.py` | DB operations — ensure JSON deserialization, add `get_setting_as_json()` |
| `api/routers/settings.py` | FastAPI settings router — remove hardcoded key/URL |
| `scripts/preflight_local.py` | Preflight checks — use config.py instead of direct file read |
| `scripts/migrate_config_to_db.py` | One-shot migration script (new) |
| `scripts/retry_pending_uploads.py` | May have config.json reference — verify and fix |

---

## Task 1: Update `src/config.py` — DB-Only + JSON Deserialization

**Files:**
- Modify: `src/config.py:1-73`
- Modify: `src/config.py:421` (end of file, add new functions)

- [ ] **Step 1: Replace `_load_settings()` — remove config.json fallback**

```python
def _load_settings() -> dict:
    """
    Load settings from database only.
    Falls back to empty dict if DB unavailable.
    """
    global _settings_cache

    if _settings_cache is None:
        try:
            from src.db import get_settings as _db_get_settings
            _settings_cache = _db_get_settings()
        except Exception:
            _settings_cache = {}

    return _settings_cache
```

- [ ] **Step 2: Add JSON deserialization to `_get_config()`**

Find the function at line 46. Replace the return statement with:

```python
def _get_config(key: str, default=None):
    """Get config value from DB with type coercion and JSON deserialization."""
    settings = _load_settings()
    value = settings.get(key, default)

    # Handle string "true"/"false" to bool conversion
    if value == "true":
        return True
    if value == "false":
        return False

    # Handle numeric strings
    if isinstance(value, str) and value:
        try:
            if "." in value:
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            pass

    # Handle JSON-serialized arrays and dicts
    if isinstance(value, str):
        if value.startswith("[") or value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

    return value
```

- [ ] **Step 3: Update `reload_config()` — remove `_config_json_fallback`**

Replace the function at line 69:

```python
def reload_config() -> None:
    """Force reload settings from database."""
    global _settings_cache
    _settings_cache = None
```

- [ ] **Step 4: Add schedule time defaults and accessors at end of file**

Add before the last line of the file:

```python
# ─── Schedule Time Defaults ────────────────────────────────────────────────────

DEFAULT_YOUTUBE_SCHEDULE_TIMES = ["06:00", "12:00", "18:00"]
DEFAULT_TWITTER_SCHEDULE_TIMES = ["09:00", "15:00", "21:00"]


def get_youtube_schedule_times() -> list:
    """
    Gets the YouTube upload schedule times.

    Returns:
        list: List of time strings, e.g. ["06:00", "12:00", "18:00"]
    """
    return _get_config("youtube_schedule_times", DEFAULT_YOUTUBE_SCHEDULE_TIMES)


def get_twitter_schedule_times() -> list:
    """
    Gets the Twitter posting schedule times.

    Returns:
        list: List of time strings, e.g. ["09:00", "15:00", "21:00"]
    """
    return _get_config("twitter_schedule_times", DEFAULT_TWITTER_SCHEDULE_TIMES)
```

- [ ] **Step 5: Commit**

```bash
git add src/config.py
git commit -m "refactor(config): remove config.json fallback, DB-only with JSON deserialization"
```

---

## Task 2: Update `src/llm_provider.py` — Remove Hardcoded Key and URL

**Files:**
- Modify: `src/llm_provider.py:1-20`
- Modify: `src/llm_provider.py:53` (API call URL)
- Modify: `src/llm_provider.py:130` (models URL)

- [ ] **Step 1: Read full context of hardcoded lines**

Line 12: `_API_KEY = "sk-dIMp6qoD0oWyMvswe"`
Line 13: `_CLIPROXY_BASE = "http://localhost:8317/v1"`

These are used at lines 19-20, 53, and 130.

- [ ] **Step 2: Replace hardcoded key with env var**

Line 12 should become:
```python
_API_KEY = os.environ.get("CLIPROXY_API_KEY", "")
```

- [ ] **Step 3: Replace hardcoded base URL with config lookup**

Line 13 should be removed. Instead, create a helper at module level:

```python
def _get_llm_base_url() -> str:
    """Get LLM base URL from config, with hardcoded fallback."""
    try:
        from config import get_llm_base_url
        return get_llm_base_url()
    except Exception:
        return "http://localhost:8317/v1"
```

- [ ] **Step 4: Update all usages of `_CLIPROXY_BASE`**

Line 53 (in `generate_text()`):
```python
# OLD:
f"{_CLIPROXY_BASE}/chat/completions",
# NEW:
f"{_get_llm_base_url()}/chat/completions",
```

Line 130 (in `get_available_models()`):
```python
# OLD:
f"{_CLIPROXY_BASE}/models", headers=_get_headers(), timeout=30.0
# NEW:
f"{_get_llm_base_url()}/models", headers=_get_headers(), timeout=30.0
```

- [ ] **Step 5: Commit**

```bash
git add src/llm_provider.py
git commit -m "refactor(llm_provider): remove hardcoded API key and base URL"
```

---

## Task 3: Update `src/scheduler.py` — Remove Direct `json.load(config.json)`

**Files:**
- Modify: `src/scheduler.py:257-261`

- [ ] **Step 1: Replace `get_active_model()` — remove direct file read**

Replace the function at line 257:

```python
def get_active_model() -> str:
    """Get the primary model from config."""
    from config import get_default_model
    model = get_default_model()
    return model if model else "xiaomi/mimo-v2-pro:free"
```

- [ ] **Step 2: Verify no other config.json references remain**

Run:
```bash
grep -n "config.json" src/scheduler.py
```
Expected: only the line(s) you just replaced (should be gone). If any remain, fix them.

- [ ] **Step 3: Commit**

```bash
git add src/scheduler.py
git commit -m "refactor(scheduler): use config.py instead of direct config.json read"
```

---

## Task 4: Update `src/db.py` — Ensure JSON Deserialization

**Files:**
- Modify: `src/db.py:464-513`

- [ ] **Step 1: Review `get_setting()` and `get_settings()` — check if JSON deserialization is needed**

Read `db.py` lines 464-513. Currently `get_settings()` returns raw DB strings. Since `_get_config()` now handles JSON deserialization (Task 1), `get_settings()` itself does NOT need to change — the deserialization happens at the config.py layer.

However, verify `get_setting()` (singular) also returns properly:

```python
def get_setting(key: str, default: str = "") -> str:
    _ensure_settings_loaded()
    return _settings_cache.get(key, default)
```

This returns raw string. It's used by `_load_settings()` → `_get_config()` which now deserializes. This is correct.

- [ ] **Step 2: Verify `set_setting()` handles all types correctly**

Current `set_setting()` at line 502 serializes dicts/lists with `json.dumps()`. This is already correct. No changes needed.

- [ ] **Step 3: Commit**

```bash
git add src/db.py
git commit -m "refactor(db): confirm JSON serialization correct — no changes needed"
```

---

## Task 5: Update `api/routers/settings.py` — Remove Hardcoded Key and URL

**Files:**
- Modify: `api/routers/settings.py:140-145`

- [ ] **Step 1: Read context around lines 140-145**

```python
api_key = os.environ.get("CLIPROXY_API_KEY", "sk-dIMp6qoD0oWyMvswe")
base_url = config.get("llm_base_url", "http://localhost:8317")
```

- [ ] **Step 2: Fix hardcoded fallbacks**

```python
api_key = os.environ.get("CLIPROXY_API_KEY", "")
base_url = config.get("llm_base_url", "http://localhost:8317")
```

Remove the hardcoded API key entirely. For base_url, the existing `config.get()` already uses the config module — confirm it reads from `config.py` (which now reads from DB). If it directly reads `config.json`, fix it to use `config._get_config()`.

- [ ] **Step 3: Commit**

```bash
git add api/routers/settings.py
git commit -m "fix(api): remove hardcoded CLIPROXY_API_KEY fallback"
```

---

## Task 6: Update `scripts/preflight_local.py` — Use Config Functions

**Files:**
- Modify: `scripts/preflight_local.py` (line with `config.json` read)

- [ ] **Step 1: Find and replace direct config.json read**

Run:
```bash
grep -n "config.json" scripts/preflight_local.py
```

Read the relevant section and replace with `config._get_config()` or the appropriate named accessor.

- [ ] **Step 2: Commit**

```bash
git add scripts/preflight_local.py
git commit -m "refactor(preflight): use config.py instead of direct config.json read"
```

---

## Task 7: Create `scripts/migrate_config_to_db.py` — One-Shot Migration Script

**Files:**
- Create: `scripts/migrate_config_to_db.py`

- [ ] **Step 1: Write the migration script**

```python
#!/usr/bin/env python3
"""
One-shot migration of config.json settings to database.
Run once to populate DB from config.json, then never again.
Safe to run multiple times (idempotent via ON CONFLICT upserts).
"""
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db import init_db, set_setting, get_settings


def migrate():
    print("Starting config.json → database migration...")

    # Initialize DB (creates tables + runs existing migrations)
    init_db()

    ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
    config_path = os.path.join(ROOT_DIR, "config.json")

    migrated_count = 0
    skipped_count = 0

    # Migrate config.json if it exists
    if os.path.exists(config_path):
        print(f"Reading {config_path}...")
        with open(config_path, "r") as f:
            config = json.load(f)

        for key, value in config.items():
            if isinstance(value, (dict, list)):
                # Serialize complex types
                serialized = json.dumps(value)
                set_setting(key, serialized)
            else:
                set_setting(key, str(value))
            migrated_count += 1
        print(f"Migrated {migrated_count} keys from config.json")
    else:
        print("config.json not found — skipping file import")
        skipped_count += 1

    # Always set defaults for NEW keys (not in config.json)
    import json as json_module

    NEW_KEYS = {
        "youtube_schedule_times": json_module.dumps(["06:00", "12:00", "18:00"]),
        "twitter_schedule_times": json_module.dumps(["09:00", "15:00", "21:00"]),
    }

    for key, default_value in NEW_KEYS.items():
        existing = get_settings().get(key)
        if not existing:
            set_setting(key, default_value)
            print(f"  Set default: {key} = {default_value}")
        else:
            print(f"  Skipped (already set): {key}")

    # Verify
    settings = get_settings()
    print(f"\nDatabase now has {len(settings)} settings")
    print("\nVerification — model keys:")
    for key in ["model_topic", "model_script", "model_seo_tags", "model_image_prompts", "model_title_desc"]:
        print(f"  {key} = {settings.get(key, 'NOT SET')}")

    print("\n✓ Migration complete. config.json is now deprecated.")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/migrate_config_to_db.py
```

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_config_to_db.py
git commit -m "feat: add one-shot config.json → DB migration script"
```

---

## Task 8: Verify — Run Migration and Preflight

**Files:**
- Run: `scripts/migrate_config_to_db.py`
- Run: `scripts/preflight_local.py`
- Run: `python -c "from src.config import _get_config; print('model_script:', _get_config('model_script')); print('tts_voice:', _get_config('tts_voice')); print('youtube_schedule_times:', _get_config('youtube_schedule_times'))"`

- [ ] **Step 1: Run migration script**

```bash
python scripts/migrate_config_to_db.py
```

Expected: Prints migration count, sets defaults, verifies DB has settings.

- [ ] **Step 2: Run preflight**

```bash
python scripts/preflight_local.py
```

Expected: All checks pass, no errors about missing config.

- [ ] **Step 3: Smoke-test config access**

```bash
python -c "
from src.config import _get_config, get_tts_voice, get_youtube_schedule_times
print('model_script:', _get_config('model_script'))
print('tts_voice:', get_tts_voice())
print('youtube_schedule_times:', get_youtube_schedule_times())
print('youtube_schedule_times type:', type(get_youtube_schedule_times()))
"
```

Expected: values from DB, list type for schedule_times.

- [ ] **Step 4: Confirm config.json is never read again**

```bash
grep -rn "config.json" src/ --include="*.py" | grep -v "__pycache__"
```

Expected: zero results (all direct config.json reads should be gone).

- [ ] **Step 5: Commit "verification" as a docs update or skip**

No code changes — just confirmation. Skip commit.

---

## Verification Checklist

After all tasks:

- [ ] `src/config.py` — `_load_settings()` returns DB only, no `_config_json_fallback`
- [ ] `src/config.py` — `_get_config()` deserializes JSON arrays/dicts
- [ ] `src/config.py` — `get_youtube_schedule_times()` and `get_twitter_schedule_times()` exist
- [ ] `src/llm_provider.py` — no hardcoded API key or base URL
- [ ] `src/scheduler.py` — no direct `json.load(config.json)`
- [ ] `api/routers/settings.py` — no hardcoded API key fallback
- [ ] `scripts/preflight_local.py` — no direct config.json read
- [ ] `scripts/migrate_config_to_db.py` — exists and is executable
- [ ] `grep -rn "config.json" src/ --include="*.py"` returns zero results
- [ ] `python scripts/preflight_local.py` passes

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| DB-only (remove config.json fallback) | Task 1 |
| JSON deserialization for arrays/dicts | Task 1 |
| New schedule time config accessors | Task 1 |
| Remove hardcoded API key in llm_provider.py | Task 2 |
| Remove hardcoded base URL in llm_provider.py | Task 2 |
| Remove direct json.load in scheduler.py | Task 3 |
| Remove hardcoded API key in api/routers/settings.py | Task 5 |
| Remove direct config.json read in scripts | Task 6 |
| Migration script | Task 7 |
| Verification | Task 8 |