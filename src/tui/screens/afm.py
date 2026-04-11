"""AFM Screen — v1 stub per DESIGN.md Section 5.5."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class AfmScreen(Screen):
    """Affiliate Marketing — stub for v1."""

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]AFFILIATE MARKETING[/]", classes="screen-title")
        yield Static(
            "[#64748b]This screen is not yet implemented.[/]",
            classes="stub-content",
        )
        yield Static(
            "Features planned for this screen:\n"
            "· product catalog with ASIN lookup\n"
            "· pitch generator via LLM\n"
            "· campaign manager\n"
            "· revenue and click tracking",
            classes="stub-features",
        )
