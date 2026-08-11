"""Read-only fresh-process proof of one native-organism CURRENT pointer."""

from __future__ import annotations

import argparse
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


PROOF_SCHEMA = "guala.production_native_current_cold_restore.v3"
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


def _rehearse_vestibular_specialization(
    current_envelope: bytes,
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> dict[str, int | bool | str]:
    """Exercise one exact quarter turn on an in-memory copy of CURRENT."""

    organism = restore_native_resident_organism(
        current_envelope=current_envelope,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    before = organism.readiness()
    successor_heading, signed_steps = exact_native_yaw_trajectory(
        predecessor_heading_millidegrees=0,
        signed_displacement_millidegrees=90_000,
        duration_microseconds=250_000,
    )
    heading = 0
    dsf_deliveries = 0
    neuronal_fractals = 0
    physical_transitions = 0
    for signed_step in signed_steps:
        prepared = organism.prepare_vestibular_tick(heading, signed_step)
        organism.commit(prepared.token)
        heading = (heading + signed_step) % 360_000
        dsf_deliveries += prepared.dsf_delivery_count
        neuronal_fractals += prepared.complete_neuron_fractal_count
        physical_transitions += prepared.physically_transitioned_neuron_count
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
    # Every vestibular sample now reaches the already-ratified specialized
    # receptor and its topology-local intrinsic integration neuron.  Both
    # neurons receive one complete, unchanged joint-field DSF delivery.  A
    # A restored, already-experienced body may also claim one integration cell
    # for each receptor topology it had reached before this release.  Therefore
    # there is no lawful fixed growth count here: every reached cell must come
    # from the finite resting population and the total population must remain
    # exactly conserved.  Nor is a new retained neuronal impression mandatory:
    # a body that has already lived this exact quarter-turn may reuse its
    # specialized path without changing any retained-fractal coordinate.  The
    # rehearsal still requires physical motion, full-field delivery, a changed
    # persisted state, and exact cold restoration.
    expected_dsf_deliveries = len(signed_steps) * 2
    if (
        successor_heading != 90_000
        or heading != successor_heading
        or len(signed_steps) != 250
        or sum(signed_steps) != 90_000
        or after.identity != before.identity
        or after.organism_tick != before.organism_tick + 250
        or after_total != before_total
        or reached_growth < 0
        or resting_use != reached_growth
        or dsf_deliveries != expected_dsf_deliveries
        or physical_transitions <= 0
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
            "vestibular specialization rehearsal changed: "
            + json.dumps(
                {
                    "after_complete": after.complete_neuron_count,
                    "after_resting": after.developmental_resting_neuron_count,
                    "after_tick": after.organism_tick,
                    "before_complete": before.complete_neuron_count,
                    "before_resting": before.developmental_resting_neuron_count,
                    "before_tick": before.organism_tick,
                    "cold_equal": cold.save() == successor_state,
                    "dsf_deliveries": dsf_deliveries,
                    "expected_dsf_deliveries": expected_dsf_deliveries,
                    "heading": heading,
                    "neuronal_fractals": neuronal_fractals,
                    "physical_transitions": physical_transitions,
                    "reached_growth": reached_growth,
                    "resting_use": resting_use,
                    "step_count": len(signed_steps),
                    "successor_heading": successor_heading,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    return {
        "vestibular_specialization_rehearsed": True,
        "vestibular_rehearsal_dsf_delivery_count": dsf_deliveries,
        "vestibular_rehearsal_fractal_count": neuronal_fractals,
        "vestibular_rehearsal_physical_transition_count": physical_transitions,
        "vestibular_rehearsal_reached_neuron_growth": reached_growth,
        "vestibular_rehearsal_state_byte_delta": (
            after.state_bytes - before.state_bytes
        ),
        "vestibular_rehearsal_successor_state_sha256": after.state_sha256,
        "vestibular_rehearsal_tick_count": 250,
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
    vestibular_proof: dict[str, int | bool | str] = {
        "vestibular_specialization_rehearsed": False,
    }
    if os.environ.get("GUALA_VESTIBULAR", "0") == "1":
        vestibular_proof = _rehearse_vestibular_specialization(
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
        **vestibular_proof,
    }
    proof = {
        **record,
        "receipt_sha256": hashlib.sha256(_canonical(record)).hexdigest(),
    }
    print(_canonical(proof).decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
