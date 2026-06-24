"""probe_forced_capacity.py — push n=200 as high as it goes with forced per-neuron
ternary chi (the diversity that made the population orthogonal: rank 1.86 -> 21.49).

Two levers together:
  1. per-neuron ternary chi address (independent projection + balanced-ternary quantize)
  2. scale neuron count — now that units are orthogonal, more should ADD capacity
     (the -144 "brain size doesn't help" was the clone artifact).

Features: per-(neuron,concept) krimelack outputs (event count + winding) over 6
modalities, fed through each neuron's own projection. Extract once, reuse.
"""
import sys, os, time
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import MODALITIES
from dsf_ai_service.loom_model.neuron import signal_attenuation
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

K = 64           # ternary chi dimension per neuron
TERCILE = 0.4307
REPS = 3


def feats(neuron, signals):
    """Per-neuron feature vector: event-count per modality = 6 dims (the proven
    diverse6; winding accumulates unbounded and poisons the projection)."""
    rpos = getattr(neuron, "ring_pos", 0); rN = getattr(neuron, "ring_N", 1)
    counts = []
    for i, m in enumerate(MODALITIES):
        krim = neuron.krimelack_bank.get(m); sig = signals.get(m)
        if krim is None or sig is None:
            counts.append(0.0); continue
        att = signal_attenuation(rpos, rN, i)
        e0 = krim.n_events if hasattr(krim, "n_events") else len(krim.events)
        if m == "language":
            krim.transduce(sig, no_reset=True, omega_override=2.0 * att)
        elif hasattr(krim, "feed_signal"):
            s = list(sig) if not isinstance(sig, list) else sig
            krim.feed_signal([x * att for x in s])
        e1 = krim.n_events if hasattr(krim, "n_events") else len(krim.events)
        counts.append(float(e1 - e0))
    return np.array(counts)


def run(n, seed_size, brain_seed=42):
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=brain_seed, seed_size=seed_size)
    pipe = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    neurons = [nn for h in brain.hemispheres for nn in h.cluster.neurons]
    P = [np.random.default_rng(7000 + i).standard_normal((K, 6)) for i in range(len(neurons))]

    # TRAIN: accumulate krimelack state over reps, capture features on last rep
    train = [dict() for _ in neurons]
    tick = 0
    for rep in range(REPS):
        last = rep == REPS - 1
        for c in corpus:
            sig = pipe._build_multi_modal_signals(c, tick)
            for ni, nn in enumerate(neurons):
                f = feats(nn, sig)
                if last:
                    train[ni][c] = P[ni] @ f
            tick += 1

    stats, codes = [], [dict() for _ in neurons]
    for ni in range(len(neurons)):
        Y = np.stack([train[ni][c] for c in corpus])
        mean, std = Y.mean(0), Y.std(0)
        stats.append((mean, std))
        for c in corpus:
            z = (train[ni][c] - mean) / np.where(std < 1e-9, 1.0, std)
            codes[ni][c] = np.where(z > TERCILE, 1.0, np.where(z < -TERCILE, -1.0, 0.0))

    # RECALL: per-neuron ternary code -> nearest stored (cosine) -> population vote
    correct = 0
    for c in corpus:
        sig = pipe._build_multi_modal_signals(c)
        votes = Counter()
        for ni, nn in enumerate(neurons):
            f = feats(nn, sig)
            mean, std = stats[ni]
            z = (P[ni] @ f - mean) / np.where(std < 1e-9, 1.0, std)
            q = np.where(z > TERCILE, 1.0, np.where(z < -TERCILE, -1.0, 0.0))
            qn = np.linalg.norm(q)
            if qn < 1e-9:
                continue
            best, bc = None, -2.0
            for cc in corpus:
                sc = codes[ni][cc]; sn = np.linalg.norm(sc)
                if sn < 1e-9:
                    continue
                cos = float(q @ sc) / (qn * sn)
                if cos > bc:
                    bc, best = cos, cc
            if best is not None:
                votes[best] += 1
        if votes and votes.most_common(1)[0][0] == c:
            correct += 1
    return correct / n * 100.0


def main():
    print(f"forced per-neuron ternary chi (K={K}, features=6 counts)")
    print(f"{'neurons':>8} {'n=200 T5':>10}")
    for ss in [8, 16, 32]:
        t0 = time.time()
        acc = run(200, ss)
        print(f"{ss*8:>8} {acc:>9.1f}%   ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
