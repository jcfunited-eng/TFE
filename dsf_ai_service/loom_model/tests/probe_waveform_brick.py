"""probe_waveform_brick.py — the one-brick test, honestly.

Claim under test: a real, temporally-structured *waveform* makes apple and pear wind
to genuinely different event streams (and light up M_k/R_rev/S_UF), where the current
non-negative sensory signal does not.

Mechanism found by reading compute_dsf: R_rev (reversals) is nonzero ONLY if the
krimelack winds in BOTH directions, which needs the signal to cross its baseline
(go negative). Every generator output is intensity*envelope >= 0 (a positive bump),
so it only winds +1 -> R_rev=0, B_k=1, M_k~0. A bipolar signal (biological
change-detection: receptors fire on the derivative, +on onset / -on decay) crosses
zero and produces reversals.

Three signal modes, fed through the REAL OscillatorKrimelack, scored with the REAL
compute_dsf:
  RAW    = concat of per-channel envelopes (what the substrate feeds now; non-negative)
  CHANGE = derivative of each channel (bipolar; biological adaptation/onset-offset)
  FLAT   = constant = channel mean (Joe's "flat number")

Concepts: apple, pear (genuinely different receptor combos), and cold_rotting_apple
(apple with story-modulated amplitudes) to test that modulation gives a related-but-
distinct signal.

Run: python -m dsf_ai_service.loom_model.tests.probe_waveform_brick
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.substrate.sensory_generators import generate_taste_waveform, generate_smell_waveform
from dsf_ai_service.sensory_krimelacks import OscillatorKrimelack
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf

# Genuinely different receptor combinations (taste: sweet/sour/salty/bitter/umami;
# smell: sweet/putrid/floral/fruity/smoky/earthy/sour/fresh). Real identities:
CONCEPTS = {
    "apple":  {"taste": {"sweet": 0.65, "sour": 0.55, "bitter": 0.05},
               "smell": {"fruity": 0.85, "fresh": 0.45, "floral": 0.20, "sweet": 0.40}},
    "pear":   {"taste": {"sweet": 0.82, "sour": 0.02, "bitter": 0.12},
               "smell": {"sweet": 0.60, "floral": 0.45, "fruity": 0.50, "fresh": 0.30}},
    # story modulation of apple: cold dampens, rot switches on putrid/sour, hunger note
    "cold_rotting_apple": {"taste": {"sweet": 0.40, "sour": 0.72, "bitter": 0.33, "umami": 0.18},
                           "smell": {"fruity": 0.35, "putrid": 0.55, "earthy": 0.45, "sour": 0.40, "fresh": 0.10}},
}

DSF_NAMES = ["D_k", "M_k", "R_rev", "U_star", "C_k", "P_k", "B_k", "S_UF"]


def composite(params, gen_fn, mode):
    wf = gen_fn(params)                       # {channel: 200-sample envelope}
    chans = [wf[k] for k in sorted(wf.keys())]
    if mode == "RAW":
        sig = np.concatenate(chans)
    elif mode == "CHANGE":
        sig = np.concatenate([np.gradient(c) * 20.0 for c in chans])  # bipolar derivative
    elif mode == "FLAT":
        sig = np.concatenate([np.full_like(c, float(np.mean(c))) for c in chans])
    return sig


def run(concept, modality, mode):
    gen = generate_taste_waveform if modality == "taste" else generate_smell_waveform
    sig = composite(CONCEPTS[concept][modality], gen, mode)
    k = OscillatorKrimelack(omega_0=2.0, kappa=60.0, dt=0.04)
    k.feed_signal(list(sig))
    events = list(k.events)
    dsf = compute_dsf(events)
    return dsf, k.n_events, k.winding


def dsf_arr(dsf):
    return np.array([getattr(dsf, n) for n in DSF_NAMES])


def main():
    for modality in ["taste", "smell"]:
        print(f"\n================ {modality.upper()} ================")
        for mode in ["FLAT", "RAW", "CHANGE"]:
            print(f"\n--- mode={mode} ---")
            print(f"{'concept':>20} {'n_ev':>5} {'wind':>6}  " + " ".join(f"{n:>6}" for n in DSF_NAMES))
            arrs = {}
            for c in CONCEPTS:
                dsf, nev, wind = run(c, modality, mode)
                arrs[c] = dsf_arr(dsf)
                print(f"{c:>20} {nev:>5} {wind:>6}  " + " ".join(f"{v:>6.2f}" for v in arrs[c]))
            # divergence: apple vs pear (different things) and apple vs cold-rot (same thing, story)
            ap = np.linalg.norm(arrs["apple"] - arrs["pear"])
            ar = np.linalg.norm(arrs["apple"] - arrs["cold_rotting_apple"])
            fired = lambda a: ", ".join(DSF_NAMES[i] for i in (1,2,7) if abs(a[i]) > 0.01) or "none"
            print(f"  DSF |apple-pear| = {ap:.3f}   |apple-coldrot| = {ar:.3f}")
            print(f"  M_k/R_rev/S_UF nonzero (apple): {fired(arrs['apple'])}")


if __name__ == "__main__":
    main()
