#!/usr/bin/env python3
"""
24/7 round-robin video generator.
Runs pipeline with topic rotation across YouTube accounts.
"""
import sys, os, json, logging, datetime
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Logging
log_dir = ROOT / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"run_24h_{datetime.date.today().isoformat()}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

DARK_NICHES = [
    "unsolved mysteries & internet rabbit holes",
    "deep sea anomalies & thalassophobia",
    "glitches in the matrix & mandela effects",
    "cosmic horror & space anomalies",
    "dark psychology & behavioral facts",
    "abandoned mega-projects & ghost towns",
    "forbidden places you can't visit",
    "survival facts & what to do if",
    "mythology & ancient curses",
    "dystopian tech & futurism",
]

STATE_FILE = Path.home() / ".mp" / "24h_state.json"
CACHE_FILE = ROOT / ".mp" / "youtube.json"


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_index": {}, "total_runs": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_accounts():
    if not CACHE_FILE.exists():
        logger.error(f"Account cache not found: {CACHE_FILE}")
        return []
    with open(CACHE_FILE) as f:
        data = json.load(f)
    # Handle both {"accounts": [...]} and [...] formats
    if isinstance(data, dict) and "accounts" in data:
        return data["accounts"]
    return data if isinstance(data, list) else []


def get_next_topic(account, state):
    """Get next topic for account using round-robin."""
    account_id = account["id"]
    topics = account.get("topics", [])
    if not topics:
        topics = DARK_NICHES

    last_idx = state.get("last_index", {}).get(account_id, -1)
    next_idx = (last_idx + 1) % len(topics)
    state["last_index"][account_id] = next_idx
    return topics[next_idx]


def add_video(niche, language, topic, title, description, script, tags, video_path, platform="youtube", account_id=None):
    """Add a generated video to the DB."""
    from src.db import add_video as db_add_video
    return db_add_video(
        niche=niche,
        account=account_id,
        title=title,
        description=description,
        script=script,
        tags=",".join(tags) if tags else "",
        platform=platform,
        file_path=video_path,
        language=language,
    )


def main():
    from src.run_pipeline import run_pipeline
    from src.db import init_db, update_video_youtube_url

    init_db()
    state = load_state()
    accounts = load_accounts()

    if not accounts:
        logger.error("No accounts found in .mp/youtube.json")
        return

    # Pick the account with fewest runs (round-robin across accounts too)
    account = min(accounts, key=lambda a: state.get("last_index", {}).get(a["id"], -1))
    topic = get_next_topic(account, state)
    language = account.get("language", "English")
    account_id = account.get("id")

    logger.info(f"=== Run #{state['total_runs'] + 1} ===")
    logger.info(f"Account: {account['username']} ({account_id[:8]}...)")
    logger.info(f"Topic: {topic}")

    try:
        result = run_pipeline(
            niche=topic,
            language=language,
            upload=True,  # Always upload
            headless=True,
        )

        if result.get("error"):
            logger.error(f"Pipeline error: {result['error']}")
        elif result.get("video_path"):
            logger.info(f"Generated: {result['video_path']}")

            # Persist to DB
            vid = add_video(
                niche=topic,
                language=language,
                topic=topic,
                title=result.get("title", ""),
                description=result.get("description", ""),
                script=result.get("script", ""),
                tags=[],
                video_path=result["video_path"],
                platform="youtube",
                account_id=account_id,
            )
            logger.info(f"Video saved to DB with ID: {vid}")

            # Persist YouTube URL if uploaded
            if result.get("uploaded") and result.get("youtube_url"):
                update_video_youtube_url(vid, result["youtube_url"])
                logger.info(f"Uploaded: {result['youtube_url']}")

        state["total_runs"] += 1
        save_state(state)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        state["total_runs"] += 1
        save_state(state)


if __name__ == "__main__":
    main()
