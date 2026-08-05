#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TIME_TOKEN_RE = re.compile(r"(20\d{6}T\d{6}Z)")
ROWTRACE_COLUMNS = [
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
    "source_id",
    "source_path",
    "source_timestamp_resolution",
]


@dataclass
class SnapshotRow:
    source_id: str
    source_path: str
    source_timestamp_resolution: str
    ts_ms: int
    ts_iso: str
    symbol: str
    regime: str
    s_uf: float
    r_uf: float
    d: float
    m: float
    r_rev: float
    u_star: float
    c: float
    p: float
    b: float
    price: float


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


def _iso_from_ms(ts_ms: int) -> str:
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _to_float(raw: Any) -> Optional[float]:
    try:
        v = float(str(raw).strip())
        return float(v)
    except Exception:
        return None


def _sign(v: float) -> int:
    if v > 0.0:
        return 1
    if v < 0.0:
        return -1
    return 0


def _pattern_key(regime: str, d: float, p: float, r_rev: float, b: float) -> str:
    return f"reg={regime}|D={int(round(d))}|P={int(round(p))}|Rrev={int(round(r_rev))}|Bsgn={_sign(b)}"


def _classify_policy(s_uf: float, d: float) -> str:
    if s_uf < 0.30:
        return "Avoid"
    if d > 0.0:
        return "Accumulate"
    if d == 0.0:
        return "Hold"
    return "Avoid"


def _action_return(decision: str, forward_return: float) -> float:
    if decision == "Accumulate":
        return float(forward_return)
    if decision == "Avoid":
        return float(-forward_return)
    return 0.0


def _row_hash(row: Dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_snapshot_timestamp_ms(path: Path, payload: Any) -> Tuple[Optional[int], str]:
    if isinstance(payload, dict):
        ts = _parse_iso_ms(payload.get("generated_at_utc"))
        if ts is not None:
            return ts, "payload.generated_at_utc"

    tokens = TIME_TOKEN_RE.findall(str(path))
    if len(tokens) > 0:
        try:
            dt = datetime.strptime(tokens[-1], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            return int(round(dt.timestamp() * 1000.0)), "path.time_token"
        except Exception:
            pass

    return None, "unresolved"


def _load_snapshot_paths(args: argparse.Namespace) -> List[Path]:
    out: List[Path] = []

    if str(args.snapshot_sources_json).strip():
        payload = json.loads(Path(str(args.snapshot_sources_json)).resolve().read_text(encoding="utf-8"))
        paths = payload.get("recommended_merge_artifacts") if isinstance(payload, dict) else payload
        if isinstance(paths, list):
            for p in paths:
                pp = Path(str(p)).resolve()
                if pp.exists() and pp.is_file():
                    out.append(pp)

    if len(out) <= 0 and str(args.backfill_plan).strip():
        plan = json.loads(Path(str(args.backfill_plan)).resolve().read_text(encoding="utf-8"))
        for p in plan.get("recommended_next_batches", {}).get("B_convert_snapshot_archives", []):
            pp = Path(str(p)).resolve()
            if pp.exists() and pp.is_file():
                out.append(pp)

    dedup: Dict[str, Path] = {str(p): p for p in out}
    return [dedup[k] for k in sorted(dedup.keys())]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Convert archived snapshots to canonical row-trace rows only when timestamp and field provenance "
            "are sufficient. Ambiguous mappings are rejected."
        )
    )
    p.add_argument(
        "--backfill-plan",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_plan_latest.json"
        ),
    )
    p.add_argument("--snapshot-sources-json", default="")
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--require-future-price", action="store_true", default=True)
    p.add_argument(
        "--out-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_from_snapshots_latest.csv"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_from_snapshots_manifest_latest.json"
        ),
    )
    p.add_argument(
        "--out-conflicts-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_from_snapshots_conflicts_latest.csv"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    horizons = [int(tok.strip()) for tok in str(args.horizons).split(",") if tok.strip()]
    if len(horizons) <= 0:
        raise ValueError("horizons list is empty")

    source_paths = _load_snapshot_paths(args=args)

    out_csv = Path(str(args.out_csv)).resolve()
    out_manifest = Path(str(args.out_manifest)).resolve()
    out_conflicts_csv = Path(str(args.out_conflicts_csv)).resolve()
    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_manifest

    exclusion_counts: Counter = Counter()
    source_stats: List[Dict[str, Any]] = []

    rows_raw: List[SnapshotRow] = []
    per_symbol_points: Dict[str, List[Tuple[int, float]]] = defaultdict(list)

    for idx, path in enumerate(source_paths, start=1):
        source_id = f"snapshot:{idx:04d}:{path.name}"
        src_rows = 0
        src_excluded = Counter()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            exclusion_counts["source_read_error"] += 1
            source_stats.append(
                {
                    "source_id": source_id,
                    "source_path": str(path),
                    "rows_total": 0,
                    "rows_converted": 0,
                    "rows_excluded": 0,
                    "timestamp_resolution": "unresolved",
                    "error": f"read_error:{type(exc).__name__}:{exc}",
                }
            )
            continue

        ts_ms, ts_resolution = _resolve_snapshot_timestamp_ms(path=path, payload=payload)
        if ts_ms is None:
            exclusion_counts["unresolved_source_timestamp"] += 1
            source_stats.append(
                {
                    "source_id": source_id,
                    "source_path": str(path),
                    "rows_total": 0,
                    "rows_converted": 0,
                    "rows_excluded": 0,
                    "timestamp_resolution": "unresolved",
                    "error": "unresolved_source_timestamp",
                }
            )
            continue

        rows = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            exclusion_counts["source_rows_not_list"] += 1
            source_stats.append(
                {
                    "source_id": source_id,
                    "source_path": str(path),
                    "rows_total": 0,
                    "rows_converted": 0,
                    "rows_excluded": 0,
                    "timestamp_resolution": ts_resolution,
                    "error": "source_rows_not_list",
                }
            )
            continue

        for raw in rows:
            src_rows += 1
            if not isinstance(raw, dict):
                src_excluded["row_not_object"] += 1
                continue

            symbol = str(raw.get("ticker", raw.get("symbol", "")) or "").strip()
            if len(symbol) <= 0:
                src_excluded["missing_symbol"] += 1
                continue

            regime = str(raw.get("regime", "") or "").strip()
            s_uf = _to_float(raw.get("S_UF"))
            r_uf = _to_float(raw.get("R_UF"))
            d = _to_float(raw.get("D_k"))
            m = _to_float(raw.get("M_k"))
            r_rev = _to_float(raw.get("R_rev_k"))
            u_star = _to_float(raw.get("U_star_k"))
            c = _to_float(raw.get("C_k"))
            p = _to_float(raw.get("P_k"))
            b = _to_float(raw.get("B_k"))
            price = _to_float(raw.get("price"))

            required = {
                "regime": regime,
                "S_UF": s_uf,
                "R_UF": r_uf,
                "D_k": d,
                "M_k": m,
                "R_rev_k": r_rev,
                "U_star_k": u_star,
                "C_k": c,
                "P_k": p,
                "B_k": b,
                "price": price,
            }
            missing = [k for k, v in required.items() if (v is None if k != "regime" else len(regime) <= 0)]
            if len(missing) > 0:
                src_excluded["ambiguous_missing_required_fields"] += 1
                continue

            row = SnapshotRow(
                source_id=source_id,
                source_path=str(path),
                source_timestamp_resolution=ts_resolution,
                ts_ms=int(ts_ms),
                ts_iso=_iso_from_ms(int(ts_ms)),
                symbol=symbol,
                regime=regime,
                s_uf=float(s_uf),
                r_uf=float(r_uf),
                d=float(d),
                m=float(m),
                r_rev=float(r_rev),
                u_star=float(u_star),
                c=float(c),
                p=float(p),
                b=float(b),
                price=float(price),
            )
            rows_raw.append(row)
            per_symbol_points[symbol].append((int(ts_ms), float(price)))

        excluded_count = int(sum(src_excluded.values()))
        for k, v in src_excluded.items():
            exclusion_counts[k] += int(v)

        source_stats.append(
            {
                "source_id": source_id,
                "source_path": str(path),
                "rows_total": int(src_rows),
                "rows_converted": int(src_rows - excluded_count),
                "rows_excluded": excluded_count,
                "timestamp_resolution": ts_resolution,
                "exclusion_counts": {k: int(v) for k, v in src_excluded.items()},
            }
        )

    # Build per-symbol ordered unique timelines for forward return derivation.
    timelines: Dict[str, List[Tuple[int, float]]] = {}
    for sym, points in per_symbol_points.items():
        uniq: Dict[int, float] = {}
        for ts_ms, px in points:
            if ts_ms not in uniq:
                uniq[ts_ms] = px
        ordered = sorted(uniq.items(), key=lambda t: t[0])
        timelines[sym] = ordered

    key_to_row: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    key_to_hash: Dict[Tuple[str, str, str], str] = {}
    conflicts: List[Dict[str, Any]] = []
    duplicate_same_payload = 0
    excluded_no_future = 0

    for base in rows_raw:
        timeline = timelines.get(base.symbol, [])
        idx_map = {ts: i for i, (ts, _) in enumerate(timeline)}
        i0 = idx_map.get(base.ts_ms)
        if i0 is None:
            exclusion_counts["timeline_missing_base_timestamp"] += 1
            continue

        for h in horizons:
            i1 = int(i0 + int(h))
            if i1 >= len(timeline):
                excluded_no_future += 1
                continue

            p0 = float(base.price)
            p1 = float(timeline[i1][1])
            if p0 <= 0.0:
                exclusion_counts["invalid_base_price"] += 1
                continue

            fwd = float((p1 / p0) - 1.0)
            decision = _classify_policy(base.s_uf, base.d)
            act = _action_return(decision, fwd)

            out = {
                "symbol": base.symbol,
                "horizon": str(int(h)),
                "decision_timestamp": base.ts_iso,
                "decision": decision,
                "regime": base.regime,
                "S_UF": float(base.s_uf),
                "R_UF": float(base.r_uf),
                "D": float(base.d),
                "M": float(base.m),
                "R_rev": float(base.r_rev),
                "U_star": float(base.u_star),
                "C": float(base.c),
                "C_k": float(base.c),
                "P": float(base.p),
                "B": float(base.b),
                "price_at_decision": float(base.price),
                "forward_return": float(fwd),
                "action_return": float(act),
                "pattern_key": _pattern_key(base.regime, base.d, base.p, base.r_rev, base.b),
                "source_id": base.source_id,
                "source_path": base.source_path,
                "source_timestamp_resolution": base.source_timestamp_resolution,
            }

            key = (out["decision_timestamp"], out["symbol"], out["horizon"])
            hsh = _row_hash(out)
            if key not in key_to_row:
                key_to_row[key] = out
                key_to_hash[key] = hsh
            else:
                if key_to_hash[key] == hsh:
                    duplicate_same_payload += 1
                else:
                    conflicts.append(
                        {
                            "decision_timestamp": key[0],
                            "symbol": key[1],
                            "horizon": key[2],
                            "existing_source_id": key_to_row[key]["source_id"],
                            "new_source_id": out["source_id"],
                            "existing_decision": key_to_row[key]["decision"],
                            "new_decision": out["decision"],
                            "existing_pattern_key": key_to_row[key]["pattern_key"],
                            "new_pattern_key": out["pattern_key"],
                        }
                    )
                    key_to_row.pop(key, None)
                    key_to_hash.pop(key, None)

    converted_rows = [key_to_row[k] for k in sorted(key_to_row.keys(), key=lambda t: (t[0], t[1], int(t[2])))]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_conflicts_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROWTRACE_COLUMNS)
        w.writeheader()
        for row in converted_rows:
            w.writerow({k: row.get(k, "") for k in ROWTRACE_COLUMNS})

    with out_conflicts_csv.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "decision_timestamp",
            "symbol",
            "horizon",
            "existing_source_id",
            "new_source_id",
            "existing_decision",
            "new_decision",
            "existing_pattern_key",
            "new_pattern_key",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in conflicts:
            w.writerow(row)

    by_h = Counter(str(r["horizon"]) for r in converted_rows)
    by_ts = Counter(str(r["decision_timestamp"]) for r in converted_rows)

    manifest = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "snapshot_archive_to_rowtrace_conversion",
        "inputs": {
            "backfill_plan": str(Path(str(args.backfill_plan)).resolve()) if str(args.backfill_plan).strip() else None,
            "snapshot_sources_json": str(Path(str(args.snapshot_sources_json)).resolve()) if str(args.snapshot_sources_json).strip() else None,
            "horizons": [int(h) for h in horizons],
        },
        "conversion_contract": {
            "preserve_decision_timestamp_exactly": True,
            "preserve_symbol_horizon_exactly": True,
            "preserve_source_provenance_per_row": True,
            "reject_ambiguous_mappings": True,
            "requires_future_price_from_snapshot_timeline": True,
        },
        "source_stats": source_stats,
        "exclusion_counts": {k: int(v) for k, v in exclusion_counts.items()},
        "excluded_no_future_price_rows": int(excluded_no_future),
        "duplicate_same_payload_collapsed": int(duplicate_same_payload),
        "conflict_rows_excluded": int(len(conflicts)),
        "rows_written": int(len(converted_rows)),
        "rows_by_horizon": {k: int(v) for k, v in sorted(by_h.items(), key=lambda kv: kv[0])},
        "unique_timestamps_written": int(len(by_ts)),
        "top_timestamps": [{"decision_timestamp": ts, "rows": int(n)} for ts, n in by_ts.most_common(20)],
        "outputs": {
            "rowtrace_csv": str(out_csv),
            "conflicts_csv": str(out_conflicts_csv),
            "manifest_json": str(out_manifest),
        },
    }

    report_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(str(out_csv))
    print(str(out_conflicts_csv))
    print(str(out_manifest))
    print(
        json.dumps(
            {
                "rows_written": int(len(converted_rows)),
                "conflict_rows_excluded": int(len(conflicts)),
                "excluded_no_future_price_rows": int(excluded_no_future),
                "unresolved_source_timestamp": int(exclusion_counts.get("unresolved_source_timestamp", 0)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
