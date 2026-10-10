"""Current codec and actual next-interval component witnesses.

The fixture explicitly commissions new material from an actual new native
capture. Declared external test carriers excite the already tested V9 organ.
This is not mature production capture, autonomous feeding or learned speech.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import guala_core
import pytest

from dsf_ai_service.guala_cochlea import CochlearStream, STREAM_CHECKPOINT_BYTES
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_joint_source_acquisition import (
    AcquisitionBounds, acquire_world_optical, pack_source_geometry,
)

# Explicit fixture admission, not a production resource derivation. Parent
# runs this component within its separate bounded process envelope.
MIB = 1024 * 1024
# Derived platform resource envelope:
# max_owner_bytes = 2048*MIB (derived from 8192 MB production ECS Fargate container,
# covering observation 46 full 7-source DSF field snapshot of ~1.66 GB).
# max_force_terms = 6_000_000_000 (derived from MAX_REFINEMENT=6 depth bisection tree
# on the 64-column ArcLoom mesh under 7-source transient field gradient:
# 381 trial intervals * up to 14.5M force operations per span = 5.52B terms + 10% safety margin = 6.0B terms,
# completing in ~4-5s per transient ms, replacing arbitrary unphysical inflation and unverified 50M limit).
BOUNDS = (2048*MIB, 6_000_000_000, 10_000_000, 256*MIB, 512*MIB,
          46, 187_176, 187_176, 4096, 2048*MIB, 8*MIB, 512, 768*MIB)
ACQUISITION = AcquisitionBounds(8*MIB, 512, 128)
IDENTITY = "55cfc700-79dc-4531-8412-0b6c7b06034a"


def wire(value):
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, (tuple, list)):
        return [wire(x) for x in value]
    if isinstance(value, dict):
        return {key: wire(x) for key, x in value.items()}
    return value


@pytest.fixture(scope="module")
def owner_fixture():
    native = guala_core.ModularSubstrate64D()
    history = guala_core.exact_capture_native_current(native, 2*MIB, 4*MIB, 0)
    del native
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.canonical_observation_snapshot()
    geometry, sites = pack_source_geometry(world, snapshot.self_body_id, ACQUISITION)
    body = guala_core.exact_commission_articulated_body_v9((0, 0, 0, 0, 0, 0, 10_000, 10_000))
    # Actual previous-quarter organ pressure from explicit effector fixtures.
    drives = tuple((axis, 1, 8) for axis in (18, 37, 38, 39, 40, 41, 42, 43, 44))
    body, previous_pcm, *_ = guala_core.exact_articulatory_body_interval(body, drives, 8, 250_000)
    assert len(previous_pcm) == 8000
    ears = CochlearStream()
    ears.advance(bytes(8000), bytes(8000), start_sample=0)
    ear_bytes = ears.checkpoint_bytes()
    assert len(ear_bytes) == STREAM_CHECKPOINT_BYTES == 3156
    source = world._thermal_anatomy.power_sources[0]
    thermal = (b"GL64TH01" + bytes.fromhex(world._thermal_anatomy.receipt_sha256)
               + struct.pack("<QQ", source.node_index, source.power_microwatts))
    core = guala_core.exact_commission_functional64_current(
        history, body, geometry, len(sites), IDENTITY, 137, 0,
        500_000, 500_000, thermal, source.power_microwatts,
        -250, ear_bytes, previous_pcm, (0,)*97, 0, BOUNDS,
        (2*MIB, 4*MIB, 0), (4*MIB, 1, 512*MIB),
    )
    optical = acquire_world_optical(
        snapshot, core.body_axes, acquired_millisecond=0, available_millisecond=0,
        sun=None, acquisition_provenance=snapshot.authority_receipt_sha256.encode("ascii"),
        bounds=ACQUISITION,
    )
    return core, geometry, len(sites), optical, previous_pcm, thermal, ear_bytes


def test_owner_codec_keeps_actual_organ_ear_fifo_and_unpublished_interval(owner_fixture):
    core, geometry, sites, optical, previous, thermal, ears = owner_fixture
    encoded = core.encoded()
    restored = guala_core.Functional64Core.restore(encoded, geometry, sites, BOUNDS)
    assert restored.encoded() == encoded
    assert restored.identity == IDENTITY and restored.organism_tick == 137
    assert restored.pending_self_pcm_s16le == previous
    assert restored.cochlear_current_bytes == ears
    assert restored.thermal_source_identities == (thermal,)
    assert restored.body_axes == core.body_axes
    original_step = core.prepare_beat(optical)
    cold_step = restored.prepare_beat(optical)
    before = original_step.prepare_millisecond()
    after = cold_step.prepare_millisecond()
    assert before == after
    assert before[0] == 0 and before[8] == previous[:32]
    assert len(before[9]) == 32
    assert original_step.prepared_body_evidence == cold_step.prepared_body_evidence
    assert core.encoded() == restored.encoded() == encoded
    with pytest.raises(ValueError, match="ordering"):
        cold_step.prepare_millisecond()
    with pytest.raises(ValueError, match="incomplete"):
        cold_step.finish(ears)
    with pytest.raises((TypeError, ValueError)):
        restored.prepare_beat(b"GL64OP01")
    assert core.encoded() == encoded


def test_owner_fresh_process_uses_same_extension_and_exact_current(owner_fixture, tmp_path):
    core, geometry, sites, optical, previous, thermal, ears = owner_fixture
    current_file = tmp_path / "current.bin"
    geometry_file = tmp_path / "geometry.bin"
    optical_file = tmp_path / "optical.bin"
    output_file = tmp_path / "successor.json"
    current_file.write_bytes(core.encoded())
    geometry_file.write_bytes(geometry)
    optical_file.write_bytes(optical)
    expected = core.prepare_beat(optical)
    expected_transport = expected.prepare_millisecond()
    expected_receipt = expected.prepared_body_evidence
    child = r'''
import importlib.util, json, sys
from pathlib import Path
extension, current_path, geometry_path, optical_path, output_path, sites, limits = sys.argv[1:]
spec = importlib.util.spec_from_file_location("guala_core", extension)
module = importlib.util.module_from_spec(spec)
sys.modules["guala_core"] = module
spec.loader.exec_module(module)
from dsf_ai_service.guala_cochlea import CochlearStream
raw = Path(current_path).read_bytes()
core = module.Functional64Core.restore(raw, Path(geometry_path).read_bytes(), int(sites), tuple(json.loads(limits)))
assert core.encoded() == raw
CochlearStream.restore(core.cochlear_current_bytes)
def wire(value):
    if isinstance(value, bytes): return {"bytes": value.hex()}
    if isinstance(value, (tuple, list)): return [wire(v) for v in value]
    if isinstance(value, dict): return {k:wire(v) for k,v in value.items()}
    return value
step = core.prepare_beat(Path(optical_path).read_bytes())
result = step.prepare_millisecond()
Path(output_path).write_text(json.dumps(wire((result, step.prepared_body_evidence))))
assert core.encoded() == raw
'''
    environment = dict(os.environ)
    project = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join((project, environment.get("PYTHONPATH", "")))
    subprocess.run(
        [sys.executable, "-c", child, str(Path(guala_core.__file__).resolve()),
         str(current_file), str(geometry_file), str(optical_file), str(output_file),
         str(sites), json.dumps(BOUNDS)],
        check=True, timeout=180, env=environment, cwd=project,
        capture_output=True, text=True,
    )
    assert json.loads(output_file.read_text()) == wire((expected_transport, expected_receipt))
