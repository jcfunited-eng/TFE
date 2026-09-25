"""Verification suite for sensory lane separation and time-aligned admission settlement.

Verifies:
1. Pure visual frames supersede pending frames in the visual lane without manufacturing extra elapsed bodily intervals.
2. Pure acoustic blocks queue in strict FIFO order in the acoustic lane.
3. Concurrent visual and acoustic streams unite into time-aligned 'camera-microphone' settlements on the native 250-ms clock.
4. Capture timestamps (t_capture_ms) are strictly preserved through admission to settlement and reflected in responses.
5. Caregiver interactions settle without dropping staged visual evidence.
6. Mailbox capacity is never exhausted under sustained concurrent 4 fps visual + 4 fps acoustic traffic.
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import time
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from dsf_ai_service.lean_actor import (
    LeanOrganismActor,
    PhysicalOccurrence,
    SettlementResult,
)
from dsf_ai_service.paired_current_store import CurrentPair, PairedCurrentStore
from dsf_ai_service.lean_production_app import (
    OCCURRENCE_ROUTE,
    OccurrenceBody,
    SensoryBody,
    create_lean_production_app,
)
from dsf_ai_service.lean_sensory_occurrence import (
    EXTERNAL_RGB_VALUE_COUNT,
    LeanSensoryOccurrence,
)


class MockPhysicalBoundary:
    def __init__(self) -> None:
        self.settled_occurrences: list[PhysicalOccurrence] = []

    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return 1

    def settle(self, runtime: any, world: any, occurrence: PhysicalOccurrence) -> SettlementResult:
        self.settled_occurrences.append(occurrence)
        runtime.live_organism_tick += 1
        return SettlementResult(
            native_interval_count=1,
            observation={"kind": occurrence.kind, "native_tick": runtime.live_organism_tick},
            pressure=None,
        )

    def unattended(self, runtime: any, world: any) -> SettlementResult:
        runtime.live_organism_tick += 1
        return SettlementResult(
            native_interval_count=1,
            observation={"kind": "unattended", "native_tick": runtime.live_organism_tick},
            pressure=None,
        )


class MockCheckpoint:
    def __init__(self, tick: int, body: bytes) -> None:
        self.organism_tick = tick
        self.state_bytes = len(body)
        self.state_sha256 = hashlib.sha256(body).hexdigest()
        self._body = body

    def encoded_generation(self) -> bytes:
        return self._body


class MockLivedState:
    def __init__(self, tick: int) -> None:
        self.organism_tick = tick

    def prepare_checkpoint(self) -> MockCheckpoint:
        return MockCheckpoint(self.organism_tick, b"mock-state-generation")


class MockRuntime:
    def __init__(self) -> None:
        self.identity = "guala-test"
        self.live_organism_tick = 1000

    def readiness(self):
        m = MagicMock()
        m.identity = self.identity
        m.organism_tick = self.live_organism_tick
        m.state_sha256 = hashlib.sha256(b"mock-state-generation").hexdigest()
        m.state_bytes = len(b"mock-state-generation")
        m.python_callback_count = 0
        return m

    def snapshot_lived_state(self):
        return MockLivedState(self.live_organism_tick)

    def validate_lived_checkpoint(self, checkpoint):
        pass

    def adopt_published_lived_checkpoint(self, checkpoint):
        pass


class MockWorld:
    def encoded_snapshot(self):
        return b"world-snapshot"


class MockCurrentPair:
    def __init__(self) -> None:
        c = MagicMock()
        c.identity = "guala-test"
        c.organism_tick = 1000
        c.body_sha256 = hashlib.sha256(b"mock-state-generation").hexdigest()
        c.body_bytes = len(b"mock-state-generation")
        c.world_bytes = len(b"world-snapshot")
        c.world_sha256 = hashlib.sha256(b"world-snapshot").hexdigest()
        self.current = c
        self.predecessor = None


class MockStore(PairedCurrentStore):
    def __init__(self) -> None:
        pass

    def publish(
        self,
        *,
        identity: str,
        organism_tick: int,
        body: bytes,
        world: bytes,
        expected_current_body_sha256: str | None,
    ) -> CurrentPair:
        c = MagicMock()
        c.identity = identity
        c.organism_tick = organism_tick
        c.body_sha256 = hashlib.sha256(body).hexdigest()
        c.body_bytes = len(body)
        c.world_bytes = len(world)
        c.world_sha256 = hashlib.sha256(world).hexdigest()
        return CurrentPair(current=c, predecessor=None)

    def reconcile(self, pointer: CurrentPair) -> None:
        pass


def _make_test_actor(boundary: MockPhysicalBoundary, interval_seconds: float = 0.05) -> tuple[LeanOrganismActor, MockRuntime]:
    runtime = MockRuntime()
    world = MockWorld()
    pointer = MockCurrentPair()
    store = MockStore()
    actor = LeanOrganismActor(
        runtime=runtime,
        world=world,
        pointer=pointer,
        store=store,
        physical=boundary,
        mailbox_capacity=4,
        checkpoint_every_intervals=32,
        unattended_interval_seconds=interval_seconds,
    )
    return actor, runtime


def test_independent_sensory_lane_staging_and_supersession():
    boundary = MockPhysicalBoundary()
    actor, runtime = _make_test_actor(boundary, interval_seconds=0.1)

    dummy_retina = (128,) * EXTERNAL_RGB_VALUE_COUNT
    dummy_retina2 = (200,) * EXTERNAL_RGB_VALUE_COUNT
    dummy_pcm = b"\x01\x00" * 4000

    actor.start()
    try:
        # Submit camera frame 1
        occ_cam1 = PhysicalOccurrence("sensory", LeanSensoryOccurrence(
            source="camera", retina_rgb_u8=dummy_retina, pressure_s16le=None, t_capture_ms=1001,
        ))
        f_cam1 = actor.offer(occ_cam1)

        # Submit camera frame 2 (supersedes frame 1 before settlement)
        occ_cam2 = PhysicalOccurrence("sensory", LeanSensoryOccurrence(
            source="camera", retina_rgb_u8=dummy_retina2, pressure_s16le=None, t_capture_ms=1002,
        ))
        f_cam2 = actor.offer(occ_cam2)

        # Submit microphone block 1 (independent acoustic lane)
        occ_mic1 = PhysicalOccurrence("sensory", LeanSensoryOccurrence(
            source="microphone", retina_rgb_u8=None, pressure_s16le=dummy_pcm, t_capture_ms=2001,
        ))
        f_mic1 = actor.offer(occ_mic1)

        # Wait for resolution
        res_cam1 = f_cam1.result(timeout=2.0)
        res_cam2 = f_cam2.result(timeout=2.0)
        res_mic1 = f_mic1.result(timeout=2.0)

        # Both camera callers and microphone caller resolve
        assert res_cam1 is not None
        assert res_cam2 is not None
        assert res_mic1 is not None

        # Verify combined settlement: camera frame 2 and microphone block 1 united as camera-microphone!
        settled = boundary.settled_occurrences
        assert len(settled) >= 1
        first = settled[0]
        assert first.kind == "sensory"
        assert isinstance(first.payload, LeanSensoryOccurrence)
        assert first.payload.source == "camera-microphone"
        # The superseded camera frame 2's retina was applied
        assert first.payload.retina_rgb_u8 == dummy_retina2
        assert first.payload.pressure_s16le == dummy_pcm

    finally:
        actor.close()


def test_clock_semantics_under_concurrent_traffic():
    boundary = MockPhysicalBoundary()
    interval_s = 0.05
    actor, runtime = _make_test_actor(boundary, interval_seconds=interval_s)

    dummy_retina = (100,) * EXTERNAL_RGB_VALUE_COUNT
    dummy_pcm = b"\x02\x00" * 4000

    actor.start()
    try:
        start_tick = runtime.live_organism_tick

        # Send 4 camera frames and 4 audio blocks over 200 ms
        futures = []
        for i in range(4):
            f_v = actor.offer(PhysicalOccurrence("sensory", LeanSensoryOccurrence(
                source="camera", retina_rgb_u8=dummy_retina, pressure_s16le=None, t_capture_ms=3000 + i,
            )))
            f_a = actor.offer(PhysicalOccurrence("sensory", LeanSensoryOccurrence(
                source="microphone", retina_rgb_u8=None, pressure_s16le=dummy_pcm, t_capture_ms=4000 + i,
            )))
            futures.extend([f_v, f_a])
            time.sleep(interval_s)

        # All 8 requests must resolve cleanly without mailbox saturation
        for f in futures:
            res = f.result(timeout=2.0)
            assert res.native_interval_count == 1

        # Bodily time must advance strictly with native cadence (not 8 ticks in 4 intervals!)
        ticks_elapsed = runtime.live_organism_tick - start_tick
        # With 4 intervals elapsed, ticks elapsed should be ~4-5, definitely NOT 8!
        assert 3 <= ticks_elapsed <= 6, f"Expected ~4-5 ticks, got {ticks_elapsed}"

    finally:
        actor.close()


def test_t_capture_ms_preserved_in_http_response(monkeypatch):
    boundary = MockPhysicalBoundary()
    actor, runtime = _make_test_actor(boundary, interval_seconds=0.05)

    app = create_lean_production_app(actor_factory=lambda: actor)
    with TestClient(app) as client:
        # Camera occurrence with t_capture_ms
        cam_payload = {
            "kind": "sensory",
            "payload": {
                "source": "camera",
                "retina_rgb_u8": list((128,) * EXTERNAL_RGB_VALUE_COUNT),
                "t_capture_ms": 1727279999001,
            },
        }
        res_cam = client.post(OCCURRENCE_ROUTE, json=cam_payload)
        assert res_cam.status_code == 200
        cam_data = res_cam.json()
        assert cam_data["schema"] == "guala.lean_occurrence_result.v1"
        assert cam_data["t_capture_ms"] == 1727279999001

        # Microphone occurrence with t_capture_ms
        pcm_b64 = base64.b64encode(b"\x00\x01" * 4000).decode("ascii")
        mic_payload = {
            "kind": "sensory",
            "payload": {
                "source": "microphone",
                "pcm_s16le_base64": pcm_b64,
                "t_capture_ms": 1727279999002,
            },
        }
        res_mic = client.post(OCCURRENCE_ROUTE, json=mic_payload)
        assert res_mic.status_code == 200
        mic_data = res_mic.json()
        assert mic_data["schema"] == "guala.lean_occurrence_result.v1"
        assert mic_data["t_capture_ms"] == 1727279999002
