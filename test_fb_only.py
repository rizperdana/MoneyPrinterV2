#!/usr/bin/env python3
"""Test just Facebook upload - shorter test"""

import os
import sys

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

os.environ["PATH"] = (
    "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0:"
    + os.environ.get("PATH", "")
)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from config import get_firefox_profile_path
from classes.YouTube import YouTube
import json

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

print("\n=== Testing Facebook Upload ===")
fb_success, fb_url = youtube.upload_to_facebook()
print(f"Facebook: {fb_success} - {fb_url}")

# Validate URL
if fb_success:
    if "/reel/" in fb_url or "/video/" in fb_url or "/post/" in fb_url:
        print("SUCCESS: Valid Facebook URL!")
    else:
        print(f"WARNING: URL may not be valid: {fb_url}")
else:
    print(f"FAILED: {fb_url}")

# Save results
result_data = {
    "facebook": {
        "success": fb_success,
        "url": fb_url if fb_success else None,
        "error": fb_url if not fb_success else None,
    }
}
with open(os.path.join(PROJECT_ROOT, "upload_results.json"), "w") as f:
    json.dump(result_data, f, indent=2)

youtube.cleanup()
