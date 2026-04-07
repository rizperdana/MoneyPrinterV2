#!/usr/bin/env python3
"""
Quick test to verify URL extraction after upload - Facebook focused
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

# Use existing video
mp_dir = os.path.join(PROJECT_ROOT, ".mp")
video_path = os.path.join(mp_dir, "077c1480-74d2-4438-b9fa-548bdc4b1ffc.mp4")

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
    "title": "Test FB - " + datetime.now().strftime("%Y%m%d %H:%M"),
    "description": "Test video #science #facts",
    "tags": ["science", "facts"],
}

print("\n=== Testing Facebook ===")
fb_success, fb_url = youtube.upload_to_facebook()
print(f"Facebook: {fb_success} - {fb_url}")

if fb_success:
    print(f"\n✅ Facebook URL: {fb_url}")
    if "/reel/" in fb_url or "/video/" in fb_url:
        print("✅ URL contains actual post path!")
    else:
        print("⚠️ URL may not contain actual post path")
else:
    print(f"\n❌ Facebook failed: {fb_url}")

youtube.cleanup()

# Save result
with open(
    "/home/anon/Projects/experiment/MoneyPrinterV2/fb_test_result.json", "w"
) as f:
    json.dump({"success": fb_success, "url": fb_url}, f, indent=2)
