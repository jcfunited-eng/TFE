"""The vocal body preserves exact mechanics across its Python/native bridge."""

from __future__ import annotations

from fractions import Fraction

from dsf_ai_service import native_production_app as production
from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
)
from guala_core import exact_articulatory_interval_trajectory


def test_articulatory_body_preserves_native_interval_timing() -> None:
    _, contiguous_pressure, *_ = exact_articulatory_interval_trajectory(
        intervals=(
            (4_000, ((0, 8),)),
            (4_000, ((0, 8),)),
        )
    )
    separated = exact_articulatory_interval_trajectory(
        intervals=(
            (4_000, ((0, 8),)),
            (4_000, ()),
            (4_000, ((0, 8),)),
        )
    )
    separated_pressure = separated[1]

    assert contiguous_pressure != separated_pressure
    assert len(separated_pressure) == 12_000 + separated[-1]


def test_articulatory_body_retains_real_span_fraction_and_binary64_projection() -> None:
    sample_rate_hz, pressure, packed_body, *_ = (
        exact_articulatory_interval_trajectory(
            intervals=((16_000, ((0, 8),)),)
        )
    )
    body_hops = production._articulatory_body_hops(
        packed_body,
        len(pressure),
        sample_rate_hz,
    )
    assert body_hops
    for hop in body_hops:
        for signal, span in zip(
            hop,
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

    hop_index = next(
        index
        for index, hop in enumerate(body_hops)
        if any(value.denominator % 5 == 0 for signal in hop for value in signal)
    )
    times, _ = production._pcm_hops(pressure, sample_rate_hz)[hop_index]
    ports = production._articulatory_body_ports(times, body_hops[hop_index])
    assert all(port.exact_physical_signal is not None for port in ports)
    for port in ports:
        assert tuple(
            Fraction.from_float(value) for value in port.normalized_signal
        ) == tuple(
            Fraction.from_float(float(value))
            for value in port.exact_physical_signal
        )

    settled = settle_native_joint_source_episode(
        assembly_id="articulatory-exact-source-boundary",
        observed_substreams={PhysicalSense.BODY: ports},
        states=production._sense_states({PhysicalSense.BODY: ports}),
        occurrences=(
            production._occurrence(tuple(range(len(ports))), times, len(times)),
        ),
    )
    assert settled.port_count == len(ports)
    assert settled.source_sample_count == len(ports) * len(times)
