"""
Pipeline worker — runs YouTube generation in a threadpool, emits events.

Bridges the synchronous YouTube pipeline into FastAPI's async world
via asyncio.to_thread() and an event Queue on the Job object.
"""

import os
import sys
import asyncio
import logging

# Ensure src/ is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from api.jobs import job_manager, JobStatus
from db import add_video, add_topic, update_video_youtube_url

STEPS = ["topic", "script", "metadata", "image_prompts", "images", "tts", "combine", "thumbnail", "upload"]


async def run_job(job_id: str):
    """Run the full pipeline for a job, pushing events to its Queue."""
    job = job_manager.get(job_id)
    if not job:
        return

    job.status = JobStatus.running
    loop = asyncio.get_event_loop()

    def on_progress(
        step: str, status: str, progress: float | None = None, detail: str = ""
    ):
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

        from config import get_firefox_profile_path, get_default_model, get_verbose
        from llm_provider import select_model
        from classes.YouTube import YouTube
        from classes.Tts import TTS
        from db import add_topic, add_video, topic_exists, get_existing_videos_for_niche
        from src.youtube_oauth import get_access_token
        from src.youtube_api import youtubeApiUpload

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
        youtube._fp_profile_path = (
            fp_profile if fp_profile and os.path.isdir(fp_profile) else ""
        )
        youtube._niche = job.niche
        youtube._language = job.language
        youtube.images = []
        youtube.subject = None
        youtube.script = None
        youtube.metadata = None
        youtube.image_prompts = None
        youtube.tts_path = None
        youtube.video_path = None
        youtube.extracted_facts = None  # will be set below after research
        youtube._browser_initialized = False
        youtube._options = None
        youtube._browser = None
        youtube._wait = None
        youtube._temp_profile_dir = None

        # Set progress callback
        youtube._progress_callback = on_progress

        # Query existing videos for this niche (to avoid duplicates)
        existing_videos = []
        try:
            existing_videos = get_existing_videos_for_niche(job.niche, limit=50)
            if existing_videos and get_verbose():
                print(f" => Loaded {len(existing_videos)} existing videos for dedup context")
        except Exception as e:
            print(f"Warning: could not load existing videos: {e}")

        # RESEARCH & EXTRACT FACTS (before topic generation)
        from research import extract_facts as _extract_facts
        try:
            research_text = youtube._research_trending_topics()
            if research_text:
                facts = _extract_facts(research_text, job.niche)
                youtube.extracted_facts = facts
                if get_verbose():
                    print(f" => Extracted facts: confidence={facts.get('confidence')}, names={facts.get('person_names')}, locs={facts.get('locations')}")
        except Exception as e:
            print(f"Warning: could not extract facts: {e}")
            youtube.extracted_facts = None

        try:
            # Step 1: Topic
            on_progress("topic", "running")
            youtube.generate_topic(existing_videos=existing_videos if existing_videos else None)
            on_progress(
                "topic", "done", detail=youtube.subject[:60] if youtube.subject else ""
            )

            # Store topic in database
            if youtube.subject and youtube._niche:
                try:
                    add_topic(youtube.subject, youtube._niche, job.account)
                except Exception as e:
                    print(f"Warning: could not add topic to db: {e}")

            if job.cancel_requested:
                return None

            # Step 2: Script
            on_progress("script", "running")
            youtube.generate_script()
            on_progress("script", "done", detail=f"{len(youtube.script or '')} chars")

            if job.cancel_requested:
                return None

            # Step 3: Metadata
            on_progress("metadata", "running")
            youtube.generate_metadata()
            metadata_title = ""
            if youtube.metadata:
                metadata_title = youtube.metadata.get("title", "") or ""
            on_progress("metadata", "done", detail=metadata_title[:40])

            if job.cancel_requested:
                return None

            # Step 4: Image Prompts
            on_progress("image_prompts", "running")
            youtube.generate_prompts()
            on_progress(
                "image_prompts", "done", detail=f"{len(youtube.image_prompts)} prompts"
            )

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
                on_progress(
                    "images",
                    "running",
                    progress=(i + 1) / total,
                    detail=f"{i + 1}/{total}",
                )

            # Fill placeholders if needed
            if len(youtube.images) < total:
                missing = total - len(youtube.images)
                from run_pipeline import _generate_placeholder_images

                _generate_placeholder_images(
                    youtube, missing, offset=len(youtube.images)
                )

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
            on_progress("combine", "done", detail=f"{size_mb} MB")

            # Step 8: Thumbnail — removed (not required for YouTube)
            # on_progress("thumbnail", "running")
            # youtube.generate_thumbnail()
            # hook_path = getattr(youtube, 'hook_frame_path', None)
            # thumb_path = getattr(youtube, 'thumbnail_path', None)
            # on_progress("thumbnail", "done", detail=f"hook:{bool(hook_path)} thumb:{bool(thumb_path)}")

            # Add video to DB first (needed for auto-upload URL update)
            metadata = youtube.metadata or {}
            tags_list = (
                metadata.get("tags", [])
                if isinstance(metadata.get("tags"), list)
                else []
            )
            video_id = add_video(
                topic=youtube.subject,
                title=metadata.get("title", "") if metadata else "",
                script=youtube.script,
                platform="youtube",
                file_path=youtube.video_path,
                niche=youtube._niche,
                description=metadata.get("description", "")
                if metadata
                else None,
                tags=",".join(tags_list) if tags_list else None,
                category=metadata.get("category", "")
                if metadata and metadata.get("category")
                else None,
                account=job.account,
                language=youtube._language,
                for_kids=job.for_kids,
            )

            # Auto-upload if enabled
            upload_url = None
            if job.auto_upload:
                on_progress("upload", "running")
                try:
                    oauth_token = get_access_token(job.account or "default")
                    if not oauth_token:
                        loop.call_soon_threadsafe(job.events.put_nowait, {
                            "type": "upload_error",
                            "error": "No OAuth token — please link your YouTube account in Settings",
                        })
                        job.status = JobStatus.failed
                        return None
                    else:
                        upload_result = youtubeApiUpload(
                            video_path=youtube.video_path,
                            title=metadata.get("title", "Untitled") if metadata else "Untitled",
                            description=metadata.get("description", "") if metadata else "",
                            tags=tags_list if tags_list else [],
                            oauth_token=oauth_token,
                            account_id=job.account or "default",
                            progress_callback=lambda step, status, pct: loop.call_soon_threadsafe(job.events.put_nowait, {"type": "upload_error", "error": status}) if step == "error" else (on_progress("upload", step, detail=status) if step != "uploading" else None),
                        )
                        if upload_result and upload_result.get("url"):
                            url = upload_result["url"]
                            job.upload_url = url
                            upload_url = url
                            update_video_youtube_url(video_id, url)
                            on_progress("upload", "done", detail=url)
                        else:
                            loop.call_soon_threadsafe(job.events.put_nowait, {
                                "type": "upload_error",
                                "error": "Upload failed",
                            })
                            job.status = JobStatus.failed
                            return None
                except Exception as e:
                    logging.error(f"Auto-upload failed: {e}")
                    loop.call_soon_threadsafe(job.events.put_nowait, {
                        "type": "upload_error",
                        "error": str(e),
                    })
                    job.status = JobStatus.failed
                    return None

            # Return all video data
            return {
                "path": youtube.video_path,
                "subject": youtube.subject,
                "script": youtube.script,
                "metadata": metadata,
                "niche": youtube._niche,
                "language": youtube._language,
                "thumbnail_path": thumb_path,
                "hook_frame_path": hook_path,
                "video_id": video_id,
                "upload_url": upload_url,
            }
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

            # Video already added in _run_sync before auto-upload
            # result contains video_id and upload_url from that process

            await job.events.put(
                {
                    "type": "done",
                    "path": job.output_path,
                }
            )
        else:
            job.status = JobStatus.failed
            job.error = "Pipeline returned None"
            await job.events.put({"type": "error", "error": job.error})
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        await job.events.put({"type": "error", "error": str(e)})
