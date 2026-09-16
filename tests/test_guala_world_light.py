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
    RETINA_TOTAL_RECEPTOR_COUNT, UPGRADED_RETINAL_SITE_GEOMETRY, _bounce_ppm, _lit_surfaces_focal, _region_radiance, _room_lights,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
COUPLING = SolarCoupling(outdoor_region_ids=("backyard",), window_share_ppm_by_region_id=(("her-room", 250_000),))
NORTH_WINDOW = WindowMM("y-max", 1_800, 3_800, 900, 2_100)


def _her_room_with_window():
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    region = next(r for r in snapshot.regions if r.region_id == "her-room")
    lit = replace(region, windows=(NORTH_WINDOW,), looks=())      # paint only, and no lamp (her glow stars emit): the sun alone is measured
    quiet = replace(snapshot, regions=tuple(lit if r.region_id == "her-room" else r for r in snapshot.regions),
                    objects=tuple(o for o in snapshot.objects if not (o.emission_ppm and any(o.emission_ppm)) and o.shape != "box"))
    return world, quiet, lit


def _field(snapshot, region, sun, heading=90_000, pitch=-25_000):
    pixels = [_region_radiance(region) for _ in UPGRADED_RETINAL_SITE_GEOMETRY]
    her = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id)
    eye = PositionMM(her.pose.position.x + 200, her.pose.position.y, 1_100)
    started = time.perf_counter()
    lights, occluders = _room_lights(snapshot, region, sun)
    _lit_surfaces_focal(snapshot, eye=eye, body_heading_millidegrees=heading, retinal_pitch_offset_millidegrees=pitch,
                        current_region=region, illumination_ppm=region.illumination_ppm, pixels=pixels,
                        site_geometry=UPGRADED_RETINAL_SITE_GEOMETRY, lights=lights, occluders=occluders)
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


def test_the_shaft_reaches_her_eye_on_the_path_her_beat_uses(monkeypatch) -> None:
    """Her beat sees the world through the loop's own retina function, so the sun must be
    handed to it there: with her head turned to her north window and pitched down, the
    focal field at one in the afternoon carries a shaft that the night field lacks, and
    the night field equals a field with no sun at all (the sky's share unchanged)."""
    from dsf_ai_service.guala_functional_loop import WORLD_FOCAL_SITES, _world_retina_u8
    from dsf_ai_service.guala_functional_organism import FunctionalOrganism
    from dsf_ai_service.guala_world_sensorium import _sun_of

    world = home_world_authority(identity=IDENTITY)          # her room has its north window
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    axes = tuple((a[0], a[1], a[2], -25_000 if a[1] == "neck_pitch" else a[3], *a[4:]) for a in organism.body_axes)   # head down at the floor
    snapshot = world.observation_snapshot()
    snapshot = replace(snapshot, bodies=tuple(                 # her body turned to face north, the window's wall
        replace(b, pose=replace(b.pose, heading_millidegrees=90_000)) if b.body_id == snapshot.self_body_id else b
        for b in snapshot.bodies))
    midnight = int(time.time()) - int(time.time()) % 86_400
    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", str(midnight + 13 * 3_600))
    sun = _sun_of(world)
    assert sun is not None and sun[2] > 0.8                    # one in the afternoon: high in the north
    noon = _world_retina_u8(snapshot, axes, sun)
    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", str(midnight + 2 * 3_600))
    assert _sun_of(world) is None
    night = _world_retina_u8(snapshot, axes, _sun_of(world))
    assert night == _world_retina_u8(snapshot, axes, None)
    lit = sum(1 for a, b in zip(noon[-WORLD_FOCAL_SITES:], night[-WORLD_FOCAL_SITES:]) if a > b)
    assert lit > 200, lit                                       # measured by hand: 934 of 4,800 at this aim
    wide = [a - b for a, b in zip(noon[:-WORLD_FOCAL_SITES], night[:-WORLD_FOCAL_SITES])]
    assert min(wide) >= 0, min(wide)                               # by day nothing in the wide field is darker
    assert sum(1 for w in wide if w > 2) < len(wide) // 10          # it rises evenly by the sun's one bounce, more only where a thing stands in the sun


def _lamp(object_id: str, x: int, y: int, radius: int, emission: int) -> EmbodiedObject:
    return EmbodiedObject(object_id, radius, 800, PositionMM(x, y, 0), emission_ppm=(emission,) * 6)


def test_a_lamp_lights_the_floor_around_it_at_night_and_a_thing_beside_it_casts_a_shadow() -> None:
    """No sun (night): a lamp in her room lights the floor near it, falling off with distance;
    a thing standing between the lamp and the floor leaves a shadow; without the lamp the
    field is the room's ambient only."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    region = next(r for r in snapshot.regions if r.region_id == "her-room")
    plain = replace(region, looks=())                                 # paint only, so light alone is measured
    quiet = replace(snapshot, regions=tuple(plain if r.region_id == "her-room" else r for r in snapshot.regions),
                    objects=tuple(o for o in snapshot.objects if not (o.emission_ppm and any(o.emission_ppm)) and o.shape != "box"))
    ambient = int(round(255 * float(_retinal_luminance((_region_radiance(plain),))[0])))
    dark, _ = _field(quiet, plain, None)
    assert all(v == ambient for v in dark)
    lit_world = replace(quiet, objects=quiet.objects + (_lamp("lamp-test", 2_600, 8_800, 150, 900_000),))   # ahead of her, north
    lamp, cost = _field(lit_world, plain, None)
    lit = [i for i, v in enumerate(lamp) if v > ambient]
    assert len(lit) > 200 and max(lamp) > ambient + 20, (len(lit), max(lamp))
    assert cost < 0.25, cost
    shaded_world = replace(lit_world, objects=lit_world.objects + (EmbodiedObject("post-test", 120, 2_000, PositionMM(2_600, 9_300, 0)),))   # beyond the lamp: its shadow falls on the floor she sees
    shaded, _ = _field(shaded_world, plain, None)
    assert sum(1 for v in shaded if v > ambient) < len(lit)          # the post's shadow


def test_one_bounce_lets_a_lamp_or_the_sun_light_the_whole_room() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    region = next(r for r in snapshot.regions if r.region_id == "her-room")
    none, _ = _room_lights(replace(snapshot, objects=()), region, None)
    assert _bounce_ppm(region, none) == (0,) * 6
    lamp_only, _ = _room_lights(replace(snapshot, objects=(_lamp("lamp-test", 2_600, 9_000, 150, 900_000),)), region, None)
    assert all(b > 0 for b in _bounce_ppm(region, lamp_only))
    sun_only, _ = _room_lights(replace(snapshot, objects=()), region, COUPLING.sun_vector(13 * 3_600))
    noon = _bounce_ppm(region, sun_only)
    assert all(b > 0 for b in noon)
    assert all(b == 0 for b in _bounce_ppm(region, _room_lights(replace(snapshot, objects=()), region, COUPLING.sun_vector(2 * 3_600))[0]))
    assert _bounce_ppm(region, sun_only) == noon                     # deterministic


def test_a_look_on_the_floor_is_read_where_the_rays_meet_it_and_survives_the_records() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    region = next(r for r in snapshot.regions if r.region_id == "her-room")
    assert region.looks, "her room declares its floor planks and wall panels"
    record = region.as_record()
    assert "looks" in record and _region_from(record) == region
    plain = replace(region, looks=())
    quiet = replace(snapshot, objects=())
    textured, cost = _field(quiet, region, None)
    flat, _ = _field(quiet, plain, None)
    assert len(set(textured)) >= 3 and len(set(flat)) == 1, (len(set(textured)), len(set(flat)))   # planks and joints, not one grey
    assert cost < 0.25, cost
    again, _ = _field(quiet, region, None)
    assert again == textured
    try:
        replace(region, looks=(replace(region.looks[0], to_mm=9_000),)).verify()
    except ValueError as error:
        assert "outside its face" in str(error)
    else:
        raise AssertionError("a look wider than its face was accepted")


def _eye_view(snapshot, x, y, heading, pitch, sun=None):
    """Her focal field from a stance in her room, through the path her beat uses."""
    from dsf_ai_service.guala_functional_loop import WORLD_FOCAL_SITES, _world_retina_u8
    from dsf_ai_service.guala_functional_organism import FunctionalOrganism
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    placed = replace(snapshot, room_id="her-room", bodies=tuple(
        replace(b, pose=replace(b.pose, position=replace(b.pose.position, x=x, y=y), heading_millidegrees=heading)) if b.body_id == snapshot.self_body_id else b
        for b in snapshot.bodies))
    axes = tuple((a[0], a[1], a[2], pitch if a[1] == "neck_pitch" else 0 if a[1] in ("neck_yaw", "left_eye_yaw", "right_eye_yaw", "left_eye_pitch", "right_eye_pitch") else a[3], *a[4:])
                 for a in organism.body_axes)
    field = _world_retina_u8(placed, axes, sun)[-WORLD_FOCAL_SITES:]
    return [field[r * 80:(r + 1) * 80] for r in range(60)]


SHAPES = {   # the test's own furniture shapes for her room: (extents, heading, elevation)
    "bed": ((1_500, 950, 500), 0, 0), "toy-chest": ((800, 450, 450), 0, 0), "desk": ((1_200, 600, 750), 0, 0),
    "desk-chair": ((400, 400, 850), 0, 0), "wall-art-shapes": ((40, 560, 760), 0, 1_300), "wall-art-weather": ((40, 560, 760), 0, 1_300),
}


def _with_boxes(snapshot):
    import math
    shaped = []
    for o in snapshot.objects:
        if o.object_id in SHAPES and o.position is not None:
            size, heading, elevation = SHAPES[o.object_id]
            o = replace(o, shape="box", size_mm=size, heading_millidegrees=heading, elevation_mm=elevation,
                        radius_mm=max(o.radius_mm, math.ceil(math.hypot(size[0], size[1]) / 2)))
        shaped.append(o)
    return replace(snapshot, objects=tuple(shaped))


def test_a_box_is_a_shape_in_the_records_and_a_sphere_still_decodes_without_one() -> None:
    from dsf_ai_service.substrate.embodiment_world import _object_from
    world = home_world_authority(identity=IDENTITY)
    desk = next(o for o in _with_boxes(world.observation_snapshot()).objects if o.object_id == "desk")
    assert desk.shape == "box" and desk.size_mm == (1_200, 600, 750)
    record = desk.as_record()
    assert record["shape"] == {"kind": "box", "size_mm": [1_200, 600, 750], "heading_millidegrees": 0, "elevation_mm": 0}
    assert _object_from(record) == desk
    ball = next(o for o in world.observation_snapshot().objects if o.object_id == "bowl")
    assert ball.shape == "sphere" and "shape" not in ball.as_record() and _object_from(ball.as_record()) == ball
    try:
        replace(desk, radius_mm=100).verify()
    except ValueError as error:
        assert "cover the box" in str(error)
    else:
        raise AssertionError("a box wider than its footprint disc was accepted")


def test_a_box_shows_faces_and_straight_edges_where_a_sphere_showed_an_orb() -> None:
    """From mid-room facing the west wall by lamplight: the two framed pictures hang at
    picture height with straight vertical edges (a column of the field changes at the
    same row for many rows), and the desk shows more than one face brightness."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = _with_boxes(world.observation_snapshot())
    lamp = EmbodiedObject("lamp-test", 200, 800, PositionMM(3_000, 7_200, 0), emission_ppm=(900_000,) * 6)
    night = tuple(replace(r, illumination_ppm=(50_000,) * 6) if r.region_id == "her-room" else r for r in snapshot.regions)
    dark = replace(snapshot, objects=snapshot.objects + (lamp,), regions=night)
    rows = _eye_view(dark, 2_600, 8_000, 180_000, -8_000)
    # A framed picture at 1.3 to 2.06 m on the wall 2.6 m away, seen from an eye at 1.1 m: above the horizon, not on the floor.
    upper = [v for row in rows[:25] for v in row]
    lower = [v for row in rows[45:] for v in row]
    assert len(set(upper)) >= 4, len(set(upper))                    # the pictures and the wall, not one grey
    # Straight vertical edges: some column carries the same brightness step across at least 12 consecutive rows.
    steps = 0
    for c in range(1, 80):
        run = 0
        for r in range(60):
            if abs(rows[r][c] - rows[r][c - 1]) >= 6:
                run += 1
                if run >= 12:
                    steps += 1
                    break
            else:
                run = 0
    assert steps >= 2, steps
    spheres_only = replace(dark, objects=tuple(replace(o, shape="sphere", size_mm=(), elevation_mm=0) if o.shape == "box" else o for o in dark.objects))
    orb_rows = _eye_view(spheres_only, 2_600, 8_000, 180_000, -8_000)
    assert orb_rows != rows                                          # the shape law changes what she sees


def test_a_box_stands_in_front_of_a_sphere_behind_it() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    keep = tuple(o for o in snapshot.objects if o.object_id not in ("bed", "pillow", "blanket", "toy-chest", "desk", "desk-chair"))
    ball = EmbodiedObject("ball-test", 200, 500, PositionMM(2_600, 9_400, 0), reflectance_ppm=(950_000,) * 6)
    wall = EmbodiedObject("crate-test", 500, 5_000, PositionMM(2_600, 8_800, 0), reflectance_ppm=(120_000,) * 6,
                          shape="box", size_mm=(800, 300, 600), heading_millidegrees=0, elevation_mm=0)
    day = tuple(replace(r, illumination_ppm=(785_000,) * 6) if r.region_id == "her-room" else r for r in snapshot.regions)
    with_ball = replace(snapshot, objects=keep + (ball,), regions=day)
    with_both = replace(snapshot, objects=keep + (ball, wall), regions=day)
    seen = _eye_view(with_ball, 2_600, 7_600, 90_000, -20_000)
    hidden = _eye_view(with_both, 2_600, 7_600, 90_000, -20_000)
    bright_seen = sum(1 for row in seen for v in row if v >= 120)
    bright_hidden = sum(1 for row in hidden for v in row if v >= 120)
    assert bright_seen > 40 and bright_hidden < bright_seen // 4, (bright_seen, bright_hidden)   # the crate hides the bright ball
