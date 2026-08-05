from concurrent.futures import ThreadPoolExecutor

import pytest

from dsf_ai_service.substrate.event_log import (
    EventLog,
    EventLogReplayError,
)


def test_snapshot_boundary_and_restart_preserve_next_event_sequence(tmp_path):
    log = EventLog(str(tmp_path), "guala")
    first = log.write("vocab_install", word="apple")
    snapshot_boundary = log.count
    post_snapshot = log.write("feedback", correct=True)

    assert first["seq"] == 0
    assert snapshot_boundary == 1
    assert post_snapshot["seq"] == snapshot_boundary
    assert log.read_since(snapshot_boundary) == [post_snapshot]

    compaction_boundary = log.count
    assert log.truncate_before(compaction_boundary) == 0

    restarted = EventLog(str(tmp_path), "guala")
    after_restart = restarted.write("feedback", correct=False)

    assert restarted.count == compaction_boundary + 1
    assert after_restart["seq"] == compaction_boundary
    assert restarted.read_since(compaction_boundary) == [after_restart]


def test_concurrent_writes_receive_one_contiguous_sequence(tmp_path):
    log = EventLog(str(tmp_path), "guala")

    with ThreadPoolExecutor(max_workers=8) as executor:
        events = tuple(executor.map(
            lambda value: log.write("feedback", correct=bool(value % 2)),
            range(80),
        ))

    sequences = sorted(event["seq"] for event in events)
    persisted = sorted(event["seq"] for event in log.read_all())

    assert sequences == list(range(80))
    assert persisted == sequences
    assert log.count == 80


@pytest.mark.parametrize(
    "event_type",
    ["", " feedback", "feedback ", "_compaction_boundary", ["feedback"]],
)
def test_public_event_type_is_canonical_and_cannot_claim_internal_marker(
        tmp_path, event_type):
    log = EventLog(str(tmp_path), "guala")

    with pytest.raises(
        ValueError,
        match="canonical nonempty public string",
    ):
        log.write(event_type, payload="real-event")

    assert log.count == 0
    assert log.read_all() == []


def test_payload_bearing_compaction_marker_halts_replay(tmp_path):
    (tmp_path / "guala.events.jsonl").write_text(
        '{"t":"_compaction_boundary","seq":0,"payload":"real-event"}\n'
    )

    with pytest.raises(
        EventLogReplayError,
        match="forged compaction marker",
    ):
        EventLog(str(tmp_path), "guala")


def test_compaction_cannot_advance_beyond_allocated_event_frontier(tmp_path):
    log = EventLog(str(tmp_path), "guala")
    log.write("feedback", correct=True)
    log.write("feedback", correct=False)
    before = (tmp_path / "guala.events.jsonl").read_bytes()

    with pytest.raises(
        ValueError,
        match="cannot exceed the allocated event frontier",
    ):
        log.truncate_before(100)

    assert log.count == 2
    assert (tmp_path / "guala.events.jsonl").read_bytes() == before
    restarted = EventLog(str(tmp_path), "guala")
    assert restarted.write("feedback", correct=True)["seq"] == 2


def test_compaction_cannot_move_behind_durable_event_floor(tmp_path):
    log = EventLog(str(tmp_path), "guala")
    for value in range(3):
        log.write("feedback", value=value)
    log.truncate_before(3)
    log.write("feedback", value=3)
    before = (tmp_path / "guala.events.jsonl").read_bytes()

    with pytest.raises(
        ValueError,
        match="cannot precede the durable event floor",
    ):
        log.truncate_before(1)

    assert log.count == 4
    assert (tmp_path / "guala.events.jsonl").read_bytes() == before
    restarted = EventLog(str(tmp_path), "guala")
    assert [event["seq"] for event in restarted.read_all()] == [3]
    assert restarted.write("feedback", value=4)["seq"] == 4


@pytest.mark.parametrize(
    "session_id",
    ["", ".", "..", "../escaped", "nested/session", "nested\\session", "\x00"],
)
def test_session_id_cannot_escape_event_log_directory(tmp_path, session_id):
    with pytest.raises(
        ValueError,
        match="one nonempty path component",
    ):
        EventLog(str(tmp_path / "sessions"), session_id)

    assert not (tmp_path / "escaped.events.jsonl").exists()


def test_opaque_single_component_session_id_is_preserved(tmp_path):
    log = EventLog(str(tmp_path), "session:room 1")
    event = log.write("feedback", correct=True)

    assert event["seq"] == 0
    assert log.session_id == "session:room 1"
    assert (tmp_path / "session:room 1.events.jsonl").is_file()


def test_event_log_directory_cannot_be_a_symlink(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    declared = tmp_path / "declared"
    declared.symlink_to(external, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="directory must be a real directory",
    ):
        EventLog(str(declared), "guala")

    assert not (external / "guala.events.jsonl").exists()


def test_event_log_file_cannot_be_a_symlink(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    external = tmp_path / "external.events"
    external.write_text("")
    (logs / "guala.events.jsonl").symlink_to(external)

    with pytest.raises(
        ValueError,
        match="path must be a private regular file",
    ):
        EventLog(str(logs), "guala")

    assert external.read_bytes() == b""


def test_event_log_file_cannot_have_an_external_hard_link(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    event_path = logs / "guala.events.jsonl"
    event_path.write_text("")
    (tmp_path / "external-hard-link.events").hardlink_to(event_path)

    with pytest.raises(
        ValueError,
        match="path must be a private regular file",
    ):
        EventLog(str(logs), "guala")


def test_live_append_cannot_mutate_replacement_hard_link(tmp_path):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    log.write("feedback", correct=True)
    event_path = logs / "guala.events.jsonl"
    event_path.unlink()
    external = tmp_path / "external.events"
    external.write_text("DO-NOT-CHANGE\n")
    event_path.hardlink_to(external)
    before = external.read_bytes()

    with pytest.raises(
        ValueError,
        match="must remain a private regular file",
    ):
        log.write("feedback", correct=False)

    assert external.read_bytes() == before
    assert event_path.read_bytes() == before
    assert log.count == 1


def test_live_append_cannot_follow_replacement_directory(tmp_path):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    log.write("feedback", correct=True)
    original_logs = tmp_path / "original-logs"
    logs.rename(original_logs)
    external = tmp_path / "external"
    external.mkdir()
    logs.symlink_to(external, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="must remain the startup directory",
    ):
        log.write("feedback", correct=False)

    assert not (external / "guala.events.jsonl").exists()
    assert log.count == 1
    assert (
        original_logs / "guala.events.jsonl"
    ).read_text().count("\n") == 1


def test_live_replay_cannot_accept_replacement_hard_link(tmp_path):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    external = tmp_path / "external.events"
    external.write_text(
        '{"t":"feedback","seq":0,"correct":true}\n'
    )
    event_path = logs / "guala.events.jsonl"
    event_path.hardlink_to(external)

    with pytest.raises(
        ValueError,
        match="must remain a private regular file",
    ):
        log.read_all()

    assert log.count == 0
    assert external.read_text() == (
        '{"t":"feedback","seq":0,"correct":true}\n'
    )


def test_live_replay_cannot_follow_replacement_directory(tmp_path):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    log.write("feedback", correct=True)
    original_logs = tmp_path / "original-logs"
    logs.rename(original_logs)
    external = tmp_path / "external"
    external.mkdir()
    external_event_path = external / "guala.events.jsonl"
    external_event_path.write_text(
        '{"t":"feedback","seq":0,"correct":false}\n'
    )
    logs.symlink_to(external, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="must remain the startup directory",
    ):
        log.read_all()

    assert log.count == 1
    assert external_event_path.read_text() == (
        '{"t":"feedback","seq":0,"correct":false}\n'
    )
    assert '"correct": true' in (
        original_logs / "guala.events.jsonl"
    ).read_text()


def test_exists_cannot_report_replacement_directory_file(tmp_path):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    original_logs = tmp_path / "original-logs"
    logs.rename(original_logs)
    external = tmp_path / "external"
    external.mkdir()
    external_event_path = external / "guala.events.jsonl"
    external_event_path.write_text("external-history\n")
    logs.symlink_to(external, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="must remain the startup directory",
    ):
        log.exists()

    assert external_event_path.read_text() == "external-history\n"
    assert not (original_logs / "guala.events.jsonl").exists()


def test_compaction_temporary_path_cannot_redirect_write(tmp_path):
    log = EventLog(str(tmp_path), "guala")
    log.write("feedback", correct=True)
    before = (tmp_path / "guala.events.jsonl").read_bytes()
    external = tmp_path / "external"
    external.write_text("DO-NOT-CHANGE")
    temporary = tmp_path / "guala.events.jsonl.tmp"
    temporary.symlink_to(external)

    with pytest.raises(FileExistsError):
        log.truncate_before(log.count)

    assert external.read_text() == "DO-NOT-CHANGE"
    assert (tmp_path / "guala.events.jsonl").read_bytes() == before
    assert not (tmp_path / "guala.events.jsonl").is_symlink()
    assert not temporary.exists()


def test_compaction_cannot_follow_directory_replaced_after_read(
    tmp_path,
    monkeypatch,
):
    logs = tmp_path / "logs"
    log = EventLog(str(logs), "guala")
    log.write("feedback", correct=True)
    original_read = log._read_all_unlocked
    original_logs = tmp_path / "original-logs"
    external = tmp_path / "external"

    def read_then_replace_directory():
        events = original_read()
        logs.rename(original_logs)
        external.mkdir()
        logs.symlink_to(external, target_is_directory=True)
        return events

    monkeypatch.setattr(
        log,
        "_read_all_unlocked",
        read_then_replace_directory,
    )

    with pytest.raises(
        ValueError,
        match="must remain the startup directory",
    ):
        log.truncate_before(log.count)

    assert not (external / "guala.events.jsonl").exists()
    assert not (external / "guala.events.jsonl.tmp").exists()
    assert log.count == 1
    assert (
        original_logs / "guala.events.jsonl"
    ).read_text().count("\n") == 1
