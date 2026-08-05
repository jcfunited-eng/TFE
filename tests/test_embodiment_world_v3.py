from __future__ import annotations

import base64
import hashlib
import hmac
import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    RETINA_SUBSTREAM_COUNT,
    physical_receptor_substreams,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    V2_ENVELOPE_SCHEMA,
    V2_STATE_DOMAIN,
    V2_STATE_SCHEMA,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)


KEY = b"w1-v3-test-key"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _execute(
    world: EmbodimentWorldAuthority,
    command: MoveCommand | PickCommand | PlaceCommand,
    number: int,
):
    return world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{number:064x}",
        expected_revision=world.observation_snapshot().revision,
    )


def _v2_snapshot() -> bytes:
    source = EmbodimentWorldAuthority(authority_key=KEY)
    observation = source.observation_snapshot()
    objects = []
    for item in observation.objects[:1]:
        record = item.as_record()
        del record["reflectance_ppm"]
        del record["material"]
        del record["optical_surface"]
        objects.append(record)
    bodies = []
    for item in observation.bodies:
        record = item.as_record()
        del record["active_contact"]
        del record["receptor_geometry"]
        bodies.append(record)
    world = {
        "bodies": bodies,
        "objects": objects,
        "revision": 23,
        "room_bounds": observation.regions[0].bounds.as_record(),
        "room_id": "W1",
        "self_body_id": observation.self_body_id,
    }
    payload = {
        "actor_ports": [item.as_record() for item in source.actor_ports],
        "limits": {
            "max_bodies": 4,
            "max_command_bytes": 4096,
            "max_encoded_state_bytes": 2 * 1024 * 1024,
            "max_objects": 8,
            "receipt_capacity": 64,
        },
        "migration_receipt": None,
        "recent_applied_receipts": [],
        "schema": V2_STATE_SCHEMA,
        "world": world,
    }
    payload_bytes = _canonical(payload)
    return _canonical(
        {
            "authority_hmac_sha256": hmac.new(
                KEY,
                V2_STATE_DOMAIN + payload_bytes,
                hashlib.sha256,
            ).hexdigest(),
            "payload_base64": base64.b64encode(payload_bytes).decode("ascii"),
            "schema": V2_ENVELOPE_SCHEMA,
        }
    )


def test_v3_manifest_is_neutral_bounded_physics() -> None:
    world = EmbodimentWorldAuthority(authority_key=KEY)
    observation = world.observation_snapshot()

    assert [item.region_id for item in observation.regions] == [
        "W1-region-A",
        "W1-region-B",
        "W1-region-C",
    ]
    assert [item.portal_id for item in observation.portals] == [
        "W1-portal-1",
        "W1-portal-2",
    ]
    assert [item.object_id for item in observation.objects[:6]] == [
        f"W1-object-{number}" for number in range(1, 7)
    ]
    assert len(observation.objects) == 42
    assert all(
        item.optical_surface is not None
        for item in observation.objects[6:]
    )
    assert observation.regions[0].ceiling_height_mm == 3000
    assert observation.regions[1].ceiling_height_mm is None
    assert observation.regions[2].ceiling_height_mm == 3000
    assert all(len(item.reflectance_ppm) == 6 for item in observation.regions)
    assert all(len(item.illumination_ppm) == 6 for item in observation.regions)
    assert all(len(item.reflectance_ppm) == 6 for item in observation.objects)
    encoded = world.encoded_snapshot()
    assert len(encoded) <= 2 * 1024 * 1024
    assert all(
        term not in encoded.lower()
        for term in (b"home", b"backyard", b"school", b"toy", b"owner")
    )
    assert world.status()["receipt_capacity"] == 16


def test_portals_govern_move_pick_place_without_remote_action() -> None:
    world = EmbodimentWorldAuthority(authority_key=KEY)
    rejected = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(16000, 2500, 0), 0),
            200_000,
        ),
        1,
    )
    assert rejected.disposition == "rejected"
    assert rejected.reason == "move_crosses_disconnected_regions"

    for number, point in enumerate(
        (
            PositionMM(1000, 2500, 0),
            PositionMM(5500, 2500, 0),
            PositionMM(5500, 1500, 0),
            PositionMM(7500, 1000, 0),
        ),
        start=2,
    ):
        assert _execute(
            world,
            MoveCommand(PoseMM(point, 0), 200_000),
            number,
        ).disposition == "applied"
    assert _execute(
        world,
        PickCommand("W1-object-4", 200_000),
        6,
    ).disposition == "applied"
    for number, point in enumerate(
        (
            PositionMM(14000, 1000, 0),
            PositionMM(14000, 2500, 0),
            PositionMM(16000, 2500, 0),
        ),
        start=7,
    ):
        assert _execute(
            world,
            MoveCommand(PoseMM(point, 0), 200_000),
            number,
        ).disposition == "applied"
    placed = _execute(
        world,
        PlaceCommand(
            "W1-object-4",
            PositionMM(16500, 2500, 0),
            200_000,
        ),
        10,
    )
    assert placed.disposition == "applied"
    assert placed.after.room_id == "W1-region-C"
    object_4 = next(
        item
        for item in placed.after.objects
        if item.object_id == "W1-object-4"
    )
    assert object_4.position == PositionMM(16500, 2500, 0)
    assert object_4.held_by_body_id is None


def test_sight_is_a_fixed_retinotopic_photon_field_without_world_ids() -> None:
    world = EmbodimentWorldAuthority(authority_key=KEY)
    before = world.observation_snapshot()
    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 2500, 0), 0),
            200_000,
        ),
        1,
    )
    observed = physical_receptor_substreams(
        before,
        execution.after,
        causal_transition=True,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    sight = observed[PhysicalSense.SIGHT]

    assert len(sight) == RETINA_SUBSTREAM_COUNT == 162
    assert all(
        tuple(axis.axis_id for axis in item.coordinates)
        == ("retinal-row", "retinal-column", "optical-band")
        for item in sight
    )
    assert any(
        item.normalized_signal[0] != item.normalized_signal[1]
        for item in sight
    )
    rendered = repr(sight)
    assert "W1-object" not in rendered
    assert "W1-portal" not in rendered
    assert "body-2" not in rendered


def test_authenticated_v2_state_migrates_once_and_round_trips() -> None:
    encoded = _v2_snapshot()
    world = EmbodimentWorldAuthority(authority_key=KEY)
    world.restore_encoded(encoded)
    observation = world.observation_snapshot()

    assert observation.revision == 24
    assert observation.room_id == "W1-region-A"
    assert len(observation.regions) == 3
    assert len(observation.portals) == 2
    assert len(observation.bodies) == 2
    assert len(observation.objects) == 37
    assert observation.objects[0].position == PositionMM(1500, 1000, 0)
    assert all(
        item.optical_surface is not None
        for item in observation.objects[1:]
    )
    assert world.status()["migration_receipt_sha256"] is not None

    restored = EmbodimentWorldAuthority(authority_key=KEY)
    restored.restore_encoded(world.encoded_snapshot())
    assert restored.observation_snapshot() == observation

    changed = bytearray(encoded)
    changed[-2] = changed[-2] ^ 1
    before = restored.encoded_snapshot()
    with pytest.raises(ValueError):
        restored.restore_encoded(bytes(changed))
    assert restored.encoded_snapshot() == before


def test_v3_hard_limits_reject_expansion() -> None:
    with pytest.raises(ValueError, match="body capacity"):
        EmbodimentWorldAuthority(authority_key=KEY, max_bodies=5)
    with pytest.raises(ValueError, match="object capacity"):
        EmbodimentWorldAuthority(authority_key=KEY, max_objects=65)
    with pytest.raises(ValueError, match="receipt capacity"):
        EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=17)
    with pytest.raises(ValueError, match="command byte capacity"):
        EmbodimentWorldAuthority(authority_key=KEY, max_command_bytes=4097)
    with pytest.raises(ValueError, match="encoded state byte capacity"):
        EmbodimentWorldAuthority(
            authority_key=KEY,
            max_encoded_state_bytes=2 * 1024 * 1024 + 1,
        )


def test_state_byte_capacity_rejects_without_evicting_or_mutating() -> None:
    capacity_probe = EmbodimentWorldAuthority(
        authority_key=KEY,
        receipt_capacity=16,
    )
    probe_genesis_bytes = len(capacity_probe.encoded_snapshot())
    assert _execute(
        capacity_probe,
        MoveCommand(
            PoseMM(PositionMM(1000, 1200, 0), 0),
            200_000,
        ),
        0,
    ).disposition == "applied"
    probe_retained_receipt_bytes = len(capacity_probe.encoded_snapshot())
    derived_capacity = probe_genesis_bytes + (
        probe_retained_receipt_bytes - probe_genesis_bytes
    ) // 2
    assert probe_genesis_bytes < derived_capacity < probe_retained_receipt_bytes

    world = EmbodimentWorldAuthority(
        authority_key=KEY,
        receipt_capacity=16,
        max_encoded_state_bytes=derived_capacity,
    )
    before = world.encoded_snapshot()
    receipt = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1200, 0), 0),
            200_000,
        ),
        1,
    )

    assert receipt.disposition == "rejected"
    assert receipt.reason == "state_capacity_exhausted"
    assert world.encoded_snapshot() == before
    assert world.status()["revision"] == 0
    assert world.status()["retained_applied_receipts"] == 0


def test_ten_thousand_transitions_remain_bounded() -> None:
    world = EmbodimentWorldAuthority(
        authority_key=KEY,
        receipt_capacity=1,
    )
    for number in range(1, 10_001):
        y_mm = 1100 if number % 2 else 1200
        receipt = _execute(
            world,
            MoveCommand(
                PoseMM(PositionMM(1000, y_mm, 0), 0),
                200_000,
            ),
            number,
        )
        assert receipt.disposition == "applied"

    status = world.status()
    assert status["revision"] == 10_000
    assert status["retained_applied_receipts"] == 1
    assert status["object_count"] == 42
    assert status["region_count"] == 3
    assert status["portal_count"] == 2
    assert len(world.encoded_snapshot()) <= 2 * 1024 * 1024
