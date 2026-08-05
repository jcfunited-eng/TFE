from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "dsf_ai_service" / "app.py"

EXPECTED_CURRENT_PRODUCTION_MIGRATIONS = {
    "authenticated_task853_native_resident_cutover_v1",
    "legacy_whole_organism_to_native_exact_v1",
    "native_materialized_fabric_v2_or_v3_to_v4",
    "native_resident_base64_to_raw_glorun_v1",
    "physical_surface_tutoring_conductor_genesis",
    "whole_organism_neuron_population_profile_v1_to_v2",
}


def test_current_production_boot_accepts_only_reviewed_schema_migrations(
) -> None:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    assignments = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name)
            and target.id == "expected_schema_migrations"
            for target in node.targets
        ):
            assignments.append(ast.unparse(node.value))

    assert assignments == [
        "set(_REVIEWED_CURRENT_SCHEMA_MIGRATIONS)"
    ]


def test_current_schema_extension_log_has_no_retired_owner_count() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    assert "authenticated whole-organism current-schema" in source
    assert "authenticated 50-owner current-schema" not in source


def test_one_reviewed_marker_constant_governs_seal_and_readiness() -> None:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    constants = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name)
            and target.id == "_REVIEWED_CURRENT_SCHEMA_MIGRATIONS"
            for target in node.targets
        ):
            constants.append(ast.literal_eval(node.value))

    assert constants == [tuple(sorted(
        EXPECTED_CURRENT_PRODUCTION_MIGRATIONS
    ))]
    source = APP_PATH.read_text(encoding="utf-8")
    assert "set(\n                _REVIEWED_CURRENT_SCHEMA_MIGRATIONS\n            )" in source
    assert "not set(extension_markers).issubset(\n                _REVIEWED_CURRENT_SCHEMA_MIGRATIONS" in source
    assert "not set(migration_markers).issubset(\n            _REVIEWED_CURRENT_SCHEMA_MIGRATIONS" in source
