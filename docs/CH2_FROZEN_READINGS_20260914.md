# CH2 — frozen readings, the nightly rebuild, and the stop-loss question (2026-09-14)

Provenance: diagnosis and repair by C1 on Joseph's question ("why is nearly
every CH2 position red and why no orders in September") and his go ("fix the
defects"). Read-only against the paper account, the live logs, and the code;
the repair touches four files and nothing in the kernel or L5.

## What was found

- `runtime_decisions_latest` has not received a new `run_id` since
  2026-08-18 00:50 UTC. Every CH2 entry pass from 2026-08-27 onward evaluated
  run_id `5d9d722c-182b-46f1-9968-123c16bc3cbe`. The sentinel's exit-side
  basin numbers for MTD, VRTS, AZZ and PHM were byte-identical on 989
  consecutive checks (2026-08-26 → 2026-09-14).
- The nightly refresh (EventBridge `tfe-daily-snapshot-refresh`, 00:17 UTC)
  started every night and never finished. Two defects, both from the
  2026-08-18 deploy of "supervise TFE runtime and expose verified health"
  (b203039e8) and "publish snapshots as immutable generations" (83cb709c2):
  1. `/api/health` verifies the on-disk artifacts against the active
     generation manifest. The rebuild rewrites those files in place, then
     hides them for the bar-cache export, then rewrites them again before a
     new manifest exists. The health check answers 503 for minutes; the ALB
     target group (15 s × 3) marks the task unhealthy; ECS replaces it
     mid-rebuild ("Amazon ECS replaced 1 tasks due to an unhealthy status"
     nightly at ~00:40–00:51 UTC, 07:3x on the Sunday full-universe run);
     the new container logs "Marked 1 stale run(s) as aborted".
  2. On the nights the old task survived to the publish step,
     `snapshot_generation._put_immutable` passed `IfNoneMatch="*"` to S3
     put_object and the image's apt-installed botocore rejected it
     ("Unknown parameter in input: IfNoneMatch"; conditional writes need
     botocore ≥ 1.35). Seen 08-22, 08-23, 08-24, 08-25, 08-30, 09-10, 09-13.
  Either way `runtime_postgres_sync` never ran, so the decision table stayed
  at the 08-18 close. CPU/memory were not the cause (70 % / 30 % during the
  rebuild).

## Effects on CH2

- September entries: 0. The pass ran every trading day; it saw the same 19
  names that passed the frozen basin; all 19 were already held; 0 after
  dedup. Fridays are blocked by design; 09-07 holiday; 09-04 afternoon and
  09-08 the DB password failed ("entries fail closed") until the 09-08
  deploy.
- Book at diagnosis: 21 positions, 15 red, −$1,613 unrealized on ~$52k
  invested; equity $98,627 on $100k funded. Broad market since the last buys
  (08-27): S&P −1.5 %, Russell 2000 −3.7 %.
- Churn on the frozen list: BDX (+26.3 %), VALE (+6.5 %), FIZZ (+5.7 %) were
  banked by DRIVE_DYING readings on 08-26/27; the next morning the frozen
  list re-bought BDX, VALE, CRVL (and FIZZ on 08-31) at the same or higher
  prices. The 09-02 "entry door memory" stops repeats but not this pattern.
- The verdict sheet was stale 09-01 → 09-08 (read_at 09-01; engine ignores
  sheets older than 4 days); holdings had only the −20 % GTC stops then.
  The reading runner (nightly door) was not running in this workspace at
  diagnosis.

## The stop-loss question

Best point reached by each loser since entry (closing basis), then where it
sat at diagnosis:

| sym  | entered    | best close | on         | now     |
|------|------------|-----------:|------------|--------:|
| PHM  | 2026-07-14 |     +8.8 % | 2026-07-28 |  −5.5 % |
| SNY  | 2026-08-12 |     +5.6 % | 2026-08-25 |  −1.1 % |
| DEI  | 2026-07-14 |     +4.7 % | 2026-07-16 | −13.2 % |
| VALE | 2026-08-27 |     +4.4 % | 2026-09-02 |  −2.7 % |
| AGNC | 2026-08-04 |     +4.2 % | 2026-08-19 |  −5.5 % |
| HDB  | 2026-07-27 |     +4.2 % | 2026-07-30 |  −1.0 % |
| LINE | 2026-08-12 |     +2.8 % | 2026-08-13 |  −9.8 % |
| VRTS | 2026-08-03 |     +2.4 % | 2026-08-13 | −11.9 % |
| AZZ  | 2026-07-15 |     +2.1 % | 2026-08-11 | −11.4 % |
| HTH  | 2026-08-12 |     +1.4 % | 2026-08-13 |  −1.1 % |
| MTD  | 2026-08-12 |     +0.4 % | 2026-08-12 | −10.5 % |
| BDX  | 2026-08-27 |     +0.3 % | 2026-08-28 |  −4.9 % |
| RBC  | 2026-08-27 |     +0.1 % | 2026-08-27 |  −5.5 % |
| BAM  | 2026-08-27 |     −0.4 % | 2026-08-28 | −10.5 % |
| FIZZ | 2026-08-31 |     −0.2 % | 2026-09-03 |  −1.7 % |

Why nothing sold them while they were up:

- No CH2 rule banks a gain under +20 %. The profit-protect floor engages only
  after a +20 % peak (giveback one third), by Joseph's order of 2026-08-13.
  The trailing ratchet (EXIT-D, sold on the first pullback past +5 %) and the
  +5 % harvest (EXIT-H) were removed 2026-06-08 as winner-capping; EXIT-A
  (S_UF ≥ 0.75) removed 2026-06-13.
- No CH2 rule sells a loss between 0 and −20 %. Joseph's exit law of
  2026-08-25 demoted the basin break and the one-day D_k flip to inputs, and
  replaced the 3×ATR / min-5 % custody stop (which sold RBC, BAM, RAL, COF at
  −6 % between 08-12 and 08-25) with the −20 % emergency brake. Losers hold
  while the nightly reading says recovery is alive; all fifteen read
  RECOVERY_ALIVE (or UNREADABLE) on the 09-11 sheet.
- The structural exits that existed before the law (D_k flip, basin break)
  were blind from 08-18 onward: they read the frozen table, and every holding
  showed break = 0.0000 on every check.
- The 25-day calendar cap was never implemented; the 90-day wall replaced it
  on 08-25. Oldest holdings at diagnosis: PHM 62 d, AZZ 61 d.

So the losers that were briefly up (+2 % to +9 %) sat inside what the law
calls weather, and the only sellers left are the readings, the wall, and the
−20 % brake. Changing that is a change to the exit law — Joseph's call, and
any candidate rule gets measured on the decade of CH2 lives before it is
proposed.

## The repair (four files)

- `rebuild_uf_snapshot.py`: records `uf_snapshot_generation.hold.json`
  (schema, pid, started_at, mode, run_id) for the whole rebuild + publish
  window; removed in `finally` on every exit path.
- `web/src/lib/runtime-health.ts`: an artifact/manifest mismatch is the
  verified state only while a live hold exists (named process alive in
  `/proc`, hold younger than 3 h — the longest observed rebuild phase is
  2,926 s); manifest identity checks stay strict; `generation_hold` is
  exposed by `/api/health` (`web/src/app/api/health/route.ts`).
- `web/Dockerfile`: `pip install boto3==1.43.93` shadows the apt copy; the
  build asserts the imported botocore is ≥ 1.35 before the image can ship.

Local proofs (scratchpad, this session): the publish chain with a
conditional-write-capable client — publish, the post-publish report rewrite,
and a fresh-container restore all keep the receipts consistent; ten
health-check cases (verified set, mismatch without hold, mismatch with live
hold, hidden artifact with hold, hold past bound, dead pid, wrong schema,
future timestamp, missing manifest, leftover hold on a verified set); hold
lifecycle on success and failure; `tsc --noEmit` and eslint clean.

Production proof: the next scheduled run logs every post-rebuild phase
complete, "Published immutable generation …", no "TFE container starting"
during the window, and the following entry pass shows a run_id other than
`5d9d722c…`. Trade switch after the deploy: `TFE_ENTRIES_HALTED=0`,
`CH3_ENTRIES_HALTED=1`.

## Addendum — deployed 2026-09-14

- Deployed as `tfe-web-task:626`, image `tfe-web:manual-20260914T150337Z`,
  commit `a6e69c74c` (fix in `0a78bbdc1`), rollout COMPLETED, task HEALTHY.
  Trade switch verified after the deploy: `TFE_ENTRIES_HALTED=0`,
  `CH3_ENTRIES_HALTED=1`. `/api/health` now answers with
  `"generation_hold": false` on the restored generation
  `snapshot_pub_v2_76d4edfbb3c9460cab59b8a1`.
- The image build printed `botocore 1.43.93` from
  `/usr/local/lib/python3.11/dist-packages` — the pip copy shadows the apt
  copy (1.29.27) as intended.
- The new container logged "Entry pass already ran: 2026-09-14" — no repeat
  entry pass from the restart.
- Deploy wrapper notes: (1) its local `web_build` gate needs Node ≥ 20.9 and
  this workspace has 18.20; the first attempt failed there and the second ran
  with a Node 22 runtime on PATH. (2) On the second attempt the wrapper's
  validation state marked `web_build` "unchanged_since_last_validated" and
  skipped it, although the unit had failed on the first attempt — the
  contract keys validation on inputs shared with the `typescript` unit,
  which had passed. The production image build (same `npm run build`, Node
  22) succeeded, which is the build proof for this deploy; the contract
  flaw is left as a follow-up, not touched here.
- The nightly reading runner (`tools/ch4_spring_daily_runner.sh`) was
  restarted in this workspace (pid 91240 at 14:36 UTC); the verdict sheet
  from 09-11 would otherwise have gone stale after 09-15.
- Proof still pending: the 2026-09-15 00:17 UTC run (all six phases,
  "Published immutable generation", no container replacement) and the
  13:45 UTC entry pass showing a run_id other than `5d9d722c…`.

## Addendum 2 — the first completed run (2026-09-15 00:17 UTC) and a third defect

- Proof of the two repairs: generation hold recorded at 00:17:21, no
  container replacement during the run, "Published immutable generation
  snapshot_pub_v2_86ef86a38c4beadfa88941a1" at 00:54:16, hold released,
  `snapshot_rebuild` complete (2,216 s), `l5_baseline_filter` complete,
  `runtime_postgres_sync` complete (472 s; 11,483 rows into
  `runtime_decisions_latest` under run_id `1294a76d-7a81-4f25-8484-3b5f552ecf58`).
  `/api/health` green on the new generation. CH2's next entry pass reads
  this run.
- Then `validation_gate` failed on `ta_semantics_integrity`: 55 of 11,483
  rows with a valid SMA anchor (11,285 on 2026-08-18). The anchors come from
  `web/data/screener-quote-cache.json`; the live container carried the
  image's March fallback (60 rows) because every container since 08-18 was
  fresh and no run had reached the post-publication quote-cache follow-up.
  In targeted/full modes the refill is deferred to a detached follow-up
  launched after the pipeline; a failed gate raises before the launch, so
  the cache could never refill and the gate could never pass. CH2 does not
  read the quote cache or the gate (verified by grep across the execution
  scripts); the website's publication resolution does (`candidateValid`),
  so the screener stays on its last validated run until the gate passes.
- Repair (commit db02a1713): `_should_defer_quote_cache_refresh` defers only
  when the cache on disk is younger than four days; otherwise the refresh
  runs inline before the runtime sync, as the pre-deferral pipeline did.
  Eleven local cases pass. Deploy follows once the live gate is green.
- Live repair of today's state: the designed follow-up
  (`--quote-cache-followup-only`) was launched by hand inside the serving
  container as the `node` user with the run's env (`TFE_REFRESH_RUN_ID` of
  the 00:17 run), logging to `/tmp/c1_followup.log`. First launch (output to
  `/proc/1/fd/1`) died silently; second launch with file logging runs:
  `build_screener_quote_cache.py` fetching 11,475 pending symbols, then the
  follow-up runtime sync and validation.
- Resume checkpoint: written after `l5_baseline_filter`; ignored after 6 h
  (`DEFAULT_RESUME_MAX_AGE_SECONDS`), so the next nightly run rebuilds from
  scratch — no re-freeze risk.

## Addendum 3 — the by-hand follow-up killed the task; liveness redesigned

- The 02:42 UTC follow-up fetched all 11,475 quotes (10 failures), then at
  02:52 UTC the task was replaced: "Task failed ELB health checks", 503 from
  the health report, container health UNHEALTHY too. RDS was idle (3–5 %
  CPU, 1–3 connections), no request timeouts; the server CPU was pinned at
  100 % by the follow-up's own re-sync. A 20 s three-process CPU burn in the
  live container flipped no check (responses ≤ 2.9 s), so load alone is not
  it; which check returned false could not be seen from outside. The
  decision table survived intact (11,483 rows, run_id `1294a76d…`); the
  provenance table carried 12,060 rows (a partial follow-up insert; the next
  full sync replaces it). The quote cache reset to the 60-row fallback with
  the new container.
- Decision (commit f12856fc3, deployed as `tfe-web-task:627`, image
  `manual-20260915T035854Z`, switches verified 0/1): `/api/health` answers
  200 while the supervisor's essential processes are alive; database
  reachability and snapshot receipts are still measured, returned in the
  body (`verified`, `database_error`) and logged with the failing check
  names, but no longer decide replacement. Reason: replacing a task never
  repairs a database outage (the 09-04/09-08 password failure would have
  looped it) and the refresh pipeline legitimately rewrites the bound files
  during its own work. Four liveness cases and the ten receipts/hold cases
  pass; tsc and eslint clean; this deploy's local gates ran and passed.
- Deploy sequencing: the wrapper's `runtime_validation` unit blocks on
  `ta_semantics_integrity_failed`, so the refill-ordering fix (db02a1713)
  was reverted (017b250b4) for this web-only deploy and is re-applied once
  the live gate passes.
- Follow-up relaunched inside the 627 container as `node` (pid 220, file
  log `/tmp/c1_followup.log`) at 04:15 UTC.

## Addendum 4 — deploys 628/629, the gate's remaining blockers, one decision for Joseph

- The second by-hand follow-up (inside the 627 container, 04:15–04:49 UTC)
  completed without a task replacement — the liveness change held. It refilled
  the quote cache (11,465 of 11,475 fetched), re-synced, and re-ran the gate:
  anchors 11,435 / 11,120 / 9,407 of 11,483, rsi 11,483 — better than the last
  passing run — yet `ta_semantics_integrity` still failed: 2,077 rows carry
  the producer's 0 placeholder with no anchor (listings without enough
  history), and "make validation reports fail closed" (7376e1392, 2026-08-18)
  had switched the check from flag-only to blocking. Read-only count on the
  live table: sma200 zero/absent 2,076, sma50 363, sma20 48; no other
  value/anchor combination exists.
- Deploy 628 (commit 1643ae0b2): `buildTaAnchorValidExpression` accepts
  NULL, a positive numeric anchor, or (value = 0 AND anchor absent); a
  computed value without a positive anchor stays invalid. Live count under
  the new rule: 0 / 0 / 0 invalid. Gate re-run in the 628 container:
  `ta_semantics_integrity` pass. Follow-up: the producer
  (`sync_runtime_postgres_impl.mjs`) writes 0 rather than NULL for an
  uncomputed average on some path.
- Deploy 629 (commit cad87acda, the refill-ordering fix re-applied): the
  wrapper's `runtime_validation` unit took the `ecs_runtime_repair_hotfix`
  path (ECS gate non-pass with `pipeline_terminal_integrity_failed`, sole
  changed input `run_refresh_with_l5_learning.py`). Switches verified 0/1.
  The new container carries both fixes and the 60-row fallback cache, so the
  next run refreshes the cache inline before the sync.
- Still failing on the 1294a76d run: `pipeline_terminal_integrity`
  (`report_status` ok but `epoch_library_status` empty — the main run died at
  the gate before the epoch step; my manual follow-up reused the run id and
  overwrote `started_at`/`trigger_source` on its row). A clean nightly run
  clears this.
- Structural blocker left for Joseph: `ui_filter_behavior_integrity` is
  `not_run` because no task definition has ever carried
  `TFE_VALIDATION_BASE_URL` / `TFE_VALIDATION_USERNAME` /
  `TFE_VALIDATION_PASSWORD`, and both `validationReportPassed()` and
  `validation-report-truth.ts` treat `not_run` as failing by design (the
  08-18 tests assert it). Consequence: no run can pass the gate, the website's
  publication stays on the 08-18 run, and refresh-pipeline deploys depend on
  the hotfix lane. Options: (1) create a site login for the checker and add
  the three variables to the task definition; (2) make `not_run` non-blocking
  (reverses the 08-18 design). Not changed without his word.

## Addendum 5 — Joseph's order: fix the loss side and reset the book (2026-09-15)

- What the record showed: since the current rules began, 16 closed CH2
  positions netted a gain (one +90 %, one +14 %, eleven at +2.3 % avg, one
  −12.6 %) while the 21 open ones sat at −$1,982. Broker equity: funded
  $100,000, peak $100,926 (2026-05-07, +0.9 %), $95,194 at the morning
  check. The reading's DEAD test ("16 sessions past its LAST damage") cannot
  fire on a sliding stock — every new low restarts the clock — so losers
  rode toward the −20 % brake (VRTS −16 %, DEI −13 %, AZZ −12 % all
  RECOVERY_ALIVE on 09-11). The entry reads only the stock's structure; the
  buys after the freeze were on stale physics, three re-buying names the
  reading had just sold as winners.
- The reset (script `_c1_flatten_ch2.mjs`, run as `node` inside the serving
  container, sell first then ledger close exactly as `ledgerClose` does,
  `exit_reason=manual_reset_joseph_20260915`, kill-cooldown keys set so the
  sentinel would not re-adopt): 21 CH2 positions sold at market, 45 fills,
  realized −$1,962.03 (3 winners, 18 losers, avg −4.38 %). Broker after:
  equity $98,300.52, cash $94,943.37, no open orders. Two holdings from
  before the ledger remain because the broker reports both assets inactive
  and refuses orders: CWAN (100 sh, cost $2,435) and HTBK (67 sh, cost
  $901). They are outside CH2 and its ledger; only a paper-account reset in
  the Alpaca dashboard removes them.
- The law change (commit with `ch2_dead_clock.mjs`): the dead clock starts
  at the FIRST closed session more than 5 % below entry; only a close back
  above that line ends the episode; more than 16 closed sessions below it
  with no heal sells (`ch2_dead_clock_exit`). 16 is Joseph's measured
  healing floor; 5 % is the old minimum stop distance. The buy order's
  first-day stop leg is now the 20 % brake (was 3×ATR / min-5 %). Exits
  with `manual_reset_*` do not trigger the 14-day cooling-off. The reading
  protocol counts from the first damage too. 13 clock assertions pass.
- Evaluation baseline (grade before spending): the fresh book starts from
  the first entry pass after this deploy, with equity $98,300.52 and no
  CH2 positions. Grading point: 20 closed positions under the new law, or
  the first 90-day wall, whichever comes first. Control: the 21 reset
  positions' exit prices above, held as the "old law would have kept
  holding" set for comparison at grading.

## Addendum 6 — the restart is complete; CH2 code frozen (2026-09-15)

Joseph: "this is a restart for ch2 with all entry and harvest rules in
place as well as all the trade mechanics working — we start with $100,000
and fresh trades ... if you see anything that will make this a money making
machine now is the time to implement it — I want to really freeze all code
changes on ch2 after this reset."

- Deployed `tfe-web-task:630` (commits 810b8628b, 35c5c4584): dead clock,
  first-day 20 % brake, reset exits do not cool off. Deployed
  `tfe-web-task:631` (commit 4b0a61709): no entries when the decision table
  is older than four days (`readingsAreStale`, logged "READINGS STALE");
  14-day cooling-off after every exit the law makes (readings, dead clock,
  brake, ratchet). Both verified live: switches `TFE_ENTRIES_HALTED=0`,
  `CH3_ENTRIES_HALTED=1`; all four changed scripts present in the container.
- Not implemented (unmeasured, and Joseph's standing rule is no unmeasured
  entry rule): a market-regime gate on entries. Measurable during the
  evaluation without touching code.
- The $100,000 start requires Joseph's Alpaca paper-account reset (the API
  has no reset; it also clears the two inactive holdings CWAN and HTBK).
  If the reset rotates the paper keys, `tfe/market-data/prod`
  (APCA_API_KEY_ID / APCA_API_SECRET_KEY) must be updated.
- Known fragility, left in place and stated to Joseph: the nightly reading
  that banks winners (`tools/ch4_spring_daily_runner.sh` →
  `ch6_nightly_door.sh` → `ch2_holdings_read.py`) runs from this workspace
  and dies with it; the sheet is ignored after four days, after which only
  the dead clock, the 90-day wall and the −20 % brake sell.
- CH2 CODE FROZEN from here. Evaluation: fresh book from the next entry
  pass; grade at 20 closed positions under these rules or the first 90-day
  wall; control = the 21 reset positions' exit prices (addendum 5).

## Addendum 7 — the reading runner's fragility, workspace layer fixed (2026-09-15)

Joseph: "Can you fix that fragility". The 2026-08-31 keepalive lived in
`.devcontainer/post-create.sh`, which runs only when the container is
created; every restart killed the nightly reading runner (and the CH6 loop,
the CH3 page loop, the book publisher and the DB rotation guard).
`.devcontainer/post-start.sh` now runs on every container start
(`postStartCommand`), /proc-guarded so it is idempotent; first run revived
three loops that were down. Commits 3c740bfde, 234bfa6f2.
What this does not cover: the reading still runs from Joseph's machine; if
it is off at the nightly time there is no reading that night. The server
layer (dossiers + the reading on ECS, with a model key in production and
the store synced through S3) is the complete fix and needs his word.

## Addendum 8 — evaluation baseline settled (Joseph, 2026-09-15)

Joseph chose not to open a new paper account. Baseline for the CH2
evaluation: broker equity $98,300.52 at the reset, cash $94,943.37, zero
CH2 positions, no open orders. CH2's score = realized P&L of ledger rows
entered after the reset (`entry_filled_at` later than the reset's last
exit) plus unrealized P&L on open CH2 rows; account equity minus
$98,300.52 is the cross-check. CWAN (100 sh) and HTBK (67 sh), both
inactive at the broker with no ledger rows, are outside CH2 and excluded.
Grading point unchanged: 20 closed positions under the frozen rules, or the
first 90-day wall.

## Addendum 9 — second nightly run (2026-09-16 00:17 UTC): rebuild proven twice; stamp defect found

- Hold recorded 00:17:20, generation `snapshot_pub_v2_e63ac9944bb8515f0b09602c`
  published 00:59:27, hold released; the quote cache was refreshed INLINE
  ("Quote cache on disk is missing or stale (age_seconds=16225303) …
  refreshing it inline", 654 s); `l5_baseline_filter` and
  `runtime_postgres_sync` complete (run_id `9711c67a-de32-4d07-a234-a24a8101c338`,
  11,483 rows, quote binding aligned); no container replacement; no
  ParamValidation. CH2's next entry pass reads this run.
- `validation_gate` failed only on `ui_filter_behavior_integrity_not_run`
  (Joseph's pending decision); `ta_semantics_integrity` passed after the
  placeholder rule.
- New defect surfaced by the first run to get this far with liveness
  intact: `build_screener_quote_cache.py` ends with
  `stamp_active_snapshot_and_quote_artifacts`, whose
  `stamp_snapshot_artifact` rewrote the published `uf_snapshot.json`
  (13,760,510 → 18,786,399 bytes, pretty-printed) at 01:10:19, so the
  runtime's snapshot receipts failed from then on (`/api/health` "verified":
  false, liveness unaffected) and `[RUNTIME-HEALTH] checks failed` logged
  on every probe. Fix: the stamp derives the snapshot metadata in memory
  and leaves a published (publication_id-bearing) snapshot untouched — the
  quote binding only needs the derived values — while an unpublished legacy
  snapshot is still stamped; seven cases pass. The health warning now logs
  on a change of state and at most every ten minutes, with a recovery line.

## Addendum 10 — first fresh entry pass (2026-09-16) and the late-fill custody defect

- Readings fresh (run `9711c67a…`, 13.5 h old). 1,366 screened, 20 passed
  the basin, 20 entries placed (~$2,459 each): 18 of the 21 names sold in
  the reset plus AEBI and AZZ. The reset's `manual_reset_*` exemption from
  the 14-day cooling-off made the re-buys possible (Joseph informed; a
  one-line change to bar them if he wants). Buy orders are limit at
  price × 1.001 with a 20 % stop leg (DAY). 17 filled within minutes; AZZ
  never filled and was cancelled by hand; MSBI filled 92 min after
  submission, AEBI 4 h 48 min after.
- Mark at 18:36 UTC: 18 CH2 positions, −$303 (−0.7 %) on $42.8k, 17 red;
  SPY +0.05 %, IWM +0.01 %, KRE −1.27 % on the day (bank-heavy book).
- Custody defect: the sentinel's phantom cleanup marked the MSBI and AEBI
  rows `cancelled` at the end of the 30-min grace while the broker orders
  stayed open; the late fills created positions with no ledger row, and
  the orphan sync refused them because the tickers had an older `closed`
  row (the reset sale) — "closed in ledger, skipping re-adoption".
  Remedy by hand: rows 888 (MSBI 73 @ 33.66) and 884 (AEBI 204 @ 12.03)
  re-activated with their fills and stop-leg ids. Code fix (this commit):
  `settlePhantomEntryAtBroker` cancels the broker order before giving up
  and records a fill that arrived meanwhile (`recordLateFill`); the orphan
  sync re-activates a cancelled row whose order filled, and skips only
  exit-blocked assets or positions closed within two days.
