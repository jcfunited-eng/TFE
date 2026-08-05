"""Current graph closure and explicit historical-reader contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model import structural_graph_state
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphError,
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas
from tools.guala_legacy_organism_graph_reader import (
    _retired_registry,
    load_authenticated_legacy_organism_graph,
)
from tools.wave_spillover import Cell


ROOT = Path(__file__).resolve().parents[1]
LIMITS = StructuralGraphLimits(
    max_encoded_bytes=256 * 1024 * 1024,
    max_nodes=1_000_000,
    max_depth=256,
)
RETIRED_MODULES = (
    "dsf_ai_service.loom_model.tapestry",
    "tools.wave_spillover",
    "wave_spillover",
)


def _run(code: str, *arguments: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", code, *(str(item) for item in arguments)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_current_graph_roundtrip_never_reaches_retired_modules(
    tmp_path: Path,
) -> None:
    first = tmp_path / "current-first.sgr"
    second = tmp_path / "current-second.sgr"
    result = _run(
        """
import json
import sys
from pathlib import Path
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
limits = StructuralGraphLimits(
    max_encoded_bytes=256 * 1024 * 1024,
    max_nodes=1_000_000,
    max_depth=256,
)
first = Path(sys.argv[1])
second = Path(sys.argv[2])
save_structural_graph(Embryo(brain_seed=42, seed_size=4), first, limits=limits)
restored = load_structural_graph(
    first,
    expected_root_type=Embryo,
    limits=limits,
)
save_structural_graph(restored, second, limits=limits)
retired = [
    name
    for name in sys.modules
    if name in %r
]
print(json.dumps({
    "byte_exact": first.read_bytes() == second.read_bytes(),
    "registry_tags": sorted(structural_registry_contract()),
    "retired_modules": retired,
}))
"""
        % (RETIRED_MODULES,),
        first,
        second,
    )
    assert result["byte_exact"] is True
    assert result["retired_modules"] == []
    assert "tapestry" not in result["registry_tags"]
    assert "wave_cell" not in result["registry_tags"]


def test_historical_types_exist_only_in_explicit_migration_registry(
    tmp_path: Path,
) -> None:
    current_contract = structural_registry_contract()
    assert "tapestry" not in current_contract
    assert "wave_cell" not in current_contract

    _legacy_by_type, legacy_by_tag = _retired_registry()
    assert legacy_by_tag["tapestry"].cls.__module__ == (
        "dsf_ai_service.loom_model.tapestry"
    )
    assert legacy_by_tag["wave_cell"].cls is Cell

    organism = Embryo(brain_seed=42, seed_size=4)
    neuron = organism.brain.hemispheres[0].cluster.neurons[0]
    neuron.binding_atlas = BindingAtlas()
    neuron.binding_atlas.cells = {
        7: Cell(
            bindings=[{"concept": "retired-only"}],
            aggregate_strength=1.0,
            last_tick=3,
        )
    }
    neuron.chi_atlas = ChiAtlas()
    neuron.chi_atlas.record("retired-only", 2, 9, tick=3)

    historical = tmp_path / "historical.sgr"
    current_registry = structural_graph_state._registry
    structural_graph_state._registry = _retired_registry
    try:
        save_structural_graph(organism, historical, limits=LIMITS)
    finally:
        structural_graph_state._registry = current_registry

    rejected = _run(
        """
import json
import sys
from pathlib import Path
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphError,
    StructuralGraphLimits,
    load_structural_graph,
)
limits = StructuralGraphLimits(
    max_encoded_bytes=256 * 1024 * 1024,
    max_nodes=1_000_000,
    max_depth=256,
)
try:
    load_structural_graph(
        Path(sys.argv[1]),
        expected_root_type=Embryo,
        limits=limits,
    )
except StructuralGraphError as error:
    message = str(error)
else:
    raise AssertionError("current reader accepted historical graph")
retired = [
    name
    for name in sys.modules
    if name in %r
]
print(json.dumps({"message": message, "retired_modules": retired}))
"""
        % (RETIRED_MODULES,),
        historical,
    )
    assert rejected == {
        "message": (
            "retired neuronal cognition requires the authenticated "
            "one-way migration reader"
        ),
        "retired_modules": [],
    }

    migrated = load_authenticated_legacy_organism_graph(
        Embryo,
        historical,
    )
    migrated_neuron = (
        migrated.brain.hemispheres[0].cluster.neurons[0]
    )
    assert "binding_atlas" not in migrated_neuron.__dict__
    assert "chi_atlas" not in migrated_neuron.__dict__

    current = tmp_path / "migrated-current.sgr"
    cold = tmp_path / "migrated-cold.sgr"
    save_structural_graph(migrated, current, limits=LIMITS)
    restored = load_structural_graph(
        current,
        expected_root_type=Embryo,
        limits=LIMITS,
    )
    save_structural_graph(restored, cold, limits=LIMITS)
    assert cold.read_bytes() == current.read_bytes()


def test_current_registry_source_has_no_retired_import_edge() -> None:
    source = (
        ROOT
        / "dsf_ai_service"
        / "loom_model"
        / "structural_graph_state.py"
    ).read_text(encoding="utf-8")
    assert "loom_model.tapestry import" not in source
    assert "wave_spillover import" not in source
    assert '"tapestry", LoomTapestry' not in source
    assert '"wave_cell", Cell' not in source

    migration_source = (
        ROOT / "tools" / "guala_legacy_organism_graph_reader.py"
    ).read_text(encoding="utf-8")
    assert "loom_model.tapestry import LoomTapestry" in migration_source
    assert "tools.wave_spillover import Cell" in migration_source
    assert "__all__" in migration_source
    assert '"load_authenticated_legacy_organism_graph"' in (
        migration_source
    )

    one_way_tool_source = (
        ROOT / "tools" / "migrate_guala_physical_state.py"
    ).read_text(encoding="utf-8")
    assert (
        "from tools.guala_legacy_organism_graph_reader import ("
        in one_way_tool_source
    )
    assert (
        "authenticated_legacy_organism_graph"
        in one_way_tool_source
    )
