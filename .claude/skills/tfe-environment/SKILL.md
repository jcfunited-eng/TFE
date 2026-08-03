---
name: tfe-environment
description: The TFE machine environment — devcontainer, mounts, rebuild behavior, backups, compute limits, data plumbing. Load after any rebuild, crash, or when anything environmental misbehaves.
---

# Environment

The environment is hostile by default: container rebuilds happen
without warning and kill everything not on a mount. Design and operate
accordingly.

## What survives a rebuild vs what dies
SURVIVES (bind mounts, host-backed):
- /workspaces/Tao_Financial_Engine (the repo + parquet stores)
- /root/.claude (memory, transcripts — mounted to E:\TFEBackup\ClaudeHome)
- /mnt/tfebackup (the backup drive), /root/.aws (read-only), /root/.codex
DIES:
- Every running process (runners, background compute, nohup'd jobs)
- /root/.claude.json (auto-restored from /mnt/tfebackup/root-claude.json
  by the devcontainer postCreateCommand; refresh that snapshot after
  granting new approvals: `cp /root/.claude.json /mnt/tfebackup/root-claude.json`)
- Anything apt/pip installed beyond the image (pandas/numpy/pyarrow and
  git are baked into .devcontainer/Dockerfile — extend the Dockerfile,
  not the running container, for anything needed long-term)

## After every rebuild (checklist)
1. `python3 -c "import pandas"` — if it fails the image is stale;
   `pip install pandas numpy pyarrow` and flag the Dockerfile.
2. Restart both runners (tfe-daily-ops), re-arm session schedules.
3. Check background tasks that were mid-flight: read their partial
   logs; never assume completion.
4. Verify /root/.claude.json has per-project settings
   (`python3 -c "import json; print('projects' in json.load(open('/root/.claude.json')))"`).

## Compute envelope
20 cores, 32GB RAM. Shard field-scale kernel runs 8-way; stream over
typed arrays in chunks (an OOM killed a 30GB tuple materialization and
took the runners with it). Long jobs go through the harness background
mechanism, not bare nohup.

## Data plumbing
- Massive/Polygon: MASSIVE_API_KEY in .env; grouped-daily endpoint for
  store appends; per-symbol aggs for intraday; ~6 req/s polite rate.
- Alpaca: .env keys are DATA-ONLY; trading keys via Secrets Manager
  (tfe-prod-touch). 15-min live bars: IEX feed.
- Store freshness: research stores are frozen snapshots; the live
  store refreshes nightly (tools/ch4_store_refresh.py) with declared
  seam-break drops. PYTHONHASHSEED matters for any hash()-touched
  reproduction — the codebase standard is blake2b, never hash().
