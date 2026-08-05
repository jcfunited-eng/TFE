"""Two-phase, asynchronous expression-bound provider for clean GLEW experiences.

Preparation verifies one signed native stream per mounted port, enforces its
receipted exact invertible physical-to-kernel map and the single native
relevance field, and runs frozen L0--L4 independently.  Each native L1 gate
closes on its own exact source timestamp.  The canonical union of those
timestamps forms one continuous sparse event sequence: only ports closing at
an event contribute evidence, while every absent topology fiber remains
explicit non-evidence in the SparseMapInjection receipt.

Finalization accepts only an expression whose ordered sparse field events bind
the exact prepared injection receipts and intervals.  Recognition therefore
follows lived evidence; an unrelated, held, resampled, zero-filled, or
precomputed expression cannot seal the experience.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import TYPE_CHECKING, Iterable, Sequence

import pandas as pd

from uf_core.layer0 import SEV, compute_sev_series
from uf_core.layer1 import GateL1State, build_gate_l1_state, segment_gates
from uf_core.layer2 import GateInterpretation, interpret_gates
from uf_core.layer3 import ResonanceResult, compute_resonance
from uf_core.layer4 import DSF, compute_directional_signal, compute_dsf

from .certified_backend import CertifiedBall
from .commit import (
    ApplicabilityState,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    ClosedExperienceSeal,
    EventSupportAuthority,
    GovernedFact,
    L5Applicability,
    L6ScopeAuthority,
    closed_experience_seal_receipt_payload,
    l5_applicability_receipt_payload,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from .event_support import (
    EventSupportEvaluation,
    EventSupportEvaluationStatus,
)
from .experience_origin import ExperienceOriginAuthority
from .expression_modes import ExpressionModeBoundaryResult
from .global_uf import GlobalUFValidationResult
from .expressions import ClosedExperienceFieldExpression
from .field import (
    EvidenceProvenance,
    EvidenceValidity,
    EvidenceValidityState,
    MountedFieldTopology,
    PortTransportEvidence,
    RegimeFact,
    SparseMapInjection,
    ResonanceFact,
    StructuralFactState,
    SupportFloorFact,
    TransportCoordinates19,
    sparse_map_inject,
)
from .l6 import (
    CandidateConstraintProduction,
    CandidateConstraintProductionStatus,
    Fixed42ConstraintStack,
    L6Evaluation,
    L6PredicateInputs,
    canonical_completeness_receipt_payload,
    canonical_row_receipt_payload,
    evaluate_l6,
    exact_rank_receipt,
)
from .physical_l6_tangents import (
    PhysicalL6TangentProduction,
    PhysicalTangentProductionStatus,
)

from .model import (
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .safe_mode import (
    SafeModeEvaluation,
    safe_mode_evaluation_receipt_payload,
)

from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    ResonanceConfirmation,
    ResonanceOperatorAuthority,
    SupportFloor,
    compute_resonance_confirmation,
    compute_support_floor,
)


KERNEL_PROVIDER_ID = "glew.closed_experience.ratified_native_l0_l4.v3"
MISSING_KERNEL_ADAPTER = (
    "a mounted native transduction result is required for every port"
)
NONPOSITIVE_NATIVE_GATE_DURATION = (
    "a native gate closed without a positive interval from the prior "
    "experience boundary; the closure cannot be dropped or assigned invented time"
)
def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _binary64(value: object, field_name: str) -> Fraction:
    try:
        encoded = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ReceiptError(f"{field_name} is not finite binary64") from exc
    if not math.isfinite(encoded):
        raise ReceiptError(f"{field_name} is not finite binary64")
    return Fraction.from_float(encoded)


def _binary_text(value: object, field_name: str) -> str:
    return _fraction_text(_binary64(value, field_name))


def _ball_payload(value: CertifiedBall) -> dict[str, object]:
    return {
        "flint_version": value.flint_version,
        "lower_exponent": value.lower_exponent,
        "lower_mantissa": value.lower_mantissa,
        "python_flint_version": value.python_flint_version,
        "upper_exponent": value.upper_exponent,
        "upper_mantissa": value.upper_mantissa,
        "wheel_sha256": value.wheel_sha256,
        "working_precision_bits": value.working_precision_bits,
    }


def _extend_registry(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("provider requires a mounted receipt registry")
    records = list(registry.records)
    mounted = {record.digest: record.payload for record in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("provider receipt must be nonempty exact bytes")
        digest = receipt_sha256(payload)
        if digest in mounted:
            if mounted[digest] != payload:
                raise ReceiptError("receipt digest collision at provider boundary")
            continue
        records.append(ReceiptRecord(digest, payload))
        mounted[digest] = payload
    return ReceiptRegistry(registry.profile_binding_sha256, tuple(records))


def _verify_registry_extension(
    base: ReceiptRegistry,
    extension: ReceiptRegistry,
) -> None:
    if not isinstance(extension, ReceiptRegistry):
        raise ReceiptError("finalization requires a mounted receipt registry")
    if extension.profile_binding_sha256 != base.profile_binding_sha256:
        raise ReceiptError("finalization registry belongs to another profile")
    for record in base.records:
        if extension.resolve(record.digest, "prepared experience receipt") != record.payload:
            raise ReceiptError("finalization registry altered prepared experience bytes")


def source_evidence_stream_receipt_payload(stream: EvidenceStream) -> bytes:
    """Canonical source-stream bytes bound by native transduction authority."""

    return _canonical_bytes(
        {
            "calibration_receipt_sha256": stream.calibration_receipt_sha256,
            "evidence_id": stream.evidence_id,
            "lane_id": stream.lane_id,
            "physical_unit": stream.physical_unit,
            "port_id": stream.port_id,
            "port_kind": stream.port_kind,
            "profile_binding_sha256": stream.profile_binding_sha256,
            "relevance_receipt_sha256": stream.relevance_receipt_sha256,
            "samples": [
                {
                    "phase_turns": _fraction_text(value.phase_turns),
                    "relevance": _fraction_text(value.relevance),
                    "signal": _fraction_text(value.signal),
                    "source_index": value.source_index,
                    "timestamp": _fraction_text(value.timestamp),
                }
                for value in stream.samples
            ],
            "schema": "glew.provider.source_evidence_stream.v1",
            "source_epoch": stream.source_epoch,
        }
    )


@dataclass(frozen=True, slots=True)
class KernelNativeInputMap:
    """One exact affine physical-field map admitted before frozen L0."""

    map_id: str
    source_min: Fraction
    source_max: Fraction
    field_offset: Fraction
    field_scale: Fraction
    profile_payload: bytes

    def __post_init__(self) -> None:
        require_identifier(self.map_id, "kernel input map id")
        for value, name in (
            (self.source_min, "source minimum"),
            (self.source_max, "source maximum"),
            (self.field_offset, "field offset"),
            (self.field_scale, "field scale"),
        ):
            if not isinstance(value, Fraction):
                raise ReceiptError(f"kernel input map {name} must be exact")
        if self.source_max <= self.source_min:
            raise ReceiptError("kernel input map source interval is empty")
        if (
            not isinstance(self.profile_payload, bytes)
            or not self.profile_payload
        ):
            raise ReceiptError("kernel input map profile must be nonempty bytes")
        if self.field_scale == 0:
            raise ReceiptError("kernel input map is not invertible")
        if (
            self.forward(self.source_min) <= 0
            or self.forward(self.source_max) <= 0
        ):
            raise ReceiptError(
                "kernel input map does not remain positive for L0"
            )

    def forward(self, source: Fraction) -> Fraction:
        if not isinstance(source, Fraction):
            raise ReceiptError("kernel input map source must be exact")
        if not self.source_min <= source <= self.source_max:
            raise ReceiptError("kernel input map source left its calibration")
        return self.field_offset + self.field_scale * source

    def inverse(self, field: Fraction) -> Fraction:
        if not isinstance(field, Fraction):
            raise ReceiptError("kernel input map field must be exact")
        source = (field - self.field_offset) / self.field_scale
        if not self.source_min <= source <= self.source_max:
            raise ReceiptError("kernel input map inverse left its calibration")
        return source

    def receipt_record(self) -> dict[str, object]:
        return {
            "field_offset": _fraction_text(self.field_offset),
            "field_scale": _fraction_text(self.field_scale),
            "forward": "F=field_offset+field_scale*s",
            "inverse": "s=(F-field_offset)/field_scale",
            "map_id": self.map_id,
            "source_max": _fraction_text(self.source_max),
            "source_min": _fraction_text(self.source_min),
        }


SIGNED_UNIT_KERNEL_INPUT_MAP = KernelNativeInputMap(
    map_id="signed-unit-affine-v1",
    source_min=Fraction(-1),
    source_max=Fraction(1),
    field_offset=Fraction(1),
    field_scale=Fraction(1, 2),
    profile_payload=(
        b"guala.live.native_sensory.F_equals_1_plus_s_over_2.v1"
    ),
)


@dataclass(frozen=True, slots=True)
class KernelNativeInputSample:
    """Receipted exact transduction output for one admitted native sample."""

    source_index: int
    timestamp: Fraction
    dimensionless_field: Fraction
    l0_relevance: Fraction

    def __post_init__(self) -> None:
        if (
            isinstance(self.source_index, bool)
            or not isinstance(self.source_index, int)
            or self.source_index < 0
        ):
            raise ReceiptError("kernel-native source index must be nonnegative")
        if not isinstance(self.timestamp, Fraction):
            raise ReceiptError("kernel-native timestamp must be exact Fraction")
        if not isinstance(self.dimensionless_field, Fraction):
            raise ReceiptError("kernel-native field must be exact Fraction")
        if self.dimensionless_field <= 0:
            raise ReceiptError("kernel-native field must remain positive for L0")
        if not isinstance(self.l0_relevance, Fraction):
            raise ReceiptError("kernel-native relevance must be exact Fraction")
        if not 0 <= self.l0_relevance <= 1:
            raise ReceiptError("kernel-native relevance must remain in [0,1]")


def kernel_native_input_receipt_payload(
    *,
    adapter_id: str,
    adapter_profile_receipt_sha256: str,
    lane_id: str,
    port_id: str,
    source_stream_receipt_sha256: str,
    samples: Sequence[KernelNativeInputSample],
    kernel_input_map: KernelNativeInputMap = SIGNED_UNIT_KERNEL_INPUT_MAP,
) -> bytes:
    for value, name in (
        (adapter_id, "kernel adapter id"),
        (lane_id, "kernel adapter lane id"),
        (port_id, "kernel adapter port id"),
    ):
        require_identifier(value, name)
    for value, name in (
        (adapter_profile_receipt_sha256, "kernel adapter profile receipt"),
        (source_stream_receipt_sha256, "kernel adapter source stream receipt"),
    ):
        sha256_digest(value, name)
    if not samples:
        raise ReceiptError("kernel adapter result requires samples")
    if not isinstance(kernel_input_map, KernelNativeInputMap):
        raise ReceiptError("kernel adapter map is not typed")
    if kernel_input_map == SIGNED_UNIT_KERNEL_INPUT_MAP:
        return _canonical_bytes({
            "adapter_id": adapter_id,
            "adapter_profile_receipt_sha256": adapter_profile_receipt_sha256,
            "kernel_input_map": {
                "forward": "F=1+s/2",
                "inverse": "s=2*(F-1)",
                "range": "[1/2,3/2]",
            },
            "lane_id": lane_id,
            "native_relevance_rule": "exact_source_relevance_identity",
            "port_id": port_id,
            "samples": [
                {
                    "dimensionless_field": _fraction_text(value.dimensionless_field),
                    "l0_relevance": _fraction_text(value.l0_relevance),
                    "source_index": value.source_index,
                    "timestamp": _fraction_text(value.timestamp),
                }
                for value in samples
            ],
            "schema": "glew.provider.kernel_native_input_result.v2",
            "source_stream_receipt_sha256": source_stream_receipt_sha256,
        })
    return _canonical_bytes({
        "adapter_id": adapter_id,
        "adapter_profile_receipt_sha256": adapter_profile_receipt_sha256,
        "kernel_input_map": kernel_input_map.receipt_record(),
        "lane_id": lane_id,
        "native_relevance_rule": "exact_source_relevance_identity",
        "port_id": port_id,
        "samples": [
            {
                "dimensionless_field": _fraction_text(value.dimensionless_field),
                "l0_relevance": _fraction_text(value.l0_relevance),
                "source_index": value.source_index,
                "timestamp": _fraction_text(value.timestamp),
            }
            for value in samples
        ],
        "schema": "glew.provider.kernel_native_input_result.v3",
        "source_stream_receipt_sha256": source_stream_receipt_sha256,
    })


@dataclass(frozen=True, slots=True)
class KernelNativeInputStream:
    adapter_id: str
    adapter_profile_receipt_sha256: str
    lane_id: str
    port_id: str
    source_stream_receipt_sha256: str
    samples: tuple[KernelNativeInputSample, ...]
    authority_receipt_sha256: str
    kernel_input_map: KernelNativeInputMap = SIGNED_UNIT_KERNEL_INPUT_MAP

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)

    def __post_init__(self) -> None:
        kernel_native_input_receipt_payload(
            adapter_id=self.adapter_id,
            adapter_profile_receipt_sha256=self.adapter_profile_receipt_sha256,
            lane_id=self.lane_id,
            port_id=self.port_id,
            source_stream_receipt_sha256=self.source_stream_receipt_sha256,
            samples=self.samples,
            kernel_input_map=self.kernel_input_map,
        )
        sha256_digest(self.authority_receipt_sha256, "kernel input authority receipt")

    def verify(self, stream: EvidenceStream, registry: ReceiptRegistry) -> None:
        if self.key != stream.key:
            raise ReceiptError("kernel adapter result belongs to another port")
        profile_payload = registry.resolve(
            self.adapter_profile_receipt_sha256,
            "kernel adapter profile receipt",
        )
        if (
            self.kernel_input_map != SIGNED_UNIT_KERNEL_INPUT_MAP
            and (
                profile_payload != self.kernel_input_map.profile_payload
                or receipt_sha256(profile_payload)
                != self.adapter_profile_receipt_sha256
            )
        ):
            raise ReceiptError("kernel adapter map profile changed")
        expected_source = source_evidence_stream_receipt_payload(stream)
        if receipt_sha256(expected_source) != self.source_stream_receipt_sha256:
            raise ReceiptError("kernel adapter result names different source evidence")
        if len(self.samples) != len(stream.samples):
            raise ReceiptError("kernel adapter changed source sample cardinality")
        for adapted, source in zip(self.samples, stream.samples, strict=True):
            if (
                adapted.source_index != source.source_index
                or adapted.timestamp != source.timestamp
            ):
                raise ReceiptError("kernel adapter changed source order or time")
            expected_field = self.kernel_input_map.forward(source.signal)
            if adapted.dimensionless_field != expected_field:
                raise ReceiptError(
                    "kernel input differs from the ratified exact F=1+s/2 map"
                    if self.kernel_input_map
                    == SIGNED_UNIT_KERNEL_INPUT_MAP
                    else "kernel input differs from its ratified exact map"
                )
            if (
                self.kernel_input_map.inverse(adapted.dimensionless_field)
                != source.signal
            ):
                raise ReceiptError("kernel input fails the ratified exact inverse map")
            if adapted.l0_relevance != source.relevance:
                raise ReceiptError(
                    "kernel relevance differs from the native source relevance"
                )
        expected = kernel_native_input_receipt_payload(
            adapter_id=self.adapter_id,
            adapter_profile_receipt_sha256=self.adapter_profile_receipt_sha256,
            lane_id=self.lane_id,
            port_id=self.port_id,
            source_stream_receipt_sha256=self.source_stream_receipt_sha256,
            samples=self.samples,
            kernel_input_map=self.kernel_input_map,
        )
        mounted = registry.resolve(
            self.authority_receipt_sha256,
            "kernel input authority receipt",
        )
        if mounted != expected or receipt_sha256(expected) != self.authority_receipt_sha256:
            raise ReceiptError("kernel adapter fields differ from mounted authority")


class ProviderStatus(str, Enum):
    READY = "ready"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClosedExperienceProviderUnknown:
    status: ProviderStatus
    missing_authority: str
    reason: str

    def __post_init__(self) -> None:
        if self.status is not ProviderStatus.UNKNOWN:
            raise ReceiptError("unknown provider result must carry UNKNOWN status")
        require_identifier(self.missing_authority, "missing provider authority")
        require_identifier(self.reason, "unknown provider reason")


@dataclass(frozen=True, slots=True)
class L5ApplicabilityRule:
    lane_id: str
    port_id: str
    fact: GovernedFact
    state: ApplicabilityState


def l5_governance_profile_receipt_payload(
    *,
    profile_id: str,
    topology_authority_receipt_sha256: str,
    rules: Sequence[L5ApplicabilityRule],
) -> bytes:
    require_identifier(profile_id, "L5 profile id")
    sha256_digest(topology_authority_receipt_sha256, "L5 topology receipt")
    if not rules:
        raise ReceiptError("L5 governance profile cannot be empty")
    return _canonical_bytes(
        {
            "profile_id": profile_id,
            "rules": [
                {
                    "fact": value.fact.value,
                    "lane_id": value.lane_id,
                    "port_id": value.port_id,
                    "state": value.state.value,
                }
                for value in rules
            ],
            "schema": "glew.provider.l5_governance_profile.v1",
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedL5GovernanceProfile:
    profile_id: str
    topology_authority_receipt_sha256: str
    rules: tuple[L5ApplicabilityRule, ...]
    authority_receipt_sha256: str

    def verify(self, topology: MountedFieldTopology, registry: ReceiptRegistry) -> None:
        if self.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
            raise ReceiptError("L5 governance belongs to another topology")
        expected_keys = tuple(
            (fiber.lane_id, fiber.port_id, fact)
            for fiber in topology.ordered_port_fibers
            for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
        )
        actual_keys = tuple(
            (value.lane_id, value.port_id, value.fact) for value in self.rules
        )
        if actual_keys != expected_keys:
            raise ReceiptError("L5 governance does not exactly cover topology")
        expected = l5_governance_profile_receipt_payload(
            profile_id=self.profile_id,
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            rules=self.rules,
        )
        if registry.resolve(self.authority_receipt_sha256, "L5 governance receipt") != expected:
            raise ReceiptError("L5 governance differs from mounted authority")


@dataclass(frozen=True, slots=True)
class ClosedExperienceEvidenceEvent:
    """One exact causal boundary in the asynchronous native closure union."""

    source_time_start: Fraction
    source_time_end: Fraction
    evidence: tuple[PortTransportEvidence, ...]
    injection: SparseMapInjection

    def __post_init__(self) -> None:
        require_fraction(self.source_time_start, "prepared event source start")
        require_fraction(self.source_time_end, "prepared event source end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("prepared sparse event requires positive source duration")
        if not self.evidence:
            raise ReceiptError("prepared sparse event requires native closing evidence")
        if not all(isinstance(value, PortTransportEvidence) for value in self.evidence):
            raise ReceiptError("prepared sparse event contains untyped evidence")
        if not isinstance(self.injection, SparseMapInjection):
            raise ReceiptError("prepared event requires a sparse MapInject receipt")

    def verify(
        self,
        topology: MountedFieldTopology,
        registry: ReceiptRegistry,
    ) -> None:
        self.injection.verify(topology, registry)
        if self.injection.source_time != self.source_time_end:
            raise ReceiptError(
                "prepared sparse event closure differs from its source boundary"
            )
        expected_receipts = tuple(
            value.evidence_receipt_sha256 for value in self.evidence
        )
        actual_receipts = tuple(
            value.evidence.evidence_receipt_sha256
            for value in self.injection.mapped_fibers
        )
        if actual_receipts != expected_receipts:
            raise ReceiptError(
                "prepared sparse event injection differs from its closing evidence"
            )


def _preparation_receipt_payload(
    *,
    topology_authority_receipt_sha256: str,
    events: Sequence[ClosedExperienceEvidenceEvent],
    source_time_start: Fraction,
    source_time_end: Fraction,
    support_floor_receipt_sha256: str,
    resonance_confirmation_receipt_sha256: str,
) -> bytes:
    sha256_digest(
        topology_authority_receipt_sha256,
        "prepared experience topology receipt",
    )
    sha256_digest(
        support_floor_receipt_sha256,
        "prepared experience support-floor receipt",
    )
    sha256_digest(
        resonance_confirmation_receipt_sha256,
        "prepared experience resonance receipt",
    )
    require_fraction(source_time_start, "prepared experience source start")
    require_fraction(source_time_end, "prepared experience source end")
    if source_time_end <= source_time_start:
        raise ReceiptError("prepared experience requires positive source duration")
    if not events:
        raise ReceiptError("prepared experience requires a sparse event sequence")
    return _canonical_bytes(
        {
            "events": [
                {
                    "evidence_receipt_sha256s": [
                        value.evidence_receipt_sha256 for value in event.evidence
                    ],
                    "sparse_map_injection_receipt_sha256": (
                        event.injection.receipt_sha256
                    ),
                    "source_time_end": _fraction_text(event.source_time_end),
                    "source_time_start": _fraction_text(event.source_time_start),
                }
                for event in events
            ],
            "resonance_confirmation_receipt_sha256": (
                resonance_confirmation_receipt_sha256
            ),
            "schema": "glew.provider.asynchronous_evidence_preparation.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "support_floor_receipt_sha256": support_floor_receipt_sha256,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class ClosedExperienceEvidencePreparation:
    status: ProviderStatus
    topology_authority_receipt_sha256: str
    events: tuple[ClosedExperienceEvidenceEvent, ...]
    source_time_start: Fraction
    source_time_end: Fraction
    support_floor: SupportFloor
    resonance_confirmation: ResonanceConfirmation
    receipt_sha256: str
    receipt_payload: bytes
    receipt_registry: ReceiptRegistry

    @property
    def evidence(self) -> tuple[PortTransportEvidence, ...]:
        return tuple(value for event in self.events for value in event.evidence)

    def verify(
        self,
        topology: MountedFieldTopology,
        registry: ReceiptRegistry,
    ) -> None:
        if self.status is not ProviderStatus.READY:
            raise ReceiptError("evidence preparation is not READY")
        if self.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
            raise ReceiptError("evidence preparation belongs to another topology")
        if not self.events:
            raise ReceiptError("evidence preparation lacks a sparse event sequence")
        expected_start = self.source_time_start
        evidence_receipts: list[str] = []
        for event in self.events:
            if event.source_time_start != expected_start:
                raise ReceiptError(
                    "prepared sparse events are not one continuous source-time chain"
                )
            event.verify(topology, registry)
            evidence_receipts.extend(
                value.evidence_receipt_sha256 for value in event.evidence
            )
            expected_start = event.source_time_end
        if expected_start != self.source_time_end:
            raise ReceiptError(
                "prepared sparse events do not close at the experience boundary"
            )
        if len(set(evidence_receipts)) != len(evidence_receipts):
            raise ReceiptError("prepared sparse events repeat native evidence")

        support_payload = _support_payload(self.support_floor)
        resonance_payload = _resonance_payload(self.resonance_confirmation)
        support_digest = receipt_sha256(support_payload)
        resonance_digest = receipt_sha256(resonance_payload)
        if registry.resolve(
            support_digest,
            "prepared support-floor result receipt",
        ) != support_payload:
            raise ReceiptError("prepared support-floor result differs from receipt")
        if registry.resolve(
            resonance_digest,
            "prepared resonance result receipt",
        ) != resonance_payload:
            raise ReceiptError("prepared resonance result differs from receipt")
        expected_payload = _preparation_receipt_payload(
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            events=self.events,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            support_floor_receipt_sha256=support_digest,
            resonance_confirmation_receipt_sha256=resonance_digest,
        )
        if (
            self.receipt_payload != expected_payload
            or self.receipt_sha256 != receipt_sha256(expected_payload)
        ):
            raise ReceiptError(
                "asynchronous evidence preparation differs from canonical receipt"
            )
        if registry.resolve(
            self.receipt_sha256,
            "asynchronous evidence preparation receipt",
        ) != expected_payload:
            raise ReceiptError(
                "asynchronous evidence preparation differs from mounted receipt"
            )


@dataclass(frozen=True, slots=True)
class SealedClosedExperience:
    """Evidence/expression/recognition seal before downstream authorities exist."""

    status: ProviderStatus
    preparation: ClosedExperienceEvidencePreparation
    expression: ClosedExperienceFieldExpression
    recognition: ExpressionModeBoundaryResult
    closed_experience: ClosedExperienceSeal
    l5_applicability: tuple[L5Applicability, ...]
    receipt_registry: ReceiptRegistry

    @property
    def evidence(self) -> tuple[PortTransportEvidence, ...]:
        return self.preparation.evidence

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.status is not ProviderStatus.READY:
            raise ReceiptError("closed-experience seal is not READY")
        _verify_registry_extension(self.receipt_registry, receipt_registry)
        self.preparation.verify(topology, receipt_registry)
        _verify_expression_binds_preparation(
            preparation=self.preparation,
            topology=topology,
            expression=self.expression,
            recognition=self.recognition,
            structural_time_unit=self.closed_experience.structural_time_unit,
            receipt_registry=receipt_registry,
        )
        self.closed_experience.verify(
            topology=topology,
            recognition=self.recognition,
            evidence=self.evidence,
            receipt_registry=receipt_registry,
        )
        expected_keys = tuple(
            (fiber.lane_id, fiber.port_id, fact)
            for fiber in topology.ordered_port_fibers
            for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
        )
        if tuple(value.key for value in self.l5_applicability) != expected_keys:
            raise ReceiptError("sealed L5 applicability does not cover the topology")
        for value in self.l5_applicability:
            value.verify(
                topology_receipt=topology.authority_receipt_sha256,
                experience_receipt=(
                    self.closed_experience.authority_receipt_sha256
                ),
                receipt_registry=receipt_registry,
            )


@dataclass(frozen=True, slots=True)
class ClosedExperienceProviderBundle:
    status: ProviderStatus
    sealed: SealedClosedExperience
    experience_origin: ExperienceOriginAuthority
    l6_production: PhysicalL6TangentProduction
    l6_evaluation: L6Evaluation
    l6_scope: L6ScopeAuthority
    safe_mode_evaluation: SafeModeEvaluation
    event_support_evaluation: EventSupportEvaluation
    global_uf_result: GlobalUFValidationResult
    receipt_registry: ReceiptRegistry

    @property
    def evidence(self) -> tuple[PortTransportEvidence, ...]:
        return self.sealed.evidence

    @property
    def support_floor(self) -> SupportFloor:
        return self.sealed.preparation.support_floor

    @property
    def resonance_confirmation(self) -> ResonanceConfirmation:
        return self.sealed.preparation.resonance_confirmation

    @property
    def closed_experience(self) -> ClosedExperienceSeal:
        return self.sealed.closed_experience

    @property
    def l5_applicability(self) -> tuple[L5Applicability, ...]:
        return self.sealed.l5_applicability

    @property
    def safe_mode(self) -> BinaryCommitAuthority:
        return self.safe_mode_evaluation.authority

    @property
    def event_support(self) -> EventSupportAuthority:
        return self.event_support_evaluation.authority

    @property
    def global_uf_validation(self) -> BinaryCommitAuthority:
        return self.global_uf_result.authority


@dataclass(frozen=True, slots=True)
class RatifiedNativeL0L4Trace:
    stream: EvidenceStream
    adapter: KernelNativeInputStream
    sev: tuple[SEV, ...]
    l1: tuple[GateL1State, ...]
    l2: tuple[GateInterpretation, ...]
    l3: tuple[ResonanceResult, ...]
    l4: tuple[DSF, ...]
    raw_payload: bytes


def _trace_payload(
    stream: EvidenceStream,
    adapter: KernelNativeInputStream,
    sev: Sequence[SEV],
    l1: Sequence[GateL1State],
    l2: Sequence[GateInterpretation],
    l3: Sequence[ResonanceResult],
    l4: Sequence[DSF],
) -> bytes:
    legacy_map = (
        adapter.kernel_input_map == SIGNED_UNIT_KERNEL_INPUT_MAP
    )
    return _canonical_bytes(
        {
            "adapter_result_receipt_sha256": adapter.authority_receipt_sha256,
            "binary64_receipt_encoding": "exact_Fraction.from_float",
            "kernel_input_map": (
                "F=1+s/2;inverse_s=2*(F-1)"
                if legacy_map
                else adapter.kernel_input_map.receipt_record()
            ),
            "kernel_provider": KERNEL_PROVIDER_ID,
            "lane_id": stream.lane_id,
            "port_id": stream.port_id,
            "L0_SEV": [
                {
                    "F_norm": _binary_text(value.F_norm, "L0.F_norm"),
                    "N": value.N,
                    "dF": _binary_text(value.dF, "L0.dF"),
                    "kappa": _binary_text(value.kappa, "L0.kappa"),
                    "relevance": _binary_text(value.relevance, "L0.relevance"),
                    "sigma": _binary_text(value.sigma, "L0.sigma"),
                }
                for value in sev
            ],
            "L1_GateL1State": [
                {
                    "C_k": value.C_k,
                    "N_gate": value.N_gate,
                    "TVR": [_binary_text(item, "L1.TVR") for item in value.tvr],
                    "delta_g": _binary_text(value.delta_g, "L1.delta_g"),
                    "end_idx": value.gate.end_idx,
                    "projections": [list(item) for item in value.projections],
                    "start_idx": value.gate.start_idx,
                }
                for value in l1
            ],
            "L2_GateInterpretation": [
                {
                    "CV_k": [_binary_text(item, "L2.CV") for item in value.CV_k],
                    "IAS_k": value.IAS_k,
                    "S_k": _binary_text(value.S_k, "L2.S_k"),
                    "U_k": _binary_text(value.U_k, "L2.U_k"),
                    "end_idx": value.gate.end_idx,
                    "regime": value.regime,
                    "start_idx": value.gate.start_idx,
                    "w_k": _binary_text(value.w_k, "L2.w_k"),
                }
                for value in l2
            ],
            "L3_ResonanceResult": [
                {
                    "Hyst_k": value.Hyst_k,
                    "R_k": _binary_text(value.R_k, "L3.R_k"),
                    "URF_k": _binary_text(value.URF_k, "L3.URF_k"),
                    "end_idx": value.gate.end_idx,
                    "g_k": value.g_k,
                    "start_idx": value.gate.start_idx,
                }
                for value in l3
            ],
            "L4_DSF": [
                {
                    name: _binary_text(getattr(value, name), f"L4.{name}")
                    for name in (
                        "D_k",
                        "M_k",
                        "R_rev_k",
                        "U_star_k",
                        "C_k",
                        "P_k",
                        "B_k",
                    )
                }
                for value in l4
            ],
            "native_relevance_rule": "exact_source_relevance_identity",
            "schema": (
                "glew.provider.complete_signed_port_l0_l4_trace.v3"
                if legacy_map
                else "glew.provider.complete_physical_port_l0_l4_trace.v4"
            ),
            "source_stream_receipt_sha256": adapter.source_stream_receipt_sha256,
        }
    )


def _run_kernel(
    stream: EvidenceStream,
    adapter: KernelNativeInputStream,
) -> RatifiedNativeL0L4Trace:
    frame = pd.DataFrame(
        {"field": [float(value.dimensionless_field) for value in adapter.samples]}
    )
    base = compute_sev_series(frame, "field")
    if len(base) != len(adapter.samples):
        raise ReceiptError("frozen L0 changed adapter sample cardinality")
    sev = tuple(
        SEV(
            F_norm=value.F_norm,
            dF=value.dF,
            sigma=value.sigma,
            kappa=value.kappa,
            relevance=float(adapted.l0_relevance),
            N=value.N,
        )
        for value, adapted in zip(base, adapter.samples, strict=True)
    )
    gates = tuple(segment_gates(sev))
    l1 = tuple(build_gate_l1_state(sev, gates))
    l2 = tuple(interpret_gates(sev, gates))
    l3 = tuple(compute_resonance(l2))
    l4 = tuple(compute_dsf(compute_directional_signal(list(l3))))
    if not gates or len({len(gates), len(l1), len(l2), len(l3), len(l4)}) != 1:
        raise ReceiptError("frozen L0-L4 gate trajectory is incomplete")
    for gate, one, two, three, four in zip(gates, l1, l2, l3, l4, strict=True):
        if not (gate == one.gate == two.gate == three.gate == four.gate):
            raise ReceiptError("frozen L0-L4 gate identities diverged")
    raw = _trace_payload(stream, adapter, sev, l1, l2, l3, l4)
    return RatifiedNativeL0L4Trace(
        stream, adapter, sev, l1, l2, l3, l4, raw
    )


def run_ratified_native_l0_l4_trace_typed(
    *,
    stream: EvidenceStream,
    adapter: KernelNativeInputStream,
    receipt_registry: ReceiptRegistry,
) -> RatifiedNativeL0L4Trace:
    """Settle one native port and retain its typed L0-L4 trajectory."""
    if stream.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
        raise ReceiptError("native stream profile binding differs from active registry")
    receipt_registry.resolve(
        stream.calibration_receipt_sha256, "calibration receipt")
    receipt_registry.resolve(
        stream.relevance_receipt_sha256, "relevance receipt")
    adapter.verify(stream, receipt_registry)
    return _run_kernel(stream, adapter)


def run_ratified_native_l0_l4_trace(
    *,
    stream: EvidenceStream,
    adapter: KernelNativeInputStream,
    receipt_registry: ReceiptRegistry,
) -> ReceiptRecord:
    """Compatibility receipt view of the typed canonical L0-L4 trace."""
    trace = run_ratified_native_l0_l4_trace_typed(
        stream=stream,
        adapter=adapter,
        receipt_registry=receipt_registry,
    )
    return ReceiptRecord(
        digest=receipt_sha256(trace.raw_payload),
        payload=trace.raw_payload,
    )


def _support_payload(value: SupportFloor) -> bytes:
    return _canonical_bytes(
        {
            "domain_authority_receipt_sha256": value.domain_authority_receipt_sha256,
            "grid_id": value.grid_id,
            "port_facts": [
                {
                    "port_key": list(item.port_key),
                    "required": item.required,
                    "support_floor": _fraction_text(item.support_floor),
                }
                for item in value.port_facts
            ],
            "schema": "glew.provider.S_UF_result.v1",
            "value": _fraction_text(value.value),
        }
    )


def _resonance_payload(value: ResonanceConfirmation) -> bytes:
    return _canonical_bytes(
        {
            "edge_facts": [
                {
                    "gamma_squared": _ball_payload(item.gamma_squared),
                    "left": list(item.edge.left_port_key),
                    "proved_zero_energy": item.proved_zero_energy,
                    "right": list(item.edge.right_port_key),
                }
                for item in value.edge_facts
            ],
            "graph_authority_receipt_sha256": value.graph_authority_receipt_sha256,
            "operator_authority_receipt_sha256": value.operator_authority_receipt_sha256,
            "schema": "glew.provider.R_UF_result.v1",
            "value": _ball_payload(value.value),
        }
    )


def _coordinates(one, two, three, four) -> TransportCoordinates19:
    return TransportCoordinates19(
        _binary64(one.tvr[0], "TVR_T"),
        _binary64(one.tvr[1], "TVR_V"),
        _binary64(one.tvr[2], "TVR_R"),
        _binary64(two.w_k, "w_k"),
        _binary64(two.CV_k[0], "CV_T"),
        _binary64(two.CV_k[1], "CV_V"),
        _binary64(two.CV_k[2], "CV_R"),
        _binary64(two.S_k, "S_k"),
        _binary64(two.U_k, "U_k"),
        Fraction(two.IAS_k),
        _binary64(three.URF_k, "URF_k"),
        _binary64(four.D_k, "D_k"),
        _binary64(four.M_k, "M_k"),
        _binary64(four.R_rev_k, "R_rev_k"),
        _binary64(four.U_star_k, "U_star_k"),
        _binary64(four.C_k, "C_k"),
        _binary64(four.P_k, "P_k"),
        _binary64(four.B_k, "B_k"),
        Fraction(one.N_gate),
    )


def _fact_payload(
    schema: str,
    trace_digest: str,
    gate_index: int | None = None,
    category: str | None = None,
) -> bytes:
    value: dict[str, object] = {
        "schema": schema,
        "trace_receipt_sha256": trace_digest,
    }
    if gate_index is not None:
        value["gate_index"] = gate_index
    if category is not None:
        value["category"] = category
    return _canonical_bytes(value)


def prepare_closed_experience_evidence(
    *,
    streams: tuple[EvidenceStream, ...],
    kernel_inputs: tuple[KernelNativeInputStream, ...] | None,
    source_time_start: Fraction,
    grid: CausalGrid,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> ClosedExperienceEvidencePreparation | ClosedExperienceProviderUnknown:
    """Produce a receipt-bound asynchronous full-field evidence sequence."""

    require_fraction(source_time_start, "closed-experience source-time start")
    if source_time_start > grid.timestamps[0]:
        raise ReceiptError(
            "closed-experience source-time start cannot follow the first native sample"
        )
    if kernel_inputs is None:
        return ClosedExperienceProviderUnknown(
            ProviderStatus.UNKNOWN,
            "native_transduction",
            MISSING_KERNEL_ADAPTER,
        )
    topology.verify(receipt_registry)
    topology_keys = tuple(value.key for value in topology.ordered_port_fibers)
    topology_positions = {
        key: index for index, key in enumerate(topology_keys)
    }
    stream_map = {value.key: value for value in streams}
    input_map = {value.key: value for value in kernel_inputs}
    if (
        len(stream_map) != len(streams)
        or len(input_map) != len(kernel_inputs)
        or set(stream_map) != set(topology_keys)
        or set(input_map) != set(topology_keys)
    ):
        raise ReceiptError("streams and kernel adapters must exactly cover topology")
    ordered_streams = tuple(stream_map[key] for key in topology_keys)
    ordered_inputs = tuple(input_map[key] for key in topology_keys)
    if len(grid.timestamps) < 2:
        raise ReceiptError("closed experience requires positive source duration")
    for stream, adapted in zip(ordered_streams, ordered_inputs, strict=True):
        if stream.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("evidence stream belongs to another profile")
        receipt_registry.resolve(stream.calibration_receipt_sha256, "calibration receipt")
        receipt_registry.resolve(stream.relevance_receipt_sha256, "relevance receipt")
        if tuple(value.timestamp for value in stream.samples) != grid.timestamps:
            raise ReceiptError("native stream does not match common causal grid")
        adapted.verify(stream, receipt_registry)

    support = compute_support_floor(
        ordered_streams,
        grid,
        support_domain,
        receipt_registry,
    )
    resonance = compute_resonance_confirmation(
        ordered_streams,
        grid,
        resonance_graph,
        resonance_operator,
        receipt_registry,
    )
    traces = tuple(
        _run_kernel(stream, adapted)
        for stream, adapted in zip(ordered_streams, ordered_inputs, strict=True)
    )

    support_payload = _support_payload(support)
    resonance_payload = _resonance_payload(resonance)
    support_digest = receipt_sha256(support_payload)
    resonance_digest = receipt_sha256(resonance_payload)
    support_by_key = {value.port_key: value for value in support.port_facts}
    generated: list[bytes] = [support_payload, resonance_payload]
    for trace in traces:
        generated.append(trace.raw_payload)
        generated.append(
            _fact_payload(
                "glew.provider.valid_trace.v3",
                receipt_sha256(trace.raw_payload),
            )
        )

    closures: dict[
        Fraction,
        list[tuple[int, PortTransportEvidence]],
    ] = {}
    for trace in traces:
        topology_index = topology_positions[trace.stream.key]
        raw = ReceiptRecord(receipt_sha256(trace.raw_payload), trace.raw_payload)
        valid_payload = _fact_payload(
            "glew.provider.valid_trace.v3",
            raw.digest,
        )
        for gate_index, (one, two, three, four) in enumerate(
            zip(trace.l1, trace.l2, trace.l3, trace.l4, strict=True)
        ):
            regime_payload = _fact_payload(
                "glew.provider.Reg_k.v3",
                raw.digest,
                gate_index,
                two.regime,
            )
            provenance_payload = _fact_payload(
                "glew.provider.gate_provenance.v3",
                raw.digest,
                gate_index,
            )
            end_sample = trace.stream.samples[four.gate.end_idx]
            value = PortTransportEvidence(
                lane_id=trace.stream.lane_id,
                port_id=trace.stream.port_id,
                evidence_id=f"{trace.stream.evidence_id}:gate:{gate_index}",
                coordinates=_coordinates(one, two, three, four),
                regime=RegimeFact(two.regime, receipt_sha256(regime_payload)),
                support_floor=SupportFloorFact(
                    StructuralFactState.AVAILABLE,
                    support_by_key[trace.stream.key].support_floor,
                    support_digest,
                ),
                resonance=ResonanceFact(
                    StructuralFactState.AVAILABLE,
                    resonance.value,
                    resonance_digest,
                ),
                validity=EvidenceValidity(
                    EvidenceValidityState.VALID,
                    receipt_sha256(valid_payload),
                ),
                provenance=EvidenceProvenance(
                    KERNEL_PROVIDER_ID,
                    trace.stream.source_epoch,
                    end_sample.source_index,
                    end_sample.timestamp,
                    receipt_sha256(provenance_payload),
                ),
                raw_record=raw,
                evidence_receipt_sha256="0" * 64,
            )
            evidence_payload = value.canonical_receipt_payload()
            value = replace(
                value,
                evidence_receipt_sha256=receipt_sha256(evidence_payload),
            )
            generated.extend(
                (regime_payload, provenance_payload, evidence_payload)
            )
            closures.setdefault(end_sample.timestamp, []).append(
                (topology_index, value)
            )

    if not closures:
        raise ReceiptError("frozen L0-L4 produced no native gate closures")
    closure_times = tuple(sorted(closures))
    if closure_times[-1] != grid.timestamps[-1]:
        raise ReceiptError(
            "native gate union does not close at the causal-grid boundary"
        )

    previous_boundary = source_time_start
    for closure_time in closure_times:
        if closure_time <= previous_boundary:
            return ClosedExperienceProviderUnknown(
                ProviderStatus.UNKNOWN,
                "positive_native_gate_duration",
                NONPOSITIVE_NATIVE_GATE_DURATION,
            )
        previous_boundary = closure_time

    evidence_registry = _extend_registry(receipt_registry, generated)
    events: list[ClosedExperienceEvidenceEvent] = []
    injection_payloads: list[bytes] = []
    previous_boundary = source_time_start
    for closure_time in closure_times:
        ordered_evidence = tuple(
            evidence
            for _, evidence in sorted(
                closures[closure_time],
                key=lambda value: value[0],
            )
        )
        injection = sparse_map_inject(
            topology,
            ordered_evidence,
            closure_time,
            evidence_registry,
        )
        events.append(
            ClosedExperienceEvidenceEvent(
                source_time_start=previous_boundary,
                source_time_end=closure_time,
                evidence=ordered_evidence,
                injection=injection,
            )
        )
        injection_payloads.append(injection.receipt_payload)
        previous_boundary = closure_time

    injection_registry = _extend_registry(
        evidence_registry,
        injection_payloads,
    )
    preparation_payload = _preparation_receipt_payload(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        events=events,
        source_time_start=source_time_start,
        source_time_end=closure_times[-1],
        support_floor_receipt_sha256=support_digest,
        resonance_confirmation_receipt_sha256=resonance_digest,
    )
    final_registry = _extend_registry(
        injection_registry,
        (preparation_payload,),
    )
    result = ClosedExperienceEvidencePreparation(
        status=ProviderStatus.READY,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        events=tuple(events),
        source_time_start=source_time_start,
        source_time_end=closure_times[-1],
        support_floor=support,
        resonance_confirmation=resonance,
        receipt_sha256=receipt_sha256(preparation_payload),
        receipt_payload=preparation_payload,
        receipt_registry=final_registry,
    )
    result.verify(topology, final_registry)
    return result


def _l5_values(
    profile: MountedL5GovernanceProfile,
    topology: MountedFieldTopology,
    experience_receipt: str,
) -> tuple[tuple[L5Applicability, ...], tuple[bytes, ...]]:
    values = []
    payloads = []
    for index, rule in enumerate(profile.rules):
        authority_id = f"{profile.profile_id}:{index}:{rule.fact.value}"
        payload = l5_applicability_receipt_payload(
            authority_id=authority_id,
            lane_id=rule.lane_id,
            port_id=rule.port_id,
            fact=rule.fact,
            state=rule.state,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=experience_receipt,
            source_governance_receipt_sha256=profile.authority_receipt_sha256,
        )
        values.append(
            L5Applicability(
                authority_id,
                rule.lane_id,
                rule.port_id,
                rule.fact,
                rule.state,
                topology.authority_receipt_sha256,
                experience_receipt,
                profile.authority_receipt_sha256,
                receipt_sha256(payload),
            )
        )
        payloads.append(payload)
    return tuple(values), tuple(payloads)


def _verify_expression_binds_preparation(
    *,
    preparation: ClosedExperienceEvidencePreparation,
    topology: MountedFieldTopology,
    expression: ClosedExperienceFieldExpression,
    recognition: ExpressionModeBoundaryResult,
    structural_time_unit: str,
    receipt_registry: ReceiptRegistry,
) -> None:
    preparation.verify(topology, receipt_registry)
    expression.verify(receipt_registry)
    recognition.verify()
    recognition.pre_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    recognition.post_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    if receipt_registry.resolve(
        expression.receipt_sha256,
        "closed input-expression receipt",
    ) != expression.receipt_payload:
        raise ReceiptError("input expression differs from mounted receipt")
    if receipt_registry.resolve(
        recognition.receipt_sha256,
        "expression recognition receipt",
    ) != recognition.receipt_payload:
        raise ReceiptError("expression recognition differs from mounted receipt")
    if recognition.input_expression_receipt_sha256 != expression.receipt_sha256:
        raise ReceiptError("recognition names a different input expression")
    if expression.topology_authority_receipt_sha256 != (
        preparation.topology_authority_receipt_sha256
    ):
        raise ReceiptError("input expression belongs to another prepared topology")
    if len(expression.steps) != len(preparation.events):
        raise ReceiptError(
            "input expression step count differs from prepared sparse events"
        )
    if expression.initial_state.source_time != preparation.source_time_start:
        raise ReceiptError("input expression starts outside the prepared experience")

    for index, (step, event) in enumerate(
        zip(expression.steps, preparation.events, strict=True)
    ):
        if not isinstance(step.injection, SparseMapInjection):
            raise ReceiptError(
                f"input expression event {index} is not a sparse native closure"
            )
        step.injection.verify(topology, receipt_registry)
        if (
            step.injection.receipt_sha256 != event.injection.receipt_sha256
            or step.injection.receipt_payload != event.injection.receipt_payload
        ):
            raise ReceiptError(
                f"input expression event {index} does not bind prepared injection"
            )
        actual_receipts = tuple(
            value.evidence.evidence_receipt_sha256
            for value in step.injection.mapped_fibers
        )
        expected_receipts = tuple(
            value.evidence_receipt_sha256 for value in event.evidence
        )
        if actual_receipts != expected_receipts:
            raise ReceiptError(
                f"input expression event {index} does not bind prepared evidence"
            )
        if (
            step.authority.source_time_start,
            step.authority.source_time_end,
        ) != (event.source_time_start, event.source_time_end):
            raise ReceiptError(
                f"input expression event {index} differs from prepared source time"
            )
        if step.authority.source_time_unit != structural_time_unit:
            raise ReceiptError(
                f"input expression event {index} uses another structural time unit"
            )
    if expression.steps[-1].authority.source_time_end != preparation.source_time_end:
        raise ReceiptError("input expression does not close the prepared experience")


def seal_closed_experience(
    *,
    experience_id: str,
    structural_time_unit: str,
    preparation: ClosedExperienceEvidencePreparation,
    topology: MountedFieldTopology,
    l5_governance: MountedL5GovernanceProfile,
    expression: ClosedExperienceFieldExpression,
    recognition: ExpressionModeBoundaryResult,
    receipt_registry: ReceiptRegistry,
) -> SealedClosedExperience:
    """Seal lived evidence and its exact expression before authority assembly."""

    require_identifier(experience_id, "experience id")
    require_identifier(structural_time_unit, "structural time unit")
    if not isinstance(preparation, ClosedExperienceEvidencePreparation):
        raise ReceiptError("sealing requires prepared full-field evidence")
    if not isinstance(expression, ClosedExperienceFieldExpression):
        raise ReceiptError("sealing requires a closed field expression")
    if not isinstance(recognition, ExpressionModeBoundaryResult):
        raise ReceiptError("sealing requires direct expression recognition")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("sealing requires a mounted receipt registry")
    _verify_registry_extension(preparation.receipt_registry, receipt_registry)
    topology.verify(receipt_registry)
    l5_governance.verify(topology, receipt_registry)
    _verify_expression_binds_preparation(
        preparation=preparation,
        topology=topology,
        expression=expression,
        recognition=recognition,
        structural_time_unit=structural_time_unit,
        receipt_registry=receipt_registry,
    )

    evidence = preparation.evidence
    evidence_receipts = tuple(
        value.evidence_receipt_sha256 for value in evidence
    )
    seal_payload = closed_experience_seal_receipt_payload(
        experience_id=experience_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=expression.receipt_sha256,
        recognition_receipt_sha256=recognition.receipt_sha256,
        ordered_evidence_receipt_sha256s=evidence_receipts,
        source_time_start=preparation.source_time_start,
        source_time_end=preparation.source_time_end,
        structural_time_unit=structural_time_unit,
    )
    seal = ClosedExperienceSeal(
        experience_id,
        topology.authority_receipt_sha256,
        expression.receipt_sha256,
        recognition.receipt_sha256,
        evidence_receipts,
        preparation.source_time_start,
        preparation.source_time_end,
        structural_time_unit,
        receipt_sha256(seal_payload),
    )
    seal_registry = _extend_registry(receipt_registry, (seal_payload,))
    seal.verify(
        topology=topology,
        recognition=recognition,
        evidence=evidence,
        receipt_registry=seal_registry,
    )
    applicability, applicability_payloads = _l5_values(
        l5_governance,
        topology,
        seal.authority_receipt_sha256,
    )
    final_registry = _extend_registry(seal_registry, applicability_payloads)
    result = SealedClosedExperience(
        status=ProviderStatus.READY,
        preparation=preparation,
        expression=expression,
        recognition=recognition,
        closed_experience=seal,
        l5_applicability=applicability,
        receipt_registry=final_registry,
    )
    result.verify(topology=topology, receipt_registry=final_registry)
    return result


def _canonical_receipt_object(payload: bytes, description: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{description} must be nonempty exact bytes")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{description} is not canonical JSON") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise ReceiptError(f"{description} is not canonical JSON")
    return value


def _unknown_authority(name: str, reason: str) -> ClosedExperienceProviderUnknown:
    return ClosedExperienceProviderUnknown(
        status=ProviderStatus.UNKNOWN,
        missing_authority=name,
        reason=reason,
    )


def _verify_safe_mode_result(
    *,
    evaluation: SafeModeEvaluation,
    topology_receipt: str,
    experience_receipt: str,
    receipt_registry: ReceiptRegistry,
) -> ReceiptRegistry:
    evaluation.verify()
    source = _canonical_receipt_object(
        evaluation.source_receipt_payload,
        "SafeMode evaluation source receipt",
    )
    scope_receipt = source.get("scope_authority_receipt_sha256")
    if not isinstance(scope_receipt, str):
        raise ReceiptError("SafeMode source lacks its scope authority receipt")
    expected_source = safe_mode_evaluation_receipt_payload(
        scope_authority_receipt_sha256=scope_receipt,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        ordered_fact_receipt_sha256s=(
            evaluation.ordered_fact_receipt_sha256s
        ),
        disposition=evaluation.disposition,
        reason=evaluation.reason,
    )
    if (
        expected_source != evaluation.source_receipt_payload
        or receipt_sha256(expected_source) != evaluation.source_receipt_sha256
    ):
        raise ReceiptError("SafeMode evaluation is not bound to this closed experience")
    receipt_registry.resolve(scope_receipt, "SafeMode scope authority receipt")
    for digest in evaluation.ordered_fact_receipt_sha256s:
        receipt_registry.resolve(digest, "SafeMode integrity fact receipt")
    mounted = _extend_registry(
        receipt_registry,
        evaluation.generated_receipt_payloads,
    )
    evaluation.authority.verify(
        expected_kind=BinaryAuthorityKind.SAFE_MODE_CLEAR,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=mounted,
    )
    return mounted


def _verify_event_support_result(
    *,
    evaluation: EventSupportEvaluation,
    origin: ExperienceOriginAuthority,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> ReceiptRegistry:
    if evaluation.status is not EventSupportEvaluationStatus.RESOLVED:
        raise ReceiptError("R_event producer did not resolve physical event support")
    if evaluation.exact_r_event is None:
        raise ReceiptError("resolved R_event evaluation lacks an exact value")
    mounted = _extend_registry(
        receipt_registry,
        evaluation.generated_receipt_payloads,
    )
    evaluation.verify(
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=(
            sealed.closed_experience.authority_receipt_sha256
        ),
        expression=sealed.expression,
        receipt_registry=mounted,
    )
    return mounted
def _merge_global_uf_result(
    *,
    result: GlobalUFValidationResult,
    sealed: SealedClosedExperience,
    topology_receipt: str,
    experience_receipt: str,
    receipt_registry: ReceiptRegistry,
) -> ReceiptRegistry:
    _verify_registry_extension(sealed.receipt_registry, result.receipt_registry)
    result.verify()
    if (
        result.source_receipt.topology_authority_receipt_sha256
        != topology_receipt
        or result.source_receipt.closed_experience_receipt_sha256
        != experience_receipt
    ):
        raise ReceiptError("global-UF result belongs to another closed experience")
    mounted = _extend_registry(
        receipt_registry,
        (record.payload for record in result.receipt_registry.records),
    )
    result.source_receipt.verify(mounted)
    result.authority.verify(
        expected_kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=mounted,
    )
    return mounted


def _mount_physical_l6_production(
    *,
    production: PhysicalL6TangentProduction,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> tuple[ReceiptRegistry, CandidateConstraintProduction]:
    if production.status is not PhysicalTangentProductionStatus.KNOWN:
        raise ReceiptError("physical L6 tangent production is unresolved")
    candidate = production.candidate_constraints
    if not isinstance(candidate, CandidateConstraintProduction):
        raise ReceiptError("physical L6 production lacks exact candidate constraints")
    if candidate.status is not CandidateConstraintProductionStatus.KNOWN:
        raise ReceiptError("physical L6 candidate constraint production is unresolved")
    if not isinstance(candidate.stack, Fixed42ConstraintStack):
        raise ReceiptError("physical L6 production lacks an exact constraint stack")
    if production.rank_receipt != exact_rank_receipt(candidate.stack):
        raise ReceiptError("physical L6 rank receipt differs from the exact stack")
    _verify_registry_extension(
        sealed.receipt_registry,
        production.receipt_registry,
    )
    _verify_registry_extension(production.receipt_registry, receipt_registry)

    topology_keys = {
        (fiber.lane_id, fiber.port_id)
        for fiber in topology.ordered_port_fibers
    }
    derived_identities = tuple(
        (
            value.profile.lane,
            value.profile.provider_id,
            value.profile.native_port_id,
        )
        for value in production.derived_ports
    )
    candidate_identities = tuple(
        (
            value.lane,
            value.provider_id,
            value.native_port_id,
        )
        for value in candidate.provider_sets
    )
    if derived_identities != candidate_identities:
        raise ReceiptError("physical tangent provenance differs from constraint production")
    for derived in production.derived_ports:
        profile = derived.profile
        if (profile.lane.value, profile.native_port_id) not in topology_keys:
            raise ReceiptError("physical L6 tangent belongs to another topology")
        if (
            derived.claim.lane is not profile.lane
            or derived.claim.provider_id != profile.provider_id
            or derived.claim.native_port_id != profile.native_port_id
            or derived.claim.tangent != derived.tangent
        ):
            raise ReceiptError("physical L6 tangent lost its native replay provenance")
        receipt_registry.resolve(
            profile.authority_receipt_sha256,
            "physical L6 perturbation profile receipt",
        )
        receipt_registry.resolve(
            derived.response_set.authority_receipt_sha256,
            "physical L6 native response-set receipt",
        )
        receipt_registry.resolve(
            derived.branch_cell_proof.authority_receipt_sha256,
            "physical L6 same-branch/cell proof receipt",
        )
        receipt_registry.resolve(
            derived.derivation_receipt_sha256,
            "physical L6 tangent derivation receipt",
        )

    produced_rows = []
    row_payloads = []
    for provider_set in candidate.provider_sets:
        if (provider_set.lane.value, provider_set.native_port_id) not in topology_keys:
            raise ReceiptError("physical L6 provider set belongs to another topology")
        receipt_registry.resolve(
            provider_set.branch_cell_receipt_sha256,
            "physical L6 translated same-branch/cell receipt",
        )
        receipt_registry.resolve(
            provider_set.tangent_receipt_sha256,
            "physical L6 translated response-tangent receipt",
        )
        if len(provider_set.rows) != len(provider_set.row_receipt_payloads):
            raise ReceiptError("physical L6 provider row receipts are incomplete")
        for row, payload in zip(
            provider_set.rows,
            provider_set.row_receipt_payloads,
            strict=True,
        ):
            if (
                row.provenance.lane is not provider_set.lane
                or row.provenance.provider_id != provider_set.provider_id
                or row.provenance.native_port_id != provider_set.native_port_id
            ):
                raise ReceiptError("physical L6 row provenance changed provider scope")
            expected = canonical_row_receipt_payload(
                lane=row.provenance.lane,
                provider_id=row.provenance.provider_id,
                native_port_id=row.provenance.native_port_id,
                operator_id=row.provenance.operator_id,
                row_id=row.provenance.row_id,
                coefficients=row.native_coefficients,
            )
            if (
                payload != expected
                or receipt_sha256(expected) != row.provenance.receipt_sha256
                or receipt_registry.resolve(
                    row.provenance.receipt_sha256,
                    "physical L6 row receipt",
                )
                != expected
            ):
                raise ReceiptError("physical L6 row differs from exact producer receipt")
            produced_rows.append(row)
            row_payloads.append(payload)
    if tuple(produced_rows) != candidate.stack.rows:
        raise ReceiptError("physical L6 stack differs from provider row production")

    completeness_lanes = tuple(
        value.lane for value in production.lane_completeness_receipts
    )
    expected_lanes = tuple(
        dict.fromkeys(value.profile.lane for value in production.derived_ports)
    )
    if completeness_lanes != expected_lanes:
        raise ReceiptError("physical L6 completeness receipts changed active lanes")
    for completeness in production.lane_completeness_receipts:
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in candidate.stack.rows
            if row.provenance.lane is completeness.lane
        )
        expected = canonical_completeness_receipt_payload(
            lane=completeness.lane,
            row_receipt_sha256s=row_digests,
        )
        if (
            completeness.receipt_payload != expected
            or completeness.receipt_sha256 != receipt_sha256(expected)
            or receipt_registry.resolve(
                completeness.receipt_sha256,
                "physical L6 lane completeness receipt",
            )
            != expected
        ):
            raise ReceiptError("physical L6 completeness receipt is inconsistent")
    return _extend_registry(receipt_registry, row_payloads), candidate


def assemble_closed_experience_provider_bundle(
    *,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    experience_origin: ExperienceOriginAuthority | None,
    safe_mode_evaluation: SafeModeEvaluation | None,
    event_support_evaluation: EventSupportEvaluation | None,
    global_uf_validation: GlobalUFValidationResult | None,
    l6_production: PhysicalL6TangentProduction | None,
    l6_predicates: L6PredicateInputs | None,
    l6_evaluation: L6Evaluation | None,
    l6_scope: L6ScopeAuthority | None,
    receipt_registry: ReceiptRegistry | None,
) -> ClosedExperienceProviderBundle | ClosedExperienceProviderUnknown:
    """Assemble only actual authorities already produced for the exact seal."""

    missing = (
        (
            experience_origin,
            ExperienceOriginAuthority,
            "experience_origin",
        ),
        (safe_mode_evaluation, SafeModeEvaluation, "safe_mode_evaluation"),
        (
            event_support_evaluation,
            EventSupportEvaluation,
            "event_support_evaluation",
        ),
        (
            global_uf_validation,
            GlobalUFValidationResult,
            "global_uf_validation",
        ),
        (
            l6_production,
            PhysicalL6TangentProduction,
            "physical_l6_production",
        ),
        (l6_predicates, L6PredicateInputs, "physical_l6_predicates"),
        (l6_evaluation, L6Evaluation, "physical_l6_evaluation"),
        (l6_scope, L6ScopeAuthority, "physical_l6_scope"),
        (receipt_registry, ReceiptRegistry, "authority_receipt_registry"),
    )
    for value, expected_type, name in missing:
        if not isinstance(value, expected_type):
            return _unknown_authority(
                name,
                f"actual {name.replace('_', ' ')} was not supplied",
            )
    if event_support_evaluation.status is not EventSupportEvaluationStatus.RESOLVED:
        return _unknown_authority(
            "event_support_evaluation",
            event_support_evaluation.reason,
        )
    if (
        isinstance(l6_production, PhysicalL6TangentProduction)
        and l6_production.status is not PhysicalTangentProductionStatus.KNOWN
    ):
        return _unknown_authority(
            "physical_l6_production",
            l6_production.reason,
        )
    if not isinstance(sealed, SealedClosedExperience):
        raise ReceiptError("authority assembly requires a sealed closed experience")
    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("authority assembly requires the mounted topology")

    _verify_registry_extension(sealed.receipt_registry, receipt_registry)
    topology.verify(receipt_registry)
    sealed.verify(topology=topology, receipt_registry=receipt_registry)
    topology_receipt = topology.authority_receipt_sha256
    experience_receipt = sealed.closed_experience.authority_receipt_sha256
    experience_origin.verify(receipt_registry)
    if (
        experience_origin.topology_authority_receipt_sha256
        != topology_receipt
        or experience_origin.closed_experience_receipt_sha256
        != experience_receipt
    ):
        raise ReceiptError("experience origin belongs to another sealed field")

    working = _verify_safe_mode_result(
        evaluation=safe_mode_evaluation,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    working = _verify_event_support_result(
        evaluation=event_support_evaluation,
        origin=experience_origin,
        sealed=sealed,
        topology=topology,
        receipt_registry=working,
    )
    working = _merge_global_uf_result(
        result=global_uf_validation,
        sealed=sealed,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=working,
    )
    working, candidate_constraints = _mount_physical_l6_production(
        production=l6_production,
        sealed=sealed,
        topology=topology,
        receipt_registry=working,
    )
    l6_stack = candidate_constraints.stack
    recomputed_l6 = evaluate_l6(
        l6_stack,
        l6_predicates,
        working,
    )
    if recomputed_l6 != l6_evaluation:
        raise ReceiptError("supplied L6 evaluation differs from exact physical production")
    evaluation_payload = l6_evaluation_receipt_payload(l6_evaluation)
    scope_payload = l6_scope_authority_receipt_payload(
        authority_id=l6_scope.authority_id,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        l6_evaluation_receipt_sha256=receipt_sha256(evaluation_payload),
    )
    if receipt_sha256(scope_payload) != l6_scope.authority_receipt_sha256:
        raise ReceiptError("L6 scope receipt differs from supplied physical scope")
    working = _extend_registry(working, (evaluation_payload, scope_payload))
    l6_scope.verify(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        evaluation=l6_evaluation,
        receipt_registry=working,
    )
    sealed.verify(topology=topology, receipt_registry=working)

    return ClosedExperienceProviderBundle(
        status=ProviderStatus.READY,
        sealed=sealed,
        experience_origin=experience_origin,
        l6_production=l6_production,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        safe_mode_evaluation=safe_mode_evaluation,
        event_support_evaluation=event_support_evaluation,
        global_uf_result=global_uf_validation,
        receipt_registry=working,
    )


__all__ = (
    "ClosedExperienceEvidenceEvent",
    "ClosedExperienceEvidencePreparation",
    "ClosedExperienceProviderBundle",
    "ClosedExperienceProviderUnknown",
    "KERNEL_PROVIDER_ID",
    "KernelNativeInputMap",
    "KernelNativeInputSample",
    "KernelNativeInputStream",
    "L5ApplicabilityRule",
    "MISSING_KERNEL_ADAPTER",
    "MountedL5GovernanceProfile",
    "NONPOSITIVE_NATIVE_GATE_DURATION",
    "ProviderStatus",
    "SIGNED_UNIT_KERNEL_INPUT_MAP",
    "SealedClosedExperience",
    "assemble_closed_experience_provider_bundle",
    "kernel_native_input_receipt_payload",
    "l5_governance_profile_receipt_payload",
    "prepare_closed_experience_evidence",
    "run_ratified_native_l0_l4_trace",
    "seal_closed_experience",
    "source_evidence_stream_receipt_payload",
)
