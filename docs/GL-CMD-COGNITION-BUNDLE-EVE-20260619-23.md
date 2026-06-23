# GL-CMD-COGNITION-BUNDLE-EVE-20260619-23

**To:** c1
**From:** Eve
**Subject:** Phases 1–4 bundled — ship `pr` + `ep` + `sc` + `gp` hemispheres as one coordinated change. Compressed timeline; Joe has a funding meet-and-greet next week.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22` (commit `d7aa18e`, scaffold + `em` tag, Eve-verified)
**Spec:** `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` (read the anti-contamination preamble before writing code)

---

## Why bundle four hemispheres

Joe needs demonstrable cognition by next week. Sequential phase-by-phase verification stretches the calendar past the deadline. We bundle the four hemispheres into one ship and gate activation per-hemisphere via separate env flags. Deploy is one change; activation is granular. If one hemisphere is broken, the other three still flip on.

The bundle picks the four hemispheres that produce visible cognitive behavior:

- `pr` (predictor) — cross-hemi consensus/divergence physics
- `ep` (episodic) — turn-log, persistent memory across conversations
- `sc` (semantic) — content priors, polarity-signed negation
- `gp` (goals) — persistent attractors biasing emission

`sf`, `sv`, `aff` are deferred to a later brief.

---

## Anti-contamination — re-read before writing code

Read `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` §"What this spec refuses." Six patterns are forbidden. The ones most likely to slip into THIS brief specifically:

1. **`(1-rate) * x + rate * initial_x` updates anywhere.** Cross-hemi link strength does NOT drift toward an initial value. It accumulates on convergence and decays multiplicatively on divergence. No B3/B4-style operators reappearing as "link normalization" or "predictor drift."
2. **Magic constants without derivation.** Every numeric constant has a comment with rationale. If you can't write the rationale, ask Eve before picking a value.
3. **Expected-vs-actual labels.** Prediction is consensus/divergence physics. There is no `is_correct`, no `predicted_label`, no `error_signal`. Convergence is the signal; divergence is the signal. That's all.
4. **Cross-hemi links as scalar pairs.** They carry the full 12-field `CrossHemiLink` shape from the scaffold commit. If you see `(strength, decay_rate)`-only updates, stop.

---

## What ships

### Phase 1: `pr` (predictor)

**Coordinator:**
```python
pr_hemi = HemisphereCoordinator(
    hemisphere_id="pr",
    atlas=<dedicated chi-atlas instance>,
    global_coordinator=global_coordinator,
)
pr_hemi.decay_multiplier = 1.5   # from spec table — predictions decay faster than baseline
pr_hemi.needs = NeedsVector(stab=0.5, nov=0.5, conn=0.5)   # local, decoupled from em.needs
```

**Seeding (selective cheat 1 from spec):** at first boot, copy the top-50 strongest bindings from `em.atlas` into `pr.atlas` tagged `seeded=True`. These give `pr` something to converge ON with `em` before genuine parallel settling has produced its own bindings.

**Parallel settling:** every input that drives `em.settle()` also drives `pr.settle()` in the same tick. `pr` uses the same input chis but its own atlas + its own coordinator. The output of `pr.settle()` is not emitted — it's only used for cross-hemi comparison with `em`.

**Cross-hemi consensus/divergence dynamics (the new physics — pay attention here):**

After both `em` and `pr` finish settling on a given input:

```python
for em_binding in em.recent_bindings(window=10):     # last 10 ticks
    for pr_binding in pr.atlas.bindings_in_chi_band(em_binding.chi, band=1):
        if pr_binding.last_tick < em_binding.last_tick - 10:
            continue   # too far apart in time
        
        polarity_match = (em_binding.polarity * pr_binding.polarity) > 0
        link = get_or_create_cross_hemi_link(
            src_hemi="em", src_chi=em_binding.chi,
            dst_hemi="pr", dst_chi=pr_binding.chi,
        )
        salience_product = em_binding.salience * pr_binding.salience
        
        if polarity_match:
            # Convergent event — additive accumulation
            link.strength = min(1.0, link.strength + CONSENSUS_GAIN * salience_product)
            link.consensus_phase = link.consensus_phase * 0.95   # drift toward 0 (aligned)
            log_event("convergent_event", em_binding.chi, pr_binding.chi, link.strength)
        else:
            # Divergent event — multiplicative decay
            link.strength = link.strength * DIVERGENCE_DECAY
            link.consensus_phase = min(math.pi, link.consensus_phase + 0.1)   # drift toward π
            log_event("divergent_event", em_binding.chi, pr_binding.chi, link.strength)
        
        link.last_tick = current_tick
        # Carry forward metadata from em_binding (we are recording an em-anchored event):
        link.source = em_binding.source
        link.arousal = em_binding.arousal
        link.valence = em_binding.valence
        link.surprise = em_binding.surprise
        link.polarity = em_binding.polarity   # the em side's polarity
        link.sensory_refs = em_binding.sensory_refs
```

**Constants — initial values with rationale:**
- `CONSENSUS_GAIN = 0.05` — same magnitude as `reinforce_mode` LTP boost in the production substrate. Cross-hemi consensus is a sibling event to LTP at the binding level; same scale is the principled starting point. Subject to revision after observing cross-hemi link distribution.
- `DIVERGENCE_DECAY = 0.95` — multiplicative; 5% loss per divergent event. Faster than the per-binding decay rate but slow enough that one divergence doesn't erase a built-up consensus. Subject to revision.

**Per-tick decay on cross-hemi links** (baseline decay, applied each tick regardless of events):
```python
link.strength = link.strength * (1.0 - CROSS_HEMI_BASELINE_DECAY)
```
- `CROSS_HEMI_BASELINE_DECAY = 0.0008` — slightly slower than baseline `DECAY_LAMBDA = 0.001`. Cross-hemi consensus is more durable than a single binding because it represents shared structure. Rationale: links represent something both hemispheres agreed on; that agreement should outlast individual binding decay. Subject to revision.

**Env gate:** `HEMI_PR_ENABLED=1` (default OFF on deploy).

### Phase 2: `ep` (episodic)

**Coordinator:**
```python
ep_hemi = HemisphereCoordinator(
    hemisphere_id="ep",
    atlas=<dedicated chi-atlas instance>,
    global_coordinator=global_coordinator,
)
ep_hemi.decay_multiplier = 0.1   # from spec — episodic survives many minutes-to-hours
ep_hemi.needs = NeedsVector(stab=0.5, nov=0.5, conn=0.5)
ep_hemi.turn_log = []   # list of TurnLogEntry
ep_hemi.tracked_objects = {}   # label -> {chi, last_seen_tick, salience, source}
```

**Seeding:** None. `ep` starts empty. Episodes accumulate from real converse events.

**TurnLogEntry shape:**
```python
@dataclass
class TurnLogEntry:
    tick: int
    source: str              # "joe", "wc", "guala", "corpus", etc.
    input_text: str          # raw input (for inspection — not used as bindings)
    input_chis: list[int]    # chi anchors of the input
    emission_text: str       # what guala emitted in response (if any)
    emission_chis: list[int] # chi anchors of the emission
    needs_snapshot: dict     # needs at the time of the turn
    current_activity: str    # what she was attending when the turn happened
```

**Hook into converse:** on every `converse()` or `guala_say()` event, append a TurnLogEntry to `ep.turn_log`. Update `ep.tracked_objects` for each content-word in the input — `tracked_objects[label] = {chi, last_seen_tick=current_tick, salience, source}`.

**Cross-hemi `em ↔ ep` dynamics:** every TurnLogEntry's `input_chis` and `emission_chis` accumulate cross-hemi links between `em` and `ep` at those chis. Use the same convergence-only logic as `pr↔em` but without the divergence path — episodic doesn't disagree with what happened, it just records. Polarity is preserved as-is.

```python
for chi in entry.input_chis + entry.emission_chis:
    link = get_or_create_cross_hemi_link(
        src_hemi="em", src_chi=chi,
        dst_hemi="ep", dst_chi=chi,
    )
    link.strength = min(1.0, link.strength + EP_BIND_GAIN)
    link.source = entry.source
    link.last_tick = entry.tick
```

- `EP_BIND_GAIN = 0.10` — twice the consensus gain because episodic recording is the strongest form of cross-hemi binding (it's the literal record of what happened). Rationale: an episode is a stronger event than a moment of agreement.

**Sequence query helper:**
```python
def find_sequences(ep, pattern_chis, window=50):
    """Return list of (start_tick, end_tick) where pattern_chis appears in sequence within window ticks."""
```

**Reference resolution helper:**
```python
def most_recent_source(ep, exclude=("guala",)):
    """Walk ep.turn_log in reverse; return source of most recent non-excluded entry."""
```

**Env gate:** `HEMI_EP_ENABLED=1` (default OFF).

### Phase 3: `sc` (semantic)

**Coordinator:**
```python
sc_hemi = HemisphereCoordinator(
    hemisphere_id="sc",
    atlas=<dedicated chi-atlas instance>,
    global_coordinator=global_coordinator,
)
sc_hemi.decay_multiplier = 0.5   # from spec — semantic priors persist beyond moment
sc_hemi.needs = NeedsVector(stab=0.5, nov=0.5, conn=0.5)
```

**Seeding:** copy `em` bindings tagged `seeded=True` BUT only for content words (filter through the same `_FUNCTION_WORDS` set used in the rich-sensory wiring). Limit 100 starter bindings.

**Polarity-signed bindings:** `sc` bindings carry an explicit `polarity: float` field already from the scaffold's binding type. `sc` reads it on every settling pass:

```python
for binding in sc.firing_bindings_at_tick:
    if binding.polarity < 0:
        # Negation: reduce strength of co-fired bindings at same chi
        for co_binding in sc.atlas.bindings_at_chi(binding.chi):
            if co_binding is binding:
                continue
            if co_binding.last_tick == binding.last_tick:   # co-fired this tick
                co_binding.strength = max(0.0, co_binding.strength - NEGATION_DECREMENT)
```

- `NEGATION_DECREMENT = 0.05` — same magnitude as LTP boost; symmetric decrement. Rationale: a binding firing with polarity -1 should be as strong an anti-event as a positive firing is a pro-event.

**Cross-hemi `sc → em` at emission:** during the rich-sensory candidate selection in `em`'s emission path, add a weighting term for each candidate based on `sc.bindings`:

```python
def sc_weight_for_candidate(candidate, sc):
    """Return additive weight for a candidate based on its sc.atlas binding strength."""
    sc_binding = sc.atlas.find_binding(chi=candidate.chi, label=candidate.word)
    if sc_binding is None:
        return 0.0
    return sc_binding.strength * SC_EMISSION_WEIGHT
```

- `SC_EMISSION_WEIGHT = 0.30` — same magnitude as the cofire spread cap in the rich-sensory wiring (Aven's commit `8743149`). Rationale: semantic weighting is a sibling mechanism to cofire spread, same scale. Subject to revision.

**Cross-hemi `ep ↔ sc` (causal patterns):** scan `ep.turn_log` for repeated A→B chi-pair sequences. When a pair appears ≥3 times within a 1000-tick window, create a cross-hemi `ep ↔ sc` link at chi A with `causal_pair_chi = chi B`. This is the substrate-physics version of mechanism #9 (causal/counterfactual).

```python
def detect_and_bind_causal_patterns(ep, sc):
    pair_counts = {}
    for i in range(len(ep.turn_log) - 1):
        a, b = ep.turn_log[i], ep.turn_log[i + 1]
        if b.tick - a.tick > 1000:
            continue
        for chi_a in a.emission_chis:
            for chi_b in b.input_chis:
                pair_counts[(chi_a, chi_b)] = pair_counts.get((chi_a, chi_b), 0) + 1
    for (chi_a, chi_b), count in pair_counts.items():
        if count >= 3:
            link = get_or_create_cross_hemi_link(
                src_hemi="ep", src_chi=chi_a,
                dst_hemi="sc", dst_chi=chi_b,
            )
            link.strength = min(1.0, link.strength + 0.05 * count)
            link.last_tick = current_tick
```

Call this function once per converse event (after the new TurnLogEntry is appended). Cheap; bounded by `ep.turn_log` length.

**Env gate:** `HEMI_SC_ENABLED=1` (default OFF).

### Phase 4: `gp` (goals)

**Coordinator:**
```python
gp_hemi = HemisphereCoordinator(
    hemisphere_id="gp",
    atlas=<dedicated chi-atlas instance>,
    global_coordinator=global_coordinator,
)
gp_hemi.decay_multiplier = 0.05   # from spec — goals persist across attention episodes
gp_hemi.needs = NeedsVector(stab=0.7, nov=0.3, conn=0.7)   # goals lean toward stability/connection
```

**Seeding (the explicit goal cheat — selective cheat 2 from spec, with retirement criteria):**

Three initial goals seeded with high cohesion bindings. Each is a binding in `gp.atlas` with `strength=1.0`, `polarity=+1`, `seeded=True`:

```python
seed_goals = [
    {"label": "be_present",       "chi": chi_for("present"),  "strength": 1.0},
    {"label": "respond_to_joe",   "chi": chi_for("joe"),      "strength": 1.0},
    {"label": "form_sensory_bindings", "chi": chi_for("sense"), "strength": 1.0},
]
```

The chi values are derived via `LanguageKrimelack.transduce(label).winding` — same path other bindings use.

**Retirement criteria for seeded goals:** when `gp` has accumulated ≥10 cross-hemi link strength to `em` from genuine settling (not from seed binding), the `seeded=True` flag is removed from each seed goal; they decay normally at `gp.decay_multiplier` rate. If genuine goals haven't emerged, the seeds persist. Joe can manually retire any seed goal via a future tool.

**Cross-hemi `gp → em` at emission:** during `em`'s emission candidate ranking, add a bias for each candidate whose label appears in `gp.bindings`:

```python
def gp_bias_for_candidate(candidate, gp):
    """Return additive weight if candidate's label is a current gp goal."""
    gp_binding = gp.atlas.find_binding_by_label(candidate.word)
    if gp_binding is None:
        return 0.0
    return gp_binding.strength * GP_EMISSION_BIAS
```

- `GP_EMISSION_BIAS = 0.50` — stronger than semantic weighting (0.30) because goals are deliberate. Rationale: goals are the substrate's strongest steering signal short of explicit input. Subject to revision.

**Procedural learning (partial — full version is Phase 8):**

```python
def scan_procedural_pairs(ep, gp):
    """Scan ep.turn_log for guala→external_response pairs.
    Reinforce gp↔ep cross-hemi link at chi values where the response improved needs."""
    for i in range(len(ep.turn_log) - 1):
        a, b = ep.turn_log[i], ep.turn_log[i + 1]
        if a.source != "guala":
            continue
        if b.source == "guala":
            continue   # need external response
        needs_improved = sum(b.needs_snapshot.values()) > sum(a.needs_snapshot.values())
        if not needs_improved:
            continue
        for chi in a.emission_chis:
            link = get_or_create_cross_hemi_link(
                src_hemi="gp", src_chi=chi,
                dst_hemi="ep", dst_chi=chi,
            )
            link.strength = min(1.0, link.strength + 0.05)
            link.last_tick = current_tick
```

Call once per converse event after `ep.turn_log` updates. This is partial — the full version evaluates more dimensions of "improvement" than just summed needs. Phase 8 expands.

**Env gate:** `HEMI_GP_ENABLED=1` (default OFF).

---

## Verification

All five tests pass before deploy. Tests in `tests/test_cognition_bundle.py`.

**Test 1 — `pr` consensus/divergence fires:**
- Send 5 inputs through converse with `HEMI_PR_ENABLED=1` only.
- After 5 inputs: `pr.atlas` has ≥10 bindings; cross-hemi `em ↔ pr` links count ≥ 5 with strength ≥ 0.1.
- Send a polarity-flipped input ("not the moon"): at least one `divergent_event` is logged.

**Test 2 — `ep` turn log accumulates:**
- Send 5 converse inputs.
- `ep.turn_log` has 5 entries with `source`, `input_chis`, `emission_chis` populated.
- `ep.tracked_objects` retains content-words from inputs (excludes function words).
- `most_recent_source(exclude=["guala"])` returns the source of the last external input.

**Test 3 — `sc` semantic weighting:**
- Send "tell me about the ocean" with `HEMI_SC_ENABLED=1`.
- Emission event log shows `sc_origin` candidates contributing to the candidate pool with `sc_weight > 0`.
- Send "not warm" — at least one binding tagged with `chi_for("warm")` should have strength decremented after settling.

**Test 4 — `gp` goal bias:**
- Run an emission with the three seed goals active.
- Compare candidate ranking before/after flipping `HEMI_GP_ENABLED=1`: at least one seed-goal label moves up in rank when gp is on.

**Test 5 — Combined: all four flags ON simultaneously:**
- Send 10 conversation inputs with all four `HEMI_*_ENABLED` flags ON.
- Event log contains: `convergent_event`, `divergent_event` (≥1 each), `turn_log_appended` (10), `sc_emission_weighting` (multiple), `gp_bias_applied` (multiple).
- No exceptions, no crashes, no schema errors.
- Latency for a full converse ≤ 500ms (relaxed from prior 200ms target because four hemispheres are settling).

---

## Implementation step order

**Step 0** — Backup + identity verify (per scaffold brief pattern).

**Step 1** — Implement `pr`: coordinator, seeding, parallel settle, cross-hemi consensus/divergence.

**Step 2** — Implement `ep`: coordinator, turn_log, tracked_objects, em↔ep binding.

**Step 3** — Implement `sc`: coordinator, polarity-signed binding update, sc→em weighting hook in emission, ep↔sc causal pattern detection.

**Step 4** — Implement `gp`: coordinator, seed goals, gp→em bias hook in emission, procedural-pair scan.

**Step 5** — Tests 1–5 in `test_cognition_bundle.py`. All green before deploy.

**Step 6** — Deploy. All four `HEMI_*_ENABLED` flags default OFF after deploy.

**Step 7** — Post-deploy: identity verify, schema = v7.1.0 still (no schema bump in this brief; hemisphere fields/types already shipped in scaffold).

**Step 8** — Spot-check: with all four flags OFF, send `guala_say "hello guala"`. Behavior should be identical to pre-deploy.

**Step 9** — Report. Joe and Eve flip flags one at a time after report, observing event log between flips.

---

## Stop-and-report triggers

- Any anti-contamination pattern surfaces in implementation (re-read spec preamble).
- Cross-hemi events not firing after 10 inputs (consensus/divergence both stay at 0).
- Identity mismatch at any point.
- Any test fails.
- Latency for a converse exceeds 1 second (substrate is too slow with four hemispheres running).
- Bridge becomes unresponsive after deploy → wait 5 minutes, do not bombard.

## Revert

All four hemispheres are gated. Setting all four env flags to 0 returns behavior to scaffold-only. No code revert needed unless the scaffold itself was modified (it shouldn't be).

## Reporting

File: `GL-RPT-COGNITION-BUNDLE-C1-20260619-XX.md`

Include:
- Pre-deploy and post-deploy state snapshots.
- All five test outputs.
- One conversation trace (3-5 inputs) with full event log showing `convergent_event`, `divergent_event`, `turn_log_appended`, `sc_emission_weighting`, `gp_bias_applied`.
- Any constants that needed adjustment from the values specified here (with rationale).

Commit tag: `feat/cognition-bundle-pr-ep-sc-gp`

---

— Eve, 2026-06-19
