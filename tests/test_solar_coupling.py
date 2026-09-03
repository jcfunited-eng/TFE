"""The real sun's schedule entering her declared outdoor places."""
import os

from dsf_ai_service.substrate.embodiment_world import SolarCoupling


def test_sky_arc_is_dark_at_night_and_peaks_at_midday() -> None:
    coupling = SolarCoupling(
        outdoor_region_ids=("backyard",),
        window_share_ppm_by_region_id=(("her-room", 250_000),),
    )
    assert coupling.sky_ppm(0) == coupling.night_ppm
    assert coupling.sky_ppm(3 * 3_600) == coupling.night_ppm
    assert coupling.sky_ppm(coupling.sunrise_second_of_day) == coupling.night_ppm
    assert coupling.sky_ppm(13 * 3_600) == coupling.peak_ppm
    assert coupling.sky_ppm(coupling.sunset_second_of_day) == coupling.night_ppm
    assert coupling.sky_ppm(23 * 3_600) == coupling.night_ppm
    # The arc rises monotonically to midday and falls after.
    morning = [coupling.sky_ppm(t) for t in range(6 * 3_600, 13 * 3_600, 900)]
    assert morning == sorted(morning)
    evening = [coupling.sky_ppm(t) for t in range(13 * 3_600, 20 * 3_600, 900)]
    assert evening == sorted(evening, reverse=True)


def test_dusk_stays_sparse_for_her_quantized_eyes() -> None:
    # The measurement gate as an exact bound: across the steepest part of
    # the arc, one 250ms sensory hop moves the sky by a tiny fraction of
    # its range, far below one retinal quantization step.
    coupling = SolarCoupling(
        outdoor_region_ids=("backyard",),
        window_share_ppm_by_region_id=(),
    )
    worst = max(
        abs(coupling.sky_ppm(t + 1) - coupling.sky_ppm(t))
        for t in range(0, 86_400, 60)
    )
    # Fewer than 100 ppm per second: under one part in ten thousand of the
    # full range per sensory hop.
    assert worst < 100


def test_action_writes_the_sun_into_outdoor_and_windowed_places(
    monkeypatch,
) -> None:
    from dsf_ai_service import native_production_app as production
    from dsf_ai_service.substrate.embodiment_world import (
        EmbodiedBody,
        EmbodimentPort,
        PORT_ID,
        SECOND_BODY_PORT_ID,
        PoseMM,
        PositionMM,
        _default_receptor_geometry,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        ThermallyCoupledEmbodimentWorldAuthority,
    )

    regions, portals, objects = production._home_rooms_and_things()
    authority = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="solar-coupling-test-key-0123456789ab",
        thermal_anatomy=production._home_thermal_anatomy(regions, portals),
        self_body_id="guala-body-1",
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(2_600, 7_600, 0), 0),
                radius_mm=250,
                reach_mm=800,
                receptor_geometry=_default_receptor_geometry(),
            ),
            EmbodiedBody(
                "person-body-1",
                PoseMM(PositionMM(7_300, 7_500, 0), 180_000),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "person-body-1"),
        ),
        regions=regions,
        portals=portals,
        initial_objects=objects,
        max_regions=12,
        max_portals=16,
        solar_coupling=SolarCoupling(
            outdoor_region_ids=("backyard",),
            window_share_ppm_by_region_id=(("her-room", 250_000),),
        ),
    )
    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", str(13 * 3_600))
    world = authority._settle_solar_illumination(authority._state.world)
    by_id = {region.region_id: region for region in world.regions}
    assert by_id["backyard"].illumination_ppm == (950_000,) * 6
    # Her room: authored lamps plus a quarter of the midday sky.
    assert by_id["her-room"].illumination_ppm == (
        min(1_000_000, 780_000 + (950_000 * 250_000) // 1_000_000),
    ) * 6
    # Unwindowed rooms keep their authored light exactly.
    assert by_id["kitchen"].illumination_ppm == (900_000,) * 6

    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", str(2 * 3_600))
    night = authority._settle_solar_illumination(world)
    by_id = {region.region_id: region for region in night.regions}
    assert by_id["backyard"].illumination_ppm == (20_000,) * 6
    assert by_id["her-room"].illumination_ppm == (785_000,) * 6
