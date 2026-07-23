"""Deterministic retinotopic sight and receipt-bound visual L5 continuity.

The camera adapter declares a complete 8 by 8 receptor topology over the
canonical 64 by 64 grayscale sensor plane.  Every receptor contributes its
reset-to-exposure mean-light trajectory to the frozen L0--L4 boundary.  The
reset phase is the physical camera-pixel reference that prevents distinct
static light levels from collapsing into one zero-motion tuple.  No
random fixation, label, chi address, Atlas entry, hash bucket, or learned
model participates.

Visual L5 runs only after the owning causal window has produced one verified
``SixSenseFullFieldBoundary``.  It reads every exact D/M/R/U/C/P/B tuple,
forms maximal four-connected regions only where complete structural histories
are exactly equal. Recurrence and retinotopic overlap across separate camera
windows remain candidates, never object identity: every new window receives
fresh anonymous lineage unless a future transport supplies an authenticated
shared exposure. Unknown and ambiguous continuity remain explicit.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import io
import base64
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping

import numpy as np

from dsf_ai_service.glew_runtime.model import ReceiptRegistry
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SenseBoundaryState,
    SixSenseFullFieldBoundary,
)


VISUAL_FRAME_HEIGHT = 64
VISUAL_FRAME_WIDTH = 64
MAX_VISUAL_SOURCE_HEIGHT = 128
MAX_VISUAL_SOURCE_WIDTH = 128
RETINA_ROWS = 8
RETINA_COLUMNS = 8
RETINA_RECEPTOR_COUNT = RETINA_ROWS * RETINA_COLUMNS
RECEPTOR_HEIGHT = VISUAL_FRAME_HEIGHT // RETINA_ROWS
RECEPTOR_WIDTH = VISUAL_FRAME_WIDTH // RETINA_COLUMNS
MIN_VISUAL_FRAMES = 4
MAX_VISUAL_FRAMES = 8
DEFAULT_VISUAL_L5_HISTORY = 1
MAX_VISUAL_L5_HISTORY = 8
MAX_VISUAL_STATE_BYTES = 2 * 1024 * 1024
MAX_VISUAL_IMAGE_BYTES = 256 * 1024
MAX_VISUAL_SEQUENCE_BYTES = 2 * 1024 * 1024
VISUAL_SOURCE_CLOCK_QUANTUM_NS = 1_000_000
_STATE_SCHEMA = "guala.visual_region_continuity.state.v3"
_SETTLEMENT_SCHEMA = "guala.visual_region_continuity.settlement.v3"


def _region_field_record(value: tuple) -> list[dict[str, object]]:
    if not isinstance(value, tuple) or not value:
        raise ValueError("visual explicit region field changed")
    record = []
    for receptor in value:
        if not isinstance(receptor, tuple) or len(receptor) != 3:
            raise ValueError("visual explicit receptor field changed")
        row, column, field_history = receptor
        if (
            isinstance(row, bool)
            or not isinstance(row, int)
            or isinstance(column, bool)
            or not isinstance(column, int)
            or not isinstance(field_history, tuple)
            or not field_history
        ):
            raise ValueError("visual explicit receptor field changed")
        encoded_history = []
        for field_tuple in field_history:
            if not isinstance(field_tuple, tuple) or len(field_tuple) != 7:
                raise ValueError("visual complete DSF tuple changed")
            if any(not isinstance(field, Fraction) for field in field_tuple):
                raise ValueError("visual exact DSF fraction changed")
            encoded_history.append([
                [field.numerator, field.denominator]
                for field in field_tuple
            ])
        record.append({
            "exact_D_M_R_U_C_P_B": encoded_history,
            "relative_retinotopic_coordinate": [row, column],
        })
    return record


def _region_field_from_record(value: object) -> tuple:
    if not isinstance(value, list) or not value:
        raise ValueError("visual explicit region field changed")
    result = []
    for expected_index, receptor in enumerate(value):
        if not isinstance(receptor, dict) or set(receptor) != {
            "exact_D_M_R_U_C_P_B",
            "relative_retinotopic_coordinate",
        }:
            raise ValueError("visual explicit receptor field changed")
        coordinate = receptor["relative_retinotopic_coordinate"]
        if (
            not isinstance(coordinate, list)
            or len(coordinate) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, int)
                for item in coordinate
            )
            or any(item < -7 or item > 7 for item in coordinate)
            or (expected_index == 0 and coordinate != [0, 0])
        ):
            raise ValueError("visual relative receptor coordinate changed")
        histories = receptor["exact_D_M_R_U_C_P_B"]
        if not isinstance(histories, list) or not histories:
            raise ValueError("visual receptor field history is empty")
        parsed_history = []
        for field_tuple in histories:
            if not isinstance(field_tuple, list) or len(field_tuple) != 7:
                raise ValueError("visual complete DSF tuple changed")
            parsed_tuple = []
            for pair in field_tuple:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or any(
                        isinstance(item, bool) or not isinstance(item, int)
                        for item in pair
                    )
                    or pair[1] == 0
                ):
                    raise ValueError("visual exact DSF fraction changed")
                fraction = Fraction(pair[0], pair[1])
                if [fraction.numerator, fraction.denominator] != pair:
                    raise ValueError("visual exact DSF fraction is not canonical")
                parsed_tuple.append(fraction)
            parsed_history.append(tuple(parsed_tuple))
        result.append((coordinate[0], coordinate[1], tuple(parsed_history)))
    return tuple(result)


def _region_structure_receipt(value: tuple) -> str:
    return _digest_payload(
        b"guala-visual-l5-region-structure-v2",
        {
            "explicit_receptor_fields": _region_field_record(value),
            "schema": "guala.visual_l5.explicit_region_structure.v2",
        },
    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest_payload(domain: bytes, payload: object) -> str:
    return hashlib.sha256(domain + b"\0" + _canonical_bytes(payload)).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a lowercase sha256 digest")
    return value


def _hmac_hex(key: bytes, domain: bytes, payload: object) -> str:
    return hmac.new(
        key,
        domain + b"\0" + _canonical_bytes(payload),
        hashlib.sha256,
    ).hexdigest()


def decode_visual_image_bytes(encoded: bytes) -> np.ndarray:
    """Canonical live-camera decoder shared by HTTP and remote ownership."""
    if not isinstance(encoded, bytes) or not encoded:
        raise ValueError("visual image bytes must be nonempty")
    from PIL import Image

    image = Image.open(io.BytesIO(encoded))
    if (
        image.width <= 0
        or image.height <= 0
        or image.width > MAX_VISUAL_SOURCE_WIDTH
        or image.height > MAX_VISUAL_SOURCE_HEIGHT
    ):
        raise ValueError(
            "visual source dimensions exceed the 128 by 128 capture boundary"
        )
    image = image.convert("L").resize((VISUAL_FRAME_WIDTH, VISUAL_FRAME_HEIGHT))
    return np.asarray(image, dtype=np.uint8)


def canonical_visual_frames_from_claims(
    claims: Iterable[Mapping[str, object]],
    *,
    source_time_start_ns: int,
    source_time_end_ns: int,
) -> tuple["CanonicalVisualFrame", ...]:
    """Validate one transport-neutral all-or-nothing visual sequence."""
    if isinstance(claims, (list, tuple)) and not (
        MIN_VISUAL_FRAMES <= len(claims) <= MAX_VISUAL_FRAMES
    ):
        raise ValueError("visual sequence must contain four through eight frames")
    ordered = tuple(claims)
    if not MIN_VISUAL_FRAMES <= len(ordered) <= MAX_VISUAL_FRAMES:
        raise ValueError("visual sequence must contain four through eight frames")
    if (
        isinstance(source_time_start_ns, bool)
        or not isinstance(source_time_start_ns, int)
        or isinstance(source_time_end_ns, bool)
        or not isinstance(source_time_end_ns, int)
        or source_time_end_ns <= source_time_start_ns
    ):
        raise ValueError("visual sequence interval is invalid")
    frames = []
    prior_time = None
    aggregate_bytes = 0
    for index, claim in enumerate(ordered):
        if not isinstance(claim, Mapping) or set(claim) != {
            "captured_ms",
            "frame_b64",
        }:
            raise ValueError(f"visual frame {index} changed shape")
        captured_ms = claim["captured_ms"]
        encoded_text = claim["frame_b64"]
        if (
            isinstance(captured_ms, bool)
            or not isinstance(captured_ms, int)
            or not isinstance(encoded_text, str)
            or not encoded_text
            or len(encoded_text) > 4 * ((MAX_VISUAL_IMAGE_BYTES + 2) // 3)
        ):
            raise ValueError(f"visual frame {index} changed shape")
        source_time_ns = captured_ms * 1_000_000
        if (
            source_time_ns < source_time_start_ns
            or source_time_ns >= source_time_end_ns
            or (prior_time is not None and source_time_ns <= prior_time)
        ):
            raise ValueError(
                f"visual frame {index} lies outside canonical source order"
            )
        try:
            encoded = base64.b64decode(encoded_text, validate=True)
        except Exception as error:
            raise ValueError(f"visual frame {index} is not valid base64") from error
        if not encoded or len(encoded) > MAX_VISUAL_IMAGE_BYTES:
            raise ValueError(f"visual frame {index} exceeds its byte boundary")
        aggregate_bytes += len(encoded)
        if aggregate_bytes > MAX_VISUAL_SEQUENCE_BYTES:
            raise ValueError("visual sequence exceeds the bounded request size")
        frames.append(
            CanonicalVisualFrame.from_uint8(
                source_time_ns, decode_visual_image_bytes(encoded)
            )
        )
        prior_time = source_time_ns
    return tuple(frames)


@dataclass(frozen=True, slots=True)
class CanonicalVisualFrame:
    """One bounded camera observation with an exact source receipt time."""

    source_time_ns: int
    pixels: bytes
    frame_sha256: str

    @classmethod
    def from_uint8(
        cls, source_time_ns: int, pixels: object
    ) -> "CanonicalVisualFrame":
        if isinstance(source_time_ns, bool) or not isinstance(source_time_ns, int):
            raise TypeError("visual frame source time must be integer nanoseconds")
        if source_time_ns < 0:
            raise ValueError("visual frame source time cannot be negative")
        array = np.asarray(pixels)
        if array.shape != (VISUAL_FRAME_HEIGHT, VISUAL_FRAME_WIDTH):
            raise ValueError("visual frame must be exactly 64 by 64")
        if array.dtype != np.uint8:
            raise ValueError("visual frame must contain canonical uint8 samples")
        if not array.flags.c_contiguous:
            array = np.ascontiguousarray(array)
        encoded = array.tobytes(order="C")
        digest = hashlib.sha256(
            b"guala-canonical-visual-frame-v1\0"
            + source_time_ns.to_bytes(8, "big", signed=False)
            + encoded
        ).hexdigest()
        return cls(source_time_ns, encoded, digest)

    def as_array(self) -> np.ndarray:
        return np.frombuffer(self.pixels, dtype=np.uint8).reshape(
            VISUAL_FRAME_HEIGHT, VISUAL_FRAME_WIDTH
        )


@dataclass(frozen=True, slots=True)
class PreparedRetinotopicSight:
    """Pure transient preparation for one complete receptor field."""

    source_time_start: Fraction
    source_time_end: Fraction
    substreams: tuple[NativeSensorySubstreamInput, ...]
    frame_receipt_sha256s: tuple[str, ...]
    preparation_receipt_sha256: str

    def __post_init__(self) -> None:
        if len(self.substreams) != RETINA_RECEPTOR_COUNT:
            raise ValueError("retinotopic preparation lost receptor coverage")
        if tuple(item.topology_index for item in self.substreams) != tuple(
            range(RETINA_RECEPTOR_COUNT)
        ):
            raise ValueError("retinotopic preparation reordered receptors")
        if self.source_time_end <= self.source_time_start:
            raise ValueError("retinotopic preparation has no temporal extent")
        if not (
            MIN_VISUAL_FRAMES
            <= len(self.frame_receipt_sha256s)
            <= MAX_VISUAL_FRAMES
        ):
            raise ValueError("retinotopic preparation changed frame cardinality")
        for digest in (*self.frame_receipt_sha256s, self.preparation_receipt_sha256):
            _require_sha256(digest, "visual preparation receipt")

    def native_records(self) -> tuple[dict[str, object], ...]:
        """Return JSON-safe v2 records for the existing causal-window owner."""

        anchor = self.source_time_start
        records = []
        for value in self.substreams:
            offsets = tuple(timestamp - anchor for timestamp in value.source_times)
            records.append(
                {
                    "schema": "guala.native_sensory_input.v2",
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
                        [offset.numerator, offset.denominator] for offset in offsets
                    ],
                    "normalized_signal": list(value.normalized_signal),
                    "phase_turns": [
                        float(phase) for phase in value.phase_turns
                    ],
                    "visual_preparation_receipt_sha256": (
                        self.preparation_receipt_sha256
                    ),
                }
            )
        return tuple(records)


@dataclass(frozen=True, slots=True)
class VisualRegionObservation:
    region_index: int
    receptor_indices: tuple[int, ...]
    explicit_structural_field: tuple
    structural_receipt_sha256: str
    continuity: str
    continuity_basis: str
    lineage_receipt_sha256: str | None
    candidate_lineage_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if self.region_index < 0:
            raise ValueError("visual region index cannot be negative")
        if not self.receptor_indices or tuple(sorted(self.receptor_indices)) != (
            self.receptor_indices
        ):
            raise ValueError("visual region receptors must be ordered and nonempty")
        if any(
            value < 0 or value >= RETINA_RECEPTOR_COUNT
            for value in self.receptor_indices
        ):
            raise ValueError("visual region receptor lies outside the retina")
        parsed_field = _region_field_from_record(
            _region_field_record(self.explicit_structural_field)
        )
        if (
            parsed_field != self.explicit_structural_field
            or len(parsed_field) != len(self.receptor_indices)
        ):
            raise ValueError("visual explicit region field lost receptor coverage")
        origin_row, origin_column = divmod(
            self.receptor_indices[0], RETINA_COLUMNS
        )
        expected_coordinates = tuple(
            (
                receptor // RETINA_COLUMNS - origin_row,
                receptor % RETINA_COLUMNS - origin_column,
            )
            for receptor in self.receptor_indices
        )
        if tuple(
            (row, column)
            for row, column, _history in parsed_field
        ) != expected_coordinates:
            raise ValueError(
                "visual explicit region field lost retinotopic correspondence"
            )
        if self.continuity not in {"unknown", "unique", "ambiguous"}:
            raise ValueError("visual continuity state changed")
        if self.continuity_basis not in {
            "no_live_predecessor",
            "authenticated_exact_structural_recurrence_candidate",
            "authenticated_reciprocal_retinotopic_overlap_candidate",
            "authenticated_competing_candidates",
            "authenticated_no_candidate",
            "touching_exact_structural_recurrence_candidate",
            "touching_reciprocal_retinotopic_overlap_candidate",
            "touching_competing_candidates",
            "touching_no_candidate",
            "source_gap_structural_recurrence",
            "source_gap_no_recurrence",
        }:
            raise ValueError("visual continuity basis changed")
        _require_sha256(self.structural_receipt_sha256, "visual structure receipt")
        if self.structural_receipt_sha256 != _region_structure_receipt(
            self.explicit_structural_field
        ):
            raise ValueError("visual structure receipt differs from explicit field")
        _require_sha256(self.authority_receipt_sha256, "visual region receipt")
        if self.lineage_receipt_sha256 is not None:
            _require_sha256(self.lineage_receipt_sha256, "visual lineage receipt")
        for digest in self.candidate_lineage_receipt_sha256s:
            _require_sha256(digest, "visual candidate lineage receipt")
        if self.continuity == "unique" and self.lineage_receipt_sha256 is None:
            raise ValueError("unique visual continuity lost its anonymous lineage")
        if (
            self.continuity == "ambiguous"
            and not self.candidate_lineage_receipt_sha256s
        ):
            raise ValueError("ambiguous visual continuity lacks a candidate")


@dataclass(frozen=True, slots=True)
class VisualL5Settlement:
    assembly_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    window_relation: str
    full_field_receipt_sha256: str
    regions: tuple[VisualRegionObservation, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.assembly_id, str) or not self.assembly_id:
            raise ValueError("visual L5 settlement requires an assembly id")
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
        ):
            raise ValueError("visual L5 settlement source interval changed")
        if self.window_relation not in {
            "first",
            "authenticated_predecessor_evidence",
            "touching_window_bounds",
            "gap",
        }:
            raise ValueError("visual L5 window relation changed")
        _require_sha256(self.full_field_receipt_sha256, "visual full-field receipt")
        _require_sha256(self.authority_receipt_sha256, "visual L5 receipt")
        if not self.regions:
            raise ValueError("visual L5 settlement requires complete regions")
        if tuple(item.region_index for item in self.regions) != tuple(
            range(len(self.regions))
        ):
            raise ValueError("visual L5 regions are incomplete or reordered")
        coverage = tuple(
            sorted(
                receptor
                for region in self.regions
                for receptor in region.receptor_indices
            )
        )
        if coverage != tuple(range(RETINA_RECEPTOR_COUNT)):
            raise ValueError("visual L5 regions do not cover every receptor once")

    def as_record(self) -> dict[str, object]:
        return {
            "schema": _SETTLEMENT_SCHEMA,
            "assembly_id": self.assembly_id,
            "source_time_start": (
                f"{self.source_time_start.numerator}/"
                f"{self.source_time_start.denominator}"
            ),
            "source_time_end": (
                f"{self.source_time_end.numerator}/"
                f"{self.source_time_end.denominator}"
            ),
            "window_relation": self.window_relation,
            "full_field_receipt_sha256": self.full_field_receipt_sha256,
            "regions": [
                {
                    "region_index": value.region_index,
                    "receptor_indices": list(value.receptor_indices),
                    "explicit_structural_field": _region_field_record(
                        value.explicit_structural_field
                    ),
                    "structural_receipt_sha256": (
                        value.structural_receipt_sha256
                    ),
                    "continuity": value.continuity,
                    "continuity_basis": value.continuity_basis,
                    "lineage_receipt_sha256": value.lineage_receipt_sha256,
                    "candidate_lineage_receipt_sha256s": list(
                        value.candidate_lineage_receipt_sha256s
                    ),
                    "authority_receipt_sha256": value.authority_receipt_sha256,
                }
                for value in self.regions
            ],
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _region_components(signatures: tuple[object, ...]) -> tuple[tuple[int, ...], ...]:
    remaining = set(range(RETINA_RECEPTOR_COUNT))
    components = []
    while remaining:
        origin = min(remaining)
        remaining.remove(origin)
        signature = signatures[origin]
        stack = [origin]
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            row, column = divmod(current, RETINA_COLUMNS)
            neighbors = []
            if row:
                neighbors.append(current - RETINA_COLUMNS)
            if row + 1 < RETINA_ROWS:
                neighbors.append(current + RETINA_COLUMNS)
            if column:
                neighbors.append(current - 1)
            if column + 1 < RETINA_COLUMNS:
                neighbors.append(current + 1)
            for neighbor in sorted(neighbors, reverse=True):
                if neighbor in remaining and signatures[neighbor] == signature:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(sorted(components, key=lambda item: item[0]))


class DeterministicVisualRegionContinuityAuthority:
    """Bounded visual receptor preparation and full-field L5 continuity."""

    def __init__(
        self,
        *,
        authority_key: bytes,
        exposure_epoch_authority=None,
        history_capacity: int = DEFAULT_VISUAL_L5_HISTORY,
    ) -> None:
        if not isinstance(authority_key, bytes) or len(authority_key) < 32:
            raise ValueError("visual continuity requires a 256-bit authority key")
        if (
            isinstance(history_capacity, bool)
            or not isinstance(history_capacity, int)
            or not 1 <= history_capacity <= MAX_VISUAL_L5_HISTORY
        ):
            raise ValueError("visual continuity history capacity is invalid")
        self._key = authority_key
        if exposure_epoch_authority is not None:
            from dsf_ai_service.substrate.visual_exposure_epoch import (
                VisualExposureEpochAuthority,
            )
            if not isinstance(
                exposure_epoch_authority, VisualExposureEpochAuthority
            ):
                raise TypeError("visual continuity exposure authority changed")
        self._exposure_epoch_authority = exposure_epoch_authority
        self._history_capacity = history_capacity
        self._prior_regions: tuple[dict[str, object], ...] = ()
        self._prior_source_time_end: Fraction | None = None
        self._prior_exposure_epoch_receipt: str | None = None
        self._live = False
        self._history: tuple[dict[str, object], ...] = ()

    @staticmethod
    def prepare_retinotopic_inputs(
        frames: Iterable[CanonicalVisualFrame],
    ) -> PreparedRetinotopicSight:
        ordered = tuple(frames)
        if not MIN_VISUAL_FRAMES <= len(ordered) <= MAX_VISUAL_FRAMES:
            raise ValueError("visual sequence must contain four through eight frames")
        if not all(isinstance(value, CanonicalVisualFrame) for value in ordered):
            raise TypeError("visual sequence contains an uncanonical frame")
        times_ns = tuple(value.source_time_ns for value in ordered)
        if any(right <= left for left, right in zip(times_ns, times_ns[1:])):
            raise ValueError("visual frame source times must strictly increase")
        if times_ns[0] < VISUAL_SOURCE_CLOCK_QUANTUM_NS:
            raise ValueError(
                "visual frames do not leave one source-clock quantum for sensor reset"
            )
        receptor_times_ns = (
            times_ns[0] - VISUAL_SOURCE_CLOCK_QUANTUM_NS,
            *times_ns,
        )
        source_times = tuple(
            Fraction(value, 1_000_000_000) for value in receptor_times_ns
        )
        arrays = tuple(value.as_array() for value in ordered)
        ports = []
        trajectory_receipts = []
        for row in range(RETINA_ROWS):
            for column in range(RETINA_COLUMNS):
                topology_index = row * RETINA_COLUMNS + column
                row_start = row * RECEPTOR_HEIGHT
                column_start = column * RECEPTOR_WIDTH
                sums = tuple(
                    int(
                        frame[
                            row_start : row_start + RECEPTOR_HEIGHT,
                            column_start : column_start + RECEPTOR_WIDTH,
                        ].sum(dtype=np.uint64)
                    )
                    for frame in arrays
                )
                denominator = RECEPTOR_HEIGHT * RECEPTOR_WIDTH * 255
                exposed_signal = tuple(
                    Fraction(2 * value, denominator) - 1 for value in sums
                )
                exact_signal = (Fraction(-1), *exposed_signal)
                trajectory_receipts.append(
                    _digest_payload(
                        b"guala-retinotopic-light-trajectory-v1",
                        {
                            "column": column,
                            "row": row,
                            "signals": [
                                [value.numerator, value.denominator]
                                for value in exact_signal
                            ],
                            "source_times_ns": list(receptor_times_ns),
                        },
                    )
                )
                ports.append(
                    NativeSensorySubstreamInput(
                        sense=PhysicalSense.SIGHT,
                        sensor_id="browser-camera-retina-8x8",
                        substream_id=f"receptor-r{row}-c{column}",
                        topology_index=topology_index,
                        coordinates=(
                            NativeAxisCoordinate("retina-row", str(row)),
                            NativeAxisCoordinate("retina-column", str(column)),
                        ),
                        physical_quantity=(
                            "reset-referenced-area-mean-light-intensity"
                        ),
                        physical_unit="normalized-sensor-code",
                        source_times=source_times,
                        normalized_signal=tuple(float(value) for value in exact_signal),
                        phase_turns=(Fraction(0),) * len(exact_signal),
                    )
                )
        preparation = {
            "frame_receipt_sha256s": [value.frame_sha256 for value in ordered],
            "frame_capture_times_ns": list(times_ns),
            "receptor_trajectory_receipt_sha256s": trajectory_receipts,
            "schema": "guala.visual_retinotopic_preparation.v1",
            "source_time_end_ns": receptor_times_ns[-1],
            "source_time_start_ns": receptor_times_ns[0],
        }
        return PreparedRetinotopicSight(
            source_time_start=source_times[0],
            source_time_end=source_times[-1],
            substreams=tuple(ports),
            frame_receipt_sha256s=tuple(value.frame_sha256 for value in ordered),
            preparation_receipt_sha256=_digest_payload(
                b"guala-visual-retinotopic-preparation-v1", preparation
            ),
        )

    @staticmethod
    def _explicit_receptor_fields(sight_boundary) -> tuple[tuple, ...]:
        if len(sight_boundary.substreams) != RETINA_RECEPTOR_COUNT:
            raise ValueError("visual L5 requires every 8x8 retina receptor")
        fields = []
        for index, value in enumerate(sight_boundary.substreams):
            profile = value.profile
            if (
                profile.sensor_id != "browser-camera-retina-8x8"
                or profile.topology_index != index
                or profile.substream_id
                != f"receptor-r{index // RETINA_COLUMNS}-c{index % RETINA_COLUMNS}"
            ):
                raise ValueError("visual L5 received another sensor topology")
            coordinates = {
                coordinate.axis_id: coordinate.coordinate_id
                for coordinate in profile.coordinates
            }
            if coordinates != {
                "retina-row": str(index // RETINA_COLUMNS),
                "retina-column": str(index % RETINA_COLUMNS),
            }:
                raise ValueError("visual receptor coordinates changed")
            exact_tuples = value.kernel_basin.exact_dsf_field_tuples
            fields.append(
                tuple(exact.as_tuple() for exact in exact_tuples)
            )
        return tuple(fields)

    def _lineage_anchor(
        self, assembly_id: str, region_index: int, structure: str
    ) -> str:
        return _hmac_hex(
            self._key,
            b"guala-visual-anonymous-lineage-v1",
            {
                "assembly_id": assembly_id,
                "region_index": region_index,
                "structural_receipt_sha256": structure,
            },
        )

    def _region_receipt_payload(
        self,
        *,
        assembly_id: str,
        full_field_receipt_sha256: str,
        region_index: int,
        receptors: tuple[int, ...],
        explicit_structural_field: tuple,
        structure: str,
        continuity: str,
        continuity_basis: str,
        lineage: str | None,
        candidates: tuple[str, ...],
    ) -> dict[str, object]:
        return {
            "assembly_id": assembly_id,
            "candidate_lineage_receipt_sha256s": list(candidates),
            "continuity": continuity,
            "continuity_basis": continuity_basis,
            "explicit_structural_field": _region_field_record(
                explicit_structural_field
            ),
            "full_field_receipt_sha256": full_field_receipt_sha256,
            "lineage_receipt_sha256": lineage,
            "receptor_indices": list(receptors),
            "region_index": region_index,
            "schema": "guala.visual_region_observation.v1",
            "structural_receipt_sha256": structure,
        }

    def settle_l5(
        self,
        boundary: SixSenseFullFieldBoundary,
        receipt_registry: ReceiptRegistry,
        *,
        exposure_evidence=None,
        preparation_receipt_sha256: str | None = None,
    ) -> VisualL5Settlement:
        if not isinstance(boundary, SixSenseFullFieldBoundary):
            raise TypeError("visual L5 requires a six-sense full-field boundary")
        if not isinstance(receipt_registry, ReceiptRegistry):
            raise TypeError("visual L5 requires the mounted receipt registry")
        boundary.verify(receipt_registry)
        sight = next(
            (
                value
                for value in boundary.boundaries
                if value.sense is PhysicalSense.SIGHT
            ),
            None,
        )
        if sight is None or sight.state is not SenseBoundaryState.OBSERVED:
            raise ValueError("visual L5 requires an observed sight boundary")
        receptor_fields = self._explicit_receptor_fields(sight)
        components = _region_components(receptor_fields)
        current_exposure_epoch_receipt = None
        authenticated_predecessor = False
        if exposure_evidence is not None:
            if self._exposure_epoch_authority is None:
                raise ValueError("visual exposure evidence has no authority")
            self._exposure_epoch_authority.verify(exposure_evidence)
            if (
                preparation_receipt_sha256
                != exposure_evidence.current_preparation_receipt_sha256
            ):
                raise ValueError(
                    "visual exposure evidence crossed preparation authority"
                )
            current_exposure_epoch_receipt = (
                exposure_evidence.authority_receipt_sha256
            )
            authenticated_predecessor = bool(
                self._live
                and self._prior_source_time_end is not None
                and sight.source_time_start == self._prior_source_time_end
                and exposure_evidence.relation
                == "authenticated_predecessor_evidence"
                and exposure_evidence.authenticated_predecessor_epoch_receipt_sha256
                == self._prior_exposure_epoch_receipt
            )
        if authenticated_predecessor:
            window_relation = "authenticated_predecessor_evidence"
            prior = self._prior_regions
        elif self._live and self._prior_source_time_end is not None:
            if sight.source_time_start < self._prior_source_time_end:
                raise ValueError(
                    "visual source interval overlaps or reorders its predecessor"
                )
            window_relation = (
                "touching_window_bounds"
                if sight.source_time_start == self._prior_source_time_end
                else "gap"
            )
            prior = self._prior_regions
        else:
            window_relation = "first"
            prior = ()

        current_descriptors = []
        for region_index, receptors in enumerate(components):
            origin_row, origin_column = divmod(receptors[0], RETINA_COLUMNS)
            explicit_structural_field = tuple(
                (
                    index // RETINA_COLUMNS - origin_row,
                    index % RETINA_COLUMNS - origin_column,
                    receptor_fields[index],
                )
                for index in receptors
            )
            structure = _region_structure_receipt(explicit_structural_field)
            current_descriptors.append({
                "explicit_structural_field": explicit_structural_field,
                "region_index": region_index,
                "receptor_indices": receptors,
                "structural_receipt_sha256": structure,
            })

        exact_current_by_prior: dict[int, tuple[int, ...]] = {}
        overlap_current_by_prior: dict[int, tuple[int, ...]] = {}
        for prior_index, prior_region in enumerate(prior):
            prior_receptors = set(prior_region["receptor_indices"])
            exact_current_by_prior[prior_index] = tuple(
                value["region_index"]
                for value in current_descriptors
                if value["structural_receipt_sha256"]
                == prior_region["structural_receipt_sha256"]
                and value["explicit_structural_field"]
                == prior_region["explicit_structural_field"]
            )
            overlap_current_by_prior[prior_index] = tuple(
                value["region_index"]
                for value in current_descriptors
                if prior_receptors.intersection(value["receptor_indices"])
            )

        regions = []
        next_prior = []
        exact_claimed_prior: set[int] = set()
        exact_claimed_current: set[int] = set()
        exact_unique_pairs: dict[int, int] = {}
        if window_relation in {
            "authenticated_predecessor_evidence",
            "touching_window_bounds",
        }:
            for descriptor in current_descriptors:
                region_index = int(descriptor["region_index"])
                exact_prior = tuple(
                    prior_index
                    for prior_index, prior_region in enumerate(prior)
                    if prior_region["structural_receipt_sha256"]
                    == descriptor["structural_receipt_sha256"]
                    and prior_region["explicit_structural_field"]
                    == descriptor["explicit_structural_field"]
                )
                if (
                    len(exact_prior) == 1
                    and len(exact_current_by_prior[exact_prior[0]]) == 1
                ):
                    exact_unique_pairs[region_index] = exact_prior[0]
                    exact_claimed_prior.add(exact_prior[0])
                    exact_claimed_current.add(region_index)

        for descriptor in current_descriptors:
            region_index = int(descriptor["region_index"])
            receptors = tuple(descriptor["receptor_indices"])
            structure = str(descriptor["structural_receipt_sha256"])
            explicit_structural_field = tuple(
                descriptor["explicit_structural_field"]
            )
            receptor_set = set(receptors)
            exact_matches = tuple(
                (prior_index, value)
                for prior_index, value in enumerate(prior)
                if value["structural_receipt_sha256"] == structure
                and value["explicit_structural_field"]
                == explicit_structural_field
            )
            overlap_matches = tuple(
                (prior_index, value)
                for prior_index, value in enumerate(prior)
                if receptor_set.intersection(value["receptor_indices"])
            )
            chosen_prior = exact_unique_pairs.get(region_index)
            if chosen_prior is not None:
                continuity = "ambiguous"
                continuity_basis = (
                    "authenticated_exact_structural_recurrence_candidate"
                    if window_relation == "authenticated_predecessor_evidence"
                    else "touching_exact_structural_recurrence_candidate"
                )
                candidates = (
                    str(prior[chosen_prior]["lineage_receipt_sha256"]),
                )
                lineage = self._lineage_anchor(
                    boundary.assembly_id, region_index, structure
                )
            elif window_relation in {
                "authenticated_predecessor_evidence",
                "touching_window_bounds",
            }:
                unmatched_overlap = tuple(
                    (prior_index, value)
                    for prior_index, value in overlap_matches
                    if prior_index not in exact_claimed_prior
                )
                reciprocal = tuple(
                    (prior_index, value)
                    for prior_index, value in unmatched_overlap
                    if tuple(
                        current_index
                        for current_index in overlap_current_by_prior[prior_index]
                        if current_index not in exact_claimed_current
                    ) == (region_index,)
                )
                if len(reciprocal) == 1 and len(unmatched_overlap) == 1:
                    continuity = "ambiguous"
                    continuity_basis = (
                        "authenticated_reciprocal_retinotopic_overlap_candidate"
                        if window_relation
                        == "authenticated_predecessor_evidence"
                        else "touching_reciprocal_retinotopic_overlap_candidate"
                    )
                    candidates = (
                        str(reciprocal[0][1]["lineage_receipt_sha256"]),
                    )
                    lineage = self._lineage_anchor(
                        boundary.assembly_id, region_index, structure
                    )
                else:
                    candidate_values = {
                        str(value["lineage_receipt_sha256"])
                        for _, value in (*exact_matches, *unmatched_overlap)
                    }
                    candidates = tuple(sorted(candidate_values))
                    continuity = "ambiguous" if candidates else "unknown"
                    if window_relation == "authenticated_predecessor_evidence":
                        continuity_basis = (
                            "authenticated_competing_candidates"
                            if candidates
                            else "authenticated_no_candidate"
                        )
                    else:
                        continuity_basis = (
                            "touching_competing_candidates"
                            if candidates
                            else "touching_no_candidate"
                        )
                    lineage = self._lineage_anchor(
                        boundary.assembly_id, region_index, structure
                    )
            elif window_relation == "gap" and exact_matches:
                continuity = "ambiguous"
                continuity_basis = "source_gap_structural_recurrence"
                candidates = tuple(sorted({
                    str(value["lineage_receipt_sha256"])
                    for _, value in exact_matches
                }))
                lineage = self._lineage_anchor(
                    boundary.assembly_id, region_index, structure
                )
            else:
                continuity = "unknown"
                continuity_basis = (
                    "source_gap_no_recurrence"
                    if window_relation == "gap"
                    else "no_live_predecessor"
                )
                candidates = ()
                lineage = self._lineage_anchor(
                    boundary.assembly_id, region_index, structure
                )
            payload = self._region_receipt_payload(
                assembly_id=boundary.assembly_id,
                full_field_receipt_sha256=boundary.authority_receipt_sha256,
                region_index=region_index,
                receptors=receptors,
                explicit_structural_field=explicit_structural_field,
                structure=structure,
                continuity=continuity,
                continuity_basis=continuity_basis,
                lineage=lineage,
                candidates=candidates,
            )
            region_receipt = _hmac_hex(
                self._key, b"guala-visual-region-observation-v1", payload
            )
            regions.append(
                VisualRegionObservation(
                    region_index=region_index,
                    receptor_indices=receptors,
                    explicit_structural_field=explicit_structural_field,
                    structural_receipt_sha256=structure,
                    continuity=continuity,
                    continuity_basis=continuity_basis,
                    lineage_receipt_sha256=lineage,
                    candidate_lineage_receipt_sha256s=candidates,
                    authority_receipt_sha256=region_receipt,
                )
            )
            if lineage is not None:
                next_prior.append(
                    {
                        "lineage_receipt_sha256": lineage,
                        "receptor_indices": list(receptors),
                        "explicit_structural_field": (
                            explicit_structural_field
                        ),
                        "structural_receipt_sha256": structure,
                    }
                )
        settlement_payload = {
            "assembly_id": boundary.assembly_id,
            "full_field_receipt_sha256": boundary.authority_receipt_sha256,
            "window_relation": window_relation,
            "source_time_end": (
                f"{sight.source_time_end.numerator}/"
                f"{sight.source_time_end.denominator}"
            ),
            "source_time_start": (
                f"{sight.source_time_start.numerator}/"
                f"{sight.source_time_start.denominator}"
            ),
            "region_receipt_sha256s": [
                value.authority_receipt_sha256 for value in regions
            ],
            "schema": _SETTLEMENT_SCHEMA,
        }
        settlement = VisualL5Settlement(
            assembly_id=boundary.assembly_id,
            source_time_start=sight.source_time_start,
            source_time_end=sight.source_time_end,
            window_relation=window_relation,
            full_field_receipt_sha256=boundary.authority_receipt_sha256,
            regions=tuple(regions),
            authority_receipt_sha256=_hmac_hex(
                self._key, b"guala-visual-l5-settlement-v1", settlement_payload
            ),
        )
        self.verify_settlement(settlement)
        record = settlement.as_record()
        history = (*self._history, record)[-self._history_capacity :]
        self._prior_regions = tuple(next_prior)
        self._prior_source_time_end = sight.source_time_end
        self._prior_exposure_epoch_receipt = current_exposure_epoch_receipt
        self._live = True
        self._history = tuple(history)
        return settlement

    def verify_settlement(self, settlement: VisualL5Settlement) -> None:
        if not isinstance(settlement, VisualL5Settlement):
            raise TypeError("visual settlement is not typed")
        for region in settlement.regions:
            payload = self._region_receipt_payload(
                assembly_id=settlement.assembly_id,
                full_field_receipt_sha256=settlement.full_field_receipt_sha256,
                region_index=region.region_index,
                receptors=region.receptor_indices,
                explicit_structural_field=region.explicit_structural_field,
                structure=region.structural_receipt_sha256,
                continuity=region.continuity,
                continuity_basis=region.continuity_basis,
                lineage=region.lineage_receipt_sha256,
                candidates=region.candidate_lineage_receipt_sha256s,
            )
            expected = _hmac_hex(
                self._key, b"guala-visual-region-observation-v1", payload
            )
            if not hmac.compare_digest(expected, region.authority_receipt_sha256):
                raise ValueError("visual region receipt authentication failed")
        payload = {
            "assembly_id": settlement.assembly_id,
            "full_field_receipt_sha256": settlement.full_field_receipt_sha256,
            "window_relation": settlement.window_relation,
            "source_time_end": (
                f"{settlement.source_time_end.numerator}/"
                f"{settlement.source_time_end.denominator}"
            ),
            "source_time_start": (
                f"{settlement.source_time_start.numerator}/"
                f"{settlement.source_time_start.denominator}"
            ),
            "region_receipt_sha256s": [
                value.authority_receipt_sha256 for value in settlement.regions
            ],
            "schema": _SETTLEMENT_SCHEMA,
        }
        expected = _hmac_hex(
            self._key, b"guala-visual-l5-settlement-v1", payload
        )
        if not hmac.compare_digest(expected, settlement.authority_receipt_sha256):
            raise ValueError("visual L5 settlement authentication failed")

    def snapshot_encoded(self) -> bytes:
        payload = {
            "history": list(self._history),
            "history_capacity": self._history_capacity,
            "live": self._live,
            "prior_exposure_epoch_receipt": (
                self._prior_exposure_epoch_receipt
            ),
            "prior_source_time_end": (
                f"{self._prior_source_time_end.numerator}/"
                f"{self._prior_source_time_end.denominator}"
                if self._prior_source_time_end is not None
                else None
            ),
            "prior_regions": [
                {
                    **{
                        key: value
                        for key, value in region.items()
                        if key != "explicit_structural_field"
                    },
                    "explicit_structural_field": _region_field_record(
                        region["explicit_structural_field"]
                    ),
                }
                for region in self._prior_regions
            ],
            "schema": _STATE_SCHEMA,
        }
        envelope = {
            "payload": payload,
            "state_hmac_sha256": _hmac_hex(
                self._key, b"guala-visual-region-state-v1", payload
            ),
        }
        encoded = _canonical_bytes(envelope)
        if len(encoded) > MAX_VISUAL_STATE_BYTES:
            raise RuntimeError("visual continuity state exceeds its byte boundary")
        return encoded

    def _restore_encoded(self, encoded: bytes, *, activate: bool) -> None:
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("visual continuity state must be nonempty bytes")
        if len(encoded) > MAX_VISUAL_STATE_BYTES:
            raise ValueError("visual continuity state exceeds its byte boundary")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("visual continuity state is invalid JSON") from error
        if _canonical_bytes(envelope) != encoded:
            raise ValueError("visual continuity state is not canonical")
        if not isinstance(envelope, dict) or set(envelope) != {
            "payload",
            "state_hmac_sha256",
        }:
            raise ValueError("visual continuity state envelope changed")
        payload = envelope["payload"]
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "history",
                "history_capacity",
                "live",
                "prior_exposure_epoch_receipt",
                "prior_regions",
                "prior_source_time_end",
                "schema",
            }
            or payload["schema"] != _STATE_SCHEMA
            or payload["history_capacity"] != self._history_capacity
            or not isinstance(payload["history"], list)
            or not isinstance(payload["live"], bool)
            or not isinstance(payload["prior_regions"], list)
            or len(payload["history"]) > self._history_capacity
            or len(payload["prior_regions"]) > RETINA_RECEPTOR_COUNT
        ):
            raise ValueError("visual continuity state fields changed")
        expected = _hmac_hex(
            self._key, b"guala-visual-region-state-v1", payload
        )
        if not hmac.compare_digest(expected, envelope["state_hmac_sha256"]):
            raise ValueError("visual continuity state authentication failed")
        prior_exposure_epoch_receipt = payload[
            "prior_exposure_epoch_receipt"
        ]
        if prior_exposure_epoch_receipt is not None:
            prior_exposure_epoch_receipt = _require_sha256(
                prior_exposure_epoch_receipt,
                "visual prior exposure epoch receipt",
            )
        prior_source_time_end = payload["prior_source_time_end"]
        if prior_source_time_end is not None:
            if (
                not isinstance(prior_source_time_end, str)
                or prior_source_time_end.count("/") != 1
            ):
                raise ValueError("visual prior source time changed")
            numerator, denominator = prior_source_time_end.split("/", 1)
            try:
                prior_source_time_end_value = Fraction(
                    int(numerator), int(denominator)
                )
            except (TypeError, ValueError, ZeroDivisionError) as error:
                raise ValueError("visual prior source time changed") from error
            if (
                f"{prior_source_time_end_value.numerator}/"
                f"{prior_source_time_end_value.denominator}"
                != prior_source_time_end
            ):
                raise ValueError("visual prior source time is not canonical")
        else:
            prior_source_time_end_value = None
        prior = []
        for value in payload["prior_regions"]:
            if not isinstance(value, dict) or set(value) != {
                "explicit_structural_field",
                "lineage_receipt_sha256",
                "receptor_indices",
                "structural_receipt_sha256",
            }:
                raise ValueError("visual prior-region state changed")
            lineage = _require_sha256(
                value["lineage_receipt_sha256"], "visual lineage receipt"
            )
            structure = _require_sha256(
                value["structural_receipt_sha256"], "visual structure receipt"
            )
            explicit_structural_field = _region_field_from_record(
                value["explicit_structural_field"]
            )
            if structure != _region_structure_receipt(
                explicit_structural_field
            ):
                raise ValueError(
                    "visual prior structure receipt differs from explicit field"
                )
            receptors = tuple(value["receptor_indices"])
            if (
                not receptors
                or len(explicit_structural_field) != len(receptors)
                or tuple(sorted(receptors)) != receptors
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, int)
                    or item < 0
                    or item >= RETINA_RECEPTOR_COUNT
                    for item in receptors
                )
            ):
                raise ValueError("visual prior-region receptors changed")
            prior.append(
                {
                    "explicit_structural_field": explicit_structural_field,
                    "lineage_receipt_sha256": lineage,
                    "receptor_indices": list(receptors),
                    "structural_receipt_sha256": structure,
                }
            )
        if payload["live"] != bool(prior) or (
            payload["live"] != (prior_source_time_end_value is not None)
        ):
            raise ValueError("visual live continuity state changed")
        history = []
        for record in payload["history"]:
            if (
                not isinstance(record, dict)
                or record.get("schema") != _SETTLEMENT_SCHEMA
            ):
                raise ValueError("visual history record changed")
            history.append(record)
        self._prior_regions = tuple(prior) if activate and payload["live"] else ()
        self._prior_source_time_end = (
            prior_source_time_end_value
            if activate and payload["live"]
            else None
        )
        self._prior_exposure_epoch_receipt = (
            prior_exposure_epoch_receipt
            if activate and payload["live"]
            else None
        )
        self._live = bool(activate and payload["live"])
        self._history = tuple(history)

    def restore_encoded(self, encoded: bytes) -> None:
        self._restore_encoded(encoded, activate=False)

    def rollback_encoded(self, encoded: bytes) -> None:
        self._restore_encoded(encoded, activate=True)

    def status(self) -> dict[str, object]:
        latest = self._history[-1] if self._history else None
        return {
            "schema": "guala.visual_region_continuity.status.v3",
            "retina_rows": RETINA_ROWS,
            "retina_columns": RETINA_COLUMNS,
            "receptor_count": RETINA_RECEPTOR_COUNT,
            "active": self._live,
            "history_count": len(self._history),
            "latest": latest,
            "field_contract": {
                "dsf_projection": "none",
                "dsf_fields": [
                    "D_k", "M_k", "R_rev_k", "U_star_k",
                    "C_k", "P_k", "B_k",
                ],
                "retina_sampling": "8x8 nonoverlapping area-mean receptors",
                "temporal_transduction": (
                    "one physical pixel reset reference followed by the "
                    "window's exposures"
                ),
                "spatial_sampling_loss": (
                    "within-receptor 8x8 pixel arrangement is not retained; "
                    "every receptor trajectory and every resulting DSF field "
                    "is retained"
                ),
                "window_relation": (
                    "authenticated_predecessor_evidence proves successive "
                    "server-owned acquisition windows; touching_window_bounds "
                    "proves only declared interval contact; neither proves "
                    "object identity"
                ),
                "unique_continuity_authority": (
                    "unavailable without an independently continuous camera "
                    "stream or overlapping visual causal windows"
                ),
            },
        }


__all__ = (
    "CanonicalVisualFrame",
    "DEFAULT_VISUAL_L5_HISTORY",
    "DeterministicVisualRegionContinuityAuthority",
    "decode_visual_image_bytes",
    "canonical_visual_frames_from_claims",
    "MAX_VISUAL_IMAGE_BYTES",
    "MAX_VISUAL_SOURCE_HEIGHT",
    "MAX_VISUAL_SOURCE_WIDTH",
    "MAX_VISUAL_FRAMES",
    "MIN_VISUAL_FRAMES",
    "PreparedRetinotopicSight",
    "RETINA_COLUMNS",
    "RETINA_RECEPTOR_COUNT",
    "RETINA_ROWS",
    "VisualL5Settlement",
    "VisualRegionObservation",
)
