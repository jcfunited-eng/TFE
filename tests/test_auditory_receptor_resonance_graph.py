from __future__ import annotations

from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.closed_experience import (
    source_evidence_stream_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    auditory_pressure_energy_relevance,
)
from dsf_ai_service.substrate.auditory_receptor_resonance_graph import (
    AUDITORY_PHASE_RESONANCE_EDGE_COUNT,
    AuditoryPhaseResonanceGraphState,
    mount_auditory_phase_resonance_graph,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


PROFILE = b"guala.auditory.receptor.resonance.test.profile.v1"
CALIBRATION = b"guala.auditory.receptor.resonance.test.calibration.v1"
RELEVANCE = b"guala.auditory.receptor.resonance.test.relevance.v1"


def _capture():
    sample_count = OBSERVATION_HOP_SAMPLES * 4
    time = np.arange(sample_count, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    return transduce_auditory_full_field(
        0.4 * np.sin(2.0 * np.pi * 440.0 * time),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )


def _streams(capture):
    profile_digest = receipt_sha256(PROFILE)
    calibration_digest = receipt_sha256(CALIBRATION)
    relevance_digest = receipt_sha256(RELEVANCE)
    times = tuple(
        Fraction(value, 1_000_000_000)
        for value in capture.channels[0].causal_offsets_ns
    )
    pressure_streams = []
    phase_streams = []
    for channel in capture.channels:
        relevances = tuple(
            auditory_pressure_energy_relevance(value)
            for value in channel.pressure_envelope_full_scale
        )
        pressure_streams.append(EvidenceStream(
            lane_id="sound",
            port_id=f"{channel.definition.name}_pressure",
            evidence_id=f"{channel.definition.name}-pressure-evidence",
            source_epoch="auditory-resonance-test",
            port_kind="cochlear-pressure-envelope",
            physical_unit="full-scale-pressure",
            profile_binding_sha256=profile_digest,
            calibration_receipt_sha256=calibration_digest,
            relevance_receipt_sha256=relevance_digest,
            samples=tuple(
                EvidenceSample(
                    source_index=index,
                    timestamp=times[index],
                    signal=Fraction.from_float(
                        channel.pressure_envelope_full_scale[index]
                    ),
                    relevance=relevances[index],
                    phase_turns=Fraction(0),
                )
                for index in range(capture.frame_count)
            ),
        ))
        phase_streams.append(EvidenceStream(
            lane_id="sound",
            port_id=f"{channel.definition.name}_cumulative_phase",
            evidence_id=f"{channel.definition.name}-phase-evidence",
            source_epoch="auditory-resonance-test",
            port_kind="cochlear-cumulative-carrier-phase",
            physical_unit="turns",
            profile_binding_sha256=profile_digest,
            calibration_receipt_sha256=calibration_digest,
            relevance_receipt_sha256=relevance_digest,
            samples=tuple(
                EvidenceSample(
                    source_index=index,
                    timestamp=times[index],
                    signal=Fraction.from_float(
                        channel.carrier_phase_advance_nyquist_fraction[
                            index
                        ]
                    ),
                    relevance=relevances[index],
                    phase_turns=Fraction.from_float(
                        channel.carrier_phase_turns[index]
                    ),
                )
                for index in range(capture.frame_count)
            ),
        ))
    payloads = tuple(
        source_evidence_stream_receipt_payload(value)
        for value in (*pressure_streams, *phase_streams)
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(CALIBRATION, RELEVANCE, *payloads),
    )
    return tuple(pressure_streams), tuple(phase_streams), registry


def test_complete_cumulative_phase_graph_has_all_120_edges() -> None:
    capture = _capture()
    pressure, phase, registry = _streams(capture)

    result = mount_auditory_phase_resonance_graph(
        capture=capture,
        pressure_streams=pressure,
        cumulative_phase_streams=phase,
        receipt_registry=registry,
    )

    assert result.state is AuditoryPhaseResonanceGraphState.READY
    assert result.authority is not None
    result.authority.verify()
    assert (
        len(result.authority.graph.required_edges)
        == AUDITORY_PHASE_RESONANCE_EDGE_COUNT
        == 120
    )
    assert all(
        "pressure" not in edge.left_port_key[1]
        and "pressure" not in edge.right_port_key[1]
        for edge in result.authority.graph.required_edges
    )
    assert not hasattr(result.authority, "value")
    assert not hasattr(result.authority, "identity")
    assert not hasattr(result.authority.graph, "value")
    assert not hasattr(result.authority.graph, "identity")


def test_phase_advance_cannot_impersonate_cumulative_phase() -> None:
    capture = _capture()
    pressure, phase, registry = _streams(capture)
    changed = tuple(
        EvidenceStream(
            lane_id=value.lane_id,
            port_id=value.port_id,
            evidence_id=value.evidence_id,
            source_epoch=value.source_epoch,
            port_kind=value.port_kind,
            physical_unit=value.physical_unit,
            profile_binding_sha256=value.profile_binding_sha256,
            calibration_receipt_sha256=value.calibration_receipt_sha256,
            relevance_receipt_sha256=value.relevance_receipt_sha256,
            samples=tuple(
                EvidenceSample(
                    source_index=sample.source_index,
                    timestamp=sample.timestamp,
                    signal=sample.signal,
                    relevance=sample.relevance,
                    phase_turns=Fraction.from_float(
                        capture.channels[channel_index]
                        .carrier_phase_advance_turns[sample.source_index]
                    ),
                )
                for sample in value.samples
            ),
        )
        for channel_index, value in enumerate(phase)
    )

    result = mount_auditory_phase_resonance_graph(
        capture=capture,
        pressure_streams=pressure,
        cumulative_phase_streams=changed,
        receipt_registry=registry,
    )

    assert result.state is AuditoryPhaseResonanceGraphState.UNRESOLVED
    assert result.authority is None
    assert "cumulative-phase evidence" in result.reason


def test_missing_graph_inputs_are_typed_unresolved() -> None:
    result = mount_auditory_phase_resonance_graph(
        capture=None,
        pressure_streams=None,
        cumulative_phase_streams=None,
        receipt_registry=None,
    )

    assert result.state is AuditoryPhaseResonanceGraphState.UNRESOLVED
    assert result.authority is None
    assert result.reason == (
        "typed auditory capture with cumulative phase is unavailable"
    )
