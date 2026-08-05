"""Anti-resurrection contract for the retired scripted cognition stack."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "dsf_ai_service" / "app.py"
ENGINE_PATH = ROOT / "dsf_ai_service" / "v4" / "gualaloom_v5_engine.py"
RUNNER_PATH = ROOT / "dsf_ai_service" / "substrate_runner.py"
UI_PATH = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
NATIVE_APP_PATH = ROOT / "dsf_ai_service" / "native_production_app.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(_source(path))
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def test_retired_python_cognition_engine_cannot_return() -> None:
    assert not ENGINE_PATH.exists()


def test_retired_text_and_teaching_functions_are_absent() -> None:
    app_source = _source(APP_PATH)
    app_functions = _function_names(APP_PATH)
    assert app_functions.isdisjoint(
        {
            "gualaloom_chat",
            "admin_force_reading",
            "load_corpus",
            "teacher_correction",
            "embodied_companion_vocalize",
            "_run_converse",
        }
    )
    for retired_surface in (
        "_converse_tasks",
        "_GLEW_ENGINE_ENABLED",
        "LanguageKrimelack",
        "LivingAtlas",
        "DeepAtlas",
        "_WaveAtlas",
    ):
        assert retired_surface not in app_source


def test_runner_has_no_scripted_cognition_command_surface() -> None:
    runner_source = _source(RUNNER_PATH)
    for retired_surface in (
        "retired_command =",
        '"/bundle:"',
        '"force_reading"',
        '"load_corpus"',
        '"teacher_correction"',
        "handle_retired_scripted_cognition",
    ):
        assert retired_surface not in runner_source


def test_live_ui_has_no_scripted_actuator_or_semantic_teaching_surface() -> None:
    ui_source = _source(UI_PATH)
    for forbidden in (
        "speechSynthesis",
        "SpeechSynthesisUtterance",
        "AudioContext",
        "createBuffer(",
        "/api/v1/teacher/feedback",
        "/api/v1/teacher/correction",
        "/api/v1/gualaloom/upload/book",
        "/addpdf:",
        "/api/v1/auditory/observations",
    ):
        assert forbidden not in ui_source
    assert 'const OBSERVATION_ROUTE="/api/v1/guala/native-observation"' in ui_source
    assert 'const OBSERVATION_SCHEMA="guala.native.public_observation.v1"' in ui_source
    assert "renderArticulation(value.articulation)" in ui_source
    assert "No native learned articulation supplied" in ui_source


def test_native_serving_does_not_import_retired_cognition_or_old_app() -> None:
    source = _source(NATIVE_APP_PATH)
    for forbidden in (
        "from dsf_ai_service.app import",
        "guala_physical_runtime",
        "generation_store",
        "owner_lock",
        "gualaloom_v5_engine",
        "speechSynthesis",
    ):
        assert forbidden not in source
    assert '"articulation": _unmounted(' in source
    assert '"no native articulation or emitted-sound transition is mounted"' in source
