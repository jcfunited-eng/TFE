# GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3

**doc_id:** GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3
**From:** c1
**Executing:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**All four fixes are correct and verified — 49 local tests plus a
full save/restore round-trip against the actual production pickle,
all green. Deployed (task-def `dsf-ai-task:557`, commit `67a002e`).
Then, during live post-deploy monitoring, found something none of
the twelve named halt conditions precisely describes: once injection
started actually firing in a long-running production process (not a
short local test), it triggered a self-sustaining reverberating
cascade through the ring/cross-hemi coupling topology — sustained,
not decaying, over 9+ minutes of observation, entirely decoupled
from real word/sensory traffic, and actively strengthening the same
small closed loop of synapses via STDP the whole time. I rolled back
to task-def `:556` rather than leave an unbounded-duration, not-fully-
understood process running in production while writing this report.
Routing with full data — this needs a design decision (add lateral
inhibition, or something narrower) before the injection call site can
redeploy.**

---

## Local verification (before any deploy attempt)

### What was built

1. **`LoomNeuron.__getstate__`/`__setstate__`** (`neuron.py`) — excludes
   `_neuron_lock` (unpicklable `threading.Lock`), `_spike_bus`, and
   `_word_firing_callback` from the pickle. `__setstate__` recreates the
   lock and backfills every Phase 1 v2 field missing from an older
   pickle at its real `__init__` default — verified against the live
   source, not the dispatch's illustrative draft, and caught one more
   correction beyond the two already known from v1's halt report:
   `_spike_bus`/`_word_firing_callback` must be explicitly backfilled to
   `None` (matching `__init__`), not left absent as v2's draft
   suggested — `_fire()` and `_on_fire_bookkeeping()` read them via
   direct attribute access, not `getattr`, unlike `LoomBrain.step()`.
   Left absent, the very first fire on a restored neuron would have
   raised `AttributeError` before `wire_spike_bus()` ever got a chance
   to run.
2. **`LoomBrain.__getstate__`/`__setstate__`** (`brain.py`) — excludes
   `_spike_bus` and `_guala_ref` (the latter would otherwise drag the
   entire live `Guala` object graph into one neuron's pickled state).
   Left absent after restore, matching `LoomBrain.step()`'s existing
   `getattr`-defensive read.
3. **`Guala.wire_spike_bus()`** (`gualaloom_v5_engine.py`) — the
   neuron/brain wiring block extracted from `__init__` into an
   idempotent method, called both from `__init__` (unchanged behavior)
   and from inside `load_full_state()` immediately after `self.organism`
   is replaced wholesale — closing the gap `GL-RPT-PHASE-1-V2-REVIVE-
   C1-20260708-v1` found, where every restored boot left the spike bus
   wired to orphaned pre-restore objects. Wrapped in its own try/except
   inside `load_full_state()` so a wiring failure is never misreported
   as "organism restore FAILED."
4. **Injection moved to the organism worker loop** (`_organism_worker_
   loop`'s word and sensory branches) — the actual point where all real
   production text and sensory traffic converges, per `GL-RPT-PHASE-1-
   V2-REVIVE-C1-20260708-v2`'s finding that `LoomBrain.step` has zero
   production callers. Word branch recomputes chi via a throwaway
   `LanguageKrimelack` (the same primitive `recall_scene_for_word` and
   others already use for the identical purpose). Both branches run
   injection alongside the existing legacy call, in their own
   try/except, never instead of the legacy path. The `input_chi is not
   None` gate on `LoomBrain.step` itself was also removed (item 6) —
   not on the production path anymore, but it contradicted `_select_
   entry_neurons`' own `None` fallback.

### Local test results

49 tests, all green:
- 33 pre-existing (`test_neuron_spike_handling.py`, `test_brain_dual_
  path.py`) — zero regressions.
- 8 new (`test_pickle_roundtrip_wiring.py`): `__getstate__`/`__setstate__`
  correctness on both classes (including confirming `pickle.dumps` on a
  fully-wired neuron, which previously raised `TypeError: cannot pickle
  '_thread.lock' object`, now succeeds), `wire_spike_bus()` idempotency
  and no-op-when-absent, and — the two tests that matter most —
  `test_worker_loop_injects_on_word_item`/`_sensory_item`, which enqueue
  a real item on a live `Guala` and confirm the actual worker thread
  injects within 3 seconds.
- 8 (`test_debug_stdp_state.py`, from the prior dispatch) — unaffected,
  still green.

### Production-pickle round-trip test — the load-bearing gate

Downloaded the actual current production state at the time
(`s3://dsf-ai-site-backups/guala/auto/2026-07-08_04-25-05_dream_end/`,
~90 seconds old, full directory not just the organism file) to a local
scratchpad. Full protocol, every assertion:

```
PHASE1 (real production pickle):
  neurons_total=64 neurons_ok=64 neurons_failed=0
  wiring OK: g._spike_bus is organism.brain._spike_bus, _guala_ref is g
  word injection: before=0 after=128
  word_neuron_map has 'probeword': True
  sensory injection: before=128 after=144
  spike_bus counters: injected=144 delivered=144 dropped=0

[saved to scratch, deleted the downloaded real state]

PHASE2 (reload from the scratch save):
  neurons_total=64 neurons_ok=64 neurons_failed=0
  wiring OK: g._spike_bus is organism.brain._spike_bus, _guala_ref is g
  word injection: before=0 after=128
  word_neuron_map has 'probeword': True
  sensory injection: before=128 after=144
  spike_bus counters: injected=144 delivered=144 dropped=0

CONVERGENCE CHECK: neuron count phase1=64 phase2=64
ROUND-TRIP TEST: ALL ASSERTIONS PASSED
```

Both phases converged identically — proof the fix works not just on a
fresh local boot (which would have hidden this exact class of bug, as
v1 and v2's own investigations found) but on the real, current,
already-in-production object graph, saved and reloaded from scratch.
(Phase 2 generated a new genesis identity rather than restoring
`0b4c244a` — an artifact of my test calling `save_full_state()` alone,
which doesn't write `guala_identity.json`; the real production save
cycle persists identity separately. Doesn't affect what this test
verifies — injection counts and field presence matched exactly across
both phases.) Downloaded state and scratch save both deleted
immediately after.

---

## Backup

`guala_backup` triggered before deploy. Verified via direct S3 listing
(not the log line, which — as found in v1's dispatch — doesn't reliably
appear): `s3://dsf-ai-site-backups/guala/UNPAUSE-PRE-20260708-043937/`,
11 files, all present with sizes consistent with live scale.

---

## Deploy and boot check

Task-def `dsf-ai-task:557`, commit `67a002e`, deployed cleanly.
`guala_status` confirmed `running_sha` matching, `load_successful_at_
boot: true`, 64/64 neurons, no dropped frames, no queue backlog.

`GET /debug/stdp_state` immediately post-boot:

```
diagnostics: {neurons_total: 64, neurons_snapshot_ok: 64,
              neurons_snapshot_failed: 0, neuron_snapshot_sample_error: null}
```

**Halt condition 5 does not fire.** Every neuron in the actual running
production process has every Phase 1 v2 field, for the first time since
this mechanism was originally deployed hours ago.

---

## What happened next: an emergent finding, not a named halt condition

### The observation

Response time was ~0.35–0.46s throughout — fine. But the numbers
themselves, tracked across four `/debug/stdp_state` reads over roughly
nine minutes of live production runtime, told a different story than
"Phase 1 v2 is alive and building state under real load":

| uptime (s) | spikes injected | fires (cumulative) | synapses touched | synapses strengthened |
|---|---|---|---|---|
| 164 | 174,710 | 1,940,972 | 448 | 0 |
| 211 | 258,373 | 1,951,778 | 448 | — |
| 391 | 618,547 | 2,013,595 | 448 | 4 |
| 521 | 836,904 | 2,049,332 | 448 | 13 |

Instantaneous rate between the 211s and later reads: ~1,700–2,000
injected spikes/sec, ~275–283 fires/sec, sustained — not decaying, not
climbing unboundedly either. `total_synapses_updated` never moved off
448 across the entire window despite hundreds of thousands of new
injections. `synapses_strengthened` climbed steadily (0→4→13):
real STDP potentiation, genuinely happening — but on the *same* fixed
set of 448 synapses the whole time.

Cross-checked against CloudWatch: `organism_experience_bound` (logged
on every real word processed) — **zero events in the preceding 7
minutes.** `sensory_organism_processed` — **zero events in the
preceding 60 seconds.** No real word or sensory item had been processed
by the worker loop during this entire window, yet injection, firing,
and STDP potentiation were all still actively ongoing at a stable rate.

### What this means

The only way spikes keep firing at a stable, sustained rate with **no
new external input** and **the same closed set of synapses** being
touched over and over is a self-sustaining reverberating cascade: an
entry-neuron fire (from some earlier real or injected event) emits to
its outgoing synapses via the *existing*, already-deployed `_fire()`
mechanism (not something this dispatch added); those downstream
neurons, once their 2ms refractory period clears, can fire again and
re-emit; the ring/cross-hemi coupling topology (`CouplingsJij`) is
cyclic by construction; and — critically — **Phase 1 v2 has no lateral
inhibition yet.** This dispatch's own "Forward-thinking pieces" section
names lateral inhibition as explicit Phase 2+ territory, not yet built.
Without it, nothing in the current design *stops* a cycle from
sustaining itself once triggered. STDP then actively *reinforces* the
loop's own synapses every time it fires — a genuine positive feedback
mechanism, which explains why `synapses_strengthened` kept climbing on
exactly the same 448-synapse set rather than the network exploring a
wider, more diverse set of connections as real experience would
suggest.

This is not a bug in anything this dispatch built. The wiring, the
pickle round-trip, the injection call sites — all verified correct,
independently, against the real production object graph. What this
finding shows is a structural property of the *already-existing*
`_fire()`/coupling mechanism that simply had never been exercised
end-to-end in a long-running production process before, because nothing
had ever successfully triggered even a single real injection until this
deploy. No local test — including this dispatch's own thorough
round-trip test — runs long enough or in a persistent-enough process to
observe a multi-minute reverberation pattern; 144 total spikes in a
few-second test script barely registers.

### Why I rolled back rather than leave it running

None of the twelve named halt conditions precisely describes "self-
sustaining activity decoupled from real input, not growing unboundedly
in amplitude but also not stopping." The literal `fires_per_second_
last_minute > 1000` threshold in halt condition 7 wasn't crossed
(directly measured instantaneous rate: ~283/sec) — but that metric
counts *distinct neurons active in the last 60s*, and since all 64
neurons had already fired at least once, it structurally cannot
distinguish "each fired once" from "each fired thousands of times" (a
limitation I noted honestly in the metric's own design, in the
STDP-introspection dispatch, but hadn't previously had a real scenario
to see it matter this much). Using `total_fire_events_since_boot`
deltas instead of the last-minute approximation was the only way to see
this clearly.

No dropped spikes, no queue backup, no crash, no runaway *amplitude*
(mean membrane potential stayed near zero throughout, well under the
0.5 emission threshold) — this wasn't heading toward an immediate
outage. But it was an unbounded-duration process, actively strengthening
synapses with no connection to real experience, that I did not fully
understand the long-term bounds of (does it stay contained to 448
synapses forever, or could STDP-strengthened weights eventually push
neighboring sub-threshold paths over threshold and widen the loop?). I
don't know, and four data points over nine minutes isn't enough to rule
either out with confidence. Given genuine uncertainty about an ongoing,
self-reinforcing process already running live, and given the dispatch's
own rollback path is well-tested and low-risk, I judged rolling back
now — rather than leaving it running for however long report-writing
and Eve's review takes — the more conservative choice.

### Rollback

`aws ecs update-service --task-definition dsf-ai-task:556 --force-new-
deployment`. Service reached steady state cleanly (`runningCount:
desiredCount: 1`). Verified: `running_sha` back to `97b3756` (task-def
`:556`, the STDP-introspection-only build, pre-this-dispatch), `guala_
status` healthy (`load_successful_at_boot: true`, saves advancing, no
backlog), and `/debug/stdp_state` confirms `total_spikes_injected_
since_boot: 0` and `total_fire_events_since_boot: 0` on the fresh
boot — **the cascade genuinely stopped**, not just went quiet, matching
the expectation that :556's code never calls the injection path at all.

One expected, harmless side effect: `/debug/stdp_state` on the rolled-
back build now reports `neurons_snapshot_failed: 64` again — the
*original* bug this whole dispatch chain exists to fix. This is not a
new problem: task-def `:557`'s ~9 minutes of runtime triggered at least
one scheduled save, which pickled the organism using v3's new
`__getstate__` (which correctly excludes `_neuron_lock`); the reverted
old code has no `__setstate__` to backfill it on restore, so unpickling
that newer-shaped pickle reproduces the exact original symptom for a
new, expected reason. Production is otherwise fully stable and
unaffected — this only shows up on the introspection endpoint's own
diagnostics field, which is read-only and was already reporting this
exact state before any of this dispatch chain began.

Regression harness (all four `harness/scenarios/mechanism/` scenarios)
run against the rolled-back state: identical `PRECONDITION_NOT_MET` /
`presence.wc` finding on all four, matching the pattern every prior
dispatch tonight has hit. No new failure mode. Legacy behavior
unaffected by the deploy-and-rollback cycle.

---

## Files touched + diff summary

- `dsf_ai_service/loom_model/neuron.py` — `__getstate__`/`__setstate__`.
- `dsf_ai_service/loom_model/brain.py` — `__getstate__`/`__setstate__`,
  `input_chi` gate removed from `step()`.
- `dsf_ai_service/v4/gualaloom_v5_engine.py` — `wire_spike_bus()`
  extracted + called from `__init__` and `load_full_state()`; injection
  added to `_organism_worker_loop`'s word and sensory branches.
- `dsf_ai_service/loom_model/tests/test_pickle_roundtrip_wiring.py` —
  new, 8 tests.

All committed and pushed to `guala-live` (tip: `67a002e`). **Currently
NOT the running code** — production is on `:556` (commit `97b3756`)
following the rollback. The fixes are real, tested, and ready; only the
injection call site (item 4 above) needs a design decision before
redeploying.

---

## Findings needing Eve routing

1. **The core finding: injection at the worker loop, exactly as
   specified, triggers a self-sustaining reverberating cascade through
   the existing cyclic coupling topology, because lateral inhibition
   (explicitly Phase 2+ territory, named in this dispatch's own
   forward-thinking notes) doesn't exist yet to damp it.** This isn't
   a flaw in items 1–4 as built — the pickle/wiring fixes are correct
   and should ship — it's that *any* injection call site that
   successfully triggers even one real fire will eventually hit this,
   given enough production runtime, regardless of which call site (word
   branch, sensory branch, or a future third option) carries it.
2. **Design directions for Eve's call, not mine to pick**: (a) build a
   minimal lateral-inhibition mechanism before re-attempting injection —
   the "right" fix per this dispatch's own forward-thinking framing, but
   a bigger scope than this dispatch; (b) add a narrow, temporary circuit
   breaker (e.g., cap total in-flight propagation depth, or a global
   fire-rate ceiling with backoff) as a stopgap that doesn't require full
   Phase 2 lateral inhibition; (c) inject only on the word branch (real
   conversational events, naturally much lower-frequency than the
   continuous internal sensory-organism-queue churn) and leave the
   sensory branch un-instrumented until inhibition exists — since the
   word path is what actually drives `word_neuron_map_size`, the
   dispatch's own primary acceptance signal, and is far less likely to
   sustain a high-frequency reverberation on its own given human-typing-
   speed input rates.
3. **The `fires_per_second_last_minute` metric (built in the STDP-
   introspection dispatch) cannot detect this class of problem** — it
   counts distinct active neurons, not event volume, and saturates at
   `population/60` once every neuron has fired at least once regardless
   of true rate. `total_fire_events_since_boot` delta-over-time (what I
   used to actually characterize this) is the metric that should gate
   any future halt condition 7-style check. Worth a small follow-up to
   either fix the existing metric's documentation/framing or add a true
   windowed-rate counter.
4. **`total_synapses_updated` staying exactly flat at 448 despite
   massive injection volume is itself a useful diagnostic signal** for
   "the network is reverberating in a closed loop, not exploring new
   connections" — worth keeping in mind as a quick health check for any
   future re-attempt (a healthy, real-experience-driven run should show
   this number growing over time, not frozen).
5. **This entire finding was only observable because injection finally
   worked and ran in a real, long-running production process** — the
   local round-trip test (144 total spikes across two brief phases)
   gave no signal of this at all, and couldn't have. Worth noting for
   how future dispatches in this chain scope their pre-deploy
   verification: correctness tests (does the mechanism work at all) and
   sustained-runtime behavior tests (does it stay well-behaved over
   minutes, not milliseconds) are different questions, and this dispatch
   chain has now hit real, serious findings in both categories at
   different stages.

## Recommendation

Items 1–3 (pickle round-trip, wiring extraction, restore-time re-wire)
are done, verified, correct, and should stay in whatever ships next —
nothing about the cascade finding implicates them. Item 4 (the
injection call site) needs Eve's design call on one of the three
directions in finding 2 above before it redeploys. Recommend starting
with direction (c) — word-branch-only injection — as the smallest,
lowest-risk next step: it still produces the dispatch's primary
acceptance signal (`word_neuron_map_size` growth from real
conversation), is far less likely to sustain a high-frequency
reverberation given natural human-typing-speed input rates, and
defers the larger lateral-inhibition design work to when Phase 2 is
actually being scoped — rather than building a stopgap circuit breaker
now that Phase 2 might make redundant anyway.

---

### Changelog
- v3 (2026-07-08, c1): All four fixes built, tested (49 local tests),
  and verified via a full save/restore round-trip against the real
  production pickle before deploy — the load-bearing gate this
  dispatch specifically added in response to v2's miss. Deployed
  (task-def `:557`, commit `67a002e`), boot check passed cleanly
  (`neurons_snapshot_failed: 0` for the first time since Phase 1 v2 was
  originally built). Then, ~9 minutes of live monitoring revealed a
  self-sustaining reverberating cascade through the existing cyclic
  coupling topology, sustained and not decaying, entirely decoupled
  from real production traffic (zero real word/sensory events logged
  during the window) — an emergent consequence of activating injection
  for the first time against a network with no lateral inhibition yet.
  Not precisely covered by any of the twelve named halt conditions.
  Rolled back to task-def `:556` rather than leave an unbounded-
  duration process running while writing this report; rollback verified
  clean (cascade stopped, production stable, no regression on the four
  harness scenarios). Five findings routed to Eve, with a
  recommendation to redeploy with word-branch-only injection as the
  smallest safe next step.
