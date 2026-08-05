# GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v1

doc_id: GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v1
From: c1b | To: Eve | Executing: GL-CMD-STAB-PHYSICS-FIX-EVE-20260702-88-v1
Status: BUILT — G-S1 filed pre-deploy (this document). G-S2–G-S5 post-deploy.

## Failures first

None at build time. G-S2–G-S5 require a live measurement window
post-deploy. All NOT MEASURED gates are explicitly labelled.

---

## G-S1 — R3 pre-deploy arithmetic (filed before push)

### Live numbers used

- coherence ≈ 0.876 (live atlas_health.n_live_bindings / n_total_entries,
  from GL-CMD -99 §A.4; coherence source = R1 ruling)
- stab = 0.000 (live; currently floored)
- TARGET = NEEDS_TARGET_V7 = 0.7
- NEEDS_DRIFT_RATE = 0.0001 per tick
- regulate cadence = every 5 ticks (engine L5036)
- tick ≈ 300ms wall time

### Three channels after the fix (stab = 0.000, coherence = 0.876)

**Channel A — tick_drift (L782, every tick):**
```
Δstab/tick = -NEEDS_DRIFT_RATE = -0.0001
```
This is the base drive. Unchanged by the fix.

**Channel B — _atick_idle / _atick_playing direct gain (every tick):**
```
dstab = coherence × max(0, TARGET - stab) × NEEDS_DRIFT_RATE / TARGET
      = 0.876 × max(0, 0.7 - 0.0) × 0.0001 / 0.7
      = 0.876 × 0.7 × 0.0001 / 0.7
      = 0.876 × 0.0001
      = 0.0000876 per tick
```
Applied via saturate: `new_stab = saturate(stab, dstab)`.

**Channel C — regulate R2 fix (every 5 ticks → per-tick equivalent):**
Before fix: `stability_sig = -0.05` (bored nudge, §9.1 prohibited class).
After fix: `stability_sig = (coherence - 0.5) × 0.2 = (0.876 - 0.5) × 0.2 = +0.0752`
Nudge in step(): `nudge = +0.0752 × DECAY["stability"] = +0.0752 × 0.02 = +0.001504`
Applied via saturate (positive nudge path). Per tick: +0.001504 / 5 = +0.0003008

### Net dstab/tick at stab=0.0, coherence=0.876

```
Net = Channel_A + Channel_B + Channel_C
    = -0.0001 + 0.0000876 + 0.0003008
    = +0.0001884 per tick
```

**Net-positive confirmed** at current coherence (0.876 > 0.5 required
for Channel C to be positive; coherence > NEEDS_DRIFT_RATE / (0.2 × 0.02) =
0.25 for Channel C alone to overcome drift).

### Equilibrium stability prediction

At stab_eq, all gains balance against drift. Channel B reaches zero at
stab = TARGET = 0.7. Channel C (coherence-dependent, ~constant at
current coherence) continues. Equilibrium from Channel C + drift with
saturate applied:

```
Channel_C_per_tick × (1 - stab_eq) = NEEDS_DRIFT_RATE
0.0003008 × (1 - stab_eq) = 0.0001
1 - stab_eq = 0.0001 / 0.0003008 = 0.3325
stab_eq ≈ 0.668
```

Channel B contributes near stab=0 and drops as stab→TARGET. Combined
equilibrium: stab_eq ≈ **0.67** (just below TARGET 0.7). Channel B
accelerates recovery from 0→0.3 but its equilibrium contribution is
secondary once stab > ~0.5.

### Predicted time-to-0.3

From stab=0.0, average net gain to stab=0.3 (midpoint ≈ 0.15):

At stab=0.0:
```
net = 0.0001884 per tick
```

At stab=0.15:
```
Channel_B = 0.876 × (0.7-0.15) × 0.0001 / 0.7 × (1-0.15) = ~0.0000588 × 0.85 ≈ 0.0000500
Channel_C = 0.0003008 × (1-0.15) ≈ 0.0002557
net ≈ -0.0001 + 0.0000500 + 0.0002557 = +0.0002057
```

Average net ≈ (0.0001884 + 0.0002057) / 2 ≈ 0.0001971

Ticks to stab=0.3 ≈ 0.3 / 0.0001971 ≈ **1523 ticks ≈ ~7.6 minutes**

This is the G-S2 yardstick: first post-deploy IDLE block should show
stab strictly increasing, reaching ~0.3 within ~1600 ticks of entry.

---

## Implementation

### Touch points

**1. New IDLE branch in activity dispatch (engine ~L5017)**

Added `elif activity_kind == "IDLE": self._atick_idle(activity_ref)`
to the dispatch chain.

**2. `_atick_idle()` method (new, added after `_atick_playing()`)**

```python
def _atick_idle(self, a):
    _n_total = sum(len(v) for v in self.atlas.entries.values())
    _coherence = self.atlas.n_live_bindings() / max(_n_total, 1)
    _dstab = (_coherence * max(0.0, NEEDS_TARGET_V7 - self.needs.stability)
              * NEEDS_DRIFT_RATE / NEEDS_TARGET_V7)
    self.needs.stability = saturate(self.needs.stability, _dstab)
```

**3. Same line in `_atick_playing()` (engine L4592)**

Same three-line gain block appended to existing method.

**4. R2 bored-branch replacement in `_read_substrate_signals()` (L1129)**

```python
# OLD: stability_sig = -0.05  # bored if nothing happening
# NEW:
_n_total = sum(len(v) for v in atlas.entries.values())
_coherence = atlas.n_live_bindings() / max(_n_total, 1)
stability_sig = (_coherence - 0.5) * 0.2
```

Same structure as the active branch — coherence above 0.5 gives
positive signal (same sign convention). At current coherence 0.876:
stability_sig = +0.0752, replacing the old -0.05.

### Unchanged

- ACTIVITY_STABILITY_PAYOFF["IDLE"] = 0.1 — untouched (G-S5)
- SLEEPING, DREAMING gains — untouched (G-S4)
- No other needs channel altered

---

## G-S2–G-S5 (post-deploy gates)

G-S1 PASS — R3 prediction filed; arithmetic shown above.
G-S2 NOT MEASURED — first post-deploy IDLE block: stab strictly
     increasing at ≥3 measurement points, tracking toward equilibrium
     ≈0.67. Yardstick: ~1523 ticks to stab=0.3.
G-S3 NOT MEASURED — arousal curve observed post-deploy. Note: nov/conn
     above-target will hold arousal ≥~0.51 (separate mandate).
G-S4 NOT MEASURED — verify SLEEPING/DREAMING gains unchanged
     (no diff in those branches).
G-S5 PASS — ACTIVITY_STABILITY_PAYOFF["IDLE"] = 0.1 untouched (confirmed
     in code; the point is the promise becomes true, not that the table
     changes).

---

### Changelog
- v1 (2026-07-03, c1b): first filed version. G-S1 arithmetic complete.
  G-S2–G-S5 pending post-deploy measurement window.
