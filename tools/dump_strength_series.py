#!/usr/bin/env python3
"""C2/1.10 (047): Dump strength series from ALL EFS snapshots.
Outputs per row: timestamp, tick, total_strength, S_fast, S_slow, n_fast, n_slow, n_released.
Run on-container or point STATE_DIR to local EFS copy."""

import json, os, sys, glob

STATE_DIR = os.environ.get("GUALALOOM_STATE_DIR", "state")
BACKUP_DIR = os.path.join(STATE_DIR, "backups")

print("timestamp,tick,total_strength,S_fast,S_slow,n_fast,n_slow,n_released")

dirs = []
if os.path.isdir(BACKUP_DIR):
    dirs = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")))
dirs.append(STATE_DIR)  # current state last

for d in dirs:
    atlas_path = os.path.join(d, "guala_atlas.json")
    core_path = os.path.join(d, "guala_core.json")
    if not os.path.exists(atlas_path):
        continue
    try:
        with open(atlas_path) as f:
            raw = json.load(f)
        data = raw.get("data", raw)
        entries = data.get("entries", {})

        tick = data.get("tick", 0)
        # Also try core for tick
        if os.path.exists(core_path):
            try:
                with open(core_path) as f:
                    core = json.load(f)
                core_data = core.get("data", core)
                tick = max(tick, core_data.get("tick", 0))
            except Exception:
                pass

        total_str = 0.0
        s_fast = 0.0
        s_slow = 0.0
        n_fast = 0
        n_slow = 0
        n_released = 0

        for chi_k, es in entries.items():
            for e in es:
                s = e.get("strength", 0)
                if s < 0.02:
                    continue
                total_str += s
                if e.get("released", False):
                    n_released += 1
                elif e.get("dwell_ticks", 0) >= 4:
                    n_slow += 1
                    s_slow += s
                else:
                    n_fast += 1
                    s_fast += s

        dirname = os.path.basename(d)
        if dirname.startswith("20"):
            ts = dirname
        else:
            ts = os.path.getmtime(atlas_path)
            from datetime import datetime
            ts = datetime.fromtimestamp(ts).strftime("%Y-%m-%d_%H-%M-%S")

        print(f"{ts},{tick},{total_str:.2f},{s_fast:.2f},{s_slow:.2f},{n_fast},{n_slow},{n_released}")
    except Exception as e:
        print(f"# ERROR {d}: {e}", file=sys.stderr)
