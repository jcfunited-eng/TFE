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
GRID_RHO_POINTS = 121
GRID_ETA_POINTS = 241
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
class FourPhaseCandidate:
    name: str
    a_expr: str
    alpha_expr: str
    xi_expr: str


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
    chi = delta / (1.0 + delta)
    q = (1.0 - point.R_rev_k) / ((1.0 + point.C_k) * (1.0 + point.P_k))
    return {"s": s, "r": r, "k": k, "g": g, "u": u, "v": v, "delta": delta, "chi": chi, "q": q}


def candidate_catalog() -> list[FourPhaseCandidate]:
    return [
        FourPhaseCandidate("family_phase_g_a", "q * max(g, 0)", "chi - q", "q * u - chi"),
        FourPhaseCandidate("family_phase_g_b", "q * max(g, 0)", "chi - q * max(v + 1, 0)", "q * (u + v) - chi"),
        FourPhaseCandidate("family_phase_g_abs", "q * sqrt(g * g)", "chi - q", "q * u - chi"),
    ]


def eval_expr(expr: str, inv: dict[str, float]) -> float:
    scope = {"max": max, "sqrt": np.sqrt}
    return float(eval(expr, {"__builtins__": {}}, {**scope, **inv}))


def potential(rho: np.ndarray, eta: np.ndarray, a: float, alpha: float, xi: float) -> np.ndarray:
    return (((rho * rho - a) ** 2) / 4.0) + (rho * rho) * ((alpha / 2.0) * (eta * eta) + (eta**4) / 4.0 - (xi / 3.0) * (eta**3))


def deterministic_ranges(paths: dict[str, list[PrimitivePoint]]) -> dict[str, float]:
    invs = [invariant_coordinates(point) for points in paths.values() for point in points]
    max_abs = lambda key: max(abs(inv[key]) for inv in invs)
    rho_max = max(1.0, max_abs("k"), max_abs("g"), max_abs("u"), max_abs("v"), max_abs("q"))
    eta_max = max(1.0, max_abs("k"), max_abs("g"), max_abs("u"), max_abs("v"), max_abs("q"))
    epsilon_rho = rho_max / (GRID_RHO_POINTS - 1)
    epsilon_eta = eta_max / (GRID_ETA_POINTS - 1)
    return {
        "rho_max": float(rho_max),
        "eta_max": float(eta_max),
        "epsilon_rho": float(epsilon_rho),
        "epsilon_eta": float(epsilon_eta),
    }


def phase_from_point(rho: float, eta: float, epsilon_rho: float, epsilon_eta: float) -> str:
    if rho <= epsilon_rho:
        return "black"
    if abs(eta) <= epsilon_eta:
        return "yellow"
    if eta > epsilon_eta:
        return "green"
    return "red"


def project_phase(phase: str) -> str:
    if phase == "green":
        return "Accumulate"
    if phase == "red":
        return "Avoid"
    return "Hold"


def evaluate_candidate(
    paths: dict[str, list[PrimitivePoint]],
    candidate: FourPhaseCandidate,
    ranges: dict[str, float],
) -> dict[str, list[dict[str, Any]]]:
    rho_axis = np.linspace(0.0, ranges["rho_max"], GRID_RHO_POINTS)
    eta_axis = np.linspace(-ranges["eta_max"], ranges["eta_max"], GRID_ETA_POINTS)
    rho_grid, eta_grid = np.meshgrid(rho_axis, eta_axis, indexing="ij")
    out: dict[str, list[dict[str, Any]]] = {}
    for path_name, points in paths.items():
        path_rows = []
        for idx, point in enumerate(points):
            inv = invariant_coordinates(point)
            a = eval_expr(candidate.a_expr, inv)
            alpha = eval_expr(candidate.alpha_expr, inv)
            xi = eval_expr(candidate.xi_expr, inv)
            phi = potential(rho_grid, eta_grid, a, alpha, xi)
            min_val = float(phi.min())
            minima_idx = np.argwhere(np.abs(phi - min_val) <= MINIMA_TIE_EPS)
            minima = []
            phases = set()
            for rho_i, eta_i in minima_idx:
                rho = float(rho_axis[rho_i])
                eta = float(eta_axis[eta_i])
                phase = phase_from_point(rho, eta, ranges["epsilon_rho"], ranges["epsilon_eta"])
                phases.add(phase)
                minima.append({"rho": rho, "eta": eta, "phi": float(phi[rho_i, eta_i]), "phase": phase})
            if not minima:
                rho = float(rho_axis[0])
                eta = float(eta_axis[0])
                phase = phase_from_point(rho, eta, ranges["epsilon_rho"], ranges["epsilon_eta"])
                minima = [{"rho": rho, "eta": eta, "phi": min_val, "phase": phase}]
                phases = {phase}
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
            path_rows.append(
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
                    "controls": {"a": a, "alpha": alpha, "xi": xi},
                    "global_minima": minima,
                }
            )
        out[path_name] = path_rows
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
        tendencies = point["tendencies"]
        if tendencies["accumulate_tendency"] == 0 and tendencies["hold_tendency"] == 0 and tendencies["avoid_tendency"] == 0:
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


def forced_conclusion(path_a_ok: bool, path_c_ok: bool, other_paths_ok: bool) -> str:
    if path_a_ok and path_c_ok and other_paths_ok:
        return "4-phase branch becomes the best UFC lead and should move to fixed-snapshot baseline comparison"
    return "4-phase branch is structurally non-viable"


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
    path_c = best_score["path_audit"]["path_C_constructive_to_covered_rupture"]
    path_a_ok = path_a["accepted"] and path_a["phase_transition_sequence"][-1] == "red" and "forbidden_accumulate_to_avoid_jump" not in path_a["acceptance_failures"]
    path_c_ok = path_c["accepted"]
    other_paths_ok = best_score["accepted_paths"] >= baseline_score["accepted_paths"]
    final_conclusion = forced_conclusion(path_a_ok, path_c_ok, other_paths_ok)

    candidates_json = {
        "generated_at_utc": utc_iso(),
        "normal_form": "Phi(rho,eta)=((rho*rho-a)^2)/4 + rho*rho * ((alpha/2)*eta*eta + (eta**4)/4 - (xi/3)*eta**3)",
        "grid_spec": {
            "rho_points": GRID_RHO_POINTS,
            "eta_points": GRID_ETA_POINTS,
            "rho_range": [0.0, ranges["rho_max"]],
            "eta_range": [-ranges["eta_max"], ranges["eta_max"]],
            "epsilon_rho": ranges["epsilon_rho"],
            "epsilon_eta": ranges["epsilon_eta"],
            "range_basis": "deterministic maxima over observed invariant ranges from the fixed deformation-path primitive set",
        },
        "candidates": [
            {"name": c.name, "a": c.a_expr, "alpha": c.alpha_expr, "xi": c.xi_expr}
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
        "path_c_ok": path_c_ok,
        "other_paths_ok": other_paths_ok,
        "grid_spec": candidates_json["grid_spec"],
        "scorecards": scorecards,
    }

    audit_md = (
        "# UFC Four Phase Path Audit V5\n\n"
        f"## Forced Conclusion\n- `{final_conclusion}`\n\n"
        f"## Best Candidate\n- `{best_score['candidate_name']}` with `{best_score['accepted_paths']}/{best_score['total_paths']}` paths accepted\n\n"
        f"## Decision Gate\n- path_A ok: `{path_a_ok}`\n"
        f"- path_C ok: `{path_c_ok}`\n"
        f"- other accepted paths retained: `{other_paths_ok}`\n\n"
        "## Grid Spec\n"
        f"- rho range: `[0, {ranges['rho_max']}]`\n"
        f"- eta range: `[-{ranges['eta_max']}, {ranges['eta_max']}]`\n"
        f"- epsilon_rho: `{ranges['epsilon_rho']}`\n"
        f"- epsilon_eta: `{ranges['epsilon_eta']}`\n\n"
        "## Candidate Summary\n"
        + "\n".join(
            f"- `{name}`: `{score['accepted_paths']}/{score['total_paths']}`"
            for name, score in scorecards.items()
        )
        + "\n"
    )

    candidates_path = BACKUPS / f"dsf_ufc_four_phase_candidates_v5_{stamp}.json"
    audit_json_path = BACKUPS / f"dsf_ufc_four_phase_path_audit_v5_{stamp}.json"
    audit_md_path = BACKUPS / f"dsf_ufc_four_phase_path_audit_v5_{stamp}.md"

    write_json(candidates_path, candidates_json)
    write_json(audit_json_path, audit_json)
    write_markdown(audit_md_path, audit_md)

    send_slack_completion(
        {
            "task": "ufc four-phase v5 identification complete",
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
                "path_c_ok": path_c_ok,
                "other_paths_ok": other_paths_ok,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
