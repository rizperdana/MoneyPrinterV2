#!/usr/bin/env python3
"""
Test script to verify YouTube, Facebook, and TikTok uploads.
Run with: python3 test_uploads.py
"""

import os
import sys
import json
import time

# Add src to path - use correct relative path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
sys.path.insert(0, src_dir)

from classes.YouTube import YouTube
from cache import get_accounts
from config import get_verbose
from llm_provider import select_model, get_active_model


def main():
    """Test the upload functionality to all platforms."""

    # Select the model first
    model = "kilo-auto/free"
    select_model(model)
    print(f"Using model: {model}")

    # Get YouTube account
    accounts = get_accounts("youtube")

    if not accounts:
        print("ERROR: No YouTube accounts found. Please set up an account first.")
        sys.exit(1)

    account = accounts[0]
    print(f"Using account: {account['nickname']}")

    # Create YouTube instance
    youtube = YouTube(
        account["id"],
        account["nickname"],
        account["firefox_profile"],
        account["niche"],
        account["language"],
    )

    try:
        # Use existing video if available
        existing_video = os.path.join(
            script_dir, ".mp", "bb0c4d03-2c2c-4970-a1c1-eca56e6c7566.mp4"
        )

        if not os.path.exists(existing_video):
            # Generate video
            print("\n=== Generating Video ===")
            from classes.Tts import TTS

            tts = TTS()
            youtube.generate_video(tts)
            print(f"Video generated: {youtube.video_path}")
        else:
            # Use existing video
            youtube.video_path = existing_video
            youtube.subject = "Venus Facts"
            youtube.metadata = {
                "title": "Venus Day Longer Than Year",
                "description": "Interesting facts about Venus #science",
                "tags": ["venus", "science", "facts"],
            }
            print(f"Using existing video: {youtube.video_path}")

        # Upload to all platforms
        print("\n=== Uploading to All Platforms ===")
        results = youtube.upload_to_all_platforms()

        print("\n=== Results ===")
        for platform, (success, url) in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"{platform}: {status}")
            if success:
                print(f"  URL: {url}")
            else:
                print(f"  Error: {url}")

        # Save results
        result_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "youtube": {
                "success": results.get("youtube", (False, ""))[0],
                "url": results.get("youtube", (False, ""))[1],
            },
            "tiktok": {
                "success": results.get("tiktok", (False, ""))[0],
                "url": results.get("tiktok", (False, ""))[1],
            },
            "facebook": {
                "success": results.get("facebook", (False, ""))[0],
                "url": results.get("facebook", (False, ""))[1],
            },
        }

        with open("upload_results.json", "w") as f:
            json.dump(result_data, f, indent=2)

        print(f"\nResults saved to upload_results.json")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup
        youtube.cleanup()


if __name__ == "__main__":
    main()
