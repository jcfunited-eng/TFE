"""Current whole-organism neuronal authority excludes retired Loom Chi."""

from __future__ import annotations

import inspect

from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    WholeOrganismNeuronPopulationOwner,
)
from dsf_ai_service.v4.guala_physical_runtime_core import Guala


def test_authenticated_full_field_reaches_current_neuron_population() -> None:
    engine_source = inspect.getsource(
        Guala._advance_live_neuron_perspective_attention
    )
    owner_source = inspect.getsource(
        WholeOrganismNeuronPopulationOwner.prepare
    )

    assert "prepared_neurons = neuron_owner.prepare(" in engine_source
    assert "local_receptor_activations=(" in engine_source
    assert "settlement.authority_receipt_sha256" in owner_source
    assert "full_field_sensory_roots(settlement)" in owner_source
    assert "chi" not in owner_source.lower()


def test_retired_chi_selection_has_no_current_dynamic_authority() -> None:
    assert not hasattr(LoomCluster, "_select_by_chi_familiarity")
    neuron_state = LoomNeuron("current-neuron").__getstate__()
    assert "chi_atlas" not in neuron_state
    assert "binding_atlas" not in neuron_state
    assert "_word_firing_callback" not in neuron_state
