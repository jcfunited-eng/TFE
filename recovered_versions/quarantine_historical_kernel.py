#!/usr/bin/env python3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


INPUT_PATH = Path("quarantine_12k_universe.parquet")
OUTPUT_PATH = Path("quarantine_12k_governed_states.parquet")
BATCH_SIZE = 200_000
PROGRESS_EVERY = 250
EPS_TAU_DAYS = 1.0
RHO_ROLLING_WINDOW = 5
R_NORM_MAX = 1.0


@dataclass
class KernelParameters:
    W: int = 20
    W_r: int = 10
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6
    alpha_1: float = 1.0
    alpha_2: float = 1.0
    alpha_3: float = 1.0
    tau_D: float = 0.20
    beta_1: float = 1.0
    beta_2: float = 1.0
    beta_3: float = 1.0
    lattices: List[Tuple[float, float, float]] = field(
        default_factory=lambda: [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0)]
    )
    lambda_1: float = 1.0
    lambda_2: float = 1.0
    lambda_3: float = 1.0
    lambda_4: float = 1.0
    lambda_5: float = 1.0
    h_max: float = 0.20
    U_max: float = 0.75
    eps_D: float = 0.00073
    eta_H: float = 0.10
    eta_IAS: float = 0.10
    xi: float = 0.10
    chi: float = 0.10
    B_min: float = -1.0
    B_max: float = 1.0

    # CV-1.0 governance parameters
    a_rho: float = 0.4
    b_rho: float = 0.4
    c_rho: float = 0.1
    d_rho: float = 0.1
    a_decay: float = 0.99
    a_nu_weight: float = 0.05
    a_pi_weight: float = 0.05
    A_f: float = 0.90
    A_m: float = 0.98
    A_s: float = 0.995
    B_f: float = 0.1
    B_m: float = 0.1
    B_s: float = 0.1
    H_mf: float = 0.1
    H_sm: float = 0.1
    G_all: float = 0.01
    L_f: float = 0.01
    L_m: float = 0.01
    L_s: float = 0.01
    lambda_s: float = 1.0
    eta_h: float = 2.0
    F_max: float = 0.45
    chi_min: float = 1.0
    theta_plus: float = 0.65
    s_uf_default: float = 1.0
    r_uf_default: float = 1.0


def sat_scalar(value: float) -> float:
    return float(np.clip(value, -1.0, 1.0))


def sat_vector(values: np.ndarray) -> np.ndarray:
    return np.clip(values.astype(float), -1.0, 1.0)


def psi_r(F_window: np.ndarray) -> float:
    return 1.0 if len(F_window) > 0 and F_window[-1] > np.mean(F_window) else 0.5


def psi_s(TVR: Tuple[float, float, float], P_list: List[Tuple[int, int, int]], C: int, delta_g: float) -> float:
    T, V, R = TVR
    return float(np.clip(1.0 / (1.0 + C + delta_g), 0.0, 1.0))


def phi_reg(P_list: List[Tuple[int, int, int]], C: int) -> str:
    return "TRANSITIONAL" if C > 1 else "STABLE"


def psi_u(C: int, delta_g: float, N_gate: int) -> float:
    return float(np.clip((C * 0.1) + (delta_g * 0.1) + (N_gate * 0.2), 0.0, 1.0))


def phi_ias(S: float, U: float, delta_g: float) -> int:
    return 1 if U > 0.8 or delta_g > 2.0 else 0


@dataclass
class SEV:
    F: float
    dF: float
    sigma: float
    kappa: float
    r: float
    N: int


def compute_l0_sev(F: np.ndarray, params: KernelParameters) -> List[SEV]:
    n = len(F)
    sevs = []
    for t in range(n):
        dF = F[t] - F[t - 1] if t > 0 else 0.0
        start_w = max(0, t - params.W + 1)
        F_window = F[start_w : t + 1]
        F_bar = np.mean(F_window)
        sigma = np.mean((F_window - F_bar) ** 2)
        if 0 < t < n - 1:
            kappa = abs(F[t + 1] - 2 * F[t] + F[t - 1])
        else:
            kappa = 0.0
        start_r = max(0, t - params.W_r + 1)
        r_val = psi_r(F[start_r : t + 1])
        N = 1 if (sigma < params.sigma_min and abs(dF) < params.delta_min and kappa < params.kappa_min) else 0
        sevs.append(SEV(F[t], dF, sigma, kappa, r_val, N))
    return sevs


@dataclass
class GateL1:
    t_a: int
    t_b: int
    TVR: Tuple[float, float, float]
    P_list: List[Tuple[int, int, int]]
    C: int
    delta_g: float
    mu: np.ndarray
    N_gate: int


def segment_l1_gates(sevs: List[SEV], params: KernelParameters) -> List[GateL1]:
    D = np.zeros(len(sevs))
    for t, sev in enumerate(sevs):
        D[t] = params.alpha_1 * abs(sev.dF) + params.alpha_2 * sev.sigma + params.alpha_3 * sev.kappa

    gates = []
    t_a = 0
    last_mu = np.zeros(3)
    for t in range(1, len(sevs)):
        if D[t] >= params.tau_D or t == len(sevs) - 1:
            t_b = t
            gate_sevs = sevs[t_a:t_b]
            if not gate_sevs:
                t_a = t
                continue
            T = float(t_b - t_a)
            V = sum(params.beta_1 * abs(s.dF) + params.beta_2 * s.sigma + params.beta_3 * s.kappa for s in gate_sevs)
            R = sum(s.r for s in gate_sevs)
            TVR = (T, V, R)
            P_list = []
            for h1, h2, h3 in params.lattices:
                P_list.append((int(T // h1), int(V // h2), int(R // h3)))
            C = len(set(P_list))
            mu_k = np.array(
                [
                    np.mean([s.dF for s in gate_sevs]),
                    np.mean([s.sigma for s in gate_sevs]),
                    np.mean([s.kappa for s in gate_sevs]),
                ]
            )
            delta_g = float(np.linalg.norm(mu_k - last_mu))
            N_gate = 1 if all(s.N == 1 for s in gate_sevs) else 0
            gates.append(GateL1(t_a, t_b, TVR, P_list, C, delta_g, mu_k, N_gate))
            last_mu = mu_k
            t_a = t
    return gates


@dataclass
class ISF:
    gate: GateL1
    w: float
    CV: np.ndarray
    S: float
    Reg: str
    U: float
    IAS: int


def compute_l2_isf(gates: List[GateL1], params: KernelParameters) -> List[ISF]:
    if not gates:
        return []
    V_max = max((g.TVR[1] for g in gates), default=1e-12)
    V_max = V_max if V_max > 0 else 1e-12
    isfs = []
    for g in gates:
        w_k = g.TVR[1] / V_max
        CV_k = np.array(g.TVR) - g.mu
        S_k = psi_s(g.TVR, g.P_list, g.C, g.delta_g)
        Reg_k = phi_reg(g.P_list, g.C)
        U_k = psi_u(g.C, g.delta_g, g.N_gate)
        IAS_k = phi_ias(S_k, U_k, g.delta_g)
        isfs.append(ISF(g, w_k, CV_k, S_k, Reg_k, U_k, IAS_k))
    return isfs


@dataclass
class Resonance:
    isf: ISF
    R: float
    Hyst: int
    g: int
    URF: float


def compute_l3_resonance(isfs: List[ISF], params: KernelParameters) -> List[Resonance]:
    if not isfs:
        return []
    Z = params.lambda_1 + params.lambda_2 + params.lambda_3 + params.lambda_4 + params.lambda_5
    CV_max = max((np.linalg.norm(isf.CV) for isf in isfs), default=1e-12)
    CV_max = CV_max if CV_max > 0 else 1e-12
    res = []
    last_R = 0.0
    for isf in isfs:
        term1 = params.lambda_1 * isf.w
        term2 = params.lambda_2 * (np.linalg.norm(isf.CV) / CV_max)
        term3 = params.lambda_3 * isf.S
        term4 = params.lambda_4 * (1.0 / (1.0 + isf.gate.C))
        term5 = params.lambda_5 * (1.0 - isf.U)
        R_k = (1.0 / Z) * (term1 + term2 + term3 + term4 + term5)
        Hyst_k = 1 if abs(R_k - last_R) > params.h_max else 0
        g_k = 1 if (isf.U <= params.U_max and isf.IAS == 0 and Hyst_k == 0) else 0
        URF_k = g_k * R_k
        res.append(Resonance(isf, R_k, Hyst_k, g_k, URF_k))
        last_R = R_k
    return res


@dataclass
class DSFState:
    D: int
    M: float
    Rev: int
    U_star: float
    C: int
    P: int
    B: float


def compute_l4_dsf(res: List[Resonance], params: KernelParameters) -> List[DSFState]:
    dsfs = []
    last_URF = 0.0
    last_URF2 = 0.0
    last_D = 0
    last_B = 0.0
    for r in res:
        delta_R = r.URF - last_URF
        if delta_R > params.eps_D:
            D_k = 1
        elif delta_R < -params.eps_D:
            D_k = -1
        else:
            D_k = 0
        M_k = r.URF - 2 * last_URF + last_URF2
        Rev_k = 1 if (D_k * last_D < 0) else 0
        U_star_k = r.isf.U + (params.eta_H * r.Hyst) + (params.eta_IAS * r.isf.IAS)
        P_k = abs(D_k - last_D)
        B_k_raw = last_B + params.xi * (1 - U_star_k) * delta_R - params.chi * U_star_k
        B_k = float(np.clip(B_k_raw, params.B_min, params.B_max))
        dsfs.append(DSFState(D_k, M_k, Rev_k, U_star_k, r.isf.gate.C, P_k, B_k))
        last_URF2 = last_URF
        last_URF = r.URF
        last_D = D_k
        last_B = B_k
    return dsfs


def days_between(current_ts: pd.Timestamp, previous_ts: pd.Timestamp | None) -> float:
    if previous_ts is None:
        return EPS_TAU_DAYS
    delta_days = (current_ts - previous_ts).total_seconds() / 86400.0
    return max(EPS_TAU_DAYS, float(delta_days))


def event_type_for(idx: int, reg_k: str, prev_reg: str | None, rev_k: int) -> str:
    if idx == 0:
        return "gate_close"
    if prev_reg is not None and reg_k != prev_reg:
        return "regime_change"
    if rev_k > 0:
        return "resonance_reversal"
    return "gate_close"


def build_state_rows(symbol: str, group: pd.DataFrame, params: KernelParameters) -> pd.DataFrame:
    group = group.sort_values("Date").reset_index(drop=True)
    close_prices = group["Close"].astype(float).to_numpy()
    date_array = pd.to_datetime(group["Date"]).to_numpy()

    sevs = compute_l0_sev(close_prices, params)
    gates = segment_l1_gates(sevs, params)
    isfs = compute_l2_isf(gates, params)
    resonances = compute_l3_resonance(isfs, params)
    dsfs = compute_l4_dsf(resonances, params)

    rows = []
    prev_timestamp = None
    prev_phi = 0.0
    prev_reg = None

    a_state = np.zeros(3, dtype=float)
    x_f = 0.0
    x_m = 0.0
    x_s = 0.0

    r_history: list[float] = []
    s_history: list[float] = []
    u_history: list[float] = []
    c_history: list[float] = []

    q_5 = np.array([1.0, 0.0, 0.0], dtype=float)
    q_20 = np.array([0.0, 1.0, 0.0], dtype=float)
    q_60 = np.array([0.0, 0.0, 1.0], dtype=float)

    for idx, (gate, isf, resonance, dsf) in enumerate(zip(gates, isfs, resonances, dsfs)):
        gate_index = int(gate.t_b)
        if gate_index < 0 or gate_index >= len(date_array):
            continue

        event_timestamp = pd.Timestamp(date_array[gate_index])
        close_price = float(close_prices[gate_index])
        event_type = event_type_for(idx, isf.Reg, prev_reg, dsf.Rev)

        delta_tau = days_between(event_timestamp, prev_timestamp)
        omega = float((2.0 * np.pi) / delta_tau)
        phi = float((prev_phi + (omega * delta_tau)) % (2.0 * np.pi))

        r_norm = float(np.clip(resonance.R / R_NORM_MAX, -1.0, 1.0))
        s_value = float(np.clip(params.s_uf_default, 0.0, 1.0))
        u_value = float(np.clip(dsf.U_star, 0.0, 1.0))
        c_norm = float(np.clip(dsf.C / 4.0, 0.0, 1.0))

        r_history.append(r_norm)
        s_history.append(s_value)
        u_history.append(u_value)
        c_history.append(c_norm)

        R_bar = float(np.mean(r_history[-RHO_ROLLING_WINDOW:]))
        S_bar = float(np.mean(s_history[-RHO_ROLLING_WINDOW:]))
        U_bar = float(np.mean(u_history[-RHO_ROLLING_WINDOW:]))
        C_bar = float(np.mean(c_history[-RHO_ROLLING_WINDOW:]))
        rho = float(np.clip((params.a_rho * R_bar) + (params.b_rho * S_bar) - (params.c_rho * U_bar) - (params.d_rho * C_bar), 0.0, 1.0))

        nu_core = sat_vector(np.array([float(dsf.D), float(dsf.M), r_norm], dtype=float))
        pi_vec = np.full(3, rho, dtype=float)

        a_state = sat_vector((params.a_decay * a_state) + (params.a_nu_weight * nu_core) + (params.a_pi_weight * pi_vec))

        x_f = sat_scalar((params.A_f * x_f) + (params.B_f * nu_core[0]) + (params.G_all * rho) + (params.L_f * a_state[0]))
        x_m = sat_scalar((params.A_m * x_m) + (params.B_m * nu_core[1]) + (params.H_mf * x_f) + (params.G_all * rho) + (params.L_m * a_state[1]))
        x_s = sat_scalar((params.A_s * x_s) + (params.B_s * nu_core[2]) + (params.H_sm * x_m) + (params.G_all * rho) + (params.L_s * a_state[2]))

        z_n = np.array([x_f, x_m, x_s], dtype=float)
        surprise = float(np.linalg.norm(nu_core - z_n))
        gamma = float(0.5 * (u_value + (1.0 - rho)))
        F_n = float(gamma + (params.lambda_s * surprise))

        q5 = float(np.dot(q_5, z_n) - (params.eta_h * F_n))
        q20 = float(np.dot(q_20, z_n) - (params.eta_h * F_n))
        q60 = float(np.dot(q_60, z_n) - (params.eta_h * F_n))

        signs = [int(np.sign(q5)), int(np.sign(q20)), int(np.sign(q60))]
        chi_n = 1.0 if (signs[0] == signs[1] == signs[2]) else 0.0

        decision = "ACCUMULATE" if (q20 > params.theta_plus and F_n <= params.F_max and chi_n >= params.chi_min) else "HOLD/AVOID"
        prev_b = float(dsfs[idx - 1].B) if idx > 0 else 0.0

        rows.append(
            {
                "Date": event_timestamp,
                "Symbol": symbol,
                "Close": close_price,
                "event_type": event_type,
                "D_k": int(dsf.D),
                "M_k": float(dsf.M),
                "R_k": float(resonance.R),
                "Rev_k": int(dsf.Rev),
                "U_star_k": float(dsf.U_star),
                "C_k": int(dsf.C),
                "P_k": int(dsf.P),
                "B_k": float(dsf.B),
                "prev_B_k": float(prev_b),
                "omega_n": omega,
                "phi_n": phi,
                "rho_n": rho,
                "s_n": surprise,
                "F_n": F_n,
                "Q_5": q5,
                "Q_20": q20,
                "Q_60": q60,
                "chi_n": chi_n,
                "x_f": x_f,
                "x_m": x_m,
                "x_s": x_s,
                "a_f": float(a_state[0]),
                "a_m": float(a_state[1]),
                "a_s": float(a_state[2]),
                "Decision": decision,
            }
        )

        prev_timestamp = event_timestamp
        prev_phi = phi
        prev_reg = isf.Reg

    return pd.DataFrame(
        rows,
        columns=[
            "Date",
            "Symbol",
            "Close",
            "event_type",
            "D_k",
            "M_k",
            "R_k",
            "Rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
            "prev_B_k",
            "omega_n",
            "phi_n",
            "rho_n",
            "s_n",
            "F_n",
            "Q_5",
            "Q_20",
            "Q_60",
            "chi_n",
            "x_f",
            "x_m",
            "x_s",
            "a_f",
            "a_m",
            "a_s",
            "Decision",
        ],
    )


def build_historical_states(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input parquet: {input_path}")
    if output_path.exists():
        output_path.unlink()

    params = KernelParameters()
    parquet = pq.ParquetFile(input_path)
    carry_symbol = None
    carry_parts: list[pd.DataFrame] = []
    writer = None
    total_rows = 0
    total_symbols = 0

    try:
        for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=["Date", "Symbol", "Close"]):
            batch_df = batch.to_pandas()
            batch_df["Date"] = pd.to_datetime(batch_df["Date"])
            batch_df["Symbol"] = batch_df["Symbol"].astype(str).str.upper()
            batch_df = batch_df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
            if batch_df.empty:
                continue

            for symbol, group in batch_df.groupby("Symbol", sort=False):
                if carry_symbol is None:
                    carry_symbol = symbol
                    carry_parts = [group]
                    continue
                if symbol == carry_symbol:
                    carry_parts.append(group)
                    continue

                symbol_df = pd.concat(carry_parts, ignore_index=True)
                state_rows = build_state_rows(carry_symbol, symbol_df, params)
                if not state_rows.empty:
                    table = pa.Table.from_pandas(state_rows, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(str(output_path), table.schema)
                    writer.write_table(table)
                    total_rows += len(state_rows)
                total_symbols += 1
                if total_symbols % PROGRESS_EVERY == 0:
                    print(f"Processed symbols: {total_symbols} governed_rows={total_rows}", flush=True)

                carry_symbol = symbol
                carry_parts = [group]

        if carry_symbol is not None and carry_parts:
            symbol_df = pd.concat(carry_parts, ignore_index=True)
            state_rows = build_state_rows(carry_symbol, symbol_df, params)
            if not state_rows.empty:
                table = pa.Table.from_pandas(state_rows, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(str(output_path), table.schema)
                writer.write_table(table)
                total_rows += len(state_rows)
            total_symbols += 1
    finally:
        if writer is not None:
            writer.close()

    if not output_path.exists():
        raise RuntimeError("No governed states were written.")

    print(f"Created {output_path}")
    print(f"Processed symbols: {total_symbols}")
    print(f"Governed event states generated: {total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_historical_states(INPUT_PATH, OUTPUT_PATH))
