"""Twitter Screen — v1 stub per DESIGN.md Section 5.5."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class TwitterScreen(Screen):
    """Twitter management — stub for v1."""

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]TWITTER[/]", classes="screen-title")
        yield Static(
            "[#64748b]This screen is not yet implemented.[/]",
            classes="stub-content",
        )
        yield Static(
            "Features planned for this screen:\n"
            "· post composer with character count\n"
            "· scheduled tweet viewer\n"
            "· recent posts table\n"
            "· follower / engagement stats",
            classes="stub-features",
        )
