"""Exact v4 quarantine and pristine v5 re-observation persistence tests."""

import base64
import gzip
import hashlib
import json

import pytest

import dsf_ai_service.v4.gualaloom_v5_engine as engine_module
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    MAX_ENCODED_SNAPSHOT_BYTES,
    inspect_legacy_v4_envelope,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _canonical(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _legacy_v4_envelope():
    payload = _canonical({
        "branch_capacity_per_class": 4,
        "class_capacity_per_kind": 64,
        "classes": [],
        "schema": "guala.auditory.causal_path.v4",
        "source_continuity": (
            "unavailable_without_receipted_stream_authority"
        ),
        "tutor_authority_required": False,
    })
    return {
        "encoding": "gzip+base64",
        "payload": base64.b64encode(
            gzip.compress(payload, compresslevel=6, mtime=0)
        ).decode("ascii"),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "schema": LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    }


def _disable_background_substrate(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "persistence-test-key")


def _write_exact_state(state_dir, monkeypatch):
    _disable_background_substrate(monkeypatch)
    writer = Guala()
    try:
        writer._generate_genesis_identity(str(state_dir))
        writer.tick = 19
        writer.save_full_state(str(state_dir))
    finally:
        writer.strict_shutdown(timeout=30.0)


def test_v4_inspector_is_integrity_only_and_fails_closed():
    envelope = _legacy_v4_envelope()
    inspection = inspect_legacy_v4_envelope(envelope)
    assert inspection.envelope_canonical_sha256 == hashlib.sha256(
        _canonical(envelope)
    ).hexdigest()
    assert inspection.encoded_payload_bytes == len(envelope["payload"])

    tampered = dict(envelope)
    tampered["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="integrity check"):
        inspect_legacy_v4_envelope(tampered)

    unknown = dict(envelope)
    unknown["schema"] = "guala.auditory.causal_path.gzip.unknown"
    with pytest.raises(ValueError, match="schema is invalid"):
        inspect_legacy_v4_envelope(unknown)

    oversized = dict(envelope)
    oversized["payload"] = "A" * (MAX_ENCODED_SNAPSHOT_BYTES + 1)
    with pytest.raises(ValueError, match="encoded boundary"):
        inspect_legacy_v4_envelope(oversized)


def test_v4_exact_load_quarantines_dependents_then_hot_save_restarts_v5(
        tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    _write_exact_state(state_dir, monkeypatch)
    teaching_path = state_dir / "guala_teaching.json"
    teaching = json.loads(teaching_path.read_text())
    legacy = _legacy_v4_envelope()
    legacy_action = dict(teaching["data"]["causal_action"])
    legacy_action["schema"] = "guala.causal_action.legacy.v0"
    legacy_terminal = {
        "schema": "guala.auditory.incremental_terminal.legacy.v2",
        "opaque_receipt": "preserve-without-applying",
    }
    teaching["data"]["auditory_reciprocity"] = legacy
    teaching["data"]["causal_action"] = legacy_action
    teaching["data"]["latest_auditory_causal_event"] = legacy_terminal
    teaching["data"].pop("auditory_v4_archive", None)
    teaching_path.write_text(json.dumps(teaching))

    transitioned = Guala()
    restarted = None
    try:
        transitioned.load_full_state(
            str(state_dir), require_exact_binary=True
        )
        assert transitioned._load_successful, transitioned._load_errors
        status = transitioned.auditory_l5_status()
        assert status["persistence_transition"] == {
            "active_envelope_schema": AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
            "state": "v5_empty_reobservation_required",
            "legacy_archive_schema": "guala.auditory.persistence_archive.v1",
            "legacy_v4_preserved": True,
            "legacy_v4_envelope_sha256": hashlib.sha256(
                _canonical(legacy)
            ).hexdigest(),
            "legacy_v4_encoded_payload_bytes": len(legacy["payload"]),
            "legacy_v4_applied": False,
            "quarantined_causal_action_present": True,
            "quarantined_terminal_event_present": True,
        }
        assert not any(status["reciprocity"]["class_counts"].values())
        assert status["incremental_terminal"]["learned_cells"] == 0
        assert status["incremental_terminal"][
            "issued_terminal_authorities"
        ] == 0
        action_status = transitioned._causal_action_owner.status()
        assert action_status["actions"] == 0
        assert action_status["witnesses"] == 0
        assert action_status["issued_actions"] == 0
        assert transitioned._latest_auditory_causal_event_record is None

        transitioned.save_hot_state(str(state_dir))
        preserved = json.loads(teaching_path.read_text())["data"]
        assert preserved["auditory_reciprocity"]["schema"] == (
            AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA
        )
        archive = preserved["auditory_v4_archive"]
        assert archive["auditory_reciprocity_v4"] == legacy
        assert archive["quarantined_causal_action"] == legacy_action
        assert archive[
            "quarantined_latest_auditory_causal_event"
        ] == legacy_terminal

        transitioned.strict_shutdown(timeout=30.0)
        transitioned = None
        restarted = Guala()
        restarted.load_full_state(
            str(state_dir), require_exact_binary=True
        )
        assert restarted._load_successful, restarted._load_errors
        restarted_status = restarted.auditory_l5_status()
        assert restarted_status["persistence_transition"][
            "state"
        ] == "v5_empty_reobservation_required"
        assert restarted._auditory_v4_archive == archive
        assert restarted._latest_auditory_causal_event_record is None
    finally:
        if transitioned is not None:
            transitioned.strict_shutdown(timeout=30.0)
        if restarted is not None:
            restarted.strict_shutdown(timeout=30.0)


def test_archive_digest_change_and_unknown_active_schema_fail_closed(
        monkeypatch):
    _disable_background_substrate(monkeypatch)
    guala = Guala()
    try:
        payload = guala._teaching_persistence_payload()
        payload["auditory_reciprocity"] = _legacy_v4_envelope()
        payload["auditory_v4_archive"] = None
        Guala._validate_teaching_payload(payload, engine_tick=0)

        payload["auditory_reciprocity"]["schema"] = "unknown"
        with pytest.raises(ValueError, match="schema is unknown"):
            Guala._validate_teaching_payload(payload, engine_tick=0)

        legacy = _legacy_v4_envelope()
        archive = Guala._build_auditory_v4_archive(
            legacy, {"opaque": "action"}, {"opaque": "terminal"}
        )
        archive["quarantined_causal_action"]["opaque"] = "changed"
        with pytest.raises(ValueError, match="digest changed"):
            Guala._validate_auditory_v4_archive(archive)
    finally:
        guala.strict_shutdown(timeout=30.0)


def test_aggregate_teaching_boundary_is_checked_before_write(monkeypatch):
    _disable_background_substrate(monkeypatch)
    guala = Guala()
    try:
        monkeypatch.setattr(engine_module, "TEACHING_STATE_MAX_BYTES", 1)
        with pytest.raises(RuntimeError, match="aggregate byte boundary"):
            guala._bounded_teaching_envelope()
    finally:
        guala.strict_shutdown(timeout=30.0)
