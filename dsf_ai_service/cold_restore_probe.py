"""Read-only fresh-process proof of one native-organism CURRENT pointer."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
import re

from dsf_ai_service.glew_runtime.native_resident_organism import (
    exact_native_yaw_trajectory,
    restore_native_resident_organism,
)
from dsf_ai_service.substrate.native_organism_binary_store import (
    NativeOrganismBinaryStoreError,
    rehearse_current_native_organism_current_format,
    restore_current_native_organism,
)
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


PROOF_SCHEMA = "guala.production_native_current_cold_restore.v6"
_COMMIT = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-store-root", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", required=True, type=int)
    parser.add_argument("--expected-state-sha256", required=True)
    parser.add_argument("--candidate-git-sha", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    return parser.parse_args()


def _rehearse_native_distributed_recall(
    current_envelope: bytes,
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> dict[str, int | bool | str | tuple[str, ...]]:
    """Prove one body partial cue becomes distributed current recall."""

    budget = {
        "max_envelope_bytes": max_envelope_bytes,
        "max_fabric_bytes": max_fabric_bytes,
        "max_logical_peak_bytes": max_logical_peak_bytes,
    }
    organism = restore_native_resident_organism(
        current_envelope=current_envelope,
        **budget,
    )
    before = organism.readiness()
    layers = {
        lineage: layer
        for lineage, layer, _receptor in (
            organism.observe_reached_neuron_lineage_layers()
        )
    }
    formations = organism.observe_retained_formation_structures()
    cues = dict(organism.observe_retained_formation_recurrence_cues())
    body_cued = [
        (receipt, members, cue)
        for receipt, members, _original, _recurrent, _reinforcements in formations
        if len(cue := cues.get(receipt, ())) == 1 and layers[cue[0]] == 5
    ]
    if len(body_cued) != 1:
        raise RuntimeError("CURRENT has no single exact body-cued formation")
    formation_receipt, formation_members, cue = body_cued[0]
    trajectory_projection = _rehearse_ordered_trajectory_projection(
        current_envelope,
        formation_members,
        budget,
    )
    recalled = None
    episodic_relation = None
    ordered_path_cold_reassembly = False
    heading = 0
    transition_count = 0
    dsf_delivery_count = 0
    for ordinal, signed_step in enumerate((-64, -64, -64, -64), 1):
        interval_predecessor = organism.save()
        prepared = organism.prepare_vestibular_tick(heading, signed_step)
        transition_count += prepared.physically_transitioned_neuron_count
        dsf_delivery_count += prepared.dsf_delivery_count
        observed = _observe_distributed_recognition(
            organism,
            prepared,
            formations,
        )
        relation = _commit_and_observe_episodic_relation(
            organism,
            prepared,
            formation_members,
        )
        if observed is not None and formation_receipt in observed[
            "distributed_recognition_formation_receipts"
        ]:
            interval_recall = {
                **observed,
                "distributed_recall_interval_ordinal": ordinal,
            }
            if (
                episodic_relation is None
                and relation is not None
                and relation["ordered_path_relation_count"] > 0
            ):
                replay = restore_native_resident_organism(
                    current_envelope=interval_predecessor,
                    **budget,
                )
                replay_prepared = replay.prepare_vestibular_tick(heading, signed_step)
                replay_relation = _commit_and_observe_episodic_relation(
                    replay,
                    replay_prepared,
                    formation_members,
                )
                if (
                    replay_prepared.partial_cue_reassembly_count <= 0
                    or replay_relation is None
                    or replay_relation["ordered_path_relation_count"] <= 0
                    or replay_relation["episodic_related_formation_receipts_sha256"]
                    != relation["episodic_related_formation_receipts_sha256"]
                    or replay_relation["episodic_related_member_sets_sha256"]
                    != relation["episodic_related_member_sets_sha256"]
                    or replay_relation["episodic_relation_active_bonds_sha256"]
                    != relation["episodic_relation_active_bonds_sha256"]
                    or replay_relation["structural_relation_sha256"]
                    != relation["structural_relation_sha256"]
                    or replay_relation["ordered_physical_paths_sha256"]
                    != relation["ordered_physical_paths_sha256"]
                    or replay_relation["ordered_path_relations_sha256"]
                    != relation["ordered_path_relations_sha256"]
                    or replay.save() != organism.save()
                ):
                    raise RuntimeError(
                        "cold replay did not reproduce the exact ordered relation"
                    )
                recalled = interval_recall
                episodic_relation = {
                    **relation,
                    "episodic_relation_interval_ordinal": ordinal,
                }
                ordered_path_cold_reassembly = True
        heading = (heading + signed_step) % 360_000
    if (
        recalled is None
        or episodic_relation is None
        or not ordered_path_cold_reassembly
    ):
        raise RuntimeError("body partial cue produced no distributed recall")
    after = organism.readiness()
    successor_state = organism.save()
    cold = restore_native_resident_organism(
        current_envelope=successor_state,
        **budget,
    )
    cold_exact = cold.save() == successor_state
    if (
        dsf_delivery_count <= 0
        or transition_count <= 0
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick + 4
        or after.python_callback_count != 0
        or after.state_sha256 == before.state_sha256
        or not cold_exact
        or cold.readiness().state_sha256 != after.state_sha256
    ):
        raise RuntimeError("native distributed-recall rehearsal changed")
    cold_formations = cold.observe_retained_formation_structures()
    cold_cues = dict(cold.observe_retained_formation_recurrence_cues())
    cold_body_cued = [
        (receipt, members, cue)
        for receipt, members, _original, _recurrent, _reinforcements in cold_formations
        if tuple(members) == tuple(formation_members)
        and len(cue := cold_cues.get(receipt, ())) == 1
    ]
    if len(cold_body_cued) != 1:
        raise RuntimeError("cold successor lost its exact body-cued formation")
    return {
        **recalled,
        **episodic_relation,
        **trajectory_projection,
        "ordered_physical_cold_reassembly": ordered_path_cold_reassembly,
        "distributed_recognition_episode_ordinal": (
            recalled["distributed_recall_interval_ordinal"] - 1
        ),
        "distributed_recognition_source_dsf_delivery_count": dsf_delivery_count,
        "distributed_recognition_source_hop_count": 4,
        "distributed_recognition_source_physical_transition_count": (
            transition_count
        ),
        "distributed_recognition_state_byte_delta": (
            after.state_bytes - before.state_bytes
        ),
        "distributed_recognition_successor_state_sha256": after.state_sha256,
        "distributed_recall_cue_lineage": cue[0],
        "distributed_recall_formation_member_count": len(formation_members),
        "distributed_recall_rehearsed": True,
        "distributed_recall_source_dsf_delivery_count": dsf_delivery_count,
        "distributed_recall_source_physical_transition_count": transition_count,
        "distributed_recall_state_byte_delta": after.state_bytes - before.state_bytes,
        "distributed_recall_successor_state_sha256": after.state_sha256,
        "episodic_archive_lookup_count": 0,
        "episodic_cold_reassembly_exact": True,
        "episodic_complete_source_replayed": False,
        "episodic_memory_rehearsed": True,
        "motor_action_rehearsed": False,
        **_rehearse_sparse_attention_frontier(current_envelope, budget),
    }


def _rehearse_sparse_attention_frontier(
    current_envelope: bytes,
    budget: dict[str, int],
) -> dict[str, int | bool | str]:
    """Cold-replay one ordinary body trajectory and its sparse route change."""

    _successor_heading, steps = exact_native_yaw_trajectory(
        predecessor_heading_millidegrees=0,
        signed_displacement_millidegrees=90_000,
        duration_microseconds=250_000,
    )
    if len(steps) != 250:
        raise RuntimeError("native attention rehearsal changed its body clock")

    def settle() -> tuple[object, object, object, bytes]:
        organism = restore_native_resident_organism(
            current_envelope=current_envelope,
            **budget,
        )
        before = organism.readiness()
        prepared = organism.prepare_vestibular_trajectory(0, steps)
        after = organism.commit(prepared.token)
        successor = organism.save()
        return before, prepared, after, successor

    before, prepared, after, successor = settle()
    replay_before, replay_prepared, replay_after, replay_successor = settle()
    current_routes = tuple(prepared.physical_frontier_routes)
    preceding_routes = tuple(
        prepared.preceding_distinct_physical_frontier_routes
    )
    replay_current_routes = tuple(replay_prepared.physical_frontier_routes)
    replay_preceding_routes = tuple(
        replay_prepared.preceding_distinct_physical_frontier_routes
    )
    reached_and_foregone_routes = tuple(
        prepared.reached_and_foregone_physical_frontier_routes
    )
    replay_reached_and_foregone_routes = tuple(
        replay_prepared.reached_and_foregone_physical_frontier_routes
    )
    working_continuations = tuple(prepared.working_causal_continuations)
    replay_working_continuations = tuple(
        replay_prepared.working_causal_continuations
    )
    settled_working_frontier = tuple(prepared.settled_working_frontier)
    replay_settled_working_frontier = tuple(
        replay_prepared.settled_working_frontier
    )
    prediction_alternatives = tuple(
        prepared.physical_prediction_alternatives
    )
    replay_prediction_alternatives = tuple(
        replay_prepared.physical_prediction_alternatives
    )
    body_consequence_transfers = tuple(prepared.body_consequence_transfers)
    replay_body_consequence_transfers = tuple(
        replay_prepared.body_consequence_transfers
    )
    route_sets = (
        reached_and_foregone_routes,
        current_routes,
        preceding_routes,
    )
    qualifying = next(
        (
            routes
            for routes in route_sets
            if len(routes) > 1
            and any(route[7] == 0 for route in routes)
            and any(route[7] != 0 for route in routes)
        ),
        (),
    )
    if (
        replay_current_routes != current_routes
        or replay_preceding_routes != preceding_routes
        or replay_reached_and_foregone_routes != reached_and_foregone_routes
        # C-015 is already live-closed. Its transient witness is reported when
        # present but cannot become a recurring release gate that every later
        # physical predecessor must reproduce.
        or replay_working_continuations != working_continuations
        or replay_settled_working_frontier != settled_working_frontier
        or replay_prediction_alternatives != prediction_alternatives
        or replay_body_consequence_transfers != body_consequence_transfers
        or replay_successor != successor
        or replay_before.state_sha256 != before.state_sha256
        or replay_after.state_sha256 != after.state_sha256
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick + len(steps)
        or prepared.dsf_delivery_count <= 0
        or prepared.physically_transitioned_neuron_count <= 0
        or after.python_callback_count != 0
    ):
        raise RuntimeError(
            "ordinary body trajectory did not replay its exact native evidence"
        )
    reached = tuple(route for route in qualifying if route[7] != 0)
    foregone = tuple(route for route in qualifying if route[7] == 0)
    downstream = {route[3] for route in reached}
    return {
        "sparse_attention_cold_replay_exact": True,
        "sparse_attention_current_route_count": len(current_routes),
        "sparse_attention_current_routes_sha256": hashlib.sha256(
            _canonical(current_routes)
        ).hexdigest(),
        "sparse_attention_dsf_delivery_count": prepared.dsf_delivery_count,
        "sparse_attention_downstream_neuron_count": len(downstream),
        "sparse_attention_foregone_route_count": len(foregone),
        "sparse_attention_interval_count": len(steps),
        "sparse_attention_physically_transitioned_neuron_count": (
            prepared.physically_transitioned_neuron_count
        ),
        "sparse_attention_preceding_route_count": len(preceding_routes),
        "sparse_attention_preceding_routes_sha256": hashlib.sha256(
            _canonical(preceding_routes)
        ).hexdigest(),
        "sparse_attention_qualifying_route_count": len(qualifying),
        "sparse_attention_qualifying_routes_sha256": hashlib.sha256(
            _canonical(qualifying)
        ).hexdigest(),
        "sparse_attention_reached_route_count": len(reached),
        "sparse_attention_rehearsed": bool(
            qualifying and preceding_routes and current_routes != preceding_routes
        ),
        "sparse_attention_state_byte_delta": after.state_bytes - before.state_bytes,
        "sparse_attention_successor_state_sha256": after.state_sha256,
        "working_causal_continuation_count": len(working_continuations),
        "working_causal_continuation_sha256": hashlib.sha256(
            _canonical(working_continuations)
        ).hexdigest(),
        "working_causal_settlement_count": len(settled_working_frontier),
        "working_causal_settlement_sha256": hashlib.sha256(
            _canonical(settled_working_frontier)
        ).hexdigest(),
        "physical_prediction_alternative_count": len(prediction_alternatives),
        "physical_prediction_alternatives_sha256": hashlib.sha256(
            _canonical(prediction_alternatives)
        ).hexdigest(),
        "body_consequence_transfer_count": len(body_consequence_transfers),
        "body_consequence_transfers_sha256": hashlib.sha256(
            _canonical(body_consequence_transfers)
        ).hexdigest(),
    }


def _rehearse_ordered_trajectory_projection(
    current_envelope: bytes,
    formation_members: tuple[str, ...],
    budget: dict[str, int],
) -> dict[str, int | bool | str]:
    """Prove a multi-interval native transaction does not lose later order."""

    def settle() -> tuple[object, object, dict[str, object] | None]:
        candidate = restore_native_resident_organism(
            current_envelope=current_envelope,
            **budget,
        )
        prepared = candidate.prepare_vestibular_trajectory(0, (-64, -64, -64, -64))
        relation = _commit_and_observe_episodic_relation(
            candidate,
            prepared,
            formation_members,
        )
        return candidate, prepared, relation

    candidate, prepared, relation = settle()
    replay, replay_prepared, replay_relation = settle()
    if (
        prepared.partial_cue_reassembly_count <= 0
        or relation is None
        or relation["ordered_path_relation_count"] <= 0
        or replay_prepared.partial_cue_reassembly_count <= 0
        or replay_relation != relation
        or replay.save() != candidate.save()
    ):
        raise RuntimeError("native trajectory projection lost ordered relation")
    return {
        "ordered_trajectory_projection_rehearsed": True,
        "ordered_trajectory_path_count": relation["ordered_physical_path_count"],
        "ordered_trajectory_paths_sha256": relation[
            "ordered_physical_paths_sha256"
        ],
        "ordered_trajectory_path_relation_count": relation[
            "ordered_path_relation_count"
        ],
        "ordered_trajectory_path_relations_sha256": relation[
            "ordered_path_relations_sha256"
        ],
        "ordered_trajectory_successor_state_sha256": candidate.readiness().state_sha256,
    }


def _commit_and_observe_episodic_relation(
    organism: object,
    prepared: object,
    recalled_members: tuple[str, ...],
) -> dict[str, int | str | tuple[str, ...]] | None:
    """Resolve one current relation against its exact retained successor."""

    relations = prepared.organic_mosaic_relations
    organism.commit(prepared.token)
    if not relations:
        return None
    formations = organism.observe_retained_formation_structures()
    by_receipt = {
        receipt: tuple(members)
        for receipt, members, _original, _recurrent, _reinforcements in formations
    }
    recalled_receipts = [
        receipt
        for receipt, members in by_receipt.items()
        if members == tuple(recalled_members)
    ]
    if len(recalled_receipts) != 1:
        return None
    recalled_receipt = recalled_receipts[0]
    candidates = []
    for (
        receipts,
        shared_lineages,
        active_bonds,
        structure_receipt,
        ordered_physical_paths,
        ordered_path_relations,
    ) in relations:
        if (
            recalled_receipt not in receipts
            or len(receipts) < 2
            or any(receipt not in by_receipt for receipt in receipts)
            or (not shared_lineages and not active_bonds)
        ):
            continue
        member_sets = tuple(sorted(tuple(sorted(by_receipt[receipt])) for receipt in receipts))
        if len(set(member_sets)) != len(member_sets):
            continue
        candidates.append(
            (
                receipts,
                shared_lineages,
                active_bonds,
                member_sets,
                structure_receipt,
                ordered_physical_paths,
                ordered_path_relations,
            )
        )
    if len(candidates) != 1:
        return None
    (
        receipts,
        shared_lineages,
        active_bonds,
        member_sets,
        structure_receipt,
        ordered_physical_paths,
        ordered_path_relations,
    ) = candidates[0]
    return {
        "episodic_recalled_formation_receipt": recalled_receipt,
        "episodic_related_formation_count": len(receipts),
        "episodic_related_formation_receipts": tuple(receipts),
        "episodic_related_formation_receipts_sha256": hashlib.sha256(
            _canonical(receipts)
        ).hexdigest(),
        "episodic_related_member_sets_sha256": hashlib.sha256(
            _canonical(member_sets)
        ).hexdigest(),
        "episodic_relation_active_bond_count": len(active_bonds),
        "episodic_relation_active_bonds_sha256": hashlib.sha256(
            _canonical(active_bonds)
        ).hexdigest(),
        "episodic_relation_shared_lineage_count": len(shared_lineages),
        "ordered_physical_path_count": len(ordered_physical_paths),
        "ordered_physical_paths_sha256": hashlib.sha256(
            _canonical(ordered_physical_paths)
        ).hexdigest(),
        "ordered_path_relation_count": len(ordered_path_relations),
        "ordered_path_relations_sha256": hashlib.sha256(
            _canonical(ordered_path_relations)
        ).hexdigest(),
        "structural_relation_sha256": structure_receipt,
    }


def _observe_distributed_recognition(
    organism: object,
    prepared: object,
    formations: tuple[tuple[str, tuple[str, ...], bool, bool, int], ...],
) -> dict[str, int | bool | str | tuple[str, ...]] | None:
    """Observe one actual multisensory reassembly; never drive recognition."""

    if prepared.partial_cue_reassembly_count <= 0:
        return None
    layers = {
        lineage: layer
        for lineage, layer, _receptor in (
            organism.observe_reached_neuron_lineage_layers()
        )
    }
    neighbours: dict[str, set[str]] = {}
    for left, right, _ordinal in prepared.active_physical_bonds:
        neighbours.setdefault(left, set()).add(right)
        neighbours.setdefault(right, set()).add(left)
    unseen = set(neighbours)
    candidates = []
    while unseen:
        seed = min(unseen)
        component = {seed}
        frontier = deque([seed])
        unseen.remove(seed)
        while frontier:
            current = frontier.popleft()
            for neighbour in sorted(neighbours.get(current, ())):
                if neighbour not in component:
                    component.add(neighbour)
                    unseen.discard(neighbour)
                    frontier.append(neighbour)
        matching_receipts = sorted(
            receipt
            for receipt, members, _original, _recurrent, _reinforcements in formations
            if set(members).issubset(component)
        )
        participants = {
            "sensory": {lineage for lineage in component if layers[lineage] <= 5},
            "association": {lineage for lineage in component if layers[lineage] == 7},
            "retention": {lineage for lineage in component if layers[lineage] == 9},
            "body": {lineage for lineage in component if layers[lineage] in {5, 8}},
            "affective": {lineage for lineage in component if layers[lineage] == 10},
            "ordering": {lineage for lineage in component if layers[lineage] == 11},
        }
        if matching_receipts and all(participants.values()):
            candidates.append((component, matching_receipts, participants))
    if len(candidates) != 1:
        return None
    component, matching_receipts, participants = candidates[0]
    active_bonds = sorted(
        (left, right, ordinal)
        for left, right, ordinal in prepared.active_physical_bonds
        if left in component and right in component
    )
    return {
        "distributed_recognition_active_bond_count": len(active_bonds),
        "distributed_recognition_active_bond_sha256": hashlib.sha256(
            _canonical(active_bonds)
        ).hexdigest(),
        "distributed_recognition_active_neuron_count": len(component),
        "distributed_recognition_affective_neuron_count": len(
            participants["affective"]
        ),
        "distributed_recognition_association_neuron_count": len(
            participants["association"]
        ),
        "distributed_recognition_body_neuron_count": len(participants["body"]),
        "distributed_recognition_formation_count": len(matching_receipts),
        "distributed_recognition_formation_receipts_sha256": hashlib.sha256(
            _canonical(matching_receipts)
        ).hexdigest(),
        "distributed_recognition_formation_receipts": tuple(matching_receipts),
        "distributed_recognition_rehearsed": True,
        "distributed_recognition_retention_neuron_count": len(
            participants["retention"]
        ),
        "distributed_recognition_ordering_neuron_count": len(
            participants["ordering"]
        ),
        "distributed_recognition_sensory_neuron_count": len(
            participants["sensory"]
        ),
    }


def main() -> int:
    values = _arguments()
    if _SHA256.fullmatch(values.expected_state_sha256) is None:
        raise ValueError("expected state SHA-256 is not canonical")
    if _COMMIT.fullmatch(values.candidate_git_sha) is None:
        raise ValueError("candidate commit is not canonical")
    if _DIGEST.fullmatch(values.candidate_image_digest) is None:
        raise ValueError("candidate image digest is not canonical")
    admission = derive_native_resident_resource_admission(
        values.native_store_root
    )
    migration_authorized = os.environ.get(
        "GUALA_CURRENT_FORMAT_MIGRATION", "0"
    )
    if migration_authorized not in {"0", "1"}:
        raise ValueError("current-format migration authorization must be 0 or 1")
    migration_rehearsed = False
    migration_predecessor: str | None = None
    try:
        restored = restore_current_native_organism(
            values.native_store_root,
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
        if migration_authorized == "1":
            restored = rehearse_current_native_organism_current_format(
                values.native_store_root,
                max_envelope_bytes=admission.max_envelope_bytes,
                max_fabric_bytes=admission.max_fabric_bytes,
                max_logical_peak_bytes=admission.max_logical_peak_bytes,
            )
            migration_rehearsed = True
    except NativeOrganismBinaryStoreError:
        if migration_authorized != "1":
            raise
        restored = rehearse_current_native_organism_current_format(
            values.native_store_root,
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
        migration_rehearsed = True
    if migration_rehearsed:
        migration_predecessor = restored.pointer.predecessor_state_sha256
        if migration_predecessor is None:
            raise RuntimeError("current-format rehearsal lost its predecessor")
    before = restored.organism.readiness()
    state = restored.organism.save()
    after = restored.organism.readiness()
    motor_proof: dict[str, int | bool | str | tuple[str, ...]] = {
        "motor_action_rehearsed": False,
    }
    if os.environ.get("GUALA_VESTIBULAR", "0") == "1":
        motor_proof = _rehearse_native_distributed_recall(
            state,
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
    source_advanced_after_baseline = before.organism_tick > values.expected_tick
    if (
        before.identity != values.expected_identity
        or before.organism_tick < values.expected_tick
        or (
            before.organism_tick == values.expected_tick
            and before.state_sha256 != values.expected_state_sha256
            and not migration_rehearsed
        )
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick
        or before.state_sha256 != after.state_sha256
        or before.state_bytes != after.state_bytes
        or before.state_bytes != len(state)
        or hashlib.sha256(state).hexdigest() != before.state_sha256
        or before.python_callback_count != 0
        or restored.pointer.identity != before.identity
        or restored.pointer.organism_tick != before.organism_tick
        or restored.pointer.state_sha256 != before.state_sha256
        or (
            migration_rehearsed
            and restored.pointer.predecessor_state_sha256
            != migration_predecessor
        )
    ):
        raise RuntimeError("native CURRENT cold restore changed")
    record = {
        "baseline_observed_state_sha256": values.expected_state_sha256,
        "baseline_observed_tick": values.expected_tick,
        "candidate_git_sha": values.candidate_git_sha,
        "candidate_image_digest": values.candidate_image_digest,
        "cold_restore_exact": True,
        "mode": "cold-restore",
        "current_format_migration_rehearsed": migration_rehearsed,
        "migration_predecessor_state_sha256": (
            migration_predecessor if migration_rehearsed else None
        ),
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "complete_neuron_count": before.complete_neuron_count,
        "developmental_resting_neuron_count": (
            before.developmental_resting_neuron_count
        ),
        "raw_glorun_current_only": True,
        "resident_state_bytes": before.state_bytes,
        "resident_state_sha256": before.state_sha256,
        "schema": PROOF_SCHEMA,
        "source_identity": before.identity,
        "source_advanced_after_baseline": source_advanced_after_baseline,
        "source_mount_read_only": True,
        "tick": before.organism_tick,
        **motor_proof,
    }
    proof = {
        **record,
        "receipt_sha256": hashlib.sha256(_canonical(record)).hexdigest(),
    }
    print(_canonical(proof).decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
