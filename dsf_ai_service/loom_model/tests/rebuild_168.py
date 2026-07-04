"""
rebuild_168.py — GL-CMD-C2-REBUILD-EVE-20260704-168-v2 measurement harness.

Model/harness only. Zero live-path changes (G-168-6). Every function here
either reads the on-origin loom_model package as-is (Part A) or monkeypatches
LoomNeuron._unwrapped_deltas for the duration of one measurement (Parts B),
restoring the original method in a `finally` block — the same pattern
tests/sweep_137_scaling_probe.py already uses. No RNG ever seeds neuron
identity (ring position only); RNG is cue-noise-only, per G-168-3.

Run with PYTHONHASHSEED=0 (experience.py._build_multi_modal_signals seeds
per-word signal RNGs from hash(word) — salted across processes otherwise).

    PYTHONHASHSEED=0 python3 -m dsf_ai_service.loom_model.tests.rebuild_168 <part>

parts: a, b1, b2, b4, b5
"""

import sys, os, time, math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES, STATE_DIM
from dsf_ai_service.loom_model.neuron import signal_attenuation, LoomNeuron
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts, STEMS

REPS = 3
BRAIN_SEED = 42


# ---------------------------------------------------------------------------
# Part A — reproduce the champion (blocking)
# ---------------------------------------------------------------------------

def part_a(n_concepts=100, seed_size=8, seed=42):
    """Native production code path. observable='event_count' explicit
    (current default is resonant_spectral, GL capacity solve). No monkeypatch."""
    corpus = generate_concepts(n_concepts, seed=seed)
    brain = LoomBrain(brain_seed=BRAIN_SEED, seed_size=seed_size, observable="event_count")
    pipeline = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))

    t0 = time.time()
    tick = 0
    for rep in range(REPS):
        for w in corpus:
            pipeline.deliver_word(w, tick, ticks_per_word=1)
            tick += 1
    teach_s = time.time() - t0

    t0 = time.time()
    correct = 0
    for w in corpus:
        signals = pipeline._build_multi_modal_signals(w)
        votes = brain.recall(signals)
        top = votes.most_common(1)
        if top and top[0][0] == w:
            correct += 1
    recall_s = time.time() - t0

    accuracy = correct / n_concepts * 100
    print(f"== Part A: event_count, n_concepts={n_concepts}, "
          f"total_neurons={brain.total_neurons()} ==")
    print(f"  T5 accuracy: {correct}/{n_concepts} = {accuracy:.1f}%  "
          f"(teach {teach_s:.1f}s, recall {recall_s:.1f}s)")
    return accuracy


# ---------------------------------------------------------------------------
# Shared: per-neuron instrumented recall (single/best/worst/plurality/unanimity)
# ---------------------------------------------------------------------------

def _degrade_signals(signals, jitter, drop_mod, rng):
    """Cue degradation: gaussian jitter on sensory arrays + one dropped
    modality. RNG here is CUE NOISE ONLY (never neuron identity, G-168-3).
    Mirrors docs/c2_model_v1.py's degradation model (phase jitter + drop)."""
    out = dict(signals)
    drop_name = MODALITIES[drop_mod] if drop_mod is not None else None
    for m in MODALITIES:
        if m == drop_name:
            out[m] = None
            continue
        if m == "language":
            continue  # language is a string token, not perturbable in place
        v = out.get(m)
        if v is None:
            continue
        arr = np.asarray(v, dtype=np.float64)
        if jitter > 0:
            arr = arr + rng.normal(0, jitter, arr.shape)
        out[m] = arr.tolist()
    return out


def _per_neuron_predict(brain, signals):
    """One prediction per neuron (argmax cosine in its own BindingAtlas).
    Restores krimelack phase/winding after, same discipline as LoomBrain.recall."""
    from dsf_ai_service.loom_model.grandurun import MODALITIES as MODS
    preds = []
    for hemi in brain.hemispheres:
        for neuron in hemi.cluster.neurons:
            snap = {}
            for m in MODS:
                krim = neuron.krimelack_bank.get(m)
                if krim is not None:
                    snap[m] = (float(krim.phase) if hasattr(krim, 'phase') else 0.0,
                               int(krim.winding) if hasattr(krim, 'winding') else 0)
            target_vec = neuron.encode_state(signals)
            best_concept, _ = neuron.binding_atlas.recall_best(target_vec)
            preds.append(best_concept)
            for m, (p, w) in snap.items():
                krim = neuron.krimelack_bank.get(m)
                if krim is not None:
                    if hasattr(krim, 'phase'):
                        krim.phase = p
                    krim.winding = w
    return preds


def _population_table(brain, pipeline, corpus, n_trials, jitter, seed=7):
    """Eve's table: single mean/best/worst, plurality vote, unanimity rate.
    RNG (which concept queried + which modality dropped + jitter) is
    CUE-NOISE-ONLY (G-168-3) — neuron identity/ring position untouched."""
    from collections import Counter
    rng = np.random.default_rng(seed)
    n_neurons = brain.total_neurons()
    single_hits = np.zeros(n_neurons)
    pop_hits = 0
    unanimous = 0
    for _ in range(n_trials):
        c_idx = int(rng.integers(len(corpus)))
        concept = corpus[c_idx]
        base_signals = pipeline._build_multi_modal_signals(concept)
        drop_mod = int(rng.integers(6))
        signals = _degrade_signals(base_signals, jitter, drop_mod, rng)
        preds = _per_neuron_predict(brain, signals)
        single_hits += np.array([1 if p == concept else 0 for p in preds])
        counts = Counter(preds)
        if counts:
            winner = counts.most_common(1)[0][0]
            pop_hits += int(winner == concept)
        unanimous += int(len(set(preds)) == 1)
    return {
        "single_mean": float(single_hits.mean() / n_trials),
        "single_best": float(single_hits.max() / n_trials),
        "single_worst": float(single_hits.min() / n_trials),
        "plurality": pop_hits / n_trials,
        "unanimity": unanimous / n_trials,
    }


def _print_table(label, result, baseline_plurality=None):
    delta = ""
    if baseline_plurality is not None:
        delta = f"  (Δ vs baseline plurality: {result['plurality']*100 - baseline_plurality*100:+.1f}pp)"
    print(f"  {label}: single mean={result['single_mean']*100:.1f}% "
          f"best={result['single_best']*100:.1f}% worst={result['single_worst']*100:.1f}% | "
          f"plurality={result['plurality']*100:.1f}% | unanimity={result['unanimity']*100:.1f}%{delta}")


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "a"
    if part == "a":
        part_a()
    else:
        print(f"unknown part {part!r} (this stage only wires 'a')")

