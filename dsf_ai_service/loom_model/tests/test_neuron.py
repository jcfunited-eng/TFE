"""
test_neuron.py — GL-CMD-78 T1–T10 sanity tests for LoomNeuron.

GL-CMD-LOOM-NEURON-STAGE1-EVE-20260620-78
"""

import math
import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron,
    PsiLattice,
    SpikeBuffer,
    CouplingsJij,
    FamiliarityFeedback,
    LawField,
    DNAExpressionSite,
    DEFAULT_LAWS,
    PSI_DIM,
    DET_COMMIT,
    P_COMMIT,
    _map_inject,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf
from dsf_ai_service.v4.gualaloom_mathloom_v1 import bt_div, bt_to_int, int_to_bt
from dsf_ai_service.v4.gualaloom_v5_engine import _SPIN_VECTOR_DIM


# ---------------------------------------------------------------------------
# T1: All 15 slots non-None after default construction
# ---------------------------------------------------------------------------

def test_t1_all_pieces_non_none():
    """LoomNeuron constructs with default DNA; all 15 pieces instantiated."""
    n = LoomNeuron("t1")

    # NEW pieces (1-6)
    assert n.psi_lattice is not None,    "1. psi_lattice missing"
    assert n.spike_buffer is not None,   "2. spike_buffer missing"
    assert n.couplings is not None,      "3. couplings missing"
    assert n.familiarity is not None,    "4. familiarity missing"
    assert n.laws is not None,           "5. laws missing"
    assert n.dna_site is not None,       "6. dna_site missing"
    # LoomNeuron itself is piece 7 — confirmed by reaching this line

    # REUSED pieces (8-15)
    assert n.trit_register is not None,  "8. trit_register missing"
    assert n.l6_tcl is not None,         "10. l6_tcl missing"
    assert n.chi_atlas is not None,      "10b. chi_atlas missing"
    assert n.krimelack is not None,      "12. krimelack missing"
    assert n.sensory_bank is not None,   "13. sensory_bank missing"

    # Pieces 9 (DSF/compute_dsf), 11 (MathLoom), 14 (_grandurun_state),
    # 15 (_SPIN_VECTOR_DIM) are module-level — verify importable
    assert compute_dsf is not None,      "9. compute_dsf not importable"
    assert bt_div is not None,           "11. bt_div not importable"
    assert _SPIN_VECTOR_DIM == 7,        "15. _SPIN_VECTOR_DIM != 7"


# ---------------------------------------------------------------------------
# T2: Single input → Krimelack winding-number transition fires (winding > 0)
# ---------------------------------------------------------------------------

def test_t2_krimelack_winding():
    """Single word input causes krimelack winding count > 0."""
    n = LoomNeuron("t2")
    # "fire" has strong consonant signal → many winding transitions
    n.krimelack.transduce("fire")
    assert n.krimelack.winding > 0, (
        f"Winding should be > 0 after 'fire', got {n.krimelack.winding}"
    )
    # Also check events were generated
    assert len(n.krimelack.events) > 0, "Expected events from 'fire'"


# ---------------------------------------------------------------------------
# T3: ψ-lattice commits on first non-trivial input
# ---------------------------------------------------------------------------

def test_t3_psi_commits_on_first_input():
    """ψ-lattice settles to a commit on first strong input."""
    n = LoomNeuron("t3")
    result = n.step("fire", tick=0)
    assert result["committed"], (
        f"Expected commit on 'fire'. p_max={np.max(n.psi_lattice.probabilities()):.3f} "
        f"B_k={n._last_dsf.B_k:.3f}"
    )


# ---------------------------------------------------------------------------
# T4: Grandurun state non-zero in chi_resonance dimension after T3
# ---------------------------------------------------------------------------

def test_t4_grandurun_chi_resonance_nonzero():
    """After a commit, grandurun vec[0] (chi_resonance) is non-zero."""
    n = LoomNeuron("t4")
    n.step("fire", tick=0)

    needs_vec = np.ones(3, dtype=np.float64) / 3.0
    vec = n.get_grandurun_state(
        target_chi=0,
        target_source="corpus",
        needs_vector=needs_vec,
        current_tick=0,
    )

    assert vec.dtype == np.complex128, f"Expected complex128, got {vec.dtype}"
    assert len(vec) == _SPIN_VECTOR_DIM, f"Expected dim={_SPIN_VECTOR_DIM}, got {len(vec)}"
    assert abs(vec[0]) > 0.0, (
        f"chi_resonance (vec[0]) should be non-zero, got {vec[0]}"
    )


# ---------------------------------------------------------------------------
# T5: Repeated identical input → match_score rises, Δ_eff rises, spike
#     intensity attenuates (monotonically non-increasing)
# ---------------------------------------------------------------------------

def test_t5_habituation():
    """Repeated identical input produces habituation: rising Δ_eff, falling intensity."""
    n = LoomNeuron("t5")

    delta_effs = []
    match_scores = []
    spike_intensities_per_step = []  # intensity of most recent spike on this step

    prev_spike_count = 0
    for i in range(10):
        result = n.step("fire", tick=i)
        delta_effs.append(result["delta_eff"])
        match_scores.append(result["match_score"])
        # Capture intensity of the spike that fired on THIS step (if any)
        cur_spike_count = result["spike_count"]
        if cur_spike_count > prev_spike_count:
            spikes = n.spike_buffer.read()
            spike_intensities_per_step.append(spikes[-1][1])
        prev_spike_count = cur_spike_count

    # match_score must be non-decreasing
    for j in range(1, len(match_scores)):
        assert match_scores[j] >= match_scores[j - 1], (
            f"match_score must be non-decreasing: step {j-1}→{j}: "
            f"{match_scores[j-1]:.3f}→{match_scores[j]:.3f}"
        )

    # delta_eff must be non-decreasing (Δ_eff = Δ_base + match_score)
    for j in range(1, len(delta_effs)):
        assert delta_effs[j] >= delta_effs[j - 1], (
            f"delta_eff must be non-decreasing: step {j-1}→{j}: "
            f"{delta_effs[j-1]:.3f}→{delta_effs[j]:.3f}"
        )

    # Spike intensities (from committed steps only) must be non-increasing
    if len(spike_intensities_per_step) >= 2:
        for j in range(1, len(spike_intensities_per_step)):
            assert spike_intensities_per_step[j] <= spike_intensities_per_step[j - 1] + 1e-9, (
                f"Spike intensity must attenuate: committed step {j-1}→{j}: "
                f"{spike_intensities_per_step[j-1]:.4f}→{spike_intensities_per_step[j]:.4f}"
            )

    # At least two distinct match_scores (rising happened at some point)
    assert max(match_scores) > min(match_scores), (
        "Expected match_score to rise at least once over 10 repetitions"
    )
    # At least one spike fired
    assert len(spike_intensities_per_step) >= 1, "Expected at least one commit+spike over 10 steps"


# ---------------------------------------------------------------------------
# T6: Folding Division — MathLoom: 6561 ÷ 81 = 81
# ---------------------------------------------------------------------------

def test_t6_mathloom_folding_division():
    """MathLoom bt_div: 6561 ÷ 81 = 81 (validated 3^4 ÷ 3^2 = 3^2)."""
    a = int_to_bt(6561)   # 3^8
    b = int_to_bt(81)     # 3^4
    q_digits, _r = bt_div(a, b)
    q = bt_to_int(q_digits)
    assert q == 81, f"Expected 6561÷81=81, got {q}"


# ---------------------------------------------------------------------------
# T7: L6-TCL reports n_eff; verify n_eff ≤ n_start after committed mode
# ---------------------------------------------------------------------------

def test_t7_l6_tcl_n_eff():
    """L6-TCL n_eff is bounded by n_start after any commit."""
    n = LoomNeuron("t7")
    result = n.step("fire", tick=0)
    dsf = n._last_dsf
    assert dsf is not None, "DSF should be set after step"

    n_eff = n.l6_tcl.n_eff(dsf)
    n_start = n.l6_tcl.n_start

    assert n_eff >= 0,        f"n_eff must be >= 0, got {n_eff}"
    assert n_eff <= n_start,  f"n_eff must be <= n_start={n_start}, got {n_eff}"
    assert result["n_eff"] == n_eff, "n_eff in result dict must match l6_tcl.n_eff(dsf)"


# ---------------------------------------------------------------------------
# T8: Spike Buffer FIFO ring — fills to depth 16 then evicts oldest
# ---------------------------------------------------------------------------

def test_t8_spike_buffer_ring():
    """SpikeBuffer fills to depth 16 then evicts oldest on append."""
    buf = SpikeBuffer()
    assert buf.DEPTH == 16

    # Fill to capacity
    for i in range(16):
        buf.append(tick=i, intensity=float(i), source_id=None)

    assert len(buf) == 16
    entries = buf.read()
    assert entries[0][0] == 0,  "Oldest entry should be tick=0"
    assert entries[-1][0] == 15, "Newest entry should be tick=15"

    # One more → evicts tick=0, tick=1 becomes oldest
    buf.append(tick=16, intensity=16.0)
    assert len(buf) == 16, "Buffer must stay at depth 16"
    entries = buf.read()
    assert entries[0][0] == 1,  f"Oldest should now be tick=1, got {entries[0][0]}"
    assert entries[-1][0] == 16, f"Newest should be tick=16, got {entries[-1][0]}"


# ---------------------------------------------------------------------------
# T9: Couplings J_ij — K=0 Stage 1, matrix shape (0, 16)
# ---------------------------------------------------------------------------

def test_t9_couplings_k0():
    """Stage 1 Couplings J_ij: no neighbors, matrix shape (0, PSI_DIM)."""
    n = LoomNeuron("t9")
    assert n.couplings.J.shape == (0, PSI_DIM), (
        f"Expected J.shape=(0,{PSI_DIM}), got {n.couplings.J.shape}"
    )
    assert len(n.couplings.neighbors) == 0, (
        f"Expected 0 neighbors in Stage 1, got {len(n.couplings.neighbors)}"
    )


# ---------------------------------------------------------------------------
# T10: DNA Expression Site round-trip
# ---------------------------------------------------------------------------

def test_t10_dna_expression_site():
    """DNAExpressionSite load/express round-trip returns identical blueprint."""
    site = DNAExpressionSite()
    blueprint = {
        "section": "listen",
        "omega_0": 2.0,
        "kappa": 80.0,
        "role_class": "subject",
    }

    returned = site.load(blueprint)
    expressed = site.express()

    assert returned is blueprint,  "load() must return the same blueprint object"
    assert expressed is blueprint, "express() must return the loaded blueprint"
    assert expressed == blueprint, "expressed blueprint must equal original"


# ---------------------------------------------------------------------------
# Bonus: PsiLattice normalization invariant
# ---------------------------------------------------------------------------

def test_psi_lattice_normalized_after_settle():
    """ψ remains unit-normalized after any settle call."""
    lattice = PsiLattice()
    events = []
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    krim = LanguageKrimelack()
    krim.transduce("water")
    dsf = compute_dsf(krim.events, atlas_similarity=0.3)
    inj = _map_inject(dsf, abs(krim.winding))
    lattice.settle(inj, [(0.25, "symmetry.basic"), (0.25, "consistency.basic")])
    norm = float(np.linalg.norm(lattice.psi))
    assert abs(norm - 1.0) < 1e-9, f"ψ must remain unit-normalized, got ||ψ||={norm}"
