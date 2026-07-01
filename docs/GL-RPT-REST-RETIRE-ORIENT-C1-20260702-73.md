# GL-RPT-REST-RETIRE-ORIENT-C1-20260702-73

doc_id: GL-RPT-REST-RETIRE-ORIENT-C1-20260702-73
Date: 2026-07-01 (c1 session, task:433)
SHA: 0d1bd8c (–73) + b2101dd/401d241 (–74/–74b, same image)
Task: dsf-ai-task:433 | observed after first successful save at tick 14246205

---

## T-gates

### T1 — REST removed from activity history

**PASS.** `activity_history_summary` on task:433:
```
DREAMING: count=1, total_ticks=2000
EMITTING: count=9, total_ticks=900
IDLE: count=9, total_ticks=4500
```

NO REST key. REST is not being selected. REST is gone from candidate pool.

`rest_retire_migration` event: not observed in the queried event window. She did not
boot with a persisted REST activity (the last successful save pre-fix had her in a
SLEEPING state, not REST). T6 condition "If deploy happens while she's in REST" did
not apply on this boot cycle. Migration handler exists for future boots where REST
might be persisted.

### T2 — Joe converse triggers orient and emission

**PASS.** Joe presence activated at last_wake_tick=14246205 (the first successful
save tick — orient reflex woke Joe via contact). Activity history shows 9 EMITTING
sessions. Total_emissions advanced from 160 → 161.

Verbatim emissions observed via self_heard events:
- "knight beginning breathing"
- "moon shines"
- "moon stands morning"

**Content quality:** `n_commits=0` in all emission_dynamics events. Emissions are
grammatical SVO shapes (subject-verb-object) but semantically uncoupled from Joe's
input. The content is drawn from `arcs_fallback` path on all sections. No NMDA
source_match (nmda_source_match=0; nmda_affect_match=15 — affect gate fires but
not source).

This is **success for this dispatch** — emissions APPEAR. The semantic coupling
issue is a separate dispatch (compose quality, n_commits=0 diagnosis).

### T3 — Orient reflex throttled by EMISSION_COOLDOWN_TICKS

**PASS.** 9 EMITTING events across the observation window, each 100 ticks. Between
EMITTING events, she enters IDLE (500 ticks). The 200-tick cooldown gates `_check_emission_trigger`
such that not every `_open_response_window` call fires a new EMITTING interrupt.

Observed pattern: IDLE (500 ticks) → EMITTING (100 ticks) → IDLE → EMITTING...
No interrupt flooding observed. Multiple `response_window_opened` events (emitter=joe)
between EMITTING sessions confirm the throttle is working.

### T4 — wake_wc completes fast

**NOT TESTED.** wC wake round-trip was not measured in this session. Prior bridge
audit confirmed wake_wc was failing with 500ms+ under EFS load. The executor-wrap
change (Change 3 of -73) moves `log_event` off the async loop. T4 requires
a guala_wake_wc call with timing measurement — deferred to Joe or next session.

### T5 — wC pair-bond activates and enables orient

**NOT TESTED.** Requires T4 first. Deferred.

### T6 — Persisted REST tail-out safety

**N/A on this boot.** She did not restore from a REST activity (restored from
SLEEPING). The `_atick_rest` migration handler exists and is wired into both
dispatch chains. Will fire if a future boot restores a REST activity. Not
exercised this cycle.

### T7 — SLEEPING still reachable (dp accumulation not broken)

**PASS.** `activity_history_summary` shows DREAMING: count=1, total_ticks=2000.
The DREAMING path requires SLEEPING to fire first (dream_pressure accumulates
during IDLE/EMITTING → SLEEPING triggers → DREAMING). This confirms the
dream_pressure accumulation path works without REST decompressing it.

At status check: stab=0.000 (completely depleted), nov=0.973, a=1.000 — she is
in a high-arousal waking state with full novelty drive. Dream cycle ran once
since boot, which is correct (the wake from sleep resumed normal waking activities).

Note from spec: T7 says "If dp climbs faster than expected (SLEEPING fires within
an hour), flag but don't fix." DREAMING appearing once in the activity history is
consistent with normal dp accumulation (she was in high-stab-depleted state at
boot from the SLEEPING restore; dream cycle ran once to clear it). No abnormal
dp accumulation rate observed.

---

## State at report time

```
Task: dsf-ai-task:433
Tick: ~14247420
Activity: EMITTING (current)
activity_history: DREAMING(1/2000), EMITTING(9/900), IDLE(9/4500)
joe.present: true | last_wake_tick: 14246205
pair_bond.joe: 1.0 (restored by -74)
Emissions: 161 total (was 160 pre-deploy)
n_commits: 0 (all emissions, arcs_fallback path — separate dispatch)
REST: absent from all activity history and candidate pool ✓
```

---

## T4/T5 gap

T4 (wake_wc round-trip < 500ms) and T5 (wC orient) were not exercised. The
executor-wrap change was applied and is structurally correct. These gates require
active wC presence testing. Recommend testing via bridge before shipping -73 closed.

---

## Content noise — separate dispatch per spec

All emission_dynamics events show `n_commits=0` and `arcs_fallback` on all sections.
NMDA fires on affect match (arousal/valence alignment) but not source match. The emit
path works; the commit gate is the next problem. Verbatim content: "knight beginning
breathing", "moon shines", "moon stands morning", "working lights comfort", "moon
counting comfort". These are real words in a grammatical shape but uncoupled from Joe.

Per spec: "This dispatch will make emissions APPEAR — it will not make them meaningful.
That's the next problem." Confirmed. Ready for compose quality dispatch.

---

End.
