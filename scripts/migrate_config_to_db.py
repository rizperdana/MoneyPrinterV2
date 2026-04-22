#!/usr/bin/env python3
"""
One-shot migration of config.json settings to database.
Run once to populate DB from config.json, then never again.
Safe to run multiple times (idempotent via ON CONFLICT upserts).
"""
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# src/ imports 'from config import ...' — must have root on path BEFORE src/
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

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