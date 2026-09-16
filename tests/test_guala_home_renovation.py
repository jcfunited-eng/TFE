"""The renovation on the lean runtime (2026-09-16): a world persisted under an older
declaration (other paint, no windows, fewer things) restores in production into the
declared home with a receipt; every lived thing is carried; an ordinary restore still
refuses; a second restore of the renovated world does nothing and is byte-exact."""
from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service import guala_home_world
from dsf_ai_service.guala_home_world import home_world_authority

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
OLD_PAINT = (620_000,) * 6
LATER_THINGS = {"stove", "refrigerator", "kitchen-counter", "kitchen-cabinet", "pantry", "pot", "pan", "plate",
                "milk", "bread", "cheese", "berries", "carrot", "apple", "tree-oak", "tree-pine", "art-circle", "art-arch"}
DECLARED_HOME = guala_home_world._home_rooms_and_things


def _older_home():
    regions, portals, objects = DECLARED_HOME()
    older_regions = tuple(replace(r, reflectance_ppm=OLD_PAINT, windows=()) for r in regions)
    older_objects = tuple(o for o in objects if o.object_id not in LATER_THINGS)
    return older_regions, portals, older_objects


def _persisted_under_the_older_declaration(monkeypatch) -> tuple[bytes, object]:
    monkeypatch.setattr(guala_home_world, "_home_rooms_and_things", _older_home)
    older = home_world_authority(identity=IDENTITY)
    monkeypatch.undo()
    return bytes(older.encoded_snapshot()), older.observation_snapshot()


def test_a_world_persisted_under_the_older_home_restores_into_the_declared_one_with_a_receipt(monkeypatch) -> None:
    encoded, lived = _persisted_under_the_older_declaration(monkeypatch)
    declared_regions, _portals, declared_objects = guala_home_world._home_rooms_and_things()
    assert len(lived.objects) < len(declared_objects)
    assert all(r.reflectance_ppm == OLD_PAINT and r.windows == () for r in lived.regions)

    plain = home_world_authority(identity=IDENTITY, encoded_world=encoded)   # an ordinary restore never renovates
    assert not plain.home_renovation_performed and bytes(plain.encoded_snapshot()) == encoded

    world = home_world_authority(identity=IDENTITY, encoded_world=encoded, migrate_physical_return=True)
    assert world.home_renovation_performed
    after = world.observation_snapshot()
    assert after.revision == lived.revision + 1
    assert {r.region_id: r.reflectance_ppm for r in after.regions} == {r.region_id: r.reflectance_ppm for r in declared_regions}
    assert {r.region_id: r.windows for r in after.regions} == {r.region_id: r.windows for r in declared_regions}
    assert {o.object_id for o in after.objects} == {o.object_id for o in declared_objects}
    # Every lived thing is carried: her stance, the person's, and each thing's lived floor position.
    assert [(b.body_id, b.pose) for b in after.bodies] == [(b.body_id, b.pose) for b in lived.bodies]
    lived_positions = {o.object_id: o.position for o in lived.objects}
    assert all(o.position == lived_positions[o.object_id] for o in after.objects if o.object_id in lived_positions)

    # The renovated world persists; restored again in production it needs nothing and is byte-exact.
    renovated = bytes(world.encoded_snapshot())
    again = home_world_authority(identity=IDENTITY, encoded_world=renovated, migrate_physical_return=True)
    assert not again.home_renovation_performed
    assert bytes(again.encoded_snapshot()) == renovated
    assert again.observation_snapshot().revision == after.revision

    # Her live case: a receipt-bearing world under a yet newer declaration (repainted rooms).
    # An ordinary restore refuses; production renovates again, carrying the lived state.
    def repainted():
        regions, portals, objects = DECLARED_HOME()
        return tuple(replace(r, reflectance_ppm=(500_000,) * 6) for r in regions), portals, objects

    monkeypatch.setattr(guala_home_world, "_home_rooms_and_things", repainted)
    with pytest.raises(ValueError, match="topology differs"):
        home_world_authority(identity=IDENTITY, encoded_world=renovated)
    third = home_world_authority(identity=IDENTITY, encoded_world=renovated, migrate_physical_return=True)
    monkeypatch.undo()
    assert third.home_renovation_performed
    third_after = third.observation_snapshot()
    assert third_after.revision == after.revision + 1
    assert all(r.reflectance_ppm == (500_000,) * 6 for r in third_after.regions)
    assert [(b.body_id, b.pose) for b in third_after.bodies] == [(b.body_id, b.pose) for b in lived.bodies]


def test_the_declared_home_restored_in_production_needs_no_renovation() -> None:
    world = home_world_authority(identity=IDENTITY)
    encoded = bytes(world.encoded_snapshot())
    again = home_world_authority(identity=IDENTITY, encoded_world=encoded, migrate_physical_return=True)
    assert not again.home_renovation_performed
    assert bytes(again.encoded_snapshot()) == encoded


def test_looks_are_stored_once_and_a_receipt_stays_small_with_the_whole_home_declared() -> None:
    """A1's 24 looks put every action receipt at 250 KB (each look's pattern inline in
    the before and the after) and the world past its byte cap after seven actions, so
    the caregiver could not walk to her. Looks live once in the surface catalog and are
    referenced from regions and receipts; a receipt with the whole home declared stays
    under 120 KB and sixteen of them fit the cap with room."""
    import base64, json
    from dsf_ai_service.guala_caretaker_hand import _Hand
    from dsf_ai_service.substrate.embodiment_world import DEFAULT_MAX_ENCODED_STATE_BYTES

    world = home_world_authority(identity=IDENTITY)
    looks = sum(len(r.looks) for r in world.observation_snapshot().regions)
    assert looks >= 20, looks
    hand = _Hand(world, "nothing")
    assert hand.walk_to_region("her-room")
    encoded = bytes(world.encoded_snapshot())
    envelope = json.loads(encoded)
    payload = json.loads(base64.b64decode(envelope["payload_base64"]))
    inner = json.loads(base64.b64decode(payload["world_state_base64"]))
    state = json.loads(base64.b64decode(inner["payload_base64"]))
    receipts = state["recent_applied_receipts"]
    assert receipts, "the walk left receipts"
    canonical = lambda value: len(json.dumps(value, separators=(",", ":"), sort_keys=True))
    largest = max(canonical(receipt) for receipt in receipts)
    assert largest < 120_000, largest
    assert all(
        set(look["surface"]) == {"content_sha256"}
        for receipt in receipts for side in ("before", "after") for region in receipt[side]["regions"] for look in region.get("looks", [])
    )
    assert 16 * largest + canonical(state["world"]) + canonical(state["optical_surface_catalog"]) < DEFAULT_MAX_ENCODED_STATE_BYTES // 2
    again = home_world_authority(identity=IDENTITY, encoded_world=encoded)
    assert bytes(again.encoded_snapshot()) == encoded


def test_an_arrival_standing_where_a_declared_thing_now_goes_is_set_one_step_aside(monkeypatch) -> None:
    """Her live world carried a thing that arrived after genesis (art-arch) exactly where
    A1's moved picture now hangs; the renovation used to fail looking up an authored
    place for it. Now the arrival is set at the nearest free spot beside where it lived."""
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM

    encoded, lived = _persisted_under_the_older_declaration(monkeypatch)
    older = home_world_authority(identity=IDENTITY, encoded_world=encoded)
    # The older home has no oak; a stray thing lives exactly where the oak is later declared.
    oak = next(o for o in DECLARED_HOME()[2] if o.object_id == "tree-oak")
    assert all(o.object_id != "tree-oak" for o in older.observation_snapshot().objects)
    older.admit_authored_arrival(EmbodiedObject("stray-ball", 200, 500, oak.position, reflectance_ppm=(500_000,) * 6))
    with_stray = bytes(older.encoded_snapshot())
    world = home_world_authority(identity=IDENTITY, encoded_world=with_stray, migrate_physical_return=True)
    assert world.home_renovation_performed
    after = {o.object_id: o for o in world.observation_snapshot().objects}
    assert after["tree-oak"].position == oak.position
    stray = after["stray-ball"]
    assert stray.position != oak.position
    dx, dy = stray.position.x - oak.position.x, stray.position.y - oak.position.y
    assert 250 <= (dx * dx + dy * dy) ** 0.5 <= 1_600
