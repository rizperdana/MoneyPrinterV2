#!/usr/bin/env python3
"""
MoneyPrinterV2 - Scheduler Daemon
Runs YouTube/Twitter jobs at peak engagement times for GLOBAL audience.
Designed to run as a persistent background process.

Global Peak Times (UTC+7):
  SEA (UTC+7):       09:00 - Morning scroll
  Middle East (UTC+3): 13:00 - Lunch break
  EU (UTC+1):        17:00 - Afternoon commute
  US East (UTC-5):   21:00 - Morning/lunch scroll
  US West (UTC-8):   00:00 - Morning scroll
  US East (UTC-5):   04:00 - Evening scroll

6 posts/day = 1 per region window, rotating coverage.

Usage:
  python src/scheduler.py start          # Start daemon in background
  python src/scheduler.py start --fg     # Start in foreground (for debugging)
  python src/scheduler.py stop           # Stop daemon
  python src/scheduler.py status         # Show status and next runs
  python src/scheduler.py logs           # Show recent logs
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Add src to path before local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env before other imports
load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from src.config import ROOT_DIR, get_verbose
from src.status import info, success, warning, error

# ─── Configuration ───────────────────────────────────────────────────────────

PID_FILE = os.path.join(ROOT_DIR, ".mp", "scheduler.pid")
LOG_FILE = os.path.join(ROOT_DIR, ".mp", "scheduler.log")
SCHEDULE_FILE = os.path.join(ROOT_DIR, ".mp", "scheduler_state.json")

# ─── Global Peak Times (UTC+7) ────────────────────────────────────────────────
# 6 posts/day hitting all major timezone peaks
#
# Slot  UTC+7   Region          Local Time
# ────  ──────  ──────────────  ──────────────
#   1   09:00   SEA (UTC+7)     09:00 morning scroll
#   2   13:00   Middle East     09:00 UAE morning
#   3   17:00   EU (UTC+1)      11:00 late morning
#   4   21:00   US East (UTC-5) 08:00 morning commute
#   5   00:00   US West (UTC-8) 09:00 morning scroll
#   6   04:00   US East (UTC-5) 15:00 afternoon scroll

# YouTube Shorts: 3/day (EU evening, US morning, US evening)
YOUTUBE_TIMES = ["17:00", "21:00", "04:00"]

# Per-account schedule — staggered across peak windows to avoid simultaneous uploads.
# Slot 1 (17:00 UTC+7): SEA peak
# Slot 2 (21:00 UTC+7): EU peak
# Slot 3 (04:00 UTC+7): US East peak
YOUTUBE_ACCOUNT_TIMES = {
    "awoogle": ["17:00", "21:00", "04:00"],
    "TechArch": ["17:10", "21:10", "04:10"],
    "MegaBuild": ["17:20", "21:20", "04:20"],
    "GoldSci": ["17:30", "21:30", "04:30"],
    "SciFiLore": ["17:40", "21:40", "04:40"],
    "BrainRot": ["17:50", "21:50", "04:50"],
}

# Twitter text posts: 3/day (morning waves)
TWITTER_TIMES = ["09:00", "17:00", "21:00"]


# ─── Logging ─────────────────────────────────────────────────────────────────


def setup_logging(foreground: bool = False) -> logging.Logger:
    """Set up logging to file + optional console."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logger = logging.getLogger("mpv2_scheduler")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (always)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler (foreground mode only)
    if foreground:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


# ─── State Management ────────────────────────────────────────────────────────


def load_state() -> dict:
    """Load scheduler state from disk."""
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return {
        "youtube_accounts": [],
        "twitter_accounts": [],
        "last_runs": {},
        "created": datetime.now().isoformat(),
    }


def save_state(state: dict) -> None:
    """Save scheduler state to disk."""
    os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_next_run(times: list[str], last_run: str = None) -> datetime:
    """Calculate the next run time from a list of HH:MM strings."""
    now = datetime.now()
    today = now.date()

    candidates = []
    for t in times:
        h, m = map(int, t.split(":"))
        run_time = datetime(today.year, today.month, today.day, h, m)
        if run_time > now:
            candidates.append(run_time)
        # Also consider tomorrow
        candidates.append(run_time + timedelta(days=1))

    # Filter out if already ran at this time
    if last_run:
        last_dt = datetime.fromisoformat(last_run)
        candidates = [c for c in candidates if c > last_dt]

    return min(candidates) if candidates else now + timedelta(hours=1)


# ─── Job Execution ───────────────────────────────────────────────────────────


def run_youtube_job(account_id: str, model: str, logger: logging.Logger) -> bool:
    """Run a YouTube video generation + upload job."""
    logger.info(f"[YouTube] Starting job for account {account_id[:8]}...")
    try:
        cron_script = os.path.join(ROOT_DIR, "src", "cron.py")
        result = subprocess.run(
            [sys.executable, cron_script, "youtube", account_id, model],
            capture_output=True,
            text=True,
            timeout=900,  # 15 min max
        )
        if result.returncode == 0:
            logger.info(f"[YouTube] Job completed successfully")
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-5:]:
                    logger.info(f"[YouTube]   {line}")
            return True
        else:
            logger.error(f"[YouTube] Job failed (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    logger.error(f"[YouTube]   {line}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"[YouTube] Job timed out (15 min)")
        return False
    except Exception as e:
        logger.error(f"[YouTube] Job exception: {e}")
        return False


def run_twitter_job(account_id: str, model: str, logger: logging.Logger) -> bool:
    """Run a Twitter post job."""
    logger.info(f"[Twitter] Starting job for account {account_id[:8]}...")
    try:
        cron_script = os.path.join(ROOT_DIR, "src", "cron.py")
        result = subprocess.run(
            [sys.executable, cron_script, "twitter", account_id, model],
            capture_output=True,
            text=True,
            timeout=120,  # 2 min max
        )
        if result.returncode == 0:
            logger.info(f"[Twitter] Job completed successfully")
            return True
        else:
            logger.error(f"[Twitter] Job failed (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-3:]:
                    logger.error(f"[Twitter]   {line}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"[Twitter] Job timed out (2 min)")
        return False
    except Exception as e:
        logger.error(f"[Twitter] Job exception: {e}")
        return False


def run_reddit_twitter_job(account_id: str, model: str, logger: logging.Logger) -> bool:
    """Run a Reddit-to-Twitter meme posting job."""
    logger.info(f"[Reddit→Twitter] Starting job for account {account_id[:8]}...")
    try:
        cron_script = os.path.join(ROOT_DIR, "src", "reddit_twitter_cron.py")
        result = subprocess.run(
            [sys.executable, cron_script, account_id, model],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max (fetch + download + post)
        )
        if result.returncode == 0:
            logger.info(f"[Reddit→Twitter] Job completed successfully")
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-5:]:
                    logger.info(f"[Reddit→Twitter]   {line}")
            return True
        else:
            logger.error(f"[Reddit→Twitter] Job failed (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    logger.error(f"[Reddit→Twitter]   {line}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"[Reddit→Twitter] Job timed out (5 min)")
        return False
    except Exception as e:
        logger.error(f"[Reddit→Twitter] Job exception: {e}")
        return False


# ─── Main Loop ───────────────────────────────────────────────────────────────


def get_active_model() -> str:
    """Get the primary model from config."""
    from src.config import get_default_model
    model = get_default_model()
    return model if model else "xiaomi/mimo-v2-pro:free"


def main_loop(logger: logging.Logger):
    """Main scheduler loop with global timezone coverage."""
    state = load_state()
    model = get_active_model()

    # Auto-discover accounts from cache
    from src.cache import get_accounts

    yt_accounts = get_accounts("youtube")
    tw_accounts = get_accounts("twitter")

    logger.info("=" * 60)
    logger.info("MoneyPrinterV2 Scheduler Started (GLOBAL)")
    logger.info("=" * 60)
    logger.info(f"Model: {model}")
    logger.info(f"YouTube accounts: {len(yt_accounts)}")
    logger.info(f"Twitter accounts: {len(tw_accounts)}")
    logger.info(f"YouTube times (UTC+7): {', '.join(YOUTUBE_TIMES)}")
    logger.info(f"Twitter times (UTC+7): {', '.join(TWITTER_TIMES)}")
    logger.info(f"Reddit→Twitter times (UTC+7): {', '.join(REDDIT_TWITTER_TIMES)}")
    logger.info(f"Peak regions: SEA → Middle East → EU → US East → US West")
    logger.info("=" * 60)

    # Calculate initial next runs (per-account staggered times)
    yt_next = {}
    for acc in yt_accounts:
        acc_times = YOUTUBE_ACCOUNT_TIMES.get(acc["nickname"], YOUTUBE_TIMES)
        yt_next[acc["id"]] = get_next_run(acc_times)
    tw_next = {acc["id"]: get_next_run(TWITTER_TIMES) for acc in tw_accounts}
    rt_next = {acc["id"]: get_next_run(REDDIT_TWITTER_TIMES) for acc in tw_accounts}

    for acc in yt_accounts:
        logger.info(
            f"[YouTube] {acc['nickname']}: next run at {yt_next[acc['id']].strftime('%Y-%m-%d %H:%M')}"
        )
    for acc in tw_accounts:
        logger.info(
            f"[Twitter] {acc['nickname']}: next run at {tw_next[acc['id']].strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info(
            f"[Reddit→Twitter] {acc['nickname']}: next run at {rt_next[acc['id']].strftime('%Y-%m-%d %H:%M')}"
        )

    running = True

    def shutdown(signum, frame):
        nonlocal running
        logger.info(f"Received signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while running:
        now = datetime.now()

        # Check YouTube jobs
        for acc in yt_accounts:
            acc_id = acc["id"]
            acc_times = YOUTUBE_ACCOUNT_TIMES.get(acc["nickname"], YOUTUBE_TIMES)
            if now >= yt_next[acc_id]:
                success = run_youtube_job(acc_id, model, logger)
                state["last_runs"][f"youtube_{acc_id}"] = now.isoformat()
                save_state(state)
                yt_next[acc_id] = get_next_run(acc_times, last_run=now.isoformat())
                logger.info(
                    f"[YouTube] {acc['nickname']}: next run at {yt_next[acc_id].strftime('%Y-%m-%d %H:%M')}"
                )

        # Check Twitter text jobs
        for acc in tw_accounts:
            acc_id = acc["id"]
            if now >= tw_next[acc_id]:
                success = run_twitter_job(acc_id, model, logger)
                state["last_runs"][f"twitter_{acc_id}"] = now.isoformat()
                save_state(state)
                tw_next[acc_id] = get_next_run(TWITTER_TIMES, last_run=now.isoformat())
                logger.info(
                    f"[Twitter] {acc['nickname']}: next run at {tw_next[acc_id].strftime('%Y-%m-%d %H:%M')}"
                )

        # Check Reddit→Twitter meme jobs (6/day global coverage)
        for acc in tw_accounts:
            acc_id = acc["id"]
            if now >= rt_next[acc_id]:
                success = run_reddit_twitter_job(acc_id, model, logger)
                state["last_runs"][f"reddit_twitter_{acc_id}"] = now.isoformat()
                save_state(state)
                rt_next[acc_id] = get_next_run(
                    REDDIT_TWITTER_TIMES, last_run=now.isoformat()
                )
                logger.info(
                    f"[Reddit→Twitter] {acc['nickname']}: next run at {rt_next[acc_id].strftime('%Y-%m-%d %H:%M')}"
                )

        # Sleep 30 seconds between checks
        time.sleep(30)

    logger.info("Scheduler stopped.")


# ─── Daemon Management ──────────────────────────────────────────────────────


def is_running() -> bool:
    """Check if scheduler is already running."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # PID file stale
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return False


def cmd_start(foreground: bool = False):
    """Start the scheduler."""
    if is_running():
        error("Scheduler is already running. Use 'stop' first.")
        return

    if foreground:
        logger = setup_logging(foreground=True)
        # Write PID
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            main_loop(logger)
        finally:
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
    else:
        # Start as background process
        log = setup_logging(foreground=False)
        log.info("Starting scheduler in background...")

        proc = subprocess.Popen(
            [sys.executable, __file__, "start", "--fg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait a moment and verify
        time.sleep(2)
        if is_running():
            success(f"Scheduler started (PID: {proc.pid})")
            info(f"Logs: {LOG_FILE}")
            info(f"Status: python src/scheduler.py status")
        else:
            error("Scheduler failed to start. Check logs.")


def cmd_stop():
    """Stop the scheduler."""
    if not is_running():
        error("Scheduler is not running.")
        return

    with open(PID_FILE, "r") as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for shutdown
        for _ in range(10):
            time.sleep(0.5)
            if not is_running():
                success("Scheduler stopped.")
                return
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        warning("Scheduler force-killed.")
    except OSError as e:
        error(f"Failed to stop scheduler: {e}")

    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def cmd_status():
    """Show scheduler status."""
    if not is_running():
        print("Status: NOT RUNNING")
        print(f"\nStart with: python src/scheduler.py start")
        return

    with open(PID_FILE, "r") as f:
        pid = int(f.read().strip())

    print(f"Status: RUNNING (PID: {pid})")
    print(f"Logs: {LOG_FILE}")
    print(f"State: {SCHEDULE_FILE}")

    # Show last runs
    state = load_state()
    if state.get("last_runs"):
        print(f"\nLast runs:")
        for key, ts in sorted(state["last_runs"].items()):
            dt = datetime.fromisoformat(ts)
            print(f"  {key}: {dt.strftime('%Y-%m-%d %H:%M')}")

    # Show next runs
    from cache import get_accounts

    yt_accounts = get_accounts("youtube")
    tw_accounts = get_accounts("twitter")

    if yt_accounts:
        print(f"\nNext YouTube runs (UTC+7):")
        for acc in yt_accounts:
            last = state.get("last_runs", {}).get(f"youtube_{acc['id']}")
            nxt = get_next_run(YOUTUBE_TIMES, last_run=last)
            print(f"  {acc['nickname']}: {nxt.strftime('%Y-%m-%d %H:%M')}")

    if tw_accounts:
        print(f"\nNext Twitter runs (UTC+7):")
        for acc in tw_accounts:
            last = state.get("last_runs", {}).get(f"twitter_{acc['id']}")
            nxt = get_next_run(TWITTER_TIMES, last_run=last)
            print(f"  {acc['nickname']}: {nxt.strftime('%Y-%m-%d %H:%M')}")

        print(f"\nNext Reddit→Twitter runs (UTC+7):")
        for acc in tw_accounts:
            last = state.get("last_runs", {}).get(f"reddit_twitter_{acc['id']}")
            nxt = get_next_run(REDDIT_TWITTER_TIMES, last_run=last)
            print(f"  {acc['nickname']}: {nxt.strftime('%Y-%m-%d %H:%M')}")

    print(f"\nSchedule (UTC+7):")
    print(f"  YouTube:        {', '.join(YOUTUBE_TIMES)}")
    print(f"  Twitter:        {', '.join(TWITTER_TIMES)}")
    print(f"  Reddit→Twitter: {', '.join(REDDIT_TWITTER_TIMES)} (6/day)")
    print(f"\nGlobal coverage:")
    print(f"  09:00 SEA morning | 13:00 Middle East | 17:00 EU")
    print(f"  21:00 US East     | 00:00 US West     | 04:00 US East evening")


def cmd_logs(lines: int = 50):
    """Show recent logs."""
    if not os.path.exists(LOG_FILE):
        error("No log file found.")
        return

    with open(LOG_FILE, "r") as f:
        all_lines = f.readlines()

    for line in all_lines[-lines:]:
        print(line.rstrip())


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        fg = "--fg" in sys.argv
        cmd_start(foreground=fg)
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "status":
        cmd_status()
    elif cmd == "logs":
        cmd_logs()
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: start, stop, status, logs")
        sys.exit(1)
