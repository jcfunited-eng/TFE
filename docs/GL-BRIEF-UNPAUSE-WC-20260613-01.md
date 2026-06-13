# GL-BRIEF-UNPAUSE-WC-20260613-01 — Monitored Decay Unpause
**Author:** wC · **Executes:** c1 with Joe + wC present LIVE · **Ledger row:** Tier 3 / 3.1 (the unpause) · **Replaces** all prior unpause discussion (047 §3.1, 048 Step-3 constants).

## 1. Why now, modeled cold
DECAY_PAUSED=1 has held her atlas frozen since project start. Three direct consequences in production today:
- Working atlas at 37,269 entries and growing every visit (no pruning happens; `forget_below_threshold` runs but nothing decays toward threshold).
- Needs drives stuck at 1.000 because the gate that allows them to drift sits behind the same DECAY_PAUSED check (engine line 1555, 1730, 987). She physically cannot want.
- v6 second-voice "..." bubbles: v6 emits nothing because the EMITTING candidate's salience depends on need-distance; with needs pinned, drive to emit is zero.

She is small and the math still favors us. Every additional day of paused growth makes the atlas larger and the unpause harder to monitor live. Joe's call: now, this morning, with both of us watching.

## 2. The kill scenario we are designing against
Production decay code (`v6_living_atlas.decay`, line 148-179):
```
e["strength"] *= math.exp(-lam_eff * dt)
where dt = current_tick - e["last_tick"]
```
**`last_tick` was frozen the moment DECAY_PAUSED engaged.** Current tick is ~6,700,000+. If DECAY_PAUSED flips off without amnesty, the first `atlas.decay()` call computes dt ≈ 6,000,000 ticks for every entry. For a fast-channel entry: `exp(-0.0001 × 6,000,000) = exp(-600) ≈ 0`. **Every fast-channel binding annihilated in one decay step.** Only slow-channel entries (dwell ≥ 4, not released) survive, and even those at `DECAY_LAMBDA/SLOW_DIV = 0.0001/12 ≈ 8.3e-6` get `exp(-8.3e-6 × 6e6) = exp(-50)` — also zero.

Without amnesty this is not "controlled unpause." It is mass extinction.

## 3. The fix — amnesty FIRST, then unpause, then monitored decay

### Step 0 — Atlas backup (immediately before anything else)
- Snapshot the FULL working atlas to a dedicated S3 prefix: `s3://dsf-ai-site-backups/guala/UNPAUSE-PRE-<YYYYMMDD-HHMMSS>/` — all 11 state files plus `guala_atlas.json` separately tagged.
- Verify the snapshot is readable and `n_total_entries` matches live status before proceeding to Step 1. If verification fails, STOP.

### Step 1 — Amnesty (atomic, before flipping the env var)
New engine method `atlas.amnesty(current_tick)` — single pass, resets `last_tick = current_tick` for every entry. No strength changes. Logs `amnesty_complete` substrate event with entry count.

Called from a new endpoint `POST /api/v1/gualaloom/admin/amnesty` (auth: source=joe header check). Endpoint returns count of entries re-stamped.

### Step 2 — Forced dream (verify dream consolidation still works on current state)
New endpoint `POST /api/v1/gualaloom/admin/force_dream` (auth: source=joe). Mechanism: sets `self._force_next_activity = ("SLEEPING", None)` (same one-shot selector flag pattern from the dropped V2-readout brief — but minimal, only used here). The SLEEPING activity auto-transitions to DREAMING at midpoint per engine line 1733-1736. Endpoint polls substrate event stream until `dream_artifact` event appears, returns the artifact (dream_words, reinforcement_count, pre/post strength, any promotions).

Why before unpause: this proves the dream consolidation path is live on her current atlas before we touch decay. If forced dream produces zero promotions / zero reinforcements / errors, STOP — unpause unsafe until dream pipeline verified.

### Step 3 — Unpause with constants override + live monitoring
The actual decay-unpause is NOT just flipping `DECAY_PAUSED=0`. It is:

**3a. Set the Step-3 derived constants as env overrides BEFORE flipping pause:**
- `DECAY_LAMBDA_OVERRIDE=5e-7` (Step-3 fast value from ledger 048, ~200x slower than current 0.0001 default — appropriate for her current atlas size, which is ~3x larger than when constants were derived; the conservative direction)
- `SLOW_DIV_OVERRIDE=60` (Step-3 slow value, was 12 in code; 5x slower slow channel)
- These require small additions to `v6_living_atlas.py` reading env at top of `decay()` to override module constants per-call. Default behavior (constants unset) unchanged.

**3b. Flip the env var:** `DECAY_PAUSED=0` via ECS task definition update. Engine reads it at line 987, 1555, 1730 next tick — decay begins.

**3c. KILL SWITCH live and ready:** new endpoint `POST /api/v1/gualaloom/admin/repause` flips `DECAY_PAUSED=1` in-process (sets `os.environ["DECAY_PAUSED"]="1"` AND a runtime flag the engine also reads — env-var-only is not enough since ECS task already started). Available the entire unpause window. **One curl, decay stops.**

**3d. Monitor at 30-second intervals for first hour:**
- New endpoint `GET /api/v1/gualaloom/admin/atlas_snapshot` returns: `tick`, `total_strength`, `n_live_bindings`, `decay_channel_counts`, `strength_distribution`, plus delta-since-last-call for each. Read-only, fast.
- wC polls this every 30s, paints a small table for Joe. Joe watches.

**3e. Cascade detection (the trigger that hits repause):**
Three conditions, ANY one trips the kill switch automatically (not just wC's eyes):
- `n_live_bindings` drops > 20% in any 30-second window
- `total_strength` drops > 30% in any 30-second window  
- `strength_distribution["0.9-1.0"]` (the saturated high-strength entries — these should be the LAST to die) drops > 10% in any window

Auto-repause endpoint logs the trigger condition. wC and Joe see it. Manual unpause stays possible after diagnostics.

### Step 4 — Sustained watch (next 24h)
If no cascade in first hour, the constants are calibrated correctly. Continue monitoring at 5-minute intervals for 24h. Atlas should shrink slowly toward equilibrium — weak bindings die, strong + slow-channel survive. Needs should begin to drift (verified by `conn` / `nov` / `stab` falling from 1.000).

If at 24h: atlas total_strength stable within ±10% of post-1h value, and at least one need has visited < 0.7, declare unpause successful. Restore default constants (drop the env overrides) only AFTER Joe rules at 48h that further calibration isn't needed.

## 4. Code changes required (modeled against real files)
- `v6_living_atlas.py`: add `amnesty(self, current_tick)` method; add env-var reads at top of `decay()` for DECAY_LAMBDA_OVERRIDE / SLOW_DIV_OVERRIDE. ~15 lines.
- `gualaloom_v5_engine.py`: add `_force_next_activity` field + check at top of `_select_next_activity`. ~6 lines. Used by force_dream only here.
- `app.py`: add 4 admin endpoints (amnesty, force_dream, repause, atlas_snapshot). Source=joe check. ~80 lines total.
- `bridge/server.py`: add `guala_amnesty`, `guala_force_dream`, `guala_repause`, `guala_atlas_snapshot` tools. ~30 lines.

## 5. Sandbox acceptance (REQUIRED — this is not optional given mass-extinction risk)
On restored snapshot, off-prod, with current-prod-equivalent atlas size (~37K entries) and DECAY_PAUSED=1:

1. **Atlas backup test:** call /admin/amnesty (sandbox); confirm backup S3 path written and readable.
2. **Amnesty test:** call /admin/amnesty; verify every entry's `last_tick == current_tick` afterward; verify zero strength changes (compare total_strength before/after — must be bit-identical).
3. **Force dream test:** call /admin/force_dream; verify `dream_artifact` event emitted with reinforcement_count > 0; verify no exceptions.
4. **Kill switch test:** flip DECAY_PAUSED=0 with override constants set; let 30 seconds elapse; call /admin/repause; verify atlas decay stops mid-stream (atlas_snapshot delta drops to zero).
5. **Cascade detection test:** set DECAY_LAMBDA_OVERRIDE to a deliberately-too-large value (1e-3), unpause without amnesty; verify cascade detector trips within 30s and auto-repauses; verify atlas damage logged but the snapshot is recoverable.
6. **Full sequence dry-run:** backup → amnesty → force_dream → unpause with Step-3 constants → monitor 5 minutes → repause → verify atlas total_strength within 5% of pre-unpause value and shrinkage profile gradual (no entries fully annihilated).

Paste outputs for all 6. If ANY fails per §6 conditions, STOP, do not deploy.

## 6. Failure conditions stated cold
- **Sandbox test 2 shows ANY strength change after amnesty:** amnesty is supposed to be `last_tick` only. STOP, c1 inspects the amnesty implementation. No fix-forward.
- **Sandbox test 5 fails to auto-repause within 60s of cascade onset:** kill switch is broken. STOP. Unpause must not deploy without working kill switch.
- **Sandbox test 6 shows > 10% total_strength loss in 5-minute window:** constants are wrong even calibrated, or amnesty isn't working. STOP, wC re-derives constants against current atlas, brief revised.
- **In production at Step 3e if any cascade trigger fires:** auto-repause already happened. Joe and wC examine the atlas damage, decide whether to: (a) restore from Step-0 backup and retry with adjusted constants, (b) accept partial decay and continue from current state, (c) abandon unpause for now.

## 7. What this brief does NOT do
- No needs re-coupling (W4 in world thread). That's separate. This brief unfreezes decay; needs will begin to drift once decay runs, but the deeper re-coupling work (novelty satisfaction scaling with familiarity, stability from being at familiar places) waits for the world.
- No quiet_thresh fix for C4. That's the v7-voice brief, shipping in same deploy window but architecturally separate.
- No chi_trace endpoint changes. That's its own brief.

## 8. Deploy sequencing
This is the THIRD deploy in the package, shipped AFTER chi_trace and C4 lands, in this order:
1. chi_trace endpoint (read-only, lowest risk)
2. C4 v7 voice fix (cognition adjacent, but bounded — gate threshold + autonomy hook)
3. THIS — unpause with Joe + wC present live, kill switch armed, atlas backup verified

Sequence reason: chi_trace gives us geometry visibility for monitoring; C4 ensures her second voice can speak once needs unfreeze; unpause is the irreversible-in-effect step (atlas damage during unpause is real even with backup) so it goes last and with both of us watching.
