"""Rejected D3 resurrection bodies must stay outside repository and release."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deploy" / "guala_release_manifest.json"

REJECTED_D3_SOURCES = (
    "native/guala_core/src/chemical_synapse_physics.rs",
    "native/guala_core/src/cognitive_capital_evidence.rs",
    "native/guala_core/src/cognitive_capital_ledger.rs",
    "native/guala_core/src/directed_synapse_recovery.rs",
    "native/guala_core/src/finite_reservoir_neuron_physics.rs",
    "native/guala_core/src/hippocampal_paged_index.rs",
    "native/guala_core/src/joint_physical_source.rs",
    "native/guala_core/src/local_krimelack_transition.rs",
    "native/guala_core/src/neuron_electrical_physics.rs",
    "native/guala_core/src/recursive_cognitive_formation.rs",
    "native/guala_core/src/physical_cognitive_capital.rs",
    "native/guala_core/src/resident_d3_runtime.rs",
    "native/guala_core/src/vestibular_hair_cell_transduction.rs",
)

REJECTED_APPARENT_AUTHORITIES = (
    "docs/GUALA_D3_FINITE_ONE_NEURON_PHYSICAL_CONTINUITY_CANDIDATE_2026-08-04.md",
    "docs/GUALA_D3_LOCAL_THREE_BASIN_KRIMELACK_LAW_2026-08-04.md",
    "docs/GUALA_D3_VESTIBULAR_HAIR_CELL_TRANSDUCTION_LAW_2026-08-04.md",
)


def _release_sources() -> set[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        source
        for category in manifest["categories"]
        for source in category["files"]
    }


def test_rejected_d3_sources_are_absent_and_unshippable() -> None:
    release_sources = _release_sources()
    for relative in REJECTED_D3_SOURCES:
        assert not (ROOT / relative).exists(), relative
        assert relative not in release_sources


def test_rejected_candidate_authorities_are_absent() -> None:
    for relative in REJECTED_APPARENT_AUTHORITIES:
        assert not (ROOT / relative).exists(), relative
