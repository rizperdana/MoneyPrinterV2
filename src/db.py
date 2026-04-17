import sqlite3
import os
from typing import Optional

from config import ROOT_DIR
from status import info, success, error, warning

# Database file path
DB_FILE = os.path.join(ROOT_DIR, "data", "moneyprinter.db")

# Global database connection
_conn: Optional[sqlite3.Connection] = None


def _get_connection() -> sqlite3.Connection:
    """Get or create the database connection."""
    global _conn
    if _conn is None:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        _conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    """Create tables if they don't exist and import initial data."""
    import json
    import os

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

    # OAuth credentials table - stores OAuth tokens and refresh tokens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            token TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_name, platform)
        )
    """)

    # Account-OAuth link table (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_oauth_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            oauth_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, oauth_id),
            FOREIGN KEY (account_id) REFERENCES accounts(id),
            FOREIGN KEY (oauth_id) REFERENCES oauth_credentials(id)
        )
    """)

    # Settings table - stores all config key-value pairs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Videos table - stores all AI-generated video data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            niche TEXT NOT NULL,
            account TEXT,
            title TEXT NOT NULL,
            description TEXT,
            script TEXT,
            tags TEXT,
            category TEXT,
            platform TEXT NOT NULL,
            file_path TEXT,
            language TEXT DEFAULT 'English',
            for_kids BOOLEAN DEFAULT 0,
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

    # Migration: Add oauth_token column to accounts table if not exists
    try:
        cursor.execute("SELECT oauth_token FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE accounts ADD COLUMN oauth_token TEXT")

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


def get_topics(
    niche: Optional[str] = None, account: Optional[str] = None, limit: int = 100
) -> list[dict]:
    """
    Get topics, optionally filtered by niche and/or account.

    Args:
        niche: Optional niche filter
        account: Optional account username filter
        limit: Maximum number of results

    Returns:
        List of topic records as dicts
    """
    conn = _get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM topics"
    params = []
    conditions = []

    if niche:
        conditions.append("niche = ?")
        params.append(niche)
    if account:
        # Join with accounts table to filter by username
        query = "SELECT t.* FROM topics t LEFT JOIN accounts a ON t.account_id = a.id WHERE a.username = ?"
        params = [account]
        if niche:
            query += " AND t.niche = ?"
            params.append(niche)
    elif conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY used_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)

    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    info(f"Retrieved {len(result)} topics")
    return result


def get_last_topic_for_account(account: str) -> Optional[dict]:
    """Get the most recent topic used by an account."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT t.* FROM topics t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.username = ?
        ORDER BY t.used_at DESC
        LIMIT 1
    """,
        (account,),
    )

    row = cursor.fetchone()
    return dict(row) if row else None


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
    script: Optional[str] = None,
    platform: str = "youtube",
    file_path: Optional[str] = None,
    niche: str = "",
    description: Optional[str] = None,
    tags: Optional[str] = None,
    category: Optional[str] = None,
    account: Optional[str] = None,
    language: str = "English",
    for_kids: bool = False,
) -> int:
    """
    Insert a video record with all AI-generated data.

    Args:
        topic: The topic text
        title: Video title
        script: Script content
        platform: Platform (youtube, twitter, tiktok, etc.)
        file_path: Path to video file
        niche: The niche/category
        description: YouTube description
        tags: SEO tags (comma-separated)
        category: Video category
        account: Account username
        language: Video language
        for_kids: Whether content is for kids

    Returns:
        The row ID of the inserted video
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get topic_id
    cursor.execute("SELECT id FROM topics WHERE topic = ?", (topic,))
    row = cursor.fetchone()
    topic_id = row["id"] if row else None

    # Convert tags to string if it's a list
    if isinstance(tags, list):
        tags = ",".join(tags)

    cursor.execute(
        """
        INSERT INTO videos (
            topic_id, niche, account, title, description, script, tags, category,
            platform, file_path, language, for_kids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            topic_id,
            niche,
            account,
            title,
            description,
            script,
            tags,
            category,
            platform,
            file_path,
            language,
            for_kids,
        ),
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


def get_video_by_id(video_id: int) -> Optional[dict]:
    """Get a single video by its ID.

    Args:
        video_id: The video's database ID

    Returns:
        Video record as dict or None if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def get_settings() -> dict:
    """Get all settings as key-value dict."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_setting(key: str, value: str) -> None:
    """Set a setting value."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """,
        (key, value),
    )
    conn.commit()


def import_config_to_db() -> None:
    """Import config.json and .env into settings table."""
    import json
    import os
    from dotenv import load_dotenv

    config_path = os.path.join(ROOT_DIR, "config.json")
    env_path = os.path.join(ROOT_DIR, ".env")

    # Load .env first
    load_dotenv(env_path)

    # Import from config.json
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            for key, value in config.items():
                if isinstance(value, (dict, list)):
                    set_setting(key, json.dumps(value))
                else:
                    set_setting(key, str(value))

    # Import .env overrides
    env_keys = ["CLIPROXY_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
    for key in env_keys:
        value = os.environ.get(key)
        if value:
            set_setting(key, value)

    info("Imported config to database")


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


def get_oauth_credentials(
    platform: Optional[str] = None, account_name: Optional[str] = None
) -> list[dict]:
    """
    Get OAuth credentials, optionally filtered by platform and/or account_name.

    Args:
        platform: Optional platform filter
        account_name: Optional account_name filter

    Returns:
        List of credential records as dicts
    """
    conn = _get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM oauth_credentials"
    params = []
    conditions = []

    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if account_name:
        conditions.append("account_name = ?")
        params.append(account_name)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY updated_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    info(f"Retrieved {len(result)} OAuth credentials")
    return result


def add_oauth_credential(
    account_name: str, platform: str, token: str, payload: str
) -> int:
    """
    Insert or update OAuth credential. Uses upsert ON CONFLICT.

    Args:
        account_name: The account name
        platform: Platform (youtube, twitter, etc.)
        token: The OAuth token
        payload: Additional JSON payload (e.g., refresh token)

    Returns:
        The row ID of the inserted/updated credential
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO oauth_credentials (account_name, platform, token, payload, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(account_name, platform) DO UPDATE SET
            token = excluded.token,
            payload = excluded.payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (account_name, platform, token, payload),
    )
    conn.commit()
    credential_id = cursor.lastrowid
    success(f"Added/updated OAuth credential: {account_name} ({platform})")
    return credential_id


def delete_oauth_credential(account_name: str, platform: str) -> bool:
    """
    Delete OAuth credential.

    Args:
        account_name: The account name
        platform: Platform (youtube, twitter, etc.)

    Returns:
        True if deleted, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM oauth_credentials WHERE account_name = ? AND platform = ?",
        (account_name, platform),
    )
    conn.commit()

    if cursor.rowcount > 0:
        success(f"Deleted OAuth credential: {account_name} ({platform})")
        return True
    return False


def link_oauth_to_account(account_id: int, oauth_id: int) -> int:
    """Link an OAuth credential to an account."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO account_oauth_links (account_id, oauth_id, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(account_id, oauth_id) DO NOTHING
        """,
        (account_id, oauth_id),
    )
    conn.commit()
    return cursor.lastrowid


def unlink_oauth_from_account(account_id: int, oauth_id: int) -> bool:
    """Unlink an OAuth credential from an account."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM account_oauth_links WHERE account_id = ? AND oauth_id = ?",
        (account_id, oauth_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_linked_oauth_ids(account_id: int) -> list[int]:
    """Get all OAuth IDs linked to an account."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT oauth_id FROM account_oauth_links WHERE account_id = ?",
        (account_id,),
    )
    return [row["oauth_id"] for row in cursor.fetchall()]


def get_oauth_credentials_by_ids(oauth_ids: list[int]) -> list[dict]:
    """Get OAuth credentials by a list of IDs."""
    if not oauth_ids:
        return []
    conn = _get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(oauth_ids))
    cursor.execute(
        f"SELECT * FROM oauth_credentials WHERE id IN ({placeholders})",
        oauth_ids,
    )
    return [dict(row) for row in cursor.fetchall()]
