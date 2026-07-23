from __future__ import annotations

import pytest

from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority,
    _emission,
    _pcm,
    _vocal_execution,
    _world,
)


CONTINUITY_KEY = b"continuity-authority-key-for-w1-tests"


def _mounted_sequence(count: int = 3):
    world = _world()
    physical = _authority(world)
    epoch = physical.open_epoch()
    mounts = []
    sample_start = 0
    for sequence in range(count):
        pressure = _pcm()
        execution = _vocal_execution(
            world,
            epoch,
            sequence=sequence,
            source_sample_start=sample_start,
            pcm=pressure,
        )
        mounts.append(physical.mount(
            epoch_token=epoch,
            sequence=sequence,
            execution_receipt=execution,
            acoustic_emission=_emission(
                physical,
                epoch,
                execution,
                sequence=sequence,
                source_sample_start=sample_start,
                pcm=pressure,
            ),
        ))
        sample_start += len(pressure) // 2
    return physical, tuple(mounts)


def _owner() -> W1AnonymousAudiovisualContinuityOwner:
    return W1AnonymousAudiovisualContinuityOwner(
        authority_key=CONTINUITY_KEY,
        physical_authority_key=EVIDENCE_KEY,
        max_transitions=2,
    )


def test_continuity_learns_only_exact_adjacent_anonymous_geometry():
    _physical, mounts = _mounted_sequence()
    owner = _owner()
    learned = []
    for mount in mounts:
        correspondence = mount.anonymous_av_correspondence
        evidence = mount.evidence_receipt
        assert correspondence is not None
        assert evidence is not None
        prepared = owner.prepare(correspondence, evidence)
        owner.commit_prepared(prepared)
        learned.append(prepared)

    assert learned[0].relation == "first_observation"
    assert learned[0].prior_continuity_receipt_sha256 is None
    assert tuple(value.relation for value in learned) == (
        "first_observation",
        "structural_change",
        "recurrence",
    )
    assert len({value.lineage_token_sha256 for value in learned}) == 1
    assert (
        learned[1].prior_continuity_receipt_sha256
        == learned[0].authority_receipt_sha256
    )
    assert owner.status()["settled"] == 3
    assert owner.status()["transitions"] == 2


def test_continuity_snapshot_restores_exact_latest_field_and_lineage():
    _physical, mounts = _mounted_sequence(2)
    owner = _owner()
    for mount in mounts:
        learned = owner.prepare(
            mount.anonymous_av_correspondence,
            mount.evidence_receipt,
        )
        owner.commit_prepared(learned)

    encoded = owner.encoded_snapshot()
    assert len(encoded) <= 4 * 1024 * 1024
    for forbidden in (
        b"pcm_s16le",
        b"external-body",
        b"guala-body-1",
        b"w1.external-emitter",
        b"routing_chis",
        b"transcript",
    ):
        assert forbidden not in encoded

    restored = _owner()
    restored.restore_encoded(encoded)
    assert restored.status() == owner.status()

    tampered = bytearray(encoded)
    tampered[len(tampered) // 2] ^= 1
    with pytest.raises(ValueError):
        _owner().restore_encoded(bytes(tampered))


def test_restored_continuity_carries_the_same_lineage_into_next_experience():
    _physical, mounts = _mounted_sequence(3)
    owner = _owner()
    learned = []
    for mount in mounts[:2]:
        experience = owner.prepare(
            mount.anonymous_av_correspondence,
            mount.evidence_receipt,
        )
        owner.commit_prepared(experience)
        learned.append(experience)

    restored = _owner()
    restored.restore_encoded(owner.encoded_snapshot())
    continued = restored.prepare(
        mounts[2].anonymous_av_correspondence,
        mounts[2].evidence_receipt,
    )

    assert continued.lineage_token_sha256 == learned[-1].lineage_token_sha256
    assert continued.prior_continuity_receipt_sha256 == (
        learned[-1].authority_receipt_sha256
    )
    assert continued.relation == "recurrence"


def test_nonadjacent_world_observation_starts_a_new_anonymous_lineage():
    _physical, mounts = _mounted_sequence(3)
    owner = _owner()
    first = owner.prepare(
        mounts[0].anonymous_av_correspondence,
        mounts[0].evidence_receipt,
    )
    owner.commit_prepared(first)
    nonadjacent = owner.prepare(
        mounts[2].anonymous_av_correspondence,
        mounts[2].evidence_receipt,
    )

    assert nonadjacent.relation == "first_observation"
    assert nonadjacent.prior_continuity_receipt_sha256 is None
    assert nonadjacent.lineage_token_sha256 != first.lineage_token_sha256


def test_continuity_prepare_discard_and_atomic_rollback_publish_nothing():
    _physical, mounts = _mounted_sequence(2)
    owner = _owner()
    first = owner.prepare(
        mounts[0].anonymous_av_correspondence,
        mounts[0].evidence_receipt,
    )
    owner.discard_prepared(first)
    assert owner.status()["settled"] == 0

    token = owner.begin_atomic_sequence()
    first = owner.prepare(
        mounts[0].anonymous_av_correspondence,
        mounts[0].evidence_receipt,
    )
    owner.commit_prepared(first)
    second = owner.prepare(
        mounts[1].anonymous_av_correspondence,
        mounts[1].evidence_receipt,
    )
    owner.commit_prepared(second)
    assert owner.status()["settled"] == 0
    assert owner.status()["atomic_sequence_staged_settled"] == 2
    owner.rollback_atomic_sequence(token)
    assert owner.status()["settled"] == 0
    assert owner.status()["has_latest"] is False


def test_continuity_rejects_a_correspondence_not_bound_to_evidence():
    _physical, mounts = _mounted_sequence(2)
    owner = _owner()
    with pytest.raises(ValueError, match="differs from correspondence"):
        owner.prepare(
            mounts[0].anonymous_av_correspondence,
            mounts[1].evidence_receipt,
        )
