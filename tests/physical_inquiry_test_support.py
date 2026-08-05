from __future__ import annotations

import hashlib

from dsf_ai_service.substrate.embodiment_world import (
    PickCommand,
    encode_command,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.test_anonymous_passive_window import _settlement


RUNTIME_KEY = (
    "physical-inquiry-runtime-authority-key-12345678901234567890"
)


def seed_held_thing_and_inquiry(guala: Guala) -> None:
    world = guala._embodiment_world
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=world.port_id,
        command_payload=encode_command(PickCommand(
            object_id="W1-object-1",
            duration_microseconds=100_000,
        )),
        causal_intent_receipt_sha256=hashlib.sha256(
            b"physical-inquiry-test-pick"
        ).hexdigest(),
        expected_revision=before.revision,
    )
    if execution.disposition != "applied":
        raise AssertionError("physical inquiry test pick was not applied")
    mount = guala._w1_physical_evidence.mount_action_outcome(
        execution,
        commit=True,
    )
    custody = guala._settled_prediction_custody(
        mount,
        world_execution=execution,
    )
    guala._admit_settled_embodiment_thing(custody, execution)
    settlement = _settlement(
        "physical-runtime-inquiry",
        receptors=("left-ear", "right-ear"),
        audiovisual=True,
    )
    passive_owner = (
        guala._passive_whole_organism_thing_learning
    )
    guala._passive_whole_organism_thing_learning = None
    try:
        admitted = guala.admit_anonymous_causal_inquiry_window(
            settlement=settlement,
            window_id="physical-runtime-inquiry",
        )
    finally:
        guala._passive_whole_organism_thing_learning = passive_owner
    if (
        admitted["decision_state"] != "silent"
        or admitted["decision_reason"]
        != "awaiting_explicit_tutor_authorization"
    ):
        raise AssertionError(
            "physical inquiry test seed did not remain unresolved"
        )


_seed_held_thing_and_inquiry = seed_held_thing_and_inquiry


__all__ = [
    "RUNTIME_KEY",
    "_seed_held_thing_and_inquiry",
    "seed_held_thing_and_inquiry",
]
