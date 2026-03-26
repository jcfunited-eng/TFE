#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_repo_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


_load_repo_env(REPO_ROOT / ".env")

from structural_recency_snapshot import build_structural_recency_payload, history_metadata_from_bars
from tfe_bar_integrity import DEFAULT_MIN_PRICE_FLOOR, sanitize_daily_bars
from tfe_market_data_service import Bar, HistoryRequest, Timespan
from uf_core.uf_structural_engine import compute_structural_state
from unified_market_data_service import get_unified_market_data


BACKUPS_ROOT = REPO_ROOT / "backups"
RUNTIME_ROOT = BACKUPS_ROOT / "runtime"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"

DEFAULT_DB_PATH = RUNTIME_ROOT / "dsf_historical_full_surface_snapshot_archive_v2.sqlite"
DEFAULT_NOTE_PATH = REPO_ROOT / "DSF_HISTORICAL_FULL_SURFACE_SNAPSHOT_ARCHIVE.md"
DEFAULT_YEARS_HISTORY = 5
SNAPSHOT_FAMILY_PATTERNS = [
    "restore-snapshot-*",
    "predeploy-prod-restore-*",
    "baseline-backup-*",
    "rollback-pack-*",
    "l0l5-pre-correction-artifacts-*",
]

REQUIRED_FULL_SURFACE_KEYS = {
    "ticker",
    "asset_type",
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
}


@dataclass(frozen=True)
class SnapshotSource:
    snapshot_timestamp_utc: str
    snapshot_rows_path: Path
    snapshot_report_path: Path
    rows_written: int
    has_full_surface: bool


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_rows_candidates(snapshot_dir: Path) -> list[Path]:
    return [
        snapshot_dir / "uf_snapshot.json",
        snapshot_dir / "captured" / "uf_snapshot.json",
    ]


def _report_path_for_snapshot_dir(snapshot_dir: Path) -> Path | None:
    candidates = [
        snapshot_dir / "uf_snapshot_rebuild_report.json",
        snapshot_dir / "captured" / "uf_snapshot_rebuild_report.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def discover_snapshot_sources() -> list[SnapshotSource]:
    sources: list[SnapshotSource] = []
    seen_rows_paths: set[str] = set()

    for pattern in SNAPSHOT_FAMILY_PATTERNS:
        for snapshot_dir in sorted(BACKUPS_ROOT.glob(pattern)):
            report_path = _report_path_for_snapshot_dir(snapshot_dir)
            if report_path is None:
                continue
            rows_path = None
            for candidate in _snapshot_rows_candidates(snapshot_dir):
                if candidate.exists():
                    rows_path = candidate
                    break
            if rows_path is None:
                continue
            if str(rows_path) in seen_rows_paths:
                continue
            seen_rows_paths.add(str(rows_path))

            try:
                rows = _load_json(rows_path)
                report = _load_json(report_path)
            except Exception:
                continue
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                continue
            ts = str(report.get("generated_at_utc") or "").strip()
            if not ts:
                continue
            keys = set(rows[0].keys())
            has_full_surface = not bool(REQUIRED_FULL_SURFACE_KEYS - keys)
            sources.append(
                SnapshotSource(
                    snapshot_timestamp_utc=ts,
                    snapshot_rows_path=rows_path,
                    snapshot_report_path=report_path,
                    rows_written=int(report.get("rows_written") or len(rows)),
                    has_full_surface=has_full_surface,
                )
            )
    return sources


def grouped_universe_by_timestamp(sources: list[SnapshotSource]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for source in sources:
        group = grouped.setdefault(
            source.snapshot_timestamp_utc,
            {
                "snapshot_timestamp_utc": source.snapshot_timestamp_utc,
                "sources": [],
                "symbols": {},
                "partial_surface_sources": 0,
                "full_surface_sources": 0,
            },
        )
        group["sources"].append(
            {
                "snapshot_rows_path": str(source.snapshot_rows_path),
                "snapshot_report_path": str(source.snapshot_report_path),
                "rows_written": source.rows_written,
                "has_full_surface": source.has_full_surface,
            }
        )
        if source.has_full_surface:
            group["full_surface_sources"] += 1
        else:
            group["partial_surface_sources"] += 1

        rows = _load_json(source.snapshot_rows_path)
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("ticker") or "").strip().upper()
            if not symbol:
                continue
            asset_type = str(row.get("asset_type") or "unknown").strip().lower() or "unknown"
            if symbol not in group["symbols"]:
                group["symbols"][symbol] = asset_type
    return grouped


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS snapshot_runs(
            snapshot_timestamp_utc TEXT PRIMARY KEY,
            snapshot_timestamp_epoch_ms INTEGER NOT NULL,
            universe_size INTEGER NOT NULL,
            source_count INTEGER NOT NULL,
            full_surface_source_count INTEGER NOT NULL,
            partial_surface_source_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            notes_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS snapshot_run_sources(
            snapshot_timestamp_utc TEXT NOT NULL,
            snapshot_rows_path TEXT NOT NULL,
            snapshot_report_path TEXT NOT NULL,
            rows_written INTEGER NOT NULL,
            has_full_surface INTEGER NOT NULL,
            PRIMARY KEY(snapshot_timestamp_utc, snapshot_rows_path)
        );

        CREATE TABLE IF NOT EXISTS snapshot_rows(
            snapshot_timestamp_utc TEXT NOT NULL,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            price REAL,
            regime TEXT NOT NULL,
            S_UF REAL NOT NULL,
            R_UF REAL NOT NULL,
            stability_score REAL NOT NULL,
            max_dd REAL NOT NULL,
            D_k REAL NOT NULL,
            M_k REAL NOT NULL,
            R_rev_k REAL NOT NULL,
            U_star_k REAL NOT NULL,
            C_k REAL NOT NULL,
            P_k REAL NOT NULL,
            B_k REAL NOT NULL,
            bar_count INTEGER NOT NULL,
            gate_count INTEGER NOT NULL,
            active_gate_count INTEGER NOT NULL,
            decision_vector_json TEXT NOT NULL,
            decision_guard_json TEXT NOT NULL,
            integrity_dropped_json TEXT NOT NULL,
            recency_json TEXT NOT NULL,
            row_json TEXT NOT NULL,
            PRIMARY KEY(snapshot_timestamp_utc, symbol)
        );

        CREATE TABLE IF NOT EXISTS snapshot_build_errors(
            snapshot_timestamp_utc TEXT NOT NULL,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            error TEXT NOT NULL,
            PRIMARY KEY(snapshot_timestamp_utc, symbol)
        );
        """
    )
    conn.commit()


def persist_discovery(conn: sqlite3.Connection, grouped: dict[str, dict[str, Any]]) -> None:
    for ts, payload in grouped.items():
        ts_epoch_ms = int(parse_utc(ts).timestamp() * 1000.0)
        notes_json = json.dumps({"symbols": sorted(payload["symbols"].keys())})
        conn.execute(
            """
            INSERT OR REPLACE INTO snapshot_runs(
                snapshot_timestamp_utc,
                snapshot_timestamp_epoch_ms,
                universe_size,
                source_count,
                full_surface_source_count,
                partial_surface_source_count,
                status,
                notes_json
            )
            VALUES(?, ?, ?, ?, ?, ?, COALESCE((SELECT status FROM snapshot_runs WHERE snapshot_timestamp_utc = ?), 'discovered'), ?)
            """,
            (
                ts,
                ts_epoch_ms,
                len(payload["symbols"]),
                len(payload["sources"]),
                int(payload["full_surface_sources"]),
                int(payload["partial_surface_sources"]),
                ts,
                notes_json,
            ),
        )
        for source in payload["sources"]:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshot_run_sources(
                    snapshot_timestamp_utc,
                    snapshot_rows_path,
                    snapshot_report_path,
                    rows_written,
                    has_full_surface
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    source["snapshot_rows_path"],
                    source["snapshot_report_path"],
                    int(source["rows_written"]),
                    1 if source["has_full_surface"] else 0,
                ),
            )
        print(f"[discover] {ts} sources={len(payload['sources'])} universe={len(payload['symbols'])}")
    conn.commit()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _pad_decision_vector(raw_dv: Any, length: int = 6) -> list[float]:
    try:
        dv = list(raw_dv) if raw_dv is not None else []
    except Exception:
        dv = []
    if len(dv) < length:
        dv = dv + [0.0] * (length - len(dv))
    if len(dv) > length:
        dv = dv[:length]
    out: list[float] = []
    for item in dv:
        try:
            out.append(float(item))
        except Exception:
            out.append(0.0)
    return out


def _safe_vector_value(vector: list[float], index: int, default: float = 0.0) -> float:
    if index < 0 or index >= len(vector):
        return float(default)
    try:
        return float(vector[index])
    except Exception:
        return float(default)


def _sqlite_real_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def build_no_data_row(symbol: str, asset_type: str, dropped: dict[str, int], bar_count: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ticker": symbol,
        "asset_type": asset_type,
        "price": None,
        "regime": "NO_DATA",
        "S_UF": 0.0,
        "R_UF": 0.0,
        "stability_score": 0.0,
        "max_dd": 0.0,
        "decision_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "D_k": 0.0,
        "M_k": 0.0,
        "R_rev_k": 0.0,
        "U_star_k": 0.0,
        "C_k": 0.0,
        "P_k": 0.0,
        "B_k": 0.0,
        "bar_count": int(bar_count),
        "gate_count": 0,
        "active_gate_count": 0,
        "decision_guard": {"gate_unlock_transient_neutralized": False},
        "integrity_dropped": dropped,
    }
    row.update(
        build_structural_recency_payload(
            symbol=symbol,
            current_state=row,
            history_available_steps=max(0, int(bar_count) - 1),
            ts_gap_days_from_prev=0.0,
        )
    )
    return row


def build_snapshot_row(symbol: str, asset_type: str, bars: list[Bar], dropped: dict[str, int]) -> dict[str, Any]:
    if not bars:
        return build_no_data_row(symbol=symbol, asset_type=asset_type, dropped=dropped, bar_count=0)

    state = compute_structural_state(symbol, bars)
    history_meta = history_metadata_from_bars(bars)

    decision_vector = _pad_decision_vector(state.get("decision_vector"))
    d_k = state.get("D_k")
    m_k = state.get("M_k")
    r_rev_k = state.get("R_rev_k")
    u_star_k = state.get("U_star_k")
    c_k = state.get("C_k")
    p_k = state.get("P_k")
    b_k = state.get("B_k")

    if d_k is None:
        d_k = _safe_vector_value(decision_vector, 0, 0.0)
    if m_k is None:
        m_k = _safe_vector_value(decision_vector, 1, 0.0)
    if r_rev_k is None:
        r_rev_k = _safe_vector_value(decision_vector, 2, 0.0)
    if u_star_k is None:
        u_star_k = _safe_vector_value(decision_vector, 3, 0.0)
    if c_k is None:
        c_k = 0.0
    if p_k is None:
        p_k = _safe_vector_value(decision_vector, 4, 0.0)
    if b_k is None:
        b_k = _safe_vector_value(decision_vector, 5, 0.0)

    row: dict[str, Any] = {
        "ticker": symbol,
        "asset_type": asset_type,
        "price": _sqlite_real_or_none(state.get("last_close")),
        "regime": str(state.get("regime", "UNKNOWN")),
        "S_UF": _safe_float(state.get("S_UF"), 0.0),
        "R_UF": _safe_float(state.get("R_UF"), 0.0),
        "stability_score": _safe_float(state.get("stability_score"), 0.0),
        "max_dd": _safe_float(state.get("max_drawdown"), 0.0),
        "decision_vector": decision_vector,
        "D_k": _safe_float(d_k, 0.0),
        "M_k": _safe_float(m_k, 0.0),
        "R_rev_k": _safe_float(r_rev_k, 0.0),
        "U_star_k": _safe_float(u_star_k, 0.0),
        "C_k": _safe_float(c_k, 0.0),
        "P_k": _safe_float(p_k, 0.0),
        "B_k": _safe_float(b_k, 0.0),
        "bar_count": int(len(bars)),
        "gate_count": _safe_int(state.get("gate_count"), 0),
        "active_gate_count": _safe_int(state.get("active_gate_count"), 0),
        "decision_guard": state.get("decision_guard", {}) if isinstance(state.get("decision_guard"), dict) else {},
        "integrity_dropped": dropped,
    }
    row.update(
        build_structural_recency_payload(
            symbol=symbol,
            current_state=row,
            history_available_steps=int(history_meta["history_available_steps"]),
            ts_gap_days_from_prev=float(history_meta["ts_gap_days_from_prev"]),
        )
    )
    return row


def fetch_raw_bars(symbol: str, start: datetime, end: datetime, client: Any) -> list[Bar]:
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )
    result = client.get_history(req)
    bars = list(getattr(result, "bars", []) or [])
    return sorted(bars, key=lambda bar: bar.timestamp)


def _slice_clean_bars(raw_bars: list[Bar], as_of: datetime) -> tuple[list[Bar], dict[str, int]]:
    sliced = [bar for bar in raw_bars if getattr(bar, "timestamp", None) is not None and bar.timestamp <= as_of]
    cleaned, dropped = sanitize_daily_bars(sliced, min_price_floor=DEFAULT_MIN_PRICE_FLOOR)
    usable: list[Bar] = []
    for bar in cleaned:
        try:
            float(getattr(bar, "close", None))
        except Exception:
            continue
        usable.append(bar)
    usable.sort(key=lambda bar: bar.timestamp)
    return usable, dropped


def insert_snapshot_row(conn: sqlite3.Connection, snapshot_timestamp_utc: str, row: dict[str, Any]) -> None:
    recency = {key: row[key] for key in row.keys() if "steps_since" in key or key == "structural_recency_schema_version"}
    conn.execute(
        """
        INSERT OR REPLACE INTO snapshot_rows(
            snapshot_timestamp_utc,
            symbol,
            asset_type,
            price,
            regime,
            S_UF,
            R_UF,
            stability_score,
            max_dd,
            D_k,
            M_k,
            R_rev_k,
            U_star_k,
            C_k,
            P_k,
            B_k,
            bar_count,
            gate_count,
            active_gate_count,
            decision_vector_json,
            decision_guard_json,
            integrity_dropped_json,
            recency_json,
            row_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_timestamp_utc,
            str(row["ticker"]),
            str(row["asset_type"]),
            row["price"],
            str(row["regime"]),
            float(row["S_UF"]),
            float(row["R_UF"]),
            float(row["stability_score"]),
            float(row["max_dd"]),
            float(row["D_k"]),
            float(row["M_k"]),
            float(row["R_rev_k"]),
            float(row["U_star_k"]),
            float(row["C_k"]),
            float(row["P_k"]),
            float(row["B_k"]),
            int(row["bar_count"]),
            int(row["gate_count"]),
            int(row["active_gate_count"]),
            json.dumps(row["decision_vector"]),
            json.dumps(row["decision_guard"]),
            json.dumps(row["integrity_dropped"]),
            json.dumps(recency),
            json.dumps(row),
        ),
    )


def insert_error(conn: sqlite3.Connection, snapshot_timestamp_utc: str, symbol: str, asset_type: str, error: str) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO snapshot_build_errors(
            snapshot_timestamp_utc,
            symbol,
            asset_type,
            error
        )
        VALUES(?, ?, ?, ?)
        """,
        (snapshot_timestamp_utc, symbol, asset_type, error),
    )


def build_archive(
    conn: sqlite3.Connection,
    grouped: dict[str, dict[str, Any]],
    years_history: int,
    max_symbols: int,
) -> dict[str, Any]:
    snapshot_timestamps = sorted(grouped.keys(), key=parse_utc)
    earliest_ts = parse_utc(snapshot_timestamps[0])
    latest_ts = parse_utc(snapshot_timestamps[-1])
    start = earliest_ts - timedelta(days=int(years_history) * 365)
    end = latest_ts

    universe_by_symbol: dict[str, str] = {}
    membership: dict[str, list[str]] = defaultdict(list)
    for ts in snapshot_timestamps:
        for symbol, asset_type in grouped[ts]["symbols"].items():
            universe_by_symbol.setdefault(symbol, asset_type)
            membership[symbol].append(ts)

    symbols = sorted(universe_by_symbol.keys())
    if max_symbols > 0:
        symbols = symbols[:max_symbols]

    client = get_unified_market_data()
    fetched_symbols = 0
    built_rows = 0
    error_rows = 0

    for idx, symbol in enumerate(symbols, start=1):
        asset_type = universe_by_symbol[symbol]
        print(f"[build] {idx}/{len(symbols)} {symbol}")
        try:
            raw_bars = fetch_raw_bars(symbol=symbol, start=start, end=end, client=client)
        except Exception as exc:
            for ts in membership[symbol]:
                insert_error(conn, ts, symbol, asset_type, f"history_fetch_failed: {type(exc).__name__}: {exc}")
                error_rows += 1
            conn.commit()
            continue

        fetched_symbols += 1
        for ts in membership[symbol]:
            as_of = parse_utc(ts)
            try:
                bars, dropped = _slice_clean_bars(raw_bars, as_of=as_of)
                row = build_snapshot_row(symbol=symbol, asset_type=asset_type, bars=bars, dropped=dropped)
                insert_snapshot_row(conn, ts, row)
                built_rows += 1
            except Exception as exc:
                insert_error(conn, ts, symbol, asset_type, f"row_build_failed: {type(exc).__name__}: {exc}")
                error_rows += 1
        conn.commit()

    expected_selected_by_ts = {
        ts: sum(1 for symbol in symbols if ts in membership[symbol])
        for ts in snapshot_timestamps
    }
    for ts in snapshot_timestamps:
        built_for_ts = conn.execute(
            "SELECT COUNT(*) FROM snapshot_rows WHERE snapshot_timestamp_utc = ?",
            (ts,),
        ).fetchone()[0]
        status = "built" if int(built_for_ts) == int(expected_selected_by_ts[ts]) else "partial"
        conn.execute(
            "UPDATE snapshot_runs SET status = ? WHERE snapshot_timestamp_utc = ?",
            (status, ts),
        )
    conn.commit()

    return {
        "snapshot_timestamps": snapshot_timestamps,
        "start_utc": start.isoformat().replace("+00:00", "Z"),
        "end_utc": end.isoformat().replace("+00:00", "Z"),
        "symbol_count_selected": len(symbols),
        "fetched_symbols": fetched_symbols,
        "built_rows": built_rows,
        "error_rows": error_rows,
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# DSF Historical Full-Surface Snapshot Archive",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- archive_db_path: `{summary['archive_db_path']}`",
        f"- snapshot_timestamps: `{summary['snapshot_timestamps']}`",
        f"- selected_symbol_count: `{summary['build']['symbol_count_selected']}`",
        f"- fetched_symbols: `{summary['build']['fetched_symbols']}`",
        f"- built_rows: `{summary['build']['built_rows']}`",
        f"- error_rows: `{summary['build']['error_rows']}`",
        "",
        "## Snapshot Runs",
        "",
    ]
    for run in summary["runs"]:
        lines.append(
            f"- `{run['snapshot_timestamp_utc']}` universe=`{run['universe_size']}` sources=`{run['source_count']}` "
            f"full_surface_sources=`{run['full_surface_source_count']}` partial_surface_sources=`{run['partial_surface_source_count']}` "
            f"status=`{run['status']}`"
        )
    return "\n".join(lines)


def write_note(path: Path) -> None:
    text = """# DSF Historical Full-Surface Snapshot Archive

This lane exists because the repo did not contain a historical series of fixed snapshots that all carried the frozen primitive surface:

- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`
- `bar_count`

Direct build path:

1. archived `backups/**/uf_snapshot.json` supplies the historical universe membership for each archived snapshot timestamp
2. archived `uf_snapshot_rebuild_report.json` supplies the exact snapshot timestamp
3. adjusted daily bars are fetched only up to that timestamp
4. `compute_structural_state(symbol, bars)` rebuilds the full primitive surface as of that historical date
5. rebuilt rows are stored in a local SQLite archive

Important honesty:

- this is a local database-centered archive because the historical Postgres lane does not exist in this environment
- older archived snapshots may be partial-surface only; they are used for universe membership and timestamp only, not as decision authority
- the frozen primitive is not changed by this lane
"""
    path.write_text(text, encoding="utf-8")


def run_slack(summary_json: Path) -> None:
    payload = {"text": f"Codex completed DSF historical full-surface snapshot archive lane. summary={summary_json.name}"}
    if SLACK_SCRIPT.exists():
        subprocess.run(
            [str(SLACK_SCRIPT)],
            cwd=str(REPO_ROOT),
            input=json.dumps(payload) + "\n",
            text=True,
            check=True,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a historical full-surface fixed-snapshot archive for the frozen DSF primitive.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--note-path", default=str(DEFAULT_NOTE_PATH))
    parser.add_argument("--years-history", type=int, default=DEFAULT_YEARS_HISTORY)
    parser.add_argument("--max-symbols", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    os.chdir(REPO_ROOT)
    args = parse_args()
    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    note_path = Path(args.note_path)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    stamp = utc_stamp()
    summary_json = RUNTIME_ROOT / f"dsf_historical_full_surface_snapshot_archive_summary_{stamp}.json"
    summary_md = RUNTIME_ROOT / f"dsf_historical_full_surface_snapshot_archive_summary_{stamp}.md"

    sources = discover_snapshot_sources()
    if not sources:
        raise SystemExit("no archived uf_snapshot.json sources with rebuild reports were found under backups/")

    grouped = grouped_universe_by_timestamp(sources)
    if not grouped:
        raise SystemExit("no grouped snapshot timestamps were discovered from archived snapshot sources")

    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        persist_discovery(conn, grouped)
        build = build_archive(
            conn=conn,
            grouped=grouped,
            years_history=int(args.years_history),
            max_symbols=int(args.max_symbols),
        )
        runs = [
            {
                "snapshot_timestamp_utc": row[0],
                "universe_size": int(row[1]),
                "source_count": int(row[2]),
                "full_surface_source_count": int(row[3]),
                "partial_surface_source_count": int(row[4]),
                "status": str(row[5]),
            }
            for row in conn.execute(
                """
                SELECT snapshot_timestamp_utc, universe_size, source_count, full_surface_source_count, partial_surface_source_count, status
                FROM snapshot_runs
                ORDER BY snapshot_timestamp_epoch_ms ASC
                """
            ).fetchall()
        ]

    write_note(note_path)

    summary = {
        "generated_at_utc": utc_now_iso(),
        "archive_db_path": str(db_path),
        "note_path": str(note_path),
        "snapshot_timestamps": sorted(grouped.keys(), key=parse_utc),
        "build": build,
        "runs": runs,
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(markdown_summary(summary), encoding="utf-8")
    run_slack(summary_json)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
