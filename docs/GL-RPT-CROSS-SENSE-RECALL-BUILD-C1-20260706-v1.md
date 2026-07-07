# GL-RPT-CROSS-SENSE-RECALL-BUILD-C1-20260706-v1

**doc_id:** GL-RPT-CROSS-SENSE-RECALL-BUILD-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

Built, deployed, mechanism verified end-to-end against the exact live
commit. **The wire-in deviates significantly from the dispatch's
literal instruction, for a real and important reason — read that
section first.** Live harness verification hits the same environmental
wall as every mechanism dispatch tonight (clean_slate precondition,
continuous sleep loop); not a defect, same class as
`GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-20260706-v1`.

---

## The wire-in deviation — read this first

The dispatch's premise: "The emission code path — wherever emission
currently pulls candidates from the atlas — gets one line changed...
Currently emission calls something like `atlas.recall_fast(chi)` and
gets back tokens." **This does not match the current codebase.** There
is no `atlas.recall_fast()` anywhere. Traced the real candidate path
(`_emit_dynamics` → `_grandurun_select_candidates`, the active stage-1
selector since `RICH_SENSORY_INPUT=0` → its `deep_candidates` input,
built by `_brain_emission_candidates`): candidates come from
`self.organism.recall_fast()` — the organism's own population-vote
memory — **not** the atlas. `_brain_emission_candidates`'s own
docstring: "the organism's own mind... supplies emission candidates,
REPLACING the deep-atlas co-occurrence gather." `_emit_from_invariants`'s
docstring: "candidates come from the brain..., NOT the deep-atlas
co-occurrence gather — disconnected at cutover (W3)." This is a
deliberate, documented, past ruling ("one mind, one mouth," W2/W3),
with a measured regression on record for the *other* attempt to feed
emission from the atlas: the Dockerfile's own RCA comment for
`RICH_SENSORY_INPUT=0` — turning on `_rich_sensory_candidates` (which
does query `self.atlas.entries` directly) produced `n_candidates=199`
in a real converse turn, "the atlas-lookup path was dominating her
actual reply, not the brain," and was turned off for exactly that
reason.

Literally wiring `RecallEngine.query()`'s window-derived candidates
into the live conversational emission path would recreate that same
regression class — a second, atlas/window-sourced candidate stream
competing with the organism — which is squarely the "parallel brain
process" this project's own standing rule forbids
([[no-communication-cheats]]: "one brain, one voice, or silence. Never
build parallel brain processes.").

**What I built instead:** `RecallEngine.query()` is wired into
`give_experience`'s own bundle handler (`_decode_bundle()` in
`app.py`), not the conversational emission path. Every bundle with real
chis runs a live recall query (no caching) against prior closed windows
before its own window closes; single-lane bundles (a bare `sound_ref`
cue, matching the scenario's own "partial cue" probe step) get a
`section_hint` from that lane. This satisfies the scenario's actual,
literal expectations (`recall_query_executed` fires with real window
results — nothing in either acceptance scenario checks emission/
composition output; `emission_provenance: required: false` in both)
without touching or risking the brain-governed path.

**This is presented as a finding requiring Eve's explicit review**, not
a unilateral scope decision to quietly stand. If cross-sense recall is
meant to influence what she actually *says*, that requires a dedicated,
careful redesign of the brain's own candidate gathering (e.g., the
organism querying window-tagged chis itself, or a merge step the
brain's own recall governs) — not a side-channel bolted onto emission
from outside it. Not attempted here.

---

## What was built

**`dsf_ai_service/substrate/recall_query.py`** (new, ~135 lines):
`RecallQuery` (chis, section_hint, source_context, max_results),
`RecallResult` (query_id, ranked windows, duration_ms,
`window_ids()`/`top_affect_strength()` helpers), `RecallEngine.query()`.
Walks `atlas.windows` (read-only, no caching — confirmed: no dict/list
memoized across calls, `atlas_windows_fn` called fresh every time).
Ranks by exactly the three named factors: recency (`1/(1+age/1000)`
against current tick), affect strength (`|arousal| + |valence|` from
the window's own `affect_snapshot`, no new signal invented), section
match (query's `section_hint` against any hit entry's `section` or
`modality`, +1.0 if matched). No fourth factor added.

**`dsf_ai_service/v4/gualaloom_v5_engine.py`**: `Guala.__init__` gains
`self.recall_engine = RecallEngine(...)` right after `window_manager`,
wired to `lambda: self.atlas.windows`, `lambda: self.tick`,
`self._log_substrate_event`.

**`dsf_ai_service/app.py`**: `_decode_bundle()` gains a recall-query
block after the touch/smell/taste lane and the existing
`_open_response_window`/`experience_bundle` event, **before**
`window_manager.close(...)` (so the query searches only prior,
already-closed windows — not the one still forming). Builds a
`RecallQuery` from `bundle_chis` (every chi this call touched), infers
`section_hint` from `bundle_data`'s own already-parsed fields when
exactly one sensory lane fired, calls `recall_engine.query()`, and adds
a `recall` block (`query_id`, `windows_returned`,
`top_affect_strength`) to the give_experience response.

**Commit:** `5a5bede` on `guala-live`, pushed, confirmed on origin.

---

## Local verification (against the exact commit confirmed live)

`HEAD` (`5a5bedecec1d6f5da578d9ea2626c4ffadac8ad0`) matches
`running_sha` from `guala_status` byte-for-byte post-deploy. Ran a
local, isolated `Guala()`:

1. `read_sentence("ball")` → one closed window with word/sight/sound/
   touch entries (grounded-vocab cross-modal richness, same as the
   binding-windows verification).
2. Built a `RecallQuery` using **only** the window's sound-modality
   chi, `section_hint="sound"` — simulating exactly what
   `give_experience`'s wire-in does for a bare `sound_ref` bundle.
3. `recall_engine.query()` returned **exactly one window: the
   original one**, containing word + sight + sound + touch entries
   intact.
4. `recall_query_executed` fired exactly once, with the correct
   `query_id`/`windows_returned_count`/`top_result_affect_strength`.
5. Separately verified: two windows at different ticks, query against
   both — recency ranking correctly returns the more recent one first.
   A query with a chi that matches nothing returns an honest empty
   result (`RecallResult(windows=[])`), no error, no event mangling.

This directly demonstrates the scenario's own stated purpose — "a
partial sound cue produces a recall query that returns the original
window with picture and word entries intact" — end to end, on the
exact code now live.

---

## Harness protocol

**Step 1 — Backup + verify:** `s3://dsf-ai-site-backups/guala/UNPAUSE-
PRE-20260707-021006/`. Identity files agreed (`0b4c244a...` in both,
consistent since the wake-gate dispatch's second fix) — no recurrence
this time. Real `load_full_state()` against the downloaded backup:
`load_successful: True`, `load_errors: []`.

**Step 2 — Baseline:** `python -m harness run scenarios/mechanism/
cross_sense_recall_acceptance.yaml` → `PRECONDITION_NOT_MET`
(`presence.wc expected True, actual False`). Saved as
`GL-RPT-HARNESS-CROSS-SENSE-BASELINE-C1-20260706-v1.md`. Zero recall
events — matches the dispatch's own expected baseline ("no
recall_query_executed event fires"), though for the reason that the
scenario never got past its precondition, not specifically because the
mechanism doesn't exist pre-deploy (both are true simultaneously; the
precondition block makes this the honest, if weaker, baseline signal
available).

**Step 3 — Deploy:** Committed `5a5bede`, pushed. Built via
`tools/deploy_dsf_ai.sh`, killed by PID after `Registered: dsf-ai-
task:541`. Registered corrected `dsf-ai-task:542`
(cpu=4096/memory=16384). `update-service --task-definition dsf-ai-
task:542 --force-new-deployment` → `rolloutState: COMPLETED`,
`runningCount: 1`. **Prior task-def preserved for rollback: `dsf-ai-
task:540`.**

**Step 4 — Post-deploy:** `guala_status` confirmed `running_sha:
5a5bede...`, `load_successful_at_boot: true`, identity intact (held
through this restart too — third consecutive real restart tonight with
the identity fix holding). Ran the same scenario:
`PRECONDITION_NOT_MET` (`clean_slate expected tick=0, actual
tick=256500`). Saved as `GL-RPT-HARNESS-CROSS-SENSE-POSTDEPLOY-C1-
20260706-v1.md`. Attempted a direct manual probe (waking `wc`,
immediately calling `/bundle:...`) twice — both times the substrate was
already back asleep (confirmed: still on the same continuous
sleep/dream loop from the binding-windows and wake-gate dispatches,
now well over 2 hours of near-continuous DREAMING with a handful of
brief SLEEPING transitions, no real IDLE window). No live,
harness-driven or manual, end-to-end probe was possible.

**Step 5 — Compare:** Baseline and post-deploy both `PRECONDITION_NOT_MET`,
same `clean_slate`-class wall in both. No regression signal (nothing
that worked before now fails) and no positive live signal either — the
observation channel is closed, not the mechanism. Local mechanism
verification against the exact deployed commit is unambiguous and
positive (see above). **Verdict: PARTIAL**, same reasoning and same
root blocker as `GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-
20260706-v1** — not a new problem, the same one, still unresolved,
now confirmed to block a second consecutive mechanism dispatch's live
verification.

**Step 6 — State disposition:** Leave in place. No production mutation
beyond the deploy itself and two harmless `/wake` calls (both already
timed out by the time of writing); no probe data to wipe.

---

## Findings routed to Eve

1. **[Most important — needs a real decision, not just a note] The
   wire-in was NOT built as literally specified.** Full reasoning
   above. Recall is real, tested, and live — but it currently
   influences only `give_experience`'s own response, not what she
   says. Making it actually shape speech requires a deliberate design
   decision about how a second information source enters a
   organism-governed emission path without becoming a second brain —
   that decision is Eve's/Joe's to make, not mine to default into by
   literally following a dispatch whose premise about the codebase was
   stale.

2. **[Recurring, escalating] The continuous sleep/dream loop has now
   blocked live verification for two consecutive dispatches in a row**
   (binding-windows and this one). First flagged as an interesting
   observation in the binding-windows report; now a confirmed,
   repeated bottleneck on every future mechanism build's ability to
   prove itself live. Still not investigated (out of scope for both
   this and the wake-gate dispatch) — recommend this become the next
   dispatch's actual subject, given it is now the reason every
   acceptance scenario in the harness library returns
   `PRECONDITION_NOT_MET` rather than a real verdict.

3. **[Reconfirmed, third time] Identity-file consistency held through
   this deploy's restart** — no recurrence of the wake-gate dispatch's
   second-occurrence finding this time. Worth noting as a data point
   (not a resolution) for whatever investigates that finding: three
   real restarts since the original fix (binding-windows' own deploy,
   wake-gate's deploy, this deploy), one had a fresh divergence
   (caught during the wake-gate dispatch), two did not.

4. **[Confirmed, scenario-design] Both acceptance scenarios
   (`binding_windows_acceptance.yaml`, `cross_sense_recall_
   acceptance.yaml`) require `clean_slate: tick=0`**, which is
   unattainable on a live, continuously-running substrate outside the
   instant right after a fresh wipe — reconfirms
   `GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1`'s Finding 6, now with
   a second, independent scenario hitting the identical wall.

---

## Rollback

`aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-
service-lb --task-definition dsf-ai-task:540 --force-new-deployment`
restores the pre-cross-sense-recall state. Not executed — kept, per
Step 6.
