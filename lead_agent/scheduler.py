"""Background job runner. Polls the SQLite job table; the HTTP server pokes it on new work."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from .brain import BrainError
from .db import Store
from .ghl import GHLError

log = logging.getLogger("lead_agent.scheduler")

BACKOFF_MINUTES = [1, 2, 5, 10, 20]


class Scheduler:
    def __init__(self, store: Store, run_job: Callable[[dict], None], poll_seconds: float = 3.0):
        self.store = store
        self.run_job = run_job
        self.poll_seconds = poll_seconds
        self.wake = threading.Event()
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="lead-agent-scheduler", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.wake.set()

    def poke(self) -> None:
        self.wake.set()

    def tick(self) -> int:
        """Run everything that is due once. Returns number of jobs processed."""
        jobs = self.store.claim_due_jobs()
        for job in jobs:
            self._run_one(job)
        return len(jobs)

    def _run_one(self, job: dict) -> None:
        try:
            self.run_job(job)
            self.store.finish_job(job["id"], ok=True)
        except (BrainError, GHLError) as e:
            transient = isinstance(e, BrainError) or getattr(e, "status", 0) in (429, 500, 502, 503, 504)
            attempts = int(job.get("attempts", 1))
            if transient and attempts <= len(BACKOFF_MINUTES):
                retry_at = time.time() + BACKOFF_MINUTES[attempts - 1] * 60
                log.warning("job %s (%s) transient failure, retry %d: %s", job["id"], job["kind"], attempts, e)
                self.store.finish_job(job["id"], ok=False, error=str(e), retry_at=retry_at)
            else:
                log.error("job %s (%s) failed permanently: %s", job["id"], job["kind"], e)
                self.store.finish_job(job["id"], ok=False, error=str(e))
                self.store.log(job["contact_id"], "job_failed", job_kind=job["kind"], error=str(e)[:400])
        except Exception as e:  # never let one lead's failure kill the loop
            log.exception("job %s (%s) crashed", job["id"], job["kind"])
            self.store.finish_job(job["id"], ok=False, error=str(e))
            self.store.log(job["contact_id"], "job_failed", job_kind=job["kind"], error=str(e)[:400])

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                n = self.tick()
            except Exception:
                log.exception("scheduler tick failed")
                n = 0
            if n == 0:
                self.wake.wait(self.poll_seconds)
                self.wake.clear()
