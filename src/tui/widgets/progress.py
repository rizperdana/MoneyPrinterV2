"""
Progress widgets for pipeline visualization.
"""

from textual.widget import Widget
from textual.widgets import Static
from textual.css.query import NoMatches
from typing import Optional

from src.tui.events import (
    PipelineStarted,
    PipelineStepStarted,
    PipelineStepComplete,
    PipelineProgress,
    PipelineError,
    PipelineComplete,
)

# Step state icons
_ICON_PENDING = "○"
_ICON_ACTIVE = "█"
_ICON_COMPLETE = "✓"
_ICON_ERROR = "✗"


class ProgressStep(Widget):
    """
    A single step in the pipeline with pending/active/complete states.
    """

    DEFAULT_CSS = """
    ProgressStep {
        height: auto;
        margin: 1 0;
    }

    .step-name {
        color: #f8fafc;
    }

    .step-duration {
        color: #94a3b8;
    }
    """

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self._state: str = "pending"
        self._duration: Optional[float] = None
        self._progress: float = 0.0

    @property
    def state(self) -> str:
        """Get current step state."""
        return self._state

    @property
    def icon(self) -> str:
        """Get icon for current state."""
        return {
            "pending": _ICON_PENDING,
            "active": _ICON_ACTIVE,
            "complete": _ICON_COMPLETE,
            "error": _ICON_ERROR,
        }.get(self._state, _ICON_PENDING)

    @property
    def css_class(self) -> str:
        """Get CSS class for current state."""
        return {
            "pending": "step-pending",
            "active": "step-active",
            "complete": "step-complete",
            "error": "step-error",
        }.get(self._state, "step-pending")

    def _build_text(self) -> str:
        """Build the display text for this step."""
        parts = [f"[{self.css_class}]{self.icon}[/{self.css_class}] {self.name}"]
        if self._state == "active" and self._progress > 0:
            parts.append(f" [{self._progress:.0%}]")
        if self._duration is not None:
            parts.append(f" [{self._duration:.1f}s]")
        return "".join(parts)

    def render(self) -> str:
        """Render the step."""
        return self._build_text()

    def set_pending(self) -> None:
        """Mark step as pending."""
        self._state = "pending"
        self._duration = None
        self._progress = 0.0
        self.refresh()

    def set_active(self) -> None:
        """Mark step as active (in progress)."""
        self._state = "active"
        self._duration = None
        self.refresh()

    def set_complete(self, duration: float) -> None:
        """Mark step as complete with duration."""
        self._state = "complete"
        self._duration = duration
        self._progress = 1.0
        self.refresh()

    def set_error(self) -> None:
        """Mark step as errored."""
        self._state = "error"
        self.refresh()

    def update_progress(self, progress: float) -> None:
        """Update progress within this step."""
        self._progress = max(0.0, min(1.0, progress))
        self.refresh()


class PipelineProgress(Widget):
    """
    Composite widget showing all pipeline steps with elapsed time tracking.
    """

    def __init__(self, steps: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._step_names = list(steps)
        self._step_widgets: dict[str, ProgressStep] = {}
        self._step_start_times: dict[str, float] = {}
        self._total_start_time: Optional[float] = None
        self._is_running = False

    def compose(self):
        """Compose the pipeline progress widget."""
        yield Static("Pipeline Progress", classes="section-header")
        for name in self._step_names:
            step = ProgressStep(name)
            self._step_widgets[name] = step
            yield step

    def on_pipeline_started(self, event: PipelineStarted) -> None:
        """Handle pipeline started event."""
        self._is_running = True
        self._total_start_time = event.total_steps  # Not used but part of API
        for step in self._step_widgets.values():
            step.set_pending()
        # Activate first step
        if self._step_names:
            self._activate_step(self._step_names[0])

    def on_pipeline_step_started(self, event: PipelineStepStarted) -> None:
        """Handle step started event."""
        if event.step_name in self._step_widgets:
            self._activate_step(event.step_name)

    def on_pipeline_step_complete(self, event: PipelineStepComplete) -> None:
        """Handle step complete event."""
        step = self._step_widgets.get(event.step_name)
        if step:
            step.set_complete(event.duration)
        # Activate next step
        idx = (
            self._step_names.index(event.step_name)
            if event.step_name in self._step_names
            else -1
        )
        if idx >= 0 and idx + 1 < len(self._step_names):
            self._activate_step(self._step_names[idx + 1])

    def on_pipeline_progress(self, event: PipelineProgress) -> None:
        """Handle progress update within a step."""
        step = self._step_widgets.get(event.step_name)
        if step:
            step.update_progress(event.progress)

    def on_pipeline_error(self, event: PipelineError) -> None:
        """Handle step error event."""
        step = self._step_widgets.get(event.step_name)
        if step:
            step.set_error()

    def on_pipeline_complete(self, event: PipelineComplete) -> None:
        """Handle pipeline complete event."""
        self._is_running = False

    def _activate_step(self, step_name: str) -> None:
        """Activate a specific step."""
        for name, step in self._step_widgets.items():
            if name == step_name:
                step.set_active()
            elif step.state not in ("complete", "error"):
                step.set_pending()

    def reset(self) -> None:
        """Reset all steps to pending."""
        self._is_running = False
        self._total_start_time = None
        for step in self._step_widgets.values():
            step.set_pending()
