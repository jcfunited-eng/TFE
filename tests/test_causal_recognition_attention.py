from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
    CausalMosaicTapestryProfile,
    ObservedCausalMosaicRelationAuthority,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    CausalRecognitionAttentionProfile,
    CausalThingRelationPathAuthority,
    WholeOrganismAttentionContextAuthority,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from tests.test_whole_organism_thing_mosaic_learning import (
    _authorization_settlement,
)


KEY = b"causal-recognition-attention-owner-test-key"
PATH_KEY = b"causal-recognition-path-test-key"
CONTEXT_KEY = b"whole-organism-attention-context-test-key"
TAPESTRY_KEY = b"recognition-tapestry-owner-test-key"
OBSERVATION_KEY = b"recognition-observation-test-key"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _stack():
    observations = ObservedCausalMosaicRelationAuthority(
        authority_key=OBSERVATION_KEY
    )
    tapestry_profile = CausalMosaicTapestryProfile.create(
        profile_id="recognition-tapestry-profile",
        max_tapestries=8,
        max_tapestry_relations=8,
        max_roots_per_tapestry=16,
        max_state_bytes=8 * 1024 * 1024,
    )
    tapestries = CausalMosaicTapestryOwner(
        authority_key=TAPESTRY_KEY,
        profile=tapestry_profile,
        relation_authority=observations,
    )
    paths = CausalThingRelationPathAuthority(
        authority_key=PATH_KEY,
        tapestry_owner=tapestries,
    )
    contexts = WholeOrganismAttentionContextAuthority(
        authority_key=CONTEXT_KEY
    )
    profile = CausalRecognitionAttentionProfile.create(
        profile_id="causal-recognition-attention-test",
        max_paths=8,
        max_roots=16,
        max_action_relations=4,
        max_inquiry_relations=4,
        max_state_bytes=16 * 1024 * 1024,
    )
    owner = CausalRecognitionAttentionOwner(
        authority_key=KEY,
        profile=profile,
        path_authority=paths,
        context_authority=contexts,
    )
    return observations, tapestries, paths, contexts, profile, owner


def _roots():
    roots = full_field_sensory_roots(_authorization_settlement())
    return {
        sense: tuple(root for root in roots if root.sense == sense)
        for sense in ("sight", "body")
    }


def _path(
    observations,
    tapestries,
    paths,
    *,
    name: str,
    sense: str,
    target: str,
    offset: int,
):
    selected = _roots()[sense]
    continuity = _sha(f"{name}-entity-continuity")
    observation = observations.observe(
        chain_id="organism-lived-continuity:" + continuity,
        entity_continuity_hmac_sha256=continuity,
        source_mosaic_receipt_sha256=_sha(f"{name}-source-mosaic"),
        target_mosaic_receipt_sha256=_sha(target),
        source_learning_receipt_sha256=_sha(f"{name}-source-learning"),
        target_learning_receipt_sha256=_sha(f"{name}-target-learning"),
        source_episode_receipt_sha256=_sha(f"{name}-source-episode"),
        continuity_predecessor_episode_receipt_sha256=_sha(
            f"{name}-source-episode"
        ),
        target_episode_receipt_sha256=_sha(f"{name}-target-episode"),
        source_time_start=Fraction(offset),
        source_time_end=Fraction(offset + 1),
        target_time_start=Fraction(offset + 1),
        target_time_end=Fraction(offset + 2),
        source_full_field_roots=selected,
        target_full_field_roots=selected,
    )
    tapestries.commit(tapestries.prepare(observation))
    tapestry = next(
        value
        for value in tapestries.tapestries
        if value.observation == observation
    )
    return paths.bind(tapestry.authority_receipt_sha256)


def _context(contexts, *, inquiry=(), actions=()):
    roots = full_field_sensory_roots(_authorization_settlement())
    return contexts.observe(
        context_id="current-whole-organism-context",
        source_time_start=Fraction(20),
        source_time_end=Fraction(21),
        current_full_field_roots=roots,
        needs_state={"rest": "uncommitted", "water": "uncommitted"},
        body_state={"pose": "standing", "temperature": "37/1"},
        chemical_state={
            "dopamine_flow": "0/1",
            "recovery_flow": "1/3",
        },
        causal_context={
            "place": "authenticated-room-receipt",
            "prior_episode": _sha("prior-episode"),
        },
        lawful_action_relation_receipts=actions,
        lawful_inquiry_relation_receipts=inquiry,
    )


def test_quiescent_genesis_and_two_sense_convergence_settle():
    observations, tapestries, paths, contexts, profile, owner = _stack()
    genesis = owner.snapshot_encoded()
    assert owner.status()["mechanism_state"] == "quiescent"

    sight = _path(
        observations,
        tapestries,
        paths,
        name="sight-path",
        sense="sight",
        target="retained-thing",
        offset=0,
    )
    body = _path(
        observations,
        tapestries,
        paths,
        name="body-path",
        sense="body",
        target="retained-thing",
        offset=4,
    )
    action = _sha("one-lawful-action-relation")
    context = _context(contexts, actions=(action,))
    prepared = owner.prepare(context=context, paths=(body, sight))
    undo = owner.commit(prepared)

    state = owner.state
    assert state is not None
    assert state.recognition_state == "settled"
    assert state.recognized_thing_mosaic_receipt_sha256 == _sha(
        "retained-thing"
    )
    assert state.participating_senses == ("body", "sight")
    assert state.attention_state == "focused_action"
    assert state.focused_relation_receipt_sha256 == action
    assert state.context == context
    assert tuple(
        root
        for path in state.paths
        for root in path.complete_tapestry_full_field_roots
    )
    status = owner.status()
    assert status["reduced_approximation"] is False
    assert status["attention_state"] == "focused_action"
    assert status["recognition_state"] == "settled"
    assert status["focused_relation_receipt_sha256"] == action
    assert status["participating_senses"] == ["body", "sight"]
    assert status["current_full_field_root_count"] == len(
        context.current_full_field_roots
    )
    assert status["path_count"] == 2
    assert status["context_id"] == context.context_id
    assert (
        status["state_authority_receipt_sha256"]
        == state.authority_receipt_sha256
    )

    owner.rollback(undo)
    assert owner.snapshot_encoded() == genesis
    cold = CausalRecognitionAttentionOwner.restore_encoded(
        authority_key=KEY,
        profile=profile,
        path_authority=paths,
        context_authority=contexts,
        encoded=genesis,
    )
    assert cold.state is None


def test_no_single_sense_can_become_master_even_with_two_paths():
    observations, tapestries, paths, contexts, _profile, owner = _stack()
    first = _path(
        observations,
        tapestries,
        paths,
        name="sight-one",
        sense="sight",
        target="one-thing",
        offset=0,
    )
    second = _path(
        observations,
        tapestries,
        paths,
        name="sight-two",
        sense="sight",
        target="one-thing",
        offset=4,
    )

    owner.commit(owner.prepare(
        context=_context(contexts),
        paths=(first, second),
    ))
    assert owner.state is not None
    assert (
        owner.state.recognition_state
        == "insufficient_multisensory_convergence"
    )
    assert owner.state.recognized_thing_mosaic_receipt_sha256 is None
    assert owner.state.attention_state == "distributed_unresolved"


def test_conflicting_paths_are_ambiguous_and_can_focus_unique_inquiry():
    observations, tapestries, paths, contexts, _profile, owner = _stack()
    first = _path(
        observations,
        tapestries,
        paths,
        name="ambiguous-sight",
        sense="sight",
        target="thing-a",
        offset=0,
    )
    second = _path(
        observations,
        tapestries,
        paths,
        name="ambiguous-body",
        sense="body",
        target="thing-b",
        offset=4,
    )
    inquiry = _sha("one-lawful-inquiry")

    owner.commit(owner.prepare(
        context=_context(contexts, inquiry=(inquiry,)),
        paths=(first, second),
    ))
    state = owner.state
    assert state is not None
    assert state.recognition_state == "ambiguous"
    assert state.recognized_thing_mosaic_receipt_sha256 is None
    assert state.candidate_thing_mosaic_receipt_sha256s == tuple(sorted(
        (_sha("thing-a"), _sha("thing-b"))
    ))
    assert state.attention_state == "focused_inquiry"
    assert state.inquiry_authorized is True
    assert state.focused_relation_receipt_sha256 == inquiry


def test_unknown_is_unresolved_and_retains_all_context_evidence():
    _observations, _tapestries, _paths, contexts, _profile, owner = _stack()
    inquiry = _sha("unknown-inquiry")
    context = _context(contexts, inquiry=(inquiry,))
    owner.commit(owner.prepare(context=context, paths=()))

    state = owner.state
    assert state is not None
    assert state.recognition_state == "unknown"
    assert state.candidate_thing_mosaic_receipt_sha256s == ()
    assert state.attention_state == "focused_inquiry"
    assert state.context.current_full_field_roots == (
        context.current_full_field_roots
    )
    assert state.context.needs_state_json == context.needs_state_json
    assert state.context.body_state_json == context.body_state_json
    assert state.context.chemical_state_json == context.chemical_state_json
    assert state.context.causal_context_json == context.causal_context_json


def test_tamper_discard_capacity_and_cold_restore_are_exact():
    observations, tapestries, paths, contexts, profile, owner = _stack()
    sight = _path(
        observations,
        tapestries,
        paths,
        name="restore-sight",
        sense="sight",
        target="restore-thing",
        offset=0,
    )
    body = _path(
        observations,
        tapestries,
        paths,
        name="restore-body",
        sense="body",
        target="restore-thing",
        offset=4,
    )
    context = _context(contexts)
    before = owner.snapshot_encoded()

    forged = replace(
        sight,
        thing_mosaic_receipt_sha256=_sha("forged-thing"),
    )
    with pytest.raises(ValueError, match="causal tapestry"):
        owner.prepare(context=context, paths=(forged, body))
    assert owner.snapshot_encoded() == before

    staged = owner.prepare(context=context, paths=(sight, body))
    owner.discard(staged)
    assert owner.snapshot_encoded() == before
    owner.commit(owner.prepare(context=context, paths=(sight, body)))
    encoded = owner.snapshot_encoded()

    cold = CausalRecognitionAttentionOwner.restore_encoded(
        authority_key=KEY,
        profile=profile,
        path_authority=paths,
        context_authority=contexts,
        encoded=encoded,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.state == owner.state

    raw = json.loads(encoded)
    raw["body"]["state"]["attention_state"] = "forged-focus"
    tampered = json.dumps(
        raw,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    with pytest.raises(ValueError, match="authority"):
        CausalRecognitionAttentionOwner.restore_encoded(
            authority_key=KEY,
            profile=profile,
            path_authority=paths,
            context_authority=contexts,
            encoded=tampered,
        )

    limited_profile = CausalRecognitionAttentionProfile.create(
        profile_id="limited-recognition-attention",
        max_paths=1,
        max_roots=16,
        max_action_relations=1,
        max_inquiry_relations=1,
        max_state_bytes=16 * 1024 * 1024,
    )
    limited = CausalRecognitionAttentionOwner(
        authority_key=KEY,
        profile=limited_profile,
        path_authority=paths,
        context_authority=contexts,
    )
    limited_before = limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="capacity"):
        limited.prepare(context=context, paths=(sight, body))
    assert limited.snapshot_encoded() == limited_before
