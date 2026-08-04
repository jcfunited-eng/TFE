# UF/DSF Kernel — canonical L0–L4 (filed from Joe, 2026-08-04)

Complete UF/DSF processing inside the neuron. This is the kernel.

## L0 — structural evaluation and Negative Space
Displacement: dF_i(t) = F_i(t) - F_i(t-dt)
Window mean: Fbar_{i,W}(t) = (1/W) sum_{b=0..W-1} F_i(t-b dt)
Dispersion: sigma_i(t) = (1/W) sum_{b=0..W-1} || F_i(t-b dt) - Fbar_{i,W}(t) ||^2
Curvature: kappa_i(t) = || F_i(t+dt) - 2 F_i(t) + F_i(t-dt) ||
Negative Space: N_i(t) = 1 iff sigma_i < sigma_min AND ||dF_i|| < delta_min AND kappa_i < kappa_min, else 0
SEV_i(t) = ( F_i, dF_i, sigma_i, kappa_i, r_i, N_i )
Negative Space is actual L0 structural state — never a later reward/label/absence score.
Perturbation invariant: || SEV_i(F+eps) - SEV_i(F) || <= C_SEV ||eps||

## L1 — gates and UF lattice geometry
Deviation: D_i(t) = a1 ||dF_i|| + a2 sigma_i + a3 kappa_i
Gate boundary: D_i(t) >= tau_D
Gate: G_ik = [t_a, t_b] with D_i(t) < tau_D for all t in (t_a, t_b)
TVR_ik = (T_ik, V_ik, R_ik):
  T_ik = t_b - t_a
  V_ik = integral_{t_a}^{t_b} ( b1 ||dF_i|| + b2 sigma_i + b3 kappa_i ) dt
  R_ik = integral_{t_a}^{t_b} r_i(t) dt
UF projection on lattice l: P_l(G_ik) = ( floor(T/h1_l), floor(V/h2_l), floor(R/h3_l) )
UF lattice divergence: C_ik = | { P_1(G_ik), ..., P_L(G_ik) } |
Gate drift: delta_g(G_ik) = || mu_ik - mu_{i,k-1} ||
C_ik is UF projection divergence — not global Coh, not coupling, not a cognitive mosaic.

## L2 — interpretive structural field
Contrast: CV_ik = TVR_ik - mu_ik
Structural score: S_ik = g1 w_ik + g2 ||CV_ik||/||CV||max + g3 * 1/(1+C_ik)
Uncertainty: U_ik = l1 (C_ik - 1)/(L-1) + l2 delta_g/delta_max + l3 N_i(G_ik)
Anomaly suppression: IAS_ik = 1 iff U_ik > U_max
ISF_ik = ( w_ik, CV_ik, S_ik, Reg_ik, U_ik, IAS_ik )
Negative Space causally enters uncertainty here.

## L3 — resonance
R_vec_ik = ( w_ik, ||CV||/||CV||max, S_ik, 1/(1+C_ik), 1-U_ik )
R_i(k) = (1/Z) ( l1 w + l2 ||CV||/max + l3 S + l4 1/(1+C) + l5 (1-U) ), Z = sum l_b
Hysteresis: Hyst_ik = 1 iff |R_i(k) - R_i(k-1)| > h_max
Contextual gating: g_ik = 1 iff U <= U_max AND IAS = 0 AND Hyst = 0
Unified Resonance Field: URF_ik = g_ik R_i(k)

## L4 — seven-field DSF
dR_i(k) = R_i(k) - R_i(k-1)
Direction D_ik: +1 / 0 / -1 vs eps_D
Momentum: M_ik = R_i(k) - 2 R_i(k-1) + R_i(k-2)
Reversal: R_rev = 1 iff D_ik * D_{i,k-1} < 0
Adjusted uncertainty: U*_ik = U + eta_H Hyst + eta_IAS IAS
Pressure: P_ik = | D_ik - D_{i,k-1} |
Breathing: B_ik = clamp( B_{i,k-1} + xi (1-U*) dR - chi U*, B_min, B_max )
Complete local DSF delivery: X_ik = ( D, M, R_rev, U*, C, P, B )
