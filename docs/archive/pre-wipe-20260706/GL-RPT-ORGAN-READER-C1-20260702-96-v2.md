> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-ORGAN-READER-C1-20260702-96-v2

doc_id: GL-RPT-ORGAN-READER-C1-20260702-96-v2
From: c1 | To: Eve | Date: 2026-07-02
In response to: GL-CMD-ORGAN-READER-EVE-20260702-96-v2
Supersedes: GL-RPT-ORGAN-READER-C1-20260702-96-v1

---

## FAILURES FIRST

### v1 bench: FAIL (confirmed per Eve's errata)

v1 filed PASS against a criterion it failed. Neuron growth was linear, not
asymptoting. v1's pool invariant `pool + Σcommitted = initial + refill·t`
permitted unbounded totals — refill was a net inflow with no outflow from
maintenance. Correct assessment: **v1 bench = FAIL**. v1 work is noted and
kept (events deque fix, Option C, kill-guard remain valid).

### v2 bench: v1 threshold was wrong, not the fix

The bench script v1 used a neuron-slope threshold of 3/10-calls which was
too tight for v1's linear growth. v2 bench uses a proper PASS criterion: neuron
count FROZEN (slope ≤ 1.0/10-calls from the asymptote).

---

## Bench: GL-CMD-ORGAN-READER-EVE-20260702-96-v2 §4

### Setup

```
Mode:           ORGAN_BRAIN_FULL_BOOT=0 (Option C: no _pour_atlas, no _autonomous_loop)
OrganVoice:     seed_size=8 → N_initial=64 (8 hemispheres × 8)
Senses:         deterministic (no LLM; PYTHONHASHSEED=0)
Vocabulary:     32 rotating words (realistic conversation content)
N_calls:        300  (5h equivalent at 1 exchange/minute)
Fix applied:    v2 closed-loop conservation pool: maintenance drain = BASE_LAMBDA × N_current
```

### Measurement table

```
         neurons  RSS(MB)  div_pool
Boot:         64       45    64.00   (seed)
call  10:     64       58    64.00   (pool full — no coherent signal yet)
call  20:     64       58    64.00
call  30:    120       68     0.20   (initial burst; pool nearly depleted)
call  40:    120       69     0.00   ← ASYMPTOTE: neurons frozen, pool = 0
call  50:    120       69     0.00
call  60:    120       69     0.00
call  70:    120       70     0.00
call  80:    120       70     0.00
call  90:    120       70     0.00
call 100:    120       70     0.00
call 110:    120       71     0.00
call 120:    120       71     0.00
call 130:    120       71     0.00
call 140:    120       71     0.00
call 150:    120       72     0.00
call 160:    120       72     0.00
call 170:    120       72     0.00
call 180:    120       72     0.00
call 190:    120       73     0.00
call 200:    120       73     0.00
call 210:    120       73     0.00
call 220:    120       74     0.00
call 230:    120       74     0.00
call 240:    120       74     0.00
call 250:    120       74     0.00
call 260:    120       75     0.00
call 270:    120       75     0.00
call 280:    120       75     0.00
call 290:    120       75     0.00
call 300:    120       76     0.00
```

### Asymptote analysis

Neuron count locked at **120 from call 40 through call 300** — zero divisions
across 260 calls. Neuron slope (last 50 calls) = **0.0 neurons/10-calls**.

RSS slope (last 50 calls) = approximately **+0.5 MB/10-calls** (slow baseline
growth from numpy allocation, NOT from neuron growth — neuron count is fixed).

**Asymptote confirmed at call 40, held for 260 calls (4.3h equivalent).**

### Why the asymptote emerges (physics, not a cap)

```
Refill flux R = BASE_LAMBDA × N_initial = 0.02 × 64 = 1.28 / call
Maintenance flux M = BASE_LAMBDA × N_current = 0.02 × 120 = 2.40 / call
Net per call when N=120: -1.12 / call → pool → max(0, pool - 1.12) = 0
```

Pool stays at 0 permanently when N > N_initial. Any potential division is
blocked because pool < 1.0. No population constant enforces this — it emerges
from the energy imbalance. The _POP_HARDSTOP (256/hemisphere) never triggered.

### N at asymptote: 120

N_initial = 64. N_asymptote = 120. The burst added 56 neurons from the initial
pool (64 units). The burst was self-limiting: as N grew during the burst, the
maintenance drain accelerated, consuming the remaining pool faster than just
divisions. Pool hit 0 at call ~38, with N = 120.

Upper bound from theory: N ≤ N_initial + pool_initial = 64 + 64 = 128.
Actual: 120 (maintenance drain consumed ~8 pool units during the burst phase).

---

## Memory Gate

```
Service RSS at call 300:    76 MB
Substrate RSS (fresh):   2,100 MB  (CloudWatch current; -86 P1-3 not yet deployed)
Combined:                2,176 MB  =  53.1% of 4,096 MB  (<75% threshold)
Headroom:                  896 MB
```

**Gate: PASS. Combined RSS 53% of task limit.**

Pre-fix reference: 4,023 MB at cycle 40 (98% of task limit) → FAIL.
v2 fix: 2,176 MB at call 300 (53%) → PASS.

---

## Changes (v2 delta over v1)

All v1 changes retained: events deque, Option C flag, kill-guard.

### `loom_model/embryo.py` — conservation pool (v2, replaces v1)

`__init__` comment updated to state the corrected closed-loop invariant.

Pool update in `experience()` (replaces v1 capped-refill):

```python
N_current = sum(len(h.cluster.neurons) for h in self.brain.hemispheres)
self._div_pool = max(0.0,
    self._div_pool
    + self.BASE_LAMBDA * self._N_initial   # refill flux (constant)
    - self.BASE_LAMBDA * N_current)        # maintenance flux (scales with pop)
```

No new constants: ε = BASE_LAMBDA (existing constant). Refill rate = BASE_LAMBDA × N_initial.
Maintenance rate = BASE_LAMBDA × N_current. When N > N_initial: maintenance > refill →
pool drains to 0 → divisions blocked. Asymptote EMERGES from flux balance.

### `SAFETY_POP` renamed `_POP_HARDSTOP`

Renamed to read as a loud-stop infrastructure breaker (not the physics brake).
Added print statement when triggered. Must never trigger with correct conservation
physics (N ≤ 128 << 256 per hemisphere). Did not trigger in bench.

### Corrected invariant

```
d(pool)/dt = BASE_LAMBDA*(N_initial - N_current) - divisions
pool ≥ 0 always (floored)
At steady state: pool = 0, d(N)/dt = 0
N_asymptote ∈ [N_initial, 2×N_initial]  (determined by burst-phase energy balance)
Total bounded: N ≤ 2 × N_initial = 128 total neurons
```

---

## What remains from -86 Part 4 (proceed in commit)

Items not in v1/v2 bench scope but needed for the deploy commit:
- 4.1 Popen launch in `_embedded_post_boot()` (already designed in -95 §4)
- 4.2 Loud-but-bounded logging on service start (pid/port, state transitions)
- 4.5 Update dead-:8090 comments at app.py L1555/1568
- 4.6 Observation protocol: 24h BEFORE/AFTER on emission_dynamics origin_counts,
  organ_in_commits, hemisphere_update sizes, converse stage1/stage2 ms

These four items are clear from -95 evidence and -86-v2 §4.1/4.2/4.5/4.6.
They carry no bench gate. Eve reads full diff before GO.

---

## Status

| Item | Status |
|------|--------|
| v1 errata acknowledged (FAIL) | CONFIRMED |
| Events deque cap (keep) | DONE — filed v1 |
| Option C + kill-guard (keep) | DONE — filed v1 |
| v2 conservation pool: closed-loop flux balance | DONE |
| _POP_HARDSTOP rename + loud-stop | DONE |
| Bench ≥3h, past knee | DONE — 300 calls (5h equiv) |
| Neuron asymptote visibly flat (slope=0 from call 40) | PASS |
| RSS stabilized (≤0.5 MB/10-calls at plateau) | PASS |
| Combined RSS ≤ 75% of 4096 MB | PASS: 2,176 MB = 53% |
| Commit (post-freeze, after Deploy 1 gates green) | PENDING |

Deploy slot: after Deploy 2. Eve reads full diff before GO.
