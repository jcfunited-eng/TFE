"""Replay a capture N beats with the caregiver's touch every K beats (kinds in turn); report her side."""
import collections, gzip, sys, time, zipfile
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence
import dsf_ai_service.lean_production_app as production
capture = sys.argv[1]; beats = int(sys.argv[2]) if len(sys.argv) > 2 else 400; every = int(sys.argv[3]) if len(sys.argv) > 3 else 30
kinds = ["touch-hold-hand", "touch-hug", "touch-pat", "touch-kiss", "touch-shoulder"]
occ = {k: production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="caretaker-food", present_food=k))) for k in kinds}
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
acts = collections.Counter(); rooms = []; moved = 0; said = 0; total = 0.0; worst = 0.0; given = collections.Counter(); felt = 0; own = 0; needs = []
for i in range(beats):
    o_kind = kinds[(i // every) % len(kinds)] if i % every == 0 and i > 0 else None
    t = time.perf_counter(); o = loop.settle(org, w, occ[o_kind] if o_kind else un).observation; dt = time.perf_counter() - t; total += dt; worst = max(worst, dt)
    acts[o["her_act"]] += 1; moved += any(o["actual_root_motion"] or []); said += o.get("said") is not None
    sk = o.get("her_skin") or {}
    if sk.get("touched"): given[sk["touched"]] += 1
    if (sk.get("contact") or 0) > 0: felt += 1
    if o["her_act"] == "reach_hand" and o.get("requested_world_action") == "reach_hand": own += 1
    needs.append((sk.get("need") or [0])[0])
    room = o["embodiment"]["room_id"]
    if not rooms or rooms[-1] != room: rooms.append(room)
print(f"{beats} beats, a touch every {every}: acts", dict(acts), "| motion", moved, "| syllables", said, "| rooms", rooms[:8], "| mean %.3f worst %.2f" % (total / beats, worst), "| body", len(org.encoded()))
print("touches given", dict(given), "| beats she felt skin", felt, "| her own reaches applied", own, "| need first/max/last", needs[0], max(needs), needs[-1])
rec = org._state["acts"]; import statistics
means = collections.defaultdict(list)
for e in rec.values():
    for a, (tries, tot) in e["acts"].items(): means[a].append(tot / max(1, tries))
print("day record mean value by act:", {a: round(statistics.mean(v), 3) for a, v in sorted(means.items())})
enc = org.encoded(); assert FunctionalOrganism.restore(enc).encoded() == enc; print("restore byte-exact")
