#!/usr/bin/env python3
"""
Quick test to verify URL extraction after upload
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
    "title": "Test Upload - " + datetime.now().strftime("%Y%m%d %H:%M"),
    "description": "Test video upload #science #facts",
    "tags": ["science", "facts"],
}

print("\n=== Testing YouTube ===")
yt_success, yt_url = youtube.upload_video()
print(f"YouTube: {yt_success} - {yt_url}")

if yt_success:
    print(f"\n✅ YouTube URL: {yt_url}")
else:
    print(f"\n❌ YouTube failed: {yt_url}")

youtube.cleanup()
