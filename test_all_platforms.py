#!/usr/bin/env python3
"""
Test all platform uploads
"""

import os
import sys
import json

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
    account_uuid="test-all",
    account_nickname="Test All",
    fp_profile_path=fp,
    niche="science facts",
    language="English",
)

youtube.video_path = video_path
youtube.metadata = {
    "title": "Test All Platforms",
    "description": "Test video #test",
    "tags": ["test"],
}

results = {}

# Test YouTube
print("=== YouTube ===")
yt_s, yt_u = youtube.upload_video()
results["youtube"] = {"success": yt_s, "url": yt_u}
print(f"Result: {yt_s} - {yt_u}")

# TikTok
print("\n=== TikTok ===")
tt_s, tt_u = youtube.upload_to_tiktok()
results["tiktok"] = {"success": tt_s, "url": tt_u}
print(f"Result: {tt_s} - {tt_u}")

# Facebook
print("\n=== Facebook ===")
fb_s, fb_u = youtube.upload_to_facebook()
results["facebook"] = {"success": fb_s, "url": fb_u}
print(f"Result: {fb_s} - {fb_u}")

# Save
with open(os.path.join(PROJECT_ROOT, "all_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n=== Final Results ===")
for p, r in results.items():
    print(f"{p}: {r['success']} - {r['url']}")

youtube.cleanup()
