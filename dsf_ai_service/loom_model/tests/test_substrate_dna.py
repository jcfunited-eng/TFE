"""
test_substrate_dna.py — GL-CMD-84 T1-T2: substrate DNA catalog tests.
"""

import sys, os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.substrate_dna import (
    KRIMELACK_PRIMITIVES,
    OverflowSignal,
    derive_daughter_parameters,
    TactileKrimelack,
    OlfactoryKrimelack,
    GustatoryKrimelack,
    VisualKrimelack,
    CochlearBankKrimelack,
    K_TOTAL,
    PSI_LATTICE_DIM,
)
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack


# ---------------------------------------------------------------------------
# T1: derive_daughter_parameters is a pure function
# ---------------------------------------------------------------------------

def test_t1_pure_function():
    """Same inputs → identical outputs across two calls."""
    parent = LoomNeuron("parent")
    parent.step("fire", tick=0)

    overflow = OverflowSignal(
        origin_transducer="tactile",
        psi_overflow_vector=np.random.default_rng(42).random(PSI_LATTICE_DIM).astype(np.complex128),
        dsf_tuple=(0.3, 0.5, 0.2, 0.4, 0.6, 0.7, 0.8, 0.3),
        events=[{"t": 0.1, "dw": 1, "s": 0.5}],
    )

    result1 = derive_daughter_parameters(overflow, parent)
    result2 = derive_daughter_parameters(overflow, parent)

    assert result1["krimelack_class"] is result2["krimelack_class"]
    assert np.array_equal(result1["psi_init"], result2["psi_init"])
    assert result1["omega_0"] == result2["omega_0"]
    assert result1["law_field_weights"] == result2["law_field_weights"]
    assert result1["k_intra"] == result2["k_intra"]
    assert result1["k_inter"] == result2["k_inter"]
    assert result1["inherited_neighbors"] == result2["inherited_neighbors"]


# ---------------------------------------------------------------------------
# T2: KRIMELACK_PRIMITIVES has exactly 6 entries
# ---------------------------------------------------------------------------

def test_t2_six_primitives():
    """Catalog has exactly 6 entries matching the 6 transducer paths."""
    assert len(KRIMELACK_PRIMITIVES) == 6, (
        f"Expected 6 primitives, got {len(KRIMELACK_PRIMITIVES)}: "
        f"{list(KRIMELACK_PRIMITIVES.keys())}"
    )
    expected_keys = {"language", "tactile", "olfactory", "gustatory", "visual", "auditory"}
    assert set(KRIMELACK_PRIMITIVES.keys()) == expected_keys, (
        f"Keys mismatch: {set(KRIMELACK_PRIMITIVES.keys())} vs {expected_keys}"
    )

    # Verify each maps to a class with transduce-compatible interface
    assert KRIMELACK_PRIMITIVES["language"] is LanguageKrimelack
    assert KRIMELACK_PRIMITIVES["tactile"] is TactileKrimelack
    assert KRIMELACK_PRIMITIVES["olfactory"] is OlfactoryKrimelack
    assert KRIMELACK_PRIMITIVES["gustatory"] is GustatoryKrimelack
    assert KRIMELACK_PRIMITIVES["visual"] is VisualKrimelack
    assert KRIMELACK_PRIMITIVES["auditory"] is CochlearBankKrimelack


# ---------------------------------------------------------------------------
# Adapter smoke tests
# ---------------------------------------------------------------------------

def test_tactile_adapter():
    """TactileKrimelack adapter produces events from touch params."""
    k = TactileKrimelack()
    k.transduce({"temperature": 0.85, "pressure": 0.3})
    assert len(k.events) > 0, "Expected events from touch transduction"
    assert k.winding != 0 or len(k.events) > 0

def test_auditory_adapter():
    """CochlearBankKrimelack adapter produces events from audio signal."""
    k = CochlearBankKrimelack()
    rng = np.random.default_rng(42)
    signal = np.sin(2 * np.pi * 50 * np.arange(400) / 200) + rng.normal(0, 0.1, 400)
    k.transduce(signal)
    assert len(k.events) > 0, "Expected events from audio transduction"
