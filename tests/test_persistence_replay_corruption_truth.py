import json

import pytest

from dsf_ai_service.substrate.event_log import (
    EventLog,
    EventLogReplayError,
)
from dsf_ai_service.substrate.persistence_consumer import (
    PersistenceConsumer,
    PersistenceRecoveryError,
)


def test_event_log_interior_corruption_halts_replay(tmp_path):
    (tmp_path / "guala.events.jsonl").write_text(
        '{"t":"feedback","seq":0}\n'
        '{"t":BROKEN}\n'
        '{"t":"feedback","seq":2}\n'
    )

    with pytest.raises(
        EventLogReplayError,
        match="malformed complete record",
    ):
        EventLog(str(tmp_path), "guala")


def test_event_log_ignores_only_unterminated_crash_tail(tmp_path):
    (tmp_path / "guala.events.jsonl").write_text(
        '{"t":"feedback","seq":0}\n'
        '{"t":"feedback","seq":'
    )

    event_log = EventLog(str(tmp_path), "guala")

    assert [event["seq"] for event in event_log.read_all()] == [0]
    assert event_log.count == 1


def test_checkpoint_event_interior_corruption_halts_recovery(tmp_path):
    (tmp_path / "checkpoint-0.json").write_text(json.dumps({
        "seq": 0,
        "state": {"identity": "guala"},
    }))
    (tmp_path / "events.log").write_text(
        '{"seq":1}\n'
        '{"seq":BROKEN}\n'
        '{"seq":3}\n'
    )

    with pytest.raises(
        PersistenceRecoveryError,
        match="malformed complete record",
    ):
        PersistenceConsumer.recover(str(tmp_path))


def test_checkpoint_recovery_ignores_only_unterminated_crash_tail(tmp_path):
    (tmp_path / "checkpoint-0.json").write_text(json.dumps({
        "seq": 0,
        "state": {"identity": "guala"},
    }))
    (tmp_path / "events.log").write_text(
        '{"seq":1}\n'
        '{"seq":'
    )

    checkpoint, events = PersistenceConsumer.recover(str(tmp_path))

    assert checkpoint["seq"] == 0
    assert [event["seq"] for event in events] == [1]


@pytest.mark.parametrize("invalid_sequence", [True, "1", -1])
def test_checkpoint_recovery_rejects_invalid_event_sequence_metadata(
        tmp_path, invalid_sequence):
    (tmp_path / "checkpoint-0.json").write_text(json.dumps({
        "seq": 0,
        "state": {"identity": "guala"},
    }))
    (tmp_path / "events.log").write_text(json.dumps({
        "seq": invalid_sequence,
    }) + "\n")

    with pytest.raises(
        PersistenceRecoveryError,
        match="invalid sequence metadata",
    ):
        PersistenceConsumer.recover(str(tmp_path))


@pytest.mark.parametrize("sequences", [(0, 2), (0, 0)])
def test_event_log_rejects_gapped_or_duplicate_sequence(
        tmp_path, sequences):
    (tmp_path / "guala.events.jsonl").write_text("".join(
        json.dumps({"t": "feedback", "seq": sequence}) + "\n"
        for sequence in sequences
    ))

    with pytest.raises(
        EventLogReplayError,
        match="sequence is not contiguous",
    ):
        EventLog(str(tmp_path), "guala")


@pytest.mark.parametrize("sequences", [(1, 3), (1, 1)])
def test_checkpoint_recovery_rejects_gapped_or_duplicate_sequence(
        tmp_path, sequences):
    (tmp_path / "checkpoint-0.json").write_text(json.dumps({
        "seq": 0,
        "state": {"identity": "guala"},
    }))
    (tmp_path / "events.log").write_text("".join(
        json.dumps({"seq": sequence}) + "\n"
        for sequence in sequences
    ))

    with pytest.raises(
        PersistenceRecoveryError,
        match="replay sequence is not contiguous",
    ):
        PersistenceConsumer.recover(str(tmp_path))
