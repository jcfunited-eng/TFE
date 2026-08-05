from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    DownstreamAuthority,
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    PreparedMechanismContribution,
    WholeOrganismEpisodeAuthority,
    create_mounted_mechanism_manifest,
)


KEY = b"whole-organism-contiguity-test-authority-key-v1"
TOPOLOGY_RECEIPT = hashlib.sha256(b"mounted-topology-v1").hexdigest()
ACTION_RECEIPT = hashlib.sha256(b"physical-action-authority").hexdigest()
EXECUTION_RECEIPT = hashlib.sha256(b"physical-action-execution").hexdigest()
L6_RECEIPT = hashlib.sha256(b"settled-L6-authority").hexdigest()
RECOVERY_RECEIPT = hashlib.sha256(b"exact-recovery-authority").hexdigest()
QUIESCENT_RECEIPT = hashlib.sha256(
    b"exact-quiescent-authority"
).hexdigest()


def _substream(
    sense: PhysicalSense,
    *,
    start: Fraction,
    frequency: int,
) -> NativeSensorySubstreamInput:
    count = 96
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"whole-organism-{sense.value}-sensor",
        substream_id=f"{sense.value}-field-0",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate(
                f"{sense.value}-axis",
                f"{sense.value}-center",
            ),
        ),
        physical_quantity=f"{sense.value}-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            start + Fraction(index, 512) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 512)
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 12) for index in range(count)
        ),
    )


def _settlement(
    label: str,
    *,
    start: Fraction,
    unknown_sound: bool = False,
):
    sight = _substream(
        PhysicalSense.SIGHT,
        start=start,
        frequency=7,
    )
    states = {
        sense: SenseBoundaryState.SENSOR_UNAVAILABLE
        for sense in SENSE_ORDER
    }
    states[PhysicalSense.SIGHT] = SenseBoundaryState.OBSERVED
    if unknown_sound:
        states[PhysicalSense.SOUND] = SenseBoundaryState.UNKNOWN
    built = build_six_sense_full_field(
        assembly_id=f"whole-organism-{label}",
        source_time_start=start,
        source_time_end=start + Fraction(96, 512),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(f"whole-organism-test:{label}",),
    )


def _manifest():
    mechanisms: list[MountedMechanismSpec] = []
    sense_ids = []
    for sense in SENSE_ORDER:
        mechanism_id = f"sense:{sense.value}"
        sense_ids.append(mechanism_id)
        available = sense is PhysicalSense.SIGHT
        mechanisms.append(
            MountedMechanismSpec(
                mechanism_id=mechanism_id,
                kind=MechanismKind.RECEPTOR_FAMILY,
                availability=(
                    MechanismAvailability.AVAILABLE
                    if available
                    else MechanismAvailability.UNAVAILABLE
                ),
                evidence_schema=(
                    f"test.whole_organism.{sense.value}.v1"
                ),
                parent_mechanism_ids=(),
                sense=sense.value,
                binds_full_field_roots=True,
                unavailable_reason=(
                    None if available else "test_anatomy_unavailable"
                ),
                physical_quantity=f"{sense.value}-intensity",
                physical_unit="normalized-intensity",
                physical_extent=f"{sense.value}-receptor-field",
                causal_clock="exact-source-time",
                transduction_authority_receipt_sha256=TOPOLOGY_RECEIPT,
                custody_authority_receipt_sha256=TOPOLOGY_RECEIPT,
            )
        )
    mechanisms.extend((
        MountedMechanismSpec(
            mechanism_id="state:embodiment",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.embodiment.v1",
            parent_mechanism_ids=tuple(sorted(sense_ids)),
        ),
        MountedMechanismSpec(
            mechanism_id="state:internal",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.internal.v1",
            parent_mechanism_ids=("state:embodiment",),
        ),
        MountedMechanismSpec(
            mechanism_id="state:needs",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.needs.v1",
            parent_mechanism_ids=("state:internal",),
        ),
        MountedMechanismSpec(
            mechanism_id="state:thing_population",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.thing_population.v1",
            parent_mechanism_ids=tuple(sorted(sense_ids)),
            binds_full_field_roots=True,
        ),
        MountedMechanismSpec(
            mechanism_id="state:relation_memory",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.relation_memory.v1",
            parent_mechanism_ids=("state:thing_population",),
            binds_full_field_roots=True,
        ),
        MountedMechanismSpec(
            mechanism_id="state:recovery",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.recovery.v1",
            parent_mechanism_ids=("state:relation_memory",),
        ),
        MountedMechanismSpec(
            mechanism_id="state:deliberation",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.deliberation.v1",
            parent_mechanism_ids=(
                "state:needs",
                "state:relation_memory",
            ),
        ),
        MountedMechanismSpec(
            mechanism_id="state:l6",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.whole_organism.l6.v1",
            parent_mechanism_ids=("state:deliberation",),
        ),
    ))
    return create_mounted_mechanism_manifest(
        authority_key=KEY,
        manifest_id="test-mounted-whole-organism-v1",
        topology_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        mechanisms=mechanisms,
    )


def _prepared(
    authority: WholeOrganismEpisodeAuthority,
    draft,
) -> tuple[PreparedMechanismContribution, ...]:
    contributions = []
    perturbed = {
        "state:embodiment",
        "state:deliberation",
        "state:l6",
    }
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
        elif spec.mechanism_id in perturbed:
            contribution = authority.prepare_perturbed_contribution(
                draft,
                capability,
                state_before={
                    "mechanism": spec.mechanism_id,
                    "state": "before",
                },
                state_after={
                    "mechanism": spec.mechanism_id,
                    "state": "after",
                },
            )
        else:
            contribution = authority.prepare_quiescent_contribution(
                draft,
                capability,
                quiescent_state={
                    "mechanism": spec.mechanism_id,
                    "state": "uncommitted",
                },
                quiescent_authority_receipt_sha256=QUIESCENT_RECEIPT,
            )
        contributions.append(contribution)
    return tuple(contributions)


def test_every_manifest_contribution_is_required_and_tampering_is_atomic():
    authority = WholeOrganismEpisodeAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    draft = authority.begin_action_authorization(
        chain_id="test-action-chain",
        settlement=_settlement("authorization", start=Fraction(0)),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    contributions = _prepared(authority, draft)
    baseline = authority.snapshot_encoded()
    learned_state = {"admitted_episodes": 0}
    learned_baseline = dict(learned_state)

    for index in range(len(contributions)):
        missing = contributions[:index] + contributions[index + 1:]
        result = authority.resolve(draft, missing)
        assert result.state == "unresolved"
        assert result.record is None
        assert result.capability is None
        assert authority.snapshot_encoded() == baseline
        assert learned_state == learned_baseline

        damaged = list(contributions)
        damaged[index] = replace(
            damaged[index],
            semantic_evidence_json="{}",
        )
        result = authority.resolve(draft, damaged)
        assert result.state == "unresolved"
        assert result.record is None
        assert result.capability is None
        assert authority.snapshot_encoded() == baseline
        assert learned_state == learned_baseline

    duplicate = authority.resolve(
        draft,
        contributions + (contributions[0],),
    )
    assert duplicate.state == "unresolved"
    assert authority.snapshot_encoded() == baseline
    assert learned_state == learned_baseline

    other_draft = authority.begin_action_authorization(
        chain_id="test-post-hoc-chain",
        settlement=_settlement("post-hoc", start=Fraction(1)),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    post_hoc = list(contributions)
    post_hoc[0] = _prepared(authority, other_draft)[0]
    assert authority.resolve(draft, post_hoc).state == "unresolved"
    assert authority.snapshot_encoded() == baseline
    assert learned_state == learned_baseline

    resolved = authority.resolve(draft, contributions)
    assert resolved.state == "resolved"
    assert resolved.capability is not None
    authority.require(
        resolved.capability,
        DownstreamAuthority.ACTION_EXECUTION,
    )
    with pytest.raises(PermissionError):
        authority.require(
            resolved.capability,
            DownstreamAuthority.LEARNING,
        )
    assert learned_state == learned_baseline


def test_unknown_receptor_is_quiescent_and_unsettled_l6_fails_closed():
    authority = WholeOrganismEpisodeAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    unknown = authority.begin_action_authorization(
        chain_id="test-unknown-chain",
        settlement=_settlement(
            "unknown-sound",
            start=Fraction(0),
            unknown_sound=True,
        ),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    before = authority.snapshot_encoded()
    sound = authority.prepare_receptor_contribution(
        unknown,
        authority.mechanism_capability(
            unknown,
            "sense:sound",
        ),
    )
    assert sound.state.value == "quiescent"
    assert "l1_n_gate_coordinates" not in sound.semantic_evidence_json
    assert authority.snapshot_encoded() == before

    observation = authority.begin_observation(
        chain_id="test-unsettled-observation",
        settlement=_settlement("unsettled", start=Fraction(1)),
        l6_disposition=L6Disposition.UNRESOLVED,
        l6_authority_receipt_sha256=None,
    )
    unresolved = authority.resolve(
        observation,
        _prepared(authority, observation),
    )
    assert unresolved.state == "unresolved"
    assert unresolved.reasons == ("l6_unresolved",)
    assert authority.snapshot_encoded() == before


def test_retained_verified_episode_serves_capabilities_without_reopening_field(
    monkeypatch,
):
    authority = WholeOrganismEpisodeAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    draft = authority.begin_action_authorization(
        chain_id="test-retained-verified-episode",
        settlement=_settlement(
            "retained-verified-episode",
            start=Fraction(0),
        ),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    resolved = authority.resolve(draft, _prepared(authority, draft))
    assert resolved.state == "resolved"
    assert resolved.record is not None

    def reopened(_record):
        raise AssertionError("retained episode was reopened")

    monkeypatch.setattr(authority, "_verify_episode_record", reopened)
    capability = authority.capability_for(
        resolved.record.authority_receipt_sha256
    )
    retained = authority.require(
        capability,
        DownstreamAuthority.ACTION_EXECUTION,
    )

    assert retained is resolved.record


def test_one_verified_draft_custody_serves_every_mechanism(monkeypatch):
    authority = WholeOrganismEpisodeAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    settlement = _settlement("single-draft-custody", start=Fraction(0))
    settlement_type = type(settlement)
    original_verify = settlement_type.verify
    verify_calls = 0

    def counted_verify(value):
        nonlocal verify_calls
        verify_calls += 1
        return original_verify(value)

    monkeypatch.setattr(settlement_type, "verify", counted_verify)
    draft = authority.begin_action_authorization(
        chain_id="test-single-draft-custody",
        settlement=settlement,
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    construction_verify_calls = verify_calls
    contributions = _prepared(authority, draft)
    resolved = authority.resolve(draft, contributions)

    assert resolved.state == "resolved"
    assert construction_verify_calls > 0
    assert verify_calls == construction_verify_calls

    crossed = replace(
        draft,
        settlement=_settlement(
            "crossed-draft-custody",
            start=Fraction(1),
        ),
    )
    with pytest.raises(ValueError, match="draft changed authority"):
        authority.mechanism_capability(
            crossed,
            authority.manifest.mechanisms[0].mechanism_id,
        )


def test_consequence_grants_learning_and_cold_round_trip_is_exact():
    manifest = _manifest()
    authority = WholeOrganismEpisodeAuthority(
        authority_key=KEY,
        manifest=manifest,
    )
    authorization_draft = authority.begin_action_authorization(
        chain_id="test-complete-chain",
        settlement=_settlement("authorization", start=Fraction(0)),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    authorization = authority.resolve(
        authorization_draft,
        _prepared(authority, authorization_draft),
    )
    assert authorization.state == "resolved"
    assert authorization.capability is not None

    consequence_settlement = _settlement(
        "consequence",
        start=Fraction(1),
    )
    consequence_draft = authority.begin_consequence(
        authorization=authorization.capability,
        settlement=consequence_settlement,
        action_execution_receipt_sha256=EXECUTION_RECEIPT,
        l6_disposition=L6Disposition.SETTLED,
        l6_authority_receipt_sha256=L6_RECEIPT,
    )
    consequence = authority.resolve(
        consequence_draft,
        _prepared(authority, consequence_draft),
    )
    assert consequence.state == "resolved"
    assert consequence.record is not None
    assert consequence.capability is not None

    learned_state = {"admitted_episodes": 0}
    for downstream in (
        DownstreamAuthority.LEARNING,
        DownstreamAuthority.CERTAINTY,
        DownstreamAuthority.SPEECH,
        DownstreamAuthority.L6_COMMIT,
    ):
        retained = authority.require(
            consequence.capability,
            downstream,
        )
        assert retained is consequence.record
    learned_state["admitted_episodes"] += 1
    assert learned_state == {"admitted_episodes": 1}

    assert consequence.record.full_field_roots == (
        full_field_sensory_roots(consequence_settlement)
    )
    assert all(
        contribution.source_time_start
        == consequence_settlement.source_time_start
        and contribution.source_time_end
        == consequence_settlement.source_time_end
        for contribution in consequence.record.contributions
    )

    encoded = authority.snapshot_encoded()
    assert b"native_evidence_transition" in encoded
    assert b"receipt_records" not in encoded
    assert b"payload_base64" not in encoded
    restored = WholeOrganismEpisodeAuthority.restore_encoded(
        authority_key=KEY,
        manifest=manifest,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    restored_capability = restored.capability_for(
        consequence.record.authority_receipt_sha256
    )
    restored.require(
        restored_capability,
        DownstreamAuthority.LEARNING,
    )

    damaged = json.loads(encoded)
    damaged["payload"]["episodes"][1]["contributions"][0][
        "semantic_evidence_json"
    ] = "{}"
    damaged_encoded = json.dumps(
        damaged,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError):
        WholeOrganismEpisodeAuthority.restore_encoded(
            authority_key=KEY,
            manifest=manifest,
            encoded=damaged_encoded,
        )
