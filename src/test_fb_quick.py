#!/usr/bin/env python3
"""
Quick Facebook upload test - use existing video from .mp directory
"""

import os
import sys
import json

# Add gecko driver to PATH
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Find existing video in .mp directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp_dir = os.path.join(ROOT_DIR, ".mp")
video_files = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]

if not video_files:
    print("ERROR: No video file found in .mp directory")
    sys.exit(1)

# Use the most recent video
video_path = os.path.join(mp_dir, sorted(video_files)[-1])
print(f"Using video: {video_path}")

# Create YouTube instance
fp = get_firefox_profile_path()
print(f"Firefox profile: {fp}")

youtube = YouTube(
    account_uuid="test-fb",
    account_nickname="Test FB",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

# Set video and metadata manually
youtube.video_path = video_path
youtube.metadata = {
    "title": "Test Upload",
    "description": "Test #science",
    "tags": ["science"],
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
print(f"Final: {'SUCCESS - ' + url if success else 'FAILED - ' + str(url)}")

youtube.cleanup()
