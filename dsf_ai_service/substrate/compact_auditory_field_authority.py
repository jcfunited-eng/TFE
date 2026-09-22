"""Lossless bounded authority for one complete auditory L4 causal field.

The native provider's receipt graph is deliberately verbose because it proves
each L0--L4 execution step.  That graph is transient execution evidence, not an
appropriate durable sensory representation.  This module closes the verified
graph into one bounded authority containing:

* every ordered D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k value;
* the inclusive source-hop interval supporting every L4 tuple;
* the complete component topology and source commitments;
* the exact upstream authority identities needed for provenance.

The seven fields are encoded as IEEE-754 binary64 bit patterns only after
proving ``Fraction.from_float(float(value)) == value``.  This is lossless for
the frozen kernel's exact binary64 receipt domain; a non-binary64 rational is
rejected instead of rounded.  Tuple indices and field names are implicit only
inside the declared canonical schema and order, so no DSF field is flattened
or discarded.  Raw pressure, PCM, and cochlear samples are never retained.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import struct
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

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
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    AuditoryL4ExperienceSupport,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5ComponentKind,
    AuditoryL5Experience,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    VerifiedCausalSettlementCapability,
    source_evidence_sample_commitment_sha256,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    MAX_EMITTED_PCM_SAMPLES,
)


COMPACT_AUDITORY_FIELD_SCHEMA = (
    "guala.compact_auditory_full_dsf_authority.v2"
)
COMPACT_AUDITORY_FIELD_MAGIC = b"GUAFFDS2"
MAX_COMPACT_AUDITORY_FIELD_BYTES = 2 * 1024 * 1024
MAX_COMPACT_AUDITORY_COMPONENTS = 64
MAX_AUDITORY_HOPS_PER_SETTLEMENT = (
    MAX_EMITTED_PCM_SAMPLES // OBSERVATION_HOP_SAMPLES
)
AUDITORY_HOP_DURATION = Fraction(
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)

_HEADER = struct.Struct(">8sI")
_FIELD_TUPLE = struct.Struct(">HH7d")
_AUTHORITY_DIGEST_BYTES = hashlib.sha256().digest_size
_TUPLE_RECEIPT_ROOT_DOMAIN = (
    b"guala.compact-auditory-full-dsf-tuple-receipts.v1\0"
)
_FULL_FIELD_STRUCTURE_DOMAIN = (
    b"guala.compact-auditory-full-dsf-structure.v1\0"
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "compact auditory exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ReceiptError(f"{name} is not a canonical exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ReceiptError(f"{name} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ReceiptError(f"{name} is not a canonical exact fraction")
    return result


def _binary64(value: Fraction, name: str) -> float:
    require_fraction(value, name)
    result = float(value)
    if (
        not math.isfinite(result)
        or Fraction.from_float(result) != value
    ):
        raise ReceiptError(
            f"{name} is outside the exact binary64 kernel receipt domain"
        )
    return result


def _digest_bytes(value: str, name: str) -> bytes:
    sha256_digest(value, name)
    return bytes.fromhex(value)


def _tuple_receipt_root(
    *,
    lane_id: str,
    port_id: str,
    source_l0_l4_trace_receipt_sha256: str,
    tuples: tuple["CompactAuditoryFieldTuple", ...],
) -> str:
    hasher = hashlib.sha256()
    hasher.update(_TUPLE_RECEIPT_ROOT_DOMAIN)
    hasher.update(struct.pack(">I", len(tuples)))
    for value in tuples:
        fields = dict(value.fields)
        payload = exact_dsf_field_tuple_receipt_payload(
            lane_id=lane_id,
            port_id=port_id,
            tuple_index=value.tuple_index,
            D_k=fields["D_k"],
            M_k=fields["M_k"],
            R_rev_k=fields["R_rev_k"],
            U_star_k=fields["U_star_k"],
            C_k=fields["C_k"],
            P_k=fields["P_k"],
            B_k=fields["B_k"],
            source_l0_l4_trace_receipt_sha256=(
                source_l0_l4_trace_receipt_sha256
            ),
        )
        hasher.update(bytes.fromhex(receipt_sha256(payload)))
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class CompactAuditoryFieldTuple:
    tuple_index: int
    source_index_start: int
    source_index_end: int
    fields: tuple[tuple[str, Fraction], ...]

    def verify(
        self,
        *,
        expected_tuple_index: int,
        source_sample_count: int,
    ) -> None:
        if (
            isinstance(self.tuple_index, bool)
            or not isinstance(self.tuple_index, int)
            or self.tuple_index != expected_tuple_index
            or isinstance(self.source_index_start, bool)
            or not isinstance(self.source_index_start, int)
            or isinstance(self.source_index_end, bool)
            or not isinstance(self.source_index_end, int)
            or not 0
            <= self.source_index_start
            <= self.source_index_end
            < source_sample_count
        ):
            raise ReceiptError(
                "compact auditory L4 tuple causal support changed"
            )
        if (
            not isinstance(self.fields, tuple)
            or tuple(name for name, _value in self.fields)
            != DSF_FIELD_ORDER
        ):
            raise ReceiptError(
                "compact auditory L4 tuple lost the full DSF field order"
            )
        for name, value in self.fields:
            _binary64(value, f"compact auditory {name}")


@dataclass(frozen=True, slots=True)
class CompactAuditoryFieldComponent:
    lane_id: str
    port_id: str
    sensor_id: str
    topology_index: int
    component_kind: str
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str
    profile_receipt_sha256: str | None
    source_sample_count: int
    source_sample_commitment_sha256: str
    source_stream_receipt_sha256: str
    source_l0_l4_trace_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    component_authority_receipt_sha256: str
    tuple_receipt_root_sha256: str
    tuples: tuple[CompactAuditoryFieldTuple, ...]

    def verify(self, expected_topology_index: int) -> None:
        for value, name in (
            (self.lane_id, "lane_id"),
            (self.port_id, "port_id"),
            (self.sensor_id, "sensor_id"),
            (self.component_kind, "component_kind"),
            (self.physical_quantity, "physical_quantity"),
            (self.physical_unit, "physical_unit"),
        ):
            require_identifier(value, f"compact auditory component {name}")
        if (
            isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or self.topology_index != expected_topology_index
            or isinstance(self.source_sample_count, bool)
            or not isinstance(self.source_sample_count, int)
            or not 1
            <= self.source_sample_count
            <= MAX_AUDITORY_HOPS_PER_SETTLEMENT
            or not isinstance(self.coordinates, tuple)
            or not self.coordinates
            or any(
                not isinstance(value, tuple)
                or len(value) != 2
                or not all(isinstance(part, str) and part for part in value)
                for value in self.coordinates
            )
            or not isinstance(self.tuples, tuple)
            or not self.tuples
            or len(self.tuples) > self.source_sample_count
        ):
            raise ReceiptError(
                "compact auditory component topology or capacity changed"
            )
        for digest, name in (
            (
                self.source_sample_commitment_sha256,
                "source sample commitment",
            ),
            (self.source_stream_receipt_sha256, "source stream"),
            (
                self.source_l0_l4_trace_receipt_sha256,
                "source L0-L4 trace",
            ),
            (self.kernel_basin_receipt_sha256, "kernel basin"),
            (
                self.component_authority_receipt_sha256,
                "component authority",
            ),
            (self.tuple_receipt_root_sha256, "tuple receipt root"),
        ):
            sha256_digest(digest, f"compact auditory {name}")
        if self.profile_receipt_sha256 is not None:
            sha256_digest(
                self.profile_receipt_sha256,
                "compact auditory profile receipt",
            )
        prior_end = -1
        for tuple_index, value in enumerate(self.tuples):
            value.verify(
                expected_tuple_index=tuple_index,
                source_sample_count=self.source_sample_count,
            )
            if value.source_index_start != prior_end + 1:
                raise ReceiptError(
                    "compact auditory component skipped a causal hop"
                )
            prior_end = value.source_index_end
        if prior_end != self.source_sample_count - 1:
            raise ReceiptError(
                "compact auditory component does not cover its source interval"
            )
        expected_root = _tuple_receipt_root(
            lane_id=self.lane_id,
            port_id=self.port_id,
            source_l0_l4_trace_receipt_sha256=(
                self.source_l0_l4_trace_receipt_sha256
            ),
            tuples=self.tuples,
        )
        if self.tuple_receipt_root_sha256 != expected_root:
            raise ReceiptError(
                "compact auditory tuple authority root changed"
            )

    def metadata_record(self) -> dict[str, object]:
        return {
            "component_authority_receipt_sha256": (
                self.component_authority_receipt_sha256
            ),
            "component_kind": self.component_kind,
            "coordinates": [list(value) for value in self.coordinates],
            "kernel_basin_receipt_sha256": (
                self.kernel_basin_receipt_sha256
            ),
            "lane_id": self.lane_id,
            "physical_quantity": self.physical_quantity,
            "physical_unit": self.physical_unit,
            "port_id": self.port_id,
            "profile_receipt_sha256": self.profile_receipt_sha256,
            "sensor_id": self.sensor_id,
            "source_l0_l4_trace_receipt_sha256": (
                self.source_l0_l4_trace_receipt_sha256
            ),
            "source_sample_commitment_sha256": (
                self.source_sample_commitment_sha256
            ),
            "source_sample_count": self.source_sample_count,
            "source_stream_receipt_sha256": (
                self.source_stream_receipt_sha256
            ),
            "topology_index": self.topology_index,
            "tuple_count": len(self.tuples),
            "tuple_receipt_root_sha256": (
                self.tuple_receipt_root_sha256
            ),
        }


def _full_field_structural_fingerprint(
    components: tuple[CompactAuditoryFieldComponent, ...],
) -> str:
    hasher = hashlib.sha256()
    hasher.update(_FULL_FIELD_STRUCTURE_DOMAIN)
    hasher.update(struct.pack(">H", len(components)))
    for component in components:
        topology = _canonical({
            "component_kind": component.component_kind,
            "coordinates": [list(value) for value in component.coordinates],
            "lane_id": component.lane_id,
            "physical_quantity": component.physical_quantity,
            "physical_unit": component.physical_unit,
            "port_id": component.port_id,
            "source_sample_count": component.source_sample_count,
            "topology_index": component.topology_index,
            "tuple_count": len(component.tuples),
        })
        hasher.update(struct.pack(">I", len(topology)))
        hasher.update(topology)
        for value in component.tuples:
            hasher.update(_FIELD_TUPLE.pack(
                value.source_index_start,
                value.source_index_end,
                *(
                    _binary64(
                        field,
                        f"compact auditory structural {name}",
                    )
                    for name, field in value.fields
                ),
            ))
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class CompactAuditoryFieldAuthority:
    experience_id: str
    structural_fingerprint: str
    assembly_id: str
    relation: str
    event_boundary: str
    source_time_start: Fraction
    source_time_end: Fraction
    assembly_receipt_sha256: str
    source_field_authority_receipt_sha256: str
    components: tuple[CompactAuditoryFieldComponent, ...]
    authority_receipt_sha256: str

    def _verify(
        self,
        *,
        trusted_preencoded: bytes | None = None,
    ) -> None:
        for value, name in (
            (self.experience_id, "experience_id"),
            (self.structural_fingerprint, "structural_fingerprint"),
            (self.assembly_id, "assembly_id"),
            (self.relation, "relation"),
            (self.event_boundary, "event_boundary"),
        ):
            require_identifier(value, f"compact auditory authority {name}")
        for value, name in (
            (self.assembly_receipt_sha256, "assembly receipt"),
            (
                self.source_field_authority_receipt_sha256,
                "source field receipt",
            ),
            (self.authority_receipt_sha256, "authority receipt"),
        ):
            sha256_digest(value, f"compact auditory {name}")
        require_fraction(
            self.source_time_start,
            "compact auditory source start",
        )
        require_fraction(
            self.source_time_end,
            "compact auditory source end",
        )
        if (
            self.source_time_end <= self.source_time_start
            or not isinstance(self.components, tuple)
            or not 1
            <= len(self.components)
            <= MAX_COMPACT_AUDITORY_COMPONENTS
        ):
            raise ReceiptError(
                "compact auditory authority interval or topology changed"
            )
        expected_structure = _full_field_structural_fingerprint(
            self.components
        )
        if self.structural_fingerprint != expected_structure:
            raise ReceiptError(
                "compact auditory full-field structure changed"
            )
        sample_counts = {
            component.source_sample_count
            for component in self.components
        }
        if len(sample_counts) != 1:
            raise ReceiptError(
                "compact auditory components left their shared causal grid"
            )
        expected_end = (
            self.source_time_start
            + next(iter(sample_counts)) * AUDITORY_HOP_DURATION
        )
        if self.source_time_end != expected_end:
            raise ReceiptError(
                "compact auditory source interval differs from its hop grid"
            )
        for topology_index, component in enumerate(self.components):
            component.verify(topology_index)
        encoded = (
            _encode_authority(self, include_digest=False)
            if trusted_preencoded is None
            else trusted_preencoded
        )
        if not isinstance(encoded, bytes):
            raise TypeError(
                "compact auditory preencoded authority must be bytes"
            )
        if (
            len(encoded) + _AUTHORITY_DIGEST_BYTES
            > MAX_COMPACT_AUDITORY_FIELD_BYTES
            or hashlib.sha256(encoded).hexdigest()
            != self.authority_receipt_sha256
        ):
            raise ReceiptError(
                "compact auditory authority changed or exceeded its boundary"
            )

    def verify(self) -> None:
        self._verify()

    def encoded(self) -> bytes:
        self.verify()
        payload = _encode_authority(self, include_digest=False)
        return payload + bytes.fromhex(self.authority_receipt_sha256)


def _metadata_record(
    authority: CompactAuditoryFieldAuthority,
) -> dict[str, object]:
    return {
        "assembly_id": authority.assembly_id,
        "assembly_receipt_sha256": authority.assembly_receipt_sha256,
        "component_count": len(authority.components),
        "components": [
            value.metadata_record() for value in authority.components
        ],
        "event_boundary": authority.event_boundary,
        "experience_id": authority.experience_id,
        "field_order": list(DSF_FIELD_ORDER),
        "hop_duration": _fraction_text(AUDITORY_HOP_DURATION),
        "relation": authority.relation,
        "schema": COMPACT_AUDITORY_FIELD_SCHEMA,
        "source_field_authority_receipt_sha256": (
            authority.source_field_authority_receipt_sha256
        ),
        "source_time_end": _fraction_text(authority.source_time_end),
        "source_time_start": _fraction_text(
            authority.source_time_start
        ),
        "structural_fingerprint": authority.structural_fingerprint,
    }


def _encode_authority(
    authority: CompactAuditoryFieldAuthority,
    *,
    include_digest: bool,
) -> bytes:
    metadata = _canonical(_metadata_record(authority))
    result = bytearray(
        _HEADER.pack(COMPACT_AUDITORY_FIELD_MAGIC, len(metadata))
    )
    result.extend(metadata)
    for component in authority.components:
        for value in component.tuples:
            result.extend(_FIELD_TUPLE.pack(
                value.source_index_start,
                value.source_index_end,
                *(
                    _binary64(field, f"compact auditory {name}")
                    for name, field in value.fields
                ),
            ))
    if include_digest:
        result.extend(hashlib.sha256(result).digest())
    return bytes(result)


def _sample_commitment(component) -> str:
    return source_evidence_sample_commitment_sha256(tuple(
        (
            value.source_index,
            value.source_time,
            value.signal,
            value.relevance,
            value.phase_turns,
        )
        for value in component.samples
    ))


def _compact_auditory_field_from_l5(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
    *,
    verify_inputs: bool,
) -> tuple[CompactAuditoryFieldAuthority, int]:
    if not isinstance(experience, AuditoryL5Experience):
        raise TypeError("compact auditory authority requires auditory L5")
    if not isinstance(support, AuditoryL4ExperienceSupport):
        raise TypeError(
            "compact auditory authority requires exact causal support"
        )
    if verify_inputs:
        experience.verify()
        support.verify(experience)
    source_components = tuple(
        component
        for channel in experience.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
    )
    if len(source_components) != len(support.components):
        raise ReceiptError(
            "compact auditory source topology is incomplete"
        )
    components = []
    for topology_index, (component, component_support) in enumerate(zip(
        source_components,
        support.components,
        strict=True,
    )):
        tuples = tuple(
            CompactAuditoryFieldTuple(
                tuple_index=exact.tuple_index,
                source_index_start=causal.source_index_start,
                source_index_end=causal.source_index_end,
                fields=exact.fields,
            )
            for exact, causal in zip(
                component.l4_field_tuples,
                component_support.tuples,
                strict=True,
            )
        )
        root = _tuple_receipt_root(
            lane_id="sound",
            port_id=component.substream_id,
            source_l0_l4_trace_receipt_sha256=(
                component.l0_l4_trace_receipt_sha256
            ),
            tuples=tuples,
        )
        original_root = hashlib.sha256()
        original_root.update(_TUPLE_RECEIPT_ROOT_DOMAIN)
        original_root.update(struct.pack(">I", len(tuples)))
        for exact in component.l4_field_tuples:
            original_root.update(_digest_bytes(
                exact.authority_receipt_sha256,
                "auditory exact tuple receipt",
            ))
        if root != original_root.hexdigest():
            raise ReceiptError(
                "compact auditory fields differ from verified L4 authority"
            )
        components.append(CompactAuditoryFieldComponent(
            lane_id="sound",
            port_id=component.substream_id,
            sensor_id=component.sensor_id,
            topology_index=topology_index,
            component_kind=component.kind.value,
            coordinates=component.coordinates,
            physical_quantity=component.physical_quantity,
            physical_unit=component.physical_unit,
            profile_receipt_sha256=None,
            source_sample_count=len(component.samples),
            source_sample_commitment_sha256=(
                _sample_commitment(component)
            ),
            source_stream_receipt_sha256=(
                component.source_stream_receipt_sha256
            ),
            source_l0_l4_trace_receipt_sha256=(
                component.l0_l4_trace_receipt_sha256
            ),
            kernel_basin_receipt_sha256=(
                component.kernel_basin_receipt_sha256
            ),
            component_authority_receipt_sha256=(
                component.authority_receipt_sha256
            ),
            tuple_receipt_root_sha256=root,
            tuples=tuples,
        ))
    provisional = CompactAuditoryFieldAuthority(
        experience_id=experience.experience_id,
        structural_fingerprint=_full_field_structural_fingerprint(
            tuple(components)
        ),
        assembly_id=experience.assembly_id,
        relation=experience.relation,
        event_boundary=experience.event_boundary,
        source_time_start=experience.source_time_start,
        source_time_end=experience.source_time_end,
        assembly_receipt_sha256=experience.assembly_receipt_sha256,
        source_field_authority_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        components=tuple(components),
        authority_receipt_sha256="0" * 64,
    )
    payload = _encode_authority(provisional, include_digest=False)
    result = CompactAuditoryFieldAuthority(
        experience_id=provisional.experience_id,
        structural_fingerprint=provisional.structural_fingerprint,
        assembly_id=provisional.assembly_id,
        relation=provisional.relation,
        event_boundary=provisional.event_boundary,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        assembly_receipt_sha256=provisional.assembly_receipt_sha256,
        source_field_authority_receipt_sha256=(
            provisional.source_field_authority_receipt_sha256
        ),
        components=provisional.components,
        authority_receipt_sha256=hashlib.sha256(payload).hexdigest(),
    )
    result._verify(trusted_preencoded=payload)
    return result, len(payload) + _AUTHORITY_DIGEST_BYTES


def compact_auditory_field_from_l5(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> CompactAuditoryFieldAuthority:
    """Close one verified auditory L5 graph into bounded durable authority."""

    return _compact_auditory_field_from_l5(
        experience,
        support,
        verify_inputs=True,
    )[0]


def _compact_auditory_field_from_verified_l5(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> CompactAuditoryFieldAuthority:
    """Close authority inside the one-shot verified L5 constructor."""

    return _compact_auditory_field_from_l5(
        experience,
        support,
        verify_inputs=False,
    )[0]


def _prepare_compact_auditory_field_from_verified_l5(
    experience: AuditoryL5Experience,
    support: AuditoryL4ExperienceSupport,
) -> tuple[CompactAuditoryFieldAuthority, int]:
    """Return verified authority and its exact serialized byte length."""

    return _compact_auditory_field_from_l5(
        experience,
        support,
        verify_inputs=False,
    )


def compact_auditory_field_from_causal_settlement(
    settlement: CausalExperienceSettlement,
    *,
    verified_capability: (
        VerifiedCausalSettlementCapability | None
    ) = None,
) -> CompactAuditoryFieldAuthority:
    """Close a verified two-ear W1 causal settlement without raw samples."""
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError(
            "compact auditory authority requires causal settlement"
        )
    if verified_capability is None:
        settlement.verify()
    else:
        verified_capability.verify_linkage(settlement)
    sound = next(
        (
            value
            for value in settlement.interpretations
            if value.sense == "sound"
        ),
        None,
    )
    if (
        sound is None
        or sound.state != "observed"
        or not 1
        <= len(sound.substreams)
        <= MAX_COMPACT_AUDITORY_COMPONENTS
    ):
        raise ReceiptError(
            "compact auditory causal settlement has no complete sound field"
        )
    components = []
    for topology_index, substream in enumerate(sound.substreams):
        trace_digests = {
            value.source_l0_l4_trace_receipt_sha256
            for value in substream.field_tuples
        }
        if len(trace_digests) != 1:
            raise ReceiptError(
                "compact auditory causal tuples cross source traces"
            )
        trace_digest = next(iter(trace_digests))
        tuple_values = tuple(
            CompactAuditoryFieldTuple(
                tuple_index=field_tuple.tuple_index,
                source_index_start=field_tuple.source_index_start,
                source_index_end=field_tuple.source_index_end,
                fields=field_tuple.fields,
            )
            for field_tuple in substream.field_tuples
        )
        root = _tuple_receipt_root(
            lane_id="sound",
            port_id=substream.substream_id,
            source_l0_l4_trace_receipt_sha256=trace_digest,
            tuples=tuple_values,
        )
        original_root = hashlib.sha256()
        original_root.update(_TUPLE_RECEIPT_ROOT_DOMAIN)
        original_root.update(struct.pack(">I", len(tuple_values)))
        for field_tuple in substream.field_tuples:
            original_root.update(_digest_bytes(
                field_tuple.authority_receipt_sha256,
                "causal settlement exact tuple receipt",
            ))
        if root != original_root.hexdigest():
            raise ReceiptError(
                "compact auditory causal fields differ from L4 authority"
            )
        coordinates = dict(substream.coordinates)
        component_kind = coordinates.get("kernel-component")
        if component_kind not in (
            "pressure-envelope",
            "carrier-phase-advance",
        ):
            raise ReceiptError(
                "compact auditory causal component kind changed"
            )
        components.append(CompactAuditoryFieldComponent(
            lane_id="sound",
            port_id=substream.substream_id,
            sensor_id=substream.sensor_id,
            topology_index=topology_index,
            component_kind=component_kind,
            coordinates=substream.coordinates,
            physical_quantity=substream.physical_quantity,
            physical_unit=substream.physical_unit,
            profile_receipt_sha256=substream.profile_receipt_sha256,
            source_sample_count=substream.source_sample_count,
            source_sample_commitment_sha256=(
                substream.source_sample_commitment_sha256
            ),
            source_stream_receipt_sha256=(
                substream.source_evidence_stream_receipt_sha256
            ),
            source_l0_l4_trace_receipt_sha256=trace_digest,
            kernel_basin_receipt_sha256=(
                substream.kernel_basin_receipt_sha256
            ),
            component_authority_receipt_sha256=(
                substream.kernel_basin_receipt_sha256
            ),
            tuple_receipt_root_sha256=root,
            tuples=tuple_values,
        ))
    provisional = CompactAuditoryFieldAuthority(
        experience_id=settlement.event_id,
        structural_fingerprint=_full_field_structural_fingerprint(
            tuple(components)
        ),
        assembly_id=settlement.assembly_id,
        relation=sound.relation,
        event_boundary="w1-binaural-observation",
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        assembly_receipt_sha256=settlement.assembly_receipt_sha256,
        source_field_authority_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
        components=tuple(components),
        authority_receipt_sha256="0" * 64,
    )
    payload = _encode_authority(provisional, include_digest=False)
    result = CompactAuditoryFieldAuthority(
        experience_id=provisional.experience_id,
        structural_fingerprint=provisional.structural_fingerprint,
        assembly_id=provisional.assembly_id,
        relation=provisional.relation,
        event_boundary=provisional.event_boundary,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        assembly_receipt_sha256=provisional.assembly_receipt_sha256,
        source_field_authority_receipt_sha256=(
            provisional.source_field_authority_receipt_sha256
        ),
        components=provisional.components,
        authority_receipt_sha256=hashlib.sha256(payload).hexdigest(),
    )
    result.verify()
    return result


def _metadata_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReceiptError("compact auditory metadata changed shape")
    return value


def decode_compact_auditory_field(
    encoded: bytes,
) -> CompactAuditoryFieldAuthority:
    """Decode, authenticate, and fully reconstruct one compact authority."""
    if (
        not isinstance(encoded, bytes)
        or len(encoded)
        < _HEADER.size + _AUTHORITY_DIGEST_BYTES
        or len(encoded) > MAX_COMPACT_AUDITORY_FIELD_BYTES
    ):
        raise ReceiptError(
            "compact auditory encoded authority exceeded its boundary"
        )
    content = encoded[:-_AUTHORITY_DIGEST_BYTES]
    mounted_digest = encoded[-_AUTHORITY_DIGEST_BYTES:]
    if not hmac.compare_digest(
        hashlib.sha256(content).digest(),
        mounted_digest,
    ):
        raise ReceiptError("compact auditory authority digest changed")
    magic, metadata_length = _HEADER.unpack_from(content)
    metadata_end = _HEADER.size + metadata_length
    if (
        magic != COMPACT_AUDITORY_FIELD_MAGIC
        or metadata_end > len(content)
    ):
        raise ReceiptError("compact auditory authority header changed")
    metadata_bytes = content[_HEADER.size:metadata_end]
    try:
        metadata = json.loads(metadata_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReceiptError(
            "compact auditory metadata is not canonical JSON"
        ) from error
    if _canonical(metadata) != metadata_bytes:
        raise ReceiptError("compact auditory metadata is not canonical")
    metadata = _metadata_mapping(metadata)
    required = {
        "assembly_id",
        "assembly_receipt_sha256",
        "component_count",
        "components",
        "event_boundary",
        "experience_id",
        "field_order",
        "hop_duration",
        "relation",
        "schema",
        "source_field_authority_receipt_sha256",
        "source_time_end",
        "source_time_start",
        "structural_fingerprint",
    }
    if (
        set(metadata) != required
        or metadata.get("schema") != COMPACT_AUDITORY_FIELD_SCHEMA
        or metadata.get("field_order") != list(DSF_FIELD_ORDER)
        or _fraction(
            metadata.get("hop_duration"),
            "compact auditory hop duration",
        )
        != AUDITORY_HOP_DURATION
        or isinstance(metadata.get("component_count"), bool)
        or not isinstance(metadata.get("component_count"), int)
        or not isinstance(metadata.get("components"), list)
        or len(metadata["components"])
        != metadata["component_count"]
    ):
        raise ReceiptError("compact auditory authority metadata changed")
    offset = metadata_end
    components = []
    for topology_index, raw_component in enumerate(
        metadata["components"]
    ):
        raw_component = _metadata_mapping(raw_component)
        component_required = {
            "component_authority_receipt_sha256",
            "component_kind",
            "coordinates",
            "kernel_basin_receipt_sha256",
            "lane_id",
            "physical_quantity",
            "physical_unit",
            "port_id",
            "profile_receipt_sha256",
            "sensor_id",
            "source_l0_l4_trace_receipt_sha256",
            "source_sample_commitment_sha256",
            "source_sample_count",
            "source_stream_receipt_sha256",
            "topology_index",
            "tuple_count",
            "tuple_receipt_root_sha256",
        }
        coordinates = raw_component.get("coordinates")
        tuple_count = raw_component.get("tuple_count")
        if (
            set(raw_component) != component_required
            or raw_component.get("topology_index") != topology_index
            or not isinstance(coordinates, list)
            or any(
                not isinstance(value, list)
                or len(value) != 2
                or not all(isinstance(part, str) for part in value)
                for value in coordinates
            )
            or isinstance(tuple_count, bool)
            or not isinstance(tuple_count, int)
            or tuple_count <= 0
        ):
            raise ReceiptError(
                "compact auditory component metadata changed"
            )
        tuples = []
        for tuple_index in range(tuple_count):
            end = offset + _FIELD_TUPLE.size
            if end > len(content):
                raise ReceiptError(
                    "compact auditory field payload was truncated"
                )
            unpacked = _FIELD_TUPLE.unpack(content[offset:end])
            offset = end
            fields = tuple(
                (name, Fraction.from_float(value))
                for name, value in zip(
                    DSF_FIELD_ORDER,
                    unpacked[2:],
                    strict=True,
                )
            )
            tuples.append(CompactAuditoryFieldTuple(
                tuple_index=tuple_index,
                source_index_start=unpacked[0],
                source_index_end=unpacked[1],
                fields=fields,
            ))
        components.append(CompactAuditoryFieldComponent(
            lane_id=raw_component.get("lane_id"),
            port_id=raw_component.get("port_id"),
            sensor_id=raw_component.get("sensor_id"),
            topology_index=topology_index,
            component_kind=raw_component.get("component_kind"),
            coordinates=tuple(tuple(value) for value in coordinates),
            physical_quantity=raw_component.get("physical_quantity"),
            physical_unit=raw_component.get("physical_unit"),
            profile_receipt_sha256=raw_component.get(
                "profile_receipt_sha256"
            ),
            source_sample_count=raw_component.get(
                "source_sample_count"
            ),
            source_sample_commitment_sha256=raw_component.get(
                "source_sample_commitment_sha256"
            ),
            source_stream_receipt_sha256=raw_component.get(
                "source_stream_receipt_sha256"
            ),
            source_l0_l4_trace_receipt_sha256=raw_component.get(
                "source_l0_l4_trace_receipt_sha256"
            ),
            kernel_basin_receipt_sha256=raw_component.get(
                "kernel_basin_receipt_sha256"
            ),
            component_authority_receipt_sha256=raw_component.get(
                "component_authority_receipt_sha256"
            ),
            tuple_receipt_root_sha256=raw_component.get(
                "tuple_receipt_root_sha256"
            ),
            tuples=tuple(tuples),
        ))
    if offset != len(content):
        raise ReceiptError("compact auditory field payload has trailing data")
    result = CompactAuditoryFieldAuthority(
        experience_id=metadata.get("experience_id"),
        structural_fingerprint=metadata.get("structural_fingerprint"),
        assembly_id=metadata.get("assembly_id"),
        relation=metadata.get("relation"),
        event_boundary=metadata.get("event_boundary"),
        source_time_start=_fraction(
            metadata.get("source_time_start"),
            "compact auditory source start",
        ),
        source_time_end=_fraction(
            metadata.get("source_time_end"),
            "compact auditory source end",
        ),
        assembly_receipt_sha256=metadata.get(
            "assembly_receipt_sha256"
        ),
        source_field_authority_receipt_sha256=metadata.get(
            "source_field_authority_receipt_sha256"
        ),
        components=tuple(components),
        authority_receipt_sha256=mounted_digest.hex(),
    )
    result.verify()
    if result.encoded() != encoded:
        raise ReceiptError(
            "compact auditory authority did not round-trip exactly"
        )
    return result


def maximum_full_field_payload_bytes() -> int:
    """Exact binary field bytes at W1's physical two-ear/hop ceiling."""
    return (
        MAX_COMPACT_AUDITORY_COMPONENTS
        * MAX_AUDITORY_HOPS_PER_SETTLEMENT
        * _FIELD_TUPLE.size
    )


__all__ = [
    "AUDITORY_HOP_DURATION",
    "COMPACT_AUDITORY_FIELD_SCHEMA",
    "CompactAuditoryFieldAuthority",
    "CompactAuditoryFieldComponent",
    "CompactAuditoryFieldTuple",
    "MAX_AUDITORY_HOPS_PER_SETTLEMENT",
    "MAX_COMPACT_AUDITORY_COMPONENTS",
    "MAX_COMPACT_AUDITORY_FIELD_BYTES",
    "_compact_auditory_field_from_verified_l5",
    "_prepare_compact_auditory_field_from_verified_l5",
    "compact_auditory_field_from_l5",
    "compact_auditory_field_from_causal_settlement",
    "decode_compact_auditory_field",
    "maximum_full_field_payload_bytes",
]
