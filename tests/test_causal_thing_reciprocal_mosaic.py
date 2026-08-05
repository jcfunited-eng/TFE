from __future__ import annotations

import ast
import inspect

import dsf_ai_service.substrate.causal_thing_reciprocal_mosaic as module
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from tests.test_causal_thing_mosaic import (
    _execute,
    _fixture,
    _outcome,
)


def _reciprocal(owner) -> CausalThingReciprocalMosaicOwner:
    return CausalThingReciprocalMosaicOwner(
        authority_key="reciprocal-mosaic-test-authority-key-20260727",
        thing_owner=owner,
        max_classes=4,
        max_roots_per_class=1_024,
        max_cue_roots=256,
    )


def test_same_thing_variants_form_one_reciprocal_multisensory_class() -> None:
    world, sensory, partitions, owner = _fixture(max_partitions=4)
    picked = _execute(
        world,
        PickCommand("W1-object-1", duration_microseconds=100_000),
        21,
    )
    first_outcome = _outcome(sensory, picked)
    first = partitions.partition(
        outcome=first_outcome,
        observation=picked.after,
        execution=picked,
    )
    genesis = owner.admit(first)

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            duration_microseconds=100_000,
        ),
        22,
    )
    second_outcome = _outcome(sensory, moved)
    second = partitions.partition(
        outcome=second_outcome,
        observation=moved.after,
        execution=moved,
        prior=first,
    )
    expanded = owner.admit(second)
    reciprocal = _reciprocal(owner)
    classes = reciprocal.classes()

    assert expanded.thing_id == genesis.thing_id
    assert len(classes) == 1
    assert classes[0].thing_id == genesis.thing_id
    assert classes[0].partition_receipt_sha256s == (
        first.authority_receipt_sha256,
        second.authority_receipt_sha256,
    )
    assert {sense for sense, _roots in classes[0].roots_by_sense} >= {
        "body",
        "sight",
        "touch",
    }

    evocation = reciprocal.evoke(
        second_outcome.causal_settlement,
        cue_senses=("touch",),
    )
    assert evocation.state == "unique"
    assert evocation.thing_ids == (genesis.thing_id,)
    assert evocation.candidate == classes[0]
    assert evocation.evoked_full_field_roots == classes[0].full_field_roots
    assert {
        root.sense for root in evocation.evoked_full_field_roots
    } >= {"body", "sight", "touch"}


def test_different_physical_things_remain_separate_classes() -> None:
    world, sensory, partitions, owner = _fixture(max_partitions=4)
    picked_one = _execute(
        world,
        PickCommand("W1-object-1", duration_microseconds=100_000),
        31,
    )
    outcome_one = _outcome(sensory, picked_one)
    partition_one = partitions.partition(
        outcome=outcome_one,
        observation=picked_one.after,
        execution=picked_one,
    )
    mosaic_one = owner.admit(partition_one)

    placed_one = _execute(
        world,
        PlaceCommand(
            "W1-object-1",
            PositionMM(1000, 1700, 0),
            duration_microseconds=100_000,
        ),
        32,
    )
    assert placed_one.disposition == "applied"
    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(2000, 1000, 0), 0),
            duration_microseconds=100_000,
        ),
        33,
    )
    assert moved.disposition == "applied"
    picked_two = _execute(
        world,
        PickCommand("W1-object-2", duration_microseconds=100_000),
        34,
    )
    outcome_two = _outcome(sensory, picked_two)
    partition_two = partitions.partition(
        outcome=outcome_two,
        observation=picked_two.after,
        execution=picked_two,
    )
    mosaic_two = owner.admit(partition_two)

    reciprocal = _reciprocal(owner)
    classes = reciprocal.classes()
    assert len(classes) == 2
    assert mosaic_one.thing_id != mosaic_two.thing_id
    assert {value.thing_id for value in classes} == {
        mosaic_one.thing_id,
        mosaic_two.thing_id,
    }

    evoked_one = reciprocal.evoke(
        outcome_one.causal_settlement,
        cue_senses=("sight", "touch"),
    )
    evoked_two = reciprocal.evoke(
        outcome_two.causal_settlement,
        cue_senses=("sight", "touch"),
    )
    assert evoked_one.state == evoked_two.state == "unique"
    assert evoked_one.thing_ids == (mosaic_one.thing_id,)
    assert evoked_two.thing_ids == (mosaic_two.thing_id,)
    assert evoked_one.evoked_full_field_roots
    assert evoked_two.evoked_full_field_roots


def test_reciprocal_class_formation_contains_no_signal_comparison_call() -> None:
    tree = ast.parse(inspect.getsource(module))
    forbidden_calls = {
        "argmin",
        "argmax",
        "corrcoef",
        "dot",
        "mean",
        "median",
        "norm",
        "polyfit",
        "searchsorted",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert not forbidden_calls.intersection(called)
