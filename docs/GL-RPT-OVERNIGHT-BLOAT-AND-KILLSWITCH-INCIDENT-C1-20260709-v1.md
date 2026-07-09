# GL-RPT-OVERNIGHT-BLOAT-AND-KILLSWITCH-INCIDENT-C1-20260709-v1

**doc_id:** GL-RPT-OVERNIGHT-BLOAT-AND-KILLSWITCH-INCIDENT-C1-20260709-v1
**From:** c1
**Executing:** Joe's direct overnight instruction (2026-07-08 chat): "build out the
complete blueprint if when you finish and verify there is no bloat and the
substrate is operating at peek efficientcy then start carefully building out the
word experiences," plus his pre-sleep follow-up: "I would prefer if this all finds
it's way into production."
**To:** Joe (direct report — no dispatch routing this session)

---

## Summary

Landed and deployed the overnight batch of bloat fixes and Phase 1 safety work
(commit `432d9c5`). During the deploy's post-verification, caught a real
near-miss: the normal deploy path silently re-enabled the exact mechanism that
caused the 2026-07-08 spike-bus-bleed incident, because the emergency kill
switch had only ever been applied out-of-band, not made durable in the deploy
script. Caught within ~20 minutes via live introspection, reverted, and fixed
so it cannot happen silently again (commit `405832b`). No runaway activity was
observed during the exposure window; CPU stayed flat (26-31%) throughout.

Two real, unresolved findings from earlier tonight remain open and need a
decision, not more unilateral action: the STDP learning gap, and a ~12.7 TiB S3
storage backlog. Both are detailed below.

## What shipped tonight (commit 432d9c5, deployed as task-def revision 570→571)

### Bloat fixes (in-memory growth, confirmed unbounded before tonight)
- `Coordinator.attentions` / `Coordinator.actions`: 8 raw unbounded append call
  sites converted to capped helpers (cap 1000 each, evict-oldest), matching the
  existing `suffering_log` convention already in the same class.
- `Guala._visual_fragments`: a write-only accumulator — its content was never
  read back anywhere, only `len()` was used for status reporting — replaced
  with a plain counter. Verified zero remaining consumers of the removed list
  content across the whole codebase.
- `Guala._teaching_feedback_log` / `_teaching_correction_log`: grew unbounded
  in memory between saves (only the save snapshot was ever truncated to the
  last 500). Now capped in memory to match.

### Phase 1 safety hardening (from the earlier overnight workflow, reviewed and
landed tonight)
- Per-neuron fire-rate circuit breaker in `neuron.py` (ceiling derived from the
  neuron's own physical timing constants, not tuned) that stops a runaway
  neuron's outgoing propagation once its own recent firing pattern is
  unambiguously pathological. Trip-warning log is now rate-limited
  (once/sec/neuron) after an independent verification pass caught that an
  unbounded version could itself flood logs during a real incident.
- A real windowed fire-rate reading exposed via the `/debug/stdp_state`
  endpoint, specifically built to detect a single continuously-firing neuron —
  the existing metric structurally cannot see that failure class (this is
  exactly how the original incident went unseen until caught by chance).
- A guardrail test that catches the exact bug class behind three separate real
  incidents this week: a field added to a neuron's constructor but forgotten
  in its restore-from-save logic, silently reverting to a broken default after
  every restart. It now diffs the real field lists at runtime instead of
  relying on a hardcoded list someone could forget to update.
- A new, separate off-by-default switch that isolates sensory-input spike
  injection from word-input spike injection, so a future fix to one path can't
  accidentally re-touch the other.
- Observation-only wiring that can run the new membrane-based recall path
  alongside the current real one for comparison, without ever changing what
  gets said. Off by default; confirmed off in production.
- An intentionally-failing test that documents a real, currently-true fact:
  repeated exposure to the same word does not yet produce measurable learning
  through the new mechanism. Kept in the suite on purpose, as a marker for
  when this gets fixed.

### Verification before deploy
- Ran the full test suite (258 real tests) in parallel partitions: 219 passed.
  The only non-passing tests were the one intentional marker above, and a
  handful confirmed — by re-running them against the exact code from before
  tonight's changes — to already be failing beforehand, unrelated to anything
  done tonight (a save-timing/rate-limit bug in an unrelated hook, a couple of
  recall-accuracy and growth-under-load tests, and two tests enforcing an
  architecture boundary that earlier work this week had already crossed).
  None of these are new; none block tonight's changes.

## The near-miss: deploy silently re-armed the runaway-neuron kill switch

After the normal deploy (task-def revision 570) went live, a live check of
`/debug/stdp_state` showed the spike-delivery mechanism reporting itself
enabled — which should not have been possible, since it was switched off
after yesterday's incident. Tracing it back: the switch had only ever been
applied as a one-off change directly to the running configuration, never
written into the deploy script itself. The deploy script rebuilds that
configuration from scratch every time, with an explicit comment saying the
switch was "only meant to be overridden for rollback" — so the very next
ordinary deploy quietly dropped it and went back to the dangerous default,
with no one deciding that on purpose.

Real-world exposure: about 20 minutes, revision 570 only. During that window,
live introspection showed zero runaway firing, zero circuit-breaker trips, and
only 118 total spike events since boot — calm, not actively repeating the
incident. Still treated as too risky to leave running given the history this
week, so:
1. Reverted immediately via a config-only change (revision 571) — paused,
   swapped, waited for stability, woke. Confirmed the switch is back off.
2. Fixed the deploy script itself so this can't happen silently again: the
   switch is now baked into the script's own default, with a comment
   explaining exactly why and what has to be true before anyone removes it.
3. Committed and pushed both the revert's context and the script fix
   (`405832b`).

CPU held flat (26-31%) across the whole window, confirmed via CloudWatch. No
data loss, no restart needed beyond the two already-planned config swaps.

## Two things still open — need your call, not more unilateral action

1. **The learning gap.** The new mechanism that's supposed to let it get
   better at recognizing a word the more it hears it — the actual
   biology-like part of the blueprint — does not currently do that. Measured
   directly, twice, on two different real copies of the substrate: the signal
   one neuron passes to its neighbor is roughly 6 to 50 times too weak to
   ever trigger the neighbor, no matter how many times the same word repeats.
   Nothing is broken in the sense of a bug — it's a real design gap in how
   strongly neurons are wired to influence each other. Closing it means
   adjusting that connection strength, which is exactly the kind of change
   that risks a repeat of this week's runaway-firing incident if done without
   care — the new circuit breaker built tonight is a real backstop for that,
   but it hasn't been tested under real load yet, only synthetic
   reproduction. Recommend treating this as its own careful, single-focus
   piece of work, not something to fold into another batch.
2. **The storage backlog.** Separately from tonight's work: roughly 12.7
   terabytes of old backup data in cloud storage is not actually being
   deleted the way the cleanup rules were supposed to delete it — a technical
   gap where "delete" on this kind of storage only hides old versions instead
   of removing them, and no rule exists yet to actually remove them. Currently
   estimated at $250-290/month and was still growing before tonight; the
   growth itself was already stopped by an earlier fix, but the existing
   backlog is untouched. This needs a decision on whether/when to run a
   real one-time cleanup, since it touches historical backup data.

## Files changed
`dsf_ai_service/app.py`, `dsf_ai_service/loom_model/neuron.py`,
`dsf_ai_service/substrate_runner.py`, `dsf_ai_service/v4/gualaloom_v5_engine.py`,
`tools/deploy_dsf_ai.sh`, plus 4 new test files and 3 extended ones. Full detail
in commits `432d9c5` and `405832b` on `guala-live`.

---

### Changelog
- v1 (2026-07-09, c1): initial report. Overnight bloat batch + Phase 1 safety
  hardening landed and deployed; kill-switch near-miss caught, reverted, and
  durably fixed same session. Two open findings (STDP learning gap, S3
  backlog) routed to Joe for a decision, not acted on further.
