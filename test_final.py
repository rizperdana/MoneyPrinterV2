#!/usr/bin/env python3
"""
Final test - check all platform upload capabilities
"""

import os
import sys
import json

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

os.environ["PATH"] = (
    "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0:"
    + os.environ.get("PATH", "")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

video_path = os.path.join(PROJECT_ROOT, ".mp/b3f87bd4-d977-426a-ba92-b6baadcee258.mp4")
fp = get_firefox_profile_path()

youtube = YouTube(
    account_uuid="final-test",
    account_nickname="Final Test",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Final Test "
    + __import__("datetime").datetime.now().strftime("%Y%m%d %H:%M"),
    "description": "Final test #test",
    "tags": ["test"],
}

results = {}

# Test YouTube
print("=== Testing YouTube ===")
try:
    yt_success, yt_url = youtube.upload_video()
    results["youtube"] = {
        "success": yt_success,
        "url": yt_url,
        "is_valid_url": "/video/" in yt_url or "youtube.com/watch" in yt_url,
    }
    print(f"YouTube: {yt_success} - {yt_url[:80] if yt_url else 'N/A'}")
except Exception as e:
    results["youtube"] = {"success": False, "error": str(e)}
    print(f"YouTube Error: {e}")

# Test TikTok
print("\n=== Testing TikTok ===")
try:
    tt_success, tt_url = youtube.upload_to_tiktok()
    results["tiktok"] = {
        "success": tt_success,
        "url": tt_url,
        "is_valid_url": "/video/" in tt_url,
    }
    print(f"TikTok: {tt_success} - {tt_url[:80] if tt_url else 'N/A'}")
except Exception as e:
    results["tiktok"] = {"success": False, "error": str(e)}
    print(f"TikTok Error: {e}")

# Test Facebook
print("\n=== Testing Facebook ===")
try:
    fb_success, fb_url = youtube.upload_to_facebook()
    results["facebook"] = {
        "success": fb_success,
        "url": fb_url,
        "is_valid_url": "/reel/" in fb_url or "/video/" in fb_url,
    }
    print(f"Facebook: {fb_success} - {fb_url[:80] if fb_url else 'N/A'}")
except Exception as e:
    results["facebook"] = {"success": False, "error": str(e)}
    print(f"Facebook Error: {e}")

# Save
with open(os.path.join(PROJECT_ROOT, "final_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n=== Summary ===")
for platform in ["youtube", "tiktok", "facebook"]:
    r = results.get(platform, {})
    status = "✅" if r.get("success") and r.get("is_valid_url") else "❌"
    print(
        f"{status} {platform}: success={r.get('success')}, valid_url={r.get('is_valid_url')}"
    )

youtube.cleanup()
