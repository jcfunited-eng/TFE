"""
GUALALOOM-SENSES-WC-2026-06-05
Five modal krimelack channels — oscillator transduction for sensory input.

Each modality gets its own oscillator krimelack (same class, different tuning).
The oscillator eats a sensory signal vector and produces winding events.
Those events are converted to a settled trit state compatible with the
engine's motif memory, so modal sections use the same commit/recall/chi
infrastructure as the word section.

Signal path:
  sensory dict → float vector → oscillator → events → trit state → commit
"""

import math
import numpy as np
from collections import defaultdict, deque

# Physical channel topology belongs to the receptor adapter, not to the
# retired hand-authored word-to-sense corpus.
MODALITY_COMPONENTS = {
    "sight": (
        "hue", "saturation", "lightness",
        "edge_density", "motion", "shape_signature",
    ),
    "sound": (
        "spectral_centroid", "spectral_bandwidth", "attack",
        "decay", "harmonicity", "loudness",
    ),
    "smell": (
        "sweet", "putrid", "floral", "fruity",
        "smoky", "earthy", "sour", "fresh",
    ),
    "taste": (
        "sweet", "sour", "bitter", "salty", "umami", "intensity",
    ),
    "touch": (
        "pressure", "temperature", "vibration",
        "texture_freq", "sharpness", "wetness",
    ),
}
MODALITIES = tuple(MODALITY_COMPONENTS)

# GL-CMD-SENSE-REPAIR: cap per-krimelack event history, same bound and same
# reason as gualaloom_v4_krimelack_dna.py's language path (GL-CMD-138):
# unbounded accumulation under no-reset cognition-path teaching is a real
# memory risk. n_events (below) is the separate, never-reset monotonic
# counter that survives eviction from this bounded buffer.
_EVENTS_MAXLEN = 256


# ── Oscillator Krimelack (from krimelack_v1.py, inlined to avoid docs/ import) ──

class OscillatorKrimelack:
    """Winding-number oscillator. Same as krimelack_v1.Krimelack."""

    def __init__(self, omega_0=2.0, kappa=80.0, dt=0.04, threshold=None):
        self.omega_0 = omega_0
        self.kappa = kappa
        self.dt = dt
        self.threshold = threshold if threshold is not None else math.pi / 3
        # GL-CMD-SENSE-REPAIR: monotonic event counter, set ONCE here (not in
        # reset()) so it survives reset()/no-reset feeding the same way the
        # language krimelack's n_events was always documented to (the
        # adapters in substrate_dna.py already assumed this existed —
        # `self._inner.n_events if hasattr(self._inner, 'n_events') else 0`
        # always took the `else 0` branch because this line never existed).
        self.n_events = 0
        self.reset()

    def reset(self):
        self.phase = 0.0
        self.t = 0.0
        self.winding = 0
        self.events = deque(maxlen=_EVENTS_MAXLEN)

    def step(self, s_t):
        omega = self.omega_0 + self.kappa * s_t
        delta_phi = (omega - self.omega_0) * self.dt
        self.phase += delta_phi
        self.t += self.dt
        transitions = 0
        while self.phase >= self.threshold:
            self.phase -= self.threshold
            self.winding += 1
            self.events.append({"t": self.t, "dw": +1, "s": s_t})
            self.n_events += 1
            transitions += 1
        while self.phase <= -self.threshold:
            self.phase += self.threshold
            self.winding -= 1
            self.events.append({"t": self.t, "dw": -1, "s": s_t})
            self.n_events += 1
            transitions += 1
        return transitions

    def feed_signal(self, signal_array):
        for s in signal_array:
            self.step(float(s))


# ── Per-modality tuning ──
# Start near text defaults (omega_0=2.0, kappa=80.0, dt=0.04, threshold=π/3).
# Slight variation per modality so different signal structures produce
# different event patterns. Event target: ~50-200 events per modal signal.

MODAL_TUNING = {
    "sight": {"omega_0": 2.0, "kappa": 75.0, "dt": 0.04, "threshold": math.pi / 3},
    "sound": {"omega_0": 2.2, "kappa": 85.0, "dt": 0.04, "threshold": math.pi / 3},
    "smell": {"omega_0": 1.8, "kappa": 70.0, "dt": 0.045, "threshold": math.pi / 3.5},
    "taste": {"omega_0": 2.0, "kappa": 90.0, "dt": 0.04, "threshold": math.pi / 3},
    "touch": {"omega_0": 1.9, "kappa": 80.0, "dt": 0.04, "threshold": math.pi / 3},
}

# Samples per component value — interpolated like text_to_signal does for chars
SAMPLES_PER_COMPONENT = 4


# ── Signal construction ──

def sensory_dict_to_signal(modality, component_dict):
    """Convert a modality's component dict to a continuous signal array.

    Components are ordered per MODALITY_COMPONENTS. Missing components
    default to 0. Values are centered to [-1, 1] range (subtract 0.5, scale by 2)
    for compatibility with the oscillator's signal expectation.
    """
    components = MODALITY_COMPONENTS[modality]
    values = []
    for comp in components:
        v = component_dict.get(comp, 0.0)
        values.append((v - 0.5) * 2.0)  # center and scale

    # Interpolate between components (like text_to_signal interpolates between chars)
    sig = []
    for i, v in enumerate(values):
        v_next = values[i + 1] if i + 1 < len(values) else 0.0
        for j in range(SAMPLES_PER_COMPONENT):
            alpha = j / SAMPLES_PER_COMPONENT
            sig.append((1 - alpha) * v + alpha * v_next)
    return np.array(sig)


def transduce_sensory(modality, component_dict):
    """Full transduction: sensory dict → oscillator → events.

    Returns the OscillatorKrimelack instance with events populated.
    """
    tuning = MODAL_TUNING[modality]
    osc = OscillatorKrimelack(**tuning)
    sig = sensory_dict_to_signal(modality, component_dict)
    osc.feed_signal(sig)
    return osc


# ── Event-to-trit conversion ──
# The engine stores motifs as trit tuples of length CONTEXT * TRITS (64).
# We convert oscillator events into a trit state of the same shape so
# modal sections share the same chi/recall/commit infrastructure.

def events_to_trit_state(events, state_len=64):
    """Convert oscillator events to a trit tuple.

    Each event is assigned a position in the trit state based on its
    index modulo state_len. The trit at that position is set to the
    winding direction (+1 or -1). Multiple events at the same position:
    sum directions, then quantize to {-1, 0, +1}.

    If no events, returns all-null (no commitment). This is correct —
    a modality that produces no events contributes nothing.
    """
    if not events:
        return tuple([0] * state_len)

    accum = defaultdict(int)
    for i, ev in enumerate(events):
        pos = i % state_len
        accum[pos] += ev["dw"]

    state = [0] * state_len
    for pos, total in accum.items():
        if total > 0:
            state[pos] = 1
        elif total < 0:
            state[pos] = -1
    return tuple(state)


def transduce_to_trit_state(modality, component_dict, state_len=64):
    """Full path: sensory dict → oscillator → events → trit state.

    Returns (trit_state, n_events). The trit state is ready for
    commit() to the modal section's Krimelack.
    """
    osc = transduce_sensory(modality, component_dict)
    state = events_to_trit_state(osc.events, state_len=state_len)
    return state, len(osc.events)
