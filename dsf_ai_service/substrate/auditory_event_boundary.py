"""Deterministic auditory-L5 event settlement inside a tutor capture.

An admitted tutor recording contains one physical utterance surrounded by its
ambient field.  This module separates those two measured cochlear-energy
basins without a transcript, fixed loudness threshold, silence timer, learned
model, chi key, or Atlas lookup. The selected event remains the complete
sixteen-channel pressure, cumulative phase, phase-advance, and normalized
phase-advance path; energy is used only to settle its temporal boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_FULL_FIELD_PROVIDER_SCHEMA,
    AuditoryFullFieldCapture,
)


AUDITORY_EVENT_BOUNDARY_SCHEMA = "guala.auditory_event_boundary.v3"
AUDITORY_EVENT_BOUNDARY_OPERATOR = (
    "two_basin_cochlear_energy_minimum_variance_v1"
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_provider_capture(capture: AuditoryFullFieldCapture) -> None:
    if not isinstance(capture, AuditoryFullFieldCapture):
        raise TypeError("auditory event boundary requires a full-field capture")
    capture.__post_init__()
    if capture.provider_schema != AUDITORY_FULL_FIELD_PROVIDER_SCHEMA:
        raise ValueError("auditory event boundary requires provider-v3 evidence")
    for channel in capture.channels:
        channel.__post_init__()
        advances = channel.carrier_phase_advance_turns
        if capture.source_first_sample_index == 0 and advances[0] != 0.0:
            raise ValueError("auditory event carrier phase genesis changed")


def _capture_sha256(capture: AuditoryFullFieldCapture) -> str:
    _validate_provider_capture(capture)
    payload = {
        "channels": [
            {
                "causal_offsets_ns": list(channel.causal_offsets_ns),
                "carrier_phase_advance_nyquist_fraction": [
                    value.hex()
                    for value in (
                        channel.carrier_phase_advance_nyquist_fraction
                    )
                ],
                "carrier_phase_advance_turns": [
                    value.hex()
                    for value in channel.carrier_phase_advance_turns
                ],
                "carrier_phase_turns": [
                    value.hex() for value in channel.carrier_phase_turns
                ],
                "centre_hz": channel.definition.centre_hz.hex(),
                "erb_width_hz": channel.definition.erb_width_hz.hex(),
                "name": channel.definition.name,
                "pressure_envelope_full_scale": [
                    value.hex()
                    for value in channel.pressure_envelope_full_scale
                ],
            }
            for channel in capture.channels
        ],
        "continuation_receipt_sha256": (
            capture.continuation_receipt_sha256
        ),
        "input_sample_count": capture.input_sample_count,
        "observation_hop_samples": capture.observation_hop_samples,
        "provider_schema": capture.provider_schema,
        "source_first_sample_index": capture.source_first_sample_index,
        "source_sample_rate_hz": capture.source_sample_rate_hz,
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _boundary_payload(
    *,
    capture_sha256: str,
    event_frame_start: int,
    event_frame_end: int,
    frame_count: int,
    lower_basin_frames: int,
    upper_basin_frames: int,
    lower_energy_upper_bound: float,
    upper_energy_lower_bound: float,
    observation_hop_samples: int,
    provider_schema: str,
) -> dict[str, object]:
    return {
        "capture_sha256": capture_sha256,
        "event_frame_end": event_frame_end,
        "event_frame_start": event_frame_start,
        "frame_count": frame_count,
        "lower_basin_frames": lower_basin_frames,
        "lower_energy_upper_bound": lower_energy_upper_bound.hex(),
        "observation_hop_samples": observation_hop_samples,
        "operator": AUDITORY_EVENT_BOUNDARY_OPERATOR,
        "provider_schema": provider_schema,
        "schema": AUDITORY_EVENT_BOUNDARY_SCHEMA,
        "upper_basin_frames": upper_basin_frames,
        "upper_energy_lower_bound": upper_energy_lower_bound.hex(),
    }


@dataclass(frozen=True, slots=True)
class AuditoryEventBoundary:
    capture_sha256: str
    provider_schema: str
    event_frame_start: int
    event_frame_end: int
    frame_count: int
    lower_basin_frames: int
    upper_basin_frames: int
    lower_energy_upper_bound: float
    upper_energy_lower_bound: float
    observation_hop_samples: int
    authority_receipt_sha256: str

    @property
    def source_sample_start(self) -> int:
        return self.event_frame_start * self.observation_hop_samples

    @property
    def source_sample_end(self) -> int:
        return self.event_frame_end * self.observation_hop_samples

    def payload(self) -> dict[str, object]:
        return _boundary_payload(
            capture_sha256=self.capture_sha256,
            event_frame_start=self.event_frame_start,
            event_frame_end=self.event_frame_end,
            frame_count=self.frame_count,
            lower_basin_frames=self.lower_basin_frames,
            upper_basin_frames=self.upper_basin_frames,
            lower_energy_upper_bound=self.lower_energy_upper_bound,
            upper_energy_lower_bound=self.upper_energy_lower_bound,
            observation_hop_samples=self.observation_hop_samples,
            provider_schema=self.provider_schema,
        )

    def verify(self) -> None:
        if self.provider_schema != AUDITORY_FULL_FIELD_PROVIDER_SCHEMA:
            raise ValueError("auditory event boundary provider schema changed")
        if (
            not isinstance(self.capture_sha256, str)
            or len(self.capture_sha256) != 64
            or any(value not in "0123456789abcdef"
                   for value in self.capture_sha256)
        ):
            raise ValueError("auditory event boundary capture changed")
        integers = (
            self.event_frame_start,
            self.event_frame_end,
            self.frame_count,
            self.lower_basin_frames,
            self.upper_basin_frames,
            self.observation_hop_samples,
        )
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in integers):
            raise ValueError("auditory event boundary cardinality changed")
        if (
            self.event_frame_start <= 0
            or self.event_frame_end <= self.event_frame_start
            or self.event_frame_end >= self.frame_count
            or self.lower_basin_frames <= 0
            or self.upper_basin_frames <= 0
            or self.lower_basin_frames + self.upper_basin_frames
            != self.frame_count
            or self.observation_hop_samples <= 0
        ):
            raise ValueError("auditory event boundary is not surrounded")
        if (
            not math.isfinite(self.lower_energy_upper_bound)
            or not math.isfinite(self.upper_energy_lower_bound)
            or self.lower_energy_upper_bound < 0.0
            or self.upper_energy_lower_bound
            <= self.lower_energy_upper_bound
        ):
            raise ValueError("auditory event basins are not physically separate")
        expected = hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()
        if expected != self.authority_receipt_sha256:
            raise ValueError("auditory event boundary receipt changed")


def settle_auditory_event_boundary(
    capture: AuditoryFullFieldCapture,
    *,
    pressure_uncertainty_full_scale: float,
) -> AuditoryEventBoundary:
    """Settle one surrounded event from two separable physical basins."""

    _validate_provider_capture(capture)
    if (
        not math.isfinite(pressure_uncertainty_full_scale)
        or pressure_uncertainty_full_scale <= 0.0
    ):
        raise ValueError("auditory event pressure uncertainty is invalid")
    frame_count = capture.frame_count
    if frame_count < 3:
        raise ValueError("auditory tutor capture cannot surround an event")
    channel_count = len(capture.channels)
    uncertainty = pressure_uncertainty_full_scale
    pressure_rows = tuple(
        tuple(
            channel.pressure_envelope_full_scale[frame_index]
            for channel in capture.channels
        )
        for frame_index in range(frame_count)
    )
    energies = tuple(
        math.fsum(value * value for value in row)
        for row in pressure_rows
    )
    physical_floor = channel_count * uncertainty * uncertainty
    log_energies = tuple(
        math.log2(max(value, physical_floor)) for value in energies
    )
    levels = tuple(sorted(set(log_energies)))
    if len(levels) < 2:
        raise ValueError("auditory tutor capture has only one physical basin")

    candidates = []
    for lower_level, upper_level in zip(levels, levels[1:], strict=False):
        lower = tuple(
            value for value in log_energies if value <= lower_level
        )
        upper = tuple(
            value for value in log_energies if value >= upper_level
        )
        if not lower or not upper:
            continue
        lower_mean = math.fsum(lower) / len(lower)
        upper_mean = math.fsum(upper) / len(upper)
        within = (
            math.fsum((value - lower_mean) ** 2 for value in lower)
            + math.fsum((value - upper_mean) ** 2 for value in upper)
        )
        candidates.append((
            within,
            -(upper_level - lower_level),
            lower_level,
            upper_level,
        ))
    if not candidates:
        raise ValueError("auditory tutor capture has no basin partition")
    _, _, lower_level, upper_level = min(candidates)
    lower_indices = tuple(
        index for index, value in enumerate(log_energies)
        if value <= lower_level
    )
    upper_indices = tuple(
        index for index, value in enumerate(log_energies)
        if value >= upper_level
    )
    event_start = upper_indices[0]
    event_end = upper_indices[-1] + 1
    if event_start <= 0 or event_end >= frame_count:
        raise ValueError(
            "auditory tutor event is not surrounded by measured ambient field"
        )
    if event_end - event_start < 2:
        raise ValueError(
            "auditory tutor event is shorter than two observations"
        )

    lower_upper_bound = max(
        math.fsum((value + uncertainty) ** 2 for value in pressure_rows[index])
        for index in lower_indices
    )
    upper_lower_bound = min(
        math.fsum(
            max(0.0, value - uncertainty) ** 2
            for value in pressure_rows[index]
        )
        for index in upper_indices
    )
    if upper_lower_bound <= lower_upper_bound:
        raise ValueError(
            "auditory tutor event and ambient basins overlap measurement uncertainty"
        )
    capture_sha256 = _capture_sha256(capture)
    payload = _boundary_payload(
        capture_sha256=capture_sha256,
        event_frame_start=event_start,
        event_frame_end=event_end,
        frame_count=frame_count,
        lower_basin_frames=len(lower_indices),
        upper_basin_frames=len(upper_indices),
        lower_energy_upper_bound=lower_upper_bound,
        upper_energy_lower_bound=upper_lower_bound,
        observation_hop_samples=capture.observation_hop_samples,
        provider_schema=capture.provider_schema,
    )
    boundary = AuditoryEventBoundary(
        capture_sha256=capture_sha256,
        provider_schema=capture.provider_schema,
        event_frame_start=event_start,
        event_frame_end=event_end,
        frame_count=frame_count,
        lower_basin_frames=len(lower_indices),
        upper_basin_frames=len(upper_indices),
        lower_energy_upper_bound=lower_upper_bound,
        upper_energy_lower_bound=upper_lower_bound,
        observation_hop_samples=capture.observation_hop_samples,
        authority_receipt_sha256=hashlib.sha256(
            _canonical_bytes(payload)
        ).hexdigest(),
    )
    boundary.verify()
    return boundary


__all__ = [
    "AUDITORY_EVENT_BOUNDARY_OPERATOR",
    "AUDITORY_EVENT_BOUNDARY_SCHEMA",
    "AuditoryEventBoundary",
    "settle_auditory_event_boundary",
]
