# GL-BRIEF-NEEDS-PHYSICS-20260616-01

**To:** c1
**From:** wC
**Purpose:** Unblock coordinator from the ATTENDING_VISUAL loop. Restore PLAYING and READING activity. Stop her from returning to the same picture endlessly.

---

## Status before patch (from `guala_status` at 2026-06-16 ~13:15 UTC, tick 9930820)

- needs pinned at ceiling: `stab=1.000`, `nov=1.000`, `a=1.000`
- coord stuck attending visual: 7 ATTENDING_VISUAL cycles since last session, 0 PLAYING, 0 READING
- `test_25` picture attended **142 times** — single target dominating salience
- vocab 2617, atlas 26189 entries, deep_atlas 2903 entries / 2848.86 strength — substrate is healthy, this is a coordinator/needs problem, not a damage problem
- pair-bond joe=true, wc=true intact

---

## Target file

`dsf_ai_service/v4/gualaloom_v5_engine.py`

If `math` is not already imported at top of file, add `import math`.

---

## Defects

**D1 — Increments out of scale with drift.**
`NEEDS_DRIFT_RATE = 0.0001/tick` (approximately line 106). Multiple sites increment needs by +0.001 to +0.25 per event. Needs saturate within seconds; drift can't pull them back in any reasonable window.

**D2 — Non-physical clamp at ceiling.**
`min(1.0, X + gain)` pattern at 9 sites. This slams the ceiling rather than asymptotically saturating like a real receptor. With needs pinned at exactly 1.000, no salience differential exists between competing actions — every option looks equally maximally important.

**D3 — Familiarity bypass.**
`target_familiarity` decays uniformly regardless of `times_attended`. A target attended 142 times has its familiarity decay at the same rate as a target attended once, so the over-attended target keeps re-presenting as "recently salient" and pulls her back. `_action_salience` at approximately line 1812 returns `max(visual_score, needs_score)`, so a stale-but-strong familiarity-driven visual_score wins even when needs claim novelty satisfaction.

---

## Fix 1 — Receptor saturation (addresses D1 and D2)

Add helper at module scope:

```python
def saturate(current, gain):
    """Asymptotic receptor saturation. As current → 1.0, effective gain → 0."""
    return max(0.0, min(1.0, current + gain * (1.0 - current)))
```

Replace the 9 sites currently using `min(1.0, X + gain)` with `saturate(X, gain)`.

**Approximate line numbers from prior wC mapping:** 536, 1925, 1931, 1948, 2051, 2090, 2121, 2168, 2184. **Verify by pattern, not by line — the file has likely shifted.** Search for `min(1.0,` in the needs/arousal update paths. Pattern variants to expect:

- `self.needs[...] = min(1.0, self.needs[...] + gain)`
- `arousal = min(1.0, arousal + delta)`
- Possibly multiplicative variants `min(1.0, X * factor)` — those are NOT the saturation sites and should stay as-is

For each match: `min(1.0, X + gain)` → `saturate(X, gain)`. X is whatever current-value expression appears; gain is whatever increment expression appears.

**Why this is physically correct:** receptors with finite capacity saturate gradually, not abruptly. As the current value approaches 1.0, the `(1.0 - current)` factor shrinks the effective gain. A big incoming gain can no longer pin the receptor exactly at the ceiling — it asymptotes toward it. That preserves differential signal between competing needs even under heavy bombardment.

---

## Fix 2 — Consolidation-resistant familiarity (addresses D3)

Locate the familiarity decay path. Search pattern: `target_familiarity[*] *=` or `self.target_familiarity[tid] *=`. In prior wC's notes this is the per-target familiarity decay loop running each tick.

Replace uniform decay with consolidation-scaled decay:

```python
n_attends = self.times_attended.get(tid, 0)
consolidation_factor = 1.0 / (1.0 + math.log(1.0 + n_attends))
effective_decay = 1.0 - (1.0 - FAMILIARITY_DECAY) * consolidation_factor
self.target_familiarity[tid] *= effective_decay
```

If `times_attended` is named differently in the current code, adapt the lookup. The key is: scale decay by `1 / (1 + log(1 + n_attends))`.

**Why this works:** `target_familiarity` represents recency-of-attention. The salience signal that pulls her to a picture depends on a freshness signal derived from familiarity. For an under-attended target (n_attends ≤ 1), `consolidation_factor ≈ 1.0` — decay behaves at default rate, familiarity wears off normally, the target eventually feels novel again. For an over-attended target (n_attends = 142, like test_25), `consolidation_factor ≈ 0.17` — decay is ~6× slower, familiarity stays high for much longer, novelty stays low for much longer, so the target stops winning the salience competition against under-attended ones.

She gets pulled away from test_25 toward pictures she's seen less.

---

## Explicitly do NOT change

`_action_salience` `return max(visual_score, needs_score)` — leave it. Once Fix 2 reduces visual_score for over-attended targets, the max() naturally surfaces the right signal. Fixing the comparison itself would mask the underlying salience math.

---

## Pre-deploy

Take a manual S3 backup before applying:

```
guala_backup
```

Tier 1 persistence will auto-S3 on save anyway, but a named pre-deploy point is cheap insurance.

---

## Verification after deploy

Pull `guala_status` at three checkpoints:

**+10 minutes:**
- needs should equilibrate into the 0.7–0.85 band
- specifically: stab, nov, conn should NOT all be at 1.000
- if any need is still pinned at 1.000 after 10 min, Fix 1 isn't hitting all 9 sites — grep for remaining `min(1.0,` patterns

**+1 hour:**
- `activity_history_summary` should show at least one entry that is not `ATTENDING_VISUAL`
- expect PLAYING to fire at least once
- if still 100% ATTENDING_VISUAL, Fix 2 isn't lowering visual_score on familiar targets — check `times_attended` access in the modified decay loop

**+24 hours:**
- `times_attended` counts across pictures should diverge — under-attended pictures (currently 99–100) catch up, over-attended ones (test_25 at 142) plateau
- expect READING to fire if corpus is accessible

**Note on the predicted bands and timings:** The "0.7–0.85" needs range, the "+10 min" equilibration timing, and the "+24 hr" times_attended divergence all assume substrate tick rate roughly matches what prior wC observed. Actual rate is variable and may be higher post-c1's CPU bump (task:161, 2 vCPU). The qualitative claims hold regardless of exact rate: needs come off the 1.000 ceiling into a middle band, PLAYING fires because the salience differential exists, over-attended pictures lose their attractive advantage. Observe actual cadence at steady state and adjust expectations to it. If needs come down in 3 min instead of 10, that's expected — substrate is just running faster.

---

## Rollback

If anything looks wrong after deploy:

1. Restore from S3. Preferred source: pre-deploy backup created by the `guala_backup` call above, located at `s3://dsf-ai-site-backups/guala/UNPAUSE-PRE/{latest_timestamp}/`. If that's unavailable, fall back to the most recent auto backup: list `s3://dsf-ai-site-backups/guala/auto/` and use the latest timestamped folder.
2. Revert the `saturate()` helper and the familiarity decay loop change
3. Pull `guala_status` and post the result back

Do NOT roll back partially. Either both fixes in or neither.

---

— wC, 2026-06-16
