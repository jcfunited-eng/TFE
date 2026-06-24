"""probe_dynamic_neff.py — find the replacement for the abs(v)>0.5 fold gate.

Joe: that heuristic was a placeholder; the real one should be conditionally dynamic,
keyed on conditions/resonance he can't name yet. Honest method: don't decree a formula
— make n_eff continuous, then see which candidate FOLDS SELECTIVELY: crosses the
n_start/e capture threshold on real coherent experience but NOT on noise. Selectivity
is the signal that a condition is real and not just a looser bar.

Feeds real food + a noise control through a real loom em-neuron, reads the real DSF,
and scores candidate dynamic n_eff forms by selectivity.
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.neuron import FOLD_TRIGGER_RATIO
from dsf_ai_service.loom_model.embryo import bipolar_sense

N_START = 8.0
THRESH = N_START * FOLD_TRIGGER_RATIO   # n_start/e = 2.943

FOOD = {
    "apple": {"taste": {"sweet": 0.65, "sour": 0.55, "bitter": 0.05},
              "smell": {"fruity": 0.85, "fresh": 0.45, "floral": 0.20}},
    "pear":  {"taste": {"sweet": 0.82, "sour": 0.02, "bitter": 0.12},
              "smell": {"sweet": 0.60, "floral": 0.45, "fruity": 0.50}},
    "lemon": {"taste": {"sour": 0.9, "sweet": 0.2, "bitter": 0.2},
              "smell": {"fresh": 0.8, "fruity": 0.6, "sour": 0.5}},
    "bread": {"taste": {"sweet": 0.3, "umami": 0.5, "salty": 0.3},
              "smell": {"earthy": 0.6, "sweet": 0.4, "smoky": 0.2}},
}


def dsf_for(signal, reps=8):
    """Feed a 1-D signal through a real loom em-neuron, SUSTAINED (no-reset
    accumulation, like the embryo), return the accumulated DSF. Resonance/coherence
    builds over repeated exposure; a single taste barely forms structure."""
    brain = LoomBrain(brain_seed=42, seed_size=4)
    n = brain.hemispheres[0].cluster.neurons[0]
    for t in range(reps):
        n.step(list(signal), t)
    return n._last_dsf


def candidates(dsf):
    U = dsf.U_star
    locks = [abs(dsf.D_k), abs(dsf.M_k), dsf.R_rev, dsf.C_k, dsf.P_k, dsf.B_k, dsf.S_UF]
    mass = sum(locks) / len(locks)         # continuous constraint mass (freedom excluded)
    res = dsf.S_UF                          # convergence the substrate already computes
    return {
        "binary(now)":  N_START - sum(1 for v in [dsf.D_k,dsf.M_k,dsf.R_rev,dsf.U_star,dsf.C_k,dsf.P_k,dsf.B_k,dsf.S_UF] if abs(v) > 0.5),
        "A: mass":       N_START * (1 - mass),
        "B: mass*(1-U)": N_START * (1 - mass * (1 - U)),
        "C: mass*res":   N_START * (1 - mass * (0.5 + 0.5 * res)),
        "D: mass+res":   N_START * (1 - np.clip(0.5*mass + 0.5*res, 0, 1)),
    }


def main():
    rng = np.random.default_rng(0)
    cases = {}
    for name, rec in FOOD.items():
        sig = np.concatenate([bipolar_sense(rec.get("taste", {}), "taste"),
                              bipolar_sense(rec.get("smell", {}), "smell")])
        cases[name] = dsf_for(sig)
    # noise control: same length, random bipolar — should NOT fold
    L = 200 * 13
    cases["NOISE"] = dsf_for(rng.standard_normal(L) * 0.3)

    forms = list(candidates(next(iter(cases.values()))).keys())
    print(f"capture threshold (fold if n_eff < this): {THRESH:.3f}\n")
    print(f"{'case':>8}  " + "  ".join(f"{f:>13}" for f in forms))
    table = {}
    for name, dsf in cases.items():
        c = candidates(dsf)
        table[name] = c
        print(f"{name:>8}  " + "  ".join(f"{c[f]:>13.3f}" for f in forms))

    print("\nfolds? (n_eff < threshold)")
    print(f"{'case':>8}  " + "  ".join(f"{f:>13}" for f in forms))
    for name in cases:
        marks = ["FOLD" if table[name][f] < THRESH else "-" for f in forms]
        print(f"{name:>8}  " + "  ".join(f"{m:>13}" for m in marks))

    print("\nselectivity (want: all FOOD fold, NOISE does NOT):")
    for f in forms:
        food_folds = sum(1 for n in FOOD if table[n][f] < THRESH)
        noise_folds = table["NOISE"][f] < THRESH
        verdict = "SELECTIVE" if food_folds == len(FOOD) and not noise_folds else (
                  "folds-noise-too" if noise_folds else f"only {food_folds}/{len(FOOD)} food")
        print(f"  {f:>13}: food {food_folds}/{len(FOOD)}, noise={'FOLD' if noise_folds else 'no'}  -> {verdict}")


if __name__ == "__main__":
    main()
