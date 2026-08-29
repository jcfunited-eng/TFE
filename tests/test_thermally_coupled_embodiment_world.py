from fractions import Fraction
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalPowerSource,
)
from dsf_ai_service.substrate.body_surface_contact import (
    BodySurfaceMaterial,
    ExactVector3,
)
from dsf_ai_service.substrate.embodiment_world import (
    AirVolumeState,
    PORT_ID,
    SECOND_BODY_PORT_ID,
    AdvancePhysicalTimeCommand,
    BodySurfaceActuation,
    BodySurfaceContactCommand,
    EmbodiedBody,
    MountedBodySurfaceSite,
    ObjectMaterialState,
    PoseMM,
    PositionMM,
    PreparedActionExecution,
    encode_command,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    CoupledThermalAnatomy,
    ThermallyCoupledEmbodimentWorldAuthority,
)


REGIONS = ("W1-region-A", "W1-region-B", "W1-region-C")


def _anatomy() -> CoupledThermalAnatomy:
    return CoupledThermalAnatomy(
        node_ids=(
            "air:W1-region-A",
            "air:W1-region-B",
            "air:W1-region-C",
            "body:skin",
            "body:core",
        ),
        initial_temperatures_millikelvin=(
            296_150,
            296_150,
            296_150,
            303_150,
            309_950,
        ),
        capacities_microjoules_per_millikelvin=(
            50_000_000,
            100_000_000,
            50_000_000,
            4_700_000,
            42_000_000,
        ),
        fixed_conductive_edges=(
            ConductiveThermalEdge(4, 3, 6_102_941),
        ),
        room_air_node_by_region_id=tuple(
            (region_id, index) for index, region_id in enumerate(REGIONS)
        ),
        skin_node_index=3,
        core_node_index=4,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        bath_edges=tuple(
            ThermalBathEdge(index, 296_150, 250_000_000)
            for index in range(3)
        ),
        power_sources=(ThermalPowerSource(4, 41_500_000),),
        parameter_provenance=("test-only exact thermal anatomy",),
    )


def _authority() -> ThermallyCoupledEmbodimentWorldAuthority:
    return ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
    )


def _prepare(authority: ThermallyCoupledEmbodimentWorldAuthority):
    before = authority.observation_snapshot()
    return authority.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(AdvancePhysicalTimeCommand(250_000)),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )


def test_prepare_is_thermally_pure_and_commit_advances_one_circuit() -> None:
    authority = _authority()
    before = authority.thermal_observation()
    prepared = _prepare(authority)

    assert isinstance(prepared, PreparedActionExecution)
    assert authority.thermal_observation() == before

    authority.commit_prepared_action(prepared)
    after = authority.thermal_observation()

    assert after.world_revision == before.world_revision + 1
    assert after.latest_transition_receipt_sha256 is not None
    assert after.temperatures_millikelvin != before.temperatures_millikelvin
    assert after.temperatures_millikelvin[4] > Fraction(309_950)


def test_discard_does_not_change_world_or_thermal_state() -> None:
    authority = _authority()
    before_world = authority.encoded_snapshot()
    before_thermal = authority.thermal_observation()
    prepared = _prepare(authority)

    authority.discard_prepared_action(prepared)

    assert authority.encoded_snapshot() == before_world
    assert authority.thermal_observation() == before_thermal


def test_committed_rollback_restores_world_and_thermal_state() -> None:
    authority = _authority()
    before_world = authority.encoded_snapshot()
    before_thermal = authority.thermal_observation()
    prepared = _prepare(authority)
    authority.commit_prepared_action(prepared)

    with authority.committed_prepared_action_rollback_transaction(
        prepared
    ) as rollback:
        rollback()

    assert authority.encoded_snapshot() == before_world
    assert authority.thermal_observation() == before_thermal


def test_one_authenticated_cold_body_restores_latest_thermal_tail() -> None:
    authority = _authority()
    prepared = _prepare(authority)
    authority.commit_prepared_action(prepared)
    encoded = authority.encoded_snapshot()
    expected = authority.thermal_observation()

    restored = _authority()
    restored.restore_encoded(encoded)

    assert restored.encoded_snapshot() == encoded
    assert restored.thermal_observation() == expected


def test_body_surface_contact_reaches_exact_skin_site_and_retains_all_heat() -> None:
    f = Fraction
    x = ExactVector3(f(1), f(0), f(0))
    y = ExactVector3(f(0), f(1), f(0))
    z = ExactVector3(f(0), f(0), f(1))
    material = BodySurfaceMaterial(f(2), f(2), f(2))

    def site(
        body_id: str,
        normal: ExactVector3,
        tangent_u: ExactVector3,
        topology_index: int | None,
    ) -> MountedBodySurfaceSite:
        return MountedBodySurfaceSite(
            body_id=body_id,
            site_id="palm",
            local_centre_micrometres=ExactVector3(f(250_000), f(0), f(0)),
            outward_normal=normal,
            tangent_u=tangent_u,
            tangent_v=z,
            half_extent_u_micrometres=f(10 if topology_index is not None else 5),
            half_extent_v_micrometres=f(10 if topology_index is not None else 5),
            material=material,
            reference_temperature_millikelvin=310_150,
            cutaneous_topology_index=topology_index,
        )

    authority = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_800, 0), 195_962),
                radius_mm=250,
                reach_mm=800,
            ),
            EmbodiedBody(
                "w1-body-2",
                PoseMM(PositionMM(1_500, 1_800, 0), 30_000),
                radius_mm=250,
                reach_mm=1_200,
            ),
        ),
        body_surface_sites=(
            site("guala-body-1", x, y, 4),
            site("w1-body-2", x, y.scaled(f(-1)), None),
        ),
    )
    command = BodySurfaceContactCommand(
        actuations=(
            BodySurfaceActuation(
                actor_site_id="palm",
                recipient_body_id="guala-body-1",
                recipient_site_id="palm",
                compression_micrometres=1,
                tangential_u_micrometres=1,
                tangential_v_micrometres=0,
            ),
        ),
        duration_microseconds=3_000,
    )

    for _ in range(2):
        prior_residue = authority._body_surface_heat_residue_nanojoules
        before = authority.observation_snapshot()
        prepared = authority.prepare_port_command(
            port_id=SECOND_BODY_PORT_ID,
            command_payload=encode_command(command),
            causal_intent_receipt_sha256="b" * 64,
            expected_revision=before.revision,
        )
        assert isinstance(prepared, PreparedActionExecution)
        contact = authority.body_surface_contacts_for_prepared_action(prepared)
        assert len(contact) == 1
        assert contact[0].recipient_cutaneous_topology_index == 4
        admitted_heat = sum(
            phase.conductive_heat_to_a_nanojoules
            for phase in contact[0].physical_phases
        )
        assert admitted_heat > 0
        expected_whole_heat = int((prior_residue + admitted_heat) / 1_000)
        expected_residue = (
            prior_residue + admitted_heat - expected_whole_heat * 1_000
        )
        authority.commit_prepared_action(prepared)
        assert (
            authority._latest_thermal_transition
            .body_surface_heat_into_skin_microjoules
            == expected_whole_heat
        )
        assert (
            authority._body_surface_heat_residue_nanojoules
            == expected_residue
        )

    encoded = authority.encoded_snapshot()
    restored = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
        bodies=authority.observation_snapshot().bodies,
        body_surface_sites=(
            site("guala-body-1", x, y, 4),
            site("w1-body-2", x, y.scaled(f(-1)), None),
        ),
    )
    restored.restore_encoded(encoded)
    assert restored.encoded_snapshot() == encoded


def test_receptor_anatomy_migration_rebinds_thermal_custody() -> None:
    source = _authority()
    geometry = source.observation_snapshot().bodies[0].receptor_geometry
    assert geometry is not None

    bare = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
        bodies=tuple(
            EmbodiedBody(
                body_id=item.body_id,
                pose=item.pose,
                radius_mm=item.radius_mm,
                reach_mm=item.reach_mm,
                receptor_geometry=(
                    None
                    if item.body_id == "guala-body-1"
                    else item.receptor_geometry
                ),
            )
            for item in source.observation_snapshot().bodies
        ),
    )
    bare_encoded = bare.encoded_snapshot()

    restored = _authority()
    restored.restore_encoded(bare_encoded)
    prior_revision = restored.thermal_observation().world_revision
    assert restored.migrate_declared_body_receptor_geometry() is True
    assert restored.thermal_observation().world_revision == prior_revision + 1
    assert (
        restored.observation_snapshot().bodies[0].receptor_geometry
        == geometry
    )


def test_material_transport_migration_rebinds_thermal_custody() -> None:
    seed = _authority()
    snapshot = seed.observation_snapshot()
    regions = tuple(
        replace(
            item,
            air=AirVolumeState(
                volume_cubic_mm=(
                    (item.bounds.maximum.x - item.bounds.minimum.x)
                    * (item.bounds.maximum.y - item.bounds.minimum.y)
                    * (item.bounds.maximum.z - item.bounds.minimum.z)
                ),
                odorant_mass_nanograms=(index + 1,) * 8,
            ),
        )
        for index, item in enumerate(snapshot.regions)
    )
    portals = tuple(
        replace(item, air_flow_cubic_mm_per_second=2_000_000)
        for item in snapshot.portals
    )
    material = ObjectMaterialState(
        odorant_reservoir_nanograms=(8_640_000,) * 8,
        odorant_release_nanograms_per_second=(10,) * 8,
        tastant_mass_micrograms=(1, 2, 3, 4, 5),
        surface_temperature_millikelvin=292_000,
        compliance_ppm=120_000,
        roughness_micrometers=15,
        moisture_ppm=850_000,
    )
    objects = tuple(
        replace(item, material=material)
        if index == 0 else item
        for index, item in enumerate(snapshot.objects)
    )
    declared = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
        bodies=snapshot.bodies,
        regions=regions,
        portals=portals,
        initial_objects=objects,
    )
    legacy = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="thermally-coupled-world-test-key",
        thermal_anatomy=_anatomy(),
        bodies=snapshot.bodies,
        regions=tuple(replace(item, air=None) for item in regions),
        portals=tuple(
            replace(item, air_flow_cubic_mm_per_second=None)
            for item in portals
        ),
        initial_objects=tuple(
            replace(item, material=None) for item in objects
        ),
    )
    declared.restore_encoded(legacy.encoded_snapshot())
    prior_revision = declared.thermal_observation().world_revision

    assert declared.migrate_declared_material_transport() is True
    assert declared.thermal_observation().world_revision == prior_revision + 1
    assert declared.observation_snapshot().objects[0].material == material


def test_bare_world_requires_explicit_one_time_thermal_genesis() -> None:
    source = _authority()
    bare_world = super(
        ThermallyCoupledEmbodimentWorldAuthority, source
    ).encoded_snapshot()
    restored = _authority()

    with pytest.raises(ValueError, match="explicit thermal genesis"):
        restored.restore_encoded(bare_world)

    restored.restore_encoded(bare_world, allow_legacy_thermal_genesis=True)
    assert restored.thermal_observation().world_revision == 0


def test_coupled_cold_body_refuses_tampering() -> None:
    authority = _authority()
    encoded = bytearray(authority.encoded_snapshot())
    encoded[-10] ^= 1

    with pytest.raises(ValueError):
        _authority().restore_encoded(bytes(encoded))


def test_atomic_action_paths_always_enter_thermal_before_world_lock() -> None:
    authority = _authority()
    entered: list[str] = []

    class RecordingLock:
        def __init__(self, name: str, lock: object) -> None:
            self.name = name
            self.lock = lock

        def __enter__(self):
            entered.append(self.name)
            self.lock.acquire()
            return self

        def __exit__(self, *_error: object) -> None:
            self.lock.release()

    authority._thermal_lock = RecordingLock(  # type: ignore[assignment]
        "thermal", authority._thermal_lock
    )
    authority._lock = RecordingLock("world", authority._lock)  # type: ignore[assignment]

    before = authority.observation_snapshot()
    entered.clear()
    authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(AdvancePhysicalTimeCommand(1_000)),
        causal_intent_receipt_sha256="b" * 64,
        expected_revision=before.revision,
    )

    assert entered[0] == "thermal"
    assert entered.index("thermal") < entered.index("world")
