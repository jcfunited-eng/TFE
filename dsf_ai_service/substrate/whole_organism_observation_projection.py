"""Truthful read-only projection of whole-organism wiring and activity.

The mounted mechanism manifest, current durable owner state, and latest
settlement activity are different physical facts.  This module preserves
that distinction.  It never treats owner presence, retained perturbation,
wall-clock polling, or a missing contribution receipt as new activity.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping


PROJECTION_SCHEMA = "guala.whole_organism.permanent_wiring.observation.v2"
MANIFEST_SCHEMA = "guala.whole_organism.manifest_state.v1"
LATEST_ACTIVITY_SCHEMA = "guala.whole_organism.latest_episode_activity.v1"
CURRENT_OWNER_SCHEMA = "guala.whole_organism.current_owner_state.v1"

_CATEGORY = {
    "receptor:sight": "neuronal_sensory_anatomy",
    "receptor:sound": "neuronal_sensory_anatomy",
    "receptor:touch": "neuronal_sensory_anatomy",
    "receptor:smell": "neuronal_sensory_anatomy",
    "receptor:taste": "neuronal_sensory_anatomy",
    "receptor:body": "neuronal_sensory_anatomy",
    "growth:neuron-population": "growth_count_curriculum_observation",
    "state:internal-physical-chemical": (
        "organism_wide_state_flow_governance"
    ),
    "state:neurochemical-flow": "organism_wide_state_flow_governance",
    "state:needs": "organism_wide_state_flow_governance",
    "state:recognition-attention": "organism_wide_state_flow_governance",
    "state:recovery": "organism_wide_state_flow_governance",
    "state:deliberation": "organism_wide_state_flow_governance",
    "settlement:l6": "organism_wide_state_flow_governance",
    "state:embodiment": "embodiment_action_world",
    "state:place-world-continuity": "embodiment_action_world",
    "state:other-perspective-model": "embodiment_action_world",
    "action:embodied": "embodiment_action_world",
    "state:sensed-consequence": "embodiment_action_world",
    "growth:mosaic": "growth_count_curriculum_observation",
    "growth:mosaic-relations": "growth_count_curriculum_observation",
    "growth:tapestry": "growth_count_curriculum_observation",
    "growth:tapestry-relations": "growth_count_curriculum_observation",
    "growth:play": "growth_count_curriculum_observation",
    "growth:dream-internally-simulated": (
        "growth_count_curriculum_observation"
    ),
    "growth:wake-test": "growth_count_curriculum_observation",
    "growth:weave": "growth_count_curriculum_observation",
    "growth:embodied-glyph-curriculum": (
        "growth_count_curriculum_observation"
    ),
}

_RECEPTOR_IDS = frozenset({
    "receptor:sight",
    "receptor:sound",
    "receptor:touch",
    "receptor:smell",
    "receptor:taste",
    "receptor:body",
})

_SHARED_PROVIDER_KEY = {
    "state:place-world-continuity": "state:embodiment",
    "growth:tapestry-relations": "growth:tapestry",
    "growth:wake-test": "growth:dream-internally-simulated",
    "growth:weave": "growth:dream-internally-simulated",
}

def _semantic_state_sha256(value: Mapping[str, object]) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record_count(
    semantic_state: Mapping[str, object],
    field: str,
) -> int:
    value = semantic_state.get(field)
    if not isinstance(value, (list, tuple)):
        raise RuntimeError(
            f"{field} is not an exact record sequence in durable observation"
        )
    return len(value)


def _bounded_durable_semantic_projection(
    mechanism_id: str,
    semantic_state: Mapping[str, object],
) -> Mapping[str, object]:
    """Project bulky owner state without copying its durable body into Loom.

    This is an observation transport boundary only.  The authenticated cold
    state, exact provider receipt, and complete semantic state remain mounted
    upstream and retain all causal authority.  No value in this projection is
    admitted back into cognition or persistence.
    """

    if mechanism_id in {
        "state:embodiment",
        "state:place-world-continuity",
    }:
        return {
            "authority_receipt_sha256": semantic_state.get(
                "authority_receipt_sha256"
            ),
            "body_count": _record_count(semantic_state, "bodies"),
            "decision_authority": False,
            "full_state_preserved_upstream": True,
            "object_count": _record_count(semantic_state, "objects"),
            "portal_count": _record_count(semantic_state, "portals"),
            "projection": "bounded_counts_and_receipts",
            "projection_loss": (
                "body, object, optical-surface, room-bound, portal, and "
                "region records are omitted from this repeated wiring view; "
                "the complete world remains in the authoritative embodiment "
                "owner and the top-level embodiment observation"
            ),
            "region_count": _record_count(semantic_state, "regions"),
            "revision": semantic_state.get("revision"),
            "room_id": semantic_state.get("room_id"),
            "schema": "guala.whole_organism.bounded_world_state_view.v1",
            "self_body_id": semantic_state.get("self_body_id"),
            "source_schema": semantic_state.get("schema"),
            "source_state_sha256": _semantic_state_sha256(semantic_state),
            "state_sha256": semantic_state.get("state_sha256"),
        }
    if mechanism_id == "state:recovery":
        roots = semantic_state.get("full_field_root_receipt_sha256s")
        coordinates = semantic_state.get("l1_n_gate_coordinates")
        if not isinstance(roots, (list, tuple)):
            raise RuntimeError(
                "recovery full-field roots are not an exact sequence"
            )
        if not isinstance(coordinates, (list, tuple)):
            raise RuntimeError(
                "recovery L1 gate coordinates are not an exact sequence"
            )
        physical_body_state = semantic_state.get("physical_body_state")
        physical_body_state_sha256 = hashlib.sha256(json.dumps(
            physical_body_state,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()
        return {
            "authority_receipt_sha256": semantic_state.get(
                "authority_receipt_sha256"
            ),
            "decision_authority": False,
            "full_field_preserved_upstream": True,
            "full_field_root_receipt_count": len(roots),
            "l1_n_gate_coordinate_count": len(coordinates),
            "moment_state": semantic_state.get("moment_state"),
            "physical_body_state_sha256": physical_body_state_sha256,
            "prior_state_receipt_sha256": semantic_state.get(
                "prior_state_receipt_sha256"
            ),
            "profile_receipt_sha256": semantic_state.get(
                "profile_receipt_sha256"
            ),
            "projection": "bounded_counts_and_receipts",
            "projection_loss": (
                "explicit DSF root receipt bodies, L1 gate coordinate bodies, "
                "and the physical body-state record are omitted from this "
                "read-only wiring view; their counts and exact content hashes "
                "are exposed while the complete recovery state remains mounted"
            ),
            "recovery_count": semantic_state.get("recovery_count"),
            "schema": "guala.whole_organism.bounded_recovery_state_view.v1",
            "sequence": semantic_state.get("sequence"),
            "settlement_authority_receipt_sha256": semantic_state.get(
                "settlement_authority_receipt_sha256"
            ),
            "source_schema": semantic_state.get("schema"),
            "source_state_sha256": _semantic_state_sha256(semantic_state),
            "source_time_end": semantic_state.get("source_time_end"),
            "source_time_start": semantic_state.get("source_time_start"),
        }
    return semantic_state


def _realization(mechanism_id: str) -> str:
    if mechanism_id in _RECEPTOR_IDS:
        return "receptor_family_neuron_population"
    if mechanism_id == "growth:neuron-population":
        return "neuron_population_observation"
    if mechanism_id == "settlement:l6":
        return "settlement_scoped"
    return "software_owner"


def _explicit_evidence(
    semantic_state: Mapping[str, object],
) -> dict[str, object]:
    receipts = {
        key: value
        for key, value in semantic_state.items()
        if (
            key == "authority_receipt_sha256"
            or key.endswith("_authority_receipt_sha256")
        )
        and isinstance(value, str)
    }
    sequences = {
        key: value
        for key, value in semantic_state.items()
        if (
            key == "sequence"
            or key.endswith("_sequence")
            or key.endswith("_cursor")
        )
        and isinstance(value, int)
        and not isinstance(value, bool)
    }
    evidence: dict[str, object] = {}
    if receipts:
        evidence["authority_receipts"] = receipts
    if sequences:
        evidence["sequences"] = sequences
    return evidence


def _neuron_context(runtime) -> dict[str, object] | None:
    owner = runtime._whole_organism_neuron_population_owner
    if owner is None:
        return None
    cold_state = owner.snapshot_encoded()
    return {
        "cold_state_sha256": hashlib.sha256(cold_state).hexdigest(),
        "neurons": owner.neurons,
        "status": owner.status(),
    }


def _receptor_owner_state(
    mechanism_id: str,
    neuron_context: Mapping[str, object] | None,
) -> dict[str, object]:
    if neuron_context is None:
        return {
            "availability": "unavailable",
            "category": _CATEGORY[mechanism_id],
            "mechanism_id": mechanism_id,
            "realization": "receptor_family_neuron_population",
            "reason": "neuron_population_owner_not_mounted",
        }
    sense = mechanism_id.split(":", 1)[1]
    neurons = sum(
        neuron.sense == sense
        for neuron in neuron_context["neurons"]
    )
    perturbed = sum(
        neuron.sense == sense
        and neuron.current_state == "perturbed"
        for neuron in neuron_context["neurons"]
    )
    return {
        "availability": "available",
        "category": _CATEGORY[mechanism_id],
        "evidence": {
            "cold_state_sha256": neuron_context["cold_state_sha256"],
            "evidence_kind": "authenticated_cold_owner_state",
        },
        "mechanism_id": mechanism_id,
        "provider_id": "whole_organism_neuron_population",
        "realization": "receptor_family_neuron_population",
        "state_projection": {
            "neurons": neurons,
            "perturbed_neurons": perturbed,
            "quiescent_neurons": neurons - perturbed,
            "state": "perturbed" if perturbed else "quiescent",
        },
    }


def _neuron_population_owner_state(
    mechanism_id: str,
    neuron_context: Mapping[str, object] | None,
) -> dict[str, object]:
    if neuron_context is None:
        return {
            "availability": "unavailable",
            "category": _CATEGORY[mechanism_id],
            "mechanism_id": mechanism_id,
            "realization": "neuron_population_observation",
            "reason": "neuron_population_owner_not_mounted",
        }
    cold_state_sha256 = neuron_context["cold_state_sha256"]
    semantic_state = neuron_context["status"]
    return {
        "availability": "available",
        "category": _CATEGORY[mechanism_id],
        "evidence": {
            "cold_state_sha256": cold_state_sha256,
            "evidence_kind": "current_provider_state",
            "provider_state_receipt_sha256": cold_state_sha256,
            **_explicit_evidence(semantic_state),
        },
        "mechanism_id": mechanism_id,
        "provider_id": "whole_organism_neuron_population",
        "realization": "neuron_population_observation",
        "state_projection": semantic_state,
    }


def _durable_owner_state(
    runtime,
    mechanism_id: str,
    provider_cache: dict[str, tuple[Mapping[str, object], str]],
) -> dict[str, object]:
    cache_key = _SHARED_PROVIDER_KEY.get(mechanism_id, mechanism_id)
    if cache_key not in provider_cache:
        provider_cache[cache_key] = (
            runtime._whole_organism_available_state(mechanism_id, None)
        )
    custodied, provider_receipt = provider_cache[cache_key]
    semantic_state = custodied["semantic_state"]
    state_projection = _bounded_durable_semantic_projection(
        mechanism_id,
        semantic_state,
    )
    evidence = {
        "cold_state_sha256": custodied["cold_state_sha256"],
        "evidence_kind": "current_provider_state",
        "provider_state_receipt_sha256": provider_receipt,
        **_explicit_evidence(semantic_state),
    }
    return {
        "availability": "available",
        "category": _CATEGORY[mechanism_id],
        "evidence": evidence,
        "mechanism_id": mechanism_id,
        "provider_id": custodied["provider_id"],
        "realization": _realization(mechanism_id),
        "state_projection": state_projection,
    }


def _current_owner_states(runtime, mechanisms) -> dict[str, object]:
    result = {}
    provider_cache = {}
    neuron_context = _neuron_context(runtime)
    for spec in mechanisms:
        mechanism_id = spec.mechanism_id
        if spec.availability.value != "available":
            result[mechanism_id] = {
                "availability": "unavailable",
                "category": _CATEGORY[mechanism_id],
                "mechanism_id": mechanism_id,
                "realization": _realization(mechanism_id),
                "reason": spec.unavailable_reason,
            }
        elif mechanism_id in _RECEPTOR_IDS:
            result[mechanism_id] = _receptor_owner_state(
                mechanism_id,
                neuron_context,
            )
        elif mechanism_id == "growth:neuron-population":
            result[mechanism_id] = _neuron_population_owner_state(
                mechanism_id,
                neuron_context,
            )
        elif mechanism_id == "settlement:l6":
            result[mechanism_id] = {
                "availability": "not_observable_without_settlement",
                "category": _CATEGORY[mechanism_id],
                "mechanism_id": mechanism_id,
                "realization": "settlement_scoped",
                "reason": "no_current_owner_state_exists_outside_settlement",
            }
        else:
            result[mechanism_id] = _durable_owner_state(
                runtime,
                mechanism_id,
                provider_cache,
            )
    return result


def _latest_episode_activity(
    latest: Mapping[str, object],
    mechanism_ids: frozenset[str],
) -> dict[str, object]:
    raw_states = latest.get("contribution_states")
    if not isinstance(raw_states, Mapping):
        return {
            "activity_counts": {
                "perturbed": None,
                "quiescent": None,
                "unavailable": None,
            },
            "contribution_states": None,
            "reason": "no_post_start_episode_contribution_receipt",
            "schema": LATEST_ACTIVITY_SCHEMA,
            "status": "not_observed_since_process_start",
        }
    contribution_states = dict(raw_states)
    if (
        set(contribution_states) != mechanism_ids
        or any(
            value not in {"perturbed", "quiescent", "unavailable"}
            for value in contribution_states.values()
        )
    ):
        raise RuntimeError(
            "latest whole-organism contribution evidence changed"
        )
    return {
        "activity_counts": {
            "perturbed": sum(
                value == "perturbed"
                for value in contribution_states.values()
            ),
            "quiescent": sum(
                value == "quiescent"
                for value in contribution_states.values()
            ),
            "unavailable": sum(
                value == "unavailable"
                for value in contribution_states.values()
            ),
        },
        "contribution_states": contribution_states,
        "episode_receipt_sha256": latest.get(
            "episode_receipt_sha256"
        ),
        "manifest_receipt_sha256": latest.get(
            "manifest_receipt_sha256"
        ),
        "resolution_state": latest.get("state"),
        "schema": LATEST_ACTIVITY_SCHEMA,
        "settlement_receipt_sha256": latest.get(
            "settlement_receipt_sha256"
        ),
        "status": "observed",
    }


def project_whole_organism_permanent_wiring(
    runtime,
    whole,
    latest: Mapping[str, object],
) -> dict[str, object]:
    """Return mounted anatomy, current state, and episode activity separately."""

    mechanisms = whole.manifest.mechanisms
    mechanism_ids = {value.mechanism_id for value in mechanisms}
    if mechanism_ids != set(_CATEGORY):
        missing = sorted(mechanism_ids - set(_CATEGORY))
        stale = sorted(set(_CATEGORY) - mechanism_ids)
        raise RuntimeError(
            "whole-organism observation classification changed: "
            f"missing={missing!r}, stale={stale!r}"
        )
    activity = _latest_episode_activity(
        latest,
        frozenset(mechanism_ids),
    )
    states = activity["contribution_states"]
    counts = activity["activity_counts"]
    category_counts = Counter(_CATEGORY.values())
    current_states = _current_owner_states(runtime, mechanisms)
    manifest_state = {
        "available_mechanisms": sum(
            value.availability.value == "available"
            for value in mechanisms
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "manifest_receipt_sha256": (
            whole.manifest.authority_receipt_sha256
        ),
        "mechanisms": [
            {
                "availability": value.availability.value,
                "category": _CATEGORY[value.mechanism_id],
                "kind": value.kind.value,
                "mechanism_id": value.mechanism_id,
                "realization": _realization(value.mechanism_id),
            }
            for value in mechanisms
        ],
        "mechanism_count": len(mechanisms),
        "schema": MANIFEST_SCHEMA,
        "status": "mounted",
        "unavailable_mechanisms": sum(
            value.availability.value == "unavailable"
            for value in mechanisms
        ),
    }
    if states is not None:
        truthful_latest = dict(latest)
    elif latest.get("schema") == (
        "guala.live.whole_organism.mount_status.v1"
    ):
        truthful_latest = {
            "reason": activity["reason"],
            "schema": LATEST_ACTIVITY_SCHEMA,
            "state": activity["status"],
        }
    else:
        truthful_latest = {
            **dict(latest),
            "episode_activity_status": activity["status"],
        }
    return {
        "available_mechanisms": (
            manifest_state["available_mechanisms"]
        ),
        "current_owner_state": {
            "mechanisms": current_states,
            "schema": CURRENT_OWNER_SCHEMA,
            "status": "observed",
        },
        "latest_contribution_states": states,
        "latest_episode_activity": activity,
        "latest_resolution": truthful_latest,
        "manifest_receipt_sha256": (
            manifest_state["manifest_receipt_sha256"]
        ),
        "manifest_state": manifest_state,
        "mechanisms": manifest_state["mechanism_count"],
        "perturbed_latest": counts["perturbed"],
        "projection_contract": {
            "activity_basis": "settlement_contribution_receipts_only",
            "current_state_is_activity": False,
            "current_state_projection": (
                "bounded per-mechanism status with exact provider receipts"
            ),
            "current_state_projection_loss": (
                "bulky world and recovery record bodies are omitted only from "
                "the repeated read-only wiring view; authoritative owner state "
                "and full DSF evaluation remain complete upstream"
            ),
            "decision_authority": False,
            "missing_activity_is_zero": False,
            "schema": PROJECTION_SCHEMA,
        },
        "quiescent_latest": counts["quiescent"],
        "schema": PROJECTION_SCHEMA,
        "status": "mounted",
        "unavailable_latest": counts["unavailable"],
        "unavailable_mechanisms": (
            manifest_state["unavailable_mechanisms"]
        ),
    }


def compatible_mechanism_counts(
    wiring: Mapping[str, object],
) -> dict[str, object]:
    """Retain the old summary without turning absent evidence into zero."""

    manifest = wiring["manifest_state"]
    activity = wiring["latest_episode_activity"]
    counts = activity["activity_counts"]
    return {
        "activity_status": activity["status"],
        "available": manifest["available_mechanisms"],
        "mechanisms": manifest["mechanism_count"],
        "perturbed": counts["perturbed"],
        "quiescent": counts["quiescent"],
        "schema": "guala.whole_organism.mechanism_counts_states.v2",
        "unavailable": counts["unavailable"],
    }
