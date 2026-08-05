"""injection_weight.py -- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2.

signal_to_injection_weight(input_signal): converts a step()-style
input_signal (word string, or numeric array/list) into a spike-bus
injection weight.
"""

from __future__ import annotations

import numpy as np

# HEURISTIC: WORD_INJECTION_WEIGHT=1.5 -- fixed strength for word (string)
# input, enough to reliably cross membrane_threshold=1.0 on a fresh entry
# neuron without saturating. Class: from-design. Measurement plan: observe
# whether entry neurons reliably fire on injection; adjust if too weak
# (silent substrate, halt condition 5) or so strong every injection
# saturates identically regardless of content (adjust down).
WORD_INJECTION_WEIGHT = 1.5

# HEURISTIC: MAX_INJECTION_WEIGHT=2.0 -- clamp ceiling for numeric-signal
# injection (L2-magnitude-derived). Class: from-design. Measurement plan:
# same as above, applied to the numeric-signal path specifically.
MAX_INJECTION_WEIGHT = 2.0

# GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 3, sensory spike
# injection): minimum injection weight -- the signal-strength FLOOR an
# injection must clear before any spike is emitted. The 2026-07-09
# incident (one entry neuron per hemisphere kicked continuously, 14M+
# fires at 3792/sec, zero synapses updated) was driven by float-dust wave
# residue that never reached exactly zero; the WaveAtlas zero-clamp fixes
# the source, and this floor fixes the sink: silence and near-silence
# inject NOTHING. 0.01 sits two orders of magnitude below a real signal
# (a modest genuine band signal like [0.1..0.4] yields ~0.27 normalized
# L2; a real word injects at WORD_INJECTION_WEIGHT=1.5) and three orders
# above the decay clamp epsilon (1e-6) -- residue can't reach it, real
# signals can't miss it. Class: from-design. Measurement plan: watch
# fires-with-zero-synapse-updates in /debug/stdp_state stay flat while
# real word/sense traffic still produces entry-neuron fires.
SPIKE_INJECTION_MIN_WEIGHT = 0.01


def signal_to_injection_weight(input_signal) -> float:
    """Word (string) input: fixed WORD_INJECTION_WEIGHT -- identity is
    conveyed by WHICH neurons get injected (chi-proximity/word-neuron
    lookup), not by injection magnitude. Numeric (array-like) input:
    normalized L2 magnitude, clamped to [0, MAX_INJECTION_WEIGHT]."""
    if isinstance(input_signal, str):
        return WORD_INJECTION_WEIGHT
    arr = np.asarray(input_signal, dtype=float)
    if arr.size == 0:
        return 0.0
    magnitude = float(np.linalg.norm(arr) / np.sqrt(arr.size))
    return max(0.0, min(magnitude, MAX_INJECTION_WEIGHT))
