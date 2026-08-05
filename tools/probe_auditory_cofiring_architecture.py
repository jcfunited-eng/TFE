"""Measure original-spec cochlear co-firing structure on tutor recordings.

This read-only diagnostic does not recognize, teach, or alter substrate state.
It compares three event descriptions already implied by the auditory design:

* physically resolvable winding crossings in each cochlear channel;
* the set of cochlear channels in the upper within-frame pressure basin;
* the ordering of cochlear channels by measured pressure.

The first follows the Audio Krimelack specification directly: an event is a
carrier winding crossing while the resonator amplitude is above the PCM
measurement quantum.  The second uses the same deterministic minimum-variance
basin partition already admitted for the auditory event boundary.  The third
retains ordering only as a diagnostic and is not proposed as recognition
authority.

Every recording is first reduced to its surrounded physical event by the live
production tutor boundary.  No transcript, filename, label, chi, Atlas lookup,
fitted tolerance, ML model, or L0--L4 modification participates.
"""

from __future__ import annotations

import io
import math
import wave
from pathlib import Path

import numpy as np

from dsf_ai_service.substrate.auditory_event_boundary import (
    partition_auditory_energy_basins,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    PCM_PRESSURE_QUANTUM,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_auditory_full_field_discrimination import _decode_pcm
from tools.probe_auditory_surrounded_event_recognition import _wav


RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Your Name is Guala.mp3"),
)


def _event_field(path: Path):
    source_pcm = _decode_pcm(path)
    _event_wav, _sample_count, _pcm_bytes, event_field = (
        Guala._auditory_tutor_event(_wav(source_pcm))
    )
    return event_field


def _winding_rows(field) -> tuple[tuple[int, ...], ...]:
    quantum = float(PCM_PRESSURE_QUANTUM)
    channel_events = []
    for channel in field.channels:
        prior_winding = math.floor(channel.carrier_phase_turns[0])
        events = [0]
        for pressure, phase in zip(
            channel.pressure_envelope_full_scale[1:],
            channel.carrier_phase_turns[1:],
            strict=True,
        ):
            winding = math.floor(phase)
            delta = winding - prior_winding
            events.append(
                0 if pressure <= quantum or delta == 0
                else 1 if delta > 0
                else -1
            )
            prior_winding = winding
        channel_events.append(tuple(events))
    return tuple(
        tuple(channel[index] for channel in channel_events)
        for index in range(field.frame_count)
    )


def _pressure_basin_rows(field) -> tuple[tuple[int, ...], ...]:
    rows = []
    uncertainty = float(PCM_PRESSURE_QUANTUM)
    for frame_index in range(field.frame_count):
        pressure = tuple(
            channel.pressure_envelope_full_scale[frame_index]
            for channel in field.channels
        )
        log_pressure = tuple(
            math.log2(max(value, uncertainty)) for value in pressure
        )
        try:
            partition = partition_auditory_energy_basins(
                tuple((value,) for value in pressure),
                pressure_uncertainty_full_scale=uncertainty,
            )
            upper = frozenset(partition.upper_indices)
        except ValueError:
            levels = tuple(sorted(set(log_pressure)))
            if len(levels) < 2:
                upper = frozenset()
            else:
                candidates = []
                for lower_level, upper_level in zip(
                    levels,
                    levels[1:],
                    strict=False,
                ):
                    lower = tuple(
                        value for value in log_pressure
                        if value <= lower_level
                    )
                    upper_values = tuple(
                        value for value in log_pressure
                        if value >= upper_level
                    )
                    lower_mean = math.fsum(lower) / len(lower)
                    upper_mean = math.fsum(upper_values) / len(upper_values)
                    within = (
                        math.fsum(
                            (value - lower_mean) ** 2 for value in lower
                        )
                        + math.fsum(
                            (value - upper_mean) ** 2
                            for value in upper_values
                        )
                    )
                    candidates.append(
                        (
                            within,
                            -(upper_level - lower_level),
                            lower_level,
                            upper_level,
                        )
                    )
                _within, _gap, _lower, upper_level = min(candidates)
                upper = frozenset(
                    index for index, value in enumerate(log_pressure)
                    if value >= upper_level
                )
        rows.append(
            tuple(1 if index in upper else 0 for index in range(len(pressure)))
        )
    return tuple(rows)


def _pressure_order_rows(field) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(sorted(
            range(len(field.channels)),
            key=lambda channel_index: (
                -field.channels[channel_index]
                .pressure_envelope_full_scale[frame_index],
                channel_index,
            ),
        ))
        for frame_index in range(field.frame_count)
    )


def _ngrams(rows, width: int):
    return {
        rows[index:index + width]
        for index in range(len(rows) - width + 1)
    }


def _pair_summary(left, right) -> str:
    values = []
    for width in (1, 2, 3, 4):
        left_values = _ngrams(left, width)
        right_values = _ngrams(right, width)
        shared = len(left_values & right_values)
        values.append(
            f"{width}:{shared}/{len(left_values)}/{len(right_values)}"
        )
    return ",".join(values)


def main() -> None:
    fields = tuple(_event_field(path) for path in RECORDINGS)
    representations = {
        "winding": tuple(_winding_rows(field) for field in fields),
        "pressure_basin": tuple(
            _pressure_basin_rows(field) for field in fields
        ),
        "pressure_order": tuple(
            _pressure_order_rows(field) for field in fields
        ),
    }
    for path, field in zip(RECORDINGS, fields, strict=True):
        print("event", path.name, "frames", field.frame_count)
    for name, recordings in representations.items():
        print("REPRESENTATION", name)
        for path, rows in zip(RECORDINGS, recordings, strict=True):
            print(
                "unique",
                path.name,
                len(set(rows)),
                "of",
                len(rows),
            )
        for left_index in range(len(RECORDINGS)):
            for right_index in range(left_index + 1, len(RECORDINGS)):
                print(
                    "pair",
                    RECORDINGS[left_index].name,
                    "VS",
                    RECORDINGS[right_index].name,
                    _pair_summary(
                        recordings[left_index],
                        recordings[right_index],
                    ),
                )


if __name__ == "__main__":
    main()
