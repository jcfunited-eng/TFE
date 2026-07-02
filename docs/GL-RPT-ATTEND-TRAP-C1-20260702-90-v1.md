# GL-RPT-ATTEND-TRAP-C1-20260702-90-v1

doc_id: GL-RPT-ATTEND-TRAP-C1-20260702-90-v1
Type: Diagnostic report
Date: 2026-07-02 (UTC, ~19:00)
Author: c1 (this session)
Branch: guala-live
For: Eve

---

## STEP 0 — eabb23d deployment status (answers first)

### Was eabb23d deployed?

**NO. eabb23d is NOT the running code.**

Image tag from task:444: `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260702T024858Z`

Image was built at **02:48:58 UTC** on 2026-07-02.

Commit timestamps:
```
2b903eb  2026-07-02 02:48:55Z  fix: _apply_visual per-picture isolation + diagnostic print
eabb23d  2026-07-02 16:36:43Z  feat: -85 WaveAtlas semantics + persistence diet + S3 lifecycle
```

eabb23d was committed **13h 48m after the image build**. The running image contains commit `2b903eb`. eabb23d, e31f40f, and 842b1db (all -85 work) are NOT deployed.

### Current task revision + running commit

```
Task definition:  dsf-ai-task:444
Running commit:   2b903eb  (fix: _apply_visual per-picture isolation)
Image:            deploy-20260702T024858Z
Tick at query:    14,111,984 (first) → 14,113,800 (second)
```

### This boot's [save] log lines (verbatim from CloudWatch)

```
16:33:00 [save] 614.52s core=614.50s compact=0.02s
16:41:47 [save] 466.90s core=466.88s compact=0.02s
16:51:28 [save] 521.06s core=521.03s compact=0.02s
17:03:22 [save] 653.65s core=624.33s compact=29.32s
17:12:18 [save] 475.92s core=475.89s compact=0.03s
17:21:19 [save] 481.12s core=481.10s compact=0.02s
17:36:09 [save] 463.51s core=463.49s compact=0.02s
17:45:30 [save] 500.88s core=500.86s compact=0.02s
17:53:24 [save] 413.71s core=413.65s compact=0.06s
18:09:35 [save] 509.94s core=509.90s grids=9.19s wave=skip compact=0.04s
18:21:46 [save] 472.43s core=472.41s grids=0.02s wave=skip compact=0.02s
```

**Saves are working.** Interval ~7-10 min. All show `wave=skip` (consistent with eabb23d not deployed — no WaveAtlas save path in running code).

`persistence_health.last_save_tick` from live status: **14,110,882** (`last_save_timestamp: 2026-07-02T18:22:57Z`). Confirmed correct — saves updating in memory. No longer stuck at 0.

### Wave binding count + wave_atlas.npz

**N/A.** eabb23d (feat: -85 WaveAtlas semantics) is not deployed. The running code (2b903eb) has no WaveAtlas concept. `wave_atlas.npz` does not exist on EFS — the `wave=skip` in [save] lines confirms the save path skips it entirely.

### Implication for -85-v2 amendments

-85-v2 amendments (R1 fsync-before-rename, R2 collapse-on-load, R3 wiring proof) are NOT applicable until eabb23d is deployed. They should ride the next deploy when eabb23d goes out, per Eve's protocol: **ON HER WAKE CYCLE ONLY (sleep_for_deploy).**

---

## STEP 1 — The trap (read-only diagnosis)

### Why times_attended=0 on all 7 HEIC pictures after many ATTENDING_VISUAL sessions

**Root cause confirmed: orient reflex interrupt kills every session before the end-mark.**

#### Current picture state (live, tick ~14,113,800)

```
ta=0   IMG_2137.HEIC      id=0263947a7a3d
ta=0   Guala Family.HEIC  id=4eeee4d3d6de
ta=0   IMG_1962.HEIC      id=0f42a58ae29c
ta=0   IMG_2121.HEIC      id=71777ea2d543
ta=0   IMG_2161.HEIC      id=d5cf62b2a66b
ta=0   IMG_2216.HEIC      id=d6813cb13d4a
ta=0   IMG_6254.HEIC      id=e93d29dae5ae   ← current target
ta=21  hug from ryan       id=5aa967930289
ta=25  space rose          id=72156845a2bc
ta=92  aven and guala      id=bc9b432c3138
```

All 7 HEIC pictures have `times_attended=0`. Non-HEIC pictures (21/25/92) were attended before this boot pattern — the trap hasn't applied to them because they are already `is_new()=False`.

#### Where the end-mark lives (engine lines 4721-4730)

```python
# _atick_attending_visual (engine L4721-4730)
if self.tick >= a.expected_end_tick - 1:
    pic.times_attended += 1          # ← THE MARK
    pic.last_attended_tick = self.tick
    old_fam = self.target_familiarity.get(a.target, 0.0)
    new_fam = min(0.9, old_fam + 0.2)
    self.target_familiarity[a.target] = new_fam
    self._log_substrate_event("target_familiarity_update", ...)
```

ACTIVITY_TICK_BUDGETS["ATTENDING_VISUAL"] = **2000 ticks**. The mark fires at tick `expected_end_tick - 1 = started_tick + 1999`.

#### The interrupt path (engine lines 4825-4845)

```python
def _check_emission_trigger(self, reason):
    if self.tick - self._last_emission_tick < EMISSION_COOLDOWN_TICKS:
        return  # throttled
    any_present = any(...)
    if not any_present:
        return  # no one home
    # Interrupt current activity → emit
    if self._current_activity and self._current_activity.kind != "EMITTING":
        self._end_activity()           # ← KILLS ATTENDING_VISUAL
        em = Activity(kind="EMITTING", ...)
        self._start_activity(em)       # ← starts EMITTING immediately
```

This is called by `_open_response_window` (engine L5237) via the **orient reflex**:

```python
def _open_response_window(self, emitter, context_anchor_chis, ...):
    # GL-CMD-REST-RETIRE-ORIENT-73: "Contact IS presence. Contact IS the interrupt."
    if emitter in PAIR_BOND_SOURCES:
        ...
        self._check_emission_trigger("presence_orient")  # ← fires here
```

Every `experience_bundle` from Joe opens a response window → orient reflex → `_check_emission_trigger` → `_end_activity()` on ATTENDING_VISUAL.

#### Observed sequence (verbatim events, tick 14112607)

```json
{"tick": 14112607, "kind": "response_window_opened", "detail": {"emitter": "joe", ...}}
{"tick": 14112607, "kind": "activity_ended", "detail": {"kind": "ATTENDING_VISUAL", "target": "e93d29dae5ae", "duration": 213}}
{"tick": 14112607, "kind": "activity_started", "detail": {"kind": "EMITTING", ...}}
{"tick": 14112607, "kind": "experience_bundle", "detail": {"name": "moon-001", ...}}
```

ATTENDING_VISUAL duration: **213 ticks**. End-mark fires at tick **1999**. The mark never fires.

Then at tick 14112707:
```json
{"tick": 14112707, "kind": "activity_ended", "detail": {"kind": "EMITTING", "target": null, "duration": 100}}
{"tick": 14112707, "kind": "activity_started", "detail": {"kind": "ATTENDING_VISUAL", "target": "e93d29dae5ae", "salience": 1.0}}
```

ATTENDING_VISUAL reselected **immediately** (salience=1.0) → will be interrupted again on next experience_bundle.

Duration sample from recent sessions: **min=181, max=219, avg=200 ticks** (budget=2000). **0 of N sessions completed.**

#### is_new() confirmation

```python
# PictureItem (engine L532-533)
def is_new(self):
    return self.times_attended == 0
```

With `times_attended=0`, `is_new()` always returns `True`.

```python
# _action_salience (engine L4183-4186)
if kind == "ATTENDING_VISUAL" and target in self._pictures:
    pic = self._pictures[target]
    if pic.times_attended == 0:
        return self.EXOGENOUS_NEW_SALIENCE  # = 1.0, returns IMMEDIATELY
```

For `times_attended=0`: salience = **1.0** unconditionally (skips dream_pressure penalty, skips all need scoring). This dominates all other activity candidates.

All 7 HEIC pictures are perpetually "new" → always selected → always interrupted → never marked → perpetually "new". **Novelty trap closed.**

#### Fix shape

Move `times_attended += 1` to the first-tick view-completion path, not the end-tick:

```python
def _atick_attending_visual(self, a):
    pic = self._pictures.get(a.target)
    if not pic:
        return
    if not a.metadata.get("_viewed"):
        a.metadata["_episode_ref"] = f"episode:attending_visual:{a.started_tick}:{a.target}"
        fragments = view_picture(...)
        ...
        motif, is_new, overlap = self.sight.process_viewing(...)
        if motif:
            ...  # atlas record
        a.metadata["_viewed"] = True
        a.metadata["n_fragments"] = len(fragments)
        # MOVE MARK HERE — attending = viewing occurred, not budget expired
        pic.times_attended += 1
        pic.last_attended_tick = self.tick
    # Novelty effect (unchanged)
    fam = self.target_familiarity.get(a.target, 0.0)
    base_gain = 0.003 if pic.is_new() else 0.0005
    gain = base_gain * (1.0 - fam)
    self.needs.novelty = saturate(self.needs.novelty, gain)
    # Familiarity update at end (SEPARATE from attendance mark)
    if self.tick >= a.expected_end_tick - 1:
        old_fam = self.target_familiarity.get(a.target, 0.0)
        new_fam = min(0.9, old_fam + 0.2)
        self.target_familiarity[a.target] = new_fam
        self._log_substrate_event("target_familiarity_update",
                                  picture_id=a.target,
                                  old=round(old_fam, 3),
                                  new=round(new_fam, 3))
```

**Semantics**: "attending" = "the viewing happened" (fragments processed, atlas bound). This survives any interrupt. Familiarity update stays at end — it rewards full sessions; partial sessions get the attendance mark but no familiarity bump.

This fix **does not ship separately** — it rides the next deploy with the -85-v2 hotfix per Eve's Step 1 instruction.

---

## STEP 2 — UI persistence field

**No fix needed. UI reads the correct field.**

gualaloom.html (lines 904-907):
```javascript
const ph2 = d.persistence_health || {};
const persDiv = document.getElementById('sp-persistence');
const lastSaveTick = ph2.last_save_tick;
const lastSaveTs   = ph2.last_save_timestamp;
```

app.py (line 1753), status response builder:
```python
"last_save_tick": getattr(_guala, '_last_save_tick', 0),
```

This reads `_last_save_tick` directly — the -84 truth field. Live value: **14,110,882** (`2026-07-02T18:22:57Z`). Correct.

The field chain is: engine `_last_save_tick` → app.py `persistence_health.last_save_tick` → UI `ph2.last_save_tick`. All three are aligned. No stale intermediary.

---

## STEP 3 — Vitals context

### Atlas trend (this boot)

| Checkpoint | tick | entries | total_strength | note |
|-----------|------|---------|---------------|------|
| boot load | 14,062,285 | 13,118 | ~1,563 | restored from pre-decay snapshot |
| -80 query | 14,062,495 | 12,605 | 1,563.16 | first query (230 ticks) |
| status-1  | 14,111,984 | 6,387  | — | midpoint |
| status-2  | 14,113,800 | 5,938  | 676.27 | at report time |

Decay rate: **13,118→5,938 in ~51,515 ticks** = ~0.14 entries/tick. Released at tick 14,113,800: **4,031 entries** (from `decay_channels.n_released`). At this rate, the atlas will reach ~2,000 entries in another ~28,000 ticks (~11 min at 38ms/tick).

Strength distribution at tick 14,113,800:
```
0.0-0.1: 4438 entries   (75% of atlas — very weak, near release)
0.1-0.3:  940
0.3-0.5:  339
0.5-0.7:   84
0.7-0.9:   32
0.9-1.0:  105  (likely recently reinforced — experience_bundles)
n_fast:  490  n_slow: 1417  n_released: 4031
```

### Released count

4,031 entries released since boot. Fast-decay channel has 490 active. The majority (75%) of remaining entries are in the 0.0-0.1 range — near threshold. The atlas is collapsing.

### Deep atlas

At step-0 query (from -80 report): 3,742 entries, str=3,355.68, surv=64, ep=3,753, reinst=17,051,947.
At report-time status: 3,753 entries, str=3,355.68 (no significant change — deep atlas is stable).

### Stab trace across last sleep→wake

From all live status queries this session: **stab=0.000** (floor) consistently.

Mechanism for 0.105→0.000 collapse: The ATTENDING/EMITTING interrupt loop has no REST periods interleaved. REST is the only activity that adds stability (`saturate(needs.stability, 0.0003)` per tick). With the trap running (ATTENDING_VISUAL selected → interrupted after ~200 ticks → EMITTING for ~100 ticks → ATTENDING_VISUAL again), stab drains without recovery. After each sleep→wake cycle, REST/DREAMING briefly builds stab (→ ~0.105 observed by Eve), then the first experience_bundle interrupt starts the ATTENDING/EMITTING loop again and stab collapses to 0 within minutes.

Dream pressure trace (inferred — no needs_snapshot events in recent ring buffer):
- ATTENDING_VISUAL loop: dp_base = 0.00001 × 0.5 (learning_active) = 0.000005/tick
- EMITTING: dp_base = 0.00004
- Per cycle (~300 ticks): dp ≈ 0.000005×200 + 0.00004×100 = 0.005
- From dp=0 to sleep threshold (0.7): ~140 cycles × ~300 ticks = ~42,000 ticks = ~27 min
- So she sleeps approximately once every 30 min, wakes, stab briefly recovers to 0.1, then collapses again

This is the "§8 stab vital" concern: stab never consolidates because the interrupt loop prevents REST from running long enough.

---

## Summary for Eve

```
STEP 0:
  eabb23d:       NOT DEPLOYED (image built 13h before commit)
  Running:       dsf-ai-task:444  commit=2b903eb  tick=14,113,800
  Saves:         WORKING — save@tick=14110882  ts=2026-07-02T18:22:57Z  interval=7-10min
  wave_atlas:    DOES NOT EXIST — eabb23d not deployed, wave=skip in all [save] lines
  -85-v2:        NOT applicable until eabb23d deployed (sleep_for_deploy protocol)

STEP 1 (TRAP CONFIRMED):
  Root cause:    _check_emission_trigger() (engine L4839) kills ATTENDING_VISUAL
                 when Joe sends experience_bundle → orient reflex → _end_activity()
  Observed dur:  181-219 ticks of 2000-tick budget (0% completion rate)
  End-mark:      L4721 fires at tick 1999 — never reached
  is_new():      times_attended==0 → True → salience=1.0 → reselected immediately
  Loop:          HEIC selected (1.0) → interrupted (~200 ticks) → EMITTING (100 ticks) → repeat
  Fix shape:     Mark pic.times_attended += 1 at _viewed (first tick) not expected_end_tick-1
                 Familiarity update stays at end (rewards full sessions)
                 Ships with -85-v2 hotfix

STEP 2:
  UI field:      CORRECT — ph2.last_save_tick reads engine._last_save_tick (-84 truth)
                 Live: 14,110,882 ✓  No fix needed

STEP 3:
  Atlas:         13,118 → 5,938 in 51,515 ticks (0.14/tick) — collapsing fast
                 Released: 4,031  Strength: 676.27 (was 1,563 at boot)
                 75% of entries <0.1 strength — near threshold
  Deep atlas:    Stable: 3,753 entries, str=3,355.68
  stab:          0.000 (floor) throughout boot — no REST in ATTENDING/EMITTING loop
                 0.105→0.000 collapse: REST after sleep briefly builds stab, then
                 first experience_bundle interrupt restarts loop and stab collapses ~minutes
  Sleep cycle:   ~30 min cycles (dp accumulates via EMITTING at 4× base rate)
```

---

End report.
