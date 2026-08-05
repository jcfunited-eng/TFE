from __future__ import annotations

import inspect

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.substrate_dna import (
    CochlearBankKrimelack,
)
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    BILATERAL_RELATIONS_PER_OCCURRENCE,
    LANES_PER_OCCURRENCE,
    W1LoomAuditoryBridge,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _vocal_execution,
    _world,
)


def _receptors():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _vocal_execution(world, epoch)
    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            execution,
        ),
    )
    assert result.binaural_receptor_settlement is not None
    return result.binaural_receptor_settlement


def _auditory_state(brain: LoomBrain):
    return {
        neuron.neuron_id: neuron.krimelack_bank[
            "auditory"
        ].authenticated_full_field_state()
        for hemisphere_id in ("H1", "H6")
        for neuron in brain._hemi_map[
            hemisphere_id
        ].cluster.neurons
    }


def test_full_binaural_field_reaches_actual_auditory_krimelacks() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    bridge = W1LoomAuditoryBridge(brain)
    settlement = _receptors()

    receipt = bridge.settle(settlement)

    receipt.verify()
    assert len(receipt.deliveries) == LANES_PER_OCCURRENCE == 576
    assert len(receipt.bilateral_relations) == (
        BILATERAL_RELATIONS_PER_OCCURRENCE
    ) == 80
    assert {value.ear_id for value in receipt.deliveries} == {
        "left",
        "right",
    }
    assert {
        value.hemisphere_id for value in receipt.deliveries
    } == {"H1", "H6"}
    assert {
        value.field_name
        for value in receipt.deliveries
        if value.field_name in DSF_FIELD_ORDER
    } == set(DSF_FIELD_ORDER)
    assert {
        value.component
        for value in receipt.deliveries
        if value.field_name in DSF_FIELD_ORDER
    } == {"pressure", "phase"}
    assert all(value.sample_count > 0 for value in receipt.deliveries)
    assert all(
        len(value.trajectory_sha256) == 64
        for value in receipt.deliveries
    )
    assert all(
        "/" in value.exact_phase
        and isinstance(value.exact_winding, int)
        and isinstance(value.exact_winding_delta, int)
        for value in receipt.deliveries
    )
    assert {
        value.relation_name
        for value in receipt.bilateral_relations
    } == {
        "pressure_difference",
        "relevance_difference",
        "cumulative_phase_difference",
        "phase_advance_difference",
        "source_time_difference",
    }
    assert all(
        value.left_exact_winding_delta
        == value.right_exact_winding_delta
        for value in receipt.bilateral_relations
    )
    for hemisphere_id in ("H1", "H6"):
        neurons = brain._hemi_map[hemisphere_id].cluster.neurons
        assert all(
            isinstance(
                neuron.krimelack_bank["auditory"],
                CochlearBankKrimelack,
            )
            for neuron in neurons
        )
        assert all(
            neuron.krimelack_bank[
                "auditory"
            ].authenticated_full_field_state()
            for neuron in neurons
        )


def test_bridge_never_calls_legacy_step_or_wave_summary() -> None:
    source = inspect.getsource(W1LoomAuditoryBridge)

    assert ".step(" not in source
    assert "wave_summary" not in source
    assert "input_chi" not in source
    assert "match_score" not in source
    assert "_map_inject" not in source
    assert "psi_lattice" not in source


def test_same_physical_occurrence_cannot_be_delivered_twice() -> None:
    bridge = W1LoomAuditoryBridge(
        LoomBrain(seed_size=8, observable="event_count")
    )
    settlement = _receptors()

    bridge.settle(settlement)
    with pytest.raises(ValueError, match="already delivered"):
        bridge.settle(settlement)


def test_no_input_causes_no_learning_or_storage_growth() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    bridge = W1LoomAuditoryBridge(brain)

    before = _auditory_state(brain)
    assert bridge.latest is None
    assert all(not state for state in before.values())
    for _index in range(10):
        assert _auditory_state(brain) == before
        assert bridge.latest is None


def test_exact_auditory_lane_state_survives_cold_restore(
    tmp_path,
) -> None:
    organism = Embryo(
        brain_seed=42,
        seed_size=8,
        observable="event_count",
    )
    bridge = W1LoomAuditoryBridge(organism.brain)
    receipt = bridge.settle(_receptors())
    before = _auditory_state(organism.brain)
    state_path = tmp_path / "organism.sgr"

    organism.save_full_state(state_path)
    restored = Embryo.load_full_state(state_path)

    assert _auditory_state(restored.brain) == before
    receipt.verify()
