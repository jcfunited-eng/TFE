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

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AuditoryGammatoneContinuationReceipt,
)


AUDITORY_STREAM_SETTLEMENT_SCHEMA = "guala.auditory.stream_settlement.v1"


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
    cochlear_receipt_sha256: str
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
        if _digest(self.payload()) != sha256_digest(
            self.authority_receipt_sha256,
            "auditory stream settlement authority receipt",
        ):
            raise ValueError("auditory stream settlement receipt was altered")


def bind_auditory_stream_settlement(
    *,
    transport: AuditoryPCMContinuityReceipt,
    cochlear: AuditoryGammatoneContinuationReceipt,
    auditory_l5: AuditoryL5Experience,
    causal_settlement: CausalExperienceSettlement,
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
    transport.verify()
    cochlear.verify()
    auditory_l5.verify()
    causal_settlement.verify()
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
    provisional = AuditoryStreamSettlementReceipt(
        stream_id=transport.stream_id,
        sequence=transport.sequence,
        first_sample_index=transport.first_sample_index,
        sample_count=transport.sample_count,
        source_time_start=expected_start,
        source_time_end=expected_end,
        assembly_id=causal_settlement.assembly_id,
        transport_receipt_sha256=transport.receipt_sha256,
        cochlear_receipt_sha256=cochlear.receipt_sha256,
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
        cochlear_receipt_sha256=provisional.cochlear_receipt_sha256,
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
    "bind_auditory_stream_settlement",
)
