"""probe_meaning.py — grounding-for-meaning on the resonant-spectral substrate.

Capacity was solved on synthetic signals (distinct by construction = memorization).
Meaning = the representations reflect what concepts ARE: feed the resonant banks
GROUNDED waveforms (real per-word sensory profiles), and perceptually-similar concepts
(apple~pear, marble~quartz) should land near each other in chi-space BECAUSE their
sensory waveforms are similar — while staying distinct enough to recall. Synthetic
hash signals cannot do this (random per word).

Tests, grounded vs hash:
  A. semantic structure: does representation similarity correlate with grounding
     similarity? (Spearman of the two similarity matrices)
  B. semantic nearest-neighbour: is each concept's nearest other concept perceptually related?
  C. capacity: clean recall still high
  D. robustness: recall under query noise (meaning should be robust)
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader, MODALITY_CHANNELS
from dsf_ai_service.curriculum.sensory_catalog import SensoryCatalog
from dsf_ai_service.curriculum.catalog_atlas_reader import CatalogAtlasReader
from dsf_ai_service.loom_model.tests.probe_solution import concept_features
from dsf_ai_service.loom_model.tests.probe_grounded_capacity import GROUNDED, build_catalog


def grounding_vector(word):
    """The concept's true sensory profile (authored channel intensities) — the
    semantic reference. Two concepts are 'similar' if their profiles are similar."""
    prof = GROUNDED.get(word, {})
    v = []
    for mod, chans in MODALITY_CHANNELS.items():
        for ch in chans:
            v.append(float(prof.get(mod, {}).get(ch, 0.0)))
    return np.array(v)


def simmat(vecs):
    M = np.stack(vecs)
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return Mn @ Mn.T


def spearman(a, b):
    ar = np.argsort(np.argsort(a)); br = np.argsort(np.argsort(b))
    ar = ar - ar.mean(); br = br - br.mean()
    return float((ar @ br) / (np.linalg.norm(ar) * np.linalg.norm(br) + 1e-12))


def run(reader_name):
    words = [w for w in GROUNDED][:60]
    brain = LoomBrain(brain_seed=42, seed_size=8)
    if reader_name == "grounded":
        reader = CatalogAtlasReader(build_catalog(words))
    else:
        reader = NullAtlasReader()
    pipe = ExperiencePipeline(brain, SensoryTransducer(reader))
    feats = {w: concept_features(pipe, w) for w in words}
    ground = {w: grounding_vector(w) for w in words}

    # A. semantic structure: corr(representation-sim, grounding-sim) off-diagonal
    R = simmat([feats[w] for w in words]); G = simmat([ground[w] for w in words])
    off = ~np.eye(len(words), dtype=bool)
    structure = spearman(R[off], G[off])

    # B. semantic nearest neighbour: nearest OTHER concept's grounding-sim to self
    nn_ground_sim = []
    for i, w in enumerate(words):
        r = R[i].copy(); r[i] = -9
        j = int(r.argmax())
        nn_ground_sim.append(G[i, j])
    nn = float(np.mean(nn_ground_sim))

    # C/D. capacity + noise robustness (population vote over per-neuron ternary chi)
    from dsf_ai_service.loom_model import resonant_chi as rc
    neurons = [nn_ for h in brain.hemispheres for nn_ in h.cluster.neurons]
    D = len(next(iter(feats.values())))
    P = [rc.neuron_projection(n.neuron_id, D) for n in neurons]
    codes = [{w: rc.ternary_chi(feats[w], P[i]) for w in words} for i in range(len(neurons))]

    def recall(qfeat):
        from collections import Counter
        votes = Counter()
        for i in range(len(neurons)):
            q = rc.ternary_chi(qfeat, P[i]); qn = np.linalg.norm(q)
            if qn < 1e-9: continue
            best, bc = None, -2
            for w in words:
                c = codes[i][w]; cn = np.linalg.norm(c)
                if cn < 1e-9: continue
                cos = float(q @ c) / (qn * cn)
                if cos > bc: bc, best = cos, w
            if best: votes[best] += 1
        return votes.most_common(1)[0][0] if votes else None

    clean = np.mean([recall(feats[w]) == w for w in words]) * 100
    rng = np.random.default_rng(0)
    noisy = np.mean([recall(feats[w] + rng.standard_normal(D) * 0.3 * np.std(feats[w])) == w
                     for w in words]) * 100
    return structure, nn, clean, noisy


def main():
    print(f"{'signals':>9} {'semantic-structure(rho)':>24} {'NN-ground-sim':>14} {'clean':>7} {'noisy':>7}")
    for name in ["hash", "grounded"]:
        s, nn, c, no = run(name)
        print(f"{name:>9} {s:>24.3f} {nn:>14.3f} {c:>6.1f}% {no:>6.1f}%", flush=True)


if __name__ == "__main__":
    main()
