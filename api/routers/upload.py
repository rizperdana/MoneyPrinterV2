"""Upload router — POST /api/upload/{job_id}."""

import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
