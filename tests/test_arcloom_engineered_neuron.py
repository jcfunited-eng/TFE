"""Verification of ArcLoom Engineered Artificial Reference Material Neuron.

Governing documents:
- docs/GUALA_ONE_NEURON_MATERIAL_ANATOMY_BINDING_2026-10-01.md
- docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md
- docs/GUALA_ONE_NEURON_PHYSICAL_PARAMETER_DOSSIER_2026-10-01.md
"""
import pytest
from guala_core import ArcLoomNeuron


def test_arcloom_engineered_neuron_genesis_and_initial_state():
    neuron = ArcLoomNeuron()
    v0 = neuron.membrane_voltage()
    # Ratified V0 ~ -65.0000031305 mV
    assert abs(v0 - (-0.0650000031305)) < 1e-9, f"Unexpected V0: {v0}"

    apertures = neuron.get_apertures()
    assert apertures == [0.05, 0.05, 0.02, 0.10], f"Unexpected apertures: {apertures}"

    res_in = neuron.get_reservoirs_in()
    assert res_in == [30270581073, 353156779183, 252255, 25225484227]

    res_out = neuron.get_reservoirs_out()
    assert res_out == [91442380324, 2522548423, 1261274211, 69370081625]

    x, ell = neuron.get_contact_geometry()
    assert abs(x - 1.0e-6) < 1e-15
    assert abs(ell - 1.0e-6) < 1e-15


def test_arcloom_engineered_neuron_transition_and_plasticity():
    neuron = ArcLoomNeuron()

    # 1. Sub-yield elastic strain (2% strain < 5% yield threshold)
    prior_v, succ_v, yielded, d_pl = neuron.step(
        applied_contact_x=1.02e-6,
        external_current_a=0.0,
        dt_seconds=1.0e-4,
    )
    assert not yielded, "2% strain must be in elastic regime"
    assert d_pl == 0.0, "Elastic deformation must have zero plastic dissipation"

    # 2. Post-yield plastic strain (15% strain > 5% yield threshold)
    prior_v2, succ_v2, yielded2, d_pl2 = neuron.step(
        applied_contact_x=1.15e-6,
        external_current_a=0.0,
        dt_seconds=1.0e-4,
    )
    assert yielded2, "15% strain must trigger plastic yield"
    assert d_pl2 > 0.0, "Plastic yield must produce positive plastic dissipation"

    x_new, ell_new = neuron.get_contact_geometry()
    assert ell_new > 1.0e-6, "Plastic yield must increase rest length"


def test_arcloom_engineered_neuron_typed_fabric():
    neuron = ArcLoomNeuron()
    neuron.add_fabric_edge(from_node=0, to_node=1, tau_trit=1, kappa_j=4.28e-20)
    neuron.add_fabric_edge(from_node=1, to_node=2, tau_trit=-1, kappa_j=4.28e-20)

    # Invalid trit outside {-1, 0, 1} must raise ValueError
    with pytest.raises(ValueError):
        neuron.add_fabric_edge(from_node=0, to_node=1, tau_trit=2, kappa_j=4.28e-20)


def test_arcloom_engineered_neuron_canonical_cold_restart():
    original = ArcLoomNeuron()
    # Advance 3 steps
    for _ in range(3):
        original.step(applied_contact_x=1.08e-6, external_current_a=5.0e-10, dt_seconds=1.0e-4)

    raw_bytes = original.export_canonical_bytes()
    assert len(raw_bytes) == 312, f"Expected 312 bytes, got {len(raw_bytes)}"

    # Restore into clean instance
    restored = ArcLoomNeuron()
    restored.import_canonical_bytes(raw_bytes)

    assert restored.export_canonical_bytes() == raw_bytes, "Restored bytes must match original"
    assert restored.membrane_voltage() == original.membrane_voltage()
    assert restored.get_apertures() == original.get_apertures()
    assert restored.get_reservoirs_in() == original.get_reservoirs_in()

    # Step both under identical stimulus
    orig_res = original.step(applied_contact_x=1.01e-6, external_current_a=-1.0e-10, dt_seconds=1.0e-4)
    rest_res = restored.step(applied_contact_x=1.01e-6, external_current_a=-1.0e-10, dt_seconds=1.0e-4)

    assert orig_res == rest_res, "Cold successor must evolve identically to continuous instance"
    assert restored.export_canonical_bytes() == original.export_canonical_bytes()
