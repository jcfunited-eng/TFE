from __future__ import annotations

from pathlib import Path
import threading

from dsf_ai_service.v4.guala_physical_runtime import Guala


def _thread_identity() -> tuple[tuple[int | None, str], ...]:
    return tuple(sorted(
        (thread.ident, thread.name)
        for thread in threading.enumerate()
    ))


def _regular_files(root: Path) -> tuple[str, ...]:
    return tuple(sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    ))


def test_sustained_observation_is_memory_bounded_and_never_starts_diary(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    guala = Guala()
    try:
        threads_before = _thread_identity()
        files_before = _regular_files(tmp_path)

        for index in range(5_000):
            guala._log_substrate_event(
                "activity_started",
                ordinal=index,
            )

        captured = capsys.readouterr()
        assert "diary persistence failed" not in captured.out.lower()
        assert "diary persistence failed" not in captured.err.lower()
        assert _regular_files(tmp_path) == files_before == ()
        assert _thread_identity() == threads_before
        assert not hasattr(guala, "_diary_queue")
        assert not hasattr(guala, "_diary_thread")
        assert len(guala._substrate_events) == 1_000
        assert guala._substrate_events[0].sequence == 4_001
        assert guala._substrate_events[-1].sequence == 5_000
        assert guala.diary_persistence_status() == {
            "schema": "guala.diary_persistence_status.v2",
            "status": "retired",
            "available": False,
            "reason": (
                "bounded_in_memory_observation_ring_is_authoritative"
            ),
            "learned_state_authority": False,
            "disk_writes": 0,
            "queue_depth": 0,
            "worker_thread": False,
        }
    finally:
        guala.shutdown()
