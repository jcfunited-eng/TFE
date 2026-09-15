"""Replay her captured live state on the checked-out tree for N beats.
Usage: PYTHONPATH=<tree> python3 replay_capture.py <capture-dir> [beats]"""
import collections, gzip, sys, time, zipfile

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence

capture = sys.argv[1]
beats = int(sys.argv[2]) if len(sys.argv) > 2 else 400
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
acts = collections.Counter(); rooms = []; moved = 0; said = 0; total = 0.0; worst = 0.0; doors = collections.Counter()
for i in range(beats):
    t = time.perf_counter(); o = loop.settle(org, w, un).observation; dt = time.perf_counter() - t; total += dt; worst = max(worst, dt)
    acts[o["her_act"]] += 1; moved += any(o["actual_root_motion"] or []); said += o.get("said") is not None
    if o["her_act"] == "toward_door":
        doors[(o["act_reason"] or "").split("; ")[-1][:40]] += 1
    room = o["embodiment"]["room_id"]
    if not rooms or rooms[-1] != room: rooms.append(room)
    if i < 3 or i % 100 == 0: print(i, o["her_act"], "|", (o["act_reason"] or "")[:100])
print(f"{beats} beats: acts", dict(acts), "| motion", moved, "| syllables", said, "| rooms", rooms[:10],
      "| mean %.3f worst %.2f" % (total / beats, worst), "| body", len(org.encoded()))
print("door targets:", dict(doors))
enc = org.encoded(); assert FunctionalOrganism.restore(enc).encoded() == enc; print("restore byte-exact")
