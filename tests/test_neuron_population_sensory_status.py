from __future__ import annotations

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from tests.test_whole_organism_neuron_population import (
    _owner,
    _settlement,
)


_FREQUENCIES = (9, 4, 5, 6, 7, 8)


def _six_sense_settlement(name: str):
    return _settlement(name, frequencies=_FREQUENCIES)


def test_status_partitions_every_owned_neuron_by_exact_sense() -> None:
    owner = _owner()
    owner.commit(owner.prepare(_six_sense_settlement("sensory-status")))

    status = owner.status()
    expected_senses = {
        family.value for family in SENSE_ORDER
    }

    assert set(status["neurons_by_sense"]) == expected_senses
    assert set(status["perturbed_neurons_by_sense"]) == expected_senses
    assert status["neurons_by_sense"] == {
        sense: 1 for sense in expected_senses
    }
    assert status["perturbed_neurons_by_sense"] == {
        sense: 1 for sense in expected_senses
    }
    assert sum(status["neurons_by_sense"].values()) == status["neurons"]
    assert sum(status["perturbed_neurons_by_sense"].values()) == (
        status["neurons"]
    )
    assert status["full_field"] is True
    assert status["reduced_approximation"] is False


def test_quiescent_neurons_remain_counted_but_not_active() -> None:
    owner = _owner()
    owner.commit(owner.prepare(_six_sense_settlement("base")))
    topology = _settlement(
        "topology",
        frequencies=_FREQUENCIES,
        add_sight_path=True,
        sight_only=True,
    )
    owner.commit(owner.prepare(topology))

    status = owner.status()

    assert status["neurons_by_sense"] == {
        "body": 1,
        "sight": 2,
        "smell": 1,
        "sound": 1,
        "taste": 1,
        "touch": 1,
    }
    assert status["perturbed_neurons_by_sense"] == {
        "body": 0,
        "sight": 2,
        "smell": 0,
        "sound": 0,
        "taste": 0,
        "touch": 0,
    }
    assert sum(status["neurons_by_sense"].values()) == status["neurons"]
    assert sum(status["perturbed_neurons_by_sense"].values()) == 2
    assert status["quiescent_neurons"] == 5
