from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
    CausalMosaicTapestryProfile,
    ObservedCausalMosaicRelationAuthority,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from tests.test_whole_organism_thing_mosaic_learning import (
    _authorization_settlement,
)


OWNER_KEY = b"causal-mosaic-tapestry-owner-test-key"
OBSERVATION_KEY = b"causal-mosaic-relation-observation-test-key"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _profile(
    *,
    max_tapestries: int = 4,
    max_tapestry_relations: int = 4,
    max_roots_per_tapestry: int = 32,
    max_state_bytes: int = 4 * 1024 * 1024,
) -> CausalMosaicTapestryProfile:
    return CausalMosaicTapestryProfile.create(
        profile_id="causal-mosaic-tapestry-test",
        max_tapestries=max_tapestries,
        max_tapestry_relations=max_tapestry_relations,
        max_roots_per_tapestry=max_roots_per_tapestry,
        max_state_bytes=max_state_bytes,
    )


def _stack(**profile_overrides):
    authority = ObservedCausalMosaicRelationAuthority(
        authority_key=OBSERVATION_KEY
    )
    profile = _profile(**profile_overrides)
    owner = CausalMosaicTapestryOwner(
        authority_key=OWNER_KEY,
        profile=profile,
        relation_authority=authority,
    )
    return authority, profile, owner


def _observation(
    authority: ObservedCausalMosaicRelationAuthority,
    *,
    prefix: str,
    source_episode: str,
    target_episode: str,
    source_mosaic: str,
    target_mosaic: str,
    source_start: Fraction,
    source_end: Fraction,
    target_start: Fraction,
    target_end: Fraction,
):
    roots = full_field_sensory_roots(_authorization_settlement())
    continuity = _sha("entity-continuity-1")
    return authority.observe(
        chain_id="organism-lived-continuity:" + continuity,
        entity_continuity_hmac_sha256=continuity,
        source_mosaic_receipt_sha256=_sha(source_mosaic),
        target_mosaic_receipt_sha256=_sha(target_mosaic),
        source_learning_receipt_sha256=_sha(f"{prefix}-source-learning"),
        target_learning_receipt_sha256=_sha(f"{prefix}-target-learning"),
        source_episode_receipt_sha256=_sha(source_episode),
        continuity_predecessor_episode_receipt_sha256=(
            _sha(source_episode)
        ),
        target_episode_receipt_sha256=_sha(target_episode),
        source_time_start=source_start,
        source_time_end=source_end,
        target_time_start=target_start,
        target_time_end=target_end,
        source_full_field_roots=roots,
        target_full_field_roots=roots,
    )


def _first(authority):
    return _observation(
        authority,
        prefix="first",
        source_episode="episode-0",
        target_episode="episode-1",
        source_mosaic="mosaic-0",
        target_mosaic="mosaic-1",
        source_start=Fraction(0),
        source_end=Fraction(1),
        target_start=Fraction(1),
        target_end=Fraction(2),
    )


def _second(authority):
    return _observation(
        authority,
        prefix="second",
        source_episode="episode-1",
        target_episode="episode-2",
        source_mosaic="mosaic-1",
        target_mosaic="mosaic-2",
        source_start=Fraction(1),
        source_end=Fraction(2),
        target_start=Fraction(2),
        target_end=Fraction(3),
    )


def test_quiescent_genesis_is_bounded_and_cold_restorable():
    authority, profile, owner = _stack()

    before = owner.snapshot_encoded()
    assert owner.status() == {
        "full_field": True,
        "mechanism_state": "quiescent",
        "reduced_approximation": False,
        "retained_roots": 0,
        "schema": "guala.causal_mosaic_tapestry.status.v1",
        "state_bytes": len(before),
        "state_capacity_bytes": profile.max_state_bytes,
        "tapestries": 0,
        "tapestry_relations": 0,
    }

    cold = CausalMosaicTapestryOwner.restore_encoded(
        authority_key=OWNER_KEY,
        profile=profile,
        relation_authority=authority,
        encoded=before,
    )
    assert cold.snapshot_encoded() == before
    assert cold.tapestries == ()
    assert cold.relations == ()


def test_real_causal_relation_perturbs_and_preserves_every_exact_field():
    authority, _profile_value, owner = _stack()
    observation = _first(authority)

    prepared = owner.prepare(observation)
    assert prepared.state == "perturbed"
    undo = owner.commit(prepared)

    assert len(owner.tapestries) == 1
    assert owner.relations == ()
    tapestry = owner.tapestries[0]
    assert tapestry.observation == observation
    assert tapestry.full_field_roots == observation.full_field_roots
    assert all(
        tuple(name for name, _value in item["fields"])
        == DSF_FIELD_ORDER
        for root in tapestry.full_field_roots
        for item in json.loads(root.full_evidence_json)["field_tuples"]
    )
    assert owner.status()["reduced_approximation"] is False

    owner.rollback(undo)
    assert owner.tapestries == ()
    assert owner.relations == ()


def test_repeat_is_quiescent_and_unrelated_records_cannot_form():
    authority, _profile_value, owner = _stack()
    observation = _first(authority)
    owner.commit(owner.prepare(observation))
    before = owner.snapshot_encoded()

    repeated = owner.prepare(observation)
    assert repeated.state == "quiescent"
    owner.commit(repeated)
    assert owner.snapshot_encoded() == before

    with pytest.raises(
        ValueError,
        match="not one observed causal predecessor pair",
    ):
        continuity = _sha("unrelated-entity-continuity")
        authority.observe(
            chain_id="organism-lived-continuity:" + continuity,
            entity_continuity_hmac_sha256=continuity,
            source_mosaic_receipt_sha256=_sha("unrelated-mosaic-0"),
            target_mosaic_receipt_sha256=_sha("unrelated-mosaic-1"),
            source_learning_receipt_sha256=_sha("unrelated-learning-0"),
            target_learning_receipt_sha256=_sha("unrelated-learning-1"),
            source_episode_receipt_sha256=_sha("unrelated-episode-0"),
            continuity_predecessor_episode_receipt_sha256=_sha(
                "different-prior-episode"
            ),
            target_episode_receipt_sha256=_sha("unrelated-episode-1"),
            source_time_start=Fraction(3),
            source_time_end=Fraction(4),
            target_time_start=Fraction(4),
            target_time_end=Fraction(5),
            source_full_field_roots=observation.source_full_field_roots,
            target_full_field_roots=observation.target_full_field_roots,
        )
    assert owner.snapshot_encoded() == before


def test_exact_causal_path_forms_tapestry_relation_without_promotion():
    authority, _profile_value, owner = _stack()
    first = _first(authority)
    second = _second(authority)
    owner.commit(owner.prepare(first))
    owner.commit(owner.prepare(second))

    assert len(owner.tapestries) == 2
    assert len(owner.relations) == 1
    relation = owner.relations[0]
    assert relation.junction_mosaic_receipt_sha256 == _sha("mosaic-1")
    assert relation.junction_episode_receipt_sha256 == _sha("episode-1")
    assert relation.source_tapestry_receipt_sha256 != (
        relation.target_tapestry_receipt_sha256
    )


def test_tamper_capacity_discard_and_rollback_leave_exact_bytes():
    authority, _profile_value, owner = _stack(max_tapestries=1)
    observation = _first(authority)
    before = owner.snapshot_encoded()

    tampered = replace(
        observation,
        target_mosaic_receipt_sha256=_sha("forged-target"),
    )
    with pytest.raises(ValueError, match="authority changed"):
        owner.prepare(tampered)
    assert owner.snapshot_encoded() == before

    staged = owner.prepare(observation)
    owner.discard(staged)
    assert owner.snapshot_encoded() == before

    undo = owner.commit(owner.prepare(observation))
    committed = owner.snapshot_encoded()
    assert committed != before
    with pytest.raises(RuntimeError, match="capacity"):
        owner.prepare(_second(authority))
    assert owner.snapshot_encoded() == committed

    owner.rollback(undo)
    assert owner.snapshot_encoded() == before


def test_cold_restore_rejects_tamper_and_preserves_topology():
    authority, profile, owner = _stack()
    owner.commit(owner.prepare(_first(authority)))
    owner.commit(owner.prepare(_second(authority)))
    encoded = owner.snapshot_encoded()

    cold = CausalMosaicTapestryOwner.restore_encoded(
        authority_key=OWNER_KEY,
        profile=profile,
        relation_authority=authority,
        encoded=encoded,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.tapestries == owner.tapestries
    assert cold.relations == owner.relations

    raw = json.loads(encoded)
    raw["body"]["tapestries"][0]["observed_relation"][
        "chain_id"
    ] = "forged-chain"
    tampered = json.dumps(
        raw,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="authority"):
        CausalMosaicTapestryOwner.restore_encoded(
            authority_key=OWNER_KEY,
            profile=profile,
            relation_authority=authority,
            encoded=tampered,
        )
