"""Typed receipts for the bounded ordered live auditory terminal pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorFullFieldEvent,
    AuditoryVerifiedReceptorEventCapability,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryVerifiedSettlementCapability,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_TERMINAL_TASK_SCHEMA = "guala.auditory.terminal_task.v1"
AUDITORY_TERMINAL_ADMISSION_SCHEMA = (
    "guala.auditory.terminal_pipeline_admission.v1"
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


@dataclass(frozen=True, slots=True)
class AuditoryTerminalTask:
    pcm_s16le: bytes
    transport: AuditoryPCMContinuityReceipt
    joint_settlement: AuditoryStreamSettlementReceipt
    full_field_event: AuditoryReceptorFullFieldEvent
    settlement: CausalExperienceSettlement
    task_id: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "causal_settlement_authority_receipt_sha256": (
                self.settlement.authority_receipt_sha256
            ),
            "full_field_event_authority_receipt_sha256": (
                self.full_field_event.authority_receipt_sha256
            ),
            "joint_settlement_authority_receipt_sha256": (
                self.joint_settlement.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(self.pcm_s16le).hexdigest(),
            "schema": AUDITORY_TERMINAL_TASK_SCHEMA,
            "sequence": self.transport.sequence,
            "stream_id": self.transport.stream_id,
            "task_id": self.task_id,
            "transport_receipt_sha256": self.transport.receipt_sha256,
        }

    def verify(self) -> None:
        if not isinstance(self.pcm_s16le, bytes) or not self.pcm_s16le:
            raise ValueError("auditory terminal task PCM is absent")
        self.transport.verify()
        self.joint_settlement.verify()
        self.full_field_event.verify()
        self.settlement.verify()
        self._verify_receipt_linkage()

    def _verify_receipt_linkage(self) -> None:
        expected_id = _digest({
            "causal_settlement_authority_receipt_sha256": (
                self.settlement.authority_receipt_sha256
            ),
            "full_field_event_authority_receipt_sha256": (
                self.full_field_event.authority_receipt_sha256
            ),
            "joint_settlement_authority_receipt_sha256": (
                self.joint_settlement.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(self.pcm_s16le).hexdigest(),
            "transport_receipt_sha256": self.transport.receipt_sha256,
        })
        if (
            self.transport.pcm_sha256
            != hashlib.sha256(self.pcm_s16le).hexdigest()
            or self.joint_settlement.stream_id != self.transport.stream_id
            or self.joint_settlement.sequence != self.transport.sequence
            or self.joint_settlement.transport_receipt_sha256
            != self.transport.receipt_sha256
            or self.full_field_event.auditory_l5_authority_receipt_sha256
            != self.joint_settlement.auditory_l5_authority_receipt_sha256
            or self.settlement.authority_receipt_sha256
            != (
                self.joint_settlement
                .causal_settlement_authority_receipt_sha256
            )
            or self.task_id != expected_id
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError("auditory terminal task authority changed")

    @classmethod
    def create(
        cls,
        *,
        pcm_s16le: bytes,
        transport: AuditoryPCMContinuityReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
        full_field_event: AuditoryReceptorFullFieldEvent,
        settlement: CausalExperienceSettlement,
    ) -> "AuditoryTerminalTask":
        if not isinstance(transport, AuditoryPCMContinuityReceipt):
            raise TypeError("auditory terminal task transport is not typed")
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("auditory terminal task settlement is not typed")
        if not isinstance(
            joint_settlement,
            AuditoryStreamSettlementReceipt,
        ):
            raise TypeError("auditory terminal joint settlement is not typed")
        if not isinstance(
            full_field_event,
            AuditoryReceptorFullFieldEvent,
        ):
            raise TypeError("auditory terminal full-field event is not typed")
        if not isinstance(pcm_s16le, bytes):
            raise TypeError("auditory terminal task PCM is not immutable")
        task_id = _digest({
            "causal_settlement_authority_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "full_field_event_authority_receipt_sha256": (
                full_field_event.authority_receipt_sha256
            ),
            "joint_settlement_authority_receipt_sha256": (
                joint_settlement.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(pcm_s16le).hexdigest(),
            "transport_receipt_sha256": transport.receipt_sha256,
        })
        provisional = cls(
            pcm_s16le=pcm_s16le,
            transport=transport,
            joint_settlement=joint_settlement,
            full_field_event=full_field_event,
            settlement=settlement,
            task_id=task_id,
            authority_receipt_sha256="0" * 64,
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        return result

    @classmethod
    def create_from_verified_custody(
        cls,
        *,
        pcm_s16le: bytes,
        transport: AuditoryPCMContinuityReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
        full_field_event: AuditoryReceptorFullFieldEvent,
        settlement: CausalExperienceSettlement,
        receptor_capability: AuditoryVerifiedReceptorEventCapability,
        settlement_capability: AuditoryVerifiedSettlementCapability,
    ) -> "AuditoryTerminalTask":
        if not isinstance(
            receptor_capability,
            AuditoryVerifiedReceptorEventCapability,
        ) or not isinstance(
            settlement_capability,
            AuditoryVerifiedSettlementCapability,
        ):
            raise TypeError(
                "auditory terminal task requires verified custody"
            )
        receptor_capability.verify_identity(full_field_event)
        settlement_capability.verify_linkage(
            pcm_s16le=pcm_s16le,
            capture=settlement_capability.capture,
            auditory_l5=settlement_capability.auditory_l5,
            transport=transport,
            cochlear=settlement_capability.cochlear,
            causal_settlement=settlement,
            joint_settlement=joint_settlement,
        )
        task_id = _digest({
            "causal_settlement_authority_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "full_field_event_authority_receipt_sha256": (
                full_field_event.authority_receipt_sha256
            ),
            "joint_settlement_authority_receipt_sha256": (
                joint_settlement.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(pcm_s16le).hexdigest(),
            "transport_receipt_sha256": transport.receipt_sha256,
        })
        provisional = cls(
            pcm_s16le=pcm_s16le,
            transport=transport,
            joint_settlement=joint_settlement,
            full_field_event=full_field_event,
            settlement=settlement,
            task_id=task_id,
            authority_receipt_sha256="0" * 64,
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result._verify_receipt_linkage()
        return result


@dataclass(frozen=True, slots=True)
class AuditoryTerminalAdmission:
    state: str
    stream_id: str
    sequence: int
    task_id: str | None
    pending_count: int
    capacity: int
    reason: str
    authority_receipt_sha256: str

    @property
    def firing_state(self) -> str:
        return "not_evaluated_pipeline_pending"

    @property
    def learning_state(self) -> str:
        return self.state

    def payload(self) -> dict[str, object]:
        return {
            "capacity": self.capacity,
            "pending_count": self.pending_count,
            "reason": self.reason,
            "schema": AUDITORY_TERMINAL_ADMISSION_SCHEMA,
            "sequence": self.sequence,
            "state": self.state,
            "stream_id": self.stream_id,
            "task_id": self.task_id,
        }

    def verify(self) -> None:
        if (
            self.state not in ("queued", "indeterminate_capacity")
            or not isinstance(self.stream_id, str)
            or not self.stream_id
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or isinstance(self.pending_count, bool)
            or not isinstance(self.pending_count, int)
            or self.pending_count < 0
            or isinstance(self.capacity, bool)
            or not isinstance(self.capacity, int)
            or self.capacity <= 0
            or not isinstance(self.reason, str)
            or not self.reason
        ):
            raise ValueError("auditory terminal admission changed")
        if self.state == "queued":
            if not isinstance(self.task_id, str) or len(self.task_id) != 64:
                raise ValueError("queued auditory terminal task is absent")
        elif self.task_id is not None:
            raise ValueError("indeterminate auditory terminal falsely queued")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("auditory terminal admission receipt changed")

    @classmethod
    def create(
        cls,
        *,
        state: str,
        stream_id: str,
        sequence: int,
        task_id: str | None,
        pending_count: int,
        capacity: int,
        reason: str,
    ) -> "AuditoryTerminalAdmission":
        provisional = cls(
            state=state,
            stream_id=stream_id,
            sequence=sequence,
            task_id=task_id,
            pending_count=pending_count,
            capacity=capacity,
            reason=reason,
            authority_receipt_sha256="0" * 64,
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        return result

    def as_record(self) -> dict[str, object]:
        self.verify()
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


__all__ = (
    "AUDITORY_TERMINAL_ADMISSION_SCHEMA",
    "AUDITORY_TERMINAL_TASK_SCHEMA",
    "AuditoryTerminalAdmission",
    "AuditoryTerminalTask",
)
