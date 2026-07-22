"""Proof that heard language cannot detach from its physical terminal."""

import copy
import hashlib
import json
import os
import sys
from dataclasses import replace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AUDITORY_INCREMENTAL_EVENT_SCHEMA,
    AuditoryIncrementalTerminalEvent,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, allow_nan=False, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _terminal(label="one plus one"):
    stream_id = "causal-conversation-test"
    fingerprint = _digest({"full_field_terminal": label})
    event_id = _digest({
        "source_sample_end": 320,
        "source_sample_start": 0,
        "stream_id": stream_id,
        "structural_fingerprint": fingerprint,
    })
    l5 = _digest({"l5": label})
    transport = (_digest({"transport": 0}), _digest({"transport": 1}))
    cochlear = (_digest({"cochlear": 0}), _digest({"cochlear": 1}))
    joint = (_digest({"joint": 0}), _digest({"joint": 1}))
    payload = {
        "cochlear_receipt_sha256s": list(cochlear),
        "event_id": event_id,
        "joint_settlement_receipt_sha256s": list(joint),
        "l5_authority_receipt_sha256": l5,
        "recognition_state": "unique",
        "sample_rate_hz": 16_000,
        "schema": AUDITORY_INCREMENTAL_EVENT_SCHEMA,
        "source_sample_end": 320,
        "source_sample_start": 0,
        "stream_id": stream_id,
        "structural_fingerprint": fingerprint,
        "transport_receipt_sha256s": list(transport),
        "tutor_label": label,
    }
    return AuditoryIncrementalTerminalEvent(
        event_id=event_id,
        stream_id=stream_id,
        source_sample_start=0,
        source_sample_end=320,
        tutor_label=label,
        structural_fingerprint=fingerprint,
        l5_authority_receipt_sha256=l5,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        authority_receipt_sha256=_digest(payload),
    )


def _issue(guala, terminal):
    registry = guala._auditory_incremental_terminals
    with registry._lock:
        registry._issue_locked(terminal)
    return terminal


@pytest.fixture
def guala(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        yield engine
    finally:
        engine.shutdown()


@pytest.mark.parametrize("phased", ("0", "1"))
def test_terminal_and_language_share_one_causal_experience(
        guala, monkeypatch, phased):
    monkeypatch.setenv("CONVERSE_PHASED", phased)
    terminal = _issue(guala, _terminal())
    captured = []
    real_settle = guala.window_manager._settle_window

    def capture(record):
        captured.append(copy.deepcopy(record))
        return real_settle(record)

    guala.window_manager._settle_window = capture
    turn = guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )

    assert turn.response == "two"
    assert turn.response_source == "mathloom"
    assert turn.causal_experience_id == terminal.event_id
    assert (turn.causal_intake_receipt_sha256
            == terminal.authority_receipt_sha256)
    assert len(captured) == 1
    window = captured[0]
    assert window["context_id"] == f"causal-experience:{terminal.event_id}"
    detail = window["context_detail"]
    assert detail["experience_origin"] == "observed"
    assert detail["episode_ref"] == terminal.event_id
    assert detail["bundle_id"] == terminal.event_id
    assert detail["causal_experience_id"] == terminal.event_id
    assert detail["auditory_terminal_event"] == terminal.as_record()
    words = [
        entry for entry in window["entries"]
        if entry["modality"] == "word"
    ]
    assert [
        entry["provenance"]["detail"]["language_form"]
        for entry in words
    ] == ["one", "plus", "one"]
    assert all(
        entry["provenance"]["episode_ref"] == terminal.event_id
        and entry["provenance"]["bundle_id"] == terminal.event_id
        and entry["provenance"]["detail"]["causal_experience_id"]
        == terminal.event_id
        and entry["provenance"]["detail"][
            "causal_intake_receipt_sha256"
        ] == terminal.authority_receipt_sha256
        for entry in words
    )
    causal_refs = [
        reference
        for entries in guala.atlas.entries.values()
        for entry in entries
        for reference in entry.get("causal_experience_refs", ())
    ]
    assert causal_refs
    assert set(tuple(sorted(reference.items())) for reference in causal_refs) == {
        tuple(sorted({
            "causal_experience_id": terminal.event_id,
            "causal_intake_receipt_sha256": (
                terminal.authority_receipt_sha256
            ),
        }.items()))
    }
    assert len(causal_refs) <= len(set(
        entry["provenance"]["detail"]["language_form"]
        for entry in words
    ))


@pytest.mark.parametrize("phased", ("0", "1"))
def test_normal_conversation_result_keeps_terminal_identity(
        guala, monkeypatch, phased):
    monkeypatch.setenv("CONVERSE_PHASED", phased)
    terminal = _issue(guala, _terminal("hello guala"))

    turn = guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )

    assert turn.causal_experience_id == terminal.event_id
    assert (turn.causal_intake_receipt_sha256
            == terminal.authority_receipt_sha256)
    assert turn.response_source in {
        "silence_no_commit", "assemblage_commit", "fact_strand_commit"
    }


def test_label_only_or_altered_terminal_cannot_claim_heard_experience(guala):
    terminal = _issue(guala, _terminal("hello guala"))

    with pytest.raises(ValueError, match="requires its auditory terminal"):
        guala.converse(
            terminal.tutor_label,
            source="auditory:unresolved_source",
        )
    with pytest.raises(ValueError, match="differs from its auditory terminal"):
        guala.converse(
            "different words",
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    with pytest.raises(ValueError, match="receipt was altered"):
        guala.converse(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=replace(
                terminal,
                authority_receipt_sha256="0" * 64,
            ),
        )
    with pytest.raises(ValueError, match="invalid source provenance"):
        guala.converse(
            terminal.tutor_label,
            source="joe",
            causal_intake=terminal,
        )

    assert guala.window_manager.active_context_id is None


def test_self_consistent_unissued_terminal_and_replay_are_rejected(guala):
    forged = _terminal("hello guala")
    with pytest.raises(ValueError, match="not issued or was already consumed"):
        guala.converse(
            forged.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=forged,
        )

    terminal = _issue(guala, _terminal("one plus one"))
    first = guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )
    assert first.causal_experience_id == terminal.event_id
    with pytest.raises(ValueError, match="not issued or was already consumed"):
        guala.converse(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    assert guala._latest_auditory_causal_event_record == terminal.as_record()


def test_latest_complete_witness_persists_without_regranting_authority(
        guala, tmp_path):
    terminal = _issue(guala, _terminal("one plus one"))
    guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )

    guala.save_hot_state(str(tmp_path))
    with (tmp_path / "guala_teaching.json").open() as saved_file:
        saved = json.load(saved_file)
    record = saved["data"]["latest_auditory_causal_event"]
    assert record == terminal.as_record()
    restored = AuditoryIncrementalTerminalEvent.from_record(record)
    with pytest.raises(ValueError, match="not issued or was already consumed"):
        guala.converse(
            restored.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=restored,
        )
    fresh = Guala()
    try:
        with pytest.raises(
            ValueError, match="not issued or was already consumed"
        ):
            fresh.converse(
                restored.tutor_label,
                source="auditory:unresolved_source",
                causal_intake=restored,
            )
    finally:
        fresh.shutdown()


def test_causal_atlas_reference_is_bounded_and_exactly_restorable(guala):
    references = []
    for ordinal in range(6):
        reference = {
            "causal_experience_id": _digest({"event": ordinal}),
            "causal_intake_receipt_sha256": _digest({"receipt": ordinal}),
        }
        references.append(reference)
        guala.atlas.record(
            "language_fact",
            7,
            23,
            tick=ordinal,
            causal_experience_id=reference["causal_experience_id"],
            causal_intake_receipt_sha256=(
                reference["causal_intake_receipt_sha256"]
            ),
        )

    exact_entry = next(
        entry for entry in guala.atlas.entries[23]
        if entry["section"] == "language_fact" and entry["motif"] == 7
    )
    assert exact_entry["causal_experience_refs"] == references[-4:]
    assert all(
        "causal_experience_refs" not in entry
        for chi, entries in guala.atlas.entries.items()
        if chi != 23
        for entry in entries
        if entry["section"] == "language_fact" and entry["motif"] == 7
    )

    payload = {
        "tick": guala.atlas.tick,
        "entries": {
            str(chi): copy.deepcopy(entries)
            for chi, entries in guala.atlas.entries.items()
        },
    }
    restored = Guala()
    try:
        restored.tick = max(restored.tick, guala.tick, guala.atlas.tick)
        restored._apply_atlas(copy.deepcopy(payload), exact=True)
        restored_entry = next(
            entry for entry in restored.atlas.entries[23]
            if entry["section"] == "language_fact" and entry["motif"] == 7
        )
        assert restored_entry["causal_experience_refs"] == references[-4:]

        tampered = copy.deepcopy(payload)
        tampered["entries"]["23"][0]["causal_experience_refs"][0][
            "causal_intake_receipt_sha256"
        ] = "not-a-digest"
        with pytest.raises(ValueError, match="must be a SHA-256 digest"):
            restored._apply_atlas(tampered, exact=True)
    finally:
        restored.shutdown()
