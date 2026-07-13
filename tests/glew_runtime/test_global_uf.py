"""Focused conformance tests for the exact Global-UF v2 boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import (
    AuthorityDisposition,
    PendingGlobalUFConjunction,
    evaluate_pending_global_uf_conjunction,
)
from dsf_ai_service.glew_runtime.global_uf import (
    DSF_FIELD_ORDER,
    AdjacentDirection,
    CertifiedNonnegativeClass,
    CertifiedOperatorBasinSignature,
    CommitBasinSignature,
    ExactDSFFieldTupleReceipt,
    GlobalUFReplayOutcome,
    GlobalUFReplayRequest,
    GlobalUFReplayResponse,
    L5DispositionState,
    L6BasinClass,
    L6BasinSignature,
    L6BasisRowSignature,
    LayerBranchGateSignature,
    MountedPreWindowState,
    MountedRawObservationWindow,
    MountedSensorResolutionProfile,
    NamedSignZeroClass,
    ObservationCoordinate,
    OperatorAvailability,
    PortKernelBasinSignature,
    PortL5BasinDisposition,
    PortReplayReceipt,
    ReplayComparisonState,
    ReplayEvidenceState,
    ReplayOutcomeStatus,
    SensorCodeResolution,
    SensorIntegerObservation,
    SignZeroClass,
    StableModeBasinSignature,
    StableModeState,
    StructuralBasinSignature,
    TypedUnicodeObservation,
    enumerate_global_uf_replay_requests,
    evaluate_global_uf_validation,
    exact_dsf_field_tuple_receipt_payload,
    global_uf_replay_outcome_receipt_payload,
    port_kernel_basin_receipt_payload,
    port_replay_receipt_payload,
    pre_window_state_receipt_payload,
    raw_observation_window_receipt_payload,
    sensor_resolution_profile_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import N_START
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from tests.glew_runtime.test_full_field_commit_boundary import (
    _bundle,
    _pending_inputs,
)


def _record(payload: bytes) -> ReceiptRecord:
    return ReceiptRecord(receipt_sha256(payload), payload)


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    values = {value.digest: value.payload for value in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        prior = values.get(digest)
        if prior is not None and prior != payload:
            raise AssertionError("test receipt digest collision")
        values[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(digest, payload) for digest, payload in values.items()),
    )


@dataclass(frozen=True)
class ExactFixture:
    topology: object
    pending: PendingGlobalUFConjunction
    base_experience_receipt: str
    replay_experience_receipt: str
    alternate_replay_experience_receipt: str
    window: MountedRawObservationWindow
    resolution: MountedSensorResolutionProfile
    pre_window: MountedPreWindowState
    registry: ReceiptRegistry


@pytest.fixture(scope="module")
def exact_fixture() -> ExactFixture:
    bundle = _bundle()
    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(bundle)
    )
    topology = bundle["topology"]

    base_experience_payload = b"global-uf-v2-base-context"
    alternate_experience_payload = b"global-uf-v2-alternate-replay-context"
    sensor_coordinate = ObservationCoordinate(
        "language",
        "typed",
        0,
        "native-test-code",
    )
    typed_coordinate = ObservationCoordinate(
        "language",
        "typed",
        1,
        "typed-test-input",
    )
    sensors = (SensorIntegerObservation(sensor_coordinate, 0),)
    typed = (TypedUnicodeObservation(typed_coordinate, "remember us"),)
    window_payload = raw_observation_window_receipt_payload(
        window_id="exact-global-uf-window",
        sensor_observations=sensors,
        typed_unicode_observations=typed,
    )
    window = MountedRawObservationWindow(
        "exact-global-uf-window",
        sensors,
        typed,
        receipt_sha256(window_payload),
    )

    resolution_source_payload = b"global-uf-v2-native-resolution-source"
    resolutions = (
        SensorCodeResolution(
            sensor_coordinate,
            -1,
            1,
            Fraction(1, 16),
            receipt_sha256(resolution_source_payload),
        ),
    )
    resolution_payload = sensor_resolution_profile_receipt_payload(
        profile_id="exact-global-uf-resolution",
        observation_window_receipt_sha256=window.authority_receipt_sha256,
        resolutions=resolutions,
    )
    resolution = MountedSensorResolutionProfile(
        "exact-global-uf-resolution",
        window.authority_receipt_sha256,
        resolutions,
        receipt_sha256(resolution_payload),
    )

    state_payloads = (
        b"global-uf-v2-chemistry-state",
        b"global-uf-v2-field-state",
        b"global-uf-v2-mode-state",
        b"global-uf-v2-memory-state",
        b"global-uf-v2-l6-state",
    )
    pre_window_payload = pre_window_state_receipt_payload(
        state_id="exact-global-uf-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(state_payloads[0]),
        field_state_receipt_sha256=receipt_sha256(state_payloads[1]),
        mode_state_receipt_sha256=receipt_sha256(state_payloads[2]),
        memory_state_receipt_sha256=receipt_sha256(state_payloads[3]),
        l6_state_receipt_sha256=receipt_sha256(state_payloads[4]),
    )
    pre_window = MountedPreWindowState(
        "exact-global-uf-pre-window",
        receipt_sha256(state_payloads[0]),
        receipt_sha256(state_payloads[1]),
        receipt_sha256(state_payloads[2]),
        receipt_sha256(state_payloads[3]),
        receipt_sha256(state_payloads[4]),
        receipt_sha256(pre_window_payload),
    )
    registry = _extend(
        bundle["receipt_registry"],
        base_experience_payload,
        alternate_experience_payload,
        pending.receipt_payload,
        window_payload,
        resolution_source_payload,
        resolution_payload,
        *state_payloads,
        pre_window_payload,
    )
    return ExactFixture(
        topology=topology,
        pending=pending,
        base_experience_receipt=receipt_sha256(base_experience_payload),
        replay_experience_receipt=(
            pending.closed_experience_receipt_sha256
        ),
        alternate_replay_experience_receipt=receipt_sha256(
            alternate_experience_payload
        ),
        window=window,
        resolution=resolution,
        pre_window=pre_window,
        registry=registry,
    )


def _sign(value: Fraction) -> SignZeroClass:
    if value < 0:
        return SignZeroClass.NEGATIVE
    if value > 0:
        return SignZeroClass.POSITIVE
    return SignZeroClass.EXACT_ZERO


def _layers(
    exact_tuple: ExactDSFFieldTupleReceipt,
) -> tuple[LayerBranchGateSignature, ...]:
    secondary = tuple(
        sorted(
            (
                NamedSignZeroClass(
                    f"{exact_tuple.tuple_index:08d}:{field_name}",
                    _sign(getattr(exact_tuple, field_name)),
                )
                for field_name in DSF_FIELD_ORDER
            ),
            key=lambda value: value.coordinate_id,
        )
    )
    return tuple(
        LayerBranchGateSignature(
            layer_index,
            f"native-L{layer_index}-branch",
            (f"native-L{layer_index}-gate",),
            secondary if layer_index == 4 else (),
        )
        for layer_index in range(5)
    )


def _basin_response(
    fixture: ExactFixture,
    request: GlobalUFReplayRequest,
    *,
    exact_d_value: Fraction = Fraction(1),
    tamper_exact_receipt: bool = False,
    replay_experience_receipt: str | None = None,
) -> GlobalUFReplayResponse:
    replay_scope = (
        fixture.replay_experience_receipt
        if replay_experience_receipt is None
        else replay_experience_receipt
    )
    lane_id, port_id = fixture.topology.ordered_port_fibers[0].key
    source_observation_payload = (
        f"request-{request.request_index}:exact-source-observation".encode()
    )
    trace_payload = f"request-{request.request_index}:exact-L0-L4-trace".encode()
    l5_payload = f"request-{request.request_index}:exact-L5-governance".encode()
    port_payload = port_replay_receipt_payload(
        lane_id=lane_id,
        port_id=port_id,
        request_receipt_sha256=request.receipt_sha256,
        source_observation_receipt_sha256=receipt_sha256(
            source_observation_payload
        ),
        l0_l4_trace_receipt_sha256=receipt_sha256(trace_payload),
        l5_governance_receipt_sha256=receipt_sha256(l5_payload),
    )
    port = PortReplayReceipt(
        lane_id,
        port_id,
        request.receipt_sha256,
        receipt_sha256(source_observation_payload),
        receipt_sha256(trace_payload),
        receipt_sha256(l5_payload),
        receipt_sha256(port_payload),
    )

    tuple_payload = exact_dsf_field_tuple_receipt_payload(
        lane_id=lane_id,
        port_id=port_id,
        tuple_index=0,
        D_k=exact_d_value,
        M_k=Fraction(1, 3),
        R_rev_k=Fraction(0),
        U_star_k=Fraction(2, 5),
        C_k=Fraction(-1, 7),
        P_k=Fraction(3, 11),
        B_k=Fraction(5, 13),
        source_l0_l4_trace_receipt_sha256=receipt_sha256(trace_payload),
    )
    exact_tuple = ExactDSFFieldTupleReceipt(
        lane_id,
        port_id,
        0,
        exact_d_value,
        Fraction(1, 3),
        Fraction(0),
        Fraction(2, 5),
        Fraction(-1, 7),
        Fraction(3, 11),
        Fraction(5, 13),
        receipt_sha256(trace_payload),
        receipt_sha256(tuple_payload),
    )
    layers = _layers(exact_tuple)
    kernel_payload = port_kernel_basin_receipt_payload(
        lane_id=lane_id,
        port_id=port_id,
        layers=layers,
        exact_dsf_field_tuples=(exact_tuple,),
    )
    kernel = PortKernelBasinSignature(
        lane_id,
        port_id,
        layers,
        (exact_tuple,),
        receipt_sha256(kernel_payload),
    )
    if tamper_exact_receipt:
        tampered_tuple = replace(exact_tuple, D_k=exact_d_value + 1)
        kernel = PortKernelBasinSignature(
            lane_id,
            port_id,
            _layers(tampered_tuple),
            (tampered_tuple,),
            receipt_sha256(kernel_payload),
        )

    s_payload = f"request-{request.request_index}:exact-S-UF".encode()
    r_payload = f"request-{request.request_index}:exact-R-UF".encode()
    l5_basin_payload = f"request-{request.request_index}:L5-basin".encode()
    l6_row_payload = f"request-{request.request_index}:fixed42-row".encode()
    l6_basin_payload = f"request-{request.request_index}:fixed42-basin".encode()
    stable_payload = f"request-{request.request_index}:stable-mode".encode()
    row = L6BasisRowSignature(
        f"row-{request.request_index}",
        "exact-native-tangent",
        (Fraction(1),) + (Fraction(0),) * (N_START - 1),
        receipt_sha256(l6_row_payload),
    )
    pending = fixture.pending
    stable_mode = StableModeBasinSignature(
        StableModeState.SELECTED,
        pending.selected_mode_index,
        pending.selected_mode_receipt_sha256,
        receipt_sha256(stable_payload),
    )
    basin = StructuralBasinSignature(
        (kernel,),
        CertifiedOperatorBasinSignature(
            OperatorAvailability.AVAILABLE,
            CertifiedNonnegativeClass.CERTIFIED_POSITIVE,
            receipt_sha256(s_payload),
        ),
        CertifiedOperatorBasinSignature(
            OperatorAvailability.AVAILABLE,
            CertifiedNonnegativeClass.CERTIFIED_POSITIVE,
            receipt_sha256(r_payload),
        ),
        (
            PortL5BasinDisposition(
                lane_id,
                port_id,
                L5DispositionState.APPLIED,
                "participating",
                receipt_sha256(l5_basin_payload),
            ),
        ),
        L6BasinSignature(
            (row,),
            1,
            N_START - 1,
            (0,),
            L6BasinClass.NO_LOCK,
            receipt_sha256(l6_basin_payload),
        ),
        stable_mode,
        CommitBasinSignature(pending),
    )
    generated_payloads = (
        source_observation_payload,
        trace_payload,
        l5_payload,
        port_payload,
        tuple_payload,
        kernel_payload,
        s_payload,
        r_payload,
        l5_basin_payload,
        l6_row_payload,
        l6_basin_payload,
        stable_payload,
    )
    outcome_payload = global_uf_replay_outcome_receipt_payload(
        outcome_id=f"{request.request_id}:exact-outcome",
        status=ReplayOutcomeStatus.RESOLVED,
        reason=None,
        request_receipt_sha256=request.receipt_sha256,
        topology_authority_receipt_sha256=(
            fixture.topology.authority_receipt_sha256
        ),
        base_closed_experience_receipt_sha256=(
            request.base_closed_experience_receipt_sha256
        ),
        replay_closed_experience_receipt_sha256=replay_scope,
        observation_window_receipt_sha256=(
            request.observation_window_receipt_sha256
        ),
        sensor_resolution_profile_receipt_sha256=(
            request.sensor_resolution_profile_receipt_sha256
        ),
        pre_window_state_receipt_sha256=request.pre_window_state_receipt_sha256,
        port_replay_receipts=(port,),
        basin_signature=basin,
    )
    outcome = GlobalUFReplayOutcome(
        f"{request.request_id}:exact-outcome",
        ReplayOutcomeStatus.RESOLVED,
        None,
        request.receipt_sha256,
        fixture.topology.authority_receipt_sha256,
        request.base_closed_experience_receipt_sha256,
        replay_scope,
        request.observation_window_receipt_sha256,
        request.sensor_resolution_profile_receipt_sha256,
        request.pre_window_state_receipt_sha256,
        (port,),
        basin,
        receipt_sha256(outcome_payload),
    )
    return GlobalUFReplayResponse(
        outcome,
        tuple(_record(payload) for payload in (*generated_payloads, outcome_payload)),
    )


class ExactProvider:
    def __init__(
        self,
        fixture: ExactFixture,
        *,
        changed_request_index: int | None = None,
        tampered_request_index: int | None = None,
        mismatched_scope_request_index: int | None = None,
        missing_request_index: int | None = None,
    ) -> None:
        self.fixture = fixture
        self.changed_request_index = changed_request_index
        self.tampered_request_index = tampered_request_index
        self.mismatched_scope_request_index = mismatched_scope_request_index
        self.missing_request_index = missing_request_index

    def replay_from_immutable_pre_window(
        self,
        request: GlobalUFReplayRequest,
    ) -> GlobalUFReplayResponse | None:
        if request.request_index == self.missing_request_index:
            return None
        changed = request.request_index == self.changed_request_index
        return _basin_response(
            self.fixture,
            request,
            exact_d_value=Fraction(2) if changed else Fraction(1),
            tamper_exact_receipt=(
                request.request_index == self.tampered_request_index
            ),
            replay_experience_receipt=(
                self.fixture.alternate_replay_experience_receipt
                if request.request_index == self.mismatched_scope_request_index
                else None
            ),
        )


class Provider:
    """Exact reusable v2 provider for vertical conformance fixtures.

    A topology alone is deliberately insufficient: the caller must supply the
    real common commit conjunction evaluated with Global-UF pending.  This
    prevents a test provider from inventing a COMMIT label.
    """

    def __init__(
        self,
        topology,
        pending_conjunction: PendingGlobalUFConjunction,
    ) -> None:
        self.topology = topology
        if not isinstance(pending_conjunction, PendingGlobalUFConjunction):
            raise ReceiptError("exact replay Provider requires a pending conjunction")
        pending_conjunction.verify()
        if (
            pending_conjunction.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
        ):
            raise ReceiptError("exact replay Provider pending topology differs")
        self.pending_conjunction = pending_conjunction

    def replay_from_immutable_pre_window(
        self,
        request: GlobalUFReplayRequest,
    ) -> GlobalUFReplayResponse:
        generated: list[bytes] = [self.pending_conjunction.receipt_payload]
        ports: list[PortReplayReceipt] = []
        kernels: list[PortKernelBasinSignature] = []
        l5_dispositions: list[PortL5BasinDisposition] = []

        for port_index, fiber in enumerate(self.topology.ordered_port_fibers):
            prefix = (
                f"exact-provider:{request.request_index}:"
                f"{fiber.lane_id}:{fiber.port_id}"
            )
            observation_payload = f"{prefix}:observation".encode()
            trace_payload = f"{prefix}:L0-L4-trace".encode()
            l5_payload = f"{prefix}:L5-governance".encode()
            port_payload = port_replay_receipt_payload(
                lane_id=fiber.lane_id,
                port_id=fiber.port_id,
                request_receipt_sha256=request.receipt_sha256,
                source_observation_receipt_sha256=receipt_sha256(
                    observation_payload
                ),
                l0_l4_trace_receipt_sha256=receipt_sha256(trace_payload),
                l5_governance_receipt_sha256=receipt_sha256(l5_payload),
            )
            ports.append(
                PortReplayReceipt(
                    fiber.lane_id,
                    fiber.port_id,
                    request.receipt_sha256,
                    receipt_sha256(observation_payload),
                    receipt_sha256(trace_payload),
                    receipt_sha256(l5_payload),
                    receipt_sha256(port_payload),
                )
            )
            values = tuple(
                Fraction((port_index + 1) * (field_index + 1), field_index + 2)
                for field_index in range(len(DSF_FIELD_ORDER))
            )
            tuple_payload = exact_dsf_field_tuple_receipt_payload(
                lane_id=fiber.lane_id,
                port_id=fiber.port_id,
                tuple_index=0,
                D_k=values[0],
                M_k=values[1],
                R_rev_k=values[2],
                U_star_k=values[3],
                C_k=values[4],
                P_k=values[5],
                B_k=values[6],
                source_l0_l4_trace_receipt_sha256=receipt_sha256(trace_payload),
            )
            exact_tuple = ExactDSFFieldTupleReceipt(
                fiber.lane_id,
                fiber.port_id,
                0,
                *values,
                receipt_sha256(trace_payload),
                receipt_sha256(tuple_payload),
            )
            layers = _layers(exact_tuple)
            kernel_payload = port_kernel_basin_receipt_payload(
                lane_id=fiber.lane_id,
                port_id=fiber.port_id,
                layers=layers,
                exact_dsf_field_tuples=(exact_tuple,),
            )
            kernels.append(
                PortKernelBasinSignature(
                    fiber.lane_id,
                    fiber.port_id,
                    layers,
                    (exact_tuple,),
                    receipt_sha256(kernel_payload),
                )
            )
            l5_basin_payload = f"{prefix}:L5-basin".encode()
            l5_dispositions.append(
                PortL5BasinDisposition(
                    fiber.lane_id,
                    fiber.port_id,
                    L5DispositionState.APPLIED,
                    "participating",
                    receipt_sha256(l5_basin_payload),
                )
            )
            generated.extend(
                (
                    observation_payload,
                    trace_payload,
                    l5_payload,
                    port_payload,
                    tuple_payload,
                    kernel_payload,
                    l5_basin_payload,
                )
            )

        prefix = f"exact-provider:{request.request_index}"
        s_payload = f"{prefix}:S-UF".encode()
        r_payload = f"{prefix}:R-UF".encode()
        l6_row_payload = f"{prefix}:fixed42-row".encode()
        l6_payload = f"{prefix}:fixed42-basin".encode()
        stable_payload = f"{prefix}:stable-mode".encode()
        row = L6BasisRowSignature(
            f"row-{request.request_index}",
            "exact-native-tangent",
            (Fraction(1),) + (Fraction(0),) * (N_START - 1),
            receipt_sha256(l6_row_payload),
        )
        pending = self.pending_conjunction
        if pending.ready_except_global_uf:
            stable = StableModeBasinSignature(
                StableModeState.SELECTED,
                pending.selected_mode_index,
                pending.selected_mode_receipt_sha256,
                receipt_sha256(stable_payload),
            )
        else:
            stable = StableModeBasinSignature(
                StableModeState.NO_STABLE_MODE,
                None,
                None,
                receipt_sha256(stable_payload),
            )
        basin = StructuralBasinSignature(
            tuple(kernels),
            CertifiedOperatorBasinSignature(
                OperatorAvailability.AVAILABLE,
                CertifiedNonnegativeClass.CERTIFIED_POSITIVE,
                receipt_sha256(s_payload),
            ),
            CertifiedOperatorBasinSignature(
                OperatorAvailability.AVAILABLE,
                CertifiedNonnegativeClass.CERTIFIED_POSITIVE,
                receipt_sha256(r_payload),
            ),
            tuple(l5_dispositions),
            L6BasinSignature(
                (row,),
                1,
                N_START - 1,
                (0,),
                L6BasinClass.NO_LOCK,
                receipt_sha256(l6_payload),
            ),
            stable,
            CommitBasinSignature(pending),
        )
        generated.extend(
            (s_payload, r_payload, l6_row_payload, l6_payload, stable_payload)
        )
        outcome_payload = global_uf_replay_outcome_receipt_payload(
            outcome_id=f"{request.request_id}:exact-provider-outcome",
            status=ReplayOutcomeStatus.RESOLVED,
            reason=None,
            request_receipt_sha256=request.receipt_sha256,
            topology_authority_receipt_sha256=(
                self.topology.authority_receipt_sha256
            ),
            base_closed_experience_receipt_sha256=(
                request.base_closed_experience_receipt_sha256
            ),
            replay_closed_experience_receipt_sha256=(
                pending.closed_experience_receipt_sha256
            ),
            observation_window_receipt_sha256=(
                request.observation_window_receipt_sha256
            ),
            sensor_resolution_profile_receipt_sha256=(
                request.sensor_resolution_profile_receipt_sha256
            ),
            pre_window_state_receipt_sha256=(
                request.pre_window_state_receipt_sha256
            ),
            port_replay_receipts=tuple(ports),
            basin_signature=basin,
        )
        outcome = GlobalUFReplayOutcome(
            f"{request.request_id}:exact-provider-outcome",
            ReplayOutcomeStatus.RESOLVED,
            None,
            request.receipt_sha256,
            self.topology.authority_receipt_sha256,
            request.base_closed_experience_receipt_sha256,
            pending.closed_experience_receipt_sha256,
            request.observation_window_receipt_sha256,
            request.sensor_resolution_profile_receipt_sha256,
            request.pre_window_state_receipt_sha256,
            tuple(ports),
            basin,
            receipt_sha256(outcome_payload),
        )
        generated.append(outcome_payload)
        records = tuple(
            _record(payload)
            for payload in dict.fromkeys(generated)
        )
        return GlobalUFReplayResponse(outcome, records)


def _evaluate(fixture: ExactFixture, provider: ExactProvider):
    return evaluate_global_uf_validation(
        authority_id="exact-global-uf-v2",
        topology=fixture.topology,
        closed_experience_receipt_sha256=fixture.base_experience_receipt,
        observation_window=fixture.window,
        sensor_resolution_profile=fixture.resolution,
        pre_window_state=fixture.pre_window,
        replay_provider=provider,
        receipt_registry=fixture.registry,
    )


def test_enumeration_is_complete_and_keeps_base_context_distinct(exact_fixture):
    requests = enumerate_global_uf_replay_requests(
        topology=exact_fixture.topology,
        closed_experience_receipt_sha256=exact_fixture.base_experience_receipt,
        observation_window=exact_fixture.window,
        sensor_resolution_profile=exact_fixture.resolution,
        pre_window_state=exact_fixture.pre_window,
        receipt_registry=exact_fixture.registry,
    )

    assert len(requests) == 3
    assert requests[0].direction is None
    assert tuple(value.direction for value in requests[1:]) == (
        AdjacentDirection.NEGATIVE,
        AdjacentDirection.POSITIVE,
    )
    assert all(
        value.base_closed_experience_receipt_sha256
        == exact_fixture.base_experience_receipt
        for value in requests
    )
    assert (
        exact_fixture.base_experience_receipt
        != exact_fixture.replay_experience_receipt
    )


def test_pass_requires_exact_tuples_and_verified_pending_conjunction(exact_fixture):
    result = _evaluate(exact_fixture, ExactProvider(exact_fixture))

    assert result.authority.disposition is AuthorityDisposition.PASS
    assert tuple(
        value.comparison_state for value in result.source_receipt.entries
    ) == (
        ReplayComparisonState.BASELINE,
        ReplayComparisonState.EXACT_MATCH,
        ReplayComparisonState.EXACT_MATCH,
    )
    assert all(
        value.replay_closed_experience_receipt_sha256
        == exact_fixture.replay_experience_receipt
        for value in result.source_receipt.entries
    )
    base_payload = result.receipt_registry.resolve(
        result.source_receipt.entries[0].structural_basin_receipt_sha256,
        "test exact structural basin",
    )
    assert b'"exact_dsf_field_tuples"' in base_payload
    assert b'"exact_fields"' in base_payload
    assert b'"secondary_semialgebraic_coordinate_classes"' in base_payload
    result.verify()


def test_positive_to_different_positive_exact_value_is_counterexample(exact_fixture):
    result = _evaluate(
        exact_fixture,
        ExactProvider(exact_fixture, changed_request_index=2),
    )

    assert result.authority.disposition is AuthorityDisposition.FAIL
    assert result.source_receipt.entries[2].comparison_state is (
        ReplayComparisonState.COUNTEREXAMPLE
    )
    assert result.source_receipt.entries[2].evidence_state is (
        ReplayEvidenceState.RESOLVED
    )


def test_exact_tuple_receipt_tamper_is_invalid_not_a_pass(exact_fixture):
    result = _evaluate(
        exact_fixture,
        ExactProvider(exact_fixture, tampered_request_index=1),
    )

    assert result.authority.disposition is AuthorityDisposition.UNKNOWN
    assert result.source_receipt.entries[1].evidence_state is (
        ReplayEvidenceState.INVALID
    )
    assert result.source_receipt.entries[1].comparison_state is (
        ReplayComparisonState.UNAVAILABLE
    )


def test_pending_conjunction_tamper_and_wrong_replay_scope_fail_closed(
    exact_fixture,
):
    tampered = replace(
        exact_fixture.pending,
        receipt_payload=b'{"tampered":true}',
    )
    with pytest.raises(ReceiptError, match="pending Global-UF conjunction"):
        CommitBasinSignature(tampered)

    result = _evaluate(
        exact_fixture,
        ExactProvider(exact_fixture, mismatched_scope_request_index=1),
    )
    assert result.authority.disposition is AuthorityDisposition.UNKNOWN
    assert result.source_receipt.entries[1].evidence_state is (
        ReplayEvidenceState.INVALID
    )


def test_missing_replay_remains_unknown(exact_fixture):
    result = _evaluate(
        exact_fixture,
        ExactProvider(exact_fixture, missing_request_index=2),
    )

    assert result.authority.disposition is AuthorityDisposition.UNKNOWN
    assert result.source_receipt.entries[2].evidence_state is (
        ReplayEvidenceState.MISSING
    )

