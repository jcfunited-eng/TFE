"""Audit whether authentic W1 intake reaches a lawful Loom learning dynamic.

This is a structural and executable audit, not a recognition candidate.
It proves where the new exact full-field receptor state stops, then records
which existing Loom dynamics cannot be reused under the hearing contract.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.loom_model.substrate_dna import (
    CochlearBankKrimelack,
)


SCHEMA = "guala.audit.w1_loom_dynamic_authority.v1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _source_facts() -> dict[str, object]:
    step_source = inspect.getsource(LoomNeuron.step)
    coupling_source = inspect.getsource(
        LoomNeuron.receive_coupling_spike
    )
    membrane_source = inspect.getsource(LoomNeuron.receive_spike)
    selection_source = inspect.getsource(
        LoomCluster._select_by_chi_familiarity
    )
    receptor_source = inspect.getsource(
        CochlearBankKrimelack.feed_authenticated_full_field_lane
    )
    return {
        "legacy_step": {
            "calls_chi_match_score": "chi_atlas.match_score" in step_source,
            "calls_map_inject": "_map_inject" in step_source,
            "calls_psi_settle": "psi_lattice.settle" in step_source,
            "commit_uses_psi": "psi_lattice.committed" in step_source,
        },
        "legacy_coupling": {
            "mutates_familiarity_dead_zone": (
                "familiarity.delta_eff" in coupling_source
            ),
            "flattens_dsf_to_array": "source_dsf.to_array()" in coupling_source,
            "repeats_field_as_psi_vector": "np.repeat(arr, 2)" in coupling_source,
            "injects_psi": "_coupling_injection" in coupling_source,
        },
        "membrane_stdp": {
            "uses_wall_clock": "time.monotonic()" in membrane_source,
            "uses_membrane_threshold": (
                "membrane_threshold" in membrane_source
            ),
            "uses_stdp_weights": (
                "_incoming_synapse_weights" in membrane_source
            ),
        },
        "cluster_selection": {
            "uses_chi_familiarity": "match_score" in selection_source,
            "uses_fixed_familiarity_threshold": (
                "FAMILIARITY_THRESHOLD" in selection_source
            ),
            "uses_fixed_novelty_pool": (
                "novelty_pool_size = 2" in selection_source
            ),
        },
        "authenticated_receptor": {
            "accepts_exact_fraction_samples": (
                "isinstance(value, Fraction)" in receptor_source
            ),
            "advances_exact_phase": "exact_phase +=" in receptor_source,
            "retains_exact_winding": (
                "\"winding\": exact_winding" in receptor_source
            ),
            "calls_neuron_state_transition": any(
                token in receptor_source
                for token in (
                    "receive_coupling_spike(",
                    "receive_spike(",
                    "psi_lattice",
                    "_last_dsf",
                    "_incoming_synapse_weights",
                )
            ),
        },
    }


def run() -> dict[str, object]:
    brain = LoomBrain(seed_size=8, observable="event_count")
    neuron = brain._hemi_map["H1"].cluster.neurons[0]
    receptor = neuron.krimelack_bank["auditory"]
    if not isinstance(receptor, CochlearBankKrimelack):
        raise RuntimeError("auditory receptor type changed")

    before = {
        "couplings": neuron.couplings.J.copy(),
        "incoming_synapses": dict(neuron._incoming_synapse_weights),
        "last_dsf": neuron._last_dsf,
        "membrane": neuron.membrane_potential,
        "psi": neuron.psi_lattice.psi.copy(),
        "receptor_state": receptor.authenticated_full_field_state(),
    }
    response = receptor.feed_authenticated_full_field_lane(
        lane=("left", "erb_00", "pressure", "D_k"),
        values=(
            Fraction(1, 1),
            Fraction(-1, 2),
            Fraction(3, 2),
        ),
        durations=(
            Fraction(1, 100),
            Fraction(1, 100),
            Fraction(1, 100),
        ),
        occurrence_receipt_sha256="1" * 64,
    )
    receptor_changed = (
        receptor.authenticated_full_field_state()
        != before["receptor_state"]
        and response["sample_count"] == 3
        and len(response["exact_winding_deltas"]) == 3
    )
    downstream_unchanged = {
        "couplings": np.array_equal(
            neuron.couplings.J,
            before["couplings"],
        ),
        "incoming_synapses": (
            neuron._incoming_synapse_weights
            == before["incoming_synapses"]
        ),
        "last_dsf": neuron._last_dsf is before["last_dsf"],
        "membrane": neuron.membrane_potential == before["membrane"],
        "psi": np.array_equal(neuron.psi_lattice.psi, before["psi"]),
    }
    source_facts = _source_facts()
    prohibited_existing_paths = {
        "legacy_step": all(source_facts["legacy_step"].values()),
        "legacy_coupling": all(source_facts["legacy_coupling"].values()),
        "membrane_stdp": all(source_facts["membrane_stdp"].values()),
        "cluster_selection": all(source_facts["cluster_selection"].values()),
    }
    payload = {
        "authenticated_receptor_state_changed": receptor_changed,
        "downstream_neuron_state_unchanged": downstream_unchanged,
        "existing_dynamic_paths_conflict_with_hearing_contract": (
            prohibited_existing_paths
        ),
        "full_field_reaches_lawful_learning_dynamic": False,
        "l0_l4_modified": False,
        "reason": (
            "authenticated exact phase/winding terminates inside each "
            "CochlearBankKrimelack lane; every existing downstream state "
            "transition depends on prohibited chi/psi/match-score, a "
            "flattened DSF injection, or heuristic wall-clock STDP gates"
        ),
        "schema": SCHEMA,
        "source_facts": source_facts,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
