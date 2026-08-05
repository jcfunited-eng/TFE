"""Exact six-lane L6 assembly and provider-boundary tests."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    ClosedExperienceProviderBundle,
    assemble_closed_experience_provider_bundle,
)
from dsf_ai_service.glew_runtime.experience_origin import ExperienceOriginKind
from dsf_ai_service.glew_runtime.heterogeneous_l6 import (
    HeterogeneousL6Assembly,
    assemble_heterogeneous_l6,
)
from dsf_ai_service.glew_runtime.l6 import (
    ConstraintRow,
    Fixed42ConstraintStack,
    L6Lane,
    NativeConstraintCovector,
    exact_rank_receipt,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.story_global_uf_basin import (
    evaluate_story_global_uf,
)
from tests.glew_runtime.test_story_global_uf_basin import (
    _mount_authorities,
    _mounted_six_lane_preparation,
)


@pytest.fixture(scope="module")
def six_lane_environment():
    preparation, topology, pre_window, profile, boundary, _, registry = (
        _mounted_six_lane_preparation()
    )
    assembly = assemble_heterogeneous_l6(
        sensor_production=preparation.sensor_l6_production,
        language_replay=preparation.language_replay,
        pre_window_state=pre_window,
        combined_stack=preparation.fixed42_stack,
        combined_rank=preparation.fixed42_rank,
        lane_completeness_receipts=(
            preparation.lane_completeness_receipts
        ),
        topology=topology,
        receipt_registry=registry,
    )
    return preparation, topology, pre_window, profile, boundary, assembly


def test_exact_six_lane_assembly_reaches_closed_experience_provider(
    six_lane_environment,
):
    preparation, topology, pre_window, profile, boundary, assembly = (
        six_lane_environment
    )
    mounted, registry = _mount_authorities(
        preparation=preparation,
        topology=topology,
        profile=profile,
        boundary=boundary,
        origin_kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        registry=assembly.receipt_registry,
    )
    global_result = evaluate_story_global_uf(
        authority_id="heterogeneous-L6-provider-global-UF",
        preparation=preparation,
        mounted_authorities=mounted,
        topology=topology,
        pre_window_state=pre_window,
        receipt_registry=registry,
    )
    context = preparation.contexts[0]
    authority = mounted[0]
    # The provider assembler demands the actual physical L6 production,
    # produced downstream of the sealed experience registry.
    from dsf_ai_service.glew_runtime.physical_l6_tangents import (
        produce_physical_l6_tangents,
    )

    replay_bundles = tuple(
        item.bundle
        for item in preparation.story_replay_results
        if item.bundle is not None
    )
    physical_production = produce_physical_l6_tangents(
        bundles=replay_bundles,
        pre_window_state=pre_window,
        receipt_registry=global_result.receipt_registry,
    )
    bundle = assemble_closed_experience_provider_bundle(
        sealed=context.sealed,
        topology=topology,
        experience_origin=authority.origin,
        safe_mode_evaluation=authority.safe_mode_evaluation,
        event_support_evaluation=authority.event_support_evaluation,
        global_uf_validation=global_result.validation,
        l6_production=physical_production,
        l6_predicates=authority.l6_predicates,
        l6_evaluation=authority.l6_evaluation,
        l6_scope=authority.l6_scope,
        receipt_registry=physical_production.receipt_registry,
    )

    assert isinstance(bundle, ClosedExperienceProviderBundle)
    assert bundle.l6_production is physical_production
    assert isinstance(assembly, HeterogeneousL6Assembly)
    assert tuple(
        value.lane for value in assembly.lane_completeness_receipts
    ) == tuple(L6Lane)
    assert any(
        row.provenance.lane is L6Lane.LANGUAGE
        for row in assembly.combined_stack.rows
    )
    assert all(
        value.profile.lane is not L6Lane.LANGUAGE
        for value in assembly.sensor_production.derived_ports
    )


def test_missing_language_lane_completeness_fails_closed(
    six_lane_environment,
):
    preparation, topology, pre_window, _, _, assembly = six_lane_environment
    incomplete = tuple(
        value
        for value in preparation.lane_completeness_receipts
        if value.lane is not L6Lane.LANGUAGE
    )

    with pytest.raises(
        ReceiptError,
        match="completeness does not cover six lanes",
    ):
        assemble_heterogeneous_l6(
            sensor_production=preparation.sensor_l6_production,
            language_replay=preparation.language_replay,
            pre_window_state=pre_window,
            combined_stack=preparation.fixed42_stack,
            combined_rank=preparation.fixed42_rank,
            lane_completeness_receipts=incomplete,
            topology=topology,
            receipt_registry=assembly.receipt_registry,
        )


def test_language_secant_row_tamper_fails_before_combined_rank(
    six_lane_environment,
):
    preparation, topology, pre_window, _, _, assembly = six_lane_environment
    language = preparation.language_replay
    cone = language.contingent_cone
    direction_index = next(
        index for index, value in enumerate(cone.directions) if value.row is not None
    )
    direction = cone.directions[direction_index]
    assert direction.row is not None
    coefficients = list(direction.row.native_coefficients)
    coefficients[0] += Fraction(1)
    altered_row = ConstraintRow(
        NativeConstraintCovector(
            direction.row.provenance,
            tuple(coefficients),
        )
    )
    altered_direction = replace(direction, row=altered_row)
    altered_directions = tuple(
        altered_direction if index == direction_index else value
        for index, value in enumerate(cone.directions)
    )
    altered_cone = replace(
        cone,
        directions=altered_directions,
        fixed42_stack=Fixed42ConstraintStack(
            tuple(
                value.row for value in altered_directions if value.row is not None
            )
        ),
    )
    altered_language = replace(language, contingent_cone=altered_cone)
    altered_combined = Fixed42ConstraintStack(
        tuple(
            sorted(
                (
                    *preparation.sensor_l6_production.candidate_constraints.stack.rows,
                    *altered_cone.fixed42_stack.rows,
                ),
                key=lambda row: row.provenance.identity,
            )
        )
    )

    with pytest.raises(
        ReceiptError,
        match="language Fixed42 row differs from its secant",
    ):
        assemble_heterogeneous_l6(
            sensor_production=preparation.sensor_l6_production,
            language_replay=altered_language,
            pre_window_state=pre_window,
            combined_stack=altered_combined,
            combined_rank=exact_rank_receipt(altered_combined),
            lane_completeness_receipts=(
                preparation.lane_completeness_receipts
            ),
            topology=topology,
            receipt_registry=assembly.receipt_registry,
        )


def test_omitted_language_direction_fails_closed(
    six_lane_environment,
):
    preparation, topology, pre_window, _, _, assembly = six_lane_environment
    language = preparation.language_replay
    cone = replace(
        language.contingent_cone,
        directions=language.contingent_cone.directions[:-1],
    )

    with pytest.raises(
        ReceiptError,
        match="omitted an admissible direction",
    ):
        assemble_heterogeneous_l6(
            sensor_production=preparation.sensor_l6_production,
            language_replay=replace(language, contingent_cone=cone),
            pre_window_state=pre_window,
            combined_stack=preparation.fixed42_stack,
            combined_rank=preparation.fixed42_rank,
            lane_completeness_receipts=(
                preparation.lane_completeness_receipts
            ),
            topology=topology,
            receipt_registry=assembly.receipt_registry,
        )
