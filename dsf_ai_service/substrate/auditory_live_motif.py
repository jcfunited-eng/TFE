"""Production boundary for exact presemantic auditory motif hearing.

This module serializes live motif outcomes without assigning words, kinds,
labels, speaker identity, or meaning.  It also authenticates the bounded,
canonical state owned by :class:`AuditoryRecurrentMotifOwner`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifActivation,
    AuditoryMotifFiring,
    AuditoryMotifObservationState,
    AuditoryMotifObservation,
    AuditoryReceptorExperience,
    AuditoryRecurrentMotifOwner,
    AuditoryVerifiedReceptorExperienceCapability,
    migrate_immediately_prior_motif_profile,
)


AUDITORY_LIVE_MOTIF_RESULT_SCHEMA = (
    "guala.auditory.live_recurrent_motif_result.v2"
)
AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA = (
    "guala.auditory.live_recurrent_motif_state.hmac.v1"
)
AUDITORY_LIVE_MOTIF_PERSISTENCE_DOMAIN = (
    b"guala-auditory-live-recurrent-motif-state-v1\0"
)
# Operational byte authorities are deliberately below the adversarial
# all-cells/all-max-Fraction derivation.  Exhaustion is typed before mutation.
# This prevents authenticated JSON/base64 persistence from producing multi-GB
# transient copies while preserving every admitted exact witness.
AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES = 64 * 1024 * 1024
AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES = 128 * 1024 * 1024
# Compatibility name is the browser-mono authority only.
AUDITORY_LIVE_MOTIF_STATE_ALLOCATION_BYTES = (
    AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES
)
AUDITORY_LIVE_MOTIF_ENVELOPE_MAX_BYTES = (
    4 * ((AUDITORY_LIVE_MOTIF_STATE_ALLOCATION_BYTES + 2) // 3)
    + 1_024
)
AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES = (
    4
    * (
        (
            AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
            + 2
        )
        // 3
    )
    + 1_024
)
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, bytes):
        result = value
    else:
        raise TypeError("auditory motif persistence key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("auditory motif persistence key left its boundary")
    return result


def _fraction_text(value) -> str:
    return f"{value.numerator}/{value.denominator}"


def _verified_fraction_text(value: object, name: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an exact fraction")
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} must be an exact fraction") from exc
    if _fraction_text(fraction) != value:
        raise ValueError(f"{name} exact fraction changed")
    return fraction


def _activation_payload(value) -> dict[str, object]:
    occurrence_receipts = tuple(
        occurrence.authority_receipt_sha256
        for occurrence in value.full_field_occurrences
    )
    return {
        "full_field_occurrence_count": len(occurrence_receipts),
        "full_field_occurrence_receipt_root_sha256": hashlib.sha256(
            _canonical({
                "ordered_full_field_occurrence_receipt_sha256s": list(
                    occurrence_receipts
                ),
                "schema": "guala.auditory.activation_support_root.v1",
            })
        ).hexdigest(),
        "motif_neuron_id": value.neuron_id,
        "segment_index": value.segment_index,
        "source_index_end": value.source_index_end,
        "source_index_start": value.source_index_start,
        "source_time_end": _fraction_text(value.source_time_end),
        "source_time_start": _fraction_text(value.source_time_start),
        "state_ordinal_end": value.state_ordinal_end,
        "state_ordinal_start": value.state_ordinal_start,
    }


@dataclass(frozen=True, slots=True)
class AuditoryLiveMotifResult:
    source_receptor_event_receipt_sha256: str
    source_experience_receipt_sha256: str
    firing_state: str
    learning_state: str
    firing_motif_neuron_ids: tuple[str, ...]
    learning_firing_motif_neuron_ids: tuple[str, ...]
    newly_grown_motif_neuron_ids: tuple[str, ...]
    reinforced_motif_neuron_ids: tuple[str, ...]
    unresolved_source_indices: tuple[int, ...]
    firing_work_cells: int
    learning_work_cells: int
    firing_reason: str
    learning_reason: str
    activation_spans: tuple[dict[str, object], ...]
    internal_activations: tuple[AuditoryMotifActivation, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "activation_spans": list(self.activation_spans),
            "firing_motif_neuron_ids": list(
                self.firing_motif_neuron_ids
            ),
            "firing_reason": self.firing_reason,
            "firing_state": self.firing_state,
            "firing_work_cells": self.firing_work_cells,
            "learning_firing_motif_neuron_ids": list(
                self.learning_firing_motif_neuron_ids
            ),
            "learning_reason": self.learning_reason,
            "learning_state": self.learning_state,
            "learning_work_cells": self.learning_work_cells,
            "newly_grown_motif_neuron_ids": list(
                self.newly_grown_motif_neuron_ids
            ),
            "reinforced_motif_neuron_ids": list(
                self.reinforced_motif_neuron_ids
            ),
            "schema": AUDITORY_LIVE_MOTIF_RESULT_SCHEMA,
            "source_experience_receipt_sha256": (
                self.source_experience_receipt_sha256
            ),
            "source_receptor_event_receipt_sha256": (
                self.source_receptor_event_receipt_sha256
            ),
            "unresolved_source_indices": list(
                self.unresolved_source_indices
            ),
        }

    def verify(self) -> None:
        _sha256(
            self.source_receptor_event_receipt_sha256,
            "source receptor event",
        )
        _sha256(
            self.source_experience_receipt_sha256,
            "source receptor experience",
        )
        for values, name in (
            (self.firing_motif_neuron_ids, "firing motif neuron"),
            (
                self.learning_firing_motif_neuron_ids,
                "learning firing motif neuron",
            ),
            (
                self.newly_grown_motif_neuron_ids,
                "newly grown motif neuron",
            ),
            (
                self.reinforced_motif_neuron_ids,
                "reinforced motif neuron",
            ),
        ):
            if not isinstance(values, tuple) or tuple(sorted(set(values))) != values:
                raise ValueError(f"{name} identities changed")
            for value in values:
                _sha256(value, name)
        if (
            not isinstance(self.firing_state, str)
            or not self.firing_state
            or not isinstance(self.learning_state, str)
            or not self.learning_state
            or not isinstance(self.unresolved_source_indices, tuple)
            or tuple(sorted(set(self.unresolved_source_indices)))
            != self.unresolved_source_indices
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in self.unresolved_source_indices
            )
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in (
                    self.firing_work_cells,
                    self.learning_work_cells,
                )
            )
            or not isinstance(self.firing_reason, str)
            or not isinstance(self.learning_reason, str)
            or not isinstance(self.activation_spans, tuple)
        ):
            raise ValueError("auditory live motif result changed")
        for span in self.activation_spans:
            expected_keys = {
                "full_field_occurrence_count",
                "full_field_occurrence_receipt_root_sha256",
                "motif_neuron_id",
                "segment_index",
                "source_index_end",
                "source_index_start",
                "source_time_end",
                "source_time_start",
                "state_ordinal_end",
                "state_ordinal_start",
            }
            if not isinstance(span, dict) or set(span) != expected_keys:
                raise ValueError("auditory motif activation span changed")
            _sha256(span.get("motif_neuron_id"), "activation motif neuron")
            _sha256(
                span.get("full_field_occurrence_receipt_root_sha256"),
                "activation full-field occurrence root",
            )
            occurrence_count = span.get("full_field_occurrence_count")
            segment_index = span.get("segment_index")
            source_index_start = span.get("source_index_start")
            source_index_end = span.get("source_index_end")
            state_ordinal_start = span.get("state_ordinal_start")
            state_ordinal_end = span.get("state_ordinal_end")
            if (
                any(
                    isinstance(value, bool) or not isinstance(value, int)
                    for value in (
                        occurrence_count,
                        segment_index,
                        source_index_start,
                        source_index_end,
                        state_ordinal_start,
                        state_ordinal_end,
                    )
                )
                or occurrence_count <= 0
                or segment_index < 0
                or source_index_start < 0
                or source_index_end < source_index_start
                or state_ordinal_start < 0
                or state_ordinal_end <= state_ordinal_start
            ):
                raise ValueError(
                    "auditory motif activation ordinals changed"
                )
            source_time_start = _verified_fraction_text(
                span.get("source_time_start"),
                "activation source time start",
            )
            source_time_end = _verified_fraction_text(
                span.get("source_time_end"),
                "activation source time end",
            )
            if source_time_start < 0 or source_time_end <= source_time_start:
                raise ValueError(
                    "auditory motif activation causal interval changed"
                )
        if (
            not isinstance(self.internal_activations, tuple)
            or len(self.internal_activations) != len(self.activation_spans)
            or tuple(
                _activation_payload(value)
                for value in self.internal_activations
            )
            != self.activation_spans
        ):
            raise ValueError(
                "auditory motif activation support root changed"
            )
        _sha256(self.authority_receipt_sha256, "live motif result")
        if (
            hashlib.sha256(_canonical(self.payload())).hexdigest()
            != self.authority_receipt_sha256
        ):
            raise ValueError("auditory live motif result receipt changed")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


_VERIFIED_LIVE_MOTIF_RESULT_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class AuditoryVerifiedLiveMotifResultCapability:
    """Request-local custody after one complete result audit."""

    _result: AuditoryLiveMotifResult
    _canonical_payload: bytes
    _construction_authority: object

    def as_record(
        self,
        result: AuditoryLiveMotifResult,
    ) -> dict[str, object]:
        if (
            self._construction_authority
            is not _VERIFIED_LIVE_MOTIF_RESULT_AUTHORITY
            or self._result is not result
            or hashlib.sha256(self._canonical_payload).hexdigest()
            != result.authority_receipt_sha256
        ):
            raise ValueError("live motif result left verified custody")
        payload = json.loads(self._canonical_payload)
        if not isinstance(payload, dict):
            raise ValueError("live motif canonical payload changed")
        payload["authority_receipt_sha256"] = (
            result.authority_receipt_sha256
        )
        return payload


_COMPACT_LIVE_MOTIF_CONSTRUCTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class AuditoryLiveMotifCompactReceipt:
    """Authenticated q receipt; full activation expansion stays off ingress."""

    record: dict[str, object]
    source_receptor_event_receipt_sha256: str
    source_experience_receipt_sha256: str
    _canonical_record: bytes
    _construction_authority: object

    @property
    def firing_state(self) -> str:
        return self.record["firing_state"]

    @property
    def learning_state(self) -> str:
        return self.record["learning_state"]

    @property
    def authority_receipt_sha256(self) -> str:
        return self.record["authority_receipt_sha256"]

    def verify(self) -> None:
        if (
            self._construction_authority
            is not _COMPACT_LIVE_MOTIF_CONSTRUCTION_AUTHORITY
            or not isinstance(self._canonical_record, bytes)
            or not isinstance(self.record, dict)
            or _canonical(self.record) != self._canonical_record
        ):
            raise ValueError("auditory compact q receipt changed")
        authority = self.record.get("authority_receipt_sha256")
        expected_record_keys = {
            "activation_spans",
            "authority_receipt_sha256",
            "firing_motif_neuron_ids",
            "firing_reason",
            "firing_state",
            "firing_work_cells",
            "learning_firing_motif_neuron_ids",
            "learning_reason",
            "learning_state",
            "learning_work_cells",
            "newly_grown_motif_neuron_ids",
            "reinforced_motif_neuron_ids",
            "schema",
            "source_experience_receipt_sha256",
            "source_receptor_event_receipt_sha256",
            "unresolved_source_indices",
        }
        payload = {
            key: value
            for key, value in self.record.items()
            if key != "authority_receipt_sha256"
        }
        if (
            set(self.record) != expected_record_keys
            or payload.get("schema") != AUDITORY_LIVE_MOTIF_RESULT_SCHEMA
            or payload.get("source_receptor_event_receipt_sha256")
            != self.source_receptor_event_receipt_sha256
            or payload.get("source_experience_receipt_sha256")
            != self.source_experience_receipt_sha256
            or hashlib.sha256(_canonical(payload)).hexdigest() != authority
        ):
            raise ValueError("auditory compact q receipt linkage changed")
        spans = payload.get("activation_spans")
        if not isinstance(spans, list):
            raise ValueError("auditory compact q spans changed")
        for span in spans:
            if (
                not isinstance(span, dict)
                or set(span) != {
                    "full_field_occurrence_count",
                    "full_field_occurrence_receipt_root_sha256",
                    "motif_neuron_id",
                    "segment_index",
                    "source_index_end",
                    "source_index_start",
                    "source_time_end",
                    "source_time_start",
                    "state_ordinal_end",
                    "state_ordinal_start",
                }
            ):
                raise ValueError("auditory compact q span changed")
            _sha256(span["motif_neuron_id"], "compact motif neuron")
            _sha256(
                span["full_field_occurrence_receipt_root_sha256"],
                "compact occurrence root",
            )
        _sha256(authority, "compact q authority")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return dict(self.record)

    def as_record_from_custody(self) -> dict[str, object]:
        """Return the once-audited q record without repeating its full walk."""

        if (
            self._construction_authority
            is not _COMPACT_LIVE_MOTIF_CONSTRUCTION_AUTHORITY
        ):
            raise ValueError("auditory compact q receipt left custody")
        record = json.loads(self._canonical_record)
        if not isinstance(record, dict):
            raise ValueError("auditory compact q canonical record changed")
        return record

    def expand(
        self,
        *,
        experience: AuditoryReceptorExperience,
    ) -> AuditoryLiveMotifResult:
        self.verify()
        return restore_live_motif_result(
            self.record,
            experience=experience,
        )


def compact_live_motif_receipt(
    record: object,
    *,
    experience: AuditoryReceptorExperience,
) -> AuditoryLiveMotifCompactReceipt:
    if not isinstance(record, dict):
        raise ValueError("auditory compact q record changed")
    mounted_record = dict(record)
    result = AuditoryLiveMotifCompactReceipt(
        record=mounted_record,
        source_receptor_event_receipt_sha256=(
            experience.source_event_receipt_sha256
        ),
        source_experience_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        _canonical_record=_canonical(mounted_record),
        _construction_authority=(
            _COMPACT_LIVE_MOTIF_CONSTRUCTION_AUTHORITY
        ),
    )
    result.verify()
    return result


def compact_live_motif_q_receipt(
    record: object,
    *,
    source_receptor_event_receipt_sha256: str,
    source_experience_receipt_sha256: str,
) -> AuditoryLiveMotifCompactReceipt:
    """Mount a compact receipt already verified by exclusive q authority."""
    if not isinstance(record, dict):
        raise ValueError("auditory compact q record changed")
    mounted_record = dict(record)
    result = AuditoryLiveMotifCompactReceipt(
        record=mounted_record,
        source_receptor_event_receipt_sha256=_sha256(
            source_receptor_event_receipt_sha256,
            "q source receptor event",
        ),
        source_experience_receipt_sha256=_sha256(
            source_experience_receipt_sha256,
            "q source experience",
        ),
        _canonical_record=_canonical(mounted_record),
        _construction_authority=(
            _COMPACT_LIVE_MOTIF_CONSTRUCTION_AUTHORITY
        ),
    )
    result.verify()
    return result


def _build_verified_live_motif_result(
    *,
    experience: AuditoryReceptorExperience,
    firing: AuditoryMotifFiring,
    observation: AuditoryMotifObservation | None,
    learning_state: str | None = None,
    learning_reason: str | None = None,
    verified_capability: (
        AuditoryVerifiedReceptorExperienceCapability | None
    ) = None,
) -> tuple[
    AuditoryLiveMotifResult,
    AuditoryVerifiedLiveMotifResultCapability,
]:
    if verified_capability is None:
        experience.verify()
    else:
        verified_capability.verify_identity(experience)
    selected_activations = (
        observation.activations
        if observation is not None and observation.activations
        else firing.activations
    )
    provisional = AuditoryLiveMotifResult(
        source_receptor_event_receipt_sha256=(
            experience.source_event_receipt_sha256
        ),
        source_experience_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        firing_state=firing.state.value,
        learning_state=(
            observation.state.value
            if observation is not None
            else learning_state or "not_attempted"
        ),
        firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
        learning_firing_motif_neuron_ids=(
            observation.firing_motif_neuron_ids
            if observation is not None else ()
        ),
        newly_grown_motif_neuron_ids=(
            observation.newly_grown_motif_neuron_ids
            if observation is not None else ()
        ),
        reinforced_motif_neuron_ids=(
            observation.reinforced_motif_neuron_ids
            if observation is not None else ()
        ),
        unresolved_source_indices=(
            experience.unresolved_source_indices
        ),
        firing_work_cells=firing.work_cells,
        learning_work_cells=(
            observation.work_cells if observation is not None else 0
        ),
        firing_reason=firing.reason,
        learning_reason=(
            observation.reason
            if observation is not None
            else learning_reason or "learning was not attempted"
        ),
        activation_spans=tuple(
            _activation_payload(value) for value in selected_activations
        ),
        internal_activations=tuple(selected_activations),
        authority_receipt_sha256="0" * 64,
    )
    canonical_payload = _canonical(provisional.payload())
    result = AuditoryLiveMotifResult(
        **{
            field: getattr(provisional, field)
            for field in provisional.__dataclass_fields__
            if field != "authority_receipt_sha256"
        },
        authority_receipt_sha256=hashlib.sha256(
            canonical_payload
        ).hexdigest(),
    )
    result.verify()
    return result, AuditoryVerifiedLiveMotifResultCapability(
        _result=result,
        _canonical_payload=canonical_payload,
        _construction_authority=(
            _VERIFIED_LIVE_MOTIF_RESULT_AUTHORITY
        ),
    )


def build_live_motif_result(
    *,
    experience: AuditoryReceptorExperience,
    firing: AuditoryMotifFiring,
    observation: AuditoryMotifObservation | None,
    learning_state: str | None = None,
    learning_reason: str | None = None,
    verified_capability: (
        AuditoryVerifiedReceptorExperienceCapability | None
    ) = None,
) -> AuditoryLiveMotifResult:
    result, _capability = _build_verified_live_motif_result(
        experience=experience,
        firing=firing,
        observation=observation,
        learning_state=learning_state,
        learning_reason=learning_reason,
        verified_capability=verified_capability,
    )
    return result


def build_verified_live_motif_result(
    *,
    experience: AuditoryReceptorExperience,
    firing: AuditoryMotifFiring,
    observation: AuditoryMotifObservation | None,
    learning_state: str | None = None,
    learning_reason: str | None = None,
    verified_capability: (
        AuditoryVerifiedReceptorExperienceCapability | None
    ) = None,
) -> tuple[
    AuditoryLiveMotifResult,
    AuditoryVerifiedLiveMotifResultCapability,
]:
    return _build_verified_live_motif_result(
        experience=experience,
        firing=firing,
        observation=observation,
        learning_state=learning_state,
        learning_reason=learning_reason,
        verified_capability=verified_capability,
    )


def build_pending_live_motif_result(
    experience: AuditoryReceptorExperience,
    *,
    verified_capability: (
        AuditoryVerifiedReceptorExperienceCapability | None
    ) = None,
) -> AuditoryLiveMotifResult:
    """Receipt one physical interval without pretending q evaluated it."""
    if verified_capability is None:
        experience.verify()
    else:
        verified_capability.verify_identity(experience)
    provisional = AuditoryLiveMotifResult(
        source_receptor_event_receipt_sha256=(
            experience.source_event_receipt_sha256
        ),
        source_experience_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        firing_state=(
            AuditoryMotifObservationState
            .AWAITING_EXACT_WINDOW_COMPOSITION.value
        ),
        learning_state="awaiting_exact_window_composition",
        firing_motif_neuron_ids=(),
        learning_firing_motif_neuron_ids=(),
        newly_grown_motif_neuron_ids=(),
        reinforced_motif_neuron_ids=(),
        unresolved_source_indices=experience.unresolved_source_indices,
        firing_work_cells=0,
        learning_work_cells=0,
        firing_reason=(
            "q was not evaluated before the exact four-unit physical "
            "window completed"
        ),
        learning_reason=(
            "exact continued receptor interval is retained within the "
            "bounded four-unit physical window"
        ),
        activation_spans=(),
        internal_activations=(),
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryLiveMotifResult(
        **{
            field: getattr(provisional, field)
            for field in provisional.__dataclass_fields__
            if field != "authority_receipt_sha256"
        },
        authority_receipt_sha256=hashlib.sha256(
            _canonical(provisional.payload())
        ).hexdigest(),
    )
    result.verify()
    return result


def restore_live_motif_result(
    record: object,
    *,
    experience: AuditoryReceptorExperience,
) -> AuditoryLiveMotifResult:
    """Rejoin compact child spans to parent-owned physical occurrences."""
    if not isinstance(record, dict):
        raise ValueError("auditory live motif record changed")
    experience.verify()
    payload_keys = {
        "activation_spans",
        "authority_receipt_sha256",
        "firing_motif_neuron_ids",
        "firing_reason",
        "firing_state",
        "firing_work_cells",
        "learning_firing_motif_neuron_ids",
        "learning_reason",
        "learning_state",
        "learning_work_cells",
        "newly_grown_motif_neuron_ids",
        "reinforced_motif_neuron_ids",
        "schema",
        "source_experience_receipt_sha256",
        "source_receptor_event_receipt_sha256",
        "unresolved_source_indices",
    }
    if set(record) != payload_keys:
        raise ValueError("auditory live motif record fields changed")
    if (
        record["schema"] != AUDITORY_LIVE_MOTIF_RESULT_SCHEMA
        or record["source_experience_receipt_sha256"]
        != experience.authority_receipt_sha256
        or record["source_receptor_event_receipt_sha256"]
        != experience.source_event_receipt_sha256
    ):
        raise ValueError("auditory live motif source changed")
    activations = []
    for span in record["activation_spans"]:
        if not isinstance(span, dict):
            raise ValueError("auditory live motif span changed")
        segment_index = span.get("segment_index")
        source_index_start = span.get("source_index_start")
        source_index_end = span.get("source_index_end")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (
                segment_index,
                source_index_start,
                source_index_end,
            )
        ):
            raise ValueError("auditory live motif span ordinals changed")
        occurrences = tuple(
            value
            for value in experience.occurrences
            if (
                value.receptor.cochlear_index == segment_index // 2
                and source_index_start
                <= value.source_index
                <= source_index_end
            )
        )
        activation = AuditoryMotifActivation(
            neuron_id=span.get("motif_neuron_id"),
            segment_index=segment_index,
            state_ordinal_start=span.get("state_ordinal_start"),
            state_ordinal_end=span.get("state_ordinal_end"),
            source_index_start=source_index_start,
            source_index_end=source_index_end,
            source_time_start=_verified_fraction_text(
                span.get("source_time_start"),
                "activation source time start",
            ),
            source_time_end=_verified_fraction_text(
                span.get("source_time_end"),
                "activation source time end",
            ),
            full_field_occurrences=occurrences,
        )
        if _activation_payload(activation) != span:
            raise ValueError(
                "auditory compact activation changed physical support"
            )
        activations.append(activation)
    result = AuditoryLiveMotifResult(
        source_receptor_event_receipt_sha256=record[
            "source_receptor_event_receipt_sha256"
        ],
        source_experience_receipt_sha256=record[
            "source_experience_receipt_sha256"
        ],
        firing_state=record["firing_state"],
        learning_state=record["learning_state"],
        firing_motif_neuron_ids=tuple(
            record["firing_motif_neuron_ids"]
        ),
        learning_firing_motif_neuron_ids=tuple(
            record["learning_firing_motif_neuron_ids"]
        ),
        newly_grown_motif_neuron_ids=tuple(
            record["newly_grown_motif_neuron_ids"]
        ),
        reinforced_motif_neuron_ids=tuple(
            record["reinforced_motif_neuron_ids"]
        ),
        unresolved_source_indices=tuple(
            record["unresolved_source_indices"]
        ),
        firing_work_cells=record["firing_work_cells"],
        learning_work_cells=record["learning_work_cells"],
        firing_reason=record["firing_reason"],
        learning_reason=record["learning_reason"],
        activation_spans=tuple(record["activation_spans"]),
        internal_activations=tuple(activations),
        authority_receipt_sha256=record[
            "authority_receipt_sha256"
        ],
    )
    result.verify()
    return result


def encode_authenticated_motif_state(
    owner: AuditoryRecurrentMotifOwner,
    *,
    authority_key: bytes | str,
) -> dict[str, object]:
    if not isinstance(owner, AuditoryRecurrentMotifOwner):
        raise TypeError("auditory motif persistence requires its owner")
    key = _key(authority_key)
    state_limit = (
        AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES
        if owner.resource_profile.ear_count == 1
        else AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
    )
    envelope_limit = (
        AUDITORY_LIVE_MOTIF_ENVELOPE_MAX_BYTES
        if owner.resource_profile.ear_count == 1
        else AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES
    )
    if (
        owner.resource_profile.encoded_state_allocation_bytes
        > state_limit
    ):
        raise ValueError(
            "auditory motif owner allocation exceeds production"
        )
    payload = owner.snapshot_encoded()
    if len(payload) > state_limit:
        raise ValueError("auditory motif state exceeds live allocation")
    encoded = base64.b64encode(payload).decode("ascii")
    envelope = {
        "authority_hmac_sha256": hmac.new(
            key,
            AUDITORY_LIVE_MOTIF_PERSISTENCE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest(),
        "payload_base64": encoded,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "schema": AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA,
    }
    if len(_canonical(envelope)) > envelope_limit:
        raise ValueError("auditory motif persistence envelope exceeds allocation")
    return envelope


def _authenticated_motif_payload(
    envelope: object,
    *,
    authority_key: bytes | str,
) -> bytes:
    key = _key(authority_key)
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {
            "authority_hmac_sha256",
            "payload_base64",
            "payload_sha256",
            "schema",
        }
        or envelope.get("schema")
        != AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA
        or len(_canonical(envelope))
        > AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES
    ):
        raise ValueError("auditory motif persistence envelope changed")
    encoded = envelope.get("payload_base64")
    if not isinstance(encoded, str):
        raise ValueError("auditory motif persistence payload is absent")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("auditory motif persistence payload is unreadable") from exc
    if (
        len(payload) > AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
        or base64.b64encode(payload).decode("ascii") != encoded
        or not hmac.compare_digest(
            envelope.get("payload_sha256", ""),
            hashlib.sha256(payload).hexdigest(),
        )
        or not hmac.compare_digest(
            envelope.get("authority_hmac_sha256", ""),
            hmac.new(
                key,
                AUDITORY_LIVE_MOTIF_PERSISTENCE_DOMAIN + payload,
                hashlib.sha256,
            ).hexdigest(),
        )
    ):
        raise ValueError("auditory motif persistence authority changed")
    return payload


def restore_authenticated_motif_state(
    envelope: object,
    *,
    authority_key: bytes | str,
) -> AuditoryRecurrentMotifOwner:
    payload = _authenticated_motif_payload(
        envelope,
        authority_key=authority_key,
    )
    owner = AuditoryRecurrentMotifOwner.restore_encoded(payload)
    state_limit = (
        AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES
        if owner.resource_profile.ear_count == 1
        else AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
    )
    if (
        owner.resource_profile.encoded_state_allocation_bytes
        > state_limit
    ):
        raise ValueError("auditory motif restored allocation exceeds production")
    return owner


@dataclass(frozen=True, slots=True)
class AuditoryMotifProfileMigration:
    owner: AuditoryRecurrentMotifOwner
    authenticated_envelope: dict[str, object]
    migrated: bool


def migrate_authenticated_motif_state_profile(
    envelope: object,
    *,
    authority_key: bytes | str,
) -> AuditoryMotifProfileMigration:
    """Atomically reissue only the immediately prior authenticated profile."""

    payload = _authenticated_motif_payload(
        envelope,
        authority_key=authority_key,
    )
    try:
        owner = AuditoryRecurrentMotifOwner.restore_encoded(payload)
        migrated = False
    except ValueError:
        try:
            owner = migrate_immediately_prior_motif_profile(payload)
        except (TypeError, ValueError, RuntimeError) as migration_error:
            raise ValueError(
                "auditory motif profile is neither current nor the "
                "authenticated immediately prior profile"
            ) from migration_error
        migrated = True
    state_limit = (
        AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES
        if owner.resource_profile.ear_count == 1
        else AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
    )
    if (
        owner.resource_profile.encoded_state_allocation_bytes
        > state_limit
        or len(owner.snapshot_encoded()) > state_limit
    ):
        raise ValueError(
            "auditory motif migrated state exceeds production allocation"
        )
    rewritten = encode_authenticated_motif_state(
        owner,
        authority_key=authority_key,
    )
    strict_owner = restore_authenticated_motif_state(
        rewritten,
        authority_key=authority_key,
    )
    if strict_owner.snapshot_encoded() != owner.snapshot_encoded():
        raise RuntimeError(
            "auditory motif profile rewrite changed learned state"
        )
    if not migrated and rewritten != envelope:
        raise RuntimeError(
            "current auditory motif envelope changed during migration check"
        )
    return AuditoryMotifProfileMigration(
        owner=owner,
        authenticated_envelope=rewritten,
        migrated=migrated,
    )


__all__ = (
    "AUDITORY_LIVE_MOTIF_ENVELOPE_MAX_BYTES",
    "AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES",
    "AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA",
    "AUDITORY_LIVE_MOTIF_RESULT_SCHEMA",
    "AUDITORY_LIVE_MOTIF_STATE_ALLOCATION_BYTES",
    "AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES",
    "AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES",
    "AuditoryLiveMotifResult",
    "AuditoryMotifProfileMigration",
    "AuditoryVerifiedLiveMotifResultCapability",
    "build_live_motif_result",
    "build_verified_live_motif_result",
    "encode_authenticated_motif_state",
    "migrate_authenticated_motif_state_profile",
    "restore_authenticated_motif_state",
)
