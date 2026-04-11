"""
Log viewer widget — extends RichLog for pipeline output.

Max 500 lines. Auto-scroll on by default with scroll lock toggle.
Log lines are routed from StatusInterceptor via LogLine messages.
"""

from datetime import datetime

from textual.widgets import RichLog
from textual.reactive import reactive
from typing import Optional


class LogViewer(RichLog):
    """
    Log viewer that receives LogLine messages and displays them
    with timestamp and color-coded level.

    Max 500 lines. Auto-scroll by default.
    """

    MAX_LINES = 500
    auto_scroll_enabled = reactive(True)

    LEVEL_COLORS = {
        "info": "#64748b",
        "success": "#10b981",
        "warn": "#f59e0b",
        "error": "#ef4444",
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(
            highlight=False,
            markup=True,
            max_lines=self.MAX_LINES,
            auto_scroll=True,
            **kwargs,
        )
        self._line_count = 0

    def write_line(self, text: str, level: str = "info") -> None:
        """Write a log line with timestamp and level color."""
        ts = datetime.now().strftime("%H:%M:%S")
        color = self.LEVEL_COLORS.get(level, "#64748b")
        formatted = f"[#64748b]{ts}[/]  [{color}]{text}[/]"
        self.write(formatted)
        self._line_count += 1

    def toggle_scroll_lock(self) -> None:
        """Toggle auto-scroll."""
        self.auto_scroll_enabled = not self.auto_scroll_enabled
        self.auto_scroll = self.auto_scroll_enabled
