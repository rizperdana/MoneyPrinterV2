"""
Custom Textual events for the MoneyPrinterV2 pipeline.
"""

from textual.events import Event
from typing import Optional


class PipelineStarted(Event):
    """Fired when the entire pipeline begins."""

    def __init__(self, total_steps: int) -> None:
        super().__init__()
        self.total_steps = total_steps


class PipelineStepStarted(Event):
    """Fired when a specific pipeline step begins."""

    def __init__(self, step_name: str) -> None:
        super().__init__()
        self.step_name = step_name


class PipelineStepComplete(Event):
    """Fired when a pipeline step completes successfully."""

    def __init__(self, step_name: str, duration: float) -> None:
        super().__init__()
        self.step_name = step_name
        self.duration = duration  # seconds


class PipelineProgress(Event):
    """Fired to report progress within a step."""

    def __init__(self, step_name: str, message: str, progress: float) -> None:
        super().__init__()
        self.step_name = step_name
        self.message = message
        self.progress = progress  # 0.0 to 1.0


class PipelineError(Event):
    """Fired when a pipeline step encounters an error."""

    def __init__(self, step_name: str, error_message: str) -> None:
        super().__init__()
        self.step_name = step_name
        self.error_message = error_message


class PipelineComplete(Event):
    """Fired when the entire pipeline completes."""

    def __init__(self, output_path: Optional[str] = None) -> None:
        super().__init__()
        self.output_path = output_path
