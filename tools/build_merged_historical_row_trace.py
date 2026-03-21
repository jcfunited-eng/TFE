#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROW_TRACE_FILENAME = "real_world_cleaned_universe_l5_row_trace_full.csv"
TIME_TOKEN_RE = re.compile(r"(20\d{6}T\d{6}Z)")
KEY_FIELDS = ("decision_timestamp", "symbol", "horizon")
REQUIRED_FIELDS = (
    "symbol",
    "horizon",
    "decision_timestamp",
    "decision",
    "regime",
    "S_UF",
    "R_UF",
    "D",
    "M",
    "R_rev",
    "U_star",
    "C",
    "C_k",
    "P",
    "B",
    "price_at_decision",
    "forward_return",
    "action_return",
    "pattern_key",
)


@dataclass(frozen=True)
class SourceEntry:
    path: Path
    capture_ts_ms: int
    capture_ts_iso_utc: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_iso_from_ms(ts_ms: int) -> str:
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_ms(raw: str) -> Optional[int]:
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


def _extract_capture_ts_ms(path: Path) -> int:
    text = str(path)
    tokens = TIME_TOKEN_RE.findall(text)
    if len(tokens) > 0:
        try:
            dt = datetime.strptime(tokens[-1], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            return int(round(dt.timestamp() * 1000.0))
        except Exception:
            pass
    stat = path.stat()
    return int(round(float(stat.st_mtime) * 1000.0))


def _discover_sources(root_row_trace: Path, backups_root: Path) -> List[SourceEntry]:
    candidates: List[Path] = []
    if root_row_trace.exists():
        candidates.append(root_row_trace.resolve())
    if backups_root.exists():
        try:
            rg = subprocess.run(
                ["rg", "--files", str(backups_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            for line in rg.stdout.splitlines():
                p = Path(line.strip())
                if p.name == ROW_TRACE_FILENAME and p.is_file():
                    candidates.append(p.resolve())
        except Exception:
            for p in backups_root.rglob(ROW_TRACE_FILENAME):
                if p.is_file():
                    candidates.append(p.resolve())

    dedup: Dict[str, Path] = {}
    for c in candidates:
        dedup[str(c)] = c

    out: List[SourceEntry] = []
    for _, p in sorted(dedup.items(), key=lambda kv: kv[0]):
        ts_ms = _extract_capture_ts_ms(p)
        out.append(SourceEntry(path=p, capture_ts_ms=ts_ms, capture_ts_iso_utc=_to_iso_from_ms(ts_ms)))

    out.sort(key=lambda s: (s.capture_ts_ms, str(s.path)))
    return out


def _row_hash(row: Dict[str, str], fields: List[str]) -> str:
    canonical = {k: str(row.get(k, "") or "").strip() for k in fields}
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _timestamp_histogram(rows: Iterable[Dict[str, str]]) -> Tuple[Counter, Optional[int], Optional[int]]:
    hist: Counter = Counter()
    ts_min: Optional[int] = None
    ts_max: Optional[int] = None
    for row in rows:
        ts_raw = str(row.get("decision_timestamp", "") or "").strip()
        ts_ms = _parse_iso_ms(ts_raw)
        if ts_ms is None:
            continue
        hist[ts_ms] += 1
        ts_min = ts_ms if ts_min is None or ts_ms < ts_min else ts_min
        ts_max = ts_ms if ts_max is None or ts_ms > ts_max else ts_max
    return hist, ts_min, ts_max


def _horizon_timeblock_feasibility(rows: List[Dict[str, str]], train_frac: float) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    by_h: Dict[int, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        try:
            h = int(float(str(row.get("horizon", "") or "0")))
        except Exception:
            continue
        by_h[h].append(row)

    for h in sorted(by_h.keys()):
        hh_rows = by_h[h]
        ts_counts: Counter = Counter()
        for row in hh_rows:
            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "") or ""))
            if ts_ms is None:
                continue
            ts_counts[ts_ms] += 1
        total = int(sum(ts_counts.values()))
        unique_ts = int(len(ts_counts))
        max_train_rows = int(total - max(ts_counts.values())) if total > 0 and unique_ts > 0 else 0
        max_train_frac = float(max_train_rows / total) if total > 0 else 0.0
        out[str(h)] = {
            "rows_total": total,
            "unique_timestamps": unique_ts,
            "max_timestamp_disjoint_train_frac": max_train_frac,
            "train_frac_target": float(train_frac),
            "timestamp_disjoint_train_frac_feasible": bool(max_train_frac >= float(train_frac)),
        }
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build one merged historical row-trace dataset from archived row-trace artifacts "
            "using archive provenance only (no row recomputation)."
        )
    )
    p.add_argument("--root-row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--backups-root", default="backups")
    p.add_argument(
        "--out-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical_manifest_latest.json"
        ),
    )
    p.add_argument(
        "--out-conflicts-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical_conflicts_latest.csv"
        ),
    )
    p.add_argument(
        "--conflict-policy",
        choices=["exclude_conflicts", "earliest_source_capture", "fail"],
        default="exclude_conflicts",
    )
    p.add_argument("--timeblock-train-frac", type=float, default=0.8)
    p.add_argument("--top-k-timestamps", type=int, default=20)
    p.add_argument("--report-out", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    root_row_trace = Path(str(args.root_row_trace)).resolve()
    backups_root = Path(str(args.backups_root)).resolve()
    out_csv = Path(str(args.out_csv)).resolve()
    out_manifest = Path(str(args.out_manifest)).resolve()
    out_conflicts_csv = Path(str(args.out_conflicts_csv)).resolve()

    sources = _discover_sources(root_row_trace=root_row_trace, backups_root=backups_root)
    if len(sources) <= 0:
        raise FileNotFoundError("no_row_trace_sources_found")

    output_fields: List[str] = list(REQUIRED_FIELDS)
    source_stats: List[Dict[str, Any]] = []
    rows_total_source = 0

    key_acc: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for src_idx, src in enumerate(sources):
        source_rows = 0
        source_hist: Counter = Counter()
        by_h_counter: Counter = Counter()

        with src.path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            source_fields = list(reader.fieldnames or [])
            missing_key_cols = [c for c in KEY_FIELDS if c not in set(source_fields)]
            if len(missing_key_cols) > 0:
                raise ValueError(f"source_missing_key_columns:{src.path}:{','.join(missing_key_cols)}")
            missing_output_cols = [c for c in output_fields if c not in set(source_fields)]
            extra_source_cols = [c for c in source_fields if c not in set(output_fields)]

            for raw_row in reader:
                source_rows += 1
                rows_total_source += 1

                row = {k: str(raw_row.get(k, "") or "").strip() for k in output_fields}
                key = tuple(row.get(k, "") for k in KEY_FIELDS)
                if any(len(str(v).strip()) <= 0 for v in key):
                    raise ValueError(f"row_missing_key_fields:source={src.path}:row_index={source_rows}")

                row_hash = _row_hash(row=row, fields=output_fields)
                source_hist[key[0]] += 1
                by_h_counter[key[2]] += 1

                acc = key_acc.get(key)
                if acc is None:
                    acc = {
                        "total_seen": 0,
                        "variants": {},
                    }
                    key_acc[key] = acc

                acc["total_seen"] = int(acc["total_seen"]) + 1
                variants = acc["variants"]
                variant = variants.get(row_hash)
                if variant is None:
                    variants[row_hash] = {
                        "row": row,
                        "first_source_idx": int(src_idx),
                        "first_source_path": str(src.path),
                        "seen_count": 1,
                    }
                else:
                    variant["seen_count"] = int(variant["seen_count"]) + 1

        source_stats.append(
            {
                "path": str(src.path),
                "capture_ts_ms": int(src.capture_ts_ms),
                "capture_ts_iso_utc": str(src.capture_ts_iso_utc),
                "rows": int(source_rows),
                "unique_timestamps": int(len(source_hist)),
                "rows_by_horizon": {str(k): int(v) for k, v in sorted(by_h_counter.items(), key=lambda kv: kv[0])},
                "missing_output_columns": missing_output_cols,
                "extra_source_columns": extra_source_cols,
                "top_timestamps": [
                    {
                        "decision_ts": ts,
                        "rows": int(n),
                    }
                    for ts, n in source_hist.most_common(5)
                ],
            }
        )

    merged_rows: List[Dict[str, str]] = []
    conflict_rows: List[Dict[str, str]] = []
    exact_duplicate_rows_collapsed = 0
    conflict_keys = 0
    conflict_keys_excluded = 0

    for key, acc in key_acc.items():
        variants: Dict[str, Dict[str, Any]] = acc["variants"]
        total_seen = int(acc["total_seen"])
        variant_count = int(len(variants))
        exact_duplicate_rows_collapsed += int(total_seen - variant_count)

        if variant_count == 1:
            only_variant = next(iter(variants.values()))
            merged_rows.append(dict(only_variant["row"]))
            continue

        conflict_keys += 1
        variant_list = sorted(
            [
                {
                    "hash": h,
                    "first_source_idx": int(v["first_source_idx"]),
                    "first_source_path": str(v["first_source_path"]),
                    "seen_count": int(v["seen_count"]),
                    "row": dict(v["row"]),
                }
                for h, v in variants.items()
            ],
            key=lambda x: (x["first_source_idx"], x["hash"]),
        )

        for v in variant_list:
            conflict_rows.append(
                {
                    "decision_timestamp": str(key[0]),
                    "symbol": str(key[1]),
                    "horizon": str(key[2]),
                    "variant_hash": str(v["hash"]),
                    "first_source_idx": int(v["first_source_idx"]),
                    "first_source_path": str(v["first_source_path"]),
                    "seen_count": int(v["seen_count"]),
                    "decision": str(v["row"].get("decision", "")),
                    "regime": str(v["row"].get("regime", "")),
                    "D": str(v["row"].get("D", "")),
                    "M": str(v["row"].get("M", "")),
                    "R_rev": str(v["row"].get("R_rev", "")),
                    "U_star": str(v["row"].get("U_star", "")),
                    "C": str(v["row"].get("C", "")),
                    "P": str(v["row"].get("P", "")),
                    "B": str(v["row"].get("B", "")),
                    "S_UF": str(v["row"].get("S_UF", "")),
                    "R_UF": str(v["row"].get("R_UF", "")),
                    "pattern_key": str(v["row"].get("pattern_key", "")),
                }
            )

        if str(args.conflict_policy) == "fail":
            raise RuntimeError(
                "merge_conflicts_detected_and_policy_is_fail:"
                f"conflict_keys={conflict_keys}"
            )

        if str(args.conflict_policy) == "exclude_conflicts":
            conflict_keys_excluded += 1
            continue

        selected = variant_list[0]
        merged_rows.append(dict(selected["row"]))

    def _sort_key(row: Dict[str, str]) -> Tuple[int, str, int]:
        ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "") or ""))
        if ts_ms is None:
            ts_ms = -1
        sym = str(row.get("symbol", "") or "")
        try:
            h = int(float(str(row.get("horizon", "") or "0")) or 0)
        except Exception:
            h = 0
        return (ts_ms, sym, h)

    merged_rows.sort(key=_sort_key)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_conflicts_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        for row in merged_rows:
            writer.writerow({k: row.get(k, "") for k in output_fields})

    with out_conflicts_csv.open("w", encoding="utf-8", newline="") as f:
        conflict_fields = [
            "decision_timestamp",
            "symbol",
            "horizon",
            "variant_hash",
            "first_source_idx",
            "first_source_path",
            "seen_count",
            "decision",
            "regime",
            "D",
            "M",
            "R_rev",
            "U_star",
            "C",
            "P",
            "B",
            "S_UF",
            "R_UF",
            "pattern_key",
        ]
        writer = csv.DictWriter(f, fieldnames=conflict_fields)
        writer.writeheader()
        for row in conflict_rows:
            writer.writerow(row)

    key_counter = Counter(
        (
            str(r.get("decision_timestamp", "") or "").strip(),
            str(r.get("symbol", "") or "").strip(),
            str(r.get("horizon", "") or "").strip(),
        )
        for r in merged_rows
    )
    duplicate_keys_in_output = int(sum(max(0, n - 1) for n in key_counter.values()))

    ts_hist, ts_min_ms, ts_max_ms = _timestamp_histogram(merged_rows)
    symbols_total = len({str(r.get("symbol", "") or "").strip() for r in merged_rows if str(r.get("symbol", "") or "").strip()})
    by_h_rows: Dict[str, int] = Counter(str(r.get("horizon", "") or "") for r in merged_rows)

    top_k = int(max(1, args.top_k_timestamps))
    top_ts = ts_hist.most_common(top_k)
    full_hist_sorted = sorted(ts_hist.items(), key=lambda kv: kv[0])

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "merged_historical_row_trace_from_archives",
        "design_contract": {
            "row_recomputation": False,
            "archive_provenance_only": True,
            "key_definition": "(decision_timestamp, symbol, horizon)",
            "conflict_policy": str(args.conflict_policy),
            "source_precedence_when_needed": "earliest_source_capture_timestamp_then_path",
        },
        "inputs": {
            "root_row_trace": str(root_row_trace),
            "backups_root": str(backups_root),
            "out_csv": str(out_csv),
            "out_conflicts_csv": str(out_conflicts_csv),
            "timeblock_train_frac_target": float(args.timeblock_train_frac),
        },
        "sources": source_stats,
        "merge_summary": {
            "source_files": int(len(sources)),
            "source_rows_total": int(rows_total_source),
            "unique_keys_seen": int(len(key_acc)),
            "exact_duplicate_rows_collapsed": int(exact_duplicate_rows_collapsed),
            "conflict_keys_total": int(conflict_keys),
            "conflict_keys_excluded": int(conflict_keys_excluded),
            "conflict_variants_rows_written": int(len(conflict_rows)),
            "rows_written": int(len(merged_rows)),
            "duplicate_key_rows_in_output": int(duplicate_keys_in_output),
        },
        "dataset_manifest": {
            "rows_total": int(len(merged_rows)),
            "symbols_total": int(symbols_total),
            "unique_timestamps": int(len(ts_hist)),
            "ts_min_ms": (int(ts_min_ms) if ts_min_ms is not None else None),
            "ts_max_ms": (int(ts_max_ms) if ts_max_ms is not None else None),
            "ts_min_iso_utc": (_to_iso_from_ms(int(ts_min_ms)) if ts_min_ms is not None else None),
            "ts_max_iso_utc": (_to_iso_from_ms(int(ts_max_ms)) if ts_max_ms is not None else None),
            "rows_by_horizon": {str(k): int(v) for k, v in sorted(by_h_rows.items(), key=lambda kv: kv[0])},
            "duplicate_count_on_key_decisionTimestamp_symbol_horizon": int(duplicate_keys_in_output),
            "top_timestamps_by_row_count": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _to_iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in top_ts
            ],
            "rows_per_timestamp_histogram": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _to_iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in full_hist_sorted
            ],
            "timeblock_feasibility_by_horizon": _horizon_timeblock_feasibility(
                rows=merged_rows,
                train_frac=float(args.timeblock_train_frac),
            ),
        },
    }

    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_manifest
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(str(out_csv))
    print(str(out_conflicts_csv))
    print(str(report_out))
    print(
        json.dumps(
            {
                "rows_total": report["dataset_manifest"]["rows_total"],
                "unique_timestamps": report["dataset_manifest"]["unique_timestamps"],
                "symbols_total": report["dataset_manifest"]["symbols_total"],
                "conflict_keys_total": report["merge_summary"]["conflict_keys_total"],
                "conflict_keys_excluded": report["merge_summary"]["conflict_keys_excluded"],
                "h5_timeblock_feasible_80_20": (
                    report["dataset_manifest"]["timeblock_feasibility_by_horizon"].get("5", {}).get(
                        "timestamp_disjoint_train_frac_feasible"
                    )
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
