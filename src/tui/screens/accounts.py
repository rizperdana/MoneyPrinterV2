"""Accounts Screen — per DESIGN.md Section 5.3."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Static, Button, DataTable, Input
from typing import Optional

from src.db import get_accounts, add_account, update_account, delete_account
from src.tui.events import LibraryChanged


class AccountsScreen(Screen):
    """Account management screen with table and detail panel."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._accounts: list[dict] = []
        self._selected: Optional[dict] = None

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]ACCOUNTS[/]", classes="screen-title")

        # Toolbar
        with Horizontal(classes="toolbar"):
            yield Input(placeholder="search...", id="search-input")
            yield Button("+ add account", id="btn-add", classes="action-primary")

        # Table
        yield DataTable(id="accounts-table")

        # Detail panel
        yield Static("[#64748b]─── details ────────────────────────────────────────────[/]",
                      classes="section-divider")
        yield Static("[#374151]Select an account to view details[/]", id="detail-panel")

        # Actions
        with Horizontal(classes="button-row"):
            yield Button("test connection", id="btn-test", disabled=True)
            yield Button("edit", id="btn-edit", disabled=True)
            yield Button("delete", id="btn-delete", disabled=True)

    def on_mount(self) -> None:
        """Setup table and load accounts."""
        table = self.query_one("#accounts-table", DataTable)
        table.add_columns("platform", "username", "status", "uploads")
        table.cursor_type = "row"
        self._refresh()

    def _refresh(self) -> None:
        """Reload accounts from database."""
        table = self.query_one("#accounts-table", DataTable)
        table.clear()
        self._accounts = get_accounts()
        for acc in self._accounts:
            status = "[#10b981]● active[/]" if acc.get("profile_path") else "[#374151]● no profile[/]"
            table.add_row(
                acc.get("platform", ""),
                f"@{acc.get('username', '')}",
                status,
                "0",
                key=str(acc.get("id", "")),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        row_key = event.row_key
        if row_key and row_key.value:
            for acc in self._accounts:
                if str(acc.get("id", "")) == str(row_key.value):
                    self._selected = acc
                    self._show_detail(acc)
                    self._set_buttons(True)
                    break

    def _show_detail(self, acc: dict) -> None:
        """Update detail panel."""
        lines = [
            f"  profile path    {acc.get('profile_path', 'not set')}",
            f"  created         {acc.get('created_at', 'unknown')[:10]}",
            f"  nickname        {acc.get('nickname', '-')}",
        ]
        self.query_one("#detail-panel", Static).update("\n".join(lines))

    def _set_buttons(self, enabled: bool) -> None:
        for bid in ("#btn-test", "#btn-edit", "#btn-delete"):
            self.query_one(bid, Button).disabled = not enabled

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-add":
            self._add_account()
        elif bid == "btn-delete" and self._selected:
            self._delete_selected()
        elif bid == "btn-test" and self._selected:
            self.app.notify(
                f"Testing @{self._selected.get('username', '')}..."
            )

    def _add_account(self) -> None:
        """Quick-add an account (placeholder)."""
        add_account(platform="youtube", username="new_channel")
        self._refresh()
        self.app.post_message(LibraryChanged())

    def _delete_selected(self) -> None:
        """Delete selected account."""
        if self._selected and "id" in self._selected:
            delete_account(self._selected["id"])
            self._selected = None
            self._set_buttons(False)
            self.query_one("#detail-panel", Static).update(
                "[#374151]Select an account to view details[/]"
            )
            self._refresh()
            self.app.post_message(LibraryChanged())

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter accounts by search."""
        if event.input.id == "search-input":
            search = event.value.lower()
            table = self.query_one("#accounts-table", DataTable)
            table.clear()
            for acc in self._accounts:
                searchable = f"{acc.get('username', '')} {acc.get('platform', '')} {acc.get('nickname', '')}".lower()
                if search in searchable:
                    status = "[#10b981]● active[/]" if acc.get("profile_path") else "[#374151]● no profile[/]"
                    table.add_row(
                        acc.get("platform", ""),
                        f"@{acc.get('username', '')}",
                        status,
                        "0",
                        key=str(acc.get("id", "")),
                    )
