#!/usr/bin/env python3
"""
Quick upload test script - uses existing video file in output directory
"""

import os
import sys
import json
from datetime import datetime

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

# Find existing video in output directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_dir = os.path.join(ROOT_DIR, "output")
video_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]

if not video_files:
    print("ERROR: No video file found in output directory")
    sys.exit(1)

# Use the most recent video
video_path = os.path.join(output_dir, sorted(video_files)[-1])
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

# Test YouTube upload
print("\n=== Testing YouTube Upload ===")
yt_success, yt_url = youtube.upload_video()
print(f"YouTube Success: {yt_success}")
print(f"YouTube URL: {yt_url}")

# Save results to JSON file
result_data = {
    "timestamp": datetime.now().isoformat(),
    "youtube": {
        "success": yt_success,
        "url": yt_url if yt_success else None,
        "error": yt_url if not yt_success else None,
    },
}

result_path = os.path.join(ROOT_DIR, "upload_results.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\nResults saved to: {result_path}")
print(f"Final YouTube URL: {yt_url if yt_success else 'FAILED'}")
