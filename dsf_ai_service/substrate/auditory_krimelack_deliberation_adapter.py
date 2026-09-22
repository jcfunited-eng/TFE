"""Authenticated bridge from confirmed hearing to causal deliberation.

This owner does not infer an action from an auditory kind.  It verifies one
confirmed ``AuditoryKrimelackDeliberationAdmission`` against the corresponding
live exact causal settlements, preserves every component full-field witness,
and passes only the final real settlement to the existing
``CausalDeliberation`` physics.  Existing learned action/outcome relations
remain the sole action authority.

For an occurrence spanning two transport settlements, both witnesses remain
in the authenticated intake.  No synthetic combined field is fabricated.
The final settlement is the current world presented to deliberation; the
preceding settlement remains exact causal provenance for the heard occurrence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA,
    AuditoryKrimelackDeliberationAdmission,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES,
    AuditoryKrimelackCausalOccurrence,
)
from dsf_ai_service.substrate.causal_action_cycle import (
    CausalActionCycle,
    VerifiedActionRelationEvidence,
)
from dsf_ai_service.substrate.causal_deliberation import (
    CausalDeliberation,
    DeliberationTurn,
    DeliberationWitness,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_KRIMELACK_DELIBERATION_INTAKE_SCHEMA = (
    "guala.auditory.krimelack_deliberation_intake.v1"
)
AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_STATE_SCHEMA = (
    "guala.auditory.krimelack_deliberation_adapter_state.v1"
)
AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_ENVELOPE_SCHEMA = (
    "guala.auditory.krimelack_deliberation_adapter_hmac.v1"
)

MAX_AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_BYTES = 16 * 1024 * 1024
MIN_AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_BYTES = (
    MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES + 16 * 1024
)

_INTAKE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_deliberation_intake.v1\0"
)
_STATE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_deliberation_adapter_state.v1\0"
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(
            "auditory deliberation adapter key must be bytes or text"
        )
    if not 32 <= len(result) <= 4096:
        raise ValueError(
            "auditory deliberation adapter key has an invalid boundary"
        )
    return result


def _sign(domain: bytes, key: bytes, value: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


def _admission_from_record(
    value: object,
    *,
    authority_key: bytes,
) -> AuditoryKrimelackDeliberationAdmission:
    expected = {
        "association_authority_receipt_sha256",
        "association_id",
        "authority_hmac_sha256",
        "current_occurrence",
        "kind_id",
        "reinforcement_occurrence_ids",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema")
        != AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA
        or not isinstance(
            value.get("reinforcement_occurrence_ids"), list
        )
    ):
        raise ValueError(
            "auditory deliberation admission record changed"
        )
    result = AuditoryKrimelackDeliberationAdmission(
        kind_id=value.get("kind_id"),
        association_id=value.get("association_id"),
        current_occurrence=(
            AuditoryKrimelackCausalOccurrence.from_record(
                value.get("current_occurrence")
            )
        ),
        reinforcement_occurrence_ids=tuple(
            value["reinforcement_occurrence_ids"]
        ),
        association_authority_receipt_sha256=value.get(
            "association_authority_receipt_sha256"
        ),
        authority_hmac_sha256=value.get(
            "authority_hmac_sha256"
        ),
    )
    result.verify(authority_key)
    if result.as_record(authority_key) != dict(value):
        raise ValueError(
            "auditory deliberation admission is not canonical"
        )
    return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackDeliberationIntake:
    admission: AuditoryKrimelackDeliberationAdmission
    world_witness_receipts: tuple[str, ...]
    current_world_receipt_sha256: str
    deliberation_status: str
    episode_id: str | None
    depth: int
    stop_reason: str | None
    action_receipt_sha256: str | None
    authority_hmac_sha256: str

    def payload(self, authority_key: object) -> dict[str, object]:
        return {
            "action_receipt_sha256": self.action_receipt_sha256,
            "admission": self.admission.as_record(authority_key),
            "current_world_receipt_sha256": (
                self.current_world_receipt_sha256
            ),
            "deliberation_status": self.deliberation_status,
            "depth": self.depth,
            "episode_id": self.episode_id,
            "schema": AUDITORY_KRIMELACK_DELIBERATION_INTAKE_SCHEMA,
            "stop_reason": self.stop_reason,
            "world_witness_receipts": list(
                self.world_witness_receipts
            ),
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        self.admission.verify(key)
        expected_receipts = tuple(
            value.settlement_receipt_sha256
            for value in self.admission.world_witnesses
        )
        if (
            not isinstance(self.world_witness_receipts, tuple)
            or self.world_witness_receipts != expected_receipts
            or not self.world_witness_receipts
            or self.current_world_receipt_sha256
            != self.world_witness_receipts[-1]
            or isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth < 0
            or self.deliberation_status not in {"action", "stopped"}
        ):
            raise ValueError(
                "auditory deliberation intake witness boundary changed"
            )
        for value in self.world_witness_receipts:
            sha256_digest(
                value,
                "auditory deliberation intake world witness",
            )
        sha256_digest(
            self.current_world_receipt_sha256,
            "auditory deliberation intake current world",
        )
        sha256_digest(
            self.authority_hmac_sha256,
            "auditory deliberation intake authority",
        )
        if self.deliberation_status == "action":
            if (
                self.episode_id is None
                or self.depth <= 0
                or self.stop_reason is not None
                or self.action_receipt_sha256 is None
            ):
                raise ValueError(
                    "auditory deliberation action intake changed"
                )
            sha256_digest(
                self.episode_id,
                "auditory deliberation intake episode",
            )
            sha256_digest(
                self.action_receipt_sha256,
                "auditory deliberation intake action",
            )
        elif (
            self.stop_reason is None
            or self.action_receipt_sha256 is not None
        ):
            raise ValueError(
                "auditory deliberation stopped intake changed"
            )
        if not hmac.compare_digest(
            self.authority_hmac_sha256,
            _sign(
                _INTAKE_HMAC_DOMAIN,
                key,
                self.payload(key),
            ),
        ):
            raise ValueError(
                "auditory deliberation intake HMAC changed"
            )

    def as_record(self, authority_key: object) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(authority_key),
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
        *,
        authority_key: object,
    ) -> "AuditoryKrimelackDeliberationIntake":
        expected = {
            "action_receipt_sha256",
            "admission",
            "authority_hmac_sha256",
            "current_world_receipt_sha256",
            "deliberation_status",
            "depth",
            "episode_id",
            "schema",
            "stop_reason",
            "world_witness_receipts",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_KRIMELACK_DELIBERATION_INTAKE_SCHEMA
            or not isinstance(value.get("world_witness_receipts"), list)
        ):
            raise ValueError(
                "auditory deliberation intake record changed"
            )
        key = _key(authority_key)
        result = cls(
            admission=_admission_from_record(
                value.get("admission"),
                authority_key=key,
            ),
            world_witness_receipts=tuple(
                value["world_witness_receipts"]
            ),
            current_world_receipt_sha256=value.get(
                "current_world_receipt_sha256"
            ),
            deliberation_status=value.get("deliberation_status"),
            episode_id=value.get("episode_id"),
            depth=value.get("depth"),
            stop_reason=value.get("stop_reason"),
            action_receipt_sha256=value.get(
                "action_receipt_sha256"
            ),
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
        )
        result.verify(key)
        if result.as_record(key) != dict(value):
            raise ValueError(
                "auditory deliberation intake is not canonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackDeliberationResult:
    intake: AuditoryKrimelackDeliberationIntake
    turn: DeliberationTurn


class AuditoryKrimelackDeliberationAdapterOwner:
    """Serial authenticated admission gate for existing deliberation."""

    def __init__(
        self,
        *,
        authority_key: object,
        deliberation: CausalDeliberation,
        log_event: Callable[..., None],
        encoded_state_capacity: int = (
            MAX_AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_BYTES
        ),
    ) -> None:
        if not isinstance(deliberation, CausalDeliberation):
            raise TypeError(
                "auditory adapter requires causal deliberation"
            )
        if (
            isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or not MIN_AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_BYTES
            <= encoded_state_capacity
            <= MAX_AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_BYTES
        ):
            raise ValueError(
                "auditory deliberation adapter capacity is invalid"
            )
        self._key = _key(authority_key)
        self._deliberation = deliberation
        self._log_event = log_event
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._latest: AuditoryKrimelackDeliberationIntake | None = None

    def _state(
        self,
        latest: AuditoryKrimelackDeliberationIntake | None,
    ) -> dict[str, object]:
        return {
            "encoded_state_capacity": self._encoded_state_capacity,
            "latest_intake": (
                latest.as_record(self._key)
                if latest is not None
                else None
            ),
            "schema": (
                AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_STATE_SCHEMA
            ),
        }

    def _encoded(
        self,
        latest: AuditoryKrimelackDeliberationIntake | None,
    ) -> bytes:
        payload = _canonical(self._state(latest))
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError(
                "auditory deliberation adapter state capacity is full"
            )
        return payload

    @staticmethod
    def _verified_worlds(
        admission: AuditoryKrimelackDeliberationAdmission,
        settlements: tuple[CausalExperienceSettlement, ...],
    ) -> tuple[DeliberationWitness, ...]:
        expected = admission.world_witnesses
        if (
            not isinstance(settlements, tuple)
            or len(settlements) != len(expected)
            or not settlements
        ):
            raise ValueError(
                "auditory deliberation settlement cardinality changed"
            )
        verified = []
        for settlement, witness in zip(
            settlements,
            expected,
            strict=True,
        ):
            if not isinstance(
                settlement,
                CausalExperienceSettlement,
            ):
                raise TypeError(
                    "auditory deliberation requires causal settlements"
                )
            settlement.verify()
            live = DeliberationWitness.from_settlement(
                settlement,
                max_bytes=2 * 1024 * 1024,
            )
            if live != witness:
                raise ValueError(
                    "auditory deliberation admission left its live full field"
                )
            verified.append(live)
        return tuple(verified)

    def start(
        self,
        *,
        admission: AuditoryKrimelackDeliberationAdmission,
        causal_settlements: tuple[
            CausalExperienceSettlement, ...
        ],
        action_cycle: CausalActionCycle | None = None,
        admitted_evidence: tuple[
            VerifiedActionRelationEvidence, ...
        ] | None = None,
    ) -> AuditoryKrimelackDeliberationResult:
        if not isinstance(
            admission,
            AuditoryKrimelackDeliberationAdmission,
        ):
            raise TypeError(
                "auditory deliberation requires confirmed admission"
            )
        admission.verify(self._key)
        worlds = self._verified_worlds(
            admission,
            causal_settlements,
        )
        with self._lock:
            turn = self._deliberation.start(
                causal_settlements[-1],
                action_cycle=action_cycle,
                admitted_evidence=admitted_evidence,
            )
            intake_payload = {
                "action_receipt_sha256": (
                    turn.action_receipt_sha256
                ),
                "admission": admission.as_record(self._key),
                "current_world_receipt_sha256": (
                    worlds[-1].settlement_receipt_sha256
                ),
                "deliberation_status": turn.status,
                "depth": turn.depth,
                "episode_id": turn.episode_id,
                "schema": (
                    AUDITORY_KRIMELACK_DELIBERATION_INTAKE_SCHEMA
                ),
                "stop_reason": turn.stop_reason,
                "world_witness_receipts": [
                    value.settlement_receipt_sha256
                    for value in worlds
                ],
            }
            intake = AuditoryKrimelackDeliberationIntake(
                admission=admission,
                world_witness_receipts=tuple(
                    value.settlement_receipt_sha256
                    for value in worlds
                ),
                current_world_receipt_sha256=(
                    worlds[-1].settlement_receipt_sha256
                ),
                deliberation_status=turn.status,
                episode_id=turn.episode_id,
                depth=turn.depth,
                stop_reason=turn.stop_reason,
                action_receipt_sha256=(
                    turn.action_receipt_sha256
                ),
                authority_hmac_sha256=_sign(
                    _INTAKE_HMAC_DOMAIN,
                    self._key,
                    intake_payload,
                ),
            )
            intake.verify(self._key)
            self._encoded(intake)
            self._latest = intake
        self._log_event(
            "auditory_krimelack_deliberation_admitted",
            association_id=admission.association_id,
            component_count=len(worlds),
            deliberation_status=turn.status,
            kind_id=admission.kind_id,
            stop_reason=turn.stop_reason,
        )
        return AuditoryKrimelackDeliberationResult(
            intake=intake,
            turn=turn,
        )

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded(self._latest)
        body = {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": (
                AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_ENVELOPE_SCHEMA
            ),
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
            != AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_ENVELOPE_SCHEMA
        ):
            raise ValueError(
                "auditory deliberation adapter envelope changed"
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
                "auditory deliberation adapter state HMAC changed"
            )
        text = envelope.get("payload_base64")
        if not isinstance(text, str):
            raise ValueError(
                "auditory deliberation adapter state is unreadable"
            )
        try:
            payload = base64.b64decode(text, validate=True)
            decoded = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "auditory deliberation adapter state is unreadable"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest()
            != envelope.get("sha256")
            or len(payload) > self._encoded_state_capacity
            or not isinstance(decoded, Mapping)
            or set(decoded)
            != {
                "encoded_state_capacity",
                "latest_intake",
                "schema",
            }
            or decoded.get("schema")
            != AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_STATE_SCHEMA
            or decoded.get("encoded_state_capacity")
            != self._encoded_state_capacity
            or _canonical(decoded) != payload
        ):
            raise ValueError(
                "auditory deliberation adapter state boundary changed"
            )
        raw_latest = decoded.get("latest_intake")
        latest = (
            None
            if raw_latest is None
            else AuditoryKrimelackDeliberationIntake.from_record(
                raw_latest,
                authority_key=self._key,
            )
        )
        if self._encoded(latest) != payload:
            raise ValueError(
                "auditory deliberation adapter state is not canonical"
            )
        with self._lock:
            self._latest = latest

    def latest_intake(
        self,
    ) -> AuditoryKrimelackDeliberationIntake | None:
        with self._lock:
            return self._latest


__all__ = (
    "AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_ENVELOPE_SCHEMA",
    "AUDITORY_KRIMELACK_DELIBERATION_ADAPTER_STATE_SCHEMA",
    "AUDITORY_KRIMELACK_DELIBERATION_INTAKE_SCHEMA",
    "AuditoryKrimelackDeliberationAdapterOwner",
    "AuditoryKrimelackDeliberationIntake",
    "AuditoryKrimelackDeliberationResult",
)
