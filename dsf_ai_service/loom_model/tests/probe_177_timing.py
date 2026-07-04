"""probe_177_timing.py — GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177.

Before/after wall-clock: recall() (original, mutate+snapshot+restore) vs
recall_fast() (I1 peek-mode + I2 vectorized-across-neurons), at:
  - the live population (N=64, seed_size=8) and headroom scales above it
    (N=256, N=1024) -- named for growth per the dispatch, even though this
    investigation also found the organism's population is NOT currently
    growing live (see report: remember()/recall() never call brain.step(),
    so process_folds() never fires on this path)
  - multiple teaching depths, including past language's saturation point
"""
import sys
import time
import numpy as np

sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.v4.gualaloom_v5_engine import _organism_signal
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader

WORDS = ("the cat sat on the mat and looked at the little dog who was "
         "running fast across the green grass near the old wooden fence "
         "while a warm bright sun shone down on them both today").split()


def time_recall(fn, sig, n_reps=15):
    t0 = time.perf_counter()
    for _ in range(n_reps):
        fn(sig)
    return (time.perf_counter() - t0) / n_reps


def run(seed_size, words_taught, n_reps=15):
    emb = Embryo(brain_seed=42, seed_size=seed_size, observable="event_count")
    transducer = SensoryTransducer(NullAtlasReader())
    for i in range(words_taught):
        w = WORDS[i % len(WORDS)]
        emb.remember(w, _organism_signal(w, transducer))

    n_pop = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    sig = _organism_signal(WORDS[0], transducer)

    t_orig = time_recall(emb.brain.recall, sig, n_reps)
    t_fast = time_recall(emb.brain.recall_fast, sig, n_reps)
    speedup = t_orig / t_fast if t_fast > 0 else float('inf')
    print(f"N={n_pop:5d}  words_taught={words_taught:4d}  "
          f"recall()={t_orig*1000:8.2f}ms  recall_fast()={t_fast*1000:7.3f}ms  "
          f"speedup={speedup:6.1f}x")
    return n_pop, words_taught, t_orig, t_fast


if __name__ == "__main__":
    print("=== timing: recall() vs recall_fast() ===")
    print("-- fixed words_taught=30, scaling population (headroom) --")
    for seed_size in (4, 8, 32, 128):
        run(seed_size, 30)

    print()
    print("-- fixed population (live scale, seed_size=8, N=64), scaling teaching depth --")
    for words_taught in (0, 10, 50, 150, 300):
        run(8, words_taught)
