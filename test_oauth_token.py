#!/usr/bin/env python3
"""Test script to verify OAuth token validity against YouTube API."""

import json
import os
import sys
import time

# Add paths like main.py does
_app_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = _app_dir
_src_dir = os.path.join(_app_dir, "src")

for _path in [_project_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src.db import get_oauth_credentials, init_db
from src.youtube_oauth import load_tokens, is_token_valid, get_oauth_config


def get_account_name_from_user():
    """Get account name from command line or ask user."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # List available accounts
    init_db()
    creds = get_oauth_credentials(platform="youtube")
    
    if not creds:
        print("ERROR: No YouTube OAuth credentials found in database")
        print("Available accounts: none")
        sys.exit(1)
    
    print("Available YouTube accounts:")
    for i, cred in enumerate(creds, 1):
        print(f"  {i}. {cred.get('account_name', 'unknown')}")
    
    if len(creds) == 1:
        return creds[0].get("account_name", "1")
    
    print("\nEnter account name (or use: python test_oauth.py <account_name>):")
    account_name = input("> ").strip()
    return account_name or creds[0].get("account_name", "1")


def truncate_token(token: str) -> str:
    """Truncate token for display."""
    if not token:
        return "NONE"
    if len(token) <= 20:
        return token
    return f"{token[:10]}...{token[-10:]}"


def test_oauth_token(account_name: str):
    """Test OAuth token validity against YouTube API."""
    print(f"\n{'='*60}")
    print(f"OAUTH TOKEN VALIDATION TEST")
    print(f"{'='*60}")
    print(f"Account: {account_name}")
    
    # Get tokens from database
    print(f"\n[1] Loading tokens from database...")
    tokens = load_tokens(account_name)
    
    if not tokens:
        print("  FAIL: No tokens found for this account in database")
        print("  -> OAuth credential likely not stored")
        return False
    
    print("  Token found in database")
    print(f"  - access_token: {truncate_token(tokens.get('access_token', ''))}")
    print(f"  - refresh_token: {truncate_token(tokens.get('refresh_token', ''))}")
    print(f"  - saved_at: {tokens.get('saved_at', 0)} ({_format_timestamp(tokens.get('saved_at', 0))})")
    print(f"  - expires_in: {tokens.get('expires_in', 0)} seconds")
    
    # Check expiry
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    expiry_time = saved_at + expires_in - 300  # 5 min buffer
    is_expired = time.time() >= expiry_time
    
    print(f"\n[2] Token expiry check...")
    print(f"  - Token saved at: {_format_timestamp(saved_at)}")
    print(f"  - Expires in: {expires_in} seconds")
    print(f"  - Expiry time: {_format_timestamp(expiry_time)}")
    print(f"  - Current time: {_format_timestamp(time.time())}")
    print(f"  - Is expired (with 5min buffer): {'YES' if is_expired else 'NO'}")
    
    # Get access token (which may refresh)
    print(f"\n[3] Getting access token...")
    
    # Manually handle refresh since there's a bug in get_access_token
    access_token = tokens.get("access_token", "")
    refresh_token_value = tokens.get("refresh_token", "")
    
    # Check if token is expired
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    if time.time() >= saved_at + expires_in - 300:
        # Token expired, need to refresh
        print("  Token expired, attempting refresh...")
        if refresh_token_value:
            from src.youtube_oauth import refresh_token as do_refresh
            new_tokens = do_refresh(refresh_token_value, account_name)
            if new_tokens:
                access_token = new_tokens.get("access_token", "")
                print(f"  Refreshed! New access token: {truncate_token(access_token)}")
            else:
                print("  Refresh FAILED")
                access_token = None
        else:
            print("  No refresh token available")
            access_token = None
    
    if not access_token:
        print("  FAIL: No valid access token")
        return False
    
    print(f"  Access token: {truncate_token(access_token)}")
    
    # Make direct API call to YouTube
    print(f"\n[4] Testing against YouTube API...")
    import requests
    
    # Test using channels list endpoint
    test_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "snippet,contentDetails,statistics", "mine": "true"}
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    
    print(f"  URL: {test_url}")
    print(f"  Params: {params}")
    print(f"  Authorization: Bearer {truncate_token(access_token)}")
    
    response = requests.get(test_url, params=params, headers=headers, timeout=30)
    
    print(f"\n[5] API Response:")
    print(f"  Status code: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    
    try:
        response_data = response.json()
        print(f"  Body: {json.dumps(response_data, indent=2)[:2000]}")
    except:
        print(f"  Body (raw): {response.text[:1000]}")
    
    # Analyze result
    print(f"\n[6] Validation Result:")
    
    if response.status_code == 200:
        print("  STATUS: VALID")
        items = response_data.get("items", [])
        if items:
            channel = items[0]
            snippet = channel.get("snippet", {})
            print(f"  Channel: {snippet.get('title', 'unknown')}")
            print(f"  Custom URL: {snippet.get('customUrl', 'N/A')}")
        return True
        
    elif response.status_code == 401:
        error_info = response_data.get("error", {})
        error_msg = error_info.get("message", "Unknown")
        error_domain = error_info.get("domain", "Unknown")
        print(f"  STATUS: INVALID (401 Unauthorized)")
        print(f"  Error domain: {error_domain}")
        print(f"  Error message: {error_msg}")
        
        if "invalid" in error_msg.lower():
            print("  -> Token is MALFORMED or REVOKED")
        elif "expired" in error_msg.lower():
            print("  -> Token is EXPIRED")
        else:
            print("  -> Token is invalid for unknown reason")
        return False
        
    elif response.status_code == 403:
        print("  STATUS: FORBIDDEN (403)")
        error_info = response_data.get("error", {})
        print(f"  Error: {error_info}")
        return False
        
    else:
        print(f"  STATUS: UNEXPECTED ({response.status_code})")
        return False


def _format_timestamp(ts: float) -> str:
    """Format Unix timestamp to readable string."""
    if not ts:
        return "N/A"
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    account_name = get_account_name_from_user()
    valid = test_oauth_token(account_name)
    
    print(f"\n{'='*60}")
    if valid:
        print("CONCLUSION: Token is VALID")
    else:
        print("CONCLUSION: Token is INVALID or EXPIRED")
    print(f"{'='*60}\n")
    
    sys.exit(0 if valid else 1)