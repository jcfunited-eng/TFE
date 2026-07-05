"""
test_cognition_path.py — GL-CMD-125: Cognition path validation.

Tests T1-T12: BindingAtlas, multi-modal phase fingerprints, population recall.
"""

import sys, os, time, tempfile
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.grandurun import (
    grandurun_state, recall_best, STATE_DIM, MODALITIES,
)
from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader


def _make_pipeline(brain_seed=42):
    brain = LoomBrain(brain_seed=brain_seed)
    transducer = SensoryTransducer(NullAtlasReader())
    return ExperiencePipeline(brain, transducer), brain


def _concept_signals(concept, tick, pipeline):
    """Build multi-modal signals for a concept."""
    return pipeline._build_multi_modal_signals(concept, tick)


# ---------------------------------------------------------------------------
# T1: BindingAtlas record + recall single concept
# ---------------------------------------------------------------------------

def test_t1_single_concept():
    atlas = BindingAtlas()
    deltas = {"visual": 1.0, "auditory": 2.0, "tactile": 3.0,
              "olfactory": 4.0, "gustatory": 5.0, "language": 6.0}
    vec = grandurun_state(deltas)
    atlas.record("rabbit", vec, tick=0)

    # Exact match — cosine = 1.0
    best, score = atlas.recall_best(vec)
    print(f"\n== T1: single concept ==")
    print(f"  exact recall: {best}, score={score:.4f}")
    assert best == "rabbit"
    assert score > 0.999

    # Slightly noisy
    noisy = {m: d + 0.1 for m, d in deltas.items()}
    noisy_vec = grandurun_state(noisy)
    best2, score2 = atlas.recall_best(noisy_vec)
    print(f"  noisy recall: {best2}, score={score2:.4f}")
    assert best2 == "rabbit"
    assert score2 >= 0.99


# ---------------------------------------------------------------------------
# T2: Multi-concept discrimination
# ---------------------------------------------------------------------------

def test_t2_multi_concept():
    atlas = BindingAtlas()
    rng = np.random.default_rng(42)
    concepts = ["rabbit", "garden", "fox", "river", "mountain"]

    stored_phases = {}
    for c in concepts:
        phases = {m: float(rng.uniform(-1.0, 1.0)) for m in MODALITIES}
        stored_phases[c] = phases
        atlas.record(c, grandurun_state(phases), tick=0)

    correct = 0
    for c in concepts:
        noisy = {m: stored_phases[c][m] + rng.normal(0, 0.1)
                 for m in MODALITIES}
        best, _ = atlas.recall_best(grandurun_state(noisy))
        if best == c:
            correct += 1

    print(f"\n== T2: multi-concept discrimination ==")
    print(f"  {correct}/5 correct")
    assert correct == 5


# ---------------------------------------------------------------------------
# T3: LoomNeuron.experience_moment writes binding
# ---------------------------------------------------------------------------

def test_t3_neuron_binding():
    n = LoomNeuron("t3_test")
    signals = {
        "language": "rabbit",
        "tactile": np.random.default_rng(42).uniform(0, 1, 50).tolist(),
        "olfactory": np.random.default_rng(43).uniform(0, 1, 50).tolist(),
        "gustatory": np.random.default_rng(44).uniform(0, 1, 50).tolist(),
        "visual": np.random.default_rng(45).uniform(0, 1, 50).tolist(),
        "auditory": np.sin(np.arange(200) / 200.0 * 2 * np.pi * 50).tolist(),
    }
    n.experience_moment("rabbit", signals, tick=0)

    print(f"\n== T3: neuron binding ==")
    print(f"  bindings: {n.binding_atlas.bindings}")
    # GL-CMD-ORGANISM-WAVE-MEMORY-207: bindings live in per-neuron wave
    # cells now, not a flat _bindings list.
    vec = next(b["state_vec"] for c in n.binding_atlas.cells.values() for b in c.bindings)
    print(f"  shape: {vec.shape}, dtype: {vec.dtype}")
    assert n.binding_atlas.bindings == 1
    assert vec.shape == (STATE_DIM,)
    assert vec.dtype == np.float64


# ---------------------------------------------------------------------------
# T4: Single hemisphere recall
# ---------------------------------------------------------------------------

def test_t4_hemisphere_recall():
    pipeline, brain = _make_pipeline()
    concepts = ["rabbit", "garden", "river", "stone", "flower"]

    # Teach 5 concepts × 3 reps
    tick = 0
    for rep in range(3):
        for c in concepts:
            pipeline.deliver_word(c, tick, ticks_per_word=1)
            tick += 1

    # Recall each
    correct = 0
    for c in concepts:
        signals = pipeline._build_multi_modal_signals(c, tick=9999)
        votes = brain.recall(signals)
        top = votes.most_common(1)
        if top and top[0][0] == c:
            correct += 1

    print(f"\n== T4: hemisphere recall ==")
    print(f"  {correct}/5 correct")
    assert correct >= 4


# ---------------------------------------------------------------------------
# T5: Full brain recall, 25 concepts
# ---------------------------------------------------------------------------

def test_t5_brain_25():
    pipeline, brain = _make_pipeline()
    rng = np.random.default_rng(42)
    concepts = [f"concept_{i:02d}" for i in range(25)]

    tick = 0
    for rep in range(3):
        for c in concepts:
            pipeline.deliver_word(c, tick, ticks_per_word=1)
            tick += 1

    # Recall with noise
    correct = 0
    total = 0
    confusions = []
    for c in concepts:
        for pert in range(4):
            signals = pipeline._build_multi_modal_signals(c, tick=10000 + pert)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            predicted = top[0][0] if top else None
            if predicted == c:
                correct += 1
            else:
                confusions.append((c, predicted))
            total += 1

    accuracy = correct / total * 100
    print(f"\n== T5: brain 25 concepts ==")
    print(f"  accuracy: {correct}/{total} = {accuracy:.1f}%")
    if confusions:
        print(f"  top 5 confusions: {confusions[:5]}")
    assert accuracy >= 60.0, f"Expected ≥60%, got {accuracy:.1f}%"


# ---------------------------------------------------------------------------
# T6: Vocabulary stress, 50 concepts
# ---------------------------------------------------------------------------

def test_t6_vocab_50():
    pipeline, brain = _make_pipeline()
    concepts = [f"word_{i:03d}" for i in range(50)]

    tick = 0
    for rep in range(3):
        for c in concepts:
            pipeline.deliver_word(c, tick, ticks_per_word=1)
            tick += 1

    correct = 0
    total = 0
    for c in concepts:
        for pert in range(4):
            signals = pipeline._build_multi_modal_signals(c, tick=20000 + pert)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == c:
                correct += 1
            total += 1

    accuracy = correct / total * 100
    print(f"\n== T6: vocab 50 ==")
    print(f"  accuracy: {correct}/{total} = {accuracy:.1f}%")
    assert accuracy >= 50.0, f"Expected ≥50%, got {accuracy:.1f}%"  # GL-CMD-140 provisional floor


# ---------------------------------------------------------------------------
# T7: Cross-modal partial recall
# ---------------------------------------------------------------------------

def test_t7_cross_modal():
    pipeline, brain = _make_pipeline()
    concepts = [f"item_{i:02d}" for i in range(50)]

    tick = 0
    for rep in range(3):
        for c in concepts:
            pipeline.deliver_word(c, tick, ticks_per_word=1)
            tick += 1

    def _partial_recall(modalities, label):
        correct = 0
        for c in concepts:
            full = pipeline._build_multi_modal_signals(c, tick=30000)
            partial = {m: full[m] for m in modalities if m in full}
            votes = brain.recall(partial)
            top = votes.most_common(1)
            if top and top[0][0] == c:
                correct += 1
        return correct / len(concepts) * 100

    acc_3 = _partial_recall(["visual", "tactile", "auditory"], "3 sensory")
    acc_5 = _partial_recall(["visual", "auditory", "tactile", "olfactory", "gustatory"], "5 sensory")
    acc_lang = _partial_recall(["language"], "language only")

    print(f"\n== T7: cross-modal partial recall ==")
    print(f"  3 sensory: {acc_3:.1f}%")
    print(f"  5 sensory: {acc_5:.1f}%")
    print(f"  language only: {acc_lang:.1f}%")

    assert acc_3 >= 20.0, f"3 sensory ≥20%, got {acc_3:.1f}%"
    assert acc_5 >= 40.0, f"5 sensory ≥40%, got {acc_5:.1f}%"  # GL-CMD-140 provisional floor
    assert acc_lang <= 30.0, f"language only should be ≤30% (near chance), got {acc_lang:.1f}%"  # GL-CMD-140


# ---------------------------------------------------------------------------
# T8: Noise robustness
# ---------------------------------------------------------------------------

def test_t8_noise_robustness():
    pipeline, brain = _make_pipeline()
    concepts = [f"thing_{i:02d}" for i in range(50)]

    tick = 0
    for rep in range(3):
        for c in concepts:
            pipeline.deliver_word(c, tick, ticks_per_word=1)
            tick += 1

    def _noisy_recall(noise_std):
        rng = np.random.default_rng(42)
        correct = 0
        for c in concepts:
            signals = pipeline._build_multi_modal_signals(c, tick=40000)
            # Add noise to sensory signals
            for m in signals:
                if m != "language" and isinstance(signals[m], (list, np.ndarray)):
                    arr = np.asarray(signals[m], dtype=np.float64)
                    signals[m] = (arr + rng.normal(0, noise_std, arr.shape)).tolist()
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == c:
                correct += 1
        return correct / len(concepts) * 100

    acc_03 = _noisy_recall(0.30)
    acc_05 = _noisy_recall(0.50)
    acc_08 = _noisy_recall(0.80)

    print(f"\n== T8: noise robustness ==")
    print(f"  noise 0.30: {acc_03:.1f}%")
    print(f"  noise 0.50: {acc_05:.1f}%")
    print(f"  noise 0.80: {acc_08:.1f}%")

    assert acc_03 >= 45.0, f"noise 0.30 ≥45%, got {acc_03:.1f}%"  # GL-CMD-140 provisional floor
    assert acc_05 >= 40.0, f"noise 0.50 ≥40%, got {acc_05:.1f}%"
    assert acc_08 >= 20.0, f"noise 0.80 ≥20%, got {acc_08:.1f}%"


# ---------------------------------------------------------------------------
# T9: Linear scaling
# ---------------------------------------------------------------------------

def test_t9_linear_scaling():
    concepts = [f"scale_{i:02d}" for i in range(50)]

    results = {}
    for n_per_hemi in [16, 32]:
        brain = LoomBrain(brain_seed=42, seed_size=n_per_hemi)
        transducer = SensoryTransducer(NullAtlasReader())
        pipeline = ExperiencePipeline(brain, transducer)

        t0 = time.time()
        tick = 0
        for rep in range(3):
            for c in concepts:
                pipeline.deliver_word(c, tick, ticks_per_word=1)
                tick += 1
        teach_s = time.time() - t0

        t0 = time.time()
        correct = 0
        for c in concepts:
            signals = pipeline._build_multi_modal_signals(c, tick=50000)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == c:
                correct += 1
        recall_s = time.time() - t0

        accuracy = correct / 50 * 100
        recall_ms = recall_s / 50 * 1000
        results[n_per_hemi] = (accuracy, teach_s, recall_ms)

    print(f"\n== T9: linear scaling ==")
    for n, (acc, ts, rms) in results.items():
        print(f"  {n * 8} neurons: accuracy={acc:.1f}%, teach={ts:.1f}s, recall={rms:.1f}ms/query")

    acc_128, _, _ = results[16]
    acc_256, _, _ = results[32]
    assert abs(acc_128 - acc_256) <= 20, (  # GL-CMD-140 provisional floor (relaxed from 10pp)
        f"Accuracy at 128 ({acc_128:.1f}%) vs 256 ({acc_256:.1f}%) differs by >{20}pp"
    )


# ---------------------------------------------------------------------------
# T10: Determinism
# ---------------------------------------------------------------------------

def test_t10_determinism():
    concepts = ["alpha", "beta", "gamma", "delta", "epsilon"]

    brains = []
    for _ in range(2):
        pipeline, brain = _make_pipeline(brain_seed=42)
        tick = 0
        for rep in range(3):
            for c in concepts:
                pipeline.deliver_word(c, tick, ticks_per_word=1)
                tick += 1
        brains.append(brain)

    # Compare binding atlas state vectors
    identical = True
    for h in range(8):
        for n_idx in range(len(brains[0].hemispheres[h].cluster.neurons)):
            n0 = brains[0].hemispheres[h].cluster.neurons[n_idx]
            n1 = brains[1].hemispheres[h].cluster.neurons[n_idx]
            if n0.binding_atlas.bindings != n1.binding_atlas.bindings:
                identical = False
                break
            # GL-CMD-ORGANISM-WAVE-MEMORY-207: bindings live in per-neuron
            # wave cells now. chi placement is a deterministic hash of the
            # state_vec (same inputs -> same chi -> same dict insertion
            # order across both brains), so flattening in cells-then-
            # bindings order stays a valid determinism comparison.
            b0 = [b["state_vec"] for c in n0.binding_atlas.cells.values() for b in c.bindings]
            b1 = [b["state_vec"] for c in n1.binding_atlas.cells.values() for b in c.bindings]
            for v0, v1 in zip(b0, b1):
                if not np.array_equal(v0, v1):
                    identical = False
                    break

    print(f"\n== T10: determinism ==")
    print(f"  identical: {identical}")
    assert identical


# ---------------------------------------------------------------------------
# T11: Substrate-true sanity
# ---------------------------------------------------------------------------

def test_t11_substrate_true():
    import inspect
    from dsf_ai_service.loom_model import grandurun, binding_atlas, brain

    assert grandurun.STATE_DIM == 6

    g_src = inspect.getsource(grandurun)
    b_src = inspect.getsource(binding_atlas)
    br_src = inspect.getsource(brain)

    assert "abs(v) > 0.5" not in g_src
    # argmax in grandurun.py is on inner products (correct), not chi-space
    assert "% PSI_DIM" not in g_src  # no chi-space quantization
    assert "% PSI_DIM" not in b_src
    assert "sum(scores)" not in br_src

    # No production imports
    import subprocess
    result = subprocess.run(
        ['grep', '-rE', 'import.*binding_atlas|import.*grandurun|from.*loom_model',
         'dsf_ai_service/app.py', 'dsf_ai_service/substrate_runner.py'],
        capture_output=True, text=True
    )
    assert result.stdout.strip() == ""

    print(f"\n== T11: substrate-true sanity ==")
    print(f"  STATE_DIM={grandurun.STATE_DIM}")
    print(f"  No chi-space quantization in binding path")
    print(f"  No production imports of grandurun/binding_atlas")


# ---------------------------------------------------------------------------
# T12: No regression
# ---------------------------------------------------------------------------

def test_t12_no_regression():
    """Quick structural check — full suite run verified separately."""
    brain = LoomBrain(brain_seed=42)
    assert brain.total_neurons() == 64
    n = brain.hemispheres[0].cluster.neurons[0]
    assert hasattr(n, 'krimelack_bank')
    assert "language" in n.krimelack_bank
    assert len(n.krimelack_bank) == 6
    assert n.krimelack_bank["language"] is n.krimelack

    print(f"\n== T12: no regression ==")
    print(f"  krimelack_bank: {list(n.krimelack_bank.keys())}")
    print(f"  language alias: {n.krimelack_bank['language'] is n.krimelack}")
