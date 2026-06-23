"""probe_146_rank_order.py — GL-CMD-146: validate rank-order observable vs event_count.

PROBE. Production path: LoomBrain(observable=...) -> brain.recall (opt-in, single
switch). Default (event_count) unchanged. Compares to the GL-CMD-144 event_count curve.

Per V4.b (rank-order regresses below event_count at smoke n=10), we do NOT run the
full 11-point sweep — we characterize at the toy's 5 points {25,50,100,200,400} x3 seeds,
pull the n=200 distribution for both observables, and run the parity check.
"""
import sys, os, time, resource
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES
from dsf_ai_service.loom_model.neuron import LoomNeuron, signal_attenuation
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

REPS = 3
SEEDS = [42, 43, 44]
POINTS = [25, 50, 100, 200, 400]


def maxrss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def teach(n, seed, observable):
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=seed, seed_size=8, observable=observable)
    pipe = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    tick = 0
    for _ in range(REPS):
        for w in corpus:
            pipe.deliver_word(w, tick, ticks_per_word=1)
            tick += 1
    return brain, pipe, corpus


def t5(n, seed, observable):
    brain, pipe, corpus = teach(n, seed, observable)
    correct = 0
    for w in corpus:
        top = brain.recall(pipe._build_multi_modal_signals(w)).most_common(1)
        if top and top[0][0] == w:
            correct += 1
    return correct / n * 100.0


def curve():
    print("\n===== CURVE: rank_order vs event_count (seed_size=8, 3 seeds) =====", flush=True)
    print(f"{'n':>5} {'event_count':>20} {'rank_order':>20}", flush=True)
    for n in POINTS:
        ec = [t5(n, s, 'event_count') for s in SEEDS]
        ro = [t5(n, s, 'rank_order') for s in SEEDS]
        print(f"{n:>5}   {np.mean(ec):>6.1f}% (sd {np.std(ec):>4.1f})   "
              f"{np.mean(ro):>6.1f}% (sd {np.std(ro):>4.1f})   rss={maxrss_mb():.0f}MB", flush=True)


def distribution(observable):
    print(f"\n===== n=200 per-neuron distribution: {observable} (seed 42) =====", flush=True)
    brain, pipe, corpus = teach(200, 42, observable)
    neurons = [nn for h in brain.hemispheres for nn in h.cluster.neurons]
    print(f"{'concept':>12} {'winner':>14} {'win':>5} {'correct':>7} {'unique':>6}", flush=True)
    for q in corpus[:5]:
        signals = pipe._build_multi_modal_signals(q)
        preds = []
        for nrn in neurons:
            snap = {m: (getattr(nrn.krimelack_bank[m], 'phase', 0.0),
                        getattr(nrn.krimelack_bank[m], 'winding', 0))
                    for m in MODALITIES if m in nrn.krimelack_bank}
            best, _ = nrn.binding_atlas.recall_best(grandurun_state(nrn._unwrapped_deltas(signals)))
            for m, (p, w) in snap.items():
                k = nrn.krimelack_bank[m]
                if hasattr(k, 'phase'): k.phase = p
                k.winding = w
            if best is not None:
                preds.append(best)
        c = Counter(preds)
        win, wv = c.most_common(1)[0]
        print(f"{q:>12} {win:>14} {wv:>5} {c.get(q,0):>7} {len(c):>6}", flush=True)


# --- parity: production (constructor opt-in) vs an INDEPENDENT harness reimpl ---
def _harness_rank_order(self, signals):
    """Independent reimplementation of the rank_order observable (monkeypatch),
    to check production transcription fidelity (V3.e). Must match production 0.0pp."""
    rpos = getattr(self, 'ring_pos', 0); rN = getattr(self, 'ring_N', 1)
    fw = {}
    for i, m in enumerate(MODALITIES):
        sig = signals.get(m); krim = self.krimelack_bank.get(m)
        if sig is None or krim is None:
            continue
        att = signal_attenuation(rpos, rN, i)
        e0 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        tp = (float(krim.t) if hasattr(krim, 't')
              else (float(krim._inner.t) if getattr(krim, '_inner', None) is not None
                    and hasattr(krim._inner, 't') else 0.0))
        if m == "language":
            krim.transduce(sig, no_reset=True, omega_override=2.0 * att)
        elif hasattr(krim, 'feed_signal'):
            s = list(sig) if not isinstance(sig, list) else sig
            krim.feed_signal([x * att for x in s])
        e1 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        nc = e1 - e0
        if nc > 0:
            fw[m] = float(list(krim.events)[-nc:][0].get("t", 0.0)) - tp
    d = {m: 0.0 for m in MODALITIES}
    for rank, (m, _t) in enumerate(sorted(fw.items(), key=lambda kv: kv[1])):
        d[m] = float(len(MODALITIES) - rank)
    return d


def parity():
    print("\n===== PARITY: rank_order production vs harness monkeypatch =====", flush=True)
    print(f"{'n':>5} {'production':>11} {'harness':>9} {'delta':>7}", flush=True)
    for n in [25, 50, 100]:
        prod = t5(n, 42, 'rank_order')
        orig = LoomNeuron._unwrapped_deltas
        LoomNeuron._unwrapped_deltas = _harness_rank_order
        try:
            # harness brain built with default observable; monkeypatch overrides
            brain, pipe, corpus = teach(n, 42, 'event_count')
            correct = sum(1 for w in corpus
                          if (brain.recall(pipe._build_multi_modal_signals(w)).most_common(1) or [(None,)])[0][0] == w)
            harn = correct / n * 100.0
        finally:
            LoomNeuron._unwrapped_deltas = orig
        print(f"{n:>5} {prod:>10.1f}% {harn:>8.1f}% {abs(prod-harn):>6.1f}", flush=True)


def main():
    t0 = time.time()
    curve()
    distribution('event_count')
    distribution('rank_order')
    parity()
    print(f"\nTotal {(time.time()-t0)/60:.1f} min  peakRSS={maxrss_mb():.0f}MB", flush=True)


if __name__ == '__main__':
    main()
