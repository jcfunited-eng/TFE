"""Verified migration and purge authority for retired cognition state.

No retired component bytes enter a new active or sealed generation.  The
pre-cutover sealed generation and its EFS backup remain the recovery
authority.  New generations retain only a compact, outer-envelope-authenticated
proof naming every discarded source component by exact path, byte count, and
SHA-256 identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Mapping


PURGED_RETIREMENT_SCHEMA = "guala.active_legacy_cognition_purged.v2"
RECOVERY_AUTHORITY = "pre_cutover_sealed_generation_and_efs_backup"

_ORGANISM_COMPONENT_ALTERNATIVES = (
    (
        "guala_organism.sgr",
        "guala_organism.sgr.binding.json",
    ),
    (
        "guala_organism.pkl.gz",
        "guala_organism.pkl.gz.binding.json",
    ),
)
_TAPESTRY_COMPONENT_ALTERNATIVES = (
    (
        "guala_tapestry.sgr",
        "guala_tapestry.sgr.binding.json",
    ),
    (
        "guala_tapestry.pkl.gz",
        "guala_tapestry.pkl.gz.binding.json",
    ),
)
_RETIRED_COMPONENT_CLASSIFICATION = {
    "guala_core.json": "pre_cutover_generation_core",
    "guala_atlas.json": "retired_legacy_chi_word_authority",
    "guala_sections.json": "retired_word_labelled_dsf_mode_authority",
    "guala_bucket.json": "retired_question_bucket_marker",
    "guala_deep_atlas.json": "retired_deep_chi_association_authority",
    "guala_teaching.json": "retired_multi_owner_cognition_monolith",
    "guala_organism.sgr": "migrated_pre_cutover_neuron_graph",
    "guala_organism.sgr.binding.json": (
        "pre_cutover_organism_authentication_receipt"
    ),
    "guala_organism.pkl.gz": "migrated_pre_graph_neuron_state",
    "guala_organism.pkl.gz.binding.json": (
        "pre_cutover_organism_authentication_receipt"
    ),
    "guala_tapestry.sgr": "migrated_pre_cutover_tapestry_graph",
    "guala_tapestry.sgr.binding.json": (
        "pre_cutover_tapestry_authentication_receipt"
    ),
    "guala_tapestry.pkl.gz": "migrated_pre_graph_tapestry_state",
    "guala_tapestry.pkl.gz.binding.json": (
        "pre_cutover_tapestry_authentication_receipt"
    ),
    "wave_atlas.npz": "retired_wave_chi_binding_authority",
    "wave_atlas.npz.binding.json": (
        "pre_cutover_wave_authentication_receipt"
    ),
    "owner_state/self_vocal_pcm_motor.json": (
        "retired_self_vocal_pcm_owner_envelope"
    ),
    "owner_state/lived_vocal_teaching.json": (
        "retired_lived_vocal_teaching_owner_envelope"
    ),
    "owner_state/causal_thing_vocal_route.json": (
        "retired_causal_thing_vocal_route_owner_envelope"
    ),
    "owner_state/articulatory_thing_vocal_custody.json": (
        "retired_articulatory_thing_vocal_owner_envelope"
    ),
    "owner_state/learned_substrate_vocal_cycle.json": (
        "retired_learned_vocal_cycle_owner_envelope"
    ),
}
_RETIRED_COMPONENTS = tuple(_RETIRED_COMPONENT_CLASSIFICATION)
_RETIRED_ONLY_COMPONENTS = tuple(
    name
    for name in _RETIRED_COMPONENTS
    if name
    not in {
        "guala_core.json",
        "guala_organism.sgr",
        "guala_organism.sgr.binding.json",
        "guala_organism.pkl.gz",
        "guala_organism.pkl.gz.binding.json",
        "guala_tapestry.sgr",
        "guala_tapestry.sgr.binding.json",
        "guala_tapestry.pkl.gz",
        "guala_tapestry.pkl.gz.binding.json",
    }
)


class RetiredLegacyCognitionError(RuntimeError):
    """The verified migration or purge contract changed."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_identity_tick(identity: str, tick: int) -> None:
    if not isinstance(identity, str) or not identity:
        raise RetiredLegacyCognitionError(
            "legacy cognition retirement identity is absent"
        )
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise RetiredLegacyCognitionError(
            "legacy cognition retirement tick is invalid"
        )


def _regular_file_record(path: Path, logical_name: str) -> dict[str, object]:
    info = os.lstat(path)
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise RetiredLegacyCognitionError(
            f"retired component is not a regular file: {logical_name}"
        )
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    if size != info.st_size:
        raise RetiredLegacyCognitionError(
            f"retired component changed while hashing: {logical_name}"
        )
    return {
        "classification": _RETIRED_COMPONENT_CLASSIFICATION[logical_name],
        "path": logical_name,
        "sha256": digest.hexdigest(),
        "size_bytes": size,
    }


def _require_one_complete_alternative(
    root: Path,
    alternatives: tuple[tuple[str, str], ...],
    label: str,
) -> None:
    complete = [
        pair
        for pair in alternatives
        if all((root / name).is_file() for name in pair)
    ]
    if len(complete) != 1:
        raise RetiredLegacyCognitionError(
            f"pre-cutover {label} artifact is absent or ambiguous"
        )


def active_generation_has_retired_components(
    state_directory: str,
) -> bool:
    """Return whether authenticated source custody contains retired bytes."""

    root = Path(state_directory)
    return any((root / name).is_file() for name in _RETIRED_ONLY_COMPONENTS)


def prepare_purge_proof_from_active_generation(
    state_directory: str,
    *,
    identity: str,
    source_generation_tick: int,
) -> dict[str, object]:
    """Hash retired source bytes once without copying or decoding them."""

    _validate_identity_tick(identity, source_generation_tick)
    root = Path(state_directory)
    for required in ("guala_core.json",):
        if not (root / required).is_file():
            raise RetiredLegacyCognitionError(
                f"required pre-cutover component is absent: {required}"
            )
    _require_one_complete_alternative(
        root,
        _ORGANISM_COMPONENT_ALTERNATIVES,
        "organism",
    )
    _require_one_complete_alternative(
        root,
        _TAPESTRY_COMPONENT_ALTERNATIVES,
        "tapestry",
    )

    records = [
        _regular_file_record(root / logical_name, logical_name)
        for logical_name in sorted(_RETIRED_COMPONENTS)
        if (root / logical_name).is_file()
    ]
    component_root = hashlib.sha256(_canonical({
        "components": records,
        "identity": identity,
        "source_generation_tick": source_generation_tick,
    })).hexdigest()
    return {
        "identity": identity,
        "migration": None,
        "recovery_authority": RECOVERY_AUTHORITY,
        "schema": PURGED_RETIREMENT_SCHEMA,
        "source_component_root_sha256": component_root,
        "source_components": records,
        "source_generation_tick": source_generation_tick,
    }


def validate_purge_proof(
    proof: object,
    *,
    expected_identity: str,
    maximum_tick: int,
) -> dict[str, object]:
    """Validate the compact proof without opening any retired component."""

    _validate_identity_tick(expected_identity, maximum_tick)
    expected_fields = {
        "identity",
        "migration",
        "recovery_authority",
        "schema",
        "source_component_root_sha256",
        "source_components",
        "source_generation_tick",
    }
    if not isinstance(proof, Mapping) or set(proof) != expected_fields:
        raise RetiredLegacyCognitionError(
            "legacy cognition purge proof field set changed"
        )
    source_tick = proof.get("source_generation_tick")
    if (
        proof.get("schema") != PURGED_RETIREMENT_SCHEMA
        or proof.get("identity") != expected_identity
        or proof.get("recovery_authority") != RECOVERY_AUTHORITY
        or isinstance(source_tick, bool)
        or not isinstance(source_tick, int)
        or source_tick < 0
        or source_tick > maximum_tick
    ):
        raise RetiredLegacyCognitionError(
            "legacy cognition purge proof authority changed"
        )
    records = proof.get("source_components")
    if not isinstance(records, list) or not records:
        raise RetiredLegacyCognitionError(
            "legacy cognition purge proof has no source components"
        )
    observed_paths = []
    for record in records:
        if (
            not isinstance(record, Mapping)
            or set(record)
            != {"classification", "path", "sha256", "size_bytes"}
        ):
            raise RetiredLegacyCognitionError(
                "legacy cognition purge component record changed"
            )
        path = record.get("path")
        digest = record.get("sha256")
        size = record.get("size_bytes")
        if (
            path not in _RETIRED_COMPONENT_CLASSIFICATION
            or record.get("classification")
            != _RETIRED_COMPONENT_CLASSIFICATION[path]
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in digest
            )
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise RetiredLegacyCognitionError(
                "legacy cognition purge component authority changed"
            )
        observed_paths.append(path)
    if observed_paths != sorted(set(observed_paths)):
        raise RetiredLegacyCognitionError(
            "legacy cognition purge components are not canonical"
        )
    expected_root = hashlib.sha256(_canonical({
        "components": [dict(record) for record in records],
        "identity": expected_identity,
        "source_generation_tick": source_tick,
    })).hexdigest()
    if proof.get("source_component_root_sha256") != expected_root:
        raise RetiredLegacyCognitionError(
            "legacy cognition source component root changed"
        )
    migration = proof.get("migration")
    if (
        not isinstance(migration, Mapping)
        or set(migration) != {"organism", "tapestry"}
    ):
        raise RetiredLegacyCognitionError(
            "legacy cognition migration proof is incomplete"
        )
    for label in ("organism", "tapestry"):
        record = migration[label]
        if (
            not isinstance(record, Mapping)
            or set(record)
            != {
                "binding_records_retired",
                "chi_records_retired",
                "language_labels_retired",
                "neurons_preserved",
            }
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in record.values()
            )
        ):
            raise RetiredLegacyCognitionError(
                f"legacy cognition {label} migration proof changed"
            )
    return {
        key: (
            [dict(record) for record in value]
            if key == "source_components"
            else (
                {
                    label: dict(record)
                    for label, record in value.items()
                }
                if key == "migration"
                else value
            )
        )
        for key, value in proof.items()
    }


def retire_neuron_legacy_bindings(root: object) -> dict[str, int]:
    """Delete retired per-neuron meaning authorities after graph validation.

    Neuron bodies, L6, oscillators, full-field state, couplings, membrane,
    and learned sensory state are not rewritten.
    """
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
        LanguageKrimelack,
    )

    if hasattr(root, "brain"):
        neurons = [
            neuron
            for hemisphere in root.brain.hemispheres
            for neuron in hemisphere.cluster.neurons
        ]
    elif hasattr(root, "mosaics"):
        neurons = [
            neuron
            for mosaic in root.mosaics
            for cluster in mosaic.clusters
            for neuron in cluster.neurons
        ]
    else:
        raise RetiredLegacyCognitionError(
            "legacy cognition retirement root has no neuron graph"
        )
    if hasattr(root, "_scP"):
        del root.__dict__["_scP"]

    retired_binding_records = 0
    retired_chi_records = 0
    retired_language_labels = 0
    neuron_ids = []
    for neuron in neurons:
        neuron_ids.append(neuron.neuron_id)
        atlas = getattr(neuron, "binding_atlas", None)
        if atlas is not None:
            retired_binding_records += sum(
                len(cell.bindings) for cell in atlas.cells.values()
            )
            retired_binding_records += len(atlas._lane_bindings)
            del neuron.__dict__["binding_atlas"]
        chi_atlas = getattr(neuron, "chi_atlas", None)
        if chi_atlas is not None:
            retired_chi_records += sum(
                len(bucket) for bucket in chi_atlas.entries.values()
            )
            del neuron.__dict__["chi_atlas"]
        if "_lane_P" in neuron.__dict__:
            del neuron.__dict__["_lane_P"]
        neuron.__dict__.pop("_word_firing_callback", None)
        seen = set()
        for krimelack in (
            neuron.krimelack,
            *neuron.krimelack_bank.values(),
        ):
            if id(krimelack) in seen:
                continue
            seen.add(id(krimelack))
            if (
                isinstance(krimelack, LanguageKrimelack)
                and "last_input_word" in krimelack.__dict__
            ):
                retired_language_labels += 1
                del krimelack.__dict__["last_input_word"]

    if len(neuron_ids) != len(set(neuron_ids)):
        raise RetiredLegacyCognitionError(
            "neuron identity changed during legacy cognition retirement"
        )
    return {
        "neurons_preserved": len(neurons),
        "binding_records_retired": retired_binding_records,
        "chi_records_retired": retired_chi_records,
        "language_labels_retired": retired_language_labels,
    }


def assert_legacy_bindings_retired(root: object) -> int:
    """Fail if an active graph still contains a retired meaning authority."""
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
        LanguageKrimelack,
    )

    if hasattr(root, "brain"):
        neurons = [
            neuron
            for hemisphere in root.brain.hemispheres
            for neuron in hemisphere.cluster.neurons
        ]
    elif hasattr(root, "mosaics"):
        neurons = [
            neuron
            for mosaic in root.mosaics
            for cluster in mosaic.clusters
            for neuron in cluster.neurons
        ]
    else:
        raise RetiredLegacyCognitionError(
            "active retirement proof root has no neuron graph"
        )
    for neuron in neurons:
        if "binding_atlas" in neuron.__dict__:
            raise RetiredLegacyCognitionError(
                "active neuron retains a legacy BindingAtlas"
            )
        if "chi_atlas" in neuron.__dict__:
            raise RetiredLegacyCognitionError(
                "active neuron retains a legacy ChiAtlas"
            )
        if "_word_firing_callback" in neuron.__dict__:
            raise RetiredLegacyCognitionError(
                "active neuron retains a word firing callback"
            )
        seen = set()
        for krimelack in (
            neuron.krimelack,
            *neuron.krimelack_bank.values(),
        ):
            if id(krimelack) in seen:
                continue
            seen.add(id(krimelack))
            if (
                isinstance(krimelack, LanguageKrimelack)
                and "last_input_word" in krimelack.__dict__
            ):
                raise RetiredLegacyCognitionError(
                    "active neuron retains a language label"
                )
    return len(neurons)


__all__ = (
    "PURGED_RETIREMENT_SCHEMA",
    "RECOVERY_AUTHORITY",
    "RetiredLegacyCognitionError",
    "active_generation_has_retired_components",
    "assert_legacy_bindings_retired",
    "prepare_purge_proof_from_active_generation",
    "retire_neuron_legacy_bindings",
    "validate_purge_proof",
)
