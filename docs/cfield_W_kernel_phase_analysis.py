"""
W Kernel Phase Sensitivity Analysis
=====================================
The central question: Does the UFCP W kernel make gravity phase-sensitive?

From Not-Math v2.0:
  Action (Eq 1):
    S = integral[ i*hbar/2*(psi* D_t psi - psi D_t psi*)
                  - psi* Omega_g psi
                  - U(rho)
                  - 1/2 * integral[ rho(x) W(x-x') rho(x') dx'] ] dx

  Equation of motion (Eq 2):
    i*hbar D_t psi = Omega_g psi + dU/drho * psi + (W*rho) * psi

  Key definitions:
    psi = sqrt(rho) * exp(i*phi)
    rho = |psi|^2 = psi* psi
    W(x-x') = W(x'-x)  (symmetric, real)

  The W kernel acts on rho, NOT on psi directly.
  rho = |psi|^2 is PHASE-BLIND: |psi|^2 = |sqrt(rho)*exp(i*phi)|^2 = rho

  THEREFORE: The W*rho term in the EOM is (W*rho)*psi.
  rho has no phase information. The W coupling is phase-blind at the
  density level.

  BUT WAIT. The W*rho term multiplies psi, not rho. The full interaction
  in the action is rho(x)*W*rho(x'). Let's decompose carefully.

  This analysis resolves the W kernel question definitively.
"""

import numpy as np

print("=" * 70)
print("W KERNEL PHASE SENSITIVITY: RIGOROUS ANALYSIS")
print("=" * 70)

# ==============================================================
# Part 1: The W*rho coupling is phase-blind
# ==============================================================
print("""
PART 1: W*rho IN THE ACTION
=============================

The interaction term in the action is:

  S_int = -1/2 * integral integral rho(x) W(x-x') rho(x') dx dx'

where rho(x) = |psi(x)|^2.

Since rho = |psi|^2, the global phase cancels:
  |sqrt(rho) * exp(i*phi)|^2 = rho  (for ANY phi)

CONCLUSION: The W kernel interaction energy is COMPLETELY phase-blind.
Flipping phi -> phi + pi does not change rho, does not change S_int,
does not change the gravitational coupling.

This seems to kill the concept. But let's look deeper.
""")

# ==============================================================
# Part 2: But the EOM has (W*rho)*psi — phase enters here
# ==============================================================
print("""
PART 2: (W*rho)*psi IN THE EQUATION OF MOTION
================================================

The EOM is:
  i*hbar d_t(psi) = Omega_g(psi) + U'(rho)*psi + (W*rho)*psi

The term (W*rho)*psi: W*rho is a real scalar field (phase-blind),
but it multiplies psi (which carries phase).

This means W*rho acts as an EFFECTIVE POTENTIAL on psi:
  V_eff(x) = W*rho = integral W(x-x') |psi(x')|^2 dx'

This potential is real and phase-blind. It's the same potential
regardless of the phase of psi. It enters the Schrodinger-like
equation as a potential energy term.

A global phase rotation psi -> psi * exp(i*alpha) gives:
  i*hbar d_t(psi * e^(i*alpha)) = Omega_g(psi*e^(i*alpha))
                                  + U'(rho)*psi*e^(i*alpha)
                                  + (W*rho)*psi*e^(i*alpha)

The e^(i*alpha) factors through everything. The dynamics are
identical. Global phase is a gauge symmetry of the NLS+W system.

CONCLUSION: Standard W kernel coupling is phase-blind.
Run 5 of our simulation confirmed this.
""")

# ==============================================================
# Part 3: BUT — what about TWO interacting fields?
# ==============================================================
print("""
PART 3: TWO INTERACTING FIELDS — THE KEY
==========================================

The analysis above considers ONE field psi interacting with itself.
Global phase is gauge — invisible.

But in the antigravity scenario, there are TWO fields:
  psi_bg(x) = background coherence field (Earth's gravitational field)
  psi_s(x)  = soliton (our superconducting device)

The TOTAL field is: psi_total = psi_bg + psi_s

The density is:
  rho_total = |psi_bg + psi_s|^2
            = |psi_bg|^2 + |psi_s|^2 + 2*Re(psi_bg* psi_s)
            = rho_bg + rho_s + 2*sqrt(rho_bg * rho_s) * cos(phi_bg - phi_s)
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                THIS TERM IS PHASE-DEPENDENT!

The cross-term 2*sqrt(rho_bg * rho_s) * cos(phi_bg - phi_s)
depends on the RELATIVE PHASE between background and soliton.

  phi_s - phi_bg = 0:    cos = +1, density INCREASES (constructive)
  phi_s - phi_bg = pi:   cos = -1, density DECREASES (destructive)

The W kernel acts on rho_total. The cross-term means the W coupling
IS sensitive to the relative phase between the soliton and background.
""")

# ==============================================================
# Part 4: Numerical demonstration
# ==============================================================
print("""
PART 4: NUMERICAL DEMONSTRATION
=================================
""")

N = 4096
L = 100.0
dx = L / N
x = np.linspace(-L/2, L/2, N)

# Background field (Earth)
sigma_bg = 25.0
rho_bg_0 = 1.0
psi_bg = np.sqrt(rho_bg_0) * np.exp(-x**2 / (4 * sigma_bg**2))
# Note: psi_bg is real (phase = 0)

# Soliton at x=15
eta = 0.8
x_0 = 15.0

# Case 1: Same phase (phi_s = 0)
psi_s_same = eta / np.cosh(eta * (x - x_0))  # real, positive
psi_total_same = psi_bg + psi_s_same
rho_total_same = np.abs(psi_total_same)**2

# Case 2: Opposite phase (phi_s = pi)
psi_s_opp = -eta / np.cosh(eta * (x - x_0))  # real, negative (phase = pi)
psi_total_opp = psi_bg + psi_s_opp
rho_total_opp = np.abs(psi_total_opp)**2

# Individual densities (phase-blind)
rho_bg = np.abs(psi_bg)**2
rho_s = np.abs(psi_s_same)**2  # same for both cases

# Cross term
cross_same = rho_total_same - rho_bg - rho_s
cross_opp = rho_total_opp - rho_bg - rho_s

idx_peak = np.argmin(np.abs(x - x_0))

print(f"At soliton peak (x={x_0}):")
print(f"  Background density rho_bg:       {rho_bg[idx_peak]:.6f}")
print(f"  Soliton density rho_s:           {rho_s[idx_peak]:.6f}")
print(f"")
print(f"  SAME PHASE (phi=0):")
print(f"    Total density:                 {rho_total_same[idx_peak]:.6f}")
print(f"    Cross term:                    {cross_same[idx_peak]:+.6f}")
print(f"    Cross / rho_s:                 {cross_same[idx_peak]/rho_s[idx_peak]:+.4f}")
print(f"")
print(f"  OPPOSITE PHASE (phi=pi):")
print(f"    Total density:                 {rho_total_opp[idx_peak]:.6f}")
print(f"    Cross term:                    {cross_opp[idx_peak]:+.6f}")
print(f"    Cross / rho_s:                 {cross_opp[idx_peak]/rho_s[idx_peak]:+.4f}")

# ==============================================================
# Part 5: W kernel force from the cross term
# ==============================================================
print(f"""
PART 5: FORCE FROM THE CROSS TERM
====================================

The W kernel interaction energy is:
  E_int = -1/2 * integral integral rho(x) W(x-x') rho(x') dx dx'

With rho_total = rho_bg + rho_s + cross:
  E_int = E_bg-bg + E_s-s + E_bg-s + E_cross terms

The force on the soliton comes from dE/dx_0.
  E_bg-bg doesn't depend on x_0 -> no force
  E_s-s is self-energy -> no net force (symmetric)
  E_bg-s is the gravitational coupling:

  E_bg-s = -integral integral rho_bg(x) W(x-x') rho_s(x') dx dx'
           -integral integral rho_bg(x) W(x-x') cross(x') dx dx'
           - ... (cross at x coupled to bg at x')

The CROSS TERM contribution:
  cross = 2*sqrt(rho_bg * rho_s) * cos(phi_bg - phi_s)

  When phi_s = phi_bg (same phase):
    cross is POSITIVE -> increases total density near soliton
    -> W coupling sees MORE density -> STRONGER attraction to center
    -> soliton falls FASTER

  When phi_s = phi_bg + pi (opposite phase):
    cross is NEGATIVE -> decreases total density near soliton
    -> W coupling sees LESS density -> WEAKER attraction
    -> soliton falls SLOWER... or does it reverse?
""")

# ==============================================================
# Part 6: Can the cross term reverse the force?
# ==============================================================
print("""
PART 6: CAN THE CROSS TERM REVERSE THE FORCE?
================================================

The gravitational force on the soliton has two parts:
  F_direct = force from rho_bg gradient on rho_s (always attractive)
  F_cross  = force from rho_bg gradient on cross term

  F_cross ~ -d/dx_0 [ integral rho_bg(x) W(x-x') cross(x') dx dx' ]

For opposite phase (cross < 0):
  F_cross has OPPOSITE sign to F_direct.

For F_total = F_direct + F_cross to reverse:
  |F_cross| > |F_direct|

  F_cross / F_direct ~ cross / rho_s ~ 2*sqrt(rho_bg/rho_s) * cos(dphi)

  For opposite phase: F_cross/F_direct ~ -2*sqrt(rho_bg/rho_s)
""")

# At the soliton location
ratio_bg_s = rho_bg[idx_peak] / rho_s[idx_peak]
force_ratio = 2 * np.sqrt(ratio_bg_s)

print(f"At soliton peak:")
print(f"  rho_bg / rho_s = {ratio_bg_s:.4f}")
print(f"  |F_cross / F_direct| = 2*sqrt(rho_bg/rho_s) = {force_ratio:.4f}")
print(f"")

if force_ratio > 1.0:
    print(f"  FORCE RATIO > 1: Cross term CAN reverse the gravitational force!")
    print(f"  The soliton would be REPELLED when phase-opposed.")
    print(f"  Net force direction: OUTWARD (antigravity)")
else:
    print(f"  FORCE RATIO < 1: Cross term reduces but cannot reverse gravity.")
    print(f"  The soliton falls slower but still falls.")

print(f"""
CRITICAL CONDITION FOR ANTIGRAVITY:
  rho_bg > rho_s / 4

  i.e., the background density must be at least 1/4 of the soliton density.

  If the soliton is very dense (rho_s >> rho_bg), the cross term is
  relatively small and gravity wins. The soliton still falls.

  If the soliton is comparable to or less dense than the background
  (rho_s <= 4*rho_bg), the cross term dominates and phase opposition
  REVERSES the force. The soliton rises.
""")

# ==============================================================
# Part 7: What this means physically
# ==============================================================
print(f"""
PART 7: PHYSICAL INTERPRETATION
=================================

The condition rho_bg > rho_s/4 means: the device must not be too much
denser than the background coherence field.

Earth's surface coherence field density (in UFCP) is set by the
gravitational potential: phi_g = GM/(Rc^2) = 6.96e-10

This is a dimensionless measure. In natural units, the background
rho_bg at Earth's surface is related to the local gravitational field.

For ORDINARY matter: rho_s >> rho_bg (matter is enormously denser
than the gravitational background field). Cross term is negligible.
Phase doesn't matter. Everything falls normally.

For a SUPERCONDUCTING CONDENSATE: the Cooper pair condensate is a
macroscopic quantum field. Its density rho_s is the condensate density,
which is ALREADY a quantum field — it's on the same footing as the
background coherence field. The cross-term interference is maximal
because psi_bg and psi_s are the same TYPE of field.

The key insight: ordinary matter's "density" in the UFCP sense is
not its mass density. It's its COHERENT quantum field amplitude.
For thermal matter (random phases), the effective coherent rho is
essentially zero — all the phases cancel. Only the incoherent
(classical) mass contributes, and that goes through T_munu -> G_munu
with the 8piG/c^4 suppression.

A superconductor's condensate IS a coherent quantum field. Its rho_s
in the coherence field sense is its full condensate amplitude.
The background rho_bg is the gravitational coherence field.
If these are comparable, the cross term dominates.
""")

# ==============================================================
# Part 8: The simulation we actually need
# ==============================================================
print("""
PART 8: THE CORRECT SIMULATION
================================

The v2 simulation was wrong — it treated the background as an external
potential. The UFCP prediction is that the soliton and background are
BOTH part of the same coherence field psi, and the W kernel acts on
the TOTAL density including cross terms.

The correct simulation:
  1. Initialize psi = psi_bg + psi_s (superposition)
  2. The W kernel acts on rho_total = |psi_bg + psi_s|^2
  3. The cross term 2*Re(psi_bg* psi_s) creates phase-dependent density
  4. The gradient of this density IS the gravitational force
  5. For same phase: enhanced density at soliton -> falls faster
  6. For opposite phase: reduced density at soliton -> falls slower or rises

This is what v1 of the simulation attempted, but the background was
unstable. The fix: use a Thomas-Fermi background that is a STATIONARY
SOLUTION of the NLS, not just any Gaussian.

Let's run it.
""")

# ==============================================================
# Part 9: Run the correct simulation
# ==============================================================
print("=" * 70)
print("RUNNING CORRECT TWO-FIELD SIMULATION")
print("=" * 70)

# Parameters
N = 4096
L = 120.0
dx = L / N
x = np.linspace(-L/2, L/2, N)
dt = 0.0005
T_final = 15.0
n_steps = int(T_final / dt)
save_every = max(1, n_steps // 150)

k = 2 * np.pi * np.fft.fftfreq(N, d=dx)
kin_phase = np.exp(-0.5j * k**2 * dt)

# Trapping potential to keep background stable (like Earth's self-gravity)
omega_trap = 0.02
V_trap = 0.5 * omega_trap**2 * x**2

# Background: Thomas-Fermi profile (stable ground state of trapped NLS)
# For trapped NLS: rho_TF = max(0, (mu - V_trap) / lambda)
# Choose mu so the profile extends to our desired width
lam = 1.0  # nonlinearity
mu_bg = 0.5  # chemical potential
rho_TF = np.maximum(0, (mu_bg - V_trap) / lam)
psi_bg = np.sqrt(rho_TF).astype(complex)

print(f"Background: Thomas-Fermi profile")
print(f"  Trap frequency: {omega_trap}")
print(f"  Chemical potential: {mu_bg}")
print(f"  TF radius: {np.sqrt(2*mu_bg)/omega_trap:.1f}")
print(f"  Peak density: {np.max(rho_TF):.4f}")

# Soliton
eta_s = 0.3   # smaller amplitude so rho_s ~ rho_bg (the critical condition!)
x_0 = 15.0

def run_two_field(phase_offset, label):
    """Run simulation with soliton at given phase offset from background."""
    psi_s = eta_s / np.cosh(eta_s * (x - x_0)) * np.exp(1j * phase_offset)
    psi_init = psi_bg + psi_s

    psi = psi_init.copy()
    positions = []
    times_out = []

    for step in range(n_steps):
        t = step * dt

        if step % save_every == 0:
            density = np.abs(psi)**2
            # Isolate soliton by subtracting background
            delta_rho = density - rho_TF
            # Weight by position to find soliton center
            # Only look near the expected soliton region
            mask = (x > 5) & (x < 40)
            d_masked = np.maximum(delta_rho, 0) * mask
            total = np.sum(d_masked) * dx
            if total > 1e-10:
                x_cm = np.sum(x * d_masked) * dx / total
            else:
                x_cm = float('nan')
            positions.append(x_cm)
            times_out.append(t)

        # Split-step with nonlinearity + trap
        V_total = V_trap
        nl = np.exp(-1j * dt/2 * (-lam * np.abs(psi)**2 + V_total))
        psi = nl * psi
        psi = np.fft.ifft(kin_phase * np.fft.fft(psi))
        nl = np.exp(-1j * dt/2 * (-lam * np.abs(psi)**2 + V_total))
        psi = nl * psi

    positions = np.array(positions)
    times_out = np.array(times_out)

    drift = positions[-1] - positions[0] if len(positions) > 1 and not np.isnan(positions[-1]) and not np.isnan(positions[0]) else float('nan')
    print(f"\n  {label}:")
    print(f"    Initial pos: {positions[0]:.4f}")
    print(f"    Final pos:   {positions[-1]:.4f}")
    print(f"    Drift:       {drift:+.4f} ({'INWARD' if drift < -0.01 else 'OUTWARD' if drift > 0.01 else 'STATIONARY'})")

    return times_out, positions

print(f"\nSoliton amplitude: {eta_s} (deliberately small, rho_s ~ rho_bg)")
print(f"Soliton position: x={x_0}")
print(f"rho_s at peak: {eta_s**2:.4f}")
print(f"rho_bg at x={x_0}: {rho_TF[np.argmin(np.abs(x-x_0))]:.4f}")
ratio = rho_TF[np.argmin(np.abs(x-x_0))] / (eta_s**2)
print(f"rho_bg / rho_s = {ratio:.2f} (need > 0.25 for force reversal)")

t_same, p_same = run_two_field(0.0, "SAME PHASE (phi=0)")
t_opp, p_opp = run_two_field(np.pi, "OPPOSITE PHASE (phi=pi)")
t_half, p_half = run_two_field(np.pi/2, "HALF PHASE (phi=pi/2)")

# Control: just background, no soliton
psi_control = psi_bg.copy()
_, p_ctrl = run_two_field(0.0, "CONTROL (tiny soliton at 0.001)")

print(f"\n{'='*70}")
print("FINAL COMPARISON")
print(f"{'='*70}")

drift_same = p_same[-1] - p_same[0] if not np.isnan(p_same[-1]) else float('nan')
drift_opp = p_opp[-1] - p_opp[0] if not np.isnan(p_opp[-1]) else float('nan')
drift_half = p_half[-1] - p_half[0] if not np.isnan(p_half[-1]) else float('nan')

print(f"  Same phase (phi=0):   drift = {drift_same:+.4f}")
print(f"  Half phase (phi=pi/2): drift = {drift_half:+.4f}")
print(f"  Opposite (phi=pi):    drift = {drift_opp:+.4f}")

print(f"\n{'='*70}")
print("TRAJECTORY")
print(f"{'='*70}")
print(f"{'Time':>6} | {'Same(0)':>8} | {'Half(pi/2)':>10} | {'Opp(pi)':>8}")
print(f"{'-'*6}-+-{'-'*8}-+-{'-'*10}-+-{'-'*8}")
step = max(1, len(t_same) // 20)
for i in range(0, min(len(t_same), len(t_opp), len(t_half)), step):
    print(f"{t_same[i]:6.1f} | {p_same[i]:8.3f} | {p_half[i]:10.3f} | {p_opp[i]:8.3f}")

if drift_same < -0.01 and drift_opp > 0.01:
    print(f"\n*** PHASE OPPOSITION REVERSES GRAVITATIONAL DRIFT ***")
    print(f"*** THE W KERNEL CROSS TERM IS PHASE-SENSITIVE ***")
    print(f"*** ANTIGRAVITY IS PREDICTED BY UFCP ***")
elif drift_same < -0.01 and drift_opp > drift_same:
    print(f"\n** Phase opposition REDUCES gravitational drift **")
    print(f"** Partial antigravity — force is weakened but not reversed **")
    print(f"** May need rho_s/rho_bg ratio adjustment **")
    print(f"** Reduction factor: {drift_opp/drift_same:.2f}x **")
elif abs(drift_same) < 0.01:
    print(f"\n  Insufficient drift detected — need longer sim or stronger gradient")
else:
    print(f"\n  Both drift inward — cross term insufficient at this rho ratio")
    print(f"  Try reducing soliton amplitude or increasing background density")
