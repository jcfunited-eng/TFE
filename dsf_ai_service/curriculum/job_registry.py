"""
job_registry.py — In-memory async-safe job registry for curriculum load jobs.

GL-CMD-CURRICULUM-ASYNC-LOAD-EVE-20260620-74

State machine: queued → running → complete
                              → failed

Job lifecycle:
  - TTL: 1 hour after completed_at/failed_at
  - Max 100 entries; oldest completed evicted first when full.

Concurrency constraint (V1):
  - Single in-flight load job at a time.
  - POST for any corpus_id while a job is queued/running → 409 Conflict.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

JOB_TTL_SECONDS = 3600       # 1 hour
JOB_MAX_ENTRIES = 100

# In-memory stores — protected by asyncio (single-threaded event loop)
_jobs: dict[str, dict] = {}          # job_id → job dict
_active_job_id: Optional[str] = None # single-job constraint


def create_job(corpus_id: str, n_sentences: int) -> dict:
    """Create a new job. Caller must ensure no conflicting job is running."""
    global _active_job_id
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "corpus_id": corpus_id,
        "state": "queued",
        "progress": {"n_fed": 0, "n_total": n_sentences},
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "_created_at": time.time(),
    }
    _jobs[job_id] = job
    _active_job_id = job_id
    return job


def get_job(job_id: str) -> Optional[dict]:
    """Return job dict or None."""
    return _jobs.get(job_id)


def get_active_job() -> Optional[dict]:
    """Return the current in-flight job, or None."""
    if _active_job_id and _active_job_id in _jobs:
        j = _jobs[_active_job_id]
        if j["state"] in ("queued", "running"):
            return j
    return None


def mark_running(job_id: str):
    j = _jobs.get(job_id)
    if j:
        j["state"] = "running"
        j["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def update_progress(job_id: str, n_fed: int):
    j = _jobs.get(job_id)
    if j:
        j["progress"]["n_fed"] = n_fed


def mark_complete(job_id: str, result: dict):
    global _active_job_id
    j = _jobs.get(job_id)
    if j:
        j["state"] = "complete"
        j["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        j["result"] = result
    if _active_job_id == job_id:
        _active_job_id = None


def mark_failed(job_id: str, error: str, partial_n_fed: int = 0):
    global _active_job_id
    j = _jobs.get(job_id)
    if j:
        j["state"] = "failed"
        j["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        j["error"] = error
        j["progress"]["n_fed"] = partial_n_fed
    if _active_job_id == job_id:
        _active_job_id = None


def gc_expired():
    """Remove jobs older than TTL, keeping within MAX_ENTRIES.
    Called periodically by the GC background task."""
    now = time.time()
    expired = [
        jid for jid, j in _jobs.items()
        if j["state"] in ("complete", "failed")
        and now - j.get("_created_at", now) > JOB_TTL_SECONDS
    ]
    for jid in expired:
        del _jobs[jid]

    # Evict oldest completed if over cap
    if len(_jobs) > JOB_MAX_ENTRIES:
        completed = sorted(
            [(jid, j) for jid, j in _jobs.items()
             if j["state"] in ("complete", "failed")],
            key=lambda x: x[1].get("_created_at", 0),
        )
        while len(_jobs) > JOB_MAX_ENTRIES and completed:
            jid, _ = completed.pop(0)
            del _jobs[jid]

    return len(expired)
