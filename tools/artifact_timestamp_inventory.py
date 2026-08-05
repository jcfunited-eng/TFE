#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

KEY_FIELDS: Tuple[str, str, str] = ("decision_timestamp", "symbol", "horizon")
MIN_REQUIRED_COLUMNS: Tuple[str, ...] = (
    "decision_timestamp",
    "symbol",
    "horizon",
    "decision",
    "regime",
    "forward_return",
    "action_return",
)
ROW_TRACE_FILE_PREFIX = "real_world_cleaned_universe_l5_row_trace"


@dataclass
class ArtifactStats:
    path: Path
    valid: bool
    invalid_reason: Optional[str]
    columns: List[str]
    rows_total: int
    rows_with_valid_timestamp: int
    rows_by_horizon: Dict[int, int]
    unique_timestamps_by_horizon: Dict[int, Set[int]]
    timestamp_bucket_by_horizon: Dict[int, Counter]
    symbols: Set[str]
    earliest_ts_ms: Optional[int]
    latest_ts_ms: Optional[int]
    duplicate_rows: int
    conflict_keys: int


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


def _iso_from_ms(ts_ms: Optional[int]) -> Optional[str]:
    if ts_ms is None:
        return None
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_horizons(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        t = token.strip()
        if len(t) <= 0:
            continue
        out.append(int(t))
    if len(out) <= 0:
        raise ValueError("horizons list is empty")
    return out


def _row_hash(row: Dict[str, str], fields: Iterable[str]) -> str:
    payload = {k: str(row.get(k, "") or "").strip() for k in fields}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _max_gap_ms(ts_values: Set[int]) -> Optional[int]:
    if len(ts_values) <= 1:
        return None
    ordered = sorted(ts_values)
    max_gap = 0
    for i in range(1, len(ordered)):
        gap = int(ordered[i] - ordered[i - 1])
        if gap > max_gap:
            max_gap = gap
    return int(max_gap)


def _is_candidate_row_trace_csv(path: Path) -> bool:
    name = path.name.lower()
    if not name.endswith(".csv"):
        return False
    if not name.startswith(ROW_TRACE_FILE_PREFIX):
        return False
    if "conflicts" in name:
        return False
    return True


def _is_excluded_candidate_path(path: Path) -> bool:
    text = str(path).lower()
    return (
        "/artifact_inventory_candidates/" in text
        or "/artifact_merge_selected/" in text
    )


def _discover_candidates(*, root_row_trace: Path, backups_root: Path, search_max_depth: int) -> List[Path]:
    candidates: Dict[str, Path] = {}

    if root_row_trace.exists() and root_row_trace.is_file() and _is_candidate_row_trace_csv(root_row_trace):
        rr = root_row_trace.resolve()
        if not _is_excluded_candidate_path(rr):
            candidates[str(rr)] = rr

    if backups_root.exists() and backups_root.is_dir():
        cmd = [
            "find",
            str(backups_root),
            "-maxdepth",
            str(int(search_max_depth)),
            "-type",
            "f",
            "-name",
            f"{ROW_TRACE_FILE_PREFIX}*.csv",
            "!",
            "-name",
            "*conflicts*",
        ]
        found = subprocess.run(cmd, check=True, capture_output=True, text=True)
        for line in found.stdout.splitlines():
            p = Path(line.strip()).resolve()
            if not p.is_file():
                continue
            if _is_excluded_candidate_path(p):
                continue
            if _is_candidate_row_trace_csv(p):
                candidates[str(p)] = p

    return [candidates[k] for k in sorted(candidates.keys())]


def _analyze_artifact(path: Path, horizons: List[int]) -> ArtifactStats:
    rows_total = 0
    rows_with_valid_timestamp = 0
    rows_by_horizon: Dict[int, int] = Counter()
    unique_ts_by_h: Dict[int, Set[int]] = {int(h): set() for h in horizons}
    ts_bucket_by_h: Dict[int, Counter] = {int(h): Counter() for h in horizons}
    symbols: Set[str] = set()
    earliest_ts_ms: Optional[int] = None
    latest_ts_ms: Optional[int] = None

    duplicate_rows = 0
    conflict_key_set: Set[Tuple[str, str, str]] = set()
    key_hash_map: Dict[Tuple[str, str, str], str] = {}

    if not path.exists() or not path.is_file():
        return ArtifactStats(
            path=path,
            valid=False,
            invalid_reason="file_not_found",
            columns=[],
            rows_total=0,
            rows_with_valid_timestamp=0,
            rows_by_horizon={},
            unique_timestamps_by_horizon=unique_ts_by_h,
            timestamp_bucket_by_horizon=ts_bucket_by_h,
            symbols=set(),
            earliest_ts_ms=None,
            latest_ts_ms=None,
            duplicate_rows=0,
            conflict_keys=0,
        )

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            columns = list(reader.fieldnames or [])
            missing = [c for c in MIN_REQUIRED_COLUMNS if c not in set(columns)]
            if len(missing) > 0:
                return ArtifactStats(
                    path=path,
                    valid=False,
                    invalid_reason=f"missing_required_columns:{','.join(missing)}",
                    columns=columns,
                    rows_total=0,
                    rows_with_valid_timestamp=0,
                    rows_by_horizon={},
                    unique_timestamps_by_horizon=unique_ts_by_h,
                    timestamp_bucket_by_horizon=ts_bucket_by_h,
                    symbols=set(),
                    earliest_ts_ms=None,
                    latest_ts_ms=None,
                    duplicate_rows=0,
                    conflict_keys=0,
                )

            hash_fields = [c for c in columns]
            horizon_set = set(int(h) for h in horizons)

            for row in reader:
                rows_total += 1
                ts_raw = str(row.get("decision_timestamp", "") or "").strip()
                sym = str(row.get("symbol", "") or "").strip()
                h_raw = str(row.get("horizon", "") or "").strip()

                try:
                    h = int(float(h_raw))
                except Exception:
                    continue
                if int(h) not in horizon_set:
                    continue

                ts_ms = _parse_iso_ms(ts_raw)
                if ts_ms is None:
                    continue

                rows_with_valid_timestamp += 1
                rows_by_horizon[int(h)] += 1
                unique_ts_by_h[int(h)].add(int(ts_ms))
                ts_bucket_by_h[int(h)][int(ts_ms)] += 1

                if len(sym) > 0:
                    symbols.add(sym)

                if earliest_ts_ms is None or ts_ms < earliest_ts_ms:
                    earliest_ts_ms = int(ts_ms)
                if latest_ts_ms is None or ts_ms > latest_ts_ms:
                    latest_ts_ms = int(ts_ms)

                key = (ts_raw, sym, str(int(h)))
                row_hash = _row_hash(row=row, fields=hash_fields)
                prior = key_hash_map.get(key)
                if prior is None:
                    key_hash_map[key] = row_hash
                elif row_hash == prior:
                    duplicate_rows += 1
                else:
                    conflict_key_set.add(key)

            return ArtifactStats(
                path=path,
                valid=True,
                invalid_reason=None,
                columns=columns,
                rows_total=int(rows_total),
                rows_with_valid_timestamp=int(rows_with_valid_timestamp),
                rows_by_horizon={int(k): int(v) for k, v in rows_by_horizon.items()},
                unique_timestamps_by_horizon=unique_ts_by_h,
                timestamp_bucket_by_horizon=ts_bucket_by_h,
                symbols=symbols,
                earliest_ts_ms=earliest_ts_ms,
                latest_ts_ms=latest_ts_ms,
                duplicate_rows=int(duplicate_rows),
                conflict_keys=int(len(conflict_key_set)),
            )
    except Exception as exc:
        return ArtifactStats(
            path=path,
            valid=False,
            invalid_reason=f"read_error:{exc}",
            columns=[],
            rows_total=0,
            rows_with_valid_timestamp=0,
            rows_by_horizon={},
            unique_timestamps_by_horizon=unique_ts_by_h,
            timestamp_bucket_by_horizon=ts_bucket_by_h,
            symbols=set(),
            earliest_ts_ms=None,
            latest_ts_ms=None,
            duplicate_rows=0,
            conflict_keys=0,
        )


def _load_baseline_profile(row_trace_path: Path, horizons: List[int]) -> Dict[str, Any]:
    if not row_trace_path.exists():
        raise FileNotFoundError(f"baseline_row_trace_not_found:{row_trace_path}")

    by_h_ts: Dict[int, Set[int]] = {int(h): set() for h in horizons}
    by_h_rows: Dict[int, int] = {int(h): 0 for h in horizons}
    by_h_buckets: Dict[int, Counter] = {int(h): Counter() for h in horizons}
    symbols: Set[str] = set()

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_raw = str(row.get("decision_timestamp", "") or "").strip()
            h_raw = str(row.get("horizon", "") or "").strip()
            sym = str(row.get("symbol", "") or "").strip()

            try:
                h = int(float(h_raw))
            except Exception:
                continue
            if int(h) not in set(int(x) for x in horizons):
                continue

            ts_ms = _parse_iso_ms(ts_raw)
            if ts_ms is None:
                continue

            by_h_ts[int(h)].add(int(ts_ms))
            by_h_rows[int(h)] += 1
            by_h_buckets[int(h)][int(ts_ms)] += 1
            if len(sym) > 0:
                symbols.add(sym)

    return {
        "row_trace_path": str(row_trace_path),
        "symbols_total": int(len(symbols)),
        "by_horizon": {
            str(h): {
                "rows_total": int(by_h_rows[int(h)]),
                "unique_timestamps": int(len(by_h_ts[int(h)])),
                "max_bucket_size": int(max(by_h_buckets[int(h)].values())) if len(by_h_buckets[int(h)]) > 0 else 0,
                "timestamp_set": by_h_ts[int(h)],
            }
            for h in horizons
        },
    }


def _run_count_and_longest(new_ts_sorted: List[int], continuity_gap_days: int) -> Tuple[int, int]:
    if len(new_ts_sorted) <= 0:
        return 0, 0
    if len(new_ts_sorted) == 1:
        return 1, 1

    gap_ms = int(max(1, continuity_gap_days)) * 86_400_000
    runs = 1
    cur_len = 1
    longest = 1
    for i in range(1, len(new_ts_sorted)):
        if int(new_ts_sorted[i] - new_ts_sorted[i - 1]) <= gap_ms:
            cur_len += 1
        else:
            runs += 1
            cur_len = 1
        if cur_len > longest:
            longest = cur_len
    return int(runs), int(longest)


def _max_nonoverlap_blocks(unique_ts: int, horizon: int, test_block_timestamps: int) -> int:
    min_test_start_idx = int(horizon + 1)
    available = int(max(0, int(unique_ts) - min_test_start_idx))
    return int(available // max(1, int(test_block_timestamps)))


def _artifact_summary(a: ArtifactStats, horizons: List[int]) -> Dict[str, Any]:
    largest_bucket_by_h = {
        str(h): int(max(a.timestamp_bucket_by_horizon[int(h)].values())) if len(a.timestamp_bucket_by_horizon[int(h)]) > 0 else 0
        for h in horizons
    }
    largest_bucket_any = int(max(largest_bucket_by_h.values())) if len(largest_bucket_by_h) > 0 else 0

    rows_by_h = {str(h): int(a.rows_by_horizon.get(int(h), 0)) for h in horizons}
    uniq_by_h = {str(h): int(len(a.unique_timestamps_by_horizon.get(int(h), set()))) for h in horizons}

    all_ts: Set[int] = set()
    for h in horizons:
        all_ts.update(a.unique_timestamps_by_horizon.get(int(h), set()))

    return {
        "artifact_path": str(a.path),
        "valid_row_trace_artifact": bool(a.valid),
        "invalid_reason": a.invalid_reason,
        "rows_total": int(a.rows_total),
        "rows_with_valid_timestamp": int(a.rows_with_valid_timestamp),
        "earliest_decision_timestamp_ms": (int(a.earliest_ts_ms) if a.earliest_ts_ms is not None else None),
        "earliest_decision_timestamp_iso_utc": _iso_from_ms(a.earliest_ts_ms),
        "latest_decision_timestamp_ms": (int(a.latest_ts_ms) if a.latest_ts_ms is not None else None),
        "latest_decision_timestamp_iso_utc": _iso_from_ms(a.latest_ts_ms),
        "rows_added_by_horizon": rows_by_h,
        "unique_timestamps_by_horizon": uniq_by_h,
        "symbol_count": int(len(a.symbols)),
        "largest_timestamp_bucket_size": int(largest_bucket_any),
        "largest_timestamp_bucket_by_horizon": largest_bucket_by_h,
        "duplicate_conflict_count": {
            "duplicate_rows_same_key_same_payload": int(a.duplicate_rows),
            "conflict_keys_same_key_different_payload": int(a.conflict_keys),
            "combined": int(a.duplicate_rows + a.conflict_keys),
        },
        "all_horizon_unique_timestamps": int(len(all_ts)),
        "max_gap_between_timestamps_ms": _max_gap_ms(all_ts),
    }


def _contribution_row(
    *,
    art: ArtifactStats,
    baseline: Dict[str, Any],
    horizons: List[int],
    test_block_timestamps: int,
    continuity_gap_days: int,
    contiguous_min_run: int,
) -> Dict[str, Any]:
    by_h: Dict[str, Any] = {}

    new_total = 0
    overlap_total = 0
    artifact_ts_total = 0
    estimated_gain_total = 0
    contiguous_h_count = 0
    isolated_h_count = 0

    for h in horizons:
        h_s = str(h)
        art_ts = set(art.unique_timestamps_by_horizon[int(h)])
        base_ts = set(baseline["by_horizon"][h_s]["timestamp_set"])

        overlap = int(len(art_ts & base_ts))
        new_ts = sorted(art_ts - base_ts)
        new_count = int(len(new_ts))
        art_count = int(len(art_ts))

        overlap_ratio = float(overlap / art_count) if art_count > 0 else 0.0

        base_blocks = _max_nonoverlap_blocks(
            unique_ts=int(len(base_ts)),
            horizon=int(h),
            test_block_timestamps=int(test_block_timestamps),
        )
        post_blocks = _max_nonoverlap_blocks(
            unique_ts=int(len(base_ts) + new_count),
            horizon=int(h),
            test_block_timestamps=int(test_block_timestamps),
        )
        estimated_gain = int(max(0, post_blocks - base_blocks))

        run_count, longest_run = _run_count_and_longest(
            new_ts_sorted=new_ts,
            continuity_gap_days=int(continuity_gap_days),
        )
        if new_count <= 0:
            contiguity_label = "none"
        elif longest_run >= int(contiguous_min_run):
            contiguity_label = "contiguous"
        elif new_count <= 2:
            contiguity_label = "isolated"
        else:
            contiguity_label = "mixed"

        by_h[h_s] = {
            "artifact_unique_timestamps": int(art_count),
            "overlap_timestamps_with_current_merged": int(overlap),
            "new_unique_timestamps_added": int(new_count),
            "timestamp_overlap_ratio": float(overlap_ratio),
            "estimated_post_purge_usable_timestamp_gain": int(estimated_gain),
            "new_timestamp_runs": int(run_count),
            "longest_new_timestamp_run": int(longest_run),
            "contiguity_label": contiguity_label,
        }

        new_total += int(new_count)
        overlap_total += int(overlap)
        artifact_ts_total += int(art_count)
        estimated_gain_total += int(estimated_gain)
        contiguous_h_count += int(1 if contiguity_label == "contiguous" else 0)
        isolated_h_count += int(1 if contiguity_label == "isolated" else 0)

    baseline_symbols_total = int(baseline["symbols_total"])
    symbol_count = int(len(art.symbols))
    symbol_coverage_ratio = float(symbol_count / baseline_symbols_total) if baseline_symbols_total > 0 else 0.0
    overlap_ratio_weighted = float(overlap_total / artifact_ts_total) if artifact_ts_total > 0 else 0.0

    return {
        "artifact_path": str(art.path),
        "new_unique_timestamps_added_by_horizon": {
            str(h): int(by_h[str(h)]["new_unique_timestamps_added"]) for h in horizons
        },
        "timestamp_overlap_by_horizon": {
            str(h): int(by_h[str(h)]["overlap_timestamps_with_current_merged"]) for h in horizons
        },
        "estimated_post_purge_usable_timestamp_gain_by_horizon": {
            str(h): int(by_h[str(h)]["estimated_post_purge_usable_timestamp_gain"]) for h in horizons
        },
        "contiguity_by_horizon": {
            str(h): str(by_h[str(h)]["contiguity_label"]) for h in horizons
        },
        "symbol_coverage": {
            "symbol_count": int(symbol_count),
            "coverage_ratio_vs_current_merged": float(symbol_coverage_ratio),
        },
        "details_by_horizon": by_h,
        "new_unique_timestamps_added_total": int(new_total),
        "estimated_post_purge_usable_timestamp_gain_total": int(estimated_gain_total),
        "weighted_timestamp_overlap_ratio": float(overlap_ratio_weighted),
        "contiguous_horizon_count": int(contiguous_h_count),
        "isolated_horizon_count": int(isolated_h_count),
    }


def _rank_artifacts(
    *,
    valid_artifacts: List[ArtifactStats],
    baseline: Dict[str, Any],
    horizons: List[int],
    test_block_timestamps: int,
    continuity_gap_days: int,
    contiguous_min_run: int,
    max_merge_candidates: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    baseline_path = str(Path(str(baseline["row_trace_path"])).resolve())

    for art in valid_artifacts:
        row = _contribution_row(
            art=art,
            baseline=baseline,
            horizons=horizons,
            test_block_timestamps=int(test_block_timestamps),
            continuity_gap_days=int(continuity_gap_days),
            contiguous_min_run=int(contiguous_min_run),
        )

        earliest_cmp = int(art.earliest_ts_ms) if art.earliest_ts_ms is not None else int(10**18)
        score = (
            -int(row["estimated_post_purge_usable_timestamp_gain_total"]),
            -int(row["new_unique_timestamps_added_total"]),
            float(row["weighted_timestamp_overlap_ratio"]),
            -int(row["contiguous_horizon_count"]),
            int(row["isolated_horizon_count"]),
            earliest_cmp,
            -int(len(art.symbols)),
            str(art.path),
        )
        row["_score"] = score
        row["_is_baseline"] = bool(str(art.path.resolve()) == baseline_path)
        rows.append(row)

    rows.sort(key=lambda r: r["_score"])

    ranked: List[Dict[str, Any]] = []
    recommended: List[str] = []
    for idx, row in enumerate(rows, start=1):
        is_baseline = bool(row.pop("_is_baseline"))
        row.pop("_score", None)

        selectable = (
            (not is_baseline)
            and int(row["new_unique_timestamps_added_total"]) > 0
            and int(row["estimated_post_purge_usable_timestamp_gain_total"]) >= 0
        )

        row["rank"] = int(idx)
        row["selection_recommended"] = bool(selectable)
        row["selection_reason"] = (
            "net_temporal_gain_candidate" if selectable else ("baseline_current_merged" if is_baseline else "no_new_timestamps")
        )

        ranked.append(row)

        if selectable and len(recommended) < int(max_merge_candidates):
            recommended.append(str(row["artifact_path"]))

    return ranked, recommended


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build an archived row-trace artifact inventory and rank artifacts by net temporal contribution "
            "against the current merged dataset."
        )
    )
    p.add_argument("--root-row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--backups-root", default="backups")
    p.add_argument("--search-max-depth", type=int, default=4)
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument(
        "--baseline-merged-row-trace",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument("--test-block-timestamps", type=int, default=5)
    p.add_argument("--continuity-gap-days", type=int, default=7)
    p.add_argument("--contiguous-min-run", type=int, default=3)
    p.add_argument("--max-merge-candidates", type=int, default=3)
    p.add_argument(
        "--inventory-out",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "artifact_timestamp_inventory_latest.json"
        ),
    )
    p.add_argument(
        "--selection-out",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "artifact_timestamp_selection_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    root_row_trace = Path(str(args.root_row_trace)).resolve()
    backups_root = Path(str(args.backups_root)).resolve()
    horizons = _parse_horizons(str(args.horizons))
    search_max_depth = int(args.search_max_depth)
    baseline_merged_row_trace = Path(str(args.baseline_merged_row_trace)).resolve()

    inventory_out = Path(str(args.inventory_out)).resolve()
    selection_out = Path(str(args.selection_out)).resolve()
    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else inventory_out

    candidates = _discover_candidates(
        root_row_trace=root_row_trace,
        backups_root=backups_root,
        search_max_depth=search_max_depth,
    )

    artifacts: List[ArtifactStats] = []
    for c in candidates:
        artifacts.append(_analyze_artifact(path=c, horizons=horizons))

    valid_artifacts = [a for a in artifacts if bool(a.valid)]
    invalid_artifacts = [a for a in artifacts if not bool(a.valid)]

    baseline = _load_baseline_profile(row_trace_path=baseline_merged_row_trace, horizons=horizons)

    ranking, recommended_paths = _rank_artifacts(
        valid_artifacts=valid_artifacts,
        baseline=baseline,
        horizons=horizons,
        test_block_timestamps=int(args.test_block_timestamps),
        continuity_gap_days=int(args.continuity_gap_days),
        contiguous_min_run=int(args.contiguous_min_run),
        max_merge_candidates=int(args.max_merge_candidates),
    )

    artifact_rows = [_artifact_summary(a=a, horizons=horizons) for a in artifacts]
    ranking_by_path = {str(r["artifact_path"]): r for r in ranking}

    for row in artifact_rows:
        path = str(row["artifact_path"])
        rk = ranking_by_path.get(path)
        if rk is None:
            row["new_unique_timestamps_added_by_horizon"] = {str(h): 0 for h in horizons}
            row["new_unique_timestamps_added_total"] = 0
            row["timestamp_overlap_by_horizon"] = {str(h): 0 for h in horizons}
            row["estimated_post_purge_usable_timestamp_gain_by_horizon"] = {str(h): 0 for h in horizons}
            row["contiguity_by_horizon"] = {str(h): "none" for h in horizons}
            row["symbol_coverage"] = {
                "symbol_count": int(row["symbol_count"]),
                "coverage_ratio_vs_current_merged": 0.0,
            }
            row["selection_recommended"] = False
            row["selection_rank"] = None
        else:
            row["new_unique_timestamps_added_by_horizon"] = dict(rk["new_unique_timestamps_added_by_horizon"])
            row["new_unique_timestamps_added_total"] = int(rk["new_unique_timestamps_added_total"])
            row["timestamp_overlap_by_horizon"] = dict(rk["timestamp_overlap_by_horizon"])
            row["estimated_post_purge_usable_timestamp_gain_by_horizon"] = dict(
                rk["estimated_post_purge_usable_timestamp_gain_by_horizon"]
            )
            row["contiguity_by_horizon"] = dict(rk["contiguity_by_horizon"])
            row["symbol_coverage"] = dict(rk["symbol_coverage"])
            row["selection_recommended"] = bool(rk["selection_recommended"])
            row["selection_rank"] = int(rk["rank"])

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "artifact_timestamp_inventory",
        "inputs": {
            "root_row_trace": str(root_row_trace),
            "backups_root": str(backups_root),
            "search_max_depth": int(search_max_depth),
            "horizons": [int(h) for h in horizons],
            "baseline_merged_row_trace": str(baseline_merged_row_trace),
            "test_block_timestamps": int(args.test_block_timestamps),
            "continuity_gap_days": int(args.continuity_gap_days),
            "contiguous_min_run": int(args.contiguous_min_run),
            "max_merge_candidates": int(args.max_merge_candidates),
            "candidate_filename_rule": f"{ROW_TRACE_FILE_PREFIX}*.csv (excluding *conflicts*)",
        },
        "design_contract": {
            "ranking_primary_key": "estimated_post_purge_usable_timestamp_gain_total_desc",
            "ranking_secondary_key": "new_unique_timestamps_added_total_desc",
            "row_count_not_used_as_rank_key": True,
            "selection_rule": "non-baseline artifact with new_unique_timestamps_added_total>0",
        },
        "baseline_profile": {
            "row_trace_path": baseline["row_trace_path"],
            "symbols_total": baseline["symbols_total"],
            "by_horizon": {
                str(h): {
                    "rows_total": baseline["by_horizon"][str(h)]["rows_total"],
                    "unique_timestamps": baseline["by_horizon"][str(h)]["unique_timestamps"],
                    "max_bucket_size": baseline["by_horizon"][str(h)]["max_bucket_size"],
                }
                for h in horizons
            },
        },
        "inventory_summary": {
            "candidate_files_discovered": int(len(candidates)),
            "valid_row_trace_artifacts": int(len(valid_artifacts)),
            "invalid_artifacts": int(len(invalid_artifacts)),
            "recommended_artifacts": int(len(recommended_paths)),
        },
        "artifacts": artifact_rows,
        "ranking_by_net_temporal_contribution": ranking,
        "recommended_merge_artifacts": recommended_paths,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    inventory_out.parent.mkdir(parents=True, exist_ok=True)
    selection_out.parent.mkdir(parents=True, exist_ok=True)

    report_json = json.dumps(report, indent=2)
    report_out.write_text(report_json, encoding="utf-8")
    inventory_out.write_text(report_json, encoding="utf-8")

    selection_payload = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "artifact_timestamp_selection",
        "selection_rule": "selected artifacts are net temporal contributors and not baseline",
        "horizons": [int(h) for h in horizons],
        "recommended_merge_artifacts": recommended_paths,
    }
    selection_out.write_text(json.dumps(selection_payload, indent=2), encoding="utf-8")

    print(str(inventory_out))
    print(str(selection_out))
    print(
        json.dumps(
            {
                "candidate_files_discovered": int(len(candidates)),
                "valid_row_trace_artifacts": int(len(valid_artifacts)),
                "recommended_artifacts": int(len(recommended_paths)),
                "top_ranked": (ranking[0]["artifact_path"] if len(ranking) > 0 else None),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
