"""
Job Ticker — persistent single-line footer showing current/last job status.

Always visible. Shows idle/running/failed/complete states.
"""

from textual.app import ComposeResult
from textual.widgets import Static
from textual.reactive import reactive

from tui.events import StepProgressed, JobCompleted, JobFailed


class JobTicker(Static):
    """Single-line persistent footer showing job status."""

    # Reactive state
    state: reactive[str] = reactive("idle")  # idle | running | failed | complete
    job_name: reactive[str] = reactive("")
    detail: reactive[str] = reactive("")
    last_info: reactive[str] = reactive("")

    def render(self) -> str:
        if self.state == "idle":
            last = f"  [#374151]last: {self.last_info}[/]" if self.last_info else ""
            return f"[#374151]■ idle[/]{last}"

        elif self.state == "running":
            return f"[#3b82f6]◐[/] generating [bold]\"{self.job_name}\"[/]  {self.detail}"

        elif self.state == "failed":
            return f"[#ef4444]✗[/] failed: {self.job_name}  {self.detail}"

        elif self.state == "complete":
            return f"[#10b981]✓[/] complete: {self.job_name}  {self.detail}"

        return ""

    def set_running(self, name: str, detail: str = "") -> None:
        """Set ticker to running state."""
        self.job_name = name
        self.detail = detail
        self.state = "running"

    def set_complete(self, name: str, detail: str = "") -> None:
        """Set ticker to complete state. Fades to idle after 30s."""
        self.job_name = name
        self.detail = detail
        self.state = "complete"
        self.last_info = f"{name} ✓"
        self.set_timer(30, self._fade_to_idle)

    def set_failed(self, name: str, detail: str = "") -> None:
        """Set ticker to failed state."""
        self.job_name = name
        self.detail = detail
        self.state = "failed"
        self.last_info = f"{name} ✗"

    def _fade_to_idle(self) -> None:
        """Fade complete state back to idle."""
        if self.state == "complete":
            self.state = "idle"
