"""vectorized_oscillator.py — GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177.

I2 (batch the identical winding-oscillator math across neurons in numpy) +
I1 (peek-mode: read current state, never mutate, so no snapshot/restore is
ever needed) for the recall-only read path.

Physics being replicated exactly (Krimelack.feed / OscillatorKrimelack.step,
gualaloom_v4_krimelack_dna.py + sensory_krimelacks.py):
    omega = omega_0 + kappa * s_t
    dphi  = (omega - omega_0) * dt   =   kappa * s_t * dt      <- omega_0 CANCELS
    phase += dphi
    while phase >=  threshold: phase -= threshold; winding += 1  (event)
    while phase <= -threshold: phase += threshold; winding -= 1  (event)

Two facts this exploits, each verified against the scalar reference in
tests/probe_177_vectorized_parity.py before this is wired into brain.py:

1. dphi depends only on s_t (the sample), never on the neuron's own phase or
   omega_0 (both cancel in the subtraction above) -- so the SEQUENCE of raw
   per-sample increments is identical regardless of any neuron's individual
   accumulated state, and can be computed ONCE per modality per query, then
   scaled per-neuron only by that neuron's attenuation multiplier (a fixed
   scalar). This is what makes cross-neuron batching exact, not approximate.

2. The wrap-and-count step (the nested while loops) is EXACT integer floor
   division per sample: a single sample's dphi can span more than one
   threshold-width (confirmed possible at production kappa/dt/threshold
   values), so this loops over SAMPLES (small: ~20-160 per query) and
   vectorizes across NEURONS (large: population-sized) at each sample --
   the safe direction. Collapsing the sample loop too (a single closed-form
   over the whole feed) was considered and REJECTED: language's per-
   character signal changes sign (vowel/consonant), so a multi-sample
   direction reversal can cross the threshold going up and back down within
   one feed call -- events that a single net-sum-then-wrap shortcut would
   silently cancel out and undercount. Only clean per-sample wrapping (not
   summed first) preserves the exact event count in that case.
"""
import numpy as np

_EVENTS_MAXLEN = 256  # matches gualaloom_v4_krimelack_dna._EVENTS_MAXLEN /
                       # sensory_krimelacks._EVENTS_MAXLEN -- same constant,
                       # both modules define it separately, kept in sync here
                       # by value (not import, to avoid coupling two otherwise
                       # independent modules over one shared literal).


def vectorized_wind_count(base_dphi, threshold, phase0, att):
    """Batch the winding-oscillator physics across neurons.

    Args:
        base_dphi: 1D array, length S. Per-sample s_t*dt (raw signal, NO
                   kappa baked in -- kappa is folded into `att` since it is
                   itself a per-neuron multiplier of the raw signal, and, on
                   this substrate, per-neuron kappa heterogeneity is real
                   (Embryo._seed_dna_diversity mutates each neuron's OWN
                   language krimelack's kappa/threshold by ring position --
                   NOT a shared constant. Confirmed empirically: sensory
                   modalities -- tactile/olfactory/gustatory -- are NOT
                   touched by that method and stay uniform across neurons,
                   so a scalar kappa is fine there; language is not).
        threshold: 1D array, length N. Each neuron's OWN threshold (same
                   per-neuron-heterogeneity reason as kappa above -- do not
                   pass a shared scalar for language).
        phase0:    1D array, length N. Each neuron's starting phase (read,
                   never mutated).
        att:       1D array, length N. Each neuron's per-modality multiplier
                   of the raw signal -- kappa for language (attenuation is
                   proven inert there, see module docstring), attenuation*
                   kappa_shared for sensory modalities (kappa folded in by
                   the caller, or just attenuation if kappa is applied to
                   base_dphi directly -- either decomposition is exact).

    Returns:
        (raw_transitions, final_phase): both 1D arrays, length N.
        raw_transitions = exact count of threshold crossings (in either
        direction) during this feed, per neuron -- matches sum of
        n_events deltas the scalar step()-based reference would produce.
    """
    n = phase0.shape[0]
    threshold = np.broadcast_to(np.asarray(threshold, dtype=np.float64), (n,)).copy()
    phase = phase0.astype(np.float64).copy()
    count = np.zeros(n, dtype=np.int64)
    for s in base_dphi:
        phase = phase + s * att
        pos = phase >= threshold
        if pos.any():
            k = np.floor(phase[pos] / threshold[pos])
            phase[pos] -= k * threshold[pos]
            count[pos] += k.astype(np.int64)
        neg = phase <= -threshold
        if neg.any():
            k = np.floor(-phase[neg] / threshold[neg])
            phase[neg] += k * threshold[neg]
            count[neg] += k.astype(np.int64)
    return count, phase


def language_base_dphi_raw(word):
    """Reproduces LanguageKrimelack.transduce's char->signal mapping exactly
    (gualaloom_v4_krimelack_dna.py LanguageKrimelack.transduce), without
    running the krimelack itself. Pure function of the word string. Returns
    the RAW per-sample signal s_t -- kappa/dt are NOT applied here, since
    kappa is per-neuron (Embryo._seed_dna_diversity), not a shared constant;
    the caller multiplies by each neuron's own kappa*dt via `att`."""
    import math
    vowels = set("aeiouy")
    signal = []
    for i, c in enumerate(word.lower()):
        if c in vowels:
            base = -0.3 + (ord(c) - ord('a')) / 25.0 * 0.5
        elif c.isalpha():
            base = +0.4 + (ord(c) - ord('a')) / 25.0 * 0.4
        else:
            base = 0.0
        for j in range(4):
            s = base + 0.05 * math.sin(i + j * math.pi / 4)
            signal.append(s)
    return np.asarray(signal, dtype=np.float64)


def saturating_new_count(ev0, raw_transitions, maxlen=_EVENTS_MAXLEN):
    """Replicates ev1-ev0 where ev0/ev1 are len(deque(maxlen=...)) reads
    (the LanguageKrimelack path -- no true n_events counter exists on the
    base Krimelack class, see gualaloom_v4_krimelack_dna.py). Once the
    deque is saturated (ev0 == maxlen), appending never changes len(), so
    the delta is exactly 0 regardless of raw_transitions -- this is the
    live, real, already-flagged 'language-dimension saturation' behavior
    (old open thread #1), reproduced exactly here, NOT fixed here."""
    ev0 = np.asarray(ev0, dtype=np.int64)
    ev1 = np.minimum(maxlen, ev0 + raw_transitions)
    return ev1 - ev0


def monotonic_new_count(raw_transitions):
    """Replicates ev1-ev0 where ev0/ev1 are true monotonic n_events counters
    (the tactile/olfactory/gustatory adapters, sensory_krimelacks.py
    OscillatorKrimelack.n_events) -- no saturation, delta == raw count."""
    return raw_transitions
