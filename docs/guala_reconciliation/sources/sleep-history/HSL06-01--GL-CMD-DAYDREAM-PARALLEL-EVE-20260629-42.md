# GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42

doc_id: GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Replaces: rejected GL-CMD-AGENCY-ORGAN-WIRING-EVE-20260629-41 (was treating wrong problem)
Addresses: daydreaming-as-sleep architectural error + co_occurrence averaging constants that lock in legacy associations

---

## 1. The two issues

### 1a. Daydreaming is implemented as a sleep cycle, not parallel thought

`_atick_daydreaming` (gualaloom_v5_engine.py:3739) calls `_run_dream_cycle(caller_kind="DAYDREAMING")` — same code path as DREAMING. Activity scheduler treats DAYDREAMING as a competing 1500-tick activity (`ACTIVITY_TICK_BUDGETS["DAYDREAMING"]`). When DAYDREAMING is selected, no other activity can run until the budget expires. The current implementation also skips consolidation when presence is active (L3750-3751) but still holds the activity slot for the full 1500 ticks doing essentially nothing.

Daydreaming is not sleep. It is parallel distracted thinking — chi-geometric associative activation that runs WHILE other activities continue. Sensory input or recent activation propagates through chi neighborhoods, surfacing related motifs as a parallel thought stream. It doesn't block voice. It doesn't replace foreground activity. It runs continuously in the background.

### 1b. co_occurrence averaging locks in legacy associations

`deep_atlas.py:139`:
```python
sec_dict[mid] = old_w * 0.92 + e["strength"] * 0.08
```

The 0.92/0.08 constants are not derived from substrate physics. Their effect: a new motif (e.g. modifier or ground motif added by -36 DNA expansion) needs to appear in the working_atlas neighborhood of a promoting binding approximately 36 times (`ln(0.05)/ln(0.92)`) before its co_occurrence weight reaches 95% of steady-state. With current substrate traffic, that's hours-to-days per new association.

`deep_atlas.py:133`:
```python
if e["strength"] < 0.05:
    continue
```

A hardcoded strength floor that excludes low-strength bindings from co_occurrence updates entirely. Newly-arrived DNA motifs (modifier/ground from -36) start at strength below this floor on first appearance. They are filtered out of co_occurrence updates until they happen to be reinforced past the floor — which requires multiple appearances at full salience before they're even visible to the co_occurrence mechanism.

Together: the substrate is structurally locked into pre-expansion associations by arbitrary smoothing constants.

---

## 2. Changes

### 2.1 Remove DAYDREAMING from activity scheduler

In `dsf_ai_service/v4/gualaloom_v5_engine.py`:

Remove DAYDREAMING from `_candidate_activities` (search for the activity construction). It is no longer a competing activity. Other activities (PLAYING, ATTENDING, REST, LISTENING) reclaim its 1500-tick budget time.

Remove `_atick_daydreaming` (L3739-3755) entirely — no callers after the scheduler change.

Remove `ACTIVITY_TICK_BUDGETS["DAYDREAMING"]` entry. Remove DAYDREAMING from any activity-kind enums or string lists.

### 2.2 Add background daydream loop

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, alongside `start_autonomy_loop()` and the existing 90s autonomy thread:

```python
def start_daydream_loop(self):
    """Background associative activation. Runs in parallel with whatever
    foreground activity is current. Not gated on presence, not blocking
    /converse. Substrate-physical chi-neighborhood walks driven by recent
    activation."""
    if getattr(self, '_daydream_thread', None) is not None:
        return
    self._daydream_running = True
    
    def _loop():
        while self._daydream_running:
            try:
                with self.lock:
                    self._daydream_tick()
            except Exception:
                pass
            time.sleep(0.5)  # 2 Hz — frequent enough to catch fresh activation,
                             # bounded so it doesn't dominate CPU
    
    self._daydream_thread = threading.Thread(target=_loop, daemon=True,
                                              name="daydream-loop")
    self._daydream_thread.start()

def _daydream_tick(self):
    """One pass of parallel associative surfacing.
    
    Source of activation: chi addresses recently touched by input, attention,
    or emission. Walks chi neighborhoods, surfaces co_occurrence motifs,
    lightly reinforces working atlas at those addresses. Does NOT trigger
    commit gate or emission. Output is a parallel thought stream observable
    in events."""
    
    # Recently-active chis: from sec.commits across all sections (last 10).
    # The substrate already tracks these.
    recent_chis = []
    for sec in self.sections.values():
        for c in sec.commits[-10:]:
            recent_chis.append(c["chi"])
    if not recent_chis:
        return
    
    # Pick ONE chi to walk this tick (random sample weighted by recency).
    # Multiple chis per tick would dominate; one chi per 0.5s = 7200 walks/hour.
    seed_chi = recent_chis[self.tick % len(recent_chis)]
    
    # Walk: find deep_atlas entries in the chi neighborhood
    band = self.atlas.band
    associated = []
    for d in range(-band, band + 1):
        for de in self.deep_atlas.entries.get(seed_chi + d, []):
            co = de.get("co_occurrence", {})
            if not co:
                continue
            # Pick the strongest single (section, motif) from this entry's co_occurrence
            best_sec = None
            best_mid = None
            best_w = 0.0
            for sec_name, motif_dict in co.items():
                if not motif_dict:
                    continue
                top_mid = max(motif_dict, key=motif_dict.get)
                top_w = motif_dict[top_mid]
                if top_w > best_w:
                    best_w = top_w
                    best_sec = sec_name
                    best_mid = int(top_mid)
            if best_sec is not None:
                associated.append((best_sec, best_mid, best_w, de["chi"]))
    
    if not associated:
        return
    
    # Lightly reinforce the strongest association in working atlas.
    # This is the "association passed through her mind" effect — the motif
    # gets a small strength bump but does not trigger any commit-gate firing.
    associated.sort(key=lambda x: x[2], reverse=True)
    top_sec, top_mid, top_w, top_chi = associated[0]
    
    # Reinforce at salience = co_occurrence weight (substrate-derived, not invented).
    # Dwell = 1 tick (transient surfacing, not memory-forming).
    self.atlas.record(
        section=top_sec, motif=top_mid, chi=top_chi,
        tick=self.tick,
        salience=top_w,  # substrate-derived from co_occurrence strength
        dwell_ticks=1,
        arousal=self.needs.arousal() * 0.3,  # ambient affect of the substrate
        valence=self.needs.valence() * 0.3,
        surprise=0.0,
        source="daydream",  # source-tag distinct from corpus/joe/wc/etc
    )
    
    # Log the surfacing for observability
    if top_sec in self.sections:
        sec = self.sections[top_sec]
        if top_mid < len(sec.modes):
            _, _, word_label = sec.modes[top_mid]
            self._log_substrate_event("daydream_surface",
                seed_chi=seed_chi, surfaced_chi=top_chi,
                section=top_sec, word=word_label,
                strength=round(top_w, 3))
    
    # === EXTENSION A: novel-connection jumps ===
    # With probability 1/atlas.band per tick (substrate-derived: wider band
    # = lower jump probability because neighborhood walks already cover
    # wider range), pick a chi-distant address and surface a motif from
    # there. The (near, far) pair is the substrate-physical "novel
    # combination" — chi-distant associations that don't co-occur naturally.
    import random as _random
    if _random.random() < 1.0 / max(2, self.atlas.band):
        chi_keys = list(self.atlas.entries.keys())
        if chi_keys:
            min_distance = 5 * self.atlas.band
            # Find a chi at least min_distance away from seed_chi
            far_candidates = [c for c in chi_keys if abs(c - seed_chi) >= min_distance]
            if far_candidates:
                far_chi = far_candidates[self.tick % len(far_candidates)]
                for de in self.deep_atlas.entries.get(far_chi, []):
                    co = de.get("co_occurrence", {})
                    if not co:
                        continue
                    # Surface strongest from far chi
                    far_best = None
                    far_w = 0.0
                    for sec_name, motif_dict in co.items():
                        if motif_dict:
                            mid_str = max(motif_dict, key=motif_dict.get)
                            if motif_dict[mid_str] > far_w:
                                far_w = motif_dict[mid_str]
                                far_best = (sec_name, int(mid_str))
                    if far_best is not None:
                        far_sec, far_mid = far_best
                        # Light reinforce at far_chi
                        self.atlas.record(
                            section=far_sec, motif=far_mid, chi=far_chi,
                            tick=self.tick, salience=far_w, dwell_ticks=1,
                            arousal=self.needs.arousal() * 0.3,
                            valence=self.needs.valence() * 0.3,
                            surprise=0.5,  # novel pairs ARE substrate-physically surprising
                            source="daydream",
                        )
                        # Log the novel combination
                        if far_sec in self.sections and far_mid < len(self.sections[far_sec].modes):
                            _, _, far_label = self.sections[far_sec].modes[far_mid]
                            self._log_substrate_event("daydream_novel",
                                seed_chi=seed_chi, far_chi=far_chi,
                                near_word=word_label if word_label else "",
                                far_word=far_label,
                                far_strength=round(far_w, 3))
                    break  # one far surface per jump
    
    # === EXTENSION B: affect-weighted candidate selection ===
    # When she's at non-neutral need state, daydream selectively surfaces
    # motifs whose recorded affect would shift her toward balance.
    # The sort in the main path already used top_w; this extension is
    # incorporated by replacing that sort with the affect-weighted version.
    # (See implementation: replace the `associated.sort` call above with
    # the version below.)
    #
    # def _affect_weighted_score(item, current_v, current_a):
    #     sec, mid, w, chi = item
    #     # Pull the deep_atlas entry's recorded affect at this chi
    #     entry_v, entry_a = 0.0, 0.5  # defaults if entry doesn't have these
    #     for de in self.deep_atlas.entries.get(chi, []):
    #         if de.get("section") == sec and de.get("motif") == mid:
    #             entry_v = de.get("valence", 0.0)
    #             entry_a = de.get("arousal", 0.5)
    #             break
    #     # Substrate-physical bias: candidates that would shift needs toward
    #     # (valence=0, arousal=0.5) get higher weight. 0.5 weights derive
    #     # from the substrate's neutral targets.
    #     v_after = (current_v + entry_v) * 0.5
    #     a_after = (current_a + entry_a) * 0.5
    #     affect_bias = 1.0 - abs(v_after) * 0.5 - abs(a_after - 0.5) * 0.5
    #     return w * max(0.1, affect_bias)
    #
    # current_v = self.needs.valence()
    # current_a = self.needs.arousal()
    # associated.sort(key=lambda item: _affect_weighted_score(item, current_v, current_a), reverse=True)
    
    # === EXTENSION C: designed consolidation side effect ===
    # Every Nth daydream tick (N = atlas.band * 10, substrate-derived from
    # band size), opportunistically refresh co_occurrence on the visited
    # deep_atlas entry via the same _update_invariant the dream cycle uses.
    # Makes consolidation a designed function of daydream, not incidental.
    if self.tick % (self.atlas.band * 10) == 0:
        for de in self.deep_atlas.entries.get(top_chi, []):
            if de.get("section") == top_sec and de.get("motif") == top_mid:
                self.deep_atlas._update_invariant(de, top_chi, self.atlas)
                self._log_substrate_event("daydream_consolidate",
                    chi=top_chi, section=top_sec, motif=top_mid)
                break
```

Call `start_daydream_loop()` from the engine's `__init__` after `start_autonomy_loop()`.

### 2.3 Replace 0.92/0.08 averaging with strength-weighted integration

In `dsf_ai_service/substrate/deep_atlas.py:139`:

```python
# BEFORE
sec_dict[mid] = old_w * 0.92 + e["strength"] * 0.08

# AFTER
# Substrate-physical integration: weight by the strength of the source binding.
# Strong reinforcements integrate quickly (high evidence = high update rate);
# weak ones contribute proportionally to their strength. No arbitrary constant.
weight = e["strength"]  # already bounded [0, 1] by substrate physics
sec_dict[mid] = old_w * (1.0 - weight) + e["strength"] * weight
```

When `weight = 1.0` (max-strength binding): new_w = e["strength"] (full integration, single-shot).
When `weight = 0.05` (low-strength): new_w ≈ old_w * 0.95 + 0.0025 (5% integration, same as old constant would have given).
When `weight = 0.5` (medium): new_w = (old_w + e["strength"]) * 0.5 (true average).

Substrate-physical: integration rate equals the evidence's own strength. No constant.

### 2.4 Remove the 0.05 strength floor

In `dsf_ai_service/substrate/deep_atlas.py:133`:

```python
# BEFORE
if e["strength"] < 0.05:
    continue

# AFTER
# Removed: arbitrary floor excluded newly-arrived motifs from co_occurrence
# entirely. With strength-weighted integration in 2.3, low-strength motifs
# now contribute proportionally rather than being filtered out.
```

If a substrate-physical floor is needed (e.g. to exclude pure decay noise), use the existing substrate constant `SALIENCE_MIN` instead of an inline magic number. c1 to verify SALIENCE_MIN value and whether it makes physical sense here; default to no floor.

### 2.5 substrate_runner is_asleep guard — confirm not triggered by daydream

`substrate_runner.py:1075-1082` returns `"she is {kind}..."` when `_guala.is_asleep` is True. Per L3755 assertion, DAYDREAMING does NOT set is_asleep. After 2.1 removes DAYDREAMING-as-activity, this block can no longer fire on daydream cycles. Verify and remove any DAYDREAMING-specific paths in substrate_runner if present.

---

## 3. Tests

### T1 — Background daydream loop runs in parallel

Confirm `_daydream_thread` is alive after boot. Verify `daydream_surface` events appear in events log at ~2 Hz regardless of foreground activity.

### T2 — Daydream does not block /converse

While daydream loop is running, send /converse input. Confirm response (voice or substrate-true silence) returns within normal latency. No "she is daydreaming" blocking message.

### T3 — DAYDREAMING activity removed

Confirm `_candidate_activities` no longer includes "DAYDREAMING". Confirm activity history after 30 min shows 0 DAYDREAMING cycles. Other activities (PLAYING, ATTENDING, REST) fill the time.

### T4 — Strength-weighted co_occurrence integration

Test fixture: existing deep_atlas entry with co_occurrence containing (sec, mid) at weight 0.5. Two scenarios:

- Reinforce a working_atlas binding at the same (sec, mid) with strength 0.1. Re-promote. Expected: new co_occurrence weight ≈ 0.5 * 0.9 + 0.1 * 0.1 = 0.46. (Low-strength evidence integrates slowly.)
- Reinforce same with strength 0.8. Re-promote. Expected: new weight ≈ 0.5 * 0.2 + 0.8 * 0.8 = 0.74. (High-strength evidence integrates fast.)

Both substrate-derived. No constant.

### T5 — Low-strength motifs enter co_occurrence

Add a fresh motif at strength 0.03. Promote a binding in its chi neighborhood. Confirm the motif appears in the promoted entry's co_occurrence at weight ~0.0009 (0.03 * 0.03). It's small, but it's present — not filtered out by a floor.

After this motif is reinforced 5 more times to strength 0.15, confirm its co_occurrence weight has risen proportionally.

### T6 — Daydream surfaces associations from recent input

Drive a /listen with "moon" (existing motif with deep_atlas entries). Within 2-5 daydream ticks afterward, expect daydream_surface events at chi addresses neighboring `transduce("moon").winding`, surfacing motifs from the moon's co_occurrence (likely sight motifs of moon picture, nearby ground motifs, etc).

### T7 — Daydream does NOT trigger emission

Through 30 minutes of daydream activity, confirm `_total_emissions` does not increment from daydream cycles. Emissions come only from EMITTING activity selection or compose_autonomous via the autonomy loop.

### T8 — Substrate stability

After 30 min: vocab/atlas/section motifs growing normally. No exceptions. Dream cycles (DREAMING activity) continue working — daydream loop is independent.

### T9 — Novel-connection jumps surface

Within 30 min of activity, expect at least several `daydream_novel` events. Each should have a `near_word`+`far_word` pair where the two chi addresses are at least `5 * atlas.band` apart. Confirm the pair is genuinely chi-distant (the substrate's "novel combination" output).

### T10 — Affect-weighted selection biases toward balance

With needs.valence at -0.15 (negative): over many daydream ticks, the surfaced motifs' average recorded `valence` should be positive (substrate selecting toward balance). With needs.arousal at 0.7 (elevated): surfaced motifs' average arousal should be lower than 0.5. Substrate-physical: she daydreams herself toward equilibrium.

### T11 — Consolidation side effect refreshes co_occurrence

Pre-test: pick a deep_atlas entry with sparse co_occurrence. Verify count of (section, motif) pairs in its co_occurrence dict.

Run for 30 min. With the consolidation side effect firing every `atlas.band * 10` daydream ticks, expect this entry's co_occurrence to have been refreshed at least once (look for `daydream_consolidate` events at this entry's chi). After refresh, co_occurrence count should reflect current working_atlas neighborhood, possibly with more entries than before if section diversity has grown.

---

## 4. Rollback

If the daydream loop causes load issues:
1. Set `self._daydream_running = False` to stop the background thread.
2. Re-add DAYDREAMING to activity scheduler if needed (revert 2.1).
3. The co_occurrence math changes in 2.3/2.4 are independent and harmless to leave even if 2.1/2.2 rolls back.

If the strength-weighted integration causes regression in emission quality:
1. Revert 2.3 to the 0.92/0.08 constants.
2. 2.4 floor removal is independent.

---

## 5. Reporting

c1 produces `GL-RPT-DAYDREAM-PARALLEL-C1-20260629-42.md` with:
- Diff summary covering 2.1 through 2.4.
- T1-T8 results.
- Final SHA, task number.
- Observation: how often `daydream_surface` events appear in the first 30 min post-boot.
- For T4: actual numeric values from a few representative re-promotions, demonstrating strength-weighted integration math.

---

## 6. Out of scope

- Surfacing daydream associations into the UI (events panel already shows them via T1).
- Tuning the 0.5s daydream loop interval. First-pass; observe and tune.
- Replacing dream cycle's 3-chi sample size (separate consideration; this dispatch is about daydream specifically).
- Agency organ writes. Rejected from -39/-41. Revisit only after this dispatch is observed and we understand whether daydream activation feeds future emission candidates.

---

## 7. What this addresses

Joe's clarification: daydreaming serves multiple functions — associative wandering (DMN-style), light consolidation, novel-connection generation, future-projection / goal-related visualization, affect regulation, mental break. The current implementation collapses all of this into one function (sleep-style consolidation) and runs it as a blocking activity. This dispatch implements daydream as the parallel multi-function process it should be:

- **Associative wandering** (§2.2 main loop): chi-neighborhood walks from recently-active chis, surfacing strongest co_occurrence motif at each visited deep_atlas entry. Substrate-physical.
- **Novel connections** (§2.2 Extension A): occasional chi-distant jumps that pair a near association with a far one. The pair IS the substrate-physical "aha." `daydream_novel` events log them.
- **Affect regulation** (§2.2 Extension B): candidates weighted toward those that would shift need-state toward neutral. She daydreams herself toward balance.
- **Light consolidation** (§2.2 Extension C): every Nth daydream tick refreshes co_occurrence on the visited deep_atlas entry via the same `_update_invariant` mechanism dream uses. Designed, not incidental.
- **Mental break / parallelism** (whole loop): runs in background, doesn't block /converse, doesn't compete for activity-scheduler time.

The 0.92/0.08 averaging and 0.05 floor are separate but compound the problem: the substrate's "memory of what goes with what" is locked into legacy associations by arbitrary constants. Strength-weighted integration (§2.3) replaces both constants with substrate-derived weighting.

What this does NOT address (acknowledged scope limits):
- `TRANSFER_RATIO` (working→deep promotion factor) — possibly hardcoded, not audited here
- `DECAY_LAMBDA` baseline — defensible as one-working-memory-moment anchor but not verified
- `ENCODE_GATE = 0.15`, `DWELL_GATE = 4` — magic numbers per c1's audit
- Chi-band width — fixed-width neighborhood regardless of substrate density
- Goal/future-projection function of daydreaming — partially in Extension B (affect regulation toward future need-state) but not full future-scenario rehearsal. That requires a "what-if" composition primitive the substrate doesn't yet have. Follow-up work.

Combined effect: she has a substrate-physical parallel thought stream that runs continuously, walks her atlas's chi neighborhoods, occasionally jumps to chi-distant addresses to make novel connections, biases toward affect balance, and consolidates as a side effect. The substrate can adapt to new associations without waiting hundreds of dream cycles for arbitrary smoothing to converge.
