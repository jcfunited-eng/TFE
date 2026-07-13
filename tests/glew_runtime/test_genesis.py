import hashlib
import json
from pathlib import Path
import sys
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.glew_runtime import field, genesis, l6


PROFILE = (
    ROOT
    / "dsf_ai_service"
    / "glew_runtime"
    / "GLEW_UPSTREAM_PROFILE_v1.json"
)
OLD_PROPOSED_PROFILE = ROOT / "docs" / "Guala_Language_Experience_Weave_v1_0.json"
FIXED_IDENTITY = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _canonical_json(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _fixed_identity(monkeypatch):
    monkeypatch.setattr(genesis.uuid, "uuid4", lambda: FIXED_IDENTITY)


def _file_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != ".generation-store.lock"
    }


def _create(root):
    return genesis.create_clean_genesis(
        root,
        profile_path=PROFILE,
        fixed42_provider=l6,
        field_provider=field,
    )


def _restore(root, identity):
    return genesis.restore_clean_genesis(
        root,
        expected_identity=identity,
        profile_path=PROFILE,
        fixed42_provider=l6,
        field_provider=field,
    )


def _create_and_restore(tmp_path, monkeypatch):
    _fixed_identity(monkeypatch)
    store_root = tmp_path / "glew"
    receipt = _create(store_root)
    restored = _restore(store_root, receipt.identity)
    return receipt, restored, restored.generation.payload(genesis.STATE_FILE)


def test_executable_profile_is_canonical_ratified_and_narrow():
    profile = json.loads(PROFILE.read_text())

    assert PROFILE.read_bytes() == _canonical_json(profile)
    assert profile["schema"] == "glew.upstream.executable_profile.v1"
    assert profile["authority"] == {
        "architecture_status": "ratified_executable",
        "full_glew_language_commit_authority": False,
        "implementation_authority": "upstream_and_field_operator_bundle_only",
    }
    assert profile["ratification"]["status"] == "ratified_executable_bundle"
    assert profile["downstream"]["field_evolution"] == (
        "operator_conformant_no_live_mounted_topology"
    )
    assert profile["downstream"]["full_GLEW_commit"] == "forbidden"
    assert "physical_profile_authority" in profile["field_operator"]["evolution"]


def test_minimal_genesis_is_profile_bound_empty_and_cold_restorable(
    tmp_path, monkeypatch
):
    receipt, restored, state = _create_and_restore(tmp_path, monkeypatch)

    assert receipt == restored.receipt
    assert receipt.identity == str(FIXED_IDENTITY)
    assert receipt.profile_sha256 == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    assert restored.generation.stored_bytes(genesis.PROFILE_FILE) == PROFILE.read_bytes()
    assert set(state) == {
        "checkpoint_kind",
        "disruption_recovery",
        "downstream_field_evolution",
        "faults",
        "field_operator_conformance",
        "fixed42",
        "identity",
        "immutable_facts",
        "memory",
        "mounted_field_topology",
        "open_windows",
        "output",
        "per_port_phase_state",
        "profile_binding",
        "receipt_registry_binding",
        "schema",
        "source_time",
        "structural_facts",
        "structural_time",
    }
    assert state["schema"] == "glew.upstream.genesis.v1"
    assert state["checkpoint_kind"] == "clean_generation_genesis"
    assert state["identity"]["lineage"] == []
    assert state["identity"]["parent_identity"] is None
    assert state["structural_time"] == {"exact_rational": "0/1", "gate_count": 0}
    assert state["source_time"] == {"ports": {}}
    assert state["per_port_phase_state"] == {}
    assert state["open_windows"] == []
    assert state["faults"] == []
    assert state["immutable_facts"] == []
    assert state["memory"] == []
    assert state["output"] == []
    assert state["disruption_recovery"] == {
        "baseline_established": False,
        "disruption_latched": False,
        "recovery_pending": False,
    }


def test_genesis_S_UF_and_R_UF_are_explicit_unknown_not_numeric_zero(
    tmp_path, monkeypatch
):
    _, _, state = _create_and_restore(tmp_path, monkeypatch)

    assert set(state["structural_facts"]) == {"S_UF", "R_UF"}
    for fact in state["structural_facts"].values():
        assert fact["status"] == "unknown"
        assert fact["value"] is None
        assert fact["reason"]


def test_genesis_binds_exact_profile_and_empty_topology_receipts(
    tmp_path, monkeypatch
):
    _, restored, state = _create_and_restore(tmp_path, monkeypatch)
    profile_digest = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    topology_payload = field.field_topology_receipt_payload("empty-genesis", ())
    topology_digest = hashlib.sha256(topology_payload).hexdigest()
    manifest = {
        "profile_binding_sha256": profile_digest,
        "record_digests": [profile_digest, topology_digest],
        "schema": "glew.receipt_registry_binding.v1",
    }

    assert restored.generation.stored_bytes(
        genesis.EMPTY_TOPOLOGY_RECEIPT_FILE
    ) == topology_payload
    assert state["receipt_registry_binding"] == {
        **manifest,
        "manifest_sha256": hashlib.sha256(_canonical_json(manifest)).hexdigest(),
    }


def test_genesis_field_topology_is_exact_zero_without_state_or_event(
    tmp_path, monkeypatch
):
    _, _, state = _create_and_restore(tmp_path, monkeypatch)
    report = field.field_conformance()

    assert state["downstream_field_evolution"] == (
        "operator_conformant_no_live_mounted_topology"
    )
    assert state["field_operator_conformance"] == {
        "schema": "glew.field.operator_conformance.v1",
        "report_sha256": report["report_sha256"],
        "status": "operator_conformant_no_live_mounted_topology",
    }
    assert state["mounted_field_topology"] == {
        "schema": "glew.field.genesis_topology.v1",
        "authority_receipt_sha256": report["empty_genesis"][
            "topology_receipt_sha256"
        ],
        "available": False,
        "dimension": 0,
        "exact_receipt_path": "field/empty_topology_receipt.bin",
        "fiber_dimension": 19,
        "ordered_port_fibers": [],
        "topology_id": "empty-genesis",
    }
    assert "field_state" not in state
    assert "evolution_event" not in state


def test_genesis_records_fixed42_basis_without_fabricating_zero_rows(
    tmp_path, monkeypatch
):
    _, _, state = _create_and_restore(tmp_path, monkeypatch)
    fixed42 = state["fixed42"]

    assert len(fixed42["column_basis"]) == 42
    assert [column["index"] for column in fixed42["column_basis"]] == list(range(42))
    assert fixed42["matrix_shape"] == [0, 42]
    assert fixed42["rows"] == []
    assert fixed42["rank_receipt"] == {
        "n_effective": 42,
        "n_start": 42,
        "pivot_columns": [],
        "rank": 0,
        "row_count": 0,
    }
    assert fixed42["evaluation"]["status"] == "unknown_no_lock"
    assert fixed42["evaluation"]["structural_lock"] is None


def test_genesis_contains_no_fixed_or_hash_derived_field_dimension(
    tmp_path, monkeypatch
):
    _, _, state = _create_and_restore(tmp_path, monkeypatch)
    encoded = _canonical_json(state).lower()

    for forbidden in (
        b'"psi"',
        b'"hamiltonian',
        b'"mode_bank"',
        b'"nodes',
        b'"hash_qr',
        b'"integration_steps',
        b'"dimension": 144',
        b'"nodes_per_lane": 24',
    ):
        assert forbidden not in encoded


def test_old_proposed_full_profile_is_rejected_before_mutation(tmp_path):
    store_root = tmp_path / "glew"

    with pytest.raises(
        genesis.GenesisAuthorityError,
        match="not the executable upstream schema",
    ):
        genesis.create_clean_genesis(
            store_root,
            profile_path=OLD_PROPOSED_PROFILE,
            fixed42_provider=l6,
            field_provider=field,
        )

    assert not store_root.exists()


@pytest.mark.parametrize("provider", [None, object()])
def test_missing_operator_providers_fail_before_mutation(tmp_path, provider):
    fixed_root = tmp_path / "fixed"
    field_root = tmp_path / "field"

    with pytest.raises(genesis.GenesisAuthorityError, match="fixed-42"):
        genesis.create_clean_genesis(
            fixed_root,
            profile_path=PROFILE,
            fixed42_provider=provider,
            field_provider=field,
        )
    with pytest.raises(genesis.GenesisAuthorityError, match="field provider"):
        genesis.create_clean_genesis(
            field_root,
            profile_path=PROFILE,
            fixed42_provider=l6,
            field_provider=provider,
        )

    assert not fixed_root.exists()
    assert not field_root.exists()


def test_noncanonical_executable_profile_fails_before_mutation(tmp_path):
    profile = json.loads(PROFILE.read_text())
    noncanonical = tmp_path / "profile.json"
    noncanonical.write_text(json.dumps(profile))
    store_root = tmp_path / "glew"

    with pytest.raises(genesis.GenesisAuthorityError, match="not recursively sorted"):
        genesis.create_clean_genesis(
            store_root,
            profile_path=noncanonical,
            fixed42_provider=l6,
            field_provider=field,
        )

    assert not store_root.exists()


def test_existing_state_is_never_imported_or_overwritten(tmp_path):
    store_root = tmp_path / "glew"
    store_root.mkdir()
    inherited = store_root / "state.json"
    inherited.write_bytes(b'{"schema":"legacy"}\n')

    with pytest.raises(genesis.GenesisStateError, match="never imported"):
        _create(store_root)

    assert inherited.read_bytes() == b'{"schema":"legacy"}\n'
    assert tuple(store_root.iterdir()) == (inherited,)


def test_fixed_identity_produces_identical_manifest_and_state_bytes(
    tmp_path, monkeypatch
):
    _fixed_identity(monkeypatch)
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_receipt = _create(first)
    second_receipt = _create(second)

    assert first_receipt == second_receipt
    assert _file_bytes(first) == _file_bytes(second)


def test_different_identity_is_the_only_entropy_source(tmp_path, monkeypatch):
    identities = iter(
        (
            uuid.UUID("00000000-0000-4000-8000-000000000001"),
            uuid.UUID("00000000-0000-4000-8000-000000000002"),
        )
    )
    monkeypatch.setattr(genesis.uuid, "uuid4", lambda: next(identities))

    first = _create(tmp_path / "first")
    second = _create(tmp_path / "second")

    assert first.identity != second.identity
    assert first.generation_uuid != second.generation_uuid
    assert first.profile_sha256 == second.profile_sha256


def test_cold_restore_rejects_changed_executable_profile(tmp_path, monkeypatch):
    _fixed_identity(monkeypatch)
    store_root = tmp_path / "glew"
    receipt = _create(store_root)
    changed = tmp_path / "changed-profile.json"
    profile = json.loads(PROFILE.read_text())
    profile["version"] = "1.1.1"
    changed.write_bytes(_canonical_json(profile))

    with pytest.raises(genesis.GenesisStateError, match="UUID is not identity-derived"):
        genesis.restore_clean_genesis(
            store_root,
            expected_identity=receipt.identity,
            profile_path=changed,
            fixed42_provider=l6,
            field_provider=field,
        )


def test_cold_restart_rejects_wrong_identity_without_loading_state(
    tmp_path, monkeypatch
):
    _fixed_identity(monkeypatch)
    _create(tmp_path / "glew")

    with pytest.raises(genesis.GenesisStateError, match="identity mismatch"):
        _restore(
            tmp_path / "glew",
            "00000000-0000-4000-8000-000000000099",
        )


def test_cold_restart_missing_root_fails_without_creating_it(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(genesis.GenesisStateError, match="root is missing"):
        _restore(missing, str(FIXED_IDENTITY))

    assert not missing.exists()


def test_cold_restart_rejects_noncanonical_current_bytes(tmp_path, monkeypatch):
    _fixed_identity(monkeypatch)
    receipt = _create(tmp_path / "glew")
    current = tmp_path / "glew" / "CURRENT"
    pointer = json.loads(current.read_text())
    current.chmod(0o644)
    current.write_text(json.dumps(pointer, sort_keys=True) + "\n")
    current.chmod(0o444)

    with pytest.raises(genesis.GenesisStateError, match="not canonical JSON"):
        _restore(tmp_path / "glew", receipt.identity)


def test_strict_discovery_uses_current_only_for_candidate_identity(
    tmp_path, monkeypatch
):
    receipt, restored, _state = _create_and_restore(tmp_path, monkeypatch)

    discovered = genesis.discover_and_restore_clean_genesis(
        tmp_path / "glew",
        profile_path=PROFILE,
        fixed42_provider=l6,
        field_provider=field,
    )

    assert discovered.receipt == receipt
    assert discovered.generation.recovery_certificate_bytes() == (
        restored.generation.recovery_certificate_bytes()
    )


def test_discovery_rejects_noncanonical_current_before_identity_use(
    tmp_path, monkeypatch
):
    _create_and_restore(tmp_path, monkeypatch)
    current = tmp_path / "glew" / "CURRENT"
    pointer = json.loads(current.read_text())
    current.chmod(0o644)
    current.write_text(json.dumps(pointer, sort_keys=True) + "\n")
    current.chmod(0o444)

    with pytest.raises(genesis.GenesisStateError, match="not canonical JSON"):
        genesis.discover_and_restore_clean_genesis(
            tmp_path / "glew",
            profile_path=PROFILE,
            fixed42_provider=l6,
            field_provider=field,
        )
