"""Decisive retirement gates for the duplicate historical Embryo authority."""

from __future__ import annotations

import ast
import inspect
import textwrap

from dsf_ai_service.substrate.owner_scoped_persistence import (
    OWNER_STATE_GROUPS,
    PATH_OWNERSHIP_REGISTRY,
    ROLE_RETIRED,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


CORE_GUALA = Guala.__mro__[1]
RETIRED_GRAPH_PATHS = {
    "guala_organism.sgr",
    "guala_organism.sgr.binding.json",
}


def _attribute_assignments(source: str) -> set[str]:
    tree = ast.parse(textwrap.dedent(source))
    result = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign)
                else [node.target]
            )
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                result.add(target.attr)
    return result


def _called_attributes(source: str) -> set[str]:
    tree = ast.parse(textwrap.dedent(source))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }


def test_runtime_constructs_only_the_whole_organism_neuron_authority() -> None:
    assigned = _attribute_assignments(inspect.getsource(CORE_GUALA.__init__))
    assert "organism" not in assigned
    assert "_spike_bus" not in assigned
    assert "_organism_growth_queue" not in assigned
    assert "_causal_organism_growth" not in assigned


def test_runtime_has_no_historical_embryo_mutation_or_reflection_path() -> None:
    source = inspect.getsource(CORE_GUALA)
    calls = _called_attributes(source)
    assert "apply_causal_growth_claim" not in calls
    assert "reflect" not in calls
    assert not hasattr(CORE_GUALA, "_organism_reflect_boundary")
    assert not hasattr(CORE_GUALA, "_organism_worker_loop")
    assert not hasattr(CORE_GUALA, "wire_spike_bus")


def test_historical_organism_graph_is_retired_from_live_persistence() -> None:
    assert RETIRED_GRAPH_PATHS.isdisjoint(
        CORE_GUALA.FULL_SAVE_MANIFEST_FILES
    )
    assert RETIRED_GRAPH_PATHS.isdisjoint(
        CORE_GUALA.HOT_SAVE_MANIFEST_FILES
    )
    assert RETIRED_GRAPH_PATHS.issubset(CORE_GUALA.RETIRED_BOOT_FILES)
    ownership = {
        item.selector: item
        for item in PATH_OWNERSHIP_REGISTRY
        if item.selector in RETIRED_GRAPH_PATHS
    }
    assert set(ownership) == RETIRED_GRAPH_PATHS
    assert all(item.role == ROLE_RETIRED for item in ownership.values())


def test_historical_growth_journal_is_not_an_owner_state_group() -> None:
    assert "causal_organism_growth" not in {
        group.owner_id for group in OWNER_STATE_GROUPS
    }
