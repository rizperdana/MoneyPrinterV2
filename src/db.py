import sqlite3
from typing import Optional

from config import ROOT_DIR
from status import info, success, error, warning


# Global database connection (in-memory)
_conn: Optional[sqlite3.Connection] = None


def _get_connection() -> sqlite3.Connection:
    """Get or create the database connection."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(":memory:")
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            nickname TEXT,
            profile_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Topics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            niche TEXT NOT NULL,
            account_id INTEGER,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # Videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            title TEXT NOT NULL,
            script TEXT,
            platform TEXT NOT NULL,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)

    # Scripts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(id)
        )
    """)

    conn.commit()
    info("Database initialized successfully")


def add_topic(topic: str, niche: str, account: Optional[str] = None) -> int:
    """
    Insert a topic record.

    Args:
        topic: The topic text
        niche: The niche/category
        account: Optional account username

    Returns:
        The row ID of the inserted topic
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get account_id if account provided
    account_id = None
    if account:
        cursor.execute("SELECT id FROM accounts WHERE username = ?", (account,))
        row = cursor.fetchone()
        if row:
            account_id = row["id"]

    cursor.execute(
        "INSERT INTO topics (topic, niche, account_id) VALUES (?, ?, ?)",
        (topic, niche, account_id),
    )
    conn.commit()
    topic_id = cursor.lastrowid
    success(f"Added topic: {topic} (niche: {niche})")
    return topic_id


def get_topics(niche: Optional[str] = None, limit: int = 100) -> list[dict]:
    """
    Get topics, optionally filtered by niche.

    Args:
        niche: Optional niche filter
        limit: Maximum number of results

    Returns:
        List of topic records as dicts
    """
    conn = _get_connection()
    cursor = conn.cursor()

    if niche:
        cursor.execute(
            "SELECT * FROM topics WHERE niche = ? ORDER BY used_at DESC LIMIT ?",
            (niche, limit),
        )
    else:
        cursor.execute("SELECT * FROM topics ORDER BY used_at DESC LIMIT ?", (limit,))

    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    info(f"Retrieved {len(result)} topics")
    return result


def topic_exists(topic: str) -> bool:
    """
    Check if a topic has already been used.

    Args:
        topic: The topic text to check

    Returns:
        True if topic exists, False otherwise
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM topics WHERE topic = ? LIMIT 1", (topic,))
    exists = cursor.fetchone() is not None
    return exists


def add_video(
    topic: str,
    title: str,
    script: Optional[str],
    platform: str,
    file_path: Optional[str] = None,
) -> int:
    """
    Insert a video record.

    Args:
        topic: The topic text
        title: Video title
        script: Optional script content
        platform: Platform (youtube, twitter, tiktok, etc.)
        file_path: Optional path to video file

    Returns:
        The row ID of the inserted video
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get topic_id
    cursor.execute("SELECT id FROM topics WHERE topic = ?", (topic,))
    row = cursor.fetchone()
    topic_id = row["id"] if row else None

    cursor.execute(
        "INSERT INTO videos (topic_id, title, script, platform, file_path) VALUES (?, ?, ?, ?, ?)",
        (topic_id, title, script, platform, file_path),
    )
    conn.commit()
    video_id = cursor.lastrowid
    success(f"Added video: {title} ({platform})")
    return video_id


def get_videos(platform: Optional[str] = None, limit: int = 50) -> list[dict]:
    """
    Get videos, optionally filtered by platform.

    Args:
        platform: Optional platform filter
        limit: Maximum number of results

    Returns:
        List of video records as dicts
    """
    conn = _get_connection()
    cursor = conn.cursor()

    if platform:
        cursor.execute(
            "SELECT * FROM videos WHERE platform = ? ORDER BY created_at DESC LIMIT ?",
            (platform, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    info(f"Retrieved {len(result)} videos")
    return result


def add_account(
    platform: str,
    username: str,
    nickname: Optional[str] = None,
    profile_path: Optional[str] = None,
) -> int:
    """
    Insert an account record.

    Args:
        platform: Platform name (youtube, twitter, tiktok, etc.)
        username: Account username
        nickname: Optional nickname
        profile_path: Optional path to profile

    Returns:
        The row ID of the inserted account
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO accounts (platform, username, nickname, profile_path) VALUES (?, ?, ?, ?)",
        (platform, username, nickname, profile_path),
    )
    conn.commit()
    account_id = cursor.lastrowid
    success(f"Added account: {username} ({platform})")
    return account_id


def get_accounts(platform: Optional[str] = None) -> list[dict]:
    """
    Get accounts, optionally filtered by platform.

    Args:
        platform: Optional platform filter

    Returns:
        List of account records as dicts
    """
    conn = _get_connection()
    cursor = conn.cursor()

    if platform:
        cursor.execute(
            "SELECT * FROM accounts WHERE platform = ? ORDER BY created_at DESC",
            (platform,),
        )
    else:
        cursor.execute("SELECT * FROM accounts ORDER BY created_at DESC")

    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    info(f"Retrieved {len(result)} accounts")
    return result


def update_account(account_id: int, updates: dict) -> bool:
    """
    Update an existing account record.

    Args:
        account_id: The account ID to update
        updates: Dictionary of fields to update

    Returns:
        True if updated, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Build update query dynamically
    valid_fields = {"platform", "username", "nickname", "profile_path"}
    update_fields = {k: v for k, v in updates.items() if k in valid_fields}

    if not update_fields:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
    values = list(update_fields.values()) + [account_id]

    cursor.execute(
        f"UPDATE accounts SET {set_clause} WHERE id = ?",
        values,
    )
    conn.commit()

    if cursor.rowcount > 0:
        success(f"Updated account ID {account_id}")
        return True
    return False


def delete_account(account_id: int) -> bool:
    """
    Delete an account record.

    Args:
        account_id: The account ID to delete

    Returns:
        True if deleted, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()

    if cursor.rowcount > 0:
        success(f"Deleted account ID {account_id}")
        return True
    return False
