"""In-memory job registry for pipeline runs."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from asyncio import Queue
from datetime import datetime


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.queued
    account: str = ""
    niche: str = ""
    locale: str = "en-US"
    for_kids: bool = False
    current_step: str = ""
    step_index: int = 0
    step_progress: float | None = None  # 0.0-1.0 or None
    output_path: str | None = None
    upload_url: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    events: Queue = field(default_factory=Queue)  # for WebSocket streaming
    cancel_requested: bool = False
    auto_upload: bool = False


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create(
        self,
        account: str,
        niche: str,
        locale: str = "en-US",
        for_kids: bool = False,
        auto_upload: bool = False,
    ) -> Job:
        job = Job(account=account, niche=niche, locale=locale, for_kids=for_kids, auto_upload=auto_upload)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(self._jobs.values())

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status in (JobStatus.queued, JobStatus.running):
            job.cancel_requested = True
            job.status = JobStatus.cancelled
            return True
        return False


# Singleton
job_manager = JobManager()
