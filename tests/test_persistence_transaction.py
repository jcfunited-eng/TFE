"""Focused production invariants for Guala persistence serialization."""

import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.save_coordinator import SaveCoordinator
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _bare_guala():
    """Build only the coordination surface needed by these unit tests."""
    guala = object.__new__(Guala)
    guala._persistence_lock = threading.RLock()
    guala._event_log_lock = threading.RLock()
    guala.tick = 0
    guala._guala_identity = "persistence-test"
    return guala


def test_persistence_entry_points_serialize_and_reenter():
    guala = _bare_guala()
    hot_entered = threading.Event()
    release_hot = threading.Event()
    full_entered = threading.Event()
    errors = []

    def hot_body(_state_dir):
        hot_entered.set()
        assert release_hot.wait(2.0)
        return "hot"

    def full_body(_state_dir):
        full_entered.set()
        return "full"

    guala._save_hot_state_locked = hot_body
    guala._save_full_state_locked = full_body

    def run(call):
        try:
            call()
        except BaseException as exc:  # surface thread assertions to pytest
            errors.append(exc)

    hot_thread = threading.Thread(target=run, args=(guala.save_hot_state,))
    full_thread = threading.Thread(target=run, args=(guala.save_full_state,))
    hot_thread.start()
    assert hot_entered.wait(1.0)
    full_thread.start()

    # The second persistence generation cannot enter while the first owns the
    # boundary.  Releasing the first is the only event that permits progress.
    assert not full_entered.wait(0.1)
    release_hot.set()
    hot_thread.join(2.0)
    full_thread.join(2.0)
    assert not hot_thread.is_alive()
    assert not full_thread.is_alive()
    assert full_entered.is_set()
    assert not errors

    # Compound callers hold the same boundary and invoke public entry points;
    # this must re-enter rather than deadlock.
    with guala.persistence_transaction():
        assert guala.save_full_state() == "full"


def test_wave_write_failure_propagates_and_cleans_tmp(tmp_path):
    guala = _bare_guala()

    class BrokenWaveAtlas:
        cells = {}

        @staticmethod
        def to_npz(_path):
            raise OSError("wave write failed")

    guala.wave_atlas = BrokenWaveAtlas()

    with pytest.raises(OSError, match="wave write failed"):
        guala._save_wave_atlas(str(tmp_path))

    assert not (tmp_path / "wave_atlas.npz.tmp").exists()


def test_hot_save_reports_any_mutable_file_failure_and_does_not_advance(
        tmp_path, monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    guala = Guala()
    try:
        guala._guala_identity = "persistence-test"
        guala._log_substrate_event = lambda *_args, **_kwargs: None
        guala._last_save_tick = 77
        guala._last_save_timestamp = "before"
        real_atomic_write = Guala._atomic_write

        def controlled_write(path, data, fsync=False):
            if os.path.basename(path) == "guala_needs.json":
                raise OSError("needs write failed")
            return real_atomic_write(path, data, fsync)

        guala._atomic_write = controlled_write

        with pytest.raises(RuntimeError, match="guala_needs.json.*needs write failed"):
            guala.save_hot_state(str(tmp_path))

        assert guala._last_save_tick == 77
        assert guala._last_save_timestamp == "before"
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        guala.shutdown()


def test_compaction_failure_propagates_and_keeps_source(tmp_path, monkeypatch):
    guala = _bare_guala()
    guala.EVENTS_LOG = "events.log"
    source = tmp_path / guala.EVENTS_LOG
    source.write_bytes(b"first\nsecond\n")
    original = source.read_bytes()

    def fail_replace(_src, _dst):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        guala.compact_events(str(tmp_path), keep_after_offset=6)

    assert source.read_bytes() == original
    assert not (tmp_path / "events.log.tmp").exists()


def test_already_sleeping_deploy_revalidates_and_never_leaves_false_marker(
        tmp_path):
    guala = _bare_guala()
    guala.lock = threading.RLock()
    guala.tick = 42
    guala.SLEEPING_MARKER = ".sleeping"
    guala._current_activity = SimpleNamespace(
        kind="SLEEPING", expected_end_tick=142)
    marker = tmp_path / guala.SLEEPING_MARKER
    marker.write_text('{"stale": true}')
    wave_called = False

    def fail_full(_state_dir):
        raise OSError("full save failed")

    def wave(_state_dir):
        nonlocal wave_called
        wave_called = True

    guala.save_full_state = fail_full
    guala._save_wave_atlas = wave

    with pytest.raises(OSError, match="full save failed"):
        guala.manual_sleep(str(tmp_path))

    assert not marker.exists()
    assert not wave_called


def test_save_coordinator_does_not_publish_or_rate_limit_failed_save():
    guala = SimpleNamespace(
        tick=1000,
        is_present_active=lambda: False,
    )

    def fail_hot(_state_dir):
        raise OSError("hot failed")

    def fail_full(_state_dir):
        raise OSError("full failed")

    guala.save_hot_state = fail_hot
    guala.save_full_state = fail_full
    coordinator = SaveCoordinator(guala, "/unused", s3_bucket="bucket")
    coordinator.queue_s3 = lambda *_args, **_kwargs: pytest.fail(
        "failed persistence must not queue S3")
    prior_wall = coordinator.last_save_wall
    prior_tick = coordinator.last_save_tick

    assert coordinator.maybe_save("backup") is False
    assert coordinator.last_save_wall == prior_wall
    assert coordinator.last_save_tick == prior_tick

    with pytest.raises(OSError, match="full failed"):
        coordinator.force_save("backup")


def test_event_append_waits_for_compaction_replace(tmp_path, monkeypatch):
    guala = _bare_guala()
    guala.EVENTS_LOG = "events.log"
    guala.EVENTS_MAX_BYTES = 10_000_000
    guala.EVENTS_MAX_ROTATED = 2
    guala.tick = 9
    source = tmp_path / guala.EVENTS_LOG
    source.write_bytes(b"captured\n")
    replace_entered = threading.Event()
    permit_replace = threading.Event()
    append_finished = threading.Event()
    real_replace = os.replace

    def controlled_replace(src, dst):
        replace_entered.set()
        assert permit_replace.wait(2.0)
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", controlled_replace)

    compact_thread = threading.Thread(
        target=lambda: guala.compact_events(
            str(tmp_path), keep_after_offset=len(b"captured\n")))
    compact_thread.start()
    assert replace_entered.wait(1.0)

    append_thread = threading.Thread(
        target=lambda: (
            guala.log_event(str(tmp_path), "after_compact", value=1),
            append_finished.set()))
    append_thread.start()
    assert not append_finished.wait(0.1)

    permit_replace.set()
    compact_thread.join(2.0)
    append_thread.join(2.0)
    assert not compact_thread.is_alive()
    assert not append_thread.is_alive()
    assert b'"type": "after_compact"' in source.read_bytes()
