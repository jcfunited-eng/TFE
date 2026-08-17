"""A-002 persistence proof for the exact world constructed by production."""

from __future__ import annotations

import hashlib

import pytest

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    DEFAULT_MAX_ENCODED_STATE_BYTES,
    MoveCommand,
    PORT_ID,
    encode_command,
)


@pytest.fixture()
def production_world(monkeypatch, tmp_path):
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(production, "WORLD_AUTHORIZED", True)
    monkeypatch.setattr(production, "_world_authority", None)
    monkeypatch.setenv(
        "GUALA_NATIVE_ORGANISM_IDENTITY",
        "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1",
    )
    yield tmp_path
    production._world_authority = None


def test_exact_production_home_consequence_persists_and_cold_restores(
    production_world,
) -> None:
    authority = production._world()
    before = authority.observation_snapshot()
    body = next(item for item in before.bodies if item.body_id == before.self_body_id)
    command = MoveCommand(
        target_pose=type(body.pose)(body.pose.position, 1_000),
        duration_microseconds=1_000,
    )

    execution = authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=hashlib.sha256(
            b"a002 exact persisted world consequence"
        ).hexdigest(),
        expected_revision=before.revision,
    )

    assert execution.disposition == "applied"
    assert execution.before == before
    assert execution.after.revision == before.revision + 1
    assert execution.after.state_sha256 != before.state_sha256
    assert execution.after.objects != ()
    production._persist_world(authority)
    persisted = (production_world / production.WORLD_STATE_FILE).read_bytes()
    assert persisted == authority.encoded_snapshot()
    assert len(persisted) <= DEFAULT_MAX_ENCODED_STATE_BYTES

    production._world_authority = None
    restored = production._world()
    assert restored.encoded_snapshot() == persisted
    assert restored.observation_snapshot() == execution.after


def test_corrupt_persisted_home_refuses_instead_of_rebuilding(
    production_world,
) -> None:
    authority = production._world()
    production._persist_world(authority)
    path = production_world / production.WORLD_STATE_FILE
    corrupt = bytearray(path.read_bytes())
    corrupt[len(corrupt) // 2] ^= 1
    path.write_bytes(bytes(corrupt))
    production._world_authority = None

    with pytest.raises(
        RuntimeError,
        match="refusing to replace Guala's causal pose history",
    ):
        production._world()
    assert path.read_bytes() == bytes(corrupt)


def test_bare_world_migration_persists_thermal_body_before_exposure(
    production_world,
) -> None:
    authority = production._world()
    bare_world = super(type(authority), authority).encoded_snapshot()
    path = production_world / production.WORLD_STATE_FILE
    path.write_bytes(bare_world)
    production._world_authority = None

    restored = production._world()
    coupled = restored.encoded_snapshot()

    assert coupled != bare_world
    assert path.read_bytes() == coupled
    assert restored.thermal_observation().world_revision == 0


def test_world_observation_is_read_only_and_bounded(production_world) -> None:
    authority = production._world()
    before = authority.encoded_snapshot()

    response = production.world_observation()

    assert response.status_code == 200
    assert authority.encoded_snapshot() == before
    payload = bytes(response.body)
    assert len(payload) < len(before)
    assert b'"revision":0' in payload
    assert b'"region_count":4' in payload
    assert b'"object_count":15' in payload
    assert b'"body_count":2' in payload
