"""probe_solution.py — the capacity solve, substrate-true.

Wall identified: the krimelack collapses each modality's waveform into ONE
event-count, destroying the structure that separates concepts. Fix: a bank of
frequency-tuned resonant receptors per modality reports the waveform's SPECTRUM
(per-receptor response) — rich, concept-distinct features. The cochlea / the
smell tumbler. Then per-neuron ternary chi (forced diversity) stores it distributed.

Verifies: substrate-true resonant-bank spectral features -> recall at n=200/400.
"""
import sys, os, time
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import MODALITIES
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

# Frequency-tuned resonant receptor bank per modality (the substrate-true spectrum).
# Each receptor's response = the signal's energy at its natural frequency = a driven
# resonator's steady-state amplitude. The response VECTOR across the bank is the
# spectrum (rich), not a scalar (which only told food from noise).
N_RECEPTORS = 16
TERCILE = 0.4307


def resonant_response(signal, n_receptors=N_RECEPTORS, dt=0.04):
    s = np.asarray(signal, float)
    s = s - s.mean()
    n = len(s)
    if n < 4 or np.allclose(s, 0):
        return np.zeros(n_receptors)
    t = np.arange(n) * dt
    freqs = np.geomspace(0.3, 12.0, n_receptors)   # tuned receptors (Hz)
    resp = np.empty(n_receptors)
    for j, f in enumerate(freqs):
        ip = np.dot(s, np.cos(2 * np.pi * f * t))
        qp = np.dot(s, np.sin(2 * np.pi * f * t))
        resp[j] = np.hypot(ip, qp) / n              # driven-resonator amplitude
    return resp


def concept_features(pipe, concept):
    """Rich per-modality spectral feature vector from the resonant receptor banks."""
    sig = pipe._build_multi_modal_signals(concept)
    parts = []
    for m in MODALITIES:
        x = sig.get(m)
        if x is None or isinstance(x, str):
            continue
        parts.append(resonant_response(x))
    return np.concatenate(parts) if parts else np.zeros(N_RECEPTORS)


def run(n, seed_size, K=128, distributed=True):
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=42, seed_size=seed_size)
    pipe = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    F = {c: concept_features(pipe, c) for c in corpus}
    D = len(next(iter(F.values())))

    if not distributed:
        # direct cosine recall on the bank features (one shared atlas)
        M = np.array([F[c] for c in corpus])
        Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        sim = Mn @ Mn.T
        return np.mean([corpus[sim[i].argmax()] == corpus[i] for i in range(n)]) * 100

    # distributed: per-neuron ternary chi (forced diversity) + population vote
    neurons = [nn for h in brain.hemispheres for nn in h.cluster.neurons]
    P = [np.random.default_rng(7000 + i).standard_normal((K, D)) for i in range(len(neurons))]
    codes = [dict() for _ in neurons]
    stats = []
    for ni in range(len(neurons)):
        Y = np.stack([P[ni] @ F[c] for c in corpus])
        mean, std = Y.mean(0), Y.std(0)
        stats.append((mean, std))
        for c in corpus:
            z = (P[ni] @ F[c] - mean) / np.where(std < 1e-9, 1.0, std)
            codes[ni][c] = np.where(z > TERCILE, 1.0, np.where(z < -TERCILE, -1.0, 0.0))
    correct = 0
    for c in corpus:
        votes = Counter()
        for ni in range(len(neurons)):
            mean, std = stats[ni]
            z = (P[ni] @ F[c] - mean) / np.where(std < 1e-9, 1.0, std)
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
    print(f"resonant receptor bank ({N_RECEPTORS}/modality) spectral features\n")
    print(f"{'n':>5} {'direct cosine':>14} {'distributed ternary-chi (64 neurons)':>40}")
    for n in [100, 200, 400]:
        t0 = time.time()
        d = run(n, 8, distributed=False)
        td = run(n, 8, distributed=True)
        print(f"{n:>5} {d:>13.1f}% {td:>39.1f}%   ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
