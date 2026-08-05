#!/usr/bin/env python3
from __future__ import annotations

import bisect
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/workspaces/Tao_Financial_Engine")
DATASET_PATH = ROOT / "backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_latest.csv"
SPY_PATH = ROOT / "backups/strict-ab-frozen-dataset-20260306T180841Z.json"
OUT_DIR = ROOT / "backups/runtime"
MAX_ROWS = 1_000_000
DECISIONS = ("Accumulate", "Hold", "Avoid")
FIELD_NAMES = ("D_cur", "M_cur", "R_rev_cur", "U_star_cur", "C_cur", "P_cur", "B_cur", "S_UF_cur", "R_UF_cur")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(raw: object, default: float = 0.0) -> float:
    try:
        out = float(raw)
        if out != out or out in (float("inf"), float("-inf")):
            return float(default)
        return out
    except Exception:
        return float(default)


def parse_iso_ms(raw: object) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(round(dt.timestamp() * 1000.0))


def spy_forward_return(spy_ts: list[int], spy_close: list[float], entry_ts: int, horizon: int) -> float | None:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None
    j = idx + int(horizon)
    if j >= len(spy_close):
        return None
    c0 = float(spy_close[idx])
    c1 = float(spy_close[j])
    if c0 <= 0.0:
        return None
    return float(c1 / c0 - 1.0)


def decision_return(decision: str, forward_return: float) -> float:
    if decision == "Accumulate":
        return float(forward_return)
    if decision == "Avoid":
        return float(-forward_return)
    return 0.0


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2.0)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def sign3(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def u_bucket(u_star: float) -> str:
    if u_star < 0.33:
        return "U0"
    if u_star < 0.66:
        return "U1"
    return "U2"


def p_bucket(p_val: float) -> str:
    p = int(round(p_val))
    if p <= 0:
        return "P0"
    if p == 1:
        return "P1"
    return "P2"


def build_signature(regime: str, fields: dict[str, float]) -> str:
    return (
        f"reg={regime}"
        f"|D={int(round(fields['D_cur']))}"
        f"|M={sign3(fields['M_cur'])}"
        f"|Rrev={1 if fields['R_rev_cur'] > 0.5 else 0}"
        f"|{u_bucket(fields['U_star_cur'])}"
        f"|{p_bucket(fields['P_cur'])}"
        f"|B={sign3(fields['B_cur'])}"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    spy_payload = json.loads(SPY_PATH.read_text(encoding="utf-8"))
    spy_ts = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close = [float(x) for x in spy_payload["spy"]["close"]]

    accumulate_rows: list[dict[str, object]] = []

    with DATASET_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            if idx > MAX_ROWS:
                break

            ts_ms = parse_iso_ms(row.get("decision_timestamp", ""))
            if ts_ms is None:
                continue

            horizon = int(round(to_float(row.get("horizon"), 0)))
            if horizon <= 0:
                continue

            forward_return = to_float(row.get("forward_return"), 0.0)
            bench_return = spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_return is None:
                continue

            excess_by_action = {
                decision: decision_return(decision, forward_return) - bench_return
                for decision in DECISIONS
            }
            ranked = sorted(excess_by_action.items(), key=lambda item: (item[1], item[0]), reverse=True)
            top_decision, top_excess = ranked[0]
            top_margin = float(ranked[0][1] - ranked[1][1])

            if top_decision != "Accumulate" or top_excess <= 0.0:
                continue

            fields = {field_name: to_float(row.get(field_name), 0.0) for field_name in FIELD_NAMES}
            regime = str(row.get("regime", "UNKNOWN"))
            accumulate_rows.append(
                {
                    "margin": top_margin,
                    "regime": regime,
                    "fields": fields,
                    "signature": build_signature(regime, fields),
                }
            )

    margins = [float(row["margin"]) for row in accumulate_rows]
    strict_margin_threshold = quantile(margins, 0.75)
    if strict_margin_threshold is None:
        raise RuntimeError("No accumulate rows found for strict subset.")

    strict_subset = [row for row in accumulate_rows if float(row["margin"]) >= strict_margin_threshold]

    field_medians = {
        field_name: median([float(row["fields"][field_name]) for row in strict_subset])
        for field_name in FIELD_NAMES
    }

    signature_counts = Counter(str(row["signature"]) for row in strict_subset)
    regime_counts = Counter(str(row["regime"]) for row in strict_subset)

    report = {
        "generated_at_utc": utc_iso(),
        "method": {
            "type": "answer_conditioned_accumulate_strict_subset",
            "note": "Tighter Accumulate subset from the same bounded 1,000,000-row temporal pass. Keeps only ex post Accumulate rows with positive excess-vs-SPY and oracle margin at or above the Accumulate class 75th percentile. This is not runtime architecture.",
            "dataset_path": str(DATASET_PATH),
            "spy_dataset_path": str(SPY_PATH),
            "max_rows": MAX_ROWS,
            "strict_margin_quantile_within_accumulate": 0.75,
            "strict_margin_threshold": strict_margin_threshold,
        },
        "source_accumulate_row_count": len(accumulate_rows),
        "strict_subset_count": len(strict_subset),
        "strict_subset_median_margin": median([float(row["margin"]) for row in strict_subset]),
        "field_medians": field_medians,
        "regime_counts": dict(regime_counts),
        "top_signatures": [
            {"signature": signature, "count": count}
            for signature, count in signature_counts.most_common(12)
        ],
    }

    out_path = OUT_DIR / f"uf_dynamic_decision_answer_conditioned_accumulate_strict_subset_{utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(out_path),
                "strict_margin_threshold": strict_margin_threshold,
                "strict_subset_count": len(strict_subset),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
