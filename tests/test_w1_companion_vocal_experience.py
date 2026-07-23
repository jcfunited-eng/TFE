from __future__ import annotations

import math
import struct

import pytest

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
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
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)


def _pcm() -> bytes:
    values = tuple(12_000 if index % 16 < 8 else -12_000 for index in range(1024))
    return struct.pack("<1024h", *values)


def _tone(frequency_hz: int) -> bytes:
    values = tuple(
        int(12_000 * math.sin(
            2 * math.pi * frequency_hz * index / 16_000
        ))
        for index in range(1024)
    )
    return struct.pack("<1024h", *values)


def _authorities(on_settlement):
    world = EmbodimentWorldAuthority(
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
        initial_objects=(
            EmbodiedObject(
                "object-1",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    owner = ExactCausalExperienceOwner(
        on_settlement=on_settlement,
        log_event=lambda *_args, **_kwargs: None,
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=b"p" * 32,
        world_authority=world,
        causal_owner=owner,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=b"a" * 32,
            world_authority=world,
        ),
    )
    companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"c" * 32,
        world_authority=world,
        physical_authority=physical,
    )
    return world, owner, physical, companion


def test_companion_vocal_prepare_and_commit_is_one_exact_experience():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.observation_snapshot()

    prepared = companion.prepare(
        pcm_s16le=_pcm(),
    )

    assert accepted == []
    assert world.observation_snapshot().revision == before.revision + 1
    assert prepared.execution_receipt.port_id == SECOND_BODY_PORT_ID
    prepared.intent_receipt.verify(b"c" * 32)
    assert prepared.execution_receipt.causal_intent_receipt_sha256 == (
        prepared.intent_receipt.authority_receipt_sha256
    )
    assert prepared.acoustic_emission.receipt.world_execution_receipt_sha256 == (
        prepared.execution_receipt.authority_receipt_sha256
    )
    sound = next(
        item for item in prepared.physical_mount.causal_settlement.interpretations
        if item.sense == "sound"
    )
    assert len(sound.substreams) == 64
    assert owner.status()["prepared_reservation"] == 1
    companion_status = companion.status()
    assert 0 < companion_status["retained_raw_media_bytes"] <= (
        companion_status["max_retained_raw_media_bytes"]
    )
    physical_status = physical.status()
    assert 0 < physical_status["retained_raw_media_bytes"] <= (
        physical_status["max_retained_raw_media_bytes"]
    )

    companion.commit(prepared)

    assert accepted == [prepared.physical_mount.causal_settlement]
    assert companion.status()["prepared"] == 0
    assert companion.status()["retained_raw_media_bytes"] == 0
    assert physical.status()["active_epochs"] == 0


def test_companion_vocal_discard_restores_world_and_reservation():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()
    prepared = companion.prepare(
        pcm_s16le=_pcm(),
    )

    companion.discard(prepared)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["prepared_reservation"] == 0
    assert physical.status()["active_epochs"] == 0
    with pytest.raises(ValueError, match="preparation changed"):
        companion.commit(prepared)


def test_receipt_verification_failure_releases_every_transaction_owner(
    monkeypatch,
):
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()

    def fail_verification(_receipt, _authority_key):
        raise RuntimeError("injected evidence receipt verification failure")

    monkeypatch.setattr(
        W1PhysicalEvidenceReceipt,
        "verify",
        fail_verification,
    )

    with pytest.raises(RuntimeError, match="receipt verification failure"):
        companion.prepare(
            pcm_s16le=_pcm(),
        )

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["prepared_reservation"] == 0
    assert physical.status()["pending_multisensory_reservation"] == 0
    assert physical.status()["prepared_multisensory_mount"] == 0
    assert physical.status()["active_epochs"] == 0
    assert companion.status()["prepared"] == 0


def test_different_pressure_waves_produce_different_cochlear_fields():
    first_world, _first_owner, _first_physical, first = _authorities(
        lambda _settlement: None
    )
    second_world, _second_owner, _second_physical, second = _authorities(
        lambda _settlement: None
    )
    assert first_world.encoded_snapshot() == second_world.encoded_snapshot()

    first_prepared = first.prepare(pcm_s16le=_tone(440))
    second_prepared = second.prepare(pcm_s16le=_tone(880))
    first_sound = next(
        item
        for item in first_prepared.physical_mount.causal_settlement.interpretations
        if item.sense == "sound"
    )
    second_sound = next(
        item
        for item in second_prepared.physical_mount.causal_settlement.interpretations
        if item.sense == "sound"
    )
    first_field = tuple(
        field_tuple.fields
        for substream in first_sound.substreams
        for field_tuple in substream.field_tuples
    )
    second_field = tuple(
        field_tuple.fields
        for substream in second_sound.substreams
        for field_tuple in substream.field_tuples
    )

    assert len(first_sound.substreams) == len(second_sound.substreams) == 64
    assert first_field != second_field

    first.discard(first_prepared)
    second.discard(second_prepared)
