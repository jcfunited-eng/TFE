"""Authenticated bounded foveal observation of physical optical surfaces.

This authority receives privileged object identity only while selecting a
physical focus target.  The signed scan plan and every receptor substream
contain only physical placement, surface geometry, spectral reflectance, and
the exact ordered fixation coordinates.  Object ids, asset ids, text, OCR,
labels, meanings, and card ordinals never cross the receptor boundary.

Each optical band remains an independent native trajectory.  No cell is
averaged, bucketed, scored, or collapsed before the existing unchanged
L0--L4 full-field builder.  Long surfaces are divided only at the existing
transport sample boundary; this segmentation preserves every sample and its
global physical time.
"""

from __future__ import annotations

import hmac
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Protocol, runtime_checkable

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    MAX_NATIVE_SIGHT_SUBSTREAMS,
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    NativeJointSourceOccurrenceInput,
    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
)
from dsf_ai_service.glew_runtime.model import require_identifier
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_OPTICAL_SURFACE_COLUMNS,
    MAX_OPTICAL_SURFACE_ROWS,
    EmbodiedObject,
    ObjectOpticalSurface,
    ObservationSnapshot,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    source_evidence_sample_commitment_sha256,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    MAX_WORLD_REVISION,
    OPTICAL_BANDS,
    _authority_key,
    _digest,
    _sign,
    _verify_observation,
)


FOVEAL_SCAN_SCHEMA = "guala.embodiment.physical_foveal_scan.v1"
FOVEAL_SCAN_DOMAIN = b"guala-embodiment-physical-foveal-scan-v1\0"
FOVEAL_OBSERVATION_SCHEMA = (
    "guala.embodiment.physical_foveal_observation.v1"
)
FOVEAL_OBSERVATION_DOMAIN = (
    b"guala-embodiment-physical-foveal-observation-v1\0"
)
FOVEAL_SENSOR_ID = "W1-physical-fovea"
FOVEAL_PHYSICAL_QUANTITY = "surface-spectral-reflectance"
FOVEAL_JOINT_RELEVANCE_PROFILE = (
    b"guala.embodiment.foveal.unit-joint-relevance.v1"
)
PALETTE_INDEXED_SURFACE_SAMPLER_PROFILE = (
    "guala.embodiment.palette_indexed_optical_surface_sampler.v1"
)
MAX_FOVEAL_FIXATIONS_PER_SCAN = (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT // OPTICAL_BANDS
)


def _fraction_record(value: Fraction, name: str) -> dict[str, int]:
    if not isinstance(value, Fraction):
        raise ValueError(f"{name} must be an exact Fraction")
    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
    }


@dataclass(frozen=True, slots=True)
class SurfaceFixation:
    """One exact row/column fixation on a physical optical surface."""

    row: int
    column: int

    def verify(self, *, rows: int, columns: int) -> None:
        if (
            isinstance(self.row, bool)
            or not isinstance(self.row, int)
            or isinstance(self.column, bool)
            or not isinstance(self.column, int)
            or not 0 <= self.row < rows
            or not 0 <= self.column < columns
        ):
            raise ValueError("foveal fixation is outside the physical surface")

    def as_record(self) -> dict[str, int]:
        return {"column": self.column, "row": self.row}


@runtime_checkable
class PhysicalOpticalSurfaceSampler(Protocol):
    """Physical coordinate-to-six-band boundary for optical surfaces."""

    profile_id: str

    def reflectance_at_ppm(
        self,
        surface: ObjectOpticalSurface,
        fixation: SurfaceFixation,
    ) -> tuple[int, ...]:
        """Return one physical six-band reflectance at one coordinate."""


class PaletteIndexedObjectOpticalSurfaceSampler:
    """Exact sampler for a palette-indexed six-band physical surface."""

    profile_id = PALETTE_INDEXED_SURFACE_SAMPLER_PROFILE

    def reflectance_at_ppm(
        self,
        surface: ObjectOpticalSurface,
        fixation: SurfaceFixation,
    ) -> tuple[int, ...]:
        fixation.verify(rows=surface.rows, columns=surface.columns)
        return surface.reflectance_at_verified_ppm(
            row=fixation.row,
            column=fixation.column,
        )


def complete_surface_fixation_sequence(
    surface: ObjectOpticalSurface,
) -> tuple[SurfaceFixation, ...]:
    """Return every physical cell once in exact row-major order."""

    if not isinstance(surface, ObjectOpticalSurface):
        raise ValueError("complete foveal scan requires an optical surface")
    surface.verify()
    return tuple(
        SurfaceFixation(row=row, column=column)
        for row in range(surface.rows)
        for column in range(surface.columns)
    )


def successive_surface_patch_fixation_sequences(
    surface: ObjectOpticalSurface,
    *,
    patch_rows: int,
    patch_columns: int,
) -> tuple[tuple[SurfaceFixation, ...], ...]:
    """Tile a raster into ordered physical gaze patches without loss."""

    if not isinstance(surface, ObjectOpticalSurface):
        raise ValueError("successive gaze patches require an optical surface")
    surface.verify()
    for value, name, maximum in (
        (patch_rows, "gaze patch rows", surface.rows),
        (patch_columns, "gaze patch columns", surface.columns),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise ValueError(f"{name} is outside the physical surface")
    if (
        patch_rows * patch_columns < 2
        or patch_rows * patch_columns
        > MAX_FOVEAL_FIXATIONS_PER_SCAN
    ):
        raise ValueError(
            "gaze patch geometry exceeds the native sample boundary"
        )

    patches: list[tuple[SurfaceFixation, ...]] = []
    for row_start in range(0, surface.rows, patch_rows):
        row_stop = min(surface.rows, row_start + patch_rows)
        for column_start in range(0, surface.columns, patch_columns):
            column_stop = min(
                surface.columns,
                column_start + patch_columns,
            )
            patch = tuple(
                SurfaceFixation(row=row, column=column)
                for row in range(row_start, row_stop)
                for column in range(column_start, column_stop)
            )
            if len(patch) == 1:
                if not patches:
                    raise ValueError(
                        "gaze patch cannot carry one structural sample"
                    )
                merged = patches[-1] + patch
                if len(merged) > MAX_FOVEAL_FIXATIONS_PER_SCAN:
                    raise ValueError(
                        "gaze patch merge exceeds the native sample boundary"
                    )
                patches[-1] = merged
            else:
                patches.append(patch)
    flattened = tuple(
        fixation for patch in patches for fixation in patch
    )
    if (
        len(flattened) != surface.rows * surface.columns
        or len(set(flattened)) != len(flattened)
        or set(flattened) != set(
            complete_surface_fixation_sequence(surface)
        )
        or any(
            not 2 <= len(patch) <= MAX_FOVEAL_FIXATIONS_PER_SCAN
            for patch in patches
        )
    ):
        raise RuntimeError("successive gaze patches lost raster custody")
    return tuple(patches)


@dataclass(frozen=True, slots=True)
class PhysicalFovealScanPlan:
    """Signed physical focus target and immutable fixation sequence."""

    world_revision: int
    target_position: PositionMM
    target_radius_mm: int
    surface_columns: int
    surface_rows: int
    surface_sha256: str
    sampler_profile_id: str
    fixations: tuple[SurfaceFixation, ...]
    source_time_start: Fraction
    source_time_end: Fraction
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "fixations": [
                fixation.as_record() for fixation in self.fixations
            ],
            "schema": FOVEAL_SCAN_SCHEMA,
            "sampler_profile_id": self.sampler_profile_id,
            "source_time_end": _fraction_record(
                self.source_time_end, "foveal source time end"
            ),
            "source_time_start": _fraction_record(
                self.source_time_start, "foveal source time start"
            ),
            "surface_columns": self.surface_columns,
            "surface_rows": self.surface_rows,
            "surface_sha256": self.surface_sha256,
            "target_position": self.target_position.as_record(),
            "target_radius_mm": self.target_radius_mm,
            "world_revision": self.world_revision,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _native_records_from_substreams(
    physical_substreams: tuple[NativeSensorySubstreamInput, ...],
) -> tuple[dict[str, object], ...]:
    records = []
    for value in physical_substreams:
        anchor = value.source_times[0]
        records.append({
            "schema": "guala.native_sensory_input.v3",
            "sense": value.sense.value,
            "sensor_id": value.sensor_id,
            "substream_id": value.substream_id,
            "topology_index": value.topology_index,
            "coordinates": [
                [coordinate.axis_id, coordinate.coordinate_id]
                for coordinate in value.coordinates
            ],
            "physical_quantity": value.physical_quantity,
            "physical_unit": value.physical_unit,
            "source_anchor_fraction": [
                anchor.numerator,
                anchor.denominator,
            ],
            "causal_offsets_fraction": [
                [
                    (timestamp - anchor).numerator,
                    (timestamp - anchor).denominator,
                ]
                for timestamp in value.source_times
            ],
            "normalized_signal": list(value.normalized_signal),
            "phase_turns_fraction": [
                [phase.numerator, phase.denominator]
                for phase in value.phase_turns
            ],
        })
    return tuple(records)


@dataclass(frozen=True, slots=True)
class PhysicalFovealObservation:
    """One authenticated physical scan awaiting one canonical L0--L4 pass."""

    scan_plan: PhysicalFovealScanPlan
    physical_substreams: tuple[NativeSensorySubstreamInput, ...]
    physical_records: tuple[dict[str, object], ...]
    source_sample_commitments: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _window_binding: "_SingleWindowBinding" = field(
        default_factory=lambda: _SingleWindowBinding(),
        compare=False,
        repr=False,
    )

    def native_records(self) -> tuple[dict[str, object], ...]:
        """Return the one retained public record of the typed trajectories."""

        return self.physical_records

    def joint_source_occurrences(
        self,
    ) -> tuple[NativeJointSourceOccurrenceInput, ...]:
        """Declare each six-band trajectory segment as one optical event."""

        segment_count, remainder = divmod(
            len(self.physical_substreams), OPTICAL_BANDS
        )
        if segment_count == 0 or remainder:
            raise ValueError("foveal receptor topology is incomplete")
        occurrences = []
        for segment in range(segment_count):
            port_indices = tuple(
                band * segment_count + segment
                for band in range(OPTICAL_BANDS)
            )
            source_times = self.physical_substreams[
                port_indices[0]
            ].source_times
            if any(
                self.physical_substreams[index].source_times
                != source_times
                for index in port_indices
            ):
                raise ValueError(
                    "foveal spectral band clocks changed within a segment"
                )
            occurrences.append(
                NativeJointSourceOccurrenceInput(
                    port_indices=port_indices,
                    source_times=source_times,
                    joint_intersample_profile_payload=(
                        UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
                    ),
                    groups=(tuple(range(OPTICAL_BANDS)),),
                    joint_relevance_profile_payload=(
                        FOVEAL_JOINT_RELEVANCE_PROFILE
                    ),
                    joint_relevance=(Fraction(1),) * len(source_times),
                )
            )
        return tuple(occurrences)

    def unsigned_record(self) -> dict[str, object]:
        return {
            "physical_substreams": list(self.native_records()),
            "scan_plan_receipt_sha256": (
                self.scan_plan.authority_receipt_sha256
            ),
            "schema": FOVEAL_OBSERVATION_SCHEMA,
        }

    def _bind_to_window_entries(
        self,
        *,
        window_id: str,
        context_id: str,
        entry_indices: tuple[int, ...],
        entry_records: tuple[dict[str, object], ...],
    ) -> "BoundPhysicalFovealObservation":
        """Bind typed receptor trajectories to their admitted evidence.

        The serialized field remains externally inspectable evidence.  The
        active settlement receives the original typed trajectories, so it
        never reconstructs exact times or phases from its own JSON record.
        """

        if len(entry_indices) != 1 or len(entry_records) != 1:
            raise RuntimeError(
                "physical foveal binding must cover one complete field entry"
            )
        try:
            admitted = entry_records[0]["full_field"]
        except (KeyError, TypeError) as error:
            raise RuntimeError(
                "physical foveal binding lost its admitted field"
            ) from error
        if admitted != list(self.native_records()):
            raise RuntimeError(
                "physical foveal binding changed admitted evidence"
            )
        self._window_binding.bind_once()
        return BoundPhysicalFovealObservation(
            window_id=window_id,
            context_id=context_id,
            entry_index=entry_indices[0],
            native_inputs=self.physical_substreams,
        )


class _SingleWindowBinding:
    """One-use request-local binding; it is never persisted."""

    __slots__ = ("_bound", "_lock")

    def __init__(self) -> None:
        self._bound = False
        self._lock = threading.Lock()

    def bind_once(self) -> None:
        with self._lock:
            if self._bound:
                raise RuntimeError(
                    "physical foveal observation was already bound"
                )
            self._bound = True


@dataclass(frozen=True, slots=True)
class BoundPhysicalFovealObservation:
    """Typed foveal input available only to its active causal settlement."""

    window_id: str
    context_id: str
    entry_index: int
    native_inputs: tuple[NativeSensorySubstreamInput, ...]

    @property
    def entry_indices(self) -> tuple[int, ...]:
        return (self.entry_index,)

    def inputs_for_settlement(
        self,
        *,
        window_id: str,
        context_id: str,
    ) -> tuple[tuple[int, NativeSensorySubstreamInput], ...]:
        if (
            window_id != self.window_id
            or context_id != self.context_id
            or not self.native_inputs
        ):
            raise RuntimeError(
                "physical foveal input left its bound causal window"
            )
        return tuple(
            (self.entry_index, native)
            for native in self.native_inputs
        )


def _surface_sha256(surface: ObjectOpticalSurface) -> str:
    surface.verify()
    return _digest(surface.as_record())


def _verify_surface_sha256(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("focused optical surface identity is invalid")
    return value


def _focused_object(
    observation: ObservationSnapshot,
    object_id: str,
) -> EmbodiedObject:
    matches = tuple(
        item for item in observation.objects
        if item.object_id == object_id
    )
    if len(matches) != 1:
        raise ValueError("physical focus target is absent or ambiguous")
    target = matches[0]
    if target.position is None or target.optical_surface is None:
        raise ValueError(
            "physical focus requires one placed optical surface"
        )
    return target


def _physically_located_object(
    observation: ObservationSnapshot,
    plan: PhysicalFovealScanPlan,
) -> EmbodiedObject:
    matches = tuple(
        item for item in observation.objects
        if (
            item.position == plan.target_position
            and item.radius_mm == plan.target_radius_mm
            and item.optical_surface is not None
            and item.optical_surface.columns == plan.surface_columns
            and item.optical_surface.rows == plan.surface_rows
            and _surface_sha256(item.optical_surface)
            == plan.surface_sha256
        )
    )
    if len(matches) != 1:
        raise ValueError(
            "authenticated physical focus target is absent or ambiguous"
        )
    return matches[0]


def _verify_fixations(
    fixations: tuple[SurfaceFixation, ...],
    *,
    rows: int,
    columns: int,
) -> None:
    if (
        not isinstance(fixations, tuple)
        or len(fixations) < 2
        or len(fixations) > min(
            rows * columns,
            MAX_FOVEAL_FIXATIONS_PER_SCAN,
        )
        or any(not isinstance(value, SurfaceFixation) for value in fixations)
    ):
        raise ValueError(
            "foveal fixation sequence exceeds its physical surface boundary"
        )
    for fixation in fixations:
        fixation.verify(rows=rows, columns=columns)


def _verified_reflectance(
    sampler: PhysicalOpticalSurfaceSampler,
    surface: ObjectOpticalSurface,
    fixation: SurfaceFixation,
) -> tuple[int, ...]:
    values = sampler.reflectance_at_ppm(surface, fixation)
    if (
        not isinstance(values, tuple)
        or len(values) != OPTICAL_BANDS
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 1_000_000
            for value in values
        )
    ):
        raise ValueError(
            "optical surface sampler left the physical six-band boundary"
        )
    return values


def _foveal_substreams(
    surface: ObjectOpticalSurface,
    plan: PhysicalFovealScanPlan,
    sampler: PhysicalOpticalSurfaceSampler,
) -> tuple[NativeSensorySubstreamInput, ...]:
    surface.verify()
    sample_count = len(plan.fixations)
    segment_count = (
        sample_count + MAX_NATIVE_SAMPLES_PER_SUBSTREAM - 1
    ) // MAX_NATIVE_SAMPLES_PER_SUBSTREAM
    receptor_count = OPTICAL_BANDS * segment_count
    if (
        receptor_count > MAX_NATIVE_SIGHT_SUBSTREAMS
        or sample_count > MAX_FOVEAL_FIXATIONS_PER_SCAN
    ):
        raise ValueError(
            "foveal surface geometry exceeds the native sensory boundary"
        )

    patches = tuple(
        _verified_reflectance(sampler, surface, fixation)
        for fixation in plan.fixations
    )
    interval = plan.source_time_end - plan.source_time_start
    result: list[NativeSensorySubstreamInput] = []
    for band in range(OPTICAL_BANDS):
        for segment in range(segment_count):
            start = segment * MAX_NATIVE_SAMPLES_PER_SUBSTREAM
            stop = min(
                sample_count,
                start + MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
            )
            result.append(
                NativeSensorySubstreamInput(
                    sense=PhysicalSense.SIGHT,
                    sensor_id=FOVEAL_SENSOR_ID,
                    substream_id=(
                        f"foveal-band-{band}-segment-{segment}"
                    ),
                    topology_index=len(result),
                    coordinates=(
                        NativeAxisCoordinate(
                            "optical-band", f"band-{band}"
                        ),
                        NativeAxisCoordinate(
                            "trajectory-segment", f"segment-{segment}"
                        ),
                    ),
                    physical_quantity=FOVEAL_PHYSICAL_QUANTITY,
                    physical_unit="fraction-of-incident-radiance",
                    source_times=tuple(
                        plan.source_time_start
                        + interval
                        * Fraction(index + 1, sample_count + 1)
                        for index in range(start, stop)
                    ),
                    normalized_signal=tuple(
                        float(Fraction(patches[index][band], 1_000_000))
                        for index in range(start, stop)
                    ),
                    phase_turns=tuple(
                        Fraction(index, sample_count)
                        for index in range(start, stop)
                    ),
                )
            )
    return tuple(result)


class PhysicalFovealObservationAuthority:
    """Stateless authenticated physical focus and foveal transducer."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        surface_sampler: PhysicalOpticalSurfaceSampler | None = None,
    ) -> None:
        self._key = _authority_key(authority_key)
        sampler = (
            PaletteIndexedObjectOpticalSurfaceSampler()
            if surface_sampler is None
            else surface_sampler
        )
        if (
            not isinstance(sampler, PhysicalOpticalSurfaceSampler)
            or not isinstance(sampler.profile_id, str)
            or not sampler.profile_id
        ):
            raise ValueError(
                "foveal observation requires a typed physical surface sampler"
            )
        require_identifier(
            sampler.profile_id, "foveal physical sampler profile"
        )
        self._surface_sampler = sampler

    def authorize_scan(
        self,
        observation: ObservationSnapshot,
        *,
        target_object_id: str,
        fixations: tuple[SurfaceFixation, ...],
        source_time_start: Fraction = Fraction(0),
        source_time_end: Fraction = Fraction(1),
    ) -> PhysicalFovealScanPlan:
        _verify_observation(self._key, observation)
        target = _focused_object(observation, target_object_id)
        surface = target.optical_surface
        assert surface is not None
        _verify_fixations(
            fixations,
            rows=surface.rows,
            columns=surface.columns,
        )
        _fraction_record(source_time_start, "foveal source time start")
        _fraction_record(source_time_end, "foveal source time end")
        if source_time_end <= source_time_start:
            raise ValueError("foveal source interval must be positive")
        unsigned = {
            "fixations": [
                fixation.as_record() for fixation in fixations
            ],
            "schema": FOVEAL_SCAN_SCHEMA,
            "sampler_profile_id": self._surface_sampler.profile_id,
            "source_time_end": _fraction_record(
                source_time_end, "foveal source time end"
            ),
            "source_time_start": _fraction_record(
                source_time_start, "foveal source time start"
            ),
            "surface_columns": surface.columns,
            "surface_rows": surface.rows,
            "surface_sha256": _surface_sha256(surface),
            "target_position": target.position.as_record(),
            "target_radius_mm": target.radius_mm,
            "world_revision": observation.revision,
        }
        signature = _sign(self._key, FOVEAL_SCAN_DOMAIN, unsigned)
        return PhysicalFovealScanPlan(
            world_revision=observation.revision,
            target_position=target.position,
            target_radius_mm=target.radius_mm,
            surface_columns=surface.columns,
            surface_rows=surface.rows,
            surface_sha256=unsigned["surface_sha256"],
            sampler_profile_id=self._surface_sampler.profile_id,
            fixations=fixations,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {
                    "authority_hmac_sha256": signature,
                    "payload": unsigned,
                }
            ),
        )

    def verify_scan_plan(
        self,
        plan: PhysicalFovealScanPlan,
    ) -> None:
        if not isinstance(plan, PhysicalFovealScanPlan):
            raise ValueError("foveal scan plan is not typed")
        if (
            isinstance(plan.world_revision, bool)
            or not isinstance(plan.world_revision, int)
            or not 0 <= plan.world_revision <= MAX_WORLD_REVISION
        ):
            raise ValueError("foveal world revision is invalid")
        plan.target_position.verify()
        if (
            isinstance(plan.target_radius_mm, bool)
            or not isinstance(plan.target_radius_mm, int)
            or not 1 <= plan.target_radius_mm <= 1_000_000
            or not 1 <= plan.surface_columns <= (
                MAX_OPTICAL_SURFACE_COLUMNS
            )
            or not 1 <= plan.surface_rows <= MAX_OPTICAL_SURFACE_ROWS
        ):
            raise ValueError("foveal physical target geometry is invalid")
        _verify_surface_sha256(plan.surface_sha256)
        if plan.sampler_profile_id != self._surface_sampler.profile_id:
            raise ValueError("foveal physical sampler profile changed")
        _verify_fixations(
            plan.fixations,
            rows=plan.surface_rows,
            columns=plan.surface_columns,
        )
        _fraction_record(plan.source_time_start, "foveal source time start")
        _fraction_record(plan.source_time_end, "foveal source time end")
        if plan.source_time_end <= plan.source_time_start:
            raise ValueError("foveal source interval must be positive")
        unsigned = plan.unsigned_record()
        expected_hmac = _sign(
            self._key, FOVEAL_SCAN_DOMAIN, unsigned
        )
        if not hmac.compare_digest(
            expected_hmac, plan.authority_hmac_sha256
        ):
            raise ValueError("foveal scan plan HMAC changed")
        expected_receipt = _digest(
            {
                "authority_hmac_sha256": expected_hmac,
                "payload": unsigned,
            }
        )
        if expected_receipt != plan.authority_receipt_sha256:
            raise ValueError("foveal scan plan receipt identity changed")

    def observe(
        self,
        observation: ObservationSnapshot,
        *,
        scan_plan: PhysicalFovealScanPlan,
    ) -> PhysicalFovealObservation:
        _verify_observation(self._key, observation)
        self.verify_scan_plan(scan_plan)
        if scan_plan.world_revision != observation.revision:
            raise ValueError("foveal scan plan is stale")
        target = _physically_located_object(observation, scan_plan)
        surface = target.optical_surface
        assert surface is not None
        substreams = _foveal_substreams(
            surface,
            scan_plan,
            self._surface_sampler,
        )
        physical_records = _native_records_from_substreams(substreams)
        source_sample_commitments = tuple(
            source_evidence_sample_commitment_sha256(tuple(
                (
                    index,
                    native.source_times[index],
                    Fraction.from_float(
                        float(native.normalized_signal[index])
                    ),
                    (
                        native.source_relevance[index]
                        if native.source_relevance is not None
                        else Fraction(1)
                    ),
                    native.phase_turns[index],
                )
                for index in range(len(native.normalized_signal))
            ))
            for native in substreams
        )
        provisional = PhysicalFovealObservation(
            scan_plan=scan_plan,
            physical_substreams=substreams,
            physical_records=physical_records,
            source_sample_commitments=source_sample_commitments,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        unsigned = provisional.unsigned_record()
        signature = _sign(
            self._key,
            FOVEAL_OBSERVATION_DOMAIN,
            unsigned,
        )
        return PhysicalFovealObservation(
            scan_plan=scan_plan,
            physical_substreams=substreams,
            physical_records=physical_records,
            source_sample_commitments=source_sample_commitments,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": unsigned,
            }),
        )

    def verify_observation(
        self,
        observation: PhysicalFovealObservation,
    ) -> None:
        if not isinstance(observation, PhysicalFovealObservation):
            raise TypeError("physical foveal observation is not typed")
        self.verify_scan_plan(observation.scan_plan)
        if (
            not isinstance(observation.physical_substreams, tuple)
            or not observation.physical_substreams
            or len(observation.physical_substreams)
            > MAX_NATIVE_SIGHT_SUBSTREAMS
            or tuple(
                value.topology_index
                for value in observation.physical_substreams
            )
            != tuple(range(len(observation.physical_substreams)))
            or any(
                not isinstance(value, NativeSensorySubstreamInput)
                or value.sense is not PhysicalSense.SIGHT
                or value.sensor_id != FOVEAL_SENSOR_ID
                for value in observation.physical_substreams
            )
            or not isinstance(observation.physical_records, tuple)
            or len(observation.physical_records)
            != len(observation.physical_substreams)
            or len(observation.source_sample_commitments)
            != len(observation.physical_substreams)
        ):
            raise ValueError("physical foveal observation extent changed")
        unsigned = observation.unsigned_record()
        expected_hmac = _sign(
            self._key,
            FOVEAL_OBSERVATION_DOMAIN,
            unsigned,
        )
        if not hmac.compare_digest(
            expected_hmac,
            observation.authority_hmac_sha256,
        ):
            raise ValueError("physical foveal observation HMAC changed")
        if observation.authority_receipt_sha256 != _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": unsigned,
        }):
            raise ValueError(
                "physical foveal observation receipt identity changed"
            )

    def verify_settlement(
        self,
        observation: PhysicalFovealObservation,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Prove the exact foveal sources entered one settled sight event."""

        if not isinstance(observation, PhysicalFovealObservation):
            raise TypeError("physical foveal observation is not typed")
        self.verify_observation(observation)
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("physical foveal settlement is not typed")
        settlement.verify()
        interpretation = next(
            (
                value
                for value in settlement.interpretations
                if value.sense == PhysicalSense.SIGHT.value
            ),
            None,
        )
        if (
            interpretation is None
            or interpretation.state != "observed"
            or len(interpretation.substreams)
            != len(observation.physical_substreams)
        ):
            raise ValueError(
                "physical foveal sources are absent from settlement"
            )
        by_topology = {
            value.topology_index: value
            for value in interpretation.substreams
        }
        for native, source_commitment in zip(
            observation.physical_substreams,
            observation.source_sample_commitments,
            strict=True,
        ):
            component = by_topology.get(native.topology_index)
            if (
                component is None
                or component.sensor_id != native.sensor_id
                or component.substream_id != native.substream_id
                or component.physical_quantity != native.physical_quantity
                or component.physical_unit != native.physical_unit
                or component.source_sample_count
                != len(native.normalized_signal)
                or component.source_sample_commitment_sha256
                != source_commitment
            ):
                raise ValueError(
                    "physical foveal source differs from settlement"
                )


__all__ = (
    "BoundPhysicalFovealObservation",
    "FOVEAL_PHYSICAL_QUANTITY",
    "FOVEAL_SCAN_SCHEMA",
    "FOVEAL_SENSOR_ID",
    "MAX_FOVEAL_FIXATIONS_PER_SCAN",
    "PALETTE_INDEXED_SURFACE_SAMPLER_PROFILE",
    "PaletteIndexedObjectOpticalSurfaceSampler",
    "PhysicalFovealObservation",
    "PhysicalFovealObservationAuthority",
    "PhysicalFovealScanPlan",
    "PhysicalOpticalSurfaceSampler",
    "SurfaceFixation",
    "complete_surface_fixation_sequence",
    "successive_surface_patch_fixation_sequences",
)
