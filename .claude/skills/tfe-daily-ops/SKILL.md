---
name: tfe-daily-ops
description: Operate the TFE live channels day-to-day — runners, nightly passes, pages, books, self-healing. Use at any session start, after container rebuilds, when a pass is missed, or when a page is stale.
---

# TFE daily operations

## The two live channels (both PAPER/SIMULATED — no real orders)
- **CH4** (daily, direction-agnostic, holds to 3rd gate reveal):
  engine herd_kgate_v1 in tools/ch4_herd_kgate_live.py. Book:
  artifacts/vtvr_observer/ch4_spring_book.json. Entries need band
  >=0.75 over n>=20 as-of-issue cases; longs dominate (market drift —
  a short must beat the drift 75% of the time to qualify, so shorts
  are rare and informative). Friday rule: exits only.
- **CH3 reveal-fade** (short-only BY DESIGN): engine
  tools/ch3_reveal_fade.py (ch3_reveal_fade_v1.1, FROZEN until 20
  closures). Shorts the day's +8%/3x-vol spikes that the herd is NOT
  backing (gband>=1 = herd-backed = excluded), $2k slices, 5-session
  time exit, no stop. Log: artifacts/vtvr_observer/ch3_shadow_log.json.
  The old mover-grab engine in ch3_shadow_hunter.py is retired; that
  file only hosts shared helpers (last_price, catalyst, ticker_type).

## Decision vs display cadence (Joe asks this)
- DECISIONS: once per day, after the close, from closed bars only —
  nightly pass 21:10-21:25 UTC weekdays via
  tools/ch4_spring_daily_runner.sh (store refresh -> herd export ->
  CH4 engine -> CH3 reveal-fade -> both pages).
- DISPLAY: tools/ch3_shadow_loop.sh regenerates the CH3 page every
  30 min during market hours; a session cron (approx :14/:44,
  13-20 UTC weekdays) regenerates BOTH pages with live marks and
  republishes both artifacts. EOD report cron ~21:33 UTC.
- Marks come from a ~15-min-delayed feed; pages are snapshots stamped
  "updated ... UTC".

## Display-math contract (Joe audits rows by hand — 2026-08-06)
Every number on a page must multiply out from the other numbers on
the page: whole shares only (floor(stake/price) at entry, remainder
stays in cash — fractional shares are not a thing markets allow),
marks rounded to cents BEFORE P&L, tiles are literal sums of rows.
Short rows: SELL at Entry, buy back at Current — Current below Entry
is a PROFIT; the footer on both pages explains this. Never flip a
correct sign to end a complaint (see memory: hold-correct-math).

## Rerun hazards
- ch3_reveal_fade.py has NO same-day guard: rerunning it after a
  manual pass can open extra positions past the 10/day cap. If the
  pass ran by hand, keep the runner down through the 21:10-21:25
  window (restart after 21:30).
- ch4_herd_kgate_live.py IS safe to rerun (refuses an already
  processed bar).
- Long-lived runner shells do NOT re-read edited scripts — kill and
  restart the runner after editing anything it calls.

## Runners die on EVERY container restart — and so do session crons
pgrep/ps may be unavailable or match wrapper shells — check /proc:
```
for p in /proc/[0-9]*; do c=$(tr '\0' ' ' < $p/cmdline 2>/dev/null);
  case "$c" in *ch3_shadow_loop.sh*|*ch4_spring_daily_runner.sh*)
    [[ "$c" == *sleep* ]] || echo "UP: $c";; esac; done
```
Restart per the header line in each script (nohup, repo root, .env
sourced by the script). ALSO recreate the two session crons (page
refresh :14/:44 13-20 UTC weekdays; EOD report 21:33 UTC weekdays) —
they are session-only and vanish with every session/container loss;
without them the artifact URLs go stale even while local pages
regenerate.

## Missed passes — run manually (with set -a; source .env; set +a)
The four commands inside ch4_spring_daily_runner.sh's close block, in
order. Verify afterward: ch4_spring_book.json last_processed == today;
ch3_shadow_log.json days has today.

## Pages (published artifacts — same URLs always)
- CH4: python tools/ch4_spring_page.py artifacts/vtvr_observer/ch4_page.html ->
  https://claude.ai/code/artifact/f70a03b7-3122-4f81-aabc-85b617a655a4
  (favicon chart, title "CH4 Paper Trades").
- CH3: python tools/ch3_shadow_page.py artifacts/vtvr_observer/ch3_shadow_page.html ->
  https://claude.ai/code/artifact/146ba700-cfd2-4322-a727-4fadb2026fbc
  (favicon dart, title "CH3 Shadow Hunter").
Keep favicons/titles stable. A conversation that didn't publish the
artifact must pass the URL as `url`.

## After a container rebuild
Image bakes pandas/numpy/pyarrow and auto-restores /root/.claude.json
from /mnt/tfebackup (postCreateCommand). If pip imports fail anyway:
`pip install pandas numpy pyarrow`. Memory dir /root/.claude is a bind
mount — survives. Config backup: /mnt/tfebackup/root-claude.json.

## Standing rules
- Never touch CH2/production behavior (see tfe-prod-touch).
- No new CH4 entries at a Friday close.
- CH3 fade engine frozen until 20 closed positions — observation is
  allowed (daily closes are already in the store; exit-timing variants
  get answered by replay AFTER the freeze, never by tinkering during).
- Git lock errors: shared .git — wait/retry first; only remove
  index.lock if hours-old and 0 bytes.
- Every ship states its bound; report only what actually ran.
