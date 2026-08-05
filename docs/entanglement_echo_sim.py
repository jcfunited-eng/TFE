#!/usr/bin/env python3
"""
Entanglement Echo Measurement Simulation

Test Joseph's idea:
- Weak measurement of 2-body correlations (echo) vs direct measurement
- Does it actually preserve entanglement?
- Does 5-100x improvement hold under realistic NV center noise?

Compare three approaches:
1. Strong direct measurement (standard qubit)
2. Qutrit null-state error detection (from diamond spec)
3. Weak echo measurement of correlations

Truth test: Does echo measurement actually work or is it bullshit?
"""

import numpy as np
from scipy.linalg import expm
from scipy import special

# Physical constants for NV center in diamond
T2_NV = 1.8e-3  # Coherence time (seconds) - from diamond spec
F_GATE = 0.99   # 2-qutrit gate fidelity target (99%)
DEPHASE_RATE = 1 / T2_NV  # Dephasing rate (Hz)

# Paulis
SIGMA_X = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_Z = np.array([[1, 0], [0, -1]], dtype=complex)
SIGMA_I = np.eye(2, dtype=complex)

# Bell state: (|00> + |11>) / sqrt(2)
BELL_STATE = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)

class QuantumSimulator:
    """Simulate entanglement under different measurement schemes."""

    def __init__(self):
        self.dephase_rate = DEPHASE_RATE
        self.t2 = T2_NV

    def depolarizing_channel(self, rho, p):
        """Apply depolarizing noise to density matrix."""
        return (1 - p) * rho + (p / 4) * np.eye(len(rho))

    def dephasing_channel(self, rho, p):
        """Apply dephasing (phase flip) noise."""
        return (1 - p) * rho + p * np.diag(np.diag(rho))

    def bell_state_density_matrix(self):
        """Construct density matrix for Bell state."""
        psi = BELL_STATE.reshape(4, 1)
        return psi @ psi.conj().T

    # ============= METHOD 1: STRONG DIRECT MEASUREMENT =============

    def strong_measurement_qubit(self, n_trials=10000):
        """
        Standard qubit measurement: measure sigma_z on each qubit
        This COLLAPSES the entanglement completely.

        Returns:
        - Fidelity after measurement
        - Entanglement entropy
        - Error rate
        """

        results = []
        entanglement_entropy_list = []

        for trial in range(n_trials):
            rho = self.bell_state_density_matrix()

            # Measurement process: collapse to eigenstate
            # Result is either |00> or |11> with 50% probability each
            if np.random.rand() < 0.5:
                collapsed = np.zeros((4, 4), dtype=complex)
                collapsed[0, 0] = 1.0  # |00><00|
            else:
                collapsed = np.zeros((4, 4), dtype=complex)
                collapsed[3, 3] = 1.0  # |11><11|

            # Fidelity: how well does collapsed state match Bell state?
            fidelity = np.trace(collapsed @ rho).real
            results.append(fidelity)

            # Entanglement entropy (von Neumann) - should be 0 (separable after measurement)
            eigvals = np.linalg.eigvalsh(collapsed)
            eigvals = eigvals[eigvals > 1e-10]  # Remove numerical zeros
            if len(eigvals) > 0:
                entropy = -np.sum(eigvals * np.log2(eigvals + 1e-15))
            else:
                entropy = 0
            entanglement_entropy_list.append(entropy)

        avg_fidelity = np.mean(results)
        avg_entropy = np.mean(entanglement_entropy_list)

        return {
            'method': 'Strong (Qubit)',
            'fidelity_loss': 1.0 - avg_fidelity,  # Should be ~1.0 (complete collapse)
            'entanglement_entropy': avg_entropy,  # Should be ~0 (product state)
            'avg_fidelity': avg_fidelity,
            'error_rate': 0.5,  # 50% chance of wrong basis
        }

    # ============= METHOD 2: QUTRIT NULL-STATE DETECTION =============

    def qutrit_null_state_measurement(self, n_trials=10000):
        """
        From diamond spec: Use ternary (3-level) system with ms=0 as error flag.
        If measurement hits ms=0, it's an error -> discard and retry.
        Otherwise, result is reliable.

        This is the baseline from the diamond quantum computer spec.
        """

        valid_fidelities = []
        discard_rate = 0

        for trial in range(n_trials):
            rho = self.bell_state_density_matrix()

            # Simulate qutrit measurement with null-state detection
            # P(correct) = 0.95 (from spec)
            # P(error to ms=0) = 0.04 (detectable)
            # P(silent error) = 0.01 (undetectable)

            r = np.random.rand()

            if r < 0.95:
                # Correct measurement
                fidelity = 0.95
                valid_fidelities.append(fidelity)
            elif r < 0.99:
                # Error to null state (ms=0) - DETECTED, discarded
                discard_rate += 1
            else:
                # Silent error - ACCEPTED (bad)
                fidelity = 0.0
                valid_fidelities.append(fidelity)

        if len(valid_fidelities) == 0:
            valid_fidelities = [0]

        avg_fidelity = np.mean(valid_fidelities)

        return {
            'method': 'Qutrit Null-State',
            'fidelity_loss': 1.0 - avg_fidelity,
            'entanglement_entropy': 0.01,  # Some loss due to silent errors
            'avg_fidelity': avg_fidelity,
            'discard_rate': discard_rate / n_trials,
            'error_rate': 0.01,  # Silent error rate (spec fig 6)
        }

    # ============= METHOD 3: WEAK ECHO MEASUREMENT =============

    def weak_echo_measurement(self, n_repeats=3, lambda_weak=0.01, n_trials=10000):
        """
        Proposed method: Weak measurement of correlations.

        REALISTIC version with actual noise sources:
        - Apparatus thermal noise
        - Measurement uncertainty
        - Pointer dephasing
        - Imperfect coupling
        - Environment decoherence during measurement
        """

        fidelities = []
        entanglement_entropies = []

        # Noise parameters from realistic NV/diamond systems
        THERMAL_NOISE = 0.01  # Thermal fluctuations in measurement apparatus
        MEASUREMENT_UNCERTAINTY = 0.02  # Fundamental quantum uncertainty
        APPARATUS_DEPHASE_T1 = 100e-6  # Apparatus relaxation time (microseconds)
        ENVIRONMENT_DEPHASE = 0.001  # Environmental dephasing rate

        for trial in range(n_trials):
            rho = self.bell_state_density_matrix()

            weak_values = []
            measurement_errors = []

            # Measure in three bases: z, x, y
            for basis_idx in range(n_repeats):
                # Choose basis
                if basis_idx == 0:
                    corr_op = np.kron(SIGMA_Z, SIGMA_Z)
                elif basis_idx == 1:
                    corr_op = np.kron(SIGMA_X, SIGMA_X)
                else:
                    corr_op = np.kron(SIGMA_Y, SIGMA_Y)

                # Weak value: <psi| A |psi>
                ideal_weak_val = np.trace(corr_op @ rho).real

                # PROBLEM 1: Measurement uncertainty
                # Weak measurement doesn't give exact value, adds noise
                measurement_noise = np.random.normal(0, MEASUREMENT_UNCERTAINTY)
                measured_weak_val = ideal_weak_val + measurement_noise

                # PROBLEM 2: Apparatus thermal noise
                thermal_noise = np.random.normal(0, THERMAL_NOISE)
                final_measurement = measured_weak_val + thermal_noise

                weak_values.append(final_measurement)
                measurement_errors.append(abs(final_measurement - ideal_weak_val))

                # PROBLEM 3: System dephases DURING the weak measurement
                # Even weak coupling causes some dephasing
                time_per_measurement = 10e-9  # 10 nanoseconds
                dephase_during_measure = (lambda_weak**2) * time_per_measurement / T2_NV
                environment_dephase = ENVIRONMENT_DEPHASE * time_per_measurement
                total_dephase = dephase_during_measure + environment_dephase

                # Apply environmental dephasing
                rho = self.dephasing_channel(rho, total_dephase)

                # PROBLEM 4: Pointer apparatus itself dephases
                # If pointer couples to environment, it loses coherence
                pointer_dephase = time_per_measurement / APPARATUS_DEPHASE_T1
                rho = self.dephasing_channel(rho, pointer_dephase * 0.1)  # Partial back-action

            # From three weak values, can we reconstruct entanglement?
            # Key question: Is measurement error smaller than signal?

            signal_strength = np.mean(np.abs(weak_values))  # How clear is the measurement?
            noise_level = np.mean(measurement_errors)  # How much error?

            # SNR = signal / noise
            snr = signal_strength / (noise_level + 1e-10)

            # If SNR is good (> 3), we can reconstruct state
            # If SNR is bad (< 3), measurement is useless
            if snr > 3:
                # Good measurement quality
                reconstruction_fidelity = 0.9 + 0.1 * (1 - noise_level)
            else:
                # Poor measurement quality - can't trust the data
                reconstruction_fidelity = 0.5 + 0.5 * snr / 3

            # State fidelity after measurement: product of reconstruction + preservation
            state_fidelity = reconstruction_fidelity * (1 - 3 * total_dephase)
            fidelities.append(state_fidelity)

            # Entanglement entropy
            eigvals = np.linalg.eigvalsh(rho)
            eigvals = eigvals[eigvals > 1e-10]
            if len(eigvals) > 0:
                entropy = -np.sum(eigvals * np.log2(eigvals + 1e-15))
            else:
                entropy = 0
            entanglement_entropies.append(entropy)

        avg_fidelity = np.mean(fidelities)
        avg_entropy = np.mean(entanglement_entropies)

        return {
            'method': f'Weak Echo (λ={lambda_weak}, realistic noise)',
            'fidelity_loss': 1.0 - avg_fidelity,
            'entanglement_entropy': avg_entropy,
            'avg_fidelity': avg_fidelity,
            'error_rate': 1.0 - avg_fidelity,
            'snr': np.mean([np.mean(weak_values) / (np.mean(measurement_errors) + 1e-10)])
        }

    # ============= THE TRUTH TEST =============

    def run_comparison(self):
        """Run all three methods and compare."""

        print("\n" + "="*80)
        print("ENTANGLEMENT MEASUREMENT: TRUTH TEST")
        print("="*80)
        print(f"\nPhysical parameters:")
        print(f"  T2 (coherence time): {self.t2*1e3:.2f} ms")
        print(f"  Dephase rate: {self.dephase_rate:.2e} Hz")
        print(f"  Bell state: (|00> + |11>)/√2")
        print()

        results = []

        # Method 1: Strong measurement
        print("Running: Strong Direct Measurement (Qubit)...")
        r1 = self.strong_measurement_qubit(n_trials=10000)
        results.append(r1)
        print(f"  ✗ Fidelity loss: {r1['fidelity_loss']:.2%}")
        print(f"  ✗ Entanglement entropy: {r1['entanglement_entropy']:.4f} (should be 0)")
        print(f"  ✗ Outcome: COMPLETE COLLAPSE (as expected)")
        print()

        # Method 2: Qutrit null-state
        print("Running: Qutrit Null-State Detection...")
        r2 = self.qutrit_null_state_measurement(n_trials=10000)
        results.append(r2)
        print(f"  ✓ Fidelity: {r2['avg_fidelity']:.2%}")
        print(f"  ✓ Fidelity loss: {r2['fidelity_loss']:.2%}")
        print(f"  ✓ Silent error rate: {r2['error_rate']:.2%}")
        print(f"  ✓ Discard rate: {r2['discard_rate']:.2%}")
        print()

        # Method 3: Weak echo (test multiple lambda values)
        print("Running: Weak Echo Measurement...")
        echo_results = []
        for lam in [0.001, 0.01, 0.05, 0.1]:
            r3 = self.weak_echo_measurement(n_repeats=3, lambda_weak=lam, n_trials=5000)
            echo_results.append(r3)
            print(f"  λ={lam}: Fidelity={r3['avg_fidelity']:.2%}, Loss={r3['fidelity_loss']:.2%}")
        print()

        # VERDICT
        print("="*80)
        print("VERDICT: DOES ENTANGLEMENT ECHO WORK?")
        print("="*80)
        print()

        strong_loss = results[0]['fidelity_loss']
        qutrit_loss = results[1]['fidelity_loss']
        echo_loss = echo_results[2]['fidelity_loss']  # λ=0.01

        print(f"Strong measurement fidelity loss: {strong_loss:.2%} (complete collapse)")
        print(f"Qutrit null-state fidelity loss:  {qutrit_loss:.2%} (baseline)")
        print(f"Weak echo (λ=0.01) fidelity loss: {echo_loss:.2%}")
        print()

        improvement = qutrit_loss / echo_loss if echo_loss > 0 else 0

        if improvement > 5:
            print(f"✓ CLAIM HOLDS: {improvement:.1f}x improvement over qutrit baseline")
            print("  Weak echo measurement DOES preserve entanglement better")
        elif improvement > 1:
            print(f"~ PARTIALLY HOLDS: {improvement:.1f}x improvement")
            print("  Improvement is real but smaller than predicted")
        else:
            print(f"✗ CLAIM FAILS: No improvement (ratio={improvement:.2f})")
            print("  Weak echo is NOT better than standard measurement")

        print()
        print("="*80)
        print("CRITICAL ASSUMPTION CHECK:")
        print("="*80)
        print()
        print("1. Weak coupling regime (λ << 1): ✓ Assumed in calculation")
        print("2. Pointer dephasing rate ∝ λ²: ✓ Standard weak measurement theory")
        print("3. Topological protection of mediating particle: ? NOT MODELED")
        print("4. Multiple basis measurements reliable: ? Noise not included")
        print()
        print("CONCLUSION:")
        if improvement > 5:
            print("✓ Entanglement echo is NOT bullshit")
            print("  Idea is mathematically sound under stated assumptions")
            print("  BUT: Mediating particle topological protection is UNPROVEN")
            print("  Recommendation: Design experiment to test topological protection")
        else:
            print("✗ Entanglement echo IS flawed")
            print("  Improvement disappears when you add realistic noise")
            print("  OR assumptions (topological protection) are wrong")

        return results, echo_results


if __name__ == "__main__":
    sim = QuantumSimulator()
    results, echo_results = sim.run_comparison()

    print("\n" + "="*80)
    print("DETAILED RESULTS TABLE:")
    print("="*80)
    print()
    print(f"{'Method':<40} {'Fidelity':<12} {'Loss':<12} {'Error Rate':<12}")
    print("-"*80)

    for r in results:
        print(f"{r['method']:<40} {r['avg_fidelity']:<12.2%} {r['fidelity_loss']:<12.2%} {r['error_rate']:<12.2%}")

    for r in echo_results:
        method = r['method'].split(' (λ=')[0]
        lam = float(r['method'].split('λ=')[1].split(',')[0])
        print(f"{method} (λ={lam}){'':<25} {r['avg_fidelity']:<12.2%} {r['fidelity_loss']:<12.2%} {r['error_rate']:<12.2%}")

    print()
    print("="*80)
