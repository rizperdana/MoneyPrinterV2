"""
Custom Textual messages for the MoneyPrinterV2 pipeline.

All communication from workers to widgets goes through these Messages.
Workers never call widget methods directly.
"""

from textual.message import Message
from typing import Optional


class StepStarted(Message):
    """A pipeline step has begun."""

    def __init__(self, step: str, index: int) -> None:
        super().__init__()
        self.step = step
        self.index = index


class StepProgressed(Message):
    """Progress within a pipeline step."""

    def __init__(self, step: str, detail: str, progress: float | None) -> None:
        super().__init__()
        self.step = step
        self.detail = detail
        self.progress = progress  # 0.0-1.0 for sub-progress, None for indeterminate


class StepCompleted(Message):
    """A pipeline step finished successfully."""

    def __init__(self, step: str, detail: str, elapsed: float) -> None:
        super().__init__()
        self.step = step
        self.detail = detail
        self.elapsed = elapsed


class StepFailed(Message):
    """A pipeline step failed."""

    def __init__(self, step: str, error: str) -> None:
        super().__init__()
        self.step = step
        self.error = error


class LogLine(Message):
    """A log line from the pipeline or status interceptor."""

    def __init__(self, level: str, text: str) -> None:
        super().__init__()
        self.level = level  # "info" | "success" | "warn" | "error"
        self.text = text


class JobCompleted(Message):
    """The entire pipeline job finished successfully."""

    def __init__(self, video_path: str, upload_url: str | None) -> None:
        super().__init__()
        self.video_path = video_path
        self.upload_url = upload_url


class JobFailed(Message):
    """The entire pipeline job failed."""

    def __init__(self, step: str, error: str) -> None:
        super().__init__()
        self.step = step
        self.error = error


class LibraryChanged(Message):
    """Posted after any db write — screens that show counts refresh themselves."""
    pass
