"""Dashboard Screen - Overview and quick actions."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from src.db import get_videos, get_accounts
from src.tui.widgets.stat_card import StatCard


class DashboardScreen(Screen):
    """Main dashboard showing stats and quick actions."""

    CSS = """
    DashboardScreen {
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

    .stats-row {
        height: auto;
        width: 100%;
        layout: horizontal;
    }

    .activity-section {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .quick-actions {
        height: auto;
        width: 100%;
        layout: horizontal;
        align: center middle;
        spacing: 1;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        # Header
        yield Static("📊 Dashboard", classes="screen-header")

        # Stats Row
        with Horizontal(classes="stats-row"):
            yield StatCard(
                title="Videos Today",
                value="0",
                icon="🎬",
                id="stat-videos-today",
            )
            yield StatCard(
                title="This Week",
                value="0",
                icon="📅",
                id="stat-videos-week",
            )
            yield StatCard(
                title="Accounts",
                value="0",
                icon="👤",
                id="stat-accounts",
            )

        # Quick Actions
        yield Static("Quick Actions", classes="section-header")
        with Horizontal(classes="quick-actions"):
            yield Button("🎬 Generate Video", variant="primary", id="btn-generate")
            yield Button("👤 Accounts", id="btn-accounts")
            yield Button("⚙️ Settings", id="btn-settings")

        # Recent Activity
        yield Static("Recent Activity", classes="section-header")
        with Container(classes="activity-section"):
            yield Static("No recent activity", id="recent-activity")
            yield Static("", id="recent-list")

    def on_mount(self) -> None:
        """Load dashboard data on mount."""
        self._refresh_stats()
        self._refresh_activity()

    def _refresh_stats(self) -> None:
        """Refresh the stat cards."""
        try:
            # Get videos
            videos = get_videos(limit=100)
            from datetime import datetime, timedelta

            today = datetime.now().date()
            week_ago = today - timedelta(days=7)

            today_count = 0
            week_count = 0

            for video in videos:
                created_at = video.get("created_at", "")
                if created_at:
                    try:
                        video_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        ).date()
                        if video_date == today:
                            today_count += 1
                        if video_date >= week_ago:
                            week_count += 1
                    except Exception:
                        pass

            # Get account count
            accounts = get_accounts()
            account_count = len(accounts)

            # Update stat cards
            self.query_one("#stat-videos-today", StatCard).update_value(
                str(today_count)
            )
            self.query_one("#stat-videos-week", StatCard).update_value(str(week_count))
            self.query_one("#stat-accounts", StatCard).update_value(str(account_count))
        except Exception as e:
            pass

    def _refresh_activity(self) -> None:
        """Refresh the recent activity list."""
        try:
            videos = get_videos(limit=10)
            if videos:
                recent_text = "\n".join(
                    f"• {v.get('title', 'Untitled')} ({v.get('platform', 'unknown')})"
                    for v in videos[:5]
                )
                self.query_one("#recent-list", Static).update(recent_text)
                self.query_one("#recent-activity", Static).update(
                    f"Last {min(5, len(videos))} videos:"
                )
            else:
                self.query_one("#recent-activity", Static).update("No recent activity")
                self.query_one("#recent-list", Static).update("")
        except Exception as e:
            self.query_one("#recent-activity", Static).update("No recent activity")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button presses."""
        button_id = event.button.id

        if button_id == "btn-generate":
            self.app.push_screen("video_gen")
        elif button_id == "btn-accounts":
            self.app.push_screen("accounts")
        elif button_id == "btn-settings":
            self.app.push_screen("settings")
