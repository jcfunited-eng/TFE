"""
ch4_uf_kernel_v2.py — CH4 conformant kernel realization v2 (side channel)
=========================================================================

The v2 build ordered by Joe 2026-07-30 ("go") after the spec-conformance
audit (docs/CH4_KERNEL_SPEC_CONFORMANCE_AUDIT_20260729.md) found five
priority defects in the preserved lineage kernel. Every change below cites
its clause. SIDE WORK ONLY: this module is self-contained, imports nothing
from production, and is used by nothing in production, CH2, or CH3.

FIXES IMPLEMENTED (audit # → clause → realization)
--------------------------------------------------
#1  L0 normalization (UF v1.3 §2.4, §2.3 scale-invariance):
    F̄(t) = log(F(t) + 1e-8). Log transform is §2.4's own named choice;
    epsilon precedented in the in-repo corrected L0.
#4  Relevance axis (v1.3 §2.3 "R(t) = domain relevance"; recovered
    lineage H3 names the financial R axis = attention via volume):
    r(t) = volume(t) / median(volume over trailing 20 bars) — unitless
    attention-burst ratio, trailing-only, W=20 from the registry.
    Missing/zero volume → r = 1 (neutral presence).
#6  Gate boundary (v1.3 §11.2): D(t) = ‖SEV(t) − SEV(t−1)‖ over the full
    six-tuple, with ADAPTIVE threshold and negative-space-flip openings:
        boundary(t) ⟺ D(t)² > mean(D²[t−w..t−1]) ∨ N(t) ≠ N(t−1)
    i.e. τ(t)² = τ₀² + α·Var-form with τ₀ = 0, α = 1 (registry α = 1;
    zero floor = the parameter-free reading). §11.2's Var(SEV[t−w:t]) is
    dimensionally ambiguous in the source (PROVENANCE notes transcription
    artifacts); the declared reading — today's step exceeds the RMS step
    of the trailing w=20 window — is dimensionally coherent, self-scaling
    across price levels, and is exactly "adaptive gate stabilization".
#10 Contrast vector (v1.3 §4.2, §11.4): CV_k = TVR_k − mean(TVR over the
    NEIGHBORING GATES) — same-unit subtraction. Causal neighborhood:
    trailing NEIGH=5 gates incl. current (5 = the registry's only pinned
    neighborhood size, RHO_ROLLING_WINDOW).
#12 Structural score (v1.3 §4.3): S_k = g(σ_k, Curv_k, R_k) — realized
    as the equal-weight mean of the three, each bounded by the in-repo
    precedented self-scaling saturation x̂ = x / (x + mean(x over the
    trailing 5-gate neighborhood)) (form precedented by the corrected
    L0's deviation/(deviation+τ) relevance).
#11 Interpretive weight (v1.3 §4.1: f(TVR, CV, S, ...), ∂w/∂S > 0,
    bounded): w_k = clip((χ̂_k + S_k)/2, 0, 1) where χ̂_k is the gate's
    structural density V_k/T_k under the same trailing-neighborhood
    saturation. Equal weights per the registry's uniform-weight
    convention; monotone in S by construction.
#13 Regimes (v1.3 §4.4, four classes): STABLE / TRANSITIONAL / VOLATILE
    / CHAOTIC classified on (σ̂_k, κ̂_k) — variance and curvature, the
    clause's own two axes — using the in-repo pinned bands 0.25 / 0.75.
#14 Anomaly suppression (v1.3 §4.5, graded): anomaly condition kept from
    the preserved pinned operator (U > 0.8 ∨ δ_g > 2.0); EFFECT changed
    from binary admissibility block to the original's graded damping
    w ← β·w with β = 0.5 (the lineage relevance step's own down-level).
    IAS no longer force-closes the resonance gate; U and hysteresis
    still do (merged ch05 L3 gating retained for those).
#20 Validation plane de-stubbed (v1.3 §11.9): S(UF) = equal-weight mean
    of {Coh, 1−H̄, 1−Var(B), 1−Ū, 1−D̂rift} over the trailing 5-gate
    window (all components bounded [0,1]); replaces the constant-1.0
    stub as the S̄ input to ρ and is recorded on the tape. Blocker
    minima remain unset — no pinned values exist and inventing them
    would be tuning.
#21 Γ pressures completed (merged ch06): Γ = U† + C† + N† + X† − ρ with
    equal unit weights (registry convention); U† = clipped U*, C† = C/4
    (lineage's own normalization), N† = current-gate negative-space
    flag, X† = 1 − χ (cross-horizon inconsistency).
#19 Event tape widened: negative-space onset/release events added (gate
    N-flag transitions). Stability is recorded via S(UF) on every event.
#23 χ graded (merged ch06 formula): χ = 1 − (1/3)Σ_h (1−sgn(Q_h)·
    sgn(Q̄))/2 ∈ {0, 1/3, 2/3, 1}; governance χ_min = 1.0 (pinned) now
    means "full agreement" on the graded scale.

UNCHANGED (conformant per audit): TVR integrals, lattices/C_k/δ_g
(merged ch05); L3 five-term resonance functional, hysteresis, URF; L4
D/M/Rev/U*/P/B recursions (merged ch05); RMM bands / a_n / z_n /
surprise / Q_h readouts and the pinned governance constants θ+ = 0.65,
F_max = 0.45, χ_min = 1.0; ignition/extinction primitives (L3-native).
OUT OF SCOPE (logged single-core degenerate mode per merged ch06):
cluster coherence, temporal anchors, multi-core fusion.

CAUSALITY: identical no-cheat law as v1 — the state at bar t is a
function of bars [0..t] only; all windows trail; endpoint-κ rule holds;
there are NO whole-history normalizations left anywhere (every
normalization is a trailing neighborhood) — the chain is strictly
recursive and incremental with periodic from-scratch self-verification.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- pinned constants (registry / preserved lineage; none invented) -------
W = 20                 # registry variance window
W_R = 20               # relevance window (registry W; H3 uses median-20)
EPS_LOG = 1e-8
LATTICES = ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0))
NEIGH = 5              # pinned neighborhood (RHO_ROLLING_WINDOW)
BAND_LO, BAND_HI = 0.25, 0.75   # pinned regime bands (uf_core)
U_MAX = 0.75
H_MAX = 0.20
EPS_D = 0.00073
ETA_H = 0.10
ETA_IAS = 0.10
XI = 0.10
CHI_B = 0.10
B_MIN, B_MAX = -1.0, 1.0
BETA_IAS = 0.5         # graded damping level (lineage step's down-level)
A_RHO, B_RHO, C_RHO, D_RHO = 0.4, 0.4, 0.1, 0.1
A_DECAY, A_NU, A_PI = 0.99, 0.05, 0.05
A_F, A_M, A_S = 0.90, 0.98, 0.995
B_F, B_M, B_S = 0.1, 0.1, 0.1
H_MF, H_SM = 0.1, 0.1
G_ALL = 0.01
L_F, L_M, L_S = 0.01, 0.01, 0.01
LAMBDA_S = 1.0
ETA_HH = 2.0
THETA_PLUS = 0.65
F_MAX = 0.45
CHI_MIN = 1.0
EPS_TAU_DAYS = 1.0
SELF_CHECK_EVERY = 100


# ---------------------------------------------------------------------------
# L0 — normalized field + six-tuple arrays (interior values static)
# ---------------------------------------------------------------------------

@dataclass
class L0V2:
    F: np.ndarray          # log field
    dF: np.ndarray
    sigma: np.ndarray
    kappa: np.ndarray      # interior; [0] = [n-1] = 0
    r: np.ndarray          # attention ratio
    N: np.ndarray
    boundary: np.ndarray   # static interior boundary flags (D or N-flip)
    perV: np.ndarray
    cs_perV: np.ndarray
    cs_r: np.ndarray
    cs_dF: np.ndarray
    cs_sigma: np.ndarray
    cs_kappa: np.ndarray
    cs_N: np.ndarray


def compute_l0_v2(closes: np.ndarray, volumes: Optional[np.ndarray]) -> L0V2:
    F = np.log(closes.astype(float) + EPS_LOG)
    n = len(F)
    dF = np.zeros(n)
    if n > 1:
        dF[1:] = np.diff(F)

    sigma = np.zeros(n)
    for t in range(n):
        w0 = max(0, t - W + 1)
        win = F[w0 : t + 1]
        sigma[t] = float(np.mean((win - win.mean()) ** 2))

    kappa = np.zeros(n)
    if n > 2:
        kappa[1 : n - 1] = np.abs(F[2:] - 2.0 * F[1 : n - 1] + F[: n - 2])

    r = np.ones(n)
    if volumes is not None:
        v = volumes.astype(float)
        for t in range(n):
            w0 = max(0, t - W_R + 1)
            med = float(np.median(v[w0 : t + 1]))
            r[t] = (v[t] / med) if med > 0 else 1.0

    # negative space on the normalized field (thresholds are the pinned
    # minima; the normalized field makes them meaningful uniformly)
    N = ((sigma < 1e-6) & (np.abs(dF) < 1e-6) & (kappa < 1e-6)).astype(np.int64)

    # #6: interior boundary flags — D(t) = ||SEV(t)-SEV(t-1)|| over the
    # six-tuple; adaptive: D(t)^2 > mean of trailing W squared steps; or
    # negative-space flip. Interior kappa used; each bar's flag is final
    # once bar t+1 exists (same finalization rule as v1).
    step2 = np.zeros(n)
    for t in range(1, n):
        d = (F[t] - F[t - 1], dF[t] - dF[t - 1], sigma[t] - sigma[t - 1],
             kappa[t] - kappa[t - 1], r[t] - r[t - 1], float(N[t] - N[t - 1]))
        step2[t] = sum(x * x for x in d)
    boundary = np.zeros(n, dtype=bool)
    for t in range(1, n - 1):
        w0 = max(1, t - W)
        trail = step2[w0:t]
        thresh = float(np.mean(trail)) if len(trail) else 0.0
        boundary[t] = (step2[t] > thresh) or (N[t] != N[t - 1])

    perV = np.abs(dF) + sigma + kappa   # beta weights = 1 (registry)

    def cs(a):
        out = np.zeros(n + 1)
        np.cumsum(a, out=out[1:])
        return out

    return L0V2(F=F, dF=dF, sigma=sigma, kappa=kappa, r=r, N=N,
                boundary=boundary, perV=perV, cs_perV=cs(perV), cs_r=cs(r),
                cs_dF=cs(dF), cs_sigma=cs(sigma), cs_kappa=cs(kappa),
                cs_N=cs(N.astype(float)))


@dataclass(frozen=True)
class GateV2:
    t_a: int
    t_b: int
    T: float
    V: float
    R: float
    C: int
    delta_g: float
    mu: Tuple[float, float, float]
    N_gate: int
    sigma_g: float      # mean sigma over gate (regime + S inputs)
    kappa_g: float      # mean kappa over gate
    r_g: float          # mean relevance over gate


def gate_from_span_v2(l0: L0V2, t_a: int, t_b: int, last_mu: np.ndarray) -> GateV2:
    ln = t_b - t_a
    T = float(ln)
    V = float(l0.cs_perV[t_b] - l0.cs_perV[t_a])
    R = float(l0.cs_r[t_b] - l0.cs_r[t_a])
    P_list = tuple((int(T // h1), int(V // h2), int(R // h3))
                   for h1, h2, h3 in LATTICES)
    C = len(set(P_list))
    mu = np.array([
        (l0.cs_dF[t_b] - l0.cs_dF[t_a]) / ln,
        (l0.cs_sigma[t_b] - l0.cs_sigma[t_a]) / ln,
        (l0.cs_kappa[t_b] - l0.cs_kappa[t_a]) / ln,
    ])
    delta_g = float(np.linalg.norm(mu - last_mu))
    N_gate = 1 if (l0.cs_N[t_b] - l0.cs_N[t_a]) == ln else 0
    return GateV2(t_a, t_b, T, V, R, C, delta_g,
                  (float(mu[0]), float(mu[1]), float(mu[2])), N_gate,
                  sigma_g=float(mu[1]), kappa_g=float(mu[2]),
                  r_g=R / ln if ln else 1.0)


# ---------------------------------------------------------------------------
# The chain state (strictly recursive + trailing windows; no global norms)
# ---------------------------------------------------------------------------

def _sat_ratio(x: float, neigh_mean: float) -> float:
    """Self-scaling bounded transform x/(x+m) (precedented in-repo)."""
    m = max(neigh_mean, 1e-12)
    return float(x / (x + m))


@dataclass
class ChainV2:
    last_R: float = 0.0
    last_URF: float = 0.0
    last_URF2: float = 0.0
    last_D: int = 0
    last_B: float = 0.0
    a1: float = 0.0
    a2: float = 0.0
    a3: float = 0.0
    x_f: float = 0.0
    x_m: float = 0.0
    x_s: float = 0.0
    prev_ord: Optional[float] = None
    prev_phi: float = 0.0
    prev_reg: Optional[str] = None
    prev_Ngate: Optional[int] = None
    k: int = 0
    # trailing neighborhoods (tuples, length <= NEIGH)
    tvr_tail: Tuple[Tuple[float, float, float], ...] = ()
    sig_tail: Tuple[float, ...] = ()
    kap_tail: Tuple[float, ...] = ()
    rg_tail: Tuple[float, ...] = ()
    chi_tail: Tuple[float, ...] = ()
    cvn_tail: Tuple[float, ...] = ()
    # process tails
    r_tail: Tuple[float, ...] = ()
    s_tail: Tuple[float, ...] = ()
    u_tail: Tuple[float, ...] = ()
    c_tail: Tuple[float, ...] = ()
    # validation-plane tails (trailing 5-gate window)
    g_tail: Tuple[float, ...] = ()
    hyst_tail: Tuple[float, ...] = ()
    b_tail: Tuple[float, ...] = ()
    ustar_tail: Tuple[float, ...] = ()
    drift_tail: Tuple[float, ...] = ()
    fn_tail: Tuple[float, ...] = ()      # trailing W=20 event F_n (prior)
    suf_tail: Tuple[float, ...] = ()     # trailing W=20 event S_UF (prior)

    def copy(self) -> "ChainV2":
        return ChainV2(**vars(self))


@dataclass
class DayStateV2:
    action: str
    ignition: int
    extinction: int
    Q_5: float
    Q_20: float
    Q_60: float
    F_n: float
    chi_n: float
    F_n_z: float
    Q_20_z: float
    chi_z: float
    action_z: str
    action_diamond: str
    S_UF: float
    R_res: float
    URF: float
    x_f: float
    x_m: float
    x_s: float
    rho_n: float
    s_n: float
    D_k: int
    B_k: float
    Rev_k: int
    U_star_k: float
    regime: str
    event_type: str
    gate_count: int


def _regime_v2(sig_hat: float, kap_hat: float) -> str:
    """#13: four classes on (variance, curvature) with pinned bands."""
    if sig_hat > BAND_HI and kap_hat > BAND_HI:
        return "CHAOTIC"
    if sig_hat > BAND_HI:
        return "VOLATILE"
    if sig_hat < BAND_LO and kap_hat < BAND_LO:
        return "STABLE"
    return "TRANSITIONAL"


def step_chain_v2(st: ChainV2, g: GateV2, date_ord: float) -> DayStateV2:
    """Advance the conformant chain by one gate. Mutates st."""
    # trailing neighborhoods including current gate (#10 causal reading)
    tvr_tail = (st.tvr_tail + ((g.T, g.V, g.R),))[-NEIGH:]
    sig_tail = (st.sig_tail + (g.sigma_g,))[-NEIGH:]
    kap_tail = (st.kap_tail + (g.kappa_g,))[-NEIGH:]
    rg_tail = (st.rg_tail + (g.r_g,))[-NEIGH:]

    # --- L2 (#10 coherent CV; #12 S from sigma/curv/relevance; #11 w;
    #        #13 regimes; #14 graded IAS)
    tvr_mean = np.mean(np.array(tvr_tail), axis=0)
    CV = np.array([g.T, g.V, g.R]) - tvr_mean
    cvn = float(np.linalg.norm(CV))
    cvn_tail = (st.cvn_tail + (cvn,))[-NEIGH:]

    sig_hat = _sat_ratio(g.sigma_g, float(np.mean(sig_tail)))
    kap_hat = _sat_ratio(g.kappa_g, float(np.mean(kap_tail)))
    r_hat = _sat_ratio(g.r_g, float(np.mean(rg_tail)))
    S = float(np.clip((sig_hat + kap_hat + r_hat) / 3.0, 0.0, 1.0))

    chi_density = g.V / max(g.T, 1e-12)
    chi_tail = (st.chi_tail + (chi_density,))[-NEIGH:]
    chi_hat = _sat_ratio(chi_density, float(np.mean(chi_tail)))
    w = float(np.clip(0.5 * (chi_hat + S), 0.0, 1.0))

    U = float(np.clip(0.1 * g.C + 0.1 * g.delta_g + 0.2 * g.N_gate, 0.0, 1.0))
    anomalous = (U > 0.8) or (g.delta_g > 2.0)
    IAS = 1 if anomalous else 0
    if anomalous:
        w = BETA_IAS * w          # #14 graded damping (was binary block)
    Reg = _regime_v2(sig_hat, kap_hat)

    # --- L3 (five-term functional; CV normalized by trailing neighborhood)
    cv_max = max(max(cvn_tail), 1e-12)
    R_res = (w + (cvn / cv_max) + S + 1.0 / (1.0 + g.C) + (1.0 - U)) / 5.0
    Hyst = 1 if abs(R_res - st.last_R) > H_MAX else 0
    g_adm = 1 if (U <= U_MAX and Hyst == 0) else 0    # IAS damping is graded now
    URF = g_adm * R_res

    ignition = 1 if (URF > 0.0 and st.last_URF == 0.0 and st.last_URF2 == 0.0) else 0
    extinction = 1 if (URF == 0.0 and st.last_URF > 0.0 and st.last_URF2 > 0.0) else 0

    # --- L4 (unchanged recursions)
    delta_R = URF - st.last_URF
    D_dir = 1 if delta_R > EPS_D else (-1 if delta_R < -EPS_D else 0)
    M = URF - 2.0 * st.last_URF + st.last_URF2
    U_star = U + ETA_H * Hyst + ETA_IAS * IAS
    Rev = 1 if (D_dir * st.last_D < 0) else 0
    B = float(np.clip(st.last_B + XI * (1.0 - U_star) * delta_R - CHI_B * U_star,
                      B_MIN, B_MAX))

    # --- validation plane S(UF) (#20), trailing 5-gate window
    g_tail = (st.g_tail + (float(g_adm),))[-NEIGH:]
    hyst_tail = (st.hyst_tail + (float(Hyst),))[-NEIGH:]
    b_tail = (st.b_tail + (B,))[-NEIGH:]
    ustar_tail = (st.ustar_tail + (float(np.clip(U_star, 0, 1)),))[-NEIGH:]
    drift_tail = (st.drift_tail + (g.delta_g,))[-NEIGH:]
    coh = float(np.mean(g_tail))
    h_bar = float(np.mean(hyst_tail))
    var_b = float(np.var(np.array(b_tail)))          # B in [-1,1] → var <= 1
    u_bar = float(np.mean(ustar_tail))
    drift_hat = _sat_ratio(g.delta_g, float(np.mean(drift_tail)))
    S_UF = float(np.clip((coh + (1 - h_bar) + (1 - var_b) + (1 - u_bar)
                          + (1 - drift_hat)) / 5.0, 0.0, 1.0))

    # --- L5 process quantities (S̄ now S(UF), de-stubbed)
    delta_tau = EPS_TAU_DAYS if st.prev_ord is None else max(EPS_TAU_DAYS, date_ord - st.prev_ord)
    omega = (2.0 * math.pi) / delta_tau
    phi = (st.prev_phi + omega * delta_tau) % (2.0 * math.pi)

    if st.k == 0:
        event_type = "gate_close"
    elif st.prev_Ngate is not None and g.N_gate != st.prev_Ngate:
        event_type = "negative_space_onset" if g.N_gate == 1 else "negative_space_release"
    elif st.prev_reg is not None and Reg != st.prev_reg:
        event_type = "regime_change"
    elif Rev > 0:
        event_type = "resonance_reversal"
    else:
        event_type = "gate_close"

    r_norm = float(np.clip(R_res, -1.0, 1.0))
    u_value = float(np.clip(U_star, 0.0, 1.0))
    c_norm = float(np.clip(g.C / 4.0, 0.0, 1.0))

    r_tail = (st.r_tail + (r_norm,))[-NEIGH:]
    s_tail = (st.s_tail + (S_UF,))[-NEIGH:]
    u_tail = (st.u_tail + (u_value,))[-NEIGH:]
    c_tail = (st.c_tail + (c_norm,))[-NEIGH:]
    rho = float(np.clip(
        A_RHO * (sum(r_tail) / len(r_tail)) + B_RHO * (sum(s_tail) / len(s_tail))
        - C_RHO * (sum(u_tail) / len(u_tail)) - D_RHO * (sum(c_tail) / len(c_tail)),
        0.0, 1.0))

    nu0 = max(-1.0, min(1.0, float(D_dir)))
    nu1 = max(-1.0, min(1.0, float(M)))
    nu2 = max(-1.0, min(1.0, r_norm))

    a1 = max(-1.0, min(1.0, A_DECAY * st.a1 + A_NU * nu0 + A_PI * rho))
    a2 = max(-1.0, min(1.0, A_DECAY * st.a2 + A_NU * nu1 + A_PI * rho))
    a3 = max(-1.0, min(1.0, A_DECAY * st.a3 + A_NU * nu2 + A_PI * rho))

    x_f = max(-1.0, min(1.0, A_F * st.x_f + B_F * nu0 + G_ALL * rho + L_F * a1))
    x_m = max(-1.0, min(1.0, A_M * st.x_m + B_M * nu1 + H_MF * x_f + G_ALL * rho + L_M * a2))
    x_s = max(-1.0, min(1.0, A_S * st.x_s + B_S * nu2 + H_SM * x_m + G_ALL * rho + L_S * a3))

    surprise = math.sqrt((nu0 - x_f) ** 2 + (nu1 - x_m) ** 2 + (nu2 - x_s) ** 2)

    # horizon heads first (χ needs them), then Γ with X† = 1 − χ (#21, #23)
    # NOTE: Q_h and F_n are simultaneous in ch06; the tape's F_n enters Q_h.
    # Resolve per ch06 order: F_n = Γ + λ_s·s with Γ's X† from the PREVIOUS
    # coherence is circular; ch06 defines χ from Q signs and F_n from Γ(s,ρ,…)
    # without χ. Fidelity: compute Γ's X† from the Q-signs of the CURRENT z
    # WITHOUT the F_n shift (pure readouts q_h·z), which ch06 permits as the
    # H_h(z_n) reading; then F_n, then the shifted Q_h for actions.
    q_raw = (x_f, x_m, x_s)
    q_bar_raw = sum(q_raw) / 3.0
    chi_raw = 1.0 - sum((1 - np.sign(q) * np.sign(q_bar_raw)) / 2 for q in q_raw) / 3.0

    # #21 — two DECLARED readings of Γ, both filed, neither tuned:
    #   raw:  Γ = ΣλᵢPᵢ − λρ·ρ with λ = 1 (the literal ch06 sum). Its scale
    #         ([−1, 4]) is provably incompatible with the pinned action
    #         constants (F_max = 0.45), which were calibrated against the
    #         deployed one-term Γ — the incompatibility that drove the
    #         deployed system to gut three pressure terms.
    #   z:    Γ_z = Γ / Σλ (five terms → /5) — the architecture's own
    #         normalization convention, identical to the resonance
    #         functional's 1/Z and S(UF)'s 1/5 in the same spec.
    gamma_sum = (u_value + c_norm + float(g.N_gate) + (1.0 - chi_raw)) - rho
    F_n = float(gamma_sum + LAMBDA_S * surprise)
    F_n_z = float(gamma_sum / 5.0 + LAMBDA_S * surprise)

    q5 = x_f - ETA_HH * F_n
    q20 = x_m - ETA_HH * F_n
    q60 = x_s - ETA_HH * F_n
    q_bar = (q5 + q20 + q60) / 3.0
    chi_n = float(1.0 - sum((1 - np.sign(q) * np.sign(q_bar)) / 2
                            for q in (q5, q20, q60)) / 3.0)   # #23 graded

    q20_z = x_m - ETA_HH * F_n_z
    q5_z = x_f - ETA_HH * F_n_z
    q60_z = x_s - ETA_HH * F_n_z
    qz_bar = (q5_z + q20_z + q60_z) / 3.0
    chi_z = float(1.0 - sum((1 - np.sign(q) * np.sign(qz_bar)) / 2
                            for q in (q5_z, q20_z, q60_z)) / 3.0)

    def _mapping(q20v: float, fnv: float, chiv: float) -> str:
        if chiv < CHI_MIN:
            return "ABSTAIN"
        if q20v > THETA_PLUS and fnv <= F_MAX:
            return "ACCUMULATE"
        if q20v < -THETA_PLUS and fnv <= F_MAX:
            return "AVOID"
        return "HOLD"

    action = _mapping(q20, F_n, chi_n)
    action_z = _mapping(q20_z, F_n_z, chi_z)

    # THE DIAMOND (declared from ch06's joint-admissibility semantics with
    # registry constants only, BEFORE any measurement): the rare
    # configuration where the field is directional, fully coherent,
    # anomaly-free, out of negative space, at LOW free energy and HIGH
    # stability relative to the vertex's own trailing W=20 events (band
    # constants 0.25/0.75 are the registry's pinned quantile bands).
    action_diamond = "HOLD"
    if len(st.fn_tail) >= W:
        fn_lo = float(np.percentile(np.array(st.fn_tail), 25))
        fn_hi = float(np.percentile(np.array(st.fn_tail), 75))
        suf_lo = float(np.percentile(np.array(st.suf_tail), 25))
        suf_hi = float(np.percentile(np.array(st.suf_tail), 75))
        base_ok = (IAS == 0 and g.N_gate == 0 and chi_raw == 1.0)
        if base_ok and D_dir == 1 and F_n <= fn_lo and S_UF >= suf_hi:
            action_diamond = "ACCUMULATE"
        elif base_ok and D_dir == -1 and F_n >= fn_hi and S_UF <= suf_lo:
            action_diamond = "AVOID"


    # mutate
    st.last_R = R_res
    st.last_URF2 = st.last_URF
    st.last_URF = URF
    st.last_D = D_dir
    st.last_B = B
    st.a1, st.a2, st.a3 = a1, a2, a3
    st.x_f, st.x_m, st.x_s = x_f, x_m, x_s
    st.prev_ord = date_ord
    st.prev_phi = phi
    st.prev_reg = Reg
    st.prev_Ngate = g.N_gate
    st.k += 1
    st.tvr_tail, st.sig_tail, st.kap_tail, st.rg_tail = tvr_tail, sig_tail, kap_tail, rg_tail
    st.chi_tail, st.cvn_tail = chi_tail, cvn_tail
    st.r_tail, st.s_tail, st.u_tail, st.c_tail = r_tail, s_tail, u_tail, c_tail
    st.g_tail, st.hyst_tail, st.b_tail = g_tail, hyst_tail, b_tail
    st.ustar_tail, st.drift_tail = ustar_tail, drift_tail
    st.fn_tail = (st.fn_tail + (F_n,))[-W:]
    st.suf_tail = (st.suf_tail + (S_UF,))[-W:]

    return DayStateV2(
        action=action, ignition=ignition, extinction=extinction,
        Q_5=q5, Q_20=q20, Q_60=q60, F_n=F_n, chi_n=chi_n,
        F_n_z=F_n_z, Q_20_z=q20_z, chi_z=chi_z, action_z=action_z,
        action_diamond=action_diamond, S_UF=S_UF,
        R_res=float(R_res), URF=float(URF),
        x_f=x_f, x_m=x_m, x_s=x_s, rho_n=rho, s_n=surprise,
        D_k=D_dir, B_k=B, Rev_k=Rev, U_star_k=float(U_star), regime=Reg,
        event_type=event_type, gate_count=st.k,
    )


# ---------------------------------------------------------------------------
# Causal replay driver (same architecture as v1; no global norms → the
# closed chain is purely append-only, no rebuilds needed)
# ---------------------------------------------------------------------------

def replay_symbol_v2(dates: Sequence, closes: np.ndarray,
                     volumes: Optional[np.ndarray] = None,
                     warmup: int = 60) -> List[Optional[DayStateV2]]:
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    vols = np.asarray(volumes, dtype=float) if volumes is not None else None
    dates_ord = np.array([np.datetime64(d, "D").astype("int64") for d in dates],
                         dtype="float64")
    l0 = compute_l0_v2(closes, vols)
    bounds = np.flatnonzero(l0.boundary)

    closed: List[GateV2] = []
    base = ChainV2()
    out: List[Optional[DayStateV2]] = [None] * n

    made = 0
    for t in range(warmup, n):
        valid_upto = np.searchsorted(bounds, t)   # boundaries strictly < t
        while made < valid_upto:
            b = int(bounds[made])
            t_a = int(bounds[made - 1]) if made >= 1 else 0
            last_mu = np.array(closed[-1].mu) if closed else np.zeros(3)
            gg = gate_from_span_v2(l0, t_a, b, last_mu)
            closed.append(gg)
            step_chain_v2(base, gg, dates_ord[b])
            made += 1

        t_a = int(closed[-1].t_b) if closed else 0
        if t <= t_a:
            out[t] = None
            continue
        last_mu = np.array(closed[-1].mu) if closed else np.zeros(3)
        final_gate = gate_from_span_v2(l0, t_a, t, last_mu)
        st_day = base.copy()
        out[t] = step_chain_v2(st_day, final_gate, dates_ord[t])

        if (t - warmup) % SELF_CHECK_EVERY == 0 or t == n - 1:
            st_ref = ChainV2()
            for gg in closed:
                step_chain_v2(st_ref, gg, dates_ord[gg.t_b])
            ref = step_chain_v2(st_ref, final_gate, dates_ord[t])
            got = out[t]
            if not (ref.action == got.action and abs(ref.Q_20 - got.Q_20) < 1e-9
                    and abs(ref.F_n - got.F_n) < 1e-9):
                raise AssertionError(f"v2 self-check divergence at t={t}")
    return out


def actions_digest_v2(symbol: str, dates, states) -> str:
    payload = json.dumps({
        "symbol": symbol, "engine": "v2",
        "actions": [(str(np.datetime64(d, "D")), s.action if s else None)
                    for d, s in zip(dates, states)],
    }, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def assert_causal_v2(dates, closes, volumes, states, sample) -> None:
    closes = np.asarray(closes, dtype=float)
    vols = np.asarray(volumes, dtype=float) if volumes is not None else None
    for t in sample:
        if states[t] is None:
            continue
        redo = replay_symbol_v2(
            dates[: t + 1], closes[: t + 1],
            vols[: t + 1] if vols is not None else None, warmup=t)[t]
        assert redo is not None, f"causality v2: no state at t={t}"
        ok = (redo.action == states[t].action
              and redo.action_diamond == states[t].action_diamond
              and abs(redo.Q_20 - states[t].Q_20) < 1e-9
              and abs(redo.F_n - states[t].F_n) < 1e-9
              and redo.gate_count == states[t].gate_count)
        assert ok, (f"V2 CAUSALITY VIOLATION t={t}: "
                    f"({redo.action},{redo.Q_20:.6f}) vs "
                    f"({states[t].action},{states[t].Q_20:.6f})")
