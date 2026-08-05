"""Known resonant language must not rescan the complete retained vocabulary."""

from collections import Counter

from dsf_ai_service.loom_model.brain import LoomBrain


def test_resonant_known_word_uses_each_neurons_exact_experience_route() -> None:
    brain = LoomBrain(
        brain_seed=42,
        seed_size=8,
        observable="resonant_spectral",
    )
    calls = []
    neurons = [
        neuron
        for hemisphere in brain.hemispheres
        for neuron in hemisphere.cluster.neurons
    ]

    for index, neuron in enumerate(neurons):
        target = {"neuron": index}
        neuron.encode_state = (
            lambda _signals, _lanes, target=target: target
        )

        def exact_or_best(concept, observed, *, target=target):
            calls.append((concept, observed))
            assert observed is target
            return "hello", 1.0

        neuron.binding_atlas.recall_exact_or_best = exact_or_best
        neuron.binding_atlas.recall_best = lambda _target: (
            (_ for _ in ()).throw(
                AssertionError("known language entered full vocabulary scan")
            )
        )

    votes = brain._recall_fast_resonant_spectral({"language": "Hello"})

    assert calls == [("hello", {"neuron": index})
                     for index in range(len(neurons))]
    assert votes == Counter({"hello": len(neurons)})


def test_resonant_unknown_word_retains_structural_best_match() -> None:
    brain = LoomBrain(
        brain_seed=42,
        seed_size=8,
        observable="resonant_spectral",
    )
    fallback_targets = []
    neurons = [
        neuron
        for hemisphere in brain.hemispheres
        for neuron in hemisphere.cluster.neurons
    ]

    for index, neuron in enumerate(neurons):
        target = {"neuron": index}
        neuron.encode_state = (
            lambda _signals, _lanes, target=target: target
        )

        def structural_best(observed, *, target=target):
            assert observed is target
            fallback_targets.append(observed)
            return "associated", 0.5

        neuron.binding_atlas.recall_best = structural_best

    votes = brain._recall_fast_resonant_spectral(
        {"language": "never-recorded"}
    )

    assert fallback_targets == [
        {"neuron": index}
        for index in range(len(neurons))
    ]
    assert votes == Counter({"associated": len(neurons)})
