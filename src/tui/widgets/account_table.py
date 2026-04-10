"""
Account table widget with filtering and sorting.
"""

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DataTable, Static, Select, Input
from textual.containers import Horizontal
from typing import Optional, Callable


class AccountRowSelected(Message):
    """Fired when an account row is selected."""

    def __init__(self, account: dict) -> None:
        super().__init__()
        self.account = account


class AccountTable(Static):
    """
    DataTable-based account list with platform filtering and column sorting.

    Usage:
        table = AccountTable()
        yield from table.compose()
        table.load_accounts(accounts)
    """

    PLATFORMS = ["All", "YouTube", "TikTok", "Twitter", "Facebook", "Instagram"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._table: Optional[DataTable] = None
        self._platform_filter: Optional[Select] = None
        self._search_input: Optional[Input] = None
        self._all_accounts: list[dict] = []
        self._selected_account: Optional[dict] = None

    def compose(self) -> ComposeResult:
        """Compose the account table with controls."""
        with Horizontal(classes="table-controls"):
            yield Static("Platform:", classes="form-label")
            yield Select(
                [(p, p) for p in self.PLATFORMS],
                value="All",
                id="platform-filter",
                allow_blank=False,
            )
            yield Static("Search:", classes="form-label")
            yield Input(placeholder="Filter accounts...", id="search-input")

        yield DataTable(
            id="accounts-table",
            fixed_rows=1,
            zebra_stripes=True,
            show_header=True,
        )

    def on_mount(self) -> None:
        """Initialize the table after mounting."""
        self._table = self.query_one("#accounts-table", DataTable)
        self._platform_filter = self.query_one("#platform-filter", Select)
        self._search_input = self.query_one("#search-input", Input)

        # Set up columns
        self._table.add_columns("Platform", "Username", "Nickname", "Status")

        # Set up row selection handler
        self._table.on_row_selected = self._on_row_selected

    def load_accounts(self, accounts: list[dict]) -> None:
        """Load accounts into the table."""
        self._all_accounts = list(accounts)
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh table with current filter/search state."""
        if self._table is None:
            return

        self._table.clear()

        # Get filter values
        platform = (
            self._platform_filter.value
            if self._platform_filter and self._platform_filter.value != "All"
            else None
        )
        search = (
            self._search_input.value.lower()
            if self._search_input and self._search_input.value
            else ""
        )

        # Filter accounts
        filtered = []
        for account in self._all_accounts:
            # Platform filter
            if platform and account.get("platform", "").lower() != platform.lower():
                continue

            # Search filter
            if search:
                searchable = (
                    f"{account.get('username', '')} "
                    f"{account.get('nickname', '')} "
                    f"{account.get('platform', '')}"
                ).lower()
                if search not in searchable:
                    continue

            filtered.append(account)

        # Add rows
        for account in filtered:
            self._table.add_row(
                account.get("platform", "Unknown"),
                account.get("username", ""),
                account.get("nickname", "") or "-",
                self._get_account_status(account),
                key=str(account.get("id", "")),
            )

    def _get_account_status(self, account: dict) -> str:
        """Get status string for an account."""
        profile_path = account.get("profile_path")
        if not profile_path:
            return "No Profile"
        return "Ready"

    def _on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        row_key = event.row_key
        if row_key and row_key.value:
            for account in self._all_accounts:
                if str(account.get("id", "")) == str(row_key.value):
                    self._selected_account = account
                    self.post_message(AccountRowSelected(account))
                    break

    def get_selected_account(self) -> Optional[dict]:
        """Get the currently selected account."""
        return self._selected_account

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle platform filter change."""
        if event.select.id == "platform-filter":
            self._refresh_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input change."""
        if event.input.id == "search-input":
            self._refresh_table()
