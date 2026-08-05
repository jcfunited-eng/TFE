#!/usr/bin/env python3
"""
L5 policy learning pipeline (production path).

Purpose:
- Train structural PSCF policy from row-trace structure data.
- Merge with anomaly-watch policy for anomaly metadata coverage.
- Validate candidate vs current runtime policy on frozen benchmark dataset.
- Atomically promote candidate to runtime policy only if gates pass.

This pipeline is deterministic from local artifacts and does not use heuristic
price-indicator shortcuts.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import json
import math
import os
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from ses_core import Envelope
from tfe_ses_core_adapter import TenantIdentity, decrypt_blob, initialize_ses_core_for_env, make_domain
from uf_core.uf_structural_engine import compute_uf_structural_state


HORIZONS: Tuple[int, int, int] = (5, 20, 60)
# Enforce structural history depth for L5 governance evaluation.
MIN_BARS = 514
DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")


def _parse_cd_bucket_edges() -> Tuple[float, float, float, float]:
    raw = str(os.environ.get("TFE_POLICY_CD_BUCKET_EDGES", "")).strip()
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) == 4:
            try:
                vals = [float(x) for x in parts]
                vals_sorted = tuple(sorted(vals))
                return (vals_sorted[0], vals_sorted[1], vals_sorted[2], vals_sorted[3])
            except Exception:
                pass
    return (-0.6, -0.4, -0.3, -0.2)


CD_BUCKET_EDGES: Tuple[float, float, float, float] = _parse_cd_bucket_edges()
MIN_PRIMARY_CELL_SAMPLES = max(0, int(os.environ.get("TFE_POLICY_MIN_PRIMARY_CELL_SAMPLES", "0")))
CD_REGIME_MODE = str(os.environ.get("TFE_POLICY_CD_REGIME_MODE", "all")).strip().lower()


def _parse_horizon_weights() -> Dict[str, float]:
    default = {str(h): 1.0 for h in HORIZONS}
    raw = str(os.environ.get("TFE_POLICY_HORIZON_WEIGHTS", "")).strip()
    if not raw:
        return default

    out = dict(default)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        kk = k.strip()
        vv = v.strip()
        if kk not in out:
            continue
        try:
            w = float(vv)
        except Exception:
            continue
        if not math.isfinite(w) or w < 0.0:
            continue
        out[kk] = w

    return out


def _parse_bounded_float(
    env_name: str,
    default_value: float,
    *,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
) -> float:
    raw = str(os.environ.get(env_name, str(default_value))).strip()
    try:
        value = float(raw)
    except Exception:
        value = float(default_value)

    if not math.isfinite(value):
        value = float(default_value)

    if lower_bound is not None and value < lower_bound:
        value = lower_bound
    if upper_bound is not None and value > upper_bound:
        value = upper_bound

    return float(value)


HORIZON_WEIGHTS: Dict[str, float] = _parse_horizon_weights()
POLICY_SOURCE_MODE = str(os.environ.get("TFE_POLICY_SOURCE_MODE", "replay")).strip().lower()
SELECTION_OBJECTIVE = str(os.environ.get("TFE_POLICY_SELECTION_OBJECTIVE", "excess")).strip().lower()
INCLUDE_STABILITY_BUCKET = str(os.environ.get("TFE_POLICY_INCLUDE_STABILITY_BUCKET", "0")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
IRF_MODE = str(os.environ.get("TFE_POLICY_IRF_MODE", "off")).strip().lower()
EVAL_MODE = str(os.environ.get("TFE_POLICY_EVAL_MODE", "replay")).strip().lower()
MIN_ACTION_EDGE = _parse_bounded_float("TFE_POLICY_MIN_ACTION_EDGE", 0.0, lower_bound=0.0)
MIN_ACTION_MARGIN = _parse_bounded_float("TFE_POLICY_MIN_ACTION_MARGIN", 0.0, lower_bound=0.0)
MIN_ACTION_WINRATE_PCT = _parse_bounded_float(
    "TFE_POLICY_MIN_ACTION_WINRATE_PCT",
    0.0,
    lower_bound=0.0,
    upper_bound=100.0,
)

DEFAULT_ROW_TRACE_PATH = Path("real_world_cleaned_universe_l5_row_trace_full.csv")
DEFAULT_RUNTIME_POLICY_PATH = Path("pscf_policy_runtime.json")
DEFAULT_REPORT_LATEST_PATH = Path("l5_policy_learning_latest.json")
DEFAULT_OUTPUT_DIR = Path("backups/runtime/l5_policy_learning")
DEFAULT_COVERAGE_SNAPSHOT_PATH = Path("uf_snapshot.ses.json")
LEGACY_COVERAGE_SNAPSHOT_PATH = Path("uf_snapshot.json")

COVERAGE_SES_PURPOSE_PREFIX = "tfe-web"
COVERAGE_SES_PURPOSE_SUFFIX = "uf-snapshot"
COVERAGE_SES_ACTOR_ID = "web-snapshot-pipeline"
COVERAGE_TENANT_ID = "tenant-tao"
COVERAGE_TENANT_DISPLAY_NAME = "Tao Tenant"


def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _utc_stamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _to_num(value: Any) -> float:
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except Exception:
        return 0.0


def _sign3(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _u_bucket(u_star: float) -> str:
    if u_star < 0.33:
        return "U0"
    if u_star < 0.66:
        return "U1"
    return "U2"


def _p_bucket(p_val: float) -> str:
    p = int(round(p_val))
    if p <= 0:
        return "P0"
    if p == 1:
        return "P1"
    return "P2"


def _bucket_3(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def _bucket_cd_opt(value: float) -> str:
    if value < CD_BUCKET_EDGES[0]:
        return "B0"
    if value < CD_BUCKET_EDGES[1]:
        return "B1"
    if value < CD_BUCKET_EDGES[2]:
        return "B2"
    if value < CD_BUCKET_EDGES[3]:
        return "B3"
    return "B4"


def _bucket_stability(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def _irf_phase(m_sgn: int, r_uf: float) -> str:
    if r_uf < 0.33 and m_sgn > 0:
        return "U2UP"
    if r_uf > 0.66 and m_sgn < 0:
        return "U2DN"
    return "UFLAT"


def _irf_phase_suffix(m_sgn: int, r_uf: float) -> str:
    if IRF_MODE == "phase":
        return f"|PH={_irf_phase(m_sgn, r_uf)}"
    return ""


def _include_cd_for_regime(regime: str) -> bool:
    mode = CD_REGIME_MODE
    rg = str(regime or "").strip().upper()

    if mode == "all":
        return True
    if mode == "nonstable_only":
        return rg != "STABLE"
    if mode == "stable_only":
        return rg == "STABLE"
    if mode == "exclude_unknown":
        return rg not in ("", "UNKNOWN")

    # Safe default if mode is invalid.
    return True


def _base_cell_key_from_parts(
    regime: str,
    d_k: int,
    m_sgn: int,
    r_rev: int,
    u_b: str,
    p_b: str,
    b_sgn: int,
) -> str:
    return f"reg={regime}|D={d_k}|M={m_sgn}|Rrev={r_rev}|{u_b}|{p_b}|B={b_sgn}"


def _row_trace_cell_key(row: Dict[str, str]) -> str:
    regime = str(row.get("regime", "UNKNOWN"))

    d_k = int(round(_to_num(row.get("D"))))
    m_sgn = _sign3(_to_num(row.get("M")))
    r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
    u_b = _u_bucket(_to_num(row.get("U_star")))
    p_b = _p_bucket(_to_num(row.get("P")))
    b_sgn = _sign3(_to_num(row.get("B")))

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn)
    s_uf = _to_num(row.get("S_UF"))
    r_uf = _to_num(row.get("R_UF"))
    st = _to_num(row.get("stability_score"))
    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)
    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        return f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}{irf_part}"
    return f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}{irf_part}"


def _row_trace_cell_key_candidates(row: Dict[str, str]) -> List[str]:
    regime = str(row.get("regime", "UNKNOWN"))

    d_k = int(round(_to_num(row.get("D"))))
    m_sgn = _sign3(_to_num(row.get("M")))
    r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
    u_b = _u_bucket(_to_num(row.get("U_star")))
    p_b = _p_bucket(_to_num(row.get("P")))
    b_sgn = _sign3(_to_num(row.get("B")))

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn)
    s_uf = _to_num(row.get("S_UF"))
    r_uf = _to_num(row.get("R_UF"))
    st = _to_num(row.get("stability_score"))

    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)

    keys: List[str] = []

    if _include_cd_for_regime(regime):
        cd_key = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(s_uf - r_uf)}{st_part}"
        if irf_part:
            keys.append(f"{cd_key}{irf_part}")
        keys.append(cd_key)

    sr_key = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    sr_legacy = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"

    if irf_part:
        keys.append(f"{sr_key}{irf_part}")
        if sr_key != sr_legacy:
            keys.append(f"{sr_legacy}{irf_part}")
    keys.append(sr_key)
    if sr_key != sr_legacy:
        keys.append(sr_legacy)

    keys.append(base)

    deduped: List[str] = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    return deduped


def _state_cell_key(state: Any) -> Optional[str]:
    level3 = getattr(state, "level3", {})
    regime = str(level3.get("regime", "UNKNOWN"))

    level5 = getattr(state, "level5", {})
    dv = level5.get("decision_vector", []) if isinstance(level5, dict) else []
    if not isinstance(dv, list) or len(dv) == 0:
        return None

    def dv_val(idx: int) -> float:
        if idx >= len(dv):
            return 0.0
        return _to_num(dv[idx])

    d_k = int(round(dv_val(0)))
    m_sgn = _sign3(dv_val(1))
    r_rev = 1 if dv_val(2) > 0.5 else 0
    u_b = _u_bucket(dv_val(3))
    p_b = _p_bucket(dv_val(4))
    b_sgn = _sign3(dv_val(5))

    level4 = getattr(state, "level4", {})
    s_uf = _to_num(level4.get("S_UF", 0.0)) if isinstance(level4, dict) else 0.0
    r_uf = _to_num(level4.get("R_UF", 0.0)) if isinstance(level4, dict) else 0.0
    st = _to_num(level4.get("stability_score", 0.0)) if isinstance(level4, dict) else 0.0
    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn)
    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        return f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}{irf_part}"
    return f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}{irf_part}"


def _state_cell_key_candidates(state: Any) -> List[str]:
    level3 = getattr(state, "level3", {})
    regime = str(level3.get("regime", "UNKNOWN"))

    level5 = getattr(state, "level5", {})
    dv = level5.get("decision_vector", []) if isinstance(level5, dict) else []
    if not isinstance(dv, list) or len(dv) == 0:
        return []

    def dv_val(idx: int) -> float:
        if idx >= len(dv):
            return 0.0
        return _to_num(dv[idx])

    d_k = int(round(dv_val(0)))
    m_sgn = _sign3(dv_val(1))
    r_rev = 1 if dv_val(2) > 0.5 else 0
    u_b = _u_bucket(dv_val(3))
    p_b = _p_bucket(dv_val(4))
    b_sgn = _sign3(dv_val(5))

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn)

    level4 = getattr(state, "level4", {})
    s_uf = _to_num(level4.get("S_UF", 0.0)) if isinstance(level4, dict) else 0.0
    r_uf = _to_num(level4.get("R_UF", 0.0)) if isinstance(level4, dict) else 0.0
    st = _to_num(level4.get("stability_score", 0.0)) if isinstance(level4, dict) else 0.0

    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)

    keys: List[str] = []

    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        enriched_cd = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}"
        if irf_part:
            keys.append(f"{enriched_cd}{irf_part}")
        keys.append(enriched_cd)

    enriched_sr = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    enriched_sr_legacy = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"

    if irf_part:
        keys.append(f"{enriched_sr}{irf_part}")
        if enriched_sr != enriched_sr_legacy:
            keys.append(f"{enriched_sr_legacy}{irf_part}")

    keys.append(enriched_sr)
    if enriched_sr != enriched_sr_legacy:
        keys.append(enriched_sr_legacy)

    keys.append(base)

    deduped: List[str] = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    return deduped


def _parse_iso_ms(value: str) -> Optional[int]:
    text = (value or "").strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.datetime.fromisoformat(text)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    return int(dt.timestamp() * 1000)


def _decision_return(decision: str, forward_return: float) -> float:
    if decision == "Accumulate":
        return forward_return
    if decision == "Avoid":
        return -forward_return
    return 0.0


def _spy_forward_return(spy_ts: Sequence[int], spy_close: Sequence[float], entry_ts: int, horizon: int) -> Optional[float]:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None

    j = idx + int(horizon)
    if j >= len(spy_close):
        return None

    c0 = float(spy_close[idx])
    c1 = float(spy_close[j])
    if c0 <= 0:
        return None

    return float(c1 / c0 - 1.0)


def _rec_template() -> Dict[str, Any]:
    return {
        "n": 0,
        "sum_excess": 0.0,
        "sum_return": 0.0,
        "wins_over_index": 0,
        "sum_excess_by_horizon": defaultdict(float),
        "n_by_horizon": defaultdict(int),
    }


def _decision_stats_template() -> Dict[str, Dict[str, Any]]:
    return {d: _rec_template() for d in DECISIONS}


def _update_record(rec: Dict[str, Any], horizon: int, action_ret: float, spy_ret: float) -> None:
    ex = float(action_ret - spy_ret)
    rec["n"] += 1
    rec["sum_excess"] += ex
    rec["sum_return"] += float(action_ret)
    rec["wins_over_index"] += int(action_ret > spy_ret)
    rec["sum_excess_by_horizon"][str(horizon)] += ex
    rec["n_by_horizon"][str(horizon)] += 1


def _summarize_decision_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    n = int(rec["n"])
    if n <= 0:
        return {
            "n": 0,
            "mean_excess_vs_spy": None,
            "outcome_over_index_pct": None,
            "mean_action_return": None,
            "mean_excess_vs_spy_by_horizon": {},
        }

    by_h: Dict[str, float] = {}
    for h_key, h_n in rec["n_by_horizon"].items():
        h_n_int = int(h_n)
        if h_n_int <= 0:
            continue
        by_h[h_key] = float(rec["sum_excess_by_horizon"][h_key] / h_n_int)

    return {
        "n": n,
        "mean_excess_vs_spy": float(rec["sum_excess"] / n),
        "outcome_over_index_pct": float(100.0 * rec["wins_over_index"] / n),
        "mean_action_return": float(rec["sum_return"] / n),
        "mean_excess_vs_spy_by_horizon": by_h,
    }


def _choose_decision(records: Dict[str, Dict[str, Any]]) -> Tuple[str, float, Dict[str, Any]]:
    details: Dict[str, Any] = {}
    scored: List[Tuple[str, float, float]] = []

    for decision, rec in records.items():
        summary = _summarize_decision_record(rec)
        if SELECTION_OBJECTIVE == "action_return":
            base_action_mean = summary.get("mean_action_return")
            selection_score = float(base_action_mean) if base_action_mean is not None else -1e18
        else:
            by_h = summary.get("mean_excess_vs_spy_by_horizon", {})
            selection_num = 0.0
            selection_den = 0.0
            if isinstance(by_h, dict):
                for h_key, h_val in by_h.items():
                    try:
                        hv = float(h_val)
                    except Exception:
                        continue
                    weight = float(HORIZON_WEIGHTS.get(str(h_key), 1.0))
                    if weight <= 0.0:
                        continue
                    selection_num += weight * hv
                    selection_den += weight
            if selection_den > 0.0:
                selection_score = float(selection_num / selection_den)
            else:
                base_mean = summary.get("mean_excess_vs_spy")
                selection_score = float(base_mean) if base_mean is not None else -1e18
        summary["selection_score"] = selection_score
        details[decision] = summary
        if summary["n"] > 0 and summary["mean_excess_vs_spy"] is not None:
            scored.append((decision, float(selection_score), float(summary["mean_excess_vs_spy"])))

    if not scored:
        return "Hold", 0.0, details

    scored.sort(key=lambda item: item[1], reverse=True)
    best_decision, best_selection_score, best_excess = scored[0]

    # Optional action confidence gates:
    # when a non-Hold choice has weak edge or weak separation, force Hold.
    use_hold_guard = False
    hold_guard_reason: Optional[str] = None

    if best_decision != "Hold":
        if best_selection_score < MIN_ACTION_EDGE:
            use_hold_guard = True
            hold_guard_reason = "min_action_edge"

        if (not use_hold_guard) and len(scored) > 1:
            second_selection_score = float(scored[1][1])
            if (best_selection_score - second_selection_score) < MIN_ACTION_MARGIN:
                use_hold_guard = True
                hold_guard_reason = "min_action_margin"

        if not use_hold_guard:
            best_stats = details.get(best_decision)
            best_winrate = None
            if isinstance(best_stats, dict):
                raw_winrate = best_stats.get("outcome_over_index_pct")
                if isinstance(raw_winrate, (int, float)):
                    best_winrate = float(raw_winrate)
            if best_winrate is not None and best_winrate < MIN_ACTION_WINRATE_PCT:
                use_hold_guard = True
                hold_guard_reason = "min_action_winrate_pct"

    if use_hold_guard:
        hold_stats = details.get("Hold")
        hold_excess = 0.0
        if isinstance(hold_stats, dict):
            raw_hold_excess = hold_stats.get("mean_excess_vs_spy")
            if isinstance(raw_hold_excess, (int, float)):
                hold_excess = float(raw_hold_excess)
            hold_stats["hold_guard_applied"] = True
            hold_stats["hold_guard_reason"] = hold_guard_reason
        return "Hold", hold_excess, details

    return best_decision, float(best_excess), details


def _selected_sample_count(cell: Dict[str, Any]) -> int:
    decision = str(cell.get("decision", ""))
    details = cell.get("decision_stats_selected")
    if isinstance(details, dict):
        selected = details.get(decision)
        if isinstance(selected, dict):
            try:
                return max(0, int(selected.get("n", 0)))
            except Exception:
                return 0
    return 0


def _latest_path(pattern: str) -> Optional[Path]:
    matches = sorted(Path(".").glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _resolve_spy_dataset() -> Path:
    env = str(os.environ.get("TFE_POLICY_SPY_DATASET", "")).strip()
    if env:
        p = Path(env)
        if p.exists():
            return p

    latest = _latest_path("backups/strict-ab-frozen-dataset-*.json")
    if latest is not None:
        return latest

    raise FileNotFoundError("No SPY dataset found. Expected backups/strict-ab-frozen-dataset-*.json")


def _resolve_validation_dataset() -> Path:
    env = str(os.environ.get("TFE_POLICY_VALIDATION_DATASET", "")).strip()
    if env:
        p = Path(env)
        if p.exists():
            return p
    return _resolve_spy_dataset()


def _resolve_anomaly_policy() -> Path:
    env = str(os.environ.get("TFE_POLICY_ANOMALY_POLICY", "")).strip()
    if env:
        p = Path(env)
        if p.exists():
            return p

    latest = _latest_path("backups/pscf-policy-anomaly-watch-*.json")
    if latest is not None:
        return latest

    raise FileNotFoundError("No anomaly-watch policy found. Expected backups/pscf-policy-anomaly-watch-*.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _load_snapshot_rows_for_coverage(snapshot_path: Path) -> Dict[str, Any]:
    if not snapshot_path.exists():
        return {
            "snapshot_path": str(snapshot_path),
            "status": "snapshot_missing",
            "rows": None,
        }

    # Legacy plaintext path (list of row objects).
    if str(snapshot_path).lower().endswith(".json") and not str(snapshot_path).lower().endswith(".ses.json"):
        payload = _load_json(snapshot_path)
        if isinstance(payload, list):
            return {
                "snapshot_path": str(snapshot_path),
                "status": "ok",
                "rows": payload,
            }
        return {
            "snapshot_path": str(snapshot_path),
            "status": "snapshot_invalid",
            "rows": None,
        }

    # Envelope path (.ses.json) used in current production.
    try:
        environment = str(os.environ.get("TFE_ENV", "dev"))
        region = str(os.environ.get("TFE_REGION", os.environ.get("AWS_REGION", "local")))
        ctx = initialize_ses_core_for_env(
            environment=environment,
            region=region,
            purpose_prefix=COVERAGE_SES_PURPOSE_PREFIX,
        )

        tenant = TenantIdentity(
            tenant_id=COVERAGE_TENANT_ID,
            display_name=COVERAGE_TENANT_DISPLAY_NAME,
            environment=environment,
            attributes={},
        )

        with snapshot_path.open("r", encoding="utf-8") as f:
            envelope_raw = f.read()

        envelope = Envelope.from_json(envelope_raw)
        domain = make_domain(ctx=ctx, purpose_suffix=COVERAGE_SES_PURPOSE_SUFFIX, version="v1")
        payload = decrypt_blob(
            ctx=ctx,
            tenant=tenant,
            domain=domain,
            envelope=envelope,
            actor_id=COVERAGE_SES_ACTOR_ID,
        )

        rows_raw = payload
        if isinstance(payload, dict):
            rows_raw = payload.get("rows", [])

        if isinstance(rows_raw, list):
            return {
                "snapshot_path": str(snapshot_path),
                "status": "ok",
                "rows": rows_raw,
            }

        return {
            "snapshot_path": str(snapshot_path),
            "status": "snapshot_invalid",
            "rows": None,
        }
    except Exception as exc:
        return {
            "snapshot_path": str(snapshot_path),
            "status": f"snapshot_decrypt_failed:{type(exc).__name__}",
            "rows": None,
        }


def _generate_policy_from_row_trace(row_trace_path: Path, spy_dataset_path: Path) -> Dict[str, Any]:
    if not row_trace_path.exists():
        raise FileNotFoundError(f"Row trace file not found: {row_trace_path}")

    spy_payload = _load_json(spy_dataset_path)
    spy_ts = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close = [float(x) for x in spy_payload["spy"]["close"]]

    row_stats: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(_decision_stats_template)

    row_count_total = 0
    row_count_used = 0
    row_count_skipped = Counter()

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_count_total += 1

            horizon = int(_to_num(row.get("horizon")))
            if horizon <= 0:
                row_count_skipped["invalid_horizon"] += 1
                continue

            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                row_count_skipped["invalid_timestamp"] += 1
                continue

            forward_return = _to_num(row.get("forward_return"))

            spy_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if spy_ret is None:
                row_count_skipped["missing_spy_benchmark"] += 1
                continue

            cell_key = _row_trace_cell_key(row)

            for decision in DECISIONS:
                action_ret = _decision_return(decision, forward_return)
                _update_record(row_stats[cell_key][decision], horizon, action_ret, spy_ret)

            row_count_used += 1

    policy_cells: Dict[str, Any] = {}
    for cell_key, records in sorted(row_stats.items()):
        best_decision, best_excess, details = _choose_decision(records)
        policy_cells[cell_key] = {
            "decision": best_decision,
            "mean_excess_vs_spy": float(best_excess),
            "scoring_mode": "row_trace_spy",
            "decision_stats_selected": details,
            "anomaly_profile": {
                "available": False,
                "note": "Row trace source does not include anomaly flags.",
            },
        }

    decision_counts = {
        "Accumulate": sum(1 for v in policy_cells.values() if v["decision"] == "Accumulate"),
        "Hold": sum(1 for v in policy_cells.values() if v["decision"] == "Hold"),
        "Avoid": sum(1 for v in policy_cells.values() if v["decision"] == "Avoid"),
    }

    top_positive = sorted(
        [
            {
                "cell": k,
                "decision": v["decision"],
                "mean_excess_vs_spy": v["mean_excess_vs_spy"],
                "n_selected": (
                    v["decision_stats_selected"].get(v["decision"], {}).get("n")
                    if isinstance(v.get("decision_stats_selected"), dict)
                    else None
                ),
            }
            for k, v in policy_cells.items()
        ],
        key=lambda item: item["mean_excess_vs_spy"],
        reverse=True,
    )[:100]

    top_negative = sorted(
        [
            {
                "cell": k,
                "decision": v["decision"],
                "mean_excess_vs_spy": v["mean_excess_vs_spy"],
                "n_selected": (
                    v["decision_stats_selected"].get(v["decision"], {}).get("n")
                    if isinstance(v.get("decision_stats_selected"), dict)
                    else None
                ),
            }
            for k, v in policy_cells.items()
        ],
        key=lambda item: item["mean_excess_vs_spy"],
    )[:100]

    return {
        "generated_at_utc": _utc_now_iso(),
        "source": {
            "row_trace": str(row_trace_path),
            "spy_benchmark_dataset": str(spy_dataset_path),
        },
        "coverage": {
            "row_count_total": row_count_total,
            "row_count_used": row_count_used,
            "row_count_used_pct": float(100.0 * row_count_used / row_count_total) if row_count_total > 0 else None,
            "row_count_skipped": dict(row_count_skipped),
        },
        "cell_key_schema": "regime + D + M_sign + R_rev + U_bucket + P_bucket + B_sign + S_bucket3 + R_bucket3 + CD_bucket_opt",
        "decision_rule": "argmax mean_excess_vs_spy among {Accumulate, Hold, Avoid}",
        "benchmark": "SPY",
        "scoring_policy": "row-trace decision timestamps with SPY forward return benchmark",
        "decision_counts": decision_counts,
        "top_cells_by_positive_mean_excess": top_positive,
        "top_cells_by_negative_mean_excess": top_negative,
        "cells": policy_cells,
    }


def _generate_policy_from_replay_dataset(dataset: Dict[str, Any], dataset_path: Path) -> Dict[str, Any]:
    if not isinstance(dataset, dict):
        raise ValueError("Replay dataset must be an object.")

    symbols_obj = dataset.get("symbols")
    spy_obj = dataset.get("spy")
    if not isinstance(symbols_obj, dict):
        raise ValueError("Replay dataset missing symbols object.")
    if not isinstance(spy_obj, dict):
        raise ValueError("Replay dataset missing spy object.")

    spy_ts = [int(x) for x in spy_obj.get("ts_ms", [])]
    spy_close = [float(x) for x in spy_obj.get("close", [])]
    if len(spy_ts) == 0 or len(spy_close) == 0 or len(spy_ts) != len(spy_close):
        raise ValueError("Replay dataset has invalid SPY benchmark arrays.")

    max_h = max(HORIZONS)

    stats_all: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(_decision_stats_template)
    stats_clean: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(_decision_stats_template)
    anomaly_watch: Dict[str, Counter] = defaultdict(Counter)

    symbol_coverage: Dict[str, Any] = {}

    symbols = sorted(symbols_obj.keys())
    for idx, sym in enumerate(symbols, start=1):
        payload = symbols_obj.get(sym, {})
        if not isinstance(payload, dict):
            symbol_coverage[sym] = {"status": "invalid_symbol_payload"}
            continue

        ts = [int(x) for x in payload.get("ts_ms", [])]
        close = [float(x) for x in payload.get("close", [])]

        n = len(close)
        if n < (MIN_BARS + max_h):
            symbol_coverage[sym] = {
                "status": "insufficient_bars",
                "bars": n,
                "required": MIN_BARS + max_h,
            }
            continue

        eval_count = 0
        for t in range(MIN_BARS - 1, n - max_h):
            hist_index = pd.to_datetime(ts[: t + 1], unit="ms", utc=True)
            hist_close = pd.Series(close[: t + 1], index=hist_index)

            try:
                state = compute_uf_structural_state(hist_close)
            except Exception:
                continue

            cell_key = _state_cell_key(state)
            if cell_key is None:
                continue

            anomaly = _anomaly_flags_from_state(state)
            entry_ts = ts[t]
            eval_count += 1

            for h in HORIZONS:
                j = t + h
                sym_ret = float(close[j] / close[t] - 1.0)
                bench_ret = _spy_forward_return(spy_ts, spy_close, entry_ts, h)
                if bench_ret is None:
                    continue

                anomaly_watch[cell_key]["eval_count"] += 1
                anomaly_watch[cell_key]["anomaly_any_count"] += int(anomaly["anomaly_any"])
                anomaly_watch[cell_key]["guard_gate_unlock_count"] += int(anomaly["guard_gate_unlock"])
                anomaly_watch[cell_key]["hardening_any_count"] += int(anomaly["hardening_any"])
                anomaly_watch[cell_key]["hardening_uncertainty_excess_count"] += int(anomaly["hardening_uncertainty_excess"])
                anomaly_watch[cell_key]["hardening_hysteresis_overload_count"] += int(
                    anomaly["hardening_hysteresis_overload"]
                )

                for decision in DECISIONS:
                    action_ret = _decision_return(decision, sym_ret)
                    _update_record(stats_all[cell_key][decision], h, action_ret, bench_ret)

                    if not anomaly["anomaly_any"]:
                        _update_record(stats_clean[cell_key][decision], h, action_ret, bench_ret)

        symbol_coverage[sym] = {
            "status": "ok",
            "bars": n,
            "evaluations": eval_count,
        }

        if idx == 1 or idx % 5 == 0:
            print(f"[L5-POLICY-REPLAY] {idx}/{len(symbols)} {sym}")

    def _has_any_samples(details: Dict[str, Any]) -> bool:
        if not isinstance(details, dict):
            return False
        for decision in DECISIONS:
            rec = details.get(decision, {})
            if isinstance(rec, dict) and int(rec.get("n", 0)) > 0:
                return True
        return False

    policy_cells: Dict[str, Any] = {}
    scoring_mode_counts = Counter()

    all_cells = set(stats_all.keys()) | set(stats_clean.keys())
    for cell_key in sorted(all_cells):
        best_decision_clean, best_excess_clean, details_clean = _choose_decision(stats_clean[cell_key])
        best_decision_all, best_excess_all, details_all = _choose_decision(stats_all[cell_key])

        has_clean = _has_any_samples(details_clean)
        if has_clean:
            selected_decision = best_decision_clean
            selected_excess = best_excess_clean
            scoring_mode = "clean_only"
            selected_stats = details_clean
        else:
            selected_decision = best_decision_all
            selected_excess = best_excess_all
            scoring_mode = "fallback_all_anomalous"
            selected_stats = details_all

        scoring_mode_counts[scoring_mode] += 1

        watch = anomaly_watch[cell_key]
        eval_count = int(watch.get("eval_count", 0))
        anomaly_any_count = int(watch.get("anomaly_any_count", 0))

        policy_cells[cell_key] = {
            "decision": selected_decision,
            "mean_excess_vs_spy": float(selected_excess),
            "scoring_mode": scoring_mode,
            "decision_stats_selected": selected_stats,
            "decision_stats_all_samples": details_all,
            "decision_stats_clean_samples": details_clean,
            "anomaly_profile": {
                "evaluations": eval_count,
                "anomaly_any_count": anomaly_any_count,
                "anomaly_any_rate_pct": float(100.0 * anomaly_any_count / eval_count) if eval_count > 0 else None,
                "guard_gate_unlock_count": int(watch.get("guard_gate_unlock_count", 0)),
                "hardening_any_count": int(watch.get("hardening_any_count", 0)),
                "hardening_uncertainty_excess_count": int(watch.get("hardening_uncertainty_excess_count", 0)),
                "hardening_hysteresis_overload_count": int(watch.get("hardening_hysteresis_overload_count", 0)),
            },
        }

    decision_counts = {
        "Accumulate": sum(1 for v in policy_cells.values() if v["decision"] == "Accumulate"),
        "Hold": sum(1 for v in policy_cells.values() if v["decision"] == "Hold"),
        "Avoid": sum(1 for v in policy_cells.values() if v["decision"] == "Avoid"),
    }

    return {
        "generated_at_utc": _utc_now_iso(),
        "source": {
            "replay_dataset": str(dataset_path),
            "benchmark": "SPY",
        },
        "cell_key_schema": "regime + D + M_sign + R_rev + U_bucket + P_bucket + B_sign + S_bucket3 + R_bucket3 + CD_bucket_opt",
        "decision_rule": "argmax mean_excess_vs_spy among {Accumulate, Hold, Avoid}",
        "scoring_policy": "score on non-anomalous samples; fallback to all samples when clean set is empty",
        "anomaly_any_definition": "guard_gate_unlock OR hardening_hysteresis_overload",
        "symbol_coverage": symbol_coverage,
        "scoring_mode_counts": dict(scoring_mode_counts),
        "decision_counts": decision_counts,
        "cells": policy_cells,
    }


def _merge_policies(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    primary_cells = primary.get("cells", {})
    secondary_cells = secondary.get("cells", {})

    if not isinstance(primary_cells, dict):
        raise ValueError("Primary policy cells must be an object.")
    if not isinstance(secondary_cells, dict):
        raise ValueError("Secondary policy cells must be an object.")

    merged_cells: Dict[str, Dict[str, Any]] = {}

    source_counts = {
        "primary_only": 0,
        "secondary_only": 0,
        "both_primary_selected": 0,
        "both_secondary_selected_low_support": 0,
        "primary_only_dropped_low_support": 0,
    }

    all_keys = set(primary_cells.keys()) | set(secondary_cells.keys())

    for key in sorted(all_keys):
        p_cell = primary_cells.get(key)
        s_cell = secondary_cells.get(key)
        p_low_support = False
        if isinstance(p_cell, dict) and MIN_PRIMARY_CELL_SAMPLES > 0:
            p_samples = _selected_sample_count(p_cell)
            p_low_support = p_samples < MIN_PRIMARY_CELL_SAMPLES

        if isinstance(p_cell, dict) and isinstance(s_cell, dict):
            if p_low_support:
                merged = dict(s_cell)
                merged["policy_source"] = "secondary"
                merged["fallback_source"] = "primary_low_support_filtered"
                merged_cells[key] = merged
                source_counts["both_secondary_selected_low_support"] += 1
                continue

            merged = dict(p_cell)
            merged["policy_source"] = "primary"
            merged["fallback_source"] = "secondary"

            primary_profile = merged.get("anomaly_profile")
            if not isinstance(primary_profile, dict) or bool(primary_profile.get("available", False)) is False:
                s_profile = s_cell.get("anomaly_profile")
                if isinstance(s_profile, dict):
                    merged["anomaly_profile"] = s_profile

            merged_cells[key] = merged
            source_counts["both_primary_selected"] += 1
            continue

        if isinstance(p_cell, dict):
            if p_low_support:
                source_counts["primary_only_dropped_low_support"] += 1
                continue
            merged = dict(p_cell)
            merged["policy_source"] = "primary"
            merged_cells[key] = merged
            source_counts["primary_only"] += 1
            continue

        if isinstance(s_cell, dict):
            merged = dict(s_cell)
            merged["policy_source"] = "secondary"
            merged_cells[key] = merged
            source_counts["secondary_only"] += 1
            continue

    merged_policy = {
        "generated_at_utc": _utc_now_iso(),
        "merge_rule": "primary-first, secondary fallback, optional low-support primary filtering",
        "primary_policy_generated_at_utc": primary.get("generated_at_utc"),
        "secondary_policy_generated_at_utc": secondary.get("generated_at_utc"),
        "cells": merged_cells,
    }

    decision_counts = {
        "Accumulate": sum(1 for v in merged_cells.values() if v.get("decision") == "Accumulate"),
        "Hold": sum(1 for v in merged_cells.values() if v.get("decision") == "Hold"),
        "Avoid": sum(1 for v in merged_cells.values() if v.get("decision") == "Avoid"),
    }

    merge_report = {
        "generated_at_utc": _utc_now_iso(),
        "merged_cell_count": len(merged_cells),
        "min_primary_cell_samples": MIN_PRIMARY_CELL_SAMPLES,
        "source_counts": source_counts,
        "decision_counts": decision_counts,
    }

    return merged_policy, merge_report


def _anomaly_flags_from_state(state: Any) -> Dict[str, bool]:
    level5 = getattr(state, "level5", {}) if state is not None else {}

    guard = level5.get("decision_guard", {}) if isinstance(level5, dict) else {}
    guard_flag = bool(guard.get("gate_unlock_transient_neutralized", False)) if isinstance(guard, dict) else False

    hard = level5.get("hardening", {}) if isinstance(level5, dict) else {}
    hard_flags = hard.get("flags", {}) if isinstance(hard, dict) else {}

    if isinstance(hard_flags, dict):
        hard_any = any(bool(v) for v in hard_flags.values())
        hard_uncertainty_excess = bool(hard_flags.get("uncertainty_excess", False))
        hard_hysteresis_overload = bool(hard_flags.get("hysteresis_overload", False))
    else:
        hard_any = False
        hard_uncertainty_excess = False
        hard_hysteresis_overload = False

    anomaly_any = bool(guard_flag or hard_hysteresis_overload)

    return {
        "anomaly_any": anomaly_any,
        "guard_gate_unlock": guard_flag,
        "hardening_any": hard_any,
        "hardening_uncertainty_excess": hard_uncertainty_excess,
        "hardening_hysteresis_overload": hard_hysteresis_overload,
    }


def _summarize(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "std": None,
            "pct_positive": None,
            "pct_negative": None,
        }

    n = len(values)
    mean_v = sum(values) / n
    med_v = median(values)
    var_v = sum((x - mean_v) ** 2 for x in values) / n
    std_v = var_v ** 0.5

    return {
        "n": n,
        "mean": float(mean_v),
        "median": float(med_v),
        "std": float(std_v),
        "pct_positive": float(sum(1 for x in values if x > 0) / n),
        "pct_negative": float(sum(1 for x in values if x < 0) / n),
    }


def _pct_outperform(strategy_returns: List[float], benchmark_returns: List[float]) -> Optional[float]:
    n = min(len(strategy_returns), len(benchmark_returns))
    if n <= 0:
        return None
    wins = 0
    for i in range(n):
        if strategy_returns[i] > benchmark_returns[i]:
            wins += 1
    return float(100.0 * wins / n)


def _evaluate_policy(dataset: Dict[str, Any], policy: Dict[str, Any], label: str) -> Dict[str, Any]:
    cells = policy.get("cells", {})
    if not isinstance(cells, dict):
        raise ValueError("Policy cells missing or invalid.")

    spy_ts: List[int] = [int(x) for x in dataset["spy"]["ts_ms"]]
    spy_close: List[float] = [float(x) for x in dataset["spy"]["close"]]

    max_h = max(HORIZONS)

    horizon_decisions: Dict[int, Counter] = {h: Counter() for h in HORIZONS}
    horizon_action_returns: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_action_returns_adj: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_bench: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_excess: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_excess_adj: Dict[int, List[float]] = {h: [] for h in HORIZONS}

    anomaly_counts: Dict[int, Counter] = {h: Counter() for h in HORIZONS}
    mapping_counts: Dict[int, Counter] = {h: Counter() for h in HORIZONS}

    symbols = sorted(dataset["symbols"].keys())

    for idx, sym in enumerate(symbols, start=1):
        payload = dataset["symbols"][sym]
        ts = [int(x) for x in payload.get("ts_ms", [])]
        close = [float(x) for x in payload.get("close", [])]

        n = len(close)
        if n < (MIN_BARS + max_h):
            continue

        for t in range(MIN_BARS - 1, n - max_h):
            hist_index = pd.to_datetime(ts[: t + 1], unit="ms", utc=True)
            hist_close = pd.Series(close[: t + 1], index=hist_index)

            try:
                state = compute_uf_structural_state(hist_close)
            except Exception:
                continue

            key_candidates = _state_cell_key_candidates(state)
            selected_key: Optional[str] = None
            selected_cell: Optional[Dict[str, Any]] = None
            for candidate in key_candidates:
                candidate_cell = cells.get(candidate)
                if isinstance(candidate_cell, dict):
                    selected_key = candidate
                    selected_cell = candidate_cell
                    break

            mapped = bool(selected_key is not None and selected_cell is not None)

            if mapped and selected_cell is not None:
                decision = str(selected_cell.get("decision", "Hold"))
                if decision not in DECISIONS:
                    decision = "Hold"
            else:
                decision = "Hold"

            anomaly = _anomaly_flags_from_state(state)
            entry_ts = ts[t]

            for h in HORIZONS:
                j = t + h
                sym_ret = float(close[j] / close[t] - 1.0)
                bench_ret = _spy_forward_return(spy_ts, spy_close, entry_ts, h)
                if bench_ret is None:
                    continue

                action_ret = _decision_return(decision, sym_ret)
                action_ret_adj = 0.0 if anomaly["anomaly_any"] else action_ret

                horizon_decisions[h][decision] += 1
                horizon_action_returns[h].append(action_ret)
                horizon_action_returns_adj[h].append(action_ret_adj)
                horizon_bench[h].append(bench_ret)
                horizon_excess[h].append(action_ret - bench_ret)
                horizon_excess_adj[h].append(action_ret_adj - bench_ret)

                anomaly_counts[h]["anomaly_any"] += int(anomaly["anomaly_any"])
                anomaly_counts[h]["guard_gate_unlock"] += int(anomaly["guard_gate_unlock"])
                anomaly_counts[h]["hardening_any"] += int(anomaly["hardening_any"])
                anomaly_counts[h]["hardening_uncertainty_excess"] += int(anomaly["hardening_uncertainty_excess"])
                anomaly_counts[h]["hardening_hysteresis_overload"] += int(anomaly["hardening_hysteresis_overload"])

                mapping_counts[h]["mapped"] += int(mapped)
                mapping_counts[h]["unmapped"] += int(not mapped)

        if idx == 1 or idx % 5 == 0:
            print(f"[L5-EVAL:{label}] {idx}/{len(symbols)} {sym}")

    horizon_summaries: Dict[str, Any] = {}

    for h in HORIZONS:
        decisions = dict(horizon_decisions[h])
        n_eval = sum(decisions.values())
        active = decisions.get("Accumulate", 0) + decisions.get("Avoid", 0)

        action_summary = _summarize(horizon_action_returns[h])
        bench_summary = _summarize(horizon_bench[h])
        excess_summary = _summarize(horizon_excess[h])

        action_adj_summary = _summarize(horizon_action_returns_adj[h])
        excess_adj_summary = _summarize(horizon_excess_adj[h])

        outperf = _pct_outperform(horizon_action_returns[h], horizon_bench[h])
        outperf_adj = _pct_outperform(horizon_action_returns_adj[h], horizon_bench[h])

        anom_any = int(anomaly_counts[h]["anomaly_any"])
        mapped = int(mapping_counts[h]["mapped"])
        unmapped = int(mapping_counts[h]["unmapped"])

        horizon_summaries[str(h)] = {
            "evaluations": n_eval,
            "decision_counts": decisions,
            "active_share": float(active / n_eval) if n_eval > 0 else None,
            "action": action_summary,
            "benchmark_spy": bench_summary,
            "excess_vs_spy": excess_summary,
            "action_anomaly_accounted": action_adj_summary,
            "excess_vs_spy_anomaly_accounted": excess_adj_summary,
            "outcome_over_index_pct": outperf,
            "outcome_over_index_pct_anomaly_accounted": outperf_adj,
            "anomalies": {
                "anomaly_any_count": anom_any,
                "anomaly_any_rate_pct": float(100.0 * anom_any / n_eval) if n_eval > 0 else None,
            },
            "policy_mapping": {
                "mapped_count": mapped,
                "unmapped_count": unmapped,
                "mapped_rate_pct": float(100.0 * mapped / n_eval) if n_eval > 0 else None,
                "unmapped_rate_pct": float(100.0 * unmapped / n_eval) if n_eval > 0 else None,
            },
        }

    return {
        "generated_at_utc": _utc_now_iso(),
        "label": label,
        "config": {
            "horizons": list(HORIZONS),
            "min_bars": MIN_BARS,
            "benchmark": "SPY",
            "decision_source": "policy_cell_mapping_only",
            "anomaly_accounting": "anomaly_any => neutral action (Hold=0) for adjusted scores",
            "anomaly_any_definition": "guard_gate_unlock OR hardening_hysteresis_overload",
        },
        "horizon_summaries": horizon_summaries,
    }


def _evaluate_policy_rowtrace(row_trace_path: Path, spy_dataset_path: Path, policy: Dict[str, Any], label: str) -> Dict[str, Any]:
    cells = policy.get("cells", {})
    if not isinstance(cells, dict):
        raise ValueError("Policy cells missing or invalid.")

    if not row_trace_path.exists():
        raise FileNotFoundError(f"Row trace file not found: {row_trace_path}")

    spy_payload = _load_json(spy_dataset_path)
    spy_ts: List[int] = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close: List[float] = [float(x) for x in spy_payload["spy"]["close"]]

    horizon_decisions: Dict[int, Counter] = {h: Counter() for h in HORIZONS}
    horizon_action_returns: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_action_returns_adj: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_bench: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_excess: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    horizon_excess_adj: Dict[int, List[float]] = {h: [] for h in HORIZONS}

    anomaly_counts: Dict[int, Counter] = {h: Counter() for h in HORIZONS}
    mapping_counts: Dict[int, Counter] = {h: Counter() for h in HORIZONS}

    rows_scanned = 0
    rows_used = 0

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_scanned += 1

            horizon = int(_to_num(row.get("horizon")))
            if horizon not in HORIZONS:
                continue

            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                continue

            forward_return = _to_num(row.get("forward_return"))
            bench_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                continue

            key_candidates = _row_trace_cell_key_candidates(row)
            selected_key: Optional[str] = None
            selected_cell: Optional[Dict[str, Any]] = None
            for candidate in key_candidates:
                candidate_cell = cells.get(candidate)
                if isinstance(candidate_cell, dict):
                    selected_key = candidate
                    selected_cell = candidate_cell
                    break

            mapped = bool(selected_key is not None and selected_cell is not None)

            if mapped and selected_cell is not None:
                decision = str(selected_cell.get("decision", "Hold"))
                if decision not in DECISIONS:
                    decision = "Hold"
            else:
                decision = "Hold"

            action_ret = _decision_return(decision, forward_return)
            action_ret_adj = action_ret

            h = horizon
            horizon_decisions[h][decision] += 1
            horizon_action_returns[h].append(action_ret)
            horizon_action_returns_adj[h].append(action_ret_adj)
            horizon_bench[h].append(bench_ret)
            horizon_excess[h].append(action_ret - bench_ret)
            horizon_excess_adj[h].append(action_ret_adj - bench_ret)

            anomaly_counts[h]["anomaly_any"] += 0
            anomaly_counts[h]["guard_gate_unlock"] += 0
            anomaly_counts[h]["hardening_any"] += 0
            anomaly_counts[h]["hardening_uncertainty_excess"] += 0
            anomaly_counts[h]["hardening_hysteresis_overload"] += 0

            mapping_counts[h]["mapped"] += int(mapped)
            mapping_counts[h]["unmapped"] += int(not mapped)

            rows_used += 1
            if rows_scanned == 1 or rows_scanned % 200000 == 0:
                print(f"[L5-EVAL-ROWTRACE:{label}] rows_scanned={rows_scanned} rows_used={rows_used}")

    horizon_summaries: Dict[str, Any] = {}

    for h in HORIZONS:
        decisions = dict(horizon_decisions[h])
        n_eval = sum(decisions.values())
        active = decisions.get("Accumulate", 0) + decisions.get("Avoid", 0)

        action_summary = _summarize(horizon_action_returns[h])
        bench_summary = _summarize(horizon_bench[h])
        excess_summary = _summarize(horizon_excess[h])

        action_adj_summary = _summarize(horizon_action_returns_adj[h])
        excess_adj_summary = _summarize(horizon_excess_adj[h])

        outperf = _pct_outperform(horizon_action_returns[h], horizon_bench[h])
        outperf_adj = _pct_outperform(horizon_action_returns_adj[h], horizon_bench[h])

        anom_any = int(anomaly_counts[h]["anomaly_any"])
        mapped = int(mapping_counts[h]["mapped"])
        unmapped = int(mapping_counts[h]["unmapped"])

        horizon_summaries[str(h)] = {
            "evaluations": n_eval,
            "decision_counts": decisions,
            "active_share": float(active / n_eval) if n_eval > 0 else None,
            "action": action_summary,
            "benchmark_spy": bench_summary,
            "excess_vs_spy": excess_summary,
            "action_anomaly_accounted": action_adj_summary,
            "excess_vs_spy_anomaly_accounted": excess_adj_summary,
            "outcome_over_index_pct": outperf,
            "outcome_over_index_pct_anomaly_accounted": outperf_adj,
            "anomalies": {
                "anomaly_any_count": anom_any,
                "anomaly_any_rate_pct": float(100.0 * anom_any / n_eval) if n_eval > 0 else None,
            },
            "policy_mapping": {
                "mapped_count": mapped,
                "unmapped_count": unmapped,
                "mapped_rate_pct": float(100.0 * mapped / n_eval) if n_eval > 0 else None,
                "unmapped_rate_pct": float(100.0 * unmapped / n_eval) if n_eval > 0 else None,
            },
        }

    return {
        "generated_at_utc": _utc_now_iso(),
        "label": label,
        "config": {
            "horizons": list(HORIZONS),
            "min_bars": MIN_BARS,
            "benchmark": "SPY",
            "decision_source": "policy_cell_mapping_rowtrace",
            "anomaly_accounting": "row-trace does not include anomaly flags; adjusted scores equal raw scores",
            "anomaly_any_definition": "unavailable_in_row_trace",
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
        },
        "horizon_summaries": horizon_summaries,
    }


def _compare_candidate_vs_current(current_eval: Dict[str, Any], candidate_eval: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    for h in ("5", "20", "60"):
        c = current_eval["horizon_summaries"][h]
        n = candidate_eval["horizon_summaries"][h]

        c_ex = c.get("excess_vs_spy_anomaly_accounted", {}).get("mean")
        n_ex = n.get("excess_vs_spy_anomaly_accounted", {}).get("mean")

        c_out = c.get("outcome_over_index_pct_anomaly_accounted")
        n_out = n.get("outcome_over_index_pct_anomaly_accounted")

        c_map = c.get("policy_mapping", {}).get("mapped_rate_pct")
        n_map = n.get("policy_mapping", {}).get("mapped_rate_pct")

        rows.append(
            {
                "horizon": int(h),
                "current_excess_mean_anomaly_accounted": c_ex,
                "candidate_excess_mean_anomaly_accounted": n_ex,
                "delta_excess_mean_anomaly_accounted": (n_ex - c_ex) if c_ex is not None and n_ex is not None else None,
                "current_outcome_over_index_pct_anomaly_accounted": c_out,
                "candidate_outcome_over_index_pct_anomaly_accounted": n_out,
                "delta_outcome_over_index_pct_anomaly_accounted": (n_out - c_out) if c_out is not None and n_out is not None else None,
                "current_mapped_rate_pct": c_map,
                "candidate_mapped_rate_pct": n_map,
                "delta_mapped_rate_pct": (n_map - c_map) if c_map is not None and n_map is not None else None,
            }
        )

    # Promotion gates (explicit): 0.0 is valid and must not fail the gate.
    def _non_negative_or_fail(value: Any) -> bool:
        if value is None:
            return False
        try:
            return float(value) >= 0.0
        except Exception:
            return False

    delta_excess_values: List[float] = []
    for row in rows:
        v = row.get("delta_excess_mean_anomaly_accounted")
        if v is None:
            delta_excess_values = []
            break
        try:
            delta_excess_values.append(float(v))
        except Exception:
            delta_excess_values = []
            break

    aggregate_delta_excess_mean = (
        float(sum(delta_excess_values) / len(delta_excess_values)) if len(delta_excess_values) == len(rows) and len(rows) > 0 else None
    )

    gate_delta_excess_aggregate_non_negative = _non_negative_or_fail(aggregate_delta_excess_mean)
    gate_outcome_non_decreasing_all = all(
        _non_negative_or_fail(r["delta_outcome_over_index_pct_anomaly_accounted"]) for r in rows
    )
    gate_mapping_non_decreasing_all = all(_non_negative_or_fail(r["delta_mapped_rate_pct"]) for r in rows)

    promote = bool(
        gate_delta_excess_aggregate_non_negative
        and gate_outcome_non_decreasing_all
        and gate_mapping_non_decreasing_all
    )

    return {
        "generated_at_utc": _utc_now_iso(),
        "horizon_rows": rows,
        "aggregate_delta_excess_mean_anomaly_accounted": aggregate_delta_excess_mean,
        "gates": {
            "delta_excess_mean_anomaly_accounted_non_negative_aggregate_mean": gate_delta_excess_aggregate_non_negative,
            "outcome_over_index_pct_anomaly_accounted_non_decreasing_all_horizons": gate_outcome_non_decreasing_all,
            "mapped_rate_non_decreasing_all_horizons": gate_mapping_non_decreasing_all,
        },
        "promote": promote,
        "gate_rule": "promote when candidate aggregate anomaly-accounted excess-mean delta is non-negative, outcome-over-index delta is non-negative at all horizons, and mapping rate is non-decreasing at all horizons",
    }


def _snapshot_mapping_coverage(policy: Dict[str, Any], snapshot_path: Path) -> Dict[str, Any]:
    loaded = _load_snapshot_rows_for_coverage(snapshot_path)
    rows = loaded.get("rows")
    status = str(loaded.get("status", "snapshot_invalid"))
    path_value = str(loaded.get("snapshot_path", str(snapshot_path)))
    if status != "ok" or not isinstance(rows, list):
        return {
            "snapshot_path": path_value,
            "status": status,
        }

    cells = policy.get("cells", {})
    if not isinstance(cells, dict):
        return {
            "snapshot_path": path_value,
            "status": "policy_invalid",
        }

    mapped = 0
    unmapped = 0

    for row in rows:
        if not isinstance(row, dict):
            continue

        dv = row.get("decision_vector")
        if not isinstance(dv, list):
            unmapped += 1
            continue

        regime = str(row.get("regime", "UNKNOWN"))
        d = int(round(_to_num(dv[0] if len(dv) > 0 else 0.0)))
        m = _sign3(_to_num(dv[1] if len(dv) > 1 else 0.0))
        rrev = 1 if _to_num(dv[2] if len(dv) > 2 else 0.0) > 0.5 else 0
        u = _u_bucket(_to_num(dv[3] if len(dv) > 3 else 0.0))
        p = _p_bucket(_to_num(dv[4] if len(dv) > 4 else 0.0))
        b = _sign3(_to_num(dv[5] if len(dv) > 5 else 0.0))

        base = _base_cell_key_from_parts(regime, d, m, rrev, u, p, b)
        s_uf = _to_num(row.get("S_UF", 0.0))
        r_uf = _to_num(row.get("R_UF", 0.0))
        st = _to_num(row.get("stability_score", 0.0))
        st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
        enriched_sr = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
        enriched_sr_legacy = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"
        enriched_cd: Optional[str] = None
        if _include_cd_for_regime(regime):
            cd = s_uf - r_uf
            enriched_cd = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}"

        irf_part = _irf_phase_suffix(m, r_uf)
        enriched_cd_irf = f"{enriched_cd}{irf_part}" if (enriched_cd is not None and irf_part) else None
        enriched_sr_irf = f"{enriched_sr}{irf_part}" if irf_part else None
        enriched_sr_legacy_irf = f"{enriched_sr_legacy}{irf_part}" if irf_part else None

        if (
            (enriched_cd_irf is not None and enriched_cd_irf in cells)
            or (enriched_sr_irf is not None and enriched_sr_irf in cells)
            or (enriched_sr_legacy_irf is not None and enriched_sr_legacy_irf in cells)
            or (enriched_cd is not None and enriched_cd in cells)
            or enriched_sr in cells
            or enriched_sr_legacy in cells
            or base in cells
        ):
            mapped += 1
        else:
            unmapped += 1

    total = mapped + unmapped

    return {
        "snapshot_path": path_value,
        "status": "ok",
        "rows": total,
        "mapped_rows": mapped,
        "unmapped_rows": unmapped,
        "mapped_pct": float(100.0 * mapped / total) if total > 0 else None,
    }


def _atomic_promote(candidate_policy_path: Path, runtime_policy_path: Path, backup_dir: Path) -> Dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_stamp()
    backup_path = backup_dir / f"pscf_policy_runtime.backup.{stamp}.json"

    if runtime_policy_path.exists():
        shutil.copy2(runtime_policy_path, backup_path)

    tmp_path = runtime_policy_path.with_suffix(runtime_policy_path.suffix + ".tmp")
    tmp_path.write_text(candidate_policy_path.read_text())
    os.replace(tmp_path, runtime_policy_path)

    return {
        "promoted_at_utc": _utc_now_iso(),
        "runtime_policy_path": str(runtime_policy_path),
        "backup_path": str(backup_path) if backup_path.exists() else None,
        "candidate_policy_path": str(candidate_policy_path),
    }


@dataclass
class LearningResult:
    report_path: Path
    report: Dict[str, Any]



def run_l5_policy_learning(trigger: str = "manual") -> LearningResult:
    stamp = _utc_stamp()

    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    row_trace_path = Path(str(os.environ.get("TFE_POLICY_ROW_TRACE", str(DEFAULT_ROW_TRACE_PATH))))
    runtime_policy_path = Path(str(os.environ.get("TFE_RUNTIME_POLICY_PATH", str(DEFAULT_RUNTIME_POLICY_PATH))))
    validation_dataset_path = _resolve_validation_dataset()
    spy_dataset_path = _resolve_spy_dataset()

    report_path = output_dir / f"l5-policy-learning-report-{stamp}.json"

    if not runtime_policy_path.exists():
        raise FileNotFoundError(f"Runtime policy not found: {runtime_policy_path}")

    current_policy = _load_json(runtime_policy_path)
    dataset = _load_json(validation_dataset_path)

    if POLICY_SOURCE_MODE == "rowtrace":
        replay_policy = _generate_policy_from_row_trace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
        )
    elif POLICY_SOURCE_MODE == "hybrid":
        replay_from_dataset = _generate_policy_from_replay_dataset(dataset=dataset, dataset_path=validation_dataset_path)
        replay_from_rowtrace = _generate_policy_from_row_trace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
        )
        replay_policy, _ = _merge_policies(replay_from_rowtrace, replay_from_dataset)
    else:
        replay_policy = _generate_policy_from_replay_dataset(dataset=dataset, dataset_path=validation_dataset_path)
    replay_policy_path = output_dir / f"pscf-policy-replay-spy-{stamp}.json"
    _write_json(replay_policy_path, replay_policy)

    # Preserve current-runtime coverage for cells absent in replay-derived policy.
    merged_policy, merge_report = _merge_policies(replay_policy, current_policy)
    candidate_policy_path = output_dir / f"pscf-policy-candidate-{stamp}.json"
    _write_json(candidate_policy_path, merged_policy)

    if EVAL_MODE == "rowtrace":
        current_eval = _evaluate_policy_rowtrace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
            policy=current_policy,
            label="current_runtime",
        )
        candidate_eval = _evaluate_policy_rowtrace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
            policy=merged_policy,
            label="candidate",
        )
    else:
        current_eval = _evaluate_policy(dataset=dataset, policy=current_policy, label="current_runtime")
        candidate_eval = _evaluate_policy(dataset=dataset, policy=merged_policy, label="candidate")

    current_eval_path = output_dir / f"policy-eval-current-{stamp}.json"
    candidate_eval_path = output_dir / f"policy-eval-candidate-{stamp}.json"
    _write_json(current_eval_path, current_eval)
    _write_json(candidate_eval_path, candidate_eval)

    compare_report = _compare_candidate_vs_current(current_eval, candidate_eval)

    coverage_snapshot_path = Path(
        str(
            os.environ.get(
                "TFE_L5_COVERAGE_SNAPSHOT_PATH",
                str(DEFAULT_COVERAGE_SNAPSHOT_PATH),
            )
        )
    )
    if not coverage_snapshot_path.exists() and LEGACY_COVERAGE_SNAPSHOT_PATH.exists():
        coverage_snapshot_path = LEGACY_COVERAGE_SNAPSHOT_PATH

    current_coverage = _snapshot_mapping_coverage(current_policy, coverage_snapshot_path)
    candidate_coverage = _snapshot_mapping_coverage(merged_policy, coverage_snapshot_path)

    promotion: Dict[str, Any] = {
        "promoted": False,
        "reason": "gates_failed",
    }

    if compare_report.get("promote") is True:
        promote_result = _atomic_promote(
            candidate_policy_path=candidate_policy_path,
            runtime_policy_path=runtime_policy_path,
            backup_dir=output_dir,
        )
        promotion = {
            "promoted": True,
            "reason": "gates_passed",
            **promote_result,
        }

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "trigger": trigger,
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "validation_dataset_path": str(validation_dataset_path),
            "runtime_policy_path": str(runtime_policy_path),
        },
        "artifacts": {
            "replay_policy_path": str(replay_policy_path),
            "candidate_policy_path": str(candidate_policy_path),
            "current_eval_path": str(current_eval_path),
            "candidate_eval_path": str(candidate_eval_path),
        },
        "merge_report": merge_report,
        "comparison": compare_report,
        "coverage": {
            "current_runtime": current_coverage,
            "candidate": candidate_coverage,
        },
        "promotion": promotion,
        "notes": {
            "irf_fmm_integration": "integrated:phase-key" if IRF_MODE == "phase" else "not integrated in this pipeline yet",
            "target_goal_reference": "index beat target is external business goal; promotion gate here is structural non-regression with mapping non-degradation",
            "cd_bucket_edges": list(CD_BUCKET_EDGES),
            "cd_regime_mode": CD_REGIME_MODE,
            "horizon_weights": HORIZON_WEIGHTS,
            "min_primary_cell_samples": MIN_PRIMARY_CELL_SAMPLES,
            "policy_source_mode": POLICY_SOURCE_MODE,
            "selection_objective": SELECTION_OBJECTIVE,
            "include_stability_bucket": INCLUDE_STABILITY_BUCKET,
            "irf_mode": IRF_MODE,
            "eval_mode": EVAL_MODE,
            "min_action_edge": MIN_ACTION_EDGE,
            "min_action_margin": MIN_ACTION_MARGIN,
            "min_action_winrate_pct": MIN_ACTION_WINRATE_PCT,
        },
    }

    _write_json(report_path, report)
    _write_json(DEFAULT_REPORT_LATEST_PATH, report)

    return LearningResult(report_path=report_path, report=report)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run L5 policy learning, validation, and gated promotion.")
    parser.add_argument("--trigger", type=str, default="manual")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_l5_policy_learning(trigger=str(args.trigger))
    print(result.report_path)
    print(json.dumps(result.report, indent=2))


if __name__ == "__main__":
    main()
