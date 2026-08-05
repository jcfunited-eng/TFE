#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
STRICT_SCORECARD = BACKUPS / "dsf_ufc_candidate_path_scorecard_strict_20260321T233741Z.json"

ALPHAS = [0.75, 1.0]
BETAS = [0.75, 1.0]
GAMMAS = [1.0]
LAMBDAS = [0.5, 1.0, 2.0]
DECISION_ORDER = {"Avoid": 0, "Hold": 1, "Accumulate": 2}
ITERATION_LIMIT = 64
CONVERGENCE_EPS = 1e-10
MINIMA_TIE_EPS = 1e-7
ROOT_TOL = 1e-9
BOUNDARY_TOL = 1e-10


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
class Candidate:
    alpha: float
    beta: float
    gamma: float
    lambda_: float

    @property
    def name(self) -> str:
        return f"rcg_a{self.alpha:g}_b{self.beta:g}_g{self.gamma:g}_l{self.lambda_:g}"


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


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
        symbol=path_name,
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


def candidate_catalog() -> list[Candidate]:
    return [
        Candidate(alpha=alpha, beta=beta, gamma=gamma, lambda_=lambda_)
        for alpha in ALPHAS
        for beta in BETAS
        for gamma in GAMMAS
        for lambda_ in LAMBDAS
    ]


def invariants(point: PrimitivePoint, prev: PrimitivePoint | None) -> dict[str, float]:
    s = point.S_UF - point.U_star_k
    r = point.R_UF - point.U_star_k
    k = s + r
    g = s * r
    u = point.D_k + point.M_k + point.B_k
    v = point.D_k * point.M_k + point.D_k * point.B_k + point.M_k * point.B_k
    raw_delta = max(u * u - 3.0 * v, 0.0)
    delta = raw_delta / (1.0 + raw_delta)
    q = (1.0 - point.R_rev_k) / ((1.0 + point.C_k) * (1.0 + point.P_k))
    cov_raw = max(g, 0.0)
    fail_raw = max(-g, 0.0)
    mpos_raw = max(u, 0.0)
    mneg_raw = max(-u, 0.0)
    cov = cov_raw / (1.0 + cov_raw)
    fail = fail_raw / (1.0 + fail_raw)
    mpos = mpos_raw / (1.0 + mpos_raw)
    mneg = mneg_raw / (1.0 + mneg_raw)

    if prev is None:
        rho_k = 0.0
    else:
        denom = prev.D_k * prev.D_k + prev.M_k * prev.M_k + prev.B_k * prev.B_k + 1e-12
        rho_k = (point.D_k * prev.D_k + point.M_k * prev.M_k + point.B_k * prev.B_k) / denom
    p = min(max(rho_k, 0.0), 1.0)
    h = 1.0 - p

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
        "rho_k": rho_k,
        "p": p,
        "h": h,
    }


def controls(candidate: Candidate, inv: dict[str, float]) -> dict[str, float]:
    ax = inv["q"] * (candidate.alpha * inv["cov"] + (1.0 - candidate.alpha) * inv["p"])
    px = inv["q"] * inv["cov"] * inv["mpos"] * inv["p"]
    ay = candidate.beta * inv["fail"] + (1.0 - candidate.beta) * max(inv["delta"], inv["h"])
    ny = (candidate.gamma * inv["fail"] + (1.0 - candidate.gamma) * max(inv["delta"], inv["h"])) * (1.0 + inv["mneg"])
    g_couple = candidate.lambda_ * (inv["fail"] + inv["delta"])
    return {"Ax": ax, "Px": px, "Ay": ay, "Ny": ny, "G": g_couple}


def phi(x: float, y: float, ctrl: dict[str, float]) -> float:
    return (
        (x**4) / 4.0
        - (ctrl["Ax"] / 2.0) * x * x
        - ctrl["Px"] * x
        + (y**4) / 4.0
        - (ctrl["Ay"] / 2.0) * y * y
        - ctrl["Ny"] * y
        + ctrl["G"] * x * x * y * y
    )


def nonnegative_cubic_stationary(a_term: float, linear_term: float) -> list[float]:
    roots = np.roots([1.0, 0.0, -a_term, -linear_term])
    values = [0.0]
    for root in roots:
        if abs(root.imag) <= ROOT_TOL and root.real >= -BOUNDARY_TOL:
            values.append(max(float(root.real), 0.0))
    deduped: list[float] = []
    for value in sorted(values):
        if not deduped or abs(value - deduped[-1]) > 1e-8:
            deduped.append(value)
    return deduped


def newton_interior(ctrl: dict[str, float], seed_x: float, seed_y: float) -> tuple[float, float] | None:
    x = max(seed_x, BOUNDARY_TOL)
    y = max(seed_y, BOUNDARY_TOL)
    for _ in range(ITERATION_LIMIT):
        f1 = x**3 - ctrl["Ax"] * x - ctrl["Px"] + 2.0 * ctrl["G"] * x * y * y
        f2 = y**3 - ctrl["Ay"] * y - ctrl["Ny"] + 2.0 * ctrl["G"] * x * x * y
        if abs(f1) <= CONVERGENCE_EPS and abs(f2) <= CONVERGENCE_EPS:
            break
        j11 = 3.0 * x * x - ctrl["Ax"] + 2.0 * ctrl["G"] * y * y
        j12 = 4.0 * ctrl["G"] * x * y
        j21 = 4.0 * ctrl["G"] * x * y
        j22 = 3.0 * y * y - ctrl["Ay"] + 2.0 * ctrl["G"] * x * x
        det = j11 * j22 - j12 * j21
        if abs(det) <= 1e-12:
            return None
        dx = (j22 * f1 - j12 * f2) / det
        dy = (-j21 * f1 + j11 * f2) / det
        x_next = x - dx
        y_next = y - dy
        if x_next < 0.0 or y_next < 0.0:
            return None
        if abs(x_next - x) <= CONVERGENCE_EPS and abs(y_next - y) <= CONVERGENCE_EPS:
            x, y = x_next, y_next
            break
        x, y = x_next, y_next
    if x <= BOUNDARY_TOL or y <= BOUNDARY_TOL:
        return None
    residual_1 = x**3 - ctrl["Ax"] * x - ctrl["Px"] + 2.0 * ctrl["G"] * x * y * y
    residual_2 = y**3 - ctrl["Ay"] * y - ctrl["Ny"] + 2.0 * ctrl["G"] * x * x * y
    if abs(residual_1) > 1e-6 or abs(residual_2) > 1e-6:
        return None
    return (x, y)


def admissible_minima(ctrl: dict[str, float]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [{"family": "black", "x": 0.0, "y": 0.0, "phi": phi(0.0, 0.0, ctrl)}]

    x_roots = nonnegative_cubic_stationary(ctrl["Ax"], ctrl["Px"])
    for x in x_roots:
        candidates.append({"family": "green", "x": x, "y": 0.0, "phi": phi(x, 0.0, ctrl)})

    y_roots = nonnegative_cubic_stationary(ctrl["Ay"], ctrl["Ny"])
    for y in y_roots:
        candidates.append({"family": "red", "x": 0.0, "y": y, "phi": phi(0.0, y, ctrl)})

    seeds = []
    positive_x = [x for x in x_roots if x > BOUNDARY_TOL]
    positive_y = [y for y in y_roots if y > BOUNDARY_TOL]
    if positive_x and positive_y:
        for x in positive_x:
            for y in positive_y:
                seeds.append((x, y))
    seeds.extend(
        [
            (max(positive_x or [1.0]), max(positive_y or [1.0])),
            (1.0, 1.0),
            (max(math.sqrt(max(ctrl["Ax"], 0.0)), BOUNDARY_TOL), max(math.sqrt(max(ctrl["Ay"], 0.0)), BOUNDARY_TOL)),
        ]
    )

    interior_seen: list[tuple[float, float]] = []
    for seed_x, seed_y in seeds:
        interior = newton_interior(ctrl, seed_x, seed_y)
        if interior is None:
            continue
        x, y = interior
        if any(abs(x - prev_x) <= 1e-7 and abs(y - prev_y) <= 1e-7 for prev_x, prev_y in interior_seen):
            continue
        interior_seen.append((x, y))
        candidates.append({"family": "yellow", "x": x, "y": y, "phi": phi(x, y, ctrl)})

    return candidates


def choose_global_minimum(ctrl: dict[str, float]) -> dict[str, Any]:
    candidates = admissible_minima(ctrl)
    min_phi = min(item["phi"] for item in candidates)
    minima = [item for item in candidates if abs(item["phi"] - min_phi) <= MINIMA_TIE_EPS]
    family_priority = {"yellow": 0, "green": 1, "red": 2, "black": 3}
    chosen = sorted(minima, key=lambda item: (family_priority[item["family"]], item["phi"], item["x"], item["y"]))[0]
    decision = {"green": "Accumulate", "yellow": "Hold", "black": "Hold", "red": "Avoid"}[chosen["family"]]
    return {
        "decision": decision,
        "family": chosen["family"],
        "chosen_minimum": chosen,
        "global_minima": minima,
    }


def evaluate_path(candidate: Candidate, points: list[PrimitivePoint]) -> list[dict[str, Any]]:
    out = []
    prev: PrimitivePoint | None = None
    for idx, point in enumerate(points):
        inv = invariants(point, prev)
        ctrl = controls(candidate, inv)
        minimum = choose_global_minimum(ctrl)
        out.append(
            {
                "index": idx,
                "decision": minimum["decision"],
                "family": minimum["family"],
                "invariants": inv,
                "controls": ctrl,
                "chosen_minimum": minimum["chosen_minimum"],
                "global_minima": minimum["global_minima"],
                "tendencies": {
                    "accumulate_tendency": 1.0 if minimum["decision"] == "Accumulate" else 0.0,
                    "hold_tendency": 1.0 if minimum["decision"] == "Hold" else 0.0,
                    "avoid_tendency": 1.0 if minimum["decision"] == "Avoid" else 0.0,
                },
            }
        )
        prev = point
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


def path_rule_evaluation(path_name: str, points: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [point["decision"] for point in points]
    families = [point["family"] for point in points]
    decision_seq = compress_sequence(decisions)
    family_seq = compress_sequence(families)
    failures: list[str] = []

    if path_name == "path_A_coverage_collapse":
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if decisions[-1] != "Avoid":
            failures.append("end_not_avoid")
        if "Hold" not in decisions:
            failures.append("missing_hold_neighborhood")
        if any(decision_seq[idx] == "Accumulate" and decision_seq[idx + 1] == "Avoid" for idx in range(len(decision_seq) - 1)):
            failures.append("forbidden_accumulate_to_avoid_jump")
        expected = {"Accumulate", "Hold", "Avoid"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_B_constructive_to_still":
        if decisions[-1] != "Hold":
            failures.append("still_termination_not_hold")
        if families[-1] == "green":
            failures.append("still_termination_green")
        if "Accumulate" not in decisions:
            failures.append("no_constructive_accumulate_prefix")
        if "Avoid" in decisions:
            failures.append("avoid_entered_on_constructive_to_still")
        expected = {"Accumulate", "Hold"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_C_constructive_to_covered_rupture":
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("rupture_endpoint_still_accumulate")
        if "Hold" not in decisions:
            failures.append("missing_hold_interval")
        if any(decision_seq[idx] == "Accumulate" and decision_seq[idx + 1] == "Avoid" for idx in range(len(decision_seq) - 1)):
            failures.append("direct_accumulate_to_avoid")
        expected = {"Accumulate", "Hold"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_D_one_sided_contested_carry_sweep":
        half = len(decisions) // 2
        if decisions[:half].count("Avoid") > decisions[:half].count("Hold"):
            failures.append("mild_damage_region_mainly_avoid")
        expected = {"Hold"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_E_reversal_activation_constructive":
        if decisions[0] != "Accumulate":
            failures.append("start_not_accumulate")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("reversal_failed_to_suppress_accumulate")
        if "Avoid" in decisions:
            failures.append("reversal_created_avoid_without_collapse")
        expected = {"Accumulate", "Hold"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    else:
        if decisions[-1] == "Accumulate":
            failures.append("still_reversal_failed_to_suppress")
        if "Avoid" in decisions:
            failures.append("still_reversal_created_avoid_without_collapse")
        expected = {"Hold"}
        monotonicity = monotonicity_score(decisions, "nonincreasing")

    return {
        "decision_transition_sequence": decision_seq,
        "family_transition_sequence": family_seq,
        "first_transition_points": first_transition_points(decisions),
        "continuity_score": continuity_score(decisions),
        "family_continuity_score": continuity_score(families),
        "monotonicity_score": monotonicity,
        "missing_basin_count": len(expected - set(decisions)),
        "acceptance_failures": failures,
        "accepted": len(failures) == 0,
    }


def candidate_summary(candidate: Candidate, path_results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    per_path = {}
    accepted_paths = 0
    failure_histogram = Counter()
    for path_name, points in path_results.items():
        audit = path_rule_evaluation(path_name, points)
        per_path[path_name] = audit
        if audit["accepted"]:
            accepted_paths += 1
        failure_histogram.update(audit["acceptance_failures"])
    return {
        "candidate": {
            "name": candidate.name,
            "alpha": candidate.alpha,
            "beta": candidate.beta,
            "gamma": candidate.gamma,
            "lambda": candidate.lambda_,
        },
        "accepted_paths": accepted_paths,
        "total_paths": len(path_results),
        "path_audit": per_path,
        "failure_histogram": dict(failure_histogram),
    }


def send_slack_completion(event: dict[str, Any]) -> None:
    payload = json.dumps(event)
    subprocess.run(
        ["bash", "-lc", f"printf '%s\\n' {json.dumps(payload)} | /workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh"],
        cwd=str(REPO_ROOT),
        check=True,
    )


def main() -> int:
    stamp = utc_stamp()
    baseline_score = load_json(STRICT_SCORECARD)["scorecards"]["baseline_runtime"]["accepted_paths"]
    paths = generate_paths()

    scorecards = []
    for candidate in candidate_catalog():
        path_results = {name: evaluate_path(candidate, points) for name, points in paths.items()}
        scorecards.append(candidate_summary(candidate, path_results))

    ranked = sorted(
        scorecards,
        key=lambda item: (
            -item["accepted_paths"],
            sum(len(path["acceptance_failures"]) for path in item["path_audit"].values()),
            item["candidate"]["alpha"],
            item["candidate"]["beta"],
            item["candidate"]["lambda"],
        ),
    )
    best = ranked[0]
    achieved_six = best["accepted_paths"] == 6
    if achieved_six:
        verdict = "transport-coupled governed UFC is viable and safer than baseline"
    else:
        verdict = "Elegant UFC not recovered under this governed retained-carry branch."

    audit_json = {
        "generated_at_utc": utc_iso(),
        "rejected_branch": {
            "name": "cosine_transport_scalar",
            "status": "rejected_without_run",
            "reason": "angle-only transport misreads aligned decay, dead-field carry, and reversal retention",
        },
        "branch_name": "Retained-Carry Governed Dual-Mode UFC (RCG-UFC)",
        "baseline_strict_score": baseline_score,
        "replacement_bar": 6,
        "achieved_six_of_six": achieved_six,
        "forced_conclusion": verdict,
        "best_candidate": best["candidate"],
        "scorecards": scorecards,
    }

    audit_md = (
        "# RCG-UFC Strict Path Audit\n\n"
        "## Decision Up Front\n"
        "- rejected branch: `tau_k = cosine transport`\n"
        "- rejection reason: angle-only transport misreads aligned decay, dead-field carry, and reversal retention\n\n"
        "## Forced Conclusion\n"
        f"- `{verdict}`\n\n"
        "## Best Combo\n"
        f"- name: `{best['candidate']['name']}`\n"
        f"- alpha: `{best['candidate']['alpha']}`\n"
        f"- beta: `{best['candidate']['beta']}`\n"
        f"- gamma: `{best['candidate']['gamma']}`\n"
        f"- lambda: `{best['candidate']['lambda']}`\n"
        f"- strict score: `{best['accepted_paths']}/6`\n"
        f"- any combo achieved 6/6: `{achieved_six}`\n\n"
        "## All 12 Combos\n"
        + "\n".join(
            f"- `{item['candidate']['name']}` -> `{item['accepted_paths']}/6` failures `{item['failure_histogram']}`"
            for item in ranked
        )
        + "\n"
    )

    audit_json_path = BACKUPS / f"dsf_ufc_transport_coupled_governed_path_audit_{stamp}.json"
    audit_md_path = BACKUPS / f"dsf_ufc_transport_coupled_governed_path_audit_{stamp}.md"
    selected_path = BACKUPS / f"dsf_ufc_transport_coupled_governed_selected_{stamp}.json"

    write_json(audit_json_path, audit_json)
    write_markdown(audit_md_path, audit_md)
    write_json(
        selected_path,
        {
            "generated_at_utc": utc_iso(),
            "forced_conclusion": verdict,
            "best_candidate": best["candidate"],
            "best_score": best["accepted_paths"],
            "achieved_six_of_six": achieved_six,
        },
    )

    send_slack_completion(
        {
            "task": "rcg-ufc retained-carry governed branch complete",
            "forced_conclusion": verdict,
            "artifact": str(audit_json_path),
        }
    )

    print(
        json.dumps(
            {
                "audit_json": str(audit_json_path),
                "audit_md": str(audit_md_path),
                "selected_json": str(selected_path),
                "forced_conclusion": verdict,
                "best_candidate": best["candidate"],
                "achieved_six_of_six": achieved_six,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
