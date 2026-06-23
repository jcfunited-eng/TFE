"""probe_capacity_diversity.py — close the loop: does substrate-true chemical DNA
diversity lift the n=200 recall capacity that started all this?

GL-CMD-144 showed the population is clones (more neurons buy nothing, n=200 -> ~18%).
The embryo work showed per-neuron chemical DNA (kappa/threshold) desynchronizes the
units. This applies that SAME diversity to the real brain.recall and measures whether
it lifts capacity vs the clone baseline. Compare to the earlier random-projection
cheat (18.5 -> 33% at n=200); chemical DNA is the substrate-true version.
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts


def seed_chemical_dna(brain):
    """Per-neuron chemical DNA on every bank krimelack: kappa (receptor gain) and
    threshold (excitability) varied ~2-3x. Same axis that desynced the embryo."""
    idx = 0
    for h in brain.hemispheres:
        for n in h.cluster.neurons:
            rng = np.random.default_rng(1000 + idx)
            for k in n.krimelack_bank.values():
                kg, tg = float(rng.uniform(0.6, 1.6)), float(rng.uniform(0.7, 1.4))
                for obj in (k, getattr(k, "_inner", None)):
                    if obj is None:
                        continue
                    if hasattr(obj, "kappa"):
                        obj.kappa = float(obj.kappa) * kg
                    if hasattr(obj, "threshold"):
                        obj.threshold = float(obj.threshold) * tg
            idx += 1


def t5(n, seed, diverse):
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=seed, seed_size=8)
    if diverse:
        seed_chemical_dna(brain)
    pipe = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
    tick = 0
    for _ in range(3):
        for w in corpus:
            pipe.deliver_word(w, tick, ticks_per_word=1)
            tick += 1
    correct = sum(1 for w in corpus
                  if (brain.recall(pipe._build_multi_modal_signals(w)).most_common(1) or [(None,)])[0][0] == w)
    return correct / n * 100.0


def main():
    print(f"{'n':>5} {'clone baseline':>15} {'chemical DNA diverse':>22}")
    for n in [100, 200]:
        b = np.mean([t5(n, s, False) for s in [42]])
        d = np.mean([t5(n, s, True) for s in [42]])
        print(f"{n:>5} {b:>14.1f}% {d:>21.1f}%   (delta {d-b:+.1f})", flush=True)


if __name__ == "__main__":
    main()
