"""Read-only repeated-experience auditory causal-recurrence census.

This probe asks a narrower question than one-shot word recognition: can five
source-disjoint, causally grouped auditory experiences grow an exact structural
memory that recalls three unheard speakers, rejects unknown sounds, and keeps
simultaneous words ambiguous rather than forcing a choice?

The folder names in the test archive are used only outside the relation as an
oracle surrogate for a repeated external causal grounding.  A production
learner would receive the grounding from the witnessed object, action, or
consequence.  No command name enters a tokenizer, recurrence decision, fission
decision, or query-to-memory relation.

Every memory retains authenticated roots to the original ordered pressure and
phase D/M/R/U/C/P/B L4 witnesses.  Shared recurrent tokens are not discarded:
they are catalogued as causally divergent and removed only from identity
authority.  Canonical L6 supplies the recurrence and relation decisions.  The
probe does not mutate L0--L4, runtime state, or learned production state.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import wave
import zipfile
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from tools.probe_auditory_full_field_hierarchical_census import (
    SPECS as QUOTIENT_SPECS,
    ExactPartition,
    HierarchicalSignature,
    HierarchicalSpec,
    _component_relation,
    _finish,
    _token,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    HELD_OUT_SPEAKERS_PER_COMMAND,
    REFERENCE_SPEAKERS_PER_COMMAND,
    CorpusItem,
    FullFieldExperience,
    _digest,
    _fraction_text,
    _l6_payload,
    _mount_experience,
    _root,
    _select_corpus,
)


REPORT_SCHEMA = "guala.audit.full_field_causal_recurrence.v1"
MEMORY_SCHEMA = "guala.audit.full_field_causal_memory.v1"
RAW_CANDIDATE = "raw_component_transition_recurrence_hierarchy_v1"
UNKNOWN_ASSETS = (
    "docs/Aurelion/imagined.wav",
    "docs/Aurelion/sample_sound.wav",
)
AMBIGUOUS_COMMAND_PAIRS = (
    ("down", "up"),
    ("go", "stop"),
    ("left", "right"),
    ("no", "yes"),
)
MAX_GROUNDINGS = len(COMMANDS)
MAX_EXPERIENCES_PER_GROUNDING = REFERENCE_SPEAKERS_PER_COMMAND


@dataclass(frozen=True, slots=True)
class CausalPartitionRecord:
    partition_id: str
    observed_token_count: int
    recurrent_token_count: int
    shared_token_count: int
    identity_token_count: int
    observed_token_root_sha256: str
    recurrent_token_root_sha256: str
    shared_token_root_sha256: str
    identity_token_root_sha256: str
    source_witness_root_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "identity_token_count": self.identity_token_count,
            "identity_token_root_sha256": (
                self.identity_token_root_sha256
            ),
            "observed_token_count": self.observed_token_count,
            "observed_token_root_sha256": (
                self.observed_token_root_sha256
            ),
            "partition_id": self.partition_id,
            "recurrent_token_count": self.recurrent_token_count,
            "recurrent_token_root_sha256": (
                self.recurrent_token_root_sha256
            ),
            "shared_token_count": self.shared_token_count,
            "shared_token_root_sha256": self.shared_token_root_sha256,
            "source_witness_root_sha256": (
                self.source_witness_root_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CausalMemory:
    candidate_id: str
    grounding_receipt_sha256: str
    source_item_ids: tuple[str, ...]
    signature: HierarchicalSignature
    partition_records: tuple[CausalPartitionRecord, ...]
    memory_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "grounding_receipt_sha256": (
                self.grounding_receipt_sha256
            ),
            "memory_receipt_sha256": self.memory_receipt_sha256,
            "partition_records": [
                value.payload() for value in self.partition_records
            ],
            "source_item_ids": list(self.source_item_ids),
        }


def _raw_component_transition(
    experience: FullFieldExperience,
) -> HierarchicalSignature:
    partitions = []
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        values = []
        for prior, current in zip(frames, frames[1:]):
            quotient = {
                "current_fields": [
                    _fraction_text(value) for value in current.fields
                ],
                "delta_fields": [
                    _fraction_text(right - left)
                    for left, right in zip(
                        prior.fields,
                        current.fields,
                        strict=True,
                    )
                ],
                "prior_fields": [
                    _fraction_text(value) for value in prior.fields
                ],
                "topology_index": topology_index,
            }
            values.append(_token(
                candidate_id=RAW_CANDIDATE,
                quotient=quotient,
                witnesses=(prior, current),
            ))
        partitions.append(ExactPartition.create(
            partition_id=f"component:{topology_index}",
            values=values,
        ))
    return _finish(RAW_CANDIDATE, experience, partitions)


def _raw_component_relation(
    left_id: str,
    right_id: str,
    left: HierarchicalSignature,
    right: HierarchicalSignature,
) -> dict[str, object]:
    return _component_relation(
        left_id,
        right_id,
        left,
        right,
        fields_inside_component=False,
    )


RAW_SPEC = HierarchicalSpec(
    candidate_id=RAW_CANDIDATE,
    hierarchy=(
        "exact adjacent full seven-field transitions -> each physical "
        "pressure/phase component -> pressure/phase banks and contiguous "
        "pressure neighborhoods -> whole cochlea"
    ),
    quotient_invariance="none over field magnitude or causal delta",
    quotient_loses=(
        "transition multiplicity after exact set formation",
        "global temporal order between distinct transitions",
    ),
    tokenizer=_raw_component_transition,
    relation=_raw_component_relation,
)
SPECS = (RAW_SPEC, *QUOTIENT_SPECS)


def _grounding_receipt(index: int) -> str:
    if not 0 <= index < MAX_GROUNDINGS:
        raise ValueError("causal grounding index left bounded census")
    return _digest({
        "grounding_index": index,
        "schema": "guala.audit.opaque_causal_grounding.v1",
    })


def _recurrent(tokens_by_experience: Iterable[frozenset[str]]) -> set[str]:
    values = tuple(tokens_by_experience)
    if len(values) != MAX_EXPERIENCES_PER_GROUNDING:
        raise ValueError("causal recurrence experience count changed")
    counts = Counter(
        token
        for tokens in values
        for token in tokens
    )
    return {
        token
        for token, count in counts.items()
        if canonical_l6_direction(
            dimensions=len(values),
            matching_non_null=count,
            matching_quiescent=0,
        ).locked
    }


def _grow_memories(
    *,
    spec: HierarchicalSpec,
    reference_groups: tuple[
        tuple[FullFieldExperience, ...],
        ...,
    ],
    signatures: Mapping[str, HierarchicalSignature],
) -> tuple[CausalMemory, ...]:
    if (
        len(reference_groups) != MAX_GROUNDINGS
        or any(
            len(group) != MAX_EXPERIENCES_PER_GROUNDING
            for group in reference_groups
        )
    ):
        raise ValueError("causal grounding census dimensions changed")
    group_signatures = tuple(
        tuple(signatures[value.item.item_id] for value in group)
        for group in reference_groups
    )
    partition_ids = tuple(
        value.partition_id
        for value in group_signatures[0][0].partitions
    )
    if any(
        tuple(value.partition_id for value in signature.partitions)
        != partition_ids
        for group in group_signatures
        for signature in group
    ):
        raise ValueError("causal memory crossed physical topology")

    recurrent_by_grounding: list[dict[str, set[str]]] = []
    observed_by_grounding: list[dict[str, set[str]]] = []
    witnesses_by_grounding: list[dict[str, set[str]]] = []
    for group in group_signatures:
        observed: dict[str, set[str]] = {}
        recurrent: dict[str, set[str]] = {}
        witnesses: dict[str, set[str]] = {}
        for partition_id in partition_ids:
            partitions = tuple(
                signature.by_id()[partition_id]
                for signature in group
            )
            token_sets = tuple(
                value.token_sha256s for value in partitions
            )
            observed[partition_id] = set().union(*token_sets)
            recurrent[partition_id] = _recurrent(token_sets)
            witnesses[partition_id] = {
                value.witness_root_sha256 for value in partitions
            }
        observed_by_grounding.append(observed)
        recurrent_by_grounding.append(recurrent)
        witnesses_by_grounding.append(witnesses)

    owners_by_partition: dict[str, dict[str, set[int]]] = {
        partition_id: {} for partition_id in partition_ids
    }
    for grounding_index, recurrence in enumerate(
        recurrent_by_grounding
    ):
        for partition_id, tokens in recurrence.items():
            for token in tokens:
                owners_by_partition[partition_id].setdefault(
                    token,
                    set(),
                ).add(grounding_index)

    memories = []
    for grounding_index, group in enumerate(reference_groups):
        grounding_receipt = _grounding_receipt(grounding_index)
        partitions = []
        records = []
        for partition_id in partition_ids:
            observed = observed_by_grounding[grounding_index][
                partition_id
            ]
            recurrent = recurrent_by_grounding[grounding_index][
                partition_id
            ]
            shared = {
                token for token in recurrent
                if len(
                    owners_by_partition[partition_id][token]
                ) > 1
            }
            identity = recurrent - shared
            source_witness_root = _root(
                "guala.audit.causal_partition_source_witnesses.v1",
                witnesses_by_grounding[grounding_index][partition_id],
            )
            partitions.append(ExactPartition(
                partition_id=partition_id,
                token_sha256s=frozenset(identity),
                token_root_sha256=_root(
                    "guala.audit.causal_identity_tokens.v1",
                    identity,
                ),
                witness_root_sha256=source_witness_root,
            ))
            records.append(CausalPartitionRecord(
                partition_id=partition_id,
                observed_token_count=len(observed),
                recurrent_token_count=len(recurrent),
                shared_token_count=len(shared),
                identity_token_count=len(identity),
                observed_token_root_sha256=_root(
                    "guala.audit.causal_observed_tokens.v1",
                    observed,
                ),
                recurrent_token_root_sha256=_root(
                    "guala.audit.causal_recurrent_tokens.v1",
                    recurrent,
                ),
                shared_token_root_sha256=_root(
                    "guala.audit.causally_divergent_shared_tokens.v1",
                    shared,
                ),
                identity_token_root_sha256=_root(
                    "guala.audit.causal_identity_tokens.v1",
                    identity,
                ),
                source_witness_root_sha256=source_witness_root,
            ))
        source_item_ids = tuple(
            value.item.item_id for value in group
        )
        receipt_payload = {
            "candidate_id": spec.candidate_id,
            "grounding_receipt_sha256": grounding_receipt,
            "partition_records": [
                value.payload() for value in records
            ],
            "schema": MEMORY_SCHEMA,
            "source_full_field_support_roots": [
                value.l4_support_integrity_sha256 for value in group
            ],
            "source_item_ids": list(source_item_ids),
            "source_tuple_authority_roots": [
                value.tuple_authority_root_sha256 for value in group
            ],
            "source_tuple_support_roots": [
                value.tuple_support_root_sha256 for value in group
            ],
        }
        receipt = _digest(receipt_payload)
        memories.append(CausalMemory(
            candidate_id=spec.candidate_id,
            grounding_receipt_sha256=grounding_receipt,
            source_item_ids=source_item_ids,
            signature=HierarchicalSignature(
                candidate_id=spec.candidate_id,
                partitions=tuple(partitions),
                quotient_receipt_sha256=receipt,
            ),
            partition_records=tuple(records),
            memory_receipt_sha256=receipt,
        ))
    return tuple(memories)


def _read_pcm_wav(data: bytes) -> tuple[int, ...]:
    with wave.open(io.BytesIO(data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != 16_000
            or source.getcomptype() != "NONE"
            or source.getnframes() < 160
            or source.getnframes() > 16_000
            or source.getnframes() % 160 != 0
        ):
            raise ValueError("recurrence WAV left canonical PCM custody")
        frames = source.readframes(source.getnframes())
    return struct.unpack(f"<{len(frames) // 2}h", frames)


def _write_pcm_wav(samples: tuple[int, ...]) -> bytes:
    if (
        not samples
        or len(samples) > 16_000
        or len(samples) % 160 != 0
        or any(value < -32_768 or value > 32_767 for value in samples)
    ):
        raise ValueError("mixed acoustic experience left PCM bounds")
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return output.getvalue()


def _mix_wavs(left: bytes, right: bytes) -> bytes:
    left_samples = _read_pcm_wav(left)
    right_samples = _read_pcm_wav(right)
    length = max(len(left_samples), len(right_samples))
    mixed = []
    for index in range(length):
        left_value = left_samples[index] if index < len(left_samples) else 0
        right_value = (
            right_samples[index] if index < len(right_samples) else 0
        )
        mixed.append(int(Fraction(left_value + right_value, 2)))
    return _write_pcm_wav(tuple(mixed))


def _auxiliary_items(
    *,
    archive: zipfile.ZipFile,
    corpus_items: tuple[CorpusItem, ...],
    workspace: Path,
) -> tuple[
    tuple[tuple[CorpusItem, bytes], ...],
    dict[str, tuple[int, ...]],
]:
    values: list[tuple[CorpusItem, bytes]] = []
    expected: dict[str, tuple[int, ...]] = {}
    ordinal = len(corpus_items)
    for asset_name in UNKNOWN_ASSETS:
        path = workspace / asset_name
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        item = CorpusItem(
            item_id=_digest({
                "asset_sha256": digest,
                "schema": "guala.audit.unknown_sound_item.v1",
            }),
            oracle_command="unknown",
            speaker_id=f"unknown-asset-{digest}",
            archive_member=asset_name,
            pcm_sha256=digest,
            split="unknown",
            ordinal=ordinal,
        )
        ordinal += 1
        values.append((item, data))
        expected[item.item_id] = ()

    held_out = {
        command: next(
            value for value in corpus_items
            if (
                value.oracle_command == command
                and value.split == "held_out"
            )
        )
        for command in COMMANDS
    }
    command_index = {
        command: index for index, command in enumerate(COMMANDS)
    }
    for left_command, right_command in AMBIGUOUS_COMMAND_PAIRS:
        left_item = held_out[left_command]
        right_item = held_out[right_command]
        data = _mix_wavs(
            archive.read(left_item.archive_member),
            archive.read(right_item.archive_member),
        )
        digest = hashlib.sha256(data).hexdigest()
        item = CorpusItem(
            item_id=_digest({
                "left_item_id": left_item.item_id,
                "mixed_pcm_sha256": digest,
                "right_item_id": right_item.item_id,
                "schema": "guala.audit.overlapping_sound_item.v1",
            }),
            oracle_command="ambiguous",
            speaker_id=(
                f"mixture:{left_item.speaker_id}+"
                f"{right_item.speaker_id}"
            ),
            archive_member=(
                f"mixture:{left_item.archive_member}+"
                f"{right_item.archive_member}"
            ),
            pcm_sha256=digest,
            split="ambiguous",
            ordinal=ordinal,
        )
        ordinal += 1
        values.append((item, data))
        expected[item.item_id] = tuple(sorted((
            command_index[left_command],
            command_index[right_command],
        )))
    return tuple(values), expected


def _query_matrix(
    *,
    spec: HierarchicalSpec,
    query_experiences: tuple[FullFieldExperience, ...],
    signatures: Mapping[str, HierarchicalSignature],
    memories: tuple[CausalMemory, ...],
) -> list[list[dict[str, object]]]:
    matrix = []
    for experience in query_experiences:
        row = []
        for memory in memories:
            row.append(spec.relation(
                experience.item.item_id,
                memory.grounding_receipt_sha256,
                signatures[experience.item.item_id],
                memory.signature,
            ))
        matrix.append(row)
    return matrix


def _evaluate(
    *,
    query_experiences: tuple[FullFieldExperience, ...],
    matrix: list[list[dict[str, object]]],
    expected_groundings: Mapping[str, tuple[int, ...]],
) -> dict[str, object]:
    checks = []
    for experience, row in zip(
        query_experiences,
        matrix,
        strict=True,
    ):
        locked = tuple(
            index for index, relation in enumerate(row)
            if relation["relation_locked"]
        )
        expected = expected_groundings[experience.item.item_id]
        checks.append({
            "expected_grounding_indices": list(expected),
            "item_id": experience.item.item_id,
            "locked_grounding_indices": list(locked),
            "oracle_command": experience.item.oracle_command,
            "passed": locked == expected,
            "split": experience.item.split,
        })
    by_split = {}
    for split in ("reference", "held_out", "unknown", "ambiguous"):
        values = [
            value for value in checks if value["split"] == split
        ]
        by_split[split] = {
            "pass_count": sum(value["passed"] for value in values),
            "total": len(values),
        }
    return {
        "by_split": by_split,
        "checks": checks,
        "relation_passed": all(value["passed"] for value in checks),
    }


def run_causal_recurrence(
    *,
    archive_path: Path,
    workspace: Path,
) -> dict[str, object]:
    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_digest != ARCHIVE_SHA256:
        raise ValueError("speech command archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus_items = _select_corpus(archive)
        auxiliary, auxiliary_expected = _auxiliary_items(
            archive=archive,
            corpus_items=corpus_items,
            workspace=workspace,
        )
        executor = start_exact_field_executor()
        executor.assert_healthy()
        owner = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        )
        try:
            corpus_experiences = tuple(
                _mount_experience(
                    item=item,
                    wav_data=archive.read(item.archive_member),
                    l5_owner=owner,
                )
                for item in corpus_items
            )
            auxiliary_experiences = tuple(
                _mount_experience(
                    item=item,
                    wav_data=data,
                    l5_owner=owner,
                )
                for item, data in auxiliary
            )
        finally:
            stop_exact_field_executor()

    command_index = {
        command: index for index, command in enumerate(COMMANDS)
    }
    reference_groups = tuple(
        tuple(
            value for value in corpus_experiences
            if (
                value.item.oracle_command == command
                and value.item.split == "reference"
            )
        )
        for command in COMMANDS
    )
    query_experiences = tuple(
        value for value in corpus_experiences
        if value.item.split in {"reference", "held_out"}
    ) + auxiliary_experiences
    expected_groundings = {
        value.item.item_id: (
            command_index[value.item.oracle_command],
        )
        for value in corpus_experiences
    }
    expected_groundings.update(auxiliary_expected)

    candidate_reports = {}
    for spec in SPECS:
        signatures = {
            value.item.item_id: spec.tokenizer(value)
            for value in (
                *corpus_experiences,
                *auxiliary_experiences,
            )
        }
        memories = _grow_memories(
            spec=spec,
            reference_groups=reference_groups,
            signatures=signatures,
        )
        matrix = _query_matrix(
            spec=spec,
            query_experiences=query_experiences,
            signatures=signatures,
            memories=memories,
        )
        candidate_reports[spec.candidate_id] = {
            "evaluation": _evaluate(
                query_experiences=query_experiences,
                matrix=matrix,
                expected_groundings=expected_groundings,
            ),
            "memories": [value.payload() for value in memories],
            "query_matrix": matrix,
            "specification": spec.record(),
        }

    all_experiences = (
        *corpus_experiences,
        *auxiliary_experiences,
    )
    report = {
        "ambiguous_mixture_rule": (
            "sample-wise exact rational half-sum, quantized toward zero "
            "to signed PCM16; shorter source continues as physical zero"
        ),
        "archive_sha256": archive_digest,
        "candidate_reports": candidate_reports,
        "causal_fission_rule": (
            "a token recurrent under canonical L6 for more than one "
            "grounding is retained as causally divergent shared structure "
            "but cannot carry grounding identity"
        ),
        "commands": list(COMMANDS),
        "experience_supports": [
            {
                "component_support_integrity_sha256s": list(
                    value.component_integrity_sha256s
                ),
                "full_field_support_integrity_sha256": (
                    value.l4_support_integrity_sha256
                ),
                "item_id": value.item.item_id,
                "oracle_command": value.item.oracle_command,
                "pcm_sha256": value.item.pcm_sha256,
                "speaker_id": value.item.speaker_id,
                "split": value.item.split,
                "tuple_authority_root_sha256": (
                    value.tuple_authority_root_sha256
                ),
                "tuple_support_root_sha256": (
                    value.tuple_support_root_sha256
                ),
            }
            for value in all_experiences
        ],
        "field_order": list(DSF_FIELD_ORDER),
        "grounding_oracle_used_only_to_group_reference_experiences": True,
        "labels_used_by_query_relations": False,
        "l0_l4_modified": False,
        "not_proof_of_learned_semantics": True,
        "query_item_ids": [
            value.item.item_id for value in query_experiences
        ],
        "recurrence_rule": (
            "within each physical partition a token recurs only when "
            "canonical L6 locks its presence across five source-disjoint "
            "causally grouped reference experiences"
        ),
        "reference_experiences_per_grounding": (
            MAX_EXPERIENCES_PER_GROUNDING
        ),
        "resource_bounds": {
            "candidate_count": len(SPECS),
            "grounding_count": MAX_GROUNDINGS,
            "query_count": len(query_experiences),
            "state_mutation": False,
        },
        "schema": REPORT_SCHEMA,
        "source_disjoint_corpus_speaker_count": len({
            value.item.speaker_id for value in corpus_experiences
        }),
        "unknown_assets": list(UNKNOWN_ASSETS),
    }
    return report | {"authority_receipt_sha256": _digest(report)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_causal_recurrence(
        archive_path=args.archive,
        workspace=args.workspace,
    )
    if args.summary:
        report = {
            "archive_sha256": report["archive_sha256"],
            "authority_receipt_sha256": (
                report["authority_receipt_sha256"]
            ),
            "candidates": {
                key: value["evaluation"]["by_split"]
                for key, value in report["candidate_reports"].items()
            },
            "schema": "guala.audit.full_field_causal_recurrence_summary.v1",
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
