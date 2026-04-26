#!/usr/bin/env python3
"""
MoneyPrinterV2 - 24/7 Content Production Runner
Runs the video pipeline using round-robin across DB accounts and their topics.
Uses model settings from DB.

Usage:
    python src/run_24_7.py [--interval 3600] [--output-dir output/] [--upload]

Environment:
    Same as run_pipeline.py — loads .env automatically
"""

import os
import sys
import json
import time
import random
import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path so 'from src.*' imports work
ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

load_dotenv(ROOT_DIR / ".env")

from src.config import get_verbose
from src.status import info, success, warning, error


def setup_logging(output_dir: str) -> logging.Logger:
    """Set up file logging for the 24/7 runner."""
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir, f"run_24_7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger("mpv2_24_7")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger



def run_single_video(
    niche: str,
    output_dir: str,
    logger: logging.Logger,
    upload: bool = False,
    locale: str = "en-US",
    audience: str = "general",
) -> dict:
    """Run the pipeline for a single video."""
    from src.run_pipeline import run_pipeline

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(output_dir, timestamp)
    os.makedirs(video_dir, exist_ok=True)

    logger.info(f"Starting video: {niche} (locale={locale})")

    try:
        result = run_pipeline(
            niche=niche, locale=locale, upload=upload, audience=audience
        )

        if result.get("video_path"):
            # Move video to output directory
            src = result["video_path"]
            dst = os.path.join(video_dir, "video.mp4")
            if os.path.exists(src):
                import shutil

                shutil.copy2(src, dst)
                result["video_path"] = dst

            # Save metadata
            meta_path = os.path.join(video_dir, "metadata.json")
            with open(meta_path, "w") as f:
                json.dump(result, f, indent=2)

            size_mb = os.path.getsize(dst) / 1024 / 1024
            logger.info(f"Video saved: {dst} ({size_mb:.1f} MB)")
            logger.info(f"Title: {result.get('title', 'N/A')}")
            logger.info(f"Tags: {len(result.get('tags', []))} tags")
        else:
            logger.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"Pipeline exception: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return {"error": str(e)}


def cleanup_old_files(output_dir: str, max_age_days: int = 7):
    """Remove old video files to free disk space."""
    import glob
    import time

    now = time.time()
    cutoff = now - (max_age_days * 86400)

    removed = 0
    for pattern in ["*.mp4", "*.wav", "*.png", "*.srt"]:
        for f in glob.glob(os.path.join(output_dir, "**", pattern), recursive=True):
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
                removed += 1

    if removed > 0:
        info(f"Cleaned up {removed} old files (>{max_age_days} days)")


def check_disk_space(min_gb: float = 2.0) -> bool:
    """Check if enough disk space is available."""
    total, used, free = shutil.disk_usage(ROOT_DIR)
    free_gb = free / (1024**3)

    if free_gb < min_gb:
        warning(f"Low disk space: {free_gb:.1f} GB free (minimum: {min_gb} GB)")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="MoneyPrinterV2 24/7 Content Production"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between videos (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: .mp/24_7/)",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=0,
        help="Max videos to produce (0 = unlimited)",
    )
    parser.add_argument(
        "--upload", action="store_true", help="Upload to YouTube after generation"
    )
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(ROOT_DIR, ".mp", "24_7")
    os.makedirs(output_dir, exist_ok=True)

    logger = setup_logging(output_dir)
    logger.info("=" * 60)
    logger.info("MoneyPrinterV2 - 24/7 Content Production")
    logger.info("=" * 60)
    logger.info(f"Interval: {args.interval}s ({args.interval / 60:.0f} min)")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Max videos: {args.max_videos or 'unlimited'}")

    # Load settings from DB
    from src.db import get_settings, get_accounts, init_db, add_video, update_video_youtube_url
    init_db()
    settings = get_settings()
    
    # Get default language from settings
    default_language = settings.get("twitter_language", "English")
    logger.info(f"Default language: {default_language}")

    # Get accounts with topics and shuffle to ensure rotation
    accounts = get_accounts()
    # Filter to only accounts with topic
    accounts = [a for a in accounts if a.get("topic")]
    # Shuffle to break deterministic ORDER BY created_at DESC ordering
    random.shuffle(accounts)
    
    if not accounts:
        logger.error("No accounts with topic found in DB. Add accounts with topics first.")
        return
    
    logger.info(f"Accounts loaded: {len(accounts)}")
    for a in accounts:
        logger.info(f"  - {a['username']}: {a.get('topic')} (locale: {a.get('locale') or default_language})")

    # Round-robin state
    account_index = 0
    video_count = 0

    try:
        while True:
            if args.max_videos > 0 and video_count >= args.max_videos:
                logger.info(f"Reached max videos ({args.max_videos}). Stopping.")
                break

            # Round-robin through accounts
            account = accounts[account_index % len(accounts)]
            account_index += 1
            
            topic = account.get("topic")
            locale = account.get("locale") or default_language
            account_name = account.get("username")
            
            if not topic:
                logger.warning(f"Account {account_name} has no topic, skipping...")
                continue

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Video #{video_count + 1}")
            logger.info(f"Account: {account_name}")
            logger.info(f"Topic: {topic}")
            logger.info(f"Locale: {locale}")
            logger.info(f"{'=' * 60}")

            # Check disk space before generating
            if not check_disk_space():
                logger.error("Insufficient disk space. Cleaning up and waiting...")
                cleanup_old_files(output_dir, max_age_days=1)
                if not check_disk_space(min_gb=1.0):
                    logger.error("Critical disk space. Stopping.")
                    break

            # Retry up to 3 times on failure
            result = None
            for attempt in range(3):
                result = run_single_video(topic, output_dir, logger, upload=args.upload, locale=locale)
                if result.get("video_path"):
                    break
                logger.warning(
                    f"Attempt {attempt + 1}/3 failed: {result.get('error', 'Unknown')}"
                )
                if attempt < 2:
                    logger.info("Retrying in 60 seconds...")
                    time.sleep(60)

            if result.get("video_path"):
                video_count += 1
                
                # Save to DB
                vid = add_video(
                    niche=topic,
                    topic=topic,
                    locale=locale,
                    title=result.get("title", ""),
                    description=result.get("description", ""),
                    script=result.get("script", ""),
                    tags=",".join(result.get("tags", [])),
                    file_path=result["video_path"],
                    platform="youtube",
                    account=account_name,
                )
                logger.info(f"Video saved to DB (ID: {vid})")
                
                # Update YouTube URL if uploaded
                if result.get("uploaded") and result.get("youtube_url"):
                    update_video_youtube_url(vid, result["youtube_url"])
                    logger.info(f"Uploaded: {result['youtube_url']}")
                
                logger.info(f"Total videos produced: {video_count}")
            else:
                logger.error(
                    f"Video failed after 3 attempts, skipping to next account..."
                )

            # Cleanup old files periodically
            if video_count % 5 == 0:
                cleanup_old_files(output_dir)

            # Wait for next video
            if args.max_videos == 0 or video_count < args.max_videos:
                logger.info(
                    f"Waiting {args.interval}s ({args.interval / 60:.0f} min) until next video..."
                )
                time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("\nStopped by user (Ctrl+C)")
        logger.info(f"Total videos produced: {video_count}")

    logger.info("24/7 runner finished.")


if __name__ == "__main__":
    main()
