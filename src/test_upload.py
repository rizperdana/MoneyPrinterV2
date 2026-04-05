#!/usr/bin/env python3
"""
Quick upload test script - uses existing video file in .mp directory
"""

import os
import sys

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

# Check final .mp directory state
remaining = os.listdir(mp_dir)
print(f"\nFiles remaining in .mp after cleanup: {remaining}")
