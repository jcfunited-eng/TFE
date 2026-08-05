import threading
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate import physical_byte_ceiling as ceiling_module
from dsf_ai_service.substrate.knowledge_gap_ledger import GapLedger
from dsf_ai_service.substrate.engine_persistence_profile import (
    derived_engine_persistence_profile_bytes,
)
from dsf_ai_service.substrate.deployment_generation import (
    MaterializationError,
    materialize_verified_generation,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
    PhysicalByteCeilingError,
)
from dsf_ai_service.substrate.persistence_consumer import (
    RING_RECEIPT_SEGMENT_MAX_BYTES,
    PersistenceConsumer,
    ring_checkpoint_max_bytes,
    ring_observation_receipt_max_bytes,
)
from dsf_ai_service.substrate.production_storage_profile import (
    ProductionStorageProfile,
    ProductionStorageProfileError,
)
from dsf_ai_service.substrate.reading_prediction_ledger import (
    ReadingPredictionLedger,
)


def _profile_environment():
    return {
        "GUALA_MAX_COLD_GENERATION_BYTES": "1000",
    }


def test_production_profile_derives_every_nonengine_capacity():
    profile = ProductionStorageProfile.from_environment(
        _profile_environment())

    assert profile.max_live_recovery_generation_bytes == 1000
    assert (
        profile.ring_event_record_bytes
        == ring_observation_receipt_max_bytes()
    )
    assert profile.ring_event_segment_bytes == RING_RECEIPT_SEGMENT_MAX_BYTES
    assert profile.ring_checkpoint_bytes == ring_checkpoint_max_bytes()
    assert profile.engine_persistence_profile_bytes == (
        derived_engine_persistence_profile_bytes(1000)
    )
    assert profile.nonengine_ceiling_bytes == sum(
        profile.nonengine_components.values())
    assert profile.namespace_ceiling_bytes == sum(
        profile.components().values())
    assert profile.namespace_ceiling_bytes == (
        profile.nonengine_ceiling_bytes
        + derived_engine_persistence_profile_bytes(1000)
    )


def test_production_profile_only_requires_cold_capacity():
    environment = _profile_environment()
    del environment["GUALA_MAX_COLD_GENERATION_BYTES"]

    with pytest.raises(
            ProductionStorageProfileError,
            match="GUALA_MAX_COLD_GENERATION_BYTES"):
        ProductionStorageProfile.from_environment(environment)


def test_legacy_nonengine_environment_guesses_are_not_authoritative():
    environment = _profile_environment()
    baseline = ProductionStorageProfile.from_environment(environment)
    environment.update({
        "GUALA_MAX_LIVE_RECOVERY_GENERATION_BYTES": "1",
        "GUALA_RING_EVENT_RECORD_BYTES": "1",
        "GUALA_RING_CHECKPOINT_BYTES": "1",
        "GUALA_KNOWLEDGE_GAP_LEDGER_BYTES": "1",
        "GUALA_READING_PREDICTION_LEDGER_BYTES": "1",
        "GUALA_DEPLOYMENT_METADATA_PEAK_BYTES": "1",
        "GUALA_OWNER_RECORD_BYTES": "1",
        "GUALA_AUTHORITY_METADATA_BYTES": "1",
    })
    derived = ProductionStorageProfile.from_environment(environment)

    assert derived == baseline


def test_atomic_replace_failure_preserves_prior_bytes_and_removes_temporary(
        tmp_path, monkeypatch):
    authority = PhysicalByteCeilingAuthority(tmp_path, 1_000_000)
    target = tmp_path / "ledger.json"
    target.write_bytes(b"authoritative-prior")
    used_before = authority.used_bytes()
    real_replace = ceiling_module.os.replace

    def reject_target(source, destination):
        if destination == target:
            raise OSError("injected replace failure")
        return real_replace(source, destination)

    monkeypatch.setattr(ceiling_module.os, "replace", reject_target)
    with pytest.raises(OSError, match="injected replace failure"):
        authority.atomic_replace_bytes(
            target,
            b"candidate",
            operation="rollback_probe",
        )

    assert target.read_bytes() == b"authoritative-prior"
    assert authority.used_bytes() == used_before
    assert not tuple(tmp_path.glob(".ledger.json.*.tmp"))


def test_concurrent_authorities_admit_only_one_last_remaining_allocation(
        tmp_path):
    ceiling = 4096
    first = PhysicalByteCeilingAuthority(tmp_path, ceiling)
    second = PhysicalByteCeilingAuthority(tmp_path, ceiling)
    allocation = ceiling - first.used_bytes()
    assert allocation > 0
    barrier = threading.Barrier(2)
    results = []
    result_lock = threading.Lock()

    def publish(authority, name):
        barrier.wait()
        try:
            authority.atomic_replace_bytes(
                tmp_path / name,
                b"x" * allocation,
                operation=f"concurrent_{name}",
            )
        except PhysicalByteCeilingError as error:
            result = ("refused", error.receipt)
        else:
            result = ("admitted", name)
        with result_lock:
            results.append(result)

    threads = [
        threading.Thread(target=publish, args=(first, "first.bin")),
        threading.Thread(target=publish, args=(second, "second.bin")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    assert sorted(result[0] for result in results) == [
        "admitted",
        "refused",
    ]
    assert authority_file_count(tmp_path) == 1
    assert first.used_bytes() == ceiling


def authority_file_count(root):
    return sum(
        path.name in {"first.bin", "second.bin"}
        for path in root.iterdir()
    )


class _IdleCursor:
    def read_available(self):
        return []


class _IdleRing:
    def subscribe(self):
        return _IdleCursor()


def test_ring_append_refusal_preserves_the_exact_prior_log(tmp_path):
    authority = PhysicalByteCeilingAuthority(tmp_path, 4096)
    state = tmp_path / "ring"
    consumer = PersistenceConsumer(
        _IdleRing(),
        state,
        lambda: {},
        physical_byte_authority=authority,
        max_event_record_bytes=1024,
        max_checkpoint_bytes=1024,
        max_event_segment_bytes=4096,
        receipt_hmac_key=b"r" * 32,
    )
    consumer.start()
    consumer.stop()
    log = state / "events.log"
    prior = log.read_bytes()
    remaining = authority.status()["remaining_bytes"]
    (tmp_path / "retained.bin").write_bytes(b"x" * remaining)

    with pytest.raises(PhysicalByteCeilingError):
        consumer._write_events(
            [{"seq": 1, "tick": 1, "kind": "probe", "data": {}}]
        )

    assert log.read_bytes() == prior


@pytest.mark.parametrize(
    "ledger_type,record",
    [
        (GapLedger, lambda ledger: ledger.record("x" * 200, "probe")),
        (
            ReadingPredictionLedger,
            lambda ledger: ledger.record(covered=True, hit=True),
        ),
    ],
)
def test_ledger_capacity_refusal_rolls_back_memory_and_disk(
        tmp_path, ledger_type, record):
    authority = PhysicalByteCeilingAuthority(tmp_path, 1_000_000)
    ledger = ledger_type(
        tmp_path,
        physical_byte_authority=authority,
        max_encoded_bytes=16,
    )

    with pytest.raises(RuntimeError, match="configured byte capacity"):
        record(ledger)

    if isinstance(ledger, GapLedger):
        assert ledger.status()["n_gaps"] == 0
        assert not (tmp_path / "knowledge_gaps.json").exists()
    else:
        assert ledger.status()["curve"] == []
        assert not (tmp_path / "reading_predictions.json").exists()


def test_materialization_refusal_preserves_prior_active_tree(tmp_path):
    scope = tmp_path / "scope"
    scope.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    payload = b"verified-generation-payload"
    (source / "core.bin").write_bytes(payload)
    store = ImmutableGenerationStore(
        scope / "sealed",
        identity="materialization-capacity-test",
        required_files=("core.bin",),
    )
    generation = store.commit(
        tick=1,
        files={"core.bin": source / "core.bin"},
    )
    active = scope / "active"
    active.mkdir()
    (active / "core.bin").write_bytes(b"prior-active-state")
    authority = PhysicalByteCeilingAuthority(scope, 1_000_000)
    requested = len(payload)
    remaining = authority.status()["remaining_bytes"]
    filler = scope / "retained-learned-state.bin"
    filler.write_bytes(b"x" * (remaining - requested + 1))

    with pytest.raises(PhysicalByteCeilingError):
        materialize_verified_generation(
            generation=generation,
            active_directory=active,
            physical_byte_authority=authority,
        )

    assert (active / "core.bin").read_bytes() == b"prior-active-state"
    assert filler.exists()
    assert not tuple(scope.glob(".active.materializing-*"))


def test_materialization_never_deletes_unsealed_runtime_state(tmp_path):
    scope = tmp_path / "scope-runtime-extra"
    scope.mkdir()
    source = tmp_path / "source-runtime-extra"
    source.mkdir()
    (source / "core.bin").write_bytes(b"new")
    store = ImmutableGenerationStore(
        scope / "sealed",
        identity="materialization-runtime-extra-test",
        required_files=("core.bin",),
    )
    generation = store.commit(
        tick=2,
        files={"core.bin": source / "core.bin"},
    )
    active = scope / "active"
    active.mkdir()
    (active / "core.bin").write_bytes(b"old")
    learned_extra = active / "diary.log"
    learned_extra.write_bytes(b"unsealed learned history")
    authority = PhysicalByteCeilingAuthority(scope, 1_000_000)

    with pytest.raises(
            MaterializationError,
            match="would delete unsealed runtime paths"):
        materialize_verified_generation(
            generation=generation,
            active_directory=active,
            physical_byte_authority=authority,
        )

    assert (active / "core.bin").read_bytes() == b"old"
    assert learned_extra.read_bytes() == b"unsealed learned history"


def test_materialization_retires_only_explicit_predecessor_runtime_paths(
        tmp_path):
    scope = tmp_path / "scope-runtime-retirement"
    scope.mkdir()
    source = tmp_path / "source-runtime-retirement"
    source.mkdir()
    (source / "core.bin").write_bytes(b"new")
    store = ImmutableGenerationStore(
        scope / "sealed",
        identity="materialization-runtime-retirement-test",
        required_files=("core.bin",),
    )
    generation = store.commit(
        tick=3,
        files={"core.bin": source / "core.bin"},
    )
    active = scope / "active"
    active.mkdir()
    (active / "core.bin").write_bytes(b"old")
    (active / "organs_manifest.json").write_text(
        '{"retired":"compatibility-merge"}\n'
    )
    ring = active / "ring_events"
    ring.mkdir()
    (ring / "events.log").write_bytes(b"retired operational receipts\n")
    authority = PhysicalByteCeilingAuthority(scope, 1_000_000)

    result = materialize_verified_generation(
        generation=generation,
        active_directory=active,
        physical_byte_authority=authority,
        retirable_runtime_paths=(
            "organs_manifest.json",
            "ring_events/events.log",
        ),
    )

    assert result.generation_uuid == generation.generation_uuid
    assert (active / "core.bin").read_bytes() == b"new"
    assert not (active / "organs_manifest.json").exists()
    assert not (active / "ring_events").exists()
    assert not tuple(scope.glob(".active.materializing-*"))
    assert not tuple(scope.glob(".active.retired-*"))


def test_materialization_retirement_never_covers_an_undeclared_extra(
        tmp_path):
    scope = tmp_path / "scope-runtime-retirement-refusal"
    scope.mkdir()
    source = tmp_path / "source-runtime-retirement-refusal"
    source.mkdir()
    (source / "core.bin").write_bytes(b"new")
    store = ImmutableGenerationStore(
        scope / "sealed",
        identity="materialization-runtime-retirement-refusal-test",
        required_files=("core.bin",),
    )
    generation = store.commit(
        tick=4,
        files={"core.bin": source / "core.bin"},
    )
    active = scope / "active"
    active.mkdir()
    (active / "core.bin").write_bytes(b"old")
    (active / "organs_manifest.json").write_text("{}\n")
    learned_extra = active / "diary.log"
    learned_extra.write_bytes(b"unsealed learned history")
    authority = PhysicalByteCeilingAuthority(scope, 1_000_000)

    with pytest.raises(MaterializationError, match="diary.log"):
        materialize_verified_generation(
            generation=generation,
            active_directory=active,
            physical_byte_authority=authority,
            retirable_runtime_paths=("organs_manifest.json",),
        )

    assert (active / "core.bin").read_bytes() == b"old"
    assert (active / "organs_manifest.json").exists()
    assert learned_extra.read_bytes() == b"unsealed learned history"
    assert not tuple(scope.glob(".active.materializing-*"))
