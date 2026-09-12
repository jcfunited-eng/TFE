from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
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
    PRESSURE_FEED_ROUTE,
    _restore_production_actor,
    create_lean_production_app,
)
from dsf_ai_service.paired_current_store import PairedCurrentStore


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
PRESSURE = b"\x01\x00\xfe\xff" * 16
PRESSURE_SHA256 = hashlib.sha256(PRESSURE).hexdigest()
SECOND_PRESSURE = b"\x03\x00\xfc\xff" * 16
SECOND_PRESSURE_SHA256 = hashlib.sha256(SECOND_PRESSURE).hexdigest()
THIRD_PRESSURE = b"\x05\x00\xfa\xff" * 16
THIRD_PRESSURE_SHA256 = hashlib.sha256(THIRD_PRESSURE).hexdigest()


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
    pending_physical_return = None

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


class _ChangingPressurePhysical(_Physical):
    def settle(
        self,
        runtime: _Runtime,
        world: _World,
        occurrence: PhysicalOccurrence,
    ) -> SettlementResult:
        assert occurrence == PhysicalOccurrence("unattended", None)
        pressures = (
            (PRESSURE_SHA256, PRESSURE),
            (SECOND_PRESSURE_SHA256, SECOND_PRESSURE),
            (THIRD_PRESSURE_SHA256, THIRD_PRESSURE),
        )
        pressure = pressures[self.count]
        self.count += 1
        runtime.tick += 1
        world.body = f"world-{runtime.tick}".encode()
        return SettlementResult(
            native_interval_count=1,
            observation={"causal": True},
            pressure=pressure,
        )


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


def test_exact_six_routes_and_bounded_pressure_receipt(
    tmp_path: Path,
) -> None:
    actor = _actor(tmp_path)
    application = create_lean_production_app(lambda: actor)
    pressure_path = PRESSURE_ROUTE.format(receipt=PRESSURE_SHA256)
    assert sorted(route.path for route in application.routes) == [
        "/api/v1/guala/observation",
        "/api/v1/guala/occurrence",
        "/api/v1/guala/pressure",
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


def test_three_emissions_remain_fetchable_in_the_bounded_feed(
    tmp_path: Path,
) -> None:
    actor = _actor(tmp_path, physical=_ChangingPressurePhysical())
    application = create_lean_production_app(lambda: actor)

    with TestClient(application) as client:
        first = client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None},
        )
        assert first.json()["pressure_sha256"] == PRESSURE_SHA256
        second = client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None},
        )
        assert second.json()["pressure_sha256"] == SECOND_PRESSURE_SHA256
        assert client.get(
            PRESSURE_ROUTE.format(receipt=PRESSURE_SHA256)
        ).content == PRESSURE
        assert client.get(
            PRESSURE_ROUTE.format(receipt=SECOND_PRESSURE_SHA256)
        ).content == SECOND_PRESSURE

        third = client.post(
            OCCURRENCE_ROUTE,
            json={"kind": "unattended", "payload": None},
        )
        assert third.json()["pressure_sha256"] == THIRD_PRESSURE_SHA256
        assert client.get(
            PRESSURE_ROUTE.format(receipt=PRESSURE_SHA256)
        ).content == PRESSURE
        assert client.get(
            PRESSURE_ROUTE.format(receipt=SECOND_PRESSURE_SHA256)
        ).content == SECOND_PRESSURE
        assert client.get(
            PRESSURE_ROUTE.format(receipt=THIRD_PRESSURE_SHA256)
        ).content == THIRD_PRESSURE


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


@pytest.mark.parametrize(("wrong_tick", "capacity_refused"), [
    (False, False), (True, False), (False, True),
])
def test_startup_validates_both_components_before_migration_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    wrong_tick: bool,
    capacity_refused: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from dsf_ai_service import lean_production_app, guala_receptor_anatomy
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
        runtime = _Runtime(body)
        if wrong_tick:
            runtime.tick = runtime.persisted_tick = 11
        return runtime

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
    anatomy = object()
    monkeypatch.setattr(guala_receptor_anatomy, "receptor_anatomy", lambda: anatomy)

    def admit_workspace(runtime, **values):
        assert values == {
            "anatomy": anatomy, "primary_frames": 27, "hearing_frames": 26,
            "hearing_sense": 1, "maximum_pressure_samples": 4000,
            "coupled_encoded_limit": 4 * 1024 * 1024,
        }
        calls.append(("admit", runtime.persisted))
        if capacity_refused:
            raise ValueError("ordinary physical input needs more logical working bytes")

    def restore_world(*, identity, encoded_world, migrate_physical_return):
        assert identity == IDENTITY and migrate_physical_return
        assert calls[-1] == ("admit", migrated_body)
        calls.append(("world", encoded_world))
        return _World(encoded_world)

    monkeypatch.setattr(_Runtime, "admit_ordinary_physical_workspace", admit_workspace, raising=False)
    monkeypatch.setattr(lean_production_app, "home_world_authority", restore_world)

    if wrong_tick:
        with pytest.raises(RuntimeError, match="native identity/tick"):
            _restore_production_actor()
        assert store.read_pointer() == predecessor
        assert capsys.readouterr().out == ""
        return

    if capacity_refused:
        with pytest.raises(ValueError, match="logical working bytes"):
            _restore_production_actor()
        assert calls == [("migrate", predecessor_body), ("restore", migrated_body),
                         ("admit", migrated_body)]
        assert store.read_pointer() == predecessor
        assert store.restore().body == predecessor_body
        assert capsys.readouterr().out == ""
        return

    receipt = {
        "schema": "guala.paired_predecessor.v1",
        "identity": IDENTITY,
        "organism_tick": 10,
        "body_sha256": hashlib.sha256(predecessor_body).hexdigest(),
        "body_bytes": len(predecessor_body),
        "world_sha256": hashlib.sha256(world_body).hexdigest(),
        "world_bytes": len(world_body),
    }
    publish = PairedCurrentStore.publish
    receipts = []

    def checked_publish(self, **values):
        # The old CURRENT receipt must already exist BEFORE publication replaces it.
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1
        receipts.append(json.loads(lines[0]))
        assert receipts == [receipt]
        return publish(self, **values)

    monkeypatch.setattr(PairedCurrentStore, "publish", checked_publish)
    actor = _restore_production_actor()
    assert receipts == [receipt]
    assert capsys.readouterr().out == ""
    monkeypatch.setattr(PairedCurrentStore, "publish", publish)
    actor.start()
    actor.close()

    current = store.restore()
    assert calls == [
        ("migrate", predecessor_body), ("restore", migrated_body),
        ("admit", migrated_body), ("world", world_body),
    ]
    assert current.body == migrated_body
    assert current.world == world_body
    assert current.pointer.current.identity == IDENTITY
    assert current.pointer.current.organism_tick == 10
    assert current.pointer.predecessor == predecessor.current


class _RepeatedPressurePhysical(_Physical):
    def settle(self, runtime, world, occurrence):
        result = super().settle(runtime, world, occurrence)
        return SettlementResult(
            result.native_interval_count, result.observation,
            (PRESSURE_SHA256, PRESSURE),
        )


def test_emission_feed_preserves_identical_events_and_reports_gaps(tmp_path):
    actor = _actor(tmp_path, physical=_RepeatedPressurePhysical())
    with TestClient(create_lean_production_app(lambda: actor)) as client:
        head = client.get(PRESSURE_FEED_ROUTE).json()
        assert head["events"] == [] and head["cursor"] == 0
        cursor = {"stream": head["stream"], "after": 0}
        for _ in range(3):
            assert client.post(OCCURRENCE_ROUTE, json={"kind": "unattended"}).status_code == 200
        feed = client.get(PRESSURE_FEED_ROUTE, params=cursor)
        assert feed.headers["cache-control"] == "no-store"
        record = feed.json()
        assert [event["tick"] for event in record["events"]] == [11, 12, 13]
        assert all(
            base64.b64decode(event["pcm_s16le_base64"]) == PRESSURE
            and event["sha256"] == PRESSURE_SHA256
            for event in record["events"]
        )
        assert client.get(PRESSURE_FEED_ROUTE, params=cursor).json() == record
        cursor["after"] = record["cursor"]
        assert client.get(PRESSURE_FEED_ROUTE, params=cursor).json()["events"] == []
        assert client.get(PRESSURE_FEED_ROUTE).json()["cursor"] == 13
        assert client.get(PRESSURE_FEED_ROUTE, params={"after": 0}).status_code == 422
        assert client.get(PRESSURE_FEED_ROUTE, params={"stream": head["stream"]}).status_code == 422
        for after in (-1, 1 << 64):
            assert client.get(PRESSURE_FEED_ROUTE, params={**cursor, "after": after}).status_code == 422
        restart = client.get(PRESSURE_FEED_ROUTE, params={
            "stream": "f" * 32 if head["stream"] != "f" * 32 else "e" * 32,
            "after": 13,
        }).json()
        assert restart["gap"] == "stream-restarted" and restart["events"] == []
        ahead = client.get(PRESSURE_FEED_ROUTE, params={**cursor, "after": 14}).json()
        assert ahead["gap"] == "cursor-ahead" and ahead["cursor"] == 13

        for _ in range(31):
            assert client.post(OCCURRENCE_ROUTE, json={"kind": "unattended"}).status_code == 200
        evicted, held = actor._pressure_feed
        assert evicted == 12 and len(held) == 32
        assert sum(len(item[2]) for item in held) <= 256000
        gap = client.get(PRESSURE_FEED_ROUTE, params={
            "stream": head["stream"], "after": 11,
        }).json()
        assert gap["gap"] == "audio-evicted" and gap["events"] == []
        assert gap["cursor"] == 44
        batch = client.get(PRESSURE_FEED_ROUTE, params={
            "stream": head["stream"], "after": 12,
        }).json()
        assert batch["gap"] is None
        assert [event["tick"] for event in batch["events"]] == list(range(13, 21))
        assert batch["cursor"] == 20 and batch["latest"] == 44
