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
import hashlib
import json
import math
import os
import signal
import shutil
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from aws_root_key_provider import AwsSecretsRootKeyProvider
from ses_core import Envelope
from tfe_ses_core_adapter import TenantIdentity, decrypt_blob, initialize_ses_core_for_env, make_domain
from uf_core.uf_structural_engine import compute_uf_structural_state

from l5_postgres_io import (
    DB_MODE_FILE,
    DB_MODE_HYBRID,
    DB_MODE_POSTGRES,
    ensure_l5_policy_tables,
    load_latest_anomaly_policy_from_postgres,
    load_latest_horizon_overrides_from_postgres,
    load_latest_rowtrace_rows_from_postgres,
    load_latest_validation_dataset_from_postgres,
    load_latest_runtime_policy_from_postgres,
    normalize_l5_policy_io_mode,
    pg_preflight_for_l5,
    persist_eval_run_summary_to_postgres,
    persist_runtime_policy_to_postgres,
    postgres_mode_enabled,
    postgres_mode_is_strict,
)


HORIZONS: Tuple[int, int, int] = (5, 20, 60)
DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")


def _parse_bounded_int(env_name: str, default_value: int, lower_bound: int, upper_bound: int) -> int:
    raw = str(os.environ.get(env_name, str(default_value))).strip()
    try:
        value = int(raw)
    except Exception:
        value = int(default_value)
    if value < lower_bound:
        return lower_bound
    if value > upper_bound:
        return upper_bound
    return value


# Enforce structural history depth for L5 governance evaluation.
MIN_BARS = _parse_bounded_int("TFE_RECOMMENDATIONS_MIN_BARS", 252, 20, 2520)


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
SPIDER_EYES_MODE = str(os.environ.get("TFE_POLICY_SPIDER_EYES_MODE", "section23")).strip().lower()
EVAL_MODE = str(os.environ.get("TFE_POLICY_EVAL_MODE", "replay")).strip().lower()
MIN_ACTION_EDGE = _parse_bounded_float("TFE_POLICY_MIN_ACTION_EDGE", 0.0, lower_bound=0.0)
MIN_ACTION_MARGIN = _parse_bounded_float("TFE_POLICY_MIN_ACTION_MARGIN", 0.0, lower_bound=0.0)
MIN_ACTION_WINRATE_PCT = _parse_bounded_float(
    "TFE_POLICY_MIN_ACTION_WINRATE_PCT",
    0.0,
    lower_bound=0.0,
    upper_bound=100.0,
)
CANDIDATE_SAMPLE_ON_TARGETED = str(
    os.environ.get("TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_ON_TARGETED", "1")
).strip().lower() in ("1", "true", "yes", "on")
CANDIDATE_SAMPLE_SIZE = max(1, int(os.environ.get("TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_SIZE", "30")))
CANDIDATE_SAMPLE_SEED = int(os.environ.get("TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_SEED", "20260301"))
AUTO_PROMOTE_RUNTIME_POLICY = str(os.environ.get("TFE_POLICY_AUTO_PROMOTE", "0")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS = _parse_bounded_float(
    "TFE_POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS",
    180.0,
    lower_bound=15.0,
    upper_bound=7200.0,
)
POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS = _parse_bounded_float(
    "TFE_POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS",
    180.0,
    lower_bound=15.0,
    upper_bound=7200.0,
)
POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS = _parse_bounded_int(
    "TFE_POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS",
    25,
    1,
    5000,
)
POLICY_STATE_COMPUTE_TIMEOUT_SECONDS = _parse_bounded_float(
    "TFE_POLICY_STATE_COMPUTE_TIMEOUT_SECONDS",
    20.0,
    lower_bound=1.0,
    upper_bound=300.0,
)

L5_POLICY_IO_MODE = normalize_l5_policy_io_mode(
    os.environ.get("TFE_L5_POLICY_IO_MODE", DB_MODE_FILE)
)

DEFAULT_ROW_TRACE_PATH = Path("real_world_cleaned_universe_l5_row_trace_full.csv")
DEFAULT_RUNTIME_POLICY_PATH = Path("pscf_policy_runtime.json")
DEFAULT_REPORT_LATEST_PATH = Path("l5_policy_learning_latest.json")
REPORT_LATEST_PATH_OVERRIDE_ENV = "TFE_L5_REPORT_LATEST_PATH"
DEFAULT_OUTPUT_DIR = Path("backups/runtime/l5_policy_learning")
DEFAULT_COVERAGE_SNAPSHOT_PATH = Path("uf_snapshot.ses.json")
DEFAULT_HORIZON_DECISION_OVERRIDES_PATH = Path("policy_horizon_overrides.json")

COVERAGE_SES_PURPOSE_PREFIX = "tfe-web"
COVERAGE_SES_PURPOSE_SUFFIX = "uf-snapshot"
COVERAGE_SES_ACTOR_ID = "web-snapshot-pipeline"
COVERAGE_TENANT_ID = "tenant-tao"
COVERAGE_TENANT_DISPLAY_NAME = "Tao Tenant"


def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _utc_stamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _resolve_report_latest_path() -> Path:
    override_raw = str(os.environ.get(REPORT_LATEST_PATH_OVERRIDE_ENV, "")).strip()
    if not override_raw:
        return DEFAULT_REPORT_LATEST_PATH

    override_path = Path(override_raw)
    if override_path.is_absolute():
        return override_path
    return Path.cwd() / override_path


def _to_num(value: Any) -> float:
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except Exception:
        return 0.0


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on", "y"):
            return True
        if text in ("0", "false", "no", "off", "n", ""):
            return False
    return False


def _state_section(state: Any, key: str) -> Dict[str, Any]:
    if isinstance(state, dict):
        section = state.get(key, {})
    else:
        section = getattr(state, key, {})
    return section if isinstance(section, dict) else {}


class _L5StateComputeTimeout(TimeoutError):
    pass


def _l5_state_compute_timeout_handler(signum: int, frame: Any) -> None:
    raise _L5StateComputeTimeout("compute_uf_structural_state timed out")


def _compute_uf_state_guarded(hist_close: pd.Series) -> Tuple[Optional[Dict[str, Any]], bool]:
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _l5_state_compute_timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, POLICY_STATE_COMPUTE_TIMEOUT_SECONDS)
    try:
        state = compute_uf_structural_state(hist_close)
        if isinstance(state, dict):
            return state, False

        level1 = getattr(state, "level1", None)
        level2 = getattr(state, "level2", None)
        level3 = getattr(state, "level3", None)
        level4 = getattr(state, "level4", None)
        level5 = getattr(state, "level5", None)
        if (
            isinstance(level1, dict)
            and isinstance(level2, dict)
            and isinstance(level3, dict)
            and isinstance(level4, dict)
            and isinstance(level5, dict)
        ):
            return {
                "level1": level1,
                "level2": level2,
                "level3": level3,
                "level4": level4,
                "level5": level5,
            }, False
        return None, False
    except _L5StateComputeTimeout:
        return None, True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


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


def _spider_eyes_tag(guard_gate_unlock: bool, hardening_hysteresis_overload: bool) -> str:
    if guard_gate_unlock and hardening_hysteresis_overload:
        return "GU_HO"
    if guard_gate_unlock:
        return "GU"
    if hardening_hysteresis_overload:
        return "HO"
    return "NONE"


def _spider_eyes_suffix_from_flags(guard_gate_unlock: bool, hardening_hysteresis_overload: bool) -> str:
    if SPIDER_EYES_MODE in ("", "0", "off", "false", "no"):
        return ""
    return f"|SE={_spider_eyes_tag(guard_gate_unlock, hardening_hysteresis_overload)}"


def _spider_eyes_suffix_from_row(row: Dict[str, Any]) -> str:
    guard_obj = row.get("decision_guard")
    guard_gate_unlock = False
    if isinstance(guard_obj, dict):
        guard_gate_unlock = _to_bool(guard_obj.get("gate_unlock_transient_neutralized"))
    if not guard_gate_unlock:
        guard_gate_unlock = _to_bool(row.get("gate_unlock_transient_neutralized"))

    hard_obj = row.get("hardening")
    flags_obj = hard_obj.get("flags") if isinstance(hard_obj, dict) else None
    hardening_hysteresis_overload = False
    if isinstance(flags_obj, dict):
        hardening_hysteresis_overload = _to_bool(flags_obj.get("hysteresis_overload"))
    if not hardening_hysteresis_overload:
        hardening_hysteresis_overload = _to_bool(row.get("hysteresis_overload"))

    return _spider_eyes_suffix_from_flags(guard_gate_unlock, hardening_hysteresis_overload)


def _suffix_variants(core_key: str, irf_part: str, spider_part: str) -> List[str]:
    out: List[str] = []
    if irf_part and spider_part:
        out.append(f"{core_key}{irf_part}{spider_part}")
    if irf_part:
        out.append(f"{core_key}{irf_part}")
    if spider_part:
        out.append(f"{core_key}{spider_part}")
    out.append(core_key)
    return out


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
    c_k: int,
    p_b: str,
    b_sgn: int,
) -> str:
    return f"reg={regime}|D={d_k}|M={m_sgn}|Rrev={r_rev}|{u_b}|C={c_k}|{p_b}|B={b_sgn}"


def _row_trace_c_k(row: Dict[str, str]) -> int:
    c_raw = row.get("C")
    if c_raw is None or str(c_raw).strip() == "":
        c_raw = row.get("C_k")
    if c_raw is None or str(c_raw).strip() == "":
        raise ValueError("Row-trace row missing required C/C_k field for L4-complete policy key.")
    return int(round(_to_num(c_raw)))


def _row_trace_cell_key(row: Dict[str, str]) -> str:
    regime = str(row.get("regime", "UNKNOWN"))

    d_k = int(round(_to_num(row.get("D"))))
    m_sgn = _sign3(_to_num(row.get("M")))
    r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
    u_b = _u_bucket(_to_num(row.get("U_star")))
    c_k = _row_trace_c_k(row)
    p_b = _p_bucket(_to_num(row.get("P")))
    b_sgn = _sign3(_to_num(row.get("B")))

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn)
    s_uf = _to_num(row.get("S_UF"))
    r_uf = _to_num(row.get("R_UF"))
    st = _to_num(row.get("stability_score"))
    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)
    spider_part = _spider_eyes_suffix_from_row(row)
    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        core = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}"
        variants = _suffix_variants(core, irf_part, spider_part)
        return variants[0]
    core = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    variants = _suffix_variants(core, irf_part, spider_part)
    return variants[0]


def _row_trace_cell_key_candidates(row: Dict[str, str]) -> List[str]:
    regime = str(row.get("regime", "UNKNOWN"))

    d_k = int(round(_to_num(row.get("D"))))
    m_sgn = _sign3(_to_num(row.get("M")))
    r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
    u_b = _u_bucket(_to_num(row.get("U_star")))
    c_k = _row_trace_c_k(row)
    p_b = _p_bucket(_to_num(row.get("P")))
    b_sgn = _sign3(_to_num(row.get("B")))

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn)
    s_uf = _to_num(row.get("S_UF"))
    r_uf = _to_num(row.get("R_UF"))
    st = _to_num(row.get("stability_score"))

    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)
    spider_part = _spider_eyes_suffix_from_row(row)

    keys: List[str] = []

    if _include_cd_for_regime(regime):
        cd_key = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(s_uf - r_uf)}{st_part}"
        keys.extend(_suffix_variants(cd_key, irf_part, spider_part))

    sr_key = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    sr_legacy = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"

    keys.extend(_suffix_variants(sr_key, irf_part, spider_part))
    if sr_key != sr_legacy:
        keys.extend(_suffix_variants(sr_legacy, irf_part, spider_part))

    # Keep legacy base-key fallback for policies generated before enriched keys.
    keys.extend(_suffix_variants(base, "", spider_part))
    keys.append(base)

    deduped: List[str] = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    return deduped


def _level5_l4_components(level5: Dict[str, Any]) -> Optional[Tuple[int, int, int, str, int, str, int]]:
    dv_obj = level5.get("decision_vector", [])
    dv = dv_obj if isinstance(dv_obj, list) else []

    def dv_val(idx: int) -> Optional[float]:
        if idx < 0 or idx >= len(dv):
            return None
        return _to_num(dv[idx])

    d_raw: Any = level5.get("D_k")
    m_raw: Any = level5.get("M_k")
    r_raw: Any = level5.get("R_rev_k")
    u_raw: Any = level5.get("U_star_k")
    c_raw: Any = level5.get("C_k")
    p_raw: Any = level5.get("P_k")
    b_raw: Any = level5.get("B_k")

    if d_raw is None:
        d_raw = dv_val(0)
    if m_raw is None:
        m_raw = dv_val(1)
    if r_raw is None:
        r_raw = dv_val(2)
    if u_raw is None:
        u_raw = dv_val(3)

    if c_raw is None and len(dv) >= 7:
        c_raw = dv_val(4)

    if p_raw is None:
        if len(dv) >= 7:
            p_raw = dv_val(5)
        elif len(dv) >= 6:
            p_raw = dv_val(4)

    if b_raw is None:
        if len(dv) >= 7:
            b_raw = dv_val(6)
        elif len(dv) >= 6:
            b_raw = dv_val(5)

    if (
        d_raw is None
        or m_raw is None
        or r_raw is None
        or u_raw is None
        or c_raw is None
        or p_raw is None
        or b_raw is None
    ):
        return None

    d_k = int(round(_to_num(d_raw)))
    m_sgn = _sign3(_to_num(m_raw))
    r_rev = 1 if _to_num(r_raw) > 0.5 else 0
    u_b = _u_bucket(_to_num(u_raw))
    c_k = int(round(_to_num(c_raw)))
    p_b = _p_bucket(_to_num(p_raw))
    b_sgn = _sign3(_to_num(b_raw))

    return d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn


def _state_cell_key(state: Any) -> Optional[str]:
    level3 = _state_section(state, "level3")
    regime = str(level3.get("regime", "UNKNOWN"))

    level5 = _state_section(state, "level5")
    if len(level5) == 0:
        return None

    parts = _level5_l4_components(level5)
    if parts is None:
        return None

    d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn = parts

    level4 = _state_section(state, "level4")
    s_uf = _to_num(level4.get("S_UF", 0.0))
    r_uf = _to_num(level4.get("R_UF", 0.0))
    st = _to_num(level4.get("stability_score", 0.0))
    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)
    anomaly = _anomaly_flags_from_state(state)
    spider_part = _spider_eyes_suffix_from_flags(
        bool(anomaly.get("guard_gate_unlock", False)),
        bool(anomaly.get("hardening_hysteresis_overload", False)),
    )

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn)
    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        core = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}"
        variants = _suffix_variants(core, irf_part, spider_part)
        return variants[0]
    core = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    variants = _suffix_variants(core, irf_part, spider_part)
    return variants[0]


def _state_cell_key_candidates(state: Any) -> List[str]:
    level3 = _state_section(state, "level3")
    regime = str(level3.get("regime", "UNKNOWN"))

    level5 = _state_section(state, "level5")
    if len(level5) == 0:
        return []

    parts = _level5_l4_components(level5)
    if parts is None:
        return []

    d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn = parts

    base = _base_cell_key_from_parts(regime, d_k, m_sgn, r_rev, u_b, c_k, p_b, b_sgn)

    level4 = _state_section(state, "level4")
    s_uf = _to_num(level4.get("S_UF", 0.0))
    r_uf = _to_num(level4.get("R_UF", 0.0))
    st = _to_num(level4.get("stability_score", 0.0))

    st_part = f"|ST={_bucket_stability(st)}" if INCLUDE_STABILITY_BUCKET else ""
    irf_part = _irf_phase_suffix(m_sgn, r_uf)
    anomaly = _anomaly_flags_from_state(state)
    spider_part = _spider_eyes_suffix_from_flags(
        bool(anomaly.get("guard_gate_unlock", False)),
        bool(anomaly.get("hardening_hysteresis_overload", False)),
    )

    keys: List[str] = []

    if _include_cd_for_regime(regime):
        cd = s_uf - r_uf
        enriched_cd = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}|CD={_bucket_cd_opt(cd)}{st_part}"
        keys.extend(_suffix_variants(enriched_cd, irf_part, spider_part))

    enriched_sr = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}{st_part}"
    enriched_sr_legacy = f"{base}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"

    keys.extend(_suffix_variants(enriched_sr, irf_part, spider_part))
    if enriched_sr != enriched_sr_legacy:
        keys.extend(_suffix_variants(enriched_sr_legacy, irf_part, spider_part))

    keys.extend(_suffix_variants(base, "", spider_part))
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
        return Path(env)

    latest = _latest_path("backups/strict-ab-frozen-dataset-*.json")
    if latest is not None:
        return latest

    # In postgres/hybrid mode, dataset can come from DB; return expected fallback
    # path for metadata/error context without forcing file existence here.
    if postgres_mode_enabled(L5_POLICY_IO_MODE):
        return Path("backups/strict-ab-frozen-dataset-latest.json")

    raise FileNotFoundError("No validation dataset found. Expected backups/strict-ab-frozen-dataset-*.json")


def _resolve_anomaly_policy() -> Path:
    env = str(os.environ.get("TFE_POLICY_ANOMALY_POLICY", "")).strip()
    if env:
        return Path(env)

    candidates = sorted(
        Path(".").glob("backups/pscf-policy-anomaly-watch-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if "-report-" not in candidate.name:
            return candidate
    if candidates:
        return candidates[0]

    if postgres_mode_enabled(L5_POLICY_IO_MODE):
        return Path("backups/pscf-policy-anomaly-watch-latest.json")

    raise FileNotFoundError("No anomaly-watch policy found. Expected backups/pscf-policy-anomaly-watch-*.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _resolve_anomaly_policy_payload(anomaly_policy_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "anomaly_policy_path": str(anomaly_policy_path),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    def _load_file_payload(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Anomaly-watch policy not found: {path}")
        payload = _load_json(path)
        if not isinstance(payload, dict):
            raise ValueError("Anomaly-watch policy payload must be a JSON object.")
        cells = payload.get("cells")
        if not isinstance(cells, dict) or len(cells) <= 0:
            raise ValueError("Anomaly-watch policy payload must include non-empty cells object.")
        return payload

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        return _load_file_payload(anomaly_policy_path), metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()
    if preflight.ok:
        try:
            latest_policy = load_latest_anomaly_policy_from_postgres()
            if latest_policy and isinstance(latest_policy.get("policy"), dict):
                candidate = latest_policy["policy"]
                candidate_cells = candidate.get("cells")
                candidate_cells_count = len(candidate_cells) if isinstance(candidate_cells, dict) else 0
                if candidate_cells_count <= 0:
                    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                        raise RuntimeError("Postgres anomaly policy payload missing non-empty cells in strict mode.")
                    metadata["postgres_read_error"] = "postgres_anomaly_policy_cells_missing_or_empty"
                else:
                    metadata["source"] = "postgres"
                    metadata["postgres_policy_id"] = latest_policy.get("policy_id")
                    metadata["postgres_source_path"] = latest_policy.get("source_path")
                    metadata["postgres_generated_at_utc"] = latest_policy.get("generated_at_utc")
                    metadata["postgres_updated_at"] = latest_policy.get("updated_at")
                    metadata["postgres_cells_count"] = candidate_cells_count
                    return candidate, metadata
        except Exception as exc:
            msg = f"Anomaly policy load from postgres failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            metadata["postgres_read_error"] = msg
    elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode anomaly policy preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires anomaly policy row in table "
            "l5_anomaly_watch_policies."
        )

    payload = _load_file_payload(anomaly_policy_path)
    metadata["source"] = "file_fallback_postgres_unavailable_or_empty"
    return payload, metadata


def _resolve_validation_dataset_payload(validation_dataset_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "validation_dataset_path": str(validation_dataset_path),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        if not validation_dataset_path.exists():
            raise FileNotFoundError(f"Validation dataset not found: {validation_dataset_path}")
        payload = _load_json(validation_dataset_path)
        if not isinstance(payload, dict):
            raise ValueError("Validation dataset must be a JSON object.")
        return payload, metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()
    if preflight.ok:
        try:
            latest_dataset = load_latest_validation_dataset_from_postgres()
            if latest_dataset and isinstance(latest_dataset.get("dataset"), dict):
                metadata["source"] = "postgres"
                metadata["postgres_dataset_id"] = latest_dataset.get("dataset_id")
                metadata["postgres_source_path"] = latest_dataset.get("source_path")
                metadata["postgres_generated_at_utc"] = latest_dataset.get("generated_at_utc")
                metadata["postgres_updated_at"] = latest_dataset.get("updated_at")
                return latest_dataset["dataset"], metadata
        except Exception as exc:
            msg = f"Validation dataset load from postgres failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            metadata["postgres_read_error"] = msg
    elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode validation dataset preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires validation dataset row in table "
            "l5_validation_datasets."
        )

    if not validation_dataset_path.exists():
        raise FileNotFoundError(
            "Validation dataset fallback file not available after Postgres lookup failure/empty result: "
            f"{validation_dataset_path}"
        )

    payload = _load_json(validation_dataset_path)
    if not isinstance(payload, dict):
        raise ValueError("Validation dataset must be a JSON object.")
    metadata["source"] = "file_fallback_postgres_unavailable_or_empty"
    return payload, metadata


def _resolve_row_trace_rows_payload(row_trace_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "row_trace_path": str(row_trace_path),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    def _load_rows_from_file(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Row trace file not found: {path}")
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        return _load_rows_from_file(row_trace_path), metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()
    if preflight.ok:
        try:
            latest = load_latest_rowtrace_rows_from_postgres()
            if latest and isinstance(latest.get("rows"), list) and len(latest.get("rows") or []) > 0:
                metadata["source"] = "postgres"
                metadata["postgres_source_path"] = latest.get("source_path")
                metadata["postgres_row_count"] = int(latest.get("row_count") or len(latest.get("rows") or []))
                rows = latest.get("rows") or []
                return [dict(r) for r in rows if isinstance(r, dict)], metadata
        except Exception as exc:
            msg = f"Row trace load from postgres failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            metadata["postgres_read_error"] = msg
    elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode row trace preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires row-trace rows in table l5_rowtrace_events."
        )

    rows = _load_rows_from_file(row_trace_path)
    metadata["source"] = "file_fallback_postgres_unavailable_or_empty"
    return rows, metadata


def _resolve_spy_benchmark_payload(spy_dataset_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "spy_dataset_path": str(spy_dataset_path),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    def _load_file_payload(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"SPY dataset not found: {path}")
        payload = _load_json(path)
        if not isinstance(payload, dict):
            raise ValueError("SPY dataset payload must be a JSON object.")
        return payload

    def _spy_arrays_valid(payload: Dict[str, Any]) -> bool:
        spy = payload.get("spy")
        if not isinstance(spy, dict):
            return False
        ts_ms = spy.get("ts_ms")
        close = spy.get("close")
        return isinstance(ts_ms, list) and isinstance(close, list) and len(ts_ms) > 0 and len(close) > 0

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        payload = _load_file_payload(spy_dataset_path)
        if not _spy_arrays_valid(payload):
            raise ValueError("SPY dataset file payload missing valid spy.ts_ms/spy.close arrays.")
        return payload, metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()
    if preflight.ok:
        try:
            latest_dataset = load_latest_validation_dataset_from_postgres()
            if latest_dataset and isinstance(latest_dataset.get("dataset"), dict):
                candidate = latest_dataset["dataset"]
                if _spy_arrays_valid(candidate):
                    metadata["source"] = "postgres_validation_dataset"
                    metadata["postgres_dataset_id"] = latest_dataset.get("dataset_id")
                    metadata["postgres_source_path"] = latest_dataset.get("source_path")
                    metadata["postgres_generated_at_utc"] = latest_dataset.get("generated_at_utc")
                    metadata["postgres_updated_at"] = latest_dataset.get("updated_at")
                    return candidate, metadata
                if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                    raise RuntimeError("Postgres validation dataset missing valid spy arrays in strict mode.")
        except Exception as exc:
            msg = f"SPY benchmark dataset load from postgres failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            metadata["postgres_read_error"] = msg
    elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode SPY dataset preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires SPY benchmark arrays in table l5_validation_datasets."
        )

    payload = _load_file_payload(spy_dataset_path)
    if not _spy_arrays_valid(payload):
        raise ValueError("SPY dataset fallback file payload missing valid spy.ts_ms/spy.close arrays.")
    metadata["source"] = "file_fallback_postgres_unavailable_or_empty"
    return payload, metadata


def _resolve_horizon_decision_overrides_path() -> Optional[Path]:
    raw = str(
        os.environ.get(
            "TFE_POLICY_HORIZON_DECISION_OVERRIDES_PATH",
            str(DEFAULT_HORIZON_DECISION_OVERRIDES_PATH),
        )
    ).strip()
    if raw.lower() in ("", "0", "off", "false", "none", "null"):
        return None
    return Path(raw)


def _normalize_horizon_decision_overrides_payload(payload: Any) -> Dict[int, Dict[str, str]]:
    if not isinstance(payload, dict):
        raise ValueError("Horizon decision overrides must be a JSON object keyed by horizon.")

    out: Dict[int, Dict[str, str]] = {}
    for h_raw, mapping in payload.items():
        try:
            horizon = int(str(h_raw).strip())
        except Exception as exc:
            raise ValueError(f"Invalid horizon in overrides: {h_raw!r}") from exc

        if horizon not in HORIZONS:
            continue

        if not isinstance(mapping, dict):
            raise ValueError(f"Overrides for horizon {horizon} must be an object of cell_key->decision.")

        horizon_map: Dict[str, str] = {}
        for key_raw, decision_raw in mapping.items():
            cell_key = str(key_raw)
            decision = str(decision_raw)
            if decision not in DECISIONS:
                raise ValueError(
                    f"Invalid override decision {decision!r} for horizon {horizon} key {cell_key!r}; "
                    f"allowed={list(DECISIONS)}"
                )
            horizon_map[cell_key] = decision

        if horizon_map:
            out[horizon] = horizon_map

    return out


def _load_horizon_decision_overrides(path: Optional[Path]) -> Dict[int, Dict[str, str]]:
    if path is None or not path.exists():
        return {}
    payload = _load_json(path)
    return _normalize_horizon_decision_overrides_payload(payload)


def _resolve_horizon_decision_overrides_payload(path: Optional[Path]) -> Tuple[Dict[int, Dict[str, str]], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "horizon_decision_overrides_path": (str(path) if path is not None else None),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        return _load_horizon_decision_overrides(path), metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()
    if preflight.ok:
        try:
            latest = load_latest_horizon_overrides_from_postgres()
            if latest and isinstance(latest.get("overrides"), dict):
                normalized = _normalize_horizon_decision_overrides_payload(latest["overrides"])
                total_cells = sum(len(v) for v in normalized.values())
                if total_cells > 0:
                    metadata["source"] = "postgres"
                    metadata["postgres_override_set_id"] = latest.get("override_set_id")
                    metadata["postgres_source_path"] = latest.get("source_path")
                    metadata["postgres_generated_at_utc"] = latest.get("generated_at_utc")
                    metadata["postgres_updated_at"] = latest.get("updated_at")
                    metadata["postgres_total_overrides"] = int(total_cells)
                    return normalized, metadata
                if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                    raise RuntimeError("Postgres horizon overrides payload is empty in strict mode.")
                metadata["postgres_read_error"] = "postgres_horizon_overrides_empty"
        except Exception as exc:
            msg = f"Horizon overrides load from postgres failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            metadata["postgres_read_error"] = msg
    elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode horizon override preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires horizon override rows in table "
            "l5_policy_horizon_overrides."
        )

    metadata["source"] = "file_fallback_postgres_unavailable_or_empty"
    return _load_horizon_decision_overrides(path), metadata


def _apply_horizon_decision_override(base_decision: str, horizon: int, selected_key: Optional[str]) -> str:
    if selected_key is None:
        return base_decision

    override = HORIZON_DECISION_OVERRIDES.get(int(horizon), {}).get(selected_key)
    if override in DECISIONS:
        return str(override)
    return base_decision


def _horizon_override_counts_summary() -> Dict[str, int]:
    return {str(h): len(HORIZON_DECISION_OVERRIDES.get(h, {})) for h in HORIZONS}


HORIZON_DECISION_OVERRIDES_PATH = _resolve_horizon_decision_overrides_path()
HORIZON_DECISION_OVERRIDES, HORIZON_DECISION_OVERRIDES_RESOLUTION = _resolve_horizon_decision_overrides_payload(
    HORIZON_DECISION_OVERRIDES_PATH
)


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

    if not str(snapshot_path).lower().endswith(".ses.json"):
        return {
            "snapshot_path": str(snapshot_path),
            "status": "snapshot_format_not_supported",
            "rows": None,
        }

    # Envelope path (.ses.json) used in current production.
    try:
        environment = str(os.environ.get("TFE_ENV", "dev"))
        region = str(os.environ.get("TFE_REGION", os.environ.get("AWS_REGION", "local")))
        root_key_provider = None
        if environment.strip().lower() == "aws":
            root_key_provider = AwsSecretsRootKeyProvider.from_env()

        ctx = initialize_ses_core_for_env(
            environment=environment,
            region=region,
            purpose_prefix=COVERAGE_SES_PURPOSE_PREFIX,
            root_key_provider=root_key_provider,
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
    row_trace_rows, row_trace_resolve = _resolve_row_trace_rows_payload(row_trace_path)

    spy_payload, spy_dataset_resolve = _resolve_spy_benchmark_payload(spy_dataset_path)
    spy_ts = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close = [float(x) for x in spy_payload["spy"]["close"]]

    row_stats: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(_decision_stats_template)
    alias_votes: Dict[str, Counter] = defaultdict(Counter)

    row_count_total = 0
    row_count_used = 0
    row_count_skipped = Counter()

    for row in row_trace_rows:
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
        key_candidates = _row_trace_cell_key_candidates(row)
        for alias_key in key_candidates:
            if alias_key == cell_key:
                continue
            alias_votes[alias_key][cell_key] += 1

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

    alias_cells_added = 0
    alias_cells_skipped_no_primary = 0
    for alias_key, votes in sorted(alias_votes.items()):
        if alias_key in policy_cells:
            continue
        if len(votes) == 0:
            continue
        primary_key, primary_votes = votes.most_common(1)[0]
        primary_cell = policy_cells.get(primary_key)
        if not isinstance(primary_cell, dict):
            alias_cells_skipped_no_primary += 1
            continue
        alias_cell = json.loads(json.dumps(primary_cell))
        alias_cell["scoring_mode"] = "row_trace_alias_projection"
        alias_cell["alias_of_cell"] = str(primary_key)
        alias_cell["alias_vote_count"] = int(primary_votes)
        alias_cell["alias_total_votes"] = int(sum(votes.values()))
        policy_cells[alias_key] = alias_cell
        alias_cells_added += 1

    return {
        "generated_at_utc": _utc_now_iso(),
        "source": {
            "row_trace": str(row_trace_path),
            "row_trace_resolution": row_trace_resolve,
            "spy_benchmark_dataset": str(spy_dataset_path),
            "spy_benchmark_dataset_resolution": spy_dataset_resolve,
        },
        "coverage": {
            "row_count_total": row_count_total,
            "row_count_used": row_count_used,
            "row_count_used_pct": float(100.0 * row_count_used / row_count_total) if row_count_total > 0 else None,
            "row_count_skipped": dict(row_count_skipped),
            "alias_projection": {
                "alias_candidates_total": int(len(alias_votes)),
                "alias_cells_added": int(alias_cells_added),
                "alias_cells_skipped_no_primary": int(alias_cells_skipped_no_primary),
                "cells_total_after_alias": int(len(policy_cells)),
            },
        },
        "cell_key_schema": "regime + D + M_sign + R_rev + U_bucket + C + P_bucket + B_sign + S_bucket3 + R_bucket3 + CD_bucket_opt + PH_opt + SE_opt",
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
    replay_timeout_count = 0
    replay_state_compute_timeout_count = 0

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
        symbol_started = time.monotonic()
        timed_out = False
        timed_out_elapsed_seconds = 0.0
        timed_out_at_bar_index: Optional[int] = None
        for t in range(MIN_BARS - 1, n - max_h):
            if (t - (MIN_BARS - 1)) % POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS == 0:
                elapsed_seconds = time.monotonic() - symbol_started
                if elapsed_seconds >= POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS:
                    timed_out = True
                    timed_out_elapsed_seconds = elapsed_seconds
                    timed_out_at_bar_index = t
                    break
            hist_index = pd.to_datetime(ts[: t + 1], unit="ms", utc=True)
            hist_close = pd.Series(close[: t + 1], index=hist_index)

            try:
                state, state_timed_out = _compute_uf_state_guarded(hist_close)
            except Exception:
                continue

            if state_timed_out:
                replay_state_compute_timeout_count += 1
                if replay_state_compute_timeout_count <= 3 or replay_state_compute_timeout_count % 25 == 0:
                    print(
                        f"[L5-STATE-TIMEOUT:replay] {idx}/{len(symbols)} {sym} "
                        f"timeout={POLICY_STATE_COMPUTE_TIMEOUT_SECONDS:.1f}s "
                        f"count={replay_state_compute_timeout_count}"
                    )
                continue
            if not isinstance(state, dict):
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

        if timed_out:
            replay_timeout_count += 1
            symbol_coverage[sym] = {
                "status": "timeout",
                "bars": n,
                "evaluations": eval_count,
                "timeout_seconds_effective": POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS,
                "elapsed_seconds": round(timed_out_elapsed_seconds, 3),
                "timed_out_at_bar_index": int(timed_out_at_bar_index) if timed_out_at_bar_index is not None else None,
            }
            print(
                f"[L5-POLICY-REPLAY-TIMEOUT] {idx}/{len(symbols)} {sym} "
                f"elapsed={timed_out_elapsed_seconds:.1f}s timeout={POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS:.1f}s "
                f"evaluations={eval_count} bars={n}"
            )
            continue

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
        "cell_key_schema": "regime + D + M_sign + R_rev + U_bucket + C + P_bucket + B_sign + S_bucket3 + R_bucket3 + CD_bucket_opt + PH_opt + SE_opt",
        "decision_rule": "argmax mean_excess_vs_spy among {Accumulate, Hold, Avoid}",
        "scoring_policy": "score on non-anomalous samples; fallback to all samples when clean set is empty",
        "anomaly_any_definition": "guard_gate_unlock OR hardening_hysteresis_overload",
        "symbol_coverage": symbol_coverage,
        "symbol_timeout_controls": {
            "replay_symbol_timeout_seconds": POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS,
            "timeout_check_interval_bars": POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS,
        },
        "symbol_timeout_count": int(replay_timeout_count),
        "state_compute_timeout_controls": {
            "state_compute_timeout_seconds": POLICY_STATE_COMPUTE_TIMEOUT_SECONDS,
        },
        "state_compute_timeout_count": int(replay_state_compute_timeout_count),
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


def _overlay_anomaly_profiles(
    policy: Dict[str, Any],
    anomaly_policy: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    policy_cells = policy.get("cells", {})
    anomaly_cells = anomaly_policy.get("cells", {})
    if not isinstance(policy_cells, dict):
        raise ValueError("Policy cells must be an object for anomaly overlay.")
    if not isinstance(anomaly_cells, dict):
        raise ValueError("Anomaly policy cells must be an object for anomaly overlay.")

    out_cells: Dict[str, Dict[str, Any]] = {}
    overlay_count = 0
    already_present_count = 0
    missing_anomaly_profile_count = 0

    for cell_key, raw_cell in sorted(policy_cells.items()):
        if not isinstance(raw_cell, dict):
            continue
        cell = dict(raw_cell)
        current_profile = cell.get("anomaly_profile")
        current_available = isinstance(current_profile, dict) and bool(current_profile.get("available", False))

        anomaly_cell = anomaly_cells.get(cell_key)
        anomaly_profile = anomaly_cell.get("anomaly_profile") if isinstance(anomaly_cell, dict) else None
        anomaly_available = isinstance(anomaly_profile, dict)

        if current_available:
            already_present_count += 1
        elif anomaly_available:
            cell["anomaly_profile"] = dict(anomaly_profile)
            overlay_count += 1
        else:
            missing_anomaly_profile_count += 1

        out_cells[cell_key] = cell

    out_policy = dict(policy)
    out_policy["cells"] = out_cells

    overlay_report = {
        "generated_at_utc": _utc_now_iso(),
        "policy_cell_count": len(out_cells),
        "anomaly_policy_cell_count": len(anomaly_cells),
        "anomaly_profile_overlay_count": overlay_count,
        "anomaly_profile_already_present_count": already_present_count,
        "anomaly_profile_missing_after_overlay_count": missing_anomaly_profile_count,
    }

    return out_policy, overlay_report


def _anomaly_flags_from_state(state: Any) -> Dict[str, bool]:
    level5 = _state_section(state, "level5") if state is not None else {}

    guard = level5.get("decision_guard", {})
    guard_flag = _to_bool(guard.get("gate_unlock_transient_neutralized", False)) if isinstance(guard, dict) else False

    hard = level5.get("hardening", {})
    hard_flags = hard.get("flags", {}) if isinstance(hard, dict) else {}

    if isinstance(hard_flags, dict):
        hard_any = any(_to_bool(v) for v in hard_flags.values())
        hard_uncertainty_excess = _to_bool(hard_flags.get("uncertainty_excess", False))
        hard_hysteresis_overload = _to_bool(hard_flags.get("hysteresis_overload", False))
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


def _stable_hash_u64(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16)


def _price_bucket(latest_price: float) -> str:
    if latest_price < 5.0:
        return "P0"
    if latest_price < 20.0:
        return "P1"
    if latest_price < 100.0:
        return "P2"
    return "P3"


def _vol_bucket(close: List[float]) -> str:
    if len(close) < 3:
        return "V0"
    start = max(1, len(close) - 61)
    log_returns: List[float] = []
    for idx in range(start, len(close)):
        prev = float(close[idx - 1])
        cur = float(close[idx])
        if prev <= 0.0 or cur <= 0.0:
            continue
        log_returns.append(math.log(cur / prev))
    if len(log_returns) <= 1:
        return "V0"
    mean_ret = sum(log_returns) / len(log_returns)
    variance = sum((x - mean_ret) ** 2 for x in log_returns) / len(log_returns)
    vol = variance ** 0.5
    if vol < 0.01:
        return "V0"
    if vol < 0.02:
        return "V1"
    if vol < 0.04:
        return "V2"
    return "V3"


def _trend_bucket(close: List[float]) -> str:
    if len(close) < 2:
        return "T2"
    start_idx = max(0, len(close) - 61)
    anchor = float(close[start_idx])
    latest = float(close[-1])
    if anchor <= 0.0:
        return "T2"
    trend = latest / anchor - 1.0
    if trend < -0.20:
        return "T0"
    if trend < -0.05:
        return "T1"
    if trend < 0.05:
        return "T2"
    if trend < 0.20:
        return "T3"
    return "T4"


def _symbol_stratum_key(payload: Dict[str, Any]) -> str:
    close = [float(x) for x in payload.get("close", [])]
    if not close:
        return "P0|V0|T2"
    latest_price = float(close[-1])
    p_bucket = _price_bucket(latest_price=latest_price)
    v_bucket = _vol_bucket(close=close)
    t_bucket = _trend_bucket(close=close)
    return f"{p_bucket}|{v_bucket}|{t_bucket}"


def _rotation_index_utc_day() -> int:
    return int(datetime.datetime.utcnow().date().toordinal())


def _should_use_targeted_refresh_sampling(trigger: str) -> bool:
    if not CANDIDATE_SAMPLE_ON_TARGETED:
        return False
    return trigger.strip().lower().startswith("refresh:targeted")


def _dataset_with_symbol_subset(dataset: Dict[str, Any], selected_symbols: Sequence[str]) -> Dict[str, Any]:
    symbols_obj = dataset.get("symbols", {})
    if not isinstance(symbols_obj, dict):
        raise ValueError("Validation dataset symbols object is missing or invalid.")
    subset = {sym: symbols_obj[sym] for sym in selected_symbols if sym in symbols_obj}
    out = dict(dataset)
    out["symbols"] = subset
    return out


def _select_seeded_stratified_rotating_symbols(
    dataset: Dict[str, Any],
    sample_size: int,
    seed: int,
    rotation_index: int,
) -> Dict[str, Any]:
    symbols_obj = dataset.get("symbols", {})
    if not isinstance(symbols_obj, dict):
        raise ValueError("Validation dataset symbols object is missing or invalid.")
    all_symbols = sorted(str(sym) for sym in symbols_obj.keys())
    if not all_symbols:
        raise ValueError("Validation dataset has zero symbols.")
    target_size = max(1, min(int(sample_size), len(all_symbols)))

    strata: Dict[str, List[str]] = defaultdict(list)
    for sym in all_symbols:
        payload = symbols_obj.get(sym, {})
        if not isinstance(payload, dict):
            payload = {}
        strata[_symbol_stratum_key(payload)].append(sym)

    rotated_by_stratum: Dict[str, List[str]] = {}
    for stratum, symbols in strata.items():
        ordered = sorted(symbols, key=lambda s: _stable_hash_u64(f"{seed}|{stratum}|{s}"))
        if not ordered:
            rotated_by_stratum[stratum] = []
            continue
        offset_seed = _stable_hash_u64(f"{seed}|{stratum}|offset")
        offset = int((rotation_index + offset_seed) % len(ordered))
        rotated_by_stratum[stratum] = ordered[offset:] + ordered[:offset]

    strata_keys = sorted(rotated_by_stratum.keys())
    pointers: Dict[str, int] = {key: 0 for key in strata_keys}
    selected: List[str] = []

    for key in strata_keys:
        if len(selected) >= target_size:
            break
        bucket = rotated_by_stratum[key]
        if bucket:
            selected.append(bucket[0])
            pointers[key] = 1

    while len(selected) < target_size:
        made_progress = False
        for key in strata_keys:
            idx = pointers[key]
            bucket = rotated_by_stratum[key]
            if idx >= len(bucket):
                continue
            selected.append(bucket[idx])
            pointers[key] = idx + 1
            made_progress = True
            if len(selected) >= target_size:
                break
        if not made_progress:
            break

    selected_set = set(selected)
    selected_by_stratum = {key: 0 for key in strata_keys}
    for key, bucket in rotated_by_stratum.items():
        selected_by_stratum[key] = sum(1 for sym in bucket if sym in selected_set)

    return {
        "strategy": "seeded_stratified_rotating",
        "sample_size_requested": int(sample_size),
        "sample_size_selected": int(len(selected)),
        "seed": int(seed),
        "rotation_index": int(rotation_index),
        "total_symbols": int(len(all_symbols)),
        "strata_total": int(len(strata_keys)),
        "eligible_by_stratum": {key: int(len(rotated_by_stratum[key])) for key in strata_keys},
        "selected_by_stratum": {key: int(selected_by_stratum[key]) for key in strata_keys},
        "selected_symbols": selected,
    }


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
    override_counts: Dict[int, int] = {h: 0 for h in HORIZONS}
    symbol_timeout_count = 0
    timed_out_symbols: Dict[str, Dict[str, Any]] = {}
    eval_state_compute_timeout_count = 0

    symbols = sorted(dataset["symbols"].keys())

    for idx, sym in enumerate(symbols, start=1):
        payload = dataset["symbols"][sym]
        ts = [int(x) for x in payload.get("ts_ms", [])]
        close = [float(x) for x in payload.get("close", [])]

        n = len(close)
        if n < (MIN_BARS + max_h):
            continue

        symbol_started = time.monotonic()
        symbol_evaluations = 0
        timed_out = False
        timed_out_elapsed_seconds = 0.0
        timed_out_at_bar_index: Optional[int] = None
        for t in range(MIN_BARS - 1, n - max_h):
            if (t - (MIN_BARS - 1)) % POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS == 0:
                elapsed_seconds = time.monotonic() - symbol_started
                if elapsed_seconds >= POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS:
                    timed_out = True
                    timed_out_elapsed_seconds = elapsed_seconds
                    timed_out_at_bar_index = t
                    break
            hist_index = pd.to_datetime(ts[: t + 1], unit="ms", utc=True)
            hist_close = pd.Series(close[: t + 1], index=hist_index)

            try:
                state, state_timed_out = _compute_uf_state_guarded(hist_close)
            except Exception:
                continue

            if state_timed_out:
                eval_state_compute_timeout_count += 1
                if eval_state_compute_timeout_count <= 3 or eval_state_compute_timeout_count % 25 == 0:
                    print(
                        f"[L5-STATE-TIMEOUT:{label}] {idx}/{len(symbols)} {sym} "
                        f"timeout={POLICY_STATE_COMPUTE_TIMEOUT_SECONDS:.1f}s "
                        f"count={eval_state_compute_timeout_count}"
                    )
                continue
            if not isinstance(state, dict):
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

                decision_h = _apply_horizon_decision_override(decision, h, selected_key)
                if decision_h != decision:
                    override_counts[h] += 1

                action_ret = _decision_return(decision_h, sym_ret)
                action_ret_adj = 0.0 if anomaly["anomaly_any"] else action_ret

                horizon_decisions[h][decision_h] += 1
                horizon_action_returns[h].append(action_ret)
                horizon_action_returns_adj[h].append(action_ret_adj)
                horizon_bench[h].append(bench_ret)
                horizon_excess[h].append(action_ret - bench_ret)
                horizon_excess_adj[h].append(action_ret_adj - bench_ret)
                symbol_evaluations += 1

                anomaly_counts[h]["anomaly_any"] += int(anomaly["anomaly_any"])
                anomaly_counts[h]["guard_gate_unlock"] += int(anomaly["guard_gate_unlock"])
                anomaly_counts[h]["hardening_any"] += int(anomaly["hardening_any"])
                anomaly_counts[h]["hardening_uncertainty_excess"] += int(anomaly["hardening_uncertainty_excess"])
                anomaly_counts[h]["hardening_hysteresis_overload"] += int(anomaly["hardening_hysteresis_overload"])

                mapping_counts[h]["mapped"] += int(mapped)
                mapping_counts[h]["unmapped"] += int(not mapped)

        if timed_out:
            symbol_timeout_count += 1
            timed_out_symbols[sym] = {
                "bars": n,
                "evaluations_recorded": symbol_evaluations,
                "timeout_seconds_effective": POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS,
                "elapsed_seconds": round(timed_out_elapsed_seconds, 3),
                "timed_out_at_bar_index": int(timed_out_at_bar_index) if timed_out_at_bar_index is not None else None,
            }
            print(
                f"[L5-EVAL-TIMEOUT:{label}] {idx}/{len(symbols)} {sym} "
                f"elapsed={timed_out_elapsed_seconds:.1f}s timeout={POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS:.1f}s "
                f"evaluations_recorded={symbol_evaluations} bars={n}"
            )
            continue

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
            "decision_overrides": {
                "horizon_key_override_count": int(override_counts[h]),
            },
        }

    return {
        "generated_at_utc": _utc_now_iso(),
        "label": label,
        "config": {
            "horizons": list(HORIZONS),
            "min_bars": MIN_BARS,
            "benchmark": "SPY",
            "evaluated_symbol_count": int(len(symbols)),
            "decision_source": "policy_cell_mapping_only",
            "anomaly_accounting": "anomaly_any => neutral action (Hold=0) for adjusted scores",
            "anomaly_any_definition": "guard_gate_unlock OR hardening_hysteresis_overload",
            "horizon_decision_overrides_path": (
                str(HORIZON_DECISION_OVERRIDES_PATH) if HORIZON_DECISION_OVERRIDES_PATH is not None else None
            ),
            "horizon_decision_overrides_cells_by_horizon": _horizon_override_counts_summary(),
            "horizon_decision_overrides_resolution": HORIZON_DECISION_OVERRIDES_RESOLUTION,
        },
        "symbol_timeout_controls": {
            "eval_symbol_timeout_seconds": POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS,
            "timeout_check_interval_bars": POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS,
        },
        "state_compute_timeout_controls": {
            "state_compute_timeout_seconds": POLICY_STATE_COMPUTE_TIMEOUT_SECONDS,
        },
        "state_compute_timeout_count": int(eval_state_compute_timeout_count),
        "symbol_timeouts": {
            "count": int(symbol_timeout_count),
            "symbols": timed_out_symbols,
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
    override_counts: Dict[int, int] = {h: 0 for h in HORIZONS}

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

            h = horizon
            decision_h = _apply_horizon_decision_override(decision, h, selected_key)
            if decision_h != decision:
                override_counts[h] += 1

            action_ret = _decision_return(decision_h, forward_return)
            action_ret_adj = action_ret

            horizon_decisions[h][decision_h] += 1
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
            "decision_overrides": {
                "horizon_key_override_count": int(override_counts[h]),
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
            "horizon_decision_overrides_path": (
                str(HORIZON_DECISION_OVERRIDES_PATH) if HORIZON_DECISION_OVERRIDES_PATH is not None else None
            ),
            "horizon_decision_overrides_cells_by_horizon": _horizon_override_counts_summary(),
            "horizon_decision_overrides_resolution": HORIZON_DECISION_OVERRIDES_RESOLUTION,
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

        level5_like = {
            "decision_vector": row.get("decision_vector"),
            "D_k": row.get("D_k"),
            "M_k": row.get("M_k"),
            "R_rev_k": row.get("R_rev_k"),
            "U_star_k": row.get("U_star_k"),
            "C_k": row.get("C_k"),
            "P_k": row.get("P_k"),
            "B_k": row.get("B_k"),
        }
        parts = _level5_l4_components(level5_like)
        if parts is None:
            unmapped += 1
            continue

        regime = str(row.get("regime", "UNKNOWN"))
        d, m, rrev, u, c, p, b = parts

        base = _base_cell_key_from_parts(regime, d, m, rrev, u, c, p, b)
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
        spider_part = _spider_eyes_suffix_from_row(row)
        candidates: List[str] = []
        if enriched_cd is not None:
            candidates.extend(_suffix_variants(enriched_cd, irf_part, spider_part))
        candidates.extend(_suffix_variants(enriched_sr, irf_part, spider_part))
        candidates.extend(_suffix_variants(enriched_sr_legacy, irf_part, spider_part))
        candidates.extend(_suffix_variants(base, "", spider_part))
        candidates.append(base)

        if any(candidate in cells for candidate in candidates):
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


def _resolve_current_runtime_policy(runtime_policy_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "io_mode": L5_POLICY_IO_MODE,
        "runtime_policy_path": str(runtime_policy_path),
        "source": "file",
        "postgres_enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "postgres_strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
    }

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        if not runtime_policy_path.exists():
            raise FileNotFoundError(f"Runtime policy not found: {runtime_policy_path}")
        return _load_json(runtime_policy_path), metadata

    preflight = pg_preflight_for_l5()
    metadata["postgres_preflight"] = preflight.as_dict()

    if not preflight.ok:
        if postgres_mode_is_strict(L5_POLICY_IO_MODE):
            raise RuntimeError(
                "Strict L5 Postgres mode preflight failed: "
                f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
            )
        if not runtime_policy_path.exists():
            raise FileNotFoundError(
                "Runtime policy fallback not available after Postgres preflight failure: "
                f"{runtime_policy_path}"
            )
        metadata["source"] = "file_fallback_postgres_preflight_failed"
        return _load_json(runtime_policy_path), metadata

    table_result = ensure_l5_policy_tables()
    metadata["postgres_tables"] = table_result

    latest_runtime = load_latest_runtime_policy_from_postgres()
    if latest_runtime and isinstance(latest_runtime.get("policy"), dict):
        metadata["source"] = "postgres"
        metadata["postgres_policy_version_id"] = latest_runtime.get("policy_version_id")
        metadata["postgres_policy_trigger"] = latest_runtime.get("trigger")
        metadata["postgres_policy_promoted_at_utc"] = latest_runtime.get("promoted_at_utc")
        return latest_runtime["policy"], metadata

    if postgres_mode_is_strict(L5_POLICY_IO_MODE):
        raise RuntimeError(
            "Strict L5 Postgres mode requires existing runtime policy in table "
            "l5_policy_runtime_current."
        )

    if not runtime_policy_path.exists():
        raise FileNotFoundError(
            "Runtime policy fallback not available when Postgres runtime policy table is empty: "
            f"{runtime_policy_path}"
        )

    metadata["source"] = "file_fallback_postgres_empty"
    return _load_json(runtime_policy_path), metadata


def _persist_l5_outputs_to_postgres(
    *,
    stamp: str,
    trigger: str,
    source_mode: str,
    eval_mode: str,
    evaluation_scope: str,
    comparison: Dict[str, Any],
    promotion: Dict[str, Any],
    coverage: Dict[str, Any],
    notes: Dict[str, Any],
    artifacts: Dict[str, Any],
    merged_policy: Dict[str, Any],
    report_path: Path,
) -> Dict[str, Any]:
    details: Dict[str, Any] = {
        "enabled": postgres_mode_enabled(L5_POLICY_IO_MODE),
        "io_mode": L5_POLICY_IO_MODE,
        "strict": postgres_mode_is_strict(L5_POLICY_IO_MODE),
        "status": "skipped",
        "policy_runtime_write": None,
        "eval_run_write": None,
        "errors": [],
    }

    if not postgres_mode_enabled(L5_POLICY_IO_MODE):
        return details

    preflight = pg_preflight_for_l5()
    details["postgres_preflight"] = preflight.as_dict()
    if not preflight.ok:
        msg = (
            "L5 Postgres persistence preflight failed: "
            f"{json.dumps(preflight.as_dict(), sort_keys=True)}"
        )
        if postgres_mode_is_strict(L5_POLICY_IO_MODE):
            raise RuntimeError(msg)
        details["status"] = "preflight_failed"
        details["errors"].append(msg)
        return details

    try:
        details["postgres_tables"] = ensure_l5_policy_tables()
    except Exception as exc:
        msg = f"L5 Postgres table ensure failed: {type(exc).__name__}: {exc}"
        if postgres_mode_is_strict(L5_POLICY_IO_MODE):
            raise RuntimeError(msg) from exc
        details["status"] = "table_ensure_failed"
        details["errors"].append(msg)
        return details

    if bool(promotion.get("promoted")):
        try:
            details["policy_runtime_write"] = persist_runtime_policy_to_postgres(
                policy=merged_policy,
                trigger=str(trigger),
                source="l5_policy_learning",
                compare_report=comparison,
                report_path=str(report_path),
            )
        except Exception as exc:
            msg = f"L5 Postgres runtime policy write failed: {type(exc).__name__}: {exc}"
            if postgres_mode_is_strict(L5_POLICY_IO_MODE):
                raise RuntimeError(msg) from exc
            details["errors"].append(msg)

    eval_run_id = f"l5-policy-eval-{stamp}"
    try:
        details["eval_run_write"] = persist_eval_run_summary_to_postgres(
            eval_run_id=eval_run_id,
            generated_at_utc=_utc_now_iso(),
            trigger=str(trigger),
            policy_source_mode=str(source_mode),
            eval_mode=str(eval_mode),
            evaluation_scope=str(evaluation_scope),
            comparison=comparison,
            promotion=promotion,
            coverage=coverage,
            notes=notes,
            artifact_paths=artifacts,
        )
    except Exception as exc:
        msg = f"L5 Postgres eval summary write failed: {type(exc).__name__}: {exc}"
        if postgres_mode_is_strict(L5_POLICY_IO_MODE):
            raise RuntimeError(msg) from exc
        details["errors"].append(msg)

    details["eval_run_id"] = eval_run_id
    details["status"] = "ok" if len(details["errors"]) == 0 else "partial"
    return details


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
    report_latest_path = _resolve_report_latest_path()

    row_trace_path = Path(str(os.environ.get("TFE_POLICY_ROW_TRACE", str(DEFAULT_ROW_TRACE_PATH))))
    runtime_policy_path = Path(str(os.environ.get("TFE_RUNTIME_POLICY_PATH", str(DEFAULT_RUNTIME_POLICY_PATH))))
    anomaly_policy_path = _resolve_anomaly_policy()
    validation_dataset_path = _resolve_validation_dataset()
    needs_validation_dataset = bool(POLICY_SOURCE_MODE in ("replay", "hybrid") or EVAL_MODE != "rowtrace")
    needs_spy_dataset = bool(POLICY_SOURCE_MODE in ("rowtrace", "hybrid") or EVAL_MODE == "rowtrace")
    spy_dataset_path: Optional[Path] = _resolve_spy_dataset() if needs_spy_dataset else None

    report_path = output_dir / f"l5-policy-learning-report-{stamp}.json"

    current_policy, runtime_policy_resolve = _resolve_current_runtime_policy(runtime_policy_path)
    anomaly_policy, anomaly_policy_resolve = _resolve_anomaly_policy_payload(anomaly_policy_path)
    validation_dataset_resolve: Dict[str, Any] = {
        "source": "not_required_for_current_modes",
        "io_mode": L5_POLICY_IO_MODE,
        "validation_dataset_path": str(validation_dataset_path),
    }
    dataset: Optional[Dict[str, Any]] = None
    if needs_validation_dataset:
        dataset, validation_dataset_resolve = _resolve_validation_dataset_payload(validation_dataset_path)

    if POLICY_SOURCE_MODE == "rowtrace":
        if spy_dataset_path is None:
            raise RuntimeError("SPY dataset path is required for POLICY_SOURCE_MODE=rowtrace.")
        replay_policy = _generate_policy_from_row_trace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
        )
    elif POLICY_SOURCE_MODE == "hybrid":
        if dataset is None:
            raise RuntimeError("Validation dataset is required for POLICY_SOURCE_MODE=hybrid.")
        if spy_dataset_path is None:
            raise RuntimeError("SPY dataset path is required for POLICY_SOURCE_MODE=hybrid.")
        replay_from_dataset = _generate_policy_from_replay_dataset(dataset=dataset, dataset_path=validation_dataset_path)
        replay_from_rowtrace = _generate_policy_from_row_trace(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
        )
        replay_policy, _ = _merge_policies(replay_from_rowtrace, replay_from_dataset)
    else:
        if dataset is None:
            raise RuntimeError("Validation dataset is required for POLICY_SOURCE_MODE=replay.")
        replay_policy = _generate_policy_from_replay_dataset(dataset=dataset, dataset_path=validation_dataset_path)
    replay_policy_path = output_dir / f"pscf-policy-replay-spy-{stamp}.json"
    _write_json(replay_policy_path, replay_policy)

    # Preserve current-runtime coverage for cells absent in replay-derived policy.
    merged_policy, merge_report = _merge_policies(replay_policy, current_policy)
    merged_policy, anomaly_overlay_report = _overlay_anomaly_profiles(merged_policy, anomaly_policy)
    candidate_policy_path = output_dir / f"pscf-policy-candidate-{stamp}.json"
    _write_json(candidate_policy_path, merged_policy)

    candidate_sampling_report: Optional[Dict[str, Any]] = None
    candidate_sampling_artifact_path: Optional[Path] = None
    eval_dataset = dataset

    if EVAL_MODE != "rowtrace" and _should_use_targeted_refresh_sampling(trigger=trigger):
        if dataset is None:
            raise RuntimeError("Validation dataset is required for targeted candidate sampling.")
        rotation_index = _rotation_index_utc_day()
        candidate_sampling_report = _select_seeded_stratified_rotating_symbols(
            dataset=dataset,
            sample_size=CANDIDATE_SAMPLE_SIZE,
            seed=CANDIDATE_SAMPLE_SEED,
            rotation_index=rotation_index,
        )
        eval_dataset = _dataset_with_symbol_subset(
            dataset=dataset,
            selected_symbols=candidate_sampling_report["selected_symbols"],
        )
        candidate_sampling_report["trigger"] = str(trigger)
        candidate_sampling_report["rotation_basis"] = "utc_day_ordinal"
        candidate_sampling_artifact_path = output_dir / f"policy-eval-candidate-sample-{stamp}.json"
        _write_json(candidate_sampling_artifact_path, candidate_sampling_report)

    if EVAL_MODE == "rowtrace":
        if spy_dataset_path is None:
            raise RuntimeError("SPY dataset path is required for EVAL_MODE=rowtrace.")
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
        if eval_dataset is None:
            raise RuntimeError("Validation dataset is required for EVAL_MODE!=rowtrace.")
        current_eval = _evaluate_policy(dataset=eval_dataset, policy=current_policy, label="current_runtime")
        candidate_eval = _evaluate_policy(dataset=eval_dataset, policy=merged_policy, label="candidate")

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

    current_coverage = _snapshot_mapping_coverage(current_policy, coverage_snapshot_path)
    candidate_coverage = _snapshot_mapping_coverage(merged_policy, coverage_snapshot_path)

    promotion: Dict[str, Any] = {
        "promoted": False,
        "reason": "gates_failed",
    }

    if compare_report.get("promote") is True:
        if not AUTO_PROMOTE_RUNTIME_POLICY:
            promotion = {
                "promoted": False,
                "reason": "gates_passed_auto_promote_disabled",
                "auto_promote_enabled": False,
            }
        elif postgres_mode_is_strict(L5_POLICY_IO_MODE):
            promotion = {
                "promoted": True,
                "reason": "gates_passed",
                "promoted_at_utc": _utc_now_iso(),
                "runtime_policy_path": None,
                "backup_path": None,
                "candidate_policy_path": str(candidate_policy_path),
                "promotion_target": "postgres_only",
                "auto_promote_enabled": True,
            }
        else:
            promote_result = _atomic_promote(
                candidate_policy_path=candidate_policy_path,
                runtime_policy_path=runtime_policy_path,
                backup_dir=output_dir,
            )
            promotion = {
                "promoted": True,
                "reason": "gates_passed",
                **promote_result,
                "promotion_target": "runtime_policy_file",
                "auto_promote_enabled": True,
            }

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "trigger": trigger,
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path) if spy_dataset_path is not None else None,
            "validation_dataset_path": str(validation_dataset_path),
            "validation_dataset_source": validation_dataset_resolve.get("source"),
            "anomaly_policy_path": str(anomaly_policy_path),
            "anomaly_policy_source": anomaly_policy_resolve.get("source"),
            "runtime_policy_path": str(runtime_policy_path),
            "runtime_policy_source": runtime_policy_resolve.get("source"),
            "policy_io_mode": L5_POLICY_IO_MODE,
            "evaluation_scope": (
                "targeted_seeded_stratified_sample"
                if candidate_sampling_report is not None
                else "full_broad"
            ),
            "evaluation_symbol_count": (
                int(len(eval_dataset.get("symbols", {}))) if isinstance(eval_dataset, dict) else None
            ),
        },
        "artifacts": {
            "replay_policy_path": str(replay_policy_path),
            "candidate_policy_path": str(candidate_policy_path),
            "current_eval_path": str(current_eval_path),
            "candidate_eval_path": str(candidate_eval_path),
            "latest_report_path": str(report_latest_path),
            "candidate_sampling_path": (
                str(candidate_sampling_artifact_path) if candidate_sampling_artifact_path is not None else None
            ),
        },
        "merge_report": merge_report,
        "anomaly_overlay_report": anomaly_overlay_report,
        "comparison": compare_report,
        "coverage": {
            "current_runtime": current_coverage,
            "candidate": candidate_coverage,
        },
        "promotion": promotion,
        "notes": {
            "irf_fmm_integration": "integrated:phase-key" if IRF_MODE == "phase" else "not integrated in this pipeline yet",
            "spider_eyes_integration": (
                "integrated:section23-key"
                if SPIDER_EYES_MODE not in ("", "0", "off", "false", "no")
                else "disabled"
            ),
            "target_goal_reference": "index beat target is external business goal; promotion gate here is structural non-regression with mapping non-degradation",
            "cd_bucket_edges": list(CD_BUCKET_EDGES),
            "cd_regime_mode": CD_REGIME_MODE,
            "horizon_weights": HORIZON_WEIGHTS,
            "min_primary_cell_samples": MIN_PRIMARY_CELL_SAMPLES,
            "policy_source_mode": POLICY_SOURCE_MODE,
            "selection_objective": SELECTION_OBJECTIVE,
            "auto_promote_runtime_policy": bool(AUTO_PROMOTE_RUNTIME_POLICY),
            "include_stability_bucket": INCLUDE_STABILITY_BUCKET,
            "irf_mode": IRF_MODE,
            "spider_eyes_mode": SPIDER_EYES_MODE,
            "eval_mode": EVAL_MODE,
            "refresh_candidate_sample_on_targeted": CANDIDATE_SAMPLE_ON_TARGETED,
            "refresh_candidate_sample_size": int(CANDIDATE_SAMPLE_SIZE),
            "refresh_candidate_sample_seed": int(CANDIDATE_SAMPLE_SEED),
            "min_action_edge": MIN_ACTION_EDGE,
            "min_action_margin": MIN_ACTION_MARGIN,
            "min_action_winrate_pct": MIN_ACTION_WINRATE_PCT,
            "horizon_decision_overrides_path": (
                str(HORIZON_DECISION_OVERRIDES_PATH) if HORIZON_DECISION_OVERRIDES_PATH is not None else None
            ),
            "horizon_decision_overrides_cells_by_horizon": _horizon_override_counts_summary(),
            "horizon_decision_overrides_resolution": HORIZON_DECISION_OVERRIDES_RESOLUTION,
            "policy_io_mode": L5_POLICY_IO_MODE,
            "runtime_policy_resolution": runtime_policy_resolve,
            "validation_dataset_resolution": validation_dataset_resolve,
            "anomaly_policy_resolution": anomaly_policy_resolve,
        },
    }

    postgres_persistence = _persist_l5_outputs_to_postgres(
        stamp=stamp,
        trigger=str(trigger),
        source_mode=str(POLICY_SOURCE_MODE),
        eval_mode=str(EVAL_MODE),
        evaluation_scope=str(report["inputs"]["evaluation_scope"]),
        comparison=compare_report,
        promotion=promotion,
        coverage=report["coverage"],
        notes=report["notes"],
        artifacts=report["artifacts"],
        merged_policy=merged_policy,
        report_path=report_path,
    )
    report["postgres_persistence"] = postgres_persistence

    _write_json(report_path, report)
    _write_json(report_latest_path, report)

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
