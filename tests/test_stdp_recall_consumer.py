"""
GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4): the STDP consumer.

Neuron STDP has been updating _incoming_synapse_weights on the spike bus
since Phase 1 with no production reader -- learning without consequence.
LoomBrain now weights every population-vote recall by each neuron's
learned mean incoming synapse strength (see brain._stdp_vote_weight and
RECALL_STDP_GAIN).

This test teaches a pattern VIA REAL SPIKES (the real receive_spike ->
_fire -> _apply_stdp_potentiation path: a presynaptic spike from a real
peer neuron id immediately followed by a firing input, repeated) and
asserts the recall RANKING shifts: the concept held by the spike-taught
neurons overtakes the concept held by more-numerous untaught neurons.

Vote split is constructed deterministically: every neuron is bound to
exactly ONE concept (34 neurons -> "apple", 30 -> "river") at the SAME
encoding, so before teaching the vote is exactly 34 vs 30 and "apple"
ranks first; STDP alone must flip it.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

import numpy as np  # noqa: E402


def _spike(target_id, source_id, weight):
    from dsf_ai_service.substrate.spike_bus import PendingSpike
    return PendingSpike(
        arrival_time=time.monotonic(),
        target_neuron_id=target_id,
        source_neuron_id=source_id,
        weight=weight,
    )


def test_spike_taught_pattern_shifts_recall_ranking():
    from dsf_ai_service.loom_model.embryo import Embryo
    from dsf_ai_service.loom_model.neuron import (
        STDP_DEFAULT_SYNAPSE_WEIGHT)

    emb = Embryo(brain_seed=42, seed_size=8, observable="resonant_spectral")
    brain = emb.brain
    all_neurons = [n for h in brain.hemispheres for n in h.cluster.neurons]
    assert len(all_neurons) == 64

    sig = np.linspace(0.1, 1.0, 32)
    signals = {"tactile": sig}
    apple_neurons = all_neurons[:34]
    river_neurons = all_neurons[34:]
    for n in apple_neurons:
        n.experience_moment("apple", signals, tick=1)
    for n in river_neurons:
        n.experience_moment("river", signals, tick=2)

    votes_before = brain.recall_fast(signals)
    assert votes_before["apple"] == 34.0 and votes_before["river"] == 30.0, (
        f"unexpected baseline vote split: {dict(votes_before)} -- the "
        "constructed one-concept-per-neuron setup did not hold")
    assert votes_before.most_common(1)[0][0] == "apple"

    # Teach the pattern via real spikes: pre (real peer source, weight
    # 0.5, subthreshold) then a firing input right after -- the pre lands
    # inside the STDP potentiation window of the fire, strengthening the
    # peer synapse through _apply_stdp_potentiation. 15 reps per neuron.
    peer_id = apple_neurons[0].neuron_id  # a REAL neuron id, not external
    for n in river_neurons:
        for _ in range(15):
            n.receive_spike(_spike(n.neuron_id, peer_id, 0.5))
            n.receive_spike(_spike(n.neuron_id, "_teach_input_", 2.0))
            time.sleep(0.004)  # clear the 2ms refractory between reps

    learned = [n._incoming_synapse_weights.get(peer_id, 0.0)
               for n in river_neurons]
    assert all(w > STDP_DEFAULT_SYNAPSE_WEIGHT for w in learned), (
        "spike teaching did not potentiate the peer synapse "
        f"(weights: {sorted(set(round(w, 3) for w in learned))})")

    votes_after = brain.recall_fast(signals)
    assert votes_after["apple"] == votes_before["apple"], (
        "untaught neurons' votes changed -- the consumer must only "
        "reweight what STDP actually learned")
    assert votes_after["river"] > votes_before["river"], (
        f"taught concept's vote weight did not rise: "
        f"{votes_after['river']} vs {votes_before['river']}")
    assert votes_after.most_common(1)[0][0] == "river", (
        f"recall ranking did not shift to the spike-taught concept: "
        f"{votes_after.most_common(2)} -- learning still has no consequence")
    print("test_spike_taught_pattern_shifts_recall_ranking: PASS "
          f"(river {votes_before['river']:.1f} -> {votes_after['river']:.1f}, "
          f"apple flat at {votes_after['apple']:.1f})")


def test_untrained_brain_votes_are_exactly_legacy():
    """Zero-potentiation organisms vote exactly 1.0 per neuron -- the
    consumer is behavior-identical to the old +=1 until real learning
    exists (restored pre-Phase-1 pickles included)."""
    from dsf_ai_service.loom_model.embryo import Embryo
    emb = Embryo(brain_seed=7, seed_size=8, observable="resonant_spectral")
    brain = emb.brain
    sig = {"tactile": np.linspace(0.2, 0.9, 16)}
    for h in brain.hemispheres:
        for n in h.cluster.neurons:
            n.experience_moment("stone", sig, tick=1)
    votes = brain.recall_fast(sig)
    assert votes["stone"] == 64.0, (
        f"untrained vote total {votes['stone']!r} != 64 -- weighting "
        "changed behavior for an organism that never learned via spikes")
    print("test_untrained_brain_votes_are_exactly_legacy: PASS")


if __name__ == "__main__":
    test_spike_taught_pattern_shifts_recall_ranking()
    test_untrained_brain_votes_are_exactly_legacy()
    print("ALL PASS: test_stdp_recall_consumer")
