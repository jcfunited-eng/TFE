#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
BASELINE_RUNTIME = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision.ts"
UNIFIED_RUNTIME = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision-unified-field.ts"

DECISION_ORDER = {"Avoid": 0, "Hold": 1, "Accumulate": 2}
STRICT_CANDIDATE_ORDER = [
    "baseline_runtime",
    "current_unified_tensor_v5",
    "ufc_family_4_bounded_resolvent_reserve",
    "ufc_family_2_raw_tensor_spectral_orientation",
    "ufc_family_5_primitive_congruence_preconditioned_tensor",
]


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


def dsf_relations(point: PrimitivePoint) -> dict[str, float]:
    s = point.S_UF - point.U_star_k
    r = point.R_UF - point.U_star_k
    q_r = 1.0 - point.R_rev_k
    q_c = 1.0 / (1.0 + point.C_k)
    q_p = 1.0 / (1.0 + point.P_k)
    d_pos = positive_part(point.D_k)
    d_neg = negative_part(point.D_k)
    m_pos = positive_part(point.M_k)
    m_neg = negative_part(point.M_k)
    b_pos = positive_part(point.B_k)
    b_neg = negative_part(point.B_k)
    rupture = max(d_neg, m_neg, b_neg, 1.0 - q_r)
    forward = d_pos * m_pos * b_pos * q_r
    contest = d_pos * q_r * positive_part(1.0 - rupture)
    return {
        "s": s,
        "r": r,
        "q_r": q_r,
        "q_c": q_c,
        "q_p": q_p,
        "weak_coverage": min(s, r),
        "secondary_coverage": max(s, r),
        "trajectory_forward": forward,
        "trajectory_contest": contest,
        "trajectory_rupture": rupture,
    }


def tensor_components(point: PrimitivePoint) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rel = dsf_relations(point)
    tensor = np.array(
        [
            [rel["s"], 0.0, point.D_k, point.M_k, point.B_k],
            [0.0, rel["r"], point.D_k, point.M_k, point.B_k],
            [point.D_k, point.D_k, rel["q_r"], 0.0, 0.0],
            [point.M_k, point.M_k, 0.0, rel["q_c"], 0.0],
            [point.B_k, point.B_k, 0.0, 0.0, rel["q_p"]],
        ],
        dtype=float,
    )
    return tensor, tensor[:2, :2], tensor[2:, 2:], tensor[:2, 2:]


def invariant_bundle(tensor: np.ndarray, effective_reserve: np.ndarray | None = None) -> dict[str, Any]:
    eigvals, eigvecs = np.linalg.eigh(tensor)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    dominant = eigvecs[:, order[0]]
    off = tensor - np.diag(np.diag(tensor))
    inv = {
        "eigenvalues": [float(v) for v in eigvals],
        "positive_spectral_mass": float(np.maximum(eigvals, 0).sum()),
        "negative_spectral_mass": float(np.maximum(-eigvals, 0).sum()),
        "indefiniteness_mass": float(min(np.maximum(eigvals, 0).sum(), np.maximum(-eigvals, 0).sum())),
        "dominant_mode_signed_coupling": float(dominant.T @ off @ dominant),
    }
    if effective_reserve is not None:
        inv["effective_reserve_eigenvalues"] = [float(v) for v in np.sort(np.linalg.eigvalsh(effective_reserve))[::-1]]
    return inv


def tendencies_from_decision(decision: str) -> dict[str, float]:
    return {
        "accumulate_tendency": 1.0 if decision == "Accumulate" else 0.0,
        "hold_tendency": 1.0 if decision == "Hold" else 0.0,
        "avoid_tendency": 1.0 if decision == "Avoid" else 0.0,
    }


def family_2_raw_tensor_spectral_orientation(point: PrimitivePoint) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(point)
    inv = invariant_bundle(tensor)
    if inv["positive_spectral_mass"] > inv["negative_spectral_mass"] and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif inv["negative_spectral_mass"] > inv["positive_spectral_mass"] and inv["dominant_mode_signed_coupling"] < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "tendencies": tendencies_from_decision(decision), "invariants": inv}


def family_4_bounded_resolvent_reserve(point: PrimitivePoint) -> dict[str, Any]:
    tensor, reserve, admissibility, coupling = tensor_components(point)
    effective = reserve - coupling @ np.linalg.inv(np.eye(3) + admissibility) @ coupling.T
    inv = invariant_bundle(tensor, effective_reserve=effective)
    mu1, mu2 = inv["effective_reserve_eigenvalues"]
    if mu1 > 0 and mu2 > 0 and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif mu1 < 0 and mu2 < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "tendencies": tendencies_from_decision(decision), "invariants": inv}


def family_5_primitive_congruence_preconditioned_tensor(point: PrimitivePoint) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(point)
    rel = dsf_relations(point)
    metric_diag = np.array(
        [1.0 + abs(rel["s"]), 1.0 + abs(rel["r"]), 1.0 + rel["q_r"], 1.0 + rel["q_c"], 1.0 + rel["q_p"]],
        dtype=float,
    )
    root = np.diag(metric_diag ** -0.5)
    transformed = root @ tensor @ root
    inv = invariant_bundle(transformed)
    if inv["positive_spectral_mass"] > inv["negative_spectral_mass"] and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif inv["negative_spectral_mass"] > inv["positive_spectral_mass"] and inv["dominant_mode_signed_coupling"] < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "tendencies": tendencies_from_decision(decision), "invariants": inv}


PYTHON_CANDIDATES = {
    "ufc_family_4_bounded_resolvent_reserve": family_4_bounded_resolvent_reserve,
    "ufc_family_2_raw_tensor_spectral_orientation": family_2_raw_tensor_spectral_orientation,
    "ufc_family_5_primitive_congruence_preconditioned_tensor": family_5_primitive_congruence_preconditioned_tensor,
}


def evaluate_ts_runtime(runtime_path: Path, paths_payload: dict[str, Any], prefix: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=prefix) as temp_dir:
        points_path = Path(temp_dir) / "paths.json"
        out_path = Path(temp_dir) / "results.json"
        write_json(points_path, paths_payload)
        node_script = f"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const Module = require("module");
const WEB_ROOT = {json.dumps(str(WEB_ROOT))};
const runtimePath = {json.dumps(str(runtime_path))};
const pointsPath = {json.dumps(str(points_path))};
const outPath = {json.dumps(str(out_path))};
const requireFromWeb = Module.createRequire(path.join(WEB_ROOT, "package.json"));
const ts = requireFromWeb("typescript");

function loadModule(runtimeFile) {{
  const source = fs.readFileSync(runtimeFile, "utf8");
  const transpiled = ts.transpileModule(source, {{
    compilerOptions: {{
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    }},
  }}).outputText;
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "ufc-path-audit-"));
  const tempModule = path.join(tempDir, path.basename(runtimeFile).replace(/\\.ts$/, ".cjs"));
  fs.writeFileSync(tempModule, transpiled);
  return require(tempModule);
}}

const mod = loadModule(runtimePath);
const payload = JSON.parse(fs.readFileSync(pointsPath, "utf8"));
const out = {{}};
for (const [pathName, points] of Object.entries(payload.paths)) {{
  out[pathName] = points.map((point, idx) => {{
    const result = mod.computePrimitiveDynamicDecision(point, {{
      profileId: "ufc_deformation_path_audit_strict",
      generatedAtUtc: {json.dumps(utc_iso())},
      minBars: 252,
    }});
    const rel = result.termBreakdown ? result.termBreakdown.relationalFieldState : null;
    return {{
      index: idx,
      decision: result.decision,
      blockerCode: result.blockerCode,
      tendencies: rel ? {{
        accumulate_tendency: rel.accumulate_tendency ?? 0,
        hold_tendency: rel.hold_tendency ?? 0,
        avoid_tendency: rel.avoid_tendency ?? 0,
      }} : {{ accumulate_tendency: 0, hold_tendency: 0, avoid_tendency: 0 }},
      dominant_relation: rel ? rel.dominant_relation : null,
    }};
  }});
}}
fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + "\\n");
"""
        proc = subprocess.run(["node", "-e", node_script], cwd=str(REPO_ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit("strict deformation path TS evaluation failed\n" + proc.stderr[-4000:])
        return json.loads(out_path.read_text())


def path_points_payload(paths: dict[str, list[PrimitivePoint]]) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_iso(),
        "paths": {
            name: [
                {
                    "symbol": p.symbol,
                    "barCount": p.barCount,
                    "S_UF": p.S_UF,
                    "R_UF": p.R_UF,
                    "D_k": p.D_k,
                    "M_k": p.M_k,
                    "R_rev_k": p.R_rev_k,
                    "U_star_k": p.U_star_k,
                    "C_k": p.C_k,
                    "P_k": p.P_k,
                    "B_k": p.B_k,
                }
                for p in pts
            ]
            for name, pts in paths.items()
        },
    }


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


def evaluate_python_candidate(paths: dict[str, list[PrimitivePoint]], evaluator) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path_name, points in paths.items():
        out[path_name] = [
            {
                "index": idx,
                "decision": result["decision"],
                "tendencies": result["tendencies"],
                "dominant_relation": result["decision"],
                "invariants": result["invariants"],
            }
            for idx, result in enumerate(evaluator(point) for point in points)
        ]
    return out


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


def strict_forced_conclusion(scorecards: dict[str, Any]) -> str:
    baseline = scorecards["baseline_runtime"]
    ufc_names = [name for name in scorecards if name != "baseline_runtime"]
    ufc_scores = [scorecards[name] for name in ufc_names]
    viable_ufc = [score for score in ufc_scores if score["accepted_paths"] >= baseline["accepted_paths"]]
    if viable_ufc:
        return "one UFC candidate remains viable under strict audit"
    if baseline["accepted_paths"] > max(score["accepted_paths"] for score in ufc_scores):
        return "baseline remains only structurally acceptable candidate"
    return "no UFC candidate remains viable under strict audit"


def exact_missing_mechanism(scorecards: dict[str, Any]) -> list[str]:
    combined = Counter()
    for candidate_name, score in scorecards.items():
        if candidate_name == "baseline_runtime":
            continue
        combined.update(score["failure_histogram"])
    return [name for name, _ in combined.most_common(5)]


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
    payload = path_points_payload(paths)

    candidate_results = {
        "baseline_runtime": evaluate_ts_runtime(BASELINE_RUNTIME, payload, "ufc-path-strict-baseline-"),
        "current_unified_tensor_v5": evaluate_ts_runtime(UNIFIED_RUNTIME, payload, "ufc-path-strict-unified-"),
    }
    for name, evaluator in PYTHON_CANDIDATES.items():
        candidate_results[name] = evaluate_python_candidate(paths, evaluator)
    candidate_results = {name: candidate_results[name] for name in STRICT_CANDIDATE_ORDER}

    scorecards = {name: candidate_summary(name, results) for name, results in candidate_results.items()}
    forced = strict_forced_conclusion(scorecards)
    missing = exact_missing_mechanism(scorecards)

    audit_json = {
        "generated_at_utc": utc_iso(),
        "audit_mode": "strict_constructive_prefix",
        "candidates": STRICT_CANDIDATE_ORDER,
        "forced_conclusion": forced,
        "exact_missing_mechanism": missing,
    }

    scorecard_json = {
        "generated_at_utc": utc_iso(),
        "audit_mode": "strict_constructive_prefix",
        "scorecards": scorecards,
        "forced_conclusion": forced,
        "exact_missing_mechanism": missing,
    }

    audit_md = (
        "# UFC Deformation Path Audit Strict\n\n"
        f"## Forced Conclusion\n- `{forced}`\n\n"
        "## Exact Missing Mechanism\n"
        + "\n".join(f"- `{item}`" for item in missing)
        + "\n\n## Candidate Summary\n"
        + "\n".join(
            f"- `{name}`: accepted paths `{score['accepted_paths']}/{score['total_paths']}`"
            for name, score in scorecards.items()
        )
        + "\n"
    )

    audit_json_path = BACKUPS / f"dsf_ufc_deformation_path_audit_strict_{stamp}.json"
    audit_md_path = BACKUPS / f"dsf_ufc_deformation_path_audit_strict_{stamp}.md"
    scorecard_path = BACKUPS / f"dsf_ufc_candidate_path_scorecard_strict_{stamp}.json"

    write_json(audit_json_path, audit_json)
    write_markdown(audit_md_path, audit_md)
    write_json(scorecard_path, scorecard_json)

    send_slack_completion(
        {
            "task": "ufc deformation path strict audit complete",
            "forced_conclusion": forced,
            "audit_artifact": str(audit_json_path),
        }
    )

    print(
        json.dumps(
            {
                "audit_json": str(audit_json_path),
                "audit_md": str(audit_md_path),
                "scorecard": str(scorecard_path),
                "forced_conclusion": forced,
                "exact_missing_mechanism": missing,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
