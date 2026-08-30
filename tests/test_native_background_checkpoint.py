"""Focused custody proofs for continuous resident Guala life."""

from __future__ import annotations

import hashlib
import threading
from types import SimpleNamespace

from dsf_ai_service import native_production_app as production


class _Checkpoint:
    def __init__(self, body: bytes, tick: int) -> None:
        self._body = body
        self.organism_tick = tick
        self.state_bytes = len(body)
        self.state_sha256 = hashlib.sha256(body).hexdigest()

    def encoded_generation(self) -> bytes:
        return self._body


class _Snapshot:
    def __init__(self, checkpoint: _Checkpoint) -> None:
        self._checkpoint = checkpoint
        self.organism_tick = checkpoint.organism_tick

    def prepare_checkpoint(self) -> _Checkpoint:
        return self._checkpoint


class _Organism:
    def __init__(self, snapshot: _Snapshot, calls: list[str]) -> None:
        self._snapshot = snapshot
        self._calls = calls

    def snapshot_lived_state(self) -> _Snapshot:
        self._calls.append("snapshot")
        return self._snapshot

    def validate_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        assert checkpoint is self._snapshot._checkpoint
        self._calls.append("validate")

    def adopt_published_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        assert checkpoint is self._snapshot._checkpoint
        self._calls.append("adopt")


def _mount_cycle(monkeypatch):
    calls: list[str] = []
    body = b"GLORUN01-background-checkpoint"
    checkpoint = _Checkpoint(body, 41)
    organism = _Organism(_Snapshot(checkpoint), calls)
    predecessor = SimpleNamespace(
        identity="12345678-9abc-4def-8123-456789abcdef",
        organism_tick=40,
        state_sha256="11" * 32,
    )
    admission = SimpleNamespace(
        max_envelope_bytes=1024,
        max_fabric_bytes=1024,
        max_logical_peak_bytes=4096,
    )
    monkeypatch.setattr(
        production,
        "_restored",
        production.RestoredNativeOrganism(organism=organism, pointer=predecessor),
    )
    monkeypatch.setattr(production, "_admission", admission)
    monkeypatch.setattr(production, "_pending_unsealed_intervals", 4)
    monkeypatch.setattr(production, "_pending_chain_predecessor_sha", "11" * 32)
    monkeypatch.setattr(production, "_custody_trajectory_epoch", 7)
    monkeypatch.setattr(production, "_last_custodian_evidence", None)
    monkeypatch.setattr(production, "_checkpoint_requested", threading.Event())
    production._checkpoint_requested.set()
    monkeypatch.setattr(production, "_object_store", lambda: object())
    monkeypatch.setattr(
        production,
        "_refresh_public_observation_cache",
        lambda: calls.append("refresh"),
    )
    return calls, checkpoint, organism, predecessor


def test_custodian_publishes_then_adopts_the_same_exact_checkpoint(monkeypatch) -> None:
    calls, checkpoint, organism, predecessor = _mount_cycle(monkeypatch)
    staged = object()
    successor = SimpleNamespace(
        identity=predecessor.identity,
        organism_tick=checkpoint.organism_tick,
        state_sha256=checkpoint.state_sha256,
    )

    def stage(*_args, **kwargs):
        assert kwargs["organism_tick"] == checkpoint.organism_tick
        calls.append("stage")
        return staged

    def publish(candidate, **kwargs):
        assert candidate is staged
        assert kwargs["expected_predecessor_sha256"] == predecessor.state_sha256
        calls.append("publish")
        return SimpleNamespace(pointer=successor)

    monkeypatch.setattr(production, "stage_native_organism_state_bytes", stage)
    monkeypatch.setattr(production, "publish_staged_native_organism", publish)
    monkeypatch.setattr(
        production,
        "discard_staged_native_organism",
        lambda _staged: calls.append("discard"),
    )

    assert production._custodian_cycle() == "checkpointed"
    assert calls == ["snapshot", "stage", "validate", "publish", "adopt", "refresh"]
    assert production._restored.organism is organism
    assert production._restored.pointer is successor
    assert production._pending_unsealed_intervals == 0
    assert production._checkpoint_requested.is_set() is False


def test_custodian_discards_a_snapshot_from_an_abandoned_trajectory(monkeypatch) -> None:
    calls, _checkpoint, _organism, _predecessor = _mount_cycle(monkeypatch)
    staged = object()

    def stage(*_args, **_kwargs):
        calls.append("stage")
        production._custody_trajectory_epoch += 1
        return staged

    monkeypatch.setattr(production, "stage_native_organism_state_bytes", stage)
    monkeypatch.setattr(
        production,
        "publish_staged_native_organism",
        lambda *_args, **_kwargs: calls.append("publish"),
    )
    monkeypatch.setattr(
        production,
        "discard_staged_native_organism",
        lambda candidate: calls.append("discard") if candidate is staged else None,
    )

    assert production._custodian_cycle() == "superseded"
    assert calls == ["snapshot", "stage", "discard"]
    assert production._pending_unsealed_intervals == 4
