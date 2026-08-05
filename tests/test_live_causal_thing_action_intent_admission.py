from __future__ import annotations

import hashlib
import threading
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.v4.guala_physical_runtime_core import Guala
from tests.test_causal_thing_action_deliberation import (
    KEY,
    _admission_custody,
    _close_relation,
    _closure_receipt,
)
from tests.test_causal_thing_action_intent import _ready_graph
from tests.test_causal_thing_mosaic import (
    ACTION_DURATION_MICROSECONDS,
)


def _brain_from_ready_graph():
    (
        world,
        _sensory,
        _partitions,
        actions,
        deliberation,
        intent_owner,
        _profile,
        first,
        current,
        _partition,
        _resolution,
        custody,
    ) = _ready_graph()
    brain = object.__new__(Guala)
    brain._causal_recognition_attention_owner = custody[
        "recognition_attention_owner"
    ]
    brain._embodied_other_perspective_owner = custody[
        "perspective_owner"
    ]
    brain._causal_thing_action_deliberation = deliberation
    brain._causal_thing_action_intent = intent_owner
    return brain, world, actions, first, current, custody


def _second_action() -> ActionCommand:
    return ActionCommand.embodiment(
        PORT_ID,
        encode_command(MoveCommand(
            PoseMM(PositionMM(1_100, 1_000, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        )),
    )


def test_live_attention_receives_exact_eligible_closure_receipts() -> None:
    brain, world, _actions, _first, current, custody = (
        _brain_from_ready_graph()
    )
    settlement = current.causal_settlement
    roots = full_field_sensory_roots(settlement)
    expected_closure = custody[
        "attention_state"
    ].focused_relation_receipt_sha256
    captured = {}

    class _Neuron:
        @staticmethod
        def has_committed_settlement(_receipt):
            return False

        @staticmethod
        def prepare(_settlement, **_values):
            return "prepared-neuron"

        @staticmethod
        def commit(_prepared):
            return "neuron-undo"

    class _Perspective:
        @staticmethod
        def prepare(**_values):
            return "prepared-perspective"

        @staticmethod
        def commit(_prepared):
            return "perspective-undo"

    class _Recognition:
        @staticmethod
        def prepare(*, context, paths):
            captured["context"] = context
            captured["paths"] = paths
            return "prepared-attention"

        @staticmethod
        def commit(_prepared):
            return None

    class _Paths:
        @staticmethod
        def bind(_receipt):
            return SimpleNamespace(
                contributing_senses=("body", "sight", "touch")
            )

    class _Contexts:
        @staticmethod
        def observe(**values):
            captured["context_values"] = values
            return values

    class _Deliberation:
        @staticmethod
        def eligible_completed_closure_receipts(
            value,
            *,
            cue_senses,
        ):
            captured["settlement"] = value
            captured["cue_senses"] = cue_senses
            return (expected_closure,)

    tapestry = SimpleNamespace(
        observation=SimpleNamespace(
            target_full_field_roots=roots,
            target_time_start=settlement.source_time_start,
            target_time_end=settlement.source_time_end,
            target_mosaic_receipt_sha256="a" * 64,
        ),
        authority_receipt_sha256="b" * 64,
    )
    brain._whole_organism_neuron_population_owner = _Neuron()
    brain._embodied_other_perspective_owner = _Perspective()
    brain._causal_recognition_attention_owner = _Recognition()
    brain._causal_thing_action_deliberation = _Deliberation()
    brain._causal_recognition_path_authority = _Paths()
    brain._whole_organism_attention_context_authority = _Contexts()
    brain._causal_mosaic_tapestry_owner = SimpleNamespace(
        tapestries=(tapestry,),
        status=lambda: {"state": "exact"},
    )
    brain._embodiment_world = world
    brain._physical_internal_body_state = SimpleNamespace(
        state=SimpleNamespace(record=lambda: {"state": "exact"})
    )
    brain._whole_organism_neurochemical_owner = SimpleNamespace(
        status=lambda: {"state": "exact"},
        local_receptor_activations=lambda _settlement: (),
    )
    brain._causal_inquiry_owner = SimpleNamespace(
        status=lambda: {"state": "exact"}
    )

    brain._advance_live_neuron_perspective_attention(settlement)

    observed = frozenset(("body", "sight", "touch"))
    assert captured["settlement"] is settlement
    assert captured["cue_senses"] == tuple(
        sense.value
        for sense in SENSE_ORDER
        if sense.value in observed
    )
    assert captured["context_values"][
        "lawful_action_relation_receipts"
    ] == (expected_closure,)


def test_one_focused_relation_retains_intent_without_execution() -> None:
    brain, world, _actions, _first, current, _custody = (
        _brain_from_ready_graph()
    )
    world_before = world.encoded_snapshot()

    intent = brain._retain_current_causal_thing_action_intent(
        current.causal_settlement
    )

    assert intent is not None
    assert brain._causal_thing_action_intent.verify_live(intent)
    assert (
        brain._causal_thing_action_intent.resolve_live(
            intent.authority_receipt_sha256
        )
        is intent
    )
    assert (
        intent.current_witness.settlement_receipt_sha256
        == current.causal_settlement.authority_receipt_sha256
    )
    assert world.encoded_snapshot() == world_before


def test_multiple_or_unresolved_attention_retains_no_intent() -> None:
    brain, _world, actions, first, current, custody = (
        _brain_from_ready_graph()
    )
    second = _close_relation(
        actions,
        trigger=first.causal_settlement,
        outcome=current.causal_settlement,
        action=_second_action(),
        ordinal=125,
    )
    first_closure = custody[
        "attention_state"
    ].focused_relation_receipt_sha256
    second_closure = _closure_receipt(actions, second.binding_id)
    thing_receipt = (
        brain._causal_thing_action_deliberation
        ._reciprocal.classes()[0].thing_mosaic_receipt_sha256
    )
    multiple = _admission_custody(
        current.causal_settlement,
        thing_mosaic_receipt_sha256=thing_receipt,
        focused_relation_receipt_sha256=first_closure,
        lawful_action_relation_receipts=tuple(sorted(
            (first_closure, second_closure)
        )),
    )
    brain._causal_recognition_attention_owner = multiple[
        "recognition_attention_owner"
    ]
    brain._embodied_other_perspective_owner = multiple[
        "perspective_owner"
    ]
    assert (
        multiple["attention_state"].attention_state
        == "distributed_recognized"
    )
    assert brain._retain_current_causal_thing_action_intent(
        current.causal_settlement
    ) is None
    assert brain._causal_thing_action_intent.status()["live_intents"] == 0

    unresolved = _admission_custody(
        current.causal_settlement,
        thing_mosaic_receipt_sha256=thing_receipt,
        focused_relation_receipt_sha256=hashlib.sha256(
            b"unresolved-live-attention"
        ).hexdigest(),
        unresolved=True,
    )
    brain._causal_recognition_attention_owner = unresolved[
        "recognition_attention_owner"
    ]
    brain._embodied_other_perspective_owner = unresolved[
        "perspective_owner"
    ]
    assert brain._retain_current_causal_thing_action_intent(
        current.causal_settlement
    ) is None
    assert brain._causal_thing_action_intent.status()["live_intents"] == 0


def test_stale_perspective_custody_is_refused_without_intent(
    monkeypatch,
) -> None:
    brain, _world, _actions, _first, current, _custody = (
        _brain_from_ready_graph()
    )
    deliberation = brain._causal_thing_action_deliberation
    original = deliberation.resolve

    def stale_before_verification(settlement, **arguments):
        perspective = brain._embodied_other_perspective_owner
        observation = SimpleNamespace(
            authenticated=True,
            revision=2,
            self_body_id="body:self",
            bodies=(SimpleNamespace(
                body_id="body:self",
                as_record=lambda: {"body_id": "body:self"},
            ),),
            objects=(),
            authority_receipt_sha256=hashlib.sha256(
                b"newer-world-observation"
            ).hexdigest(),
        )
        perspective.commit(perspective.prepare(
            observation=observation,
            access_provenance=(),
        ))
        return original(settlement, **arguments)

    monkeypatch.setattr(
        deliberation,
        "resolve",
        stale_before_verification,
    )
    with pytest.raises(ValueError, match="perspective custody"):
        brain._retain_current_causal_thing_action_intent(
            current.causal_settlement
        )
    assert brain._causal_thing_action_intent.status()["live_intents"] == 0


class _NoMutationOwner:
    def __init__(self, settlement_receipt_sha256: str) -> None:
        self.state = SimpleNamespace(
            settlement_authority_receipt_sha256=(
                settlement_receipt_sha256
            )
        )

    @staticmethod
    def snapshot_encoded():
        return None

    @staticmethod
    def advance(_settlement):
        return None


class _InactiveCausalOwner:
    @staticmethod
    def verify_active_transaction(_settlement):
        return False


def test_settlement_failure_restores_intent_owner_byte_exact() -> None:
    brain, _world, _actions, _first, current, custody = (
        _brain_from_ready_graph()
    )
    settlement = current.causal_settlement
    intent_before = brain._causal_thing_action_intent.snapshot_encoded()

    brain._engine_quiesced = False
    brain._causal_experience_owner = _InactiveCausalOwner()
    brain._full_field_prediction = None
    brain._anonymous_passive_window = None
    brain._causal_inquiry_owner = None
    brain._physical_internal_body_state = None
    brain._whole_organism_recovery_owner = _NoMutationOwner(
        settlement.authority_receipt_sha256
    )
    brain._whole_organism_episode_authority = None
    brain._whole_organism_structural_owner = None
    brain._causal_mosaic_tapestry_owner = None
    brain._organism_dream_wake_weave_owner = None
    brain._whole_organism_neuron_population_owner = None
    brain._whole_organism_neurochemical_owner = _NoMutationOwner(
        settlement.authority_receipt_sha256
    )
    brain._latest_causal_settlement = None
    brain._causal_settlement_accepted = 0
    brain._latest_full_field_prediction_observation = None
    brain._prediction_conditioned_intent_receipt = None
    brain._prediction_conditioned_binding_id = None
    brain._latest_causal_inquiry_observation = None
    brain._latest_whole_organism_episode_resolution = None
    brain._causal_cycle_bridge_lock = threading.RLock()
    brain._synchronize_physical_internal_body_state = (
        lambda _settlement: None
    )
    brain._advance_live_neuron_perspective_attention = (
        lambda _settlement: None
    )
    brain._observe_whole_organism_settlement = (
        lambda _settlement: None
    )
    brain._record_causal_perception_without_dispatch = (
        lambda _settlement, **_values: None
    )
    brain._restore_causal_recognition_attention_snapshot = (
        lambda _encoded: None
    )
    brain._restore_embodied_other_perspective_snapshot = (
        lambda _encoded: None
    )

    def retain_then_fail(value):
        retained = Guala._retain_current_causal_thing_action_intent(
            brain,
            value,
        )
        assert retained is not None
        raise RuntimeError("injected post-intent settlement failure")

    brain._retain_current_causal_thing_action_intent = retain_then_fail
    with pytest.raises(
        RuntimeError,
        match="injected post-intent settlement failure",
    ):
        Guala._accept_causal_settlement(brain, settlement)

    assert (
        brain._causal_thing_action_intent.snapshot_encoded()
        == intent_before
    )
    assert brain._causal_thing_action_intent.status()["live_intents"] == 0
    assert (
        brain._causal_recognition_attention_owner
        is custody["recognition_attention_owner"]
    )
