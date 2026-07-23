"""Incremental native-hop proposals for tutor-witnessed auditory terminals.

The owner in this module is deliberately outside L0--L4.  It carries a
bounded monotone dynamic-programming state over continuous 10 ms auditory L5
pressure and provider-settled phase-advance frames. The state cannot recognize an identity: it has no
candidate-level L4 field.  After a full-field UNIQUE gate, its complete exact
paired recurrence can prove only the negative structural fact that the
verified path no longer extends; that closes the pending physical interval but
cannot create or change its learned meaning.

A proposed terminal must be rebuilt from its exact retained PCM through the
unchanged sixteen-channel, thirty-two-component boundary. The
existing ``AuditoryReciprocityOwner`` must then return one UNIQUE tutor label
from pressure, phase advance, topology, and both explicit L4 banks. UNKNOWN,
AMBIGUOUS, discontinuity, and resource exhaustion release nothing.

Terminal extent comes from the tutor-witnessed path length.  The current
reciprocity relation duration-normalizes complete candidates and does not
learn a separate variable-duration end transition.  Consequently this owner
can discover witnessed terminal extents at any native-hop offset, but it does
not claim to infer unwitnessed variable-duration endings.

Transport ids and receipts prove continuity only.  They never represent a
speaker, source, word, identity, meaning, or chi.  No text, ML model, acoustic
score, fitted threshold, or fixed vocabulary enters this module.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import secrets
import struct
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Callable

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    AUDITORY_KERNEL_SENSOR_ID,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AUDITORY_L5_SCHEMA,
    AuditoryL5ComponentKind,
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_STREAM_CAPACITY,
    PCM_STREAM_IDLE_SECONDS,
    AuditoryPCMContinuityReceipt,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECOGNITION_OPERATOR,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    MAX_INTERVAL_COMPONENTS_PER_CELL,
    MAX_PATH_BRANCHES_PER_CLASS,
    MAX_REACHABILITY_CELLS_PER_RECOGNITION,
    PCM_PRESSURE_QUANTUM,
    AuditoryRecognitionOccurrence,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP,
    AuditoryFullFieldCapture,
    AuditoryGammatoneContinuationReceipt,
)

try:
    from guala_core import (
        AuditoryIncrementalProposalCells as _NativeIncrementalProposalCells,
    )
except ImportError:
    _NativeIncrementalProposalCells = None


AUDITORY_INCREMENTAL_EVENT_SCHEMA = "guala.auditory.incremental_terminal.v1"
AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2 = (
    "guala.auditory.incremental_terminal.v2"
)
AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3 = (
    "guala.auditory.incremental_terminal.v3"
)
AUDITORY_INCREMENTAL_ADVANCE_SCHEMA = "guala.auditory.incremental_advance.v2"
AUDITORY_INCREMENTAL_BATCH_SCHEMA = (
    "guala.auditory.incremental_terminal_batch.v1"
)
_AUDITORY_INCREMENTAL_BATCH_KEY_DOMAIN = (
    b"guala.auditory.incremental_terminal_batch.v1\0"
)
MAX_EVENT_SAMPLES = PCM_SAMPLE_RATE_HZ * MAX_CAPTURE_SECONDS
MAX_EVENT_HOPS = MAX_EVENT_SAMPLES // OBSERVATION_HOP_SAMPLES
# This is a resource boundary, never a semantic threshold.  Exceeding the
# existing full-recognition work budget yields a typed indeterminate result.
MAX_ACTIVE_TRACKERS = max(
    1, MAX_REACHABILITY_CELLS_PER_RECOGNITION // MAX_EVENT_HOPS
)
# Every full-field confirmation performed by one advance shares the existing
# recognition boundary.  Proposal count, closure count, and chunk size cannot
# multiply this authority.
MAX_FULL_GATE_WORK_PER_ADVANCE = MAX_REACHABILITY_CELLS_PER_RECOGNITION
MAX_FULL_GATE_FIELD_SAMPLES_PER_ADVANCE = MAX_NATIVE_SAMPLES_PER_SETTLEMENT
# One terminal needs at least one native hop, so an advance can never release
# more terminals than the maximum hop count already admitted for one event.
# This is a resource capacity only; terminal identity and closure never depend
# on it.
MAX_RELEASED_TERMINALS_PER_ADVANCE = MAX_EVENT_HOPS


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hmac(key: bytes, value: object) -> str:
    return hmac.new(key, _canonical_bytes(value), hashlib.sha256).hexdigest()


def _canonical_digest(value: object, name: str) -> str:
    return sha256_digest(value, name)


class AuditoryIncrementalStatus(str, Enum):
    UNKNOWN = "unknown"
    CONTINUING = "continuing"
    RELEASED_UNIQUE = "released_unique"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE_RESOURCE = "indeterminate_resource"
    DISCONTINUITY = "discontinuity"


def _event_payload(
    *,
    event_id: str,
    stream_id: str,
    source_sample_start: int,
    source_sample_end: int,
    tutor_label: str,
    structural_fingerprint: str,
    l5_authority_receipt_sha256: str,
    transport_receipt_sha256s: tuple[str, ...],
    cochlear_receipt_sha256s: tuple[str, ...],
    joint_settlement_receipt_sha256s: tuple[str, ...],
    recognition_occurrence: AuditoryRecognitionOccurrence | None,
    schema: str | None = None,
    l5_schema: str | None = None,
    reciprocity_snapshot_schema: str | None = None,
    recognition_operator: str | None = None,
) -> dict[str, object]:
    if schema is None:
        schema = (
            AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2
            if recognition_occurrence is not None
            else AUDITORY_INCREMENTAL_EVENT_SCHEMA
        )
    payload = {
        "cochlear_receipt_sha256s": list(cochlear_receipt_sha256s),
        "event_id": event_id,
        "joint_settlement_receipt_sha256s": list(
            joint_settlement_receipt_sha256s
        ),
        "l5_authority_receipt_sha256": l5_authority_receipt_sha256,
        "recognition_state": AuditoryRecognitionState.UNIQUE.value,
        "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
        "schema": schema,
        "source_sample_end": source_sample_end,
        "source_sample_start": source_sample_start,
        "stream_id": stream_id,
        "structural_fingerprint": structural_fingerprint,
        "transport_receipt_sha256s": list(transport_receipt_sha256s),
        "tutor_label": tutor_label,
    }
    if recognition_occurrence is not None:
        recognition_occurrence.verify()
        payload["recognition_occurrence"] = recognition_occurrence.as_record()
    if schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3:
        payload.update({
            "l5_schema": l5_schema,
            "recognition_operator": recognition_operator,
            "reciprocity_snapshot_schema": reciprocity_snapshot_schema,
        })
    return payload


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalTerminalEvent:
    event_id: str
    stream_id: str
    source_sample_start: int
    source_sample_end: int
    tutor_label: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    transport_receipt_sha256s: tuple[str, ...]
    cochlear_receipt_sha256s: tuple[str, ...]
    joint_settlement_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str
    recognition_occurrence: AuditoryRecognitionOccurrence | None = None
    schema: str | None = None
    l5_schema: str | None = None
    reciprocity_snapshot_schema: str | None = None
    recognition_operator: str | None = None

    @property
    def sample_count(self) -> int:
        return self.source_sample_end - self.source_sample_start

    @property
    def record_schema(self) -> str:
        return (
            self.schema
            if self.schema is not None
            else AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2
            if self.recognition_occurrence is not None
            else AUDITORY_INCREMENTAL_EVENT_SCHEMA
        )

    def verify(self) -> None:
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("incremental auditory event has no stream epoch")
        if (
            isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or self.source_sample_start < 0
            or self.source_sample_start % OBSERVATION_HOP_SAMPLES
            or isinstance(self.source_sample_end, bool)
            or not isinstance(self.source_sample_end, int)
            or self.source_sample_end <= self.source_sample_start
            or self.sample_count > MAX_EVENT_SAMPLES
            or self.sample_count % OBSERVATION_HOP_SAMPLES
        ):
            raise ValueError("incremental auditory event interval is invalid")
        if not isinstance(self.tutor_label, str) or not self.tutor_label:
            raise ValueError("incremental auditory event has no tutor label")
        fingerprint = _canonical_digest(
            self.structural_fingerprint,
            "incremental auditory structural fingerprint",
        )
        l5_receipt = _canonical_digest(
            self.l5_authority_receipt_sha256,
            "incremental auditory L5 receipt",
        )
        schema = self.record_schema
        if schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3:
            if (
                self.recognition_occurrence is None
                or self.l5_schema != AUDITORY_L5_SCHEMA
                or self.reciprocity_snapshot_schema
                != AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
                or self.recognition_operator
                != AUDITORY_RECOGNITION_OPERATOR
            ):
                raise ValueError(
                    "incremental auditory event generation changed"
                )
        elif schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2:
            if (
                self.recognition_occurrence is None
                or self.l5_schema is not None
                or self.reciprocity_snapshot_schema is not None
                or self.recognition_operator is not None
            ):
                raise ValueError(
                    "incremental auditory v2 audit record changed"
                )
        elif schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA:
            if (
                self.recognition_occurrence is not None
                or self.l5_schema is not None
                or self.reciprocity_snapshot_schema is not None
                or self.recognition_operator is not None
            ):
                raise ValueError(
                    "incremental auditory v1 audit record changed"
                )
        else:
            raise ValueError("incremental auditory event schema changed")
        if self.recognition_occurrence is not None:
            self.recognition_occurrence.verify()
            if (
                self.recognition_occurrence.kind
                is not AuditoryReciprocityKind.SPOKEN_FORM
                or self.recognition_occurrence.state
                is not AuditoryRecognitionState.UNIQUE
                or self.recognition_occurrence.structural_fingerprint
                != fingerprint
                or self.recognition_occurrence.l5_authority_receipt_sha256
                != l5_receipt
                or (
                    schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3
                    and self.recognition_occurrence.operator
                    != self.recognition_operator
                )
            ):
                raise ValueError(
                    "incremental auditory recognition occurrence changed"
                )
        receipt_groups = (
            self.transport_receipt_sha256s,
            self.cochlear_receipt_sha256s,
            self.joint_settlement_receipt_sha256s,
        )
        if any(
            not isinstance(group, tuple)
            or not group
            or len(group) > MAX_EVENT_HOPS
            for group in receipt_groups
        ):
            raise ValueError("incremental auditory event lost causal evidence")
        if len({len(group) for group in receipt_groups}) != 1:
            raise ValueError("incremental auditory event evidence is not joint")
        transport, cochlear, joint = (
            tuple(
                _canonical_digest(value, "incremental auditory evidence receipt")
                for value in group
            )
            for group in receipt_groups
        )
        expected_id = _digest({
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "stream_id": self.stream_id,
            "structural_fingerprint": fingerprint,
        })
        if self.event_id != expected_id:
            raise ValueError("incremental auditory event identity changed")
        payload = _event_payload(
            event_id=expected_id,
            stream_id=self.stream_id,
            source_sample_start=self.source_sample_start,
            source_sample_end=self.source_sample_end,
            tutor_label=self.tutor_label,
            structural_fingerprint=fingerprint,
            l5_authority_receipt_sha256=l5_receipt,
            transport_receipt_sha256s=transport,
            cochlear_receipt_sha256s=cochlear,
            joint_settlement_receipt_sha256s=joint,
            recognition_occurrence=self.recognition_occurrence,
            schema=schema,
            l5_schema=self.l5_schema,
            reciprocity_snapshot_schema=self.reciprocity_snapshot_schema,
            recognition_operator=self.recognition_operator,
        )
        if _digest(payload) != _canonical_digest(
            self.authority_receipt_sha256,
            "incremental auditory event authority receipt",
        ):
            raise ValueError("incremental auditory event receipt was altered")

    def as_record(self) -> dict[str, object]:
        """Return the complete canonical terminal only after verification.

        The tutor label is one field inside this receipt-bound physical event;
        it is never a stand-alone recognition authority at the cognition door.
        """
        self.verify()
        record = _event_payload(
            event_id=self.event_id,
            stream_id=self.stream_id,
            source_sample_start=self.source_sample_start,
            source_sample_end=self.source_sample_end,
            tutor_label=self.tutor_label,
            structural_fingerprint=self.structural_fingerprint,
            l5_authority_receipt_sha256=self.l5_authority_receipt_sha256,
            transport_receipt_sha256s=self.transport_receipt_sha256s,
            cochlear_receipt_sha256s=self.cochlear_receipt_sha256s,
            joint_settlement_receipt_sha256s=(
                self.joint_settlement_receipt_sha256s
            ),
            recognition_occurrence=self.recognition_occurrence,
            schema=self.record_schema,
            l5_schema=self.l5_schema,
            reciprocity_snapshot_schema=self.reciprocity_snapshot_schema,
            recognition_operator=self.recognition_operator,
        )
        record["authority_receipt_sha256"] = self.authority_receipt_sha256
        return record

    @classmethod
    def from_record(
        cls,
        record: dict[str, object],
    ) -> "AuditoryIncrementalTerminalEvent":
        """Restore one complete bounded witness without granting admission.

        Reconstructing a durable record proves its internal receipt graph only.
        It does not put the event back into the live registry, so a restored or
        copied record can never replay a conversation turn.
        """
        if not isinstance(record, dict):
            raise TypeError("incremental auditory event record must be an object")
        expected_fields = {
            "authority_receipt_sha256",
            "cochlear_receipt_sha256s",
            "event_id",
            "joint_settlement_receipt_sha256s",
            "l5_authority_receipt_sha256",
            "recognition_state",
            "sample_rate_hz",
            "schema",
            "source_sample_end",
            "source_sample_start",
            "stream_id",
            "structural_fingerprint",
            "transport_receipt_sha256s",
            "tutor_label",
        }
        schema = record.get("schema")
        if schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3:
            expected_fields.update({
                "l5_schema",
                "recognition_occurrence",
                "recognition_operator",
                "reciprocity_snapshot_schema",
            })
        elif schema == AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2:
            expected_fields.add("recognition_occurrence")
        elif schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA:
            raise ValueError("incremental auditory event record schema changed")
        if set(record) != expected_fields:
            raise ValueError("incremental auditory event record fields changed")
        if record.get("recognition_state") != AuditoryRecognitionState.UNIQUE.value:
            raise ValueError("incremental auditory event record is not unique")
        if record.get("sample_rate_hz") != PCM_SAMPLE_RATE_HZ:
            raise ValueError("incremental auditory event sample rate changed")
        for field in (
            "transport_receipt_sha256s",
            "cochlear_receipt_sha256s",
            "joint_settlement_receipt_sha256s",
        ):
            values = record.get(field)
            if (
                not isinstance(values, list)
                or not values
                or len(values) > MAX_EVENT_HOPS
            ):
                raise ValueError(
                    f"incremental auditory event {field} is invalid"
                )
        event = cls(
            event_id=record.get("event_id"),
            stream_id=record.get("stream_id"),
            source_sample_start=record.get("source_sample_start"),
            source_sample_end=record.get("source_sample_end"),
            tutor_label=record.get("tutor_label"),
            structural_fingerprint=record.get("structural_fingerprint"),
            l5_authority_receipt_sha256=record.get(
                "l5_authority_receipt_sha256"
            ),
            transport_receipt_sha256s=tuple(
                record["transport_receipt_sha256s"]
            ),
            cochlear_receipt_sha256s=tuple(
                record["cochlear_receipt_sha256s"]
            ),
            joint_settlement_receipt_sha256s=tuple(
                record["joint_settlement_receipt_sha256s"]
            ),
            schema=schema,
            recognition_occurrence=(
                AuditoryRecognitionOccurrence.from_record(
                    record["recognition_occurrence"]
                )
                if schema in (
                    AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2,
                    AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
                ) else None
            ),
            l5_schema=record.get("l5_schema"),
            reciprocity_snapshot_schema=record.get(
                "reciprocity_snapshot_schema"
            ),
            recognition_operator=record.get("recognition_operator"),
            authority_receipt_sha256=record.get(
                "authority_receipt_sha256"
            ),
        )
        event.verify()
        if event.as_record() != record:
            raise ValueError("incremental auditory event record is not canonical")
        return event


def _advance_payload(
    *,
    status: AuditoryIncrementalStatus,
    released_terminals: tuple[AuditoryIncrementalTerminalEvent, ...],
    processed_hops: int,
    active_tracker_count: int,
) -> dict[str, object]:
    reply_candidate = (
        released_terminals[0] if len(released_terminals) == 1 else None
    )
    return {
        "active_tracker_count": active_tracker_count,
        "processed_hops": processed_hops,
        "released_terminal_receipt_sha256s": [
            value.authority_receipt_sha256 for value in released_terminals
        ],
        "reply_candidate_receipt_sha256": (
            reply_candidate.authority_receipt_sha256
            if reply_candidate is not None else None
        ),
        "schema": AUDITORY_INCREMENTAL_ADVANCE_SCHEMA,
        "status": status.value,
    }


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalAdvance:
    status: AuditoryIncrementalStatus
    released_terminals: tuple[AuditoryIncrementalTerminalEvent, ...]
    processed_hops: int
    active_tracker_count: int
    authority_receipt_sha256: str

    @property
    def reply_candidate(self) -> AuditoryIncrementalTerminalEvent | None:
        """Compatibility view for callers that can consume exactly one event."""
        return (
            self.released_terminals[0]
            if len(self.released_terminals) == 1 else None
        )

    def verify(self) -> None:
        if not isinstance(self.status, AuditoryIncrementalStatus):
            raise ValueError("incremental auditory status is invalid")
        for value, name in (
            (self.processed_hops, "processed hops"),
            (self.active_tracker_count, "active tracker count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"incremental auditory {name} is invalid")
        if self.active_tracker_count > MAX_ACTIVE_TRACKERS:
            raise ValueError("incremental auditory tracker boundary was exceeded")
        if (
            not isinstance(self.released_terminals, tuple)
            or len(self.released_terminals) > MAX_RELEASED_TERMINALS_PER_ADVANCE
        ):
            raise ValueError("incremental auditory release boundary was exceeded")
        if self.status is AuditoryIncrementalStatus.RELEASED_UNIQUE:
            if not self.released_terminals:
                raise ValueError("unique auditory release has no terminals")
        elif self.released_terminals:
            raise ValueError("non-release auditory state exposed terminals")
        prior: AuditoryIncrementalTerminalEvent | None = None
        seen: set[str] = set()
        for terminal in self.released_terminals:
            if not isinstance(terminal, AuditoryIncrementalTerminalEvent):
                raise TypeError("incremental auditory release is not a terminal")
            terminal.verify()
            if terminal.event_id in seen:
                raise ValueError("incremental auditory release repeats a terminal")
            if prior is not None and (
                terminal.stream_id != prior.stream_id
                or terminal.source_sample_start < prior.source_sample_end
            ):
                raise ValueError(
                    "incremental auditory terminals are not in physical source order"
                )
            seen.add(terminal.event_id)
            prior = terminal
        payload = _advance_payload(
            status=self.status,
            released_terminals=self.released_terminals,
            processed_hops=self.processed_hops,
            active_tracker_count=self.active_tracker_count,
        )
        if _digest(payload) != _canonical_digest(
            self.authority_receipt_sha256,
            "incremental auditory advance receipt",
        ):
            raise ValueError("incremental auditory advance receipt was altered")


def _batch_entry_payload(
    value: "AuditoryIncrementalTerminalBatchEntry",
) -> dict[str, object]:
    return {
        "l5_authority_receipt_sha256": (
            value.auditory_l5.authority_receipt_sha256
        ),
        "l5_experience_id": value.auditory_l5.experience_id,
        "source_sample_end": value.event.source_sample_end,
        "source_sample_start": value.event.source_sample_start,
        "source_time_end": [
            value.auditory_l5.source_time_end.numerator,
            value.auditory_l5.source_time_end.denominator,
        ],
        "source_time_start": [
            value.auditory_l5.source_time_start.numerator,
            value.auditory_l5.source_time_start.denominator,
        ],
        "stream_id": value.event.stream_id,
        "structural_fingerprint": value.event.structural_fingerprint,
        "terminal_authority_receipt_sha256": (
            value.event.authority_receipt_sha256
        ),
        "terminal_event_id": value.event.event_id,
    }


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalTerminalBatchEntry:
    """One exact terminal and the complete L5 field released with it."""

    event: AuditoryIncrementalTerminalEvent
    auditory_l5: AuditoryL5Experience

    def verify(self) -> None:
        self._verify(verify_full_field=True)

    def _verify(self, *, verify_full_field: bool) -> None:
        if not isinstance(self.event, AuditoryIncrementalTerminalEvent):
            raise TypeError("incremental auditory batch entry has no terminal")
        if not isinstance(self.auditory_l5, AuditoryL5Experience):
            raise TypeError("incremental auditory batch entry has no L5 field")
        self.event.verify()
        if verify_full_field:
            self.auditory_l5.verify()
        if (
            self.event.schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3
            or self.auditory_l5.event_boundary != "utterance"
            or self.auditory_l5.structural_fingerprint
            != self.event.structural_fingerprint
            or self.auditory_l5.authority_receipt_sha256
            != self.event.l5_authority_receipt_sha256
            or self.auditory_l5.source_time_end
            - self.auditory_l5.source_time_start
            != Fraction(self.event.sample_count, PCM_SAMPLE_RATE_HZ)
        ):
            raise ValueError(
                "incremental auditory batch terminal and full field disagree"
            )


def _batch_payload(
    *,
    advance_authority_receipt_sha256: str,
    entries: tuple[AuditoryIncrementalTerminalBatchEntry, ...],
) -> dict[str, object]:
    return {
        "advance_authority_receipt_sha256": (
            advance_authority_receipt_sha256
        ),
        "entries": [_batch_entry_payload(value) for value in entries],
        "schema": AUDITORY_INCREMENTAL_BATCH_SCHEMA,
    }


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalTerminalBatch:
    """Canonical ordered authority for every terminal in one release.

    The receipt binds order and every exact terminal/L5 authority graph.  The
    full immutable L5 objects remain present; this is not a compatibility
    vector or a reduced projection of their explicit fields.
    """

    advance_authority_receipt_sha256: str
    entries: tuple[AuditoryIncrementalTerminalBatchEntry, ...]
    authority_receipt_sha256: str
    authority_hmac_sha256: str

    def verify(self) -> None:
        self._verify(verify_full_fields=True)

    def _verify(self, *, verify_full_fields: bool) -> None:
        _canonical_digest(
            self.advance_authority_receipt_sha256,
            "incremental auditory batch advance receipt",
        )
        if (
            not isinstance(self.entries, tuple)
            or not self.entries
            or len(self.entries) > MAX_RELEASED_TERMINALS_PER_ADVANCE
        ):
            raise ValueError("incremental auditory batch boundary is invalid")
        prior: AuditoryIncrementalTerminalBatchEntry | None = None
        seen: set[str] = set()
        epoch: Fraction | None = None
        for entry in self.entries:
            if not isinstance(entry, AuditoryIncrementalTerminalBatchEntry):
                raise TypeError("incremental auditory batch entry is untyped")
            entry._verify(verify_full_field=verify_full_fields)
            event = entry.event
            current_epoch = entry.auditory_l5.source_time_start - Fraction(
                event.source_sample_start,
                PCM_SAMPLE_RATE_HZ,
            )
            if epoch is None:
                epoch = current_epoch
            elif current_epoch != epoch:
                raise ValueError(
                    "incremental auditory batch source clocks disagree"
                )
            if event.event_id in seen:
                raise ValueError("incremental auditory batch repeats a terminal")
            if prior is not None and (
                event.stream_id != prior.event.stream_id
                or event.source_sample_start < prior.event.source_sample_end
                or entry.auditory_l5.source_time_start
                < prior.auditory_l5.source_time_end
            ):
                raise ValueError(
                    "incremental auditory batch is not in physical order"
                )
            seen.add(event.event_id)
            prior = entry
        payload = _batch_payload(
            advance_authority_receipt_sha256=(
                self.advance_authority_receipt_sha256
            ),
            entries=self.entries,
        )
        if _digest(payload) != _canonical_digest(
            self.authority_receipt_sha256,
            "incremental auditory batch authority receipt",
        ):
            raise ValueError("incremental auditory batch receipt was altered")
        _canonical_digest(
            self.authority_hmac_sha256,
            "incremental auditory batch authority HMAC",
        )


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalTerminalBatchClaim:
    """Opaque immutable reservation for one complete release batch."""

    batch: AuditoryIncrementalTerminalBatch
    authority_positions: tuple[int, ...]
    owner_token: object = field(compare=False, repr=False)
    reservation_token: object = field(compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class _Branch:
    structural_fingerprint: str
    sample_count: int
    topology: tuple[tuple[object, ...], ...]
    source_indices: tuple[int, ...]
    causal_offset_start: Fraction
    causal_offset_step: Fraction
    pressure_l4_field_tuples: tuple[tuple[tuple[object, ...], ...], ...]
    carrier_phase_advance_l4_field_tuples: tuple[
        tuple[tuple[object, ...], ...], ...
    ]
    # cochlear channel -> frame -> (pressure, settled phase-advance turns)
    values: tuple[tuple[tuple[float, float], ...], ...]


@dataclass(frozen=True, slots=True)
class _Cell:
    tutor_label: str
    left: _Branch
    right: _Branch
    reference_count: int
    terminal_floor: int
    recurrence_incoming: tuple[tuple[int, ...], ...]


Interval = tuple[float, float]
IntervalSet = tuple[Interval, ...]


@dataclass(slots=True)
class _Tracker:
    cell_index: int
    start_sample: int
    frames_seen: int
    first_pressure: tuple[float, ...]
    first_phase_advance: tuple[float, ...]
    previous_pressure: tuple[float, ...]
    previous_phase_advance: tuple[float, ...]
    row: tuple[IntervalSet, ...] | None


@dataclass(frozen=True, slots=True)
class _Evidence:
    start: int
    end: int
    transport: str
    cochlear: str
    joint: str


@dataclass(frozen=True, slots=True)
class _Frame:
    completion_sample: int
    pressure: tuple[float, ...]
    phase_advance: tuple[float, ...]
    phase_advance_nyquist_fraction: tuple[float, ...]


def _event_local_phase_component(
    frames: tuple[_Frame, ...],
    channel_index: int,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Establish phase origin for one derived bounded auditory event.

    The continuous capture keeps its real predecessor-dependent first
    advance.  A derived utterance has no predecessor inside its own causal
    boundary, so only its phase component begins at exact zero.  Every later
    provider-settled advance remains unchanged.
    """
    if not frames:
        raise ValueError("event-local auditory phase requires frames")
    if (
        isinstance(channel_index, bool)
        or not isinstance(channel_index, int)
        or not 0 <= channel_index < COCHLEAR_CHANNEL_COUNT
    ):
        raise ValueError("event-local auditory phase channel is invalid")
    advances = tuple(
        0.0 if index == 0 else frame.phase_advance[channel_index]
        for index, frame in enumerate(frames)
    )
    normalized = tuple(
        0.0
        if index == 0
        else frame.phase_advance_nyquist_fraction[channel_index]
        for index, frame in enumerate(frames)
    )
    return advances, normalized


@dataclass(frozen=True, slots=True)
class _PendingTerminal:
    start: int
    end: int
    tutor_label: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    transport_receipt_sha256s: tuple[str, ...]
    cochlear_receipt_sha256s: tuple[str, ...]
    joint_settlement_receipt_sha256s: tuple[str, ...]
    auditory_l5: AuditoryL5Experience
    recognition_occurrence: AuditoryRecognitionOccurrence | None = None


@dataclass(frozen=True, slots=True)
class _OwnerLiveStateCheckpoint:
    stream_id: str | None
    last_transport: AuditoryPCMContinuityReceipt | None
    last_cochlear: AuditoryGammatoneContinuationReceipt | None
    last_result: AuditoryIncrementalAdvance | None
    last_committed_receipt_sha256: str | None
    buffer_start: int
    pcm: bytes
    evidence: tuple[_Evidence, ...]
    frames: tuple[_Frame, ...]
    pending: tuple[tuple[int, _PendingTerminal], ...]
    released_full_fields: tuple[
        tuple[str, AuditoryL5Experience], ...
    ]
    native_active_starts: tuple[int, ...]
    native_active_tracker_count: int
    native_state: object | None = field(compare=False, repr=False)


@dataclass(slots=True)
class _AdvanceFullGateWorkLedger:
    """Cumulative exact field and reachability authority for one advance."""

    reachability_limit: int
    field_sample_limit: int
    reachability_consumed: int = 0
    field_samples_consumed: int = 0

    @property
    def remaining_reachability(self) -> int:
        return self.reachability_limit - self.reachability_consumed

    @staticmethod
    def _work(required: int, name: str) -> int:
        if (
            isinstance(required, bool)
            or not isinstance(required, int)
            or required < 0
        ):
            raise ValueError(f"full-gate {name} work must be non-negative")
        return required

    def reserve_field_samples(self, required: int) -> bool:
        required = self._work(required, "field-sample")
        if required > self.field_sample_limit - self.field_samples_consumed:
            return False
        self.field_samples_consumed += required
        return True

    def charge_reachability(self, required: int) -> None:
        required = self._work(required, "reachability")
        if required > self.remaining_reachability:
            raise RuntimeError("full-gate work exceeded its granted authority")
        self.reachability_consumed += required


def _branch_from_snapshot(value: object) -> _Branch:
    if not isinstance(value, dict):
        raise ValueError("incremental auditory witness is malformed")
    sample_count = value.get("sample_count")
    topology_raw = value.get("topology")
    packed_raw = value.get("packed_samples")
    source_indices_raw = value.get("source_indices")
    pressure_l4_raw = value.get("pressure_l4_field_tuples")
    phase_l4_raw = value.get("carrier_phase_advance_l4_field_tuples")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 2
        or sample_count > MAX_EVENT_HOPS
        or not isinstance(topology_raw, list)
        or len(topology_raw) != COCHLEAR_CHANNEL_COUNT
        or not isinstance(packed_raw, list)
        or len(packed_raw) != COCHLEAR_CHANNEL_COUNT
        or not isinstance(source_indices_raw, list)
        or source_indices_raw != list(range(sample_count))
        or not isinstance(pressure_l4_raw, list)
        or len(pressure_l4_raw) != COCHLEAR_CHANNEL_COUNT
        or not isinstance(phase_l4_raw, list)
        or len(phase_l4_raw) != COCHLEAR_CHANNEL_COUNT
    ):
        raise ValueError("incremental auditory witness exceeds its boundary")

    def exact_fraction(raw: object, name: str) -> Fraction:
        if not isinstance(raw, str):
            raise ValueError(f"{name} is not an exact fraction")
        try:
            return Fraction(raw)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{name} is not an exact fraction") from exc

    exact_fraction(
        value.get("source_time_start"),
        "incremental auditory source time start",
    )
    causal_offset_start = exact_fraction(
        value.get("causal_offset_start"),
        "incremental auditory causal offset start",
    )
    causal_offset_step = exact_fraction(
        value.get("causal_offset_step"),
        "incremental auditory causal offset step",
    )
    native_hop = Fraction(
        OBSERVATION_HOP_SAMPLES,
        PCM_SAMPLE_RATE_HZ,
    )
    if (
        causal_offset_start != native_hop
        or causal_offset_step != native_hop
    ):
        raise ValueError("incremental auditory witness grid changed")

    def component_topology(
        raw: object,
        *,
        channel_index: int,
        phase_advance: bool,
    ) -> tuple[object, ...]:
        if not isinstance(raw, dict):
            raise ValueError("incremental auditory component topology changed")
        definition = AUDITORY_CHANNELS[channel_index]
        expected_index = channel_index * 2 + int(phase_advance)
        component = (
            "carrier-phase-advance" if phase_advance else "pressure-envelope"
        )
        expected_coordinates = (
            ("cochlear-channel", definition.name),
            ("kernel-component", component),
            ("centre-hz", str(definition.centre_hz)),
            ("erb-width-hz", str(definition.erb_width_hz)),
            ("gammatone-order", "4"),
            ("observation-hop-samples", str(OBSERVATION_HOP_SAMPLES)),
        )
        coordinates_raw = raw.get("coordinates")
        coordinates = (
            tuple(tuple(item) for item in coordinates_raw)
            if isinstance(coordinates_raw, list)
            and all(isinstance(item, list) and len(item) == 2
                    for item in coordinates_raw)
            else ()
        )
        expected_substream = (
            f"{definition.name}_phase_advance"
            if phase_advance
            else f"{definition.name}_pressure"
        )
        expected_quantity = (
            "cochlear-carrier-phase-advance"
            if phase_advance
            else "cochlear-pressure-envelope"
        )
        expected_unit = (
            "nyquist-fraction-per-observation-hop"
            if phase_advance
            else "full-scale-pressure"
        )
        if (
            raw.get("sensor_id") != AUDITORY_KERNEL_SENSOR_ID
            or raw.get("substream_id") != expected_substream
            or raw.get("topology_index") != expected_index
            or coordinates != expected_coordinates
            or raw.get("physical_quantity") != expected_quantity
            or raw.get("physical_unit") != expected_unit
        ):
            raise ValueError("incremental auditory witness topology changed")
        return (
            raw.get("sensor_id"),
            raw.get("substream_id"),
            raw.get("topology_index"),
            coordinates,
            raw.get("physical_quantity"),
            raw.get("physical_unit"),
            _canonical_digest(
                raw.get("source_stream_receipt_sha256"),
                "incremental auditory source stream receipt",
            ),
            _canonical_digest(
                raw.get("l0_l4_trace_receipt_sha256"),
                "incremental auditory L0-L4 trace receipt",
            ),
            _canonical_digest(
                raw.get("kernel_basin_receipt_sha256"),
                "incremental auditory kernel basin receipt",
            ),
            _canonical_digest(
                raw.get("authority_receipt_sha256"),
                "incremental auditory component receipt",
            ),
        )

    def l4_bank(raw: object, name: str) -> tuple[tuple[object, ...], ...]:
        if (
            not isinstance(raw, list)
            or not raw
            or len(raw) > MAX_EVENT_HOPS
        ):
            raise ValueError(f"{name} is incomplete")
        restored = []
        for expected_index, item in enumerate(raw):
            if (
                not isinstance(item, dict)
                or item.get("tuple_index") != expected_index
                or not isinstance(item.get("fields"), list)
            ):
                raise ValueError(f"{name} is incomplete")
            fields = tuple(
                (field[0], exact_fraction(field[1], f"{name}.{field[0]}"))
                for field in item["fields"]
                if isinstance(field, list) and len(field) == 2
            )
            if (
                len(fields) != len(item["fields"])
                or tuple(field_name for field_name, _ in fields)
                != DSF_FIELD_ORDER
            ):
                raise ValueError(f"{name} field structure changed")
            restored.append((
                expected_index,
                fields,
                _canonical_digest(
                    item.get("authority_receipt_sha256"),
                    f"{name} receipt",
                ),
            ))
        return tuple(restored)

    topology = []
    values = []
    pressure_l4 = []
    phase_l4 = []
    for channel_index, (
        raw_topology,
        encoded,
        raw_pressure_l4,
        raw_phase_l4,
    ) in enumerate(
        zip(
            topology_raw,
            packed_raw,
            pressure_l4_raw,
            phase_l4_raw,
            strict=True,
        )
    ):
        if (
            not isinstance(raw_topology, dict)
            or raw_topology.get("cochlear_index") != channel_index
            or raw_topology.get("channel_id")
            != AUDITORY_CHANNELS[channel_index].name
            or not isinstance(encoded, str)
        ):
            raise ValueError("incremental auditory witness topology changed")
        pair_receipt = _canonical_digest(
            raw_topology.get("pair_receipt_sha256"),
            "incremental auditory pair receipt",
        )
        pressure_topology = component_topology(
            raw_topology.get("pressure"),
            channel_index=channel_index,
            phase_advance=False,
        )
        phase_topology = component_topology(
            raw_topology.get("carrier_phase_advance"),
            channel_index=channel_index,
            phase_advance=True,
        )
        topology.append((
            channel_index,
            raw_topology.get("channel_id"),
            pressure_topology,
            phase_topology,
            pair_receipt,
        ))
        try:
            packed = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError(
                "incremental auditory witness samples cannot be decoded"
            ) from exc
        if len(packed) != sample_count * 16:
            raise ValueError("incremental auditory witness cardinality changed")
        unpacked = struct.unpack(f"<{sample_count * 2}d", packed)
        if any(not math.isfinite(item) for item in unpacked):
            raise ValueError("incremental auditory witness is not finite")
        channel_values = tuple(
            (unpacked[index * 2], unpacked[index * 2 + 1])
            for index in range(sample_count)
        )
        if any(
            not 0.0 <= pressure <= 1.0
            or not -PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            <= phase_advance
            <= PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            for pressure, phase_advance in channel_values
        ):
            raise ValueError("incremental auditory witness left physical bounds")
        values.append(channel_values)
        pressure_l4.append(l4_bank(
            raw_pressure_l4,
            f"incremental pressure L4 channel {channel_index}",
        ))
        phase_l4.append(l4_bank(
            raw_phase_l4,
            f"incremental phase L4 channel {channel_index}",
        ))
        if tuple(value[2] for value in pressure_l4[-1]) == tuple(
            value[2] for value in phase_l4[-1]
        ):
            raise ValueError("incremental auditory L4 banks are not independent")
    return _Branch(
        structural_fingerprint=_canonical_digest(
            value.get("structural_fingerprint"),
            "incremental auditory witness fingerprint",
        ),
        sample_count=sample_count,
        topology=tuple(topology),
        source_indices=tuple(source_indices_raw),
        causal_offset_start=causal_offset_start,
        causal_offset_step=causal_offset_step,
        pressure_l4_field_tuples=tuple(pressure_l4),
        carrier_phase_advance_l4_field_tuples=tuple(phase_l4),
        values=tuple(values),
    )


def _branch_sample(
    branch: _Branch,
    port: int,
    query_index: int,
    query_count: int,
) -> tuple[float, float]:
    """Return pressure and phase advance on the common reference grid."""

    if branch.sample_count == 1 or query_count == 1:
        return branch.values[port][0]
    position = query_index * (branch.sample_count - 1) / (query_count - 1)
    left_index = int(math.floor(position))
    right_index = min(left_index + 1, branch.sample_count - 1)
    weight = position - left_index
    left_pressure = branch.values[port][left_index][0]
    right_pressure = branch.values[port][right_index][0]

    left_phase = branch.values[port][left_index][1]
    right_phase = branch.values[port][right_index][1]
    return (
        left_pressure + weight * (right_pressure - left_pressure),
        left_phase + weight * (right_phase - left_phase),
    )


def _branch_phase_prior_pressure(
    branch: _Branch,
    port: int,
    query_index: int,
    query_count: int,
) -> float:
    position = (
        0.0
        if query_count == 1
        else query_index * (branch.sample_count - 1) / (query_count - 1)
    )
    prior_position = position - 1.0 if position >= 1.0 else position + 1.0
    left = int(math.floor(prior_position))
    right = min(left + 1, branch.sample_count - 1)
    weight = prior_position - left
    return (
        branch.values[port][left][0]
        + weight
        * (branch.values[port][right][0] - branch.values[port][left][0])
    )


def _phase_uncertainty(*pressures: float) -> float | None:
    quantum = float(PCM_PRESSURE_QUANTUM)
    if any(value <= quantum for value in pressures):
        return None
    return sum(
        math.asin(min(1.0, quantum / value)) / (2.0 * math.pi)
        for value in pressures
    )


def _intersect_lambda(
    interval: Interval,
    *,
    query: float,
    left: float,
    right: float,
    uncertainty: float,
) -> Interval | None:
    lower, upper = interval
    difference = right - left
    if difference == 0.0:
        return interval if abs(query - left) <= uncertainty else None
    first = (query - uncertainty - left) / difference
    second = (query + uncertainty - left) / difference
    result = (max(lower, min(first, second)), min(upper, max(first, second)))
    return result if result[0] <= result[1] else None


def _intersect_many(values: IntervalSet, local: Interval) -> IntervalSet | None:
    clipped = [
        (max(lower, local[0]), min(upper, local[1]))
        for lower, upper in values
        if max(lower, local[0]) <= min(upper, local[1])
    ]
    if not clipped:
        return ()
    clipped.sort()
    merged = [clipped[0]]
    for lower, upper in clipped[1:]:
        prior_lower, prior_upper = merged[-1]
        if lower <= prior_upper:
            merged[-1] = (prior_lower, max(prior_upper, upper))
        else:
            merged.append((lower, upper))
    if len(merged) > MAX_INTERVAL_COMPONENTS_PER_CELL:
        return None
    return tuple(merged)


def _local_interval(
    cell: _Cell,
    *,
    query_pressure: tuple[float, ...],
    query_phase_advance: tuple[float, ...],
    query_phase_prior_pressure: tuple[float, ...],
    reference_index: int,
) -> Interval | None:
    interval: Interval | None = (0.0, 1.0)
    pressure_uncertainty = 2.0 * float(PCM_PRESSURE_QUANTUM)
    for port in range(COCHLEAR_CHANNEL_COUNT):
        left_pressure, left_phase = _branch_sample(
            cell.left, port, reference_index, cell.reference_count
        )
        right_pressure, right_phase = _branch_sample(
            cell.right, port, reference_index, cell.reference_count
        )
        interval = _intersect_lambda(
            interval,
            query=query_pressure[port],
            left=left_pressure,
            right=right_pressure,
            uncertainty=pressure_uncertainty,
        )
        if interval is None:
            return None
        phase_uncertainty = _phase_uncertainty(
            query_pressure[port],
            query_phase_prior_pressure[port],
            left_pressure,
            _branch_phase_prior_pressure(
                cell.left, port, reference_index, cell.reference_count
            ),
            right_pressure,
            _branch_phase_prior_pressure(
                cell.right, port, reference_index, cell.reference_count
            ),
        )
        if phase_uncertainty is None:
            continue
        interval = _intersect_lambda(
            interval,
            query=query_phase_advance[port],
            left=left_phase,
            right=right_phase,
            uncertainty=phase_uncertainty,
        )
        if interval is None:
            return None
    return interval


def _cells_from_owner(owner: AuditoryReciprocityOwner) -> tuple[_Cell, ...]:
    snapshot = owner.snapshot()
    if isinstance(snapshot, dict) and snapshot.get("schema") == (
        LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
    ):
        raise ValueError("incremental auditory rejects reciprocity v4 evidence")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema") != AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
        or not isinstance(snapshot.get("classes"), list)
        or snapshot.get("branch_capacity_per_class")
        != MAX_PATH_BRANCHES_PER_CLASS
    ):
        raise ValueError("incremental auditory learning snapshot is invalid")
    cells = []
    for learned in snapshot["classes"]:
        if not isinstance(learned, dict) or learned.get("kind") != (
            AuditoryReciprocityKind.SPOKEN_FORM.value
        ):
            continue
        label = learned.get("tutor_label")
        raw_branches = learned.get("branches")
        if (
            not isinstance(label, str)
            or not label
            or not isinstance(raw_branches, list)
            or not 1 <= len(raw_branches) <= MAX_PATH_BRANCHES_PER_CLASS
        ):
            raise ValueError("incremental auditory learned class is malformed")
        branches = tuple(_branch_from_snapshot(value) for value in raw_branches)

        def physical_topology(branch: _Branch) -> tuple[object, ...]:
            return tuple(
                (
                    channel[0],
                    channel[1],
                    channel[2][:6],
                    channel[3][:6],
                )
                for channel in branch.topology
            )

        if any(
            physical_topology(branch) != physical_topology(branches[0])
            for branch in branches[1:]
        ):
            raise ValueError("incremental auditory learned topology changed")
        for left_index, left in enumerate(branches):
            for right in branches[left_index:]:
                reference_count = max(left.sample_count, right.sample_count)
                cells.append(_Cell(
                    tutor_label=label,
                    left=left,
                    right=right,
                    reference_count=reference_count,
                    terminal_floor=min(left.sample_count, right.sample_count),
                    # This compatibility field is not used by the live path.
                    # The native state owner receives the exact branch-
                    # fingerprint relation and constructs the same recurrence
                    # graph once with its immutable cell.
                    recurrence_incoming=tuple(
                        () for _ in range(reference_count)
                    ),
                ))
    return tuple(cells)


def _advance_row(
    cell: _Cell,
    previous: tuple[IntervalSet, ...] | None,
    *,
    pressure: tuple[float, ...],
    phase_advance: tuple[float, ...],
    phase_prior_pressure: tuple[float, ...],
) -> tuple[IntervalSet, ...] | None:
    current: list[IntervalSet] = [() for _ in range(cell.reference_count)]
    for reference_index in range(cell.reference_count):
        if previous is None and reference_index == 0:
            predecessors: IntervalSet = ((0.0, 1.0),)
        else:
            incoming = []
            if previous is not None:
                incoming.extend(previous[reference_index])
            if reference_index > 0:
                incoming.extend(current[reference_index - 1])
            if previous is not None and reference_index > 0:
                incoming.extend(previous[reference_index - 1])
            if previous is not None:
                for recurrent in cell.recurrence_incoming[reference_index]:
                    incoming.extend(previous[recurrent])
            predecessors = tuple(incoming)
        if not predecessors:
            continue
        local = _local_interval(
            cell,
            query_pressure=pressure,
            query_phase_advance=phase_advance,
            query_phase_prior_pressure=phase_prior_pressure,
            reference_index=reference_index,
        )
        if local is None:
            continue
        intersected = _intersect_many(predecessors, local)
        if intersected is None:
            return None
        current[reference_index] = intersected
    return tuple(current)


class AuditoryIncrementalTerminalOwner:
    """Bounded 10 ms proposal automaton with a full-field positive gate."""

    def __init__(
        self,
        *,
        reciprocity_owner: AuditoryReciprocityOwner,
        max_active_trackers: int = MAX_ACTIVE_TRACKERS,
        released_terminal_capacity: int = MAX_RELEASED_TERMINALS_PER_ADVANCE,
        log_event=None,
        _prepared_cells: tuple[_Cell, ...] | None = None,
    ) -> None:
        if not isinstance(reciprocity_owner, AuditoryReciprocityOwner):
            raise TypeError("incremental terminal requires reciprocity ownership")
        if (
            isinstance(max_active_trackers, bool)
            or not isinstance(max_active_trackers, int)
            or max_active_trackers <= 0
            or max_active_trackers > MAX_ACTIVE_TRACKERS
        ):
            raise ValueError("incremental tracker capacity is invalid")
        if (
            isinstance(released_terminal_capacity, bool)
            or not isinstance(released_terminal_capacity, int)
            or released_terminal_capacity <= 0
            or released_terminal_capacity
            > MAX_RELEASED_TERMINALS_PER_ADVANCE
        ):
            raise ValueError("incremental released-terminal capacity is invalid")
        self._reciprocity_owner = reciprocity_owner
        self._max_active_trackers = max_active_trackers
        self._released_terminal_capacity = released_terminal_capacity
        self._log_event = log_event or (lambda *_args, **_kwargs: None)
        self._cells = (
            _cells_from_owner(reciprocity_owner)
            if _prepared_cells is None else _prepared_cells
        )
        if self._cells and _NativeIncrementalProposalCells is None:
            raise RuntimeError(
                "learned incremental auditory perception requires the exact "
                "native proposal kernel"
            )
        self._native_proposals = self._new_native_proposal_owner()
        self._lock = threading.RLock()
        self._released_full_fields: dict[str, AuditoryL5Experience] = {}
        self._clear_live_state()

    def _new_native_proposal_owner(self):
        return (
            _NativeIncrementalProposalCells([
                (
                    [
                        [
                            coordinate
                            for observation in port
                            for coordinate in observation
                        ]
                        for port in cell.left.values
                    ],
                    cell.left.sample_count,
                    [
                        [
                            coordinate
                            for observation in port
                            for coordinate in observation
                        ]
                        for port in cell.right.values
                    ],
                    cell.right.sample_count,
                    cell.terminal_floor,
                    cell.left.structural_fingerprint
                    == cell.right.structural_fingerprint,
                )
                for cell in self._cells
            ])
            if self._cells else None
        )

    def _clear_live_state(self) -> None:
        if (
            hasattr(self, "_native_proposals")
            and self._native_proposals is not None
        ):
            self._native_proposals.clear()
        self._stream_id: str | None = None
        self._last_transport: AuditoryPCMContinuityReceipt | None = None
        self._last_cochlear: AuditoryGammatoneContinuationReceipt | None = None
        self._last_result: AuditoryIncrementalAdvance | None = None
        self._last_committed_receipt_sha256: str | None = None
        self._buffer_start = 0
        self._pcm = bytearray()
        self._evidence: list[_Evidence] = []
        self._frames: list[_Frame] = []
        self._pending: dict[int, _PendingTerminal] = {}

    def _transaction_checkpoint(self) -> _OwnerLiveStateCheckpoint:
        native_starts = (
            tuple(self._native_proposals.active_starts)
            if self._native_proposals is not None else ()
        )
        native_count = (
            self._native_proposals.active_tracker_count
            if self._native_proposals is not None else 0
        )
        if native_count > MAX_ACTIVE_TRACKERS:
            raise RuntimeError(
                "incremental auditory checkpoint exceeds tracker capacity"
            )
        native_state = (
            self._native_proposals.checkpoint_state()
            if self._native_proposals is not None else None
        )
        return _OwnerLiveStateCheckpoint(
            stream_id=self._stream_id,
            last_transport=self._last_transport,
            last_cochlear=self._last_cochlear,
            last_result=self._last_result,
            last_committed_receipt_sha256=(
                self._last_committed_receipt_sha256
            ),
            buffer_start=self._buffer_start,
            pcm=bytes(self._pcm),
            evidence=tuple(self._evidence),
            frames=tuple(self._frames),
            pending=tuple(self._pending.items()),
            released_full_fields=tuple(self._released_full_fields.items()),
            native_active_starts=native_starts,
            native_active_tracker_count=native_count,
            native_state=native_state,
        )

    def _restore_transaction_checkpoint(
        self, checkpoint: _OwnerLiveStateCheckpoint
    ) -> None:
        if not isinstance(checkpoint, _OwnerLiveStateCheckpoint):
            raise TypeError("incremental auditory checkpoint is invalid")
        native = checkpoint.native_state
        if native is None:
            if (
                checkpoint.native_active_starts
                or checkpoint.native_active_tracker_count
            ):
                raise RuntimeError(
                    "incremental auditory checkpoint lost its learned cells"
                )
        else:
            if (
                tuple(native.active_starts)
                != checkpoint.native_active_starts
                or native.active_tracker_count
                != checkpoint.native_active_tracker_count
            ):
                raise RuntimeError(
                    "incremental auditory native rollback changed state"
                )

        self._native_proposals = native
        self._stream_id = checkpoint.stream_id
        self._last_transport = checkpoint.last_transport
        self._last_cochlear = checkpoint.last_cochlear
        self._last_result = checkpoint.last_result
        self._last_committed_receipt_sha256 = (
            checkpoint.last_committed_receipt_sha256
        )
        self._buffer_start = checkpoint.buffer_start
        self._pcm = bytearray(checkpoint.pcm)
        self._evidence = list(checkpoint.evidence)
        self._frames = list(checkpoint.frames)
        self._pending = dict(checkpoint.pending)
        self._released_full_fields = dict(checkpoint.released_full_fields)

    @property
    def active_tracker_count(self) -> int:
        with self._lock:
            return (
                self._native_proposals.active_tracker_count
                if self._native_proposals is not None else 0
            )

    @property
    def retained_sample_count(self) -> int:
        with self._lock:
            return len(self._pcm) // 2

    @property
    def learned_cell_count(self) -> int:
        return len(self._cells)

    def snapshot(self) -> dict[str, object]:
        return {
            "active_state_persisted": False,
            "learned_cell_count": len(self._cells),
            "schema": "guala.auditory.incremental_snapshot.v1",
        }

    def _make_result(
        self,
        status: AuditoryIncrementalStatus,
        *,
        released_terminals: tuple[
            AuditoryIncrementalTerminalEvent, ...
        ] = (),
        processed_hops: int = 0,
    ) -> AuditoryIncrementalAdvance:
        payload = _advance_payload(
            status=status,
            released_terminals=released_terminals,
            processed_hops=processed_hops,
            active_tracker_count=self.active_tracker_count,
        )
        result = AuditoryIncrementalAdvance(
            status=status,
            released_terminals=released_terminals,
            processed_hops=processed_hops,
            active_tracker_count=self.active_tracker_count,
            authority_receipt_sha256=_digest(payload),
        )
        result.verify()
        self._last_result = result
        return result

    @staticmethod
    def _frame_values(
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
    ) -> tuple[
        tuple[
            int,
            tuple[float, ...],
            tuple[float, ...],
            tuple[float, ...],
        ], ...
    ]:
        auditory_l5.verify()
        if (
            len(auditory_l5.channels) != COCHLEAR_CHANNEL_COUNT
            or not auditory_l5.receipt_registry.resolve(
                auditory_l5.authority_receipt_sha256,
                "incremental auditory L5 v3 authority",
            )
        ):
            raise ValueError("incremental auditory requires paired L5 v3")
        if any(
            len(component.samples) != capture.frame_count
            or not component.l4_field_tuples
            or tuple(
                value.tuple_index for value in component.l4_field_tuples
            ) != tuple(range(len(component.l4_field_tuples)))
            or any(
                tuple(name for name, _ in value.fields) != DSF_FIELD_ORDER
                for value in component.l4_field_tuples
            )
            for channel in auditory_l5.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
        ):
            raise ValueError(
                "incremental auditory requires two complete independent L4 banks"
            )
        completions = []
        for offset_ns in capture.channels[0].causal_offsets_ns:
            numerator = offset_ns * PCM_SAMPLE_RATE_HZ
            if numerator % 1_000_000_000:
                raise ValueError("incremental auditory frame left the native grid")
            completions.append(numerator // 1_000_000_000)
        frames = []
        for frame_index, completion in enumerate(completions):
            pressures = []
            phase_advances = []
            normalized_phase_advances = []
            for channel_index, (source, settled) in enumerate(
                zip(capture.channels, auditory_l5.channels, strict=True)
            ):
                pressure = settled.pressure
                phase = settled.carrier_phase_advance
                pressure_sample = pressure.samples[frame_index]
                phase_sample = phase.samples[frame_index]
                if (
                    settled.cochlear_index != channel_index
                    or settled.channel_id != source.definition.name
                    or pressure.kind is not AuditoryL5ComponentKind.PRESSURE
                    or phase.kind
                    is not AuditoryL5ComponentKind.CARRIER_PHASE_ADVANCE
                    or pressure_sample.source_index != frame_index
                    or phase_sample.source_index != frame_index
                    or Fraction.from_float(
                        source.pressure_envelope_full_scale[frame_index]
                    ) != pressure_sample.signal
                    or pressure_sample.phase_turns != 0
                    or Fraction.from_float(
                        source.carrier_phase_advance_turns[frame_index]
                    ) != phase_sample.phase_turns
                    or Fraction.from_float(
                        source.carrier_phase_advance_nyquist_fraction[
                            frame_index
                        ]
                    ) != phase_sample.signal
                    or float(phase_sample.signal)
                    != float(phase_sample.phase_turns)
                    / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                ):
                    raise ValueError(
                        "incremental auditory capture differs from settled L5"
                    )
                pressures.append(float(pressure_sample.signal))
                phase_advances.append(float(phase_sample.phase_turns))
                normalized_phase_advances.append(float(phase_sample.signal))
            frames.append((
                completion,
                tuple(pressures),
                tuple(phase_advances),
                tuple(normalized_phase_advances),
            ))
        return tuple(frames)

    @staticmethod
    def _verify_chunk(
        pcm_s16le: bytes,
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint: AuditoryStreamSettlementReceipt,
    ) -> tuple[
        tuple[
            int,
            tuple[float, ...],
            tuple[float, ...],
            tuple[float, ...],
        ], ...
    ]:
        if not isinstance(transport, AuditoryPCMContinuityReceipt):
            raise TypeError("incremental terminal requires typed PCM continuity")
        if not isinstance(cochlear, AuditoryGammatoneContinuationReceipt):
            raise TypeError("incremental terminal requires typed cochlear continuity")
        if not isinstance(joint, AuditoryStreamSettlementReceipt):
            raise TypeError("incremental terminal requires typed joint settlement")
        if not isinstance(capture, AuditoryFullFieldCapture):
            raise TypeError("incremental terminal requires typed cochlear frames")
        if not isinstance(auditory_l5, AuditoryL5Experience):
            raise TypeError("incremental terminal requires typed auditory L5")
        transport.verify()
        cochlear.verify()
        joint.verify()
        auditory_l5.verify()
        if (
            not isinstance(pcm_s16le, bytes)
            or len(pcm_s16le) != transport.sample_count * 2
            or hashlib.sha256(pcm_s16le).hexdigest() != transport.pcm_sha256
        ):
            raise ValueError("incremental auditory PCM differs from transport")
        if (
            capture.source_first_sample_index != transport.first_sample_index
            or capture.input_sample_count != transport.sample_count
            or capture.continuation_receipt_sha256 != cochlear.receipt_sha256
            or cochlear.stream_id != transport.stream_id
            or cochlear.sequence != transport.sequence
            or cochlear.first_sample_index != transport.first_sample_index
            or cochlear.sample_count != transport.sample_count
            or cochlear.transport_receipt_sha256 != transport.receipt_sha256
            or joint.stream_id != transport.stream_id
            or joint.sequence != transport.sequence
            or joint.first_sample_index != transport.first_sample_index
            or joint.sample_count != transport.sample_count
            or joint.transport_receipt_sha256 != transport.receipt_sha256
            or joint.cochlear_receipt_sha256 != cochlear.receipt_sha256
            or joint.auditory_l5_authority_receipt_sha256
            != auditory_l5.authority_receipt_sha256
            or joint.assembly_id != auditory_l5.assembly_id
        ):
            raise ValueError("incremental auditory authorities are not joint")
        expected_start = Fraction(
            transport.source_epoch_start_ns,
            1_000_000_000,
        ) + Fraction(transport.first_sample_index, PCM_SAMPLE_RATE_HZ)
        expected_end = expected_start + Fraction(
            transport.sample_count, PCM_SAMPLE_RATE_HZ
        )
        if (
            joint.source_time_start != expected_start
            or joint.source_time_end != expected_end
            or auditory_l5.source_time_start != expected_start
            or auditory_l5.source_time_end != expected_end
        ):
            raise ValueError("incremental auditory source interval changed")
        frames = AuditoryIncrementalTerminalOwner._frame_values(
            capture, auditory_l5
        )
        if not frames:
            raise ValueError("incremental auditory chunk has no completed hop")
        if (
            frames[0][0] <= transport.first_sample_index
            or frames[-1][0] > transport.last_sample_index_exclusive
            or any(
                right[0] - left[0] != OBSERVATION_HOP_SAMPLES
                for left, right in zip(frames, frames[1:], strict=False)
            )
        ):
            raise ValueError("incremental auditory hop identity changed")
        return frames

    def _is_continuous(
        self,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
    ) -> bool:
        prior_transport = self._last_transport
        prior_cochlear = self._last_cochlear
        return bool(
            prior_transport is not None
            and prior_cochlear is not None
            and transport.stream_id == prior_transport.stream_id
            and transport.source_epoch_start_ns
            == prior_transport.source_epoch_start_ns
            and transport.sequence == prior_transport.sequence + 1
            and transport.first_sample_index
            == prior_transport.last_sample_index_exclusive
            and transport.prior_receipt_sha256
            == prior_transport.receipt_sha256
            and cochlear.prior_state_receipt_sha256
            == prior_cochlear.receipt_sha256
        )

    def _append_pcm(
        self,
        pcm_s16le: bytes,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint: AuditoryStreamSettlementReceipt,
    ) -> bool:
        if not self._pcm:
            self._buffer_start = transport.first_sample_index
        expected = self._buffer_start + len(self._pcm) // 2
        if transport.first_sample_index != expected:
            raise RuntimeError("incremental auditory rolling PCM lost continuity")
        self._pcm.extend(pcm_s16le)
        self._evidence.append(_Evidence(
            start=transport.first_sample_index,
            end=transport.last_sample_index_exclusive,
            transport=transport.receipt_sha256,
            cochlear=cochlear.receipt_sha256,
            joint=joint.authority_receipt_sha256,
        ))
        current_end = transport.last_sample_index_exclusive
        keep_from = max(0, current_end - MAX_EVENT_SAMPLES)
        if keep_from <= self._buffer_start:
            return False
        drop = keep_from - self._buffer_start
        del self._pcm[:drop * 2]
        self._buffer_start = keep_from
        self._evidence = [value for value in self._evidence if value.end > keep_from]
        self._frames = [
            value for value in self._frames
            if value.completion_sample > keep_from
        ]
        expired = (
            self._native_proposals.expire_before(keep_from)
            if self._native_proposals is not None else False
        )
        if any(start < keep_from for start in self._pending):
            expired = True
            self._pending = {
                start: value
                for start, value in self._pending.items()
                if start >= keep_from
            }
        return expired

    def _candidate_pcm(self, start: int, end: int) -> bytes:
        first = start - self._buffer_start
        last = end - self._buffer_start
        if first < 0 or last <= first or last * 2 > len(self._pcm):
            raise RuntimeError("incremental auditory candidate left PCM retention")
        return bytes(self._pcm[first * 2:last * 2])

    def _candidate_evidence(
        self, start: int, end: int
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        values = [
            value for value in self._evidence
            if value.start < end and value.end > start
        ]
        if not values:
            raise RuntimeError("incremental auditory candidate has no evidence")
        return (
            tuple(value.transport for value in values),
            tuple(value.cochlear for value in values),
            tuple(value.joint for value in values),
        )

    def _full_gate(
        self, start: int, end: int, *, max_work: int
    ) -> tuple[AuditoryRecognitionState, _PendingTerminal | None, int]:
        if self._stream_id is None:
            raise RuntimeError("incremental auditory candidate has no stream")
        # Retained PCM proves exact sample identity, but the candidate field is
        # rebuilt from the already-continuous cochlear frames.  Resetting the
        # gammatone recurrence at ``start`` would fabricate a different sense.
        pcm_sha256 = hashlib.sha256(self._candidate_pcm(start, end)).hexdigest()
        selected = tuple(
            value for value in self._frames
            if start < value.completion_sample <= end
        )
        if (
            not selected
            or selected[0].completion_sample
            != start + OBSERVATION_HOP_SAMPLES
            or selected[-1].completion_sample != end
            or len(selected) != (end - start) // OBSERVATION_HOP_SAMPLES
        ):
            raise RuntimeError("incremental auditory candidate frame extent changed")
        epoch_start = self._evidence_epoch_start()
        components = []
        source_times = tuple(
            epoch_start
            + Fraction(value.completion_sample, PCM_SAMPLE_RATE_HZ)
            for value in selected
        )
        zero_phase = (Fraction(0),) * len(selected)
        for channel_index, definition in enumerate(AUDITORY_CHANNELS):
            event_phase_advances, event_normalized_phase_advances = (
                _event_local_phase_component(selected, channel_index)
            )
            pressure_index = channel_index * 2
            phase_index = pressure_index + 1
            common_coordinates = (
                NativeAxisCoordinate("cochlear-channel", definition.name),
            )
            fixed_coordinates = (
                NativeAxisCoordinate("centre-hz", str(definition.centre_hz)),
                NativeAxisCoordinate(
                    "erb-width-hz", str(definition.erb_width_hz)
                ),
                NativeAxisCoordinate("gammatone-order", "4"),
                NativeAxisCoordinate(
                    "observation-hop-samples",
                    str(OBSERVATION_HOP_SAMPLES),
                ),
            )
            components.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id=AUDITORY_KERNEL_SENSOR_ID,
                substream_id=f"{definition.name}_pressure",
                topology_index=pressure_index,
                coordinates=(
                    *common_coordinates,
                    NativeAxisCoordinate(
                        "kernel-component", "pressure-envelope"
                    ),
                    *fixed_coordinates,
                ),
                physical_quantity="cochlear-pressure-envelope",
                physical_unit="full-scale-pressure",
                source_times=source_times,
                normalized_signal=tuple(
                    value.pressure[channel_index] for value in selected
                ),
                phase_turns=zero_phase,
            ))
            components.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id=AUDITORY_KERNEL_SENSOR_ID,
                substream_id=f"{definition.name}_phase_advance",
                topology_index=phase_index,
                coordinates=(
                    *common_coordinates,
                    NativeAxisCoordinate(
                        "kernel-component", "carrier-phase-advance"
                    ),
                    *fixed_coordinates,
                ),
                physical_quantity="cochlear-carrier-phase-advance",
                physical_unit="nyquist-fraction-per-observation-hop",
                source_times=source_times,
                normalized_signal=event_normalized_phase_advances,
                phase_turns=tuple(
                    Fraction.from_float(value)
                    for value in event_phase_advances
                ),
            ))
        if (
            len(components) != AUDITORY_KERNEL_COMPONENT_COUNT
            or tuple(value.topology_index for value in components)
            != tuple(range(AUDITORY_KERNEL_COMPONENT_COUNT))
        ):
            raise RuntimeError(
                "incremental auditory full gate lost paired topology"
            )
        identity = _digest({
            "pcm_sha256": pcm_sha256,
            "source_sample_end": end,
            "source_sample_start": start,
            "stream_id": self._stream_id,
        })
        built = build_six_sense_full_field(
            assembly_id=f"auditory-incremental-{identity}",
            source_time_start=(
                epoch_start + Fraction(start, PCM_SAMPLE_RATE_HZ)
            ),
            source_time_end=epoch_start + Fraction(end, PCM_SAMPLE_RATE_HZ),
            observed_substreams={PhysicalSense.SOUND: tuple(components)},
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.SOUND
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        experience = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        ).settle(built, event_boundary="utterance")
        if experience is None:
            raise RuntimeError("incremental auditory candidate did not settle")
        experience.verify()
        recognition, consumed_cells = (
            self._reciprocity_owner.recognize_bounded(
            experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            max_work=max_work,
        ))
        if recognition.state is not AuditoryRecognitionState.UNIQUE:
            return recognition.state, None, consumed_cells
        if not recognition.tutor_label:
            raise RuntimeError("unique incremental recognition has no tutor label")
        transport, cochlear, joint = self._candidate_evidence(start, end)
        return recognition.state, _PendingTerminal(
            start=start,
            end=end,
            tutor_label=recognition.tutor_label,
            structural_fingerprint=experience.structural_fingerprint,
            l5_authority_receipt_sha256=experience.authority_receipt_sha256,
            transport_receipt_sha256s=transport,
            cochlear_receipt_sha256s=cochlear,
            joint_settlement_receipt_sha256s=joint,
            recognition_occurrence=recognition.occurrence,
            auditory_l5=experience,
        ), consumed_cells

    def _evidence_epoch_start(self) -> Fraction:
        if self._last_transport is None:
            raise RuntimeError("incremental auditory stream has no time authority")
        return Fraction(
            self._last_transport.source_epoch_start_ns,
            1_000_000_000,
        )

    def _event(self, value: _PendingTerminal) -> AuditoryIncrementalTerminalEvent:
        if self._stream_id is None:
            raise RuntimeError("incremental auditory terminal has no stream")
        event_id = _digest({
            "source_sample_end": value.end,
            "source_sample_start": value.start,
            "stream_id": self._stream_id,
            "structural_fingerprint": value.structural_fingerprint,
        })
        payload = _event_payload(
            event_id=event_id,
            stream_id=self._stream_id,
            source_sample_start=value.start,
            source_sample_end=value.end,
            tutor_label=value.tutor_label,
            structural_fingerprint=value.structural_fingerprint,
            l5_authority_receipt_sha256=value.l5_authority_receipt_sha256,
            transport_receipt_sha256s=value.transport_receipt_sha256s,
            cochlear_receipt_sha256s=value.cochlear_receipt_sha256s,
            joint_settlement_receipt_sha256s=(
                value.joint_settlement_receipt_sha256s
            ),
            recognition_occurrence=value.recognition_occurrence,
            schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
            l5_schema=AUDITORY_L5_SCHEMA,
            reciprocity_snapshot_schema=(
                AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
            ),
            recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
        )
        event = AuditoryIncrementalTerminalEvent(
            event_id=event_id,
            stream_id=self._stream_id,
            source_sample_start=value.start,
            source_sample_end=value.end,
            tutor_label=value.tutor_label,
            structural_fingerprint=value.structural_fingerprint,
            l5_authority_receipt_sha256=value.l5_authority_receipt_sha256,
            transport_receipt_sha256s=value.transport_receipt_sha256s,
            cochlear_receipt_sha256s=value.cochlear_receipt_sha256s,
            joint_settlement_receipt_sha256s=(
                value.joint_settlement_receipt_sha256s
            ),
            schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
            recognition_occurrence=value.recognition_occurrence,
            l5_schema=AUDITORY_L5_SCHEMA,
            reciprocity_snapshot_schema=(
                AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
            ),
            recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
            authority_receipt_sha256=_digest(payload),
        )
        event.verify()
        existing = self._released_full_fields.get(event.event_id)
        if existing is not None and existing != value.auditory_l5:
            raise RuntimeError(
                "incremental auditory terminal released two full fields"
            )
        if (
            existing is None
            and len(self._released_full_fields)
            >= self._released_terminal_capacity
        ):
            raise RuntimeError(
                "incremental auditory released-field capacity is full"
            )
        self._released_full_fields[event.event_id] = value.auditory_l5
        return event

    def claim_released_full_field(
        self,
        event: AuditoryIncrementalTerminalEvent,
    ) -> AuditoryL5Experience:
        """Transfer the exact field released with one terminal event."""
        event.verify()
        if event.schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3:
            raise ValueError(
                "legacy incremental auditory audit record is not live authority"
            )
        with self._lock:
            experience = self._released_full_fields.pop(event.event_id, None)
        if experience is None:
            raise ValueError(
                "incremental auditory terminal has no released full field"
            )
        experience.verify()
        if (
            experience.event_boundary != "utterance"
            or experience.structural_fingerprint
            != event.structural_fingerprint
            or experience.authority_receipt_sha256
            != event.l5_authority_receipt_sha256
            or experience.source_time_end - experience.source_time_start
            != Fraction(event.sample_count, PCM_SAMPLE_RATE_HZ)
        ):
            raise ValueError(
                "incremental auditory terminal field authority changed"
            )
        return experience

    def _spawn(
        self,
        completion: int,
        pressure: tuple[float, ...],
        phase_advance: tuple[float, ...],
    ) -> None:
        start = completion - OBSERVATION_HOP_SAMPLES
        pressure_uncertainty = 2.0 * float(PCM_PRESSURE_QUANTUM)
        for cell_index, cell in enumerate(self._cells):
            interval: Interval | None = (0.0, 1.0)
            for port in range(COCHLEAR_CHANNEL_COUNT):
                left, _ = _branch_sample(
                    cell.left, port, 0, cell.reference_count
                )
                right, _ = _branch_sample(
                    cell.right, port, 0, cell.reference_count
                )
                interval = _intersect_lambda(
                    interval,
                    query=pressure[port],
                    left=left,
                    right=right,
                    uncertainty=pressure_uncertainty,
                )
                if interval is None:
                    break
            if interval is not None:
                self._trackers.append(_Tracker(
                    cell_index=cell_index,
                    start_sample=start,
                    frames_seen=1,
                    first_pressure=pressure,
                    first_phase_advance=phase_advance,
                    previous_pressure=pressure,
                    previous_phase_advance=phase_advance,
                    row=None,
                ))

    def _advance_tracker(
        self,
        tracker: _Tracker,
        pressure: tuple[float, ...],
        phase_advance: tuple[float, ...],
    ) -> bool | None:
        cell = self._cells[tracker.cell_index]
        if tracker.row is None:
            first_row = _advance_row(
                cell,
                None,
                pressure=tracker.first_pressure,
                phase_advance=tracker.first_phase_advance,
                phase_prior_pressure=pressure,
            )
            if first_row is None:
                return None
            if not any(first_row):
                return False
            row = _advance_row(
                cell,
                first_row,
                pressure=pressure,
                phase_advance=phase_advance,
                phase_prior_pressure=tracker.first_pressure,
            )
        else:
            row = _advance_row(
                cell,
                tracker.row,
                pressure=pressure,
                phase_advance=phase_advance,
                phase_prior_pressure=tracker.previous_pressure,
            )
        if row is None:
            return None
        if not any(row):
            return False
        tracker.row = row
        tracker.frames_seen += 1
        tracker.previous_pressure = pressure
        tracker.previous_phase_advance = phase_advance
        return bool(
            tracker.frames_seen >= cell.terminal_floor and row[-1]
        )

    @staticmethod
    def _resolve_closed(
        values: list[_PendingTerminal],
    ) -> tuple[_PendingTerminal | None, bool]:
        if not values:
            return None, False
        labels = {value.tutor_label for value in values}
        if len(labels) != 1:
            return None, True
        ordered = sorted(
            values,
            key=lambda value: (
                value.end - value.start,
                -value.start,
                value.structural_fingerprint,
            ),
            reverse=True,
        )
        return ordered[0], False

    def _process_frame(
        self,
        completion: int,
        pressure: tuple[float, ...],
        phase_advance: tuple[float, ...],
        full_gate_work: _AdvanceFullGateWorkLedger,
    ) -> tuple[_PendingTerminal | None, bool, bool]:
        if self._native_proposals is None:
            raise RuntimeError(
                "incremental auditory proposal owner has no learned cells"
            )
        prior_pending = dict(self._pending)
        (
            terminal_spans,
            remove_pending_starts,
            resource,
            clear_all_state,
            _proposal_work_cells,
            _active_tracker_count,
            _active_starts,
        ) = self._native_proposals.step(
            completion,
            list(pressure),
            list(phase_advance),
            [
                (start, pending.end)
                for start, pending in self._pending.items()
            ],
            self._max_active_trackers,
            MAX_REACHABILITY_CELLS_PER_RECOGNITION,
            MAX_INTERVAL_COMPONENTS_PER_CELL,
        )
        closed_pending_starts = set(remove_pending_starts)
        for start in closed_pending_starts:
            self._pending.pop(start, None)
        if clear_all_state:
            self._native_proposals.clear()
            self._pending.clear()
            return None, False, True

        ambiguous = False
        rejected_starts = set()
        for start, end in sorted(terminal_spans):
            span = end - start
            if span <= 0 or span % OBSERVATION_HOP_SAMPLES:
                raise RuntimeError("incremental auditory gate extent changed")
            field_samples = (
                span // OBSERVATION_HOP_SAMPLES
                * AUDITORY_KERNEL_COMPONENT_COUNT
            )
            if not full_gate_work.reserve_field_samples(field_samples):
                self._native_proposals.clear()
                self._pending.clear()
                return None, False, True
            state, pending, consumed_cells = self._full_gate(
                start,
                end,
                max_work=full_gate_work.remaining_reachability,
            )
            full_gate_work.charge_reachability(consumed_cells)
            if state is AuditoryRecognitionState.UNIQUE:
                if pending is None:
                    raise RuntimeError("unique full-field gate lost its terminal")
                self._pending[start] = pending
            elif state is AuditoryRecognitionState.AMBIGUOUS:
                self._pending.pop(start, None)
                rejected_starts.add(start)
                ambiguous = True
            elif state is AuditoryRecognitionState.INDETERMINATE:
                self._pending.pop(start, None)
                rejected_starts.add(start)
                resource = True
            else:
                if start in self._pending:
                    prior_pending[start] = self._pending.pop(start)
                rejected_starts.add(start)
        if rejected_starts:
            self._native_proposals.discard_starts(sorted(rejected_starts))
        active_starts = set(self._native_proposals.active_starts)
        closed = []
        for start, pending in tuple(prior_pending.items()):
            if (
                start in closed_pending_starts
                or (start not in active_starts and start not in self._pending)
            ):
                closed.append(pending)
        # A closed interval cannot be released independently of a still-live
        # full-field identity whose physical interval overlaps it.  Those
        # candidates are one contemporaneous causal component.  Resolve the
        # component by learned identity only after every proposal ending on
        # this frame has passed the full field; proposal iteration order never
        # owns segmentation or meaning.
        overlap_pending = [
            pending for pending in self._pending.values()
            if any(
                pending.start < closed_value.end
                and closed_value.start < pending.end
                for closed_value in closed
            )
        ]
        component = [*closed, *overlap_pending]
        component_labels = {value.tutor_label for value in component}
        closure_ambiguity = len(component_labels) > 1
        chosen, closed_ambiguity = self._resolve_closed(closed)
        closure_ambiguity = closure_ambiguity or closed_ambiguity
        ambiguous = ambiguous or closure_ambiguity
        if chosen is not None and not closure_ambiguity and not ambiguous:
            self._native_proposals.retain_at_or_after(chosen.end)
            self._pending = {
                start: value for start, value in self._pending.items()
                if start >= chosen.end
            }
        elif component and ambiguous:
            component_end = max(value.end for value in component)
            self._native_proposals.retain_at_or_after(component_end)
            self._pending = {
                start: value for start, value in self._pending.items()
                if start >= component_end
            }
            chosen = None
        return chosen, ambiguous, resource

    def advance(
        self,
        *,
        pcm_s16le: bytes,
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
    ) -> AuditoryIncrementalAdvance:
        # Verification is intentionally before duplicate recognition: the
        # receipt alone cannot authorize a result for different chunk bytes or
        # a different full-field graph.
        self._verify_chunk(
            pcm_s16le,
            capture,
            auditory_l5,
            transport,
            cochlear,
            joint_settlement,
        )
        with self._lock:
            if (
                transport.receipt_sha256
                == self._last_committed_receipt_sha256
            ):
                if self._last_result is None:
                    raise RuntimeError(
                        "incremental auditory committed retry has no result"
                    )
                return self._last_result
            checkpoint = self._transaction_checkpoint()
            try:
                result = self._advance_untransactional(
                    pcm_s16le=pcm_s16le,
                    capture=capture,
                    auditory_l5=auditory_l5,
                    transport=transport,
                    cochlear=cochlear,
                    joint_settlement=joint_settlement,
                )
            except Exception as advance_error:
                try:
                    self._restore_transaction_checkpoint(checkpoint)
                except Exception as rollback_error:
                    raise ExceptionGroup(
                        "incremental auditory advance and rollback failed",
                        [advance_error, rollback_error],
                    )
                raise
            self._last_committed_receipt_sha256 = transport.receipt_sha256
            return result

    def _advance_untransactional(
        self,
        *,
        pcm_s16le: bytes,
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
    ) -> AuditoryIncrementalAdvance:
        frames = self._verify_chunk(
            pcm_s16le,
            capture,
            auditory_l5,
            transport,
            cochlear,
            joint_settlement,
        )
        with self._lock:
            if (
                self._last_committed_receipt_sha256 is not None
                and transport.receipt_sha256
                == self._last_committed_receipt_sha256
            ):
                if self._last_result is None:
                    raise RuntimeError("incremental auditory retry has no result")
                return self._last_result
            first = self._last_transport is None
            valid_first = (
                transport.sequence == 0
                and transport.first_sample_index == 0
                and transport.prior_receipt_sha256 is None
                and cochlear.prior_state_receipt_sha256 is None
            )
            if (first and not valid_first) or (
                not first and not self._is_continuous(transport, cochlear)
            ):
                self._clear_live_state()
                return self._make_result(
                    AuditoryIncrementalStatus.DISCONTINUITY,
                    processed_hops=0,
                )
            if first:
                self._stream_id = transport.stream_id
            self._last_transport = transport
            self._last_cochlear = cochlear
            if not self._cells:
                return self._make_result(
                    AuditoryIncrementalStatus.UNKNOWN,
                    processed_hops=len(frames),
                )
            expired = self._append_pcm(
                pcm_s16le, transport, cochlear, joint_settlement
            )
            self._frames.extend(
                _Frame(completion, pressure, phase_advance, normalized)
                for completion, pressure, phase_advance, normalized in frames
            )
            released = []
            ambiguous = False
            resource = expired
            processed_hops = 0
            full_gate_work = _AdvanceFullGateWorkLedger(
                reachability_limit=MAX_FULL_GATE_WORK_PER_ADVANCE,
                field_sample_limit=MAX_FULL_GATE_FIELD_SAMPLES_PER_ADVANCE,
            )
            if resource:
                if self._native_proposals is not None:
                    self._native_proposals.clear()
                self._pending.clear()
            else:
                for completion, pressure, phase_advance, _normalized in frames:
                    processed_hops += 1
                    terminal, frame_ambiguous, frame_resource = (
                        self._process_frame(
                            completion,
                            pressure,
                            phase_advance,
                            full_gate_work,
                        )
                    )
                    ambiguous = ambiguous or frame_ambiguous
                    resource = resource or frame_resource
                    if frame_resource:
                        released.clear()
                        self._native_proposals.clear()
                        self._pending.clear()
                        break
                    if terminal is not None:
                        released.append(terminal)
                    if (
                        len(released)
                        > self._released_terminal_capacity
                        - len(self._released_full_fields)
                    ):
                        released.clear()
                        resource = True
                        self._native_proposals.clear()
                        self._pending.clear()
                        break
            if resource:
                terminals: tuple[AuditoryIncrementalTerminalEvent, ...] = ()
            else:
                terminals = tuple(self._event(value) for value in released)
            if resource:
                status = AuditoryIncrementalStatus.INDETERMINATE_RESOURCE
            elif terminals:
                status = AuditoryIncrementalStatus.RELEASED_UNIQUE
            elif ambiguous:
                status = AuditoryIncrementalStatus.AMBIGUOUS
            elif self.active_tracker_count or self._pending:
                status = AuditoryIncrementalStatus.CONTINUING
            else:
                status = AuditoryIncrementalStatus.UNKNOWN
            result = self._make_result(
                status,
                released_terminals=terminals,
                processed_hops=processed_hops,
            )
            self._log_event(
                "auditory_incremental_terminal_advanced",
                status=status.value,
                processed_hops=processed_hops,
                active_tracker_count=self.active_tracker_count,
                reply_candidate_count=(
                    1 if len(terminals) == 1 else 0
                ),
                released_terminal_count=len(terminals),
                full_gate_reachability_cells=(
                    full_gate_work.reachability_consumed
                ),
                full_gate_field_samples=full_gate_work.field_samples_consumed,
            )
            return result

    def close_stream(self) -> AuditoryIncrementalAdvance:
        with self._lock:
            chosen, ambiguous = self._resolve_closed(list(self._pending.values()))
            resource = bool(
                chosen is not None
                and len(self._released_full_fields)
                >= self._released_terminal_capacity
            )
            terminals = (
                (self._event(chosen),)
                if chosen is not None and not resource else ()
            )
            self._clear_live_state()
            status = (
                AuditoryIncrementalStatus.INDETERMINATE_RESOURCE
                if resource
                else AuditoryIncrementalStatus.RELEASED_UNIQUE
                if terminals
                else AuditoryIncrementalStatus.AMBIGUOUS
                if ambiguous
                else AuditoryIncrementalStatus.UNKNOWN
            )
            return self._make_result(status, released_terminals=terminals)


@dataclass(slots=True)
class _OwnedIncrementalTerminal:
    owner: AuditoryIncrementalTerminalOwner
    last_activity: float


@dataclass(slots=True)
class _AuditoryTerminalClaim:
    event: AuditoryIncrementalTerminalEvent
    auditory_l5: AuditoryL5Experience
    owner_token: object
    reservation_token: object
    authority_position: int
    lifecycle: str = "in_flight"
    prepared_causal_settlement: CausalExperienceSettlement | None = None
    causal_settlement: CausalExperienceSettlement | None = None


@dataclass(frozen=True, slots=True)
class _IssuedTerminal:
    event: AuditoryIncrementalTerminalEvent
    auditory_l5: AuditoryL5Experience


@dataclass(frozen=True, slots=True)
class _InFlightTerminal:
    issued: _IssuedTerminal
    reservation_token: object
    authority_position: int


@dataclass(frozen=True, slots=True)
class _InFlightTerminalBatch:
    batch: AuditoryIncrementalTerminalBatch
    reservation_token: object
    authority_positions: tuple[int, ...]


class AuditoryIncrementalTerminalRegistry:
    """Bound one incremental terminal owner to each live PCM stream epoch."""

    def __init__(
        self,
        *,
        reciprocity_owner: AuditoryReciprocityOwner,
        clock=time.monotonic,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        terminal_authority_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
        log_event=None,
    ) -> None:
        if not isinstance(reciprocity_owner, AuditoryReciprocityOwner):
            raise TypeError("incremental registry requires reciprocity ownership")
        if (
            isinstance(stream_capacity, bool)
            or not isinstance(stream_capacity, int)
            or stream_capacity <= 0
            or isinstance(terminal_authority_capacity, bool)
            or not isinstance(terminal_authority_capacity, int)
            or terminal_authority_capacity <= 0
            or terminal_authority_capacity
            > MAX_RELEASED_TERMINALS_PER_ADVANCE
            or isinstance(idle_seconds, bool)
            or not isinstance(idle_seconds, int)
            or idle_seconds <= 0
        ):
            raise ValueError("incremental registry bounds must be positive")
        self._reciprocity_owner = reciprocity_owner
        self._clock = clock
        self._stream_capacity = stream_capacity
        self._terminal_authority_capacity = terminal_authority_capacity
        self._idle_seconds = idle_seconds
        self._log_event = log_event or (lambda *_args, **_kwargs: None)
        self._lock = threading.RLock()
        self._cells = _cells_from_owner(reciprocity_owner)
        self._streams: OrderedDict[str, _OwnedIncrementalTerminal] = (
            OrderedDict()
        )
        self._issued: OrderedDict[str, _IssuedTerminal] = OrderedDict()
        self._in_flight: OrderedDict[str, _InFlightTerminal] = OrderedDict()
        self._in_flight_batches: OrderedDict[
            str, _InFlightTerminalBatch
        ] = OrderedDict()
        self._authority_order: list[str] = []
        self._claim_token = object()
        self._batch_claim_token = object()
        batch_root = secrets.token_bytes(32)
        self._batch_authority_key = hashlib.sha256(
            _AUDITORY_INCREMENTAL_BATCH_KEY_DOMAIN + batch_root
        ).digest()

    def _order_issued_locked(self) -> None:
        self._issued = OrderedDict(
            (event_id, self._issued[event_id])
            for event_id in self._authority_order
            if event_id in self._issued
        )

    def _remove_authority_order_locked(self, event_id: str) -> None:
        try:
            self._authority_order.remove(event_id)
        except ValueError as error:
            raise RuntimeError(
                "incremental terminal authority order changed"
            ) from error

    def _expire_locked(self, now: float) -> None:
        for stream_id in tuple(self._streams):
            if now - self._streams[stream_id].last_activity > self._idle_seconds:
                del self._streams[stream_id]
                self._log_event(
                    "auditory_incremental_terminal_expired",
                    stream_id=stream_id,
                )
    def _issue_locked(
        self,
        event: AuditoryIncrementalTerminalEvent,
        auditory_l5: AuditoryL5Experience,
    ) -> None:
        event.verify()
        auditory_l5.verify()
        if (
            event.schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3
            or auditory_l5.event_boundary != "utterance"
            or auditory_l5.structural_fingerprint
            != event.structural_fingerprint
            or auditory_l5.authority_receipt_sha256
            != event.l5_authority_receipt_sha256
            or auditory_l5.source_time_end - auditory_l5.source_time_start
            != Fraction(event.sample_count, PCM_SAMPLE_RATE_HZ)
        ):
            raise ValueError(
                "incremental auditory issued field differs from terminal"
            )
        existing = self._issued.get(event.event_id)
        if existing is not None:
            if existing != _IssuedTerminal(event, auditory_l5):
                raise RuntimeError(
                    "incremental terminal identity was issued twice differently"
                )
            return
        reserved = self._in_flight.get(event.event_id)
        if reserved is not None:
            if reserved.issued != _IssuedTerminal(event, auditory_l5):
                raise RuntimeError(
                    "incremental terminal identity changed while claimed"
                )
            return
        if len(self._authority_order) >= self._terminal_authority_capacity:
            raise RuntimeError(
                "incremental terminal authority capacity is full"
            )
        self._issued[event.event_id] = _IssuedTerminal(event, auditory_l5)
        self._authority_order.append(event.event_id)

    def _issue_batch_from_owner_locked(
        self,
        owner: AuditoryIncrementalTerminalOwner,
        events: tuple[AuditoryIncrementalTerminalEvent, ...],
    ) -> None:
        """Transfer one ordered release set into registry ownership atomically."""
        if not isinstance(events, tuple):
            raise TypeError("incremental terminal release batch must be a tuple")
        if len(events) > self._terminal_authority_capacity:
            raise RuntimeError(
                "incremental terminal authority capacity is full"
            )
        prior: AuditoryIncrementalTerminalEvent | None = None
        seen: set[str] = set()
        new_events = []
        for event in events:
            if not isinstance(event, AuditoryIncrementalTerminalEvent):
                raise TypeError("incremental terminal release batch is untyped")
            event.verify()
            if event.event_id in seen:
                raise ValueError("incremental terminal release batch repeats an event")
            if prior is not None and (
                event.stream_id != prior.stream_id
                or event.source_sample_start < prior.source_sample_end
            ):
                raise ValueError(
                    "incremental terminal release batch is not in source order"
                )
            seen.add(event.event_id)
            prior = event
            existing = self._issued.get(event.event_id)
            if existing is not None:
                if existing.event != event:
                    raise RuntimeError(
                        "incremental terminal identity was issued twice differently"
                    )
                continue
            reserved = self._in_flight.get(event.event_id)
            if reserved is not None:
                if reserved.issued.event != event:
                    raise RuntimeError(
                        "incremental terminal identity changed while claimed"
                    )
                continue
            new_events.append(event)
        if (
            len(self._authority_order) + len(new_events)
            > self._terminal_authority_capacity
        ):
            raise RuntimeError(
                "incremental terminal authority capacity is full"
            )
        issued = tuple(
            _IssuedTerminal(event, owner.claim_released_full_field(event))
            for event in new_events
        )
        for value in issued:
            self._issue_locked(value.event, value.auditory_l5)

    def materialize_batch(
        self,
        advance: AuditoryIncrementalAdvance,
    ) -> AuditoryIncrementalTerminalBatch:
        """Expose one complete release without consuming live authority.

        Materialization is a pure bounded view over already-issued registry
        authority.  It never stores a copy, and therefore repeated reads cannot
        grow live state.
        """
        if not isinstance(advance, AuditoryIncrementalAdvance):
            raise TypeError("incremental auditory batch requires an advance")
        advance.verify()
        if (
            advance.status is not AuditoryIncrementalStatus.RELEASED_UNIQUE
            or not advance.released_terminals
        ):
            raise ValueError(
                "incremental auditory batch requires released terminals"
            )
        with self._lock:
            entries = []
            positions = []
            for event in advance.released_terminals:
                issued = self._issued.get(event.event_id)
                if issued is None or issued.event != event:
                    raise ValueError(
                        "incremental auditory batch terminal is not issued"
                    )
                try:
                    position = self._authority_order.index(event.event_id)
                except ValueError as error:
                    raise RuntimeError(
                        "incremental auditory batch lost issued order"
                    ) from error
                positions.append(position)
                entries.append(AuditoryIncrementalTerminalBatchEntry(
                    event=event,
                    auditory_l5=issued.auditory_l5,
                ))
            if positions != list(range(positions[0], positions[0] + len(positions))):
                raise RuntimeError(
                    "incremental auditory release is not one authority batch"
                )
        immutable_entries = tuple(entries)
        payload = _batch_payload(
            advance_authority_receipt_sha256=(
                advance.authority_receipt_sha256
            ),
            entries=immutable_entries,
        )
        batch = AuditoryIncrementalTerminalBatch(
            advance_authority_receipt_sha256=(
                advance.authority_receipt_sha256
            ),
            entries=immutable_entries,
            authority_receipt_sha256=_digest(payload),
            authority_hmac_sha256=_hmac(self._batch_authority_key, payload),
        )
        batch._verify(verify_full_fields=False)
        return batch

    def _verify_materialized_batch_locked(
        self,
        batch: AuditoryIncrementalTerminalBatch,
    ) -> None:
        batch._verify(verify_full_fields=False)
        payload = _batch_payload(
            advance_authority_receipt_sha256=(
                batch.advance_authority_receipt_sha256
            ),
            entries=batch.entries,
        )
        if not hmac.compare_digest(
            batch.authority_hmac_sha256,
            _hmac(self._batch_authority_key, payload),
        ):
            raise ValueError(
                "incremental auditory batch owner authentication changed"
            )

    def claim_batch(
        self,
        batch: AuditoryIncrementalTerminalBatch,
    ) -> AuditoryIncrementalTerminalBatchClaim:
        """Atomically reserve every exact terminal in a materialized batch."""
        if not isinstance(batch, AuditoryIncrementalTerminalBatch):
            raise TypeError("incremental auditory batch claim is untyped")
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            self._verify_materialized_batch_locked(batch)
            if batch.authority_receipt_sha256 in self._in_flight_batches:
                raise ValueError("incremental auditory batch is already claimed")
            issued_values = []
            positions = []
            for entry in batch.entries:
                event = entry.event
                if event.event_id in self._in_flight:
                    raise ValueError(
                        "incremental auditory batch terminal is already claimed"
                    )
                issued = self._issued.get(event.event_id)
                if issued != _IssuedTerminal(event, entry.auditory_l5):
                    raise ValueError(
                        "incremental auditory batch terminal is not issued"
                    )
                try:
                    position = self._authority_order.index(event.event_id)
                except ValueError as error:
                    raise RuntimeError(
                        "incremental auditory batch lost authority order"
                    ) from error
                issued_values.append(issued)
                positions.append(position)
            if positions != list(range(positions[0], positions[0] + len(positions))):
                raise RuntimeError(
                    "incremental auditory batch authority is no longer contiguous"
                )
            reservation_token = object()
            prospective_issued = OrderedDict(self._issued)
            prospective_in_flight = OrderedDict(self._in_flight)
            for issued, position in zip(
                issued_values,
                positions,
                strict=True,
            ):
                del prospective_issued[issued.event.event_id]
                prospective_in_flight[issued.event.event_id] = (
                    _InFlightTerminal(
                        issued=issued,
                        reservation_token=reservation_token,
                        authority_position=position,
                    )
                )
            reservation = _InFlightTerminalBatch(
                batch=batch,
                reservation_token=reservation_token,
                authority_positions=tuple(positions),
            )
            prospective_batches = OrderedDict(self._in_flight_batches)
            prospective_batches[batch.authority_receipt_sha256] = reservation
            self._issued = prospective_issued
            self._in_flight = prospective_in_flight
            self._in_flight_batches = prospective_batches
            return AuditoryIncrementalTerminalBatchClaim(
                batch=batch,
                authority_positions=tuple(positions),
                owner_token=self._batch_claim_token,
                reservation_token=reservation_token,
            )

    def _verify_batch_claim_identity(
        self,
        claim: AuditoryIncrementalTerminalBatchClaim,
    ) -> None:
        if (
            not isinstance(claim, AuditoryIncrementalTerminalBatchClaim)
            or claim.owner_token is not self._batch_claim_token
        ):
            raise ValueError(
                "incremental auditory batch claim has no owner authority"
            )
        if not isinstance(claim.batch, AuditoryIncrementalTerminalBatch):
            raise TypeError("incremental auditory batch claim is untyped")
        if (
            not isinstance(claim.authority_positions, tuple)
            or len(claim.authority_positions) != len(claim.batch.entries)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in claim.authority_positions
            )
        ):
            raise ValueError(
                "incremental auditory batch claim positions are invalid"
            )

    def verify_batch_claim(
        self,
        claim: AuditoryIncrementalTerminalBatchClaim,
    ) -> AuditoryIncrementalTerminalBatch:
        """Return only a complete live batch reservation."""
        self._verify_batch_claim_identity(claim)
        with self._lock:
            self._verify_materialized_batch_locked(claim.batch)
            reserved = self._in_flight_batches.get(
                claim.batch.authority_receipt_sha256
            )
            if (
                reserved is None
                or reserved.batch != claim.batch
                or reserved.reservation_token is not claim.reservation_token
                or reserved.authority_positions != claim.authority_positions
            ):
                raise ValueError(
                    "incremental auditory batch claim is not live"
                )
            for entry, position in zip(
                claim.batch.entries,
                claim.authority_positions,
                strict=True,
            ):
                terminal = self._in_flight.get(entry.event.event_id)
                if (
                    terminal is None
                    or terminal.reservation_token is not claim.reservation_token
                    or terminal.authority_position != position
                    or terminal.issued
                    != _IssuedTerminal(entry.event, entry.auditory_l5)
                ):
                    raise ValueError(
                        "incremental auditory batch lost a terminal reservation"
                    )
                if (
                    position >= len(self._authority_order)
                    or self._authority_order[position] != entry.event.event_id
                ):
                    raise ValueError(
                        "incremental auditory batch authority order changed"
                    )
        return claim.batch

    def consume_batch(
        self,
        claim: AuditoryIncrementalTerminalBatchClaim,
        *,
        commit_batch: Callable[[], None] | None = None,
    ) -> AuditoryIncrementalTerminalBatch:
        """Atomically commit downstream work and consume the whole batch."""
        if commit_batch is not None and not callable(commit_batch):
            raise TypeError("incremental auditory batch commit must be callable")
        with self._lock:
            batch = self.verify_batch_claim(claim)
            prospective_in_flight = OrderedDict(self._in_flight)
            prospective_order = list(self._authority_order)
            for entry in batch.entries:
                del prospective_in_flight[entry.event.event_id]
                try:
                    prospective_order.remove(entry.event.event_id)
                except ValueError as error:
                    raise RuntimeError(
                        "incremental auditory batch lost consumed order"
                    ) from error
            prospective_batches = OrderedDict(self._in_flight_batches)
            del prospective_batches[batch.authority_receipt_sha256]
            if commit_batch is not None:
                commit_batch()
            self._in_flight = prospective_in_flight
            self._authority_order = prospective_order
            self._in_flight_batches = prospective_batches
            return batch

    def rollback_batch(
        self,
        claim: AuditoryIncrementalTerminalBatchClaim,
    ) -> None:
        """Atomically restore every reserved terminal to its original order."""
        with self._lock:
            batch = self.verify_batch_claim(claim)
            prospective_issued = OrderedDict(self._issued)
            prospective_in_flight = OrderedDict(self._in_flight)
            for entry in batch.entries:
                del prospective_in_flight[entry.event.event_id]
                prospective_issued[entry.event.event_id] = _IssuedTerminal(
                    entry.event,
                    entry.auditory_l5,
                )
            prospective_batches = OrderedDict(self._in_flight_batches)
            del prospective_batches[batch.authority_receipt_sha256]
            self._issued = prospective_issued
            self._in_flight = prospective_in_flight
            self._in_flight_batches = prospective_batches
            self._order_issued_locked()

    def claim(
        self,
        event: AuditoryIncrementalTerminalEvent,
    ) -> _AuditoryTerminalClaim:
        """Move one issued event into a bounded in-flight reservation."""
        if not isinstance(event, AuditoryIncrementalTerminalEvent):
            raise TypeError("auditory terminal claim requires a typed event")
        event.verify()
        if event.schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3:
            raise ValueError(
                "legacy incremental auditory audit record cannot be claimed"
            )
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            if event.event_id in self._in_flight:
                raise ValueError(
                    "auditory terminal was not issued or was already consumed; "
                    "auditory terminal is already claimed"
                )
            issued = self._issued.get(event.event_id)
            if issued is None:
                raise ValueError(
                    "auditory terminal was not issued or was already consumed"
                )
            if issued.event != event:
                raise ValueError("auditory terminal differs from owner authority")
            try:
                authority_position = self._authority_order.index(event.event_id)
            except ValueError as error:
                raise RuntimeError(
                    "auditory terminal lost its issued order"
                ) from error
            reservation_token = object()
            del self._issued[event.event_id]
            self._in_flight[event.event_id] = _InFlightTerminal(
                issued=issued,
                reservation_token=reservation_token,
                authority_position=authority_position,
            )
            return _AuditoryTerminalClaim(
                event=event,
                auditory_l5=issued.auditory_l5,
                owner_token=self._claim_token,
                reservation_token=reservation_token,
                authority_position=authority_position,
            )

    def _verify_claim_identity(
        self, claim: _AuditoryTerminalClaim
    ) -> None:
        if (
            not isinstance(claim, _AuditoryTerminalClaim)
            or claim.owner_token is not self._claim_token
        ):
            raise ValueError("auditory terminal claim has no owner authority")
        claim.event.verify()
        claim.auditory_l5.verify()
        if (
            claim.event.schema != AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3
            or claim.auditory_l5.event_boundary != "utterance"
            or claim.auditory_l5.structural_fingerprint
            != claim.event.structural_fingerprint
            or claim.auditory_l5.authority_receipt_sha256
            != claim.event.l5_authority_receipt_sha256
        ):
            raise ValueError("auditory terminal claim lost its full field")

    def verify_claim(
        self,
        claim: _AuditoryTerminalClaim,
    ) -> AuditoryIncrementalTerminalEvent:
        self._verify_claim_identity(claim)
        with self._lock:
            reserved = self._in_flight.get(claim.event.event_id)
            if (
                claim.lifecycle != "in_flight"
                or reserved is None
                or reserved.reservation_token is not claim.reservation_token
                or reserved.issued
                != _IssuedTerminal(claim.event, claim.auditory_l5)
                or reserved.authority_position != claim.authority_position
            ):
                raise ValueError(
                    "auditory terminal claim is not the live reservation"
                )
        return claim.event

    def full_field_from_claim(
        self,
        claim: _AuditoryTerminalClaim,
    ) -> AuditoryL5Experience:
        """Return the exact field while preserving claim ownership."""
        self.verify_claim(claim)
        return claim.auditory_l5

    def _validate_claim_settlement(
        self,
        claim: _AuditoryTerminalClaim,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Verify that one prepared settlement preserves the claimed field."""
        self._verify_claim_identity(claim)
        if claim.lifecycle != "in_flight" or claim.causal_settlement is not None:
            raise ValueError("auditory terminal claim was already settled")
        self.verify_claim(claim)
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "auditory terminal claim requires a causal settlement"
            )
        settlement.verify()
        experience = claim.auditory_l5
        if (
            settlement.source_time_start != experience.source_time_start
            or settlement.source_time_end != experience.source_time_end
        ):
            raise ValueError(
                "auditory causal settlement changed the source interval"
            )
        sound = next(
            (
                value for value in settlement.interpretations
                if value.sense == "sound"
            ),
            None,
        )
        if sound is None or sound.state != "observed":
            raise ValueError(
                "auditory causal settlement lost the observed sound field"
            )
        components = tuple(
            component
            for channel in experience.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
        )
        if (
            len(components) != AUDITORY_KERNEL_COMPONENT_COUNT
            or len(sound.substreams) != AUDITORY_KERNEL_COMPONENT_COUNT
        ):
            raise ValueError(
                "auditory causal settlement changed field topology"
            )
        for interpreted, component in zip(
            sound.substreams,
            components,
            strict=True,
        ):
            # The joined window is a new receipt graph, so graph-local receipt
            # strings do not establish cross-graph equality.  The invariant
            # is exact source commitment, topology, and every explicit L4
            # field value.
            if (
                interpreted.sensor_id != component.sensor_id
                or interpreted.substream_id != component.substream_id
                or interpreted.topology_index != component.topology_index
                or interpreted.coordinates != component.coordinates
                or interpreted.physical_quantity
                != component.physical_quantity
                or interpreted.physical_unit != component.physical_unit
                or not interpreted.matches_source_claim(
                    source_evidence_stream_receipt_sha256=(
                        component.source_stream_receipt_sha256
                    ),
                    samples=tuple(
                        (
                            sample.source_index,
                            sample.source_time,
                            sample.signal,
                            sample.phase_turns,
                        )
                        for sample in component.samples
                    ),
                )
                or tuple(
                    (
                        value.tuple_index,
                        value.fields,
                    )
                    for value in interpreted.field_tuples
                )
                != tuple(
                    (
                        value.tuple_index,
                        value.fields,
                    )
                    for value in component.l4_field_tuples
                )
            ):
                raise ValueError(
                    "auditory causal settlement reduced the exact field"
                )
        if len(settlement.language_events) != 1:
            raise ValueError(
                "auditory causal settlement changed terminal language cardinality"
            )
        language_event = settlement.language_events[0]
        event = claim.event
        if (
            language_event.form != event.tutor_label
            or language_event.unicode_scalars
            != tuple(ord(value) for value in event.tutor_label)
            or language_event.source_event_id != event.event_id
            or language_event.source_authority_receipt_sha256
            != event.authority_receipt_sha256
            or language_event.source_l5_authority_receipt_sha256
            != event.l5_authority_receipt_sha256
            or language_event.recognition_occurrence
            != event.recognition_occurrence
        ):
            raise ValueError(
                "auditory causal settlement changed the issued terminal"
            )

    def prepare_claim(
        self,
        claim: _AuditoryTerminalClaim,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Attach one verified, still-uncommitted settlement to a live claim."""
        self._validate_claim_settlement(claim, settlement)
        with self._lock:
            self.verify_claim(claim)
            existing = claim.prepared_causal_settlement
            if existing is not None and existing != settlement:
                raise ValueError(
                    "auditory terminal claim was prepared differently"
                )
            claim.prepared_causal_settlement = settlement

    def prepared_settlement_from_claim(
        self,
        claim: _AuditoryTerminalClaim,
    ) -> CausalExperienceSettlement:
        """Return only a verified settlement that has not yet been committed."""
        self.verify_claim(claim)
        settlement = claim.prepared_causal_settlement
        if settlement is None:
            raise ValueError("auditory terminal claim is not prepared")
        self._validate_claim_settlement(claim, settlement)
        return settlement

    def complete_claim(
        self,
        claim: _AuditoryTerminalClaim,
        settlement: CausalExperienceSettlement | None = None,
        *,
        commit_settlement: Callable[[], None] | None = None,
    ) -> None:
        """Atomically commit one prepared settlement and consume its claim."""
        if settlement is None:
            settlement = self.prepared_settlement_from_claim(claim)
        else:
            self._validate_claim_settlement(claim, settlement)
        event = claim.event
        with self._lock:
            self.verify_claim(claim)
            prepared = claim.prepared_causal_settlement
            if prepared is not None and prepared != settlement:
                raise ValueError(
                    "auditory terminal claim settlement changed after prepare"
                )
            if commit_settlement is not None:
                if not callable(commit_settlement):
                    raise TypeError("claim settlement commit must be callable")
                commit_settlement()
            del self._in_flight[event.event_id]
            self._remove_authority_order_locked(event.event_id)
            claim.prepared_causal_settlement = None
            claim.causal_settlement = settlement
            claim.lifecycle = "completed"

    def rollback_claim(self, claim: _AuditoryTerminalClaim) -> None:
        """Restore a failed conversation claim to its exact issued slot."""

        self._verify_claim_identity(claim)
        with self._lock:
            if claim.lifecycle == "rolled_back":
                raise ValueError("auditory terminal claim was already rolled back")
            issued = _IssuedTerminal(claim.event, claim.auditory_l5)
            if claim.lifecycle != "in_flight":
                raise ValueError(
                    "completed auditory terminal claim cannot be rolled back"
                )
            reserved = self._in_flight.get(claim.event.event_id)
            if (
                reserved is None
                or reserved.reservation_token is not claim.reservation_token
                or reserved.issued != issued
                or reserved.authority_position != claim.authority_position
            ):
                raise ValueError(
                    "auditory terminal rollback lost its reservation"
                )
            del self._in_flight[claim.event.event_id]
            self._issued[claim.event.event_id] = issued
            self._order_issued_locked()
            claim.prepared_causal_settlement = None
            claim.causal_settlement = None
            claim.lifecycle = "rolled_back"

    def causal_settlement_from_claim(
        self,
        claim: _AuditoryTerminalClaim,
    ) -> CausalExperienceSettlement:
        """Return only a verified, fully joined causal action authority."""
        self._verify_claim_identity(claim)
        if claim.lifecycle != "completed":
            raise ValueError("auditory terminal claim is not completed")
        settlement = claim.causal_settlement
        if settlement is None:
            raise ValueError("auditory terminal claim is not causally settled")
        settlement.verify()
        return settlement

    def discard_unadmitted(
        self,
        event: AuditoryIncrementalTerminalEvent,
    ) -> bool:
        """Release authority for an event rejected by the bounded reply door."""
        if not isinstance(event, AuditoryIncrementalTerminalEvent):
            raise TypeError("auditory terminal discard requires a typed event")
        event.verify()
        with self._lock:
            if event.event_id in self._in_flight:
                raise ValueError("claimed auditory terminal cannot be discarded")
            issued = self._issued.get(event.event_id)
            if issued is None:
                return False
            if issued.event != event:
                raise ValueError("auditory terminal differs from owner authority")
            del self._issued[event.event_id]
            self._remove_authority_order_locked(event.event_id)
            return True

    def advance(self, **authorities) -> AuditoryIncrementalAdvance:
        transport = authorities.get("transport")
        if not isinstance(transport, AuditoryPCMContinuityReceipt):
            raise TypeError("incremental registry requires typed PCM continuity")
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            mounted = self._streams.get(transport.stream_id)
            created = False
            if transport.sequence == 0:
                if mounted is not None:
                    if (
                        mounted.owner._last_committed_receipt_sha256
                        != transport.receipt_sha256
                    ):
                        raise ValueError(
                            "incremental stream epoch already exists"
                        )
                else:
                    if len(self._streams) >= self._stream_capacity:
                        raise RuntimeError("incremental stream capacity is full")
                    mounted = _OwnedIncrementalTerminal(
                        owner=AuditoryIncrementalTerminalOwner(
                            reciprocity_owner=self._reciprocity_owner,
                            log_event=self._log_event,
                            _prepared_cells=self._cells,
                        ),
                        last_activity=now,
                    )
                    self._streams[transport.stream_id] = mounted
                    created = True
            elif mounted is None:
                raise ValueError("incremental stream epoch is unknown or expired")
            prior_issued = OrderedDict(self._issued)
            prior_authority_order = list(self._authority_order)
            with mounted.owner._lock:
                checkpoint = mounted.owner._transaction_checkpoint()
                owner_advance_completed = False
                try:
                    result = mounted.owner.advance(**authorities)
                    owner_advance_completed = True
                    if result.status is AuditoryIncrementalStatus.DISCONTINUITY:
                        self._streams.pop(transport.stream_id, None)
                        return result
                    if result.released_terminals:
                        self._issue_batch_from_owner_locked(
                            mounted.owner, result.released_terminals
                        )
                except Exception as advance_error:
                    self._issued = prior_issued
                    self._authority_order = prior_authority_order
                    if created:
                        self._streams.pop(transport.stream_id, None)
                    if owner_advance_completed:
                        try:
                            mounted.owner._restore_transaction_checkpoint(
                                checkpoint
                            )
                        except Exception as rollback_error:
                            raise ExceptionGroup(
                                "incremental auditory registry advance and "
                                "rollback failed",
                                [advance_error, rollback_error],
                            )
                    raise
            mounted.last_activity = now
            self._streams.move_to_end(transport.stream_id)
            return result

    def close(
        self,
        stream_id: str,
        *,
        release_terminal: bool,
    ) -> AuditoryIncrementalAdvance | None:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("incremental stream id is required")
        with self._lock:
            mounted = self._streams.get(stream_id)
            if mounted is None:
                return None
            if not release_terminal:
                del self._streams[stream_id]
                return None
            prior_issued = OrderedDict(self._issued)
            prior_authority_order = list(self._authority_order)
            with mounted.owner._lock:
                checkpoint = mounted.owner._transaction_checkpoint()
                try:
                    result = mounted.owner.close_stream()
                    if result.released_terminals:
                        self._issue_batch_from_owner_locked(
                            mounted.owner, result.released_terminals
                        )
                except Exception as close_error:
                    self._issued = prior_issued
                    self._authority_order = prior_authority_order
                    try:
                        mounted.owner._restore_transaction_checkpoint(
                            checkpoint
                        )
                    except Exception as rollback_error:
                        raise ExceptionGroup(
                            "incremental auditory registry close and rollback "
                            "failed",
                            [close_error, rollback_error],
                        )
                    raise
            removed = self._streams.pop(stream_id, None)
            if removed is not mounted:
                raise RuntimeError(
                    "incremental auditory stream changed during close"
                )
            return result

    def refresh_learning(self) -> int:
        """Atomically rebuild tutor cells and discard provisional streams."""

        cells = _cells_from_owner(self._reciprocity_owner)
        with self._lock:
            count = len(self._streams)
            self._streams.clear()
            self._cells = cells
            return count

    def status(self) -> dict[str, int]:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "active_streams": len(self._streams),
                "stream_capacity": self._stream_capacity,
                "retained_samples": sum(
                    value.owner.retained_sample_count
                    for value in self._streams.values()
                ),
                "active_trackers": sum(
                    value.owner.active_tracker_count
                    for value in self._streams.values()
                ),
                "learned_cells": len(self._cells),
                "issued_terminal_authorities": len(self._issued),
                "in_flight_terminal_authorities": len(self._in_flight),
                "issued_terminal_capacity": self._terminal_authority_capacity,
            }

    def authority_counts(self) -> dict[str, int]:
        """Read terminal ownership for fail-closed lifecycle certification."""
        with self._lock:
            return {
                "issued_terminal_authorities": len(self._issued),
                "in_flight_terminal_authorities": len(self._in_flight),
            }

    def batch_claim_count(self) -> int:
        """Read bounded batch reservations without changing legacy status."""
        with self._lock:
            return len(self._in_flight_batches)


__all__ = (
    "AUDITORY_INCREMENTAL_ADVANCE_SCHEMA",
    "AUDITORY_INCREMENTAL_BATCH_SCHEMA",
    "AUDITORY_INCREMENTAL_EVENT_SCHEMA",
    "AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2",
    "AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3",
    "AuditoryIncrementalAdvance",
    "AuditoryIncrementalStatus",
    "AuditoryIncrementalTerminalBatch",
    "AuditoryIncrementalTerminalBatchClaim",
    "AuditoryIncrementalTerminalBatchEntry",
    "AuditoryIncrementalTerminalEvent",
    "AuditoryIncrementalTerminalOwner",
    "AuditoryIncrementalTerminalRegistry",
    "MAX_ACTIVE_TRACKERS",
    "MAX_EVENT_SAMPLES",
    "MAX_EVENT_HOPS",
    "MAX_RELEASED_TERMINALS_PER_ADVANCE",
)
