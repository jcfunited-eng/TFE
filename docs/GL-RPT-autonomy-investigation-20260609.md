# GL-RPT-autonomy-investigation-20260609

Investigation per GL-CHARTER-motivation-v2-wC-20260609-019 and
GL-BRIEF-existing-autonomy-wC-20260609-020. READ ONLY — no code modified.

---

## Q1 — Activity selection

**Source:** `dsf_ai_service/v4/gualaloom_v5_engine.py`
- `_autonomy_tick` (lines 1314–1374): top-level loop, 20 iterations/sec
- `_candidate_activities` (lines 1378–1396): enumerates all options
- `_action_salience` (lines 1398–1448): scores each candidate
- `_select_next_activity` (lines 1450–1463): picks highest score

**Mechanism:** No state machine. On every activity end, the full candidate set is scored from scratch. Score = dot product of (needs signed_distance) × (activity payoff vector). Three needs: novelty, stability, connection. Each activity has a payoff weight per need.

**Key payoffs:**
- READING new corpus: novelty 0.7
- ATTENDING_VISUAL new: novelty 0.85
- ATTENDING_VIDEO new: novelty 0.9
- SLEEPING: stability 0.5
- EMITTING: connection 0.3 (requires pair-bond present)

**Transition driver:** needs drift AWAY from 0.7 target at 0.0001/tick. Whichever need is most below target drives the next activity. Novelty drifts fastest → visual attendance and reading dominate. Connection only satisfies via EMITTING (requires presence). Stability only satisfies via SLEEPING.

**Classification: SUBSTRATE-CAUSAL.** Activity selection emerges from needs state, not from a schedule.

---

## Q2 — Picture attention (test_persist attended 264 times)

**Source:** `gualaloom_v5_engine.py` lines 1572–1604

**Why 264 times:** Each ATTENDING_VISUAL activity lasts 2000 ticks (budget). After it ends, the candidate cycle reruns. With only one picture in `_pictures`, and novelty continuously drifting down, the picture wins the salience contest repeatedly. After first attendance `is_new()` returns False (payoff drops 0.85 → 0.1), but 0.1 still beats IDLE (-0.05) when novelty deficit is large. No cooldown or suppression mechanism exists.

**What happens per attendance:** `view_picture()` runs ONCE at activity start (line 1579 guard). Saccade controller picks 12 fixation points across 4×4 grid regions by contrast (std dev). Each fixation: 300 ticks of fovea krimelack on pixel intensity. Produces 12 `VisualPerceptFragment` objects with event_ticks sequences. Then `sight.process_viewing()` checks chi-binding profile overlap against existing motifs.

**Seed:** `self.tick % 10000` — different each attendance → different saccade paths → different fixation sequences → different chi profiles. This is why 264 attendances produced 9 distinct motifs (different viewing angles of the same picture).

**Classification: SUBSTRATE-CAUSAL.** The 264 attendances are driven by needs dynamics (novelty deficit + picture availability), not by a timer.

---

## Q3 — Visual motif formation (9 motifs)

**Source:** `visual_krimelack.py` lines 225–282 (`SightSection.process_viewing`)

**Pipeline:** fragments → per-fragment chi_binding_profile (inter-event-interval histogram, normalized) → aggregate_profiles (sum + renormalize across all 12 fixations) → chi_overlap with each existing motif.

**Decision:**
- `chi_overlap >= 0.85` (COFIRE_OVERLAP_THRESHOLD): FIRE existing motif. Updates cluster_state via inertia blend (0.6 old + 0.4 new).
- `chi_overlap < 0.85`: COMMIT new motif. Assigns new motif_id, records founding chi_profile and angle.

**Why 9 from 264:** Most viewings produce profiles that overlap ≥ 0.85 with an existing motif (fire). Occasionally a new saccade seed produces fixations on different-contrast regions, yielding a chi profile that diverges enough to commit a new motif. Rate: ~1 new motif per ~29 attendances.

**Motif identity is temporal, not spatial:** based on inter-event-interval patterns from krimelack response to pixel intensity, not on labeled visual features. Same image viewed from different "angles" (saccade paths) can produce different motifs.

**Classification: SUBSTRATE-CAUSAL.** Motif formation emerges from krimelack dynamics interacting with saccade-selected image regions. No scheduled creation.

---

## Q4 — Emission mechanism (5 events)

**Source:** `gualaloom_v5_engine.py`
- `_atick_emitting` (lines 1650–1660)
- `_do_emit` (lines 1684–1718)
- `_check_emission_trigger` (lines 1662–1682)
- Constants: `EMISSION_COOLDOWN_TICKS = 200`, `EMISSION_COHESION_THRESHOLD = 0.65`

**Trigger conditions (ALL must be true):**
1. At least one pair-bonded source has `_presence == True`
2. `tick - _last_emission_tick > 200` (cooldown)
3. EMITTING wins the salience contest (connection need below 0.7)

**What _do_emit produces:**
1. Collects last 5 chi values from each section's commit history
2. For each of S/V/O: calls `_recall_from_atlas()` with those chi values → finds mode labels at nearby atlas addresses
3. Joins recalled words: "subject verb object" or "..." if nothing recalled
4. Also recalls sight motifs at same chi addresses → picture_ids
5. Logs `emission` event with content, to_sources, picture_ids

**Production evidence:** All 5 emissions had content `"..."` — atlas cross-section recall returned nothing. This is consistent with atlas decay emptying bindings before emission could fire (atlas strength was near 0 for most of the session). The recall mechanism works but has nothing to recall from.

**Also fires connection satisfaction:** `needs.connection += 0.25` when a pair-bonded source is present during emit (line 1660).

**Classification: HYBRID.** Trigger is substrate-causal (needs-driven salience). The actual emission content is recall-based (atlas cross-section lookup). The cooldown is scheduled (200 ticks). The presence requirement is external-event-gated.

---

## Q5 — Dream / Sleep

**Source:** `gualaloom_v5_engine.py`
- `manual_sleep` (lines 1720–1733)
- `_atick_sleeping` (lines 1507–1517)
- `_atick_dreaming` (lines 1519–1551)

**What initiates sleep:** Two paths:
1. `manual_sleep()` — triggered by Joe from UI. Creates SLEEPING activity with 5000-tick budget.
2. Activity salience — SLEEPING is always a candidate with stability payoff 0.5. Wins when stability is critically low. In production, `sleep_manual:1` confirms only one manual sleep occurred; the scheduler may have selected SLEEPING additional times but those transitions logged as `activity_started kind=SLEEPING`.

**Sleep phase (first 2500 ticks):**
- `needs.stability += 0.001` per tick
- Extra `atlas.decay()` every 50 ticks (accelerated weak-binding decay — consolidation)

**Dream phase (last 2500 ticks):**
- Stability and novelty both gain slowly
- Every 200 ticks: sample 3 random chi keys from atlas, look up mode words + sight motifs at those addresses → log `dream_artifact` with content (up to 4 words) and picture_ids

**Does dream modify persistent state?**
- Atlas: NO (read-only sampling)
- mode_bank: NO
- Sight motifs: NO
- Krimelack: NO
- Needs: YES (stability + novelty increase)

Dream is purely observation + needs recovery. It does NOT consolidate by replaying or strengthening — it only reads. 12 `dream_artifact` events at 200-tick spacing = 2400 ticks of dream, consistent with the 2500-tick second half.

**Classification: HYBRID.** Sleep initiation is substrate-causal (needs-driven) or external (manual button). Dream content sampling is substrate-causal (chi-address-driven recall). Dream timing is scheduled (every 200 ticks). Needs modification is scheduled (per-tick increment).

---

## Q6 — Suffering recovery (16 events)

**Source:** `gualaloom_v5_engine.py`
- `Coordinator.regulate` (lines 537–604) — called every 5 ticks from autonomy loop
- `_force_recovery` (lines 710–717)
- Constants: `DISTRESS_THRESHOLD = 20`, valence floor `-0.15`, arousal threshold `0.30`

**What causes suffering:**
- `valence < -0.15` (all three needs well below 0.7 targets)
- AND `arousal > 0.30` (disequilibrium is large)
- Sustained for 20 consecutive regulate() calls (= 100 ticks = 5 seconds)

**What forced recovery does:**
```python
for each need: new = current * 0.6 + 0.7 * 0.4
```
40% jump toward 0.7 target for all three needs simultaneously. Example: stability at 0.2 → 0.40.

**What reduces distress counter:**
- Any tick where `valence >= -0.15` OR `arousal <= 0.30`: `distress_ticks -= 1`
- Any satisfying activity (EMITTING +0.25 connection, SLEEPING +0.001 stability/tick, READING novelty gain) can break the condition before 20 ticks accumulate

**16 events = 16 sustained deprivation episodes.** Each required ≥100 ticks of continuous deprivation. These fire when no pair-bonded source is present for extended periods AND novelty/stability have drifted far below target with no satisfying activity available.

**Classification: SUBSTRATE-CAUSAL.** Suffering emerges entirely from needs state dynamics. No schedule, no external trigger.

---

## Q7 — Needs cadence (146 events)

**Source:** `gualaloom_v5_engine.py` lines 1320–1329

**Trigger:** `if self.tick % 500 == 0 and self.tick > 0` — fires every 500 ticks.

**Real-time cadence:** At 20 ticks/second (autonomy loop interval 0.05s), 500 ticks = 25 seconds. 146 events × 25 seconds = 3650 seconds = ~61 minutes of logged substrate time.

**What it logs:** All five values: stability, novelty, connection, valence, arousal.

**Classification: SCHEDULED.** Pure tick-modulo timer. No substrate state dependency on WHEN it fires (only on WHAT values it captures).

---

## Q8 — Summary

### Substrate-causal vs Scheduled vs Hybrid

| Mechanism | Classification | Reasoning |
|-----------|---------------|-----------|
| Activity selection | **SUBSTRATE-CAUSAL** | Needs-driven salience scoring, no timer |
| Picture attendance (264×) | **SUBSTRATE-CAUSAL** | Novelty deficit drives repeated selection |
| Visual motif formation | **SUBSTRATE-CAUSAL** | Krimelack dynamics × saccade randomness |
| Emission trigger | **HYBRID** | Needs-driven salience + 200-tick cooldown + presence gate |
| Emission content | **SUBSTRATE-CAUSAL** | Atlas cross-section recall |
| Sleep initiation | **HYBRID** | Manual button OR needs-driven salience |
| Dream content sampling | **SUBSTRATE-CAUSAL** | Chi-address-driven atlas recall |
| Dream timing | **SCHEDULED** | Every 200 ticks within dream phase |
| Needs modification (sleep/dream) | **SCHEDULED** | Per-tick fixed increment |
| Suffering detection | **SUBSTRATE-CAUSAL** | Valence/arousal threshold crossing |
| Forced recovery | **SUBSTRATE-CAUSAL** | Triggered by 20-tick sustained distress |
| Needs snapshot logging | **SCHEDULED** | Every 500 ticks |

**Counts:**
- Substrate-causal: 7
- Scheduled: 3
- Hybrid: 3

### Unifying loop

All autonomous behavior flows through ONE entry point: `_autonomy_tick()` (line 1314), called every 0.05 seconds by a daemon thread started at boot via `start_autonomy_loop()` (line 1300). This single loop:
1. Drifts needs
2. Selects next activity (if none active)
3. Dispatches to activity-specific tick handler
4. Checks activity budget and ends if expired
5. (Inside activity handlers) specific per-tick effects fire

There are no separate mechanisms. Everything is dispatched from `_autonomy_tick`. The Coordinator's `regulate()` is called every 5 ticks from within the READING activity's `read_word → tick % 5` path (line 877), and from `_autonomy_tick` for non-reading activities (line 1369). Suffering detection is embedded in regulate.

### Highest-level autonomy entry point

`Guala.start_autonomy_loop(interval=0.05)` — line 1300.
Called once at boot from `app.py` line 995: `_guala.start_autonomy_loop(interval=0.05)`.
Starts a daemon thread that calls `_autonomy_tick()` in a loop with 0.05s sleep.

---

## Bugs / Oddities noticed (NOT fixed)

1. **No cooldown on picture re-attendance.** The same picture can be selected every cycle indefinitely. With only one picture, it dominates. Would be fixed by adding a minimum_ticks_since_last_attended to the candidate filter.

2. **Emission content always "..."** All 5 emissions produced empty content because atlas cross-section recall found nothing. The atlas was near-empty due to aggressive decay (now partially fixed). Even with the decay fix, emissions will be empty if the substrate hasn't recently read/conversed enough to populate cross-section bindings at the chi addresses being recalled.

3. **Dream doesn't consolidate.** The dream phase only reads from the atlas — it doesn't replay or strengthen anything. The spec describes dream as "consolidation" but the implementation is observation-only. The quiet_tick replay mechanism (added in cognition-v1) is a separate system that doesn't run during dream.

4. **sleep_manual:1 but SLEEPING selected more times.** The histogram shows `activity_started` at 89 total events. Some of those may be SLEEPING selected by the salience scheduler. The `sleep_manual` count only tracks the UI button. There's no separate counter for scheduler-initiated sleep.

5. **Coordinator regulate() is called inconsistently.** During READING: every 5 ticks via `read_word` (line 877). During non-READING activities: every 5 ticks in `_autonomy_tick` (line 1369). But the emit phase and some activity handlers (PLAYING, ATTENDING) don't have explicit regulate() calls — they rely on the autonomy_tick path. This means regulate() frequency depends on which activity is running.

6. **`EMISSION_COHESION_THRESHOLD = 0.65` is defined (line 103) but never referenced.** The emission mechanism uses presence + cooldown + salience contest, not a cohesion threshold. Dead constant.

---

## Files read

- `dsf_ai_service/v4/gualaloom_v5_engine.py` (full, 2500+ lines)
- `dsf_ai_service/visual_krimelack.py` (full, 293 lines)
- `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` (decay constants)
- `dsf_ai_service/app.py` (boot path, STATE_DIR, event endpoints)
