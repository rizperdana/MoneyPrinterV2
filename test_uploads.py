#!/usr/bin/env python3
"""
Test script to generate video and upload to all platforms
"""

import os
import sys

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

from config import get_firefox_profile_path, get_headless
from classes.YouTube import YouTube

# Generate a simple test video if none exists
mp_dir = os.path.join(PROJECT_ROOT, ".mp")
os.makedirs(mp_dir, exist_ok=True)

# Check for existing video or create test video
existing_videos = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]
if existing_videos:
    video_path = os.path.join(mp_dir, existing_videos[0])
    print(f"Using existing video: {video_path}")
else:
    print("ERROR: No video file found. Please generate a video first.")
    sys.exit(1)

fp = get_firefox_profile_path()
print(f"Firefox profile: {fp}")
print(f"Headless: {get_headless()}")

youtube = YouTube(
    account_uuid="test-upload",
    account_nickname="Test Upload",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test Upload - " + datetime.now().strftime("%Y%m%d %H:%M"),
    "description": "Test video upload #science #facts #test",
    "tags": ["science", "facts", "test"],
}

results = {}

# Test YouTube
print("\n=== Testing YouTube Upload ===")
try:
    yt_success, yt_url = youtube.upload_video()
    results["youtube"] = {"success": yt_success, "url": yt_url}
    print(f"YouTube: {yt_success} - {yt_url}")
except Exception as e:
    print(f"YouTube ERROR: {e}")
    results["youtube"] = {"success": False, "error": str(e)}

# Refresh browser state between uploads
print("\n--- Refreshing browser state ---")
youtube.browser.get("about:blank")
time.sleep(2)

# Test TikTok
print("\n=== Testing TikTok Upload ===")
try:
    tt_success, tt_url = youtube.upload_to_tiktok()
    results["tiktok"] = {"success": tt_success, "url": tt_url}
    print(f"TikTok: {tt_success} - {tt_url}")
except Exception as e:
    print(f"TikTok ERROR: {e}")
    results["tiktok"] = {"success": False, "error": str(e)}

# Refresh browser
youtube.browser.get("about:blank")
time.sleep(2)

# Test Facebook
print("\n=== Testing Facebook Upload ===")
try:
    fb_success, fb_url = youtube.upload_to_facebook()
    results["facebook"] = {"success": fb_success, "url": fb_url}
    print(f"Facebook: {fb_success} - {fb_url}")
except Exception as e:
    print(f"Facebook ERROR: {e}")
    results["facebook"] = {"success": False, "error": str(e)}

# Validate URLs
print("\n=== URL Validation ===")
valid = True
for platform, data in results.items():
    if data.get("success"):
        url = data.get("url", "")
        is_valid = False
        if platform == "youtube" and "youtube.com/watch?v=" in url:
            is_valid = True
        elif platform == "tiktok" and "/video/" in url:
            is_valid = True
        elif platform == "facebook" and (
            "/reel/" in url or "/video/" in url or "/watch?v=" in url
        ):
            is_valid = True

        if is_valid:
            print(f"{platform.upper()}: VALID - {url}")
        else:
            print(f"{platform.upper()}: INVALID - {url}")
            valid = False
    else:
        print(f"{platform.upper()}: FAILED - {data.get('error', 'unknown')}")

# Save results
result_path = os.path.join(PROJECT_ROOT, "upload_test_results.json")
with open(result_path, "w") as f:
    json.dump(
        {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "all_valid": valid,
        },
        f,
        indent=2,
    )

print(f"\nResults saved to: {result_path}")

youtube.cleanup()

if valid:
    print("\n✅ ALL UPLOADS SUCCESSFUL WITH VALID URLs!")
else:
    print("\n❌ Some uploads failed or returned invalid URLs")
