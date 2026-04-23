import logging
import os
import time
from pathlib import Path
import json
from typing import Any, Callable, Optional

import requests

from src.youtube_oauth import get_access_token, is_token_valid_for_token
from src.db import _get_connection

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
MAX_RETRIES = 3
RETRY_DELAY = 2


def _handle_api_error(response: requests.Response) -> str:
    """Extract and format error message from YouTube API response."""
    try:
        error_data = response.json()
        errors = error_data.get("error", {}).get("errors", [])
        if errors:
            return errors[0].get("message", error_data.get("error", {}).get("message", "Unknown error"))
        return error_data.get("error", {}).get("message", "Unknown error")
    except Exception:
        return response.text[:500] if response.text else f"HTTP {response.status_code}"


def _get_error_category(status_code: int, error_message: str) -> str:
    """Categorize error for better debugging."""
    error_lower = error_message.lower()
    if status_code == 401:
        if "expired" in error_lower or "invalid" in error_lower:
            return "TOKEN_EXPIRED"
        return "UNAUTHORIZED"
    elif status_code == 403:
        if "quota" in error_lower:
            return "QUOTA_EXCEEDED"
        elif "not verified" in error_lower or "verification" in error_lower:
            return "NOT_VERIFIED"
        elif "forbidden" in error_lower:
            return "FORBIDDEN"
        return "FORBIDDEN"
    elif status_code == 404:
        return "NOT_FOUND"
    elif status_code >= 500:
        return "SERVER_ERROR"
    return "UNKNOWN"


def youtubeApiUpload(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    account_id: str = "1",
    oauth_token: str = None,
    progress_callback: Optional[Callable[[str, str, float], None]] = None,
) -> dict | None:
    """Upload video to YouTube Data API.

    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        account_id: Account ID (used to get token if oauth_token not provided)
        oauth_token: Direct OAuth token (optional, preferred over account_id)

    Returns:
        dict with "url" and "video_id" keys, or None on failure (logs error)

    Raises:
        Exception: If token acquisition fails or video file not found
    """

    def _log(event: str, **kwargs):
        logger.info(json.dumps({"event": event, **kwargs}))

    # Get access token - validate passed token before using
    if oauth_token:
        if is_token_valid_for_token(oauth_token, account_id):
            access_token = oauth_token
        else:
            # Token expired or invalid, try to find which account has this token
            logger.info("OAuth token expired or not for this account, finding account...")
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT account_name FROM oauth_credentials WHERE token = ? AND platform = ?", (oauth_token, "youtube"))
            row = cursor.fetchone()
            if row:
                account_id = row[0]
            access_token = get_access_token(account_id)
    else:
        access_token = get_access_token(account_id)
    if not access_token:
        logger.error(f"No valid OAuth token for account {account_id}")
        raise Exception("No valid OAuth token for account")

    # Validate video file
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        raise Exception(f"Video file not found: {video_path}")

    video_path = Path(video_path)
    file_size = video_path.stat().st_size

    # Prepare metadata
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500] if tags else [],
        },
        "status": {"privacyStatus": "public"},
    }

    # Step 1: Initialize resumable upload
    logger.info(f"Initializing YouTube upload for: {title}")
    
    init_response: requests.Response | None = None
    try:
        init_response = requests.post(
            UPLOAD_URL,
            params={
                "part": "snippet,status",
                "uploadType": "resumable",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Length": str(file_size),
            },
            json=metadata,
            timeout=60,
        )

        # Handle init response errors
        if init_response.status_code == 401:
            error_msg = _handle_api_error(init_response)
            logger.error(f"401 Unauthorized - Token may be expired/invalid: {error_msg}")
            raise Exception(f"Authentication failed (401): {error_msg}. Please refresh OAuth token.")
        
        if init_response.status_code == 403:
            error_msg = _handle_api_error(init_response)
            category = _get_error_category(403, error_msg)
            logger.error(f"403 Forbidden ({category}): {error_msg}")
            raise Exception(f"Upload forbidden (403): {error_msg}. Check API quotas and account permissions.")
        
        if init_response.status_code >= 500:
            error_msg = _handle_api_error(init_response)
            logger.error(f"Server error ({init_response.status_code}): {error_msg}")
            raise Exception(f"YouTube API server error ({init_response.status_code}): {error_msg}")
        
        if init_response.status_code != 200:
            error_msg = _handle_api_error(init_response)
            logger.error(f"Upload init failed with status {init_response.status_code}: {error_msg}")
            raise Exception(f"Upload init failed ({init_response.status_code}): {error_msg}")

    except requests.RequestException as e:
        logger.error(f"Network error during upload init: {e}")
        if progress_callback:
            progress_callback("error", str(e), 0)
        _log("youtube_upload", phase="error", error=str(e))
        raise Exception(f"Network error during upload init: {e}")

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        logger.error("No upload URL in initialization response")
        raise Exception("No upload URL in response from YouTube API")

    if progress_callback:
        progress_callback("initializing", "Starting upload...", 5.0)
    _log("youtube_upload", phase="init", title=title, account_id=account_id)

    # Step 2: Upload video file
    logger.info(f"Uploading video to: {upload_url[:80]}...")
    
    upload_response: requests.Response | None = None
    try:
        chunk_size = 1024 * 1024  # 1 MB chunks
        bytes_sent = 0
        with open(video_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunk_len = len(chunk)
                if bytes_sent == 0:
                    # First chunk - send with Content-Length header
                    upload_response = requests.put(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Length": str(file_size),
                            "Content-Range": f"bytes 0-{chunk_len - 1}/{file_size}",
                        },
                        timeout=600,
                    )
                else:
                    # Subsequent chunks
                    start = bytes_sent
                    end = bytes_sent + chunk_len - 1
                    upload_response = requests.put(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Range": f"bytes {start}-{end}/{file_size}",
                        },
                        timeout=600,
                    )
                bytes_sent += chunk_len
                progress_pct = 5.0 + (bytes_sent / file_size) * 90.0
                # Call callback every ~5% or on last chunk
                if progress_callback and (bytes_sent >= file_size or progress_pct >= 5.0):
                    progress_callback("uploading", f"Uploading... {int(progress_pct)}%", progress_pct)
                if bytes_sent % (5 * 1024 * 1024) == 0 or bytes_sent >= file_size:
                    _log("youtube_upload", phase="uploading", progress=round(progress_pct, 1), bytes_sent=bytes_sent, total_bytes=file_size)

        # Handle upload response errors
        if upload_response.status_code == 401:
            error_msg = _handle_api_error(upload_response)
            logger.error(f"401 Unauthorized during upload: {error_msg}")
            raise Exception(f"Authentication failed during upload (401): {error_msg}")
        
        if upload_response.status_code == 403:
            error_msg = _handle_api_error(upload_response)
            logger.error(f"403 Forbidden during upload: {error_msg}")
            raise Exception(f"Upload forbidden (403): {error_msg}")
        
        if upload_response.status_code >= 500:
            error_msg = _handle_api_error(upload_response)
            logger.error(f"Server error during upload ({upload_response.status_code}): {error_msg}")
            raise Exception(f"YouTube server error during upload ({upload_response.status_code}): {error_msg}")
        
        if upload_response.status_code != 200:
            error_msg = _handle_api_error(upload_response)
            logger.error(f"Upload failed with status {upload_response.status_code}: {error_msg}")
            raise Exception(f"Upload failed ({upload_response.status_code}): {error_msg}")

    except requests.RequestException as e:
        logger.error(f"Network error during video upload: {e}")
        if progress_callback:
            progress_callback("error", str(e), 0)
        _log("youtube_upload", phase="error", error=str(e))
        raise Exception(f"Network error during video upload: {e}")

    # Step 3: Extract video ID from response
    if progress_callback:
        progress_callback("metadata", "Setting title, description, tags...", 97.0)
    _log("youtube_upload", phase="metadata", title=title)

    try:
        response_json = upload_response.json()
        video_id = response_json.get("id")
        
        if not video_id:
            logger.error(f"Video ID not found in API response: {response_json}")
            raise Exception("Video ID not found in API response. Upload may have completed but tracking failed.")
        
        logger.info(f"Upload successful! Video ID: {video_id}")

        if progress_callback:
            progress_callback("complete", "Upload complete!", 100.0)
        _log("youtube_upload", phase="complete", video_id=video_id, url=f"https://www.youtube.com/watch?v={video_id}")

        return {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
        }
        
    except ValueError as e:
        logger.error(f"Failed to parse API response: {e}")
        if progress_callback:
            progress_callback("error", str(e), 0)
        _log("youtube_upload", phase="error", error=str(e))
        raise Exception(f"Failed to parse API response: {e}")
