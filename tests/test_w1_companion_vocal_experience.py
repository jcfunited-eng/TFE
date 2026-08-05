from __future__ import annotations

import hashlib
import math
import json
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
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    MAX_COMPANION_VOCAL_EPISODE_SAMPLES,
    W1CompanionVocalExperienceAuthority,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)


def _pcm() -> bytes:
    sample_count = 960
    values = tuple(
        12_000 if index % 16 < 8 else -12_000
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *values)


def _tone(frequency_hz: int) -> bytes:
    sample_count = 960
    values = tuple(
        int(12_000 * math.sin(
            2 * math.pi * frequency_hz * index / 16_000
        ))
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *values)


def _long_tone(frequency_hz: int, sample_count: int) -> bytes:
    values = tuple(
        int(12_000 * math.sin(
            2 * math.pi * frequency_hz * index / 16_000
        ))
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *values)


MULTIBLOCK_TEST_SAMPLES = (
    MAX_EMITTED_PCM_SAMPLES + MIN_EMITTED_PCM_SAMPLES
)


def _authorities(on_settlement, *, ambiguous_source=False):
    companion_position = (
        PositionMM(1_800, 2_500, 0)
        if ambiguous_source
        else PositionMM(3_500, 2_500, 0)
    )
    additional_objects = (
        (
            EmbodiedObject(
                "same-path-object",
                radius_mm=75,
                mass_grams=250,
                position=PositionMM(200, 2_500, 0),
            ),
        )
        if ambiguous_source
        else ()
    )
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
                PoseMM(companion_position, 180_000),
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
            *additional_objects,
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
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=b"v" * 32,
                physical_authority_key=b"p" * 32,
            )
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


def test_committed_companion_episode_can_roll_back_as_one_authority():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    world_before = world.encoded_snapshot()
    owner_before = owner.status()
    binaural_before = physical._binaural_auditory_l5_owner.status()
    continuity_before = (
        physical._anonymous_av_continuity_owner.encoded_snapshot()
    )
    prepared = companion.prepare_episode(
        pcm_s16le=_long_tone(440, MULTIBLOCK_TEST_SAMPLES),
    )

    undo = companion.commit_episode(prepared)
    assert world.observation_snapshot().revision == 2
    assert owner.status()["settled"] == 2
    assert physical._binaural_auditory_l5_owner.status()["settled"] == 2
    assert physical._anonymous_av_continuity_owner.status()["settled"] == 2
    assert companion.status()["has_latest_episode"] is True

    companion.rollback_committed_episode(undo)

    assert world.encoded_snapshot() == world_before
    assert owner.status() == owner_before
    assert physical._binaural_auditory_l5_owner.status() == binaural_before
    assert (
        physical._anonymous_av_continuity_owner.encoded_snapshot()
        == continuity_before
    )
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert companion.status()["has_latest_episode"] is False


def test_one_block_episode_intent_authenticates_explicit_causal_parent():
    accepted = []
    world, _owner, _physical, companion = _authorities(accepted.append)
    before = world.observation_snapshot()
    pcm = _pcm()
    parent = "1" * 64

    prepared = companion.prepare_episode(
        pcm_s16le=pcm,
        causal_parent_receipt_sha256=parent,
    )
    intent = prepared.intent_receipt
    companion.verify_episode_intent(intent)
    record = companion.episode_intent_record(intent)
    reconstructed = companion.episode_intent_from_record(record)

    assert reconstructed == intent
    assert record == {
        "authority_hmac_sha256": intent.authority_hmac_sha256,
        "authority_receipt_sha256": intent.authority_receipt_sha256,
        "block_count": 1,
        "causal_parent_receipt_sha256": parent,
        "companion_port_id": SECOND_BODY_PORT_ID,
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "sample_rate_hz": 16_000,
        "schema": "guala.w1.companion_vocal_episode_intent.v2",
        "total_sample_count": len(pcm) // 2,
        "world_observation_receipt_sha256": (
            before.authority_receipt_sha256
        ),
    }
    execution = prepared.prediction_blocks[0].execution_receipt
    assert execution.causal_intent_receipt_sha256 == (
        intent.authority_receipt_sha256
    )
    assert execution.before.authority_receipt_sha256 == (
        intent.world_observation_receipt_sha256
    )
    assert prepared.episode.intent_authority_receipt_sha256 == (
        intent.authority_receipt_sha256
    )
    assert prepared.episode.world_before_receipt_sha256 == (
        intent.world_observation_receipt_sha256
    )

    companion.discard_episode(prepared)
    assert world.observation_snapshot() == before
    assert accepted == []


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("causal_parent_receipt_sha256", "2" * 64),
        ("world_observation_receipt_sha256", "3" * 64),
        ("pcm_sha256", "4" * 64),
        ("total_sample_count", 1_440),
        ("block_count", 2),
    ),
)
def test_episode_intent_record_rejects_every_tampered_signed_relation(
    field_name,
    replacement,
):
    _world, _owner, _physical, companion = _authorities(
        lambda _settlement: None
    )
    prepared = companion.prepare_episode(
        pcm_s16le=_pcm(),
        causal_parent_receipt_sha256="1" * 64,
    )
    record = companion.episode_intent_record(prepared.intent_receipt)
    record[field_name] = replacement

    with pytest.raises(ValueError):
        companion.episode_intent_from_record(record)

    companion.discard_episode(prepared)


def test_episode_intent_record_cannot_cross_authority_owners():
    world, _owner, physical, companion = _authorities(
        lambda _settlement: None
    )
    crossed = W1CompanionVocalExperienceAuthority(
        authority_key=b"d" * 32,
        world_authority=world,
        physical_authority=physical,
    )
    prepared = companion.prepare_episode(
        pcm_s16le=_pcm(),
        causal_parent_receipt_sha256="1" * 64,
    )
    record = companion.episode_intent_record(prepared.intent_receipt)

    with pytest.raises(
        ValueError,
        match="episode intent authority changed",
    ):
        crossed.episode_intent_from_record(record)

    companion.discard_episode(prepared)


def test_causal_parent_is_rejected_for_multiblock_episode_before_mutation():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()

    with pytest.raises(
        ValueError,
        match="causal parent requires exactly one physical block",
    ):
        companion.prepare_episode(
            pcm_s16le=_long_tone(440, MULTIBLOCK_TEST_SAMPLES),
            causal_parent_receipt_sha256="1" * 64,
        )

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert companion.status()["prepared_episode"] == 0


@pytest.mark.parametrize("parent", ("not-a-digest", b"1" * 64, True))
def test_causal_parent_requires_one_typed_lowercase_digest(parent):
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        companion.prepare_episode(
            pcm_s16le=_pcm(),
            causal_parent_receipt_sha256=parent,
        )

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["atomic_episode"] == 0


def test_parented_episode_rejects_stale_starting_world_and_rolls_back(
    monkeypatch,
):
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()
    issue_intent = companion._issue_episode_intent

    def issue_then_change_world(**values):
        intent = issue_intent(**values)
        current = world.observation_snapshot()
        execution = world.execute_port_command(
            port_id=SECOND_BODY_PORT_ID,
            command_payload=encode_command(VocalizeCommand(
                epoch_commitment_sha256="5" * 64,
                sequence=0,
                source_sample_start=0,
                pcm_sha256="6" * 64,
                sample_count=160,
            )),
            causal_intent_receipt_sha256="7" * 64,
            expected_revision=current.revision,
        )
        assert execution.disposition == "applied"
        return intent

    monkeypatch.setattr(
        companion,
        "_issue_episode_intent",
        issue_then_change_world,
    )
    with pytest.raises(RuntimeError, match="starting world changed"):
        companion.prepare_episode(
            pcm_s16le=_pcm(),
            causal_parent_receipt_sha256="1" * 64,
        )

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert physical.status()["active_epochs"] == 0
    assert companion.status()["prepared_episode"] == 0


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
    assert physical.status()["binaural_auditory_l5"]["prepared"] == 0
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"]["prepared"] == 0
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


def test_companion_episode_hears_pressure_when_visual_source_is_ambiguous():
    accepted = []
    world, owner, physical, companion = _authorities(
        accepted.append,
        ambiguous_source=True,
    )
    before = world.observation_snapshot()

    prepared = companion.prepare_episode(pcm_s16le=_pcm())
    block = prepared.episode.blocks[0]
    mount = prepared.prediction_blocks[0].physical_mount

    assert mount.reason == (
        "anonymous_multisensory_evidence_observed_source_ambiguous"
    )
    assert block.binaural_l5 is mount.binaural_auditory_l5
    assert block.anonymous_av_correspondence is None
    assert block.anonymous_av_continuity_receipt_sha256 is None
    assert mount.anonymous_av_continuity is None
    assert mount.causal_settlement is not None
    assert accepted == []

    undo = companion.commit_episode(prepared)

    assert world.observation_snapshot().revision == before.revision + 1
    assert owner.status()["settled"] == 1
    assert physical._binaural_auditory_l5_owner.status()["settled"] == 1
    assert physical._anonymous_av_continuity_owner.status()["settled"] == 0

    companion.rollback_committed_episode(undo)

    assert world.observation_snapshot() == before
    assert owner.status()["settled"] == 0
    assert physical._binaural_auditory_l5_owner.status()["settled"] == 0
    assert physical._anonymous_av_continuity_owner.status()["settled"] == 0


def test_known_length_multiblock_episode_preserves_every_full_field():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.observation_snapshot()

    prepared = companion.prepare_episode(
        pcm_s16le=_long_tone(440, MULTIBLOCK_TEST_SAMPLES),
    )
    episode = prepared.episode
    episode.verify(b"c" * 32)

    assert prepared.intent_receipt.causal_parent_receipt_sha256 is None
    assert len(episode.blocks) == 2
    assert len(prepared.prediction_blocks) == 2
    exact_mounts = tuple(
        prediction.physical_mount
        for prediction in prepared.prediction_blocks
    )
    assert all(
        prediction.causal_settlement
        is prediction.physical_mount.causal_settlement
        and prediction.evidence_receipt
        is prediction.physical_mount.evidence_receipt
        and prediction.anonymous_av_continuity
        is prediction.physical_mount.anonymous_av_continuity
        for prediction in prepared.prediction_blocks
    )
    for mount in exact_mounts:
        physical.verify_mount(mount)
    assert all(
        prediction.execution_receipt.authority_receipt_sha256
        == block.world_execution_receipt_sha256
        and prediction.causal_settlement.authority_receipt_sha256
        == block.causal_settlement_receipt_sha256
        and prediction.evidence_receipt.authority_receipt_sha256
        == block.physical_evidence_receipt_sha256
        and prediction.anonymous_av_continuity.authority_receipt_sha256
        == block.anonymous_av_continuity_receipt_sha256
        for prediction, block in zip(
            prepared.prediction_blocks, episode.blocks, strict=True
        )
    )
    assert tuple(block.sequence for block in episode.blocks) == (0, 1)
    assert tuple(
        (block.source_sample_start, block.source_sample_end)
        for block in episode.blocks
    ) == (
        (0, MAX_EMITTED_PCM_SAMPLES),
        (MAX_EMITTED_PCM_SAMPLES, MULTIBLOCK_TEST_SAMPLES),
    )
    assert all(
        sum(len(channel.pressure.field_tuples)
            + len(channel.carrier_phase_advance.field_tuples)
            for ear in block.binaural_l5.ears
            for channel in ear.channels) > 0
        for block in episode.blocks
    )
    assert all(
        len(block.binaural_l5.ears) == 2
        and all(len(ear.channels) == 16 for ear in block.binaural_l5.ears)
        for block in episode.blocks
    )
    assert all(
        block.anonymous_av_correspondence.matched_ordinal
        < len(block.anonymous_av_correspondence.candidates)
        and block.anonymous_av_correspondence.observed_acoustic_path
        == block.anonymous_av_correspondence.candidates[
            block.anonymous_av_correspondence.matched_ordinal
        ].predicted_acoustic_path
        for block in episode.blocks
    )
    assert accepted == []
    assert world.observation_snapshot().revision == before.revision + 2
    assert owner.status()["settled"] == 0
    assert owner.status()["atomic_sequence"] == 1
    assert owner.status()["atomic_sequence_staged_settled"] == 2
    assert physical.status()["atomic_episode"] == 1
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["binaural_auditory_l5"][
        "atomic_sequence_staged_settled"
    ] == 2
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"][
        "atomic_sequence_staged_settled"
    ] == 2
    assert physical._binaural_auditory_l5_owner.latest is None
    persisted = json.dumps(episode.persistence_record(b"c" * 32))
    prepared_prediction = repr(prepared.prediction_blocks)
    assert "pcm_s16le" not in persisted
    assert "left_pcm_s16le" not in persisted
    assert "right_pcm_s16le" not in persisted
    assert "pcm_s16le" not in prepared_prediction
    assert "left_pcm_s16le" not in prepared_prediction
    assert "right_pcm_s16le" not in prepared_prediction
    assert "anonymous_av_correspondence_authority" in persisted
    assert len(persisted.encode("utf-8")) <= 8 * 1024 * 1024

    undo = companion.commit_episode(prepared)

    assert accepted == []
    assert tuple(
        prediction.physical_mount
        for prediction in undo.prepared.prediction_blocks
    ) == exact_mounts
    assert all(
        retained is exact
        for retained, exact in zip(
            (
                prediction.physical_mount
                for prediction in undo.prepared.prediction_blocks
            ),
            exact_mounts,
            strict=True,
        )
    )
    assert physical.status()["atomic_episode"] == 0
    assert physical.status()["active_epochs"] == 0
    assert owner.status()["atomic_sequence"] == 0
    assert owner.status()["settled"] == 2
    assert physical.status()["binaural_auditory_l5"]["settled"] == 2
    assert physical.status()["anonymous_av_continuity"]["settled"] == 2
    assert physical.status()["anonymous_av_continuity"][
        "has_latest"
    ] is True
    assert companion.status()["has_latest_episode"] is True
    assert companion.status()["prepared_episode"] == 0

    companion.rollback_committed_episode(undo)

    assert world.observation_snapshot() == before
    assert all(
        prediction.physical_mount is exact
        for prediction, exact in zip(
            undo.prepared.prediction_blocks,
            exact_mounts,
            strict=True,
        )
    )
    assert owner.status()["settled"] == 0
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert companion.status()["has_latest_episode"] is False


def test_multiblock_episode_discard_restores_world_causal_and_l5_state():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()

    prepared = companion.prepare_episode(
        pcm_s16le=_long_tone(660, MULTIBLOCK_TEST_SAMPLES),
    )
    companion.discard_episode(prepared)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["settled"] == 0
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["binaural_auditory_l5"]["has_latest"] is False
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"][
        "has_latest"
    ] is False


def test_second_block_failure_rolls_back_the_complete_episode(monkeypatch):
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()
    original_mount = physical.mount

    def fail_second_block(**kwargs):
        if kwargs["sequence"] == 1:
            raise RuntimeError("injected second block failure")
        return original_mount(**kwargs)

    monkeypatch.setattr(physical, "mount", fail_second_block)
    with pytest.raises(RuntimeError, match="second block failure"):
        companion.prepare_episode(
            pcm_s16le=_long_tone(880, MULTIBLOCK_TEST_SAMPLES),
        )

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["settled"] == 0
    assert owner.status()["prepared_reservation"] == 0
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert physical.status()["prepared_multisensory_mount"] == 0
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["binaural_auditory_l5"]["prepared"] == 0


def test_episode_commit_failure_restores_l5_publication_and_remains_discardable(
    monkeypatch,
):
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()
    prepared = companion.prepare_episode(
        pcm_s16le=_long_tone(550, MULTIBLOCK_TEST_SAMPLES),
    )
    original_commit = owner.commit_atomic_sequence

    def fail_causal_publish(_token):
        raise RuntimeError("injected causal episode publish failure")

    monkeypatch.setattr(owner, "commit_atomic_sequence", fail_causal_publish)
    with pytest.raises(RuntimeError, match="episode publish failure"):
        companion.commit_episode(prepared)

    assert physical.status()["atomic_episode"] == 1
    assert physical.status()["active_epochs"] == 1
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["binaural_auditory_l5"]["atomic_sequence"] == 1
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"][
        "atomic_sequence"
    ] == 1
    assert companion.status()["prepared_episode"] == 1

    monkeypatch.setattr(owner, "commit_atomic_sequence", original_commit)
    companion.discard_episode(prepared)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["settled"] == 0
    assert owner.status()["atomic_sequence"] == 0
    assert physical.status()["atomic_episode"] == 0
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["binaural_auditory_l5"]["settled"] == 0
    assert physical.status()["binaural_auditory_l5"]["atomic_sequence"] == 0
    assert physical.status()["anonymous_av_continuity"]["settled"] == 0
    assert physical.status()["anonymous_av_continuity"][
        "atomic_sequence"
    ] == 0


def test_episode_partition_preserves_complete_auditory_hops():
    blocks = W1CompanionVocalExperienceAuthority._episode_blocks(
        _long_tone(
            440,
            MAX_EMITTED_PCM_SAMPLES + MIN_EMITTED_PCM_SAMPLES,
        )
    )
    assert tuple(len(block) // 2 for block in blocks) == (
        MAX_EMITTED_PCM_SAMPLES,
        MIN_EMITTED_PCM_SAMPLES,
    )


def test_oversize_episode_fails_before_any_authority_mutates():
    accepted = []
    world, owner, physical, companion = _authorities(accepted.append)
    before = world.encoded_snapshot()
    pcm = b"\x00\x00" * (MAX_COMPANION_VOCAL_EPISODE_SAMPLES + 1)

    with pytest.raises(ValueError, match="exact sample boundary"):
        companion.prepare_episode(pcm_s16le=pcm)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert owner.status()["settled"] == 0
    assert physical.status()["active_epochs"] == 0
    assert physical.status()["atomic_episode"] == 0
