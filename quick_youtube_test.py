#!/usr/bin/env python3
"""
Quick YouTube upload test to verify current behavior
"""

import os
import sys
import time

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

from config import get_firefox_profile_path, get_headless
from classes.YouTube import YouTube

# Use existing video
video_path = os.path.join(
    PROJECT_ROOT, "output/077c1480-74d2-4438-b9fa-548bdc4b1ffc.mp4"
)

if not os.path.exists(video_path):
    print(f"ERROR: Video not found at {video_path}")
    sys.exit(1)

fp = get_firefox_profile_path()
print(f"Firefox profile: {fp}")
print(f"Headless: {get_headless()}")

youtube = YouTube(
    account_uuid="test-youtube",
    account_nickname="Test YouTube",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test YouTube Upload " + time.strftime("%Y%m%d %H:%M"),
    "description": "Test video upload #science #facts #test",
    "tags": ["science", "facts", "test"],
}

print("\n=== Testing YouTube Upload ===")
start = time.time()
yt_success, yt_url = youtube.upload_video()
elapsed = time.time() - start

print(f"\n--- Result ---")
print(f"Success: {yt_success}")
print(f"URL: {yt_url}")
print(f"Elapsed: {elapsed:.1f}s")

# Check if URL is valid
if yt_success:
    if "youtube.com/watch?v=" in yt_url or "youtu.be/" in yt_url:
        print("✓ VALID YouTube URL")
    elif "youtube.com" in yt_url and len(yt_url) > 30:
        print("✓ VALID YouTube URL (alternate format)")
    else:
        print(f"✗ INVALID YouTube URL (base URL returned): {yt_url}")
else:
    print(f"✗ Upload failed: {yt_url}")

youtube.browser.quit()
