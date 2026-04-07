#!/usr/bin/env python3
"""
Quick upload test script - uses existing video file in .mp directory
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

# Find existing video in .mp directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp_dir = os.path.join(ROOT_DIR, ".mp")
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

print("Starting upload_to_all_platforms test...")
results = youtube.upload_to_all_platforms()

print("\n=== UPLOAD RESULTS ===")
for platform, (success, result) in results.items():
    print(f"{platform}: {'SUCCESS' if success else 'FAILED'} - {result}")

# Save results to JSON file for external consumption
result_data = {
    "timestamp": datetime.now().isoformat(),
    "youtube": {
        "success": results.get("youtube", (False, ""))[0],
        "url": results.get("youtube", (False, ""))[1]
        if results.get("youtube", (False, ""))[0]
        else None,
        "error": results.get("youtube", (False, ""))[1]
        if not results.get("youtube", (False, ""))[0]
        else None,
    },
    "tiktok": {
        "success": results.get("tiktok", (False, ""))[0],
        "url": results.get("tiktok", (False, ""))[1]
        if results.get("tiktok", (False, ""))[0]
        else None,
        "error": results.get("tiktok", (False, ""))[1]
        if not results.get("tiktok", (False, ""))[0]
        else None,
    },
    "facebook": {
        "success": results.get("facebook", (False, ""))[0],
        "url": results.get("facebook", (False, ""))[1]
        if results.get("facebook", (False, ""))[0]
        else None,
        "error": results.get("facebook", (False, ""))[1]
        if not results.get("facebook", (False, ""))[0]
        else None,
    },
}

result_path = os.path.join(ROOT_DIR, "upload_results.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\nResults saved to: {result_path}")

# Check final .mp directory state
remaining = os.listdir(mp_dir)
print(f"\nFiles remaining in .mp after cleanup: {remaining}")
