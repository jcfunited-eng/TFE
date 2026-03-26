#!/usr/bin/env python3
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

GATE_COUNTS = defaultdict(int)
DEFAULT_INPUT = Path("real_world_cleaned_universe_l5_row_trace_full.csv")


def _to_num(value):
    try:
        parsed = float(value)
        return 0.0 if math.isnan(parsed) or math.isinf(parsed) else parsed
    except Exception:
        return 0.0


def evaluate_l5_primitive(row, memory_buffer):
    GATE_COUNTS["TOTAL_ROWS"] += 1

    s_uf = _to_num(row.get("S_UF", 0))
    r_rev_k = _to_num(row.get("R_rev", row.get("R_rev_k", 0)))
    d_k = _to_num(row.get("D", row.get("D_k", 0)))
    r_uf = _to_num(row.get("R_UF", 0))
    p_k = _to_num(row.get("P", row.get("P_k", 0)))
    b_k = _to_num(row.get("B", row.get("B_k", 0)))
    m_k = _to_num(row.get("M", row.get("M_k", 0)))
    u_star = _to_num(row.get("U_star", row.get("U_star_k", 0)))
    forward_return = _to_num(row.get("forward_return", 0))

    if s_uf < -0.1:
        GATE_COUNTS["01_KILLED_BY_S_UF"] += 1
        return "AVOID", 0.0

    if r_rev_k > 0:
        GATE_COUNTS["02_KILLED_BY_R_REV"] += 1
        return "AVOID", 0.0

    if d_k < 0:
        GATE_COUNTS["02_KILLED_BY_D_K_NEGATIVE"] += 1
        return "AVOID", 0.0

    if len(memory_buffer) < 5:
        GATE_COUNTS["05_MISSED_INSUFFICIENT_MEMORY"] += 1
        return "AVOID", 0.0

    old_row = memory_buffer[0]
    old_b_k = _to_num(old_row.get("B", old_row.get("B_k", 0)))

    if r_uf > 0 and p_k <= 1 and m_k >= 0 and u_star < 0.5 and b_k > old_b_k:
        GATE_COUNTS["03_STATE_ACCUMULATE"] += 1
        return "ACCUMULATE", forward_return

    GATE_COUNTS["04_STATE_HOLD"] += 1
    return "HOLD", 0.0


def run(input_path: Path) -> int:
    if not input_path.exists():
        print(f"File missing: {input_path}")
        return 1

    data = defaultdict(list)
    with input_path.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            data[row.get("symbol", "UNK")].append(row)

    results = []
    for rows in data.values():
        rows.sort(key=lambda row: row.get("decision_timestamp", ""))
        memory_buffer = []

        for row in rows:
            decision, projected_return = evaluate_l5_primitive(row, memory_buffer)
            if decision == "ACCUMULATE":
                results.append(projected_return)

            memory_buffer.append(row)
            if len(memory_buffer) > 5:
                memory_buffer.pop(0)

    count = len(results)
    avg_return = (sum(results) / count * 100.0) if count > 0 else 0.0

    print("\n================ FINAL L5 RESULTS ================")
    print(f"Input File:               {input_path}")
    print(f"Total 'Accumulate' Count: {count}")
    print(f"Projected Average Return: {avg_return:.2f}%")
    print("================ DIAGNOSTIC FUNNEL ===============")
    for key, value in sorted(GATE_COUNTS.items()):
        print(f"{key}: {value}")
    print("==================================================\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the tightened L5 shadow pipeline on a row-trace CSV.")
    parser.add_argument("input_csv", nargs="?", default=str(DEFAULT_INPUT))
    args = parser.parse_args()
    return run(Path(str(args.input_csv)).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
