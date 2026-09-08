from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest

from dsf_ai_service.lean_actor import (
    LeanOrganismActor,
    PhysicalOccurrence,
    SettlementResult,
)
from dsf_ai_service.lean_production_app import (
    MAX_OCCURRENCE_BODY_BYTES,
    OBSERVATION_ROUTE,
    OCCURRENCE_ROUTE,
    PRESSURE_ROUTE,
    _restore_production_actor,
    create_lean_production_app,
)
from dsf_ai_service.paired_current_store import PairedCurrentStore


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
PRESSURE = b"\x01\x00\xfe\xff" * 16
PRESSURE_SHA256 = hashlib.sha256(PRESSURE).hexdigest()


@dataclass(slots=True)
class _Readiness:
    identity: str
    organism_tick: int
    state_sha256: str
    state_bytes: int
    python_callback_count: int = 0


@dataclass(slots=True)
class _Checkpoint:
    organism_tick: int
    body: bytes

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def state_bytes(self) -> int:
        return len(self.body)

    def encoded_generation(self) -> bytes:
        return self.body


@dataclass(slots=True)
class _Snapshot:
    organism_tick: int
    body: bytes

    def prepare_checkpoint(self) -> _Checkpoint:
        return _Checkpoint(self.organism_tick, self.body)


class _Runtime:
    def __init__(self, body: bytes) -> None:
        self.tick = 10
        self.persisted_tick = 10
        self.persisted = body

    @property
    def live_organism_tick(self) -> int:
        return self.tick

    def readiness(self) -> _Readiness:
        return _Readiness(
            IDENTITY,
            self.persisted_tick,
            hashlib.sha256(self.persisted).hexdigest(),
            len(self.persisted),
        )

    def snapshot_lived_state(self) -> _Snapshot:
        return _Snapshot(self.tick, f"body-{self.tick}".encode())

    def validate_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        assert checkpoint.organism_tick <= self.tick

    def adopt_published_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        self.persisted_tick = checkpoint.organism_tick
        self.persisted = checkpoint.body


class _World:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def encoded_snapshot(self) -> bytes:
        return self.body


class _Physical:
    def __init__(self) -> None:
        self.count = 0

    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return 1

    def settle(
        self,
        runtime: _Runtime,
        world: _World,
        occurrence: PhysicalOccurrence,
    ) -> SettlementResult:
        assert occurrence == PhysicalOccurrence("unattended", None)
        self.count += 1
        runtime.tick += 1
        world.body = f"world-{runtime.tick}".encode()
        return SettlementResult(
            native_interval_count=1,
            observation={"causal": True},
            pressure=(PRESSURE_SHA256, PRESSURE) if self.count == 1 else None,
        )

    def unattended(self, runtime: _Runtime, world: _World) -> SettlementResult:
        return self.settle(runtime, world, PhysicalOccurrence("unattended", None))


class _FatalUnattendedPhysical(_Physical):
    def unattended(self, runtime: _Runtime, world: _World) -> SettlementResult:
        raise RuntimeError("unattended physical failure")


@dataclass(frozen=True, slots=True)
class _Admission:
    max_envelope_bytes: int = 4096
    max_fabric_bytes: int = 3072
    max_logical_peak_bytes: int = 8192


def _actor(
    root: Path,
    *,
    physical: _Physical | None = None,
    unattended_interval_seconds: float = 60,
) -> LeanOrganismActor:
    body = b"body-10"
    world_body = b"world-10"
    store = PairedCurrentStore(
        root,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    pointer = store.publish(
        identity=IDENTITY,
        organism_tick=10,
        body=body,
        world=world_body,
        expected_current_body_sha256=None,
    )
    return LeanOrganismActor(
        runtime=_Runtime(body),
        world=_World(world_body),
        pointer=pointer,
        store=store,
        physical=physical or _Physical(),
        mailbox_capacity=1,
        checkpoint_every_intervals=4,
        unattended_interval_seconds=unattended_interval_seconds,
    )


def test_exact_five_routes_and_one_bounded_pressure_receipt(
    tmp_path: Path,
) -> None:
    actor = _actor(tmp_path)
    application = create_lean_production_app(lambda: actor)
    pressure_path = PRESSURE_ROUTE.format(receipt=PRESSURE_SHA256)
    assert sorted(route.path for route in application.routes) == [
        "/api/v1/guala/observation",
        "/api/v1/guala/occurrence",
        "/api/v1/guala/pressure/{receipt}",
        "/health",
        "/ready",
    ]

    with TestClient(application) as client:
        assert client.get("/health").json() == {
            "alive": True,
            "schema": "guala.lean_health.v1",
        }
        assert client.get("/ready").json() == {"ready": True}
        assert client.get("/docs").status_code == 404
        assert client.get("/observation").status_code == 404
        assert client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None, "extra": True},
        ).status_code == 422
        assert client.post(
            OCCURRENCE_ROUTE,
            content=b"x" * (MAX_OCCURRENCE_BODY_BYTES + 1),
        ).status_code == 413

        first = client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None},
        )
        assert first.status_code == 200
        assert first.json()["pressure_sha256"] == PRESSURE_SHA256
        pressure = client.get(pressure_path)
        assert pressure.status_code == 200
        assert pressure.content == PRESSURE
        assert pressure.headers["content-type"] == "application/octet-stream"
        assert pressure.headers["etag"] == f'"{PRESSURE_SHA256}"'
        assert pressure.headers["x-guala-pcm-channels"] == "1"
        assert pressure.headers["x-guala-pcm-encoding"] == (
            "signed-16-little-endian"
        )
        assert pressure.headers["x-guala-pcm-sample-rate-hz"] == "16000"

        second = client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None},
        )
        assert second.status_code == 200
        assert second.json()["pressure_sha256"] is None
        observation = client.get(OBSERVATION_ROUTE).json()
        assert observation["pressure_sha256"] == PRESSURE_SHA256
        assert client.get(pressure_path).content == PRESSURE
        assert client.get(
            PRESSURE_ROUTE.format(receipt="not-a-receipt")
        ).status_code == 404


def test_health_fails_when_the_organism_owner_fails(tmp_path: Path) -> None:
    actor = _actor(
        tmp_path,
        physical=_FatalUnattendedPhysical(),
        unattended_interval_seconds=0.01,
    )
    application = create_lean_production_app(lambda: actor)

    with pytest.raises(RuntimeError, match="organism actor stopped after failure"):
        with TestClient(application) as client:
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                response = client.get("/health")
                if response.status_code == 503:
                    break
                time.sleep(0.005)
            assert response.status_code == 503
            assert response.json() == {
                "alive": False,
                "schema": "guala.lean_health.v1",
            }


def test_startup_publishes_native_migration_before_actor_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from dsf_ai_service import lean_production_app
    from dsf_ai_service.glew_runtime import native_resident_organism
    from dsf_ai_service.substrate import native_resident_resource_admission

    predecessor_body = b"body-10-v41"
    migrated_body = b"body-10-v42"
    world_body = b"world-10"
    store = PairedCurrentStore(
        tmp_path,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    predecessor = store.publish(
        identity=IDENTITY,
        organism_tick=10,
        body=predecessor_body,
        world=world_body,
        expected_current_body_sha256=None,
    )
    calls: list[tuple[str, bytes]] = []

    def migrate(**values: object) -> bytes:
        assert values["current_envelope"] == predecessor_body
        assert values["expected_predecessor_sha256"] == (
            predecessor.current.body_sha256
        )
        calls.append(("migrate", predecessor_body))
        return migrated_body

    def restore(**values: object) -> _Runtime:
        body = values["current_envelope"]
        assert isinstance(body, bytes)
        calls.append(("restore", body))
        return _Runtime(body)

    monkeypatch.setenv("GUALA_PAIRED_ROOT", str(tmp_path))
    monkeypatch.setenv("GUALA_MAX_WORLD_BYTES", "4096")
    monkeypatch.setattr(
        native_resident_resource_admission,
        "derive_native_resident_resource_admission",
        lambda _root: _Admission(),
    )
    monkeypatch.setattr(
        native_resident_organism,
        "migrate_native_resident_organism_exact_energy",
        migrate,
    )
    monkeypatch.setattr(
        native_resident_organism,
        "restore_native_resident_organism",
        restore,
    )
    monkeypatch.setattr(
        lean_production_app,
        "home_world_authority",
        lambda *, identity, encoded_world: (
            _World(encoded_world) if identity == IDENTITY else None
        ),
    )

    actor = _restore_production_actor()
    actor.start()
    actor.close()

    current = store.restore()
    assert calls == [("migrate", predecessor_body), ("restore", migrated_body)]
    assert current.body == migrated_body
    assert current.world == world_body
    assert current.pointer.current.identity == IDENTITY
    assert current.pointer.current.organism_tick == 10
    assert current.pointer.predecessor == predecessor.current
