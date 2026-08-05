# GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1

**doc_id:** GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT. Routed per the dispatch's own explicit instruction — two
independent named halt conditions confirmed, not one.** The C library
was built exactly as specified, compiles clean, and is functionally
correct (round-trips every field exactly) and concurrency-safe (zero
lost/duplicated/corrupted writes under real thread contention). But
the dispatch's own **halt condition #2 (single-threaded regression)**
and **halt condition #4 (1024-entry overflow)** are both confirmed
real, empirically. Per the dispatch's own measurement mini-task
("before the six-step protocol, run a focused before/after benchmark
... if C uniform < 1.5x at 4 threads, NO GO" — the equivalent
threshold here), this stops *before* `window_manager.py` is touched
and before the acceptance harness or deploy protocol run at all.
Nothing in production changed. `window_manager.py` was never modified.

---

## What was built (matches the dispatch's own BUILD spec)

1. **`dsf_ai_service/substrate/binding_window.c`** — `BindingWindow`/`WindowEntry` structs exactly as specified (`window_id[40]`, `opened_tick`/`closed_tick` int64, wall-clock doubles, `is_closed`/`entry_count` int32, fixed `entries[MAX_ENTRIES_PER_WINDOW]`, `pthread_mutex_t lock`). `bw_open`, `bw_add_entry`, `bw_close`, `bw_entry_count`, `bw_free` ported from the reference `docs/binding_window.c`. One addition beyond the reference (authorized by the dispatch's own "use them or refine"): **`bw_get_entry`** — named in the dispatch's own function list but missing from the reference file. Added with explicit bounds checking (`idx < 0 || idx >= entry_count`) since a missing check here is a real out-of-bounds memory read, not a catchable Python exception.
   Compiled clean: `gcc -Wall -Wextra -O2 -shared -fPIC -o libbindingwindow.so binding_window.c -lpthread` → exit 0, zero warnings. `sizeof(WindowEntry) = 64` bytes confirmed (fixed-size scalars only, safe to mirror in ctypes).

2. **`dsf_ai_service/substrate/binding_window_c.py`** — thin ctypes wrapper, `CBindingWindow` class matching the existing `BindingWindow` API surface (`add_entry`, `close`, `get_entries`). Design choices:
   - `BindingWindow*` is a fully opaque `c_void_p`, never mirrored as a `ctypes.Structure` — it embeds a `pthread_mutex_t`, whose layout is platform/libc-specific; mirroring it would risk silent memory corruption on a struct-layout mismatch, the single riskiest failure mode available here.
   - `WindowEntry` **is** mirrored (fixed scalars only, the safe case) — needed for `bw_get_entry`'s out-parameter.
   - Section-name ↔ id mapping implemented as a plain Python dict, assigning each distinct section name the next integer id on first sight (lock-guarded check-and-insert), matching the dispatch's "kept in Python as a small dict" instruction. Not a fixed enum — section names are open-ended at runtime (`audio_low`/`audio_high` per cochlear band, `modal_touch` etc.), so a fixed C-side enum would be fragile against a future channel name. `modality_id` **is** the dispatch's fixed six-value enum (sight/sound/word/touch/smell/taste), matching the C file's own comment.
   - `free()` + a `__del__` safety net, since `bw_open`'s `calloc` allocates the full ~65KB struct (including the inline 1024-entry array) up front — the C heap has no garbage collector, an un-freed handle leaks for good.

`window_manager.py` was **not modified** — the halt happened before that step, matching the dispatch's own sequencing ("before the six-step protocol, run a focused before/after benchmark").

## Correctness check — clean pass

Standalone test (not the `binding_windows_acceptance.yaml` harness — halted before reaching that step): every field round-trips exactly across all six modalities, a dynamically-added section name, and a 40-character `source_tag` (correctly truncated to 31 chars + null, matching `SOURCE_TAG_MAX`). `add_entry` after `close()` correctly raises. Overflow correctly raised at exactly the 1024th entry, and `get_entries()` correctly returns all 1024 on a full window. Section-name table correctly round-trips 12 distinct names across 3 repetitions each (36 entries, all correct).

## Concurrency stress test — clean pass

8 threads × 128 adds = 1024 concurrent writes to the *same* window, repeated 3×. Zero lost writes, zero duplicated indices, zero corrupted fields (`chi`/`tick`/`source_tag` all correctly attributed per-thread) in every run. This specific class of test caught three real bugs elsewhere tonight (wave-atlas-decay v1/v2, sensory-queue starvation) — it did not catch one here. The C mutex + fixed array is genuinely safe under contention.

## Halt condition #2 (single-threaded regression) — CONFIRMED

The dispatch's own measured claim: "Python binding window ops cap at 130k ops/sec... C via ctypes at 239k ops/sec single-threaded (10x faster)... expected combined effect ~40x throughput." Measured directly here, using the exact benchmark shape from `docs/test_binding_window_contention.py` (adapted only to point at the real build path and the real shipped `CBindingWindow` wrapper, not a raw inline ctypes call):

| Threads | Python ops/sec | C ops/sec | C/Python |
|---|---|---|---|
| 1 | 335,626 | 294,638 | **0.88x** |
| 2 | 156,082 | 129,754 | 0.83x |
| 4 | 405,675 | 57,004 | **0.14x** |
| 8 | 400,655 | 48,199 | **0.12x** |

C is slower than Python at **every** thread count tested, including single-threaded — halt condition #2, triggered exactly as the dispatch itself anticipated as a possible outcome ("ctypes overhead can bite for very fast operations"). The degradation gets *worse*, not better, with more threads — the inverse of the dispatch's central hypothesis that GIL release lets this scale across production's 4 cores.

**Root cause, isolated empirically (not inferred):** ran a second test calling a **no-op, lock-free** C function (`bw_entry_count`, pure read, no mutex) under the same thread-count sweep — it degrades on the *same* curve (218k → 272k → 143k → 38k ops/sec, 1→2→4→8 threads) with **zero** actual contention on shared state. This rules out the `pthread_mutex` as the cause. A third test compared true single-threaded sequential calls (no `threading.Thread` object at all: 1.37M ops/sec) against the same call pattern wrapped in one thread via the benchmark's own harness — confirming per-call cost is genuinely tiny in isolation. The bottleneck is the **GIL release/reacquire handshake itself**, under real contention from multiple threads simultaneously crossing that boundary — a well-documented CPython pathology ("GIL thrashing") for frequent, short C calls under multi-thread pressure: the synchronization overhead of the handshake swamps the actual work once several threads contend for it, regardless of what the C code does or doesn't lock. Repeated 3× at 8 threads for consistency: 52,061 / 53,452 / 53,531 ops/sec — stable, not noise.

This directly corroborates [[gualaloom-item7-neff-wall-cause]]-adjacent prior work this session: the documented fix for GIL contention under real concurrent load is a full process split, not a per-call C port of a single fine-grained operation — releasing the GIL for a call this short doesn't amortize the crossing cost, it multiplies the number of crossings under contention.

## Halt condition #4 (1024-entry overflow) — CONFIRMED

Direct, reproducible local test (carried over from earlier investigation, re-confirmed): a single realistic sustained-reading sequence (384 words, repeated common vocabulary) produced 1235 entries in one still-open window — exceeding `MAX_ENTRIES_PER_WINDOW=1024` by 211 entries before the window ever closed. This is not an edge case; ordinary reading activity crosses the fixed-array boundary. `bw_add_entry` correctly returns `-1` on overflow (no crash, no corruption) — but a production deploy would silently start dropping entries mid-window during real usage.

## Why this halts here rather than proceeding

Both conditions are named, explicit halt clauses in the dispatch's own text, and the dispatch is explicit that the ctypes-overhead check happens *before* the six-step deploy protocol for exactly this reason — to catch a not-net-positive port before it touches `window_manager.py`, the acceptance harness, or production. Two independent, empirically confirmed reasons are present, either alone sufficient. Proceeding to wire this into `window_manager.py` would ship code that makes concurrent word-processing *slower* under real load — the opposite of every dispatch that led here tonight.

## Recommendation

Not a rejection of the underlying goal (relieving GIL contention on hot paths) — three of the four halt conditions this dispatch worried about didn't materialize (correctness, thread-safety, and the array-overflow crash-safety are all clean). But this specific approach — a fine-grained, single-entry-per-call C port of a tiny critical section — is empirically the wrong shape for the fix. If GIL contention on binding-window adds is still worth solving, two directions worth Eve's consideration, neither built here (out of this dispatch's scope, "add features"):
- **Batching**: one C call per *word* (all its entries in one crossing) instead of one call per entry, amortizing the GIL-crossing cost over more work per call — untested here, a real redesign, not a tonight-sized change.
- **The already-documented fix**: full process split (per `GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2.md`'s own prior finding), which sidesteps GIL crossing entirely rather than trying to make individual crossings cheaper.

Either direction is new design work, not a refinement of tonight's port. Recommend Eve decide whether either is worth a future dispatch, or whether binding-window throughput is deprioritized relative to the sensory-organism-queue starvation problem still open from earlier tonight.

## Rollback / state

Code committed to `guala-live` (so the work, the reproducer, and the root-cause data aren't lost) but **not deployed** — no task-def touched, no `window_manager.py` change, production untouched, still running the last known-healthy state.

---

### Changelog
- v1 (2026-07-07, c1): Phase-1-only build (C lib + ctypes wrapper). Correctness + concurrency-safety clean. Halt conditions #2 and #4 both confirmed via direct measurement; root cause of #2 isolated to GIL-crossing overhead under contention, not the mutex. Not deployed, not wired to `window_manager.py`.
