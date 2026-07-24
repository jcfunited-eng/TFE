import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from dsf_ai_service.substrate.authoritative_cold_generation_store import (
    AuthoritativeColdGenerationError,
    AuthoritativeColdGenerationStore,
    RETAINED_AUTHORITATIVE_GENERATIONS,
    TRANSIENT_AUTHORITATIVE_GENERATIONS,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    GENERATIONS_DIRECTORY,
)


IDENTITY = "authoritative-cold-test-identity"
REQUIRED_FILES = ("brain.json", "organism.bin")
CAPACITY = 64 * 1024


def _store(
    root: Path,
    *,
    validator=lambda generation: True,
) -> AuthoritativeColdGenerationStore:
    return AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=REQUIRED_FILES,
        max_encoded_generation_bytes=CAPACITY,
        pre_publish_validator=validator,
    )


def _files(root: Path, tick: int) -> dict[str, object]:
    binary = root / f"organism-{tick}.bin"
    binary.write_bytes(f"organism-{tick}".encode("utf-8"))
    return {
        "brain.json": json.dumps({
            "tick": tick,
            "field": {
                "D_k": 0.1,
                "M_k": 0.2,
                "R_rev": 0.3,
                "U_star": 0.4,
                "C_k": 0.5,
                "P_k": 0.6,
                "B_k": 0.7,
                "S_UF": 0.8,
            },
        }).encode("utf-8"),
        "organism.bin": binary,
    }


def _uuid(tick: int) -> str:
    return f"00000000-0000-4000-8000-{tick:012d}"


def test_five_commits_retain_exactly_current_and_predecessor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    states = []
    for tick in range(1, 6):
        states.append(store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        ))
    state = states[-1]
    assert state.current.tick == 5
    assert state.predecessor is not None
    assert state.predecessor.tick == 4
    assert len(state.census) == RETAINED_AUTHORITATIVE_GENERATIONS
    assert sum(item.current for item in state.census) == 1
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(4), _uuid(5)}
    assert store.max_transient_encoded_bytes == (
        TRANSIENT_AUTHORITATIVE_GENERATIONS * CAPACITY
    )
    inspected = store.inspect()
    assert inspected.current.generation_uuid == _uuid(5)
    assert inspected.predecessor is not None
    assert inspected.predecessor.generation_uuid == _uuid(4)


def test_first_generation_is_not_claimed_as_production_ready(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "store")
    state = store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    assert state.predecessor is None
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="no verified predecessor",
    ):
        store.inspect()
    assert store.inspect(require_predecessor=False).current.tick == 1


def test_recurring_current_reference_proof_never_rehashes_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    first = store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    second = store.commit(
        tick=2,
        files=_files(tmp_path, 2),
        generation_uuid=_uuid(2),
    )

    def forbidden_verify(_generation_uuid):
        raise AssertionError("readiness rehashed a generation payload")

    monkeypatch.setattr(
        store._store,
        "verify_generation",
        forbidden_verify,
    )
    assert (
        store.assert_current_reference(second.current)
        is second.current
    )
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="differs from the boot-verified generation",
    ):
        store.assert_current_reference(first.current)


def test_prune_failure_blocks_subsequent_admission_and_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    for tick in (1, 2):
        store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )

    def fail_prune(*args, **kwargs):
        raise OSError("injected prune failure")

    monkeypatch.setattr(store._store, "prune_generations", fail_prune)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="injected prune failure",
    ):
        store.commit(
            tick=3,
            files=_files(tmp_path, 3),
            generation_uuid=_uuid(3),
        )
    assert store.blocked_reason is not None
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="authority is blocked",
    ):
        store.commit(
            tick=4,
            files=_files(tmp_path, 4),
            generation_uuid=_uuid(4),
        )
    assert len(list((root / GENERATIONS_DIRECTORY).iterdir())) == 3

    restarted = _store(root)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="exceeds CURRENT plus predecessor",
    ):
        restarted.inspect()
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="exceeds CURRENT plus predecessor",
    ):
        restarted.commit(
            tick=4,
            files=_files(tmp_path, 4),
            generation_uuid=_uuid(4),
        )
    assert restarted.blocked_reason is not None


def test_oversized_candidate_blocks_without_changing_current(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    before = store.inspect(require_predecessor=False)
    large = tmp_path / "large.bin"
    large.write_bytes(b"x" * CAPACITY)
    files = _files(tmp_path, 2)
    files["organism.bin"] = large
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="encoded-byte capacity",
    ):
        store.commit(
            tick=2,
            files=files,
            generation_uuid=_uuid(2),
        )
    assert store.blocked_reason is not None
    verifier = _store(root)
    after = verifier.inspect(require_predecessor=False)
    assert after.current.generation_uuid == before.current.generation_uuid
    assert len(after.census) == 1


def test_cold_restore_rejection_preserves_current_and_removes_candidate(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    accepted = _store(root)
    accepted.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    current_bytes = (root / "CURRENT").read_bytes()
    tree_before = {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    }
    seen = []

    def reject_unloadable(generation):
        seen.append(generation.payload("brain.json")["tick"])
        return False

    rejecting = _store(root, validator=reject_unloadable)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="failed cold-restore validation",
    ):
        rejecting.commit(
            tick=2,
            files=_files(tmp_path, 2),
            generation_uuid=_uuid(2),
        )
    assert seen == [2]
    assert (root / "CURRENT").read_bytes() == current_bytes
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == tree_before


def test_current_publication_failure_removes_provably_unpublished_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    current_bytes = (root / "CURRENT").read_bytes()

    def fail_before_pointer_change(generation):
        raise OSError("injected CURRENT publication failure")

    monkeypatch.setattr(store._store, "_write_current", fail_before_pointer_change)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="injected CURRENT publication failure",
    ):
        store.commit(
            tick=2,
            files=_files(tmp_path, 2),
            generation_uuid=_uuid(2),
        )
    assert (root / "CURRENT").read_bytes() == current_bytes
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1)}


def test_post_pointer_failure_keeps_new_current_for_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    for tick in (1, 2):
        store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )
    real_write_current = store._store._write_current

    def fail_after_pointer_change(generation):
        real_write_current(generation)
        raise OSError("injected post-CURRENT failure")

    monkeypatch.setattr(store._store, "_write_current", fail_after_pointer_change)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="injected post-CURRENT failure",
    ):
        store.commit(
            tick=3,
            files=_files(tmp_path, 3),
            generation_uuid=_uuid(3),
        )
    verifier = _store(root)
    assert verifier._store.load_current().generation_uuid == _uuid(3)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1), _uuid(2), _uuid(3)}


@pytest.mark.parametrize("candidate_tick", [1, 0])
def test_nonmonotonic_tick_is_rejected_before_tree_mutation(
    tmp_path: Path,
    candidate_tick: int,
) -> None:
    root = tmp_path / f"store-{candidate_tick}"
    store = _store(root)
    store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    tree_before = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
    )
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="strictly newer",
    ):
        store.commit(
            tick=candidate_tick,
            files=_files(tmp_path, candidate_tick),
            generation_uuid=_uuid(100 + candidate_tick),
        )
    assert sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
    ) == tree_before


@pytest.mark.parametrize(
    "crash_boundary",
    [
        "after-candidate-rename",
        "during-cold-restore-validation",
        "immediately-before-current-swap",
    ],
)
def test_restart_retires_verified_unpublished_candidate_and_preserves_current(
    tmp_path: Path,
    crash_boundary: str,
) -> None:
    root = tmp_path / crash_boundary
    store = _store(root)
    store.commit(
        tick=2,
        files=_files(tmp_path, 2),
        generation_uuid=_uuid(2),
    )
    store._store.commit(
        tick=3,
        files=_files(tmp_path, 3),
        generation_uuid=_uuid(3),
        publish_current=False,
    )
    current_bytes = (root / "CURRENT").read_bytes()
    restarted = _store(root)
    state = restarted.inspect(require_predecessor=False)
    assert state.current.generation_uuid == _uuid(2)
    assert state.predecessor is None
    assert (root / "CURRENT").read_bytes() == current_bytes
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(2)}


@pytest.mark.parametrize(
    "crash_boundary",
    [
        "first-after-candidate-rename",
        "first-during-cold-restore-validation",
        "first-immediately-before-current-swap",
    ],
)
def test_restart_discards_never_published_first_candidate(
    tmp_path: Path,
    crash_boundary: str,
) -> None:
    root = tmp_path / crash_boundary
    interrupted = _store(root)
    interrupted._store.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(100),
        publish_current=False,
    )
    assert not (root / "CURRENT").exists()

    restarted = _store(root)
    state = restarted.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    assert state.current.generation_uuid == _uuid(1)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1)}


def test_restart_discards_partial_private_build_tree_before_commit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    interrupted = _store(root)
    building = (
        root
        / GENERATIONS_DIRECTORY
        / f".building-{_uuid(100)}"
    )
    building.mkdir()
    (building / "partial.bin").write_bytes(b"partial")

    restarted = _store(root)
    state = restarted.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    assert state.current.generation_uuid == _uuid(1)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1)}


def test_verified_reconciliation_reduces_retain_three_to_exact_two(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    for tick in (1, 2, 3):
        store._store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )
    reconciled = store.reconcile_verified_retention()
    assert reconciled.current.generation_uuid == _uuid(3)
    assert reconciled.predecessor is not None
    assert reconciled.predecessor.generation_uuid == _uuid(2)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(2), _uuid(3)}


def test_legacy_transition_waits_for_exact_real_current_restore(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    validator_calls = []
    store = _store(
        root,
        validator=lambda generation: validator_calls.append(
            generation.generation_uuid
        ),
    )
    for tick in (1, 2, 3):
        store._store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )

    audited = store.inspect_legacy_retention_transition()
    assert validator_calls == []
    assert len(audited.census) == TRANSIENT_AUTHORITATIVE_GENERATIONS
    before = {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    }
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="exact CURRENT engine-restore proof",
    ):
        store.complete_legacy_retention_transition(
            audited_current=audited.current,
            restored_identity=audited.current.identity,
            restored_tick=audited.current.tick + 1,
        )
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == before

    transitioned = store.complete_legacy_retention_transition(
        audited_current=audited.current,
        restored_identity=audited.current.identity,
        restored_tick=audited.current.tick,
    )
    assert validator_calls == []
    assert transitioned.current.generation_uuid == _uuid(3)
    assert transitioned.predecessor is not None
    assert transitioned.predecessor.generation_uuid == _uuid(2)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(2), _uuid(3)}


def test_legacy_transition_refuses_changed_current_after_restore(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    store = _store(root)
    for tick in (1, 2, 3):
        store._store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )
    audited = store.inspect_legacy_retention_transition()
    os.chmod(audited.current.directory / "brain.json", 0o644)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="verification failed",
    ):
        store.complete_legacy_retention_transition(
            audited_current=audited.current,
            restored_identity=audited.current.identity,
            restored_tick=audited.current.tick,
        )
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1), _uuid(2), _uuid(3)}


def test_reconciliation_never_removes_older_loadable_recovery_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    writer = _store(root)
    for tick in (1, 2, 3):
        writer._store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )

    def reject_newest_predecessor(generation):
        return generation.tick != 2

    reconciler = _store(root, validator=reject_newest_predecessor)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="predecessor failed cold-restore validation",
    ):
        reconciler.reconcile_verified_retention()
    assert writer._store.load_current().generation_uuid == _uuid(3)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1), _uuid(2), _uuid(3)}


def test_reconciliation_reverifies_after_validator_before_retirement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    writer = _store(root)
    for tick in (1, 2, 3):
        writer._store.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )

    def mutate_predecessor(generation):
        if generation.tick == 2:
            os.chmod(generation.directory / "brain.json", 0o644)
        return True

    reconciler = _store(root, validator=mutate_predecessor)
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="reconciliation failed",
    ):
        reconciler.reconcile_verified_retention()
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {_uuid(1), _uuid(2), _uuid(3)}


def test_authority_accepts_exact_generation_specific_complete_contracts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "dynamic-store"
    validated_contracts = []

    def validate(generation):
        validated_contracts.append(generation.required_files)
        return True

    store = AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=CAPACITY,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
        pre_publish_validator=validate,
    )
    first = store.commit(
        tick=1,
        files={
            "brain.json": b'{"tick":1}',
            "assets/first.bin": b"first",
        },
        generation_uuid=_uuid(1),
    )
    second = store.commit(
        tick=2,
        files={
            "brain.json": b'{"tick":2}',
            "assets/second.bin": b"second",
            "sounds/voice.audio": b"voice",
        },
        generation_uuid=_uuid(2),
    )
    assert first.current.required_files == (
        "assets/first.bin",
        "brain.json",
    )
    assert second.current.required_files == (
        "assets/second.bin",
        "brain.json",
        "sounds/voice.audio",
    )
    assert second.predecessor is not None
    assert second.predecessor.required_files == (
        "assets/first.bin",
        "brain.json",
    )
    assert validated_contracts == [
        first.current.required_files,
        second.current.required_files,
    ]


def test_concurrent_writers_never_leave_more_than_exact_retention(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    initial = _store(root)
    initial.commit(
        tick=1,
        files=_files(tmp_path, 1),
        generation_uuid=_uuid(1),
    )
    stores = (_store(root), _store(root))
    barrier = threading.Barrier(2)

    def commit_after_barrier(index: int, tick: int):
        barrier.wait()
        try:
            return stores[index].commit(
                tick=tick,
                files=_files(tmp_path, tick),
                generation_uuid=_uuid(tick),
            )
        except AuthoritativeColdGenerationError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(
            lambda pair: commit_after_barrier(*pair),
            ((0, 2), (1, 3)),
        ))
    assert any(result is not None for result in results)
    verifier = _store(root)
    state = verifier.inspect()
    assert len(state.census) == RETAINED_AUTHORITATIVE_GENERATIONS
    assert len(list((root / GENERATIONS_DIRECTORY).iterdir())) == 2


def test_inspect_waits_for_commit_prune_and_audit_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    writer = _store(root)
    for tick in (1, 2):
        writer.commit(
            tick=tick,
            files=_files(tmp_path, tick),
            generation_uuid=_uuid(tick),
        )
    inspector = _store(root)
    prune_entered = threading.Event()
    permit_prune = threading.Event()
    inspect_started = threading.Event()
    inspect_audit_entered = threading.Event()
    real_prune = writer._store.prune_generations
    real_audit = inspector._audit

    def paused_prune(*args, **kwargs):
        prune_entered.set()
        assert permit_prune.wait(timeout=5)
        return real_prune(*args, **kwargs)

    def marked_audit(*args, **kwargs):
        inspect_audit_entered.set()
        return real_audit(*args, **kwargs)

    def run_inspect():
        inspect_started.set()
        return inspector.inspect()

    monkeypatch.setattr(writer._store, "prune_generations", paused_prune)
    monkeypatch.setattr(inspector, "_audit", marked_audit)
    with ThreadPoolExecutor(max_workers=2) as executor:
        commit_future = executor.submit(
            writer.commit,
            tick=3,
            files=_files(tmp_path, 3),
            generation_uuid=_uuid(3),
        )
        assert prune_entered.wait(timeout=5)
        inspect_future = executor.submit(run_inspect)
        assert inspect_started.wait(timeout=5)
        assert not inspect_audit_entered.wait(timeout=0.2)
        permit_prune.set()
        assert commit_future.result(timeout=5).current.tick == 3
        assert inspect_future.result(timeout=5).current.tick == 3


@pytest.mark.parametrize("capacity", [True, False, 0, -1, 1.5, "65536"])
def test_capacity_must_be_positive_integer(
    tmp_path: Path,
    capacity: object,
) -> None:
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="capacity must be a positive integer",
    ):
        AuthoritativeColdGenerationStore(
            tmp_path / str(capacity),
            identity=IDENTITY,
            required_files=REQUIRED_FILES,
            max_encoded_generation_bytes=capacity,
            pre_publish_validator=lambda generation: True,
        )


@pytest.mark.parametrize("validator", [None, False, 7, "restore"])
def test_prepublication_validator_must_be_callable(
    tmp_path: Path,
    validator: object,
) -> None:
    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="validator must be callable",
    ):
        AuthoritativeColdGenerationStore(
            tmp_path / str(validator),
            identity=IDENTITY,
            required_files=REQUIRED_FILES,
            max_encoded_generation_bytes=CAPACITY,
            pre_publish_validator=validator,
        )
