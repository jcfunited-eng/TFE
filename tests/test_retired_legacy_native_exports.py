from __future__ import annotations

from pathlib import Path

import guala_core

from tools.package_guala_release import resolve_runtime_closure


ROOT = Path(__file__).resolve().parents[1]
RETIRED_EXPORTS = {
    "krim_feed",
    "biquad_bandpass",
    "cochlear_feed",
    "fovea_feed",
    "fingerprint",
    "compute_dsf",
    "map_inject",
    "psi_settle",
}


def test_legacy_native_installer_and_startup_patch_are_absent():
    assert not (ROOT / "dsf_ai_service/substrate/native_core.py").exists()
    app_source = (ROOT / "dsf_ai_service/app.py").read_text(encoding="utf-8")
    assert "NATIVE_CORE_ENABLED" not in app_source
    assert "native_core.install" not in app_source
    assert "from dsf_ai_service.substrate import native_core" not in app_source


def test_rust_module_does_not_register_retired_exports():
    source = (ROOT / "native/guala_core/src/lib.rs").read_text(
        encoding="utf-8"
    )

    for retired in RETIRED_EXPORTS:
        assert f"wrap_pyfunction!({retired}" not in source
        assert f"fn {retired}(" not in source

    for accepted_registration in (
        "auditory::register(module)?",
        "auditory_reachability::register(module)?",
        "canonical_basin::register(module)?",
        "canonical_l0_l4::register(module)?",
        "content_defined_chunker::register(module)?",
        "full_field_bank::register(module)?",
        "materialized_fabric::register(module)?",
    ):
        assert accepted_registration in source


def test_built_native_module_exposes_no_retired_export():
    for retired in RETIRED_EXPORTS:
        assert not hasattr(guala_core, retired)


def test_release_closure_cannot_reach_retired_oscillator_graph():
    closure = resolve_runtime_closure(
        ROOT,
        ["dsf_ai_service/app.py"],
        ["dsf_ai_service", "ses_core", "uf_core"],
        {
            "app": "dsf_ai_service/app.py",
            "integrity": "dsf_ai_service/integrity.py",
        },
    )

    for retired_path in (
        "dsf_ai_service/substrate/native_core.py",
        "dsf_ai_service/loom_model/neuron.py",
        "dsf_ai_service/loom_model/physical_oscillators.py",
        "dsf_ai_service/loom_model/substrate_dna.py",
        "dsf_ai_service/sensory_krimelacks.py",
        "dsf_ai_service/substrate/krimelack.py",
        "dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py",
    ):
        assert retired_path not in closure
