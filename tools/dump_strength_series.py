#!/usr/bin/env python3
"""C2 (042): Dump strength series from EFS snapshots for wC Step-3 derivation.
Outputs (timestamp, total_strength, n_fast, n_slow, n_released, n_live) CSV.
Run on-container or point STATE_DIR to local EFS copy. No deploy needed."""

import json, os, sys, glob
from collections import defaultdict

STATE_DIR = os.environ.get("GUALALOOM_STATE_DIR", "state")
BACKUP_DIR = os.path.join(STATE_DIR, "backups")

print("timestamp,total_strength,n_live,n_fast,n_slow,n_released")

# Scan snapshot directories
if os.path.isdir(BACKUP_DIR):
    snap_dirs = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")))
else:
    snap_dirs = []

# Also include current state
dirs_to_check = snap_dirs + [STATE_DIR]

for d in dirs_to_check:
    atlas_path = os.path.join(d, "guala_atlas.json")
    if not os.path.exists(atlas_path):
        continue
    try:
        with open(atlas_path) as f:
            raw = json.load(f)
        data = raw.get("data", raw)
        entries = data.get("entries", {})

        total_str = 0.0
        n_live = 0
        n_fast = 0
        n_slow = 0
        n_released = 0

        for chi_k, es in entries.items():
            for e in es:
                s = e.get("strength", 0)
                if s >= 0.02:
                    total_str += s
                    n_live += 1
                    if e.get("released", False):
                        n_released += 1
                    elif e.get("dwell_ticks", 0) >= 4:
                        n_slow += 1
                    else:
                        n_fast += 1

        # Timestamp from directory name or file mtime
        dirname = os.path.basename(d)
        if dirname.startswith("20"):
            ts = dirname
        else:
            ts = os.path.getmtime(atlas_path)
            from datetime import datetime
            ts = datetime.fromtimestamp(ts).strftime("%Y-%m-%d_%H-%M-%S")

        print(f"{ts},{total_str:.2f},{n_live},{n_fast},{n_slow},{n_released}")
    except Exception as e:
        print(f"# ERROR {d}: {e}", file=sys.stderr)
