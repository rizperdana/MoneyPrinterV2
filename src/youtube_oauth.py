import datetime
import json
import os
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

import requests

ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config() -> dict:
    """Load config from config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def get_oauth_config() -> dict:
    # Try env vars first, fall back to config.json
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    scopes_env = os.getenv("GOOGLE_SCOPES", "")

    # Fall back to config.json if env vars not set
    if not client_id or not client_secret or not redirect_uri:
        config = load_config()
        google_oauth = config.get("google_oauth", {})
        client_id = client_id or google_oauth.get("client_id")
        client_secret = client_secret or google_oauth.get("client_secret")
        redirect_uri = redirect_uri or google_oauth.get("redirect_uri")
        scopes_env = scopes_env or " ".join(google_oauth.get("scopes", []))

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError(
            "Missing required OAuth config. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI env vars."
        )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": scopes_env.split() if scopes_env else [],
    }


def get_authorization_url(account_id: str = None) -> str:
    config = get_oauth_config()
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(config.get("scopes", [])),
        "access_type": "offline",
        "prompt": "consent",
    }
    if account_id:
        params["state"] = account_id
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def save_tokens(tokens: dict, account_id: str = None) -> None:
    if not account_id:
        return
    # Try new oauth_credentials table first
    try:
        from src.db import add_oauth_credential

        access_token = tokens.get("access_token", "")
        # Build payload with all token info except access_token
        payload = {k: v for k, v in tokens.items() if k != "access_token"}
        payload["saved_at"] = tokens.get("saved_at", 0)
        payload["expires_in"] = tokens.get("expires_in", 3600)
        add_oauth_credential(account_id, "youtube", access_token, json.dumps(payload))
        return
    except Exception:
        pass
    # Fallback to old accounts.oauth_token column
    from src.db import _get_connection

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET oauth_token = ? WHERE id = ?",
        (json.dumps(tokens), account_id),
    )
    conn.commit()


def load_tokens(account_id: str = None) -> dict | None:
    if not account_id:
        return None
    # Try new oauth_credentials table first
    try:
        from src.db import get_oauth_credentials

        creds = get_oauth_credentials(account_name=account_id, platform="youtube")
        if creds:
            cred = creds[0]
            token = cred.get("token", "")
            payload = json.loads(cred.get("payload", "{}"))
            return {
                "access_token": token,
                "refresh_token": payload.get("refresh_token"),
                "expires_in": payload.get("expires_in", 3600),
                "saved_at": payload.get("saved_at", 0),
            }
    except Exception:
        pass
    # Fallback to old accounts.oauth_token column
    try:
        from src.db import _get_connection

        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT oauth_token FROM accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def is_token_valid(account_id: str = None) -> bool:
    tokens = load_tokens(account_id)
    if not tokens:
        return False
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    expiry_time = saved_at + expires_in - 300
    return time.time() < expiry_time


def is_token_valid_for_token(access_token: str, account_id: str = None) -> bool:
    """Check if a specific access token is still valid.
    
    Compares against stored token for the account if available.
    If no account_id, checks if token matches stored token and hasn't expired.
    """
    tokens = load_tokens(account_id)
    if not tokens:
        return False
    # Token must match what we have stored
    if tokens.get("access_token") != access_token:
        return False
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    expiry_time = saved_at + expires_in - 300
    return time.time() < expiry_time


def get_access_token(account_id: str = None) -> str | None:
    tokens = load_tokens(account_id)
    if not tokens:
        return None
    if not is_token_valid(account_id):
        refresh_token_str = tokens.get("refresh_token")
        if refresh_token_str:
            new_tokens = refresh_token(refresh_token_str, account_id)
            if new_tokens:
                return new_tokens.get("access_token")
        return None
    return tokens.get("access_token")


def refresh_token(refresh_token: str, account_id: str = None) -> dict | None:
    config = get_oauth_config()
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if response.status_code == 200:
        data = response.json()
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": refresh_token,
            "expires_in": data.get("expires_in", 3600),
            "saved_at": time.time(),
        }
        save_tokens(tokens, account_id)
        return tokens
    return None


def exchange_code_for_tokens(code: str, account_id: str = None) -> dict | None:
    config = get_oauth_config()
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config["redirect_uri"],
        },
    )
    if response.status_code == 200:
        data = response.json()
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 3600),
            "saved_at": time.time(),
        }
        save_tokens(tokens, account_id)
        return tokens
    return None


def start_oauth_flow() -> str:
    url = get_authorization_url()
    webbrowser.open(url)
    return url


def get_oauth_status(account_id: str = None) -> str:
    """Get OAuth connection status for an account."""
    if not account_id:
        return "Not connected"
    tokens = load_tokens(account_id)
    if not tokens:
        return "Not connected"
    saved_at = tokens.get("saved_at", 0)
    if saved_at:
        dt = datetime.datetime.fromtimestamp(saved_at)
        return f"Connected (last updated: {dt.strftime('%Y-%m-%d %H:%M')})"
    return "Connected"
