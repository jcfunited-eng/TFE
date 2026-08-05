"""Hierarchical extension of the read-only full-field separability census.

The v1 census deliberately tested exact quotient-token sets without labels,
but one global set still lets populous components dominate and therefore is a
reduced field evaluation.  This probe keeps the same verified corpus and
complete L0--L4 witnesses while applying canonical L6 in physical order:

    exact token relation -> field -> component/neighborhood
    -> pressure and phase banks -> whole cochlea.

No relation receives a command name.  Labels enter only after all 64x64
matrices exist.  No runtime owner or learned state is mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

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
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    HELD_OUT_SPEAKERS_PER_COMMAND,
    REFERENCE_SPEAKERS_PER_COMMAND,
    CorpusItem,
    ExactFrame,
    FullFieldExperience,
    _canonical,
    _digest,
    _direction,
    _l6_payload,
    _mount_experience,
    _positive_scale_ray,
    _root,
    _select_corpus,
)


REPORT_SCHEMA = "guala.audit.full_field_hierarchical_census.v1"
TOKEN_SCHEMA = "guala.audit.full_field_hierarchical_token.v1"
RELATION_SCHEMA = "guala.audit.full_field_hierarchical_relation.v1"
MAX_TOKENS_PER_PARTITION = 512


@dataclass(frozen=True, slots=True)
class ExactPartition:
    partition_id: str
    token_sha256s: frozenset[str]
    token_root_sha256: str
    witness_root_sha256: str

    @classmethod
    def create(
        cls,
        *,
        partition_id: str,
        values: Iterable[tuple[str, str]],
    ) -> "ExactPartition":
        tokens: dict[str, set[str]] = {}
        for token, witness in values:
            tokens.setdefault(token, set()).add(witness)
        if (
            not tokens
            or len(tokens) > MAX_TOKENS_PER_PARTITION
        ):
            raise ValueError("hierarchical partition token boundary changed")
        token_values = frozenset(tokens)
        return cls(
            partition_id=partition_id,
            token_sha256s=token_values,
            token_root_sha256=_root(
                "guala.audit.hierarchical_partition_tokens.v1",
                token_values,
            ),
            witness_root_sha256=_digest({
                "partition_id": partition_id,
                "schema": (
                    "guala.audit.hierarchical_partition_witnesses.v1"
                ),
                "token_witness_roots": [
                    [
                        token,
                        _root(
                            "guala.audit.hierarchical_token_witness_set.v1",
                            witnesses,
                        ),
                    ]
                    for token, witnesses in sorted(tokens.items())
                ],
            }),
        )


@dataclass(frozen=True, slots=True)
class HierarchicalSignature:
    candidate_id: str
    partitions: tuple[ExactPartition, ...]
    quotient_receipt_sha256: str

    def by_id(self) -> dict[str, ExactPartition]:
        return {
            value.partition_id: value for value in self.partitions
        }


@dataclass(frozen=True, slots=True)
class HierarchicalSpec:
    candidate_id: str
    hierarchy: str
    quotient_invariance: str
    quotient_loses: tuple[str, ...]
    tokenizer: Callable[[FullFieldExperience], HierarchicalSignature]
    relation: Callable[
        [str, str, HierarchicalSignature, HierarchicalSignature],
        dict[str, object],
    ]

    def record(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "full_fields_used": list(DSF_FIELD_ORDER),
            "hierarchy": self.hierarchy,
            "pressure_and_phase_used": True,
            "quotient_invariance": self.quotient_invariance,
            "quotient_loses": list(self.quotient_loses),
        }


def _token(
    *,
    candidate_id: str,
    quotient: object,
    witnesses: Iterable[ExactFrame],
) -> tuple[str, str]:
    witness_values = tuple(sorted({
        value.tuple_integrity_sha256 for value in witnesses
    }))
    if not witness_values:
        raise ValueError("hierarchical token lacks full-field witnesses")
    token = _digest({
        "candidate_id": candidate_id,
        "quotient": quotient,
        "schema": TOKEN_SCHEMA,
    })
    witness = _digest({
        "candidate_token_sha256": token,
        "schema": "guala.audit.hierarchical_token_witness.v1",
        "tuple_support_integrity_sha256s": list(witness_values),
    })
    return token, witness


def _finish(
    candidate_id: str,
    experience: FullFieldExperience,
    partitions: Iterable[ExactPartition],
) -> HierarchicalSignature:
    values = tuple(sorted(
        partitions,
        key=lambda value: value.partition_id,
    ))
    if not values or len({value.partition_id for value in values}) != len(
        values
    ):
        raise ValueError("hierarchical partition topology changed")
    receipt = _digest({
        "candidate_id": candidate_id,
        "full_field_support_integrity_sha256": (
            experience.l4_support_integrity_sha256
        ),
        "partitions": [
            [
                value.partition_id,
                value.token_root_sha256,
                value.witness_root_sha256,
            ]
            for value in values
        ],
        "schema": "guala.audit.full_field_hierarchical_quotient.v1",
    })
    return HierarchicalSignature(
        candidate_id=candidate_id,
        partitions=values,
        quotient_receipt_sha256=receipt,
    )


def _component_field_order(
    experience: FullFieldExperience,
) -> HierarchicalSignature:
    candidate = "component_field_order_b_c_hierarchy_v1"
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    partitions = []
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        for field_index, field_name in enumerate(DSF_FIELD_ORDER):
            values = []
            prior_quotient = None
            for prior, current, following in zip(
                frames,
                frames[1:],
                frames[2:],
            ):
                quotient = {
                    "B_k_gate": [
                        _direction(
                            prior.fields[b_index],
                            current.fields[b_index],
                        ),
                        _direction(
                            current.fields[b_index],
                            following.fields[b_index],
                        ),
                    ],
                    "C_k_gate": [
                        _direction(
                            prior.fields[c_index],
                            current.fields[c_index],
                        ),
                        _direction(
                            current.fields[c_index],
                            following.fields[c_index],
                        ),
                    ],
                    "field_name": field_name,
                    "local_order_type": [
                        _direction(
                            prior.fields[field_index],
                            current.fields[field_index],
                        ),
                        _direction(
                            current.fields[field_index],
                            following.fields[field_index],
                        ),
                        _direction(
                            prior.fields[field_index],
                            following.fields[field_index],
                        ),
                    ],
                    "topology_index": topology_index,
                }
                if quotient == prior_quotient:
                    continue
                prior_quotient = quotient
                values.append(_token(
                    candidate_id=candidate,
                    quotient=quotient,
                    witnesses=(prior, current, following),
                ))
            partitions.append(ExactPartition.create(
                partition_id=f"component:{topology_index}:field:{field_index}",
                values=values,
            ))
    return _finish(candidate, experience, partitions)


def _component_ray_gate(
    experience: FullFieldExperience,
) -> HierarchicalSignature:
    candidate = "component_full_ray_b_c_partition_hierarchy_v1"
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    partitions = []
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        values = []
        prior_quotient = None
        for prior, current in zip(frames, frames[1:]):
            deltas = tuple(
                right - left
                for left, right in zip(
                    prior.fields,
                    current.fields,
                    strict=True,
                )
            )
            quotient = {
                "B_k_gate": _direction(
                    prior.fields[b_index],
                    current.fields[b_index],
                ),
                "C_k_gate": _direction(
                    prior.fields[c_index],
                    current.fields[c_index],
                ),
                "positive_scale_delta_ray": list(
                    _positive_scale_ray(deltas)
                ),
                "positive_scale_state_ray": list(
                    _positive_scale_ray(current.fields)
                ),
                "topology_index": topology_index,
            }
            if quotient == prior_quotient:
                continue
            prior_quotient = quotient
            values.append(_token(
                candidate_id=candidate,
                quotient=quotient,
                witnesses=(prior, current),
            ))
        partitions.append(ExactPartition.create(
            partition_id=f"component:{topology_index}",
            values=values,
        ))
    return _finish(candidate, experience, partitions)


def _neighborhood_field_order(
    experience: FullFieldExperience,
) -> HierarchicalSignature:
    candidate = "neighborhood_field_order_b_c_hierarchy_v1"
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    partitions = []
    for parity, kind in ((0, "pressure"), (1, "phase")):
        for start in range(COCHLEAR_CHANNEL_COUNT - 2):
            component_indices = tuple(
                channel * 2 + parity
                for channel in range(start, start + 3)
            )
            for field_index, field_name in enumerate(DSF_FIELD_ORDER):
                values = []
                prior_quotient = None
                for frame_index in range(1, experience.observation_count):
                    prior = tuple(
                        experience.frames_by_component[index][frame_index - 1]
                        for index in component_indices
                    )
                    current = tuple(
                        experience.frames_by_component[index][frame_index]
                        for index in component_indices
                    )
                    quotient = {
                        "B_k_gates": [
                            _direction(
                                left.fields[b_index],
                                right.fields[b_index],
                            )
                            for left, right in zip(
                                prior,
                                current,
                                strict=True,
                            )
                        ],
                        "C_k_gates": [
                            _direction(
                                left.fields[c_index],
                                right.fields[c_index],
                            )
                            for left, right in zip(
                                prior,
                                current,
                                strict=True,
                            )
                        ],
                        "component_kind": kind,
                        "cross_channel_order": [
                            _direction(
                                current[left].fields[field_index],
                                current[right].fields[field_index],
                            )
                            for left, right in ((0, 1), (1, 2), (0, 2))
                        ],
                        "field_name": field_name,
                        "neighborhood_start": start,
                        "temporal_order": [
                            _direction(
                                left.fields[field_index],
                                right.fields[field_index],
                            )
                            for left, right in zip(
                                prior,
                                current,
                                strict=True,
                            )
                        ],
                    }
                    if quotient == prior_quotient:
                        continue
                    prior_quotient = quotient
                    values.append(_token(
                        candidate_id=candidate,
                        quotient=quotient,
                        witnesses=(*prior, *current),
                    ))
                partitions.append(ExactPartition.create(
                    partition_id=(
                        f"neighborhood:{kind}:{start}:field:{field_index}"
                    ),
                    values=values,
                ))
    return _finish(candidate, experience, partitions)


def _partition_relation(
    left: ExactPartition,
    right: ExactPartition,
) -> tuple[bool, dict[str, object]]:
    if left.partition_id != right.partition_id:
        raise ValueError("hierarchical relation crossed partitions")
    intersection = left.token_sha256s.intersection(
        right.token_sha256s
    )
    matching = len(intersection)
    left_l6 = canonical_l6_direction(
        dimensions=len(left.token_sha256s),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(right.token_sha256s),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    locked = left_l6.locked and right_l6.locked
    return locked, {
        "intersection_root_sha256": _root(
            "guala.audit.hierarchical_partition_intersection.v1",
            intersection,
        ),
        "left_l6": _l6_payload(left_l6),
        "locked": locked,
        "matching_token_count": matching,
        "partition_id": left.partition_id,
        "right_l6": _l6_payload(right_l6),
    }


def _bank_direction(
    locks: tuple[bool, ...],
) -> dict[str, object]:
    direction = canonical_l6_direction(
        dimensions=len(locks),
        matching_non_null=sum(locks),
        matching_quiescent=0,
    )
    return _l6_payload(direction)


def _component_relation(
    left_id: str,
    right_id: str,
    left: HierarchicalSignature,
    right: HierarchicalSignature,
    *,
    fields_inside_component: bool,
) -> dict[str, object]:
    left_values = left.by_id()
    right_values = right.by_id()
    if set(left_values) != set(right_values):
        raise ValueError("component hierarchy changed partitions")
    details = tuple(
        _partition_relation(
            left_values[partition_id],
            right_values[partition_id],
        )[1]
        for partition_id in sorted(left_values)
    )
    if fields_inside_component:
        component_locks = []
        for component_index in range(AUDITORY_KERNEL_COMPONENT_COUNT):
            field_locks = tuple(
                bool(next(
                    value["locked"] for value in details
                    if value["partition_id"] == (
                        f"component:{component_index}:field:{field_index}"
                    )
                ))
                for field_index in range(len(DSF_FIELD_ORDER))
            )
            component_locks.append(
                canonical_l6_direction(
                    dimensions=len(field_locks),
                    matching_non_null=sum(field_locks),
                    matching_quiescent=0,
                ).locked
            )
    else:
        component_locks = [
            bool(next(
                value["locked"] for value in details
                if value["partition_id"] == f"component:{component_index}"
            ))
            for component_index in range(AUDITORY_KERNEL_COMPONENT_COUNT)
        ]
    component_values = tuple(component_locks)
    pressure = component_values[0::2]
    phase = component_values[1::2]
    whole = _bank_direction(component_values)
    pressure_direction = _bank_direction(pressure)
    phase_direction = _bank_direction(phase)
    pressure_neighborhoods = tuple(
        canonical_l6_direction(
            dimensions=3,
            matching_non_null=sum(pressure[index:index + 3]),
            matching_quiescent=0,
        ).locked
        for index in range(len(pressure) - 2)
    )
    locked = (
        bool(whole["locked"])
        and bool(pressure_direction["locked"])
        and bool(phase_direction["locked"])
        and all(pressure_neighborhoods)
    )
    payload = {
        "candidate_id": left.candidate_id,
        "component_locks": list(component_values),
        "left_item_id": left_id,
        "left_quotient_receipt_sha256": left.quotient_receipt_sha256,
        "partition_relation_root_sha256": _digest({
            "partition_relations": details,
            "schema": "guala.audit.hierarchical_partition_relations.v1",
        }),
        "phase_bank_l6": phase_direction,
        "pressure_bank_l6": pressure_direction,
        "pressure_neighborhood_locks": list(pressure_neighborhoods),
        "relation_locked": locked,
        "right_item_id": right_id,
        "right_quotient_receipt_sha256": right.quotient_receipt_sha256,
        "schema": RELATION_SCHEMA,
        "whole_cochlea_l6": whole,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def _component_field_relation(
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
        fields_inside_component=True,
    )


def _component_ray_relation(
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


def _neighborhood_relation(
    left_id: str,
    right_id: str,
    left: HierarchicalSignature,
    right: HierarchicalSignature,
) -> dict[str, object]:
    left_values = left.by_id()
    right_values = right.by_id()
    details = tuple(
        _partition_relation(
            left_values[partition_id],
            right_values[partition_id],
        )[1]
        for partition_id in sorted(left_values)
    )
    neighborhood_locks = []
    by_kind: dict[str, list[bool]] = {"pressure": [], "phase": []}
    for kind in ("pressure", "phase"):
        for start in range(COCHLEAR_CHANNEL_COUNT - 2):
            field_locks = tuple(
                bool(next(
                    value["locked"] for value in details
                    if value["partition_id"] == (
                        f"neighborhood:{kind}:{start}:field:{field_index}"
                    )
                ))
                for field_index in range(len(DSF_FIELD_ORDER))
            )
            locked = canonical_l6_direction(
                dimensions=len(field_locks),
                matching_non_null=sum(field_locks),
                matching_quiescent=0,
            ).locked
            neighborhood_locks.append(locked)
            by_kind[kind].append(locked)
    whole = _bank_direction(tuple(neighborhood_locks))
    pressure = _bank_direction(tuple(by_kind["pressure"]))
    phase = _bank_direction(tuple(by_kind["phase"]))
    locked = (
        bool(whole["locked"])
        and bool(pressure["locked"])
        and bool(phase["locked"])
    )
    payload = {
        "candidate_id": left.candidate_id,
        "left_item_id": left_id,
        "left_quotient_receipt_sha256": left.quotient_receipt_sha256,
        "neighborhood_locks": list(neighborhood_locks),
        "partition_relation_root_sha256": _digest({
            "partition_relations": details,
            "schema": "guala.audit.hierarchical_partition_relations.v1",
        }),
        "phase_bank_l6": phase,
        "pressure_bank_l6": pressure,
        "relation_locked": locked,
        "right_item_id": right_id,
        "right_quotient_receipt_sha256": right.quotient_receipt_sha256,
        "schema": RELATION_SCHEMA,
        "whole_cochlea_l6": whole,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


SPECS = (
    HierarchicalSpec(
        candidate_id="component_field_order_b_c_hierarchy_v1",
        hierarchy=(
            "token set -> each D/M/R/U/C/P/B field -> each component -> "
            "pressure/phase banks and contiguous pressure neighborhoods -> "
            "whole cochlea"
        ),
        quotient_invariance=(
            "independent monotone transform of each field across local "
            "three-observation order types"
        ),
        quotient_loses=(
            "field magnitudes",
            "causal-delta ratios",
            "multiplicity and nonlocal temporal order",
        ),
        tokenizer=_component_field_order,
        relation=_component_field_relation,
    ),
    HierarchicalSpec(
        candidate_id="component_full_ray_b_c_partition_hierarchy_v1",
        hierarchy=(
            "exact ray token set -> component -> pressure/phase banks and "
            "contiguous pressure neighborhoods -> whole cochlea"
        ),
        quotient_invariance=(
            "strictly-positive common rational scale per complete "
            "seven-field state and causal-delta tuple"
        ),
        quotient_loses=(
            "absolute common tuple scale",
            "multiplicity and global temporal order",
        ),
        tokenizer=_component_ray_gate,
        relation=_component_ray_relation,
    ),
    HierarchicalSpec(
        candidate_id="neighborhood_field_order_b_c_hierarchy_v1",
        hierarchy=(
            "token set -> each field -> each three-channel neighborhood -> "
            "pressure/phase neighborhood banks -> whole cochlea"
        ),
        quotient_invariance=(
            "independent monotone field transforms retaining exact temporal "
            "and cross-channel order inside each neighborhood"
        ),
        quotient_loses=(
            "field magnitudes",
            "causal-delta ratios",
            "multiplicity and nonlocal temporal order",
        ),
        tokenizer=_neighborhood_field_order,
        relation=_neighborhood_relation,
    ),
)


def _evaluate(
    items: tuple[CorpusItem, ...],
    matrix: list[list[dict[str, object]]],
) -> dict[str, object]:
    within = []
    cross = []
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(
                matrix[left_index][right_index]["relation_locked"]
            )
            (within if left.oracle_command == right.oracle_command else cross).append(
                locked
            )
    checks = []
    for query_index, query in enumerate(items):
        if query.split != "held_out":
            continue
        same = []
        other = []
        for reference_index, reference in enumerate(items):
            if reference.split != "reference":
                continue
            if matrix[query_index][reference_index]["relation_locked"]:
                (
                    same
                    if query.oracle_command == reference.oracle_command
                    else other
                ).append(reference.item_id)
        checks.append({
            "held_out_item_id": query.item_id,
            "oracle_command": query.oracle_command,
            "other_command_reference_lock_count": len(other),
            "other_command_reference_locks": other,
            "passed": (
                len(same) == REFERENCE_SPEAKERS_PER_COMMAND
                and not other
            ),
            "same_command_reference_lock_count": len(same),
            "same_command_reference_locks": same,
        })
    return {
        "cross_command_locked_pairs": sum(cross),
        "cross_command_pair_count": len(cross),
        "held_out_checks": checks,
        "held_out_pass_count": sum(value["passed"] for value in checks),
        "held_out_total": len(checks),
        "relation_passed": (
            all(within) and not any(cross)
            and all(value["passed"] for value in checks)
        ),
        "within_command_locked_pairs": sum(within),
        "within_command_pair_count": len(within),
    }


def _matrix(
    spec: HierarchicalSpec,
    items: tuple[CorpusItem, ...],
    signatures: Mapping[str, HierarchicalSignature],
) -> list[list[dict[str, object]]]:
    result = []
    for left in items:
        row = []
        for right in items:
            if left.item_id == right.item_id:
                signature = signatures[left.item_id]
                row.append({
                    "authority_receipt_sha256": _digest({
                        "candidate_id": spec.candidate_id,
                        "item_id": left.item_id,
                        "schema": "guala.audit.hierarchical_identity.v1",
                        "quotient_receipt_sha256": (
                            signature.quotient_receipt_sha256
                        ),
                    }),
                    "relation_locked": True,
                })
            else:
                row.append(spec.relation(
                    left.item_id,
                    right.item_id,
                    signatures[left.item_id],
                    signatures[right.item_id],
                ))
        result.append(row)
    return result


def run_hierarchical_census(archive_path: Path) -> dict[str, object]:
    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_digest != ARCHIVE_SHA256:
        raise ValueError("speech command archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        executor = start_exact_field_executor()
        executor.assert_healthy()
        l5_owner = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        )
        try:
            experiences = tuple(
                _mount_experience(
                    item=item,
                    wav_data=archive.read(item.archive_member),
                    l5_owner=l5_owner,
                )
                for item in items
            )
        finally:
            stop_exact_field_executor()
    reports = {}
    witness_records = {}
    for spec in SPECS:
        signatures = {
            value.item.item_id: spec.tokenizer(value)
            for value in experiences
        }
        matrix = _matrix(spec, items, signatures)
        reports[spec.candidate_id] = {
            "evaluation": _evaluate(items, matrix),
            "matrix": matrix,
            "specification": spec.record(),
        }
        witness_records[spec.candidate_id] = {
            item_id: {
                "partition_count": len(signature.partitions),
                "partition_root_sha256": _digest({
                    "partitions": [
                        [
                            value.partition_id,
                            value.token_root_sha256,
                            value.witness_root_sha256,
                        ]
                        for value in signature.partitions
                    ],
                    "schema": (
                        "guala.audit.hierarchical_partition_catalog.v1"
                    ),
                }),
                "quotient_receipt_sha256": (
                    signature.quotient_receipt_sha256
                ),
            }
            for item_id, signature in signatures.items()
        }
    report = {
        "archive_sha256": archive_digest,
        "candidate_reports": reports,
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
                "speaker_id": value.item.speaker_id,
                "split": value.item.split,
                "tuple_authority_root_sha256": (
                    value.tuple_authority_root_sha256
                ),
                "tuple_support_root_sha256": (
                    value.tuple_support_root_sha256
                ),
            }
            for value in experiences
        ],
        "field_order": list(DSF_FIELD_ORDER),
        "held_out_speakers_per_command": (
            HELD_OUT_SPEAKERS_PER_COMMAND
        ),
        "labels_used_by_relations": False,
        "l0_l4_modified": False,
        "matrix_item_ids": [value.item_id for value in items],
        "reference_speakers_per_command": (
            REFERENCE_SPEAKERS_PER_COMMAND
        ),
        "schema": REPORT_SCHEMA,
        "source_disjoint_speaker_count": len({
            value.speaker_id for value in items
        }),
        "witness_records": witness_records,
    }
    return report | {"authority_receipt_sha256": _digest(report)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_hierarchical_census(args.archive)
    if args.summary:
        report = {
            "archive_sha256": report["archive_sha256"],
            "authority_receipt_sha256": (
                report["authority_receipt_sha256"]
            ),
            "candidates": {
                key: value["evaluation"]
                for key, value in report["candidate_reports"].items()
            },
            "schema": (
                "guala.audit.full_field_hierarchical_summary.v1"
            ),
            "source_disjoint_speaker_count": (
                report["source_disjoint_speaker_count"]
            ),
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
