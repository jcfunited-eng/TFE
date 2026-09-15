"""How stable is the structure she chooses under? Replay a capture N beats and count
distinct choice keys, per-stream regime flips, and familiarity hits."""
import collections, gzip, sys, zipfile
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import FunctionalOrganism, STREAMS, CHOICE_STREAMS, choice_key, FAMILIARITY_CAPACITY
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.lean_actor import PhysicalOccurrence
capture = sys.argv[1]; beats = int(sys.argv[2]) if len(sys.argv) > 2 else 400
z = zipfile.ZipFile(f"{capture}/current.zip")
org = FunctionalOrganism.restore(gzip.decompress(z.read("body.glorun.gz")))
w = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1", encoded_world=z.read("world.json"), migrate_physical_return=True)
loop = FunctionalPhysicalLoop(); un = PhysicalOccurrence("unattended", None)
keys = []; flips = collections.Counter(); prev = None; novel = 0; letters_seen = collections.defaultdict(set)
for i in range(beats):
    o = loop.settle(org, w, un).observation
    sig = o.get("kernel_signature") or ""
    tokens = sig.split(" ")
    regimes = "".join(t[0] for t in tokens)
    keys.append(choice_key(regimes))
    novel += bool(o.get("kernel_novel"))
    for name, letter in zip(STREAMS, regimes):
        letters_seen[name].add(letter)
        if prev is not None and prev[STREAMS.index(name)] != letter:
            flips[name] += 1
    prev = regimes
print("familiarity capacity", FAMILIARITY_CAPACITY, "| familiarity size", len(org._state["familiarity"]), "| record size", len(org._state["acts"]))
print(f"{beats} beats: distinct keys {len(set(keys))}, novel {novel}, key repeats next beat {sum(1 for a, b in zip(keys, keys[1:]) if a == b)}")
print("regime flips per stream:", {k: flips[k] for k in STREAMS})
print("letters per stream:", {k: "".join(sorted(v)) for k, v in letters_seen.items()})
