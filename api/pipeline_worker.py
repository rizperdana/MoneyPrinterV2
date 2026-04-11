"""
Pipeline worker — runs YouTube generation in a threadpool, emits events.

Bridges the synchronous YouTube pipeline into FastAPI's async world
via asyncio.to_thread() and an event Queue on the Job object.
"""

import os
import sys
import asyncio

# Ensure src/ is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from api.jobs import job_manager, JobStatus

STEPS = ["topic", "script", "metadata", "image_prompts", "images", "tts", "combine"]


async def run_job(job_id: str):
    """Run the full pipeline for a job, pushing events to its Queue."""
    job = job_manager.get(job_id)
    if not job:
        return

    job.status = JobStatus.running
    loop = asyncio.get_event_loop()

    def on_progress(step: str, status: str, progress: float | None = None, detail: str = ""):
        """Callback invoked from the sync pipeline thread."""
        job.current_step = step
        job.step_index = STEPS.index(step) if step in STEPS else job.step_index
        job.step_progress = progress
        event = {
            "type": "progress",
            "step": step,
            "status": status,
            "progress": progress,
            "detail": detail,
        }
        loop.call_soon_threadsafe(job.events.put_nowait, event)

    def _run_sync():
        """Synchronous pipeline execution."""
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_project_root, ".env"))

        from config import get_firefox_profile_path, get_default_model
        from llm_provider import select_model
        from classes.YouTube import YouTube
        from classes.Tts import TTS

        # Select LLM model
        model = get_default_model()
        if model:
            select_model(model)

        tts = TTS()
        fp_profile = get_firefox_profile_path()

        # Create YouTube instance (no browser unless uploading)
        youtube = YouTube.__new__(YouTube)
        youtube._account_uuid = job.account or "web-api"
        youtube._account_nickname = job.account or "Web API"
        youtube._fp_profile_path = fp_profile if fp_profile and os.path.isdir(fp_profile) else ""
        youtube._niche = job.niche
        youtube._language = job.language
        youtube.images = []
        youtube.subject = None
        youtube.script = None
        youtube.metadata = None
        youtube.image_prompts = None
        youtube.tts_path = None
        youtube.video_path = None
        youtube._browser_initialized = False
        youtube._options = None
        youtube._browser = None
        youtube._wait = None
        youtube._temp_profile_dir = None

        # Set progress callback
        youtube._progress_callback = on_progress

        try:
            # Step 1: Topic
            on_progress("topic", "running")
            youtube.generate_topic()
            on_progress("topic", "done", detail=youtube.subject[:60] if youtube.subject else "")

            if job.cancel_requested:
                return None

            # Step 2: Script
            on_progress("script", "running")
            youtube.generate_script()
            on_progress("script", "done", detail=f"{len(youtube.script)} chars")

            if job.cancel_requested:
                return None

            # Step 3: Metadata
            on_progress("metadata", "running")
            youtube.generate_metadata()
            on_progress("metadata", "done", detail=youtube.metadata.get("title", "")[:40])

            if job.cancel_requested:
                return None

            # Step 4: Image Prompts
            on_progress("image_prompts", "running")
            youtube.generate_prompts()
            on_progress("image_prompts", "done", detail=f"{len(youtube.image_prompts)} prompts")

            if job.cancel_requested:
                return None

            # Step 5: Images
            on_progress("images", "running")
            total = len(youtube.image_prompts)
            for i, prompt in enumerate(youtube.image_prompts):
                if job.cancel_requested:
                    return None
                result = youtube.generate_image(prompt)
                if result:
                    youtube.images.append(result)
                on_progress("images", "running", progress=(i + 1) / total,
                            detail=f"{i + 1}/{total}")

            # Fill placeholders if needed
            if len(youtube.images) < total:
                missing = total - len(youtube.images)
                from run_pipeline import _generate_placeholder_images
                _generate_placeholder_images(youtube, missing, offset=len(youtube.images))

            on_progress("images", "done", detail=f"{len(youtube.images)} images")

            if job.cancel_requested:
                return None

            # Step 6: TTS
            on_progress("tts", "running")
            youtube.generate_script_to_speech(tts)
            on_progress("tts", "done")

            if job.cancel_requested:
                return None

            # Step 7: Combine
            on_progress("combine", "running")
            path = youtube.combine()
            youtube.video_path = os.path.abspath(path)
            size_mb = os.path.getsize(youtube.video_path) / 1024 / 1024
            on_progress("combine", "done", detail=f"{size_mb:.1f} MB")

            return {"path": youtube.video_path}
        finally:
            if hasattr(youtube, "_browser") and youtube._browser:
                try:
                    youtube._browser.quit()
                except Exception:
                    pass

    try:
        result = await asyncio.to_thread(_run_sync)
        if job.cancel_requested:
            job.status = JobStatus.cancelled
            await job.events.put({"type": "cancelled"})
        elif result:
            job.status = JobStatus.done
            job.output_path = result.get("path")
            await job.events.put({
                "type": "done",
                "path": job.output_path,
            })
        else:
            job.status = JobStatus.failed
            job.error = "Pipeline returned None"
            await job.events.put({"type": "error", "error": job.error})
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        await job.events.put({"type": "error", "error": str(e)})
