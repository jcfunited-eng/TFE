from __future__ import annotations

import hashlib
import inspect

import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import in_hand_reach


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_home_world_is_one_bounded_physical_declaration() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    assert snapshot.revision == 0
    assert len(snapshot.regions) == 9
    assert len(snapshot.objects) == 30   # the radio joined the declaration (a thing that sounds)
    assert {item.body_id for item in snapshot.bodies} == {
        "guala-body-1",
        "person-body-1",
    }
    assert any(item.object_id == "book" for item in snapshot.objects)


def test_home_world_cold_restore_is_byte_exact() -> None:
    original = home_world_authority(identity=IDENTITY)
    body = bytes(original.encoded_snapshot())

    restored = home_world_authority(identity=IDENTITY, encoded_world=body)
    successor = bytes(restored.encoded_snapshot())

    assert successor == body
    assert hashlib.sha256(successor).hexdigest() == hashlib.sha256(body).hexdigest()


def test_home_world_fails_closed_on_identity_or_body_change() -> None:
    body = bytes(home_world_authority(identity=IDENTITY).encoded_snapshot())

    with pytest.raises(ValueError, match="canonical UUID"):
        home_world_authority(identity="not-an-identity")
    with pytest.raises(ValueError):
        home_world_authority(
            identity="18fcfe11-315f-428f-84f4-b6515498e06c",
            encoded_world=body,
        )
    with pytest.raises(ValueError):
        home_world_authority(identity=IDENTITY, encoded_world=body[:-1])


def test_home_world_has_no_old_shell_dependency() -> None:
    source = inspect.getsource(inspect.getmodule(home_world_authority))

    assert "native_production_app" not in source
    assert "FastAPI" not in source
    assert "threading" not in source
    assert "CURRENT" not in source


def test_home_world_vertical_affordances_and_clear_traversal_corridors() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    by_id = {item.object_id: item for item in snapshot.objects}

    # 1. Ceiling stars: mounted high on ceiling plane, permanently out of hand reach
    stars = by_id["glow-stars"]
    assert stars.position is not None and stars.position.z == 2_500
    assert in_hand_reach(snapshot, stars) is False

    # 2. Wall art: mounted on vertical wall plane at standing eye level
    art_shapes = by_id["wall-art-shapes"]
    art_weather = by_id["wall-art-weather"]
    assert art_shapes.position is not None and art_shapes.position.z == 800
    assert art_weather.position is not None and art_weather.position.z == 800

    # 3. Picture book: shelved on shelf-a at elevated shelf height
    book = by_id["book"]
    assert book.position is not None and book.position.x == 12_000

    # 4. Dining traversal corridor to Daddy's room and WC is clear:
    # Traversal corridor spans y in [1800, 3200]. Table and chair are north of y=2900.
    table = by_id["dining-table"]
    chair = by_id["dining-chair"]
    assert table.position is not None and table.position.y - table.radius_mm >= 2_900
    assert chair.position is not None and chair.position.y - chair.radius_mm >= 2_900
