# GL-CMD-WAVE-ATLAS-C-PORT-EVE-20260707-v1

**doc_id:** GL-CMD-WAVE-ATLAS-C-PORT-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after binding window C port hit contention at scale)
**Supersedes as target:** `GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1`. The binding window port revealed architectural serialization on the single open window; this dispatch pivots to the wave atlas layer, which has a genuinely different concurrency shape.

## Verdict

Binding window C port hit contention at 4 threads because all entries fund ONE window — architecturally serialized. I extrapolated 1-core benchmark data into a multi-core prediction that didn't hold. That was a real mistake.

The wave atlas has a different shape. 262,144 cells addressed by `chi_value % N_CELLS`. Different chi values → different cells → different memory locations. Real sensory input distributes across chi space, so most concurrent writes don't touch the same cell. This is naturally partition-parallel.

That's the hypothesis. Hypothesis alone is what got me last time. Before doing the full port this dispatch requires measurement — a small proof-of-concept showing the parallelism gain is real on production hardware before committing to the full port.

**Two-phase dispatch. Phase 1 is measurement-only. Phase 2 only proceeds if Phase 1 confirms the hypothesis.**

## Phase 1 — Proof-of-concept measurement

### What's built

Minimal C port of `spill_write` and `_commit_cell` from `tools/wave_spillover.py`. Standalone C library + Python ctypes wrapper + benchmark script. Not integrated into the substrate.

**`bench/wave_atlas_bench.c`** — C implementation:
- `Cell` struct: `float aggregate_strength`, `int32_t is_saturated`, `int32_t binding_count`, `double phase_vec[32]` (16 complex as 32 doubles), `Binding *bindings` (dynamic array)
- `Binding` struct: `int64_t motif_id`, `int64_t chi`, `float strength`
- `WaveAtlasC`: array of 262,144 `Cell*` pointers, lazily allocated on first write
- Partitioned mutex: 256 buckets by high bits of chi, each with its own `pthread_mutex_t`. Multiple threads writing to different buckets don't contend.
- `wa_spill_write(atlas, chi_target, phase_vec, motif_id, chi, strength)` — matches Python `spill_write` semantics: commit at chi_target if unsaturated, otherwise scan ±chi_band by phase affinity (vdot on 16-complex), recurse if best neighbor also saturated
- `wa_commit_cell` — appends binding via realloc, updates aggregate_strength, updates running phase mean, marks saturated

Bucket count 256 is a starting parameter. c1 may measure other values (64, 512, 1024) if 256 shows contention.

**`bench/wave_atlas_bench.py`** — benchmark:
- Baseline: pure-Python `spill_write` from existing `wave_spillover.py`, N threads doing 1000 writes each
- C port: same workload via ctypes
- Measures ops/sec at 1, 2, 4, 8 threads
- Two chi distributions:
  - **Uniform** — chi values random across full N_CELLS space (best case for partitioning)
  - **Clumpy** — chi values biased toward a hot region (realistic for reading a single passage)

### Success criteria for Phase 1

At 4 threads on production 4-core hardware:
- **Uniform distribution:** C throughput ≥ 3.5x single-thread throughput (theoretical max 4x)
- **Clumpy distribution:** C throughput ≥ 2x single-thread throughput
- **Python throughput** stays flat vs 1 thread on both distributions — confirms GIL ceiling

If both hold: Phase 2 is worth doing.

If C only gets ~1.5x at 4 threads on uniform: architectural contention worse than hypothesis, full port not worth doing. Route back, stop.

If Python stays flat AND C shows partial gain (2–2.5x on uniform, less on clumpy): partial win, Eve decides on Phase 2 direction.

### What's NOT in Phase 1

- No integration with substrate
- No wire-in to atlas write callsites
- No deploy
- No harness runs (isolated primitive benchmark)
- No decay/prune (not needed to measure write path parallelism)
- No spillover subdivision callback
- No persistence

Bench-only. If it fails, a day's work has taught us something real.

### Halt conditions for Phase 1

1. **Correctness diff** — C `spill_write` and Python `spill_write` produce different final chi positions for identical inputs. Real bug.
2. **Race conditions** — concurrent writes to same chi produce missing bindings, corrupted phase_vec, or wrong aggregate_strength. Partitioned-mutex design insufficient; need a different primitive.
3. **Segfault** — any thread crashes. Real bug.

Any halt: route with the finding. No workaround.

## Phase 2 — Full port (dispatched separately, only if Phase 1 succeeds)

Not detailed here. Sketch of what Phase 2 would look like:
- Port `WaveAtlas` class to use the C library
- Keep Python API surface unchanged
- Wire into existing atlas write callsites in engine
- Standard six-step harness protocol
- Migration flag: `WAVE_ATLAS_C_ENABLED=0/1` for rollback
- Integration with existing Python decay/prune code — decide whether decay migrates to C or stays Python

Phase 2 dispatch is written after Phase 1 report lands.

## Scope guardrails for Phase 1

Do NOT:
- Wire anything into the substrate
- Modify existing `wave_atlas.py` or `wave_spillover.py`
- Add features beyond the benchmark
- Skip the correctness check (final chi must match Python for identical inputs)
- Skip the clumpy chi distribution test — partition-parallelism depends on real chi distributions, not just uniform

If Phase 1 raises design questions the benchmark can't answer alone, halt and route.

## Report

`GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1.md` with:
- Files: `bench/wave_atlas_bench.c`, `bench/wave_atlas_bench.py`
- Compile confirmation
- Correctness check result (same final chi for identical inputs, both distributions)
- Benchmark table: Python vs C at 1/2/4/8 threads, uniform + clumpy chi distributions, ops/sec each
- Verdict: does C hit ≥3.5x at 4 threads on uniform? ≥2x on clumpy?
- Any findings needing Eve routing
- Recommendation: Phase 2 GO / NO GO / PARTIAL, with the specific data supporting it

Do not ask Joe questions in the report. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Two-phase dispatch. Phase 1 is bench-only measurement of the wave atlas parallelism hypothesis. Phase 2 (full port) only if Phase 1 confirms real multi-core scaling. Learning from binding window C port dispatch: measure hypothesis with real workload before committing to full port.
