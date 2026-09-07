from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.guala_physical_sensorium import (
    PORT_COUNT,
    compact_signal_body,
)
from dsf_ai_service.guala_world_sensorium import (
    passive_sensorium,
    prepare_passive_world_interval,
)
from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalPowerSource,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    CoupledThermalAnatomy,
    ThermallyCoupledEmbodimentWorldAuthority,
)


def _world() -> ThermallyCoupledEmbodimentWorldAuthority:
    regions = ("W1-region-A", "W1-region-B", "W1-region-C")
    anatomy = CoupledThermalAnatomy(
        node_ids=(
            "air:W1-region-A",
            "air:W1-region-B",
            "air:W1-region-C",
            "body:cutaneous-shell",
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
        fixed_conductive_edges=(ConductiveThermalEdge(4, 3, 6_102_941),),
        room_air_node_by_region_id=tuple(
            (region_id, index) for index, region_id in enumerate(regions)
        ),
        skin_node_index=3,
        core_node_index=4,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        bath_edges=tuple(
            ThermalBathEdge(index, 296_150, 250_000_000)
            for index in range(3)
        ),
        power_sources=(ThermalPowerSource(4, 41_500_000),),
        parameter_provenance=("exact test thermal anatomy",),
    )
    return ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="lean-world-sensorium-test-key-0001",
        thermal_anatomy=anatomy,
    )


BODY_AXES = (
    (0, "neck_yaw", "millidegree", 0, -180_000, 0, 180_000),
    (1, "left_eyelid_aperture", "micrometre", 160, 0, 0, 320),
    (2, "right_eyelid_aperture", "micrometre", 320, 0, 0, 320),
)


def _commit(world: ThermallyCoupledEmbodimentWorldAuthority):
    prepared = prepare_passive_world_interval(world)
    with world.prepared_action_visibility_transaction(prepared):
        execution = world.commit_prepared_action(prepared)
    return prepared, execution


def test_real_world_passive_interval_builds_complete_truthful_sensorium() -> None:
    world = _world()
    before = world.observation_snapshot()
    _prepared, execution = _commit(world)
    sensorium = passive_sensorium(
        world=world,
        snapshot=execution.after,
        body_axes=BODY_AXES,
        frame_count=26,
    )
    after = world.observation_snapshot()

    assert after.revision == before.revision + 1
    assert len(sensorium.ordered_ports()) == PORT_COUNT
    assert len(compact_signal_body(sensorium, frame_count=26)) == (
        PORT_COUNT * 26 * 8
    )
    assert all(len(trajectory) == 26 for trajectory in sensorium.ordered_ports())
    assert sensorium.legacy_ears == ((Fraction(0),) * 26,) * 2
    assert sensorium.cochleae == ((Fraction(0),) * 26,) * 32
    assert sensorium.articulation == ((Fraction(0),) * 26,) * 4
    assert sensorium.retina[0][0] == sensorium.retina[0][-1]
    assert sensorium.thermal[0][0] != sensorium.thermal[1][0]


def test_committed_world_interval_can_roll_back_after_native_refusal() -> None:
    world = _world()
    before = bytes(world.encoded_snapshot())
    prepared, _execution = _commit(world)
    with world.committed_prepared_action_rollback_transaction(
        prepared
    ) as rollback:
        rollback()
    assert bytes(world.encoded_snapshot()) == before
