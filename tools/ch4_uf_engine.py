"""
ch4_uf_engine.py — CH4 true-to-original UF engine (side channel, paper only)
============================================================================

MANDATE (Joe, 2026-07-29): CH4 is the true-to-original-design kernel with NO
L0-L4 internals flattened, evaluated over the FULL history and structure of
each ticker, governed by the ch06 L5 interpretation logic. It never touches
production; it feeds only the CH4 side page.

WHAT IS RESTORED vs the deployed (flattened) path
-------------------------------------------------
Deployed today: kernel runs, then everything except the LAST gate's scalars
is discarded; relevance is hardcoded 1.0; "level1/level2" are ordinary
finance stats (vol, drawdown, polyfit trend); L5 is a row-first filter.
Here: the ordered gate trajectory, ISF, resonance sequence, DSF trajectory,
event tape, and the full L5 state recursion (mode amplitude, three-band
resonant memory, latent field, surprise, free structural energy, horizon
heads, cross-horizon coherence, action mapping) are all kept and used, and
the action at every bar is computed from the ENTIRE structure known at that
bar.

KERNEL SEMANTICS
----------------
The preserved faithful lineage (quarantine_historical_kernel.py), verbatim:
pinned KernelParameters; real psi_r relevance (not 1.0); canonical psi_s /
phi_reg / psi_u / phi_ias operators; L0 SEV -> L1 gates (D >= tau_D, forced
close at series end, half-open content slices) -> L2 ISF -> L3 resonance
(hysteresis vs previous gate, admissibility gating) -> L4 DSF over gated
URF (D/M/Rev/U*/B recursions).

Field modes (both declared BEFORE any evaluation run; primary fixed first):
  RAW (primary)  — F = close, exactly as the preserved lineage ran.
  LOG (variant)  — F = log(close) per UF-Spec v1.3.0 §2.4 normalization
                   (monotone, shape-preserving, scale-invariant), same
                   pinned thresholds. Reported alongside, labeled.

L5 GOVERNANCE (ch06 + preserved lineage)
----------------------------------------
Event tape over the gate trajectory (gate_close / regime_change /
resonance_reversal), process quantities (delta_tau, omega, phi, rho), mode
amplitude a_n, RMM bands x_f/x_m/x_s (A=0.90/0.98/0.995 pinned), latent
z_n = (x_f, x_m, x_s), structural surprise s_n, free structural energy
F_n, horizon heads Q_5/Q_20/Q_60 (readout basis e1/e2/e3, eta_h=2.0),
coherence chi_n, and the FULL ch06 action mapping:

    ABSTAIN     chi_n < chi_min
    ACCUMULATE  Q_20 >  theta_plus  and F_n <= F_max
    AVOID       Q_20 < -theta_plus  and F_n <= F_max   (theta_minus :=
                theta_plus, declared symmetric per spec theta_h^{+-})
    HOLD        otherwise

Pinned governance: theta_plus=0.65, F_max=0.45, chi_min=1.0 (lineage
values). N_persist and reversal cooldown: the preserved lineage realized
neither (N_persist=1, no cooldown) — kept as lineage-realized, declared.

CAUSALITY (the no-cheat law)
----------------------------
The daily action at bar t is a function of bars [0..t] ONLY. kappa at the
current bar is 0 by the spec's endpoint rule (it needs t+1); it becomes
real the next day. Interior kappa at s<t uses bar s+1 <= t: known at the
close of t. No normalization (V_max, CV_max, delta_max) ever sees a gate
that has not happened. `assert_causal` re-derives sampled days from
truncated inputs and demands identical actions.

IMPLEMENTATION NOTE (speed with a self-audit)
---------------------------------------------
Closed gates are append-only and their raw content is immutable, so the
L2->L5 recursion is maintained incrementally; the current (partial) gate is
evaluated on a copy each day. Whenever a running normalization maximum
(V_max / CV_max / delta_max over closed gates + the current partial gate)
changes, the chain is rebuilt from scratch. Every `SELF_CHECK_EVERY` bars,
and on the final bar, the incremental result is verified against a full
from-scratch recompute and any mismatch raises. Determinism: no randomness
anywhere; SHA-256 receipt over (params, field mode, symbol, dates, action
sequence).
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

from quarantine_historical_kernel import KernelParameters, psi_r  # noqa: E402

PARAMS = KernelParameters()
RHO_ROLLING_WINDOW = 5
R_NORM_MAX = 1.0
EPS_TAU_DAYS = 1.0
SELF_CHECK_EVERY = 100


# ---------------------------------------------------------------------------
# L0 — full-series arrays (interior values are static; the endpoint kappa
# rule only affects the current bar, which is never inside a gate slice)
# ---------------------------------------------------------------------------

@dataclass
class L0Arrays:
    F: np.ndarray
    dF: np.ndarray
    sigma: np.ndarray
    kappa: np.ndarray       # interior kappa; kappa[t] uses F[t+1]; [0]=[n-1]=0
    r: np.ndarray
    N: np.ndarray           # negative-space per bar (interior semantics)
    D: np.ndarray           # boundary functional (interior semantics)
    perV: np.ndarray        # per-bar V integrand
    # prefix-sum caches (index i holds sum over [0, i))
    cs_perV: np.ndarray
    cs_r: np.ndarray
    cs_dF: np.ndarray
    cs_sigma: np.ndarray
    cs_kappa: np.ndarray
    cs_N: np.ndarray


def compute_l0_arrays(F: np.ndarray, p: KernelParameters = PARAMS) -> L0Arrays:
    n = len(F)
    dF = np.zeros(n)
    if n > 1:
        dF[1:] = np.diff(F)

    sigma = np.zeros(n)
    for t in range(n):
        w0 = max(0, t - p.W + 1)
        win = F[w0 : t + 1]
        sigma[t] = float(np.mean((win - win.mean()) ** 2))

    kappa = np.zeros(n)
    if n > 2:
        kappa[1 : n - 1] = np.abs(F[2:] - 2.0 * F[1 : n - 1] + F[: n - 2])

    r = np.zeros(n)
    for t in range(n):
        w0 = max(0, t - p.W_r + 1)
        r[t] = psi_r(F[w0 : t + 1])

    N = ((sigma < p.sigma_min) & (np.abs(dF) < p.delta_min) & (kappa < p.kappa_min)).astype(np.int64)
    D = p.alpha_1 * np.abs(dF) + p.alpha_2 * sigma + p.alpha_3 * kappa
    perV = p.beta_1 * np.abs(dF) + p.beta_2 * sigma + p.beta_3 * kappa

    def cs(a: np.ndarray) -> np.ndarray:
        out = np.zeros(n + 1)
        np.cumsum(a, out=out[1:])
        return out

    return L0Arrays(
        F=F, dF=dF, sigma=sigma, kappa=kappa, r=r, N=N, D=D, perV=perV,
        cs_perV=cs(perV), cs_r=cs(r), cs_dF=cs(dF), cs_sigma=cs(sigma),
        cs_kappa=cs(kappa), cs_N=cs(N.astype(float)),
    )


@dataclass(frozen=True)
class GateRec:
    """Immutable raw content of one gate [t_a, t_b) stamped at bar t_b."""
    t_a: int
    t_b: int
    T: float
    V: float
    R: float
    C: int
    delta_g: float
    mu: Tuple[float, float, float]
    N_gate: int


def _gate_from_span(l0: L0Arrays, t_a: int, t_b: int, last_mu: np.ndarray,
                    p: KernelParameters) -> GateRec:
    """Gate content over the half-open span [t_a, t_b) via prefix sums.
    All interior bars s < t_b use static kappa (needs bar s+1 <= t_b)."""
    ln = t_b - t_a
    T = float(ln)
    V = float(l0.cs_perV[t_b] - l0.cs_perV[t_a])
    R = float(l0.cs_r[t_b] - l0.cs_r[t_a])
    P_list = tuple((int(T // h1), int(V // h2), int(R // h3)) for h1, h2, h3 in p.lattices)
    C = len(set(P_list))
    mu = np.array([
        (l0.cs_dF[t_b] - l0.cs_dF[t_a]) / ln,
        (l0.cs_sigma[t_b] - l0.cs_sigma[t_a]) / ln,
        (l0.cs_kappa[t_b] - l0.cs_kappa[t_a]) / ln,
    ])
    delta_g = float(np.linalg.norm(mu - last_mu))
    N_gate = 1 if (l0.cs_N[t_b] - l0.cs_N[t_a]) == ln else 0
    return GateRec(t_a, t_b, T, V, R, C, delta_g, (float(mu[0]), float(mu[1]), float(mu[2])), N_gate)


# ---------------------------------------------------------------------------
# The L2->L5 chain as an explicit recursion state over the gate sequence
# ---------------------------------------------------------------------------

@dataclass
class ChainState:
    # L3/L4 recursion memory
    last_R: float = 0.0
    last_URF: float = 0.0
    last_URF2: float = 0.0
    last_D: int = 0
    last_B: float = 0.0
    # L5 memory
    a1: float = 0.0
    a2: float = 0.0
    a3: float = 0.0
    x_f: float = 0.0
    x_m: float = 0.0
    x_s: float = 0.0
    prev_ord: Optional[float] = None
    prev_phi: float = 0.0
    prev_reg: Optional[str] = None
    k: int = 0                      # gates consumed
    # rolling process-quantity tails (length <= RHO_ROLLING_WINDOW)
    r_tail: Tuple[float, ...] = ()
    s_tail: Tuple[float, ...] = ()
    u_tail: Tuple[float, ...] = ()
    c_tail: Tuple[float, ...] = ()

    def copy(self) -> "ChainState":
        return ChainState(**vars(self))


@dataclass
class DayState:
    action: str            # strict ch06 threshold mapping (lineage A-form)
    action_cp2: str        # lineage-realized sequential governance (B-form)
    ignition: int          # URF admitted after >=2 suppressed gates
    extinction: int        # URF suppressed after >=2 admitted gates
    Q_5: float
    Q_20: float
    Q_60: float
    F_n: float
    chi_n: float
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


def _step_chain(st: ChainState, g: GateRec, norms: Tuple[float, float, float],
                date_ord: float, p: KernelParameters) -> DayState:
    """Advance the chain by ONE gate under the given normalization maxima
    (V_max, CV_max, delta_max are field-level quantities of the known
    structure). Mutates st. Returns the governed state at this gate."""
    V_max, CV_max, delta_max = norms  # delta_max reserved (lineage psi_u does not use it)

    # --- L2 (canonical operators)
    w = g.V / V_max
    CV = np.array([g.T, g.V, g.R]) - np.array(g.mu)
    cvn = float(np.linalg.norm(CV))
    S = float(np.clip(1.0 / (1.0 + g.C + g.delta_g), 0.0, 1.0))
    U = float(np.clip(0.1 * g.C + 0.1 * g.delta_g + 0.2 * g.N_gate, 0.0, 1.0))
    IAS = 1 if (U > 0.8 or g.delta_g > 2.0) else 0
    Reg = "TRANSITIONAL" if g.C > 1 else "STABLE"

    # --- L3
    Z = p.lambda_1 + p.lambda_2 + p.lambda_3 + p.lambda_4 + p.lambda_5
    R_res = (
        p.lambda_1 * w
        + p.lambda_2 * (cvn / CV_max if CV_max > 0 else 0.0)
        + p.lambda_3 * S
        + p.lambda_4 * (1.0 / (1.0 + g.C))
        + p.lambda_5 * (1.0 - U)
    ) / Z
    Hyst = 1 if abs(R_res - st.last_R) > p.h_max else 0
    g_adm = 1 if (U <= p.U_max and IAS == 0 and Hyst == 0) else 0
    URF = g_adm * R_res

    # --- L4
    delta_R = URF - st.last_URF
    if delta_R > p.eps_D:
        D_dir = 1
    elif delta_R < -p.eps_D:
        D_dir = -1
    else:
        D_dir = 0
    M = URF - 2.0 * st.last_URF + st.last_URF2
    U_star = U + p.eta_H * Hyst + p.eta_IAS * IAS
    Rev = 1 if (D_dir * st.last_D < 0) else 0
    B = float(np.clip(st.last_B + p.xi * (1.0 - U_star) * delta_R - p.chi * U_star, p.B_min, p.B_max))

    # --- L5 process quantities on the event tape
    delta_tau = EPS_TAU_DAYS if st.prev_ord is None else max(EPS_TAU_DAYS, date_ord - st.prev_ord)
    omega = (2.0 * math.pi) / delta_tau
    phi = (st.prev_phi + omega * delta_tau) % (2.0 * math.pi)

    if st.k == 0:
        event_type = "gate_close"
    elif st.prev_reg is not None and Reg != st.prev_reg:
        event_type = "regime_change"
    elif Rev > 0:
        event_type = "resonance_reversal"
    else:
        event_type = "gate_close"

    r_norm = float(np.clip(R_res / R_NORM_MAX, -1.0, 1.0))
    s_value = float(np.clip(p.s_uf_default, 0.0, 1.0))
    u_value = float(np.clip(U_star, 0.0, 1.0))
    c_norm = float(np.clip(g.C / 4.0, 0.0, 1.0))

    r_tail = (st.r_tail + (r_norm,))[-RHO_ROLLING_WINDOW:]
    s_tail = (st.s_tail + (s_value,))[-RHO_ROLLING_WINDOW:]
    u_tail = (st.u_tail + (u_value,))[-RHO_ROLLING_WINDOW:]
    c_tail = (st.c_tail + (c_norm,))[-RHO_ROLLING_WINDOW:]

    rho = float(np.clip(
        p.a_rho * (sum(r_tail) / len(r_tail))
        + p.b_rho * (sum(s_tail) / len(s_tail))
        - p.c_rho * (sum(u_tail) / len(u_tail))
        - p.d_rho * (sum(c_tail) / len(c_tail)),
        0.0, 1.0,
    ))

    nu0 = max(-1.0, min(1.0, float(D_dir)))
    nu1 = max(-1.0, min(1.0, float(M)))
    nu2 = max(-1.0, min(1.0, r_norm))

    a1 = max(-1.0, min(1.0, p.a_decay * st.a1 + p.a_nu_weight * nu0 + p.a_pi_weight * rho))
    a2 = max(-1.0, min(1.0, p.a_decay * st.a2 + p.a_nu_weight * nu1 + p.a_pi_weight * rho))
    a3 = max(-1.0, min(1.0, p.a_decay * st.a3 + p.a_nu_weight * nu2 + p.a_pi_weight * rho))

    x_f = max(-1.0, min(1.0, p.A_f * st.x_f + p.B_f * nu0 + p.G_all * rho + p.L_f * a1))
    x_m = max(-1.0, min(1.0, p.A_m * st.x_m + p.B_m * nu1 + p.H_mf * x_f + p.G_all * rho + p.L_m * a2))
    x_s = max(-1.0, min(1.0, p.A_s * st.x_s + p.B_s * nu2 + p.H_sm * x_m + p.G_all * rho + p.L_s * a3))

    surprise = math.sqrt((nu0 - x_f) ** 2 + (nu1 - x_m) ** 2 + (nu2 - x_s) ** 2)
    gamma = 0.5 * (u_value + (1.0 - rho))
    F_n = float(gamma + p.lambda_s * surprise)

    q5 = x_f - p.eta_h * F_n
    q20 = x_m - p.eta_h * F_n
    q60 = x_s - p.eta_h * F_n

    sg = (int(np.sign(q5)), int(np.sign(q20)), int(np.sign(q60)))
    chi_n = 1.0 if (sg[0] == sg[1] == sg[2]) else 0.0

    if chi_n < p.chi_min:
        action = "ABSTAIN"
    elif q20 > p.theta_plus and F_n <= p.F_max:
        action = "ACCUMULATE"
    elif q20 < -p.theta_plus and F_n <= p.F_max:
        action = "AVOID"
    else:
        action = "HOLD"

    # Lineage-realized sequential governance (the preserved system's actual
    # trade rule, reconstructed from its own artifacts and the CP-2 baseline):
    #   primitive ACCUMULATE = resonance ignition — this gate admitted
    #     (URF > 0) after >= 2 suppressed gates (URF == 0, URF_prev == 0),
    #     which is exactly the preserved trades' signature (D=+1,
    #     M = URF in the admissible-resonance band);
    #   cognitive gate (CP-2, pinned in tfe_l5_baseline): F_n <= 1.65 and
    #     raw_x_m (= x_m) <= 0.50;
    #   primitive AVOID = resonance extinction (symmetric, declared).
    # The $5 price floor is applied at the evaluation layer.
    ignition = 1 if (URF > 0.0 and st.last_URF == 0.0 and st.last_URF2 == 0.0) else 0
    extinction = 1 if (URF == 0.0 and st.last_URF > 0.0 and st.last_URF2 > 0.0) else 0
    if ignition and F_n <= 1.65 and x_m <= 0.50:
        action_cp2 = "ACCUMULATE"
    elif extinction:
        action_cp2 = "AVOID"
    else:
        action_cp2 = "HOLD"

    # mutate recursion state
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
    st.k += 1
    st.r_tail, st.s_tail, st.u_tail, st.c_tail = r_tail, s_tail, u_tail, c_tail

    return DayState(
        action=action, action_cp2=action_cp2, ignition=ignition,
        extinction=extinction, Q_5=q5, Q_20=q20, Q_60=q60, F_n=F_n,
        chi_n=chi_n, x_f=x_f, x_m=x_m, x_s=x_s, rho_n=rho, s_n=surprise,
        D_k=D_dir, B_k=B, Rev_k=Rev, U_star_k=U_star, regime=Reg,
        event_type=event_type, gate_count=st.k,
    )


# ---------------------------------------------------------------------------
# Causal replay driver
# ---------------------------------------------------------------------------

def _static_boundaries(l0: L0Arrays, p: KernelParameters) -> np.ndarray:
    """Interior boundary bars: D[t] >= tau_D with full (static) kappa.
    Bar t's boundary status is known at the close of bar t+1 and never
    changes after; the current bar itself is always a forced close."""
    n = len(l0.F)
    flags = l0.D >= p.tau_D
    flags[0] = False
    if n > 0:
        flags[n - 1] = False  # the last bar's real D is only known later
    return np.flatnonzero(flags)


def _closed_gates_upto(l0: L0Arrays, bounds: np.ndarray, t: int,
                       p: KernelParameters, cache: List[GateRec]) -> List[GateRec]:
    """Extend `cache` with gates permanently closed by static boundaries
    strictly below the current bar t. Boundary bars are strictly
    increasing, so every span [t_a, b) is non-empty."""
    made = len(cache)
    valid = bounds[bounds < t]
    while made < len(valid):
        b = int(valid[made])
        t_a = int(valid[made - 1]) if made >= 1 else 0
        last_mu = np.array(cache[-1].mu) if cache else np.zeros(3)
        cache.append(_gate_from_span(l0, t_a, b, last_mu, p))
        made += 1
    return cache


def replay_symbol(
    dates: Sequence,
    closes: np.ndarray,
    field_mode: str = "RAW",
    warmup: int = 60,
    p: KernelParameters = PARAMS,
) -> List[Optional[DayState]]:
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    F = closes.copy() if field_mode == "RAW" else np.log(closes)
    if field_mode not in ("RAW", "LOG"):
        raise ValueError(f"unknown field_mode {field_mode!r}")

    dates_ord = np.array([np.datetime64(d, "D").astype("int64") for d in dates], dtype="float64")

    l0 = compute_l0_arrays(F, p)
    bounds = _static_boundaries(l0, p)

    closed: List[GateRec] = []          # closed-gate cache (append-only)
    base = ChainState()                  # chain state through all closed gates
    base_norms = (0.0, 0.0, 0.0)         # (V_max, CV_max, delta_max) over closed
    consumed = 0                         # closed gates consumed into `base`

    out: List[Optional[DayState]] = [None] * n

    def rebuild(k_closed: int, norms: Tuple[float, float, float]) -> ChainState:
        stx = ChainState()
        for gg in closed[:k_closed]:
            _step_chain(stx, gg, norms, dates_ord[gg.t_b], p)
        return stx

    cvmax_closed = 0.0
    vmax_closed = 0.0
    dmax_closed = 0.0

    for t in range(warmup, n):
        _closed_gates_upto(l0, bounds, t, p, closed)
        k_closed = len(closed)

        # final (current) partial gate [t_a, t)
        t_a = int(closed[-1].t_b) if closed else 0
        if t == t_a:
            # nothing new beyond the last boundary; current gate empty ->
            # lineage skips empty slices; state is the closed chain as-is
            final_gate = None
        else:
            last_mu = np.array(closed[-1].mu) if closed else np.zeros(3)
            final_gate = _gate_from_span(l0, t_a, t, last_mu, p)

        # maxima over closed gates (incremental)
        while consumed < k_closed:
            gg = closed[consumed]
            vmax_closed = max(vmax_closed, gg.V)
            cv = math.sqrt((gg.T - gg.mu[0]) ** 2 + (gg.V - gg.mu[1]) ** 2 + (gg.R - gg.mu[2]) ** 2)
            cvmax_closed = max(cvmax_closed, cv)
            dmax_closed = max(dmax_closed, gg.delta_g)
            consumed += 1  # counted, not yet stepped

        vmax = vmax_closed
        cvmax = cvmax_closed
        dmax = dmax_closed
        if final_gate is not None:
            vmax = max(vmax, final_gate.V)
            cv_f = math.sqrt((final_gate.T - final_gate.mu[0]) ** 2 + (final_gate.V - final_gate.mu[1]) ** 2 + (final_gate.R - final_gate.mu[2]) ** 2)
            cvmax = max(cvmax, cv_f)
            dmax = max(dmax, final_gate.delta_g)
        vmax = max(vmax, 1e-12)
        cvmax = max(cvmax, 1e-12)
        norms = (vmax, cvmax, dmax)

        # keep `base` = chain through all closed gates under `norms`
        if norms != base_norms:
            base = rebuild(k_closed, norms)
            base_norms = norms
        else:
            while base.k < k_closed:
                gg = closed[base.k]
                _step_chain(base, gg, norms, dates_ord[gg.t_b], p)

        if final_gate is None:
            # replicate: state at t is the last closed gate's governed state
            # (no new event today) — recompute its DayState cheaply
            if k_closed == 0:
                out[t] = None
                continue
            st_tmp = rebuild(k_closed - 1, norms)
            gg = closed[k_closed - 1]
            out[t] = _step_chain(st_tmp, gg, norms, dates_ord[gg.t_b], p)
            continue

        st_day = base.copy()
        out[t] = _step_chain(st_day, final_gate, norms, dates_ord[t], p)

        # periodic from-scratch verification (and always on the last bar)
        if (t - warmup) % SELF_CHECK_EVERY == 0 or t == n - 1:
            st_ref = rebuild(k_closed, norms)
            ref = _step_chain(st_ref, final_gate, norms, dates_ord[t], p)
            got = out[t]
            if not (
                ref.action == got.action
                and abs(ref.Q_20 - got.Q_20) < 1e-9
                and abs(ref.F_n - got.F_n) < 1e-9
            ):
                raise AssertionError(
                    f"incremental/self-check divergence at t={t}: {ref} vs {got}"
                )

    return out


def actions_digest(symbol: str, dates, states: List[Optional[DayState]], field_mode: str) -> str:
    payload = json.dumps(
        {
            "symbol": symbol,
            "field_mode": field_mode,
            "params": {k: (list(map(list, v)) if isinstance(v, list) else v) for k, v in vars(PARAMS).items()},
            "actions": [
                (str(np.datetime64(d, "D")), s.action if s else None)
                for d, s in zip(dates, states)
            ],
        },
        sort_keys=True,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def assert_causal(dates, closes, states: List[Optional[DayState]], field_mode: str,
                  sample: Sequence[int], p: KernelParameters = PARAMS) -> None:
    """No-cheat law: the action recorded for bar t must be reproducible from
    data truncated at t. Identical or AssertionError."""
    closes = np.asarray(closes, dtype=float)
    for t in sample:
        if states[t] is None:
            continue
        redo = replay_symbol(dates[: t + 1], closes[: t + 1], field_mode=field_mode,
                             warmup=t, p=p)[t]
        assert redo is not None, f"causality: no state at t={t}"
        same = (
            redo.action == states[t].action
            and abs(redo.Q_20 - states[t].Q_20) < 1e-9
            and abs(redo.F_n - states[t].F_n) < 1e-9
            and redo.gate_count == states[t].gate_count
        )
        assert same, (
            f"CAUSALITY VIOLATION at t={t}: truncated=({redo.action},{redo.Q_20:.6f},"
            f"{redo.F_n:.6f},k={redo.gate_count}) recorded=({states[t].action},"
            f"{states[t].Q_20:.6f},{states[t].F_n:.6f},k={states[t].gate_count})"
        )
