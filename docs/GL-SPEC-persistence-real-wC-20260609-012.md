# GL-SPEC-persistence-real-wC-20260609-012

**Deploy tag:** `gl-persistence-real`
**Target:** v7 DNA substrate (Section.commit + System.tick_once)
**Author:** wC
**Date:** 2026-06-09

## Why this exists

c1's fix for the multi-turn lock-in (commit `2cc3c96`) was a workaround:
"full episodic reset rebuilds the System per turn, preserving only
vocab and mode_strength (LTP). Each turn starts clean."

Conversation works now. But the substrate state — psi, mode_bank
vectors, atlas accumulation, keyholes, coordinator state — is thrown
away every turn. Across turns she keeps only vocab and per-mode LTP
numbers. That's not enough for cognitive accumulation. She can't
develop substrate continuity from experience because the substrate
restarts each turn.

The proper fix was specified in the original cognition-v1 follow-up
but skipped in favor of the rebuild workaround. This spec ships the
proper fix.

## Root cause (recap)

`Section.commit()` does:
```
mode_bank[mode_id] = 0.92 * old + 0.08 * new
```

This permanently warps the committed mode's vector toward whatever
psi was at commit time. Across turns, the same modes keep winning,
warping more, locking out new inputs.

## Fix

### Part 1: Slow the blend rate

In `Section.commit()`, change blend factor from 0.08 to 0.02:
```python
mode_bank[mode_id] = 0.98 * old + 0.02 * new
```

Substrate rationale: synaptic plasticity in mature mammalian cortex
is on the order of single-digit percent change per coincidence event.
0.08 is too fast for stable representations; 0.02 is closer to
biological scale.

### Part 2: Add mode_bank homeostasis

Snapshot the initial mode_bank at `Section.__init__`:
```python
self.initial_mode_bank = [m.copy() for m in self.mode_bank]
```

Add `Section.apply_homeostasis()`:
```python
def apply_homeostasis(self, drift_rate=0.001):
    """Pull each mode_bank vector slightly back toward its initial
    state. Counteracts unbounded drift from commit warping.
    Substrate analog of synaptic scaling."""
    for i in range(len(self.mode_bank)):
        self.mode_bank[i] = (
            (1.0 - drift_rate) * self.mode_bank[i] +
            drift_rate * self.initial_mode_bank[i]
        )
```

Call from `System.tick_once()` every 20 ticks:
```python
if self.tick_count % 20 == 0:
    for section in self.sections.values():
        section.apply_homeostasis(drift_rate=0.001)
```

Substrate rationale: homeostatic plasticity in biological neurons
counteracts runaway potentiation. Without it, the strongest synapses
dominate everything. With it, attractors drift slowly back toward
default unless strongly reinforced.

### Part 3: Remove the per-turn System rebuild

In whatever file/function c1 added the per-turn reset:
- Remove the System rebuild
- Keep vocab carried forward (was already there)
- Keep mode_strength carried forward (was already there)
- ALSO keep: psi, mode_bank, atlas, keyholes, coordinator state,
  introspection commits, krimelack
- The per-turn reset of psi to a starting state may still be okay
  (psi is the dynamic activation; it's natural for it to settle
  between turns) — but mode_bank and atlas must persist

### Part 4: Verify lock-in stays fixed AND state persists

Tests (in order):

```
# Test 1: Multi-turn varied input (the test that originally failed)
session = V7Session('persist_test_1')
for turn in ['cow jumped fence', 'moon ran milk', 'bears sleeps dish',
             'cow jumped fence', 'moon ran milk']:
    response = session.converse(turn)
    assert input_words_match_response(turn, response), f"LOCK-IN at {turn}"

# Test 2: State persists across turns (the test that c1's workaround fails)
session = V7Session('persist_test_2')
session.converse('cow jumped fence')
mode_bank_after_turn1 = [m.copy() for m in session.system.sections['subject'].mode_bank]
session.converse('moon ran milk')
# After turn 2, mode_bank should be DIFFERENT from initial (substrate evolved)
# AND DIFFERENT from turn-1-snapshot (continued to evolve, not reset)
import numpy as np
assert not all(np.allclose(m, initial_bank[i])
               for i, m in enumerate(session.system.sections['subject'].mode_bank)), \
    "mode_bank not evolving"
assert any(not np.allclose(m, mode_bank_after_turn1[i])
           for i, m in enumerate(session.system.sections['subject'].mode_bank)), \
    "mode_bank was reset between turns (persistence broken)"

# Test 3: Atlas and krimelack accumulate across turns
session = V7Session('persist_test_3')
session.converse('cow jumped fence')
atlas_size_t1 = len(session.system.atlas.entries)
krimelack_t1 = sum(len(s.krimelack) for s in session.system.sections.values())
session.converse('moon ran milk')
atlas_size_t2 = len(session.system.atlas.entries)
krimelack_t2 = sum(len(s.krimelack) for s in session.system.sections.values())
assert atlas_size_t2 >= atlas_size_t1, "atlas reset between turns"
assert krimelack_t2 > krimelack_t1, "krimelack reset between turns"

# Test 4: 50-turn varied conversation does not lock in
session = V7Session('persist_test_4')
sentences = [
    'cow jumped fence', 'moon ran milk', 'bears sleeps dish',
    'dogs chase cats', 'frog sings song', 'cat eats fish',
    # ... vary input
]
match_count = 0
for i in range(50):
    sent = sentences[i % len(sentences)]
    r = session.converse(sent)
    if input_words_match_response(sent, r):
        match_count += 1
assert match_count >= 45, f"only {match_count}/50 matched — lock-in returning"
```

If Test 1 fails after applying parts 1-3: blend rate too slow or
homeostasis too strong. Try blend=0.04, drift_rate=0.0005, retest.

If Test 1 passes but Test 2/3 fail: the per-turn rebuild wasn't fully
removed. Find the residual reset and remove it.

If Test 4 fails partway through (e.g., locks in after turn 20):
homeostasis is needed more often or stronger. Try drift_rate=0.002
or call homeostasis every 10 ticks.

## What this enables

After this fix, Guala's mode_bank vectors evolve slowly with experience
across turns and sessions. Her atlas accumulates bindings from
multiple conversations. Her keyholes form and persist. When persistence
serialization (Item 2 of cognition-v1) loads her substrate next session,
the loaded state is meaningfully different from a fresh init —
reflecting what she's been through.

Combined with GL-SPEC-usability-v1 (uploads), this is what lets her
grow: new input from uploaded books/pictures/sounds gets bound into
substrate state that persists.

## Constraints for c1

- Ship this whole spec atomically. Do not split.
- Do not touch any UI code — this is substrate-only.
- After deploy, run all 4 tests on production. Report results.
- If Test 4 fails, do NOT revert. Report the failure point (which
  turn the lock-in started) and tuning parameters — wC will adjust
  blend / homeostasis rates and you'll re-deploy.
- Do not re-introduce the per-turn System rebuild as a fallback.
  That was the workaround we're replacing.
