#!/usr/bin/env python3
"""
Try getting videos from regular YouTube channel page
"""

import os
import sys
import re
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
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

fp = get_firefox_profile_path()
options = Options()
options.add_argument("--headless")
options.add_argument("-profile")
options.add_argument(fp)

browser = webdriver.Firefox(options=options)

try:
    # Try regular YouTube channel videos page
    print("=== Go to YouTube channel videos ===")
    browser.get("https://www.youtube.com/channel/UCFhX7gLJhz7cBMSzIdSgpqg/videos")
    time.sleep(15)
    print(f"URL: {browser.current_url}")

    # Get page source
    content = browser.page_source

    # Try patterns
    patterns = [
        (r'"videoId":"([^"]+)"', "videoId"),
        (r"/video/([a-zA-Z0-9_-]{11})", "/video/"),
        (r"/shorts/([a-zA-Z0-9_-]{11})", "/shorts/"),
    ]

    for pattern, name in patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"{name}: {matches[:3]}")

    # Try JS on regular YouTube
    print("\n=== JS extraction ===")
    js_result = browser.execute_script("""
        var results = [];
        
        // Try finding video links
        var links = document.querySelectorAll('a[href*="/watch?v="], a[href*="/shorts/"]');
        console.log('Found ' + links.length + ' video links');
        
        for (var i = 0; i < Math.min(links.length, 5); i++) {
            results.push(links[i].href);
        }
        
        return results;
    """)
    print(f"Video links: {js_result}")

finally:
    browser.quit()
