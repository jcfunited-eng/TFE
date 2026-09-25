"""Retention ordinary actor proof on one authenticated disposable live pair."""
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time
import zlib

signal.alarm(150)
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence

def store_at(root):
    admission = derive_native_resident_resource_admission(root)
    return PairedCurrentStore(root, max_body_bytes=admission.max_envelope_bytes,
                              max_world_bytes=int(os.environ["GUALA_MAX_WORLD_BYTES"]))

def verify_actor(actor, pair):
    assert actor._runtime.encoded() == pair.body
    assert bytes(actor._world.encoded_snapshot()) == pair.world
    assert actor._pointer == pair.pointer

def persisted(actor, store):
    pair = store.restore()
    assert actor._runtime.encoded() == pair.body
    assert bytes(actor._world.encoded_snapshot()) == pair.world
    assert actor._pointer == pair.pointer
    return pair

if len(sys.argv) == 2 and sys.argv[1] == "--fresh":
    store = store_at(Path(os.environ["GUALA_PAIRED_ROOT"]))
    before = store.restore()
    actor = _restore_production_actor()
    verify_actor(actor, before)
    actor.start()
    try:
        result = actor.submit(PhysicalOccurrence("unattended", None), timeout=45)
    finally:
        actor.close()
    after = persisted(actor, store)
    assert after.pointer.current.identity == before.pointer.current.identity
    assert after.pointer.current.organism_tick > before.pointer.current.organism_tick
    assert after.pointer.current.body_sha256 != before.pointer.current.body_sha256
    print(json.dumps({"fresh_process_next_interval": True,
        "before": asdict(before.pointer.current), "after": asdict(after.pointer.current),
        "act": result.observation.get("her_act")}), flush=True)
    sys.exit(0)

text = Path("/tmp/a1-capture.log").read_text()
assert "truncated output" not in text
parts = re.findall(r"A1_CAPTURE_PART (\d+):([^\r\n]+)", text)
raw = ""
for offset, part in parts:
    assert int(offset) == len(raw)
    raw += part
assert len(raw) == int(re.search(r"A1_CAPTURE_START (\d+)", text).group(1))
assert hashlib.sha256(raw.encode()).hexdigest() == re.search(r"A1_CAPTURE_END ([a-f0-9]+)", text).group(1)
record = json.loads(raw)
descriptor = record["pointer"]["current"]
body = zlib.decompress(base64.b64decode(record["body_zlib"]))
world = zlib.decompress(base64.b64decode(record["world_zlib"]))
for name, data in (("body", body), ("world", world)):
    assert len(data) == descriptor[name + "_bytes"]
    assert hashlib.sha256(data).hexdigest() == descriptor[name + "_sha256"]
root = Path(tempfile.mkdtemp(prefix="a1-retention-proof-"))
os.environ["GUALA_PAIRED_ROOT"] = str(root)
store = store_at(root)
store.publish(identity=descriptor["identity"], organism_tick=descriptor["organism_tick"],
              body=body, world=world, expected_current_body_sha256=None)
initial = store.restore()
actor = _restore_production_actor()
verify_actor(actor, store.restore())
initial_reserves = actor._runtime.reserve_micrograms
initial_feeding = actor._runtime.feeding
print(json.dumps({"authenticated_predecessor": descriptor, "exact_startup": True,
    "initial_reserves": initial_reserves, "initial_feeding": initial_feeding}), flush=True)
start = time.monotonic()
actor.start()
bite = False
first_presentation = None
try:
    for index in range(8):
        occurrence = (PhysicalOccurrence("sensory", LeanSensoryOccurrence(
            source="caretaker-food", retina_rgb_u8=None, pressure_s16le=None,
            present_food="apple-delivery")) if index == 0 else PhysicalOccurrence("unattended", None))
        result = actor.submit(occurrence, timeout=45)
        ob = result.observation
        if index == 0:
            first_presentation = ob.get("caregiver_presentation")
            assert first_presentation is not None
            assert first_presentation["schema"] == "guala.caregiver_presentation.v1"
            assert "steps" in first_presentation
        bite = bite or ob.get("her_act") == "bite"
        print(json.dumps({"interval": index, "act": ob.get("her_act"),
            "presentation": ob.get("caregiver_presentation")}, default=str), flush=True)
finally:
    actor.close()
after = persisted(actor, store)
if initial_feeding and (first_presentation or {}).get("presented"):
    assert bite, "no physical bite occurred while hungry and food presented"
    assert actor._runtime.reserve_micrograms > initial_reserves
else:
    assert not bite, "sated organism erroneously bit food"
assert after.pointer.current.identity == initial.pointer.current.identity
assert after.pointer.current.organism_tick >= initial.pointer.current.organism_tick + 8
assert after.pointer.current.world_sha256 != initial.pointer.current.world_sha256
print(json.dumps({"published_successor": asdict(after.pointer.current),
    "reserves": actor._runtime.reserve_micrograms, "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "seconds": time.monotonic()-start}), flush=True)
subprocess.run([sys.executable, __file__, "--fresh"], check=True, timeout=60)
print("RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS", flush=True)
