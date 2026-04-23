#!/usr/bin/env python3
"""Retry pending YouTube uploads using the API method."""
import sys, os
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.config import get_firefox_profile_path
from src.db import get_videos, init_db, update_video_youtube_url
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload

fp = get_firefox_profile_path()

init_db()
videos = get_videos()

pending = [
    v for v in videos
    if not v.get("youtube_url")
    and v.get("file_path")
    and os.path.exists(v.get("file_path", ""))
]

print(f"Found {len(pending)} pending uploads\n")

oauth_token = get_access_token("default")
if not oauth_token:
    print("❌ No OAuth token available")
    sys.exit(1)

for video in pending:
    video_id = video["id"]
    niche = video.get("niche", "unknown")
    file_path = video["file_path"]
    title = video.get("title", niche) or niche

    print(f"=== Retrying upload ID={video_id} ===")
    print(f"  Niche: {niche}")
    print(f"  File: {file_path}")
    print(f"  Title: {title[:60]}...")

    try:
        result = youtubeApiUpload(
            video_path=file_path,
            title=title[:100],
            description=video.get("description", "") or "",
            tags=video.get("tags", []) or [],
            oauth_token=oauth_token,
            account_id="default",
            progress_callback=None,
        )
        if result and result.get("url"):
            print(f"  ✅ SUCCESS: {result['url']}")
            update_video_youtube_url(video_id, result["url"])
        else:
            print(f"  ❌ FAILED: No result returned")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")

    print()