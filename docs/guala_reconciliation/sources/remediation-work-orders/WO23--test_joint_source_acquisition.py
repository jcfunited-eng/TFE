"""Actual immutable Home acquisition evidence; no cognition/feeding claims."""
from fractions import Fraction
import struct

import guala_core
import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_joint_source_acquisition import (
    AcquisitionBounds, acquire_world_optical, pack_source_geometry,
)
from dsf_ai_service.substrate.w1_physical_receptors import retinal_irradiance_field


BOUNDS = AcquisitionBounds(8 * 1024 * 1024, 512, 128)


def _axes(body):
    positions = struct.unpack_from(">45i", body, 10)
    return tuple((*row[:3], positions[row[0]], *row[3:])
                 for row in guala_core.exact_articulated_body_axis_contract(9))


def _optical_record(raw):
    assert raw[:8] == b"GL64OP01"
    cursor = 24

    def integer():
        nonlocal cursor
        value, = struct.unpack_from("<Q", raw, cursor)
        cursor += 8
        return value

    def blob():
        nonlocal cursor
        size = integer()
        value = raw[cursor:cursor + size]
        cursor += size
        return value

    def fraction():
        return Fraction(int.from_bytes(blob(), "little"), int.from_bytes(blob(), "little"))

    identity = blob()
    assert integer() == 116_010
    values = tuple(fraction() for _ in range(116_010))
    assert integer() == 480
    power = tuple(fraction() for _ in range(480))
    assert cursor == len(raw)
    return identity, values, power


def test_real_home_six_band_acquisition_preserves_all_exact_readings_and_world():
    world = home_world_authority(identity="5f9f6747-cd42-4282-b2be-9e055149dfb9")
    before = world.encoded_snapshot()
    snapshot = world.observation_snapshot()
    # This fixture acquires an immutable public snapshot. The complete owner's
    # private boundary supplies its own original provenance, separately from the
    # changed private physical scene; no signed snapshot is manufactured there.
    provenance = snapshot.authority_receipt_sha256.encode("ascii")
    geometry, sites = pack_source_geometry(world, snapshot.self_body_id, BOUNDS)
    assert geometry[:8] == b"GL64SG01"
    assert struct.unpack_from("<Q", geometry, 8) == (19_335,)
    assert len(sites) <= 32
    body = guala_core.exact_commission_articulated_body_v9((0, 0, 0, 0, 0, 0, 12_000, 12_000))
    encoded = acquire_world_optical(
        snapshot, _axes(body), acquired_millisecond=0, available_millisecond=0,
        sun=None, acquisition_provenance=provenance, bounds=BOUNDS,
    )
    _identity, values, power = _optical_record(encoded)
    actual = retinal_irradiance_field(snapshot, include_focal=True, sun=None)
    assert values == tuple(value for bands in actual for value in bands)
    disconnected = {(0, 3), (0, 6), (1, 3), (1, 6), (6, 3), (6, 6), (7, 3), (7, 6)}
    assert all(power[60 * column + 6 * row + band] == 0
               for column, row in disconnected for band in range(6))
    assert all(0 <= value <= 100 for value in power)
    # Acquisition precedes shutters. The native source/release applies the
    # actual current lids at each real endpoint, preserving held illumination.
    closed = guala_core.exact_commission_articulated_body_v9((0, 0, 0, 0, 0, 0, 0, 0))
    closed_record = acquire_world_optical(
        snapshot, _axes(closed), acquired_millisecond=0, available_millisecond=0,
        sun=None, acquisition_provenance=provenance, bounds=BOUNDS,
    )
    assert closed_record == encoded
    assert world.encoded_snapshot() == before
    restored = home_world_authority(
        identity="5f9f6747-cd42-4282-b2be-9e055149dfb9", encoded_world=before,
    )
    cold_snapshot = restored.observation_snapshot()
    restored_record = acquire_world_optical(
        cold_snapshot, _axes(body), acquired_millisecond=0, available_millisecond=0,
        sun=None, acquisition_provenance=cold_snapshot.authority_receipt_sha256.encode("ascii"),
        bounds=BOUNDS,
    )
    assert restored_record == encoded
    with pytest.raises(ValueError, match="admission"):
        acquire_world_optical(
            snapshot, _axes(body), acquired_millisecond=0, available_millisecond=0,
            sun=None, acquisition_provenance=provenance,
            bounds=AcquisitionBounds(32, 512, 128),
        )
