#!/usr/bin/env python3
"""
Very quick test - just navigate and check what we see
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
time.sleep(10)

print(f"Current URL: {youtube.browser.current_url}")

# Check page source for video IDs
content = youtube.browser.page_source

# Look for video IDs
patterns = [
    r'video-id="([a-zA-Z0-9_-]{11})"',
    r"/video/([a-zA-Z0-9_-]{11})",
    r'"videoId":"([a-zA-Z0-9_-]{11})"',
]

for pattern in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"Found video IDs with pattern {pattern}: {matches[:5]}")
    else:
        print(f"No matches for pattern: {pattern}")

# Look for links
links = youtube.browser.find_elements("css selector", "a[href*='/video/']")
print(f"Found {len(links)} video links")
for link in links[:3]:
    print(f"  - {link.get_attribute('href')}")

youtube.cleanup()
