"""Exact owner and role authority for production generation paths.

This registry is intentionally declarative.  A path is admitted only when
exactly one specification owns it.  Multi-owner convenience files remain
visible as ``requires_split`` and cannot issue an owner snapshot receipt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable
from typing import Mapping


OWNER_STATE_SNAPSHOT_RECEIPT_SCHEMA = (
    "guala.owner_state_snapshot_receipt.v1"
)
_OWNER_RECEIPT_DOMAIN = b"guala-owner-state-snapshot-receipt-v1\0"

ROLE_CONFIG = "configuration"
ROLE_DYNAMIC = "dynamic_state"
ROLE_IDENTITY = "identity"
ROLE_LEARNED = "learned_state"
ROLE_MIGRATION = "migration_evidence"
ROLE_RECEIPT = "receipt_metadata"
ROLE_RETIRED = "retired_nonauthoritative_placeholder"


class OwnerScopedPersistenceError(RuntimeError):
    """A persisted path has ambiguous, absent, or invalid ownership."""


@dataclass(frozen=True, slots=True)
class PathOwnership:
    selector: str
    prefix: bool
    role: str
    owner_ids: tuple[str, ...]
    stable_body_required: bool
    requires_split: bool = False

    def matches(self, relative_path: str) -> bool:
        if self.prefix:
            return relative_path.startswith(self.selector)
        return relative_path == self.selector


@dataclass(frozen=True, slots=True)
class OwnerStateSnapshotReceipt:
    identity: str
    owner_id: str
    relative_path: str
    role: str
    body_sha256: str
    body_bytes: int
    mutation_root_sha256: str
    frozen_tick: int
    authority_hmac_sha256: str
    schema: str = OWNER_STATE_SNAPSHOT_RECEIPT_SCHEMA

    def record(self) -> dict:
        return {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "body_bytes": self.body_bytes,
            "body_sha256": self.body_sha256,
            "frozen_tick": self.frozen_tick,
            "identity": self.identity,
            "mutation_root_sha256": self.mutation_root_sha256,
            "owner_id": self.owner_id,
            "relative_path": self.relative_path,
            "role": self.role,
            "schema": self.schema,
        }


@dataclass(frozen=True, slots=True)
class OwnerStateGroup:
    owner_id: str
    state_keys: tuple[str, ...]
    mutation_root_field: str

    @property
    def relative_path(self) -> str:
        return f"owner_state/{self.owner_id}.json"


@dataclass(frozen=True, slots=True)
class _FrozenPathContract:
    top_level_fields: frozenset[str]
    schema_path: tuple[str, ...]
    schema: str
    mutation_root_path: tuple[str, ...]
    receipt_path: tuple[str, ...] | None = None


OWNER_STATE_BODY_SCHEMA = "guala.owner_state_body.v1"
LEGACY_MISSING_CAUSAL_THING_ACTION_INTENT_PATH = (
    "owner_state/causal_thing_action_intents.json"
)
LEGACY_MISSING_CAUSAL_THING_SENSORY_EXPANSION_PATH = (
    "owner_state/causal_thing_sensory_expansion.json"
)
LEGACY_MISSING_CAUSAL_THING_LIVED_CONTEXT_PATH = (
    "owner_state/causal_thing_lived_context.json"
)
LEGACY_MISSING_PENDING_ARTICULATORY_ATTEMPT_PATH = (
    "owner_state/pending_articulatory_causal_attempt.json"
)
LEGACY_MISSING_CUSTODY_NATIVE_TUTORING_PATH = (
    "owner_state/custody_native_tutoring_curriculum.json"
)
LEGACY_MISSING_EMBODIMENT_CAUSAL_SEQUENCE_PATH = (
    "owner_state/embodiment_outcome_causal_sequence.json"
)
LEGACY_MISSING_CUSTODY_TUTORING_ACTION_LATCH_PATH = (
    "owner_state/custody_native_tutoring_action_selector.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_RECOVERY_PATH = (
    "owner_state/whole_organism_recovery.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_STRUCTURAL_PATH = (
    "owner_state/whole_organism_structural_perturbation.json"
)
LEGACY_MISSING_CAUSAL_MOSAIC_TAPESTRY_PATH = (
    "owner_state/causal_mosaic_tapestry.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_THING_MOSAIC_LEARNING_PATH = (
    "owner_state/whole_organism_thing_mosaic_learning.json"
)
LEGACY_MISSING_ORGANISM_DREAM_WAKE_WEAVE_PATH = (
    "owner_state/organism_dream_wake_weave.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_NEURON_POPULATION_PATH = (
    "owner_state/whole_organism_neuron_population.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_NEUROCHEMICAL_PATH = (
    "owner_state/whole_organism_neurochemical_mount.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_REFLECTION_PATH = (
    "owner_state/whole_organism_reflection_monitor.json"
)
LEGACY_MISSING_AUTONOMOUS_EXPERIENCE_DRIVER_PATH = (
    "owner_state/autonomous_experience_driver.json"
)
LEGACY_MISSING_WHOLE_ORGANISM_INTERNAL_REENTRY_PATH = (
    "owner_state/whole_organism_internal_reentry.json"
)
LEGACY_MISSING_CAUSAL_RECOGNITION_ATTENTION_PATH = (
    "owner_state/causal_recognition_attention.json"
)
LEGACY_MISSING_EMBODIED_OTHER_PERSPECTIVE_PATH = (
    "owner_state/embodied_other_perspective.json"
)
LEGACY_MISSING_DURABLE_SENSED_CONSEQUENCE_PATH = (
    "owner_state/durable_sensed_consequence.json"
)
LEGACY_MISSING_EMBODIED_GLYPH_CURRICULUM_PATH = (
    "owner_state/embodied_glyph_curriculum.json"
)
LEGACY_MISSING_EMBODIED_READING_LESSON_CONTROLLER_PATH = (
    "owner_state/embodied_reading_lesson_controller.json"
)
LEGACY_MISSING_NATIVE_MATERIALIZED_FABRIC_PATH = (
    "owner_state/native_materialized_fabric.json"
)

_FROZEN_PATH_CONTRACTS = {
    "owner_state/pending_body_owned_vocal_consequence.state": (
        _FrozenPathContract(
            frozenset({"body", "schema", "state_hmac_sha256"}),
            ("schema",),
            "guala.pending_body_owned_vocal_consequence.state_hmac.v2",
            ("state_hmac_sha256",),
        )
    ),
    "owner_state/w1_companion_av_continuity.state": (
        _FrozenPathContract(
            frozenset({
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "payload",
            }),
            ("payload", "schema"),
            "guala.w1.anonymous_audiovisual_continuity.snapshot.v2",
            ("authority_hmac_sha256",),
            ("authority_receipt_sha256",),
        )
    ),
    "owner_state/experience_grown_vocal_causal_relation.state": (
        _FrozenPathContract(
            frozenset({"body", "schema", "state_hmac_sha256"}),
            ("schema",),
            "guala.experience_grown_vocal_causal_relation.state_hmac.v1",
            ("state_hmac_sha256",),
        )
    ),
    "owner_state/organism_ordered_lived_experience.state": (
        _FrozenPathContract(
            frozenset({"body", "schema", "state_hmac_sha256"}),
            ("schema",),
            "guala.organism_ordered_lived_experience.state_hmac.v1",
            ("state_hmac_sha256",),
        )
    ),
}

OWNER_STATE_GROUPS = (
    OwnerStateGroup(
        "auditory_recurrent_motif",
        ("auditory_recurrent_motif",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "auditory_temporal_relation_assembly",
        ("auditory_temporal_relation_assembly",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "auditory_w1_binaural_peak_bank",
        ("auditory_w1_binaural_peak_bank_state",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_thing_mosaic",
        ("causal_thing_mosaic",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_thing_sensory_expansion",
        ("causal_thing_sensory_expansion",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_thing_lived_context",
        ("causal_thing_lived_context",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_thing_action_intents",
        ("causal_thing_action_intents",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "anonymous_passive_window",
        ("anonymous_passive_window",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_inquiry",
        ("causal_inquiry",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "articulatory_self_vocal",
        ("articulatory_self_vocal",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "articulatory_consequence_closure",
        ("articulatory_consequence_closure",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "lived_vocal_teaching",
        ("lived_vocal_teaching",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "grounded_articulatory_vocal_turn",
        ("grounded_articulatory_vocal_turn",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "pending_articulatory_causal_attempt",
        ("pending_articulatory_causal_attempt",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "custody_native_tutoring_curriculum",
        ("custody_native_tutoring_curriculum",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodiment_outcome_causal_sequence",
        ("embodiment_outcome_causal_sequence",),
        "state_sha256",
    ),
    OwnerStateGroup(
        "custody_native_tutoring_action_selector",
        ("custody_native_tutoring_action_selector",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_action_cycle",
        (
            "causal_action_cycle",
            "causal_action_cycle_pending_review",
        ),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_action_dispatcher",
        ("causal_action_dispatcher",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodiment_world",
        ("embodiment_world",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "physical_internal_body_state",
        ("physical_internal_body_state",),
        "cold_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_episode",
        ("whole_organism_episode",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_recovery",
        ("whole_organism_recovery",),
        "cold_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_structural_perturbation",
        ("whole_organism_structural_perturbation",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_mosaic_tapestry",
        ("causal_mosaic_tapestry",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_thing_mosaic_learning",
        ("whole_organism_thing_mosaic_learning",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "organism_dream_wake_weave",
        ("organism_dream_wake_weave",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_neuron_population",
        ("whole_organism_neuron_population",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "native_materialized_fabric",
        ("native_materialized_fabric",),
        "state_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_neurochemical_mount",
        ("whole_organism_neurochemical_mount",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_reflection_monitor",
        ("whole_organism_reflection_monitor",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "autonomous_experience_driver",
        ("autonomous_experience_driver",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "whole_organism_internal_reentry",
        ("whole_organism_internal_reentry",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_recognition_attention",
        ("causal_recognition_attention",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodied_other_perspective",
        ("embodied_other_perspective",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "durable_sensed_consequence",
        ("durable_sensed_consequence",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodied_glyph_curriculum",
        ("embodied_glyph_curriculum",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodied_reading_lesson_controller",
        ("embodied_reading_lesson_controller",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "w1_binaural_auditory_l5",
        ("w1_binaural_auditory_l5",),
        "state_receipt_sha256",
    ),
    OwnerStateGroup(
        "visual_region_continuity",
        (
            "visual_region_continuity",
            "latest_visual_region_observation",
        ),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "embodied_action_teaching",
        ("embodied_action_teaching",),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "causal_deliberation",
        ("causal_deliberation",),
        "state_hmac_sha256",
    ),
    OwnerStateGroup(
        "autonomous_causal_play",
        ("autonomous_causal_play", "causal_play_observation"),
        "authority_hmac_sha256",
    ),
    OwnerStateGroup(
        "full_field_prediction",
        (
            "full_field_prediction",
            "latest_full_field_prediction",
        ),
        "authority_hmac_sha256",
    ),
)

ACTIVE_OWNER_STATE_KEYS = frozenset(
    key
    for group in OWNER_STATE_GROUPS
    for key in group.state_keys
)


TEACHING_MONOLITH_OWNERS = (
    "auditory_recurrent_motif",
    "auditory_temporal_relation_assembly",
    "auditory_w1_binaural_peak_bank",
    "autonomous_causal_play",
    "autonomous_experience_driver",
    "causal_action_cycle",
    "causal_action_dispatcher",
    "causal_deliberation",
    "causal_thing_mosaic",
    "causal_thing_sensory_expansion",
    "causal_thing_lived_context",
    "causal_thing_action_intents",
    "anonymous_passive_window",
    "causal_inquiry",
    "articulatory_self_vocal",
    "articulatory_consequence_closure",
    "lived_vocal_teaching",
    "grounded_articulatory_vocal_turn",
    "pending_articulatory_causal_attempt",
    "custody_native_tutoring_curriculum",
    "embodiment_outcome_causal_sequence",
    "custody_native_tutoring_action_selector",
    "embodied_action_teaching",
    "embodiment_world",
    "physical_internal_body_state",
    "whole_organism_episode",
    "whole_organism_recovery",
    "whole_organism_structural_perturbation",
    "causal_mosaic_tapestry",
    "whole_organism_thing_mosaic_learning",
    "organism_dream_wake_weave",
    "whole_organism_neuron_population",
    "whole_organism_neurochemical_mount",
    "whole_organism_reflection_monitor",
    "whole_organism_internal_reentry",
    "causal_recognition_attention",
    "embodied_other_perspective",
    "durable_sensed_consequence",
    "embodied_glyph_curriculum",
    "full_field_prediction",
    "visual_region_continuity",
    "w1_binaural_auditory_l5",
)


PATH_OWNERSHIP_REGISTRY = (
    PathOwnership(
        "CAUSAL_GENERATION.json", False, ROLE_RECEIPT,
        ("causal_generation_authority",), False,
    ),
    PathOwnership(
        "guala_identity.json", False, ROLE_IDENTITY,
        ("guala_identity_authority",), False,
    ),
    PathOwnership(
        "guala_core.json", False, ROLE_DYNAMIC,
        ("guala_runtime_checkpoint_metadata",), False,
    ),
    PathOwnership(
        "guala_needs.json", False, ROLE_DYNAMIC,
        ("homeostatic_checkpoint_state",), False,
    ),
    PathOwnership(
        "guala_coordinator.json", False, ROLE_DYNAMIC,
        ("substrate_coordinator_checkpoint_metadata",), False,
    ),
    PathOwnership(
        "guala_bucket.json", False, ROLE_RETIRED,
        ("retired_question_bucket_marker",), False,
    ),
    PathOwnership(
        "guala_survival.json", False, ROLE_RETIRED,
        ("retired_deep_survival_history",), False,
    ),
    PathOwnership(
        "guala_atlas.json", False, ROLE_RETIRED,
        ("retired_living_atlas",), False,
    ),
    PathOwnership(
        "guala_sections.json", False, ROLE_RETIRED,
        ("retired_word_labelled_sections",), False,
    ),
    PathOwnership(
        "guala_deep_atlas.json", False, ROLE_RETIRED,
        ("retired_deep_atlas",), False,
    ),
    PathOwnership(
        "wave_atlas.npz", False, ROLE_RETIRED,
        ("retired_wave_atlas",), False,
    ),
    PathOwnership(
        "wave_atlas.npz.binding.json", False, ROLE_RECEIPT,
        ("retired_wave_atlas_binding",), False,
    ),
    PathOwnership(
        "guala_organism.sgr", False, ROLE_RETIRED,
        ("retired_organism_structural_graph",), False,
    ),
    PathOwnership(
        "guala_organism.sgr.binding.json", False, ROLE_RETIRED,
        ("retired_organism_structural_graph_binding",), False,
    ),
    PathOwnership(
        "guala_tapestry.sgr", False, ROLE_DYNAMIC,
        ("tapestry_structural_graph",), True,
    ),
    PathOwnership(
        "guala_tapestry.sgr.binding.json", False, ROLE_RECEIPT,
        ("tapestry_structural_graph",), False,
    ),
    PathOwnership(
        "guala_visual.json", False, ROLE_LEARNED,
        ("visual_experience_library",), True,
    ),
    PathOwnership(
        "guala_sight_motifs.json", False, ROLE_LEARNED,
        ("visual_motif_field",), True,
    ),
    PathOwnership(
        "guala_sounds.json", False, ROLE_LEARNED,
        ("auditory_experience_library",), True,
    ),
    PathOwnership(
        "guala_videos.json", False, ROLE_LEARNED,
        ("audiovisual_experience_library",), True,
    ),
    PathOwnership(
        "guala_episodic.json", False, ROLE_LEARNED,
        ("episodic_experience_memory",), True,
    ),
    PathOwnership(
        "guala_teaching.json", False, ROLE_LEARNED,
        TEACHING_MONOLITH_OWNERS, True, True,
    ),
    PathOwnership(
        "world_state.json", False, ROLE_DYNAMIC,
        ("embodiment_world_file",), True,
    ),
    PathOwnership(
        "curriculum_progress.json", False, ROLE_DYNAMIC,
        ("tutoring_curriculum_progress",), True,
    ),
    PathOwnership(
        "curriculum.json", False, ROLE_CONFIG,
        ("tutoring_curriculum_definition",), False,
    ),
    PathOwnership(
        "guala_runtime_config.json", False, ROLE_CONFIG,
        ("runtime_configuration",), False,
    ),
    PathOwnership(
        "dream_gate_cleared.json", False, ROLE_DYNAMIC,
        ("dream_gate_state",), True,
    ),
    PathOwnership(
        ".sleeping", False, ROLE_DYNAMIC,
        ("sleep_checkpoint_marker",), False,
    ),
    PathOwnership(
        "assets/", True, ROLE_LEARNED,
        ("sensory_media_assets",), True,
    ),
    PathOwnership(
        "sounds/", True, ROLE_LEARNED,
        ("raw_auditory_experience_assets",), True,
    ),
    PathOwnership(
        "legacy_cognition_archive/", True, ROLE_MIGRATION,
        ("legacy_cognition_migration_custody",), False,
    ),
    PathOwnership(
        "receipts/causal_generation_mutation.v2.json",
        False,
        ROLE_RECEIPT,
        ("causal_generation_mutation_authority",),
        False,
    ),
    PathOwnership(
        "receipts/owner_state/", True, ROLE_RECEIPT,
        ("owner_state_snapshot_receipt_store",), False,
    ),
    PathOwnership(
        "owner_state/embodied_vocal_body.state",
        False,
        ROLE_DYNAMIC,
        ("embodied_vocal_body",),
        True,
    ),
    PathOwnership(
        "owner_state/experience_grown_vocal_motor_fragment.state",
        False,
        ROLE_LEARNED,
        ("experience_grown_vocal_motor_fragment",),
        True,
    ),
    PathOwnership(
        "owner_state/pending_body_owned_vocal_consequence.state",
        False,
        ROLE_DYNAMIC,
        ("pending_body_owned_vocal_consequence",),
        True,
    ),
    PathOwnership(
        "owner_state/w1_companion_av_continuity.state",
        False,
        ROLE_LEARNED,
        ("w1_anonymous_audiovisual_continuity",),
        True,
    ),
    PathOwnership(
        "owner_state/experience_grown_vocal_causal_relation.state",
        False,
        ROLE_LEARNED,
        ("experience_grown_vocal_causal_relation",),
        True,
    ),
    PathOwnership(
        "owner_state/passive_whole_organism_thing_learning.state",
        False,
        ROLE_LEARNED,
        ("passive_whole_organism_thing_learning",),
        True,
    ),
    PathOwnership(
        "owner_state/organism_ordered_lived_experience.state",
        False,
        ROLE_LEARNED,
        ("organism_ordered_lived_experience",),
        True,
    ),
) + tuple(
    PathOwnership(
        group.relative_path,
        False,
        ROLE_LEARNED,
        (group.owner_id,),
        True,
    )
    for group in OWNER_STATE_GROUPS
)


def _path(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or value != value.strip()
    ):
        raise OwnerScopedPersistenceError(
            "persistence path is invalid"
        )
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or ".." in parsed.parts
        or parsed.as_posix() != value
    ):
        raise OwnerScopedPersistenceError(
            "persistence path is invalid"
        )
    return value


def ownership_for_path(relative_path: str) -> PathOwnership:
    relative = _path(relative_path)
    matches = tuple(
        record
        for record in PATH_OWNERSHIP_REGISTRY
        if record.matches(relative)
    )
    if len(matches) != 1:
        raise OwnerScopedPersistenceError(
            f"persistence path {relative!r} has {len(matches)} owners"
        )
    ownership = matches[0]
    if not ownership.owner_ids or len(set(ownership.owner_ids)) != len(
        ownership.owner_ids
    ):
        raise OwnerScopedPersistenceError(
            f"persistence path {relative!r} has invalid owner IDs"
        )
    return ownership


def census_generation_path_ownership(
    relative_paths: Iterable[str],
) -> dict[str, PathOwnership]:
    paths = tuple(relative_paths)
    if len(set(paths)) != len(paths):
        raise OwnerScopedPersistenceError(
            "generation path census contains duplicates"
        )
    return {
        path: ownership_for_path(path)
        for path in sorted(paths)
    }


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def owner_state_bodies(
    teaching_payload: Mapping[str, object],
) -> dict[str, bytes]:
    """Split the active teaching graph into stable single-owner bodies."""
    if not isinstance(teaching_payload, Mapping):
        raise TypeError("teaching payload must be a mapping")
    missing = ACTIVE_OWNER_STATE_KEYS - set(teaching_payload)
    if missing:
        raise OwnerScopedPersistenceError(
            "teaching payload is missing active owner keys: "
            + ", ".join(sorted(missing))
        )
    bodies = {}
    for group in OWNER_STATE_GROUPS:
        state = {
            key: teaching_payload[key]
            for key in group.state_keys
        }
        bodies[group.relative_path] = _canonical({
            "owner_id": group.owner_id,
            "schema": OWNER_STATE_BODY_SCHEMA,
            "state": state,
        })
    return bodies


def owner_state_body_mutation_root(
    group: OwnerStateGroup,
    encoded_body: bytes,
) -> str:
    """Return the owner's explicit state root, or its immutable genesis root."""
    if not isinstance(group, OwnerStateGroup):
        raise TypeError("owner state group must be typed")
    if not isinstance(encoded_body, bytes):
        raise TypeError("owner state body must be bytes")
    try:
        body = json.loads(encoded_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OwnerScopedPersistenceError(
            "owner state body is unreadable"
        ) from error
    if (
        not isinstance(body, dict)
        or set(body) != {"owner_id", "schema", "state"}
        or body.get("schema") != OWNER_STATE_BODY_SCHEMA
        or body.get("owner_id") != group.owner_id
        or _canonical(body) != encoded_body
    ):
        raise OwnerScopedPersistenceError(
            "owner state body contract changed"
        )
    state = body.get("state")
    if (
        not isinstance(state, dict)
        or set(state) != set(group.state_keys)
    ):
        raise OwnerScopedPersistenceError(
            "owner state body key set changed"
        )
    primary = state[group.state_keys[0]]
    if primary is None:
        if any(
            value is not None
            and value not in ({}, [], ())
            for value in tuple(state.values())[1:]
        ):
            # A companion observation cannot mutate without its owner state.
            # The sole exception is the explicit fresh-cycle status.
            if not (
                group.owner_id == "learned_substrate_vocal_cycle"
                and state.get("latest_thing_vocal_learning") == {
                    "reason": "no_lived_vocal_occurrence",
                    "schema": "guala.thing_vocal_learning.status.v1",
                    "state": "unobserved",
                }
            ):
                raise OwnerScopedPersistenceError(
                    "owner companion state exists without its owner"
                )
        return hashlib.sha256(
            b"guala-owner-state-genesis-v1\0"
            + group.owner_id.encode("utf-8")
            + encoded_body
        ).hexdigest()
    if not isinstance(primary, dict):
        raise OwnerScopedPersistenceError(
            "owner primary state is not an object"
        )
    mutation_root = primary.get(group.mutation_root_field)
    if (
        not isinstance(mutation_root, str)
        or len(mutation_root) != 64
        or any(
            character not in "0123456789abcdef"
            for character in mutation_root
        )
    ):
        raise OwnerScopedPersistenceError(
            f"{group.owner_id} has no exact mutation root"
        )
    return mutation_root


def frozen_path_owner_mutation_root(
    relative_path: str,
    encoded_body: bytes,
) -> str:
    """Verify one engine-issued learned-owner freeze lineage."""
    ownership = ownership_for_path(relative_path)
    if (
        ownership.requires_split
        or len(ownership.owner_ids) != 1
        or not ownership.stable_body_required
    ):
        raise OwnerScopedPersistenceError(
            f"{relative_path!r} has no learned-owner freeze lineage"
        )
    if not isinstance(encoded_body, bytes) or not encoded_body:
        raise OwnerScopedPersistenceError(
            "learned-owner frozen body is invalid"
        )
    try:
        envelope = json.loads(encoded_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OwnerScopedPersistenceError(
            "learned-owner frozen body is not JSON"
        ) from error
    contract = _FROZEN_PATH_CONTRACTS.get(relative_path)
    if contract is not None:
        if (
            not isinstance(envelope, dict)
            or set(envelope) != contract.top_level_fields
            or json.dumps(
                envelope,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8") != encoded_body
        ):
            raise OwnerScopedPersistenceError(
                "learned-owner frozen body contract changed"
            )

        def contract_value(path: tuple[str, ...]):
            current = envelope
            for field in path:
                if not isinstance(current, dict) or field not in current:
                    raise OwnerScopedPersistenceError(
                        "learned-owner frozen body contract changed"
                    )
                current = current[field]
            return current

        if contract_value(contract.schema_path) != contract.schema:
            raise OwnerScopedPersistenceError(
                "learned-owner frozen body schema changed"
            )
        mutation_root = contract_value(contract.mutation_root_path)
        if (
            not isinstance(mutation_root, str)
            or len(mutation_root) != 64
            or any(
                character not in "0123456789abcdef"
                for character in mutation_root
            )
        ):
            raise OwnerScopedPersistenceError(
                "learned-owner mutation root changed"
            )
        if contract.receipt_path is not None:
            supplied_receipt = contract_value(contract.receipt_path)
            expected_receipt = hashlib.sha256(json.dumps(
                {
                    "authority_hmac_sha256": mutation_root,
                    "payload": envelope["payload"],
                },
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")).hexdigest()
            if supplied_receipt != expected_receipt:
                raise OwnerScopedPersistenceError(
                    "learned-owner authority receipt changed"
                )
        return mutation_root
    if not isinstance(envelope, dict) or not isinstance(
        envelope.get("data"),
        dict,
    ):
        raise OwnerScopedPersistenceError(
            "learned-owner frozen body has no engine payload"
    )
    payload = dict(envelope["data"])
    receipt = payload.pop("owner_freeze_receipt", None)
    if not isinstance(receipt, dict) or set(receipt) != {
        "mutation_root_sha256",
        "owner_id",
        "schema",
        "semantic_body_sha256",
    }:
        raise OwnerScopedPersistenceError(
            "learned-owner freeze receipt is absent"
        )
    if (
        receipt.get("schema") != "guala.owner_freeze_receipt.v1"
        or receipt.get("owner_id") != ownership.owner_ids[0]
    ):
        raise OwnerScopedPersistenceError(
            "learned-owner freeze receipt changed"
        )
    semantic = hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    if receipt.get("semantic_body_sha256") != semantic:
        raise OwnerScopedPersistenceError(
            "learned-owner freeze body changed"
        )
    mutation_root = receipt.get("mutation_root_sha256")
    if (
        not isinstance(mutation_root, str)
        or len(mutation_root) != 64
        or any(
            character not in "0123456789abcdef"
            for character in mutation_root
        )
    ):
        raise OwnerScopedPersistenceError(
            "learned-owner mutation root changed"
        )
    return mutation_root


def frozen_binary_owner_mutation_root(
    relative_path: str,
    *,
    binding_body: bytes,
    artifact_sha256: str,
    artifact_bytes: int,
) -> str:
    """Verify one streamed structural-graph body through its owner receipt."""
    ownership = ownership_for_path(relative_path)
    if (
        ownership.requires_split
        or len(ownership.owner_ids) != 1
        or not ownership.stable_body_required
        or not relative_path.endswith(".sgr")
    ):
        raise OwnerScopedPersistenceError(
            f"{relative_path!r} has no binary-owner freeze lineage"
        )
    if (
        not isinstance(artifact_sha256, str)
        or len(artifact_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in artifact_sha256
        )
        or isinstance(artifact_bytes, bool)
        or not isinstance(artifact_bytes, int)
        or artifact_bytes < 0
    ):
        raise OwnerScopedPersistenceError(
            "binary-owner artifact measurement is invalid"
        )
    if not isinstance(binding_body, bytes) or not binding_body:
        raise OwnerScopedPersistenceError(
            "binary-owner binding body is invalid"
        )
    try:
        envelope = json.loads(binding_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OwnerScopedPersistenceError(
            "binary-owner binding body is not JSON"
        ) from error
    if not isinstance(envelope, dict) or not isinstance(
        envelope.get("data"),
        dict,
    ):
        raise OwnerScopedPersistenceError(
            "binary-owner binding has no engine payload"
    )
    payload = dict(envelope["data"])
    receipt = payload.pop("owner_freeze_receipt", None)
    saved_at_tick = payload.pop("saved_at_tick", None)
    if not isinstance(receipt, dict) or set(receipt) != {
        "mutation_root_sha256",
        "owner_id",
        "schema",
        "semantic_body_sha256",
    }:
        raise OwnerScopedPersistenceError(
            "binary-owner freeze receipt is absent"
        )
    owner_id = ownership.owner_ids[0]
    if (
        receipt.get("schema") != "guala.owner_freeze_receipt.v1"
        or receipt.get("owner_id") != owner_id
    ):
        raise OwnerScopedPersistenceError(
            "binary-owner freeze receipt changed"
        )
    if (
        payload.get("binding_contract") != "guala_binary_binding_v1"
        or payload.get("artifact") != relative_path.rsplit("/", 1)[-1]
        or payload.get("sha256") != artifact_sha256
        or payload.get("bytes") != artifact_bytes
        or isinstance(saved_at_tick, bool)
        or not isinstance(saved_at_tick, int)
        or saved_at_tick < 0
    ):
        raise OwnerScopedPersistenceError(
            "binary-owner binding differs from its artifact"
        )
    semantic = hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    if receipt.get("semantic_body_sha256") != semantic:
        raise OwnerScopedPersistenceError(
            "binary-owner freeze body changed"
        )
    mutation_root = receipt.get("mutation_root_sha256")
    if (
        not isinstance(mutation_root, str)
        or len(mutation_root) != 64
        or any(
            character not in "0123456789abcdef"
            for character in mutation_root
        )
    ):
        raise OwnerScopedPersistenceError(
            "binary-owner mutation root changed"
        )
    return mutation_root


def decode_owner_state_bodies(
    encoded_by_path: Mapping[str, bytes],
) -> dict[str, object]:
    """Merge an exact complete set of stable bodies for existing restorers."""
    expected = {
        group.relative_path for group in OWNER_STATE_GROUPS
    }
    supplied = set(encoded_by_path)
    optional_genesis_paths = {
        LEGACY_MISSING_CAUSAL_THING_ACTION_INTENT_PATH,
        LEGACY_MISSING_CAUSAL_THING_LIVED_CONTEXT_PATH,
        LEGACY_MISSING_CAUSAL_THING_SENSORY_EXPANSION_PATH,
        LEGACY_MISSING_PENDING_ARTICULATORY_ATTEMPT_PATH,
        LEGACY_MISSING_CUSTODY_NATIVE_TUTORING_PATH,
        LEGACY_MISSING_EMBODIMENT_CAUSAL_SEQUENCE_PATH,
        LEGACY_MISSING_CUSTODY_TUTORING_ACTION_LATCH_PATH,
        LEGACY_MISSING_WHOLE_ORGANISM_RECOVERY_PATH,
        LEGACY_MISSING_WHOLE_ORGANISM_STRUCTURAL_PATH,
        LEGACY_MISSING_CAUSAL_MOSAIC_TAPESTRY_PATH,
        LEGACY_MISSING_AUTONOMOUS_EXPERIENCE_DRIVER_PATH,
        LEGACY_MISSING_WHOLE_ORGANISM_INTERNAL_REENTRY_PATH,
        LEGACY_MISSING_NATIVE_MATERIALIZED_FABRIC_PATH,
    }
    if (
        supplied - expected
        or not supplied.issuperset(expected - optional_genesis_paths)
    ):
        raise OwnerScopedPersistenceError(
            "owner state body file set changed"
        )
    merged = {}
    for group in OWNER_STATE_GROUPS:
        if group.relative_path not in encoded_by_path:
            if group.relative_path not in optional_genesis_paths:
                raise OwnerScopedPersistenceError(
                    "owner state body file set changed"
                )
            if (
                group.relative_path
                == LEGACY_MISSING_CAUSAL_THING_ACTION_INTENT_PATH
            ):
                merged["causal_thing_action_intents"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_CAUSAL_THING_SENSORY_EXPANSION_PATH
            ):
                merged["causal_thing_sensory_expansion"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_CAUSAL_THING_LIVED_CONTEXT_PATH
            ):
                merged["causal_thing_lived_context"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_PENDING_ARTICULATORY_ATTEMPT_PATH
            ):
                merged["pending_articulatory_causal_attempt"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_CUSTODY_NATIVE_TUTORING_PATH
            ):
                merged["custody_native_tutoring_curriculum"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_EMBODIMENT_CAUSAL_SEQUENCE_PATH
            ):
                merged["embodiment_outcome_causal_sequence"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_CUSTODY_TUTORING_ACTION_LATCH_PATH
            ):
                merged["custody_native_tutoring_action_selector"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_WHOLE_ORGANISM_RECOVERY_PATH
            ):
                merged["whole_organism_recovery"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_WHOLE_ORGANISM_STRUCTURAL_PATH
            ):
                merged["whole_organism_structural_perturbation"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_AUTONOMOUS_EXPERIENCE_DRIVER_PATH
            ):
                merged["autonomous_experience_driver"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_WHOLE_ORGANISM_INTERNAL_REENTRY_PATH
            ):
                merged["whole_organism_internal_reentry"] = None
            elif (
                group.relative_path
                == LEGACY_MISSING_NATIVE_MATERIALIZED_FABRIC_PATH
            ):
                merged["native_materialized_fabric"] = None
            else:
                merged["causal_mosaic_tapestry"] = None
            continue
        encoded = encoded_by_path[group.relative_path]
        owner_state_body_mutation_root(group, encoded)
        body = json.loads(encoded)
        for key, value in body["state"].items():
            if key in merged:
                raise OwnerScopedPersistenceError(
                    "owner state key has overlapping owners"
                )
            merged[key] = value
    if set(merged) != ACTIVE_OWNER_STATE_KEYS:
        raise OwnerScopedPersistenceError(
            "owner state key census changed"
        )
    return merged


def issue_owner_state_snapshot_receipt(
    *,
    identity: str,
    relative_path: str,
    body_sha256: str,
    body_bytes: int,
    mutation_root_sha256: str,
    frozen_tick: int,
    authority_key: bytes,
) -> OwnerStateSnapshotReceipt:
    ownership = ownership_for_path(relative_path)
    if (
        ownership.requires_split
        or len(ownership.owner_ids) != 1
        or not ownership.stable_body_required
    ):
        raise OwnerScopedPersistenceError(
            f"{relative_path!r} cannot issue one owner snapshot receipt"
        )
    unsigned = {
        "body_bytes": body_bytes,
        "body_sha256": body_sha256,
        "frozen_tick": frozen_tick,
        "identity": identity,
        "mutation_root_sha256": mutation_root_sha256,
        "owner_id": ownership.owner_ids[0],
        "relative_path": relative_path,
        "role": ownership.role,
        "schema": OWNER_STATE_SNAPSHOT_RECEIPT_SCHEMA,
    }
    if (
        not isinstance(identity, str)
        or not identity
        or isinstance(body_bytes, bool)
        or not isinstance(body_bytes, int)
        or body_bytes < 0
        or isinstance(frozen_tick, bool)
        or not isinstance(frozen_tick, int)
        or frozen_tick < 0
    ):
        raise OwnerScopedPersistenceError(
            "owner snapshot identity, size, or tick is invalid"
        )
    for field in ("body_sha256", "mutation_root_sha256"):
        digest = unsigned[field]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in digest
            )
        ):
            raise OwnerScopedPersistenceError(
                f"owner snapshot {field} is invalid"
            )
    if (
        not isinstance(authority_key, bytes)
        or len(authority_key) < 32
    ):
        raise OwnerScopedPersistenceError(
            "owner snapshot authority key is invalid"
        )
    signature = hmac.new(
        authority_key,
        _OWNER_RECEIPT_DOMAIN + _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    return OwnerStateSnapshotReceipt(
        **{
            key: value
            for key, value in unsigned.items()
            if key != "schema"
        },
        authority_hmac_sha256=signature,
    )


def verify_owner_state_snapshot_receipt(
    receipt: OwnerStateSnapshotReceipt | Mapping[str, object],
    authority_key: bytes,
) -> OwnerStateSnapshotReceipt:
    if isinstance(receipt, OwnerStateSnapshotReceipt):
        supplied = receipt.record()
    elif isinstance(receipt, Mapping):
        supplied = dict(receipt)
    else:
        raise TypeError(
            "owner state snapshot receipt must be typed or a mapping"
        )
    fields = {
        "authority_hmac_sha256",
        "body_bytes",
        "body_sha256",
        "frozen_tick",
        "identity",
        "mutation_root_sha256",
        "owner_id",
        "relative_path",
        "role",
        "schema",
    }
    if set(supplied) != fields:
        raise OwnerScopedPersistenceError(
            "owner state snapshot receipt field set changed"
        )
    signature = supplied.pop("authority_hmac_sha256")
    if (
        not isinstance(signature, str)
        or len(signature) != 64
        or not isinstance(authority_key, bytes)
        or len(authority_key) < 32
    ):
        raise OwnerScopedPersistenceError(
            "owner state snapshot authentication is invalid"
        )
    ownership = ownership_for_path(supplied["relative_path"])
    if (
        supplied.get("schema")
        != OWNER_STATE_SNAPSHOT_RECEIPT_SCHEMA
        or ownership.requires_split
        or not ownership.stable_body_required
        or ownership.owner_ids != (supplied.get("owner_id"),)
        or ownership.role != supplied.get("role")
    ):
        raise OwnerScopedPersistenceError(
            "owner state snapshot differs from the path registry"
        )
    expected = hmac.new(
        authority_key,
        _OWNER_RECEIPT_DOMAIN + _canonical(supplied),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise OwnerScopedPersistenceError(
            "owner state snapshot authentication failed"
        )
    reconstructed = issue_owner_state_snapshot_receipt(
        identity=supplied["identity"],
        relative_path=supplied["relative_path"],
        body_sha256=supplied["body_sha256"],
        body_bytes=supplied["body_bytes"],
        mutation_root_sha256=supplied["mutation_root_sha256"],
        frozen_tick=supplied["frozen_tick"],
        authority_key=authority_key,
    )
    if reconstructed.authority_hmac_sha256 != signature:
        raise OwnerScopedPersistenceError(
            "owner state snapshot canonical reconstruction changed"
        )
    return reconstructed


__all__ = [
    "OWNER_STATE_SNAPSHOT_RECEIPT_SCHEMA",
    "OWNER_STATE_BODY_SCHEMA",
    "OWNER_STATE_GROUPS",
    "LEGACY_MISSING_AUTONOMOUS_EXPERIENCE_DRIVER_PATH",
    "LEGACY_MISSING_CAUSAL_THING_LIVED_CONTEXT_PATH",
    "LEGACY_MISSING_CUSTODY_NATIVE_TUTORING_PATH",
    "LEGACY_MISSING_EMBODIED_READING_LESSON_CONTROLLER_PATH",
    "LEGACY_MISSING_PENDING_ARTICULATORY_ATTEMPT_PATH",
    "LEGACY_MISSING_NATIVE_MATERIALIZED_FABRIC_PATH",
    "LEGACY_MISSING_WHOLE_ORGANISM_INTERNAL_REENTRY_PATH",
    "ACTIVE_OWNER_STATE_KEYS",
    "OwnerScopedPersistenceError",
    "OwnerStateSnapshotReceipt",
    "PATH_OWNERSHIP_REGISTRY",
    "PathOwnership",
    "ROLE_CONFIG",
    "ROLE_DYNAMIC",
    "ROLE_IDENTITY",
    "ROLE_LEARNED",
    "ROLE_MIGRATION",
    "ROLE_RECEIPT",
    "ROLE_RETIRED",
    "TEACHING_MONOLITH_OWNERS",
    "census_generation_path_ownership",
    "issue_owner_state_snapshot_receipt",
    "decode_owner_state_bodies",
    "frozen_path_owner_mutation_root",
    "frozen_binary_owner_mutation_root",
    "owner_state_bodies",
    "owner_state_body_mutation_root",
    "ownership_for_path",
    "verify_owner_state_snapshot_receipt",
]
