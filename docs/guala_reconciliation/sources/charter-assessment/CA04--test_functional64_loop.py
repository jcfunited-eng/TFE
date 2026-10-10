"""Ordinary caller/persistence witnesses, never mature learning/autonomy proof.

All participants are explicitly new test fixtures. The legacy genesis record
is inert original-envelope custody; no legacy cognition is run. The retained
organ excitation in owner_fixture is an explicit prior physical test drive.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import guala_core
from test_functional64_owner import owner_fixture, ACQUISITION, BOUNDS, IDENTITY, wire
from dsf_ai_service.guala_functional64_loop import Functional64PhysicalLoop
from dsf_ai_service.guala_functional64_runtime import EnvelopeBounds, Functional64Runtime
from dsf_ai_service.guala_functional64_world import commission_home_world, verify_world_current
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.paired_current_store import PairedCurrentStore


def test_complete_quarters_persist_exact_pair_and_continue_in_fresh_process(owner_fixture, tmp_path, monkeypatch):
    # Fixed external clock is a disclosed fixture boundary, never a live solar claim.
    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", "1791000000")
    core, _geometry, _sites, _optical, _previous, _thermal, _ears = owner_fixture
    original_world = home_world_authority(identity=IDENTITY).encoded_snapshot()
    original_body = b"GLFUNC01" + json.dumps({"schema": "guala.functional_organism.v1", "identity": IDENTITY, "tick": 137}).encode("utf-8")
    encoded_limit = BOUNDS[0] + len(original_body) + len(original_world) + struct.calcsize("<8sHQQQ")
    bounds = EnvelopeBounds(encoded_limit, 4 * encoded_limit + 2 * BOUNDS[0], BOUNDS)
    runtime = Functional64Runtime.from_commissioned(
        core, original_body, original_world, original_identity=IDENTITY,
        original_tick=137, bounds=bounds,
    )
    world = commission_home_world(original_world=original_world, core=core)
    loop = Functional64PhysicalLoop(world, runtime, ACQUISITION)
    observed = []
    for _ in range(2):
        predecessor = runtime.live_organism_tick
        result = loop.unattended(runtime, world)
        assert runtime.live_organism_tick == predecessor + 1
        assert result.native_interval_count == 1
        assert result.observation["python_callback_count"] == 0
        assert result.observation["cochlear_frame_count"] == 25
        assert result.observation["said"] is None
        observed.append(result.observation["native_physical_summary"])
        verify_world_current(world, runtime.core)
    # Actual source delivery is a prerequisite, not evidence of learned speech.
    assert sum(row["fields_delivered"] for row in observed) > 0
    body = runtime.encoded()
    world_bytes = world.encoded_snapshot()
    pair_root = tmp_path / "pair"
    store = PairedCurrentStore(pair_root, max_body_bytes=encoded_limit,
                               max_world_bytes=world._max_encoded_state_bytes)
    current = store.publish(identity=IDENTITY, organism_tick=runtime.live_organism_tick,
                            body=body, world=world_bytes, expected_current_body_sha256=None)
    restored = store.restore()
    assert restored.body == body and restored.world == world_bytes
    expected = loop.unattended(runtime, world)
    extension = Path(guala_core.__file__).resolve()
    output_file = tmp_path / "observation.json"
    child = r'''
import hashlib, importlib.util, json, os, sys
from pathlib import Path
extension, expected_digest, pair_path, output_path, encoded_limit, staged_limit, world_limit, limits = sys.argv[1:]
assert hashlib.sha256(Path(extension).read_bytes()).hexdigest() == expected_digest
spec = importlib.util.spec_from_file_location("guala_core", extension)
module = importlib.util.module_from_spec(spec)
sys.modules["guala_core"] = module
spec.loader.exec_module(module)
# Reject legacy cognition imports in the actual serving restore path. Original
# history is raw retained bytes; this child never constructs legacy genesis.
class NoLegacyCognition:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"dsf_ai_service.guala_functional_organism",
                        "dsf_ai_service.guala_functional_loop",
                        "dsf_ai_service.substrate.native_core"}:
            raise AssertionError("serving restore attempted retired cognition: " + fullname)
        return None
sys.meta_path.insert(0, NoLegacyCognition())
os.environ["GUALA_PAIRED_ROOT"] = pair_path
os.environ["GUALA_MAX_WORLD_BYTES"] = world_limit
os.environ["GUALA64_ADMISSION_JSON"] = json.dumps({
    "encoded_bytes": int(encoded_limit), "staged_bytes": int(staged_limit),
    "native": json.loads(limits), "events": 128,
})
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.guala_functional64_world import verify_world_current
actor = _restore_production_actor()
try:
    actor._verify_restored_authorities()
    runtime, world, store = actor._runtime, actor._world, actor._store
    current = actor._pointer.current
    restored = store.restore()
    assert runtime.encoded() == restored.body and world.encoded_snapshot() == restored.world
    original_body = runtime._current.history.body
    original_world = runtime._current.history.world
    # A single controlled ordinary actor call permits deterministic comparison;
    # this component does not claim wall-clock unattended scheduling evidence.
    result = actor._settle(PhysicalOccurrence("unattended", None))
    assert runtime.live_organism_tick == current.organism_tick + 1
    verify_world_current(world, runtime.core)
    assert runtime._current.history.body == original_body and runtime._current.history.world == original_world
    actor._finish_checkpoint()
    successor = store.restore()
    assert successor.pointer.predecessor == current
    assert successor.pointer.current == actor._pointer.current
    assert successor.body == runtime.encoded() and successor.world == world.encoded_snapshot()
    actor._verify_restored_authorities()
    observation = actor.observation()
    assert observation["live_tick"] == observation["persisted_tick"] == runtime.live_organism_tick
    assert observation["last_occurrence"]["native_physical_summary"] == result.observation["native_physical_summary"]
    def wire(value):
        if isinstance(value, bytes): return {"bytes": value.hex()}
        if isinstance(value, (tuple, list)): return [wire(item) for item in value]
        if isinstance(value, dict): return {key: wire(item) for key, item in value.items()}
        return value
    Path(output_path).write_text(json.dumps(wire((result.native_interval_count, result.observation, result.pressure)), allow_nan=False))
finally:
    actor.close()
'''
    project = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(project), environment.get("PYTHONPATH", "")))
    subprocess.run(
        [sys.executable, "-c", child, str(extension), hashlib.sha256(extension.read_bytes()).hexdigest(),
         str(pair_root), str(output_file), str(encoded_limit), str(bounds.staged_bytes),
         str(world._max_encoded_state_bytes), json.dumps(BOUNDS)],
        check=True, timeout=1800, env=environment, cwd=project, capture_output=True, text=True,
    )
    successor = store.restore()
    assert successor.pointer.predecessor == current.current
    assert successor.body == runtime.encoded()
    assert successor.world == world.encoded_snapshot()
    assert json.loads(output_file.read_text()) == wire(
        (expected.native_interval_count, expected.observation, expected.pressure)
    )
    assert runtime._current.history.body == original_body
    assert runtime._current.history.world == original_world
