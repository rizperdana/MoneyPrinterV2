"""
Account form widget for adding and editing accounts.
"""

from textual.app import ComposeResult
from textual.events import Mount
from textual.message import Message
from textual.widgets import Static, Input, Button, Select
from textual.containers import Vertical, Horizontal
from typing import Optional
from dataclasses import dataclass
import os


@dataclass
class AccountData:
    """Data class for account form results."""

    platform: str
    username: str
    nickname: str
    profile_path: str


class AccountFormSubmitted(Message):
    """Fired when the form is submitted successfully."""

    def __init__(self, form: "AccountForm", data: AccountData) -> None:
        super().__init__()
        self.form = form
        self.data = data


class AccountForm(Vertical):
    """
    Form for adding or editing accounts.

    Usage:
        form = AccountForm()  # New account
        form = AccountForm(account=dict)  # Edit existing
        yield from form.compose()
    """

    PLATFORMS = ["YouTube", "TikTok", "Twitter", "Facebook", "Instagram"]

    def __init__(self, account: Optional[dict] = None, **kwargs) -> None:
        """
        Initialize the form.

        Args:
            account: None for new account, dict for editing existing
        """
        super().__init__(**kwargs)
        self._account = account
        self._is_edit = account is not None

        # Form fields
        self._platform_select: Optional[Select] = None
        self._username_input: Optional[Input] = None
        self._nickname_input: Optional[Input] = None
        self._profile_path_input: Optional[Input] = None
        self._submit_button: Optional[Button] = None
        self._test_button: Optional[Button] = None
        self._errors: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose the form fields."""
        title = "Edit Account" if self._is_edit else "Add Account"
        yield Static(title, classes="form-title")

        with Vertical(classes="form-fields"):
            # Platform dropdown
            with Horizontal():
                yield Static("Platform:", classes="form-label")
                yield Select(
                    [(p, p) for p in self.PLATFORMS],
                    id="platform-select",
                    allow_blank=False,
                )

            # Username
            with Horizontal():
                yield Static("Username:", classes="form-label")
                yield Input(id="username-input", placeholder="Enter username...")

            # Nickname (optional)
            with Horizontal():
                yield Static("Nickname:", classes="form-label")
                yield Input(id="nickname-input", placeholder="Optional display name...")

            # Profile path
            with Horizontal():
                yield Static("Profile Path:", classes="form-label")
                yield Input(
                    id="profile-path-input",
                    placeholder="/path/to/browser/profile...",
                )

        # Error display
        yield Static("", id="form-errors", classes="form-errors")

        # Action buttons
        with Horizontal(classes="form-buttons"):
            yield Button("Save", id="btn-save", variant="primary")
            yield Button("Test Connection", id="btn-test")
            yield Button("Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        """Initialize form fields after mounting."""
        self._platform_select = self.query_one("#platform-select", Select)
        self._username_input = self.query_one("#username-input", Input)
        self._nickname_input = self.query_one("#nickname-input", Input)
        self._profile_path_input = self.query_one("#profile-path-input", Input)
        self._submit_button = self.query_one("#btn-save", Button)
        self._test_button = self.query_one("#btn-test", Button)
        self._errors_static = self.query_one("#form-errors", Static)

        # Pre-fill if editing
        if self._is_edit and self._account:
            platform = self._account.get("platform", "")
            if platform in self.PLATFORMS:
                self._platform_select.value = platform
            self._username_input.value = self._account.get("username", "")
            self._nickname_input.value = self._account.get("nickname", "") or ""
            self._profile_path_input.value = self._account.get("profile_path", "") or ""

    def validate(self) -> list[str]:
        """Validate form fields. Returns list of error messages."""
        errors = []

        # Username required
        username = self._username_input.value if self._username_input else ""
        if not username.strip():
            errors.append("Username is required")

        # Platform required
        platform = self._platform_select.value if self._platform_select else ""
        if not platform or platform not in self.PLATFORMS:
            errors.append("Please select a platform")

        # Profile path validation (if provided)
        profile_path = (
            self._profile_path_input.value if self._profile_path_input else ""
        )
        if profile_path and not os.path.exists(os.path.expanduser(profile_path)):
            errors.append("Profile path does not exist")

        self._errors = errors
        return errors

    def _show_errors(self) -> None:
        """Display validation errors."""
        if self._errors_static:
            if self._errors:
                self._errors_static.update("\n".join(f"• {e}" for e in self._errors))
                self._errors_static.styles.color = "#ef4444"
            else:
                self._errors_static.update("")
                self._errors_static.styles.color = "transparent"

    def submit(self) -> Optional[AccountData]:
        """
        Validate and return form data.

        Returns:
            AccountData if valid, None if invalid
        """
        errors = self.validate()
        self._show_errors()

        if errors:
            return None

        return AccountData(
            platform=self._platform_select.value,
            username=self._username_input.value.strip(),
            nickname=self._nickname_input.value.strip(),
            profile_path=self._profile_path_input.value.strip(),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-save":
            data = self.submit()
            if data:
                self.post_message(AccountFormSubmitted(self, data))

        elif button_id == "btn-cancel":
            self.app.pop_screen()

        elif button_id == "btn-test":
            self._test_connection()

    def _test_connection(self) -> None:
        """Test browser connection with the profile path."""
        profile_path = (
            self._profile_path_input.value if self._profile_path_input else ""
        )

        if not profile_path:
            self._errors = ["Please enter a profile path to test"]
            self._show_errors()
            return

        # Expand user path
        profile_path = os.path.expanduser(profile_path)

        if not os.path.exists(profile_path):
            self._errors = ["Profile path does not exist"]
            self._show_errors()
            return

        # TODO: Implement actual browser test
        # For now, just show success
        self._errors = []
        self._errors_static.update("✓ Profile path is valid")
        self._errors_static.styles.color = "#22c55e"
