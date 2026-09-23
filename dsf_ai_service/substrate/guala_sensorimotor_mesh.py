"""Constitutive Electromechanical Contact-Conductance Sensorimotor Substrate for Guala.

This module implements the deterministic, energy-accounted sensorimotor bridge
connecting Guala's cochlear ear to her airway vocal articulators.

Constitutive Physics (sections 9-11 of definitive-neuron specification):
1. Persistent Contact Geometry:
   - Contact gap: ell_ij in [ELL_MIN, ELL_0] (micrometers).
   - Asperity contact volume: Omega_0 = 10.0 um^3 (conserved material constant).
   - Conserved volume identity: A_ij * ell_ij == Omega_0 everywhere.
   - Contact area: A_ij = Omega_0 / ell_ij (micrometers squared).
   - Physical contact conductance: g_ij = sigma_mat * Omega_0 / ell_ij^2 (mS).

2. Coupled Mechanical-Electrostatic Equilibrium (Radial Return):
   - Co-active Maxwell electrostatic attractive stress:
     sigma_elec(ell) = 0.5 * epsilon_eff * (coactivity / ell)^2 (Pascals).
   - Solid mechanical compressive yield with isotropic hardening:
     sigma_yield(ell) = Y + H * (ELL_0 - ell) / ELL_0 (Pascals).
   - Equilibrium requires mechanical balance:
     sigma_elec(ell*) = sigma_yield(ell*) + N, where N >= 0 is normal reaction at mechanical stop.
   - For pull-in snap-through to ELL_MIN: normal reaction N >= 0 balances electrostatic stress.
   - For interior equilibrium: f(ell*) = sigma_elec(ell*) - sigma_yield(ell*) = 0,
     solved via Newton-Raphson with exact signed derivative:
     df/dell = -2 * sigma_elec / ell + H / ELL_0.
   - Kuhn-Tucker complementarity and equilibrium residual verified on all 120 junctions.

3. Strict SI Energy Accounting:
   - Volume in m^3: Omega_0_m3 = Omega_0 * 1e-18 m^3.
   - Plastic work: W_p = Y * Omega_0_m3 * ln(ell_prev / ell_new) (Joules).
   - Hardening energy: U_h = 0.5 * H * ((ELL_0 - ell)/ELL_0)^2 * Omega_0_m3 (Joules).
   - Total dissipation tracked in Joules.

4. Continuous Dynamical Conduction & Authentic Rest State:
   - Continuous numerical evolution of leaky membrane potential:
     V(t + dt) = V(t) * exp(-dt / tau_m) + V_eff * (1 - exp(-dt / tau_m)),
     where tau_m = 20 ms, dt = 10 ms. Zero authored frame segmentation (no tau < 8 split).
   - Firing threshold: effectors actuate iff max(V) >= V_threshold.
   - Unpracticed virgin contacts (ell_0) remain below threshold (~0.015 V << 0.22 V), ensuring an authentic
     rest / no-fire state without argmax heuristics.
"""
from __future__ import annotations

import math
from typing import Any, Sequence
import numpy as np

import dsf_ai_service.guala_voice as gv
from dsf_ai_service.guala_acoustic_gate import EAR_BANDS

# Declared airway anatomical degrees of freedom
PITCHES_DECIHERTZ = gv.PITCHES_DECIHERTZ      # (3450, 3600, 3750, 3900)
ONSETS = gv.ONSETS                            # 11 canonical infant articulators
VOWELS = tuple(v[0] for v in gv.VOWELS)       # ('ah', 'eh', 'ee', 'oh', 'oo') - 5 vowels

N_AFFERENT = EAR_BANDS                        # 6 ERB cochlear frequency bands
N_ONSET = len(ONSETS)                         # 11 onset effectors
N_VOWEL = len(VOWELS)                         # 5 vowel cavity effectors
N_PITCH = len(PITCHES_DECIHERTZ)              # 4 pitch effectors
N_EFFERENT = N_ONSET + N_VOWEL + N_PITCH      # 20 total effector degrees of freedom

# Constitutive material constants
ELL_0 = 10.0          # um: baseline undeformed contact gap
ELL_MIN = 1.0         # um: minimum contact gap (mechanical closure stop)
OMEGA_0 = 10.0        # um^3: conserved asperity contact volume
OMEGA_0_M3 = 10.0e-18 # m^3: conserved asperity contact volume in SI units
SIGMA_MAT = 0.05      # mS * um / um^2: specific bulk conductivity of contact asperities

# Electrical circuit parameters
C_NODE = 10.0         # nF: node membrane capacitance
G_LOAD_EFF = 0.30     # mS: efferent mechanical load conductance
V_THRESHOLD = 0.22    # V: effector activation threshold (unpracticed virgin contacts stay ~0.015 V << 0.22 V)

# Plastic yield parameters (Radial Return & Mechanics)
YIELD_STRESS = 100.0  # Pa: material yield stress
HARDENING = 20.0      # Pa: plastic hardening modulus
EPSILON_EFF = 1.0e6   # effective dielectric factor for Maxwell stress
TAU_DECAY = 0.35      # seconds: temporal polarization decay across the sensory cue window
TAU_MEMBRANE = 0.020  # seconds: 20 ms continuous membrane relaxation time constant
DT_FRAME = 0.010      # seconds: 10 ms cochlear frame duration
DECAY_MEMBRANE = math.exp(-DT_FRAME / TAU_MEMBRANE)


def solve_contact_equilibrium(coactivity: float, ell_init: float) -> tuple[float, float, float]:
    """Solves the coupled mechanical-electrostatic contact equilibrium for a single junction.
    Returns:
        ell_star: equilibrium gap in [ELL_MIN, ELL_0].
        normal_reaction: compressive mechanical stop reaction N >= 0 in Pascals.
        residual: equilibrium residual (must be <= 1e-6).
    """
    K = 0.5 * EPSILON_EFF * (coactivity ** 2)
    s0 = K / (ELL_0 ** 2)
    if s0 <= YIELD_STRESS:
        # Elastic regime: stress below yield, contact stays at resting gap
        return ELL_0, 0.0, max(0.0, s0 - YIELD_STRESS)

    s_min = K / (ELL_MIN ** 2)
    y_min = YIELD_STRESS + HARDENING * (ELL_0 - ELL_MIN) / ELL_0

    ell = float(ell_init)
    converged = False
    for _ in range(25):
        s = K / (ell ** 2)
        y = YIELD_STRESS + HARDENING * (ELL_0 - ell) / ELL_0
        f = s - y
        if abs(f) < 1e-6:
            converged = True
            break
        # Exact signed derivative df/dell = -2*K/ell^3 + H/ELL_0
        df = -2.0 * K / (ell ** 3) + HARDENING / ELL_0
        if abs(df) < 1e-12:
            break
        ell_next = ell - f / df
        if ell_next <= ELL_MIN:
            ell = ELL_MIN
            break
        if ell_next >= ELL_0:
            ell = ELL_0
            break
        ell = ell_next

    if ell <= ELL_MIN or not converged:
        # Pull-in snap-through to mechanical closure stop ELL_MIN
        ell = ELL_MIN
        normal_reaction = max(0.0, s_min - y_min)
        residual = max(0.0, y_min - s_min)
        return ell, normal_reaction, residual
    else:
        # Interior equilibrium root
        normal_reaction = 0.0
        residual = abs(K / (ell ** 2) - (YIELD_STRESS + HARDENING * (ELL_0 - ell) / ELL_0))
        return ell, normal_reaction, residual


class GualaSensorimotorMesh:
    """Bounded, recurrent electromechanical sensorimotor path connecting cochlea to airway."""

    def __init__(self, ell: np.ndarray | None = None, theta: np.ndarray | None = None) -> None:
        if ell is not None:
            self.ell = np.array(ell, dtype=np.float64)
        else:
            self.ell = np.full((N_AFFERENT, N_EFFERENT), ELL_0, dtype=np.float64)

        if theta is not None:
            self.theta = np.array(theta, dtype=np.float64)
        else:
            self.theta = np.zeros(N_AFFERENT, dtype=np.float64)

        self.total_plastic_work_joules: float = 0.0
        self.total_hardening_energy_joules: float = 0.0

    @property
    def total_plastic_work(self) -> float:
        """Plastic work dissipation in Joules."""
        return self.total_plastic_work_joules

    @property
    def conductance(self) -> np.ndarray:
        """Physical junction conductances g_ij = sigma_mat * Omega_0 / ell_ij^2 in mS."""
        return SIGMA_MAT * OMEGA_0 / (self.ell ** 2)

    @property
    def area(self) -> np.ndarray:
        """Physical junction contact areas A_ij = Omega_0 / ell_ij in um^2."""
        return OMEGA_0 / self.ell

    def equilibrium_residual(self, coactivity: np.ndarray) -> float:
        """Verifies the coupled mechanical-electrostatic equilibrium residual across all 120 junctions."""
        max_res = 0.0
        for i in range(N_AFFERENT):
            for j in range(N_EFFERENT):
                _l, _n, r = solve_contact_equilibrium(float(coactivity[i, j]), float(self.ell[i, j]))
                max_res = max(max_res, r)
        return float(max_res)

    def step_polarization(self, heard_frames: Sequence[Sequence[float]] | None, dt_beat: float = 0.25) -> None:
        """Updates the afferent temporal polarization trace across organism beats.
        Decays exponentially with time constant TAU_DECAY = 0.35 s.
        If acoustic frames are heard, integrates the normalized cochlear band distribution.
        """
        decay = math.exp(-dt_beat / TAU_DECAY)
        self.theta = self.theta * decay
        if heard_frames:
            band_sum = np.zeros(N_AFFERENT, dtype=np.float64)
            for f in heard_frames:
                energy = float(f[0])
                if energy > 0.0001:
                    band_sum += energy * np.array(f[1:], dtype=np.float64)
            total = float(np.sum(band_sum))
            if total > 0.0:
                normalized = band_sum / total
                self.theta += normalized * 1.5

    def propagate_frames(self, frames: Sequence[Sequence[float]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Continuous chronological conduction across efferent nodes via leaky membrane dynamics.
        Evolves V(t + dt) = V(t) * exp(-dt/tau_m) + V_eff * (1 - exp(-dt/tau_m)).
        Returns peak membrane potentials reached across the continuous acoustic event:
            peak_onset_V: shape (11,)
            peak_vowel_V: shape (5,)
            peak_pitch_V: shape (4,)
        """
        g_mat = self.conductance  # (6, 20)
        g_eff_denom = np.sum(g_mat, axis=0) + G_LOAD_EFF  # (20,)

        V = np.zeros(N_EFFERENT, dtype=np.float64)
        peak_V = np.zeros(N_EFFERENT, dtype=np.float64)

        for frame in frames:
            energy = float(frame[0])
            if energy <= 0.0005:
                V_eff = np.zeros(N_EFFERENT, dtype=np.float64)
            else:
                band_fractions = np.array(frame[1:], dtype=np.float64)
                V_eff = np.dot(band_fractions, g_mat) / g_eff_denom  # (20,)

            # Continuous, unconditionally stable exponential integration
            V = V * DECAY_MEMBRANE + V_eff * (1.0 - DECAY_MEMBRANE)
            peak_V = np.maximum(peak_V, V)

        return peak_V[:N_ONSET], peak_V[N_ONSET:N_ONSET + N_VOWEL], peak_V[N_ONSET + N_VOWEL:]

    def readout(self, frames: Sequence[Sequence[float]]) -> tuple[tuple[int, int, int] | None, str | None, dict[str, Any]]:
        """Physical actuator readout with explicit activation threshold.
        Returns:
            drive: (pitch_decihertz, vowel_index, onset_index) or None if resting.
            syllable_name: e.g. 'mah0' or None if resting.
            info: diagnostic measurement dictionary.
        """
        p_onset, p_vowel, p_pitch = self.propagate_frames(frames)
        max_o = float(np.max(p_onset)) if len(p_onset) else 0.0
        max_v = float(np.max(p_vowel)) if len(p_vowel) else 0.0
        max_p = float(np.max(p_pitch)) if len(p_pitch) else 0.0

        info = {
            "max_onset_v": max_o,
            "max_vowel_v": max_v,
            "max_pitch_v": max_p,
            "v_threshold": V_THRESHOLD,
            "v_onset": [round(float(x), 4) for x in p_onset],
            "v_vowel": [round(float(x), 4) for x in p_vowel],
            "v_pitch": [round(float(x), 4) for x in p_pitch],
        }

        # Authentic Rest State: all three effector groups must reach activation threshold
        if max_o < V_THRESHOLD or max_v < V_THRESHOLD or max_p < V_THRESHOLD:
            return None, None, info

        o_idx = int(np.argmax(p_onset))
        v_idx = int(np.argmax(p_vowel))
        p_idx = int(np.argmax(p_pitch))

        pitch_val = PITCHES_DECIHERTZ[p_idx]
        drive = (pitch_val, v_idx, o_idx)
        name = f"{ONSETS[o_idx]}{VOWELS[v_idx]}{p_idx}"
        return drive, name, info

    def plastic_settle(self, drive: tuple[int, int, int], self_frames: Sequence[Sequence[float]]) -> int:
        """Constitutive radial return plastic update driven by co-activity of
        afferent cue polarization trace and actual motor reafference frames.
        Enforces coupled mechanical-electrostatic equilibrium and material volume conservation.
        """
        pitch_val, v_idx, o_idx = drive
        p_idx = PITCHES_DECIHERTZ.index(pitch_val)

        # Profile timings of the enacted onset
        onset_name = ONSETS[o_idx]
        prof = gv.ONSET_PROFILES.get(onset_name)
        onset_ms = prof['onset_ms'] if prof else 0
        onset_frames = int(round(onset_ms / 10.0))

        coactivity = np.zeros((N_AFFERENT, N_EFFERENT), dtype=np.float64)

        for tau, f in enumerate(self_frames):
            energy = float(f[0])
            if energy <= 0.0001:
                continue
            band_frac = np.array(f[1:], dtype=np.float64)

            # Motor articulation trajectory: onset effector acts during onset duration;
            # vowel cavity shapes phonation following tract opening
            m_eff = np.zeros(N_EFFERENT, dtype=np.float64)
            if tau < onset_frames:
                m_eff[o_idx] = 1.0
            else:
                m_eff[N_ONSET + v_idx] = 1.0
            m_eff[N_ONSET + N_VOWEL + p_idx] = 1.0

            # Causal co-activity
            coactivity += np.outer(self.theta * band_frac, m_eff)

        # Solve coupled mechanical-electrostatic equilibrium across all junctions
        yielded_count = 0
        for i in range(N_AFFERENT):
            for j in range(N_EFFERENT):
                ell_new, _normal_rxn, _res = solve_contact_equilibrium(float(coactivity[i, j]), float(self.ell[i, j]))
                if ell_new < self.ell[i, j]:
                    # Exact closed-form continuum dissipation integral in Joules
                    d_wp = YIELD_STRESS * OMEGA_0_M3 * math.log(self.ell[i, j] / ell_new)
                    strain_new = (ELL_0 - ell_new) / ELL_0
                    strain_old = (ELL_0 - self.ell[i, j]) / ELL_0
                    d_uh = 0.5 * HARDENING * (strain_new ** 2 - strain_old ** 2) * OMEGA_0_M3
                    self.total_plastic_work_joules += d_wp
                    self.total_hardening_energy_joules += d_uh
                    self.ell[i, j] = ell_new
                    yielded_count += 1

        return yielded_count

    def to_dict(self) -> dict[str, Any]:
        """Serializes persistent geometric state for Guala's body storage."""
        return {
            "ell": self.ell.tolist(),
            "theta": self.theta.tolist(),
            "total_plastic_work_joules": float(self.total_plastic_work_joules),
            "total_hardening_energy_joules": float(self.total_hardening_energy_joules),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GualaSensorimotorMesh:
        """Reconstitutes persistent geometric state from Guala's body storage."""
        m = cls(
            ell=np.array(data["ell"], dtype=np.float64) if "ell" in data else None,
            theta=np.array(data["theta"], dtype=np.float64) if "theta" in data else None,
        )
        m.total_plastic_work_joules = float(data.get("total_plastic_work_joules", 0.0))
        m.total_hardening_energy_joules = float(data.get("total_hardening_energy_joules", 0.0))
        return m
