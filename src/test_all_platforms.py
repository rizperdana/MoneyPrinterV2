#!/usr/bin/env python3
"""
Full platform upload test - tests upload_to_all_platforms()
"""

import os
import sys
import json
from datetime import datetime

# Add gecko driver to PATH for selenium
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from classes.YouTube import YouTube

# Find existing video in output directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_dir = os.path.join(ROOT_DIR, "output")
video_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]

if not video_files:
    print("ERROR: No video file found in output directory")
    sys.exit(1)

# Use the most recent video
video_path = os.path.join(output_dir, sorted(video_files)[-1])
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

# Test upload to all platforms
print("\n=== Testing All Platforms Upload ===")
print("This will upload to TikTok, Facebook, and YouTube sequentially...")
print("Each platform returns actual post URLs, not base platform URLs\n")

results = youtube.upload_to_all_platforms()

print("\n=== FINAL RESULTS ===")
for platform, (success, result) in results.items():
    status = "SUCCESS" if success else "FAILED"
    print(f"\n{platform.upper()}:")
    print(f"  Status: {status}")
    if success:
        print(f"  URL: {result}")
        # Verify it's not a base URL
        if platform == "youtube" and "watch?v=" in result:
            print(f"  ✓ Actual video URL (not base)")
        elif platform == "tiktok" and "/video/" in result:
            print(f"  ✓ Actual video URL (not base)")
        elif platform == "facebook" and "/reel/" in result:
            print(f"  ✓ Actual reel URL (not base)")
    else:
        print(f"  Error: {result}")

# Save comprehensive results
result_data = {
    "timestamp": datetime.now().isoformat(),
    "youtube": {
        "success": results.get("youtube", (False, ""))[0],
        "url": results.get("youtube", (False, ""))[1]
        if results.get("youtube", (False, ""))[0]
        else None,
    },
    "tiktok": {
        "success": results.get("tiktok", (False, ""))[0],
        "url": results.get("tiktok", (False, ""))[1]
        if results.get("tiktok", (False, ""))[0]
        else None,
    },
    "facebook": {
        "success": results.get("facebook", (False, ""))[0],
        "url": results.get("facebook", (False, ""))[1]
        if results.get("facebook", (False, ""))[0]
        else None,
    },
}

result_path = os.path.join(ROOT_DIR, "upload_results.json")
with open(result_path, "w") as f:
    json.dump(result_data, f, indent=2)

print(f"\n\nResults saved to: {result_path}")

# Final summary
all_success = all(r[0] for r in results.values())
print(f"\n=== SUMMARY ===")
print(f"All uploads successful: {all_success}")

# Show actual URLs
print("\nActual published URLs:")
if results.get("youtube", (False, ""))[0]:
    print(f"  YouTube: {results['youtube'][1]}")
if results.get("tiktok", (False, ""))[0]:
    print(f"  TikTok:  {results['tiktok'][1]}")
if results.get("facebook", (False, ""))[0]:
    print(f"  Facebook: {results['facebook'][1]}")
