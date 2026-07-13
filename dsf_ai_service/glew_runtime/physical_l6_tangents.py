"""Exact physical-response producer for fixed-42 L6 constraints.

The generic L6 row producer accepts exact seven-by-native-response tangents.
This module supplies those tangents from independently receipted native replay
responses.  Every replay begins from one immutable pre-window chemistry,
field, mode, memory, and L6 state.  Non-language ports use exhaustive adjacent
integer sensor codes with a mounted physical quantum.  The language lane uses
only exact typed ternary perturbations; it is never treated as a sensor code.

For each directed adjacent replay the producer forms the exact finite secant

    (L4_perturbed - L4_base) / native_delta

in the canonical seven-field lane basis.  Opposite directions remain separate
columns, preserving nonlinear response geometry.  A mounted upstream proof
must bind every response to the same L0--L4 branch and cell.  The derived
tangent, upstream source receipts, translated candidate receipts, emitted rows,
and per-lane completeness receipts remain mounted as one auditable result.

There is no desired-rank construction, observed-value row, tolerance, numeric
threshold, score, random sample, or hash-derived physics.  Missing response,
state binding, or branch proof returns typed UNKNOWN and releases no partial
constraint stack.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, IntEnum
from fractions import Fraction
from typing import Iterable, Sequence

from .global_uf import MountedPreWindowState
from .l6 import (
    CANDIDATE_BRANCH_CELL_RECEIPT_FIELD,
    CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD,
    COMPLETENESS_RECEIPT_FIELD,
    FIELD_ORDER,
    LANE_ORDER,
    CandidateConstraintProduction,
    CandidateConstraintProductionStatus,
    CandidateProviderTangentClaim,
    ExactRankReceipt,
    L6Lane,
    canonical_candidate_branch_cell_receipt_payload,
    canonical_candidate_local_tangent_receipt_payload,
    canonical_completeness_receipt_payload,
    exact_rank_receipt,
    produce_candidate_fixed42_constraints,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


PHYSICAL_TANGENT_OPERATOR_ID = "glew.l6.exact_native_replay_secants.v1"


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


def _extend_records(
    registry: ReceiptRegistry,
    records: Iterable[ReceiptRecord],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("physical L6 producer requires a receipt registry")
    mounted = {record.digest: record.payload for record in registry.records}
    additions: dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("physical L6 producer received a non-receipt record")
        prior = mounted.get(record.digest)
        if prior is not None and prior != record.payload:
            raise ReceiptError("receipt digest collision at physical L6 boundary")
        added = additions.get(record.digest)
        if added is not None and added != record.payload:
            raise ReceiptError("one digest was supplied with different receipt bytes")
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


def _extend_payloads(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    records = []
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("physical L6 receipt payload must be nonempty bytes")
        records.append(ReceiptRecord(receipt_sha256(payload), payload))
    return _extend_records(registry, records)


class TypedTrit(IntEnum):
    NEGATIVE = -1
    QUIESCENT = 0
    POSITIVE = 1


class NativeDirection(IntEnum):
    NEGATIVE = -1
    POSITIVE = 1


@dataclass(frozen=True, slots=True)
class SensorNativeCoordinate:
    coordinate_id: str
    base_code: int
    minimum_code: int
    maximum_code: int
    physical_quantum: Fraction
    source_authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.coordinate_id, "sensor native coordinate_id")
        _require_integer(self.base_code, "sensor base_code")
        _require_integer(self.minimum_code, "sensor minimum_code")
        _require_integer(self.maximum_code, "sensor maximum_code")
        if self.minimum_code > self.maximum_code:
            raise ReceiptError("sensor native code bounds are inverted")
        if not self.minimum_code <= self.base_code <= self.maximum_code:
            raise ReceiptError("sensor base code lies outside exact native bounds")
        require_fraction(self.physical_quantum, "sensor physical_quantum")
        if self.physical_quantum <= 0:
            raise ReceiptError("sensor physical_quantum must be strictly positive")
        sha256_digest(
            self.source_authority_receipt_sha256,
            "sensor coordinate authority receipt",
        )


@dataclass(frozen=True, slots=True)
class LanguageTritCoordinate:
    coordinate_id: str
    base_trit: TypedTrit
    trit_authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.coordinate_id, "language trit coordinate_id")
        if not isinstance(self.base_trit, TypedTrit):
            raise ReceiptError("language base value must be an exact typed trit")
        sha256_digest(
            self.trit_authority_receipt_sha256,
            "language trit authority receipt",
        )


def native_perturbation_profile_receipt_payload(
    *,
    profile_id: str,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    sensor_coordinates: tuple[SensorNativeCoordinate, ...],
    language_trit_coordinates: tuple[LanguageTritCoordinate, ...],
) -> bytes:
    require_identifier(profile_id, "native perturbation profile_id")
    if not isinstance(lane, L6Lane):
        raise ReceiptError("native perturbation lane must be typed")
    require_identifier(provider_id, "native perturbation provider_id")
    require_identifier(native_port_id, "native perturbation native_port_id")
    if not isinstance(sensor_coordinates, tuple):
        raise ReceiptError("sensor coordinates must be immutable")
    if not isinstance(language_trit_coordinates, tuple):
        raise ReceiptError("language trit coordinates must be immutable")
    return _canonical_bytes(
        {
            "language_trit_coordinates": [
                {
                    "base_trit": int(value.base_trit),
                    "coordinate_id": value.coordinate_id,
                    "trit_authority_receipt_sha256": (
                        value.trit_authority_receipt_sha256
                    ),
                }
                for value in language_trit_coordinates
            ],
            "lane": lane.value,
            "native_port_id": native_port_id,
            "profile_id": profile_id,
            "provider_id": provider_id,
            "schema": "glew.l6.native_perturbation_profile.v1",
            "sensor_coordinates": [
                {
                    "base_code": value.base_code,
                    "coordinate_id": value.coordinate_id,
                    "maximum_code": value.maximum_code,
                    "minimum_code": value.minimum_code,
                    "physical_quantum": _fraction_text(value.physical_quantum),
                    "source_authority_receipt_sha256": (
                        value.source_authority_receipt_sha256
                    ),
                }
                for value in sensor_coordinates
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class MountedNativePerturbationProfile:
    profile_id: str
    lane: L6Lane
    provider_id: str
    native_port_id: str
    sensor_coordinates: tuple[SensorNativeCoordinate, ...]
    language_trit_coordinates: tuple[LanguageTritCoordinate, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.profile_id, "native perturbation profile_id")
        if not isinstance(self.lane, L6Lane):
            raise ReceiptError("native perturbation lane must be typed")
        require_identifier(self.provider_id, "native perturbation provider_id")
        require_identifier(self.native_port_id, "native perturbation native_port_id")
        if not isinstance(self.sensor_coordinates, tuple) or not all(
            isinstance(value, SensorNativeCoordinate)
            for value in self.sensor_coordinates
        ):
            raise ReceiptError("sensor coordinates must be typed and immutable")
        if not isinstance(self.language_trit_coordinates, tuple) or not all(
            isinstance(value, LanguageTritCoordinate)
            for value in self.language_trit_coordinates
        ):
            raise ReceiptError("language trit coordinates must be typed and immutable")
        if self.lane is L6Lane.LANGUAGE:
            if self.sensor_coordinates or not self.language_trit_coordinates:
                raise ReceiptError(
                    "language requires typed trit authority and forbids sensor codes"
                )
        elif self.language_trit_coordinates or not self.sensor_coordinates:
            raise ReceiptError(
                "non-language native ports require physical sensor coordinates"
            )
        sensor_ids = tuple(value.coordinate_id for value in self.sensor_coordinates)
        trit_ids = tuple(
            value.coordinate_id for value in self.language_trit_coordinates
        )
        if sensor_ids != tuple(sorted(sensor_ids)) or len(set(sensor_ids)) != len(
            sensor_ids
        ):
            raise ReceiptError("sensor coordinates are not canonical and unique")
        if trit_ids != tuple(sorted(trit_ids)) or len(set(trit_ids)) != len(
            trit_ids
        ):
            raise ReceiptError("language trit coordinates are not canonical and unique")
        sha256_digest(
            self.authority_receipt_sha256,
            "native perturbation profile authority receipt",
        )

    @property
    def identity(self) -> tuple[int, str, str]:
        return (
            LANE_ORDER.index(self.lane),
            self.provider_id,
            self.native_port_id,
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for value in self.sensor_coordinates:
            receipt_registry.resolve(
                value.source_authority_receipt_sha256,
                "sensor coordinate authority receipt",
            )
        for value in self.language_trit_coordinates:
            receipt_registry.resolve(
                value.trit_authority_receipt_sha256,
                "language trit authority receipt",
            )
        expected = native_perturbation_profile_receipt_payload(
            profile_id=self.profile_id,
            lane=self.lane,
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            sensor_coordinates=self.sensor_coordinates,
            language_trit_coordinates=self.language_trit_coordinates,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "native perturbation profile authority receipt",
        )


@dataclass(frozen=True, slots=True)
class SensorCodeState:
    coordinate_id: str
    raw_code: int

    def __post_init__(self) -> None:
        require_identifier(self.coordinate_id, "sensor state coordinate_id")
        _require_integer(self.raw_code, "sensor state raw_code")


@dataclass(frozen=True, slots=True)
class LanguageTritState:
    coordinate_id: str
    trit: TypedTrit

    def __post_init__(self) -> None:
        require_identifier(self.coordinate_id, "language state coordinate_id")
        if not isinstance(self.trit, TypedTrit):
            raise ReceiptError("language state value must be a typed trit")


class NativeReplayCaseKind(str, Enum):
    BASE = "base"
    SENSOR_ADJACENT_CODE = "sensor_adjacent_code"
    LANGUAGE_TYPED_TRIT = "language_typed_trit"


def native_replay_case_receipt_payload(
    *,
    case_id: str,
    case_index: int,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    kind: NativeReplayCaseKind,
    target_coordinate_id: str | None,
    direction: NativeDirection | None,
    native_delta: Fraction,
    sensor_codes: tuple[SensorCodeState, ...],
    language_trits: tuple[LanguageTritState, ...],
) -> bytes:
    require_identifier(case_id, "native replay case_id")
    _require_integer(case_index, "native replay case_index")
    if case_index < 0:
        raise ReceiptError("native replay case_index cannot be negative")
    if not isinstance(lane, L6Lane):
        raise ReceiptError("native replay lane must be typed")
    require_identifier(provider_id, "native replay provider_id")
    require_identifier(native_port_id, "native replay native_port_id")
    sha256_digest(profile_receipt_sha256, "native replay profile receipt")
    sha256_digest(
        pre_window_state_receipt_sha256,
        "native replay pre-window state receipt",
    )
    if not isinstance(kind, NativeReplayCaseKind):
        raise ReceiptError("native replay case kind must be typed")
    if target_coordinate_id is not None:
        require_identifier(target_coordinate_id, "native replay target coordinate")
    if direction is not None and not isinstance(direction, NativeDirection):
        raise ReceiptError("native replay direction must be typed")
    require_fraction(native_delta, "native replay native_delta")
    return _canonical_bytes(
        {
            "case_id": case_id,
            "case_index": case_index,
            "direction": None if direction is None else int(direction),
            "kind": kind.value,
            "lane": lane.value,
            "language_trits": [
                {"coordinate_id": value.coordinate_id, "trit": int(value.trit)}
                for value in language_trits
            ],
            "native_delta": _fraction_text(native_delta),
            "native_port_id": native_port_id,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "provider_id": provider_id,
            "schema": "glew.l6.native_replay_case.v1",
            "sensor_codes": [
                {"coordinate_id": value.coordinate_id, "raw_code": value.raw_code}
                for value in sensor_codes
            ],
            "target_coordinate_id": target_coordinate_id,
        }
    )


@dataclass(frozen=True, slots=True)
class NativeReplayCase:
    case_id: str
    case_index: int
    lane: L6Lane
    provider_id: str
    native_port_id: str
    profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    kind: NativeReplayCaseKind
    target_coordinate_id: str | None
    direction: NativeDirection | None
    native_delta: Fraction
    sensor_codes: tuple[SensorCodeState, ...]
    language_trits: tuple[LanguageTritState, ...]
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.sensor_codes, tuple) or not all(
            isinstance(value, SensorCodeState) for value in self.sensor_codes
        ):
            raise ReceiptError("native replay sensor codes are not typed")
        if not isinstance(self.language_trits, tuple) or not all(
            isinstance(value, LanguageTritState) for value in self.language_trits
        ):
            raise ReceiptError("native replay language trits are not typed")
        sensor_ids = tuple(value.coordinate_id for value in self.sensor_codes)
        trit_ids = tuple(value.coordinate_id for value in self.language_trits)
        if sensor_ids != tuple(sorted(sensor_ids)) or len(set(sensor_ids)) != len(
            sensor_ids
        ):
            raise ReceiptError("native replay sensor state is not canonical")
        if trit_ids != tuple(sorted(trit_ids)) or len(set(trit_ids)) != len(
            trit_ids
        ):
            raise ReceiptError("native replay trit state is not canonical")
        if self.kind is NativeReplayCaseKind.BASE:
            if (
                self.target_coordinate_id is not None
                or self.direction is not None
                or self.native_delta != 0
            ):
                raise ReceiptError("base native replay cannot carry a perturbation")
        elif (
            self.target_coordinate_id is None
            or self.direction is None
            or self.native_delta == 0
        ):
            raise ReceiptError("adjacent native replay lacks target, direction, or delta")
        if self.lane is L6Lane.LANGUAGE:
            if self.sensor_codes or not self.language_trits:
                raise ReceiptError("language replay must preserve typed trit state")
            if self.kind not in (
                NativeReplayCaseKind.BASE,
                NativeReplayCaseKind.LANGUAGE_TYPED_TRIT,
            ):
                raise ReceiptError("language replay cannot use sensor-code perturbation")
        elif self.language_trits or not self.sensor_codes:
            raise ReceiptError("sensor replay must preserve integer native state")
        expected = native_replay_case_receipt_payload(
            case_id=self.case_id,
            case_index=self.case_index,
            lane=self.lane,
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            profile_receipt_sha256=self.profile_receipt_sha256,
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            kind=self.kind,
            target_coordinate_id=self.target_coordinate_id,
            direction=self.direction,
            native_delta=self.native_delta,
            sensor_codes=self.sensor_codes,
            language_trits=self.language_trits,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("native replay case differs from its receipt")


def _make_case(
    *,
    case_id: str,
    case_index: int,
    profile: MountedNativePerturbationProfile,
    pre_window_state: MountedPreWindowState,
    kind: NativeReplayCaseKind,
    target_coordinate_id: str | None,
    direction: NativeDirection | None,
    native_delta: Fraction,
    sensor_codes: tuple[SensorCodeState, ...],
    language_trits: tuple[LanguageTritState, ...],
) -> NativeReplayCase:
    payload = native_replay_case_receipt_payload(
        case_id=case_id,
        case_index=case_index,
        lane=profile.lane,
        provider_id=profile.provider_id,
        native_port_id=profile.native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        kind=kind,
        target_coordinate_id=target_coordinate_id,
        direction=direction,
        native_delta=native_delta,
        sensor_codes=sensor_codes,
        language_trits=language_trits,
    )
    return NativeReplayCase(
        case_id,
        case_index,
        profile.lane,
        profile.provider_id,
        profile.native_port_id,
        profile.authority_receipt_sha256,
        pre_window_state.authority_receipt_sha256,
        kind,
        target_coordinate_id,
        direction,
        native_delta,
        sensor_codes,
        language_trits,
        receipt_sha256(payload),
        payload,
    )


def enumerate_native_replay_cases(
    profile: MountedNativePerturbationProfile,
    pre_window_state: MountedPreWindowState,
) -> tuple[NativeReplayCase, ...]:
    """Enumerate base plus every admissible directed adjacent native state."""

    if not isinstance(profile, MountedNativePerturbationProfile):
        raise ReceiptError("native replay enumeration requires a mounted profile")
    if not isinstance(pre_window_state, MountedPreWindowState):
        raise ReceiptError("native replay enumeration requires immutable state")
    sensor_base = tuple(
        SensorCodeState(value.coordinate_id, value.base_code)
        for value in profile.sensor_coordinates
    )
    trit_base = tuple(
        LanguageTritState(value.coordinate_id, value.base_trit)
        for value in profile.language_trit_coordinates
    )
    cases = [
        _make_case(
            case_id=f"{profile.profile_id}:native:0",
            case_index=0,
            profile=profile,
            pre_window_state=pre_window_state,
            kind=NativeReplayCaseKind.BASE,
            target_coordinate_id=None,
            direction=None,
            native_delta=Fraction(0),
            sensor_codes=sensor_base,
            language_trits=trit_base,
        )
    ]
    case_index = 1
    if profile.lane is L6Lane.LANGUAGE:
        for coordinate in profile.language_trit_coordinates:
            for direction in (NativeDirection.NEGATIVE, NativeDirection.POSITIVE):
                target_value = int(coordinate.base_trit) + int(direction)
                if target_value not in (-1, 0, 1):
                    continue
                changed = tuple(
                    LanguageTritState(
                        value.coordinate_id,
                        TypedTrit(target_value)
                        if value.coordinate_id == coordinate.coordinate_id
                        else value.base_trit,
                    )
                    for value in profile.language_trit_coordinates
                )
                cases.append(
                    _make_case(
                        case_id=f"{profile.profile_id}:native:{case_index}",
                        case_index=case_index,
                        profile=profile,
                        pre_window_state=pre_window_state,
                        kind=NativeReplayCaseKind.LANGUAGE_TYPED_TRIT,
                        target_coordinate_id=coordinate.coordinate_id,
                        direction=direction,
                        native_delta=Fraction(int(direction)),
                        sensor_codes=(),
                        language_trits=changed,
                    )
                )
                case_index += 1
    else:
        for coordinate in profile.sensor_coordinates:
            for direction in (NativeDirection.NEGATIVE, NativeDirection.POSITIVE):
                target_code = coordinate.base_code + int(direction)
                if not coordinate.minimum_code <= target_code <= coordinate.maximum_code:
                    continue
                changed = tuple(
                    SensorCodeState(
                        value.coordinate_id,
                        target_code
                        if value.coordinate_id == coordinate.coordinate_id
                        else value.base_code,
                    )
                    for value in profile.sensor_coordinates
                )
                cases.append(
                    _make_case(
                        case_id=f"{profile.profile_id}:native:{case_index}",
                        case_index=case_index,
                        profile=profile,
                        pre_window_state=pre_window_state,
                        kind=NativeReplayCaseKind.SENSOR_ADJACENT_CODE,
                        target_coordinate_id=coordinate.coordinate_id,
                        direction=direction,
                        native_delta=(
                            Fraction(int(direction)) * coordinate.physical_quantum
                        ),
                        sensor_codes=changed,
                        language_trits=(),
                    )
                )
                case_index += 1
    return tuple(cases)


@dataclass(frozen=True, slots=True)
class ExactL4Response:
    D_k: Fraction
    M_k: Fraction
    R_rev_k: Fraction
    U_star_k: Fraction
    C_k: Fraction
    P_k: Fraction
    B_k: Fraction

    def __post_init__(self) -> None:
        for field_name in FIELD_ORDER:
            require_fraction(getattr(self, field_name.value), field_name.value)

    def as_tuple(self) -> tuple[Fraction, ...]:
        return tuple(getattr(self, field_name.value) for field_name in FIELD_ORDER)


def _l4_payload(value: ExactL4Response) -> dict[str, str]:
    if not isinstance(value, ExactL4Response):
        raise ReceiptError("L4 replay response must preserve all seven fields")
    return {
        field_name.value: _fraction_text(getattr(value, field_name.value))
        for field_name in FIELD_ORDER
    }


def native_l4_replay_response_receipt_payload(
    *,
    response_id: str,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    case_receipt_sha256: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    branch_id: str,
    cell_id: str,
    l4_response: ExactL4Response,
    source_operator_receipt_sha256: str,
) -> bytes:
    require_identifier(response_id, "native L4 response_id")
    if not isinstance(lane, L6Lane):
        raise ReceiptError("native L4 response lane must be typed")
    for value, field_name in (
        (provider_id, "native L4 provider_id"),
        (native_port_id, "native L4 native_port_id"),
        (branch_id, "native L4 branch_id"),
        (cell_id, "native L4 cell_id"),
    ):
        require_identifier(value, field_name)
    for digest, field_name in (
        (case_receipt_sha256, "native L4 case receipt"),
        (profile_receipt_sha256, "native L4 profile receipt"),
        (pre_window_state_receipt_sha256, "native L4 state receipt"),
        (source_operator_receipt_sha256, "native L4 source operator receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "branch_id": branch_id,
            "case_receipt_sha256": case_receipt_sha256,
            "cell_id": cell_id,
            "l4_response": _l4_payload(l4_response),
            "lane": lane.value,
            "native_port_id": native_port_id,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "provider_id": provider_id,
            "response_id": response_id,
            "schema": "glew.l6.native_l4_replay_response.v1",
            "source_operator_receipt_sha256": source_operator_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class NativeL4ReplayResponse:
    response_id: str
    lane: L6Lane
    provider_id: str
    native_port_id: str
    case_receipt_sha256: str
    profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    branch_id: str
    cell_id: str
    l4_response: ExactL4Response
    source_operator_receipt_sha256: str
    receipt_sha256: str

    def verify(
        self,
        *,
        case: NativeReplayCase,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        bindings = (
            (self.lane, case.lane, "lane"),
            (self.provider_id, case.provider_id, "provider"),
            (self.native_port_id, case.native_port_id, "native port"),
            (self.case_receipt_sha256, case.receipt_sha256, "replay case"),
            (self.profile_receipt_sha256, case.profile_receipt_sha256, "profile"),
            (
                self.pre_window_state_receipt_sha256,
                case.pre_window_state_receipt_sha256,
                "pre-window state",
            ),
        )
        for actual, expected, name in bindings:
            if actual != expected:
                raise ReceiptError(f"native L4 response belongs to another {name}")
        receipt_registry.resolve(
            self.source_operator_receipt_sha256,
            "native L4 source operator receipt",
        )
        expected = native_l4_replay_response_receipt_payload(
            response_id=self.response_id,
            lane=self.lane,
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            case_receipt_sha256=self.case_receipt_sha256,
            profile_receipt_sha256=self.profile_receipt_sha256,
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            branch_id=self.branch_id,
            cell_id=self.cell_id,
            l4_response=self.l4_response,
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            expected,
            "native L4 replay response receipt",
        )


def native_response_set_receipt_payload(
    *,
    response_set_id: str,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    responses: tuple[NativeL4ReplayResponse, ...],
    source_completeness_receipt_sha256: str,
) -> bytes:
    require_identifier(response_set_id, "native response-set id")
    if not isinstance(lane, L6Lane):
        raise ReceiptError("native response-set lane must be typed")
    require_identifier(provider_id, "native response-set provider_id")
    require_identifier(native_port_id, "native response-set native_port_id")
    for digest, field_name in (
        (profile_receipt_sha256, "native response-set profile receipt"),
        (pre_window_state_receipt_sha256, "native response-set state receipt"),
        (
            source_completeness_receipt_sha256,
            "native response-set completeness source receipt",
        ),
    ):
        sha256_digest(digest, field_name)
    if not isinstance(responses, tuple):
        raise ReceiptError("native response set must be immutable")
    return _canonical_bytes(
        {
            "lane": lane.value,
            "native_port_id": native_port_id,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "provider_id": provider_id,
            "response_receipt_sha256s": [
                value.receipt_sha256 for value in responses
            ],
            "response_set_id": response_set_id,
            "schema": "glew.l6.native_response_set.v1",
            "source_completeness_receipt_sha256": (
                source_completeness_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class MountedNativeResponseSet:
    response_set_id: str
    lane: L6Lane
    provider_id: str
    native_port_id: str
    profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    responses: tuple[NativeL4ReplayResponse, ...]
    source_completeness_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(
        self,
        *,
        profile: MountedNativePerturbationProfile,
        pre_window_state: MountedPreWindowState,
        expected_cases: tuple[NativeReplayCase, ...],
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (
            self.lane is not profile.lane
            or self.provider_id != profile.provider_id
            or self.native_port_id != profile.native_port_id
            or self.profile_receipt_sha256 != profile.authority_receipt_sha256
            or self.pre_window_state_receipt_sha256
            != pre_window_state.authority_receipt_sha256
        ):
            raise ReceiptError("native response set belongs to another provider state")
        if not isinstance(self.responses, tuple) or not all(
            isinstance(value, NativeL4ReplayResponse) for value in self.responses
        ):
            raise ReceiptError("native response set is not typed and immutable")
        if len(self.responses) != len(expected_cases):
            raise ReceiptError("a required adjacent native response is missing")
        if tuple(value.case_receipt_sha256 for value in self.responses) != tuple(
            value.receipt_sha256 for value in expected_cases
        ):
            raise ReceiptError("native responses are incomplete or out of replay order")
        receipt_registry.resolve(
            self.source_completeness_receipt_sha256,
            "native response-set completeness source receipt",
        )
        for response, case in zip(self.responses, expected_cases, strict=True):
            response.verify(case=case, receipt_registry=receipt_registry)
        expected = native_response_set_receipt_payload(
            response_set_id=self.response_set_id,
            lane=self.lane,
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            profile_receipt_sha256=self.profile_receipt_sha256,
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            responses=self.responses,
            source_completeness_receipt_sha256=(
                self.source_completeness_receipt_sha256
            ),
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "native response-set authority receipt",
        )


def same_branch_cell_proof_receipt_payload(
    *,
    proof_id: str,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    branch_id: str,
    cell_id: str,
    response_receipt_sha256s: tuple[str, ...],
    source_operator_receipt_sha256: str,
) -> bytes:
    require_identifier(proof_id, "same-branch/cell proof_id")
    if not isinstance(lane, L6Lane):
        raise ReceiptError("same-branch/cell proof lane must be typed")
    for value, field_name in (
        (provider_id, "same-branch/cell provider_id"),
        (native_port_id, "same-branch/cell native_port_id"),
        (branch_id, "same-branch/cell branch_id"),
        (cell_id, "same-branch/cell cell_id"),
    ):
        require_identifier(value, field_name)
    for digest, field_name in (
        (profile_receipt_sha256, "same-branch/cell profile receipt"),
        (pre_window_state_receipt_sha256, "same-branch/cell state receipt"),
        (source_operator_receipt_sha256, "same-branch/cell source receipt"),
    ):
        sha256_digest(digest, field_name)
    if not isinstance(response_receipt_sha256s, tuple):
        raise ReceiptError("same-branch/cell response receipts must be immutable")
    for digest in response_receipt_sha256s:
        sha256_digest(digest, "same-branch/cell response receipt")
    return _canonical_bytes(
        {
            "branch_id": branch_id,
            "cell_id": cell_id,
            "lane": lane.value,
            "native_port_id": native_port_id,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "proof_id": proof_id,
            "provider_id": provider_id,
            "response_receipt_sha256s": list(response_receipt_sha256s),
            "schema": "glew.l6.same_branch_cell_replay_proof.v1",
            "source_operator_receipt_sha256": source_operator_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedSameBranchCellProof:
    proof_id: str
    lane: L6Lane
    provider_id: str
    native_port_id: str
    profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    branch_id: str
    cell_id: str
    response_receipt_sha256s: tuple[str, ...]
    source_operator_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(
        self,
        *,
        profile: MountedNativePerturbationProfile,
        pre_window_state: MountedPreWindowState,
        responses: tuple[NativeL4ReplayResponse, ...],
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (
            self.lane is not profile.lane
            or self.provider_id != profile.provider_id
            or self.native_port_id != profile.native_port_id
            or self.profile_receipt_sha256 != profile.authority_receipt_sha256
            or self.pre_window_state_receipt_sha256
            != pre_window_state.authority_receipt_sha256
        ):
            raise ReceiptError("same-branch/cell proof belongs to another provider state")
        expected_response_digests = tuple(value.receipt_sha256 for value in responses)
        if self.response_receipt_sha256s != expected_response_digests:
            raise ReceiptError("same-branch/cell proof does not bind every replay")
        if any(
            value.branch_id != self.branch_id or value.cell_id != self.cell_id
            for value in responses
        ):
            raise ReceiptError("native replays cross an L0-L4 branch or cell boundary")
        receipt_registry.resolve(
            self.source_operator_receipt_sha256,
            "same-branch/cell proof source receipt",
        )
        expected = same_branch_cell_proof_receipt_payload(
            proof_id=self.proof_id,
            lane=self.lane,
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            profile_receipt_sha256=self.profile_receipt_sha256,
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            branch_id=self.branch_id,
            cell_id=self.cell_id,
            response_receipt_sha256s=self.response_receipt_sha256s,
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "same-branch/cell proof authority receipt",
        )


@dataclass(frozen=True, slots=True)
class NativePortReplayBundle:
    profile: MountedNativePerturbationProfile
    response_set: MountedNativeResponseSet | None
    branch_cell_proof: MountedSameBranchCellProof | None


def tangent_derivation_receipt_payload(
    *,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    response_set_receipt_sha256: str,
    branch_proof_receipt_sha256: str,
    candidate_branch_receipt_sha256: str,
    candidate_tangent_receipt_sha256: str,
    perturbation_case_receipt_sha256s: tuple[str, ...],
    response_receipt_sha256s: tuple[str, ...],
    perturbation_coordinate_ids: tuple[str, ...],
    tangent: tuple[tuple[Fraction, ...], ...],
) -> bytes:
    if not isinstance(lane, L6Lane):
        raise ReceiptError("tangent derivation lane must be typed")
    require_identifier(provider_id, "tangent derivation provider_id")
    require_identifier(native_port_id, "tangent derivation native_port_id")
    for digest, field_name in (
        (profile_receipt_sha256, "tangent derivation profile receipt"),
        (pre_window_state_receipt_sha256, "tangent derivation state receipt"),
        (response_set_receipt_sha256, "tangent derivation response-set receipt"),
        (branch_proof_receipt_sha256, "tangent derivation branch proof receipt"),
        (candidate_branch_receipt_sha256, "candidate branch receipt"),
        (candidate_tangent_receipt_sha256, "candidate tangent receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "branch_proof_receipt_sha256": branch_proof_receipt_sha256,
            "candidate_branch_receipt_sha256": candidate_branch_receipt_sha256,
            "candidate_tangent_receipt_sha256": candidate_tangent_receipt_sha256,
            "field_order": [value.value for value in FIELD_ORDER],
            "lane": lane.value,
            "native_port_id": native_port_id,
            "operator": PHYSICAL_TANGENT_OPERATOR_ID,
            "perturbation_case_receipt_sha256s": list(
                perturbation_case_receipt_sha256s
            ),
            "perturbation_coordinate_ids": list(perturbation_coordinate_ids),
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "provider_id": provider_id,
            "response_receipt_sha256s": list(response_receipt_sha256s),
            "response_set_receipt_sha256": response_set_receipt_sha256,
            "schema": "glew.l6.exact_native_tangent_derivation.v1",
            "tangent": [
                [_fraction_text(value) for value in row] for row in tangent
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class DerivedNativePortTangent:
    profile: MountedNativePerturbationProfile
    replay_cases: tuple[NativeReplayCase, ...]
    response_set: MountedNativeResponseSet
    branch_cell_proof: MountedSameBranchCellProof
    tangent: tuple[tuple[Fraction, ...], ...]
    claim: CandidateProviderTangentClaim
    derivation_receipt_sha256: str


class PhysicalTangentProductionStatus(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LaneCompletenessReceipt:
    lane: L6Lane
    receipt_sha256: str
    receipt_payload: bytes


@dataclass(frozen=True, slots=True)
class PhysicalL6TangentProduction:
    status: PhysicalTangentProductionStatus
    derived_ports: tuple[DerivedNativePortTangent, ...]
    candidate_constraints: CandidateConstraintProduction | None
    rank_receipt: ExactRankReceipt | None
    lane_completeness_receipts: tuple[LaneCompletenessReceipt, ...]
    receipt_registry: ReceiptRegistry
    reason: str


def _unknown(
    registry: ReceiptRegistry,
    reason: str,
) -> PhysicalL6TangentProduction:
    return PhysicalL6TangentProduction(
        PhysicalTangentProductionStatus.UNKNOWN,
        (),
        None,
        None,
        (),
        registry,
        reason,
    )


def _derive_tangent(
    cases: tuple[NativeReplayCase, ...],
    responses: tuple[NativeL4ReplayResponse, ...],
) -> tuple[tuple[Fraction, ...], ...]:
    if len(cases) < 2 or len(cases) != len(responses):
        raise ReceiptError("native tangent requires base and adjacent replay responses")
    base = responses[0].l4_response.as_tuple()
    columns = []
    for case, response in zip(cases[1:], responses[1:], strict=True):
        if case.native_delta == 0:
            raise ReceiptError("adjacent native replay has exact zero delta")
        values = response.l4_response.as_tuple()
        columns.append(
            tuple(
                (value - base_value) / case.native_delta
                for value, base_value in zip(values, base, strict=True)
            )
        )
    return tuple(
        tuple(column[field_index] for column in columns)
        for field_index in range(len(FIELD_ORDER))
    )


def produce_physical_l6_tangents(
    *,
    bundles: tuple[NativePortReplayBundle, ...] | None,
    pre_window_state: MountedPreWindowState,
    receipt_registry: ReceiptRegistry,
) -> PhysicalL6TangentProduction:
    """Derive exact native response secants and feed fixed-42 row production."""

    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("physical L6 producer requires a mounted registry")
    if bundles is None or not isinstance(bundles, tuple) or not bundles:
        return _unknown(receipt_registry, "native replay bundles are missing")
    if not isinstance(pre_window_state, MountedPreWindowState):
        return _unknown(receipt_registry, "immutable pre-window state is missing")
    try:
        pre_window_state.verify(receipt_registry)
    except ReceiptError as exc:
        return _unknown(receipt_registry, f"pre-window state is unknown: {exc}")
    if any(not isinstance(value, NativePortReplayBundle) for value in bundles):
        return _unknown(receipt_registry, "a native replay bundle has invalid type")
    ordered = tuple(sorted(bundles, key=lambda value: value.profile.identity))
    identities = tuple(value.profile.identity for value in ordered)
    if len(set(identities)) != len(identities):
        return _unknown(receipt_registry, "native replay bundles repeat a provider port")

    working_registry = receipt_registry
    derived: list[DerivedNativePortTangent] = []
    claims: list[CandidateProviderTangentClaim] = []
    try:
        for bundle in ordered:
            profile = bundle.profile
            if not isinstance(profile, MountedNativePerturbationProfile):
                raise ReceiptError("native replay bundle lacks a mounted profile")
            profile.verify(working_registry)
            cases = enumerate_native_replay_cases(profile, pre_window_state)
            working_registry = _extend_payloads(
                working_registry,
                (value.receipt_payload for value in cases),
            )
            if bundle.response_set is None:
                raise ReceiptError("a required native response set is missing")
            response_set = bundle.response_set
            response_set.verify(
                profile=profile,
                pre_window_state=pre_window_state,
                expected_cases=cases,
                receipt_registry=working_registry,
            )
            if bundle.branch_cell_proof is None:
                raise ReceiptError("same-branch/cell proof is missing")
            branch_proof = bundle.branch_cell_proof
            branch_proof.verify(
                profile=profile,
                pre_window_state=pre_window_state,
                responses=response_set.responses,
                receipt_registry=working_registry,
            )
            tangent = _derive_tangent(cases, response_set.responses)
            perturbation_ids = tuple(value.case_id for value in cases[1:])

            candidate_branch_payload = canonical_candidate_branch_cell_receipt_payload(
                lane=profile.lane,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                branch_id=branch_proof.branch_id,
                cell_id=branch_proof.cell_id,
            )
            candidate_branch_digest = receipt_sha256(candidate_branch_payload)
            candidate_tangent_payload = canonical_candidate_local_tangent_receipt_payload(
                lane=profile.lane,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                branch_id=branch_proof.branch_id,
                cell_id=branch_proof.cell_id,
                perturbation_coordinate_ids=perturbation_ids,
                tangent=tangent,
                branch_cell_receipt_sha256=candidate_branch_digest,
            )
            candidate_tangent_digest = receipt_sha256(candidate_tangent_payload)
            derivation_payload = tangent_derivation_receipt_payload(
                lane=profile.lane,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                profile_receipt_sha256=profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                response_set_receipt_sha256=response_set.authority_receipt_sha256,
                branch_proof_receipt_sha256=branch_proof.authority_receipt_sha256,
                candidate_branch_receipt_sha256=candidate_branch_digest,
                candidate_tangent_receipt_sha256=candidate_tangent_digest,
                perturbation_case_receipt_sha256s=tuple(
                    value.receipt_sha256 for value in cases[1:]
                ),
                response_receipt_sha256s=tuple(
                    value.receipt_sha256 for value in response_set.responses
                ),
                perturbation_coordinate_ids=perturbation_ids,
                tangent=tangent,
            )
            working_registry = _extend_payloads(
                working_registry,
                (
                    candidate_branch_payload,
                    candidate_tangent_payload,
                    derivation_payload,
                ),
            )
            claim = CandidateProviderTangentClaim(
                lane=profile.lane,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                branch_id=branch_proof.branch_id,
                cell_id=branch_proof.cell_id,
                perturbation_coordinate_ids=perturbation_ids,
                tangent=tangent,
                branch_cell_receipt_sha256=candidate_branch_digest,
                tangent_receipt_sha256=candidate_tangent_digest,
            )
            claims.append(claim)
            derived.append(
                DerivedNativePortTangent(
                    profile,
                    cases,
                    response_set,
                    branch_proof,
                    tangent,
                    claim,
                    receipt_sha256(derivation_payload),
                )
            )
    except (ReceiptError, TypeError, ValueError) as exc:
        return _unknown(receipt_registry, f"physical native response is unknown: {exc}")

    candidate = produce_candidate_fixed42_constraints(
        tuple(claims),
        working_registry,
    )
    if (
        candidate.status is not CandidateConstraintProductionStatus.KNOWN
        or candidate.stack is None
    ):
        return _unknown(
            receipt_registry,
            f"candidate fixed-42 production is unknown: {candidate.reason}",
        )
    row_payloads = tuple(
        payload
        for provider_set in candidate.provider_sets
        for payload in provider_set.row_receipt_payloads
    )
    working_registry = _extend_payloads(working_registry, row_payloads)
    completeness = []
    completeness_payloads = []
    active_lanes = tuple(
        lane
        for lane in LANE_ORDER
        if any(value.profile.lane is lane for value in derived)
    )
    for lane in active_lanes:
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in candidate.stack.rows
            if row.provenance.lane is lane
        )
        payload = canonical_completeness_receipt_payload(
            lane=lane,
            row_receipt_sha256s=row_digests,
        )
        completeness_payloads.append(payload)
        completeness.append(
            LaneCompletenessReceipt(lane, receipt_sha256(payload), payload)
        )
    working_registry = _extend_payloads(
        working_registry,
        completeness_payloads,
    )
    return PhysicalL6TangentProduction(
        PhysicalTangentProductionStatus.KNOWN,
        tuple(derived),
        candidate,
        exact_rank_receipt(candidate.stack),
        tuple(completeness),
        working_registry,
        (
            "fixed-42 rows are exactly derived from exhaustive native replay "
            "secants and mounted same-branch/cell proofs"
        ),
    )
