"""The kernel as Joe's canon writes it (docs/UF_DSF_KERNEL_CANON_20260804.md),
fed the field the canon describes: F(t) = (Open, High, Low, Close, Volume).

Built from the two implementations in the repository, taking from each the
part that matches the canon:
  L0, L1  the literal file's operators on the 5-vector (tools/literal_kernel_ohlcv.py):
          ||dF||, sigma = mean ||F − Fbar||², kappa = ||F(t+1) − 2F(t) + F(t−1)||,
          D = ||dF|| + sigma + kappa, boundary D >= tau_D, TVR, lattices, C,
          mu_k = the gate's OWN mean, delta_g = ||mu_k − mu_{k−1}||.
  L2      the canon's formulas as uf_core/layer2.py has them (w from density
          chi/chi_max, psi = ||CV||/||CV||max, S, U with delta_g/delta_max, IAS,
          regime) — but CV_k = TVR_k − mu_k with the gate's own mean, as the
          canon says, not the mean over all gates.
  L3, L4  uf_core/layer3.py and layer4.py unchanged (R, Hyst, g, URF; D, M,
          R_rev, U*, P, B).
Relevance r(t) = 1 on every bar, as production has it (the canon leaves r to
the domain adapter). No log, no scaling, no history-wide mean anywhere.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import List

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))

from standalone_truth_kernel import KernelParameters                       # noqa: E402
from literal_kernel_ohlcv import compute_l0_sev, segment_l1_gates          # noqa: E402
from uf_core.layer1 import Gate                                             # noqa: E402
from uf_core.layer2 import (GateInterpretation, _compute_CV_vectors, _compute_density,  # noqa: E402
                            _compute_w_k_from_density, _compute_psi, _compute_S_k,
                            _compute_U_k, _compute_IAS_k, _classify_regime)
from uf_core.layer3 import compute_resonance                                # noqa: E402
from uf_core.layer4 import compute_directional_signal, compute_dsf          # noqa: E402


def interpret_local(gates_l1) -> List[GateInterpretation]:
    tvr_list = [g.TVR for g in gates_l1]
    C_k_list = [g.C for g in gates_l1]
    delta_g_list = [g.delta_g for g in gates_l1]
    N_gate_list = [g.N_gate for g in gates_l1]
    CV_list = [np.array(g.TVR, dtype=float) - g.mu for g in gates_l1]     # the gate's own mean (canon)
    chi_list = _compute_density(tvr_list)
    w_list = _compute_w_k_from_density(chi_list)
    psi_list, _ = _compute_psi(CV_list)
    S_list = _compute_S_k(w_list, psi_list, C_k_list)
    U_list = _compute_U_k(C_k_list, delta_g_list, N_gate_list)
    IAS_list = _compute_IAS_k(U_list)
    out = []
    for g, cv, w, S, U, IAS, chi, psi in zip(gates_l1, CV_list, w_list, S_list, U_list, IAS_list, chi_list, psi_list):
        T, V, R = g.TVR
        out.append(GateInterpretation(gate=Gate(g.t_a, g.t_b - 1), w_k=float(w), CV_k=tuple(map(float, cv)), S_k=float(S),
                                      U_k=float(U), IAS_k=int(IAS), regime=_classify_regime(chi, psi), C_k=int(g.C),
                                      delta_g=float(g.delta_g), N_gate=int(g.N_gate), T_k=float(T), V_k=float(V), R_k=float(R),
                                      chi_k=float(chi), psi_k=float(psi)))
    return out


def run(F: np.ndarray, tau_D: float = 0.20):
    p = KernelParameters(tau_D=tau_D)
    sevs = compute_l0_sev(F, p)
    for s in sevs:
        s.r = 1.0
    gates = segment_l1_gates(sevs, p)
    interps = interpret_local(gates)
    res = compute_resonance(interps)
    dsf = compute_dsf(compute_directional_signal(res))
    return sevs, gates, interps, res, dsf
