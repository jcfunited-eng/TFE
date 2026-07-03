# GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2

doc_id: GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2
From: c1b | To: Eve | Executing: GL-CMD-STAB-PHYSICS-FIX-EVE-20260703-88-v2
Status: BUILT — G-S1 filed pre-push (this document). G-S2v2/G-S3v2/G-S6 post-deploy.

## Failures first

None at build time. G-S1 arithmetic below (blocking pre-push). G-S2v2–G-S6
require post-deploy measurement window.

---

## Root cause (from Deploy-2 G-S2 FAIL forensics)

The regulate function (`_read_substrate_signals()`) had two branches:

**ACTIVE branch (when `recent_commits > 0`):**
```
reinforcement_rate = 1.0 - (total_modes / max(recent_commits, 1))
stability_sig = (reinforcement_rate - 0.5) * 0.2
```
`recent_commits` and `total_modes` are LIFETIME counters (never reset). As
the atlas matures, `total_modes` grows to thousands while `recent_commits`
grows proportionally; the ratio `total_modes / recent_commits` stays >> 1 so
`reinforcement_rate` is structurally negative. Observed: −0.377 → signal
−0.1754 → nudge = −0.1754 × 0.02 = −0.003508/call → per tick (every 5 ticks):
**−0.0007016/tick drain, every non-reading state, always.**

**QUIET branch (when `recent_commits == 0`):** only fires on a fresh substrate
with no learning history. After any corpus reading this branch never fires.
Despite being shipped correctly in Deploy 2 (R2), it never executed in practice.

**G-S2 FAIL mechanism:** IDLE gain (Channel B, +0.0000876/tick) + regulate
quiet branch (would have been +0.0003008/tick) were positive, but the active
branch drain (−0.0007016/tick) overwrote them because `recent_commits > 0` is
always true after boot. Net in IDLE was −0.0001 + 0.0000876 − 0.0007016 =
**−0.0007140/tick** — stab fell, not rose.

---

## The fix

**`dsf_ai_service/v4/gualaloom_v5_engine.py` — `_read_substrate_signals()` (L1110)**

Retired the `if recent_commits > 0 / else` branch entirely for the stability
signal. Both paths replaced with the single coherence measure already shipped
in the quiet branch (Deploy 2, R2):

```python
_n_total = sum(len(v) for v in atlas.entries.values())
_coherence = atlas.n_live_bindings() / max(_n_total, 1)
stability_sig = (_coherence - 0.5) * 0.2
```

`recent_commits` and `total_modes` loop retained — needed by the novelty signal
(`novelty_rate = total_modes / recent_commits`). Only their use in the stability
path is retired.

**Unchanged (per CMD discipline):**
- `_atick_idle()` / `_atick_playing()` Channel B gain (Deploy 2, v1)
- tick_drift Channel A
- SLEEPING / DREAMING gains
- ACTIVITY_STABILITY_PAYOFF table
- Needs.step(), saturate(), all other need channels

---

## G-S1 — pre-push arithmetic (blocking)

### Live numbers used

- coherence ≈ 0.876 (R1 measure: n_live_bindings / n_total_entries;
  same source as v1 G-S1, GL-CMD-99 §A.4)
- stab = 0.000 (live; currently floored)
- TARGET = NEEDS_TARGET_V7 = 0.7
- NEEDS_DRIFT_RATE = 0.0001/tick
- DECAY["stability"] = 0.02
- regulate cadence = every 5 ticks (confirmed L1722, L4143, L5062)
- tick ≈ 300ms wall time

### Three channels after v2 fix (stab=0, coherence=0.876)

**Channel A — tick_drift (L782, every tick):**
```
Δstab/tick = -NEEDS_DRIFT_RATE = -0.0001
```

**Channel B — _atick_idle / _atick_playing (every tick, IDLE/PLAYING only):**
```
_dstab = coherence × max(0, TARGET - stab) × rate / TARGET
       = 0.876 × 0.7 × 0.0001 / 0.7
       = 0.0000876/tick  (via saturate at stab=0)
```
Unchanged from v1; fires only in IDLE and PLAYING activity states.

**Channel C — regulate, now both branches (every 5 ticks):**
```
stability_sig = (0.876 - 0.5) × 0.2 = 0.376 × 0.2 = 0.0752
nudge/call    = 0.0752 × DECAY["stability"] = 0.0752 × 0.02 = 0.001504
via saturate at stab=0: 0.001504 × (1-0) = 0.001504/call
per tick:     0.001504 / 5 = +0.0003008/tick
```

### Net dstab/tick in IDLE state (stab=0, coherence=0.876)

```
Net = A + B + C
    = -0.0001 + 0.0000876 + 0.0003008
    = +0.0001884/tick
```

**Net-positive confirmed.** This is the same prediction as v1 G-S1 — now
actually achievable: the active branch drain (−0.0007016/tick) that prevented
it from materialising is retired.

### Net dstab/tick in ACTIVE/curriculum state (stab=0, coherence=0.876)

Channel B does not fire during corpus reading (only in IDLE/PLAYING activities).

```
Old (v1): Net = A + C_old = -0.0001 + (-0.0007016) = -0.0008016/tick  ← drain
New (v2): Net = A + C_new = -0.0001 + (+0.0003008) = +0.0002008/tick  ← gain
```

Swing: **+0.0010024/tick** in curriculum state. G-S6 yardstick.

### Equilibrium stability prediction (IDLE)

Near stab_eq, via saturate both Channel B and C asymptote:
- Channel C at stab_eq ≈ 0.67: 0.0003008 × (1-0.67) = 0.0000993
- Channel B at stab_eq ≈ 0.67: 0.876 × (0.7-0.67) × 0.0001/0.7 × (1-0.67)
  = 0.876 × 0.0000043 × 0.33 = 0.00000124
- Net ≈ -0.0001 + 0.00000124 + 0.0000993 ≈ 0

**stab_eq ≈ 0.67** (same as v1 prediction; same dominant-channel equilibrium)

### Predicted time-to-0.3 in IDLE state (G-S2v2 yardstick)

Using three-point Simpson estimate (stab 0, 0.15, 0.3):

At stab=0:   net = +0.0001884/tick
At stab=0.15:
  B = 0.876×(0.7-0.15)×0.0001/0.7×(1-0.15) = 0.0000584
  C = 0.0003008×0.85 = 0.0002557
  net = -0.0001 + 0.0000584 + 0.0002557 = +0.0002141/tick
At stab=0.3:
  B = 0.876×(0.7-0.3)×0.0001/0.7×(1-0.3) = 0.0000350
  C = 0.0003008×0.70 = 0.0002106
  net = -0.0001 + 0.0000350 + 0.0002106 = +0.0001456/tick

Simpson average: (0.0001884 + 4×0.0002141 + 0.0001456) / 6 = +0.0001984/tick

Ticks to stab=0.3 ≈ 0.3 / 0.0001984 ≈ **1512 ticks ≈ 7.5 minutes**

G-S2v2 yardstick: first post-deploy IDLE block should show stab strictly
increasing at ≥3 measurement points, reaching ~0.3 within ~1600 ticks of entry.

---

## Gates

G-S1   PASS — pre-push arithmetic above; net positive in IDLE (+0.0001884/tick);
       ACTIVE swing +0.0010024/tick; stab_eq≈0.67; time-to-0.3≈7.5 min filed.

G-S2v2 NOT MEASURED — first post-deploy IDLE block: stab strictly increasing
       at ≥3 measured points; yardstick ~1512 ticks to stab=0.3. Stop if fails.

G-S3v2 NOT MEASURED — arousal curve post-deploy. nov/conn above-target hold
       arousal ≥~0.51 (separate mandate).

G-S6   NOT MEASURED — ACTIVE/curriculum window: needs trace shows stability no
       longer bleeding at −0.0007/tick; paste the trace verbatim.

G-S4/G-S5 (from v1): SLEEP/DREAM gains unchanged (no diff in those branches);
          ACTIVITY_STABILITY_PAYOFF["IDLE"]=0.1 untouched. Carry from v1 report.

---

### Changelog
- v2 (2026-07-03, c1b): first filed version for v2 CMD. Root cause confirmed
  (active branch is the drain), fix applied, G-S1 arithmetic filed pre-push.
  G-S2v2/G-S3v2/G-S6 pending post-deploy measurement window.
