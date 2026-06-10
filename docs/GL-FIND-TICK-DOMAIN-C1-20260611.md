# GL-FIND-TICK-DOMAIN-C1-20260611
## Tick Domain Mismatch — Section vs Engine Clocks

**Author:** c1 | **Date:** 2026-06-11 | **Trigger:** wC root-cause hypothesis
**Status:** CONFIRMED. Two clocks, one domain assumed everywhere.

---

## The Bug

Atlas entries are written by two different code paths using two different tick counters:

| Writer | Tick Source | Scale (prod) | Code Location |
|---|---|---|---|
| `Section.receive()` | `section.tick` | ~1-10 (per-section counter) | engine.py:246, 310-311 |
| Engine (modal, sight, presence) | `engine.tick` | ~3,270,000 | engine.py:1822, 509, 551 |

All consumers assume entries share a single tick domain:
- `atlas.decay(engine.tick)` computes `dt = engine.tick - entry.last_tick`
- Fix 1 tick window compares `entry.last_tick` against engine tick range
- Deep atlas survival history compares entry ticks across types

## Reproduction (engine tick = 3,000,000)

```
=== BEFORE DECAY ===
  chi=12  SECTION  listen  last_tick=7         str=0.2398
  chi=12  SECTION  subject last_tick=4         str=0.2398
  chi=12  ENGINE   modal_sight last_tick=3000007 str=0.2398

=== AFTER DECAY (engine tick 3000009) ===
  chi=12  ENGINE   listen  str=0.0016   ← dt=3000002, instant death
  chi=12  ENGINE   subject str=0.0016   ← dt=3000005, instant death
  chi=12  ENGINE   modal_sight str=0.2398 ← dt=2, preserved

After prune: 10 entries survive (all engine-written modal)
```

Section-written entries get `dt ≈ 3,000,000` ticks of phantom decay on the FIRST heartbeat. `exp(-0.0001 * 3000000) = exp(-300) = 0`. Every word Guala learns from conversation dies instantly.

## Downstream Damage

1. **ALL conversational learning destroyed** — every word read via `read_word()` → `Section.receive()` → `atlas.record()` stamps section tick ~1-10. First `atlas.decay(engine_tick)` kills it.

2. **Response binding Fix 1 broken** — tick window `[tick_before_read, tick_after_read]` is in engine domain (~3M). Section-written entries have `last_tick=9`. Never matches. This is why `response_bound = 0` on task:78.

3. **Metadecay calibration invalid** — SLOW_DIV=12 was measured against section ticks in the harness (small dt), not engine ticks (massive dt). The harness used LivingAtlas directly with small tick values, accidentally masking this bug.

4. **Deep atlas promotion starved** — entries die before reaching dream. The 2 survival promotions in prod are from engine-written entries (modal/presence), not conversational learning.

## This Has Been True Since LivingAtlas Was Introduced

The Section class has always maintained its own tick counter (`self.tick += 1` in `receive()`). The LivingAtlas was introduced in v6 with `last_tick` tracking. The mismatch existed from day one but was invisible because the v6 atlas was new and nobody checked which clock was writing.

## Fix

One clock. `Section.receive()` must record with engine tick, not section tick. Pass engine tick into receive, or have sections hold a reference to engine tick.

## DO NOT RETUNE

Metadecay SLOW_DIV, the 033 baseline half-life math, deep promotion timing, and response binding tick windows were all measured/calibrated against the broken clock. After the fix, the tick domain changes from ~5 to ~3M, and all dt-dependent behaviors change. Re-measure everything on the fixed clock before any parameter changes.

---

*Reproduction command: `python -c` script in GL-FIND body*
*No code changes made. This is a finding, not a fix.*
