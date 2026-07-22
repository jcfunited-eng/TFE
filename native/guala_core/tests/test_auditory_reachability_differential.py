"""Strict differential contract for native auditory path reachability."""

from __future__ import annotations

import random
import struct
from fractions import Fraction

import pytest

import guala_core
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate import auditory_reciprocity as reciprocity
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryChannelTopology,
    AuditoryComponentTopology,
    AuditoryPathWitness,
    PackedL4Tuple,
)


MAX_WORK = reciprocity.MAX_REACHABILITY_CELLS_PER_RECOGNITION
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def _fields(offset: Fraction) -> tuple[tuple[str, Fraction], ...]:
    return tuple(
        (name, Fraction(index, 7) + offset)
        for index, name in enumerate(DSF_FIELD_ORDER)
    )


def _witness(
    values: list[list[tuple[float, float]]],
    *,
    fingerprint: str,
    l4_offset: Fraction,
    inconsistent_field: bool = False,
) -> AuditoryPathWitness:
    sample_count = len(values[0])
    assert all(len(port) == sample_count for port in values)
    def component(index: int, kind: str) -> AuditoryComponentTopology:
        phase = kind == "phase"
        return AuditoryComponentTopology(
            sensor_id="test-cochlea",
            substream_id=f"port-{index}-{kind}",
            topology_index=index * 2 + int(phase),
            coordinates=(
                ("cochlear-channel", str(index)),
                ("kernel-component", kind),
            ),
            physical_quantity=(
                "cochlear-carrier-phase-advance"
                if phase
                else "cochlear-pressure-envelope"
            ),
            physical_unit=(
                "turns-per-observation-hop"
                if phase
                else "full-scale-pressure"
            ),
            source_stream_receipt_sha256="1" * 64,
            l0_l4_trace_receipt_sha256="2" * 64,
            kernel_basin_receipt_sha256="3" * 64,
            authority_receipt_sha256="4" * 64,
        )

    topology = tuple(
        AuditoryChannelTopology(
            cochlear_index=index,
            channel_id=f"port-{index}",
            pressure=component(index, "pressure"),
            carrier_phase_advance=component(index, "phase"),
            pair_receipt_sha256="5" * 64,
        )
        for index in range(len(values))
    )
    l4_ports = []
    for port_index in range(len(values)):
        fields = list(_fields(l4_offset))
        if inconsistent_field and port_index == len(values) - 1:
            name, value = fields[-1]
            fields[-1] = (name, value + Fraction(1, 13))
        l4_ports.append((PackedL4Tuple(
            tuple_index=0,
            fields=tuple(fields),
            authority_receipt_sha256="d" * 64,
        ),))
    return AuditoryPathWitness(
        experience_id="e" * 64,
        structural_fingerprint=fingerprint,
        topology=topology,
        sample_count=sample_count,
        source_indices=tuple(range(sample_count)),
        source_time_start=Fraction(0),
        causal_offset_start=Fraction(0),
        causal_offset_step=Fraction(1, 100),
        packed_samples=tuple(
            struct.pack(
                f"<{sample_count * 2}d",
                *(number for sample in port for number in sample),
            )
            for port in values
        ),
        pressure_l4_field_tuples=tuple(l4_ports),
        carrier_phase_advance_l4_field_tuples=tuple(l4_ports),
    )


def _random_values(
    generator: random.Random,
    ports: int,
    samples: int,
    *,
    allow_unresolved_phase: bool,
) -> list[list[tuple[float, float]]]:
    result = []
    for _ in range(ports):
        port = []
        for index in range(samples):
            pressure = generator.uniform(0.001, 0.8)
            if allow_unresolved_phase and index % 4 == 0:
                pressure = generator.choice((0.0, 1.0 / 65_536.0))
            phase_advance = generator.uniform(-0.15, 0.15)
            port.append((pressure, phase_advance))
        result.append(port)
    return result


def _assert_differential(
    query: AuditoryPathWitness,
    left: AuditoryPathWitness,
    right: AuditoryPathWitness,
    *,
    max_work: int = MAX_WORK,
) -> None:
    expected = reciprocity._joint_cell_contains_python(
        query, left, right, max_work=max_work
    )
    actual = reciprocity._joint_cell_contains_native(
        query, left, right, max_work=max_work
    )
    assert actual == expected


def test_seeded_pressure_phase_interval_and_recurrence_cases_are_exact() -> None:
    generator = random.Random(20260721)
    for case in range(240):
        port_count = 16
        left_count = generator.randint(1, 8)
        query_count = generator.randint(1, 8)
        left_values = _random_values(
            generator,
            port_count,
            left_count,
            allow_unresolved_phase=True,
        )
        recurrence = case % 3 == 0
        if recurrence:
            left = _witness(
                left_values, fingerprint=HEX_A, l4_offset=Fraction(0)
            )
            right = left
        else:
            right_count = generator.randint(1, 8)
            right = _witness(
                _random_values(
                    generator,
                    port_count,
                    right_count,
                    allow_unresolved_phase=True,
                ),
                fingerprint=HEX_B,
                l4_offset=Fraction(2),
            )
            left = _witness(
                left_values, fingerprint=HEX_A, l4_offset=Fraction(0)
            )
        query_offset = (
            Fraction(0)
            if recurrence
            else generator.choice((Fraction(0), Fraction(1), Fraction(2)))
        )
        query = _witness(
            _random_values(
                generator,
                port_count,
                query_count,
                allow_unresolved_phase=True,
            ),
            fingerprint=HEX_C,
            l4_offset=query_offset,
            inconsistent_field=(case % 11 == 0 and not recurrence),
        )
        _assert_differential(query, left, right)


def test_accept_reject_topology_l4_and_budget_results_are_exact() -> None:
    path = [
        [(0.25, 0.0), (0.3, 0.1), (0.35, 0.2)]
        for _ in range(16)
    ]
    left = _witness(path, fingerprint=HEX_A, l4_offset=Fraction(0))
    right = _witness(path, fingerprint=HEX_B, l4_offset=Fraction(2))
    for offset in (Fraction(0), Fraction(1), Fraction(2), Fraction(9)):
        query = _witness(path, fingerprint=HEX_C, l4_offset=offset)
        _assert_differential(query, left, right)
    expected_work = query.sample_count * max(
        left.sample_count, right.sample_count
    )
    _assert_differential(
        query, left, right, max_work=expected_work - 1
    )

    changed_topology = _witness(
        [*path, path[0]], fingerprint=HEX_C, l4_offset=Fraction(1)
    )
    _assert_differential(changed_topology, left, right)


def test_fallback_and_native_failures_are_not_confused(monkeypatch) -> None:
    path = [[(0.25, 0.0), (0.3, 0.1)] for _ in range(16)]
    witness = _witness(path, fingerprint=HEX_A, l4_offset=Fraction(0))
    expected = reciprocity._joint_cell_contains_python(
        witness, witness, witness, max_work=MAX_WORK
    )
    monkeypatch.setattr(reciprocity, "_native_joint_path_contains", None)
    assert reciprocity._joint_cell_contains(
        witness, witness, witness, max_work=MAX_WORK
    ) == expected

    def native_failure(*_args):
        raise RuntimeError("native reachability failure")

    monkeypatch.setattr(
        reciprocity, "_native_joint_path_contains", native_failure
    )
    with pytest.raises(RuntimeError, match="native reachability failure"):
        reciprocity._joint_cell_contains(
            witness, witness, witness, max_work=MAX_WORK
        )


def test_native_boundary_rejects_changed_sample_shape() -> None:
    with pytest.raises(ValueError, match="changed shape"):
        guala_core.auditory_joint_path_contains(
            [[0.25, 0.0] for _ in range(16)],
            2,
            [[0.25, 0.0, 0.3, 0.1] for _ in range(16)],
            2,
            [[0.25, 0.0, 0.3, 0.1] for _ in range(16)],
            2,
            True,
            0.0,
            1.0,
            64,
        )


def test_native_boundary_rejects_equal_but_noncochlear_port_cardinality() -> None:
    ports = [[0.25, 0.0] for _ in range(15)]
    with pytest.raises(ValueError, match="exactly 16 cochlear ports"):
        guala_core.auditory_joint_path_contains(
            ports,
            1,
            ports,
            1,
            ports,
            1,
            False,
            0.0,
            1.0,
            64,
        )


def test_native_boundary_rejects_oversized_event_hop_count() -> None:
    oversized_count = 801
    oversized = [[0.25, 0.0] * oversized_count for _ in range(16)]
    singleton = [[0.25, 0.0] for _ in range(16)]
    with pytest.raises(ValueError, match="800-hop event boundary"):
        guala_core.auditory_joint_path_contains(
            oversized,
            oversized_count,
            singleton,
            1,
            singleton,
            1,
            False,
            0.0,
            1.0,
            64,
        )


def test_native_boundary_rejects_excessive_cell_and_recurrence_work() -> None:
    query_count = 899
    reference_count = 900
    query = [[0.25, 0.0] * query_count for _ in range(16)]
    reference = [[0.25, 0.0] * reference_count for _ in range(16)]
    with pytest.raises(ValueError, match="1000000-work boundary"):
        guala_core.auditory_joint_path_contains(
            query,
            query_count,
            reference,
            reference_count,
            reference,
            reference_count,
            True,
            0.0,
            1.0,
            64,
        )


def test_singleton_genesis_is_pressure_authoritative() -> None:
    query_values = [[(0.25, 1.0)] for _ in range(16)]
    left_values = [[(0.25, -1.0)] for _ in range(16)]
    right_values = [[(0.25, 0.0)] for _ in range(16)]
    query = _witness(
        query_values, fingerprint=HEX_C, l4_offset=Fraction(0)
    )
    left = _witness(
        left_values, fingerprint=HEX_A, l4_offset=Fraction(0)
    )
    right = _witness(
        right_values, fingerprint=HEX_B, l4_offset=Fraction(0)
    )

    _assert_differential(query, left, right)
    assert guala_core.auditory_joint_path_contains(
        [[0.25, 1.0] for _ in range(16)],
        1,
        [[0.25, -1.0] for _ in range(16)],
        1,
        [[0.25, 0.0] for _ in range(16)],
        1,
        False,
        0.0,
        1.0,
        64,
    ) is True


def test_genesis_phase_is_ignored_but_post_genesis_phase_is_direct() -> None:
    query_values = [[(0.25, 1.0), (0.25, 0.35)] for _ in range(16)]
    mismatch_values = [[(0.25, 1.0), (0.25, -0.35)] for _ in range(16)]
    reference_values = [[(0.25, -1.0), (0.25, 0.35)] for _ in range(16)]
    left = _witness(
        reference_values, fingerprint=HEX_A, l4_offset=Fraction(0)
    )
    right = _witness(
        reference_values, fingerprint=HEX_B, l4_offset=Fraction(0)
    )
    query = _witness(
        query_values, fingerprint=HEX_C, l4_offset=Fraction(0)
    )
    mismatch = _witness(
        mismatch_values, fingerprint=HEX_C, l4_offset=Fraction(0)
    )

    _assert_differential(query, left, right)
    _assert_differential(mismatch, left, right)
    assert reciprocity._joint_cell_contains_python(
        query, left, right, max_work=MAX_WORK
    )[0] is True
    assert reciprocity._joint_cell_contains_python(
        mismatch, left, right, max_work=MAX_WORK
    )[0] is False


def test_recurrence_equivalence_involving_genesis_uses_pressure_only() -> None:
    query_values = [[(0.25, -0.75), (0.25, 0.35)] for _ in range(16)]
    reference_values = [
        [(0.25, -0.75), (0.8, 0.0), (0.25, 0.35)]
        for _ in range(16)
    ]
    reference = _witness(
        reference_values, fingerprint=HEX_A, l4_offset=Fraction(0)
    )
    query = _witness(
        query_values, fingerprint=HEX_C, l4_offset=Fraction(0)
    )

    _assert_differential(query, reference, reference)
    assert reciprocity._joint_cell_contains_python(
        query, reference, reference, max_work=MAX_WORK
    )[0] is True
