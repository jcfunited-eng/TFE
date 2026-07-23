from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    VocalizeCommand,
    decode_command,
    encode_command,
)


def _intent(number: int) -> str:
    return f"{number:064x}"


def _execute(authority, command, *, intent_number: int, expected_revision: int | None = None):
    observed = authority.observation_snapshot()
    return authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=_intent(intent_number),
        expected_revision=observed.revision if expected_revision is None else expected_revision,
    )


def _body(observation, body_id="guala-body-1"):
    return next(item for item in observation.bodies if item.body_id == body_id)


def _legacy_snapshot(key: str, *, body=None, objects=None, revision=0) -> bytes:
    legacy_body = body or EmbodiedBody(
        body_id="guala-body-1",
        pose=PoseMM(PositionMM(1000, 1000, 0), 0),
        radius_mm=250,
        reach_mm=800,
    )
    legacy_objects = objects or (
        EmbodiedObject(
            object_id="W1-object-1",
            radius_mm=100,
            mass_grams=500,
            position=PositionMM(1500, 1000, 0),
        ),
    )
    payload_value = {
        "limits": {
            "max_command_bytes": 4096,
            "max_encoded_state_bytes": 8 * 1024 * 1024,
            "max_objects": 8,
            "receipt_capacity": 64,
        },
        "port_id": PORT_ID,
        "recent_applied_receipts": [],
        "schema": "guala.embodiment.state.v1",
        "world": {
            "body": legacy_body.as_record(),
            "objects": [
                {
                    key: value
                    for key, value in item.as_record().items()
                    if key != "reflectance_ppm"
                }
                for item in legacy_objects
            ],
            "revision": revision,
            "room_bounds": {
                "maximum": {"x_mm": 5000, "y_mm": 5000, "z_mm": 3000},
                "minimum": {"x_mm": 0, "y_mm": 0, "z_mm": 0},
            },
            "room_id": "W1",
        },
    }
    canonical = lambda value: json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload = canonical(payload_value)
    envelope = {
        "authority_hmac_sha256": hmac.new(
            key.encode("utf-8"),
            b"guala-embodiment-state-v1\0" + payload,
            hashlib.sha256,
        ).hexdigest(),
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": "guala.embodiment.state.hmac.v1",
    }
    return canonical(envelope)


def test_valid_move_pick_place_are_exact_authenticated_transitions() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-test-key")
    initial = authority.observation_snapshot()
    assert initial.room_id == "W1-region-A"
    assert initial.revision == 0
    assert initial.self_body_id == "guala-body-1"
    assert tuple(item.body_id for item in initial.bodies) == (
        "guala-body-1", "w1-body-2"
    )
    assert _body(initial).pose.position == PositionMM(1000, 1000, 0)
    assert tuple(item.object_id for item in initial.objects) == tuple(
        f"W1-object-{number}" for number in range(1, 7)
    )

    pick = _execute(authority, PickCommand("W1-object-1"), intent_number=1)
    assert pick.disposition == "applied"
    assert pick.before == initial
    assert pick.after.revision == 1
    assert pick.actor_body_id == "guala-body-1"
    assert _body(pick.after).held_object_id == "W1-object-1"
    assert pick.after.objects[0].position is None
    assert pick.after.objects[0].held_by_body_id == "guala-body-1"
    assert pick.lifecycle == (
        "received",
        "port_validated",
        "command_decoded",
        "geometry_validated",
        "applied",
    )

    moved_pose = PoseMM(PositionMM(1200, 1200, 0), 90_000)
    moved = _execute(authority, MoveCommand(moved_pose), intent_number=2)
    assert moved.disposition == "applied"
    assert _body(moved.after).pose == moved_pose
    assert _body(moved.after).held_object_id == "W1-object-1"

    placed_position = PositionMM(1800, 1200, 0)
    placed = _execute(
        authority,
        PlaceCommand("W1-object-1", placed_position),
        intent_number=3,
    )
    assert placed.disposition == "applied"
    assert placed.after.revision == 3
    assert _body(placed.after).held_object_id is None
    assert placed.after.objects[0].position == placed_position
    assert placed.after.objects[0].held_by_body_id is None
    assert len({
        pick.authority_receipt_sha256,
        moved.authority_receipt_sha256,
        placed.authority_receipt_sha256,
    }) == 3


@pytest.mark.parametrize(
    ("command", "reason"),
    (
        (MoveCommand(PoseMM(PositionMM(100, 100, 0), 0)), "move_outside_room"),
        (MoveCommand(PoseMM(PositionMM(2000, 1000, 0), 0)), "move_path_intersects_object"),
        (PickCommand("missing-object"), "pick_unknown_object"),
        (PlaceCommand("W1-object-1", PositionMM(1700, 1000, 0)), "place_object_not_held"),
    ),
)
def test_invalid_geometry_rejects_without_any_authority_state_change(command, reason) -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-reject-key")
    before = authority.encoded_snapshot()
    receipt = _execute(authority, command, intent_number=11)
    assert receipt.disposition == "rejected"
    assert receipt.reason == reason
    assert receipt.before == receipt.after
    assert receipt.lifecycle[-2:] == ("geometry_rejected", "rejected")
    assert authority.encoded_snapshot() == before
    assert authority.status()["retained_applied_receipts"] == 0


def test_pick_and_place_enforce_exact_reach_and_collision_geometry() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-geometry-key")
    _execute(authority, PickCommand("W1-object-1"), intent_number=20)

    before = authority.encoded_snapshot()
    out_of_reach = _execute(
        authority,
        PlaceCommand("W1-object-1", PositionMM(2000, 1000, 0)),
        intent_number=21,
    )
    assert out_of_reach.reason == "place_out_of_reach"
    assert authority.encoded_snapshot() == before

    intersects_body = _execute(
        authority,
        PlaceCommand("W1-object-1", PositionMM(1200, 1000, 0)),
        intent_number=22,
    )
    assert intersects_body.reason == "place_intersects_body"
    assert authority.encoded_snapshot() == before


def test_command_language_is_typed_canonical_and_bounded() -> None:
    move = MoveCommand(PoseMM(PositionMM(1100, 1200, 0), 180_000))
    payload = encode_command(move)
    assert decode_command(payload) == move
    vocal = VocalizeCommand(
        epoch_commitment_sha256="a" * 64,
        sequence=3,
        source_sample_start=2_048,
        pcm_sha256="b" * 64,
        sample_count=1_024,
    )
    assert decode_command(encode_command(vocal)) == vocal
    assert payload == json.dumps(
        json.loads(payload),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    authority = EmbodimentWorldAuthority(
        authority_key="embodiment-command-capacity-key",
        max_command_bytes=64,
    )
    before = authority.encoded_snapshot()
    with pytest.raises(ValueError, match="byte boundary"):
        authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=b"x" * 65,
            causal_intent_receipt_sha256=_intent(30),
            expected_revision=0,
        )
    assert authority.encoded_snapshot() == before

    malformed = authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=b"{}",
        causal_intent_receipt_sha256=_intent(31),
        expected_revision=0,
    )
    assert malformed.disposition == "rejected"
    assert malformed.reason == "command_not_canonical"
    assert authority.encoded_snapshot() == before


def test_revision_binding_makes_successful_replay_fail_closed() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-replay-key")
    payload = encode_command(PickCommand("W1-object-1"))
    first = authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=payload,
        causal_intent_receipt_sha256=_intent(40),
        expected_revision=0,
    )
    assert first.disposition == "applied"
    after_first = authority.encoded_snapshot()

    replay = authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=payload,
        causal_intent_receipt_sha256=_intent(40),
        expected_revision=0,
    )
    assert replay.disposition == "rejected"
    assert replay.reason == "stale_world_revision"
    assert authority.encoded_snapshot() == after_first


def test_concurrent_commands_on_one_observed_world_allow_exactly_one_commit() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-concurrency-key")
    barrier = threading.Barrier(3)

    def run(number: int, y: int):
        barrier.wait()
        return authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(
                MoveCommand(PoseMM(PositionMM(1000, y, 0), number * 1000))
            ),
            causal_intent_receipt_sha256=_intent(50 + number),
            expected_revision=0,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, 1, 1200), pool.submit(run, 2, 1400)]
        barrier.wait()
        receipts = [future.result() for future in futures]

    assert sorted(item.disposition for item in receipts) == ["applied", "rejected"]
    rejected = next(item for item in receipts if item.disposition == "rejected")
    assert rejected.reason == "stale_world_revision"
    assert authority.observation_snapshot().revision == 1
    assert len(authority.recent_applied_receipts()) == 1


def test_persistence_round_trip_rejects_tamper_wrong_key_and_noncanonical_envelope() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-persistence-key")
    _execute(authority, PickCommand("W1-object-1"), intent_number=60)
    _execute(
        authority,
        MoveCommand(PoseMM(PositionMM(1200, 1200, 0), 90_000)),
        intent_number=61,
    )
    encoded = authority.encoded_snapshot()

    restored = EmbodimentWorldAuthority(authority_key="embodiment-persistence-key")
    restored.restore_encoded(encoded)
    assert restored.encoded_snapshot() == encoded
    assert restored.observation_snapshot() == authority.observation_snapshot()

    tampered = bytearray(encoded)
    tampered[len(tampered) // 2] ^= 1
    with pytest.raises(ValueError):
        restored.restore_encoded(bytes(tampered))

    wrong_key = EmbodimentWorldAuthority(authority_key="wrong-embodiment-key")
    with pytest.raises(ValueError, match="HMAC"):
        wrong_key.restore_encoded(encoded)

    with pytest.raises(ValueError, match="canonical"):
        restored.restore_encoded(encoded + b" ")


def test_object_inventory_and_retained_receipts_are_strictly_bounded_long_run() -> None:
    second = EmbodiedObject(
        object_id="W1-object-2",
        radius_mm=100,
        mass_grams=500,
        position=PositionMM(2500, 2500, 0),
    )
    with pytest.raises(ValueError, match="inventory"):
        EmbodimentWorldAuthority(
            authority_key="embodiment-object-capacity-key",
            initial_objects=(
                EmbodiedObject(
                    object_id="W1-object-1",
                    radius_mm=100,
                    mass_grams=500,
                    position=PositionMM(1500, 1000, 0),
                ),
                second,
            ),
            max_objects=1,
        )

    authority = EmbodimentWorldAuthority(
        authority_key="embodiment-long-run-key",
        receipt_capacity=4,
    )
    _execute(authority, PickCommand("W1-object-1"), intent_number=70)
    for number in range(1, 301):
        coordinate = 1100 if number % 2 else 1000
        receipt = _execute(
            authority,
            MoveCommand(PoseMM(PositionMM(coordinate, 1000, 0), 0)),
            intent_number=70 + number,
        )
        assert receipt.disposition == "applied"
    status = authority.status()
    assert status["revision"] == 301
    assert status["object_count"] == 6
    assert status["retained_applied_receipts"] == 4
    encoded_size = len(authority.encoded_snapshot())

    for number in range(301, 401):
        coordinate = 1100 if number % 2 else 1000
        _execute(
            authority,
            MoveCommand(PoseMM(PositionMM(coordinate, 1000, 0), 0)),
            intent_number=70 + number,
        )
    assert authority.status()["retained_applied_receipts"] == 4
    assert len(authority.encoded_snapshot()) <= encoded_size + 256

    byte_bounded = EmbodimentWorldAuthority(
        authority_key="embodiment-byte-capacity-key",
        receipt_capacity=1,
        max_encoded_state_bytes=16384,
    )
    _execute(byte_bounded, PickCommand("W1-object-1"), intent_number=600)
    for number in range(1, 20):
        coordinate = 1100 if number % 2 else 1000
        result = _execute(
            byte_bounded,
            MoveCommand(PoseMM(PositionMM(coordinate, 1000, 0), 0)),
            intent_number=600 + number,
        )
        assert result.disposition == "applied"
        assert len(byte_bounded.encoded_snapshot()) <= 16384
    assert byte_bounded.status()["retained_applied_receipts"] == 1


def test_atomic_commit_rolls_back_even_when_baseexception_occurs_after_assignment(monkeypatch) -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-rollback-key")
    before = authority.encoded_snapshot()

    def exploding_commit(candidate):
        authority._state = candidate
        raise KeyboardInterrupt("simulated process-level interruption")

    monkeypatch.setattr(authority, "_commit_authority_state", exploding_commit)
    with pytest.raises(KeyboardInterrupt):
        _execute(authority, PickCommand("W1-object-1"), intent_number=500)
    assert authority.encoded_snapshot() == before


def test_observation_snapshot_is_immutable_and_reports_only_owned_world_truth() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-observation-key")
    observation = authority.observation_snapshot()
    assert observation.room_id == authority.status()["room_id"]
    assert observation.self_body_id == authority.status()["self_body_id"]
    assert len(observation.bodies) == authority.status()["body_count"]
    assert observation.state_sha256
    assert observation.authority_hmac_sha256
    assert observation.authority_receipt_sha256
    with pytest.raises(FrozenInstanceError):
        observation.revision = 99


def test_actor_specific_ports_move_only_their_owned_physical_body() -> None:
    authority = EmbodimentWorldAuthority(authority_key="multi-port-key")
    before = authority.observation_snapshot()
    result = authority.execute_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=encode_command(
            MoveCommand(PoseMM(PositionMM(4000, 4000, 0), 90_000))
        ),
        causal_intent_receipt_sha256=_intent(900),
        expected_revision=before.revision,
    )
    assert result.disposition == "applied"
    assert result.actor_body_id == "w1-body-2"
    assert _body(result.after).pose == _body(before).pose
    assert _body(result.after, "w1-body-2").pose == PoseMM(
        PositionMM(4000, 4000, 0), 90_000
    )

    rejected = authority.execute_port_command(
        port_id="guala.embodiment.w1.unknown",
        command_payload=encode_command(
            MoveCommand(PoseMM(PositionMM(1100, 1000, 0), 0))
        ),
        causal_intent_receipt_sha256=_intent(901),
        expected_revision=result.after.revision,
    )
    assert rejected.reason == "port_mismatch"
    assert rejected.actor_body_id is None
    assert rejected.after == result.after


def test_multi_body_collision_and_holding_reciprocity_fail_closed() -> None:
    bodies = (
        EmbodiedBody(
            "guala-body-1", PoseMM(PositionMM(1000, 1000, 0), 0), 250, 800
        ),
        EmbodiedBody(
            "w1-body-2", PoseMM(PositionMM(2200, 1000, 0), 180_000), 250, 1000
        ),
    )
    objects = (
        EmbodiedObject(
            "W1-object-1", 100, 500, PositionMM(2700, 1000, 0)
        ),
    )
    authority = EmbodimentWorldAuthority(
        authority_key="multi-physics-key",
        bodies=bodies,
        initial_objects=objects,
    )
    collision = _execute(
        authority,
        MoveCommand(PoseMM(PositionMM(3000, 1000, 0), 0)),
        intent_number=910,
    )
    assert collision.reason == "move_path_intersects_body"
    assert collision.before == collision.after

    before = authority.observation_snapshot()
    picked = authority.execute_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=encode_command(PickCommand("W1-object-1")),
        causal_intent_receipt_sha256=_intent(911),
        expected_revision=before.revision,
    )
    assert picked.disposition == "applied"
    assert _body(picked.after, "w1-body-2").held_object_id == "W1-object-1"
    assert picked.after.objects[0].held_by_body_id == "w1-body-2"

    unavailable = _execute(
        authority, PickCommand("W1-object-1"), intent_number=912
    )
    assert unavailable.reason == "pick_object_unavailable"
    assert unavailable.before == unavailable.after

    blocked_place = authority.execute_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=encode_command(
            PlaceCommand("W1-object-1", PositionMM(1200, 1000, 0))
        ),
        causal_intent_receipt_sha256=_intent(913),
        expected_revision=picked.after.revision,
    )
    assert blocked_place.reason == "place_intersects_body"
    assert blocked_place.before == blocked_place.after


def test_concurrent_actor_ports_share_one_exact_world_revision() -> None:
    authority = EmbodimentWorldAuthority(authority_key="multi-concurrency-key")
    barrier = threading.Barrier(3)

    def move(port_id, target, intent):
        barrier.wait()
        return authority.execute_port_command(
            port_id=port_id,
            command_payload=encode_command(MoveCommand(target)),
            causal_intent_receipt_sha256=_intent(intent),
            expected_revision=0,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(
                move,
                PORT_ID,
                PoseMM(PositionMM(1000, 1200, 0), 0),
                920,
            ),
            pool.submit(
                move,
                SECOND_BODY_PORT_ID,
                PoseMM(PositionMM(4000, 4000, 0), 180_000),
                921,
            ),
        )
        barrier.wait()
        results = [item.result() for item in futures]
    assert sorted(item.disposition for item in results) == ["applied", "rejected"]
    assert next(item for item in results if item.disposition == "rejected").reason == "stale_world_revision"
    assert authority.observation_snapshot().revision == 1


def test_authenticated_v1_state_migrates_once_without_rewriting_prior_world() -> None:
    key = "legacy-migration-key"
    encoded = _legacy_snapshot(key, revision=7)
    authority = EmbodimentWorldAuthority(authority_key=key)
    authority.restore_encoded(encoded)
    observed = authority.observation_snapshot()
    assert observed.revision == 8
    assert observed.self_body_id == "guala-body-1"
    assert _body(observed).pose.position == PositionMM(1000, 1000, 0)
    assert _body(observed, "w1-body-2").pose.position == PositionMM(
        4750, 4750, 0
    )
    assert observed.objects[0].position == PositionMM(1500, 1000, 0)
    status = authority.status()
    assert len(status["migration_receipt_sha256"]) == 64
    migrated = authority.encoded_snapshot()
    assert json.loads(migrated)["schema"] == "guala.embodiment.state.hmac.v3"
    restored = EmbodimentWorldAuthority(authority_key=key)
    restored.restore_encoded(migrated)
    assert restored.encoded_snapshot() == migrated
    assert restored.observation_snapshot() == observed


def test_v1_migration_rejects_occupied_added_body_geometry_atomically() -> None:
    key = "legacy-migration-collision-key"
    occupied = (
        EmbodiedObject(
            "W1-object-1", 100, 500, PositionMM(4750, 4750, 0)
        ),
    )
    encoded = _legacy_snapshot(key, objects=occupied)
    authority = EmbodimentWorldAuthority(authority_key=key)
    before = authority.encoded_snapshot()
    with pytest.raises(ValueError, match="cannot settle"):
        authority.restore_encoded(encoded)
    assert authority.encoded_snapshot() == before


def test_body_inventory_and_new_state_are_hard_bounded() -> None:
    bodies = tuple(
        EmbodiedBody(
            f"body-{index}",
            PoseMM(PositionMM(500 + index * 800, 4000, 0), 0),
            100,
            400,
        )
        for index in range(5)
    )
    with pytest.raises(ValueError, match="body inventory"):
        EmbodimentWorldAuthority(
            authority_key="body-capacity-key",
            self_body_id="body-0",
            bodies=bodies,
            max_bodies=4,
        )
    authority = EmbodimentWorldAuthority(authority_key="world-two-mib-key")
    assert len(authority.encoded_snapshot()) <= 2 * 1024 * 1024
    assert authority.status()["body_capacity"] == 4
    assert authority.status()["receipt_capacity"] == 16
