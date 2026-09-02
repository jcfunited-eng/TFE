"""Focused custody proofs for continuous resident Guala life."""

from __future__ import annotations

import hashlib
import threading
from types import SimpleNamespace

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.native_organism_binary_store import (
    CommittedNativeOrganismPublicationError,
    PendingNativeOrganismCleanup,
)


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
    monkeypatch.setattr(production, "_pending_custody_cleanup", None)
    monkeypatch.setattr(production, "_pending_custody_candidate", None)
    monkeypatch.setattr(production, "_checkpoint_requested", threading.Event())
    production._checkpoint_requested.set()
    monkeypatch.setattr(production, "_object_store", lambda: object())
    monkeypatch.setattr(
        production,
        "_read_current",
        lambda _root: (
            None if production._restored is None else production._restored.pointer
        ),
    )
    monkeypatch.setattr(
        production,
        "clone_staged_native_organism",
        lambda _candidate: calls.append("clone-stage") or object(),
    )
    monkeypatch.setattr(
        production,
        "_world",
        lambda: SimpleNamespace(
            encoded_snapshot=lambda: calls.append("world-snapshot") or b"world-41"
        ),
    )
    monkeypatch.setattr(
        production,
        "_publish_world_recovery_pair",
        lambda _body_sha, world_body: calls.append("world-pair")
        or {
            "world_state_sha256": hashlib.sha256(world_body).hexdigest(),
            "world_state_bytes": len(world_body),
        },
    )
    monkeypatch.setattr(
        production,
        "_reconcile_world_recovery_store",
        lambda _pointer: calls.append("world-reconcile") or (0, 0),
    )
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
    assert calls == [
        "snapshot",
        "world-snapshot",
        "stage",
        "clone-stage",
        "world-pair",
        "validate",
        "publish",
        "adopt",
        "discard",
        "world-reconcile",
        "refresh",
    ]
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
        lambda _candidate: calls.append("discard"),
    )

    assert production._custodian_cycle() == "superseded"
    assert calls == [
        "snapshot",
        "world-snapshot",
        "stage",
        "clone-stage",
        "world-pair",
        "discard",
        "discard",
        "world-reconcile",
    ]
    assert production._pending_unsealed_intervals == 4


def test_post_current_commit_adopts_once_then_retries_cleanup_only(monkeypatch) -> None:
    calls, checkpoint, organism, predecessor = _mount_cycle(monkeypatch)
    staged = object()
    successor = SimpleNamespace(
        identity=predecessor.identity,
        organism_tick=checkpoint.organism_tick,
        state_sha256=checkpoint.state_sha256,
    )
    published = SimpleNamespace(pointer=successor)
    cleanup = PendingNativeOrganismCleanup(
        store_root=production.STATE_ROOT,
        prior=predecessor,
        successor=successor,
        accounting=SimpleNamespace(),
        max_envelope_bytes=1024,
    )

    def stage(*_args, **_kwargs):
        calls.append("stage")
        return staged

    def publish(*_args, **_kwargs):
        calls.append("publish-committed")
        raise CommittedNativeOrganismPublicationError(
            "CURRENT committed; cleanup pending",
            published=published,
            cleanup=cleanup,
        )

    monkeypatch.setattr(production, "stage_native_organism_state_bytes", stage)
    monkeypatch.setattr(production, "publish_staged_native_organism", publish)
    monkeypatch.setattr(
        production,
        "discard_staged_native_organism",
        lambda _candidate: calls.append("discard"),
    )
    monkeypatch.setattr(
        production,
        "retry_committed_native_organism_cleanup",
        lambda candidate, **_kwargs: calls.append("cleanup")
        if candidate is cleanup
        else None,
    )

    assert production._custodian_cycle() == "checkpointed_cleanup_pending"
    assert calls == [
        "snapshot",
        "world-snapshot",
        "stage",
        "clone-stage",
        "world-pair",
        "validate",
        "publish-committed",
        "adopt",
        "discard",
        "world-reconcile",
        "refresh",
    ]
    assert production._restored.organism is organism
    assert production._restored.pointer is successor
    assert production._pending_unsealed_intervals == 0
    assert production._pending_custody_cleanup is cleanup
    assert production._checkpoint_requested.is_set()

    assert production._custodian_cycle() == "cleanup_completed"
    assert calls[-1] == "cleanup"
    assert calls.count("snapshot") == 1
    assert calls.count("stage") == 1
    assert calls.count("publish-committed") == 1
    assert production._pending_custody_cleanup is None
    assert not production._checkpoint_requested.is_set()


def test_pre_current_retry_reuses_one_prepared_candidate(monkeypatch) -> None:
    calls, checkpoint, organism, predecessor = _mount_cycle(monkeypatch)
    successor = SimpleNamespace(
        identity=predecessor.identity,
        organism_tick=checkpoint.organism_tick,
        state_sha256=checkpoint.state_sha256,
    )
    publication_attempts = 0

    monkeypatch.setattr(
        production,
        "stage_native_organism_state_bytes",
        lambda *_args, **_kwargs: calls.append("stage") or object(),
    )

    def publish(*_args, **_kwargs):
        nonlocal publication_attempts
        publication_attempts += 1
        calls.append("publish")
        if publication_attempts < 3:
            raise OSError("injected pre-CURRENT refusal")
        return SimpleNamespace(pointer=successor)

    monkeypatch.setattr(production, "publish_staged_native_organism", publish)
    monkeypatch.setattr(
        production,
        "discard_staged_native_organism",
        lambda _candidate: calls.append("discard"),
    )

    for expected_attempt in (1, 2):
        try:
            production._custodian_cycle()
        except OSError as error:
            assert "pre-CURRENT" in str(error)
        else:
            raise AssertionError("pre-CURRENT refusal was not surfaced")
        assert publication_attempts == expected_attempt
        assert production._pending_custody_candidate is not None

    assert production._custodian_cycle() == "checkpointed"
    assert publication_attempts == 3
    assert calls.count("snapshot") == 1
    assert calls.count("world-snapshot") == 1
    assert calls.count("stage") == 1
    assert calls.count("world-pair") == 1
    assert calls.count("clone-stage") == 3
    assert calls.count("validate") == 3
    assert calls.count("publish") == 3
    assert calls.count("adopt") == 1
    assert production._pending_custody_candidate is None
    assert production._restored.organism is organism
    assert production._restored.pointer is successor


def test_later_refusal_retains_already_lived_resident_successor(monkeypatch) -> None:
    checkpoint_requested = threading.Event()
    predecessor = SimpleNamespace(organism_tick=40, state_sha256="11" * 32)
    monkeypatch.setattr(production, "_pending_unsealed_intervals", 3)
    monkeypatch.setattr(production, "_pending_chain_predecessor_sha", "11" * 32)
    monkeypatch.setattr(production, "_checkpoint_requested", checkpoint_requested)
    monkeypatch.setattr(production, "_checkpoint_every_intervals", lambda: 4)

    retained = production._retain_already_lived_intake_after_refusal(
        SimpleNamespace(live_organism_tick=44),
        predecessor,
        "live-audiovisual:test",
        RuntimeError("downstream evidence refused"),
    )

    assert retained is True
    assert production._pending_unsealed_intervals == 4
    assert production._pending_chain_predecessor_sha == predecessor.state_sha256
    assert checkpoint_requested.is_set()


def test_refusal_without_a_lived_successor_does_not_claim_retention(monkeypatch) -> None:
    checkpoint_requested = threading.Event()
    predecessor = SimpleNamespace(organism_tick=40, state_sha256="11" * 32)
    monkeypatch.setattr(production, "_pending_unsealed_intervals", 3)
    monkeypatch.setattr(production, "_pending_chain_predecessor_sha", "11" * 32)
    monkeypatch.setattr(production, "_checkpoint_requested", checkpoint_requested)

    retained = production._retain_already_lived_intake_after_refusal(
        SimpleNamespace(live_organism_tick=40),
        predecessor,
        "live-audiovisual:test",
        RuntimeError("native settlement refused"),
    )

    assert retained is False
    assert production._pending_unsealed_intervals == 3
    assert not checkpoint_requested.is_set()
