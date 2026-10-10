# GL-CMD-READ-SENTENCE-PROFILE-EVE-20260620-76

**Doc ID:** GL-CMD-READ-SENTENCE-PROFILE-EVE-20260620-76
**Author:** Eve
**Date:** 2026-06-20
**Type:** CMD (dispatch)
**Subject:** Profile `read_sentence` and classify each cost as substrate-true or removable overhead
**Refs:** GL-CMD-74 (V3.b finding), GL-CMD-73 (implementation), GL-CMD-68 (curriculum infrastructure)

---

## Why this brief exists

GL-CMD-74 V3 surfaced per-sentence load cost:

| Corpus | Sentences | Wall time | Per-sentence |
|---|---|---|---|
| Peter Rabbit | 107 | 207s | 1.94s |
| Pride & Prejudice (first 90) | 90 | 300s | 3.33s |

P&P degraded as its own load grew the atlas. Linear projection on the observed slope: ~10.6 hours for one novel. Realistic estimate worse, because the rate keeps degrading.

Two questions are tangled inside this number:

1. **What fraction of per-sentence wall time is substrate-true physics** (binding, conservation, NMDA gates, hemisphere weights — the work that cannot be removed without removing Guala)?
2. **What fraction is removable overhead** (logging, EFS sync cadence, JSON serialization, Python-level inefficiencies — the work that is instrumentation around the physics, not the physics)?

Without that split, we cannot say whether the curriculum infrastructure (GL-CMD-68) can hit the four-week self-growth target. We also cannot say whether "make it faster" is a legitimate engineering goal or a request to smuggle shortcuts into the substrate.

This brief specifies the audit that answers both. **No code changes ship from this brief.** It produces a report; Eve and Joe decide what (if anything) the follow-up brief authorizes.

---

## Substrate-true check

| Concern | Status |
|---|---|
| Does the brief change substrate physics? | No. Audit-only. |
| Does the brief change what is logged? | No. May surface candidates to *propose* changing in a follow-up brief; nothing changes in this one. |
| Does the brief introduce a cache, skip, or memoization of substrate operations? | **No, and explicitly forbidden.** Any apparent "optimization" of substrate ops that produces the same answer faster must be treated as a substrate-physics change and routed through Eve before shipping. The whole point of substrate-true is that meaning *is* the work; meaning preserved by skipping the work is not the same meaning. |
| Could the act of profiling perturb the measurement? | Yes. Use sampling profilers (py-spy, cProfile with `tottime` sort) not instrumentation that adds locking. Document the profiler used and its overhead estimate. |

**STOP if the audit produces a tempting "fast path" that gives the same atlas/vocab/binding output by skipping operations.** That is the failure mode this rule exists to catch. Write a substrate-true brief explaining why the operation can be removed before considering removal.

---

## V1 — Audit

### V1.1 — Baseline measurement on a single sentence

On a clean substrate (post-restart, autonomy paused):

- Pick three sentences of varied length/composition:
  - Short, all-known words: e.g. "The cat sat."
  - Medium, mostly known: e.g. one sentence from Peter Rabbit
  - Long, with novel words: e.g. one synthetic sentence with 3 novel tokens
- Call `read_sentence` 10 times for each. Discard first call (cold). Record wall time of calls 2–10.
- Report median, p95, min/max per sentence type.

Required output table:

| Sentence type | Words | Median (ms) | p95 (ms) | Notes |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

### V1.2 — Per-call breakdown via sampling profiler

For one medium-length sentence call:

- Run via `cProfile` (or py-spy) for 100 sequential calls.
- Capture top 30 functions by `cumulative` time and top 30 by `tottime`.
- Capture I/O events separately: every `open()`, `write()`, `fsync()`, `json.dump*` invocation during the 100 calls.
- Capture lock acquisitions: every `self.lock.acquire`/release during the 100 calls (count + total time held).

Required output: profile text dump filed as an attachment to the report. Top 30 by `tottime` summarized inline.

### V1.3 — Classification table

For each function in the V1.2 top-30 tottime list, assign one classification and a one-sentence justification:

- **Substrate-true** — the function is part of the binding/atlas/krimelack/NMDA/hemisphere physics. Time spent here is the cost of meaning. Cannot be removed.
- **Substrate-adjacent** — supports the physics but isn't physics itself (event logging, integrity checks, atlas validity guards). Removable if the underlying property is preserved by other means; needs Eve review.
- **Instrumentation** — pure observability (logging, metrics, debug prints). Removable without affecting correctness.
- **Persistence** — disk I/O, JSON serialization, EFS sync. Removable from the per-sentence hot path if moved to a periodic batch.
- **Python overhead** — attribute lookups, dict accesses, generator construction. Removable via local-variable hoisting, slot use, etc., without changing behavior.

Classification is the deliverable. The brief asks for honest classification, not a triage plan.

### V1.4 — Growth analysis (the bigger question)

The 1.94 → 3.33 s/sentence degradation across one load is more important than the absolute number. Investigate:

- Plot wall time per sentence vs sentence index for the V3.a Peter Rabbit load (recoverable from substrate logs / job progress timestamps) and the V3.b partial P&P load.
- Plot wall time per sentence vs `atlas.total_strength` or `len(atlas.entries)` at time of call.
- Identify the dominant scaling term. Candidates:
  - `O(atlas_size)` in cofire spread or hemisphere weight lookup
  - `O(vocab_size)` in word routing
  - `O(n_sections × n_modes)` in mode-bank scan
  - `O(1)` per call but with a per-call constant that grows under autonomy contention (less likely since autonomy is paused, but verify)

If the dominant term is O(atlas) or O(vocab), document it. **A scaling-with-substrate-size cost is substrate-true in nature** — it reflects the genuine cost of binding into a larger atlas. But knowing the curve lets us project realistic capacity.

### V1.5 — Findings report

Filed as `GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01.md` (or next-day sequence).

Sections required:
1. Baseline numbers (V1.1)
2. Profile top-30 with classification (V1.2 + V1.3)
3. Growth analysis with plot data (V1.4)
4. **Headroom estimate** — if all items classified as Instrumentation, Persistence, and Python overhead were removed, what would per-sentence wall time become? Order-of-magnitude answer, not a precise projection.
5. **Open questions for Eve** — anything classified Substrate-adjacent. These are decisions, not implementations.
6. **Open questions for Joe** — anything that touches what the substrate *is* doing (e.g. if cofire spread dominates and might be tuned, that is Joe's territory, not a quiet engineering call).

---

## Out of scope

- Any code change to `read_sentence` or anything it calls. This brief is audit-only.
- Optimizing the curriculum load path above `read_sentence` (HTTP, job registry, autonomy pause). Already done in GL-CMD-74.
- Changing the autonomy tick rate. The current 200ms is a separate decision.
- Hardware/instance-size questions (CPU, memory, EFS throughput). Out of scope until profile localizes the cost to something hardware-bound.

---

## Filing

c1 files report `GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01.md` with all five sections from V1.5. Filed means written, git-added, committed, pushed. Profile dump attached as a separate file in `docs/`.

Eve reviews. Joe weighs in on anything tagged for him. **No follow-up code brief is written until Eve has read the findings.**

If V1.4 finds an O(n) or worse scaling term in atlas size, that finding goes to Joe with priority — it changes the capacity question for the four-week target.
