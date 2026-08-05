# GL-RPT-SENSORY-ORGANISM-QUEUE-BUILD-C1-20260707-v1

**doc_id:** GL-RPT-SENSORY-ORGANISM-QUEUE-BUILD-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT. Routed per the dispatch's own explicit instruction.** The core
fix works and is confirmed correct — moving the 64x `neuron.step()`
calls off `_autonomy_tick`'s synchronous path genuinely solves the
regression this whole series has been chasing. But the specific
priority scheme built ("word queue keeps priority") turned out, under
testing, to mean *absolute* priority — any word item, no matter how
small, completely starves the sensory queue — and real, sustained word
traffic (which I directly observed live in production earlier tonight,
independent of anything in this dispatch) keeps the word queue
non-empty for extended periods. That is exactly this dispatch's own
named halt condition: **"Queue backlog grows unboundedly during
sustained sensory input."** Not deployed. Code committed for the fix to
build on.

---

## What was built

**`dsf_ai_service/substrate/wave_summary.py`**: `push_wave_summary_to_organism`
rewritten to enqueue instead of stepping neurons directly. Skip-when-
empty is unchanged. For each of the six non-word hemispheres (H0-H4,
H6 — H5/H7 are the language-band hemispheres per `topology.
HEMISPHERE_PRIMARY_MODALITY`, explicitly skipped since word content
already reaches the organism through the existing word queue),
`guala._enqueue_organism_sensory(hemi.hemi_id, input_signal, tick)` is
called and `sensory_organism_enqueued` fires with the real band/
amplitude.

**`dsf_ai_service/v4/gualaloom_v5_engine.py`**:
- `Guala.__init__` gains `self._organism_sensory_queue = queue.Queue()`
  (eager, unbounded — matching the dispatch's given snippet exactly).
- New `_enqueue_organism_sensory(hemi_id, input_signal, tick)`. One
  addition beyond the dispatch's literal one-line body: it also calls
  `self._ensure_organism_worker()` first. Without this, a sensory push
  that happens to be the very first organism-bound work of a fresh boot
  (e.g. `give_experience` before any word has ever been read) would
  enqueue into a queue nobody is draining, since the worker thread only
  starts on the word-path's own `_ensure_organism_worker()` call today.
  Flagged as a deviation, not silently added — matches the same
  pattern as `_enqueue_organism_remember`'s own call to the same
  method.
- `_organism_worker_loop` restructured: non-blocking check of the word
  queue first, then the sensory queue, then a short (0.1s) blocking
  wait on the word queue as the idle path (avoids busy-spinning when
  both are empty — not a tuned priority weight, just how one consumer
  thread watches two queues without a native "wait on either" 
  primitive). Sensory items call `hemi.step(input_signal, tick)` under
  `self._organism_lock`, then fire `sensory_organism_processed` with
  `wall_clock_delay`. The existing word-processing body is unchanged,
  just reached through the new branching.
- `hemi.step()` (not `cluster.step()` or direct `neuron.step()`) was
  the right entrypoint: each sensory work item is already hemisphere-
  specific (the input_signal was computed for that hemisphere's own
  band before enqueueing), and `hemi.step()` naturally applies it to
  every neuron in that hemisphere via its own unmodified `step()`,
  *and* gets Phase B/C (intra-hemisphere coupling propagation, J_ij
  refresh) for free — v3's original direct-neuron.step() approach
  deliberately skipped those phases to keep the synchronous cost lower;
  now that this runs off the critical path asynchronously, there's no
  reason to skip them, and doing the full step is more correct, not
  just more convenient.
- `_organism_lock` genuinely exists and is live (`self._organism_lock =
  threading.Lock()`, actively acquired at the organism-save point and
  one `recall()` call site) — not something to invent. One documentation
  inconsistency noticed in passing, unrelated to this build: a comment
  near the save-point call claims it's "the only remaining `_organism_
  lock` acquisition anywhere," which isn't quite true (the `recall()`
  call site also takes it) — noted for the record, not something this
  dispatch asked me to reconcile.
- `WAVE_ATLAS_DECAY_ENABLED`'s default flipped from `"1"` to `"0"`,
  per this dispatch's "Abandons wave-atlas decay series... Not
  deploying decay work" — the code stays, the default now matches
  "not exercised in this deploy," and can be flipped back with no code
  change if it's revisited later.
- New `WAVE_SUMMARY_ENQUEUE_ENABLED` (default `"1"`) gates the whole
  enqueue-and-push block, per the dispatch's own "Rollback: task-def
  revert or WAVE_SUMMARY_ENQUEUE_ENABLED=0."

## Local verification

**The core fix is real and confirmed.** Same controlled measurement
approach as the wave-atlas-decay report: `_autonomy_tick()` on an
identically-prepared organism now costs single-digit-to-low-hundreds
of milliseconds for the *enqueue* work (7.7ms on one run, ~103ms on
another, noise from organism state — never the 246-290ms the
synchronous version cost). `sensory_organism_enqueued` and `sensory_
organism_processed` both fire with correct payloads; in an isolated
test (5 words read, no artificial contention), all 6 sensory items were
processed within 2-23ms of being enqueued — comfortably inside the
dispatch's own "<5s target."

**The halt-triggering finding.** Ran three escalating concurrency
tests:
1. Sensory-only, no word traffic: queue drains completely and
   immediately (0 remaining). Confirms the mechanism itself is sound in
   isolation.
2. Sensory + a *realistic* word cadence (one word every 150ms, roughly
   matching normal reading pace) together for 8 seconds, then stopped
   both: after the stop, the word queue drained slowly but steadily
   (35 → 32 → 24 → 13 over the next ~30 seconds) — consistent with
   organism word-processing being genuinely slow (confirmed via this
   session's own earlier live production readings: 795-2545ms per
   organism-worker item during real reading, independent of anything in
   this dispatch). **The sensory queue did not move at all** during
   this entire window — not partially, not slowly, exactly zero items
   processed while the word queue had anything left in it.
3. Same setup, watched continuously for 40 more seconds waiting for the
   word queue to reach exactly zero: it never did (7 items still
   remaining at the 40s mark). The sensory queue: still stuck, now at
   895, having grown slightly from residual enqueues before the stop
   signal took effect.

**Root cause, understood precisely, not just observed:** the worker's
"check word first" step uses a non-blocking `get_nowait()` — this
succeeds (finds an item) as long as the word queue has *anything* in
it, however small. It never partially yields to sensory; it's absolute
priority, not weighted or interleaved priority. Given that real,
sustained reading sessions keep the word queue non-empty for minutes
at a time in actual production (directly observed, this session, well
before this dispatch existed — organism-worker backlogs of 500-2000+
items during active reading are a known, standing condition, not
hypothetical), this design would starve the sensory queue for
comparably long stretches under real load — and if sensory content
keeps arriving during that stretch (which it will, every autonomy-tick,
whenever the wave field has anything in it), the backlog has no reason
to ever shrink. This is precisely "queue backlog grows unboundedly
during sustained sensory input," confirmed with real, repeated test
evidence, not inferred from a single run.

## Why this halts here rather than being patched in-flight

"Word queue keeps priority" is explicit in the dispatch text, and I
implemented the most literal reading of it (word always wins if
anything is queued). The fix — some form of guaranteed sensory
progress even under a real word backlog (round-robin instead of strict
priority, a small guaranteed sensory slice per loop iteration, a cap
on how many consecutive word items can be drained before a mandatory
sensory check, etc.) — is a genuine change to the priority *mechanism*
itself, which "DO NOT: ... Tune queue sizes or worker priorities"
names directly. Whether "priority" was meant as "absolute" or "weighted
but word-favored" is a real design question, not an implementation
detail I should resolve by guessing.

## Recommendation

The enqueue-based architecture is sound and worth keeping — it
provably removes the synchronous cost that caused the original
regression, with clean isolated verification to back it up. The one
open question is purely about how the two queues share one worker
thread when both are genuinely busy at once. Options surfaced, not
decided:
1. Round-robin: alternate which queue gets checked first each loop
   iteration, rather than always word-first.
2. Bounded word streak: drain up to N word items (a small, fixed
   number) before mandatorily checking sensory once, regardless of
   whether more word items remain.
3. Time-boxed fairness: after word queue has had priority for longer
   than some short wall-clock budget, force a sensory check regardless
   of word-queue state.
4. Accept it as designed and rely on `sample_wave_summary`'s already-
   cheap cost (0.03-0.05ms, confirmed in the wave-atlas-decay report)
   plus a bounded sensory queue size (a maxsize, matching the word
   queue's own `maxsize=2000` with drop-and-count-under-backpressure
   behavior) to make "unbounded" impossible even if starvation during
   heavy reading is tolerated as a real, accepted trade-off — this
   would need "tune queue sizes" to be back in scope, so flagging
   rather than assuming.

## What was NOT done

Not deployed — no backup, no harness run, no task-def touched. Code
committed to `guala-live` (the fix is real and worth keeping; only the
priority-sharing detail needs another pass) with
`WAVE_SUMMARY_ENQUEUE_ENABLED` defaulting to `"1"` in the code as
written (matching the dispatch's own text) — moot for now since this
commit was never deployed. Production is untouched, still on `5a5bede`
(task:542).
