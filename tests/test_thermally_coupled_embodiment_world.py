from fractions import Fraction

import pytest

from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalPowerSource,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    AdvancePhysicalTimeCommand,
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
