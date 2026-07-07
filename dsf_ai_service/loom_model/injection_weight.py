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
