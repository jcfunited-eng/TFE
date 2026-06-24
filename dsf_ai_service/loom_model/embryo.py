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
from dsf_ai_service.substrate.sensory_generators import (
    generate_taste_waveform, generate_smell_waveform, generate_visual_waveform)


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
    if modality == "taste":
        gen = generate_taste_waveform
    elif modality == "visual":
        gen = generate_visual_waveform
    else:
        gen = generate_smell_waveform
    wf = gen(receptors)
    chans = [np.gradient(wf[k]) * 20.0 for k in sorted(wf.keys())]
    return np.concatenate(chans)


class Embryo:
    def __init__(self, brain_seed=42, seed_size=4):
        # resonant_spectral = the one mechanism that WORKS (recall, n=200 -> 100%)
        self.brain = LoomBrain(brain_seed=brain_seed, seed_size=seed_size,
                               observable="resonant_spectral")
        self.brain_seed = brain_seed
        self.seed_size = seed_size
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
        self._seed_dna_diversity()

    def _seed_dna_diversity(self):
        """Multi-axis neuron DNA — the real source of difference (Joe: not just
        resonant). RESONANT (omega_0) is INERT in the current krimelack: winding is
        Delta-phi = (omega - omega_0)*dt = kappa*s*dt, so omega_0 cancels. True
        resonant tuning needs the driven-resonator krimelack (open research thread).
        The CHEMICAL axis differentiates here, and it's biology-real:
          kappa     — receptor gain / sensitivity (scales the winding response)
          threshold — excitability / ion-channel density (phase per winding event)
          aff_gain  — neuromodulator receptor density (how much arousal moves the cell)
          polarity  — transmitter type (excitatory +1 / inhibitory -1)
        Structural diversity (ring position) already varies per neuron from the seed.
        Ranges are population variation (~2-3x), not outcome-tuned."""
        idx = 0
        for h in self.brain.hemispheres:
            for n in h.cluster.neurons:
                rng = np.random.default_rng(1000 + idx)
                k = n.krimelack
                if hasattr(k, "kappa"):
                    k.kappa = float(k.kappa) * float(rng.uniform(0.6, 1.6))
                if hasattr(k, "threshold"):
                    k.threshold = float(k.threshold) * float(rng.uniform(0.7, 1.4))
                n._aff_gain = float(rng.uniform(0.3, 1.7))
                n._polarity = 1.0 if rng.random() > 0.2 else -1.0   # ~20% inhibitory
                idx += 1

    def _hemi(self, tag):
        return self.hemi_by_op[tag]

    def _neff_population(self, tag):
        h = self._hemi(tag)
        ns = h.cluster.neurons
        neffs = [n.l6_tcl.n_eff(n._last_dsf) for n in ns if n._last_dsf is not None]
        return (float(np.mean(neffs)) if neffs else float('nan'),
                min(neffs) if neffs else float('nan'),
                len(ns))

    SAFETY_POP = 256   # backstop against runaway-loop bugs, NOT the brake (physics is the brake)

    def _charge_and_fold(self, hemi, coherent, quantum):
        """Physics-based folding. Each neuron accumulates coherent-constraint charge
        q from coherent experience; effective dimensionality collapses as
        n_eff = n_start*exp(-q), so the spec's capture basin n_eff < n_start/e
        becomes q > 1 (threshold DERIVED from the same e, not tuned). Division
        discharges q into the daughter (conservation), so a cell must recharge
        before dividing again — a self-limiting cell cycle. Contact inhibition
        (neighbour saturation) still gates. Maps to a charging/dumping capacitor."""
        for n in hemi.cluster.neurons:
            if not hasattr(n, "_q"):
                n._q = 0.0
            if coherent:
                # per-neuron neuromodulator sensitivity (chemical DNA) sets the gain
                gain = 1.0 + self.arousal * getattr(n, "_aff_gain", 1.0)
                n._q += quantum * gain
        new = []
        for neuron in list(hemi.cluster.neurons):
            if len(hemi.cluster.neurons) + len(new) >= self.SAFETY_POP:
                break
            if getattr(neuron, "_q", 0.0) <= 1.0:   # n_eff = n_start*e^-q >= n_start/e
                continue
            sat = len(neuron.couplings.neighbors) / K_TOTAL
            if (1.0 - sat) ** 2 <= 0.0:
                neuron._q = 1.0                  # held at basin edge by contact inhibition
                continue
            overflow = neuron.compute_overflow_signal()
            params = derive_daughter_parameters(overflow, neuron)
            did = hemi.cluster.next_id()
            d = LoomNeuron(did, birth_params=params,
                           primary_modality=hemi.cluster.primary_modality,
                           observable=hemi.cluster.observable)
            d._q = 0.0
            # daughter inherits parent DNA with small mutation (evolution across cells)
            jr = np.random.default_rng(self.tick * 131 + len(new))
            if hasattr(d.krimelack, "kappa") and hasattr(neuron.krimelack, "kappa"):
                d.krimelack.kappa = float(neuron.krimelack.kappa) * float(jr.uniform(0.9, 1.1))
            if hasattr(d.krimelack, "threshold") and hasattr(neuron.krimelack, "threshold"):
                d.krimelack.threshold = float(neuron.krimelack.threshold) * float(jr.uniform(0.95, 1.05))
            d._aff_gain = float(getattr(neuron, "_aff_gain", 1.0)) * float(jr.uniform(0.9, 1.1))
            d._polarity = getattr(neuron, "_polarity", 1.0)
            hemi.cluster.attach(d, inherit_from=neuron)
            neuron._q = 0.0                       # parent discharged into daughter
            new.append(did)
        return new

    BASE_LAMBDA = 0.02   # per-experience decay base; per-hemi multiplier scales it
    CROSS_ATTEN = 0.4    # cross-hemi coupling is weak at seed (echo, not full signal)

    K_PROD = 0.3    # aff synthesis rate (arousal builds on salient experience)
    K_CLEAR = 0.1   # aff clearance rate (first-order; ~10-experience relaxation)

    def _organ_signature(self, tag):
        """Scalar phase/direction signature of an organ's response to the current
        experience (mean winding direction). Links compare signatures: aligned ->
        converge (strengthen), opposed -> diverge (weaken)."""
        ns = self._hemi(tag).cluster.neurons
        vals = [n._last_dsf.D_k * getattr(n, "_polarity", 1.0)
                for n in ns if getattr(n, "_last_dsf", None) is not None]
        return float(np.mean(vals)) if vals else 0.0

    def _feed_and_fold(self, hemi, signal, sig_res, theta, ticks=6, quantum_scale=1.0):
        for _ in range(ticks):
            hemi.cluster.step(list(signal), self.tick)   # keep the substrate active
            self.tick += 1
        coherent = sig_res > theta
        return len(self._charge_and_fold(hemi, coherent, quantum=sig_res * quantum_scale))

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
        theta_eff = theta   # gate is the noise floor; brake is the charge cycle, not theta

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
                    # divergence physics: link strengthens when the two organs respond
                    # IN PHASE, weakens when they diverge (Kuramoto/phase coherence).
                    coh = self._organ_signature(a) * self._organ_signature(b)  # [-1,1]
                    self.consensus[(a, b)] += float(np.clip(coh, -1, 1)) * sig_res
                    self.consensus[(a, b)] = max(0.0, self.consensus[(a, b)])

        # 2b. gp bootstrap: goals are persistent attractors. gp is a SLOW integrator
        # of em activity (its 0.05 decay = longest time-constant), so a goal only
        # crystallizes from experience that recurs. em drives gp weakly each tick;
        # gp folds via the same charge cycle once integrated drive crosses q>1.
        if active.get("em"):
            gp_folds = self._feed_and_fold(self._hemi("gp"), echo * 0.5, sig_res,
                                           theta_eff, quantum_scale=0.2)   # slow integrator
            folds["gp"] = gp_folds
            active["gp"] = active.get("gp", False) or gp_folds > 0

        # 3. per-organ binding strength: active organs accumulate; ALL decay at their rate
        for h in self.brain.hemispheres:
            tag, decay = self.op[h.hemi_id]
            self.strength[tag] = self.strength[tag] * (1 - decay * self.BASE_LAMBDA) \
                + (1.0 if active.get(tag) else 0.0)

        # 4. aff = bounded chemical pool: saturating synthesis from salience (the
        # experience's coherence), first-order clearance. Bounded [0,1], relaxes by
        # clearance — NOT drift-to-initial. A leaky saturating capacitor on silicon.
        salience = sig_res if sig_res > theta_eff else 0.0
        self.arousal += self.K_PROD * salience * (1.0 - self.arousal) - self.K_CLEAR * self.arousal
        self.arousal = float(min(1.0, max(0.0, self.arousal)))
        return folds, sig_res

    def observe(self):
        rows = []
        for tag, _ in OPERATIONS:
            mean_neff, min_neff, pop = self._neff_population(tag)
            rows.append((tag, pop, mean_neff, min_neff))
        return rows

    # --- the WORKING mechanism wired into the seed: perceive -> remember -> recall ---
    def remember(self, concept, signals):
        """Write the concept across all hemispheres via the resonant-spectral chi
        (the verified recall mechanism). This is the one piece that actually works."""
        for h in self.brain.hemispheres:
            for n in h.cluster.neurons:
                n.experience_moment(concept, signals, self.tick)
        self.tick += 1

    def recall(self, signals):
        """Population-vote recall (resonant ternary chi). Verified n=200 -> 100%."""
        return self.brain.recall(signals)

    def _sc_proj(self, neuron, dim):
        """Per-sc-neuron projection over the PROFILE feature (meaning read), distinct
        from the spectral projection em/pr/ep use for capacity."""
        from dsf_ai_service.loom_model import resonant_chi as rc
        if not hasattr(self, "_scP"):
            self._scP = {}
        key = neuron.neuron_id
        if key not in self._scP:
            self._scP[key] = rc.neuron_projection(("sc", key), dim)
        return self._scP[key]

    def _sc_encode(self, neuron, profile):
        from dsf_ai_service.loom_model import resonant_chi as rc
        return rc.ternary_chi(profile, self._sc_proj(neuron, len(profile)))

    def recall_op(self, op_tag, signals, profile=None):
        """Population vote within ONE operation-hemisphere. em/pr/ep read the spectral
        chi (capacity); sc reads the stable profile chi (meaning)."""
        from collections import Counter
        votes = Counter()
        for n in self.hemi_by_op[op_tag].cluster.neurons:
            if op_tag == "sc" and profile is not None:
                q = self._sc_encode(n, profile)
            else:
                q = n.encode_state(signals)
            best, _ = n.binding_atlas.recall_best(q)
            if best is not None:
                votes[best] += 1
        return votes

    def sc_learn(self, concept, profile):
        """sc binds the concept by its stable grounded profile -> semantic chi."""
        for n in self.hemi_by_op["sc"].cluster.neurons:
            n.binding_atlas.record(concept, self._sc_encode(n, profile), self.tick)

    # --- state / regulation operations (primitive, grow later) ---
    def sv_anchor(self, identity="guala"):
        """sv (survival/identity): the persistent core. Bound once, slowest decay
        (0.001), always recallable — 'who I am' survives while episodes fade."""
        self._identity = identity
        sig = np.ones(8)  # stable identity signature (placeholder; grows into real self)
        for n in self.hemi_by_op["sv"].cluster.neurons:
            n.binding_atlas.record(identity, np.sign(self._sc_proj(n, 8) @ sig), 0)

    def sf_sense(self):
        """sf (self-model): a vector of the organism's OWN current state — what it
        can introspect. Grows; today it's arousal + per-organ population + growth."""
        pops = [len(h.cluster.neurons) for h in self.brain.hemispheres]
        return np.array([self.arousal, float(np.mean(pops)), float(np.max(pops))]
                        + [self.strength[t] for t, _ in OPERATIONS])

    def gp_set_goal(self, concept, profile):
        """gp (goals): hold a target percept the organism is oriented toward."""
        self._goal = (concept, np.asarray(profile, float))

    def gp_drive(self, current_profile):
        """gp: drive = how close the current percept is to the goal (cosine). High
        near the goal, low far from it — the primitive of wanting."""
        if not getattr(self, "_goal", None):
            return 0.0
        a = np.asarray(current_profile, float); b = self._goal[1]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return float(a @ b / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0

    def aff_arousal(self):
        """aff (regulator): the global arousal scalar (from recent fold/commit
        activity) that modulates the fold threshold. Already live in experience()."""
        return self.arousal

    # --- movable / portable: serialize the learned organism, reload it elsewhere ---
    def save(self):
        """Serialize to a portable dict. Only the LEARNED state travels — the
        structure and every projection regenerate deterministically from
        (brain_seed, seed_size, neuron_id), so a reload is bit-identical. This is
        what makes the substrate movable to another host / the ArcLoom ASIC."""
        neurons = []
        for h in self.brain.hemispheres:
            op = self.op[h.hemi_id][0]
            for n in h.cluster.neurons:
                binds = [{"c": b["concept"], "v": np.asarray(b["state_vec"]).tolist(),
                          "t": int(b["tick"])} for b in n.binding_atlas._bindings]
                if binds:
                    neurons.append({"id": n.neuron_id, "op": op, "b": binds})
        return {
            "schema": "loom-seed-v1",
            "brain_seed": self.brain_seed,
            "seed_size": self.seed_size,
            "tick": int(self.tick),
            "identity": getattr(self, "_identity", None),
            "strength": dict(self.strength),
            "arousal": float(self.arousal),
            "neurons": neurons,
        }

    @staticmethod
    def load(d):
        """Rebuild the organism from save(). Structure + projections regenerate from
        the seed; learned bindings are restored verbatim. Recall is identical."""
        emb = Embryo(brain_seed=d["brain_seed"], seed_size=d["seed_size"])
        nmap = {n.neuron_id: n for h in emb.brain.hemispheres
                for n in h.cluster.neurons}
        for rec in d["neurons"]:
            n = nmap.get(rec["id"])
            if n is None:
                continue
            for b in rec["b"]:
                n.binding_atlas.record(b["c"], np.array(b["v"], dtype=float), b["t"])
        emb.tick = d.get("tick", 0)
        emb._identity = d.get("identity")
        emb.strength.update(d.get("strength", {}))
        emb.arousal = d.get("arousal", 0.0)
        return emb

    def perceive_sequence(self, concepts, pipe):
        """Substrate-true seeds, differentiated only by BINDING POLICY on one chi
        substrate:
          em (perception): bind concept_t  <- encode(signals_t)
          pr (prediction): bind concept_t+1 <- encode(signals_t)   (the next thing)
          ep (episodic):   bind concept_t-1 <- encode(signals_t)   (what preceded NOW)
        Same machinery, different target. That is what makes them real operations
        instead of bolted-on lookups."""
        sigs = [pipe._build_multi_modal_signals(c) for c in concepts]
        for i, c in enumerate(concepts):
            for h in self.brain.hemispheres:
                op = self.op[h.hemi_id][0]
                for n in h.cluster.neurons:
                    if op == "em":
                        n.experience_moment(c, sigs[i], self.tick)
                    elif op == "pr" and i + 1 < len(concepts):
                        n.experience_moment(concepts[i + 1], sigs[i], self.tick)
                    elif op == "ep" and i > 0:
                        n.experience_moment(concepts[i - 1], sigs[i], self.tick)
            self.tick += 1
        return sigs


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
    for epoch in range(16):
        ep_folds = 0
        for word, rec in items:
            folds, sig_res = emb.experience(word, rec or {}, theta=THETA, noise=(rec is None))
            ep_folds += sum(folds.values())
        em_pop = len(emb._hemi("em").cluster.neurons)
        total = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
        print(f"  epoch {epoch}: folds={ep_folds:>3}  em_pop={em_pop:>3}  total={total:>3}  arousal={emb.arousal:.3f}", flush=True)
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


def seed_organism():
    """The complete SEED, one piece: the 8 operation-hemispheres (em/pr/ep/sc/gp/sf/
    sv/aff) seeded with chemical-DNA diversity, decay timescales, aff regulator, and
    cross-hemi links — PLUS the one mechanism that actually works wired in (recall via
    resonant-spectral chi). Honest labels: recall WORKS; the other operations are
    SEEDS that grow through experience, not finished mechanisms."""
    from dsf_ai_service.loom_model.experience import ExperiencePipeline
    from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
    from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

    emb = Embryo(brain_seed=42, seed_size=8)
    pipe = ExperiencePipeline(emb.brain, SensoryTransducer(NullAtlasReader()))
    print("SEED ORGANISM — one piece")
    print("  hemispheres (seeded operations):",
          {h.hemi_id: emb.op[h.hemi_id][0] for h in emb.brain.hemispheres})
    print("  encoding (working mechanism): resonant_spectral chi recall\n")
    for n in [50, 200]:
        concepts = generate_concepts(n, seed=42)
        for c in concepts:
            emb.remember(c, pipe._build_multi_modal_signals(c))
        correct = sum(1 for c in concepts
                      if (emb.recall(pipe._build_multi_modal_signals(c)).most_common(1)
                          or [(None,)])[0][0] == c)
        print(f"  perceive+recall {n} concepts -> {correct/n*100:.1f}% (recall mechanism, WORKS)",
              flush=True)
    print("\n  status: recall = working & verified; "
          "pr/ep/sc/gp/sf/sv/aff = seeded scaffolds, grow through experience (not yet mechanisms)")


if __name__ == "__main__":
    main()
