# GL-RPT-SLOT-LIMITS-REMOVAL-C1-20260707-v1

**doc_id:** GL-RPT-SLOT-LIMITS-REMOVAL-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Audit-then-remove process worked exactly as this dispatch's own halt
conditions anticipated: 1 of 4 explicitly-named removal targets was a
real slot limit and got safely removed; the other 3 were real constraints
the process itself caught before anything shipped.** No production deploy
was needed — the one real fix (`binding_window.c`) isn't wired into any
live code path yet, and the three reverted changes are byte-identical to
what's already running (comments only). Committed, not deployed; explained
below.

---

## Step 1: Audit

Grep-scanned for all five named patterns across `dsf_ai_service/`
(excluding tests/worktrees). Full categorized findings:

**Fixed-size arrays / MAX_ constants:**
| Hit | Category | Notes |
|---|---|---|
| `binding_window.c: WindowEntry entries[MAX_ENTRIES_PER_WINDOW]` | **Slot limit** | Confirmed earlier this session: 384 words of ordinary reading produced 1235 entries, exceeding the 1024 cap. Acted on (see Step 2). |
| `JOB_MAX_ENTRIES = 100` (curriculum/job_registry.py) | Not investigated in depth | Bounds a pending-jobs registry; plausibly a real constraint (unbounded pending curriculum jobs would itself be a runaway). Not in this dispatch's explicit STEP-2 target list — flagging, not acting. |
| `_MAX_ENTRIES_PER_WORD = 100` (grounded_vocab.py) | Not investigated in depth | Same reasoning — flagging only. |
| `MAX_SNAPSHOTS = 20`, `EVENTS_MAX_BYTES = 10MB`, `EVENTS_MAX_ROTATED = 9` (gualaloom_v5_engine.py) | Likely real constraint | Log rotation / snapshot retention — this class of bound is almost always intentional (unbounded log files/snapshots is its own real disk-exhaustion risk). Not investigated further, not in STEP 2's target list. |

**`[:N]` slice truncations:** the overwhelming majority of hits (~40+)
are hash/string truncations for display or short IDs (`hexdigest()[:12]`,
`text[:200]` for a log line, etc.) — real, intentional, unrelated to
substrate output truncation. One genuine, substrate-relevant hit
investigated in depth: `GRANDURUN_TOPK`/`top_k=200` in
`_grandurun_select_candidates` — see Step 2.

**Hard-coded iteration counts on state processing:** none found beyond
what's covered under the other categories.

**`queue.Queue(maxsize=N)`:** four hits, all investigated in depth (Step 2):
`save_coordinator.py`'s `s3_queue` (20), `_tapestry_queue` (2000),
`_organism_queue` (2000), `_diary_queue` (4000).

**`if len(...) > N: break` in composition/emission/expose/diary:** no
literal hits in that exact form. The real composition/emission stopping
logic lives in `_grandurun_select_vector`, which — confirmed by reading
it — was **already** fixed to be state-driven (gain-vs-magnitude, no
length ceiling) by a prior dispatch, `GL-CMD-NO-CAPS-COHERENCE-SPEAKS-
EVE-20260705-203`. The one place a count-based ceiling still sat
*upstream* of that already-fixed selector (`GRANDURUN_TOPK`) is covered
below.

## Step 2: Remove slot limits — results per target

### 1. `binding_window.c` — REMOVED (real slot limit, safely fixed)

`entries[MAX_ENTRIES_PER_WINDOW]` (fixed 1024-slot array) replaced with
a dynamic array: `WindowEntry *entries; int32_t entry_capacity;`, starting
at 64, doubling via `realloc` on overflow, per the dispatch's exact spec.
`bw_add_entry` now only fails on a closed window or genuine allocation
failure (out of memory) — capacity is no longer a distinct failure mode.
`bw_free` frees the entries array before the struct.

**Verified**: 8 threads × 250 entries = 2000 concurrent adds to a single
window (double the old cap) — 0 lost, 0 duplicated, clean compile
(`-Wall -Wextra`, zero warnings).

`dsf_ai_service/substrate/binding_window_c.py` (the ctypes wrapper)
updated to match: `MAX_ENTRIES_PER_WINDOW` constant removed (replaced with
`INITIAL_ENTRY_CAPACITY = 64`, documentation only, not a cap);
`CBindingWindowOverflow` renamed `CBindingWindowClosed` since "the window
is full" is no longer a real failure mode, only "closed" or "OOM" are.

**Not currently live**: confirmed (again) that `window_manager.py` does
not import or reference `binding_window_c`/`CBindingWindow` anywhere —
this C port was built and halted in an earlier dispatch tonight
(`GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1.md`, for unrelated
performance reasons) and was never wired into the substrate's actual
window-management path. This fix is real and correct, ready for whenever
that integration happens, but changes nothing about what's running in
production today.

### 2. Python `WindowManager` — nothing to remove

Audited the live `BindingWindow.add_entry` in `window_manager.py`: it is
already an unbounded Python list (`self.entries.append(...)`), no
`len(entries) >= cap` guard exists anywhere in it. The dispatch's
instruction here describes a guard that doesn't exist in the live path —
likely referring to the (also non-live) C port's own cap, already
addressed above.

### 3. Queue `maxsize=N` specifications — **all 4 reverted after direct
stress testing confirmed real runaway risk**

Initially removed all four (`_organism_queue`, `_tapestry_queue`,
`_diary_queue`, `s3_queue`), per the dispatch's literal instruction. Before
deploying anything, checked each queue's actual producer code: **all four
use `put_nowait()` wrapped in `except queue.Full: <drop and count>`** —
meaning the `maxsize` cap is not blocking backpressure, it's a
deliberate, tracked load-shedding valve. Removing it doesn't slow
producers down (nothing here ever did), it removes the *only* mechanism
that was preventing the queue from growing without limit when a producer
outpaces its consumer.

Given this session already found, hours earlier, that the organism
worker's consumer thread costs 800-2500ms/word under real contention —
well below the throughput a fast producer (or even ordinary reading
cadence) could sustain — this was not a theoretical concern. Ran a direct
stress test on each of the four: a single unbounded feeder thread, no
sleep, calling the real enqueue function as fast as Python allows,
watching queue size and process RSS every 3 seconds.

| Queue | maxsize removed | Result after ~18s of unbounded feeding |
|---|---|---|
| `_organism_queue` | was 2000 | 14M+ items queued, RSS 252MB → 1241MB, still climbing linearly |
| `_tapestry_queue` | was 2000 | 13.8M+ items queued, RSS 228MB → 1044MB, still climbing |
| `_diary_queue` | was 4000 | 14.6M+ items queued, RSS 763MB → 4436MB (worse per-item cost — each diary event carries a detail dict) |
| `s3_queue` | was 20 | 11.9M+ items in 8s testing pure producer rate (no consumer thread even started) — confirms the "rate-limited by caller convention" reasoning I initially used to justify this one doesn't actually protect the queue itself; any other/future/buggy caller bypassing that convention hits the same unbounded growth |

**All four reverted to their original `maxsize` values.** This is a clean,
direct, empirical confirmation of this dispatch's own named halt condition
("Runaway after cap removal — cap was catching real bug"), for all four
queues, not inferred or assumed for any of them. The reverts are
comment-only in the sense that matters: `git diff` on the surviving state
shows zero behavioral change to `Queue(maxsize=...)` constructor calls —
each queue's actual cap value is identical to before this dispatch started.

### 4. Composition/emission `GRANDURUN_TOPK` — investigated, kept as-is

The one count-based ceiling still sitting upstream of the already-uncapped
`_grandurun_select_vector` selector: `_grandurun_select_candidates`'s
`top_k=200` parameter, truncating the candidate pool before it ever
reaches the (already state-driven) selection stage. This looked like
exactly the pattern this dispatch targets. Before removing it, read the
comment on `GRANDURUN_TOPK`'s own definition — dated 2026-07-05,
`GL-CMD-ENABLE-COGNITION-EVE-20260705-211` — which documents a real,
prior, carefully-reasoned finding: **too many competing candidates
measurably breaks the emission commit step itself** ("200 competing
candidates makes the settle-on-one-winner commit step nearly
impossible"), not merely a performance cost. This matches this session's
own standing memory of sentence-completion already struggling to commit
under competing signal. A real correctness constraint on the emission
mechanism, not an arbitrary slot limit — reverted to the original
`top_k=200` default, unchanged behavior.

## Step 3: verify no runaway

Covered above for the four queues — the direct stress test *is* this
step for the changes that were attempted. `binding_window.c`'s 2000-entry
concurrent test (Step 2, item 1) covers the "1000 concurrent words to a
single window" ask directly. The "10 min reading memory watch" and
"induce quiet, emission terminates naturally" tests were not run against
a live deploy, since nothing that reached a deployable state has any
behavioral difference from what's already running to watch.

## Findings needing Eve routing

1. **All four queue caps are real, load-bearing safety valves, not
   arbitrary limits** — confirmed empirically, not just re-affirmed by
   assumption. If genuine unbounded throughput headroom is wanted here in
   the future, it needs a different mechanism than simply deleting the
   cap (e.g., a real backpressure/blocking `put()` that slows the
   *producer* down to match the consumer, rather than either dropping
   silently or growing without bound) — a substantive design change, not
   a one-line removal.
2. **`GRANDURUN_TOPK`'s cap is a documented correctness constraint**, not
   a slot limit — worth making that distinction clearer in the audit
   patterns for any future "remove limits" dispatch, since it matched
   the literal grep pattern this dispatch searched for despite not being
   in the category the dispatch actually wants removed.
3. **`JOB_MAX_ENTRIES`, `_MAX_ENTRIES_PER_WORD`, `MAX_SNAPSHOTS`/
   `EVENTS_MAX_BYTES`/`EVENTS_MAX_ROTATED`** — flagged in the audit table
   above but not investigated in the depth the four queues got, since they
   weren't in this dispatch's explicit STEP-2 target list. Worth a
   dedicated look if slot-limit removal continues as a theme.

## Recommendation

Ship the `binding_window.c` fix as committed (real, verified, safe,
currently inert). Do not pursue removing the four queue caps or
`GRANDURUN_TOPK` further without a genuine design change to how
backpressure/candidate-pooling works — the caps are catching real bugs,
confirmed directly, not just suspected.

## Scope compliance

`N_CELLS`, neuron count seed, coupling neighbor count, and numerical
stability clamps were never touched. No production deploy — nothing that
survived this dispatch changes live behavior; deploying would have been
safe but would verify nothing new.

---

### Changelog
- v1 (2026-07-07, c1): Audited all five named patterns. Removed the one
  real slot limit found (`binding_window.c`'s fixed entry array, currently
  inert/not wired live). Attempted, then reverted after direct stress
  testing, all four `queue.Queue(maxsize=N)` removals — confirmed real,
  unbounded runaway for all four, exactly matching this dispatch's own
  named halt condition. Attempted, then reverted after finding a
  documented prior correctness finding, the `GRANDURUN_TOPK` removal.
  Committed; not deployed (no behavioral change to verify in production).
