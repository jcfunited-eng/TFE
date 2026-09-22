"""Mount authoritative causal support for every auditory L4 tuple.

The frozen L0--L4 trace receipts already contain the inclusive observation
indices behind each L4 gate. The auditory provider defines every observation
as one completed 10 ms cochlear hop. This module binds each exact L4 tuple to
the corresponding contiguous hop interval without rerunning or changing the
kernel.

Support objects are not standalone authorities. Their ``verify`` methods
require the original verified auditory L5 experience, whose immutable L5 and
upstream receipt registries remain the authority graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import (
    DSF_FIELD_ORDER,
    exact_dsf_field_tuple_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5ComponentKind,
    AuditoryL5Experience,
    AuditoryL5FieldTuple,
    AuditoryL5KernelComponent,
)
from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)


AUDITORY_L4_CAUSAL_SUPPORT_SCHEMA = (
    "guala.auditory.l4_causal_support.v2"
)
AUDITORY_L4_COMPONENT_SUPPORT_SCHEMA = (
    "guala.auditory.l4_component_support.v2"
)
AUDITORY_L4_EXPERIENCE_SUPPORT_SCHEMA = (
    "guala.auditory.l4_experience_support.v2"
)
_SIGNED_TRACE_SCHEMA = (
    "glew.provider.complete_signed_port_l0_l4_trace.v3"
)
_PHYSICAL_TRACE_SCHEMA = (
    "glew.provider.complete_physical_port_l0_l4_trace.v4"
)
_COMPONENTS_PER_CHANNEL = 2
_HOP_DURATION = Fraction(
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory L4 support fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ReceiptError(f"{name} is not a canonical exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ReceiptError(
            f"{name} is not a canonical exact fraction"
        ) from error
    if _fraction_text(result) != value:
        raise ReceiptError(f"{name} is not a canonical exact fraction")
    return result


def _mounted_exact(
    *,
    experience: AuditoryL5Experience,
    digest: str,
    expected: bytes,
    field_name: str,
    upstream: bool,
) -> None:
    registry = (
        experience.upstream_receipt_registry
        if upstream
        else experience.receipt_registry
    )
    mounted = registry.resolve(digest, field_name)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} differs from mounted authority")


@dataclass(frozen=True, slots=True)
class AuditoryL4CausalSupport:
    tuple_index: int
    source_index_start: int
    source_index_end: int
    causal_interval_start: Fraction
    causal_interval_end: Fraction
    causal_offset_start: Fraction
    causal_offset_end: Fraction
    fields: tuple[tuple[str, Fraction], ...]
    l4_tuple_authority_receipt_sha256: str
    source_l0_l4_trace_receipt_sha256: str
    integrity_receipt_sha256: str

    def payload(self) -> bytes:
        return _canonical_bytes({
            "causal_interval_end": _fraction_text(
                self.causal_interval_end
            ),
            "causal_interval_start": _fraction_text(
                self.causal_interval_start
            ),
            "causal_offset_end": _fraction_text(self.causal_offset_end),
            "causal_offset_start": _fraction_text(
                self.causal_offset_start
            ),
            "exact_fields": {
                name: _fraction_text(value)
                for name, value in self.fields
            },
            "l4_tuple_authority_receipt_sha256": (
                self.l4_tuple_authority_receipt_sha256
            ),
            "schema": AUDITORY_L4_CAUSAL_SUPPORT_SCHEMA,
            "source_index_end_inclusive": self.source_index_end,
            "source_index_start_inclusive": self.source_index_start,
            "source_l0_l4_trace_receipt_sha256": (
                self.source_l0_l4_trace_receipt_sha256
            ),
            "tuple_index": self.tuple_index,
        })

    def verify(
        self,
        experience: AuditoryL5Experience,
        component: AuditoryL5KernelComponent,
        exact: AuditoryL5FieldTuple,
    ) -> None:
        if not isinstance(experience, AuditoryL5Experience):
            raise ReceiptError(
                "auditory L4 support requires its L5 experience authority"
            )
        if not isinstance(component, AuditoryL5KernelComponent):
            raise ReceiptError(
                "auditory L4 support requires its L5 component authority"
            )
        if not isinstance(exact, AuditoryL5FieldTuple):
            raise ReceiptError(
                "auditory L4 support requires its L4 tuple authority"
            )
        if (
            isinstance(self.tuple_index, bool)
            or not isinstance(self.tuple_index, int)
            or self.tuple_index < 0
            or isinstance(self.source_index_start, bool)
            or not isinstance(self.source_index_start, int)
            or isinstance(self.source_index_end, bool)
            or not isinstance(self.source_index_end, int)
            or not 0 <= self.source_index_start <= self.source_index_end
        ):
            raise ReceiptError("auditory L4 causal support indices changed")
        for name, value in (
            ("interval start", self.causal_interval_start),
            ("interval end", self.causal_interval_end),
            ("offset start", self.causal_offset_start),
            ("offset end", self.causal_offset_end),
        ):
            require_fraction(value, f"auditory L4 support {name}")
        if (
            self.causal_interval_end <= self.causal_interval_start
            or self.causal_offset_end <= self.causal_offset_start
            or self.causal_interval_start
            != experience.source_time_start + self.causal_offset_start
            or self.causal_interval_end
            != experience.source_time_start + self.causal_offset_end
        ):
            raise ReceiptError("auditory L4 causal interval changed")
        if (
            tuple(name for name, _value in self.fields)
            != DSF_FIELD_ORDER
            or any(
                not isinstance(value, Fraction)
                for _name, value in self.fields
            )
            or self.tuple_index != exact.tuple_index
            or self.fields != exact.fields
            or self.l4_tuple_authority_receipt_sha256
            != exact.authority_receipt_sha256
            or self.source_l0_l4_trace_receipt_sha256
            != component.l0_l4_trace_receipt_sha256
            or self.source_l0_l4_trace_receipt_sha256
            != exact.source_l0_l4_trace_receipt_sha256
        ):
            raise ReceiptError(
                "auditory L4 causal support differs from its authority"
            )
        exact_fields = dict(self.fields)
        tuple_payload = exact_dsf_field_tuple_receipt_payload(
            lane_id="sound",
            port_id=component.substream_id,
            tuple_index=self.tuple_index,
            D_k=exact_fields["D_k"],
            M_k=exact_fields["M_k"],
            R_rev_k=exact_fields["R_rev_k"],
            U_star_k=exact_fields["U_star_k"],
            C_k=exact_fields["C_k"],
            P_k=exact_fields["P_k"],
            B_k=exact_fields["B_k"],
            source_l0_l4_trace_receipt_sha256=(
                self.source_l0_l4_trace_receipt_sha256
            ),
        )
        _mounted_exact(
            experience=experience,
            digest=self.l4_tuple_authority_receipt_sha256,
            expected=tuple_payload,
            field_name="auditory exact L4 tuple authority",
            upstream=True,
        )
        experience.upstream_receipt_registry.resolve(
            self.source_l0_l4_trace_receipt_sha256,
            "auditory L0-L4 trace authority",
        )
        if receipt_sha256(self.payload()) != self.integrity_receipt_sha256:
            raise ReceiptError("auditory L4 causal support integrity changed")


@dataclass(frozen=True, slots=True)
class AuditoryL4ComponentSupport:
    topology_index: int
    substream_id: str
    component_kind: AuditoryL5ComponentKind
    component_authority_receipt_sha256: str
    source_l0_l4_trace_receipt_sha256: str
    tuples: tuple[AuditoryL4CausalSupport, ...]
    integrity_receipt_sha256: str

    def payload(self) -> bytes:
        return _canonical_bytes({
            "component_authority_receipt_sha256": (
                self.component_authority_receipt_sha256
            ),
            "component_kind": self.component_kind.value,
            "schema": AUDITORY_L4_COMPONENT_SUPPORT_SCHEMA,
            "source_l0_l4_trace_receipt_sha256": (
                self.source_l0_l4_trace_receipt_sha256
            ),
            "substream_id": self.substream_id,
            "topology_index": self.topology_index,
            "tuple_support_integrity_sha256s": [
                value.integrity_receipt_sha256 for value in self.tuples
            ],
        })

    def verify(
        self,
        experience: AuditoryL5Experience,
        component: AuditoryL5KernelComponent,
    ) -> None:
        if (
            isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or not 0
            <= self.topology_index
            < AUDITORY_KERNEL_COMPONENT_COUNT
            or not isinstance(self.substream_id, str)
            or not self.substream_id
            or not isinstance(
                self.component_kind,
                AuditoryL5ComponentKind,
            )
            or self.topology_index != component.topology_index
            or self.substream_id != component.substream_id
            or self.component_kind is not component.kind
            or self.component_authority_receipt_sha256
            != component.authority_receipt_sha256
            or self.source_l0_l4_trace_receipt_sha256
            != component.l0_l4_trace_receipt_sha256
        ):
            raise ReceiptError(
                "auditory L4 component support differs from its authority"
            )
        component.verify(experience.receipt_registry)
        if (
            not self.tuples
            or len(self.tuples) != len(component.l4_field_tuples)
            or tuple(value.tuple_index for value in self.tuples)
            != tuple(range(len(self.tuples)))
        ):
            raise ReceiptError("auditory L4 component support is incomplete")
        prior_index_end = -1
        prior_interval_end: Fraction | None = None
        for value, exact in zip(
            self.tuples,
            component.l4_field_tuples,
            strict=True,
        ):
            value.verify(experience, component, exact)
            if (
                value.source_index_start != prior_index_end + 1
                or (
                    prior_interval_end is not None
                    and value.causal_interval_start
                    != prior_interval_end
                )
            ):
                raise ReceiptError(
                    "auditory L4 component support skipped a causal interval"
                )
            prior_index_end = value.source_index_end
            prior_interval_end = value.causal_interval_end
        if (
            prior_index_end != len(component.samples) - 1
            or self.tuples[0].causal_interval_start
            != experience.source_time_start
            or self.tuples[-1].causal_interval_end
            != experience.source_time_end
        ):
            raise ReceiptError(
                "auditory L4 support does not cover its complete experience"
            )
        if receipt_sha256(self.payload()) != self.integrity_receipt_sha256:
            raise ReceiptError(
                "auditory L4 component support integrity changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryL4ExperienceSupport:
    experience_id: str
    structural_fingerprint: str
    assembly_id: str
    relation: str
    event_boundary: str
    source_time_start: Fraction
    source_time_end: Fraction
    assembly_receipt_sha256: str
    l5_authority_receipt_sha256: str
    components: tuple[AuditoryL4ComponentSupport, ...]
    integrity_receipt_sha256: str

    def payload(self) -> bytes:
        return _canonical_bytes({
            "assembly_id": self.assembly_id,
            "assembly_receipt_sha256": self.assembly_receipt_sha256,
            "component_support_integrity_sha256s": [
                value.integrity_receipt_sha256
                for value in self.components
            ],
            "event_boundary": self.event_boundary,
            "experience_id": self.experience_id,
            "l5_authority_receipt_sha256": (
                self.l5_authority_receipt_sha256
            ),
            "relation": self.relation,
            "schema": AUDITORY_L4_EXPERIENCE_SUPPORT_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "structural_fingerprint": self.structural_fingerprint,
        })

    def verify(self, experience: AuditoryL5Experience) -> None:
        experience.verify()
        if (
            self.experience_id != experience.experience_id
            or self.structural_fingerprint
            != experience.structural_fingerprint
            or self.assembly_id != experience.assembly_id
            or self.relation != experience.relation
            or self.event_boundary != experience.event_boundary
            or self.source_time_start != experience.source_time_start
            or self.source_time_end != experience.source_time_end
            or self.assembly_receipt_sha256
            != experience.assembly_receipt_sha256
            or self.l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
        ):
            raise ReceiptError(
                "auditory L4 experience support differs from its authority"
            )
        require_identifier(self.assembly_id, "auditory support assembly")
        sha256_digest(
            self.structural_fingerprint,
            "auditory support structural fingerprint",
        )
        sha256_digest(
            self.assembly_receipt_sha256,
            "auditory support assembly authority",
        )
        l5_payload = experience.receipt_registry.resolve(
            self.l5_authority_receipt_sha256,
            "auditory support L5 authority",
        )
        if receipt_sha256(l5_payload) != self.l5_authority_receipt_sha256:
            raise ReceiptError("auditory support L5 authority changed")
        if (
            len(self.components) != AUDITORY_KERNEL_COMPONENT_COUNT
            or tuple(
                value.topology_index for value in self.components
            ) != tuple(range(AUDITORY_KERNEL_COMPONENT_COUNT))
        ):
            raise ReceiptError(
                "auditory L4 experience support lost a component"
            )
        source_components = tuple(
            component
            for channel in experience.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
        )
        for index, (value, component) in enumerate(zip(
            self.components,
            source_components,
            strict=True,
        )):
            value.verify(experience, component)
            expected_kind = (
                AuditoryL5ComponentKind.PRESSURE
                if index % _COMPONENTS_PER_CHANNEL == 0
                else AuditoryL5ComponentKind.CARRIER_PHASE_ADVANCE
            )
            if value.component_kind is not expected_kind:
                raise ReceiptError(
                    "auditory L4 component topology was reordered"
                )
        if receipt_sha256(self.payload()) != self.integrity_receipt_sha256:
            raise ReceiptError(
                "auditory L4 experience support integrity changed"
            )


def _gate_interval(
    trace: dict[str, object],
    tuple_index: int,
    sample_count: int,
) -> tuple[int, int]:
    intervals = []
    for layer_name in (
        "L1_GateL1State",
        "L2_GateInterpretation",
        "L3_ResonanceResult",
    ):
        layer = trace.get(layer_name)
        if not isinstance(layer, list) or tuple_index >= len(layer):
            raise ReceiptError(
                "auditory L4 trace gate trajectory is incomplete"
            )
        row = layer[tuple_index]
        if not isinstance(row, dict):
            raise ReceiptError("auditory L4 trace gate is malformed")
        start = row.get("start_idx")
        end = row.get("end_idx")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
        ):
            raise ReceiptError("auditory L4 trace gate index changed")
        intervals.append((start, end))
    if len(set(intervals)) != 1:
        raise ReceiptError("auditory L1-L3 gate supports diverged")
    start, end = intervals[0]
    if not 0 <= start <= end < sample_count:
        raise ReceiptError("auditory L4 gate support left its source grid")
    return start, end


def _trace(
    experience: AuditoryL5Experience,
    component: AuditoryL5KernelComponent,
) -> dict[str, object]:
    payload = experience.upstream_receipt_registry.resolve(
        component.l0_l4_trace_receipt_sha256,
        "auditory L4 causal-support source trace",
    )
    if receipt_sha256(payload) != component.l0_l4_trace_receipt_sha256:
        raise ReceiptError("auditory L4 source trace receipt changed")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReceiptError("auditory L4 source trace is not JSON") from error
    if (
        not isinstance(value, dict)
        or value.get("schema")
        not in (_SIGNED_TRACE_SCHEMA, _PHYSICAL_TRACE_SCHEMA)
        or value.get("lane_id") != "sound"
        or value.get("port_id") != component.substream_id
        or _canonical_bytes(value) != payload
    ):
        raise ReceiptError("auditory L4 source trace authority changed")
    if value["schema"] == _PHYSICAL_TRACE_SCHEMA:
        if (
            component.kind is not AuditoryL5ComponentKind.PRESSURE
            or value.get("kernel_input_map")
            != AUDITORY_PRESSURE_KERNEL_INPUT_MAP.receipt_record()
        ):
            raise ReceiptError(
                "auditory L4 physical input-map authority changed"
            )
    elif value.get("kernel_input_map") != (
        "F=1+s/2;inverse_s=2*(F-1)"
    ):
        raise ReceiptError(
            "auditory L4 signed input-map authority changed"
        )
    l0 = value.get("L0_SEV")
    l4 = value.get("L4_DSF")
    gate_layers = tuple(
        value.get(name)
        for name in (
            "L1_GateL1State",
            "L2_GateInterpretation",
            "L3_ResonanceResult",
        )
    )
    if (
        not isinstance(l0, list)
        or len(l0) != len(component.samples)
        or not isinstance(l4, list)
        or len(l4) != len(component.l4_field_tuples)
        or any(
            not isinstance(layer, list) or len(layer) != len(l4)
            for layer in gate_layers
        )
    ):
        raise ReceiptError(
            "auditory L4 source trace cardinality changed"
        )
    return value


def _with_tuple_integrity(
    value: AuditoryL4CausalSupport,
) -> AuditoryL4CausalSupport:
    return AuditoryL4CausalSupport(
        tuple_index=value.tuple_index,
        source_index_start=value.source_index_start,
        source_index_end=value.source_index_end,
        causal_interval_start=value.causal_interval_start,
        causal_interval_end=value.causal_interval_end,
        causal_offset_start=value.causal_offset_start,
        causal_offset_end=value.causal_offset_end,
        fields=value.fields,
        l4_tuple_authority_receipt_sha256=(
            value.l4_tuple_authority_receipt_sha256
        ),
        source_l0_l4_trace_receipt_sha256=(
            value.source_l0_l4_trace_receipt_sha256
        ),
        integrity_receipt_sha256=receipt_sha256(value.payload()),
    )


def _with_component_integrity(
    value: AuditoryL4ComponentSupport,
) -> AuditoryL4ComponentSupport:
    return AuditoryL4ComponentSupport(
        topology_index=value.topology_index,
        substream_id=value.substream_id,
        component_kind=value.component_kind,
        component_authority_receipt_sha256=(
            value.component_authority_receipt_sha256
        ),
        source_l0_l4_trace_receipt_sha256=(
            value.source_l0_l4_trace_receipt_sha256
        ),
        tuples=value.tuples,
        integrity_receipt_sha256=receipt_sha256(value.payload()),
    )


def _mount_component(
    experience: AuditoryL5Experience,
    component: AuditoryL5KernelComponent,
    *,
    verify_result: bool = True,
) -> AuditoryL4ComponentSupport:
    trace = _trace(experience, component)
    raw_l4 = trace["L4_DSF"]
    if not isinstance(raw_l4, list):
        raise ReceiptError("auditory L4 trace field path changed")
    supports = []
    prior_end = -1
    for index, exact in enumerate(component.l4_field_tuples):
        row = raw_l4[index]
        if not isinstance(row, dict) or set(row) != set(DSF_FIELD_ORDER):
            raise ReceiptError("auditory L4 trace field structure changed")
        fields = tuple(
            (
                field_name,
                _fraction(
                    row[field_name],
                    f"auditory L4 trace {field_name}",
                ),
            )
            for field_name in DSF_FIELD_ORDER
        )
        if fields != exact.fields:
            raise ReceiptError(
                "auditory L4 trace differs from mounted exact tuple"
            )
        start, end = _gate_interval(
            trace,
            index,
            len(component.samples),
        )
        if start != prior_end + 1:
            raise ReceiptError(
                "auditory L4 gates overlap or omit source samples"
            )
        prior_end = end
        interval_start = component.samples[start].source_time - _HOP_DURATION
        interval_end = component.samples[end].source_time
        provisional = AuditoryL4CausalSupport(
            tuple_index=index,
            source_index_start=start,
            source_index_end=end,
            causal_interval_start=interval_start,
            causal_interval_end=interval_end,
            causal_offset_start=(
                interval_start - experience.source_time_start
            ),
            causal_offset_end=(
                interval_end - experience.source_time_start
            ),
            fields=fields,
            l4_tuple_authority_receipt_sha256=(
                exact.authority_receipt_sha256
            ),
            source_l0_l4_trace_receipt_sha256=(
                component.l0_l4_trace_receipt_sha256
            ),
            integrity_receipt_sha256="",
        )
        supports.append(_with_tuple_integrity(provisional))
    provisional_component = AuditoryL4ComponentSupport(
        topology_index=component.topology_index,
        substream_id=component.substream_id,
        component_kind=component.kind,
        component_authority_receipt_sha256=(
            component.authority_receipt_sha256
        ),
        source_l0_l4_trace_receipt_sha256=(
            component.l0_l4_trace_receipt_sha256
        ),
        tuples=tuple(supports),
        integrity_receipt_sha256="",
    )
    result = _with_component_integrity(provisional_component)
    if verify_result:
        result.verify(experience, component)
    return result


def _mount_experience_support(
    experience: AuditoryL5Experience,
    *,
    verify_components: bool,
) -> AuditoryL4ExperienceSupport:
    components = tuple(
        _mount_component(
            experience,
            component,
            verify_result=verify_components,
        )
        for channel in experience.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
    )
    provisional = AuditoryL4ExperienceSupport(
        experience_id=experience.experience_id,
        structural_fingerprint=experience.structural_fingerprint,
        assembly_id=experience.assembly_id,
        relation=experience.relation,
        event_boundary=experience.event_boundary,
        source_time_start=experience.source_time_start,
        source_time_end=experience.source_time_end,
        assembly_receipt_sha256=experience.assembly_receipt_sha256,
        l5_authority_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        components=components,
        integrity_receipt_sha256="",
    )
    result = AuditoryL4ExperienceSupport(
        experience_id=provisional.experience_id,
        structural_fingerprint=provisional.structural_fingerprint,
        assembly_id=provisional.assembly_id,
        relation=provisional.relation,
        event_boundary=provisional.event_boundary,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        assembly_receipt_sha256=provisional.assembly_receipt_sha256,
        l5_authority_receipt_sha256=(
            provisional.l5_authority_receipt_sha256
        ),
        components=provisional.components,
        integrity_receipt_sha256=receipt_sha256(provisional.payload()),
    )
    return result


def mount_auditory_l4_causal_support(
    experience: AuditoryL5Experience,
) -> AuditoryL4ExperienceSupport:
    """Bind every exact auditory L4 tuple to its authoritative hop support."""

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "auditory L4 support requires an exact L5 experience"
        )
    experience.verify()
    result = _mount_experience_support(
        experience,
        verify_components=True,
    )
    result.verify(experience)
    return result


def _mount_auditory_l4_causal_support_from_verified_l5(
    experience: AuditoryL5Experience,
) -> AuditoryL4ExperienceSupport:
    """Derive support inside the one-shot verified L5 constructor.

    The caller must own the exact immutable ``experience`` and must have
    completed ``experience.verify()`` immediately before this call.
    Component trace, gate, field-order, interval, and receipt checks remain
    inside deterministic construction; repeated deep L5 traversal does not.
    """

    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError(
            "verified auditory support requires exact L5"
        )
    return _mount_experience_support(
        experience,
        verify_components=False,
    )


__all__ = (
    "AUDITORY_L4_CAUSAL_SUPPORT_SCHEMA",
    "AUDITORY_L4_COMPONENT_SUPPORT_SCHEMA",
    "AUDITORY_L4_EXPERIENCE_SUPPORT_SCHEMA",
    "AuditoryL4CausalSupport",
    "AuditoryL4ComponentSupport",
    "AuditoryL4ExperienceSupport",
    "_mount_auditory_l4_causal_support_from_verified_l5",
    "mount_auditory_l4_causal_support",
)
