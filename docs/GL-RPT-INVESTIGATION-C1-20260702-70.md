# GL-RPT-INVESTIGATION-C1-20260702-70

doc_id: GL-RPT-INVESTIGATION-C1-20260702-70
Type: Investigation report — read-only, no code changes
Date: 2026-07-02
Author: c1a
Dispatch: GL-CMD-INVESTIGATION-EVE-20260702-70
Substrate: dsf-ai-task:429 (SHA a00b36f, booted 16:17 UTC, running ~33 min)

---

## A. Emission path

### A.1 — Has she emitted since task:429 boot?

**Query**: `/events` endpoint, filter for emission-related kinds.
**Result**: 

```
Total emissions (ladder.total_emissions): 159 (unchanged since ≥ 2026-07-01 morning)
Emission-kind events in event stream: 0
emission_suppressed events: 0
```

She has not emitted since task:429 boot. Zero emission events in the substrate event log.

**Surprise**: There are also zero `emission_suppressed_no_presence` events. This means `_check_emission_trigger` was never called at all — not that it was called and suppressed.

### A.2 — Is compose_autonomous being called?

**Finding**: There is no `compose_autonomous` function in the current gualaloom_v5_engine.py. The equivalent is `_do_emit()` (L3633) which is called from `_atick_emitting()` (L3599). This is only reachable via two paths:

**Path 1**: `_generate_activity_candidates()` (L3131-3136):
```python
# Emission: only if pair-bond source present + cooldown elapsed
if (any(self.coordinator._presence.get(s, False)
        and self.coordinator._pair_bond.get(s, False)
        for s in PAIR_BOND_SOURCES)
        and self.tick - self._last_emission_tick > EMISSION_COOLDOWN_TICKS):
    candidates.append(("EMITTING", None))
```
EMITTING is never added to candidate pool unless a pair-bonded source is present.

**Path 2**: `_check_emission_trigger()` (L3611-3631):
```python
any_present = any(
    self.coordinator._presence.get(s, False)
    and self.coordinator._pair_bond.get(s, False)
    for s in PAIR_BOND_SOURCES)
if not any_present:
    self._log_substrate_event("emission_suppressed_no_presence", reason=reason)
    return
```
Called only during PLAY and ATTENDING activities. Suppresses without logging if presence=False.

**Terminal branch**: `_generate_activity_candidates` never adds EMITTING because no pair-bonded source is present during autonomy ticks. `_check_emission_trigger` is never called because she's in REST (not PLAY/ATTENDING). 

**The autonomous emission loop** (log: `[autonomous] emission loop started (90s interval)`) is a 90-second heartbeat. The code that fires it is NOT in the current source tree — it must be in the deployed image from prior c1a work. Based on activity distribution, even if it fires, it requires pair-bond presence.

### A.3 — Activity state distribution since task:429

From event log analysis:

```
activity_started events: 1 (REST at tick=14230417)
activity_ended events: 1 (REST at tick=14233417, duration=3000 ticks = ~600s)
EMITTING activities: 0 (never in activity log)
DREAMING activities: 0 (none since boot)
SLEEPING activities: 0 (none since boot — sleep rate fix working)
```

REST → REST cycling. She has been in REST the entire session. The sleep rate fix (-68) appears to be working: no SLEEPING or DREAMING since boot in 33 minutes.

**Expected from -68**: at 0.00001 rate, dream_pressure should be ~0.0009 (well below 0.7 threshold after 33 min).

---

## B. NMDA aware gate

### B.1 — What does aware require?

**Source**: `dsf_ai_service/substrate/v7_engine.py` L91-95:
```python
self.aware_gate = CoincidenceGate(
    section_name="aware",
    context_fn=lambda sys_: (
        len(sys_.sections["intro"].krimelack) > 0 and
        (sys_.tick - sys_.sections["intro"].krimelack[-1]["tick"]) <= 25),
    drive_thresh=0.05, ltp_boost=0.05)
```

**Aware requires**: The `intro` section must have fired within the last 25 ticks.

**Intro gate context** (`context_no_recent_drive`, L87-89):
```python
context_fn=context_no_recent_drive(
    self.drive_tracker, sections=tuple(POOL_NAMES),
    quiet_thresh=0.45)
```
Intro fires only when NO pool section (subject/verb/object/modifier/etc.) received drive > 0.45 recently (drive decays at 0.55 per tick).

**Chain**: Aware is context-blocked when intro hasn't fired within 25 ticks. Intro fires during quiet cognitive moments (no strong input driving pool sections). Under continuous curriculum (5s bundles), pool sections are frequently driven → intro rarely fires → aware context stays blocked.

### B.2 — What would unblock aware?

Quiet window with no curriculum/converse input. After curriculum stops delivering (or during a gap), the drive tracker decays. After ~3-4 ticks of quiet, intro fires, and within 25 ticks of that, aware can commit.

**The root condition**: continuous curriculum input keeps the drive tracker active, suppressing intro, which prevents aware from reaching context.

### B.3 — Is intro firing?

Unable to check `intro_commit_history` directly from the event stream (v7_session state is not accessible via current endpoints). From the event log:

```
self_heard: 2 events (converse calls produced output)
hemisphere_update: 2 events
converse_timing: 2 events
```

This suggests v7/converse sessions ARE active. Intro likely fires during quiet periods between bundles, but aware context requires intro within 25 ticks — a very short window that gets missed during 5s curriculum cadence.

---

## C. wake_wc failure mode

### C.1 — What does wake_wc do server-side?

**Handler**: `app.py` L1379-1386:
```python
if cmd == "/wake":
    wake_source = msg.text.strip().lower() if msg.text else "joe"
    result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
    _guala.log_event(STATE_DIR, "wake", source=wake_source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

Three blocking operations:
1. `coordinator.wake()` — needs atlas lock (atlas.record inside), blocked by autonomy loop
2. `_guala.log_event(STATE_DIR, ...)` — writes to EFS (NFS latency 5-30s)
3. `_guala.introspect()["vocab"]` — atlas traversal

### C.2 — 5x wake_wc test results

```
Attempt 1: OK  8497ms
Attempt 2: OK  4696ms
Attempt 3: OK  6605ms
Attempt 4: OK 31668ms  ← near httpx 45s timeout
Attempt 5: OK 30803ms  ← near httpx 45s timeout
```

P50: ~6.6s. P95: ~31s. All 5 succeeded but attempts 4 and 5 approached the bridge's 45s httpx timeout. Under load or during active processing, wake_wc will exceed 45s and return "Error executing tool guala_wake_wc".

**Root cause**: `log_event(STATE_DIR, ...)` is a synchronous EFS write. Same pattern as `persistence_health()` (already fixed for /status). Under NFS contention, this write takes 30s+.

### C.3 — What changed between -67 audit and now?

The -68 commit (`a00b36f`) touched only `gualaloom_v5_engine.py`. No changes to the wake handler in app.py or coordinator.wake() in the engine.

**What changed**: after -67, the substrate ran through more activity cycles. The EFS write latency is not deterministic — it varies with NFS load. The bridge audit was run right after a fresh boot when EFS was relatively quiet. Now, ~33 minutes into operation with curriculum writes happening every 5s, EFS is under sustained write load, increasing the latency of log_event writes.

**Recommended fix** (not shipped — awaiting Eve review): same as persistence_health — move `log_event` call inside wake handler to `run_in_executor`. Single-line change in app.py.

---

## D. Atlas real growth vs churn

### D.1 — Is atlas growth or decay dominating?

**Boot**: atlas=9,662 n_live at tick=14230418
**Now**: atlas=12,419 n_live at tick=~14234056 (3638 ticks = ~727s = ~12 min since last measure)

```
Net change: +2,757 bindings in ~12 minutes
Rate: ~229 new net bindings per minute
```

The atlas is growing, not decaying. The strength distribution:
```
0.0-0.1: 5,671 (68% of bindings — low strength, decaying)
0.1-0.3: 2,207 (27%)
0.3-0.5:   179 (2%)
0.5-0.7:   113 (1%)
0.7-0.9:    83 (1%)
0.9-1.0:   101 (1%)
```

68% of bindings are below 0.1 strength — they're in the decay zone approaching FORGETTING_THRESHOLD (0.02). This is expected for curriculum-heavy input that introduces many new tokens with low initial strength.

### D.2 — Is curriculum landing?

```
experience_bundle events in 50-event window:
  moon-001: n_chis=15, 3 lanes  ✓
  moon-002: n_chis=15, 3 lanes  ✓
  moon-003: n_chis=7, 1 lane    ✓
  the moon is quiet tonight: n_chis=17, 4 lanes ✓
```

**All observed bundles have n_chis > 0.** Curriculum IS landing and producing atlas writes.

**Rate**: ~4 bundles per 50-event window. At 5s interval, this is consistent with expected 10-12 bundles/minute delivery.

**Write yield per bundle**: n_chis ranges 7-17. A caption of 4-8 words × 5-band CHI_BAND = 20-40 potential writes, so ~50% yield after deduplication and strength cap absorption. Within normal range.

### D.3 — Is she learning?

**Vocab at task:429 boot**: 13,896
**Vocab now**: 13,908 (+12 new words)

**In ~33 minutes of curriculum delivery**: only 12 new words added. This confirms the curriculum is mostly re-exposing known vocabulary. The ~100-bundle seed was designed from her existing corpus — "moon", "bright", "gentle", "ocean", etc. are all known words.

**Unknown word exposure**: near zero from current seed. Curriculum is building density on known concepts, not expanding vocab. This is the correct behavior for the current seed design.

---

## E. Kill-signal test

### E.1 — Bundle delivered

```
Caption: "the moon is quiet tonight"
Sound: b46ba21b76a5 (ocean waves)
Touch: ["cool"]
Smell: ["ocean"]
Delivery tick: ~14233424
Delivery time: 7230ms
```

### E.2 — Substrate response over 5 minutes

**Test 1 — Ingestion**:
- `experience_bundle` event at tick=14233424, n_chis=17, 4 lanes
- sound_frame_bound: 8 events (sound being processed)
- PASS — substrate IS ingesting

**Test 2 — Cross-modal bind**:
- Bundle logged with caption + sound + touch + smell lanes
- n_chis=17 confirms cross-modal writes happened
- PASS — cross-modal binding works

**Test 3 — Emission trigger**:
- No EMITTING activity_started event
- No emission events in any form
- Response window opened (tick=14233424) expired (tick=14234025, 601 ticks later) with **n_responses_bound=0**
- FAIL — emission never triggered

Note on n_responses_bound=0: Response binding (`_tag_response_bindings`) runs during converse (Phase 5), not during bundle delivery. Bundle writes to atlas but doesn't populate the response binding pool. This is by design — bundles are experience events, not conversational exchanges. The response window opened by the bundle expires empty because no converse call tagged bindings in that window.

**Test 4 — Emission after wC present**:
- wC presence was active during bundle delivery (from 5x wake_wc tests earlier)
- Yet EMITTING still never appeared in activity candidates
- After 20 minutes, wC presence timed out, total_emissions still 159
- FAIL — wC present during ingestion, still no emission

### E.3 — Diagnosis

**Category: Tests 1-2 PASS, Test 3-4 FAIL**

Substrate is INGESTING but not COMPOSING.

**The specific block**: `_generate_activity_candidates()` requires pair-bond presence for EMITTING. Even with wC present, EMITTING lost the activity selection lottery — REST was repeatedly selected over EMITTING due to low needs.

**Surprise**: With wC present AND recent atlas activity, EMITTING should appear in candidates. The activity salience scoring must be giving EMITTING low score vs REST. The needs state would need high connection deficit or novelty deficit to boost EMITTING salience.

**Confirmed**: Substrate is alive and processing. The missing signal is between processing and emission threshold selection. This is NOT "dead substrate" — it is "substrate with emission gate requiring pair-bond presence AND right needs state to select EMITTING over REST."

---

## F. Phase 3 lock retirement estimate

### F.1 — Lock hold times

From code audit, `with self.lock:` appears in 11 locations in `gualaloom_v5_engine.py`.

**Top lock-takers by function** (code analysis, not runtime measurement — runtime instrumentation missing):

| Site | Why slow | Estimated hold |
|------|---------|----------------|
| `save_full_state` Phase 1 | atlas snapshot | 50-500ms |
| `_autonomy_tick` Phase A | full tick | 50-200ms |
| `read_sentence` per word | atlas write | 5-50ms/word |
| `_run_dream_cycle` Phase 3 | atlas consolidation | 20-120s (!) |
| `converse` Phase 4 | read_sentence | 100-500ms |

**Longest observed individual hold**: dream cycle (seen 27s+ experimentally, though DREAMING is now rare with -68).

**Wake_wc latency** (C.2 result) suggests current lock waits are 5-31s, implying the autonomy tick (Phase A) and read_sentence are holding the lock for 5-30s at times.

**Missing**: No EFS-instrumented lock timing. The 5-31s wake_wc latency is primarily EFS log_event write time, not lock contention.

### F.2 — What's blocking Phase 3

Phase 3 (-59 §3) requires removing 26 `self.lock` acquires. Current state:

| Requirement | Status |
|-------------|--------|
| Coordinator per-source cells | NO design (only boolean _pair_bond dict + float strength) |
| Per-source tick domain | NO design |
| Lock-free atlas reads | Needs WaveAtlas as read path (Phase 2 in progress) |
| Remove 11+ `with self.lock:` sites | Not started |

c1a's honest assessment: Phase 3 has no implementation design for cells or per-source ticks. Phase 2 (WaveAtlas as read path) is the prerequisite and is partially deployed (Commit A rolled back after Gate 1 FAIL). Phase 3 cannot be estimated without Phase 2 succeeding.

---

## Summary — What Eve should update in her model

1. **Emission is blocked by a presence gate, not a processing failure.** She processes input (ingestion PASS, cross-modal PASS). She doesn't emit autonomously because EMITTING requires pair-bond presence AND winning activity selection. Joe's observation "nothing surfaces" is correct but the cause is the gate.

2. **Total_emissions=159 will remain at 159 until either**: (a) pair-bond source is present AND needs state creates high connection deficit that boosts EMITTING score, OR (b) the presence requirement is removed from emission candidate generation.

3. **Pictures are gone.** `n_pictures=0` at task:429 boot. Prior task had 11 pictures. The boot log shows `Visual restored: 0 pictures`. This means picture state was lost between task:428 and task:429. WaveAtlas serialization is also failing repeatedly (`Object of type complex is not JSON serializable`). The state save is partially broken.

4. **Atlas IS growing.** From 9,662 (boot) to 12,419 (now). Curriculum is landing and producing writes. She is learning in the atlas even without emitting.

5. **Vocab is barely moving** (+12 words in 33 min). Curriculum seed is mostly known vocabulary. She is not acquiring new concepts, she is reinforcing existing ones.

6. **Wake_wc will fail intermittently** as EFS write load increases. The log_event call in the wake handler is the same blocking EFS pattern as persistence_health — same fix applies.

7. **Sleep rate fix appears to be working**: zero SLEEPING or DREAMING events in 33 minutes of runtime (was 6-10 min previously). Dream pressure should be ~0.0009 (33 min × 60s × 5 ticks/s × 0.00001 rate).

---

## Recommended next actions (if Joe approves further code work)

**Independent fixes** (each a single app.py change):
1. **Wrap wake_wc `log_event` in run_in_executor** — same pattern as persistence_health. Eliminates 30s EFS-write spike in wake handler.
2. **Remove presence requirement from `_generate_activity_candidates`** — EMITTING goes into candidates regardless of presence. Substrate emits when it has something to say. Eve approves this direction before shipping.

**Structural investigation needed** (before any code):
3. **Why n_pictures=0** — pictures lost between task:428 and task:429. Need to understand whether this is a WaveAtlas JSON serialization failure causing corrupted EFS state, or a different path.
4. **WaveAtlas `complex` serialization error** — repeated failure in save. c1a should examine what's storing complex numbers in WaveAtlas cells.
5. **EMITTING activity selection** — with wC present and active bundles, EMITTING still lost to REST. The needs state needs to be examined (needs_arousal, needs_connection) to understand what would tip the salience balance.

---

End report.
