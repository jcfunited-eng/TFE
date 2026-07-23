from __future__ import annotations

import json
import struct
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    MAX_EMITTED_PCM_SAMPLES,
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
)


WORLD_KEY = b"world-authority-key-for-w1-tests"
EVIDENCE_KEY = b"evidence-authority-key-for-w1-tests"
INTENT_RECEIPT = "1" * 64
EMITTER_PORT = "w1.external-emitter"


def _pcm(sample_count: int = 1_024) -> bytes:
    samples = tuple(
        12_000 if index % 16 < 8 else -12_000
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *samples)


def _world(
    *,
    external_position: PositionMM = PositionMM(3_500, 2_500, 0),
) -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(external_position, 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )


def _owner(on_settlement=None) -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=on_settlement or (lambda _settlement: None),
        log_event=lambda *_args, **_kwargs: None,
    )


def _execution(world: EmbodimentWorldAuthority):
    before = world.observation_snapshot()
    receipt = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PickCommand("teaching-object")),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert receipt.disposition == "applied"
    return receipt


def _authority(world, owner=None):
    return W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=EVIDENCE_KEY,
        world_authority=world,
        causal_owner=owner or _owner(),
    )


def test_mount_retains_full_fields_but_no_perceptual_identity_or_raw_media():
    accepted = []
    world = _world()
    authority = _authority(world, _owner(accepted.append))
    epoch = authority.open_epoch()

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=_execution(world),
        emitter_port_id=EMITTER_PORT,
        emitted_pcm_s16le=_pcm(),
    )

    assert result.state is W1EvidenceState.OBSERVED
    result.verify(EVIDENCE_KEY)
    assert len(accepted) == 1
    assert result.binaural_pcm is not None
    assert (
        result.binaural_pcm.left_pcm_s16le
        != result.binaural_pcm.right_pcm_s16le
    )
    settlement = result.causal_settlement
    assert settlement is not None
    assert settlement.source_tags == ()
    assert settlement.routing_chis == ()
    observed = {
        item.sense: item
        for item in settlement.interpretations
        if item.state == "observed"
    }
    assert set(observed) == {"sight", "sound"}
    assert len(observed["sight"].substreams) == 4
    assert len(observed["sound"].substreams) == 2
    for interpretation in settlement.interpretations:
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER

    persisted = json.dumps(result.persistence_record(), sort_keys=True)
    for forbidden in (
        "external-body",
        EMITTER_PORT,
        "guala-body-1",
        "teaching-object",
        "pcm_s16le",
    ):
        assert forbidden not in persisted
    assert authority.status()["retained_raw_media_bytes"] == 0


def test_tampered_world_receipt_is_rejected_before_mounting():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    tampered = replace(execution, authority_hmac_sha256="0" * 64)

    with pytest.raises(ValueError, match="execution HMAC"):
        authority.mount(
            epoch_token=epoch,
            sequence=0,
            execution_receipt=tampered,
            emitter_port_id=EMITTER_PORT,
            emitted_pcm_s16le=_pcm(),
        )

    assert authority.status()["active_epochs"] == 1
    assert authority.status()["retained_raw_media_bytes"] == 0


def test_sequence_gap_and_process_restart_fail_unknown_and_close_state():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    gap = authority.mount(
        epoch_token=epoch,
        sequence=1,
        execution_receipt=execution,
        emitter_port_id=EMITTER_PORT,
        emitted_pcm_s16le=_pcm(),
    )
    assert gap.state is W1EvidenceState.UNKNOWN
    assert gap.reason == "audiovisual_sequence_gap_closed_the_epoch"
    assert authority.status()["active_epochs"] == 0

    replacement = _authority(world)
    restarted = replacement.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        emitter_port_id=EMITTER_PORT,
        emitted_pcm_s16le=_pcm(),
    )
    assert restarted.state is W1EvidenceState.UNKNOWN
    assert restarted.reason == "audiovisual_epoch_unknown_after_gap_or_restart"


def test_symmetric_two_ear_field_is_explicitly_ambiguous():
    world = _world(external_position=PositionMM(3_500, 1_000, 0))
    authority = _authority(world)

    result = authority.mount(
        epoch_token=authority.open_epoch(),
        sequence=0,
        execution_receipt=_execution(world),
        emitter_port_id=EMITTER_PORT,
        emitted_pcm_s16le=_pcm(),
    )

    assert result.state is W1EvidenceState.AMBIGUOUS
    assert result.reason == "two_ear_field_is_spatially_symmetric"
    assert result.binaural_pcm is not None
    assert (
        result.binaural_pcm.left_pcm_s16le
        == result.binaural_pcm.right_pcm_s16le
    )


def test_anonymous_visual_order_crossing_is_explicitly_ambiguous():
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        max_bodies=3,
        bodies=(
            EmbodiedBody(
                "body-a",
                PoseMM(PositionMM(2_000, 4_000, 0), 0),
                radius_mm=100,
                reach_mm=500,
            ),
            EmbodiedBody(
                "body-b",
                PoseMM(PositionMM(4_000, 2_000, 0), 0),
                radius_mm=100,
                reach_mm=500,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort("w1.body-a", "body-a"),
            EmbodimentPort("w1.body-b", "body-b"),
        ),
        initial_objects=(
            EmbodiedObject(
                "remote-object",
                radius_mm=50,
                mass_grams=100,
                position=PositionMM(4_500, 500, 0),
            ),
        ),
    )
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id="w1.body-a",
        command_payload=encode_command(MoveCommand(
            PoseMM(PositionMM(4_500, 4_000, 0), 0)
        )),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    authority = _authority(world)

    result = authority.mount(
        epoch_token=authority.open_epoch(),
        sequence=0,
        execution_receipt=execution,
        emitter_port_id="w1.body-b",
        emitted_pcm_s16le=_pcm(),
    )

    assert result.state is W1EvidenceState.AMBIGUOUS
    assert result.reason == "anonymous_visual_order_crossed"
    assert result.causal_settlement is not None


def test_resource_bounds_and_transaction_rollback_preserve_epoch():
    failures = [True]

    def fail_once(_settlement):
        if failures:
            failures.pop()
            raise RuntimeError("downstream settlement rejected")

    owner = _owner(fail_once)
    world = _world()
    authority = _authority(world, owner)
    epoch = authority.open_epoch()
    execution = _execution(world)

    with pytest.raises(RuntimeError, match="downstream settlement rejected"):
        authority.mount(
            epoch_token=epoch,
            sequence=0,
            execution_receipt=execution,
            emitter_port_id=EMITTER_PORT,
            emitted_pcm_s16le=_pcm(),
        )
    assert owner.status()["prepared_reservation"] == 0

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        emitter_port_id=EMITTER_PORT,
        emitted_pcm_s16le=_pcm(),
    )
    assert result.state is W1EvidenceState.OBSERVED

    second = authority.open_epoch()
    with pytest.raises(RuntimeError, match="epoch capacity"):
        authority.open_epoch()
    assert authority.close_epoch(second)

    with pytest.raises(ValueError, match="sample boundary"):
        authority.mount(
            epoch_token=epoch,
            sequence=1,
            execution_receipt=execution,
            emitter_port_id=EMITTER_PORT,
            emitted_pcm_s16le=_pcm(MAX_EMITTED_PCM_SAMPLES + 1),
        )
    assert authority.status()["retained_raw_media_bytes"] == 0
