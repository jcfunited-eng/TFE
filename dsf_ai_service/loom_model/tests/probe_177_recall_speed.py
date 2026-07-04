"""probe_177_recall_speed.py — GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177.

Reproduces the LIVE organism.recall() path exactly (same Embryo construction,
same _organism_signal multi-modal tap, same observable="event_count") so any
optimization can be profiled/timed/verified against production reality, not
a synthetic stand-in.

Part A: cProfile organism.recall() at realistic scale to confirm hot spots.
Part B: confirm population is FIXED at 64 for the organism path (remember()/
        recall() never call brain.step(), so charge-and-fold never fires --
        correction to the handoff's "population grows, no ceiling" framing).
"""
import cProfile
import pstats
import io
import sys
import time

sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.v4.gualaloom_v5_engine import _organism_signal
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader

WORDS = ("the cat sat on the mat and looked at the little dog who was "
         "running fast across the green grass near the old wooden fence "
         "while a warm bright sun shone down on them both today").split()


def build_organism(seed_size=8):
    emb = Embryo(brain_seed=42, seed_size=seed_size, observable="event_count")
    transducer = SensoryTransducer(NullAtlasReader())
    return emb, transducer


def teach(emb, transducer, words):
    for w in words:
        sig = _organism_signal(w, transducer)
        emb.remember(w, sig)


def part_a_profile():
    emb, transducer = build_organism()
    teach(emb, transducer, WORDS[:30])  # realistic partial exposure before profiling

    n_pop = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    print(f"population (neurons): {n_pop}")

    query_words = WORDS[:10]
    pr = cProfile.Profile()
    pr.enable()
    for w in query_words:
        emb.recall(_organism_signal(w, transducer))
    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())


def part_b_population_check():
    emb, transducer = build_organism()
    n0 = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    for w in WORDS:
        sig = _organism_signal(w, transducer)
        emb.remember(w, sig)
        emb.recall(sig)
    n1 = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    print(f"population before teaching {len(WORDS)} words: {n0}")
    print(f"population after teaching {len(WORDS)} words + recalling each: {n1}")
    print("(remember()/recall() never call brain.step(), so process_folds() "
          "never runs on this path -- population is static)")


def part_c_timing_curve():
    """Recall() wall-clock at increasing words-taught, fixed population=64 --
    the axis that's ACTUALLY live-growing (each neuron's own binding_atlas)."""
    emb, transducer = build_organism()
    checkpoints = [0, 10, 30, 60, 100, len(WORDS)]
    taught = 0
    for cp in checkpoints:
        while taught < cp:
            w = WORDS[taught % len(WORDS)]
            emb.remember(w, _organism_signal(w, transducer))
            taught += 1
        # time 10 recall calls, average
        t0 = time.perf_counter()
        for w in WORDS[:10]:
            emb.recall(_organism_signal(w, transducer))
        dt = (time.perf_counter() - t0) / 10.0
        print(f"words_taught={taught:4d}  avg_recall_ms={dt*1000:.2f}")


if __name__ == "__main__":
    print("=== Part A: cProfile ===")
    part_a_profile()
    print("\n=== Part B: population check ===")
    part_b_population_check()
    print("\n=== Part C: timing curve vs words taught ===")
    part_c_timing_curve()
