#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/workspaces/Tao_Financial_Engine")
DATASET_PATH = ROOT / "backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_latest.csv"
SPY_PATH = ROOT / "backups/strict-ab-frozen-dataset-20260306T180841Z.json"
OUT_DIR = ROOT / "backups/runtime"
DECISIONS = ("Accumulate", "Hold", "Avoid")
FIELD_NAMES = ("D_cur", "M_cur", "R_rev_cur", "U_star_cur", "C_cur", "P_cur", "B_cur", "S_UF_cur", "R_UF_cur")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline answer-conditioned DSF structure extractor from temporal dataset truth."
    )
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--spy-dataset", default=str(SPY_PATH))
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=250000)
    parser.add_argument(
        "--ambiguity-quantile",
        type=float,
        default=0.10,
        help="Rows with top-vs-second-best oracle margin at or below this quantile are labeled Hold.",
    )
    return parser.parse_args()


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(raw: Any, default: float = 0.0) -> float:
    try:
        out = float(raw)
        if out != out or out in (float("inf"), float("-inf")):
            return float(default)
        return out
    except Exception:
        return float(default)


def parse_iso_ms(raw: str) -> int | None:
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


def append_field(store: dict[str, list[float]], fields: dict[str, float]) -> None:
    for field_name in FIELD_NAMES:
        store[field_name].append(fields[field_name])


def summarize_field_store(store: dict[str, list[float]]) -> dict[str, float | None]:
    return {field_name: median(values) for field_name, values in store.items()}


def iter_rows(dataset_path: Path, max_rows: int):
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            if max_rows > 0 and idx > max_rows:
                break
            yield idx, row


def compute_oracle_scores(
    row: dict[str, Any],
    spy_ts: list[int],
    spy_close: list[float],
) -> tuple[str, float, float, str, dict[str, float]] | None:
    ts_ms = parse_iso_ms(str(row.get("decision_timestamp", "")))
    if ts_ms is None:
        return None

    horizon = int(round(to_float(row.get("horizon"), 0)))
    if horizon <= 0:
        return None

    forward_return = to_float(row.get("forward_return"), 0.0)
    bench_return = spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
    if bench_return is None:
        return None

    fields = {field_name: to_float(row.get(field_name), 0.0) for field_name in FIELD_NAMES}
    regime = str(row.get("regime", "UNKNOWN"))

    excess_by_action = {
        decision: decision_return(decision, forward_return) - bench_return for decision in DECISIONS
    }
    ranked = sorted(excess_by_action.items(), key=lambda item: (item[1], item[0]), reverse=True)
    top_decision = ranked[0][0]
    top_margin = float(ranked[0][1] - ranked[1][1])
    top_excess = float(ranked[0][1])
    return top_decision, top_margin, top_excess, regime, fields


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset)
    spy_path = Path(args.spy_dataset)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    spy_payload = json.loads(spy_path.read_text(encoding="utf-8"))
    spy_ts = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close = [float(x) for x in spy_payload["spy"]["close"]]

    positive_active_margins: list[float] = []
    first_pass_scanned = 0
    first_pass_used = 0

    for row_idx, row in iter_rows(dataset_path, args.max_rows):
        first_pass_scanned = row_idx
        computed = compute_oracle_scores(row, spy_ts, spy_close)
        if computed is None:
            continue
        top_decision, top_margin, top_excess, _regime, _fields = computed
        first_pass_used += 1

        if args.progress_every > 0 and row_idx % args.progress_every == 0:
            print(
                json.dumps(
                    {
                        "phase": "first_pass",
                        "rows_scanned": row_idx,
                        "rows_used": first_pass_used,
                    }
                ),
                flush=True,
            )

        if top_decision != "Hold" and top_excess > 0.0:
            positive_active_margins.append(top_margin)

    ambiguity_margin_threshold = quantile(positive_active_margins, args.ambiguity_quantile)
    if ambiguity_margin_threshold is None:
        raise RuntimeError("No usable positive active oracle margins found.")

    outcome_counts = Counter()
    realized_decision_counts = Counter()
    regime_outcome_counts: dict[str, Counter[str]] = defaultdict(Counter)
    signature_counts: dict[str, Counter[str]] = defaultdict(Counter)
    field_values: dict[str, dict[str, list[float]]] = {
        decision: {field_name: [] for field_name in FIELD_NAMES} for decision in DECISIONS
    }
    margin_values: dict[str, list[float]] = {decision: [] for decision in DECISIONS}

    second_pass_scanned = 0
    second_pass_used = 0

    for row_idx, row in iter_rows(dataset_path, args.max_rows):
        second_pass_scanned = row_idx
        computed = compute_oracle_scores(row, spy_ts, spy_close)
        if computed is None:
            continue
        top_decision, top_margin, _top_excess, regime, fields = computed
        second_pass_used += 1

        if args.progress_every > 0 and row_idx % args.progress_every == 0:
            print(
                json.dumps(
                    {
                        "phase": "second_pass",
                        "rows_scanned": row_idx,
                        "rows_used": second_pass_used,
                        "oracle_outcome_counts": dict(outcome_counts),
                    }
                ),
                flush=True,
            )

        if top_decision == "Hold" or top_margin <= ambiguity_margin_threshold:
            oracle_decision = "Hold"
        else:
            oracle_decision = top_decision

        outcome_counts[oracle_decision] += 1
        realized_decision_counts[str(row.get("decision", "UNKNOWN"))] += 1
        regime_outcome_counts[regime][oracle_decision] += 1
        signature_counts[oracle_decision][build_signature(regime, fields)] += 1
        append_field(field_values[oracle_decision], fields)
        margin_values[oracle_decision].append(top_margin)

    top_signatures = {
        decision: [
            {"signature": signature, "count": count}
            for signature, count in signature_counts[decision].most_common(12)
        ]
        for decision in DECISIONS
    }

    field_medians = {decision: summarize_field_store(field_values[decision]) for decision in DECISIONS}
    median_margins = {decision: median(values) for decision, values in margin_values.items()}

    report = {
        "generated_at_utc": utc_iso(),
        "method": {
            "type": "offline_answer_conditioned_structure_extract",
            "note": "Ex post oracle class uses realized excess return versus SPY, but rows with low top-vs-second-best margin are reassigned to Hold as ambiguity structure. This is not runtime architecture.",
            "dataset_path": str(dataset_path),
            "spy_dataset_path": str(spy_path),
            "max_rows": args.max_rows,
            "ambiguity_quantile": args.ambiguity_quantile,
            "ambiguity_margin_threshold": ambiguity_margin_threshold,
        },
        "first_pass_rows_scanned": first_pass_scanned,
        "first_pass_rows_used": first_pass_used,
        "second_pass_rows_scanned": second_pass_scanned,
        "second_pass_rows_used": second_pass_used,
        "oracle_outcome_counts": dict(outcome_counts),
        "realized_decision_counts": dict(realized_decision_counts),
        "median_oracle_margin_vs_second_best": median_margins,
        "regime_oracle_outcome_counts": {regime: dict(counter) for regime, counter in regime_outcome_counts.items()},
        "field_medians_by_oracle_outcome": field_medians,
        "top_signatures_by_oracle_outcome": top_signatures,
    }

    out_path = OUT_DIR / f"uf_dynamic_decision_answer_conditioned_structure_extract_{utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(out_path), "oracle_outcome_counts": dict(outcome_counts)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
