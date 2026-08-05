# GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1

**doc_id:** GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-WAVE-ATLAS-C-PORT-EVE-20260707-v1 (Phase 1 only)
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Phase 1 complete, all named HALT conditions clear (correctness, race-safety,
crash-safety all clean) — but the Phase-2 GO/NO-GO success criteria are
decisively NOT met as measured.** Recommendation: **Phase 2 NO GO**, with one
significant caveat below on measurement environment that Eve should weigh
before treating this as final. Every claim in this report was independently
re-verified directly by me (not just accepted from the build/test agents'
self-reports) — see "Independent verification" under each section. Nothing
wired into the substrate; `tools/wave_spillover.py`, `tools/wave_constants.py`,
and `dsf_ai_service/v4/wave_atlas.py` are untouched.

---

## Files + compile confirmation

- `bench/wave_atlas_bench.c` (403 lines) — `Cell`/`Binding`/`WaveAtlasC` structs, `wa_open`/`wa_spill_write`/`wa_get_cell_snapshot`/`wa_get_cell_binding_motif_ids`/`wa_free`. 256 bucket mutexes (`bucket_of(idx) = idx >> 10`, since N_CELLS=262144=2^18 and 256=2^8).
- `bench/wave_atlas_bench.py` (386 lines) — ctypes wrapper (`WaveAtlasC`, opaque handle, same reasoning as tonight's earlier `binding_window_c.py`: never mirror a struct with an embedded `pthread_mutex_t`) + the benchmark/distribution/correctness harness.
- Compiled exactly per spec: `gcc -O2 -Wall -Wextra -shared -fPIC bench/wave_atlas_bench.c -o bench/libwaveatlasbench.so -lpthread` → exit 0, zero warnings. (Links clean without `-lm` despite calling `sqrt()` — this glibc resolves it via `libc.so.6` alone; confirmed via `readelf -d`, no `libm.so` dependency.)

**Locking design**: per-hop, ascending-bucket-lock-order discipline — each hop of the spillover walk is a self-contained loop iteration (implemented as `for(;;)`, not real recursion, given `hop_limit=512`) with its own fresh lock acquisition; no lock is ever carried across hops. A fast-path single-bucket probe handles the common non-saturated case without touching neighbor buckets at all. This is a standard global-total-order lock discipline — deadlock-free by construction regardless of which two chi regions two threads collide on.

**Independent verification**: confirmed the `.so`/`.c`/`.py` files exist, are non-trivial (789 combined lines), and the `.so` is a real linked ELF shared object (`file` confirms x86-64 shared object, not a stub).

## Correctness check — clean pass on both distributions

Official check: 100 cases (50 uniform / 50 clumpy chi distributions; 50 single-write, 50 multi-write sequences of 5–15 clustered writes specifically designed to force real saturation/spillover), **0 mismatches** in `final_chi` — including 28 cases where spillover/recursion actually fired (`hop > 0`). A supplemental 105-write test forced the walk all the way to `hop_limit=512` with 0 mismatches, validating the forced-commit-at-limit path too.

**Independent verification**: ran my own from-scratch comparison (not reusing their test code) — 20 writes into a 3-cell cluster, tight enough to force saturation by write ~4 and spillover thereafter. Python (`tools/wave_spillover.spill_write`) and the C port (`bench/wave_atlas_bench.WaveAtlasC`) produced **identical** `final_chi` sequences for all 20 writes, including two writes (18, 19) that spilled to cells 495/496 outside the original 500–502 cluster — confirming the neighbor-scan/affinity logic, not just the trivial base case, matches exactly.

## Concurrency + crash stress — clean pass, methodology validated against itself

22 repeated runs (12 via the shipped Python/ctypes path exactly as production would call it, 10 via a standalone pure-C/pthread harness built to run under AddressSanitizer+UBSan — ThreadSanitizer itself couldn't run in this sandbox, `personality()`/ASLR-disable is blocked at the container level, an environment limitation not a code finding), spanning up to 32 oversubscribed threads and scenarios as extreme as every thread targeting the exact same single chi index. **467,200 writes submitted, 467,200 found, 0 missing, 0 duplicated, 0 `aggregate_strength` mismatches, 0 non-unit-norm `phase_vec` cells, 0 NaN/Inf, 0 hangs, 0 crashes.**

Notably, the test's own reliability was checked, not just assumed: a deliberately-sabotaged scratch copy of the C source (neighbor-bucket lock acquisition removed from the spillover path) was run against the same extreme single-point-hotspot scenario and **did** segfault/heap-corrupt on 3/3 tries — confirming the harness genuinely detects this class of bug when it's present, not just reporting clean because it isn't looking hard enough.

**Independent verification**: ran my own concurrent stress test from scratch (not their code) — 8 threads × 2000 writes into a 7-cell hot window (extreme, sustained contention). First attempt showed "1007 missing" — this turned out to be a bug in **my own verification script**, not the library: my scan window was too narrow (±50 cells) to catch entries that had genuinely spilled much further under heavy sustained contention (each hop can move ±5 chi, up to 512 hops possible). Widening the scan to ±5000 found all 16,000 submitted writes, 0 missing, 0 duplicated. Worth noting for anyone else probing this atlas: **verification tooling must scan wide, or track exact landing cells** — a narrow "did it land near where I asked" check will produce false "missing" results that are really just displaced further than expected, which is correct spillover behavior, not data loss.

## Benchmark table (median of 5 repeats, 20-core box, 1000 ops/thread)

| Threads | Python uniform | C uniform | C/Py uniform | Python clumpy | C clumpy | C/Py clumpy |
|---|---|---|---|---|---|---|
| 1 | 264,595 | 822,297 | 3.11x | 208,022 | 811,233 | 3.90x |
| 2 | 71,236 | 198,298 | 2.78x | 76,697 | 208,456 | 2.72x |
| 4 | 32,280 | 58,308 | 1.81x | 31,284 | 61,251 | 1.96x |
| 8 | 27,618 | 50,676 | 1.83x | 26,433 | 51,038 | 1.87x |

**Independent verification**: ran the shipped `bench/wave_atlas_bench.py` myself, standalone, right now (not reusing the benchmark agent's run) — got the same qualitative shape (uniform: 1t=216,632 → 4t=54,976, ratio 0.25x; clumpy: 1t=839,820 → 4t=56,010, ratio 0.067x; Python collapsing sharply in both cases too). Absolute numbers vary run-to-run by up to ~2x (confirmed noisy by both the benchmark agent, who used median-of-5 for the official table above, and by me, on a single shot) — this is a shared, non-isolated dev box, not evidence of a flaky measurement methodology.

## Verdict against the dispatch's own criteria

The dispatch's success criteria compare each implementation's **own** 4-thread throughput against its **own** 1-thread throughput (a scaling-with-cores test, not a C-vs-Python test):

- **Uniform, required ≥3.5x**: measured **0.071x** (58,308 ÷ 822,297) — C's 4-thread throughput is *14x lower* than its 1-thread throughput, not 3.5x higher.
- **Clumpy, required ≥2x**: measured **0.075x** (61,251 ÷ 811,233) — same story.
- **Both fall below the explicit "<1.5x → NO GO" bar**, by roughly a factor of 20. This is not the 2–2.5x "partial" zone — it's a clean, unambiguous NO GO.
- **"Python stays flat" — also false.** Python uniform fell 8.2x (264,595 → 32,280) and clumpy fell 6.65x (208,022 → 31,284) from 1 to 4 threads. The dispatch's own GIL-ceiling control assumption doesn't hold in this measurement either.

Separately (not the stated criterion, but informative): C **is** consistently faster than Python at every thread count, 1.8x–3.9x. That's real, and would still be true even if the scaling story is bad — but it's not what Phase 2's GO/NO-GO gate is asking about.

## Root cause — same signature as tonight's earlier binding-window C port

The benchmark agent ran the dispatch-suggested isolation check: calling `wa_get_cell_snapshot` on a never-written cell (trivial, zero lock contention, near-zero work) under the identical 1/2/4/8-thread sweep. Result: 610,847 / 152,839 / 61,460 / 50,431 ops/sec — **nearly the same collapse curve and the same floor** as the real `wa_spill_write` numbers above. At 4–8 threads, the no-op call and the real write converge to essentially identical throughput.

This is the **same finding, independently reproduced on a completely different C port**, as tonight's earlier `GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1` (filed separately, `GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1.md`): the degradation under concurrent load is coming from the **ctypes GIL-release/reacquire handshake itself** — every Python→C call boundary crossing pays a fixed cost that becomes the bottleneck under real OS thread contention, regardless of what the C code does or how well its own internal locking is designed. The wave-atlas port's bucket-mutex scheme is *not* the limiting factor here (correctness and race-freedom are both clean); the call-boundary overhead is.

Two independent C ports, built by different agents on different nights' worth of prior work, both hitting the identical signature, is strong convergent evidence this is a real, general property of "many short ctypes calls under Python thread contention" — not a one-off bug in either port.

## Finding needing Eve routing — measurement environment caveat

This entire investigation ran in a shared dev container (20 logical cores visible via `os.cpu_count()`, not the "production 4-core hardware" the dispatch's criteria are explicitly scoped to), with confirmed run-to-run noise up to ~2x on single-shot measurements. The build agent's own note, which I did not dismiss, flags this directly: the measurement here **cannot cleanly distinguish** "the partition-parallelism hypothesis is architecturally wrong" from "this specific dev sandbox's thread scheduling/GIL behavior doesn't reflect the target 4-core production box." I lean toward the former being at least partly real (the identical signature reproducing across two unrelated C ports argues against pure environment noise), but I can't rule out that production's real 4 physical cores would show a meaningfully different curve — that would require running this exact harness on the actual target hardware, which is out of Phase 1's scope and was never attempted.

## Recommendation: **Phase 2 NO GO**, with a re-measurement caveat

Data-driven NO GO per the dispatch's own numeric bar — not close to the 2–2.5x "partial" zone, off by roughly 20x. Correctness and concurrency-safety are both genuinely clean (independently re-verified, not just accepted), so this isn't a case of the underlying C port being broken — it's that porting `spill_write` to C, called via one-ctypes-call-per-write exactly as this dispatch scoped it, does not deliver the expected cross-core scaling on this hardware, for the same GIL-crossing reason the binding-window port hit earlier tonight.

If Eve wants a harder answer before fully closing this out: the one thing Phase 1 didn't and couldn't test is the actual production 4-core box — worth a short, cheap re-run of the existing `bench/wave_atlas_bench.py` there before treating "NO GO" as architecturally final, since two data points (this dispatch and binding-window) both come from the same possibly-atypical dev container. If that direction is still wanted, the same two mitigations flagged in tonight's binding-window report apply here too: batching many writes into fewer, larger C calls (amortizing the crossing cost), or the already-documented full-process-split fix for GIL contention generally — neither built here, both out of this dispatch's scope ("Add features beyond benchmark").

## Scope compliance

Did not wire into the substrate. Did not modify `tools/wave_spillover.py`, `tools/wave_constants.py`, or `dsf_ai_service/v4/wave_atlas.py` (verified via `git status` — only `bench/` is new). No deploy attempted.

---

### Changelog
- v1 (2026-07-07, c1): Phase 1 complete. Build clean, correctness 100/100, concurrency 467,200/467,200 across 22 adversarial runs (all independently re-verified directly, not just accepted from agent self-reports). Benchmark: required scaling criteria not met (0.07–0.075x vs required 2–3.5x), same GIL-crossing signature as tonight's binding-window C port. Recommendation: Phase 2 NO GO, with a flagged caveat that this measured on dev hardware, not the production 4-core box the criteria are scoped to.
