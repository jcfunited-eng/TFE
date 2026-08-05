"""Bounded experience-grown causal associations for heard Krimelack kinds.

An auditory kind is not meaning.  This owner admits a heard occurrence to
deliberation only after two distinct, exact causal occurrences establish the
same kind/full-field association.  Replaying one receipt cannot reinforce it.
One conflicting full-field association makes the kind ambiguous and therefore
stops admission; no frequency vote, score, salience, decay, or tie breaker is
used.

Every retained occurrence carries the complete compact auditory DSF authority
and complete six-sense causal witnesses defined by
``auditory_krimelack_causal_occurrence``.  Chi, tutor labels, transcripts, and
actions are absent from association identity.  Persistence is fixed-capacity,
canonical, and HMAC authenticated.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES,
    AuditoryKrimelackCausalOccurrence,
)
from dsf_ai_service.substrate.causal_deliberation import (
    DeliberationWitness,
)


AUDITORY_KRIMELACK_ASSOCIATION_VARIANT_SCHEMA = (
    "guala.auditory.krimelack_association_variant.v1"
)
AUDITORY_KRIMELACK_KIND_ASSOCIATION_SCHEMA = (
    "guala.auditory.krimelack_kind_association.v1"
)
AUDITORY_KRIMELACK_ASSOCIATION_STATE_SCHEMA = (
    "guala.auditory.krimelack_association_state.v1"
)
AUDITORY_KRIMELACK_ASSOCIATION_ENVELOPE_SCHEMA = (
    "guala.auditory.krimelack_association_hmac.v1"
)
AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA = (
    "guala.auditory.krimelack_deliberation_admission.v1"
)
AUDITORY_KRIMELACK_DELIBERATION_DECISION_SCHEMA = (
    "guala.auditory.krimelack_deliberation_decision.v1"
)

MAX_AUDITORY_KRIMELACK_CAUSAL_ASSOCIATIONS = 64
MAX_ASSOCIATION_VARIANTS_PER_KIND = 2
REQUIRED_DISTINCT_OCCURRENCES = 2
MAX_AUDITORY_KRIMELACK_ASSOCIATION_STATE_BYTES = 64 * 1024 * 1024

_STATE_HMAC_DOMAIN = b"guala.auditory.krimelack_association_state.v1\0"
_ADMISSION_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_deliberation_admission.v1\0"
)


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
        raise ValueError(
            "auditory causal association key must be bytes or text"
        )
    if not 32 <= len(result) <= 4096:
        raise ValueError(
            "auditory causal association key has an invalid boundary"
        )
    return result


def _sign(domain: bytes, key: bytes, value: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


class AuditoryKrimelackAssociationState(str, Enum):
    UNKNOWN = "unknown"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    ADMITTED = "admitted"


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackAssociationVariant:
    association_id: str
    occurrences: tuple[AuditoryKrimelackCausalOccurrence, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "association_id": self.association_id,
            "occurrence_ids": [
                value.occurrence_id for value in self.occurrences
            ],
            "schema": AUDITORY_KRIMELACK_ASSOCIATION_VARIANT_SCHEMA,
        }

    def verify(self, *, expected_kind_id: str) -> None:
        sha256_digest(
            self.association_id,
            "auditory causal association variant",
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory causal association variant authority",
        )
        if (
            not isinstance(self.occurrences, tuple)
            or not 1
            <= len(self.occurrences)
            <= REQUIRED_DISTINCT_OCCURRENCES
            or len({
                value.occurrence_id for value in self.occurrences
            })
            != len(self.occurrences)
        ):
            raise ValueError(
                "auditory causal association evidence cardinality changed"
            )
        for occurrence in self.occurrences:
            occurrence.verify()
            if (
                occurrence.kind_id != expected_kind_id
                or occurrence.association_id != self.association_id
            ):
                raise ValueError(
                    "auditory causal association mixed structural evidence"
                )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError(
                "auditory causal association variant authority changed"
            )

    def as_record(self, *, expected_kind_id: str) -> dict[str, object]:
        self.verify(expected_kind_id=expected_kind_id)
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "occurrences": [
                value.as_record() for value in self.occurrences
            ],
        }

    @classmethod
    def from_record(
        cls,
        value: object,
        *,
        expected_kind_id: str,
    ) -> "AuditoryKrimelackAssociationVariant":
        expected = {
            "association_id",
            "authority_receipt_sha256",
            "occurrence_ids",
            "occurrences",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_KRIMELACK_ASSOCIATION_VARIANT_SCHEMA
            or not isinstance(value.get("occurrence_ids"), list)
            or not isinstance(value.get("occurrences"), list)
        ):
            raise ValueError(
                "auditory causal association variant record changed"
            )
        occurrences = tuple(
            AuditoryKrimelackCausalOccurrence.from_record(item)
            for item in value["occurrences"]
        )
        result = cls(
            association_id=value.get("association_id"),
            occurrences=occurrences,
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        if value["occurrence_ids"] != [
            item.occurrence_id for item in occurrences
        ]:
            raise ValueError(
                "auditory causal association occurrence links changed"
            )
        result.verify(expected_kind_id=expected_kind_id)
        if result.as_record(
            expected_kind_id=expected_kind_id
        ) != dict(value):
            raise ValueError(
                "auditory causal association variant is not canonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackKindAssociation:
    kind_id: str
    variants: tuple[AuditoryKrimelackAssociationVariant, ...]
    authority_receipt_sha256: str

    @property
    def state(self) -> AuditoryKrimelackAssociationState:
        if len(self.variants) > 1:
            return AuditoryKrimelackAssociationState.AMBIGUOUS
        if len(self.variants[0].occurrences) < (
            REQUIRED_DISTINCT_OCCURRENCES
        ):
            return AuditoryKrimelackAssociationState.UNCONFIRMED
        return AuditoryKrimelackAssociationState.CONFIRMED

    def payload(self) -> dict[str, object]:
        return {
            "kind_id": self.kind_id,
            "schema": AUDITORY_KRIMELACK_KIND_ASSOCIATION_SCHEMA,
            "variant_authority_receipts": [
                value.authority_receipt_sha256
                for value in self.variants
            ],
        }

    def verify(self) -> None:
        sha256_digest(self.kind_id, "auditory causal associated kind")
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory causal kind association authority",
        )
        if (
            not isinstance(self.variants, tuple)
            or not 1
            <= len(self.variants)
            <= MAX_ASSOCIATION_VARIANTS_PER_KIND
            or tuple(
                sorted(
                    self.variants,
                    key=lambda value: value.association_id,
                )
            )
            != self.variants
            or len({
                value.association_id for value in self.variants
            })
            != len(self.variants)
        ):
            raise ValueError(
                "auditory causal kind association variants changed"
            )
        for variant in self.variants:
            variant.verify(expected_kind_id=self.kind_id)
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError(
                "auditory causal kind association authority changed"
            )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "state": self.state.value,
            "variants": [
                value.as_record(expected_kind_id=self.kind_id)
                for value in self.variants
            ],
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "AuditoryKrimelackKindAssociation":
        expected = {
            "authority_receipt_sha256",
            "kind_id",
            "schema",
            "state",
            "variant_authority_receipts",
            "variants",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_KRIMELACK_KIND_ASSOCIATION_SCHEMA
            or not isinstance(value.get("variants"), list)
            or not isinstance(
                value.get("variant_authority_receipts"), list
            )
        ):
            raise ValueError(
                "auditory causal kind association record changed"
            )
        kind_id = value.get("kind_id")
        variants = tuple(
            AuditoryKrimelackAssociationVariant.from_record(
                item,
                expected_kind_id=kind_id,
            )
            for item in value["variants"]
        )
        result = cls(
            kind_id=kind_id,
            variants=variants,
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        if (
            value["variant_authority_receipts"]
            != [
                item.authority_receipt_sha256 for item in variants
            ]
            or value.get("state") != result.state.value
        ):
            raise ValueError(
                "auditory causal kind association links changed"
            )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError(
                "auditory causal kind association is not canonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackAssociationObservation:
    state: AuditoryKrimelackAssociationState
    kind_id: str
    association_id: str
    distinct_occurrences: int
    variant_count: int
    repeated: bool
    association_authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackDeliberationAdmission:
    kind_id: str
    association_id: str
    current_occurrence: AuditoryKrimelackCausalOccurrence
    reinforcement_occurrence_ids: tuple[str, ...]
    association_authority_receipt_sha256: str
    authority_hmac_sha256: str

    @property
    def world_witnesses(self) -> tuple[DeliberationWitness, ...]:
        return tuple(
            value.causal_witness
            for value in self.current_occurrence.components
        )

    def payload(self) -> dict[str, object]:
        return {
            "association_authority_receipt_sha256": (
                self.association_authority_receipt_sha256
            ),
            "association_id": self.association_id,
            "current_occurrence": self.current_occurrence.as_record(),
            "kind_id": self.kind_id,
            "reinforcement_occurrence_ids": list(
                self.reinforcement_occurrence_ids
            ),
            "schema": AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA,
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        for value, name in (
            (self.kind_id, "kind"),
            (self.association_id, "association"),
            (
                self.association_authority_receipt_sha256,
                "association authority",
            ),
            (self.authority_hmac_sha256, "admission authority"),
        ):
            sha256_digest(
                value,
                f"auditory deliberation admission {name}",
            )
        self.current_occurrence.verify()
        if (
            self.current_occurrence.kind_id != self.kind_id
            or self.current_occurrence.association_id
            != self.association_id
            or not isinstance(
                self.reinforcement_occurrence_ids, tuple
            )
            or len(self.reinforcement_occurrence_ids)
            != REQUIRED_DISTINCT_OCCURRENCES
            or len(set(self.reinforcement_occurrence_ids))
            != REQUIRED_DISTINCT_OCCURRENCES
        ):
            raise ValueError(
                "auditory deliberation admission evidence changed"
            )
        for value in self.reinforcement_occurrence_ids:
            sha256_digest(
                value,
                "auditory deliberation reinforcement occurrence",
            )
        if not hmac.compare_digest(
            self.authority_hmac_sha256,
            _sign(_ADMISSION_HMAC_DOMAIN, key, self.payload()),
        ):
            raise ValueError(
                "auditory deliberation admission HMAC changed"
            )

    def as_record(self, authority_key: object) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackDeliberationDecision:
    state: AuditoryKrimelackAssociationState
    kind_id: str
    occurrence_id: str
    association_id: str
    admission: AuditoryKrimelackDeliberationAdmission | None
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "admission_authority_hmac_sha256": (
                self.admission.authority_hmac_sha256
                if self.admission is not None
                else None
            ),
            "association_id": self.association_id,
            "kind_id": self.kind_id,
            "occurrence_id": self.occurrence_id,
            "schema": AUDITORY_KRIMELACK_DELIBERATION_DECISION_SCHEMA,
            "state": self.state.value,
        }

    def verify(self, authority_key: object) -> None:
        for value, name in (
            (self.kind_id, "kind"),
            (self.occurrence_id, "occurrence"),
            (self.association_id, "association"),
            (self.authority_receipt_sha256, "decision authority"),
        ):
            sha256_digest(value, f"auditory deliberation decision {name}")
        if self.state is AuditoryKrimelackAssociationState.ADMITTED:
            if self.admission is None:
                raise ValueError(
                    "admitted auditory deliberation has no authority"
                )
            self.admission.verify(authority_key)
            if (
                self.admission.kind_id != self.kind_id
                or self.admission.association_id != self.association_id
                or self.admission.current_occurrence.occurrence_id
                != self.occurrence_id
            ):
                raise ValueError(
                    "auditory deliberation decision left its admission"
                )
        elif self.admission is not None:
            raise ValueError(
                "stopped auditory deliberation released an admission"
            )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError(
                "auditory deliberation decision authority changed"
            )


class AuditoryKrimelackCausalAssociationOwner:
    """Serial bounded owner of exact kind/full-field causal recurrence."""

    def __init__(
        self,
        *,
        authority_key: object,
        log_event: Callable[..., None],
        association_capacity: int = (
            MAX_AUDITORY_KRIMELACK_CAUSAL_ASSOCIATIONS
        ),
        encoded_state_capacity: int = (
            MAX_AUDITORY_KRIMELACK_ASSOCIATION_STATE_BYTES
        ),
    ) -> None:
        if (
            isinstance(association_capacity, bool)
            or not isinstance(association_capacity, int)
            or not 1
            <= association_capacity
            <= MAX_AUDITORY_KRIMELACK_CAUSAL_ASSOCIATIONS
            or isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or not 1
            <= encoded_state_capacity
            <= MAX_AUDITORY_KRIMELACK_ASSOCIATION_STATE_BYTES
        ):
            raise ValueError(
                "auditory causal association capacity is invalid"
            )
        self._key = _key(authority_key)
        self._log_event = log_event
        self._association_capacity = association_capacity
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._associations: dict[
            str, AuditoryKrimelackKindAssociation
        ] = {}
        self._encoded_bytes = len(
            self._encoded(self._associations)
        )

    @staticmethod
    def _variant(
        *,
        association_id: str,
        occurrences: tuple[
            AuditoryKrimelackCausalOccurrence, ...
        ],
    ) -> AuditoryKrimelackAssociationVariant:
        provisional = AuditoryKrimelackAssociationVariant(
            association_id=association_id,
            occurrences=occurrences,
            authority_receipt_sha256="0" * 64,
        )
        return AuditoryKrimelackAssociationVariant(
            association_id=provisional.association_id,
            occurrences=provisional.occurrences,
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )

    @staticmethod
    def _association(
        *,
        kind_id: str,
        variants: tuple[
            AuditoryKrimelackAssociationVariant, ...
        ],
    ) -> AuditoryKrimelackKindAssociation:
        ordered = tuple(sorted(
            variants,
            key=lambda value: value.association_id,
        ))
        provisional = AuditoryKrimelackKindAssociation(
            kind_id=kind_id,
            variants=ordered,
            authority_receipt_sha256="0" * 64,
        )
        result = AuditoryKrimelackKindAssociation(
            kind_id=provisional.kind_id,
            variants=provisional.variants,
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )
        result.verify()
        return result

    def _state(
        self,
        associations: Mapping[
            str, AuditoryKrimelackKindAssociation
        ],
    ) -> dict[str, object]:
        return {
            "association_capacity": self._association_capacity,
            "associations": [
                associations[key].as_record()
                for key in sorted(associations)
            ],
            "encoded_state_capacity": self._encoded_state_capacity,
            "max_occurrence_bytes": (
                MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES
            ),
            "max_variants_per_kind": (
                MAX_ASSOCIATION_VARIANTS_PER_KIND
            ),
            "required_distinct_occurrences": (
                REQUIRED_DISTINCT_OCCURRENCES
            ),
            "schema": AUDITORY_KRIMELACK_ASSOCIATION_STATE_SCHEMA,
        }

    def _encoded(
        self,
        associations: Mapping[
            str, AuditoryKrimelackKindAssociation
        ],
    ) -> bytes:
        payload = _canonical(self._state(associations))
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError(
                "auditory causal association state capacity is full"
            )
        return payload

    def observe(
        self,
        occurrence: AuditoryKrimelackCausalOccurrence,
    ) -> AuditoryKrimelackAssociationObservation:
        if not isinstance(
            occurrence,
            AuditoryKrimelackCausalOccurrence,
        ):
            raise TypeError(
                "auditory association requires a causal occurrence"
            )
        occurrence.verify()
        with self._lock:
            prior = self._associations.get(occurrence.kind_id)
            if prior is None:
                if len(self._associations) >= self._association_capacity:
                    raise RuntimeError(
                        "auditory causal association capacity is full"
                    )
                variants: tuple[
                    AuditoryKrimelackAssociationVariant, ...
                ] = ()
            else:
                variants = prior.variants
            repeated = any(
                seen.occurrence_id == occurrence.occurrence_id
                for variant in variants
                for seen in variant.occurrences
            )
            matched = next((
                value
                for value in variants
                if value.association_id == occurrence.association_id
            ), None)
            if repeated:
                learned = prior
            elif matched is not None:
                learned_variant = (
                    matched
                    if len(matched.occurrences)
                    >= REQUIRED_DISTINCT_OCCURRENCES
                    else self._variant(
                        association_id=matched.association_id,
                        occurrences=(
                            *matched.occurrences,
                            occurrence,
                        ),
                    )
                )
                learned = self._association(
                    kind_id=occurrence.kind_id,
                    variants=tuple(
                        learned_variant
                        if value.association_id
                        == learned_variant.association_id
                        else value
                        for value in variants
                    ),
                )
            else:
                if len(variants) >= MAX_ASSOCIATION_VARIANTS_PER_KIND:
                    raise RuntimeError(
                        "auditory causal association conflict capacity is full"
                    )
                learned = self._association(
                    kind_id=occurrence.kind_id,
                    variants=(
                        *variants,
                        self._variant(
                            association_id=occurrence.association_id,
                            occurrences=(occurrence,),
                        ),
                    ),
                )
            if learned is None:
                raise RuntimeError(
                    "auditory association repeated absent evidence"
                )
            if not repeated:
                prospective = dict(self._associations)
                prospective[learned.kind_id] = learned
                encoded = self._encoded(prospective)
                self._associations = prospective
                self._encoded_bytes = len(encoded)
            active_variant = next((
                value
                for value in learned.variants
                if value.association_id == occurrence.association_id
            ), None)
            if active_variant is None:
                raise RuntimeError(
                    "auditory association lost current evidence"
                )
            observation = AuditoryKrimelackAssociationObservation(
                state=learned.state,
                kind_id=learned.kind_id,
                association_id=occurrence.association_id,
                distinct_occurrences=len(
                    active_variant.occurrences
                ),
                variant_count=len(learned.variants),
                repeated=repeated,
                association_authority_receipt_sha256=(
                    learned.authority_receipt_sha256
                ),
            )
        self._log_event(
            "auditory_krimelack_causal_association_observed",
            association_id=observation.association_id,
            distinct_occurrences=observation.distinct_occurrences,
            kind_id=observation.kind_id,
            repeated=observation.repeated,
            state=observation.state.value,
            variant_count=observation.variant_count,
        )
        return observation

    @staticmethod
    def _decision(
        *,
        state: AuditoryKrimelackAssociationState,
        occurrence: AuditoryKrimelackCausalOccurrence,
        admission: (
            AuditoryKrimelackDeliberationAdmission | None
        ) = None,
    ) -> AuditoryKrimelackDeliberationDecision:
        provisional = AuditoryKrimelackDeliberationDecision(
            state=state,
            kind_id=occurrence.kind_id,
            occurrence_id=occurrence.occurrence_id,
            association_id=occurrence.association_id,
            admission=admission,
            authority_receipt_sha256="0" * 64,
        )
        return AuditoryKrimelackDeliberationDecision(
            state=provisional.state,
            kind_id=provisional.kind_id,
            occurrence_id=provisional.occurrence_id,
            association_id=provisional.association_id,
            admission=provisional.admission,
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )

    def admit(
        self,
        occurrence: AuditoryKrimelackCausalOccurrence,
    ) -> AuditoryKrimelackDeliberationDecision:
        if not isinstance(
            occurrence,
            AuditoryKrimelackCausalOccurrence,
        ):
            raise TypeError(
                "auditory deliberation requires a causal occurrence"
            )
        occurrence.verify()
        with self._lock:
            association = self._associations.get(occurrence.kind_id)
            if association is None:
                decision = self._decision(
                    state=AuditoryKrimelackAssociationState.UNKNOWN,
                    occurrence=occurrence,
                )
            elif len(association.variants) > 1:
                decision = self._decision(
                    state=AuditoryKrimelackAssociationState.AMBIGUOUS,
                    occurrence=occurrence,
                )
            else:
                variant = association.variants[0]
                if variant.association_id != occurrence.association_id:
                    decision = self._decision(
                        state=(
                            AuditoryKrimelackAssociationState.CONFLICTING
                        ),
                        occurrence=occurrence,
                    )
                elif len(variant.occurrences) < (
                    REQUIRED_DISTINCT_OCCURRENCES
                ):
                    decision = self._decision(
                        state=(
                            AuditoryKrimelackAssociationState.UNCONFIRMED
                        ),
                        occurrence=occurrence,
                    )
                else:
                    admission_payload = {
                        "association_authority_receipt_sha256": (
                            association.authority_receipt_sha256
                        ),
                        "association_id": occurrence.association_id,
                        "current_occurrence": occurrence.as_record(),
                        "kind_id": occurrence.kind_id,
                        "reinforcement_occurrence_ids": [
                            value.occurrence_id
                            for value in variant.occurrences
                        ],
                        "schema": (
                            AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA
                        ),
                    }
                    admission = (
                        AuditoryKrimelackDeliberationAdmission(
                            kind_id=occurrence.kind_id,
                            association_id=occurrence.association_id,
                            current_occurrence=occurrence,
                            reinforcement_occurrence_ids=tuple(
                                value.occurrence_id
                                for value in variant.occurrences
                            ),
                            association_authority_receipt_sha256=(
                                association.authority_receipt_sha256
                            ),
                            authority_hmac_sha256=_sign(
                                _ADMISSION_HMAC_DOMAIN,
                                self._key,
                                admission_payload,
                            ),
                        )
                    )
                    admission.verify(self._key)
                    decision = self._decision(
                        state=(
                            AuditoryKrimelackAssociationState.ADMITTED
                        ),
                        occurrence=occurrence,
                        admission=admission,
                    )
            decision.verify(self._key)
            return decision

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded(self._associations)
        body = {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": AUDITORY_KRIMELACK_ASSOCIATION_ENVELOPE_SCHEMA,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        return {
            **body,
            "authority_hmac_sha256": _sign(
                _STATE_HMAC_DOMAIN,
                self._key,
                body,
            ),
        }

    def restore_encoded(self, envelope: object) -> None:
        expected = {
            "authority_hmac_sha256",
            "payload_base64",
            "schema",
            "sha256",
        }
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected
            or envelope.get("schema")
            != AUDITORY_KRIMELACK_ASSOCIATION_ENVELOPE_SCHEMA
        ):
            raise ValueError(
                "auditory causal association envelope changed"
            )
        body = {
            "payload_base64": envelope.get("payload_base64"),
            "schema": envelope.get("schema"),
            "sha256": envelope.get("sha256"),
        }
        if not hmac.compare_digest(
            str(envelope.get("authority_hmac_sha256")),
            _sign(_STATE_HMAC_DOMAIN, self._key, body),
        ):
            raise ValueError(
                "auditory causal association state HMAC changed"
            )
        text = envelope.get("payload_base64")
        if not isinstance(text, str):
            raise ValueError(
                "auditory causal association state is unreadable"
            )
        try:
            payload = base64.b64decode(text, validate=True)
            decoded = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "auditory causal association state is unreadable"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest()
            != envelope.get("sha256")
            or len(payload) > self._encoded_state_capacity
            or not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or decoded.get("schema")
            != AUDITORY_KRIMELACK_ASSOCIATION_STATE_SCHEMA
            or decoded.get("association_capacity")
            != self._association_capacity
            or decoded.get("encoded_state_capacity")
            != self._encoded_state_capacity
            or decoded.get("max_occurrence_bytes")
            != MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES
            or decoded.get("max_variants_per_kind")
            != MAX_ASSOCIATION_VARIANTS_PER_KIND
            or decoded.get("required_distinct_occurrences")
            != REQUIRED_DISTINCT_OCCURRENCES
            or not isinstance(decoded.get("associations"), list)
            or len(decoded["associations"])
            > self._association_capacity
        ):
            raise ValueError(
                "auditory causal association state boundary changed"
            )
        restored: dict[str, AuditoryKrimelackKindAssociation] = {}
        for record in decoded["associations"]:
            association = (
                AuditoryKrimelackKindAssociation.from_record(record)
            )
            if association.kind_id in restored:
                raise ValueError(
                    "auditory causal kind association is duplicated"
                )
            restored[association.kind_id] = association
        encoded = self._encoded(restored)
        if encoded != payload:
            raise ValueError(
                "auditory causal association state is not canonical"
            )
        with self._lock:
            self._associations = restored
            self._encoded_bytes = len(encoded)

    def status(self) -> dict[str, object]:
        with self._lock:
            counts = {
                state.value: sum(
                    value.state is state
                    for value in self._associations.values()
                )
                for state in (
                    AuditoryKrimelackAssociationState.UNCONFIRMED,
                    AuditoryKrimelackAssociationState.CONFIRMED,
                    AuditoryKrimelackAssociationState.AMBIGUOUS,
                )
            }
            return {
                "association_count": len(self._associations),
                "encoded_bytes": self._encoded_bytes,
                "schema": (
                    "guala.auditory.krimelack_association_status.v1"
                ),
                "states": counts,
                "variant_count": sum(
                    len(value.variants)
                    for value in self._associations.values()
                ),
            }


__all__ = (
    "AUDITORY_KRIMELACK_ASSOCIATION_ENVELOPE_SCHEMA",
    "AUDITORY_KRIMELACK_ASSOCIATION_STATE_SCHEMA",
    "AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_ASSOCIATION_STATE_BYTES",
    "MAX_AUDITORY_KRIMELACK_CAUSAL_ASSOCIATIONS",
    "AuditoryKrimelackAssociationObservation",
    "AuditoryKrimelackAssociationState",
    "AuditoryKrimelackCausalAssociationOwner",
    "AuditoryKrimelackDeliberationAdmission",
    "AuditoryKrimelackDeliberationDecision",
)
