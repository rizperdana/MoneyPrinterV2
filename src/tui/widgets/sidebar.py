"""
Sidebar widget — persistent left navigation panel.

Fixed-width, never scrolls, never hides.
Navigation items are Buttons styled as menu items.
Active item gets border-left accent.
"""

from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical


class SidebarItem(Button):
    """A single item in the sidebar navigation."""

    def __init__(self, label: str, target: str, **kwargs):
        super().__init__(label, **kwargs)
        self.target = target


class Sidebar(Vertical):
    """Navigation sidebar for the TUI."""

    NAV_ITEMS = [
        ("DASH", "dashboard"),
        ("VIDEO", "video_gen"),
        ("ACCTS", "accounts"),
        ("TWITTER", "twitter"),
        ("AFM", "afm"),
        ("REACH", "outreach"),
    ]

    BOTTOM_ITEMS = [
        ("SETUP", "settings"),
    ]

    def compose(self) -> ComposeResult:
        for label, target in self.NAV_ITEMS:
            yield SidebarItem(label, target, classes="nav-item")
        yield Static("──────", classes="nav-separator")
        for label, target in self.BOTTOM_ITEMS:
            yield SidebarItem(label, target, classes="nav-item")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle nav clicks."""
        button = event.button
        if isinstance(button, SidebarItem):
            event.stop()
            self.app.action_go_to(button.target)

    def set_active(self, screen_name: str) -> None:
        """Highlight the active navigation item."""
        for button in self.query(SidebarItem):
            if button.target == screen_name:
                button.add_class("nav-active")
            else:
                button.remove_class("nav-active")
