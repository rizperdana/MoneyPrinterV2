#!/usr/bin/env python3
"""
Very quick test - wait longer, scroll, and check more
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
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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

print(f"Current URL: {youtube.browser.current_url}")

# Check if logged in - look for account elements
print("\nChecking for login status...")
account_elements = youtube.browser.find_elements(
    By.CSS_SELECTOR, "img[src*='accounts.google']"
)
print(f"Google account elements: {len(account_elements)}")

# Check for any content at all
body = youtube.browser.find_element(By.TAG_NAME, "body")
print(f"Page text length: {len(body.text)}")

if len(body.text) < 100:
    print("Page seems empty - checking for redirects or login")
    # Check for redirect
    print(f"Current URL: {youtube.browser.current_url}")
else:
    print(f"Page has content: {body.text[:500]}")

# Try scrolling
print("\nTrying to scroll...")
youtube.browser.execute_script("window.scrollTo(0, 500);")
time.sleep(3)

# Check again
content = youtube.browser.page_source

# Look for video IDs - expanded patterns
patterns = [
    r'video-id="([^"]+)"',
    r"/video/([a-zA-Z0-9_-]+)",
    r'"videoId":"([^"]+)"',
    r'data-video-id="([^"]+)"',
    r"videoId=([a-zA-Z0-9_-]+)",
]

print("\nSearching for video IDs in page source...")
for pattern in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"Found matches: {matches[:5]}")
    else:
        print(f"No matches for: {pattern}")

# Try JS to get more info
js_info = youtube.browser.execute_script("""
    return {
        url: window.location.href,
        title: document.title,
        readyState: document.readyState,
        bodyLength: document.body.innerHTML.length
    };
""")
print(f"\nPage info: {js_info}")

youtube.cleanup()
