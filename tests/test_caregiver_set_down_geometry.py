"""Release geometry: a held object is not counted twice at set-down."""
import hashlib

from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedBody, EmbodiedObject, EmbodimentWorldAuthority, PlaceCommand,
    PoseMM, PositionMM, SECOND_BODY_PORT_ID, encode_command,
)


def _world():
    return EmbodimentWorldAuthority(
        authority_key=b"a1-placement-collision-proof-key",
        bodies=(
            EmbodiedBody("guala-body-1", PoseMM(PositionMM(1000, 1000, 0), 0), 250, 800),
            EmbodiedBody("person-body-1", PoseMM(PositionMM(3000, 3000, 0), 0), 250, 800,
                         held_object_id="carried"),
        ),
        initial_objects=(
            EmbodiedObject("carried", 507, 8500, None, held_by_body_id="person-body-1"),
        ),
    )


def _place(world, x):
    return world.execute_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=encode_command(PlaceCommand("carried", PositionMM(x, 3000, 0), 250000)),
        causal_intent_receipt_sha256=hashlib.sha256(str(x).encode()).hexdigest(),
        expected_revision=world.observation_snapshot().revision,
    )


def test_wide_object_release_preserves_clearance_custody_and_restart():
    world = _world()
    before = bytes(world.encoded_snapshot())
    refused = _place(world, 3700)
    assert refused.reason == "place_intersects_body"
    assert bytes(world.encoded_snapshot()) == before

    applied = _place(world, 3800)
    assert applied.reason == "applied"
    snapshot = world.observation_snapshot()
    person = next(body for body in snapshot.bodies if body.body_id == "person-body-1")
    item = next(obj for obj in snapshot.objects if obj.object_id == "carried")
    assert person.held_object_id is None
    assert item.held_by_body_id is None
    assert item.position == PositionMM(3800, 3000, 0)
    assert item.mass_grams == 8500
    assert 800 >= person.radius_mm + item.radius_mm
    encoded = bytes(world.encoded_snapshot())
    restored = _world()
    restored.restore_encoded(encoded)
    assert bytes(restored.encoded_snapshot()) == encoded
    assert _place(restored, 3800).reason == "place_object_not_held"
