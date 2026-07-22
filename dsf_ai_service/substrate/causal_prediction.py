"""Bounded deterministic prediction over ordered causal full-field settlements.

Prediction identity is the exact six-sense structural fingerprint already
certified by :mod:`exact_causal_experience`.  Routing chi, capture source,
written-word order, scalar scores, frequencies, and probabilities have no
authority here.  A context with no learned successor is ``unknown``; one exact
successor is ``predicted``; more than one is ``ambiguous``.

An episode explicitly starts with ``start``.  Each ``advance`` first resolves
the prediction issued after the preceding settlement, then learns the exact
ordered transition, and finally issues the prediction that precedes the next
settlement.  Relations retain only their latest exact transition evidence and
latest applicable resolution.  State retains one current context, one pending
prediction, and one latest resolution rather than a lifetime event index.
Unique relations are bounded by deterministic oldest-witnessed replacement.
Every retained authority is HMAC authenticated and every mutation is atomic.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    SETTLEMENT_SCHEMA,
)


WITNESS_SCHEMA = "guala.causal_prediction.witness.v1"
EVIDENCE_SCHEMA = "guala.causal_prediction.transition_evidence.v1"
RELATION_SCHEMA = "guala.causal_prediction.transition_relation.v1"
ATTEMPT_SCHEMA = "guala.causal_prediction.attempt.v1"
RESOLUTION_SCHEMA = "guala.causal_prediction.resolution.v1"
STATE_SCHEMA = "guala.causal_prediction.state.v1"
ENVELOPE_SCHEMA = "guala.causal_prediction.hmac.v1"

EVIDENCE_DOMAIN = b"guala-causal-prediction-evidence-v1\0"
RELATION_DOMAIN = b"guala-causal-prediction-relation-v1\0"
ATTEMPT_DOMAIN = b"guala-causal-prediction-attempt-v1\0"
RESOLUTION_DOMAIN = b"guala-causal-prediction-resolution-v1\0"
STATE_DOMAIN = b"guala-causal-prediction-state-v1\0"

DEFAULT_RELATION_CAPACITY = 64
DEFAULT_EVIDENCE_CAPACITY = 260
DEFAULT_MAX_WITNESS_BYTES = 2 * 1024 * 1024
DEFAULT_ENCODED_STATE_BYTES = 32 * 1024 * 1024


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("causal prediction authority key must be bytes or text")
    if not result:
        raise ValueError("causal prediction authority key is required")
    return result


def _sign(key: bytes, domain: bytes, payload: bytes) -> str:
    return hmac.new(key, domain + payload, hashlib.sha256).hexdigest()


def _signed_receipt(payload: Mapping[str, object], signature: str) -> str:
    sha256_digest(signature, "causal prediction authority HMAC")
    return _digest({"authority_hmac_sha256": signature, "payload": dict(payload)})


def _verify_signed(
    *,
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
    identity: str,
    signature: str,
    name: str,
) -> None:
    encoded = _canonical(payload)
    if receipt_sha256(encoded) != sha256_digest(identity, f"{name} identity"):
        raise ValueError(f"{name} identity changed")
    expected = _sign(key, domain, encoded)
    if not hmac.compare_digest(expected, signature):
        raise ValueError(f"{name} HMAC changed")


def _payload_structure(decoded: Mapping[str, object]) -> str:
    interpretations = decoded.get("interpretations")
    language_events = decoded.get("language_events")
    expected_senses = tuple(item.value for item in SENSE_ORDER)
    if (
        not isinstance(interpretations, list)
        or len(interpretations) != len(expected_senses)
        or any(not isinstance(item, Mapping) for item in interpretations)
        or tuple(item.get("sense") for item in interpretations) != expected_senses
        or not isinstance(language_events, list)
    ):
        raise ValueError("prediction witness lost canonical six-sense structure")
    sense_identity: dict[str, dict[str, object]] = {}
    for sense in interpretations:
        expected_fields = {
            "boundary_receipt_sha256",
            "relation",
            "sense",
            "state",
            "structural_fingerprint",
            "substreams",
            "topology_receipt_sha256",
        }
        if set(sense) != expected_fields or not isinstance(sense.get("substreams"), list):
            raise ValueError("prediction witness sense fields changed")
        compact_substreams = []
        for topology_index, substream in enumerate(sense["substreams"]):
            if not isinstance(substream, Mapping):
                raise ValueError("prediction witness substream fields changed")
            expected_substream_fields = {
                "coordinates",
                "field_tuples",
                "kernel_basin_receipt_sha256",
                "physical_quantity",
                "physical_unit",
                "profile_receipt_sha256",
                "sensor_id",
                "source_evidence_stream_receipt_sha256",
                "source_sample_commitment_sha256",
                "source_sample_count",
                "substream_id",
                "topology_index",
            }
            if (
                set(substream) != expected_substream_fields
                or substream.get("topology_index") != topology_index
                or not isinstance(substream.get("coordinates"), list)
                or not isinstance(substream.get("field_tuples"), list)
            ):
                raise ValueError("prediction witness substream topology changed")
            compact_tuples = []
            for tuple_index, field_tuple in enumerate(substream["field_tuples"]):
                if (
                    not isinstance(field_tuple, Mapping)
                    or set(field_tuple)
                    != {"authority_receipt_sha256", "fields", "tuple_index"}
                    or field_tuple.get("tuple_index") != tuple_index
                    or not isinstance(field_tuple.get("fields"), list)
                    or tuple(
                        item[0]
                        for item in field_tuple["fields"]
                        if isinstance(item, list) and len(item) == 2
                    )
                    != DSF_FIELD_ORDER
                    or len(field_tuple["fields"]) != len(DSF_FIELD_ORDER)
                ):
                    raise ValueError("prediction witness DSF tuple changed")
                compact_fields = []
                for name, value in field_tuple["fields"]:
                    if not isinstance(value, str):
                        raise ValueError("prediction witness DSF field is not exact")
                    try:
                        exact = Fraction(value)
                    except (ValueError, ZeroDivisionError) as error:
                        raise ValueError(
                            "prediction witness DSF field is not exact"
                        ) from error
                    if f"{exact.numerator}/{exact.denominator}" != value:
                        raise ValueError("prediction witness DSF field is not canonical")
                    compact_fields.append([name, value])
                compact_tuples.append({
                    "fields": compact_fields,
                    "tuple_index": tuple_index,
                })
            compact_substreams.append({
                "coordinates": substream["coordinates"],
                "field_tuples": compact_tuples,
                "physical_quantity": substream.get("physical_quantity"),
                "physical_unit": substream.get("physical_unit"),
                "substream_id": substream.get("substream_id"),
                "topology_index": topology_index,
            })
        recomputed = _digest({
            "state": sense.get("state"),
            "substreams": compact_substreams,
        })
        if recomputed != sense.get("structural_fingerprint"):
            raise ValueError("prediction witness explicit DSF field changed")
        sense_identity[sense["sense"]] = {
            "state": sense.get("state"),
            "structural_fingerprint": recomputed,
        }
    language_identity = []
    for item in language_events:
        if not isinstance(item, Mapping):
            raise ValueError("prediction witness language event changed")
        occurrence = item.get("recognition_occurrence")
        selected = (
            occurrence.get("selected_class_authority_receipt_sha256")
            if isinstance(occurrence, Mapping)
            else None
        )
        language_identity.append({
            "form": item.get("form"),
            "recognition_class_authority_receipt_sha256": selected,
            "unicode_scalars": item.get("unicode_scalars"),
        })
    return _digest({
        "interpretations": sense_identity,
        "language_events": language_identity,
    })


@dataclass(frozen=True, slots=True)
class PredictionWitness:
    event_id: str
    settlement_receipt_sha256: str
    structural_fingerprint: str
    settlement_payload_base64: str

    @classmethod
    def from_settlement(
        cls, settlement: CausalExperienceSettlement, *, max_bytes: int
    ) -> "PredictionWitness":
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal prediction requires an exact causal settlement")
        settlement.verify()
        payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "causal prediction settlement",
        )
        if not payload or len(payload) > max_bytes:
            raise RuntimeError("causal prediction witness exceeds its byte boundary")
        witness = cls(
            event_id=settlement.event_id,
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            structural_fingerprint=settlement.structural_fingerprint,
            settlement_payload_base64=base64.b64encode(payload).decode("ascii"),
        )
        witness.verify(max_bytes=max_bytes)
        return witness

    def verify(self, *, max_bytes: int) -> None:
        sha256_digest(self.event_id, "prediction event")
        sha256_digest(self.settlement_receipt_sha256, "prediction settlement")
        sha256_digest(self.structural_fingerprint, "prediction structure")
        try:
            payload = base64.b64decode(self.settlement_payload_base64, validate=True)
        except Exception as error:
            raise ValueError("prediction witness is not canonical base64") from error
        if (
            not payload
            or len(payload) > max_bytes
            or receipt_sha256(payload) != self.settlement_receipt_sha256
            or base64.b64encode(payload).decode("ascii")
            != self.settlement_payload_base64
        ):
            raise ValueError("prediction witness receipt changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("prediction witness payload is invalid") from error
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or decoded.get("schema") != SETTLEMENT_SCHEMA
            or decoded.get("event_id") != self.event_id
            or decoded.get("structural_fingerprint") != self.structural_fingerprint
            or _payload_structure(decoded) != self.structural_fingerprint
        ):
            raise ValueError("prediction witness structural identity changed")

    def as_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "schema": WITNESS_SCHEMA,
            "settlement_payload_base64": self.settlement_payload_base64,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "structural_fingerprint": self.structural_fingerprint,
        }


def _witness_from(value: object, *, max_bytes: int) -> PredictionWitness:
    expected = {
        "event_id",
        "schema",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != WITNESS_SCHEMA
    ):
        raise ValueError("prediction witness fields changed")
    witness = PredictionWitness(
        event_id=value.get("event_id"),
        settlement_receipt_sha256=value.get("settlement_receipt_sha256"),
        structural_fingerprint=value.get("structural_fingerprint"),
        settlement_payload_base64=value.get("settlement_payload_base64"),
    )
    witness.verify(max_bytes=max_bytes)
    return witness


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    from_settlement_receipt_sha256: str
    from_structural_fingerprint: str
    to_settlement_receipt_sha256: str
    to_structural_fingerprint: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "from_settlement_receipt_sha256": self.from_settlement_receipt_sha256,
            "from_structural_fingerprint": self.from_structural_fingerprint,
            "schema": EVIDENCE_SCHEMA,
            "to_settlement_receipt_sha256": self.to_settlement_receipt_sha256,
            "to_structural_fingerprint": self.to_structural_fingerprint,
        }

    @property
    def evidence_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.from_settlement_receipt_sha256, "transition source settlement"),
            (self.from_structural_fingerprint, "transition source structure"),
            (self.to_settlement_receipt_sha256, "transition target settlement"),
            (self.to_structural_fingerprint, "transition target structure"),
        ):
            sha256_digest(value, name)
        _verify_signed(
            key=key,
            domain=EVIDENCE_DOMAIN,
            payload=self.payload(),
            identity=self.evidence_id,
            signature=self.authority_hmac_sha256,
            name="transition evidence",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _evidence_from(value: object, *, key: bytes) -> TransitionEvidence:
    expected = {
        "authority_hmac_sha256",
        "from_settlement_receipt_sha256",
        "from_structural_fingerprint",
        "schema",
        "to_settlement_receipt_sha256",
        "to_structural_fingerprint",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != EVIDENCE_SCHEMA
    ):
        raise ValueError("transition evidence fields changed")
    evidence = TransitionEvidence(
        from_settlement_receipt_sha256=value.get(
            "from_settlement_receipt_sha256"
        ),
        from_structural_fingerprint=value.get("from_structural_fingerprint"),
        to_settlement_receipt_sha256=value.get("to_settlement_receipt_sha256"),
        to_structural_fingerprint=value.get("to_structural_fingerprint"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    evidence.verify(key)
    return evidence


@dataclass(frozen=True, slots=True, order=True)
class PredictionCandidate:
    target_structural_fingerprint: str
    relation_id: str

    def verify(self) -> None:
        sha256_digest(self.target_structural_fingerprint, "prediction candidate target")
        sha256_digest(self.relation_id, "prediction candidate relation")

    def as_record(self) -> dict[str, object]:
        return {
            "relation_id": self.relation_id,
            "target_structural_fingerprint": self.target_structural_fingerprint,
        }


def _candidate_from(value: object) -> PredictionCandidate:
    expected = {"relation_id", "target_structural_fingerprint"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("prediction candidate fields changed")
    candidate = PredictionCandidate(
        target_structural_fingerprint=value.get("target_structural_fingerprint"),
        relation_id=value.get("relation_id"),
    )
    candidate.verify()
    return candidate


@dataclass(frozen=True, slots=True)
class PredictionAttempt:
    context_settlement_receipt_sha256: str
    context_structural_fingerprint: str
    status: str
    candidates: tuple[PredictionCandidate, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidates": [item.as_record() for item in self.candidates],
            "context_settlement_receipt_sha256": (
                self.context_settlement_receipt_sha256
            ),
            "context_structural_fingerprint": self.context_structural_fingerprint,
            "schema": ATTEMPT_SCHEMA,
            "status": self.status,
        }

    @property
    def attempt_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        sha256_digest(self.context_settlement_receipt_sha256, "prediction context")
        sha256_digest(self.context_structural_fingerprint, "prediction context structure")
        if (
            not isinstance(self.candidates, tuple)
            or self.candidates != tuple(sorted(self.candidates))
            or len(set(self.candidates)) != len(self.candidates)
        ):
            raise ValueError("prediction candidates are not exact and canonical")
        for candidate in self.candidates:
            candidate.verify()
        expected_status = (
            "unknown"
            if len(self.candidates) == 0
            else "predicted"
            if len(self.candidates) == 1
            else "ambiguous"
        )
        if self.status != expected_status:
            raise ValueError("prediction status differs from exact relations")
        _verify_signed(
            key=key,
            domain=ATTEMPT_DOMAIN,
            payload=self.payload(),
            identity=self.attempt_id,
            signature=self.authority_hmac_sha256,
            name="prediction attempt",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _attempt_from(value: object, *, key: bytes) -> PredictionAttempt:
    expected = {
        "authority_hmac_sha256",
        "candidates",
        "context_settlement_receipt_sha256",
        "context_structural_fingerprint",
        "schema",
        "status",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != ATTEMPT_SCHEMA
        or not isinstance(value.get("candidates"), list)
    ):
        raise ValueError("prediction attempt fields changed")
    attempt = PredictionAttempt(
        context_settlement_receipt_sha256=value.get(
            "context_settlement_receipt_sha256"
        ),
        context_structural_fingerprint=value.get(
            "context_structural_fingerprint"
        ),
        status=value.get("status"),
        candidates=tuple(_candidate_from(item) for item in value["candidates"]),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    attempt.verify(key)
    return attempt


@dataclass(frozen=True, slots=True)
class PredictionResolution:
    attempt_receipt_sha256: str
    attempt_authority_hmac_sha256: str
    context_settlement_receipt_sha256: str
    context_structural_fingerprint: str
    prediction_status: str
    candidates: tuple[PredictionCandidate, ...]
    actual_settlement_receipt_sha256: str
    actual_structural_fingerprint: str
    verification: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "actual_settlement_receipt_sha256": (
                self.actual_settlement_receipt_sha256
            ),
            "actual_structural_fingerprint": self.actual_structural_fingerprint,
            "attempt_authority_hmac_sha256": self.attempt_authority_hmac_sha256,
            "attempt_receipt_sha256": self.attempt_receipt_sha256,
            "candidates": [item.as_record() for item in self.candidates],
            "context_settlement_receipt_sha256": (
                self.context_settlement_receipt_sha256
            ),
            "context_structural_fingerprint": self.context_structural_fingerprint,
            "prediction_status": self.prediction_status,
            "schema": RESOLUTION_SCHEMA,
            "verification": self.verification,
        }

    @property
    def resolution_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.attempt_receipt_sha256, "resolved prediction attempt"),
            (self.context_settlement_receipt_sha256, "resolved context"),
            (self.context_structural_fingerprint, "resolved context structure"),
            (self.actual_settlement_receipt_sha256, "resolved actual settlement"),
            (self.actual_structural_fingerprint, "resolved actual structure"),
        ):
            sha256_digest(value, name)
        if (
            not isinstance(self.candidates, tuple)
            or self.candidates != tuple(sorted(self.candidates))
            or len(set(self.candidates)) != len(self.candidates)
        ):
            raise ValueError("resolved prediction candidates changed")
        targets = tuple(item.target_structural_fingerprint for item in self.candidates)
        if self.prediction_status == "unknown" and not targets:
            expected = "unknown_observed"
        elif self.prediction_status == "predicted" and len(targets) == 1:
            expected = (
                "predicted_match"
                if self.actual_structural_fingerprint == targets[0]
                else "predicted_mismatch"
            )
        elif self.prediction_status == "ambiguous" and len(targets) > 1:
            expected = (
                "ambiguous_candidate_observed"
                if self.actual_structural_fingerprint in targets
                else "ambiguous_novel_observed"
            )
        else:
            raise ValueError("resolved prediction status changed")
        if self.verification != expected:
            raise ValueError("prediction verification differs from exact outcome")
        for candidate in self.candidates:
            candidate.verify()
        attempt = PredictionAttempt(
            context_settlement_receipt_sha256=(
                self.context_settlement_receipt_sha256
            ),
            context_structural_fingerprint=self.context_structural_fingerprint,
            status=self.prediction_status,
            candidates=self.candidates,
            authority_hmac_sha256=self.attempt_authority_hmac_sha256,
        )
        attempt.verify(key)
        if attempt.authority_receipt_sha256 != self.attempt_receipt_sha256:
            raise ValueError("prediction resolution names a different attempt")
        _verify_signed(
            key=key,
            domain=RESOLUTION_DOMAIN,
            payload=self.payload(),
            identity=self.resolution_id,
            signature=self.authority_hmac_sha256,
            name="prediction resolution",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _resolution_from(value: object, *, key: bytes) -> PredictionResolution:
    expected = {
        "actual_settlement_receipt_sha256",
        "actual_structural_fingerprint",
        "attempt_authority_hmac_sha256",
        "attempt_receipt_sha256",
        "authority_hmac_sha256",
        "candidates",
        "context_settlement_receipt_sha256",
        "context_structural_fingerprint",
        "prediction_status",
        "schema",
        "verification",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != RESOLUTION_SCHEMA
        or not isinstance(value.get("candidates"), list)
    ):
        raise ValueError("prediction resolution fields changed")
    resolution = PredictionResolution(
        attempt_receipt_sha256=value.get("attempt_receipt_sha256"),
        attempt_authority_hmac_sha256=value.get(
            "attempt_authority_hmac_sha256"
        ),
        context_settlement_receipt_sha256=value.get(
            "context_settlement_receipt_sha256"
        ),
        context_structural_fingerprint=value.get(
            "context_structural_fingerprint"
        ),
        prediction_status=value.get("prediction_status"),
        candidates=tuple(_candidate_from(item) for item in value["candidates"]),
        actual_settlement_receipt_sha256=value.get(
            "actual_settlement_receipt_sha256"
        ),
        actual_structural_fingerprint=value.get("actual_structural_fingerprint"),
        verification=value.get("verification"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    resolution.verify(key)
    return resolution


@dataclass(frozen=True, slots=True)
class TransitionRelation:
    relation_id: str
    from_structural_fingerprint: str
    to_structural_fingerprint: str
    latest_evidence: TransitionEvidence
    latest_resolution: PredictionResolution | None
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "from_structural_fingerprint": self.from_structural_fingerprint,
            "latest_evidence": self.latest_evidence.as_record(),
            "latest_resolution": (
                self.latest_resolution.as_record()
                if self.latest_resolution is not None
                else None
            ),
            "relation_id": self.relation_id,
            "schema": RELATION_SCHEMA,
            "to_structural_fingerprint": self.to_structural_fingerprint,
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        expected_id = _digest({
            "from_structural_fingerprint": self.from_structural_fingerprint,
            "schema": "guala.causal_prediction.exact_relation.v1",
            "to_structural_fingerprint": self.to_structural_fingerprint,
        })
        self.latest_evidence.verify(key)
        if (
            self.relation_id != expected_id
            or self.latest_evidence.from_structural_fingerprint
            != self.from_structural_fingerprint
            or self.latest_evidence.to_structural_fingerprint
            != self.to_structural_fingerprint
        ):
            raise ValueError("transition relation identity changed")
        if self.latest_resolution is not None:
            self.latest_resolution.verify(key)
            matching = tuple(
                item
                for item in self.latest_resolution.candidates
                if item.relation_id == self.relation_id
            )
            if (
                len(matching) != 1
                or matching[0].target_structural_fingerprint
                != self.to_structural_fingerprint
                or self.latest_resolution.context_structural_fingerprint
                != self.from_structural_fingerprint
            ):
                raise ValueError("relation resolution does not name the relation")
        encoded = _canonical(self.payload())
        expected = _sign(key, RELATION_DOMAIN, encoded)
        sha256_digest(self.authority_hmac_sha256, "transition relation HMAC")
        if not hmac.compare_digest(expected, self.authority_hmac_sha256):
            raise ValueError("transition relation HMAC changed")

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _relation_from(value: object, *, key: bytes) -> TransitionRelation:
    expected = {
        "authority_hmac_sha256",
        "from_structural_fingerprint",
        "latest_evidence",
        "latest_resolution",
        "relation_id",
        "schema",
        "to_structural_fingerprint",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != RELATION_SCHEMA
    ):
        raise ValueError("transition relation fields changed")
    raw_resolution = value.get("latest_resolution")
    relation = TransitionRelation(
        relation_id=value.get("relation_id"),
        from_structural_fingerprint=value.get("from_structural_fingerprint"),
        to_structural_fingerprint=value.get("to_structural_fingerprint"),
        latest_evidence=_evidence_from(value.get("latest_evidence"), key=key),
        latest_resolution=(
            _resolution_from(raw_resolution, key=key)
            if raw_resolution is not None
            else None
        ),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    relation.verify(key)
    return relation


@dataclass(frozen=True, slots=True)
class PredictionStep:
    resolution: PredictionResolution
    transition: TransitionEvidence
    next_prediction: PredictionAttempt
    evicted_relation_id: str | None


class CausalPredictionAuthority:
    """Serial authority for bounded exact full-field temporal prediction."""

    def __init__(
        self,
        *,
        authority_key: object,
        log_event: Callable[..., None] | None = None,
        relation_capacity: int = DEFAULT_RELATION_CAPACITY,
        evidence_capacity: int = DEFAULT_EVIDENCE_CAPACITY,
        max_witness_bytes: int = DEFAULT_MAX_WITNESS_BYTES,
        encoded_state_capacity: int = DEFAULT_ENCODED_STATE_BYTES,
    ) -> None:
        capacities = (
            relation_capacity,
            evidence_capacity,
            max_witness_bytes,
            encoded_state_capacity,
        )
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in capacities
        ):
            raise ValueError("causal prediction capacities must be positive integers")
        if evidence_capacity < (4 * relation_capacity) + 4:
            raise ValueError(
                "prediction evidence capacity must cover bounded relation evidence"
            )
        self._key = _key(authority_key)
        self._log = log_event or (lambda *_args, **_kwargs: None)
        self._relation_capacity = relation_capacity
        self._evidence_capacity = evidence_capacity
        self._max_witness_bytes = max_witness_bytes
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._relations: OrderedDict[str, TransitionRelation] = OrderedDict()
        self._evidence: dict[str, PredictionWitness] = {}
        self._current_receipt: str | None = None
        self._pending: PredictionAttempt | None = None
        self._latest_resolution: PredictionResolution | None = None

    def _capacities(self) -> dict[str, int]:
        return {
            "encoded_state_capacity": self._encoded_state_capacity,
            "evidence_capacity": self._evidence_capacity,
            "max_witness_bytes": self._max_witness_bytes,
            "relation_capacity": self._relation_capacity,
        }

    def _state(self) -> dict[str, object]:
        return {
            "capacities": self._capacities(),
            "current_receipt": self._current_receipt,
            "evidence": [
                self._evidence[key].as_record() for key in sorted(self._evidence)
            ],
            "latest_resolution": (
                self._latest_resolution.as_record()
                if self._latest_resolution is not None
                else None
            ),
            "pending": self._pending.as_record() if self._pending is not None else None,
            "relations": [item.as_record() for item in self._relations.values()],
            "schema": STATE_SCHEMA,
        }

    def _encoded_payload_locked(self) -> bytes:
        payload = _canonical(self._state())
        envelope = _canonical({
            "authority_hmac_sha256": _sign(self._key, STATE_DOMAIN, payload),
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        })
        if len(envelope) > self._encoded_state_capacity:
            raise RuntimeError("causal prediction encoded state capacity is full")
        return envelope

    @contextmanager
    def _atomic(self):
        prior = (
            OrderedDict(self._relations),
            dict(self._evidence),
            self._current_receipt,
            self._pending,
            self._latest_resolution,
        )
        try:
            yield
            self._encoded_payload_locked()
        except BaseException:
            (
                self._relations,
                self._evidence,
                self._current_receipt,
                self._pending,
                self._latest_resolution,
            ) = prior
            raise

    def _retain_locked(self, witness: PredictionWitness) -> None:
        existing = self._evidence.get(witness.settlement_receipt_sha256)
        if existing is not None and existing != witness:
            raise ValueError("prediction evidence receipt was offered differently")
        self._evidence[witness.settlement_receipt_sha256] = witness

    def _required_evidence_locked(self) -> set[str]:
        required: set[str] = set()
        if self._current_receipt is not None:
            required.add(self._current_receipt)
        for relation in self._relations.values():
            evidence = relation.latest_evidence
            required.update((
                evidence.from_settlement_receipt_sha256,
                evidence.to_settlement_receipt_sha256,
            ))
            if relation.latest_resolution is not None:
                resolution = relation.latest_resolution
                required.update((
                    resolution.context_settlement_receipt_sha256,
                    resolution.actual_settlement_receipt_sha256,
                ))
        if self._latest_resolution is not None:
            required.update((
                self._latest_resolution.context_settlement_receipt_sha256,
                self._latest_resolution.actual_settlement_receipt_sha256,
            ))
        return required

    def _gc_evidence_locked(self) -> None:
        required = self._required_evidence_locked()
        self._evidence = {
            key: value for key, value in self._evidence.items() if key in required
        }
        if len(self._evidence) > self._evidence_capacity:
            raise RuntimeError("causal prediction evidence capacity is full")
        if set(self._evidence) != required:
            raise ValueError("causal prediction state lost exact settlement evidence")

    def _relation_candidates_locked(self, structure: str) -> tuple[PredictionCandidate, ...]:
        return tuple(sorted(
            PredictionCandidate(
                target_structural_fingerprint=item.to_structural_fingerprint,
                relation_id=item.relation_id,
            )
            for item in self._relations.values()
            if item.from_structural_fingerprint == structure
        ))

    def _issue_locked(self, witness: PredictionWitness) -> PredictionAttempt:
        candidates = self._relation_candidates_locked(witness.structural_fingerprint)
        status = (
            "unknown" if not candidates else "predicted" if len(candidates) == 1 else "ambiguous"
        )
        unsigned = {
            "candidates": [item.as_record() for item in candidates],
            "context_settlement_receipt_sha256": witness.settlement_receipt_sha256,
            "context_structural_fingerprint": witness.structural_fingerprint,
            "schema": ATTEMPT_SCHEMA,
            "status": status,
        }
        attempt = PredictionAttempt(
            context_settlement_receipt_sha256=witness.settlement_receipt_sha256,
            context_structural_fingerprint=witness.structural_fingerprint,
            status=status,
            candidates=candidates,
            authority_hmac_sha256=_sign(self._key, ATTEMPT_DOMAIN, _canonical(unsigned)),
        )
        attempt.verify(self._key)
        return attempt

    def _resolve_locked(
        self, attempt: PredictionAttempt, actual: PredictionWitness
    ) -> PredictionResolution:
        targets = tuple(
            item.target_structural_fingerprint for item in attempt.candidates
        )
        if attempt.status == "unknown":
            verification = "unknown_observed"
        elif attempt.status == "predicted":
            verification = (
                "predicted_match"
                if actual.structural_fingerprint == targets[0]
                else "predicted_mismatch"
            )
        else:
            verification = (
                "ambiguous_candidate_observed"
                if actual.structural_fingerprint in targets
                else "ambiguous_novel_observed"
            )
        unsigned = {
            "actual_settlement_receipt_sha256": actual.settlement_receipt_sha256,
            "actual_structural_fingerprint": actual.structural_fingerprint,
            "attempt_authority_hmac_sha256": attempt.authority_hmac_sha256,
            "attempt_receipt_sha256": attempt.authority_receipt_sha256,
            "candidates": [item.as_record() for item in attempt.candidates],
            "context_settlement_receipt_sha256": (
                attempt.context_settlement_receipt_sha256
            ),
            "context_structural_fingerprint": attempt.context_structural_fingerprint,
            "prediction_status": attempt.status,
            "schema": RESOLUTION_SCHEMA,
            "verification": verification,
        }
        resolution = PredictionResolution(
            attempt_receipt_sha256=attempt.authority_receipt_sha256,
            attempt_authority_hmac_sha256=attempt.authority_hmac_sha256,
            context_settlement_receipt_sha256=(
                attempt.context_settlement_receipt_sha256
            ),
            context_structural_fingerprint=attempt.context_structural_fingerprint,
            prediction_status=attempt.status,
            candidates=attempt.candidates,
            actual_settlement_receipt_sha256=actual.settlement_receipt_sha256,
            actual_structural_fingerprint=actual.structural_fingerprint,
            verification=verification,
            authority_hmac_sha256=_sign(
                self._key, RESOLUTION_DOMAIN, _canonical(unsigned)
            ),
        )
        resolution.verify(self._key)
        return resolution

    def _evidence_locked(
        self, before: PredictionWitness, after: PredictionWitness
    ) -> TransitionEvidence:
        unsigned = {
            "from_settlement_receipt_sha256": before.settlement_receipt_sha256,
            "from_structural_fingerprint": before.structural_fingerprint,
            "schema": EVIDENCE_SCHEMA,
            "to_settlement_receipt_sha256": after.settlement_receipt_sha256,
            "to_structural_fingerprint": after.structural_fingerprint,
        }
        evidence = TransitionEvidence(
            from_settlement_receipt_sha256=before.settlement_receipt_sha256,
            from_structural_fingerprint=before.structural_fingerprint,
            to_settlement_receipt_sha256=after.settlement_receipt_sha256,
            to_structural_fingerprint=after.structural_fingerprint,
            authority_hmac_sha256=_sign(
                self._key, EVIDENCE_DOMAIN, _canonical(unsigned)
            ),
        )
        evidence.verify(self._key)
        return evidence

    def _relation_with(
        self,
        evidence: TransitionEvidence,
        resolution: PredictionResolution | None,
    ) -> TransitionRelation:
        relation_id = _digest({
            "from_structural_fingerprint": evidence.from_structural_fingerprint,
            "schema": "guala.causal_prediction.exact_relation.v1",
            "to_structural_fingerprint": evidence.to_structural_fingerprint,
        })
        unsigned = {
            "from_structural_fingerprint": evidence.from_structural_fingerprint,
            "latest_evidence": evidence.as_record(),
            "latest_resolution": (
                resolution.as_record() if resolution is not None else None
            ),
            "relation_id": relation_id,
            "schema": RELATION_SCHEMA,
            "to_structural_fingerprint": evidence.to_structural_fingerprint,
        }
        relation = TransitionRelation(
            relation_id=relation_id,
            from_structural_fingerprint=evidence.from_structural_fingerprint,
            to_structural_fingerprint=evidence.to_structural_fingerprint,
            latest_evidence=evidence,
            latest_resolution=resolution,
            authority_hmac_sha256=_sign(
                self._key, RELATION_DOMAIN, _canonical(unsigned)
            ),
        )
        relation.verify(self._key)
        return relation

    def _attach_resolution_locked(self, resolution: PredictionResolution) -> None:
        if resolution.prediction_status != "predicted":
            return
        for candidate in resolution.candidates:
            relation = self._relations.get(candidate.relation_id)
            if relation is None:
                raise ValueError("pending prediction relation disappeared")
            updated = self._relation_with(
                relation.latest_evidence,
                resolution,
            )
            self._relations[candidate.relation_id] = updated

    def start(self, settlement: CausalExperienceSettlement) -> PredictionAttempt:
        """Start one episode and issue a prediction before its next settlement."""
        witness = PredictionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        with self._lock:
            if self._current_receipt is not None or self._pending is not None:
                raise ValueError("causal prediction episode is already active")
            with self._atomic():
                self._current_receipt = witness.settlement_receipt_sha256
                self._retain_locked(witness)
                self._pending = self._issue_locked(witness)
                self._gc_evidence_locked()
                attempt = self._pending
        self._log(
            "causal_prediction_started",
            event_id=witness.event_id,
            prediction_status=attempt.status,
        )
        return attempt

    def advance(self, settlement: CausalExperienceSettlement) -> PredictionStep:
        """Resolve the pending prediction, learn the transition, and predict again."""
        actual = PredictionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        with self._lock:
            if self._current_receipt is None or self._pending is None:
                raise ValueError("causal prediction episode has not started")
            before = self._evidence.get(self._current_receipt)
            if before is None:
                raise ValueError("causal prediction current evidence is missing")
            if actual.settlement_receipt_sha256 == before.settlement_receipt_sha256:
                raise ValueError("causal prediction cannot advance the same settlement")
            with self._atomic():
                self._retain_locked(actual)
                resolution = self._resolve_locked(self._pending, actual)
                self._attach_resolution_locked(resolution)
                evidence = self._evidence_locked(before, actual)
                relation = self._relation_with(
                    evidence,
                    resolution
                    if resolution.prediction_status == "predicted" and any(
                        item.relation_id
                        == _digest({
                            "from_structural_fingerprint": evidence.from_structural_fingerprint,
                            "schema": "guala.causal_prediction.exact_relation.v1",
                            "to_structural_fingerprint": evidence.to_structural_fingerprint,
                        })
                        for item in resolution.candidates
                    )
                    else None,
                )
                evicted = None
                if relation.relation_id not in self._relations:
                    if len(self._relations) >= self._relation_capacity:
                        evicted, _old = self._relations.popitem(last=False)
                    self._relations[relation.relation_id] = relation
                else:
                    existing = self._relations[relation.relation_id]
                    if relation.latest_resolution is None:
                        relation = self._relation_with(
                            evidence, existing.latest_resolution
                        )
                    self._relations[relation.relation_id] = relation
                    self._relations.move_to_end(relation.relation_id)
                self._latest_resolution = resolution
                self._current_receipt = actual.settlement_receipt_sha256
                self._pending = self._issue_locked(actual)
                self._gc_evidence_locked()
                step = PredictionStep(
                    resolution=resolution,
                    transition=evidence,
                    next_prediction=self._pending,
                    evicted_relation_id=evicted,
                )
        self._log(
            "causal_prediction_advanced",
            event_id=actual.event_id,
            verification=step.resolution.verification,
            next_prediction_status=step.next_prediction.status,
            evicted_relation_id=step.evicted_relation_id,
        )
        return step

    def stop(self) -> None:
        """End the episode so unrelated sessions cannot become a transition."""
        with self._lock:
            with self._atomic():
                self._current_receipt = None
                self._pending = None
                self._gc_evidence_locked()
        self._log("causal_prediction_stopped")

    def current_prediction(self) -> PredictionAttempt | None:
        with self._lock:
            return self._pending

    def latest_resolution(self) -> PredictionResolution | None:
        with self._lock:
            return self._latest_resolution

    def relation_records(self) -> tuple[dict[str, object], ...]:
        with self._lock:
            return tuple(
                json.loads(_canonical(item.as_record()).decode("utf-8"))
                for item in self._relations.values()
            )

    def status(self) -> dict[str, object]:
        with self._lock:
            by_context: dict[str, int] = {}
            for relation in self._relations.values():
                by_context[relation.from_structural_fingerprint] = (
                    by_context.get(relation.from_structural_fingerprint, 0) + 1
                )
            ambiguous_contexts = sum(
                1 for value in by_context.values() if value > 1
            )
            return {
                "active_episode": self._current_receipt is not None,
                "ambiguous_contexts": ambiguous_contexts,
                "evidence": len(self._evidence),
                "latest_verification": (
                    self._latest_resolution.verification
                    if self._latest_resolution is not None
                    else None
                ),
                "pending_status": (
                    self._pending.status if self._pending is not None else None
                ),
                "relations": len(self._relations),
            }

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_payload_locked()

    def restore_encoded(self, encoded: bytes) -> None:
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("causal prediction snapshot must be nonempty bytes")
        if len(encoded) > self._encoded_state_capacity:
            raise ValueError("causal prediction snapshot exceeds its byte boundary")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("causal prediction snapshot is invalid JSON") from error
        expected_envelope = {
            "authority_hmac_sha256",
            "payload_base64",
            "schema",
        }
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected_envelope
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("causal prediction snapshot envelope changed")
        try:
            payload = base64.b64decode(envelope["payload_base64"], validate=True)
        except Exception as error:
            raise ValueError("causal prediction payload is not canonical base64") from error
        if base64.b64encode(payload).decode("ascii") != envelope["payload_base64"]:
            raise ValueError("causal prediction payload base64 changed")
        expected_hmac = _sign(self._key, STATE_DOMAIN, payload)
        signature = envelope.get("authority_hmac_sha256")
        sha256_digest(signature, "causal prediction state HMAC")
        if not hmac.compare_digest(expected_hmac, signature):
            raise ValueError("causal prediction state HMAC changed")
        try:
            state = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("causal prediction state payload is invalid") from error
        expected_state = {
            "capacities",
            "current_receipt",
            "evidence",
            "latest_resolution",
            "pending",
            "relations",
            "schema",
        }
        if (
            not isinstance(state, Mapping)
            or set(state) != expected_state
            or state.get("schema") != STATE_SCHEMA
            or _canonical(state) != payload
            or state.get("capacities") != self._capacities()
            or not isinstance(state.get("evidence"), list)
            or not isinstance(state.get("relations"), list)
        ):
            raise ValueError("causal prediction state contract changed")
        evidence_values = [
            _witness_from(item, max_bytes=self._max_witness_bytes)
            for item in state["evidence"]
        ]
        evidence = {
            item.settlement_receipt_sha256: item for item in evidence_values
        }
        if len(evidence) != len(evidence_values):
            raise ValueError("causal prediction state repeats evidence")
        relation_values = [
            _relation_from(item, key=self._key) for item in state["relations"]
        ]
        relations = OrderedDict((item.relation_id, item) for item in relation_values)
        if len(relations) != len(relation_values):
            raise ValueError("causal prediction state repeats relations")
        pending = (
            _attempt_from(state["pending"], key=self._key)
            if state.get("pending") is not None
            else None
        )
        latest = (
            _resolution_from(state["latest_resolution"], key=self._key)
            if state.get("latest_resolution") is not None
            else None
        )
        current = state.get("current_receipt")
        if (
            (current is None) != (pending is None)
            or (current is not None and current not in evidence)
            or len(relations) > self._relation_capacity
            or len(evidence) > self._evidence_capacity
        ):
            raise ValueError("causal prediction live state is inconsistent")
        if pending is not None and pending.context_settlement_receipt_sha256 != current:
            raise ValueError("causal prediction pending context changed")
        for relation in relations.values():
            source_witness = evidence.get(
                relation.latest_evidence.from_settlement_receipt_sha256
            )
            target_witness = evidence.get(
                relation.latest_evidence.to_settlement_receipt_sha256
            )
            required = {
                relation.latest_evidence.from_settlement_receipt_sha256,
                relation.latest_evidence.to_settlement_receipt_sha256,
            }
            if relation.latest_resolution is not None:
                required.update((
                    relation.latest_resolution.context_settlement_receipt_sha256,
                    relation.latest_resolution.actual_settlement_receipt_sha256,
                ))
            if not required.issubset(evidence):
                raise ValueError("transition relation lost settlement evidence")
            if (
                source_witness is None
                or target_witness is None
                or source_witness.structural_fingerprint
                != relation.from_structural_fingerprint
                or target_witness.structural_fingerprint
                != relation.to_structural_fingerprint
            ):
                raise ValueError("transition relation differs from full-field evidence")
            if relation.latest_resolution is not None:
                resolution = relation.latest_resolution
                if (
                    evidence[resolution.context_settlement_receipt_sha256]
                    .structural_fingerprint
                    != resolution.context_structural_fingerprint
                    or evidence[resolution.actual_settlement_receipt_sha256]
                    .structural_fingerprint
                    != resolution.actual_structural_fingerprint
                ):
                    raise ValueError(
                        "relation resolution differs from full-field evidence"
                    )
        if latest is not None and not {
            latest.context_settlement_receipt_sha256,
            latest.actual_settlement_receipt_sha256,
        }.issubset(evidence):
            raise ValueError("latest prediction resolution lost evidence")
        if latest is not None and (
            evidence[latest.context_settlement_receipt_sha256].structural_fingerprint
            != latest.context_structural_fingerprint
            or evidence[latest.actual_settlement_receipt_sha256].structural_fingerprint
            != latest.actual_structural_fingerprint
        ):
            raise ValueError("latest prediction resolution differs from evidence")
        with self._lock:
            prior = (
                OrderedDict(self._relations),
                dict(self._evidence),
                self._current_receipt,
                self._pending,
                self._latest_resolution,
            )
            try:
                self._relations = relations
                self._evidence = evidence
                self._current_receipt = current
                self._pending = pending
                self._latest_resolution = latest
                self._gc_evidence_locked()
                if self._pending is not None:
                    current_witness = self._evidence[self._current_receipt]
                    expected_candidates = self._relation_candidates_locked(
                        current_witness.structural_fingerprint
                    )
                    if (
                        self._pending.context_structural_fingerprint
                        != current_witness.structural_fingerprint
                        or self._pending.candidates != expected_candidates
                    ):
                        raise ValueError(
                            "pending prediction differs from exact transition relations"
                        )
                if self._encoded_payload_locked() != encoded:
                    raise ValueError("causal prediction snapshot is not canonical state")
            except BaseException:
                (
                    self._relations,
                    self._evidence,
                    self._current_receipt,
                    self._pending,
                    self._latest_resolution,
                ) = prior
                raise


__all__ = [
    "CausalPredictionAuthority",
    "PredictionAttempt",
    "PredictionCandidate",
    "PredictionResolution",
    "PredictionStep",
    "PredictionWitness",
    "TransitionEvidence",
    "TransitionRelation",
]
