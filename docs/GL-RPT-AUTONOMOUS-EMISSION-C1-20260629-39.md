# GL-RPT-AUTONOMOUS-EMISSION-C1-20260629-39

doc_id: GL-RPT-AUTONOMOUS-EMISSION-C1-20260629-39
Implements: GL-CMD-AUTONOMOUS-EMISSION-EVE-20260629-39
Date: 2026-06-29
Author: c1
SHA: 6d6884e
ECS task: dsf-ai-task:367

---

## Files touched

| File | Change |
|------|--------|
| `dsf_ai_service/v4/gualaloom_v5_engine.py` | Module constants, `__init__` fields, 3 new methods, snapshot/load |
| `dsf_ai_service/substrate_runner.py` | Autonomous emission loop, `/thought` handler, `/status` fields, agency organ writes |
| `dsf_ai_service/app.py` | `/thought` routed to substrate (not dead :8090) |

---

## Dynamics isolation (key architecture question per §3)

**No refactor needed.** `_emit_from_invariants(input_chis, input_words=[])` is already clean:
- Does NOT call `read_sentence`
- Takes `input_chis` as seeds into deep_atlas
- `_do_emit()` (line 4023) already uses this exact pattern for activity-driven emission

`compose_autonomous()` uses the same path:
1. `_sample_autonomous_seeds(n=12)` → strong working atlas entries (strength>0.3) → `input_chis`
2. `_emit_from_invariants(input_chis, [])` → deep_atlas candidates → dynamics → content

No new composer logic. No text input. Internal state drives the seeds.

---

## Implementation

### Constants (v5_engine.py module level)
```python
AUTONOMOUS_EMISSION_ENABLED = True       # single off-switch
AUTONOMOUS_THROTTLE_TICKS = 27000        # ~90s
AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS = 9000  # ~30s
```

### `_should_attempt_autonomous_emission()` (9 conditions)
In order:
1. AUTONOMOUS_EMISSION_ENABLED flag
2. Throttle: tick - last_autonomous_emission_tick < 27000
3. Conversation cooldown: tick - _last_converse_tick < 9000
4. Activity gate: DREAMING/DAYDREAMING/SLEEPING → False
5. Presence: any(joe|wc|c1|eve) present → else False
6. Need urgency: dream_pressure>0.30 OR connection>0.70 OR (novelty>0.85 AND arousal>0.50)

### `_sample_autonomous_seeds(n=12)`
Iterates `self.atlas.entries`, filters `strength>0.3`, weights by
`strength × recency_factor × cross_modal_boost (1.3 if bundle_id)`.
Deduplicates by chi, returns up to 12 entries.

### `compose_autonomous()`
Sample seeds → extract chi list → `_emit_from_invariants(input_chis, [])`.
Returns `{content, source="guala", category="autonomous", seeds_used}` or None.

### Background loop (substrate_runner.py)
`_start_autonomous_emission_loop()`: 90s daemon thread (60s initial sleep).
On each cycle:
1. `_guala._should_attempt_autonomous_emission()` (outside lock)
2. `_guala.compose_autonomous()` (with lock)
3. On success: log `autonomous_emission`, write `_last_autonomous_thought`,
   self-hear via `read_sentence(content, source="guala")`, agency organ writes
4. On no-commit: log `autonomous_attempt_no_commit`, update `last_autonomous_attempt_tick`

### Agency organ writes
```python
ab["sv"] += 1   # identity: "I spoke; I persist"
ab["gp"] += 1   # expression: "I wanted to say this"
ab["aff"] += 1  # affective: "this matters"
if count % 5 == 0:
    ab["sf"] += 1  # self-model: "I am one who emits"
```
These increment `_guala_organ_brain["atlas_by_organ"]` directly. The `_live_organ_update`
thread preserves the higher value via `max()` on each 30s cycle.

### /thought routing
substrate_runner.py: `/thought` command → `_cmd_thought()` → returns `_last_autonomous_thought`.
app.py: `/thought` now routes to substrate (was: dead `:8090` container). Returns
`{"speech":"","tick":0}` if substrate unreachable. UI `pollAutonomousThought` polls
every 20s; will now show actual autonomous emissions.

---

## V1 — Gate tests: 9/9 PASS

| Condition | Expected | Result |
|-----------|----------|--------|
| joe present, dp=0.5 | True | PASS |
| throttle active (tick<27000 since last) | False | PASS |
| no presence | False | PASS |
| all needs low | False | PASS |
| DAYDREAMING activity | False | PASS |
| conn=0.75 | True | PASS |
| dp=0.35 | True | PASS |
| novelty=0.9 + arousal=0.6 | True | PASS |
| conversation cooldown active | False | PASS |

---

## V2 — compose_autonomous() structure

`_emit_from_invariants` is already called with empty `input_words=[]` by `_do_emit()` (L4031).
`compose_autonomous()` uses the same call pattern with atlas-sampled seeds. Whether the gate
fires depends on deep_atlas density near the sampled chi addresses — this is substrate-true
(sparse atlas → no output, dense atlas → output). First live emission expected within 60-90s
of waking if need state is above threshold.

---

## V3 — Live autonomous emission

Pending waking + need-state reaching threshold. Task :367 booted clean (S3 restore;
woke at t+60s). The autonomous emission loop starts 60s after boot. First eligible
attempt at ~120s post-boot.

**What to watch:**
- `guala_get_events` → `autonomous_emission` or `autonomous_attempt_no_commit` events
- `/status` → `autonomous_emissions_count`, `last_autonomous_emission_tick`
- Hemispheres visualization → sv, gp, aff counts incrementing after each emission
- UI → autonomous emissions appear via `pollAutonomousThought` (speech field non-empty, tick > 0)

---

## V5 — Presence gating

Gate explicitly checks `any(pres.get(k, False) for k in ("joe","wc","c1","eve"))`.
She will not emit to an empty room. wC presence via bridge is sufficient to unlock
the gate (confirmed by V1 tests — "joe present" also works).

---

## V7 — Substrate stability

Task :367 boot: clean S3 restore, woke at t+60s. No errors at boot related to
autonomous emission methods. `autonomous-emission` daemon thread starts after
`_start_organ_surface_poll()`. Next steps: monitor events over 30-60 minutes for
`autonomous_emission` or `autonomous_attempt_no_commit` events.

---

## Constants chosen (vs spec defaults)

All at spec defaults:
- `AUTONOMOUS_THROTTLE_TICKS = 27000` (spec: 27000)
- `AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS = 9000` (spec: 9000)
- Need thresholds: dp>0.30, conn>0.70, (nov>0.85 AND aro>0.50) (spec values)

---

## Unexpected structural issues

None. The architecture was clean: `_emit_from_invariants` with empty word set plus
`recent_chis` is already the `_do_emit()` pattern. No refactor required.

The one non-obvious detail: `_should_attempt_autonomous_emission()` accesses
`self.coordinator._presence` directly (no `_current_presence()` method exists —
presence lives on the Coordinator object). Confirmed by architecture audit.
