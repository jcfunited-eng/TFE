from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
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


def test_valid_move_pick_place_are_exact_authenticated_transitions() -> None:
    authority = EmbodimentWorldAuthority(authority_key="embodiment-test-key")
    initial = authority.observation_snapshot()
    assert initial.room_id == "W1"
    assert initial.revision == 0
    assert initial.body.pose.position == PositionMM(1000, 1000, 0)
    assert tuple(item.object_id for item in initial.objects) == ("W1-object-1",)

    pick = _execute(authority, PickCommand("W1-object-1"), intent_number=1)
    assert pick.disposition == "applied"
    assert pick.before == initial
    assert pick.after.revision == 1
    assert pick.after.body.held_object_id == "W1-object-1"
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
    assert moved.after.body.pose == moved_pose
    assert moved.after.body.held_object_id == "W1-object-1"

    placed_position = PositionMM(1800, 1200, 0)
    placed = _execute(
        authority,
        PlaceCommand("W1-object-1", placed_position),
        intent_number=3,
    )
    assert placed.disposition == "applied"
    assert placed.after.revision == 3
    assert placed.after.body.held_object_id is None
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
    assert status["object_count"] == 1
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
        receipt_capacity=64,
        max_encoded_state_bytes=4096,
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
        assert len(byte_bounded.encoded_snapshot()) <= 4096
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
    assert observation.body.body_id == authority.status()["body_id"]
    assert observation.state_sha256
    assert observation.authority_hmac_sha256
    assert observation.authority_receipt_sha256
    with pytest.raises(FrozenInstanceError):
        observation.revision = 99
