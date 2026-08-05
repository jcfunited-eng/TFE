import json

from dsf_ai_service.substrate.persistence_consumer import (
    LOCAL_CHECKPOINT_RETENTION,
    PersistenceConsumer,
    ring_checkpoint_max_bytes,
    ring_checkpoint_state,
    ring_observation_receipt,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)


HMAC_KEY = b"ring-write-amplification-proof-key"


class _IdleCursor:
    def read_available(self):
        return []


class _IdleRing:
    def subscribe(self):
        return _IdleCursor()


def _event(sequence):
    return {
        "data": {"measurement": sequence},
        "kind": "bounded_observation",
        "seq": sequence,
        "tick": sequence,
    }


def _receipt_bytes(event):
    return (
        json.dumps(
            ring_observation_receipt(event, hmac_key=HMAC_KEY),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def test_sustained_ring_receipts_have_bounded_growth_and_no_orphans(
        tmp_path, monkeypatch):
    authority = PhysicalByteCeilingAuthority(tmp_path, 10 * 1024 * 1024)
    state = tmp_path / "ring"
    segment_bytes = 1024
    consumer = PersistenceConsumer(
        _IdleRing(),
        state,
        lambda: ring_checkpoint_state(250),
        physical_byte_authority=authority,
        max_event_record_bytes=512,
        max_checkpoint_bytes=ring_checkpoint_max_bytes(),
        max_event_segment_bytes=segment_bytes,
        receipt_hmac_key=HMAC_KEY,
    )
    consumer.start()
    steady_base = authority.used_bytes()
    admissions = []
    real_admit = authority.admit

    def tracked_admit(*, operation, requested_bytes):
        receipt = real_admit(
            operation=operation,
            requested_bytes=requested_bytes,
        )
        admissions.append(receipt)
        return receipt

    monkeypatch.setattr(authority, "admit", tracked_admit)
    events = [_event(sequence) for sequence in range(250)]
    logical_receipt_bytes = sum(
        len(_receipt_bytes(event)) for event in events)
    for event in events:
        consumer._write_events([event])
        assert (state / "events.log").stat().st_size <= segment_bytes
        assert len(tuple(state.glob("checkpoint-*.json"))) <= (
            LOCAL_CHECKPOINT_RETENTION)
        assert not tuple(state.rglob("*.tmp"))
        assert not tuple(state.rglob("*.prior"))
        assert not tuple(state.rglob("*.building"))
    consumer.stop()

    positive = [
        receipt for receipt in admissions
        if receipt["requested_bytes"] > 0
    ]
    event_admitted = sum(
        receipt["requested_bytes"]
        for receipt in positive
        if receipt["operation"] == "append_ring_persistence_event"
    )
    checkpoint_admitted = sum(
        receipt["requested_bytes"]
        for receipt in positive
        if receipt["operation"] == "publish_ring_persistence_checkpoint"
    )
    checkpoint_count = sum(
        receipt["operation"] == "publish_ring_persistence_checkpoint"
        for receipt in positive
    )
    assert event_admitted == logical_receipt_bytes
    assert checkpoint_admitted <= (
        checkpoint_count * ring_checkpoint_max_bytes())
    assert max(
        receipt["projected_bytes"] for receipt in admissions
    ) <= (
        steady_base
        + segment_bytes
        + (LOCAL_CHECKPOINT_RETENTION + 1)
        * ring_checkpoint_max_bytes()
    )
    assert authority.used_bytes() <= (
        steady_base
        + segment_bytes
        + LOCAL_CHECKPOINT_RETENTION * ring_checkpoint_max_bytes()
    )
    assert not tuple(state.rglob("*.tmp"))
    assert not tuple(state.rglob("*.prior"))
    assert not tuple(state.rglob("*.building"))
