from __future__ import annotations

import hashlib
from dataclasses import replace
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.embodied_other_perspective import (
    AccessProvenanceKind,
    AccessState,
    EmbodiedOtherPerspectiveOwner,
    EmbodiedOtherPerspectiveProfile,
    OtherBodyAccessProvenanceAuthority,
)


KEY = b"embodied-other-perspective-test-key" * 2


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _Geometry:
    def __init__(self, identity: str, x: int) -> None:
        self.body_id = identity
        self.object_id = identity
        self.x = x

    def as_record(self):
        return {"geometry_id": self.body_id, "x_mm": self.x}


class _World:
    @staticmethod
    def verify_observation_snapshot(value: object) -> None:
        if getattr(value, "authenticated", False) is not True:
            raise ValueError("W1 observation authority changed")


def _snapshot(
    revision: int,
    *,
    object_x: int,
    other_present: bool,
):
    self_body = _Geometry("body:self", 0)
    bodies = [self_body]
    if other_present:
        bodies.append(_Geometry("body:other", 10))
    return SimpleNamespace(
        authenticated=True,
        revision=revision,
        self_body_id="body:self",
        bodies=tuple(bodies),
        objects=(_Geometry("object:one", object_x),),
        authority_receipt_sha256=_h(f"observation:{revision}:{object_x}"),
    )


def _profile() -> EmbodiedOtherPerspectiveProfile:
    return EmbodiedOtherPerspectiveProfile.create(
        profile_id="bounded-other-perspective",
        max_other_bodies=4,
        max_objects_per_body=8,
        max_state_bytes=1024 * 1024,
    )


def _owners():
    world = _World()
    access = OtherBodyAccessProvenanceAuthority(
        authority_key=KEY,
        world_authority=world,
        max_objects=8,
    )
    owner = EmbodiedOtherPerspectiveOwner(
        authority_key=KEY,
        profile=_profile(),
        world_authority=world,
        access_authority=access,
    )
    return owner, world, access


def _access(
    authority: OtherBodyAccessProvenanceAuthority,
    snapshot: object,
    state: AccessState,
):
    return authority.issue(
        observation=snapshot,
        body_id="body:other",
        object_access=(("object:one", state),),
        provenance_kind=(
            AccessProvenanceKind.EXPLICITLY_MODELED_ACCESS
        ),
        source_evidence_receipt_sha256=_h(
            f"modeled-access:{snapshot.revision}:{state.value}"
        ),
    )


def _commit(
    owner: EmbodiedOtherPerspectiveOwner,
    snapshot: object,
    *access,
):
    prepared = owner.prepare(
        observation=snapshot,
        access_provenance=tuple(access),
    )
    return owner.commit(prepared)


def _object_x(model) -> int:
    return model.object_states[0].object_geometry["x_mm"]


def test_shared_observation_and_absent_other_do_not_share_state() -> None:
    owner, _, access = _owners()
    shared = _snapshot(1, object_x=100, other_present=True)
    _commit(owner, shared, _access(access, shared, AccessState.ACCESSIBLE))

    assert owner.self_world_state.object_geometries[0][1]["x_mm"] == 100
    assert _object_x(owner.model_for("body:other")) == 100
    absent = _snapshot(2, object_x=200, other_present=False)
    _commit(owner, absent)

    assert owner.self_world_state.object_geometries[0][1]["x_mm"] == 200
    other = owner.model_for("body:other")
    assert _object_x(other) == 100
    assert other.private_belief_claimed is False


def test_moved_object_diverges_then_reacquisition_corrects() -> None:
    owner, _, access = _owners()
    first = _snapshot(1, object_x=100, other_present=True)
    _commit(owner, first, _access(access, first, AccessState.ACCESSIBLE))
    moved = _snapshot(2, object_x=300, other_present=True)
    _commit(
        owner,
        moved,
        _access(access, moved, AccessState.INACCESSIBLE),
    )

    assert owner.self_world_state.object_geometries[0][1]["x_mm"] == 300
    assert _object_x(owner.model_for("body:other")) == 100
    reacquired = _snapshot(3, object_x=300, other_present=True)
    _commit(
        owner,
        reacquired,
        _access(access, reacquired, AccessState.ACCESSIBLE),
    )
    other = owner.model_for("body:other")
    assert _object_x(other) == 300
    assert other.current_access == (
        ("object:one", AccessState.ACCESSIBLE),
    )


def test_unknown_access_is_unresolved_and_never_updates_object() -> None:
    owner, _, access = _owners()
    first = _snapshot(1, object_x=100, other_present=True)
    _commit(owner, first, _access(access, first, AccessState.ACCESSIBLE))
    moved = _snapshot(2, object_x=400, other_present=True)
    _commit(owner, moved)

    other = owner.model_for("body:other")
    assert _object_x(other) == 100
    assert other.current_access == (
        ("object:one", AccessState.UNRESOLVED),
    )
    assert owner.status()["unresolved_access_entries"] == 1


def test_tamper_rollback_and_authenticated_cold_restore() -> None:
    owner, world, access = _owners()
    first = _snapshot(1, object_x=100, other_present=True)
    evidence = _access(access, first, AccessState.ACCESSIBLE)
    tampered = replace(
        evidence,
        object_access=(("object:one", AccessState.INACCESSIBLE),),
    )
    with pytest.raises(ValueError, match="access authority changed"):
        owner.prepare(
            observation=first,
            access_provenance=(tampered,),
        )

    prepared = owner.prepare(
        observation=first,
        access_provenance=(evidence,),
    )
    changed_model = replace(
        prepared.staged_models[0],
        body_geometry={"geometry_id": "body:other", "x_mm": 999},
    )
    changed_prepared = replace(
        prepared,
        staged_models=(changed_model,),
    )
    with pytest.raises(ValueError, match="model authority changed"):
        owner.commit(changed_prepared)
    owner.discard(prepared)

    undo = _commit(owner, first, evidence)
    encoded = owner.snapshot_encoded()
    restored = EmbodiedOtherPerspectiveOwner.restore_encoded(
        authority_key=KEY,
        profile=_profile(),
        world_authority=world,
        access_authority=access,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.models == owner.models

    owner.rollback(undo)
    assert owner.models == ()
    assert owner.self_world_state is None
    prepared = restored.prepare(
        observation=_snapshot(2, object_x=500, other_present=True),
        access_provenance=(),
    )
    restored.discard(prepared)
    assert restored.snapshot_encoded() == encoded

    corrupted = bytearray(encoded)
    corrupted[-2] = corrupted[-2] ^ 1
    with pytest.raises(ValueError):
        EmbodiedOtherPerspectiveOwner.restore_encoded(
            authority_key=KEY,
            profile=_profile(),
            world_authority=world,
            access_authority=access,
            encoded=bytes(corrupted),
        )
