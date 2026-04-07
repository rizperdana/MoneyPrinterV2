#!/usr/bin/env python3
"""
Very quick test - wait longer and try more selectors
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
time.sleep(15)

print(f"Current URL: {youtube.browser.current_url}")

# Check page source for video IDs
content = youtube.browser.page_source

# Look for video IDs
patterns = [
    r'video-id="([a-zA-Z0-9_-]{11})"',
    r"/video/([a-zA-Z0-9_-]{11})",
    r'"videoId":"([a-zA-Z0-9_-]{11})"',
    r'"id"\s*:\s*"([a-zA-Z0-9_-]{11})"',
    r'data-video-id="([a-zA-Z0-9_-]{11})"',
]

for pattern in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"Found video IDs with pattern {pattern}: {matches[:5]}")
    else:
        print(f"No matches for pattern: {pattern}")

# Try different selectors
selectors = [
    "a[href*='/video/']",
    "a[href*='watch?v=']",
    "ytcp-video-row",
    "ytd-grid-video-renderer a",
    "ytd-video-renderer a",
    "[href*='/video/']",
]

for sel in selectors:
    try:
        links = youtube.browser.find_elements(By.CSS_SELECTOR, sel)
        if links:
            print(f"Found {len(links)} elements with selector: {sel}")
            for link in links[:3]:
                print(f"  - {link.get_attribute('href')}")
    except Exception as e:
        pass

# Try JavaScript approach
js_result = youtube.browser.execute_script("""
    var links = document.querySelectorAll('a[href*="/video/"], a[href*="watch?v="]');
    var results = [];
    for (var i = 0; i < Math.min(links.length, 10); i++) {
        results.push(links[i].href);
    }
    return results;
""")
print(f"JS found {len(js_result) if js_result else 0} links")
if js_result:
    for link in js_result[:5]:
        print(f"  - {link}")

youtube.cleanup()
