"""Coupled external articulation in the bounded W1 physical world.

One verified articulatory synthesis is the common physical cause of both the
companion's time-resolved visible mouth aperture and its emitted pressure.
The pressure is executed through the real companion port, propagated to the
two calibrated ears, and mounted with the visible motion in one exact
six-sense causal settlement.  The authority retains receipts and full DSF
field custody, never waveform bytes, labels, transcripts, or meaning.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, replace
from fractions import Fraction
from math import gcd

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ACTUATOR_RECEPTOR_SAMPLE_DIVISOR,
    MAX_TRACT_AREA_MM2,
    ArticulatorySelfVocalMotorOwner,
    ArticulatorySynthesis,
    generate_articulatory_pressure_with_quiescence,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    PositionMM,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1BinauralCalibration,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
    body_from_snapshot,
    calibrated_ear_positions,
    distance_squared_mm,
    pcm16_bytes,
    render_ear_pressure,
    signed_pcm16_samples,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
    settle_w1_binaural_receptors,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    physical_receptor_substreams,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)


DEMONSTRATION_SCHEMA = "guala.w1.companion_articulation.v2"
DEMONSTRATION_DOMAIN = b"guala.w1.companion.articulation.v2\0"
MAX_DEMONSTRATION_RECEIPT_BYTES = 32 * 1024
MAX_DEMONSTRATION_STATE_BYTES = 256 * 1024
DEFAULT_MAX_COMPLETED_DEMONSTRATIONS = 1024
STATE_SCHEMA = "guala.w1.companion_articulation.state.v1"
STATE_DOMAIN = b"guala.w1.companion_articulation.state.v1\0"
ARTICULATOR_RETINAL_CONE = (
    "forward-positive-and-absolute-lateral-not-greater-than-forward"
)
NEUTRAL_TRACT_SECTION_AREAS_MM2 = (
    30,
    130,
    169,
    191,
    178,
    216,
    347,
    201,
)
NEUTRAL_TRACT_CALIBRATION = {
    "author": "Brad H. Story",
    "citation": (
        "Journal of the Acoustical Society of America "
        "117(5), 3231-3254 (2005)"
    ),
    "doi": "10.1121/1.1869752",
    "source": "Table III neutral diameter function",
    "source_tubelet_count": 44,
    "source_tubelet_length_cm": "0.396825",
    "integration": (
        "volume-conserving integration of 44 equal tubelets into "
        "8 equal-length tract sections"
    ),
    "neutral_section_area_mm2": list(
        NEUTRAL_TRACT_SECTION_AREAS_MM2
    ),
    "schema": "guala.w1.neutral_vocal_tract.calibration.v1",
}


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


NEUTRAL_TRACT_CALIBRATION_RECEIPT_SHA256 = _digest(
    NEUTRAL_TRACT_CALIBRATION
)


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not 32 <= len(value) <= 4096:
        raise ValueError(
            "companion articulatory authority key has an invalid boundary"
        )
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("physical source time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _bounded_positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _field_custody(
    settlement: CausalExperienceSettlement,
) -> tuple[int, str]:
    records = []
    count = 0
    for sense in settlement.interpretations:
        for substream in sense.substreams:
            tuples = []
            for field_tuple in substream.field_tuples:
                if tuple(name for name, _value in field_tuple.fields) != (
                    DSF_FIELD_ORDER
                ):
                    raise ValueError(
                        "companion articulation lost the full DSF field"
                    )
                tuples.append({
                    "authority_receipt_sha256": (
                        field_tuple.authority_receipt_sha256
                    ),
                    "fields": [
                        (name, _fraction_text(value))
                        for name, value in field_tuple.fields
                    ],
                    "source_index_end": field_tuple.source_index_end,
                    "source_index_start": field_tuple.source_index_start,
                    "source_l0_l4_trace_receipt_sha256": (
                        field_tuple.source_l0_l4_trace_receipt_sha256
                    ),
                    "tuple_index": field_tuple.tuple_index,
                })
                count += 1
            records.append({
                "sense": sense.sense,
                "substream_id": substream.substream_id,
                "topology_index": substream.topology_index,
                "tuples": tuples,
            })
    if count <= 0:
        raise ValueError("companion articulation produced no DSF field custody")
    return count, _digest({
        "records": records,
        "schema": "guala.w1.companion_articulation.full_dsf_custody.v1",
    })


def _round_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("articulatory interpolation denominator is invalid")
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return sign * quotient


def _mouth_area_trajectory(
    synthesis: ArticulatorySynthesis,
) -> tuple[int, ...]:
    tract = synthesis.program.tract
    count = synthesis.program.sample_count
    final_index = count - 1
    apex_index = final_index // 2
    result = []
    for sample_index in range(count):
        if sample_index <= apex_index:
            left = tract.initial_section_area_mm2[-1]
            right = tract.apex_section_area_mm2[-1]
            position = sample_index
            denominator = max(1, apex_index)
        else:
            left = tract.apex_section_area_mm2[-1]
            right = tract.final_section_area_mm2[-1]
            position = sample_index - apex_index
            denominator = max(1, final_index - apex_index)
        result.append(_round_div(
            left * (denominator - position) + right * position,
            denominator,
        ))
    return tuple(result)


def _cardinal_retinal_ray(
    *,
    eye: PositionMM,
    heading_millidegrees: int,
    source: PositionMM,
) -> tuple[str, int, int]:
    dx = source.x - eye.x
    dy = source.y - eye.y
    if heading_millidegrees == 0:
        forward, lateral = dx, dy
    elif heading_millidegrees == 90_000:
        forward, lateral = dy, -dx
    elif heading_millidegrees == 180_000:
        forward, lateral = -dx, -dy
    elif heading_millidegrees == 270_000:
        forward, lateral = -dy, dx
    else:
        raise ValueError(
            "companion articulator requires cardinal retinal calibration"
        )
    if forward <= 0 or abs(lateral) > forward:
        raise ValueError(
            "companion articulator is outside the exact admitted retinal cone"
        )
    divisor = gcd(abs(forward), abs(lateral))
    reduced_forward = forward // divisor
    reduced_lateral = lateral // divisor
    side = "left" if lateral > 0 else "right" if lateral < 0 else "centre"
    return side, reduced_forward, reduced_lateral


def _mouth_aperture_input(
    *,
    mouth_areas_mm2: tuple[int, ...],
    source_time_start: Fraction,
    eye: PositionMM,
    eye_heading_millidegrees: int,
    companion_position: PositionMM,
    topology_index: int,
    reference_distance_mm: int,
) -> tuple[NativeSensorySubstreamInput, str, str, int, int]:
    if len(set(mouth_areas_mm2)) <= 1:
        raise ValueError(
            "changing companion articulation produced a static mouth"
        )
    indices = list(range(
        0,
        len(mouth_areas_mm2),
        ACTUATOR_RECEPTOR_SAMPLE_DIVISOR,
    ))
    if indices[-1] != len(mouth_areas_mm2) - 1:
        indices.append(len(mouth_areas_mm2) - 1)
    distance_squared = distance_squared_mm(eye, companion_position)
    reference_squared = reference_distance_mm**2
    projection = Fraction(
        reference_squared,
        max(reference_squared, distance_squared),
    )
    source_times = tuple(
        source_time_start + Fraction(index, VOCAL_SAMPLE_RATE_HZ)
        for index in indices
    )
    neutral_area = NEUTRAL_TRACT_SECTION_AREAS_MM2[-1]
    normalized = tuple(
        float(Fraction(
            mouth_areas_mm2[index] - neutral_area,
            max(mouth_areas_mm2[index], neutral_area),
        ))
        for index in indices
    )
    actuator_trajectory_commitment = _digest({
        "areas_mm2": [
            mouth_areas_mm2[index] for index in indices
        ],
        "sample_indices": indices,
        "schema": "guala.w1.mouth_actuator_trajectory.v1",
    })
    trajectory_commitment = _digest({
        "actuator_trajectory_sha256": actuator_trajectory_commitment,
        "local_contrast_law": (
            "(aperture_area-neutral_area)/"
            "max(aperture_area,neutral_area)"
        ),
        "neutral_area_mm2": neutral_area,
        "projection": _fraction_text(projection),
        "schema": "guala.w1.visible_mouth_aperture_trajectory.v1",
        "source_times": [
            _fraction_text(value) for value in source_times
        ],
    })
    retinal_side, ray_forward, ray_lateral = _cardinal_retinal_ray(
        eye=eye,
        heading_millidegrees=eye_heading_millidegrees,
        source=companion_position,
    )
    return (
        NativeSensorySubstreamInput(
            sense=PhysicalSense.SIGHT,
            sensor_id="W1-retinal-articulatory-edge-receptor",
            substream_id="visible-mouth-aperture-motion",
            topology_index=topology_index,
            coordinates=(
                NativeAxisCoordinate(
                    "optical-admission-cone",
                    ARTICULATOR_RETINAL_CONE,
                ),
                NativeAxisCoordinate("retinal-side", retinal_side),
                NativeAxisCoordinate(
                    "optical-ray-forward-projective",
                    str(ray_forward),
                ),
                NativeAxisCoordinate(
                    "optical-ray-lateral-projective",
                    str(ray_lateral),
                ),
                NativeAxisCoordinate(
                    "optical-geometric-feature",
                    "mouth-aperture-boundary",
                ),
            ),
            physical_quantity="local-mouth-aperture-area-contrast",
            physical_unit="signed-rational-contrast",
            source_times=source_times,
            normalized_signal=normalized,
            phase_turns=tuple(
                Fraction(index, max(1, len(mouth_areas_mm2) - 1))
                for index in indices
            ),
        ),
        trajectory_commitment,
        actuator_trajectory_commitment,
        min(mouth_areas_mm2),
        max(mouth_areas_mm2),
    )


@dataclass(frozen=True, slots=True)
class W1CompanionArticulatoryDemonstrationReceipt:
    occurrence: int
    source_sample_start: int
    source_sample_end: int
    active_source_sample_start: int
    active_source_sample_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    pre_rest_sample_count: int
    post_rest_sample_count: int
    relaxation_sample_count: int
    neutral_tract_calibration_receipt_sha256: str
    terminal_traveling_wave_state_sha256: str
    synthesis_receipt_sha256: str
    actuator_full_field_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    acoustic_emission_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    binaural_receptor_settlement_receipt_sha256: str
    mouth_actuator_trajectory_sha256: str
    mouth_aperture_trajectory_sha256: str
    mouth_aperture_sample_count: int
    mouth_aperture_min_mm2: int
    mouth_aperture_max_mm2: int
    left_pressure_sha256: str
    right_pressure_sha256: str
    left_delay_samples: int
    right_delay_samples: int
    left_attenuation: Fraction
    right_attenuation: Fraction
    full_dsf_tuple_count: int
    full_dsf_custody_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_emission_receipt_sha256": (
                self.acoustic_emission_receipt_sha256
            ),
            "actuator_full_field_receipt_sha256": (
                self.actuator_full_field_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "binaural_receptor_settlement_receipt_sha256": (
                self.binaural_receptor_settlement_receipt_sha256
            ),
            "companion_port_id": SECOND_BODY_PORT_ID,
            "full_dsf_custody_sha256": self.full_dsf_custody_sha256,
            "full_dsf_tuple_count": self.full_dsf_tuple_count,
            "left_attenuation": _fraction_text(self.left_attenuation),
            "left_delay_samples": self.left_delay_samples,
            "left_pressure_sha256": self.left_pressure_sha256,
            "mouth_aperture_max_mm2": self.mouth_aperture_max_mm2,
            "mouth_aperture_min_mm2": self.mouth_aperture_min_mm2,
            "mouth_aperture_sample_count": (
                self.mouth_aperture_sample_count
            ),
            "mouth_aperture_trajectory_sha256": (
                self.mouth_aperture_trajectory_sha256
            ),
            "mouth_actuator_trajectory_sha256": (
                self.mouth_actuator_trajectory_sha256
            ),
            "active_source_sample_end": self.active_source_sample_end,
            "active_source_sample_start": self.active_source_sample_start,
            "neutral_tract_calibration_receipt_sha256": (
                self.neutral_tract_calibration_receipt_sha256
            ),
            "occurrence": self.occurrence,
            "post_rest_sample_count": self.post_rest_sample_count,
            "pre_rest_sample_count": self.pre_rest_sample_count,
            "relaxation_sample_count": self.relaxation_sample_count,
            "right_attenuation": _fraction_text(self.right_attenuation),
            "right_delay_samples": self.right_delay_samples,
            "right_pressure_sha256": self.right_pressure_sha256,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": DEMONSTRATION_SCHEMA,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "synthesis_receipt_sha256": self.synthesis_receipt_sha256,
            "terminal_traveling_wave_state_sha256": (
                self.terminal_traveling_wave_state_sha256
            ),
            "source_inventory_after": "authenticated-empty",
            "source_inventory_before": "authenticated-empty",
            "terminal_ear_delay_lines": "exact-zero",
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

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        for value, name in (
            (self.synthesis_receipt_sha256, "synthesis receipt"),
            (
                self.actuator_full_field_receipt_sha256,
                "actuator full field receipt",
            ),
            (
                self.world_before_receipt_sha256,
                "world before receipt",
            ),
            (
                self.world_after_receipt_sha256,
                "world after receipt",
            ),
            (
                self.world_execution_receipt_sha256,
                "world execution receipt",
            ),
            (
                self.acoustic_emission_receipt_sha256,
                "acoustic emission receipt",
            ),
            (
                self.causal_settlement_receipt_sha256,
                "causal settlement receipt",
            ),
            (self.binaural_l5_receipt_sha256, "binaural L5 receipt"),
            (
                self.binaural_receptor_settlement_receipt_sha256,
                "binaural receptor settlement receipt",
            ),
            (
                self.mouth_aperture_trajectory_sha256,
                "mouth aperture trajectory",
            ),
            (
                self.mouth_actuator_trajectory_sha256,
                "mouth actuator trajectory",
            ),
            (
                self.neutral_tract_calibration_receipt_sha256,
                "neutral tract calibration",
            ),
            (
                self.terminal_traveling_wave_state_sha256,
                "terminal traveling-wave state",
            ),
            (self.left_pressure_sha256, "left pressure"),
            (self.right_pressure_sha256, "right pressure"),
            (self.full_dsf_custody_sha256, "full DSF custody"),
            (self.authority_hmac_sha256, "authority HMAC"),
            (self.authority_receipt_sha256, "authority receipt"),
        ):
            _sha256(value, name)
        if (
            isinstance(self.occurrence, bool)
            or not isinstance(self.occurrence, int)
            or self.occurrence < 0
            or isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or isinstance(self.source_sample_end, bool)
            or not isinstance(self.source_sample_end, int)
            or self.source_sample_start < 0
            or self.source_sample_end <= self.source_sample_start
            or self.active_source_sample_start
            != self.source_sample_start + self.pre_rest_sample_count
            or self.active_source_sample_end
            <= self.active_source_sample_start
            or self.source_time_start
            != Fraction(self.source_sample_start, VOCAL_SAMPLE_RATE_HZ)
            or self.source_time_end
            != Fraction(self.source_sample_end, VOCAL_SAMPLE_RATE_HZ)
            or self.pre_rest_sample_count != OBSERVATION_HOP_SAMPLES
            or self.post_rest_sample_count < OBSERVATION_HOP_SAMPLES
            or self.relaxation_sample_count < 0
            or self.source_sample_end - self.source_sample_start
            != (
                self.pre_rest_sample_count
                + (
                    self.active_source_sample_end
                    - self.active_source_sample_start
                )
                + self.relaxation_sample_count
                + max(self.left_delay_samples, self.right_delay_samples)
                + self.post_rest_sample_count
            )
            or self.neutral_tract_calibration_receipt_sha256
            != NEUTRAL_TRACT_CALIBRATION_RECEIPT_SHA256
            or self.mouth_aperture_sample_count <= 1
            or not 1
            <= self.mouth_aperture_min_mm2
            < self.mouth_aperture_max_mm2
            <= MAX_TRACT_AREA_MM2
            or self.left_delay_samples < 0
            or self.right_delay_samples < 0
            or not 0 < self.left_attenuation <= 1
            or not 0 < self.right_attenuation <= 1
            or self.full_dsf_tuple_count <= 0
        ):
            raise ValueError(
                "companion articulatory demonstration boundary changed"
            )
        signature = hmac.new(
            key,
            DEMONSTRATION_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        expected = _digest({
            "authority_hmac_sha256": signature,
            "payload": self.payload(),
        })
        if (
            not hmac.compare_digest(
                signature,
                self.authority_hmac_sha256,
            )
            or expected != self.authority_receipt_sha256
        ):
            raise ValueError(
                "companion articulatory demonstration authority changed"
            )


@dataclass(frozen=True, slots=True)
class W1CompanionArticulatoryDemonstration:
    receipt: W1CompanionArticulatoryDemonstrationReceipt
    causal_settlement: CausalExperienceSettlement
    binaural_l5: W1BinauralAuditoryL5Experience
    binaural_receptor_settlement: W1BinauralReceptorSettlement


class W1CompanionArticulatoryDemonstrationAuthority:
    """Own one bounded external articulation-to-perception transaction."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        causal_owner: ExactCausalExperienceOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        acoustic_emitter: W1AcousticEmitterAuthority,
        binaural_l5_owner: W1BinauralAuditoryL5Owner,
        calibration: W1BinauralCalibration = W1BinauralCalibration(),
        companion_port_id: str = SECOND_BODY_PORT_ID,
        max_completed_demonstrations: int = (
            DEFAULT_MAX_COMPLETED_DEMONSTRATIONS
        ),
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "companion articulation requires W1 world authority"
            )
        if not isinstance(causal_owner, ExactCausalExperienceOwner):
            raise TypeError(
                "companion articulation requires causal settlement owner"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "companion articulation requires articulatory authority"
            )
        if not isinstance(acoustic_emitter, W1AcousticEmitterAuthority):
            raise TypeError(
                "companion articulation requires acoustic authority"
            )
        if not isinstance(
            binaural_l5_owner,
            W1BinauralAuditoryL5Owner,
        ):
            raise TypeError(
                "companion articulation requires binaural L5 authority"
            )
        if not acoustic_emitter.owns_world(world_authority):
            raise ValueError(
                "companion articulation authorities do not share one world"
            )
        if not isinstance(calibration, W1BinauralCalibration):
            raise TypeError(
                "companion articulation calibration is not typed"
            )
        calibration.verify()
        if companion_port_id != SECOND_BODY_PORT_ID:
            raise ValueError(
                "companion articulation requires the real companion port"
            )
        actor_by_port = {
            item.port_id: item.actor_body_id
            for item in world_authority.actor_ports
        }
        companion_body_id = actor_by_port.get(companion_port_id)
        if (
            companion_port_id == PORT_ID
            or companion_body_id is None
            or companion_body_id == world_authority.self_body_id
        ):
            raise ValueError(
                "companion articulation cannot execute through self"
            )
        self._key = _key(authority_key)
        self._world = world_authority
        self._causal = causal_owner
        self._articulatory = articulatory_owner
        self._emitter = acoustic_emitter
        self._binaural_l5 = binaural_l5_owner
        self._calibration = calibration
        self._companion_port_id = companion_port_id
        self._companion_body_id = companion_body_id
        self._max_completed = _bounded_positive(
            max_completed_demonstrations,
            "completed companion articulation capacity",
        )
        self._completed_synthesis_receipts: tuple[str, ...] = ()
        self._next_source_sample = 0
        self._transaction_active = False
        self._lock = threading.RLock()

    def _has_unsettled_transaction_locked(self) -> bool:
        causal_status = self._causal.status()
        l5_status = self._binaural_l5.status()
        return (
            self._transaction_active
            or self._emitter.status()["prepared"] != 0
            or self._world.status()["prepared_action_execution"] != 0
            or causal_status["prepared_reservation"] != 0
            or causal_status["atomic_sequence"] != 0
            or l5_status["prepared"] != 0
            or l5_status["atomic_sequence"] != 0
        )

    @property
    def next_source_time_start(self) -> Fraction:
        """Return the next active onset after one authenticated rest hop."""

        with self._lock:
            return Fraction(
                self._next_source_sample + OBSERVATION_HOP_SAMPLES,
                VOCAL_SAMPLE_RATE_HZ,
            )

    @staticmethod
    def _reindex(
        values: tuple[NativeSensorySubstreamInput, ...],
    ) -> tuple[NativeSensorySubstreamInput, ...]:
        return tuple(
            replace(value, topology_index=index)
            for index, value in enumerate(values)
        )

    def _receipt(
        self,
        *,
        occurrence: int,
        synthesis: ArticulatorySynthesis,
        execution: ActionExecutionReceipt,
        acoustic_emission_receipt_sha256: str,
        settlement: CausalExperienceSettlement,
        binaural_l5: W1BinauralAuditoryL5Experience,
        binaural_receptors: W1BinauralReceptorSettlement,
        mouth_actuator_trajectory_sha256: str,
        mouth_aperture_trajectory_sha256: str,
        mouth_aperture_sample_count: int,
        mouth_aperture_min_mm2: int,
        mouth_aperture_max_mm2: int,
        left_pressure_sha256: str,
        right_pressure_sha256: str,
        left_delay_samples: int,
        right_delay_samples: int,
        left_attenuation: Fraction,
        right_attenuation: Fraction,
        total_sample_count: int,
        post_rest_sample_count: int,
        relaxation_sample_count: int,
        terminal_traveling_wave_state_sha256: str,
    ) -> W1CompanionArticulatoryDemonstrationReceipt:
        field_count, field_custody = _field_custody(settlement)
        provisional = W1CompanionArticulatoryDemonstrationReceipt(
            occurrence=occurrence,
            source_sample_start=self._next_source_sample,
            source_sample_end=(
                self._next_source_sample + total_sample_count
            ),
            active_source_sample_start=(
                self._next_source_sample + OBSERVATION_HOP_SAMPLES
            ),
            active_source_sample_end=(
                self._next_source_sample
                + OBSERVATION_HOP_SAMPLES
                + synthesis.program.sample_count
            ),
            source_time_start=Fraction(
                self._next_source_sample,
                VOCAL_SAMPLE_RATE_HZ,
            ),
            source_time_end=Fraction(
                self._next_source_sample + total_sample_count,
                VOCAL_SAMPLE_RATE_HZ,
            ),
            pre_rest_sample_count=OBSERVATION_HOP_SAMPLES,
            post_rest_sample_count=post_rest_sample_count,
            relaxation_sample_count=relaxation_sample_count,
            neutral_tract_calibration_receipt_sha256=(
                NEUTRAL_TRACT_CALIBRATION_RECEIPT_SHA256
            ),
            terminal_traveling_wave_state_sha256=(
                terminal_traveling_wave_state_sha256
            ),
            synthesis_receipt_sha256=(
                synthesis.receipt.authority_receipt_sha256
            ),
            actuator_full_field_receipt_sha256=(
                synthesis.receipt.actuator_full_field_receipt_sha256
            ),
            world_before_receipt_sha256=(
                execution.before.authority_receipt_sha256
            ),
            world_after_receipt_sha256=(
                execution.after.authority_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                execution.authority_receipt_sha256
            ),
            acoustic_emission_receipt_sha256=(
                acoustic_emission_receipt_sha256
            ),
            causal_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            binaural_l5_receipt_sha256=(
                binaural_l5.authority_receipt_sha256
            ),
            binaural_receptor_settlement_receipt_sha256=(
                binaural_receptors.authority_receipt_sha256
            ),
            mouth_actuator_trajectory_sha256=(
                mouth_actuator_trajectory_sha256
            ),
            mouth_aperture_trajectory_sha256=(
                mouth_aperture_trajectory_sha256
            ),
            mouth_aperture_sample_count=mouth_aperture_sample_count,
            mouth_aperture_min_mm2=mouth_aperture_min_mm2,
            mouth_aperture_max_mm2=mouth_aperture_max_mm2,
            left_pressure_sha256=left_pressure_sha256,
            right_pressure_sha256=right_pressure_sha256,
            left_delay_samples=left_delay_samples,
            right_delay_samples=right_delay_samples,
            left_attenuation=left_attenuation,
            right_attenuation=right_attenuation,
            full_dsf_tuple_count=field_count,
            full_dsf_custody_sha256=field_custody,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            DEMONSTRATION_DOMAIN + _canonical(provisional.payload()),
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
        result.verify(self._key)
        if len(_canonical(result.payload())) > (
            MAX_DEMONSTRATION_RECEIPT_BYTES
        ):
            raise ValueError(
                "companion articulation receipt exceeds its byte boundary"
            )
        return result

    def demonstrate(
        self,
        synthesis: ArticulatorySynthesis,
    ) -> W1CompanionArticulatoryDemonstration:
        """Execute and settle one fresh external articulatory occurrence."""

        self._articulatory.verify_synthesis(synthesis)
        with self._lock:
            if self._has_unsettled_transaction_locked():
                raise RuntimeError(
                    "companion articulation has stranded prepared state"
                )
            synthesis_receipt = (
                synthesis.receipt.authority_receipt_sha256
            )
            if synthesis_receipt in self._completed_synthesis_receipts:
                raise ValueError(
                    "companion articulatory synthesis was replayed"
                )
            if len(self._completed_synthesis_receipts) >= self._max_completed:
                raise ValueError(
                    "companion articulation capacity is exhausted"
                )
            expected_time = Fraction(
                self._next_source_sample + OBSERVATION_HOP_SAMPLES,
                VOCAL_SAMPLE_RATE_HZ,
            )
            if (
                synthesis.receipt.source_time_start != expected_time
                or synthesis.receipt.source_time_end
                != expected_time + Fraction(
                    synthesis.program.sample_count,
                    VOCAL_SAMPLE_RATE_HZ,
                )
            ):
                raise ValueError(
                    "companion articulation source clock does not match"
                )

            pressure = generate_articulatory_pressure_with_quiescence(
                program=synthesis.program,
                neutral_section_area_mm2=(
                    NEUTRAL_TRACT_SECTION_AREAS_MM2
                ),
            )
            if pcm16_bytes(pressure.active_radiated_pressure_pcm) != (
                synthesis.radiated_pcm_s16le
            ):
                raise ValueError(
                    "continuous articulation differs from authenticated synthesis"
                )
            mouth_areas_active = _mouth_area_trajectory(synthesis)
            if len(set(mouth_areas_active)) <= 1:
                raise ValueError(
                    "changing companion articulation produced a static mouth"
                )

            before = self._world.observation_snapshot()
            intent_payload = {
                "occurrence": len(self._completed_synthesis_receipts),
                "schema": (
                    "guala.w1.companion_articulation.physical_intent.v1"
                ),
                "source_sample_start": (
                    self._next_source_sample
                    + OBSERVATION_HOP_SAMPLES
                ),
                "synthesis_receipt_sha256": synthesis_receipt,
                "world_before_receipt_sha256": (
                    before.authority_receipt_sha256
                ),
            }
            intent_receipt = _digest({
                "authority_hmac_sha256": hmac.new(
                    self._key,
                    DEMONSTRATION_DOMAIN + _canonical(intent_payload),
                    hashlib.sha256,
                ).hexdigest(),
                "payload": intent_payload,
            })
            epoch_token = hmac.new(
                self._key,
                DEMONSTRATION_DOMAIN
                + b"epoch\0"
                + _canonical(intent_payload),
                hashlib.sha256,
            ).hexdigest()
            command = VocalizeCommand(
                epoch_commitment_sha256=hashlib.sha256(
                    epoch_token.encode("utf-8")
                ).hexdigest(),
                sequence=before.revision,
                source_sample_start=(
                    self._next_source_sample
                    + OBSERVATION_HOP_SAMPLES
                ),
                pcm_sha256=hashlib.sha256(
                    synthesis.radiated_pcm_s16le
                ).hexdigest(),
                sample_count=synthesis.program.sample_count,
            )
            command_payload = encode_command(command)
            reserved: CausalExperienceSettlement | None = None
            prepared_l5: W1BinauralAuditoryL5Experience | None = None
            prepared_world = None
            causal_token: str | None = None
            l5_token: str | None = None
            causal_sequence_undo = None
            l5_sequence_undo = None
            prepared_emission = None
            causal_reservation_live = False
            l5_preparation_live = False
            emitter_preparation_live = False
            state_staged = False
            prior_completed = self._completed_synthesis_receipts
            prior_next_source_sample = self._next_source_sample
            self._transaction_active = True
            try:
                prepared_world = self._world.prepare_port_command(
                    port_id=self._companion_port_id,
                    command_payload=command_payload,
                    causal_intent_receipt_sha256=intent_receipt,
                    expected_revision=before.revision,
                )
                if isinstance(prepared_world, ActionExecutionReceipt):
                    self._world.verify_execution_receipt(prepared_world)
                    raise ValueError(
                        "companion articulation world preparation rejected: "
                        f"{prepared_world.reason}"
                    )
                execution = prepared_world.execution_receipt
                self._world.verify_execution_receipt(execution)
                if (
                    execution.disposition != "applied"
                    or execution.port_id != self._companion_port_id
                    or execution.actor_body_id != self._companion_body_id
                    or execution.before != before
                ):
                    raise ValueError(
                        "companion articulation did not prepare externally"
                    )
                after = execution.after
                if self._world.observation_snapshot() != before:
                    raise ValueError(
                        "companion articulation preparation changed the world"
                    )
                prepared_emission = self._emitter.prepare_emission(
                    epoch_token=epoch_token,
                    sequence=before.revision,
                    source_sample_start=(
                        self._next_source_sample
                        + OBSERVATION_HOP_SAMPLES
                    ),
                    prepared_world_action=prepared_world,
                    command_payload=command_payload,
                    emitter_port_id=self._companion_port_id,
                    pcm_s16le=synthesis.radiated_pcm_s16le,
                )
                emitter_preparation_live = True
                self._emitter.verify_prepared_emission(prepared_emission)

                self_body = body_from_snapshot(after, after.self_body_id)
                companion_body = body_from_snapshot(
                    after,
                    self._companion_body_id,
                )
                ears = calibrated_ear_positions(
                    self_body,
                    self._calibration.ear_separation_mm,
                )
                if ears is None:
                    raise ValueError(
                        "companion articulation has no calibrated two-ear pose"
                    )
                source_pressure = (
                    *signed_pcm16_samples(
                        synthesis.radiated_pcm_s16le
                    ),
                    *pressure.relaxation_radiated_pressure_pcm,
                )
                (
                    left_active_pcm,
                    left_pending,
                    _left_pending_receipts,
                    _left_contributors,
                    left_delay,
                    left_attenuation,
                ) = render_ear_pressure(
                    source_pressure,
                    source=companion_body.pose.position,
                    ear=ears[0],
                    reference_distance_mm=(
                        self._calibration.reference_distance_mm
                    ),
                    pending_samples=(),
                    pending_receipt_sha256s=(),
                    emission_receipt_sha256=(
                        prepared_emission
                        .prospective_emission_receipt_sha256
                    ),
                )
                (
                    right_active_pcm,
                    right_pending,
                    _right_pending_receipts,
                    _right_contributors,
                    right_delay,
                    right_attenuation,
                ) = render_ear_pressure(
                    source_pressure,
                    source=companion_body.pose.position,
                    ear=ears[1],
                    reference_distance_mm=(
                        self._calibration.reference_distance_mm
                    ),
                    pending_samples=(),
                    pending_receipt_sha256s=(),
                    emission_receipt_sha256=(
                        prepared_emission
                        .prospective_emission_receipt_sha256
                    ),
                )
                continuous_core_count = (
                    OBSERVATION_HOP_SAMPLES
                    + len(source_pressure)
                    + max(left_delay, right_delay)
                )
                total_sample_count = (
                    (
                        continuous_core_count
                        + OBSERVATION_HOP_SAMPLES
                        - 1
                    )
                    // OBSERVATION_HOP_SAMPLES
                    * OBSERVATION_HOP_SAMPLES
                    + OBSERVATION_HOP_SAMPLES
                )
                post_rest_sample_count = (
                    total_sample_count - continuous_core_count
                )
                left_active = signed_pcm16_samples(left_active_pcm)
                right_active = signed_pcm16_samples(right_active_pcm)
                left_samples = (
                    (0,) * OBSERVATION_HOP_SAMPLES
                    + left_active
                    + left_pending
                    + (0,) * (
                        total_sample_count
                        - OBSERVATION_HOP_SAMPLES
                        - len(left_active)
                        - len(left_pending)
                    )
                )
                right_samples = (
                    (0,) * OBSERVATION_HOP_SAMPLES
                    + right_active
                    + right_pending
                    + (0,) * (
                        total_sample_count
                        - OBSERVATION_HOP_SAMPLES
                        - len(right_active)
                        - len(right_pending)
                    )
                )
                left_pcm = pcm16_bytes(left_samples)
                right_pcm = pcm16_bytes(right_samples)
                if (
                    (
                        left_delay != right_delay
                        or left_attenuation != right_attenuation
                    )
                    and left_pcm == right_pcm
                ):
                    raise ValueError(
                        "resolvable two-ear paths produced identical pressure"
                    )
                if (
                    any(left_samples[-post_rest_sample_count:])
                    or any(right_samples[-post_rest_sample_count:])
                ):
                    raise ValueError(
                        "companion articulation did not end in zero ear pressure"
                    )

                source_start = Fraction(
                    self._next_source_sample,
                    VOCAL_SAMPLE_RATE_HZ,
                )
                source_end = Fraction(
                    self._next_source_sample + total_sample_count,
                    VOCAL_SAMPLE_RATE_HZ,
                )
                physical = physical_receptor_substreams(
                    before,
                    after,
                    causal_transition=True,
                    source_time_start=source_start,
                    source_time_end=source_end,
                )
                sight = physical[PhysicalSense.SIGHT]
                mouth_areas = (
                    (NEUTRAL_TRACT_SECTION_AREAS_MM2[-1],)
                    * OBSERVATION_HOP_SAMPLES
                    + mouth_areas_active
                    + (NEUTRAL_TRACT_SECTION_AREAS_MM2[-1],)
                    * (
                        total_sample_count
                        - OBSERVATION_HOP_SAMPLES
                        - len(mouth_areas_active)
                    )
                )
                (
                    mouth_input,
                    mouth_commitment,
                    mouth_actuator_commitment,
                    mouth_minimum,
                    mouth_maximum,
                ) = _mouth_aperture_input(
                    mouth_areas_mm2=mouth_areas,
                    source_time_start=source_start,
                    eye=self_body.pose.position,
                    eye_heading_millidegrees=(
                        self_body.pose.heading_millidegrees
                    ),
                    companion_position=companion_body.pose.position,
                    topology_index=len(sight),
                    reference_distance_mm=(
                        self._calibration.reference_distance_mm
                    ),
                )
                left_custody = binaural_sound_field_inputs(
                    ear="left",
                    topology_index=0,
                    pcm=left_pcm,
                    source_time_start=source_start,
                )
                right_custody = binaural_sound_field_inputs(
                    ear="right",
                    topology_index=len(left_custody),
                    pcm=right_pcm,
                    source_time_start=source_start,
                )
                left_custody.verify()
                right_custody.verify()
                observed = {
                    PhysicalSense.SIGHT: self._reindex(
                        (*sight, mouth_input)
                    ),
                    PhysicalSense.SOUND: self._reindex(
                        (*left_custody, *right_custody)
                    ),
                    PhysicalSense.TOUCH: self._reindex(
                        physical[PhysicalSense.TOUCH]
                    ),
                    PhysicalSense.BODY: self._reindex(
                        physical[PhysicalSense.BODY]
                    ),
                }
                built = build_transaction_owned_six_sense_full_field(
                    assembly_id=(
                        "w1-companion-articulation-occurrence-"
                        f"{len(self._completed_synthesis_receipts):016d}"
                    ),
                    source_time_start=source_start,
                    source_time_end=source_end,
                    observed_substreams=observed,
                    states={
                        sense: (
                            SenseBoundaryState.OBSERVED
                            if sense in observed
                            else SenseBoundaryState.SENSOR_UNAVAILABLE
                        )
                        for sense in SENSE_ORDER
                    },
                )
                causal_token = self._causal.begin_atomic_sequence()
                l5_token = self._binaural_l5.begin_atomic_sequence()
                reserved = self._causal.settle(
                    built,
                    routing_chis=(),
                    source_tags=(),
                    commit=False,
                    reserve=True,
                )
                causal_reservation_live = True
                prepared_l5 = self._binaural_l5.prepare(reserved)
                l5_preparation_live = True
                binaural_receptors = settle_w1_binaural_receptors(
                    left_custody=left_custody,
                    right_custody=right_custody,
                    causal_settlement=reserved,
                    w1_l5=prepared_l5,
                )
                receipt = self._receipt(
                    occurrence=len(
                        self._completed_synthesis_receipts
                    ),
                    synthesis=synthesis,
                    execution=execution,
                    acoustic_emission_receipt_sha256=(
                        prepared_emission
                        .prospective_emission_receipt_sha256
                    ),
                    settlement=reserved,
                    binaural_l5=prepared_l5,
                    binaural_receptors=binaural_receptors,
                    mouth_actuator_trajectory_sha256=(
                        mouth_actuator_commitment
                    ),
                    mouth_aperture_trajectory_sha256=mouth_commitment,
                    mouth_aperture_sample_count=len(
                        mouth_input.normalized_signal
                    ),
                    mouth_aperture_min_mm2=mouth_minimum,
                    mouth_aperture_max_mm2=mouth_maximum,
                    left_pressure_sha256=hashlib.sha256(
                        left_pcm
                    ).hexdigest(),
                    right_pressure_sha256=hashlib.sha256(
                        right_pcm
                    ).hexdigest(),
                    left_delay_samples=left_delay,
                    right_delay_samples=right_delay,
                    left_attenuation=left_attenuation,
                    right_attenuation=right_attenuation,
                    total_sample_count=total_sample_count,
                    post_rest_sample_count=post_rest_sample_count,
                    relaxation_sample_count=len(
                        pressure.relaxation_radiated_pressure_pcm
                    ),
                    terminal_traveling_wave_state_sha256=_digest({
                        "left_pressure": list(
                            pressure.quiescent_terminal_state.left_pressure
                        ),
                        "previous_glottal_flow": (
                            pressure.quiescent_terminal_state
                            .previous_glottal_flow
                        ),
                        "right_pressure": list(
                            pressure.quiescent_terminal_state.right_pressure
                        ),
                        "schema": (
                            "guala.articulatory.traveling_wave.terminal.v1"
                        ),
                    }),
                )
                result = W1CompanionArticulatoryDemonstration(
                    receipt=receipt,
                    causal_settlement=reserved,
                    binaural_l5=prepared_l5,
                    binaural_receptor_settlement=binaural_receptors,
                )
                self.verify(result)
                completed = (
                    *self._completed_synthesis_receipts,
                    synthesis_receipt,
                )
                next_source_sample = (
                    self._next_source_sample + total_sample_count
                )
                self._binaural_l5.commit_prepared(
                    prepared_l5
                )
                l5_preparation_live = False
                self._causal.commit_prepared(reserved)
                causal_reservation_live = False
                causal_sequence_undo = self._causal.commit_atomic_sequence(
                    causal_token
                )
                l5_sequence_undo = (
                    self._binaural_l5.commit_atomic_sequence(l5_token)
                )
                self._completed_synthesis_receipts = completed
                self._next_source_sample = next_source_sample
                self._transaction_active = False
                state_staged = True
                self._emitter.commit_prepared_emission(
                    prepared_emission
                )
                emitter_preparation_live = False
                self._world.commit_prepared_action(prepared_world)
                return result
            except BaseException as original_error:
                if state_staged:
                    self._completed_synthesis_receipts = prior_completed
                    self._next_source_sample = prior_next_source_sample
                cleanup_steps = []
                if l5_sequence_undo is not None:
                    cleanup_steps.append((
                        "rollback published binaural L5 sequence",
                        lambda: self._binaural_l5
                        .rollback_committed_atomic_sequence(
                            l5_sequence_undo
                        ),
                    ))
                if causal_sequence_undo is not None:
                    cleanup_steps.append((
                        "rollback published causal sequence",
                        lambda: self._causal
                        .rollback_committed_atomic_sequence(
                            causal_sequence_undo
                        ),
                    ))
                if l5_preparation_live and prepared_l5 is not None:
                    cleanup_steps.append((
                        "discard prepared binaural L5 experience",
                        lambda: self._binaural_l5.discard_prepared(
                            prepared_l5
                        ),
                    ))
                if causal_reservation_live and reserved is not None:
                    cleanup_steps.append((
                        "discard prepared causal settlement",
                        lambda: self._causal.discard_prepared(reserved),
                    ))
                if l5_token is not None:
                    cleanup_steps.append((
                        "rollback binaural L5 atomic sequence",
                        lambda: self._binaural_l5.rollback_atomic_sequence(
                            l5_token
                        ),
                    ))
                if causal_token is not None:
                    cleanup_steps.append((
                        "rollback causal atomic sequence",
                        lambda: self._causal.rollback_atomic_sequence(
                            causal_token
                        ),
                    ))
                if (
                    emitter_preparation_live
                    and prepared_emission is not None
                ):
                    cleanup_steps.append((
                        "discard prepared acoustic emission",
                        lambda: self._emitter.discard_prepared_emission(
                            prepared_emission
                        ),
                    ))
                if prepared_world is not None and not isinstance(
                    prepared_world,
                    ActionExecutionReceipt,
                ):
                    cleanup_steps.append((
                        "discard prepared world action",
                        lambda: self._world.discard_prepared_action(
                            prepared_world
                        ),
                    ))
                cleanup_errors = []
                for label, cleanup in cleanup_steps:
                    try:
                        cleanup()
                    except BaseException as cleanup_error:
                        cleanup_error.add_note(
                            f"companion articulation cleanup step: {label}"
                        )
                        cleanup_errors.append(cleanup_error)
                self._transaction_active = bool(cleanup_errors)
                if cleanup_errors:
                    errors = [original_error, *cleanup_errors]
                    group_type = (
                        BaseExceptionGroup
                        if any(
                            not isinstance(error, Exception)
                            for error in errors
                        )
                        else ExceptionGroup
                    )
                    raise group_type(
                        "companion articulation failed and cleanup failed",
                        errors,
                    )
                raise

    def verify(
        self,
        value: W1CompanionArticulatoryDemonstration,
    ) -> None:
        if not isinstance(
            value,
            W1CompanionArticulatoryDemonstration,
        ):
            raise TypeError(
                "companion articulatory demonstration is not typed"
            )
        value.receipt.verify(self._key)
        value.causal_settlement.verify()
        value.binaural_l5.verify()
        value.binaural_receptor_settlement.verify()
        count, custody = _field_custody(value.causal_settlement)
        if (
            value.receipt.causal_settlement_receipt_sha256
            != value.causal_settlement.authority_receipt_sha256
            or value.receipt.binaural_l5_receipt_sha256
            != value.binaural_l5.authority_receipt_sha256
            or value.receipt.binaural_receptor_settlement_receipt_sha256
            != value.binaural_receptor_settlement.authority_receipt_sha256
            or value.binaural_l5.upstream_causal_settlement_receipt_sha256
            != value.causal_settlement.authority_receipt_sha256
            or (
                value.binaural_receptor_settlement
                .upstream_causal_settlement_receipt_sha256
            )
            != value.causal_settlement.authority_receipt_sha256
            or value.binaural_receptor_settlement.upstream_w1_l5
            != value.binaural_l5
            or value.receipt.full_dsf_tuple_count != count
            or value.receipt.full_dsf_custody_sha256 != custody
            or value.causal_settlement.language_events
        ):
            raise ValueError(
                "companion articulatory full-field custody changed"
            )

    def snapshot_encoded(self) -> bytes:
        """Return bounded authenticated replay and physical-clock custody."""

        with self._lock:
            binaural_status = self._binaural_l5.status()
            causal_status = self._causal.status()
            emitter_status = self._emitter.status()
            world_status = self._world.status()
            if (
                self._transaction_active
                or emitter_status["prepared"] != 0
                or world_status["prepared_action_execution"] != 0
                or causal_status["prepared_reservation"] != 0
                or causal_status["atomic_sequence"] != 0
                or binaural_status["prepared"] != 0
                or binaural_status["atomic_sequence"] != 0
                or binaural_status["settled"]
                != len(self._completed_synthesis_receipts)
            ):
                raise RuntimeError(
                    "companion articulation cold authorities diverged"
                )
            payload = {
                "companion_port_id": self._companion_port_id,
                "completed_synthesis_receipts": list(
                    self._completed_synthesis_receipts
                ),
                "max_completed": self._max_completed,
                "next_source_sample": self._next_source_sample,
                "schema": STATE_SCHEMA,
            }
            signature = hmac.new(
                self._key,
                STATE_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            encoded = _canonical({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
            if len(encoded) > MAX_DEMONSTRATION_STATE_BYTES:
                raise RuntimeError(
                    "companion articulation state exceeds its byte boundary"
                )
            return encoded

    def restore_encoded(self, encoded: bytes) -> None:
        """Restore replay and clock custody beside the restored binaural owner."""

        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > MAX_DEMONSTRATION_STATE_BYTES
        ):
            raise ValueError(
                "companion articulation state exceeds its byte boundary"
            )
        try:
            record = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "companion articulation state is unreadable"
            ) from error
        if (
            not isinstance(record, dict)
            or set(record) != {"authority_hmac_sha256", "payload"}
            or not isinstance(record.get("payload"), dict)
            or _canonical(record) != encoded
        ):
            raise ValueError(
                "companion articulation state envelope changed"
            )
        payload = record["payload"]
        if set(payload) != {
            "companion_port_id",
            "completed_synthesis_receipts",
            "max_completed",
            "next_source_sample",
            "schema",
        }:
            raise ValueError(
                "companion articulation state fields changed"
            )
        signature = hmac.new(
            self._key,
            STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        completed = payload.get("completed_synthesis_receipts")
        next_source_sample = payload.get("next_source_sample")
        if (
            payload.get("schema") != STATE_SCHEMA
            or payload.get("companion_port_id")
            != self._companion_port_id
            or payload.get("max_completed") != self._max_completed
            or not hmac.compare_digest(
                signature,
                str(record.get("authority_hmac_sha256")),
            )
            or not isinstance(completed, list)
            or len(completed) > self._max_completed
            or len(set(completed)) != len(completed)
            or any(
                not isinstance(value, str)
                or _sha256(value, "completed synthesis receipt") != value
                for value in completed
            )
            or isinstance(next_source_sample, bool)
            or not isinstance(next_source_sample, int)
            or next_source_sample < 0
            or (bool(completed) != (next_source_sample > 0))
        ):
            raise ValueError(
                "companion articulation state authority changed"
            )
        with self._lock:
            if (
                self._transaction_active
                or self._completed_synthesis_receipts
                or self._next_source_sample != 0
                or self._emitter.status()["prepared"] != 0
                or self._world.status()["prepared_action_execution"] != 0
                or self._causal.status()["prepared_reservation"] != 0
                or self._causal.status()["atomic_sequence"] != 0
                or self._binaural_l5.status()["prepared"] != 0
                or self._binaural_l5.status()["atomic_sequence"] != 0
                or self._binaural_l5.status()["settled"] != len(completed)
            ):
                raise ValueError(
                    "companion articulation restore authorities diverged"
                )
            self._completed_synthesis_receipts = tuple(completed)
            self._next_source_sample = next_source_sample
            if self.snapshot_encoded() != encoded:
                raise ValueError(
                    "companion articulation restored state changed"
                )

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "completed": len(
                    self._completed_synthesis_receipts
                ),
                "max_completed": self._max_completed,
                "next_source_sample": self._next_source_sample,
                "prepared": int(
                    self._has_unsettled_transaction_locked()
                ),
                "retained_raw_pcm_bytes": 0,
                "schema": (
                    "guala.w1.companion_articulation.status.v1"
                ),
            }


__all__ = (
    "ARTICULATOR_RETINAL_CONE",
    "DEFAULT_MAX_COMPLETED_DEMONSTRATIONS",
    "MAX_DEMONSTRATION_RECEIPT_BYTES",
    "MAX_DEMONSTRATION_STATE_BYTES",
    "W1CompanionArticulatoryDemonstration",
    "W1CompanionArticulatoryDemonstrationAuthority",
    "W1CompanionArticulatoryDemonstrationReceipt",
)
