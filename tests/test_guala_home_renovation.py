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
