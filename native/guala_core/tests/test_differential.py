#!/usr/bin/env python3
"""Differential tests: identical inputs through the pure-Python kernels and
the guala_core (Rust) ports must give identical outputs.

Tolerance policy (documented per kernel):
  - Oscillator loops, biquad filter, DSF statistics, fingerprint, char
    signal: EXACT (bit-equal) -- both sides are plain f64 arithmetic in the
    same operation order, and libm (sin/cos/exp/log10/hypot) resolves to the
    same glibc on this platform.
  - map_inject: <=1e-12 abs (numpy's vectorized exp may round differently
    from scalar libm exp by <1 ulp).
  - psi_settle: <=1e-9 relative (numpy evolves psi through BLAS matmul +
    pairwise-summed norms; summation order differs from the naive loop).
  - End-to-end organism drive: discrete observables (tick, population,
    windings, division count) must match exactly; analog observables
    (arousal, consensus) to <=1e-6.

Run:  python3 native/guala_core/tests/test_differential.py
  or  pytest native/guala_core/tests/test_differential.py
"""

import math
import os
import sys

if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np  # noqa: E402

import guala_core as gc  # noqa: E402

from dsf_ai_service.substrate import native_core  # noqa: E402
from dsf_ai_service.substrate.krimelack import Krimelack as SubKrim  # noqa: E402
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (  # noqa: E402
    Krimelack as V4Krim, LanguageKrimelack,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf as py_dsf  # noqa: E402
from dsf_ai_service.loom_model.substrate_dna import (  # noqa: E402
    CochlearBankKrimelack, VisualKrimelack,
)
from dsf_ai_service.loom_model.neuron import (  # noqa: E402
    PsiLattice, _map_inject as py_map_inject,
)

RNG = np.random.default_rng(1234)

WORDS = ["water", "garden", "The-Sun!", "guala", "fire", "wonder",
         "xylophone", "a", "supercalifragilistic", "cafe", "night"]


def events_equal(py_events, rs_tuples):
    assert len(py_events) == len(rs_tuples), \
        f"event count {len(py_events)} != {len(rs_tuples)}"
    for e, (t, dw, s) in zip(py_events, rs_tuples):
        assert e["t"] == t, (e, t)
        assert e["dw"] == dw, (e, dw)
        assert e["s"] == s, (e, s)


# ---------------------------------------------------------------------------

def test_krim_feed_v4():
    for trial in range(50):
        sig = list(RNG.uniform(-1.0, 1.0, int(RNG.integers(1, 400))))
        k = V4Krim(omega_0=2.0, kappa=float(RNG.uniform(20, 120)),
                   dt=0.04, threshold=math.pi / 3)
        # random starting state (mid-life krimelack)
        k.phase = float(RNG.uniform(-1.0, 1.0))
        k.t = float(RNG.uniform(0, 50))
        k.winding = int(RNG.integers(-100, 100))
        k.n_events = int(RNG.integers(0, 1000))

        r = gc.krim_feed(k.phase, k.t, k.winding, k.n_events,
                         k.omega_0, k.kappa, k.dt, k.threshold, sig)
        k.feed(sig)
        assert k.phase == r[0], (k.phase, r[0])
        assert k.t == r[1]
        assert k.winding == r[2]
        assert k.n_events == r[3]
        # v4 events live in a deque(maxlen=256): the Python side keeps only
        # the newest 256; the kernel returns all new events and the wrapper's
        # deque-append reproduces the same eviction. Compare the tail.
        py_ev = list(k.events)
        events_equal(py_ev, r[4][-len(py_ev):] if py_ev else [])
    print("ok  krim_feed vs v4 Krimelack.feed (50 trials, exact)")


def test_krim_feed_substrate():
    for trial in range(50):
        sig = list(RNG.uniform(-1.0, 1.0, int(RNG.integers(1, 400))))
        k = SubKrim(omega_0=2.0, kappa=60.0, dt=0.02,
                    integration_threshold=math.pi / 3)
        k.phase = float(RNG.uniform(-1.0, 1.0))
        r = gc.krim_feed(k.phase, k.t, k.winding, 0,
                         k.omega_0, k.kappa, k.dt, k.threshold, sig)
        k.feed_signal(sig)
        assert k.phase == r[0]
        assert k.t == r[1]
        assert k.winding == r[2]
        events_equal(k.events, r[4])
    print("ok  krim_feed vs substrate Krimelack.feed_signal (50 trials, exact)")


def test_lang_transduce():
    for word in WORDS:
        for no_reset in (False, True):
            for offset in (0.0, math.pi / 3 * 5):
                k_py = LanguageKrimelack()
                k_rs = LanguageKrimelack()
                if no_reset:  # pre-advance both identically
                    k_py.transduce("prelude", no_reset=False)
                    k_rs.transduce("prelude", no_reset=False)
                fp_py, role_py, senses_py = k_py.transduce(
                    word, omega_override=1.7, phase_offset=offset,
                    no_reset=no_reset)
                fp_rs, role_rs, senses_rs = native_core._lang_transduce(
                    k_rs, word, omega_override=1.7, phase_offset=offset,
                    no_reset=no_reset)
                assert fp_py == fp_rs, (word, fp_py, fp_rs)
                assert role_py == role_rs and senses_py == senses_rs
                assert k_py.phase == k_rs.phase
                assert k_py.t == k_rs.t
                assert k_py.winding == k_rs.winding
                assert k_py.n_events == k_rs.n_events
                assert list(k_py.events) == list(k_rs.events)
    print(f"ok  lang_transduce vs LanguageKrimelack.transduce "
          f"({len(WORDS)} words x reset/no_reset x offsets, exact)")


def test_biquad():
    from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
        bandpass_filter, COCHLEAR_BANDS,
    )
    for band in COCHLEAR_BANDS:
        sig = RNG.uniform(-1.0, 1.0, 300)
        y_py = bandpass_filter(sig, band["freq"], band["bandwidth"], 200)
        y_rs = gc.biquad_bandpass(sig.tolist(), float(band["freq"]),
                                  float(band["bandwidth"]), 200.0)
        assert np.array_equal(y_py, np.asarray(y_rs)), band["name"]
    print("ok  biquad_bandpass vs bandpass_filter (6 bands, exact)")


def test_cochlear():
    for trial in range(10):
        sig = RNG.uniform(-1.0, 1.0, int(RNG.integers(50, 400)))
        a_py = CochlearBankKrimelack()
        a_py.feed_signal(sig)
        tw_rs, ev_rs = gc.cochlear_feed(sig.tolist())
        # feed_signal applies winding += total, phase = winding*0.1
        assert a_py.winding == tw_rs, (a_py.winding, tw_rs)
        events_equal(a_py.events, ev_rs)
    print("ok  cochlear_feed vs CochlearBankKrimelack.feed_signal (10 trials, exact)")


def test_fovea():
    for trial in range(10):
        v_py = VisualKrimelack()
        v_rs = VisualKrimelack()
        for feed_i in range(3):  # state carries across feeds
            sig = RNG.random(int(RNG.integers(20, 150)))
            v_py.feed_signal(sig)
            native_core._visual_feed_signal(v_rs, sig)
            assert v_py._fovea.phase == v_rs._fovea.phase
            assert v_py._fovea.winding_count == v_rs._fovea.winding_count
            assert v_py._fovea.adapt_state == v_rs._fovea.adapt_state
            assert v_py.winding == v_rs.winding
            assert v_py.n_events == v_rs.n_events
            assert v_py.events == v_rs.events
    print("ok  fovea_feed vs VisualKrimelack.feed_signal (10 trials x 3 feeds, exact)")


def test_fingerprint():
    for trial in range(30):
        k = V4Krim(omega_0=2.0, kappa=80.0, dt=0.04, threshold=math.pi / 3)
        k.feed(list(RNG.uniform(-1.0, 1.0, int(RNG.integers(0, 300)))))
        fp_py = k.fingerprint()
        fp_rs = native_core._v4_fingerprint(k)
        assert fp_py == fp_rs, (fp_py, fp_rs)
    print("ok  fingerprint (30 trials, exact)")


def test_compute_dsf():
    for trial in range(50):
        n = int(RNG.integers(0, 60))
        t = 0.0
        events = []
        for _ in range(n):
            t += float(RNG.uniform(0.01, 0.2))
            events.append({"t": t, "dw": int(RNG.choice([-1, 1])),
                           "s": float(RNG.uniform(-1, 1))})
        sim = float(RNG.uniform(0, 1.2))
        d_py = py_dsf(events, atlas_similarity=sim)
        d_rs = native_core._compute_dsf(events, atlas_similarity=sim)
        for f in ("D_k", "M_k", "R_rev", "U_star", "C_k", "P_k", "B_k", "S_UF"):
            assert getattr(d_py, f) == getattr(d_rs, f), \
                (f, getattr(d_py, f), getattr(d_rs, f))
    print("ok  compute_dsf (50 trials incl n=0/1, exact)")


def test_map_inject():
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    for trial in range(30):
        dsf = py_dsf([{"t": 0.1 * (i + 1), "dw": 1, "s": 0.5}
                      for i in range(int(RNG.integers(2, 20)))])
        chi = int(RNG.integers(0, 10000))
        v_py = py_map_inject(dsf, chi)
        v_rs = native_core._map_inject(dsf, chi)
        assert np.allclose(v_py, v_rs, rtol=0, atol=1e-12), (chi, v_py - v_rs)
    print("ok  map_inject (30 trials, atol 1e-12)")


def test_psi_settle():
    max_rel = 0.0
    for trial in range(30):
        lat_py = PsiLattice()
        # random mid-life psi (normalized)
        psi0 = RNG.standard_normal(16) + 1j * RNG.standard_normal(16)
        psi0 = psi0 / np.linalg.norm(psi0)
        lat_py.psi = psi0.copy()
        inj = RNG.uniform(0, 1.0, 16) * (0.0 if trial % 7 == 0 else 1.0)
        laws = [(0.25, "symmetry.basic"), (0.25, "consistency.basic")]
        out_py = lat_py.settle(inj.copy(), laws)
        out_rs = np.asarray(gc.psi_settle(psi0.tolist(), inj.tolist(),
                                          [0.25, 0.25]), dtype=np.complex128)
        rel = float(np.max(np.abs(out_py - out_rs)) / np.max(np.abs(out_py)))
        max_rel = max(max_rel, rel)
        assert rel <= 1e-9, rel
    print(f"ok  psi_settle (30 trials, max rel diff {max_rel:.2e} <= 1e-9)")


def test_end_to_end_organism():
    """Two organisms, same seed, same word stream: one pure Python, one with
    the native kernels installed. Discrete state must match exactly."""
    from dsf_ai_service.loom_model.embryo import Embryo

    def drive(org, rng):
        words = ["water", "fire", "garden", "the", "bird", "sun", "night",
                 "apple", "wind", "stone", "guala", "moon", "bell", "cat",
                 "warm", "river", "song", "cloud", "tree", "star"]
        for i, w in enumerate(words):
            sig = {"language": w}
            if i % 4 == 0:
                sig["visual"] = rng.random(100)
                sig["auditory"] = rng.uniform(-1.0, 1.0, 300)
            org.experience_word(w, sig)
        return words

    def snapshot(org):
        return {
            "tick": org.tick,
            "population": org.brain.total_neurons(),
            "divisions": getattr(org, "_total_divisions", 0),
            "windings": {h.hemi_id: sorted(h.cluster.winding_signature().items())
                         for h in org.brain.hemispheres},
            "arousal": org.arousal,
            "consensus": dict(org.consensus),
            "strength": dict(org.strength),
        }

    assert not native_core.is_installed()
    org_py = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    drive(org_py, np.random.default_rng(99))
    snap_py = snapshot(org_py)

    assert native_core.install(), "native install failed"
    try:
        org_rs = Embryo(brain_seed=42, seed_size=8, observable="event_count")
        drive(org_rs, np.random.default_rng(99))
        snap_rs = snapshot(org_rs)
    finally:
        native_core.uninstall()

    assert snap_py["tick"] == snap_rs["tick"]
    assert snap_py["population"] == snap_rs["population"], \
        (snap_py["population"], snap_rs["population"])
    assert snap_py["divisions"] == snap_rs["divisions"]
    assert snap_py["windings"] == snap_rs["windings"]
    assert abs(snap_py["arousal"] - snap_rs["arousal"]) <= 1e-6
    for k in snap_py["consensus"]:
        assert abs(snap_py["consensus"][k] - snap_rs["consensus"][k]) <= 1e-6, k
    for k in snap_py["strength"]:
        assert abs(snap_py["strength"][k] - snap_rs["strength"][k]) <= 1e-6, k
    print(f"ok  end-to-end organism drive (20 words, 5 multi-modal): "
          f"tick={snap_rs['tick']} population={snap_rs['population']} "
          f"divisions={snap_rs['divisions']} windings exact, "
          f"arousal/consensus/strength <= 1e-6")


def main():
    test_krim_feed_v4()
    test_krim_feed_substrate()
    test_lang_transduce()
    test_biquad()
    test_cochlear()
    test_fovea()
    test_fingerprint()
    test_compute_dsf()
    test_map_inject()
    test_psi_settle()
    test_end_to_end_organism()
    print("\nALL DIFFERENTIAL TESTS PASSED")


if __name__ == "__main__":
    main()
