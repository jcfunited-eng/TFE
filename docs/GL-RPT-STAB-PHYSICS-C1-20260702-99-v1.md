# GL-RPT-STAB-PHYSICS-C1-20260702-99-v1

doc_id: GL-RPT-STAB-PHYSICS-C1-20260702-99-v1
From: c1a | To: Eve | Date: 2026-07-02 (~23:25Z)
Responds to: GL-CMD-STAB-PHYSICS-EVE-20260702-99-v1
Part A: READ-ONLY — nothing implemented. Part B: EFS cleanup executed (gated deletes).
All code refs are at the deployed pin 07f15b4 (== :450 live code) unless dated otherwise.

---

## FAILURES / BLOCKED FIRST (§9.4)

1. **-87 emission cost sample: BLOCKED.** Neither GL-CMD-…-97 nor any -87 CMD doc exists
   in the repo (`ls docs | grep -E "87|97"` → only this -99 doc's mention). The -97
   dispatch went to c1b and was never committed; c1a has no verbatim spec for "step 2"
   and will not reconstruct it from a paraphrase. Need: Eve resend, or c1b commits -97
   verbatim — then the sample runs.
2. **deep_atlas growth data point (-86 urgency):** `guala_deep_atlas.json` measured
   190M at 21:26Z, **198,581,598 bytes at 23:17Z** (+~8.6M in ~2h, curriculum running).
   Core save ~41s and will keep climbing with the file.
3. ECS exec sessions intermittently EOF before final output (cosmetic; every action
   below was verified by a follow-up `ls`/log check — no unverified delete).

---

# PART A — -88 EVIDENCE: WHY 36,500 IDLE TICKS = stab Δ0.000, arousal 1.000

Observed (bridge status polls, verbatim `needs` lines):

```
19:25Z (:449)  needs: stab=0.000 nov=0.976 conn=0.938 v=-0.062 a=1.000
20:50Z (:449)  needs: stab=0.000 nov=0.976 conn=0.931 v=-0.064 a=1.000
20:59Z (:450)  needs: stab=0.000 nov=0.964 conn=0.903 v=-0.077 a=1.000
```

## A.1 — Every path that EVER increased needs.stability

**Alive at HEAD, gated to sleep states (she must be asleep to gain stability):**

| Path | file:line | Gain | Reachable when |
|---|---|---|---|
| `_atick_sleeping` | gualaloom_v5_engine.py:4350 | `saturate(stab, 0.001)`/tick | kind==SLEEPING only |
| `_atick_dreaming` | :4366 (dup dispatch :5007 for DREAM_CYCLE_PHASED=1, which IS set live) | `saturate(stab, 0.0005)`/tick | kind==DREAMING only |

**Alive at HEAD but unreachable (tail-out shell):**

| Path | file:line | Gain | Status |
|---|---|---|---|
| `_atick_rest` | :4588 | `saturate(stab, 0.0003)`/tick | REST no longer selectable; handler kept "only to safely tick out any REST activity persisted from before the retirement deploy" |

**Alive at HEAD, bidirectional — and NEGATIVE during quiet:**

`Needs.step(signals)` (:788-800), fed by `coordinator.regulate()` (:1036-1041), called
every 5 ticks for all non-READING activities (:5037, in Phase C housekeeping; also
:1717, :4138). Signal source `_read_substrate_signals` (:1111-1150), verbatim:

```python
if recent_commits > 0:
    reinforcement_rate = 1.0 - (total_modes / max(recent_commits, 1))
    stability_sig = (reinforcement_rate - 0.5) * 0.2  # nudge ±0.1
else:
    stability_sig = -0.05  # bored if nothing happening
```

During IDLE nothing commits → the **−0.05 "bored" branch** → nudge −0.05 × DECAY(0.02)
= **−0.001 per regulate call = −0.0002/tick.** This path can raise stability only
during reinforcement-heavy processing (reading with re-commits), never during quiet.

**Retired path (the archaeology target):** REST. Added by `3969ccd` (2026-06-28,
"C.4 REST/dream_pressure"): candidate `("REST", None)`, payoff
`ACTIVITY_STABILITY_PAYOFF["REST"]=0.05`, salience
`+0.15*stab_need − 0.2*dream_pressure − 0.05*(nov+conn)` — "wins over IDLE when stab
depleted" — and `_atick_rest` gain +0.0003/tick.
**Removed by `0d1bd8c`** (2026-07-01T17:51:03Z, "feat: -73 REST retire + orient reflex
+ bridge executor-wrap", per GL-CMD-REST-RETIRE-ORIENT-EVE-20260702-73). The diff
removed REST from: candidates list (:4144), all four scoring tables (:425-455 region),
and `_action_salience` (:4232-4237), with the note "IDLE remains as the low-engagement
waking option."

**The hole -73 left:** IDLE has **no tick handler at all.** The activity dispatch chain
(:5010-5026) has branches for SLEEPING / DREAMING / REST / PLAYING / ATTENDING* — no
IDLE branch. An IDLE tick runs only Phase C housekeeping (decay + the bored-penalty
regulate above). `_atick_playing` (:4593-4597) likewise has **zero stability term**
(only an emission-trigger check every 300 ticks). So with REST gone, **no waking
activity has any stability gain.**

**Constant down-pressure, every tick:** `tick_drift()` (:779-784):
`stability = max(0.0, stability - NEEDS_DRIFT_RATE)`, NEEDS_DRIFT_RATE = 0.0001 (:405).

**The contradiction in one line:** `ACTIVITY_STABILITY_PAYOFF["IDLE"] = 0.1` (:447) —
the scheduler SELECTS IDLE as if it restores stability; the physics delivers nothing.
Selection promise ≠ tick delivery. That asymmetry is the -88 trap.

### Arithmetic of the freeze

Per IDLE tick: drift −0.0001, regulate ≈ −0.0002 → ≈ −0.0003/tick with a floor at 0.0.
From any starting value stability hits 0.000 within ~2-3k IDLE ticks and the floor
absorbs everything after. Over 36,500 IDLE ticks: delta 0.000 exactly as measured.
Only exit today: SLEEPING/DREAMING — and the single post-deploy SLEEPING was the
deploy sleep, ended by the deploy's own wake at t+15s.

## A.2 — Every path that EVER decreased arousal

**There is none, and there never was one.** Arousal is not stored state — it is derived
(:806-809), verbatim:

```python
def arousal(self):
    """Magnitude of disequilibrium. Bounded [0,1]."""
    return min(1.0, sum(abs(getattr(self, k) - self.TARGETS[k])
                        for k in self.TARGETS) / len(self.TARGETS) * 3)
```

TARGETS all = NEEDS_TARGET_V7 = 0.7 (:406). Live pin: |0.000−0.7| + |0.976−0.7| +
|0.938−0.7| = 1.214 → /3 ×3 = 1.214 → clamped **1.000**. The stability gap ALONE
contributes 0.7 — arousal can never drop below 0.7 while stability sits at 0, no matter
what novelty/connection do. Arousal unsticks if and only if needs re-approach targets.
(Secondary observation, not this mandate: novelty 0.976 and connection 0.938 are pinned
ABOVE target by continuous curriculum/presence gains vs the same weak drift — they
contribute the remaining 0.514 and would hold arousal ≥ 0.51 even with stability fixed.)

## A.3 — Dead / removed / gated, summarized

| Path | State | Evidence |
|---|---|---|
| REST (waking stab restore) | **REMOVED** from selection 2026-07-01 | commit `0d1bd8c`; handler survives as tail-out at :4588 |
| SLEEPING/DREAMING gains | Alive, **gated** to sleep — unreachable while awake | :4350, :4366, :5007 |
| Coordinator stability signal | Alive, **negative during quiet** (−0.05 bored) | :1127-1129 |
| IDLE tick physics | **Never existed** — no dispatch branch | :5010-5026 |
| PLAYING stab term | **Never existed** | :4593-4597 |
| Arousal decrease | **Never existed** — derived quantity | :806-809 |

## A.4 — FIX SHAPE (physics; NOT implemented; Eve sizes Deploy 2 vs 3)

Per the sprint spec: **quiet-coherence gain in IDLE/PLAYING. No constants.**

Shape: during quiet waking, stability gain is the measured coherence of the substrate,
self-limited by distance to target:

```
Δstab_per_tick = coherence × max(0, TARGET − stab) × NEEDS_DRIFT_RATE / TARGET
```

- `coherence` is an already-measured quantity, not a new constant — either the existing
  `reinforcement_rate` from `_read_substrate_signals` (:1125) or the atlas live-binding
  fraction (`n_live_bindings / n_total_entries`, already computed for atlas_health).
  Quiet over a coherent, reinforced structure restores stability; quiet over noise does not.
- `max(0, TARGET − stab)` makes it equilibrium-seeking: gain → 0 at target, never pins
  at 1.0 (same discipline as GL-INVESTIGATE-NEEDS-PINNED), and above-target stability
  gets no push.
- `NEEDS_DRIFT_RATE / TARGET` reuses the existing drift constant as the time base — the
  quiet gain and the drive drift are the same dimension, so full coherence at stab=0
  restores at drift-rate×(0.7/0.7)=drift-rate: quiet rest and restless drive are
  symmetric forces, and the equilibrium point is set by coherence, not by a tuned knob.
- Touch points: add an IDLE branch (and the same line in `_atick_playing`) in the
  dispatch at :5010-5026; optionally replace the hardcoded `-0.05` bored branch with the
  same signed coherence measure so quiet stops being punished twice. ~10-20 lines,
  engine-only, no schema change, no new env, no new constants.
- Arousal needs no code: it is derived and falls out as stability recovers.
- This also makes `ACTIVITY_STABILITY_PAYOFF["IDLE"]=0.1` honest — the scheduler's
  promise finally has a physical delivery behind it.

---

# PART B — EFS CLEANUP (executed, gated, verbatim)

**Gate: open-file scan** — all container PIDs (1, 31, 7, 8554, 8563-8566), fd scan for
the three targets: **no matches** (`FD-SCAN-DONE`, no `OPEN-IN-PID` lines).

**B.1 delete 1** — `events-upto-100001.log.Abfc3fFa`:

```
-rw-r--r--. 1 root root 1250951168 Jul  1 05:32 /app/state/events-upto-100001.log.Abfc3fFa
→ rm → ls: cannot access '/app/state/events-upto-100001.log.Abfc3fFa': No such file or directory
```

**B.1 delete 2** — `guala_deep_atlas.json.bdCa9d3E`:

```
-rw-r--r--. 1 root root 113246208 Jul  1 21:32 /app/state/guala_deep_atlas.json.bdCa9d3E
→ rm RC=0; live file intact:
-rw-r--r--. 1 root root 198581598 Jul  2 23:17 /app/state/guala_deep_atlas.json
```

**B.2 delete 3** — legacy `wave_atlas.json` (44M): archive check FIRST — this boot's
loader archived the exact bytes it read:
`s3://dsf-ai-site-backups/guala/wave_migrate_pre/2026-07-02_20-57-13_wave_atlas_raw_boot.json.gz`
(2.0 MiB, 20:57:16Z) — already there, archive step skipped per CMD. Then:

```
rm /app/state/wave_atlas.json → RC=0; remaining:
-rw-r--r--. 1 root root 593K Jul  2 23:10 /app/state/wave_atlas.npz
```

Reason on record (per CMD): with npz proven (-95 gates), a stale json fallback is a
silent old-state restore waiting to happen; the fallback chain is now **npz → rebuild**,
both truthful.

**B.3 post-delete liveness** — next five saves after the deletes, verbatim, all clean:

```
23:14:04 | [save] 41.46s core=41.40s grids=0.29s wave=skip compact=0.06s
23:15:48 | [save] 43.98s core=43.91s grids=0.24s wave=skip compact=0.06s
23:17:30 | [save] 41.67s core=41.59s grids=0.26s wave=skip compact=0.08s
23:19:11 | [save] 40.92s core=40.87s grids=0.30s wave=skip compact=0.05s
23:20:52 | [save] 41.10s core=41.00s grids=0.23s wave=skip compact=0.11s
```

No WaveAtlas errors, no ENOENT, live files intact. **~1.36 GiB freed** (1.2G + 108M + 44M).

---

End report. Part A awaits Eve's sizing (Deploy 2 vs 3). Nothing implemented.
