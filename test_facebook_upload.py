#!/usr/bin/env python3
"""Facebook-only upload test script. Tests URL extraction improvements."""

import os
import sys

# Add gecko driver to PATH for selenium
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv

load_dotenv(".env")

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Find existing video in .mp directory
mp_dir = ".mp"
video_files = [f for f in os.listdir(mp_dir) if f.endswith(".mp4")]

if not video_files:
    print("ERROR: No video file found")
    sys.exit(1)

video_path = os.path.abspath(os.path.join(mp_dir, video_files[0]))
print(f"Testing with video: {video_path}")

# Create YouTube instance
fp = get_firefox_profile_path()
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

print("Starting Facebook-only upload test...")
success, result = youtube.upload_to_facebook()

print(f"Facebook Result: {success} - {result}")

# Validate URL is not just a base URL
if success:
    if result in ("https://www.facebook.com", "https://facebook.com", ""):
        print("WARNING: Got base URL only, not a specific reel/video URL")
        success = False
        result = "Got base URL only - URL extraction failed"
    elif "/reel/" not in result and "/video/" not in result and "/post/" not in result:
        print(f"WARNING: URL does not contain /reel/, /video/, or /post/: {result}")

print("Cleaning up...")
youtube.cleanup()

sys.exit(0 if success else 1)
