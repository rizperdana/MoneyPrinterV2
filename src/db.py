import sqlite3
import os
import json
from pathlib import Path
from typing import Optional

ROOT_DIR = str(Path(__file__).parent.parent)

from src import status

info = status.info
success = status.success
error = status.error
warning = status.warning

# BCP-47 locale mapping from bare language names
LANGUAGE_TO_LOCALE = {
    "Indonesian": "id-ID",
    "Javanese": "jv-ID",
    "Sundanese": "su-ID",
    "Malay": "ms-MY",
    "Thai": "th-TH",
    "Vietnamese": "vi-VN",
    "Filipino": "fil-PH",
    "Korean": "ko-KR",
    "Japanese": "ja-JP",
    "Chinese": "zh-CN",
    "Arabic": "ar-SA",
    "Hindi": "hi-IN",
    "Spanish": "es-ES",
    "French": "fr-FR",
    "German": "de-DE",
    "Italian": "it-IT",
    "Portuguese": "pt-BR",
    "Russian": "ru-RU",
    "Turkish": "tr-TR",
    "Polish": "pl-PL",
    "Dutch": "nl-NL",
    "Swedish": "sv-SE",
    "Danish": "da-DK",
    "Norwegian": "no-NO",
    "Finnish": "fi-FI",
    "Greek": "el-GR",
    "Czech": "cs-CZ",
    "Hungarian": "hu-HU",
    "Romanian": "ro-RO",
    "Ukrainian": "uk-UA",
    "English": "en-US",   # default fallback
}

# Database file path
DB_FILE = os.path.join(ROOT_DIR, "data", "moneyprinter.db")

# Global database connection
_conn: Optional[sqlite3.Connection] = None

# In-memory cache for settings (populated on first read)
_settings_cache: dict | None = None


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
            topic TEXT NOT NULL UNIQUE,
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
            account_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES topics(id),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
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

    # Migration: add topics column to accounts (JSON array of niche strings)
    try:
        cursor.execute("SELECT topics FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE accounts ADD COLUMN topics TEXT DEFAULT '[]'")

    # Migration: add topic column to accounts (replace niche)
    try:
        cursor.execute("SELECT topic FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE accounts ADD COLUMN topic TEXT DEFAULT ''")

    # Migration: add audience column to accounts (target demographic)
    try:
        cursor.execute("SELECT audience FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE accounts ADD COLUMN audience TEXT DEFAULT 'general'")

    # Migration: add youtube_url column to videos
    try:
        cursor.execute("SELECT youtube_url FROM videos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE videos ADD COLUMN youtube_url TEXT")

    # Migration: add account_id column to videos
    try:
        cursor.execute("SELECT account_id FROM videos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE videos ADD COLUMN account_id INTEGER REFERENCES accounts(id)")

    # Migration: add localevoices column (JSON dict of locale->voice)
    try:
        cursor.execute("SELECT localevoices FROM settings LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("SELECT languagevoices FROM settings LIMIT 1")
            old_row = cursor.fetchone()
            if old_row and old_row[0]:
                cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT ?", (old_row[0],))
            else:
                cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'")

    # Migration: rename language column to locale (BCP-47)
    try:
        cursor.execute("SELECT locale FROM accounts LIMIT 1")
        try:
            cursor.execute("SELECT language FROM accounts LIMIT 1")
            cursor.execute("SELECT id, language FROM accounts WHERE language IS NOT NULL AND language != ''")
            for account_id, lang in cursor.fetchall():
                locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)
                cursor.execute("UPDATE accounts SET locale = ? WHERE id = ?", (locale_val, account_id))
            cursor.execute("ALTER TABLE accounts DROP COLUMN language")
        except sqlite3.OperationalError:
            pass
    except sqlite3.OperationalError:
        try:
            cursor.execute("SELECT language FROM accounts LIMIT 1")
            cursor.execute("ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'")
            cursor.execute("SELECT id, language FROM accounts WHERE language IS NOT NULL AND language != ''")
            for account_id, lang in cursor.fetchall():
                locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)
                cursor.execute("UPDATE accounts SET locale = ? WHERE id = ?", (locale_val, account_id))
            cursor.execute("ALTER TABLE accounts DROP COLUMN language")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'")
    
    # Migration: rename language column to locale (BCP-47) in videos table
    try:
        cursor.execute("SELECT locale FROM videos LIMIT 1")
        # Already has locale, try to migrate data from language if exists
        try:
            cursor.execute("SELECT id, language FROM videos WHERE language IS NOT NULL AND language != '' AND (locale IS NULL OR locale = '')")
            for video_id, lang in cursor.fetchall():
                locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)
                cursor.execute("UPDATE videos SET locale = ? WHERE id = ?", (locale_val, video_id))
            cursor.execute("ALTER TABLE videos DROP COLUMN language")
        except sqlite3.OperationalError:
            pass
    except sqlite3.OperationalError:
        try:
            cursor.execute("SELECT language FROM videos LIMIT 1")
            cursor.execute("ALTER TABLE videos ADD COLUMN locale TEXT DEFAULT 'en-US'")
            cursor.execute("SELECT id, language FROM videos WHERE language IS NOT NULL AND language != ''")
            for video_id, lang in cursor.fetchall():
                locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)
                cursor.execute("UPDATE videos SET locale = ? WHERE id = ?", (locale_val, video_id))
            cursor.execute("ALTER TABLE videos DROP COLUMN language")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE videos ADD COLUMN locale TEXT DEFAULT 'en-US'")

    info("Database initialized successfully")

    # Auto-import config into DB if settings table is empty
    try:
        cursor.execute("SELECT COUNT(*) FROM settings")
        count = cursor.fetchone()[0]
        if count == 0:
            import_config_to_db()
            reload_settings()  # Refresh in-memory cache after import
    except sqlite3.OperationalError:
        pass

    # Pre-populate localevoices if empty
    try:
        cursor.execute("SELECT value FROM settings WHERE key='localevoices'")
        row = cursor.fetchone()
        if not row or not row[0] or row[0] == '{}':
            set_setting("localevoices", json.dumps({
                "id-ID": "id-ID-GadisNeural",
                "jv-ID": "jv-ID-SitiNeural",
                "su-ID": "su-ID-TutiNeural"
            }))
    except (sqlite3.OperationalError, KeyError) as e:
        error(f"Failed to pre-populate localevoices: {e}")


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


def get_existing_videos_for_niche(niche: str, limit: int = 50) -> list[dict]:
    """
    Get existing video titles and topics for a niche to avoid duplicates.

    Args:
        niche: The niche/category to search
        limit: Maximum number of results

    Returns:
        List of dicts with 'title' and 'topic' keys from past videos
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT v.title, v.niche, t.topic
        FROM videos v
        LEFT JOIN topics t ON v.topic_id = t.id
        WHERE v.niche = ?
        ORDER BY v.created_at DESC
        LIMIT ?
    """,
        (niche, limit),
    )

    rows = cursor.fetchall()
    return [{"title": row["title"], "niche": row["niche"], "topic": row["topic"] or ""} for row in rows]


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
    locale: str = "en-US",
    for_kids: bool = False,
    account_id: Optional[int] = None,
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
        locale: Video locale (BCP-47 code, default: en-US)
        for_kids: Whether content is for kids
        account_id: Optional account ID (resolves from account if not provided)

    Returns:
        The row ID of the inserted video
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get topic_id
    cursor.execute("SELECT id FROM topics WHERE topic = ?", (topic,))
    row = cursor.fetchone()
    topic_id = row["id"] if row else None

    # Resolve account_id from account username if not provided
    if account_id is None and account:
        cursor.execute("SELECT id FROM accounts WHERE username = ?", (account,))
        row = cursor.fetchone()
        if row:
            account_id = row["id"]

    # Convert tags to string if it's a list
    if isinstance(tags, list):
        tags = ",".join(tags)

    cursor.execute(
        """
        INSERT INTO videos (
            topic_id, niche, account, title, description, script, tags, category,
            platform, file_path, locale, for_kids, account_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            locale,
            for_kids,
            account_id,
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


def update_video_youtube_url(video_id: int, youtube_url: str) -> bool:
    """Update the youtube_url for a video. Returns True if updated."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE videos SET youtube_url = ? WHERE id = ?", (youtube_url, video_id))
    conn.commit()
    return cursor.rowcount > 0


def get_settings() -> dict:
    """Get all settings as key-value dict."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    return {row["key"]: row["value"] for row in rows}


def _ensure_settings_loaded() -> None:
    """Ensure settings are loaded into cache."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = get_settings()


def get_setting(key: str, default: str = "") -> str:
    """
    Get a single setting value.

    Args:
        key: Settings key
        default: Default value if not found

    Returns:
        Setting value or default
    """
    _ensure_settings_loaded()
    return _settings_cache.get(key, default)


def reload_settings() -> None:
    """Force reload settings from database."""
    global _settings_cache
    _settings_cache = None
    _ensure_settings_loaded()


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
    topic: Optional[str] = None,
    topics: Optional[str] = None,
    locale: str = "en-US",
    audience: str = "general",
) -> int:
    """
    Insert an account record.

    Args:
        platform: Platform name (youtube, twitter, tiktok, etc.)
        username: Account username
        nickname: Optional nickname
        profile_path: Optional path to profile
        niche: Optional niche/topic for the account
        topics: Optional JSON string of topics list
        locale: Account locale (default: en-US)

    Returns:
        The row ID of the inserted account
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Note: profile_path removed - stored in config.json or OAuth credentials instead
    cursor.execute(
        "INSERT INTO accounts (platform, username, nickname, topic, topics, locale, audience) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (platform, username, nickname or "", topic or "", topics or "", locale, audience),
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


def get_account_by_username(username: str) -> Optional[dict]:
    """Get account by username. Returns dict or None."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE username = ?", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_accounts_with_topics() -> list[dict]:
    """List all accounts from DB."""
    return get_accounts()


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
    valid_fields = {"platform", "username", "nickname", "topic", "locale", "audience"}
    update_fields = {}
    for k, v in updates.items():
        if k in valid_fields:
            update_fields[k] = v

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

    # Link oauth to account
    account = get_account_by_username(account_name)
    if account:
        link_oauth_to_account(account["id"], credential_id)

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


def delete_oauth_credential_by_id(oauth_id: int) -> bool:
    """Delete OAuth credential by ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM oauth_credentials WHERE id = ?", (oauth_id,))
    conn.commit()
    return cursor.rowcount > 0


def link_oauth_to_account(account_id: int | str, oauth_id: int) -> int:
    """Link an OAuth credential to an account. Accepts int or str account_id."""
    if isinstance(account_id, str) and account_id.isdigit():
        account_id = int(account_id)
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


def unlink_oauth_from_account(account_id: int | str, oauth_id: int) -> bool:
    """Remove link between account and OAuth credential."""
    if isinstance(account_id, str) and account_id.isdigit():
        account_id = int(account_id)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM account_oauth_links WHERE account_id = ? AND oauth_id = ?",
        (account_id, oauth_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_linked_oauth_ids(account_id: int | str) -> list[int]:
    """Get all OAuth IDs linked to an account."""
    if isinstance(account_id, str) and account_id.isdigit():
        account_id = int(account_id)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT oauth_id FROM account_oauth_links WHERE account_id = ?",
        (account_id,),
    )
    return [row["oauth_id"] for row in cursor.fetchall()]


def get_linked_account_ids(oauth_id: int) -> list[int]:
    """Get all account IDs linked to an OAuth credential."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT account_id FROM account_oauth_links WHERE oauth_id = ?",
        (oauth_id,),
    )
    return [row["account_id"] for row in cursor.fetchall()]


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
