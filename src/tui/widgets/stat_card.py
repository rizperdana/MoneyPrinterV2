"""
Stat card widget for dashboard display.
"""

from textual.widget import Widget
from textual.widgets import Static
from textual.css.query import NoMatches


class StatCard(Widget):
    """
    A dashboard stat card showing a title, value, and optional icon.

    Example:
        StatCard(title="Videos Created", value="42", icon="🎬")
    """

    DEFAULT_CSS = """
    StatCard {
        width: 100%;
        height: auto;
        background: #1e293b;
        border: solid #334155;
        padding: 2;
    }

    .stat-card-icon {
        color: #6366f1;
        text-align: center;
    }

    .stat-card-title {
        color: #94a3b8;
        text-style: italic;
    }

    .stat-card-value {
        color: #f8fafc;
        text-style: bold;
    }
    """

    def __init__(
        self,
        title: str,
        value: str,
        icon: str = "",
        css_class: str = "stat-card",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.icon = icon
        self._css_class = css_class

    def compose(self):
        """Compose the stat card layout."""
        if self.icon:
            yield Static(self.icon, classes="stat-card-icon")
        yield Static(self.title, classes="stat-card-title")
        yield Static(self.value, classes="stat-card-value")

    def update_value(self, value: str) -> None:
        """Update the displayed value."""
        self.value = value
        try:
            value_widget = self.query_one(".stat-card-value", Static)
            value_widget.update(value)
        except NoMatches:
            pass

    def update_value_and_refresh(self, value: str) -> None:
        """Update value and refresh display."""
        self.value = value
        self.refresh()
