"""Authenticated ordering of already-bounded auditory L5 token events.

This module does not segment sound.  It admits only a complete
``AuditoryIncrementalTerminalEvent`` whose exact interval and L5 authority
already agree with a verified ``AuditoryL5Experience``.  The terminal's tutor
label is deliberately ignored: a separate authenticated teacher receipt must
designate the entire admitted physical event as one token class.

Token classification is set-valued and deterministic.  No designation is an
honest unknown; one designated class is unique; conflicting designations are
ambiguous.  Sequence settlement preserves caller-supplied physical order and
gaps without sorting, splitting, timing inference, probabilities, scores,
chi, Atlas, or a grammar table.

The live engine is intentionally not wired here.  It still needs an upstream
owner capable of releasing more than one individually bounded auditory L5
sub-event from a continuous utterance.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.model import require_fraction, sha256_digest
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    MAX_EVENT_HOPS,
    AuditoryIncrementalTerminalEvent,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_pcm_stream import PCM_SAMPLE_RATE_HZ
from dsf_ai_service.substrate.auditory_reciprocity import (
    MAX_RECIPROCAL_CLASSES_PER_KIND,
    AuditoryRecognitionState,
)


ADMITTED_SUB_EVENT_SCHEMA = "guala.auditory_token.sub_event_admission.v1"
TEACHER_TOKEN_DESIGNATION_SCHEMA = (
    "guala.auditory_token.teacher_designation.v1"
)
TOKEN_CLASSIFICATION_SCHEMA = "guala.auditory_token.classification.v1"
TOKEN_SEQUENCE_SCHEMA = "guala.auditory_token.sequence.v1"
TOKEN_AUTHORITY_SNAPSHOT_SCHEMA = "guala.auditory_token.snapshot.v1"

_ADMISSION_KEY_DOMAIN = b"guala.auditory_token.admission.v1\0"
_TEACHER_KEY_DOMAIN = b"guala.auditory_token.teacher.v1\0"
_CLASSIFICATION_KEY_DOMAIN = b"guala.auditory_token.classification.v1\0"
_SEQUENCE_KEY_DOMAIN = b"guala.auditory_token.sequence.v1\0"
_SNAPSHOT_KEY_DOMAIN = b"guala.auditory_token.snapshot.v1\0"

# These are storage/work boundaries only.  They do not influence recognition.
MAX_TOKEN_CLASS_SCALARS = 512
MAX_TOKEN_CLASS_UTF8_BYTES = MAX_TOKEN_CLASS_SCALARS * 4
MAX_TOKEN_BINDINGS = MAX_RECIPROCAL_CLASSES_PER_KIND * 4
MAX_TOKEN_OCCURRENCES_PER_SEQUENCE = MAX_EVENT_HOPS
MAX_ADMISSION_BYTES = 16 * 1024
MAX_SEQUENCE_BYTES = MAX_TOKEN_OCCURRENCES_PER_SEQUENCE * 2048
MAX_SNAPSHOT_BYTES = MAX_TOKEN_BINDINGS * 4096


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


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory token exact time")
    return f"{value.numerator}/{value.denominator}"


def _identifier(value: object, name: str, *, maximum_bytes: int = 256) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be nonempty text")
    if len(value.encode("utf-8")) > maximum_bytes:
        raise ValueError(f"{name} exceeds its byte boundary")
    return value


def _sha256(value: object, name: str) -> str:
    return sha256_digest(value, name)


def _nonce(value: object) -> str:
    result = _sha256(value, "auditory token teacher nonce")
    if result != value:
        raise ValueError("auditory token teacher nonce is not canonical")
    return result


def _token_form(value: object) -> tuple[str, tuple[int, ...]]:
    if not isinstance(value, str) or not value:
        raise ValueError("teacher token form must be nonempty text")
    scalars = tuple(ord(character) for character in value)
    if (
        len(scalars) > MAX_TOKEN_CLASS_SCALARS
        or len(value.encode("utf-8", errors="strict")) > MAX_TOKEN_CLASS_UTF8_BYTES
        or any(0xD800 <= scalar <= 0xDFFF for scalar in scalars)
    ):
        raise ValueError("teacher token form exceeds its Unicode boundary")
    return value, scalars


@dataclass(frozen=True, slots=True)
class AdmittedAuditoryStructuralSubEvent:
    """Compact authenticated relation between one terminal and its full L5."""

    sub_event_id: str
    stream_id: str
    source_sample_start: int
    source_sample_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    terminal_authority_receipt_sha256: str
    recognition_authority_receipt_sha256: str
    physical_class_authority_receipt_sha256: str
    admission_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "l5_authority_receipt_sha256": self.l5_authority_receipt_sha256,
            "physical_class_authority_receipt_sha256": (
                self.physical_class_authority_receipt_sha256
            ),
            "recognition_authority_receipt_sha256": (
                self.recognition_authority_receipt_sha256
            ),
            "schema": ADMITTED_SUB_EVENT_SCHEMA,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "stream_id": self.stream_id,
            "structural_fingerprint": self.structural_fingerprint,
            "sub_event_id": self.sub_event_id,
            "terminal_authority_receipt_sha256": (
                self.terminal_authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class TeacherTokenDesignationReceipt:
    """Teacher authority that the complete sub-event is one token class."""

    nonce: str
    sub_event_id: str
    sub_event_admission_hmac_sha256: str
    physical_class_authority_receipt_sha256: str
    token_class_id: str
    token_form: str
    unicode_scalars: tuple[int, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "nonce": self.nonce,
            "physical_class_authority_receipt_sha256": (
                self.physical_class_authority_receipt_sha256
            ),
            "schema": TEACHER_TOKEN_DESIGNATION_SCHEMA,
            "sub_event_admission_hmac_sha256": (
                self.sub_event_admission_hmac_sha256
            ),
            "sub_event_id": self.sub_event_id,
            "token_class_id": self.token_class_id,
            "token_form": self.token_form,
            "unicode_scalars": list(self.unicode_scalars),
        }

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


@dataclass(frozen=True, slots=True)
class TokenClassIdentity:
    token_class_id: str
    token_form: str

    def as_record(self) -> dict[str, str]:
        return {
            "token_class_id": self.token_class_id,
            "token_form": self.token_form,
        }


class TokenClassificationState(str, Enum):
    UNKNOWN = "unknown"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class TokenClassification:
    sub_event_id: str
    state: TokenClassificationState
    candidates: tuple[TokenClassIdentity, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidates": [value.as_record() for value in self.candidates],
            "schema": TOKEN_CLASSIFICATION_SCHEMA,
            "state": self.state.value,
            "sub_event_id": self.sub_event_id,
        }


@dataclass(frozen=True, slots=True)
class OrderedAuditoryTokenOccurrence:
    ordinal: int
    sub_event_id: str
    source_sample_start: int
    source_sample_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    terminal_authority_receipt_sha256: str
    sub_event_admission_hmac_sha256: str
    classification_state: TokenClassificationState
    token_candidates: tuple[TokenClassIdentity, ...]
    classification_authority_hmac_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "classification_authority_hmac_sha256": (
                self.classification_authority_hmac_sha256
            ),
            "classification_state": self.classification_state.value,
            "l5_authority_receipt_sha256": self.l5_authority_receipt_sha256,
            "ordinal": self.ordinal,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "structural_fingerprint": self.structural_fingerprint,
            "sub_event_admission_hmac_sha256": (
                self.sub_event_admission_hmac_sha256
            ),
            "sub_event_id": self.sub_event_id,
            "terminal_authority_receipt_sha256": (
                self.terminal_authority_receipt_sha256
            ),
            "token_candidates": [
                value.as_record() for value in self.token_candidates
            ],
        }


@dataclass(frozen=True, slots=True)
class AuditoryTokenSequenceReceipt:
    sequence_id: str
    stream_id: str
    binding_state_sha256: str
    occurrences: tuple[OrderedAuditoryTokenOccurrence, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binding_state_sha256": self.binding_state_sha256,
            "occurrences": [value.as_record() for value in self.occurrences],
            "schema": TOKEN_SEQUENCE_SCHEMA,
            "sequence_id": self.sequence_id,
            "stream_id": self.stream_id,
        }


@dataclass(frozen=True, slots=True)
class _TokenBinding:
    physical_class_authority_receipt_sha256: str
    token_class_id: str
    token_form: str
    designation: TeacherTokenDesignationReceipt

    @property
    def key(self) -> tuple[str, str]:
        return (
            self.physical_class_authority_receipt_sha256,
            self.token_class_id,
        )

    def as_record(self) -> dict[str, object]:
        return {
            "designation": self.designation.as_record(),
            "physical_class_authority_receipt_sha256": (
                self.physical_class_authority_receipt_sha256
            ),
            "token_class_id": self.token_class_id,
            "token_form": self.token_form,
        }


class AuditoryTokenSequenceAuthority:
    """Bounded owner of explicit whole-event token designations and order."""

    def __init__(
        self,
        *,
        authority_secret: bytes,
        max_bindings: int = MAX_TOKEN_BINDINGS,
        max_snapshot_bytes: int = MAX_SNAPSHOT_BYTES,
    ) -> None:
        if not isinstance(authority_secret, bytes) or len(authority_secret) < 32:
            raise ValueError("auditory token authority requires at least 32 secret bytes")
        if (
            isinstance(max_bindings, bool)
            or not isinstance(max_bindings, int)
            or not 0 < max_bindings <= MAX_TOKEN_BINDINGS
        ):
            raise ValueError("auditory token binding capacity is invalid")
        if (
            isinstance(max_snapshot_bytes, bool)
            or not isinstance(max_snapshot_bytes, int)
            or max_snapshot_bytes <= 0
            or max_snapshot_bytes > MAX_SNAPSHOT_BYTES
        ):
            raise ValueError("auditory token snapshot boundary is invalid")
        root = hashlib.sha256(authority_secret).digest()
        self._admission_key = hashlib.sha256(_ADMISSION_KEY_DOMAIN + root).digest()
        self._teacher_key = hashlib.sha256(_TEACHER_KEY_DOMAIN + root).digest()
        self._classification_key = hashlib.sha256(
            _CLASSIFICATION_KEY_DOMAIN + root
        ).digest()
        self._sequence_key = hashlib.sha256(_SEQUENCE_KEY_DOMAIN + root).digest()
        self._snapshot_key = hashlib.sha256(_SNAPSHOT_KEY_DOMAIN + root).digest()
        self._max_bindings = max_bindings
        self._max_snapshot_bytes = max_snapshot_bytes
        self._bindings: dict[tuple[str, str], _TokenBinding] = {}
        self._accepted_teacher_nonces: set[str] = set()
        self._lock = threading.RLock()

    @property
    def binding_count(self) -> int:
        with self._lock:
            return len(self._bindings)

    @property
    def snapshot_bytes(self) -> int:
        return len(_canonical_bytes(self.snapshot()))

    def _verify_admitted(
        self, value: AdmittedAuditoryStructuralSubEvent
    ) -> None:
        if not isinstance(value, AdmittedAuditoryStructuralSubEvent):
            raise TypeError("auditory token operation requires an admitted sub-event")
        _sha256(value.sub_event_id, "auditory token sub-event id")
        _identifier(value.stream_id, "auditory token stream id")
        if (
            isinstance(value.source_sample_start, bool)
            or not isinstance(value.source_sample_start, int)
            or isinstance(value.source_sample_end, bool)
            or not isinstance(value.source_sample_end, int)
            or value.source_sample_start < 0
            or value.source_sample_end <= value.source_sample_start
        ):
            raise ValueError("auditory token sub-event sample interval is invalid")
        require_fraction(value.source_time_start, "auditory token source start")
        require_fraction(value.source_time_end, "auditory token source end")
        if value.source_time_end <= value.source_time_start:
            raise ValueError("auditory token sub-event time interval is invalid")
        if value.source_time_end - value.source_time_start != Fraction(
            value.source_sample_end - value.source_sample_start,
            PCM_SAMPLE_RATE_HZ,
        ):
            raise ValueError("auditory token sample and time intervals disagree")
        for digest, name in (
            (value.structural_fingerprint, "structural fingerprint"),
            (value.l5_authority_receipt_sha256, "L5 authority"),
            (value.terminal_authority_receipt_sha256, "terminal authority"),
            (value.recognition_authority_receipt_sha256, "recognition authority"),
            (
                value.physical_class_authority_receipt_sha256,
                "physical class authority",
            ),
            (value.admission_hmac_sha256, "admission HMAC"),
        ):
            _sha256(digest, f"auditory token {name}")
        expected_id = _digest({
            "l5_authority_receipt_sha256": value.l5_authority_receipt_sha256,
            "source_sample_end": value.source_sample_end,
            "source_sample_start": value.source_sample_start,
            "stream_id": value.stream_id,
            "structural_fingerprint": value.structural_fingerprint,
            "terminal_authority_receipt_sha256": (
                value.terminal_authority_receipt_sha256
            ),
        })
        if value.sub_event_id != expected_id:
            raise ValueError("auditory token sub-event identity changed")
        if not hmac.compare_digest(
            value.admission_hmac_sha256,
            _hmac(self._admission_key, value.payload()),
        ):
            raise ValueError("auditory token sub-event admission changed")
        if len(_canonical_bytes(value.payload())) > MAX_ADMISSION_BYTES:
            raise ValueError("auditory token sub-event admission exceeds its boundary")

    def admit(
        self,
        terminal: AuditoryIncrementalTerminalEvent,
        auditory_l5: AuditoryL5Experience,
    ) -> AdmittedAuditoryStructuralSubEvent:
        """Authenticate one complete existing terminal; never divide it."""
        if not isinstance(terminal, AuditoryIncrementalTerminalEvent):
            raise TypeError("auditory token admission requires a terminal event")
        if not isinstance(auditory_l5, AuditoryL5Experience):
            raise TypeError("auditory token admission requires an auditory L5 field")
        terminal.verify()
        auditory_l5.verify()
        occurrence = terminal.recognition_occurrence
        if (
            auditory_l5.event_boundary != "utterance"
            or occurrence is None
            or occurrence.state is not AuditoryRecognitionState.UNIQUE
            or occurrence.selected_class_authority_receipt_sha256 is None
            or terminal.structural_fingerprint
            != auditory_l5.structural_fingerprint
            or terminal.l5_authority_receipt_sha256
            != auditory_l5.authority_receipt_sha256
            or occurrence.experience_id != auditory_l5.experience_id
            or occurrence.structural_fingerprint
            != auditory_l5.structural_fingerprint
            or occurrence.l5_authority_receipt_sha256
            != auditory_l5.authority_receipt_sha256
        ):
            raise ValueError("auditory token terminal and full L5 field disagree")
        duration = Fraction(terminal.sample_count, PCM_SAMPLE_RATE_HZ)
        if auditory_l5.source_time_end - auditory_l5.source_time_start != duration:
            raise ValueError("auditory token terminal and L5 duration disagree")
        sub_event_id = _digest({
            "l5_authority_receipt_sha256": auditory_l5.authority_receipt_sha256,
            "source_sample_end": terminal.source_sample_end,
            "source_sample_start": terminal.source_sample_start,
            "stream_id": terminal.stream_id,
            "structural_fingerprint": auditory_l5.structural_fingerprint,
            "terminal_authority_receipt_sha256": (
                terminal.authority_receipt_sha256
            ),
        })
        provisional = AdmittedAuditoryStructuralSubEvent(
            sub_event_id=sub_event_id,
            stream_id=terminal.stream_id,
            source_sample_start=terminal.source_sample_start,
            source_sample_end=terminal.source_sample_end,
            source_time_start=auditory_l5.source_time_start,
            source_time_end=auditory_l5.source_time_end,
            structural_fingerprint=auditory_l5.structural_fingerprint,
            l5_authority_receipt_sha256=auditory_l5.authority_receipt_sha256,
            terminal_authority_receipt_sha256=(
                terminal.authority_receipt_sha256
            ),
            recognition_authority_receipt_sha256=(
                occurrence.authority_receipt_sha256
            ),
            physical_class_authority_receipt_sha256=(
                occurrence.selected_class_authority_receipt_sha256
            ),
            admission_hmac_sha256="",
        )
        admitted = AdmittedAuditoryStructuralSubEvent(
            **{
                field: getattr(provisional, field)
                for field in provisional.__dataclass_fields__
                if field != "admission_hmac_sha256"
            },
            admission_hmac_sha256=_hmac(
                self._admission_key, provisional.payload()
            ),
        )
        self._verify_admitted(admitted)
        return admitted

    def issue_teacher_designation(
        self,
        sub_event: AdmittedAuditoryStructuralSubEvent,
        *,
        token_class_id: str,
        token_form: str,
        nonce: str | None = None,
    ) -> TeacherTokenDesignationReceipt:
        self._verify_admitted(sub_event)
        class_id = _sha256(token_class_id, "teacher token class id")
        form, scalars = _token_form(token_form)
        actual_nonce = _nonce(nonce if nonce is not None else secrets.token_hex(32))
        provisional = TeacherTokenDesignationReceipt(
            nonce=actual_nonce,
            sub_event_id=sub_event.sub_event_id,
            sub_event_admission_hmac_sha256=sub_event.admission_hmac_sha256,
            physical_class_authority_receipt_sha256=(
                sub_event.physical_class_authority_receipt_sha256
            ),
            token_class_id=class_id,
            token_form=form,
            unicode_scalars=scalars,
            authority_hmac_sha256="",
        )
        return TeacherTokenDesignationReceipt(
            nonce=provisional.nonce,
            sub_event_id=provisional.sub_event_id,
            sub_event_admission_hmac_sha256=(
                provisional.sub_event_admission_hmac_sha256
            ),
            physical_class_authority_receipt_sha256=(
                provisional.physical_class_authority_receipt_sha256
            ),
            token_class_id=provisional.token_class_id,
            token_form=provisional.token_form,
            unicode_scalars=provisional.unicode_scalars,
            authority_hmac_sha256=_hmac(
                self._teacher_key, provisional.payload()
            ),
        )

    def _verify_designation(
        self,
        designation: TeacherTokenDesignationReceipt,
        sub_event: AdmittedAuditoryStructuralSubEvent | None = None,
    ) -> None:
        if not isinstance(designation, TeacherTokenDesignationReceipt):
            raise TypeError("auditory token teaching requires a designation receipt")
        _nonce(designation.nonce)
        _sha256(designation.sub_event_id, "teacher token sub-event")
        _sha256(
            designation.sub_event_admission_hmac_sha256,
            "teacher token sub-event admission",
        )
        _sha256(
            designation.physical_class_authority_receipt_sha256,
            "teacher token physical class",
        )
        _sha256(designation.token_class_id, "teacher token class id")
        _sha256(
            designation.authority_hmac_sha256,
            "teacher token designation HMAC",
        )
        form, scalars = _token_form(designation.token_form)
        if form != designation.token_form or scalars != designation.unicode_scalars:
            raise ValueError("teacher token Unicode order changed")
        if not hmac.compare_digest(
            designation.authority_hmac_sha256,
            _hmac(self._teacher_key, designation.payload()),
        ):
            raise ValueError("teacher token designation authority changed")
        if sub_event is not None and (
            designation.sub_event_id != sub_event.sub_event_id
            or designation.sub_event_admission_hmac_sha256
            != sub_event.admission_hmac_sha256
            or designation.physical_class_authority_receipt_sha256
            != sub_event.physical_class_authority_receipt_sha256
        ):
            raise ValueError("teacher token designation names a different sub-event")

    def teach(
        self,
        sub_event: AdmittedAuditoryStructuralSubEvent,
        designation: TeacherTokenDesignationReceipt,
    ) -> TokenClassIdentity:
        self._verify_admitted(sub_event)
        self._verify_designation(designation, sub_event)
        binding = _TokenBinding(
            physical_class_authority_receipt_sha256=(
                designation.physical_class_authority_receipt_sha256
            ),
            token_class_id=designation.token_class_id,
            token_form=designation.token_form,
            designation=designation,
        )
        with self._lock:
            if designation.nonce in self._accepted_teacher_nonces:
                raise RuntimeError("teacher token designation nonce was already used")
            if binding.key in self._bindings:
                raise RuntimeError("teacher token class relation already exists")
            if len(self._bindings) >= self._max_bindings:
                raise RuntimeError("auditory token binding capacity is full")
            for current in self._bindings.values():
                if (
                    current.token_class_id == binding.token_class_id
                    and current.token_form != binding.token_form
                ):
                    raise ValueError("one token class has conflicting Unicode forms")
            prospective = dict(self._bindings)
            prospective[binding.key] = binding
            prospective_nonces = set(self._accepted_teacher_nonces)
            prospective_nonces.add(designation.nonce)
            self._snapshot_envelope(prospective, prospective_nonces)
            self._bindings = prospective
            self._accepted_teacher_nonces = prospective_nonces
        return TokenClassIdentity(binding.token_class_id, binding.token_form)

    def _classification_payload(
        self,
        sub_event: AdmittedAuditoryStructuralSubEvent,
        state: TokenClassificationState,
        candidates: tuple[TokenClassIdentity, ...],
    ) -> dict[str, object]:
        return {
            "candidates": [value.as_record() for value in candidates],
            "schema": TOKEN_CLASSIFICATION_SCHEMA,
            "state": state.value,
            "sub_event_id": sub_event.sub_event_id,
        }

    def _classify_locked(
        self, sub_event: AdmittedAuditoryStructuralSubEvent
    ) -> TokenClassification:
        identities = {
            (binding.token_class_id, binding.token_form)
            for binding in self._bindings.values()
            if binding.physical_class_authority_receipt_sha256
            == sub_event.physical_class_authority_receipt_sha256
        }
        candidates = tuple(
            TokenClassIdentity(class_id, form)
            for class_id, form in sorted(identities)
        )
        state = (
            TokenClassificationState.UNKNOWN
            if not candidates
            else TokenClassificationState.UNIQUE
            if len(candidates) == 1
            else TokenClassificationState.AMBIGUOUS
        )
        payload = self._classification_payload(sub_event, state, candidates)
        return TokenClassification(
            sub_event_id=sub_event.sub_event_id,
            state=state,
            candidates=candidates,
            authority_hmac_sha256=_hmac(self._classification_key, payload),
        )

    def classify(
        self, sub_event: AdmittedAuditoryStructuralSubEvent
    ) -> TokenClassification:
        self._verify_admitted(sub_event)
        with self._lock:
            return self._classify_locked(sub_event)

    def _binding_state_payload(
        self, bindings: Mapping[tuple[str, str], _TokenBinding]
    ) -> list[dict[str, object]]:
        return [bindings[key].as_record() for key in sorted(bindings)]

    def settle_sequence(
        self,
        sub_events: tuple[AdmittedAuditoryStructuralSubEvent, ...],
    ) -> AuditoryTokenSequenceReceipt:
        """Preserve an already-delimited physical order without sorting it."""
        if not isinstance(sub_events, tuple) or not sub_events:
            raise ValueError("auditory token sequence requires an immutable sub-event tuple")
        if len(sub_events) > MAX_TOKEN_OCCURRENCES_PER_SEQUENCE:
            raise ValueError("auditory token sequence exceeds its event boundary")
        for value in sub_events:
            self._verify_admitted(value)
        stream_id = sub_events[0].stream_id
        epoch = sub_events[0].source_time_start - Fraction(
            sub_events[0].source_sample_start, PCM_SAMPLE_RATE_HZ
        )
        seen: set[str] = set()
        prior: AdmittedAuditoryStructuralSubEvent | None = None
        for current in sub_events:
            if current.stream_id != stream_id:
                raise ValueError("auditory token sequence crosses stream epochs")
            if current.sub_event_id in seen:
                raise ValueError("auditory token sequence repeats a sub-event")
            seen.add(current.sub_event_id)
            current_epoch = current.source_time_start - Fraction(
                current.source_sample_start, PCM_SAMPLE_RATE_HZ
            )
            if current_epoch != epoch:
                raise ValueError("auditory token sequence source clocks disagree")
            if prior is not None and (
                current.source_sample_start < prior.source_sample_end
                or current.source_time_start < prior.source_time_end
            ):
                raise ValueError("auditory token sequence is overlapping or out of order")
            prior = current

        with self._lock:
            occurrences = []
            for ordinal, sub_event in enumerate(sub_events):
                classification = self._classify_locked(sub_event)
                occurrences.append(OrderedAuditoryTokenOccurrence(
                    ordinal=ordinal,
                    sub_event_id=sub_event.sub_event_id,
                    source_sample_start=sub_event.source_sample_start,
                    source_sample_end=sub_event.source_sample_end,
                    source_time_start=sub_event.source_time_start,
                    source_time_end=sub_event.source_time_end,
                    structural_fingerprint=sub_event.structural_fingerprint,
                    l5_authority_receipt_sha256=(
                        sub_event.l5_authority_receipt_sha256
                    ),
                    terminal_authority_receipt_sha256=(
                        sub_event.terminal_authority_receipt_sha256
                    ),
                    sub_event_admission_hmac_sha256=(
                        sub_event.admission_hmac_sha256
                    ),
                    classification_state=classification.state,
                    token_candidates=classification.candidates,
                    classification_authority_hmac_sha256=(
                        classification.authority_hmac_sha256
                    ),
                ))
            binding_state_sha256 = _digest(
                self._binding_state_payload(self._bindings)
            )
            sequence_base = {
                "binding_state_sha256": binding_state_sha256,
                "occurrences": [value.as_record() for value in occurrences],
                "schema": TOKEN_SEQUENCE_SCHEMA,
                "stream_id": stream_id,
            }
            sequence_id = _digest(sequence_base)
            provisional = AuditoryTokenSequenceReceipt(
                sequence_id=sequence_id,
                stream_id=stream_id,
                binding_state_sha256=binding_state_sha256,
                occurrences=tuple(occurrences),
                authority_hmac_sha256="",
            )
            payload = provisional.payload()
            if len(_canonical_bytes(payload)) > MAX_SEQUENCE_BYTES:
                raise RuntimeError("auditory token sequence receipt is too large")
            receipt = AuditoryTokenSequenceReceipt(
                sequence_id=sequence_id,
                stream_id=stream_id,
                binding_state_sha256=binding_state_sha256,
                occurrences=tuple(occurrences),
                authority_hmac_sha256=_hmac(self._sequence_key, payload),
            )
        self.verify_sequence(receipt)
        return receipt

    def verify_sequence(self, value: AuditoryTokenSequenceReceipt) -> None:
        if not isinstance(value, AuditoryTokenSequenceReceipt):
            raise TypeError("auditory token sequence receipt is not typed")
        _sha256(value.sequence_id, "auditory token sequence id")
        _sha256(value.binding_state_sha256, "auditory token binding state")
        _identifier(value.stream_id, "auditory token sequence stream")
        if (
            not isinstance(value.occurrences, tuple)
            or not value.occurrences
            or len(value.occurrences) > MAX_TOKEN_OCCURRENCES_PER_SEQUENCE
        ):
            raise ValueError("auditory token sequence occurrence boundary changed")
        prior_end = -1
        seen: set[str] = set()
        for ordinal, occurrence in enumerate(value.occurrences):
            if not isinstance(occurrence, OrderedAuditoryTokenOccurrence):
                raise TypeError("auditory token sequence contains an untyped occurrence")
            if occurrence.ordinal != ordinal:
                raise ValueError("auditory token sequence ordinal changed")
            if (
                occurrence.sub_event_id in seen
                or occurrence.source_sample_start < prior_end
            ):
                raise ValueError("auditory token sequence physical order changed")
            seen.add(occurrence.sub_event_id)
            prior_end = occurrence.source_sample_end
            candidates = occurrence.token_candidates
            if (
                occurrence.classification_state is TokenClassificationState.UNKNOWN
                and candidates
            ) or (
                occurrence.classification_state is TokenClassificationState.UNIQUE
                and len(candidates) != 1
            ) or (
                occurrence.classification_state is TokenClassificationState.AMBIGUOUS
                and len(candidates) < 2
            ):
                raise ValueError("auditory token classification cardinality changed")
            classification_payload = {
                "candidates": [candidate.as_record() for candidate in candidates],
                "schema": TOKEN_CLASSIFICATION_SCHEMA,
                "state": occurrence.classification_state.value,
                "sub_event_id": occurrence.sub_event_id,
            }
            if not hmac.compare_digest(
                occurrence.classification_authority_hmac_sha256,
                _hmac(self._classification_key, classification_payload),
            ):
                raise ValueError("auditory token classification authority changed")
        base = {
            "binding_state_sha256": value.binding_state_sha256,
            "occurrences": [item.as_record() for item in value.occurrences],
            "schema": TOKEN_SEQUENCE_SCHEMA,
            "stream_id": value.stream_id,
        }
        if value.sequence_id != _digest(base):
            raise ValueError("auditory token sequence identity changed")
        payload = value.payload()
        if len(_canonical_bytes(payload)) > MAX_SEQUENCE_BYTES:
            raise ValueError("auditory token sequence receipt exceeds its boundary")
        if not hmac.compare_digest(
            value.authority_hmac_sha256,
            _hmac(self._sequence_key, payload),
        ):
            raise ValueError("auditory token sequence authority changed")

    def _snapshot_payload(
        self,
        bindings: Mapping[tuple[str, str], _TokenBinding],
        accepted_nonces: set[str],
    ) -> dict[str, object]:
        return {
            "accepted_teacher_nonces": sorted(accepted_nonces),
            "bindings": self._binding_state_payload(bindings),
            "max_bindings": self._max_bindings,
            "schema": TOKEN_AUTHORITY_SNAPSHOT_SCHEMA,
        }

    def _snapshot_envelope(
        self,
        bindings: Mapping[tuple[str, str], _TokenBinding],
        accepted_nonces: set[str],
    ) -> dict[str, object]:
        payload = self._snapshot_payload(bindings, accepted_nonces)
        envelope = {
            "authority_hmac_sha256": _hmac(self._snapshot_key, payload),
            "payload": payload,
        }
        if len(_canonical_bytes(envelope)) > self._max_snapshot_bytes:
            raise RuntimeError("auditory token snapshot capacity is full")
        return envelope

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._snapshot_envelope(
                self._bindings, self._accepted_teacher_nonces
            )

    def restore(self, snapshot: object) -> None:
        """Verify completely and replace state while excluding concurrent writes."""
        with self._lock:
            self._restore_locked(snapshot)

    def _restore_locked(self, snapshot: object) -> None:
        if not isinstance(snapshot, Mapping) or set(snapshot) != {
            "authority_hmac_sha256", "payload"
        }:
            raise ValueError("auditory token snapshot envelope is malformed")
        if len(_canonical_bytes(snapshot)) > self._max_snapshot_bytes:
            raise ValueError("auditory token snapshot exceeds its byte boundary")
        payload = snapshot.get("payload")
        signature = snapshot.get("authority_hmac_sha256")
        if not isinstance(payload, Mapping) or set(payload) != {
            "accepted_teacher_nonces", "bindings", "max_bindings", "schema"
        }:
            raise ValueError("auditory token snapshot payload is malformed")
        if (
            payload.get("schema") != TOKEN_AUTHORITY_SNAPSHOT_SCHEMA
            or payload.get("max_bindings") != self._max_bindings
            or not isinstance(signature, str)
            or not hmac.compare_digest(signature, _hmac(self._snapshot_key, payload))
        ):
            raise ValueError("auditory token snapshot authority changed")
        raw_bindings = payload.get("bindings")
        raw_nonces = payload.get("accepted_teacher_nonces")
        if not isinstance(raw_bindings, list) or not isinstance(raw_nonces, list):
            raise ValueError("auditory token snapshot collections are malformed")
        if len(raw_bindings) > self._max_bindings:
            raise ValueError("auditory token snapshot exceeds binding capacity")
        bindings: dict[tuple[str, str], _TokenBinding] = {}
        nonces: set[str] = set()
        for raw in raw_bindings:
            if not isinstance(raw, Mapping) or set(raw) != {
                "designation",
                "physical_class_authority_receipt_sha256",
                "token_class_id",
                "token_form",
            }:
                raise ValueError("auditory token binding record is malformed")
            designation_raw = raw.get("designation")
            if not isinstance(designation_raw, Mapping) or set(designation_raw) != {
                "authority_hmac_sha256",
                "nonce",
                "physical_class_authority_receipt_sha256",
                "schema",
                "sub_event_admission_hmac_sha256",
                "sub_event_id",
                "token_class_id",
                "token_form",
                "unicode_scalars",
            }:
                raise ValueError("teacher token designation record is malformed")
            if designation_raw.get("schema") != TEACHER_TOKEN_DESIGNATION_SCHEMA:
                raise ValueError("teacher token designation schema changed")
            scalars = designation_raw.get("unicode_scalars")
            if not isinstance(scalars, list):
                raise ValueError("teacher token Unicode scalars are malformed")
            designation = TeacherTokenDesignationReceipt(
                nonce=designation_raw.get("nonce"),
                sub_event_id=designation_raw.get("sub_event_id"),
                sub_event_admission_hmac_sha256=designation_raw.get(
                    "sub_event_admission_hmac_sha256"
                ),
                physical_class_authority_receipt_sha256=designation_raw.get(
                    "physical_class_authority_receipt_sha256"
                ),
                token_class_id=designation_raw.get("token_class_id"),
                token_form=designation_raw.get("token_form"),
                unicode_scalars=tuple(scalars),
                authority_hmac_sha256=designation_raw.get(
                    "authority_hmac_sha256"
                ),
            )
            self._verify_designation(designation)
            binding = _TokenBinding(
                physical_class_authority_receipt_sha256=raw.get(
                    "physical_class_authority_receipt_sha256"
                ),
                token_class_id=raw.get("token_class_id"),
                token_form=raw.get("token_form"),
                designation=designation,
            )
            if (
                binding.physical_class_authority_receipt_sha256
                != designation.physical_class_authority_receipt_sha256
                or binding.token_class_id != designation.token_class_id
                or binding.token_form != designation.token_form
                or binding.key in bindings
            ):
                raise ValueError("auditory token binding differs from its designation")
            bindings[binding.key] = binding
            nonces.add(designation.nonce)
        supplied_nonces = {_nonce(value) for value in raw_nonces}
        if (
            len(supplied_nonces) != len(raw_nonces)
            or supplied_nonces != nonces
        ):
            raise ValueError("auditory token snapshot nonce ledger changed")
        forms: dict[str, str] = {}
        for binding in bindings.values():
            previous = forms.setdefault(binding.token_class_id, binding.token_form)
            if previous != binding.token_form:
                raise ValueError("auditory token snapshot has conflicting class forms")
        self._snapshot_envelope(bindings, supplied_nonces)
        self._bindings = bindings
        self._accepted_teacher_nonces = supplied_nonces


__all__ = [
    "ADMITTED_SUB_EVENT_SCHEMA",
    "TEACHER_TOKEN_DESIGNATION_SCHEMA",
    "TOKEN_AUTHORITY_SNAPSHOT_SCHEMA",
    "TOKEN_CLASSIFICATION_SCHEMA",
    "TOKEN_SEQUENCE_SCHEMA",
    "AdmittedAuditoryStructuralSubEvent",
    "AuditoryTokenSequenceAuthority",
    "AuditoryTokenSequenceReceipt",
    "OrderedAuditoryTokenOccurrence",
    "TeacherTokenDesignationReceipt",
    "TokenClassIdentity",
    "TokenClassification",
    "TokenClassificationState",
]
