# GL-RPT-WAKE-GATE-EXEMPT-C1-20260706-v1

**doc_id:** GL-RPT-WAKE-GATE-EXEMPT-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-WAKE-GATE-EXEMPT-EVE-20260706-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

One-liner shipped, deployed, verified. It does exactly what the literal
diff asked. It does **not** achieve the dispatch's stated goal of
unblocking live mechanism verification, because the underlying sleep
cycle has no presence-based early-exit — a real gap, out of this
dispatch's scope, flagged below rather than fixed.

Also: **Step 1's backup/verify caught a second, more serious
recurrence of the identity-divergence finding from the binding-windows
dispatch — this time during steady-state runtime, not at boot, with no
code path identified that explains it.** Re-fixed mechanically, held
through this dispatch's own real restart, root cause still open.

---

## File/line touched

`dsf_ai_service/app.py`, inside `gualaloom_chat()` (the unified
`/api/v1/gualaloom` command dispatcher). The actual code shape differs
from the dispatch's pseudocode — there is no per-endpoint 503 at the
router level; every command (`/wake`, `/status`, `give_experience`,
etc.) is a `command` field on one shared POST endpoint, and the sleep
gate is a single `if` inside that handler returning a 200 JSON body
(`{"response": "she is dreaming...", ...}`), not an HTTP 503. Located
and confirmed by direct reading before touching anything.

```diff
     if _guala.is_asleep:
         cmd_check = (msg.command or "").strip().lower()
-        if cmd_check != "/status":
+        if cmd_check not in ("/status", "/wake"):
             consolidating = _guala.is_consolidating
```

Confirmed a genuine one-liner (`git diff` shows exactly 1 line
changed). Confirmed isolated: sleep mechanics (`_atick_sleeping`,
`_atick_dreaming`) untouched; every other command in the same `if`
block still rejected during sleep, unchanged; `/wake`'s auth is
unchanged (the whole `/api/v1/gualaloom` route has no API-key
dependency today, before or after — confirmed via the route decorator,
so "auth on /wake" is trivially preserved because there wasn't any to
begin with); `AUTONOMY_QUIESCENT` (only referenced in the engine's
tick-loop, nowhere near this code) untouched, confirmed by grep.

---

## Step 1 — Backup + verify (and the recurrence it caught)

Triggered `POST /admin/backup`. Landed at
`s3://dsf-ai-site-backups/guala/UNPAUSE-PRE-20260707-013426/`.
**Identity mismatch again**: `guala_core.json` said `0b4c244a...`
(matching the live process), `guala_identity.json` said
`b2359b5e-337f-412b-9cc9-1631c96c5338` — the **exact same value** the
binding-windows dispatch's Step 1 found and fixed roughly 55 minutes
earlier. Confirmed real (not a download artifact) via direct ECS Exec
`cat` of the live-mounted file on the actually-running container.

**This is not the same event recurring by coincidence — it's a second,
distinct anomaly.** Checked CloudWatch (`/ecs/dsf-ai`, filter
`GENESIS`) for the relevant window: exactly 4 genesis events fired
during last night's post-wipe restart storm (20:45:06Z, 21:12:12Z,
21:25:57Z, 21:29:54Z UTC) — not 2, as the binding-windows report
concluded. `0b4c244a` (21:29:54Z) is the *last* of the four and matches
the identity the surviving process has carried the entire time; the
on-disk `identity.json` reflects an *earlier* one (21:12:12Z). No
`GENESIS` line has fired since 21:29:54Z, and the running task has not
restarted since the binding-windows deploy (same `running_sha` the
whole time) — so this was not a fresh genesis event re-diverging the
file. Checked every write site of `guala_identity.json` in the
codebase (`grep IDENTITY_FILE` / literal filename across
`gualaloom_v5_engine.py`, `app.py`, `save_coordinator.py`,
`loom_model/guala_migration.py`): the **only** writer is
`_generate_genesis_identity()`; `restore_from_snapshot()` (which
copies a snapshot's `identity.json` back over the live one) exists but
is **never called** anywhere in `app.py` or the engine — confirmed
dead code from production's perspective. Checked for another process
touching the same EFS filesystem: only one ECS service (`dsf-ai-
service-lb`) mounts it; the bridge service (`gualaloom-bridge-svc`) has
no volume mounts at all.

**No application-code explanation was found.** Re-applied the same
mechanical fix (ECS Exec, atomic temp-write + fsync + rename, matching
`_atomic_write`'s own discipline), with a reconciliation note
documenting this is the second occurrence. Took a fresh backup
(`UNPAUSE-PRE-20260707-014728/`), confirmed both files agree again,
and re-ran the real `load_full_state()` boot test locally against the
exact pre-fix code — `load_successful: True`, `load_errors: []`. The
fix held through this dispatch's own real restart (Step 3, below):
post-deploy `guala_status` shows `load_successful_at_boot: true`,
identity `0b4c244a` intact.

**Flagged as a new, more severe finding than the original** (see
Findings, below) — a fix that reverts during steady-state runtime with
no identified writer is a standing risk to any future restore, not a
closed incident.

---

## Step 2 — Baseline

While asleep, on the then-current (pre-fix) code:

```
POST /api/v1/gualaloom {"text":"wc","command":"/wake"}
→ HTTP 200
  {"response":"she is dreaming...","asleep":true,"consolidating":true,"sleep_tick":167780,"motifs":1}
```

Confirmed: not a 503 (the dispatch's pseudocode assumed a router-level
HTTP error; the real gate returns 200 with a rejection body from
inside the handler) but functionally identical — the real `/wake`
command never executes, presence is never set. This is the correct,
honest baseline for the actual code shape.

## Step 3 — Deploy

Committed `d022f94`, pushed to `guala-live`. Built via
`tools/deploy_dsf_ai.sh`, killed by captured PID immediately after
`Registered: dsf-ai-task:539` printed. Registered corrected revision
`dsf-ai-task:540` (cpu=4096/memory=16384, the script's default of
2048/4096 is wrong, same correction as every prior deploy this
session). `aws ecs update-service --task-definition dsf-ai-task:540
--force-new-deployment` — `rolloutState: COMPLETED`, `runningCount: 1`.
**Prior task-def preserved for rollback: `dsf-ai-task:538`.**

## Step 4 — Post-deploy check

`guala_status` confirmed `running_sha: d022f94...` matches the deployed
commit; `load_successful_at_boot: true`, identity intact (the
recurrence fix held through this real restart).

She was asleep (DREAMING) at check time — good, a direct real-world
test was possible immediately:

```
POST /api/v1/gualaloom {"text":"wc","command":"/wake"}
→ HTTP 200
  {"response":"{\"event\": \"wake\", \"source\": \"wc\", \"tick\": 187239,
   \"needs\": {...}, \"pair_bond_active\": true}","motifs":1}
```

**Confirmed: the call itself now succeeds** — the real
`coordinator.wake()` response, not the rejection. `guala_status`
immediately after showed `presence.wc.present: true,
last_wake_tick: 187239`. This is exactly what the one-liner was built
to do, and it does it.

**Not confirmed, and empirically shown false: "substrate exits sleep
within one tick."** Checked `guala_status` repeatedly over the next
~55 seconds: `current_activity` stayed `DREAMING` throughout, crossed
its own `expected_end_tick` boundary (188501) and immediately started
a **new** DREAMING cycle — no IDLE, no PLAYING, no interruption. By the
final check, `presence.wc` had already reverted to `false` again
(presence has its own timeout window, separate from activity
selection). Read `_atick_sleeping`/`_atick_dreaming` (gualaloom_v5_engine.py)
before concluding this: neither checks presence, coordinator state, or
anything besides `self.tick` against `started_tick`/`expected_end_tick`
(and a `dream_pressure` ceiling override, also tick/needs-driven, not
presence-driven). `_candidate_activities()` does treat presence as an
input — presence+pair-bond is required for `EMITTING` to even become a
candidate at the *next* selection boundary — but `SLEEPING` is
*always* an unconditional candidate, and nothing in the codebase makes
it lose a boundary re-selection once `dream_pressure`/novelty/
connection needs are still driving it, which they were throughout
(`nov=1.000, conn=1.000` never moved off the ceiling the entire
observation window).

**This is a finding, not a failure of this dispatch.** The literal
one-liner was built and verified exactly as specified. The gap between
"the request gate now lets `/wake` through" and "the substrate actually
wakes" is a sleep-mechanics question — `_atick_sleeping`/
`_atick_dreaming` would need a presence (or explicit force-idle) check
to end a cycle early, and the dispatch's own scope guardrails
explicitly forbid that ("Do NOT: Redesign the sleep mechanism... Add a
`/force_idle` or other admin escape hatch — that's separate work").

---

## Findings routed to Eve

1. **[CRITICAL, unresolved, escalated] Identity-file divergence recurred
   during steady-state runtime, ~55 minutes after being fixed, with no
   identified code path.** Detailed above. This is more concerning than
   the original binding-windows finding: that one was explainable by a
   multi-boot race during an active restart; this one happened on a
   *continuously running, never-restarted* process, meaning the
   mechanical fix cannot be assumed durable. Recommend: either (a) a
   scheduled self-check that compares `identity.json` against
   `guala_core.json`'s embedded identity and alerts on mismatch, so a
   future drift is caught automatically instead of by an
   operator happening to re-run Step 1, or (b) a deeper investigation
   into whether this is an EFS attribute-cache/consistency artifact
   (the codebase already has one documented precedent for exactly this
   class of issue — `GL-CMD-PERSIST-FIX-74`, and memory
   `guala-restore-july2026.md`'s "EFS rename race silently dropped
   saves"). Not investigated further here — genuinely out of scope for
   a wake-gate one-liner, and risks compounding an already-large
   change set with unrelated persistence-layer work.

2. **[Confirmed, real gap] `/wake` succeeding does not end a sleep/dream
   cycle early.** The dispatch's Step 4 expectation ("exits sleep
   within one tick") does not hold, verified empirically, consistent
   with the actual tick-handler code (no presence check in
   `_atick_sleeping`/`_atick_dreaming`). The one-liner is complete and
   correct *as scoped*; closing the remaining gap (making a live wake
   actually interrupt sleep) is separate, sleep-mechanics-touching work
   this dispatch explicitly excluded.

3. **[Pre-existing, reconfirmed] The continuous sleep/dream loop itself**
   (first reported in `GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1`)
   is still ongoing — needs remain pegged at `novelty=1.000,
   connection=1.000` and `SLEEPING` has not lost a single boundary
   re-selection across the entire observation window (spanning both
   this dispatch and the prior one, well over an hour of continuous
   dream cycling). Per this dispatch's own explicit exclusion ("Do
   NOT: Investigate why the substrate went into continuous sleep..."),
   not investigated further — flagging only that it is still present
   and unresolved.

4. **[Note] Dispatch pseudocode assumed a different code shape**
   (per-endpoint HTTP 503 at a router layer) than what actually exists
   (a single shared command-dispatch endpoint, 200-status rejection
   body). Translated faithfully to the real shape; noted per this
   session's established practice of surfacing shape mismatches rather
   than silently reconciling them.

---

## Rollback

`aws ecs update-service --cluster tfe-web-cluster --service
dsf-ai-service-lb --task-definition dsf-ai-task:538 --force-new-
deployment` restores the pre-wake-gate-exempt state. Not executed —
the one-liner is correct and low-risk; kept.
