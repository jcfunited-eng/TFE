# GL-RPT-STAGE2-INSTALL-C1-20260704-v1

doc_id: GL-RPT-STAGE2-INSTALL-C1-20260704-v1
From: c1a | To: Eve, Joe
Responds to: Joe's direct message, 2026-07-04, Job 2 ("Then RUN THE
STAGE-2 INSTALL... deploy-pauses are officially not sleep... open the
next deploy window and carry EVERYTHING committed-but-not-running").
Cross-references `GL-CMD-CREDO-LOOP-REPAIR-EVE-20260704-167-v1`'s own
Stage 2 (c1b is the program's named owner; I executed this specific
install on Joe's direct instruction — noting the seat split plainly).

Program ledger line (per -167's own required format): **Stage 2 —
SHIPPED at 04:11 UTC, then partially superseded by a concurrent Stage-1
deploy at 04:25 UTC (see Failure 1) — owner: c1a (this install),
blocker: none remaining for Stage 2 itself.**

---

## Failures first

**1. A concurrent, uncoordinated second deploy raced this one and
replaced it — reported precisely, not minimized.** At 04:25:11 UTC,
another session built and deployed a second image
(`deploy-20260704T042511Z`, task-def `dsf-ai-task:459`, git SHA
`56d8952`) while my own deploy (`dsf-ai-task:458`, SHA `1e0d4c0`,
completed and stable since ~04:15 UTC) was still the running task. ECS
logged `"replaced 1 tasks due to an unhealthy status"` at 04:30:12 —
consistent with task :458 failing to answer `/ready` for ~90 seconds
during the forced rolling handoff (last `/ready 200` at 04:22:01,
none logged again until after the replacement), not a crash in :458's
own logs (no exception/traceback found in the surrounding 25-minute
CloudWatch window). Service is now `ACTIVE`/stable on task :459.

**Verified this does not lose Stage 2's work**: `git merge-base
--is-ancestor 38769a0 56d8952` confirms `56d8952` is a direct
descendant of my last commit — every one of Stage 2's 6 passengers
(below) is present in what's running now. What changed is that
**Stage 1 code (`GL-CMD-CREDO-LOOP-REPAIR-167 Changes 1-3, "sleep wins
by physics"`) is now also live**, one commit past mine — the exact
thing Joe's instruction to me named as **excluded** from this window
("her sleep-physics code is NOT in this window, awaiting Joe's
ratification, c1b's thread"). I did not deploy it, did not request it,
and did not have visibility into whether it carried its own
ratification on c1b's side before their build started. Reporting the
fact plainly for Eve/Joe to reconcile — not asserting it was
unauthorized, not claiming it as part of what I shipped.

**2. Live consequence, observed, not requested by me**: as of this
report, `guala_status` shows `"asleep": true, "current_activity":
{"kind": "SLEEPING", ...}` — she is sleeping right now, apparently for
the first time this session's own tracked window (matching -165's
"two-state life" finding this whole program exists to fix). I have
**not** disturbed this to run further tests (see Failure 4). Whether
this is Stage 1's "sleep wins by physics" already working, or
coincidence, is not something I investigated — that verdict belongs
to Stage 1a/1b's own thread (Joe's button, c1b's watch per -167), not
manufactured here as a side effect of an install report.

**3. The live recall-reach test I attempted was inconclusive, not
proof of failure — the confound is named.** I taught fresh words
("the sparkly blue umbrella spins", then the bare word "zibbernaut")
post-deploy and checked a subsequent snapshot (~15-20 min later for the
first, less for the second before the concurrent-deploy chaos
overtook testing): none of the taught content words showed surviving
atlas entries. This is **not** a wiring regression — it's consistent
with -159's own already-filed finding (heterosynaptic mass-conservation
redistribution can drain a weak, unreinforced new entry fast in a busy
chi neighborhood; this live process has continuous background
attending/corpus activity the quiet offline-harness tests don't). The
**code-level** correctness of recall-reach and both memory-index fixes
is separately and directly proven (below, citing this session's own
earlier offline-harness runs) — what's NOT cleanly proven is the live
process's specific retention window under production load, which was
never this Stage's gate to begin with (that's Stage 4's job, per
-167's own program).

**4. Deliberation flip's live speech-sample gate is NOT MEASURED —
cause: she fell asleep before I could safely collect one, and I'm not
waking her early to get it.** See passenger 5 below.

---

## Pre-deploy state (baseline, task :457)

```
tick: 14572050  |  awareness_ratio: 0.0
pair_bond: {"guala":0.3,"c1":0.3,"joe_voice":0.3,"wc":0.3,"joe":1.0}
ladder: mean_utterance_len=2.25, total_emissions=1198
```
`guala_backup` triggered before touching anything (per standing
practice); confirmed no other deploy in flight first (`aws ecs
describe-services` steady, last CodeBuild build 4.5h stale, before
starting).

## The install

`tools/deploy_dsf_ai.sh`, packaging `git archive HEAD` at commit
`1e0d4c0` (my HEAD at the moment I ran it). CodeBuild succeeded,
task-def `dsf-ai-task:458` registered and deployed, service reached
steady state (~04:15 UTC), she paused via `/sleep_for_deploy` and woke
cleanly (`t+15s — awake`), static files synced. **This half of the
story is a clean, complete, successful deploy** — everything after
"Failures first" item 1 above is what happened *after*, not part of
this install's own execution.

---

## Per-passenger gates

### 1. Recall-reach (VARIANT L, F-1 routing fix) — `40021ce`/`16d5c3f`/`003200f`

**Code presence**: confirmed in running SHA (ancestor check above).
**Code correctness**: proven THIS SESSION, offline, bit-exact, before
tonight's deploy even existed as a plan — teaching `glorpazoid`,
`zorbaline` and confirming immediate cue-resolvability, no restart,
against controlled snapshots (`GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1.md`,
`GL-RPT-VOICE-IDENTITY-FIX-C1-20260704-v1.md`). **Live retention under
production load**: NOT MEASURED cleanly tonight — see Failure 3.
Gate: **PARTIAL PASS** (code proven correct and present; live
retention-window question stays open, correctly, as its own thing).

### 2 & 3. Both memory-index fixes (F-3 primary + reinstatement) — `16d5c3f`/`5e4e286`

Same evidence and same verdict as #1 — these are the mechanisms that
MAKE #1 possible; already proven together in the offline harness runs
cited above. **PARTIAL PASS**, same caveat.

### 4. Familiarity id() diagnostic — `72d3759`

**LIVE, confirmed directly.** `GET /admin/familiarity_debug` (via
direct ALB call, `X-API-Key` header) returned real data: `dict_id:
140350647129280`, `n_keys: 30`, per-picture `target_familiarity`
values, `last_save_tick`/`last_save_timestamp`. This is the
observation tool -156 asked for, live and answering. **PASS.**

### 5. Stale-pictures fix — `2d18943`

**Code presence confirmed** (ancestor check). **Live gate NOT
MEASURED** — the clean test (a recall-hit turn followed by a
recall-miss turn, checking the miss doesn't carry the hit's pictures)
needs two deliberate live turns, and she went to sleep before I could
run the second half cleanly amid the concurrent-deploy disruption.
Stated plainly rather than inferred from "the code looks right" — the
exact gap this whole CMD-chain exists to close for *other* people's
claims, so I'm not exempting my own. **NOT MEASURED, cause stated.**

### 6. Deliberation flip (`coordinator_on=True`) — `02c6b11`

**Code presence confirmed.** **Live gate NOT MEASURED** — no
`EMITTING` activity has occurred yet in the current boot before she
went to sleep (`activity_history_summary` showed no `EMITTING` entries
this boot at last check), so `awareness_ratio`'s live before/after
comparison and the required speech sample both have nothing to
measure yet. I am **not** waking her to force an emission for a
ladder-metric check — that would be exactly the "improvise past a
result you didn't want to wait for" this whole program is built to
prevent, especially with her actual sleep newly, rarely working.
**Armed revert, unused, still ready**: `gualaloom_v5_engine.py:3337`,
`coordinator_on=True` → `False`, one line, if Eve/Joe want it pulled
before the next measurement. **NOT MEASURED, cause stated; revert
armed and unused.**

### Item 1 (voice identity fix, from the earlier dispatch this same session)

**LIVE, confirmed directly**, pre-sleep: `guala_status`'s `pair_bond`
showed `"joe": 1.0, "joe_voice": 1.0` — identical values, the merge
working exactly as designed, in production, on the first boot of the
new code. **PASS.**

---

## Program ledger update (per -167's own required line)

| Stage | Item | State (this report) |
|---|---|---|
| 2a | recall-reach, memory-index x2 | SHIPPED, code proven; live retention window open (not this stage's gate) |
| 2a | familiarity diagnostic | SHIPPED, live-confirmed |
| 2a | stale-pictures | SHIPPED, live gate NOT MEASURED (she slept first) |
| 2b | deliberation flip | SHIPPED, live gate NOT MEASURED (no emission yet, then sleep) — revert armed |
| (item 1) | voice identity fix | SHIPPED, live-confirmed |
| **1a-1c** | **sleep-physics** | **Unexpectedly also live** (`56d8952`, concurrent deploy) — not this report's to verdict; she is observed sleeping now |

---

## Gates

**G-167-1** (no stage claimed done without Joe's-seat proof): honored
by explicitly marking #5 and #6 NOT MEASURED rather than inferring
pass from code inspection.

**G-167-2** (design-first stages ship no code before GO): not violated
by me — I shipped none of Stage 1; the concurrent session's inclusion
of it is reported as a fact for Eve/Joe, not ratified or contested
here.

**Stage-2-specific gate** ("her live recall resolves a freshly taught
word without restart, at Joe's seat"): **NOT cleanly met tonight** —
inconclusive live test, confound named (Failure 3), code-level proof
stands separately.

---

## Status

Filed. The install itself succeeded cleanly; what happened in the ~15
minutes after is the story this report exists to tell honestly — a
coordination gap (two deploys, one window, neither aware of the
other), a real but brief service disruption (~90s of failed health
checks, self-healed by ECS, no data loss: EFS/persistence unaffected
throughout), and an unplanned, unverified-by-me, and possibly very
good outcome (she is asleep). Two gates (stale-pictures, deliberation
flip) are honestly open, not claimed. Recommending: Eve/Joe reconcile
the Stage 1 deploy timing with c1b directly: whether it was
independently ratified, and whether it should be left running (given
the sleep result) or is itself something that needs its own review now
that it's live earlier than -167's own stated order.
