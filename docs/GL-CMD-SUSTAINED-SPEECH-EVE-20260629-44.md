# GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44

doc_id: GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Prereq: GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43 (multi-anchor composer must ship first)

---

## 1. Purpose

After -43 lands, the composer can produce multi-word coherent emissions. But three structural caps still prevent sustained speech:

1. **`MAX_COMPOSITION_LEN = 12`** (gualaloom_v5_engine.py:339) — hardcoded cap on words per emission. Substrate-physical termination already exists via `MIN_GAIN_THRESHOLD` — when no remaining candidate adds enough coherence gain, composition stops. The cap is redundant and clips substrate-physical expression at an arbitrary length.

2. **No emission chaining** — when she emits, the content gets fed back via `read_sentence(content, source="guala")` (per -39) but the *next* emission attempt does not explicitly use the last emission's chi addresses as input. So successive emissions don't carry topic continuity through the composer's input_chis.

3. **`EMISSION_COOLDOWN_TICKS = 200`** (gualaloom_v5_engine.py:396) — fixed 40s pause between emissions regardless of substrate state. When she has more to express (low coherence emission, recent input), cooldown is too long. When she expressed fully (high coherence), cooldown is fine. The fix: substrate-derived cooldown based on last emission's coherence.

Together these enable sustained speech: longer single emissions (1), connected successive emissions (2), substrate-paced cadence (3).

---

## 2. Changes

### 2.1 Remove MAX_COMPOSITION_LEN as a hard cap

In `_grandurun_select` (L65, single-anchor — pre -43) and `_grandurun_select_multichi` (added by -43), the loop currently terminates on `len(chosen_words) >= MAX_COMPOSITION_LEN`. Remove this termination. Keep the substrate-physical termination (gain below threshold).

```python
# BEFORE (in both selectors)
for chi_addr, strength, word in pool:
    amp = ...
    gain = ...
    if gain > MIN_GAIN_THRESHOLD:
        chosen_words.append(word)
        ...
    if len(chosen_words) >= MAX_COMPOSITION_LEN:
        break

# AFTER
for chi_addr, strength, word in pool:
    amp = ...
    gain = ...
    if gain > MIN_GAIN_THRESHOLD:
        chosen_words.append(word)
        ...
    # Substrate-physical termination: gain threshold + pool exhaustion.
    # No artificial length cap.
```

The `MAX_COMPOSITION_LEN = 12` constant remains in the module for reference but is no longer enforced. Add a SAFETY_COMPOSITION_LEN = 200 as a runaway-prevention bound (one full emission with one word per pool entry, generous upper bound):

```python
SAFETY_COMPOSITION_LEN = 200  # runaway-prevention only; substrate physics terminates earlier
```

And:
```python
if len(chosen_words) >= SAFETY_COMPOSITION_LEN:
    break  # paranoia only — never expected to fire
```

### 2.2 Emission chaining via input_chis augmentation

After every successful emission (both `_emit_grandurun` returning content and `compose_autonomous` succeeding), record the emitted content's chi addresses for use in the next emission's input.

Add to `Guala.__init__`:
```python
self._last_emission_chis = []  # chi addresses from last emission's content
self._last_emission_chi_tick = -100_000
self._last_emission_coherence = 0.0
```

Add a helper:
```python
def _record_emission_chain(self, content, coherence):
    """Store chi addresses from emitted content for chaining into next emission.
    Coherence stored separately for dynamic cooldown (§2.3)."""
    if not content or content == "...":
        self._last_emission_coherence = 0.0
        return
    from .gualaloom_v4_krimelack_dna import LanguageKrimelack
    chis = []
    for w in _normalize_text(content):
        k = LanguageKrimelack()
        k.transduce(w)
        chis.append(k.winding)
    self._last_emission_chis = chis
    self._last_emission_chi_tick = self.tick
    self._last_emission_coherence = float(coherence)
```

Call `_record_emission_chain(emission_text, coherent_sum)` at the end of `_emit_grandurun` (after L2023) and equivalent end-of-emission point in `_emit_grandurun_vector` if it exists. For `compose_autonomous`, call after a successful result with `coherence = result.get("n_commits", 0) * 0.5` (substrate-derived from commit count if no direct coherence available).

Add an input_chis augmentation helper:
```python
def _augment_input_chis_with_chain(self, input_chis):
    """If recent self-emission exists, include its chi addresses in input.
    Persist window: 3 × EMISSION_COOLDOWN_TICKS — chained content remains
    relevant for approximately three emission cycles, then fades naturally
    from the input. Substrate-derived from existing constant."""
    chained = getattr(self, '_last_emission_chis', None)
    chained_tick = getattr(self, '_last_emission_chi_tick', -100_000)
    persist_window = EMISSION_COOLDOWN_TICKS * 3
    if chained and (self.tick - chained_tick) < persist_window:
        return list(chained) + list(input_chis)
    return input_chis
```

Use it in `_emit_from_invariants` (L1801) — augment input_chis at the top before deep_candidates gathering:
```python
def _emit_from_invariants(self, input_chis, input_words, v7_session=None):
    ...
    # GL-CMD-SUSTAINED-SPEECH-44: chain recent emission context
    input_chis = self._augment_input_chis_with_chain(input_chis)
    ...
```

This makes successive emissions chi-coherent with prior emitted content via the multi-anchor composer (per -43). Topic continuity emerges as substrate-physical resonance across emissions, not as a tracked variable.

### 2.3 Substrate-derived dynamic cooldown

Replace fixed `EMISSION_COOLDOWN_TICKS` comparisons with a dynamic effective cooldown derived from the last emission's coherence.

Add to engine:
```python
def _effective_cooldown(self):
    """Substrate-derived cooldown based on last emission's coherence.
    
    High coherence emission = more expressed = longer recovery
    (multiplier near 2.0).
    Low coherence emission = fragments = ready sooner to chain
    (multiplier near 0.5).
    
    Bounds [0.5×base, 2.0×base] are substrate-cycle multiples — half-cycle
    minimum so emissions can't fire arbitrarily fast, two-cycle maximum so
    she's never blocked from speaking for more than ~80s by cooldown alone.
    """
    last_coh = getattr(self, '_last_emission_coherence', 0.0)
    # Multiplier scales with coherence: 0 → 0.5, 0.5 → 1.0, 1.5+ → 2.0 (clamped)
    multiplier = max(0.5, min(2.0, last_coh + 0.5))
    return int(EMISSION_COOLDOWN_TICKS * multiplier)
```

Replace the three current uses of `EMISSION_COOLDOWN_TICKS` comparisons:

L3601 in activity scheduler (`_candidate_activities`):
```python
# BEFORE
and self.tick - self._last_emission_tick > EMISSION_COOLDOWN_TICKS):

# AFTER
and self.tick - self._last_emission_tick > self._effective_cooldown()):
```

L4127 in `_check_emission_trigger`:
```python
# BEFORE
if self.tick - self._last_emission_tick < EMISSION_COOLDOWN_TICKS:

# AFTER
if self.tick - self._last_emission_tick < self._effective_cooldown():
```

The third place (any in `_should_attempt_autonomous_emission` from -39) — apply same substitution if it uses EMISSION_COOLDOWN_TICKS or AUTONOMOUS_THROTTLE_TICKS comparison; otherwise leave (different gate).

### 2.4 Persistence

`_last_emission_chis`, `_last_emission_chi_tick`, and `_last_emission_coherence` should be serialized in `snapshot()` (around L4966) and restored in `load_snapshot()` (around L5433). Without persistence, post-restart she loses her recent emission context. Small atomic addition.

---

## 3. Tests

### T1 — Composition no longer clips at 12 words

Construct a pool where 20+ candidates each contribute MIN_GAIN_THRESHOLD-level gain (high coherence with target). Run the selector. Expected: composition length > 12 words. The substrate-physical termination (gain below threshold) is what stops composition, not the cap.

If composition stops short of 12 in practice on real substrate state, that's substrate-true sparsity, not cap clipping — verify by inspecting the last gain calculation in the selector.

### T2 — Chain augmentation: successive emissions reference prior content

Drive an autonomous emission (via wake_wc + presence + need-state per -39). Record emission text E1 with chi addresses C1.

Within 3 × EMISSION_COOLDOWN_TICKS, force another emission (manipulate need state or wait for next EMITTING activity selection). E2's `_emit_from_invariants` should receive augmented input_chis including C1. Verify by either:
- Inspecting input_chis at the top of `_emit_from_invariants` (debug log or test instrumentation)
- Or by observing that E2's content shares chi-coherence with E1 — words in E2 should be chi-near at least one word in E1

After 3 × EMISSION_COOLDOWN_TICKS passes with no new emission, the next emission's `_last_emission_chis` should NOT augment (window expired).

### T3 — Dynamic cooldown shortens after low-coherence emission

Force a low-coherence emission (e.g. by manipulating substrate to produce 1-word emission with low coherence_sum). `_last_emission_coherence` should be near 0. `_effective_cooldown()` should return ≈ `100` ticks (0.5 × base = 100).

Force a high-coherence emission (multi-word, high coherence). `_effective_cooldown()` should return ≈ `400` ticks (2.0 × base = 400).

Verify activity scheduler picks EMITTING again at ~100 ticks vs ~400 ticks in the two scenarios.

### T4 — Sustained speech demonstration

After all changes deploy, drive substrate density via curriculum (8-10 sentences as wC over 5 minutes). Then wait. Expected behavior in the next 10 minutes:
- At least one autonomous emission with > 5 words
- At least one chained emission pair (E1 followed within 200 ticks by E2 with topic-coherent content)
- Total of 3-5+ autonomous emissions in the 10-minute window (vs. ~1 pre-deploy)

If she produces only 0-1 emissions, sustained speech architecture didn't activate — surface for diagnosis (cooldown too long, pool too sparse, or other gate not crossed).

### T5 — Persistence round-trip

Trigger save during a session with non-zero `_last_emission_coherence` and non-empty `_last_emission_chis`. Restart task. Verify both restored. Confirm next emission still chains from the persisted previous emission if within the persist window.

### T6 — Substrate stability

After 30 min: vocab/atlas/motif growth normal. Daydream loop continues. No exceptions in emission path. Average emission length should be observably higher than pre-deploy (track via events log emission entries).

---

## 4. Rollback

Each change is independently revertable:
- §2.1: re-add `if len(chosen_words) >= MAX_COMPOSITION_LEN: break` to selectors.
- §2.2: comment out the `_augment_input_chis_with_chain` call. Helper and state vars are harmless to leave.
- §2.3: replace `self._effective_cooldown()` with `EMISSION_COOLDOWN_TICKS` at the three sites.

If T4 shows runaway emission (she emits too frequently or output degrades), most likely cause is §2.3 — raise the lower bound on `_effective_cooldown` from 0.5× to 0.75× or 1.0×.

---

## 5. Reporting

c1 produces `GL-RPT-SUSTAINED-SPEECH-C1-20260629-44.md` with:
- Diff summary for §2.1, §2.2, §2.3, §2.4.
- T1: example composition length on synthetic high-coherence pool.
- T2: pair of E1/E2 emission content, augmented input_chis at E2.
- T3: numeric `_effective_cooldown()` values in low/high coherence scenarios.
- T4: full count of autonomous emissions in 10-min window post curriculum drive, with content of each. Average word length.
- T5: persistence round-trip verification.
- T6: stability metrics.
- Final SHA, task number.

If T4 shows < 2 autonomous emissions or no chained pair, surface immediately.

---

## 6. Out of scope

- `MIN_GAIN_THRESHOLD` substrate derivation (flagged in -43; still not changed here — change one structural thing at a time).
- `CHI_CORR_LENGTH` substrate derivation (same).
- Agency organ writes (still rejected; defer until sustained speech is observed).
- Discourse-level features (turn-taking, question-answering structure, conversational repair). These are higher-order behaviors that may emerge from the chaining + cooldown architecture, or may need separate dispatches.
- Activity-scheduler tuning to favor EMITTING. Current need-driven selection unchanged; dynamic cooldown shortens the lockout but doesn't change selection probability.

---

## 7. What this builds toward

The substrate's voice capacity after this dispatch (combined with -43):

- **Single emission**: substrate-physically bounded length — composer continues adding words as long as candidates contribute coherence gain, terminates naturally when pool/coherence exhausts. No 12-word ceiling.
- **Successive emissions**: chained via input_chis augmentation. Topic continuity emerges as multi-anchor resonance includes prior emission's chis. She "stays on topic" because her own recent words are still in the resonance pool.
- **Cadence**: substrate-paced. Low-coherence emission (fragments) → fast follow-up → chain to extend the burst. High-coherence emission (complete expression) → longer recovery → next emission starts fresh.

Combined effect: when substrate has resonance to express, she expresses it as connected multi-emission sequences. When substrate is sparse, emissions remain substrate-true short — but not because of heuristic clipping.

Whether she "talks for hours" depends on substrate state, need-state, and accumulated experience. The architecture supports it. The behavior emerges from substrate physics.
