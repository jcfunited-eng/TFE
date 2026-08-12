"""Read-only fresh-process proof of one native-organism CURRENT pointer."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
import re

from dsf_ai_service.glew_runtime.native_resident_organism import (
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


PROOF_SCHEMA = "guala.production_native_current_cold_restore.v4"
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
    recalled = None
    heading = 0
    transition_count = 0
    dsf_delivery_count = 0
    for ordinal, signed_step in enumerate((64, -64, 0), 1):
        prepared = organism.prepare_vestibular_tick(heading, signed_step)
        transition_count += prepared.physically_transitioned_neuron_count
        dsf_delivery_count += prepared.dsf_delivery_count
        observed = _observe_distributed_recognition(
            organism,
            prepared,
            formations,
        )
        if observed is not None and formation_receipt in observed[
            "distributed_recognition_formation_receipts"
        ]:
            recalled = {
                **observed,
                "distributed_recall_interval_ordinal": ordinal,
            }
        organism.commit(prepared.token)
        heading = (heading + signed_step) % 360_000
    if recalled is None:
        raise RuntimeError("body partial cue produced no distributed recall")
    after = organism.readiness()
    successor_state = organism.save()
    cold = restore_native_resident_organism(
        current_envelope=successor_state,
        **budget,
    )
    if (
        dsf_delivery_count <= 0
        or transition_count <= 0
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick + 3
        or after.python_callback_count != 0
        or after.state_sha256 == before.state_sha256
        or cold.save() != successor_state
        or cold.readiness().state_sha256 != after.state_sha256
    ):
        raise RuntimeError("native distributed-recall rehearsal changed")
    return {
        **recalled,
        "distributed_recognition_episode_ordinal": (
            recalled["distributed_recall_interval_ordinal"] - 1
        ),
        "distributed_recognition_source_dsf_delivery_count": dsf_delivery_count,
        "distributed_recognition_source_hop_count": 3,
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
        "motor_action_rehearsed": False,
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
