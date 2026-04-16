"""Generate router — POST /api/generate, GET /api/jobs."""

import os
import sys

_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.jobs import job_manager, JobStatus
from api.pipeline_worker import run_job
from api.models import GenerateRequest, JobResponse

router = APIRouter()


@router.get("/topics")
async def list_topics(account: str | None = None):
    """List previously used topics."""
    from db import get_topics

    topics = get_topics(account=account, limit=50)
    return {"topics": topics}


@router.post("/generate", response_model=JobResponse)
async def start_generation(req: GenerateRequest, bg: BackgroundTasks):
    """Start a video generation pipeline."""
    # Check for duplicate topic
    from db import get_topics, topic_exists

    existing = get_topics(niche=req.niche, limit=100)
    if existing:
        topic_list = [t.get("topic", "") for t in existing]

    job = job_manager.create(
        account=req.account,
        niche=req.niche,
        language=req.language,
        for_kids=req.for_kids,
    )
    bg.add_task(run_job, job.id)
    return JobResponse(job_id=job.id, status=job.status.value)


@router.get("/jobs")
async def list_jobs():
    """List all jobs."""
    return [
        {
            "id": j.id,
            "status": j.status.value,
            "account": j.account,
            "niche": j.niche,
            "step": j.current_step,
            "step_index": j.step_index,
            "created_at": j.created_at,
            "output_path": j.output_path,
            "error": j.error,
        }
        for j in job_manager.list()
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "status": job.status.value,
        "account": job.account,
        "niche": job.niche,
        "current_step": job.current_step,
        "step_index": job.step_index,
        "step_progress": job.step_progress,
        "output_path": job.output_path,
        "upload_url": job.upload_url,
        "error": job.error,
        "created_at": job.created_at,
    }


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running or queued job."""
    if job_manager.cancel(job_id):
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found or not cancellable")


@router.get("/videos")
async def list_videos(platform: str | None = None):
    """List previously generated videos with script included for debugging."""
    from db import get_videos

    videos = get_videos(platform=platform, limit=50)
    # Add script to each video response for debugging
    for v in videos:
        if v.get("script"):
            v["script_preview"] = v["script"][:200] + "..." if len(v.get("script", "")) > 200 else v.get("script", "")
    return {"videos": videos}


@router.get("/videos/{video_id}")
async def get_video_detail(video_id: int):
    """Get a specific video with full script for debugging."""
    from db import get_video_by_id

    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
