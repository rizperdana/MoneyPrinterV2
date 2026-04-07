#!/usr/bin/env python3
"""
Super quick test - just Facebook upload with timeout
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

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Use existing video
mp_dir = os.path.join(PROJECT_ROOT, ".mp")
video_path = os.path.join(mp_dir, "077c1480-74d2-4438-b9fa-548bdc4b1ffc.mp4")

fp = get_firefox_profile_path()
youtube = YouTube(
    account_uuid="test",
    account_nickname="Test",
    fp_profile_path=fp,
    niche="test",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test FB",
    "description": "Test #fb",
    "tags": ["test"],
}

print("Starting Facebook upload...")

try:
    fb_success, fb_url = youtube.upload_to_facebook()
    print(f"Result: {fb_success} - {fb_url}")
except Exception as e:
    print(f"Error: {e}")
    fb_success, fb_url = False, str(e)

youtube.cleanup()

# Save result
with open("/home/anon/Projects/experiment/MoneyPrinterV2/fb_result.json", "w") as f:
    json.dump({"success": fb_success, "url": fb_url}, f, indent=2)

print(f"\n{'SUCCESS' if fb_success else 'FAILED'}: {fb_url}")
