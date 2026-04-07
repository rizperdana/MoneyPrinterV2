#!/usr/bin/env python3
"""
Quick TikTok upload test script
"""

import os
import sys
import json

# Add gecko driver to PATH for selenium
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Use existing video in .mp directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
mp_dir = os.path.join(ROOT_DIR, ".mp")

# Find existing video
video_files = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]
if not video_files:
    print("ERROR: No video file found in .mp directory")
    sys.exit(1)

video_path = os.path.join(mp_dir, video_files[0])
print(f"Testing with video: {video_path}")

# Create YouTube instance
fp = get_firefox_profile_path()
print(f"Firefox profile: {fp}")

youtube = YouTube(
    account_uuid="test-upload",
    account_nickname="Test Upload",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

# Set the video path manually for testing
youtube.video_path = video_path
youtube.metadata = {
    "title": "Test Upload - Science Facts",
    "description": "Test video upload #science #facts",
    "tags": ["science", "facts"],
}

print("Starting TikTok upload test...")
success, url = youtube.upload_to_tiktok()
print(f"\n=== TIKTOK RESULT ===")
print(f"Success: {success}")
print(f"URL: {url}")

# Save results
result_data = {
    "platform": "tiktok",
    "success": success,
    "url": url if success else None,
    "error": url if not success else None,
}

result_path = os.path.join(ROOT_DIR, "tiktok_test_result.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\nResults saved to: {result_path}")
