import math

import pytest

from dsf_ai_service.substrate.ring_buffer import (
    InputRing,
    SubstrateRing,
    SubstrateRingCapacityError,
    SubstrateRingOverrunError,
)
from dsf_ai_service.substrate.persistence_consumer import PersistenceConsumer


def _lapped_cursor():
    ring = SubstrateRing(size=4)
    cursor = ring.subscribe()
    for sequence in range(6):
        ring.publish("experience", tick=sequence)
    return cursor


def test_read_available_reports_overrun_without_advancing_cursor():
    cursor = _lapped_cursor()

    with pytest.raises(
        SubstrateRingOverrunError,
        match="exceeded lossless capacity",
    ):
        cursor.read_available()

    assert cursor.behind == 6


def test_read_one_reports_overrun_without_advancing_cursor():
    cursor = _lapped_cursor()

    with pytest.raises(
        SubstrateRingOverrunError,
        match="exceeded lossless capacity",
    ):
        cursor.read_one()

    assert cursor.behind == 6


def test_cursor_delivers_complete_contiguous_retained_sequence():
    ring = SubstrateRing(size=8)
    cursor = ring.subscribe()
    for sequence in range(8):
        ring.publish("experience", tick=sequence)

    events = cursor.read_available()

    assert [event["seq"] for event in events] == list(range(8))
    assert cursor.behind == 0


def test_persistence_consumer_surfaces_ring_overrun(tmp_path):
    ring = SubstrateRing(size=4)
    consumer = PersistenceConsumer(ring, str(tmp_path), lambda: {})
    for sequence in range(6):
        ring.publish("experience", tick=sequence)
    consumer.start()
    consumer._thread.join(1.0)

    with pytest.raises(
        RuntimeError,
        match="persistence consumer failed",
    ) as exc_info:
        consumer.stop(timeout=2.0)

    assert isinstance(exc_info.value.__cause__, SubstrateRingOverrunError)


def test_published_events_do_not_share_caller_mutable_state():
    substrate_ring = SubstrateRing(size=4)
    substrate_cursor = substrate_ring.subscribe()
    substrate_value = ["before"]
    substrate_ring.publish("experience", tick=1, value=substrate_value)

    input_ring = InputRing(size=4)
    input_value = ["before"]
    input_ring.publish(
        "experience_bundle",
        "room",
        value=input_value,
    )

    substrate_value.append("after")
    input_value.append("after")

    assert substrate_cursor.read_one()["data"]["value"] == ["before"]
    retained_input = input_ring.drain()[0]
    assert retained_input["source"] == "room"
    assert retained_input["data"]["value"] == ["before"]


def test_substrate_consumers_receive_private_event_copies():
    ring = SubstrateRing(size=4)
    first = ring.subscribe()
    second = ring.subscribe()
    ring.publish("experience", tick=1, value=["original"])

    first_event = first.read_one()
    first_event["data"]["value"].append("mutated-by-first-consumer")

    assert second.read_one()["data"]["value"] == ["original"]


def test_substrate_event_byte_refusal_preserves_sequence_and_prior_event():
    ring = SubstrateRing(size=4, max_event_record_bytes=128)
    cursor = ring.subscribe()
    ring.publish("probe", tick=1, value="retained")
    published_before = ring._published_seq
    first_before = ring._data[0].copy()

    with pytest.raises(
            SubstrateRingCapacityError,
            match="canonical byte capacity"):
        ring.publish("probe", tick=2, value="x" * 200)

    assert ring._published_seq == published_before
    assert ring._data[0] == first_before
    assert cursor.read_one() == first_before


@pytest.mark.parametrize("invalid_size", [0, -1, 3, True, 4.0])
@pytest.mark.parametrize("ring_type", [SubstrateRing, InputRing])
def test_ring_capacity_must_be_exact_positive_integer_power_of_two(
        ring_type, invalid_size):
    with pytest.raises(
        ValueError,
        match="positive integer power of 2",
    ):
        ring_type(size=invalid_size)


@pytest.mark.parametrize("ring_type", [SubstrateRing, InputRing])
def test_minimum_exact_ring_capacity_is_operational(ring_type):
    ring = ring_type(size=1)

    if ring_type is SubstrateRing:
        cursor = ring.subscribe()
        ring.publish("experience", tick=0)
        assert cursor.read_one()["seq"] == 0
    else:
        ring.publish("wake_signal", "system", marker="minimum-capacity")
        assert ring.drain()[0]["seq"] == 0


@pytest.mark.parametrize(
    ("kind", "tick", "message"),
    [
        (["experience"], 1, "kind must be a nonempty string"),
        ("", 1, "kind must be a nonempty string"),
        ("experience", {"tick": 1}, "tick must be a uint64 integer"),
        ("experience", True, "tick must be a uint64 integer"),
        ("experience", -1, "tick must be a uint64 integer"),
    ],
)
def test_substrate_event_metadata_is_exact_before_sequence_allocation(
        kind, tick, message):
    ring = SubstrateRing(size=4)

    with pytest.raises(ValueError, match=message):
        ring.publish(kind, tick)

    assert ring._published_seq == 0


@pytest.mark.parametrize("source", [["room"], "", " room", "room "])
def test_input_event_source_is_canonical_before_sequence_allocation(source):
    ring = InputRing(size=4)

    with pytest.raises(
        ValueError,
        match="source must be a canonical nonempty string",
    ):
        ring.publish("experience_bundle", source, value="event")

    assert ring.pending == 0
    assert ring.pending_transport_bytes == 0


@pytest.mark.parametrize(
    "payload",
    [b"physical-bytes", math.nan, {"not", "json"}],
)
def test_substrate_payload_is_exact_json_before_sequence_allocation(payload):
    ring = SubstrateRing(size=4)
    cursor = ring.subscribe()

    with pytest.raises(
        ValueError,
        match="not exact finite JSON",
    ):
        ring.publish("experience", tick=1, payload=payload)

    assert ring._published_seq == 0
    assert cursor.read_available() == []
