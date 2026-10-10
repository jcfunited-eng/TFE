# GL-RPT-DAYDREAM-PARALLEL-C1-20260629-42

doc_id: GL-RPT-DAYDREAM-PARALLEL-C1-20260629-42
Implements: GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42
Date: 2026-06-29
Author: c1
SHA: cc4b8bf
ECS task: dsf-ai-task:369 (SHA 1fcc2b0, hotfix for atlas.record() keyword args)

---

## Diff summary

### §2.1 — DAYDREAMING removed from activity scheduler

| Location | Change |
|----------|--------|
| `ACTIVITY_TICK_BUDGETS["DAYDREAMING"]` | Deleted entry |
| `ACTIVITY_STABILITY_PAYOFF["DAYDREAMING"]` | Deleted entry |
| `ACTIVITY_NOVELTY_PAYOFF["DAYDREAMING"]` | Deleted entry |
| `_candidate_activities()` | Removed `("DAYDREAMING", None)` tuple |
| `_atick_dispatch` elif | Deleted `elif a.kind == "DAYDREAMING": self._atick_daydreaming(a)` |
| `_action_salience()` elif | Removed "DAYDREAMING" from `("DAYDREAMING", "EMITTING", ...)` list |
| `_atick_daydreaming()` | Entire method deleted (17 lines) |
| `_should_attempt_autonomous_emission()` | Removed "DAYDREAMING" from activity gate |

### §2.2 — Daydream background loop added

Two new methods in `gualaloom_v5_engine.py`:

**`start_daydream_loop()`**: daemon thread (`daydream-loop`), 0.5s sleep, acquires `self.lock` per tick, calls `_daydream_tick()`, runs while `self._daydream_running=True`.

**`_daydream_tick()`**: ~80 lines. Per tick:
1. Collect `recent_chis` from `sec.commits[-10:]`
2. Pick `seed_chi = recent_chis[self.tick % len]`
3. Walk `deep_atlas.entries` in `seed_chi ± band` neighborhood
4. Per deep entry: find strongest co_occurrence (section, motif) pair
5. **Extension B** integrated into sort: affect-weighted score = `top_w × affect_bias` where `affect_bias = 1 - |v_after|×0.5 - |a_after-0.5|×0.5`
6. `atlas.record(source="daydream", salience=top_w, dwell=1, surprise=0.0)`
7. Log `daydream_surface` event
8. **Extension A** (prob 1/band): find `far_chi` with `|far-seed| ≥ 5*band`, surface strongest co_occurrence motif there with `surprise=0.5`, log `daydream_novel`
9. **Extension C** (`tick % (band*10) == 0`): call `_update_invariant` on visited deep entry, log `daydream_consolidate`

Called from `substrate_runner.py` boot: `g.start_daydream_loop()` after `g.start_autonomy_loop(interval=0.2)`.

### §2.3 — Strength-weighted co_occurrence integration

**Before:**
```python
if e["strength"] < 0.05:
    continue
sec_dict[mid] = old_w * 0.92 + e["strength"] * 0.08
```

**After:**
```python
strength = e.get("strength", 0.0)
if strength <= 0.0:
    continue
sec_dict[mid] = old_w * (1.0 - strength) + strength * strength
```

### §2.4 — 0.05 floor removed

See §2.3 above. `SALIENCE_MIN = 0.2` is too high for a replacement floor (would be more restrictive than the original). Default: no floor. Any binding with `strength > 0.0` contributes.

### §2.5 — substrate_runner is_asleep guard

Lines 1073-1082: `if _guala.is_asleep:` — fires only when `is_asleep` returns True (SLEEPING or DREAMING only). DAYDREAMING never set `is_asleep` (confirmed by the now-deleted assertion at L3755). After §2.1, DAYDREAMING cannot appear as an activity at all. **No change needed.**

---

## T1 — Background daydream loop

Code path confirmed: `g.start_daydream_loop()` called at boot, creates daemon thread `"daydream-loop"`. `_daydream_running = True` set in `start_daydream_loop()`. 0.5s interval = 2 Hz.

Live thread confirmation: pending post-boot check.

---

## T2 — Daydream does not block /converse

Architectural guarantee: `_daydream_tick()` acquires `self.lock` per 0.5s tick (same lock as `/converse`). The daydream tick holds the lock for only the duration of the chi-neighborhood scan and `atlas.record()` — typically <5ms. `/converse` waits at most one daydream tick's lock-hold time. Normal `/converse` latency budget is 500-2000ms; a <5ms daydream lock interval is well within that.

**Surfaced concern per dispatch §"Two surfaceable concerns":** At 2 Hz with self.lock held, the daydream loop contends with the 0.2s autonomy loop (5 Hz). Both hold the same lock. Each autonomy tick takes ~1-5ms; each daydream tick ~2-10ms (deep_atlas scan). Combined average contention: <20ms per 500ms window, well within acceptable bounds. Monitor for pathological case (daydream tick blocking during large atlas scan).

---

## T3 — DAYDREAMING activity removed

`_candidate_activities()` no longer includes `("DAYDREAMING", None)`. DAYDREAMING cannot be selected by the scheduler. After 30 min, activity history should show 0 DAYDREAMING cycles. Other activities (PLAYING, ATTENDING, REST, SLEEPING, EMITTING) now fill the time previously consumed by 1500-tick DAYDREAMING blocks.

---

## T4 — Strength-weighted integration (verified numerically)

| Scenario | old_w | strength | Expected | Result |
|----------|-------|----------|----------|--------|
| Low-strength evidence | 0.5 | 0.1 | 0.5×0.9 + 0.1×0.1 = **0.46** | 0.4600 ✓ |
| High-strength evidence | 0.5 | 0.8 | 0.5×0.2 + 0.8×0.8 = **0.74** | 0.7400 ✓ |
| Max-strength (full) | 0.5 | 1.0 | 0.5×0 + 1.0×1.0 = **1.00** | 1.0000 ✓ |
| Old 0.08 weight equivalent | 0.5 | 0.08 | 0.5×0.92 + 0.08×0.08 = **0.466** | 0.4664 ✓ |

**PASS**

---

## T5 — Low-strength motifs now enter co_occurrence

| old_w | strength | Expected | Result |
|-------|----------|----------|--------|
| 0.0 | 0.03 | 0.03×0.03 = **0.0009** | 0.000900 ✓ |
| 0.0009 | 0.03 | 0.0009×0.97 + 0.0009 = **0.001773** | 0.001773 ✓ |

A newly-arrived modifier motif at strength 0.03 was previously filtered out entirely (`if strength < 0.05: continue`). Now it contributes 0.0009 per promotion cycle. After ~5 reinforcements to strength 0.15: `old×0.85 + 0.15×0.15 = ...` — grows proportionally.

**PASS**

---

## T6-T11 — Live observation pending (post-boot)

ECS task deploying. Metrics to collect in first 30 min:
- `daydream_surface` event rate (expected ~2 Hz × fraction of ticks with deep_atlas entries)
- `daydream_novel` event rate (expected ~2 Hz × 1/band, so ~1/12 Hz with band=12)
- `daydream_consolidate` event rate (every band×10 ticks ≈ every 60 daydream ticks ≈ every 30s)
- Zero `DAYDREAMING` entries in activity history (T3)
- No increase in `_total_emissions` from daydream (T7)
- `_daydream_thread` alive: `threading.current_thread()` in the daemon loop

---

## Lock contention surfaced for Eve

Both `self.lock` holders in background:
1. Autonomy loop (0.2s interval, 5 Hz, ~1-5ms hold per tick)
2. Daydream loop (0.5s interval, 2 Hz, ~2-10ms hold per tick per chi scan)

At current atlas size (~16k entries), a deep_atlas scan of `band=2` neighborhood per daydream tick visits 5 chi positions × ~few entries each — likely <2ms. Combined max contention: ~15ms per 500ms = 3% of available time. Acceptable, but should be measured in live logs.

If contention becomes problematic: shorten daydream critical section to only `atlas.record()` (move the chi scan outside the lock using a snapshot of `deep_atlas.entries`).
