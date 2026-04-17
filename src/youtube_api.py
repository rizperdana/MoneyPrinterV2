import os
import time
from pathlib import Path

import requests

from src.youtube_oauth import get_access_token

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def youtubeApiUpload(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    account_id: str = "1",
    oauth_token: str = None,
) -> dict | None:
    """Upload video to YouTube Data API.

    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        account_id: Account ID (used to get token if oauth_token not provided)
        oauth_token: Direct OAuth token (optional, preferred over account_id)
    """
    access_token = oauth_token or get_access_token(account_id)
    if not access_token:
        raise Exception("No valid OAuth token for account")

    if not os.path.exists(video_path):
        raise Exception(f"Video file not found: {video_path}")

    video_path = Path(video_path)
    file_size = video_path.stat().st_size

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500] if tags else [],
        },
        "status": {"privacyStatus": "public"},
    }

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

    if init_response.status_code != 200:
        raise Exception(f"Upload init failed: {init_response.text}")

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        raise Exception("No upload URL in response")

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_response = requests.put(
        upload_url,
        data=video_data,
        headers={"Content-Length": str(file_size)},
        timeout=600,
    )

    if upload_response.status_code != 200:
        raise Exception(f"Upload failed: {upload_response.text}")

    video_id = upload_response.json().get("id")
    return {
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
    }
