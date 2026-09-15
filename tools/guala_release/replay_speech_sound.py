"""Replay a capture N beats with a room sound (a 370 Hz tone card) every K beats; report her speech record."""
import base64, collections, gzip, math, struct, sys, time, zipfile
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence
import dsf_ai_service.lean_production_app as production
capture = sys.argv[1]; beats = int(sys.argv[2]) if len(sys.argv) > 2 else 400; every = int(sys.argv[3]) if len(sys.argv) > 3 else 5
def tone(frequency_hz, samples=4000):
    return struct.pack(f"<{samples}h", *(int(9000 * math.sin(2 * math.pi * frequency_hz * i / 16000)) for i in range(samples)))
hear = production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="microphone", pcm_s16le_base64=base64.b64encode(tone(370)).decode("ascii"))))
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
acts = collections.Counter(); said = 0; total = 0.0; worst = 0.0; reasons = collections.Counter()
for i in range(beats):
    occ = hear if i % every == 0 else un
    t = time.perf_counter(); o = loop.settle(org, w, occ).observation; dt = time.perf_counter() - t; total += dt; worst = max(worst, dt)
    acts[o["her_act"]] += 1
    if o["her_act"] == "say":
        said += 1; r = (o["act_reason"] or ""); reasons[r.split("; ")[-1][:60]] += 1
st = org._state; speech = st.get("speech", {})
answered = sum(int(d[1]) for e in speech.values() for d in e["syllables"].values())
tries = sum(int(d[0]) for e in speech.values() for d in e["syllables"].values())
print(f"{beats} beats, a tone every {every}: acts", dict(acts), "| mean %.3f worst %.2f" % (total / beats, worst), "| body", len(org.encoded()))
print("say reasons:", dict(reasons.most_common(10)))
print("speech contexts", len(speech), "| tries", tries, "| answered", answered, "| syllable_totals", dict(st.get("syllable_totals", {})))
best = [(k, {s: d for s, d in e["syllables"].items() if d[1] > 0}) for k, e in speech.items() if any(d[1] > 0 for d in e["syllables"].values())]
print("contexts with answered syllables:", len(best), best[:6])
enc = org.encoded(); assert FunctionalOrganism.restore(enc).encoded() == enc; print("restore byte-exact")
