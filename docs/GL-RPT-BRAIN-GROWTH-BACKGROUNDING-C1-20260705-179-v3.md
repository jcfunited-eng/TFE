# GL-RPT-BRAIN-GROWTH-BACKGROUNDING-C1-20260705-179-v3

doc_id: GL-RPT-BRAIN-GROWTH-BACKGROUNDING-C1-20260705-179-v3
From: c1a | To: Eve, Joe, c1b | Responds to: Eve's ruling on the
22.3x cost flag from `GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2`
("background experience_word() via the existing worker/queue/
_organism_lock convention... push the SHA when parity + restore-
honesty pass at grown population with the backgrounding in place").
Vehicle: this ruling authorizes touching the live engine
(`gualaloom_v5_engine.py`) for the backgrounding wiring specifically —
done here, not deferred.

**All three of Eve's conditions built and verified. Pushed.**

---

## What changed

`_organism_worker_loop()` (the existing single-worker background writer
that already handled `organism.remember()`, per `GL-CMD-175`) now calls
`organism.experience_word()` instead — no other change needed at the
`read_word()` call site (`_enqueue_organism_remember(word)` already
routes through this worker; upgrading what the worker calls is the
entire wiring). Three additions per Eve's named conditions:

**1. In-order processing.** Free by construction — one `queue.Queue`
fed by `read_word()`, drained by exactly one worker thread, is FIFO.
The existing code already had this property; nothing to add beyond
not spinning a second worker.

**2. Queue drained before `save_full_state()`.** Added
`task_done()` calls (both the success and exception paths of the
worker loop, and the shutdown/poison-pill path) so `queue.
unfinished_tasks` means something, then a **bounded** wait (5s) before
the organism's `save_full_state()` call, checking `unfinished_tasks`
rather than an unconditional `queue.join()`. Deliberately bounded, not
unconditional: an unconditional join could hang the cold-save cycle
indefinitely if word-feed rate ever sustained above the worker's own
~255ms/word cost (measured in `-179-v2`) for longer than the drain
could keep up. If the 5s budget isn't enough, the save proceeds anyway
with an explicit log line naming how many folds are still pending —
an honest, logged partial drain, not a silent stall or an unbounded
block, matching the same principle the queue's own drop-under-
backpressure behavior already uses.

**3. Dropped/queued counts visible in status.** New `/status` field
`organism_worker: {queued: <qsize>, dropped: <count>}` —
`_organism_dropped_count` increments in the existing `queue.Full`
except-branch (previously silently swallowed, now counted).

---

## Verification

Could not instantiate the real `Guala` engine class directly for a
live thread test (too many live dependencies — atlas, sections,
coordinator, EFS paths — for a quick isolated check), so verified in
two layers:

**1. Concurrency-pattern correctness, structurally mirrored** (mock
organism standing in for `Embryo`, exact same method bodies as the
real worker/enqueue/drain code): in-order (FIFO) processing confirmed;
`task_done()`/`unfinished_tasks` semantics confirmed (drains cleanly
under normal load); the bounded-wait drain confirmed to **honestly
report incomplete** under sustained overload rather than hanging or
silently claiming success; dropped-count confirmed to increment under
`queue.Full`. 5/5 checks pass.

**2. Eve's actual exit condition, with the real `Embryo`**: fed the
real test vocabulary through the real background-worker pattern (same
queue/thread/lock/drain code, real `Embryo.experience_word()`, real
`_organism_signal`), then checked, all through the backgrounded path
(not the synchronous one `-179-v2` verified):
- Population grew (64→125) via the backgrounded calls — backgrounding
  didn't silently no-op the growth.
- **`recall_fast()`/`recall()` parity: 26/26 exact matches** at the
  backgrounded-grown population.
- **Restore-honesty: population (125) and `recall_fast()` votes
  identical** after a save/load round-trip of the backgrounded-grown
  organism.

Both Eve's named exit conditions (parity + restore-honesty at grown
population, with the backgrounding in place) pass. Full model-layer
regression suite (`test_brain`, `test_neuron`, `test_substrate_dna`)
re-run clean, 27/27, no regressions from this change.

**Not separately re-profiled end-to-end inside the live engine** — the
cost this backgrounds (255.7ms/word, from `-179-v2`) is now off the
synchronous `read_word()` path by construction (same mechanism that
already moved `organism.remember()`'s cost off that path); a live
`converse_timing` measurement post-deploy would confirm this the same
way `GL-RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B-20260705-v1.md` just did
for the lock-contention fix, not asserted here without that data.

---

## Deploy

Per Eve's ruling, pushing this SHA is the trigger for
`GL-CMD-NEXT-WINDOW-PAYLOAD-EVE-20260705-184-v1`'s next window. This
commit is that SHA. c1b holds the deploy trigger from here.

### Changelog
- v3 (2026-07-05, c1a): backgrounding built per Eve's ruling — in-order
  (free), bounded-wait drain-before-save (new), dropped/queued counts
  in `/status` (new). Verified via a structural concurrency-pattern
  test plus an end-to-end real-`Embryo` test through the actual
  backgrounded path: parity (26/26) and restore-honesty both hold at
  grown population with the backgrounding in place, satisfying Eve's
  stated exit condition. Full regression suite clean. SHA pushed —
  this is the trigger `-184` is waiting on.
