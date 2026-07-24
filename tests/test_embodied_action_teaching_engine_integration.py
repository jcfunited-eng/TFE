from __future__ import annotations

import base64
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from dsf_ai_service.substrate.auditory_pcm_stream import pcm_s16le_wav
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _configure(monkeypatch, key: str) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)


def _move_payload(y_mm: int) -> bytes:
    return encode_command(MoveCommand(PoseMM(
        PositionMM(1000, y_mm, 0),
        90_000,
    )))


def _snapshots(guala: Guala):
    return (
        guala._embodiment_world.encoded_snapshot(),
        guala._causal_action_cycle.encoded_snapshot(),
        guala._embodied_action_teaching.encoded_snapshot(),
        guala._full_field_prediction.encoded_snapshot(),
    )


def _enable_test_publisher(guala: Guala) -> None:
    guala._authoritative_hot_generation_publisher = lambda **_values: None


def test_durable_demonstration_executes_once_and_closes_exact_outcome(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "engine-guided-demonstration-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        saves = []
        guala.save_hot_state = lambda state_dir: saves.append(state_dir)
        result = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="engine-guided-demonstration-0001",
            port_id=PORT_ID,
            command_payload=_move_payload(1400),
            state_dir="unused",
        )

        assert result["world_revision_before"] == 0
        assert result["world_revision_after"] == 1
        assert len(result["closure_receipt_sha256"]) == 64
        assert saves == ["unused"]
        assert guala._embodied_action_teaching.status()["demonstrations"] == 1
        assert len(guala._embodiment_world.recent_applied_receipts()) == 1
        cycle = guala._causal_action_cycle.status()
        assert cycle["bindings"] == 1
        assert cycle["closures"] == 1
        assert cycle["intents"] == 0
        assert cycle["executions"] == 0
        assert cycle["outcomes"] == 0
        relation = guala._causal_action_cycle.verified_relation_evidence()[0]
        guided = (
            guala._embodied_action_teaching
            .verified_guided_relation_evidence()
        )
        assert guided == (relation,)
        assert relation.teacher_schema == (
            "guala.causal_action_cycle.teacher.v2"
        )
        assert relation.teacher_source == "joe"
        assert relation.teaching_evidence_receipt_sha256 == (
            result["demonstration_receipt_sha256"]
        )
        assert relation.latest_closure_receipt_sha256 == (
            result["closure_receipt_sha256"]
        )
        assert relation.outcome_witness.settlement_receipt_sha256
    finally:
        guala.shutdown()


@pytest.mark.parametrize(
    ("port_id", "payload", "message"),
    (
        (
            SECOND_BODY_PORT_ID,
            _move_payload(1400),
            "self-body port",
        ),
        (
            PORT_ID,
            _move_payload(4900),
            "guided W1 execution was rejected",
        ),
    ),
)
def test_other_body_and_rejected_geometry_teach_nothing(
    monkeypatch,
    port_id,
    payload,
    message,
) -> None:
    _configure(monkeypatch, "engine-guided-rejection-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        guala.save_hot_state = lambda _state_dir: pytest.fail(
            "rejected demonstration reached persistence"
        )
        before = _snapshots(guala)
        with pytest.raises(ValueError, match=message):
            guala.durably_demonstrate_embodied_action(
                tutor_id="joe",
                nonce="engine-guided-demonstration-0002",
                port_id=port_id,
                command_payload=payload,
                state_dir="unused",
            )
        assert _snapshots(guala) == before
        assert guala._causal_action_cycle.status()["closures"] == 0
    finally:
        guala.shutdown()


def test_replay_and_save_failure_restore_all_authorities(monkeypatch) -> None:
    _configure(monkeypatch, "engine-guided-rollback-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        guala.save_hot_state = lambda _state_dir: None
        values = {
            "tutor_id": "joe",
            "nonce": "engine-guided-demonstration-0003",
            "port_id": PORT_ID,
            "command_payload": _move_payload(1400),
            "state_dir": "unused",
        }
        guala.durably_demonstrate_embodied_action(**values)
        learned = _snapshots(guala)
        with pytest.raises(ValueError, match="nonce was already used"):
            guala.durably_demonstrate_embodied_action(**values)
        assert _snapshots(guala) == learned
        assert len(guala._embodiment_world.recent_applied_receipts()) == 1
        assert guala._causal_action_cycle.status()["closures"] == 1

        guala.save_hot_state = lambda _state_dir: (_ for _ in ()).throw(
            RuntimeError("injected save failure")
        )
        with pytest.raises(RuntimeError, match="injected save failure"):
            guala.durably_demonstrate_embodied_action(
                tutor_id="wc",
                nonce="engine-guided-demonstration-0004",
                port_id=PORT_ID,
                command_payload=_move_payload(1800),
                state_dir="unused",
            )
        assert _snapshots(guala) == learned
        assert len(guala._embodiment_world.recent_applied_receipts()) == 1
        assert guala._causal_action_cycle.status()["closures"] == 1
    finally:
        guala.shutdown()


def test_teacher_review_durably_revokes_one_observed_embodied_binding(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "engine-guided-review-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        saves = []
        guala.save_hot_state = lambda state_dir: saves.append(state_dir)
        trigger = (
            guala._w1_physical_evidence
            .mount_current_observation(commit=False)
            .causal_settlement
        )
        taught = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="engine-guided-review-demo-0001",
            port_id=PORT_ID,
            command_payload=_move_payload(1400),
            state_dir="unused",
        )

        reviewed = guala.durably_review_causal_action_binding(
            binding_id=taught["binding_id"],
            decision="revoke",
            source="joe",
            nonce="engine-guided-review-feedback-0001",
            state_dir="unused",
        )

        assert reviewed == {
            "binding_id": taught["binding_id"],
            "decision": "revoke",
            "ok": True,
            "resulting_binding_status": "revoked",
            "status": "applied",
        }
        assert saves == ["unused", "unused"]
        evidence = guala._causal_action_cycle.verified_relation_evidence()
        assert len(evidence) == 1
        assert evidence[0].status == "revoked"
        assert guala._causal_action_cycle.select(trigger).status == "unknown"
    finally:
        guala.shutdown()


def test_teacher_review_save_failure_restores_binding(monkeypatch) -> None:
    _configure(monkeypatch, "engine-guided-review-rollback-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        guala.save_hot_state = lambda _state_dir: None
        taught = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="engine-guided-review-rollback-demo-0001",
            port_id=PORT_ID,
            command_payload=_move_payload(1400),
            state_dir="unused",
        )
        before = guala._causal_action_cycle.encoded_snapshot()
        guala.save_hot_state = lambda _state_dir: (_ for _ in ()).throw(
            RuntimeError("injected review save failure")
        )

        with pytest.raises(
            RuntimeError, match="injected review save failure"
        ):
            guala.durably_review_causal_action_binding(
                binding_id=taught["binding_id"],
                decision="revoke",
                source="joe",
                nonce="engine-guided-review-rollback-feedback-0001",
                state_dir="unused",
            )

        assert guala._causal_action_cycle.encoded_snapshot() == before
        evidence = guala._causal_action_cycle.verified_relation_evidence()
        assert len(evidence) == 1
        assert evidence[0].status == "provisional"
    finally:
        guala.shutdown()


def test_tampered_post_sensory_proof_rolls_back_without_closure(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "engine-guided-tamper-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        guala.save_hot_state = lambda _state_dir: pytest.fail(
            "tampered demonstration reached persistence"
        )
        before = _snapshots(guala)
        authority = guala._w1_physical_evidence
        mount_action_outcome = authority.mount_action_outcome

        def tamper_post(execution_receipt, **values):
            outcome = mount_action_outcome(execution_receipt, **values)
            return replace(
                outcome,
                evidence_receipt=replace(
                    outcome.evidence_receipt,
                    world_observation_after_receipt_sha256="0" * 64,
                ),
            )

        authority.mount_action_outcome = tamper_post
        with pytest.raises(ValueError, match="W1 evidence HMAC changed"):
            guala.durably_demonstrate_embodied_action(
                tutor_id="joe",
                nonce="engine-guided-demonstration-0006",
                port_id=PORT_ID,
                command_payload=_move_payload(1400),
                state_dir="unused",
            )
        assert _snapshots(guala) == before
        assert guala._causal_action_cycle.status()["closures"] == 0
        assert len(guala._embodiment_world.recent_applied_receipts()) == 0
    finally:
        guala.shutdown()


def test_guided_world_binding_and_closure_restore_together(
    monkeypatch,
    tmp_path,
) -> None:
    _configure(monkeypatch, "engine-guided-persistence-key")
    writer = Guala()
    restored = None
    try:
        _enable_test_publisher(writer)
        writer.save_full_state(str(tmp_path))
        result = writer.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="engine-guided-demonstration-0005",
            port_id=PORT_ID,
            command_payload=_move_payload(1400),
            state_dir=str(tmp_path),
        )
        payload = writer._teaching_persistence_payload()
        writer._validate_teaching_payload(payload, writer.tick)
        assert payload["embodied_action_teaching"] is not None
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))
        assert restored._load_successful, restored._load_errors
        assert restored._embodiment_world.observation_snapshot().revision == 1
        assert restored._embodied_action_teaching.status()[
            "demonstrations"
        ] == 1
        relation = restored._causal_action_cycle \
            .verified_relation_evidence()[0]
        assert relation.binding_id == result["binding_id"]
        assert relation.latest_closure_receipt_sha256 == (
            result["closure_receipt_sha256"]
        )
        assert restored._causal_action_cycle.status()["closures"] == 1
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()


def test_typed_api_is_key_protected_and_transports_canonical_w1(
    monkeypatch,
) -> None:
    import dsf_ai_service.app as app_module

    calls = []

    class FakeGuala:
        def durably_demonstrate_embodied_action(self, **values):
            calls.append(values)
            return {"binding_id": "b" * 64}

        def durably_review_causal_action_binding(self, **values):
            calls.append(values)
            return {
                "binding_id": values["binding_id"],
                "decision": values["decision"],
                "ok": True,
                "resulting_binding_status": "revoked",
                "status": "applied",
            }

        def experience_companion_vocal_episode(
            self, pcm_s16le, *, state_dir
        ):
            calls.append({
                "pcm_s16le": pcm_s16le,
                "state_dir": state_dir,
            })
            return {
                "block_count": 1,
                "schema": "guala.w1.companion_vocal_episode.v1",
            }

    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "guided-api-key")
    monkeypatch.setattr(app_module, "_guala", FakeGuala())
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    request = {
        "tutor_id": "joe",
        "nonce": "api-guided-demonstration-0001",
        "port_id": PORT_ID,
        "operation": "move",
        "target_pose": {
            "position": {"x_mm": 1000, "y_mm": 1400, "z_mm": 0},
            "heading_millidegrees": 90000,
        },
    }
    client = TestClient(app_module.app)
    assert client.post(
        "/api/v1/embodiment/demonstrate", json=request
    ).status_code == 401
    accepted = client.post(
        "/api/v1/embodiment/demonstrate",
        json=request,
        headers={"X-API-Key": "guided-api-key"},
    )
    assert accepted.status_code == 200
    assert accepted.json() == {"binding_id": "b" * 64}
    assert len(calls) == 1
    assert calls[0]["port_id"] == PORT_ID
    assert calls[0]["command_payload"] == _move_payload(1400)
    assert not isinstance(calls[0]["command_payload"], str)
    review = {
        "binding_id": "b" * 64,
        "decision": "revoke",
        "source": "joe",
        "nonce": "api-guided-review-0001",
    }
    assert client.post(
        "/api/v1/causal-action/review-binding", json=review
    ).status_code == 401
    reviewed = client.post(
        "/api/v1/causal-action/review-binding",
        json=review,
        headers={"X-API-Key": "guided-api-key"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["resulting_binding_status"] == "revoked"
    assert calls[1]["binding_id"] == "b" * 64
    assert calls[1]["nonce"] == "api-guided-review-0001"
    pcm = b"\x00\x00" * 1024
    import dsf_ai_service.substrate_runner as runner
    monkeypatch.setattr(
        runner,
        "_webm_to_wav_bytes",
        lambda _encoded: pcm_s16le_wav(pcm),
    )
    files = {"file": ("voice.mp3", b"encoded-audio", "audio/mpeg")}
    assert client.post(
        "/api/v1/embodiment/companion-vocalize",
        files=files,
        data={"tutor_id": "joe"},
    ).status_code == 401
    vocalized = client.post(
        "/api/v1/embodiment/companion-vocalize",
        files=files,
        data={"tutor_id": "joe"},
        headers={"X-API-Key": "guided-api-key"},
    )
    assert vocalized.status_code == 200
    assert vocalized.json()["block_count"] == 1
    assert calls[2]["pcm_s16le"] == pcm


def test_remote_handler_rejects_noncanonical_command_transport(
    monkeypatch,
) -> None:
    import dsf_ai_service.substrate_runner as runner

    calls = []
    monkeypatch.setattr(
        runner,
        "_guala",
        type("FakeGuala", (), {
            "durably_demonstrate_embodied_action": (
                lambda self, **values: calls.append(values) or {"ok": True}
            )
        })(),
    )
    payload = _move_payload(1400)
    accepted = runner.handle_embodied_action_demonstrate({
        "tutor_id": "joe",
        "nonce": "runner-guided-demonstration-0001",
        "port_id": PORT_ID,
        "command_payload_base64": base64.b64encode(payload).decode("ascii"),
    })
    assert accepted == {"ok": True}
    assert calls[0]["command_payload"] == payload
    assert runner.handle_embodied_action_demonstrate({
        "command_payload_base64": "not base64",
    })["error"]
    assert len(calls) == 1
