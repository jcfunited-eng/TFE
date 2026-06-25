#!/usr/bin/env python3
"""
tools/d1_backfill_s_n.py — Gate D1 backfill script.

For rows in runtime_decisions_history where s_n IS NULL and snapshot_row_json
already has 's_n', update the column from the JSON field.

For rows where neither the column nor the JSON has s_n (rows predating Gate D1
deployment), this script does NOT recompute from bars — that would require the
full bar history and is out-of-scope for a backfill. Instead, it reports the
count of such rows as "needs_recompute".

Idempotent: re-running is a no-op on already-filled rows.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
BATCH_SIZE = 10_000


def log(m):
    print(f"[D1-BACKFILL {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    t0 = time.time()
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()

    # Count rows where s_n column is NULL
    cur.execute("SELECT COUNT(*) FROM runtime_decisions_history WHERE s_n IS NULL")
    total_null = cur.fetchone()[0]
    log(f"Rows with s_n IS NULL: {total_null:,}")

    # Count where JSON has s_n but column doesn't
    cur.execute("""
        SELECT COUNT(*) FROM runtime_decisions_history
        WHERE s_n IS NULL AND snapshot_row_json ? 's_n'
    """)
    can_backfill = cur.fetchone()[0]
    log(f"  Can backfill from JSON: {can_backfill:,}")
    log(f"  Needs recompute from bars: {total_null - can_backfill:,} (not done here)")

    if can_backfill == 0:
        log("Nothing to backfill. Done.")
        conn.close()
        return

    # Backfill in batches
    updated = 0
    failed = 0
    while True:
        cur.execute("""
            UPDATE runtime_decisions_history
               SET s_n = (snapshot_row_json->>'s_n')::DOUBLE PRECISION
             WHERE id IN (
               SELECT id FROM runtime_decisions_history
                WHERE s_n IS NULL AND snapshot_row_json ? 's_n'
               LIMIT %s
             )
        """, (BATCH_SIZE,))
        n = cur.rowcount
        conn.commit()
        updated += n
        log(f"  Updated {updated:,}/{can_backfill:,}")
        if n < BATCH_SIZE:
            break

    cur.execute("SELECT COUNT(*) FROM runtime_decisions_history WHERE s_n IS NOT NULL")
    final_non_null = cur.fetchone()[0]
    conn.close()

    log(f"Backfill complete: {updated:,} rows updated, {failed} errors")
    log(f"Final non-null s_n count: {final_non_null:,}")
    log(f"Wall time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
