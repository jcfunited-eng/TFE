"""Exact bounded separation of two anonymous W1 acoustic paths.

This module does not perform blind source separation.  A mono pressure trace
cannot determine two arbitrary causes, and two ears still cannot distinguish
two causes whose acoustic transfer paths are linearly identical.

The admitted case is narrower and physical: two calibrated ears settle one
closed pressure interval and W1's anonymous multisensory geometry supplies two
exact delay/attenuation paths.  The resulting sparse linear equations are
solved with ``Fraction`` arithmetic.  A source is released only when every
sample is uniquely determined, every redundant equation agrees, and exact
forward rendering reproduces both ear captures.  No tolerance, score,
probability, transcript, source label, chi, or learned classifier participates.

Recovered integral PCM can then enter the existing canonical auditory
transducer and frozen L0--L4 kernel independently.  The returned auditory L5
experiences retain every explicit D_k, M_k, R_rev_k, U_star_k, C_k, P_k, and
B_k field; the separation receipt is physical provenance, not a replacement
field or a source identity.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import deque
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.embodiment_world import MAX_VOCAL_SAMPLE_COUNT
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


EXACT_BINAURAL_SEPARATION_SCHEMA = (
    "guala.w1.exact_binaural_source_separation.v1"
)
EXACT_BINAURAL_SOURCE_FIELD_SCHEMA = (
    "guala.w1.exact_binaural_source_field.v1"
)
SOURCE_COUNT = 2
EAR_COUNT = 2
MAX_PATH_DELAY_SAMPLES = 2_048
MAX_EXACT_BINAURAL_SOURCE_SAMPLES = MAX_VOCAL_SAMPLE_COUNT
PCM_MIN = -(1 << 15)
PCM_MAX = (1 << 15) - 1


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("binaural transfer value must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _pcm_samples(value: bytes, name: str) -> tuple[int, ...]:
    if not isinstance(value, bytes) or len(value) % 2:
        raise ValueError(f"{name} must be signed little-endian PCM16")
    return tuple(item[0] for item in struct.iter_unpack("<h", value))


def _pcm_bytes(values: tuple[int, ...]) -> bytes:
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not PCM_MIN <= value <= PCM_MAX
        for value in values
    ):
        raise ValueError("separated pressure left calibrated PCM16")
    return struct.pack(f"<{len(values)}h", *values)


@dataclass(frozen=True, slots=True)
class ExactBinauralTransferPath:
    """One anonymous point-source path to the two calibrated ears."""

    left_delay_samples: int
    right_delay_samples: int
    left_attenuation: Fraction
    right_attenuation: Fraction

    def verify(self) -> None:
        for name, value in (
            ("left", self.left_delay_samples),
            ("right", self.right_delay_samples),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_PATH_DELAY_SAMPLES
            ):
                raise ValueError(
                    f"{name} binaural transfer delay is outside its boundary"
                )
        for name, value in (
            ("left", self.left_attenuation),
            ("right", self.right_attenuation),
        ):
            if not isinstance(value, Fraction) or not 0 < value <= 1:
                raise ValueError(
                    f"{name} binaural transfer attenuation is invalid"
                )

    def payload(self) -> dict[str, object]:
        self.verify()
        return {
            "left_attenuation": _fraction_text(self.left_attenuation),
            "left_delay_samples": self.left_delay_samples,
            "right_attenuation": _fraction_text(self.right_attenuation),
            "right_delay_samples": self.right_delay_samples,
        }


class ExactBinauralSeparationState(str, Enum):
    SEPARATED = "separated"
    INDETERMINATE_INSUFFICIENT_SENSORS = (
        "indeterminate_insufficient_sensors"
    )
    INDETERMINATE_NONUNIQUE_TRANSFER = (
        "indeterminate_nonunique_transfer"
    )
    INDETERMINATE_INCONSISTENT_EVIDENCE = (
        "indeterminate_inconsistent_evidence"
    )
    INDETERMINATE_PCM_QUANTIZATION = (
        "indeterminate_pcm_quantization"
    )


_STATE_REASON = {
    ExactBinauralSeparationState.SEPARATED: (
        "two_exact_anonymous_paths_uniquely_solved"
    ),
    ExactBinauralSeparationState.INDETERMINATE_INSUFFICIENT_SENSORS: (
        "one_pressure_channel_cannot_determine_two_arbitrary_sources"
    ),
    ExactBinauralSeparationState.INDETERMINATE_NONUNIQUE_TRANSFER: (
        "binaural_transfer_equations_do_not_have_one_unique_source_pair"
    ),
    ExactBinauralSeparationState.INDETERMINATE_INCONSISTENT_EVIDENCE: (
        "closed_binaural_capture_disagrees_with_the_supplied_physical_paths"
    ),
    ExactBinauralSeparationState.INDETERMINATE_PCM_QUANTIZATION: (
        "unique_pressure_solution_is_not_integral_calibrated_pcm16"
    ),
}


@dataclass(frozen=True, slots=True)
class ExactBinauralSourceSeparation:
    """A transient exact result; raw pressure is never in its receipt."""

    state: ExactBinauralSeparationState
    reason: str
    source_sample_count: int
    capture_sample_count: int
    paths: tuple[ExactBinauralTransferPath, ...]
    left_pcm_sha256: str
    right_pcm_sha256: str | None
    separated_pcm_s16le: tuple[bytes, ...]
    authority_receipt_sha256: str

    def authority_payload(self) -> dict[str, object]:
        return {
            "capture_sample_count": self.capture_sample_count,
            "left_pcm_sha256": self.left_pcm_sha256,
            "paths": [value.payload() for value in self.paths],
            "reason": self.reason,
            "right_pcm_sha256": self.right_pcm_sha256,
            "schema": EXACT_BINAURAL_SEPARATION_SCHEMA,
            "separated_pcm_sha256s": [
                hashlib.sha256(value).hexdigest()
                for value in self.separated_pcm_s16le
            ],
            "source_sample_count": self.source_sample_count,
            "state": self.state.value,
        }

    def verify(self) -> None:
        if (
            not isinstance(self.state, ExactBinauralSeparationState)
            or self.reason != _STATE_REASON[self.state]
            or isinstance(self.source_sample_count, bool)
            or not isinstance(self.source_sample_count, int)
            or not 1
            <= self.source_sample_count
            <= MAX_EXACT_BINAURAL_SOURCE_SAMPLES
            or isinstance(self.capture_sample_count, bool)
            or not isinstance(self.capture_sample_count, int)
            or self.capture_sample_count < self.source_sample_count
            or len(self.paths) != SOURCE_COUNT
        ):
            raise ValueError("exact binaural separation boundary changed")
        for value in self.paths:
            value.verify()
        if self.capture_sample_count != self.source_sample_count + max(
            max(
                value.left_delay_samples,
                value.right_delay_samples,
            )
            for value in self.paths
        ):
            raise ValueError("exact binaural propagation tail changed")
        sha256_digest(self.left_pcm_sha256, "left binaural pressure")
        if self.right_pcm_sha256 is not None:
            sha256_digest(self.right_pcm_sha256, "right binaural pressure")
        if self.state is ExactBinauralSeparationState.SEPARATED:
            if (
                self.right_pcm_sha256 is None
                or len(self.separated_pcm_s16le) != SOURCE_COUNT
                or any(
                    len(value) != self.source_sample_count * 2
                    for value in self.separated_pcm_s16le
                )
            ):
                raise ValueError("separated binaural pressure is incomplete")
            for value in self.separated_pcm_s16le:
                _pcm_samples(value, "separated pressure")
        elif self.separated_pcm_s16le:
            raise ValueError(
                "indeterminate binaural evidence released source pressure"
            )
        if receipt_sha256(_canonical(self.authority_payload())) != (
            self.authority_receipt_sha256
        ):
            raise ValueError("exact binaural separation authority changed")


@dataclass(frozen=True, slots=True)
class ExactSeparatedAuditoryField:
    """One anonymous separated source mounted through full auditory L0--L4."""

    source_ordinal: int
    separation_authority_receipt_sha256: str
    auditory_l5: AuditoryL5Experience
    authority_receipt_sha256: str

    def authority_payload(self) -> dict[str, object]:
        return {
            "auditory_l5_authority_receipt_sha256": (
                self.auditory_l5.authority_receipt_sha256
            ),
            "schema": EXACT_BINAURAL_SOURCE_FIELD_SCHEMA,
            "separation_authority_receipt_sha256": (
                self.separation_authority_receipt_sha256
            ),
            "source_ordinal": self.source_ordinal,
        }

    def verify(self) -> None:
        self.auditory_l5.verify()
        sha256_digest(
            self.separation_authority_receipt_sha256,
            "exact binaural separation",
        )
        if (
            isinstance(self.source_ordinal, bool)
            or not isinstance(self.source_ordinal, int)
            or not 0 <= self.source_ordinal < SOURCE_COUNT
        ):
            raise ValueError("separated source ordinal changed")
        for channel in self.auditory_l5.channels:
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                if (
                    not component.l4_field_tuples
                    or any(
                        tuple(name for name, _field in value.fields)
                        != DSF_FIELD_ORDER
                        for value in component.l4_field_tuples
                    )
                ):
                    raise ValueError(
                        "separated auditory source lost explicit DSF fields"
                    )
        if receipt_sha256(_canonical(self.authority_payload())) != (
            self.authority_receipt_sha256
        ):
            raise ValueError("separated auditory field authority changed")


def _result(
    *,
    state: ExactBinauralSeparationState,
    source_sample_count: int,
    capture_sample_count: int,
    paths: tuple[ExactBinauralTransferPath, ...],
    left_pcm_sha256: str,
    right_pcm_sha256: str | None,
    separated_pcm_s16le: tuple[bytes, ...] = (),
) -> ExactBinauralSourceSeparation:
    draft = ExactBinauralSourceSeparation(
        state=state,
        reason=_STATE_REASON[state],
        source_sample_count=source_sample_count,
        capture_sample_count=capture_sample_count,
        paths=paths,
        left_pcm_sha256=left_pcm_sha256,
        right_pcm_sha256=right_pcm_sha256,
        separated_pcm_s16le=separated_pcm_s16le,
        authority_receipt_sha256="0" * 64,
    )
    result = ExactBinauralSourceSeparation(
        state=draft.state,
        reason=draft.reason,
        source_sample_count=draft.source_sample_count,
        capture_sample_count=draft.capture_sample_count,
        paths=draft.paths,
        left_pcm_sha256=draft.left_pcm_sha256,
        right_pcm_sha256=draft.right_pcm_sha256,
        separated_pcm_s16le=draft.separated_pcm_s16le,
        authority_receipt_sha256=receipt_sha256(
            _canonical(draft.authority_payload())
        ),
    )
    result.verify()
    return result


def _render(
    sources: tuple[tuple[Fraction, ...], ...],
    *,
    paths: tuple[ExactBinauralTransferPath, ...],
    capture_sample_count: int,
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    rendered: list[tuple[Fraction, ...]] = []
    for ear_index in range(EAR_COUNT):
        ear_values: list[Fraction] = []
        for capture_index in range(capture_sample_count):
            pressure = Fraction(0)
            for source_index, source in enumerate(sources):
                path = paths[source_index]
                delay = (
                    path.left_delay_samples
                    if ear_index == 0 else path.right_delay_samples
                )
                source_sample_index = capture_index - delay
                if 0 <= source_sample_index < len(source):
                    attenuation = (
                        path.left_attenuation
                        if ear_index == 0 else path.right_attenuation
                    )
                    pressure += (
                        attenuation * source[source_sample_index]
                    )
            ear_values.append(pressure)
        rendered.append(tuple(ear_values))
    return rendered[0], rendered[1]


def _solve_exact_sources(
    left: tuple[int, ...],
    right: tuple[int, ...],
    *,
    paths: tuple[ExactBinauralTransferPath, ...],
    source_sample_count: int,
) -> tuple[
    ExactBinauralSeparationState,
    tuple[tuple[Fraction, ...], ...],
]:
    capture_sample_count = len(left)
    equation_variables: list[list[int]] = []
    equation_coefficients: list[list[Fraction]] = []
    residuals: list[Fraction] = []
    adjacency: list[list[int]] = [
        [] for _value in range(SOURCE_COUNT * source_sample_count)
    ]

    for ear_index, observed in enumerate((left, right)):
        for capture_index in range(capture_sample_count):
            variables: list[int] = []
            coefficients: list[Fraction] = []
            for source_index, path in enumerate(paths):
                delay = (
                    path.left_delay_samples
                    if ear_index == 0 else path.right_delay_samples
                )
                source_index_in_interval = capture_index - delay
                if 0 <= source_index_in_interval < source_sample_count:
                    variable = (
                        source_index * source_sample_count
                        + source_index_in_interval
                    )
                    coefficient = (
                        path.left_attenuation
                        if ear_index == 0 else path.right_attenuation
                    )
                    variables.append(variable)
                    coefficients.append(coefficient)
            equation_index = len(residuals)
            equation_variables.append(variables)
            equation_coefficients.append(coefficients)
            residuals.append(Fraction(observed[capture_index]))
            for variable in variables:
                adjacency[variable].append(equation_index)

    known: list[Fraction | None] = [None] * len(adjacency)
    pending = deque(range(len(residuals)))
    pair_equations: dict[tuple[int, int], list[int]] = {}
    inconsistent = False

    def assign(variable: int, value: Fraction) -> None:
        nonlocal inconsistent
        current = known[variable]
        if current is not None:
            if current != value:
                inconsistent = True
            return
        known[variable] = value
        for equation_index in adjacency[variable]:
            variables = equation_variables[equation_index]
            if variable not in variables:
                continue
            position = variables.index(variable)
            coefficient = equation_coefficients[equation_index].pop(
                position
            )
            variables.pop(position)
            residuals[equation_index] -= coefficient * value
            pending.append(equation_index)

    while pending and not inconsistent:
        equation_index = pending.popleft()
        variables = equation_variables[equation_index]
        coefficients = equation_coefficients[equation_index]
        residual = residuals[equation_index]
        if not variables:
            if residual:
                inconsistent = True
            continue
        if len(variables) == 1:
            assign(variables[0], residual / coefficients[0])
            continue
        if len(variables) != SOURCE_COUNT:
            raise RuntimeError(
                "two-source binaural equation exceeded its sparse topology"
            )
        ordered = tuple(sorted(variables))
        prior_equations = pair_equations.setdefault(ordered, [])
        solved_pair = False
        first_variable, second_variable = ordered

        def ordered_coefficients(index: int) -> tuple[Fraction, Fraction]:
            mounted = dict(zip(
                equation_variables[index],
                equation_coefficients[index],
                strict=True,
            ))
            return (
                mounted[first_variable],
                mounted[second_variable],
            )

        a, b = ordered_coefficients(equation_index)
        for prior_index in prior_equations:
            if (
                tuple(sorted(equation_variables[prior_index])) != ordered
            ):
                continue
            c, d = ordered_coefficients(prior_index)
            determinant = a * d - b * c
            prior_residual = residuals[prior_index]
            if determinant:
                first_value = (
                    residual * d - b * prior_residual
                ) / determinant
                second_value = (
                    a * prior_residual - residual * c
                ) / determinant
                assign(first_variable, first_value)
                assign(second_variable, second_value)
                solved_pair = True
                break
            if a * prior_residual != c * residual:
                inconsistent = True
                break
        if not solved_pair and not inconsistent:
            prior_equations.append(equation_index)

    if inconsistent:
        return (
            ExactBinauralSeparationState
            .INDETERMINATE_INCONSISTENT_EVIDENCE,
            (),
        )
    if any(value is None for value in known):
        return (
            ExactBinauralSeparationState
            .INDETERMINATE_NONUNIQUE_TRANSFER,
            (),
        )
    sources = tuple(
        tuple(
            known[source_index * source_sample_count + sample_index]
            for sample_index in range(source_sample_count)
        )
        for source_index in range(SOURCE_COUNT)
    )
    if any(
        not isinstance(value, Fraction)
        for source in sources
        for value in source
    ):
        raise RuntimeError("exact binaural solver released an untyped sample")
    rendered_left, rendered_right = _render(
        sources,
        paths=paths,
        capture_sample_count=capture_sample_count,
    )
    if (
        rendered_left != tuple(Fraction(value) for value in left)
        or rendered_right != tuple(Fraction(value) for value in right)
    ):
        return (
            ExactBinauralSeparationState
            .INDETERMINATE_INCONSISTENT_EVIDENCE,
            (),
        )
    return ExactBinauralSeparationState.SEPARATED, sources


def separate_exact_binaural_sources(
    *,
    left_pcm_s16le: bytes,
    right_pcm_s16le: bytes | None,
    paths: tuple[ExactBinauralTransferPath, ...],
    source_sample_count: int,
) -> ExactBinauralSourceSeparation:
    """Uniquely solve two closed anonymous acoustic paths or refuse release."""

    if len(paths) != SOURCE_COUNT:
        raise ValueError("exact binaural separation requires two paths")
    for path in paths:
        path.verify()
    if (
        isinstance(source_sample_count, bool)
        or not isinstance(source_sample_count, int)
        or not 1
        <= source_sample_count
        <= MAX_EXACT_BINAURAL_SOURCE_SAMPLES
    ):
        raise ValueError("exact binaural source interval is invalid")
    maximum_delay = max(
        path.left_delay_samples
        for path in paths
    )
    maximum_delay = max(
        maximum_delay,
        *(path.right_delay_samples for path in paths),
    )
    capture_sample_count = source_sample_count + maximum_delay
    left = _pcm_samples(left_pcm_s16le, "left binaural pressure")
    if len(left) != capture_sample_count:
        raise ValueError(
            "left binaural pressure does not close the propagation tail"
        )
    left_sha256 = hashlib.sha256(left_pcm_s16le).hexdigest()
    if right_pcm_s16le is None:
        return _result(
            state=ExactBinauralSeparationState
            .INDETERMINATE_INSUFFICIENT_SENSORS,
            source_sample_count=source_sample_count,
            capture_sample_count=capture_sample_count,
            paths=paths,
            left_pcm_sha256=left_sha256,
            right_pcm_sha256=None,
        )
    right = _pcm_samples(right_pcm_s16le, "right binaural pressure")
    if len(right) != capture_sample_count:
        raise ValueError(
            "right binaural pressure does not close the propagation tail"
        )
    right_sha256 = hashlib.sha256(right_pcm_s16le).hexdigest()
    state, exact_sources = _solve_exact_sources(
        left,
        right,
        paths=paths,
        source_sample_count=source_sample_count,
    )
    if state is not ExactBinauralSeparationState.SEPARATED:
        return _result(
            state=state,
            source_sample_count=source_sample_count,
            capture_sample_count=capture_sample_count,
            paths=paths,
            left_pcm_sha256=left_sha256,
            right_pcm_sha256=right_sha256,
        )
    if any(
        value.denominator != 1
        or not PCM_MIN <= value.numerator <= PCM_MAX
        for source in exact_sources
        for value in source
    ):
        return _result(
            state=ExactBinauralSeparationState
            .INDETERMINATE_PCM_QUANTIZATION,
            source_sample_count=source_sample_count,
            capture_sample_count=capture_sample_count,
            paths=paths,
            left_pcm_sha256=left_sha256,
            right_pcm_sha256=right_sha256,
        )
    separated = tuple(
        _pcm_bytes(tuple(value.numerator for value in source))
        for source in exact_sources
    )
    return _result(
        state=ExactBinauralSeparationState.SEPARATED,
        source_sample_count=source_sample_count,
        capture_sample_count=capture_sample_count,
        paths=paths,
        left_pcm_sha256=left_sha256,
        right_pcm_sha256=right_sha256,
        separated_pcm_s16le=separated,
    )


def mount_exact_separated_auditory_fields(
    separation: ExactBinauralSourceSeparation,
    *,
    source_time_start: Fraction,
) -> tuple[ExactSeparatedAuditoryField, ...]:
    """Mount each uniquely recovered source through canonical full-field L0--L4."""

    separation.verify()
    if separation.state is not ExactBinauralSeparationState.SEPARATED:
        raise ValueError(
            "indeterminate binaural evidence cannot enter auditory cognition"
        )
    if not isinstance(source_time_start, Fraction):
        raise TypeError("separated auditory source time must be exact")
    if separation.source_sample_count % OBSERVATION_HOP_SAMPLES:
        raise ValueError(
            "separated auditory source does not close one cochlear hop"
        )
    source_time_end = source_time_start + Fraction(
        separation.source_sample_count,
        REQUIRED_SAMPLE_RATE_HZ,
    )
    mounted_fields: list[ExactSeparatedAuditoryField] = []
    for source_ordinal, pcm in enumerate(separation.separated_pcm_s16le):
        samples = _pcm_samples(pcm, "separated pressure")
        capture = transduce_auditory_full_field(
            np.asarray(samples, dtype=np.float64) / 32_768.0,
            sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        )
        inputs = auditory_kernel_component_inputs(
            capture,
            source_anchor=source_time_start,
        )
        states = {
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        }
        built = build_six_sense_full_field(
            assembly_id=(
                "w1-separated-"
                f"{separation.authority_receipt_sha256[:32]}-"
                f"{source_ordinal}"
            ),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            observed_substreams={PhysicalSense.SOUND: inputs},
            states=states,
            # Every cochlear kernel component transduces the one uniquely
            # recovered acoustic source over one exact interval: one joint
            # occurrence per separated source.
            occurrences=declare_joint_source_occurrences(
                observed_substreams={PhysicalSense.SOUND: inputs},
                declared_units=(
                    tuple(
                        (PhysicalSense.SOUND, port.topology_index)
                        for port in inputs
                    ),
                ),
            ),
        )
        auditory_l5 = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None,
            max_transitions=1,
        ).settle(built, event_boundary="ambient")
        if auditory_l5 is None:
            raise RuntimeError(
                "separated auditory source did not settle full-field L5"
            )
        payload = {
            "auditory_l5_authority_receipt_sha256": (
                auditory_l5.authority_receipt_sha256
            ),
            "schema": EXACT_BINAURAL_SOURCE_FIELD_SCHEMA,
            "separation_authority_receipt_sha256": (
                separation.authority_receipt_sha256
            ),
            "source_ordinal": source_ordinal,
        }
        field = ExactSeparatedAuditoryField(
            source_ordinal=source_ordinal,
            separation_authority_receipt_sha256=(
                separation.authority_receipt_sha256
            ),
            auditory_l5=auditory_l5,
            authority_receipt_sha256=receipt_sha256(
                _canonical(payload)
            ),
        )
        field.verify()
        mounted_fields.append(field)
    return tuple(mounted_fields)


__all__ = [
    "EXACT_BINAURAL_SEPARATION_SCHEMA",
    "EXACT_BINAURAL_SOURCE_FIELD_SCHEMA",
    "ExactBinauralSeparationState",
    "ExactBinauralSourceSeparation",
    "ExactBinauralTransferPath",
    "ExactSeparatedAuditoryField",
    "MAX_EXACT_BINAURAL_SOURCE_SAMPLES",
    "MAX_PATH_DELAY_SAMPLES",
    "mount_exact_separated_auditory_fields",
    "separate_exact_binaural_sources",
]
