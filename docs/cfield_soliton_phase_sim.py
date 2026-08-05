"""
C-Field Phase Opposition Simulation
=====================================
Reproduces the UFCP "cotton candy" simulation from Not-Math v2.0 Section 10,
then tests whether a phase-flipped soliton drifts in the opposite direction.

Setup:
  - Background coherence field with density that fades toward boundaries
    (models a gravitational density gradient)
  - Soliton placed at mid-region where density is thinning
  - Run 1: Normal phase (phi=0) — expect inward drift (gravity)
  - Run 2: Opposite phase (phi=pi) — does it drift outward (antigravity)?

Physics: Focusing nonlinear Schrodinger equation (UFCP Eq 8):
  i*hbar * d_t(psi) = -(hbar^2/2m) * nabla^2(psi) - lambda*|psi|^2*psi

With background envelope that creates the density gradient.

The soliton solution: psi = eta * sech(eta * x) * exp(i*eta^2*t/2)
"""

import numpy as np

# ==============================================================
# Simulation parameters
# ==============================================================
# Grid
N = 2048            # spatial points
L = 80.0            # domain size
dx = L / N
x = np.linspace(-L/2, L/2, N)

# Time
dt = 0.001          # time step
T_final = 20.0      # total simulation time
n_steps = int(T_final / dt)
save_interval = int(n_steps / 100)  # save 100 snapshots

# Physics (natural units: hbar=1, m=1)
hbar = 1.0
m = 1.0
lam = 1.0           # self-interaction strength (focusing)

print("=" * 60)
print("C-FIELD SOLITON PHASE OPPOSITION SIMULATION")
print("=" * 60)
print(f"Grid: {N} points, L={L}, dx={dx:.4f}")
print(f"Time: T={T_final}, dt={dt}, steps={n_steps}")

# ==============================================================
# Background coherence field (the "cotton candy")
# ==============================================================
# Creates a density gradient: dense in center, fading at edges
# This IS the gravitational field in UFCP
# Using a smooth envelope: rho_bg(x) = rho_0 * exp(-x^2 / (2*sigma^2))

sigma_bg = 20.0     # width of background density
rho_0 = 1.0         # peak background density

background_envelope = rho_0 * np.exp(-x**2 / (2 * sigma_bg**2))

print(f"\nBackground: Gaussian envelope, sigma={sigma_bg}, rho_0={rho_0}")
print(f"  Center density:  {background_envelope[N//2]:.4f}")
print(f"  Edge density:    {background_envelope[0]:.6f}")

# ==============================================================
# Soliton initial condition
# ==============================================================
# Place soliton at x_0 (off-center, in the gradient region)
x_0 = 15.0          # initial soliton position (in the thinning region)
eta = 1.0            # soliton amplitude/inverse width
v_0 = 0.0            # initial velocity (start at rest)

def make_soliton(x, x_0, eta, phase_offset=0.0, v_0=0.0):
    """Create a soliton with given position, amplitude, phase, velocity."""
    soliton = eta * np.cosh(eta * (x - x_0))**(-1)  # sech profile
    # Apply phase: exp(i * (phase_offset + v_0 * x))
    # v_0*x gives the soliton a kick (momentum)
    phase = np.exp(1j * (phase_offset + v_0 * x))
    return soliton * phase

# ==============================================================
# Split-step Fourier method for NLS evolution
# ==============================================================
# i * d_t(psi) = -0.5 * d_xx(psi) - lambda * |psi|^2 * psi + V(x) * psi
#
# V(x) is the effective potential from the background density gradient.
# In UFCP, the background creates a potential through the W kernel:
# V_eff(x) = -lambda * rho_background(x)
# (density-density coupling: the soliton is attracted to higher background density)

k = 2 * np.pi * np.fft.fftfreq(N, d=dx)
kinetic_phase = np.exp(-0.5j * (hbar / (2*m)) * k**2 * dt)

# Background potential (W kernel coupling)
# The soliton feels the background density as an attractive potential
V_background = -lam * background_envelope

def evolve(psi_init, n_steps, dt, track_position=True):
    """Evolve psi using split-step Fourier method."""
    psi = psi_init.copy()
    positions = []
    times = []
    densities_at_snapshots = []

    for step in range(n_steps):
        t = step * dt

        # Track soliton center of mass
        if track_position and step % save_interval == 0:
            density = np.abs(psi)**2
            # Subtract background to isolate soliton
            soliton_density = density - background_envelope
            soliton_density = np.maximum(soliton_density, 0)  # clip negatives

            total = np.sum(soliton_density) * dx
            if total > 1e-10:
                x_cm = np.sum(x * soliton_density) * dx / total
            else:
                x_cm = float('nan')

            positions.append(x_cm)
            times.append(t)

        # Split-step: half nonlinear -> full kinetic -> half nonlinear
        # Nonlinear + potential step (half)
        nonlinear_phase = np.exp(-1j * dt/2 * (-lam * np.abs(psi)**2 + V_background))
        psi = nonlinear_phase * psi

        # Kinetic step (full) in Fourier space
        psi_k = np.fft.fft(psi)
        psi_k = kinetic_phase * psi_k
        psi = np.fft.ifft(psi_k)

        # Nonlinear + potential step (half)
        nonlinear_phase = np.exp(-1j * dt/2 * (-lam * np.abs(psi)**2 + V_background))
        psi = nonlinear_phase * psi

    return psi, np.array(times), np.array(positions)

# ==============================================================
# Run 1: Normal phase (phi = 0) — should drift INWARD (gravity)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 1: NORMAL PHASE (phi = 0)")
print(f"{'='*60}")

psi_normal = make_soliton(x, x_0, eta, phase_offset=0.0) + np.sqrt(background_envelope)
# Actually, let's keep soliton and background separate to track properly
# The total field is background + soliton perturbation
# But NLS is nonlinear so we can't just superpose.
#
# Better approach: initialize with soliton ON TOP of background
# psi = sqrt(rho_bg) + soliton
# The soliton's density adds to the background

psi_normal = np.sqrt(background_envelope) + make_soliton(x, x_0, eta, phase_offset=0.0)

print(f"Soliton at x_0 = {x_0}")
print(f"Phase offset = 0")
print(f"Initial density at soliton peak: {np.abs(psi_normal[N//2 + int(x_0/dx)])**2:.4f}")

psi_final_normal, times_normal, pos_normal = evolve(psi_normal, n_steps, dt)

drift_normal = pos_normal[-1] - pos_normal[0] if len(pos_normal) > 1 else 0
print(f"Initial position: {pos_normal[0]:.4f}")
print(f"Final position:   {pos_normal[-1]:.4f}")
print(f"Drift:            {drift_normal:.4f} ({'inward' if drift_normal < 0 else 'outward'})")

# ==============================================================
# Run 2: Opposite phase (phi = pi) — does it drift OUTWARD?
# ==============================================================
print(f"\n{'='*60}")
print("RUN 2: OPPOSITE PHASE (phi = pi)")
print(f"{'='*60}")

psi_opposite = np.sqrt(background_envelope) + make_soliton(x, x_0, eta, phase_offset=np.pi)

print(f"Soliton at x_0 = {x_0}")
print(f"Phase offset = pi")
print(f"Initial density at soliton peak: {np.abs(psi_opposite[N//2 + int(x_0/dx)])**2:.4f}")

psi_final_opposite, times_opposite, pos_opposite = evolve(psi_opposite, n_steps, dt)

drift_opposite = pos_opposite[-1] - pos_opposite[0] if len(pos_opposite) > 1 else 0
print(f"Initial position: {pos_opposite[0]:.4f}")
print(f"Final position:   {pos_opposite[-1]:.4f}")
print(f"Drift:            {drift_opposite:.4f} ({'inward' if drift_opposite < 0 else 'outward'})")

# ==============================================================
# Run 3: Control — no soliton, just background (should be stable)
# ==============================================================
print(f"\n{'='*60}")
print("RUN 3: CONTROL — Background only (no soliton)")
print(f"{'='*60}")

psi_control = np.sqrt(background_envelope).astype(complex)
norm_before = np.sum(np.abs(psi_control)**2) * dx
psi_final_control, _, _ = evolve(psi_control, n_steps, dt, track_position=False)
norm_after = np.sum(np.abs(psi_final_control)**2) * dx
print(f"Norm conservation: {norm_before:.6f} -> {norm_after:.6f} (delta={abs(norm_after-norm_before):.2e})")

density_before = np.abs(psi_control)**2
density_after = np.abs(psi_final_control)**2
max_change = np.max(np.abs(density_after - density_before))
print(f"Max density change: {max_change:.6e}")
print(f"Background stability: {'STABLE' if max_change < 0.01 else 'UNSTABLE'}")

# ==============================================================
# Run 4: Phase = pi/2 — intermediate, should drift less
# ==============================================================
print(f"\n{'='*60}")
print("RUN 4: INTERMEDIATE PHASE (phi = pi/2)")
print(f"{'='*60}")

psi_half = np.sqrt(background_envelope) + make_soliton(x, x_0, eta, phase_offset=np.pi/2)

psi_final_half, times_half, pos_half = evolve(psi_half, n_steps, dt)

drift_half = pos_half[-1] - pos_half[0] if len(pos_half) > 1 else 0
print(f"Initial position: {pos_half[0]:.4f}")
print(f"Final position:   {pos_half[-1]:.4f}")
print(f"Drift:            {drift_half:.4f} ({'inward' if drift_half < 0 else 'outward'})")

# ==============================================================
# Summary
# ==============================================================
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"")
print(f"  Phase = 0 (normal):     drift = {drift_normal:+.4f} ({'INWARD — gravity' if drift_normal < 0 else 'OUTWARD — antigravity' if drift_normal > 0 else 'NONE'})")
print(f"  Phase = pi/2 (half):    drift = {drift_half:+.4f} ({'INWARD — gravity' if drift_half < 0 else 'OUTWARD — antigravity' if drift_half > 0 else 'NONE'})")
print(f"  Phase = pi (opposite):  drift = {drift_opposite:+.4f} ({'INWARD — gravity' if drift_opposite < 0 else 'OUTWARD — antigravity' if drift_opposite > 0 else 'NONE'})")
print(f"")

if drift_normal < -0.01 and drift_opposite > 0.01:
    print(f"  RESULT: Phase opposition REVERSES gravitational drift!")
    print(f"  The concept works within UFCP dynamics.")
    print(f"  Normal phase -> attracted (falls)")
    print(f"  Opposite phase -> repulsed (rises)")
    ratio = abs(drift_opposite / drift_normal) if abs(drift_normal) > 1e-10 else float('inf')
    print(f"  Drift ratio (opposite/normal): {ratio:.2f}")
elif drift_normal < -0.01 and drift_opposite < -0.01:
    print(f"  RESULT: Both phases drift inward.")
    print(f"  Phase does NOT affect gravitational coupling in this model.")
    print(f"  The concept does NOT work as proposed.")
    ratio = drift_opposite / drift_normal if abs(drift_normal) > 1e-10 else 1.0
    print(f"  Drift ratio: {ratio:.2f} (1.0 = identical, <1.0 = reduced gravity)")
elif abs(drift_normal) < 0.01:
    print(f"  RESULT: No significant drift detected in either case.")
    print(f"  May need longer simulation time, different parameters,")
    print(f"  or stronger background gradient.")
else:
    print(f"  RESULT: Unexpected behavior — needs investigation.")
    print(f"  Normal drift direction: {'inward' if drift_normal < 0 else 'outward'}")
    print(f"  Opposite drift direction: {'inward' if drift_opposite < 0 else 'outward'}")

# ==============================================================
# Detailed trajectory output
# ==============================================================
print(f"\n{'='*60}")
print("TRAJECTORY DATA (every 10th sample)")
print(f"{'='*60}")
print(f"{'Time':>8} | {'Normal (phi=0)':>14} | {'Half (phi=pi/2)':>15} | {'Opposite (phi=pi)':>17}")
print(f"{'-'*8}-+-{'-'*14}-+-{'-'*15}-+-{'-'*17}")

step = max(1, len(times_normal) // 20)
for i in range(0, len(times_normal), step):
    t = times_normal[i]
    p_n = pos_normal[i] if i < len(pos_normal) else float('nan')
    p_h = pos_half[i] if i < len(pos_half) else float('nan')
    p_o = pos_opposite[i] if i < len(pos_opposite) else float('nan')
    print(f"{t:8.2f} | {p_n:14.4f} | {p_h:15.4f} | {p_o:17.4f}")
