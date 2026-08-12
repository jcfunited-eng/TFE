"""Read-only fresh-process proof of one native-organism CURRENT pointer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from dsf_ai_service.glew_runtime.native_resident_organism import (
    exact_motor_unit_yaw_trajectory,
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


def _rehearse_native_sparse_index(
    current_envelope: bytes,
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
    source_dsf_deliveries: int,
    source_physical_transitions: int,
) -> dict[str, int | bool | str]:
    """Prove one bounded member -> layer-9 -> members physical route."""

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
    layer_nine_before = sum(layer == 9 for layer in layers.values())
    formations = organism.observe_retained_formation_structures()

    inbound = organism.prepare_vestibular_tick(0, 64)
    organism.commit(inbound.token)
    outbound = organism.prepare_vestibular_tick(64, 0)
    organism.commit(outbound.token)

    inbound_layer_nine = [
        bond
        for bond in inbound.active_physical_bonds
        if 9 in (layers[bond[0]], layers[bond[1]])
    ]
    if len(inbound_layer_nine) != 1:
        raise RuntimeError("bounded cue did not reach exactly one layer-9 route")
    index_lineage = next(
        lineage
        for lineage in inbound_layer_nine[0][:2]
        if layers[lineage] == 9
    )
    outbound_members = {
        right if left == index_lineage else left
        for left, right, _ordinal in outbound.active_physical_bonds
        if index_lineage in (left, right)
    }
    matching = [
        (receipt, members)
        for receipt, members, _original, _recurrent, _reinforcements in formations
        if set(members) == outbound_members
    ]
    if len(matching) != 1:
        raise RuntimeError(
            "layer-9 route did not reach one exact distributed formation"
        )
    formation_receipt, formation_members = matching[0]

    after = organism.readiness()
    successor_state = organism.save()
    cold = restore_native_resident_organism(
        current_envelope=successor_state,
        **budget,
    )
    layer_nine_after = sum(
        layer == 9
        for _lineage, layer, _receptor in (
            cold.observe_reached_neuron_lineage_layers()
        )
    )
    if (
        source_dsf_deliveries <= 0
        or source_physical_transitions <= 0
        or inbound.dsf_delivery_count <= 0
        or outbound.dsf_delivery_count <= 0
        or inbound.physically_transitioned_neuron_count <= 0
        or outbound.physically_transitioned_neuron_count <= 0
        or len(outbound_members) != len(formation_members)
        or layer_nine_after != layer_nine_before
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick + 2
        or after.python_callback_count != 0
        or after.state_sha256 == before.state_sha256
        or cold.save() != successor_state
        or cold.readiness().state_sha256 != after.state_sha256
    ):
        raise RuntimeError("native sparse-index rehearsal changed")
    return {
        "hippocampal_sparse_index_rehearsed": True,
        "hippocampal_route_formation_receipt": formation_receipt,
        "hippocampal_route_index_lineage": index_lineage,
        "hippocampal_route_inbound_bond_count": len(inbound_layer_nine),
        "hippocampal_route_outbound_member_count": len(outbound_members),
        "hippocampal_route_layer_nine_count": layer_nine_after,
        "hippocampal_route_inbound_transition_count": (
            inbound.physically_transitioned_neuron_count
        ),
        "hippocampal_route_outbound_transition_count": (
            outbound.physically_transitioned_neuron_count
        ),
        "hippocampal_route_state_byte_delta": after.state_bytes - before.state_bytes,
        "hippocampal_route_successor_state_sha256": after.state_sha256,
        "motor_action_rehearsed": False,
    }


def _rehearse_native_motor_action(
    current_envelope: bytes,
    *,
    native_store_root: str,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> dict[str, int | bool | str]:
    """Exercise production sensory source -> motor -> yaw -> balance once.

    The source is one ordinary unattended whole-sensorium interval built by
    the production transport from a copied embodiment world.  No motor event
    is injected.  Both organism and world are throwaway copies and nothing is
    published.
    """

    organism = restore_native_resident_organism(
        current_envelope=current_envelope,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    before = organism.readiness()
    with tempfile.TemporaryDirectory(prefix="guala-motor-rehearsal-") as world_root:
        previous_root = os.environ.get("GUALA_NATIVE_ORGANISM_ROOT")
        os.environ["GUALA_NATIVE_ORGANISM_ROOT"] = world_root
        try:
            from dsf_ai_service import native_production_app as production
        finally:
            if previous_root is None:
                os.environ.pop("GUALA_NATIVE_ORGANISM_ROOT", None)
            else:
                os.environ["GUALA_NATIVE_ORGANISM_ROOT"] = previous_root
        if production.STATE_ROOT != Path(world_root):
            raise RuntimeError("production motor rehearsal did not bind its throwaway root")
        source_world = Path(native_store_root) / production.WORLD_STATE_FILE
        target_world = production.STATE_ROOT / production.WORLD_STATE_FILE
        if source_world.is_file():
            target_world.write_bytes(source_world.read_bytes())

        episodes, environment = production._unattended_interval_episodes(
            "candidate-native-motor-reachability"
        )
        recruitments: list[tuple[str, int, int]] = []
        source_dsf_deliveries = 0
        source_fractals = 0
        source_physical_transitions = 0
        for episode, admissions in episodes:
            prepared = organism.prepare_admitted(episode, admissions)
            organism.commit(prepared.token)
            recruitments.extend(prepared.motor_unit_recruitments)
            source_dsf_deliveries += prepared.dsf_delivery_count
            source_fractals += prepared.complete_neuron_fractal_count
            source_physical_transitions += (
                prepared.physically_transitioned_neuron_count
            )
        if not recruitments:
            return _rehearse_native_sparse_index(
                current_envelope,
                max_envelope_bytes=max_envelope_bytes,
                max_fabric_bytes=max_fabric_bytes,
                max_logical_peak_bytes=max_logical_peak_bytes,
                source_dsf_deliveries=source_dsf_deliveries,
                source_physical_transitions=source_physical_transitions,
            )
        prepared_motor = production._prepare_motor_yaw_action(
            before.state_sha256,
            tuple(recruitments),
        )
        if prepared_motor is None:
            raise RuntimeError("native motor discharge produced no body yaw")
        authority, prepared_world, predecessor_heading, signed_steps = prepared_motor
        with authority.prepared_action_visibility_transaction(prepared_world):
            execution = authority.commit_prepared_action(prepared_world)
            committed_world_body = authority.encoded_committed_prepared_action(
                prepared_world
            )
            production._persist_world_body(committed_world_body)
        authority.verify_execution_receipt(execution)
        successor_heading, expected_steps = exact_motor_unit_yaw_trajectory(
            predecessor_heading_millidegrees=predecessor_heading,
            recruitments=tuple(
                (topology, outward_carriers)
                for _, topology, outward_carriers in recruitments
            ),
        )
        if signed_steps != expected_steps:
            raise RuntimeError("production body boundary changed native motor yaw")
        after_body = next(
            body
            for body in execution.after.bodies
            if body.body_id == execution.after.self_body_id
        )
        vestibular = organism.prepare_vestibular_trajectory(
            predecessor_heading,
            signed_steps,
        )
        organism.commit(vestibular.token)
    after = organism.readiness()
    successor_state = organism.save()
    cold = restore_native_resident_organism(
        current_envelope=successor_state,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    cold_observation = cold.readiness()
    before_total = (
        before.complete_neuron_count
        + before.developmental_resting_neuron_count
    )
    after_total = (
        after.complete_neuron_count
        + after.developmental_resting_neuron_count
    )
    reached_growth = after.complete_neuron_count - before.complete_neuron_count
    resting_use = (
        before.developmental_resting_neuron_count
        - after.developmental_resting_neuron_count
    )
    expected_vestibular_dsf_deliveries = len(signed_steps) * 2
    outward_carriers = sum(channels for _, _, channels in recruitments)
    signed_yaw = sum(signed_steps)
    if (
        len(episodes) == 0
        or outward_carriers <= 0
        or not signed_steps
        or signed_yaw == 0
        or successor_heading
        != (predecessor_heading + signed_yaw) % 360_000
        or after_body.pose.heading_millidegrees != successor_heading
        or execution.after.revision != execution.before.revision + 1
        or after.identity != before.identity
        or after.organism_tick
        != before.organism_tick + len(episodes) + len(signed_steps)
        or after_total != before_total
        or reached_growth < 0
        or resting_use != reached_growth
        or source_dsf_deliveries <= 0
        or source_physical_transitions <= 0
        or vestibular.dsf_delivery_count != expected_vestibular_dsf_deliveries
        or vestibular.physically_transitioned_neuron_count <= 0
        or after.python_callback_count != 0
        or after.state_sha256 == before.state_sha256
        or len(successor_state) != after.state_bytes
        or hashlib.sha256(successor_state).hexdigest() != after.state_sha256
        or cold.save() != successor_state
        or cold_observation.identity != after.identity
        or cold_observation.organism_tick != after.organism_tick
        or cold_observation.state_sha256 != after.state_sha256
    ):
        raise RuntimeError(
            "native motor action rehearsal changed: "
            + json.dumps(
                {
                    "after_complete": after.complete_neuron_count,
                    "after_resting": after.developmental_resting_neuron_count,
                    "after_tick": after.organism_tick,
                    "before_complete": before.complete_neuron_count,
                    "before_resting": before.developmental_resting_neuron_count,
                    "before_tick": before.organism_tick,
                    "cold_equal": cold.save() == successor_state,
                    "motor_recruitment_count": len(recruitments),
                    "outward_carriers": outward_carriers,
                    "signed_yaw": signed_yaw,
                    "source_dsf_deliveries": source_dsf_deliveries,
                    "source_fractals": source_fractals,
                    "source_physical_transitions": source_physical_transitions,
                    "reached_growth": reached_growth,
                    "resting_use": resting_use,
                    "source_hop_count": len(episodes),
                    "step_count": len(signed_steps),
                    "successor_heading": successor_heading,
                    "vestibular_dsf_deliveries": vestibular.dsf_delivery_count,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    return {
        "motor_action_rehearsed": True,
        "motor_rehearsal_external_luminance_present": environment[
            "external_luminance_present"
        ],
        "motor_rehearsal_external_smell_present": environment[
            "external_smell_present"
        ],
        "motor_rehearsal_outward_elementary_carriers": outward_carriers,
        "motor_rehearsal_recruitment_count": len(recruitments),
        "motor_rehearsal_reached_neuron_growth": reached_growth,
        "motor_rehearsal_signed_yaw_millidegrees": signed_yaw,
        "motor_rehearsal_source_dsf_delivery_count": source_dsf_deliveries,
        "motor_rehearsal_source_fractal_count": source_fractals,
        "motor_rehearsal_source_hop_count": len(episodes),
        "motor_rehearsal_source_physical_transition_count": (
            source_physical_transitions
        ),
        "motor_rehearsal_state_byte_delta": after.state_bytes - before.state_bytes,
        "motor_rehearsal_successor_state_sha256": after.state_sha256,
        "motor_rehearsal_vestibular_dsf_delivery_count": (
            vestibular.dsf_delivery_count
        ),
        "motor_rehearsal_vestibular_tick_count": len(signed_steps),
        "motor_rehearsal_world_revision_delta": (
            execution.after.revision - execution.before.revision
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
    motor_proof: dict[str, int | bool | str] = {
        "motor_action_rehearsed": False,
    }
    if os.environ.get("GUALA_VESTIBULAR", "0") == "1":
        motor_proof = _rehearse_native_motor_action(
            state,
            native_store_root=values.native_store_root,
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
