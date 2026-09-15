"""Replay a capture N beats unattended and report her speech record."""
import collections, gzip, sys, time, zipfile
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence
capture = sys.argv[1]; beats = int(sys.argv[2]) if len(sys.argv) > 2 else 400
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
acts = collections.Counter(); rooms = []; said = 0; total = 0.0; worst = 0.0; reasons = collections.Counter(); syls = collections.Counter()
for i in range(beats):
    t = time.perf_counter(); o = loop.settle(org, w, un).observation; dt = time.perf_counter() - t; total += dt; worst = max(worst, dt)
    acts[o["her_act"]] += 1
    if o["her_act"] == "say":
        said += 1; r = (o["act_reason"] or ""); reasons[r.split("; ")[-1].split(" under")[0][:40]] += 1
    room = o["embodiment"]["room_id"]
    if not rooms or rooms[-1] != room: rooms.append(room)
st = org._state
speech = st.get("speech", {})
answered = sum(int(d[1]) for e in speech.values() for d in e["syllables"].values())
tries = sum(int(d[0]) for e in speech.values() for d in e["syllables"].values())
print(f"{beats} beats: acts", dict(acts), "| rooms", rooms[:8], "| mean %.3f worst %.2f" % (total / beats, worst), "| body", len(org.encoded()))
print("say reasons:", dict(reasons.most_common(8)))
print("speech contexts", len(speech), "| syllable tries in record", tries, "| answered", answered, "| syllable_totals", dict(st.get("syllable_totals", {})), "| voice entries", len(st.get("voice", [])), "| prior", st.get("prior_syllable"))
enc = org.encoded(); assert FunctionalOrganism.restore(enc).encoded() == enc; print("restore byte-exact")
