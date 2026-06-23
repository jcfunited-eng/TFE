"""
model_cognition_v2.py — Cognition substrate that actually scales.

What broke in v1:
  1. Grandurun state vector mostly held constants. Only chi_resonance (dim 0)
     and a centroid-of-modalities (dim 5) discriminated concepts. Other 5
     dimensions were modality_index, sensory_count, recency, polarity, affect
     — all near-constant per concept.
  2. The centroid of chi positions on the unit circle collapses many distinct
     chi patterns to the same point. Concepts with permuted chi values mapped
     to the same state vector.
  3. Sum-pooling across all bindings biased toward concepts in dense chi
     regions. "Rope" / "bread" / "fresh" became attractors because their chi
     positions happened to land in heavily-occupied bins.
  4. Band-replicate (±2) made every binding stamp 5 chi keys. With 50 concepts
     × 6 modalities × 5 keys = 1500 bindings into 64 chi slots → ~23 bindings
     per slot. Pure noise.

What I'm changing:
  1. Grandurun state vector becomes a true multi-modal fingerprint: each of
     the first 6 dimensions encodes ONE modality's phase directly as
     exp(1j * phase_m). The 6D pattern fully specifies the multi-modal
     signature; permutations produce distinct vectors.
  2. Drop chi quantization in the binding path entirely. Store continuous
     phase. Quantization only used at coupling layer (not cognition).
  3. Drop band-replicate. Each binding is recorded once at its actual phase
     pattern.
  4. Recall = find best-matching binding per neuron (max inner product),
     then population votes. Max-pooling, not sum-pooling. The concept whose
     best binding scores highest in each neuron wins that neuron's vote.

Test plan:
  - Same concept corpus as v1 (50 concepts from Peter-Rabbit-style vocab)
  - Same perturbation discipline (training noise 0.05 rad, query noise 0.15 rad)
  - Progressive scale: 64 → 256 → 1024 neurons
  - Target: accuracy ≥ 90% at all scales
"""

import sys, math, cmath, time
from collections import defaultdict, Counter
sys.path.insert(0, '/home/claude/TFE')

import numpy as np

MODALITIES = ["visual", "auditory", "tactile", "olfactory", "gustatory", "language"]
N_HEMIS = 8

CONCEPT_CORPUS = [
    # Animals (20)
    "rabbit", "tiger", "bear", "wolf", "snake", "fox", "owl", "fish", "bee", "spider",
    "horse", "cow", "sheep", "goat", "duck", "frog", "ant", "deer", "crow", "moth",
    # Plants / food (20)
    "flower", "rose", "lettuce", "carrot", "berry", "bread", "honey", "apple", "tea", "soup",
    "grape", "pear", "wheat", "milk", "cheese", "butter", "salt", "pepper", "sugar", "oil",
    # Materials / objects (20)
    "stone", "wood", "iron", "glass", "rope", "basket", "umbrella", "key", "coin", "blanket",
    "chair", "table", "book", "candle", "mirror", "needle", "thread", "cloth", "shoe", "hat",
    # Natural elements (20)
    "fire", "water", "ice", "wind", "rain", "mud", "snow", "sand", "smoke", "ash",
    "cloud", "fog", "sun", "moon", "star", "thunder", "lightning", "river", "lake", "hill",
    # Sensations / states (20)
    "warm", "cold", "sweet", "bitter", "sharp", "soft", "loud", "quiet", "fresh", "rotten",
    "heavy", "light", "wet", "dry", "rough", "smooth", "bright", "dark", "thick", "thin",
]


# ---- Signature generation (multi-modal phase per concept) ----

def signature_for(concept, perturbation_seed=None, noise_scale=0.0):
    """Deterministic 6D phase signature per concept.

    Same concept → same center across calls. perturbation_seed adds noise
    (substrate-true: real F1 transducer samples from a distribution; here the
    'distribution' is concept_center ± noise).
    """
    # Concept's center phase in each modality — derived from word characters
    # (in production this comes from the catalog's LLM-derived parameter dict)
    h = sum(ord(c) * (i + 1) for i, c in enumerate(concept))
    rng_center = np.random.default_rng(h)
    center = {m: float(rng_center.uniform(0, 2 * math.pi)) for m in MODALITIES}

    if perturbation_seed is None and noise_scale == 0:
        return center

    rng_pert = np.random.default_rng(h * 1000 + (perturbation_seed or 0))
    return {m: (center[m] + noise_scale * rng_pert.standard_normal()) % (2 * math.pi)
            for m in MODALITIES}


# ---- Grandurun state vector (true multi-modal fingerprint) ----

def grandurun_state(phases):
    """7D complex state vector. First 6 dims = per-modality phase as
    exp(1j * phase_m). Dim 7 = polarity (constant for positive bindings).

    Inner product properties:
      |<state_A, state_B>| = |sum_m exp(1j * (phase_A_m - phase_B_m))| + 1
      Max value = 7 (all phases match)
      Min value ≈ 0 (phases uniformly distributed apart)
    """
    vec = np.zeros(7, dtype=np.complex128)
    for i, m in enumerate(MODALITIES):
        vec[i] = cmath.exp(1j * phases[m])
    vec[6] = 1.0 + 0.0j  # polarity
    return vec


# ---- Substrate ----

class CogNeuron:
    """Per-neuron atlas with state-vector bindings. Each neuron has a
    position_offset that shifts its phase frame — Sur's-ferrets variance."""

    def __init__(self, neuron_id, position_offset=0.0):
        self.neuron_id = neuron_id
        self.position_offset = position_offset
        self.atlas = []  # [{concept, state_vec, tick}]
        # Vectorized cache built once after teaching
        self._atlas_matrix = None  # (N_bindings, 7) complex
        self._atlas_concepts = None  # length-N list

    def _offset_phases(self, phases):
        return {m: (p + self.position_offset) % (2 * math.pi)
                for m, p in phases.items()}

    def experience_moment(self, concept, phases, tick):
        state_vec = grandurun_state(self._offset_phases(phases))
        self.atlas.append({"concept": concept, "state_vec": state_vec, "tick": tick})
        self._atlas_matrix = None  # invalidate cache

    def _build_cache(self):
        if self._atlas_matrix is None and self.atlas:
            self._atlas_matrix = np.stack([e["state_vec"] for e in self.atlas])
            self._atlas_concepts = [e["concept"] for e in self.atlas]

    def recall_best(self, query_phases, mask=None):
        """Find atlas binding with highest |⟨target, binding⟩|.

        mask: optional length-7 complex array zeroing out modalities not
        present in the query (for partial-modality recall).
        """
        self._build_cache()
        target = grandurun_state(self._offset_phases(query_phases))
        if mask is not None:
            target = target * mask
            atlas = self._atlas_matrix * mask
        else:
            atlas = self._atlas_matrix
        # |inner product| for every binding at once
        inners = np.abs(atlas @ np.conj(target))
        best_idx = int(np.argmax(inners))
        return self._atlas_concepts[best_idx], float(inners[best_idx])


def build_brain(neurons_per_hemi):
    brain = []
    # Position offsets spread across the ring — Sur's-ferrets discipline.
    # Each neuron at a unique phase position.
    total_neurons = neurons_per_hemi * N_HEMIS
    for idx in range(total_neurons):
        offset = (2 * math.pi * idx / total_neurons)
        hi = idx // neurons_per_hemi
        ni = idx % neurons_per_hemi
        brain.append(CogNeuron(f"H{hi}_n{ni}", offset))
    return brain


# ---- Test harness ----

def test_scale(neurons_per_hemi, n_concepts, n_reps, n_test_perturbations=4,
               training_noise=0.05, query_noise=0.15):
    total_neurons = neurons_per_hemi * N_HEMIS
    print(f"\n  {N_HEMIS}×{neurons_per_hemi} = {total_neurons:>5} neurons, "
          f"{n_concepts:>2} concepts, {n_reps} reps", end="  ")

    concepts = CONCEPT_CORPUS[:n_concepts]
    brain = build_brain(neurons_per_hemi)

    # Teach
    t0 = time.time()
    tick = 0
    for rep in range(n_reps):
        for concept in concepts:
            phases = signature_for(concept, perturbation_seed=rep, noise_scale=training_noise)
            for n in brain:
                n.experience_moment(concept, phases, tick)
            tick += 1
    t_teach = time.time() - t0

    # Recall — population votes by max-pooling per neuron
    t1 = time.time()
    correct = 0
    total = 0
    confusion = defaultdict(Counter)
    for concept in concepts:
        for pert in range(n_test_perturbations):
            query = signature_for(concept, perturbation_seed=10000 + pert,
                                  noise_scale=query_noise)
            votes = Counter()
            for n in brain:
                best_c, _ = n.recall_best(query)
                votes[best_c] += 1
            predicted = votes.most_common(1)[0][0]
            confusion[concept][predicted] += 1
            if predicted == concept:
                correct += 1
            total += 1
    t_recall = time.time() - t1

    accuracy = 100 * correct / total
    baseline = 100 / n_concepts
    print(f"|  acc {correct:>3}/{total:>3} = {accuracy:>5.1f}%  ({accuracy/baseline:>4.1f}× chance)  "
          f"|  teach {t_teach:>5.1f}s  recall {1000*t_recall/total:>4.0f}ms/q")

    if accuracy < 95:
        confs = [(c, p, cnt) for c, preds in confusion.items()
                  for p, cnt in preds.items() if p != c]
        confs.sort(key=lambda x: -x[2])
        if confs:
            print(f"     confusions:", end="")
            for c, p, cnt in confs[:5]:
                print(f"  {c}→{p}({cnt})", end="")
            print()

    return accuracy


def test_partial_modality(neurons_per_hemi, n_concepts, n_reps, modalities_used,
                           training_noise=0.05, query_noise=0.15):
    """Recall when ONLY some modalities are present in the query.

    Real cross-modal binding: see a rabbit (visual only) → recall the word
    "rabbit". The substrate should aggregate evidence from whichever
    modalities are present.
    """
    total_neurons = neurons_per_hemi * N_HEMIS
    print(f"\n  partial recall via {modalities_used}: ", end="")

    concepts = CONCEPT_CORPUS[:n_concepts]
    brain = build_brain(neurons_per_hemi)

    # Teach with FULL signatures
    tick = 0
    for rep in range(n_reps):
        for concept in concepts:
            phases = signature_for(concept, perturbation_seed=rep, noise_scale=training_noise)
            for n in brain:
                n.experience_moment(concept, phases, tick)
            tick += 1

    # Recall with ONLY the specified modalities — zero out the others
    correct = 0
    total = 0
    mask = np.array([1.0 if m in modalities_used else 0.0
                      for m in MODALITIES] + [0.0], dtype=np.complex128)
    for concept in concepts:
        for pert in range(4):
            full_query = signature_for(concept, perturbation_seed=10000 + pert,
                                       noise_scale=query_noise)
            partial_query = {m: (full_query[m] if m in modalities_used else 0.0)
                             for m in MODALITIES}
            votes = Counter()
            for n in brain:
                best_c, _ = n.recall_best(partial_query, mask=mask)
                votes[best_c] += 1
            predicted = votes.most_common(1)[0][0]
            if predicted == concept:
                correct += 1
            total += 1

    accuracy = 100 * correct / total
    baseline = 100 / n_concepts
    print(f"acc {correct}/{total} = {accuracy:.1f}%  ({accuracy/baseline:.1f}× chance)")
    return accuracy


if __name__ == "__main__":
    print("=" * 88)
    print("Cognition substrate v2 — full multi-modal phase fingerprint + max-pooled population vote")
    print("=" * 88)

    # 1. Progressive scale at moderate concept count
    print("\n--- Progressive scale (50 concepts, training noise 0.05, query noise 0.15) ---")
    test_scale(neurons_per_hemi=8,   n_concepts=5,   n_reps=3)
    test_scale(neurons_per_hemi=8,   n_concepts=25,  n_reps=3)
    test_scale(neurons_per_hemi=8,   n_concepts=50,  n_reps=3)
    test_scale(neurons_per_hemi=32,  n_concepts=50,  n_reps=3)
    test_scale(neurons_per_hemi=128, n_concepts=50,  n_reps=3)

    # 2. Push concept count: 75, 100 at full 1024-neuron brain
    print("\n--- Vocabulary scaling (1024 neurons) ---")
    test_scale(neurons_per_hemi=128, n_concepts=75,  n_reps=3)
    test_scale(neurons_per_hemi=128, n_concepts=100, n_reps=3)

    # 3. Noise robustness at 100 concepts
    print("\n--- Noise robustness (1024 neurons, 100 concepts) ---")
    test_scale(neurons_per_hemi=128, n_concepts=100, n_reps=3, query_noise=0.3)
    test_scale(neurons_per_hemi=128, n_concepts=100, n_reps=3, query_noise=0.5)
    test_scale(neurons_per_hemi=128, n_concepts=100, n_reps=3, query_noise=0.8)

    # 4. Partial-modality recall — cross-modal binding test
    print("\n--- Partial-modality recall (1024 neurons, 100 concepts) ---")
    test_partial_modality(128, 100, 3, ["visual"])
    test_partial_modality(128, 100, 3, ["visual", "tactile"])
    test_partial_modality(128, 100, 3, ["visual", "tactile", "auditory"])
    test_partial_modality(128, 100, 3, ["language"])
    test_partial_modality(128, 100, 3, ["visual", "auditory", "tactile", "olfactory", "gustatory"])  # no language
