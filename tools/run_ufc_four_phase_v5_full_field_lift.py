#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
BASELINE_RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision.ts"
FIXED_SNAPSHOT_CSV = BACKUPS / "canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv"
FIXED_SNAPSHOT_META = BACKUPS / "canonical_real_rowtrace_production_fixed_snapshot_metadata_20260320T210125Z.json"
EXACT_REPAIR_JSON = BACKUPS / "dsf_ufc_four_phase_v5_exact_repair_20260322T093005Z.json"

ROW_COLUMNS = [
    "symbol",
    "decision_timestamp",
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]

BASELINE_COUNTS = {"Accumulate": 133, "Hold": 1132, "Avoid": 4148}
PHASE_TO_DECISION = {"green": "Accumulate", "yellow": "Hold", "black": "Hold", "red": "Avoid"}
TIE_EPS = 1e-12


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
class RowControls:
    symbol: str
    a: float
    alpha: float
    s: float
    chi: float
    T: float


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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


def generate_paths(num_points: int = 41) -> dict[str, list[PrimitivePoint]]:
    paths: dict[str, list[PrimitivePoint]] = {}
    ts = [i / (num_points - 1) for i in range(num_points)]

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
    s_cov = point.S_UF - point.U_star_k
    r_cov = point.R_UF - point.U_star_k
    g = s_cov * r_cov
    u = point.D_k + point.M_k + point.B_k
    v = point.D_k * point.M_k + point.D_k * point.B_k + point.M_k * point.B_k
    delta_raw = max(u * u - 3.0 * v, 0.0)
    chi = delta_raw / (1.0 + delta_raw)
    q = (1.0 - point.R_rev_k) / ((1.0 + point.C_k) * (1.0 + point.P_k))
    return {"g": g, "u": u, "v": v, "chi": chi, "q": q}


def alpha_floor(inv: dict[str, float]) -> float:
    return max(2.0 * inv["chi"] - inv["q"], 0.0)


def support_s(inv: dict[str, float]) -> float:
    return inv["q"] * inv["u"]


def threshold_T(alpha: float) -> float:
    return math.sqrt(4.5 * alpha)


def row_controls(point: PrimitivePoint) -> RowControls:
    inv = invariant_coordinates(point)
    a = inv["q"] * max(inv["g"], 0.0)
    alpha = alpha_floor(inv)
    s_val = support_s(inv)
    chi = inv["chi"]
    return RowControls(symbol=point.symbol, a=a, alpha=alpha, s=s_val, chi=chi, T=threshold_T(alpha))


def F_eta(eta: float, alpha: float, xi: float) -> float:
    return (alpha / 2.0) * eta * eta + (eta**4) / 4.0 - (xi / 3.0) * (eta**3)


def phi_value(z: float, eta: float, a: float, alpha: float, xi: float) -> float:
    return ((z - a) ** 2) / 4.0 + z * F_eta(eta, alpha, xi)


def exact_solver(point: PrimitivePoint, lambda_s: float) -> dict[str, Any]:
    ctl = row_controls(point)
    xi = lambda_s * ctl.s - ctl.chi
    candidates: list[dict[str, Any]] = []

    candidates.append({"z": 0.0, "eta": 0.0, "phi": phi_value(0.0, 0.0, ctl.a, ctl.alpha, xi), "phase": "black", "reason": "black_origin"})
    z0 = max(ctl.a, 0.0)
    candidates.append(
        {
            "z": z0,
            "eta": 0.0,
            "phi": phi_value(z0, 0.0, ctl.a, ctl.alpha, xi),
            "phase": "yellow" if z0 > TIE_EPS else "black",
            "reason": "yellow_eta0" if z0 > TIE_EPS else "black_origin",
        }
    )

    discriminant = xi * xi - 4.0 * ctl.alpha
    if discriminant >= -TIE_EPS:
        root_term = math.sqrt(max(discriminant, 0.0))
        roots = []
        for eta in ((xi - root_term) / 2.0, (xi + root_term) / 2.0):
            if not any(abs(eta - seen) <= TIE_EPS for seen in roots):
                roots.append(eta)
        for eta in roots:
            z = max(ctl.a - 2.0 * F_eta(eta, ctl.alpha, xi), 0.0)
            phi = phi_value(z, eta, ctl.a, ctl.alpha, xi)
            if z <= TIE_EPS:
                if eta > 0.0:
                    phase = "black"
                    reason = "positive_root_loses_to_origin"
                elif eta < 0.0:
                    phase = "black"
                    reason = "negative_root_loses_to_origin"
                else:
                    phase = "black"
                    reason = "black_origin"
            elif eta > TIE_EPS:
                phase = "green"
                reason = "green_root_wins"
            elif eta < -TIE_EPS:
                phase = "red"
                reason = "red_root_wins"
            else:
                phase = "yellow"
                reason = "yellow_eta0"
            candidates.append({"z": z, "eta": eta, "phi": phi, "phase": phase, "reason": reason})

    priority = {"red": 0, "yellow": 1, "black": 2, "green": 3}
    winner = min(candidates, key=lambda item: (item["phi"], priority[item["phase"]], abs(item["eta"]), -item["z"]))
    phase = winner["phase"]
    decision = PHASE_TO_DECISION[phase]

    if discriminant < -TIE_EPS:
        if xi > 0.0:
            reason = "no_positive_real_root"
        elif xi < 0.0:
            reason = "no_negative_real_root"
        else:
            reason = winner["reason"]
    elif winner["reason"] == "yellow_eta0":
        if xi > 0.0:
            reason = "positive_root_loses_to_eta0"
        elif xi < 0.0:
            reason = "negative_root_loses_to_eta0"
        else:
            reason = "yellow_eta0"
    else:
        reason = winner["reason"]

    return {
        "decision": decision,
        "phase": phase,
        "a": ctl.a,
        "alpha": ctl.alpha,
        "s": ctl.s,
        "chi": ctl.chi,
        "xi": xi,
        "discriminant": discriminant,
        "winning_eta": winner["eta"],
        "winning_z": winner["z"],
        "winning_phase_reason": reason,
        "T": ctl.T,
    }


def threshold_decision_from_controls(ctl: RowControls, lambda_s: float) -> dict[str, Any]:
    xi = lambda_s * ctl.s - ctl.chi
    if ctl.s > TIE_EPS:
        lambda_red_exit = max((ctl.chi - ctl.T) / ctl.s, 0.0)
        lambda_green_entry = (ctl.chi + ctl.T) / ctl.s
        if lambda_s < lambda_red_exit - TIE_EPS:
            phase = "red"
        elif lambda_s > lambda_green_entry + TIE_EPS:
            phase = "green"
        else:
            phase = "yellow" if ctl.a > 0.0 else "black"
    elif ctl.s < -TIE_EPS:
        lambda_red_entry = max((ctl.T - ctl.chi) / (-ctl.s), 0.0)
        if lambda_s > lambda_red_entry + TIE_EPS:
            phase = "red"
        else:
            phase = "yellow" if ctl.a > 0.0 else "black"
    else:
        if ctl.chi > ctl.T + TIE_EPS:
            phase = "red"
        else:
            phase = "yellow" if ctl.a > 0.0 else "black"
    return {
        "decision": PHASE_TO_DECISION[phase],
        "phase": phase,
        "a": ctl.a,
        "alpha": ctl.alpha,
        "s": ctl.s,
        "chi": ctl.chi,
        "xi": xi,
        "T": ctl.T,
    }


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


DECISION_ORDER = {"Avoid": 0, "Hold": 1, "Accumulate": 2}


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
    prefix_len = max(1, math.ceil(len(decisions) * 0.25))
    return "Accumulate" in decisions[:prefix_len]


def path_rule_evaluation(path_name: str, points: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [point["decision"] for point in points]
    phases = [point["phase"] for point in points]
    decision_seq = compress_sequence(decisions)
    phase_seq = compress_sequence(phases)
    failures: list[str] = []

    if path_name == "path_A_coverage_collapse":
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
        if phases[-1] not in {"yellow", "black"}:
            failures.append("still_termination_not_neutral")
        if "Accumulate" not in decisions:
            failures.append("no_constructive_accumulate_prefix")
        if "Avoid" in decisions:
            failures.append("avoid_entered_on_constructive_to_still")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_C_constructive_to_covered_rupture":
        if phases[0] != "green":
            failures.append("start_not_green")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("rupture_endpoint_still_accumulate")
        if decisions.count("Hold") < decisions.count("Avoid"):
            failures.append("hold_not_primary_through_rupture_rotation")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_D_one_sided_contested_carry_sweep":
        half = len(decisions) // 2
        if decisions[:half].count("Avoid") > decisions[:half].count("Hold"):
            failures.append("mild_damage_region_mainly_avoid")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    elif path_name == "path_E_reversal_activation_constructive":
        if phases[0] != "green":
            failures.append("start_not_green")
        if not has_accumulate_in_first_quarter(decisions):
            failures.append("no_constructive_prefix")
        if decisions[-1] == "Accumulate":
            failures.append("reversal_failed_to_suppress_accumulate")
        monotonicity = monotonicity_score(decisions, "nonincreasing")
    else:
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
        "continuity_score": continuity_score(decisions),
        "phase_continuity_score": continuity_score(phases),
        "monotonicity_score": monotonicity,
        "acceptance_failures": failures,
        "accepted": len(failures) == 0,
    }


def evaluate_paths(paths: dict[str, list[PrimitivePoint]], lambda_s: float, solver) -> dict[str, Any]:
    accepted = 0
    audit = {}
    for path_name, points in paths.items():
        evaluated = [solver(point, lambda_s) for point in points]
        path_result = path_rule_evaluation(path_name, evaluated)
        audit[path_name] = path_result
        if path_result["accepted"]:
            accepted += 1
    return {"accepted_paths": accepted, "total_paths": len(paths), "path_audit": audit}


def load_snapshot() -> tuple[list[PrimitivePoint], list[dict[str, str]]]:
    points: list[PrimitivePoint] = []
    with FIXED_SNAPSHOT_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if reader.fieldnames != ROW_COLUMNS:
        raise SystemExit(f"unexpected fixed snapshot schema: {reader.fieldnames}")
    for row in rows:
        points.append(
            PrimitivePoint(
                symbol=str(row["symbol"]).strip(),
                barCount=int(float(row["bar_count"])),
                S_UF=float(row["S_UF"]),
                R_UF=float(row["R_UF"]),
                D_k=float(row["D_k"]),
                M_k=float(row["M_k"]),
                R_rev_k=float(row["R_rev_k"]),
                U_star_k=float(row["U_star_k"]),
                C_k=float(row["C_k"]),
                P_k=float(row["P_k"]),
                B_k=float(row["B_k"]),
            )
        )
    return points, rows


def replay_baseline_runtime(snapshot_rows: list[dict[str, str]], min_bars: int) -> list[dict[str, Any]]:
    temp_dir = Path(tempfile.mkdtemp(prefix="v5_support_gain_", dir=str(BACKUPS)))
    input_path = temp_dir / "input.json"
    output_path = temp_dir / "output.json"
    input_path.write_text(json.dumps(snapshot_rows), encoding="utf-8")

    node_code = f"""
const fs = require("fs");
const path = require("path");
const ts = require("typescript");
const runtimePath = {json.dumps(str(BASELINE_RUNTIME_SOURCE))};
const inputPath = {json.dumps(str(input_path))};
const outputPath = {json.dumps(str(output_path))};
const source = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(source, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;
const tempModulePath = path.join({json.dumps(str(temp_dir))}, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const profile = {{
  profileId: "v5_support_gain_audit",
  generatedAtUtc: {json.dumps(utc_iso())},
  minBars: {min_bars},
}};
function toNumber(value) {{
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}}
const results = rows.map((row) => {{
  const input = {{
    symbol: row.symbol,
    barCount: Number(row.bar_count),
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    D_k: toNumber(row.D_k),
    M_k: toNumber(row.M_k),
    R_rev_k: toNumber(row.R_rev_k),
    U_star_k: toNumber(row.U_star_k),
    C_k: toNumber(row.C_k),
    P_k: toNumber(row.P_k),
    B_k: toNumber(row.B_k),
  }};
  const result = mod.computePrimitiveDynamicDecision(input, profile);
  return {{ symbol: row.symbol, decision: result.decision }};
}});
fs.writeFileSync(outputPath, JSON.stringify(results));
"""
    try:
        subprocess.run(["node", "-e", node_code], cwd=WEB_ROOT, check=True, capture_output=True, text=True)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"baseline runtime replay failed: {exc.stderr or exc.stdout or exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return payload


def unique_thresholds(values: list[float]) -> list[float]:
    ordered = sorted(value for value in values if math.isfinite(value) and value >= 1.0 - TIE_EPS)
    out: list[float] = []
    for value in ordered:
        value = max(1.0, value)
        if not out or abs(value - out[-1]) > 1e-10:
            out.append(value)
    return out


def representative_lambda(lo: float, hi: float) -> float:
    if math.isinf(hi):
        return max(lo + 1.0, lo * 2.0)
    return (lo + hi) / 2.0


def interval_text(lo: float, hi: float) -> str:
    left = f"{lo:.12g}"
    right = "+inf" if math.isinf(hi) else f"{hi:.12g}"
    return f"({left}, {right})"


def counts_copy(counts: dict[str, int]) -> dict[str, int]:
    return {key: int(counts[key]) for key in ("Accumulate", "Hold", "Avoid")}


def point_counts_at_lambda(controls_rows: list[RowControls], lambda_s: float) -> dict[str, int]:
    counts = Counter()
    for ctl in controls_rows:
        counts[threshold_decision_from_controls(ctl, lambda_s)["decision"]] += 1
    return {key: int(counts.get(key, 0)) for key in ("Accumulate", "Hold", "Avoid")}


def evaluate_snapshot_exact(points: list[PrimitivePoint], lambda_s: float) -> dict[str, Any]:
    rows = []
    for point in points:
        solved = exact_solver(point, lambda_s)
        rows.append({"symbol": point.symbol, **solved})
    decision_counts = Counter(row["decision"] for row in rows)
    phase_counts = Counter(row["phase"] for row in rows)
    return {
        "rows": rows,
        "decision_counts": {key: int(decision_counts.get(key, 0)) for key in ("Accumulate", "Hold", "Avoid")},
        "phase_counts": {key: int(phase_counts.get(key, 0)) for key in ("green", "yellow", "black", "red")},
    }


def l1_distance(counts: dict[str, int]) -> int:
    return sum(abs(counts[key] - BASELINE_COUNTS[key]) for key in BASELINE_COUNTS)


def summarize_numeric(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None, "mean": None}
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {
        "count": len(ordered),
        "min": float(ordered[0]),
        "median": float(median),
        "max": float(ordered[-1]),
        "mean": float(sum(ordered) / len(ordered)),
    }


def mismatch_buckets(rows: list[dict[str, Any]], baseline_by_symbol: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "baseline_Accumulate_candidate_Hold": [],
        "baseline_Avoid_candidate_Hold": [],
        "baseline_Avoid_candidate_Accumulate": [],
    }
    for row in rows:
        baseline = baseline_by_symbol.get(row["symbol"])
        key = f"baseline_{baseline}_candidate_{row['decision']}"
        if key in grouped:
            grouped[key].append(row)
    out = []
    for key, bucket in grouped.items():
        if not bucket:
            continue
        out.append(
            {
                "bucket": key,
                "count": len(bucket),
                "a_summary": summarize_numeric([row["a"] for row in bucket]),
                "alpha_summary": summarize_numeric([row["alpha"] for row in bucket]),
                "xi_summary": summarize_numeric([row["xi"] for row in bucket]),
                "discriminant_summary": summarize_numeric([row["discriminant"] for row in bucket]),
                "winning_eta_summary": summarize_numeric([row["winning_eta"] for row in bucket]),
                "winning_z_summary": summarize_numeric([row["winning_z"] for row in bucket]),
                "winning_phase_reason_counts": dict(Counter(row["winning_phase_reason"] for row in bucket)),
            }
        )
    return out


def send_slack_completion(event: dict[str, Any]) -> None:
    payload = json.dumps(event)
    subprocess.run(
        ["bash", "-lc", f"printf '%s\\n' {json.dumps(payload)} | /workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh"],
        cwd=str(REPO_ROOT),
        check=True,
    )


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)
    json_path = BACKUPS / f"dsf_ufc_four_phase_v5_support_gain_audit_{stamp}.json"
    md_path = BACKUPS / f"dsf_ufc_four_phase_v5_support_gain_audit_{stamp}.md"

    repaired_ref = load_json(EXACT_REPAIR_JSON)
    expected_counts = repaired_ref["snapshot_counts"]["v5_B_alpha_floor0"]["decision_counts"]

    paths = generate_paths()
    exact_lambda_1 = evaluate_paths(paths, 1.0, exact_solver)
    threshold_lambda_1 = evaluate_paths(paths, 1.0, threshold_decision_from_controls_wrapper(paths))

    snapshot_points, snapshot_rows = load_snapshot()
    controls_rows = [row_controls(point) for point in snapshot_points]
    lambda_one_snapshot = evaluate_snapshot_exact(snapshot_points, 1.0)
    lambda_one_counts_match = lambda_one_snapshot["decision_counts"] == expected_counts

    result: dict[str, Any] = {
        "generated_at_utc": utc_iso(started),
        "candidate": "v5_B_alpha_floor0_support_gain",
        "lambda_s_1_anchor": {
            "strict_score": exact_lambda_1["accepted_paths"],
            "snapshot_decision_counts": lambda_one_snapshot["decision_counts"],
            "snapshot_phase_counts": lambda_one_snapshot["phase_counts"],
            "matches_expected_snapshot_counts": lambda_one_counts_match,
            "expected_snapshot_counts": expected_counts,
        },
        "closed_form_law_matches_exact_at_lambda_s_1": exact_lambda_1["path_audit"] == threshold_lambda_1["path_audit"],
    }

    if exact_lambda_1["accepted_paths"] != 6 or not lambda_one_counts_match:
        result["verdict"] = "lambda_s=1 anchor mismatch"
        result["exact_lambda_s_1"] = exact_lambda_1
        result["threshold_lambda_s_1"] = threshold_lambda_1
        result["recommendation"] = "keep baseline frozen"
        write_json(json_path, result)
        write_markdown(md_path, "# Exact V5_B Support-Only Gain Audit\n\n- `lambda_s=1 anchor mismatch`")
        send_slack_completion({"task": "v5_B support-only gain audit complete", "verdict": result["verdict"], "artifact": str(json_path)})
        print(json.dumps({"json": str(json_path), "md": str(md_path), "verdict": result["verdict"]}, indent=2))
        return 0

    if not result["closed_form_law_matches_exact_at_lambda_s_1"]:
        result["verdict"] = "closed-form threshold law mismatch at lambda_s=1"
        result["exact_lambda_s_1"] = exact_lambda_1
        result["threshold_lambda_s_1"] = threshold_lambda_1
        result["recommendation"] = "keep baseline frozen"
        write_json(json_path, result)
        write_markdown(md_path, "# Exact V5_B Support-Only Gain Audit\n\n- `closed-form threshold law mismatch at lambda_s=1`")
        send_slack_completion({"task": "v5_B support-only gain audit complete", "verdict": result["verdict"], "artifact": str(json_path)})
        print(json.dumps({"json": str(json_path), "md": str(md_path), "verdict": result["verdict"]}, indent=2))
        return 0

    accumulate_ceiling = sum(1 for ctl in controls_rows if ctl.s > TIE_EPS)
    hold_floor_asymptotic = sum(1 for ctl in controls_rows if abs(ctl.s) <= TIE_EPS and ctl.chi <= ctl.T + TIE_EPS)
    avoid_asymptotic = len(controls_rows) - accumulate_ceiling - hold_floor_asymptotic
    result["accumulate_ceiling_precheck"] = {
        "Accumulate_ceiling": accumulate_ceiling,
        "Hold_floor_asymptotic": hold_floor_asymptotic,
        "Avoid_asymptotic": avoid_asymptotic,
    }

    if accumulate_ceiling < BASELINE_COUNTS["Accumulate"]:
        result["strict_admissible_lambda_s_intervals"] = []
        result["universe_change_points_ge_1"] = []
        result["universe_count_intervals"] = []
        result["smallest_strict_admissible_lambda_s_meeting_baseline_like_counts"] = None
        result["best_strict_admissible_l1_match_lambda_s"] = None
        result["verdict"] = "exact v5_B support-only gain is tuple-dead for Accumulate mass"
        result["recommendation"] = "keep baseline frozen"
        result["stop_reason"] = "Approved 12-column tuple cannot recover baseline-like Accumulate mass inside exact v5_B by support-only gain."
        write_json(json_path, result)
        write_markdown(
            md_path,
            "\n".join(
                [
                    "# Exact V5_B Support-Only Gain Audit",
                    "",
                    "## Closed-Form Threshold Law",
                    f"- matches exact solver at lambda_s=1: `{result['closed_form_law_matches_exact_at_lambda_s_1']}`",
                    "",
                    "## Accumulate Ceiling Precheck",
                    f"- Accumulate_ceiling: `{accumulate_ceiling}`",
                    "",
                    "## Verdict",
                    f"- `{result['verdict']}`",
                    f"- recommendation: `{result['recommendation']}`",
                ]
            ),
        )
        send_slack_completion({"task": "v5_B support-only gain audit complete", "verdict": result["verdict"], "artifact": str(json_path)})
        print(json.dumps({"json": str(json_path), "md": str(md_path), "verdict": result["verdict"]}, indent=2))
        return 0

    synthetic_thresholds: list[float] = []
    for path_points in paths.values():
        for point in path_points:
            ctl = row_controls(point)
            if ctl.s > TIE_EPS:
                synthetic_thresholds.append(max((ctl.chi - ctl.T) / ctl.s, 0.0))
                synthetic_thresholds.append((ctl.chi + ctl.T) / ctl.s)
            elif ctl.s < -TIE_EPS:
                synthetic_thresholds.append(max((ctl.T - ctl.chi) / (-ctl.s), 0.0))

    strict_change_points = unique_thresholds(synthetic_thresholds)
    strict_test_values: list[float] = [1.0]
    for idx, cp in enumerate(strict_change_points):
        strict_test_values.append(cp)
        hi = strict_change_points[idx + 1] if idx + 1 < len(strict_change_points) else math.inf
        strict_test_values.append(representative_lambda(cp, hi))
    strict_test_values = unique_thresholds(strict_test_values)

    strict_evaluations = []
    for lambda_s in strict_test_values:
        audit = evaluate_paths(paths, lambda_s, exact_solver)
        strict_evaluations.append({"lambda_s": lambda_s, "score": audit["accepted_paths"], "path_audit": audit["path_audit"]})
    result["strict_evaluations"] = strict_evaluations

    breakpoint_set = {value for value in strict_change_points}
    strict_admissible: list[dict[str, Any]] = []
    current_open_start: float | None = None
    for item in strict_evaluations:
        lambda_s = item["lambda_s"]
        is_breakpoint = any(abs(lambda_s - bp) <= 1e-10 for bp in breakpoint_set)
        if item["score"] == 6 and not is_breakpoint:
            if current_open_start is None:
                current_open_start = lambda_s
        else:
            if current_open_start is not None:
                strict_admissible.append({"type": "open_interval", "interval": interval_text(current_open_start, lambda_s)})
                current_open_start = None
        if item["score"] == 6 and is_breakpoint:
            strict_admissible.append({"type": "point", "lambda_s": lambda_s})
    if current_open_start is not None:
        strict_admissible.append({"type": "open_interval", "interval": interval_text(current_open_start, math.inf)})
    result["strict_admissible_lambda_s_intervals"] = strict_admissible

    initial_point_counts = point_counts_at_lambda(controls_rows, 1.0)
    point_events: dict[float, dict[str, int]] = defaultdict(lambda: {"Accumulate": 0, "Hold": 0, "Avoid": 0})
    post_events: dict[float, dict[str, int]] = defaultdict(lambda: {"Accumulate": 0, "Hold": 0, "Avoid": 0})
    universe_change_points_raw: list[float] = []

    for ctl in controls_rows:
        if ctl.s > TIE_EPS:
            lambda_red_exit = max((ctl.chi - ctl.T) / ctl.s, 0.0)
            lambda_green_entry = (ctl.chi + ctl.T) / ctl.s
            if lambda_red_exit > 1.0 + 1e-10:
                cp = lambda_red_exit
                universe_change_points_raw.append(cp)
                point_events[cp]["Avoid"] -= 1
                point_events[cp]["Hold"] += 1
            if lambda_green_entry > 1.0 + 1e-10:
                cp = lambda_green_entry
                universe_change_points_raw.append(cp)
                post_events[cp]["Hold"] -= 1
                post_events[cp]["Accumulate"] += 1
        elif ctl.s < -TIE_EPS:
            lambda_red_entry = max((ctl.T - ctl.chi) / (-ctl.s), 0.0)
            if lambda_red_entry > 1.0 + 1e-10:
                cp = lambda_red_entry
                universe_change_points_raw.append(cp)
                post_events[cp]["Hold"] -= 1
                post_events[cp]["Avoid"] += 1

    universe_change_points = unique_thresholds(universe_change_points_raw)
    result["universe_change_points_ge_1"] = universe_change_points

    open_counts = counts_copy(initial_point_counts)
    for cp, delta in post_events.items():
        if abs(cp - 1.0) <= 1e-10:
            for key in open_counts:
                open_counts[key] += delta[key]

    point_counts_map: dict[float, dict[str, int]] = {1.0: counts_copy(initial_point_counts)}
    open_intervals: list[dict[str, Any]] = []
    prev = 1.0
    for cp in universe_change_points:
        if cp > prev + 1e-10:
            open_intervals.append(
                {
                    "type": "open_interval",
                    "interval": interval_text(prev, cp),
                    "representative_lambda_s": representative_lambda(prev, cp),
                    "counts": counts_copy(open_counts),
                }
            )
        point_counts = counts_copy(open_counts)
        if cp in point_events:
            for key in point_counts:
                point_counts[key] += point_events[cp][key]
        point_counts_map[cp] = counts_copy(point_counts)
        for key in open_counts:
            open_counts[key] = point_counts[key] + post_events[cp][key]
        prev = cp
    open_intervals.append(
        {
            "type": "open_interval",
            "interval": interval_text(prev, math.inf),
            "representative_lambda_s": representative_lambda(prev, math.inf),
            "counts": counts_copy(open_counts),
        }
    )
    result["universe_count_intervals"] = open_intervals

    baseline_rows = replay_baseline_runtime(snapshot_rows, int(load_json(FIXED_SNAPSHOT_META).get("profile", {}).get("min_bars", 200)))
    baseline_by_symbol = {row["symbol"]: row["decision"] for row in baseline_rows}

    admissible_open_ranges: list[tuple[float, float]] = []
    admissible_points: list[float] = []
    for item in strict_admissible:
        if item["type"] == "point":
            admissible_points.append(item["lambda_s"])
        else:
            text = item["interval"][1:-1]
            lo_text, hi_text = [part.strip() for part in text.split(",")]
            lo = float(lo_text)
            hi = math.inf if hi_text == "+inf" else float(hi_text)
            admissible_open_ranges.append((lo, hi))

    exact_target_hits: list[dict[str, Any]] = []
    best_match: dict[str, Any] | None = None

    for record in open_intervals:
        text = record["interval"][1:-1]
        lo_text, hi_text = [part.strip() for part in text.split(",")]
        lo = float(lo_text)
        hi = math.inf if hi_text == "+inf" else float(hi_text)
        counts = record["counts"]
        distance = l1_distance(counts)
        for a_lo, a_hi in admissible_open_ranges:
            overlap_lo = max(lo, a_lo)
            overlap_hi = min(hi, a_hi)
            if overlap_lo >= overlap_hi:
                continue
            overlap_rep = representative_lambda(overlap_lo, overlap_hi)
            if counts["Accumulate"] >= BASELINE_COUNTS["Accumulate"] and counts["Avoid"] >= BASELINE_COUNTS["Avoid"]:
                exact_target_hits.append({"lambda_s": overlap_rep, "counts": counts, "type": "open_interval"})
            if best_match is None or distance < best_match["l1"] or (distance == best_match["l1"] and overlap_rep < best_match["lambda_s"]):
                best_match = {"lambda_s": overlap_rep, "counts": counts, "l1": distance, "type": "open_interval"}

    for lambda_s in unique_thresholds(admissible_points):
        counts = point_counts_map.get(lambda_s)
        if counts is None:
            counts = point_counts_at_lambda(controls_rows, lambda_s)
        distance = l1_distance(counts)
        if counts["Accumulate"] >= BASELINE_COUNTS["Accumulate"] and counts["Avoid"] >= BASELINE_COUNTS["Avoid"]:
            exact_target_hits.append({"lambda_s": lambda_s, "counts": counts, "type": "point"})
        if best_match is None or distance < best_match["l1"] or (distance == best_match["l1"] and lambda_s < best_match["lambda_s"]):
            best_match = {"lambda_s": lambda_s, "counts": counts, "l1": distance, "type": "point"}

    if exact_target_hits:
        winner = min(exact_target_hits, key=lambda item: item["lambda_s"])
        exact_snapshot = evaluate_snapshot_exact(snapshot_points, winner["lambda_s"])
        result["smallest_strict_admissible_lambda_s_meeting_baseline_like_counts"] = {
            "lambda_s": winner["lambda_s"],
            "strict_score": evaluate_paths(paths, winner["lambda_s"], exact_solver)["accepted_paths"],
            "decision_counts": exact_snapshot["decision_counts"],
            "phase_counts": exact_snapshot["phase_counts"],
            "delta_vs_frozen_baseline": {key: exact_snapshot["decision_counts"][key] - BASELINE_COUNTS[key] for key in BASELINE_COUNTS},
            "baseline_accumulate_rows_became_green": sum(
                1 for row in exact_snapshot["rows"] if baseline_by_symbol.get(row["symbol"]) == "Accumulate" and row["decision"] == "Accumulate"
            ),
            "baseline_avoid_rows_became_red": sum(
                1 for row in exact_snapshot["rows"] if baseline_by_symbol.get(row["symbol"]) == "Avoid" and row["decision"] == "Avoid"
            ),
        }
        result["best_strict_admissible_l1_match_lambda_s"] = None
        result["verdict"] = "one-parameter xi gain feasible"
        result["recommendation"] = "promote exact v5_B_alpha_floor0_support_gain to shadow lane"
    else:
        if best_match is not None:
            exact_snapshot = evaluate_snapshot_exact(snapshot_points, best_match["lambda_s"])
            result["smallest_strict_admissible_lambda_s_meeting_baseline_like_counts"] = None
            result["best_strict_admissible_l1_match_lambda_s"] = {
                "lambda_s": best_match["lambda_s"],
                "strict_score": evaluate_paths(paths, best_match["lambda_s"], exact_solver)["accepted_paths"],
                "decision_counts": exact_snapshot["decision_counts"],
                "phase_counts": exact_snapshot["phase_counts"],
                "delta_vs_frozen_baseline": {key: exact_snapshot["decision_counts"][key] - BASELINE_COUNTS[key] for key in BASELINE_COUNTS},
                "baseline_accumulate_rows_became_green": sum(
                    1 for row in exact_snapshot["rows"] if baseline_by_symbol.get(row["symbol"]) == "Accumulate" and row["decision"] == "Accumulate"
                ),
                "baseline_avoid_rows_became_red": sum(
                    1 for row in exact_snapshot["rows"] if baseline_by_symbol.get(row["symbol"]) == "Avoid" and row["decision"] == "Avoid"
                ),
                "top_mismatch_buckets": mismatch_buckets(exact_snapshot["rows"], baseline_by_symbol),
            }
        else:
            result["smallest_strict_admissible_lambda_s_meeting_baseline_like_counts"] = None
            result["best_strict_admissible_l1_match_lambda_s"] = None
        result["verdict"] = "exact v5_B support-only gain is path-valid but universe-invalid on the approved tuple"
        result["recommendation"] = "keep baseline frozen"

    md_lines = [
        "# Exact V5_B Support-Only Gain Audit",
        "",
        "## Closed-Form Threshold Law",
        f"- matches exact solver at lambda_s=1: `{result['closed_form_law_matches_exact_at_lambda_s_1']}`",
        "",
        "## Accumulate Ceiling Precheck",
        f"- Accumulate_ceiling: `{result['accumulate_ceiling_precheck']['Accumulate_ceiling']}`",
        f"- Hold_floor_asymptotic: `{result['accumulate_ceiling_precheck']['Hold_floor_asymptotic']}`",
        f"- Avoid_asymptotic: `{result['accumulate_ceiling_precheck']['Avoid_asymptotic']}`",
        "",
        "## Strict-Admissible Lambda_s Intervals",
    ]
    if result["strict_admissible_lambda_s_intervals"]:
        for item in result["strict_admissible_lambda_s_intervals"]:
            if item["type"] == "point":
                md_lines.append(f"- point `{item['lambda_s']}`")
            else:
                md_lines.append(f"- interval `{item['interval']}`")
    else:
        md_lines.append("- none")
    md_lines.extend(
        [
            "",
            "## Verdict",
            f"- `{result['verdict']}`",
            f"- recommendation: `{result['recommendation']}`",
        ]
    )

    write_json(json_path, result)
    write_markdown(md_path, "\n".join(md_lines))
    send_slack_completion({"task": "v5_B support-only gain audit complete", "verdict": result["verdict"], "artifact": str(json_path)})
    print(json.dumps({"json": str(json_path), "md": str(md_path), "verdict": result["verdict"]}, indent=2))
    return 0


def threshold_decision_from_controls_wrapper(paths: dict[str, list[PrimitivePoint]]):
    def solver(point: PrimitivePoint, lambda_s: float) -> dict[str, Any]:
        return threshold_decision_from_controls(row_controls(point), lambda_s)

    return solver


if __name__ == "__main__":
    raise SystemExit(main())
