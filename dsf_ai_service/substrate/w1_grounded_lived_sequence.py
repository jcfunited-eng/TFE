"""Authenticated ordered lived sequences cited by grounded vocal responses.

This authority adds no story labels, topic labels, transcripts, or tutor
answers.  It proves one structural fact: a grounded vocal response cites roots
that occur in an exact, source-disjoint, temporally ordered sequence of lived
W1 settlements.  The response and challenge remain the grounded cues retained
by ``W1GroundedDemonstrationOwner``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.w1_grounded_demonstration import (
    W1GroundedDemonstration,
    W1GroundedDemonstrationOwner,
)


LIVED_SEQUENCE_PROFILE_SCHEMA = "guala.w1.grounded_lived_sequence.profile.v1"
LIVED_SEQUENCE_EVENT_SCHEMA = "guala.w1.grounded_lived_sequence.event.v1"
LIVED_SEQUENCE_PROOF_SCHEMA = "guala.w1.grounded_lived_sequence.proof.v1"
LIVED_SEQUENCE_STATE_SCHEMA = "guala.w1.grounded_lived_sequence.state.v1"
LIVED_SEQUENCE_ENVELOPE_SCHEMA = (
    "guala.w1.grounded_lived_sequence.state_hmac.v1"
)
_PROOF_DOMAIN = b"guala-w1-grounded-lived-sequence-proof-v1\0"
_STATE_DOMAIN = b"guala-w1-grounded-lived-sequence-state-v1\0"
_HEX = frozenset("0123456789abcdef")


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
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("lived sequence key boundary changed")
    return result


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("lived sequence time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class W1GroundedLivedSequenceProfile:
    profile_id: str
    max_proofs: int
    max_events_per_proof: int
    max_roots_per_event: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_proofs: int,
        max_events_per_proof: int,
        max_roots_per_event: int,
        max_state_bytes: int,
    ) -> "W1GroundedLivedSequenceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("lived sequence profile identifier changed")
        provisional = cls(
            profile_id=profile_id,
            max_proofs=_positive(max_proofs, "lived sequence proofs"),
            max_events_per_proof=_positive(
                max_events_per_proof, "lived sequence events"
            ),
            max_roots_per_event=_positive(
                max_roots_per_event, "lived sequence roots"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "lived sequence state"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_proofs=provisional.max_proofs,
            max_events_per_proof=provisional.max_events_per_proof,
            max_roots_per_event=provisional.max_roots_per_event,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_events_per_proof": self.max_events_per_proof,
            "max_proofs": self.max_proofs,
            "max_roots_per_event": self.max_roots_per_event,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": LIVED_SEQUENCE_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        _positive(self.max_proofs, "lived sequence proofs")
        _positive(self.max_events_per_proof, "lived sequence events")
        _positive(self.max_roots_per_event, "lived sequence roots")
        _positive(self.max_state_bytes, "lived sequence state")
        _sha256(
            self.authority_receipt_sha256,
            "lived sequence profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("lived sequence profile authority changed")


@dataclass(frozen=True, slots=True)
class W1GroundedLivedEvent:
    event_id: str
    settlement_receipt_sha256: str
    structural_fingerprint: str
    source_time_start: Fraction
    source_time_end: Fraction
    roots: tuple[GroundingRoot, ...]

    def payload(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "roots": [value.as_record() for value in self.roots],
            "schema": LIVED_SEQUENCE_EVENT_SCHEMA,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "structural_fingerprint": self.structural_fingerprint,
        }

    def verify(self, maximum_roots: int) -> None:
        for value, name in (
            (self.event_id, "lived sequence event"),
            (
                self.settlement_receipt_sha256,
                "lived sequence settlement",
            ),
            (
                self.structural_fingerprint,
                "lived sequence structural fingerprint",
            ),
        ):
            _sha256(value, name)
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or not self.roots
            or len(self.roots) > maximum_roots
            or tuple(sorted(self.roots, key=lambda root: root.root_id))
            != self.roots
        ):
            raise ValueError("lived sequence event changed")
        for root in self.roots:
            root.verify()


@dataclass(frozen=True, slots=True)
class W1GroundedLivedSequenceProof:
    proof_id: str
    demonstration_id: str
    challenge_cue_id: str
    response_cue_id: str
    ordered_events: tuple[W1GroundedLivedEvent, ...]
    response_root_identities: tuple[tuple[str, str], ...]
    source_episode_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "challenge_cue_id": self.challenge_cue_id,
            "demonstration_id": self.demonstration_id,
            "ordered_events": [
                value.payload() for value in self.ordered_events
            ],
            "response_cue_id": self.response_cue_id,
            "response_root_identities": [
                list(value) for value in self.response_root_identities
            ],
            "schema": LIVED_SEQUENCE_PROOF_SCHEMA,
            "source_episode_receipt_sha256s": list(
                self.source_episode_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "proof_id": self.proof_id,
        }


class W1GroundedLivedSequenceOwner:
    """Bounded authority for ordered lived-event citation proofs."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1GroundedLivedSequenceProfile,
        demonstration_owner: W1GroundedDemonstrationOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(
            demonstration_owner, W1GroundedDemonstrationOwner
        ):
            raise TypeError(
                "lived sequence requires grounded demonstration authority"
            )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._proof_key = hashlib.sha256(_PROOF_DOMAIN + root).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._demonstrations = demonstration_owner
        self._proofs: dict[str, W1GroundedLivedSequenceProof] = {}
        self._lock = threading.RLock()

    @property
    def proofs(self) -> tuple[W1GroundedLivedSequenceProof, ...]:
        with self._lock:
            return tuple(self._proofs[key] for key in sorted(self._proofs))

    def _owned_demonstration(
        self, demonstration_id: str
    ) -> W1GroundedDemonstration:
        matches = tuple(
            value
            for value in self._demonstrations.demonstrations
            if value.demonstration_id == demonstration_id
        )
        if len(matches) != 1:
            raise ValueError(
                "lived sequence lost its grounded demonstration"
            )
        return matches[0]

    def verify(self, proof: W1GroundedLivedSequenceProof) -> None:
        for value, name in (
            (proof.proof_id, "lived sequence proof"),
            (proof.demonstration_id, "lived sequence demonstration"),
            (proof.challenge_cue_id, "lived sequence challenge cue"),
            (proof.response_cue_id, "lived sequence response cue"),
            (
                proof.authority_hmac_sha256,
                "lived sequence proof HMAC",
            ),
            (
                proof.authority_receipt_sha256,
                "lived sequence proof authority",
            ),
            *(
                (value, "lived sequence physical source")
                for value in proof.source_episode_receipt_sha256s
            ),
        ):
            _sha256(value, name)
        demonstration = self._owned_demonstration(
            proof.demonstration_id
        )
        if (
            demonstration.kind != "cited_lived_sequence_response"
            or demonstration.response_cue is None
            or demonstration.challenge_cue.cue_id
            != proof.challenge_cue_id
            or demonstration.response_cue.cue_id != proof.response_cue_id
            or not 2 <= len(proof.ordered_events)
            <= self._profile.max_events_per_proof
            or proof.source_episode_receipt_sha256s
            != demonstration.source_episode_receipt_sha256s
            or tuple(sorted(set(
                proof.source_episode_receipt_sha256s
            ))) != proof.source_episode_receipt_sha256s
        ):
            raise ValueError("grounded lived sequence proof changed")
        prior_end = None
        for event in proof.ordered_events:
            event.verify(self._profile.max_roots_per_event)
            if (
                prior_end is not None
                and event.source_time_start < prior_end
            ):
                raise ValueError("lived event sequence reordered")
            prior_end = event.source_time_end
        scene_records = tuple(
            (
                value.settlement_receipt_sha256,
                tuple(value.roots),
            )
            for value in demonstration.scenes
        )
        event_records = tuple(
            (
                value.settlement_receipt_sha256,
                value.roots,
            )
            for value in proof.ordered_events
        )
        scene_roots = {
            (root.root_id, root.value_sha256)
            for event in proof.ordered_events
            for root in event.roots
        }
        expected_response_roots = tuple(sorted({
            (value.root.root_id, value.root.value_sha256)
            for value in demonstration.response_cue.elements
        }))
        if (
            scene_records != event_records
            or proof.response_root_identities != expected_response_roots
            or not set(expected_response_roots).issubset(scene_roots)
        ):
            raise ValueError(
                "grounded response left its lived event sequence"
            )
        payload = proof.payload()
        signature = hmac.new(
            self._proof_key,
            _PROOF_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            proof.proof_id != _digest(payload)
            or not hmac.compare_digest(
                proof.authority_hmac_sha256, signature
            )
            or proof.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("lived sequence proof authority changed")

    def admit(
        self,
        *,
        demonstration: W1GroundedDemonstration,
        lived_settlements: tuple[CausalExperienceSettlement, ...],
    ) -> W1GroundedLivedSequenceProof:
        owned = self._owned_demonstration(demonstration.demonstration_id)
        if owned != demonstration:
            raise ValueError(
                "lived sequence demonstration is not authority-owned"
            )
        if (
            demonstration.response_cue is None
            or not isinstance(lived_settlements, tuple)
            or not 2 <= len(lived_settlements)
            <= self._profile.max_events_per_proof
        ):
            raise ValueError("lived sequence admission boundary changed")
        events = []
        for settlement in lived_settlements:
            settlement.verify()
            roots = grounding_roots_from_settlement(settlement)
            if len(roots) > self._profile.max_roots_per_event:
                raise ValueError("lived sequence root capacity exhausted")
            events.append(W1GroundedLivedEvent(
                event_id=settlement.event_id,
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                structural_fingerprint=settlement.structural_fingerprint,
                source_time_start=settlement.source_time_start,
                source_time_end=settlement.source_time_end,
                roots=roots,
            ))
        provisional = W1GroundedLivedSequenceProof(
            proof_id="0" * 64,
            demonstration_id=demonstration.demonstration_id,
            challenge_cue_id=demonstration.challenge_cue.cue_id,
            response_cue_id=demonstration.response_cue.cue_id,
            ordered_events=tuple(events),
            response_root_identities=tuple(sorted({
                (value.root.root_id, value.root.value_sha256)
                for value in demonstration.response_cue.elements
            })),
            source_episode_receipt_sha256s=(
                demonstration.source_episode_receipt_sha256s
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._proof_key,
            _PROOF_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1GroundedLivedSequenceProof(
            proof_id=_digest(payload),
            demonstration_id=provisional.demonstration_id,
            challenge_cue_id=provisional.challenge_cue_id,
            response_cue_id=provisional.response_cue_id,
            ordered_events=provisional.ordered_events,
            response_root_identities=(
                provisional.response_root_identities
            ),
            source_episode_receipt_sha256s=(
                provisional.source_episode_receipt_sha256s
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        with self._lock:
            if result.proof_id in self._proofs:
                return result
            if any(
                set(value.source_episode_receipt_sha256s).intersection(
                    result.source_episode_receipt_sha256s
                )
                for value in self._proofs.values()
            ):
                raise ValueError(
                    "lived sequence proofs reuse a physical source"
                )
            if len(self._proofs) >= self._profile.max_proofs:
                raise RuntimeError("lived sequence proof capacity exhausted")
            staged = dict(self._proofs)
            staged[result.proof_id] = result
            self._encoded(staged)
            self._proofs = staged
        return result

    def _body(
        self, values: dict[str, W1GroundedLivedSequenceProof]
    ) -> dict[str, object]:
        return {
            "proofs": [values[key].record() for key in sorted(values)],
            "resource_profile": self._profile.record(),
            "schema": LIVED_SEQUENCE_STATE_SCHEMA,
        }

    def _encoded(
        self, values: dict[str, W1GroundedLivedSequenceProof]
    ) -> bytes:
        body = self._body(values)
        encoded = _canonical({
            "body": body,
            "schema": LIVED_SEQUENCE_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("lived sequence state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._proofs)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        demonstration_owner: W1GroundedDemonstrationOwner,
    ) -> "W1GroundedLivedSequenceOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("lived sequence state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("lived sequence state is unreadable") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != LIVED_SEQUENCE_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError("lived sequence envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"proofs", "resource_profile", "schema"}
            or body.get("schema") != LIVED_SEQUENCE_STATE_SCHEMA
            or not isinstance(body.get("proofs"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("lived sequence state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_events_per_proof",
            "max_proofs",
            "max_roots_per_event",
            "max_state_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("lived sequence profile record changed")
        profile = W1GroundedLivedSequenceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_proofs=raw_profile.get("max_proofs"),
            max_events_per_proof=raw_profile.get(
                "max_events_per_proof"
            ),
            max_roots_per_event=raw_profile.get(
                "max_roots_per_event"
            ),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            demonstration_owner=demonstration_owner,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError("lived sequence state HMAC changed")
        restored: dict[str, W1GroundedLivedSequenceProof] = {}
        used_sources: set[str] = set()
        for raw in body["proofs"]:
            if not isinstance(raw, Mapping):
                raise ValueError("lived sequence proof record changed")
            events = []
            for event_raw in raw.get("ordered_events", ()):
                if not isinstance(event_raw, Mapping):
                    raise ValueError("lived sequence event record changed")
                roots = tuple(
                    GroundingRoot(
                        root_id=root.get("root_id"),
                        value_sha256=root.get("value_sha256"),
                        value_json=root.get("value_json"),
                    )
                    for root in event_raw.get("roots", ())
                )
                events.append(W1GroundedLivedEvent(
                    event_id=event_raw.get("event_id"),
                    settlement_receipt_sha256=event_raw.get(
                        "settlement_receipt_sha256"
                    ),
                    structural_fingerprint=event_raw.get(
                        "structural_fingerprint"
                    ),
                    source_time_start=_fraction(
                        event_raw.get("source_time_start"),
                        "lived sequence source start",
                    ),
                    source_time_end=_fraction(
                        event_raw.get("source_time_end"),
                        "lived sequence source end",
                    ),
                    roots=roots,
                ))
            proof = W1GroundedLivedSequenceProof(
                proof_id=raw.get("proof_id"),
                demonstration_id=raw.get("demonstration_id"),
                challenge_cue_id=raw.get("challenge_cue_id"),
                response_cue_id=raw.get("response_cue_id"),
                ordered_events=tuple(events),
                response_root_identities=tuple(
                    tuple(value)
                    for value in raw.get(
                        "response_root_identities", ()
                    )
                ),
                source_episode_receipt_sha256s=tuple(
                    raw.get("source_episode_receipt_sha256s", ())
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
                authority_receipt_sha256=raw.get(
                    "authority_receipt_sha256"
                ),
            )
            owner.verify(proof)
            if (
                proof.proof_id in restored
                or used_sources.intersection(
                    proof.source_episode_receipt_sha256s
                )
            ):
                raise ValueError("lived sequence restored sources repeat")
            restored[proof.proof_id] = proof
            used_sources.update(proof.source_episode_receipt_sha256s)
        owner._proofs = restored
        if owner.snapshot_encoded() != encoded:
            raise ValueError("lived sequence state is not canonical")
        return owner

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            return {
                "capacity": self._profile.max_proofs,
                "capacity_exhausted": (
                    len(self._proofs) >= self._profile.max_proofs
                ),
                "count": len(self._proofs),
                "state_bytes": len(self._encoded(self._proofs)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "LIVED_SEQUENCE_ENVELOPE_SCHEMA",
    "LIVED_SEQUENCE_EVENT_SCHEMA",
    "LIVED_SEQUENCE_PROFILE_SCHEMA",
    "LIVED_SEQUENCE_PROOF_SCHEMA",
    "LIVED_SEQUENCE_STATE_SCHEMA",
    "W1GroundedLivedEvent",
    "W1GroundedLivedSequenceOwner",
    "W1GroundedLivedSequenceProfile",
    "W1GroundedLivedSequenceProof",
]
