import json

from dsf_ai_service.substrate.persistence_consumer import (
    LOCAL_CHECKPOINT_RETENTION,
    PersistenceConsumer,
    ring_checkpoint_state,
)


def _checkpoint(path, sequence, state):
    path.write_text(json.dumps({
        "seq": sequence,
        "ts": float(sequence),
        "state": state,
    }))


def test_torn_newest_checkpoint_falls_back_to_valid_predecessor(tmp_path):
    _checkpoint(
        tmp_path / "checkpoint-10.json",
        10,
        {"identity": "guala-valid"},
    )
    (tmp_path / "checkpoint-20.json").write_text('{"seq":20')
    (tmp_path / "events.log").write_text(
        '{"seq":11,"event":"after-valid"}\n'
    )

    checkpoint, events = PersistenceConsumer.recover(str(tmp_path))

    assert checkpoint["seq"] == 10
    assert checkpoint["state"] == {"identity": "guala-valid"}
    assert [event["seq"] for event in events] == [11]


def test_filename_body_sequence_mismatch_cannot_override_predecessor(
        tmp_path):
    _checkpoint(
        tmp_path / "checkpoint-10.json",
        10,
        {"identity": "guala-valid"},
    )
    _checkpoint(
        tmp_path / "checkpoint-20.json",
        12,
        {"identity": "wrong-lineage"},
    )
    (tmp_path / "events.log").write_text(
        '{"seq":11,"event":"after-valid"}\n'
    )

    checkpoint, events = PersistenceConsumer.recover(str(tmp_path))

    assert checkpoint["seq"] == 10
    assert checkpoint["state"] == {"identity": "guala-valid"}
    assert [event["seq"] for event in events] == [11]


def test_checkpoint_writes_retain_exact_current_and_predecessor(tmp_path):
    class Ring:
        @staticmethod
        def subscribe():
            return object()

    consumer = PersistenceConsumer(
        Ring(),
        str(tmp_path),
        lambda: ring_checkpoint_state(60),
        receipt_hmac_key=b"r" * 32,
    )
    consumer._log_fd = (tmp_path / "events.log").open("a")
    try:
        for sequence in range(10, 70, 10):
            consumer._write_checkpoint(sequence)
    finally:
        consumer._log_fd.close()
        consumer._log_fd = None

    checkpoints = sorted(tmp_path.glob("checkpoint-*.json"))

    assert len(checkpoints) == LOCAL_CHECKPOINT_RETENTION
    assert [path.name for path in checkpoints] == [
        "checkpoint-50.json",
        "checkpoint-60.json",
    ]
    recovered, events = PersistenceConsumer.recover(str(tmp_path))
    assert recovered["seq"] == 60
    assert events == []
