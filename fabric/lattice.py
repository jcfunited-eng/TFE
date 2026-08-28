"""THE LATTICE FORM — the same physics a crystal would do.

A loop that checks candidates one at a time cannot be poured into
glass. A crystal does one thing: light enters, meets every stored
pattern at once, and what matches comes back bright while what
does not cancels. So the engine has to be written that way here,
in the same mathematics, so the step to a lattice is a change of
substrate and not a change of method.

  a word          -> a phase pattern (a grating)
  an entry        -> the sum of its words' patterns
  a candidate     -> the superposition of its entries
  a law           -> a stored pattern to resonate against
  judging         -> ONE product: every candidate against every
                     law at once. In glass this is one pass of
                     light; here it is one matrix multiply.

Resonance above threshold means the law's condition is present in
the candidate — the law grips, and the candidate goes dark. What
stays bright is what survives. Same answers as the sequential
engine; a form that a lattice can hold.
"""
import os, sys, hashlib
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

D = 256          # lattice dimension (gratings per pattern)

def _phase(word):
    h = hashlib.sha256(word.encode()).digest()
    seed = int.from_bytes(h[:8], "big") % (2**32)
    rng = np.random.default_rng(seed)
    return np.exp(1j * rng.uniform(0, 2*np.pi, D)) / np.sqrt(D)

_cache = {}
def pattern(words):
    v = np.zeros(D, dtype=complex)
    for w in words:
        if w not in _cache: _cache[w] = _phase(w)
        v += _cache[w]
    return v

def law_patterns(req, forb):
    pats, kinds = [], []
    for a, b, e, txt in forb:
        pats.append(pattern(a | b)); kinds.append(("forbids", a, b, e, txt))
    for a, b, e, txt in req:
        pats.append(pattern(a)); kinds.append(("requires", a, b, e, txt))
    return np.array(pats), kinds

def scan(candidate_wordsets, req, forb):
    """One pass: every candidate against every law simultaneously."""
    C = np.array([pattern(ws) for ws in candidate_wordsets])
    L, kinds = law_patterns(req, forb)
    # the interference: each candidate meets every stored pattern
    R = np.abs(C @ L.conj().T)          # <- one pass of light
    return R, kinds

def survives(candidate_words, R_row, kinds, thresh):
    for v, (kind, a, b, e, txt) in zip(R_row, kinds):
        if kind == "forbids":
            if v >= thresh * (len(a | b) ** 0.5): return False, txt
        else:
            if v >= thresh * (len(a) ** 0.5) and not (b & candidate_words):
                return False, txt
    return True, None
