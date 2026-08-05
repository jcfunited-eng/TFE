"""Decisive contracts for world-owned material senses at the W1 seam."""

from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
    build_coupled_six_sense_full_field,
    material_receptor_substreams,
)


WORLD_KEY = b"runtime-independent-material-world-key"
EVIDENCE_KEY = b"runtime-independent-material-evidence-key"
EMISSION_KEY = b"runtime-independent-material-emission-key"


def _owner(committed=None):
    return ExactCausalExperienceOwner(
        on_settlement=(
            committed.append
            if committed is not None
            else lambda _settlement: None
        ),
        log_event=lambda *_args, **_kwargs: None,
    )


def _authority(world, owner=None):
    return W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=EVIDENCE_KEY,
        world_authority=world,
        causal_owner=owner or _owner(),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=(
                    b"runtime-independent-material-continuity-key"
                ),
                physical_authority_key=EVIDENCE_KEY,
            )
        ),
    )


def _move(world):
    before = world.observation_snapshot()
    receipt = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_000, 1_200, 0), 0),
                200_000,
            )
        ),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    assert receipt.disposition == "applied"
    return receipt


def _states(settlement):
    return {
        interpretation.sense: interpretation.state
        for interpretation in settlement.interpretations
    }


def test_action_mount_observes_material_zero_and_marks_sound_unavailable():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    execution = _move(world)
    committed = []
    authority = _authority(world, _owner(committed))

    result = authority.mount_action_outcome(execution)

    assert result.state is W1EvidenceState.OBSERVED
    assert result.binaural_pcm is None
    assert result.causal_settlement is not None
    assert committed == [result.causal_settlement]
    assert _states(result.causal_settlement) == {
        "sight": "observed",
        "sound": "sensor_unavailable",
        "touch": "observed",
        "smell": "observed",
        "taste": "observed",
        "body": "observed",
    }
    assert result.evidence_receipt is not None
    assert result.evidence_receipt.source_time_start == Fraction(0)
    assert result.evidence_receipt.source_time_end == Fraction(1, 5)

    native = material_receptor_substreams(
        world_authority=world,
        before=execution.before,
        after=execution.after,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
    )
    assert all(
        value == 0.0
        for substream in native[next(
            sense for sense in native if sense.value == "touch"
        )]
        for value in substream.normalized_signal
    )
    assert all(
        value == 0.0
        for substream in native[next(
            sense for sense in native if sense.value == "taste"
        )]
        for value in substream.normalized_signal
    )


def test_material_mount_preserves_every_full_field_and_no_identity():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    execution = _move(world)
    result = _authority(world).mount_action_outcome(execution)
    settlement = result.causal_settlement
    assert settlement is not None

    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for interpretation in settlement.interpretations
        if interpretation.state == "observed"
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    )
    material = tuple(
        substream
        for interpretation in settlement.interpretations
        if interpretation.sense in {"touch", "smell", "taste"}
        for substream in interpretation.substreams
    )
    assert len(material) == 6 + 8 + 5
    assert all(
        "W1-object" not in substream.sensor_id
        and "W1-object" not in substream.substream_id
        and "profile" not in substream.sensor_id
        and "profile" not in substream.substream_id
        for substream in material
    )
    assert result.binaural_pcm is None
    assert all(
        not isinstance(value, bytes)
        for interpretation in settlement.interpretations
        for substream in interpretation.substreams
        for value in (
            substream.sensor_id,
            substream.substream_id,
            substream.source_sample_commitment_sha256,
        )
    )


def test_optional_sound_requires_both_authenticated_ears():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    execution = _move(world)
    with pytest.raises(
        ValueError,
        match="both ears or remain unavailable",
    ):
        build_coupled_six_sense_full_field(
            assembly_id="one-ear-is-not-an-observation",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1, 5),
            world_authority=world,
            execution_receipt=execution,
            left_sound=object(),
        )


def test_material_action_reservation_keeps_atomic_commit_semantics():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    execution = _move(world)
    committed = []
    owner = _owner(committed)
    authority = _authority(world, owner)
    episode = authority.begin_atomic_episode()

    prepared = authority.mount_action_outcome(
        execution,
        commit=False,
        reserve=True,
    )
    assert committed == []
    assert owner.status()["prepared_reservation"] == 1

    authority.commit_prepared_mount(prepared)
    undo = authority.commit_atomic_episode(episode)
    assert committed == []
    assert owner.status()["prepared_reservation"] == 0
    assert owner.status()["settled"] == 1
    assert set(owner.status()["tracked_senses"]) == {
        "body",
        "sight",
        "smell",
        "taste",
        "touch",
    }

    authority.rollback_committed_atomic_episode(undo)
    assert committed == []
    assert owner.status()["settled"] == 0
    assert owner.status()["tracked_senses"] == []
