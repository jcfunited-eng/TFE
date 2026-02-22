#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

LOOPS = [
    {
        "name": "l5_legacy",
        "root": Path("/tmp/l5_opt_loop"),
        "best_key": "best_avg_outcome_over_index_pct_anomaly_accounted",
        "last_score_key": "avg_outcome_over_index_pct_anomaly_accounted",
    },
    {
        "name": "g32_legacy",
        "root": Path("/tmp/g32_horse_race_loop"),
        "best_key": "best_g32_symbol_avg_outcome_over_index_pct",
        "last_score_key": "g32_symbol_avg_outcome_over_index_pct",
    },
    {
        "name": "g32_thoroughbred",
        "root": Path("/tmp/g32_thoroughbred_loop"),
        "best_key": "best_g32_symbol_avg_outcome_over_index_pct",
        "last_score_key": "g32_symbol_avg_outcome_over_index_pct",
    },
    {
        "name": "g32_insanity",
        "root": Path("/tmp/g32_insanity_loop"),
        "best_key": "best_g32_symbol_avg_outcome_over_index_pct",
        "last_score_key": "g32_symbol_avg_outcome_over_index_pct",
    },
]


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _tail_jsonl(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    last = ""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    if not last:
        return None
    try:
        payload = json.loads(last)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_run_id(name: Optional[str], fallback: Optional[Any]) -> Optional[int]:
    if isinstance(fallback, int) and fallback > 0:
        return int(fallback)
    if not isinstance(name, str):
        return None
    m = re.search(r"(?:run_|g32_run_|thoroughbred_|insanity_)(\d+)_", name)
    if m is None:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _loop_status(spec: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(spec["root"])
    name = str(spec["name"])
    best_key = str(spec["best_key"])
    last_score_key = str(spec["last_score_key"])

    state = _read_json(root / "state.json") or {}
    best = _read_json(root / "best_summary.json") or {}
    results = root / "results.jsonl"
    latest = _tail_jsonl(results) or {}

    run_id = int(state.get("run_id", 0))
    completed = _line_count(results)
    best_score = best.get(best_key)
    best_run_name = best.get("best_run_name")
    best_run_id = _extract_run_id(best_run_name, best.get("best_run_id"))
    runs_since_best = (run_id - best_run_id) if best_run_id is not None else run_id

    return {
        "loop": name,
        "present": root.exists(),
        "current_iteration": run_id,
        "completed_iterations": completed,
        "best_score": best_score,
        "best_run_id": best_run_id,
        "best_run_name": best_run_name,
        "runs_since_best": runs_since_best,
        "last_run_name": latest.get("run_name"),
        "last_run_score": latest.get(last_score_key),
        "last_run_status": latest.get("status"),
        "updated_at_utc": state.get("updated_at_utc"),
    }


def _leaderboard(loop_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked: List[Dict[str, Any]] = []
    for row in loop_rows:
        s = row.get("best_score")
        if isinstance(s, (int, float)):
            ranked.append({"loop": row.get("loop"), "best_score": float(s)})
    ranked.sort(key=lambda x: x["best_score"], reverse=True)
    if len(ranked) == 0:
        return {"leader": None, "delta_to_second": None, "ranking": []}
    if len(ranked) == 1:
        return {"leader": ranked[0]["loop"], "delta_to_second": None, "ranking": ranked}
    return {
        "leader": ranked[0]["loop"],
        "delta_to_second": float(ranked[0]["best_score"] - ranked[1]["best_score"]),
        "ranking": ranked,
    }


def main() -> None:
    loops = [_loop_status(spec) for spec in LOOPS]
    payload = {
        "loops": loops,
        "leaderboard": _leaderboard(loops),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
