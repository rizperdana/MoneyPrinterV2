"""
Reusable confirmation dialog widget.
"""

from textual.app import ComposeResult
from textual.widgets import Static, Button, Label
from textual.containers import Horizontal, Vertical
from textual.message import Message


class ConfirmDialog(Vertical):
    """
    A reusable confirmation dialog modal.

    Messages:
        ConfirmDialog.YES: User confirmed
        ConfirmDialog.NO: User declined

    Example:
        dialog = ConfirmDialog(
            title="Delete Video?",
            message="This action cannot be undone.",
            yes_label="Delete",
            no_label="Cancel",
        )
        # Mount and listen for responses
    """

    class Yes(Message):
        """Fired when user confirms."""

        def __init__(self, dialog: "ConfirmDialog") -> None:
            super().__init__()
            self.dialog = dialog

    class No(Message):
        """Fired when user declines."""

        def __init__(self, dialog: "ConfirmDialog") -> None:
            super().__init__()
            self.dialog = dialog

    DEFAULT_CSS = """
    ConfirmDialog {
        width: 50%;
        max-width: 60;
        height: auto;
        background: #1e293b;
        border: solid #475569;
        padding: 2;
        align: center middle;
    }

    .dialog-title {
        color: #f8fafc;
        text-style: bold;
        text-align: center;
    }

    .dialog-message {
        color: #94a3b8;
        text-align: center;
        padding: 1 0;
    }

    .dialog-buttons {
        height: auto;
        align: center middle;
    }
    """

    def __init__(
        self,
        title: str,
        message: str,
        yes_label: str = "Yes",
        no_label: str = "No",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.dialog_title = title
        self.dialog_message = message
        self.yes_label = yes_label
        self.no_label = no_label

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        yield Static(self.dialog_title, classes="dialog-title")
        yield Label(self.dialog_message, classes="dialog-message")
        with Horizontal(classes="dialog-buttons"):
            yield Button(self.yes_label, id="btn-yes", variant="primary")
            yield Button(self.no_label, id="btn-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-yes":
            self.post_message(self.Yes(self))
        elif event.button.id == "btn-no":
            self.post_message(self.No(self))
