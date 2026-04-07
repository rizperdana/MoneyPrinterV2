#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Iteration 5
Generate 5 niche videos and upload to all platforms.
"""

import os
import sys
import json
import time

# Add gecko driver to PATH
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from run_pipeline import run_pipeline
from classes.YouTube import YouTube

# 5 Niche topics (more obscure than popular)
NICHES = [
    "underwater ocean mysteries",
    "ancient technology facts",
    "strange animal behaviors",
    "hidden archaeological discoveries",
    "bizarre weather phenomena",
]

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def upload_to_platforms(video_path, title, description):
    """Upload video to YouTube, TikTok, Facebook."""
    fp = get_firefox_profile_path()

    youtube = YouTube(
        account_uuid="ralph-wiggum",
        account_nickname="Ralph Wiggum",
        fp_profile_path=fp,
        niche="niche facts",
        language="English",
    )

    youtube.video_path = video_path
    youtube.metadata = {
        "title": title,
        "description": description,
        "tags": ["niche", "facts", "viral"],
    }

    results = {}

    # YouTube
    print("  → YouTube...")
    yt_ok, yt_url = youtube.upload_video()
    results["youtube"] = {"success": yt_ok, "url": yt_url}
    print(f"    YouTube: {'✓' if yt_ok else '✗'} {yt_url or ''}")
    if yt_ok:
        time.sleep(2)

    # TikTok
    print("  → TikTok...")
    tt_ok, tt_url = youtube.upload_to_tiktok()
    results["tiktok"] = {"success": tt_ok, "url": tt_url}
    print(f"    TikTok: {'✓' if tt_ok else '✗'} {tt_url or ''}")
    if tt_ok:
        time.sleep(2)

    # Facebook
    print("  → Facebook...")
    fb_ok, fb_url = youtube.upload_to_facebook()
    results["facebook"] = {"success": fb_ok, "url": fb_url}
    print(f"    Facebook: {'✓' if fb_ok else '✗'} {fb_url or ''}")

    return results


def main():
    print("=" * 60)
    print("RALPH WIGGUM LOOP - NICHE VIDEO PIPELINE")
    print("=" * 60)

    for i, niche in enumerate(NICHES):
        print(f"\n[{i + 1}/{len(NICHES)}] NICHE: {niche}")
        print("-" * 40)

        # Generate video
        print("  Generating video...")
        result = run_pipeline(
            niche=niche,
            language="English",
            upload=False,
        )

        if not result.get("video_path") or not os.path.exists(result["video_path"]):
            print(f"  ✗ FAILED: {result.get('error', 'Unknown')}")
            continue

        video_path = result["video_path"]
        title = result.get("title", niche)
        desc = result.get("description", "")

        print(f"  ✓ Video: {os.path.basename(video_path)}")
        print(f"    Title: {title}")

        # Upload to platforms
        print("  Uploading to platforms...")
        upload_results = upload_to_platforms(video_path, title, desc)

        # Store result
        result["niche"] = niche
        result["platforms"] = upload_results
        RESULTS.append(result)

        # Save progress
        with open(os.path.join(ROOT_DIR, "batch_results.json"), "w") as f:
            json.dump(RESULTS, f, indent=2)

        print("  → Progress saved")
        time.sleep(3)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY - PUBLISHED URLs")
    print("=" * 60)

    for i, res in enumerate(RESULTS):
        print(f"\n{i + 1}. {res.get('title', 'N/A')}")
        print(f"   Niche: {res.get('niche', 'N/A')}")
        platforms = res.get("platforms", {})
        for p, data in platforms.items():
            status = "✓" if data.get("success") else "✗"
            url = data.get("url") or "N/A"
            print(f"   {p}: {status} {url}")

    return RESULTS


if __name__ == "__main__":
    main()
