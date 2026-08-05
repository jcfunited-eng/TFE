"""Exact directional causal-resonance census over repeated hearing.

The reciprocal set relation falsified by the causal-recurrence census asks a
noisy observation to be mostly explained by the learned memory.  Causal
recognition has a physical direction instead: the recurrent memory must be
present in the observation, while additional observed structure remains
unclaimed ambient structure.

This probe grows recurrence from five source-disjoint grounded experiences.
Within each physical partition, canonical L6 decides recurrence.  A recurrent
token shared by different causal outcomes is retained as quiescent context; a
grounding-specific recurrent token carries non-null causal identity.  Both the
identity subset and the complete recurrent memory must independently L6-lock
inside a query.  Higher levels use canonical L6 in cochlear topology order.

No command text enters growth after grouping or any relation.  No tolerance,
score, alignment, ML, q identity, Krim reduction, or runtime mutation exists.
All memories retain roots to the original pressure/phase D/M/R/U/C/P/B tuples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
)
from tools.probe_auditory_full_field_causal_recurrence import (
    MAX_EXPERIENCES_PER_GROUNDING,
    MAX_GROUNDINGS,
    RAW_SPEC,
    SPECS,
    _auxiliary_items,
    _evaluate,
    _grounding_receipt,
)
from tools.probe_auditory_full_field_hierarchical_census import (
    HierarchicalSignature,
    HierarchicalSpec,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    FullFieldExperience,
    _digest,
    _l6_payload,
    _mount_experience,
    _root,
    _select_corpus,
)


REPORT_SCHEMA = "guala.audit.full_field_causal_resonance.v1"
RELATION_SCHEMA = "guala.audit.full_field_causal_resonance_relation.v1"


@dataclass(frozen=True, slots=True)
class ResonantPartition:
    partition_id: str
    observed_token_sha256s: frozenset[str]
    recurrent_token_sha256s: frozenset[str]
    shared_token_sha256s: frozenset[str]
    identity_token_sha256s: frozenset[str]
    source_witness_root_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "identity_token_count": len(self.identity_token_sha256s),
            "identity_token_root_sha256": _root(
                "guala.audit.causal_resonance_identity_tokens.v1",
                self.identity_token_sha256s,
            ),
            "observed_token_count": len(self.observed_token_sha256s),
            "observed_token_root_sha256": _root(
                "guala.audit.causal_resonance_observed_tokens.v1",
                self.observed_token_sha256s,
            ),
            "partition_id": self.partition_id,
            "recurrent_token_count": len(
                self.recurrent_token_sha256s
            ),
            "recurrent_token_root_sha256": _root(
                "guala.audit.causal_resonance_recurrent_tokens.v1",
                self.recurrent_token_sha256s,
            ),
            "shared_token_count": len(self.shared_token_sha256s),
            "shared_token_root_sha256": _root(
                "guala.audit.causal_resonance_shared_tokens.v1",
                self.shared_token_sha256s,
            ),
            "source_witness_root_sha256": (
                self.source_witness_root_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class ResonantMemory:
    candidate_id: str
    grounding_receipt_sha256: str
    source_item_ids: tuple[str, ...]
    partitions: tuple[ResonantPartition, ...]
    memory_receipt_sha256: str

    def by_id(self) -> dict[str, ResonantPartition]:
        return {
            value.partition_id: value for value in self.partitions
        }

    def payload(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "grounding_receipt_sha256": (
                self.grounding_receipt_sha256
            ),
            "memory_receipt_sha256": self.memory_receipt_sha256,
            "partitions": [
                value.payload() for value in self.partitions
            ],
            "source_item_ids": list(self.source_item_ids),
        }


def _recurrent(
    token_sets: tuple[frozenset[str], ...],
) -> set[str]:
    if len(token_sets) != MAX_EXPERIENCES_PER_GROUNDING:
        raise ValueError("causal resonance experience count changed")
    counts = Counter(
        token for values in token_sets for token in values
    )
    return {
        token
        for token, count in counts.items()
        if canonical_l6_direction(
            dimensions=len(token_sets),
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
) -> tuple[ResonantMemory, ...]:
    if (
        len(reference_groups) != MAX_GROUNDINGS
        or any(
            len(group) != MAX_EXPERIENCES_PER_GROUNDING
            for group in reference_groups
        )
    ):
        raise ValueError("causal resonance grounding dimensions changed")
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
        raise ValueError("causal resonance crossed physical topology")

    observed_by_grounding = []
    recurrent_by_grounding = []
    witnesses_by_grounding = []
    for group in group_signatures:
        observed = {}
        recurrent = {}
        witnesses = {}
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

    owners = {
        partition_id: {} for partition_id in partition_ids
    }
    for grounding_index, recurrence in enumerate(
        recurrent_by_grounding
    ):
        for partition_id, tokens in recurrence.items():
            for token in tokens:
                owners[partition_id].setdefault(
                    token,
                    set(),
                ).add(grounding_index)

    memories = []
    for grounding_index, group in enumerate(reference_groups):
        grounding = _grounding_receipt(grounding_index)
        partitions = []
        for partition_id in partition_ids:
            recurrent = recurrent_by_grounding[grounding_index][
                partition_id
            ]
            shared = {
                token for token in recurrent
                if len(owners[partition_id][token]) > 1
            }
            partitions.append(ResonantPartition(
                partition_id=partition_id,
                observed_token_sha256s=frozenset(
                    observed_by_grounding[grounding_index][partition_id]
                ),
                recurrent_token_sha256s=frozenset(recurrent),
                shared_token_sha256s=frozenset(shared),
                identity_token_sha256s=frozenset(
                    recurrent - shared
                ),
                source_witness_root_sha256=_root(
                    "guala.audit.causal_resonance_source_witnesses.v1",
                    witnesses_by_grounding[grounding_index][partition_id],
                ),
            ))
        source_item_ids = tuple(
            value.item.item_id for value in group
        )
        payload = {
            "candidate_id": spec.candidate_id,
            "grounding_receipt_sha256": grounding,
            "partitions": [
                value.payload() for value in partitions
            ],
            "schema": "guala.audit.full_field_causal_resonant_memory.v1",
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
        memories.append(ResonantMemory(
            candidate_id=spec.candidate_id,
            grounding_receipt_sha256=grounding,
            source_item_ids=source_item_ids,
            partitions=tuple(partitions),
            memory_receipt_sha256=_digest(payload),
        ))
    return tuple(memories)


def _partition_relation(
    query_tokens: frozenset[str],
    memory: ResonantPartition,
) -> dict[str, object]:
    identity_intersection = query_tokens.intersection(
        memory.identity_token_sha256s
    )
    shared_intersection = query_tokens.intersection(
        memory.shared_token_sha256s
    )
    identity_l6 = canonical_l6_direction(
        dimensions=len(memory.identity_token_sha256s),
        matching_non_null=len(identity_intersection),
        matching_quiescent=0,
    )
    recurrent_l6 = canonical_l6_direction(
        dimensions=len(memory.recurrent_token_sha256s),
        matching_non_null=len(identity_intersection),
        matching_quiescent=len(shared_intersection),
    )
    locked = (
        bool(memory.identity_token_sha256s)
        and identity_l6.locked
        and recurrent_l6.locked
    )
    return {
        "identity_intersection_root_sha256": _root(
            "guala.audit.causal_resonance_identity_intersection.v1",
            identity_intersection,
        ),
        "identity_l6": _l6_payload(identity_l6),
        "locked": locked,
        "partition_id": memory.partition_id,
        "recurrent_l6": _l6_payload(recurrent_l6),
        "shared_intersection_root_sha256": _root(
            "guala.audit.causal_resonance_shared_intersection.v1",
            shared_intersection,
        ),
    }


def _lock_direction(locks: tuple[bool, ...]) -> dict[str, object]:
    return _l6_payload(canonical_l6_direction(
        dimensions=len(locks),
        matching_non_null=sum(locks),
        matching_quiescent=0,
    ))


def _component_relation(
    *,
    query_id: str,
    query: HierarchicalSignature,
    memory: ResonantMemory,
    fields_inside_component: bool,
) -> dict[str, object]:
    query_values = query.by_id()
    memory_values = memory.by_id()
    if set(query_values) != set(memory_values):
        raise ValueError("causal resonance component topology changed")
    details = {
        partition_id: _partition_relation(
            query_values[partition_id].token_sha256s,
            memory_values[partition_id],
        )
        for partition_id in sorted(query_values)
    }
    if fields_inside_component:
        component_locks = tuple(
            canonical_l6_direction(
                dimensions=len(DSF_FIELD_ORDER),
                matching_non_null=sum(
                    details[
                        f"component:{component_index}:field:{field_index}"
                    ]["locked"]
                    for field_index in range(len(DSF_FIELD_ORDER))
                ),
                matching_quiescent=0,
            ).locked
            for component_index in range(
                AUDITORY_KERNEL_COMPONENT_COUNT
            )
        )
    else:
        component_locks = tuple(
            bool(details[f"component:{component_index}"]["locked"])
            for component_index in range(
                AUDITORY_KERNEL_COMPONENT_COUNT
            )
        )
    pressure = component_locks[0::2]
    phase = component_locks[1::2]
    pressure_neighborhoods = tuple(
        canonical_l6_direction(
            dimensions=3,
            matching_non_null=sum(pressure[index:index + 3]),
            matching_quiescent=0,
        ).locked
        for index in range(len(pressure) - 2)
    )
    whole_l6 = _lock_direction(component_locks)
    pressure_l6 = _lock_direction(pressure)
    phase_l6 = _lock_direction(phase)
    pressure_neighborhood_l6 = _lock_direction(
        pressure_neighborhoods
    )
    locked = (
        bool(whole_l6["locked"])
        and bool(pressure_l6["locked"])
        and bool(phase_l6["locked"])
        and bool(pressure_neighborhood_l6["locked"])
    )
    payload = {
        "candidate_id": query.candidate_id,
        "component_locks": list(component_locks),
        "grounding_receipt_sha256": (
            memory.grounding_receipt_sha256
        ),
        "memory_receipt_sha256": memory.memory_receipt_sha256,
        "partition_relation_root_sha256": _digest({
            "partition_relations": details,
            "schema": "guala.audit.causal_resonance_partitions.v1",
        }),
        "phase_bank_l6": phase_l6,
        "pressure_bank_l6": pressure_l6,
        "pressure_neighborhood_bank_l6": (
            pressure_neighborhood_l6
        ),
        "pressure_neighborhood_locks": list(
            pressure_neighborhoods
        ),
        "query_id": query_id,
        "query_quotient_receipt_sha256": (
            query.quotient_receipt_sha256
        ),
        "relation_locked": locked,
        "schema": RELATION_SCHEMA,
        "whole_cochlea_l6": whole_l6,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def _neighborhood_relation(
    *,
    query_id: str,
    query: HierarchicalSignature,
    memory: ResonantMemory,
) -> dict[str, object]:
    query_values = query.by_id()
    memory_values = memory.by_id()
    if set(query_values) != set(memory_values):
        raise ValueError("causal resonance neighborhood topology changed")
    details = {
        partition_id: _partition_relation(
            query_values[partition_id].token_sha256s,
            memory_values[partition_id],
        )
        for partition_id in sorted(query_values)
    }
    neighborhood_locks = []
    by_kind = {"pressure": [], "phase": []}
    for kind in ("pressure", "phase"):
        for start in range(COCHLEAR_CHANNEL_COUNT - 2):
            field_locks = tuple(
                bool(details[
                    f"neighborhood:{kind}:{start}:field:{field_index}"
                ]["locked"])
                for field_index in range(len(DSF_FIELD_ORDER))
            )
            locked = canonical_l6_direction(
                dimensions=len(field_locks),
                matching_non_null=sum(field_locks),
                matching_quiescent=0,
            ).locked
            neighborhood_locks.append(locked)
            by_kind[kind].append(locked)
    whole_l6 = _lock_direction(tuple(neighborhood_locks))
    pressure_l6 = _lock_direction(tuple(by_kind["pressure"]))
    phase_l6 = _lock_direction(tuple(by_kind["phase"]))
    locked = (
        bool(whole_l6["locked"])
        and bool(pressure_l6["locked"])
        and bool(phase_l6["locked"])
    )
    payload = {
        "candidate_id": query.candidate_id,
        "grounding_receipt_sha256": (
            memory.grounding_receipt_sha256
        ),
        "memory_receipt_sha256": memory.memory_receipt_sha256,
        "neighborhood_locks": list(neighborhood_locks),
        "partition_relation_root_sha256": _digest({
            "partition_relations": details,
            "schema": "guala.audit.causal_resonance_partitions.v1",
        }),
        "phase_bank_l6": phase_l6,
        "pressure_bank_l6": pressure_l6,
        "query_id": query_id,
        "query_quotient_receipt_sha256": (
            query.quotient_receipt_sha256
        ),
        "relation_locked": locked,
        "schema": RELATION_SCHEMA,
        "whole_cochlea_l6": whole_l6,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def _relation(
    *,
    spec: HierarchicalSpec,
    query_id: str,
    query: HierarchicalSignature,
    memory: ResonantMemory,
) -> dict[str, object]:
    if (
        spec.candidate_id == RAW_SPEC.candidate_id
        or spec.candidate_id
        == "component_full_ray_b_c_partition_hierarchy_v1"
    ):
        return _component_relation(
            query_id=query_id,
            query=query,
            memory=memory,
            fields_inside_component=False,
        )
    if (
        spec.candidate_id
        == "component_field_order_b_c_hierarchy_v1"
    ):
        return _component_relation(
            query_id=query_id,
            query=query,
            memory=memory,
            fields_inside_component=True,
        )
    if (
        spec.candidate_id
        == "neighborhood_field_order_b_c_hierarchy_v1"
    ):
        return _neighborhood_relation(
            query_id=query_id,
            query=query,
            memory=memory,
        )
    raise ValueError("causal resonance candidate relation is unknown")


def _query_matrix(
    *,
    spec: HierarchicalSpec,
    query_experiences: tuple[FullFieldExperience, ...],
    signatures: Mapping[str, HierarchicalSignature],
    memories: tuple[ResonantMemory, ...],
) -> list[list[dict[str, object]]]:
    return [
        [
            _relation(
                spec=spec,
                query_id=experience.item.item_id,
                query=signatures[experience.item.item_id],
                memory=memory,
            )
            for memory in memories
        ]
        for experience in query_experiences
    ]


def run_causal_resonance(
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
    query_experiences = tuple(corpus_experiences) + auxiliary_experiences
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
            for value in query_experiences
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

    all_experiences = query_experiences
    report = {
        "archive_sha256": archive_digest,
        "candidate_reports": candidate_reports,
        "causal_direction": (
            "memory identity and complete recurrent memory must L6-lock "
            "inside the observation; observation-only structure is neither "
            "discarded nor counted against the causal memory"
        ),
        "causal_fission": (
            "recurrent structure shared across outcomes is retained as "
            "matching quiescence; grounding-specific recurrence must "
            "independently lock as matching non-null"
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
    }
    return report | {"authority_receipt_sha256": _digest(report)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_causal_resonance(
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
            "schema": "guala.audit.full_field_causal_resonance_summary.v1",
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
