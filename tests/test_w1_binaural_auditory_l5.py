from __future__ import annotations

import json
import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    _sound_inputs,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)


def _tone(frequency_hz: int) -> bytes:
    values = tuple(
        int(12_000 * math.sin(
            2 * math.pi * frequency_hz * index / 16_000
        ))
        for index in range(1024)
    )
    return struct.pack("<1024h", *values)


def _owner() -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _world() -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=b"w" * 32,
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                250,
                800,
            ),
            EmbodiedBody(
                "companion-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                200,
                600,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "companion-body"),
        ),
    )


def _authorities():
    world = _world()
    causal = _owner()
    auditory_l5 = W1BinauralAuditoryL5Owner(
        max_transitions=4,
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=b"p" * 32,
        world_authority=world,
        causal_owner=causal,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=b"a" * 32,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=auditory_l5,
    )
    companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"c" * 32,
        world_authority=world,
        physical_authority=physical,
    )
    return world, causal, auditory_l5, physical, companion


def _sound_settlement(
    *,
    left_hz: int,
    right_hz: int | None,
    routing_chis: tuple[int, ...] = (),
    source_tags: tuple[str, ...] = (),
):
    start = Fraction(0)
    left = _sound_inputs(
        ear="left",
        topology_index=0,
        pcm=_tone(left_hz),
        source_time_start=start,
    )
    sound = left
    if right_hz is not None:
        right = _sound_inputs(
            ear="right",
            topology_index=len(left),
            pcm=_tone(right_hz),
            source_time_start=start,
        )
        sound = (*left, *right)
    built = build_six_sense_full_field(
        assembly_id="binaural-l5-test-assembly",
        source_time_start=start,
        source_time_end=Fraction(1024, 16_000),
        observed_substreams={PhysicalSense.SOUND: sound},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return _owner().settle(
        built,
        routing_chis=routing_chis,
        source_tags=source_tags,
    )


def test_exact_w1_mount_commits_one_bounded_two_ear_l5_experience():
    _world_authority, causal, auditory_l5, physical, companion = _authorities()
    prepared = companion.prepare(pcm_s16le=_tone(440))
    experience = prepared.physical_mount.binaural_auditory_l5

    assert experience is not None
    experience.verify()
    assert tuple(ear.ear_id for ear in experience.ears) == ("left", "right")
    assert all(len(ear.channels) == 16 for ear in experience.ears)
    assert auditory_l5.status()["prepared"] == 1
    assert causal.status()["prepared_reservation"] == 1

    companion.commit(prepared)

    assert auditory_l5.latest == experience
    assert auditory_l5.status()["settled"] == 1
    assert auditory_l5.status()["prepared"] == 0
    assert physical.status()["active_epochs"] == 0

    persisted = json.dumps(experience.persistence_record(), sort_keys=True)
    structural = json.dumps(experience.structural_payload(), sort_keys=True)
    authority = json.dumps(experience.authority_payload(), sort_keys=True)
    assert "pcm_s16le" not in persisted
    assert "receipt_registry" not in persisted
    assert "source_sample_commitment_sha256" not in structural
    assert "source_sample_commitment_sha256" in authority
    assert len(persisted.encode("utf-8")) <= auditory_l5.status()[
        "max_authority_bytes"
    ]


def test_mono_settlement_is_not_adapted_or_duplicated_into_two_ears():
    settlement = _sound_settlement(left_hz=440, right_hz=None)
    owner = W1BinauralAuditoryL5Owner()

    with pytest.raises(ReceiptError, match="exactly 64"):
        owner.prepare(settlement)

    assert owner.status()["prepared"] == 0
    assert owner.status()["settled"] == 0


def test_routing_chi_and_source_tags_cannot_become_auditory_identity():
    plain = _sound_settlement(
        left_hz=440,
        right_hz=660,
    )
    routed = _sound_settlement(
        left_hz=440,
        right_hz=660,
        routing_chis=(3, 9, 27),
        source_tags=("control-only",),
    )
    first_owner = W1BinauralAuditoryL5Owner()
    second_owner = W1BinauralAuditoryL5Owner()
    first = first_owner.prepare(plain)
    second = second_owner.prepare(routed)

    assert plain.authority_receipt_sha256 != routed.authority_receipt_sha256
    assert first.structural_fingerprint == second.structural_fingerprint
    assert first.experience_id == second.experience_id
    assert first.authority_receipt_sha256 != second.authority_receipt_sha256

    first_owner.discard_prepared(first)
    second_owner.discard_prepared(second)


def test_each_ear_contributes_independently_to_full_field_identity():
    balanced = _sound_settlement(left_hz=440, right_hz=440)
    changed_right = _sound_settlement(left_hz=440, right_hz=1_760)
    first_owner = W1BinauralAuditoryL5Owner()
    second_owner = W1BinauralAuditoryL5Owner()
    first = first_owner.prepare(balanced)
    second = second_owner.prepare(changed_right)

    assert first.structural_fingerprint != second.structural_fingerprint
    first_owner.discard_prepared(first)
    second_owner.discard_prepared(second)


def test_altered_committed_field_fails_before_l5_owner_mutation():
    settlement = _sound_settlement(left_hz=440, right_hz=660)
    sound_index = next(
        index
        for index, value in enumerate(settlement.interpretations)
        if value.sense == "sound"
    )
    sound = settlement.interpretations[sound_index]
    component = sound.substreams[0]
    field_tuple = component.field_tuples[0]
    changed_fields = tuple(field_tuple.fields)
    changed_fields = (
        (changed_fields[0][0], changed_fields[0][1] + Fraction(1, 1024)),
        *changed_fields[1:],
    )
    changed_component = replace(
        component,
        field_tuples=(
            replace(field_tuple, fields=changed_fields),
            *component.field_tuples[1:],
        ),
    )
    changed_sound = replace(
        sound,
        substreams=(changed_component, *sound.substreams[1:]),
    )
    changed = replace(
        settlement,
        interpretations=(
            *settlement.interpretations[:sound_index],
            changed_sound,
            *settlement.interpretations[sound_index + 1:],
        ),
    )
    owner = W1BinauralAuditoryL5Owner()

    with pytest.raises(ReceiptError):
        owner.prepare(changed)

    assert owner.status()["prepared"] == 0
    assert owner.status()["settled"] == 0


def test_l5_prepare_and_commit_failures_leave_no_partial_transaction(
    monkeypatch,
):
    world, causal, auditory_l5, physical, companion = _authorities()
    world_before = world.encoded_snapshot()

    def fail_prepare(_settlement):
        raise RuntimeError("injected binaural L5 prepare failure")

    monkeypatch.setattr(auditory_l5, "prepare", fail_prepare)
    with pytest.raises(RuntimeError, match="prepare failure"):
        companion.prepare(pcm_s16le=_tone(440))
    assert world.encoded_snapshot() == world_before
    assert causal.status()["prepared_reservation"] == 0
    assert auditory_l5.status()["prepared"] == 0
    assert physical.status()["active_epochs"] == 0

    monkeypatch.undo()
    prepared = companion.prepare(pcm_s16le=_tone(440))

    def fail_commit(_experience):
        raise RuntimeError("injected binaural L5 commit failure")

    monkeypatch.setattr(auditory_l5, "commit_prepared", fail_commit)
    with pytest.raises(RuntimeError, match="commit failure"):
        companion.commit(prepared)
    assert world.encoded_snapshot() == world_before
    assert causal.status()["prepared_reservation"] == 0
    assert auditory_l5.status()["prepared"] == 0
    assert auditory_l5.status()["settled"] == 0
    assert physical.status()["active_epochs"] == 0


def test_failure_after_causal_mutation_rolls_back_both_owners(
    monkeypatch,
):
    world, causal, auditory_l5, physical, companion = _authorities()
    world_before = world.encoded_snapshot()
    prepared = companion.prepare(pcm_s16le=_tone(440))
    original_commit = causal._commit_prepared_locked

    def fail_after_causal_mutation(settlement):
        original_commit(settlement)
        raise RuntimeError("injected failure after causal mutation")

    monkeypatch.setattr(
        causal,
        "_commit_prepared_locked",
        fail_after_causal_mutation,
    )
    with pytest.raises(RuntimeError, match="after causal mutation"):
        companion.commit(prepared)

    assert world.encoded_snapshot() == world_before
    assert causal.status()["settled"] == 0
    assert causal.status()["prepared_reservation"] == 0
    assert auditory_l5.status()["settled"] == 0
    assert auditory_l5.status()["prepared"] == 0
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["prepared_multisensory_mount"] == 0


def test_repeated_l5_commits_replace_latest_inside_fixed_capacity():
    _world_authority, _causal, auditory_l5, physical, companion = _authorities()
    for frequency_hz in (440, 550, 660, 770, 880, 990):
        prepared = companion.prepare(pcm_s16le=_tone(frequency_hz))
        companion.commit(prepared)

    status = auditory_l5.status()
    assert status["settled"] == 6
    assert status["transition_relations"] <= status["transition_capacity"] == 4
    assert status["prepared"] == 0
    assert physical.status()["retained_raw_media_bytes"] == 0
