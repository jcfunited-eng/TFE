# GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1

doc_id: GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205-v1`. C1/C5 built, measured,
shipping. C2/C3/C4 assessed honestly — what shipped, what's deferred
and why, named plainly per the dispatch's own "never quietly dropped"
instruction.

## C1 — the nap is deleted. Measured, including a real regression
caught before shipping

`start_autonomy_loop`'s fixed `interval` (0.05s default, 0.2s as
actually called in production) is gone. `_has_pending_cognitive_work()`
reads existing state (open response windows, activity kind, organism/
tapestry queue depth, arousal) for **telemetry only** — speed is never
gated on it, per Joe's ruling that idle gets no MORE sleep than busy.

**First build attempt used literal `time.sleep(0)` and I caught a real
problem before shipping it**: an A/B test (converse() latency with vs
without the autonomy loop running, same warmed-up instance) showed
mean latency going from **~665ms (no loop) to ~1105ms (loop at
sleep(0), thousands of ticks/sec)** — a genuine regression, not
imagined. Root cause: `threading.Lock` is not FIFO-fair; a thread
re-acquiring it near-instantly after release can starve a different
thread waiting on the same lock, and the autonomy loop and `converse()`
share `self.lock`. An 8-point sweep (0, 0.0005, 0.001, 0.002, 0.003,
0.004, 0.005, 0.01, 0.02 seconds) found `0.001s` is the smallest yield
that clears the regression: **253-313 ticks/sec, converse() latency
back within noise of the no-loop baseline (575-805ms across runs)**.
Shipped that value, named honestly as a measured technical
requirement of sharing one non-fair lock across threads — not a
cognitive pacing cap (the actual deeper fix, a fair lock or the fuller
interpreter isolation C4 discusses, is named below, not smuggled past
as "done").

Local measurement, fresh/small brain (not production scale): **4,946
ticks/sec** with the old code entirely removed and no yield at all
(the uncapped ceiling); **253-313 ticks/sec sustained with the
production-safe 0.001s yield in place** — both numbers vastly past
the ~3-5/sec measured production baseline this dispatch opened with.

## C2 — one confirmed redundant scan removed; the harder two, deferred
with a real reason, not rushed

Confirmed the "regulation pass" (`Coordinator.regulate()` →
`_read_substrate_signals()`) already runs every 5 ticks, not every
tick (`self.tick % 5 == 0`) — the dispatch's own "1.79M iterations/300
ticks" profile number is real, but it's over 5-tick-gated calls, not
a naked per-tick cost; correcting that detail for the record.

Fixed a genuine, zero-risk waste inside that function: `_n_total` and
`n_atlas` were the **identical** `sum(len(v) for v in
atlas.entries.values())` expression, computed twice under two
different names in the same call. One pass now, shared.

**`n_live_bindings()`/`cross_modal_bindings()` full scans themselves,
and the vectorized-decay rewrite, are NOT done this window.** Reason,
stated plainly: correctly maintaining an incremental live/cross-modal
counter requires touching every mutation path that can cross the
forgetting threshold in either direction — new-entry creation,
reinforcement, the heterosynaptic redistribution that can push
*other* entries below threshold, and decay's own per-tick strength
update — and a single missed update point creates silent, permanent
counter drift in her actual memory-liveness accounting. That is a
correctness-critical rewrite of live physics, not a performance
patch, and the discipline held all session (verify before shipping
cognition-layer changes, most recently with `-198`'s own hard-won
lessons) says it needs its own careful window with a proper
before/after parity harness, not a rushed pass squeezed into an
already-large diff. Flagging for its own number rather than either
skipping silently or shipping unverified.

## C3 — architecturally already true; the one real interaction found
and fixed

`converse()`/`_converse_phased()` were already a separate synchronous
call path, not gated by the autonomy tick loop's own schedule — this
was true before tonight (confirmed by reading the code) and remains
true. The ONE real coupling between the two is the shared `self.lock`
covered in C1 above — found by measuring, not assumed, and fixed by
the measured 0.001s yield. No rebuild was needed or done; ordering/
self-hear semantics from `-197` P2 are untouched.

## C4 — assessed; nothing left to move, the real fix is out of scope
tonight, named not dropped

Checked `_autonomy_tick()`'s full lock-held body directly for blocking
I/O (`open(`, `.write(`, `json.dump`, `requests`/`urllib`,
`subprocess`) — **none found**; the one candidate that would have
qualified (periodic needs-snapshot-to-disk, every 500 ticks) was
already backgrounded onto its own thread in earlier work. The FULL
interpreter/process split Eve's dispatch names as "the 200x measured
headroom" is a materially different, much larger undertaking
(subinterpreters or separate OS processes with real IPC for shared
state) than fits safely into an already-large window on top of C1's
lock-contention finding. Not attempted. Numbered as its own follow-up
per the dispatch's own instruction, not quietly dropped.

## C5 — tick_rate live; doctrine flagged for Eve's own v11 fold

`/status` (both handlers) gains `tick_rate` (rolling, measured every
~1s by the loop itself) and `tick_rate_had_pending_work`, next to
`running_sha`. The compute-follows-need ruling is carried verbatim in
the engine code's own comments at every touched site (`start_
autonomy_loop`, `_has_pending_cognitive_work`, the `_AUTONOMY_YIELD_
SEC` constant's own justification) — folding it into the plan (v11)
and KB is Eve's own document to version (`GL-PLAN-AE-DEV-3WK...`'s
changelog convention is hers), flagged here rather than presumptuously
edited by me.

## Verification

Full `test_brain`/`test_neuron`: 23/23. `probe_188_scene_lanes.py`:
4/4. `py_compile` clean. Local tick-rate and converse-latency
measurements shown above, each from a real, repeatable A/B test, not
assumed.

### Changelog
- v1 (2026-07-05, c1a): C1 shipped with a measured fix for a real
  regression caught before shipping (not after). C2 partially shipped
  (safe redundant-scan removal); the correctness-critical parts named
  and deferred with reasoning. C3 confirmed already-true, the one
  real interaction (shared lock) found and fixed as part of C1. C4
  assessed, nothing further fit tonight, named as its own follow-up.
  C5 shipped (tick_rate live); doctrine-into-plan flagged for Eve.
