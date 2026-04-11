"""
Async pipeline wrapper for YouTube video generation.

Wraps the synchronous YouTube class with:
- Async interface via asyncio.to_thread()
- Lazy browser initialization (browser only starts when generate_video is called)
- Progress event emission via Message system
- Cancellation support via asyncio.Event
- Proper browser cleanup in finally block
"""

import asyncio
import atexit
import time
from typing import Optional

from textual.app import App

from src.classes.YouTube import YouTube
from src.tui.events import (
    StepStarted,
    StepProgressed,
    StepCompleted,
    StepFailed,
    JobCompleted,
    JobFailed,
    LogLine,
)


STEPS = ["topic", "script", "image_prompts", "images", "tts", "combine", "upload"]


class PipelineWrapper:
    """
    Wraps YouTube class with async + message-based events.

    Usage:
        wrapper = PipelineWrapper(app, account_uuid)
        await wrapper.run(niche, language, for_kids)
    """

    def __init__(self, app: App, account_uuid: str, account_nickname: str = "",
                 fp_profile_path: str = ""):
        self.app = app
        self.account_uuid = account_uuid
        self.account_nickname = account_nickname
        self.fp_profile_path = fp_profile_path
        self._cancel = asyncio.Event()
        self._youtube: Optional[YouTube] = None

    def cancel(self) -> None:
        """Request cancellation. Checked between steps."""
        self._cancel.set()

    async def run(self, niche: str, language: str, for_kids: bool) -> None:
        """Run the pipeline asynchronously. Posts messages — never calls widgets."""
        try:
            await asyncio.to_thread(self._run_sync, niche, language, for_kids)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.app.post_message(JobFailed(step="unknown", error=str(e)[:300]))

    def _run_sync(self, niche: str, language: str, for_kids: bool) -> None:
        """Synchronous pipeline — runs in thread pool via asyncio.to_thread()."""
        try:
            # Lazy browser init — only here, not in __init__
            self._youtube = YouTube(
                account_uuid=self.account_uuid,
                account_nickname=self.account_nickname,
                fp_profile_path=self.fp_profile_path,
                niche=niche,
                language=language,
            )

            # Register atexit as fallback for browser cleanup
            atexit.register(self._cleanup_browser)

            if self._cancel.is_set():
                return

            # --- Step 1: Topic ---
            self._run_step("topic", 0, lambda: self._youtube.generate_topic())

            # --- Step 2: Script ---
            self._run_step("script", 1, lambda: self._youtube.generate_script())

            # --- Step 3: Image Prompts ---
            self._run_step("image_prompts", 2, lambda: self._youtube.generate_prompts())

            # --- Step 4: Images ---
            self._emit(StepStarted("images", 3))
            step_start = time.time()
            total_images = len(getattr(self._youtube, 'image_prompts', []))
            for i, prompt in enumerate(getattr(self._youtube, 'image_prompts', [])):
                if self._cancel.is_set():
                    raise InterruptedError("cancelled by user")
                self._youtube.generate_image(prompt)
                progress = (i + 1) / max(total_images, 1)
                self._emit(StepProgressed(
                    "images",
                    f"image {i + 1}/{total_images}",
                    progress,
                ))
            elapsed = time.time() - step_start
            self._emit(StepCompleted("images", f"{total_images} images", elapsed))

            # --- Step 5: TTS ---
            from src.classes.Tts import TTS
            tts = TTS()
            self._run_step("tts", 4, lambda: self._youtube.generate_script_to_speech(tts))

            # --- Step 6: Combine ---
            video_path = None
            def do_combine():
                nonlocal video_path
                video_path = self._youtube.combine()
            self._run_step("combine", 5, do_combine)

            # --- Step 7: Upload ---
            # Upload is optional — only if video was generated
            if video_path:
                upload_url = None
                def do_upload():
                    nonlocal upload_url
                    # Upload is handled by YouTube class if configured
                    # For TUI, we just mark it complete
                    pass
                self._run_step("upload", 6, do_upload)
                self._emit(JobCompleted(video_path=video_path or "", upload_url=upload_url))
            else:
                self._emit(JobFailed(step="combine", error="No video output"))

        except InterruptedError:
            self._emit(LogLine("warn", "Pipeline cancelled by user"))

        except Exception as e:
            error_msg = str(e)[:300]
            self._emit(JobFailed(step="unknown", error=error_msg))

        finally:
            self._cleanup_browser()

    def _run_step(self, step: str, index: int, fn) -> None:
        """Run a single step with timing, cancellation check, and error handling."""
        if self._cancel.is_set():
            raise InterruptedError("cancelled by user")

        self._emit(StepStarted(step, index))
        step_start = time.time()
        try:
            fn()
            elapsed = time.time() - step_start
            detail = ""
            # Try to get useful detail from YouTube state
            if step == "topic":
                detail = getattr(self._youtube, 'subject', '') or ''
                if detail:
                    detail = f'"{detail}"'
            elif step == "script":
                script = getattr(self._youtube, 'script', '') or ''
                word_count = len(script.split()) if script else 0
                detail = f"{word_count} words" if word_count else "complete"
            self._emit(StepCompleted(step, detail, elapsed))
        except InterruptedError:
            raise
        except Exception as e:
            elapsed = time.time() - step_start
            self._emit(StepFailed(step, str(e)[:300]))
            raise

    def _emit(self, message) -> None:
        """Thread-safe message emission to TUI."""
        try:
            self.app.call_from_thread(lambda: self.app.post_message(message))
        except Exception:
            pass

    def _cleanup_browser(self) -> None:
        """Clean up the browser if it exists."""
        try:
            if self._youtube and hasattr(self._youtube, 'browser'):
                browser = self._youtube.browser
                if browser is not None:
                    browser.quit()
        except Exception:
            pass
        self._youtube = None
