#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import itertools
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path("/tmp/g32_insanity_loop")
RUNS_DIR = ROOT / "runs"
LOG_PATH = ROOT / "loop.log"
RESULTS_PATH = ROOT / "results.jsonl"
BEST_PATH = ROOT / "best_summary.json"
STATE_PATH = ROOT / "state.json"
STOP_PATH = ROOT / "STOP"
LOCK_PATH = ROOT / "LOCK"
UNFAVORABLE_PATH = ROOT / "unfavorable_runs.jsonl"
AB_STATE_PATH = ROOT / "ab_state.json"
AB_SUMMARY_PATH = ROOT / "ab_summary.json"

WORKSPACE = Path("/workspaces/Tao_Financial_Engine")
RUNNER = WORKSPACE / "g32_horse_race.py"
ROW_TRACE = WORKSPACE / "real_world_cleaned_universe_l5_row_trace_full.csv"
DATASET = WORKSPACE / "backups/strict-ab-frozen-dataset-20260218T133559Z.json"

RNG_SEED = 20260219
RUN_TIMEOUT_SECONDS = 3000
TARGET_AVG_OUTCOME = 80.0
BASELINE_REFERENCE = 42.15330258121504
ADAPTIVE_MIN_HISTORY = 20
ADAPTIVE_EXPLORE_RATE = 0.30
ADAPTIVE_RETRIES = 1200
PLATEAU_REEXPLORE_AFTER = 20
PLATEAU_EXPLORE_MAX = 0.90

NEG_FIELD_UNFAVORABLE_MAX = 500
NEG_FIELD_PROXIMITY_WEIGHT = 4.2
NEG_FIELD_UNCERTAINTY_BONUS = 1.40
NEG_FIELD_TEMPERATURE_BASE = 0.28
NEG_FIELD_TEMPERATURE_STEP = 0.012

AB_WARMUP_RUNS = 24
AB_ARM_EXPLORATION = 0.20
AB_ARM_BASELINE = "baseline_estimated"
AB_ARM_SOFT = "soft_negative_space"
CURRENT_OBJECTIVE_METRIC = "avg_return_multiple_over_spy_pct_log_v2"

REQUIRED_CONFIG_KEYS = (
    "min_samples_grid",
    "min_suf_grid",
    "include_irf_modes",
    "train_fracs",
    "test_frac",
    "min_edge_grid",
    "min_winrate_grid",
    "uncertainty_penalty_grid",
    "hold_bias_grid",
)


def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def stamp() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def log(msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def stop_requested() -> bool:
    return STOP_PATH.exists()


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    return Path(f"/proc/{pid}").exists()


def _sha256_path(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _file_fingerprint(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": None,
            "mtime_epoch": None,
            "sha256": None,
        }
    st = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": int(st.st_size),
        "mtime_epoch": float(st.st_mtime),
        "sha256": _sha256_path(path),
    }


def build_fingerprint() -> Dict[str, Any]:
    loop_runner = Path(__file__).resolve()
    return {
        "fingerprint_version": "v1",
        "captured_at_utc": utc_now(),
        "python_version": sys.version.split()[0],
        "runner": _file_fingerprint(RUNNER),
        "loop_runner": _file_fingerprint(loop_runner),
        "row_trace": _file_fingerprint(ROW_TRACE),
        "dataset": _file_fingerprint(DATASET),
    }


def acquire_lock() -> bool:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    me = os.getpid()
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(me))
        return True
    except FileExistsError:
        try:
            current = int(LOCK_PATH.read_text().strip())
        except Exception:
            current = 0
        if _pid_running(current):
            log(f"lock_active pid={current}; exiting")
            return False
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(me))
        return True


def release_lock() -> None:
    try:
        if LOCK_PATH.exists():
            lock_pid = int(LOCK_PATH.read_text().strip())
            if lock_pid == os.getpid():
                LOCK_PATH.unlink()
    except Exception:
        pass


def build_pool() -> List[Dict[str, str]]:
    min_samples_grid = [
        "1,3,5,10,20",
        "1,5,10,20,30,40",
    ]
    min_suf_grid = [
        "0.05,0.10,0.20,0.30,0.40,0.50,0.60",
        "0.10,0.20,0.30,0.40,0.50,0.60,0.70",
        "0.20,0.30,0.40,0.50,0.60,0.70,0.80",
    ]
    include_irf_modes = ["0", "1", "0,1"]
    train_fracs = [
        "0.45,0.55,0.65,0.75",
        "0.50,0.60,0.70,0.80",
        "0.60,0.70,0.80,0.90",
    ]
    test_frac = ["0.08", "0.10", "0.12"]
    min_edge_values = ["0.0", "0.001", "0.003", "0.006"]
    min_winrate_values = ["0", "50", "60", "70"]
    uncertainty_penalty_values = ["0.0", "0.001", "0.01", "0.05"]
    hold_bias_values = ["-0.001", "0.0", "0.002", "0.005"]

    pool: List[Dict[str, str]] = []
    for a, b, c, d, e, f, g, h, i in itertools.product(
        min_samples_grid,
        min_suf_grid,
        include_irf_modes,
        train_fracs,
        test_frac,
        min_edge_values,
        min_winrate_values,
        uncertainty_penalty_values,
        hold_bias_values,
    ):
        pool.append(
            {
                "min_samples_grid": a,
                "min_suf_grid": b,
                "include_irf_modes": c,
                "train_fracs": d,
                "test_frac": e,
                "min_edge_grid": f,
                "min_winrate_grid": g,
                "uncertainty_penalty_grid": h,
                "hold_bias_grid": i,
            }
        )
    return pool


def normalize_config(cfg: Dict[str, Any]) -> Optional[Dict[str, str]]:
    normalized = {str(k): str(v) for k, v in cfg.items()}
    for key in REQUIRED_CONFIG_KEYS:
        if key not in normalized:
            return None
    return {key: normalized[key] for key in REQUIRED_CONFIG_KEYS}


def config_signature(cfg: Dict[str, str]) -> str:
    keys = sorted(cfg.keys())
    return "|".join(f"{k}={cfg[k]}" for k in keys)


def load_seen() -> set[str]:
    seen: set[str] = set()
    if not RESULTS_PATH.exists():
        return seen
    for line in RESULTS_PATH.read_text().splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        cfg = obj.get("config")
        if isinstance(cfg, dict):
            normalized = normalize_config(cfg)
            if normalized is not None:
                seen.add(config_signature(normalized))
    return seen


def load_scored_history() -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    if not RESULTS_PATH.exists():
        return history
    for line in RESULTS_PATH.read_text().splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("status") != "ok":
            continue
        metric = str(obj.get("objective_metric", "")).strip()
        if metric != CURRENT_OBJECTIVE_METRIC:
            continue
        score = obj.get("legacy_outcome_score")
        if not isinstance(score, (int, float)):
            score = obj.get("g32_symbol_avg_outcome_over_index_pct")
        cfg = obj.get("config")
        if not isinstance(score, (int, float)):
            continue
        if not isinstance(cfg, dict):
            continue
        normalized = normalize_config(cfg)
        if normalized is None:
            continue
        history.append({"config": normalized, "score": float(score)})
    return history


def _iter_current_metric_results() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not RESULTS_PATH.exists():
        return out
    for line in RESULTS_PATH.read_text().splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("status") != "ok":
            continue
        metric = str(obj.get("objective_metric", "")).strip()
        if metric != CURRENT_OBJECTIVE_METRIC:
            continue
        out.append(obj)
    return out


def load_best_percent_over_index_record() -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_score: Optional[float] = None
    for obj in _iter_current_metric_results():
        score_obj = obj.get("legacy_outcome_score")
        if not isinstance(score_obj, (int, float)):
            continue
        cfg = obj.get("config")
        if not isinstance(cfg, dict):
            continue
        normalized = normalize_config(cfg)
        if normalized is None:
            continue
        score = float(score_obj)
        if (best_score is None) or (score > best_score):
            best_score = score
            best = {"score": score, "config": normalized, "run_name": obj.get("run_name")}
    return best


def load_unfavorable_configs(max_entries: int = NEG_FIELD_UNFAVORABLE_MAX) -> List[Dict[str, str]]:
    if not UNFAVORABLE_PATH.exists():
        return []
    lines = UNFAVORABLE_PATH.read_text().splitlines()
    if max_entries > 0 and len(lines) > max_entries:
        lines = lines[-max_entries:]
    out: List[Dict[str, str]] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            continue
        cfg = obj.get("config")
        if not isinstance(cfg, dict):
            continue
        normalized = normalize_config(cfg)
        if normalized is not None:
            out.append(normalized)
    return out


def build_value_score_table(history: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, float]], float]:
    sums: Dict[str, Dict[str, float]] = {}
    counts: Dict[str, Dict[str, int]] = {}
    global_sum = 0.0
    global_count = 0

    for row in history:
        cfg = row["config"]
        score = float(row["score"])
        global_sum += score
        global_count += 1
        for key, value in cfg.items():
            key_sums = sums.setdefault(key, {})
            key_counts = counts.setdefault(key, {})
            key_sums[value] = key_sums.get(value, 0.0) + score
            key_counts[value] = key_counts.get(value, 0) + 1

    means: Dict[str, Dict[str, float]] = {}
    for key, key_sums in sums.items():
        key_means: Dict[str, float] = {}
        for value, total in key_sums.items():
            count = counts[key][value]
            key_means[value] = total / float(max(1, count))
        means[key] = key_means

    global_mean = global_sum / float(max(1, global_count))
    return means, global_mean


def build_value_count_table(history: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    for row in history:
        cfg = row["config"]
        for key, value in cfg.items():
            key_counts = counts.setdefault(key, {})
            key_counts[value] = key_counts.get(value, 0) + 1
    return counts


def build_unfavorable_value_rates(unfavorable_cfgs: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    counts: Dict[str, Dict[str, int]] = {}
    for cfg in unfavorable_cfgs:
        for key, value in cfg.items():
            key_counts = counts.setdefault(key, {})
            key_counts[value] = key_counts.get(value, 0) + 1
    total = float(max(1, len(unfavorable_cfgs)))
    rates: Dict[str, Dict[str, float]] = {}
    for key, key_counts in counts.items():
        rates[key] = {value: (float(n) / total) for value, n in key_counts.items()}
    return rates


def estimate_config_score(cfg: Dict[str, str], value_means: Dict[str, Dict[str, float]], global_mean: float) -> float:
    total = 0.0
    used = 0
    for key in REQUIRED_CONFIG_KEYS:
        key_means = value_means.get(key, {})
        value = cfg[key]
        total += key_means.get(value, global_mean)
        used += 1
    if used <= 0:
        return global_mean
    return total / float(used)


def estimate_uncertainty_bonus(cfg: Dict[str, str], value_counts: Dict[str, Dict[str, int]]) -> float:
    s = 0.0
    for key in REQUIRED_CONFIG_KEYS:
        n = float(value_counts.get(key, {}).get(cfg[key], 0))
        s += 1.0 / math.sqrt(1.0 + n)
    return NEG_FIELD_UNCERTAINTY_BONUS * (s / float(len(REQUIRED_CONFIG_KEYS)))


def config_similarity(cfg_a: Dict[str, str], cfg_b: Dict[str, str]) -> float:
    matches = 0
    for key in REQUIRED_CONFIG_KEYS:
        if cfg_a.get(key) == cfg_b.get(key):
            matches += 1
    return float(matches) / float(len(REQUIRED_CONFIG_KEYS))


def estimate_negative_space(
    cfg: Dict[str, str],
    unfavorable_cfgs: List[Dict[str, str]],
    unfavorable_rates: Dict[str, Dict[str, float]],
) -> Tuple[float, float, float]:
    if not unfavorable_cfgs:
        return 0.0, 0.0, 0.0

    proximity_sum = 0.0
    for bad in unfavorable_cfgs:
        sim = config_similarity(cfg, bad)
        proximity_sum += sim * sim
    proximity = proximity_sum / float(len(unfavorable_cfgs))

    resonance = 0.0
    for key in REQUIRED_CONFIG_KEYS:
        resonance += unfavorable_rates.get(key, {}).get(cfg[key], 0.0)
    resonance = resonance / float(len(REQUIRED_CONFIG_KEYS))

    penalty = NEG_FIELD_PROXIMITY_WEIGHT * ((0.60 * proximity) + (0.40 * resonance))
    return penalty, proximity, resonance


def softmax_pick(
    scored_rows: List[Tuple[Dict[str, str], float, float, float, float, float, float]],
    temperature: float,
    rng: random.Random,
) -> Tuple[Dict[str, str], float, float, float, float, float, float, float]:
    if not scored_rows:
        raise ValueError("softmax_pick requires scored_rows")
    denom = max(0.05, float(temperature))
    max_u = max(row[6] for row in scored_rows)
    weights = [math.exp((row[6] - max_u) / denom) for row in scored_rows]
    total = sum(weights)
    if (not math.isfinite(total)) or total <= 0.0:
        best_row = max(scored_rows, key=lambda row: row[6])
        return best_row[0], best_row[1], best_row[2], best_row[3], best_row[4], best_row[5], best_row[6], 1.0

    threshold = rng.random() * total
    running = 0.0
    for row, weight in zip(scored_rows, weights):
        running += weight
        if running >= threshold:
            prob = weight / total
            return row[0], row[1], row[2], row[3], row[4], row[5], row[6], prob
    last_row = scored_rows[-1]
    last_prob = weights[-1] / total
    return last_row[0], last_row[1], last_row[2], last_row[3], last_row[4], last_row[5], last_row[6], last_prob


def compute_explore_rate(stale_runs: int) -> float:
    if stale_runs <= PLATEAU_REEXPLORE_AFTER:
        return ADAPTIVE_EXPLORE_RATE
    bonus = min(0.60, 0.03 * float(stale_runs - PLATEAU_REEXPLORE_AFTER))
    return min(PLATEAU_EXPLORE_MAX, ADAPTIVE_EXPLORE_RATE + bonus)


def init_ab_state() -> Dict[str, Dict[str, Any]]:
    return {
        AB_ARM_BASELINE: {
            "runs": 0,
            "ok_runs": 0,
            "sum_score": 0.0,
            "sum_sq_score": 0.0,
            "best_score": None,
            "above_reference_runs": 0,
        },
        AB_ARM_SOFT: {
            "runs": 0,
            "ok_runs": 0,
            "sum_score": 0.0,
            "sum_sq_score": 0.0,
            "best_score": None,
            "above_reference_runs": 0,
        },
    }


def load_ab_state() -> Dict[str, Dict[str, Any]]:
    if not AB_STATE_PATH.exists():
        return init_ab_state()
    try:
        payload = read_json(AB_STATE_PATH)
    except Exception:
        return init_ab_state()
    if not isinstance(payload, dict):
        return init_ab_state()

    if "arms" in payload:
        objective_metric = str(payload.get("objective_metric", "")).strip()
        if objective_metric != CURRENT_OBJECTIVE_METRIC:
            return init_ab_state()
        source = payload.get("arms")
        if not isinstance(source, dict):
            return init_ab_state()
    else:
        # Legacy AB state format is not metric-isolated; do not reuse it.
        return init_ab_state()

    baseline = source.get(AB_ARM_BASELINE)
    soft = source.get(AB_ARM_SOFT)
    if not isinstance(baseline, dict) or not isinstance(soft, dict):
        return init_ab_state()
    out = init_ab_state()
    for arm in (AB_ARM_BASELINE, AB_ARM_SOFT):
        src = source.get(arm, {})
        dst = out[arm]
        for key in ("runs", "ok_runs", "above_reference_runs"):
            v = src.get(key)
            if isinstance(v, int) and v >= 0:
                dst[key] = v
        for key in ("sum_score", "sum_sq_score"):
            v = src.get(key)
            if isinstance(v, (int, float)):
                dst[key] = float(v)
        v = src.get("best_score")
        if isinstance(v, (int, float)):
            dst["best_score"] = float(v)
    return out


def arm_avg_score(arm_state: Dict[str, Any]) -> Optional[float]:
    ok_runs = int(arm_state.get("ok_runs", 0))
    if ok_runs <= 0:
        return None
    return float(arm_state.get("sum_score", 0.0)) / float(ok_runs)


def choose_ab_arm(ab_state: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    baseline = ab_state[AB_ARM_BASELINE]
    soft = ab_state[AB_ARM_SOFT]
    b_runs = int(baseline.get("runs", 0))
    s_runs = int(soft.get("runs", 0))
    total = b_runs + s_runs

    if total < AB_WARMUP_RUNS:
        if b_runs < s_runs:
            return AB_ARM_BASELINE, "warmup_balance"
        if s_runs < b_runs:
            return AB_ARM_SOFT, "warmup_balance"
        return (AB_ARM_BASELINE if (total % 2 == 0) else AB_ARM_SOFT), "warmup_alternate"

    if b_runs < s_runs:
        return AB_ARM_BASELINE, "post_warmup_balance"
    if s_runs < b_runs:
        return AB_ARM_SOFT, "post_warmup_balance"

    b_avg = arm_avg_score(baseline)
    s_avg = arm_avg_score(soft)
    if b_avg is None and s_avg is None:
        return AB_ARM_BASELINE, "no_arm_history"
    if b_avg is None:
        return AB_ARM_SOFT, "soft_has_history"
    if s_avg is None:
        return AB_ARM_BASELINE, "baseline_has_history"
    if s_avg > b_avg:
        return AB_ARM_SOFT, "higher_empirical_mean"
    if b_avg > s_avg:
        return AB_ARM_BASELINE, "higher_empirical_mean"
    return AB_ARM_BASELINE, "equal_empirical_mean"


def update_ab_state(ab_state: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> None:
    selection = rec.get("selection")
    if not isinstance(selection, dict):
        return
    arm = selection.get("arm")
    if arm not in (AB_ARM_BASELINE, AB_ARM_SOFT):
        return
    arm_state = ab_state[arm]
    arm_state["runs"] = int(arm_state.get("runs", 0)) + 1

    score = rec.get("g32_symbol_avg_outcome_over_index_pct")
    status = rec.get("status")
    if status != "ok" or not isinstance(score, (int, float)):
        return
    score_f = float(score)
    arm_state["ok_runs"] = int(arm_state.get("ok_runs", 0)) + 1
    arm_state["sum_score"] = float(arm_state.get("sum_score", 0.0)) + score_f
    arm_state["sum_sq_score"] = float(arm_state.get("sum_sq_score", 0.0)) + (score_f * score_f)
    if score_f > BASELINE_REFERENCE:
        arm_state["above_reference_runs"] = int(arm_state.get("above_reference_runs", 0)) + 1
    current_best = arm_state.get("best_score")
    if (current_best is None) or (score_f > float(current_best)):
        arm_state["best_score"] = score_f


def write_ab_artifacts(
    ab_state: Dict[str, Dict[str, Any]],
    run_id: int,
    history_size: int,
    stale_runs: int,
) -> None:
    write_json(
        AB_STATE_PATH,
        {
            "objective_metric": CURRENT_OBJECTIVE_METRIC,
            "updated_at_utc": utc_now(),
            "arms": ab_state,
        },
    )

    summary_arms: Dict[str, Dict[str, Any]] = {}
    for arm_name in (AB_ARM_BASELINE, AB_ARM_SOFT):
        arm_state = ab_state[arm_name]
        runs = int(arm_state.get("runs", 0))
        ok_runs = int(arm_state.get("ok_runs", 0))
        sum_score = float(arm_state.get("sum_score", 0.0))
        sum_sq_score = float(arm_state.get("sum_sq_score", 0.0))
        avg = (sum_score / float(ok_runs)) if ok_runs > 0 else None
        var = (sum_sq_score / float(ok_runs) - (avg * avg)) if (ok_runs > 0 and avg is not None) else None
        std = math.sqrt(max(0.0, var)) if isinstance(var, (int, float)) else None
        above_reference = int(arm_state.get("above_reference_runs", 0))
        summary_arms[arm_name] = {
            "runs": runs,
            "ok_runs": ok_runs,
            "avg_score": avg,
            "std_score": std,
            "best_score": arm_state.get("best_score"),
            "above_reference_pct": (100.0 * above_reference / float(ok_runs)) if ok_runs > 0 else None,
        }

    b_avg = summary_arms[AB_ARM_BASELINE]["avg_score"]
    s_avg = summary_arms[AB_ARM_SOFT]["avg_score"]
    winner = None
    if isinstance(b_avg, (int, float)) and isinstance(s_avg, (int, float)):
        if s_avg > b_avg:
            winner = AB_ARM_SOFT
        elif b_avg > s_avg:
            winner = AB_ARM_BASELINE
        else:
            winner = "tie"

    payload = {
        "updated_at_utc": utc_now(),
        "run_id": run_id,
        "history_size": history_size,
        "stale_runs": stale_runs,
        "arms": summary_arms,
        "current_winner_by_avg": winner,
    }
    write_json(AB_SUMMARY_PATH, payload)


def select_next_config(
    pool: List[Dict[str, str]],
    seen: set[str],
    history: List[Dict[str, Any]],
    stale_runs: int,
    ab_state: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[Dict[str, str]], Dict[str, Any]]:
    remaining = sorted((cfg for cfg in pool if config_signature(cfg) not in seen), key=config_signature)
    if not remaining:
        return None, {"mode": "depleted", "remaining": 0}

    history_size = len(history)
    if history_size < ADAPTIVE_MIN_HISTORY:
        cfg = remaining[0]
        return cfg, {
            "mode": "cold_start_deterministic",
            "arm": "deterministic",
            "remaining": len(remaining),
            "history_size": history_size,
            "stale_runs": stale_runs,
        }

    value_means, global_mean = build_value_score_table(history)
    value_counts = build_value_count_table(history)
    sample_count = len(remaining)
    candidates = remaining

    arm, arm_reason = choose_ab_arm(ab_state=ab_state)

    if arm == AB_ARM_BASELINE:
        best_cfg: Optional[Dict[str, str]] = None
        best_est = float("-inf")
        best_sig = ""
        for cfg in candidates:
            est = estimate_config_score(cfg, value_means=value_means, global_mean=global_mean)
            sig = config_signature(cfg)
            if (est > best_est) or (est == best_est and (not best_sig or sig < best_sig)):
                best_est = est
                best_cfg = cfg
                best_sig = sig
        if best_cfg is None:
            return None, {"mode": "depleted", "remaining": 0}
        return best_cfg, {
            "mode": "pfsc_deterministic_baseline",
            "arm": AB_ARM_BASELINE,
            "ab_reason": arm_reason,
            "remaining": len(remaining),
            "history_size": history_size,
            "stale_runs": stale_runs,
            "estimated_score": round(best_est, 6),
            "candidate_sample_count": int(sample_count),
        }

    unfavorable_cfgs = load_unfavorable_configs(max_entries=NEG_FIELD_UNFAVORABLE_MAX)
    unfavorable_rates = build_unfavorable_value_rates(unfavorable_cfgs)
    temperature = min(
        1.35,
        NEG_FIELD_TEMPERATURE_BASE + (NEG_FIELD_TEMPERATURE_STEP * float(max(0, stale_runs - PLATEAU_REEXPLORE_AFTER))),
    )

    scored_rows: List[Tuple[Dict[str, str], float, float, float, float, float, float]] = []
    for cfg in candidates:
        est = estimate_config_score(cfg, value_means=value_means, global_mean=global_mean)
        uncertainty_bonus = estimate_uncertainty_bonus(cfg, value_counts=value_counts)
        penalty, proximity, resonance = estimate_negative_space(
            cfg,
            unfavorable_cfgs=unfavorable_cfgs,
            unfavorable_rates=unfavorable_rates,
        )
        utility = est + uncertainty_bonus - penalty
        scored_rows.append((cfg, est, uncertainty_bonus, penalty, proximity, resonance, utility))

    if not scored_rows:
        return None, {"mode": "depleted", "remaining": 0}

    best_row: Optional[Tuple[Dict[str, str], float, float, float, float, float, float]] = None
    best_sig = ""
    for row in scored_rows:
        sig = config_signature(row[0])
        if best_row is None:
            best_row = row
            best_sig = sig
            continue
        if (row[6] > best_row[6]) or (row[6] == best_row[6] and row[1] > best_row[1]) or (
            row[6] == best_row[6] and row[1] == best_row[1] and sig < best_sig
        ):
            best_row = row
            best_sig = sig
    if best_row is None:
        return None, {"mode": "depleted", "remaining": 0}
    cfg, est, uncertainty_bonus, penalty, proximity, resonance, utility = best_row
    return cfg, {
        "mode": "pfsc_deterministic_negative_space",
        "arm": AB_ARM_SOFT,
        "ab_reason": arm_reason,
        "remaining": len(remaining),
        "history_size": history_size,
        "stale_runs": stale_runs,
        "temperature": round(temperature, 6),
        "estimated_score": round(est, 6),
        "uncertainty_bonus": round(uncertainty_bonus, 6),
        "negative_space_penalty": round(penalty, 6),
        "negative_space_proximity": round(proximity, 6),
        "negative_space_resonance": round(resonance, 6),
        "selection_probability": 1.0,
        "utility": round(utility, 6),
        "candidate_sample_count": int(sample_count),
        "unfavorable_profile_size": len(unfavorable_cfgs),
    }


def load_best_config() -> Optional[Dict[str, str]]:
    best_record = load_best_percent_over_index_record()
    if isinstance(best_record, dict):
        cfg = best_record.get("config")
        if isinstance(cfg, dict):
            normalized = normalize_config(cfg)
            if normalized is not None:
                return normalized

    if not BEST_PATH.exists():
        return None
    try:
        best = read_json(BEST_PATH)
    except Exception:
        return None
    if not isinstance(best, dict):
        return None
    cfg = best.get("best_config")
    if not isinstance(cfg, dict):
        return None
    return normalize_config(cfg)


def load_current_best_score() -> Optional[float]:
    best_record = load_best_percent_over_index_record()
    if isinstance(best_record, dict):
        value = best_record.get("score")
        if isinstance(value, (int, float)):
            return float(value)

    if not BEST_PATH.exists():
        return None
    try:
        best = read_json(BEST_PATH)
    except Exception:
        return None
    if not isinstance(best, dict):
        return None
    objective_metric = str(best.get("objective_metric", "")).strip()
    if objective_metric != CURRENT_OBJECTIVE_METRIC:
        return None
    value = best.get("best_percent_over_index")
    if isinstance(value, (int, float)):
        return float(value)
    value = best.get("best_legacy_outcome_score")
    if isinstance(value, (int, float)):
        return float(value)
    value = best.get("best_objective_score")
    if isinstance(value, (int, float)):
        return float(value)
    fallback = best.get("best_g32_symbol_avg_outcome_over_index_pct")
    if isinstance(fallback, (int, float)):
        return float(fallback)
    return None


def init_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            obj = read_json(STATE_PATH)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {"run_id": 0, "updated_at_utc": utc_now()}


def maybe_update_best(record: Dict[str, Any]) -> bool:
    current: Optional[float] = load_current_best_score()
    candidate = record.get("legacy_outcome_score")
    if not isinstance(candidate, (int, float)):
        candidate = record.get("g32_symbol_avg_outcome_over_index_pct")
    if not isinstance(candidate, (int, float)):
        return False
    cand_v = float(candidate)

    if (current is None) or (cand_v > current):
        learner_obj = record.get("g32_symbol_avg_outcome_over_index_pct")
        learner_v = float(learner_obj) if isinstance(learner_obj, (int, float)) else None
        payload = {
            "best_percent_over_index": cand_v,
            "best_legacy_outcome_score": cand_v,
            "best_learner_metric_score": learner_v,
            "best_g32_symbol_avg_outcome_over_index_pct": learner_v,
            "best_objective_score": learner_v,
            "best_delta_vs_reference": record.get("delta_vs_reference"),
            "best_run_name": record.get("run_name"),
            "best_report_path": record.get("report_path"),
            "objective_metric": record.get("objective_metric"),
            "best_config": record.get("config"),
            "best_fingerprint": record.get("fingerprint"),
            "updated_at_utc": utc_now(),
        }
        write_json(BEST_PATH, payload)
        log(f"new_best_insanity run={record.get('run_name')} pct_over_index={cand_v}")
        return True
    return False


def maybe_log_unfavorable(record: Dict[str, Any], current_best: Optional[float]) -> None:
    reasons: List[str] = []
    status = str(record.get("status"))
    score_obj = record.get("legacy_outcome_score")
    if not isinstance(score_obj, (int, float)):
        score_obj = record.get("g32_symbol_avg_outcome_over_index_pct")
    score: Optional[float] = None

    if status != "ok":
        reasons.append(f"status_{status}")

    if isinstance(score_obj, (int, float)):
        score = float(score_obj)
        if score < BASELINE_REFERENCE:
            reasons.append("below_reference")
        if (current_best is not None) and (score < (current_best - 5.0)):
            reasons.append("below_current_best_minus_5")
    else:
        reasons.append("missing_score")

    if not reasons:
        return

    append_jsonl(
        UNFAVORABLE_PATH,
        {
            "run_id": record.get("run_id"),
            "run_name": record.get("run_name"),
            "status": status,
            "score": score,
            "delta_vs_reference": record.get("delta_vs_reference"),
            "reasons": reasons,
            "config": record.get("config"),
            "report_path": record.get("report_path"),
            "selection": record.get("selection"),
            "logged_at_utc": utc_now(),
        },
    )


def run_one(run_id: int, cfg: Dict[str, str], fingerprint: Dict[str, Any]) -> Dict[str, Any]:
    run_name = f"insanity_{run_id:04d}_{stamp()}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    log_path = run_dir / "run.log"

    cmd = [
        sys.executable,
        str(RUNNER),
        "--row-trace",
        str(ROW_TRACE),
        "--dataset",
        str(DATASET),
        "--output",
        str(report_path),
        "--min-samples-grid",
        cfg["min_samples_grid"],
        "--min-suf-grid",
        cfg["min_suf_grid"],
        "--include-irf-modes",
        cfg["include_irf_modes"],
        "--train-fracs",
        cfg["train_fracs"],
        "--test-frac",
        cfg["test_frac"],
        "--min-edge-grid",
        cfg["min_edge_grid"],
        "--min-winrate-grid",
        cfg["min_winrate_grid"],
        "--uncertainty-penalty-grid",
        cfg["uncertainty_penalty_grid"],
        "--hold-bias-grid",
        cfg["hold_bias_grid"],
    ]

    started = time.time()
    status = "ok"
    error: Optional[str] = None

    with log_path.open("w", encoding="utf-8") as out:
        try:
            proc = subprocess.run(
                cmd,
                cwd=WORKSPACE,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
            if proc.returncode != 0:
                status = f"exit_{proc.returncode}"
        except subprocess.TimeoutExpired:
            status = "timeout"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = f"{type(exc).__name__}: {exc}"

    elapsed = round(time.time() - started, 2)
    g32_score = None
    legacy_score = None
    objective_metric = None
    delta = None
    if status == "ok" and report_path.exists():
        try:
            report = read_json(report_path)
            horse = report.get("horse_race", {})
            objective_metric = horse.get("objective_metric")
            v = horse.get("g32_best_symbol_return_multiple_over_spy_pct")
            legacy_v = horse.get("g32_best_symbol_avg_outcome_over_index_pct")
            d = horse.get("delta_vs_reference")
            if isinstance(v, (int, float)):
                g32_score = float(v)
            elif isinstance(legacy_v, (int, float)):
                g32_score = float(legacy_v)
            if isinstance(legacy_v, (int, float)):
                legacy_score = float(legacy_v)
            if isinstance(d, (int, float)):
                delta = float(d)
        except Exception as exc:  # noqa: BLE001
            status = "bad_report"
            error = f"{type(exc).__name__}: {exc}"

    return {
        "run_id": run_id,
        "run_name": run_name,
        "status": status,
        "error": error,
        "elapsed_seconds": elapsed,
        "config": cfg,
        "fingerprint": fingerprint,
        "report_path": str(report_path) if report_path.exists() else None,
        "g32_symbol_avg_outcome_over_index_pct": g32_score,
        "legacy_outcome_score": legacy_score,
        "objective_metric": objective_metric,
        "delta_vs_reference": delta,
        "finished_at_utc": utc_now(),
    }


def execute_run(
    run_id: int,
    cfg: Dict[str, str],
    fingerprint: Dict[str, Any],
    seen: set[str],
    selection: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool]:
    write_json(
        STATE_PATH,
        {
            "run_id": run_id,
            "phase": "running",
            "current_config": cfg,
            "selection": selection,
            "fingerprint": fingerprint,
            "updated_at_utc": utc_now(),
        },
    )

    log(f"start run_id={run_id} cfg={cfg}")
    rec = run_one(run_id=run_id, cfg=cfg, fingerprint=fingerprint)
    rec["selection"] = selection
    append_jsonl(RESULTS_PATH, rec)
    seen.add(config_signature(cfg))

    improved = maybe_update_best(rec)
    current_best = load_current_best_score()
    maybe_log_unfavorable(rec, current_best=current_best)

    log(
        "done "
        f"run_id={run_id} status={rec['status']} "
        f"pct_over_index={rec.get('legacy_outcome_score')} "
        f"learner={rec.get('g32_symbol_avg_outcome_over_index_pct')} "
        f"delta={rec.get('delta_vs_reference')} "
        f"elapsed={rec.get('elapsed_seconds')}s "
        f"improved={improved}"
    )

    state = {
        "run_id": run_id,
        "phase": "idle",
        "fingerprint": fingerprint,
        "updated_at_utc": utc_now(),
    }
    write_json(STATE_PATH, state)
    return rec, improved


def maybe_record_history(history: List[Dict[str, Any]], rec: Dict[str, Any]) -> None:
    if rec.get("status") != "ok":
        return
    score = rec.get("legacy_outcome_score")
    if not isinstance(score, (int, float)):
        score = rec.get("g32_symbol_avg_outcome_over_index_pct")
    cfg = rec.get("config")
    if not isinstance(score, (int, float)):
        return
    if not isinstance(cfg, dict):
        return
    normalized = normalize_config(cfg)
    if normalized is None:
        return
    history.append({"config": normalized, "score": float(score)})


def main() -> None:
    if not RUNNER.exists():
        raise FileNotFoundError(f"Missing runner: {RUNNER}")
    if not ROW_TRACE.exists():
        raise FileNotFoundError(f"Missing row trace: {ROW_TRACE}")
    if not DATASET.exists():
        raise FileNotFoundError(f"Missing dataset: {DATASET}")

    if not acquire_lock():
        return

    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        pool = build_pool()
        pool = sorted(pool, key=config_signature)

        fingerprint = build_fingerprint()
        runner_sha = str(fingerprint.get("runner", {}).get("sha256", ""))[:12]
        loop_sha = str(fingerprint.get("loop_runner", {}).get("sha256", ""))[:12]
        log(f"fingerprint runner_sha={runner_sha} loop_sha={loop_sha}")

        state = init_state()
        run_id = int(state.get("run_id", 0))
        seen = load_seen()
        history = load_scored_history()
        stale_runs = 0
        ab_state = load_ab_state()
        write_ab_artifacts(ab_state=ab_state, run_id=run_id, history_size=len(history), stale_runs=stale_runs)

        log(
            "loop_start insanity "
            f"pool={len(pool)} seen={len(seen)} history={len(history)} "
            f"target_avg_outcome={TARGET_AVG_OUTCOME} "
            f"start_best_percent_over_index={load_current_best_score()}"
        )

        champion_cfg = load_best_config()
        if champion_cfg is not None:
            run_id += 1
            kickoff_selection = {
                "mode": "champion_kickoff",
                "arm": "champion_kickoff",
                "history_size": len(history),
                "remaining": None,
            }
            log(f"champion_kickoff run_id={run_id} cfg={champion_cfg}")
            rec, improved = execute_run(
                run_id=run_id,
                cfg=champion_cfg,
                fingerprint=fingerprint,
                seen=seen,
                selection=kickoff_selection,
            )
            update_ab_state(ab_state, rec)
            maybe_record_history(history, rec)
            stale_runs = 0 if improved else stale_runs + 1
            write_ab_artifacts(ab_state=ab_state, run_id=run_id, history_size=len(history), stale_runs=stale_runs)
            v = rec.get("legacy_outcome_score")
            if not isinstance(v, (int, float)):
                v = rec.get("g32_symbol_avg_outcome_over_index_pct")
            if isinstance(v, (int, float)) and float(v) >= TARGET_AVG_OUTCOME:
                log(f"target_reached run_id={run_id} avg_out={v}")
                log("loop_complete")
                return
        else:
            log("champion_kickoff skipped reason=no_best_config")

        while True:
            if stop_requested():
                log("stop_requested")
                break

            cfg, selection = select_next_config(
                pool=pool,
                seen=seen,
                history=history,
                stale_runs=stale_runs,
                ab_state=ab_state,
            )
            if cfg is None:
                log("pool_depleted")
                break

            run_id += 1
            log(f"adaptive_choice run_id={run_id} selection={selection}")
            rec, improved = execute_run(
                run_id=run_id,
                cfg=cfg,
                fingerprint=fingerprint,
                seen=seen,
                selection=selection,
            )
            update_ab_state(ab_state, rec)
            maybe_record_history(history, rec)
            stale_runs = 0 if improved else stale_runs + 1
            write_ab_artifacts(ab_state=ab_state, run_id=run_id, history_size=len(history), stale_runs=stale_runs)

            v = rec.get("legacy_outcome_score")
            if not isinstance(v, (int, float)):
                v = rec.get("g32_symbol_avg_outcome_over_index_pct")
            if isinstance(v, (int, float)) and float(v) >= TARGET_AVG_OUTCOME:
                log(f"target_reached run_id={run_id} avg_out={v}")
                break

        log("loop_complete")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
