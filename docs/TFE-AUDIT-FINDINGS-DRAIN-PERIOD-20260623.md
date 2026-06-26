# TFE Drain-Period Audit Findings Registry

**Doc ID:** TFE-AUDIT-FINDINGS-DRAIN-PERIOD-20260623
**Branch:** codex/persistent-etl-update-20260326
**Period covered:** drain start → fresh-ledger cutover
**Purpose:** Register every contamination, ML hack, pipeline defect,
bookkeeping artifact, or destruction-pattern instance lurking in TFE's
code/config/runtime state, so the fresh-ledger system ships into a known
landscape. Audit ≠ remediation: findings are registered, not necessarily
fixed during drain.

## Disposition vocabulary

- **BLOCKS-FRESH-RUN** — must be resolved before the new ledger sees its
  first close.
- **DEPLOY-BEFORE-ARCHIVE** — small fix that should land before the
  contaminated ledger is sealed; doesn't gate drain.
- **ARCHIVE-AND-FORGET** — historical data artifact; lives in archived
  ledger; new system unaffected.
- **TAGGED, NO IMMEDIATE FIX** — documented, deferred.
- **PROBE** — not yet a finding; read-only investigation queued.

## What counts as a finding

Anything in code, config, schema, or live ECS state that, surviving into
the fresh run, would: (a) corrupt instrumentation, (b) constitute one of
the seven destruction patterns (PROJECT_STATE §7.1, KERNEL_PHILOSOPHY §3),
(c) violate the single-pipeline invariant, or (d) be a heuristic,
threshold, or ML/ML-adjacent component not in the approved registry.

Bookkeeping artifacts existing only in the contaminated ledger are
registered once as ARCHIVE-AND-FORGET; the *code paths that produced them*
are the live finding target.

## Findings

### F-001 — Canonical-record blind spot in close paths
**Source:** `docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md` Scope A.
**Detail:** 308 of 487 closes since Apr 7 carry NULL `p_l` across 17 exit
reasons. Close paths #3/#6/#7 never fetch exit price. Paths #4/#5 fetch
from expired DAY-TIF entry-order legs. Path #5 (zombie fallback) invents
`bracket_tp_sl_exit` as a guess.
**Disposition:** BLOCKS-FRESH-RUN. Forward fix (Scope B + F-002 semantics)
must ship before new ledger sees first close.

### F-002 — sentinel_exit_order_id holds submit-time intent, not fill truth
**Source:** c1 dry-run report 2026-06-23, Query 2(d).
**Detail:** Stored at submit (`sentinel_monitor.mjs:435`), never
reconciled against fill. When populated, identifies the actually-filling
order only 53% of the time; 47% point at sentinel sells that
expired/canceled under DAY TIF before a subsequent order filled.
**Disposition:** BLOCKS-FRESH-RUN. Forward fix must overwrite the pointer
with fill-confirmed exit-order-id once `filled_avg_price` is known.

### F-003 — Duplicate-row write paths in personal_trade_ledger
**Source:** c1 duplicate-sizing probe 2026-06-24, Queries 1–3.
**Detail:** 35 duplicate groups / 134 rows (~30% of population since
Apr 7), two mechanisms:
1. **Bulk re-insertion** (~24 size-2 groups): low-id April rows paired
   with 7529–7539 May re-inserts under `bracket_tp_sl_exit` /
   `stale_position_cleanup`. HTBK-orphan pattern at scale.
2. **Retry-loop writes**: XOMAO×32, OGE×13, BCPC×6, AM×6 — NULL
   `entry_order_id`, tight id clusters, writer retried without dedup.

Every duplicate group has ≥1 NULL `entry_order_id`. Patterns (NULL oids,
tight clustering, identical-millisecond timestamps) clear the
parallel-engine destruction pattern #7 — these are write-path defects,
not parallel broker entries.
**Disposition:** Data → ARCHIVE-AND-FORGET. Code paths that produced them
→ BLOCKS-FRESH-RUN, pending identification (F-006 is first cut).

### F-004 — Shared-branch deploy SHA misdirection
**Source:** `PROJECT_STATE.md` §7.1 item 6.
**Detail:** Live `tfe-web-task:551` reports `TFE_GIT_COMMIT_SHA = 9bf86de`
(GualaLoom commit) while actual TFE `web/` code state is `4ba8bff` /
task-548 (`web/` diff 548→551 = 0). Forensics reading deployed SHA as
code state get the wrong answer.
**Disposition:** TAGGED, NO IMMEDIATE FIX. (Joe to confirm — see open
question.) Per-project content hashing on deploy is the eventual fix.

### F-005 — HTBK phantom twin (7532 live / 364 closed-stale)
**Source:** c1 live-position probe 2026-06-24.
**Detail:** Only duplicate-group case bridging into the live drain set;
entries 0.69s apart. Addressed by committed-but-undeployed migrations 007
(closes 7532 to `p_l = -0.67`) + 008 (neutralizes orphan 364 to
`p_l = 0` with `orphan_note`).
**Disposition:** DEPLOY-BEFORE-ARCHIVE. Land 007+008 so HTBK closes
cleanly before sealing contaminated ledger.

### F-006 — NULL entry_order_id on live drain rows (RESOLVED)
**Source:** c1 live-position probe 2026-06-24; resolved by c1
F-006-writepath probe 2026-06-24.
**Detail:** Both NULL-oid live rows (HTBK 7532, MYE 7834) are
`orphan_sync` adoptions — synthetic ledger rows written by the
reconciliation sub-routine in `sentinel_monitor.mjs:590`, not by the
normal entry pipeline. The normal entry path always records
`entry_order_id`. Resolution surfaced F-007.
**Disposition:** RESOLVED — root cause identified, see F-007.

### F-007 — orphan_sync ungated reconciliation writer (LIVE PRODUCER OF F-003)
**Source:** c1 F-006-writepath probe 2026-06-24, Queries 1–3.
**Detail:** `runSentinel()` in `sentinel_daemon.mjs:312` is called every
cycle regardless of `TFE_ENTRIES_HALTED`. Inside it, the orphan-adopt
block at `sentinel_monitor.mjs:590` INSERTs synthetic
`status='filled'` rows into `personal_trade_ledger` for any Alpaca
position not found in the ledger's *open* rows. The kill switch halts
entries; it does not halt this writer.

**Verified active during drain:** orphan_sync has written 13 new rows
since the kill switch went on. Latest creation: 2026-06-22 13:51 UTC
(APH, NBIX, NOMD, PHM — all carrying old entry dates).

**Causal loop with F-001 and F-003:** F-001 mislabels a position closed
(`bracket_tp_sl_exit`, NULL price) while Alpaca still holds the
position. orphan_sync's dedup guard (`:568-573`) only checks for *open*
ledger rows, so the now-mislabeled-closed position appears to be an
orphan. orphan_sync re-adopts it as a fresh `filled` row, copying
entry price/date from the prior closed row (`:579-589`). Next cycle,
F-001 mislabels again, and the loop continues. XOMAO×32, OGE×13,
BCPC×6, AM×6 are this loop running N times per ticker. May 20
`f52cdda` ("orphan loop" patch) did not stop it; still firing yesterday.

**Clears destruction pattern #7** (no parallel broker orders — NULL
oids are the tell). **Violates single-pipeline-invariant in spirit**:
a second code path is mutating canonical position state outside
`submitEntry()`, and doing so during a declared write-quiet drain.

**Disposition (split):**
- **(a) DEPLOY-BEFORE-ARCHIVE — do now.** Gate the orphan-adopt block
  behind `TFE_ENTRIES_HALTED`. One-line guard. Stops new duplicate
  rows from accumulating during remaining drain cycles. Brief in
  flight (TFE-CMD-F007A-GATE-ORPHAN-SYNC-DRAIN-20260624).
- **(b) BLOCKS-FRESH-RUN.** Fix the dedup guard at `:568-573` to
  check Alpaca-held-but-ledger-closed positions, not just ledger-open
  rows. Depends on F-001 forward fix (mislabeling is what makes
  positions look orphaned). Do not implement until F-001 lands.

### F-008 — Production `runtime_decisions_history` lacks uniqueness on (ticker, generated_at_utc)
**Source:** validation-env Mode B import 2026-06-24.
**Detail:** Prod's `runtime_decisions_history` is append-only with no
unique constraint on `(ticker, generated_at_utc)`. The 90-day window
contains 2,672,685 rows where only 2,511,891 represent distinct
structural moments — ~160K duplicate (ticker, timestamp) pairs. Every
query against this table that aggregates on structural moment without
deduplication double-counts those rows.
**Disposition:** TAGGED, NO IMMEDIATE FIX. The validation env enforces
the constraint locally; production query call sites that aggregate on
structural moment can add `DISTINCT ON (ticker, generated_at_utc)`
where it matters. A schema-level constraint in prod requires a
migration that handles the existing duplicates first — separate work.

### F-009 — Recurrent shared-branch tangling between wC and Codex sessions
**Source:** validation-env work session 2026-06-24, observed three times.
**Detail:** The branch `codex/persistent-etl-update-20260326` is being
worked concurrently by two agents — wC (web Claude, this session) and
a separate Codex session. The Codex session has rebased shared history
at least once during the session, orphaning a session-start base from
origin's history. The result: wC's local commits diverge from origin
(12 ahead / 62 behind at the time of this finding), risking either
loss of wC's work on a hard reset or clobber of Codex's uncommitted
working-tree changes on a force operation.
**Workaround used (this finding's session):** Land via isolated
`git worktree` at origin's current tip. Apply edits in the worktree,
commit, push, discard worktree. Main checkout untouched. This
succeeded for the refresh.py + setup.sh modea change but does not
scale to longer-lived parallel work.
**Disposition:** BLOCKS-FRESH-RUN as a procedural rule, not a code
fix. The fresh-ledger cutover and the subsequent Mar 26 wire-in must
happen with a single agent on the branch at a time. Joe coordinates
via:
  - A single named coordination doc (`docs/BRANCH_OWNERSHIP.md`) that
    states which agent currently holds the branch and what the active
    change is, OR
  - A pre-action protocol where the inactive agent's session is
    paused while the active agent ships, OR
  - Separate working branches per agent, with explicit merge-to-main
    events.
Procedural decision pending Joe. Until decided, every wC-side push
uses the worktree pattern from this finding.

### F-010 — Fabricated L5 rule in validation_env_refresh.py write_output
**Source:** Sonnet 4.6 audit 2026-06-24 (artifact 3), wC verification
against production L5 paths.
**Detail:** `tools/validation_env_refresh.py:174` contained
`if d_k == 1 and s_uf is not None and s_uf >= 0.5: decision = "Accumulate"`.
This rule matches NO production L5 source path:
  - `tfe_l5_baseline.py` uses V3 basin formula + Stable Titan scaler
  - `tuple_proximity_engine.mjs` uses neighbor_wr >= 0.65 threshold
  - `recovered_versions/tfe_l5_mar26_recovered.py` uses 8 simultaneous
    conditions including F_n/raw_x_m gates
None of these reduces to a 2-field D_k + S_UF threshold. The rule was
fabricated — destruction pattern #2 (tuple flattening to scalar threshold)
per KERNEL_PHILOSOPHY §3.
**Provenance:** Introduced 2026-06-12 in commit 475de3e by Codex (predates
the Opus 4.8 validation-env build session). Inherited unchanged through
V4B and the Mode A namespace work. Sat in the repo 12 days before audit.
**Disposition:** RESOLVED (this finding's commit). decision_label is now
NULL in Mode A output. The kernel-tuple fields in snapshot_row_json are
unaffected and remain valid kernel-reproduction output.
**Impact assessment:**
  - V3 gate result (99.41% PASS) STANDS — gate compares kernel-tuple
    fields, not decision_label
  - `runtime_decisions_modea.decision_label` values from 5,732 prior
    Mode A rows are contaminated; cleared by the backfill in this
    finding's commit
  - Mar 26 wire-in plan UNAFFECTED — Mar 26 filter reads kernel-tuple
    fields directly from snapshot_row_json, not decision_label

## Add new findings below this line
