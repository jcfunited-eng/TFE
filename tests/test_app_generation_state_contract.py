from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import dsf_ai_service.app as app_module
from dsf_ai_service.v4.guala_physical_runtime import Guala


RUNTIME_KEY = (
    "app-current-generation-contract-key-12345678901234567890"
)


def _files(root: Path) -> set[str]:
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    }


def test_app_startup_calls_only_the_current_physical_schema(
    monkeypatch,
    tmp_path,
) -> None:
    calls: list[object] = []

    class PhysicalSchemaOnly:
        _load_successful = True
        _load_errors: list[str] = []
        _guala_identity = ""
        tick = 0

        def load_full_state(self, state_dir: str) -> None:
            calls.append(("load", state_dir))

        def start_autonomous_experience_driver(self) -> dict:
            calls.append("autonomous-experience")
            return {"lifecycle": "running"}

    monkeypatch.setenv("NATIVE_CORE_ENABLED", "0")
    monkeypatch.delenv("FORCE_S3_RESTORE", raising=False)
    monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "_guala", None)
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", False)
    monkeypatch.setattr(app_module, "_physical_byte_authority", None)
    monkeypatch.setattr(app_module, "Guala", PhysicalSchemaOnly)
    monkeypatch.setattr(
        app_module,
        "_embedded_post_boot",
        lambda value: calls.append(("post-boot", value)),
    )

    app_module._gl_init()

    assert isinstance(app_module._guala, PhysicalSchemaOnly)
    assert calls[0] == ("load", str(tmp_path))
    assert calls[1] == "autonomous-experience"
    assert calls[2] == ("post-boot", app_module._guala)
    assert not hasattr(
        app_module,
        "_verified_generation_requires_legacy_pickle_migration",
    )
    source = inspect.getsource(app_module._gl_init)
    assert "allow_authenticated_legacy_pickle" not in source
    assert "legacy_pickle_migration" not in source
    assert "start_causal_play_loop" not in source
    post_boot_source = inspect.getsource(app_module._embedded_post_boot)
    assert "heartbeat" not in post_boot_source


def test_app_startup_rejects_retired_state_without_implicit_migration(
    monkeypatch,
    tmp_path,
) -> None:
    retired = tmp_path / "guala_organism.pkl.gz"
    retired.write_bytes(b"retired executable state")
    calls: list[str] = []

    class PhysicalSchemaOnly:
        def __init__(self) -> None:
            calls.append("construct")

        def load_full_state(self, state_dir: str) -> None:
            calls.append(f"load:{state_dir}")
            raise RuntimeError(
                "retired state requires explicit one-way migration"
            )

    monkeypatch.setenv("NATIVE_CORE_ENABLED", "0")
    monkeypatch.delenv("FORCE_S3_RESTORE", raising=False)
    monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "_guala", None)
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", False)
    monkeypatch.setattr(app_module, "_physical_byte_authority", None)
    monkeypatch.setattr(app_module, "Guala", PhysicalSchemaOnly)

    with pytest.raises(
        RuntimeError,
        match="requires explicit one-way migration",
    ):
        app_module._gl_init()

    assert calls == ["construct", f"load:{tmp_path}"]
    assert app_module._guala is None


def test_current_generation_is_exact_native_state_and_cold_restorable(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    writer = Guala()
    reader = None
    try:
        writer.tick = 73
        writer.save_full_state(
            tmp_path,
            publish_generation=False,
        )
        expected_files = set(writer.FULL_SAVE_MANIFEST_FILES) | {
            writer.IDENTITY_FILE,
        }
        assert _files(tmp_path) == expected_files
        expected_identity = writer._guala_identity
        expected_native_state = writer._native_materialized_fabric_state

        reader = Guala()
        reader.load_full_state(
            tmp_path,
            require_exact_binary=True,
        )
        assert reader._load_successful is True
        assert reader._guala_identity == expected_identity
        assert reader.tick == 73
        assert reader._native_materialized_fabric_state == (
            expected_native_state
        )
        assert reader._causal_thing_mosaic_owner is None
    finally:
        if reader is not None:
            reader.shutdown()
        writer.shutdown()


def test_current_generation_manifest_excludes_retired_cognition() -> None:
    current = set(Guala.FULL_SAVE_MANIFEST_FILES)
    assert current == {"guala_core.json"}
    assert "guala_organism.sgr" not in current
    assert "guala_organism.sgr.binding.json" not in current
    assert not any(path.startswith("owner_state/") for path in current)
    assert not current.intersection(Guala.RETIRED_BOOT_FILES)
    assert not {
        "guala_organism.pkl.gz",
        "guala_tapestry.pkl.gz",
        "events.log",
        "wave_atlas.npz",
    }.intersection(current)


def test_current_core_names_only_the_physical_continuity_contract(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    guala = Guala()
    try:
        guala.save_full_state(
            tmp_path,
            publish_generation=False,
        )
        envelope = json.loads(
            (tmp_path / "guala_core.json").read_text(
                encoding="utf-8"
            )
        )
        assert envelope["data"]["continuity_contract"] == (
            Guala.WHOLE_ORGANISM_STATE_CONTRACT
        )
        assert set(envelope["data"]["organism_state"]) == {
            "native_materialized_fabric",
            "schema",
        }
        encoded = (
            tmp_path / "guala_core.json"
        ).read_bytes().lower()
        for forbidden in (
            b"pickle",
            b"chi_atlas",
            b"binding_atlas",
            b"wave_atlas",
            b"languagekrimelack",
        ):
            assert forbidden not in encoded
    finally:
        guala.shutdown()
