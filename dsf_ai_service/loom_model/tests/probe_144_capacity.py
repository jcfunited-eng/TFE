"""probe_144_capacity.py — GL-CMD-144: measure the n=200 capacity cliff.

PROBE ONLY. No production edits. Calls production brain.recall directly (NOT the
sweep_136/137 monkeypatch, which overrides _unwrapped_deltas — V1.a). Clean,
full-cue, single-query T5 (matches the GL-CMD-140 parity methodology).

Curves:
  A. capacity:   seed_size=8, n in {25,50,75,100,125,150,175,200,250,300,400}, 3 seeds
  B. brain size: n=100, seed_size in {4,8,16,32,64}, 3 seeds, RSS-guarded (halt >1GB)
  C. per-neuron vote distribution at n=200 (>=5 concepts)
  D. repeatability: 3 brain_seeds per point -> mean/std

Run: python -m dsf_ai_service.loom_model.tests.probe_144_capacity
"""
import sys, os, time, resource
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

REPS = 3
SEEDS = [42, 43, 44]
RSS_CEIL_MB = 1024.0


def maxrss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0  # KB->MB (linux)


def teach(n_concepts, seed_size, brain_seed):
    corpus = generate_concepts(n_concepts, seed=42)  # fixed corpus; brain_seed varies wiring
    brain = LoomBrain(brain_seed=brain_seed, seed_size=seed_size)
    pipeline = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    tick = 0
    for _rep in range(REPS):
        for w in corpus:
            pipeline.deliver_word(w, tick, ticks_per_word=1)
            tick += 1
    return brain, pipeline, corpus


def t5_clean(n_concepts, seed_size, brain_seed):
    """Production-path clean full-cue T5 via brain.recall."""
    brain, pipeline, corpus = teach(n_concepts, seed_size, brain_seed)
    correct = 0
    for w in corpus:
        signals = pipeline._build_multi_modal_signals(w)
        top = brain.recall(signals).most_common(1)
        if top and top[0][0] == w:
            correct += 1
    return correct / n_concepts * 100.0


def curve_A():
    print("\n===== CURVE A: capacity (seed_size=8) =====", flush=True)
    print(f"{'n':>5} {'mean_T5':>8} {'std':>6} {'per-seed':>22} {'rss_MB':>7}", flush=True)
    rows = []
    for n in [25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400]:
        vals = []
        for s in SEEDS:
            vals.append(t5_clean(n, 8, s))
            if maxrss_mb() > RSS_CEIL_MB:
                print(f"  STOP V4.a: RSS {maxrss_mb():.0f}MB > {RSS_CEIL_MB}MB at n={n}", flush=True)
                return rows
        m, sd = float(np.mean(vals)), float(np.std(vals))
        rows.append((n, m, sd, vals))
        print(f"{n:>5} {m:>7.1f}% {sd:>6.1f} {str([round(v,1) for v in vals]):>22} {maxrss_mb():>7.0f}", flush=True)
    return rows


def curve_B():
    print("\n===== CURVE B: brain size (n=100) =====", flush=True)
    print(f"{'seed_size':>9} {'neurons':>7} {'mean_T5':>8} {'std':>6} {'per-seed':>22} {'rss_MB':>7}", flush=True)
    rows = []
    for ss in [4, 8, 16, 32, 64]:
        if maxrss_mb() > RSS_CEIL_MB:
            print(f"  STOP V4.a: RSS {maxrss_mb():.0f}MB > {RSS_CEIL_MB}MB before seed_size={ss}", flush=True)
            break
        vals = []
        halted = False
        for s in SEEDS:
            vals.append(t5_clean(100, ss, s))
            if maxrss_mb() > RSS_CEIL_MB:
                print(f"  STOP V4.a: RSS {maxrss_mb():.0f}MB > {RSS_CEIL_MB}MB at seed_size={ss}", flush=True)
                halted = True
                break
        if vals:
            m, sd = float(np.mean(vals)), float(np.std(vals))
            rows.append((ss, ss * 8, m, sd, vals))
            print(f"{ss:>9} {ss*8:>7} {m:>7.1f}% {sd:>6.1f} {str([round(v,1) for v in vals]):>22} {maxrss_mb():>7.0f}", flush=True)
        if halted:
            break
    return rows


def curve_C():
    print("\n===== CURVE C: per-neuron vote distribution at n=200 (seed=42) =====", flush=True)
    brain, pipeline, corpus = teach(200, 8, 42)
    neurons = [nn for h in brain.hemispheres for nn in h.cluster.neurons]
    print(f"{len(neurons)} neurons; reporting first 5 concepts", flush=True)
    print(f"{'concept':>12} {'winner':>14} {'win_votes':>10} {'correct_votes':>13} {'unique':>7} {'top3'}", flush=True)
    rows = []
    for q in corpus[:5]:
        signals = pipeline._build_multi_modal_signals(q)
        preds = []
        for nrn in neurons:
            snap = {m: (getattr(nrn.krimelack_bank[m], 'phase', 0.0),
                        getattr(nrn.krimelack_bank[m], 'winding', 0))
                    for m in MODALITIES if m in nrn.krimelack_bank}
            qd = nrn._unwrapped_deltas(signals)
            best, _ = nrn.binding_atlas.recall_best(grandurun_state(qd))
            for m, (p, w) in snap.items():
                k = nrn.krimelack_bank[m]
                if hasattr(k, 'phase'): k.phase = p
                k.winding = w
            if best is not None:
                preds.append(best)
        c = Counter(preds)
        win, wv = c.most_common(1)[0]
        rows.append((q, win, wv, c.get(q, 0), len(c), c.most_common(3)))
        print(f"{q:>12} {win:>14} {wv:>10} {c.get(q,0):>13} {len(c):>7} {c.most_common(3)}", flush=True)
    return rows


def main():
    t0 = time.time()
    a = curve_A()
    b = curve_B()
    c = curve_C()
    print(f"\nTotal wall time: {(time.time()-t0)/60:.1f} min  peakRSS={maxrss_mb():.0f}MB", flush=True)


if __name__ == '__main__':
    main()
