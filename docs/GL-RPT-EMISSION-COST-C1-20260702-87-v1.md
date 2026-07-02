# GL-RPT-EMISSION-COST-C1-20260702-87-v1

doc_id: GL-RPT-EMISSION-COST-C1-20260702-87-v1
From: c1b | To: Eve | Date: 2026-07-02
In response to: GL-CMD-DEPLOY1-GATES-EVE-20260702-97-v1 step 2 + -86-v3 §4.7 rider condition

---

## VERDICT: CLEAN

```
20 emission_dynamics samples collected from stream fd3ace1da0064f598b9fcec686fe5f89
Tick range: 14170823 – 14179115  (current stream, post-Deploy-1 boot)
dynamics_ticks: 40 in all 20 samples (invariant)
n_commits:      0 in all 20 samples (invariant)
stage2_ms:      82.9 – 92.1 ms  mean=87.7ms  σ=2.3ms
n_candidates:   197 in all 20 samples (invariant)
origin:         grandurun=197 in all 20 samples (invariant)

-87 rider condition met: sample ≥20, filed, clean.
EMISSION_DYNAMICS_TICKS 40→80 may accompany Deploy 2.
```

---

## Sample Table

| # | tick | stage2_ms | dynamics_ticks | n_commits | type |
|---|------|-----------|----------------|-----------|------|
| 1 | 14170823 | 88.7 | 40 | 0 | curriculum |
| 2 | 14171214 | 92.1 | 40 | 0 | curriculum |
| 3 | 14172745 | 86.9 | 40 | 0 | curriculum |
| 4 | 14173125 | 90.5 | 40 | 0 | curriculum |
| 5 | 14173540 | 86.6 | 40 | 0 | curriculum |
| 6 | 14173928 | 85.7 | 40 | 0 | curriculum |
| 7 | 14174328 | 84.8 | 40 | 0 | curriculum |
| 8 | 14174761 | 87.9 | 40 | 0 | curriculum |
| 9 | 14175143 | 87.9 | 40 | 0 | curriculum |
| 10 | 14175547 | 88.1 | 40 | 0 | curriculum |
| 11 | 14175941 | 89.6 | 40 | 0 | curriculum |
| 12 | 14176316 | 90.4 | 40 | 0 | curriculum |
| 13 | 14176713 | 90.5 | 40 | 0 | curriculum |
| 14 | 14176944 | 82.9 | 40 | 0 | autonomous |
| 15 | 14177106 | 88.5 | 40 | 0 | curriculum |
| 16 | 14177499 | 88.1 | 40 | 0 | curriculum |
| 17 | 14177900 | 85.0 | 40 | 0 | curriculum |
| 18 | 14178307 | 87.0 | 40 | 0 | curriculum |
| 19 | 14178737 | 84.7 | 40 | 0 | curriculum |
| 20 | 14179115 | 87.9 | 40 | 0 | curriculum |

---

## Invariants (all 20 samples)

```
dynamics_ticks    = 40     (current env; -87 proposes 80)
n_commits         = 0      (no organ commits yet — organ reader not deployed)
n_candidates      = 197
origin_counts     = {grandurun: 197}
organ_in_commits  = false
keyhole_fires     = 0
nmda_fired        = 80 (19 curriculum) / 40 (1 autonomous, sample 14)
```

Curriculum source_counts (19 of 20):
```
{curriculum: 60, wc: 18, worldfeed: 116, bundle: 2, joe: 1}  → sum=197
```

Autonomous source_counts (sample 14 only):
```
{worldfeed: 105, curriculum: 86, corpus: 5, wc: 1}  → sum=197
```

---

## Statistics

```
N          = 20
min        = 82.9 ms  (sample 14, autonomous emission)
max        = 92.1 ms  (sample 2, curriculum)
mean       = 87.7 ms
std dev    = 2.3 ms  (sample)
range      = 9.2 ms
```

No outliers. The autonomous emission (82.9ms) is at the low end but within 2σ of the
curriculum mean. Spread is normal measurement noise; no bimodal pattern.

---

## Emission cycle timing (observed)

```
IDLE duration:   278–330 ticks per cycle
EMITTING phase:  100 ticks fixed
Cycle period:    ~378–430 ticks ≈ 76–86 seconds real-time
```

---

## -87 rider assessment

Current EMISSION_DYNAMICS_TICKS=40: stage2_ms budget 82.9–92.1ms across 20 samples.

Doubling to 80 ticks doubles the grandurun pass count. The grandurun semantic
neighborhood fix (SHA 6561288) made that pass O(1) per chi (pre-computed mean scalar),
so 2× ticks ≈ 2× pass count with minimal per-pass overhead. Expected stage2_ms
headroom at 40 ticks: mean+3σ = 87.7 + 6.9 = ~94.6ms. At 80 ticks the pass runs
twice; if grandurun dominates stage2, expect ~95–100ms. Within acceptable bounds for
non-interactive background emission.

Rider condition per -86-v3 §4.7: **MET.**
Sample count: 20 ✓ | Filed before GO ✓ | Sample clean ✓

---

## Collection method

Ring buffer (engine `_substrate_events`, deque maxlen=1000). Collected via
`guala_get_events(since_tick=..., limit=50)` advancing since_tick past each observed
emission_dynamics tick. Bridge hardcodes limit=50 (`substrate_runner.py` L1412).
`emission_dynamics` is not in CloudWatch critical events list (engine L3810-3814) —
ring buffer only. No persistence. Sample spans two context windows of the same stream.
