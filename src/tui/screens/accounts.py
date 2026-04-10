"""Accounts Screen - Full platform account management."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.screen import ModalScreen, Screen
from textual.widgets import Static, Button, DataTable
from textual.message import Message
from typing import Optional

from src.db import get_accounts, add_account, update_account, delete_account
from src.tui.widgets.account_table import AccountTable, AccountRowSelected
from src.tui.widgets.account_form import AccountForm, AccountFormSubmitted
from src.tui.widgets.confirm_dialog import ConfirmDialog


class AccountFormModal(ModalScreen):
    """Modal screen for the account form."""

    def __init__(self, account: Optional[dict] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._account = account

    def compose(self) -> ComposeResult:
        """Compose the modal form."""
        yield Container(
            AccountForm(account=self._account),
            id="form-container",
        )


class AccountsScreen(Screen):
    """Full account management screen with table, details, and actions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_account: Optional[dict] = None

    def compose(self) -> ComposeResult:
        """Compose the accounts screen layout."""
        # Header
        yield Static("Accounts", classes="screen-header")

        # Toolbar
        with Horizontal(classes="toolbar"):
            yield Button("+ Add Account", variant="primary", id="btn-add")
            yield Button("Edit", id="btn-edit", disabled=True)
            yield Button("Delete", id="btn-delete", variant="error", disabled=True)
            yield Button("Test Connection", id="btn-test", disabled=True)

        # Main content area
        with Horizontal(id="main-content"):
            # Left: Account table
            with Vertical(id="table-panel"):
                yield AccountTable(id="account-table")

            # Right: Account details
            with Vertical(id="details-panel"):
                yield Static("Account Details", classes="section-header")
                yield Static("Select an account to view details", id="account-details")
                yield Static("", id="detail-platform", classes="detail-field")
                yield Static("", id="detail-username", classes="detail-field")
                yield Static("", id="detail-nickname", classes="detail-field")
                yield Static("", id="detail-profile", classes="detail-field")

    def on_mount(self) -> None:
        """Load accounts on mount."""
        self._refresh_accounts()

    def _refresh_accounts(self) -> None:
        """Reload accounts from database."""
        table = self.query_one("#account-table", AccountTable)
        accounts = get_accounts()
        table.load_accounts(accounts)

    def on_account_row_selected(self, event: AccountRowSelected) -> None:
        """Handle account row selection."""
        self._selected_account = event.account
        self._update_details(event.account)
        self._update_button_states(True)

    def _update_details(self, account: dict) -> None:
        """Update the details panel."""
        self.query_one("#account-details", Static).update(
            f"@{account.get('username', '')}"
        )
        self.query_one(
            "#detail-platform", Static
        ).update = f"Platform: {account.get('platform', 'N/A')}"
        self.query_one(
            "#detail-username", Static
        ).update = f"Username: {account.get('username', 'N/A')}"
        self.query_one(
            "#detail-nickname", Static
        ).update = f"Nickname: {account.get('nickname', 'N/A')}"
        self.query_one(
            "#detail-profile", Static
        ).update = f"Profile: {account.get('profile_path', 'N/A')}"

    def _update_button_states(self, has_selection: bool) -> None:
        """Enable/disable buttons based on selection."""
        self.query_one("#btn-edit", Button).disabled = not has_selection
        self.query_one("#btn-delete", Button).disabled = not has_selection
        self.query_one("#btn-test", Button).disabled = not has_selection

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle toolbar button presses."""
        button_id = event.button.id

        if button_id == "btn-add":
            self._show_add_form()

        elif button_id == "btn-edit":
            if self._selected_account:
                self._show_edit_form(self._selected_account)

        elif button_id == "btn-delete":
            if self._selected_account:
                self._show_delete_confirmation()

        elif button_id == "btn-test":
            if self._selected_account:
                self._test_connection()

    def _show_add_form(self) -> None:
        """Show the add account form."""
        self.app.push_screen(AccountFormModal(), self._on_form_complete)

    def _show_edit_form(self, account: dict) -> None:
        """Show the edit account form."""
        self.app.push_screen(AccountFormModal(account=account), self._on_form_complete)

    def _on_form_complete(self, submitted: AccountFormSubmitted) -> None:
        """Handle form submission."""
        if submitted and submitted.data:
            data = submitted.data
            if self._selected_account and "id" in self._selected_account:
                # Update existing
                update_account(
                    self._selected_account["id"],
                    {
                        "platform": data.platform,
                        "username": data.username,
                        "nickname": data.nickname or None,
                        "profile_path": data.profile_path or None,
                    },
                )
            else:
                # Add new
                add_account(
                    platform=data.platform,
                    username=data.username,
                    nickname=data.nickname or None,
                    profile_path=data.profile_path or None,
                )
            self._refresh_accounts()
            self._clear_selection()

    def _show_delete_confirmation(self) -> None:
        """Show delete confirmation dialog."""
        if not self._selected_account:
            return

        username = self._selected_account.get("username", "this account")
        dialog = ConfirmDialog(
            title="Delete Account?",
            message=f"Are you sure you want to delete @{username}?",
            yes_label="Delete",
            no_label="Cancel",
        )

        def on_confirm(dialog_event):
            if isinstance(dialog_event, ConfirmDialog.Yes):
                self._delete_account()

        self.mount(dialog)
        self.listen(ConfirmDialog.Yes, on_confirm)
        self.listen(ConfirmDialog.No, lambda _: dialog.remove())

    def _delete_account(self) -> None:
        """Delete the selected account."""
        if self._selected_account and "id" in self._selected_account:
            delete_account(self._selected_account["id"])
            self._refresh_accounts()
            self._clear_selection()

    def _test_connection(self) -> None:
        """Test connection for selected account."""
        if self._selected_account:
            profile_path = self._selected_account.get("profile_path", "")
            # TODO: Implement actual browser test
            # For now, show a placeholder
            self.app.notify(
                f"Testing connection for @{self._selected_account.get('username')}..."
            )

    def _clear_selection(self) -> None:
        """Clear the current selection."""
        self._selected_account = None
        self._update_button_states(False)
        self.query_one("#account-details", Static).update(
            "Select an account to view details"
        )
        self.query_one("#detail-platform", Static).update("")
        self.query_one("#detail-username", Static).update("")
        self.query_one("#detail-nickname", Static).update("")
        self.query_one("#detail-profile", Static).update("")
