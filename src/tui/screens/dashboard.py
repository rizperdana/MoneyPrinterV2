"""Dashboard Screen — Overview and quick actions."""

import asyncio
import httpx
from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from src.db import get_videos, get_accounts
from src.tui.widgets.stat_card import StatCard
from src.tui.events import LibraryChanged
from src.tui.screens.video_detail import VideoDetailScreen

_API_BASE = "http://localhost:8000"


class DashboardScreen(Screen):
    """Main dashboard showing stats, recent activity, and quick actions."""

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]DASHBOARD[/]", classes="screen-title")

        # Stats Row
        with Horizontal(classes="stats-row"):
            yield StatCard(title="videos today", value="0", id="stat-today")
            yield StatCard(title="this week", value="0", id="stat-week")
            yield StatCard(title="accounts", value="0", id="stat-accounts")

        # Recent Activity
        yield Static(
            "[#64748b]─── recent activity (click to view) ──────────────────────[/]",
            classes="section-divider",
        )
        with Vertical(classes="activity-section", id="activity-container"):
            yield Static("[#374151](no activity yet)[/]", id="activity-list")

        # Quick Actions
        yield Static(
            "[#64748b]─── quick actions ──────────────────────────────────────[/]",
            classes="section-divider",
        )
        with Horizontal(classes="quick-actions"):
            yield Button("[G] Generate Video", id="btn-gen", classes="action-primary")
            yield Button("[U] Upload Latest", id="btn-upload")
            yield Button("[A] Accounts", id="btn-accts")
            yield Button("[S] Settings", id="btn-settings")

    BINDINGS = [
        ("g", "go_to_video", "Generate"),
        ("u", "upload_latest", "Upload"),
    ]

    def on_mount(self) -> None:
        """Load dashboard data on mount."""
        self._refresh_stats()
        self._refresh_activity()
        # Tick clock every 60s
        self.set_interval(60, self._refresh_stats)

    def on_library_changed(self, message: LibraryChanged) -> None:
        """Refresh stats when DB changes."""
        self._refresh_stats()
        self._refresh_activity()

    def _refresh_stats(self) -> None:
        """Refresh the stat cards from db."""
        try:
            videos = get_videos(limit=200)
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)

            today_count = 0
            week_count = 0
            for v in videos:
                created = v.get("created_at", "")
                if created:
                    try:
                        vdate = datetime.fromisoformat(
                            created.replace("Z", "+00:00")
                        ).date()
                        if vdate == today:
                            today_count += 1
                        if vdate >= week_ago:
                            week_count += 1
                    except Exception:
                        pass

            accounts = get_accounts()
            active_count = len(accounts)

            self.query_one("#stat-today", StatCard).update_value(str(today_count))
            self.query_one("#stat-week", StatCard).update_value(str(week_count))
            self.query_one("#stat-accounts", StatCard).update_value(
                f"{active_count} active" if active_count else "0"
            )
        except Exception:
            pass

    def _refresh_activity(self) -> None:
        """Refresh the recent activity list as clickable buttons."""
        try:
            videos = get_videos(limit=20)
            container = self.query_one("#activity-container", Vertical)

            for child in list(container.children):
                if child.id != "activity-list":
                    container.remove(child)

            if hasattr(self, "_activity_buttons"):
                for btn in self._activity_buttons:
                    btn.remove()
            self._activity_buttons = []

            if videos:
                for v in videos[:10]:
                    video_id = v.get("id", 0)
                    title = v.get("title", "Untitled")
                    platform = v.get("platform", "")
                    created = v.get("created_at", "")[:16]
                    display = f"[View] {created} | {title} [{platform}]"

                    btn = Button(
                        display, id=f"video-{video_id}", classes="activity-btn"
                    )
                    self._activity_buttons.append(btn)
                    container.mount(btn)
            else:
                container.mount(
                    Static("[#374151](no activity yet)[/]", id="activity-list")
                )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle quick action buttons and video detail buttons."""
        bid = event.button.id
        if bid == "btn-gen":
            self.app.action_go_to("video_gen")
        elif bid == "btn-accts":
            self.app.action_go_to("accounts")
        elif bid == "btn-settings":
            self.app.action_go_to("settings")
        elif bid and bid.startswith("video-"):
            video_id = int(bid.replace("video-", ""))
            self._show_video_detail(video_id)

    def _show_video_detail(self, video_id: int) -> None:
        """Show video detail screen."""
        screen = VideoDetailScreen(video_id=video_id)
        self.app.push_screen(screen)

    def action_go_to_video(self) -> None:
        self.app.action_go_to("video_gen")

    def action_upload_latest(self) -> None:
        """Upload the latest video to YouTube."""
        try:
            videos = get_videos(limit=20)
            if not videos:
                self._show_notification("No videos to upload")
                return

            latest = videos[0]
            video_id = latest.get("id")
            title = latest.get("title", "Untitled")

            if not video_id:
                self._show_notification("No video ID found")
                return

            self._show_notification(f"Uploading: {title}...")

            asyncio.create_task(self._do_upload(video_id, title))
        except Exception as e:
            self._show_notification(f"Error: {e}")

    async def _do_upload(self, video_id: int, title: str) -> None:
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
                        self._show_notification(f"✓ Uploaded! {url}")
                    else:
                        self._show_notification("✓ Uploaded successfully!")
                else:
                    error = response.text[:100] if response.text else "Unknown error"
                    self._show_notification(f"Upload failed: {error}")
        except httpx.ConnectError:
            self._show_notification("Error: Cannot connect to API server")
        except Exception as e:
            self._show_notification(f"Error: {e}")

    def _show_notification(self, message: str) -> None:
        """Show a notification message on the dashboard."""
        try:
            container = self.query_one("#activity-container", Vertical)
            notif = Static(f"[#22c55e]{message}[/]", classes="notification")
            container.mount(notif)

            def clear_notif():
                try:
                    notif.remove()
                except Exception:
                    pass

            self.set_timer(5, clear_notif)
        except Exception:
            pass
