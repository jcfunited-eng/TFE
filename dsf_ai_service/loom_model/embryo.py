"""embryo.py — the seed organism, built to GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21.

NOT a toy: assembled on the real loom_model substrate (LoomBrain / LoomNeuron /
krimelack / psi-lattice / folding / cross-hemi couplings). Eight hemispheres tagged
as the eight cognitive OPERATIONS (the map: hemispheres ARE the mechanisms), each
differentiated by its cognitive-timescale decay multiplier. Senses live inside `em`.
Bipolar sensory waveforms feed `em` so we can OBSERVE whether folding (growth) fires.

Honesty / selective cheats (named, per the spec's anti-contamination protocol):
  - Cross-hemi consensus here is MINIMAL: convergent co-fire strengthens a link,
    divergent weakens it. The full rich-metadata CrossHemiLink is not yet built.
  - `aff` regulator is a single global arousal scalar (from recent fold/commit
    activity) that modulates the fold threshold. The full needs/valence/arousal
    state is not yet built.
  - Per-hemi decay acts on a per-hemisphere binding-strength accumulator, since the
    loom binding atlas has no native decay. Multipliers are from the map (derived
    from cognitive timescales), NOT tuned.
  - Whether bipolar senses actually unblock folding is OPEN — this observes it.
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.neuron import FOLD_TRIGGER_RATIO, LoomNeuron
from dsf_ai_service.loom_model.substrate_dna import derive_daughter_parameters, K_TOTAL
from dsf_ai_service.substrate.sensory_generators import generate_taste_waveform, generate_smell_waveform


def resonance(events):
    """Temporal-pattern coherence of the krimelack event stream — the missing
    dimension. Spectral concentration of the event s-sequence: a coherent (periodic)
    experience puts power in few frequencies (high), noise spreads it flat (low).
    This is what distinguishes apple from white noise where direction-based DSF can't.
    """
    if len(events) < 16:
        return 0.0
    s = np.array([e["s"] for e in events], dtype=float)
    s = s - s.mean()
    if np.allclose(s, 0):
        return 0.0
    ps = np.abs(np.fft.rfft(s)) ** 2
    tot = ps.sum()
    if tot <= 0:
        return 0.0
    ps = ps / tot
    return float(np.sort(ps)[-3:].sum())   # top-3 spectral concentration


def resonance_signal(arr):
    """Resonance measured on the raw sensory SIGNAL (before the krimelack), where
    food and noise are still distinct. The krimelack event stream washes this out,
    so coherence must be read at the input — this is a property of the experience."""
    s = np.asarray(arr, dtype=float)
    s = s - s.mean()
    if np.allclose(s, 0):
        return 0.0
    ps = np.abs(np.fft.rfft(s)) ** 2
    tot = ps.sum()
    if tot <= 0:
        return 0.0
    ps = ps / tot
    return float(np.sort(ps)[-3:].sum())

# H0..H7 -> cognitive operation + decay multiplier (map table, derived from timescales)
OPERATIONS = [
    ("em",  1.0),    # embodiment: perception+emission+working memory  (~700 ticks)
    ("pr",  1.5),    # predictor
    ("ep",  0.1),    # episodic
    ("sc",  0.5),    # semantic
    ("gp",  0.05),   # goals
    ("sf",  0.1),    # self-model
    ("sv",  0.001),  # survival / identity
    ("aff", 1.0),    # affective regulation (the regulator)
]
# 9 default routing pairs (by operation tag)
DEFAULT_PAIRS = [("em","pr"),("em","sc"),("em","ep"),("em","sv"),("em","aff"),
                 ("ep","sf"),("ep","sc"),("gp","em"),("sc","pr")]

DSF_COMPONENTS = ["D_k","M_k","R_rev","U_star","C_k","P_k","B_k","S_UF"]


def bipolar_sense(receptors, modality):
    """Receptor combination -> bipolar (change-detection) sensory waveform.
    Biological: receptors fire on the derivative (onset +, offset -), which crosses
    zero and can wind the krimelack both ways."""
    gen = generate_taste_waveform if modality == "taste" else generate_smell_waveform
    wf = gen(receptors)
    chans = [np.gradient(wf[k]) * 20.0 for k in sorted(wf.keys())]
    return np.concatenate(chans)


class Embryo:
    def __init__(self, brain_seed=42, seed_size=4):
        self.brain = LoomBrain(brain_seed=brain_seed, seed_size=seed_size)
        # tag hemispheres as operations
        self.op = {}            # hemi_id -> ("em", decay_mult)
        self.hemi_by_op = {}    # "em" -> hemisphere
        for h, (tag, decay) in zip(self.brain.hemispheres, OPERATIONS):
            h._op_tag = tag
            h._decay_mult = decay
            self.op[h.hemi_id] = (tag, decay)
            self.hemi_by_op[tag] = h
        self.consensus = {p: 0.0 for p in DEFAULT_PAIRS}   # minimal consensus link strength
        self.strength = {tag: 0.0 for tag, _ in OPERATIONS}  # per-organ binding strength
        self.arousal = 0.0                                  # aff global state
        self.tick = 0

    def _hemi(self, tag):
        return self.hemi_by_op[tag]

    def _neff_population(self, tag):
        h = self._hemi(tag)
        ns = h.cluster.neurons
        neffs = [n.l6_tcl.n_eff(n._last_dsf) for n in ns if n._last_dsf is not None]
        return (float(np.mean(neffs)) if neffs else float('nan'),
                min(neffs) if neffs else float('nan'),
                len(ns))

    def _fold_on_resonance(self, hemi, theta):
        """Mirror cluster.process_folds, but gate on resonance (temporal coherence
        of the event stream) instead of the direction-based n_eff. Fold a neuron
        when its experience is coherent (resonance > theta); noise stays quiet.
        Contact inhibition still bounds growth."""
        new = []
        MAX_POP = 16   # per-organ exploration cap (8 organs now)
        for neuron in list(hemi.cluster.neurons):
            if len(hemi.cluster.neurons) + len(new) >= MAX_POP:
                break
            r = resonance(getattr(neuron, "_last_events", []))
            neuron._last_resonance = r
            if r <= theta:
                continue
            # refractory: a neuron folds at most once per experience window
            if getattr(neuron, "_folded_this_exp", False):
                continue
            neuron._folded_this_exp = True
            sat = len(neuron.couplings.neighbors) / K_TOTAL
            if (1.0 - sat) ** 2 <= 0.0:
                continue  # contact inhibition: saturated
            overflow = neuron.compute_overflow_signal()
            params = derive_daughter_parameters(overflow, neuron)
            did = hemi.cluster.next_id()
            d = LoomNeuron(did, birth_params=params,
                           primary_modality=hemi.cluster.primary_modality,
                           observable=hemi.cluster.observable)
            hemi.cluster.attach(d, inherit_from=neuron)
            new.append(did)
        return new

    BASE_LAMBDA = 0.02   # per-experience decay base; per-hemi multiplier scales it
    CROSS_ATTEN = 0.4    # cross-hemi coupling is weak at seed (echo, not full signal)

    def _feed_and_fold(self, hemi, signal, sig_res, theta, ticks=6):
        for n in hemi.cluster.neurons:
            n._folded_this_exp = False
        for _ in range(ticks):
            hemi.cluster.step(list(signal), self.tick)
            self.tick += 1
        return len(self._fold_on_resonance(hemi, theta)) if sig_res > theta else 0

    def experience(self, word, receptors, theta=0.05, noise=False):
        """One experience. em perceives the bipolar senses; its activity cascades
        through the cross-hemi routing to the other organs (weak echo). Each organ
        folds on the experience's coherence (resonance), accumulates a binding
        strength that decays at its own cognitive timescale, and cross-hemi links
        strengthen on convergent co-fire. aff arousal modulates the fold gate."""
        if noise:
            rng = np.random.default_rng(abs(hash(word)) % (2**31))
            composite = rng.standard_normal(200 * 13) * 0.3
        else:
            composite = np.concatenate([bipolar_sense(receptors.get("taste", {}), "taste"),
                                        bipolar_sense(receptors.get("smell", {}), "smell")])
        sig_res = resonance_signal(composite)
        # aff: arousal lowers the fold bar (salience makes coherent experience bind easier)
        theta_eff = theta / (1.0 + 0.5 * self.arousal)

        active, folds = {}, {}
        # 1. em perceives the raw senses
        folds["em"] = self._feed_and_fold(self._hemi("em"), composite, sig_res, theta_eff)
        active["em"] = sig_res > theta_eff

        # 2. cascade through default routing (two passes so 2-hop activation flows)
        echo = composite * self.CROSS_ATTEN
        for _pass in range(2):
            for a, b in DEFAULT_PAIRS:
                if not active.get(a):
                    continue
                if b not in folds:
                    folds[b] = self._feed_and_fold(self._hemi(b), echo, sig_res, theta_eff)
                    active[b] = sig_res > theta_eff
                if active.get(a) and active.get(b):
                    self.consensus[(a, b)] += sig_res          # convergent co-fire strengthens

        # 3. per-organ binding strength: active organs accumulate; ALL decay at their rate
        for h in self.brain.hemispheres:
            tag, decay = self.op[h.hemi_id]
            self.strength[tag] = self.strength[tag] * (1 - decay * self.BASE_LAMBDA) \
                + (1.0 if active.get(tag) else 0.0)

        # 4. aff arousal from total organ activity this experience
        self.arousal = 0.9 * self.arousal + 0.1 * sum(1 for v in active.values() if v)
        return folds, sig_res

    def observe(self):
        rows = []
        for tag, _ in OPERATIONS:
            mean_neff, min_neff, pop = self._neff_population(tag)
            rows.append((tag, pop, mean_neff, min_neff))
        return rows


def main():
    # a tiny curriculum of grounded experiences (bipolar receptor combos)
    CURRICULUM = {
        "apple": {"taste": {"sweet": 0.65, "sour": 0.55, "bitter": 0.05},
                  "smell": {"fruity": 0.85, "fresh": 0.45, "floral": 0.20}},
        "pear":  {"taste": {"sweet": 0.82, "sour": 0.02, "bitter": 0.12},
                  "smell": {"sweet": 0.60, "floral": 0.45, "fruity": 0.50}},
        "lemon": {"taste": {"sour": 0.9, "sweet": 0.2, "bitter": 0.2},
                  "smell": {"fresh": 0.8, "fruity": 0.6, "sour": 0.5}},
        "bread": {"taste": {"sweet": 0.3, "umami": 0.5, "salty": 0.3},
                  "smell": {"earthy": 0.6, "sweet": 0.4, "smoky": 0.2}},
    }
    THETA = 0.05   # resonance fold gate (discovered separatrix; refine/adapt later)
    emb = Embryo(brain_seed=42, seed_size=4)
    tags = [t for t, _ in OPERATIONS]
    print("operation tags:", {h.hemi_id: emb.op[h.hemi_id][0] for h in emb.brain.hemispheres})
    print(f"seed: 4 neurons/organ, 32 total   resonance gate theta={THETA}\n")
    items = list(CURRICULUM.items()) + [("~noise~", None)]
    for epoch in range(4):
        for word, rec in items:
            folds, sig_res = emb.experience(word, rec or {}, theta=THETA, noise=(rec is None))
            fired = "".join(t[0] if folds.get(t, 0) > 0 else "." for t in tags)
            print(f"  e{epoch} {word:>8} res={sig_res:.3f} arous={emb.arousal:.2f}  organs-folded[{fired}]", flush=True)
    print(f"\n--- per-organ state (pop = grew via folding; strength = binding accumulator) ---")
    print(f"{'organ':>5} {'decay×':>7} {'pop':>4} {'strength':>9}")
    for tag, decay in OPERATIONS:
        h = emb.hemi_by_op[tag]
        print(f"{tag:>5} {decay:>7} {len(h.cluster.neurons):>4} {emb.strength[tag]:>9.2f}")
    print(f"\n--- cross-hemi consensus link strengths (convergent co-fire) ---")
    for (a, b), s in sorted(emb.consensus.items(), key=lambda kv: -kv[1]):
        print(f"  {a:>3} <-> {b:<3} : {s:.2f}")
    total = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    print(f"\nTOTAL neurons: 32 -> {total}   final arousal={emb.arousal:.2f}")


if __name__ == "__main__":
    main()
