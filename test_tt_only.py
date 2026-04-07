#!/usr/bin/env python3
"""
Quick test - minimal: just test TikTok URL extraction first
"""

import os
import sys

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

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

print(f"Using video: {video_path}")

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
    "title": "Test TT - " + datetime.now().strftime("%H%M"),
    "description": "Test #test",
    "tags": ["test"],
}

print("\n=== Testing TikTok ===")
try:
    tt_success, tt_url = youtube.upload_to_tiktok()
    print(f"Result: {tt_success} - {tt_url}")
except Exception as e:
    print(f"Error: {e}")
    tt_success, tt_url = False, str(e)

youtube.cleanup()

# Save result
import json

with open("/home/anon/Projects/experiment/MoneyPrinterV2/tt_result.json", "w") as f:
    json.dump({"success": tt_success, "url": tt_url}, f, indent=2)

if tt_success:
    print(f"✅ TikTok URL: {tt_url}")
else:
    print(f"❌ TikTok failed")
