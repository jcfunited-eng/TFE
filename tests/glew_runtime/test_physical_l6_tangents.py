from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import (
    MountedPreWindowState,
    pre_window_state_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import (
    ActiveLaneState,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    evaluate_l6,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.physical_l6_tangents import (
    ExactL4Response,
    LanguageTritCoordinate,
    MountedNativePerturbationProfile,
    MountedNativeResponseSet,
    MountedSameBranchCellProof,
    NativeL4ReplayResponse,
    NativePortReplayBundle,
    NativeReplayCase,
    NativeReplayCaseKind,
    PhysicalTangentProductionStatus,
    SensorNativeCoordinate,
    TypedTrit,
    enumerate_native_replay_cases,
    native_l4_replay_response_receipt_payload,
    native_perturbation_profile_receipt_payload,
    native_response_set_receipt_payload,
    produce_physical_l6_tangents,
    same_branch_cell_proof_receipt_payload,
)


ZERO7 = tuple(Fraction(0) for _ in range(7))


@dataclass(frozen=True)
class Experiment:
    state: MountedPreWindowState
    bundles: tuple[NativePortReplayBundle, ...]
    registry: ReceiptRegistry


def _add(left: tuple[Fraction, ...], right: tuple[Fraction, ...]):
    return tuple(a + b for a, b in zip(left, right, strict=True))


def _scale(vector: tuple[Fraction, ...], scale: Fraction):
    return tuple(value * scale for value in vector)


def _unit(index: int) -> tuple[Fraction, ...]:
    return tuple(Fraction(int(value == index)) for value in range(7))


def _l4(values: tuple[Fraction, ...]) -> ExactL4Response:
    return ExactL4Response(*values)


def _state() -> tuple[MountedPreWindowState, tuple[bytes, ...]]:
    state_payloads = (
        b"physical-l6-chemistry-state",
        b"physical-l6-field-state",
        b"physical-l6-mode-state",
        b"physical-l6-memory-state",
        b"physical-l6-l6-state",
    )
    binding = pre_window_state_receipt_payload(
        state_id="physical-l6-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(state_payloads[0]),
        field_state_receipt_sha256=receipt_sha256(state_payloads[1]),
        mode_state_receipt_sha256=receipt_sha256(state_payloads[2]),
        memory_state_receipt_sha256=receipt_sha256(state_payloads[3]),
        l6_state_receipt_sha256=receipt_sha256(state_payloads[4]),
    )
    return (
        MountedPreWindowState(
            "physical-l6-pre-window",
            receipt_sha256(state_payloads[0]),
            receipt_sha256(state_payloads[1]),
            receipt_sha256(state_payloads[2]),
            receipt_sha256(state_payloads[3]),
            receipt_sha256(state_payloads[4]),
            receipt_sha256(binding),
        ),
        (*state_payloads, binding),
    )


def _profile(
    lane: L6Lane,
    payloads: list[bytes],
) -> MountedNativePerturbationProfile:
    provider_id = f"{lane.value}-exact-native-provider"
    native_port_id = f"{lane.value}-native-port"
    if lane is L6Lane.LANGUAGE:
        source = b"language-typed-trit-perturbation-authority"
        payloads.append(source)
        sensors = ()
        trits = (
            LanguageTritCoordinate(
                "utterance-trit",
                TypedTrit.QUIESCENT,
                receipt_sha256(source),
            ),
        )
    else:
        coordinate_count = 3 if lane is L6Lane.SIGHT else 1
        sensor_values = []
        for index in range(coordinate_count):
            source = f"{lane.value}-sensor-{index}-code-authority".encode()
            payloads.append(source)
            sensor_values.append(
                SensorNativeCoordinate(
                    f"native-coordinate-{index}",
                    1,
                    0,
                    2,
                    Fraction(1, 8 + index),
                    receipt_sha256(source),
                )
            )
        sensors = tuple(sensor_values)
        trits = ()
    profile_payload = native_perturbation_profile_receipt_payload(
        profile_id=f"{lane.value}-physical-profile",
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        sensor_coordinates=sensors,
        language_trit_coordinates=trits,
    )
    payloads.append(profile_payload)
    return MountedNativePerturbationProfile(
        f"{lane.value}-physical-profile",
        lane,
        provider_id,
        native_port_id,
        sensors,
        trits,
        receipt_sha256(profile_payload),
    )


def _native_displacements(
    profile: MountedNativePerturbationProfile,
    case: NativeReplayCase,
) -> tuple[Fraction, ...]:
    if profile.lane is L6Lane.LANGUAGE:
        by_id = {value.coordinate_id: value for value in case.language_trits}
        return tuple(
            Fraction(int(by_id[value.coordinate_id].trit) - int(value.base_trit))
            for value in profile.language_trit_coordinates
        )
    by_id = {value.coordinate_id: value for value in case.sensor_codes}
    return tuple(
        Fraction(by_id[value.coordinate_id].raw_code - value.base_code)
        * value.physical_quantum
        for value in profile.sensor_coordinates
    )


def _response_law(
    profile: MountedNativePerturbationProfile,
    case: NativeReplayCase,
    *,
    expanded_sight_geometry: bool,
) -> ExactL4Response:
    base = tuple(Fraction(10 + index, 3) for index in range(7))
    displacement = _native_displacements(profile, case)
    response = base
    common = tuple(Fraction(index + 1) for index in range(7))
    for coordinate_index, value in enumerate(displacement):
        if expanded_sight_geometry and profile.lane is L6Lane.SIGHT:
            if coordinate_index == 0:
                linear, bend = _unit(0), _unit(1)
            elif coordinate_index == 1:
                linear, bend = _unit(2), _unit(3)
            else:
                linear, bend = _unit(4), ZERO7
        else:
            linear, bend = common, ZERO7
        response = _add(response, _scale(linear, value))
        response = _add(response, _scale(bend, value * value))
    return _l4(response)


def _bundle(
    profile: MountedNativePerturbationProfile,
    state: MountedPreWindowState,
    payloads: list[bytes],
    *,
    expanded_sight_geometry: bool,
) -> NativePortReplayBundle:
    cases = enumerate_native_replay_cases(profile, state)
    responses = []
    branch_id = f"{profile.lane.value}-same-l4-branch"
    cell_id = f"{profile.lane.value}-same-l4-cell"
    for case in cases:
        source = (
            f"{profile.profile_id}:{case.case_index}:"
            "independent-exact-response-law"
        ).encode()
        payloads.append(source)
        response_payload = native_l4_replay_response_receipt_payload(
            response_id=f"{profile.profile_id}:response:{case.case_index}",
            lane=profile.lane,
            provider_id=profile.provider_id,
            native_port_id=profile.native_port_id,
            case_receipt_sha256=case.receipt_sha256,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=state.authority_receipt_sha256,
            branch_id=branch_id,
            cell_id=cell_id,
            l4_response=_response_law(
                profile,
                case,
                expanded_sight_geometry=expanded_sight_geometry,
            ),
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        payloads.append(response_payload)
        responses.append(
            NativeL4ReplayResponse(
                f"{profile.profile_id}:response:{case.case_index}",
                profile.lane,
                profile.provider_id,
                profile.native_port_id,
                case.receipt_sha256,
                profile.authority_receipt_sha256,
                state.authority_receipt_sha256,
                branch_id,
                cell_id,
                _response_law(
                    profile,
                    case,
                    expanded_sight_geometry=expanded_sight_geometry,
                ),
                receipt_sha256(source),
                receipt_sha256(response_payload),
            )
        )
    response_tuple = tuple(responses)
    completeness_source = (
        f"{profile.profile_id}:all-native-cases-executed-exactly"
    ).encode()
    payloads.append(completeness_source)
    response_set_payload = native_response_set_receipt_payload(
        response_set_id=f"{profile.profile_id}:responses",
        lane=profile.lane,
        provider_id=profile.provider_id,
        native_port_id=profile.native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=state.authority_receipt_sha256,
        responses=response_tuple,
        source_completeness_receipt_sha256=receipt_sha256(completeness_source),
    )
    payloads.append(response_set_payload)
    response_set = MountedNativeResponseSet(
        f"{profile.profile_id}:responses",
        profile.lane,
        profile.provider_id,
        profile.native_port_id,
        profile.authority_receipt_sha256,
        state.authority_receipt_sha256,
        response_tuple,
        receipt_sha256(completeness_source),
        receipt_sha256(response_set_payload),
    )

    branch_source = f"{profile.profile_id}:same-branch-cell-operator".encode()
    payloads.append(branch_source)
    branch_payload = same_branch_cell_proof_receipt_payload(
        proof_id=f"{profile.profile_id}:same-branch-cell",
        lane=profile.lane,
        provider_id=profile.provider_id,
        native_port_id=profile.native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=state.authority_receipt_sha256,
        branch_id=branch_id,
        cell_id=cell_id,
        response_receipt_sha256s=tuple(
            value.receipt_sha256 for value in response_tuple
        ),
        source_operator_receipt_sha256=receipt_sha256(branch_source),
    )
    payloads.append(branch_payload)
    proof = MountedSameBranchCellProof(
        f"{profile.profile_id}:same-branch-cell",
        profile.lane,
        profile.provider_id,
        profile.native_port_id,
        profile.authority_receipt_sha256,
        state.authority_receipt_sha256,
        branch_id,
        cell_id,
        tuple(value.receipt_sha256 for value in response_tuple),
        receipt_sha256(branch_source),
        receipt_sha256(branch_payload),
    )
    return NativePortReplayBundle(profile, response_set, proof)


def _experiment(*, expanded_sight_geometry: bool) -> Experiment:
    profile_binding = b"physical-l6-test-profile-binding"
    state, state_payloads = _state()
    payloads = list(state_payloads)
    bundles = []
    for lane in (
        L6Lane.LANGUAGE,
        L6Lane.SIGHT,
        L6Lane.SOUND,
        L6Lane.TOUCH,
        L6Lane.SMELL,
    ):
        profile = _profile(lane, payloads)
        bundles.append(
            _bundle(
                profile,
                state,
                payloads,
                expanded_sight_geometry=expanded_sight_geometry,
            )
        )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_binding,
        receipt_payloads=tuple(payloads),
    )
    return Experiment(state, tuple(bundles), registry)


def _evaluate_from_production(production):
    assert production.candidate_constraints is not None
    assert production.candidate_constraints.stack is not None
    completeness = {
        value.lane: value.receipt_sha256
        for value in production.lane_completeness_receipts
    }
    base_u_star = {
        value.profile.lane: value.response_set.responses[0].l4_response.U_star_k
        for value in production.derived_ports
    }
    lane_states = tuple(
        ActiveLaneState(
            lane,
            base_u_star[lane],
            True,
            completeness[lane],
        )
        for lane in completeness
    )
    return evaluate_l6(
        production.candidate_constraints.stack,
        L6PredicateInputs(lane_states, True),
        production.receipt_registry,
    )


def test_exact_replay_geometry_naturally_changes_rank_and_lock() -> None:
    quiet_experiment = _experiment(expanded_sight_geometry=False)
    quiet = produce_physical_l6_tangents(
        bundles=quiet_experiment.bundles,
        pre_window_state=quiet_experiment.state,
        receipt_registry=quiet_experiment.registry,
    )
    assert quiet.status is PhysicalTangentProductionStatus.KNOWN
    assert quiet.rank_receipt is not None
    assert quiet.rank_receipt.rank == 30
    quiet_l6 = _evaluate_from_production(quiet)
    assert quiet_l6.status is L6EvaluationStatus.LOCK

    expanded_experiment = _experiment(expanded_sight_geometry=True)
    expanded = produce_physical_l6_tangents(
        bundles=expanded_experiment.bundles,
        pre_window_state=expanded_experiment.state,
        receipt_registry=expanded_experiment.registry,
    )
    assert expanded.status is PhysicalTangentProductionStatus.KNOWN
    assert expanded.rank_receipt is not None
    assert expanded.rank_receipt.rank == 26
    expanded_l6 = _evaluate_from_production(expanded)
    assert expanded_l6.status is L6EvaluationStatus.NO_LOCK

    sight = next(
        value for value in expanded.derived_ports if value.profile.lane is L6Lane.SIGHT
    )
    assert len(sight.tangent) == 7
    assert len(sight.tangent[0]) == 6
    assert expanded.receipt_registry.resolve(
        sight.derivation_receipt_sha256,
        "exact tangent derivation receipt",
    )


def test_language_uses_only_typed_trit_replays() -> None:
    experiment = _experiment(expanded_sight_geometry=False)
    language = experiment.bundles[0].profile
    cases = enumerate_native_replay_cases(language, experiment.state)

    assert tuple(value.kind for value in cases) == (
        NativeReplayCaseKind.BASE,
        NativeReplayCaseKind.LANGUAGE_TYPED_TRIT,
        NativeReplayCaseKind.LANGUAGE_TYPED_TRIT,
    )
    assert all(not value.sensor_codes for value in cases)
    assert tuple(value.native_delta for value in cases) == (
        Fraction(0),
        Fraction(-1),
        Fraction(1),
    )

    sensor_source = b"forbidden-language-sensor-source"
    with pytest.raises(ReceiptError, match="forbids sensor codes"):
        MountedNativePerturbationProfile(
            "bad-language-profile",
            L6Lane.LANGUAGE,
            "bad-language-provider",
            "bad-language-port",
            (
                SensorNativeCoordinate(
                    "wrong-code",
                    0,
                    -1,
                    1,
                    Fraction(1),
                    receipt_sha256(sensor_source),
                ),
            ),
            (),
            "0" * 64,
        )


def test_missing_response_or_branch_proof_is_unknown_without_partial_rows() -> None:
    experiment = _experiment(expanded_sight_geometry=False)
    first = experiment.bundles[0]
    assert first.response_set is not None

    incomplete_set = replace(
        first.response_set,
        responses=first.response_set.responses[:-1],
    )
    incomplete = (
        replace(first, response_set=incomplete_set),
        *experiment.bundles[1:],
    )
    missing_response = produce_physical_l6_tangents(
        bundles=incomplete,
        pre_window_state=experiment.state,
        receipt_registry=experiment.registry,
    )
    assert missing_response.status is PhysicalTangentProductionStatus.UNKNOWN
    assert missing_response.candidate_constraints is None
    assert missing_response.rank_receipt is None
    assert "required adjacent native response" in missing_response.reason

    no_branch = (
        replace(first, branch_cell_proof=None),
        *experiment.bundles[1:],
    )
    missing_branch = produce_physical_l6_tangents(
        bundles=no_branch,
        pre_window_state=experiment.state,
        receipt_registry=experiment.registry,
    )
    assert missing_branch.status is PhysicalTangentProductionStatus.UNKNOWN
    assert missing_branch.candidate_constraints is None
    assert "same-branch/cell proof is missing" in missing_branch.reason


def test_response_state_tamper_is_unknown_and_never_becomes_geometry() -> None:
    experiment = _experiment(expanded_sight_geometry=False)
    first = experiment.bundles[0]
    assert first.response_set is not None
    response = first.response_set.responses[1]
    tampered_response = replace(
        response,
        pre_window_state_receipt_sha256="f" * 64,
    )
    response_set = replace(
        first.response_set,
        responses=(
            first.response_set.responses[0],
            tampered_response,
            *first.response_set.responses[2:],
        ),
    )
    result = produce_physical_l6_tangents(
        bundles=(replace(first, response_set=response_set), *experiment.bundles[1:]),
        pre_window_state=experiment.state,
        receipt_registry=experiment.registry,
    )
    assert result.status is PhysicalTangentProductionStatus.UNKNOWN
    assert result.candidate_constraints is None
    assert "another pre-window state" in result.reason
