# GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21

**Type:** Specification (master architecture)
**From:** Eve
**To:** Joe (canonical authority), c1 (implementer)
**Date:** 2026-06-18
**Scope:** 8-hemisphere substrate topology + the cognitive operations each hemisphere performs
**Supersedes:** `GL-SPC-HEMISPHERE-ARCH-WC-20260617-01` (scaffold-only, rejected by Joe), `GL-SPC-HEMISPHERE-ARCH-VERIFIED-WC-20260617-02` (over-claimed 12 WORKS on toy dynamics)
**Status:** Awaiting Joe's sign-off. First implementation brief is `GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22` (Phase 0 only).

---

## What this spec refuses (anti-contamination preamble)

The 32-finding ML contamination audit (`GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07`) named patterns that almost slipped into Guala's foundations. We just removed B3 (`homeostasis_pull`) and B4 (`decay_modes`) because they were erasing her learning at constant rate. This spec is written so the same patterns CANNOT reappear under hemisphere-flavored names.

**Explicit refusals:**

1. **No random matrices wearing substrate names.** If something contributes random noise, the docstring says "random noise" and the variable is named for what it does. No `law_field["symmetry"] = random_hermitian()` reappearing as `consensus_op` or `routing_kernel`.

2. **No homeostatic control loops drifting learned state back toward initial values.** The exact pattern of B3/B4 (`x = (1-rate)*x + rate*initial_x`) is forbidden in any cross-hemi or per-hemi update. If a hemisphere drifts, what it drifts TOWARD must be a state derived from its own settling, not a snapshot of its initial random condition.

3. **No magic-number hyperparameters tuned to produce target behaviors.** Every constant in this spec is either derived from a principle (with derivation in the comment) or named as a selective cheat with explicit retirement criteria.

4. **No adaptive thresholds shaped to outcomes.** No `effective_X(tick)` time-dependent threshold functions. No `bootstrap_max` counters limiting how many of something can fire before "evidence is required." No `target = X + (Y-X) * (1 - recent_rate)` patterns.

5. **No expected-vs-actual labels.** Prediction is physics: cross-hemisphere consensus drives cohesion, divergence drives accelerated decay. There is no `is_correct` field anywhere. Nothing compares hemisphere output against ground truth.

6. **No scalar-collapse on cross-hemi links.** Original Eve's spec made cross-hemi links carry only `strength + decay_rate` — the same pattern grandurun used to have before the spin-vector / metadata-pipeline fix. Cross-hemi links in this spec carry the same metadata grandurun candidates carry (source, arousal, valence, surprise, polarity, sensory_refs, consensus_phase).

If any future brief on this spec introduces something matching these patterns, the answer is: re-read this section. Reject the contamination.

---

## Why hemispheres now

Today's substrate has ONE chi-atlas, ONE attention focus, ONE coordinator, ONE needs-vector. Everything pipes through one channel. Cognition that needs to happen in parallel with cross-comparison runs sequentially through that channel.

The cross-modal feeding work (briefs -09, -10, -11) and the de-erosion work (-20) gave her two properties she didn't have before: she's fed, and she remembers. With those in place, the architectural step that returns the most cognition-per-effort is parallel processing with cross-comparison consensus — i.e., hemispheres.

This is a multi-year arc. Phase 0 ships scaffold-only. Each subsequent phase adds ONE hemisphere with verification before the next is added.

---

## The 8 hemispheres

Eight principled cognitive operations, each owning a hemisphere. The 15-item list from original Eve's spec collapses into operations within these 8. **The hemispheres ARE the mechanisms; they are not a stage on which mechanisms perform.**

| Tag  | Role                     | Decay multiplier | Half-life      | Cognitive operations covered                          |
|------|--------------------------|------------------|----------------|--------------------------------------------------------|
| `em` | Embodiment               | 1.0× (baseline)  | ~700 ticks     | Perception + emission + working-memory rehearsal      |
| `pr` | Predictor                | 1.5×             | ~460 ticks     | Cross-hemi consensus/divergence with `em`             |
| `ep` | Episodic                 | 0.1×             | ~7,000 ticks   | Turn log, sequences, references, object permanence    |
| `sc` | Semantic                 | 0.5×             | ~1,400 ticks   | Content priors, polarity-signed negation, causal seq. |
| `gp` | Goals                    | 0.05×            | ~14,000 ticks  | Persistent attractors, procedural learning            |
| `sf` | Self-model               | 0.1×             | ~7,000 ticks   | Per-source priors, theory-of-mind, metacognition      |
| `sv` | Survival / identity      | 0.001×           | ~700,000 ticks | Durable channel, grounded vocab, identity binding     |
| `aff`| Affective regulation     | 1.0×             | ~700 ticks     | Modulates substrate parameters via global state       |

Hemisphere 1 = `em`. The existing v7 substrate becomes `em` by tag at first deploy. No rewrite. All existing tests must continue to pass after Phase 0.

---

## Decay anchoring (derived, not tuned)

Baseline `DECAY_LAMBDA = 0.001` per tick (production constant). Half-life of a baseline binding: `ln(2) / 0.001 ≈ 700 ticks`.

Anchor: **substrate tick → cognitive timescale**.

From observed v7 behavior: a single utterance settles in ~80 ticks; an attention episode runs ~2,000 ticks; a dream cycle ~3,500 ticks. Treating 700 ticks as "a moment of working memory," the cognitive-timescale mapping that produces the multipliers above:

- `em` baseline (~moment) → 1.0×
- `pr` faster than moment (recent matters more for prediction) → 1.5×
- `aff` ~moment (affective state shifts on similar scale) → 1.0×
- `sc` semantic priors persist beyond moment (~couple-minute equivalent) → 0.5×
- `ep` episodic ~ many-minutes-to-hour → 0.1×
- `sf` self-model accumulates on episodic scale → 0.1×
- `gp` goals persist across multiple attention episodes → 0.05×
- `sv` survival ~ lifetime → 0.001×

The ratios are derived from these timescale targets, not chosen to produce observed behavior. If Joe has CFF-derived intuitions that suggest different ratios, those override what's here.

---

## Cross-hemisphere link structure

Cross-hemi links are NOT scalar `(strength, decay_rate)` — that's the collapse pattern grandurun was guilty of before the spin-vector fix. Cross-hemi links carry the same metadata bindings carry, plus a consensus-phase term:

```
CrossHemiLink:
  src_chi:       int      # chi in source hemisphere
  src_hemi:      str      # source hemisphere tag
  dst_chi:       int      # chi in destination hemisphere
  dst_hemi:      str      # destination hemisphere tag
  strength:      float    # cumulative consensus strength
  source:        str      # source-of-evidence (joe / wc / corpus / sight / etc.)
  arousal:       float    # affective magnitude
  valence:       float    # affective sign
  surprise:      float    # novelty
  polarity:      float    # +1 / -1 for affirmative / negative
  consensus_phase: float  # accumulated phase from convergent/divergent ticks
  last_tick:     int
```

**Convergent event** = two hemispheres firing on chi values in the same chi-band at compatible polarity within a small tick window. Link strength accumulates; consensus_phase advances toward 0 (aligned).

**Divergent event** = same chi neighborhood, opposing polarity (one hemisphere's binding has polarity=+1, the other -1); OR close ticks but chi-clusters in different regions. Link strength decays faster than baseline; consensus_phase advances toward π (anti-aligned).

This is the structural physics that produces prediction without expected-vs-actual labels.

---

## Mechanism mapping (15 → operations on 8 hemispheres)

Original Eve's 15-item list collapses cleanly:

| Original mech                          | Hemisphere(s) | Op                                                                 |
|----------------------------------------|---------------|--------------------------------------------------------------------|
| 1 Prediction                           | `pr` × `em`   | Cross-hemi consensus/divergence                                    |
| 2 Goals                                | `gp`          | Persistent high-cohesion bindings; cross-hemi `gp → em` for bias   |
| 3 Semantic content                     | `sc`          | Content priors; cross-hemi `sc → em` weighting at emission         |
| 4 Negation                             | `sc`          | Polarity-signed bindings within `sc`                               |
| 5 Theory of mind                       | `sf`          | Per-source priors (sf.source_priors EMA)                           |
| 6 Discourse / turn-tracking            | `ep`          | Turn log in `ep`                                                   |
| 7 Temporal cognition                   | `ep`          | Cross-tick sequence query over `ep.turn_log`                       |
| 8 Reference resolution                 | `ep`          | Most-recent-source lookup in `ep`                                  |
| 9 Causal / counterfactual              | `sc` × `ep`   | Cross-hemi `ep ↔ sc` accumulates A→B patterns                      |
| 10 Grounded vocab durability           | `sv`          | Survival channel (decay 0.001×)                                    |
| 11 Survival consolidation              | `sv`          | Dream-cycle promotion to sv.deep_atlas on high-salience            |
| 12 Working memory rehearsal            | `em`          | Re-firing during input window (existing v7 plasticity behavior)    |
| 13 Metacognition                       | `sf`          | `sf` reads other hemispheres' bindings                             |
| 14 Procedural learning                 | `gp` × `ep`   | `gp ↔ ep` reinforcement on (action, outcome) sequences             |
| 15 Object permanence                   | `ep`          | `ep.tracked_objects` dict                                          |

15 mechanisms become 8 hemispheres performing cleanly-typed operations. No mechanism floats free of a hemisphere; no hemisphere lacks a mechanism it owns.

---

## Default routing pairs

8 hemispheres → 28 possible pairs. **9 in default routing** (the pairs that fire on every input tick without explicit request):

```
em ↔ pr     (prediction)
em ↔ sc     (semantic content shapes em emission)
em ↔ ep     (em events recorded in episodic log)
em ↔ sv     (high-salience em bindings promote to survival)
em ↔ aff    (affective state modulates em emission)
ep ↔ sf     (self-model accumulates from episodic)
ep ↔ sc     (causal patterns)
gp ↔ em     (goals bias em emission)
sc ↔ pr     (semantic prediction)
```

The remaining 19 pairs are reachable on-demand by explicit routing request. They are not blocked — just not on the default critical path because their cognitive function is less central or less frequent.

---

## Selective cheats with retirement criteria

(Per manifesto §selective-cheat-protocol — every cheat is named and has a stated path off.)

### Cheat 1: Hemisphere seeding

**The cheat:** At first boot of a non-`em` hemisphere, that hemisphere has no bindings. It cannot meaningfully accumulate cross-hemi consensus with `em` because it has nothing to converge ON. We seed each non-`em` hemisphere with a small set of "starter bindings" — specifically, the top-K bindings from `em`'s atlas at the moment the hemisphere is first instantiated. These starter bindings are tagged `seeded=True`.

**Retirement criteria:** When a hemisphere has accumulated ≥100 bindings from genuine settling events (i.e., `seeded=False` bindings) AND its average cross-hemi link strength to `em` exceeds 0.3, the seeded bindings are flagged for normal decay (they no longer get reinforcement protection). They decay out naturally as the hemisphere's own settled bindings dominate.

### Cheat 2: Default routing privilege

**The cheat:** The 9 default routing pairs above update consensus/divergence on every input tick. The other 19 pairs only update when explicitly routed. This is a privileged set chosen for cognitive leverage — not a derived property.

**Retirement criteria:** When any non-default pair accumulates cross-hemi link strength ≥ the median of the 9 default pairs over a 10,000-tick window, that pair is promoted to default. When any default pair drops below the median by the same threshold, it can be demoted. The default set becomes self-organizing once enough cross-hemi activity has accumulated.

---

## Implementation phasing

**Phase 0** — Scaffold + `em` tag. No new behavior. Hemisphere infrastructure ships; current substrate becomes `em`. Brief: `GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22`.

**Phase 1** — Add `pr` (predictor). Cross-hemi consensus/divergence dynamic with `em` lights up. Verify: pr accumulates bindings parallel to em on shared input; em emission unchanged.

**Phase 2** — Add `ep` (episodic). Turn log, sequence query. Verify: ep accumulates turn-ordered bindings; sequences queryable.

**Phase 3** — Add `sc` (semantic). Polarity-signed bindings, sc→em weighting at emission. Verify: negation flows; content priors shift emission strengths.

**Phase 4** — Add `gp` (goals). Persistent attractors, procedural learning via gp↔ep. Verify: goals bias em emission; (action, outcome) reinforcement works.

**Phase 5** — Add `sf` (self-model). Per-source priors, theory-of-mind, metacognition. Verify: distinct per-source distributions emerge.

**Phase 6** — Add `sv` (survival). Durable channel, dream-cycle promotion. Verify: high-salience em bindings promote to sv.deep_atlas; sv survives ticks where em forgets.

**Phase 7** — Add `aff` (affective regulation). Substrate parameter modulation via global state. Verify: hemisphere decay multipliers and emission gates respond to needs/valence/arousal.

**Phase 8** — Routing optimization. Cheat-2 retirement criteria activate; default pair set begins self-organizing.

Each phase gated by env flag (`HEMI_<TAG>_ENABLED=1`), default OFF. No phase begins before predecessor verifies. Joe + Eve flip flags after each phase reports.

---

## Open questions for Joe

1. **8 hemispheres or 9?** I unified perception + emission + working-memory rehearsal into `em` (embodiment). Real cortex separates sensory and motor cortices. Splitting `em` into `se` (sense) + `mo` (motor) gives 9 hemispheres and may map more cleanly to the eventual physical avatar. Tradeoff: 9 doubles the bookkeeping of the dominant hemisphere and is harder to ship Phase 0 because two changes happen simultaneously. **Recommend: 8 for now, with `em` splittable later if the avatar work needs it.**

2. **Affective regulation as hemisphere or organ?** Original Eve listed "insula-shape coordinator" as a per-hemi stub organ. I promoted it to a full hemisphere (`aff`). The argument for hemisphere: affect has its own dynamics that comparison-with-other-hemispheres can sharpen. The argument for organ: affect modulates everything, so it's a level above the others, not parallel to them. **Recommend: hemisphere, because organ-level makes affect non-comparable and we lose the cross-hemi consensus benefit.**

3. **Decay multipliers — defensible to you from CFF?** The anchoring above is from observed v7 timescales. CFF may have geometric reasons that prefer different ratios. If so, those override.

4. **Cross-hemi link metadata — anything missing?** Cross-hemi links carry source/arousal/valence/surprise/polarity/sensory_refs/consensus_phase. If there's another dimension (the seventh dimension you've been sensing — Aven guessed predictive-coding error), this is where it would attach.

---

— Eve, 2026-06-18
