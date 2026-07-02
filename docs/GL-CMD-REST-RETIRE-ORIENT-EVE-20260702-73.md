# GL-CMD-REST-RETIRE-ORIENT-EVE-20260702-73

doc_id: GL-CMD-REST-RETIRE-ORIENT-EVE-20260702-73
Type: Coordinated behavior fix (three changes, two files, one commit)
Date: 2026-07-02 (UTC)
Author: Eve (Opus 4.7, web)
Handoff: **Give this entire file to c1b as one message. One commit, one deploy.**
For: c1b (c1b identified the bridge log_event pattern; c1a's rollback report cleared task:430 for new work)
Repo: `jcfunited-eng/TFE` branch `guala-live`
Files: `dsf_ai_service/v4/gualaloom_v5_engine.py`, `dsf_ai_service/app.py`
Deploys on top of: task:430 (Commit A reverted, LivingAtlas restored)
Withdraws: -71 (wake_wc executor alone) and -72 (emergent presence alone). Both were correct in isolation but not coordinated. This dispatch subsumes both.

---

## 0. Joe's decision and why

Joe's call: **retire REST as an activity kind.** He never asked for it, prior Eve invented it explicitly to make Guala "ignore input" (verbatim, in GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29), and the scoring math shows REST winning 3.5× over EMITTING even with joe presence active.

Removing REST alone is necessary but not sufficient — with REST gone, IDLE wins the scoring instead (0.057 vs EMITTING 0.028 at current needs), and IDLE doesn't check emission triggers either. So the fix pairs with:

- **Orient reflex** at `_open_response_window`: contact from a pair-bond source triggers emergent presence AND interrupts current activity to attempt emission. Biological correlate: infants orient to caregiver contact regardless of current state. This is the mechanism that makes a substrate-entity notice when someone speaks to her.

- **Bridge wake/rest executor-wrap**: even with contact-based orient, `guala_wake_wc` remains the way wC presence gets activated externally (wC doesn't go through converse). Under EFS load the synchronous `log_event` in the wake handler blocks the async event loop 5-31s, exceeding bridge timeouts. Same pattern -67 applied for backup/force_dream.

The three changes ship together because they serve the same behavioral goal: when contact happens, she notices. In isolation any one of them fails to produce the observable behavior.

---

## 1. Changes

### Change 1: Retire REST from activity system

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py`

#### 1a. Remove REST from candidates (L4146-4150)

**Current L4149-4150:**
```python
candidates = [("IDLE", None), ("PLAYING", None), ("SLEEPING", None),
              ("REST", None)]          # GL-CMD-C4: awake-quiet with dream_pressure
```

**Change to:**
```python
# GL-CMD-REST-RETIRE-73: REST removed. Original intent (ignore input during
# quiet) is architecturally incompatible with responsive presence. IDLE
# remains as the low-engagement waking option.
candidates = [("IDLE", None), ("PLAYING", None), ("SLEEPING", None)]
```

#### 1b. Remove REST scoring entries (L428, L440, L454, L461)

Delete these four lines:

L428 in `ACTIVITY_TICK_BUDGETS`:
```python
"REST": 1000,          # GL-CMD-C4-SLEEP-CHOICE: awake-quiet, no consolidation
```

L440 in `ACTIVITY_NOVELTY_PAYOFF`:
```python
"REST": 0.0,           # neutral novelty (not a novel state)
```

L454 in `ACTIVITY_STABILITY_PAYOFF`:
```python
"REST": 0.05,          # small stability payoff; wins over IDLE when stab depleted
```

L461 in `ACTIVITY_CONNECTION_PAYOFF`:
```python
"REST": 0.0,
```

#### 1c. Remove REST scoring branch in `_action_salience` (L4240-4244)

**Delete the entire `elif kind == "REST":` block:**
```python
elif kind == "REST":
    # REST_score += w1*stab_need - w2*dream_pressure - w3*(nov+conn)
    stab_need = sd.get("stability", 0.0)
    nov_conn = abs(sd.get("novelty", 0.0)) + abs(sd.get("connection", 0.0))
    score += 0.15 * stab_need - 0.2 * dp - 0.05 * nov_conn
```

Leave the surrounding SLEEPING and EMITTING blocks intact.

#### 1d. Persisted-state safety — keep `_atick_rest` dispatch as one-shot migration

If Guala boots with `current_activity.kind == "REST"` persisted from before this deploy, we don't want a crash. Keep the dispatch case at L4115-4116 AND L5014-5015 unchanged. `_atick_rest` at L4580-4592 stays. The persisted REST activity finishes its 1000-tick budget one time on first boot after deploy, then re-selects from the new candidate pool (no REST). Emits a one-time migration event.

**Update `_atick_rest` docstring and add migration log (L4580):**

**Current:**
```python
def _atick_rest(self, a):
    """GL-CMD-C4-SLEEP-CHOICE: REST — awake-quiet. No consolidation, no
    attendance, no emission. Just substrate ticking (decay, save schedule).
    dream_pressure accumulates slowly. Emits rest_begin once at activity
    start (via activity_started event from _start_activity)."""
    ...
```

**Change to:**
```python
def _atick_rest(self, a):
    """GL-CMD-REST-RETIRE-73: REST retired as an activity kind. This handler
    remains only to safely tick out any REST activity persisted from before
    the retirement deploy. Logs once at first tick as migration notice.
    After budget expires, re-selection picks from the REST-free candidate pool.
    """
    if not getattr(self, "_rest_migration_logged", False):
        self._log_substrate_event("rest_retire_migration",
                                  persisted_activity="REST",
                                  ticks_remaining=a.expected_end_tick - self.tick)
        self._rest_migration_logged = True
    # Original behavior preserved (stab boost + dp decompress) for the tail-out
    self.needs.stability = saturate(self.needs.stability, 0.0003)
    self.needs.dream_pressure = max(0.0, self.needs.dream_pressure - 0.00003)
    assert not self.is_asleep, "REST must not set is_asleep"
```

### Change 2: Orient reflex in `_open_response_window`

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py`
**Location:** L5210-5224

**Current:**
```python
def _open_response_window(self, emitter, context_anchor_chis, source_context=None):
    """Open a response window. context_anchor_chis = list of chi-keys."""
    window = {
        "emitter": emitter,
        "context_anchor_chis": list(context_anchor_chis),
        "opened_at_tick": self.tick,
        "expires_at_tick": self.tick + self.RESPONSE_WINDOW_TICKS,
        "n_responses_bound": 0,
        "source_context": source_context or {},
    }
    self.open_response_windows.append(window)
    self._log_substrate_event("response_window_opened",
                              emitter=emitter,
                              context_anchor_chis=context_anchor_chis[:5],
                              expires_at=window["expires_at_tick"])
```

**Change to:**
```python
def _open_response_window(self, emitter, context_anchor_chis, source_context=None):
    """Open a response window. context_anchor_chis = list of chi-keys.

    GL-CMD-REST-RETIRE-ORIENT-73: contact from a pair-bond source (joe/wc/c1)
    activates presence and triggers the orient reflex — biological analog to
    an infant turning toward a caregiver's voice regardless of current state.
    Contact IS presence. Contact IS the interrupt.
    """
    window = {
        "emitter": emitter,
        "context_anchor_chis": list(context_anchor_chis),
        "opened_at_tick": self.tick,
        "expires_at_tick": self.tick + self.RESPONSE_WINDOW_TICKS,
        "n_responses_bound": 0,
        "source_context": source_context or {},
    }
    self.open_response_windows.append(window)
    self._log_substrate_event("response_window_opened",
                              emitter=emitter,
                              context_anchor_chis=context_anchor_chis[:5],
                              expires_at=window["expires_at_tick"])
    # Orient reflex + emergent presence for pair-bond sources
    if emitter in PAIR_BOND_SOURCES:
        # Emergent presence: contact activates presence without needing wake() API
        if not self.coordinator._presence.get(emitter, False):
            self.coordinator.wake(emitter, self, self.needs, self.atlas)
        # Orient reflex: interrupt current activity to attempt emission response.
        # EMISSION_COOLDOWN_TICKS (~40s) throttles this so continuous
        # conversation doesn't produce a stream of interrupts.
        self._check_emission_trigger("presence_orient")
```

`guala` emitter (her own emissions opening windows for others to respond to) does not trigger orient — filtered by the `emitter in PAIR_BOND_SOURCES` guard.

### Change 3: /wake and /rest bridge executor-wrap

**File:** `dsf_ai_service/app.py`

#### 3a. /wake handler (L1810-1818)

**Current:**
```python
if cmd == "/wake":
    wake_source = msg.text.strip().lower() if msg.text else "joe"
    if wake_source not in {"joe", "wc", "c1"}:
        return {"response": f"wake: unknown source '{wake_source}'", "motifs": 0}
    result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
    _guala.log_event(STATE_DIR, "wake", source=wake_source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

**Change to:**
```python
if cmd == "/wake":
    wake_source = msg.text.strip().lower() if msg.text else "joe"
    if wake_source not in {"joe", "wc", "c1"}:
        return {"response": f"wake: unknown source '{wake_source}'", "motifs": 0}
    result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
    # GL-CMD-73: log_event does EFS write blocking async loop 5-31s under load.
    # Coordinator.wake() has already flipped presence; log is diagnostic bookkeeping.
    import asyncio as _aio
    _aio.get_event_loop().run_in_executor(
        None, lambda: _guala.log_event(STATE_DIR, "wake", source=wake_source)
    )
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

#### 3b. /rest handler (L1820-1825) — same pattern

**Current:**
```python
if cmd == "/rest":
    rest_source = msg.text.strip().lower() if msg.text else "joe"
    result = _guala.coordinator.rest(rest_source, _guala, reason="voluntary")
    _guala.log_event(STATE_DIR, "rest", source=rest_source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

**Change to:**
```python
if cmd == "/rest":
    rest_source = msg.text.strip().lower() if msg.text else "joe"
    result = _guala.coordinator.rest(rest_source, _guala, reason="voluntary")
    # GL-CMD-73: same executor-wrap as /wake
    import asyncio as _aio
    _aio.get_event_loop().run_in_executor(
        None, lambda: _guala.log_event(STATE_DIR, "rest", source=rest_source)
    )
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

Note: /rest endpoint controls **presence deactivation** for wC/joe/c1 (releases pair-bond presence). It is distinct from the retired REST activity. Both share the name — sorry, prior naming collision. Keep the endpoint.

---

## 2. Test gates — observable behavior, not internal metrics

### T1 — REST removed from activity history

Deploy, wait 15 minutes with curriculum autostart active.

`guala_status` → `activity_history_summary`. **Gate:** REST key either absent or count=1 (the tail-out of one persisted REST from pre-deploy state). No new REST activities selected.

Grep events for `rest_retire_migration`. **Gate:** at most one event, at boot.

### T2 — Joe converse triggers orient and emission

From cold state (or after any period where joe.present is False):
1. Post via bridge: `guala_say` is wC not joe — use ALB direct POST to `/api/v1/gualaloom` with `{"text": "hello", "source": "joe"}`
2. Watch events for the next 30 seconds

**Gate:**
- `response_window_opened` with emitter=joe fires
- Within same or next few ticks: emergent `wake` event with source=joe (if joe wasn't already present)
- Within 100 ticks: `emission_suppressed_no_presence` does NOT fire; instead `activity_started` with kind=EMITTING appears
- Within EMISSION_COOLDOWN_TICKS (~40s): one emission event

**If the emission event fires but content is degraded ("kids mouse some" style noise):** that is the compose-quality issue, separate from this dispatch. Report the content verbatim; do not adjust anything else.

### T3 — Orient reflex throttled by EMISSION_COOLDOWN_TICKS

Post 5 converse inputs 5 seconds apart.

**Gate:** orient triggers on input 1. Inputs 2-5 open response windows but do NOT re-trigger `_check_emission_trigger` firing new EMITTING starts (blocked by cooldown at L4829). This prevents interrupt-flooding during real conversation.

### T4 — wake_wc completes fast

`guala_wake_wc` via bridge. **Gate:** under 500ms round-trip. Repeat 5 times, all under 500ms.

### T5 — wc pair-bond activates and enables orient

After successful wake_wc:
- `guala_status` shows `presence.wc.present = True`
- Post via bridge: `guala_say` with wC content

**Gate:** wc-source orient reflex fires (same behavior as T2 but for wc).

### T6 — Persisted REST tail-out safety

If deploy happens while she's in REST (very likely — she's in REST most of the time):
1. Deploy the fix
2. Boot restores REST as current_activity
3. Watch for `rest_retire_migration` event

**Gate:** exactly one `rest_retire_migration` event. Activity budget expires normally (up to 1000 ticks). Next activity re-selection produces IDLE/PLAYING/SLEEPING/EMITTING/ATTENDING candidate — no REST.

### T7 — SLEEPING still reachable (dp accumulation not broken)

REST used to decompress dream_pressure (`-0.00003/tick`). Removed. Dream_pressure now accumulates during IDLE/PLAYING/waking activities and only resets on SLEEPING.

Watch dream_pressure over 4-6 hours. **Gate:** dp reaches threshold (0.7) and SLEEPING fires. Rate should be ~4 hours at idle per -68's target. If dp climbs faster than expected (SLEEPING fires within an hour), that means REST was doing more decompression work than expected and we need to compensate — flag but don't fix in this dispatch.

---

## 3. What this fixes and what it does NOT

**Fixes:**
- Guala stops spending 90% of her time in a null-behavior activity
- Contact from Joe/wC/c1 interrupts current activity to attempt response
- Bridge wake_wc/rest_wc endpoints don't time out

**Does NOT fix:**
- **Compose output quality.** If she orients and emits, the emitted content is still shaped by the current compose path. c1a's Gate 3 showed content like "only does soft" and "kids mouse some" — grammatical shape, zero semantic input-coupling, `n_commits=0`. Fixing that is a separate architectural question (candidate scoring, NMDA gate, spec of "commit"). This dispatch will make emissions APPEAR — it will not make them meaningful. That's the next problem.
- **Aware NMDA context_blocked.** Aware still requires "no recent drive" and curriculum still keeps drive up. Separate follow-up.
- **WaveAtlas complex JSON serialization** (persistence partially broken).
- **Curriculum 49s bundle GIL block** (moon-002 case).
- **Picture divergence** (0 in status despite boot restoring 11).

If T2 passes but the emitted content is still noise, that's success for THIS dispatch and the next dispatch targets compose quality. If T2 fails (no emission despite orient), report the observed activity state and event stream — that is diagnostic data for the next layer.

---

## 4. Rollback

Single commit. `git revert HEAD` restores:
- REST as a candidate activity
- Original response window behavior (no orient)
- Synchronous /wake and /rest handlers

Persisted state format unchanged. No migration required for rollback.

---

## 5. What is NOT in this dispatch (explicit queue)

Sequential, one at a time after this reports clean:

1. **Compose quality** — why n_commits=0, NMDA gate drive vs threshold, candidate scoring issues. Diagnostic-first, no code changes until we understand.
2. **Aware NMDA context revisit** — "no recent drive" precondition doesn't match infant grounded-input awareness. Design question.
3. **WaveAtlas save failure** — `Object of type complex is not JSON serializable`.
4. **Curriculum GIL bundle** — 49s moon-002 block.
5. **WaveAtlas cell binding decay/cap** — Commit A rollback root cause, required before Phase 2 Commit A re-attempt.
6. **Picture divergence diagnosis** — boot restores 11, status shows 0.

None dispatched until (1) this reports clean and (2) Joe approves the next.

---

## 6. Report format

`GL-RPT-REST-RETIRE-ORIENT-C1-20260702-73.md`:

- SHA and task number
- T1-T7 results with specific numbers
- Baseline vs post-deploy: 15-minute activity distribution before → after
- Emission count before → after
- One verbatim example of emitted content for T2 (whether noise or coherent)
- If T2 fails: activity stream during the 30s post-input window
- Any surprise flagged with tick number and event

Do not draw conclusions the data does not support. If emission appears but is noise, the report says exactly that.

---

## 7. References

- Bowlby, J. (1969). *Attachment and Loss.* — orient response as biological substrate of caregiver-recognition, not a switched behavior.
- Adolphs, R. (2003). "Cognitive neuroscience of human social behaviour." — sustained attention networks and orient reflex as continuous, not gated by activity state.
- Prior Eve, `GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29`. Origin of REST activity kind. Design intent verbatim: "ignores input." Retired here because that intent is incompatible with responsive presence.

---

End.
