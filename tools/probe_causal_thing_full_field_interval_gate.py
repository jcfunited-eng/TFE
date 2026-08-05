"""Read-only walk-up of experience-grown exact full-field interval gates.

This probe does not create production hearing authority.  It asks whether
bounded extrema learned from repeated, causally grouped real W1 experiences
can provide the missing held-out relation without a tuned tolerance.  Every
gate is an exact closed interval whose endpoints are observed Fractions.
Canonical L6 evaluates the complete fixed gate population.  Labels group
completed reference experiences only and are revealed after every query-to-
memory relation exists.

The complete D/M/R/U/C/P/B trajectories and their L4 support receipts remain
authoritative.  The interval hull is explicitly a diagnostic gating surface,
not a replacement for those trajectories or a THING identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Mapping, Sequence

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.w1_speech_commands_tutor_plan import (
    W1SpeechCommandTutorExample,
    load_w1_speech_command_tutor_plan,
)
from tools.probe_auditory_full_field_separability_census import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    CorpusItem,
    FullFieldExperience,
    _mount_experience,
)


SCHEMA = "guala.audit.causal_thing_full_field_interval_gate.v1"
KEY = b"guala-causal-thing-full-field-interval-gate-20260727"


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


@dataclass(frozen=True, slots=True)
class ExactIntervalGate:
    lower: Fraction
    upper: Fraction

    def contains(self, value: Fraction) -> bool:
        if not isinstance(value, Fraction):
            raise TypeError("full-field interval input is not exact")
        return self.lower <= value <= self.upper


def _items(
    plan: Sequence[W1SpeechCommandTutorExample],
    root: Path,
) -> tuple[tuple[CorpusItem, bytes], ...]:
    result = []
    for ordinal, example in enumerate(plan):
        matches = tuple(
            root.glob(
                f"{example.tutor_command}/"
                f"{example.speaker_sha256_prefix}_nohash_*.wav"
            )
        )
        if len(matches) != 1:
            raise ValueError("speech interval source is not unique")
        wav_data = matches[0].read_bytes()
        wav_sha256 = hashlib.sha256(wav_data).hexdigest()
        result.append((
            CorpusItem(
                item_id=_digest({
                    "pressure_receipt_sha256": (
                        example.pressure.authority_receipt_sha256
                    ),
                    "schema": "guala.audit.interval_corpus_item.v1",
                }),
                oracle_command=example.tutor_command,
                speaker_id=example.speaker_sha256_prefix,
                archive_member=str(matches[0]),
                pcm_sha256=wav_sha256,
                split=(
                    "held_out"
                    if example.tutor_role == "fresh_challenge"
                    else "reference"
                ),
                ordinal=ordinal,
            ),
            wav_data,
        ))
    return tuple(result)


def _global_cells(
    experience: FullFieldExperience,
) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        tuple(
            frame.fields[field_index]
            for frame in component
        )
        for component in experience.frames_by_component
        for field_index in range(len(DSF_FIELD_ORDER))
    )


def _aligned_cells(
    experience: FullFieldExperience,
) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        (frame.fields[field_index],)
        for component in experience.frames_by_component
        for frame in component
        for field_index in range(len(DSF_FIELD_ORDER))
    )


def _memory(
    experiences: Sequence[FullFieldExperience],
    cells: Callable[
        [FullFieldExperience],
        tuple[tuple[Fraction, ...], ...],
    ],
) -> tuple[ExactIntervalGate, ...]:
    observed = tuple(cells(value) for value in experiences)
    if not observed or len({len(value) for value in observed}) != 1:
        raise ValueError("full-field interval topology changed")
    return tuple(
        ExactIntervalGate(
            lower=min(
                value
                for experience in observed
                for value in experience[index]
            ),
            upper=max(
                value
                for experience in observed
                for value in experience[index]
            ),
        )
        for index in range(len(observed[0]))
    )


def _relation(
    memory: Sequence[ExactIntervalGate],
    query: FullFieldExperience,
    cells: Callable[
        [FullFieldExperience],
        tuple[tuple[Fraction, ...], ...],
    ],
) -> dict[str, object]:
    observed = cells(query)
    if len(memory) != len(observed):
        raise ValueError("interval relation topology changed")
    matching = sum(
        all(gate.contains(value) for value in values)
        for gate, values in zip(memory, observed, strict=True)
    )
    direction = canonical_l6_direction(
        dimensions=len(memory),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    return {
        "dimensions": direction.dimensions,
        "effective_dimensions": direction.effective_dimensions,
        "knee": direction.knee,
        "locked": direction.locked,
        "matching_non_null": direction.matching_non_null,
    }


def _overlaps(
    left: ExactIntervalGate,
    right: ExactIntervalGate,
) -> bool:
    return not (
        left.upper < right.lower
        or right.upper < left.lower
    )


def _fissioned_indices(
    command: str,
    memories: Mapping[str, Sequence[ExactIntervalGate]],
) -> tuple[int, ...]:
    selected = memories[command]
    return tuple(
        index
        for index, gate in enumerate(selected)
        if all(
            not _overlaps(gate, other[index])
            for other_command, other in memories.items()
            if other_command != command
        )
    )


def _fissioned_relation(
    memory: Sequence[ExactIntervalGate],
    retained_indices: Sequence[int],
    query: FullFieldExperience,
    cells: Callable[
        [FullFieldExperience],
        tuple[tuple[Fraction, ...], ...],
    ],
) -> dict[str, object]:
    observed = cells(query)
    if not retained_indices:
        return {
            "dimensions": 0,
            "effective_dimensions": 0,
            "knee": 0,
            "locked": False,
            "matching_non_null": 0,
        }
    matching = sum(
        all(memory[index].contains(value) for value in observed[index])
        for index in retained_indices
    )
    direction = canonical_l6_direction(
        dimensions=len(retained_indices),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    return {
        "dimensions": direction.dimensions,
        "effective_dimensions": direction.effective_dimensions,
        "knee": direction.knee,
        "locked": direction.locked,
        "matching_non_null": direction.matching_non_null,
    }


def run(
    *,
    asset_root: Path,
    manifest_path: Path,
) -> dict[str, object]:
    plan = load_w1_speech_command_tutor_plan(
        authority_key=KEY,
        asset_root=asset_root,
        manifest_path=manifest_path,
    )
    selected = _items(plan, asset_root)
    executor = start_exact_field_executor()
    executor.assert_healthy()
    l5_owner = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    )
    try:
        experiences = tuple(
            _mount_experience(
                item=item,
                wav_data=wav_data,
                l5_owner=l5_owner,
            )
            for item, wav_data in selected
        )
    finally:
        stop_exact_field_executor()
    commands = tuple(sorted({
        value.item.oracle_command for value in experiences
    }))
    references = {
        command: tuple(
            value
            for value in experiences
            if (
                value.item.oracle_command == command
                and value.item.split == "reference"
            )
        )
        for command in commands
    }
    held_out = tuple(
        value for value in experiences
        if value.item.split == "held_out"
    )
    candidates: dict[str, object] = {}
    for candidate_id, cell_owner in (
        ("global_trajectory_extrema_v1", _global_cells),
        ("causal_frame_aligned_extrema_v1", _aligned_cells),
    ):
        memories = {
            command: _memory(values, cell_owner)
            for command, values in references.items()
        }
        matrix = {
            query.item.item_id: {
                command: _relation(memory, query, cell_owner)
                for command, memory in memories.items()
            }
            for query in held_out
        }
        decisions = []
        for query in held_out:
            locked = tuple(
                command
                for command, relation in matrix[
                    query.item.item_id
                ].items()
                if relation["locked"]
            )
            decisions.append({
                "expected_command": query.item.oracle_command,
                "held_out_item_id": query.item.item_id,
                "locked_commands": list(locked),
                "passed": locked == (query.item.oracle_command,),
            })
        candidates[candidate_id] = {
            "decision_records": decisions,
            "gate_count": len(next(iter(memories.values()))),
            "held_out_pass_count": sum(
                value["passed"] for value in decisions
            ),
            "held_out_total": len(decisions),
            "matrix": matrix,
            "relation_loss": (
                "interval gates retain extrema but do not preserve "
                "multiplicity or temporal order inside each gate"
                if candidate_id == "global_trajectory_extrema_v1"
                else "aligned gates retain causal frame position but "
                "collapse repeated reference values to observed extrema"
            ),
        }
        fissioned = {
            command: _fissioned_indices(command, memories)
            for command in commands
        }
        fissioned_matrix = {
            query.item.item_id: {
                command: _fissioned_relation(
                    memory,
                    fissioned[command],
                    query,
                    cell_owner,
                )
                for command, memory in memories.items()
            }
            for query in held_out
        }
        fissioned_decisions = []
        for query in held_out:
            locked = tuple(
                command
                for command, relation in fissioned_matrix[
                    query.item.item_id
                ].items()
                if relation["locked"]
            )
            fissioned_decisions.append({
                "expected_command": query.item.oracle_command,
                "held_out_item_id": query.item.item_id,
                "locked_commands": list(locked),
                "passed": locked == (query.item.oracle_command,),
            })
        candidates[f"{candidate_id}.causal_fission_v1"] = {
            "decision_records": fissioned_decisions,
            "gate_count_by_grounding": {
                command: len(indices)
                for command, indices in fissioned.items()
            },
            "held_out_pass_count": sum(
                value["passed"] for value in fissioned_decisions
            ),
            "held_out_total": len(fissioned_decisions),
            "matrix": fissioned_matrix,
            "relation_loss": (
                "experience extrema are retained; any gate whose learned "
                "interval overlaps a causally divergent grounding is "
                "quiescent and cannot supply non-null identity support"
            ),
        }
    payload = {
        "candidate_reports": candidates,
        "command_count": len(commands),
        "field_order": list(DSF_FIELD_ORDER),
        "full_trajectory_authority_retained": True,
        "labels_used_by_gates_or_relations": False,
        "l0_l4_modified": False,
        "pressure_and_phase_component_count": (
            AUDITORY_KERNEL_COMPONENT_COUNT
        ),
        "schema": SCHEMA,
        "source_disjoint_speaker_count": len(experiences),
        "tutor_metadata_used_only_to_emulate_causal_thing_grouping": True,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(
        asset_root=args.asset_root,
        manifest_path=args.manifest,
    )
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
