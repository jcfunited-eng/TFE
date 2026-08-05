"""Read-only causal-THING familiarity walk-up over existing recurrent neurons.

Five source-disjoint W1 experiences per causal grounding first grow one shared
bilateral auditory neuron bank.  Only after all physical learning is complete
does tutor metadata group finished experiences as stand-ins for authenticated
THING continuity.  A neuron's recurrence across a grounding is evaluated by
canonical L6.  Any neuron that independently locks under more than one
causally divergent grounding is quiescent and cannot identify either.

Held-out sources fire without learning.  This probe reports auditory-only
uniqueness.  It never converts counts to a score, uses a tuned threshold, or
exposes tutor metadata to receptor or neuron construction.  Every activation
retains its complete D/M/R/U/C/P/B occurrence witnesses from both ears.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    _select_corpus,
)
from tools.probe_existing_auditory_neuron_temporal_go_no_go import (
    _mounts,
    _read_pcm,
)


SCHEMA = "guala.audit.causal_thing_bilateral_recurrent_familiarity.v1"
TEST_COMMANDS = COMMANDS[:3]
REFERENCE_COUNT = 5
HELD_OUT_COUNT = 1


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


def _motif_owner() -> AuditoryRecurrentMotifOwner:
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="causal-thing-bilateral-familiarity",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=256 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


def _locked_recurrence(
    activation_sets: tuple[frozenset[str], ...],
) -> frozenset[str]:
    population = frozenset().union(*activation_sets)
    return frozenset(
        neuron_id
        for neuron_id in population
        if canonical_l6_direction(
            dimensions=len(activation_sets),
            matching_non_null=sum(
                neuron_id in values for values in activation_sets
            ),
            matching_quiescent=0,
        ).locked
    )


def _fires(
    required: frozenset[str],
    observed: frozenset[str],
) -> dict[str, object]:
    if not required:
        return {
            "dimensions": 0,
            "effective_dimensions": 0,
            "knee": 0,
            "locked": False,
            "matching_non_null": 0,
        }
    direction = canonical_l6_direction(
        dimensions=len(required),
        matching_non_null=len(required.intersection(observed)),
        matching_quiescent=0,
    )
    return {
        "dimensions": direction.dimensions,
        "effective_dimensions": direction.effective_dimensions,
        "knee": direction.knee,
        "locked": direction.locked,
        "matching_non_null": direction.matching_non_null,
    }


def run(archive_path: Path) -> dict[str, object]:
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech corpus archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus = _select_corpus(archive)
        references = tuple(
            item
            for command in TEST_COMMANDS
            for item in corpus
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        held_out = tuple(
            next(
                item
                for item in corpus
                if (
                    item.oracle_command == command
                    and item.split == "held_out"
                )
            )
            for command in TEST_COMMANDS
        )
        ordered = (*references, *held_out)
        pcm = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in ordered
        }
    if (
        len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT
        or len(held_out) != len(TEST_COMMANDS) * HELD_OUT_COUNT
        or len({item.speaker_id for item in ordered}) != len(ordered)
    ):
        raise ValueError("causal familiarity corpus split changed")
    mounts = _mounts(ordered, pcm)
    owner = _motif_owner()
    learning_records = []
    for item in references:
        settlement = mounts[item.item_id].binaural_receptor_settlement
        observation = owner.observe_binaural(settlement).observation
        learning_records.append({
            "item_id": item.item_id,
            "newly_grown_count": len(
                observation.newly_grown_motif_neuron_ids
            ),
            "reinforced_count": len(
                observation.reinforced_motif_neuron_ids
            ),
        })
    reference_sets = {
        command: tuple(
            frozenset(
                owner.fire_binaural(
                    mounts[
                        item.item_id
                    ].binaural_receptor_settlement
                ).firing.firing_motif_neuron_ids
            )
            for item in references
            if item.oracle_command == command
        )
        for command in TEST_COMMANDS
    }
    recurrent = {
        command: _locked_recurrence(values)
        for command, values in reference_sets.items()
    }
    shared = frozenset(
        neuron_id
        for values in recurrent.values()
        for neuron_id in values
        if sum(
            neuron_id in other
            for other in recurrent.values()
        ) > 1
    )
    fissioned = {
        command: values.difference(shared)
        for command, values in recurrent.items()
    }
    decisions = []
    for item in held_out:
        firing = owner.fire_binaural(
            mounts[item.item_id].binaural_receptor_settlement
        ).firing
        observed = frozenset(firing.firing_motif_neuron_ids)
        relations = {
            command: _fires(required, observed)
            for command, required in fissioned.items()
        }
        locked = tuple(
            command
            for command, relation in relations.items()
            if relation["locked"]
        )
        decisions.append({
            "expected_grounding": item.oracle_command,
            "held_out_item_id": item.item_id,
            "locked_groundings": list(locked),
            "passed": locked == (item.oracle_command,),
            "query_firing_neuron_count": len(observed),
            "relations": relations,
        })
    payload = {
        "causal_fission_rule": (
            "a recurrent neuron locked under divergent THING continuity "
            "is quiescent for identity"
        ),
        "commands": list(TEST_COMMANDS),
        "decision_records": decisions,
        "ear_ids": ["left", "right"],
        "full_field_occurrence_witnesses_retained": True,
        "held_out_pass_count": sum(
            value["passed"] for value in decisions
        ),
        "held_out_total": len(decisions),
        "l0_l4_modified": False,
        "labels_used_by_receptor_or_neuron_construction": False,
        "learning_records": learning_records,
        "motif_owner_status": owner.status(),
        "recurrent_neuron_count_by_grounding": {
            command: len(values)
            for command, values in recurrent.items()
        },
        "schema": SCHEMA,
        "shared_quiescent_neuron_count": len(shared),
        "source_disjoint_speaker_count": len(ordered),
        "thing_specific_neuron_count_by_grounding": {
            command: len(values)
            for command, values in fissioned.items()
        },
        "tutor_metadata_used_only_to_emulate_thing_continuity": True,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.archive)
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    if args.output is not None:
        args.output.write_bytes(encoded)
    print(encoded.decode("utf-8"))


if __name__ == "__main__":
    main()
