"""Positive ordinary-path component witness; not learned-language evidence.

The participant is explicitly new. There are no pre-excited organs, supplied
END carriers, seeded plastic contacts, authored speech or legacy decisions.
The four-quarter horizon contains the first real460ms source completion, its
250ms material delivery and the existing250ms self-pressure delay. A failure
is a physical/admission finding; it must not trigger fixture gain/drive tuning.
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

from test_functional64_owner import ACQUISITION, BOUNDS, MIB, wire
from dsf_ai_service.guala_cochlea import CochlearStream, STREAM_CHECKPOINT_BYTES
from dsf_ai_service.guala_functional64_loop import Functional64PhysicalLoop
from dsf_ai_service.guala_functional64_runtime import EnvelopeBounds, Functional64Runtime
from dsf_ai_service.guala_functional64_world import commission_home_world, verify_world_current
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_joint_source_acquisition import pack_source_geometry
from dsf_ai_service.paired_current_store import PairedCurrentStore


IDENTITY = "5507f270-4dc5-421e-a6ab-0ec3be102530"
SILENCE = bytes(8000)
PHASE_BYTES = 20_480 * 2 * 8


def neutral_participant():
    native = guala_core.ModularSubstrate64D()
    history = guala_core.exact_capture_native_current(native, 2*MIB, 4*MIB, 0)
    del native
    original_world = home_world_authority(identity=IDENTITY)
    snapshot = original_world.canonical_observation_snapshot()
    geometry, sites = pack_source_geometry(original_world, snapshot.self_body_id, ACQUISITION)
    body = guala_core.exact_commission_articulated_body_v9((0, 0, 0, 0, 0, 0, 10_000, 10_000))
    # Explicit preceding quiet physical interval of this new fixture. Continuous
    # ears are then advanced by the ordinary caller; they are never reset.
    ears = CochlearStream()
    ears.advance(SILENCE, SILENCE, start_sample=0)
    ear_bytes = ears.checkpoint_bytes()
    assert len(ear_bytes) == STREAM_CHECKPOINT_BYTES == 3156
    heat = original_world._thermal_anatomy.power_sources[0]
    thermal = (b"GL64TH01" + bytes.fromhex(original_world._thermal_anatomy.receipt_sha256)
               + struct.pack("<QQ", heat.node_index, heat.power_microwatts))
    core = guala_core.exact_commission_functional64_current(
        history, body, geometry, len(sites), IDENTITY, 0, 0,
        500_000, 500_000, thermal, heat.power_microwatts,
        -250, ear_bytes, SILENCE, (0,)*97, 0, BOUNDS,
        (2*MIB, 4*MIB, 0), (4*MIB, 1, 512*MIB),
    )
    old_world = original_world.encoded_snapshot()
    old_body = b"GLFUNC01" + json.dumps({"schema": "guala.functional_organism.v1", "identity": IDENTITY, "tick": 0}).encode("utf-8")
    encoded_limit = BOUNDS[0] + len(old_body) + len(old_world) + struct.calcsize("<8sHQQQ")
    bounds = EnvelopeBounds(encoded_limit, 4*encoded_limit + 2*BOUNDS[0], BOUNDS)
    runtime = Functional64Runtime.from_commissioned(
        core, old_body, old_world, original_identity=IDENTITY, original_tick=0, bounds=bounds,
    )
    world = commission_home_world(original_world=old_world, core=core)
    return runtime, world, bounds, old_body, old_world, ear_bytes


def actual_phases(core):
    raw = core.phase_pairs_le
    assert type(raw) is bytes and len(raw) == PHASE_BYTES
    return struct.unpack("<40960d", raw)


def verify_end_receipt(core, summary):
    rows = summary["terminal_end_discharges"]
    assert len(rows) <= 250 * 97
    prior = (0, -1)
    pending = [0] * 97
    for offset, terminal, carriers in rows:
        assert type(offset) is int and 1 <= offset <= 250
        assert type(terminal) is int and 0 <= terminal < 97
        assert type(carriers) is int and 0 < carriers < 1 << 64
        assert (offset, terminal) > prior
        prior = offset, terminal
        if offset == 250:
            pending[terminal] = carriers
    # Last native END is the actual next1ms state, not re-emitted on restore.
    assert core.pending_terminal_carriers == tuple(pending)


def test_neutral_world_source_reaches64_and_native_pressure_survives_cold(tmp_path, monkeypatch):
    monkeypatch.setenv("GUALA_SOLAR_UTC_OVERRIDE", "1791000000")
    runtime, world, bounds, original_body, original_world, ear_bytes = neutral_participant()
    core = runtime.core
    before = core.encoded()
    assert actual_phases(core) == (0.0,) * 40960
    assert core.pending_terminal_carriers == (0,) * 97
    assert core.field_delivery_evidence == ()
    assert core.pending_self_pcm_s16le == SILENCE
    assert core.encoded() == before  # Explicit getters are read-only.
    initial_axes = core.body_axes
    loop = Functional64PhysicalLoop(world, runtime, ACQUISITION)
    ears = CochlearStream.restore(ear_bytes)
    previous_pressure = SILENCE
    results = []
    phases_before_first_field = None
    pair_root = tmp_path / "pair"
    store = PairedCurrentStore(pair_root, max_body_bytes=bounds.encoded_bytes,
                               max_world_bytes=world._max_encoded_state_bytes)
    checkpoint = None
    for quarter in range(4):
        if quarter == 1:
            phases_before_first_field = actual_phases(runtime.core)
        result = loop.unattended(runtime, world)
        results.append(result)
        verify_world_current(world, runtime.core)
        summary = result.observation["native_physical_summary"]
        verify_end_receipt(runtime.core, summary)
        assert result.native_interval_count == 1
        assert result.observation["said"] is None
        assert result.observation["python_callback_count"] == 0
        assert result.pressure is not None and len(result.pressure[1]) == 8000
        ears.advance(previous_pressure, previous_pressure, start_sample=ears.sample_count)
        assert ears.checkpoint_bytes() == runtime.core.cochlear_current_bytes
        assert runtime.core.pending_self_pcm_s16le == result.pressure[1]
        previous_pressure = result.pressure[1]
        if quarter == 1:
            # The actual first46th10ms completion is460ms; at500ms a real
            # installed gate has progressed. Exact gate endings may have
            # installed=False, because the NEXT gate is awaiting its next1ms.
            cursors = runtime.core.field_delivery_evidence
            assert any(n*1000 == 460*d and (gate > 0 or installed)
                       for _identity, (n, d), gate, _remaining, installed in cursors)
            after = actual_phases(runtime.core)
            assert phases_before_first_field is not None
            changed_columns = tuple(column for column in range(64)
                                    if after[column*640:(column+1)*640]
                                    != phases_before_first_field[column*640:(column+1)*640])
            assert changed_columns == tuple(range(64))
            checkpoint = store.publish(identity=IDENTITY, organism_tick=runtime.live_organism_tick,
                                       body=runtime.encoded(), world=world.encoded_snapshot(),
                                       expected_current_body_sha256=None)
    assert runtime.core.body_axes != initial_axes
    discharges = [(row.observation["source_millisecond_start"] + offset, terminal, count)
                  for row in results
                  for offset, terminal, count in row.observation["native_physical_summary"]["terminal_end_discharges"]]
    respiratory_ends = [time for time, terminal, _count in discharges if terminal == 96]
    assert respiratory_ends, "ordinary neutral source produced no respiratory END"
    pressure = b"".join(row.pressure[1] for row in results)
    first_respiratory_end = min(respiratory_ends)
    # Spectral tract shape alone cannot generate breath. No pressure may
    # precede the actual respiratory END; its first application starts at END.
    assert not any(pressure[:first_respiratory_end * 32])
    assert any(pressure[:3*8000]), "no ordinary pressure arrived in time for self-hearing"
    # Full-field publication is460ms. Its first consuming native interval ends
    # at461ms; those END carriers first reach the body in the following1ms.
    post_field_respiratory_ends = [time for time in respiratory_ends if time >= 461]
    assert post_field_respiratory_ends, "no respiratory END followed actual full-field delivery"
    assert any(pressure[min(post_field_respiratory_ends)*32:3*8000]), (
        "no actual pressure followed a post-field respiratory END before750ms"
    )
    assert checkpoint is not None
    restored = store.restore()
    assert restored.pointer.current == checkpoint.current

    extension = Path(guala_core.__file__).resolve()
    output_file = tmp_path / "cold_observations.json"
    child = r'''
import hashlib, importlib.util, json, sys
from pathlib import Path
extension, expected_digest, pair_path, output_path, encoded_limit, staged_limit, world_limit, limits = sys.argv[1:]
assert hashlib.sha256(Path(extension).read_bytes()).hexdigest() == expected_digest
spec = importlib.util.spec_from_file_location("guala_core", extension)
module = importlib.util.module_from_spec(spec)
sys.modules["guala_core"] = module
spec.loader.exec_module(module)
from dsf_ai_service.guala_functional64_runtime import EnvelopeBounds, Functional64Runtime
from dsf_ai_service.guala_functional64_loop import Functional64PhysicalLoop
from dsf_ai_service.guala_functional64_world import restore_home_world, verify_world_current
from dsf_ai_service.guala_joint_source_acquisition import AcquisitionBounds, pack_source_geometry
from dsf_ai_service.paired_current_store import PairedCurrentStore
native_bounds = tuple(json.loads(limits))
bounds = EnvelopeBounds(int(encoded_limit), int(staged_limit), native_bounds)
acquisition = AcquisitionBounds(native_bounds[10], native_bounds[11], 128)
store = PairedCurrentStore(Path(pair_path), max_body_bytes=int(encoded_limit), max_world_bytes=int(world_limit))
restored = store.restore()
pointer = restored.pointer.current
world = restore_home_world(identity=pointer.identity, encoded=restored.world)
geometry, sites = pack_source_geometry(world, world.canonical_observation_snapshot().self_body_id, acquisition)
runtime = Functional64Runtime.restore(restored.body, geometry_record=geometry, surface_sites=len(sites), bounds=bounds)
verify_world_current(world, runtime.core)
assert runtime.encoded() == restored.body and world.encoded_snapshot() == restored.world
assert runtime.identity == pointer.identity and runtime.live_organism_tick == pointer.organism_tick
old_body, old_world = runtime._current.history.body, runtime._current.history.world
loop = Functional64PhysicalLoop(world, runtime, acquisition)
observed = []
for _ in range(2):
    result = loop.unattended(runtime, world)
    verify_world_current(world, runtime.core)
    observed.append((result.native_interval_count, result.observation, result.pressure))
    published = store.publish(identity=runtime.identity, organism_tick=runtime.live_organism_tick,
                              body=runtime.encoded(), world=world.encoded_snapshot(),
                              expected_current_body_sha256=pointer.body_sha256)
    assert published.predecessor == pointer
    pointer = published.current
assert runtime._current.history.body == old_body and runtime._current.history.world == old_world
assert store.restore().body == runtime.encoded()
def wire(value):
    if isinstance(value, bytes): return {"bytes": value.hex()}
    if isinstance(value, (tuple, list)): return [wire(item) for item in value]
    if isinstance(value, dict): return {key:wire(item) for key,item in value.items()}
    return value
Path(output_path).write_text(json.dumps(wire(observed), allow_nan=False))
'''
    project = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(project), environment.get("PYTHONPATH", "")))
    subprocess.run(
        [sys.executable, "-c", child, str(extension), hashlib.sha256(extension.read_bytes()).hexdigest(),
         str(pair_root), str(output_file), str(bounds.encoded_bytes), str(bounds.staged_bytes),
         str(world._max_encoded_state_bytes), json.dumps(BOUNDS)],
        check=True, timeout=180, env=environment, cwd=project, capture_output=True, text=True,
    )
    cold = store.restore()
    assert cold.body == runtime.encoded()
    assert cold.world == world.encoded_snapshot()
    assert json.loads(output_file.read_text()) == wire([
        (r.native_interval_count, r.observation, r.pressure) for r in results[2:]
    ])
    assert runtime._current.history.body == original_body
    assert runtime._current.history.world == original_world
