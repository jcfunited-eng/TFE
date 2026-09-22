"""Full-field auditory Krimelack relation over exact causal DSF paths.

One auditory experience contains thirty-two frozen-kernel component paths:
pressure and carrier-phase advance for each of sixteen cochlear resonators.
Every ordered L4 tuple contributes all seven authoritative fields in canonical
order: D_k, M_k, R_rev_k, U_star_k, C_k, P_k, and B_k.

Each exact field contributes both its balanced relation to zero and its
balanced causal change from the immediately prior tuple: negative ``-1``,
quiescent ``0``, or positive ``+1``.  No threshold, fitted constant, label,
transcript, chi, lookup cell, or scalar score participates.
Canonical L6 is applied hierarchically:

* all seven DSF fields decide whether two local tuples lock;
* monotone one-to-one paths decide each physical component;
* the pressure bank and every contiguous lower/current/upper cochlear
  neighborhood must lock by canonical L6, preserving spectral topology;
* the phase bank must lock reciprocally because phase can be physically
  quiescent in low-pressure resonators;
* the complete thirty-two-component cochlea must also lock reciprocally.

The complete compact full-field authority is retained separately by auditory
kind memory.  This module's relation is therefore both an actual evaluation
of every explicit DSF field and a bounded structural interpretation of it,
not a receipt-only claim or reduced pressure projection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    AuditoryL4ExperienceSupport,
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.canonical_l6 import (
    L6Direction,
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)


AUDITORY_KRIMELACK_PATH_SCHEMA = "guala.auditory.krimelack_path.v5"
AUDITORY_KRIMELACK_RELATION_SCHEMA = (
    "guala.auditory.krimelack_relation.v5"
)
AUDITORY_KRIMELACK_RELATION_OPERATOR = (
    "full_dsf_state_change_component_path_reciprocal_l6_v5"
)
AUDITORY_KRIMELACK_FIELD_COUNT = 2 * len(DSF_FIELD_ORDER)
AUDITORY_KRIMELACK_PRESSURE_COMPONENTS = (
    AUDITORY_KERNEL_COMPONENT_COUNT // 2
)
AUDITORY_KRIMELACK_PHASE_COMPONENTS = (
    AUDITORY_KERNEL_COMPONENT_COUNT // 2
)
MAX_AUDITORY_KRIMELACK_FRAMES = (
    MAX_CAPTURE_SECONDS
    * REQUIRED_SAMPLE_RATE_HZ
    // OBSERVATION_HOP_SAMPLES
)
MAX_AUDITORY_KRIMELACK_WORK_CELLS = (
    AUDITORY_KERNEL_COMPONENT_COUNT
    * MAX_AUDITORY_KRIMELACK_FRAMES ** 2
)

AuditoryDSFMotif = tuple[int, ...]
AuditoryComponentPath = tuple[AuditoryDSFMotif, ...]
AuditoryComponentPaths = tuple[AuditoryComponentPath, ...]


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _l6_payload(value: L6Direction) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def _field_trit(value: Fraction) -> int:
    if not isinstance(value, Fraction):
        raise TypeError("auditory Krimelack DSF field must remain exact")
    return -1 if value < 0 else 1 if value > 0 else 0


def _verify_component_paths(component_paths: AuditoryComponentPaths) -> None:
    if (
        not isinstance(component_paths, tuple)
        or len(component_paths) != AUDITORY_KERNEL_COMPONENT_COUNT
    ):
        raise ValueError(
            "auditory Krimelack path lost a kernel component"
        )
    for path in component_paths:
        if (
            not isinstance(path, tuple)
            or not 1 <= len(path) <= MAX_AUDITORY_KRIMELACK_FRAMES
            or any(
                not isinstance(motif, tuple)
                or len(motif) != AUDITORY_KRIMELACK_FIELD_COUNT
                or any(value not in (-1, 0, 1) for value in motif)
                for motif in path
            )
        ):
            raise ValueError(
                "auditory Krimelack full-field component path changed"
            )


def _component_paths_record(
    component_paths: AuditoryComponentPaths,
) -> list[list[list[int]]]:
    return [
        [list(motif) for motif in path]
        for path in component_paths
    ]


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackPath:
    """All explicit DSF paths for one verified auditory L5 experience."""

    experience_id: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    l4_causal_support_receipt_sha256: str
    component_paths: AuditoryComponentPaths
    committed_trits: int
    authority_receipt_sha256: str

    @property
    def component_count(self) -> int:
        return len(self.component_paths)

    @property
    def tuple_count(self) -> int:
        return sum(len(path) for path in self.component_paths)

    def payload(self) -> bytes:
        return _canonical_bytes({
            "committed_trits": self.committed_trits,
            "component_paths": _component_paths_record(
                self.component_paths
            ),
            "experience_id": self.experience_id,
            "field_order": list(DSF_FIELD_ORDER),
            "field_relation_order": [
                [relation, name]
                for relation in ("state", "causal_change")
                for name in DSF_FIELD_ORDER
            ],
            "l4_causal_support_receipt_sha256": (
                self.l4_causal_support_receipt_sha256
            ),
            "l5_authority_receipt_sha256": (
                self.l5_authority_receipt_sha256
            ),
            "schema": AUDITORY_KRIMELACK_PATH_SCHEMA,
            "structural_fingerprint": self.structural_fingerprint,
        })

    def verify(self, experience: AuditoryL5Experience) -> None:
        support = mount_auditory_l4_causal_support(experience)
        self.verify_with_support(experience, support)

    def verify_with_support(
        self,
        experience: AuditoryL5Experience,
        support: AuditoryL4ExperienceSupport,
    ) -> None:
        if not isinstance(experience, AuditoryL5Experience):
            raise TypeError(
                "auditory Krimelack path requires auditory L5"
            )
        if not isinstance(support, AuditoryL4ExperienceSupport):
            raise TypeError(
                "auditory Krimelack path requires exact causal support"
        )
        experience.verify()
        support.verify(experience)
        self._verify_mounted_authorities(experience, support)

    def _verify_mounted_authorities(
        self,
        experience: AuditoryL5Experience,
        support: AuditoryL4ExperienceSupport,
    ) -> None:
        self._verify_fresh_mounted_authorities(experience, support)
        if _mount_path(experience, support) != self:
            raise ValueError(
                "auditory Krimelack path left its complete L0-L4 field"
            )

    def _verify_fresh_mounted_authorities(
        self,
        experience: AuditoryL5Experience,
        support: AuditoryL4ExperienceSupport,
    ) -> None:
        """Verify a path returned directly by ``_mount_path``.

        The fresh constructor has already traversed every support tuple to
        create ``component_paths``.  Re-running that same constructor is not
        an independent authority check; it only repeats the complete field
        traversal.  External or restored paths continue through
        ``_verify_mounted_authorities`` and are independently remounted.
        """
        _verify_component_paths(self.component_paths)
        if (
            self.experience_id != experience.experience_id
            or self.structural_fingerprint
            != experience.structural_fingerprint
            or self.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or self.committed_trits
            != self.tuple_count * AUDITORY_KRIMELACK_FIELD_COUNT
            or receipt_sha256(self.payload())
            != self.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory Krimelack path differs from its authority"
            )
        if (
            self.l4_causal_support_receipt_sha256
            != support.integrity_receipt_sha256
        ):
            raise ValueError(
                "auditory Krimelack path left its complete L0-L4 field"
            )


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackRelation:
    """Label-free reciprocal relation across the complete auditory field."""

    left_path_receipt_sha256: str
    right_path_receipt_sha256: str
    matching_non_null: int
    pressure_matching_non_null: int
    phase_matching_non_null: int
    pressure_neighborhoods_locked: bool
    work_cells: int
    left_l6: L6Direction
    right_l6: L6Direction
    left_pressure_l6: L6Direction
    right_pressure_l6: L6Direction
    left_phase_l6: L6Direction
    right_phase_l6: L6Direction
    structurally_locked: bool
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return _canonical_bytes({
            "left_l6": _l6_payload(self.left_l6),
            "left_path_receipt_sha256": (
                self.left_path_receipt_sha256
            ),
            "left_phase_l6": _l6_payload(self.left_phase_l6),
            "left_pressure_l6": _l6_payload(
                self.left_pressure_l6
            ),
            "matching_locked_components": self.matching_non_null,
            "operator": AUDITORY_KRIMELACK_RELATION_OPERATOR,
            "phase_matching_locked_components": (
                self.phase_matching_non_null
            ),
            "pressure_matching_locked_components": (
                self.pressure_matching_non_null
            ),
            "pressure_neighborhoods_locked": (
                self.pressure_neighborhoods_locked
            ),
            "right_l6": _l6_payload(self.right_l6),
            "right_path_receipt_sha256": (
                self.right_path_receipt_sha256
            ),
            "right_phase_l6": _l6_payload(self.right_phase_l6),
            "right_pressure_l6": _l6_payload(
                self.right_pressure_l6
            ),
            "schema": AUDITORY_KRIMELACK_RELATION_SCHEMA,
            "structurally_locked": self.structurally_locked,
            "work_cells": self.work_cells,
        })

    def verify(
        self,
        left: AuditoryKrimelackPath,
        right: AuditoryKrimelackPath,
    ) -> None:
        if (
            self.left_path_receipt_sha256
            != left.authority_receipt_sha256
            or self.right_path_receipt_sha256
            != right.authority_receipt_sha256
            or receipt_sha256(self.payload())
            != self.authority_receipt_sha256
            or relate_auditory_krimelack_paths(left, right) != self
        ):
            raise ValueError(
                "auditory Krimelack relation differs from causal paths"
            )


def _mount_component_paths(
    support: AuditoryL4ExperienceSupport,
) -> AuditoryComponentPaths:
    if len(support.components) != AUDITORY_KERNEL_COMPONENT_COUNT:
        raise ValueError(
            "auditory Krimelack support lost a kernel component"
        )
    mounted = []
    for component in support.components:
        component_path = []
        prior_values = None
        for field_tuple in component.tuples:
            values = tuple(
                value for _name, value in field_tuple.fields
            )
            component_path.append(
                tuple(_field_trit(value) for value in values)
                + tuple(
                    0
                    if prior_values is None
                    else _field_trit(value - prior_value)
                    for value, prior_value in zip(
                        values,
                        (
                            values
                            if prior_values is None
                            else prior_values
                        ),
                        strict=True,
                    )
                )
            )
            prior_values = values
        mounted.append(tuple(component_path))
    result = tuple(mounted)
    if any(
        tuple(name for name, _value in field_tuple.fields)
        != DSF_FIELD_ORDER
        for component in support.components
        for field_tuple in component.tuples
    ):
        raise ValueError(
            "auditory Krimelack support changed DSF field order"
        )
    _verify_component_paths(result)
    return result


def _mount_path(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> AuditoryKrimelackPath:
    component_paths = _mount_component_paths(support)
    provisional = AuditoryKrimelackPath(
        experience_id=experience.experience_id,
        structural_fingerprint=experience.structural_fingerprint,
        l5_authority_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        l4_causal_support_receipt_sha256=(
            support.integrity_receipt_sha256
        ),
        component_paths=component_paths,
        committed_trits=(
            sum(len(path) for path in component_paths)
            * AUDITORY_KRIMELACK_FIELD_COUNT
        ),
        authority_receipt_sha256="",
    )
    return AuditoryKrimelackPath(
        experience_id=provisional.experience_id,
        structural_fingerprint=provisional.structural_fingerprint,
        l5_authority_receipt_sha256=(
            provisional.l5_authority_receipt_sha256
        ),
        l4_causal_support_receipt_sha256=(
            provisional.l4_causal_support_receipt_sha256
        ),
        component_paths=provisional.component_paths,
        committed_trits=provisional.committed_trits,
        authority_receipt_sha256=receipt_sha256(
            provisional.payload()
        ),
            )


def mount_auditory_krimelack_path_from_support(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> AuditoryKrimelackPath:
    """Mount one path from the already verified exact L4 support."""

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "auditory Krimelack requires an auditory L5 experience"
        )
    if not isinstance(support, AuditoryL4ExperienceSupport):
        raise TypeError(
            "auditory Krimelack requires exact causal support"
        )
    experience.verify()
    support.verify(experience)
    result = _mount_path(experience, support)
    result.verify_with_support(experience, support)
    return result


def _mount_auditory_krimelack_path_from_verified_support(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> AuditoryKrimelackPath:
    """Mount and verify path inside the one-shot L5 constructor."""

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "verified auditory Krimelack path requires auditory L5"
        )
    if not isinstance(support, AuditoryL4ExperienceSupport):
        raise TypeError(
            "verified auditory Krimelack path requires exact support"
        )
    result = _mount_path(experience, support)
    result._verify_fresh_mounted_authorities(experience, support)
    return result


def mount_auditory_krimelack_path(
    experience: AuditoryL5Experience,
) -> AuditoryKrimelackPath:
    """Evaluate every exact auditory L4 field as a causal ternary path."""

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "auditory Krimelack requires an auditory L5 experience"
        )
    experience.verify()
    support = mount_auditory_l4_causal_support(experience)
    return mount_auditory_krimelack_path_from_support(
        experience,
        support,
    )


def _motif_locks(
    left: AuditoryDSFMotif,
    right: AuditoryDSFMotif,
) -> bool:
    if (
        len(left) != AUDITORY_KRIMELACK_FIELD_COUNT
        or len(right) != AUDITORY_KRIMELACK_FIELD_COUNT
    ):
        raise ValueError("auditory Krimelack DSF motif width changed")
    matching_non_null = sum(
        left_value == right_value and left_value != 0
        for left_value, right_value in zip(left, right, strict=True)
    )
    matching_quiescent = sum(
        left_value == right_value == 0
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_l6 = canonical_l6_direction(
        dimensions=len(left),
        matching_non_null=matching_non_null,
        matching_quiescent=matching_quiescent,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(right),
        matching_non_null=matching_non_null,
        matching_quiescent=matching_quiescent,
    )
    return left_l6.locked and right_l6.locked


def _matching_locked_motifs(
    left: AuditoryComponentPath,
    right: AuditoryComponentPath,
) -> int:
    """Maximum monotone one-to-one sequence of full-DSF tuple locks."""

    local_cache: dict[
        tuple[AuditoryDSFMotif, AuditoryDSFMotif],
        bool,
    ] = {}
    prior = [0] * (len(right) + 1)
    for left_motif in left:
        current = [0]
        for right_index, right_motif in enumerate(right, 1):
            key = (left_motif, right_motif)
            locked = local_cache.get(key)
            if locked is None:
                locked = _motif_locks(left_motif, right_motif)
                local_cache[key] = locked
            current.append(max(
                prior[right_index],
                current[-1],
                prior[right_index - 1] + int(locked),
            ))
        prior = current
    return prior[-1]


def _component_locks(
    left: AuditoryComponentPath,
    right: AuditoryComponentPath,
) -> tuple[bool, int]:
    matching = _matching_locked_motifs(left, right)
    locked = (
        canonical_l6_direction(
            dimensions=len(left),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
        and canonical_l6_direction(
            dimensions=len(right),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
    )
    return locked, len(left) * len(right)


@dataclass(frozen=True, slots=True)
class _ComponentPathRelation:
    component_locks: tuple[bool, ...]
    matching: int
    pressure_matching: int
    phase_matching: int
    pressure_neighborhoods_locked: bool
    work_cells: int
    left_l6: L6Direction
    right_l6: L6Direction
    left_pressure_l6: L6Direction
    right_pressure_l6: L6Direction
    left_phase_l6: L6Direction
    right_phase_l6: L6Direction
    locked: bool


def _relation_from_component_locks(
    locks: tuple[bool, ...],
    *,
    work_cells: int,
) -> _ComponentPathRelation:
    if (
        len(locks) != AUDITORY_KERNEL_COMPONENT_COUNT
        or not all(isinstance(value, bool) for value in locks)
        or not 0 <= work_cells <= MAX_AUDITORY_KRIMELACK_WORK_CELLS
    ):
        raise ValueError(
            "auditory Krimelack component relation boundary changed"
        )
    matching = sum(locks)
    pressure_locks = locks[0::2]
    phase_locks = locks[1::2]
    pressure_matching = sum(pressure_locks)
    phase_matching = sum(phase_locks)
    pressure_neighborhoods_locked = all(
        canonical_l6_direction(
            dimensions=3,
            matching_non_null=sum(
                pressure_locks[index:index + 3]
            ),
            matching_quiescent=0,
        ).locked
        for index in range(len(pressure_locks) - 2)
    )
    left_l6 = canonical_l6_direction(
        dimensions=len(locks),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(locks),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    left_pressure_l6 = canonical_l6_direction(
        dimensions=AUDITORY_KRIMELACK_PRESSURE_COMPONENTS,
        matching_non_null=pressure_matching,
        matching_quiescent=0,
    )
    right_pressure_l6 = canonical_l6_direction(
        dimensions=AUDITORY_KRIMELACK_PRESSURE_COMPONENTS,
        matching_non_null=pressure_matching,
        matching_quiescent=0,
    )
    left_phase_l6 = canonical_l6_direction(
        dimensions=AUDITORY_KRIMELACK_PHASE_COMPONENTS,
        matching_non_null=phase_matching,
        matching_quiescent=0,
    )
    right_phase_l6 = canonical_l6_direction(
        dimensions=AUDITORY_KRIMELACK_PHASE_COMPONENTS,
        matching_non_null=phase_matching,
        matching_quiescent=0,
    )
    return _ComponentPathRelation(
        component_locks=locks,
        matching=matching,
        pressure_matching=pressure_matching,
        phase_matching=phase_matching,
        pressure_neighborhoods_locked=(
            pressure_neighborhoods_locked
        ),
        work_cells=work_cells,
        left_l6=left_l6,
        right_l6=right_l6,
        left_pressure_l6=left_pressure_l6,
        right_pressure_l6=right_pressure_l6,
        left_phase_l6=left_phase_l6,
        right_phase_l6=right_phase_l6,
        locked=(
            left_l6.locked
            and right_l6.locked
            and left_pressure_l6.locked
            and right_pressure_l6.locked
            and pressure_neighborhoods_locked
            and left_phase_l6.locked
            and right_phase_l6.locked
        ),
    )


def _component_paths_relation(
    left: AuditoryComponentPaths,
    right: AuditoryComponentPaths,
) -> _ComponentPathRelation:
    _verify_component_paths(left)
    _verify_component_paths(right)
    component_results = tuple(
        _component_locks(left_path, right_path)
        for left_path, right_path in zip(left, right, strict=True)
    )
    work_cells = sum(work for _locked, work in component_results)
    if work_cells > MAX_AUDITORY_KRIMELACK_WORK_CELLS:
        raise ValueError(
            "auditory Krimelack relation exceeds its work boundary"
        )
    return _relation_from_component_locks(
        tuple(locked for locked, _work in component_results),
        work_cells=work_cells,
    )


def relate_auditory_krimelack_paths(
    left: AuditoryKrimelackPath,
    right: AuditoryKrimelackPath,
) -> AuditoryKrimelackRelation:
    """Apply reciprocal L6 to every DSF tuple and physical component."""

    if not isinstance(left, AuditoryKrimelackPath) or not isinstance(
        right,
        AuditoryKrimelackPath,
    ):
        raise TypeError(
            "auditory Krimelack relation requires typed paths"
        )
    for value, name in (
        (left.authority_receipt_sha256, "left auditory path receipt"),
        (right.authority_receipt_sha256, "right auditory path receipt"),
    ):
        sha256_digest(value, name)
    evidence = _component_paths_relation(
        left.component_paths,
        right.component_paths,
    )
    provisional = AuditoryKrimelackRelation(
        left_path_receipt_sha256=left.authority_receipt_sha256,
        right_path_receipt_sha256=right.authority_receipt_sha256,
        matching_non_null=evidence.matching,
        pressure_matching_non_null=evidence.pressure_matching,
        phase_matching_non_null=evidence.phase_matching,
        pressure_neighborhoods_locked=(
            evidence.pressure_neighborhoods_locked
        ),
        work_cells=evidence.work_cells,
        left_l6=evidence.left_l6,
        right_l6=evidence.right_l6,
        left_pressure_l6=evidence.left_pressure_l6,
        right_pressure_l6=evidence.right_pressure_l6,
        left_phase_l6=evidence.left_phase_l6,
        right_phase_l6=evidence.right_phase_l6,
        structurally_locked=evidence.locked,
        authority_receipt_sha256="",
    )
    return AuditoryKrimelackRelation(
        left_path_receipt_sha256=(
            provisional.left_path_receipt_sha256
        ),
        right_path_receipt_sha256=(
            provisional.right_path_receipt_sha256
        ),
        matching_non_null=provisional.matching_non_null,
        pressure_matching_non_null=(
            provisional.pressure_matching_non_null
        ),
        phase_matching_non_null=provisional.phase_matching_non_null,
        pressure_neighborhoods_locked=(
            provisional.pressure_neighborhoods_locked
        ),
        work_cells=provisional.work_cells,
        left_l6=provisional.left_l6,
        right_l6=provisional.right_l6,
        left_pressure_l6=provisional.left_pressure_l6,
        right_pressure_l6=provisional.right_pressure_l6,
        left_phase_l6=provisional.left_phase_l6,
        right_phase_l6=provisional.right_phase_l6,
        structurally_locked=provisional.structurally_locked,
        authority_receipt_sha256=receipt_sha256(
            provisional.payload()
        ),
    )


__all__ = (
    "AUDITORY_KRIMELACK_FIELD_COUNT",
    "AUDITORY_KRIMELACK_PATH_SCHEMA",
    "AUDITORY_KRIMELACK_RELATION_OPERATOR",
    "AUDITORY_KRIMELACK_RELATION_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_FRAMES",
    "MAX_AUDITORY_KRIMELACK_WORK_CELLS",
    "AuditoryComponentPath",
    "AuditoryComponentPaths",
    "AuditoryDSFMotif",
    "AuditoryKrimelackPath",
    "AuditoryKrimelackRelation",
    "_component_paths_relation",
    "_relation_from_component_locks",
    "_matching_locked_motifs",
    "_mount_auditory_krimelack_path_from_verified_support",
    "mount_auditory_krimelack_path",
    "mount_auditory_krimelack_path_from_support",
    "relate_auditory_krimelack_paths",
)
