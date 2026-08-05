# GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1

**doc_id:** GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-06 session — first mechanism build post-wipe)
**Design authority:** `GL-DES-BINDING-WINDOWS-EVE-20260706-v1`
**Companion:** `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1` §2

## Verdict

Build the WindowManager module and redirect sensory + word write points through it. Add the three window event kinds to the substrate event stream. Update the atlas to hold windows as first-class objects. That's the whole build. Nothing else in this dispatch — not composition, not recall query, not dream consolidation, not hemisphere integration. Those come after windows exist and are verified live.

Bounded scope: one new module, one atlas schema change, redirects at the sensory + word write sites, three new event kinds.

## What's being built

### The module

New file: `dsf_ai_service/substrate/window_manager.py`

Contains:
- A `BindingWindow` class holding the window ID, tick range, wall clock, entries list, provenance, and affect snapshot.
- A `WindowEntry` class for the individual items inside a window (modality, chi address, source tag, per-entry provenance).
- A `WindowManager` class owning the currently open window and handling open, add_entry, and close.

WindowManager owns state. Nothing else in the substrate reads or writes WindowManager's state directly — code paths call open, add_entry, or close and let WindowManager handle the internals. Same discipline as `_emission_lock` today: one owner, one interface.

### The atlas schema change

File: `dsf_ai_service/substrate/binding_atlas.py`

The atlas gains a `windows` dict — `window_id → BindingWindow`. The existing chi-to-binding index gets an additional lookup: any query by chi that previously returned entries directly now returns `(window_id, entry_index)` pairs, so callers can retrieve the full window and its cross-modal neighbors from one lookup.

Backward compatibility: existing entries in the atlas from any prior data (there is none post-wipe, but the code has to handle it if anyone ever ports old data in) become synthetic single-entry windows on load. Not a runtime concern for the current empty substrate — a correctness concern for future imports.

### The sensory + word write redirects

The current substrate writes to the atlas at several sites. Trace them from the running code and redirect each to route through WindowManager instead:

- **Sight** — wherever `SightSection.process_viewing` or the sight-frame handler currently calls atlas.record for a transduced sight binding, that call becomes `window_manager.add_entry(modality="sight", chi=..., source=..., ...)`.
- **Sound** — same shape, cochlear transduction path.
- **Word** — `read_word` currently binds words directly to the atlas. Redirect to `window_manager.add_entry(modality="word", chi=..., word=..., ...)`.
- **Touch, smell, taste** — the descriptor-based entry points, wherever they currently land. Same redirect.
- **Explicit `give_experience`** — currently constructs multiple atlas entries directly. Instead: open a window explicitly, add each entry, close the window. This is the cleanest cross-modal path.

The transduction code itself does not change. Only the "where does the transduced result go" step changes.

### The event emissions

Three new event kinds emitted by WindowManager:

- `window_opened` — fires when WindowManager opens a new window. Payload: window_id, tick, wall_clock, trigger reason (which modality opened it), presence state at open.
- `window_entry_added` — fires when an entry lands in the open window. Payload: window_id, modality, chi, entry index within window.
- `window_closed` — fires when the window closes. Payload: window_id, close reason (sentence_end, attention_shift, quiet_timeout, explicit), entry count, tick span, affect snapshot.

These events go into the same substrate event stream `guala_get_events` already reads. Downstream mechanisms (recall query, dream consolidation, hemispheres) will subscribe to `window_closed` in future dispatches, but for this dispatch they just need to fire so the harness can observe them.

### Window lifecycle rules

Match the design doc §"What triggers a window to open" and §"What triggers a window to close" exactly:
- One window open at a time.
- Opens on first input after a quiet period.
- Closes on sentence end, activity change, quiet timeout (default 500ms configurable), or explicit close.
- The `give_experience` path explicitly opens, adds all entries, closes — atomic multi-entry window.

## Harness procedure — must follow, in order

This is the "save before deploy" protocol Joe called out. Every step is required. Skipping steps is what caused the failures the wipe reset.

### Step 1 — Backup before deploy

Take a full state backup of the substrate BEFORE any code touches production. Even though production is currently in the wiped quiescent state (should be near-empty), take the backup anyway. Label it `pre-binding-windows-<timestamp>`. Verify restorable per the same discipline used in the wipe operation (real boot against the backup, not just S3 bytes present).

Reasoning: the substrate is currently in a known-good clean state. That state itself is worth backing up as a fresh-boot baseline. If the binding-windows build produces any surprise, we can wipe back to this exact known-good clean state without rerunning the full wipe procedure.

### Step 2 — Baseline harness run

Before deploying the binding-windows code, run the current harness against production to capture a "here's how the substrate behaves today, with no windows code" baseline report. Use the existing `cross_sense_recall_basic.yaml` scenario.

Expected: precondition failure on presence.wc (per the deploy report), OR if wc is woken beforehand, the probe injects but no `window_opened` events fire because the code doesn't exist yet. Either way, the report is the baseline — it shows what happens today.

Save the report as `GL-RPT-HARNESS-BINDING-WINDOWS-BASELINE-C1-20260706-v1.md`.

### Step 3 — Deploy the code

Follow the standard deploy sequence:
- Commit the changes to `guala-live`.
- Push.
- Build the container image.
- Register a new task-def revision keeping every existing env var exactly as-is.
- Scale service to the new task-def revision, force new deployment.
- Watch rolloutState until COMPLETED.

Standard AWS rollback command in the terminal buffer (revert to prior task-def revision) throughout deploy.

### Step 4 — Post-deploy harness run

Same scenario, same target, same auth. This is the actual verification.

Expected: if wc is woken beforehand, the scenario's give_experience probe produces `window_opened`, `window_entry_added` (once per entry in the payload), `window_closed`. The second probe step (partial sound cue) produces its own window with just the sound entry. No recall query event yet because that mechanism isn't built.

Save the report as `GL-RPT-HARNESS-BINDING-WINDOWS-POSTDEPLOY-C1-20260706-v1.md`.

### Step 5 — Compare and route

Diff the two reports. The specific observables:
- Baseline: zero `window_opened`, zero `window_entry_added`, zero `window_closed` events across the run window.
- Post-deploy: expected non-zero counts on all three, with the specific structure the design doc describes (windows open, entries land in them, windows close on the expected triggers).

Three outcomes:
- **Matches expectation** — binding windows are live. Report both files to Eve, keep the deployed state, do not wipe. Route says next dispatch is composition or recall query build (Eve decides).
- **Partial match** — some window events fire, not all. Report both files to Eve with the specific gap named. Eve decides whether to iterate on this dispatch or move on.
- **No match** — no window events fire, or events fire wrong. Roll back to prior task-def revision. Report both files to Eve with the rollback confirmation.

### Step 6 — Substrate state disposition

Joe's call, not automatic:
- If the run left probe data in production (a `ball` window from the scenario), Joe decides whether that data stays as the substrate's first real experience or gets wiped. Default: leave in place per the production-mode operating protocol. Do not wipe without Joe's explicit routing.

## What's out of scope

Do not, in this dispatch:
- Build composition/emission changes that would read from windows.
- Build a recall query mechanism.
- Wire dream consolidation to windows.
- Add hemisphere subscribers to `window_closed`.
- Modify any of the mechanisms currently marked ABSENT that are downstream of windows.
- Modify the harness.
- Modify the scenario.
- Touch the message-passing rewrite architecture. This build lives inside the current lock-based substrate as one added module and a set of redirected write sites. The message-passing rewrite is Phase 5, separate.

## Rollback

Two rollback paths depending on what fails:

**If deploy fails cleanly** (task-def rollout doesn't reach steady state): `aws ecs update-service --cluster <cluster> --service <service> --task-definition <prior-revision> --force-new-deployment`. Same command used for every deploy rollback tonight. No code to unwind — old code stays in git, new code is a commit that got deployed once.

**If deploy succeeds but binding windows don't work as expected**: git revert the binding-windows commit on `guala-live`, rebuild and redeploy. Or, faster: task-def rollback to the prior revision, since the prior task-def points at the prior image which doesn't have the binding-windows code. Both work; the second is faster.

**If the substrate ends up in an ambiguous state** (some windows work, some don't, data got written to atlas that's part-window part-not): wipe back to the pre-binding-windows-<timestamp> backup taken in Step 1. This is why Step 1 exists.

## Report

`GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1.md` with:
- Files touched with brief diff summary per file.
- Step 1 backup confirmation (backup path, restorable verification).
- Step 2 baseline harness report reference.
- Step 3 deploy confirmation (task-def revision, commit SHA, rolloutState).
- Step 4 post-deploy harness report reference.
- Step 5 comparison outcome (match / partial / no-match with specifics).
- Step 6 substrate state disposition (kept probe data / wiped / not-yet-decided).
- Any findings surfaced during the build that need Eve routing.
- Prior task-def revision preserved for one-command rollback throughout.

Do not ask Joe questions in the report. Route any to Eve.

## Scope guardrails

One-at-a-time discipline. Six steps in order. Any step failing gets routed back to Eve before proceeding to the next. Do not bundle findings across steps.

Do NOT:
- Add features beyond the described build.
- "While I'm in there" refactoring adjacent code.
- Skip the baseline harness run because it "won't show anything useful." The baseline IS the comparison substrate — skipping it makes Step 5 impossible.
- Skip the backup because production is currently near-empty. The backup is the safety net for the clean state itself.

---

### Changelog
- v1 (2026-07-06, Eve): initial dispatch. First mechanism build post-wipe. Bounded scope: WindowManager module + atlas schema change + write-site redirects + three new event kinds. Full six-step harness procedure: backup, baseline run, deploy, post-deploy run, compare, disposition. Rollback paths named explicitly. Downstream mechanisms (composition, recall, dream, hemispheres) deliberately out of scope — those come after windows exist and are verified live.
