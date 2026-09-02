from fractions import Fraction

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    BodySurfaceContactCommand,
    EmbodiedBody,
    EmbodimentPort,
    PORT_ID,
    SECOND_BODY_PORT_ID,
    PoseMM,
    PositionMM,
    _default_receptor_geometry,
    command_record,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    ThermallyCoupledEmbodimentWorldAuthority,
)


def test_named_care_profiles_end_at_physical_surface_commands_only() -> None:
    expected_width = {
        "forehead_kiss": 1,
        "head_pat": 1,
        "hold_hand": 1,
        "hug": 3,
        "shoulder_touch": 1,
    }
    for operation, width in expected_width.items():
        actuations, duration = production._companion_contact_profile(
            operation,
            "guala-body-1",
        )
        record = command_record(
            BodySurfaceContactCommand(actuations, duration)
        )
        hop_microseconds = production.INTAKE_HOP_MILLISECONDS * 1_000
        assert 0 < duration < hop_microseconds, (
            "a companion contact must land strictly inside one intake hop "
            "or the sensory law refuses every care gesture"
        )
        assert record["operation"] == "body_surface_contact"
        assert len(record["actuations"]) == width
        encoded = repr(record).lower()
        assert operation not in encoded
        assert "reward" not in encoded
        assert "dopamine" not in encoded
        assert "meaning" not in encoded


def test_one_surface_contact_reaches_only_its_exact_cutaneous_site(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "TOUCH_RECEPTORS_AUTHORIZED", True)
    times = (Fraction(0), Fraction(1, 2))
    topology_index = 4
    trajectories = tuple(
        (
            (Fraction(1, 2), Fraction(1, 2))
            if index == topology_index
            else (Fraction(0), Fraction(0))
        )
        for index in range(production.CONTACT_SHEET_SITE_COUNT)
    )
    ports = production._touch_ports(
        times,
        None,
        body_surface_contact_trajectories=trajectories,
    )

    sheet = ports[: production.CONTACT_SHEET_SITE_COUNT]
    assert tuple(
        index
        for index, port in enumerate(sheet)
        if any(port.normalized_signal)
    ) == (topology_index,)
    assert sheet[topology_index].normalized_signal == (
        Fraction(1, 2),
        Fraction(1, 2),
    )


def test_surface_morphology_migration_preserves_the_lived_home_exactly(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "TOUCH_RECEPTORS_AUTHORIZED", True)
    regions, portals, objects = production._home_rooms_and_things()
    bodies = (
        EmbodiedBody(
            "guala-body-1",
            PoseMM(PositionMM(3_200, 1_200, 0), 0),
            radius_mm=250,
            reach_mm=800,
        ),
        EmbodiedBody(
            "person-body-1",
            PoseMM(
                PositionMM(3_500, production.HOME_ROOM_SPAN_MM + 3_600, 0),
                180_000,
            ),
            radius_mm=250,
            reach_mm=800,
        ),
    )
    ports = (
        EmbodimentPort(PORT_ID, "guala-body-1"),
        EmbodimentPort(SECOND_BODY_PORT_ID, "person-body-1"),
    )
    common = {
        "authority_key": "surface-morphology-migration-test-key",
        "thermal_anatomy": production._home_thermal_anatomy(regions, portals),
        "self_body_id": "guala-body-1",
        "bodies": bodies,
        "actor_ports": ports,
        "regions": regions,
        "portals": portals,
        "initial_objects": objects,
        "max_regions": 4,
    }
    bare = ThermallyCoupledEmbodimentWorldAuthority(**common)
    declared_bodies = (
        EmbodiedBody(
            "guala-body-1",
            bodies[0].pose,
            radius_mm=bodies[0].radius_mm,
            reach_mm=bodies[0].reach_mm,
            receptor_geometry=_default_receptor_geometry(),
        ),
        bodies[1],
    )
    prior = ThermallyCoupledEmbodimentWorldAuthority(
        **{**common, "bodies": declared_bodies},
    )
    prior.restore_encoded(bare.encoded_snapshot())
    assert prior.migrate_declared_body_receptor_geometry() is True
    prior_world = prior.observation_snapshot()
    prior_thermal = prior.thermal_observation()

    migrated = ThermallyCoupledEmbodimentWorldAuthority(
        **{**common, "bodies": declared_bodies},
        body_surface_sites=production._companion_body_surface_sites(),
    )
    assert prior._state.migration_receipt is not None
    assert (
        prior._state.migration_receipt.manifest_sha256
        != migrated._physical_manifest_sha256()
    )
    migrated.restore_encoded(
        prior.encoded_snapshot(),
        allow_authenticated_physical_manifest_migration=True,
    )
    after_world = migrated.observation_snapshot()
    after_thermal = migrated.thermal_observation()

    assert after_world.revision == prior_world.revision + 1
    assert after_world.regions == prior_world.regions
    assert after_world.portals == prior_world.portals
    assert after_world.bodies == prior_world.bodies
    assert after_world.objects == prior_world.objects
    assert after_thermal.temperatures_millikelvin == (
        prior_thermal.temperatures_millikelvin
    )
