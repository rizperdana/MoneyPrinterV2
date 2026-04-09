"""
Tracker module for MoneyPrinterV2.

Keeps track of generated topics, uploaded videos, and prevents duplicates.
"""

import json
import os
from datetime import datetime
from typing import Optional, List
from config import ROOT_DIR


def _get_tracker_path() -> str:
    """Get the path to the tracker JSON file."""
    return os.path.join(ROOT_DIR, ".mp", "tracker.json")


def _load_tracker() -> dict:
    """Load tracker data from JSON file."""
    path = _get_tracker_path()
    if not os.path.exists(path):
        return {"topics": {}, "uploads": {}, "recent_topics": []}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {"topics": {}, "uploads": {}, "recent_topics": []}


def _save_tracker(data: dict) -> None:
    """Save tracker data to JSON file."""
    path = _get_tracker_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def record_attempt(
    account_id: str,
    account_name: str,
    niche: str,
    topic: str,
    title: str,
    description: str,
    tags: List[str],
    video_path: str,
) -> int:
    """
    Record a video generation attempt.

    Returns:
        upload_id (int): The ID of the recorded attempt.
    """
    tracker = _load_tracker()

    # Generate upload ID
    upload_id = len(tracker.get("uploads", {})) + 1

    if "uploads" not in tracker:
        tracker["uploads"] = {}

    tracker["uploads"][upload_id] = {
        "account_id": account_id,
        "account_name": account_name,
        "niche": niche,
        "topic": topic,
        "title": title,
        "description": description,
        "tags": tags,
        "video_path": video_path,
        "status": "attempted",
        "timestamp": datetime.now().isoformat(),
    }

    # Track topic usage
    if topic:
        if topic not in tracker.get("topics", {}):
            tracker["topics"][topic] = []
        tracker["topics"][topic].append(
            {
                "account_id": account_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Update recent topics list
        if "recent_topics" not in tracker:
            tracker["recent_topics"] = []
        tracker["recent_topics"] = [
            t
            for t in tracker["recent_topics"]
            if t.get("account_id") != account_id or t.get("topic") != topic
        ]
        tracker["recent_topics"].insert(
            0,
            {
                "account_id": account_id,
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
            },
        )
        # Keep only last 50 topics per account
        tracker["recent_topics"] = tracker["recent_topics"][:100]

    _save_tracker(tracker)
    return upload_id


def record_uploading(upload_id: int) -> None:
    """Mark an upload as currently uploading."""
    tracker = _load_tracker()
    if str(upload_id) in tracker.get("uploads", {}):
        tracker["uploads"][str(upload_id)]["status"] = "uploading"
        _save_tracker(tracker)


def record_success(upload_id: int, url: str = "") -> None:
    """Mark an upload as successful."""
    tracker = _load_tracker()
    key = str(upload_id)
    if key in tracker.get("uploads", {}):
        tracker["uploads"][key]["status"] = "success"
        tracker["uploads"][key]["url"] = url
        tracker["uploads"][key]["completed_at"] = datetime.now().isoformat()
        _save_tracker(tracker)


def record_failure(upload_id: int, error: str = "") -> None:
    """Mark an upload as failed."""
    tracker = _load_tracker()
    key = str(upload_id)
    if key in tracker.get("uploads", {}):
        tracker["uploads"][key]["status"] = "failed"
        tracker["uploads"][key]["error"] = error
        tracker["uploads"][key]["completed_at"] = datetime.now().isoformat()
        _save_tracker(tracker)


def is_topic_used(account_id: str, topic: str) -> bool:
    """Check if a topic has been used by this account recently."""
    tracker = _load_tracker()
    topics = tracker.get("topics", {})

    if topic not in topics:
        return False

    # Check if this specific account used this topic
    for usage in topics[topic]:
        if usage.get("account_id") == account_id:
            return True

    return False


def get_recent_topics(account_id: str, limit: int = 20) -> List[dict]:
    """Get recent topics used by an account."""
    tracker = _load_tracker()
    recent = tracker.get("recent_topics", [])

    account_topics = [t for t in recent if t.get("account_id") == account_id]

    return account_topics[:limit]


def get_upload_status(upload_id: int) -> Optional[dict]:
    """Get the status of an upload."""
    tracker = _load_tracker()
    return tracker.get("uploads", {}).get(str(upload_id))


def get_all_uploads(status: Optional[str] = None) -> List[dict]:
    """Get all recorded uploads, optionally filtered by status."""
    tracker = _load_tracker()
    uploads = list(tracker.get("uploads", {}).values())

    if status:
        uploads = [u for u in uploads if u.get("status") == status]

    return uploads


# Export all functions
__all__ = [
    "record_attempt",
    "record_uploading",
    "record_success",
    "record_failure",
    "is_topic_used",
    "get_recent_topics",
    "get_upload_status",
    "get_all_uploads",
]
