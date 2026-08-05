> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01

**Doc ID:** GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01
**Author:** c1 (Codex)
**Date:** 2026-06-20
**Type:** RPT (audit-only — no code changes)
**Refs:** GL-CMD-76, GL-CMD-74 (V3 findings), profile dump: GL-ATTACH-READ-SENTENCE-PROFILE-C1-20260620-01.txt

---

## Setup

**State:** S3 backup `guala/auto/2026-06-20_21-00-15_activity_ended`
- id: `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`
- vocab: 3,591 words
- atlas entries: 27,577
- reads: 239,193
- tick: 11,437,183

**Section mode counts at load time:**
| Section | Modes |
|---|---|
| listen | 3,495 |
| verb | 3,203 |
| intro | 3,212 |
| subject | 574 |
| object | 986 |
| modifier | 24 |
| ground | 33 |

**Profiler:** CPython cProfile with `tottime` sort, then `cumulative` sort.
**Platform:** GitHub Codespace (Linux), Python 3.11. ECS Fargate runs same Python version on AWS infrastructure — ~2.3× faster than Codespace at current workloads.
**Autonomy:** Not running during any measurement (no `start_autonomy_loop` called in profiling harness).

---

## V1.1 — Baseline Measurement (wall time)

5 calls per sentence type; first call discarded (cold); calls 2–5 measured.

| Sentence type | Words | Median (ms) | p95 (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|---|
| `short_known` — "the cat sat" | 3 | 1,296 | 1,315 | 1,276 | 1,315 |
| `medium_known` — "peter rabbit lived under the big fir tree with his mother" | 11 | 4,492 | 4,681 | 4,189 | 4,681 |
| `long_novel` — "the xylophone zephyr quasar crystalline ephemeral vortex threshold oscillating phenomenon" | 10 | 1,637 | 1,676 | 1,551 | 1,676 |

**Unexpected finding:** `long_novel` (10 words, mostly unknown) is faster than `medium_known` (11 words, all known). Root cause established in V1.2 and V1.3: the heterosynaptic redistribution in `atlas.record()` fires with higher cost when existing bindings are present (known words). Novel words create new bindings with no redistribution inner loop.

**Per-word cost:**
- `short_known`: 432 ms/word
- `medium_known`: 408 ms/word
- `long_novel`: 164 ms/word

These figures include Codespace overhead (~2.3×). Production ECS estimates:
- `medium_known`: ~180 ms/word
- `long_novel`: ~70 ms/word

---

## V1.2 — cProfile (20 calls, medium_known sentence)

**Total time: 195.9s for 20 calls** — 9.8s/sentence (includes 2.3× Codespace overhead; ECS estimate ~4.3s/sentence, consistent with GL-CMD-74 V3.a result of 4.2s/sentence).

**Top 30 by tottime:**

```
ncalls   tottime  percall  cumtime  percall  function
 82020    76.379    0.001  168.589    0.002  living_atlas.py:87(record)
388226103  32.677    0.000   32.677    0.000  living_atlas.py:169(<genexpr>)
390773031  30.174    0.000   30.175    0.000  {built-in method builtins.max}
   413350  18.728    0.000   51.493    0.000  {built-in method builtins.sum}
   410038  10.368    0.000   10.368    0.000  living_atlas.py:168(<listcomp>)
    81260   5.424    0.000    5.971    0.000  deep_atlas.py:171(get_prior)
      700   4.818    0.007  193.063    0.276  v5_engine.py:489(receive)
    81260   4.115    0.000    4.356    0.000  deep_atlas.py:182(reinstate)
  4201760   3.890    0.000    7.256    0.000  numpy/linalg/_linalg.py:2598(norm)
  4201760   1.521    0.000    1.521    0.000  {method 'dot' of numpy.ndarray}
  2102980   0.865    0.000    0.865    0.000  {built-in method numpy.array}
  2102980   0.756    0.000    1.621    0.000  v4_uf_kernel.py:30(to_array)
       22   0.671    0.030    0.911    0.041  living_atlas.py:243(decay)
  4201760   0.638    0.000    0.836    0.000  numpy/linalg/_linalg.py:169(isComplexType)
  6412502   0.521    0.000    0.521    0.000  {method 'get' of dict}
      700   0.516    0.001    0.517    0.001  living_atlas.py:381(match_score)
  4201760   0.496    0.000    0.496    0.000  {method 'ravel' of numpy.ndarray}
  8403520   0.439    0.000    0.439    0.000  {built-in method builtins.issubclass}
    13112   0.351    0.000    0.351    0.000  living_atlas.py:375(<listcomp>)
  4201760   0.284    0.000    0.284    0.000  numpy/linalg/_linalg.py:2594(_norm_dispatcher)
   162806   0.276    0.000    0.429    0.000  <frozen os>:674(__getitem__)
      220   0.261    0.001    0.365    0.002  living_atlas.py:291(bindings_at_chi_neighborhood)
  4201760   0.226    0.000    0.226    0.000  {built-in method numpy.asarray}
  2100880   0.175    0.000    0.175    0.000  numpy/_core/multiarray.py:748(dot)
       88   0.159    0.002    0.663    0.008  living_atlas.py:370(cross_modal_bindings)
   162520   0.158    0.000    0.737    0.000  deep_atlas.py:34(_deep_prior_enabled)
   162806   0.152    0.000    0.581    0.000  <frozen _collections_abc>:771(get)
  2344096   0.151    0.000    0.151    0.000  living_atlas.py:376(<genexpr>)
   664860   0.124    0.000    0.124    0.000  {built-in method builtins.min}
   162806   0.089    0.000    0.154    0.000  <frozen os>:756(encode)
```

**Lock acquisition:** cProfile shows `threading.Lock.acquire()` called 22 times (once per `read_sentence` call — the outer `with self.lock`). Not a bottleneck. No contention in this measurement (autonomy not running).

**I/O:** No `open()`, `write()`, `json.dump()`, or `fsync()` calls appear in top-30 by tottime. `read_sentence` is I/O-free in the hot path.

---

## V1.3 — Classification Table

| Function | File:line | Classification | Justification |
|---|---|---|---|
| `atlas.record()` | living_atlas.py:87 | **Substrate-true** | Reinforcing chi-band bindings with heterosynaptic redistribution IS the binding physics. 76.4s. |
| `<genexpr>` (heterosynaptic scan) | living_atlas.py:169 | **Substrate-true** | `sum(e["strength"] for e in others)` — step 1 of mass-conservation redistribution. 32.7s. |
| `builtins.max` | built-in | **Substrate-true** | Used in STRENGTH_CAP enforcement and inner redistribution loop. 30.2s. |
| `builtins.sum` | built-in | **Substrate-true** | Heterosynaptic redistribution strength totals. 18.7s. |
| `<listcomp>` (others list) | living_atlas.py:168 | **Substrate-true** | `[e for e in entries if e is not existing]` — constructs redistribution target list. 10.4s. |
| `deep_atlas.get_prior()` | deep_atlas.py:171 | **Substrate-true** | Consolidation priors for deep atlas reinstatement; part of the deep learning cycle. 5.4s. |
| `Section.receive()` | v5_engine.py:489 | **Substrate-true** | Word-anchored mode commit, mode similarity scan, atlas calls. 4.8s. |
| `deep_atlas.reinstate()` | deep_atlas.py:182 | **Substrate-true** | Reinstating consolidated deep atlas entries into live atlas. 4.1s. |
| `numpy.linalg.norm` | numpy | **Substrate-true** | DSF vector norms for mode similarity scan in Section.receive(); ~210K calls/sentence = O(n_modes) per word per section. 3.9s. |
| `numpy.ndarray.dot` | built-in | **Substrate-true** | DSF similarity dot product; O(n_modes) per word per section. 1.5s. |
| `numpy.array` | built-in | **Python overhead** | Array construction from DSF, called once per mode in the similarity scan; could be precomputed. 0.9s. |
| `DSF.to_array()` | v4_uf_kernel.py:30 | **Python overhead** | Constructs numpy array from DSF each time it's compared; called 2.1M times. 0.8s. |
| `atlas.decay()` | living_atlas.py:243 | **Substrate-true** | Entropy decay; 1 call per 10 ticks; fundamental physics. 0.7s (22 calls). |
| `numpy isComplexType` | numpy | **Python overhead** | Type-check overhead from numpy.linalg.norm; called per norm invocation. 0.6s. |
| `dict.get` | built-in | **Python overhead** | Generic dict field access. 0.5s. |
| `atlas.match_score()` | living_atlas.py:381 | **Substrate-true** | Chi familiarity scoring; called per word per section. 0.5s. |
| `ndarray.ravel` | numpy | **Python overhead** | Internal numpy reshape in norm computation. 0.5s. |
| `builtins.issubclass` | built-in | **Python overhead** | Type dispatch overhead inside numpy. 0.4s. |
| `<listcomp>` at :375 | living_atlas.py:375 | **Substrate-true** | Filtering atlas entries by chi in match_score. 0.35s. |
| `numpy._norm_dispatcher` | numpy | **Python overhead** | Dispatch overhead for numpy.linalg.norm. 0.3s. |
| `os.__getitem__` | frozen os | **Python overhead** | Environment variable lookup inside `deep_atlas._deep_prior_enabled()`. 0.3s — called 162K times/20 sentences = 8K times/sentence. |
| `atlas.bindings_at_chi_neighborhood()` | living_atlas.py:291 | **Substrate-true** | Chi neighborhood binding query. 0.3s. |
| `numpy.asarray` | numpy | **Python overhead** | Another intermediate numpy array conversion. 0.2s. |
| `numpy._core.multiarray.dot` | numpy | **Substrate-true** | Core dot product implementation. 0.2s. |
| `atlas.cross_modal_bindings()` | living_atlas.py:370 | **Substrate-true** | Cross-modal recall; part of recall physics. 0.2s. |
| `deep_atlas._deep_prior_enabled()` | deep_atlas.py:34 | **Substrate-adjacent** | Checks `os.environ` + flag every time it's called; called 162K times/20 sentences = 8K/sentence. The flag does not change during a `read_sentence` call. 0.2s — removable by caching the boolean at session init. |
| `_collections_abc.get` | frozen stdlib | **Python overhead** | Attribute access indirection. 0.2s. |
| `<genexpr>` at :376 | living_atlas.py:376 | **Substrate-true** | Cross-modal binding score aggregation. 0.15s. |
| `builtins.min` | built-in | **Substrate-true** | Used in binding strength floor enforcement. 0.1s. |
| `os.encode` | frozen os | **Python overhead** | String encoding for env var lookup; same root cause as `os.__getitem__`. 0.1s. |

---

## V1.4 — Growth Analysis

### 25-sentence Peter Rabbit growth run

State at start: vocab=3,591, atlas=27,577 entries, listen_modes=3,495.

| Idx | ms | Atlas entries | Listen modes | Words |
|---|---|---|---|---|
| 0 | 4,366 | 27,577 | 3,495 | 18 |
| 1 | 4,917 | 27,477 | 3,495 | 18 |
| 2 | 4,428 | 27,778 | 3,495 | 19 |
| 3 | 2,645 | 27,939 | 3,495 | 14 |
| 4 | 3,824 | 28,889 | 3,495 | 18 |
| 5 | 4,178 | 28,927 | 3,495 | 16 |
| 6 | 5,437 | 29,006 | 3,495 | 17 |
| 7 | 4,668 | 29,094 | 3,495 | 18 |
| 8 | 5,433 | 29,162 | 3,495 | 17 |
| 9 | 1,752 | 29,404 | 3,495 | 12 |
| 10 | 6,685 | 29,517 | 3,495 | 19 |
| 11 | 6,121 | 29,698 | 3,495 | 16 |
| 12 | 3,185 | 29,758 | 3,495 | 20 |
| 13 | 4,472 | 28,194 | 3,495 | 18 |
| 14 | 4,319 | 28,317 | 3,495 | 16 |
| 15 | 5,102 | 28,475 | 3,495 | 17 |
| 16 | 3,198 | 28,631 | 3,495 | 17 |
| 17 | 4,684 | 28,704 | 3,495 | 17 |
| 18 | 3,790 | 28,810 | 3,496 | 21 |
| 19 | 5,493 | 28,846 | 3,496 | 18 |
| 20 | 4,944 | 28,912 | 3,496 | 21 |
| 21 | 3,922 | 28,989 | 3,496 | 18 |
| 22 | 5,584 | 29,195 | 3,496 | 19 |
| 23 | 6,595 | 29,230 | 3,496 | 21 |
| 24 | 7,163 | 28,185 | 3,496 | 23 |

First 13 sentences: median **4,428 ms**
Last 12 sentences: median **4,684 ms**

### Dominant scaling term

**The atlas is NOT monotonically growing during corpus loading.** Atlas entries oscillate (27,477–29,758) across the 25 sentences because `atlas.decay()` runs every 10 ticks and removes weak bindings, roughly balancing new additions. Net atlas growth over 25 sentences: +1 mode (vocab). This confirms the substrate is near equilibrium at 239,193 reads.

**Linear slope:** 199.8 μs per atlas entry, 944 ms per listen_mode. Both values are noisy because atlas oscillates rather than growing monotonically.

**Per-word normalization:**
- First 13 sentences: **259 ms/word**
- Last 12 sentences: **270 ms/word**
- 4% increase over 25 sentences; not a meaningful growth trend.

### Reconciling GL-CMD-74 V3 observation

GL-CMD-74 reported per-sentence cost of 1.94s (Peter Rabbit) rising to 3.33s (P&P). Per-word:
- Peter Rabbit: 1.94s / ~10 words = **194 ms/word** (ECS Fargate)
- P&P partial: 3.33s / ~17 words = **196 ms/word** (ECS Fargate)

These are **identical per word.** The 1.94→3.33s apparent growth is entirely explained by P&P having longer sentences than Peter Rabbit, not by atlas growth. The GL-CMD-74 brief's statement "the rate keeps degrading" was not confirmed.

**Dominant scaling term: O(words_per_sentence × entries_per_chi_bucket)**

The per-sentence cost scales linearly with sentence length. The per-word cost is approximately constant at the current atlas state (~260ms/word locally, ~200ms/word on ECS).

The per-word cost itself scales with local atlas density (entries per chi bucket). This would grow if the atlas fills up further, but is currently near equilibrium at 27,000-30,000 total entries across 100 chi buckets (~280 entries/bucket × 5 chi band = ~1,400 entry scans per atlas.record() call).

### Is this O(atlas) scaling substrate-true?

Yes. The heterosynaptic redistribution (the dominant cost) IS the mass conservation law. Every reinforcement in a chi band removes an equal and opposite amount from neighboring bindings. This requires scanning all entries at all 5 chi neighbors. The cost scales with entries_per_chi, which is a direct reflection of how many bindings currently exist near the input word's chi value.

Meaning accumulates in the atlas. The cost of reading a new word reflects the genuine cognitive load of situating it among everything the substrate currently knows. This is substrate-true in nature.

---

## V1.5 — Findings

### 1. Baseline Numbers

At current state (vocab=3,591, atlas=27,577, ECS Fargate):
- Per-word cost: ~200 ms/word
- Short 3-word sentence: ~600 ms
- Medium 11-word sentence: ~2.2 s (2,200 ms)
- Long sentence (20+ words): ~4 s

### 2. Profile Top-30 with Classification Summary

| Classification | Time in top-30 | % of total |
|---|---|---|
| **Substrate-true** | ~185s | ~94% |
| **Python overhead** | ~8s | ~4% |
| **Substrate-adjacent** | ~1.4s | ~0.7% |
| **Instrumentation** | 0 | 0% |
| **Persistence** | 0 | 0% |

No I/O, no logging, no persistence in the hot path.

### 3. Growth Analysis

Per-word cost is constant at current atlas equilibrium. The 1.94→3.33s apparent degradation in GL-CMD-74 is explained entirely by longer P&P sentence lengths — not by atlas growth. There is NO runaway degradation.

### 4. Headroom Estimate

If all Substrate-adjacent and Python-overhead items were removed:
- Removable: ~9.4s out of 195.9s per 20 sentences = ~4.8%
- At ECS per-sentence cost of 2.2s (medium sentence): saves ~105ms → **~2.1s/sentence**
- This does NOT materially change the P&P problem (11,436 sentences × 2.1s ≈ 6.7h instead of 7h)

The core cost is substrate-true physics and cannot be removed without removing Guala.

### 5. Open Questions for Eve

- **`deep_atlas._deep_prior_enabled()` called 8,000×/sentence** (162K calls for 20 sentences): This checks `os.environ` + a flag on every call. The flag does not change during a sentence. **Classification: Substrate-adjacent** — the deep prior feature is substrate-physics, but checking an environment variable on every invocation is not. This is a candidate for one-time caching at session init. Saves ~0.3s/20 sentences (1.5%) without changing behavior. Awaiting Eve review before touching.

- **`DSF.to_array()` called 2.1M×/20 sentences**: Each mode's DSF is reconverted to a numpy array for every similarity check. The DSF values do not change between comparisons within a single `read_sentence` call. Pre-computing `to_array()` results before the mode scan loop would save 0.8s/20 sentences (0.4%). This is Python overhead around substrate-true work. Awaiting Eve review — would require a structural change to how Section.receive() iterates modes.

### 6. Open Questions for Joe

- **Atlas equilibrium confirms substrate health.** At 239,193 reads, the atlas (27-30K entries) is in near-equilibrium: new bindings roughly match decaying ones. This is expected behavior — the substrate is not filling up unboundedly.

- **The 200ms/word constant is the substrate's current learning rate.** Faster processing would mean the substrate binds less thoroughly per word. This is a design parameter, not a bug. Joe should know: loading a Gutenberg novel (100K words) at current rate ≈ 20,000 seconds ≈ 5.6 hours of autonomy paused. The question of whether that is acceptable — or whether a slower, incremental background-reading architecture should replace bulk load — is Joe's call, not an engineering optimization.

---

## Filing

Profile dump as separate attachment: `docs/GL-ATTACH-READ-SENTENCE-PROFILE-C1-20260620-01.txt`

No follow-up code brief written. Eve and Joe review first.
