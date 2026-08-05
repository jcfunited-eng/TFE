"""
GL-FIX-CHI-ATLAS-BUCKET-ORDER-20260712: unit tests for the
chi_atlas.record() argument-order bug in LoomNeuron.step() and its
kill-switched fix.

Bug under test
---------------
GL-CMD-CHI-UNIFICATION-EVE-20260707-v3 (2026-07-07) intended chi_atlas to
bucket entries by the UPSTREAM chi (the same krimelack-derived chi the
wave atlas uses) instead of `dominant_mode` (an internal PSI_DIM=16
argmax index) -- that dispatch's own text: "chi_atlas gets the upstream
chi so match_score can compare against future inputs." But
ChiAtlas.record's real signature is
`record(self, section_name, motif_id, chi_value, tick=None)`
(gualaloom_v4_chi_atlas_l6.py:46), and `chi_value` -- the THIRD
positional slot -- is what `.entries` is actually bucketed by
(`self.entries[chi_value + d]`, line 55), not `motif_id`. The call this
dispatch shipped at neuron.py's step() commit path has always been:

    self.chi_atlas.record("neuron", _chi_for_atlas, dominant_mode, tick)

-- upstream chi in the motif_id slot, dominant_mode in the chi_value
slot. Backwards from the dispatch's own stated intent. Net effect:
chi_atlas has bucketed by dominant_mode (0-15) since v3 shipped, not by
upstream chi -- the exact "two incompatible numeric ranges" symptom v3
itself was written to fix, reintroduced one argument slot over.

This also gates LoomCluster._select_by_chi_familiarity (cluster.py:211),
the real "chi-familiarity neuron gate" that restricts which neurons
process a given input each tick. With the bug, `familiar` is effectively
always empty for real (wide-range) input_chi, so every tick falls
through to the 2-lowest-entry-count novelty pool -- and WHICH neurons
that is keeps drifting, tick to tick, instead of converging on the
neurons that have actually seen this chi before.

Kill switch under test: CHI_ATLAS_BUCKET_FIX_ENABLED (default OFF/unset).
OFF must reproduce today's exact (buggy) call byte-for-byte. ON must
produce the corrected bucketing (and, as a consequence, real convergence
in the chi-familiarity neuron gate).

Real path only: every test below drives the real LoomNeuron.step() /
LoomCluster.step() production entry points with a real input_chi -- no
ChiAtlas internals are called directly to force a result, and the
kill-switch flag is read the same live-every-call way neuron.py reads it
(os.environ.get(..., "0") == "1"), never monkeypatched.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

import pytest

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron,
    CHI_ATLAS_BUCKET_FIX_ENABLED_ENV,
)
from dsf_ai_service.loom_model.cluster import LoomCluster, FAMILIARITY_THRESHOLD
from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas, CHI_BAND

# A realistic upstream chi: krimelack winding-derived, far outside
# PSI_DIM=16's dominant_mode range -- exactly the class of value real
# production callers pass (see GL-CMD-CHI-UNIFICATION-EVE-20260707-v3's
# own "first exposure of a word with upstream chi=42000" example).
WIDE_CHI = 42000
N_REPS = 8


@pytest.fixture(autouse=True)
def _clean_env():
    """Never let one test's env mutation leak into the next."""
    prior = os.environ.pop(CHI_ATLAS_BUCKET_FIX_ENABLED_ENV, None)
    yield
    if prior is None:
        os.environ.pop(CHI_ATLAS_BUCKET_FIX_ENABLED_ENV, None)
    else:
        os.environ[CHI_ATLAS_BUCKET_FIX_ENABLED_ENV] = prior


def _drive_neuron(switch_value):
    """Fresh LoomNeuron, N_REPS repeated commits of the SAME wide-range
    input_chi, kill switch set to switch_value (None = unset)."""
    if switch_value is None:
        os.environ.pop(CHI_ATLAS_BUCKET_FIX_ENABLED_ENV, None)
    else:
        os.environ[CHI_ATLAS_BUCKET_FIX_ENABLED_ENV] = switch_value

    n = LoomNeuron("chi_bucket_test")
    trace = []
    for i in range(N_REPS):
        result = n.step("fire", tick=i, input_chi=WIDE_CHI)
        trace.append({
            "tick": i,
            "committed": result["committed"],
            "match_score": result["match_score"],
            "last_commit_chi": n._last_commit_chi,
            "entries_keys": sorted(n.chi_atlas.entries.keys()),
        })
    return n, trace


# ---------------------------------------------------------------------------
# 1. Reproduce the bug against today's (unfixed-by-default) code
# ---------------------------------------------------------------------------

def test_bug_reproduces_with_switch_unset():
    """Default state (no env var set at all, i.e. what production runs
    today): repeated commits of the SAME upstream chi never raise
    match_score above 0 -- the chi-familiarity gate is non-functional for
    real, wide-range chi. This is the failure this whole fix exists for,
    proven against the real call path, not assumed."""
    n, trace = _drive_neuron(None)

    assert all(row["committed"] for row in trace), (
        "fixture assumption broken: 'fire' should commit every tick")

    match_scores = [row["match_score"] for row in trace]
    assert max(match_scores) == 0.0, (
        f"expected match_score to stay at 0.0 across {N_REPS} repeats of "
        f"the identical input_chi={WIDE_CHI} with the bug present (switch "
        f"unset) -- got {match_scores}. If this now rises, the bug may "
        f"already be fixed or the default flipped -- investigate before "
        f"trusting this test suite's other assertions.")

    # _last_commit_chi correctly holds the real upstream chi (that part of
    # v3's fix -- what's recorded as the neuron's OWN chi state -- works).
    assert all(row["last_commit_chi"] == WIDE_CHI for row in trace)

    # But chi_atlas.entries -- what match_score / _select_by_chi_familiarity
    # actually read -- never contains a key anywhere near WIDE_CHI. Every
    # key present is in dominant_mode's small PSI_DIM=16-ish range instead.
    final_keys = trace[-1]["entries_keys"]
    band = set(range(WIDE_CHI - CHI_BAND, WIDE_CHI + CHI_BAND + 1))
    assert not (band & set(final_keys)), (
        f"expected NO chi_atlas key near WIDE_CHI={WIDE_CHI} with the bug "
        f"present, got keys={final_keys} intersecting {sorted(band)}")
    assert all(k < 32 for k in final_keys), (
        f"expected all chi_atlas keys to stay in dominant_mode's small "
        f"(0-15-ish) range with the bug present, got {final_keys}")

    final_match = n.chi_atlas.match_score(WIDE_CHI, "neuron")
    assert final_match <= FAMILIARITY_THRESHOLD, (
        f"chi-familiarity gate should NOT consider this neuron familiar "
        f"with WIDE_CHI under the bug: match_score={final_match} vs "
        f"FAMILIARITY_THRESHOLD={FAMILIARITY_THRESHOLD}")


def test_bug_reproduces_with_switch_explicitly_off():
    """Same as above but with the env var explicitly '0' rather than
    unset -- both must behave identically (defense against a future
    default-flip elsewhere leaving unset != '0')."""
    _, trace_unset = _drive_neuron(None)
    _, trace_off = _drive_neuron("0")
    # Strip the object-identity-independent fields for comparison.
    simplify = lambda t: [(r["tick"], r["committed"], r["match_score"],
                            r["last_commit_chi"], r["entries_keys"]) for r in t]
    assert simplify(trace_unset) == simplify(trace_off), (
        "unset and explicit '0' must produce byte-identical traces")


# ---------------------------------------------------------------------------
# 2. Fix corrects the behavior when the kill switch is ON
# ---------------------------------------------------------------------------

def test_fix_restores_familiarity_when_switch_on():
    """With the kill switch on, repeated commits of the SAME upstream chi
    correctly accumulate real familiarity: entries bucket under WIDE_CHI's
    band, and match_score rises above FAMILIARITY_THRESHOLD -- restoring
    the exact "depth of learning" behavior GL-CMD-CHI-UNIFICATION-EVE-
    20260707-v3 was written to produce."""
    n, trace = _drive_neuron("1")

    match_scores = [row["match_score"] for row in trace]
    assert match_scores[0] == 0.0, (
        "first exposure should still be novel (nothing recorded yet)")
    assert max(match_scores) > FAMILIARITY_THRESHOLD, (
        f"expected match_score to rise above FAMILIARITY_THRESHOLD="
        f"{FAMILIARITY_THRESHOLD} after repeated exposure to the same "
        f"chi with the fix ON -- got {match_scores}")
    # Non-decreasing: familiarity should never regress across identical
    # repeated input (same invariant test_neuron.py's existing habituation
    # test already holds for the input_chi=None path).
    for j in range(1, len(match_scores)):
        assert match_scores[j] >= match_scores[j - 1], (
            f"match_score regressed at tick {j}: "
            f"{match_scores[j-1]} -> {match_scores[j]}")

    final_keys = trace[-1]["entries_keys"]
    band = set(range(WIDE_CHI - CHI_BAND, WIDE_CHI + CHI_BAND + 1))
    assert band & set(final_keys), (
        f"expected chi_atlas to have bucketed under WIDE_CHI={WIDE_CHI}'s "
        f"band with the fix ON, got keys={final_keys}")

    final_match = n.chi_atlas.match_score(WIDE_CHI, "neuron")
    assert final_match > FAMILIARITY_THRESHOLD, (
        f"chi-familiarity gate SHOULD consider this neuron familiar with "
        f"WIDE_CHI once fixed: match_score={final_match}")


# ---------------------------------------------------------------------------
# 3. Kill switch off => byte-identical to today, on a second independent
#    metric: dominant_mode's own psi_lattice bookkeeping is untouched
#    either way (this dispatch's own DO-NOT), regardless of switch state.
# ---------------------------------------------------------------------------

def test_dominant_mode_bookkeeping_unaffected_by_switch():
    """base_intensity = probs[dominant_mode] and dominant_mode's own
    computation must be identical with the switch on or off -- this fix
    only changes what chi_atlas.record() buckets by, never dominant_mode
    itself (scope guardrail from the original v3 dispatch, still
    respected here)."""
    n_off, _ = _drive_neuron(None)
    n_on, _ = _drive_neuron("1")

    # Same deterministic construction + input sequence -> psi_lattice
    # trajectories must match regardless of the chi_atlas bucketing switch.
    assert n_off.psi_lattice.probabilities().tolist() == pytest.approx(
        n_on.psi_lattice.probabilities().tolist()
    ), "psi_lattice state diverged between switch states -- the fix must not touch ψ dynamics"


# ---------------------------------------------------------------------------
# 4. Population-level consequence: the chi-familiarity neuron gate
#    (LoomCluster._select_by_chi_familiarity) actually stabilizes once
#    fixed, instead of drifting across the whole population every tick.
#    This is the concrete "previously-inert gate becomes active" effect
#    flagged for review -- proven directly, not asserted from theory.
# ---------------------------------------------------------------------------

def _drive_cluster(switch_value, n_neurons=8, k_neighbors=4, n_ticks=6):
    if switch_value is None:
        os.environ.pop(CHI_ATLAS_BUCKET_FIX_ENABLED_ENV, None)
    else:
        os.environ[CHI_ATLAS_BUCKET_FIX_ENABLED_ENV] = switch_value

    c = LoomCluster("chi_bucket_cluster", n_neurons=n_neurons, k_neighbors=k_neighbors)
    selected_per_tick = []
    for i in range(n_ticks):
        results = c.step("fire", tick=i, input_chi=WIDE_CHI)
        selected_per_tick.append(frozenset(results.keys()))
    return selected_per_tick


def test_familiarity_gate_drifts_under_bug():
    """With the bug present (switch off), the same repeated input_chi
    does NOT converge on a stable neuron subset -- the novelty-pool
    fallback (ranked by total, mis-bucketed entry count) keeps selecting
    different neurons tick to tick, because `familiar` never has any
    members for this wide-range chi."""
    selected = _drive_cluster(None)
    distinct_selections = set(selected)
    assert len(distinct_selections) > 1, (
        f"expected the buggy gate to drift across ticks for repeated "
        f"input_chi={WIDE_CHI}, but selection was stable: {selected} -- "
        f"if this is now stable, the underlying bug behavior may have "
        f"changed; re-verify before relying on this test")


def test_familiarity_gate_stabilizes_when_fixed():
    """With the fix on, the same repeated input_chi converges onto (and
    stays on) the same familiar neuron subset from the second tick
    onward -- this is the real, first-order production-routing change
    the fix introduces, demonstrated directly."""
    selected = _drive_cluster("1")
    # First tick is always the novelty pool (nothing recorded yet).
    # From the second tick onward it must be stable.
    stable_tail = selected[1:]
    assert len(set(stable_tail)) == 1, (
        f"expected the fixed gate to converge on one stable neuron subset "
        f"from tick 1 onward for repeated input_chi={WIDE_CHI}, got "
        f"per-tick selections: {selected}")


if __name__ == "__main__":
    test_bug_reproduces_with_switch_unset()
    test_bug_reproduces_with_switch_explicitly_off()
    test_fix_restores_familiarity_when_switch_on()
    test_dominant_mode_bookkeeping_unaffected_by_switch()
    test_familiarity_gate_drifts_under_bug()
    test_familiarity_gate_stabilizes_when_fixed()
    print("ALL PASS: test_chi_atlas_bucket_fix")
