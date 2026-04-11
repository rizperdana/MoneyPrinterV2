"""Outreach Screen — v1 stub per DESIGN.md Section 5.5."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class OutreachScreen(Screen):
    """Business outreach — stub for v1."""

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]OUTREACH[/]", classes="screen-title")
        yield Static(
            "[#64748b]This screen is not yet implemented.[/]",
            classes="stub-content",
        )
        yield Static(
            "Features planned for this screen:\n"
            "· Google Maps business scraper\n"
            "· email template editor with variables\n"
            "· campaign manager\n"
            "· send tracking with open/click stats",
            classes="stub-features",
        )
