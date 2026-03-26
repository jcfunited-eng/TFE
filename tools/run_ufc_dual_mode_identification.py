#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
STRICT_TENSOR_SCORECARD = BACKUPS / "dsf_ufc_candidate_path_scorecard_strict_20260321T233741Z.json"
DECISION_ORDER = {"Avoid": 0, "Hold": 1, "Accumulate": 2}
GRID_X_POINTS = 121
GRID_Y_POINTS = 121
MINIMA_TIE_EPS = 1e-7


@dataclass(frozen=True)
class PrimitivePoint:
    symbol: str
    barCount: int
    S_UF: float
    R_UF: float
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float


@dataclass(frozen=True)
class DualCandidate:
    name: str
    ax_expr: str
    ay_expr: str
    px_expr: str
    ny_expr: str
    g_expr: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def write_markdown(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def point_from_coordinates(
    path_name: str,
    idx: int,
    u_star: float,
    s: float,
    r: float,
    d_k: float,
    m_k: float,
    r_rev_k: float,
    c_k: float,
    p_k: float,
    b_k: float,
) -> PrimitivePoint:
    return PrimitivePoint(
        symbol=f"{path_name}_{idx}",
        barCount=252,
        S_UF=clip(u_star + s, 0.0, 1.0),
        R_UF=clip(u_star + r, 0.0, 1.0),
        D_k=clip(d_k, -1.0, 1.0),
        M_k=clip(m_k, -1.0, 1.0),
        R_rev_k=clip(r_rev_k, 0.0, 1.0),
        U_star_k=clip(u_star, 0.0, 1.0),
        C_k=max(0.0, c_k),
        P_k=max(0.0, p_k),
        B_k=clip(b_k, -1.0, 1.0),
    )


def interpolate(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def piecewise_transition(
    t: float,
    left: tuple[float, ...],
    mid: tuple[float, ...],
    right: tuple[float, ...],
) -> tuple[float, ...]:
    if t <= 0.5:
        local = t / 0.5
        return tuple(interpolate(left[i], mid[i], local) for i in range(len(left)))
    local = (t - 0.5) / 0.5
    return tuple(interpolate(mid[i], right[i], local) for i in range(len(left)))


def generate_paths(num_points: int = 41) -> dict[str, list[PrimitivePoint]]:
    paths: dict[str, list[PrimitivePoint]] = {}
    ts = np.linspace(0.0, 1.0, num_points)

    path_a = []
    for idx, t in enumerate(ts):
        u, s, r, d, m, rev, c, p, b = piecewise_transition(
            float(t),
            (0.25, 0.34, 0.28, 1.0, 0.6, 0.0, 0.0, 0.0, 0.45),
            (0.40, -0.02, 0.16, 0.5, 0.1, 0.0, 1.0, 1.0, 0.05),
            (0.55, -0.20, -0.18, -0.6, -0.6, 0.4, 3.0, 3.0, -0.7),
        )
        path_a.append(point_from_coordinates("path_A_coverage_collapse", idx, u, s, r, d, m, rev, c, p, b))
    paths["path_A_coverage_collapse"] = path_a

    path_b = []
    for idx, t in enumerate(ts):
        path_b.append(
            point_from_coordinates(
                "path_B_constructive_to_still",
                idx,
                0.30,
                0.24,
                0.20,
                interpolate(1.0, 0.0, float(t)),
                interpolate(0.6, 0.0, float(t)),
                0.0,
                0.5,
                0.5,
                interpolate(0.4, 0.0, float(t)),
            )
        )
    paths["path_B_constructive_to_still"] = path_b

    path_c = []
    for idx, t in enumerate(ts):
        path_c.append(
            point_from_coordinates(
                "path_C_constructive_to_covered_rupture",
                idx,
                0.30,
                0.24,
                0.20,
                interpolate(1.0, 0.1, float(t)),
                interpolate(0.6, -0.8, float(t)),
                interpolate(0.0, 0.8, float(t)),
                interpolate(0.5, 2.0, float(t)),
                interpolate(0.5, 2.0, float(t)),
                interpolate(0.4, -0.9, float(t)),
            )
        )
    paths["path_C_constructive_to_covered_rupture"] = path_c

    path_d = []
    for idx, t in enumerate(ts):
        path_d.append(
            point_from_coordinates(
                "path_D_one_sided_contested_carry_sweep",
                idx,
                0.40,
                -0.08,
                0.14,
                0.6,
                0.0,
                0.0,
                1.0,
                1.0,
                interpolate(0.4, -1.0, float(t)),
            )
        )
    paths["path_D_one_sided_contested_carry_sweep"] = path_d

    path_e_constructive = []
    path_e_still = []
    for idx, t in enumerate(ts):
        path_e_constructive.append(
            point_from_coordinates(
                "path_E_reversal_activation_constructive",
                idx,
                0.30,
                0.22,
                0.18,
                0.8,
                0.5,
                interpolate(0.0, 1.0, float(t)),
                0.5,
                0.5,
                0.35,
            )
        )
        path_e_still.append(
            point_from_coordinates(
                "path_E_reversal_activation_still",
                idx,
                0.30,
                0.22,
                0.18,
                0.0,
                0.0,
                interpolate(0.0, 1.0, float(t)),
                0.5,
                0.5,
                0.0,
            )
        )
    paths["path_E_reversal_activation_constructive"] = path_e_constructive
    paths["path_E_reversal_activation_still"] = path_e_still
    return paths


def invariant_coordinates(point: PrimitivePoint) -> dict[str, float]:
    s = point.S_UF - point.U_star_k
    r = point.R_UF - point.U_star_k
    k = s + r
    g = s * r
    u = point.D_k + point.M_k + point.B_k
    v = point.D_k * point.M_k + point.D_k * point.B_k + point.M_k * point.B_k
    delta = max(u * u - 3.0 * v, 0.0)
    q = (1.0 - point.R_rev_k) / ((1.0 + point.C_k) * (1.0 + point.P_k))
    cov_raw = max(g, 0.0)
    fail_raw = max(-g, 0.0)
    mpos_raw = max(u, 0.0)
    mneg_raw = max(-u, 0.0)
    cov = cov_raw / (1.0 + cov_raw)
    fail = fail_raw / (1.0 + fail_raw)
    mpos = mpos_raw / (1.0 + mpos_raw + delta)
    mneg = mneg_raw / (1.0 + mneg_raw)
    rup = ((1.0 - q) + delta) / (1.0 + (1.0 - q) + delta)
    return {
        "s": s,
        "r": r,
        "k": k,
        "g": g,
        "u": u,
        "v": v,
        "delta": delta,
        "q": q,
        "cov": cov,
        "fail": fail,
        "mpos": mpos,
        "mneg": mneg,
        "rup": rup,
    }


def candidate_catalog() -> list[DualCandidate]:
    return [
        DualCandidate(
            "family_dual_c",
            "cov * mpos",
            "rup * (cov + fail)",
            "cov * mpos",
            "rup * (1 + mneg)",
            "sqrt(max(k*k - 4*g, 0)) + max(-g, 0)",
        ),
        DualCandidate(
            "family_dual_c_variant",
            "cov * mpos * q",
            "rup * (cov + fail)",
            "cov * mpos",
            "rup * (1 + mneg)",
            "sqrt(max(k*k - 4*g, 0)) + max(-g, 0)",
        ),
    ]


def eval_expr(expr: str, inv: dict[str, float]) -> float:
    scope = {"max": max, "sqrt": np.sqrt}
    return float(eval(expr, {"__builtins__": {}}, {**scope, **inv}))


def potential(x: np.ndarray, y: np.ndarray, ax: float, ay: float, px: float, ny: float, g_couple: float) -> np.ndarray:
    return ((x**4) / 4.0) - (ax / 2.0) * (x**2) - px * x + ((y**4) / 4.0) - (ay / 2.0) * (y**2) - ny * y + g_couple * (x**2) * (y**2)


def deterministic_ranges(paths: dict[str, list[PrimitivePoint]]) -> dict[str, float]:
    invs = [invariant_coordinates(point) for points in paths.values() for point in points]
    max_abs = lambda key: max(abs(inv[key]) for inv in invs)
    amp_max = max(1.0, max_abs("k"), max_abs("g"), max_abs("u"), max_abs("v"), max_abs("q"))
    eps = amp_max / (GRID_X_POINTS - 1)
    return {"amp_max": float(amp_max), "epsilon": float(eps)}


def phase_from_point(x: float, y: float, eps: float) -> str:
    if x > eps and y <= eps:
        return "green"
    if x > eps and y > eps:
        return "yellow"
    if x <= eps and y <= eps:
        return "black"
    return "red"


def project_phase(phase: str) -> str:
    if phase == "green":
        return "Accumulate"
    if phase == "red":
        return "Avoid"
    return "Hold"


def evaluate_candidate(paths: dict[str, list[PrimitivePoint]], candidate: DualCandidate, ranges: dict[str, float]) -> dict[str, list[dict[str, Any]]]:
    x_axis = np.linspace(0.0, ranges["amp_max"], GRID_X_POINTS)
    y_axis = np.linspace(0.0, ranges["amp_max"], GRID_Y_POINTS)
    x_grid, y_grid = np.meshgrid(x_axis, y_axis, indexing="ij")
    out: dict[str, list[dict[str, Any]]] = {}
    for path_name, points in paths.items():
        rows = []
        for idx, point in enumerate(points):
            inv = invariant_coordinates(point)
            ax = eval_expr(candidate.ax_expr, inv)
            ay = eval_expr(candidate.ay_expr, inv)
            px = eval_expr(candidate.px_expr, inv)
            ny = eval_expr(candidate.ny_expr, inv)
            g_couple = eval_expr(candidate.g_expr, inv)
            phi = potential(x_grid, y_grid, ax, ay, px, ny, g_couple)
            min_val = float(phi.min())
            minima_idx = np.argwhere(np.abs(phi - min_val) <= MINIMA_TIE_EPS)
            minima = []
            phases = set()
            for x_i, y_i in minima_idx:
                x = float(x_axis[x_i])
                y = float(y_axis[y_i])
                phase = phase_from_point(x, y, ranges["epsilon"])
                phases.add(phase)
                minima.append({"x": x, "y": y, "phi": float(phi[x_i, y_i]), "phase": phase})
            if not minima:
                x = float(x_axis[0])
                y = float(y_axis[0])
                phase = phase_from_point(x, y, ranges["epsilon"])
                phases = {phase}
                minima = [{"x": x, "y": y, "phi": min_val, "phase": phase}]
            if phases == {"green"}:
                phase = "green"
            elif phases == {"red"}:
                phase = "red"
            elif "yellow" in phases:
                phase = "yellow"
            elif "black" in phases:
                phase = "black"
            else:
                phase = "yellow"
            decision = project_phase(phase)
            rows.append(
                {
                    "index": idx,
                    "decision": decision,
                    "internal_phase": phase,
                    "tendencies": {
                        "accumulate_tendency": 1.0 if decision == "Accumulate" else 0.0,
                        "hold_tendency": 1.0 if decision == "Hold" else 0.0,
                        "avoid_tendency": 1.0 if decision == "Avoid" else 0.0,
                    },
                    "invariants": inv,
                    "controls": {"Ax": ax, "Ay": ay, "Px": px, "Ny": ny, "G": g_couple},
                    "global_minima": minima,
                }
            )
        out[path_name] = rows
    return out


def compress_sequence(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if not out or out[-1] != value:
            out.append(value)
    return out


def first_transition_points(values: list[str]) -> list[dict[str, Any]]:
    out = []
    for idx in range(1, len(values)):
        if values[idx] != values[idx - 1]:
            out.append({"index": idx, "from": values[idx - 1], "to": values[idx]})
    return out


def continuity_score(values: list[str]) -> float:
    if len(values) <= 1:
        return 1.0
    transitions = sum(1 for idx in range(1, len(values)) if values[idx] != values[idx - 1])
    return 1.0 - transitions / (len(values) - 1)


def monotonicity_score(decisions: list[str], direction: str) -> float:
    values = [DECISION_ORDER[d] for d in decisions]
    deltas = [values[idx + 1] - values[idx] for idx in range(len(values) - 1)]
    if not deltas:
        return 1.0
    if direction == "nonincreasing":
        return sum(1 for delta in deltas if delta <= 0) / len(deltas)
    return sum(1 for delta in deltas if delta >= 0) / len(deltas)


def has_accumulate_in_first_quarter(decisions: list[str]) -> bool:
    prefix_len = max(1, int(np.ceil(len(decisions) * 0.25)))
    return "Accumulate" in decisions[:prefix_len]


def zero_basin_count(points: list[dict[str, Any]]) -> int:
    count = 0
    for point in points:
        t = point["tendencies"]
        if t["accumulate_tendency"] == 0 and t["hold_tendency"] == 0 and t["avoid_tendency"] == 0:
            count += 1
    return count


def missing_basin_count(decisions: list[str], expected: set[str]) -> int:
    return len(expected - set(decisions))


def path_rule_evaluation(path_name: str, points: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [point["decision"] for point in points]
    phases = [point["internal_phase"] for point in points]
    decision_seq = compress_sequence(decisions)
    phase_seq = compress_sequence(phases)
    failures: list[str] = []

    if path_name == "path_A_coverage_collapse":
        expected = {"Accumulate", "Hold", "Avoid"}
        if phases[0] != "green":
            failures.append("start_not_green")
        if phases[-1] != "red":
            failures.append("end_not_red")
        if not any(phase in {"yellow", "black"} for phase in phases):
            failures.append("missing_neutral_neighborhood")
        if any(decision_seq[idx] == "Accumulate" and decision_seq[idx + 1] == "Avoid" for idx in range(len(decision_seq) - 1)):
            failures.append("forbidden_accumulate_to_avoid_jump")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_B_constructive_to_still":
        expected = {"Accumulate", "Hold"}
        if phases[-1] not in {"yellow", "black"}:
            failures.append("still_termination_not_neutral")
        if "Accumulate" not in decisions:
            failures.append("no_constructive_accumulate_prefix")
        if "Avoid" in decisions:
            failures.append("avoid_entered_on_constructive_to_still")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_C_constructive_to_covered_rupture":
        expected = {"Accumulate", "Hold"}
        if phases[0] != "green":
            failures.append("start_not_green")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("rupture_endpoint_still_accumulate")
        if decisions.count("Hold") < decisions.count("Avoid"):
            failures.append("hold_not_primary_through_rupture_rotation")
        if not any(phase in {"yellow", "black"} for phase in phases[:-1]):
            failures.append("missing_neutral_before_rupture")
        if zero_basin_count(points) > 0:
            failures.append("zero_basin_swamp_present")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_D_one_sided_contested_carry_sweep":
        expected = {"Hold"}
        half = len(decisions) // 2
        if decisions[:half].count("Avoid") > decisions[:half].count("Hold"):
            failures.append("mild_damage_region_mainly_avoid")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_E_reversal_activation_constructive":
        expected = {"Accumulate", "Hold"}
        if phases[0] != "green":
            failures.append("start_not_green")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("reversal_failed_to_suppress_accumulate")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    else:
        expected = {"Hold"}
        if phases[-1] not in {"yellow", "black"}:
            failures.append("still_reversal_not_neutral")
        if "Avoid" in decisions:
            failures.append("reversal_created_avoid_without_collapse")
        monotonicity = monotonicity_score(decisions, "nonincreasing")

    return {
        "decision_transition_sequence": decision_seq,
        "phase_transition_sequence": phase_seq,
        "first_decision_transition_points": first_transition_points(decisions),
        "first_phase_transition_points": first_transition_points(phases),
        "forbidden_jump_count": len([failure for failure in failures if "jump" in failure]),
        "missing_basin_count": missing_basin_count(decisions, expected),
        "zero_basin_count": zero_basin_count(points),
        "continuity_score": continuity_score(decisions),
        "phase_continuity_score": continuity_score(phases),
        "monotonicity_score": monotonicity,
        "acceptance_failures": failures,
        "accepted": len(failures) == 0,
    }


def candidate_summary(candidate_name: str, path_results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    per_path = {}
    accepted_paths = 0
    failures = Counter()
    for path_name, points in path_results.items():
        audit = path_rule_evaluation(path_name, points)
        per_path[path_name] = audit
        if audit["accepted"]:
            accepted_paths += 1
        failures.update(audit["acceptance_failures"])
    return {
        "candidate_name": candidate_name,
        "accepted_paths": accepted_paths,
        "total_paths": len(path_results),
        "path_audit": per_path,
        "failure_histogram": dict(failures),
    }


def load_strict_tensor_scorecard() -> dict[str, Any]:
    return json.loads(STRICT_TENSOR_SCORECARD.read_text(encoding="utf-8"))


def forced_conclusion(path_a_ok: bool, path_b_ok: bool, path_c_ok: bool, path_e_ok: bool, best_vs_baseline: bool) -> str:
    if path_a_ok and path_b_ok and path_c_ok and path_e_ok and best_vs_baseline:
        return "dual-mode UFC candidate is viable and should replace the 4-phase branch as the best elegant UFC lead"
    if path_a_ok and path_e_ok and (path_b_ok or path_c_ok):
        return "dual-mode UFC candidate is promising but not yet baseline-safe"
    return "current primitive tuple still does not support a safe coefficient-free UFC under the tested internal-phase families"


def send_slack_completion(event: dict[str, Any]) -> None:
    payload = json.dumps(event)
    subprocess.run(
        ["bash", "-lc", f"printf '%s\\n' {json.dumps(payload)} | /workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh"],
        cwd=str(REPO_ROOT),
        check=True,
    )


def main() -> int:
    stamp = utc_stamp()
    paths = generate_paths()
    ranges = deterministic_ranges(paths)
    candidates = candidate_catalog()
    candidate_results = {candidate.name: evaluate_candidate(paths, candidate, ranges) for candidate in candidates}
    scorecards = {name: candidate_summary(name, results) for name, results in candidate_results.items()}

    ranked = sorted(
        scorecards.values(),
        key=lambda score: (-score["accepted_paths"], sum(len(path["acceptance_failures"]) for path in score["path_audit"].values())),
    )
    best_score = ranked[0]

    strict_tensor = load_strict_tensor_scorecard()
    baseline_score = strict_tensor["scorecards"]["baseline_runtime"]

    path_a = best_score["path_audit"]["path_A_coverage_collapse"]
    path_b = best_score["path_audit"]["path_B_constructive_to_still"]
    path_c = best_score["path_audit"]["path_C_constructive_to_covered_rupture"]
    path_e = best_score["path_audit"]["path_E_reversal_activation_constructive"]

    path_a_ok = path_a["accepted"] and any(phase in {"yellow", "black"} for phase in path_a["phase_transition_sequence"][1:-1]) and "forbidden_accumulate_to_avoid_jump" not in path_a["acceptance_failures"]
    path_b_ok = path_b["accepted"] and path_b["phase_transition_sequence"][-1] in {"yellow", "black"}
    path_c_ok = path_c["accepted"] and path_c["phase_transition_sequence"][-1] != "green" and any(phase in {"yellow", "black"} for phase in path_c["phase_transition_sequence"][:-1])
    path_e_ok = path_e["accepted"]
    best_vs_baseline = best_score["accepted_paths"] >= baseline_score["accepted_paths"]
    final_conclusion = forced_conclusion(path_a_ok, path_b_ok, path_c_ok, path_e_ok, best_vs_baseline)

    candidates_json = {
        "generated_at_utc": utc_iso(),
        "normal_form": "Phi(x,y)=(x**4)/4 - (Ax/2)*x**2 - Px*x + (y**4)/4 - (Ay/2)*y**2 - Ny*y + G*x*x*y*y",
        "grid_spec": {
            "x_points": GRID_X_POINTS,
            "y_points": GRID_Y_POINTS,
            "range": [0.0, ranges["amp_max"]],
            "epsilon": ranges["epsilon"],
            "range_basis": "deterministic maxima over observed invariant ranges from the fixed deformation-path primitive set",
        },
        "candidates": [
            {
                "name": c.name,
                "Ax": c.ax_expr,
                "Ay": c.ay_expr,
                "Px": c.px_expr,
                "Ny": c.ny_expr,
                "G": c.g_expr,
            }
            for c in candidates
        ],
    }

    audit_json = {
        "generated_at_utc": utc_iso(),
        "forced_conclusion": final_conclusion,
        "best_candidate": best_score["candidate_name"],
        "best_candidate_accepted_paths": best_score["accepted_paths"],
        "baseline_accepted_paths": baseline_score["accepted_paths"],
        "path_a_ok": path_a_ok,
        "path_b_ok": path_b_ok,
        "path_c_ok": path_c_ok,
        "path_e_ok": path_e_ok,
        "grid_spec": candidates_json["grid_spec"],
        "scorecards": scorecards,
    }

    audit_md = (
        "# UFC Dual Mode Path Audit V2\n\n"
        f"## Forced Conclusion\n- `{final_conclusion}`\n\n"
        f"## Best Candidate\n- `{best_score['candidate_name']}` with `{best_score['accepted_paths']}/{best_score['total_paths']}` paths accepted\n\n"
        "## Decision Gate\n"
        f"- path_A ok: `{path_a_ok}`\n"
        f"- path_B ok: `{path_b_ok}`\n"
        f"- path_C ok: `{path_c_ok}`\n"
        f"- path_E ok: `{path_e_ok}`\n\n"
        "## Grid Spec\n"
        f"- x/y range: `[0, {ranges['amp_max']}]`\n"
        f"- epsilon: `{ranges['epsilon']}`\n\n"
        "## Candidate Summary\n"
        + "\n".join(
            f"- `{name}`: `{score['accepted_paths']}/{score['total_paths']}`"
            for name, score in scorecards.items()
        )
        + "\n"
    )

    candidates_path = BACKUPS / f"dsf_ufc_dual_mode_candidates_v2_{stamp}.json"
    audit_json_path = BACKUPS / f"dsf_ufc_dual_mode_path_audit_v2_{stamp}.json"
    audit_md_path = BACKUPS / f"dsf_ufc_dual_mode_path_audit_v2_{stamp}.md"

    write_json(candidates_path, candidates_json)
    write_json(audit_json_path, audit_json)
    write_markdown(audit_md_path, audit_md)

    send_slack_completion(
        {
            "task": "ufc dual-mode v2 identification complete",
            "forced_conclusion": final_conclusion,
            "audit_artifact": str(audit_json_path),
        }
    )

    print(
        json.dumps(
            {
                "candidates_json": str(candidates_path),
                "audit_json": str(audit_json_path),
                "audit_md": str(audit_md_path),
                "forced_conclusion": final_conclusion,
                "best_candidate": best_score["candidate_name"],
                "best_candidate_accepted_paths": best_score["accepted_paths"],
                "path_a_ok": path_a_ok,
                "path_b_ok": path_b_ok,
                "path_c_ok": path_c_ok,
                "path_e_ok": path_e_ok,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
