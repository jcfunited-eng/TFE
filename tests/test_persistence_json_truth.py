import math

import pytest

from dsf_ai_service.substrate.event_log import EventLog
from dsf_ai_service.substrate.persistence_consumer import (
    PersistenceCapacityError,
    PersistenceConsumer,
)


class _Ring:
    @staticmethod
    def subscribe():
        return object()


@pytest.mark.parametrize("unsupported", [b"physical-bytes", math.nan])
def test_event_log_rejects_json_substitution_without_advancing_sequence(
        tmp_path, unsupported):
    event_log = EventLog(str(tmp_path), "guala")

    with pytest.raises((TypeError, ValueError)):
        event_log.write("experience", payload=unsupported)

    assert event_log.count == 0
    assert event_log.read_all() == []


def test_ring_event_writer_rejects_json_substitution_before_append(tmp_path):
    consumer = PersistenceConsumer(
        _Ring(), str(tmp_path), lambda: {},
        receipt_hmac_key=b"r" * 32)
    log_path = tmp_path / "events.log"
    consumer._log_fd = log_path.open("a")
    try:
        with pytest.raises(ValueError):
            consumer._write_events([
                {
                    "seq": 1,
                    "kind": "probe",
                    "tick": 1,
                    "data": {"payload": b"physical-bytes"},
                },
            ])
    finally:
        consumer._log_fd.close()
        consumer._log_fd = None

    assert log_path.read_bytes() == b""
    assert consumer._unfsynced == 0


def test_checkpoint_rejects_json_substitution_without_truncating_log(
        tmp_path):
    consumer = PersistenceConsumer(
        _Ring(),
        str(tmp_path),
        lambda: {"payload": b"physical-bytes"},
        receipt_hmac_key=b"r" * 32,
    )
    log_path = tmp_path / "events.log"
    consumer._log_fd = log_path.open("a")
    consumer._log_fd.write('{"seq":1}\n')
    consumer._log_fd.flush()
    try:
        with pytest.raises(PersistenceCapacityError):
            consumer._write_checkpoint(1)
    finally:
        consumer._log_fd.close()
        consumer._log_fd = None

    assert log_path.read_text() == '{"seq":1}\n'
    assert not (tmp_path / "checkpoint-1.json").exists()
    assert not (tmp_path / "checkpoint-1.json.tmp").exists()
