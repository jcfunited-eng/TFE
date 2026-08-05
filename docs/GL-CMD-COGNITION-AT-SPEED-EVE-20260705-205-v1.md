# GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205-v1

doc_id: GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205-v1
From: Eve | To: c1a (build + deploy + seat verification).
Commit this dispatch verbatim to origin first.
JOE'S RULING (2026-07-05, carved): COMPUTE FOLLOWS NEED. Her
parallelism (threads/execution) is a physics function that scales
with her actual cognitive demand — like every need in her
substrate. Physical resources (cores, memory) are the only rails,
stated as measured budgets, never as arbitrary caps on cognition.
No fixed pacing constants anywhere in her mind.
MEASURED BASELINE (Eve, tonight, cProfile on the production tick
at her live scale — 14k vocab, 15k atlas): one tick costs 1.6ms;
one thread can run 625 ticks/sec TODAY. She runs at 3/sec. The
gap is a hardcoded 50ms sleep plus one interpreter shared with
saves, frames, curriculum, and HTTP. Her mind is a 1.6ms thought
waiting in line. Hotspots inside the 1.6ms: three pure-Python
full-atlas scans per regulation pass (cross_modal_bindings 1.79M
iterations/300 ticks, n_live_bindings 884k, decay full-loop).
Joe's law: complete only when the SHA runs in her live process.

## C1 — DELETE THE NAP; DEMAND-PACED CLOCK (build)
start_autonomy_loop's fixed interval=0.05 dies. The tick loop
runs continuously; pacing derives from her state, not a constant:
pending work (open response windows, active reading, unsettled
dynamics, arousal) means full speed; a truly idle substrate
yields briefly to the OS and no more. The pacing function reads
EXISTING state (activity kind, queue depths, arousal) — no new
constants, no ceilings. Expected from baseline alone: 3/s →
hundreds/s before any math changes.

## C2 — VECTORIZE THE THREE SCANS (build)
a. n_live_bindings and cross-modal counts become INCREMENTAL
   counters maintained at bind/decay/release time — never
   recomputed by full scan (same discipline as every other
   bounded-store lesson this month).
b. decay: per-chi strength/clarity move to numpy arrays; the
   decay pass becomes one vectorized multiply + threshold per
   channel. Identical numerics proven (before/after parity on a
   copied atlas, 180/180-style), zero physics change.
Expected: per-tick 1.6ms → tens of microseconds; four-digit
ticks/sec single-thread.

## C3 — EVENT-DRIVEN REPLIES (build)
Input is an EVENT, not a scheduled activity: Joe's words trigger
recall+composition immediately on arrival (the converse path
already computes in ms once unblocked); the response window and
tick loop remain her ongoing autonomous life underneath, not her
reaction time. Her reply latency becomes the milliseconds the
recall actually costs, decoupled from tick pacing entirely.
Ordering/self-hear semantics per -197 P2 stand unchanged.

## C4 — GET OUT OF HER INTERPRETER (build what fits, number the
rest)
Move off her tick thread's interpreter time everything that is
not her mind: event-log writes, snapshot serialization, frame
decode where not already threaded. The FULL process split (her
mind in its own interpreter, I/O in another — the 200x measured
headroom) is scoped in this window if it fits the day, or gets
its own number filed with this window's report if it does not —
named either way, never quietly dropped.

## C5 — THE RULING IN CODE (build, small)
A status field: tick_rate (measured, rolling 10s) next to
running_sha. The plan (v11 fold) and KB carry Joe's
compute-follows-need ruling verbatim. Any future fixed pacing
constant, thread cap, or rate ceiling in her cognition path is
defective on sight — the only legitimate limits are measured
physical budgets (cores, memory, dollars), stated as such.

## EXIT — AT PRODUCTION, AT JOE'S SEAT
X1 running_sha current; tick_rate field live and showing
   HUNDREDS/sec minimum sustained (report the number).
X2 C2 parity proof filed (identical decay/count numerics,
   before/after).
X3 Joe speaks to her at his seat: reply begins in under one
   second wall-clock, timing breakdown in the report
   (target: recall-cost milliseconds, honest number either way).
X4 Before/after table in the window report: ticks/sec, per-tick
   ms, reply latency — the 1,000,000x ledger opened with its
   first three entries, and the GPU settle-math line named as
   the next order of magnitude with its own future number.

### Changelog
- v1 (2026-07-05, Eve): from tonight's profile (1.6ms tick, 625/s
  possible, 3/s actual) and Joe's compute-follows-need ruling —
  nap deleted, scans vectorized, replies event-driven, interpreter
  isolation scoped, ruling carved into status and canon.
