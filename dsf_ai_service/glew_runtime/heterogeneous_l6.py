"""Exact six-lane L6 assembly without flattening native authorities.

Five continuous sensory lanes retain their physical same-branch/cell tangent
production.  The typed-language lane retains its complete discrete Bouligand
contingent cone.  This module verifies those authorities independently and
then binds their complete row union, exact rank, and six lane-completeness
receipts into one immutable assembly receipt.

Language is never wrapped as a continuous ``NativePortReplayBundle`` and no
row is averaged, selected, normalized, scored, or otherwise reduced.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from .field import MountedFieldTopology
from .global_uf import MountedPreWindowState
from .l6 import (
    CandidateConstraintProductionStatus,
    ExactRankReceipt,
    Fixed42ConstraintStack,
    L6Lane,
    canonical_completeness_receipt_payload,
    canonical_row_receipt_payload,
    exact_rank_receipt,
    produce_candidate_fixed42_constraints,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from .physical_l6_tangents import (
    LaneCompletenessReceipt,
    PhysicalL6TangentProduction,
    PhysicalTangentProductionStatus,
    enumerate_native_replay_cases,
    tangent_derivation_receipt_payload,
)
from .typed_language_native_replay import (
    TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID,
    TypedLanguageNativeReplayResult,
)


HETEROGENEOUS_L6_ASSEMBLY_OPERATOR_ID = (
    "glew.l6.exact_five_sensor_plus_language_cone.v1"
)
_SENSOR_LANES = (
    L6Lane.SIGHT,
    L6Lane.SOUND,
    L6Lane.TOUCH,
    L6Lane.SMELL,
    L6Lane.TASTE,
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
    if not isinstance(value, Fraction):
        raise ReceiptError("heterogeneous L6 value must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _verify_registry_contains(
    source: ReceiptRegistry,
    mounted: ReceiptRegistry,
) -> None:
    if not isinstance(source, ReceiptRegistry) or not isinstance(
        mounted,
        ReceiptRegistry,
    ):
        raise ReceiptError("heterogeneous L6 requires mounted receipt registries")
    if source.profile_binding_sha256 != mounted.profile_binding_sha256:
        raise ReceiptError("heterogeneous L6 registries belong to different profiles")
    for record in source.records:
        if mounted.resolve(record.digest, "heterogeneous L6 source receipt") != record.payload:
            raise ReceiptError("heterogeneous L6 source receipt bytes were altered")


def _extend_registry(
    registry: ReceiptRegistry,
    *sources: ReceiptRegistry,
    payloads: tuple[bytes, ...] = (),
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("heterogeneous L6 requires a mounted receipt registry")
    result = list(registry.records)
    mounted = {record.digest: record.payload for record in result}
    for source in sources:
        if not isinstance(source, ReceiptRegistry):
            raise ReceiptError("heterogeneous L6 source registry is not typed")
        if source.profile_binding_sha256 != registry.profile_binding_sha256:
            raise ReceiptError("heterogeneous L6 source registry changed profile")
        for record in source.records:
            previous = mounted.get(record.digest)
            if previous is not None:
                if previous != record.payload:
                    raise ReceiptError("heterogeneous L6 receipt digest collision")
                continue
            mounted[record.digest] = record.payload
            result.append(record)
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("heterogeneous L6 generated an empty receipt")
        digest = receipt_sha256(payload)
        previous = mounted.get(digest)
        if previous is not None:
            if previous != payload:
                raise ReceiptError("heterogeneous L6 generated receipt collision")
            continue
        mounted[digest] = payload
        result.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(result),
    )


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    field_name: str,
) -> None:
    if receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} digest differs from exact bytes")
    if registry.resolve(digest, field_name) != expected:
        raise ReceiptError(f"{field_name} differs from mounted exact bytes")


def _derive_exact_tangent(
    derived,
    cases,
) -> tuple[tuple[Fraction, ...], ...]:
    responses = derived.response_set.responses
    if len(cases) < 2 or len(cases) != len(responses):
        raise ReceiptError("sensor tangent omitted a native replay direction")
    base = responses[0].l4_response.as_tuple()
    columns = []
    for case, response in zip(cases[1:], responses[1:], strict=True):
        if case.native_delta == 0:
            raise ReceiptError("sensor tangent contains a zero native delta")
        columns.append(
            tuple(
                (target - source) / case.native_delta
                for source, target in zip(
                    base,
                    response.l4_response.as_tuple(),
                    strict=True,
                )
            )
        )
    return tuple(
        tuple(column[field_index] for column in columns)
        for field_index in range(len(base))
    )


def _verify_sensor_source(
    *,
    production: PhysicalL6TangentProduction,
    pre_window_state: MountedPreWindowState,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> Fixed42ConstraintStack:
    if not isinstance(production, PhysicalL6TangentProduction):
        raise ReceiptError("heterogeneous L6 lacks typed sensory production")
    if production.status is not PhysicalTangentProductionStatus.KNOWN:
        raise ReceiptError(f"sensory L6 production is unresolved: {production.reason}")
    _verify_registry_contains(production.receipt_registry, receipt_registry)
    candidate = production.candidate_constraints
    if (
        candidate is None
        or candidate.status is not CandidateConstraintProductionStatus.KNOWN
        or candidate.stack is None
    ):
        raise ReceiptError("sensory L6 production lacks exact candidate rows")
    if production.rank_receipt != exact_rank_receipt(candidate.stack):
        raise ReceiptError("sensory L6 rank differs from its exact stack")

    active_lanes = tuple(
        lane
        for lane in _SENSOR_LANES
        if any(value.profile.lane is lane for value in production.derived_ports)
    )
    if active_lanes != _SENSOR_LANES:
        raise ReceiptError("sensory L6 production does not preserve all five senses")
    if any(value.profile.lane is L6Lane.LANGUAGE for value in production.derived_ports):
        raise ReceiptError("continuous sensory production improperly contains language")
    identities = tuple(value.profile.identity for value in production.derived_ports)
    if len(set(identities)) != len(identities):
        raise ReceiptError("sensory L6 production repeats a native port")
    topology_keys = {
        (fiber.lane_id, fiber.port_id) for fiber in topology.ordered_port_fibers
    }

    claims = []
    for derived in production.derived_ports:
        profile = derived.profile
        if (profile.lane.value, profile.native_port_id) not in topology_keys:
            raise ReceiptError("sensory L6 production belongs to another topology")
        profile.verify(receipt_registry)
        cases = enumerate_native_replay_cases(profile, pre_window_state)
        derived.response_set.verify(
            profile=profile,
            pre_window_state=pre_window_state,
            expected_cases=cases,
            receipt_registry=receipt_registry,
        )
        derived.branch_cell_proof.verify(
            profile=profile,
            pre_window_state=pre_window_state,
            responses=derived.response_set.responses,
            receipt_registry=receipt_registry,
        )
        exact_tangent = _derive_exact_tangent(derived, cases)
        if derived.tangent != exact_tangent or derived.claim.tangent != exact_tangent:
            raise ReceiptError("sensory L6 tangent differs from exact replay secants")
        if (
            derived.claim.lane is not profile.lane
            or derived.claim.provider_id != profile.provider_id
            or derived.claim.native_port_id != profile.native_port_id
            or derived.claim.branch_id != derived.branch_cell_proof.branch_id
            or derived.claim.cell_id != derived.branch_cell_proof.cell_id
        ):
            raise ReceiptError("sensory L6 claim lost its native source authority")
        derivation_payload = tangent_derivation_receipt_payload(
            lane=profile.lane,
            provider_id=profile.provider_id,
            native_port_id=profile.native_port_id,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
            response_set_receipt_sha256=derived.response_set.authority_receipt_sha256,
            branch_proof_receipt_sha256=(
                derived.branch_cell_proof.authority_receipt_sha256
            ),
            candidate_branch_receipt_sha256=(
                derived.claim.branch_cell_receipt_sha256
            ),
            candidate_tangent_receipt_sha256=derived.claim.tangent_receipt_sha256,
            perturbation_case_receipt_sha256s=tuple(
                value.receipt_sha256 for value in cases[1:]
            ),
            response_receipt_sha256s=tuple(
                value.receipt_sha256 for value in derived.response_set.responses
            ),
            perturbation_coordinate_ids=derived.claim.perturbation_coordinate_ids,
            tangent=exact_tangent,
        )
        _mounted_exact(
            receipt_registry,
            derived.derivation_receipt_sha256,
            derivation_payload,
            "sensory exact tangent derivation receipt",
        )
        claims.append(derived.claim)

    reproduced = produce_candidate_fixed42_constraints(
        tuple(claims),
        receipt_registry,
    )
    if reproduced != candidate:
        raise ReceiptError("sensory Fixed42 rows differ from exact tangent production")

    completeness_lanes = tuple(
        value.lane for value in production.lane_completeness_receipts
    )
    if completeness_lanes != _SENSOR_LANES:
        raise ReceiptError("sensory completeness does not cover exactly five senses")
    for completeness in production.lane_completeness_receipts:
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in candidate.stack.rows
            if row.provenance.lane is completeness.lane
        )
        payload = canonical_completeness_receipt_payload(
            lane=completeness.lane,
            row_receipt_sha256s=row_digests,
        )
        if completeness.receipt_payload != payload:
            raise ReceiptError("sensory lane completeness bytes were altered")
        _mounted_exact(
            receipt_registry,
            completeness.receipt_sha256,
            payload,
            "sensory lane completeness receipt",
        )
    return candidate.stack


def _language_source_completeness_payload(
    language_replay: TypedLanguageNativeReplayResult,
) -> bytes:
    cone = language_replay.contingent_cone
    return _canonical_bytes(
        {
            "case_receipt_sha256s": [
                value.case.receipt_sha256 for value in language_replay.executions
            ],
            "execution_preparation_receipt_sha256s": [
                value.preparation.receipt_sha256
                for value in language_replay.executions
            ],
            "language_capture_receipt_sha256": cone.language_capture_receipt_sha256,
            "operator": TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID,
            "profile_receipt_sha256": cone.profile_receipt_sha256,
            "schema": "glew.typed_language.native_response_completeness.v2",
        }
    )


def _verify_language_source(
    *,
    language_replay: TypedLanguageNativeReplayResult,
    pre_window_state: MountedPreWindowState,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> Fixed42ConstraintStack:
    if not isinstance(language_replay, TypedLanguageNativeReplayResult):
        raise ReceiptError("heterogeneous L6 lacks typed language replay authority")
    _verify_registry_contains(language_replay.receipt_registry, receipt_registry)
    bundle = language_replay.bundle
    profile = bundle.profile
    if profile.lane is not L6Lane.LANGUAGE:
        raise ReceiptError("language replay source is not the language lane")
    if bundle.branch_cell_proof is not None:
        raise ReceiptError("language was incorrectly assigned same-branch/cell authority")
    if (profile.lane.value, profile.native_port_id) not in {
        (fiber.lane_id, fiber.port_id) for fiber in topology.ordered_port_fibers
    }:
        raise ReceiptError("language replay belongs to another topology")
    profile.verify(receipt_registry)
    cases = enumerate_native_replay_cases(profile, pre_window_state)
    execution_cases = tuple(value.case for value in language_replay.executions)
    if execution_cases != cases:
        raise ReceiptError("language replay omitted or reordered an adjacency")
    response_set = bundle.response_set
    if response_set is None:
        raise ReceiptError("language replay lacks its exact response set")
    response_set.verify(
        profile=profile,
        pre_window_state=pre_window_state,
        expected_cases=cases,
        receipt_registry=receipt_registry,
    )
    if len(response_set.responses) != len(language_replay.executions):
        raise ReceiptError("language replay execution/response counts differ")
    for execution, response in zip(
        language_replay.executions,
        response_set.responses,
        strict=True,
    ):
        if (
            response.case_receipt_sha256 != execution.case.receipt_sha256
            or response.branch_id != execution.branch_id
            or response.cell_id != execution.cell_id
            or response.l4_response != execution.l4_response
            or response.source_operator_receipt_sha256
            != execution.source_operator_receipt_sha256
        ):
            raise ReceiptError("language response differs from executed frozen L0-L4 replay")
        execution.preparation.verify(topology, receipt_registry)
    source_payload = _language_source_completeness_payload(language_replay)
    _mounted_exact(
        receipt_registry,
        response_set.source_completeness_receipt_sha256,
        source_payload,
        "language native response completeness receipt",
    )
    cone = language_replay.contingent_cone
    cone.verify(
        profile=profile,
        pre_window_state=pre_window_state,
        cases=cases,
        response_set=response_set,
        receipt_registry=receipt_registry,
    )
    return cone.fixed42_stack


def heterogeneous_l6_assembly_receipt_payload(
    *,
    pre_window_state_receipt_sha256: str,
    sensor_derivation_receipt_sha256s: tuple[str, ...],
    language_cone_receipt_sha256: str,
    combined_stack: Fixed42ConstraintStack,
    combined_rank: ExactRankReceipt,
    lane_completeness_receipts: tuple[LaneCompletenessReceipt, ...],
) -> bytes:
    if not isinstance(combined_stack, Fixed42ConstraintStack):
        raise ReceiptError("heterogeneous L6 receipt requires an exact Fixed42 stack")
    if not isinstance(combined_rank, ExactRankReceipt):
        raise ReceiptError("heterogeneous L6 receipt requires an exact rank")
    return _canonical_bytes(
        {
            "combined_rank": {
                "n_effective": combined_rank.n_effective,
                "n_start": combined_rank.n_start,
                "pivot_columns": list(combined_rank.pivot_columns),
                "rank": combined_rank.rank,
                "row_count": combined_rank.row_count,
            },
            "language_cone_receipt_sha256": language_cone_receipt_sha256,
            "lane_completeness_receipt_sha256s": [
                value.receipt_sha256 for value in lane_completeness_receipts
            ],
            "operator": HETEROGENEOUS_L6_ASSEMBLY_OPERATOR_ID,
            "ordered_combined_row_receipt_sha256s": [
                row.provenance.receipt_sha256 for row in combined_stack.rows
            ],
            "pre_window_state_receipt_sha256": (
                pre_window_state_receipt_sha256
            ),
            "schema": "glew.l6.heterogeneous_six_lane_assembly.v1",
            "sensor_derivation_receipt_sha256s": list(
                sensor_derivation_receipt_sha256s
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class HeterogeneousL6Assembly:
    """Receipted union of separate sensory and discrete-language authorities."""

    sensor_production: PhysicalL6TangentProduction
    language_replay: TypedLanguageNativeReplayResult
    pre_window_state: MountedPreWindowState
    combined_stack: Fixed42ConstraintStack
    combined_rank: ExactRankReceipt
    lane_completeness_receipts: tuple[LaneCompletenessReceipt, ...]
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        _verify_registry_contains(self.receipt_registry, receipt_registry)
        topology.verify(receipt_registry)
        self.pre_window_state.verify(receipt_registry)
        sensor_stack = _verify_sensor_source(
            production=self.sensor_production,
            pre_window_state=self.pre_window_state,
            topology=topology,
            receipt_registry=receipt_registry,
        )
        language_stack = _verify_language_source(
            language_replay=self.language_replay,
            pre_window_state=self.pre_window_state,
            topology=topology,
            receipt_registry=receipt_registry,
        )
        expected_rows = tuple(
            sorted(
                (*sensor_stack.rows, *language_stack.rows),
                key=lambda row: row.provenance.identity,
            )
        )
        if self.combined_stack != Fixed42ConstraintStack(expected_rows):
            raise ReceiptError("heterogeneous L6 stack omitted, altered, or reordered a row")
        if self.combined_rank != exact_rank_receipt(self.combined_stack):
            raise ReceiptError("heterogeneous L6 rank differs from the exact combined stack")
        if tuple(value.lane for value in self.lane_completeness_receipts) != tuple(
            L6Lane
        ):
            raise ReceiptError("heterogeneous L6 completeness does not cover six lanes")
        for completeness in self.lane_completeness_receipts:
            row_digests = tuple(
                row.provenance.receipt_sha256
                for row in self.combined_stack.rows
                if row.provenance.lane is completeness.lane
            )
            payload = canonical_completeness_receipt_payload(
                lane=completeness.lane,
                row_receipt_sha256s=row_digests,
            )
            if completeness.receipt_payload != payload:
                raise ReceiptError("heterogeneous L6 lane completeness bytes were altered")
            _mounted_exact(
                receipt_registry,
                completeness.receipt_sha256,
                payload,
                "heterogeneous L6 lane completeness receipt",
            )
        for row in self.combined_stack.rows:
            payload = canonical_row_receipt_payload(
                lane=row.provenance.lane,
                provider_id=row.provenance.provider_id,
                native_port_id=row.provenance.native_port_id,
                operator_id=row.provenance.operator_id,
                row_id=row.provenance.row_id,
                coefficients=row.native_coefficients,
            )
            _mounted_exact(
                receipt_registry,
                row.provenance.receipt_sha256,
                payload,
                "heterogeneous L6 exact row receipt",
            )
        payload = heterogeneous_l6_assembly_receipt_payload(
            pre_window_state_receipt_sha256=(
                self.pre_window_state.authority_receipt_sha256
            ),
            sensor_derivation_receipt_sha256s=tuple(
                value.derivation_receipt_sha256
                for value in self.sensor_production.derived_ports
            ),
            language_cone_receipt_sha256=(
                self.language_replay.contingent_cone.authority_receipt_sha256
            ),
            combined_stack=self.combined_stack,
            combined_rank=self.combined_rank,
            lane_completeness_receipts=self.lane_completeness_receipts,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            payload,
            "heterogeneous L6 assembly authority receipt",
        )


def assemble_heterogeneous_l6(
    *,
    sensor_production: PhysicalL6TangentProduction,
    language_replay: TypedLanguageNativeReplayResult,
    pre_window_state: MountedPreWindowState,
    combined_stack: Fixed42ConstraintStack,
    combined_rank: ExactRankReceipt,
    lane_completeness_receipts: tuple[LaneCompletenessReceipt, ...],
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> HeterogeneousL6Assembly:
    """Verify and mount one exact five-sense plus language-cone assembly."""

    if not isinstance(pre_window_state, MountedPreWindowState):
        raise ReceiptError("heterogeneous L6 lacks immutable pre-window state")
    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("heterogeneous L6 lacks mounted topology")
    if not isinstance(combined_stack, Fixed42ConstraintStack):
        raise ReceiptError("heterogeneous L6 lacks exact combined Fixed42 rows")
    if not isinstance(combined_rank, ExactRankReceipt):
        raise ReceiptError("heterogeneous L6 lacks exact combined rank")
    if not isinstance(lane_completeness_receipts, tuple) or not all(
        isinstance(value, LaneCompletenessReceipt)
        for value in lane_completeness_receipts
    ):
        raise ReceiptError("heterogeneous L6 lane completeness is not typed")
    working = _extend_registry(
        receipt_registry,
        sensor_production.receipt_registry,
        language_replay.receipt_registry,
    )
    payload = heterogeneous_l6_assembly_receipt_payload(
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        sensor_derivation_receipt_sha256s=tuple(
            value.derivation_receipt_sha256
            for value in sensor_production.derived_ports
        ),
        language_cone_receipt_sha256=(
            language_replay.contingent_cone.authority_receipt_sha256
        ),
        combined_stack=combined_stack,
        combined_rank=combined_rank,
        lane_completeness_receipts=lane_completeness_receipts,
    )
    working = _extend_registry(working, payloads=(payload,))
    assembly = HeterogeneousL6Assembly(
        sensor_production=sensor_production,
        language_replay=language_replay,
        pre_window_state=pre_window_state,
        combined_stack=combined_stack,
        combined_rank=combined_rank,
        lane_completeness_receipts=lane_completeness_receipts,
        authority_receipt_sha256=receipt_sha256(payload),
        receipt_registry=working,
    )
    assembly.verify(topology=topology, receipt_registry=working)
    return assembly


__all__ = (
    "HETEROGENEOUS_L6_ASSEMBLY_OPERATOR_ID",
    "HeterogeneousL6Assembly",
    "assemble_heterogeneous_l6",
    "heterogeneous_l6_assembly_receipt_payload",
)
