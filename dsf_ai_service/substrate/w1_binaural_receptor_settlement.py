"""Typed two-ear receptor settlement at the raw W1 pressure boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    AuditoryReceptorFullFieldEvent,
    settle_w1_ear_receptor_event,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryReceptorExperience,
    receptor_experience_from_full_field_event,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    VerifiedCausalSettlementCapability,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    W1EarAuditoryTransductionCustody,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    EAR_IDS,
    W1BinauralAuditoryL5Experience,
)


W1_BINAURAL_RECEPTOR_SETTLEMENT_SCHEMA = (
    "guala.w1.binaural_receptor_settlement.v1"
)
W1_EAR_RECEPTOR_SETTLEMENT_SCHEMA = (
    "guala.w1.ear_receptor_settlement.v1"
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


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class W1EarReceptorSettlement:
    ear_id: str
    source_pcm_sha256: str
    capture_receipt_sha256: str
    event: AuditoryReceptorFullFieldEvent
    experience: AuditoryReceptorExperience

    def payload(self) -> dict[str, object]:
        return {
            "capture_receipt_sha256": self.capture_receipt_sha256,
            "ear_id": self.ear_id,
            "event_receipt_sha256": self.event.authority_receipt_sha256,
            "experience_receipt_sha256": (
                self.experience.authority_receipt_sha256
            ),
            "schema": W1_EAR_RECEPTOR_SETTLEMENT_SCHEMA,
            "source_pcm_sha256": self.source_pcm_sha256,
        }

    def verify(self) -> None:
        self.event.verify()
        self.experience.verify()
        self._verify_linkage()

    def _verify_linkage(self) -> None:
        """Verify local links after the event and experience verified once."""
        if (
            self.ear_id not in EAR_IDS
            or self.capture_receipt_sha256
            != self.event.capture_receipt_sha256
            or self.experience.source_event_receipt_sha256
            != self.event.authority_receipt_sha256
        ):
            raise ValueError("W1 ear receptor settlement changed")


@dataclass(frozen=True, slots=True)
class W1BinauralReceptorSettlement:
    assembly_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    upstream_causal_settlement_receipt_sha256: str
    upstream_w1_l5: W1BinauralAuditoryL5Experience
    ears: tuple[W1EarReceptorSettlement, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "ears": [value.payload() for value in self.ears],
            "schema": W1_BINAURAL_RECEPTOR_SETTLEMENT_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "upstream_causal_settlement_receipt_sha256": (
                self.upstream_causal_settlement_receipt_sha256
            ),
            "upstream_w1_l5_authority_receipt_sha256": (
                self.upstream_w1_l5.authority_receipt_sha256
            ),
        }

    def verify(self) -> None:
        self.upstream_w1_l5.verify()
        for value in self.ears:
            value.verify()
        self._verify_linkage()

    def _verify_linkage(self) -> None:
        """Verify assembly links under exact request-local object custody."""
        for value in self.ears:
            value._verify_linkage()
        if (
            self.assembly_id != self.upstream_w1_l5.assembly_id
            or self.source_time_start
            != self.upstream_w1_l5.source_time_start
            or self.source_time_end != self.upstream_w1_l5.source_time_end
            or self.upstream_causal_settlement_receipt_sha256
            != (
                self.upstream_w1_l5
                .upstream_causal_settlement_receipt_sha256
            )
            or tuple(value.ear_id for value in self.ears) != EAR_IDS
            or any(
                value.event.auditory_l5_authority_receipt_sha256
                != self.upstream_w1_l5.authority_receipt_sha256
                for value in self.ears
            )
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError("W1 binaural receptor settlement changed")

    def authority_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def settle_w1_binaural_receptors(
    *,
    left_custody: W1EarAuditoryTransductionCustody,
    right_custody: W1EarAuditoryTransductionCustody,
    causal_settlement: CausalExperienceSettlement,
    w1_l5: W1BinauralAuditoryL5Experience,
    verified_capability: (
        VerifiedCausalSettlementCapability | None
    ) = None,
) -> W1BinauralReceptorSettlement:
    """Settle both ears before the transient W1 PCM is released."""

    if verified_capability is None:
        causal_settlement.verify()
    else:
        verified_capability.verify_linkage(causal_settlement)
    w1_l5.verify()
    if (
        w1_l5.assembly_id != causal_settlement.assembly_id
        or w1_l5.upstream_causal_settlement_receipt_sha256
        != causal_settlement.authority_receipt_sha256
        or not isinstance(
            left_custody,
            W1EarAuditoryTransductionCustody,
        )
        or not isinstance(
            right_custody,
            W1EarAuditoryTransductionCustody,
        )
    ):
        raise ValueError("W1 receptor settlement upstream authority changed")
    custodies = (left_custody, right_custody)
    for ear_id, custody in zip(EAR_IDS, custodies, strict=True):
        custody.verify()
        expected_end = custody.source_time_start + Fraction(
            custody.capture.input_sample_count,
            custody.capture.source_sample_rate_hz,
        )
        if (
            custody.ear_id != ear_id
            or custody.source_time_start != w1_l5.source_time_start
            or expected_end != w1_l5.source_time_end
        ):
            raise ValueError("W1 receptor transduction custody changed")
    ears = []
    for ear_id, custody, ear in zip(
        EAR_IDS,
        custodies,
        w1_l5.ears,
        strict=True,
    ):
        result = settle_w1_ear_receptor_event(
            capture=custody.capture,
            mounted_component_inputs=custody.component_inputs,
            ear_id=ear_id,
            source_time_start=w1_l5.source_time_start,
            pressure_components=tuple(
                value.pressure for value in ear.channels
            ),
            phase_components=tuple(
                value.carrier_phase_advance for value in ear.channels
            ),
            w1_l5_authority_receipt_sha256=(
                w1_l5.authority_receipt_sha256
            ),
            w1_l5_experience_id=w1_l5.experience_id,
        )
        if (
            result.state is not AuditoryReceptorEventState.OBSERVED
            or result.event is None
            or result.verified_capability is None
        ):
            raise ValueError(
                f"W1 {ear_id} receptor settlement failed: {result.reason}"
            )
        experience = receptor_experience_from_full_field_event(
            result.event,
            verified_capability=result.verified_capability,
        )
        ear_settlement = W1EarReceptorSettlement(
            ear_id=ear_id,
            source_pcm_sha256=custody.source_pcm_sha256,
            capture_receipt_sha256=result.event.capture_receipt_sha256,
            event=result.event,
            experience=experience,
        )
        ear_settlement._verify_linkage()
        ears.append(ear_settlement)
    provisional = W1BinauralReceptorSettlement(
        assembly_id=w1_l5.assembly_id,
        source_time_start=w1_l5.source_time_start,
        source_time_end=w1_l5.source_time_end,
        upstream_causal_settlement_receipt_sha256=(
            causal_settlement.authority_receipt_sha256
        ),
        upstream_w1_l5=w1_l5,
        ears=tuple(ears),
        authority_receipt_sha256="0" * 64,
    )
    result = W1BinauralReceptorSettlement(
        assembly_id=provisional.assembly_id,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        upstream_causal_settlement_receipt_sha256=(
            provisional.upstream_causal_settlement_receipt_sha256
        ),
        upstream_w1_l5=provisional.upstream_w1_l5,
        ears=provisional.ears,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result._verify_linkage()
    return result


__all__ = [
    "W1BinauralReceptorSettlement",
    "W1EarReceptorSettlement",
    "settle_w1_binaural_receptors",
]
