"""probe_diversity_substrate.py — test the diversity hypothesis ON THE SUBSTRATE.

Hypothesis (from GL-CMD-144: neurons are clones -> population adds no capacity):
giving each neuron its OWN cut of the substrate's features should lift recall at
n=200 where event_count collapses to ~16% confident-collision.

This is NOT a toy. Same real LoomBrain, same krimelacks, same generate_concepts
corpus that breaks event_count. Only the per-neuron ENCODE changes:
  - baseline : real brain.recall (event_count -> grandurun -> cosine)  [control]
  - diverse6 : per-neuron gaussian projection of the 6 event-count deltas
               -> z-score (training stats) -> ternary cut -> per-neuron code,
               population vote.   (the "cheat": random per-neuron DNA)
  - diverse18: same, but feature = (count, dwinding, dphase) per modality = 18-dim,
               to separate "clone problem" from "feature-poverty problem".

Run: PYTHONHASHSEED=0 python -m dsf_ai_service.loom_model.tests.probe_diversity_substrate
"""
import sys, os, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import MODALITIES
from dsf_ai_service.loom_model.neuron import signal_attenuation
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts
from dsf_ai_service.loom_model.tests.probe_146_rank_order import t5 as real_t5  # event_count control

REPS = 3
K = 64                # per-neuron code dimension
TERCILE = 0.4307      # z threshold for balanced ternary under N(0,1)


def _phase(krim):
    return float(getattr(krim, 'phase', 0.0) or 0.0)


def extract_feats(neuron, signals):
    """Feed query/concept through this neuron's krimelack bank (faithful to the
    substrate feed: language=transduce no_reset, sensory=feed_signal, ring atten),
    capturing per-modality (count, dwinding, dphase). Snapshot/restore phase+winding
    so the call doesn't pollute state (same contract as brain.recall)."""
    rpos = getattr(neuron, 'ring_pos', 0)
    rN = getattr(neuron, 'ring_N', 1)
    snap = {}
    counts = []; dwind = []; dphase = []
    for i, m in enumerate(MODALITIES):
        krim = neuron.krimelack_bank.get(m)
        sig = signals.get(m)
        if krim is None or sig is None:
            counts.append(0.0); dwind.append(0.0); dphase.append(0.0)
            continue
        snap[m] = (_phase(krim), int(getattr(krim, 'winding', 0)))
        att = signal_attenuation(rpos, rN, i)
        e0 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        w0 = int(getattr(krim, 'winding', 0)); p0 = _phase(krim)
        if m == "language":
            krim.transduce(sig, no_reset=True, omega_override=2.0 * att)
        elif hasattr(krim, 'feed_signal'):
            s = list(sig) if not isinstance(sig, list) else sig
            krim.feed_signal([x * att for x in s])
        e1 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        w1 = int(getattr(krim, 'winding', 0)); p1 = _phase(krim)
        counts.append(float(e1 - e0)); dwind.append(float(w1 - w0)); dphase.append(float(p1 - p0))
    return np.array(counts), np.array(dwind), np.array(dphase), snap


def restore(neuron, snap):
    for m, (p, w) in snap.items():
        krim = neuron.krimelack_bank.get(m)
        if krim is None:
            continue
        if hasattr(krim, 'phase'):
            krim.phase = p
        krim.winding = w


def ternary_z(y, mean, std):
    z = (y - mean) / np.where(std < 1e-9, 1.0, std)
    out = np.zeros_like(z)
    out[z > TERCILE] = 1.0
    out[z < -TERCILE] = -1.0
    return out


def run_diverse(n, brain_seed, feat_dim):
    """feat_dim in {6,18}. Returns T5 (%)."""
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=brain_seed, seed_size=8)
    pipe = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    neurons = [nn for h in brain.hemispheres for nn in h.cluster.neurons]

    # per-neuron projection (DNA), seeded by neuron index
    P = [np.random.default_rng(7000 + i).standard_normal((K, feat_dim)) for i in range(len(neurons))]

    def featvec(neuron, signals):
        c, dw, dp, snap = extract_feats(neuron, signals)
        if feat_dim == 6:
            v = c
        else:
            v = np.concatenate([c, dw, dp])
        return v, snap

    # ---- TRAIN: feed REPS, capture each neuron's projected feature per concept
    # (last rep = trained state). No restore during training (state accumulates).
    proj_train = [dict() for _ in neurons]   # neuron -> {concept: projected raw y}
    tick = 0
    for rep in range(REPS):
        last = (rep == REPS - 1)
        for c in corpus:
            signals = pipe._build_multi_modal_signals(c, tick)
            for ni, neuron in enumerate(neurons):
                v, _snap = featvec(neuron, signals)   # training: keep state (no restore)
                if last:
                    proj_train[ni][c] = P[ni] @ v
            tick += 1

    # per-neuron z-stats + ternary codes for stored concepts
    codes = [dict() for _ in neurons]
    stats = []
    for ni in range(len(neurons)):
        Y = np.stack([proj_train[ni][c] for c in corpus])      # (n, K)
        mean = Y.mean(axis=0); std = Y.std(axis=0)
        stats.append((mean, std))
        for c in corpus:
            codes[ni][c] = ternary_z(proj_train[ni][c], mean, std)

    # ---- RECALL: clean query per concept; per-neuron code -> cosine vs stored -> vote
    from collections import Counter
    correct = 0
    for c in corpus:
        signals = pipe._build_multi_modal_signals(c)
        votes = Counter()
        for ni, neuron in enumerate(neurons):
            v, snap = featvec(neuron, signals)
            restore(neuron, snap)                              # don't pollute (recall contract)
            mean, std = stats[ni]
            qcode = ternary_z(P[ni] @ v, mean, std)
            qn = np.linalg.norm(qcode)
            if qn < 1e-9:
                continue
            best = None; bestcos = -2.0
            for cc in corpus:
                sc = codes[ni][cc]
                sn = np.linalg.norm(sc)
                if sn < 1e-9:
                    continue
                cos = float(qcode @ sc) / (qn * sn)
                if cos > bestcos:
                    bestcos = cos; best = cc
            if best is not None:
                votes[best] += 1
        top = votes.most_common(1)
        if top and top[0][0] == c:
            correct += 1
    return correct / n * 100.0


def main():
    seed = 42
    points = [100, 200, 400]
    print(f"{'n':>5} {'baseline(event_count)':>22} {'diverse6':>10} {'diverse18':>10}", flush=True)
    for n in points:
        t0 = time.time()
        base = real_t5(n, seed, 'event_count')
        d6 = run_diverse(n, seed, 6)
        d18 = run_diverse(n, seed, 18)
        print(f"{n:>5} {base:>21.1f}% {d6:>9.1f}% {d18:>9.1f}%   ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
