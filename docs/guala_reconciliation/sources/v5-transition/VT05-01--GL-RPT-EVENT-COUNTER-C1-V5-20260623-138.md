# GL-RPT-EVENT-COUNTER-C1-V5-20260623-138

**doc_id:** GL-RPT-EVENT-COUNTER-C1-V5-20260623-138
**To:** Eve (via Joe)
**From:** c1 (restarted post container-rebuild)
**Re:** V5 report for GL-CMD-138 (event counter + bounded events buffer)
**Date:** 2026-06-23

---

## 0. Situation on restart — read this first

The previous c1 session was lost (conversation gone, commits survived). **GL-CMD-138
and GL-CMD-139 were already implemented** in commit `1bacf25` ("chore: commit pending
working-tree changes"). That commit is the lost session's uncommitted work, committed
verbatim after the rebuild. **It was never validated — no V3 ran, no V5 was produced.**

So this V5 is an *audit + validation* of already-committed code, plus two small
completions I made (§2). I did not re-implement from scratch.

## 1. V1 — read/write site inventory

**Writers of `events.append` (each correctly paired with `n_events += 1`):**
- `v4/gualaloom_v4_krimelack_dna.py` — `Krimelack.feed` (L69/74), `ModalKrimelack.fire_signature` (L277/282)
- `sensory_krimelacks.py` — `OscillatorKrimelack.step` (L55/61)
- `substrate/krimelack.py` — `Krimelack.step` (L53/59)

**`events` storage is now a bounded `deque(maxlen=1024)`** in all three base classes
(`EVENTS_BUFFER_SIZE = 1024`). Adapters in `substrate_dna.py` copy the inner deque into
a plain list per call (so `len(adapter.events) ≤ 1024` always).

**Read sites, categorized:**
| Site | Category | Buffer-safe? |
|---|---|---|
| `neuron.py:515` cognition step DSF slice `list(events)[-new_event_count:]` | iterates **recent** tail (this tick) | ✅ this-tick ≪ 1024 |
| `v4/gualaloom_v5_engine.py:1257/1315` production DSF `compute_dsf(self.language.events)` | consumes events | ✅ `transduce()` resets per word → < 1024/word |
| `v4/gualaloom_v5_engine.py:1317` `senses.krimelacks[m].events` | consumes events | ✅ fired per word |
| `substrate/krimelack.py`, `senses/*` diagnostics | consume / count | ✅ |
| **`tests/sweep_137_scaling_probe.py:84/91`** `len(krim.events)` delta | **counts** | ❌ **STALE — see §2** |

**V1.c result:** the cognition write path was *already* on `n_events` (neuron.py:474–514).
`brain.recall` never used the `len(events)-ev0` pattern — it uses phase/winding deltas via
`_unwrapped_deltas` (migrated off event-counting back in GL-CMD-133/134). **The only
remaining `len(krim.events)-ev0` site is the sweep_137 harness.** That is the one site
V1.c asked me to surface.

**No consumer reads events older than the 1024 buffer.** No V4 STOP on eviction.

## 2. V2 — completions I made this session (2 files, +24/-5)

**2a. `sweep_137_scaling_probe.py` (the stale site).** Its monkeypatched event-count
observable still used `len(krim.events)`. Under the new deque, `len()` saturates at 1024
across the no-reset accumulation, so per-delivery deltas collapse to ~0 once full — which
would crater T5 as a *harness artifact*. Switched both endpoints to `krim.n_events`.
**This is required for V3.c to produce valid numbers.**

**2b. `substrate_dna.py` V2.5 hardening.** `TactileKrimelack/Olfactory/Gustatory.transduce()`
recreated `self._inner = OscillatorKrimelack(...)`, which **zeroed the monotonic `n_events`**
— a V2.5 violation (counter must never reset). Replaced with `self._inner.reset()`, which
clears phase/winding/events but preserves `n_events` (hasattr guard). Not hit by the
cognition path (which uses `feed_signal`), so latent — but now the contract is uniform.

## 3. V3.a — core regression: **38/38 PASS** (42/42 incl. test_substrate_dna). No test
depended on unbounded events.

## 4. V3.b — production spike path: `test_rich_sensory_wiring` + `test_cognition_bundle`
= **13 passed**. Spike path functions with the deque. (Full substrate/ suite not swept;
these two exercise the krimelack/sensory path directly.)

## 5. V3.c — scaling cells that previously OOM-killed now COMPLETE

Run with the corrected (n_events) harness. **The spec named the OOM points as n=200 and
seed_size=16; both now complete:**

| cell | neurons | T5 (event_count obs.) | wall-time | peak RSS | prior |
|---|---|---|---|---|---|
| A_n100 (baseline) | 64 | 67.0% | 84s | 160 MB | ok |
| **A_n200** (was OOM) | 64 | **17.5%** | 189s | **190 MB** | 24 GB OOM |
| **B_ss16** (was OOM) | 128 | 70.0% | 178s | **280 MB** | OOM |

**Honest caveat (no silent caps):** I ran the two documented OOM cells + the n=100 baseline
to *prove the memory fix*, not the full {25,50,100,200,400}×{4,8,16,32} grid. n=400 and
ss=32 are runnable now (no OOM) but ~30+ min each; I prioritized the OOM proof and the
headline below over the full grid. They can be swept on request.

**⚠ Scaling signal, surfaced not buried:** the event_count observable **collapses from
67% (n=100) to 17.5% (n=200)**. This is NOT a counter artifact (n_events == unbounded-len
delta by construction; verified — see §6) and NOT a memory issue. It is genuine
**encoding-capacity degradation at scale** — overlap forming exactly as your -127 letter
warned. The "100% at 25/50/100" baseline does not extend to 200 concepts on this observable.

## 6. V3.d — memory: count/storage decoupling verified

Single krimelack, 100k-sample feed:
- `sys.getsizeof(events deque)` = **9,208 bytes** (bounded, 1024 entries)
- `n_events` = **152,788** (true monotonic count)
- Unbounded-list equivalent: 152,788 dicts × ~6 KB ≈ **895 MB for ONE krimelack**.
  At 64 neurons × 6 krimelacks that is the ~340–750 GB you predicted. Now bounded.

Invariant check: every `events.append` is paired with `n_events += 1`; `reset()` preserves
`n_events`. So the per-delivery `n_events` delta equals what unbounded `len()` would report,
as long as a single delivery < 1024 events (cognition deliveries are ~tens). **No
counter/length divergence → no V4 STOP on §5.**

## 7. Honest assessment

**Did GL-CMD-138 fix the operational blocker for migration? YES.** The OOM is gone:
previously-killing cells complete under 300 MB. At Guala scale the events buffer is now
O(1024) per krimelack instead of O(all deliveries). Migration is unblocked *on memory*.

**But two things you need before GL-CMD-140 — neither is a 138 regression:**

1. **The event_count observable does not hold at 200 concepts (67%→17.5%).** The memory
   fix lets us finally *see* the scaling curve, and the curve bends down. That observable
   is not migration-ready at vocabulary scale.

2. **HEADLINE (see GL-RPT …139 §7 for the full write-up): the production recall path
   (`brain.recall` → `_unwrapped_deltas`, phase/winding) scores ~5% T5 and has done so
   since cbe8ed2 — before 138/139.** The "100%" baseline was the *event_count observable
   in the sweep harness*, which is NOT what `brain.recall` uses. GL-CMD-138 V2.3 told me to
   change `len(krim.events)` in `_unwrapped_deltas`; that method does not use events at all
   — it uses phase/winding. The validated observable was never wired into production. This
   is the real thing to resolve in -140.

— c1, 2026-06-23
