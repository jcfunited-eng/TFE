"""Exact, receipt-bound Global-UF adjacent-state validation.

Global-UF replays one immutable observation window from one immutable
pre-window state.  The base state and every admissible adjacent native sensor
code are executed by an independent provider.  PASS means that every replay
resolved and returned the same complete structural basin.  One exact basin
counterexample is FAIL.  Missing, invalid, or unresolved evidence is UNKNOWN.

The seven DSF L4 fields are retained together as exact rational tuples:
``D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k``.  Their immutable tuple
receipts are the primary L4 basin authority.  Sign/zero labels are retained
only as a derived, secondary semialgebraic description and can never replace
the exact tuple.  No score, tolerance, weighted reduction, lookup table, or
probabilistic comparison is used.

The commit portion of a replay basin is not a provider-declared COMMIT label.
It is a verified :class:`PendingGlobalUFConjunction` produced by the common
commit boundary after every authority except the recursively pending
Global-UF result has been evaluated.  Each counterfactual may bind its own
closed-experience receipt while the validation authority remains anchored to
the base closed-experience context named by the replay plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Iterable, Protocol, runtime_checkable

from .commit import (
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    PendingGlobalUFConjunction,
    PendingGlobalUFStatus,
    binary_authority_receipt_payload,
)
from .field import MountedFieldTopology
from .l6 import N_START
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


GLOBAL_UF_OPERATOR_ID = "glew.global_uf.exact_adjacent_state_replay.v2"
DSF_FIELD_ORDER = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _require_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReceiptError(f"{field_name} must be an exact integer")
    return value


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    field_name: str,
) -> None:
    mounted = registry.resolve(digest, field_name)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} differs from mounted authority bytes")


def _extend_with_records(
    registry: ReceiptRegistry,
    records: Iterable[ReceiptRecord],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("Global-UF requires a mounted receipt registry")
    mounted = {record.digest: record.payload for record in registry.records}
    additions: dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("replay provider returned a non-receipt record")
        prior = mounted.get(record.digest)
        if prior is not None and prior != record.payload:
            raise ReceiptError("receipt digest collision at Global-UF boundary")
        repeated = additions.get(record.digest)
        if repeated is not None and repeated != record.payload:
            raise ReceiptError("provider repeated a digest with different bytes")
        additions[record.digest] = record.payload
    new_records = tuple(
        ReceiptRecord(digest, additions[digest])
        for digest in sorted(additions)
        if digest not in mounted
    )
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        (*registry.records, *new_records),
    )


def _extend_with_payloads(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    records: list[ReceiptRecord] = []
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("Global-UF generated an empty receipt payload")
        records.append(ReceiptRecord(receipt_sha256(payload), payload))
    return _extend_with_records(registry, records)


@dataclass(frozen=True, slots=True, order=True)
class ObservationCoordinate:
    """One exact raw coordinate before native transduction."""

    lane_id: str
    port_id: str
    source_index: int
    coordinate_id: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "observation lane_id")
        require_identifier(self.port_id, "observation port_id")
        _require_integer(self.source_index, "observation source_index")
        if self.source_index < 0:
            raise ReceiptError("observation source_index cannot be negative")
        require_identifier(self.coordinate_id, "observation coordinate_id")

    @property
    def port_key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)


def _coordinate_payload(value: ObservationCoordinate) -> dict[str, object]:
    if not isinstance(value, ObservationCoordinate):
        raise ReceiptError("observation coordinate is not typed")
    return {
        "coordinate_id": value.coordinate_id,
        "lane_id": value.lane_id,
        "port_id": value.port_id,
        "source_index": value.source_index,
    }


@dataclass(frozen=True, slots=True)
class SensorIntegerObservation:
    coordinate: ObservationCoordinate
    raw_code: int

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate, ObservationCoordinate):
            raise ReceiptError("sensor observation requires a typed coordinate")
        _require_integer(self.raw_code, "sensor raw_code")


@dataclass(frozen=True, slots=True)
class TypedUnicodeObservation:
    """Exact artificial-interface data retained without numeric coercion."""

    coordinate: ObservationCoordinate
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate, ObservationCoordinate):
            raise ReceiptError("typed Unicode observation requires a coordinate")
        if not isinstance(self.text, str) or not self.text:
            raise ReceiptError("typed Unicode observation must contain exact text")
        try:
            self.text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ReceiptError("typed Unicode observation contains a surrogate") from exc


def raw_observation_window_receipt_payload(
    *,
    window_id: str,
    sensor_observations: tuple[SensorIntegerObservation, ...],
    typed_unicode_observations: tuple[TypedUnicodeObservation, ...],
) -> bytes:
    require_identifier(window_id, "raw observation window_id")
    if not isinstance(sensor_observations, tuple):
        raise ReceiptError("sensor observations must be an immutable tuple")
    if not isinstance(typed_unicode_observations, tuple):
        raise ReceiptError("typed Unicode observations must be an immutable tuple")
    return _canonical_bytes(
        {
            "schema": "glew.global_uf.raw_observation_window.v2",
            "sensor_integer_observations": [
                {
                    "coordinate": _coordinate_payload(value.coordinate),
                    "raw_code": value.raw_code,
                }
                for value in sensor_observations
            ],
            "typed_unicode_observations": [
                {
                    "coordinate": _coordinate_payload(value.coordinate),
                    "text": value.text,
                }
                for value in typed_unicode_observations
            ],
            "window_id": window_id,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedRawObservationWindow:
    window_id: str
    sensor_observations: tuple[SensorIntegerObservation, ...]
    typed_unicode_observations: tuple[TypedUnicodeObservation, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.window_id, "raw observation window_id")
        sha256_digest(
            self.authority_receipt_sha256,
            "raw observation window authority receipt",
        )
        if not isinstance(self.sensor_observations, tuple) or not all(
            isinstance(value, SensorIntegerObservation)
            for value in self.sensor_observations
        ):
            raise ReceiptError("sensor observations must be a typed immutable tuple")
        if not isinstance(self.typed_unicode_observations, tuple) or not all(
            isinstance(value, TypedUnicodeObservation)
            for value in self.typed_unicode_observations
        ):
            raise ReceiptError(
                "typed Unicode observations must be a typed immutable tuple"
            )
        sensor_coordinates = tuple(
            value.coordinate for value in self.sensor_observations
        )
        typed_coordinates = tuple(
            value.coordinate for value in self.typed_unicode_observations
        )
        if sensor_coordinates != tuple(sorted(sensor_coordinates)):
            raise ReceiptError("sensor observations are not in canonical order")
        if typed_coordinates != tuple(sorted(typed_coordinates)):
            raise ReceiptError("typed Unicode observations are not canonical")
        all_coordinates = (*sensor_coordinates, *typed_coordinates)
        if len(set(all_coordinates)) != len(all_coordinates):
            raise ReceiptError("raw observation window repeats a coordinate")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        expected = raw_observation_window_receipt_payload(
            window_id=self.window_id,
            sensor_observations=self.sensor_observations,
            typed_unicode_observations=self.typed_unicode_observations,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "raw observation window authority receipt",
        )


@dataclass(frozen=True, slots=True)
class SensorCodeResolution:
    coordinate: ObservationCoordinate
    minimum_code: int
    maximum_code: int
    physical_quantum: Fraction
    source_authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate, ObservationCoordinate):
            raise ReceiptError("sensor resolution requires a typed coordinate")
        _require_integer(self.minimum_code, "minimum sensor code")
        _require_integer(self.maximum_code, "maximum sensor code")
        if self.minimum_code > self.maximum_code:
            raise ReceiptError("sensor code bounds are inverted")
        require_fraction(self.physical_quantum, "sensor physical_quantum")
        if self.physical_quantum <= 0:
            raise ReceiptError("sensor physical_quantum must be strictly positive")
        sha256_digest(
            self.source_authority_receipt_sha256,
            "sensor resolution source authority receipt",
        )


def sensor_resolution_profile_receipt_payload(
    *,
    profile_id: str,
    observation_window_receipt_sha256: str,
    resolutions: tuple[SensorCodeResolution, ...],
) -> bytes:
    require_identifier(profile_id, "sensor resolution profile_id")
    sha256_digest(
        observation_window_receipt_sha256,
        "sensor profile observation-window receipt",
    )
    if not isinstance(resolutions, tuple):
        raise ReceiptError("sensor resolutions must be an immutable tuple")
    return _canonical_bytes(
        {
            "observation_window_receipt_sha256": (
                observation_window_receipt_sha256
            ),
            "profile_id": profile_id,
            "resolutions": [
                {
                    "coordinate": _coordinate_payload(value.coordinate),
                    "maximum_code": value.maximum_code,
                    "minimum_code": value.minimum_code,
                    "physical_quantum": _fraction_text(value.physical_quantum),
                    "source_authority_receipt_sha256": (
                        value.source_authority_receipt_sha256
                    ),
                }
                for value in resolutions
            ],
            "schema": "glew.global_uf.sensor_resolution_profile.v2",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedSensorResolutionProfile:
    profile_id: str
    observation_window_receipt_sha256: str
    resolutions: tuple[SensorCodeResolution, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.profile_id, "sensor resolution profile_id")
        sha256_digest(
            self.observation_window_receipt_sha256,
            "sensor profile observation-window receipt",
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "sensor resolution profile authority receipt",
        )
        if not isinstance(self.resolutions, tuple) or not all(
            isinstance(value, SensorCodeResolution) for value in self.resolutions
        ):
            raise ReceiptError("sensor resolutions must be a typed immutable tuple")
        coordinates = tuple(value.coordinate for value in self.resolutions)
        if coordinates != tuple(sorted(coordinates)):
            raise ReceiptError("sensor resolutions are not in canonical order")
        if len(set(coordinates)) != len(coordinates):
            raise ReceiptError("sensor resolution profile repeats a coordinate")

    def verify(
        self,
        observation_window: MountedRawObservationWindow,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if not isinstance(observation_window, MountedRawObservationWindow):
            raise ReceiptError("sensor profile requires a mounted observation window")
        if (
            self.observation_window_receipt_sha256
            != observation_window.authority_receipt_sha256
        ):
            raise ReceiptError("sensor profile belongs to another observation window")
        expected_coordinates = tuple(
            value.coordinate for value in observation_window.sensor_observations
        )
        actual_coordinates = tuple(value.coordinate for value in self.resolutions)
        if actual_coordinates != expected_coordinates:
            raise ReceiptError(
                "sensor profile must cover every and only integer sensor observation"
            )
        for observation, resolution in zip(
            observation_window.sensor_observations,
            self.resolutions,
            strict=True,
        ):
            if not (
                resolution.minimum_code
                <= observation.raw_code
                <= resolution.maximum_code
            ):
                raise ReceiptError("base sensor code lies outside mounted exact bounds")
            receipt_registry.resolve(
                resolution.source_authority_receipt_sha256,
                "sensor resolution source authority receipt",
            )
        expected = sensor_resolution_profile_receipt_payload(
            profile_id=self.profile_id,
            observation_window_receipt_sha256=(
                self.observation_window_receipt_sha256
            ),
            resolutions=self.resolutions,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "sensor resolution profile authority receipt",
        )


def pre_window_state_receipt_payload(
    *,
    state_id: str,
    chemistry_state_receipt_sha256: str,
    field_state_receipt_sha256: str,
    mode_state_receipt_sha256: str,
    memory_state_receipt_sha256: str,
    l6_state_receipt_sha256: str,
) -> bytes:
    require_identifier(state_id, "pre-window state_id")
    for digest, field_name in (
        (chemistry_state_receipt_sha256, "chemistry state receipt"),
        (field_state_receipt_sha256, "field state receipt"),
        (mode_state_receipt_sha256, "mode state receipt"),
        (memory_state_receipt_sha256, "memory state receipt"),
        (l6_state_receipt_sha256, "L6 state receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "chemistry_state_receipt_sha256": chemistry_state_receipt_sha256,
            "field_state_receipt_sha256": field_state_receipt_sha256,
            "l6_state_receipt_sha256": l6_state_receipt_sha256,
            "memory_state_receipt_sha256": memory_state_receipt_sha256,
            "mode_state_receipt_sha256": mode_state_receipt_sha256,
            "schema": "glew.global_uf.pre_window_state.v2",
            "state_id": state_id,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedPreWindowState:
    state_id: str
    chemistry_state_receipt_sha256: str
    field_state_receipt_sha256: str
    mode_state_receipt_sha256: str
    memory_state_receipt_sha256: str
    l6_state_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.state_id, "pre-window state_id")
        for digest, field_name in (
            (self.chemistry_state_receipt_sha256, "chemistry state receipt"),
            (self.field_state_receipt_sha256, "field state receipt"),
            (self.mode_state_receipt_sha256, "mode state receipt"),
            (self.memory_state_receipt_sha256, "memory state receipt"),
            (self.l6_state_receipt_sha256, "L6 state receipt"),
            (self.authority_receipt_sha256, "pre-window authority receipt"),
        ):
            sha256_digest(digest, field_name)

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for digest, field_name in (
            (self.chemistry_state_receipt_sha256, "chemistry state receipt"),
            (self.field_state_receipt_sha256, "field state receipt"),
            (self.mode_state_receipt_sha256, "mode state receipt"),
            (self.memory_state_receipt_sha256, "memory state receipt"),
            (self.l6_state_receipt_sha256, "L6 state receipt"),
        ):
            receipt_registry.resolve(digest, field_name)
        expected = pre_window_state_receipt_payload(
            state_id=self.state_id,
            chemistry_state_receipt_sha256=self.chemistry_state_receipt_sha256,
            field_state_receipt_sha256=self.field_state_receipt_sha256,
            mode_state_receipt_sha256=self.mode_state_receipt_sha256,
            memory_state_receipt_sha256=self.memory_state_receipt_sha256,
            l6_state_receipt_sha256=self.l6_state_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "pre-window state authority receipt",
        )


class ReplayKind(str, Enum):
    BASE = "base"
    ADJACENT_CODE = "adjacent_code"


class AdjacentDirection(int, Enum):
    NEGATIVE = -1
    POSITIVE = 1


@dataclass(frozen=True, slots=True)
class ReplaySensorCode:
    coordinate: ObservationCoordinate
    raw_code: int

    def __post_init__(self) -> None:
        if not isinstance(self.coordinate, ObservationCoordinate):
            raise ReceiptError("replay sensor code requires a coordinate")
        _require_integer(self.raw_code, "replay sensor raw_code")


def global_uf_replay_request_receipt_payload(
    *,
    request_id: str,
    request_index: int,
    kind: ReplayKind,
    target_coordinate: ObservationCoordinate | None,
    direction: AdjacentDirection | None,
    physical_delta: Fraction,
    sensor_codes: tuple[ReplaySensorCode, ...],
    topology_authority_receipt_sha256: str,
    base_closed_experience_receipt_sha256: str,
    observation_window_receipt_sha256: str,
    sensor_resolution_profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
) -> bytes:
    require_identifier(request_id, "Global-UF replay request_id")
    _require_integer(request_index, "Global-UF replay request_index")
    if request_index < 0:
        raise ReceiptError("Global-UF replay request_index cannot be negative")
    if not isinstance(kind, ReplayKind):
        raise ReceiptError("Global-UF replay kind must be typed")
    if target_coordinate is not None and not isinstance(
        target_coordinate,
        ObservationCoordinate,
    ):
        raise ReceiptError("Global-UF target coordinate is not typed")
    if direction is not None and not isinstance(direction, AdjacentDirection):
        raise ReceiptError("Global-UF adjacent direction is not typed")
    require_fraction(physical_delta, "Global-UF physical_delta")
    if not isinstance(sensor_codes, tuple):
        raise ReceiptError("Global-UF sensor codes must be immutable")
    for digest, field_name in (
        (topology_authority_receipt_sha256, "Global-UF topology receipt"),
        (
            base_closed_experience_receipt_sha256,
            "Global-UF base experience receipt",
        ),
        (observation_window_receipt_sha256, "Global-UF observation receipt"),
        (
            sensor_resolution_profile_receipt_sha256,
            "Global-UF sensor-resolution receipt",
        ),
        (pre_window_state_receipt_sha256, "Global-UF pre-window state receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "base_closed_experience_receipt_sha256": (
                base_closed_experience_receipt_sha256
            ),
            "kind": kind.value,
            "observation_window_receipt_sha256": (
                observation_window_receipt_sha256
            ),
            "physical_delta": _fraction_text(physical_delta),
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "request_id": request_id,
            "request_index": request_index,
            "schema": "glew.global_uf.replay_request.v2",
            "sensor_codes": [
                {
                    "coordinate": _coordinate_payload(value.coordinate),
                    "raw_code": value.raw_code,
                }
                for value in sensor_codes
            ],
            "sensor_resolution_profile_receipt_sha256": (
                sensor_resolution_profile_receipt_sha256
            ),
            "target": (
                None
                if target_coordinate is None
                else {
                    "coordinate": _coordinate_payload(target_coordinate),
                    "direction": direction.value if direction is not None else None,
                }
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
            "typed_unicode": "retained_by_observation_window_receipt",
        }
    )


@dataclass(frozen=True, slots=True)
class GlobalUFReplayRequest:
    request_id: str
    request_index: int
    kind: ReplayKind
    target_coordinate: ObservationCoordinate | None
    direction: AdjacentDirection | None
    physical_delta: Fraction
    sensor_codes: tuple[ReplaySensorCode, ...]
    topology_authority_receipt_sha256: str
    base_closed_experience_receipt_sha256: str
    observation_window_receipt_sha256: str
    sensor_resolution_profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        if self.kind is ReplayKind.BASE:
            if self.target_coordinate is not None or self.direction is not None:
                raise ReceiptError("base replay cannot carry a perturbation target")
            if self.physical_delta != 0:
                raise ReceiptError("base replay physical delta must be exact zero")
        elif self.kind is ReplayKind.ADJACENT_CODE:
            if self.target_coordinate is None or self.direction is None:
                raise ReceiptError("adjacent replay requires target and direction")
            if self.physical_delta == 0:
                raise ReceiptError("adjacent replay cannot carry zero physical delta")
        else:
            raise ReceiptError("Global-UF replay kind must be typed")
        if not isinstance(self.sensor_codes, tuple) or not all(
            isinstance(value, ReplaySensorCode) for value in self.sensor_codes
        ):
            raise ReceiptError("Global-UF sensor codes must be typed and immutable")
        coordinates = tuple(value.coordinate for value in self.sensor_codes)
        if coordinates != tuple(sorted(coordinates)):
            raise ReceiptError("Global-UF sensor codes are not canonical")
        if len(set(coordinates)) != len(coordinates):
            raise ReceiptError("Global-UF replay repeats a sensor coordinate")
        expected = global_uf_replay_request_receipt_payload(
            request_id=self.request_id,
            request_index=self.request_index,
            kind=self.kind,
            target_coordinate=self.target_coordinate,
            direction=self.direction,
            physical_delta=self.physical_delta,
            sensor_codes=self.sensor_codes,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            base_closed_experience_receipt_sha256=(
                self.base_closed_experience_receipt_sha256
            ),
            observation_window_receipt_sha256=(
                self.observation_window_receipt_sha256
            ),
            sensor_resolution_profile_receipt_sha256=(
                self.sensor_resolution_profile_receipt_sha256
            ),
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError("Global-UF replay request differs from its receipt")


def _make_replay_request(
    *,
    request_id: str,
    request_index: int,
    kind: ReplayKind,
    target_coordinate: ObservationCoordinate | None,
    direction: AdjacentDirection | None,
    physical_delta: Fraction,
    sensor_codes: tuple[ReplaySensorCode, ...],
    topology_authority_receipt_sha256: str,
    base_closed_experience_receipt_sha256: str,
    observation_window_receipt_sha256: str,
    sensor_resolution_profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
) -> GlobalUFReplayRequest:
    payload = global_uf_replay_request_receipt_payload(
        request_id=request_id,
        request_index=request_index,
        kind=kind,
        target_coordinate=target_coordinate,
        direction=direction,
        physical_delta=physical_delta,
        sensor_codes=sensor_codes,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        base_closed_experience_receipt_sha256=(
            base_closed_experience_receipt_sha256
        ),
        observation_window_receipt_sha256=observation_window_receipt_sha256,
        sensor_resolution_profile_receipt_sha256=(
            sensor_resolution_profile_receipt_sha256
        ),
        pre_window_state_receipt_sha256=pre_window_state_receipt_sha256,
    )
    return GlobalUFReplayRequest(
        request_id=request_id,
        request_index=request_index,
        kind=kind,
        target_coordinate=target_coordinate,
        direction=direction,
        physical_delta=physical_delta,
        sensor_codes=sensor_codes,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        base_closed_experience_receipt_sha256=(
            base_closed_experience_receipt_sha256
        ),
        observation_window_receipt_sha256=observation_window_receipt_sha256,
        sensor_resolution_profile_receipt_sha256=(
            sensor_resolution_profile_receipt_sha256
        ),
        pre_window_state_receipt_sha256=pre_window_state_receipt_sha256,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def enumerate_global_uf_replay_requests(
    *,
    topology: MountedFieldTopology,
    closed_experience_receipt_sha256: str,
    observation_window: MountedRawObservationWindow,
    sensor_resolution_profile: MountedSensorResolutionProfile,
    pre_window_state: MountedPreWindowState,
    receipt_registry: ReceiptRegistry,
) -> tuple[GlobalUFReplayRequest, ...]:
    """Return the complete finite native adjacent-code replay plan."""

    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("Global-UF enumeration requires a mounted topology")
    topology.verify(receipt_registry)
    sha256_digest(
        closed_experience_receipt_sha256,
        "Global-UF base closed-experience receipt",
    )
    receipt_registry.resolve(
        closed_experience_receipt_sha256,
        "Global-UF base closed-experience receipt",
    )
    observation_window.verify(receipt_registry)
    sensor_resolution_profile.verify(observation_window, receipt_registry)
    pre_window_state.verify(receipt_registry)
    topology_keys = {fiber.key for fiber in topology.ordered_port_fibers}
    for observation in (
        *observation_window.sensor_observations,
        *observation_window.typed_unicode_observations,
    ):
        if observation.coordinate.port_key not in topology_keys:
            raise ReceiptError("raw observation belongs to an unmounted native port")

    base_codes = tuple(
        ReplaySensorCode(value.coordinate, value.raw_code)
        for value in observation_window.sensor_observations
    )
    common = {
        "topology_authority_receipt_sha256": topology.authority_receipt_sha256,
        "base_closed_experience_receipt_sha256": (
            closed_experience_receipt_sha256
        ),
        "observation_window_receipt_sha256": (
            observation_window.authority_receipt_sha256
        ),
        "sensor_resolution_profile_receipt_sha256": (
            sensor_resolution_profile.authority_receipt_sha256
        ),
        "pre_window_state_receipt_sha256": (
            pre_window_state.authority_receipt_sha256
        ),
    }
    requests = [
        _make_replay_request(
            request_id=f"{observation_window.window_id}:global-uf:0",
            request_index=0,
            kind=ReplayKind.BASE,
            target_coordinate=None,
            direction=None,
            physical_delta=Fraction(0),
            sensor_codes=base_codes,
            **common,
        )
    ]
    request_index = 1
    for observation, resolution in zip(
        observation_window.sensor_observations,
        sensor_resolution_profile.resolutions,
        strict=True,
    ):
        for direction in (
            AdjacentDirection.NEGATIVE,
            AdjacentDirection.POSITIVE,
        ):
            adjacent_code = observation.raw_code + direction.value
            if not (
                resolution.minimum_code
                <= adjacent_code
                <= resolution.maximum_code
            ):
                continue
            changed = tuple(
                ReplaySensorCode(
                    value.coordinate,
                    (
                        adjacent_code
                        if value.coordinate == observation.coordinate
                        else value.raw_code
                    ),
                )
                for value in observation_window.sensor_observations
            )
            requests.append(
                _make_replay_request(
                    request_id=(
                        f"{observation_window.window_id}:global-uf:{request_index}"
                    ),
                    request_index=request_index,
                    kind=ReplayKind.ADJACENT_CODE,
                    target_coordinate=observation.coordinate,
                    direction=direction,
                    physical_delta=(
                        Fraction(direction.value) * resolution.physical_quantum
                    ),
                    sensor_codes=changed,
                    **common,
                )
            )
            request_index += 1
    return tuple(requests)


class SignZeroClass(str, Enum):
    NEGATIVE = "negative"
    EXACT_ZERO = "exact_zero"
    POSITIVE = "positive"


def _sign_zero(value: Fraction) -> SignZeroClass:
    require_fraction(value, "semialgebraic source value")
    if value < 0:
        return SignZeroClass.NEGATIVE
    if value > 0:
        return SignZeroClass.POSITIVE
    return SignZeroClass.EXACT_ZERO


@dataclass(frozen=True, slots=True)
class NamedSignZeroClass:
    """Secondary semialgebraic metadata; never an exact field authority."""

    coordinate_id: str
    value_class: SignZeroClass

    def __post_init__(self) -> None:
        require_identifier(self.coordinate_id, "structural coordinate_id")
        if not isinstance(self.value_class, SignZeroClass):
            raise ReceiptError("structural value class must be typed")


@dataclass(frozen=True, slots=True)
class LayerBranchGateSignature:
    layer_index: int
    branch_id: str
    gate_path: tuple[str, ...]
    coordinate_classes: tuple[NamedSignZeroClass, ...]

    def __post_init__(self) -> None:
        _require_integer(self.layer_index, "kernel layer_index")
        if self.layer_index not in range(5):
            raise ReceiptError("kernel layer_index must be one of L0--L4")
        require_identifier(self.branch_id, "kernel branch_id")
        if not isinstance(self.gate_path, tuple):
            raise ReceiptError("kernel gate path must be immutable")
        for gate_id in self.gate_path:
            require_identifier(gate_id, "kernel gate_id")
        if not isinstance(self.coordinate_classes, tuple) or not all(
            isinstance(value, NamedSignZeroClass)
            for value in self.coordinate_classes
        ):
            raise ReceiptError(
                "secondary semialgebraic classes must be typed and immutable"
            )
        ids = tuple(value.coordinate_id for value in self.coordinate_classes)
        if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
            raise ReceiptError(
                "secondary semialgebraic classes are not canonical"
            )


def exact_dsf_field_tuple_receipt_payload(
    *,
    lane_id: str,
    port_id: str,
    tuple_index: int,
    D_k: Fraction,
    M_k: Fraction,
    R_rev_k: Fraction,
    U_star_k: Fraction,
    C_k: Fraction,
    P_k: Fraction,
    B_k: Fraction,
    source_l0_l4_trace_receipt_sha256: str,
) -> bytes:
    require_identifier(lane_id, "exact DSF tuple lane_id")
    require_identifier(port_id, "exact DSF tuple port_id")
    _require_integer(tuple_index, "exact DSF tuple_index")
    if tuple_index < 0:
        raise ReceiptError("exact DSF tuple_index cannot be negative")
    values = {
        "D_k": D_k,
        "M_k": M_k,
        "R_rev_k": R_rev_k,
        "U_star_k": U_star_k,
        "C_k": C_k,
        "P_k": P_k,
        "B_k": B_k,
    }
    for field_name in DSF_FIELD_ORDER:
        require_fraction(values[field_name], field_name)
    sha256_digest(
        source_l0_l4_trace_receipt_sha256,
        "exact DSF tuple source L0-L4 trace receipt",
    )
    return _canonical_bytes(
        {
            "exact_fields": {
                field_name: _fraction_text(values[field_name])
                for field_name in DSF_FIELD_ORDER
            },
            "lane_id": lane_id,
            "port_id": port_id,
            "schema": "glew.global_uf.exact_dsf_field_tuple.v1",
            "source_l0_l4_trace_receipt_sha256": (
                source_l0_l4_trace_receipt_sha256
            ),
            "tuple_index": tuple_index,
        }
    )


@dataclass(frozen=True, slots=True)
class ExactDSFFieldTupleReceipt:
    """Lossless receipt for one complete seven-field L4 tuple."""

    lane_id: str
    port_id: str
    tuple_index: int
    D_k: Fraction
    M_k: Fraction
    R_rev_k: Fraction
    U_star_k: Fraction
    C_k: Fraction
    P_k: Fraction
    B_k: Fraction
    source_l0_l4_trace_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "exact DSF tuple lane_id")
        require_identifier(self.port_id, "exact DSF tuple port_id")
        _require_integer(self.tuple_index, "exact DSF tuple_index")
        if self.tuple_index < 0:
            raise ReceiptError("exact DSF tuple_index cannot be negative")
        for field_name in DSF_FIELD_ORDER:
            require_fraction(getattr(self, field_name), field_name)
        sha256_digest(
            self.source_l0_l4_trace_receipt_sha256,
            "exact DSF tuple source trace receipt",
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "exact DSF tuple authority receipt",
        )

    def as_tuple(self) -> tuple[Fraction, ...]:
        return tuple(getattr(self, field_name) for field_name in DSF_FIELD_ORDER)

    def verify(
        self,
        *,
        expected_lane_id: str,
        expected_port_id: str,
        expected_l0_l4_trace_receipt_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (self.lane_id, self.port_id) != (
            expected_lane_id,
            expected_port_id,
        ):
            raise ReceiptError("exact DSF tuple belongs to another native port")
        if (
            self.source_l0_l4_trace_receipt_sha256
            != expected_l0_l4_trace_receipt_sha256
        ):
            raise ReceiptError("exact DSF tuple belongs to another L0-L4 trace")
        receipt_registry.resolve(
            self.source_l0_l4_trace_receipt_sha256,
            "exact DSF tuple source trace receipt",
        )
        expected = exact_dsf_field_tuple_receipt_payload(
            lane_id=self.lane_id,
            port_id=self.port_id,
            tuple_index=self.tuple_index,
            D_k=self.D_k,
            M_k=self.M_k,
            R_rev_k=self.R_rev_k,
            U_star_k=self.U_star_k,
            C_k=self.C_k,
            P_k=self.P_k,
            B_k=self.B_k,
            source_l0_l4_trace_receipt_sha256=(
                self.source_l0_l4_trace_receipt_sha256
            ),
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "exact DSF seven-field tuple receipt",
        )


def _derived_l4_classes(
    tuples: tuple[ExactDSFFieldTupleReceipt, ...],
) -> tuple[NamedSignZeroClass, ...]:
    values = tuple(
        NamedSignZeroClass(
            f"{item.tuple_index:08d}:{field_name}",
            _sign_zero(getattr(item, field_name)),
        )
        for item in tuples
        for field_name in DSF_FIELD_ORDER
    )
    return tuple(sorted(values, key=lambda value: value.coordinate_id))


def _sign_class_payload(value: NamedSignZeroClass) -> dict[str, object]:
    return {
        "coordinate_id": value.coordinate_id,
        "value_class": value.value_class.value,
    }


def _layer_payload(value: LayerBranchGateSignature) -> dict[str, object]:
    return {
        "branch_id": value.branch_id,
        "gate_path": list(value.gate_path),
        "layer_index": value.layer_index,
        "secondary_semialgebraic_coordinate_classes": [
            _sign_class_payload(item) for item in value.coordinate_classes
        ],
    }


def _exact_tuple_payload(
    value: ExactDSFFieldTupleReceipt,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "exact_fields": {
            field_name: _fraction_text(getattr(value, field_name))
            for field_name in DSF_FIELD_ORDER
        },
        "tuple_index": value.tuple_index,
    }
    if include_authority:
        result.update(
            {
                "authority_receipt_sha256": value.authority_receipt_sha256,
                "lane_id": value.lane_id,
                "port_id": value.port_id,
                "source_l0_l4_trace_receipt_sha256": (
                    value.source_l0_l4_trace_receipt_sha256
                ),
            }
        )
    return result


def port_kernel_basin_receipt_payload(
    *,
    lane_id: str,
    port_id: str,
    layers: tuple[LayerBranchGateSignature, ...],
    exact_dsf_field_tuples: tuple[ExactDSFFieldTupleReceipt, ...],
) -> bytes:
    require_identifier(lane_id, "kernel basin lane_id")
    require_identifier(port_id, "kernel basin port_id")
    if not isinstance(layers, tuple):
        raise ReceiptError("kernel basin layers must be immutable")
    if not isinstance(exact_dsf_field_tuples, tuple):
        raise ReceiptError("exact DSF field tuples must be immutable")
    return _canonical_bytes(
        {
            "exact_dsf_field_tuple_receipt_sha256s": [
                value.authority_receipt_sha256
                for value in exact_dsf_field_tuples
            ],
            "l0_l4_trace_receipt_sha256": (
                exact_dsf_field_tuples[0].source_l0_l4_trace_receipt_sha256
                if exact_dsf_field_tuples
                else None
            ),
            "lane_id": lane_id,
            "layers": [_layer_payload(value) for value in layers],
            "port_id": port_id,
            "schema": "glew.global_uf.port_kernel_basin.v2",
        }
    )


@dataclass(frozen=True, slots=True)
class PortKernelBasinSignature:
    lane_id: str
    port_id: str
    layers: tuple[LayerBranchGateSignature, ...]
    exact_dsf_field_tuples: tuple[ExactDSFFieldTupleReceipt, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "kernel basin lane_id")
        require_identifier(self.port_id, "kernel basin port_id")
        if not isinstance(self.layers, tuple) or not all(
            isinstance(value, LayerBranchGateSignature) for value in self.layers
        ):
            raise ReceiptError("kernel basin layers must be typed and immutable")
        if tuple(value.layer_index for value in self.layers) != tuple(range(5)):
            raise ReceiptError("kernel basin must preserve exactly L0 through L4")
        if not isinstance(self.exact_dsf_field_tuples, tuple) or not all(
            isinstance(value, ExactDSFFieldTupleReceipt)
            for value in self.exact_dsf_field_tuples
        ):
            raise ReceiptError("exact DSF field tuples must be typed and immutable")
        if not self.exact_dsf_field_tuples:
            raise ReceiptError("resolved kernel basin requires exact L4 field tuples")
        if tuple(
            value.tuple_index for value in self.exact_dsf_field_tuples
        ) != tuple(range(len(self.exact_dsf_field_tuples))):
            raise ReceiptError("exact DSF field tuples are not in complete order")
        keys = {
            (value.lane_id, value.port_id)
            for value in self.exact_dsf_field_tuples
        }
        if keys != {(self.lane_id, self.port_id)}:
            raise ReceiptError("exact DSF field tuples cross native port boundaries")
        source_traces = {
            value.source_l0_l4_trace_receipt_sha256
            for value in self.exact_dsf_field_tuples
        }
        if len(source_traces) != 1:
            raise ReceiptError("exact DSF tuples do not share one L0-L4 trace")
        l4 = self.layers[4]
        if l4.coordinate_classes != _derived_l4_classes(
            self.exact_dsf_field_tuples
        ):
            raise ReceiptError(
                "L4 semialgebraic classes are not derived from exact tuples"
            )
        sha256_digest(
            self.authority_receipt_sha256,
            "kernel basin authority receipt",
        )

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)

    def verify(
        self,
        *,
        expected_l0_l4_trace_receipt_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        for value in self.exact_dsf_field_tuples:
            value.verify(
                expected_lane_id=self.lane_id,
                expected_port_id=self.port_id,
                expected_l0_l4_trace_receipt_sha256=(
                    expected_l0_l4_trace_receipt_sha256
                ),
                receipt_registry=receipt_registry,
            )
        expected = port_kernel_basin_receipt_payload(
            lane_id=self.lane_id,
            port_id=self.port_id,
            layers=self.layers,
            exact_dsf_field_tuples=self.exact_dsf_field_tuples,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "port kernel basin authority receipt",
        )


class OperatorAvailability(str, Enum):
    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"


class CertifiedNonnegativeClass(str, Enum):
    EXACT_ZERO = "exact_zero"
    CERTIFIED_POSITIVE = "certified_positive"


@dataclass(frozen=True, slots=True)
class CertifiedOperatorBasinSignature:
    availability: OperatorAvailability
    value_class: CertifiedNonnegativeClass | None
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.availability, OperatorAvailability):
            raise ReceiptError("operator availability must be typed")
        if self.availability is OperatorAvailability.AVAILABLE:
            if not isinstance(self.value_class, CertifiedNonnegativeClass):
                raise ReceiptError("available operator requires a certified class")
        elif self.value_class is not None:
            raise ReceiptError("not-applicable operator cannot carry a value class")
        sha256_digest(
            self.authority_receipt_sha256,
            "certified operator authority receipt",
        )


class L5DispositionState(str, Enum):
    APPLIED = "applied"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class PortL5BasinDisposition:
    lane_id: str
    port_id: str
    state: L5DispositionState
    disposition_id: str | None
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "L5 basin lane_id")
        require_identifier(self.port_id, "L5 basin port_id")
        if not isinstance(self.state, L5DispositionState):
            raise ReceiptError("L5 disposition state must be typed")
        if self.state is L5DispositionState.APPLIED:
            require_identifier(self.disposition_id or "", "L5 disposition_id")
        elif self.disposition_id is not None:
            raise ReceiptError("not-applicable L5 disposition cannot carry an id")
        sha256_digest(self.authority_receipt_sha256, "L5 authority receipt")

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)


@dataclass(frozen=True, slots=True)
class L6BasisRowSignature:
    row_id: str
    row_class: str
    coefficients: tuple[Fraction, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.row_id, "L6 basis row_id")
        require_identifier(self.row_class, "L6 row_class")
        if (
            not isinstance(self.coefficients, tuple)
            or len(self.coefficients) != N_START
        ):
            raise ReceiptError("L6 basis row must preserve all fixed-42 coordinates")
        for value in self.coefficients:
            require_fraction(value, "L6 basis coefficient")
        if not any(value != 0 for value in self.coefficients):
            raise ReceiptError("L6 basis cannot contain an all-zero row")
        sha256_digest(self.authority_receipt_sha256, "L6 row authority receipt")

    @property
    def canonical_key(self) -> tuple[str, str]:
        return (self.row_class, self.row_id)


def _exact_basis_pivots(
    rows: tuple[L6BasisRowSignature, ...],
) -> tuple[int, ...]:
    matrix = [list(row.coefficients) for row in rows]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(N_START):
        selected = next(
            (
                index
                for index in range(pivot_row, len(matrix))
                if matrix[index][column] != 0
            ),
            None,
        )
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]
        for index in range(len(matrix)):
            if index == pivot_row:
                continue
            factor = matrix[index][column]
            if factor:
                matrix[index] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        matrix[index],
                        matrix[pivot_row],
                        strict=True,
                    )
                ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return tuple(pivots)


class L6BasinClass(str, Enum):
    LOCK = "lock"
    NO_LOCK = "no_lock"


@dataclass(frozen=True, slots=True)
class L6BasinSignature:
    row_basis: tuple[L6BasisRowSignature, ...]
    rank: int
    n_effective: int
    pivot_columns: tuple[int, ...]
    basin_class: L6BasinClass
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.row_basis, tuple) or not all(
            isinstance(value, L6BasisRowSignature) for value in self.row_basis
        ):
            raise ReceiptError("L6 row basis must be typed and immutable")
        keys = tuple(value.canonical_key for value in self.row_basis)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ReceiptError("L6 row basis is not canonical")
        _require_integer(self.rank, "L6 exact rank")
        _require_integer(self.n_effective, "L6 n_effective")
        if not isinstance(self.pivot_columns, tuple) or not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in self.pivot_columns
        ):
            raise ReceiptError("L6 pivot columns must be exact integers")
        pivots = _exact_basis_pivots(self.row_basis)
        if self.rank != len(self.row_basis) or self.pivot_columns != pivots:
            raise ReceiptError("L6 row-basis rank or pivots are inconsistent")
        if self.n_effective != N_START - self.rank:
            raise ReceiptError("L6 n_effective differs from the exact row basis")
        if not isinstance(self.basin_class, L6BasinClass):
            raise ReceiptError("L6 basin class must be resolved and typed")
        sha256_digest(self.authority_receipt_sha256, "L6 basin authority receipt")


class StableModeState(str, Enum):
    SELECTED = "selected"
    NO_STABLE_MODE = "no_stable_mode"


@dataclass(frozen=True, slots=True)
class StableModeBasinSignature:
    state: StableModeState
    selected_mode_index: int | None
    selected_mode_receipt_sha256: str | None
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.state, StableModeState):
            raise ReceiptError("stable-mode state must be resolved and typed")
        if self.state is StableModeState.SELECTED:
            _require_integer(self.selected_mode_index, "selected stable-mode index")
            if self.selected_mode_index is None or self.selected_mode_index < 0:
                raise ReceiptError("selected stable-mode index cannot be negative")
            sha256_digest(
                self.selected_mode_receipt_sha256 or "",
                "selected stable-mode receipt",
            )
        elif (
            self.selected_mode_index is not None
            or self.selected_mode_receipt_sha256 is not None
        ):
            raise ReceiptError("no-stable-mode state cannot carry a selected mode")
        sha256_digest(
            self.authority_receipt_sha256,
            "stable-mode authority receipt",
        )


@dataclass(frozen=True, slots=True)
class CommitBasinSignature:
    """The shared commit conjunction with only Global-UF still pending."""

    pending_conjunction: PendingGlobalUFConjunction

    def __post_init__(self) -> None:
        if not isinstance(self.pending_conjunction, PendingGlobalUFConjunction):
            raise ReceiptError("commit basin requires a typed pending conjunction")
        self.pending_conjunction.verify()

    @property
    def authority_receipt_sha256(self) -> str:
        return self.pending_conjunction.receipt_sha256

    def verify(
        self,
        *,
        topology_authority_receipt_sha256: str,
        replay_closed_experience_receipt_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        pending = self.pending_conjunction
        pending.verify()
        if (
            pending.topology_authority_receipt_sha256
            != topology_authority_receipt_sha256
        ):
            raise ReceiptError("pending commit conjunction belongs to another topology")
        if (
            pending.closed_experience_receipt_sha256
            != replay_closed_experience_receipt_sha256
        ):
            raise ReceiptError(
                "pending commit conjunction belongs to another replay experience"
            )
        _mounted_exact(
            receipt_registry,
            pending.receipt_sha256,
            pending.receipt_payload,
            "pending Global-UF conjunction receipt",
        )
        referenced = (
            pending.topology_authority_receipt_sha256,
            pending.closed_experience_receipt_sha256,
            pending.expression_recognition_receipt_sha256,
            pending.pre_growth_expression_bank_receipt_sha256,
            pending.l6_evaluation_receipt_sha256,
            pending.safe_mode_receipt_sha256,
            pending.event_support_receipt_sha256,
            *pending.evidence_receipt_sha256s,
            *pending.applicability_receipt_sha256s,
        )
        if pending.selected_mode_receipt_sha256 is not None:
            referenced = (*referenced, pending.selected_mode_receipt_sha256)
        for digest in referenced:
            receipt_registry.resolve(
                digest,
                "pending Global-UF conjunction source receipt",
            )


def _operator_payload(
    value: CertifiedOperatorBasinSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "availability": value.availability.value,
        "value_class": (
            None if value.value_class is None else value.value_class.value
        ),
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
    return result


def _l5_payload(
    value: PortL5BasinDisposition,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "disposition_id": value.disposition_id,
        "lane_id": value.lane_id,
        "port_id": value.port_id,
        "state": value.state.value,
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
    return result


def _l6_row_payload(
    value: L6BasisRowSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "coefficients": [_fraction_text(item) for item in value.coefficients],
        "row_class": value.row_class,
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
        result["row_id"] = value.row_id
    return result


def _l6_payload(
    value: L6BasinSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "basin_class": value.basin_class.value,
        "n_effective": value.n_effective,
        "pivot_columns": list(value.pivot_columns),
        "rank": value.rank,
        "row_basis": [
            _l6_row_payload(item, include_authority=include_authority)
            for item in value.row_basis
        ],
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
    return result


def _stable_mode_payload(
    value: StableModeBasinSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "selected_mode_index": value.selected_mode_index,
        "selected_mode_receipt_sha256": value.selected_mode_receipt_sha256,
        "state": value.state.value,
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
    return result


def _commit_payload(
    value: CommitBasinSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    pending = value.pending_conjunction
    result: dict[str, object] = {
        "findings": list(pending.findings),
        "selected_mode_index": pending.selected_mode_index,
        "selected_mode_receipt_sha256": (
            pending.selected_mode_receipt_sha256
        ),
        "status": pending.status.value,
    }
    if include_authority:
        result["pending_conjunction_receipt_sha256"] = pending.receipt_sha256
    return result


def _port_kernel_payload(
    value: PortKernelBasinSignature,
    *,
    include_authority: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "exact_dsf_field_tuples": [
            _exact_tuple_payload(item, include_authority=include_authority)
            for item in value.exact_dsf_field_tuples
        ],
        "lane_id": value.lane_id,
        "layers": [_layer_payload(item) for item in value.layers],
        "port_id": value.port_id,
    }
    if include_authority:
        result["authority_receipt_sha256"] = value.authority_receipt_sha256
    return result


@dataclass(frozen=True, slots=True)
class StructuralBasinSignature:
    port_kernel_basins: tuple[PortKernelBasinSignature, ...]
    s_uf: CertifiedOperatorBasinSignature
    r_uf: CertifiedOperatorBasinSignature
    l5_dispositions: tuple[PortL5BasinDisposition, ...]
    l6: L6BasinSignature
    stable_mode: StableModeBasinSignature
    commit: CommitBasinSignature

    def __post_init__(self) -> None:
        if not isinstance(self.port_kernel_basins, tuple) or not all(
            isinstance(value, PortKernelBasinSignature)
            for value in self.port_kernel_basins
        ):
            raise ReceiptError("kernel basins must be typed and immutable")
        if not isinstance(self.s_uf, CertifiedOperatorBasinSignature):
            raise ReceiptError("S_UF basin signature is not typed")
        if not isinstance(self.r_uf, CertifiedOperatorBasinSignature):
            raise ReceiptError("R_UF basin signature is not typed")
        if not isinstance(self.l5_dispositions, tuple) or not all(
            isinstance(value, PortL5BasinDisposition)
            for value in self.l5_dispositions
        ):
            raise ReceiptError("L5 dispositions must be typed and immutable")
        if not isinstance(self.l6, L6BasinSignature):
            raise ReceiptError("L6 basin signature is not typed")
        if not isinstance(self.stable_mode, StableModeBasinSignature):
            raise ReceiptError("stable-mode basin signature is not typed")
        if not isinstance(self.commit, CommitBasinSignature):
            raise ReceiptError("commit basin signature is not typed")

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        replay_closed_experience_receipt_sha256: str,
        port_replay_receipts: tuple["PortReplayReceipt", ...],
        receipt_registry: ReceiptRegistry,
    ) -> None:
        expected_keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
        if tuple(value.key for value in self.port_kernel_basins) != expected_keys:
            raise ReceiptError("kernel basin does not preserve mounted port order")
        if tuple(value.key for value in self.l5_dispositions) != expected_keys:
            raise ReceiptError("L5 basin does not preserve mounted port order")
        replay_by_key = {value.key: value for value in port_replay_receipts}
        if tuple(replay_by_key) != expected_keys:
            raise ReceiptError("port replay map does not preserve mounted order")
        for value in self.port_kernel_basins:
            value.verify(
                expected_l0_l4_trace_receipt_sha256=(
                    replay_by_key[value.key].l0_l4_trace_receipt_sha256
                ),
                receipt_registry=receipt_registry,
            )
        source_digests = (
            self.s_uf.authority_receipt_sha256,
            self.r_uf.authority_receipt_sha256,
            *(value.authority_receipt_sha256 for value in self.l5_dispositions),
            *(value.authority_receipt_sha256 for value in self.l6.row_basis),
            self.l6.authority_receipt_sha256,
            self.stable_mode.authority_receipt_sha256,
        )
        if self.stable_mode.selected_mode_receipt_sha256 is not None:
            source_digests = (
                *source_digests,
                self.stable_mode.selected_mode_receipt_sha256,
            )
        for digest in source_digests:
            receipt_registry.resolve(digest, "structural basin source receipt")
        self.commit.verify(
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            replay_closed_experience_receipt_sha256=(
                replay_closed_experience_receipt_sha256
            ),
            receipt_registry=receipt_registry,
        )
        pending = self.commit.pending_conjunction
        if pending.status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF:
            if (
                self.stable_mode.state is not StableModeState.SELECTED
                or self.stable_mode.selected_mode_index
                != pending.selected_mode_index
                or self.stable_mode.selected_mode_receipt_sha256
                != pending.selected_mode_receipt_sha256
            ):
                raise ReceiptError(
                    "stable-mode basin differs from pending commit conjunction"
                )

    def structural_payload(self) -> bytes:
        """Exact basin values with replay-specific receipt provenance omitted."""

        return _canonical_bytes(
            {
                "commit": _commit_payload(self.commit, include_authority=False),
                "l5_dispositions": [
                    _l5_payload(value, include_authority=False)
                    for value in self.l5_dispositions
                ],
                "l6": _l6_payload(self.l6, include_authority=False),
                "port_kernel_basins": [
                    _port_kernel_payload(value, include_authority=False)
                    for value in self.port_kernel_basins
                ],
                "r_uf": _operator_payload(self.r_uf, include_authority=False),
                "s_uf": _operator_payload(self.s_uf, include_authority=False),
                "schema": "glew.global_uf.exact_structural_basin.v2",
                "stable_mode": _stable_mode_payload(
                    self.stable_mode,
                    include_authority=False,
                ),
            }
        )


def _basin_payload(value: StructuralBasinSignature) -> dict[str, object]:
    return {
        "commit": _commit_payload(value.commit, include_authority=True),
        "l5_dispositions": [
            _l5_payload(item, include_authority=True)
            for item in value.l5_dispositions
        ],
        "l6": _l6_payload(value.l6, include_authority=True),
        "port_kernel_basins": [
            _port_kernel_payload(item, include_authority=True)
            for item in value.port_kernel_basins
        ],
        "r_uf": _operator_payload(value.r_uf, include_authority=True),
        "s_uf": _operator_payload(value.s_uf, include_authority=True),
        "stable_mode": _stable_mode_payload(
            value.stable_mode,
            include_authority=True,
        ),
    }


def port_replay_receipt_payload(
    *,
    lane_id: str,
    port_id: str,
    request_receipt_sha256: str,
    source_observation_receipt_sha256: str,
    l0_l4_trace_receipt_sha256: str,
    l5_governance_receipt_sha256: str,
) -> bytes:
    require_identifier(lane_id, "replay port lane_id")
    require_identifier(port_id, "replay port port_id")
    for digest, field_name in (
        (request_receipt_sha256, "replay port request receipt"),
        (source_observation_receipt_sha256, "replay port observation receipt"),
        (l0_l4_trace_receipt_sha256, "replay port L0-L4 trace receipt"),
        (l5_governance_receipt_sha256, "replay port L5 receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "l0_l4_trace_receipt_sha256": l0_l4_trace_receipt_sha256,
            "l5_governance_receipt_sha256": l5_governance_receipt_sha256,
            "lane_id": lane_id,
            "port_id": port_id,
            "request_receipt_sha256": request_receipt_sha256,
            "schema": "glew.global_uf.port_replay.v2",
            "source_observation_receipt_sha256": (
                source_observation_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class PortReplayReceipt:
    lane_id: str
    port_id: str
    request_receipt_sha256: str
    source_observation_receipt_sha256: str
    l0_l4_trace_receipt_sha256: str
    l5_governance_receipt_sha256: str
    receipt_sha256: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)

    def verify(
        self,
        *,
        expected_request_receipt_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.request_receipt_sha256 != expected_request_receipt_sha256:
            raise ReceiptError("port replay belongs to another replay request")
        for digest, field_name in (
            (self.source_observation_receipt_sha256, "port observation receipt"),
            (self.l0_l4_trace_receipt_sha256, "port L0-L4 trace receipt"),
            (self.l5_governance_receipt_sha256, "port L5 receipt"),
        ):
            receipt_registry.resolve(digest, field_name)
        expected = port_replay_receipt_payload(
            lane_id=self.lane_id,
            port_id=self.port_id,
            request_receipt_sha256=self.request_receipt_sha256,
            source_observation_receipt_sha256=(
                self.source_observation_receipt_sha256
            ),
            l0_l4_trace_receipt_sha256=self.l0_l4_trace_receipt_sha256,
            l5_governance_receipt_sha256=self.l5_governance_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            expected,
            "port replay receipt",
        )


class ReplayOutcomeStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


def global_uf_replay_outcome_receipt_payload(
    *,
    outcome_id: str,
    status: ReplayOutcomeStatus,
    reason: str | None,
    request_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    base_closed_experience_receipt_sha256: str,
    replay_closed_experience_receipt_sha256: str | None,
    observation_window_receipt_sha256: str,
    sensor_resolution_profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    port_replay_receipts: tuple[PortReplayReceipt, ...],
    basin_signature: StructuralBasinSignature | None,
) -> bytes:
    require_identifier(outcome_id, "Global-UF replay outcome_id")
    if not isinstance(status, ReplayOutcomeStatus):
        raise ReceiptError("Global-UF replay outcome status must be typed")
    if status is ReplayOutcomeStatus.RESOLVED:
        if (
            reason is not None
            or not isinstance(basin_signature, StructuralBasinSignature)
            or replay_closed_experience_receipt_sha256 is None
        ):
            raise ReceiptError(
                "resolved replay requires one scoped experience and complete basin"
            )
    else:
        require_identifier(reason or "", "unresolved replay reason")
        if basin_signature is not None:
            raise ReceiptError("unresolved replay cannot carry a nominal basin")
    for digest, field_name in (
        (request_receipt_sha256, "outcome request receipt"),
        (topology_authority_receipt_sha256, "outcome topology receipt"),
        (base_closed_experience_receipt_sha256, "outcome base experience receipt"),
        (observation_window_receipt_sha256, "outcome observation receipt"),
        (
            sensor_resolution_profile_receipt_sha256,
            "outcome sensor-resolution receipt",
        ),
        (pre_window_state_receipt_sha256, "outcome pre-window state receipt"),
    ):
        sha256_digest(digest, field_name)
    if replay_closed_experience_receipt_sha256 is not None:
        sha256_digest(
            replay_closed_experience_receipt_sha256,
            "outcome replay-scoped experience receipt",
        )
    if not isinstance(port_replay_receipts, tuple):
        raise ReceiptError("outcome port receipts must be immutable")
    return _canonical_bytes(
        {
            "base_closed_experience_receipt_sha256": (
                base_closed_experience_receipt_sha256
            ),
            "basin_signature": (
                None if basin_signature is None else _basin_payload(basin_signature)
            ),
            "observation_window_receipt_sha256": (
                observation_window_receipt_sha256
            ),
            "outcome_id": outcome_id,
            "port_replay_receipt_sha256s": [
                value.receipt_sha256 for value in port_replay_receipts
            ],
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "reason": reason,
            "replay_closed_experience_receipt_sha256": (
                replay_closed_experience_receipt_sha256
            ),
            "request_receipt_sha256": request_receipt_sha256,
            "schema": "glew.global_uf.replay_outcome.v2",
            "sensor_resolution_profile_receipt_sha256": (
                sensor_resolution_profile_receipt_sha256
            ),
            "status": status.value,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class GlobalUFReplayOutcome:
    outcome_id: str
    status: ReplayOutcomeStatus
    reason: str | None
    request_receipt_sha256: str
    topology_authority_receipt_sha256: str
    base_closed_experience_receipt_sha256: str
    replay_closed_experience_receipt_sha256: str | None
    observation_window_receipt_sha256: str
    sensor_resolution_profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    port_replay_receipts: tuple[PortReplayReceipt, ...]
    basin_signature: StructuralBasinSignature | None
    receipt_sha256: str

    def verify(
        self,
        *,
        request: GlobalUFReplayRequest,
        topology: MountedFieldTopology,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        expected_bindings = (
            (self.request_receipt_sha256, request.receipt_sha256, "replay request"),
            (
                self.topology_authority_receipt_sha256,
                request.topology_authority_receipt_sha256,
                "topology",
            ),
            (
                self.base_closed_experience_receipt_sha256,
                request.base_closed_experience_receipt_sha256,
                "base closed experience",
            ),
            (
                self.observation_window_receipt_sha256,
                request.observation_window_receipt_sha256,
                "observation window",
            ),
            (
                self.sensor_resolution_profile_receipt_sha256,
                request.sensor_resolution_profile_receipt_sha256,
                "sensor-resolution profile",
            ),
            (
                self.pre_window_state_receipt_sha256,
                request.pre_window_state_receipt_sha256,
                "immutable pre-window state",
            ),
        )
        for actual, expected, name in expected_bindings:
            if actual != expected:
                raise ReceiptError(f"replay outcome belongs to another {name}")
        receipt_registry.resolve(
            self.base_closed_experience_receipt_sha256,
            "outcome base closed-experience receipt",
        )
        if self.replay_closed_experience_receipt_sha256 is not None:
            receipt_registry.resolve(
                self.replay_closed_experience_receipt_sha256,
                "outcome replay-scoped closed-experience receipt",
            )
        if not isinstance(self.port_replay_receipts, tuple) or not all(
            isinstance(value, PortReplayReceipt)
            for value in self.port_replay_receipts
        ):
            raise ReceiptError("replay outcome port receipts are not typed")
        topology_keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
        outcome_keys = tuple(value.key for value in self.port_replay_receipts)
        if self.status is ReplayOutcomeStatus.RESOLVED:
            if outcome_keys != topology_keys:
                raise ReceiptError("resolved replay does not preserve every native port")
        else:
            if len(set(outcome_keys)) != len(outcome_keys):
                raise ReceiptError("unresolved replay repeats a native port")
            expected_subset = tuple(
                key for key in topology_keys if key in set(outcome_keys)
            )
            if outcome_keys != expected_subset:
                raise ReceiptError("unresolved replay ports are not in topology order")
        for value in self.port_replay_receipts:
            value.verify(
                expected_request_receipt_sha256=request.receipt_sha256,
                receipt_registry=receipt_registry,
            )
        if self.status is ReplayOutcomeStatus.RESOLVED:
            if (
                self.reason is not None
                or self.basin_signature is None
                or self.replay_closed_experience_receipt_sha256 is None
            ):
                raise ReceiptError("resolved replay lacks a complete scoped basin")
            self.basin_signature.verify(
                topology=topology,
                replay_closed_experience_receipt_sha256=(
                    self.replay_closed_experience_receipt_sha256
                ),
                port_replay_receipts=self.port_replay_receipts,
                receipt_registry=receipt_registry,
            )
        else:
            require_identifier(self.reason or "", "unresolved replay reason")
            if self.basin_signature is not None:
                raise ReceiptError("unresolved replay carries a nominal basin")
        expected = global_uf_replay_outcome_receipt_payload(
            outcome_id=self.outcome_id,
            status=self.status,
            reason=self.reason,
            request_receipt_sha256=self.request_receipt_sha256,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            base_closed_experience_receipt_sha256=(
                self.base_closed_experience_receipt_sha256
            ),
            replay_closed_experience_receipt_sha256=(
                self.replay_closed_experience_receipt_sha256
            ),
            observation_window_receipt_sha256=(
                self.observation_window_receipt_sha256
            ),
            sensor_resolution_profile_receipt_sha256=(
                self.sensor_resolution_profile_receipt_sha256
            ),
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            port_replay_receipts=self.port_replay_receipts,
            basin_signature=self.basin_signature,
        )
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            expected,
            "Global-UF replay outcome receipt",
        )


@dataclass(frozen=True, slots=True)
class GlobalUFReplayResponse:
    """One provider outcome plus every newly mounted immutable receipt."""

    outcome: GlobalUFReplayOutcome
    receipt_records: tuple[ReceiptRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, GlobalUFReplayOutcome):
            raise ReceiptError("Global-UF response lacks a typed replay outcome")
        if not isinstance(self.receipt_records, tuple) or not all(
            isinstance(value, ReceiptRecord) for value in self.receipt_records
        ):
            raise ReceiptError(
                "Global-UF response receipts must be typed and immutable"
            )
        digests = tuple(value.digest for value in self.receipt_records)
        if len(set(digests)) != len(digests):
            raise ReceiptError("Global-UF response repeats a receipt digest")


@runtime_checkable
class GlobalUFReplayProvider(Protocol):
    """Live executor boundary; validation never fabricates replay outcomes."""

    def replay_from_immutable_pre_window(
        self,
        request: GlobalUFReplayRequest,
    ) -> GlobalUFReplayResponse | None:
        """Execute exactly one receipted request, or return explicit missing."""


class ReplayEvidenceState(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    MISSING = "missing"
    INVALID = "invalid"


class ReplayComparisonState(str, Enum):
    BASELINE = "baseline"
    EXACT_MATCH = "exact_match"
    COUNTEREXAMPLE = "counterexample"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class GlobalUFSourceReplayEntry:
    request_index: int
    request_receipt_sha256: str
    kind: ReplayKind
    target_coordinate: ObservationCoordinate | None
    direction: AdjacentDirection | None
    evidence_state: ReplayEvidenceState
    comparison_state: ReplayComparisonState
    outcome_receipt_sha256: str | None
    replay_closed_experience_receipt_sha256: str | None
    structural_basin_receipt_sha256: str | None
    port_replay_receipt_sha256s: tuple[str, ...]
    reason: str | None

    def __post_init__(self) -> None:
        _require_integer(self.request_index, "source replay request_index")
        sha256_digest(self.request_receipt_sha256, "source replay request receipt")
        if not isinstance(self.kind, ReplayKind):
            raise ReceiptError("source replay kind must be typed")
        if not isinstance(self.evidence_state, ReplayEvidenceState):
            raise ReceiptError("source replay evidence state must be typed")
        if not isinstance(self.comparison_state, ReplayComparisonState):
            raise ReceiptError("source replay comparison state must be typed")
        for digest, field_name in (
            (self.outcome_receipt_sha256, "source outcome receipt"),
            (
                self.replay_closed_experience_receipt_sha256,
                "source replay experience receipt",
            ),
            (
                self.structural_basin_receipt_sha256,
                "source structural-basin receipt",
            ),
        ):
            if digest is not None:
                sha256_digest(digest, field_name)
        if not isinstance(self.port_replay_receipt_sha256s, tuple):
            raise ReceiptError("source port replay receipts must be immutable")
        for digest in self.port_replay_receipt_sha256s:
            sha256_digest(digest, "source port replay receipt")
        if self.evidence_state is ReplayEvidenceState.RESOLVED:
            if (
                self.outcome_receipt_sha256 is None
                or self.replay_closed_experience_receipt_sha256 is None
                or self.structural_basin_receipt_sha256 is None
                or self.reason is not None
            ):
                raise ReceiptError("resolved source replay lacks complete receipts")
        else:
            require_identifier(self.reason or "", "non-resolved replay reason")


def _source_entry_payload(value: GlobalUFSourceReplayEntry) -> dict[str, object]:
    return {
        "comparison_state": value.comparison_state.value,
        "direction": None if value.direction is None else value.direction.value,
        "evidence_state": value.evidence_state.value,
        "kind": value.kind.value,
        "outcome_receipt_sha256": value.outcome_receipt_sha256,
        "port_replay_receipt_sha256s": list(
            value.port_replay_receipt_sha256s
        ),
        "reason": value.reason,
        "replay_closed_experience_receipt_sha256": (
            value.replay_closed_experience_receipt_sha256
        ),
        "request_index": value.request_index,
        "request_receipt_sha256": value.request_receipt_sha256,
        "structural_basin_receipt_sha256": (
            value.structural_basin_receipt_sha256
        ),
        "target_coordinate": (
            None
            if value.target_coordinate is None
            else _coordinate_payload(value.target_coordinate)
        ),
    }


def global_uf_source_receipt_payload(
    *,
    authority_id: str,
    disposition: AuthorityDisposition,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    observation_window_receipt_sha256: str,
    sensor_resolution_profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    expected_replay_count: int,
    entries: tuple[GlobalUFSourceReplayEntry, ...],
) -> bytes:
    require_identifier(authority_id, "Global-UF authority_id")
    if not isinstance(disposition, AuthorityDisposition):
        raise ReceiptError("Global-UF source disposition must be typed")
    _require_integer(expected_replay_count, "Global-UF expected replay count")
    if not isinstance(entries, tuple):
        raise ReceiptError("Global-UF source entries must be immutable")
    for digest, field_name in (
        (topology_authority_receipt_sha256, "Global-UF source topology receipt"),
        (closed_experience_receipt_sha256, "Global-UF source base experience"),
        (observation_window_receipt_sha256, "Global-UF source observation"),
        (
            sensor_resolution_profile_receipt_sha256,
            "Global-UF source sensor-resolution",
        ),
        (pre_window_state_receipt_sha256, "Global-UF source state receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "base_closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "disposition": disposition.value,
            "entries": [_source_entry_payload(value) for value in entries],
            "expected_replay_count": expected_replay_count,
            "observation_window_receipt_sha256": (
                observation_window_receipt_sha256
            ),
            "operator": GLOBAL_UF_OPERATOR_ID,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "schema": "glew.global_uf.validation_source.v2",
            "sensor_resolution_profile_receipt_sha256": (
                sensor_resolution_profile_receipt_sha256
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class GlobalUFSourceReceipt:
    authority_id: str
    disposition: AuthorityDisposition
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    observation_window_receipt_sha256: str
    sensor_resolution_profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    expected_replay_count: int
    entries: tuple[GlobalUFSourceReplayEntry, ...]
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.expected_replay_count != len(self.entries):
            raise ReceiptError("Global-UF source receipt is incomplete")
        if tuple(value.request_index for value in self.entries) != tuple(
            range(self.expected_replay_count)
        ):
            raise ReceiptError("Global-UF source entries are not in request order")
        expected = global_uf_source_receipt_payload(
            authority_id=self.authority_id,
            disposition=self.disposition,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            observation_window_receipt_sha256=(
                self.observation_window_receipt_sha256
            ),
            sensor_resolution_profile_receipt_sha256=(
                self.sensor_resolution_profile_receipt_sha256
            ),
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            expected_replay_count=self.expected_replay_count,
            entries=self.entries,
        )
        if self.receipt_payload != expected:
            raise ReceiptError("Global-UF source fields differ from receipt payload")
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            expected,
            "Global-UF detailed source receipt",
        )
        for entry in self.entries:
            receipt_registry.resolve(
                entry.request_receipt_sha256,
                "Global-UF replay request receipt",
            )
            for digest, field_name in (
                (entry.outcome_receipt_sha256, "Global-UF replay outcome receipt"),
                (
                    entry.replay_closed_experience_receipt_sha256,
                    "Global-UF replay-scoped experience receipt",
                ),
                (
                    entry.structural_basin_receipt_sha256,
                    "Global-UF structural basin receipt",
                ),
            ):
                if digest is not None:
                    receipt_registry.resolve(digest, field_name)
            for digest in entry.port_replay_receipt_sha256s:
                receipt_registry.resolve(digest, "Global-UF port replay receipt")


@dataclass(frozen=True, slots=True)
class GlobalUFValidationResult:
    authority: BinaryCommitAuthority
    source_receipt: GlobalUFSourceReceipt
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        if self.authority.kind is not BinaryAuthorityKind.GLOBAL_UF_VALIDATION:
            raise ReceiptError("Global-UF result carries the wrong binary authority")
        if self.authority.disposition is not self.source_receipt.disposition:
            raise ReceiptError("Global-UF authority and source dispositions differ")
        if (
            self.authority.source_operator_receipt_sha256
            != self.source_receipt.receipt_sha256
        ):
            raise ReceiptError("Global-UF authority does not bind its detailed source")
        self.source_receipt.verify(self.receipt_registry)
        self.authority.verify(
            expected_kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
            topology_receipt=(
                self.source_receipt.topology_authority_receipt_sha256
            ),
            experience_receipt=(
                self.source_receipt.closed_experience_receipt_sha256
            ),
            receipt_registry=self.receipt_registry,
        )


def _source_entry(
    *,
    request: GlobalUFReplayRequest,
    evidence_state: ReplayEvidenceState,
    comparison_state: ReplayComparisonState,
    outcome: GlobalUFReplayOutcome | None,
    structural_basin_receipt_sha256: str | None,
    reason: str | None,
) -> GlobalUFSourceReplayEntry:
    return GlobalUFSourceReplayEntry(
        request_index=request.request_index,
        request_receipt_sha256=request.receipt_sha256,
        kind=request.kind,
        target_coordinate=request.target_coordinate,
        direction=request.direction,
        evidence_state=evidence_state,
        comparison_state=comparison_state,
        outcome_receipt_sha256=(
            None if outcome is None else outcome.receipt_sha256
        ),
        replay_closed_experience_receipt_sha256=(
            None
            if outcome is None
            else outcome.replay_closed_experience_receipt_sha256
        ),
        structural_basin_receipt_sha256=structural_basin_receipt_sha256,
        port_replay_receipt_sha256s=(
            ()
            if outcome is None
            else tuple(
                value.receipt_sha256 for value in outcome.port_replay_receipts
            )
        ),
        reason=reason,
    )


def evaluate_global_uf_validation(
    *,
    authority_id: str,
    topology: MountedFieldTopology,
    closed_experience_receipt_sha256: str,
    observation_window: MountedRawObservationWindow,
    sensor_resolution_profile: MountedSensorResolutionProfile,
    pre_window_state: MountedPreWindowState,
    replay_provider: GlobalUFReplayProvider,
    receipt_registry: ReceiptRegistry,
) -> GlobalUFValidationResult:
    """Produce one exact, fail-closed Global-UF binary authority."""

    require_identifier(authority_id, "Global-UF authority_id")
    if not isinstance(replay_provider, GlobalUFReplayProvider):
        raise ReceiptError("Global-UF requires a concrete replay provider")
    requests = enumerate_global_uf_replay_requests(
        topology=topology,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        observation_window=observation_window,
        sensor_resolution_profile=sensor_resolution_profile,
        pre_window_state=pre_window_state,
        receipt_registry=receipt_registry,
    )
    working_registry = _extend_with_payloads(
        receipt_registry,
        (value.receipt_payload for value in requests),
    )
    entries: list[GlobalUFSourceReplayEntry] = []
    base_structural_payload: bytes | None = None
    has_counterexample = False
    has_unresolved = False

    for request in requests:
        response = replay_provider.replay_from_immutable_pre_window(request)
        if response is None:
            has_unresolved = True
            entries.append(
                _source_entry(
                    request=request,
                    evidence_state=ReplayEvidenceState.MISSING,
                    comparison_state=ReplayComparisonState.UNAVAILABLE,
                    outcome=None,
                    structural_basin_receipt_sha256=None,
                    reason="provider-returned-no-replay",
                )
            )
            continue
        try:
            if not isinstance(response, GlobalUFReplayResponse):
                raise ReceiptError("provider response is not typed")
            candidate_registry = _extend_with_records(
                working_registry,
                response.receipt_records,
            )
            response.outcome.verify(
                request=request,
                topology=topology,
                receipt_registry=candidate_registry,
            )
        except ReceiptError:
            has_unresolved = True
            entries.append(
                _source_entry(
                    request=request,
                    evidence_state=ReplayEvidenceState.INVALID,
                    comparison_state=ReplayComparisonState.UNAVAILABLE,
                    outcome=None,
                    structural_basin_receipt_sha256=None,
                    reason="invalid-replay-receipt-or-binding",
                )
            )
            continue

        working_registry = candidate_registry
        outcome = response.outcome
        if outcome.status is ReplayOutcomeStatus.UNRESOLVED:
            has_unresolved = True
            entries.append(
                _source_entry(
                    request=request,
                    evidence_state=ReplayEvidenceState.UNRESOLVED,
                    comparison_state=ReplayComparisonState.UNAVAILABLE,
                    outcome=outcome,
                    structural_basin_receipt_sha256=None,
                    reason=outcome.reason,
                )
            )
            continue

        if outcome.basin_signature is None:
            raise ReceiptError("verified resolved replay unexpectedly lacks a basin")
        structural_payload = outcome.basin_signature.structural_payload()
        working_registry = _extend_with_payloads(
            working_registry,
            (structural_payload,),
        )
        structural_digest = receipt_sha256(structural_payload)
        if request.kind is ReplayKind.BASE:
            base_structural_payload = structural_payload
            comparison = ReplayComparisonState.BASELINE
        elif base_structural_payload is None:
            has_unresolved = True
            comparison = ReplayComparisonState.UNAVAILABLE
        elif structural_payload == base_structural_payload:
            comparison = ReplayComparisonState.EXACT_MATCH
        else:
            comparison = ReplayComparisonState.COUNTEREXAMPLE
            has_counterexample = True
        entries.append(
            _source_entry(
                request=request,
                evidence_state=ReplayEvidenceState.RESOLVED,
                comparison_state=comparison,
                outcome=outcome,
                structural_basin_receipt_sha256=structural_digest,
                reason=None,
            )
        )

    if has_counterexample:
        disposition = AuthorityDisposition.FAIL
    elif has_unresolved or base_structural_payload is None:
        disposition = AuthorityDisposition.UNKNOWN
    else:
        disposition = AuthorityDisposition.PASS

    source_payload = global_uf_source_receipt_payload(
        authority_id=authority_id,
        disposition=disposition,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        observation_window_receipt_sha256=(
            observation_window.authority_receipt_sha256
        ),
        sensor_resolution_profile_receipt_sha256=(
            sensor_resolution_profile.authority_receipt_sha256
        ),
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        expected_replay_count=len(requests),
        entries=tuple(entries),
    )
    source = GlobalUFSourceReceipt(
        authority_id=authority_id,
        disposition=disposition,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        observation_window_receipt_sha256=(
            observation_window.authority_receipt_sha256
        ),
        sensor_resolution_profile_receipt_sha256=(
            sensor_resolution_profile.authority_receipt_sha256
        ),
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        expected_replay_count=len(requests),
        entries=tuple(entries),
        receipt_sha256=receipt_sha256(source_payload),
        receipt_payload=source_payload,
    )
    authority_payload = binary_authority_receipt_payload(
        authority_id=authority_id,
        kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        disposition=disposition,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        source_operator_receipt_sha256=source.receipt_sha256,
    )
    authority = BinaryCommitAuthority(
        authority_id=authority_id,
        kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        disposition=disposition,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        source_operator_receipt_sha256=source.receipt_sha256,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    final_registry = _extend_with_payloads(
        working_registry,
        (source_payload, authority_payload),
    )
    result = GlobalUFValidationResult(authority, source, final_registry)
    result.verify()
    return result


__all__ = [
    "AdjacentDirection",
    "CertifiedNonnegativeClass",
    "CertifiedOperatorBasinSignature",
    "CommitBasinSignature",
    "DSF_FIELD_ORDER",
    "ExactDSFFieldTupleReceipt",
    "GLOBAL_UF_OPERATOR_ID",
    "GlobalUFReplayOutcome",
    "GlobalUFReplayProvider",
    "GlobalUFReplayRequest",
    "GlobalUFReplayResponse",
    "GlobalUFSourceReceipt",
    "GlobalUFSourceReplayEntry",
    "GlobalUFValidationResult",
    "L5DispositionState",
    "L6BasinClass",
    "L6BasinSignature",
    "L6BasisRowSignature",
    "LayerBranchGateSignature",
    "MountedPreWindowState",
    "MountedRawObservationWindow",
    "MountedSensorResolutionProfile",
    "NamedSignZeroClass",
    "ObservationCoordinate",
    "OperatorAvailability",
    "PortKernelBasinSignature",
    "PortL5BasinDisposition",
    "PortReplayReceipt",
    "ReplayComparisonState",
    "ReplayEvidenceState",
    "ReplayKind",
    "ReplayOutcomeStatus",
    "ReplaySensorCode",
    "SensorCodeResolution",
    "SensorIntegerObservation",
    "SignZeroClass",
    "StableModeBasinSignature",
    "StableModeState",
    "StructuralBasinSignature",
    "TypedUnicodeObservation",
    "enumerate_global_uf_replay_requests",
    "evaluate_global_uf_validation",
    "exact_dsf_field_tuple_receipt_payload",
    "global_uf_replay_outcome_receipt_payload",
    "global_uf_replay_request_receipt_payload",
    "global_uf_source_receipt_payload",
    "port_kernel_basin_receipt_payload",
    "port_replay_receipt_payload",
    "pre_window_state_receipt_payload",
    "raw_observation_window_receipt_payload",
    "sensor_resolution_profile_receipt_payload",
]
