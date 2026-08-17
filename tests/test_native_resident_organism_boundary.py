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
    rest_recovered_neuron_count: int = 0
    rest_drained_dissipation_quanta: int = 0
    unmet_dissipation_quanta: int = 0
    externally_perturbed_body_receptor_count: int = 0
    physical_frontier_routes: tuple[
        tuple[str, int, int, str, int, int, int, int], ...
    ] = ()
    preceding_distinct_physical_frontier_routes: tuple[
        tuple[str, int, int, str, int, int, int, int], ...
    ] = ()
    reached_and_foregone_physical_frontier_routes: tuple[
        tuple[str, int, int, str, int, int, int, int], ...
    ] = ()
    working_causal_continuations: tuple[
        tuple[tuple[str, str, int, int], tuple[str, str, int, int]], ...
    ] = ()
    settled_working_frontier: tuple[tuple[str, str, int, int], ...] = ()
    physical_prediction_alternatives: tuple[
        tuple[tuple[str, str, int, int], tuple[str, str, int, int]], ...
    ] = ()
    body_consequence_transfers: tuple[tuple[str, str, int, int], ...] = ()
    affective_balance_trajectories: tuple[
        tuple[
            str,
            int,
            int,
            tuple[int, tuple[str, str, int, int]] | None,
            tuple[int, tuple[str, str, int, int]] | None,
            tuple[
                int,
                int,
                int,
                int,
                int,
                int,
                int,
                tuple[str, str],
                tuple[str, str],
                tuple[str, str],
            ]
            | None,
        ],
        ...,
    ] = ()
    localized_fluid_chemistry: tuple[tuple[object, ...], ...] = ()
    localized_metabolic_strain_evaluated_body_receptor_lineages: tuple[str, ...] = ()
    localized_metabolic_strain: tuple[tuple[object, ...], ...] = ()
    organic_mosaic_relations: tuple[
        tuple[
            tuple[str, ...],
            tuple[str, ...],
            tuple[tuple[str, str, int], ...],
            str,
            tuple[
                tuple[
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                ],
                ...,
            ],
            tuple[
                tuple[
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                ],
                ...,
            ],
        ],
        ...,
    ] = ()
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

    @property
    def articulated_body_axes(
        self,
    ) -> list[tuple[int, str, str, int, int, int, int]]:
        return [
            (ordinal, f"axis_{ordinal}", "millidegree", 0, -1, 0, 1)
            for ordinal in range(37)
        ]

    @property
    def articulated_body_lung_air_microlitres(self) -> int:
        return 2_000_000

    @property
    def articulated_body_vocal_tract_areas_square_millimetres(self) -> list[int]:
        return [125, 145, 165, 185, 205, 225, 245, 265]

    @property
    def articulated_body_state_bytes(self) -> int:
        return 195

    @property
    def articulated_body_proprioception_initialized(self) -> bool:
        return False

    @property
    def articulated_body_state_sha256(self) -> str:
        return hashlib.sha256(b"neutral articulated body").hexdigest()


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
    internally_reassembled_formation_cues: list[
        tuple[str, list[str]]
    ] | None = None
    complete_neuron_count: int = 0
    developmental_resting_neuron_count: int = 0
    physically_transitioned_neuron_count: int = 0
    metabolically_perturbed_body_receptor_count: int = 0
    rest_recovered_neuron_count: int = 0
    rest_drained_dissipation_quanta: int = 0
    unmet_dissipation_quanta: int = 0
    externally_perturbed_body_receptor_count: int = 0
    externally_perturbed_neuron_lineages: list[str] | None = None
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
    motor_unit_recruitments: list[
        tuple[
            str,
            int,
            int,
            list[tuple[str, int, str, int, int, int]],
            list[tuple[str, str, str, int, int, str, str]],
        ]
    ] | None = None
    body_effector_bindings: list[tuple[str, str, str, int]] | None = None
    articulated_body_consequences: list[tuple[object, ...]] | None = None
    body_proprioceptive_sources: list[bytes] | None = None
    body_proprioceptive_source_extents: list[tuple[int, int, int, int, int]] | None = None
    active_physical_bonds: list[tuple[str, str, int]] | None = None
    changed_contact_channel_states: list[tuple[object, ...]] | None = None
    physical_frontier_routes: list[
        tuple[str, int, int, str, int, int, int, int]
    ] | None = None
    preceding_distinct_physical_frontier_routes: list[
        tuple[str, int, int, str, int, int, int, int]
    ] | None = None
    reached_and_foregone_physical_frontier_routes: list[
        tuple[str, int, int, str, int, int, int, int]
    ] | None = None
    working_causal_continuations: list[
        tuple[tuple[str, str, int, str], tuple[str, str, int, str]]
    ] | None = None
    settled_working_frontier: list[tuple[str, str, int, str]] | None = None
    physical_prediction_alternatives: list[
        tuple[tuple[str, str, int, str], tuple[str, str, int, str]]
    ] | None = None
    body_consequence_transfers: list[tuple[str, str, int, str]] | None = None
    affective_balance_trajectories: list[tuple[object, ...]] | None = None
    localized_fluid_chemistry: list[tuple[object, ...]] | None = None
    localized_metabolic_strain_evaluated_body_receptor_lineages: list[str] | None = None
    localized_metabolic_strain: list[tuple[object, ...]] | None = None
    organic_mosaic_relations: list[
        tuple[
            list[str],
            list[str],
            list[tuple[str, str, int]],
            str,
            list[tuple[tuple[str, str, int, str], tuple[str, str, int, str]]],
            list[
                tuple[
                    tuple[str, str, int, str],
                    tuple[str, str, int, str],
                    tuple[str, str, int, str],
                    tuple[str, str, int, str],
                ]
            ],
        ]
    ] | None = None
    reached_source_port_count: int = 96
    causal_interval_count: int = 1
    python_callback_count: int = 0

    def __post_init__(self) -> None:
        if self.emitted_neuron_fractals is None:
            self.emitted_neuron_fractals = []
        if self.motor_unit_recruitments is None:
            self.motor_unit_recruitments = []
        if self.body_effector_bindings is None:
            self.body_effector_bindings = []
        if self.articulated_body_consequences is None:
            self.articulated_body_consequences = []
        if self.body_proprioceptive_sources is None:
            self.body_proprioceptive_sources = []
        if self.body_proprioceptive_source_extents is None:
            self.body_proprioceptive_source_extents = []
        if self.active_physical_bonds is None:
            self.active_physical_bonds = []
        if self.changed_contact_channel_states is None:
            self.changed_contact_channel_states = []
        if self.physical_frontier_routes is None:
            self.physical_frontier_routes = []
        if self.preceding_distinct_physical_frontier_routes is None:
            self.preceding_distinct_physical_frontier_routes = []
        if self.reached_and_foregone_physical_frontier_routes is None:
            self.reached_and_foregone_physical_frontier_routes = []
        if self.working_causal_continuations is None:
            self.working_causal_continuations = []
        if self.settled_working_frontier is None:
            self.settled_working_frontier = []
        if self.physical_prediction_alternatives is None:
            self.physical_prediction_alternatives = []
        if self.body_consequence_transfers is None:
            self.body_consequence_transfers = []
        if self.affective_balance_trajectories is None:
            self.affective_balance_trajectories = []
        if self.localized_fluid_chemistry is None:
            self.localized_fluid_chemistry = []
        if self.localized_metabolic_strain_evaluated_body_receptor_lineages is None:
            self.localized_metabolic_strain_evaluated_body_receptor_lineages = []
        if self.localized_metabolic_strain is None:
            self.localized_metabolic_strain = []
        if self.organic_mosaic_relations is None:
            self.organic_mosaic_relations = []
        if self.internally_reassembled_formation_cues is None:
            self.internally_reassembled_formation_cues = []
        if self.externally_perturbed_neuron_lineages is None:
            self.externally_perturbed_neuron_lineages = []

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

    def observe_retained_formation_recurrence_evidence(
        self,
    ) -> list[tuple[str, list[str], str]]:
        return [("b" * 64, ["01" * 16], "internally_simulated")]

    def observe_reached_neuron_lineage_layers(
        self,
    ) -> list[tuple[str, int, bool]]:
        return [("01" * 16, 5, True), ("02" * 16, 9, False)]

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
            rest_drained_dissipation_quanta=7,
            unmet_dissipation_quanta=3,
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


def test_observation_signature_carries_deep_ordered_relation() -> None:
    transfer = ("01" * 16, "02" * 16, 0, 3)
    route = ("01" * 16, 5, 1, "03" * 16, 8, 2, 0, 0)
    relation = (
        ("a" * 64, "b" * 64),
        (),
        (("01" * 16, "02" * 16, 0),),
        "c" * 64,
        ((transfer, transfer),),
        ((transfer, transfer, transfer, transfer),),
    )
    observation = replace(
        _active(),
        physical_frontier_routes=(route,),
        organic_mosaic_relations=(relation,),
    )

    signature = boundary._observation_signature(observation)

    assert (relation,) in signature
    assert (route,) in signature


def test_affective_balance_trajectory_preserves_exact_local_physics() -> None:
    lineage = "10" * 16
    association = (7, ("07" * 16, lineage, 0, "3"))
    body = (8, ("08" * 16, lineage, 0, "2"))
    gradient = (
        9,
        -5,
        -3,
        -4,
        2,
        2,
        0,
        ("11", "2"),
        ("13", "2"),
        ("1", "1"),
    )
    plasticity = (
        9,
        "2",
        "2",
        ("1", "8"),
        ("7", "8"),
        ("0", "1"),
        ("1", "1"),
        ("4", "3"),
        (("1", "1"), ("0", "1"), ("0", "1")),
        (("7", "8"), ("1", "8"), ("0", "1")),
    )
    observation = replace(
        _active(),
        affective_balance_trajectories=(
            (lineage, 10, 4, association, body, gradient, plasticity),
        ),
    )

    assert boundary._affective_balance_trajectory_evidence(
        list(observation.affective_balance_trajectories)
    ) == ((
        lineage,
        10,
        4,
        (7, ("07" * 16, lineage, 0, 3)),
        (8, ("08" * 16, lineage, 0, 2)),
        (9, -5, -3, -4, 2, 2, 0, (11, 2), (13, 2), (1, 1)),
        (
            9,
            2,
            2,
            (1, 8),
            (7, 8),
            (0, 1),
            (1, 1),
            (4, 3),
            ((1, 1), (0, 1), (0, 1)),
            ((7, 8), (1, 8), (0, 1)),
        ),
    ),)
    assert observation.affective_balance_trajectories in boundary._observation_signature(
        observation
    )


def test_affective_balance_preserves_a_lawful_zero_reaction_extent() -> None:
    lineage = "10" * 16
    plasticity = (
        9,
        "2",
        "0",
        ("0", "1"),
        ("7", "8"),
        ("7", "8"),
        ("4", "3"),
        ("4", "3"),
        (("1", "1"), ("0", "1"), ("0", "1")),
        (("1", "1"), ("0", "1"), ("0", "1")),
    )

    observed = boundary._affective_balance_trajectory_evidence(
        [(lineage, 10, 4, None, None, None, plasticity)]
    )

    assert observed[0][6] is not None
    assert observed[0][6][2] == 0


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


def test_recurrence_origin_observation_is_exact_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    before = runtime.active.state_sha256

    assert organism.observe_retained_formation_recurrence_evidence() == (
        ("b" * 64, ("01" * 16,), "internally_simulated"),
    )
    assert runtime.active.state_sha256 == before


def test_lineage_layer_observation_is_exact_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    before = runtime.active.state_sha256

    assert organism.observe_reached_neuron_lineage_layers() == (
        ("01" * 16, 5, True),
        ("02" * 16, 9, False),
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
    assert prepared.rest_recovered_neuron_count == 0
    assert prepared.rest_drained_dissipation_quanta == 7
    assert prepared.unmet_dissipation_quanta == 3
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


def test_prepare_validation_refusal_discards_the_native_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.prepare_result_override = replace(genuine, dsf_delivery_count=-1)

    with pytest.raises(RuntimeError, match="DSF delivery count"):
        organism.prepare(_Source())

    assert runtime.pending is None
    assert organism.readiness().state_sha256 == genuine.predecessor_state_sha256



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


def test_prepare_accepts_equal_consecutive_per_interval_reassembly_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    runtime.active.mounted_step_completed = True
    runtime.active.partial_cue_reassembly_count = 1
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine,
        cognitive_formation_claimed=True,
        partial_cue_reassembly_count=1,
    )

    prepared = organism.prepare(_Source())

    assert prepared.cognitive_formation_claimed
    assert prepared.partial_cue_reassembly_count == 1


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


def test_prepare_carries_exact_layer_eleven_motor_contact_transfer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    motor = "12" * 16
    ordering = "11" * 16
    regulation = "08" * 16
    integration = "06" * 16
    receptor = "05" * 16
    runtime.prepare_result_override = replace(
        genuine,
        motor_unit_recruitments=[
            (
                motor,
                3,
                9,
                [(motor, 12, ordering, 11, 0, 4)],
                [
                    (
                        regulation,
                        integration,
                        receptor,
                        5,
                        17,
                        "mounted-vestibular-organ",
                        "yaw-canal",
                    )
                ],
            )
        ],
    )

    prepared = organism.prepare(_Source())

    assert prepared.motor_unit_recruitments == (
        (
            motor,
            3,
            9,
            ((motor, 12, ordering, 11, 0, 4),),
            (
                (
                    regulation,
                    integration,
                    receptor,
                    5,
                    17,
                    "mounted-vestibular-organ",
                    "yaw-canal",
                ),
            ),
        ),
    )


def test_prepare_refuses_motor_transfer_not_incident_to_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    runtime.prepare_result_override = replace(
        genuine,
        motor_unit_recruitments=[
            (
                "12" * 16,
                3,
                9,
                [("11" * 16, 11, "22" * 16, 12, 0, 4)],
                [],
            )
        ],
    )

    with pytest.raises(RuntimeError, match="exact layer 11/layer 12 contact"):
        organism.prepare(_Source())


def test_prepare_refuses_motor_without_exact_body_afferent_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    motor = "12" * 16
    runtime.prepare_result_override = replace(
        genuine,
        motor_unit_recruitments=[
            (
                motor,
                3,
                9,
                [(motor, 12, "11" * 16, 11, 0, 4)],
                [],
            )
        ],
    )

    with pytest.raises(RuntimeError, match="body afferent paths changed format"):
        organism.prepare(_Source())


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


def test_prepare_carries_exact_bounded_physical_frontier_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    reached = ("01" * 16, 5, 7, "02" * 16, 8, 3, 0, 2)
    foregone = ("01" * 16, 5, 7, "03" * 16, 8, 4, 0, 0)
    preceding = ("04" * 16, 9, 1, "05" * 16, 11, 2, 0, -1)
    runtime.prepare_result_override = replace(
        genuine,
        physical_frontier_routes=[reached, foregone],
        preceding_distinct_physical_frontier_routes=[preceding],
        reached_and_foregone_physical_frontier_routes=[reached, foregone],
    )

    prepared = organism.prepare(_Source())

    assert prepared.physical_frontier_routes == (reached, foregone)
    assert prepared.preceding_distinct_physical_frontier_routes == (preceding,)
    assert prepared.reached_and_foregone_physical_frontier_routes == (
        reached,
        foregone,
    )


def test_prepare_carries_only_bounded_adjacent_working_causal_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organism, runtime, _native = _restore(monkeypatch)
    genuine = runtime.prepare(_Source())
    runtime.pending = None
    first = ("01" * 16, "02" * 16, 0, "7")
    second = ("02" * 16, "03" * 16, 0, "5")
    runtime.prepare_result_override = replace(
        genuine,
        working_causal_continuations=[(first, second)],
        settled_working_frontier=[second],
    )

    prepared = organism.prepare(_Source())

    assert prepared.working_causal_continuations == (
        (
            (first[0], first[1], first[2], 7),
            (second[0], second[1], second[2], 5),
        ),
    )
    assert prepared.settled_working_frontier == (
        (second[0], second[1], second[2], 5),
    )


def test_public_constructor_and_non_fixed_tokens_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TypeError, match="created by cold restore"):
        boundary.NativeResidentOrganism()

    organism, _runtime, _native = _restore(monkeypatch)
    with pytest.raises(ValueError, match="exactly 32 immutable bytes"):
        organism.commit(b"short")
