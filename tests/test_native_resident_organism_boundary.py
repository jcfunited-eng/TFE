from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

import pytest

from dsf_ai_service.glew_runtime import native_resident_organism as boundary


def _state(label: str) -> bytes:
    return b"GLORUN01-" + label.encode("ascii")


@dataclass
class _NativeResidentOrganismObservation:
    state: bytes
    organism_tick: int
    fabric_generation: int
    mounted_generation: int
    mounted_step_completed: bool = False
    physical_transition_claimed: bool = False
    cognitive_formation_claimed: bool = False
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    cognitive_mosaic_count: int = 0
    mosaic_of_mosaics_count: int = 0
    formation_activation_count: int = 0
    partial_cue_reassembly_count: int = 0
    endogenous_partial_cue_reassembly_count: int = 0
    complete_neuron_count: int = 0
    developmental_resting_neuron_count: int = 0
    physically_transitioned_neuron_count: int = 0
    metabolically_perturbed_body_receptor_count: int = 0
    python_callback_count: int = 0
    schema: str = boundary.OBSERVATION_SCHEMA
    identity: str = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
    fabric_bytes: int = 10
    fabric_sha256: str = "a" * 64
    joint_field_count: int = 2
    joint_neuron_count: int = 6
    cold_restore_authentication_count: int = 1
    cold_restore_decode_count: int = 1
    cold_restore_rebuilt_field_count: int = 0

    @property
    def state_bytes(self) -> int:
        return len(self.state)

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.state).hexdigest()


@dataclass
class _NativeResidentOrganismPrepare:
    predecessor: _NativeResidentOrganismObservation
    successor: _NativeResidentOrganismObservation
    current_cohort_count: int
    token: bytes
    schema: str = boundary.PREPARE_SCHEMA
    predecessor_authentication_count: int = 0
    predecessor_decode_count: int = 0
    predecessor_rebuilt_field_count: int = 0
    successor_seal_count: int = 1
    dsf_delivery_count: int = 6
    complete_neuron_fractal_count: int = 0
    emitted_neuron_fractals: list[tuple[str, list[tuple[str, int, bool, str, str]]]] | None = None
    recurrent_complete_neuron_fractal_count: int = 0
    physical_transition_claimed: bool = False
    cognitive_formation_claimed: bool = False
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    cognitive_mosaic_count: int = 0
    formation_activation_count: int = 0
    partial_cue_reassembly_count: int = 0
    endogenous_partial_cue_reassembly_count: int = 0
    complete_neuron_count: int = 0
    developmental_resting_neuron_count: int = 0
    physically_transitioned_neuron_count: int = 0
    metabolically_perturbed_body_receptor_count: int = 0
    receptor_ingress_sense_counts: tuple[int, int, int, int, int, int] = (
        96,
        0,
        0,
        0,
        0,
        0,
    )
    receptor_ingress_changing_count: int = 0
    receptor_ingress_quiescent_count: int = 96
    motor_unit_recruitments: list[tuple[str, int, int]] | None = None
    python_callback_count: int = 0

    def __post_init__(self) -> None:
        if self.emitted_neuron_fractals is None:
            self.emitted_neuron_fractals = []
        if self.motor_unit_recruitments is None:
            self.motor_unit_recruitments = []

    @property
    def token_hex(self) -> str:
        return self.token.hex()

    @property
    def predecessor_state_sha256(self) -> str:
        return self.predecessor.state_sha256

    @property
    def prepared_state_sha256(self) -> str:
        return self.successor.state_sha256

    @property
    def predecessor_organism_tick(self) -> int:
        return self.predecessor.organism_tick

    @property
    def organism_tick(self) -> int:
        return self.successor.organism_tick

    @property
    def predecessor_fabric_generation(self) -> int:
        return self.predecessor.fabric_generation

    @property
    def fabric_generation(self) -> int:
        return self.successor.fabric_generation

    @property
    def predecessor_mounted_generation(self) -> int:
        return self.predecessor.mounted_generation

    @property
    def mounted_generation(self) -> int:
        return self.successor.mounted_generation

    @property
    def current_cohort_evaluation_count(self) -> int:
        return self.current_cohort_count


class _Source:
    port_count = 96


class _NativeResidentOrganismRuntime:
    schema = boundary.RUNTIME_SCHEMA

    def __init__(self, active: _NativeResidentOrganismObservation) -> None:
        self.active = active
        self.pending: tuple[
            bytes, _NativeResidentOrganismObservation
        ] | None = None
        self.prepare_result_override: object | None = None

    def readiness(self) -> object:
        return self.active

    def save(self) -> bytes:
        return self.active.state

    def observe_retained_formation_recurrence_cues(
        self,
    ) -> list[tuple[str, list[str]]]:
        return [("b" * 64, ["01" * 16])]

    def prepare(self, source: _Source) -> object:
        if self.prepare_result_override is not None:
            return self.prepare_result_override
        token = bytes(range(32))
        successor = _NativeResidentOrganismObservation(
            state=_state("successor"),
            organism_tick=self.active.organism_tick + 1,
            fabric_generation=self.active.fabric_generation + 1,
            mounted_generation=self.active.mounted_generation + 1,
            mounted_step_completed=True,
        )
        self.pending = (token, successor)
        return _NativeResidentOrganismPrepare(
            predecessor=self.active,
            successor=successor,
            current_cohort_count=2,
            token=token,
        )

    def commit(self, token: bytes) -> None:
        if self.pending is None or token != self.pending[0]:
            raise ValueError("pending token mismatch")
        self.active = self.pending[1]
        self.pending = None

    def discard(self, token: bytes) -> None:
        if self.pending is None or token != self.pending[0]:
            raise ValueError("pending token mismatch")
        self.pending = None


class _NativeModule:
    NativeResidentOrganismRuntime = _NativeResidentOrganismRuntime
    NativeResidentOrganismObservation = _NativeResidentOrganismObservation
    NativeResidentOrganismPrepare = _NativeResidentOrganismPrepare

    def __init__(
        self,
        runtime: _NativeResidentOrganismRuntime | object,
    ) -> None:
        self.runtime = runtime
        self.restore_calls: list[tuple[object, ...]] = []

    def restore_native_resident_organism_runtime(
        self, *values: object
    ) -> object:
        self.restore_calls.append(values)
        return self.runtime


def _active() -> _NativeResidentOrganismObservation:
    return _NativeResidentOrganismObservation(
        state=_state("active"),
        organism_tick=100,
        fabric_generation=20,
        mounted_generation=7,
    )


def _restore(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    boundary.NativeResidentOrganism,
    _NativeResidentOrganismRuntime,
    _NativeModule,
]:
    runtime = _NativeResidentOrganismRuntime(_active())
    native = _NativeModule(runtime)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)
    organism = boundary.restore_native_resident_organism(
        current_envelope=runtime.active.state,
        max_envelope_bytes=2_048,
        max_fabric_bytes=2_000,
        max_logical_peak_bytes=5_000,
    )
    return organism, runtime, native


def test_factory_cold_restores_one_concrete_runtime_with_coherent_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, native = _restore(monkeypatch)

    assert native.restore_calls == [
        (runtime.active.state, 2_048, 2_000, 5_000)
    ]
    assert organism.readiness() is runtime.active
    assert organism.save() == runtime.active.state


def test_recurrence_cue_observation_is_exact_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    before = runtime.active.state_sha256

    assert organism.observe_retained_formation_recurrence_cues() == (
        ("b" * 64, ("01" * 16,)),
    )
    assert runtime.active.state_sha256 == before


def test_prepare_accepts_96_ports_as_two_cohorts_without_publishing_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    active = runtime.active

    prepared = organism.prepare(_Source())

    assert prepared.token == bytes(range(32))
    assert prepared.token_hex == bytes(range(32)).hex()
    assert prepared.predecessor_state_sha256 == active.state_sha256
    assert prepared.prepared_state_sha256 != active.state_sha256
    assert prepared.organism_tick == 101
    assert prepared.fabric_generation == 21
    assert prepared.mounted_generation == 8
    assert prepared.predecessor_authentication_count == 0
    assert prepared.predecessor_decode_count == 0
    assert prepared.predecessor_rebuilt_field_count == 0
    assert _Source.port_count == 96
    assert prepared.current_cohort_evaluation_count == 2
    assert prepared.successor_seal_count == 1
    assert prepared.dsf_delivery_count == 6
    assert prepared.complete_neuron_fractal_count == 0
    assert prepared.recurrent_complete_neuron_fractal_count == 0
    assert prepared.python_callback_count == 0
    assert not prepared.physical_transition_claimed
    assert not prepared.cognitive_formation_claimed
    assert not hasattr(prepared, "state")
    assert not hasattr(prepared, "as_bytes")
    assert organism.readiness() is active
    assert organism.save() == active.state


def test_commit_publishes_only_the_native_prepared_successor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    prepared = organism.prepare(_Source())

    committed = organism.commit(prepared.token)

    assert committed is runtime.active
    assert committed.state_sha256 == prepared.prepared_state_sha256
    assert organism.save() == runtime.active.state


def test_discard_preserves_exact_active_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    active = runtime.active
    prepared = organism.prepare(_Source())

    observed = organism.discard(prepared.token)

    assert observed is active
    assert runtime.active is active
    assert organism.save() == active.state


@pytest.mark.parametrize(
    ("envelope", "fabric", "logical"),
    (
        (0, 2_000, 5_000),
        (2_048, True, 5_000),
        (2_048, 2_048, 5_000),
        (2_048, 2_000, 4_096),
    ),
)
def test_incoherent_budget_refuses_before_native_cold_restore(
    monkeypatch: pytest.MonkeyPatch,
    envelope: object,
    fabric: object,
    logical: object,
) -> None:
    runtime = _NativeResidentOrganismRuntime(_active())
    native = _NativeModule(runtime)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    with pytest.raises(ValueError, match="resident organism"):
        boundary.restore_native_resident_organism(
            current_envelope=runtime.active.state,
            max_envelope_bytes=envelope,  # type: ignore[arg-type]
            max_fabric_bytes=fabric,  # type: ignore[arg-type]
            max_logical_peak_bytes=logical,  # type: ignore[arg-type]
        )

    assert native.restore_calls == []


def test_factory_refuses_a_structural_runtime_impostor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RuntimeImpostor:
        schema = boundary.RUNTIME_SCHEMA

        def readiness(self) -> _NativeResidentOrganismObservation:
            return _active()

        def save(self) -> bytes:
            return _active().state

    native = _NativeModule(_RuntimeImpostor())
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    with pytest.raises(TypeError, match="structural impostor"):
        boundary.restore_native_resident_organism(
            current_envelope=_active().state,
            max_envelope_bytes=2_048,
            max_fabric_bytes=2_000,
            max_logical_peak_bytes=5_000,
        )


def test_readiness_refuses_a_structural_observation_impostor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)

    @dataclass
    class _ObservationImpostor:
        state: bytes = _state("impostor")
        schema: str = boundary.OBSERVATION_SCHEMA

    runtime.active = _ObservationImpostor()  # type: ignore[assignment]

    with pytest.raises(TypeError, match="structural impostor"):
        organism.readiness()


def test_prepare_refuses_a_structural_prepare_impostor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None

    class _PrepareImpostor:
        def __getattr__(self, name: str) -> object:
            return getattr(genuine, name)

    runtime.prepare_result_override = _PrepareImpostor()

    with pytest.raises(TypeError, match="structural impostor"):
        organism.prepare(_Source())


def test_prepare_refuses_mutable_native_token_even_when_convertible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine, token=bytearray(range(32))
    )

    with pytest.raises(RuntimeError, match="token changed format"):
        organism.prepare(_Source())



@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("predecessor_authentication_count", 1),
        ("predecessor_decode_count", 1),
        ("predecessor_rebuilt_field_count", 1),
        ("successor_seal_count", 0),
        ("physical_transition_claimed", True),
        ("python_callback_count", 1),
    ),
)
def test_prepare_refuses_replay_or_false_claims(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(genuine, **{field: value})

    with pytest.raises(RuntimeError, match="changed causal physics"):
        organism.prepare(_Source())


def test_prepare_refuses_dsfs_presented_as_native_cognitive_formation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine,
        cognitive_formation_claimed=True,
        cognitive_ordinal=1,
        cognitive_trace_count=1,
    )

    with pytest.raises(RuntimeError, match="changed causal physics"):
        organism.prepare(_Source())


def test_prepare_carries_one_exact_sparse_post_quiescence_fractal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine,
        complete_neuron_fractal_count=1,
        emitted_neuron_fractals=[
            (
                "01" * 16,
                [
                    ("psi-winding", 2, True, "3", "1"),
                    ("plastic-rest-length", 0, False, "5", "7"),
                    ("receptor-quantum-residue", 0, False, "11", "13"),
                ],
            )
        ],
    )

    prepared = organism.prepare(_Source())

    assert prepared.emitted_neuron_fractals == (
        (
            "01" * 16,
            (
                ("psi-winding", 2, True, 3, 1),
                ("plastic-rest-length", 0, False, 5, 7),
                ("receptor-quantum-residue", 0, False, 11, 13),
            ),
        ),
    )


def test_prepare_refuses_fractal_count_without_per_neuron_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine,
        complete_neuron_fractal_count=1,
        emitted_neuron_fractals=[],
    )

    with pytest.raises(RuntimeError, match="count lost its exact evidence"):
        organism.prepare(_Source())


def test_public_constructor_and_non_fixed_tokens_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TypeError, match="created by cold restore"):
        boundary.NativeResidentOrganism()

    organism, _runtime, _native = _restore(monkeypatch)
    with pytest.raises(ValueError, match="exactly 32 immutable bytes"):
        organism.commit(b"short")
