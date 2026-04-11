"""
Log viewer widget with filtering and export capabilities.
"""

from textual.widgets import RichLog, Button, Static
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from typing import Optional, List
from pathlib import Path


class LogViewer(RichLog):
    """
    A log viewer widget extending RichLog with:
    - Log level filtering (INFO/WARN/ERROR)
    - Auto-scroll toggle
    - Clear and export buttons

    Usage:
        log = LogViewer()
        yield log
        log.write_entry("Processing video...", "INFO")
        log.write_entry("Warning: low memory", "WARN")
        log.write_entry("Failed to render", "ERROR")
    """

    auto_scroll = reactive(True)

    LEVEL_COLORS = {
        "INFO": "#6366f1",  # Primary (indigo)
        "WARN": "#f59e0b",  # Warning (amber)
        "ERROR": "#ef4444",  # Error (red)
        "DEBUG": "#94a3b8",  # Secondary (slate)
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(highlight=False, markup=True, **kwargs)
        self._filter_level: Optional[str] = None
        self._log_lines: List[str] = []

    def write_entry(self, message: str, level: str = "INFO") -> None:
        """
        Write a log entry with level.

        Args:
            message: The log message
            level: Log level (INFO, WARN, ERROR, DEBUG)
        """
        if self._filter_level and level != self._filter_level:
            return

        color = self.LEVEL_COLORS.get(level, "#f8fafc")
        styled_msg = f"[{color}][{level}][/{color}] {message}"
        self.write(styled_msg)
        self._log_lines.append(f"[{level}] {message}")

    def info(self, message: str) -> None:
        """Write an INFO level message."""
        self.write_entry(message, "INFO")

    def warn(self, message: str) -> None:
        """Write a WARN level message."""
        self.write_entry(message, "WARN")

    def error(self, message: str) -> None:
        """Write an ERROR level message."""
        self.write_entry(message, "ERROR")

    def debug(self, message: str) -> None:
        """Write a DEBUG level message."""
        self.write_entry(message, "DEBUG")

    def set_filter(self, level: Optional[str]) -> None:
        """Set the log level filter."""
        self._filter_level = level

    def clear(self) -> None:
        """Clear the log and stored lines."""
        super().clear()
        self._log_lines.clear()

    def export_to_file(self, path: Optional[Path] = None) -> None:
        """Export log contents to file."""
        if path is None:
            path = Path("log_export.txt")
        try:
            path.write_text("\n".join(self._log_lines))
        except Exception:
            pass


class LogViewerWithControls(Vertical):
    """
    A composite widget containing a LogViewer with control buttons.

    Usage:
        container = LogViewerWithControls()
        yield from container.compose()
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._log_viewer = LogViewer()

    def compose(self):
        """Compose controls and log viewer."""
        with Horizontal(classes="log-controls"):
            yield Static("Filter:", classes="form-label")
            yield Button("ALL", id="filter-all", variant="primary")
            yield Button("INFO", id="filter-info", variant="default")
            yield Button("WARN", id="filter-warn", variant="default")
            yield Button("ERROR", id="filter-error", variant="default")
            yield Button("Clear", id="clear-log", variant="default")
            yield Button("Export", id="export-log", variant="default")
            yield Button("Auto", id="toggle-scroll", variant="primary")
        yield self._log_viewer

    @property
    def log_viewer(self) -> LogViewer:
        """Get the underlying log viewer."""
        return self._log_viewer

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        lv = self._log_viewer

        if button_id == "filter-all":
            lv.set_filter(None)
            self._update_filter_buttons("filter-all")
        elif button_id == "filter-info":
            lv.set_filter("INFO")
            self._update_filter_buttons("filter-info")
        elif button_id == "filter-warn":
            lv.set_filter("WARN")
            self._update_filter_buttons("filter-warn")
        elif button_id == "filter-error":
            lv.set_filter("ERROR")
            self._update_filter_buttons("filter-error")
        elif button_id == "clear-log":
            lv.clear()
        elif button_id == "export-log":
            lv.export_to_file()
        elif button_id == "toggle-scroll":
            lv.auto_scroll = not lv.auto_scroll
            self._update_scroll_button()

    def _update_filter_buttons(self, active_id: str) -> None:
        """Update filter button variants."""
        for button in self.query(Button):
            if button.id and button.id.startswith("filter-"):
                button.variant = "primary" if button.id == active_id else "default"

    def _update_scroll_button(self) -> None:
        """Update auto-scroll button variant."""
        btn = self.query_one("#toggle-scroll", Button)
        btn.variant = "primary" if self._log_viewer.auto_scroll else "default"
