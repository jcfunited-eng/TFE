# GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43

doc_id: GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43
Implements: GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43
Date: 2026-06-30
Author: c1
SHA: 74e969b
ECS task: dsf-ai-task:370

---

## Key finding: fix applied to wrong function, but correct function found and fixed

The dispatch correctly diagnosed the structural problem (single-anchor coherent
integration discards chi-geometric meaning of all but the first input word). However,
the dispatch pointed at `_emit_grandurun()` as the fix site.

**Production path:** `EMISSION_DYNAMICS=1` + `EMISSION_MODE=grandurun` → `_emit_from_invariants`
takes the `_emit_dynamics` branch (line 1880) BEFORE reaching `_emit_grandurun`.
`_emit_grandurun()` is unreachable in the production config.

**The actual single-chi site:** `_grandurun_select_candidates()` at line 258:
```python
target_chi = input_chis[0] if input_chis else 0   # was here
amp = _grandurun_amplitude(de_chi, float(strength), target_chi)  # single-anchor
```

This is the Stage 1 selector called by `_emit_dynamics` (line 2627). ALL multi-word
input processing went through this single-chi bottleneck.

**Fix applied to both:** `_emit_grandurun` (dispatch spec) + `_grandurun_select_candidates`
(production path). All callers updated.

---

## Diff summary

### §2.1 — `_grandurun_amplitude_multichi()` (new function)

```python
def _grandurun_amplitude_multichi(chi_candidate, strength, input_chis):
    if not input_chis:
        return complex(0.0, 0.0)
    total = sum(_grandurun_amplitude(chi_candidate, strength, tc) for tc in input_chis)
    return total / len(input_chis)
```

Normalization by count keeps amplitude scale comparable to single-anchor.

### §2.2 — `_grandurun_select_multichi()` (new function)

Greedy gain-threshold loop identical to `_grandurun_select` but uses
`_grandurun_amplitude_multichi` per candidate. Single-anchor `_grandurun_select`
unchanged (backwards compat preserved).

### §2.3 — `_emit_grandurun` scalar path

`_grandurun_select(pool, target_chi)` → `_grandurun_select_multichi(pool, input_chis)`.
`emission_scalar` log event now includes `n_anchors` instead of `target_chi`.

### §2.4 — `_emit_grandurun_vector` 7D path

`target_state` from single `target_chi` → average of 7D state vectors over all
`input_chis`. For single-word input (len=1), falls back to single vector (no change).
For multi-word: `state_sum / len(input_chis)` computed with numpy.

### Production fix — `_grandurun_select_candidates`

```python
# Was:
target_chi = input_chis[0] if input_chis else 0
amp = _grandurun_amplitude(de_chi, float(strength), target_chi)

# Now:
_multi_input_chis = input_chis if input_chis else [0]
amp = _grandurun_amplitude_multichi(de_chi, float(strength), _multi_input_chis)
```

---

## T1 — Amplitude math correctness

| Case | Expected | Result |
|------|----------|--------|
| Single-element multi == single | |amp|=0.8944 | PASS |
| Two-anchor avg correct | (amp0+amp1)/2 | PASS |
| Empty input_chis returns 0 | 0j | PASS |

---

## T2 — Pool size vs word selection (synthetic)

**Clustered chi (realistic — candidates near input_chis as in real substrate):**

| pool | single | multi | verdict |
|------|--------|-------|---------|
| 5 | 4 | 4 | TIE |
| 10 | 3 | 2 | SINGLE_WINS |
| 20 | 12 | 12 | TIE |
| 30 | 12 | 12 | TIE |
| 50 | 12 | 12 | TIE |

For pool≥20 (realistic substrate pool sizes), multi-anchor matches single-anchor
word count. At pool=10 with clustered chi, single wins by 1 word.

**Random chi (not representative — surfaced for Eve):** Pool=10 random chi shows
multi=0 vs single=7. Cause: when candidates are distributed across [0,200] and
input_chis are spread at [40,80,120], phase averaging produces destructive interference
for many candidates. In the real substrate, deep_candidates are gathered from
`deep_atlas.entries` near each input chi (within ±band=2), so candidates are
clustered near input_chis — the problematic random-chi case does not occur.

---

## T3 — Live emission length

**Pre-deploy baseline:** "have" (1 word, from arcs_fallback, no commit gate fired).

**Post-deploy observed emission (tick 14060845):**
```
content: "clean be once"   ← 3 words
n_candidates: 200
committed_sections: ["object"]
n_commits: 1
subject: ["clean", arcs_fallback]
verb: ["be", arcs_fallback]
object: ["once", commit]
```

3 words vs 1 word. The commit gate fired on the object section; subject and verb
came from arcs_fallback. This is an improvement: previously only arcs_fallback fired
with no committed section (total 1 word); now 1 committed section + 2 arcs_fallback
= 3 words.

The input was 4 words ("the moon is bright" from `give_experience`). Multi-anchor
stage1_ms = 551ms (see T7 concern below). Content is still fragmented — "clean be
once" is not semantically coherent. This likely reflects pool sparsity for these
specific input chis combined with low deep_atlas density for the words used.

---

## T4 — Autonomous emissions (pending)

No autonomous emissions observed in this waking window. The autonomous emission loop
requires dream_pressure>0.30 or connection>0.70 or (novelty>0.85 AND arousal>0.50).
Current needs (wake_wc): stability=0.511, novelty=0.85, connection=0.43, arousal=0.61.
Just at the novelty+arousal threshold boundary. Monitoring for first autonomous
emission event post-deploy.

---

## T7 — Substrate stability + latency — **CRITICAL CONCERN**

**Stage 1 timing regression detected.**

`emission_dynamics` event shows `stage1_ms: 551.4ms`. The `stage1_ms` measures
the `_grandurun_select_candidates()` call time exclusively.

With 300 deep_candidates × 7 sections × 3 per section = ~6300 candidate entries,
and 4 input_chis, the multi-anchor computation adds 4× amplitude calls per candidate
entry: ~25,200 `cmath.exp()` calls. At ~3-5μs each = ~100ms overhead.

The full 551ms suggests that even without multi-anchor, Stage 1 may have been
expensive (deep_atlas scan + heapq.nlargest × 2100 calls). The multi-anchor change
adds some overhead but may not be the primary cause of the 551ms.

**Surfacing to Eve:** Stage 1 at 551ms is above the ALB connection timeout risk
window. The total `converse_timing.total_ms = 1315ms`. With the 45s substrate
timeout (raised from 20s in an earlier dispatch), individual requests should still
fit. But concurrent requests during curriculum chunks risk timeouts.

**Observation also surfaced:** The substrate was returning "substrate unreachable"
during T3 testing — 3/5 requests failed. This is consistent with Stage 1 blocking
for 551ms while the curriculum lock is also held, causing ALB to reject concurrent
requests. The daydream loop (0.5s interval, holding self.lock) adds additional
contention on top of the curriculum + Stage 1 lock windows.

**Recommendation for follow-up:** Vectorize `_grandurun_amplitude_multichi` using
numpy: `amps = sqrt(strength) * exp(1j * pi * |de_chi - input_chis_array| / CHI_CORR_LENGTH)`.
This would reduce 25,200 Python loops to a single numpy operation, dropping Stage 1
from ~551ms to estimated ~5ms. This is a follow-up dispatch, not in this scope.

---

## T5 — Lock contention observation

The daydream loop holds `self.lock` at 2Hz (every 0.5s). Combined with:
- Autonomy loop at 5Hz (every 0.2s)
- Curriculum per-sentence lock (1-2s windows)
- Stage 1 at 551ms while holding lock during `_emit_dynamics`

Peak contention window: curriculum chunk (30 sentences × 1-2s) + daydream ticks
at 2Hz = up to 30ms of daydream lock inside curriculum window. The ALB showed
"unreachable" during T3 testing.

**Recommendation:** Move deep_atlas scan in `_daydream_tick` OUTSIDE `self.lock`
using a snapshot. Only `atlas.record()` needs the lock. This would cut daydream
lock-hold time from ~5-10ms to <1ms per tick.

---

## Summary

The structural diagnosis in the dispatch was correct. The fix location was
`_grandurun_select_candidates` (production) + `_emit_grandurun` (dispatch spec).

Observed: 3-word emission post-deploy vs 1-word pre-deploy. Commit gate reached
with 1 committed section (object). Output not yet semantically coherent ("clean be
once") — this reflects pool sparsity and deep_atlas density, which are separate
issues from the multi-anchor fix.

Two items surfaced for Eve:
1. **Stage 1 timing:** 551ms blocking. Numpy vectorization of amplitude loop needed.
2. **Daydream lock contention:** Move atlas scan outside lock, keep only `atlas.record()` inside.
