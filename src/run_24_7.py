#!/usr/bin/env python3
"""
MoneyPrinterV2 - 24/7 Content Production Runner
Runs the video pipeline continuously with configurable intervals and niches.

Usage:
    python src/run_24_7.py [--interval 7200] [--niches niches.txt] [--output-dir output/]

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
from datetime import datetime
from pathlib import Path

# Load .env before other imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ROOT_DIR, get_verbose
from status import info, success, warning, error

# Default niches if no file provided
DEFAULT_NICHES = [
    "amazing space facts",
    "mind-blowing science discoveries",
    "incredible ocean mysteries",
    "fascinating history facts",
    "amazing animal behaviors",
    "unbelievable technology facts",
    "mysterious deep sea creatures",
    "incredible human body facts",
    "amazing nature phenomena",
    "mind-bending physics facts",
    "ancient civilization mysteries",
    "incredible engineering marvels",
    "surprising psychology facts",
    "amazing astronomical discoveries",
    "fascinating chemistry facts",
    "incredible wildlife adaptations",
    "mind-blowing math facts",
    "amazing geological formations",
    "incredible medical breakthroughs",
    "fascinating cultural traditions",
]


def setup_logging(output_dir: str) -> logging.Logger:
    """Set up file logging for the 24/7 runner."""
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"run_24_7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger = logging.getLogger("mpv2_24_7")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def load_niches(niches_file: str = None) -> list:
    """Load niches from file or use defaults."""
    if niches_file and os.path.exists(niches_file):
        with open(niches_file, "r") as f:
            niches = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return niches
    return DEFAULT_NICHES


def run_single_video(niche: str, output_dir: str, logger: logging.Logger, upload: bool = False) -> dict:
    """Run the pipeline for a single video."""
    from run_pipeline import run_pipeline

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(output_dir, timestamp)
    os.makedirs(video_dir, exist_ok=True)

    logger.info(f"Starting video: {niche}")

    try:
        result = run_pipeline(niche=niche, language="English", upload=upload)

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


def main():
    parser = argparse.ArgumentParser(description="MoneyPrinterV2 24/7 Content Production")
    parser.add_argument("--interval", type=int, default=7200, help="Seconds between videos (default: 7200 = 2 hours)")
    parser.add_argument("--niches", type=str, default=None, help="Path to niches file (one per line)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory (default: .mp/24_7/)")
    parser.add_argument("--max-videos", type=int, default=0, help="Max videos to produce (0 = unlimited)")
    parser.add_argument("--random-order", action="store_true", default=True, help="Randomize niche order")
    parser.add_argument("--no-random-order", action="store_true", help="Use niches in order")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generation")
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

    niches = load_niches(args.niches)
    logger.info(f"Niches loaded: {len(niches)}")

    if args.random_order and not args.no_random_order:
        random.shuffle(niches)

    video_count = 0
    niche_index = 0

    try:
        while True:
            if args.max_videos > 0 and video_count >= args.max_videos:
                logger.info(f"Reached max videos ({args.max_videos}). Stopping.")
                break

            niche = niches[niche_index % len(niches)]
            niche_index += 1

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Video #{video_count + 1}: {niche}")
            logger.info(f"{'=' * 60}")

            result = run_single_video(niche, output_dir, logger, upload=args.upload)

            if result.get("video_path"):
                video_count += 1
                logger.info(f"Total videos produced: {video_count}")
            else:
                logger.warning(f"Video failed, continuing to next...")

            # Reshuffle niches when we've gone through all
            if niche_index >= len(niches):
                random.shuffle(niches)
                niche_index = 0
                logger.info("Reshuffled niches for next cycle")

            # Wait for next video
            if args.max_videos == 0 or video_count < args.max_videos:
                logger.info(f"Waiting {args.interval}s ({args.interval / 60:.0f} min) until next video...")
                time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("\nStopped by user (Ctrl+C)")
        logger.info(f"Total videos produced: {video_count}")

    logger.info("24/7 runner finished.")


if __name__ == "__main__":
    main()
