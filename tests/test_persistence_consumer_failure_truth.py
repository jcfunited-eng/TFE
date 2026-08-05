import threading

import pytest

from dsf_ai_service.substrate.persistence_consumer import (
    CHECKPOINT_INTERVAL,
    PersistenceCapacityError,
    PersistenceConsumer,
    ring_checkpoint_state,
)


class _OneEventCursor:
    def __init__(self):
        self.sent = False

    def read_available(self):
        if self.sent:
            return []
        self.sent = True
        return [{
            "seq": 1,
            "kind": "experience",
            "tick": 1,
            "data": {},
        }]


class _Ring:
    def __init__(self):
        self.cursor = _OneEventCursor()

    def subscribe(self):
        return self.cursor


def test_background_disk_failure_is_re_raised_by_stop(tmp_path, monkeypatch):
    consumer = PersistenceConsumer(
        _Ring(), str(tmp_path), lambda: {},
        receipt_hmac_key=b"r" * 32)
    attempted = threading.Event()
    failure = OSError("injected durable-write failure")

    def reject_write(_events):
        attempted.set()
        raise failure

    monkeypatch.setattr(consumer, "_write_events", reject_write)
    consumer.start()
    assert attempted.wait(1.0)

    with pytest.raises(
        RuntimeError,
        match="persistence consumer failed",
    ) as exc_info:
        consumer.stop(timeout=2.0)

    assert exc_info.value.__cause__ is failure
    assert not consumer._thread.is_alive()
    assert consumer._log_fd is None


def test_checkpoint_snapshot_failure_stops_writer_and_is_re_raised(
    tmp_path,
    monkeypatch,
):
    attempted = threading.Event()
    failure = RuntimeError("snapshot state unavailable")

    def reject_snapshot():
        attempted.set()
        raise failure

    monkeypatch.setattr(
        "dsf_ai_service.substrate.persistence_consumer."
        "CHECKPOINT_INTERVAL",
        1,
    )
    consumer = PersistenceConsumer(
        _Ring(), str(tmp_path), reject_snapshot,
        receipt_hmac_key=b"r" * 32)
    consumer.start()
    assert attempted.wait(1.0)

    with pytest.raises(
        RuntimeError,
        match="persistence consumer failed",
    ) as exc_info:
        consumer.stop(timeout=2.0)

    assert exc_info.value.__cause__ is failure
    assert not list(tmp_path.glob("checkpoint-*.json"))
    assert consumer._events_since_checkpoint == 1
    assert not consumer._thread.is_alive()
    assert consumer._log_fd is None


def test_checkpoint_log_truncation_failure_stops_writer_and_is_re_raised(
    tmp_path,
    monkeypatch,
):
    attempted = threading.Event()
    failure = OSError("event-log truncation denied")

    def reject_truncation(_descriptor, _length):
        attempted.set()
        raise failure

    monkeypatch.setattr(
        "dsf_ai_service.substrate.persistence_consumer."
        "CHECKPOINT_INTERVAL",
        1,
    )
    monkeypatch.setattr(
        "dsf_ai_service.substrate.persistence_consumer.os.ftruncate",
        reject_truncation,
    )
    consumer = PersistenceConsumer(
        _Ring(),
        str(tmp_path),
        lambda: ring_checkpoint_state(1),
        receipt_hmac_key=b"r" * 32,
    )
    consumer.start()
    assert attempted.wait(1.0)

    with pytest.raises(
        RuntimeError,
        match="persistence consumer failed",
    ) as exc_info:
        consumer.stop(timeout=2.0)

    assert exc_info.value.__cause__ is failure
    assert (tmp_path / "checkpoint-1.json").is_file()
    assert consumer._events_since_checkpoint == 1
    assert not consumer._thread.is_alive()
    assert consumer._log_fd is None


def test_start_cannot_follow_external_event_log_symlink(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    external = tmp_path / "external.events"
    external.write_text("DO-NOT-CHANGE\n")
    (state_dir / "events.log").symlink_to(external)
    consumer = PersistenceConsumer(
        _Ring(), str(state_dir), lambda: {},
        receipt_hmac_key=b"r" * 32)

    with pytest.raises(OSError):
        consumer.start()

    assert external.read_text() == "DO-NOT-CHANGE\n"
    assert consumer._log_fd is None
    assert consumer._thread is None


def test_consumer_cannot_start_two_persistence_threads(tmp_path):
    consumer = PersistenceConsumer(
        _Ring(), str(tmp_path), lambda: {},
        receipt_hmac_key=b"r" * 32)
    consumer.start()
    first_thread = consumer._thread
    first_descriptor = consumer._log_fd.fileno()

    with pytest.raises(
        RuntimeError,
        match="cannot be started more than once",
    ):
        consumer.start()

    assert consumer._thread is first_thread
    assert consumer._log_fd.fileno() == first_descriptor
    assert first_thread.is_alive()
    consumer.stop(timeout=2.0)
    assert not first_thread.is_alive()
    assert consumer._log_fd is None


def test_oversized_legacy_event_segment_is_refused_without_deletion(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    log = state_dir / "events.log"
    prior = b"x" * (CHECKPOINT_INTERVAL + 1)
    log.write_bytes(prior)
    consumer = PersistenceConsumer(
        _Ring(),
        str(state_dir),
        lambda: ring_checkpoint_state(0),
        max_event_record_bytes=1,
        max_checkpoint_bytes=1024,
        max_event_segment_bytes=CHECKPOINT_INTERVAL,
        receipt_hmac_key=b"r" * 32,
    )

    with pytest.raises(
            PersistenceCapacityError,
            match="segment exceeds"):
        consumer.start()

    assert log.read_bytes() == prior
    assert consumer._thread is None
    assert consumer._log_fd is None
