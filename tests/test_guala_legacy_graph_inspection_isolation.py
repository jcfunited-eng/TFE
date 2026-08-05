"""Regression proof for production legacy-graph inspection isolation."""

import builtins
import importlib
import sys


def test_production_migration_imports_no_retired_cognition(monkeypatch):
    module_name = "tools.guala_legacy_organism_graph_reader"
    retired_prefixes = (
        "dsf_ai_service.loom_model.binding_atlas",
        "dsf_ai_service.loom_model.tapestry",
        "dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6",
        "dsf_ai_service.substrate.retired_legacy_cognition",
        "tools.wave_spillover",
        "wave_constants",
    )
    for name in tuple(sys.modules):
        if name == module_name or name.startswith(retired_prefixes):
            sys.modules.pop(name, None)

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(retired_prefixes):
            raise AssertionError(
                "production migration imported retired cognition: " + name
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    reader = importlib.import_module(module_name)
    by_type, by_tag = reader._inspection_registry()

    assert {
        "binding_atlas",
        "chi_atlas",
        "tapestry",
        "wave_cell",
    }.issubset(by_tag)
    assert len(by_type) == len(by_tag)
    assert not any(
        name.startswith(retired_prefixes)
        for name in sys.modules
    )
