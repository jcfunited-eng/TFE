"""native_core.py -- opt-in native (Rust) kernel swap for the organism hot path.

GL native-core track, 2026-07-16. Build-time fallback module, NOT a cognition
dual-path: `import guala_core` (the PyO3 crate at native/guala_core/) if the
wheel is installed, else everything stays pure-Python. NOTHING here runs
unless a caller explicitly invokes install() -- importing this module changes
no behavior, and no production file imports it. The kernels are exact ports
(same operation order, same event semantics) verified by
native/guala_core/tests/test_differential.py.

What install() swaps (the profile-verified hot kernels of
organism.experience_word / neuron.step, per tools/bench_organism_core.py):

  - v4 Krimelack.feed            -> guala_core.krim_feed
  - v4 Krimelack.fingerprint     -> guala_core.fingerprint
  - LanguageKrimelack.transduce  -> guala_core.lang_transduce (+ fingerprint)
  - substrate Krimelack.feed_signal -> guala_core.krim_feed
  - CochlearBankKrimelack.feed_signal -> guala_core.cochlear_feed
  - VisualKrimelack.feed_signal  -> guala_core.fovea_feed
  - uf_kernel.compute_dsf        -> guala_core.compute_dsf (all import sites)
  - neuron._map_inject           -> guala_core.map_inject
  - PsiLattice.settle            -> guala_core.psi_settle

All Python-side object state (event deques, winding counters, pickle shape)
stays exactly where it was -- the kernels are pure functions; wrappers write
the results back to the same attributes the Python code mutates. The Rust
side releases the GIL for every kernel loop and holds no lock and no shared
state of any kind (lock-free by construction).

uninstall() restores the originals (used by the differential tests).
"""

from __future__ import annotations

import numpy as np

try:
    import guala_core as _gc
    HAVE_NATIVE = True
except ImportError:  # build-time fallback: pure Python everywhere
    _gc = None
    HAVE_NATIVE = False

_installed = False
_originals: dict = {}


def is_installed() -> bool:
    return _installed


def _as_list(signal):
    if hasattr(signal, "tolist"):
        return signal.tolist()
    if isinstance(signal, list):
        return signal
    return list(signal)


def _events_to_dicts(events):
    return [{"t": t, "dw": dw, "s": s} for (t, dw, s) in events]


# ---------------------------------------------------------------------------
# wrappers (bound as methods / functions by install())
# ---------------------------------------------------------------------------

def _v4_feed(self, signal_array):
    """Native twin of gualaloom_v4_krimelack_dna.Krimelack.feed, including
    its n_events pickle-compat self-heal."""
    if not hasattr(self, "n_events"):
        self.n_events = 0
    phase, t, winding, n_events, events = _gc.krim_feed(
        self.phase, self.t, self.winding, self.n_events,
        self.omega_0, self.kappa, self.dt, self.threshold,
        _as_list(signal_array))
    self.phase = phase
    self.t = t
    self.winding = winding
    self.n_events = n_events
    ev = self.events  # deque(maxlen=...) -- append preserves eviction
    for tup in events:
        ev.append({"t": tup[0], "dw": tup[1], "s": tup[2]})


def _v4_fingerprint(self):
    """Native twin of v4 Krimelack.fingerprint."""
    ev = self.events
    if len(ev) == 0:
        return (0, 0, 0.0, 0, 0, 0, 0)
    ts = [e["t"] for e in ev]
    ss = [e["s"] for e in ev]
    return _gc.fingerprint(ts, ss, self.winding)


def _lang_transduce(self, word, omega_override=None, phase_offset=0.0,
                    no_reset=False):
    """Native twin of LanguageKrimelack.transduce. Same semantics:
    last_input_word set first; reset unless no_reset; phase starts at
    phase_offset; omega_0 temporarily overridden (mathematically inert --
    dphi = (omega - omega_0)*dt -- but preserved for exactness); fingerprint
    over the full (possibly accumulated) event deque; ROLE/SENSORY DNA
    lookups unchanged."""
    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as _kdna
    wl = word.lower()
    self.last_input_word = wl
    if not no_reset:
        self.reset()
    if not hasattr(self, "n_events"):
        self.n_events = 0
    omega_eff = float(omega_override) if omega_override is not None else self.omega_0
    phase, t, winding, n_events, events = _gc.lang_transduce(
        wl, float(phase_offset), self.t, self.winding, self.n_events,
        omega_eff, self.kappa, self.dt, self.threshold)
    self.phase = phase
    self.t = t
    self.winding = winding
    self.n_events = n_events
    ev = self.events
    for tup in events:
        ev.append({"t": tup[0], "dw": tup[1], "s": tup[2]})
    fp = self.fingerprint()
    role = _kdna.ROLE_DNA.get(wl, "unknown")
    senses = _kdna.SENSORY_DNA.get(wl, {})
    return fp, role, senses


def _substrate_feed_signal(self, signal_array):
    """Native twin of substrate.krimelack.Krimelack.feed_signal (events is a
    plain list on this class; no n_events attribute exists -- not added)."""
    phase, t, winding, _n, events = _gc.krim_feed(
        self.phase, self.t, self.winding, 0,
        self.omega_0, self.kappa, self.dt, self.threshold,
        _as_list(signal_array))
    self.phase = phase
    self.t = t
    self.winding = winding
    self.events.extend(_events_to_dicts(events))


def _cochlear_feed_signal(self, signal):
    """Native twin of substrate_dna.CochlearBankKrimelack.feed_signal:
    6 fixed bands x (biquad + normalize + fresh krimelack), stable t-sort."""
    arr = np.asarray(signal, dtype=np.float64)
    total_winding, events = _gc.cochlear_feed(arr.tolist())
    all_events = _events_to_dicts(events)
    self.events = all_events
    self._n_events += len(all_events)
    self.winding += total_winding
    self._phase = float(self.winding) * 0.1


def _visual_feed_signal(self, signal):
    """Native twin of substrate_dna.VisualKrimelack.feed_signal: fovea tick
    loop with t = i*VIS_DT per feed; fovea events accumulate across feeds;
    self.events mirrors the fovea's FULL history (existing semantics)."""
    from dsf_ai_service.loom_model.substrate_dna import VIS_DT
    arr = np.asarray(signal, dtype=np.float64).ravel()
    f = self._fovea
    phase, winding, adapt, events = _gc.fovea_feed(
        f.phase, f.winding_count, f.adapt_state, arr.tolist(),
        f.omega_0, f.kappa_max, f.adapt_tau, f.recover_tau, VIS_DT)
    f.phase = phase
    f.winding_count = winding
    f.adapt_state = adapt
    f.events.extend(_events_to_dicts(events))
    self.events = list(f.events)
    self._n_events += len(self.events)
    self.winding = f.winding_count
    self._phase = float(self.winding) * 0.1


def _compute_dsf(events, atlas_similarity=0.0, recall_match=0.0):
    """Native twin of gualaloom_v4_uf_kernel.compute_dsf. Returns the same
    DSF dataclass (Python-side), fields computed natively."""
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    n = len(events)
    if n == 0:
        return DSF(0, 0, 0, 1, 0, 0, 0, 0)
    ts = [e["t"] for e in events]
    dws = [float(e["dw"]) for e in events]
    ss = [e["s"] for e in events]
    vals = _gc.compute_dsf(ts, dws, ss, float(atlas_similarity))
    return DSF(*vals)


def _map_inject(dsf, chi, dim=None, sigma=None):
    from dsf_ai_service.loom_model import neuron as _neuron
    if dim is None:
        dim = _neuron.PSI_DIM
    if sigma is None:
        sigma = _neuron.INJECT_SIGMA
    return np.asarray(_gc.map_inject(int(chi), float(dsf.B_k), int(dim),
                                     float(sigma)), dtype=np.float64)


def _psi_settle(self, injection_vector, law_fields, n_steps=None, eps=None):
    from dsf_ai_service.loom_model import neuron as _neuron
    if n_steps is None:
        n_steps = _neuron.SETTLE_STEPS
    if eps is None:
        eps = _neuron.SETTLE_EPS
    law_weights = [float(w) for (w, fam) in law_fields
                   if fam in ("symmetry.basic", "consistency.basic")]
    psi = _gc.psi_settle(self.psi.tolist(), _as_list(injection_vector),
                         law_weights, int(n_steps), float(eps))
    self.psi = np.asarray(psi, dtype=np.complex128)
    return self.psi


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------

def install() -> bool:
    """Swap the native kernels in. Returns True if active. Explicit opt-in:
    nothing anywhere calls this by default."""
    global _installed
    if not HAVE_NATIVE:
        return False
    if _installed:
        return True

    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as kdna
    from dsf_ai_service.v4 import gualaloom_v4_uf_kernel as ufk
    from dsf_ai_service.substrate import krimelack as skrim
    from dsf_ai_service.loom_model import substrate_dna as sdna
    from dsf_ai_service.loom_model import neuron as neuron_mod
    from dsf_ai_service.substrate import language_fact_strand as lfs

    _originals["v4_feed"] = kdna.Krimelack.feed
    _originals["v4_fingerprint"] = kdna.Krimelack.fingerprint
    _originals["lang_transduce"] = kdna.LanguageKrimelack.transduce
    _originals["substrate_feed_signal"] = skrim.Krimelack.feed_signal
    _originals["cochlear_feed_signal"] = sdna.CochlearBankKrimelack.feed_signal
    _originals["visual_feed_signal"] = sdna.VisualKrimelack.feed_signal
    _originals["ufk_compute_dsf"] = ufk.compute_dsf
    _originals["neuron_compute_dsf"] = neuron_mod.compute_dsf
    _originals["sdna_compute_dsf"] = sdna.compute_dsf
    _originals["lfs_compute_dsf"] = lfs.compute_dsf
    _originals["map_inject"] = neuron_mod._map_inject
    _originals["psi_settle"] = neuron_mod.PsiLattice.settle

    kdna.Krimelack.feed = _v4_feed
    kdna.Krimelack.fingerprint = _v4_fingerprint
    kdna.LanguageKrimelack.transduce = _lang_transduce
    skrim.Krimelack.feed_signal = _substrate_feed_signal
    sdna.CochlearBankKrimelack.feed_signal = _cochlear_feed_signal
    sdna.VisualKrimelack.feed_signal = _visual_feed_signal
    ufk.compute_dsf = _compute_dsf
    neuron_mod.compute_dsf = _compute_dsf
    sdna.compute_dsf = _compute_dsf
    lfs.compute_dsf = _compute_dsf
    neuron_mod._map_inject = _map_inject
    neuron_mod.PsiLattice.settle = _psi_settle

    _installed = True
    return True


def uninstall() -> None:
    """Restore the pure-Python originals (differential-test helper)."""
    global _installed
    if not _installed:
        return

    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as kdna
    from dsf_ai_service.v4 import gualaloom_v4_uf_kernel as ufk
    from dsf_ai_service.substrate import krimelack as skrim
    from dsf_ai_service.loom_model import substrate_dna as sdna
    from dsf_ai_service.loom_model import neuron as neuron_mod
    from dsf_ai_service.substrate import language_fact_strand as lfs

    kdna.Krimelack.feed = _originals["v4_feed"]
    kdna.Krimelack.fingerprint = _originals["v4_fingerprint"]
    kdna.LanguageKrimelack.transduce = _originals["lang_transduce"]
    skrim.Krimelack.feed_signal = _originals["substrate_feed_signal"]
    sdna.CochlearBankKrimelack.feed_signal = _originals["cochlear_feed_signal"]
    sdna.VisualKrimelack.feed_signal = _originals["visual_feed_signal"]
    ufk.compute_dsf = _originals["ufk_compute_dsf"]
    neuron_mod.compute_dsf = _originals["neuron_compute_dsf"]
    sdna.compute_dsf = _originals["sdna_compute_dsf"]
    lfs.compute_dsf = _originals["lfs_compute_dsf"]
    neuron_mod._map_inject = _originals["map_inject"]
    neuron_mod.PsiLattice.settle = _originals["psi_settle"]

    _installed = False
