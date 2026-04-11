"""
Stat card widget for dashboard display.
"""

from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult


class StatCard(Widget):
    """
    A dashboard stat card showing a label and bold value.

    Example:
        StatCard(title="Videos Today", value="12", id="stat-today")
    """

    def __init__(self, title: str, value: str, icon: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._value = value

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="stat-label")
        yield Static(self._value, classes="stat-value", id=f"{self.id}-val" if self.id else None)

    def update_value(self, value: str) -> None:
        """Update the displayed value."""
        self._value = value
        try:
            val_widget = self.query_one(".stat-value", Static)
            val_widget.update(value)
        except Exception:
            pass
