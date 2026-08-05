from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    PAIRED_SOURCE_RELEVANCE_RULE,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.physical_internal_body_state import (
    create_embodiment_proprioceptive_internal_body_authority,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    ContributionState,
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    WholeOrganismEpisodeAuthority,
    create_mounted_mechanism_manifest,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    ExactWholeOrganismRecoveryOwner,
    NEGATIVE_SPACE_RULE,
    QUIESCENT_SEMANTICS,
    RecoveryMomentState,
)


RECOVERY_KEY = b"whole-organism-recovery-owner-test-key-v1"
BODY_KEY = b"whole-organism-recovery-body-test-key-v1"
EPISODE_KEY = b"whole-organism-recovery-episode-test-key-v1"
TOPOLOGY_RECEIPT = hashlib.sha256(
    b"whole-organism-recovery-test-topology"
).hexdigest()


def _body_owner():
    return create_embodiment_proprioceptive_internal_body_authority(
        authority_key=BODY_KEY,
        world_observation_receipt_sha256=hashlib.sha256(
            b"whole-organism-recovery-world-observation"
        ).hexdigest(),
        position_x_mm=Fraction(0),
        position_y_mm=Fraction(0),
        position_z_mm=Fraction(0),
        supported_load_grams=Fraction(0),
    )


def _settlement(
    label: str,
    *,
    negative_space: bool,
    start: Fraction = Fraction(0),
):
    sample_count = 64
    source_times = tuple(
        start + Fraction(index, 256)
        for index in range(sample_count)
    )
    if negative_space:
        signal = (0.0,) * sample_count
        relevance = (Fraction(0),) * sample_count
        relevance_rule = PAIRED_SOURCE_RELEVANCE_RULE
        relevance_origin = f"{label}-physical-relevance-origin"
    else:
        signal = tuple(
            math.sin(2 * math.pi * 7 * index / 256)
            for index in range(sample_count)
        )
        relevance = None
        relevance_rule = "exact-unit-source-relevance.v1"
        relevance_origin = None
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id=f"{label}-camera",
        substream_id=f"{label}-retinal-field",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("retinal-axis", "retinal-center"),
        ),
        physical_quantity="irradiance",
        physical_unit="normalized-irradiance",
        source_times=source_times,
        normalized_signal=signal,
        phase_turns=(Fraction(0),) * sample_count,
        source_relevance=relevance,
        source_relevance_rule=relevance_rule,
        source_relevance_origin_substream_id=relevance_origin,
    )
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_six_sense_full_field(
        assembly_id=f"whole-organism-recovery-{label}",
        source_time_start=start,
        source_time_end=start + Fraction(sample_count, 256),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(f"recovery-test:{label}",),
    )


def _episode_authority() -> WholeOrganismEpisodeAuthority:
    mechanisms = []
    receptor_ids = []
    for sense in SENSE_ORDER:
        mechanism_id = f"receptor:{sense.value}"
        receptor_ids.append(mechanism_id)
        mechanisms.append(MountedMechanismSpec(
            mechanism_id=mechanism_id,
            kind=MechanismKind.RECEPTOR_FAMILY,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema=(
                "test.whole_organism.recovery.receptor."
                f"{sense.value}.v1"
            ),
            parent_mechanism_ids=(),
            sense=sense.value,
            binds_full_field_roots=True,
            physical_quantity=f"{sense.value}-physical-quantity",
            physical_unit=f"{sense.value}-physical-unit",
            physical_extent=f"{sense.value}-physical-extent",
            causal_clock="exact-source-time",
            transduction_authority_receipt_sha256=(
                TOPOLOGY_RECEIPT
            ),
            custody_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        ))
    mechanisms.append(MountedMechanismSpec(
        mechanism_id="state:recovery",
        kind=MechanismKind.STATEFUL,
        availability=MechanismAvailability.AVAILABLE,
        evidence_schema="test.whole_organism.recovery.state.v1",
        parent_mechanism_ids=tuple(sorted(receptor_ids)),
        binds_full_field_roots=True,
    ))
    manifest = create_mounted_mechanism_manifest(
        authority_key=EPISODE_KEY,
        manifest_id="test-whole-organism-recovery-manifest-v1",
        topology_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        mechanisms=mechanisms,
    )
    return WholeOrganismEpisodeAuthority(
        authority_key=EPISODE_KEY,
        manifest=manifest,
        max_episodes=4,
        max_state_bytes=16 * 1024 * 1024,
    )


def _prepare_episode(
    authority: WholeOrganismEpisodeAuthority,
    settlement,
    recovery_state,
):
    draft = authority.begin_observation(
        chain_id=(
            "whole-organism-recovery-test:"
            + settlement.authority_receipt_sha256
        ),
        settlement=settlement,
        l6_disposition=L6Disposition.UNRESOLVED,
        l6_authority_receipt_sha256=None,
    )
    contributions = []
    for spec in authority.manifest.mechanisms:
        capability = authority.mechanism_capability(
            draft,
            spec.mechanism_id,
        )
        if spec.kind is MechanismKind.RECEPTOR_FAMILY:
            contribution = authority.prepare_receptor_contribution(
                draft,
                capability,
            )
        elif recovery_state.is_recovery:
            contribution = authority.prepare_recovery_contribution(
                draft,
                capability,
                stable_state=recovery_state.record(),
                l1_n_gate_coordinates=(
                    recovery_state.l1_n_gate_coordinates
                ),
                recovery_authority_receipt_sha256=(
                    recovery_state.authority_receipt_sha256
                ),
            )
        else:
            contribution = authority.prepare_quiescent_contribution(
                draft,
                capability,
                quiescent_state=recovery_state.record(),
                quiescent_authority_receipt_sha256=(
                    recovery_state.authority_receipt_sha256
                ),
            )
        contributions.append(contribution)
    resolution = authority.resolve(draft, tuple(contributions))
    return tuple(contributions), resolution


def test_non_negative_space_is_authenticated_mounted_quiescence() -> None:
    body = _body_owner()
    owner = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    genesis = owner.snapshot_encoded()
    settlement = _settlement("active-field", negative_space=False)

    prepared = owner.prepare_observation(settlement)

    assert prepared.before.moment_state is RecoveryMomentState.QUIESCENT
    assert prepared.after.moment_state is RecoveryMomentState.QUIESCENT
    assert prepared.after.l1_n_gate_coordinates
    assert all(
        value == Fraction(0)
        for value in prepared.after.l1_n_gate_coordinates
    )
    assert prepared.after.recovery_count == 0
    assert prepared.after.physical_body_state == body.state
    assert prepared.after.full_field_root_receipt_sha256s
    assert prepared.after.payload()["quiescent_semantics"] == (
        QUIESCENT_SEMANTICS
    )
    assert prepared.after.payload()["negative_space_rule"] == (
        NEGATIVE_SPACE_RULE
    )

    undo = owner.commit_prepared(prepared)
    assert owner.state == prepared.after
    owner.rollback_committed(undo)

    assert owner.snapshot_encoded() == genesis
    assert owner.state.moment_state is RecoveryMomentState.QUIESCENT


def test_exact_native_negative_space_is_the_only_recovery_perturbation() -> None:
    body = _body_owner()
    owner = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    settlement = _settlement(
        "exact-negative-space",
        negative_space=True,
    )

    prepared = owner.prepare_observation(settlement)

    assert prepared.after.moment_state is RecoveryMomentState.PERTURBED
    assert prepared.after.l1_n_gate_coordinates == (Fraction(1),)
    assert prepared.after.recovery_count == 1
    assert all(
        value == Fraction(1)
        for value in prepared.after.l1_n_gate_coordinates
    )
    owner.commit_prepared(prepared)

    cold = owner.snapshot_encoded()
    restored = ExactWholeOrganismRecoveryOwner.restore_encoded(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
        encoded=cold,
    )
    assert restored.state == owner.state
    assert restored.snapshot_encoded() == cold
    assert restored.status()["moment_state"] == "perturbed"


def test_cold_restore_rejects_tamper_and_wrong_body_continuity() -> None:
    body = _body_owner()
    owner = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    owner.commit_prepared(owner.prepare_observation(
        _settlement("cold-auth", negative_space=True)
    ))
    cold = owner.snapshot_encoded()
    changed = json.loads(cold)
    changed["body"]["state"]["recovery_count"] = 0
    tampered = json.dumps(
        changed,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    with pytest.raises(ValueError, match="cold authentication"):
        ExactWholeOrganismRecoveryOwner.restore_encoded(
            authority_key=RECOVERY_KEY,
            physical_body_authority=body,
            encoded=tampered,
        )

    other_body = create_embodiment_proprioceptive_internal_body_authority(
        authority_key=BODY_KEY,
        world_observation_receipt_sha256=hashlib.sha256(
            b"different-body-manifest-parameter"
        ).hexdigest(),
        position_x_mm=Fraction(1),
        position_y_mm=Fraction(0),
        position_z_mm=Fraction(0),
        supported_load_grams=Fraction(0),
    )
    with pytest.raises(
        ValueError,
        match="profile crossed anatomy|body continuity",
    ):
        ExactWholeOrganismRecoveryOwner.restore_encoded(
            authority_key=RECOVERY_KEY,
            physical_body_authority=other_body,
            encoded=cold,
        )


def test_tampered_actual_n_gate_and_body_state_fail_closed() -> None:
    body = _body_owner()
    owner = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    settlement = _settlement("tamper", negative_space=False)
    witness = settlement.native_evidence_witness
    changed_port = replace(witness.ports[0], n_gates=(1,))
    changed_witness = replace(witness, ports=(changed_port,))
    changed_settlement = replace(
        settlement,
        native_evidence_witness=changed_witness,
    )

    with pytest.raises(
        ReceiptError,
        match="N_gate (?:evidence|index) changed",
    ):
        owner.prepare_observation(changed_settlement)

    body._state = replace(
        body.state,
        sequence=body.state.sequence + 1,
    )
    with pytest.raises(ValueError, match="state authority changed"):
        owner.prepare_observation(settlement)


@pytest.mark.parametrize(
    ("negative_space", "expected_state"),
    (
        (False, ContributionState.QUIESCENT),
        (True, ContributionState.PERTURBED),
    ),
)
def test_exact_owner_drives_whole_organism_recovery_contribution(
    negative_space: bool,
    expected_state: ContributionState,
) -> None:
    body = _body_owner()
    recovery = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    settlement = _settlement(
        f"episode-{negative_space}",
        negative_space=negative_space,
    )
    recovery.commit_prepared(
        recovery.prepare_observation(settlement)
    )
    episode = _episode_authority()

    contributions, resolution = _prepare_episode(
        episode,
        settlement,
        recovery.state,
    )
    recovery_contribution = next(
        value
        for value in contributions
        if value.mechanism_id == "state:recovery"
    )
    semantic = json.loads(
        recovery_contribution.semantic_evidence_json
    )

    assert recovery_contribution.state is expected_state
    assert semantic["full_field_root_receipt_sha256s"]
    assert resolution.state == "unresolved"
    assert resolution.reasons == ("l6_unresolved",)
    if negative_space:
        assert semantic["rule"] == (
            "authenticated_recovery_with_actual_n_gate"
        )
        assert semantic["l1_n_gate_coordinates"] == ["1/1"]
    else:
        assert semantic["rule"] == (
            "authenticated_mounted_uncommitted_zero"
        )
        assert semantic["quiescent_semantics"] == (
            QUIESCENT_SEMANTICS
        )


def test_identical_cold_restores_prepare_identical_next_state() -> None:
    body = _body_owner()
    owner = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    owner.commit_prepared(owner.prepare_observation(
        _settlement("first", negative_space=False)
    ))
    cold = owner.snapshot_encoded()
    left = ExactWholeOrganismRecoveryOwner.restore_encoded(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
        encoded=cold,
    )
    right = ExactWholeOrganismRecoveryOwner.restore_encoded(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
        encoded=cold,
    )
    next_settlement = _settlement(
        "next",
        negative_space=True,
        start=Fraction(1),
    )

    left_prepared = left.prepare_observation(next_settlement)
    right_prepared = right.prepare_observation(next_settlement)

    assert left_prepared.after == right_prepared.after
    assert left_prepared.after.authority_receipt_sha256 == (
        right_prepared.after.authority_receipt_sha256
    )
