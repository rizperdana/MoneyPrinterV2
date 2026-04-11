"""Video Generation Screen — Full pipeline with progress tracking.

PRIORITY screen per DESIGN.md Section 5.2.
Form → Pipeline Panel → Output → Log Viewer.
Worker pattern per Section 10.
"""

import os
import time

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static, Switch
from textual.reactive import reactive

from src.db import get_accounts
from src.tui.events import (
    StepStarted, StepProgressed, StepCompleted, StepFailed,
    LogLine, JobCompleted, JobFailed,
)
from src.tui.widgets.pipeline_panel import PipelinePanel
from src.tui.widgets.log_viewer import LogViewer
from src.tui.wrappers.pipeline import PipelineWrapper


class VideoGenScreen(Screen):
    """Video generation pipeline screen with real-time progress."""

    BINDINGS = [
        ("escape", "cancel_or_back", "Back"),
        ("ctrl+l", "clear_log", "Clear log"),
        ("ctrl+s", "toggle_scroll_lock", "Scroll lock"),
    ]

    # Reactive state per DESIGN Section 11
    is_running: reactive[bool] = reactive(False)
    current_step: reactive[str] = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wrapper: PipelineWrapper | None = None
        self._accounts: list[dict] = []
        self._start_time: float = 0.0
        self._elapsed_timer = None

    def compose(self) -> ComposeResult:
        # Title + elapsed timer
        with Horizontal():
            yield Static("[bold #e2e8f0]VIDEO GENERATION[/]", classes="screen-title")
            yield Static("", id="elapsed-label", classes="elapsed-label")

        # Form
        with Horizontal(classes="form-row"):
            yield Static("account", classes="form-label")
            yield Input(placeholder="Select YouTube account...", id="input-account",
                        classes="form-input")

        with Horizontal(classes="form-row"):
            yield Static("niche", classes="form-label")
            yield Input(placeholder="e.g., space mysteries for beginners",
                        id="input-niche", classes="form-input")

        with Horizontal(classes="form-row"):
            yield Static("language", classes="form-label")
            yield Input(placeholder="English", id="input-language", classes="form-input")

        with Horizontal(classes="form-row"):
            yield Static("for kids", classes="form-label")
            yield Switch(id="switch-kids")

        # Buttons
        with Horizontal(classes="button-row"):
            yield Button("▶ GENERATE", id="generate-btn", classes="action-primary")
            yield Button("⏹ STOP", id="stop-btn")

        # Pipeline panel
        yield Static("[#64748b]─── pipeline ──────────────────────────────────────────[/]",
                      classes="section-divider")
        yield PipelinePanel(id="pipeline-panel")

        # Output section
        yield Static("[#64748b]─── output ───────────────────────────────────────────[/]",
                      classes="section-divider")
        with Vertical(classes="output-section"):
            yield Static("[#374151](no output yet)[/]", id="output-info")

        # Log viewer
        yield Static("[#64748b]─── log ──────────────────────────────────────────────[/]",
                      classes="section-divider")
        yield LogViewer(id="log-viewer")

    def on_mount(self) -> None:
        """Load accounts and set initial state."""
        self._load_accounts()
        # Hide stop button initially
        self.query_one("#stop-btn", Button).display = False
        self.query_one("#elapsed-label", Static).display = False

    def _load_accounts(self) -> None:
        """Load YouTube accounts from database."""
        try:
            self._accounts = get_accounts(platform="youtube")
            input_acc = self.query_one("#input-account", Input)
            if self._accounts:
                names = ", ".join(a["username"] for a in self._accounts[:3])
                if len(self._accounts) > 3:
                    names += f" (+{len(self._accounts) - 3} more)"
                input_acc.placeholder = f"Accounts: {names}"
            else:
                input_acc.placeholder = "No YouTube accounts — add one first"
        except Exception:
            pass

    # --- Reactive watchers (DESIGN Section 11) ---

    def watch_is_running(self, running: bool) -> None:
        """Toggle generate/stop buttons and elapsed timer."""
        try:
            self.query_one("#generate-btn", Button).display = not running
            self.query_one("#stop-btn", Button).display = running
            self.query_one("#elapsed-label", Static).display = running

            # Disable form during generation
            for iid in ("#input-account", "#input-niche", "#input-language"):
                self.query_one(iid, Input).disabled = running
            self.query_one("#switch-kids", Switch).disabled = running
        except Exception:
            pass

    # --- Button handlers ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "generate-btn":
            self._on_generate()
        elif bid == "stop-btn":
            self._on_stop()

    def _on_generate(self) -> None:
        """Handle Generate button — start pipeline worker."""
        # Validate
        niche = self.query_one("#input-niche", Input).value.strip()
        if not niche:
            self._log("warn", "Please enter a niche/topic")
            return

        # Resolve account
        account_input = self.query_one("#input-account", Input).value.strip()
        account = None
        for acc in self._accounts:
            if str(acc["id"]) == account_input or acc["username"] == account_input:
                account = acc
                break
        if not account and self._accounts:
            account = self._accounts[0]
        if not account:
            self._log("error", "No YouTube accounts — add one first")
            return

        language = self.query_one("#input-language", Input).value.strip() or "English"
        for_kids = self.query_one("#switch-kids", Switch).value

        # Reset pipeline panel and output
        self.query_one("#pipeline-panel", PipelinePanel).reset()
        self.query_one("#output-info", Static).update("[#374151](generating...)[/]")

        # Create wrapper (DESIGN Section 10)
        self._wrapper = PipelineWrapper(
            app=self.app,
            account_uuid=str(account["id"]),
            account_nickname=account.get("nickname", account["username"]),
            fp_profile_path=account.get("profile_path", ""),
        )

        # Start elapsed timer
        self._start_time = time.time()
        self._elapsed_timer = self.set_interval(1.0, self._tick_elapsed)

        self.is_running = True
        self._log("info", f"Starting pipeline: {niche}")

        # Run worker (DESIGN Section 10 pattern)
        self.run_worker(
            self._pipeline_worker(niche, language, for_kids),
            exclusive=True,
            name="pipeline",
        )

    async def _pipeline_worker(self, niche: str, language: str, for_kids: bool) -> None:
        """Worker coroutine — posts messages, never calls widgets directly."""
        try:
            await self._wrapper.run(niche, language, for_kids)
        except Exception as e:
            self.app.post_message(JobFailed(step="worker", error=str(e)[:300]))

    def _on_stop(self) -> None:
        """Handle Stop button — cancel pipeline."""
        if self._wrapper:
            self._log("warn", "Stopping pipeline...")
            self._wrapper.cancel()

    # --- Elapsed timer ---

    def _tick_elapsed(self) -> None:
        """Update elapsed time display."""
        if self.is_running:
            elapsed = time.time() - self._start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            try:
                self.query_one("#elapsed-label", Static).update(
                    f"[#64748b]elapsed: {mins:02d}:{secs:02d}[/]"
                )
            except Exception:
                pass

    def _stop_elapsed(self) -> None:
        """Stop elapsed timer."""
        if self._elapsed_timer:
            self._elapsed_timer.stop()
            self._elapsed_timer = None

    # --- Message handlers (DESIGN Section 11) ---

    def on_step_started(self, message: StepStarted) -> None:
        """Route step start to pipeline panel."""
        self.current_step = message.step
        try:
            self.query_one("#pipeline-panel", PipelinePanel).set_active(message.step)
        except Exception:
            pass

    def on_step_progressed(self, message: StepProgressed) -> None:
        """Route progress to pipeline panel."""
        try:
            self.query_one("#pipeline-panel", PipelinePanel).update_step(
                message.step, message.detail, message.progress
            )
        except Exception:
            pass

    def on_step_completed(self, message: StepCompleted) -> None:
        """Route step completion to pipeline panel."""
        try:
            self.query_one("#pipeline-panel", PipelinePanel).complete_step(
                message.step, message.detail, message.elapsed
            )
        except Exception:
            pass

    def on_step_failed(self, message: StepFailed) -> None:
        """Route step failure to pipeline panel (DESIGN Section 14 rule)."""
        try:
            self.query_one("#pipeline-panel", PipelinePanel).fail_step(
                message.step, message.error
            )
        except Exception:
            pass

    def on_log_line(self, message: LogLine) -> None:
        """Route log lines to log viewer."""
        self._log(message.level, message.text)

    def on_job_completed(self, message: JobCompleted) -> None:
        """Pipeline finished successfully."""
        self._stop_elapsed()
        self.is_running = False

        # Update output section
        try:
            video_path = message.video_path
            parts = []
            parts.append(f"file    [#3b82f6]{video_path}[/]")
            if os.path.exists(video_path):
                size = os.path.getsize(video_path)
                if size < 1024 * 1024:
                    parts.append(f"size    [#3b82f6]{size / 1024:.1f} KB[/]")
                else:
                    parts.append(f"size    [#3b82f6]{size / (1024 * 1024):.1f} MB[/]")
            if message.upload_url:
                parts.append(f"url     [#3b82f6]{message.upload_url}[/]")
            self.query_one("#output-info", Static).update("\n".join(parts))
        except Exception:
            pass
        self._log("success", f"Pipeline complete: {message.video_path}")

    def on_job_failed(self, message: JobFailed) -> None:
        """Pipeline failed."""
        self._stop_elapsed()
        self.is_running = False
        self._log("error", f"Pipeline failed at {message.step}: {message.error}")

    # --- Log helper ---

    def _log(self, level: str, text: str) -> None:
        """Write to the log viewer."""
        try:
            self.query_one("#log-viewer", LogViewer).write_line(text, level)
        except Exception:
            pass

    # --- Key actions ---

    def action_cancel_or_back(self) -> None:
        """Escape: stop pipeline if running, else go back."""
        if self.is_running and self._wrapper:
            self._wrapper.cancel()
        else:
            self.app.action_pop_screen_or_home()

    def action_clear_log(self) -> None:
        try:
            self.query_one("#log-viewer", LogViewer).clear()
        except Exception:
            pass

    def action_toggle_scroll_lock(self) -> None:
        try:
            self.query_one("#log-viewer", LogViewer).toggle_scroll_lock()
        except Exception:
            pass
