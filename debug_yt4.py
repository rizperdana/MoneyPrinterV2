#!/usr/bin/env python3
"""
Check what's actually in the YouTube Studio page
"""

import os
import sys

PROJECT_ROOT = "/home/anon/Projects/experiment/MoneyPrinterV2"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import time
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

from config import get_firefox_profile_path
from classes.YouTube import YouTube

fp = get_firefox_profile_path()
youtube = YouTube(
    account_uuid="test",
    account_nickname="Test",
    fp_profile_path=fp,
    niche="test",
    language="English",
)

# Navigate to videos page directly
print("Navigating to YouTube Studio videos...")
youtube.browser.get("https://studio.youtube.com/videos")
time.sleep(20)

content = youtube.browser.page_source

# Save content for inspection
with open("/tmp/yt_page.html", "w") as f:
    f.write(content[:50000])
print("Saved page content to /tmp/yt_page.html")

# Look for various patterns
patterns = [
    (r'"videoId":"([^"]+)"', "videoId"),
    (r'videoId["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{11})', "videoId = "),
    (r'data-video-id="([^"]+)"', "data-video-id"),
    (r'"id":"([^"]+)"', '"id"'),
    (r"/video/([a-zA-Z0-9_-]{11})", "/video/"),
    (r'"video_id":"([^"]+)"', '"video_id"'),
]

print("\nSearching for video IDs...")
for pattern, name in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"  {name}: {matches[:3]}")
    else:
        print(f"  {name}: none")

# Try getting video from a known uploaded video - let's see if there's a pattern
# Look for the newest video by checking the page structure
js_videos = youtube.browser.execute_script("""
    // Try to find video data in various ways
    var results = [];
    
    // Look in window.__DATA__ or similar
    for (var key in window) {
        if (key.includes('DATA') || key.includes('Video') || key.includes('Grid')) {
            try {
                var val = window[key];
                if (val && typeof val === 'object') {
                    results.push({key: key, type: typeof val});
                }
            } catch(e) {}
        }
    }
    
    return results.slice(0, 10);
""")
print(f"\nWindow data keys found: {js_videos}")

# Try clicking on content and waiting more
print("\nTrying to wait more and check...")
youtube.browser.execute_script("window.scrollTo(0, 1000);")
time.sleep(5)

# Check again
body = youtube.browser.find_element("css selector", "body")
print(f"After scroll, text length: {len(body.text)}")

if body.text:
    print(f"Sample text: {body.text[:300]}")

youtube.cleanup()
