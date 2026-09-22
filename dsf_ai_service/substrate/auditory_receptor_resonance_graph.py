"""Complete cross-channel phase-resonance graph for auditory receptors.

Frozen L0--L4 runs independently per native port.  That independence is
correct, but it does not by itself mount GLEW's cross-port ``R_UF`` graph.
This module provides the missing typed graph boundary without changing the
kernel.

All sixteen cumulative-phase streams are required and every unordered pair is
an edge (120 edges).  This is the original receptor co-firing topology:
co-activity is possible between every distinct receptor pair, so completeness
is derived from the physical sixteen-channel topology rather than selecting
edges that happen to produce a favorable result.  Pressure streams are
retained as their paired physical
relevance authority but are deliberately not graph vertices: their phase is
identically zero, so an all-pressure coherence graph would be trivially one
and would not describe auditory resonance.

No scalar resonance value is computed here and the graph is never sound
identity.  A caller must still execute the mounted certified GLEW operator.
Missing cumulative phase, exact ``r=p^2`` pairing, source receipts, or a
common causal grid returns typed UNRESOLVED with ``authority=None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.closed_experience import (
    source_evidence_stream_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    MountedResonanceGraph,
    RequiredEdge,
    resonance_graph_receipt_payload,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    auditory_pressure_energy_relevance,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    AuditoryFullFieldCapture,
)


AUDITORY_PHASE_RESONANCE_GRAPH_ID = (
    "guala-auditory-complete-cumulative-phase-16-v1"
)
AUDITORY_PHASE_RESONANCE_EDGE_COUNT = (
    COCHLEAR_CHANNEL_COUNT * (COCHLEAR_CHANNEL_COUNT - 1) // 2
)


class AuditoryPhaseResonanceGraphState(str, Enum):
    READY = "ready"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class AuditoryPhaseResonanceGraphAuthority:
    graph: MountedResonanceGraph
    pressure_port_keys: tuple[tuple[str, str], ...]
    cumulative_phase_port_keys: tuple[tuple[str, str], ...]
    pressure_source_receipt_sha256s: tuple[str, ...]
    cumulative_phase_source_receipt_sha256s: tuple[str, ...]
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        if (
            len(self.pressure_port_keys) != COCHLEAR_CHANNEL_COUNT
            or len(self.cumulative_phase_port_keys)
            != COCHLEAR_CHANNEL_COUNT
            or len(self.pressure_source_receipt_sha256s)
            != COCHLEAR_CHANNEL_COUNT
            or len(self.cumulative_phase_source_receipt_sha256s)
            != COCHLEAR_CHANNEL_COUNT
            or len(self.graph.required_edges)
            != AUDITORY_PHASE_RESONANCE_EDGE_COUNT
        ):
            raise ReceiptError(
                "auditory cumulative-phase graph lost complete topology"
            )
        expected_edges = tuple(
            RequiredEdge(
                self.cumulative_phase_port_keys[left],
                self.cumulative_phase_port_keys[right],
            )
            for left in range(COCHLEAR_CHANNEL_COUNT)
            for right in range(left + 1, COCHLEAR_CHANNEL_COUNT)
        )
        if self.graph.required_edges != expected_edges:
            raise ReceiptError(
                "auditory cumulative-phase graph changed its complete edges"
            )
        self.graph.verify(self.receipt_registry)
        for digest in (
            *self.pressure_source_receipt_sha256s,
            *self.cumulative_phase_source_receipt_sha256s,
        ):
            self.receipt_registry.resolve(
                digest,
                "auditory resonance source receipt",
            )


@dataclass(frozen=True, slots=True)
class AuditoryPhaseResonanceGraphResult:
    state: AuditoryPhaseResonanceGraphState
    authority: AuditoryPhaseResonanceGraphAuthority | None
    reason: str


def _unresolved(reason: str) -> AuditoryPhaseResonanceGraphResult:
    return AuditoryPhaseResonanceGraphResult(
        state=AuditoryPhaseResonanceGraphState.UNRESOLVED,
        authority=None,
        reason=reason,
    )


def _extend_registry(
    registry: ReceiptRegistry,
    payload: bytes,
) -> ReceiptRegistry:
    digest = receipt_sha256(payload)
    records = list(registry.records)
    existing = {
        record.digest: record.payload for record in registry.records
    }
    if digest in existing:
        if existing[digest] != payload:
            raise ReceiptError(
                "auditory resonance graph receipt collision"
            )
    else:
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(records),
    )


def _source_receipt(
    stream: EvidenceStream,
    registry: ReceiptRegistry,
) -> str:
    payload = source_evidence_stream_receipt_payload(stream)
    digest = receipt_sha256(payload)
    if registry.resolve(
        digest,
        "auditory resonance source stream receipt",
    ) != payload:
        raise ReceiptError(
            "auditory resonance source stream receipt changed"
        )
    return digest


def mount_auditory_phase_resonance_graph(
    *,
    capture: AuditoryFullFieldCapture | None,
    pressure_streams: tuple[EvidenceStream, ...] | None,
    cumulative_phase_streams: tuple[EvidenceStream, ...] | None,
    receipt_registry: ReceiptRegistry | None,
) -> AuditoryPhaseResonanceGraphResult:
    """Mount the complete sixteen-channel phase graph or typed UNRESOLVED."""

    try:
        if not isinstance(capture, AuditoryFullFieldCapture):
            raise ReceiptError(
                "typed auditory capture with cumulative phase is unavailable"
            )
        capture.__post_init__()
        if (
            not isinstance(pressure_streams, tuple)
            or not isinstance(cumulative_phase_streams, tuple)
            or len(pressure_streams) != COCHLEAR_CHANNEL_COUNT
            or len(cumulative_phase_streams) != COCHLEAR_CHANNEL_COUNT
            or not all(
                isinstance(value, EvidenceStream)
                for value in (
                    *pressure_streams,
                    *cumulative_phase_streams,
                )
            )
        ):
            raise ReceiptError(
                "auditory resonance requires sixteen paired pressure and "
                "cumulative-phase streams"
            )
        if not isinstance(receipt_registry, ReceiptRegistry):
            raise ReceiptError(
                "auditory resonance source receipt registry is unavailable"
            )
        pressure_keys = tuple(value.key for value in pressure_streams)
        phase_keys = tuple(value.key for value in cumulative_phase_streams)
        if (
            len(set(pressure_keys)) != COCHLEAR_CHANNEL_COUNT
            or len(set(phase_keys)) != COCHLEAR_CHANNEL_COUNT
            or set(pressure_keys).intersection(phase_keys)
            or any(value.lane_id != "sound" for value in pressure_streams)
            or any(
                value.lane_id != "sound"
                for value in cumulative_phase_streams
            )
        ):
            raise ReceiptError(
                "auditory resonance source topology is not independent"
            )
        reference_times = pressure_streams[0].samples
        reference_timestamps = tuple(
            value.timestamp for value in reference_times
        )
        if (
            len(reference_timestamps) != capture.frame_count
            or any(
                tuple(sample.timestamp for sample in stream.samples)
                != reference_timestamps
                for stream in (
                    *pressure_streams,
                    *cumulative_phase_streams,
                )
            )
        ):
            raise ReceiptError(
                "auditory resonance streams lack one common causal grid"
            )
        for channel_index, (
            channel,
            pressure,
            phase,
        ) in enumerate(zip(
            capture.channels,
            pressure_streams,
            cumulative_phase_streams,
            strict=True,
        )):
            if channel.definition != AUDITORY_CHANNELS[channel_index]:
                raise ReceiptError(
                    "auditory resonance capture topology changed"
                )
            for frame_index, (
                pressure_sample,
                phase_sample,
            ) in enumerate(zip(
                pressure.samples,
                phase.samples,
                strict=True,
            )):
                amplitude = Fraction.from_float(
                    channel.pressure_envelope_full_scale[frame_index]
                )
                relevance = auditory_pressure_energy_relevance(
                    channel.pressure_envelope_full_scale[frame_index]
                )
                cumulative_phase = Fraction.from_float(
                    channel.carrier_phase_turns[frame_index]
                )
                if (
                    pressure_sample.signal != amplitude
                    or pressure_sample.relevance != relevance
                    or pressure_sample.phase_turns != 0
                    or phase_sample.relevance != relevance
                    or phase_sample.phase_turns != cumulative_phase
                ):
                    raise ReceiptError(
                        "auditory resonance stream is not exact paired "
                        "pressure-energy/cumulative-phase evidence"
                    )
        pressure_receipts = tuple(
            _source_receipt(value, receipt_registry)
            for value in pressure_streams
        )
        phase_receipts = tuple(
            _source_receipt(value, receipt_registry)
            for value in cumulative_phase_streams
        )
        edges = tuple(
            RequiredEdge(phase_keys[left], phase_keys[right])
            for left in range(COCHLEAR_CHANNEL_COUNT)
            for right in range(left + 1, COCHLEAR_CHANNEL_COUNT)
        )
        graph_payload = resonance_graph_receipt_payload(
            AUDITORY_PHASE_RESONANCE_GRAPH_ID,
            edges,
        )
        extended_registry = _extend_registry(
            receipt_registry,
            graph_payload,
        )
        graph = MountedResonanceGraph(
            graph_id=AUDITORY_PHASE_RESONANCE_GRAPH_ID,
            required_edges=edges,
            authority_receipt_sha256=receipt_sha256(graph_payload),
        )
        authority = AuditoryPhaseResonanceGraphAuthority(
            graph=graph,
            pressure_port_keys=pressure_keys,
            cumulative_phase_port_keys=phase_keys,
            pressure_source_receipt_sha256s=pressure_receipts,
            cumulative_phase_source_receipt_sha256s=phase_receipts,
            receipt_registry=extended_registry,
        )
        authority.verify()
        return AuditoryPhaseResonanceGraphResult(
            state=AuditoryPhaseResonanceGraphState.READY,
            authority=authority,
            reason=(
                "complete sixteen-channel cumulative-phase graph mounted; "
                "certified R_UF execution remains a separate operation"
            ),
        )
    except (IndexError, KeyError, ReceiptError, TypeError, ValueError) as exc:
        return _unresolved(str(exc))


__all__ = (
    "AUDITORY_PHASE_RESONANCE_EDGE_COUNT",
    "AUDITORY_PHASE_RESONANCE_GRAPH_ID",
    "AuditoryPhaseResonanceGraphAuthority",
    "AuditoryPhaseResonanceGraphResult",
    "AuditoryPhaseResonanceGraphState",
    "mount_auditory_phase_resonance_graph",
)
