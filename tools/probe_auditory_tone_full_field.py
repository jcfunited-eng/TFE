"""Compare deterministic full-field relation evidence for isolated tones."""

from __future__ import annotations

import os

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    mount_auditory_krimelack_path,
    relate_auditory_krimelack_paths,
)
from dsf_ai_service.substrate.auditory_event_boundary import (
    partition_auditory_energy_basins,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    PCM_PRESSURE_QUANTUM,
)
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tests.test_auditory_tutor_authority import _tone_wav


def main() -> None:
    os.environ.update(
        EVENT_DRIVEN_SUBSTRATE="0",
        SELF_HEARING_ENABLED="0",
        WAVE_ATLAS_ENABLED="0",
        WAVE_SUMMARY_ENQUEUE_ENABLED="0",
    )
    start_exact_field_executor().assert_healthy()
    engine = Guala()
    try:
        paths = []
        pressure_paths = []
        for index, frequency in enumerate((330, 440, 550)):
            canonical, sample_count, _pcm_bytes, event_field = (
                engine._auditory_tutor_event(
                    _tone_wav(frequency_hz=frequency)
                )
            )
            anchor_ns = 1_000_000_000 + index * 2_000_000_000
            engine.process_sound_frame(
                canonical,
                source="auditory_tutor_asset",
                source_anchor_ns=anchor_ns,
                source_time_end_ns=(
                    anchor_ns
                    + sample_count * 1_000_000_000 // 16_000
                ),
                auditory_event_boundary="utterance",
                _auditory_field_override=event_field,
            )
            experience = engine._latest_auditory_l5_experience
            paths.append(mount_auditory_krimelack_path(experience))
            pressure_paths.append(tuple(
                _pressure_motif(experience, frame)
                for frame in range(
                    len(experience.channels[0].pressure.samples)
                )
            ))
        for left in range(len(paths)):
            for right in range(left + 1, len(paths)):
                relation = relate_auditory_krimelack_paths(
                    paths[left],
                    paths[right],
                )
                print(
                    (330, 440, 550)[left],
                    (330, 440, 550)[right],
                    "matching",
                    relation.matching_non_null,
                    "pressure",
                    relation.pressure_matching_non_null,
                    "phase",
                    relation.phase_matching_non_null,
                    "neighborhoods",
                    relation.pressure_neighborhoods_locked,
                    "locked",
                    relation.structurally_locked,
                    "pressure_basin",
                    _pressure_relation(
                        pressure_paths[left],
                        pressure_paths[right],
                    ),
                )
    finally:
        stop_exact_field_executor()


def _pressure_motif(experience, frame):
    pressure = tuple(
        float(channel.pressure.samples[frame].signal)
        for channel in experience.channels
    )
    try:
        partition = partition_auditory_energy_basins(
            tuple((value,) for value in pressure),
            pressure_uncertainty_full_scale=float(
                PCM_PRESSURE_QUANTUM
            ),
        )
    except ValueError:
        return (0,) * len(pressure)
    upper = frozenset(partition.upper_indices)
    return tuple(
        1 if index in upper else -1
        for index in range(len(pressure))
    )


def _pressure_relation(left, right):
    prior = [0] * (len(right) + 1)
    for left_motif in left:
        current = [0]
        for index, right_motif in enumerate(right, 1):
            current.append(max(
                prior[index],
                current[-1],
                prior[index - 1] + int(left_motif == right_motif),
            ))
        prior = current
    matching = prior[-1]
    return (
        matching,
        canonical_l6_direction(
            dimensions=len(left),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked,
        canonical_l6_direction(
            dimensions=len(right),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked,
    )


if __name__ == "__main__":
    main()
