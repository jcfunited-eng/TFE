"""Authenticated one-way inspection for retired organism graph types.

This module is migration tooling, not part of the physical runtime closure.
The production migration path validates the already hash-bound SQLite graph
without importing, constructing, or executing any retired cognition class.
The older decode helper remains migration-test-only and immediately removes
every retired cognition field from the reconstructed organism.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from dsf_ai_service.loom_model import structural_graph_state
from dsf_ai_service.loom_model.structural_graph_state import ObjectSpec


@dataclass(frozen=True, slots=True)
class LegacyOrganismGraphInspection:
    identity_uuid: str
    node_count: int
    node_type_counts: dict[str, int]
    field_counts: dict[str, int]
    sha256: str
    size_bytes: int


class _RetiredBindingAtlasCarrier:
    """Inert structural carrier; never an active BindingAtlas."""


class _RetiredChiAtlasCarrier:
    """Inert structural carrier; never an active ChiAtlas."""


class _RetiredTapestryCarrier:
    """Inert structural carrier; never an active LoomTapestry."""


class _RetiredWaveCellCarrier:
    """Inert structural carrier; never an active WaveAtlas cell."""


def _registry_with_retired_classes(
    *,
    binding_atlas_type: type,
    chi_atlas_type: type,
    tapestry_type: type,
    wave_cell_type: type,
    **_ignored,
) -> tuple[dict[type, ObjectSpec], dict[str, ObjectSpec]]:
    specs = []
    for spec in structural_graph_state._object_specs(
        include_legacy_coupling_backlog=True,
    ):
        durable_fields = spec.durable_fields
        cls = spec.cls
        if spec.tag == "loom_neuron":
            durable_fields = durable_fields.union(
                {"binding_atlas", "chi_atlas", "_lane_P"}
            )
        elif spec.tag == "embryo":
            durable_fields = durable_fields.union({"_scP"})
        elif spec.tag == "language_krimelack":
            durable_fields = durable_fields.union({"last_input_word"})
        elif spec.tag == "wave_cell":
            cls = wave_cell_type
        specs.append(
            ObjectSpec(
                spec.tag,
                cls,
                durable_fields,
                spec.runtime_fields,
            )
        )
    specs.extend(
        (
            ObjectSpec(
                "wave_cell",
                wave_cell_type,
                structural_graph_state._fields(
                    "bindings aggregate_strength phase_vec "
                    "last_tick saturated"
                ),
            ),
            ObjectSpec(
                "tapestry",
                tapestry_type,
                structural_graph_state._fields(
                    "name n_mosaics seed _tick mosaics "
                    "_engine_prev_word"
                ),
            ),
            ObjectSpec(
                "binding_atlas",
                binding_atlas_type,
                structural_graph_state._fields(
                    "cells _concept_to_chi _lane_bindings "
                    "_lane_concept_shape_to_idx _m_row _m_concepts "
                    "_m_matrix _m_len"
                ),
            ),
            ObjectSpec(
                "chi_atlas",
                chi_atlas_type,
                structural_graph_state._fields("band entries tick"),
            ),
        )
    )
    by_type = {spec.cls: spec for spec in specs}
    by_tag = {spec.tag: spec for spec in specs}
    if len(by_type) != len(specs) or len(by_tag) != len(specs):
        raise structural_graph_state.StructuralGraphError(
            "retired structural class registry is ambiguous"
        )
    return by_type, by_tag


def _inspection_registry(
    **_ignored,
) -> tuple[dict[type, ObjectSpec], dict[str, ObjectSpec]]:
    """Return a complete read-only registry with no retired import edge."""
    return _registry_with_retired_classes(
        binding_atlas_type=_RetiredBindingAtlasCarrier,
        chi_atlas_type=_RetiredChiAtlasCarrier,
        tapestry_type=_RetiredTapestryCarrier,
        wave_cell_type=_RetiredWaveCellCarrier,
    )


def _retired_registry(
    **_ignored,
) -> tuple[dict[type, ObjectSpec], dict[str, ObjectSpec]]:
    """Return the historical decode registry for migration tests only.

    Imports are deliberately local. Production migration performs a database
    census through ``_inspection_registry`` and therefore cannot import or
    reactivate BindingAtlas, ChiAtlas, LoomTapestry, or WaveAtlas mechanics.
    """
    from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
    from dsf_ai_service.loom_model.tapestry import LoomTapestry
    from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas
    from tools.wave_spillover import Cell

    return _registry_with_retired_classes(
        binding_atlas_type=BindingAtlas,
        chi_atlas_type=ChiAtlas,
        tapestry_type=LoomTapestry,
        wave_cell_type=Cell,
    )


def load_authenticated_legacy_organism_graph(
    organism_type: type,
    path: str | Path,
):
    """Decode and retire one graph after its outer binding was verified."""
    from dsf_ai_service.substrate.retired_legacy_cognition import (
        retire_neuron_legacy_bindings,
    )

    current_registry = structural_graph_state._registry
    structural_graph_state._registry = _retired_registry
    try:
        organism = organism_type.load_full_state(path)
    finally:
        structural_graph_state._registry = current_registry
    retire_neuron_legacy_bindings(organism)
    return organism


def inspect_authenticated_legacy_organism_graph(
    organism_type: type,
    path: str | Path,
) -> LegacyOrganismGraphInspection:
    """Validate and census a retired graph without constructing its objects."""

    path = Path(path)
    current_registry = structural_graph_state._registry
    structural_graph_state._registry = _inspection_registry
    reader = None
    try:
        reader = structural_graph_state._GraphReader(
            path,
            limits=(
                structural_graph_state
                .structural_graph_limits_from_environment()
            ),
            expected_root_type=organism_type,
        )
        connection = reader.connection
        node_type_counts = {
            ("untyped" if tag is None else str(tag)): int(count)
            for tag, count in connection.execute(
                "SELECT type_tag,COUNT(*) FROM nodes "
                "GROUP BY type_tag ORDER BY type_tag"
            )
        }
        field_counts = {
            ("unkeyed" if field is None else str(field)): int(count)
            for field, count in connection.execute(
                "SELECT field_name,COUNT(*) FROM edges "
                "GROUP BY field_name ORDER BY field_name"
            )
        }
        unknown_tags = sorted(
            tag for tag in node_type_counts
            if tag not in {"untyped", *_inspection_registry()[1]}
        )
        if unknown_tags:
            raise structural_graph_state.StructuralGraphError(
                "retired graph contains unregistered types: "
                + ", ".join(unknown_tags)
            )
        metadata = {
            key: json.loads(bytes(value).decode("utf-8"))
            for key, value in connection.execute(
                "SELECT key,value FROM metadata ORDER BY key"
            )
        }
        root_id = metadata["root_id"]
        identity_rows = connection.execute(
            "SELECT n.kind,n.payload "
            "FROM edges AS e "
            "JOIN nodes AS n ON n.node_id=e.value_id "
            "WHERE e.parent_id=? AND e.field_name='identity_uuid'",
            (root_id,),
        ).fetchall()
        if len(identity_rows) != 1 or identity_rows[0][0] != "str":
            raise structural_graph_state.StructuralGraphError(
                "retired graph identity field is absent or ambiguous"
            )
        try:
            identity_uuid = bytes(identity_rows[0][1]).decode("utf-8")
        except (TypeError, UnicodeDecodeError) as error:
            raise structural_graph_state.StructuralGraphError(
                "retired graph identity is not canonical UTF-8"
            ) from error
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        return LegacyOrganismGraphInspection(
            identity_uuid=identity_uuid,
            node_count=reader.node_count,
            node_type_counts=node_type_counts,
            field_counts=field_counts,
            sha256=digest.hexdigest(),
            size_bytes=size,
        )
    finally:
        if reader is not None:
            reader.connection.close()
        structural_graph_state._registry = current_registry


__all__ = [
    "LegacyOrganismGraphInspection",
    "inspect_authenticated_legacy_organism_graph",
    "load_authenticated_legacy_organism_graph",
]
