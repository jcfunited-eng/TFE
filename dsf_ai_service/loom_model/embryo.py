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
import sys, os, math, uuid
from fractions import Fraction
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.neuron import FOLD_TRIGGER_RATIO, LoomNeuron, MAX_CHI_DISTANCE
from dsf_ai_service.loom_model.substrate_dna import derive_daughter_parameters, K_TOTAL
from dsf_ai_service.loom_model.topology import N_HEMISPHERES
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


def resonance_and_signature(arr):
    """GL-FIX-GROWTH-POOL-LAW-20260716: resonance_signal() plus the top-3
    spectral bin indices it already ranks -- ONE rfft serves both (this
    runs once per experience_word on the organism worker's hot path).
    The bin-index tuple is the growth law's novelty observable: WHICH
    frequencies carried this experience's coherence (replay-stable, and
    measured distinct for genuinely different signals), where sig_res is
    only HOW MUCH coherence. Returns (0.0, None) for an empty/all-zero
    signal -- honest absence, same convention as resonance_signal()."""
    s = np.asarray(arr, dtype=float)
    s = s - s.mean()
    if np.allclose(s, 0):
        return 0.0, None
    ps = np.abs(np.fft.rfft(s)) ** 2
    tot = ps.sum()
    if tot <= 0:
        return 0.0, None
    ps = ps / tot
    top3 = np.argsort(ps)[-3:]
    return float(ps[top3].sum()), tuple(int(b) for b in np.sort(top3))

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


def _structural_dna(hemi_index, ring_pos, ring_N, n_hemispheres=N_HEMISPHERES):
    """Deterministic per-neuron chemical differentiation from STRUCTURE
    (hemisphere index + ring position), replacing the retired
    np.random.default_rng(1000+neuron_index) per
    GL-CMD-ORGANISM-PERSIST-EVE-20260704-169-v1 B1.

    hemi_index/ring_pos are the same two coordinates the retired RNG's
    enumeration order implicitly walked (hemisphere, then neuron-within-
    hemisphere) — only the mapping from position to value changes, from a
    random draw to a deterministic reading, same ring-cosine convention as
    signal_attenuation (neuron.py, GL-CMD-131): one structural angle read at
    four quarter-turn-offset phases, one phase per chemical axis, so a
    single (hemisphere, ring) position yields four distinct scalars with no
    RNG anywhere. Ranges match the retired RNG's (population variation, not
    outcome-tuned); the ~20% inhibitory split matches the pre-existing
    biology note this replaces, not a new tuning.
    """
    frac = (hemi_index * ring_N + ring_pos) / float(n_hemispheres * ring_N)

    def _wave(offset, lo, hi):
        c = 0.5 + 0.5 * math.cos(2.0 * math.pi * (frac + offset))
        return lo + (hi - lo) * c

    kappa_mult = _wave(0.00, 0.6, 1.6)
    threshold_mult = _wave(0.25, 0.7, 1.4)
    aff_gain = _wave(0.50, 0.3, 1.7)
    polarity = -1.0 if ((frac + 0.75) % 1.0) >= 0.8 else 1.0
    return kappa_mult, threshold_mult, aff_gain, polarity


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
    def __init__(self, brain_seed=42, seed_size=4, observable="resonant_spectral",
                 identity_uuid=None):
        # The observable remains a constructor-supplied physical gauge so twin
        # organisms can be compared without assigning semantic identity.
        self.brain = LoomBrain(brain_seed=brain_seed, seed_size=seed_size,
                               observable=observable)
        self.brain_seed = brain_seed
        self.seed_size = seed_size
        # GL-CMD-ORGANISM-PERSIST-169 B1: identity recorded once at birth.
        # Existing callers that never pass identity_uuid (every caller before
        # this dispatch) are unaffected — they just get a fresh uuid stamped
        # on construction, an additive attribute nothing reads yet. The
        # resumable raising loop is the only caller that passes the ORIGINAL
        # uuid back in on load, so identity survives restore.
        self.identity_uuid = identity_uuid or str(uuid.uuid4())
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
        # Conservation pool — population-level division-energy budget.
        # Energy loop (closed): refill flux R = BASE_LAMBDA * N_initial per experience;
        # maintenance flux M = BASE_LAMBDA * N_current per experience (per-neuron upkeep,
        # derived from the existing charge-cycle constant — no new magic values).
        # Net: d(pool)/dt = R - M - divisions = BASE_LAMBDA*(N_initial - N_current) - divs
        # Steady state: pool = 0, d(N)/dt = 0. Mechanism: when N_current > N_initial,
        # M > R → pool drains to 0 → divisions blocked → N stable. Asymptote EMERGES
        # from flux balance; no population constant enforces it.
        # Bounded: pool ≥ 0 always; max total divisions = N_initial (initial pool); N ≤ 2*N_initial.
        self._N_initial = len(OPERATIONS) * seed_size
        # Retained as a backward-compatible telemetry field.  Division energy
        # is no longer preloaded or refilled by the legacy word/spectrum path;
        # exact causal experience contributes to per-organ rational
        # reservoirs below.
        self._div_pool = 0.0
        # GL-CMD-GROWTH-TRUTH-EVE-20260705-198 P3: growth telemetry state.
        # _total_divisions: lifetime count, survives restore (see
        # save_full_state/load_full_state). _fold_events_buffer: per-
        # division detail (hemi/parent/daughter/q), drained by the engine
        # via pop_fold_events() right after each experience_word() call --
        # "growth we cannot see is growth we cannot verify."
        self._total_divisions = 0
        self._fold_events_buffer = []
        self._causal_growth_reservoirs = {
            tag: (0, 1) for tag, _decay in OPERATIONS
        }
        self._causal_growth_parent_cursors = {
            tag: 0 for tag, _decay in OPERATIONS
        }
        self._causal_growth_organ_cursor = 0
        self._causal_growth_applied_claims = []
        # GL-FIX-GROWTH-POOL-LAW-20260716: bounded spectral-signature
        # history for the novelty term of the refill flux (see
        # _experience_core / resonance_and_signature). A repeated
        # experience lands on the same top-3 spectral bins and stops
        # funding; a novel one lands elsewhere and funds. Bounded deque,
        # same discipline as _reflection_snapshots below. Restored-pickle
        # organisms self-heal via _novelty_of_signature's getattr (same
        # -198 pattern as _fold_events_buffer).
        self._recent_input_signatures = None  # lazily created deque (see _novelty_of_signature)
        self._growth_cap_hits = 0
        # GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711, built for
        # real 2026-07-11: bounded (tick, sf_sense_vector) history for real
        # self-state-then-vs-now reflection (see reflect()/_reflect_snapshot()
        # below). Same bounded-deque discipline as every other unbounded-
        # growth fix this project has already shipped (population lane-
        # recompute, fold-events buffer, lane-binding dedup) -- oldest
        # evicted, never unbounded.
        from collections import deque
        self._reflection_snapshots = deque(maxlen=self.REFLECTION_HISTORY_MAXLEN)
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
        GL-CMD-ORGANISM-PERSIST-169 B1: derived from STRUCTURE (hemisphere index
        + ring position, see _structural_dna) — the retired RNG-seeded-by-index
        diversity is gone; identical (brain_seed, seed_size) always yields
        identical DNA with no seed dependency at all, which is what makes birth
        reproducible without needing to separately persist DNA on save/restore.
        Ranges are population variation (~2-3x), not outcome-tuned.

        Idempotent per neuron, per stage -- callable again on an organism
        restored from a pickle that predates the membrane_threshold/
        chi_position stage below (verified directly against the real
        production pickle, tick 223937: _polarity was already correctly
        set at original construction and survives pickling verbatim, but
        membrane_threshold/chi_position were still at raw __init__
        defaults). Uses the fields themselves as the seeded/not-seeded
        marker rather than a new sentinel flag, since an old real pickle
        has no way to carry a flag that didn't exist when it was saved.
        _polarity present -> kappa/krimelack.threshold/aff_gain/polarity
        already done, must NOT re-multiply an already-evolved real
        organism's kappa/threshold a second time. chi_position is None ->
        the newer stage hasn't run yet, backfill only that."""
        for hemi_index, h in enumerate(self.brain.hemispheres):
            for n in h.cluster.neurons:
                already_seeded = getattr(n, "_polarity", None) is not None
                needs_phase1_backfill = getattr(n, "chi_position", None) is None
                if already_seeded and not needs_phase1_backfill:
                    continue
                ring_pos = getattr(n, "ring_pos", 0)
                ring_N = getattr(n, "ring_N", len(h.cluster.neurons))
                kappa_mult, threshold_mult, aff_gain, polarity = _structural_dna(
                    hemi_index, ring_pos, ring_N, len(self.brain.hemispheres))
                if not already_seeded:
                    k = n.krimelack
                    if hasattr(k, "kappa"):
                        k.kappa = float(k.kappa) * kappa_mult
                    if hasattr(k, "threshold"):
                        k.threshold = float(k.threshold) * threshold_mult
                    n._aff_gain = aff_gain
                    n._polarity = polarity
                if not needs_phase1_backfill:
                    continue
                # threshold_mult was previously applied only to the
                # krimelack's own oscillator threshold (winding-event
                # phase wrap, a different mechanism entirely) -- the
                # Phase-1 firing threshold (membrane_threshold, read by
                # receive_spike's fire check) stayed uniformly 1.0 for
                # every neuron regardless of its real per-neuron
                # excitability chemistry, same class of gap as polarity
                # above. Applying it here too means neurons are no longer
                # identically excitable: a population with a real,
                # deterministic 0.7-1.4x spread in how easily each one
                # fires desynchronizes collective activity on its own,
                # rather than 64 neurons crossing threshold in near
                # lock-step (observed directly: all 64 firing 125-144
                # times each over the same 500-word drive before this
                # change -- a suspiciously narrow, synchronized range for
                # a population that's supposed to have real diversity).
                if hasattr(n, "membrane_threshold"):
                    n.membrane_threshold = float(n.membrane_threshold) * threshold_mult
                # chi_position (Phase-1 propagation-delay coordinate) has
                # never been populated anywhere in this codebase --
                # _compute_propagation_delay_ms has always fallen back to
                # a single flat DEFAULT_DELAY_MS for every spike, meaning
                # every hop in the network takes the exact same 1ms with
                # zero variation. That uniform timing lets many small,
                # simultaneously-arriving contributions sum in lockstep
                # across the whole population instead of arriving
                # scattered in time. Real per-neuron structural position
                # already exists (the same hemi_index/ring_pos/ring_N
                # used for the chemical-DNA formula above) -- spreading it
                # across the full chi address space this delay formula
                # was designed to use activates the already-built,
                # already-tested delay mechanism instead of adding a new
                # one.
                if hasattr(n, "chi_position"):
                    n_hemispheres = len(self.brain.hemispheres)
                    structural_index = hemi_index * ring_N + ring_pos
                    total_positions = n_hemispheres * ring_N
                    n.chi_position = int(
                        structural_index * MAX_CHI_DISTANCE / total_positions)

    def _hemi(self, tag):
        return self.hemi_by_op[tag]

    def _neff_population(self, tag):
        h = self._hemi(tag)
        ns = h.cluster.neurons
        neffs = [n.l6_tcl.n_eff(n._last_dsf) for n in ns if n._last_dsf is not None]
        return (float(np.mean(neffs)) if neffs else float('nan'),
                min(neffs) if neffs else float('nan'),
                len(ns))

    # Infrastructure ceiling — loud-stop only; must never trigger with correct conservation
    # physics (N ≤ 2*N_initial << 256). If it fires: conservation pool has a bug.
    _POP_HARDSTOP = 256

    # GL-FIX-GROWTH-POOL-LAW-20260716: organism-TOTAL neuron ceiling
    # (the per-hemisphere _POP_HARDSTOP above allows 8*256=2048 total --
    # not a real whole-organism bound). Config via env, default generous
    # (4x seed; the flux law's own emergent asymptote is N <= 2*N_initial,
    # so a correct organism never reaches this). Loudly logged when hit
    # (Joe's standing rule: bounded RAM/CPU, no silent runaway growth).
    @staticmethod
    def _max_total_neurons():
        try:
            return int(os.environ.get("GUALA_MAX_TOTAL_NEURONS", "256"))
        except (TypeError, ValueError):
            return 256

    def _novelty_of_signature(self, signature):
        # KNOWN FIDELITY LIMIT (2026-07-16 review): the signature is raw
        # rfft bin INDICES compared across composites of varying length --
        # the same bin index means a different physical frequency at a
        # different composite length, so a modality-set change (e.g.
        # visual-only vs visual+auditory moment of the same scene) can read
        # as novel. Errs toward over-funding, and is bounded either way by
        # the flux law itself (refill can never outrun the maintenance
        # asymptote, N <= 2*N_initial) plus the GUALA_MAX_TOTAL_NEURONS
        # hard cap.
        """GL-FIX-GROWTH-POOL-LAW-20260716: novelty of THIS experience,
        measured on its spectral signature (resonance_and_signature's
        top-3 rfft bin indices -- the SAME bins the fold gate's own
        coherence measure ranks) against a bounded history of recent
        experiences.

        familiarity = mean bin-overlap fraction with the recent history
        (|intersection| / 3 per past experience); novelty = 1 -
        familiarity. A replayed/looped signal fills the history with its
        own exact signature -> overlap 1.0 -> novelty -> 0 -> funds
        nothing (growth can never scale with tick count, only with novel
        experience). An empty history (first real experience) is fully
        novel. None signature (no real signal) is 0.0 novelty -- a
        silent moment funds nothing, same convention as sig_res.

        Self-heals the history attribute for organisms restored from a
        pre-fix pickle (same getattr pattern as _fold_events_buffer)."""
        if signature is None:
            return 0.0
        history = getattr(self, "_recent_input_signatures", None)
        if history is None:
            from collections import deque
            history = deque(maxlen=self.NOVELTY_HISTORY_MAXLEN)
            self._recent_input_signatures = history
        if not history:
            history.append(signature)
            return 1.0
        sig_set = set(signature)
        denom = float(len(signature))
        fam = 0.0
        for past in history:
            fam += len(sig_set.intersection(past)) / denom
        novelty = 1.0 - (fam / len(history))
        history.append(signature)
        return max(0.0, min(1.0, novelty))

    # Bounded history length: structural bound only (same bounded-deque
    # discipline as REFLECTION_HISTORY_MAXLEN / _fold_events_buffer), a
    # judgment call stated plainly, not physics tuning: long enough that
    # one experience's signature doesn't age out within a normal reading
    # breath, short enough to stay O(hundreds) per experience.
    NOVELTY_HISTORY_MAXLEN = 256

    def _causal_growth_state(self):
        """Return validated, backward-compatible causal plasticity state."""
        organ_order = tuple(tag for tag, _decay in OPERATIONS)
        reservoirs = getattr(self, "_causal_growth_reservoirs", None)
        if reservoirs is None:
            reservoirs = {tag: (0, 1) for tag in organ_order}
            self._causal_growth_reservoirs = reservoirs
        if set(reservoirs) != set(organ_order):
            raise RuntimeError("causal growth reservoirs changed organ extent")
        exact_reservoirs = {}
        for tag in organ_order:
            value = reservoirs[tag]
            if (
                not isinstance(value, tuple)
                or len(value) != 2
                or any(
                    isinstance(part, bool) or not isinstance(part, int)
                    for part in value
                )
                or value[0] < 0
                or value[1] <= 0
            ):
                raise RuntimeError(
                    f"causal growth reservoir {tag} is not an exact fraction"
                )
            exact_reservoirs[tag] = Fraction(value[0], value[1])
        cursors = getattr(self, "_causal_growth_parent_cursors", None)
        if cursors is None:
            cursors = {tag: 0 for tag in organ_order}
            self._causal_growth_parent_cursors = cursors
        if (
            set(cursors) != set(organ_order)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in cursors.values()
            )
        ):
            raise RuntimeError("causal growth parent cursors changed")
        organ_cursor = getattr(self, "_causal_growth_organ_cursor", 0)
        if (
            isinstance(organ_cursor, bool)
            or not isinstance(organ_cursor, int)
            or organ_cursor < 0
        ):
            raise RuntimeError("causal growth organ cursor changed")
        applied = getattr(self, "_causal_growth_applied_claims", None)
        if applied is None:
            applied = []
            self._causal_growth_applied_claims = applied
        if (
            not isinstance(applied, list)
            or len(applied) > self._N_initial
            or any(
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
                for value in applied
            )
            or len(set(applied)) != len(applied)
        ):
            raise RuntimeError("causal growth checkpoint claims changed")
        return organ_order, exact_reservoirs, cursors, organ_cursor, applied

    def _store_causal_growth_reservoirs(self, reservoirs):
        self._causal_growth_reservoirs = {
            tag: (value.numerator, value.denominator)
            for tag, value in reservoirs.items()
        }
        self._div_pool = float(sum(reservoirs.values(), Fraction(0, 1)))

    def _select_causal_growth_parent(self, tag, cursor):
        neurons = self._hemi(tag).cluster.neurons
        if not neurons:
            return None, cursor
        ordered = [
            neurons[(cursor + offset) % len(neurons)]
            for offset in range(len(neurons))
        ]
        eligible = [
            neuron for neuron in ordered
            if getattr(neuron, "_last_dsf", None) is not None
            and len(neuron.couplings.neighbors) < K_TOTAL
        ]
        if not eligible:
            return None, cursor
        highest_q = max(float(getattr(neuron, "_q", 0.0))
                        for neuron in eligible)
        parent = next(
            neuron for neuron in eligible
            if float(getattr(neuron, "_q", 0.0)) == highest_q
        )
        return parent, (neurons.index(parent) + 1) % len(neurons)

    def _spawn_causal_daughter(self, tag, parent, claim_id):
        """Divide one real neuron from its own full structural state."""
        hemi = self._hemi(tag)
        overflow = parent.compute_overflow_signal()
        params = derive_daughter_parameters(overflow, parent)
        daughter_id = hemi.cluster.next_id()
        daughter = LoomNeuron(
            daughter_id,
            birth_params=params,
            primary_modality=hemi.cluster.primary_modality,
            observable=hemi.cluster.observable,
        )
        daughter._q = 0.0
        daughter._aff_gain = float(getattr(parent, "_aff_gain", 1.0))
        daughter._polarity = getattr(parent, "_polarity", 1.0)
        hemi.cluster.attach(daughter, inherit_from=parent)
        q_at_fold = float(getattr(parent, "_q", 0.0))
        parent._q = 0.0
        self._total_divisions = getattr(self, "_total_divisions", 0) + 1
        if not hasattr(self, "_fold_events_buffer"):
            self._fold_events_buffer = []
        event = {
            "cause": "exact_causal_experience",
            "causal_growth_claim_id": claim_id,
            "daughter": daughter_id,
            "division_energy_at_fold": "1/1",
            "hemi": tag,
            "parent": parent.neuron_id,
            "q_at_fold": round(q_at_fold, 4),
            "tick": self.tick,
        }
        self._fold_events_buffer.append(event)
        return event

    def apply_causal_growth_claim(self, claim):
        """Apply one verified journal claim exactly once on the organism writer.

        One novel causal experience contributes one conserved division-energy
        unit, equipartitioned across the mechanisms that actually participated.
        Rational reservoirs make the settlement independent of method-call
        order.  A division still requires a neuron with real structural state
        and unsaturated physical coupling; otherwise its energy remains stored.
        """
        from dsf_ai_service.substrate.causal_organism_growth import (
            CAUSAL_GROWTH_ORGAN_ORDER,
            CausalOrganismGrowthClaim,
        )

        if not isinstance(claim, CausalOrganismGrowthClaim):
            raise TypeError("organism growth requires a typed causal claim")
        organ_order, reservoirs, cursors, organ_cursor, applied = (
            self._causal_growth_state()
        )
        if organ_order != CAUSAL_GROWTH_ORGAN_ORDER:
            raise RuntimeError("organism and causal growth organ order differ")
        if claim.claim_id in applied:
            return {
                "applied": False,
                "claim_id": claim.claim_id,
                "folds": (),
                "reason": "already_applied",
            }
        if not claim.contributes_division_energy:
            raise ValueError(
                "a recurrent causal observation cannot enter growth journal"
            )
        if (
            not claim.active_organs
            or any(tag not in organ_order for tag in claim.active_organs)
            or claim.active_organs
            != tuple(tag for tag in organ_order if tag in claim.active_organs)
        ):
            raise ValueError("causal growth claim organ order changed")

        total_now = sum(
            len(hemi.cluster.neurons) for hemi in self.brain.hemispheres
        )
        total_divisions = getattr(self, "_total_divisions", 0)
        population_delta = total_now - self._N_initial
        if population_delta != total_divisions:
            raise RuntimeError(
                "organism population and lifetime division count diverged"
            )
        remaining_divisions = max(0, self._N_initial - total_divisions)
        stored = sum(reservoirs.values(), Fraction(0, 1))
        if stored > remaining_divisions:
            raise RuntimeError("causal growth stored energy exceeds lifetime budget")
        available_storage = Fraction(remaining_divisions, 1) - stored
        contribution = min(Fraction(1, 1), available_storage)
        if contribution > 0:
            share = contribution / len(claim.active_organs)
            for tag in claim.active_organs:
                reservoirs[tag] += share

        folds = []
        max_total = min(
            self._max_total_neurons(),
            2 * self._N_initial,
        )
        while remaining_divisions > 0 and total_now < max_total:
            ready = [
                tag for tag in claim.active_organs
                if reservoirs[tag] >= 1
            ]
            candidates = []
            for tag in ready:
                parent, next_cursor = self._select_causal_growth_parent(
                    tag,
                    cursors[tag],
                )
                if parent is not None:
                    tag_index = organ_order.index(tag)
                    cyclic_distance = (
                        tag_index - organ_cursor
                    ) % len(organ_order)
                    candidates.append((
                        len(self._hemi(tag).cluster.neurons),
                        cyclic_distance,
                        tag,
                        parent,
                        next_cursor,
                    ))
            if not candidates:
                break
            _population, _distance, tag, parent, next_cursor = min(
                candidates,
                key=lambda value: (value[0], value[1]),
            )
            folds.append(
                self._spawn_causal_daughter(tag, parent, claim.claim_id)
            )
            reservoirs[tag] -= 1
            cursors[tag] = next_cursor
            organ_cursor = (organ_order.index(tag) + 1) % len(organ_order)
            remaining_divisions -= 1
            total_now += 1

        if total_now >= max_total and any(value >= 1 for value in reservoirs.values()):
            self._growth_cap_hits = getattr(self, "_growth_cap_hits", 0) + 1
            print(
                "[embryo] GROWTH CAP HIT: "
                f"total neurons {total_now} >= bounded maximum {max_total}",
                flush=True,
            )
        self._store_causal_growth_reservoirs(reservoirs)
        self._causal_growth_parent_cursors = cursors
        self._causal_growth_organ_cursor = organ_cursor
        applied.append(claim.claim_id)
        self.tick += 1
        return {
            "applied": True,
            "claim_id": claim.claim_id,
            "contributed_energy": (
                f"{contribution.numerator}/{contribution.denominator}"
            ),
            "folds": tuple(folds),
            "remaining_lifetime_divisions": max(
                0,
                self._N_initial - getattr(self, "_total_divisions", 0),
            ),
        }

    def causal_growth_checkpoint_claim_ids(self):
        self._causal_growth_state()
        return tuple(self._causal_growth_applied_claims)

    def clear_causal_growth_checkpoint_claims(self, expected_claim_ids):
        current = self.causal_growth_checkpoint_claim_ids()
        expected = tuple(expected_claim_ids)
        if current[:len(expected)] != expected:
            raise ValueError("causal growth checkpoint claims changed")
        self._causal_growth_applied_claims = list(current[len(expected):])

    def _charge_and_fold(self, hemi, coherent, quantum):
        """Retired legacy entry point.

        Word-order spectral charge is not causal growth authority.  Live
        division now enters only through ``apply_causal_growth_claim``.
        """
        raise RuntimeError(
            "legacy spectral charge-and-fold is retired; "
            "an exact causal growth claim is required"
        )

    def pop_fold_events(self):
        """Drain and return fold events accumulated since the last call.
        GL-CMD-GROWTH-TRUTH-EVE-20260705-198 P3b."""
        events = getattr(self, "_fold_events_buffer", [])
        self._fold_events_buffer = []
        return events

    def growth_snapshot(self):
        """Report real population and exact causal plasticity reservoirs."""
        _order, reservoirs, _cursors, _organ_cursor, applied = (
            self._causal_growth_state()
        )
        per_hemisphere = {}
        q_over_0_5 = 0
        q_over_0_9 = 0
        for h in self.brain.hemispheres:
            tag = h._op_tag
            per_hemisphere[tag] = len(h.cluster.neurons)
            for n in h.cluster.neurons:
                q = getattr(n, "_q", 0.0)
                if q > 0.9:
                    q_over_0_9 += 1
                if q > 0.5:
                    q_over_0_5 += 1
        return {
            "per_hemisphere": per_hemisphere,
            "total_neurons": sum(per_hemisphere.values()),
            "n_initial": self._N_initial,
            "total_divisions": getattr(self, "_total_divisions", 0),
            "division_pool": round(
                float(sum(reservoirs.values(), Fraction(0, 1))),
                4,
            ),
            "causal_growth_reservoirs": {
                tag: f"{value.numerator}/{value.denominator}"
                for tag, value in reservoirs.items()
            },
            "causal_growth_uncheckpointed_claims": len(applied),
            "remaining_lifetime_divisions": max(
                0,
                self._N_initial - getattr(self, "_total_divisions", 0),
            ),
            "n_q_over_0_5": q_over_0_5,
            "n_q_over_0_9": q_over_0_9,
            # GL-FIX-GROWTH-POOL-LAW-20260716: hard-cap telemetry (0 unless
            # the GUALA_MAX_TOTAL_NEURONS ceiling ever blocked a division).
            "growth_cap_hits": getattr(self, "_growth_cap_hits", 0),
            "max_total_neurons": self._max_total_neurons(),
        }

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
            hemi.cluster.step(list(signal), self.tick)
            self.tick += 1
        # The signal still reaches every real neuron and updates its native
        # krimelack/DSF state.  Population division is intentionally absent:
        # a waveform or word queue item is not a committed causal-experience
        # authority.  The durable causal-growth journal is the only live
        # division entrance.
        return 0

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
        return self._experience_core(composite, theta)

    def experience_word(self, concept, multi_modal_signals, theta=0.05):
        """Drive the organism only from co-occurring numeric sensory fields.

        ``concept`` remains a shell compatibility argument and has no
        neuronal storage, routing, identity, or growth authority.  Only the
        supplied visual, auditory, tactile, olfactory, and gustatory signals
        enter the physical organism.
        """
        # A label is not a sensory cause and is not stored in the neurons.
        del concept

        parts = []
        for m in ("visual", "auditory", "tactile", "olfactory", "gustatory"):
            v = multi_modal_signals.get(m)
            if v is not None:
                parts.append(np.asarray(v, dtype=float))
        composite = np.concatenate(parts) if parts else np.zeros(1)
        return self._experience_core(composite, theta)

    def _experience_core(self, composite, theta):
        """Process a real signal without granting it division authority.

        The krimelacks, neurons, organ routing, and affect remain active.
        Growth is settled separately from an authenticated exact causal
        experience, so queue order and a reduced spectral signature cannot
        decide which organ receives neurons.
        """
        sig_res, _spectral_signature = resonance_and_signature(composite)
        theta_eff = theta

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

        # 2b. gp bootstrap: goals are persistent attractors.  This processes
        # the same real echo but cannot divide from a label or queue item.
        if active.get("em"):
            gp_folds = self._feed_and_fold(self._hemi("gp"), echo * 0.5, sig_res,
                                           theta_eff, quantum_scale=0.2)   # slow integrator
            folds["gp"] = gp_folds
            active["gp"] = sig_res > theta_eff

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

    # GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711: not tuned to
    # any corpus -- 50 ticks is simply "not every word" (remember() advances
    # self.tick by exactly one per word, so a snapshot every word would be
    # both wasteful and would make "then" and "now" nearly always identical,
    # defeating the point of a THEN-vs-NOW comparison); 20 kept snapshots at
    # that interval covers 1000 ticks of real history at any moment, bounded,
    # same "keep a short real window, not the whole lifetime" discipline
    # REFLECTION_MAX_HISTORY already uses for the v5-engine's own
    # `_reflections` deque (gualaloom_v5_engine.py).
    REFLECTION_SNAPSHOT_INTERVAL = 50
    REFLECTION_HISTORY_MAXLEN = 20

    def remember(self, concept, signals):
        """Advance one unlabeled physical population moment.

        The legacy name is retained for the engine shell. The supplied label
        has no neuronal authority; only numeric sensory lanes are presented.
        """
        del concept
        parts = []
        for modality in (
            "visual",
            "auditory",
            "tactile",
            "olfactory",
            "gustatory",
        ):
            signal = signals.get(modality)
            if signal is not None:
                parts.append(np.asarray(signal, dtype=float).reshape(-1))
        composite = np.concatenate(parts) if parts else np.zeros(1)
        result = self.brain.step(composite, self.tick)
        self.tick += 1
        if self.tick % self.REFLECTION_SNAPSHOT_INTERVAL == 0:
            self._reflect_snapshot()
            self._apply_homeostatic_scaling_pass()
        return result

    # GL-CMD-LOOM-HOMEOSTATIC-SCALING: population-level driver for
    # LoomNeuron.apply_homeostatic_scaling() -- see neuron.py's
    # HOMEOSTATIC_SCALING_CEILING module comment for the full safety
    # reasoning (multiplicative-decrease-only, derived ceiling, same
    # _neuron_lock discipline as every other mutator of
    # _incoming_synapse_weights).
    def _apply_homeostatic_scaling_pass(self) -> None:
        """Kill switch: HOMEOSTATIC_SCALING_ENABLED, default OFF ("0"),
        read live on every call -- same live-read, opt-in-only convention
        as gualaloom_v5_engine.py's WAVE_ATLAS_DECAY_ENABLED. Nothing in
        this subsystem goes live-by-default. With the switch OFF (the
        current default, and the only state this ships in), this method
        returns immediately and touches nothing -- zero behavior change
        from before this addition.

        Called only from remember()'s existing REFLECTION_SNAPSHOT_INTERVAL
        tick-modulo hook -- the same call site _reflect_snapshot() already
        uses, at most once every 50 real experiences. NOT called from
        gualaloom_v5_engine.py, _fire(), receive_spike(), or anywhere else
        on the spike-bus hot path.

        Snapshots hemispheres and each cluster's neuron list with list()
        before iterating (the WaveAtlas v3 lesson: never iterate a
        population/dict that could be mutated concurrently without
        snapshotting first) -- defensive, since folding division
        (_charge_and_fold above) can grow a cluster's neuron list between
        ticks. Per-neuron weight-dict safety is handled inside
        LoomNeuron.apply_homeostatic_scaling() itself (same _neuron_lock
        every STDP mutator already uses).
        """
        if os.environ.get("HOMEOSTATIC_SCALING_ENABLED", "0") != "1":
            return
        for h in list(self.brain.hemispheres):
            for n in list(h.cluster.neurons):
                n.apply_homeostatic_scaling()

    def _reflect_snapshot(self) -> None:
        """Append a real (tick, sf_sense()) reading to the bounded reflection
        history. sf_sense() is already real, already computed, already live
        (the test harness's gauge_meta_monitoring reads it every checkpoint)
        -- the only piece that was missing was KEEPING a bounded history of
        it so a later moment can compare against an earlier one. Self-heals
        the attribute (same getattr/backfill pattern -198 already
        established for _fold_events_buffer/_total_divisions) so a real
        organism pickled before this dispatch restores and keeps working --
        it just starts its reflection history from whenever this first
        runs, honestly, rather than crashing or fabricating a backfilled
        past it never actually experienced."""
        if not hasattr(self, "_reflection_snapshots"):
            from collections import deque
            self._reflection_snapshots = deque(maxlen=self.REFLECTION_HISTORY_MAXLEN)
        self._reflection_snapshots.append((int(self.tick), self.sf_sense()))

    def reflect(self, against: str = "oldest"):
        """Real self-state-then-vs-now reflection -- §4a of GL-RPT-BRAIN-
        IMAGINATION-REFLECTION-DESIGN-C1-20260711-v1, built for real this
        time. Compares the CURRENT sf_sense() reading against a real,
        previously-recorded snapshot from this organism's own bounded
        history (_reflect_snapshot(), called periodically from remember()).

        `against`: "oldest" (default -- the longest-range comparison still
        held, i.e. as far back as the bounded history reaches) or "latest"
        (the most recent snapshot before now -- the shortest-range, most
        sensitive comparison).

        Returns None (not a fabricated zero-baseline) if no snapshot has
        been taken yet -- an honest "nothing to reflect on yet."

        This is structurally the SAME move the v5-engine's own
        _form_reflection already makes (then vs. now) -- just over the
        organism's own introspectable axis (arousal / population / per-
        organ binding strength, sf_sense()'s own real fields) instead of
        external episodic affect. A distinct, organism-native signal, not
        a renamed copy of the v5-engine's mechanism (per §3 of the design
        doc)."""
        history = getattr(self, "_reflection_snapshots", None)
        if not history:
            return None
        if against == "latest":
            then_tick, then_vec = history[-1]
        else:
            then_tick, then_vec = history[0]
        now_tick = int(self.tick)
        now_vec = self.sf_sense()
        delta = now_vec - then_vec
        field_names = ["arousal", "pop_mean", "pop_max"] + [t for t, _ in OPERATIONS]
        per_field = {
            name: {"then": float(then_vec[i]), "now": float(now_vec[i]),
                   "delta": float(delta[i])}
            for i, name in enumerate(field_names)
        }
        return {
            "against": against,
            "tick_then": then_tick,
            "tick_now": now_tick,
            "ticks_elapsed": now_tick - then_tick,
            "delta_norm": float(np.linalg.norm(delta)),
            "per_field": per_field,
        }

    def imagine(self, op_tag: str = "sc", top_k: int = 5, max_concepts: int = 200):
        """No per-neuron label association is available for imagination."""
        del op_tag, top_k, max_concepts
        return []

    def recall(self, signals):
        """Return no label vote; causal mosaics own learned recognition."""
        from collections import Counter
        del signals
        return Counter()

    def recall_fast(self, signals):
        """Return no label vote; causal mosaics own learned recognition."""
        return self.recall(signals)

    def _sc_proj(self, neuron, dim):
        del neuron, dim
        raise RuntimeError("retired per-neuron semantic projection")

    def _sc_encode(self, neuron, profile):
        del neuron, profile
        raise RuntimeError("retired per-neuron semantic encoding")

    def recall_op(self, op_tag, signals, profile=None):
        from collections import Counter
        del op_tag, signals, profile
        return Counter()

    def sc_learn(self, concept, profile):
        del concept, profile
        raise RuntimeError("retired per-neuron semantic binding")

    # --- state / regulation operations (primitive, grow later) ---
    def sv_anchor(self, identity="guala"):
        """Record the explicit organism name without projecting it into neurons."""
        self._identity = identity

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
        """Refuse the lossy legacy dictionary format."""
        raise RuntimeError(
            "portable loom-seed-v1 persistence is retired; "
            "use save_full_state()"
        )

    # --- full-fidelity organism persistence ---
    # The retired dictionary persistence cannot represent the physical
    # organism. save_full_state/load_full_state instead preserve the
    # ENTIRE registered structural graph — every neuron actually present (including
    # divisions), each one's DNA/charge/couplings, cross-hemi consensus,
    # arousal, division pool, tick, and identity_uuid — so restore is
    # bit-honest by construction. The closed durable-field registry rejects
    # any newly introduced field until its persistence authority is explicit;
    # runtime threads, locks, and callbacks are rebuilt after restore.
    def save_full_state(self, path, *, persistence_admission=None):
        """Persist the exact organism through the bounded graph boundary."""
        from dsf_ai_service.loom_model.structural_graph_state import (
            save_structural_graph,
            structural_graph_limits_from_environment,
        )
        return save_structural_graph(
            self,
            path,
            limits=structural_graph_limits_from_environment(),
            persistence_admission=persistence_admission,
        )

    @staticmethod
    def load_full_state(path):
        from dsf_ai_service.loom_model.structural_graph_state import (
            load_structural_graph,
            structural_graph_limits_from_environment,
        )
        return load_structural_graph(
            path,
            expected_root_type=Embryo,
            limits=structural_graph_limits_from_environment(),
        )

    @staticmethod
    def load_legacy_pickle_state(path):
        """Read one authenticated pre-graph generation for migration only."""
        import gzip
        import pickle
        with gzip.open(path, "rb") as source:
            restored = pickle.load(source)
        if not isinstance(restored, Embryo):
            raise TypeError("legacy organism state restored an unexpected type")
        return restored

    @staticmethod
    def load(d):
        del d
        raise RuntimeError(
            "portable loom-seed-v1 persistence is retired; "
            "use load_full_state()"
        )

    def perceive_sequence(self, concepts, pipe):
        """Advance physical sensory experience without assigning labels."""
        sigs = [pipe._build_multi_modal_signals(c) for c in concepts]
        for concept, signals in zip(concepts, sigs):
            self.experience_word(concept, signals)
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


if __name__ == "__main__":
    main()
