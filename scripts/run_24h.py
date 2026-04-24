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


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
    else:
        state = {}
    # Ensure all expected keys exist (migration for old state files)
    state.setdefault("last_index", {})
    state.setdefault("last_topic", {})
    state.setdefault("total_runs", 0)
    return state


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_accounts():
    """Load accounts from DB."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from src.db import list_accounts_with_topics

    return list_accounts_with_topics()


def get_next_topic(account, state):
    """Get next topic for account.
    Uses account.topic directly.
    """
    account_id = account["id"]
    account_topic = account.get("topic")

    # Use account's topic if available
    if account_topic:
        state["last_topic"][account_id] = account_topic
        return account_topic

    # Fallback to DARK_NICHES if no topic set
    topic = random.choice(DARK_NICHES)
    state["last_topic"][account_id] = topic
    return topic


def add_video(niche, locale, topic, title, description, script, tags, video_path, platform="youtube", account=None):
    """Add a generated video to the DB."""
    from src.db import add_video as db_add_video
    return db_add_video(
        niche=niche,
        topic=topic,
        account=account,
        title=title,
        description=description,
        script=script,
        tags=",".join(tags) if tags else "",
        platform=platform,
        file_path=video_path,
        locale=locale,
    )


def main():
    from src.run_pipeline import run_pipeline
    from src.db import init_db, update_video_youtube_url

    init_db()
    state = load_state()
    accounts = load_accounts()

    if not accounts:
        logger.error("No accounts found in database")
        return

    # Pick the account with fewest runs (round-robin across accounts too)
    account = min(accounts, key=lambda a: state.get("last_index", {}).get(a["id"], -1))
    topic = get_next_topic(account, state)
    locale = account.get("locale", "en-US")
    account_id = account.get("id")

    logger.info(f"=== Run #{state['total_runs'] + 1} ===")
    account_id = str(account.get("id", ""))
    logger.info(f"Account: {account.get('username', '?')} ({account_id[:8] if len(account_id) >= 8 else account_id})")
    logger.info(f"Topic: {topic}")

    # Simple dedup: if last run used same topic for same account, skip and pick next
    last = state.get("last_topic", {}).get(account_id)
    if last == topic:
        # Account has single topic, just use it (dedup already done in get_next_topic)
        logger.info(f"Same topic as last run for this account: {topic}")

    try:
        result = run_pipeline(
            niche=topic,
            locale=locale,
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
                locale=locale,
                topic=topic,
                title=result.get("title", ""),
                description=result.get("description", ""),
                script=result.get("script", ""),
                tags=[],
                video_path=result["video_path"],
                platform="youtube",
                account=account.get("username"),
            )
            logger.info(f"Video saved to DB with ID: {vid}")

            # Persist YouTube URL if uploaded
            if result.get("uploaded") and result.get("youtube_url"):
                update_video_youtube_url(vid, result["youtube_url"])
                logger.info(f"Uploaded: {result['youtube_url']}")

        state["total_runs"] += 1
        state["last_topic"][account_id] = topic
        save_state(state)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        state["total_runs"] += 1
        save_state(state)


if __name__ == "__main__":
    main()
