"""The vocal body preserves exact mechanics across its Python/native bridge."""

from __future__ import annotations

from array import array
from fractions import Fraction
import sys

from dsf_ai_service import native_production_app as production
from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
)
from guala_core import (
    exact_articulatory_interval_trajectory,
    exact_neutral_articulated_body_state,
)


NEUTRAL_BODY = bytes(exact_neutral_articulated_body_state())


def test_articulatory_body_preserves_native_interval_timing() -> None:
    _, contiguous_pressure, *_ = exact_articulatory_interval_trajectory(
        intervals=(
            (4_000, ((0, 8),), NEUTRAL_BODY),
            (4_000, ((0, 8),), NEUTRAL_BODY),
        )
    )
    separated = exact_articulatory_interval_trajectory(
        intervals=(
            (4_000, ((0, 8),), NEUTRAL_BODY),
            (4_000, (), NEUTRAL_BODY),
            (4_000, ((0, 8),), NEUTRAL_BODY),
        )
    )
    separated_pressure = separated[1]

    assert contiguous_pressure != separated_pressure
    assert len(separated_pressure) == 12_000 + separated[-1]


def test_articulatory_body_retains_exact_motor_event_on_shared_sensory_clock() -> None:
    sample_rate_hz, pressure, packed_body, *_ = (
        exact_articulatory_interval_trajectory(
            intervals=((16_000, ((0, 8),), NEUTRAL_BODY),)
        )
    )
    raw_body = array("h")
    raw_body.frombytes(packed_body)
    if sys.byteorder != "little":
        raw_body.byteswap()
    changed = {0, len(pressure)}
    for channel_index in range(production.ARTICULATORY_BODY_PORT_COUNT):
        start = channel_index * len(pressure)
        channel = raw_body[start : start + len(pressure)]
        changed.update(
            index
            for index in range(1, len(channel))
            if channel[index] != channel[index - 1]
        )
    change_indices = tuple(
        index
        for index in sorted(changed)
        if (index * 1_000_000) % sample_rate_hz == 0
    )

    pressure_hops = production._pcm_hops(
        pressure,
        sample_rate_hz,
        change_indices,
    )
    body_hops = production._articulatory_body_hops(
        packed_body,
        len(pressure),
        sample_rate_hz,
        change_indices,
    )
    assert body_hops
    assert len(body_hops) == len(pressure_hops)
    for (times, _), body_hop in zip(pressure_hops, body_hops, strict=True):
        assert all(len(signal) == len(times) for signal in body_hop)
        for signal, span in zip(
            body_hop,
            production.ARTICULATORY_BODY_DECLARED_SPANS,
            strict=True,
        ):
            assert all(isinstance(value, Fraction) for value in signal)
            assert all((value * span).denominator == 1 for value in signal)
            assert all(
                Fraction.from_float(float(value))
                == Fraction.from_float(float(value.numerator / value.denominator))
                for value in signal
            )

    first_times, _ = pressure_hops[0]
    assert Fraction(1, sample_rate_hz) not in first_times
    assert Fraction(2, sample_rate_hz) in first_times
    assert Fraction(1, 1_000) in first_times
    assert all((time * 1_000_000).denominator == 1 for time in first_times)
    first_ports = production._articulatory_body_ports(
        first_times,
        body_hops[0],
    )
    assert all(port.exact_physical_signal is not None for port in first_ports)
    for port in first_ports:
        assert tuple(
            Fraction.from_float(value) for value in port.normalized_signal
        ) == tuple(
            Fraction.from_float(float(value))
            for value in port.exact_physical_signal
        )

    settled = settle_native_joint_source_episode(
        assembly_id="articulatory-exact-source-boundary",
        observed_substreams={PhysicalSense.BODY: first_ports},
        states=production._sense_states({PhysicalSense.BODY: first_ports}),
        occurrences=(
            production._occurrence(
                tuple(range(len(first_ports))),
                first_times,
                len(first_times),
            ),
        ),
    )
    assert settled.port_count == len(first_ports)
    assert settled.source_sample_count == len(first_ports) * len(first_times)
