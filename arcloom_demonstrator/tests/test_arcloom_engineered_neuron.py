"""Component falsification for the numerical material transition.

These tests do not close A10 (full joint-field mounting) or A11 (organism motor
causality). They independently check actual energy residuals, exact carrier
identities, causal controls, finite solver refusal and complete cold custody.
"""
from fractions import Fraction
import math
import struct
import zlib
import pytest
from guala_core import ArcLoomNeuron

E = Fraction(1602176634, 10**28)
VALENCES = (1, 1, 2, -1, 1, 1)
PAYLOAD_OFFSET = 26


def remainder_ratios(neuron):
    def integer(limbs):
        return sum(value << (64 * i) for i, value in enumerate(limbs))
    return [
        (-1 if negative else 1) * Fraction(integer(num), integer(den))
        for negative, num, den in neuron.get_exact_remainders()
    ]


def rewrite_payload(snapshot, offset, fmt, value):
    data = bytearray(snapshot)
    struct.pack_into(fmt, data, PAYLOAD_OFFSET + offset, value)
    data[-4:] = struct.pack(">I", zlib.crc32(data[PAYLOAD_OFFSET:-4]))
    return bytes(data)


def physical_bytes(neuron):
    return bytes(neuron.export_canonical_bytes())


def check_energy(result):
    residual = result.delta_enthalpy_j - result.work_input_j + result.heat_dissipated_j
    assert result.heat_dissipated_j >= 0
    assert residual == result.energy_residual_j
    assert abs(residual) <= result.numerical_energy_bound_j + result.carrier_energy_bound_j
    assert result.convergence_error <= 1e-6
    assert 2 <= result.subintervals <= 4096
    assert math.isfinite(result.delta_enthalpy_j)


def test_genesis_and_exact_endpoint_charge():
    cell = ArcLoomNeuron()
    assert cell.get_reservoirs_in() == [30270581073, 353156779183, 252255, 25225484227]
    assert cell.get_reservoirs_out() == [91442380324, 2522548423, 1261274211, 69370081625]
    assert cell.get_apertures() == [0.05, 0.05, 0.02, 0.10]
    capacitance = .01 * 4 * math.pi * (10e-6)**2
    gate = (20 + 15 + .8) * float(E)
    expected = (-5098117 * float(E) - gate) / capacitance
    assert cell.membrane_voltage() == pytest.approx(expected, rel=1e-14)
    assert cell.receiving_voltage() == -405698 * float(E) / 1e-12
    assert sum(cell.get_integer_charge_endpoints()) == 0
    assert remainder_ratios(cell) == [0] * 6


def test_exact_carrier_identity_and_receiving_endpoints():
    cell = ArcLoomNeuron()
    totals = [a+b for a,b in zip(cell.get_reservoirs_in(), cell.get_reservoirs_out())]
    for current in (1e-9, -1e-9, 2e-10, 0.0):
        before = remainder_ratios(cell)
        endpoints_before = cell.get_integer_charge_endpoints()
        result = cell.step(external_current_a=current, dt_seconds=1e-4)
        after = remainder_ratios(cell)
        for lane, (z, count, charge) in enumerate(zip(VALENCES, result.whole_carriers, result.integrated_charge_c)):
            # Independent unbounded rational ORACLE, not production arithmetic.
            assert z * E * (count + after[lane] - before[lane]) == Fraction.from_float(charge)
            assert abs(after[lane]) < 1
        endpoints_after = cell.get_integer_charge_endpoints()
        assert sum(endpoints_after) == 0
        assert endpoints_after[3] - endpoints_before[3] == result.whole_carriers[5]
        assert endpoints_after[2] - endpoints_before[2] == -result.whole_carriers[4]
        assert [a+b for a,b in zip(cell.get_reservoirs_in(), cell.get_reservoirs_out())] == totals
        check_energy(result)


def test_nonempty_topology_cold_successor_and_repeated_use():
    original = ArcLoomNeuron()
    original.add_fabric_edge(0, 1, 1, 4.28e-20, dim=0, role=0, position=1)
    original.add_fabric_edge(1, 2, -1, 4.28e-20, dim=1, role=1, position=2)
    original.step(applied_contact_x=1.08e-6, external_current_a=5e-10)
    encoded = physical_bytes(original)
    fresh = ArcLoomNeuron()
    used = ArcLoomNeuron()
    used.add_fabric_edge(2, 3, -1, 1e-20, dim=4, position=5)
    used.step(external_current_a=2e-10)
    for copy in (fresh, used):
        copy.import_canonical_bytes(encoded)
        assert physical_bytes(copy) == encoded
    for _ in range(3):
        results = [n.step(applied_contact_x=1.01e-6, external_current_a=-2e-10) for n in (original, fresh, used)]
        assert physical_bytes(original) == physical_bytes(fresh) == physical_bytes(used)
        for key in ("delta_enthalpy_j", "energy_residual_j", "whole_carriers", "integrated_charge_c", "subintervals"):
            assert getattr(results[0], key) == getattr(results[1], key) == getattr(results[2], key)
        check_energy(results[0])


def test_retained_deformation_causally_changes_equal_load_response():
    learned = ArcLoomNeuron()
    first = learned.step(applied_contact_x=1.15e-6, external_current_a=1e-9)
    assert first.plastic_yield_occurred and first.plastic_dissipation_j > 0
    encoded = physical_bytes(learned)
    # This is a disclosed single-cause counterfactual, not an invented experience:
    # all state/anatomy is identical except retained stress-free contact length.
    ell_offset = 5*8 + 6*145 + 4*32 + 8
    ablated = ArcLoomNeuron()
    ablated.import_canonical_bytes(rewrite_payload(encoded, ell_offset, ">d", 1e-6))
    assert learned.get_phases() == ablated.get_phases()
    assert learned.get_apertures() == ablated.get_apertures()
    assert learned.get_reservoirs_in() == ablated.get_reservoirs_in()
    assert learned.get_integer_charge_endpoints() == ablated.get_integer_charge_endpoints()
    a = learned.step(applied_contact_force_n=0.0)
    b = ablated.step(applied_contact_force_n=0.0)
    assert learned.get_contact_geometry()[0] != ablated.get_contact_geometry()[0]
    assert a.integrated_charge_c[5] != b.integrated_charge_c[5]
    assert a.whole_carriers[5] != b.whole_carriers[5]
    check_energy(a)
    check_energy(b)
    # Negative control: identical imposed actual geometry must NOT receive
    # a developer-authored conductance multiplier from the retained rest length.
    learned.import_canonical_bytes(encoded)
    ablated.import_canonical_bytes(rewrite_payload(encoded, ell_offset, ">d", 1e-6))
    a = learned.step(applied_contact_x=1.05e-6)
    b = ablated.step(applied_contact_x=1.05e-6)
    assert a.integrated_charge_c == b.integrated_charge_c
    assert a.whole_carriers == b.whole_carriers


def independent_energy(cell):
    # Independent high-precision oracle; no production energy getter is used.
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = 70
        D = Decimal.from_float
        material_offset = PAYLOAD_OFFSET + 5*8 + 6*145 + 4*32
        data = physical_bytes(cell)
        x, ell, crec, _, _, _, cmem, stiffness, _, _, _ = struct.unpack_from(">11d", data, material_offset)
        y = cell.get_apertures()
        phases = cell.get_phases()
        kb_t = D(1.380649e-23 * 300.0)
        z_free, _, _, z_receiver = cell.get_integer_charge_endpoints()
        elementary = Decimal(E.numerator) / Decimal(E.denominator)
        q_gate = sum(Decimal(m)*Decimal(z)*elementary*D(aperture)
                     for m, z, aperture in zip((100,100,20,50),(4,3,2,0),y))
        h = (Decimal(z_free)*elementary-q_gate)**2/(2*D(cmem))
        h += (Decimal(-405698+z_receiver)*elementary)**2/(2*D(crec))
        h += D(stiffness)*(D(x)/D(ell)-1)**2/2
        for m, aperture, rest in zip((100,100,20,50), y, (.05,.05,.02,.10)):
            h += Decimal(m)*D(100.0*(1.380649e-23*300.0))*(D(aperture)-D(rest))**2/2
        nedge_offset = material_offset + 11*8
        nedge, = struct.unpack_from(">H", data, nedge_offset)
        for index in range(nedge):
            _, _, _, a, b, trit, kappa = struct.unpack_from(">BBHBBbd", data, nedge_offset+2+15*index)
            delta = phases[b]-phases[a]
            h -= D(kappa)*D(math.cos(delta-2*math.pi*trit/3))
            h -= Decimal((100,100,20,50)[a])*D(1e-20)*D(y[a])*D(math.cos(delta))
        vin = (4.0/3.0)*math.pi*(10e-6)*(10e-6)*(10e-6)
        for counts, volume in ((cell.get_reservoirs_in(),vin),(cell.get_reservoirs_out(),.25*vin)):
            for count in counts:
                n = Decimal(count)
                h += kb_t*n*((n/D(volume)).ln()-1)
        return +h


def test_first_law_is_an_equation_not_a_finite_number_test():
    cell = ArcLoomNeuron()
    cell.add_fabric_edge(0, 1, 1, 4.28e-20)
    for x in (1e-6, 1.02e-6, 1.15e-6):
        initial = independent_energy(cell)
        result = cell.step(applied_contact_x=x, external_current_a=1e-9)
        final = independent_energy(cell)
        delta = float(final-initial)
        check_energy(result)
        assert abs(delta-result.delta_enthalpy_j) <= result.numerical_energy_bound_j
        assert abs(delta-result.work_input_j+result.heat_dissipated_j) <= (
            result.numerical_energy_bound_j + result.carrier_energy_bound_j)
        assert result.heat_dissipated_j >= result.plastic_dissipation_j


def test_invalid_and_crc_valid_malformed_input_is_atomic():
    cell = ArcLoomNeuron()
    encoded = physical_bytes(cell)
    for size in range(len(encoded)):
        with pytest.raises(ValueError):
            cell.import_canonical_bytes(encoded[:size])
        assert physical_bytes(cell) == encoded
    for offset, fmt, value in [
        (0, ">Q", 2**64-1),             # admitted endpoint, next-step overflow tested below
        (40, ">B", 2),                 # noncanonical remainder sign
        (5*8+6*145+16, ">d", -0.01),    # gate aperture
        (5*8+6*145+24, ">d", math.pi),  # noncanonical phase, no wrapping on decode
    ]:
        changed = rewrite_payload(encoded, offset, fmt, value)
        if offset == 0:
            cell.import_canonical_bytes(changed)
            with pytest.raises(RuntimeError):
                cell.step()
            assert physical_bytes(cell) == changed
            cell.import_canonical_bytes(encoded)
        else:
            with pytest.raises(ValueError):
                cell.import_canonical_bytes(changed)
            assert physical_bytes(cell) == encoded
    # A valid checksum over an empty payload used to reach unchecked slices.
    header = b"ARCLOOM_NEURON_V3\0" + struct.pack(">I", 0)
    empty = header + struct.pack(">I", zlib.crc32(header)) + struct.pack(">I", zlib.crc32(b""))
    for invalid in (empty, encoded + b"\0", encoded + bytes(1 << 20)):
        with pytest.raises(ValueError):
            cell.import_canonical_bytes(invalid)
        assert physical_bytes(cell) == encoded
    for args in (
        {"external_current_a": math.nan}, {"external_current_a": 1e308, "dt_seconds": 1.0},
        {"applied_contact_x": 1e308}, {"dt_seconds": 0.0}, {"relative_tolerance": 0.0},
        {"applied_contact_x": 1e-6, "applied_contact_force_n": 0.0},
    ):
        with pytest.raises(RuntimeError):
            cell.step(**args)
        assert physical_bytes(cell) == encoded


def test_solver_accuracy_refines_observables_and_refuses_exhausted_budget():
    results = []
    for tolerance in (1e-4, 1e-6, 1e-8):
        cell = ArcLoomNeuron()
        cell.add_fabric_edge(0, 1, 1, 4.28e-20)
        result = cell.step(external_current_a=1e-9, relative_tolerance=tolerance)
        assert result.convergence_error <= tolerance
        results.append((cell, result))
    coarse, medium, fine = results
    assert coarse[1].subintervals < medium[1].subintervals < fine[1].subintervals
    thermal_voltage = (1.380649e-23 * 300) / float(E)
    for method in ("membrane_voltage", "receiving_voltage"):
        a, b, c = [getattr(cell, method)() for cell, _ in results]
        assert abs(b-c) < abs(a-c)
        assert abs(b-c) <= 1e-6 * thermal_voltage
    # The finite work budget is a numerical refusal, not a state clamp.
    cell = ArcLoomNeuron()
    cell.add_fabric_edge(0, 1, 1, 4.28e-20)
    before = physical_bytes(cell)
    with pytest.raises(RuntimeError, match="numerical work budget exhausted"):
        cell.step(dt_seconds=0.01, relative_tolerance=1e-12)
    assert physical_bytes(cell) == before
    with pytest.raises(RuntimeError, match="No static sub-yield equilibrium"):
        cell.step(applied_contact_force_n=1.0)
    assert physical_bytes(cell) == before


def test_fresh_process_restores_the_same_complete_successor():
    import subprocess
    import sys
    import guala_core
    cell = ArcLoomNeuron()
    cell.add_fabric_edge(0, 1, 1, 4.28e-20, dim=2, role=1, position=38)
    cell.step(applied_contact_x=1.15e-6, external_current_a=1e-9)
    before = physical_bytes(cell)
    cell.step(applied_contact_force_n=0.0, external_current_a=-2e-10)
    script = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("guala_core", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
neuron = module.ArcLoomNeuron()
neuron.import_canonical_bytes(bytes.fromhex(sys.stdin.read()))
neuron.step(applied_contact_force_n=0.0, external_current_a=-2e-10)
print(bytes(neuron.export_canonical_bytes()).hex())
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, guala_core.__file__],
        input=before.hex(), text=True, capture_output=True, timeout=15, check=True)
    assert bytes.fromhex(result.stdout.strip()) == physical_bytes(cell)


def test_recurrent_component_retains_no_per_step_history():
    cell = ArcLoomNeuron()
    cell.add_fabric_edge(0, 1, 1, 4.28e-20)
    size = len(physical_bytes(cell))
    total = [a+b for a,b in zip(cell.get_reservoirs_in(), cell.get_reservoirs_out())]
    for index in range(32):
        result = cell.step(external_current_a=(1 if index % 2 == 0 else -1) * 2e-10)
        check_energy(result)
        assert sum(cell.get_integer_charge_endpoints()) == 0
        assert [a+b for a,b in zip(cell.get_reservoirs_in(), cell.get_reservoirs_out())] == total
        assert len(physical_bytes(cell)) == size
    # This is a fixed-size component custody witness, not a lifetime/RSS proof.


def test_constrained_gate_boundary_obeys_energy_or_refuses_atomically():
    cell = ArcLoomNeuron()
    initial = independent_energy(cell)
    result = cell.step(external_current_a=-1e-9, dt_seconds=1e-3)
    assert cell.get_apertures() == [0.0, 0.0, 0.0, 0.1]
    check_energy(result)
    delta = float(independent_energy(cell)-initial)
    assert abs(delta-result.work_input_j+result.heat_dissipated_j) <= (
        result.numerical_energy_bound_j + result.carrier_energy_bound_j)
    cell = ArcLoomNeuron()
    initial_bytes = physical_bytes(cell)
    # A stronger/longer load is refused; it is not rescued by clipping the
    # final capacitor voltage, finite chemical reservoirs, or error receipt.
    with pytest.raises(RuntimeError, match="Atomic refusal"):
        cell.step(external_current_a=-1e-9, dt_seconds=1e-2)
    assert physical_bytes(cell) == initial_bytes
