"""Video Detail Screen — Full video information display."""

import asyncio
import httpx

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

_API_BASE = "http://localhost:8000"


class VideoDetailScreen(Screen):
    """Screen showing full video details."""

    def __init__(self, video_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self._video_id = video_id
        self._video_data = None

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]VIDEO DETAIL[/]", classes="screen-title")

        with Vertical(id="detail-content"):
            yield Static("[#64748b]Loading...[/]", id="detail-loading")

        with Horizontal(classes="detail-actions"):
            yield Button(
                "[↑] Upload to YouTube", id="btn-upload", classes="action-primary"
            )
            yield Button("[←] Back", id="btn-back", classes="action-secondary")

    def on_mount(self) -> None:
        """Load video data on mount."""
        self._load_video()

    def _load_video(self) -> None:
        """Load video data from database."""
        if self._video_id is None:
            self._show_empty()
            return

        try:
            from src.db import get_videos

            videos = get_videos(limit=200)
            for v in videos:
                if v.get("id") == self._video_id:
                    self._video_data = v
                    break

            if self._video_data:
                self._render_details()
            else:
                self._show_empty()
        except Exception as e:
            self._show_error(str(e))

    def _render_details(self) -> None:
        """Render video details to the screen."""
        v = self._video_data

        title = v.get("title", "Untitled")
        description = v.get("description", "")
        script = v.get("script", "")
        tags = v.get("tags", "")
        topic = v.get("niche", "")
        language = v.get("language", "English")
        platform = v.get("platform", "")
        file_path = v.get("file_path", "")
        created_at = v.get("created_at", "")

        content = Vertical()
        content.add(Static("[bold #e2e8f0]Title[/]", classes="detail-label"))
        content.add(Static(f"[#a5b4fc]{title}[/]", classes="detail-value"))
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Description[/]", classes="detail-label"))
        content.add(
            Static(f"[#d1d5db]{description or '(none)'}[/]", classes="detail-value")
        )
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Script[/]", classes="detail-label"))
        content.add(
            Static(
                f"[#9ca3af]{script or '(none)'}[/]",
                classes="detail-value detail-script",
            )
        )
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Tags[/]", classes="detail-label"))
        content.add(Static(f"[#10b981]{tags or '(none)'}[/]", classes="detail-value"))
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Topic / Niche[/]", classes="detail-label"))
        content.add(Static(f"[#f472b6]{topic}[/]", classes="detail-value"))
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Language[/]", classes="detail-label"))
        content.add(Static(f"[#38bdf8]{language}[/]", classes="detail-value"))
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Platform[/]", classes="detail-label"))
        content.add(Static(f"[#fb923c]{platform}[/]", classes="detail-value"))
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]File Path[/]", classes="detail-label"))
        content.add(
            Static(f"[#94a3b8]{file_path or '(none)'}[/]", classes="detail-value")
        )
        content.add(Static(""))

        content.add(Static("[bold #e2e8f0]Created[/]", classes="detail-label"))
        content.add(Static(f"[#64748b]{created_at}[/]", classes="detail-value"))

        container = self.query_one("#detail-content", Vertical)
        container.remove()
        self.mount(
            Vertical(
                Vertical(*content.children, id="detail-content"),
                classes="detail-container",
            )
        )

    def _show_empty(self) -> None:
        """Show empty state."""
        container = self.query_one("#detail-content", Vertical)
        container.remove()
        self.mount(
            Vertical(
                Static("[#ef4444]Video not found[/]", classes="detail-error"),
                id="detail-content",
            )
        )

    def _show_error(self, error: str) -> None:
        """Show error state."""
        container = self.query_one("#detail-content", Vertical)
        container.remove()
        self.mount(
            Vertical(
                Static(f"[#ef4444]Error: {error}[/]", classes="detail-error"),
                id="detail-content",
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        bid = event.button.id
        if bid == "btn-back":
            self.app.action_pop_screen_or_home()
        elif bid == "btn-upload":
            self._handle_upload()

    def _handle_upload(self) -> None:
        """Handle upload button click."""
        if not self._video_id:
            self._show_error("No video selected")
            return

        title = (
            self._video_data.get("title", "Untitled") if self._video_data else "Video"
        )
        self._show_uploading(title)

        asyncio.create_task(self._do_upload(self._video_id))

    async def _do_upload(self, video_id: int) -> None:
        """Perform the upload API call."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{_API_BASE}/api/videos/{video_id}/upload"
                )

                if response.status_code == 200:
                    data = response.json()
                    url = data.get("url", "")
                    if url:
                        self._show_success(f"Uploaded! {url}")
                    else:
                        self._show_success("Uploaded successfully!")
                else:
                    error = response.text[:100] if response.text else "Unknown error"
                    self._show_error(f"Upload failed: {error}")
        except httpx.ConnectError:
            self._show_error("Cannot connect to API server")
        except Exception as e:
            self._show_error(f"Error: {e}")

    def _show_uploading(self, title: str) -> None:
        """Show uploading status."""
        content = self.query_one("#detail-content", Vertical)
        content.remove()
        self.mount(
            Vertical(
                Static(f"[#fbbf24]Uploading: {title}...[/]", classes="detail-status"),
                id="detail-content",
            )
        )

    def _show_success(self, message: str) -> None:
        """Show success message."""
        content = self.query_one("#detail-content", Vertical)
        content.remove()
        self.mount(
            Vertical(
                Static(f"[#22c55e]✓ {message}[/]", classes="detail-success"),
                Button("[←] Back", id="btn-back", classes="action-secondary"),
                id="detail-content",
            )
        )


def show_video_detail(video_id: int) -> type:
    """Factory function to create a video detail screen for a specific video."""

    class _VideoDetailScreen(VideoDetailScreen):
        pass

    screen = _VideoDetailScreen(video_id=video_id)
    return screen
