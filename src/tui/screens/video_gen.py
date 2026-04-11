"""Video Generation Screen - Full pipeline with progress tracking."""

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
    Switch,
)

from src.db import get_accounts
from src.tui.events import (
    PipelineStarted,
    PipelineStepStarted,
    PipelineStepComplete,
    PipelineProgress,
    PipelineError,
    PipelineComplete,
)
from src.tui.widgets.progress import PipelineProgress as PipelineProgressWidget
from src.tui.widgets.log_viewer import LogViewerWithControls
from src.tui.wrappers.pipeline import PipelineWrapper


# Supported languages
LANGUAGES = [
    ("English", "English"),
    ("Spanish", "Spanish"),
    ("French", "French"),
    ("German", "German"),
    ("Portuguese", "Portuguese"),
    ("Italian", "Italian"),
    ("Japanese", "Japanese"),
    ("Korean", "Korean"),
    ("Chinese", "Chinese"),
    ("Hindi", "Hindi"),
]


class VideoGenScreen(Screen):
    """Video generation pipeline screen with real-time progress."""

    CSS = """
    VideoGenScreen {
        layout: vertical;
        height: 100%;
        padding: 1;
    }

    .screen-header {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    .section-header {
        width: 100%;
        height: auto;
        text-style: bold;
        color: $primary;
        padding-top: 1;
        padding-bottom: 1;
    }

    .form-row {
        height: auto;
        width: 100%;
        padding: 0 0;
    }

    .form-label {
        width: 1fr;
        height: auto;
        content-align: left middle;
        color: $text-muted;
    }

    .form-input {
        width: 2fr;
        height: auto;
    }

    .progress-section {
        height: auto;
        min-height: 3;
        max-height: 12;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .log-section {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .output-section {
        height: auto;
        min-height: 3;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .button-row {
        height: auto;
        width: 100%;
        align: center middle;
    }

    #btn-stop {
        display: none;
    }

    .btn-disabled {
        opacity: 0.5;
    }
    """

    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        self._app = app
        self._pipeline: PipelineWrapper = None
        self._running_task = None
        self._accounts: list[dict] = []
        self._selected_account: dict = None

    def compose(self) -> ComposeResult:
        """Compose the video generation screen."""
        # Header
        yield Static("🎬 VIDEO GENERATION", classes="screen-header")

        with Vertical(id="form-container"):
            # Account Selection - use Input instead of Select
            with Horizontal(classes="form-row"):
                yield Static("Account:", classes="form-label")
                yield Input(
                    placeholder="Select YouTube account...",
                    id="input-account",
                    classes="form-input",
                )

            # Niche Input
            with Horizontal(classes="form-row"):
                yield Static("Niche:", classes="form-label")
                yield Input(
                    placeholder="e.g., Tech Facts, Space Wonders, Animal Kingdom",
                    id="input-niche",
                    classes="form-input",
                )

            # Language Selection - use Input with placeholder
            with Horizontal(classes="form-row"):
                yield Static("Language:", classes="form-label")
                yield Input(
                    placeholder="English",
                    id="input-language",
                    classes="form-input",
                )

            # For Kids Toggle
            with Horizontal(classes="form-row"):
                yield Static("For Kids:", classes="form-label")
                yield Switch(id="switch-for-kids", classes="form-input")

        # Pipeline Progress
        with Container(classes="progress-section"):
            yield PipelineProgressWidget(
                steps=[
                    "Topic",
                    "Script",
                    "Metadata",
                    "Image Prompts",
                    "Images",
                    "TTS",
                    "Combine",
                ],
                id="pipeline-progress",
            )

        # Button Row
        with Horizontal(classes="button-row"):
            yield Button("Generate Video", variant="primary", id="btn-generate")
            yield Button("Stop", variant="error", id="btn-stop")

        # Output Section
        with Vertical(classes="output-section"):
            yield Static("Output", classes="section-header")
            yield Static("No output yet", id="output-path")
            yield Static("", id="output-size")
            with Horizontal():
                yield Button("Play", variant="success", id="btn-play", disabled=True)
                yield Button(
                    "Upload", variant="primary", id="btn-upload", disabled=True
                )

        # Log Viewer
        with Container(classes="log-section"):
            yield LogViewerWithControls(id="log-viewer")

    def on_mount(self) -> None:
        """Handle screen mount - load accounts."""
        self._load_accounts()
        self._setup_log(
            "Video Generation screen ready. Select an account and enter a niche to begin."
        )

    def _load_accounts(self) -> None:
        """Load YouTube accounts from database."""
        try:
            accounts = get_accounts(platform="youtube")
            self._accounts = accounts

            # Show account count in the input placeholder
            input_acc = self.query_one("#input-account", Input)
            if accounts:
                account_names = ", ".join([acc["username"] for acc in accounts[:3]])
                if len(accounts) > 3:
                    account_names += f" (+{len(accounts) - 3} more)"
                input_acc.placeholder = f"Accounts: {account_names}"
                self._setup_log(f"Loaded {len(accounts)} YouTube account(s)")
            else:
                input_acc.placeholder = "No YouTube accounts - add one first"
                self._setup_log(
                    "No YouTube accounts found. Please add an account first.", "WARN"
                )
        except Exception as e:
            self._setup_log(f"Error loading accounts: {e}", "ERROR")

    def _get_account_details(self, account_id) -> dict:
        """Get account details by ID."""
        for acc in self._accounts:
            if acc["id"] == account_id:
                return acc
        return None

    def _setup_log(self, message: str, level: str = "INFO") -> None:
        """Write to the log viewer."""
        try:
            log_viewer = self.query_one("#log-viewer", LogViewerWithControls)
            log_viewer.log_viewer.write_entry(message, level)
        except Exception:
            pass

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable form controls during pipeline execution."""
        generate_btn = self.query_one("#btn-generate", Button)
        stop_btn = self.query_one("#btn-stop", Button)
        input_acc = self.query_one("#input-account", Input)
        input_niche = self.query_one("#input-niche", Input)
        input_lang = self.query_one("#input-language", Input)
        switch_kids = self.query_one("#switch-for-kids", Switch)

        generate_btn.display = enabled
        stop_btn.display = not enabled

        input_acc.disabled = not enabled
        input_niche.disabled = not enabled
        input_lang.disabled = not enabled
        switch_kids.disabled = not enabled

    def _show_output(self, video_path: str) -> None:
        """Display the output video information."""
        output_path = self.query_one("#output-path", Static)
        output_size = self.query_one("#output-size", Static)
        btn_play = self.query_one("#btn-play", Button)
        btn_upload = self.query_one("#btn-upload", Button)

        output_path.update(f"📁 {video_path}")

        # Get file size
        if os.path.exists(video_path):
            size_bytes = os.path.getsize(video_path)
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            output_size.update(f"📊 Size: {size_str}")

            btn_play.disabled = False
            btn_upload.disabled = False
        else:
            output_size.update("⚠️ File not found")
            btn_play.disabled = True
            btn_upload.disabled = True

    def _reset_output(self) -> None:
        """Reset the output section."""
        output_path = self.query_one("#output-path", Static)
        output_size = self.query_one("#output-size", Static)
        btn_play = self.query_one("#btn-play", Button)
        btn_upload = self.query_one("#btn-upload", Button)

        output_path.update("No output yet")
        output_size.update("")
        btn_play.disabled = True
        btn_upload.disabled = True

    async def _on_generate_click(self) -> None:
        """Handle Generate button click."""
        # Get form values
        input_acc = self.query_one("#input-account", Input)
        input_niche = self.query_one("#input-niche", Input)
        input_lang = self.query_one("#input-language", Input)
        switch_kids = self.query_one("#switch-for-kids", Switch)

        # Parse account ID from input (format: "id:username")
        account_input = input_acc.value.strip()

        # Validate inputs
        if not account_input:
            self._setup_log("Please select a YouTube account", "WARN")
            return

        if not input_niche.value.strip():
            self._setup_log("Please enter a niche/topic", "WARN")
            return

        # Parse account - either "id:username" or just select from the list
        try:
            # Try to find account by ID
            account = None
            for acc in self._accounts:
                if str(acc["id"]) == account_input or acc["username"] == account_input:
                    account = acc
                    break

            if not account:
                # Use first available account
                if self._accounts:
                    account = self._accounts[0]
                else:
                    self._setup_log("No YouTube accounts available", "ERROR")
                    return
        except Exception as e:
            self._setup_log(f"Invalid account: {e}", "ERROR")
            return

        niche = input_niche.value.strip()
        language = input_lang.value.strip() or "English"
        for_kids = switch_kids.value

        # Get account details
        if not account:
            self._setup_log("Invalid account selected", "ERROR")
            return

        # Reset output and progress
        self._reset_output()
        progress = self.query_one("#pipeline-progress", PipelineProgressWidget)
        progress.reset()

        # Disable controls and show stop button
        self._set_controls_enabled(False)
        self._setup_log(f"Starting pipeline for niche: {niche}", "INFO")

        # Create pipeline wrapper
        self._pipeline = PipelineWrapper(
            app=self.app,
            account_uuid=str(account["id"]),
            account_nickname=account.get("nickname", account["username"]),
            fp_profile_path=account.get("profile_path", ""),
        )

        # Start async generation
        self._running_task = self.app.call_later(
            self._run_pipeline, niche, language, for_kids
        )

    async def _run_pipeline(self, niche: str, language: str, for_kids: bool) -> None:
        """Run the pipeline asynchronously."""
        try:
            result = await self._pipeline.generate(niche, language, for_kids)

            if result["success"]:
                self._setup_log(
                    f"✅ Pipeline complete! Video: {result['video_path']}", "INFO"
                )
                self._show_output(result["video_path"])
            else:
                error_msg = result.get("error", "Unknown error")
                self._setup_log(f"❌ Pipeline failed: {error_msg}", "ERROR")

        except Exception as e:
            self._setup_log(f"❌ Unexpected error: {e}", "ERROR")
        finally:
            self._set_controls_enabled(True)
            self._running_task = None

    def _on_stop_click(self) -> None:
        """Handle Stop button click."""
        if self._pipeline:
            self._setup_log("Stopping pipeline...", "WARN")
            self._pipeline.cancel()
            self._setup_log("Pipeline stop requested", "INFO")

    def _on_play_click(self) -> None:
        """Handle Play button click - open video in default player."""
        output_path = self.query_one("#output-path", Static)
        video_path = output_path.renderable.strip()

        if video_path and os.path.exists(video_path):
            try:
                import subprocess

                # Open with default video player
                if sys.platform == "darwin":
                    subprocess.run(["open", video_path])
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", video_path])
                elif sys.platform == "win32":
                    subprocess.run(["start", "", video_path], shell=True)
                self._setup_log(f"Opening video: {video_path}", "INFO")
            except Exception as e:
                self._setup_log(f"Failed to open video: {e}", "ERROR")
        else:
            self._setup_log("Video file not found", "WARN")

    def _on_upload_click(self) -> None:
        """Handle Upload button click - navigate to upload screen."""
        self._setup_log("Navigate to Upload screen to upload the video", "INFO")
        # TODO: Navigate to upload screen when implemented
        # self.app.push_screen("upload")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button press events."""
        button_id = event.button.id

        if button_id == "btn-generate":
            self.app.call_later(self._on_generate_click)
        elif button_id == "btn-stop":
            self._on_stop_click()
        elif button_id == "btn-play":
            self._on_play_click()
        elif button_id == "btn-upload":
            self._on_upload_click()

    # Pipeline event handlers
    def on_pipeline_started(self, event: PipelineStarted) -> None:
        """Handle pipeline started event."""
        self._setup_log(f"Pipeline started ({event.total_steps} steps)", "INFO")

    def on_pipeline_step_started(self, event: PipelineStepStarted) -> None:
        """Handle pipeline step started event."""
        self._setup_log(f"→ {event.step_name} started", "INFO")

    def on_pipeline_step_complete(self, event: PipelineStepComplete) -> None:
        """Handle pipeline step complete event."""
        self._setup_log(f"✓ {event.step_name} complete ({event.duration:.1f}s)", "INFO")

    def on_pipeline_progress(self, event: PipelineProgress) -> None:
        """Handle pipeline progress event."""
        self._setup_log(f"  {event.message} ({event.progress:.0%})", "INFO")

    def on_pipeline_error(self, event: PipelineError) -> None:
        """Handle pipeline error event."""
        self._setup_log(f"✗ Error: {event.error_message}", "ERROR")

    def on_pipeline_complete(self, event: PipelineComplete) -> None:
        """Handle pipeline complete event."""
        if event.output_path:
            self._setup_log(f"Pipeline complete: {event.output_path}", "INFO")
        else:
            self._setup_log("Pipeline complete", "INFO")
