#!/usr/bin/env python3
"""
Batch pipeline runner - creates videos for multiple niches and uploads to platforms.
"""

import os
import sys
import json
import time
from datetime import datetime

from dotenv import load_dotenv

# Add gecko driver to PATH for selenium
gecko_dir = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0"
os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

# Add src to path before local imports
sys.path.insert(0, os.path.dirname(__file__))

# Load .env before other imports
load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from config import get_firefox_profile_path
from run_pipeline import run_pipeline
from classes.YouTube import YouTube
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload

# Define the niches - mixing popular + niche topics
NICHES = {
    "popular": [
        "mind-blowing science facts",
        "space mysteries explained",
        "shocking history facts",
        "viral biology discoveries",
        "incredible physics phenomena",
    ],
    "niche": [
        "underwater ocean mysteries",
        "ancient technology facts",
        "strange animal behaviors",
        "hidden archaeological discoveries",
        "bizarre weather phenomena",
        "deep sea creatures discovery",
        "abandoned places history",
        "rare astronomical events",
        "unexplained natural phenomena",
        "obscure historical figures",
        "parallel universes explained",
        "simulation theory explained",
        "consciousness mysteries",
        "time paradoxes explained",
        "origin of life theories",
    ],
}

# All niches for the pipeline
ALL_NICHES = NICHES["popular"] + NICHES["niche"]

# Number of videos per niche
VIDEOS_PER_NICHE = 5

RESULTS = []


def upload_to_platforms(video_path: str, title: str, description: str):
    """Upload a video to all platforms and return URLs."""
    fp = get_firefox_profile_path()

    youtube = YouTube(
        account_uuid="batch-upload",
        account_nickname="Batch Upload",
        fp_profile_path=fp,
        niche="science facts",
        locale="en-US",
    )

    youtube.video_path = video_path
    youtube.metadata = {
        "title": title,
        "description": description,
        "tags": ["science", "facts", "viral"],
    }

    results = {}

    # Upload to YouTube
    print("\n=== Uploading to YouTube ===")
    oauth_token = get_access_token("default")
    if not oauth_token:
        yt_success = False
        yt_url = "No OAuth token"
    else:
        try:
            upload_result = youtubeApiUpload(
                video_path=video_path,
                title=title,
                description=description,
                tags=["science", "facts", "viral"],
                oauth_token=oauth_token,
                account_id="default",
                progress_callback=None,
            )
            yt_success = bool(upload_result and upload_result.get("url"))
            yt_url = upload_result.get("url", "") if upload_result else ""
        except Exception as e:
            yt_success = False
            yt_url = str(e)
    results["youtube"] = {"success": yt_success, "url": yt_url}
    print(f"YouTube: {yt_success} - {yt_url}")

    if yt_success:
        time.sleep(2)

    # Upload to TikTok
    print("\n=== Uploading to TikTok ===")
    tt_success, tt_url = youtube.upload_to_tiktok()
    results["tiktok"] = {"success": tt_success, "url": tt_url if tt_success else None}
    print(f"TikTok: {tt_success} - {tt_url}")

    if tt_success:
        time.sleep(2)

    # Upload to Facebook
    print("\n=== Uploading to Facebook ===")
    fb_success, fb_url = youtube.upload_to_facebook()
    results["facebook"] = {"success": fb_success, "url": fb_url if fb_success else None}
    print(f"Facebook: {fb_success} - {fb_url}")

    return results


def main():
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 60)
    print("BATCH VIDEO PIPELINE")
    print("=" * 60)

    created_count = 0

    # Create videos for each niche
    for niche in ALL_NICHES:
        for video_num in range(1, VIDEOS_PER_NICHE + 1):
            print(f"\n{'=' * 60}")
            print(f"Creating video {video_num}/{VIDEOS_PER_NICHE} for: {niche}")
            print(f"{'=' * 60}")

            # Run pipeline (without upload - we'll upload separately)
            result = run_pipeline(
                niche=niche,
                locale="en-US",
                upload=False,  # Generate only first
            )

            if result.get("video_path") and os.path.exists(result["video_path"]):
                created_count += 1

                print(f"\n✓ Video created: {result['video_path']}")
                print(f"  Title: {result.get('title', 'N/A')}")

                # Now upload to platforms
                print(f"\n>>> Uploading to platforms...")
                upload_results = upload_to_platforms(
                    video_path=result["video_path"],
                    title=result.get("title", niche),
                    description=result.get("description", ""),
                )

                result["platforms"] = upload_results
                result["niche"] = niche
                result["video_number"] = video_num
                RESULTS.append(result)

                # Save progress
                with open(os.path.join(ROOT_DIR, "batch_results.json"), "w") as f:
                    json.dump(RESULTS, f, indent=2)
            else:
                print(f"✗ Failed to create video for: {niche}")
                print(f"  Error: {result.get('error', 'Unknown')}")

            # Rate limit between videos
            time.sleep(5)

    print(f"\n{'=' * 60}")
    print(f"COMPLETED: {created_count}/{len(ALL_NICHES)} videos created")
    print(f"{'=' * 60}")

    # Print summary
    print("\nPUBLISHED URLs:")
    for i, res in enumerate(RESULTS):
        print(f"\n{i + 1}. {res.get('title', 'N/A')}")
        platforms = res.get("platforms", {})
        for p, data in platforms.items():
            status = "✓" if data.get("success") else "✗"
            url = data.get("url", "N/A")
            print(f"   {p}: {status} {url}")


if __name__ == "__main__":
    main()
