#!/usr/bin/env python3
"""
Quick test for platform uploads - runs individually with timeout
"""

import os
import sys

# Fix path to find config module
PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

from config import get_firefox_profile_path
from classes.YouTube import YouTube

mp_dir = os.path.join(PROJECT_ROOT, ".mp")
video_files = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]

if not video_files:
    print("ERROR: No video file found")
    sys.exit(1)

video_path = os.path.join(mp_dir, video_files[0])
print(f"Using video: {video_path}")

fp = get_firefox_profile_path()
youtube = YouTube(
    account_uuid="test-upload",
    account_nickname="Test Upload",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test Upload - Science Facts",
    "description": "Test video upload #science #facts",
    "tags": ["science", "facts"],
}

print("\n=== Testing TikTok Upload ===")
try:
    tt_success, tt_url = youtube.upload_to_tiktok()
    print(f"TikTok: {tt_success} - {tt_url}")
except Exception as e:
    print(f"TikTok ERROR: {e}")
    tt_success, tt_url = False, str(e)

print("\n=== Testing Facebook Upload ===")
try:
    fb_success, fb_url = youtube.upload_to_facebook()
    print(f"Facebook: {fb_success} - {fb_url}")
except Exception as e:
    print(f"Facebook ERROR: {e}")
    fb_success, fb_url = False, str(e)

print("\n=== Testing YouTube Upload ===")
try:
    yt_success, yt_url = youtube.upload_video()
    print(f"YouTube: {yt_success} - {yt_url}")
except Exception as e:
    print(f"YouTube ERROR: {e}")
    yt_success, yt_url = False, str(e)

# Save results
result_data = {
    "timestamp": datetime.now().isoformat(),
    "youtube": {
        "success": yt_success,
        "url": yt_url if yt_success else None,
        "error": yt_url if not yt_success else None,
    },
    "tiktok": {
        "success": tt_success,
        "url": tt_url if tt_success else None,
        "error": tt_url if not tt_success else None,
    },
    "facebook": {
        "success": fb_success,
        "url": fb_url if fb_success else None,
        "error": fb_url if not fb_success else None,
    },
}

result_path = os.path.join(PROJECT_ROOT, "upload_results.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\nResults saved to: {result_path}")

# Check if all URLs are actual post URLs
print("\n=== URL Validation ===")
for platform, data in [
    ("YouTube", {"success": yt_success, "url": yt_url}),
    ("TikTok", {"success": tt_success, "url": tt_url}),
    ("Facebook", {"success": fb_success, "url": fb_url}),
]:
    if data["success"]:
        url = data["url"]
        is_valid = False
        if platform == "YouTube" and "youtube.com/watch?v=" in url:
            is_valid = True
        elif platform == "TikTok" and "/video/" in url:
            is_valid = True
        elif platform == "Facebook" and (
            "/reel/" in url or "/video/" in url or "/post/" in url
        ):
            is_valid = True

        if is_valid:
            print(f"{platform}: VALID URL - {url}")
        else:
            print(f"{platform}: INVALID URL - {url}")
    else:
        print(f"{platform}: FAILED - {data.get('url', 'no URL')}")

youtube.cleanup()
