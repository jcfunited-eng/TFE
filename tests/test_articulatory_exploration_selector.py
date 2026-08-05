from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.substrate import articulatory_self_vocal_motor as motor_module
from dsf_ai_service.substrate.articulatory_exploration_selector import (
    ActivePendingArticulatoryAttemptError,
    ArticulatoryExplorationSelector,
    ArticulatoryExplorationState,
    physical_action_for_program,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryProgram,
    LaryngealExcitationConfiguration,
)
from dsf_ai_service.substrate.pending_articulatory_causal_attempt import (
    PendingArticulatoryCausalAttemptOwner,
    PendingArticulatoryCausalAttemptProfile,
)
from tests.test_articulatory_consequence_closure import (
    _Harness,
)
from tests.test_articulatory_self_vocal_motor import _program


KEY = b"articulatory-exploration-selector-test-key"


def _pending(
    harness: _Harness,
) -> PendingArticulatoryCausalAttemptOwner:
    return PendingArticulatoryCausalAttemptOwner(
        authority_key=KEY,
        profile=PendingArticulatoryCausalAttemptProfile.create(
            profile_id="articulatory-exploration-pending",
            max_state_bytes=2 * 1024 * 1024,
        ),
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        world_authority=harness.world,
        consequence_closure_owner=harness.closure,
    )


def _selector(
    harness: _Harness,
    pending: PendingArticulatoryCausalAttemptOwner,
) -> ArticulatoryExplorationSelector:
    return ArticulatoryExplorationSelector(
        motor_owner=harness.articulatory,
        consequence_closure_owner=harness.closure,
        pending_attempt_owner=pending,
    )


def _close(
    harness: _Harness,
    mosaic,
    *,
    program_id: str,
    name: str,
) -> None:
    _mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=program_id,
        name=name,
    )
    consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )
    harness.closure.commit_prepared(
        harness.closure.prepare(attempt, consequence)
    )


def test_physical_action_is_exact_excitation_and_section_area_travel():
    program = _program()
    action = physical_action_for_program(program)
    excitation, _radiated, areas = (
        motor_module._generate_physical_pressure(program)
    )
    expected_travel = sum(abs(value) for value in excitation)
    expected_motion = tuple(
        sum(
            abs(right - left)
            for left, right in zip(
                section,
                section[1:],
            )
        )
        for section in areas
    )

    assert (
        action.laryngeal_excitation_travel_pcm
        == expected_travel
    )
    assert action.tract_section_area_travel_mm2 == expected_motion
    assert len(action.tract_section_area_travel_mm2) == 8


def test_unique_minimum_selects_without_state_and_equal_action_is_silent():
    harness = _Harness(
        world_key=b"articulatory-exploration-unique-world-key"
    )
    pending = _pending(harness)
    selector = _selector(harness, pending)

    selected = selector.select()

    assert selected.state is ArticulatoryExplorationState.SELECTED
    assert selected.program == harness.programs[0]
    assert selected.unclosed_program_count == 2
    assert selected.minimal_program_count == 1
    selector.verify_selection(selected)
    assert selector.select() == selected
    assert selector.status() == {
        "actuator_dimensions": 9,
        "retained_pcm_bytes": 0,
        "retained_selection_count": 0,
        "schema": (
            "guala.articulatory_exploration_selector.status.v1"
        ),
        "stateful": False,
    }
    assert not hasattr(selector, "snapshot_encoded")

    first = harness.programs[0]
    tied = ArticulatoryProgram.create(
        sample_count=first.sample_count,
        larynx=first.larynx,
        tract=replace(
            first.tract,
            radiation_load_area_mm2=(
                first.tract.radiation_load_area_mm2 + 1
            ),
        ),
    )
    harness.articulatory.admit_program(tied)
    silent = selector.select()

    assert silent.state is ArticulatoryExplorationState.SILENT
    assert silent.program is None
    assert silent.physical_action is None
    assert silent.unclosed_program_count == 3
    assert silent.minimal_program_count == 2
    with pytest.raises(ValueError, match="changed custody"):
        selector.verify_selection(selected)


def test_closed_programs_are_excluded_and_pending_custody_rejects_selection():
    harness = _Harness(
        world_key=b"articulatory-exploration-closure-world-key"
    )
    pending = _pending(harness)
    selector = _selector(harness, pending)
    mosaic = harness.start_first_thing()
    _close(
        harness,
        mosaic,
        program_id=harness.programs[0].program_id,
        name="close-componentwise-minimum",
    )

    selected = selector.select()

    assert selected.state is ArticulatoryExplorationState.SELECTED
    assert selected.program == harness.programs[1]
    assert selected.unclosed_program_count == 1

    second = _Harness(
        world_key=b"articulatory-exploration-pending-world-key"
    )
    second_pending = _pending(second)
    second_selector = _selector(second, second_pending)
    second_mosaic = second.start_first_thing()
    _mosaic, attempt, _synthesis = second.attempt(
        second_mosaic,
        program_id=second.programs[0].program_id,
        name="pending-exploration-attempt",
    )
    prepared = second_pending.prepare_arm(attempt)
    with pytest.raises(
        ActivePendingArticulatoryAttemptError,
        match="active pending attempt",
    ):
        second_selector.select()
    undo = second_pending.commit_prepared_arm(prepared)
    with pytest.raises(
        ActivePendingArticulatoryAttemptError,
        match="active pending attempt",
    ):
        second_selector.select()
    second_pending.rollback_committed_arm(undo)
    assert (
        second_selector.select().state
        is ArticulatoryExplorationState.SELECTED
    )


def test_no_unclosed_or_incomparable_physical_actions_remains_silent():
    harness = _Harness(
        world_key=b"articulatory-exploration-incomparable-world-key"
    )
    pending = _pending(harness)
    selector = _selector(harness, pending)
    first = harness.start_first_thing()
    _close(
        harness,
        first,
        program_id=harness.programs[0].program_id,
        name="close-first-seed",
    )
    second = harness.start_second_thing()
    _close(
        harness,
        second,
        program_id=harness.programs[1].program_id,
        name="close-second-seed",
    )

    empty = selector.select()

    assert empty.state is ArticulatoryExplorationState.SILENT
    assert empty.unclosed_program_count == 0
    assert empty.minimal_program_count == 0

    lower_larynx = _program(5_000)
    neutral_tract = replace(
        lower_larynx.tract,
        apex_section_area_mm2=(
            lower_larynx.tract.initial_section_area_mm2
        ),
        final_section_area_mm2=(
            lower_larynx.tract.initial_section_area_mm2
        ),
    )
    lower_motion = ArticulatoryProgram.create(
        sample_count=lower_larynx.sample_count,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=(
                lower_larynx.larynx.cycle_samples
            ),
            open_samples=lower_larynx.larynx.open_samples,
            peak_volume_velocity_pcm=6_000,
        ),
        tract=neutral_tract,
    )
    harness.articulatory.admit_program(lower_larynx)
    harness.articulatory.admit_program(lower_motion)

    incomparable = selector.select()

    assert incomparable.state is ArticulatoryExplorationState.SILENT
    assert incomparable.unclosed_program_count == 2
    assert incomparable.minimal_program_count == 2
    assert (
        physical_action_for_program(lower_larynx)
        .laryngeal_excitation_travel_pcm
        < physical_action_for_program(lower_motion)
        .laryngeal_excitation_travel_pcm
    )
    assert any(
        left > right
        for left, right in zip(
            physical_action_for_program(lower_larynx)
            .tract_section_area_travel_mm2,
            physical_action_for_program(lower_motion)
            .tract_section_area_travel_mm2,
            strict=True,
        )
    )


def test_selector_rejects_crossed_exact_owner_graph():
    first = _Harness(
        world_key=b"articulatory-exploration-first-owner-world-key"
    )
    second = _Harness(
        world_key=b"articulatory-exploration-second-owner-world-key"
    )

    with pytest.raises(ValueError, match="crossed exact owner custody"):
        ArticulatoryExplorationSelector(
            motor_owner=first.articulatory,
            consequence_closure_owner=first.closure,
            pending_attempt_owner=_pending(second),
        )
