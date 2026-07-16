"""
test_growth_pool_law.py — GL-FIX-GROWTH-POOL-LAW-20260716.

Root-cause regression tests for the live growth freeze (2M words of real
reading -> total_divisions=0, division_pool=0.0, n_q_over_0_9=64):
the -198 flux law guaranteed refill <= maintenance for every possible
experience, so the division pool drained monotonically to zero and every
charged neuron was clamped at the basin edge forever.

Every test here drives the REAL production path — the exact
organism.experience_word(word, multi_modal_signals) call
_organism_worker_loop makes (gualaloom_v5_engine.py ~6312), with the
exact signal dict shape _organism_signal_with_senses builds — and
asserts REAL measurable growth (divisions, neurons, coupling edges), not
internals-only bookkeeping.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.embryo import Embryo, resonance_signal, resonance_and_signature


SEED_KW = dict(brain_seed=42, seed_size=8, observable="event_count")  # production shape: 8x8=64


def _sense_signal(i):
    """A coherent, varied multi-sense moment — the shape a real camera/mic
    frame or descriptor-modal signal takes by the time it reaches
    experience_word (1D float arrays under visual/auditory keys)."""
    t = np.linspace(0, 2 * np.pi, 200)
    vis = np.sin(t * (3 + i % 11)) + 0.3 * np.sin(t * (13 + i % 7))
    aud = np.sin(t * (5 + i % 9)) + 0.2 * np.cos(t * (2 + i % 5))
    return {"language": f"word{i}", "visual": vis * (1 + 0.1 * (i % 4)), "auditory": aud}


def _coupling_edges(emb):
    """Total real synaptic edges: every neuron's couplings.neighbors list.
    New edges form ONLY at cluster.attach() (daughter wiring at division)
    on the live path — this is the connection-formation observable."""
    return sum(len(n.couplings.neighbors)
               for h in emb.brain.hemispheres for n in h.cluster.neurons)


def _drained(emb):
    """Model the live organism's actual state: the pre-fix law had already
    drained its pool to exactly 0.0 (observed live). Growth after this
    point must be funded entirely by real novel experience."""
    emb._div_pool = 0.0
    return emb


# ---------------------------------------------------------------------------
# 1. The smoking gun, fixed: real experience through the real path grows.
# ---------------------------------------------------------------------------

def test_novel_experience_drives_real_divisions_and_connections():
    emb = _drained(Embryo(**SEED_KW))
    edges_before = _coupling_edges(emb)
    neurons_before = emb.growth_snapshot()["total_neurons"]
    assert neurons_before == 64

    div_marks = []
    for i in range(300):
        emb.experience_word(f"w{i}", _sense_signal(i))
        if i + 1 in (100, 200, 300):
            div_marks.append(emb.growth_snapshot()["total_divisions"])

    snap = emb.growth_snapshot()
    # Real growth happened.
    assert snap["total_divisions"] > 0, "2M-word freeze regression: no divisions"
    assert snap["total_neurons"] > neurons_before
    # Real connections formed (daughter coupling wiring), scaling with growth.
    assert _coupling_edges(emb) > edges_before
    # Growth SCALES with input: strictly more divisions at 300 words than 100.
    assert div_marks[-1] > div_marks[0] > 0
    # fold events were recorded for the engine's pop_fold_events() drain
    # (already drained by earlier calls is fine — total counter is the record).
    assert snap["total_divisions"] == snap["total_neurons"] - 64


def test_fold_events_surface_through_pop_fold_events():
    """The engine drains pop_fold_events() right after each
    experience_word (gualaloom_v5_engine.py ~6339) — every division must
    surface there, with the real hemi/parent/daughter detail."""
    emb = _drained(Embryo(**SEED_KW))
    seen = []
    for i in range(120):
        emb.experience_word(f"w{i}", _sense_signal(i))
        seen.extend(emb.pop_fold_events())
    assert len(seen) == emb.growth_snapshot()["total_divisions"] > 0
    for ev in seen:
        assert ev["hemi"] and ev["parent"] and ev["daughter"]
        assert ev["q_at_fold"] > 1.0


# ---------------------------------------------------------------------------
# 2. Bounded-growth guards: novelty-funded, never tick-funded, hard-capped.
# ---------------------------------------------------------------------------

def test_replayed_signal_funds_nothing_growth_never_scales_with_tick_count():
    emb = _drained(Embryo(**SEED_KW))
    fixed = _sense_signal(7)
    for _ in range(300):
        emb.experience_word("same", fixed)
    snap = emb.growth_snapshot()
    # A replay loop (same signal, unbounded ticks) must not fund growth:
    # its spectral signature saturates the novelty history immediately.
    assert snap["total_divisions"] == 0
    assert snap["total_neurons"] == 64
    assert snap["division_pool"] < 1.0  # never accumulates a division's worth


def test_language_only_reading_neither_funds_nor_bleeds_the_pool():
    """The live case: ~2M words of reading are language-only moments
    (composite all-zero). Pre-fix, each one bled 1.28 from the pool
    (maintenance billed on every word); post-fix a seed-sized organism
    pays no pool upkeep (the pool only maintains pool-created mass), so
    reading leaves the growth budget exactly intact."""
    emb = Embryo(**SEED_KW)
    assert emb._div_pool == 64.0
    for i in range(300):
        emb.experience_word(f"read{i}", {"language": f"read{i}"})
    snap = emb.growth_snapshot()
    assert snap["division_pool"] == 64.0
    assert snap["total_divisions"] == 0
    assert snap["n_q_over_0_9"] == 0  # language-only moments are not coherent


def test_pool_never_exceeds_birth_capacity():
    emb = Embryo(**SEED_KW)
    for i in range(150):
        emb.experience_word(f"w{i}", _sense_signal(i))
        assert emb._div_pool <= float(emb._N_initial) + 1e-9


def test_hard_population_cap_blocks_loudly(capsys, monkeypatch):
    monkeypatch.setenv("GUALA_MAX_TOTAL_NEURONS", "70")
    emb = Embryo(**SEED_KW)  # full birth pool: would burst past 70 without the cap
    for i in range(80):
        emb.experience_word(f"w{i}", _sense_signal(i))
    snap = emb.growth_snapshot()
    assert snap["total_neurons"] <= 70
    assert snap["growth_cap_hits"] > 0
    assert snap["max_total_neurons"] == 70
    out = capsys.readouterr().out
    assert "GROWTH CAP HIT" in out and "GUALA_MAX_TOTAL_NEURONS=70" in out


def test_emergent_asymptote_stays_under_twice_seed():
    """The flux law's own equilibrium is N_eq = N_init*(1 + E[sig_res *
    novelty]) <= 2*N_init — the bound the original -169 design stated.
    A long, maximally-novel coherent diet must respect it without ever
    touching the hard cap."""
    emb = Embryo(**SEED_KW)
    for i in range(400):
        emb.experience_word(f"w{i}", _sense_signal(i))
    snap = emb.growth_snapshot()
    assert snap["total_neurons"] <= 2 * emb._N_initial
    assert snap["growth_cap_hits"] == 0  # default cap (256) never involved


# ---------------------------------------------------------------------------
# 3. The law itself: refill can now genuinely exceed maintenance (the
#    pre-fix impossibility), and the rollback env restores old behavior.
# ---------------------------------------------------------------------------

def test_pool_can_refill_from_novel_coherent_experience():
    """Pre-fix, the per-word pool delta was NEVER positive (verified by
    driving the real path). Post-fix, a novel coherent moment on a
    drained seed-sized organism must produce a strictly positive delta."""
    emb = _drained(Embryo(**SEED_KW))
    before = emb._div_pool
    emb.experience_word("w0", _sense_signal(0))
    assert emb._div_pool > before


def test_legacy_env_restores_prefix_flux(monkeypatch):
    monkeypatch.setenv("GUALA_GROWTH_LAW_LEGACY", "1")
    emb = Embryo(**SEED_KW)
    p0 = emb._div_pool
    emb.experience_word("x", {"language": "x"})
    # old law at seed population: refill lambda*64 == maintenance lambda*64
    assert emb._div_pool == pytest.approx(p0)


def test_resonance_and_signature_matches_resonance_signal():
    """The single-FFT helper must be numerically identical to the
    existing gate measure for every real signal shape."""
    rng = np.random.default_rng(0)
    for arr in (np.zeros(1), np.zeros(64), rng.standard_normal(200),
                np.sin(np.linspace(0, 20, 400)),
                np.concatenate([np.sin(np.linspace(0, 30, 200)),
                                rng.standard_normal(100) * 0.1])):
        res, sig = resonance_and_signature(arr)
        assert res == pytest.approx(resonance_signal(arr))
        if res == 0.0:
            assert sig is None
        else:
            assert isinstance(sig, tuple) and len(sig) == 3


def test_novelty_history_is_bounded():
    emb = Embryo(**SEED_KW)
    for i in range(600):
        emb.experience_word(f"w{i}", _sense_signal(i))
    assert emb._recent_input_signatures is not None
    assert len(emb._recent_input_signatures) <= emb.NOVELTY_HISTORY_MAXLEN


def test_restored_prefix_pickle_self_heals():
    """An organism pickled before this fix has no _recent_input_signatures
    / _growth_cap_hits (pickle bypasses __init__ — the -198 lesson). The
    growth law must self-heal and keep working on such an organism."""
    emb = Embryo(**SEED_KW)
    del emb._recent_input_signatures
    del emb._growth_cap_hits
    emb._div_pool = 0.0
    for i in range(120):
        emb.experience_word(f"w{i}", _sense_signal(i))
    snap = emb.growth_snapshot()
    assert snap["total_divisions"] > 0
    assert snap["growth_cap_hits"] == 0
