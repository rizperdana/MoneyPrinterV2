"""Dashboard Screen — Overview and quick actions."""

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from src.db import get_videos, get_accounts
from src.tui.widgets.stat_card import StatCard
from src.tui.events import LibraryChanged


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
        yield Static("[#64748b]─── recent activity ─────────────────────────────────────[/]",
                      classes="section-divider")
        with Vertical(classes="activity-section"):
            yield Static("[#374151](no activity yet)[/]", id="activity-list")

        # Quick Actions
        yield Static("[#64748b]─── quick actions ──────────────────────────────────────[/]",
                      classes="section-divider")
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
        """Refresh the recent activity list."""
        try:
            videos = get_videos(limit=20)
            if videos:
                lines = []
                for v in videos[:10]:
                    title = v.get("title", "Untitled")
                    platform = v.get("platform", "")
                    created = v.get("created_at", "")[:16]
                    lines.append(
                        f"[#10b981]✓[/] {created}  {title}  [#64748b]{platform}[/]"
                    )
                self.query_one("#activity-list", Static).update("\n".join(lines))
            else:
                self.query_one("#activity-list", Static).update(
                    "[#374151](no activity yet)[/]"
                )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle quick action buttons."""
        bid = event.button.id
        if bid == "btn-gen":
            self.app.action_go_to("video_gen")
        elif bid == "btn-accts":
            self.app.action_go_to("accounts")
        elif bid == "btn-settings":
            self.app.action_go_to("settings")

    def action_go_to_video(self) -> None:
        self.app.action_go_to("video_gen")

    def action_upload_latest(self) -> None:
        pass  # TODO
