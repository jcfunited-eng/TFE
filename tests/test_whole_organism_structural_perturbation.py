from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
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
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    PreparedMechanismContribution,
    WholeOrganismEpisodeAuthority,
    create_mounted_mechanism_manifest,
)
from dsf_ai_service.substrate.whole_organism_structural_perturbation import (
    WholeOrganismStructuralPerturbationOwner,
)


EPISODE_KEY = b"whole-organism-perturbation-episode-key-v1"
OWNER_KEY = b"whole-organism-perturbation-owner-key-v1"
OTHER_EPISODE_KEY = b"other-whole-organism-episode-key-v1"
TOPOLOGY_RECEIPT = hashlib.sha256(
    b"whole-organism-perturbation-topology"
).hexdigest()
L6_RECEIPT = hashlib.sha256(
    b"whole-organism-perturbation-l6"
).hexdigest()
QUIESCENT_RECEIPT = hashlib.sha256(
    b"whole-organism-perturbation-quiescence"
).hexdigest()
ACTION_RECEIPT = hashlib.sha256(
    b"whole-organism-perturbation-action"
).hexdigest()

RECEPTOR_IDS = {
    sense: f"mounted-mechanism-{index:03d}"
    for index, sense in enumerate(SENSE_ORDER)
}
STATE_IDS = (
    "mounted-mechanism-006",
    "mounted-mechanism-007",
    "mounted-mechanism-008",
)
PERTURBED_STATE_ID = STATE_IDS[-1]


def _substream(
    *,
    label: str,
    start: Fraction,
    frequency: int,
) -> NativeSensorySubstreamInput:
    count = 48
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id=f"structural-perturbation-{label}-sight",
        substream_id="sight-field-0",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("sight-axis", "sight-center"),
        ),
        physical_quantity="sight-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            start + Fraction(index, 256) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 256)
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 8) for index in range(count)
        ),
    )


def _settlement(
    label: str,
    *,
    start: Fraction,
    frequency: int,
):
    states = {
        sense: SenseBoundaryState.SENSOR_UNAVAILABLE
        for sense in SENSE_ORDER
    }
    states[PhysicalSense.SIGHT] = SenseBoundaryState.OBSERVED
    built = build_six_sense_full_field(
        assembly_id=f"structural-perturbation-{label}",
        source_time_start=start,
        source_time_end=start + Fraction(48, 256),
        observed_substreams={
            PhysicalSense.SIGHT: (
                _substream(
                    label=label,
                    start=start,
                    frequency=frequency,
                ),
            ),
        },
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(f"structural-perturbation:{label}",),
    )


def _manifest(*, authority_key: bytes = EPISODE_KEY):
    mechanisms: list[MountedMechanismSpec] = []
    receptor_ids = []
    for sense in SENSE_ORDER:
        mechanism_id = RECEPTOR_IDS[sense]
        receptor_ids.append(mechanism_id)
        mechanisms.append(
            MountedMechanismSpec(
                mechanism_id=mechanism_id,
                kind=MechanismKind.RECEPTOR_FAMILY,
                availability=MechanismAvailability.AVAILABLE,
                evidence_schema=(
                    f"test.structural_perturbation.{sense.value}.v1"
                ),
                parent_mechanism_ids=(),
                sense=sense.value,
                binds_full_field_roots=True,
                physical_quantity=f"{sense.value}-intensity",
                physical_unit="normalized-intensity",
                physical_extent=f"{sense.value}-receptor-field",
                causal_clock="exact-source-time",
                transduction_authority_receipt_sha256=(
                    TOPOLOGY_RECEIPT
                ),
                custody_authority_receipt_sha256=TOPOLOGY_RECEIPT,
            )
        )
    mechanisms.extend((
        MountedMechanismSpec(
            mechanism_id=STATE_IDS[0],
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.structural_perturbation.state.0.v1",
            parent_mechanism_ids=tuple(sorted(receptor_ids)),
        ),
        MountedMechanismSpec(
            mechanism_id=STATE_IDS[1],
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.structural_perturbation.state.1.v1",
            parent_mechanism_ids=(STATE_IDS[0],),
            binds_full_field_roots=True,
        ),
        MountedMechanismSpec(
            mechanism_id=STATE_IDS[2],
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.structural_perturbation.state.2.v1",
            parent_mechanism_ids=(STATE_IDS[1],),
        ),
    ))
    return create_mounted_mechanism_manifest(
        authority_key=authority_key,
        manifest_id="test-whole-organism-structural-perturbation-v1",
        topology_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        mechanisms=mechanisms,
    )


def _contributions(
    authority: WholeOrganismEpisodeAuthority,
    draft,
    *,
    final_state: object,
) -> tuple[PreparedMechanismContribution, ...]:
    result = []
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
        elif spec.mechanism_id == PERTURBED_STATE_ID:
            contribution = authority.prepare_perturbed_contribution(
                draft,
                capability,
                state_before={"state": "open"},
                state_after=final_state,
            )
        else:
            contribution = authority.prepare_quiescent_contribution(
                draft,
                capability,
                quiescent_state={"state": "mounted-uncommitted-zero"},
                quiescent_authority_receipt_sha256=(
                    QUIESCENT_RECEIPT
                ),
            )
        result.append(contribution)
    return tuple(result)


def _settled_capability(
    authority: WholeOrganismEpisodeAuthority,
    *,
    label: str,
    start: Fraction,
    frequency: int,
    final_state: object | None = None,
):
    draft = authority.begin_observation(
        chain_id=f"structural-perturbation-chain-{label}",
        settlement=_settlement(
            label,
            start=start,
            frequency=frequency,
        ),
        l6_disposition=L6Disposition.SETTLED,
        l6_authority_receipt_sha256=L6_RECEIPT,
    )
    resolved = authority.resolve(
        draft,
        _contributions(
            authority,
            draft,
            final_state=(
                {"state": "settled"}
                if final_state is None
                else final_state
            ),
        ),
    )
    assert resolved.state == "resolved"
    assert resolved.record is not None
    assert resolved.capability is not None
    return resolved


def _action_capability(
    authority: WholeOrganismEpisodeAuthority,
):
    draft = authority.begin_action_authorization(
        chain_id="structural-perturbation-action-chain",
        settlement=_settlement(
            "action",
            start=Fraction(9),
            frequency=13,
        ),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    resolved = authority.resolve(
        draft,
        _contributions(
            authority,
            draft,
            final_state={"state": "settled"},
        ),
    )
    assert resolved.state == "resolved"
    assert resolved.capability is not None
    return resolved.capability


def _authority_and_episodes():
    authority = WholeOrganismEpisodeAuthority(
        authority_key=EPISODE_KEY,
        manifest=_manifest(),
    )
    first = _settled_capability(
        authority,
        label="first-wrapper",
        start=Fraction(0),
        frequency=7,
    )
    identical = _settled_capability(
        authority,
        label="second-wrapper",
        start=Fraction(0),
        frequency=7,
    )
    changed_root = _settled_capability(
        authority,
        label="changed-root",
        start=Fraction(1),
        frequency=11,
    )
    changed_mechanism = _settled_capability(
        authority,
        label="changed-mechanism",
        start=Fraction(0),
        frequency=7,
        final_state={"state": "changed"},
    )
    return (
        authority,
        first,
        identical,
        changed_root,
        changed_mechanism,
    )


def _owner(
    authority: WholeOrganismEpisodeAuthority,
    *,
    max_state_bytes: int = 256 * 1024,
) -> WholeOrganismStructuralPerturbationOwner:
    return WholeOrganismStructuralPerturbationOwner(
        authority_key=OWNER_KEY,
        episode_authority=authority,
        max_state_bytes=max_state_bytes,
    )


def _commit_capability(owner, capability):
    prepared = owner.prepare(capability)
    assert prepared.state == "prepared"
    assert prepared.prepared is not None
    return prepared, owner.commit(prepared.prepared)


def test_genesis_is_manifest_bound_mounted_uncommitted_zero():
    authority, *_episodes = _authority_and_episodes()
    owner = _owner(authority)

    state = owner.current_state
    structural = json.loads(state.structural_state_json)
    provenance = json.loads(state.provenance_json)

    assert structural["manifest_authority_receipt_sha256"] == (
        authority.manifest.authority_receipt_sha256
    )
    assert structural["roots"] == []
    assert tuple(
        value["mechanism_id"] for value in structural["mechanisms"]
    ) == tuple(
        value.mechanism_id for value in authority.manifest.mechanisms
    )
    assert {
        value["state"] for value in structural["mechanisms"]
    } == {"quiescent"}
    assert {
        value["value"]["quiescent_semantics"]
        for value in structural["mechanisms"]
    } == {"mounted-uncommitted-zero"}
    assert provenance == {
        "manifest_authority_receipt_sha256": (
            authority.manifest.authority_receipt_sha256
        ),
        "origin": "mounted_uncommitted_zero",
        "schema": "guala.whole_organism.structural_provenance.v2",
    }

    restored = (
        WholeOrganismStructuralPerturbationOwner.restore_encoded(
            authority_key=OWNER_KEY,
            episode_authority=authority,
            encoded=owner.snapshot_encoded(),
        )
    )
    assert restored.current_state == state


def test_provenance_is_separate_and_distinct_wrappers_are_no_change():
    authority, first, identical, *_changed = _authority_and_episodes()
    assert first.record.episode_id != identical.record.episode_id
    owner = _owner(authority)

    first_prepared, first_commit = _commit_capability(
        owner,
        first.capability,
    )
    assert first_commit.state == "changed"
    first_state = owner.current_state
    baseline = owner.snapshot_encoded()

    second_prepared = owner.prepare(identical.capability)
    assert second_prepared.prepared is not None
    second_state = second_prepared.prepared.after_state
    assert (
        first_state.structural_state_sha256
        == second_state.structural_state_sha256
    )
    assert first_state.structural_state_json == (
        second_state.structural_state_json
    )
    assert first_state.provenance_sha256 != second_state.provenance_sha256
    assert first_state.provenance_json != second_state.provenance_json
    assert (
        first_state.authority_receipt_sha256
        != second_state.authority_receipt_sha256
    )

    no_change = owner.commit(second_prepared.prepared)
    assert no_change.state == "no_durable_change"
    assert no_change.commit is not None
    assert (
        no_change.commit.before_structural_state_sha256
        == no_change.commit.after_structural_state_sha256
    )
    assert (
        no_change.commit.before_state_authority_receipt_sha256
        != no_change.commit.after_state_authority_receipt_sha256
    )
    assert owner.snapshot_encoded() == baseline
    assert first_prepared.prepared is not None


def test_every_explicit_dsf_coordinate_participates_in_identity():
    authority, first, *_episodes = _authority_and_episodes()
    owner = _owner(authority)
    prepared = owner.prepare(first.capability)
    assert prepared.prepared is not None
    receipt = prepared.prepared.after_state
    structural = json.loads(receipt.structural_state_json)
    fields = structural["roots"][0]["field_tuples"][0]["fields"]
    assert tuple(value[0] for value in fields) == DSF_FIELD_ORDER

    for field_index, field_name in enumerate(DSF_FIELD_ORDER):
        changed = json.loads(receipt.structural_state_json)
        changed_value = changed["roots"][0]["field_tuples"][0][
            "fields"
        ][field_index][1]
        changed["roots"][0]["field_tuples"][0]["fields"][
            field_index
        ][1] = str(Fraction(changed_value) + 1)
        changed_json = json.dumps(
            changed,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        assert hashlib.sha256(
            changed_json.encode("utf-8")
        ).hexdigest() != receipt.structural_state_sha256, field_name


def test_exact_root_or_opaque_mechanism_state_change_is_changed():
    (
        authority,
        first,
        _identical,
        changed_root,
        changed_mechanism,
    ) = _authority_and_episodes()

    root_owner = _owner(authority)
    assert _commit_capability(
        root_owner,
        first.capability,
    )[1].state == "changed"
    root_prepared = root_owner.prepare(changed_root.capability)
    assert root_prepared.prepared is not None
    before_root = json.loads(
        root_prepared.prepared.before_state.structural_state_json
    )
    after_root = json.loads(
        root_prepared.prepared.after_state.structural_state_json
    )
    assert before_root["roots"] != after_root["roots"]
    root_changed = root_owner.commit(root_prepared.prepared)
    assert root_changed.state == "changed"

    mechanism_owner = _owner(authority)
    assert _commit_capability(
        mechanism_owner,
        first.capability,
    )[1].state == "changed"
    mechanism_prepared = mechanism_owner.prepare(
        changed_mechanism.capability
    )
    assert mechanism_prepared.prepared is not None
    before_mechanism = json.loads(
        mechanism_prepared.prepared.before_state.structural_state_json
    )
    after_mechanism = json.loads(
        mechanism_prepared.prepared.after_state.structural_state_json
    )
    assert before_mechanism["roots"] == after_mechanism["roots"]
    before_by_id = {
        value["mechanism_id"]: value
        for value in before_mechanism["mechanisms"]
    }
    after_by_id = {
        value["mechanism_id"]: value
        for value in after_mechanism["mechanisms"]
    }
    assert {
        key
        for key in before_by_id
        if before_by_id[key] != after_by_id[key]
    } == {PERTURBED_STATE_ID}
    mechanism_changed = mechanism_owner.commit(
        mechanism_prepared.prepared
    )
    assert mechanism_changed.state == "changed"


def test_unsettled_wrong_and_damaged_custody_fail_closed():
    authority, first, _identical, changed_root, _mechanism = (
        _authority_and_episodes()
    )
    owner = _owner(authority)
    baseline = owner.snapshot_encoded()

    action = owner.prepare(_action_capability(authority))
    assert action.state == "unresolved"
    assert action.reasons[0].startswith(
        "settled_whole_organism_custody_missing:"
    )
    assert owner.snapshot_encoded() == baseline

    other_authority = WholeOrganismEpisodeAuthority(
        authority_key=OTHER_EPISODE_KEY,
        manifest=_manifest(authority_key=OTHER_EPISODE_KEY),
    )
    other = _settled_capability(
        other_authority,
        label="other",
        start=Fraction(3),
        frequency=17,
    )
    assert owner.prepare(other.capability).state == "unresolved"
    assert owner.snapshot_encoded() == baseline

    damaged_capability = replace(
        first.capability,
        authority_hmac_sha256="0" * 64,
    )
    assert owner.prepare(damaged_capability).state == "unresolved"
    assert owner.snapshot_encoded() == baseline

    damaged_record = replace(
        changed_root.record,
        full_field_roots=(),
    )
    authority._episodes[  # noqa: SLF001 - deliberate custody corruption
        changed_root.record.authority_receipt_sha256
    ] = damaged_record
    damaged_root = owner.prepare(changed_root.capability)
    assert damaged_root.state == "unresolved"
    assert damaged_root.reasons[0].startswith(
        "settled_whole_organism_custody_missing:"
    )
    assert owner.snapshot_encoded() == baseline


def test_lock_restore_rollback_capacity_and_bounded_retention():
    authority, first, identical, *_changed = _authority_and_episodes()
    owner = _owner(authority)
    baseline = owner.snapshot_encoded()
    prepared = owner.prepare(first.capability)
    assert prepared.prepared is not None
    in_flight_encoded = owner.snapshot_encoded()

    locked = owner.prepare(identical.capability)
    assert locked.state == "unresolved"
    assert locked.reasons == ("transfer_lock_unavailable",)

    restored = (
        WholeOrganismStructuralPerturbationOwner.restore_encoded(
            authority_key=OWNER_KEY,
            episode_authority=authority,
            encoded=in_flight_encoded,
        )
    )
    assert restored.in_flight == prepared.prepared
    assert restored.commit(restored.in_flight).state == "changed"

    assert owner.rollback(prepared.prepared).state == "rolled_back"
    assert owner.snapshot_encoded() == baseline
    assert owner.commit(None).reasons == ("transfer_lock_missing",)

    retained = json.loads(owner.snapshot_encoded())["payload"]
    assert set(retained) == {
        "current_state",
        "in_flight_transfer",
        "max_state_bytes",
        "schema",
    }
    assert "completed_transfers" not in retained
    assert "episodes" not in retained

    constrained = _owner(
        authority,
        max_state_bytes=len(baseline) + 64,
    )
    constrained_baseline = constrained.snapshot_encoded()
    refused = constrained.prepare(first.capability)
    assert refused.state == "unresolved"
    assert refused.reasons[0].startswith(
        "transfer_capacity_or_custody_missing:"
    )
    assert "state capacity full" in refused.reasons[0]
    assert constrained.snapshot_encoded() == constrained_baseline

    damaged = json.loads(in_flight_encoded)
    damaged["payload"]["in_flight_transfer"][
        "authority_hmac_sha256"
    ] = "0" * 64
    damaged_encoded = json.dumps(
        damaged,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError):
        WholeOrganismStructuralPerturbationOwner.restore_encoded(
            authority_key=OWNER_KEY,
            episode_authority=authority,
            encoded=damaged_encoded,
        )
