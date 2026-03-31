#!/usr/bin/env python3
"""
MoneyPrinterV2 - Reddit to Twitter Cron Script
Standalone script for automated Reddit meme → Twitter posting.

Usage:
    python src/reddit_twitter_cron.py <twitter_account_id> <ollama_model>

Designed to be called by the schedule library from main.py or directly
from system cron / scheduler.py.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ROOT_DIR, get_verbose
from status import info, success, warning, error
from cache import get_accounts
from classes.Reddit import Reddit
from classes.Twitter import Twitter
from llm_provider import select_model

# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(ROOT_DIR, ".mp", "reddit_twitter_cron.log")


def setup_logging() -> logging.Logger:
    """Set up logging to file."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logger = logging.getLogger("reddit_twitter_cron")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def run_reddit_twitter_pipeline(account_id: str, model: str) -> bool:
    """
    Fetch the best meme from Reddit and post it to Twitter.

    Args:
        account_id (str): The Twitter account UUID
        model (str): The Ollama model to use for caption generation

    Returns:
        bool: True if successful, False otherwise
    """
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info(f"Reddit→Twitter cron started | account={account_id[:8]}... model={model}")

    # Select the LLM model
    try:
        select_model(model)
    except Exception as e:
        logger.error(f"Failed to select model '{model}': {e}")
        error(f"Failed to select model: {e}")
        return False

    # Find the Twitter account
    accounts = get_accounts("twitter")
    selected_account = None

    for acc in accounts:
        if acc["id"] == account_id:
            selected_account = acc
            break

    if not selected_account:
        logger.error(f"Twitter account {account_id[:8]}... not found in cache")
        error("Twitter account not found in cache.")
        return False

    logger.info(f"Account: {selected_account['nickname']}")

    # Initialize Twitter
    try:
        twitter = Twitter(
            selected_account["id"],
            selected_account["nickname"],
            selected_account["firefox_profile"],
            selected_account["topic"]
        )
    except Exception as e:
        logger.error(f"Failed to initialize Twitter: {e}")
        error(f"Failed to initialize Twitter: {e}")
        return False

    # Initialize Reddit — fetch from popular meme subreddits
    reddit = Reddit(
        subreddits=["memes", "dankmemes", "ProgrammerHumor"],
        limit=25,
        min_score=500
    )

    # Fetch trending posts
    logger.info("Fetching trending posts from Reddit...")
    posts = reddit.fetch_trending_posts()

    if not posts:
        logger.warning("No posts with media found (min_score=500). Trying with lower threshold...")
        # Retry with lower score
        reddit = Reddit(
            subreddits=["memes", "dankmemes", "ProgrammerHumor"],
            limit=25,
            min_score=100
        )
        posts = reddit.fetch_trending_posts()

    if not posts:
        logger.warning("No suitable Reddit posts found. Skipping this run.")
        warning("No suitable Reddit posts found.")
        return False

    # Get the best post
    best_post = reddit.get_best_post()

    if not best_post:
        logger.warning("No best post could be determined.")
        warning("No best post found.")
        reddit.cleanup()
        return False

    logger.info(f"Best post: {best_post.get('title', '')[:80]}")
    logger.info(f"Score: {best_post.get('score', 0):,} | r/{best_post.get('subreddit')}")

    # Download the media
    logger.info("Downloading media...")
    media_path = reddit.download_media(best_post)

    if not media_path:
        logger.error("Failed to download media from Reddit post.")
        error("Failed to download media.")
        reddit.cleanup()
        return False

    logger.info(f"Media downloaded: {media_path}")

    # Generate caption
    caption = twitter.generate_caption_from_reddit(best_post)
    logger.info(f"Caption: {caption[:80]}...")

    # Post to Twitter
    logger.info("Posting to Twitter...")
    result = twitter.post_with_media(caption, media_path)

    if result:
        logger.info("✓ Posted to Twitter successfully!")
        success("Posted to Twitter successfully!")
    else:
        logger.error("✗ Failed to post to Twitter.")
        error("Failed to post to Twitter.")

    # Cleanup temp files
    reddit.cleanup()
    logger.info("Cleanup complete.")
    logger.info("=" * 50)

    return result


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/reddit_twitter_cron.py <twitter_account_id> <ollama_model>")
        print()
        print("Example:")
        print("  python src/reddit_twitter_cron.py abc123-def456 llama3.2:3b")
        sys.exit(1)

    account_id = sys.argv[1]
    model = sys.argv[2]

    success_flag = run_reddit_twitter_pipeline(account_id, model)
    sys.exit(0 if success_flag else 1)
