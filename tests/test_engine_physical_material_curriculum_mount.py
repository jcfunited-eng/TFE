from __future__ import annotations

import hashlib

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    PickCommand,
    encode_command,
)


KEY = "engine-physical-material-curriculum-authority-key"


def test_engine_mounts_physical_material_multi_emitter_and_curriculum(
    monkeypatch,
):
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", KEY)
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    engine = Guala()
    try:
        assert engine._w1_material_physics.status()["material_count"] == 6
        assert engine._w1_multi_emitter_capture.status()["max_causes"] == 2
        curriculum = engine._custody_native_tutoring_curriculum.status()
        assert curriculum["reduced_approximation"] is False
        assert curriculum["full_field_authority_retained_upstream"] is True

        before = engine._embodiment_world.observation_snapshot()
        execution = engine._embodiment_world.execute_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(PickCommand("W1-object-1")),
            causal_intent_receipt_sha256=hashlib.sha256(
                b"engine-material-pick"
            ).hexdigest(),
            expected_revision=before.revision,
        )
        assert execution.disposition == "applied"

        result = engine.experience_oral_material_contact(
            tutor_id="joe",
            nonce="engine-material-contact-0001",
            object_id="W1-object-1",
            contact_area_square_mm=10_000,
        )
        assert result["settlement_state"] == (
            "awaiting_coupled_room_pressure"
        )
        assert result["persistent_learned_state_created"] is False
        assert (
            engine._w1_material_physics.status()["oral_action_sequence"]
            == 1
        )
    finally:
        engine.shutdown()
