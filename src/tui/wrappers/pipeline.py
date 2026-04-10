"""
Async pipeline wrapper for YouTube video generation.

Wraps the synchronous YouTube class with:
- Async interface for TUI integration
- Lazy browser initialization
- Progress event emission
- Proper cleanup on cancel/interrupt
"""

import asyncio
import time
import sys
from typing import Optional
from textual.app import App

from src.classes.YouTube import YouTube
from src.classes.Tts import TTS
from src.tui.events import (
    PipelineStarted,
    PipelineStepStarted,
    PipelineStepComplete,
    PipelineProgress,
    PipelineError,
    PipelineComplete,
)


# Pipeline step definitions
PIPELINE_STEPS = [
    "Topic",
    "Script",
    "Metadata",
    "Image Prompts",
    "Images",
    "TTS",
    "Combine",
    "Upload",
]


class PipelineWrapper:
    """
    Wraps YouTube class with async + events.

    Usage:
        wrapper = PipelineWrapper(app, account_uuid, account_nickname, fp_profile_path)
        result = await wrapper.generate(niche="Tech Facts", language="English", for_kids=False)
    """

    def __init__(
        self,
        app: App,
        account_uuid: str,
        account_nickname: str,
        fp_profile_path: str,
    ):
        self.app = app
        self.account_uuid = account_uuid
        self.account_nickname = account_nickname
        self.fp_profile_path = fp_profile_path
        self.youtube: Optional[YouTube] = None
        self._cancelled = False
        self._running = False
        self._step_times: dict[str, float] = {}

    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self._running

    def _publish(self, event) -> None:
        """Post event to the TUI app."""
        self.app.post_message(event)

    async def _init_youtube(self, niche: str, language: str) -> YouTube:
        """Initialize YouTube with lazy browser creation."""
        yt = YouTube(
            account_uuid=self.account_uuid,
            account_nickname=self.account_nickname,
            fp_profile_path=self.fp_profile_path,
            niche=niche,
            language=language,
        )
        return yt

    async def _run_sync(self, coro):
        """Run a coroutine in a thread pool to avoid blocking the event loop."""
        return await asyncio.to_thread(coro)

    async def _generate_video_async(
        self, niche: str, language: str, for_kids: bool
    ) -> dict:
        """
        Run the video generation pipeline asynchronously.

        Intercepts status.* calls to emit TUI events.
        """
        result = {
            "success": False,
            "video_path": None,
            "topic": None,
            "error": None,
        }

        try:
            # Initialize TTS (needed by YouTube.generate_video)
            tts = TTS()

            # Initialize YouTube (browser will be created lazily)
            self.youtube = YouTube(
                account_uuid=self.account_uuid,
                account_nickname=self.account_nickname,
                fp_profile_path=self.fp_profile_path,
                niche=niche,
                language=language,
            )

            # Track step timing
            step_start = time.time()

            # Step 1: Generate Topic
            self._publish(PipelineStepStarted(step_name="Topic"))
            step_start = time.time()
            self.youtube.generate_topic()
            self._step_times["Topic"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Topic", duration=self._step_times["Topic"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 2: Generate Script
            self._publish(PipelineStepStarted(step_name="Script"))
            step_start = time.time()
            self.youtube.generate_script()
            self._step_times["Script"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Script", duration=self._step_times["Script"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 3: Generate Metadata
            self._publish(PipelineStepStarted(step_name="Metadata"))
            step_start = time.time()
            self.youtube.generate_metadata()
            self._step_times["Metadata"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Metadata", duration=self._step_times["Metadata"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 4: Generate Image Prompts
            self._publish(PipelineStepStarted(step_name="Image Prompts"))
            step_start = time.time()
            self.youtube.generate_prompts()
            self._step_times["Image Prompts"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Image Prompts",
                    duration=self._step_times["Image Prompts"],
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 5: Generate Images
            self._publish(PipelineStepStarted(step_name="Images"))
            step_start = time.time()
            total_images = len(self.youtube.image_prompts)
            for i, prompt in enumerate(self.youtube.image_prompts):
                if self._cancelled:
                    raise asyncio.CancelledError("Pipeline cancelled")
                self.youtube.generate_image(prompt)
                # Emit progress within step
                self._publish(
                    PipelineProgress(
                        step_name="Images",
                        message=f"Generating image {i + 1}/{total_images}",
                        progress=(i + 1) / total_images,
                    )
                )
            self._step_times["Images"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Images", duration=self._step_times["Images"]
                )
            )

            # Step 6: Generate TTS
            self._publish(PipelineStepStarted(step_name="TTS"))
            step_start = time.time()
            self.youtube.generate_script_to_speech(tts)
            self._step_times["TTS"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(step_name="TTS", duration=self._step_times["TTS"])
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 7: Combine into Video
            self._publish(PipelineStepStarted(step_name="Combine"))
            step_start = time.time()
            video_path = self.youtube.combine()
            self._step_times["Combine"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Combine", duration=self._step_times["Combine"]
                )
            )

            # Success
            result["success"] = True
            result["video_path"] = video_path
            result["topic"] = getattr(self.youtube, "subject", None)
            self._publish(PipelineComplete(output_path=video_path))

        except asyncio.CancelledError:
            result["error"] = "Pipeline cancelled"
            self._publish(
                PipelineError(step_name="", error_message="Pipeline cancelled")
            )
            raise

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            # Try to determine which step failed
            self._publish(PipelineError(step_name="", error_message=error_msg))

        return result

    async def generate(self, niche: str, language: str, for_kids: bool = False) -> dict:
        """
        Run the video generation pipeline asynchronously.

        Args:
            niche: The topic niche for the video
            language: The language for the video (e.g., "English", "Spanish")
            for_kids: Whether the video is made for kids

        Returns:
            dict with keys: success (bool), video_path (str), topic (str), error (str)
        """
        if self._running:
            return {
                "success": False,
                "video_path": None,
                "topic": None,
                "error": "Pipeline already running",
            }

        self._running = True
        self._cancelled = False
        self._step_times = {}

        # Publish pipeline started event
        self._publish(PipelineStarted(total_steps=len(PIPELINE_STEPS)))

        try:
            # Run the synchronous pipeline in a thread pool
            result = await asyncio.to_thread(
                self._run_sync_gen, niche, language, for_kids
            )
            return result
        finally:
            self._running = False

    def _run_sync_gen(self, niche: str, language: str, for_kids: bool) -> dict:
        """
        Synchronous wrapper that runs the pipeline.

        This is executed in a thread pool via asyncio.to_thread().
        """
        result = {
            "success": False,
            "video_path": None,
            "topic": None,
            "error": None,
        }

        try:
            # Initialize TTS
            tts = TTS()

            # Initialize YouTube (browser will be created lazily)
            self.youtube = YouTube(
                account_uuid=self.account_uuid,
                account_nickname=self.account_nickname,
                fp_profile_path=self.fp_profile_path,
                niche=niche,
                language=language,
            )

            # Track step timing
            step_start = time.time()

            # Step 1: Generate Topic
            self._publish(PipelineStepStarted(step_name="Topic"))
            step_start = time.time()
            self.youtube.generate_topic()
            self._step_times["Topic"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Topic", duration=self._step_times["Topic"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 2: Generate Script
            self._publish(PipelineStepStarted(step_name="Script"))
            step_start = time.time()
            self.youtube.generate_script()
            self._step_times["Script"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Script", duration=self._step_times["Script"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 3: Generate Metadata
            self._publish(PipelineStepStarted(step_name="Metadata"))
            step_start = time.time()
            self.youtube.generate_metadata()
            self._step_times["Metadata"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Metadata", duration=self._step_times["Metadata"]
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 4: Generate Image Prompts
            self._publish(PipelineStepStarted(step_name="Image Prompts"))
            step_start = time.time()
            self.youtube.generate_prompts()
            self._step_times["Image Prompts"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Image Prompts",
                    duration=self._step_times["Image Prompts"],
                )
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 5: Generate Images
            self._publish(PipelineStepStarted(step_name="Images"))
            step_start = time.time()
            total_images = len(self.youtube.image_prompts)
            for i, prompt in enumerate(self.youtube.image_prompts):
                if self._cancelled:
                    raise asyncio.CancelledError("Pipeline cancelled")
                self.youtube.generate_image(prompt)
                # Emit progress within step
                self._publish(
                    PipelineProgress(
                        step_name="Images",
                        message=f"Generating image {i + 1}/{total_images}",
                        progress=(i + 1) / total_images,
                    )
                )
            self._step_times["Images"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Images", duration=self._step_times["Images"]
                )
            )

            # Step 6: Generate TTS
            self._publish(PipelineStepStarted(step_name="TTS"))
            step_start = time.time()
            self.youtube.generate_script_to_speech(tts)
            self._step_times["TTS"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(step_name="TTS", duration=self._step_times["TTS"])
            )
            if self._cancelled:
                raise asyncio.CancelledError("Pipeline cancelled")

            # Step 7: Combine into Video
            self._publish(PipelineStepStarted(step_name="Combine"))
            step_start = time.time()
            video_path = self.youtube.combine()
            self._step_times["Combine"] = time.time() - step_start
            self._publish(
                PipelineStepComplete(
                    step_name="Combine", duration=self._step_times["Combine"]
                )
            )

            # Success
            result["success"] = True
            result["video_path"] = video_path
            result["topic"] = getattr(self.youtube, "subject", None)
            self._publish(PipelineComplete(output_path=video_path))

        except asyncio.CancelledError:
            result["error"] = "Pipeline cancelled"
            self._publish(
                PipelineError(step_name="", error_message="Pipeline cancelled")
            )

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            self._publish(PipelineError(step_name="", error_message=error_msg))

        return result

    def cancel(self) -> None:
        """
        Cancel the running pipeline.

        Sets the cancelled flag and triggers browser cleanup.
        """
        self._cancelled = True
        if self.youtube:
            self._cleanup_browser()

    def _cleanup_browser(self) -> None:
        """Clean up the browser if it exists."""
        try:
            if self.youtube and hasattr(self.youtube, "browser"):
                browser = self.youtube.browser
                if browser is not None:
                    try:
                        browser.quit()
                    except Exception:
                        pass
        except Exception:
            pass
        self.youtube = None

    def cleanup(self) -> None:
        """
        Full cleanup - cancel pipeline and close browser.
        """
        self.cancel()
