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
