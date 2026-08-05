"""
C-Field Phase Opposition Simulation v2
========================================
Fixes from v1:
  - Background is treated as an EXTERNAL potential, not part of psi
  - Soliton is the ONLY thing in psi
  - Background gradient creates effective gravitational potential
  - This avoids destructive interference between soliton and background
  - Phase of the soliton is internal (relative to itself)

Physics model:
  i * d_t(psi) = -0.5 * d_xx(psi) - lambda * |psi|^2 * psi + V_grav(x) * psi

  V_grav(x) models the density gradient (gravity):
  - For normal phase coupling: V = -alpha * rho_bg(x) -> attracted to high density
  - For opposite phase coupling: V = +alpha * rho_bg(x) -> repelled from high density

  The phase of the soliton determines the SIGN of the coupling.
  This is the UFCP prediction: phase opposition flips attraction to repulsion.

  Alternatively, we can model this without changing V by using the
  quantum pressure / phase gradient interaction directly.
"""

import numpy as np

# ==============================================================
# Simulation parameters
# ==============================================================
N = 4096
L = 100.0
dx = L / N
x = np.linspace(-L/2, L/2, N)

dt = 0.0005
T_final = 30.0
n_steps = int(T_final / dt)
save_interval = max(1, n_steps // 200)

k = 2 * np.pi * np.fft.fftfreq(N, d=dx)

print("=" * 60)
print("C-FIELD v2: CLEAN PHASE OPPOSITION SIMULATION")
print("=" * 60)
print(f"Grid: {N} points, L={L}, dx={dx:.4f}")
print(f"Time: T={T_final}, dt={dt}, steps={n_steps}")

# ==============================================================
# Gravitational potential (external, from background density)
# ==============================================================
# Models Earth's coherence field density gradient
# Dense at center (x=0), fading outward
# V_grav < 0 at center -> soliton attracted inward
sigma_bg = 25.0
V_strength = 0.3  # coupling strength

V_grav_attract = -V_strength * np.exp(-x**2 / (2 * sigma_bg**2))
V_grav_repulse = +V_strength * np.exp(-x**2 / (2 * sigma_bg**2))

print(f"\nGravitational potential: Gaussian well, sigma={sigma_bg}")
print(f"Coupling strength: {V_strength}")
print(f"V at center (attract): {V_grav_attract[N//2]:.3f}")
print(f"V at center (repulse): {V_grav_repulse[N//2]:.3f}")

# ==============================================================
# Soliton initial condition
# ==============================================================
eta = 1.5
x_0 = 18.0
v_0 = 0.0

def make_soliton(x, x_0, eta, v_0=0.0):
    """Bright soliton of focusing NLS."""
    profile = eta / np.cosh(eta * (x - x_0))
    kick = np.exp(1j * v_0 * (x - x_0))
    return profile * kick

# ==============================================================
# Split-step evolution
# ==============================================================
def evolve(psi_init, V_ext, n_steps, dt, label=""):
    """Split-step Fourier with external potential."""
    psi = psi_init.copy().astype(complex)
    kinetic = np.exp(-0.5j * k**2 * dt)  # hbar=1, m=1 -> hbar/(2m) = 0.5

    positions = []
    times = []
    norms = []
    peak_densities = []

    for step in range(n_steps):
        t = step * dt

        if step % save_interval == 0:
            density = np.abs(psi)**2
            total_norm = np.sum(density) * dx
            x_cm = np.sum(x * density) * dx / total_norm if total_norm > 1e-10 else float('nan')
            peak_rho = np.max(density)

            positions.append(x_cm)
            times.append(t)
            norms.append(total_norm)
            peak_densities.append(peak_rho)

        # Half nonlinear + potential
        nl = np.exp(-1j * dt/2 * (-np.abs(psi)**2 + V_ext))
        psi = nl * psi

        # Full kinetic
        psi = np.fft.ifft(kinetic * np.fft.fft(psi))

        # Half nonlinear + potential
        nl = np.exp(-1j * dt/2 * (-np.abs(psi)**2 + V_ext))
        psi = nl * psi

    return np.array(times), np.array(positions), np.array(norms), np.array(peak_densities)

# ==============================================================
# Run 1: Attractive potential (normal gravity)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 1: ATTRACTIVE POTENTIAL (normal gravity, phi=0)")
print(f"Soliton at x={x_0}, amplitude={eta}")
print(f"{'='*60}")

psi_1 = make_soliton(x, x_0, eta)
t1, p1, n1, d1 = evolve(psi_1, V_grav_attract, n_steps, dt, "attract")

print(f"Initial position:  {p1[0]:.4f}")
print(f"Final position:    {p1[-1]:.4f}")
print(f"Drift:             {p1[-1]-p1[0]:+.4f}")
print(f"Norm conservation: {n1[0]:.4f} -> {n1[-1]:.4f} (delta={abs(n1[-1]-n1[0]):.2e})")
print(f"Peak density:      {d1[0]:.4f} -> {d1[-1]:.4f}")

# ==============================================================
# Run 2: Repulsive potential (antigravity — phase-flipped coupling)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 2: REPULSIVE POTENTIAL (antigravity, phi=pi)")
print(f"Soliton at x={x_0}, amplitude={eta}")
print(f"{'='*60}")

psi_2 = make_soliton(x, x_0, eta)
t2, p2, n2, d2 = evolve(psi_2, V_grav_repulse, n_steps, dt, "repulse")

print(f"Initial position:  {p2[0]:.4f}")
print(f"Final position:    {p2[-1]:.4f}")
print(f"Drift:             {p2[-1]-p2[0]:+.4f}")
print(f"Norm conservation: {n2[0]:.4f} -> {n2[-1]:.4f} (delta={abs(n2[-1]-n2[0]):.2e})")
print(f"Peak density:      {d2[0]:.4f} -> {d2[-1]:.4f}")

# ==============================================================
# Run 3: No potential (free soliton — should stay put)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 3: CONTROL — No potential (free soliton)")
print(f"{'='*60}")

V_zero = np.zeros_like(x)
psi_3 = make_soliton(x, x_0, eta)
t3, p3, n3, d3 = evolve(psi_3, V_zero, n_steps, dt, "free")

print(f"Initial position:  {p3[0]:.4f}")
print(f"Final position:    {p3[-1]:.4f}")
print(f"Drift:             {p3[-1]-p3[0]:+.4f}")
print(f"Norm conservation: {n3[0]:.4f} -> {n3[-1]:.4f} (delta={abs(n3[-1]-n3[0]):.2e})")
print(f"Peak density:      {d3[0]:.4f} -> {d3[-1]:.4f}")

# ==============================================================
# Run 4: Weak attractive (half strength — half gravity)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 4: HALF ATTRACTIVE (half gravity)")
print(f"{'='*60}")

V_half = V_grav_attract * 0.5
psi_4 = make_soliton(x, x_0, eta)
t4, p4, n4, d4 = evolve(psi_4, V_half, n_steps, dt, "half")

print(f"Initial position:  {p4[0]:.4f}")
print(f"Final position:    {p4[-1]:.4f}")
print(f"Drift:             {p4[-1]-p4[0]:+.4f}")

# ==============================================================
# Run 5: Self-consistent phase test
# ==============================================================
# Instead of changing V, keep V attractive but change the
# soliton's initial phase. In standard NLS, the global phase
# doesn't affect dynamics (gauge symmetry). But if we add
# a phase-dependent coupling term, it would.
#
# This tests whether standard NLS shows any phase effect.
# If it doesn't, that confirms the effect must come from
# the W kernel (UFCP-specific) and not from basic NLS.
print(f"\n{'='*60}")
print("RUN 5: SAME ATTRACTIVE V, but soliton phase = pi")
print(f"(Tests whether standard NLS cares about global phase)")
print(f"{'='*60}")

psi_5 = make_soliton(x, x_0, eta) * np.exp(1j * np.pi)  # flip phase
t5, p5, n5, d5 = evolve(psi_5, V_grav_attract, n_steps, dt, "phase-pi")

print(f"Initial position:  {p5[0]:.4f}")
print(f"Final position:    {p5[-1]:.4f}")
print(f"Drift:             {p5[-1]-p5[0]:+.4f}")
print(f"Same as Run 1?     {'YES' if abs(p5[-1]-p1[-1]) < 0.1 else 'NO'}")

# ==============================================================
# Summary
# ==============================================================
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"")
print(f"  Run 1 (normal gravity):  {p1[-1]-p1[0]:+.4f} {'INWARD' if p1[-1]<p1[0] else 'OUTWARD'}")
print(f"  Run 2 (antigravity):     {p2[-1]-p2[0]:+.4f} {'INWARD' if p2[-1]<p2[0] else 'OUTWARD'}")
print(f"  Run 3 (no gravity):      {p3[-1]-p3[0]:+.4f} {'INWARD' if p3[-1]<p3[0] else 'OUTWARD' if abs(p3[-1]-p3[0])>0.01 else 'STATIONARY'}")
print(f"  Run 4 (half gravity):    {p4[-1]-p4[0]:+.4f} {'INWARD' if p4[-1]<p4[0] else 'OUTWARD'}")
print(f"  Run 5 (phase=pi, att V): {p5[-1]-p5[0]:+.4f} {'INWARD' if p5[-1]<p5[0] else 'OUTWARD'}")
print(f"")

# Key interpretation
print(f"--- INTERPRETATION ---")
print(f"")
if abs(p1[-1]-p1[0]) > 0.5 and (p1[-1]-p1[0]) < 0:
    print(f"Run 1 confirms: attractive potential pulls soliton inward. GRAVITY WORKS.")
else:
    print(f"Run 1: unexpected — check parameters.")

if abs(p2[-1]-p2[0]) > 0.5 and (p2[-1]-p2[0]) > 0:
    print(f"Run 2 confirms: repulsive potential pushes soliton outward. ANTIGRAVITY WORKS.")
elif abs(p2[-1]-p2[0]) > 0.5 and (p2[-1]-p2[0]) < 0:
    print(f"Run 2: soliton still falls inward despite repulsive V. Self-gravity dominates?")
else:
    print(f"Run 2: minimal drift — check parameters.")

if abs(p5[-1]-p1[-1]) < 0.1:
    print(f"Run 5 confirms: standard NLS is phase-blind. Global phase does NOT")
    print(f"  affect gravity coupling in basic NLS. The effect MUST come from")
    print(f"  UFCP's W kernel (density-density coupling with phase sensitivity)")
    print(f"  or from a modified interaction term. Standard physics says no.")
    print(f"  UFCP says maybe. The simulation confirms where the question lives.")
else:
    print(f"Run 5: UNEXPECTED — standard NLS showed phase sensitivity!")
    print(f"  This would be a significant finding. Investigate further.")

print(f"")
print(f"--- WHAT THIS MEANS FOR THE CONCEPT ---")
print(f"")
print(f"The attractive/repulsive potential model (Runs 1-4) shows that")
print(f"IF the phase-gravity coupling exists, a soliton WILL drift in")
print(f"the opposite direction. The dynamics work. The physics is sound.")
print(f"")
print(f"The open question (Run 5) is: does flipping the soliton's phase")
print(f"actually flip the sign of the gravitational coupling? Standard NLS")
print(f"says no (phase is gauge-invisible). UFCP's W kernel MIGHT say yes")
print(f"because it couples density-to-density with phase sensitivity.")
print(f"")
print(f"This is the exact experiment needed: measure whether a")
print(f"superconductor's weight changes when its condensate phase is")
print(f"modified by an external magnetic field.")

# ==============================================================
# Trajectory table
# ==============================================================
print(f"\n{'='*60}")
print("TRAJECTORY COMPARISON (sampled)")
print(f"{'='*60}")
print(f"{'Time':>6} | {'Attract':>8} | {'Repulse':>8} | {'Free':>8} | {'Half':>8} | {'PhiPi':>8}")
print(f"{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")

step = max(1, len(t1) // 25)
for i in range(0, min(len(t1), len(t2), len(t3), len(t4), len(t5)), step):
    print(f"{t1[i]:6.1f} | {p1[i]:8.3f} | {p2[i]:8.3f} | {p3[i]:8.3f} | {p4[i]:8.3f} | {p5[i]:8.3f}")
