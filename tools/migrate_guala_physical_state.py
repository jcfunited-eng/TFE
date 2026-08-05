#!/usr/bin/env python3
"""One-way authenticated migration into the current physical Guala runtime.

The historical source generation is immutable.  Its exact historical owner
allowlist is authenticated independently from owners that only exist in the
current runtime.  The embodied vocal body, experience-grown motor fragment,
pending body-owned consequence, companion audiovisual continuity, and
experience-grown causal relation are minted together at destination genesis
after the historical world has been restored. Historical articulatory programs
are authenticated as migration evidence and deliberately retired; they are
never installed in the live destination motor owner.  The historical Embryo
graph is likewise authenticated and censused as source-only retirement
evidence.  It is never attached to the graph-free whole-organism runtime and
never emitted into a current generation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from dsf_ai_service.substrate.deployment_generation import (
    CAUSAL_GENERATION_RECEIPT,
    _stream_materialized_file,
    discover_and_load_current,
    load_generation_deployment_seal,
    materialize_verified_generation,
    persist_deployment_seal,
    reconcile_generation_deployment_seals,
    reconcile_remote_generation_prefixes,
    stage_authoritative_commit_upload,
    verified_causal_generation_receipt,
)
from dsf_ai_service.substrate.migration_live_recovery_cutover import (
    authenticated_terminal_same_source_retry_custody,
    publish_after_source_overlay_retirement,
    restore_source_after_destination_overlay_custody,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    GENERATIONS_DIRECTORY,
    GenerationValidationError,
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.production_storage_profile import (
    MAX_COLD_REQUIRED_FILES,
    MAX_COLD_REQUIRED_PATH_BYTES,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)
from dsf_ai_service.substrate.whole_organism_persistence import (
    WholeOrganismPersistenceError,
    whole_organism_mutation_root,
)

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ARTICULATORY_PROGRAM_SCHEMA,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    ACTIVE_OWNER_STATE_KEYS,
    OWNER_STATE_GROUPS,
    OwnerScopedPersistenceError,
    owner_state_bodies,
    owner_state_body_mutation_root,
)
from dsf_ai_service.substrate.legacy_learned_state_gate import (
    LegacyLearnedStateGateError,
    LegacyLearnedStateUnresolved,
    build_legacy_learned_state_plan,
    verify_legacy_learned_state_plan,
)
from dsf_ai_service.substrate.embodied_vocal_body import (
    EmbodiedVocalBodyAuthority,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.experience_grown_vocal_causal_relation import (
    ExperienceGrownVocalCausalRelationOwner,
)
from dsf_ai_service.substrate.experience_grown_vocal_motor_fragment import (
    ExperienceGrownVocalMotorFragmentOwner,
)
from dsf_ai_service.substrate.pending_body_owned_vocal_consequence import (
    PendingBodyOwnedVocalConsequenceOwner,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveThingLearningProfile,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.v4.guala_physical_runtime import (
    BODY_OWNED_VOCAL_STATE_MAX_BYTES,
    BODY_OWNED_VOCAL_STATE_PATH,
    EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_MAX_BYTES,
    EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_PATH,
    EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_MAX_COUNT,
    EXPERIENCE_GROWN_VOCAL_FRAGMENT_MAX_COUNT,
    EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_MAX_BYTES,
    EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_PATH,
    PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_MAX_BYTES,
    PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_PATH,
    PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_PROFILE_ID,
    PASSIVE_WHOLE_ORGANISM_THING_MAX_RECORDS,
    PASSIVE_WHOLE_ORGANISM_THING_MAX_ROOTS_PER_RECORD,
    PASSIVE_WHOLE_ORGANISM_THING_STATE_MAX_BYTES,
    PASSIVE_WHOLE_ORGANISM_THING_STATE_PATH,
    ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_MAX_BYTES,
    ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_PATH,
    W1_COMPANION_AV_CONTINUITY_STATE_MAX_BYTES,
    W1_COMPANION_AV_CONTINUITY_STATE_PATH,
    Guala,
)
from dsf_ai_service.v4.guala_physical_runtime_core import (
    Guala as PhysicalGualaRuntimeCore,
)
from dsf_ai_service.loom_model.embryo import Embryo
from tools.guala_legacy_organism_graph_reader import (
    LegacyOrganismGraphInspection,
    inspect_authenticated_legacy_organism_graph,
)
from tools.retired_legacy_s3_archive import (
    RetiredLegacyArchiveError,
    archive_retired_legacy_generation,
)


MIGRATION_PROOF_SCHEMA = "guala.physical_state_one_way_migration.v5"
PRODUCTION_HANDOFF_SCHEMA = "guala.physical_state_production_handoff.v2"
PRODUCTION_ROLLBACK_SCHEMA = "guala.physical_state_production_rollback.v2"
MIGRATION_PROOF_RELATIVE_PATH = (
    "legacy_cognition_archive/retired_component_purge_proof.json"
)
_MIGRATION_PROOF_DOMAIN = b"guala-physical-state-one-way-migration-v5\0"
_RETIRED_ARCHIVE_AUTHORITY_DOMAIN = (
    b"guala-physical-state-retired-archive-authority-v1\0"
)
_TREE_ROOT_DOMAIN = b"guala-physical-state-tree-root-v2\0"
_RETIRED_ROOT_DOMAIN = b"guala-retired-component-root-v2\0"
_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS = frozenset({
    "organs_manifest.json",
    "ring_events/events.log",
})
_MIGRATION_SEALED_OPERATIONAL_FILES = frozenset({".sleeping"})
_SENSORY_EXPANSION_V1_STATE_SCHEMA = (
    "guala.causal_thing.sensory_expansion.state.v1"
)
_SENSORY_EXPANSION_V1_ENVELOPE_SCHEMA = (
    "guala.causal_thing.sensory_expansion.state_hmac.v1"
)
_SENSORY_EXPANSION_V1_STATE_DOMAIN = (
    b"guala-causal-thing-sensory-expansion-state-v1\0"
)

# These owners were absent from the authenticated historical generation and
# are therefore minted only by the current runtime.
GENESIS_ONLY_OWNER_IDS = frozenset(
    {
        "anonymous_passive_window",
        "causal_mosaic_tapestry",
        "causal_recognition_attention",
        "causal_inquiry",
        "durable_sensed_consequence",
        "embodied_glyph_curriculum",
        "embodied_other_perspective",
        "embodied_reading_lesson_controller",
        "grounded_articulatory_vocal_turn",
        "lived_vocal_teaching",
        "organism_dream_wake_weave",
        "whole_organism_recovery",
        "whole_organism_neuron_population",
        "whole_organism_neurochemical_mount",
        "whole_organism_structural_perturbation",
        "whole_organism_reflection_monitor",
        "whole_organism_thing_mosaic_learning",
    }
)

# This is the exact owner census required at the authenticated source
# generation boundary.  The two whole-organism owners are learned-state
# evidence, not destination genesis: their authenticated bodies must be read,
# restored into the migration runtime, written into the physical generation,
# and verified byte-exact after a cold restore.
HISTORICAL_SOURCE_OWNER_IDS = frozenset(
    {
        "articulatory_consequence_closure",
        "articulatory_self_vocal",
        "auditory_recurrent_motif",
        "auditory_temporal_relation_assembly",
        "auditory_w1_binaural_peak_bank",
        "autonomous_causal_play",
        "causal_action_cycle",
        "causal_action_dispatcher",
        "causal_deliberation",
        "causal_thing_action_intents",
        "causal_thing_lived_context",
        "causal_thing_mosaic",
        "causal_thing_sensory_expansion",
        "custody_native_tutoring_action_selector",
        "custody_native_tutoring_curriculum",
        "embodied_action_teaching",
        "embodiment_outcome_causal_sequence",
        "embodiment_world",
        "full_field_prediction",
        "pending_articulatory_causal_attempt",
        "physical_internal_body_state",
        "visual_region_continuity",
        "w1_binaural_auditory_l5",
        "whole_organism_episode",
    }
)

CURRENT_GENESIS_EXTENSION_PATHS = frozenset(
    {
        *(
            group.relative_path
            for group in OWNER_STATE_GROUPS
            if group.owner_id in GENESIS_ONLY_OWNER_IDS
        ),
        BODY_OWNED_VOCAL_STATE_PATH,
        EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_PATH,
        PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_PATH,
        W1_COMPANION_AV_CONTINUITY_STATE_PATH,
        EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_PATH,
        PASSIVE_WHOLE_ORGANISM_THING_STATE_PATH,
        ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_PATH,
    }
)

RAW_CURRENT_OWNER_SPECS = (
    (
        "embodied_vocal_body",
        BODY_OWNED_VOCAL_STATE_PATH,
        BODY_OWNED_VOCAL_STATE_MAX_BYTES,
    ),
    (
        "experience_grown_vocal_motor_fragment",
        EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_PATH,
        EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_MAX_BYTES,
    ),
    (
        "pending_body_owned_vocal_consequence",
        PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_PATH,
        PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_MAX_BYTES,
    ),
    (
        "w1_companion_av_continuity",
        W1_COMPANION_AV_CONTINUITY_STATE_PATH,
        W1_COMPANION_AV_CONTINUITY_STATE_MAX_BYTES,
    ),
    (
        "experience_grown_vocal_causal_relation",
        EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_PATH,
        EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_MAX_BYTES,
    ),
    (
        "passive_whole_organism_thing_learning",
        PASSIVE_WHOLE_ORGANISM_THING_STATE_PATH,
        PASSIVE_WHOLE_ORGANISM_THING_STATE_MAX_BYTES,
    ),
    (
        "organism_ordered_lived_experience",
        ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_PATH,
        ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_MAX_BYTES,
    ),
)

RETIRED_ARTICULATORY_OWNER_ID = "articulatory_self_vocal"
RETIRED_ARTICULATORY_OWNER_PATH = (
    "owner_state/articulatory_self_vocal.json"
)

_SOURCE_REQUIRED_FILES = frozenset(
    {
        "guala_core.json",
        "guala_identity.json",
        "guala_organism.sgr",
        "guala_organism.sgr.binding.json",
    }
)


class PhysicalStateMigrationError(RuntimeError):
    """The source or candidate destination failed a migration contract."""


@dataclass(frozen=True, slots=True)
class FileMeasurement:
    path: str
    bytes: int
    sha256: str

    def record(self) -> dict[str, object]:
        return {
            "bytes": self.bytes,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class RetiredArticulatoryMotor:
    source_program_count: int
    source_program_receipts: tuple[str, ...]
    source_program_root_sha256: str
    destination_program_count: int

    def record(self) -> dict[str, object]:
        return {
            "action": (
                "authenticated_source_programs_retired_destination_genesis"
            ),
            "destination_program_count": self.destination_program_count,
            "source_program_count": self.source_program_count,
            "source_program_receipts": list(
                self.source_program_receipts
            ),
            "source_program_root_sha256": (
                self.source_program_root_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class VerifiedSource:
    identity: str
    identity_record: dict[str, object]
    tick: int
    graph: FileMeasurement
    graph_census: dict[str, object]
    owner_bodies: dict[str, bytes]
    owner_mutation_roots: dict[str, str]
    destination_genesis_bodies: dict[str, bytes]
    direct_translated_owner_paths: tuple[str, ...]
    legacy_learned_plan_record: dict[str, object] | None
    retired_articulatory_motor: RetiredArticulatoryMotor
    retired_components: tuple[FileMeasurement, ...]
    source_tree_bytes: int
    source_tree_root_sha256: str


@dataclass(frozen=True, slots=True)
class MigrationResult:
    destination: Path
    identity: str
    tick: int
    retired_source_organism_sha256: str
    current_state_file_count: int
    source_owner_evidence_count: int
    retired_component_count: int
    proof_sha256: str

    def record(self) -> dict[str, object]:
        return {
            "current_state_file_count": self.current_state_file_count,
            "destination": str(self.destination),
            "identity": self.identity,
            "proof_sha256": self.proof_sha256,
            "retired_source_organism_sha256": (
                self.retired_source_organism_sha256
            ),
            "retired_component_count": self.retired_component_count,
            "source_owner_evidence_count": (
                self.source_owner_evidence_count
            ),
            "tick": self.tick,
        }


@dataclass(frozen=True, slots=True)
class ProductionHandoffResult:
    source_generation: str
    source_manifest_sha256: str
    destination_generation: str
    destination_manifest_sha256: str
    identity: str
    tick: int
    active_recovery_generation: str
    active_recovery_manifest_sha256: str
    active_recovery_tick: int
    migration_proof_sha256: str
    live_recovery_cutover_intent_sha256: str
    retired_archive_prefix: str
    retired_archive_receipt_hmac_sha256: str
    retired_archive_source_tree_sha256: str
    retired_archive_storage_mode: str
    retired_archive_total_bytes: int

    def record(self) -> dict[str, object]:
        return {
            "active_recovery_generation": self.active_recovery_generation,
            "active_recovery_manifest_sha256": (
                self.active_recovery_manifest_sha256
            ),
            "active_recovery_tick": self.active_recovery_tick,
            "destination_generation": self.destination_generation,
            "destination_manifest_sha256": (
                self.destination_manifest_sha256
            ),
            "identity": self.identity,
            "migration_proof_sha256": self.migration_proof_sha256,
            "live_recovery_cutover_intent_sha256": (
                self.live_recovery_cutover_intent_sha256
            ),
            "retired_archive_prefix": self.retired_archive_prefix,
            "retired_archive_receipt_hmac_sha256": (
                self.retired_archive_receipt_hmac_sha256
            ),
            "retired_archive_source_tree_sha256": (
                self.retired_archive_source_tree_sha256
            ),
            "retired_archive_storage_mode": (
                self.retired_archive_storage_mode
            ),
            "retired_archive_total_bytes": (
                self.retired_archive_total_bytes
            ),
            "source_generation": self.source_generation,
            "source_manifest_sha256": self.source_manifest_sha256,
            "tick": self.tick,
        }


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant {value!r}")


def _reject_duplicate_json_members(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for name, member in pairs:
        if name in value:
            raise ValueError(f"duplicate JSON member {name!r}")
        value[name] = member
    return value


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _migration_key(authority_secret: str) -> bytes:
    if not isinstance(authority_secret, str) or len(authority_secret) < 16:
        raise PhysicalStateMigrationError(
            "GUALA_CAUSAL_ACTION_KEY must contain at least 16 characters"
        )
    return hmac.new(
        authority_secret.encode("utf-8"),
        _MIGRATION_PROOF_DOMAIN,
        hashlib.sha256,
    ).digest()


def _authority_secret_from_environment() -> str:
    authority_secret = (
        os.environ.get("GUALA_CAUSAL_ACTION_KEY")
        or os.environ.get("GUALALOOM_API_KEY")
    )
    if not authority_secret:
        raise PhysicalStateMigrationError(
            "GUALA_CAUSAL_ACTION_KEY or GUALALOOM_API_KEY is required "
            "for owner verification"
        )
    _migration_key(authority_secret)
    return authority_secret


def _retired_archive_authority_key(authority_secret: str) -> bytes:
    """Derive a separate fixed-width archive authority from migration trust."""

    return hmac.new(
        _migration_key(authority_secret),
        _RETIRED_ARCHIVE_AUTHORITY_DOMAIN,
        hashlib.sha256,
    ).digest()


def _archive_retired_source(
    source,
    *,
    s3_client: Any,
    bucket: str,
    authority_secret: str,
    archive_root_prefix: str,
    max_total_archive_bytes: int,
):
    """Archive one retired source under its derived independent authority."""

    try:
        return archive_retired_legacy_generation(
            source,
            s3_client=s3_client,
            bucket=bucket,
            authority_key=_retired_archive_authority_key(
                authority_secret
            ),
            archive_root_prefix=archive_root_prefix,
            max_total_archive_bytes=max_total_archive_bytes,
        )
    except RetiredLegacyArchiveError as error:
        raise PhysicalStateMigrationError(
            "retired source archive failed: " + str(error)
        ) from error


def _regular_file_measurement(
    root: Path,
    relative_path: str,
) -> FileMeasurement:
    path = root / relative_path
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise PhysicalStateMigrationError(
            f"required source file is missing: {relative_path}"
        ) from error
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise PhysicalStateMigrationError(
            f"migration artifact is not a regular file: {relative_path}"
        )
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    if size != info.st_size:
        raise PhysicalStateMigrationError(
            f"migration artifact changed while hashing: {relative_path}"
        )
    return FileMeasurement(relative_path, size, digest.hexdigest())


def _regular_tree_measurements(
    root: Path,
) -> tuple[FileMeasurement, ...]:
    if not root.is_dir() or root.is_symlink():
        raise PhysicalStateMigrationError(
            "migration source must be one regular directory"
        )
    measurements: list[FileMeasurement] = []
    for directory, directory_names, file_names in os.walk(root):
        directory_path = Path(directory)
        for name in sorted(directory_names):
            child = directory_path / name
            if child.is_symlink():
                raise PhysicalStateMigrationError(
                    "migration source contains a directory symlink: "
                    + child.relative_to(root).as_posix()
                )
        for name in sorted(file_names):
            child = directory_path / name
            relative = child.relative_to(root).as_posix()
            measurements.append(
                _regular_file_measurement(root, relative)
            )
    return tuple(
        sorted(measurements, key=lambda item: item.path)
    )


def _measurement_root(
    measurements: tuple[FileMeasurement, ...],
    *,
    domain: bytes,
) -> str:
    digest = hashlib.sha256(domain)
    for measurement in measurements:
        digest.update(_canonical(measurement.record()))
    return digest.hexdigest()


def _structural_graph_census(
    inspection: LegacyOrganismGraphInspection,
) -> dict[str, object]:
    node_types = inspection.node_type_counts
    field_counts = inspection.field_counts
    retired_node_count = sum(
        node_types.get(tag, 0)
        for tag in ("binding_atlas", "chi_atlas")
    )
    retired_field_count = sum(
        field_counts.get(field, 0)
        for field in (
            "binding_atlas",
            "chi_atlas",
            "_lane_P",
            "_scP",
            "last_input_word",
            "_word_firing_callback",
        )
    )
    return {
        "bytes": inspection.size_bytes,
        "dsf_nodes": node_types.get("dsf", 0),
        "field_counts": dict(sorted(field_counts.items())),
        "legacy_coupling_backlog_fields": field_counts.get(
            "_coupling_signal_accum",
            0,
        ),
        "loom_neuron_nodes": node_types.get("loom_neuron", 0),
        "node_count": inspection.node_count,
        "node_type_counts": dict(sorted(node_types.items())),
        "retired_cognition_fields": retired_field_count,
        "retired_cognition_nodes": retired_node_count,
        "sha256": inspection.sha256,
    }


def _assert_current_graph_census(
    source_census: Mapping[str, object],
    target_census: Mapping[str, object],
) -> None:
    if (
        target_census.get("retired_cognition_nodes") != 0
        or target_census.get("retired_cognition_fields") != 0
        or target_census.get("legacy_coupling_backlog_fields") != 0
    ):
        raise PhysicalStateMigrationError(
            "retired cognition remained in the physical organism graph"
        )
    for field in ("loom_neuron_nodes", "dsf_nodes"):
        if target_census.get(field) != source_census.get(field):
            raise PhysicalStateMigrationError(
                f"physical organism graph changed {field}"
            )


def _owner_group_by_id() -> dict[str, object]:
    result = {group.owner_id: group for group in OWNER_STATE_GROUPS}
    current_ids = set(result)
    if not HISTORICAL_SOURCE_OWNER_IDS.issubset(current_ids):
        raise PhysicalStateMigrationError(
            "historical source owner contract left the current registry"
        )
    if HISTORICAL_SOURCE_OWNER_IDS & GENESIS_ONLY_OWNER_IDS:
        raise PhysicalStateMigrationError(
            "historical and genesis owner allowlists overlap"
        )
    return result


def _read_canonical_owner_body(
    source: Path,
    group,
) -> tuple[bytes, dict[str, object], str]:
    measurement = _regular_file_measurement(
        source, group.relative_path
    )
    body = (source / group.relative_path).read_bytes()
    if (
        len(body) != measurement.bytes
        or _sha256_hex(body) != measurement.sha256
    ):
        raise PhysicalStateMigrationError(
            f"owner body changed while reading: {group.relative_path}"
        )
    try:
        decoded = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PhysicalStateMigrationError(
            f"owner body is unreadable: {group.relative_path}"
        ) from error
    try:
        mutation_root = owner_state_body_mutation_root(group, body)
    except OwnerScopedPersistenceError as error:
        raise PhysicalStateMigrationError(
            f"owner body contract failed: {group.relative_path}: {error}"
        ) from error
    return body, decoded["state"], mutation_root


def _verify_and_admit_empty_sensory_expansion_v1(
    value: object,
    *,
    runtime: Guala,
) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"body", "schema", "state_hmac_sha256"}
        or value.get("schema")
        != _SENSORY_EXPANSION_V1_ENVELOPE_SCHEMA
    ):
        raise PhysicalStateMigrationError(
            "sensory expansion V1 envelope changed"
        )
    body = value.get("body")
    current_owner = runtime._causal_thing_sensory_expansion
    expected_limits = {
        "max_expansions": current_owner._max_expansions,
        "max_roots_per_expansion": current_owner._max_roots,
        "max_state_bytes": current_owner._max_state_bytes,
    }
    if (
        not isinstance(body, dict)
        or set(body) != {"expansions", "limits", "schema"}
        or body.get("schema")
        != _SENSORY_EXPANSION_V1_STATE_SCHEMA
        or body.get("limits") != expected_limits
        or not isinstance(body.get("expansions"), list)
    ):
        raise PhysicalStateMigrationError(
            "sensory expansion V1 body changed"
        )
    if body["expansions"]:
        raise PhysicalStateMigrationError(
            "non-empty sensory expansion V1 requires provenance that "
            "cannot be losslessly derived for V2"
        )
    thing_key = runtime._thing_vocal_key
    if not isinstance(thing_key, bytes) or len(thing_key) < 32:
        raise PhysicalStateMigrationError(
            "sensory expansion V1 has no current authority key"
        )
    root = hashlib.sha256(
        b"causal THING sensory expansion\0" + thing_key
    ).digest()
    state_key = hashlib.sha256(
        _SENSORY_EXPANSION_V1_STATE_DOMAIN + root
    ).digest()
    expected_hmac = hmac.new(
        state_key,
        _SENSORY_EXPANSION_V1_STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    supplied_hmac = value.get("state_hmac_sha256")
    if (
        not isinstance(supplied_hmac, str)
        or not hmac.compare_digest(expected_hmac, supplied_hmac)
    ):
        raise PhysicalStateMigrationError(
            "sensory expansion V1 authority HMAC changed"
        )


def _validate_identity_record(
    source: Path,
) -> tuple[str, dict[str, object]]:
    _regular_file_measurement(source, "guala_identity.json")
    try:
        record = json.loads(
            (source / "guala_identity.json").read_text(
                encoding="utf-8"
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PhysicalStateMigrationError(
            "source identity record is unreadable"
        ) from error
    if not isinstance(record, dict):
        raise PhysicalStateMigrationError(
            "source identity record is not an object"
        )
    identity = record.get("guala_identity")
    try:
        parsed = uuid.UUID(identity) if isinstance(identity, str) else None
    except ValueError as error:
        raise PhysicalStateMigrationError(
            "source Guala identity is not a UUID"
        ) from error
    if parsed is None or str(parsed) != identity:
        raise PhysicalStateMigrationError(
            "source Guala identity is not canonical"
        )
    if record.get("schema_version") not in Guala.COMPATIBLE_SCHEMAS:
        raise PhysicalStateMigrationError(
            "source identity schema is not accepted by the physical runtime"
        )
    return identity, record


def _validate_legacy_core(
    source: Path,
    *,
    identity: str,
) -> tuple[int, dict[str, int]]:
    _regular_file_measurement(source, "guala_core.json")
    try:
        core = json.loads(
            (source / "guala_core.json").read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PhysicalStateMigrationError(
            "source core record is unreadable"
        ) from error
    if not isinstance(core, dict):
        raise PhysicalStateMigrationError(
            "source core record is not an object"
        )
    if core.get("guala_identity") != identity:
        raise PhysicalStateMigrationError(
            "source core identity differs from durable identity"
        )
    if core.get("schema_version") not in Guala.COMPATIBLE_SCHEMAS:
        raise PhysicalStateMigrationError(
            "source core schema is not accepted by the physical runtime"
        )
    tick = core.get("saved_at_tick")
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise PhysicalStateMigrationError(
            "source core tick is invalid"
        )
    data = core.get("data")
    if not isinstance(data, dict):
        raise PhysicalStateMigrationError(
            "source core has no legacy payload"
        )
    if (
        data.get("continuity_contract")
        != Guala.ENGINE_CONTINUITY_CONTRACT
        or data.get("binary_binding_contract")
        != Guala.BINARY_BINDING_CONTRACT
        or data.get("last_save_tick") != tick
        or data.get("tick") != tick
    ):
        raise PhysicalStateMigrationError(
            "source core continuity or tick contract changed"
        )
    state_file_ticks = data.get("state_file_ticks")
    if not isinstance(state_file_ticks, dict):
        raise PhysicalStateMigrationError(
            "source core has no exact state-file tick manifest"
        )
    validated: dict[str, int] = {}
    for path, file_tick in state_file_ticks.items():
        if (
            not isinstance(path, str)
            or not path
            or isinstance(file_tick, bool)
            or not isinstance(file_tick, int)
            or file_tick < 0
        ):
            raise PhysicalStateMigrationError(
                "source state-file tick manifest is invalid"
            )
        validated[path] = file_tick
    return tick, validated


def _retire_authenticated_articulatory_motor(
    value: object,
    *,
    runtime: Guala,
    genesis_value: object,
) -> RetiredArticulatoryMotor:
    try:
        legacy = ArticulatorySelfVocalMotorOwner.restore_encoded(
            authority_key=runtime._thing_vocal_key,
            encoded=_canonical(value),
        )
        genesis = ArticulatorySelfVocalMotorOwner.restore_encoded(
            authority_key=runtime._thing_vocal_key,
            encoded=_canonical(genesis_value),
        )
    except Exception as error:
        raise PhysicalStateMigrationError(
            f"retired articulatory motor authentication failed: {error}"
        ) from error
    if genesis.programs:
        raise PhysicalStateMigrationError(
            "destination articulatory motor genesis is not empty"
        )
    records = tuple(program.as_record() for program in legacy.programs)
    if any(
        record.get("schema") != ARTICULATORY_PROGRAM_SCHEMA
        for record in records
    ):
        raise PhysicalStateMigrationError(
            "retired articulatory motor program schema changed"
        )
    receipts = tuple(
        sorted(record["authority_receipt_sha256"] for record in records)
    )
    return RetiredArticulatoryMotor(
        source_program_count=len(records),
        source_program_receipts=receipts,
        source_program_root_sha256=_sha256_hex(
            _canonical(list(sorted(
                records,
                key=lambda item: item["program_id"],
            )))
        ),
        destination_program_count=0,
    )


def _mint_current_raw_owner_genesis(
    runtime: Guala,
) -> dict[str, bytes]:
    authority_key = runtime._body_owned_vocal_authority_key
    if (
        not isinstance(authority_key, bytes)
        or len(authority_key) < 32
        or not isinstance(runtime._causal_cycle_key, str)
    ):
        raise PhysicalStateMigrationError(
            "current raw owner genesis lacks runtime authority"
        )
    body = EmbodiedVocalBodyAuthority(
        authority_key=authority_key,
        world_authority=runtime._embodiment_world,
        inquiry_owner=runtime._causal_inquiry_owner,
        max_state_bytes=BODY_OWNED_VOCAL_STATE_MAX_BYTES,
    )
    pending = PendingBodyOwnedVocalConsequenceOwner(
        authority_key=authority_key,
        profile_id=PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_PROFILE_ID,
        max_state_bytes=(
            PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_MAX_BYTES
        ),
        inquiry_owner=runtime._causal_inquiry_owner,
        vocal_body_owner=body,
    )
    fragment = ExperienceGrownVocalMotorFragmentOwner(
        authority_key=authority_key,
        vocal_body_owner=body,
        motor_owner=runtime._articulatory_self_vocal_owner,
        inquiry_owner=runtime._causal_inquiry_owner,
        thing_owner=runtime._causal_thing_mosaic_owner,
        world_authority=runtime._embodiment_world,
        companion_authority=runtime._w1_companion_vocal_experience,
        tutor_authorization_verifier=(
            runtime._causal_inquiry_tutor_authority.verifier()
        ),
        max_fragments=EXPERIENCE_GROWN_VOCAL_FRAGMENT_MAX_COUNT,
        max_state_bytes=EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_MAX_BYTES,
    )
    prior_reciprocal = runtime._causal_thing_reciprocal_mosaic
    reciprocal = CausalThingReciprocalMosaicOwner(
        authority_key=runtime._causal_cycle_key,
        thing_owner=runtime._causal_thing_mosaic_owner,
        sensory_expansion_owner=(
            runtime._causal_thing_sensory_expansion
        ),
        max_classes=prior_reciprocal._max_classes,
        max_roots_per_class=(
            prior_reciprocal._max_roots_per_class
        ),
        max_cue_roots=prior_reciprocal._max_cue_roots,
    )
    relation = ExperienceGrownVocalCausalRelationOwner(
        authority_key=authority_key,
        max_relations=EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_MAX_COUNT,
        max_state_bytes=(
            EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_MAX_BYTES
        ),
        fragment_owner=fragment,
        inquiry_owner=runtime._causal_inquiry_owner,
        pending_owner=pending,
        thing_owner=runtime._causal_thing_mosaic_owner,
        reciprocal_owner=reciprocal,
        motor_owner=runtime._articulatory_self_vocal_owner,
    )
    root_key = runtime._causal_cycle_key.encode("utf-8")
    continuity = W1AnonymousAudiovisualContinuityOwner(
        authority_key=hmac.new(
            root_key,
            b"guala-w1-anonymous-audiovisual-continuity-v1",
            hashlib.sha256,
        ).digest(),
        physical_authority_key=runtime._w1_physical_key,
        max_transitions=64,
    )
    passive_key = runtime._passive_thing_learning_authority_key
    if not isinstance(passive_key, bytes) or len(passive_key) < 32:
        raise PhysicalStateMigrationError(
            "passive whole-organism genesis lacks runtime authority"
        )
    passive_learning = PassiveWholeOrganismThingLearningOwner(
        authority_key=passive_key,
        profile=PassiveThingLearningProfile.create(
            profile_id=(
                "guala-passive-whole-organism-thing-learning-v1"
            ),
            max_records=PASSIVE_WHOLE_ORGANISM_THING_MAX_RECORDS,
            max_roots_per_record=(
                PASSIVE_WHOLE_ORGANISM_THING_MAX_ROOTS_PER_RECORD
            ),
            max_state_bytes=(
                PASSIVE_WHOLE_ORGANISM_THING_STATE_MAX_BYTES
            ),
        ),
        partition_authority=runtime._thing_partition_authority,
        thing_owner=runtime._causal_thing_mosaic_owner,
        neuron_owner=runtime._whole_organism_neuron_population_owner,
    )
    bodies = {
        BODY_OWNED_VOCAL_STATE_PATH: body.snapshot_encoded(),
        EXPERIENCE_GROWN_VOCAL_FRAGMENT_STATE_PATH: (
            fragment.snapshot_encoded()
        ),
        PENDING_BODY_OWNED_VOCAL_CONSEQUENCE_STATE_PATH: (
            pending.snapshot_encoded()
        ),
        W1_COMPANION_AV_CONTINUITY_STATE_PATH: (
            continuity.encoded_snapshot()
        ),
        EXPERIENCE_GROWN_VOCAL_CAUSAL_RELATION_STATE_PATH: (
            relation.snapshot_encoded()
        ),
        PASSIVE_WHOLE_ORGANISM_THING_STATE_PATH: (
            passive_learning.snapshot_encoded()
        ),
        ORGANISM_ORDERED_LIVED_EXPERIENCE_STATE_PATH: (
            runtime._organism_ordered_lived_experience_owner
            .snapshot_encoded()
        ),
    }
    for _state_key, path, maximum_bytes in RAW_CURRENT_OWNER_SPECS:
        if len(bodies[path]) > maximum_bytes:
            raise PhysicalStateMigrationError(
                f"current genesis owner exceeded its ceiling: {path}"
            )
    return bodies


def _verify_source(
    source: Path,
    *,
    runtime: Guala,
    max_legacy_learned_escrow_bytes: int | None = None,
) -> VerifiedSource:
    all_measurements = _regular_tree_measurements(source)
    by_path = {
        measurement.path: measurement
        for measurement in all_measurements
    }
    missing_files = _SOURCE_REQUIRED_FILES - set(by_path)
    if missing_files:
        raise PhysicalStateMigrationError(
            "source generation is incomplete: "
            + ", ".join(sorted(missing_files))
        )
    groups = _owner_group_by_id()
    historical_paths = {
        groups[owner_id].relative_path
        for owner_id in HISTORICAL_SOURCE_OWNER_IDS
    }
    source_owner_paths = {
        measurement.path
        for measurement in all_measurements
        if measurement.path.startswith("owner_state/")
    }
    has_legacy_teaching = "guala_teaching.json" in by_path
    pre_owner_source = has_legacy_teaching and not source_owner_paths
    if source_owner_paths and source_owner_paths != historical_paths:
        missing = historical_paths - source_owner_paths
        unexpected = source_owner_paths - historical_paths
        details = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unexpected:
            details.append(
                "unexpected=" + ",".join(sorted(unexpected))
            )
        raise PhysicalStateMigrationError(
            "historical source owner file set changed: "
            + "; ".join(details)
        )

    identity, identity_record = _validate_identity_record(source)
    tick, state_file_ticks = _validate_legacy_core(
        source,
        identity=identity,
    )
    runtime._guala_identity = identity
    runtime._identity_record = dict(identity_record)
    runtime._expected_file_ticks = dict(state_file_ticks)

    legacy_learned_plan = None
    owner_bodies: dict[str, bytes] = {}
    owner_mutation_roots: dict[str, str] = {}
    initial_bodies = runtime._bounded_owner_state_bodies()
    articulatory_group = groups[RETIRED_ARTICULATORY_OWNER_ID]
    genesis_articulatory = json.loads(
        initial_bodies[articulatory_group.relative_path]
    )["state"]["articulatory_self_vocal"]

    if has_legacy_teaching:
        if (
            isinstance(max_legacy_learned_escrow_bytes, bool)
            or not isinstance(max_legacy_learned_escrow_bytes, int)
            or max_legacy_learned_escrow_bytes <= 0
        ):
            raise PhysicalStateMigrationError(
                "legacy learned-state source has no explicit sealed "
                "escrow byte ceiling"
            )
        try:
            legacy_learned_plan = build_legacy_learned_state_plan(
                source,
                identity=identity,
                tick=tick,
                authority_key=_authority_secret_from_environment(),
                max_sealed_escrow_bytes=(
                    max_legacy_learned_escrow_bytes
                ),
                runtime=runtime,
            )
        except LegacyLearnedStateUnresolved as error:
            plan = error.plan
            raise PhysicalStateMigrationError(
                str(error)
                + "; accounted_bytes="
                + str(plan.body["learned_source_bytes"])
                + "; gate_hmac="
                + plan.authority_hmac_sha256
            ) from error
        except LegacyLearnedStateGateError as error:
            raise PhysicalStateMigrationError(
                "legacy learned-state gate failed: " + str(error)
            ) from error
    if pre_owner_source:
        retired_motor = _retire_authenticated_articulatory_motor(
            genesis_articulatory,
            runtime=runtime,
            genesis_value=genesis_articulatory,
        )
    else:
        decoded_owner_state: dict[str, object] = {
            key: None for key in ACTIVE_OWNER_STATE_KEYS
        }
        decoded_owner_state.update({
            state_key: None
            for state_key, _path, _maximum_bytes
            in RAW_CURRENT_OWNER_SPECS
        })
        decoded_owner_state.update({
            "_legacy_missing_autonomous_experience_driver": True,
            "_legacy_missing_native_materialized_fabric": True,
            "_legacy_missing_organism_ordered_lived_experience": True,
            "_legacy_missing_whole_organism_internal_reentry": True,
            "_legacy_missing_causal_mosaic_tapestry": True,
            "_legacy_missing_causal_recognition_attention": True,
            "_legacy_missing_durable_sensed_consequence": True,
            "_legacy_missing_embodied_glyph_curriculum": True,
            "_legacy_missing_embodied_other_perspective": True,
            "_legacy_missing_embodied_reading_lesson_controller": True,
            "_legacy_missing_organism_dream_wake_weave": True,
            "_legacy_missing_whole_organism_neuron_population": True,
            "_legacy_missing_whole_organism_neurochemical": True,
            "_legacy_missing_whole_organism_reflection": True,
            "_legacy_missing_whole_organism_recovery": True,
            "_legacy_missing_whole_organism_structural": True,
            "_legacy_missing_whole_organism_thing_learning": True,
        })
        for owner_id in sorted(HISTORICAL_SOURCE_OWNER_IDS):
            group = groups[owner_id]
            if state_file_ticks.get(group.relative_path) != tick:
                raise PhysicalStateMigrationError(
                    "source owner tick differs from core: "
                    + group.relative_path
                )
            body, state, mutation_root = _read_canonical_owner_body(
                source,
                group,
            )
            owner_bodies[group.relative_path] = body
            owner_mutation_roots[group.relative_path] = mutation_root
            for key, value in state.items():
                if decoded_owner_state[key] is not None:
                    raise PhysicalStateMigrationError(
                        f"source owner state key overlaps: {key}"
                    )
                decoded_owner_state[key] = value

        sensory = decoded_owner_state[
            "causal_thing_sensory_expansion"
        ]
        if (
            isinstance(sensory, dict)
            and sensory.get("schema")
            == _SENSORY_EXPANSION_V1_ENVELOPE_SCHEMA
        ):
            _verify_and_admit_empty_sensory_expansion_v1(
                sensory,
                runtime=runtime,
            )
            decoded_owner_state[
                "causal_thing_sensory_expansion"
            ] = None
        passive_state = decoded_owner_state[
            "passive_whole_organism_thing_learning"
        ]
        if (
            isinstance(passive_state, dict)
            and isinstance(passive_state.get("body"), dict)
            and passive_state["body"].get("schema")
            == "guala.passive_thing_learning.state.v1"
        ):
            current_passive = (
                runtime._passive_whole_organism_thing_learning
            )
            migrated_passive = (
                PassiveWholeOrganismThingLearningOwner
                .migrate_authenticated_empty_v1_encoded(
                    authority_key=(
                        runtime._passive_thing_learning_authority_key
                    ),
                    profile=current_passive._profile,
                    partition_authority=(
                        runtime._thing_partition_authority
                    ),
                    thing_owner=runtime._causal_thing_mosaic_owner,
                    neuron_owner=(
                        runtime
                        ._whole_organism_neuron_population_owner
                    ),
                    encoded=_canonical(passive_state),
                )
            )
            decoded_owner_state[
                "passive_whole_organism_thing_learning"
            ] = json.loads(migrated_passive)
        retired_motor = _retire_authenticated_articulatory_motor(
            decoded_owner_state["articulatory_self_vocal"],
            runtime=runtime,
            genesis_value=genesis_articulatory,
        )
        decoded_owner_state[
            "articulatory_self_vocal"
        ] = genesis_articulatory
        try:
            PhysicalGualaRuntimeCore._restore_whole_organism_state(
                runtime,
                decoded_owner_state,
            )
            genesis_raw_bodies = _mint_current_raw_owner_genesis(
                runtime
            )
            for state_key, path, _maximum_bytes in RAW_CURRENT_OWNER_SPECS:
                decoded_owner_state[state_key] = genesis_raw_bodies[path]
            runtime._restore_whole_organism_state(decoded_owner_state)
        except Exception as error:
            raise PhysicalStateMigrationError(
                "source current-owner authority verification failed: "
                + str(error)
            ) from error

    try:
        runtime._verify_binary_binding(
            str(source / "guala_organism.sgr"),
            tick,
        )
        graph = by_path["guala_organism.sgr"]
        graph_inspection = inspect_authenticated_legacy_organism_graph(
            Embryo,
            source / "guala_organism.sgr",
        )
        graph_census = _structural_graph_census(graph_inspection)
    except Exception as error:
        raise PhysicalStateMigrationError(
            "source organism binding or graph verification failed: "
            + str(error)
        ) from error
    if graph_inspection.identity_uuid != identity:
        raise PhysicalStateMigrationError(
            "source organism identity differs from durable identity"
        )

    runtime.tick = tick
    runtime._last_save_tick = tick
    runtime._last_cold_save_tick = tick
    destination_state = runtime._bounded_owner_state_bodies()
    direct_translated_paths = (
        ()
        if legacy_learned_plan is None
        else tuple(sorted(
            legacy_learned_plan.direct_owner_bodies
        ))
    )
    if legacy_learned_plan is not None:
        for path, translated_body in (
            legacy_learned_plan.direct_owner_bodies.items()
        ):
            if path in destination_state:
                observed = destination_state[path]
            elif path == W1_COMPANION_AV_CONTINUITY_STATE_PATH:
                observed = (
                    runtime._w1_anonymous_av_continuity_owner
                    .encoded_snapshot()
                )
            else:
                raise PhysicalStateMigrationError(
                    "translated legacy owner has no current custody: "
                    + path
                )
            if observed != translated_body:
                raise PhysicalStateMigrationError(
                    "authenticated learned-owner translation differs "
                    f"from destination owner: {path}"
                )

    destination_genesis_paths = {
        *(
            CURRENT_GENESIS_EXTENSION_PATHS
            - set(direct_translated_paths)
        ),
        RETIRED_ARTICULATORY_OWNER_PATH,
    }
    destination_genesis_bodies = {
        path: destination_state[path]
        for path in destination_genesis_paths
        if path in destination_state
    }
    for _state_key, path, _maximum_bytes in RAW_CURRENT_OWNER_SPECS:
        if path not in direct_translated_paths:
            destination_genesis_bodies[path] = (
                runtime._bounded_owner_state_bodies()[path]
                if path in runtime._bounded_owner_state_bodies()
                else _mint_current_raw_owner_genesis(runtime)[path]
            )
    if runtime._articulatory_self_vocal_owner.programs:
        raise PhysicalStateMigrationError(
            "retired articulatory programs entered live runtime"
        )

    preserved_paths = {
        "guala_core.json",
        "guala_identity.json",
        *owner_bodies,
    }
    retired_components = tuple(
        measurement
        for measurement in all_measurements
        if measurement.path not in preserved_paths
    )
    return VerifiedSource(
        identity=identity,
        identity_record=identity_record,
        tick=tick,
        graph=graph,
        graph_census=graph_census,
        owner_bodies=owner_bodies,
        owner_mutation_roots=owner_mutation_roots,
        destination_genesis_bodies=destination_genesis_bodies,
        direct_translated_owner_paths=direct_translated_paths,
        legacy_learned_plan_record=(
            None
            if legacy_learned_plan is None
            else legacy_learned_plan.record()
        ),
        retired_articulatory_motor=retired_motor,
        retired_components=retired_components,
        source_tree_bytes=sum(
            measurement.bytes for measurement in all_measurements
        ),
        source_tree_root_sha256=_measurement_root(
            all_measurements,
            domain=_TREE_ROOT_DOMAIN,
        ),
    )


def _unified_core_state(
    root: Path,
) -> tuple[FileMeasurement, dict[str, object], dict[str, object], str]:
    measurement = _regular_file_measurement(root, "guala_core.json")
    encoded = (root / "guala_core.json").read_bytes()
    if (
        len(encoded) != measurement.bytes
        or _sha256_hex(encoded) != measurement.sha256
    ):
        raise PhysicalStateMigrationError(
            "unified organism core changed while reading"
        )
    try:
        core = json.loads(
            encoded,
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=_reject_json_constant,
        )
        mutation_root = whole_organism_mutation_root(encoded)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        WholeOrganismPersistenceError,
    ) as error:
        raise PhysicalStateMigrationError(
            "destination unified organism core is invalid: " + str(error)
        ) from error
    data = core.get("data") if isinstance(core, dict) else None
    organism_state = (
        data.get("organism_state") if isinstance(data, dict) else None
    )
    if not isinstance(organism_state, dict):
        raise PhysicalStateMigrationError(
            "destination unified organism state is absent"
        )
    return measurement, core, organism_state, mutation_root


def _manifest_measurements(
    root: Path,
) -> tuple[FileMeasurement, ...]:
    return tuple(
        _regular_file_measurement(root, path)
        for path in ("guala_core.json", "guala_identity.json")
    )


def _assert_no_retired_files(root: Path) -> None:
    present = sorted(
        relative
        for relative in Guala.RETIRED_BOOT_FILES
        if (root / relative).exists()
    )
    if present:
        raise PhysicalStateMigrationError(
            "retired runtime files entered the physical generation: "
            + ", ".join(present)
        )
    allowed = {
        "guala_core.json",
        "guala_identity.json",
        MIGRATION_PROOF_RELATIVE_PATH,
        CAUSAL_GENERATION_RECEIPT,
        *_MIGRATION_SEALED_OPERATIONAL_FILES,
    }
    actual = {
        measurement.path
        for measurement in _regular_tree_measurements(root)
    }
    unexpected = sorted(actual - allowed)
    if unexpected:
        raise PhysicalStateMigrationError(
            "non-unified files entered the physical generation: "
            + ", ".join(unexpected)
        )
    missing = {"guala_core.json", "guala_identity.json"} - actual
    if missing:
        raise PhysicalStateMigrationError(
            "unified physical generation is incomplete: "
            + ", ".join(sorted(missing))
        )
    if any(path.startswith("owner_state/") for path in actual):
        raise PhysicalStateMigrationError(
            "owner-scoped state remained active at destination"
        )


def _source_owner_import_evidence(
    verified_source: VerifiedSource,
    organism_state: Mapping[str, object],
) -> list[dict[str, object]]:
    try:
        target_bodies = owner_state_bodies(organism_state)
    except OwnerScopedPersistenceError as error:
        raise PhysicalStateMigrationError(
            "unified organism cannot account for authenticated source state: "
            + str(error)
        ) from error
    groups_by_path = {
        group.relative_path: group for group in OWNER_STATE_GROUPS
    }
    evidence = []
    for source_path, source_body in sorted(
        verified_source.owner_bodies.items()
    ):
        group = groups_by_path[source_path]
        target_body = target_bodies[source_path]
        if source_path == RETIRED_ARTICULATORY_OWNER_PATH:
            disposition = "authenticated_source_component_retired"
        elif target_body == source_body:
            disposition = "imported_exactly_into_unified_organism"
        elif group.owner_id in {
            "causal_thing_sensory_expansion",
            "embodiment_world",
        }:
            disposition = "authenticated_one_way_schema_translation"
        else:
            raise PhysicalStateMigrationError(
                "authenticated learned state changed during unified import: "
                + source_path
            )
        evidence.append({
            "disposition": disposition,
            "source_body_sha256": _sha256_hex(source_body),
            "source_mutation_root_sha256": (
                verified_source.owner_mutation_roots[source_path]
            ),
            "source_path": source_path,
            "target_mechanism_state_sha256": _sha256_hex(target_body),
        })
    return evidence


def _destination_whole_organism_record(
    final_root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    measurement, core, organism_state, mutation_root = (
        _unified_core_state(final_root)
    )
    data = core["data"]
    return ({
        "core": measurement.record(),
        "mutation_root_sha256": mutation_root,
        "organism_state_bytes": data["organism_state_bytes"],
        "organism_state_sha256": data["organism_state_sha256"],
        "state_file_count": 1,
    }, organism_state)


def _issue_purge_proof(
    *,
    verified_source: VerifiedSource,
    final_root: Path,
    authority_secret: str,
) -> dict[str, object]:
    final_manifest = _manifest_measurements(final_root)
    destination_record, organism_state = (
        _destination_whole_organism_record(final_root)
    )
    source_import_evidence = _source_owner_import_evidence(
        verified_source,
        organism_state,
    )
    raw_mechanism_bounds = {}
    for state_key, _legacy_path, maximum_bytes in RAW_CURRENT_OWNER_SPECS:
        value = organism_state.get(state_key)
        if value is None:
            raise PhysicalStateMigrationError(
                "destination unified organism lacks mechanism: " + state_key
            )
        actual_bytes = len(Guala._canonical_persistence_bytes(value))
        if actual_bytes > maximum_bytes:
            raise PhysicalStateMigrationError(
                "destination unified mechanism exceeded its byte boundary: "
                + state_key
            )
        raw_mechanism_bounds[state_key] = {
            "actual_bytes": actual_bytes,
            "maximum_bytes": maximum_bytes,
        }
    articulatory_target = organism_state.get("articulatory_self_vocal")
    body = {
        "destination_manifest": [
            measurement.record() for measurement in final_manifest
        ],
        "destination_manifest_root_sha256": _measurement_root(
            final_manifest,
            domain=_TREE_ROOT_DOMAIN,
        ),
        "destination_whole_organism": destination_record,
        "direct_translated_source_paths": list(
            verified_source.direct_translated_owner_paths
        ),
        "identity": verified_source.identity,
        "legacy_learned_state_gate": (
            verified_source.legacy_learned_plan_record
        ),
        "organism_graph_retirement": {
            "action": (
                "authenticated_source_graph_retired_not_loaded_or_emitted"
            ),
            "destination_present": False,
            "source": verified_source.graph_census,
        },
        "resource_proof": {
            "active_destination_manifest_bytes": sum(
                measurement.bytes for measurement in final_manifest
            ),
            "active_state_file_count": 1,
            "cold_restore_exact": True,
            "raw_mechanism_bounds": raw_mechanism_bounds,
            "retained_pcm_bytes": 0,
            "source_tree_bytes": verified_source.source_tree_bytes,
        },
        "retired_articulatory_motor": {
            **verified_source.retired_articulatory_motor.record(),
            "source_body_sha256": (
                _sha256_hex(
                    verified_source.owner_bodies[
                        RETIRED_ARTICULATORY_OWNER_PATH
                    ]
                )
                if RETIRED_ARTICULATORY_OWNER_PATH
                in verified_source.owner_bodies
                else None
            ),
            "source_mutation_root_sha256": (
                verified_source.owner_mutation_roots.get(
                    RETIRED_ARTICULATORY_OWNER_PATH
                )
            ),
            "target_mechanism_state_sha256": _sha256_hex(
                Guala._canonical_persistence_bytes(articulatory_target)
            ),
        },
        "retired_component_count": len(
            verified_source.retired_components
        ),
        "retired_component_root_sha256": _measurement_root(
            verified_source.retired_components,
            domain=_RETIRED_ROOT_DOMAIN,
        ),
        "retired_components": [
            measurement.record()
            for measurement in verified_source.retired_components
        ],
        "schema": MIGRATION_PROOF_SCHEMA,
        "source_owner_import_evidence": source_import_evidence,
        "source_tree_root_sha256": (
            verified_source.source_tree_root_sha256
        ),
        "tick": verified_source.tick,
    }
    return {
        "authority_hmac_sha256": hmac.new(
            _migration_key(authority_secret),
            _MIGRATION_PROOF_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest(),
        "body": body,
        "schema": MIGRATION_PROOF_SCHEMA,
    }


def verify_purge_proof(
    proof: Mapping[str, object],
    *,
    authority_secret: str,
    destination: Path | None = None,
) -> dict[str, object]:
    if not isinstance(proof, Mapping):
        raise PhysicalStateMigrationError(
            "migration proof is not an object"
        )
    supplied = dict(proof)
    if set(supplied) != {
        "authority_hmac_sha256",
        "body",
        "schema",
    }:
        raise PhysicalStateMigrationError(
            "migration proof fields changed"
        )
    if supplied.get("schema") != MIGRATION_PROOF_SCHEMA:
        raise PhysicalStateMigrationError(
            "migration proof schema changed"
        )
    body = supplied.get("body")
    signature = supplied.get("authority_hmac_sha256")
    expected_body_fields = {
        "destination_manifest",
        "destination_manifest_root_sha256",
        "destination_whole_organism",
        "direct_translated_source_paths",
        "identity",
        "legacy_learned_state_gate",
        "organism_graph_retirement",
        "resource_proof",
        "retired_articulatory_motor",
        "retired_component_count",
        "retired_component_root_sha256",
        "retired_components",
        "schema",
        "source_owner_import_evidence",
        "source_tree_root_sha256",
        "tick",
    }
    if (
        not isinstance(body, dict)
        or body.get("schema") != MIGRATION_PROOF_SCHEMA
        or set(body) != expected_body_fields
    ):
        raise PhysicalStateMigrationError(
            "migration proof body changed"
        )
    if not isinstance(signature, str) or len(signature) != 64:
        raise PhysicalStateMigrationError(
            "migration proof authentication is invalid"
        )
    expected = hmac.new(
        _migration_key(authority_secret),
        _MIGRATION_PROOF_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise PhysicalStateMigrationError(
            "migration proof authentication failed"
        )
    evidence = body.get("source_owner_import_evidence")
    if not isinstance(evidence, list):
        raise PhysicalStateMigrationError(
            "migration proof source import evidence changed"
        )
    evidence_paths = [
        record.get("source_path")
        for record in evidence
        if isinstance(record, dict)
    ]
    if (
        len(evidence_paths) != len(evidence)
        or evidence_paths != sorted(set(evidence_paths))
    ):
        raise PhysicalStateMigrationError(
            "migration proof source import evidence is not exact"
        )
    learned_gate = body.get("legacy_learned_state_gate")
    if learned_gate is None:
        expected_source_paths = sorted(
            _owner_group_by_id()[owner_id].relative_path
            for owner_id in HISTORICAL_SOURCE_OWNER_IDS
        )
        if evidence_paths != expected_source_paths:
            raise PhysicalStateMigrationError(
                "migration proof source owner evidence changed"
            )
        if body.get("direct_translated_source_paths") != []:
            raise PhysicalStateMigrationError(
                "migration proof introduced unverified source translations"
            )
    else:
        try:
            verified_gate = verify_legacy_learned_state_plan(
                learned_gate,
                authority_key=authority_secret,
            )
        except LegacyLearnedStateGateError as error:
            raise PhysicalStateMigrationError(
                "migration proof learned-state gate changed: " + str(error)
            ) from error
        translated = [
            record["path"]
            for record in verified_gate["direct_owner_bodies"]
        ]
        if body.get("direct_translated_source_paths") != translated:
            raise PhysicalStateMigrationError(
                "migration proof direct translations changed"
            )
    destination_record = body.get("destination_whole_organism")
    if (
        not isinstance(destination_record, dict)
        or destination_record.get("state_file_count") != 1
    ):
        raise PhysicalStateMigrationError(
            "migration proof unified destination changed"
        )
    if destination is not None:
        destination = Path(destination).resolve()
        _assert_no_retired_files(destination)
        manifest = _manifest_measurements(destination)
        if body.get("destination_manifest") != [
            measurement.record() for measurement in manifest
        ]:
            raise PhysicalStateMigrationError(
                "migration proof destination manifest changed"
            )
        if body.get(
            "destination_manifest_root_sha256"
        ) != _measurement_root(manifest, domain=_TREE_ROOT_DOMAIN):
            raise PhysicalStateMigrationError(
                "migration proof destination root changed"
            )
        observed_destination, _organism_state = (
            _destination_whole_organism_record(destination)
        )
        if destination_record != observed_destination:
            raise PhysicalStateMigrationError(
                "migration proof unified organism changed"
            )
    return body


def _idempotent_result_from_exact_seal(
    *,
    source: Path,
    destination: Path,
    authority_secret: str,
) -> MigrationResult:
    if destination.is_symlink() or not destination.is_dir():
        raise PhysicalStateMigrationError(
            "existing migration destination lacks an exact seal"
        )
    try:
        proof_path = destination / MIGRATION_PROOF_RELATIVE_PATH
        proof_measurement = _regular_file_measurement(
            destination,
            MIGRATION_PROOF_RELATIVE_PATH,
        )
        body = verify_purge_proof(
            _load_proof(proof_path),
            authority_secret=authority_secret,
            destination=destination,
        )
        source_root = _measurement_root(
            _regular_tree_measurements(source),
            domain=_TREE_ROOT_DOMAIN,
        )
    except PhysicalStateMigrationError as error:
        raise PhysicalStateMigrationError(
            "existing migration destination lacks the exact source seal: "
            + str(error)
        ) from error
    if body["source_tree_root_sha256"] != source_root:
        raise PhysicalStateMigrationError(
            "existing migration destination belongs to another source"
        )
    identity = body["identity"]
    tick = body["tick"]
    retired_component_count = body["retired_component_count"]
    if (
        not isinstance(identity, str)
        or isinstance(tick, bool)
        or not isinstance(tick, int)
        or tick < 0
        or isinstance(retired_component_count, bool)
        or not isinstance(retired_component_count, int)
        or retired_component_count < 0
    ):
        raise PhysicalStateMigrationError(
            "existing migration seal has an invalid identity or extent"
        )
    graph_records = [
        record
        for record in body["retired_components"]
        if record.get("path") == "guala_organism.sgr"
    ]
    if len(graph_records) != 1:
        raise PhysicalStateMigrationError(
            "migration seal lacks the retired source organism measurement"
        )
    return MigrationResult(
        destination=destination,
        identity=identity,
        tick=tick,
        retired_source_organism_sha256=graph_records[0]["sha256"],
        current_state_file_count=1,
        source_owner_evidence_count=len(
            body["source_owner_import_evidence"]
        ),
        retired_component_count=retired_component_count,
        proof_sha256=proof_measurement.sha256,
    )


def _write_proof(
    path: Path,
    proof: Mapping[str, object],
) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=False)
    encoded = _canonical(proof)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(encoded)
            target.flush()
            os.fsync(target.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _load_proof(path: Path) -> dict[str, object]:
    measurement = _regular_file_measurement(
        path.parent.parent,
        f"{path.parent.name}/{path.name}",
    )
    encoded = path.read_bytes()
    if (
        len(encoded) != measurement.bytes
        or _sha256_hex(encoded) != measurement.sha256
    ):
        raise PhysicalStateMigrationError(
            "migration proof changed while reading"
        )
    try:
        proof = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PhysicalStateMigrationError(
            "migration proof is unreadable"
        ) from error
    if _canonical(proof) != encoded:
        raise PhysicalStateMigrationError(
            "migration proof is not canonical"
        )
    return proof


def _strict_shutdown(runtime: Guala | None) -> None:
    if runtime is not None:
        runtime.strict_shutdown(timeout=30.0)


def _assert_genesis_extensions(
    runtime: Guala,
    expected_bodies: Mapping[str, bytes],
) -> None:
    bodies = runtime._bounded_owner_state_bodies()
    for path, expected in expected_bodies.items():
        if bodies.get(path) != expected:
            raise PhysicalStateMigrationError(
                f"destination genesis owner changed: {path}"
            )
    if runtime._articulatory_self_vocal_owner.programs:
        raise PhysicalStateMigrationError(
            "retired articulatory motor programs restored live"
        )
    if (
        runtime._embodied_vocal_body.status()[
            "completed_transient_count"
        ]
        != 0
        or runtime._experience_grown_vocal_motor_fragment.status()[
            "fragment_count"
        ]
        != 0
        or runtime._pending_body_owned_vocal_consequence.status()[
            "pending_count"
        ]
        != 0
        or runtime._w1_anonymous_av_continuity_owner.status()[
            "has_latest"
        ]
        is not False
        or runtime._w1_anonymous_av_continuity_owner.status()[
            "transitions"
        ]
        != 0
        or runtime._experience_grown_vocal_causal_relation.status()[
            "relation_count"
        ]
        != 0
        or runtime._passive_whole_organism_thing_learning.status()[
            "records"
        ]
        != 0
    ):
        raise PhysicalStateMigrationError(
            "destination vocal owner left authenticated genesis"
        )


def _migrate_physical_state_unbounded(
    source: Path,
    destination: Path,
    *,
    max_legacy_learned_escrow_bytes: int | None = None,
    max_migration_workspace_bytes: int | None = None,
) -> MigrationResult:
    """Migrate one verified generation without modifying its source."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise PhysicalStateMigrationError(
            "migration source and destination must differ"
        )
    if source in destination.parents or destination in source.parents:
        raise PhysicalStateMigrationError(
            "migration source and destination cannot contain one another"
        )
    if max_migration_workspace_bytes is not None and (
        isinstance(max_migration_workspace_bytes, bool)
        or not isinstance(max_migration_workspace_bytes, int)
        or max_migration_workspace_bytes <= 0
    ):
        raise PhysicalStateMigrationError(
            "migration workspace byte capacity must be positive"
        )
    authority_secret = _authority_secret_from_environment()
    if destination.exists() or destination.is_symlink():
        return _idempotent_result_from_exact_seal(
            source=source,
            destination=destination,
            authority_secret=authority_secret,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.is_symlink():
        raise PhysicalStateMigrationError(
            "migration destination parent cannot be a symlink"
        )
    lock_path = destination.parent / (
        f".{destination.name}.migration.lock"
    )
    lock_descriptor: int | None = None
    temporary_root: Path | None = None
    validator: Guala | None = None
    first_boot: Guala | None = None
    cold_restore: Guala | None = None
    try:
        try:
            lock_descriptor = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as error:
            raise PhysicalStateMigrationError(
                "another migration owns the destination lock"
            ) from error
        os.write(
            lock_descriptor,
            str(os.getpid()).encode("ascii"),
        )
        os.fsync(lock_descriptor)

        temporary_root = Path(tempfile.mkdtemp(
            prefix=f".{destination.name}.migration-",
            dir=destination.parent,
        ))
        first_generation = (
            temporary_root / "first-physical-generation"
        )
        final_generation = (
            temporary_root / "cold-roundtrip-generation"
        )

        validator = Guala()
        verified = _verify_source(
            source,
            runtime=validator,
            max_legacy_learned_escrow_bytes=(
                max_legacy_learned_escrow_bytes
            ),
        )
        if _measurement_root(
            _regular_tree_measurements(source),
            domain=_TREE_ROOT_DOMAIN,
        ) != verified.source_tree_root_sha256:
            raise PhysicalStateMigrationError(
                "migration source changed during verification"
            )
        validator.save_full_state(
            first_generation,
            publish_generation=False,
        )
        if (
            max_migration_workspace_bytes is not None
            and sum(
                measurement.bytes
                for measurement in _regular_tree_measurements(
                    temporary_root
                )
            )
            > max_migration_workspace_bytes
        ):
            raise PhysicalStateMigrationError(
                "first physical generation exceeded migration workspace "
                "capacity"
            )
        _assert_no_retired_files(first_generation)
        (
            _first_measurement,
            first_core,
            first_organism_state,
            first_mutation_root,
        ) = _unified_core_state(first_generation)
        if (
            first_core.get("guala_identity") != verified.identity
            or first_core.get("saved_at_tick") != verified.tick
        ):
            raise PhysicalStateMigrationError(
                "first unified state changed Guala identity or tick"
            )
        _source_owner_import_evidence(
            verified,
            first_organism_state,
        )
        _assert_genesis_extensions(
            validator,
            verified.destination_genesis_bodies,
        )

        _strict_shutdown(validator)
        validator = None

        first_boot = Guala()
        first_boot.load_full_state(first_generation)
        if (
            first_boot._guala_identity != verified.identity
            or first_boot.tick != verified.tick
        ):
            raise PhysicalStateMigrationError(
                "physical boot changed Guala identity or tick"
            )
        _assert_genesis_extensions(
            first_boot,
            verified.destination_genesis_bodies,
        )
        if max_migration_workspace_bytes is not None:
            shutil.rmtree(first_generation)
        first_boot.save_full_state(
            final_generation,
            publish_generation=False,
        )
        if (
            max_migration_workspace_bytes is not None
            and sum(
                measurement.bytes
                for measurement in _regular_tree_measurements(
                    temporary_root
                )
            )
            > max_migration_workspace_bytes
        ):
            raise PhysicalStateMigrationError(
                "cold-roundtrip generation exceeded migration workspace "
                "capacity"
            )
        _strict_shutdown(first_boot)
        first_boot = None
        _assert_no_retired_files(final_generation)
        (
            _final_measurement,
            final_core,
            final_organism_state,
            final_mutation_root,
        ) = _unified_core_state(final_generation)
        if (
            final_core.get("guala_identity") != verified.identity
            or final_core.get("saved_at_tick") != verified.tick
            or final_organism_state != first_organism_state
            or final_mutation_root != first_mutation_root
        ):
            raise PhysicalStateMigrationError(
                "unified organism changed during cold boot/save roundtrip"
            )

        proof = _issue_purge_proof(
            verified_source=verified,
            final_root=final_generation,
            authority_secret=authority_secret,
        )
        proof_path = (
            final_generation / MIGRATION_PROOF_RELATIVE_PATH
        )
        if (
            max_migration_workspace_bytes is not None
            and sum(
                measurement.bytes
                for measurement in _regular_tree_measurements(
                    temporary_root
                )
            )
            + len(_canonical(proof))
            > max_migration_workspace_bytes
        ):
            raise PhysicalStateMigrationError(
                "migration proof exceeded migration workspace capacity"
            )
        _write_proof(proof_path, proof)
        verify_purge_proof(
            _load_proof(proof_path),
            authority_secret=authority_secret,
            destination=final_generation,
        )

        cold_restore = Guala()
        cold_restore.load_full_state(final_generation)
        if (
            cold_restore._guala_identity != verified.identity
            or cold_restore.tick != verified.tick
            or cold_restore._whole_organism_persistence_payload()
            != final_organism_state
        ):
            raise PhysicalStateMigrationError(
                "cold restore changed the unified Guala organism"
            )
        _assert_genesis_extensions(
            cold_restore,
            verified.destination_genesis_bodies,
        )
        if _measurement_root(
            _regular_tree_measurements(source),
            domain=_TREE_ROOT_DOMAIN,
        ) != verified.source_tree_root_sha256:
            raise PhysicalStateMigrationError(
                "migration source changed before publication"
            )
        _strict_shutdown(cold_restore)
        cold_restore = None

        if destination.exists() or destination.is_symlink():
            raise PhysicalStateMigrationError(
                "migration destination appeared before atomic publication"
            )
        os.rename(final_generation, destination)
        proof_measurement = _regular_file_measurement(
            destination,
            MIGRATION_PROOF_RELATIVE_PATH,
        )
        verify_purge_proof(
            _load_proof(
                destination / MIGRATION_PROOF_RELATIVE_PATH
            ),
            authority_secret=authority_secret,
            destination=destination,
        )
        return MigrationResult(
            destination=destination,
            identity=verified.identity,
            tick=verified.tick,
            retired_source_organism_sha256=verified.graph.sha256,
            current_state_file_count=1,
            source_owner_evidence_count=len(
                proof["body"]["source_owner_import_evidence"]
            ),
            retired_component_count=len(
                verified.retired_components
            ),
            proof_sha256=proof_measurement.sha256,
        )
    finally:
        for runtime in (cold_restore, first_boot, validator):
            try:
                _strict_shutdown(runtime)
            except Exception:
                pass
        if temporary_root is not None and temporary_root.exists():
            shutil.rmtree(temporary_root)
        if lock_descriptor is not None:
            os.close(lock_descriptor)
        if lock_path.exists() and not lock_path.is_symlink():
            lock_path.unlink()


def migrate_physical_state(
    source: Path,
    destination: Path,
    *,
    max_legacy_learned_escrow_bytes: int | None = None,
    physical_byte_authority: PhysicalByteCeilingAuthority | None = None,
    max_migration_workspace_bytes: int | None = None,
) -> MigrationResult:
    """Migrate one source, optionally under shared physical-byte admission."""

    if physical_byte_authority is None:
        if max_migration_workspace_bytes is not None:
            raise PhysicalStateMigrationError(
                "migration workspace capacity requires physical-byte "
                "authority"
            )
        return _migrate_physical_state_unbounded(
            source,
            destination,
            max_legacy_learned_escrow_bytes=(
                max_legacy_learned_escrow_bytes
            ),
        )
    if not isinstance(
        physical_byte_authority,
        PhysicalByteCeilingAuthority,
    ):
        raise TypeError(
            "physical_byte_authority must be a "
            "PhysicalByteCeilingAuthority"
        )
    if (
        isinstance(max_migration_workspace_bytes, bool)
        or not isinstance(max_migration_workspace_bytes, int)
        or max_migration_workspace_bytes <= 0
    ):
        raise PhysicalStateMigrationError(
            "bounded migration requires a positive workspace byte capacity"
        )
    resolved_source = Path(source).resolve()
    resolved_destination_parent = Path(destination).parent.resolve(
        strict=True
    )
    try:
        resolved_source.relative_to(physical_byte_authority.scope_root)
        resolved_destination_parent.relative_to(
            physical_byte_authority.scope_root
        )
    except ValueError as error:
        raise PhysicalStateMigrationError(
            "bounded migration source and destination must remain inside "
            "the physical-byte scope"
        ) from error
    with physical_byte_authority.admitted_mutation(
        operation="one_way_physical_state_migration_workspace",
        requested_bytes=max_migration_workspace_bytes,
    ):
        return _migrate_physical_state_unbounded(
            resolved_source,
            Path(destination),
            max_legacy_learned_escrow_bytes=(
                max_legacy_learned_escrow_bytes
            ),
            max_migration_workspace_bytes=(
                max_migration_workspace_bytes
            ),
        )


def _canonical_uuid(value: object, description: str) -> str:
    if not isinstance(value, str):
        raise PhysicalStateMigrationError(f"{description} is not a UUID")
    try:
        canonical = str(uuid.UUID(value))
    except ValueError as error:
        raise PhysicalStateMigrationError(
            f"{description} is not a UUID"
        ) from error
    if canonical != value:
        raise PhysicalStateMigrationError(
            f"{description} is not canonical"
        )
    return value


def _canonical_digest(value: object, description: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PhysicalStateMigrationError(
            f"{description} is not a SHA-256 digest"
        )
    return value


def _nonnegative_tick(value: object, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PhysicalStateMigrationError(
            f"{description} is not a nonnegative integer"
        )
    return value


def _deployment_hmac_key(authority_secret: str) -> bytes:
    if not isinstance(authority_secret, str) or len(authority_secret) < 16:
        raise PhysicalStateMigrationError(
            "deployment control authority is absent"
        )
    return hashlib.sha256(
        (
            "guala-deployment-seal-v1\0" + authority_secret
        ).encode("utf-8")
    ).digest()


def validate_sealed_composite_evidence(
    *,
    source_generation: str,
    source_manifest_sha256: str,
    source_tick: int,
    deployment_baseline_generation: str,
    deployment_baseline_manifest_sha256: str,
    deployment_baseline_tick: int,
    active_recovery_generation: str,
    active_recovery_manifest_sha256: str,
    active_recovery_tick: int,
    active_recovery_is_overlay: bool,
) -> None:
    """Reject a baseline, overlay, or failed candidate as migration source."""
    source_generation = _canonical_uuid(
        source_generation,
        "sealed composite generation",
    )
    deployment_baseline_generation = _canonical_uuid(
        deployment_baseline_generation,
        "deployment baseline generation",
    )
    active_recovery_generation = _canonical_uuid(
        active_recovery_generation,
        "active recovery generation",
    )
    _canonical_digest(
        source_manifest_sha256,
        "sealed composite manifest",
    )
    _canonical_digest(
        deployment_baseline_manifest_sha256,
        "deployment baseline manifest",
    )
    _canonical_digest(
        active_recovery_manifest_sha256,
        "active recovery manifest",
    )
    source_tick = _nonnegative_tick(
        source_tick,
        "sealed composite tick",
    )
    deployment_baseline_tick = _nonnegative_tick(
        deployment_baseline_tick,
        "deployment baseline tick",
    )
    active_recovery_tick = _nonnegative_tick(
        active_recovery_tick,
        "active recovery tick",
    )
    if active_recovery_is_overlay is not True:
        raise PhysicalStateMigrationError(
            "the pre-seal active recovery overlay was not proven"
        )
    if active_recovery_generation == deployment_baseline_generation:
        raise PhysicalStateMigrationError(
            "active recovery evidence names only the deployment baseline"
        )
    if source_generation in {
        deployment_baseline_generation,
        active_recovery_generation,
    }:
        raise PhysicalStateMigrationError(
            "migration source must be the new full composite seal, not its "
            "baseline or recovery overlay"
        )
    if source_manifest_sha256 in {
        deployment_baseline_manifest_sha256,
        active_recovery_manifest_sha256,
    }:
        raise PhysicalStateMigrationError(
            "migration source manifest does not prove a new full composite "
            "seal"
        )
    if active_recovery_tick < deployment_baseline_tick:
        raise PhysicalStateMigrationError(
            "active recovery overlay precedes its deployment baseline"
        )
    if source_tick < active_recovery_tick:
        raise PhysicalStateMigrationError(
            "sealed composite precedes the active recovery overlay"
        )


def _isolated_cold_restore(
    generation,
    *,
    materialized_root: Path | None = None,
) -> bool:
    """Materialize and cold-boot one exact generation in a child process."""
    private_root = None
    try:
        if materialized_root is None:
            private_root = Path(tempfile.mkdtemp(
                prefix="guala-migration-cold-restore-",
            ))
            materialized_root = private_root / "active"
            materialize_verified_generation(
                generation=generation,
                active_directory=materialized_root,
            )
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsf_ai_service.cold_restore_probe",
                "--active-directory",
                str(materialized_root),
                "--expected-identity",
                generation.identity,
                "--expected-tick",
                str(generation.tick),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=540,
            env=os.environ.copy(),
        )
        if completed.returncode != 0:
            diagnostic = (
                (completed.stdout or "") + (completed.stderr or "")
            )[-4096:]
            raise PhysicalStateMigrationError(
                "isolated migrated-generation cold restore failed: "
                + (diagnostic or "no diagnostic output")
            )
        return True
    except subprocess.TimeoutExpired as error:
        raise PhysicalStateMigrationError(
            "isolated migrated-generation cold restore timed out"
        ) from error
    finally:
        if private_root is not None and private_root.exists():
            shutil.rmtree(private_root)


def _dynamic_store(
    *,
    store_root: Path,
    identity: str,
    max_generation_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
) -> ImmutableGenerationStore:
    return ImmutableGenerationStore(
        store_root,
        identity=identity,
        required_files=None,
        content_addressed=True,
        max_encoded_generation_bytes=max_generation_bytes,
        max_dynamic_required_files=MAX_COLD_REQUIRED_FILES,
        max_dynamic_path_bytes=MAX_COLD_REQUIRED_PATH_BYTES,
        physical_byte_ceiling=physical_byte_ceiling,
        physical_byte_scope=physical_byte_scope,
    )


def _active_regular_paths(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise PhysicalStateMigrationError(
            "active state path is not a real directory"
        )
    paths: set[str] = set()
    for directory, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(directory)
        if current.is_symlink() or not current.is_dir():
            raise PhysicalStateMigrationError(
                "active state contains an unsafe directory"
            )
        for name in directory_names:
            child = current / name
            if child.is_symlink():
                raise PhysicalStateMigrationError(
                    "active state contains a directory symlink"
                )
        for name in file_names:
            child = current / name
            info = child.lstat()
            if (
                child.is_symlink()
                or not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
            ):
                raise PhysicalStateMigrationError(
                    "active state contains an unsafe file"
                )
            paths.add(child.relative_to(root).as_posix())
    return paths


def _verify_exact_active_generation(
    active: Path,
    generation,
    *,
    allowed_extras: frozenset[str] = frozenset(),
    allowed_missing: frozenset[str] = frozenset(),
    allowed_differences: frozenset[str] = frozenset(),
) -> None:
    if (
        allowed_differences
        and allowed_differences
        != frozenset({CAUSAL_GENERATION_RECEIPT})
    ):
        raise PhysicalStateMigrationError(
            "only the causal generation receipt may differ during "
            "authenticated predecessor reconciliation"
        )
    actual = _active_regular_paths(active)
    required = set(generation.required_files)
    missing = required - actual - set(allowed_missing)
    unexpected = actual - required - set(allowed_extras)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unexpected:
            details.append(
                "unexpected=" + ",".join(sorted(unexpected))
            )
        raise PhysicalStateMigrationError(
            "active state differs from the verified generation: "
            + "; ".join(details)
        )
    for relative_path in generation.required_files:
        if relative_path not in actual:
            continue
        if relative_path in allowed_differences:
            continue
        if (
            not generation.content_addressed
            and relative_path.endswith(".json")
            and relative_path != CAUSAL_GENERATION_RECEIPT
        ):
            # Legacy-v1 envelopes authenticated the decoded JSON value and
            # discarded the writer's byte formatting.  Compare exactly at
            # that authenticated boundary and retain the active writer bytes.
            # Content-addressed generations and causal receipts remain
            # byte-exact.
            observed = _regular_file_measurement(
                active,
                relative_path,
            )
            (
                materialized_sha256,
                materialized_bytes,
            ) = _stream_materialized_file(
                generation,
                relative_path,
            )
            if (
                observed.bytes == materialized_bytes
                and observed.sha256 == materialized_sha256
            ):
                continue
            active_body = (active / relative_path).read_bytes()
            if (
                observed.bytes != len(active_body)
                or observed.sha256 != _sha256_hex(active_body)
            ):
                raise PhysicalStateMigrationError(
                    "active legacy JSON changed while reading at "
                    + relative_path
                )
            try:
                active_value = json.loads(
                    active_body,
                    parse_constant=_reject_json_constant,
                    object_pairs_hook=_reject_duplicate_json_members,
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as error:
                raise PhysicalStateMigrationError(
                    "active legacy JSON is not strict at "
                    + relative_path
                ) from error
            if _canonical(active_value) != _canonical(
                generation.payload(relative_path)
            ):
                raise PhysicalStateMigrationError(
                    "active state differs from the verified generation at "
                    + relative_path
                )
            continue
        expected_sha256, expected_bytes = _stream_materialized_file(
            generation,
            relative_path,
        )
        observed = _regular_file_measurement(active, relative_path)
        if (
            observed.bytes != expected_bytes
            or observed.sha256 != expected_sha256
        ):
            raise PhysicalStateMigrationError(
                "active state differs from the verified generation at "
                + relative_path
            )


def _bounded_materialized_generation_body(
    generation,
    relative_path: str,
    *,
    maximum_bytes: int,
) -> bytes:
    expected_sha256, expected_bytes = _stream_materialized_file(
        generation,
        relative_path,
    )
    if expected_bytes > maximum_bytes:
        raise PhysicalStateMigrationError(
            "materialized causal generation receipt exceeds its bound"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".guala-causal-generation-receipt-",
    )
    temporary = Path(temporary_name)
    try:
        try:
            observed_sha256, observed_bytes = _stream_materialized_file(
                generation,
                relative_path,
                destination_fd=descriptor,
            )
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if (
            observed_sha256 != expected_sha256
            or observed_bytes != expected_bytes
        ):
            raise PhysicalStateMigrationError(
                "materialized causal generation receipt changed while read"
            )
        body = temporary.read_bytes()
        if (
            len(body) != expected_bytes
            or hashlib.sha256(body).hexdigest() != expected_sha256
        ):
            raise PhysicalStateMigrationError(
                "materialized causal generation receipt measurement differs"
            )
        return body
    finally:
        temporary.unlink(missing_ok=True)


def _reconcile_authenticated_causal_receipt(
    *,
    active: Path,
    source,
    deployment_baseline=None,
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> None:
    relative_path = CAUSAL_GENERATION_RECEIPT
    source_receipt = _verified_generation_causal_receipt(
        source,
        "sealed source",
    )
    active_path = active / relative_path
    info = active_path.lstat()
    if (
        active_path.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_size > 64 * 1024
    ):
        raise PhysicalStateMigrationError(
            "active causal generation receipt is not one bounded "
            "regular file"
        )
    observed = _regular_file_measurement(active, relative_path)
    source_body = _bounded_materialized_generation_body(
        source,
        relative_path,
        maximum_bytes=64 * 1024,
    )
    source_measurement = (
        hashlib.sha256(source_body).hexdigest(),
        len(source_body),
    )
    observed_measurement = (observed.sha256, observed.bytes)
    if observed_measurement == source_measurement:
        return
    if deployment_baseline is None:
        raise PhysicalStateMigrationError(
            "stale active causal receipt lacks an authenticated deployment "
            "baseline"
        )
    baseline_receipt = _verified_generation_causal_receipt(
        deployment_baseline,
        "deployment baseline",
    )
    if (
        source_receipt.causal_state_sha256
        == baseline_receipt.causal_state_sha256
    ):
        if (
            source_receipt.state_revision
            != baseline_receipt.state_revision
        ):
            raise PhysicalStateMigrationError(
                "causally identical source and baseline receipts have "
                "different revisions"
            )
    elif (
        source_receipt.state_revision
        != baseline_receipt.state_revision + 1
    ):
        raise PhysicalStateMigrationError(
            "sealed source causal receipt is not the immediate successor "
            "of the deployment baseline"
        )
    baseline_body = _bounded_materialized_generation_body(
        deployment_baseline,
        relative_path,
        maximum_bytes=64 * 1024,
    )
    baseline_measurement = (
        hashlib.sha256(baseline_body).hexdigest(),
        len(baseline_body),
    )
    if observed_measurement != baseline_measurement:
        raise PhysicalStateMigrationError(
            "active causal generation receipt matches neither the "
            "authenticated baseline nor sealed source"
        )
    physical_byte_authority.atomic_replace_bytes(
        active_path,
        source_body,
        operation="advance_authenticated_causal_generation_receipt",
        mode=0o644,
    )
    advanced = _regular_file_measurement(active, relative_path)
    if (
        advanced.sha256 != source_measurement[0]
        or advanced.bytes != source_measurement[1]
    ):
        raise PhysicalStateMigrationError(
            "advanced causal generation receipt differs from sealed source"
        )


def _verified_generation_causal_receipt(
    generation,
    description: str,
):
    if CAUSAL_GENERATION_RECEIPT not in generation.required_files:
        raise PhysicalStateMigrationError(
            f"{description} has no causal generation receipt"
        )
    try:
        receipt = verified_causal_generation_receipt(generation)
    except Exception as error:
        raise PhysicalStateMigrationError(
            f"{description} causal generation receipt failed"
        ) from error
    if receipt is None:
        raise PhysicalStateMigrationError(
            f"{description} causal generation receipt is absent"
        )
    return receipt


def _verify_deployment_seal_causal_binding(
    *,
    generation,
    seal: Mapping[str, Any],
    description: str,
) -> None:
    if CAUSAL_GENERATION_RECEIPT not in generation.required_files:
        return
    receipt = _verified_generation_causal_receipt(
        generation,
        description,
    )
    expected = {
        "state_revision": receipt.state_revision,
        "causal_state_sha256": receipt.causal_state_sha256,
        "operational_metadata_sha256": (
            receipt.operational_metadata_sha256
        ),
    }
    for field, value in expected.items():
        if seal.get(field) != value:
            raise PhysicalStateMigrationError(
                f"{description} deployment seal {field} mismatch"
            )


def _restore_sealed_operational_files(
    *,
    active: Path,
    source,
    missing: set[str],
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> None:
    if not missing:
        return
    if not missing.issubset(_MIGRATION_SEALED_OPERATIONAL_FILES):
        raise PhysicalStateMigrationError(
            "refusing to restore a non-operational missing file"
        )
    for relative_path in sorted(missing):
        physical_byte_authority.atomic_replace_bytes(
            active / relative_path,
            source.stored_bytes(relative_path),
            operation=(
                "restore_authenticated_sealed_operational_file:"
                + relative_path
            ),
            mode=0o644,
        )
    _verify_exact_active_generation(
        active,
        source,
        allowed_extras=_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS,
    )


def _materialize_migration_source(
    *,
    active: Path,
    source,
    physical_byte_authority: PhysicalByteCeilingAuthority,
    retirable_runtime_paths: tuple[str, ...] = (),
):
    materialized = materialize_verified_generation(
        generation=source,
        active_directory=active,
        physical_byte_authority=physical_byte_authority,
        retirable_runtime_paths=retirable_runtime_paths,
    )
    if not source.content_addressed:
        required_paths = set(source.required_files)
        for group in OWNER_STATE_GROUPS:
            relative_path = group.relative_path
            if relative_path not in required_paths:
                continue
            physical_byte_authority.atomic_replace_bytes(
                active / relative_path,
                _canonical(source.payload(relative_path)),
                operation=(
                    "restore_legacy_owner_canonical_body:"
                    + relative_path
                ),
                mode=0o600,
            )
    _verify_exact_active_generation(
        active,
        source,
        allowed_extras=frozenset(retirable_runtime_paths),
    )
    return materialized


def _ensure_source_active_materialization(
    *,
    active: Path,
    source,
    deployment_baseline=None,
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> None:
    active.parent.mkdir(parents=True, exist_ok=True)
    if active.exists():
        actual = _active_regular_paths(active)
        if actual:
            receipt_present = (
                CAUSAL_GENERATION_RECEIPT
                in set(source.required_files)
            )
            receipt_differences = (
                frozenset({CAUSAL_GENERATION_RECEIPT})
                if receipt_present
                else frozenset()
            )
            missing_operational = (
                (set(source.required_files) - actual)
                & _MIGRATION_SEALED_OPERATIONAL_FILES
            )
            _verify_exact_active_generation(
                active,
                source,
                allowed_extras=_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS,
                allowed_missing=_MIGRATION_SEALED_OPERATIONAL_FILES,
                allowed_differences=receipt_differences,
            )
            if receipt_present:
                _reconcile_authenticated_causal_receipt(
                    active=active,
                    source=source,
                    deployment_baseline=deployment_baseline,
                    physical_byte_authority=physical_byte_authority,
                )
            if not missing_operational:
                _verify_exact_active_generation(
                    active,
                    source,
                    allowed_extras=(
                        _MIGRATION_OPERATIONAL_ACTIVE_EXTRAS
                    ),
                )
                return
            _restore_sealed_operational_files(
                active=active,
                source=source,
                missing=missing_operational,
                physical_byte_authority=physical_byte_authority,
            )
            return
    _materialize_migration_source(
        active=active,
        source=source,
        physical_byte_authority=physical_byte_authority,
        retirable_runtime_paths=tuple(
            sorted(_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS)
        ),
    )


def _verified_generation_content_fingerprints(
    generation,
) -> dict[str, tuple[str, int]]:
    certificate = generation.recovery_certificate()
    records = certificate.get("required_files")
    if not isinstance(records, list):
        raise PhysicalStateMigrationError(
            "verified generation certificate has no required-file records"
        )
    fingerprints = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise PhysicalStateMigrationError(
                "verified generation file record is malformed"
            )
        path = record.get("relative_path")
        digest = record.get("sha256")
        size = record.get("size_bytes")
        if (
            not isinstance(path, str)
            or not isinstance(digest, str)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or path in fingerprints
        ):
            raise PhysicalStateMigrationError(
                "verified generation file custody is ambiguous"
            )
        fingerprints[path] = (digest, size)
    if set(fingerprints) != set(generation.required_files):
        raise PhysicalStateMigrationError(
            "verified generation certificate path census changed"
        )
    return fingerprints


def _activate_migrated_generation(
    *,
    active: Path,
    source,
    destination,
    migration_proof: Mapping[str, object],
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> None:
    _verify_exact_active_generation(
        active,
        source,
        allowed_extras=_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS,
    )
    retired_records = migration_proof.get("retired_components")
    if not isinstance(retired_records, list):
        raise PhysicalStateMigrationError(
            "migration proof has no retired-component custody"
        )
    retired_paths = {
        record.get("path")
        for record in retired_records
        if isinstance(record, Mapping)
        and isinstance(record.get("path"), str)
    }
    if len(retired_paths) != len(retired_records):
        raise PhysicalStateMigrationError(
            "migration retired-component paths are ambiguous"
        )
    imported_source_records = migration_proof.get(
        "source_owner_import_evidence"
    )
    if not isinstance(imported_source_records, list):
        raise PhysicalStateMigrationError(
            "migration proof has no authenticated source import custody"
        )
    imported_source_paths = {
        record.get("source_path")
        for record in imported_source_records
        if isinstance(record, Mapping)
        and isinstance(record.get("source_path"), str)
    }
    if len(imported_source_paths) != len(imported_source_records):
        raise PhysicalStateMigrationError(
            "migration source import paths are ambiguous"
        )
    retired_active_paths = retired_paths | imported_source_paths
    source_fingerprints = _verified_generation_content_fingerprints(source)
    destination_fingerprints = (
        _verified_generation_content_fingerprints(destination)
    )
    expected_retired = (
        set(source.required_files) - set(destination.required_files)
    )
    if (
        CAUSAL_GENERATION_RECEIPT in source_fingerprints
        and CAUSAL_GENERATION_RECEIPT in destination_fingerprints
        and source_fingerprints[CAUSAL_GENERATION_RECEIPT]
        != destination_fingerprints[CAUSAL_GENERATION_RECEIPT]
    ):
        expected_retired.add(CAUSAL_GENERATION_RECEIPT)
    if retired_active_paths != expected_retired:
        raise PhysicalStateMigrationError(
            "migration proof does not authorize the exact active paths "
            "that destination replacement retires"
        )
    materialize_verified_generation(
        generation=destination,
        active_directory=active,
        physical_byte_authority=physical_byte_authority,
        retirable_runtime_paths=tuple(sorted(
            (
                retired_active_paths - set(destination.required_files)
            )
            | _MIGRATION_OPERATIONAL_ACTIVE_EXTRAS
        )),
    )
    _verify_exact_active_generation(active, destination)


def _restore_source_active_materialization(
    *,
    active: Path,
    source,
    deployment_baseline=None,
    destination,
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> None:
    if not active.exists() or not _active_regular_paths(active):
        _ensure_source_active_materialization(
            active=active,
            source=source,
            deployment_baseline=deployment_baseline,
            physical_byte_authority=physical_byte_authority,
        )
        return
    try:
        _ensure_source_active_materialization(
            active=active,
            source=source,
            deployment_baseline=deployment_baseline,
            physical_byte_authority=physical_byte_authority,
        )
        return
    except PhysicalStateMigrationError as source_error:
        try:
            _verify_exact_active_generation(
                active,
                destination,
                allowed_extras=_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS,
            )
        except PhysicalStateMigrationError as destination_error:
            raise PhysicalStateMigrationError(
                "rollback active state matches neither authenticated "
                f"generation: source={source_error}; "
                f"destination={destination_error}"
            ) from destination_error
    destination_only = set(destination.required_files) - set(
        source.required_files
    )
    _materialize_migration_source(
        active=active,
        source=source,
        physical_byte_authority=physical_byte_authority,
        retirable_runtime_paths=tuple(sorted(
            destination_only | _MIGRATION_OPERATIONAL_ACTIVE_EXTRAS
        )),
    )
    _verify_exact_active_generation(
        active,
        source,
        allowed_extras=_MIGRATION_OPERATIONAL_ACTIVE_EXTRAS,
    )


def _authenticated_deployment_baseline(
    *,
    store_root: Path,
    store,
    source,
    generation_uuid: str,
    manifest_sha256: str,
    tick: int,
    hmac_key: bytes,
):
    baseline = store.verify_generation(_canonical_uuid(
        generation_uuid,
        "deployment baseline generation",
    ))
    if (
        baseline.generation_uuid == source.generation_uuid
        or baseline.manifest_sha256
        != _canonical_digest(
            manifest_sha256,
            "deployment baseline manifest",
        )
        or baseline.tick != tick
        or baseline.tick > source.tick
        or baseline.identity != source.identity
    ):
        raise PhysicalStateMigrationError(
            "authenticated deployment baseline differs"
        )
    seal = load_generation_deployment_seal(
        store_root,
        baseline.generation_uuid,
        hmac_key=hmac_key,
    )
    for field in (
        "generation_uuid",
        "identity",
        "manifest_sha256",
        "tick",
    ):
        if seal.get(field) != getattr(baseline, field):
            raise PhysicalStateMigrationError(
                f"deployment baseline seal {field} mismatch"
            )
    _verify_deployment_seal_causal_binding(
        generation=baseline,
        seal=seal,
        description="deployment baseline",
    )
    return baseline


def _authenticated_post_rollback_retry_custody(
    *,
    store,
    source,
    hmac_key: bytes,
    physical_byte_authority: PhysicalByteCeilingAuthority,
    live_recovery_root: Path,
    cutover_intent_path: Path,
) -> None:
    """Prove the retired baseline through the exact prior migration custody."""
    custody = authenticated_terminal_same_source_retry_custody(
        live_recovery_root=live_recovery_root,
        intent_path=cutover_intent_path,
        source=source,
        hmac_key=hmac_key,
    )
    destination_record = custody["destination"]
    destination = store.verify_generation(
        destination_record["generation_uuid"]
    )
    for field in (
        "generation_uuid",
        "identity",
        "manifest_sha256",
        "tick",
    ):
        if getattr(destination, field) != destination_record[field]:
            raise PhysicalStateMigrationError(
                "same-source retry destination custody differs at " + field
            )
    verification_root = Path(tempfile.mkdtemp(
        prefix=".guala-migration-retry-custody-",
        dir=physical_byte_authority.scope_root,
    ))
    try:
        source_active = verification_root / "source"
        destination_active = verification_root / "destination"
        _materialize_migration_source(
            source=source,
            active=source_active,
            physical_byte_authority=physical_byte_authority,
        )
        materialize_verified_generation(
            generation=destination,
            active_directory=destination_active,
            physical_byte_authority=physical_byte_authority,
        )
        proof = verify_purge_proof(
            _load_proof(
                destination_active / MIGRATION_PROOF_RELATIVE_PATH
            ),
            authority_secret=_authority_secret_from_environment(),
            destination=destination_active,
        )
        source_root = _measurement_root(
            _regular_tree_measurements(source_active),
            domain=_TREE_ROOT_DOMAIN,
        )
        if proof["source_tree_root_sha256"] != source_root:
            raise PhysicalStateMigrationError(
                "same-source retry destination does not authenticate the "
                "restored source"
            )
    finally:
        with physical_byte_authority.exclusive_writer():
            if verification_root.exists():
                shutil.rmtree(verification_root)


def production_handoff(
    *,
    store_root: Path,
    expected_source_generation: str,
    expected_source_manifest_sha256: str,
    expected_source_identity: str,
    expected_source_tick: int,
    deployment_baseline_generation: str,
    deployment_baseline_manifest_sha256: str,
    deployment_baseline_tick: int,
    active_recovery_generation: str,
    active_recovery_manifest_sha256: str,
    active_recovery_tick: int,
    active_recovery_is_overlay: bool,
    s3_client: Any,
    bucket: str,
    prefix: str,
    nonce: str,
    max_generation_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
    active_directory: Path,
    live_recovery_root: Path,
    cutover_intent_path: Path,
    retired_archive_prefix: str,
) -> ProductionHandoffResult:
    """Publish a cold-proven current-schema successor of one exact seal."""
    validate_sealed_composite_evidence(
        source_generation=expected_source_generation,
        source_manifest_sha256=expected_source_manifest_sha256,
        source_tick=expected_source_tick,
        deployment_baseline_generation=deployment_baseline_generation,
        deployment_baseline_manifest_sha256=(
            deployment_baseline_manifest_sha256
        ),
        deployment_baseline_tick=deployment_baseline_tick,
        active_recovery_generation=active_recovery_generation,
        active_recovery_manifest_sha256=(
            active_recovery_manifest_sha256
        ),
        active_recovery_tick=active_recovery_tick,
        active_recovery_is_overlay=active_recovery_is_overlay,
    )
    store_root = Path(store_root).resolve()
    physical_byte_scope = Path(physical_byte_scope).resolve()
    source = discover_and_load_current(store_root).generation
    if (
        source.generation_uuid != expected_source_generation
        or source.manifest_sha256 != expected_source_manifest_sha256
        or source.identity != expected_source_identity
        or source.tick != expected_source_tick
    ):
        raise PhysicalStateMigrationError(
            "CURRENT is not the exact newly successful composite seal"
        )
    authority_secret = _authority_secret_from_environment()
    deployment_key = _deployment_hmac_key(authority_secret)
    source_seal = load_generation_deployment_seal(
        store_root,
        source.generation_uuid,
        hmac_key=deployment_key,
        expected_nonce=nonce,
    )
    for field in (
        "generation_uuid",
        "identity",
        "manifest_sha256",
        "tick",
    ):
        if source_seal.get(field) != getattr(source, field):
            raise PhysicalStateMigrationError(
                f"source deployment seal {field} mismatch"
            )
    _verify_deployment_seal_causal_binding(
        generation=source,
        seal=source_seal,
        description="source",
    )
    generation_store = _dynamic_store(
        store_root=store_root,
        identity=expected_source_identity,
        max_generation_bytes=max_generation_bytes,
        physical_byte_ceiling=physical_byte_ceiling,
        physical_byte_scope=physical_byte_scope,
    )
    physical_byte_authority = PhysicalByteCeilingAuthority(
        physical_byte_scope,
        physical_byte_ceiling,
    )
    try:
        _authenticated_deployment_baseline(
            store_root=store_root,
            store=generation_store,
            source=source,
            generation_uuid=deployment_baseline_generation,
            manifest_sha256=deployment_baseline_manifest_sha256,
            tick=deployment_baseline_tick,
            hmac_key=deployment_key,
        )
    except GenerationValidationError as error:
        baseline_uuid = _canonical_uuid(
            deployment_baseline_generation,
            "deployment baseline generation",
        )
        baseline_path = (
            store_root / GENERATIONS_DIRECTORY / baseline_uuid
        )
        if baseline_path.exists() or baseline_path.is_symlink():
            raise PhysicalStateMigrationError(
                "retained deployment baseline failed authentication"
            ) from error
        _authenticated_post_rollback_retry_custody(
            store=generation_store,
            source=source,
            hmac_key=deployment_key,
            physical_byte_authority=physical_byte_authority,
            live_recovery_root=live_recovery_root,
            cutover_intent_path=cutover_intent_path,
        )
    source_materialization_root = Path(tempfile.mkdtemp(
        prefix=".guala-migration-source-",
        dir=physical_byte_authority.scope_root,
    ))
    migration_root = Path(tempfile.mkdtemp(
        prefix=".guala-migration-destination-",
        dir=physical_byte_authority.scope_root,
    ))
    source_active = source_materialization_root / "active"
    migrated_active = migration_root / "current-schema"
    try:
        materialized = _materialize_migration_source(
            source=source,
            active=source_active,
            physical_byte_authority=physical_byte_authority,
        )
        if (
            materialized.generation_uuid != source.generation_uuid
            or materialized.manifest_sha256 != source.manifest_sha256
        ):
            raise PhysicalStateMigrationError(
                "source materialization differs from the sealed generation"
            )
        source_before = source.recovery_certificate_bytes()
        migrated = migrate_physical_state(
            source_active,
            migrated_active,
            max_legacy_learned_escrow_bytes=max_generation_bytes,
            physical_byte_authority=physical_byte_authority,
            max_migration_workspace_bytes=max_generation_bytes,
        )
        migration_proof = verify_purge_proof(
            _load_proof(
                migrated_active / MIGRATION_PROOF_RELATIVE_PATH
            ),
            authority_secret=authority_secret,
            destination=migrated_active,
        )
        _materialize_migration_source(
            active=Path(active_directory).resolve(),
            source=source,
            physical_byte_authority=physical_byte_authority,
            retirable_runtime_paths=tuple(sorted(
                _MIGRATION_OPERATIONAL_ACTIVE_EXTRAS
            )),
        )
        retired_archive = _archive_retired_source(
            source,
            s3_client=s3_client,
            bucket=bucket,
            authority_secret=authority_secret,
            archive_root_prefix=retired_archive_prefix,
            max_total_archive_bytes=max_generation_bytes,
        )
        if (
            retired_archive.source_generation_uuid
            != source.generation_uuid
            or retired_archive.identity != source.identity
            or retired_archive.tick != source.tick
            or retired_archive.manifest_sha256
            != source.manifest_sha256
        ):
            raise PhysicalStateMigrationError(
                "retired archive receipt differs from the sealed source"
            )

        def save_candidate(stage: Path, admission) -> int:
            for measurement in _regular_tree_measurements(
                migrated_active
            ):
                admission.copy_regular_file(
                    migrated_active / measurement.path,
                    stage / measurement.path,
                    logical_path=measurement.path,
                )
            return migrated.tick

        def validate_candidate(generation) -> bool:
            if generation.generation_uuid == source.generation_uuid:
                raise PhysicalStateMigrationError(
                    "migration destination reused the source generation"
                )
            candidate_root = Path(tempfile.mkdtemp(
                prefix=".guala-migration-candidate-",
                dir=physical_byte_authority.scope_root,
            ))
            try:
                active = candidate_root / "active"
                physical_byte_authority.admit(
                    operation=(
                        "materialize_migration_candidate_under_shared_lock"
                    ),
                    requested_bytes=sum(
                        int(record["size_bytes"])
                        for record in generation.recovery_certificate()[
                            "required_files"
                        ]
                    ),
                )
                materialize_verified_generation(
                    generation=generation,
                    active_directory=active,
                )
                proof = verify_purge_proof(
                    _load_proof(
                        active / MIGRATION_PROOF_RELATIVE_PATH
                    ),
                    authority_secret=authority_secret,
                    destination=active,
                )
                if (
                    proof["identity"] != source.identity
                    or proof["tick"] != source.tick
                ):
                    raise PhysicalStateMigrationError(
                        "migration proof differs from sealed source"
                    )
                return _isolated_cold_restore(
                    generation,
                    materialized_root=active,
                )
            finally:
                if candidate_root.exists():
                    shutil.rmtree(candidate_root)

        def publish_and_activate():
            publication = stage_authoritative_commit_upload(
                store_root=store_root,
                identity=source.identity,
                save_callback=save_candidate,
                s3_client=s3_client,
                bucket=bucket,
                prefix=prefix,
                hmac_key=deployment_key,
                nonce=nonce,
                max_encoded_generation_bytes=max_generation_bytes,
                max_dynamic_required_files=MAX_COLD_REQUIRED_FILES,
                max_dynamic_path_bytes=MAX_COLD_REQUIRED_PATH_BYTES,
                cold_restore_validator=validate_candidate,
                physical_byte_ceiling=physical_byte_ceiling,
                physical_byte_scope=physical_byte_scope,
                allow_equal_tick_schema_migration=True,
            )
            _activate_migrated_generation(
                active=Path(active_directory).resolve(),
                source=source,
                destination=publication.generation,
                migration_proof=migration_proof,
                physical_byte_authority=physical_byte_authority,
            )
            return publication

        live_cutover = publish_after_source_overlay_retirement(
            live_recovery_root=Path(live_recovery_root).resolve(),
            intent_path=Path(cutover_intent_path).resolve(),
            source=source,
            hmac_key=deployment_key,
            physical_byte_authority=physical_byte_authority,
            publish_destination=publish_and_activate,
        )
        published = live_cutover.publication
        destination = published.generation
        if destination.generation_uuid == source.generation_uuid:
            raise PhysicalStateMigrationError(
                "migration destination is not distinct from source"
            )
        source_after = _dynamic_store(
            store_root=store_root,
            identity=source.identity,
            max_generation_bytes=max_generation_bytes,
            physical_byte_ceiling=physical_byte_ceiling,
            physical_byte_scope=physical_byte_scope,
        ).verify_generation(source.generation_uuid)
        if source_after.recovery_certificate_bytes() != source_before:
            raise PhysicalStateMigrationError(
                "immutable source changed during production handoff"
            )
        if discover_and_load_current(
            store_root
        ).generation.generation_uuid != destination.generation_uuid:
            raise PhysicalStateMigrationError(
                "published migration destination is not CURRENT"
            )
        return ProductionHandoffResult(
            source_generation=source.generation_uuid,
            source_manifest_sha256=source.manifest_sha256,
            destination_generation=destination.generation_uuid,
            destination_manifest_sha256=destination.manifest_sha256,
            identity=destination.identity,
            tick=destination.tick,
            active_recovery_generation=(
                live_cutover.source_overlay_generation
            ),
            active_recovery_manifest_sha256=(
                live_cutover.source_overlay_manifest_sha256
            ),
            active_recovery_tick=live_cutover.source_overlay_tick,
            migration_proof_sha256=migrated.proof_sha256,
            live_recovery_cutover_intent_sha256=(
                live_cutover.intent_sha256
            ),
            retired_archive_prefix=retired_archive.versioned_prefix,
            retired_archive_receipt_hmac_sha256=(
                retired_archive.receipt_hmac_sha256
            ),
            retired_archive_source_tree_sha256=(
                retired_archive.source_tree_sha256
            ),
            retired_archive_storage_mode=(
                retired_archive.source_storage_mode
            ),
            retired_archive_total_bytes=(
                retired_archive.total_archive_bytes
            ),
        )
    finally:
        with physical_byte_authority.exclusive_writer():
            for root in (migration_root, source_materialization_root):
                if root.exists():
                    shutil.rmtree(root)


def rollback_production_handoff(
    *,
    store_root: Path,
    expected_source_generation: str,
    expected_source_manifest_sha256: str,
    expected_source_identity: str,
    expected_source_tick: int,
    deployment_baseline_generation: str,
    deployment_baseline_manifest_sha256: str,
    deployment_baseline_tick: int,
    s3_client: Any,
    bucket: str,
    prefix: str,
    max_generation_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
    active_directory: Path,
    live_recovery_root: Path,
    cutover_intent_path: Path,
) -> dict[str, object]:
    """Restore CURRENT and its seal pointer without deleting either generation."""
    store_root = Path(store_root).resolve()
    current = discover_and_load_current(store_root).generation
    if current.identity != expected_source_identity:
        raise PhysicalStateMigrationError(
            "rollback CURRENT identity differs from the source"
        )
    store = _dynamic_store(
        store_root=store_root,
        identity=expected_source_identity,
        max_generation_bytes=max_generation_bytes,
        physical_byte_ceiling=physical_byte_ceiling,
        physical_byte_scope=physical_byte_scope,
    )
    source = store.verify_generation(
        _canonical_uuid(
            expected_source_generation,
            "rollback source generation",
        )
    )
    if (
        source.manifest_sha256
        != _canonical_digest(
            expected_source_manifest_sha256,
            "rollback source manifest",
        )
        or source.tick != expected_source_tick
    ):
        raise PhysicalStateMigrationError(
            "rollback source generation proof differs"
        )
    physical_byte_authority = PhysicalByteCeilingAuthority(
        Path(physical_byte_scope).resolve(),
        physical_byte_ceiling,
    )
    migration_was_published = (
        current.generation_uuid != source.generation_uuid
    )
    authority_secret = _authority_secret_from_environment()
    deployment_key = _deployment_hmac_key(authority_secret)
    if not migration_was_published:
        _authenticated_deployment_baseline(
            store_root=store_root,
            store=store,
            source=source,
            generation_uuid=deployment_baseline_generation,
            manifest_sha256=deployment_baseline_manifest_sha256,
            tick=deployment_baseline_tick,
            hmac_key=deployment_key,
        )
    if migration_was_published:
        verification_root = Path(tempfile.mkdtemp(
            prefix=".guala-migration-rollback-",
            dir=physical_byte_authority.scope_root,
        ))
        try:
            source_active = verification_root / "source"
            current_active = verification_root / "current"
            _materialize_migration_source(
                source=source,
                active=source_active,
                physical_byte_authority=physical_byte_authority,
            )
            materialize_verified_generation(
                generation=current,
                active_directory=current_active,
                physical_byte_authority=physical_byte_authority,
            )
            body = verify_purge_proof(
                _load_proof(
                    current_active / MIGRATION_PROOF_RELATIVE_PATH
                ),
                authority_secret=_authority_secret_from_environment(),
                destination=current_active,
            )
            source_root = _measurement_root(
                _regular_tree_measurements(source_active),
                domain=_TREE_ROOT_DOMAIN,
            )
            if body["source_tree_root_sha256"] != source_root:
                raise PhysicalStateMigrationError(
                    "CURRENT is not the authenticated migration of the "
                    "rollback source"
                )
        finally:
            with physical_byte_authority.exclusive_writer():
                if verification_root.exists():
                    shutil.rmtree(verification_root)
    rollback_live_recovery = None
    if migration_was_published:
        def restore_source():
            _restore_source_active_materialization(
                active=Path(active_directory).resolve(),
                source=source,
                destination=current,
                physical_byte_authority=physical_byte_authority,
            )
            store.publish(source)
            return source

        rollback_live_recovery = (
            restore_source_after_destination_overlay_custody(
                live_recovery_root=Path(live_recovery_root).resolve(),
                intent_path=Path(cutover_intent_path).resolve(),
                source=source,
                destination=current,
                hmac_key=deployment_key,
                physical_byte_authority=physical_byte_authority,
                restore_source=restore_source,
            )
        )
    else:
        _materialize_migration_source(
            active=Path(active_directory).resolve(),
            source=source,
            physical_byte_authority=physical_byte_authority,
            retirable_runtime_paths=tuple(sorted(
                _MIGRATION_OPERATIONAL_ACTIVE_EXTRAS
            )),
        )
    source_seal = load_generation_deployment_seal(
        store_root,
        source.generation_uuid,
        hmac_key=deployment_key,
    )
    certificate = _canonical(source_seal)
    persist_deployment_seal(
        store_root,
        certificate,
        hmac_key=deployment_key,
        expected_nonce=base64.b64decode(
            source_seal["nonce_base64"],
            validate=True,
        ),
        physical_byte_authority=physical_byte_authority,
    )
    if migration_was_published:
        retained = tuple(sorted({
            source.generation_uuid,
            current.generation_uuid,
        }))
        reconcile_generation_deployment_seals(
            store_root,
            retained_generation_uuids=retained,
            physical_byte_authority=physical_byte_authority,
        )
        reconcile_remote_generation_prefixes(
            s3_client=s3_client,
            bucket=bucket,
            prefix=prefix,
            retained_generation_uuids=retained,
            maximum_objects_per_generation=(
                MAX_COLD_REQUIRED_FILES + 1
            ),
        )
    restored = discover_and_load_current(store_root).generation
    if restored.recovery_certificate_bytes() != source.recovery_certificate_bytes():
        raise PhysicalStateMigrationError(
            "rollback did not restore the exact source generation"
        )
    return {
        "destination_generation_retained": (
            None
            if current.generation_uuid == source.generation_uuid
            else current.generation_uuid
        ),
        "identity": source.identity,
        "source_generation": source.generation_uuid,
        "source_manifest_sha256": source.manifest_sha256,
        "tick": source.tick,
        "live_recovery_overlay_disposition": (
            None
            if rollback_live_recovery is None
            else rollback_live_recovery.overlay_disposition
        ),
        "live_recovery_quarantined_path": (
            None
            if rollback_live_recovery is None
            else rollback_live_recovery.quarantined_path
        ),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate one authenticated Guala generation into the bounded "
            "physical runtime without executing retired cognition."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--production-handoff", action="store_true")
    mode.add_argument("--rollback-handoff", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--store-root", type=Path)
    parser.add_argument("--expected-source-generation")
    parser.add_argument("--expected-source-manifest")
    parser.add_argument("--expected-source-identity")
    parser.add_argument("--expected-source-tick", type=int)
    parser.add_argument("--deployment-baseline-generation")
    parser.add_argument("--deployment-baseline-manifest")
    parser.add_argument("--deployment-baseline-tick", type=int)
    parser.add_argument("--active-recovery-generation")
    parser.add_argument("--active-recovery-manifest")
    parser.add_argument("--active-recovery-tick", type=int)
    parser.add_argument("--active-recovery-is-overlay", action="store_true")
    parser.add_argument("--bucket")
    parser.add_argument("--prefix")
    parser.add_argument("--nonce")
    parser.add_argument("--max-generation-bytes", type=int)
    parser.add_argument(
        "--max-legacy-learned-escrow-bytes",
        type=int,
    )
    parser.add_argument("--physical-byte-ceiling", type=int)
    parser.add_argument("--physical-byte-scope", type=Path)
    parser.add_argument("--active-directory", type=Path)
    parser.add_argument("--live-recovery-root", type=Path)
    parser.add_argument("--cutover-intent-path", type=Path)
    parser.add_argument("--retired-archive-prefix")
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    try:
        if arguments.production_handoff:
            import boto3
            result = production_handoff(
                store_root=arguments.store_root,
                expected_source_generation=(
                    arguments.expected_source_generation
                ),
                expected_source_manifest_sha256=(
                    arguments.expected_source_manifest
                ),
                expected_source_identity=(
                    arguments.expected_source_identity
                ),
                expected_source_tick=arguments.expected_source_tick,
                deployment_baseline_generation=(
                    arguments.deployment_baseline_generation
                ),
                deployment_baseline_manifest_sha256=(
                    arguments.deployment_baseline_manifest
                ),
                deployment_baseline_tick=(
                    arguments.deployment_baseline_tick
                ),
                active_recovery_generation=(
                    arguments.active_recovery_generation
                ),
                active_recovery_manifest_sha256=(
                    arguments.active_recovery_manifest
                ),
                active_recovery_tick=arguments.active_recovery_tick,
                active_recovery_is_overlay=(
                    arguments.active_recovery_is_overlay
                ),
                s3_client=boto3.client("s3", region_name="us-east-1"),
                bucket=arguments.bucket,
                prefix=arguments.prefix,
                nonce=arguments.nonce,
                max_generation_bytes=arguments.max_generation_bytes,
                physical_byte_ceiling=arguments.physical_byte_ceiling,
                physical_byte_scope=arguments.physical_byte_scope,
                active_directory=arguments.active_directory,
                live_recovery_root=arguments.live_recovery_root,
                cutover_intent_path=arguments.cutover_intent_path,
                retired_archive_prefix=(
                    arguments.retired_archive_prefix
                ),
            )
            payload = {
                **result.record(),
                "schema": PRODUCTION_HANDOFF_SCHEMA,
                "status": "migrated",
            }
        elif arguments.rollback_handoff:
            import boto3
            rollback = rollback_production_handoff(
                store_root=arguments.store_root,
                expected_source_generation=(
                    arguments.expected_source_generation
                ),
                expected_source_manifest_sha256=(
                    arguments.expected_source_manifest
                ),
                expected_source_identity=(
                    arguments.expected_source_identity
                ),
                expected_source_tick=arguments.expected_source_tick,
                deployment_baseline_generation=(
                    arguments.deployment_baseline_generation
                ),
                deployment_baseline_manifest_sha256=(
                    arguments.deployment_baseline_manifest
                ),
                deployment_baseline_tick=(
                    arguments.deployment_baseline_tick
                ),
                s3_client=boto3.client("s3", region_name="us-east-1"),
                bucket=arguments.bucket,
                prefix=arguments.prefix,
                max_generation_bytes=arguments.max_generation_bytes,
                physical_byte_ceiling=arguments.physical_byte_ceiling,
                physical_byte_scope=arguments.physical_byte_scope,
                active_directory=arguments.active_directory,
                live_recovery_root=arguments.live_recovery_root,
                cutover_intent_path=arguments.cutover_intent_path,
            )
            payload = {
                **rollback,
                "schema": PRODUCTION_ROLLBACK_SCHEMA,
                "status": "rolled_back",
            }
        else:
            if arguments.source is None or arguments.destination is None:
                raise PhysicalStateMigrationError(
                    "--source and --destination are required"
                )
            result = migrate_physical_state(
                arguments.source,
                arguments.destination,
                max_legacy_learned_escrow_bytes=(
                    arguments.max_legacy_learned_escrow_bytes
                ),
            )
            payload = {
                **result.record(),
                "schema": "guala.physical_state_migration.success.v3",
                "status": "migrated",
            }
    except PhysicalStateMigrationError as error:
        print(_canonical({
            "error": str(error),
            "schema": "guala.physical_state_migration.failure.v3",
            "status": "failed",
        }).decode("ascii"))
        return 2
    print(_canonical(payload).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
