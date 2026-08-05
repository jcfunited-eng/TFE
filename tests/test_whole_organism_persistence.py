import json
import pytest

from dsf_ai_service.substrate.whole_organism_persistence import (
    WHOLE_ORGANISM_STATE_CONTRACT,
    whole_organism_mutation_root,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from dsf_ai_service.v4.guala_physical_runtime_core import (
    GualaBootStateIntegrityHalt,
)


def test_mutation_root_uses_the_runtime_native_envelope_contract() -> None:
    assert WHOLE_ORGANISM_STATE_CONTRACT == (
        Guala.WHOLE_ORGANISM_STATE_CONTRACT
    )


def test_lived_state_is_one_exact_cold_restorable_organism(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "whole-organism-test-key-0123456789abcdef0123456789abcdef",
    )
    first = Guala()
    first.save_full_state(str(tmp_path), publish_generation=False)
    first_core = (tmp_path / "guala_core.json").read_bytes()
    first_state = json.loads(first_core)["data"]["organism_state"]

    restored = Guala()
    restored.load_full_state(str(tmp_path))
    restored.save_full_state(str(tmp_path), publish_generation=False)
    restored_core = (tmp_path / "guala_core.json").read_bytes()
    restored_state = json.loads(restored_core)["data"]["organism_state"]

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "guala_core.json",
        "guala_identity.json",
    ]
    assert restored_state == first_state
    assert whole_organism_mutation_root(restored_core) == (
        whole_organism_mutation_root(first_core)
    )
    assert set(restored_state) == {
        "native_materialized_fabric",
        "schema",
    }
    assert restored_state["schema"] == Guala.NATIVE_EXACT_ORGANISM_SCHEMA


def test_failed_whole_organism_save_leaves_prior_generation_exact(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "whole-organism-failed-save-0123456789abcdef0123456789ab",
    )
    organism = Guala()
    organism.save_full_state(str(tmp_path), publish_generation=False)
    prior = (tmp_path / "guala_core.json").read_bytes()
    original_atomic_write = organism._atomic_write

    def interrupted_write(path, data, fsync=False):
        original_atomic_write(path, data, fsync=fsync)
        raise RuntimeError("simulated whole-organism save interruption")

    monkeypatch.setattr(organism, "_atomic_write", interrupted_write)
    organism.tick += 1
    with pytest.raises(RuntimeError, match="save interruption"):
        organism.save_full_state(str(tmp_path), publish_generation=False)

    assert (tmp_path / "guala_core.json").read_bytes() == prior
    assert not (tmp_path / "guala_core.json.tmp").exists()


def test_changed_whole_organism_bytes_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "whole-organism-tamper-test-0123456789abcdef0123456789",
    )
    organism = Guala()
    organism.save_full_state(str(tmp_path), publish_generation=False)
    core_path = tmp_path / "guala_core.json"
    changed = json.loads(core_path.read_text())
    changed["data"]["tick"] += 1
    core_path.write_text(json.dumps(changed))

    with pytest.raises(GualaBootStateIntegrityHalt):
        Guala().load_full_state(str(tmp_path))
