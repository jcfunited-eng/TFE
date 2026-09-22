"""Bounded experience-grown auditory kinds with tutor designation.

Structural kind membership is decided only by the balanced hierarchical
Krimelack relation.  Tutor text may designate an already observed kind, but it
cannot make unrelated paths equivalent, split a locked kind, participate in
recall, or become sensory identity.

Every retained exemplar contains both its causal co-firing path and a compact,
lossless authority for every explicit L0--L4 DSF field and causal interval.
The owner has fixed kind, exemplar, work, and encoded-state boundaries.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    AUDITORY_KRIMELACK_FIELD_COUNT,
    AUDITORY_KRIMELACK_PATH_SCHEMA,
    AuditoryKrimelackPath,
    _mount_auditory_krimelack_path_from_verified_support,
    mount_auditory_krimelack_path,
    relate_auditory_krimelack_paths,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    AuditoryL4ExperienceSupport,
    _mount_auditory_l4_causal_support_from_verified_l5,
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryVerifiedSettlementCapability,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
    canonical_tutor_label,
)
from dsf_ai_service.substrate.compact_auditory_field_authority import (
    CompactAuditoryFieldAuthority,
    _prepare_compact_auditory_field_from_verified_l5,
    compact_auditory_field_from_l5,
    decode_compact_auditory_field,
)
AUDITORY_KRIMELACK_MEMORY_SCHEMA = "guala.auditory.krimelack_memory.v1"
AUDITORY_KRIMELACK_KIND_SCHEMA = "guala.auditory.krimelack_kind.v1"
AUDITORY_KRIMELACK_RECOGNITION_SCHEMA = (
    "guala.auditory.krimelack_recognition.v1"
)
AUDITORY_KRIMELACK_KIND_DOMAIN = b"guala.auditory.krimelack_kind.v1\0"
MAX_AUDITORY_KRIMELACK_KINDS = 64
MAX_AUDITORY_KRIMELACK_EXEMPLARS_PER_KIND = 4
MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS = 4_000_000
MAX_AUDITORY_KRIMELACK_MEMORY_BYTES = 64 * 1024 * 1024
_LIVE_PREPARATION_AUTHORITY = object()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _path_record(path: AuditoryKrimelackPath) -> dict[str, object]:
    return {
        "authority_receipt_sha256": path.authority_receipt_sha256,
        "committed_trits": path.committed_trits,
        "component_paths": [
            [list(motif) for motif in component_path]
            for component_path in path.component_paths
        ],
        "experience_id": path.experience_id,
        "l4_causal_support_receipt_sha256": (
            path.l4_causal_support_receipt_sha256
        ),
        "l5_authority_receipt_sha256": (
            path.l5_authority_receipt_sha256
        ),
        "schema": AUDITORY_KRIMELACK_PATH_SCHEMA,
        "structural_fingerprint": path.structural_fingerprint,
    }


def _path_from_record(value: object) -> AuditoryKrimelackPath:
    if not isinstance(value, Mapping) or value.get("schema") != (
        AUDITORY_KRIMELACK_PATH_SCHEMA
    ):
        raise ValueError("auditory Krimelack stored path schema changed")
    try:
        path = AuditoryKrimelackPath(
            experience_id=value["experience_id"],
            structural_fingerprint=value["structural_fingerprint"],
            l5_authority_receipt_sha256=(
                value["l5_authority_receipt_sha256"]
            ),
            l4_causal_support_receipt_sha256=(
                value["l4_causal_support_receipt_sha256"]
            ),
            component_paths=tuple(
                tuple(
                    tuple(motif) for motif in component_path
                )
                for component_path in value["component_paths"]
            ),
            committed_trits=value["committed_trits"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )
    except (KeyError, TypeError) as error:
        raise ValueError(
            "auditory Krimelack stored path is malformed"
        ) from error
    _verify_stored_path(path)
    return path


def _verify_stored_path(path: AuditoryKrimelackPath) -> None:
    if not isinstance(path, AuditoryKrimelackPath):
        raise TypeError("auditory kind exemplar path is not typed")
    for digest, name in (
        (path.experience_id, "experience"),
        (path.structural_fingerprint, "structural fingerprint"),
        (path.l5_authority_receipt_sha256, "L5 authority"),
        (path.l4_causal_support_receipt_sha256, "L4 support"),
        (path.authority_receipt_sha256, "path authority"),
    ):
        sha256_digest(digest, f"auditory kind {name}")
    if (
        path.component_count != 32
        or any(
            not component_path
            or any(
                len(motif) != AUDITORY_KRIMELACK_FIELD_COUNT
                or any(value not in (-1, 0, 1) for value in motif)
                for motif in component_path
            )
            for component_path in path.component_paths
        )
        or path.committed_trits
        != path.tuple_count * AUDITORY_KRIMELACK_FIELD_COUNT
        or receipt_sha256(path.payload()) != path.authority_receipt_sha256
    ):
        raise ValueError("auditory kind stored path authority changed")


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackExemplar:
    path: AuditoryKrimelackPath
    full_dsf_authority: CompactAuditoryFieldAuthority

    def verify(self) -> None:
        _verify_stored_path(self.path)
        self.full_dsf_authority.verify()
        if (
            self.full_dsf_authority.experience_id
            != self.path.experience_id
            or self.full_dsf_authority.source_field_authority_receipt_sha256
            != self.path.l5_authority_receipt_sha256
        ):
            raise ValueError(
                "auditory kind exemplar left its full DSF authority"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            "full_dsf_authority_base64": base64.b64encode(
                self.full_dsf_authority.encoded()
            ).decode("ascii"),
            "path": _path_record(self.path),
        }

    @classmethod
    def from_record(cls, value: object) -> "AuditoryKrimelackExemplar":
        if not isinstance(value, Mapping):
            raise ValueError("auditory kind exemplar record changed")
        encoded = value.get("full_dsf_authority_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("auditory kind full DSF authority is absent")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except Exception as error:
            raise ValueError(
                "auditory kind full DSF authority is unreadable"
            ) from error
        if base64.b64encode(decoded).decode("ascii") != encoded:
            raise ValueError(
                "auditory kind full DSF authority is not canonical"
            )
        result = cls(
            path=_path_from_record(value.get("path")),
            full_dsf_authority=decode_compact_auditory_field(decoded),
        )
        result.verify()
        return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackPreparedExemplar:
    """One deeply verified immutable live artifact with constant-size reuse."""

    exemplar: AuditoryKrimelackExemplar
    full_dsf_encoded_bytes: int
    l5_authority_receipt_sha256: str
    verification_receipt_sha256: str
    _construction_authority: object

    def verify_linkage(self, experience: AuditoryL5Experience) -> None:
        if not isinstance(experience, AuditoryL5Experience):
            raise TypeError(
                "prepared auditory exemplar requires auditory L5"
            )
        if (
            self._construction_authority
            is not _LIVE_PREPARATION_AUTHORITY
            or not isinstance(self.exemplar, AuditoryKrimelackExemplar)
            or isinstance(self.full_dsf_encoded_bytes, bool)
            or not isinstance(self.full_dsf_encoded_bytes, int)
            or self.full_dsf_encoded_bytes <= 0
        ):
            raise ValueError(
                "prepared auditory exemplar construction changed"
            )
        path = self.exemplar.path
        full_dsf = self.exemplar.full_dsf_authority
        for value, name in (
            (
                self.l5_authority_receipt_sha256,
                "prepared L5 authority",
            ),
            (path.authority_receipt_sha256, "prepared path"),
            (
                full_dsf.authority_receipt_sha256,
                "prepared full DSF",
            ),
            (
                self.verification_receipt_sha256,
                "prepared verification",
            ),
        ):
            sha256_digest(value, name)
        if (
            self.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or path.experience_id != experience.experience_id
            or path.structural_fingerprint
            != experience.structural_fingerprint
            or path.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or full_dsf.experience_id != experience.experience_id
            or full_dsf.source_field_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or self.verification_receipt_sha256
            != _digest({
                "experience_id": experience.experience_id,
                "full_dsf_receipt_sha256": (
                    full_dsf.authority_receipt_sha256
                ),
                "full_dsf_encoded_bytes": self.full_dsf_encoded_bytes,
                "l4_support_receipt_sha256": (
                    path.l4_causal_support_receipt_sha256
                ),
                "l5_authority_receipt_sha256": (
                    experience.authority_receipt_sha256
                ),
                "path_receipt_sha256": path.authority_receipt_sha256,
                "schema": (
                    "guala.auditory.krimelack_prepared_exemplar.v1"
                ),
            })
        ):
            raise ValueError(
                "prepared auditory exemplar left its verified authority"
            )


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackPreparedPath:
    """Verified full-field path without a mounted compact DSF authority."""

    path: AuditoryKrimelackPath
    support: AuditoryL4ExperienceSupport
    encoded_bytes: int
    l5_authority_receipt_sha256: str
    verification_receipt_sha256: str
    _construction_authority: object

    def verify_linkage(self, experience: AuditoryL5Experience) -> None:
        if not isinstance(experience, AuditoryL5Experience):
            raise TypeError(
                "prepared auditory path requires auditory L5"
            )
        if (
            self._construction_authority
            is not _LIVE_PREPARATION_AUTHORITY
            or not isinstance(self.path, AuditoryKrimelackPath)
            or not isinstance(
                self.support,
                AuditoryL4ExperienceSupport,
            )
            or isinstance(self.encoded_bytes, bool)
            or not isinstance(self.encoded_bytes, int)
            or self.encoded_bytes <= 0
        ):
            raise ValueError(
                "prepared auditory path construction changed"
            )
        if (
            self.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or self.path.experience_id != experience.experience_id
            or self.path.structural_fingerprint
            != experience.structural_fingerprint
            or self.path.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or self.path.l4_causal_support_receipt_sha256
            != self.support.integrity_receipt_sha256
            or self.support.experience_id != experience.experience_id
            or self.support.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or self.verification_receipt_sha256
            != _digest({
                "encoded_bytes": self.encoded_bytes,
                "experience_id": experience.experience_id,
                "l4_support_receipt_sha256": (
                    self.support.integrity_receipt_sha256
                ),
                "l5_authority_receipt_sha256": (
                    experience.authority_receipt_sha256
                ),
                "path_receipt_sha256": (
                    self.path.authority_receipt_sha256
                ),
                "schema": (
                    "guala.auditory.krimelack_prepared_path.v1"
                ),
            })
        ):
            raise ValueError(
                "prepared auditory path left its verified authority"
            )


def prepare_auditory_krimelack_path(
    experience: AuditoryL5Experience,
    *,
    verified_capability: (
        AuditoryVerifiedSettlementCapability | None
    ) = None,
    joint_settlement: (
        AuditoryStreamSettlementReceipt | None
    ) = None,
) -> AuditoryKrimelackPreparedPath:
    """Evaluate every explicit DSF field without mounting compact evidence."""

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "auditory Krimelack path requires auditory L5"
        )
    if verified_capability is None:
        if joint_settlement is not None:
            raise ValueError(
                "joint settlement requires verified auditory capability"
            )
        experience.verify()
    else:
        if not isinstance(
            verified_capability,
            AuditoryVerifiedSettlementCapability,
        ):
            raise TypeError(
                "Krimelack path preparation requires verified capability"
            )
        if not isinstance(
            joint_settlement,
            AuditoryStreamSettlementReceipt,
        ):
            raise TypeError(
                "Krimelack path capability requires joint settlement"
            )
        verified_capability.verify_linkage(
            pcm_s16le=verified_capability.pcm_s16le,
            capture=verified_capability.capture,
            auditory_l5=experience,
            transport=verified_capability.transport,
            cochlear=verified_capability.cochlear,
            causal_settlement=(
                verified_capability.causal_settlement
            ),
            joint_settlement=joint_settlement,
        )
    support = _mount_auditory_l4_causal_support_from_verified_l5(
        experience
    )
    path = _mount_auditory_krimelack_path_from_verified_support(
        experience,
        support,
    )
    encoded_bytes = (
        len(support.payload())
        + sum(len(component.payload()) for component in support.components)
        + sum(
            len(field_tuple.payload())
            for component in support.components
            for field_tuple in component.tuples
        )
        + len(_canonical(_path_record(path)))
    )
    result = AuditoryKrimelackPreparedPath(
        path=path,
        support=support,
        encoded_bytes=encoded_bytes,
        l5_authority_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        verification_receipt_sha256=_digest({
            "encoded_bytes": encoded_bytes,
            "experience_id": experience.experience_id,
            "l4_support_receipt_sha256": (
                support.integrity_receipt_sha256
            ),
            "l5_authority_receipt_sha256": (
                experience.authority_receipt_sha256
            ),
            "path_receipt_sha256": path.authority_receipt_sha256,
            "schema": (
                "guala.auditory.krimelack_prepared_path.v1"
            ),
        }),
        _construction_authority=_LIVE_PREPARATION_AUTHORITY,
    )
    result.verify_linkage(experience)
    return result


def finalize_auditory_krimelack_exemplar(
    experience: AuditoryL5Experience,
    prepared_path: AuditoryKrimelackPreparedPath,
) -> AuditoryKrimelackPreparedExemplar:
    """Mount and verify lossless compact authority for a selected path."""

    if not isinstance(
        prepared_path,
        AuditoryKrimelackPreparedPath,
    ):
        raise TypeError(
            "auditory Krimelack finalization requires prepared path"
        )
    prepared_path.verify_linkage(experience)
    full_dsf, full_dsf_encoded_bytes = (
        _prepare_compact_auditory_field_from_verified_l5(
            experience,
            prepared_path.support,
        )
    )
    exemplar = AuditoryKrimelackExemplar(
        path=prepared_path.path,
        full_dsf_authority=full_dsf,
    )
    result = AuditoryKrimelackPreparedExemplar(
        exemplar=exemplar,
        full_dsf_encoded_bytes=full_dsf_encoded_bytes,
        l5_authority_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        verification_receipt_sha256=_digest({
            "experience_id": experience.experience_id,
            "full_dsf_receipt_sha256": (
                full_dsf.authority_receipt_sha256
            ),
            "full_dsf_encoded_bytes": full_dsf_encoded_bytes,
            "l4_support_receipt_sha256": (
                prepared_path.support.integrity_receipt_sha256
            ),
            "l5_authority_receipt_sha256": (
                experience.authority_receipt_sha256
            ),
            "path_receipt_sha256": (
                prepared_path.path.authority_receipt_sha256
            ),
            "schema": (
                "guala.auditory.krimelack_prepared_exemplar.v1"
            ),
        }),
        _construction_authority=_LIVE_PREPARATION_AUTHORITY,
    )
    result.verify_linkage(experience)
    return result


def prepare_auditory_krimelack_exemplar(
    experience: AuditoryL5Experience,
    *,
    verified_capability: (
        AuditoryVerifiedSettlementCapability | None
    ) = None,
    joint_settlement: (
        AuditoryStreamSettlementReceipt | None
    ) = None,
) -> AuditoryKrimelackPreparedExemplar:
    """Mount one immutable path/full-DSF authority for live consumers."""
    prepared_path = prepare_auditory_krimelack_path(
        experience,
        verified_capability=verified_capability,
        joint_settlement=joint_settlement,
    )
    return finalize_auditory_krimelack_exemplar(
        experience,
        prepared_path,
    )


def _kind_id(path: AuditoryKrimelackPath) -> str:
    return hashlib.sha256(
        AUDITORY_KRIMELACK_KIND_DOMAIN
        + bytes.fromhex(path.authority_receipt_sha256)
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackKind:
    kind_id: str
    tutor_label: str
    exemplars: tuple[AuditoryKrimelackExemplar, ...]
    reinforcement_count: int
    first_experience_id: str
    last_experience_id: str
    tutor_authority_receipts: tuple[dict[str, object], ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "exemplar_path_receipts": [
                value.path.authority_receipt_sha256
                for value in self.exemplars
            ],
            "first_experience_id": self.first_experience_id,
            "kind_id": self.kind_id,
            "last_experience_id": self.last_experience_id,
            "reinforcement_count": self.reinforcement_count,
            "schema": AUDITORY_KRIMELACK_KIND_SCHEMA,
            "tutor_authority_receipt_count": len(
                self.tutor_authority_receipts
            ),
            "tutor_label": self.tutor_label,
        }

    def verify(self) -> None:
        sha256_digest(self.kind_id, "auditory Krimelack kind")
        sha256_digest(
            self.first_experience_id,
            "auditory kind first experience",
        )
        sha256_digest(
            self.last_experience_id,
            "auditory kind last experience",
        )
        if (
            canonical_tutor_label(self.tutor_label) != self.tutor_label
            or not 1
            <= len(self.exemplars)
            <= MAX_AUDITORY_KRIMELACK_EXEMPLARS_PER_KIND
            or isinstance(self.reinforcement_count, bool)
            or not isinstance(self.reinforcement_count, int)
            or self.reinforcement_count < len(self.exemplars)
            or self.kind_id != _kind_id(self.exemplars[0].path)
            or self.first_experience_id
            != self.exemplars[0].path.experience_id
            or self.last_experience_id
            not in {
                value.path.experience_id for value in self.exemplars
            }
            or len({
                value.path.authority_receipt_sha256
                for value in self.exemplars
            }) != len(self.exemplars)
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError("auditory Krimelack kind authority changed")
        for exemplar in self.exemplars:
            exemplar.verify()


class AuditoryKrimelackRecognitionState(str, Enum):
    UNKNOWN = "unknown"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE_RESOURCE = "indeterminate_resource"


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackRecognition:
    state: AuditoryKrimelackRecognitionState
    experience_id: str
    candidate_kind_ids: tuple[str, ...]
    candidate_labels: tuple[str, ...]
    selected_kind_id: str | None
    tutor_label: str | None
    work_cells: int
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_kind_ids": list(self.candidate_kind_ids),
            "candidate_labels": list(self.candidate_labels),
            "experience_id": self.experience_id,
            "operator": "auditory_hierarchical_reciprocal_l6_v1",
            "schema": AUDITORY_KRIMELACK_RECOGNITION_SCHEMA,
            "selected_kind_id": self.selected_kind_id,
            "state": self.state.value,
            "tutor_label": self.tutor_label,
            "work_cells": self.work_cells,
        }

    def verify(self) -> None:
        sha256_digest(self.experience_id, "auditory recognition experience")
        if (
            tuple(sorted(self.candidate_kind_ids))
            != self.candidate_kind_ids
            or len(self.candidate_kind_ids) != len(self.candidate_labels)
            or self.state is AuditoryKrimelackRecognitionState.UNKNOWN
            and self.candidate_kind_ids
            or self.state is AuditoryKrimelackRecognitionState.UNIQUE
            and (
                len(self.candidate_kind_ids) != 1
                or self.selected_kind_id != self.candidate_kind_ids[0]
                or self.tutor_label != self.candidate_labels[0]
            )
            or self.state
            is AuditoryKrimelackRecognitionState.AMBIGUOUS
            and (
                len(self.candidate_kind_ids) < 2
                or self.selected_kind_id is not None
                or self.tutor_label is not None
            )
            or self.state
            is AuditoryKrimelackRecognitionState.INDETERMINATE_RESOURCE
            and (
                self.candidate_kind_ids
                or self.selected_kind_id is not None
                or self.tutor_label is not None
            )
            or not 0 <= self.work_cells
            <= MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError("auditory Krimelack recognition changed")


class AuditoryKrimelackMemoryOwner:
    """Serial bounded owner of label-independent auditory kinds."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        max_kinds: int = MAX_AUDITORY_KRIMELACK_KINDS,
        max_exemplars_per_kind: int = (
            MAX_AUDITORY_KRIMELACK_EXEMPLARS_PER_KIND
        ),
        max_work_cells: int = (
            MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS
        ),
        max_encoded_bytes: int = MAX_AUDITORY_KRIMELACK_MEMORY_BYTES,
        tutor_authority: AuditoryTutorAuthority | None = None,
    ) -> None:
        if (
            isinstance(max_kinds, bool)
            or not isinstance(max_kinds, int)
            or not 1 <= max_kinds <= MAX_AUDITORY_KRIMELACK_KINDS
            or isinstance(max_exemplars_per_kind, bool)
            or not isinstance(max_exemplars_per_kind, int)
            or not 1
            <= max_exemplars_per_kind
            <= MAX_AUDITORY_KRIMELACK_EXEMPLARS_PER_KIND
            or isinstance(max_work_cells, bool)
            or not isinstance(max_work_cells, int)
            or not 1
            <= max_work_cells
            <= MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS
            or isinstance(max_encoded_bytes, bool)
            or not isinstance(max_encoded_bytes, int)
            or not 1 <= max_encoded_bytes <= MAX_AUDITORY_KRIMELACK_MEMORY_BYTES
        ):
            raise ValueError("auditory Krimelack memory boundary is invalid")
        self._log_event = log_event
        self._max_kinds = max_kinds
        self._max_exemplars = max_exemplars_per_kind
        self._max_work = max_work_cells
        self._max_encoded = max_encoded_bytes
        self._tutor_authority = (
            tutor_authority
            if tutor_authority is not None
            else AuditoryTutorAuthority.from_environment()
        )
        self._lock = threading.RLock()
        self._kinds: dict[str, AuditoryKrimelackKind] = {}
        self._encoded_bytes = len(self._encoded_for(self._kinds))
        self._accepted_nonces: set[str] = set()
        self._resource_exhaustions = 0

    def issue_tutor_authority(
        self,
        *,
        experience_id: str,
        tutor_label: str,
    ) -> dict[str, object] | None:
        if not self._tutor_authority.required:
            return None
        return self._tutor_authority.issue(
            experience_id=experience_id,
            kind="spoken_form",
            tutor_label=tutor_label,
        ).as_dict()

    @staticmethod
    def _exemplar(
        experience: AuditoryL5Experience,
    ) -> AuditoryKrimelackExemplar:
        return prepare_auditory_krimelack_exemplar(
            experience
        ).exemplar

    def _required_work(
        self,
        query: AuditoryKrimelackPath,
    ) -> int:
        return sum(
            sum(
                len(query_component) * len(exemplar_component)
                for query_component, exemplar_component in zip(
                    query.component_paths,
                    exemplar.path.component_paths,
                    strict=True,
                )
            )
            for kind in self._kinds.values()
            for exemplar in kind.exemplars
        )

    def _related_kinds(
        self,
        query: AuditoryKrimelackPath,
    ) -> tuple[AuditoryKrimelackKind, ...]:
        return tuple(
            kind
            for kind in self._kinds.values()
            if any(
                relate_auditory_krimelack_paths(
                    query,
                    exemplar.path,
                ).structurally_locked
                for exemplar in kind.exemplars
            )
        )

    def _snapshot_for(
        self,
        kinds: Mapping[str, AuditoryKrimelackKind],
    ) -> dict[str, object]:
        return {
            "kind_capacity": self._max_kinds,
            "kinds": [
                {
                    "authority_receipt_sha256": (
                        kind.authority_receipt_sha256
                    ),
                    "exemplars": [
                        value.record() for value in kind.exemplars
                    ],
                    "first_experience_id": kind.first_experience_id,
                    "kind_id": kind.kind_id,
                    "last_experience_id": kind.last_experience_id,
                    "reinforcement_count": kind.reinforcement_count,
                    "schema": AUDITORY_KRIMELACK_KIND_SCHEMA,
                    "tutor_authority_receipts": list(
                        kind.tutor_authority_receipts
                    ),
                    "tutor_label": kind.tutor_label,
                }
                for kind in sorted(
                    kinds.values(),
                    key=lambda item: item.kind_id,
                )
            ],
            "max_encoded_bytes": self._max_encoded,
            "max_exemplars_per_kind": self._max_exemplars,
            "max_work_cells": self._max_work,
            "schema": AUDITORY_KRIMELACK_MEMORY_SCHEMA,
            "tutor_authority_required": self._tutor_authority.required,
        }

    def _encoded_for(
        self,
        kinds: Mapping[str, AuditoryKrimelackKind],
    ) -> bytes:
        encoded = _canonical(self._snapshot_for(kinds))
        if len(encoded) > self._max_encoded:
            raise RuntimeError(
                "auditory Krimelack memory encoded capacity is full"
            )
        return encoded

    def teach(
        self,
        experience: AuditoryL5Experience,
        *,
        tutor_label: str,
        authority_receipt: object | None = None,
    ) -> AuditoryKrimelackKind:
        experience.verify()
        if experience.event_boundary != "utterance":
            raise ValueError(
                "auditory Krimelack tutoring requires an utterance"
            )
        label = canonical_tutor_label(tutor_label)
        mounted_authority = None
        if authority_receipt is None:
            if self._tutor_authority.required:
                raise RuntimeError(
                    "auditory tutoring requires authenticated authority"
                )
        elif not self._tutor_authority.required:
            raise ValueError(
                "unrequired auditory owner rejects authority receipts"
            )
        else:
            mounted_authority = self._tutor_authority.verify(
                authority_receipt,
                experience_id=experience.experience_id,
                kind="spoken_form",
                tutor_label=label,
            )
        exemplar = self._exemplar(experience)
        with self._lock:
            if (
                mounted_authority is not None
                and mounted_authority.nonce in self._accepted_nonces
            ):
                raise RuntimeError(
                    "auditory tutor authority nonce was already used"
                )
            required = self._required_work(exemplar.path)
            if required > self._max_work:
                raise RuntimeError(
                    "auditory kind relation work capacity is full"
                )
            related = self._related_kinds(exemplar.path)
            if len(related) > 1:
                raise RuntimeError(
                    "auditory tutor experience relates to multiple kinds"
                )
            labels = {
                kind.tutor_label for kind in self._kinds.values()
            }
            if not related:
                if label in labels:
                    raise ValueError(
                        "tutor label cannot merge unrelated auditory kinds"
                    )
                if len(self._kinds) >= self._max_kinds:
                    raise RuntimeError(
                        "auditory Krimelack kind capacity is full"
                    )
                exemplars = (exemplar,)
                kind_id = _kind_id(exemplar.path)
                reinforcement = 1
                first = exemplar.path.experience_id
            else:
                prior = related[0]
                if prior.tutor_label != label:
                    raise ValueError(
                        "tutor label cannot split one auditory kind"
                    )
                repeated = next((
                    value
                    for value in prior.exemplars
                    if value.path.authority_receipt_sha256
                    == exemplar.path.authority_receipt_sha256
                ), None)
                if repeated is None and len(prior.exemplars) >= (
                    self._max_exemplars
                ):
                    raise RuntimeError(
                        "auditory Krimelack exemplar capacity is full"
                    )
                exemplars = (
                    prior.exemplars
                    if repeated is not None
                    else (*prior.exemplars, exemplar)
                )
                kind_id = prior.kind_id
                reinforcement = prior.reinforcement_count + 1
                first = prior.first_experience_id
            authority_values = (
                ()
                if mounted_authority is None
                else (mounted_authority.as_dict(),)
            )
            if related:
                authority_values = (
                    *related[0].tutor_authority_receipts,
                    *authority_values,
                )
            provisional = AuditoryKrimelackKind(
                kind_id=kind_id,
                tutor_label=label,
                exemplars=exemplars,
                reinforcement_count=reinforcement,
                first_experience_id=first,
                last_experience_id=exemplar.path.experience_id,
                tutor_authority_receipts=authority_values,
                authority_receipt_sha256="",
            )
            learned = AuditoryKrimelackKind(
                kind_id=provisional.kind_id,
                tutor_label=provisional.tutor_label,
                exemplars=provisional.exemplars,
                reinforcement_count=provisional.reinforcement_count,
                first_experience_id=provisional.first_experience_id,
                last_experience_id=provisional.last_experience_id,
                tutor_authority_receipts=(
                    provisional.tutor_authority_receipts
                ),
                authority_receipt_sha256=_digest(
                    provisional.payload()
                ),
            )
            learned.verify()
            prospective = dict(self._kinds)
            prospective[learned.kind_id] = learned
            encoded = self._encoded_for(prospective)
            self._kinds = prospective
            self._encoded_bytes = len(encoded)
            if mounted_authority is not None:
                self._accepted_nonces.add(mounted_authority.nonce)
        self._log_event(
            "auditory_krimelack_kind_taught",
            exemplar_count=len(learned.exemplars),
            experience_id=experience.experience_id,
            kind_id=learned.kind_id,
            reinforcement_count=learned.reinforcement_count,
        )
        return learned

    def recognize(
        self,
        experience: AuditoryL5Experience,
    ) -> AuditoryKrimelackRecognition:
        query = mount_auditory_krimelack_path(experience)
        with self._lock:
            work = self._required_work(query)
            if work > self._max_work:
                state = (
                    AuditoryKrimelackRecognitionState
                    .INDETERMINATE_RESOURCE
                )
                matched: tuple[AuditoryKrimelackKind, ...] = ()
                admitted_work = 0
                self._resource_exhaustions += 1
            else:
                matched = tuple(sorted(
                    self._related_kinds(query),
                    key=lambda item: item.kind_id,
                ))
                admitted_work = work
                state = (
                    AuditoryKrimelackRecognitionState.UNKNOWN
                    if not matched
                    else AuditoryKrimelackRecognitionState.UNIQUE
                    if len(matched) == 1
                    else AuditoryKrimelackRecognitionState.AMBIGUOUS
                )
        kind_ids = tuple(value.kind_id for value in matched)
        labels = tuple(value.tutor_label for value in matched)
        selected = kind_ids[0] if state is (
            AuditoryKrimelackRecognitionState.UNIQUE
        ) else None
        label = labels[0] if state is (
            AuditoryKrimelackRecognitionState.UNIQUE
        ) else None
        provisional = AuditoryKrimelackRecognition(
            state=state,
            experience_id=experience.experience_id,
            candidate_kind_ids=kind_ids,
            candidate_labels=labels,
            selected_kind_id=selected,
            tutor_label=label,
            work_cells=admitted_work,
            authority_receipt_sha256="",
        )
        result = AuditoryKrimelackRecognition(
            state=provisional.state,
            experience_id=provisional.experience_id,
            candidate_kind_ids=provisional.candidate_kind_ids,
            candidate_labels=provisional.candidate_labels,
            selected_kind_id=provisional.selected_kind_id,
            tutor_label=provisional.tutor_label,
            work_cells=provisional.work_cells,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        return result

    def encoded_snapshot(self) -> dict[str, str]:
        with self._lock:
            payload = self._encoded_for(self._kinds)
        return {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    def restore_encoded(self, envelope: object) -> None:
        if not isinstance(envelope, Mapping) or set(envelope) != {
            "payload_base64",
            "sha256",
        }:
            raise ValueError("auditory Krimelack memory envelope changed")
        text = envelope.get("payload_base64")
        digest = envelope.get("sha256")
        if not isinstance(text, str) or not isinstance(digest, str):
            raise ValueError("auditory Krimelack memory envelope changed")
        try:
            payload = base64.b64decode(text, validate=True)
            snapshot = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "auditory Krimelack memory is unreadable"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest() != digest
            or len(payload) > self._max_encoded
            or not isinstance(snapshot, Mapping)
            or snapshot.get("schema") != AUDITORY_KRIMELACK_MEMORY_SCHEMA
            or snapshot.get("kind_capacity") != self._max_kinds
            or snapshot.get("max_exemplars_per_kind")
            != self._max_exemplars
            or snapshot.get("max_work_cells") != self._max_work
            or snapshot.get("max_encoded_bytes") != self._max_encoded
            or snapshot.get("tutor_authority_required")
            is not self._tutor_authority.required
            or not isinstance(snapshot.get("kinds"), list)
            or len(snapshot["kinds"]) > self._max_kinds
        ):
            raise ValueError(
                "auditory Krimelack memory boundary changed"
            )
        restored: dict[str, AuditoryKrimelackKind] = {}
        nonces: set[str] = set()
        for record in snapshot["kinds"]:
            if not isinstance(record, Mapping):
                raise ValueError("auditory Krimelack kind record changed")
            exemplars = tuple(
                AuditoryKrimelackExemplar.from_record(value)
                for value in record.get("exemplars", ())
            )
            receipts = tuple(record.get("tutor_authority_receipts", ()))
            kind = AuditoryKrimelackKind(
                kind_id=record.get("kind_id"),
                tutor_label=record.get("tutor_label"),
                exemplars=exemplars,
                reinforcement_count=record.get("reinforcement_count"),
                first_experience_id=record.get("first_experience_id"),
                last_experience_id=record.get("last_experience_id"),
                tutor_authority_receipts=receipts,
                authority_receipt_sha256=record.get(
                    "authority_receipt_sha256"
                ),
            )
            kind.verify()
            if kind.kind_id in restored:
                raise ValueError("auditory Krimelack kind is duplicated")
            if any(
                value.tutor_label == kind.tutor_label
                for value in restored.values()
            ):
                raise ValueError(
                    "auditory tutor label spans unrelated kinds"
                )
            for receipt in receipts:
                mounted = self._tutor_authority.verify(
                    receipt,
                    experience_id=receipt.get("experience_id"),
                    kind="spoken_form",
                    tutor_label=kind.tutor_label,
                )
                if mounted.nonce in nonces:
                    raise ValueError(
                        "auditory tutor authority nonce is duplicated"
                    )
                nonces.add(mounted.nonce)
            restored[kind.kind_id] = kind
        if _canonical(snapshot) != payload:
            raise ValueError(
                "auditory Krimelack memory is not canonical"
            )
        encoded = self._encoded_for(restored)
        if encoded != payload:
            raise ValueError(
                "auditory Krimelack memory encoded authority changed"
            )
        with self._lock:
            self._kinds = restored
            self._encoded_bytes = len(encoded)
            self._accepted_nonces = nonces

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "encoded_bytes": self._encoded_bytes,
                "encoded_snapshot_capacity_bytes": self._max_encoded,
                "exemplar_count": sum(
                    len(value.exemplars)
                    for value in self._kinds.values()
                ),
                "kind_count": len(self._kinds),
                "resource_exhaustions": self._resource_exhaustions,
                "schema": "guala.auditory.krimelack_memory.status.v1",
                "tutor_authority_nonce_count": len(
                    self._accepted_nonces
                ),
                "tutor_authority_required": (
                    self._tutor_authority.required
                ),
            }


__all__ = (
    "AUDITORY_KRIMELACK_MEMORY_SCHEMA",
    "AUDITORY_KRIMELACK_RECOGNITION_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_EXEMPLARS_PER_KIND",
    "MAX_AUDITORY_KRIMELACK_KINDS",
    "MAX_AUDITORY_KRIMELACK_MEMORY_BYTES",
    "MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS",
    "AuditoryKrimelackExemplar",
    "AuditoryKrimelackKind",
    "AuditoryKrimelackMemoryOwner",
    "AuditoryKrimelackPreparedExemplar",
    "AuditoryKrimelackPreparedPath",
    "AuditoryKrimelackRecognition",
    "AuditoryKrimelackRecognitionState",
    "finalize_auditory_krimelack_exemplar",
    "prepare_auditory_krimelack_exemplar",
    "prepare_auditory_krimelack_path",
)
