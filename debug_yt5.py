#!/usr/bin/env python3
"""
Check YouTube Studio Content section
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

# Try going to content section
print("Navigating to YouTube Studio Content...")
youtube.browser.get("https://studio.youtube.com/content")
time.sleep(25)

print(f"Current URL: {youtube.browser.current_url}")

# Check page text
body = youtube.browser.find_element(By.TAG_NAME, "body")
print(f"Page text length: {len(body.text)}")
print(f"Page text sample: {body.text[:500] if body.text else 'empty'}")

# Check page source
content = youtube.browser.page_source

# Save for debugging
with open("/tmp/yt_content.html", "w") as f:
    f.write(content[:80000])
print("\nSaved to /tmp/yt_content.html")

# Look for video patterns
patterns = [
    (r'"videoId":"([^"]+)"', "videoId"),
    (r"/video/([a-zA-Z0-9_-]{11})", "/video/"),
    (r'data-video-id="([^"]+)"', "data-video-id"),
    (r'"id":"([^"]+)"', '"id"'),
]

print("\nSearching for video IDs...")
for pattern, name in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"  {name}: {matches[:5]}")
    else:
        print(f"  {name}: none")

# Try getting video links via JS
js_result = youtube.browser.execute_script("""
    var results = [];
    
    // Try various selectors
    var selectors = [
        'a[href*="/video/"]',
        'a[href*="watch?v="]',
        'a[href*="studio.youtube.com/video"]'
    ];
    
    for (var s = 0; s < selectors.length; s++) {
        var els = document.querySelectorAll(selectors[s]);
        for (var i = 0; i < Math.min(els.length, 5); i++) {
            results.push(els[i].href);
        }
    }
    
    return results.slice(0, 10);
""")
print(f"\nJS found links: {js_result}")

youtube.cleanup()
