from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_inquiry import (
    CAUSAL_INQUIRY_CONSUMER_ID,
    CausalInquiryCapacityError,
    CausalInquiryOwner,
    CausalInquiryProfile,
    InquiryAttemptAbandonment,
    InquiryDecision,
)
from dsf_ai_service.substrate.causal_inquiry_tutor_authority import (
    CausalInquiryTutorAuthorizationAuthority,
)
from dsf_ai_service.substrate.causal_thing_mosaic import CausalThingRoute
from dsf_ai_service.substrate.custodied_thing_encounter import (
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PlaceCommand,
    PickCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)
from tests.test_articulatory_consequence_closure import (
    EVIDENCE_KEY,
    _Harness,
    _vocal_pcm,
)
from tests.test_articulatory_exploration_selector import (
    _pending,
    _selector,
)


INQUIRY_KEY = b"causal-inquiry-owner-authority-key-v1"
TUTOR_AUTHORITY_KEY = (
    b"causal-inquiry-external-tutor-authority-key-v1"
)


def _tutor_authority() -> CausalInquiryTutorAuthorizationAuthority:
    return CausalInquiryTutorAuthorizationAuthority(
        authority_key=TUTOR_AUTHORITY_KEY
    )


def _profile(
    *,
    max_witnesses: int = 12,
    max_bindings: int = 4,
) -> CausalInquiryProfile:
    return CausalInquiryProfile.create(
        profile_id="focused-causal-inquiry",
        max_witnesses=max_witnesses,
        max_bindings=max_bindings,
        max_roots_per_witness=512,
        max_state_bytes=64 * 1024 * 1024,
    )


def _owner(
    harness: _Harness,
    *,
    profile: CausalInquiryProfile | None = None,
) -> CausalInquiryOwner:
    return CausalInquiryOwner(
        authority_key=INQUIRY_KEY,
        profile=profile or _profile(),
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=harness.companion_vocal,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )


def _authorization(
    harness: _Harness,
    need,
    selection,
    nonce_byte: int,
):
    return _tutor_authority().issue(
        need_receipt_sha256=need.authority_receipt_sha256,
        world_observation_receipt_sha256=(
            harness.world.observation_snapshot()
            .authority_receipt_sha256
        ),
        program_id=selection.program.program_id,
        nonce=bytes((nonce_byte,)) * 32,
    )


def _custody_for_action(harness: _Harness, execution):
    mount = harness.physical.mount_action_outcome(execution)
    custody = harness._settled(
        mount,
        execution,
        self_acoustic=False,
    )
    capability = custody.issue_child(
        CAUSAL_INQUIRY_CONSUMER_ID
    )
    return custody, capability


def _admit_witness(
    owner: CausalInquiryOwner,
    harness: _Harness,
    execution,
    *,
    prior=None,
):
    custody, capability = _custody_for_action(harness, execution)
    prepared = owner.prepare_witness(
        custody_authority=custody,
        custody_capability=capability,
        prior_witness=prior,
    )
    owner.commit_prepared(prepared)
    return prepared.result, custody


def _initial_need(
    owner: CausalInquiryOwner,
    harness: _Harness,
):
    witness, custody = _admit_witness(
        owner,
        harness,
        harness.self_action(
            PickCommand(
                object_id="W1-object-1",
                duration_microseconds=100_000,
            ),
            "causal-inquiry-lived-occurrence",
        ),
    )
    assert owner.active_need is not None
    return witness, custody, owner.active_need


def _root_fields(root) -> tuple[str, ...]:
    evidence = json.loads(root.full_evidence_json)
    return tuple(
        field[0]
        for field in evidence["field_tuples"][0]["fields"]
    )


def _learn_first_binding(
    owner: CausalInquiryOwner,
    harness: _Harness,
    witness,
    witness_custody,
    need,
):
    thing_capability = witness_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    partition = harness.partitions.partition_from_custody(
        custody_authority=witness_custody,
        capability=thing_capability,
        prior=None,
    )
    mosaic = harness.things.admit(partition)
    pending = _pending(harness)
    selector = _selector(harness, pending)
    selection = selector.select()
    authorization = _authorization(
        harness,
        need,
        selection,
        1,
    )
    mosaic, fresh, _synthesis = harness.attempt(
        mosaic,
        program_id=selection.program.program_id,
        name="causal-inquiry-exploratory-attempt",
    )
    prepared_attempt = owner.prepare_attempt(
        need=need,
        fresh_articulatory_receipt=fresh,
        tutor_authorization=authorization,
        exploration_selector=selector,
        exploration_selection=selection,
    )
    owner.commit_prepared(prepared_attempt)
    response = harness.companion_action(
        causal_intent_receipt_sha256=(
            fresh.authority_receipt_sha256
        )
    )
    consequence_closure = harness.closure.prepare(fresh, response)
    harness.closure.commit_prepared(consequence_closure)
    later_custody, later_capability = _custody_for_action(
        harness,
        response,
    )
    later_view = later_custody.open_child(later_capability)
    later_route = harness.things.route(
        later_view.causal_settlement
    )
    assert later_route.state == "unique"
    prepared_closure = owner.prepare_closure(
        attempt=prepared_attempt.result,
        tutor_response=response,
        later_custody_authority=later_custody,
        later_custody_capability=later_capability,
    )
    owner.commit_prepared(prepared_closure)
    return (
        prepared_closure.result,
        response,
        mosaic,
        later_custody,
    )


def test_one_lived_occurrence_opens_need_and_verified_consequence_binds():
    harness = _Harness(
        world_key=b"causal-inquiry-accepted-world-authority-key"
    )
    owner = _owner(harness)
    witness, witness_custody, need = _initial_need(
        owner,
        harness,
    )

    assert witness.route_state == "unresolved"
    assert witness.causal_continuation_relation == "genesis"
    assert isinstance(witness.source_time_start, Fraction)
    assert isinstance(witness.source_time_end, Fraction)
    assert witness.source_time_end > witness.source_time_start
    assert len(witness.observed_senses) >= 2
    assert witness.full_field_roots
    assert all(
        _root_fields(root) == DSF_FIELD_ORDER
        for root in witness.full_field_roots
    )
    with pytest.raises(ValueError, match="structure changed"):
        owner._verify_witness(replace(
            witness,
            source_time_end=witness.source_time_start,
        ))
    with pytest.raises(ValueError, match="authority changed"):
        owner._verify_witness(replace(
            witness,
            source_time_end=witness.source_time_end + 1,
        ))
    silent = owner.prepare_resolution(need)
    assert isinstance(silent, InquiryDecision)
    assert silent.state == "silent"
    assert silent.candidate_program_ids == ()
    assert not silent.meaning_authority
    assert not silent.word_authority
    assert not silent.label_authority

    binding, response, _mosaic, _later = _learn_first_binding(
        owner,
        harness,
        witness,
        witness_custody,
        need,
    )

    assert binding.tutor_response == response
    assert binding.prior_route_state == "unresolved"
    assert binding.later_route_state == "unique"
    assert len(binding.later_boundary_receipts) >= 2
    assert all(
        _root_fields(root) == DSF_FIELD_ORDER
        for root in binding.later_full_field_roots
    )
    assert owner.pending_attempt is None
    status = owner.status()
    assert status["binding_count"] == 1
    assert status["full_dsf_field_preserved"] is True
    assert status["reduced_approximation"] is False
    assert status["retained_media_bytes"] == 0
    assert status["meaning_authority"] is False
    assert status["word_authority"] is False
    assert status["label_authority"] is False

    encoded = owner.snapshot_encoded()
    lowered = encoded.lower()
    for forbidden in (
        b'"pcm"',
        b'"media"',
        b'"transcript"',
        b'"text"',
        b'"label"',
        b'"chi"',
        b'"atlas"',
        b'"score"',
        b'"threshold"',
        b'"similarity"',
        b'"recurrence"',
        b'"tutor_id"',
        b'"tutor_label"',
        b'"joe"',
        b'"wc"',
    ):
        assert forbidden not in lowered
    restored = CausalInquiryOwner.restore_encoded(
        authority_key=INQUIRY_KEY,
        profile=_profile(),
        encoded=encoded,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=harness.companion_vocal,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )
    assert restored.snapshot_encoded() == encoded
    with pytest.raises(ValueError, match="authority changed"):
        CausalInquiryOwner.restore_encoded(
            authority_key=INQUIRY_KEY,
            profile=_profile(),
            encoded=encoded,
            thing_owner=harness.things,
            articulatory_owner=harness.articulatory,
            fresh_articulatory_authority=harness.fresh,
            companion_vocal_authority=harness.companion_vocal,
            world_authority=harness.world,
            tutor_authorization_verifier=(
                CausalInquiryTutorAuthorizationAuthority(
                    authority_key=(
                        b"foreign-cold-inquiry-tutor-authority-key"
                    )
                ).verifier()
            ),
        )
    tampered = bytearray(encoded)
    tampered[-8] ^= 1
    with pytest.raises(ValueError):
        CausalInquiryOwner.restore_encoded(
            authority_key=INQUIRY_KEY,
            profile=_profile(),
            encoded=bytes(tampered),
            thing_owner=harness.things,
            articulatory_owner=harness.articulatory,
            fresh_articulatory_authority=harness.fresh,
            companion_vocal_authority=harness.companion_vocal,
            world_authority=harness.world,
            tutor_authorization_verifier=(
                _tutor_authority().verifier()
            ),
        )


def test_prepare_discard_commit_rollback_and_capacity_are_exact():
    harness = _Harness(
        world_key=b"causal-inquiry-transaction-world-authority-key"
    )
    owner = _owner(
        harness,
        profile=_profile(max_witnesses=1),
    )
    execution = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_010, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-transaction-edge",
    )
    custody, capability = _custody_for_action(harness, execution)
    before = owner.snapshot_encoded()
    prepared = owner.prepare_witness(
        custody_authority=custody,
        custody_capability=capability,
    )
    assert owner.witnesses == ()
    owner.discard_prepared(prepared)
    assert owner.snapshot_encoded() == before

    prepared = owner.prepare_witness(
        custody_authority=custody,
        custody_capability=capability,
    )
    undo = owner.commit_prepared(prepared)
    admitted = owner.snapshot_encoded()
    assert admitted != before
    retry = owner.prepare_witness(
        custody_authority=custody,
        custody_capability=capability,
    )
    owner.commit_prepared(retry)
    assert owner.snapshot_encoded() == admitted

    owner.rollback_committed(
        owner.commit_prepared(
            owner.prepare_witness(
                custody_authority=custody,
                custody_capability=capability,
            )
        )
    )
    assert owner.snapshot_encoded() == admitted
    with pytest.raises(ValueError, match="stale"):
        owner.rollback_committed(undo)

    second = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_020, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-over-capacity-edge",
    )
    second_custody, second_capability = _custody_for_action(
        harness,
        second,
    )
    with pytest.raises(
        CausalInquiryCapacityError,
        match="need capacity",
    ):
        owner.prepare_witness(
            custody_authority=second_custody,
            custody_capability=second_capability,
            prior_witness=owner.witnesses[0],
        )
    assert owner.snapshot_encoded() == admitted


def test_signed_relation_gap_witness_preserves_one_unique_thing():
    harness = _Harness(
        world_key=b"causal-inquiry-unique-relation-gap-world-key"
    )
    owner = _owner(harness)
    execution = harness.self_action(
        PickCommand(
            object_id="W1-object-1",
            duration_microseconds=100_000,
        ),
        "causal-inquiry-unique-relation-gap-edge",
    )
    custody, capability = _custody_for_action(harness, execution)
    view = owner._open_lived_child(custody, capability)
    senses, boundaries, roots = owner._lived_evidence(view)
    route = CausalThingRoute(
        state="unique",
        thing_ids=("1" * 64,),
        matching_route_keys=(roots[0].route_key,),
    )

    witness = owner._seal_witness(
        sequence=1,
        view=view,
        capability=capability,
        senses=senses,
        boundaries=boundaries,
        roots=roots,
        route=route,
        prior=None,
        causal_continuation_relation="genesis",
    )

    assert witness.route_state == "unique"
    assert witness.thing_ids == ("1" * 64,)
    owner._verify_witness(witness)


def test_unique_routes_passive_frames_and_noncausal_continuation_are_bounded(
    monkeypatch,
):
    harness = _Harness(
        world_key=b"causal-inquiry-refusal-world-authority-key"
    )
    owner = _owner(harness)
    execution = harness.self_action(
        PickCommand(
            object_id="W1-object-1",
            duration_microseconds=100_000,
        ),
        "causal-inquiry-refusal-edge",
    )
    custody, capability = _custody_for_action(harness, execution)
    monkeypatch.setattr(
        harness.things,
        "route",
        lambda _settlement: CausalThingRoute(
            state="unique",
            thing_ids=("1" * 64,),
            matching_route_keys=(("sight", "2" * 64),),
        ),
    )
    with pytest.raises(ValueError, match="unique routes"):
        owner.prepare_witness(
            custody_authority=custody,
            custody_capability=capability,
        )
    assert owner.witnesses == ()

    monkeypatch.undo()
    passive_mount = harness.physical.mount_current_observation()
    passive = SettledExperienceCustodyAuthority(
        authority_key=b"causal-inquiry-passive-custody-key",
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=harness.world_key,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="causal-inquiry-passive-custody",
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    passive.admit(
        passive_mount,
        world_observation=harness.world.observation_snapshot(),
    )
    passive_capability = passive.issue_child(
        CAUSAL_INQUIRY_CONSUMER_ID
    )
    passive_prepared = owner.prepare_witness(
        custody_authority=passive,
        custody_capability=passive_capability,
    )
    owner.commit_prepared(passive_prepared)
    passive_witness = passive_prepared.result
    assert passive_witness.origin == "passive_observation"
    assert passive_witness.world_execution_receipt_sha256 is None
    assert passive_witness.world_before_receipt_sha256 is None
    assert passive_witness.world_after_receipt_sha256 is None
    assert passive_witness.prior_witness_receipt_sha256 is None
    assert passive_witness.causal_continuation_relation == "genesis"
    passive_need = owner.active_need
    assert passive_need.origin == "passive_observation"
    passive_decision = owner.prepare_resolution(passive_need)
    assert passive_decision.state == "silent"
    assert passive_decision.reason == (
        "awaiting_explicit_tutor_authorization"
    )
    selector = _selector(harness, _pending(harness))
    selection = selector.select()
    active_thing_capability = custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    active_partition = harness.partitions.partition_from_custody(
        custody_authority=custody,
        capability=active_thing_capability,
        prior=None,
    )
    active_mosaic = harness.things.admit(active_partition)
    authorization = _authorization(
        harness,
        passive_need,
        selection,
        2,
    )
    _passive_mosaic, passive_fresh, _passive_synthesis = (
        harness.attempt(
            active_mosaic,
            program_id=selection.program.program_id,
            name="causal-inquiry-passive-exploration",
        )
    )
    foreign_authorization = (
        CausalInquiryTutorAuthorizationAuthority(
            authority_key=(
                b"foreign-causal-inquiry-tutor-authority-key"
            )
        ).issue(
            need_receipt_sha256=(
                passive_need.authority_receipt_sha256
            ),
            world_observation_receipt_sha256=(
                passive_witness.world_observation_receipt_sha256
            ),
            program_id=selection.program.program_id,
            nonce=b"\x03" * 32,
        )
    )
    with pytest.raises(ValueError, match="authority changed"):
        owner.prepare_attempt(
            need=passive_need,
            fresh_articulatory_receipt=passive_fresh,
            tutor_authorization=foreign_authorization,
            exploration_selector=selector,
            exploration_selection=selection,
        )
    with pytest.raises(ValueError, match="authority changed"):
        owner.prepare_attempt(
            need=passive_need,
            fresh_articulatory_receipt=passive_fresh,
            tutor_authorization=replace(
                authorization,
                nonce_sha256="f" * 64,
            ),
            exploration_selector=selector,
            exploration_selection=selection,
        )
    stale_authorization = _tutor_authority().issue(
        need_receipt_sha256=(
            passive_need.authority_receipt_sha256
        ),
        world_observation_receipt_sha256="f" * 64,
        program_id=selection.program.program_id,
        nonce=b"\x04" * 32,
    )
    with pytest.raises(ValueError, match="need or physical act"):
        owner.prepare_attempt(
            need=passive_need,
            fresh_articulatory_receipt=passive_fresh,
            tutor_authorization=stale_authorization,
            exploration_selector=selector,
            exploration_selection=selection,
        )
    passive_attempt = owner.prepare_attempt(
        need=passive_need,
        fresh_articulatory_receipt=passive_fresh,
        tutor_authorization=authorization,
        exploration_selector=selector,
        exploration_selection=selection,
    )
    owner.commit_prepared(passive_attempt)
    assert owner.pending_attempt.mode == "exploratory"
    assert (
        owner.pending_attempt.tutor_authorization
        == authorization
    )
    passive_encoded = owner.snapshot_encoded()
    passive_cold = CausalInquiryOwner.restore_encoded(
        authority_key=INQUIRY_KEY,
        profile=_profile(),
        encoded=passive_encoded,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=harness.companion_vocal,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )
    assert passive_cold.snapshot_encoded() == passive_encoded
    assert (
        passive_cold.pending_attempt.tutor_authorization
        == authorization
    )

    owner = _owner(harness)
    monkeypatch.setattr(
        harness.things,
        "route",
        lambda _settlement: CausalThingRoute(
            state="unresolved",
            thing_ids=(),
            matching_route_keys=(),
        ),
    )
    first, _ = _admit_witness(
        owner,
        harness,
        harness.self_action(
            PlaceCommand(
                object_id="W1-object-1",
                target_position=PositionMM(1_000, 1_700, 0),
                duration_microseconds=100_000,
            ),
            "causal-inquiry-retained-first",
        ),
    )
    intervening = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_500, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-unobserved-intervening-edge",
    )
    assert intervening.disposition == "applied"
    noncausal = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_600, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-noncausal-candidate",
    )
    noncausal_custody, noncausal_capability = _custody_for_action(
        harness,
        noncausal,
    )
    with pytest.raises(ValueError, match="no exact causal edge"):
        owner.prepare_witness(
            custody_authority=noncausal_custody,
            custody_capability=noncausal_capability,
            prior_witness=first,
        )


def test_one_binding_issues_nonsemantic_opportunity_and_one_slot_refuses_growth(
    monkeypatch,
):
    harness = _Harness(
        world_key=b"causal-inquiry-opportunity-world-authority-key"
    )
    owner = _owner(harness)
    witness, witness_custody, need = _initial_need(
        owner,
        harness,
    )
    _binding, response, mosaic, _later = _learn_first_binding(
        owner,
        harness,
        witness,
        witness_custody,
        need,
    )
    mosaic = harness.admit_consequence(mosaic, response)
    original_route = harness.things.route
    monkeypatch.setattr(
        harness.things,
        "route",
        lambda _settlement: CausalThingRoute(
            state="unresolved",
            thing_ids=(),
            matching_route_keys=(),
        ),
    )
    next_execution = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_020, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-later-exact-chain",
    )
    assert (
        next_execution.before.authority_receipt_sha256
        == response.after.authority_receipt_sha256
    )
    later_recurrence, later_custody = _admit_witness(
        owner,
        harness,
        next_execution,
        prior=witness,
    )
    thing_capability = later_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    later_partition = harness.partitions.partition_from_custody(
        custody_authority=later_custody,
        capability=thing_capability,
        prior=mosaic.partitions[-1],
    )
    mosaic = harness.things.admit(later_partition)
    assert (
        later_recurrence.causal_continuation_relation
        == "exact_inquiry_resolution_chain"
    )
    later_need = owner.active_need
    prepared = owner.prepare_resolution(later_need)
    decision = prepared.result
    assert decision.state == "ready"
    assert decision.opportunity.action_role == (
        "attention_seeking_attempt"
    )
    assert decision.opportunity.meaning_authority is False
    assert decision.opportunity.word_authority is False
    assert decision.opportunity.label_authority is False
    owner.commit_prepared(prepared)

    monkeypatch.setattr(harness.things, "route", original_route)
    _mosaic, fresh, _synthesis = harness.attempt(
        mosaic,
        program_id=decision.opportunity.program_id,
        name="causal-inquiry-learned-attempt",
    )
    replayed_authorization = _tutor_authority().issue(
        need_receipt_sha256=need.authority_receipt_sha256,
        world_observation_receipt_sha256=(
            witness.world_observation_receipt_sha256
        ),
        program_id=owner.bindings[0].program_id,
        nonce=b"\x01" * 32,
    )
    assert replayed_authorization == (
        owner.bindings[0].exploratory_tutor_authorization
    )
    replay_selector = _selector(harness, _pending(harness))
    replay_selection = replay_selector.select()
    with pytest.raises(ValueError, match="before learning"):
        owner.prepare_attempt(
            need=later_need,
            fresh_articulatory_receipt=fresh,
            tutor_authorization=replayed_authorization,
            exploration_selector=replay_selector,
            exploration_selection=replay_selection,
        )
    armed = owner.prepare_attempt(
        need=later_need,
        fresh_articulatory_receipt=fresh,
        opportunity=decision.opportunity,
    )
    owner.commit_prepared(armed)
    stable = owner.snapshot_encoded()
    with pytest.raises(
        CausalInquiryCapacityError,
        match="pending-attempt capacity",
    ):
        owner.prepare_attempt(
            need=later_need,
            fresh_articulatory_receipt=fresh,
            opportunity=decision.opportunity,
        )
    assert owner.snapshot_encoded() == stable

    harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_030, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-unrelated-edge-abandons-stale-attempt",
    )
    abandoned = owner.prepare_abandonment(
        attempt=armed.result,
    )
    assert abandoned.operation == "abandon_attempt"
    assert abandoned.result == InquiryAttemptAbandonment(
        reason="stale_world",
        attempt_receipt_sha256=(
            armed.result.authority_receipt_sha256
        ),
        tutor_response_receipt_sha256=None,
        later_settlement_receipt_sha256=None,
        later_route_state=None,
    )
    owner.commit_prepared(abandoned)
    assert owner.pending_attempt is None
    assert owner.active_opportunity is None
    assert len(owner.bindings) == 1


def test_existing_binding_prevents_tutor_bootstrap_override(
    monkeypatch,
):
    harness = _Harness(
        world_key=b"causal-inquiry-ambiguous-world-authority-key"
    )
    owner = _owner(harness)
    first_witness, first_custody, first_need = (
        _initial_need(owner, harness)
    )
    _first_binding, first_response, mosaic, _later = (
        _learn_first_binding(
            owner,
            harness,
            first_witness,
            first_custody,
            first_need,
        )
    )
    mosaic = harness.admit_consequence(mosaic, first_response)
    original_route = harness.things.route
    monkeypatch.setattr(
        harness.things,
        "route",
        lambda _settlement: CausalThingRoute(
            state="unresolved",
            thing_ids=(),
            matching_route_keys=(),
        ),
    )
    second_edge = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_020, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        "causal-inquiry-second-learning-edge",
    )
    second_recurrence, second_custody = _admit_witness(
        owner,
        harness,
        second_edge,
        prior=first_witness,
    )
    second_thing_capability = second_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    second_partition = harness.partitions.partition_from_custody(
        custody_authority=second_custody,
        capability=second_thing_capability,
        prior=mosaic.partitions[-1],
    )
    mosaic = harness.things.admit(second_partition)
    selector = _selector(harness, _pending(harness))
    selection = selector.select()
    assert selection.program == harness.programs[1]
    second_need = owner.active_need
    authorization = _authorization(
        harness,
        second_need,
        selection,
        5,
    )
    _mosaic, second_fresh, _synthesis = harness.attempt(
        mosaic,
        program_id=selection.program.program_id,
        name="causal-inquiry-bootstrap-override-refusal",
    )
    with pytest.raises(ValueError, match="before learning"):
        owner.prepare_attempt(
            need=second_need,
            fresh_articulatory_receipt=second_fresh,
            tutor_authorization=authorization,
            exploration_selector=selector,
            exploration_selection=selection,
        )
    decision = owner.prepare_resolution(second_need)
    assert decision.result.state == "ready"
    assert decision.result.candidate_program_ids == (
        owner.bindings[0].program_id,
    )
    assert owner.active_opportunity is None


def test_nested_companion_episode_intent_closes_and_cold_authenticates():
    harness = _Harness(
        world_key=b"causal-inquiry-nested-companion-world-key"
    )
    owner = _owner(harness)
    witness, witness_custody, need = _initial_need(
        owner,
        harness,
    )
    thing_capability = witness_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    partition = harness.partitions.partition_from_custody(
        custody_authority=witness_custody,
        capability=thing_capability,
        prior=None,
    )
    mosaic = harness.things.admit(partition)
    selector = _selector(harness, _pending(harness))
    selection = selector.select()
    authorization = _authorization(
        harness,
        need,
        selection,
        6,
    )
    _mosaic, fresh, _synthesis = harness.attempt(
        mosaic,
        program_id=selection.program.program_id,
        name="causal-inquiry-nested-companion-attempt",
    )
    armed = owner.prepare_attempt(
        need=need,
        fresh_articulatory_receipt=fresh,
        tutor_authorization=authorization,
        exploration_selector=selector,
        exploration_selection=selection,
    )
    owner.commit_prepared(armed)
    pending_encoded = owner.snapshot_encoded()

    episode = harness.companion_vocal.prepare_episode(
        pcm_s16le=_vocal_pcm(),
        causal_parent_receipt_sha256=(
            fresh.authority_receipt_sha256
        ),
    )
    intent = episode.intent_receipt
    block = episode.prediction_blocks[0]
    response = block.execution_receipt
    harness.companion_vocal.commit_episode(episode)
    later_custody = harness._settled(
        block.physical_mount,
        response,
        self_acoustic=False,
    )
    later_capability = later_custody.issue_child(
        CAUSAL_INQUIRY_CONSUMER_ID
    )

    changed_intent = replace(
        intent,
        causal_parent_receipt_sha256="f" * 64,
    )
    with pytest.raises(ValueError, match="intent authority changed"):
        owner.prepare_closure(
            attempt=armed.result,
            tutor_response=response,
            later_custody_authority=later_custody,
            later_custody_capability=later_capability,
            companion_episode_intent=changed_intent,
        )
    assert owner.bindings == ()

    foreign_companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"causal-inquiry-foreign-companion-key",
        world_authority=harness.world,
        physical_authority=harness.physical,
    )
    foreign_owner = CausalInquiryOwner.restore_encoded(
        authority_key=INQUIRY_KEY,
        profile=_profile(),
        encoded=pending_encoded,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=foreign_companion,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )
    with pytest.raises(ValueError, match="intent authority changed"):
        foreign_owner.prepare_closure(
            attempt=foreign_owner.pending_attempt,
            tutor_response=response,
            later_custody_authority=later_custody,
            later_custody_capability=later_capability,
            companion_episode_intent=intent,
        )

    with pytest.raises(
        ValueError,
        match="resolving response requires causal closure",
    ):
        owner.prepare_abandonment(
            attempt=armed.result,
            tutor_response=response,
            later_custody_authority=later_custody,
            later_custody_capability=later_capability,
            companion_episode_intent=intent,
        )
    prepared = owner.prepare_closure(
        attempt=armed.result,
        tutor_response=response,
        later_custody_authority=later_custody,
        later_custody_capability=later_capability,
        companion_episode_intent=intent,
    )
    owner.commit_prepared(prepared)
    assert prepared.result.companion_episode_intent == intent
    assert prepared.result.tutor_response == response
    assert not hasattr(prepared.result, "text")
    encoded = owner.snapshot_encoded()
    cold = CausalInquiryOwner.restore_encoded(
        authority_key=INQUIRY_KEY,
        profile=_profile(),
        encoded=encoded,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=harness.companion_vocal,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.bindings == owner.bindings


def test_verified_nonresolving_abandonment_is_exactly_transactional(
    monkeypatch,
):
    harness = _Harness(
        world_key=b"causal-inquiry-nonresolving-abandon-world-key"
    )
    owner = _owner(harness)
    witness, witness_custody, need = _initial_need(
        owner,
        harness,
    )
    thing_capability = witness_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    partition = harness.partitions.partition_from_custody(
        custody_authority=witness_custody,
        capability=thing_capability,
        prior=None,
    )
    mosaic = harness.things.admit(partition)
    selector = _selector(harness, _pending(harness))
    selection = selector.select()
    authorization = _authorization(
        harness,
        need,
        selection,
        7,
    )
    _mosaic, fresh, _synthesis = harness.attempt(
        mosaic,
        program_id=selection.program.program_id,
        name="causal-inquiry-nonresolving-attempt",
    )
    armed = owner.prepare_attempt(
        need=need,
        fresh_articulatory_receipt=fresh,
        tutor_authorization=authorization,
        exploration_selector=selector,
        exploration_selection=selection,
    )
    owner.commit_prepared(armed)
    response = harness.companion_action(
        causal_intent_receipt_sha256=(
            fresh.authority_receipt_sha256
        )
    )
    later_custody, later_capability = _custody_for_action(
        harness,
        response,
    )
    later_settlement_receipt = (
        later_custody.open_child(later_capability)
        .causal_settlement.authority_receipt_sha256
    )
    monkeypatch.setattr(
        harness.things,
        "route",
        lambda _settlement: CausalThingRoute(
            state="unresolved",
            thing_ids=(),
            matching_route_keys=(),
        ),
    )
    before = owner.snapshot_encoded()
    witnesses = owner.witnesses
    bindings = owner.bindings
    prepared = owner.prepare_abandonment(
        attempt=armed.result,
        tutor_response=response,
        later_custody_authority=later_custody,
        later_custody_capability=later_capability,
    )
    expected = InquiryAttemptAbandonment(
        reason="verified_nonresolving_response",
        attempt_receipt_sha256=(
            armed.result.authority_receipt_sha256
        ),
        tutor_response_receipt_sha256=(
            response.authority_receipt_sha256
        ),
        later_settlement_receipt_sha256=(
            later_settlement_receipt
        ),
        later_route_state="unresolved",
    )
    assert prepared.result == expected
    assert owner.pending_attempt == armed.result
    assert owner.witnesses == witnesses
    assert owner.bindings == bindings
    owner.discard_prepared(prepared)
    assert owner.snapshot_encoded() == before

    retry = owner.prepare_abandonment(
        attempt=armed.result,
        tutor_response=response,
        later_custody_authority=later_custody,
        later_custody_capability=later_capability,
    )
    assert retry.result == expected
    undo = owner.commit_prepared(retry)
    committed = owner.snapshot_encoded()
    assert owner.pending_attempt is None
    assert owner.active_opportunity is None
    assert owner.witnesses == witnesses
    assert owner.bindings == bindings

    owner.rollback_committed(undo)
    assert owner.snapshot_encoded() == before
    deterministic_retry = owner.prepare_abandonment(
        attempt=armed.result,
        tutor_response=response,
        later_custody_authority=later_custody,
        later_custody_capability=later_capability,
    )
    assert deterministic_retry.result == expected
    owner.commit_prepared(deterministic_retry)
    assert owner.snapshot_encoded() == committed

    cold = CausalInquiryOwner.restore_encoded(
        authority_key=INQUIRY_KEY,
        profile=_profile(),
        encoded=committed,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        fresh_articulatory_authority=harness.fresh,
        companion_vocal_authority=harness.companion_vocal,
        world_authority=harness.world,
        tutor_authorization_verifier=(
            _tutor_authority().verifier()
        ),
    )
    assert cold.snapshot_encoded() == committed
    assert cold.pending_attempt is None
    assert cold.witnesses == witnesses
    assert cold.bindings == bindings
