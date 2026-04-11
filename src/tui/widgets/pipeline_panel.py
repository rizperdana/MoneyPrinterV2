"""
Pipeline panel — step tracker with progress display.

Shows 7 pipeline steps with pending/running/done/error states.
Each step shows icon, name, detail, and elapsed time.
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual.timer import Timer
from typing import Optional

from tui.events import StepStarted, StepProgressed, StepCompleted, StepFailed

# Step state icons — consistent across all views (DESIGN Section 3.3)
_SPIN_FRAMES = ["◐", "◑", "◒", "◓"]
_ICON_PENDING = "○"
_ICON_DONE = "✓"
_ICON_ERROR = "✗"
_ICON_SKIPPED = "⊘"

STEPS = [
    ("topic", "topic"),
    ("script", "script"),
    ("image_prompts", "image prompts"),
    ("images", "images"),
    ("tts", "tts"),
    ("combine", "combine"),
    ("upload", "upload"),
]


class PipelineStep(Static):
    """A single step row in the pipeline panel."""

    status: reactive[str] = reactive("pending")  # pending | running | done | error
    detail: reactive[str] = reactive("")
    elapsed: reactive[float] = reactive(0.0)

    def __init__(self, step_key: str, step_label: str, index: int, **kwargs):
        super().__init__(**kwargs)
        self.step_key = step_key
        self.step_label = step_label
        self.index = index
        self._spin_index = 0
        self._spin_timer: Optional[Timer] = None

    def on_mount(self) -> None:
        self.add_class("pipeline-step", "step-pending")

    def render(self) -> str:
        num = f"{self.index + 1}."

        if self.status == "pending":
            icon = f"[#374151]{_ICON_PENDING}[/]"
            return f"  {icon}  {num} {self.step_label:<16} [#374151]pending[/]"

        elif self.status == "running":
            icon = f"[#3b82f6]{_SPIN_FRAMES[self._spin_index]}[/]"
            detail_str = f"  [#3b82f6]{self.detail}[/]" if self.detail else ""
            return f"  {icon}  {num} {self.step_label:<16}{detail_str}"

        elif self.status == "done":
            icon = f"[#10b981]{_ICON_DONE}[/]"
            detail_str = f"  [#10b981]{self.detail}[/]" if self.detail else ""
            elapsed_str = f"  [#64748b]{self.elapsed:.1f}s[/]" if self.elapsed > 0 else ""
            return f"  {icon}  {num} {self.step_label:<16}{detail_str}{elapsed_str}"

        elif self.status == "error":
            icon = f"[#ef4444]{_ICON_ERROR}[/]"
            detail_str = f"  [#ef4444]{self.detail}[/]" if self.detail else ""
            return f"  {icon}  {num} {self.step_label:<16}{detail_str}"

        return f"  {_ICON_PENDING}  {num} {self.step_label}"

    def set_running(self) -> None:
        """Mark step as running with animated spinner."""
        self.status = "running"
        self._update_classes("step-running")
        # Start spinner animation
        if self._spin_timer is None:
            self._spin_timer = self.set_interval(0.2, self._tick_spinner)

    def set_done(self, detail: str = "", elapsed: float = 0.0) -> None:
        """Mark step as completed."""
        self._stop_spinner()
        self.status = "done"
        self.detail = detail
        self.elapsed = elapsed
        self._update_classes("step-done")

    def set_error(self, detail: str = "") -> None:
        """Mark step as failed."""
        self._stop_spinner()
        self.status = "error"
        self.detail = detail
        self._update_classes("step-error")

    def set_pending(self) -> None:
        """Reset step to pending."""
        self._stop_spinner()
        self.status = "pending"
        self.detail = ""
        self.elapsed = 0.0
        self._update_classes("step-pending")

    def update_detail(self, detail: str) -> None:
        """Update the detail text for a running step."""
        self.detail = detail
        self.refresh()

    def _tick_spinner(self) -> None:
        self._spin_index = (self._spin_index + 1) % len(_SPIN_FRAMES)
        self.refresh()

    def _stop_spinner(self) -> None:
        if self._spin_timer is not None:
            self._spin_timer.stop()
            self._spin_timer = None

    def _update_classes(self, active_class: str) -> None:
        for cls in ("step-pending", "step-running", "step-done", "step-error"):
            self.remove_class(cls)
        self.add_class(active_class)
        self.refresh()


class PipelinePanel(Widget):
    """Composite widget showing all 7 pipeline steps."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._steps: dict[str, PipelineStep] = {}

    def compose(self) -> ComposeResult:
        for i, (key, label) in enumerate(STEPS):
            step = PipelineStep(key, label, i)
            self._steps[key] = step
            yield step

    def set_active(self, step_key: str) -> None:
        """Mark a step as running."""
        step = self._steps.get(step_key)
        if step:
            step.set_running()

    def update_step(self, step_key: str, detail: str, progress: float | None) -> None:
        """Update a running step's detail/progress."""
        step = self._steps.get(step_key)
        if step:
            step.update_detail(detail)

    def complete_step(self, step_key: str, detail: str = "", elapsed: float = 0.0) -> None:
        """Mark a step as done."""
        step = self._steps.get(step_key)
        if step:
            step.set_done(detail, elapsed)

    def fail_step(self, step_key: str, error: str = "") -> None:
        """Mark a step as failed."""
        step = self._steps.get(step_key)
        if step:
            step.set_error(error)

    def reset(self) -> None:
        """Reset all steps to pending."""
        for step in self._steps.values():
            step.set_pending()
