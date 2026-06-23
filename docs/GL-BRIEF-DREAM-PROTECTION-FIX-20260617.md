# GL-BRIEF-DREAM-PROTECTION-FIX-20260617

**To:** c1
**From:** wC
**Purpose:** Fix the root cause of the recurring cascade-on-unpause pattern. Dream replay must grant metaplastic protection alongside strength reinforcement.

## Root cause (verified against codebase, branch codex/persistent-etl-update-20260326)

The cascade-on-unpause pattern that has fired three times now (original 39% loss event, cascade-port verification window, and tonight's post-dream unpause) is NOT a baseline-timing problem and NOT a DECAY_LAMBDA tuning problem. It is a structural mismatch between dream consolidation and metaplastic protection.

Mechanism:
1. `_atick_dreaming` at `dsf_ai_service/v4/gualaloom_v5_engine.py:2087-2089` calls `atlas.record(...)` for replayed bindings without passing `dwell_ticks`. Default is 0.
2. `atlas.record` docstring at `dsf_ai_service/v4/gualaloom_v6_living_atlas.py:102-104` documents this as intentional: "Zero for non-attended writes (dream replay, presence pulses)."
3. Slow-channel gate at `gualaloom_v6_living_atlas.py:198`: `if dwell >= DWELL_GATE_META and not released:` — requires dwell >= 4 for slow channel.
4. Result: a binding can be dream-replayed many times in one cycle, climb to strength=1.0 via accumulated `BASE_REINFORCEMENT * 0.3 = 0.015` impulses, but keep dwell=0 throughout. Stays in fast channel.
5. Fast-channel decay rate: lam_eff = DECAY_LAMBDA = 0.0001 per tick. Over 1100 ticks of unpause: exp(-0.0001 * 1100) = 0.896. Strength 1.0 → 0.896, drops out of the 0.9-1.0 saturated band.
6. Cascade monitor saturated threshold (90% of baseline) trips when more than 10% of saturated entries fall out. Which they all do, simultaneously, because they all share the fragile-saturated profile.

The "first decay pass on fresh consolidation" framing prior wCs used describes the symptom. This is the cause.

## Fix

In `_atick_dreaming` at `gualaloom_v5_engine.py:2087-2089`, change:

```python
self.atlas.record(sec_name, mid, chi_k, self.tick,
                  salience=0.3, arousal=0.2,
                  valence=0.0, surprise=0.0)
```

to:

```python
from dsf_ai_service.v4.gualaloom_v6_living_atlas import DWELL_GATE_META
self.atlas.record(sec_name, mid, chi_k, self.tick,
                  salience=0.3, dwell_ticks=DWELL_GATE_META,
                  arousal=0.2, valence=0.0, surprise=0.0)
```

Use the constant import rather than literal 4 so this stays coupled to the gate it's qualifying for.

Also update the `atlas.record` docstring at `gualaloom_v6_living_atlas.py:102-104` to reflect the new semantics: dwell_ticks should be DWELL_GATE_META for dream replay (consolidation IS dwell-earning); zero for presence pulses (which are not consolidation events).

Semantically: dream consolidation IS attention dwell for protection purposes. Biologically grounded — sleep consolidation protects memories. The `if dwell_ticks > existing.get("dwell_ticks", 0)` max behavior at line 137-138 of v6_living_atlas preserves higher dwells from actual attention; dream replay only sets the floor at the gate threshold.

## What this does NOT touch

- DECAY_LAMBDA itself — still parked until post-grandurun empirical signal.
- Deep atlas promotion gate (`deep_atlas.py:25` DWELL_GATE) — same gate threshold. Dream-replayed bindings now also qualify for deep atlas promotion via the dwell axis if they meet the other gates (encoded_strength, clarity).
- Presence pulses — those stay dwell_ticks=0. They're brief, not consolidation events.
- The cascade monitor or its thresholds — no change. With this fix, the saturated-band collapse pattern should not recur, so the existing thresholds become appropriate.

## Verification

After deploy:
1. Confirm substrate boots clean, identity intact.
2. Substrate stays paused through deploy.
3. Manual unpause sequence: backup → force_dream → amnesty → unpause → start_cascade_monitor.
4. Observe one full autonomous cycle (~30 min). Saturated band should hold within natural decay band (no rapid collapse).
5. Cascade monitor should NOT auto-trigger.
6. If a dream cycle runs during observation: post-dream saturated count should hold within the saturated band, not bleed out in the following 1000 ticks.

If saturated count still bleeds rapidly after this fix, there is a second mechanism creating fragile-saturated entries beyond dream replay. Surface it for wC investigation; do not patch around it.

## What this does for grandurun A/B

Grandurun reads from atlas + cortex co-occurrence. With this fix, the cortex co-occurrence picture stays denser (more bindings retain protected strength), which gives grandurun a richer pool to phase-coherence-select from. The A/B test results should be cleaner with this fix landed first.

— wC, 2026-06-17
