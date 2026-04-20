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
    account_id: str = None,
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

    # Select account by name, video's account, or first available
    # Use video's account field as default when not specified
    target_account_id = account_name or video.get("account")
    if target_account_id:
        account = next(
            (a for a in accounts if a.get("id") == target_account_id), accounts[0]
        )
    else:
        account = accounts[0]

    # Get OAuth credentials
    oauth_token = None
    oauth_lookup_id = account_id or target_account_id
    if platform == "youtube":
        from src.db import get_linked_oauth_ids, get_oauth_credentials_by_ids, get_oauth_credentials

        oauth_ids = get_linked_oauth_ids(oauth_lookup_id)
        if oauth_ids:
            oauth_creds = get_oauth_credentials_by_ids(oauth_ids)
            oauth_creds = [c for c in oauth_creds if c["platform"] == "youtube"]
            if oauth_creds:
                oauth_token = oauth_creds[0].get("token")

        # Fallback: if no linked credentials, try direct lookup by account_name
        if not oauth_token:
            direct_creds = get_oauth_credentials(account_name=oauth_lookup_id, platform="youtube")
            if direct_creds:
                oauth_token = direct_creds[0].get("token")

    # Create job for WebSocket event streaming
    upload_job = job_manager.create(
        account=account.get("id", "unknown"),
        niche="",
        language="",
    )
    upload_job.status = JobStatus.running

    # Emit initial progress
    upload_job.events.put_nowait({
        "type": "upload_progress",
        "step": "initializing",
        "status": "Starting upload...",
        "progress": 5,
    })

    # Run upload in background
    bg.add_task(_do_upload_video, file_path, video, account, platform, oauth_token, upload_job, oauth_lookup_id)
    return {
        "status": "uploading",
        "video_id": video_id,
        "platform": platform,
        "account": account.get("id"),
        "job_id": upload_job.id,
    }


async def _do_upload_video(
    file_path: str,
    video: dict,
    account: dict,
    platform: str = "youtube",
    oauth_token: str = None,
    job=None,
    oauth_account_id: str = None,
):
    """Upload video to YouTube or TikTok in a background task."""
    import asyncio
    import logging

    def _emit_progress(step, status_msg, progress):
        """Thread-safe event emission to job.events via asyncio bridge."""
        event = {"type": "upload_progress", "step": step, "status": status_msg, "progress": progress}
        if job:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(job.events.put_nowait, event)
            except RuntimeError:
                pass  # No event loop in this thread context

    def _sync_upload():

        # YouTube API upload (OAuth required)
        if oauth_token and platform == "youtube":
            try:
                from src.youtube_api import youtubeApiUpload

                result = youtubeApiUpload(
                    video_path=file_path,
                    title=video.get("title", "Untitled"),
                    description=video.get("description", ""),
                    tags=video.get("tags", "").split(",") if video.get("tags") else [],
                    oauth_token=oauth_token,
                    account_id=oauth_account_id,
                    progress_callback=_emit_progress,
                )
                if result:
                    logging.info(f"API upload successful: {result.get('url')}")
                return result
            except Exception as e:
                logging.error(f"YouTube API upload failed: {e}")
                raise Exception(
                    "YouTube OAuth upload failed. Your OAuth token may be expired or invalid. "
                    "Please re-authenticate your YouTube account and try again."
                ) from e

        # No OAuth token provided
        if platform == "youtube":
            raise Exception(
                "No OAuth token provided. Please link your YouTube account with OAuth "
                "credentials to enable video uploads."
            )

        # TikTok uploads require OAuth - no browser fallback
        if platform == "tiktok":
            raise Exception(
                "TikTok uploads require OAuth credentials. Please configure TikTok API access."
            )

        raise Exception(f"Unsupported platform: {platform}")

    result = None
    try:
        result = await asyncio.to_thread(_sync_upload)
        # Emit completion event
        if job:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(job.events.put_nowait, {
                    "type": "upload_complete",
                    "url": result.get("url", "") if result else "",
                    "video_id": result.get("video_id", "") if result else "",
                })
                job.status = JobStatus.done
                if result:
                    job.upload_url = result.get("url", "")
            except RuntimeError:
                pass
    except Exception as e:
        # Emit error event
        logging.error(f"Upload error: {e}")
        if job:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(job.events.put_nowait, {
                    "type": "upload_error",
                    "error": str(e),
                })
                job.status = JobStatus.failed
                job.error = str(e)
            except RuntimeError:
                pass
