#!/usr/bin/env python3
"""
Simple YouTube upload test with proper result saving
"""

import os
import sys
import json
import time

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

os.environ["PATH"] = (
    "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0:"
    + os.environ.get("PATH", "")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

video_path = os.path.join(PROJECT_ROOT, ".mp/077c1480-74d2-4438-b9fa-548bdc4b1ffc.mp4")
fp = get_firefox_profile_path()

youtube = YouTube(
    account_uuid="yt-test",
    account_nickname="YT Test",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test " + time.strftime("%Y%m%d %H:%M"),
    "description": "Test",
    "tags": ["test"],
}

print("Testing YouTube upload...")
result = {}

try:
    yt_success, yt_url = youtube.upload_video()
    result = {
        "success": yt_success,
        "url": yt_url,
        "is_valid": "/video/" in yt_url or "youtube.com/watch" in yt_url
        if yt_url
        else False,
    }
    print(f"Result: {yt_success} - {yt_url}")
except Exception as e:
    result = {"success": False, "error": str(e)}
    print(f"Error: {e}")

# Save result
with open(os.path.join(PROJECT_ROOT, "yt_result.json"), "w") as f:
    json.dump(result, f, indent=2)

print(f"Saved: {result}")

youtube.cleanup()
