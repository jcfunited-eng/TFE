"""Bounded learned continuity for exact anonymous W1 audiovisual evidence.

This owner never names a source.  It carries one anonymous lineage only when
the prior world observation is exactly the current before-observation and the
prior matched visual geometry has exactly one continuation in the current
candidate field.  The complete authenticated sight, body, and binaural L5
field remains attached to the latest learned relation.  Transition memory is
bounded and receipt-only; raw media, words, chi, Atlas addresses, scores, and
control identities never enter this authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    CORRESPONDENCE_AUTHORITY_DOMAIN,
    CORRESPONDENCE_AUTHORITY_SCHEMA,
    W1AnonymousAcousticVisualCorrespondence,
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import EAR_IDS


CONTINUITY_SCHEMA = "guala.w1.anonymous_audiovisual_continuity.v1"
CONTINUITY_AUTHORITY_SCHEMA = (
    "guala.w1.anonymous_audiovisual_continuity.authority.v1"
)
CONTINUITY_AUTHORITY_DOMAIN = (
    b"guala.w1.anonymous_audiovisual_continuity.authority.v1\0"
)
LINEAGE_AUTHORITY_DOMAIN = (
    b"guala.w1.anonymous_audiovisual_lineage.authority.v1\0"
)
SNAPSHOT_SCHEMA = "guala.w1.anonymous_audiovisual_continuity.snapshot.v1"
SNAPSHOT_AUTHORITY_DOMAIN = (
    b"guala.w1.anonymous_audiovisual_continuity.snapshot.v1\0"
)
MAX_CONTINUITY_AUTHORITY_BYTES = 4 * 1024 * 1024
RELATIONS = ("first_observation", "recurrence", "structural_change")


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


def _key(value: bytes | str, name: str) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not value:
        raise ValueError(f"{name} is unavailable")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise ValueError("continuity geometry must remain exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{name} fraction is not canonical")
    return result


def _geometry_payload(
    geometry: tuple[Fraction, Fraction, Fraction, Fraction],
) -> list[str]:
    if len(geometry) != 4:
        raise ValueError("continuity geometry cardinality changed")
    return [_fraction_text(value) for value in geometry]


def _geometry_from_record(value: object, name: str) -> tuple[Fraction, ...]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{name} cardinality changed")
    return tuple(
        _fraction(item, f"{name}[{index}]")
        for index, item in enumerate(value)
    )


def _verify_serialized_full_fields(correspondence: dict[str, object]) -> None:
    def verify_sense(value: object, sense_name: str) -> None:
        if not isinstance(value, dict) or value.get("sense") != sense_name:
            raise ValueError(f"continuity {sense_name} authority changed")
        substreams = value.get("substreams")
        if not isinstance(substreams, list) or not substreams:
            raise ValueError(f"continuity {sense_name} field is empty")
        for substream in substreams:
            if not isinstance(substream, dict):
                raise ValueError(f"continuity {sense_name} substream changed")
            field_tuples = substream.get("field_tuples")
            if not isinstance(field_tuples, list) or not field_tuples:
                raise ValueError(f"continuity {sense_name} tuples are empty")
            for field_tuple in field_tuples:
                if not isinstance(field_tuple, dict):
                    raise ValueError(
                        f"continuity {sense_name} field tuple changed"
                    )
                fields = field_tuple.get("fields")
                if (
                    not isinstance(fields, list)
                    or tuple(
                        item[0]
                        for item in fields
                        if isinstance(item, list) and len(item) == 2
                    ) != DSF_FIELD_ORDER
                ):
                    raise ValueError(
                        f"continuity {sense_name} full field changed"
                    )

    verify_sense(correspondence.get("sight_authority"), "sight")
    verify_sense(correspondence.get("body_authority"), "body")
    auditory = correspondence.get("auditory_l5_authority")
    ears = auditory.get("ears") if isinstance(auditory, dict) else None
    if (
        not isinstance(ears, list)
        or tuple(
            ear.get("ear_id") if isinstance(ear, dict) else None
            for ear in ears
        ) != EAR_IDS
    ):
        raise ValueError("continuity two-ear field changed")
    for ear in ears:
        channels = ear.get("channels")
        if not isinstance(channels, list) or len(channels) != COCHLEAR_CHANNEL_COUNT:
            raise ValueError("continuity cochlear field changed")
        for channel in channels:
            if not isinstance(channel, dict):
                raise ValueError("continuity cochlear channel changed")
            for component_name in ("pressure", "carrier_phase_advance"):
                component = channel.get(component_name)
                field_tuples = (
                    component.get("field_tuples")
                    if isinstance(component, dict) else None
                )
                if not isinstance(field_tuples, list) or not field_tuples:
                    raise ValueError("continuity auditory tuples are empty")
                for field_tuple in field_tuples:
                    fields = (
                        field_tuple.get("fields")
                        if isinstance(field_tuple, dict) else None
                    )
                    if (
                        not isinstance(fields, list)
                        or tuple(
                            item[0]
                            for item in fields
                            if isinstance(item, list) and len(item) == 2
                        ) != DSF_FIELD_ORDER
                    ):
                        raise ValueError(
                            "continuity auditory full field changed"
                        )


def _verify_correspondence_record(
    value: object,
    physical_authority_key: bytes,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("continuity correspondence record changed")
    record = dict(value)
    signature = record.pop("authority_hmac_sha256", None)
    receipt = record.pop("authority_receipt_sha256", None)
    _sha256(signature, "continuity correspondence HMAC")
    _sha256(receipt, "continuity correspondence receipt")
    if record.get("schema") != CORRESPONDENCE_AUTHORITY_SCHEMA:
        raise ValueError("continuity correspondence schema changed")
    encoded = _canonical(record)
    expected_signature = hmac.new(
        physical_authority_key,
        CORRESPONDENCE_AUTHORITY_DOMAIN + encoded,
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(signature, expected_signature)
        or receipt
        != _digest({
            "authority_hmac_sha256": expected_signature,
            "payload": record,
        })
    ):
        raise ValueError("continuity correspondence authority changed")
    _verify_serialized_full_fields(record)
    forbidden_keys = {
        "body_id",
        "object_id",
        "port_id",
        "source_tag",
        "source_tags",
        "routing_chi",
        "routing_chis",
        "transcript",
        "pcm_s16le",
        "left_pcm_s16le",
        "right_pcm_s16le",
    }

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if forbidden_keys.intersection(node):
                raise ValueError("continuity retained forbidden identity or media")
            for nested in node.values():
                walk(nested)
        elif isinstance(node, list):
            for nested in node:
                walk(nested)

    walk(record)
    return {
        **record,
        "authority_hmac_sha256": signature,
        "authority_receipt_sha256": receipt,
    }


@dataclass(frozen=True, slots=True)
class W1AnonymousAudiovisualContinuityExperience:
    lineage_token_sha256: str
    relation: str
    prior_continuity_receipt_sha256: str | None
    world_observation_before_receipt_sha256: str
    world_observation_after_receipt_sha256: str
    matched_before_geometry: tuple[Fraction, Fraction, Fraction, Fraction]
    matched_after_geometry: tuple[Fraction, Fraction, Fraction, Fraction]
    correspondence: W1AnonymousAcousticVisualCorrespondence
    physical_evidence_receipt_sha256: str
    structural_fingerprint: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def structural_payload(self) -> dict[str, object]:
        return {
            "correspondence": self.correspondence.structural_payload(),
            "lineage_token_sha256": self.lineage_token_sha256,
            "matched_after_geometry": _geometry_payload(
                self.matched_after_geometry
            ),
            "matched_before_geometry": _geometry_payload(
                self.matched_before_geometry
            ),
            "prior_continuity_receipt_sha256": (
                self.prior_continuity_receipt_sha256
            ),
            "relation": self.relation,
            "schema": CONTINUITY_SCHEMA,
            "world_observation_after_receipt_sha256": (
                self.world_observation_after_receipt_sha256
            ),
            "world_observation_before_receipt_sha256": (
                self.world_observation_before_receipt_sha256
            ),
        }

    def authority_payload(self) -> dict[str, object]:
        return {
            "correspondence_authority": self.correspondence.authority_record(),
            "physical_evidence_receipt_sha256": (
                self.physical_evidence_receipt_sha256
            ),
            "schema": CONTINUITY_AUTHORITY_SCHEMA,
            "structural_fingerprint": self.structural_fingerprint,
            **{
                key: value
                for key, value in self.structural_payload().items()
                if key not in {"correspondence", "schema"}
            },
        }

    def verify_structure(self) -> None:
        self.correspondence.verify_structure()
        for value, name in (
            (self.lineage_token_sha256, "continuity lineage"),
            (
                self.world_observation_before_receipt_sha256,
                "continuity world before",
            ),
            (
                self.world_observation_after_receipt_sha256,
                "continuity world after",
            ),
            (self.physical_evidence_receipt_sha256, "physical evidence"),
        ):
            _sha256(value, name)
        if self.prior_continuity_receipt_sha256 is not None:
            _sha256(
                self.prior_continuity_receipt_sha256,
                "prior continuity",
            )
        if self.relation not in RELATIONS:
            raise ValueError("anonymous continuity relation changed")
        if (self.relation == "first_observation") != (
            self.prior_continuity_receipt_sha256 is None
        ):
            raise ValueError("anonymous continuity ancestry changed")
        candidate = self.correspondence.candidates[
            self.correspondence.matched_ordinal
        ]
        if (
            candidate.before_geometry != self.matched_before_geometry
            or candidate.after_geometry != self.matched_after_geometry
        ):
            raise ValueError("anonymous continuity matched geometry changed")
        structural = _digest(self.structural_payload())
        if structural != self.structural_fingerprint:
            raise ValueError("anonymous continuity full structure changed")

    def verify(
        self,
        authority_key: bytes | str,
        physical_authority_key: bytes | str,
    ) -> None:
        key = _key(authority_key, "continuity authority key")
        physical_key = _key(
            physical_authority_key,
            "continuity physical authority key",
        )
        self.verify_structure()
        self.correspondence.verify(physical_key)
        payload = self.authority_payload()
        encoded = _canonical(payload)
        expected_signature = hmac.new(
            key,
            CONTINUITY_AUTHORITY_DOMAIN + encoded,
            hashlib.sha256,
        ).hexdigest()
        if (
            len(encoded) > MAX_CONTINUITY_AUTHORITY_BYTES
            or not hmac.compare_digest(
                expected_signature,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_signature,
                "payload": payload,
            })
        ):
            raise ValueError("anonymous continuity authority changed")

    def authority_record(self) -> dict[str, object]:
        return {
            **self.authority_payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class W1AnonymousAudiovisualContinuityTransition:
    lineage_token_sha256: str
    relation: str
    prior_continuity_receipt_sha256: str
    current_continuity_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "current_continuity_receipt_sha256": (
                self.current_continuity_receipt_sha256
            ),
            "lineage_token_sha256": self.lineage_token_sha256,
            "prior_continuity_receipt_sha256": (
                self.prior_continuity_receipt_sha256
            ),
            "relation": self.relation,
        }

    def verify(self) -> None:
        for value, name in (
            (self.lineage_token_sha256, "continuity transition lineage"),
            (
                self.prior_continuity_receipt_sha256,
                "continuity transition prior",
            ),
            (
                self.current_continuity_receipt_sha256,
                "continuity transition current",
            ),
        ):
            _sha256(value, name)
        if self.relation not in ("recurrence", "structural_change"):
            raise ValueError("continuity transition relation changed")


@dataclass(frozen=True, slots=True)
class _ContinuityAnchor:
    lineage_token_sha256: str
    matched_after_geometry: tuple[Fraction, Fraction, Fraction, Fraction]
    world_observation_after_receipt_sha256: str
    correspondence_structural_fingerprint: str
    authority_receipt_sha256: str
    authority_record: dict[str, object]


@dataclass(frozen=True, slots=True)
class _CommitUndo:
    authority_receipt_sha256: str
    prior_anchor: _ContinuityAnchor | None
    prior_transitions: tuple[W1AnonymousAudiovisualContinuityTransition, ...]
    prior_settled: int
    prior_generation: int
    atomic_sequence_token: str | None


@dataclass(slots=True)
class _AtomicSequenceState:
    token: str
    owner_thread_id: int
    anchor: _ContinuityAnchor | None
    transitions: list[W1AnonymousAudiovisualContinuityTransition]
    settled: int
    generation: int


@dataclass(frozen=True, slots=True)
class _AtomicSequenceCommitUndo:
    sequence: _AtomicSequenceState
    prior_anchor: _ContinuityAnchor | None
    prior_transitions: tuple[W1AnonymousAudiovisualContinuityTransition, ...]
    prior_settled: int
    prior_generation: int


def _anchor_from_experience(
    experience: W1AnonymousAudiovisualContinuityExperience,
) -> _ContinuityAnchor:
    return _ContinuityAnchor(
        lineage_token_sha256=experience.lineage_token_sha256,
        matched_after_geometry=experience.matched_after_geometry,
        world_observation_after_receipt_sha256=(
            experience.world_observation_after_receipt_sha256
        ),
        correspondence_structural_fingerprint=(
            experience.correspondence.structural_fingerprint
        ),
        authority_receipt_sha256=experience.authority_receipt_sha256,
        authority_record=experience.authority_record(),
    )


class W1AnonymousAudiovisualContinuityOwner:
    """Transactional capacity-one owner of learned anonymous continuity."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        physical_authority_key: bytes | str,
        max_transitions: int = 64,
    ) -> None:
        if (
            isinstance(max_transitions, bool)
            or not isinstance(max_transitions, int)
            or max_transitions <= 0
        ):
            raise ValueError("anonymous continuity transition capacity is invalid")
        self._key = _key(authority_key, "continuity authority key")
        self._physical_key = _key(
            physical_authority_key,
            "continuity physical authority key",
        )
        self._max_transitions = max_transitions
        self._anchor: _ContinuityAnchor | None = None
        self._prepared: W1AnonymousAudiovisualContinuityExperience | None = None
        self._transitions: list[
            W1AnonymousAudiovisualContinuityTransition
        ] = []
        self._settled = 0
        self._generation = 0
        self._atomic_sequence: _AtomicSequenceState | None = None
        self._lock = threading.RLock()

    def _require_sequence_owner_locked(self) -> None:
        sequence = self._atomic_sequence
        if (
            sequence is not None
            and sequence.owner_thread_id != threading.get_ident()
        ):
            raise RuntimeError(
                "anonymous continuity is reserved by an atomic sequence"
            )

    def begin_atomic_sequence(self) -> str:
        with self._lock:
            if self._prepared is not None or self._atomic_sequence is not None:
                raise RuntimeError("anonymous continuity transaction is active")
            token = secrets.token_urlsafe(24)
            self._atomic_sequence = _AtomicSequenceState(
                token=token,
                owner_thread_id=threading.get_ident(),
                anchor=self._anchor,
                transitions=list(self._transitions),
                settled=self._settled,
                generation=self._generation,
            )
            return token

    def verify_atomic_sequence(self, token: str) -> None:
        with self._lock:
            sequence = self._atomic_sequence
            if (
                sequence is None
                or sequence.token != token
                or sequence.owner_thread_id != threading.get_ident()
                or self._prepared is not None
            ):
                raise ValueError("anonymous continuity atomic sequence changed")

    def commit_atomic_sequence(
        self,
        token: str,
    ) -> _AtomicSequenceCommitUndo:
        with self._lock:
            self.verify_atomic_sequence(token)
            sequence = self._atomic_sequence
            if sequence is None:
                raise RuntimeError("anonymous continuity sequence disappeared")
            undo = _AtomicSequenceCommitUndo(
                sequence=sequence,
                prior_anchor=self._anchor,
                prior_transitions=tuple(self._transitions),
                prior_settled=self._settled,
                prior_generation=self._generation,
            )
            self._anchor = sequence.anchor
            self._transitions = sequence.transitions
            self._settled = sequence.settled
            self._generation = sequence.generation
            self._atomic_sequence = None
            return undo

    def rollback_committed_atomic_sequence(
        self,
        undo: _AtomicSequenceCommitUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(undo, _AtomicSequenceCommitUndo)
                or self._atomic_sequence is not None
                or self._anchor != undo.sequence.anchor
                or self._transitions != undo.sequence.transitions
                or self._settled != undo.sequence.settled
                or self._generation != undo.sequence.generation
            ):
                raise ValueError("anonymous continuity published sequence changed")
            self._anchor = undo.prior_anchor
            self._transitions = list(undo.prior_transitions)
            self._settled = undo.prior_settled
            self._generation = undo.prior_generation
            self._atomic_sequence = undo.sequence

    def rollback_atomic_sequence(self, token: str) -> None:
        with self._lock:
            self.verify_atomic_sequence(token)
            self._atomic_sequence = None

    def prepare(
        self,
        correspondence: W1AnonymousAcousticVisualCorrespondence,
        evidence_receipt: W1PhysicalEvidenceReceipt,
    ) -> W1AnonymousAudiovisualContinuityExperience:
        if not isinstance(
            correspondence,
            W1AnonymousAcousticVisualCorrespondence,
        ):
            raise TypeError("typed anonymous audiovisual correspondence is required")
        if not isinstance(evidence_receipt, W1PhysicalEvidenceReceipt):
            raise TypeError("typed physical evidence receipt is required")
        correspondence.verify(self._physical_key)
        evidence_receipt.verify(self._physical_key)
        if (
            evidence_receipt.anonymous_av_correspondence_receipt_sha256
            != correspondence.authority_receipt_sha256
        ):
            raise ValueError("continuity evidence differs from correspondence")
        candidate = correspondence.candidates[correspondence.matched_ordinal]
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared is not None:
                raise RuntimeError("anonymous continuity preparation is active")
            sequence = self._atomic_sequence
            prior = sequence.anchor if sequence is not None else self._anchor
            relation = "first_observation"
            prior_receipt = None
            if prior is not None and (
                evidence_receipt.world_observation_before_receipt_sha256
                == prior.world_observation_after_receipt_sha256
            ):
                matches = tuple(
                    item.ordinal
                    for item in correspondence.candidates
                    if item.before_geometry == prior.matched_after_geometry
                )
                if len(matches) > 1:
                    raise ValueError(
                        "anonymous continuity geometry is ambiguous"
                    )
                if matches == (correspondence.matched_ordinal,):
                    prior_receipt = prior.authority_receipt_sha256
                    relation = (
                        "recurrence"
                        if correspondence.structural_fingerprint
                        == prior.correspondence_structural_fingerprint
                        else "structural_change"
                    )
            lineage = (
                prior.lineage_token_sha256
                if prior_receipt is not None and prior is not None
                else hmac.new(
                    self._key,
                    LINEAGE_AUTHORITY_DOMAIN + _canonical({
                        "correspondence_authority_receipt_sha256": (
                            correspondence.authority_receipt_sha256
                        ),
                        "world_observation_before_receipt_sha256": (
                            evidence_receipt
                            .world_observation_before_receipt_sha256
                        ),
                    }),
                    hashlib.sha256,
                ).hexdigest()
            )
            structural_payload = {
                "correspondence": correspondence.structural_payload(),
                "lineage_token_sha256": lineage,
                "matched_after_geometry": _geometry_payload(
                    candidate.after_geometry
                ),
                "matched_before_geometry": _geometry_payload(
                    candidate.before_geometry
                ),
                "prior_continuity_receipt_sha256": prior_receipt,
                "relation": relation,
                "schema": CONTINUITY_SCHEMA,
                "world_observation_after_receipt_sha256": (
                    evidence_receipt
                    .world_observation_after_receipt_sha256
                ),
                "world_observation_before_receipt_sha256": (
                    evidence_receipt
                    .world_observation_before_receipt_sha256
                ),
            }
            fingerprint = _digest(structural_payload)
            provisional = W1AnonymousAudiovisualContinuityExperience(
                lineage_token_sha256=lineage,
                relation=relation,
                prior_continuity_receipt_sha256=prior_receipt,
                world_observation_before_receipt_sha256=(
                    evidence_receipt
                    .world_observation_before_receipt_sha256
                ),
                world_observation_after_receipt_sha256=(
                    evidence_receipt
                    .world_observation_after_receipt_sha256
                ),
                matched_before_geometry=candidate.before_geometry,
                matched_after_geometry=candidate.after_geometry,
                correspondence=correspondence,
                physical_evidence_receipt_sha256=(
                    evidence_receipt.authority_receipt_sha256
                ),
                structural_fingerprint=fingerprint,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            payload = provisional.authority_payload()
            signature = hmac.new(
                self._key,
                CONTINUITY_AUTHORITY_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            result = W1AnonymousAudiovisualContinuityExperience(
                lineage_token_sha256=provisional.lineage_token_sha256,
                relation=provisional.relation,
                prior_continuity_receipt_sha256=(
                    provisional.prior_continuity_receipt_sha256
                ),
                world_observation_before_receipt_sha256=(
                    provisional.world_observation_before_receipt_sha256
                ),
                world_observation_after_receipt_sha256=(
                    provisional.world_observation_after_receipt_sha256
                ),
                matched_before_geometry=provisional.matched_before_geometry,
                matched_after_geometry=provisional.matched_after_geometry,
                correspondence=provisional.correspondence,
                physical_evidence_receipt_sha256=(
                    provisional.physical_evidence_receipt_sha256
                ),
                structural_fingerprint=provisional.structural_fingerprint,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )
            result.verify(self._key, self._physical_key)
            self._prepared = result
            return result

    def verify_experience(
        self,
        experience: W1AnonymousAudiovisualContinuityExperience,
    ) -> None:
        if not isinstance(
            experience,
            W1AnonymousAudiovisualContinuityExperience,
        ):
            raise TypeError("typed anonymous continuity experience is required")
        experience.verify(self._key, self._physical_key)

    def commit_prepared(
        self,
        experience: W1AnonymousAudiovisualContinuityExperience,
    ) -> _CommitUndo:
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared != experience:
                raise ValueError("anonymous continuity preparation changed")
            sequence = self._atomic_sequence
            prior_anchor = sequence.anchor if sequence is not None else self._anchor
            transitions = (
                sequence.transitions if sequence is not None else self._transitions
            )
            settled = sequence.settled if sequence is not None else self._settled
            generation = (
                sequence.generation if sequence is not None else self._generation
            )
            undo = _CommitUndo(
                authority_receipt_sha256=experience.authority_receipt_sha256,
                prior_anchor=prior_anchor,
                prior_transitions=tuple(transitions),
                prior_settled=settled,
                prior_generation=generation,
                atomic_sequence_token=(sequence.token if sequence else None),
            )
            if experience.prior_continuity_receipt_sha256 is not None:
                transition = W1AnonymousAudiovisualContinuityTransition(
                    lineage_token_sha256=experience.lineage_token_sha256,
                    relation=experience.relation,
                    prior_continuity_receipt_sha256=(
                        experience.prior_continuity_receipt_sha256
                    ),
                    current_continuity_receipt_sha256=(
                        experience.authority_receipt_sha256
                    ),
                )
                transition.verify()
                transitions.append(transition)
                del transitions[:-self._max_transitions]
            anchor = _anchor_from_experience(experience)
            if sequence is not None:
                sequence.anchor = anchor
                sequence.settled += 1
                sequence.generation += 1
            else:
                self._anchor = anchor
                self._settled += 1
                self._generation += 1
            self._prepared = None
            return undo

    def rollback_committed(self, undo: _CommitUndo) -> None:
        with self._lock:
            self._require_sequence_owner_locked()
            sequence = self._atomic_sequence
            anchor = sequence.anchor if sequence is not None else self._anchor
            settled = sequence.settled if sequence is not None else self._settled
            generation = (
                sequence.generation if sequence is not None else self._generation
            )
            if (
                anchor is None
                or anchor.authority_receipt_sha256
                != undo.authority_receipt_sha256
                or settled != undo.prior_settled + 1
                or generation != undo.prior_generation + 1
                or (sequence.token if sequence else None)
                != undo.atomic_sequence_token
            ):
                raise ValueError("anonymous continuity rollback authority changed")
            if sequence is not None:
                sequence.anchor = undo.prior_anchor
                sequence.transitions = list(undo.prior_transitions)
                sequence.settled = undo.prior_settled
                sequence.generation = undo.prior_generation
            else:
                self._anchor = undo.prior_anchor
                self._transitions = list(undo.prior_transitions)
                self._settled = undo.prior_settled
                self._generation = undo.prior_generation

    def discard_prepared(
        self,
        experience: W1AnonymousAudiovisualContinuityExperience,
    ) -> None:
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared != experience:
                raise ValueError("anonymous continuity preparation changed")
            self._prepared = None

    def _snapshot_payload_locked(self) -> dict[str, object]:
        return {
            "generation": self._generation,
            "latest": (
                self._anchor.authority_record
                if self._anchor is not None else None
            ),
            "schema": SNAPSHOT_SCHEMA,
            "settled": self._settled,
            "transition_capacity": self._max_transitions,
            "transitions": [value.payload() for value in self._transitions],
        }

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            payload = self._snapshot_payload_locked()
            signature = hmac.new(
                self._key,
                SNAPSHOT_AUTHORITY_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            result = _canonical({
                "authority_hmac_sha256": signature,
                "authority_receipt_sha256": _digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
                "payload": payload,
            })
            if len(result) > MAX_CONTINUITY_AUTHORITY_BYTES:
                raise ValueError("anonymous continuity snapshot exceeds its boundary")
            return result

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > MAX_CONTINUITY_AUTHORITY_BYTES
        ):
            raise ValueError("anonymous continuity snapshot boundary changed")
        try:
            record = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("anonymous continuity snapshot is unreadable") from error
        if not isinstance(record, dict) or not isinstance(
            record.get("payload"), dict
        ):
            raise ValueError("anonymous continuity snapshot changed")
        payload = record["payload"]
        signature = record.get("authority_hmac_sha256")
        receipt = record.get("authority_receipt_sha256")
        expected_signature = hmac.new(
            self._key,
            SNAPSHOT_AUTHORITY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(str(signature), expected_signature)
            or receipt
            != _digest({
                "authority_hmac_sha256": expected_signature,
                "payload": payload,
            })
            or payload.get("schema") != SNAPSHOT_SCHEMA
        ):
            raise ValueError("anonymous continuity snapshot authority changed")
        capacity = payload.get("transition_capacity")
        transitions_raw = payload.get("transitions")
        settled = payload.get("settled")
        generation = payload.get("generation")
        if (
            capacity != self._max_transitions
            or not isinstance(transitions_raw, list)
            or len(transitions_raw) > self._max_transitions
            or isinstance(settled, bool)
            or not isinstance(settled, int)
            or settled < 0
            or isinstance(generation, bool)
            or not isinstance(generation, int)
            or generation < 0
            or generation != settled
        ):
            raise ValueError("anonymous continuity snapshot extent changed")
        transitions = []
        for value in transitions_raw:
            if not isinstance(value, dict):
                raise ValueError("anonymous continuity transition changed")
            transition = W1AnonymousAudiovisualContinuityTransition(
                lineage_token_sha256=value.get("lineage_token_sha256"),
                relation=value.get("relation"),
                prior_continuity_receipt_sha256=(
                    value.get("prior_continuity_receipt_sha256")
                ),
                current_continuity_receipt_sha256=(
                    value.get("current_continuity_receipt_sha256")
                ),
            )
            transition.verify()
            transitions.append(transition)
        latest = payload.get("latest")
        anchor = None
        if latest is not None:
            if not isinstance(latest, dict):
                raise ValueError("anonymous continuity latest record changed")
            latest_record = dict(latest)
            latest_signature = latest_record.pop("authority_hmac_sha256", None)
            latest_receipt = latest_record.pop(
                "authority_receipt_sha256", None
            )
            if latest_record.get("schema") != CONTINUITY_AUTHORITY_SCHEMA:
                raise ValueError("anonymous continuity latest schema changed")
            expected_latest_signature = hmac.new(
                self._key,
                CONTINUITY_AUTHORITY_DOMAIN + _canonical(latest_record),
                hashlib.sha256,
            ).hexdigest()
            if (
                not hmac.compare_digest(
                    str(latest_signature), expected_latest_signature
                )
                or latest_receipt
                != _digest({
                    "authority_hmac_sha256": expected_latest_signature,
                    "payload": latest_record,
                })
            ):
                raise ValueError("anonymous continuity latest authority changed")
            correspondence_record = _verify_correspondence_record(
                latest_record.get("correspondence_authority"),
                self._physical_key,
            )
            candidates = correspondence_record.get("candidates")
            matched = correspondence_record.get("matched_ordinal")
            if (
                not isinstance(candidates, list)
                or isinstance(matched, bool)
                or not isinstance(matched, int)
                or not 0 <= matched < len(candidates)
                or not isinstance(candidates[matched], dict)
            ):
                raise ValueError("anonymous continuity matched candidate changed")
            candidate = candidates[matched]
            after_geometry = _geometry_from_record(
                candidate.get("after_geometry"),
                "continuity latest after geometry",
            )
            expected_after = _geometry_from_record(
                latest_record.get("matched_after_geometry"),
                "continuity authority after geometry",
            )
            if after_geometry != expected_after:
                raise ValueError("anonymous continuity latest geometry changed")
            lineage = _sha256(
                latest_record.get("lineage_token_sha256"),
                "continuity latest lineage",
            )
            world_after = _sha256(
                latest_record.get(
                    "world_observation_after_receipt_sha256"
                ),
                "continuity latest world after",
            )
            correspondence_fingerprint = _sha256(
                correspondence_record.get("structural_fingerprint"),
                "continuity latest correspondence structure",
            )
            anchor = _ContinuityAnchor(
                lineage_token_sha256=lineage,
                matched_after_geometry=after_geometry,
                world_observation_after_receipt_sha256=world_after,
                correspondence_structural_fingerprint=(
                    correspondence_fingerprint
                ),
                authority_receipt_sha256=_sha256(
                    latest_receipt,
                    "continuity latest receipt",
                ),
                authority_record={
                    **latest_record,
                    "authority_hmac_sha256": latest_signature,
                    "authority_receipt_sha256": latest_receipt,
                },
            )
        if (settled == 0) != (anchor is None):
            raise ValueError("anonymous continuity latest extent changed")
        with self._lock:
            if self._prepared is not None or self._atomic_sequence is not None:
                raise RuntimeError("anonymous continuity restore is not settled")
            self._anchor = anchor
            self._transitions = transitions
            self._settled = settled
            self._generation = generation

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "atomic_sequence": int(self._atomic_sequence is not None),
                "atomic_sequence_staged_settled": (
                    self._atomic_sequence.settled - self._settled
                    if self._atomic_sequence is not None else 0
                ),
                "generation": self._generation,
                "has_latest": self._anchor is not None,
                "max_authority_bytes": MAX_CONTINUITY_AUTHORITY_BYTES,
                "prepared": int(self._prepared is not None),
                "schema": "guala.w1.anonymous_audiovisual_continuity.status.v1",
                "settled": self._settled,
                "transition_capacity": self._max_transitions,
                "transitions": len(self._transitions),
            }


__all__ = (
    "MAX_CONTINUITY_AUTHORITY_BYTES",
    "W1AnonymousAudiovisualContinuityExperience",
    "W1AnonymousAudiovisualContinuityOwner",
    "W1AnonymousAudiovisualContinuityTransition",
)
