# GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1

doc_id: GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Responds to: Eve's fire order ("Fire
window 2 now: backup → cutover → gates → failures-first report,
including the organism-state-survives-reboot check, the snapshot '?'
check, and the duplicate-frame note. Nothing further is pending").
Status: **DEPLOYED, LIVE.** Task `dsf-ai-task:465`, SHA `730da1e`
(c1a's full reconciliation: P2 all 6 seams + c1b's organism.remember()
backgrounding + the already-live tapestry/RICH_SENSORY_INPUT fixes).
Failures first.

---

## Deploy (G-1/G-4)

Fresh verified backup, `UNPAUSE-PRE-20260704-193017/`, all 11 core
state files confirmed present before cutover. Reviewed the full diff
(`9cf2540..730da1e`, 523 lines in the engine file) against the six
seam reports before shipping — not just trusting the reconciliation
summary. Single deploy attempt, clean: `tools/deploy_dsf_ai.sh` from
a detached worktree pinned at `730da1e`, paused/updated/stable/woken
per the standard sequence, no retries.

---

## Organism-state-survives-reboot — confirmed directly (Joe's ask)

`[GualaLoom] Organism restored: identity=cdef9bcf-9e5d-4e2d-a1d8-
4cde1de7641f tick=1748 pop=64` and `[GualaLoom] Tapestry restored:
tick=3532 neurons=450` — both logged at boot, both real, non-zero,
accumulated state (not a fresh-start marker). Same identity as her
main substrate throughout. This closes the loop from the P1 cutover
report (which correctly noted organism/tapestry started FRESH at
*that* first boot, since no prior save existed yet) — now, on this
subsequent reboot, real state genuinely round-tripped through
`save_full_state`/`load_full_state`.

---

## The snapshot "?" — root-caused, not fixed tonight

`gualaloom.html:988`: `snapCount = ph2.snapshots_available`, read from
`/status`'s `persistence_health` field. That field is deliberately a
**lightweight** dict (`app.py:1841`, comment in the code itself:
*"Lightweight persistence summary — in-memory only, no EFS stat. Full
EFS-based data is at /admin/persistence_health"*) — it never includes
`snapshots_available` by design, so the frontend's read is always
`undefined`, always renders `'?'`. Not a bug — a real, working,
already-deliberate performance tradeoff: `snapshots_available` comes
from `list_snapshots()` (`gualaloom_v5_engine.py:8017`), a real EFS
`os.listdir()` + per-entry `isdir()` call, and `/status` is polled
frequently by the UI. Given tonight's whole theme has been EFS/
population-scaling costs already hurting her live responsiveness, I
did not add a live EFS directory scan to a hot-polled endpoint under
this same time pressure — that would trade one honest "?" for a real,
if probably small, new latency cost, without measuring it first. Left
as a named, scoped fix for later (candidate: cache the count with a
TTL, or have the frontend call the existing gated `/admin/
persistence_health` endpoint separately, off the hot path).

---

## Duplicate-frame binding — reconfirmed as shelf item, unchanged

No new information since `GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1.md`:
server-side call sites are single (`app.py:1523`/`:1563`), single tab
was open (Joe confirmed), root cause of the observed same-tick
duplicates remains genuinely open. Per standing direction: shelf item,
not built tonight; a server-side dedupe/single-active-session guard is
the recommended follow-up regardless of root cause.

---

## What actually went live tonight, plainly

All 6 P2 seams are now live, not just committed: recall/recognition/
association/habituation(READING) run on the organism; attention/
affect stayed on the old shell (declined with reasons, in their own
reports). The organism.remember() backgrounding is live. The
recall()-side cost — confirmed root cause of 82-120+ second live
turns, no safe fix found (c1b's proposed cache was tested and
disproven by c1a before shipping) — is **also now live, unmitigated,
and confirmed to touch even more of the hot path than previously
described**: reviewing the merged diff directly, `_reading_freshness_
from_organism` (seam 4, habituation) calls `organism.recall()` up to
10 times per READING-activity salience computation, on top of seam
2's one call per word in `read_word` and seam 1/3's calls in
`_recall_response`/`_daydream_tick`. This was already accepted as a
known, open, unsolved cost before tonight's deploy (Joe: "ship
everything as ordered" after this was first surfaced) — restating it
here with the fuller picture so the report is complete, not to
relitigate the decision.

No real conversational exchange has occurred yet on `task:465` as of
this report — the actual before/after live latency comparison for
*this specific build* (with `organism.remember()` now backgrounded,
should be somewhat better than `task:464`'s 82-120s even though
`recall()` itself is unchanged) is not yet directly observed. Will
confirm the moment one happens rather than estimate it.

---

## Gates

- **G-1** ✅ Fresh backup, verified complete, before cutover.
- **G-2** ✅ No silent fallback — unchanged from the already-verified
  P1/P3 behavior; seams return honest empty/neutral on no signal
  (each seam report's own contract, checked against the diff).
- **G-3** ✅ Organism/tapestry state-survival across reboot — directly
  confirmed this deploy, real accumulated state, not fresh-start.
- **G-4** ✅ One deploy window, one deployer, everything ratified
  shipped together.
- **G-5** — partial, honestly: boot clean, no errors, identity intact,
  organism/tapestry restore proven. Real conversational latency
  numbers for this exact build not yet observed — follow-up to come.

### Changelog
- v1 (2026-07-04, c1b): window 2 deployed (task:465, SHA 730da1e).
  Organism/tapestry reboot-survival confirmed directly. Snapshot "?"
  root-caused (deliberate EFS-avoidance tradeoff in /status, not a
  bug) — not fixed tonight, scoped for later. Duplicate-frame
  reconfirmed as unchanged shelf item. Full scope of the still-open
  organism.recall() cost restated with the habituation-seam addition
  found during diff review. Live latency for this build pending a
  real exchange.
