"""Concrete Python boundary for one native resident Guala organism.

The native object is the sole active and pending-state authority.  Python
retains only that object and returns fixed prepare receipts; it never carries
prepared organism bytes or a second materialized-fabric state.
"""

from __future__ import annotations

import hashlib
import importlib
import sys
from dataclasses import dataclass
from typing import Protocol


RUNTIME_SCHEMA = "guala.native.resident_organism_runtime.v3"
OBSERVATION_SCHEMA = "guala.native.resident_organism_observation.v3"
PREPARE_SCHEMA = "guala.native.resident_organism_prepare.v3"

DirectedPhysicalTransferEvidence = tuple[str, str, int, int]
TimedDirectedPhysicalTransferEvidence = tuple[int, DirectedPhysicalTransferEvidence]
ExactRationalEvidence = tuple[int, int]
LocalAffectiveGradientSettlementEvidence = tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    ExactRationalEvidence,
    ExactRationalEvidence,
    ExactRationalEvidence,
]
AffectiveBalanceTrajectoryEvidence = tuple[
    str,
    int,
    int,
    TimedDirectedPhysicalTransferEvidence | None,
    TimedDirectedPhysicalTransferEvidence | None,
    LocalAffectiveGradientSettlementEvidence | None,
]
LocalizedFluidChemistryEvidence = tuple[
    str,
    int,
    int,
    int,
    tuple[int, ExactRationalEvidence, int, int, int, int, int],
    tuple[int, int, int, int, int, int, int, int],
    tuple[
        tuple[ExactRationalEvidence, ExactRationalEvidence, ExactRationalEvidence],
        tuple[ExactRationalEvidence, ExactRationalEvidence, ExactRationalEvidence],
        ExactRationalEvidence,
    ],
]

_FACTORY_AUTHORITY = object()


class NativeJointSourceView(Protocol):
    """Annotation only; the native prepare method enforces source type."""

    @property
    def port_count(self) -> int: ...


class NativeResidentObservationView(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def identity(self) -> str: ...

    @property
    def organism_tick(self) -> int: ...

    @property
    def fabric_generation(self) -> int: ...

    @property
    def mounted_generation(self) -> int: ...

    @property
    def state_bytes(self) -> int: ...

    @property
    def state_sha256(self) -> str: ...

    @property
    def fabric_bytes(self) -> int: ...

    @property
    def fabric_sha256(self) -> str: ...

    @property
    def joint_field_count(self) -> int: ...

    @property
    def joint_neuron_count(self) -> int: ...

    @property
    def complete_neuron_count(self) -> int: ...

    @property
    def developmental_resting_neuron_count(self) -> int: ...

    @property
    def physically_transitioned_neuron_count(self) -> int: ...

    @property
    def metabolically_perturbed_body_receptor_count(self) -> int: ...

    @property
    def cold_restore_authentication_count(self) -> int: ...

    @property
    def cold_restore_decode_count(self) -> int: ...

    @property
    def cold_restore_rebuilt_field_count(self) -> int: ...

    @property
    def mounted_step_completed(self) -> bool: ...

    @property
    def physical_transition_claimed(self) -> bool: ...

    @property
    def cognitive_formation_claimed(self) -> bool: ...

    @property
    def cognitive_ordinal(self) -> int: ...

    @property
    def cognitive_trace_count(self) -> int: ...

    @property
    def cognitive_mosaic_count(self) -> int: ...

    @property
    def mosaic_of_mosaics_count(self) -> int: ...

    @property
    def physical_frontier_routes(
        self,
    ) -> list[tuple[str, int, int, str, int, int, int, int]]: ...

    @property
    def preceding_distinct_physical_frontier_routes(
        self,
    ) -> list[tuple[str, int, int, str, int, int, int, int]]: ...

    @property
    def reached_and_foregone_physical_frontier_routes(
        self,
    ) -> list[tuple[str, int, int, str, int, int, int, int]]: ...

    @property
    def working_causal_continuations(
        self,
    ) -> list[tuple[tuple[str, str, int, str], tuple[str, str, int, str]]]: ...

    @property
    def settled_working_frontier(
        self,
    ) -> list[tuple[str, str, int, str]]: ...

    @property
    def physical_prediction_alternatives(
        self,
    ) -> list[tuple[tuple[str, str, int, str], tuple[str, str, int, str]]]: ...

    @property
    def body_consequence_transfers(
        self,
    ) -> list[tuple[str, str, int, str]]: ...

    @property
    def affective_balance_trajectories(
        self,
    ) -> list[
        tuple[
            str,
            int,
            int,
            tuple[int, tuple[str, str, int, str]] | None,
            tuple[int, tuple[str, str, int, str]] | None,
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
        ]
    ]: ...

    @property
    def localized_fluid_chemistry(self) -> list[tuple[object, ...]]: ...

    @property
    def organic_mosaic_relations(
        self,
    ) -> list[
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
    ]: ...

    @property
    def formation_activation_count(self) -> int: ...

    @property
    def partial_cue_reassembly_count(self) -> int: ...

    @property
    def endogenous_partial_cue_reassembly_count(self) -> int: ...

    @property
    def python_callback_count(self) -> int: ...

    # Exact shared body-energy state. Local neuronal lanes keep their own
    # discrete reaction extents; only exact rational zeptojoules cross this
    # organism boundary.
    @property
    def available_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def spent_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def thermal_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def available_energy_capacity_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def dissipated_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def dissipation_capacity_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def separated_elementary_charges(self) -> int: ...

    @property
    def energy_exhausted(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ResidentContactGrowthEvidence:
    """Receipts for one prepared AUTHORED contact growth.

    Developmental authorship, not a sensory occurrence: it advances the
    organism tick and the fabric generation and nothing else.  The mounted
    joint generation is unchanged, and this boundary refuses any candidate
    that claims otherwise.
    """

    token: bytes
    token_hex: str
    predecessor_state_sha256: str
    prepared_state_sha256: str
    predecessor_organism_tick: int
    organism_tick: int
    predecessor_fabric_generation: int
    fabric_generation: int
    mounted_generation: int
    authored_contact_count: int


@dataclass(frozen=True, slots=True)
class ResidentPrepareEvidence:
    """Fixed receipt and causal evidence for one native pending candidate."""

    token: bytes
    token_hex: str
    predecessor_state_sha256: str
    prepared_state_sha256: str
    predecessor_organism_tick: int
    organism_tick: int
    predecessor_fabric_generation: int
    fabric_generation: int
    predecessor_mounted_generation: int
    mounted_generation: int
    predecessor_authentication_count: int
    predecessor_decode_count: int
    predecessor_rebuilt_field_count: int
    current_cohort_evaluation_count: int
    successor_seal_count: int
    dsf_delivery_count: int
    complete_neuron_fractal_count: int
    recurrent_complete_neuron_fractal_count: int
    physical_transition_claimed: bool
    cognitive_formation_claimed: bool
    cognitive_ordinal: int
    cognitive_trace_count: int
    cognitive_mosaic_count: int
    formation_activation_count: int
    partial_cue_reassembly_count: int
    endogenous_partial_cue_reassembly_count: int
    python_callback_count: int
    complete_neuron_count: int = 0
    developmental_resting_neuron_count: int = 0
    physically_transitioned_neuron_count: int = 0
    metabolically_perturbed_body_receptor_count: int = 0
    receptor_ingress_sense_counts: tuple[int, int, int, int, int, int] = (
        0,
        0,
        0,
        0,
        0,
        0,
    )
    receptor_ingress_changing_count: int = 0
    receptor_ingress_quiescent_count: int = 0
    motor_unit_recruitments: tuple[
        tuple[
            str,
            int,
            int,
            tuple[tuple[str, int, str, int, int, int], ...],
        ],
        ...,
    ] = ()
    articulatory_unit_recruitments: tuple[
        tuple[
            str,
            int,
            int,
            tuple[tuple[str, int, str, int, int, int], ...],
        ],
        ...,
    ] = ()
    emitted_neuron_fractals: tuple[
        tuple[str, tuple[tuple[str, int, bool, int, int], ...]], ...
    ] = ()
    active_physical_bonds: tuple[tuple[str, str, int], ...] = ()
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
        tuple[
            tuple[str, str, int, int],
            tuple[str, str, int, int],
        ],
        ...,
    ] = ()
    settled_working_frontier: tuple[tuple[str, str, int, int], ...] = ()
    physical_prediction_alternatives: tuple[
        tuple[
            tuple[str, str, int, int],
            tuple[str, str, int, int],
        ],
        ...,
    ] = ()
    body_consequence_transfers: tuple[tuple[str, str, int, int], ...] = ()
    affective_balance_trajectories: tuple[
        AffectiveBalanceTrajectoryEvidence, ...
    ] = ()
    localized_fluid_chemistry: tuple[LocalizedFluidChemistryEvidence, ...] = ()
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


def _native_core():
    return importlib.import_module("guala_core")


def _positive_integer(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > sys.maxsize
    ):
        raise ValueError(f"resident organism {label} must be a positive native integer")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"resident organism {label} is not a nonnegative integer")
    return value


def _signed_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"resident organism {label} is not an exact signed integer")
    return value


def _positive_decimal_integer(value: object, label: str) -> int:
    if (
        not isinstance(value, str)
        or not value
        or any(character not in "0123456789" for character in value)
        or value[0] == "0"
    ):
        raise RuntimeError(f"resident organism {label} is not a positive exact integer")
    return int(value)


def _nonnegative_decimal_integer(value: object, label: str) -> int:
    if (
        not isinstance(value, str)
        or not value
        or any(character not in "0123456789" for character in value)
        or (len(value) > 1 and value[0] == "0")
    ):
        raise RuntimeError(f"resident organism {label} is not a nonnegative exact integer")
    return int(value)


def _canonical_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"resident organism {label} is not canonical SHA-256")
    return value


def _canonical_lineage_hex(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"resident organism {label} is not canonical")
    return value


def _physical_frontier_route_evidence(
    value: object, label: str
) -> tuple[tuple[str, int, int, str, int, int, int, int], ...]:
    if not isinstance(value, list):
        raise RuntimeError(f"resident organism {label} changed format")
    routes: list[tuple[str, int, int, str, int, int, int, int]] = []
    seen: set[tuple[str, str, int]] = set()
    for raw_route in value:
        if not isinstance(raw_route, tuple) or len(raw_route) != 8:
            raise RuntimeError(f"resident organism {label} changed format")
        route = (
            _canonical_lineage_hex(raw_route[0], f"{label} seed lineage"),
            _nonnegative_integer(raw_route[1], f"{label} seed layer"),
            _nonnegative_integer(raw_route[2], f"{label} seed topology"),
            _canonical_lineage_hex(raw_route[3], f"{label} adjacent lineage"),
            _nonnegative_integer(raw_route[4], f"{label} adjacent layer"),
            _nonnegative_integer(raw_route[5], f"{label} adjacent topology"),
            _nonnegative_integer(raw_route[6], f"{label} parallel ordinal"),
            _signed_integer(raw_route[7], f"{label} outward carriers"),
        )
        if route[0] == route[3]:
            raise RuntimeError(f"resident organism {label} joined one lineage to itself")
        identity = (route[0], route[3], route[6])
        if identity in seen:
            raise RuntimeError(f"resident organism {label} repeated one route")
        seen.add(identity)
        routes.append(route)
    return tuple(routes)


def _directed_physical_transfer_evidence(
    value: object, label: str
) -> tuple[str, str, int, int]:
    if not isinstance(value, tuple) or len(value) != 4:
        raise RuntimeError(f"resident organism {label} changed format")
    carriers_text = value[3]
    if not isinstance(carriers_text, str) or not carriers_text.isdecimal():
        raise RuntimeError(f"resident organism {label} lost exact carriers")
    carriers = int(carriers_text)
    if carriers <= 0:
        raise RuntimeError(f"resident organism {label} carried no material")
    sender = _canonical_lineage_hex(value[0], f"{label} sender")
    receiver = _canonical_lineage_hex(value[1], f"{label} receiver")
    if sender == receiver:
        raise RuntimeError(f"resident organism {label} joined one lineage to itself")
    return (
        sender,
        receiver,
        _nonnegative_integer(value[2], f"{label} bond ordinal"),
        carriers,
    )


def _working_causal_continuation_evidence(
    value: object,
) -> tuple[
    tuple[
        tuple[str, str, int, int],
        tuple[str, str, int, int],
    ],
    ...,
]:
    if not isinstance(value, list) or len(value) > 1:
        raise RuntimeError("resident organism working continuation changed bounds")
    paths = []
    for raw_path in value:
        if not isinstance(raw_path, tuple) or len(raw_path) != 2:
            raise RuntimeError("resident organism working continuation changed format")
        first = _directed_physical_transfer_evidence(
            raw_path[0], "working continuation first transfer"
        )
        second = _directed_physical_transfer_evidence(
            raw_path[1], "working continuation second transfer"
        )
        if first[1] != second[0]:
            raise RuntimeError("resident organism working continuation is not adjacent")
        paths.append((first, second))
    return tuple(paths)


def _settled_working_frontier_evidence(
    value: object,
) -> tuple[tuple[str, str, int, int], ...]:
    if not isinstance(value, list) or len(value) > 1:
        raise RuntimeError("resident organism settled working frontier changed bounds")
    return tuple(
        _directed_physical_transfer_evidence(
            transfer, "settled working frontier transfer"
        )
        for transfer in value
    )


def _physical_prediction_alternative_evidence(
    value: object,
) -> tuple[
    tuple[
        tuple[str, str, int, int],
        tuple[str, str, int, int],
    ],
    ...,
]:
    if not isinstance(value, list) or len(value) not in (0, 2):
        raise RuntimeError("resident organism prediction alternatives changed bounds")
    paths = tuple(
        (
            _directed_physical_transfer_evidence(
                raw_path[0], "prediction alternative first transfer"
            ),
            _directed_physical_transfer_evidence(
                raw_path[1], "prediction alternative second transfer"
            ),
        )
        for raw_path in value
        if isinstance(raw_path, tuple) and len(raw_path) == 2
    )
    if len(paths) != len(value):
        raise RuntimeError("resident organism prediction alternative changed format")
    if paths and (
        paths[0][0][1] != paths[0][1][0]
        or paths[1][0][1] != paths[1][1][0]
        or paths[0][0][0] != paths[1][0][0]
        or paths[0][0][1] == paths[1][0][1]
        or paths[0][1][1] == paths[1][1][1]
    ):
        raise RuntimeError("resident organism prediction alternatives lost topology")
    return paths


def _body_consequence_transfer_evidence(
    value: object,
) -> tuple[tuple[str, str, int, int], ...]:
    if not isinstance(value, list) or len(value) > 1:
        raise RuntimeError("resident organism body consequence changed bounds")
    return tuple(
        _directed_physical_transfer_evidence(
            transfer, "body consequence transfer"
        )
        for transfer in value
    )


def _exact_rational_evidence(value: object, label: str) -> ExactRationalEvidence:
    if not isinstance(value, tuple) or len(value) != 2:
        raise RuntimeError(f"resident organism {label} changed format")
    numerator_text, denominator_text = value
    if (
        not isinstance(numerator_text, str)
        or not isinstance(denominator_text, str)
        or not numerator_text.removeprefix("-").isdecimal()
        or not denominator_text.isdecimal()
    ):
        raise RuntimeError(f"resident organism {label} lost exact rational")
    numerator = int(numerator_text)
    denominator = int(denominator_text)
    if denominator <= 0:
        raise RuntimeError(f"resident organism {label} has invalid denominator")
    return numerator, denominator


def _timed_directed_physical_transfer_evidence(
    value: object, label: str
) -> TimedDirectedPhysicalTransferEvidence:
    if not isinstance(value, tuple) or len(value) != 2:
        raise RuntimeError(f"resident organism {label} changed format")
    return (
        _nonnegative_integer(value[0], f"{label} cognitive ordinal"),
        _directed_physical_transfer_evidence(value[1], label),
    )


def _affective_balance_trajectory_evidence(
    value: object,
) -> tuple[AffectiveBalanceTrajectoryEvidence, ...]:
    if not isinstance(value, list):
        raise RuntimeError("resident organism affective-balance trajectory changed format")
    trajectories: list[AffectiveBalanceTrajectoryEvidence] = []
    for raw in value:
        if not isinstance(raw, tuple) or len(raw) != 6:
            raise RuntimeError(
                "resident organism affective-balance trajectory changed format"
            )
        lineage = _canonical_lineage_hex(raw[0], "affective-balance lineage")
        layer = _nonnegative_integer(raw[1], "affective-balance layer")
        topology = _nonnegative_integer(raw[2], "affective-balance topology")
        if layer != 10:
            raise RuntimeError("resident organism affective-balance cell left layer 10")
        association = (
            None
            if raw[3] is None
            else _timed_directed_physical_transfer_evidence(
                raw[3], "affective-balance association influence"
            )
        )
        body = (
            None
            if raw[4] is None
            else _timed_directed_physical_transfer_evidence(
                raw[4], "affective-balance body influence"
            )
        )
        for influence in (association, body):
            if influence is not None and lineage not in influence[1][:2]:
                raise RuntimeError(
                    "resident organism affective-balance influence missed its cell"
                )
        gradient = None
        if raw[5] is not None:
            if not isinstance(raw[5], tuple) or len(raw[5]) != 10:
                raise RuntimeError(
                    "resident organism affective-balance gradient changed format"
                )
            gradient = (
                _nonnegative_integer(raw[5][0], "affective-balance gradient ordinal"),
                _signed_integer(raw[5][1], "affective-balance predecessor charge"),
                _signed_integer(raw[5][2], "affective-balance post-gradient charge"),
                _signed_integer(raw[5][3], "affective-balance successor charge"),
                _signed_integer(raw[5][4], "affective-balance returned carriers"),
                _signed_integer(raw[5][5], "affective-balance pumped carriers"),
                _signed_integer(raw[5][6], "affective-balance remaining charge"),
                _exact_rational_evidence(raw[5][7], "affective-balance gradient work"),
                _exact_rational_evidence(
                    raw[5][8], "affective-balance environment delivery"
                ),
                _exact_rational_evidence(raw[5][9], "affective-balance heat export"),
            )
        trajectories.append((lineage, layer, topology, association, body, gradient))
    if tuple(item[0] for item in trajectories) != tuple(
        sorted({item[0] for item in trajectories})
    ):
        raise RuntimeError("resident organism affective-balance trajectories are not canonical")
    return tuple(trajectories)


def _localized_fluid_chemistry_evidence(
    value: object,
) -> tuple[LocalizedFluidChemistryEvidence, ...]:
    if not isinstance(value, list) or len(value) > 1:
        raise RuntimeError("resident organism localized fluid chemistry changed format")
    settlements: list[LocalizedFluidChemistryEvidence] = []
    for raw in value:
        if not isinstance(raw, tuple) or len(raw) != 7:
            raise RuntimeError("resident organism localized fluid chemistry changed format")
        lineage = _canonical_lineage_hex(raw[0], "localized fluid target lineage")
        layer = _nonnegative_integer(raw[1], "localized fluid target layer")
        topology = _nonnegative_integer(raw[2], "localized fluid target topology")
        ordinal = _positive_integer(raw[3], "localized fluid cognitive ordinal")
        contact = raw[4]
        carrier = raw[5]
        reservoir = raw[6]
        if not isinstance(contact, tuple) or len(contact) != 7:
            raise RuntimeError("resident organism localized fluid contact changed format")
        contact_evidence = (
            _positive_integer(contact[0], "localized fluid interval"),
            _exact_rational_evidence(contact[1], "localized fluid contact power"),
            _positive_integer(contact[2], "localized fluid reached count"),
            _positive_integer(contact[3], "localized fluid changed reached count"),
            _nonnegative_integer(contact[4], "localized fluid unchanged unreached count"),
            _nonnegative_integer(
                contact[5], "localized fluid unchanged developmental resting count"
            ),
            _nonnegative_integer(contact[6], "localized fluid changed unreached count"),
        )
        if contact_evidence[3] > contact_evidence[2] or contact_evidence[6] != 0:
            raise RuntimeError("resident organism localized fluid locality was not preserved")
        if not isinstance(carrier, tuple) or len(carrier) != 8:
            raise RuntimeError("resident organism localized fluid carrier changed format")
        carrier_evidence = (
            _signed_integer(carrier[0], "localized fluid predecessor charge"),
            _signed_integer(carrier[1], "localized fluid successor charge"),
            _nonnegative_decimal_integer(carrier[2], "localized fluid predecessor intracellular"),
            _nonnegative_decimal_integer(carrier[3], "localized fluid predecessor extracellular"),
            _nonnegative_decimal_integer(carrier[4], "localized fluid successor intracellular"),
            _nonnegative_decimal_integer(carrier[5], "localized fluid successor extracellular"),
            _signed_integer(carrier[6], "localized fluid returned carriers"),
            _signed_integer(carrier[7], "localized fluid pumped carriers"),
        )
        if carrier_evidence[2] + carrier_evidence[3] != carrier_evidence[4] + carrier_evidence[5]:
            raise RuntimeError("resident organism localized fluid carrier material changed")
        if not isinstance(reservoir, tuple) or len(reservoir) != 3:
            raise RuntimeError("resident organism localized fluid reservoir changed format")
        reservoir_states: list[
            tuple[ExactRationalEvidence, ExactRationalEvidence, ExactRationalEvidence]
        ] = []
        for index, state in enumerate(reservoir[:2]):
            if not isinstance(state, tuple) or len(state) != 3:
                raise RuntimeError("resident organism localized fluid reservoir changed format")
            reservoir_states.append(
                (
                    _exact_rational_evidence(state[0], f"localized fluid reservoir {index} available"),
                    _exact_rational_evidence(state[1], f"localized fluid reservoir {index} spent"),
                    _exact_rational_evidence(state[2], f"localized fluid reservoir {index} thermal"),
                )
            )
        settlements.append(
            (
                lineage,
                layer,
                topology,
                ordinal,
                contact_evidence,
                carrier_evidence,
                (
                    reservoir_states[0],
                    reservoir_states[1],
                    _exact_rational_evidence(reservoir[2], "localized fluid gradient work"),
                ),
            )
        )
    return tuple(settlements)


def _validated_causal_intervals(
    maximum_causal_intervals: object,
) -> list[tuple[int, int]]:
    """Validate caller-authored maximum causal intervals.

    One exact positive rational ``(numerator, denominator)`` per source
    occurrence, in exact occurrence order.  Every value is authored by the
    caller as independent environment/anatomy authority; nothing is defaulted
    or derived here.
    """

    if not isinstance(maximum_causal_intervals, (tuple, list)) or not (
        maximum_causal_intervals
    ):
        raise ValueError(
            "resident organism admission requires one authored maximum causal "
            "interval per source occurrence"
        )
    validated: list[tuple[int, int]] = []
    for index, interval in enumerate(maximum_causal_intervals):
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise TypeError(
                f"authored admission {index} must be (numerator, denominator)"
            )
        numerator, denominator = interval
        if (
            isinstance(numerator, bool)
            or isinstance(denominator, bool)
            or not isinstance(numerator, int)
            or not isinstance(denominator, int)
        ):
            raise TypeError(
                f"authored admission {index} must carry exact integers"
            )
        if denominator == 0:
            raise ValueError(f"authored admission {index} has a zero denominator")
        if numerator * denominator <= 0:
            raise ValueError(
                f"authored admission {index} is not a positive causal interval"
            )
        validated.append((numerator, denominator))
    return validated


def _exact_token(value: object) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("resident organism token must be exactly 32 immutable bytes")
    return value


def _concrete_class(core: object, name: str) -> type:
    candidate = getattr(core, name, None)
    if not isinstance(candidate, type):
        raise RuntimeError(f"guala_core does not expose concrete {name}")
    return candidate


def _validate_budget(
    max_envelope_bytes: object,
    max_fabric_bytes: object,
    max_logical_peak_bytes: object,
) -> tuple[int, int, int]:
    envelope = _positive_integer(max_envelope_bytes, "envelope budget")
    fabric = _positive_integer(max_fabric_bytes, "fabric budget")
    logical = _positive_integer(max_logical_peak_bytes, "logical peak budget")
    if fabric >= envelope:
        raise ValueError(
            "resident organism fabric budget must fit inside its envelope budget"
        )
    if logical <= 2 * envelope:
        raise ValueError(
            "resident organism logical peak budget must retain two envelopes and workspace"
        )
    return envelope, fabric, logical


def _observation_signature(
    observation: NativeResidentObservationView,
) -> tuple[object, ...]:
    return (
        observation.identity,
        observation.organism_tick,
        observation.fabric_generation,
        observation.mounted_generation,
        observation.state_bytes,
        observation.state_sha256,
        observation.fabric_bytes,
        observation.fabric_sha256,
        observation.joint_field_count,
        observation.joint_neuron_count,
        observation.complete_neuron_count,
        observation.developmental_resting_neuron_count,
        observation.cognitive_ordinal,
        observation.cognitive_trace_count,
        observation.cognitive_mosaic_count,
        tuple(observation.physical_frontier_routes),
        tuple(observation.preceding_distinct_physical_frontier_routes),
        tuple(observation.reached_and_foregone_physical_frontier_routes),
        tuple(observation.working_causal_continuations),
        tuple(observation.settled_working_frontier),
        tuple(observation.physical_prediction_alternatives),
        tuple(observation.body_consequence_transfers),
        tuple(observation.affective_balance_trajectories),
        tuple(observation.localized_fluid_chemistry),
        tuple(
            (
                tuple(receipts),
                tuple(lineages),
                tuple(bonds),
                structure_receipt,
                tuple(ordered_paths),
                tuple(ordered_path_relations),
            )
            for (
                receipts,
                lineages,
                bonds,
                structure_receipt,
                ordered_paths,
                ordered_path_relations,
            ) in observation.organic_mosaic_relations
        ),
        observation.partial_cue_reassembly_count,
        observation.endogenous_partial_cue_reassembly_count,
    )


class NativeResidentOrganism:
    """Factory-only handle retaining exactly one concrete native runtime."""

    __slots__ = (
        "__runtime",
        "__runtime_type",
        "__observation_type",
        "__prepare_type",
    )

    def __new__(cls, authority: object = None, *args: object, **kwargs: object):
        del args, kwargs
        if authority is not _FACTORY_AUTHORITY:
            raise TypeError(
                "native resident organism must be created by cold restore"
            )
        return super().__new__(cls)

    def __init__(
        self,
        authority: object,
        runtime: object,
        runtime_type: type,
        observation_type: type,
        prepare_type: type,
    ) -> None:
        if authority is not _FACTORY_AUTHORITY or not isinstance(
            runtime, runtime_type
        ):
            raise TypeError("native resident organism runtime is not concrete")
        self.__runtime = runtime
        self.__runtime_type = runtime_type
        self.__observation_type = observation_type
        self.__prepare_type = prepare_type

    def _require_observation(
        self, candidate: object
    ) -> NativeResidentObservationView:
        if not isinstance(candidate, self.__observation_type):
            raise TypeError(
                "resident organism operation returned a structural impostor"
            )
        if candidate.schema != OBSERVATION_SCHEMA:
            raise RuntimeError("resident organism observation schema changed")
        if not isinstance(candidate.identity, str) or not candidate.identity:
            raise RuntimeError("resident organism identity is absent")
        organism_tick = _nonnegative_integer(
            candidate.organism_tick, "organism tick"
        )
        fabric_generation = _nonnegative_integer(
            candidate.fabric_generation, "fabric generation"
        )
        mounted_generation = _nonnegative_integer(
            candidate.mounted_generation, "mounted generation"
        )
        del organism_tick, fabric_generation, mounted_generation
        state_bytes = _positive_integer(candidate.state_bytes, "state bytes")
        fabric_bytes = _positive_integer(candidate.fabric_bytes, "fabric bytes")
        if fabric_bytes >= state_bytes:
            raise RuntimeError("resident organism fabric does not fit its envelope")
        _canonical_sha256(candidate.state_sha256, "state receipt")
        _canonical_sha256(candidate.fabric_sha256, "fabric receipt")
        _nonnegative_integer(
            candidate.joint_field_count, "joint field count"
        )
        _nonnegative_integer(
            candidate.joint_neuron_count, "joint neuron count"
        )
        if (
            _nonnegative_integer(
                candidate.cold_restore_authentication_count,
                "cold authentication count",
            )
            != 1
            or _nonnegative_integer(
                candidate.cold_restore_decode_count, "cold decode count"
            )
            != 1
        ):
            raise RuntimeError("resident organism did not cold restore exactly once")
        _nonnegative_integer(
            candidate.cold_restore_rebuilt_field_count,
            "cold rebuilt field count",
        )
        cognitive_ordinal = _nonnegative_integer(
            candidate.cognitive_ordinal, "cognitive ordinal"
        )
        cognitive_trace_count = _nonnegative_integer(
            candidate.cognitive_trace_count, "cognitive trace count"
        )
        cognitive_mosaic_count = _nonnegative_integer(
            candidate.cognitive_mosaic_count, "cognitive mosaic count"
        )
        mosaic_of_mosaics_count = _nonnegative_integer(
            candidate.mosaic_of_mosaics_count, "mosaic of mosaics count"
        )
        del mosaic_of_mosaics_count
        activation_count = _nonnegative_integer(
            candidate.formation_activation_count,
            "formation activation count",
        )
        partial_count = _nonnegative_integer(
            candidate.partial_cue_reassembly_count,
            "partial cue reassembly count",
        )
        endogenous_partial_count = _nonnegative_integer(
            candidate.endogenous_partial_cue_reassembly_count,
            "endogenous partial cue reassembly count",
        )
        complete_count = _nonnegative_integer(
            candidate.complete_neuron_count, "complete neuron count"
        )
        resting_count = _nonnegative_integer(
            candidate.developmental_resting_neuron_count,
            "developmental resting neuron count",
        )
        transitioned_count = _nonnegative_integer(
            candidate.physically_transitioned_neuron_count,
            "physically transitioned neuron count",
        )
        metabolic_body_count = _nonnegative_integer(
            candidate.metabolically_perturbed_body_receptor_count,
            "metabolically perturbed body receptor count",
        )
        del cognitive_ordinal, cognitive_trace_count, complete_count, resting_count
        if (
            not isinstance(candidate.mounted_step_completed, bool)
            or not isinstance(candidate.physical_transition_claimed, bool)
            or not isinstance(candidate.cognitive_formation_claimed, bool)
            or candidate.physical_transition_claimed
            != (transitioned_count > 0)
            or metabolic_body_count > transitioned_count
            or candidate.python_callback_count != 0
            or endogenous_partial_count > partial_count
        ):
            raise RuntimeError("resident organism observation made a false claim")
        if not candidate.mounted_step_completed and (
            candidate.physical_transition_claimed
            or candidate.cognitive_formation_claimed
            or activation_count != 0
            or partial_count != 0
            or transitioned_count != 0
        ):
            raise RuntimeError(
                "resident organism cold observation claimed step effects"
            )
        del cognitive_mosaic_count
        return candidate

    def readiness(self) -> NativeResidentObservationView:
        """Observe only the active native state."""

        if not isinstance(self.__runtime, self.__runtime_type):
            raise RuntimeError("resident organism runtime identity changed")
        return self._require_observation(self.__runtime.readiness())

    def save(self) -> bytes:
        """Seal only the active GLORUN envelope."""

        observation = self.readiness()
        state = self.__runtime.save()
        if (
            not isinstance(state, bytes)
            or not state.startswith(b"GLORUN01")
            or len(state) != observation.state_bytes
            or hashlib.sha256(state).hexdigest() != observation.state_sha256
        ):
            raise RuntimeError("resident organism save changed active custody")
        return state

    def observe_retained_formations(self) -> tuple[tuple[tuple[str, ...], int], ...]:
        """Read-only structure of the retained distributed formations.

        One entry per admitted mosaic as ``(member_lineage_hexes,
        recurrence_bond_count)``.  Structure only — no recognition, recall,
        meaning, or capital — and reading advances nothing (verified against
        the active state receipt).
        """

        before = self.readiness()
        formations = self.__runtime.observe_retained_formations()
        validated = []
        for members, bond_count in formations:
            lineages = tuple(str(lineage) for lineage in members)
            if len(lineages) < 3 or any(
                len(lineage) != 32 for lineage in lineages
            ):
                raise RuntimeError(
                    "retained formation observation is structurally invalid"
                )
            validated.append((lineages, _nonnegative_integer(
                bond_count, "recurrence bond count"
            )))
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("formation observation advanced the organism")
        return tuple(validated)

    def observe_reached_neuron_lineage_layers(
        self,
    ) -> tuple[tuple[str, int, bool], ...]:
        """Read reached lineage, developmental layer, and receptor anatomy."""

        before = self.readiness()
        observed = self.__runtime.observe_reached_neuron_lineage_layers()
        validated = []
        seen_lineages: set[str] = set()
        for lineage, layer, receptor in observed:
            lineage = str(lineage)
            layer = _nonnegative_integer(layer, "reached developmental layer")
            if (
                len(lineage) != 32
                or lineage in seen_lineages
                or not isinstance(receptor, bool)
            ):
                raise RuntimeError("reached lineage-layer observation is invalid")
            validated.append((lineage, layer, receptor))
            seen_lineages.add(lineage)
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("lineage-layer observation advanced the organism")
        return tuple(validated)

    def observe_retained_formation_structures(
        self,
    ) -> tuple[
        tuple[
            str,
            tuple[str, ...],
            tuple[tuple[str, str, int], ...],
            tuple[tuple[str, str, int], ...],
            int,
        ],
        ...,
    ]:
        """Read exact retained structure without assigning meaning."""

        before = self.readiness()
        observed = self.__runtime.observe_retained_formation_structures()
        validated = []
        for receipt, members, original_bonds, recurrence_bonds, reinforcements in observed:
            receipt = str(receipt)
            member_lineages = tuple(str(lineage) for lineage in members)
            if len(receipt) != 64 or len(member_lineages) < 3 or any(
                len(lineage) != 32 for lineage in member_lineages
            ):
                raise RuntimeError("retained formation structure is invalid")

            def bonds(values: object) -> tuple[tuple[str, str, int], ...]:
                canonical = []
                for left, right, ordinal in values:
                    left = str(left)
                    right = str(right)
                    ordinal = _nonnegative_integer(ordinal, "parallel bond ordinal")
                    if len(left) != 32 or len(right) != 32 or left >= right:
                        raise RuntimeError("retained formation bond is invalid")
                    canonical.append((left, right, ordinal))
                return tuple(canonical)

            validated.append(
                (
                    receipt,
                    member_lineages,
                    bonds(original_bonds),
                    bonds(recurrence_bonds),
                    _nonnegative_integer(reinforcements, "reinforcement count"),
                )
            )
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("formation structure observation advanced the organism")
        return tuple(validated)

    def observe_retained_formation_recurrence_cues(
        self,
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Read the latest proper physical cue for each retained formation."""

        before = self.readiness()
        observed = self.__runtime.observe_retained_formation_recurrence_cues()
        validated = []
        for receipt, cue in observed:
            receipt = str(receipt)
            cue_lineages = tuple(str(lineage) for lineage in cue)
            if (
                len(receipt) != 64
                or not cue_lineages
                or any(len(lineage) != 32 for lineage in cue_lineages)
            ):
                raise RuntimeError("retained formation recurrence cue is invalid")
            validated.append((receipt, cue_lineages))
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("formation cue observation advanced the organism")
        return tuple(validated)

    def navigate_hippocampal(self, lineage_hex: str) -> None:
        """Refused: the hippocampal episode archive is retired.

        This walked an archived posting chain and returned episode addresses.
        The archive is no longer written or read: it never carried
        recognition, recall or meaning, and it grew by roughly 893 files per
        recognition.  Her memories are the retained formations in her body —
        read those with :meth:`observe_retained_formations`.
        """

        return self.__runtime.navigate_hippocampal(lineage_hex)

    def prepare(self, source: NativeJointSourceView) -> ResidentPrepareEvidence:
        """Prepare one native candidate and return receipts, never state bytes.

        The bare source path remains severed by the mandatory-admission law:
        the native runtime refuses it because no occurrence admission is
        supplied.  Use :meth:`prepare_admitted`.
        """

        source_port_count = _nonnegative_integer(
            getattr(source, "port_count", None), "source port count"
        )
        active_before = self.readiness()
        candidate = self.__runtime.prepare(source)
        return self._validated_prepare_evidence(
            candidate, source_port_count, active_before
        )

    def prepare_admitted(
        self,
        source: NativeJointSourceView,
        maximum_causal_intervals: object,
    ) -> ResidentPrepareEvidence:
        """Prepare one admitted native candidate and return receipts.

        ``maximum_causal_intervals`` carries one caller-authored maximum
        causal interval ``(numerator, denominator)`` in source-time units per
        source occurrence, in exact occurrence order.  It is independent
        environment/anatomy authority; this boundary never derives it from the
        occurrence.

        An admitted transition requires NO durable cold-custody directory and
        writes no file of its own: what a lesson changes is her body, and the
        caller persists that body once per lesson.
        """

        source_port_count = _nonnegative_integer(
            getattr(source, "port_count", None), "source port count"
        )
        intervals = _validated_causal_intervals(maximum_causal_intervals)
        active_before = self.readiness()
        candidate = self.__runtime.prepare_admitted(source, intervals)
        return self._validated_prepare_evidence(
            candidate, source_port_count, active_before
        )

    def prepare_vestibular_tick(
        self,
        predecessor_heading_millidegrees: int,
        signed_body_motion_millidegrees: int,
    ) -> ResidentPrepareEvidence:
        """Prepare one native one-millisecond body-and-balance successor."""

        predecessor_heading = _nonnegative_integer(
            predecessor_heading_millidegrees,
            "vestibular predecessor heading",
        )
        if predecessor_heading >= 360_000:
            raise ValueError("vestibular predecessor heading must be below 360000")
        if (
            not isinstance(signed_body_motion_millidegrees, int)
            or isinstance(signed_body_motion_millidegrees, bool)
            or not -(1 << 31)
            <= signed_body_motion_millidegrees
            < (1 << 31)
        ):
            raise TypeError("vestibular signed yaw step must be a signed 32-bit integer")
        active_before = self.readiness()
        candidate = self.__runtime.prepare_vestibular_tick(
            predecessor_heading,
            signed_body_motion_millidegrees,
        )
        return self._validated_prepare_evidence(candidate, 1, active_before)

    def prepare_vestibular_trajectory(
        self,
        predecessor_heading_millidegrees: int,
        signed_body_motion_millidegrees: tuple[int, ...],
    ) -> ResidentPrepareEvidence:
        """Prepare ordered one-millisecond balance intervals and seal once."""

        predecessor_heading = _nonnegative_integer(
            predecessor_heading_millidegrees,
            "vestibular predecessor heading",
        )
        if predecessor_heading >= 360_000:
            raise ValueError("vestibular predecessor heading must be below 360000")
        if (
            not isinstance(signed_body_motion_millidegrees, tuple)
            or not signed_body_motion_millidegrees
        ):
            raise TypeError("vestibular trajectory must be a nonempty tuple")
        if any(
            not isinstance(step, int)
            or isinstance(step, bool)
            or not -(1 << 31) <= step < (1 << 31)
            for step in signed_body_motion_millidegrees
        ):
            raise TypeError(
                "vestibular trajectory steps must be signed 32-bit integers"
            )
        active_before = self.readiness()
        candidate = self.__runtime.prepare_vestibular_trajectory(
            predecessor_heading,
            list(signed_body_motion_millidegrees),
        )
        return self._validated_prepare_evidence(
            candidate,
            1,
            active_before,
            causal_interval_count=len(signed_body_motion_millidegrees),
        )

    def _validated_prepare_evidence(
        self,
        candidate: object,
        source_port_count: int,
        active_before: NativeResidentObservationView,
        *,
        causal_interval_count: int = 1,
    ) -> ResidentPrepareEvidence:
        if not isinstance(candidate, self.__prepare_type):
            raise TypeError("resident organism prepare returned a structural impostor")
        if candidate.schema != PREPARE_SCHEMA:
            raise RuntimeError("resident organism prepare schema changed")
        token = candidate.token
        if (
            not isinstance(token, bytes)
            or len(token) != 32
            or candidate.token_hex != token.hex()
        ):
            raise RuntimeError("resident organism prepare token changed format")
        predecessor_state_sha256 = _canonical_sha256(
            candidate.predecessor_state_sha256, "predecessor state receipt"
        )
        prepared_state_sha256 = _canonical_sha256(
            candidate.prepared_state_sha256, "prepared state receipt"
        )
        predecessor_organism_tick = _nonnegative_integer(
            candidate.predecessor_organism_tick, "predecessor organism tick"
        )
        organism_tick = _nonnegative_integer(
            candidate.organism_tick, "prepared organism tick"
        )
        predecessor_fabric_generation = _nonnegative_integer(
            candidate.predecessor_fabric_generation,
            "predecessor fabric generation",
        )
        fabric_generation = _nonnegative_integer(
            candidate.fabric_generation, "prepared fabric generation"
        )
        predecessor_mounted_generation = _nonnegative_integer(
            candidate.predecessor_mounted_generation,
            "predecessor mounted generation",
        )
        mounted_generation = _nonnegative_integer(
            candidate.mounted_generation, "prepared mounted generation"
        )
        predecessor_authentication_count = _nonnegative_integer(
            candidate.predecessor_authentication_count,
            "prepare predecessor authentication count",
        )
        predecessor_decode_count = _nonnegative_integer(
            candidate.predecessor_decode_count,
            "prepare predecessor decode count",
        )
        predecessor_rebuilt_field_count = _nonnegative_integer(
            candidate.predecessor_rebuilt_field_count,
            "prepare predecessor rebuilt field count",
        )
        current_cohort_evaluation_count = _nonnegative_integer(
            candidate.current_cohort_evaluation_count,
            "current cohort evaluation count",
        )
        successor_seal_count = _nonnegative_integer(
            candidate.successor_seal_count, "successor seal count"
        )
        dsf_delivery_count = _nonnegative_integer(
            candidate.dsf_delivery_count,
            "DSF delivery count",
        )
        complete_neuron_fractal_count = _nonnegative_integer(
            candidate.complete_neuron_fractal_count,
            "complete-neuron fractal count",
        )
        raw_neuron_fractals = candidate.emitted_neuron_fractals
        if not isinstance(raw_neuron_fractals, list):
            raise RuntimeError("neuronal fractal evidence changed format")
        emitted_neuron_fractals: list[
            tuple[str, tuple[tuple[str, int, bool, int, int], ...]]
        ] = []
        emitted_lineages: set[str] = set()
        retained_coordinates = {
            "psi-winding",
            "gate-open-population",
            "plastic-rest-length",
            "dna-expressed-product",
            "receptor-quantum-residue",
        }
        for raw_fractal in raw_neuron_fractals:
            if not isinstance(raw_fractal, tuple) or len(raw_fractal) != 2:
                raise RuntimeError("neuronal fractal evidence changed format")
            lineage = _canonical_lineage_hex(raw_fractal[0], "fractal lineage")
            if lineage in emitted_lineages:
                raise RuntimeError("neuronal fractal lineage was emitted twice")
            emitted_lineages.add(lineage)
            raw_entries = raw_fractal[1]
            if not isinstance(raw_entries, list) or not raw_entries:
                raise RuntimeError("neuronal fractal has no sparse retained delta")
            entries: list[tuple[str, int, bool, int, int]] = []
            seen_coordinates: set[tuple[str, int]] = set()
            for raw_entry in raw_entries:
                if not isinstance(raw_entry, tuple) or len(raw_entry) != 5:
                    raise RuntimeError("neuronal fractal entry changed format")
                coordinate = raw_entry[0]
                if coordinate not in retained_coordinates:
                    raise RuntimeError("neuronal fractal carried a transient coordinate")
                index = _nonnegative_integer(raw_entry[1], "fractal coordinate index")
                if coordinate != "psi-winding" and index != 0:
                    raise RuntimeError("scalar fractal coordinate carried an index")
                key = (coordinate, index)
                if key in seen_coordinates:
                    raise RuntimeError("neuronal fractal repeated a coordinate")
                seen_coordinates.add(key)
                negative = raw_entry[2]
                if not isinstance(negative, bool):
                    raise RuntimeError("neuronal fractal sign changed format")
                magnitude = _positive_decimal_integer(
                    raw_entry[3], "fractal delta magnitude"
                )
                denominator = _positive_decimal_integer(
                    raw_entry[4], "fractal delta denominator"
                )
                entries.append(
                    (coordinate, index, negative, magnitude, denominator)
                )
            emitted_neuron_fractals.append((lineage, tuple(entries)))
        if len(emitted_neuron_fractals) != complete_neuron_fractal_count:
            raise RuntimeError("neuronal fractal count lost its exact evidence")
        raw_active_physical_bonds = candidate.active_physical_bonds
        if not isinstance(raw_active_physical_bonds, list):
            raise RuntimeError("active physical-bond evidence changed format")
        active_physical_bonds: list[tuple[str, str, int]] = []
        for raw_bond in raw_active_physical_bonds:
            if not isinstance(raw_bond, tuple) or len(raw_bond) != 3:
                raise RuntimeError("active physical-bond evidence changed format")
            active_physical_bonds.append(
                (
                    _canonical_lineage_hex(raw_bond[0], "active bond left lineage"),
                    _canonical_lineage_hex(raw_bond[1], "active bond right lineage"),
                    _nonnegative_integer(raw_bond[2], "active bond parallel ordinal"),
                )
            )
        physical_frontier_routes = _physical_frontier_route_evidence(
            candidate.physical_frontier_routes,
            "physical frontier route evidence",
        )
        preceding_distinct_physical_frontier_routes = (
            _physical_frontier_route_evidence(
                candidate.preceding_distinct_physical_frontier_routes,
                "preceding distinct physical frontier route evidence",
            )
        )
        reached_and_foregone_physical_frontier_routes = (
            _physical_frontier_route_evidence(
                candidate.reached_and_foregone_physical_frontier_routes,
                "reached and foregone physical frontier route evidence",
            )
        )
        if reached_and_foregone_physical_frontier_routes and not (
            len(reached_and_foregone_physical_frontier_routes) > 1
            and any(
                route[7] == 0
                for route in reached_and_foregone_physical_frontier_routes
            )
            and any(
                route[7] != 0
                for route in reached_and_foregone_physical_frontier_routes
            )
        ):
            raise RuntimeError(
                "reached and foregone frontier evidence lost its exact distinction"
            )
        working_causal_continuations = _working_causal_continuation_evidence(
            candidate.working_causal_continuations
        )
        settled_working_frontier = _settled_working_frontier_evidence(
            candidate.settled_working_frontier
        )
        physical_prediction_alternatives = (
            _physical_prediction_alternative_evidence(
                candidate.physical_prediction_alternatives
            )
        )
        body_consequence_transfers = _body_consequence_transfer_evidence(
            candidate.body_consequence_transfers
        )
        affective_balance_trajectories = _affective_balance_trajectory_evidence(
            candidate.affective_balance_trajectories
        )
        localized_fluid_chemistry = _localized_fluid_chemistry_evidence(
            candidate.localized_fluid_chemistry
        )
        raw_organic_mosaic_relations = candidate.organic_mosaic_relations
        if not isinstance(raw_organic_mosaic_relations, list):
            raise RuntimeError("organic mosaic-relation evidence changed format")
        organic_mosaic_relations: list[
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
            ]
        ] = []
        for raw_relation in raw_organic_mosaic_relations:
            if not isinstance(raw_relation, tuple) or len(raw_relation) != 6:
                raise RuntimeError("organic mosaic relation changed format")
            (
                raw_receipts,
                raw_lineages,
                raw_bonds,
                raw_structure_receipt,
                raw_ordered_paths,
                raw_ordered_path_relations,
            ) = raw_relation
            if (
                not isinstance(raw_receipts, list)
                or not isinstance(raw_lineages, list)
                or not isinstance(raw_bonds, list)
                or not isinstance(raw_ordered_paths, list)
                or not isinstance(raw_ordered_path_relations, list)
            ):
                raise RuntimeError("organic mosaic relation changed format")
            receipts = tuple(
                _canonical_sha256(value, "related formation receipt")
                for value in raw_receipts
            )
            shared_lineages = tuple(
                _canonical_lineage_hex(value, "shared mosaic lineage")
                for value in raw_lineages
            )
            relation_bonds = tuple(
                (
                    _canonical_lineage_hex(value[0], "relation bond left lineage"),
                    _canonical_lineage_hex(value[1], "relation bond right lineage"),
                    _nonnegative_integer(value[2], "relation bond parallel ordinal"),
                )
                for value in raw_bonds
                if isinstance(value, tuple) and len(value) == 3
            )
            structure_receipt = _canonical_sha256(
                raw_structure_receipt,
                "organic relation structural receipt",
            )
            ordered_paths: list[
                tuple[
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                ]
            ] = []
            for raw_path in raw_ordered_paths:
                if not isinstance(raw_path, tuple) or len(raw_path) != 2:
                    raise RuntimeError("ordered physical path changed format")
                transfers: list[tuple[str, str, int, int]] = []
                for raw_transfer in raw_path:
                    if not isinstance(raw_transfer, tuple) or len(raw_transfer) != 4:
                        raise RuntimeError("directed physical transfer changed format")
                    carriers_text = raw_transfer[3]
                    if (
                        not isinstance(carriers_text, str)
                        or not carriers_text.isdecimal()
                    ):
                        raise RuntimeError("directed physical transfer lost exact carriers")
                    carriers = int(carriers_text)
                    if carriers <= 0:
                        raise RuntimeError("directed physical transfer carried no material")
                    transfers.append(
                        (
                            _canonical_lineage_hex(raw_transfer[0], "transfer sender"),
                            _canonical_lineage_hex(raw_transfer[1], "transfer receiver"),
                            _nonnegative_integer(raw_transfer[2], "transfer bond ordinal"),
                            carriers,
                        )
                    )
                if transfers[0][1] != transfers[1][0]:
                    raise RuntimeError("ordered physical path is not causally continuous")
                ordered_paths.append((transfers[0], transfers[1]))
            ordered_path_relations: list[
                tuple[
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                    tuple[str, str, int, int],
                ]
            ] = []
            for raw_path_relation in raw_ordered_path_relations:
                if not isinstance(raw_path_relation, tuple) or len(raw_path_relation) != 4:
                    raise RuntimeError("ordered path relation changed format")
                transfers = []
                for raw_transfer in raw_path_relation:
                    if not isinstance(raw_transfer, tuple) or len(raw_transfer) != 4:
                        raise RuntimeError("directed physical transfer changed format")
                    carriers_text = raw_transfer[3]
                    if not isinstance(carriers_text, str) or not carriers_text.isdecimal():
                        raise RuntimeError("directed physical transfer lost exact carriers")
                    carriers = int(carriers_text)
                    if carriers <= 0:
                        raise RuntimeError("directed physical transfer carried no material")
                    transfers.append(
                        (
                            _canonical_lineage_hex(raw_transfer[0], "transfer sender"),
                            _canonical_lineage_hex(raw_transfer[1], "transfer receiver"),
                            _nonnegative_integer(raw_transfer[2], "transfer bond ordinal"),
                            carriers,
                        )
                    )
                if (
                    transfers[0][1] != transfers[1][0]
                    or transfers[2][1] != transfers[3][0]
                    or tuple(item[:3] for item in transfers[:2])
                    != tuple(item[:3] for item in transfers[2:])
                ):
                    raise RuntimeError("ordered path relation did not recur physically")
                ordered_path_relations.append(
                    (transfers[0], transfers[1], transfers[2], transfers[3])
                )
            if (
                len(relation_bonds) != len(raw_bonds)
                or len(receipts) < 2
                or tuple(sorted(set(receipts))) != receipts
                or tuple(sorted(set(shared_lineages))) != shared_lineages
                or tuple(sorted(set(relation_bonds))) != relation_bonds
                or (not shared_lineages and not relation_bonds)
            ):
                raise RuntimeError("organic mosaic relation is not canonical physical evidence")
            organic_mosaic_relations.append(
                (
                    receipts,
                    shared_lineages,
                    relation_bonds,
                    structure_receipt,
                    tuple(ordered_paths),
                    tuple(ordered_path_relations),
                )
            )
        recurrent_complete_neuron_fractal_count = _nonnegative_integer(
            candidate.recurrent_complete_neuron_fractal_count,
            "recurrent complete-neuron fractal count",
        )
        cognitive_ordinal = _nonnegative_integer(
            candidate.cognitive_ordinal, "cognitive ordinal"
        )
        cognitive_trace_count = _nonnegative_integer(
            candidate.cognitive_trace_count, "cognitive trace count"
        )
        cognitive_mosaic_count = _nonnegative_integer(
            candidate.cognitive_mosaic_count, "cognitive mosaic count"
        )
        formation_activation_count = _nonnegative_integer(
            candidate.formation_activation_count,
            "formation activation count",
        )
        partial_cue_reassembly_count = _nonnegative_integer(
            candidate.partial_cue_reassembly_count,
            "partial cue reassembly count",
        )
        endogenous_partial_cue_reassembly_count = _nonnegative_integer(
            candidate.endogenous_partial_cue_reassembly_count,
            "endogenous partial cue reassembly count",
        )
        complete_neuron_count = _nonnegative_integer(
            candidate.complete_neuron_count, "complete neuron count"
        )
        developmental_resting_neuron_count = _nonnegative_integer(
            candidate.developmental_resting_neuron_count,
            "developmental resting neuron count",
        )
        physically_transitioned_neuron_count = _nonnegative_integer(
            candidate.physically_transitioned_neuron_count,
            "physically transitioned neuron count",
        )
        metabolically_perturbed_body_receptor_count = _nonnegative_integer(
            candidate.metabolically_perturbed_body_receptor_count,
            "metabolically perturbed body receptor count",
        )
        raw_ingress_sense_counts = candidate.receptor_ingress_sense_counts
        if (
            not isinstance(raw_ingress_sense_counts, tuple)
            or len(raw_ingress_sense_counts) != 6
        ):
            raise RuntimeError("receptor ingress sense counts changed format")
        receptor_ingress_sense_counts = tuple(
            _nonnegative_integer(value, "receptor ingress sense count")
            for value in raw_ingress_sense_counts
        )
        receptor_ingress_changing_count = _nonnegative_integer(
            candidate.receptor_ingress_changing_count,
            "receptor ingress changing count",
        )
        receptor_ingress_quiescent_count = _nonnegative_integer(
            candidate.receptor_ingress_quiescent_count,
            "receptor ingress quiescent count",
        )
        if (
            sum(receptor_ingress_sense_counts) != source_port_count
            or receptor_ingress_changing_count
            + receptor_ingress_quiescent_count
            != source_port_count
        ):
            raise RuntimeError("receptor ingress observation lost source ports")
        raw_motor_recruitments = candidate.motor_unit_recruitments
        if not isinstance(raw_motor_recruitments, list):
            raise RuntimeError("motor-unit recruitments changed format")
        motor_unit_recruitments: list[
            tuple[
                str,
                int,
                int,
                tuple[tuple[str, int, str, int, int, int], ...],
            ]
        ] = []
        for raw in raw_motor_recruitments:
            if not isinstance(raw, tuple) or len(raw) != 4:
                raise RuntimeError("motor-unit recruitment changed format")
            lineage = _canonical_lineage_hex(raw[0], "motor-unit lineage")
            topology_index = _nonnegative_integer(
                raw[1], "motor-unit topology index"
            )
            outward_elementary_carriers = _positive_integer(
                raw[2], "motor-unit outward elementary carriers"
            )
            if not isinstance(raw[3], list) or not raw[3]:
                raise RuntimeError("motor-unit preparation transfers changed format")
            preparation_transfers: list[
                tuple[str, int, str, int, int, int]
            ] = []
            for transfer in raw[3]:
                if not isinstance(transfer, tuple) or len(transfer) != 6:
                    raise RuntimeError(
                        "motor-unit preparation transfer changed format"
                    )
                sender = _canonical_lineage_hex(
                    transfer[0], "motor preparation sender"
                )
                sender_layer = _nonnegative_integer(
                    transfer[1], "motor preparation sender layer"
                )
                receiver = _canonical_lineage_hex(
                    transfer[2], "motor preparation receiver"
                )
                receiver_layer = _nonnegative_integer(
                    transfer[3], "motor preparation receiver layer"
                )
                parallel_ordinal = _nonnegative_integer(
                    transfer[4], "motor preparation parallel ordinal"
                )
                transferred_whole_carriers = _positive_integer(
                    transfer[5], "motor preparation transferred whole carriers"
                )
                if (
                    sender == receiver
                    or not (
                        (
                            sender == lineage
                            and sender_layer == 12
                            and receiver_layer == 11
                        )
                        or (
                            receiver == lineage
                            and receiver_layer == 12
                            and sender_layer == 11
                        )
                    )
                ):
                    raise RuntimeError(
                        "motor-unit preparation is not an exact layer 11/layer 12 contact transfer"
                    )
                preparation_transfers.append(
                    (
                        sender,
                        sender_layer,
                        receiver,
                        receiver_layer,
                        parallel_ordinal,
                        transferred_whole_carriers,
                    )
                )
            motor_unit_recruitments.append(
                (
                    lineage,
                    topology_index,
                    outward_elementary_carriers,
                    tuple(preparation_transfers),
                )
            )
        # Older pure-Python boundary doubles carry no layer-13 observation;
        # absence is exactly an empty transient recruitment list. Native
        # production candidates expose the field explicitly.
        raw_articulatory_recruitments = getattr(
            candidate, "articulatory_unit_recruitments", []
        )
        if not isinstance(raw_articulatory_recruitments, list):
            raise RuntimeError("articulatory-unit recruitments changed format")
        articulatory_unit_recruitments: list[
            tuple[
                str,
                int,
                int,
                tuple[tuple[str, int, str, int, int, int], ...],
            ]
        ] = []
        for raw in raw_articulatory_recruitments:
            if not isinstance(raw, tuple) or len(raw) != 4:
                raise RuntimeError("articulatory-unit recruitment changed format")
            lineage = _canonical_lineage_hex(raw[0], "articulatory-unit lineage")
            topology_index = _nonnegative_integer(
                raw[1], "articulatory-unit topology index"
            )
            outward_elementary_carriers = _positive_integer(
                raw[2], "articulatory-unit outward elementary carriers"
            )
            if not isinstance(raw[3], list) or not raw[3]:
                raise RuntimeError(
                    "articulatory-unit motor transfers changed format"
                )
            motor_transfers: list[
                tuple[str, int, str, int, int, int]
            ] = []
            for transfer in raw[3]:
                if not isinstance(transfer, tuple) or len(transfer) != 6:
                    raise RuntimeError(
                        "articulatory-unit motor transfer changed format"
                    )
                sender = _canonical_lineage_hex(
                    transfer[0], "articulatory motor sender"
                )
                sender_layer = _nonnegative_integer(
                    transfer[1], "articulatory motor sender layer"
                )
                receiver = _canonical_lineage_hex(
                    transfer[2], "articulatory motor receiver"
                )
                receiver_layer = _nonnegative_integer(
                    transfer[3], "articulatory motor receiver layer"
                )
                parallel_ordinal = _nonnegative_integer(
                    transfer[4], "articulatory motor parallel ordinal"
                )
                transferred_whole_carriers = _positive_integer(
                    transfer[5], "articulatory motor transferred whole carriers"
                )
                if (
                    sender == receiver
                    or not (
                        (
                            sender == lineage
                            and sender_layer == 13
                            and receiver_layer == 12
                        )
                        or (
                            receiver == lineage
                            and receiver_layer == 13
                            and sender_layer == 12
                        )
                    )
                ):
                    raise RuntimeError(
                        "articulatory-unit preparation is not an exact layer 12/layer 13 contact transfer"
                    )
                motor_transfers.append(
                    (
                        sender,
                        sender_layer,
                        receiver,
                        receiver_layer,
                        parallel_ordinal,
                        transferred_whole_carriers,
                    )
                )
            articulatory_unit_recruitments.append(
                (
                    lineage,
                    topology_index,
                    outward_elementary_carriers,
                    tuple(motor_transfers),
                )
            )
        # A mounted joint cohort exists only where at least two ports share
        # one exact source clock, so a lawful episode can evaluate zero
        # mounted cohorts (cognition still receives its occurrences).
        cohort_count_changed = current_cohort_evaluation_count > (
            source_port_count * causal_interval_count
        )
        reached_neuron_growth = (
            complete_neuron_count - active_before.complete_neuron_count
        )
        claimed_resting_neurons = (
            active_before.developmental_resting_neuron_count
            - developmental_resting_neuron_count
        )
        if (
            predecessor_state_sha256 != active_before.state_sha256
            or predecessor_organism_tick != active_before.organism_tick
            or organism_tick != predecessor_organism_tick + causal_interval_count
            or predecessor_fabric_generation
            != active_before.fabric_generation
            or fabric_generation
            != predecessor_fabric_generation + causal_interval_count
            or predecessor_mounted_generation
            != active_before.mounted_generation
            or mounted_generation
            != predecessor_mounted_generation + causal_interval_count
            or predecessor_authentication_count != 0
            or predecessor_decode_count != 0
            or predecessor_rebuilt_field_count != 0
            or cohort_count_changed
            or successor_seal_count != 1
            or recurrent_complete_neuron_fractal_count
            > complete_neuron_fractal_count
            or reached_neuron_growth < 0
            or claimed_resting_neurons < 0
            or claimed_resting_neurons > reached_neuron_growth
            or endogenous_partial_cue_reassembly_count
            > partial_cue_reassembly_count
            or metabolically_perturbed_body_receptor_count
            > physically_transitioned_neuron_count
            or not isinstance(candidate.physical_transition_claimed, bool)
            or not isinstance(candidate.cognitive_formation_claimed, bool)
            or candidate.physical_transition_claimed
            != (physically_transitioned_neuron_count > 0)
            # A cognitive-formation claim must ride on evidence of the
            # formation kind: mosaic admission, activations, or partial-cue
            # reassembly stand on their own counters; trace/ordinal advance
            # is only lawful in a step that delivered genuine neuronal
            # fractals. A bare-DSF prepare dressing itself in advanced
            # cognitive counters is an impostor.
            or (
                candidate.cognitive_formation_claimed
                and cognitive_mosaic_count <= active_before.cognitive_mosaic_count
                and formation_activation_count == 0
                and partial_cue_reassembly_count
                <= active_before.partial_cue_reassembly_count
                and complete_neuron_fractal_count == 0
                and not organic_mosaic_relations
            )
            or candidate.python_callback_count != 0
        ):
            raise RuntimeError("resident organism prepare changed causal physics")
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism prepare published pending state")
        return ResidentPrepareEvidence(
            token=token,
            token_hex=candidate.token_hex,
            predecessor_state_sha256=predecessor_state_sha256,
            prepared_state_sha256=prepared_state_sha256,
            predecessor_organism_tick=predecessor_organism_tick,
            organism_tick=organism_tick,
            predecessor_fabric_generation=predecessor_fabric_generation,
            fabric_generation=fabric_generation,
            predecessor_mounted_generation=predecessor_mounted_generation,
            mounted_generation=mounted_generation,
            predecessor_authentication_count=predecessor_authentication_count,
            predecessor_decode_count=predecessor_decode_count,
            predecessor_rebuilt_field_count=predecessor_rebuilt_field_count,
            current_cohort_evaluation_count=current_cohort_evaluation_count,
            successor_seal_count=successor_seal_count,
            dsf_delivery_count=dsf_delivery_count,
            complete_neuron_fractal_count=complete_neuron_fractal_count,
            recurrent_complete_neuron_fractal_count=(
                recurrent_complete_neuron_fractal_count
            ),
            cognitive_ordinal=cognitive_ordinal,
            cognitive_trace_count=cognitive_trace_count,
            cognitive_mosaic_count=cognitive_mosaic_count,
            formation_activation_count=formation_activation_count,
            partial_cue_reassembly_count=partial_cue_reassembly_count,
            endogenous_partial_cue_reassembly_count=(
                endogenous_partial_cue_reassembly_count
            ),
            physical_transition_claimed=candidate.physical_transition_claimed,
            cognitive_formation_claimed=candidate.cognitive_formation_claimed,
            python_callback_count=0,
            complete_neuron_count=complete_neuron_count,
            developmental_resting_neuron_count=(
                developmental_resting_neuron_count
            ),
            physically_transitioned_neuron_count=(
                physically_transitioned_neuron_count
            ),
            metabolically_perturbed_body_receptor_count=(
                metabolically_perturbed_body_receptor_count
            ),
            receptor_ingress_sense_counts=receptor_ingress_sense_counts,
            receptor_ingress_changing_count=receptor_ingress_changing_count,
            receptor_ingress_quiescent_count=receptor_ingress_quiescent_count,
            motor_unit_recruitments=tuple(motor_unit_recruitments),
            articulatory_unit_recruitments=tuple(
                articulatory_unit_recruitments
            ),
            emitted_neuron_fractals=tuple(emitted_neuron_fractals),
            active_physical_bonds=tuple(active_physical_bonds),
            physical_frontier_routes=physical_frontier_routes,
            preceding_distinct_physical_frontier_routes=(
                preceding_distinct_physical_frontier_routes
            ),
            reached_and_foregone_physical_frontier_routes=(
                reached_and_foregone_physical_frontier_routes
            ),
            working_causal_continuations=working_causal_continuations,
            settled_working_frontier=settled_working_frontier,
            physical_prediction_alternatives=physical_prediction_alternatives,
            body_consequence_transfers=body_consequence_transfers,
            affective_balance_trajectories=affective_balance_trajectories,
            localized_fluid_chemistry=localized_fluid_chemistry,
            organic_mosaic_relations=tuple(organic_mosaic_relations),
        )

    def prepare_authored_contacts(
        self, contacts: object
    ) -> ResidentContactGrowthEvidence:
        """Prepare one AUTHORED contact growth and return its receipts.

        ``contacts`` is a sequence of ``(left_sensor_id, left_substream_id,
        right_sensor_id, right_substream_id, conductance_picosiemens)``: the
        caller names two of its OWN declared receptors and the conductance of
        the contact between them, exactly the authorship growth DNA carries at
        genesis.  This boundary derives no adjacency and no conductance.

        Growth is append-only in the body: existing contacts keep their index,
        endpoints, conductance and retained carrier phase. A growth carries
        no sensory occurrence, so no fractal may be claimed. The resident
        cognitive generation advances once because the body itself changed.
        """

        authored: list[tuple[str, str, str, str, int]] = []
        for entry in contacts:
            left_sensor, left_substream, right_sensor, right_substream, conductance = (
                entry
            )
            if (
                not isinstance(left_sensor, str)
                or not isinstance(left_substream, str)
                or not isinstance(right_sensor, str)
                or not isinstance(right_substream, str)
                or not left_sensor
                or not left_substream
                or not right_sensor
                or not right_substream
            ):
                raise TypeError("authored contact endpoints must be declared receptor names")
            authored.append(
                (
                    left_sensor,
                    left_substream,
                    right_sensor,
                    right_substream,
                    _positive_integer(conductance, "authored contact conductance"),
                )
            )
        if not authored:
            raise ValueError("authored contact growth requires at least one contact")
        active_before = self.readiness()
        candidate = self.__runtime.prepare_authored_contacts(authored)
        if not isinstance(candidate, self.__prepare_type):
            raise TypeError("resident organism prepare returned a structural impostor")
        if candidate.schema != PREPARE_SCHEMA:
            raise RuntimeError("resident organism prepare schema changed")
        token = candidate.token
        if (
            not isinstance(token, bytes)
            or len(token) != 32
            or candidate.token_hex != token.hex()
        ):
            raise RuntimeError("resident organism prepare token changed format")
        predecessor_state_sha256 = _canonical_sha256(
            candidate.predecessor_state_sha256, "predecessor state receipt"
        )
        prepared_state_sha256 = _canonical_sha256(
            candidate.prepared_state_sha256, "prepared state receipt"
        )
        if (
            predecessor_state_sha256 != active_before.state_sha256
            or candidate.predecessor_organism_tick != active_before.organism_tick
            or candidate.organism_tick != active_before.organism_tick + 1
            or candidate.predecessor_fabric_generation
            != active_before.fabric_generation
            or candidate.fabric_generation != active_before.fabric_generation + 1
            or candidate.mounted_generation
            != active_before.mounted_generation + 1
            or candidate.dsf_delivery_count != 0
            or candidate.complete_neuron_fractal_count != 0
            or candidate.physical_transition_claimed
            or candidate.cognitive_formation_claimed
        ):
            raise RuntimeError(
                "resident organism contact growth changed causal physics"
            )
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism prepare published pending state")
        return ResidentContactGrowthEvidence(
            token=token,
            token_hex=candidate.token_hex,
            predecessor_state_sha256=predecessor_state_sha256,
            prepared_state_sha256=prepared_state_sha256,
            predecessor_organism_tick=candidate.predecessor_organism_tick,
            organism_tick=candidate.organism_tick,
            predecessor_fabric_generation=candidate.predecessor_fabric_generation,
            fabric_generation=candidate.fabric_generation,
            mounted_generation=candidate.mounted_generation,
            authored_contact_count=len(authored),
        )

    def observe_cohort_contacts(self) -> tuple[tuple[int, int], ...]:
        """Decoded ``(member_count, contact_count)`` per living cohort."""

        return tuple(
            (int(members), int(contacts))
            for members, contacts in self.__runtime.observe_cohort_contacts()
        )

    def observe_reached_neuron_count_by_layer(
        self,
    ) -> tuple[tuple[int, int], ...]:
        """Decoded ``(layer, reached_count)`` from persisted neuron anatomy."""

        observed = tuple(
            (
                _nonnegative_integer(layer, "developmental layer"),
                _nonnegative_integer(count, "reached neuron layer count"),
            )
            for layer, count in (
                self.__runtime.observe_reached_neuron_count_by_layer()
            )
        )
        if any(
            count == 0
            or (index > 0 and observed[index - 1][0] >= layer)
            for index, (layer, count) in enumerate(observed)
        ):
            raise RuntimeError(
                "reached neuron layer distribution is not canonical"
            )
        return observed

    def observe_reached_neuron_electrical_by_layer(
        self,
    ) -> tuple[tuple[int, int, int, int, int, int], ...]:
        """Read-only layer, charge, capacitance and carrier material."""

        before = self.readiness()
        observed = tuple(
            (
                _nonnegative_integer(layer, "developmental layer"),
                int(charge),
                int(capacitance_numerator),
                _positive_integer(
                    capacitance_denominator, "capacitance denominator"
                ),
                _nonnegative_integer(intracellular, "intracellular carriers"),
                _nonnegative_integer(extracellular, "extracellular carriers"),
            )
            for (
                layer,
                charge,
                capacitance_numerator,
                capacitance_denominator,
                intracellular,
                extracellular,
            ) in (
                self.__runtime.observe_reached_neuron_electrical_by_layer()
            )
        )
        if len(observed) != before.complete_neuron_count:
            raise RuntimeError("reached neuron electrical projection changed width")
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("reached neuron electrical observation advanced the organism")
        return observed

    def observe_reached_contact_count_by_layer_pair(
        self,
    ) -> tuple[tuple[int, int, int], ...]:
        """Read-only sparse-contact counts by endpoint layer pair."""

        before = self.readiness()
        observed = tuple(
            (
                _nonnegative_integer(left, "left developmental layer"),
                _nonnegative_integer(right, "right developmental layer"),
                _nonnegative_integer(count, "interlayer contact count"),
            )
            for left, right, count in (
                self.__runtime.observe_reached_contact_count_by_layer_pair()
            )
        )
        if any(left > right or count == 0 for left, right, count in observed):
            raise RuntimeError("reached contact layer projection is not canonical")
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("reached contact observation advanced the organism")
        return observed

    def observe_reached_source_site_count(
        self,
        sensor_id: str,
        substream_id: str,
    ) -> int:
        """Count reached cells with one exact persisted physical source."""

        if not isinstance(sensor_id, str) or not sensor_id:
            raise TypeError("reached source sensor identity must be nonempty text")
        if not isinstance(substream_id, str) or not substream_id:
            raise TypeError("reached source substream identity must be nonempty text")
        return _nonnegative_integer(
            self.__runtime.observe_reached_source_site_count(
                sensor_id,
                substream_id,
            ),
            "reached source site count",
        )

    def commit(self, token: bytes) -> NativeResidentObservationView:
        """Commit the native pending candidate selected by its fixed token."""

        self.__runtime.commit(_exact_token(token))
        return self.readiness()

    def discard(self, token: bytes) -> NativeResidentObservationView:
        """Discard the native pending candidate and preserve active state."""

        active_before = self.readiness()
        self.__runtime.discard(_exact_token(token))
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism discard changed active state")
        return active_after


def restore_native_resident_organism(
    *,
    current_envelope: bytes,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> NativeResidentOrganism:
    """Cold restore one current GLORUN state into one native resident runtime."""

    if (
        not isinstance(current_envelope, bytes)
        or not current_envelope.startswith(b"GLORUN01")
    ):
        raise TypeError("resident organism cold restore requires GLORUN bytes")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    core = _native_core()
    runtime_type = _concrete_class(core, "NativeResidentOrganismRuntime")
    observation_type = _concrete_class(
        core, "NativeResidentOrganismObservation"
    )
    prepare_type = _concrete_class(core, "NativeResidentOrganismPrepare")
    restore = getattr(core, "restore_native_resident_organism_runtime", None)
    if not callable(restore):
        raise RuntimeError("guala_core does not expose resident cold restore")
    runtime = restore(current_envelope, envelope, fabric, logical)
    if not isinstance(runtime, runtime_type):
        raise TypeError("resident organism cold restore returned a structural impostor")
    if runtime.schema != RUNTIME_SCHEMA:
        raise RuntimeError("resident organism runtime schema changed")
    organism = NativeResidentOrganism(
        _FACTORY_AUTHORITY,
        runtime,
        runtime_type,
        observation_type,
        prepare_type,
    )
    organism.save()
    return organism


def exact_native_yaw_trajectory(
    *,
    predecessor_heading_millidegrees: int,
    signed_displacement_millidegrees: int,
    duration_microseconds: int,
) -> tuple[int, tuple[int, ...]]:
    """Return the native minimum-jerk yaw path on the 1 ms body clock."""

    trajectory = getattr(_native_core(), "exact_virtual_yaw_trajectory", None)
    if not callable(trajectory):
        raise RuntimeError("guala_core does not expose exact virtual yaw physics")
    successor, steps = trajectory(
        predecessor_heading_millidegrees,
        signed_displacement_millidegrees,
        duration_microseconds,
    )
    return int(successor), tuple(int(step) for step in steps)


def exact_motor_unit_yaw_trajectory(
    *,
    predecessor_heading_millidegrees: int,
    recruitments: tuple[tuple[int, int], ...],
) -> tuple[int, tuple[int, ...]]:
    """Settle transient native motor recruitment on the body yaw lattice."""

    trajectory = getattr(_native_core(), "exact_motor_unit_yaw_trajectory", None)
    if not callable(trajectory):
        raise RuntimeError("guala_core does not expose motor-unit yaw physics")
    successor, steps = trajectory(
        predecessor_heading_millidegrees,
        list(recruitments),
    )
    return int(successor), tuple(int(step) for step in steps)


def exact_articulatory_unit_trajectory(
    *,
    recruitments: tuple[tuple[int, int], ...],
) -> tuple[int, tuple[int, ...], int, int, int, int, int, int, int]:
    """Settle native layer-13 discharge through the bounded vocal body."""

    trajectory = getattr(_native_core(), "exact_articulatory_unit_trajectory", None)
    if not callable(trajectory):
        raise RuntimeError(
            "guala_core does not expose native articulatory body physics"
        )
    (
        sample_rate_hz,
        radiated_pressure_pcm,
        peak_breath_flow_pcm,
        glottal_open_samples_at_apex,
        mouth_area_square_millimetres_at_apex,
        perioral_area_displacement_square_millimetres,
        applied_motor_quanta,
        stalled_motor_quanta,
        relaxation_sample_count,
    ) = trajectory(list(recruitments))
    return (
        int(sample_rate_hz),
        tuple(int(value) for value in radiated_pressure_pcm),
        int(peak_breath_flow_pcm),
        int(glottal_open_samples_at_apex),
        int(mouth_area_square_millimetres_at_apex),
        int(perioral_area_displacement_square_millimetres),
        int(applied_motor_quanta),
        int(stalled_motor_quanta),
        int(relaxation_sample_count),
    )


def migrate_native_resident_organism_exact_energy(
    *,
    current_envelope: bytes,
    expected_predecessor_sha256: str,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> bytes:
    """Derive the explicit current-format body from one exact predecessor.

    The native boundary is idempotent: an already-current body is returned
    byte-identically. Publication decides whether that is a no-op; treating
    equality as an error here made every explicitly authorized restart fail.
    """

    if (
        not isinstance(current_envelope, bytes)
        or not current_envelope.startswith(b"GLORUN01")
    ):
        raise TypeError("exact-energy migration requires GLORUN bytes")
    predecessor = _canonical_sha256(
        expected_predecessor_sha256, "exact-energy predecessor receipt"
    )
    if hashlib.sha256(current_envelope).hexdigest() != predecessor:
        raise RuntimeError("exact-energy migration predecessor changed")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    migrate = getattr(
        _native_core(), "migrate_native_resident_organism_exact_energy", None
    )
    if not callable(migrate):
        raise RuntimeError("guala_core does not expose exact-energy migration")
    migrated = bytes(migrate(current_envelope, envelope, fabric, logical))
    if not migrated.startswith(b"GLORUN01") or len(migrated) > envelope:
        raise RuntimeError("current-format migration produced an invalid body")
    restore_native_resident_organism(
        current_envelope=migrated,
        max_envelope_bytes=envelope,
        max_fabric_bytes=fabric,
        max_logical_peak_bytes=logical,
    )
    return migrated


def _validated_growth_dna(
    growth_dna: object,
    episode_type: type,
) -> tuple[object, list[tuple[list[int], list[tuple[int, int, int]]]]]:
    """Validate authored growth DNA: (anatomy_episode, seed_groups).

    Each seed group is (port_indices, contacts): port_indices name joint
    source ports of the anatomy episode, and each contact is
    (left_seed_index, right_seed_index, conductance_picosiemens). Every value
    is authored by the caller; nothing is defaulted or inferred here.
    """

    if not isinstance(growth_dna, (tuple, list)) or len(growth_dna) != 2:
        raise TypeError(
            "resident organism growth_dna must be (anatomy_episode, seed_groups)"
        )
    anatomy_episode, seed_groups = growth_dna
    if not isinstance(anatomy_episode, episode_type):
        raise TypeError(
            "resident organism growth_dna anatomy episode must be a concrete "
            "native joint source episode"
        )
    if not isinstance(seed_groups, (tuple, list)) or not seed_groups:
        raise ValueError(
            "resident organism growth_dna requires at least one authored seed group"
        )

    def _index(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"growth_dna {label} must be a nonnegative integer")
        return value

    validated_groups: list[tuple[list[int], list[tuple[int, int, int]]]] = []
    for group_index, group in enumerate(seed_groups):
        if not isinstance(group, (tuple, list)) or len(group) != 2:
            raise TypeError(
                f"growth_dna seed group {group_index} must be "
                "(port_indices, contacts)"
            )
        port_indices, contacts = group
        if not isinstance(port_indices, (tuple, list)) or not port_indices:
            raise ValueError(
                f"growth_dna seed group {group_index} must name at least one "
                "port index"
            )
        validated_ports = [
            _index(port_index, f"seed group {group_index} port index")
            for port_index in port_indices
        ]
        if not isinstance(contacts, (tuple, list)):
            raise TypeError(
                f"growth_dna seed group {group_index} contacts must be a sequence"
            )
        validated_contacts: list[tuple[int, int, int]] = []
        for contact in contacts:
            if not isinstance(contact, (tuple, list)) or len(contact) != 3:
                raise TypeError(
                    f"growth_dna seed group {group_index} contact must be "
                    "(left_seed_index, right_seed_index, conductance_picosiemens)"
                )
            left, right, conductance = contact
            if isinstance(conductance, bool) or not isinstance(conductance, int):
                raise ValueError(
                    f"growth_dna seed group {group_index} conductance must be "
                    "an authored integer picosiemens value"
                )
            validated_contacts.append(
                (
                    _index(left, f"seed group {group_index} contact left index"),
                    _index(right, f"seed group {group_index} contact right index"),
                    conductance,
                )
            )
        validated_groups.append((validated_ports, validated_contacts))
    return anatomy_episode, validated_groups


def create_native_resident_organism(
    *,
    organism_identity: str,
    organism_tick: int = 0,
    growth_dna: object,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> NativeResidentOrganism:
    """Create the canonical native genesis carrying authored growth DNA.

    ``growth_dna`` is required: growth never invents electrical contacts, so a
    genesis without authored developmental seeds could never form a physical
    mosaic. The seeded genesis is still structurally empty — zero cohorts,
    traces, and mosaics — until its seeds are reached and expressed.
    """

    if not isinstance(organism_identity, str) or not organism_identity:
        raise TypeError("resident organism genesis identity must be text")
    tick = _nonnegative_integer(organism_tick, "genesis organism tick")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    core = _native_core()
    runtime_type = _concrete_class(core, "NativeResidentOrganismRuntime")
    observation_type = _concrete_class(
        core, "NativeResidentOrganismObservation"
    )
    prepare_type = _concrete_class(core, "NativeResidentOrganismPrepare")
    episode_type = _concrete_class(core, "NativeJointSourceEpisode")
    anatomy_episode, seed_groups = _validated_growth_dna(
        growth_dna, episode_type
    )
    create = getattr(
        core, "create_native_resident_organism_runtime_with_growth_dna", None
    )
    if not callable(create):
        raise RuntimeError(
            "guala_core does not expose resident growth-dna genesis"
        )
    runtime = create(
        organism_identity,
        tick,
        anatomy_episode,
        seed_groups,
        envelope,
        fabric,
        logical,
    )
    if not isinstance(runtime, runtime_type):
        raise TypeError("resident organism genesis returned a structural impostor")
    if runtime.schema != RUNTIME_SCHEMA:
        raise RuntimeError("resident organism genesis runtime schema changed")
    organism = NativeResidentOrganism(
        _FACTORY_AUTHORITY,
        runtime,
        runtime_type,
        observation_type,
        prepare_type,
    )
    observation = organism.readiness()
    if (
        observation.identity != organism_identity
        or observation.organism_tick != tick
        or observation.fabric_generation != 0
        or observation.mounted_generation != 0
        or observation.joint_field_count != 0
        or observation.joint_neuron_count != 0
        or observation.cognitive_ordinal != 0
        or observation.cognitive_trace_count != 0
        or observation.cognitive_mosaic_count != 0
    ):
        raise RuntimeError("resident organism genesis was not structurally empty")
    organism.save()
    return organism


__all__ = (
    "NativeResidentObservationView",
    "NativeResidentOrganism",
    "OBSERVATION_SCHEMA",
    "PREPARE_SCHEMA",
    "RUNTIME_SCHEMA",
    "ResidentPrepareEvidence",
    "create_native_resident_organism",
    "exact_motor_unit_yaw_trajectory",
    "exact_articulatory_unit_trajectory",
    "exact_native_yaw_trajectory",
    "restore_native_resident_organism",
    "migrate_native_resident_organism_exact_energy",
)
