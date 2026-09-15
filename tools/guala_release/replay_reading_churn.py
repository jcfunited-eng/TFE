"""Replay a capture with a reading (Alice ch.1 blocks every beat) for N beats: key churn, novelty, beat cost."""
import collections, gzip, os, sys, time, zipfile, base64
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism, STREAMS, choice_key
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence
import dsf_ai_service.lean_production_app as production
capture = sys.argv[1]; beats = int(sys.argv[2]) if len(sys.argv) > 2 else 300
pcm = open("/workspaces/Tao_Financial_Engine/guala_caretaker/media/alice_in_wonderland_librivox/wonderland_ch_01_64kb.pcm", "rb").read()
blocks = [pcm[i:i + 8000] for i in range(0, 8000 * beats, 8000)]
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
def hear(b): return production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="microphone", pcm_s16le_base64=base64.b64encode(b).decode("ascii"))))
keys = []; novel = 0; total = 0.0; worst = 0.0; acts = collections.Counter(); kinds = collections.Counter()
for i in range(beats):
    t = time.perf_counter(); o = loop.settle(org, w, hear(blocks[i])).observation; dt = time.perf_counter() - t; total += dt; worst = max(worst, dt)
    tokens = (o.get("kernel_signature") or "").split(" "); keys.append(choice_key("".join(t_[0] for t_ in tokens))); novel += bool(o.get("kernel_novel")); acts[o["her_act"]] += 1
    r = o.get("act_reason") or ""; kinds["from her sleep" if "from her sleep" in r else "best so far" if "best so far" in r else "least tried" if "least tried" in r else "first try" if "first try" in r else "other"] += 1
print(f"streams {len(STREAMS)} | {beats} beats of reading: distinct keys {len(set(keys))}, novel {novel}, key repeats next beat {sum(1 for a, b in zip(keys, keys[1:]) if a == b)} | mean %.3f worst %.2f" % (total / beats, worst), "| choice kinds", dict(kinds), "| body", len(org.encoded()))
enc = org.encoded(); assert FunctionalOrganism.restore(enc).encoded() == enc; print("restore byte-exact")
