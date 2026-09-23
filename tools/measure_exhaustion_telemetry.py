"""Read-only observation of displacement changes and the complete delivered tuple.

Database publication rows are NOT market bars. This tool does not infer tau_in,
ignition, energy or an exit timer from publication counts. It retains intervening
labels and invalid observations instead of joining across them. Equal D_k does
not imply that the remaining field is stationary.

Use --receipts FILE.jsonl.gz [...] for retained as-of field histories, or --database
with PGHOST/PGDATABASE/PGUSER/PGPASSWORD for publication history. Output is JSON;
--output creates a new file and refuses to overwrite existing evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

FIELDS = ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")


def field_errors(field):
    errors = []
    for key in FIELDS:
        value = field.get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            errors.append(key)
    return errors


def measure(observations, clock):
    """Preserve all observations and adjacent comparisons, without state inference."""
    rows = list(observations)
    previous = {}
    pairs = []
    for row in rows:
        symbol = row["symbol"]
        stamp = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        prior = previous.get(symbol)
        if prior is not None:
            prior_row, prior_stamp = prior
            if stamp <= prior_stamp:
                raise ValueError(f"non-increasing observation time for {symbol}")
            invalid_before = field_errors(prior_row["field"])
            invalid_after = field_errors(row["field"])
            pair = {"symbol": symbol, "before": prior_row["observed_at"],
                    "after": row["observed_at"],
                    "invalid_before": invalid_before, "invalid_after": invalid_after}
            if not invalid_before and not invalid_after:
                changed = [k for k in FIELDS if prior_row["field"][k] != row["field"][k]]
                delta = row["field"]["D_k"] - prior_row["field"]["D_k"]
                pair.update(delta_D_k=delta, changed_fields=changed,
                            equal_D_with_other_field_changes=delta == 0 and bool(changed))
            pairs.append(pair)
        previous[symbol] = (row, stamp)
    valid = [p for p in pairs if "delta_D_k" in p]
    return {
        "clock": clock,
        "authority": "observation only; neither quiescence nor strategy validation",
        "bar_continuity_verified": False,
        "observation_count": len(rows), "adjacent_pair_count": len(pairs),
        "valid_pair_count": len(valid),
        "equal_D_with_other_field_changes": sum(p["equal_D_with_other_field_changes"] for p in valid),
        "observations": rows, "adjacent_pairs": pairs,
    }


def read_receipts(paths):
    observations, provenance = [], []
    common_hashes = None
    for path in paths:
        path = Path(path)
        provenance.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with gzip.open(path, "rt") as stream:
            for line in stream:
                receipt = json.loads(line)
                hashes = receipt["kernel_sha256"]
                if common_hashes is None:
                    common_hashes = hashes
                if hashes != common_hashes:
                    raise ValueError("receipts contain different kernel versions")
                field = receipt["gate_history"][-1]["l4"]
                observations.append({
                    "symbol": receipt["symbol"], "observed_at": receipt["as_of"],
                    "field": {k: field.get(k) for k in FIELDS},
                    "context": receipt["adapter_context"],
                    "gate": field["gate"], "input_sha256": receipt["input_sha256"],
                })
    return observations, {"files": provenance, "kernel_sha256": common_hashes}


def fetch_history(cursor, days):
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("history days must be a positive integer")
    # Select the current cohort once; preserve ALL its historical labels.
    # Publication timestamps remain publication timestamps, never bar dates.
    cursor.execute("""
        SELECT h.ticker, h.generated_at_utc, h.decision_label, h.snapshot_row_json
        FROM runtime_decisions_history h
        WHERE h.ticker IN (
            SELECT ticker FROM runtime_decisions_latest
            WHERE decision_label = 'Accumulate'
        )
        AND h.generated_at_utc >= NOW() - (%s * INTERVAL '1 day')
        ORDER BY h.ticker, h.generated_at_utc ASC
    """, (days,))
    observations = []
    for symbol, stamp, label, snapshot in cursor:
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        if not isinstance(snapshot, dict):
            raise ValueError(f"invalid snapshot object for {symbol}")
        observations.append({"symbol": symbol, "observed_at": stamp.isoformat(),
                             "label": label,
                             "field": {k: snapshot.get(k) for k in FIELDS},
                             "snapshot": snapshot})
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--receipts", nargs="+", type=Path)
    source.add_argument("--database", action="store_true")
    parser.add_argument("--history-days", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        raise FileExistsError(args.output)
    if args.receipts:
        observations, provenance = read_receipts(args.receipts)
        clock = "retained as-of observation dates; adjusted-data vintage not certified"
    else:
        import psycopg2
        required = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise ValueError("missing environment variables: " + ", ".join(missing))
        conn = psycopg2.connect("")  # libpq reads PG* variables without printing secrets.
        try:
            conn.set_session(readonly=True)
            with conn.cursor() as cursor:
                observations = fetch_history(cursor, args.history_days)
        finally:
            conn.close()
        provenance = {"source": "runtime_decisions_history", "history_days": args.history_days}
        clock = "database publication timestamps; not market-bar timestamps"
    if not observations:
        raise ValueError("no historical observations; no latest-row fallback")
    report = measure(observations, clock)
    report["provenance"] = provenance
    report["observer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    encoded = json.dumps(report, indent=2, allow_nan=False, default=str) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(encoded)
        print(json.dumps({k: report[k] for k in ("observation_count", "adjacent_pair_count",
                                               "valid_pair_count", "equal_D_with_other_field_changes")}))
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
