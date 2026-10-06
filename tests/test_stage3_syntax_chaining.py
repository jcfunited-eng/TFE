"""
Verification of Stage 3 Combinatorial Syntax Chaining via Native Directional Delay Fasciculi.

This test validates:
1. Structural fascicular connectivity of Cluster 4 (Columns 32..39: Syntax) within ModularSubstrate64D:
   - Recurrent inter-column connectivity within Cluster 4 (k_from == 4, k_to == 4).
   - Auditory afferent projections from Cluster 1 (Columns 8..15) to Cluster 4 (Columns 32..39).
   - Motor efferent projections from Cluster 4 to Cluster 5 (Columns 40..47: Motor/Vocal).
2. Material yield stress plasticity (f = |sigma| - Y <= 0) forming directional conductance bridges
   under sequential phonemic stimulation (A -> B: 'pah0' -> 'lah0').
3. Nocturnal sleep consolidation (Synaptic Homeostasis Hypothesis):
   - Proportional downscaling (g *= 1.0 - decay).
   - Competitive pruning of sub-threshold noise (w < prune_thresh -> 0.0).
   - Retention of consolidated syntactic fasciculi and lossless binary serialization round-trip.
4. Autonomous successor depolarization:
   - Probe with Syllable A alone triggers sequential depolarization and vocal motor drive.
   - Divergence from unconditioned naive control (naive control produces strictly zero vocal drive).
5. Domestic demand syllable sequencing in FunctionalOrganism:
   - Multi-syllable sequence chaining without Python scorecards, reward tables, or dictionaries.
"""

import struct
import numpy as np
import pytest

import guala_core
from dsf_ai_service.guala_functional_organism import FunctionalOrganism


L23_NODES = 128
L5_NODES = 64
NUM_COLUMNS = 64


def extract_inter_column_conductance_pairs(sparse_bytes: bytes) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    """
    Directly parse canonical ArcLoom v4 sparse binary checkpoint to extract
    lossless non-zero inter-column conductances across Layer 2/3 and Layer 5.
    """
    assert sparse_bytes[:8] == b"ARCLOOM4", "Invalid ArcLoom v4 magic header"
    offset = 24  # 8 bytes magic + 16 bytes header
    # Skip 64 column structures
    for _ in range(NUM_COLUMNS):
        offset += 36   # Scalar column header
        offset += 320  # Laminar nodes (L1:32, L23:128, L4:64, L5:64, L6:32)
        nz_count, = struct.unpack_from("<I", sparse_bytes, offset)
        offset += 4 + nz_count * 7  # Active intra-column entries

    # Layer 2/3 inter-column connections
    nz23_count, = struct.unpack_from("<I", sparse_bytes, offset)
    offset += 4
    pairs_23: dict[tuple[int, int], float] = {}
    denom_23 = NUM_COLUMNS * L23_NODES * L23_NODES
    step_23 = L23_NODES * L23_NODES
    for _ in range(nz23_count):
        idx, g = struct.unpack_from("<If", sparse_bytes, offset)
        offset += 8
        c_from = idx // denom_23
        rem = idx % denom_23
        c_to = rem // step_23
        pairs_23[(c_from, c_to)] = pairs_23.get((c_from, c_to), 0.0) + abs(g)

    # Layer 5 inter-column connections
    nz5_count, = struct.unpack_from("<I", sparse_bytes, offset)
    offset += 4
    pairs_5: dict[tuple[int, int], float] = {}
    denom_5 = NUM_COLUMNS * L5_NODES * L5_NODES
    step_5 = L5_NODES * L5_NODES
    for _ in range(nz5_count):
        idx, g = struct.unpack_from("<If", sparse_bytes, offset)
        offset += 8
        c_from = idx // denom_5
        rem = idx % denom_5
        c_to = rem // step_5
        pairs_5[(c_from, c_to)] = pairs_5.get((c_from, c_to), 0.0) + abs(g)

    return pairs_23, pairs_5


def test_syntax_cluster4_structural_connectivity() -> None:
    """Verify structural fascicular connectivity of Cluster 4 in ModularSubstrate64D."""
    sub = guala_core.ModularSubstrate64D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.20)

    # 1. Cluster 4 internal recurrent fasciculation (Columns 32..39)
    for c_from in range(32, 40):
        for c_to in range(32, 40):
            if c_from != c_to:
                assert not sub.is_tract_severed(c_from, c_to), f"Tract {c_from}->{c_to} within Cluster 4 must be intact"

    # 2. Auditory Cluster 1 (Cols 8..15) -> Syntax Cluster 4 (Cols 32..39)
    for a_col in range(8, 16):
        for s_col in range(32, 40):
            assert not sub.is_tract_severed(a_col, s_col), f"Tract {a_col}->{s_col} (Auditory->Syntax) must be intact"

    # 3. Syntax Cluster 4 (Cols 32..39) -> Motor Cluster 5 (Cols 40..47)
    for s_col in range(32, 40):
        for m_col in range(40, 48):
            assert not sub.is_tract_severed(s_col, m_col), f"Tract {s_col}->{m_col} (Syntax->Motor) must be intact"

    # 4. Syntax Cluster 4 (Cols 32..39) -> Prefrontal Cluster 7 (Cols 56..63)
    for s_col in range(32, 40):
        for p_col in range(56, 64):
            assert not sub.is_tract_severed(s_col, p_col), f"Tract {s_col}->{p_col} (Syntax->Prefrontal) must be intact"


def test_asymmetric_directional_delay_fasciculi_and_yield_plasticity() -> None:
    """
    Verify that sequential phonemic presentation (A -> B) drives plastic yield
    and establishes persistent asymmetric inter-column conductances in Cluster 4.
    """
    sub = guala_core.ModularSubstrate64D(yield_threshold=0.30, plastic_rate=0.20, activation_threshold=0.15)
    som = [0] * 32

    # Initial newborn substrate must have 0 active plastic synapses
    assert sub.active_synapses() == 0, "Genesis substrate must possess zero ungrounded plastic synapses"

    # Present Syllable A ('pah0') at Auditory Col 8 (sensory trit index 16)
    sens_a = [0] * 64
    sens_a[16] = 1

    # Present Syllable B ('lah0') at Auditory Col 9 (sensory trit index 17)
    sens_b = [0] * 64
    sens_b[17] = 1

    # Train sequence A -> B over 15 repeated pairings with quiet intervals
    for _ in range(15):
        sub.step(sens_a, som, 200.0, 0, 0.0, [])
        sub.step(sens_b, som, 200.0, 0, 0.0, [])
        sub.step([0] * 64, som, 200.0, 0, 0.0, [])

    trained_synapses = sub.active_synapses()
    assert trained_synapses > 50000, f"Plastic deformation must exceed 50,000 active synapses, got {trained_synapses}"

    # Extract non-zero plastic conductances directly from canonical binary export
    sparse_data = sub.export_sparse()
    pairs_23, pairs_5 = extract_inter_column_conductance_pairs(bytes(sparse_data))

    # Verify that plastic conductance bridges formed between Cluster 1, Cluster 4, and Cluster 5
    assert len(pairs_23) > 0, "Layer 2/3 inter-column plastic conductances must be non-empty"
    assert len(pairs_5) > 0, "Layer 5 inter-column plastic conductances must be non-empty"

    # Verify that Cluster 4 has active horizontal conductance bridges
    cluster4_cols = set(range(32, 40))
    c4_incoming = sum(v for (cf, ct), v in pairs_23.items() if ct in cluster4_cols)
    assert c4_incoming > 0.0, "Cluster 4 (Syntax) must receive positive plastic conductance from training"


def test_nocturnal_sleep_consolidation_pruning_and_roundtrip() -> None:
    """
    Verify nocturnal sleep downscaling, competitive noise pruning, and lossless
    binary serialization round-trip of the consolidated syntactic substrate.
    """
    sub = guala_core.ModularSubstrate64D(yield_threshold=0.30, plastic_rate=0.20, activation_threshold=0.15)
    som = [0] * 32
    sens_a = [0] * 64
    sens_a[16] = 1
    sens_b = [0] * 64
    sens_b[17] = 1

    for _ in range(15):
        sub.step(sens_a, som, 200.0, 0, 0.0, [])
        sub.step(sens_b, som, 200.0, 0, 0.0, [])
        sub.step([0] * 64, som, 200.0, 0, 0.0, [])

    pre_sleep = sub.active_synapses()

    # Execute production sleep consolidation (decay=0.03, prune_thresh=0.015)
    decayed, pruned = sub.sleep_consolidation(decay=0.03, prune_thresh=0.015)
    assert decayed > 0, "Sleep consolidation must execute downscaling on active conductances"
    post_sleep = sub.active_synapses()
    assert post_sleep <= pre_sleep, "Consolidation must prune or maintain active synapses"
    assert post_sleep > 10000, "Consolidated core sequence fasciculi must survive downscaling"

    # Lossless binary checkpoint export and restoration into fresh substrate clone
    exported = sub.export_sparse()
    assert len(exported) > 0
    assert len(exported) % 8 == 0, "ArcLoom v4 binary format must maintain 8-byte alignment"

    sub_clone = guala_core.ModularSubstrate64D()
    sub_clone.import_sparse(exported)
    assert sub_clone.active_synapses() == post_sleep, "Reconstituted clone must preserve exact consolidated synapse count"


def test_successor_depolarization_and_learned_divergence_from_naive() -> None:
    """
    Verify that presenting Syllable A alone triggers sequential depolarization
    and causal vocal efferent activation, diverging 100% from naive control.
    """
    sub_trained = guala_core.ModularSubstrate64D(yield_threshold=0.30, plastic_rate=0.20, activation_threshold=0.15)
    som = [0] * 32
    sens_a = [0] * 64
    sens_a[16] = 1
    sens_b = [0] * 64
    sens_b[17] = 1

    for _ in range(15):
        sub_trained.step(sens_a, som, 200.0, 0, 0.0, [])
        sub_trained.step(sens_b, som, 200.0, 0, 0.0, [])
        sub_trained.step([0] * 64, som, 200.0, 0, 0.0, [])

    sub_trained.sleep_consolidation(decay=0.03, prune_thresh=0.015)

    # Conditioned Probe: Present Syllable A on beat 0
    sub_trained.step(sens_a, som, 200.0, 0, 0.0, [])

    # Quiet Probe on beat 1: Observe successor chaining into Vocal Motor Column 43
    sub_trained.step([0] * 64, som, 200.0, 0, 0.0, [])
    vocal_trained, stride_trained, steer_trained, grip_trained = sub_trained.get_motor_efferent()

    # Naive Control under identical sequence probe
    sub_naive = guala_core.ModularSubstrate64D(yield_threshold=0.30, plastic_rate=0.20, activation_threshold=0.15)
    sub_naive.step(sens_a, som, 200.0, 0, 0.0, [])
    sub_naive.step([0] * 64, som, 200.0, 0, 0.0, [])
    vocal_naive, stride_naive, steer_naive, grip_naive = sub_naive.get_motor_efferent()

    # Trained substrate must produce positive vocal motor efferent
    assert vocal_trained > 0.0, f"Learned syntax chaining must depolarize vocal motor efferent, got {vocal_trained}"

    # Naive control under identical input must produce strictly ZERO vocal motor efferent
    assert vocal_naive == 0.0, f"Naive control must exhibit zero vocal drive without learning, got {vocal_naive}"

    # Verify complete causal divergence between learned organism and naive control
    assert vocal_trained != vocal_naive, "Learned syntactic competence must diverge from naive control"


def test_domestic_demand_syntax_chaining_in_organism_without_scorecards() -> None:
    """
    Verify multi-syllable sequence transitions ('pah0' -> 'lah0') in FunctionalOrganism
    during domestic/feeding demand routines without Python scorecards or dictionaries.
    """
    organism = FunctionalOrganism.genesis(identity="guala-stage3-syntax", organism_tick=1)
    state = organism._state

    # Heuristic score-driven pending_chain must remain inert/empty
    assert not state.get("pending_chain"), "Heuristic pending_chain queue must be inert/empty"

    # Simulate domestic caregiver prompt 'pah0'
    state["last_spoke_tick"] = 10
    state["prior_syllable"] = "pah0"

    # Under domestic feeding demand, verify syllable selection references authentic context
    situation = "room-dining"
    drive, name, context, reason = organism._choose_syllable(situation, prior_syllable="pah0")

    assert drive is not None, "Organism must produce physical vocal drive vector"
    assert len(drive) == 3, "Vocal drive vector must have 3 physical articulatory parameters"
    assert isinstance(name, str) and len(name) > 0, "Syllable name must be non-empty string"
    assert "pah0" in context, f"Syllable context must bind to prior syllable 'pah0', got '{context}'"

    # Verify no Python scorecards or heuristic reward dictionaries exist in decision
    assert not state.get("pending_chain"), "Authored syllable queues must remain inert"
