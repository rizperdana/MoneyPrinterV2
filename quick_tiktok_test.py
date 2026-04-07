#!/usr/bin/env python3
"""
Quick TikTok upload test to verify current behavior
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
    PROJECT_ROOT, "output/b3f87bd4-d977-426a-ba92-b6baadcee258.mp4"
)

if not os.path.exists(video_path):
    print(f"ERROR: Video not found at {video_path}")
    sys.exit(1)

fp = get_firefox_profile_path()
print(f"Firefox profile: {fp}")
print(f"Headless: {get_headless()}")

youtube = YouTube(
    account_uuid="test-tiktok",
    account_nickname="Test TikTok",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test TikTok Upload " + time.strftime("%Y%m%d %H:%M"),
    "description": "Test #science #facts",
    "tags": ["science", "facts"],
}

print("\n=== Testing TikTok Upload ===")
start = time.time()
tt_success, tt_url = youtube.upload_to_tiktok()
elapsed = time.time() - start

print(f"\n--- Result ---")
print(f"Success: {tt_success}")
print(f"URL: {tt_url}")
print(f"Elapsed: {elapsed:.1f}s")

# Check if URL is valid
if tt_success:
    if "/video/" in tt_url and "tiktok.com" in tt_url:
        print("✓ VALID TikTok URL")
    else:
        print("✗ INVALID TikTok URL (base URL returned)")
else:
    print(f"✗ Upload failed: {tt_url}")

youtube.browser.quit()
