"""Controlled distinctions over complete W1 action-vocal lesson fields.

Each alternative is the complete ordered assembly of dynamic non-auditory
roots from an action outcome.  The assembly is never reduced to one root,
coordinate, action name, or scalar fingerprint authority; every root remains
present in the authenticated record.  The fingerprint is only the record's
content identity.

Every physical alternative requires two source-disjoint lesson episodes.
Its vocal diagnostic is the exact intersection of all positive left/right q
cells minus the union of every contrast cell.  Empty diagnostics remain
unresolved.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    W1ActionVocalLesson,
    W1ActionVocalLessonAuthority,
)
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1DiagnosticCell,
)


W1_ACTION_VOCAL_DISTINCTION_PROFILE_SCHEMA = (
    "guala.w1.action_vocal_distinction.profile.v1"
)
W1_ACTION_VOCAL_DISTINCTION_SCHEMA = (
    "guala.w1.action_vocal_distinction.v1"
)
_DISTINCTION_DOMAIN = b"guala-w1-action-vocal-distinction-v1\0"
_HEX = frozenset("0123456789abcdef")
_MINIMUM_POSITIVE_LESSONS = 2


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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 action-vocal distinction key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 action-vocal distinction key changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class W1ActionVocalDistinctionResourceProfile:
    profile_id: str
    max_distinctions: int
    max_lessons_per_distinction: int
    max_alternatives_per_distinction: int
    max_roots_per_alternative: int
    max_diagnostic_cells_per_alternative: int
    max_distinction_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_distinctions: int,
        max_lessons_per_distinction: int,
        max_alternatives_per_distinction: int,
        max_roots_per_alternative: int,
        max_diagnostic_cells_per_alternative: int,
        max_distinction_bytes: int,
    ) -> "W1ActionVocalDistinctionResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("W1 action-vocal profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_distinctions=_positive(
                max_distinctions, "W1 distinction capacity"
            ),
            max_lessons_per_distinction=_positive(
                max_lessons_per_distinction,
                "W1 distinction lesson capacity",
            ),
            max_alternatives_per_distinction=_positive(
                max_alternatives_per_distinction,
                "W1 distinction alternative capacity",
            ),
            max_roots_per_alternative=_positive(
                max_roots_per_alternative,
                "W1 distinction root capacity",
            ),
            max_diagnostic_cells_per_alternative=_positive(
                max_diagnostic_cells_per_alternative,
                "W1 distinction diagnostic capacity",
            ),
            max_distinction_bytes=_positive(
                max_distinction_bytes,
                "W1 distinction byte capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_distinctions=provisional.max_distinctions,
            max_lessons_per_distinction=(
                provisional.max_lessons_per_distinction
            ),
            max_alternatives_per_distinction=(
                provisional.max_alternatives_per_distinction
            ),
            max_roots_per_alternative=(
                provisional.max_roots_per_alternative
            ),
            max_diagnostic_cells_per_alternative=(
                provisional.max_diagnostic_cells_per_alternative
            ),
            max_distinction_bytes=provisional.max_distinction_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_alternatives_per_distinction": (
                self.max_alternatives_per_distinction
            ),
            "max_diagnostic_cells_per_alternative": (
                self.max_diagnostic_cells_per_alternative
            ),
            "max_distinction_bytes": self.max_distinction_bytes,
            "max_distinctions": self.max_distinctions,
            "max_lessons_per_distinction": (
                self.max_lessons_per_distinction
            ),
            "max_roots_per_alternative": (
                self.max_roots_per_alternative
            ),
            "profile_id": self.profile_id,
            "schema": W1_ACTION_VOCAL_DISTINCTION_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_distinctions, "W1 distinction capacity"),
            (
                self.max_lessons_per_distinction,
                "W1 distinction lesson capacity",
            ),
            (
                self.max_alternatives_per_distinction,
                "W1 distinction alternative capacity",
            ),
            (
                self.max_roots_per_alternative,
                "W1 distinction root capacity",
            ),
            (
                self.max_diagnostic_cells_per_alternative,
                "W1 distinction diagnostic capacity",
            ),
            (
                self.max_distinction_bytes,
                "W1 distinction byte capacity",
            ),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 action-vocal profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 action-vocal profile authority changed")


@dataclass(frozen=True, slots=True)
class W1ActionFieldAlternative:
    action_roots: tuple[GroundingRoot, ...]
    diagnostic_vocal_cells: tuple[W1DiagnosticCell, ...]
    positive_lesson_receipt_sha256s: tuple[str, ...]

    @property
    def action_field_identity(self) -> str:
        return _digest({
            "complete_dynamic_action_roots": [
                [value.root_id, value.value_sha256]
                for value in self.action_roots
            ]
        })

    @property
    def resolved(self) -> bool:
        return bool(self.diagnostic_vocal_cells)

    def record(self) -> dict[str, object]:
        return {
            "action_field_identity": self.action_field_identity,
            "action_roots": [
                value.as_record() for value in self.action_roots
            ],
            "diagnostic_vocal_cells": [
                value.record()
                for value in self.diagnostic_vocal_cells
            ],
            "positive_lesson_receipt_sha256s": list(
                self.positive_lesson_receipt_sha256s
            ),
        }


@dataclass(frozen=True, slots=True)
class W1ActionVocalDistinction:
    distinction_id: str
    controlled_before_world_state_sha256: str
    alternatives: tuple[W1ActionFieldAlternative, ...]
    source_lesson_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "alternatives": [
                value.record() for value in self.alternatives
            ],
            "controlled_before_world_state_sha256": (
                self.controlled_before_world_state_sha256
            ),
            "schema": W1_ACTION_VOCAL_DISTINCTION_SCHEMA,
            "source_lesson_receipt_sha256s": list(
                self.source_lesson_receipt_sha256s
            ),
        }


class W1ActionVocalDistinctionOwner:
    """Bounded exact contrast owner for physical lesson assemblies."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ActionVocalDistinctionResourceProfile,
        lesson_authority: W1ActionVocalLessonAuthority,
    ) -> None:
        resource_profile.verify()
        if not isinstance(
            lesson_authority, W1ActionVocalLessonAuthority
        ):
            raise TypeError("W1 distinction requires lesson authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._distinction_key = hashlib.sha256(
            _DISTINCTION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._lesson_authority = lesson_authority
        self._distinctions: dict[
            str, W1ActionVocalDistinction
        ] = {}
        self._lock = threading.RLock()

    def _verify_alternative(
        self,
        alternative: W1ActionFieldAlternative,
    ) -> None:
        if (
            not alternative.action_roots
            or len(alternative.action_roots)
            > self._profile.max_roots_per_alternative
            or tuple(
                root.root_id for root in alternative.action_roots
            ) != tuple(sorted(set(
                root.root_id for root in alternative.action_roots
            )))
            or alternative.diagnostic_vocal_cells
            != tuple(sorted(set(
                alternative.diagnostic_vocal_cells
            )))
            or len(alternative.diagnostic_vocal_cells)
            > self._profile.max_diagnostic_cells_per_alternative
            or len(alternative.positive_lesson_receipt_sha256s)
            < _MINIMUM_POSITIVE_LESSONS
            or alternative.positive_lesson_receipt_sha256s
            != tuple(sorted(set(
                alternative.positive_lesson_receipt_sha256s
            )))
        ):
            raise ValueError("W1 action-field alternative changed")
        for root in alternative.action_roots:
            root.verify()
        for cell in alternative.diagnostic_vocal_cells:
            cell.verify()
        for receipt in alternative.positive_lesson_receipt_sha256s:
            _sha256(receipt, "W1 positive lesson")

    def verify(
        self,
        distinction: W1ActionVocalDistinction,
    ) -> None:
        if not isinstance(distinction, W1ActionVocalDistinction):
            raise TypeError("W1 action-vocal distinction is not typed")
        for value, name in (
            (distinction.distinction_id, "W1 action-vocal distinction"),
            (
                distinction.controlled_before_world_state_sha256,
                "W1 controlled world before",
            ),
            (
                distinction.authority_hmac_sha256,
                "W1 action-vocal distinction HMAC",
            ),
            (
                distinction.authority_receipt_sha256,
                "W1 action-vocal distinction authority",
            ),
        ):
            _sha256(value, name)
        if (
            not 2
            <= len(distinction.alternatives)
            <= self._profile.max_alternatives_per_distinction
            or distinction.alternatives
            != tuple(sorted(
                distinction.alternatives,
                key=lambda value: value.action_field_identity,
            ))
            or distinction.source_lesson_receipt_sha256s
            != tuple(sorted(set(
                distinction.source_lesson_receipt_sha256s
            )))
            or len(distinction.source_lesson_receipt_sha256s)
            > self._profile.max_lessons_per_distinction
        ):
            raise ValueError("W1 action-vocal distinction changed")
        used_lessons: set[str] = set()
        used_cells: set[W1DiagnosticCell] = set()
        for alternative in distinction.alternatives:
            self._verify_alternative(alternative)
            if (
                used_lessons.intersection(
                    alternative.positive_lesson_receipt_sha256s
                )
                or used_cells.intersection(
                    alternative.diagnostic_vocal_cells
                )
            ):
                raise ValueError(
                    "W1 action-vocal alternatives overlap"
                )
            used_lessons.update(
                alternative.positive_lesson_receipt_sha256s
            )
            used_cells.update(alternative.diagnostic_vocal_cells)
        if used_lessons != set(
            distinction.source_lesson_receipt_sha256s
        ):
            raise ValueError("W1 distinction lost source lessons")
        payload = distinction.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            distinction.distinction_id != _digest(payload)
            or len(_canonical(payload))
            > self._profile.max_distinction_bytes
            or not hmac.compare_digest(
                signature, distinction.authority_hmac_sha256
            )
            or distinction.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError(
                "W1 action-vocal distinction authority changed"
            )

    def learn(
        self,
        lessons: tuple[W1ActionVocalLesson, ...],
    ) -> W1ActionVocalDistinction:
        if (
            not isinstance(lessons, tuple)
            or not lessons
            or len(lessons)
            > self._profile.max_lessons_per_distinction
        ):
            raise ValueError("W1 distinction lesson boundary changed")
        for lesson in lessons:
            self._lesson_authority.verify(lesson)
        source_receipts = tuple(sorted(
            value.authority_receipt_sha256 for value in lessons
        ))
        if len(source_receipts) != len(set(source_receipts)):
            raise ValueError(
                "W1 distinction requires source-disjoint lessons"
            )
        physical_sources = tuple(
            receipt
            for lesson in lessons
            for receipt in (
                lesson.action_execution_receipt_sha256,
                lesson.action_evidence_receipt_sha256,
                lesson.action_settlement_receipt_sha256,
                lesson.vocal_execution_receipt_sha256,
                lesson.vocal_evidence_receipt_sha256,
                lesson.vocal_grounding_receipt_sha256,
            )
        )
        if len(physical_sources) != len(set(physical_sources)):
            raise ValueError(
                "W1 distinction reuses an underlying physical source"
            )
        controlled_before = {
            lesson.action_before_world_state_sha256
            for lesson in lessons
        }
        if len(controlled_before) != 1:
            raise ValueError(
                "W1 distinction controlled world-before field changed"
            )
        controlled_before_world_state_sha256 = controlled_before.pop()
        groups: dict[str, list[W1ActionVocalLesson]] = {}
        roots_by_identity: dict[str, tuple[GroundingRoot, ...]] = {}
        for lesson in lessons:
            identity = _digest({
                "complete_dynamic_action_roots": [
                    [root.root_id, root.value_sha256]
                    for root in lesson.action_roots
                ]
            })
            groups.setdefault(identity, []).append(lesson)
            roots_by_identity[identity] = lesson.action_roots
        if (
            not 2
            <= len(groups)
            <= self._profile.max_alternatives_per_distinction
            or any(
                len(values) < _MINIMUM_POSITIVE_LESSONS
                for values in groups.values()
            )
        ):
            raise ValueError(
                "W1 distinction requires two independent lessons "
                "per complete action field"
            )
        cells_by_group = {
            identity: tuple(
                lesson.vocal_cells for lesson in group
            )
            for identity, group in groups.items()
        }
        alternatives = []
        for identity in sorted(groups):
            positives = cells_by_group[identity]
            intersection = set(positives[0])
            for cells in positives[1:]:
                intersection.intersection_update(cells)
            contrast: set[W1DiagnosticCell] = set()
            for other_identity, cell_sets in cells_by_group.items():
                if other_identity == identity:
                    continue
                for cells in cell_sets:
                    contrast.update(cells)
            diagnostic = tuple(sorted(
                intersection.difference(contrast)
            ))
            if (
                len(diagnostic)
                > self._profile.max_diagnostic_cells_per_alternative
            ):
                raise RuntimeError(
                    "W1 distinction diagnostic capacity exhausted"
                )
            alternatives.append(W1ActionFieldAlternative(
                action_roots=roots_by_identity[identity],
                diagnostic_vocal_cells=diagnostic,
                positive_lesson_receipt_sha256s=tuple(sorted(
                    lesson.authority_receipt_sha256
                    for lesson in groups[identity]
                )),
            ))
        provisional = W1ActionVocalDistinction(
            distinction_id="0" * 64,
            controlled_before_world_state_sha256=(
                controlled_before_world_state_sha256
            ),
            alternatives=tuple(alternatives),
            source_lesson_receipt_sha256s=source_receipts,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1ActionVocalDistinction(
            distinction_id=_digest(payload),
            controlled_before_world_state_sha256=(
                provisional.controlled_before_world_state_sha256
            ),
            alternatives=provisional.alternatives,
            source_lesson_receipt_sha256s=(
                provisional.source_lesson_receipt_sha256s
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        with self._lock:
            existing = self._distinctions.get(result.distinction_id)
            if existing is not None:
                return existing
            if (
                len(self._distinctions)
                >= self._profile.max_distinctions
            ):
                raise RuntimeError("W1 distinction capacity exhausted")
            self._distinctions[result.distinction_id] = result
        return result

    def resolve(
        self,
        *,
        distinction: W1ActionVocalDistinction,
        active_vocal_cells: frozenset[W1DiagnosticCell],
    ) -> tuple[W1ActionFieldAlternative, ...]:
        self.verify(distinction)
        for cell in active_vocal_cells:
            cell.verify()
        return tuple(
            alternative
            for alternative in distinction.alternatives
            if (
                alternative.diagnostic_vocal_cells
                and set(
                    alternative.diagnostic_vocal_cells
                ).issubset(active_vocal_cells)
            )
        )

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            return {
                "capacity": self._profile.max_distinctions,
                "count": len(self._distinctions),
                "resolved_alternatives": sum(
                    alternative.resolved
                    for distinction in self._distinctions.values()
                    for alternative in distinction.alternatives
                ),
                "unresolved_alternatives": sum(
                    not alternative.resolved
                    for distinction in self._distinctions.values()
                    for alternative in distinction.alternatives
                ),
            }


__all__ = [
    "W1ActionFieldAlternative",
    "W1ActionVocalDistinction",
    "W1ActionVocalDistinctionOwner",
    "W1ActionVocalDistinctionResourceProfile",
]
