---
name: tfe-daily-ops
description: Operate the TFE live channels day-to-day — runners, nightly passes, pages, books, self-healing. Use at any session start, after container rebuilds, when a pass is missed, or when a page is stale.
---

# TFE daily operations

## The two live channels (both PAPER — no real orders)
- **CH4** (daily, holds across days): engine herd_kgate_v1 in
  tools/ch4_herd_kgate_live.py. Book:
  artifacts/vtvr_observer/ch4_spring_book.json. Runner:
  tools/ch4_spring_daily_runner.sh — weekdays 21:10 UTC runs
  refresh -> herd export -> engine -> page. Friday rule: exits only.
- **CH3 shadow** (intraday, flat at every close): engine
  tools/ch3_shadow_hunter.py (its brain is the condemned triad,
  kept only as an honest record until replaced). Loop:
  tools/ch3_shadow_loop.sh — 15-min cycles 13:35-20:00 UTC, close
  pass 20:05. Log: artifacts/vtvr_observer/ch3_shadow_log.json.

## Runners die on EVERY container restart
pgrep/ps may be unavailable — check via /proc:
```
pid=$(grep -o "pid [0-9]*" artifacts/vtvr_observer/ch4_spring_runner.log | tail -1 | cut -d' ' -f2)
[ -d /proc/$pid ] && echo ALIVE || echo DEAD
```
Restart per the header line in each script (nohup ... &). Always
`set -a; source .env; set +a` context comes from the scripts themselves.

## Missed passes — run manually
- CH4 close pass: the four commands inside ch4_spring_daily_runner.sh's
  close block, in order.
- CH3 close grading: `python tools/ch3_shadow_hunter.py close`.
Verify afterward: ch4_spring_book.json last_processed == today;
ch3_shadow_log.json days has today.

## Pages (published artifacts — same URLs always)
- CH4: render `python tools/ch4_spring_page.py <out>.html`, publish to
  https://claude.ai/code/artifact/f70a03b7-3122-4f81-aabc-85b617a655a4
  (favicon chart, title "CH4 Paper Trades").
- CH3: render `python tools/ch3_shadow_page.py artifacts/vtvr_observer/ch3_shadow_page.html`,
  publish to
  https://claude.ai/code/artifact/146ba700-cfd2-4322-a727-4fadb2026fbc
  (favicon dart, title "CH3 Shadow Hunter").
Keep favicons/titles stable. A conversation that didn't publish the
artifact must pass the URL as `url`.

## After a container rebuild
Image now bakes pandas/numpy/pyarrow and auto-restores
/root/.claude.json from /mnt/tfebackup (postCreateCommand). If pip
imports fail anyway: `pip install pandas numpy pyarrow`. Memory dir
/root/.claude is a bind mount to E:\TFEBackup\ClaudeHome — survives.
Backups of the config live at /mnt/tfebackup/root-claude.json.

## Standing rules
- Never touch CH2/production behavior (see tfe-prod-touch).
- No new CH4 entries at a Friday close.
- Git lock errors: shared .git — wait/retry first; only remove
  index.lock if hours-old and 0 bytes.
- Every ship states its bound; report only what actually ran.
