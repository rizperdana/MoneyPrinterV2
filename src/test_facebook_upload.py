#!/usr/bin/env python3
"""
Quick Facebook upload test script
"""

import os
import sys
import json
import time

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

# Test Facebook upload
print("\n=== Testing Facebook Upload ===")
success, url = youtube.upload_to_facebook()
print(f"Facebook Success: {success}")
print(f"Facebook URL: {url}")

# Save results
result_data = {
    "platform": "facebook",
    "success": success,
    "url": url if success else None,
    "error": url if not success else None,
}

result_path = os.path.join(ROOT_DIR, "facebook_test_result.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\nResults saved to: {result_path}")
print(f"Final Facebook URL: {url if success else 'FAILED'}")

# Cleanup
youtube.cleanup()
