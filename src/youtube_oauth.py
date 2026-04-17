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


def get_oauth_config() -> dict:
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "scopes": os.getenv("GOOGLE_SCOPES", "").split(),
    }


def getAuthorizationUrl(account_id: str = None) -> str:
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


def saveTokens(tokens: dict, account_id: str = None) -> None:
    if not account_id:
        return
    from src.db import _get_connection
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET oauth_token = ? WHERE id = ?",
        (json.dumps(tokens), account_id)
    )
    conn.commit()


def loadTokens(account_id: str = None) -> dict | None:
    if not account_id:
        return None
    from src.db import _get_connection
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT oauth_token FROM accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()
    if row and row[0]:
        return json.loads(row[0])
    return None


def isTokenValid(account_id: str = None) -> bool:
    tokens = loadTokens(account_id)
    if not tokens:
        return False
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    expiry_time = saved_at + expires_in - 300
    return time.time() < expiry_time


def getAccessToken(account_id: str = None) -> str | None:
    tokens = loadTokens(account_id)
    if not tokens:
        return None
    if not isTokenValid(account_id):
        refresh_token = tokens.get("refresh_token")
        if refresh_token:
            new_tokens = refreshToken(refresh_token, account_id)
            if new_tokens:
                return new_tokens.get("access_token")
        return None
    return tokens.get("access_token")


def refreshToken(refresh_token: str, account_id: str = None) -> dict | None:
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
        saveTokens(tokens, account_id)
        return tokens
    return None


def exchangeCodeForTokens(code: str, account_id: str = None) -> dict | None:
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
        saveTokens(tokens, account_id)
        return tokens
    return None


def startOAuthFlow() -> str:
    url = getAuthorizationUrl()
    webbrowser.open(url)
    return url