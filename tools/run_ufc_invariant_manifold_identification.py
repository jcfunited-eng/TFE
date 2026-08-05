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
ROOT_EPS = 1e-8
MINIMA_TIE_EPS = 1e-7
ZERO_POSITION_EPS = 1e-6


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
class ManifoldCandidate:
    name: str
    a_expr: str
    b_expr: str


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


def positive_part(value: float) -> float:
    return max(value, 0.0)


def negative_part(value: float) -> float:
    return max(-value, 0.0)


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
    w = point.D_k * point.M_k * point.B_k
    q = (1.0 - point.R_rev_k) / ((1.0 + point.C_k) * (1.0 + point.P_k))
    return {"s": s, "r": r, "k": k, "g": g, "u": u, "v": v, "w": w, "q": q}


def candidate_catalog() -> list[ManifoldCandidate]:
    return [
        ManifoldCandidate("cusp_kq_ku", "-(k*q)", "-(k*u)"),
        ManifoldCandidate("cusp_gq_ku", "-(g*q)", "-(k*u)"),
        ManifoldCandidate("cusp_kq_gu", "-(k*q)", "-(g*u)"),
        ManifoldCandidate("cusp_gq_kw", "-(g*q)", "-(k*w)"),
        ManifoldCandidate("cusp_kq_kv", "-(k*q)", "-(k*v)"),
        ManifoldCandidate("cusp_gq_gw", "-(g*q)", "-(g*w)"),
    ]


def eval_expr(expr: str, inv: dict[str, float]) -> float:
    return float(eval(expr, {"__builtins__": {}}, inv))


def phi(z: float, A: float, B: float) -> float:
    return 0.25 * (z**4) + 0.5 * A * (z**2) + B * z


def cusp_decision(A: float, B: float) -> tuple[str, dict[str, Any]]:
    coeffs = [1.0, 0.0, A, B]
    roots = np.roots(coeffs)
    real_roots = sorted({round(float(root.real), 12) for root in roots if abs(root.imag) < ROOT_EPS})
    minima = []
    for root in real_roots:
        second = 3.0 * (root**2) + A
        if second > ROOT_EPS:
            minima.append((root, phi(root, A, B)))
    if not minima:
        minima.append((0.0, phi(0.0, A, B)))
    minima.sort(key=lambda item: item[1])
    best_value = minima[0][1]
    near_best = [item for item in minima if abs(item[1] - best_value) <= MINIMA_TIE_EPS]
    if len(near_best) != 1:
        decision = "Hold"
    else:
        z_min = near_best[0][0]
        if z_min > ZERO_POSITION_EPS:
            decision = "Accumulate"
        elif z_min < -ZERO_POSITION_EPS:
            decision = "Avoid"
        else:
            decision = "Hold"
    return decision, {
        "A": A,
        "B": B,
        "critical_points_real": real_roots,
        "minima": [{"z": z, "phi": val} for z, val in minima],
        "near_best_minima_count": len(near_best),
    }


def tendencies_from_decision(decision: str) -> dict[str, float]:
    return {
        "accumulate_tendency": 1.0 if decision == "Accumulate" else 0.0,
        "hold_tendency": 1.0 if decision == "Hold" else 0.0,
        "avoid_tendency": 1.0 if decision == "Avoid" else 0.0,
    }


def evaluate_manifold_candidate(paths: dict[str, list[PrimitivePoint]], candidate: ManifoldCandidate) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for path_name, points in paths.items():
        path_results = []
        for idx, point in enumerate(points):
            inv = invariant_coordinates(point)
            A = eval_expr(candidate.a_expr, inv)
            B = eval_expr(candidate.b_expr, inv)
            decision, normal_form = cusp_decision(A, B)
            path_results.append(
                {
                    "index": idx,
                    "decision": decision,
                    "dominant_relation": decision,
                    "tendencies": tendencies_from_decision(decision),
                    "invariants": inv,
                    "normal_form": normal_form,
                }
            )
        out[path_name] = path_results
    return out


def compress_sequence(decisions: list[str]) -> list[str]:
    out: list[str] = []
    for decision in decisions:
        if not out or out[-1] != decision:
            out.append(decision)
    return out


def first_transition_points(decisions: list[str]) -> list[dict[str, Any]]:
    out = []
    for idx in range(1, len(decisions)):
        if decisions[idx] != decisions[idx - 1]:
            out.append({"index": idx, "from": decisions[idx - 1], "to": decisions[idx]})
    return out


def continuity_score(decisions: list[str]) -> float:
    if len(decisions) <= 1:
        return 1.0
    transitions = sum(1 for idx in range(1, len(decisions)) if decisions[idx] != decisions[idx - 1])
    return 1.0 - transitions / (len(decisions) - 1)


def monotonicity_score(decisions: list[str], direction: str) -> float:
    values = [DECISION_ORDER[d] for d in decisions]
    deltas = [values[idx + 1] - values[idx] for idx in range(len(values) - 1)]
    if not deltas:
        return 1.0
    if direction == "nonincreasing":
        return sum(1 for delta in deltas if delta <= 0) / len(deltas)
    return sum(1 for delta in deltas if delta >= 0) / len(deltas)


def zero_basin_count(points: list[dict[str, Any]]) -> int:
    count = 0
    for point in points:
        tendencies = point["tendencies"]
        if tendencies["accumulate_tendency"] == 0 and tendencies["hold_tendency"] == 0 and tendencies["avoid_tendency"] == 0:
            count += 1
    return count


def missing_basin_count(decisions: list[str], expected: set[str]) -> int:
    return len(expected - set(decisions))


def has_accumulate_in_first_quarter(decisions: list[str]) -> bool:
    prefix_len = max(1, int(np.ceil(len(decisions) * 0.25)))
    return "Accumulate" in decisions[:prefix_len]


def path_rule_evaluation(path_name: str, decisions: list[str], points: list[dict[str, Any]]) -> dict[str, Any]:
    seq = compress_sequence(decisions)
    transitions = first_transition_points(decisions)
    failures: list[str] = []
    if path_name == "path_A_coverage_collapse":
        expected = {"Accumulate", "Hold", "Avoid"}
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if decisions[-1] != "Avoid":
            failures.append("end_not_avoid")
        if "Hold" not in decisions:
            failures.append("missing_hold_neighborhood")
        if any(seq[idx] == "Accumulate" and seq[idx + 1] == "Avoid" for idx in range(len(seq) - 1)):
            failures.append("forbidden_accumulate_to_avoid_jump")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_B_constructive_to_still":
        expected = {"Accumulate", "Hold"}
        if decisions[-1] != "Hold":
            failures.append("still_termination_not_hold")
        if "Accumulate" not in decisions:
            failures.append("no_constructive_accumulate_prefix")
        if "Avoid" in decisions:
            failures.append("avoid_entered_on_constructive_to_still")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_C_constructive_to_covered_rupture":
        expected = {"Accumulate", "Hold"}
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if seq == ["Hold"]:
            failures.append("constructive_path_collapsed_to_hold")
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
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if seq == ["Hold"]:
            failures.append("constructive_reversal_path_collapsed_to_hold")
        if decisions[-1] == "Accumulate":
            failures.append("reversal_failed_to_suppress_accumulate")
        if "Avoid" in decisions:
            failures.append("reversal_created_avoid_without_collapse")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    else:
        expected = {"Hold"}
        if decisions[-1] == "Accumulate":
            failures.append("reversal_failed_to_suppress_accumulate")
        if "Avoid" in decisions:
            failures.append("reversal_created_avoid_without_collapse")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    return {
        "path_transition_sequence": seq,
        "first_transition_points": transitions,
        "forbidden_jump_count": len([failure for failure in failures if "jump" in failure]),
        "missing_basin_count": missing_basin_count(decisions, expected),
        "zero_basin_count": zero_basin_count(points),
        "continuity_score": continuity_score(decisions),
        "monotonicity_score": monotonicity,
        "acceptance_failures": failures,
        "accepted": len(failures) == 0,
    }


def candidate_summary(candidate_name: str, path_results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    per_path = {}
    accepted_paths = 0
    failures = Counter()
    for path_name, points in path_results.items():
        decisions = [point["decision"] for point in points]
        audit = path_rule_evaluation(path_name, decisions, points)
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


def decide_forced_conclusion(best_manifold: dict[str, Any], baseline_score: dict[str, Any], tensor_best_accepted_paths: int) -> str:
    if best_manifold["accepted_paths"] > baseline_score["accepted_paths"] and best_manifold["accepted_paths"] > tensor_best_accepted_paths:
        return "invariant-manifold UFC candidate is viable and should replace the tensor line"
    if best_manifold["accepted_paths"] > tensor_best_accepted_paths and best_manifold["accepted_paths"] <= baseline_score["accepted_paths"]:
        return "invariant-manifold UFC candidate is promising but not yet baseline-safe"
    return "elegant primitive UFC not identifiable from current approved primitive tuple at this stage"


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
    candidates = candidate_catalog()
    candidate_results = {candidate.name: evaluate_manifold_candidate(paths, candidate) for candidate in candidates}
    scorecards = {name: candidate_summary(name, results) for name, results in candidate_results.items()}

    ranked = sorted(
        scorecards.values(),
        key=lambda score: (-score["accepted_paths"], sum(len(path["acceptance_failures"]) for path in score["path_audit"].values())),
    )
    best_manifold = ranked[0]

    strict_tensor = load_strict_tensor_scorecard()
    strict_scores = strict_tensor["scorecards"]
    baseline_score = strict_scores["baseline_runtime"]
    tensor_best_accepted_paths = max(
        score["accepted_paths"] for name, score in strict_scores.items() if name != "baseline_runtime"
    )
    forced_conclusion = decide_forced_conclusion(best_manifold, baseline_score, tensor_best_accepted_paths)

    candidates_json = {
        "generated_at_utc": utc_iso(),
        "normal_form": "Phi(z)=z^4/4 + (A/2) z^2 + B z",
        "candidates": [{"name": c.name, "A": c.a_expr, "B": c.b_expr} for c in candidates],
    }

    audit_json = {
        "generated_at_utc": utc_iso(),
        "forced_conclusion": forced_conclusion,
        "best_manifold_candidate": best_manifold["candidate_name"],
        "best_manifold_accepted_paths": best_manifold["accepted_paths"],
        "baseline_accepted_paths": baseline_score["accepted_paths"],
        "best_tensor_accepted_paths": tensor_best_accepted_paths,
        "scorecards": scorecards,
    }

    audit_md = (
        "# UFC Invariant Manifold Path Audit\n\n"
        f"## Forced Conclusion\n- `{forced_conclusion}`\n\n"
        f"## Best Manifold Candidate\n- `{best_manifold['candidate_name']}` with `{best_manifold['accepted_paths']}/{best_manifold['total_paths']}` paths accepted\n\n"
        f"## Baseline / Tensor Reference\n- baseline strict audit: `{baseline_score['accepted_paths']}/{baseline_score['total_paths']}`\n"
        f"- best tensor strict audit: `{tensor_best_accepted_paths}/{baseline_score['total_paths']}`\n\n"
        "## Manifold Candidates\n"
        + "\n".join(
            f"- `{name}`: `{score['accepted_paths']}/{score['total_paths']}`"
            for name, score in scorecards.items()
        )
        + "\n"
    )

    candidates_path = BACKUPS / f"dsf_ufc_invariant_manifold_candidates_{stamp}.json"
    audit_json_path = BACKUPS / f"dsf_ufc_invariant_manifold_path_audit_{stamp}.json"
    audit_md_path = BACKUPS / f"dsf_ufc_invariant_manifold_path_audit_{stamp}.md"

    write_json(candidates_path, candidates_json)
    write_json(audit_json_path, audit_json)
    write_markdown(audit_md_path, audit_md)

    send_slack_completion(
        {
            "task": "ufc invariant manifold identification complete",
            "forced_conclusion": forced_conclusion,
            "audit_artifact": str(audit_json_path),
        }
    )

    print(
        json.dumps(
            {
                "candidates_json": str(candidates_path),
                "audit_json": str(audit_json_path),
                "audit_md": str(audit_md_path),
                "forced_conclusion": forced_conclusion,
                "best_manifold_candidate": best_manifold["candidate_name"],
                "best_manifold_accepted_paths": best_manifold["accepted_paths"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
