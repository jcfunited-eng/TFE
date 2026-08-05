#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KEY_FIELDS = ("decision_timestamp", "symbol", "horizon")
ROWTRACE_BASE_COLUMNS = [
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
]
PROVENANCE_COLUMNS = ["source_id", "source_path", "source_timestamp_resolution", "source_type"]
OUTPUT_COLUMNS = ROWTRACE_BASE_COLUMNS + PROVENANCE_COLUMNS


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_ms(raw: str) -> Optional[int]:
    text = str(raw or "").strip()
    if len(text) <= 0:
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


def _row_hash(row: Dict[str, str], fields: List[str]) -> str:
    payload = {k: str(row.get(k, "") or "").strip() for k in fields}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Merge baseline + backfilled row-trace rows, deduplicate on "
            "(decision_timestamp, symbol, horizon), preserve source provenance, exclude conflicts by policy."
        )
    )
    p.add_argument(
        "--baseline-rowtrace",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument(
        "--snapshot-backfill-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_from_snapshots_latest.csv"
        ),
    )
    p.add_argument(
        "--regenerated-backfill-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_regenerated_raw_latest.csv"
        ),
    )
    p.add_argument("--additional-backfill-csvs", default="")
    p.add_argument(
        "--conflict-policy",
        choices=["exclude_conflicts", "earliest_source", "fail"],
        default="exclude_conflicts",
    )
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
            "rowtrace_backfill_merge_manifest_latest.json"
        ),
    )
    p.add_argument(
        "--out-conflicts-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_merge_conflicts_latest.csv"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def _source_rows(path: Path, default_source_id: str, default_source_type: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        missing = [c for c in ROWTRACE_BASE_COLUMNS if c not in set(cols)]
        if len(missing) > 0:
            raise ValueError(f"missing_required_columns:{path}:{','.join(missing)}")

        for raw in reader:
            row: Dict[str, str] = {c: str(raw.get(c, "") or "").strip() for c in ROWTRACE_BASE_COLUMNS}
            row["source_id"] = str(raw.get("source_id", "") or "").strip() or default_source_id
            row["source_path"] = str(raw.get("source_path", "") or "").strip() or str(path)
            row["source_timestamp_resolution"] = str(raw.get("source_timestamp_resolution", "") or "").strip()
            row["source_type"] = str(raw.get("source_type", "") or "").strip() or default_source_type
            rows.append(row)

    stats = {
        "path": str(path),
        "rows_total": int(len(rows)),
        "source_id_default": default_source_id,
        "source_type_default": default_source_type,
    }
    return rows, stats


def main() -> int:
    args = parse_args()

    baseline = Path(str(args.baseline_rowtrace)).resolve()
    snapshot = Path(str(args.snapshot_backfill_csv)).resolve()
    regenerated = Path(str(args.regenerated_backfill_csv)).resolve()
    out_csv = Path(str(args.out_csv)).resolve()
    out_manifest = Path(str(args.out_manifest)).resolve()
    out_conflicts = Path(str(args.out_conflicts_csv)).resolve()
    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_manifest

    if not baseline.exists():
        raise FileNotFoundError(f"baseline_rowtrace_not_found:{baseline}")

    source_paths: List[Tuple[Path, str, str]] = [(baseline, "baseline_merged", "baseline")]
    if snapshot.exists() and snapshot.stat().st_size > 0:
        source_paths.append((snapshot, "snapshot_backfill", "snapshot_backfill"))
    if regenerated.exists() and regenerated.stat().st_size > 0:
        source_paths.append((regenerated, "raw_regenerated_backfill", "raw_regenerated_backfill"))

    addl = [tok.strip() for tok in str(args.additional_backfill_csvs).split(",") if tok.strip()]
    for i, raw in enumerate(addl, start=1):
        p = Path(raw).resolve()
        if p.exists() and p.stat().st_size > 0:
            source_paths.append((p, f"additional_backfill_{i}", "additional_backfill"))

    all_rows: List[Dict[str, str]] = []
    source_stats: List[Dict[str, Any]] = []

    for p, sid, stype in source_paths:
        rows, stats = _source_rows(path=p, default_source_id=sid, default_source_type=stype)
        all_rows.extend(rows)
        source_stats.append(stats)

    key_acc: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    hash_fields = list(OUTPUT_COLUMNS)

    for row in all_rows:
        key = tuple(str(row.get(k, "") or "").strip() for k in KEY_FIELDS)
        if any(len(k) <= 0 for k in key):
            continue
        row_hash = _row_hash(row, hash_fields)
        entry = {
            "row": row,
            "hash": row_hash,
        }
        key_acc.setdefault(key, []).append(entry)

    merged_rows: List[Dict[str, str]] = []
    conflicts: List[Dict[str, Any]] = []
    duplicate_same_payload = 0
    conflicting_keys = 0
    excluded_conflicting_keys = 0

    for key, items in key_acc.items():
        by_hash: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            by_hash.setdefault(it["hash"], []).append(it)

        if len(by_hash) == 1:
            representative = next(iter(next(iter(by_hash.values()))))["row"] if False else next(iter(by_hash.values()))[0]["row"]
            duplicate_same_payload += int(len(items) - 1)
            merged_rows.append(representative)
            continue

        conflicting_keys += 1
        variants = []
        for hsh, arr in by_hash.items():
            sample = arr[0]["row"]
            variants.append(
                {
                    "hash": hsh,
                    "count": int(len(arr)),
                    "source_id": str(sample.get("source_id", "") or ""),
                    "decision": str(sample.get("decision", "") or ""),
                    "pattern_key": str(sample.get("pattern_key", "") or ""),
                }
            )

        conflicts.append(
            {
                "decision_timestamp": key[0],
                "symbol": key[1],
                "horizon": key[2],
                "variant_count": int(len(variants)),
                "variants": variants,
            }
        )

        if str(args.conflict_policy) == "fail":
            raise RuntimeError(f"conflict_policy_fail:key={key}")

        if str(args.conflict_policy) == "exclude_conflicts":
            excluded_conflicting_keys += 1
            continue

        # earliest_source: choose baseline first by source_type, else lexical source_id.
        ranked = sorted(
            [arr[0]["row"] for arr in by_hash.values()],
            key=lambda r: (
                0 if str(r.get("source_type", "")) == "baseline" else 1,
                str(r.get("source_id", "")),
            ),
        )
        merged_rows.append(ranked[0])

    def _sort_key(r: Dict[str, str]) -> Tuple[int, str, int]:
        ts = _parse_iso_ms(str(r.get("decision_timestamp", "") or ""))
        ts = -1 if ts is None else int(ts)
        sym = str(r.get("symbol", "") or "")
        try:
            h = int(float(str(r.get("horizon", "") or "0")))
        except Exception:
            h = 0
        return (ts, sym, h)

    merged_rows.sort(key=_sort_key)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_conflicts.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        for row in merged_rows:
            w.writerow({k: row.get(k, "") for k in OUTPUT_COLUMNS})

    with out_conflicts.open("w", encoding="utf-8", newline="") as f:
        fields = ["decision_timestamp", "symbol", "horizon", "variant_count", "variants"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in conflicts:
            w.writerow(
                {
                    "decision_timestamp": c["decision_timestamp"],
                    "symbol": c["symbol"],
                    "horizon": c["horizon"],
                    "variant_count": c["variant_count"],
                    "variants": json.dumps(c["variants"], separators=(",", ":")),
                }
            )

    by_h = Counter(str(r.get("horizon", "") or "") for r in merged_rows)
    by_ts = Counter(str(r.get("decision_timestamp", "") or "") for r in merged_rows)
    by_source_type = Counter(str(r.get("source_type", "") or "") for r in merged_rows)

    manifest = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "merge_backfilled_rowtrace",
        "inputs": {
            "baseline_rowtrace": str(baseline),
            "snapshot_backfill_csv": str(snapshot),
            "regenerated_backfill_csv": str(regenerated),
            "additional_backfill_csvs": addl,
            "conflict_policy": str(args.conflict_policy),
        },
        "merge_contract": {
            "dedupe_key": "(decision_timestamp,symbol,horizon)",
            "preserve_provenance_source_id": True,
            "exclude_conflicting_rows_by_policy": True,
        },
        "source_stats": source_stats,
        "merge_summary": {
            "source_rows_total": int(len(all_rows)),
            "rows_written": int(len(merged_rows)),
            "duplicate_same_payload_collapsed": int(duplicate_same_payload),
            "conflicting_keys_total": int(conflicting_keys),
            "conflicting_keys_excluded": int(excluded_conflicting_keys),
        },
        "dataset_manifest": {
            "rows_total": int(len(merged_rows)),
            "rows_by_horizon": {k: int(v) for k, v in sorted(by_h.items(), key=lambda kv: kv[0])},
            "rows_by_source_type": {k: int(v) for k, v in sorted(by_source_type.items(), key=lambda kv: kv[0])},
            "unique_timestamps": int(len(by_ts)),
            "top_timestamps": [{"decision_timestamp": ts, "rows": int(n)} for ts, n in by_ts.most_common(20)],
        },
        "outputs": {
            "merged_rowtrace_csv": str(out_csv),
            "conflicts_csv": str(out_conflicts),
            "manifest_json": str(out_manifest),
        },
    }

    report_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(str(out_csv))
    print(str(out_conflicts))
    print(str(out_manifest))
    print(
        json.dumps(
            {
                "rows_written": int(len(merged_rows)),
                "unique_timestamps": int(len(by_ts)),
                "conflicting_keys_total": int(conflicting_keys),
                "conflicting_keys_excluded": int(excluded_conflicting_keys),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
