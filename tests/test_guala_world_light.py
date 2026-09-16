"""The sun's direct light in her world (2026-09-16, Joe's two photographs): windows on a
room's walls as declared content; the sun's path over her home from the real clock; a
shaft through a window onto the floor and walls, cut by shadows of things and bodies,
falling off with the sun's angle; all geometry, nothing else. Measured, not designed."""
from __future__ import annotations

import time
from dataclasses import replace

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_world_sensorium import _retinal_luminance
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject, PhysicalRegion, PositionMM, SolarCoupling, WindowMM, _region_from,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    RETINA_TOTAL_RECEPTOR_COUNT, UPGRADED_RETINAL_SITE_GEOMETRY, _direct_sun_focal, _region_radiance,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
COUPLING = SolarCoupling(outdoor_region_ids=("backyard",), window_share_ppm_by_region_id=(("her-room", 250_000),))
NORTH_WINDOW = WindowMM("y-max", 1_800, 3_800, 900, 2_100)


def _her_room_with_window():
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    region = next(r for r in snapshot.regions if r.region_id == "her-room")
    lit = replace(region, windows=(NORTH_WINDOW,))
    return world, replace(snapshot, regions=tuple(lit if r.region_id == "her-room" else r for r in snapshot.regions)), lit


def _field(snapshot, region, sun, heading=90_000, pitch=-25_000):
    pixels = [_region_radiance(region) for _ in UPGRADED_RETINAL_SITE_GEOMETRY]
    her = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id)
    eye = PositionMM(her.pose.position.x + 200, her.pose.position.y, 1_100)
    started = time.perf_counter()
    if sun is not None:
        _direct_sun_focal(snapshot, eye=eye, body_heading_millidegrees=heading, retinal_pitch_offset_millidegrees=pitch,
                          current_region=region, pixels=pixels, site_geometry=UPGRADED_RETINAL_SITE_GEOMETRY, sun=sun)
    elapsed = time.perf_counter() - started
    luminance = [int(round(255 * float(v))) for v in _retinal_luminance(tuple(pixels))][RETINA_TOTAL_RECEPTOR_COUNT:]
    return luminance, elapsed


def test_windows_are_declared_content_that_survive_the_records_and_old_records_decode_without() -> None:
    world = home_world_authority(identity=IDENTITY)
    region = next(r for r in world.observation_snapshot().regions if r.region_id == "her-room")
    lit = replace(region, windows=(NORTH_WINDOW,))
    record = lit.as_record()
    assert record["windows"] == [{"wall": "y-max", "from_mm": 1_800, "to_mm": 3_800, "sill_mm": 900, "top_mm": 2_100}]
    assert _region_from(record) == lit
    hallway = next(r for r in world.observation_snapshot().regions if r.region_id == "hallway")
    old = hallway.as_record()                       # a room with no window: the record as it was before today
    assert "windows" not in old and _region_from(old).windows == ()
    try:
        replace(region, windows=(WindowMM("y-max", 0, 9_000, 900, 2_100),)).verify()
    except ValueError as error:
        assert "outside its wall" in str(error)
    else:
        raise AssertionError("a window wider than its wall was accepted")


def test_the_sun_rises_in_the_east_passes_north_at_midday_and_sets_in_the_west() -> None:
    sunrise = COUPLING.sun_vector(COUPLING.sunrise_second_of_day + 1)
    noon = COUPLING.sun_vector((COUPLING.sunrise_second_of_day + COUPLING.sunset_second_of_day) // 2)
    sunset = COUPLING.sun_vector(COUPLING.sunset_second_of_day - 1)
    assert sunrise[0] > 0.99 and abs(sunrise[2]) < 0.01          # east, on the horizon
    assert abs(noon[0]) < 0.01 and noon[1] > 0.49 and 0.86 < noon[2] < 0.87   # north, sixty degrees up
    assert sunset[0] < -0.99 and abs(sunset[2]) < 0.01           # west, on the horizon
    assert COUPLING.sun_vector(2 * 3_600) is None                 # night


def test_a_shaft_through_her_window_lights_the_floor_moves_with_the_hour_and_is_gone_at_night() -> None:
    _world, snapshot, region = _her_room_with_window()
    ambient = int(round(255 * float(_retinal_luminance((_region_radiance(region),))[0])))
    noon, cost = _field(snapshot, region, COUPLING.sun_vector(13 * 3_600))
    morning, _ = _field(snapshot, region, COUPLING.sun_vector(9 * 3_600))
    night, _ = _field(snapshot, region, COUPLING.sun_vector(2 * 3_600))
    lit_noon = {i for i, v in enumerate(noon) if v > ambient}
    lit_morning = {i for i, v in enumerate(morning) if v > ambient}
    assert len(lit_noon) > 200 and max(noon) > ambient, (len(lit_noon), max(noon))          # a shaft, not a glow
    assert lit_morning and lit_morning != lit_noon                                            # it moves with the hour
    assert all(v == ambient for v in night)                                                    # no sun, no shaft
    assert cost < 0.06, cost                                                                   # measured: about 23 ms
    again, _ = _field(snapshot, region, COUPLING.sun_vector(13 * 3_600))
    assert again == noon                                                                       # deterministic


def test_a_thing_standing_in_the_shaft_casts_a_shadow() -> None:
    _world, snapshot, region = _her_room_with_window()
    ambient = int(round(255 * float(_retinal_luminance((_region_radiance(region),))[0])))
    sun = COUPLING.sun_vector(13 * 3_600)
    before, _ = _field(snapshot, region, sun)
    # A tall thing just inside the window, between the sun and the floor.
    blocker = EmbodiedObject("shade", 400, 5_000, PositionMM(2_800, 9_300, 0))
    shaded = replace(snapshot, objects=snapshot.objects + (blocker,))
    after, _ = _field(shaded, region, sun)
    lit_before = sum(1 for v in before if v > ambient)
    lit_after = sum(1 for v in after if v > ambient)
    assert lit_after < lit_before, (lit_before, lit_after)
