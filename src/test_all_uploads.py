#!/usr/bin/env python3
"""
Test all platform uploads (YouTube, TikTok, Facebook) using existing video.
"""

import os
import sys
import json
from datetime import datetime

# Add gecko driver to PATH for selenium
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Find existing video in project root .mp directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp_dir = os.path.join(ROOT_DIR, ".mp")

# Find existing video files
video_files = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]
if not video_files:
    print("ERROR: No video file found in .mp directory")
    sys.exit(1)

# Use the most recent video
video_path = os.path.join(mp_dir, sorted(video_files)[-1])
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

# Test all platforms sequentially
results = {}

print("\n" + "=" * 50)
print("Testing YouTube Upload")
print("=" * 50)
yt_success, yt_url = youtube.upload_video()
print(f"YouTube Success: {yt_success}")
print(f"YouTube URL: {yt_url}")
results["youtube"] = {
    "success": yt_success,
    "url": yt_url if yt_success else None,
    "error": yt_url if not yt_success else None,
}

# Save intermediate result
with open(os.path.join(ROOT_DIR, "upload_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 50)
print("Testing TikTok Upload")
print("=" * 50)
tt_success, tt_url = youtube.upload_to_tiktok()
print(f"TikTok Success: {tt_success}")
print(f"TikTok URL: {tt_url}")
results["tiktok"] = {
    "success": tt_success,
    "url": tt_url if tt_success else None,
    "error": tt_url if not tt_success else None,
}

# Save intermediate result
with open(os.path.join(ROOT_DIR, "upload_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 50)
print("Testing Facebook Upload")
print("=" * 50)
fb_success, fb_url = youtube.upload_to_facebook()
print(f"Facebook Success: {fb_success}")
print(f"Facebook URL: {fb_url}")
results["facebook"] = {
    "success": fb_success,
    "url": fb_url if fb_success else None,
    "error": fb_url if not fb_success else None,
}

# Final save
result_data = {
    "timestamp": datetime.now().isoformat(),
    "results": results,
}

result_path = os.path.join(ROOT_DIR, "upload_results.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\n{'=' * 50}")
print("FINAL RESULTS")
print("=" * 50)
print(f"YouTube: {'SUCCESS' if yt_success else 'FAILED'} -> {yt_url}")
print(f"TikTok: {'SUCCESS' if tt_success else 'FAILED'} -> {tt_url}")
print(f"Facebook: {'SUCCESS' if fb_success else 'FAILED'} -> {fb_url}")
print(f"\nResults saved to: {result_path}")

# Cleanup
youtube.cleanup()
