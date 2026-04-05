#!/usr/bin/env python3
"""
End-to-end test for MoneyPrinterV2 YouTube Shorts generation.
Bypasses the interactive menu and directly tests the pipeline.
"""
import os
import sys

# Setup paths
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
sys.path.insert(0, SRC_DIR)
os.chdir(PROJECT_DIR)

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

# Ensure CLIPROXY_API_KEY is set
if not os.environ.get('CLIPROXY_API_KEY'):
    os.environ['CLIPROXY_API_KEY'] = 'sk-dIMp6qoD0oWyMvswe'

from uuid import uuid4
from cache import add_account, get_accounts
from classes.YouTube import YouTube
from classes.Tts import TTS
from utils import rem_temp_files, assert_folder_structure
from llm_provider import select_model

# Select a free model before any LLM calls
select_model("kilo-auto/free")

FIREFOX_PROFILE = "/home/anon/.mozilla/firefox/1gb196dc.default-release"

def main():
    print("=" * 60)
    print("MoneyPrinterV2 - End-to-End Test")
    print("=" * 60)

    # Step 1: Ensure folder structure
    print("\n[1/6] Setting up folder structure...")
    assert_folder_structure()
    rem_temp_files()
    print("  OK")

    # Step 2: Setup test account if none exists
    print("\n[2/6] Checking for YouTube account...")
    cached = get_accounts("youtube")
    if not cached:
        account_id = str(uuid4())
        account_data = {
            "id": account_id,
            "nickname": "test-channel",
            "firefox_profile": FIREFOX_PROFILE,
            "niche": "science facts",
            "language": "English",
            "videos": [],
        }
        add_account("youtube", account_data)
        print(f"  Created test account: {account_id}")
        cached = get_accounts("youtube")
    else:
        print(f"  Found {len(cached)} cached account(s)")

    account = cached[0]
    print(f"  Using: {account['nickname']} (niche: {account['niche']})")

    # Step 3: Initialize YouTube class
    print("\n[3/6] Initializing YouTube automation...")
    youtube = YouTube(
        account["id"],
        account["nickname"],
        account["firefox_profile"],
        account["niche"],
        account["language"],
    )
    print("  OK")

    # Step 4: Initialize TTS
    print("\n[4/6] Initializing TTS (EdgeTTS)...")
    tts = TTS()
    print("  OK")

    # Step 5: Generate Video
    print("\n[5/6] Generating video (this may take a few minutes)...")
    print("  - Generating topic...")
    topic = youtube.generate_topic()
    print(f"    Topic: {topic[:80]}...")

    print("  - Generating script...")
    script = youtube.generate_script()
    print(f"    Script: {script[:100]}...")

    print("  - Generating metadata...")
    metadata = youtube.generate_metadata()
    print(f"    Title: {metadata.get('title', 'N/A')}")
    print(f"    Tags: {len(metadata.get('tags', []))} tags")

    print("  - Generating image prompts...")
    prompts = youtube.generate_prompts()
    print(f"    {len(prompts)} image prompts generated")

    print("  - Generating images...")
    for i, prompt in enumerate(prompts):
        print(f"    [{i+1}/{len(prompts)}] {prompt[:60]}...")
        result = youtube.generate_image(prompt)
        if result:
            print(f"      -> {os.path.basename(result)}")
        else:
            print(f"      -> FAILED (will use placeholder)")

    print(f"  - Total images: {len(youtube.images)}")

    print("  - Generating TTS audio...")
    tts_path = youtube.generate_script_to_speech(tts)
    print(f"    -> {os.path.basename(tts_path)}")

    print("  - Combining video...")
    video_path = youtube.combine()
    print(f"    -> {os.path.basename(video_path)}")

    youtube.video_path = os.path.abspath(video_path)

    # Step 6: Verify output
    print("\n[6/6] Verifying output...")
    if os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"  Video file: {video_path}")
        print(f"  Size: {size_mb:.2f} MB")

        # Copy to output folder
        output_dir = os.path.join(PROJECT_DIR, "output")
        os.makedirs(output_dir, exist_ok=True)
        import shutil
        output_path = os.path.join(output_dir, os.path.basename(video_path))
        shutil.copy2(video_path, output_path)
        print(f"  Copied to: {output_path}")

        print("\n" + "=" * 60)
        print("SUCCESS: Video generated successfully!")
        print("=" * 60)
        return True
    else:
        print("  FAILED: Video file not found!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
