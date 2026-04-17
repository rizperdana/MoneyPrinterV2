"""Upload router — POST /api/upload/{job_id}."""

import os
import sys

_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, HTTPException, BackgroundTasks

from api.jobs import job_manager, JobStatus

router = APIRouter()


@router.post("/upload/{job_id}")
async def upload_video(job_id: str, bg: BackgroundTasks):
    """Upload a completed job's video to YouTube."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.done:
        raise HTTPException(status_code=400, detail="Job is not complete")
    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=400, detail="Video file not found")

    # Run upload in background
    bg.add_task(_do_upload, job)
    return {"status": "uploading", "job_id": job_id}


async def _do_upload(job):
    """Upload video to YouTube in a background task."""
    import asyncio

    def _sync_upload():
        from config import get_firefox_profile_path
        from classes.YouTube import YouTube

        fp_profile = get_firefox_profile_path()
        if not fp_profile or not os.path.isdir(fp_profile):
            raise ValueError("No valid Firefox profile configured")

        yt = YouTube(
            account_uuid=job.account,
            account_nickname=job.account,
            fp_profile_path=fp_profile,
            niche=job.niche,
            language=job.language,
        )
        yt.video_path = job.output_path
        try:
            success_flag, result = yt.upload_video()
            if success_flag:
                job.upload_url = result
            else:
                job.error = f"Upload failed: {result}"
        finally:
            if hasattr(yt, "_browser") and yt._browser:
                try:
                    yt._browser.quit()
                except Exception:
                    pass

    try:
        await asyncio.to_thread(_sync_upload)
    except Exception as e:
        job.error = f"Upload error: {str(e)}"


@router.post("/videos/{video_id}/upload")
async def upload_video_by_id(
    video_id: int,
    bg: BackgroundTasks,
    platform: str = "youtube",
    account_name: str = None,
    account_id: int = None,
):
    """Upload a video from the database directly by its video_id.

    This bypasses job_manager so it works even after server restart.
    Supported platforms: youtube, tiktok
    Optional account_name: select specific account instead of first available
    Optional account_id: use linked OAuth credentials for API upload
    """
    import json

    # Look up video from database
    from db import get_video_by_id

    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found in database")

    # Validate file exists
    file_path = video.get("file_path") or video.get("path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=400, detail=f"Video file not found: {file_path}"
        )

    # Read accounts from .mp cache files (primary source)
    cache_file = os.path.join(_project_root, ".mp", f"{platform}.json")
    accounts = []
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
            accounts = data.get("accounts", [])

    if not accounts:
        raise HTTPException(status_code=400, detail=f"No {platform} account configured")

    # Select account by name or use first available
    if account_name:
        account = next(
            (a for a in accounts if a.get("id") == account_name), accounts[0]
        )
    else:
        account = accounts[0]

    # Get OAuth credentials when account_id is provided
    oauth_token = None
    if account_id and platform == "youtube":
        from db import get_linked_oauth_ids, get_oauth_credentials_by_ids

        oauth_ids = get_linked_oauth_ids(account_id)
        if oauth_ids:
            oauth_creds = get_oauth_credentials_by_ids(oauth_ids)
            # Filter by platform
            oauth_creds = [c for c in oauth_creds if c["platform"] == "youtube"]
            if oauth_creds:
                oauth_token = oauth_creds[0].get("token")

    # Run upload in background
    bg.add_task(_do_upload_video, file_path, video, account, platform, oauth_token)
    return {
        "status": "uploading",
        "video_id": video_id,
        "platform": platform,
        "account": account.get("id"),
    }


async def _do_upload_video(
    file_path: str,
    video: dict,
    account: dict,
    platform: str = "youtube",
    oauth_token: str = None,
):
    """Upload video to YouTube or TikTok in a background task."""
    import asyncio

    def _sync_upload():
        import logging

        # If we have oauth_token for youtube, use API upload instead of browser
        if oauth_token and platform == "youtube":
            try:
                from src.youtube_api import youtubeApiUpload

                result = youtubeApiUpload(
                    video_path=file_path,
                    title=video.get("title", "Untitled"),
                    description=video.get("description", ""),
                    tags=video.get("tags", "").split(",") if video.get("tags") else [],
                    oauth_token=oauth_token,
                )
                if result:
                    logging.info(f"API upload successful: {result.get('url')}")
                    return
            except Exception as e:
                logging.error(f"YouTube API upload failed: {e}")
                # Fall back to browser upload

        # Browser-based upload
        from classes.YouTube import YouTube

        # Use firefox_profile from account, fall back to config
        fp_profile = account.get("firefox_profile")
        if not fp_profile or not os.path.isdir(fp_profile):
            from config import get_firefox_profile_path

            fp_profile = get_firefox_profile_path()
            if not fp_profile or not os.path.isdir(fp_profile):
                raise ValueError("No valid Firefox profile configured")

        yt = YouTube(
            account_uuid=account.get("id") or account.get("uuid"),
            account_nickname=account.get("nickname"),
            fp_profile_path=fp_profile,
            niche=video.get("niche") or video.get("topic") or "",
            language=video.get("language") or "English",
        )
        yt.video_path = file_path
        # Set metadata dict directly so upload functions use existing data
        yt.metadata = {
            "title": video.get("title", "Untitled"),
            "description": video.get("description", ""),
            "tags": video.get("tags", "").split(",") if video.get("tags") else [],
        }
        try:
            if platform == "tiktok":
                success_flag, result = yt.upload_to_tiktok()
            else:
                success_flag, result = yt.upload_video()
            if not success_flag:
                raise Exception(f"Upload failed: {result}")
        finally:
            if hasattr(yt, "_browser") and yt._browser:
                try:
                    yt._browser.quit()
                except Exception:
                    pass

    try:
        await asyncio.to_thread(_sync_upload)
    except Exception as e:
        # Log error - in a production system you'd want to update a job status
        print(f"Upload error: {e}")
