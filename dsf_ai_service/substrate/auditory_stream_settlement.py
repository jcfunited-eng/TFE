"""Joint authority for one continuous auditory causal settlement.

The transport receipt proves exact PCM order. The cochlear receipt proves the
stateful sixteen-port recurrence advanced from the immediately prior physical
state. Auditory L5 and the six-sense settlement prove that the complete field
entered the causal experience boundary. This module binds those four already
verified authorities into one receipt; it assigns no speech, source, identity,
word, meaning, or chi semantics.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
)
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AuditoryGammatoneContinuationReceipt,
)


AUDITORY_STREAM_SETTLEMENT_SCHEMA = "guala.auditory.stream_settlement.v2"
_VERIFIED_TRANSACTION_GRAPH_AUTHORITY = object()


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


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("auditory settlement time must be exact")
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class AuditoryStreamSettlementReceipt:
    stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    source_time_start: Fraction
    source_time_end: Fraction
    assembly_id: str
    transport_receipt_sha256: str
    prior_transport_receipt_sha256: str | None
    cochlear_receipt_sha256: str
    prior_cochlear_state_receipt_sha256: str | None
    auditory_l5_authority_receipt_sha256: str
    causal_settlement_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict:
        return {
            "assembly_id": self.assembly_id,
            "auditory_l5_authority_receipt_sha256": (
                self.auditory_l5_authority_receipt_sha256
            ),
            "causal_settlement_authority_receipt_sha256": (
                self.causal_settlement_authority_receipt_sha256
            ),
            "cochlear_receipt_sha256": self.cochlear_receipt_sha256,
            "first_sample_index": self.first_sample_index,
            "sample_count": self.sample_count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": AUDITORY_STREAM_SETTLEMENT_SCHEMA,
            "sequence": self.sequence,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "stream_id": self.stream_id,
            "prior_cochlear_state_receipt_sha256": (
                self.prior_cochlear_state_receipt_sha256
            ),
            "prior_transport_receipt_sha256": (
                self.prior_transport_receipt_sha256
            ),
            "transport_receipt_sha256": self.transport_receipt_sha256,
        }

    def verify(self) -> None:
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("auditory stream settlement has no stream epoch")
        if (
            isinstance(self.sequence, bool)
            or self.sequence < 0
            or isinstance(self.first_sample_index, bool)
            or self.first_sample_index < 0
            or isinstance(self.sample_count, bool)
            or self.sample_count <= 0
        ):
            raise ValueError("auditory stream settlement sample identity is invalid")
        if self.source_time_end <= self.source_time_start:
            raise ValueError("auditory stream settlement interval is invalid")
        if not isinstance(self.assembly_id, str) or not self.assembly_id:
            raise ValueError("auditory stream settlement has no assembly")
        for value, name in (
            (self.transport_receipt_sha256, "transport receipt"),
            (self.cochlear_receipt_sha256, "cochlear receipt"),
            (self.auditory_l5_authority_receipt_sha256, "auditory L5 receipt"),
            (
                self.causal_settlement_authority_receipt_sha256,
                "causal settlement receipt",
            ),
        ):
            sha256_digest(value, f"auditory stream settlement {name}")
        for value, name in (
            (
                self.prior_transport_receipt_sha256,
                "prior transport receipt",
            ),
            (
                self.prior_cochlear_state_receipt_sha256,
                "prior cochlear state receipt",
            ),
        ):
            if value is not None:
                sha256_digest(value, f"auditory stream settlement {name}")
        if self.sequence == 0:
            if (
                self.prior_transport_receipt_sha256 is not None
                or self.prior_cochlear_state_receipt_sha256 is not None
            ):
                raise ValueError(
                    "auditory stream settlement epoch has prior authority"
                )
        elif (
            self.prior_transport_receipt_sha256 is None
            or self.prior_cochlear_state_receipt_sha256 is None
        ):
            raise ValueError(
                "auditory stream settlement continuation lost prior authority"
            )
        if _digest(self.payload()) != sha256_digest(
            self.authority_receipt_sha256,
            "auditory stream settlement authority receipt",
        ):
            raise ValueError("auditory stream settlement receipt was altered")


@dataclass(frozen=True, slots=True)
class VerifiedAuditoryTransactionGraph:
    """Request-local authority for one already verified complete graph."""

    built: BuiltSixSenseFullField
    transport: AuditoryPCMContinuityReceipt
    cochlear: AuditoryGammatoneContinuationReceipt
    auditory_l5: AuditoryL5Experience
    causal_settlement: CausalExperienceSettlement
    _construction_authority: object

    def verify_linkage(
        self,
        *,
        built: BuiltSixSenseFullField,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        auditory_l5: AuditoryL5Experience,
        causal_settlement: CausalExperienceSettlement,
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_TRANSACTION_GRAPH_AUTHORITY
            or self.built is not built
            or self.transport is not transport
            or self.cochlear is not cochlear
            or self.auditory_l5 is not auditory_l5
            or self.causal_settlement is not causal_settlement
        ):
            raise ValueError(
                "verified auditory transaction graph changed identity"
            )


def _verify_authority_links(
    *,
    transport: AuditoryPCMContinuityReceipt,
    cochlear: AuditoryGammatoneContinuationReceipt,
    auditory_l5: AuditoryL5Experience,
    causal_settlement: CausalExperienceSettlement,
) -> tuple[Fraction, Fraction]:
    if (
        cochlear.stream_id != transport.stream_id
        or cochlear.sequence != transport.sequence
        or cochlear.first_sample_index != transport.first_sample_index
        or cochlear.sample_count != transport.sample_count
        or cochlear.transport_receipt_sha256 != transport.receipt_sha256
    ):
        raise ValueError("cochlear continuation differs from PCM continuity")
    if auditory_l5.assembly_id != causal_settlement.assembly_id:
        raise ValueError("auditory L5 belongs to another causal settlement")
    expected_start = Fraction(
        transport.source_epoch_start_ns,
        1_000_000_000,
    ) + Fraction(transport.first_sample_index, PCM_SAMPLE_RATE_HZ)
    expected_end = expected_start + Fraction(
        transport.sample_count,
        PCM_SAMPLE_RATE_HZ,
    )
    if (
        auditory_l5.source_time_start != expected_start
        or auditory_l5.source_time_end != expected_end
        or causal_settlement.source_time_start != expected_start
        or causal_settlement.source_time_end != expected_end
    ):
        raise ValueError("auditory continuity interval differs from settlement")
    return expected_start, expected_end


def prepare_verified_auditory_transaction_graph(
    *,
    built: BuiltSixSenseFullField,
    auditory_l5_owner: AuditoryL5Owner,
    causal_owner: ExactCausalExperienceOwner,
    transport: AuditoryPCMContinuityReceipt,
    cochlear: AuditoryGammatoneContinuationReceipt,
    auditory_l5: AuditoryL5Experience,
    causal_settlement: CausalExperienceSettlement,
) -> VerifiedAuditoryTransactionGraph:
    """Verify one live complete graph and issue exact identity authority."""
    if not isinstance(auditory_l5_owner, AuditoryL5Owner):
        raise TypeError(
            "auditory transaction graph requires its auditory L5 owner"
        )
    if not isinstance(causal_owner, ExactCausalExperienceOwner):
        raise TypeError(
            "auditory transaction graph requires its causal owner"
        )
    built.verify_construction(
        boundary=auditory_l5.upstream_boundary,
        receipt_registry=auditory_l5.upstream_receipt_registry,
    )
    transport.verify()
    cochlear.verify()
    auditory_l5_owner.verify_transaction_linkage(
        built=built,
        experience=auditory_l5,
    )
    if not causal_owner.verify_active_transaction(causal_settlement):
        raise ValueError(
            "causal settlement has no active transaction authority"
        )
    _verify_authority_links(
        transport=transport,
        cochlear=cochlear,
        auditory_l5=auditory_l5,
        causal_settlement=causal_settlement,
    )
    return VerifiedAuditoryTransactionGraph(
        built=built,
        transport=transport,
        cochlear=cochlear,
        auditory_l5=auditory_l5,
        causal_settlement=causal_settlement,
        _construction_authority=_VERIFIED_TRANSACTION_GRAPH_AUTHORITY,
    )


def bind_auditory_stream_settlement(
    *,
    transport: AuditoryPCMContinuityReceipt,
    cochlear: AuditoryGammatoneContinuationReceipt,
    auditory_l5: AuditoryL5Experience,
    causal_settlement: CausalExperienceSettlement,
    verified_transaction: VerifiedAuditoryTransactionGraph | None = None,
) -> AuditoryStreamSettlementReceipt:
    """Verify and jointly receipt one exact continuous auditory settlement."""
    if not isinstance(transport, AuditoryPCMContinuityReceipt):
        raise TypeError("auditory settlement requires typed PCM continuity")
    if not isinstance(cochlear, AuditoryGammatoneContinuationReceipt):
        raise TypeError("auditory settlement requires typed cochlear continuity")
    if not isinstance(auditory_l5, AuditoryL5Experience):
        raise TypeError("auditory settlement requires typed auditory L5")
    if not isinstance(causal_settlement, CausalExperienceSettlement):
        raise TypeError("auditory settlement requires a typed causal settlement")
    if verified_transaction is None:
        transport.verify()
        cochlear.verify()
        auditory_l5.verify()
        causal_settlement.verify()
    else:
        if not isinstance(
            verified_transaction,
            VerifiedAuditoryTransactionGraph,
        ):
            raise TypeError(
                "auditory settlement transaction authority has wrong type"
            )
        verified_transaction.verify_linkage(
            built=verified_transaction.built,
            transport=transport,
            cochlear=cochlear,
            auditory_l5=auditory_l5,
            causal_settlement=causal_settlement,
        )
    expected_start, expected_end = _verify_authority_links(
        transport=transport,
        cochlear=cochlear,
        auditory_l5=auditory_l5,
        causal_settlement=causal_settlement,
    )
    provisional = AuditoryStreamSettlementReceipt(
        stream_id=transport.stream_id,
        sequence=transport.sequence,
        first_sample_index=transport.first_sample_index,
        sample_count=transport.sample_count,
        source_time_start=expected_start,
        source_time_end=expected_end,
        assembly_id=causal_settlement.assembly_id,
        transport_receipt_sha256=transport.receipt_sha256,
        prior_transport_receipt_sha256=transport.prior_receipt_sha256,
        cochlear_receipt_sha256=cochlear.receipt_sha256,
        prior_cochlear_state_receipt_sha256=(
            cochlear.prior_state_receipt_sha256
        ),
        auditory_l5_authority_receipt_sha256=(
            auditory_l5.authority_receipt_sha256
        ),
        causal_settlement_authority_receipt_sha256=(
            causal_settlement.authority_receipt_sha256
        ),
        authority_receipt_sha256="0" * 64,
    )
    receipt = AuditoryStreamSettlementReceipt(
        stream_id=provisional.stream_id,
        sequence=provisional.sequence,
        first_sample_index=provisional.first_sample_index,
        sample_count=provisional.sample_count,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        assembly_id=provisional.assembly_id,
        transport_receipt_sha256=provisional.transport_receipt_sha256,
        prior_transport_receipt_sha256=(
            provisional.prior_transport_receipt_sha256
        ),
        cochlear_receipt_sha256=provisional.cochlear_receipt_sha256,
        prior_cochlear_state_receipt_sha256=(
            provisional.prior_cochlear_state_receipt_sha256
        ),
        auditory_l5_authority_receipt_sha256=(
            provisional.auditory_l5_authority_receipt_sha256
        ),
        causal_settlement_authority_receipt_sha256=(
            provisional.causal_settlement_authority_receipt_sha256
        ),
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    receipt.verify()
    return receipt


__all__ = (
    "AUDITORY_STREAM_SETTLEMENT_SCHEMA",
    "AuditoryStreamSettlementReceipt",
    "VerifiedAuditoryTransactionGraph",
    "bind_auditory_stream_settlement",
    "prepare_verified_auditory_transaction_graph",
)
