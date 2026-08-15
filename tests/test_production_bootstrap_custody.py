"""Production boot may restore learned state but may not fabricate it."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

import dsf_ai_service.app as app_module
import dsf_ai_service.substrate_runner as runner_module


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "dsf_ai_service" / "app.py"
COLD_PROBE_PATH = ROOT / "dsf_ai_service" / "cold_restore_probe.py"
RUNNER_PATH = ROOT / "dsf_ai_service" / "substrate_runner.py"


def _function(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _called_attributes(function: ast.FunctionDef) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }


def test_production_and_cold_restore_create_no_scripted_learning() -> None:
    app_source = APP_PATH.read_text(encoding="utf-8")
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")
    cold_source = COLD_PROBE_PATH.read_text(encoding="utf-8")

    for source in (app_source, runner_source, cold_source):
        assert "SEED_CORPORA" not in source
        assert "see spot run" not in source
        assert "Seed Corpus" not in source

    for path, name in ((APP_PATH, "_gl_init"), (COLD_PROBE_PATH, "main")):
        calls = _called_attributes(_function(path, name))
        assert not {
            "add_corpus",
            "load_corpus",
            "read_sentence",
        }.intersection(calls)
        if path == APP_PATH:
            assert "load_full_state" in calls
        else:
            assert "load_full_state" not in calls
            assert "restore_current_native_organism(" in cold_source

    assert "causal sensory tutor not yet connected" not in app_source
    assert "background_curriculum_retired" not in app_source
    assert "curriculum.status()" not in app_source
    assert "native tutoring unavailable" in app_source


def test_sealed_direct_initialization_fails_before_engine_construction(
    monkeypatch,
) -> None:
    constructed = []

    monkeypatch.setattr(app_module, "_guala", None)
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(app_module, "_loaded_generation", None)
    monkeypatch.setattr(
        app_module,
        "Guala",
        lambda *args, **kwargs: constructed.append((args, kwargs)),
    )

    with pytest.raises(
        RuntimeError,
        match="sealed-state generation boot is not complete",
    ):
        app_module._gl_init()

    assert constructed == []


def test_standalone_runner_has_no_mutable_restore_or_identity_heuristic() -> None:
    source = ast.get_source_segment(
        RUNNER_PATH.read_text(encoding="utf-8"),
        _function(RUNNER_PATH, "boot_substrate"),
    )
    assert source is not None
    for forbidden in (
        "FORCE_S3_RESTORE",
        "EXPECTED_IDENTITY",
        "seed_state",
        "best_vocab",
        "list_objects_v2",
        "download_file",
        "load_full_state",
    ):
        assert forbidden not in source

    with pytest.raises(
        RuntimeError,
        match="authenticated immutable generation",
    ):
        runner_module.boot_substrate()


@pytest.mark.parametrize(
    "failing_helper",
    (
        "_mount_embedded_rings",
        "_start_embedded_input_consumer",
    ),
)
def test_required_embedded_transport_failure_propagates(
    monkeypatch,
    failing_helper,
) -> None:
    prior_runner_guala = runner_module._guala

    def admitted(*_args, **_kwargs):
        return None

    def rejected(*_args, **_kwargs):
        raise RuntimeError(f"injected {failing_helper} failure")

    for helper in (
        "_mount_embedded_rings",
        "_start_embedded_input_consumer",
    ):
        monkeypatch.setattr(app_module, helper, admitted)
    monkeypatch.setattr(app_module, failing_helper, rejected)

    try:
        with pytest.raises(
            RuntimeError,
            match=f"injected {failing_helper} failure",
        ):
            app_module._embedded_post_boot(SimpleNamespace())
    finally:
        runner_module._guala = prior_runner_guala
