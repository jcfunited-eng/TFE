from __future__ import annotations

import hashlib
import json

from dsf_ai_service.substrate.physical_surface_tutoring_conductor import (
    CARD_EXPOSURE_NS,
    PhysicalSurfaceTutoringConductor,
    PhysicalSurfaceTutoringPlanStep,
)


KEY = b"physical-surface-tutoring-conductor-test-key-v1"
SURFACES = tuple(
    f"W1-optical-surface-{index:02d}"
    for index in range(1, 37)
)


def _wav(ordinal: int) -> bytes:
    return b"RIFF" + ordinal.to_bytes(4, "little") + b"physical-pressure"


def _step(ordinal: int) -> PhysicalSurfaceTutoringPlanStep:
    wav = _wav(ordinal)
    return PhysicalSurfaceTutoringPlanStep.create(
        target_object_id=SURFACES[ordinal - 1],
        source_media_receipt_sha256=hashlib.sha256(wav).hexdigest(),
    )


def _result(ordinal: int) -> dict[str, object]:
    return {
        "passive_learning_receipt_sha256": f"{ordinal + 2:x}" * 64,
        "retained_pcm_bytes": 0,
        "schema": "guala.physical_surface_lesson.result.v1",
        "settlement_receipt_sha256": f"{ordinal:x}" * 64,
        "thing_id": f"physical-thing-{ordinal}",
        "visual_exposure_duration_ns": CARD_EXPOSURE_NS,
        "whole_organism_episode_receipt_sha256": f"{ordinal + 1:x}" * 64,
    }


def _raises(error_type, operation) -> str:
    try:
        operation()
    except error_type as error:
        return str(error)
    raise AssertionError(f"{error_type.__name__} was not raised")


def _conductor() -> PhysicalSurfaceTutoringConductor:
    return PhysicalSurfaceTutoringConductor(
        authority_key=KEY,
        approved_surface_ids=SURFACES,
    )


def test_steps_are_prior_bound_contiguous_and_cold_restorable() -> None:
    conductor = _conductor()
    plan = conductor.issue_plan(
        steps=(_step(1), _step(2)),
        initial_source_time_ns=20_000_000_000,
    )
    first = conductor.prepare_step(
        plan_receipt_sha256=plan.authority_receipt_sha256,
        step_index=0,
        prior_progression_receipt_sha256=None,
        wav_bytes=_wav(1),
        remaining_episode_slots=2,
        remaining_passive_slots=2,
        remaining_thing_partition_slots=2,
    )
    first_tail = conductor.commit_step(first, _result(1))
    assert first_tail.source_time_start_ns == 20_000_000_000
    assert first_tail.source_time_end_ns == 35_000_000_000

    encoded = conductor.snapshot_encoded()
    restored = PhysicalSurfaceTutoringConductor.restore_encoded(
        encoded,
        authority_key=KEY,
        approved_surface_ids=SURFACES,
    )
    assert restored.snapshot_encoded() == encoded
    second = restored.prepare_step(
        plan_receipt_sha256=plan.authority_receipt_sha256,
        step_index=1,
        prior_progression_receipt_sha256=(
            first_tail.authority_receipt_sha256
        ),
        wav_bytes=_wav(2),
        remaining_episode_slots=1,
        remaining_passive_slots=1,
        remaining_thing_partition_slots=1,
    )
    assert second.source_time_start_ns == first_tail.source_time_end_ns
    second_tail = restored.commit_step(second, _result(2))
    assert second_tail.prior_progression_receipt_sha256 == (
        first_tail.authority_receipt_sha256
    )
    assert restored.status() == {
        "active": False,
        "in_flight": False,
        "next_step_index": 2,
        "plan_receipt_sha256": plan.authority_receipt_sha256,
        "plan_step_count": 2,
        "progression_tail_receipt_sha256": (
            second_tail.authority_receipt_sha256
        ),
        "retained_pcm_bytes": 0,
        "schema": "guala.physical_surface_tutoring.status.v1",
    }
    continued = restored.issue_plan(
        steps=(_step(3),),
        initial_source_time_ns=None,
        prior_progression_receipt_sha256=(
            second_tail.authority_receipt_sha256
        ),
    )
    assert continued.initial_source_time_ns == second_tail.source_time_end_ns
    assert continued.prior_plan_progression_receipt_sha256 == (
        second_tail.authority_receipt_sha256
    )
    third = restored.prepare_step(
        plan_receipt_sha256=continued.authority_receipt_sha256,
        step_index=0,
        prior_progression_receipt_sha256=(
            second_tail.authority_receipt_sha256
        ),
        wav_bytes=_wav(3),
        remaining_episode_slots=1,
        remaining_passive_slots=1,
        remaining_thing_partition_slots=1,
    )
    assert third.source_time_start_ns == second_tail.source_time_end_ns


def test_stale_replay_capacity_and_parallel_admission_fail_before_progression() -> None:
    conductor = _conductor()
    plan = conductor.issue_plan(
        steps=(_step(1), _step(2)),
        initial_source_time_ns=1,
    )
    before = conductor.snapshot_encoded()
    message = _raises(
        RuntimeError,
        lambda: conductor.prepare_step(
            plan_receipt_sha256=plan.authority_receipt_sha256,
            step_index=0,
            prior_progression_receipt_sha256=None,
            wav_bytes=_wav(1),
            remaining_episode_slots=0,
            remaining_passive_slots=2,
            remaining_thing_partition_slots=2,
        ),
    )
    assert "episode capacity is exhausted" in message
    assert conductor.snapshot_encoded() == before

    prepared = conductor.prepare_step(
        plan_receipt_sha256=plan.authority_receipt_sha256,
        step_index=0,
        prior_progression_receipt_sha256=None,
        wav_bytes=_wav(1),
        remaining_episode_slots=2,
        remaining_passive_slots=2,
        remaining_thing_partition_slots=2,
    )
    assert "in flight" in _raises(
        RuntimeError,
        lambda: conductor.prepare_step(
            plan_receipt_sha256=plan.authority_receipt_sha256,
            step_index=0,
            prior_progression_receipt_sha256=None,
            wav_bytes=_wav(1),
            remaining_episode_slots=2,
            remaining_passive_slots=2,
            remaining_thing_partition_slots=2,
        ),
    )
    conductor.abort_step(prepared)
    prepared = conductor.prepare_step(
        plan_receipt_sha256=plan.authority_receipt_sha256,
        step_index=0,
        prior_progression_receipt_sha256=None,
        wav_bytes=_wav(1),
        remaining_episode_slots=2,
        remaining_passive_slots=2,
        remaining_thing_partition_slots=2,
    )
    tail = conductor.commit_step(prepared, _result(1))
    after = conductor.snapshot_encoded()

    assert "stale" in _raises(
        ValueError,
        lambda: conductor.prepare_step(
            plan_receipt_sha256=plan.authority_receipt_sha256,
            step_index=0,
            prior_progression_receipt_sha256=None,
            wav_bytes=_wav(1),
            remaining_episode_slots=1,
            remaining_passive_slots=1,
            remaining_thing_partition_slots=1,
        ),
    )
    assert conductor.snapshot_encoded() == after
    assert "prior receipt is stale" in _raises(
        ValueError,
        lambda: conductor.prepare_step(
            plan_receipt_sha256=plan.authority_receipt_sha256,
            step_index=1,
            prior_progression_receipt_sha256="f" * 64,
            wav_bytes=_wav(2),
            remaining_episode_slots=1,
            remaining_passive_slots=1,
            remaining_thing_partition_slots=1,
        ),
    )
    assert conductor.progression_tail == tail
    assert conductor.snapshot_encoded() == after


def test_state_is_bounded_authenticated_and_retains_no_media_or_meaning() -> None:
    conductor = _conductor()
    plan = conductor.issue_plan(
        steps=tuple(_step(index) for index in range(1, 37)),
        initial_source_time_ns=0,
    )
    encoded = conductor.snapshot_encoded()
    assert len(encoded) < 128 * 1024
    assert _wav(1) not in encoded
    payload = json.loads(encoded)
    flattened = encoded.decode("ascii")
    assert "transcript" not in flattened.replace(
        '"transcript_authority":false',
        "",
    )
    assert "pronunciation" not in flattened
    assert "word" not in flattened.replace('"word_authority":false', "")
    assert plan.payload()["authority_boundary"] == {
        "meaning_authority": False,
        "recognition_authority": False,
        "transcript_authority": False,
        "word_authority": False,
    }

    tampered = bytearray(encoded)
    tampered[-8] ^= 1
    _raises(
        ValueError,
        lambda: PhysicalSurfaceTutoringConductor.restore_encoded(
            bytes(tampered),
            authority_key=KEY,
            approved_surface_ids=SURFACES,
        ),
    )
    assert "not approved" in _raises(
        ValueError,
        lambda: conductor.issue_plan(
            steps=(PhysicalSurfaceTutoringPlanStep.create(
                target_object_id="unmounted-surface",
                source_media_receipt_sha256="a" * 64,
            ),),
            initial_source_time_ns=0,
        ),
    )
