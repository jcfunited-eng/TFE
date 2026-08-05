"""Atomic bounded orchestration for grounded auditory cognition.

This owner is the single persistence and transaction boundary around the
typed auditory causal stages.  It accepts only a verified UNIQUE Krimelack
recognition together with the exact auditory, stream, and causal settlements
that produced it.  The stages remain:

    causal occurrence -> recurrent association -> deliberation admission
    -> grounded referent -> ordered grounded composition

No transcript, tutor label, token, scripted response, action relation, or chi
identity enters this owner.  The complete explicit DSF and six-sense fields
remain inside the existing typed authorities.  Digests are transaction links
and indexes only.

All mutable child owners, including causal deliberation, are restored together
if an advance, composition observation, aggregate capacity check, or event
commit fails.  The outward persistence surface is one canonical HMAC envelope
with a fixed aggregate byte boundary.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackAssociationObservation,
    AuditoryKrimelackAssociationState,
    AuditoryKrimelackCausalAssociationOwner,
    AuditoryKrimelackDeliberationAdmission,
    AuditoryKrimelackDeliberationDecision,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    AuditoryKrimelackCausalOccurrence,
    bind_auditory_krimelack_causal_occurrence,
)
from dsf_ai_service.substrate.auditory_krimelack_deliberation_adapter import (
    AuditoryKrimelackDeliberationAdapterOwner,
    AuditoryKrimelackDeliberationResult,
)
from dsf_ai_service.substrate.auditory_krimelack_grounded_composition import (
    AuditoryGroundedCompositionObservation,
    AuditoryGroundedCompositionResolution,
    AuditoryKrimelackGroundedCompositionOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_grounded_referent import (
    AuditoryGroundedConstruction,
    AuditoryGroundedLearning,
    AuditoryKrimelackGroundedReferentOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    AuditoryKrimelackPreparedExemplar,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamRecognition,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.causal_deliberation import (
    CausalDeliberation,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_KRIMELACK_COGNITION_STATE_SCHEMA = (
    "guala.auditory.krimelack_cognition_state.v1"
)
AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA = (
    "guala.auditory.krimelack_cognition_hmac.v1"
)
DEFAULT_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES = 128 * 1024 * 1024
MAX_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES = 256 * 1024 * 1024
AUDITORY_KRIMELACK_COGNITION_ENVELOPE_RESERVE_BYTES = 4096
DEFAULT_AUDITORY_KRIMELACK_COGNITION_PERSISTENCE_BYTES = (
    4
    * (
        (
            DEFAULT_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES
            + 2
        )
        // 3
    )
    + AUDITORY_KRIMELACK_COGNITION_ENVELOPE_RESERVE_BYTES
)

_STATE_HMAC_DOMAIN = b"guala.auditory.krimelack_cognition_state.v1\0"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _key(value: object, name: str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(f"{name} must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError(f"{name} has an invalid boundary")
    return result


def _sign(key: bytes, value: object) -> str:
    return hmac.new(
        key,
        _STATE_HMAC_DOMAIN + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackCognitionAdvance:
    occurrence: AuditoryKrimelackCausalOccurrence
    association: AuditoryKrimelackAssociationObservation
    decision: AuditoryKrimelackDeliberationDecision
    deliberation: AuditoryKrimelackDeliberationResult | None
    grounding: AuditoryGroundedLearning
    state_revision_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackCognitionCompositionAdvance:
    observation: AuditoryGroundedCompositionObservation
    resolution: AuditoryGroundedCompositionResolution
    state_revision_sha256: str


class AuditoryKrimelackCognitionOwner:
    """One serial owner for the exact auditory cognition chain."""

    def __init__(
        self,
        *,
        authority_key: object,
        deliberation_authority_key: object,
        log_event: Callable[..., None],
        encoded_state_capacity: int = (
            DEFAULT_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES
        ),
    ) -> None:
        if (
            isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or not 1
            <= encoded_state_capacity
            <= MAX_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES
        ):
            raise ValueError(
                "auditory cognition state capacity is invalid"
            )
        self._key = _key(
            authority_key,
            "auditory cognition authority key",
        )
        self._deliberation_key = _key(
            deliberation_authority_key,
            "auditory cognition deliberation authority key",
        )
        self._log_event = log_event
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._deliberation = CausalDeliberation(
            authority_key=self._deliberation_key,
        )
        self._association = (
            AuditoryKrimelackCausalAssociationOwner(
                authority_key=self._key,
                log_event=self._component_event,
            )
        )
        self._adapter = AuditoryKrimelackDeliberationAdapterOwner(
            authority_key=self._key,
            deliberation=self._deliberation,
            log_event=self._component_event,
        )
        self._grounding = AuditoryKrimelackGroundedReferentOwner(
            authority_key=self._key,
            log_event=self._component_event,
        )
        self._composition = (
            AuditoryKrimelackGroundedCompositionOwner(
                authority_key=self._key,
                log_event=self._component_event,
            )
        )
        initial = self._encoded()
        self._encoded_bytes = len(initial)
        self._state_revision_sha256 = hashlib.sha256(
            initial
        ).hexdigest()

    @staticmethod
    def _component_event(
        _event: str,
        **_fields: object,
    ) -> None:
        # Child mutations are represented by one aggregate event only after
        # the complete root transaction has passed its capacity boundary.
        return None

    def _state(self) -> dict[str, object]:
        return {
            "association": self._association.encoded_snapshot(),
            "composition": self._composition.encoded_snapshot(),
            "deliberation": self._deliberation.encoded_snapshot(),
            "deliberation_adapter": self._adapter.encoded_snapshot(),
            "encoded_state_capacity": self._encoded_state_capacity,
            "grounding": self._grounding.encoded_snapshot(),
            "schema": AUDITORY_KRIMELACK_COGNITION_STATE_SCHEMA,
        }

    def _encoded(self) -> bytes:
        payload = _canonical(self._state())
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError(
                "auditory cognition aggregate state capacity is full"
            )
        return payload

    def _restore_components(self, state: Mapping[str, object]) -> None:
        self._association.restore_encoded(state["association"])
        self._composition.restore_encoded(state["composition"])
        self._deliberation.restore_encoded(state["deliberation"])
        self._adapter.restore_encoded(state["deliberation_adapter"])
        self._grounding.restore_encoded(state["grounding"])

    def advance(
        self,
        *,
        recognition: AuditoryKrimelackStreamRecognition,
        auditory_experiences: tuple[AuditoryL5Experience, ...],
        stream_settlements: tuple[
            AuditoryStreamSettlementReceipt, ...
        ],
        causal_settlements: tuple[
            CausalExperienceSettlement, ...
        ],
        prepared_exemplars: (
            tuple[AuditoryKrimelackPreparedExemplar, ...] | None
        ) = None,
    ) -> AuditoryKrimelackCognitionAdvance:
        """Atomically advance one exact recognized lived occurrence."""

        occurrence = bind_auditory_krimelack_causal_occurrence(
            recognition=recognition,
            auditory_experiences=auditory_experiences,
            stream_settlements=stream_settlements,
            causal_settlements=causal_settlements,
            prepared_exemplars=prepared_exemplars,
        )
        with self._lock:
            prior = self._state()
            try:
                association = self._association.observe(occurrence)
                decision = self._association.admit(occurrence)
                deliberation = None
                if (
                    decision.state
                    is AuditoryKrimelackAssociationState.ADMITTED
                ):
                    if decision.admission is None:
                        raise RuntimeError(
                            "admitted auditory cognition lost admission"
                        )
                    deliberation = self._adapter.start(
                        admission=decision.admission,
                        causal_settlements=causal_settlements,
                        action_cycle=None,
                        admitted_evidence=(),
                    )
                    self._grounding.observe(decision.admission)
                elif decision.admission is not None:
                    raise RuntimeError(
                        "unadmitted auditory cognition gained admission"
                    )
                grounding = self._grounding.learn()
                payload = self._encoded()
                revision = hashlib.sha256(payload).hexdigest()
                result = AuditoryKrimelackCognitionAdvance(
                    occurrence=occurrence,
                    association=association,
                    decision=decision,
                    deliberation=deliberation,
                    grounding=grounding,
                    state_revision_sha256=revision,
                )
                self._log_event(
                    "auditory_krimelack_cognition_advanced",
                    association_state=association.state.value,
                    deliberation_admitted=deliberation is not None,
                    grounding_state=grounding.state,
                    kind_id=occurrence.kind_id,
                    occurrence_id=occurrence.occurrence_id,
                    state_revision_sha256=revision,
                )
                self._encoded_bytes = len(payload)
                self._state_revision_sha256 = revision
            except BaseException:
                self._restore_components(prior)
                raise
        return result

    def compose(
        self,
        *,
        grounding: AuditoryGroundedConstruction,
        left: AuditoryKrimelackDeliberationAdmission,
        right: AuditoryKrimelackDeliberationAdmission,
    ) -> AuditoryKrimelackCognitionCompositionAdvance:
        """Atomically observe one exact ordered pair under current grounding."""

        if not isinstance(grounding, AuditoryGroundedConstruction):
            raise TypeError(
                "auditory cognition composition requires grounding"
            )
        if not isinstance(
            left,
            AuditoryKrimelackDeliberationAdmission,
        ) or not isinstance(
            right,
            AuditoryKrimelackDeliberationAdmission,
        ):
            raise TypeError(
                "auditory cognition composition requires admissions"
            )
        grounding.verify(self._key)
        left.verify(self._key)
        right.verify(self._key)
        with self._lock:
            prior = self._state()
            try:
                current = self._grounding.learn()
                if (
                    current.construction is None
                    or current.construction != grounding
                ):
                    raise ValueError(
                        "auditory cognition grounding is not current"
                    )
                for admission in (left, right):
                    decision = self._association.admit(
                        admission.current_occurrence
                    )
                    if (
                        decision.state
                        is not AuditoryKrimelackAssociationState.ADMITTED
                        or decision.admission != admission
                    ):
                        raise ValueError(
                            "auditory cognition admission is not owned"
                        )
                observation = self._composition.observe(
                    grounding=grounding,
                    left=left,
                    right=right,
                )
                resolution = self._composition.resolve(
                    grounding_construction_id=(
                        grounding.construction_id
                    ),
                    left_kind_id=left.kind_id,
                    right_kind_id=right.kind_id,
                )
                payload = self._encoded()
                revision = hashlib.sha256(payload).hexdigest()
                result = (
                    AuditoryKrimelackCognitionCompositionAdvance(
                        observation=observation,
                        resolution=resolution,
                        state_revision_sha256=revision,
                    )
                )
                self._log_event(
                    "auditory_krimelack_cognition_composed",
                    composition_id=observation.composition_id,
                    distinct_episodes=(
                        observation.distinct_episodes
                    ),
                    state=observation.state,
                    state_revision_sha256=revision,
                )
                self._encoded_bytes = len(payload)
                self._state_revision_sha256 = revision
            except BaseException:
                self._restore_components(prior)
                raise
        return result

    def current_grounding(self) -> AuditoryGroundedLearning:
        with self._lock:
            return self._grounding.learn()

    def resolve_composition(
        self,
        *,
        grounding_construction_id: str,
        left_kind_id: str,
        right_kind_id: str,
    ) -> AuditoryGroundedCompositionResolution:
        with self._lock:
            return self._composition.resolve(
                grounding_construction_id=(
                    grounding_construction_id
                ),
                left_kind_id=left_kind_id,
                right_kind_id=right_kind_id,
            )

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded()
        body = {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        return {
            **body,
            "authority_hmac_sha256": _sign(self._key, body),
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
            != AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA
        ):
            raise ValueError(
                "auditory cognition envelope changed"
            )
        text = envelope.get("payload_base64")
        if (
            not isinstance(text, str)
            or len(text)
            > 4 * ((self._encoded_state_capacity + 2) // 3)
        ):
            raise ValueError(
                "auditory cognition state is unreadable"
            )
        body = {
            "payload_base64": text,
            "schema": envelope.get("schema"),
            "sha256": envelope.get("sha256"),
        }
        if not hmac.compare_digest(
            str(envelope.get("authority_hmac_sha256")),
            _sign(self._key, body),
        ):
            raise ValueError(
                "auditory cognition state HMAC changed"
            )
        try:
            payload = base64.b64decode(text, validate=True)
            decoded = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "auditory cognition state is unreadable"
            ) from error
        if (
            not payload
            or len(payload) > self._encoded_state_capacity
            or base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest()
            != envelope.get("sha256")
            or not isinstance(decoded, Mapping)
            or set(decoded)
            != {
                "association",
                "composition",
                "deliberation",
                "deliberation_adapter",
                "encoded_state_capacity",
                "grounding",
                "schema",
            }
            or decoded.get("schema")
            != AUDITORY_KRIMELACK_COGNITION_STATE_SCHEMA
            or decoded.get("encoded_state_capacity")
            != self._encoded_state_capacity
            or _canonical(decoded) != payload
        ):
            raise ValueError(
                "auditory cognition state boundary changed"
            )
        with self._lock:
            prior = self._state()
            try:
                self._restore_components(decoded)
                if self._encoded() != payload:
                    raise ValueError(
                        "auditory cognition state is not canonical"
                    )
                self._encoded_bytes = len(payload)
                self._state_revision_sha256 = hashlib.sha256(
                    payload
                ).hexdigest()
            except BaseException:
                self._restore_components(prior)
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "association": self._association.status(),
                "composition": self._composition.status(),
                "deliberation": self._deliberation.status(),
                "encoded_bytes": self._encoded_bytes,
                "grounding": self._grounding.status(),
                "latest_deliberation_intake": (
                    self._adapter.latest_intake() is not None
                ),
                "schema": (
                    "guala.auditory.krimelack_cognition_status.v1"
                ),
                "state_revision_sha256": self._state_revision_sha256,
            }


__all__ = (
    "AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA",
    "AUDITORY_KRIMELACK_COGNITION_ENVELOPE_RESERVE_BYTES",
    "AUDITORY_KRIMELACK_COGNITION_STATE_SCHEMA",
    "AuditoryKrimelackCognitionAdvance",
    "AuditoryKrimelackCognitionCompositionAdvance",
    "AuditoryKrimelackCognitionOwner",
    "DEFAULT_AUDITORY_KRIMELACK_COGNITION_PERSISTENCE_BYTES",
    "DEFAULT_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES",
    "MAX_AUDITORY_KRIMELACK_COGNITION_STATE_BYTES",
)
