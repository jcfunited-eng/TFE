"""Experience-driven transient vocal action inside an unresolved inquiry.

This authority extends exactly one authenticated self body with a neutral
larynx and eight-section tube geometry.  An unresolved or ambiguous lived
witness opens context custody, and every complete auditory D/M/R/U/C/P/B
trajectory remains in that custody unchanged.

The seven auditory fields independently drive seven local tract antagonists
through their complete exact temporal paths.  Simultaneous auditory channels
converge only within the same named field; fields are never summed, scored, or
ranked against one another.  Exact field minima and maxima span one native
mechanical resolution on either side of neutral, and every source interval
receives physical time in the one-second phonatory exhalation.  The eighth
tract section and glottal timing remain at anatomy-owned neutral coordinates.
This is a bounded physical efferent response, not acoustic matching.

Fresh pressure is synthesized, physically emitted, and self-heard through W1.
The anatomy returns to exact neutral after pressure reaches quiescence.

No caller or tutor can submit a motor coordinate, direction, duration,
pressure, waveform, program identity, label, word, or meaning.  This is one
causal self-vocal inquiry act.  It is not imitation, word recognition, or an
intelligibility claim.

Only anatomy and bounded resource accounting are persisted.  BODY full
fields, PCM, prepared acts, candidates, W1 settlements, and rollback
capabilities remain transient.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import struct
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Iterator, Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    MAX_ARTICULATORY_SAMPLES,
    ArticulatoryBodyTrajectoryInterval,
    ArticulatoryProgram,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
    generate_articulatory_pressure_with_quiescence,
)
from dsf_ai_service.substrate.causal_inquiry import (
    CausalInquiryOwner,
    InquiryNeed,
    InquiryWitness,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    ActionExecutionReceipt,
    EmbodiedBody,
    EmbodimentWorldAuthority,
    PreparedActionExecution,
    VocalizeCommand,
    encode_command,
)


VOCAL_BODY_STATE_SCHEMA = "guala.embodied_vocal_body.state.v3"
VOCAL_BODY_ENVELOPE_SCHEMA = "guala.embodied_vocal_body.hmac.v3"
BODY_CUSTODY_SCHEMA = (
    "guala.embodied_vocal_body.inquiry_context_custody.v2"
)
TRANSIENT_ACT_SCHEMA = "guala.embodied_vocal_body.transient_act.v2"
TRANSIENT_CANDIDATE_SCHEMA = (
    "guala.embodied_vocal_body.transient_candidate.v2"
)
MOTOR_FRAGMENT_CUSTODY_SCHEMA = (
    "guala.embodied_vocal_body.motor_fragment_custody.v1"
)
_STATE_DOMAIN = b"guala-embodied-vocal-body-state-v3\0"
_CUSTODY_DOMAIN = b"guala-embodied-vocal-body-inquiry-context-v2\0"
_ACT_DOMAIN = b"guala-embodied-vocal-body-transient-act-v2\0"
_CANDIDATE_DOMAIN = b"guala-embodied-vocal-body-candidate-v2\0"
_MOTOR_FRAGMENT_CUSTODY_DOMAIN = (
    b"guala-embodied-vocal-body-motor-fragment-custody-v1\0"
)
_VISIBILITY_INSTALL_AUTHORITY = object()
_COMMITTED_UNDO_AUTHORITY = object()
_CUSTODY_AUTHORITY = object()
_PREPARED_AUTHORITY = object()
_CANDIDATE_AUTHORITY = object()
_MOTOR_FRAGMENT_CUSTODY_AUTHORITY = object()
_CANDIDATE_FINALIZATION_UNDO_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")
_FIELD_NAMES = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)
_AUDITORY_HOP_SAMPLES = 160
_MAX_LOCAL_TENSION_QUANTA = 8
_MAX_TRACT_AREA_MM2 = 2_000
_MAX_COMPLETED_TRANSIENT_COUNT = (1 << 63) - 1
_MAX_SIMULTANEOUS_TRANSIENT_CUSTODIES = 1


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("vocal-body key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("vocal-body key has an invalid boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} is outside its exact integer boundary")
    return value


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _body_from_observation(
    observation,
    body_id: str,
) -> EmbodiedBody:
    matches = tuple(
        body for body in observation.bodies
        if body.body_id == body_id
    )
    if len(matches) != 1:
        raise ValueError("vocal body left authenticated world custody")
    return matches[0]


@dataclass(frozen=True, slots=True)
class LocalAntagonistState:
    neuron_id: str
    tension_quanta: int

    def verify(self) -> None:
        if (
            not isinstance(self.neuron_id, str)
            or not self.neuron_id
            or self.neuron_id.strip() != self.neuron_id
        ):
            raise ValueError("local antagonist identity changed")
        _integer(
            self.tension_quanta,
            "local antagonist tension",
            minimum=0,
            maximum=_MAX_LOCAL_TENSION_QUANTA,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "neuron_id": self.neuron_id,
            "tension_quanta": self.tension_quanta,
        }


@dataclass(frozen=True, slots=True)
class LocalVocalActuator:
    actuator_id: str
    physical_quantity: str
    physical_unit: str
    minimum_coordinate: int
    maximum_coordinate: int
    neutral_coordinate: int
    current_coordinate: int
    native_resolution: int
    negative: LocalAntagonistState
    positive: LocalAntagonistState

    def verify(self) -> None:
        for value, name in (
            (self.actuator_id, "local vocal actuator"),
            (self.physical_quantity, "local vocal quantity"),
            (self.physical_unit, "local vocal unit"),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value.strip() != value
            ):
                raise ValueError(f"{name} changed")
        _integer(
            self.minimum_coordinate,
            "actuator minimum",
            minimum=1,
            maximum=_MAX_TRACT_AREA_MM2,
        )
        _integer(
            self.maximum_coordinate,
            "actuator maximum",
            minimum=self.minimum_coordinate,
            maximum=_MAX_TRACT_AREA_MM2,
        )
        _integer(
            self.neutral_coordinate,
            "actuator neutral coordinate",
            minimum=self.minimum_coordinate,
            maximum=self.maximum_coordinate,
        )
        _integer(
            self.current_coordinate,
            "actuator current coordinate",
            minimum=self.minimum_coordinate,
            maximum=self.maximum_coordinate,
        )
        _integer(
            self.native_resolution,
            "actuator native resolution",
            minimum=1,
            maximum=self.maximum_coordinate - self.minimum_coordinate,
        )
        if (
            (self.neutral_coordinate - self.minimum_coordinate)
            % self.native_resolution
            or (self.current_coordinate - self.minimum_coordinate)
            % self.native_resolution
        ):
            raise ValueError(
                "actuator coordinate left native mechanical lattice"
            )
        self.negative.verify()
        self.positive.verify()
        if self.negative.neuron_id == self.positive.neuron_id:
            raise ValueError("local antagonists collapsed into one neuron")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "actuator_id": self.actuator_id,
            "current_coordinate": self.current_coordinate,
            "maximum_coordinate": self.maximum_coordinate,
            "minimum_coordinate": self.minimum_coordinate,
            "native_resolution": self.native_resolution,
            "negative": self.negative.as_record(),
            "neutral_coordinate": self.neutral_coordinate,
            "physical_quantity": self.physical_quantity,
            "physical_unit": self.physical_unit,
            "positive": self.positive.as_record(),
        }


@dataclass(frozen=True, slots=True)
class EmbodiedVocalAnatomy:
    body_id: str
    laryngeal_cycle_samples: int
    phonatory_exhalation_samples: int
    respiratory_peak_volume_velocity_pcm: int
    radiation_load_area_mm2: int
    wall_retention_ppm: int
    actuators: tuple[LocalVocalActuator, ...]

    def verify(self) -> None:
        if (
            not isinstance(self.body_id, str)
            or not self.body_id
            or self.body_id.strip() != self.body_id
        ):
            raise ValueError("vocal anatomy body identity changed")
        _integer(
            self.laryngeal_cycle_samples,
            "laryngeal cycle",
            minimum=16,
            maximum=800,
        )
        _integer(
            self.phonatory_exhalation_samples,
            "phonatory exhalation",
            minimum=VOCAL_SAMPLE_RATE_HZ,
            maximum=VOCAL_SAMPLE_RATE_HZ,
        )
        if (
            self.phonatory_exhalation_samples
            % self.laryngeal_cycle_samples
        ):
            raise ValueError(
                "phonatory exhalation does not close laryngeal cycles"
            )
        _integer(
            self.respiratory_peak_volume_velocity_pcm,
            "respiratory pressure",
            minimum=1,
            maximum=16_000,
        )
        _integer(
            self.radiation_load_area_mm2,
            "oral radiation load",
            minimum=1,
            maximum=_MAX_TRACT_AREA_MM2,
        )
        _integer(
            self.wall_retention_ppm,
            "vocal wall retention",
            minimum=1,
            maximum=999_999,
        )
        if (
            not isinstance(self.actuators, tuple)
            or len(self.actuators) != 9
        ):
            raise ValueError(
                "vocal anatomy must retain one larynx and eight tube actuators"
            )
        for actuator in self.actuators:
            actuator.verify()
        if len({item.actuator_id for item in self.actuators}) != 9:
            raise ValueError("vocal actuator topology identities repeat")
        if self.actuators[0].physical_quantity != "glottal-open-samples":
            raise ValueError("laryngeal actuator left topology index zero")
        if tuple(
            item.physical_quantity for item in self.actuators[1:]
        ) != tuple(
            f"tube-section-{index:02d}-area"
            for index in range(8)
        ):
            raise ValueError("eight-section vocal topology changed order")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "actuators": [
                actuator.as_record()
                for actuator in self.actuators
            ],
            "body_id": self.body_id,
            "laryngeal_cycle_samples": (
                self.laryngeal_cycle_samples
            ),
            "phonatory_exhalation_samples": (
                self.phonatory_exhalation_samples
            ),
            "radiation_load_area_mm2": (
                self.radiation_load_area_mm2
            ),
            "respiratory_peak_volume_velocity_pcm": (
                self.respiratory_peak_volume_velocity_pcm
            ),
            "wall_retention_ppm": self.wall_retention_ppm,
        }


def _initial_anatomy(body: EmbodiedBody) -> EmbodiedVocalAnatomy:
    """Derive one unlabeled anatomy from the authenticated body geometry."""

    body.verify()
    base_area = max(80, min(240, body.radius_mm // 2))
    tract_neutral = tuple(
        base_area + 20 * index for index in range(8)
    )
    quantities = (
        ("glottal-open-samples", "samples", 16, 144, 80, 8),
        *tuple(
            (
                f"tube-section-{index:02d}-area",
                "square-millimetres",
                40,
                1_000,
                tract_neutral[index],
                5,
            )
            for index in range(8)
        ),
    )
    actuators = []
    for index, (
        quantity,
        unit,
        minimum,
        maximum,
        neutral,
        resolution,
    ) in enumerate(quantities):
        actuators.append(LocalVocalActuator(
            actuator_id=f"{body.body_id}.vocal-actuator-{index:02d}",
            physical_quantity=quantity,
            physical_unit=unit,
            minimum_coordinate=minimum,
            maximum_coordinate=maximum,
            neutral_coordinate=neutral,
            current_coordinate=neutral,
            native_resolution=resolution,
            negative=LocalAntagonistState(
                neuron_id=(
                    f"{body.body_id}.vocal-actuator-{index:02d}.negative"
                ),
                tension_quanta=0,
            ),
            positive=LocalAntagonistState(
                neuron_id=(
                    f"{body.body_id}.vocal-actuator-{index:02d}.positive"
                ),
                tension_quanta=0,
            ),
        ))
    result = EmbodiedVocalAnatomy(
        body_id=body.body_id,
        laryngeal_cycle_samples=160,
        phonatory_exhalation_samples=VOCAL_SAMPLE_RATE_HZ,
        respiratory_peak_volume_velocity_pcm=4_000,
        radiation_load_area_mm2=base_area + 7 * 20,
        wall_retention_ppm=985_000,
        actuators=tuple(actuators),
    )
    result.verify()
    return result


@dataclass(frozen=True, slots=True)
class ExactInquirySoundTrajectory:
    topology_index: int
    sound_root_sha256: str
    boundary_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    field_support_sample_count: int
    source_intervals: tuple[tuple[int, int], ...]
    tuples: tuple[
        tuple[
            Fraction,
            Fraction,
            Fraction,
            Fraction,
            Fraction,
            Fraction,
            Fraction,
        ],
        ...,
    ]

    def verify(self) -> None:
        _integer(
            self.topology_index,
            "sound root topology index",
            minimum=0,
            maximum=1_000_000,
        )
        _sha256(
            self.sound_root_sha256,
            "inquiry sound root",
        )
        _sha256(
            self.boundary_receipt_sha256,
            "inquiry sound boundary",
        )
        _sha256(
            self.kernel_basin_receipt_sha256,
            "inquiry sound kernel basin",
        )
        _integer(
            self.field_support_sample_count,
            "inquiry sound field-support sample count",
            minimum=1,
            maximum=MAX_ARTICULATORY_SAMPLES,
        )
        if not self.tuples:
            raise ValueError("inquiry sound trajectory is empty")
        if (
            not isinstance(self.source_intervals, tuple)
            or len(self.source_intervals) != len(self.tuples)
        ):
            raise ValueError(
                "inquiry sound trajectory lost exact source intervals"
            )
        prior_end = -1
        for interval in self.source_intervals:
            if (
                not isinstance(interval, tuple)
                or len(interval) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    for value in interval
                )
                or interval[0] != prior_end + 1
                or not interval[0] <= interval[1]
                or interval[1] >= self.field_support_sample_count
            ):
                raise ValueError(
                    "inquiry sound trajectory source coverage changed"
                )
            prior_end = interval[1]
        if prior_end != self.field_support_sample_count - 1:
            raise ValueError(
                "inquiry sound trajectory did not close its source grid"
            )
        if any(
            len(item) != len(_FIELD_NAMES)
            or any(not isinstance(value, Fraction) for value in item)
            for item in self.tuples
        ):
            raise ValueError(
                "inquiry sound trajectory lost D/M/R/U/C/P/B"
            )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "kernel_basin_receipt_sha256": (
                self.kernel_basin_receipt_sha256
            ),
            "sound_root_sha256": self.sound_root_sha256,
            "field_support_sample_count": (
                self.field_support_sample_count
            ),
            "source_intervals": [
                [start, end]
                for start, end in self.source_intervals
            ],
            "topology_index": self.topology_index,
            "trajectory_sha256": _digest([
                {
                    "fields": [
                        _fraction_text(value) for value in item
                    ],
                    "source_index_end": interval[1],
                    "source_index_start": interval[0],
                }
                for interval, item in zip(
                    self.source_intervals,
                    self.tuples,
                    strict=True,
                )
            ]),
            "tuple_count": len(self.tuples),
        }


@dataclass(frozen=True, slots=True)
class InquiryEfferentCustodyCapability:
    body_id: str
    world_observation_receipt_sha256: str
    anatomy_sha256: str
    need_receipt_sha256: str
    witness_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    source_sample_count: int
    sound_fields: tuple[ExactInquirySoundTrajectory, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _observation: object = field(repr=False, compare=False)
    _need: InquiryNeed = field(repr=False, compare=False)
    _witness: InquiryWitness = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )

    def payload(self) -> dict[str, object]:
        return {
            "anatomy_sha256": self.anatomy_sha256,
            "body_id": self.body_id,
            "need_receipt_sha256": self.need_receipt_sha256,
            "sound_fields": [
                item.as_record() for item in self.sound_fields
            ],
            "source_sample_count": self.source_sample_count,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(
                self.source_time_start
            ),
            "schema": BODY_CUSTODY_SCHEMA,
            "witness_receipt_sha256": self.witness_receipt_sha256,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class PreparedBodyOwnedTransientAct:
    transient_act_id: str
    custody_receipt_sha256: str
    pressure_sha256: str
    source_sample_count: int
    program_sample_count: int
    sample_count: int
    exact_quiescent: bool
    prepared_world_action: PreparedActionExecution
    prospective_act_receipt_sha256: str
    _pcm_s16le: bytes = field(repr=False, compare=False)
    _program: ArticulatoryProgram = field(
        repr=False,
        compare=False,
    )
    _next_anatomy: EmbodiedVocalAnatomy = field(
        repr=False,
        compare=False,
    )
    _apex_anatomy: EmbodiedVocalAnatomy = field(
        repr=False,
        compare=False,
    )
    _prior_anatomy: EmbodiedVocalAnatomy = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )

    def payload(self) -> dict[str, object]:
        execution = self.prepared_world_action.execution_receipt
        return {
            "custody_receipt_sha256": self.custody_receipt_sha256,
            "exact_quiescent": self.exact_quiescent,
            "pressure_sha256": self.pressure_sha256,
            "program_sample_count": self.program_sample_count,
            "sample_count": self.sample_count,
            "source_sample_count": self.source_sample_count,
            "schema": TRANSIENT_ACT_SCHEMA,
            "transient_act_id": self.transient_act_id,
            "world_after_receipt_sha256": (
                execution.after.authority_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                execution.before.authority_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class TransientVocalCandidate:
    transient_act_id: str
    custody_receipt_sha256: str
    actuator_graph_receipt_sha256: str
    pressure_sha256: str
    source_sample_count: int
    program_sample_count: int
    sample_count: int
    exact_quiescent: bool
    world_execution_receipt_sha256: str
    w1_mount_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    receptor_settlement_receipt_sha256: str
    recurrent_q_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _w1_undo: object = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )

    def payload(self) -> dict[str, object]:
        return {
            "actuator_graph_receipt_sha256": (
                self.actuator_graph_receipt_sha256
            ),
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "custody_receipt_sha256": self.custody_receipt_sha256,
            "exact_quiescent": self.exact_quiescent,
            "pressure_sha256": self.pressure_sha256,
            "program_sample_count": self.program_sample_count,
            "receptor_settlement_receipt_sha256": (
                self.receptor_settlement_receipt_sha256
            ),
            "recurrent_q_receipt_sha256": (
                self.recurrent_q_receipt_sha256
            ),
            "sample_count": self.sample_count,
            "source_sample_count": self.source_sample_count,
            "schema": TRANSIENT_CANDIDATE_SCHEMA,
            "transient_act_id": self.transient_act_id,
            "w1_mount_receipt_sha256": (
                self.w1_mount_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class BodyOwnedMotorFragmentCustody:
    candidate_receipt_sha256: str
    transient_act_id: str
    pressure_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_graph_sha256: str
    program: ArticulatoryProgram
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _candidate: TransientVocalCandidate = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )

    def payload(self) -> dict[str, object]:
        return {
            "candidate_receipt_sha256": (
                self.candidate_receipt_sha256
            ),
            "command_graph_sha256": self.command_graph_sha256,
            "pressure_sha256": self.pressure_sha256,
            "program": self.program.as_record(),
            "schema": MOTOR_FRAGMENT_CUSTODY_SCHEMA,
            "transient_act_id": self.transient_act_id,
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }


@dataclass(slots=True)
class _CandidateFinalizationState:
    phase: str = "committed"


@dataclass(frozen=True, slots=True)
class BodyOwnedCandidateFinalizationUndo:
    """Typed authority to restore the original live candidate until publish."""

    candidate: TransientVocalCandidate
    _state: _CandidateFinalizationState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class _VisibilityInstall:
    prepared: PreparedBodyOwnedTransientAct
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class _CommittedBodyUndo:
    prior_anatomy: EmbodiedVocalAnatomy
    apex_anatomy: EmbodiedVocalAnatomy
    program: ArticulatoryProgram
    prior_world_receipt_sha256: str
    prior_completed_count: int
    installed_anatomy: EmbodiedVocalAnatomy
    installed_world_receipt_sha256: str
    installed_completed_count: int
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


class EmbodiedVocalCapacityError(RuntimeError):
    pass


class EmbodiedVocalBodyAuthority:
    """Own one physical vocal anatomy and its local efferent closure."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        inquiry_owner: CausalInquiryOwner | None = None,
        max_state_bytes: int = 131_072,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("vocal body requires its embodiment world")
        self._key = hashlib.sha256(_key(authority_key)).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + self._key
        ).digest()
        self._custody_key = hashlib.sha256(
            _CUSTODY_DOMAIN + self._key
        ).digest()
        self._act_key = hashlib.sha256(
            _ACT_DOMAIN + self._key
        ).digest()
        self._candidate_key = hashlib.sha256(
            _CANDIDATE_DOMAIN + self._key
        ).digest()
        self._motor_fragment_custody_key = hashlib.sha256(
            _MOTOR_FRAGMENT_CUSTODY_DOMAIN + self._key
        ).digest()
        if (
            inquiry_owner is not None
            and not isinstance(inquiry_owner, CausalInquiryOwner)
        ):
            raise TypeError(
                "vocal body inquiry owner has the wrong type"
            )
        self._world = world_authority
        self._inquiry = inquiry_owner
        self._max_state_bytes = _integer(
            max_state_bytes,
            "vocal-body state capacity",
            minimum=4_096,
            maximum=2 * 1024 * 1024,
        )
        observation = self._world.observation_snapshot()
        body = _body_from_observation(
            observation,
            observation.self_body_id,
        )
        self._body_id = body.body_id
        self._anatomy = _initial_anatomy(body)
        self._world_receipt_sha256 = (
            self._world.physical_vocal_anatomy_receipt()
        )
        self._completed_count = 0
        self._live_custody: (
            InquiryEfferentCustodyCapability | None
        ) = None
        self._prepared: PreparedBodyOwnedTransientAct | None = None
        self._live_candidate: TransientVocalCandidate | None = None
        self._candidate_finalization_undo: (
            BodyOwnedCandidateFinalizationUndo | None
        ) = None
        self._visibility_install: _VisibilityInstall | None = None
        self._custody_owner = object()
        self._prepared_owner = object()
        self._candidate_owner = object()
        self._motor_fragment_custody_owner = object()
        self._candidate_finalization_owner = object()
        self._visibility_owner = object()
        self._undo_owner = object()
        self._lock = threading.RLock()
        self._encoded_state()

    @property
    def anatomy(self) -> EmbodiedVocalAnatomy:
        with self._lock:
            return self._anatomy

    @property
    def acquired_program_count(self) -> int:
        return 0

    def owns_world(
        self,
        world_authority: EmbodimentWorldAuthority,
    ) -> bool:
        return world_authority is self._world

    def _state_payload(self) -> dict[str, object]:
        return {
            "anatomy": self._anatomy.as_record(),
            "body_id": self._body_id,
            "completed_transient_count": self._completed_count,
            "limits": {
                "max_completed_transient_count": (
                    _MAX_COMPLETED_TRANSIENT_COUNT
                ),
                "max_simultaneous_transient_custodies": (
                    _MAX_SIMULTANEOUS_TRANSIENT_CUSTODIES
                ),
                "max_state_bytes": self._max_state_bytes,
            },
            "schema": VOCAL_BODY_STATE_SCHEMA,
            "world_observation_receipt_sha256": (
                self._world_receipt_sha256
            ),
        }

    def _encoded_state(self) -> bytes:
        payload = _canonical(self._state_payload())
        if len(payload) > self._max_state_bytes:
            raise EmbodiedVocalCapacityError(
                "vocal-body state exceeds exact byte capacity"
            )
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": VOCAL_BODY_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise EmbodiedVocalCapacityError(
                "encoded vocal-body state exceeds exact byte capacity"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if (
                self._live_custody is not None
                or self._prepared is not None
                or self._live_candidate is not None
                or self._visibility_install is not None
            ):
                raise RuntimeError(
                    "transient vocal custody cannot enter persistence"
                )
            observation = self._world.observation_snapshot()
            self._world.verify_observation_snapshot(observation)
            body = _body_from_observation(
                observation,
                self._body_id,
            )
            if body.body_id != self._anatomy.body_id:
                raise ValueError(
                    "vocal anatomy is not bound to the current body edge"
                )
            self._world_receipt_sha256 = (
                self._world.physical_vocal_anatomy_receipt()
            )
            return self._encoded_state()

    @staticmethod
    def _sound_trajectory(
        root: FullFieldSensoryRoot,
    ) -> ExactInquirySoundTrajectory:
        root.verify()
        if root.sense != "sound":
            raise ValueError("vocal efferent root is not sound")
        try:
            evidence = json.loads(root.full_evidence_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "vocal efferent sound root is unreadable"
            ) from error
        field_tuples = evidence.get("field_tuples")
        source_sample_count = evidence.get("source_sample_count")
        if (
            not isinstance(field_tuples, list)
            or not field_tuples
            or isinstance(source_sample_count, bool)
            or not isinstance(source_sample_count, int)
            or not 1
            <= source_sample_count
            <= MAX_ARTICULATORY_SAMPLES
        ):
            raise ValueError(
                "vocal efferent sound extent changed"
            )
        exact_tuples = []
        source_intervals = []
        for expected_index, item in enumerate(field_tuples):
            if (
                not isinstance(item, Mapping)
                or item.get("tuple_index") != expected_index
                or isinstance(item.get("source_index_start"), bool)
                or not isinstance(
                    item.get("source_index_start"),
                    int,
                )
                or isinstance(item.get("source_index_end"), bool)
                or not isinstance(item.get("source_index_end"), int)
                or not isinstance(item.get("fields"), list)
                or len(item["fields"]) != len(DSF_FIELD_ORDER)
                or tuple(
                    value[0]
                    for value in item["fields"]
                    if isinstance(value, list)
                    and len(value) == 2
                ) != DSF_FIELD_ORDER
            ):
                raise ValueError(
                    "vocal efferent sound trajectory changed order"
                )
            source_intervals.append((
                item["source_index_start"],
                item["source_index_end"],
            ))
            exact = []
            for _name, text in item["fields"]:
                if not isinstance(text, str):
                    raise ValueError(
                        "vocal efferent field lost exact fractions"
                    )
                try:
                    value = Fraction(text)
                except (ValueError, ZeroDivisionError) as error:
                    raise ValueError(
                        "vocal efferent field fraction changed"
                    ) from error
                if _fraction_text(value) != text:
                    raise ValueError(
                        "vocal efferent field fraction is noncanonical"
                    )
                exact.append(value)
            exact_tuples.append(tuple(exact))
        result = ExactInquirySoundTrajectory(
            topology_index=root.topology_index,
            sound_root_sha256=_digest(root.record()),
            boundary_receipt_sha256=_sha256(
                evidence.get("boundary_receipt_sha256"),
                "vocal efferent sound boundary",
            ),
            kernel_basin_receipt_sha256=_sha256(
                evidence.get("kernel_basin_receipt_sha256"),
                "vocal efferent sound kernel basin",
            ),
            field_support_sample_count=source_sample_count,
            source_intervals=tuple(source_intervals),
            tuples=tuple(exact_tuples),
        )
        result.verify()
        return result

    def capture_inquiry_efferent(
        self,
        *,
        need: InquiryNeed,
        witness: InquiryWitness,
    ) -> InquiryEfferentCustodyCapability:
        """Authenticate one active inquiry's complete sound-field drive."""

        with self._lock:
            if (
                self._inquiry is None
                or self._live_custody is not None
                or self._prepared is not None
                or self._live_candidate is not None
                or self._candidate_finalization_undo is not None
            ):
                raise RuntimeError(
                    "vocal body cannot open inquiry efferent custody"
                )
            self._inquiry.snapshot_encoded()
            if (
                not isinstance(need, InquiryNeed)
                or not isinstance(witness, InquiryWitness)
                or self._inquiry.active_need != need
                or need.witness_receipt_sha256
                != witness.authority_receipt_sha256
                or witness.route_state not in {"unresolved", "ambiguous"}
                or sum(
                    retained == witness
                    for retained in self._inquiry.witnesses
                ) != 1
            ):
                raise ValueError(
                    "vocal efferent drive is not the active inquiry"
                )
            observation = self._world.observation_snapshot()
            self._world.verify_observation_snapshot(observation)
            body = _body_from_observation(observation, self._body_id)
            if (
                body.body_id != self._anatomy.body_id
                or witness.world_observation_receipt_sha256
                != observation.authority_receipt_sha256
                or witness.world_observation_revision
                != observation.revision
            ):
                raise ValueError(
                    "vocal efferent drive left its witnessed world edge"
                )
            self._world_receipt_sha256 = (
                self._world.physical_vocal_anatomy_receipt()
            )
            sound_fields = tuple(sorted(
                (
                    self._sound_trajectory(root)
                    for root in witness.full_field_roots
                    if root.sense == "sound"
                ),
                key=lambda value: value.topology_index,
            ))
            if (
                not sound_fields
                or len({
                    field.topology_index
                    for field in sound_fields
                }) != len(sound_fields)
                or len({
                    field.field_support_sample_count
                    for field in sound_fields
                }) != 1
            ):
                raise ValueError(
                    "active inquiry has no unique ordered sound extent"
                )
            source_sample_count = self._witness_source_sample_count(
                witness
            )
            provisional = InquiryEfferentCustodyCapability(
                body_id=self._body_id,
                world_observation_receipt_sha256=(
                    self._world.physical_vocal_anatomy_receipt()
                ),
                anatomy_sha256=_digest(self._anatomy.as_record()),
                need_receipt_sha256=need.authority_receipt_sha256,
                witness_receipt_sha256=(
                    witness.authority_receipt_sha256
                ),
                source_time_start=witness.source_time_start,
                source_time_end=witness.source_time_end,
                source_sample_count=source_sample_count,
                sound_fields=sound_fields,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _observation=observation,
                _need=need,
                _witness=witness,
                _owner_authority=self._custody_owner,
                _construction_authority=_CUSTODY_AUTHORITY,
            )
            signature = hmac.new(
                self._custody_key,
                _CUSTODY_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            custody = replace(
                provisional,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._live_custody = custody
            self.verify_custody(custody)
            return custody

    def verify_custody(
        self,
        custody: InquiryEfferentCustodyCapability,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    custody,
                    InquiryEfferentCustodyCapability,
                )
                or custody._construction_authority
                is not _CUSTODY_AUTHORITY
                or custody._owner_authority is not self._custody_owner
                or self._live_custody is not custody
                or custody.body_id != self._body_id
                or custody.anatomy_sha256
                != _digest(self._anatomy.as_record())
                or custody.world_observation_receipt_sha256
                != self._world_receipt_sha256
                or self._inquiry is None
                or self._inquiry.active_need != custody._need
                or custody._witness not in self._inquiry.witnesses
                or custody.need_receipt_sha256
                != custody._need.authority_receipt_sha256
                or custody.witness_receipt_sha256
                != custody._witness.authority_receipt_sha256
            ):
                raise ValueError(
                    "inquiry efferent custody changed authority"
                )
            self._inquiry.snapshot_encoded()
            for trajectory in custody.sound_fields:
                trajectory.verify()
            expected_fields = tuple(sorted(
                (
                    self._sound_trajectory(root)
                    for root in custody._witness.full_field_roots
                    if root.sense == "sound"
                ),
                key=lambda value: value.topology_index,
            ))
            signature = hmac.new(
                self._custody_key,
                _CUSTODY_DOMAIN + _canonical(custody.payload()),
                hashlib.sha256,
            )
            signature_hex = signature.hexdigest()
            current = self._world.observation_snapshot()
            if (
                expected_fields != custody.sound_fields
                or len({
                    value.field_support_sample_count
                    for value in expected_fields
                }) != 1
                or custody.source_sample_count
                != self._witness_source_sample_count(
                    custody._witness
                )
                or custody.source_time_start
                != custody._witness.source_time_start
                or custody.source_time_end
                != custody._witness.source_time_end
                or custody._observation != current
                or not hmac.compare_digest(
                    signature_hex,
                    custody.authority_hmac_sha256,
                )
                or custody.authority_receipt_sha256
                != _digest({
                    "authority_hmac_sha256": signature_hex,
                    "payload": custody.payload(),
                })
            ):
                raise ValueError(
                    "inquiry efferent custody changed state"
                )

    def discard_inquiry_efferent(
        self,
        custody: InquiryEfferentCustodyCapability,
    ) -> None:
        """Release an authenticated efferent when no act was prepared."""

        with self._lock:
            self.verify_custody(custody)
            self._live_custody = None

    @staticmethod
    def _witness_source_sample_count(
        witness: InquiryWitness,
    ) -> int:
        if not isinstance(witness, InquiryWitness):
            raise TypeError(
                "vocal duration requires an inquiry witness"
            )
        extent = (
            witness.source_time_end - witness.source_time_start
        ) * VOCAL_SAMPLE_RATE_HZ
        if (
            extent.denominator != 1
            or not 1 <= extent.numerator <= MAX_VOCAL_SAMPLE_COUNT
        ):
            raise ValueError(
                "inquiry source interval is not an exact bounded "
                "16 kHz sample extent"
            )
        return extent.numerator

    @staticmethod
    def _pcm_bytes(values: tuple[int, ...]) -> bytes:
        return b"".join(
            struct.pack("<h", int(value)) for value in values
        )

    def _physical_pressure(
        self,
        *,
        program: ArticulatoryProgram,
    ) -> tuple[bytes, bool, int]:
        current = self._anatomy
        if (
            not program.body_trajectory
            or not 1
            <= program.sample_count
            <= MAX_ARTICULATORY_SAMPLES
        ):
            raise ValueError(
                "anatomy-owned body trajectory exceeds physical bounds"
            )
        initial_areas = tuple(
            item.neutral_coordinate
            for item in current.actuators[1:]
        )
        pressure = generate_articulatory_pressure_with_quiescence(
            program=program,
            neutral_section_area_mm2=initial_areas,
        )
        values = (
            *pressure.active_radiated_pressure_pcm,
            *pressure.relaxation_radiated_pressure_pcm,
        )
        remainder = len(values) % _AUDITORY_HOP_SAMPLES
        if remainder:
            values = (
                *values,
                *(0 for _ in range(
                    _AUDITORY_HOP_SAMPLES - remainder
                )),
            )
        if len(values) > MAX_VOCAL_SAMPLE_COUNT:
            raise ValueError(
                "complete anatomy-owned vocal act exceeds world bound"
            )
        if not any(values):
            raise RuntimeError(
                "asymmetric local release produced no physical pressure"
            )
        return (
            self._pcm_bytes(tuple(values)),
            pressure.quiescent_terminal_state.is_quiescent,
            program.sample_count,
        )

    def _neutral_phonation_program(self) -> ArticulatoryProgram:
        """Return one authenticated neutral phonatory exhalation."""

        anatomy = self._anatomy
        anatomy.verify()
        coordinates = tuple(
            actuator.current_coordinate
            for actuator in anatomy.actuators
        )
        neutral_coordinates = tuple(
            actuator.neutral_coordinate
            for actuator in anatomy.actuators
        )
        if coordinates != neutral_coordinates:
            raise ValueError(
                "neutral phonation requires neutral authenticated anatomy"
            )
        cycle = anatomy.laryngeal_cycle_samples
        exhalation = anatomy.phonatory_exhalation_samples
        glottal_open_samples = coordinates[0]
        section_areas = coordinates[1:]
        return ArticulatoryProgram.create(
            sample_count=exhalation,
            larynx=LaryngealExcitationConfiguration(
                cycle_samples=cycle,
                open_samples=glottal_open_samples,
                peak_volume_velocity_pcm=(
                    anatomy.respiratory_peak_volume_velocity_pcm
                ),
            ),
            tract=VocalTractConfiguration(
                initial_section_area_mm2=section_areas,
                apex_section_area_mm2=section_areas,
                final_section_area_mm2=section_areas,
                radiation_load_area_mm2=(
                    anatomy.radiation_load_area_mm2
                ),
                wall_retention_ppm=anatomy.wall_retention_ppm,
            ),
            body_trajectory=(
                ArticulatoryBodyTrajectoryInterval(
                    sample_start=0,
                    sample_end=exhalation,
                    glottal_open_samples=glottal_open_samples,
                    section_area_mm2=section_areas,
                ),
            ),
        )

    @staticmethod
    def _experience_field_path(
        custody: InquiryEfferentCustodyCapability,
    ) -> tuple[tuple[int, int, tuple[Fraction, ...]], ...]:
        """Converge simultaneous channels within each exact named field."""

        trajectories = custody.sound_fields
        if not trajectories:
            raise ValueError("experience vocal drive has no sound field")
        support = trajectories[0].field_support_sample_count
        if any(
            trajectory.field_support_sample_count != support
            for trajectory in trajectories
        ):
            raise ValueError(
                "experience vocal drive changed its shared source extent"
            )
        boundaries = {0, support}
        for trajectory in trajectories:
            trajectory.verify()
            for start, end in trajectory.source_intervals:
                boundaries.add(start)
                boundaries.add(end + 1)
        ordered = tuple(sorted(boundaries))
        result = []
        cursors = [0 for _trajectory in trajectories]
        for source_start, source_stop in zip(
            ordered,
            ordered[1:],
            strict=False,
        ):
            values = []
            for trajectory_index, trajectory in enumerate(trajectories):
                cursor = cursors[trajectory_index]
                while (
                    trajectory.source_intervals[cursor][1]
                    < source_start
                ):
                    cursor += 1
                interval = trajectory.source_intervals[cursor]
                if not (
                    interval[0] <= source_start
                    and source_stop - 1 <= interval[1]
                ):
                    raise ValueError(
                        "experience vocal drive lost temporal coverage"
                    )
                cursors[trajectory_index] = cursor
                values.append(trajectory.tuples[cursor])
            result.append((
                source_start,
                source_stop - 1,
                tuple(
                    sum(
                        (value[field_index] for value in values),
                        Fraction(0),
                    )
                    for field_index in range(len(DSF_FIELD_ORDER))
                ),
            ))
        return tuple(result)

    @staticmethod
    def _round_fraction(value: Fraction) -> int:
        """Round an exact fraction to nearest, halves away from zero."""

        sign = -1 if value < 0 else 1
        magnitude = abs(value)
        quotient, remainder = divmod(
            magnitude.numerator,
            magnitude.denominator,
        )
        if 2 * remainder >= magnitude.denominator:
            quotient += 1
        return sign * quotient

    def _experience_phonation_program(
        self,
        custody: InquiryEfferentCustodyCapability,
    ) -> tuple[ArticulatoryProgram, EmbodiedVocalAnatomy]:
        """Drive seven local tract antagonists over the full field path."""

        neutral = self._neutral_phonation_program()
        field_path = self._experience_field_path(custody)
        if (
            not field_path
            or any(
                len(values) != len(DSF_FIELD_ORDER)
                for _start, _end, values in field_path
            )
        ):
            raise RuntimeError(
                "experience vocal drive lost full DSF field"
            )
        exhalation = neutral.sample_count
        active_sample_count = exhalation - 2
        if len(field_path) > active_sample_count:
            raise EmbodiedVocalCapacityError(
                "experience field path exceeds vocal temporal resolution"
            )
        minima = tuple(
            min(values[field_index] for _start, _end, values in field_path)
            for field_index in range(len(DSF_FIELD_ORDER))
        )
        maxima = tuple(
            max(values[field_index] for _start, _end, values in field_path)
            for field_index in range(len(DSF_FIELD_ORDER))
        )
        area_path = []
        for _source_start, _source_end, values in field_path:
            areas = []
            for field_index, actuator in enumerate(
                self._anatomy.actuators[1:]
            ):
                if field_index >= len(DSF_FIELD_ORDER):
                    areas.append(actuator.neutral_coordinate)
                    continue
                lower = max(
                    actuator.minimum_coordinate,
                    actuator.neutral_coordinate
                    - actuator.native_resolution,
                )
                upper = min(
                    actuator.maximum_coordinate,
                    actuator.neutral_coordinate
                    + actuator.native_resolution,
                )
                minimum = minima[field_index]
                maximum = maxima[field_index]
                span = upper - lower
                if span % actuator.native_resolution:
                    raise ValueError(
                        "local antagonist span left its native lattice"
                    )
                coordinate = (
                    actuator.neutral_coordinate
                    if minimum == maximum
                    else lower + actuator.native_resolution
                    * self._round_fraction(
                        (values[field_index] - minimum)
                        * (span // actuator.native_resolution)
                        / (maximum - minimum)
                    )
                )
                areas.append(coordinate)
            area_path.append(tuple(areas))
        if not any(
            areas != neutral.tract.initial_section_area_mm2
            for areas in area_path
        ):
            raise ValueError(
                "experience field path produced no physical perturbation"
            )
        total_source_samples = sum(
            source_end - source_start + 1
            for source_start, source_end, _values in field_path
        )
        extra_samples = active_sample_count - len(field_path)
        cumulative_source = 0
        allocated_extra = 0
        active_lengths = []
        for source_start, source_end, _values in field_path:
            cumulative_source += source_end - source_start + 1
            next_allocated_extra = (
                extra_samples * cumulative_source
                // total_source_samples
            )
            active_lengths.append(
                1 + next_allocated_extra - allocated_extra
            )
            allocated_extra = next_allocated_extra
        if sum(active_lengths) != active_sample_count:
            raise AssertionError(
                "experience vocal temporal allocation did not close"
            )
        glottal = neutral.larynx.open_samples
        neutral_areas = neutral.tract.initial_section_area_mm2
        intervals = [
            ArticulatoryBodyTrajectoryInterval(
                sample_start=0,
                sample_end=1,
                glottal_open_samples=glottal,
                section_area_mm2=neutral_areas,
            )
        ]
        sample_cursor = 1
        for areas, interval_length in zip(
            area_path,
            active_lengths,
            strict=True,
        ):
            next_cursor = sample_cursor + interval_length
            intervals.append(ArticulatoryBodyTrajectoryInterval(
                sample_start=sample_cursor,
                sample_end=next_cursor,
                glottal_open_samples=glottal,
                section_area_mm2=areas,
            ))
            sample_cursor = next_cursor
        intervals.append(ArticulatoryBodyTrajectoryInterval(
            sample_start=sample_cursor,
            sample_end=exhalation,
            glottal_open_samples=glottal,
            section_area_mm2=neutral_areas,
        ))
        midpoint = exhalation // 2
        apex_tuple = next(
            interval.section_area_mm2
            for interval in intervals
            if interval.sample_start <= midpoint < interval.sample_end
        )
        actuators = list(self._anatomy.actuators)
        for index, (actuator, coordinate) in enumerate(
            zip(
                self._anatomy.actuators[1:],
                apex_tuple,
                strict=True,
            ),
            start=1,
        ):
            actuators[index] = replace(
                actuator,
                current_coordinate=coordinate,
                negative=replace(
                    actuator.negative,
                    tension_quanta=int(
                        coordinate < actuator.neutral_coordinate
                    ),
                ),
                positive=replace(
                    actuator.positive,
                    tension_quanta=int(
                        coordinate > actuator.neutral_coordinate
                    ),
                ),
            )
        apex = replace(self._anatomy, actuators=tuple(actuators))
        apex.verify()
        program = ArticulatoryProgram.create(
            sample_count=exhalation,
            larynx=neutral.larynx,
            tract=VocalTractConfiguration(
                initial_section_area_mm2=neutral_areas,
                apex_section_area_mm2=apex_tuple,
                final_section_area_mm2=neutral_areas,
                radiation_load_area_mm2=(
                    neutral.tract.radiation_load_area_mm2
                ),
                wall_retention_ppm=(
                    neutral.tract.wall_retention_ppm
                ),
            ),
            body_trajectory=tuple(intervals),
        )
        return program, apex

    def prepare_transient(
        self,
        custody: InquiryEfferentCustodyCapability,
    ) -> PreparedBodyOwnedTransientAct:
        """Stage one anatomy-owned act inside authenticated inquiry context."""

        with self._lock:
            self.verify_custody(custody)
            program, apex_anatomy = (
                self._experience_phonation_program(custody)
            )
            pcm, quiescent, program_sample_count = self._physical_pressure(
                program=program,
            )
            observation = custody._observation
            graph_record = program.as_record()
            graph_sha256 = _digest(graph_record)
            transient_act_id = _digest({
                "actuator_graph_receipt_sha256": graph_sha256,
                "custody_receipt_sha256": (
                    custody.authority_receipt_sha256
                ),
                "world_before_receipt_sha256": (
                    observation.authority_receipt_sha256
                ),
            })
            epoch = _digest({
                "transient_act_id": transient_act_id,
                "vocal_body": self._body_id,
            })
            command = VocalizeCommand(
                epoch_commitment_sha256=epoch,
                sequence=observation.revision,
                source_sample_start=0,
                pcm_sha256=hashlib.sha256(pcm).hexdigest(),
                sample_count=len(pcm) // 2,
            )
            command_payload = encode_command(command)
            prepared_world = self._world.prepare_port_command(
                port_id=PORT_ID,
                command_payload=command_payload,
                causal_intent_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                expected_revision=observation.revision,
            )
            if isinstance(prepared_world, ActionExecutionReceipt):
                self._world.verify_execution_receipt(prepared_world)
                self._live_custody = None
                raise ValueError(
                    "body-owned vocal act was rejected: "
                    f"{prepared_world.reason}"
                )
            provisional = PreparedBodyOwnedTransientAct(
                transient_act_id=transient_act_id,
                custody_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                pressure_sha256=hashlib.sha256(pcm).hexdigest(),
                source_sample_count=program.sample_count,
                program_sample_count=program_sample_count,
                sample_count=len(pcm) // 2,
                exact_quiescent=quiescent,
                prepared_world_action=prepared_world,
                prospective_act_receipt_sha256="0" * 64,
                _pcm_s16le=pcm,
                _program=program,
                _next_anatomy=self._anatomy,
                _apex_anatomy=apex_anatomy,
                _prior_anatomy=self._anatomy,
                _owner_authority=self._prepared_owner,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            signature = hmac.new(
                self._act_key,
                _ACT_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = replace(
                provisional,
                prospective_act_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._prepared = prepared
            self._live_custody = None
            try:
                self.verify_prepared_transient(prepared)
            except BaseException:
                self._world.discard_prepared_action(prepared_world)
                self._prepared = None
                raise
            return prepared

    def verify_prepared_transient(
        self,
        prepared: PreparedBodyOwnedTransientAct,
    ) -> None:
        with self._lock:
            if isinstance(prepared, PreparedBodyOwnedTransientAct):
                prepared._program.verify()
            if (
                not isinstance(
                    prepared,
                    PreparedBodyOwnedTransientAct,
                )
                or prepared._construction_authority
                is not _PREPARED_AUTHORITY
                or prepared._owner_authority is not self._prepared_owner
                or self._prepared is not prepared
                or prepared._prior_anatomy != self._anatomy
                or prepared.pressure_sha256
                != hashlib.sha256(prepared._pcm_s16le).hexdigest()
                or prepared.sample_count
                != len(prepared._pcm_s16le) // 2
                or prepared._program.sample_count
                != prepared.program_sample_count
                or not prepared._program.body_trajectory
                or not 1
                <= prepared.source_sample_count
                <= prepared.program_sample_count
                <= MAX_ARTICULATORY_SAMPLES
                or prepared._next_anatomy
                != prepared._prior_anatomy
                or prepared._apex_anatomy.body_id
                != self._body_id
                or not prepared.exact_quiescent
            ):
                raise ValueError(
                    "prepared body-owned transient changed custody"
                )
            self._world.verify_prepared_action(
                prepared.prepared_world_action
            )
            provisional = replace(
                prepared,
                prospective_act_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._act_key,
                _ACT_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            if prepared.prospective_act_receipt_sha256 != _digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }):
                raise ValueError(
                    "prepared body-owned transient changed state"
                )

    def discard_prepared_transient(
        self,
        prepared: PreparedBodyOwnedTransientAct,
    ) -> None:
        with self._lock:
            self.verify_prepared_transient(prepared)
            self._world.discard_prepared_action(
                prepared.prepared_world_action
            )
            self._prepared = None

    def preverify_transient_visibility_install(
        self,
        prepared: PreparedBodyOwnedTransientAct,
    ) -> _VisibilityInstall:
        with self._lock:
            self.verify_prepared_transient(prepared)
            if self._visibility_install is not None:
                raise RuntimeError(
                    "vocal-body visibility install already exists"
                )
            return _VisibilityInstall(
                prepared=prepared,
                _owner_authority=self._visibility_owner,
                _construction_authority=(
                    _VISIBILITY_INSTALL_AUTHORITY
                ),
            )

    @contextmanager
    def transient_visibility_transaction(
        self,
        install: _VisibilityInstall,
    ) -> Iterator[object]:
        with self._lock:
            if (
                not isinstance(install, _VisibilityInstall)
                or install._construction_authority
                is not _VISIBILITY_INSTALL_AUTHORITY
                or install._owner_authority is not self._visibility_owner
            ):
                raise ValueError(
                    "vocal-body visibility install changed"
                )
            prepared = install.prepared
            self.verify_prepared_transient(prepared)
            self._visibility_install = install
            installed = [False]
            undo = [None]

            def install_now() -> _CommittedBodyUndo:
                if installed[0]:
                    raise RuntimeError(
                        "vocal-body visibility installed twice"
                    )
                execution = self._world.commit_prepared_action(
                    prepared.prepared_world_action
                )
                prior_count = self._completed_count
                if prior_count >= _MAX_COMPLETED_TRANSIENT_COUNT:
                    raise EmbodiedVocalCapacityError(
                        "vocal-body completed counter exhausted"
                    )
                prior_receipt = self._world_receipt_sha256
                self._anatomy = prepared._next_anatomy
                self._world_receipt_sha256 = (
                    self._world.physical_vocal_anatomy_receipt()
                )
                self._completed_count += 1
                self._prepared = None
                self._encoded_state()
                undo[0] = _CommittedBodyUndo(
                    prior_anatomy=prepared._prior_anatomy,
                    apex_anatomy=prepared._apex_anatomy,
                    program=prepared._program,
                    prior_world_receipt_sha256=prior_receipt,
                    prior_completed_count=prior_count,
                    installed_anatomy=self._anatomy,
                    installed_world_receipt_sha256=(
                        self._world_receipt_sha256
                    ),
                    installed_completed_count=(
                        self._completed_count
                    ),
                    _owner_authority=self._undo_owner,
                    _construction_authority=(
                        _COMMITTED_UNDO_AUTHORITY
                    ),
                )
                installed[0] = True
                return undo[0]

            try:
                yield install_now
            except BaseException:
                if installed[0]:
                    assert undo[0] is not None
                    self._anatomy = undo[0].prior_anatomy
                    self._world_receipt_sha256 = (
                        undo[0].prior_world_receipt_sha256
                    )
                    self._completed_count = (
                        undo[0].prior_completed_count
                    )
                    self._prepared = prepared
                raise
            finally:
                self._visibility_install = None

    @contextmanager
    def committed_transient_rollback_transaction(
        self,
        undo: _CommittedBodyUndo,
    ) -> Iterator[object]:
        with self._lock:
            if (
                not isinstance(undo, _CommittedBodyUndo)
                or undo._construction_authority
                is not _COMMITTED_UNDO_AUTHORITY
                or undo._owner_authority is not self._undo_owner
                or self._anatomy != undo.installed_anatomy
                or self._world_receipt_sha256
                != undo.installed_world_receipt_sha256
                or self._completed_count
                != undo.installed_completed_count
                or self._prepared is not None
                or self._live_custody is not None
            ):
                raise ValueError(
                    "committed vocal-body rollback authority changed"
                )
            rolled_back = [False]

            def rollback_now() -> None:
                if rolled_back[0]:
                    raise RuntimeError("vocal-body rollback repeated")
                self._anatomy = undo.prior_anatomy
                self._world_receipt_sha256 = (
                    undo.prior_world_receipt_sha256
                )
                self._completed_count = undo.prior_completed_count
                self._encoded_state()
                rolled_back[0] = True

            yield rollback_now

    def attempt_with_transient_delivery(
        self,
        custody: InquiryEfferentCustodyCapability,
        *,
        w1_authority,
    ) -> tuple[TransientVocalCandidate, bytes]:
        """Close self-hearing and return exact pressure once, without retention."""

        from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
            W1SelfAcousticPropagationAuthority,
        )

        if not isinstance(
            w1_authority,
            W1SelfAcousticPropagationAuthority,
        ):
            raise TypeError(
                "body-owned vocal attempt requires W1 self-hearing"
            )
        try:
            prepared = self.prepare_transient(custody)
        except BaseException:
            if self._live_custody is custody:
                self.discard_inquiry_efferent(custody)
            raise
        staged_w1 = w1_authority.prepare_body_owned_transient(
            prepared,
            vocal_body_owner=self,
        )
        commitment, undo = (
            w1_authority.commit_body_owned_transient(staged_w1)
        )
        try:
            graph_sha256 = _digest(prepared._program.as_record())
            provisional = TransientVocalCandidate(
                transient_act_id=prepared.transient_act_id,
                custody_receipt_sha256=(
                    prepared.custody_receipt_sha256
                ),
                actuator_graph_receipt_sha256=graph_sha256,
                pressure_sha256=prepared.pressure_sha256,
                source_sample_count=(
                    prepared.source_sample_count
                ),
                program_sample_count=(
                    prepared.program_sample_count
                ),
                sample_count=prepared.sample_count,
                exact_quiescent=prepared.exact_quiescent,
                world_execution_receipt_sha256=(
                    commitment.world_execution_receipt_sha256
                ),
                w1_mount_receipt_sha256=(
                    commitment.mount_receipt_sha256
                ),
                causal_settlement_receipt_sha256=(
                    commitment.causal_settlement_receipt_sha256
                ),
                binaural_l5_receipt_sha256=(
                    commitment.binaural_l5_receipt_sha256
                ),
                receptor_settlement_receipt_sha256=(
                    commitment.receptor_settlement_receipt_sha256
                ),
                recurrent_q_receipt_sha256=(
                    commitment.recurrent_q_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _w1_undo=undo,
                _owner_authority=self._candidate_owner,
                _construction_authority=_CANDIDATE_AUTHORITY,
            )
            signature = hmac.new(
                self._candidate_key,
                _CANDIDATE_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            candidate = replace(
                provisional,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._live_candidate = candidate
            self.verify_candidate(candidate)
            return candidate, bytes(prepared._pcm_s16le)
        except BaseException:
            w1_authority.rollback_body_owned_transient(undo)
            self._live_candidate = None
            raise

    def attempt(
        self,
        custody: InquiryEfferentCustodyCapability,
        *,
        w1_authority,
    ) -> TransientVocalCandidate:
        """Close one inquiry efferent -> act -> W1 self-hearing transaction."""

        candidate, _transient_delivery = (
            self.attempt_with_transient_delivery(
                custody,
                w1_authority=w1_authority,
            )
        )
        return candidate

    def verify_candidate(
        self,
        candidate: TransientVocalCandidate,
    ) -> None:
        if (
            not isinstance(candidate, TransientVocalCandidate)
            or candidate._construction_authority
            is not _CANDIDATE_AUTHORITY
            or candidate._owner_authority is not self._candidate_owner
            or self._live_candidate is not candidate
            or not candidate.exact_quiescent
            or candidate.sample_count <= 0
            or not 1
            <= candidate.source_sample_count
            <= candidate.program_sample_count
            <= MAX_ARTICULATORY_SAMPLES
        ):
            raise ValueError("transient vocal candidate changed custody")
        signature = hmac.new(
            self._candidate_key,
            _CANDIDATE_DOMAIN + _canonical(candidate.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                candidate.authority_hmac_sha256,
            )
            or candidate.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": candidate.payload(),
            })
        ):
            raise ValueError("transient vocal candidate changed state")

    def rollback_candidate(
        self,
        candidate: TransientVocalCandidate,
        *,
        w1_authority,
    ) -> None:
        self.verify_candidate(candidate)
        w1_authority.rollback_body_owned_transient(
            candidate._w1_undo
        )
        self._live_candidate = None

    def finalize_candidate(
        self,
        candidate: TransientVocalCandidate,
    ) -> None:
        """Release transient candidate custody after durable consequence seal."""

        undo = self.commit_candidate_finalization(candidate)
        self.finalize_candidate_finalization(undo)

    def commit_candidate_finalization(
        self,
        candidate: TransientVocalCandidate,
    ) -> BodyOwnedCandidateFinalizationUndo:
        """Remove ordinary live custody while retaining exact publish rollback."""

        with self._lock:
            if self._candidate_finalization_undo is not None:
                raise RuntimeError(
                    "candidate finalization is already awaiting publication"
                )
            self.verify_candidate(candidate)
            undo = BodyOwnedCandidateFinalizationUndo(
                candidate=candidate,
                _state=_CandidateFinalizationState(),
                _owner_authority=self._candidate_finalization_owner,
                _construction_authority=(
                    _CANDIDATE_FINALIZATION_UNDO_AUTHORITY
                ),
            )
            self._live_candidate = None
            self._candidate_finalization_undo = undo
            return undo

    def _verify_candidate_finalization_undo(
        self,
        undo: BodyOwnedCandidateFinalizationUndo,
    ) -> None:
        if (
            not isinstance(undo, BodyOwnedCandidateFinalizationUndo)
            or undo._construction_authority
            is not _CANDIDATE_FINALIZATION_UNDO_AUTHORITY
            or undo._owner_authority
            is not self._candidate_finalization_owner
            or self._candidate_finalization_undo is not undo
            or undo._state.phase != "committed"
            or self._live_candidate is not None
        ):
            raise ValueError(
                "candidate finalization rollback authority changed"
            )

    def rollback_candidate_finalization(
        self,
        undo: BodyOwnedCandidateFinalizationUndo,
    ) -> None:
        """Restore the original typed candidate and its authentic W1 undo."""

        with self._lock:
            self._verify_candidate_finalization_undo(undo)
            self._live_candidate = undo.candidate
            undo._state.phase = "rolled_back"
            self._candidate_finalization_undo = None
            self.verify_candidate(undo.candidate)

    def finalize_candidate_finalization(
        self,
        undo: BodyOwnedCandidateFinalizationUndo,
    ) -> None:
        """Irreversibly release rollback custody after publication succeeds."""

        with self._lock:
            self._verify_candidate_finalization_undo(undo)
            undo._state.phase = "finalized"
            self._candidate_finalization_undo = None

    def open_motor_fragment_custody(
        self,
        candidate: TransientVocalCandidate,
    ) -> BodyOwnedMotorFragmentCustody:
        """Derive the exact compact command from live body custody only."""

        with self._lock:
            self.verify_candidate(candidate)
            w1_undo = candidate._w1_undo
            body_undo = getattr(w1_undo, "_vocal_body_undo", None)
            state = getattr(w1_undo, "_state", None)
            if (
                getattr(w1_undo, "_vocal_body_owner", None)
                is not self
                or body_undo is None
                or body_undo._construction_authority
                is not _COMMITTED_UNDO_AUTHORITY
                or body_undo._owner_authority is not self._undo_owner
                or state is None
                or not state.sealed
                or state.rolled_back
                or self._anatomy != body_undo.installed_anatomy
                or self._completed_count
                != body_undo.installed_completed_count
            ):
                raise ValueError(
                    "transient candidate lost live body custody"
                )
            prior = body_undo.prior_anatomy
            program = body_undo.program
            program.verify()
            if (
                not program.body_trajectory
                or program.sample_count
                != candidate.program_sample_count
            ):
                raise ValueError(
                    "transient candidate lost its temporal body program"
                )
            pressure = generate_articulatory_pressure_with_quiescence(
                program=program,
                neutral_section_area_mm2=(
                    tuple(
                        actuator.neutral_coordinate
                        for actuator in prior.actuators[1:]
                    )
                ),
            )
            values = (
                *pressure.active_radiated_pressure_pcm,
                *pressure.relaxation_radiated_pressure_pcm,
            )
            remainder = len(values) % _AUDITORY_HOP_SAMPLES
            if remainder:
                values = (
                    *values,
                    *(0 for _ in range(
                        _AUDITORY_HOP_SAMPLES - remainder
                    )),
                )
            pressure_sha256 = hashlib.sha256(
                self._pcm_bytes(tuple(values))
            ).hexdigest()
            execution = (
                w1_undo._prepared_world_action.execution_receipt
            )
            command_graph_sha256 = _digest(program.as_record())
            if (
                pressure_sha256 != candidate.pressure_sha256
                or len(values) != candidate.sample_count
                or execution.authority_receipt_sha256
                != candidate.world_execution_receipt_sha256
                or self._world.physical_vocal_anatomy_receipt()
                != body_undo.prior_world_receipt_sha256
                or self._world.physical_vocal_anatomy_receipt()
                != body_undo.installed_world_receipt_sha256
            ):
                raise ValueError(
                    "transient candidate cannot reproduce its body command"
                )
            provisional = BodyOwnedMotorFragmentCustody(
                candidate_receipt_sha256=(
                    candidate.authority_receipt_sha256
                ),
                transient_act_id=candidate.transient_act_id,
                pressure_sha256=pressure_sha256,
                world_before_receipt_sha256=(
                    execution.before.authority_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    execution.after.authority_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    execution.authority_receipt_sha256
                ),
                command_graph_sha256=command_graph_sha256,
                program=program,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _candidate=candidate,
                _owner_authority=(
                    self._motor_fragment_custody_owner
                ),
                _construction_authority=(
                    _MOTOR_FRAGMENT_CUSTODY_AUTHORITY
                ),
            )
            signature = hmac.new(
                self._motor_fragment_custody_key,
                _MOTOR_FRAGMENT_CUSTODY_DOMAIN
                + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            result = replace(
                provisional,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self.verify_motor_fragment_custody(
                result,
                candidate,
            )
            return result

    def verify_motor_fragment_custody(
        self,
        custody: BodyOwnedMotorFragmentCustody,
        candidate: TransientVocalCandidate,
    ) -> None:
        self.verify_candidate(candidate)
        if (
            not isinstance(custody, BodyOwnedMotorFragmentCustody)
            or custody._construction_authority
            is not _MOTOR_FRAGMENT_CUSTODY_AUTHORITY
            or custody._owner_authority
            is not self._motor_fragment_custody_owner
            or custody._candidate is not candidate
            or custody.candidate_receipt_sha256
            != candidate.authority_receipt_sha256
            or custody.transient_act_id
            != candidate.transient_act_id
            or custody.pressure_sha256
            != candidate.pressure_sha256
        ):
            raise ValueError(
                "body-owned motor fragment custody changed"
            )
        custody.program.verify()
        signature = hmac.new(
            self._motor_fragment_custody_key,
            _MOTOR_FRAGMENT_CUSTODY_DOMAIN
            + _canonical(custody.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                custody.authority_hmac_sha256,
            )
            or custody.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": custody.payload(),
            })
        ):
            raise ValueError(
                "body-owned motor fragment custody lost authority"
            )

    @staticmethod
    def _antagonist_from(value: object) -> LocalAntagonistState:
        if (
            not isinstance(value, Mapping)
            or set(value) != {"neuron_id", "tension_quanta"}
        ):
            raise ValueError("retained antagonist fields changed")
        result = LocalAntagonistState(
            neuron_id=value.get("neuron_id"),
            tension_quanta=value.get("tension_quanta"),
        )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError("retained antagonist is not canonical")
        return result

    @classmethod
    def _actuator_from(cls, value: object) -> LocalVocalActuator:
        expected = {
            "actuator_id",
            "current_coordinate",
            "maximum_coordinate",
            "minimum_coordinate",
            "native_resolution",
            "negative",
            "neutral_coordinate",
            "physical_quantity",
            "physical_unit",
            "positive",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("retained vocal actuator fields changed")
        result = LocalVocalActuator(
            actuator_id=value.get("actuator_id"),
            physical_quantity=value.get("physical_quantity"),
            physical_unit=value.get("physical_unit"),
            minimum_coordinate=value.get("minimum_coordinate"),
            maximum_coordinate=value.get("maximum_coordinate"),
            neutral_coordinate=value.get("neutral_coordinate"),
            current_coordinate=value.get("current_coordinate"),
            native_resolution=value.get("native_resolution"),
            negative=cls._antagonist_from(value.get("negative")),
            positive=cls._antagonist_from(value.get("positive")),
        )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError("retained vocal actuator is not canonical")
        return result

    @classmethod
    def _anatomy_from(cls, value: object) -> EmbodiedVocalAnatomy:
        expected = {
            "actuators",
            "body_id",
            "laryngeal_cycle_samples",
            "phonatory_exhalation_samples",
            "radiation_load_area_mm2",
            "respiratory_peak_volume_velocity_pcm",
            "wall_retention_ppm",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("retained vocal anatomy fields changed")
        raw_actuators = value.get("actuators")
        if not isinstance(raw_actuators, list):
            raise ValueError("retained vocal actuators changed")
        result = EmbodiedVocalAnatomy(
            body_id=value.get("body_id"),
            laryngeal_cycle_samples=value.get(
                "laryngeal_cycle_samples"
            ),
            phonatory_exhalation_samples=value.get(
                "phonatory_exhalation_samples"
            ),
            respiratory_peak_volume_velocity_pcm=value.get(
                "respiratory_peak_volume_velocity_pcm"
            ),
            radiation_load_area_mm2=value.get(
                "radiation_load_area_mm2"
            ),
            wall_retention_ppm=value.get("wall_retention_ppm"),
            actuators=tuple(
                cls._actuator_from(item) for item in raw_actuators
            ),
        )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError("retained vocal anatomy is not canonical")
        return result

    def restore_encoded(
        self,
        encoded: bytes,
        *,
        allow_authenticated_body_edge_migration: bool = False,
    ) -> bool:
        if not isinstance(allow_authenticated_body_edge_migration, bool):
            raise TypeError(
                "vocal body-edge migration authority must be boolean"
            )
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._max_state_bytes
        ):
            raise ValueError(
                "encoded vocal-body state exceeds exact capacity"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "vocal-body envelope is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {
                "authority_hmac_sha256",
                "payload_base64",
                "schema",
            }
            or envelope.get("schema") != VOCAL_BODY_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("vocal-body envelope fields changed")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"),
                validate=True,
            )
        except Exception as error:
            raise ValueError(
                "vocal-body payload is not canonical base64"
            ) from error
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            signature,
            envelope.get("authority_hmac_sha256"),
        ):
            raise ValueError("vocal-body state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "vocal-body payload is not canonical JSON"
            ) from error
        expected = {
            "anatomy",
            "body_id",
            "completed_transient_count",
            "limits",
            "schema",
            "world_observation_receipt_sha256",
        }
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != expected
            or decoded.get("schema") != VOCAL_BODY_STATE_SCHEMA
            or _canonical(decoded) != payload
            or decoded.get("limits") != {
                "max_completed_transient_count": (
                    _MAX_COMPLETED_TRANSIENT_COUNT
                ),
                "max_simultaneous_transient_custodies": (
                    _MAX_SIMULTANEOUS_TRANSIENT_CUSTODIES
                ),
                "max_state_bytes": self._max_state_bytes,
            }
        ):
            raise ValueError("vocal-body state fields changed")
        anatomy = self._anatomy_from(decoded.get("anatomy"))
        body_id = decoded.get("body_id")
        count = _integer(
            decoded.get("completed_transient_count"),
            "retained transient count",
            minimum=0,
            maximum=_MAX_COMPLETED_TRANSIENT_COUNT,
        )
        world_receipt = _sha256(
            decoded.get("world_observation_receipt_sha256"),
            "retained world observation",
        )
        current = self._world.observation_snapshot()
        body = _body_from_observation(current, self._body_id)
        current_body_receipt = (
            self._world.physical_vocal_anatomy_receipt()
        )
        migrated_body_edge = world_receipt != current_body_receipt
        if (
            body_id != self._body_id
            or anatomy.body_id != self._body_id
            or (
                world_receipt != current_body_receipt
                and not allow_authenticated_body_edge_migration
            )
        ):
            raise ValueError(
                "retained vocal anatomy belongs to another body edge"
            )
        with self._lock:
            if (
                self._live_custody is not None
                or self._prepared is not None
                or self._visibility_install is not None
                or self._live_candidate is not None
                or self._candidate_finalization_undo is not None
            ):
                raise RuntimeError(
                    "cannot restore across transient vocal custody"
                )
            prior = (
                self._anatomy,
                self._world_receipt_sha256,
                self._completed_count,
            )
            self._anatomy = anatomy
            self._world_receipt_sha256 = current_body_receipt
            self._completed_count = count
            try:
                current_encoded = self._encoded_state()
                if not migrated_body_edge and current_encoded != encoded:
                    raise ValueError(
                        "vocal-body state is not canonical"
                    )
            except BaseException:
                (
                    self._anatomy,
                    self._world_receipt_sha256,
                    self._completed_count,
                ) = prior
                raise
            return migrated_body_edge

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "acquired_program_count": 0,
                "body_id": self._body_id,
                "completed_transient_count": self._completed_count,
                "completed_transient_count_max": (
                    _MAX_COMPLETED_TRANSIENT_COUNT
                ),
                "live_custody": int(self._live_custody is not None),
                "live_candidate": int(
                    self._live_candidate is not None
                ),
                "candidate_finalization_pending": int(
                    self._candidate_finalization_undo is not None
                ),
                "max_simultaneous_transient_custodies": (
                    _MAX_SIMULTANEOUS_TRANSIENT_CUSTODIES
                ),
                "prepared_transient": int(self._prepared is not None),
                "retained_pcm_bytes": 0,
                "schema": "guala.embodied_vocal_body.status.v1",
            }


__all__ = [
    "BODY_CUSTODY_SCHEMA",
    "BodyOwnedCandidateFinalizationUndo",
    "BodyOwnedMotorFragmentCustody",
    "InquiryEfferentCustodyCapability",
    "EmbodiedVocalAnatomy",
    "EmbodiedVocalBodyAuthority",
    "EmbodiedVocalCapacityError",
    "ExactInquirySoundTrajectory",
    "LocalAntagonistState",
    "LocalVocalActuator",
    "PreparedBodyOwnedTransientAct",
    "TRANSIENT_ACT_SCHEMA",
    "TRANSIENT_CANDIDATE_SCHEMA",
    "TransientVocalCandidate",
    "VOCAL_BODY_ENVELOPE_SCHEMA",
    "VOCAL_BODY_STATE_SCHEMA",
]
