// Frozen rational constants — must match tools/cohort_trajectory_extract_20260625.py
const BETA = 37 / 64;
const CONTESTED_WEIGHT = 27 / 64;
const MOTION_WEIGHT = 3 / 5;
const MOTION_POWER = 5 / 4;
const REVERSAL_BALANCE_POWER = 16;
const CARRY_BALANCE_POWER = 4;
const BURDEN_SCALE = 1 / 128;
const V3_TIE_EPS = 1e-12;

function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

/**
 * Compute V3 basin coupled read from a tuple snapshot.
 * All inputs are floats; nulls -> return null.
 *
 * DO NOT MODIFY THE FORMULAS. This is the deterministic coupled math.
 * Any scalar override on individual fields undoes the coupling and
 * re-introduces the flattening pattern documented in
 * KERNEL_PHILOSOPHY.md §3.
 */
export function computeV3Basin(tuple) {
  const required = ["S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"];
  for (const f of required) {
    const v = tuple[f];
    if (v === null || v === undefined || !Number.isFinite(Number(v))) return null;
  }
  const S_UF     = Number(tuple.S_UF);
  const R_UF     = Number(tuple.R_UF);
  const D_k      = Number(tuple.D_k);
  const M_k      = Number(tuple.M_k);
  const R_rev_k  = Number(tuple.R_rev_k);
  const U_star_k = Number(tuple.U_star_k);
  const C_k      = Number(tuple.C_k);
  const P_k      = Number(tuple.P_k);
  const B_k      = Number(tuple.B_k);

  const M_hat = clamp(M_k, -1, 1);

  const s = S_UF - U_star_k;
  const r = R_UF - U_star_k;
  const s_pos = Math.max(s, 0);
  const r_pos = Math.max(r, 0);

  const core      = Math.min(s_pos, r_pos);
  const edge      = Math.max(s_pos, r_pos) - core;
  const live      = core + BETA * edge;
  const contested = CONTESTED_WEIGHT * edge;
  const balance   = core / (core + edge + 1e-12);
  const rupture   = Math.max(0, -Math.max(s, r));

  const D_nonadverse = (1 + D_k) / 2;
  const D_adverse    = Math.max(0, -D_k);
  const M_continue   = (1 + M_hat) / 2;
  const M_bend       = (1 - M_hat) / 2;

  const motion = Math.pow(
    MOTION_WEIGHT * Math.pow(D_nonadverse, MOTION_POWER)
    + (1 - MOTION_WEIGHT) * Math.pow(M_continue, MOTION_POWER),
    1 / MOTION_POWER,
  );

  const adverse_break  = D_adverse * M_bend;
  const reversal_break = R_rev_k * Math.pow(1 - balance, REVERSAL_BALANCE_POWER);
  const carry_break    = (-B_k) * R_rev_k
                       * Math.pow(1 - balance, CARRY_BALANCE_POWER)
                       * (1 - adverse_break);
  const burden         = BURDEN_SCALE * (C_k / (1 + C_k)) * (P_k / (1 + P_k));
  const break_agreement = Math.max(adverse_break, reversal_break, carry_break);

  const accumulate_basin = live * motion * (1 - R_rev_k) * (1 - adverse_break) * (1 - burden);
  const hold_basin       = contested * (1 - break_agreement)
                         + live * R_rev_k * balance
                         + live * (1 - R_rev_k) * ((1 - motion) * (1 - adverse_break) + motion * burden);
  const avoid_basin      = rupture + (live + contested) * break_agreement;

  const max_b = Math.max(accumulate_basin, hold_basin, avoid_basin);
  const near_acc  = Math.abs(max_b - accumulate_basin) <= V3_TIE_EPS;
  const near_hold = Math.abs(max_b - hold_basin)        <= V3_TIE_EPS;
  const near_avd  = Math.abs(max_b - avoid_basin)       <= V3_TIE_EPS;
  const n_near = Number(near_acc) + Number(near_hold) + Number(near_avd);
  let decision_argmax;
  if (n_near > 1) decision_argmax = "Tie";
  else if (near_acc) decision_argmax = "Accumulate";
  else if (near_hold) decision_argmax = "Hold";
  else decision_argmax = "Avoid";

  return {
    s, r, core, edge, live, contested, balance, rupture,
    D_nonadverse, D_adverse, M_continue, M_bend, motion,
    adverse_break, reversal_break, carry_break, burden, break_agreement,
    accumulate_basin, hold_basin, avoid_basin,
    decision_argmax,
  };
}
