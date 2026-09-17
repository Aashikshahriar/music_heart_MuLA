import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from app.config import settings
from app.inference import runner


@dataclass
class Job:
    job_id: str
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    output_path: Optional[str] = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = Lock()

    def create(
        self,
        lyrics: str,
        tags: str,
        max_audio_length_ms: int,
        topk: int,
        temperature: float,
        cfg_scale: float,
    ) -> Job:
        job_id = uuid.uuid4().hex[:12]
        output_path = str(Path(settings.output_dir) / f"{job_id}.mp3")
        job = Job(job_id=job_id, output_path=output_path)

        with self._lock:
            self._jobs[job_id] = job

        def _task():
            self.mark_running(job_id)
            runner.generate_sync(
                lyrics,
                tags,
                output_path,
                max_audio_length_ms,
                topk,
                temperature,
                cfg_scale,
            )

        future = runner.submit_callable(_task)
        future.add_done_callback(lambda f: self._on_done(job_id, f))
        job.status = "queued"
        return job

    def _on_done(self, job_id: str, future) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.finished_at = time.time()
            exc = future.exception()
            if exc is not None:
                job.status = "error"
                job.error = str(exc)
            else:
                job.status = "done"

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None and job.status == "queued":
                job.status = "running"
                job.started_at = time.time()

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 50):
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


job_manager = JobManager()
