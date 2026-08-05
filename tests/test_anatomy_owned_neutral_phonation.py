from __future__ import annotations

import base64
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    PickCommand,
    encode_command,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.physical_inquiry_test_support import RUNTIME_KEY
from tests.test_anonymous_passive_window import _settlement
from tests.test_articulatory_consequence_closure import _vocal_pcm


def _runtime(monkeypatch: pytest.MonkeyPatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    return Guala()


def _seed_physical_experience(
    engine: Guala,
    *,
    receptors: tuple[str, ...],
    occurrence: str,
) -> None:
    world = engine._embodiment_world
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=world.port_id,
        command_payload=encode_command(PickCommand(
            object_id="W1-object-1",
            duration_microseconds=100_000,
        )),
        causal_intent_receipt_sha256=hashlib.sha256(
            occurrence.encode("ascii")
        ).hexdigest(),
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    mount = engine._w1_physical_evidence.mount_action_outcome(
        execution,
        commit=True,
    )
    custody = engine._settled_prediction_custody(
        mount,
        world_execution=execution,
    )
    engine._admit_settled_embodiment_thing(custody, execution)
    settlement = _settlement(
        occurrence,
        receptors=receptors,
        audiovisual=True,
    )
    passive_owner = engine._passive_whole_organism_thing_learning
    engine._passive_whole_organism_thing_learning = None
    try:
        result = engine.admit_anonymous_causal_inquiry_window(
            settlement=settlement,
            window_id=occurrence,
        )
    finally:
        engine._passive_whole_organism_thing_learning = passive_owner
    assert result["decision_state"] == "silent"
    assert (
        result["decision_reason"]
        == "awaiting_explicit_tutor_authorization"
    )


def _learn_restore_and_resynthesize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    state_dir: Path,
    receptors: tuple[str, ...],
    occurrence: str,
    nonce: bytes,
) -> dict[str, object]:
    live = _runtime(monkeypatch)
    request_one_restored = None
    learned_restored = None
    try:
        _seed_physical_experience(
            live,
            receptors=receptors,
            occurrence=occurrence,
        )
        need = live._causal_inquiry_owner.active_need
        assert need is not None
        witness = next(
            item
            for item in live._causal_inquiry_owner.witnesses
            if item.authority_receipt_sha256
            == need.witness_receipt_sha256
        )
        sound_roots = tuple(
            root
            for root in witness.full_field_roots
            if root.sense == "sound"
        )
        assert len(sound_roots) == len(receptors)
        for root in sound_roots:
            evidence = json.loads(root.full_evidence_json)
            assert all(
                tuple(name for name, _value in item["fields"])
                == DSF_FIELD_ORDER
                for item in evidence["field_tuples"]
            )
        efferent = live._embodied_vocal_body.capture_inquiry_efferent(
            need=need,
            witness=witness,
        )
        field_path = live._embodied_vocal_body._experience_field_path(
            efferent
        )
        live._embodied_vocal_body.discard_inquiry_efferent(efferent)
        assert field_path
        assert all(
            len(values) == len(DSF_FIELD_ORDER)
            for _start, _end, values in field_path
        )

        live.save_full_state(state_dir, publish_generation=False)
        request_one = live.create_body_owned_vocal_request_one(
            state_dir=state_dir,
        )
        pending = live._pending_body_owned_vocal_consequence.pending
        assert pending is not None
        program = pending.program
        neutral = tuple(
            actuator.neutral_coordinate
            for actuator in live._embodied_vocal_body.anatomy.actuators[1:]
        )
        assert len(program.body_trajectory) == len(field_path) + 2
        assert (
            program.body_trajectory[0].section_area_mm2
            == program.body_trajectory[-1].section_area_mm2
            == neutral
        )
        assert any(
            interval.section_area_mm2 != neutral
            for interval in program.body_trajectory[1:-1]
        )
        assert len({
            pending.candidate_w1_mount_receipt_sha256,
            pending.candidate_causal_settlement_receipt_sha256,
            pending.candidate_binaural_l5_receipt_sha256,
            pending.candidate_receptor_settlement_receipt_sha256,
            pending.candidate_recurrent_q_receipt_sha256,
        }) == 5
        observation = (
            live._latest_body_owned_transient_vocal_observation
        )
        assert observation is not None
        assert (
            observation["motor_derivation"]
            == "authenticated_full_field_local_antagonist_trajectory"
        )
        assert observation["motor_derived_from_witness_field"] is True
        assert observation["witness_full_dsf_field_preserved"] is True
        assert observation["imitation_authority"] is False
        assert observation["intelligibility_authority"] is False
        assert observation["meaning_authority"] is False
        assert observation["word_authority"] is False

        request_one_restored = _runtime(monkeypatch)
        request_one_restored.load_full_state(state_dir)
        restored_pending = (
            request_one_restored
            ._pending_body_owned_vocal_consequence.pending
        )
        assert restored_pending is not None
        assert restored_pending.program == program
        assert (
            restored_pending.candidate_pressure_sha256
            == request_one.pressure_sha256
        )
        learned = (
            request_one_restored.create_body_owned_vocal_request_two(
                client_capability=request_one.client_capability,
                nonce=nonce,
                companion_pcm_s16le=_vocal_pcm(),
                state_dir=state_dir,
            )
        )
        assert learned.program_id == program.program_id
        assert learned.inquiry_resolved is True
        assert learned.autonomous_reuse_available is True

        learned_restored = _runtime(monkeypatch)
        learned_restored.load_full_state(state_dir)
        retained = tuple(
            item
            for item in (
                learned_restored._articulatory_self_vocal_owner.programs
            )
            if item.program_id == learned.program_id
        )
        assert retained == (program,)
        synthesis = (
            learned_restored._articulatory_self_vocal_owner.synthesize(
                program_id=program.program_id,
                source_time_start=Fraction(100),
            )
        )
        assert (
            synthesis.receipt.radiated_pcm_sha256
            == request_one.pressure_sha256
        )
        assert (
            hashlib.sha256(synthesis.radiated_pcm_s16le).hexdigest()
            == request_one.pressure_sha256
        )
        assert (
            learned_restored._experience_grown_vocal_causal_relation
            .status()["relation_count"]
            == 1
        )
        assert (
            learned_restored._experience_grown_vocal_causal_relation
            .status()["motor_derived_from_witness_field"]
            is True
        )
        assert (
            learned_restored._articulatory_self_vocal_owner.status()[
                "retained_pcm_bytes"
            ]
            == 0
        )
        assert (
            learned_restored._embodied_vocal_body.status()[
                "retained_pcm_bytes"
            ]
            == 0
        )
        for retained_file in state_dir.rglob("*"):
            if not retained_file.is_file():
                continue
            retained_bytes = retained_file.read_bytes()
            assert request_one.pcm_s16le not in retained_bytes
            assert (
                base64.b64encode(request_one.pcm_s16le)
                not in retained_bytes
            )
            assert _vocal_pcm() not in retained_bytes
            assert base64.b64encode(_vocal_pcm()) not in retained_bytes
        return {
            "field_path": field_path,
            "pressure_sha256": request_one.pressure_sha256,
            "program": program,
            "radiated_pcm_s16le": synthesis.radiated_pcm_s16le,
        }
    finally:
        if learned_restored is not None:
            learned_restored.shutdown()
        if request_one_restored is not None:
            request_one_restored.shutdown()
        live.shutdown()


def test_two_experiences_grow_distinct_cold_restorable_articulations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mono = _learn_restore_and_resynthesize(
        monkeypatch,
        state_dir=tmp_path / "mono",
        receptors=("microphone",),
        occurrence="experience-grown-mono",
        nonce=b"\x51" * 32,
    )
    bilateral = _learn_restore_and_resynthesize(
        monkeypatch,
        state_dir=tmp_path / "bilateral",
        receptors=("left-ear", "right-ear"),
        occurrence="experience-grown-bilateral",
        nonce=b"\x52" * 32,
    )

    assert mono["field_path"] != bilateral["field_path"]
    assert mono["program"] != bilateral["program"]
    assert (
        mono["program"].program_id
        != bilateral["program"].program_id
    )
    assert (
        mono["pressure_sha256"]
        != bilateral["pressure_sha256"]
    )
    assert (
        mono["radiated_pcm_s16le"]
        != bilateral["radiated_pcm_s16le"]
    )
