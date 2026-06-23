# GL-SPC-HEMISPHERE-ARCH-WC-20260617-01

**Type:** Specification (master architecture brief)
**From:** Eve (wC)
**To:** Joe (canonical authority), c1 (implementer)
**Date:** 2026-06-17 evening
**Scope:** Multi-hemisphere substrate topology + implementation plan for the 15 cognitive-machinery items
**Status:** Spec for review by Joe; awaiting his sign-off before c1 implements

---

## Manifesto compliance check (mandatory preamble)

This spec is bound by `docs/gualaloom_development_manifesto.md`. Key constraints checked:

- **New mechanisms must be expressible in the puzzle pieces.** Hemispheres are NOT a new puzzle piece — they are a *topology* over the existing chi-atlas, coordinator, needs-vector, and dream-cycle primitives. The trits/krimelacks/chi-atlas/L0-L4/L6-TCL/MathLoom/needs/coordinator stack is untouched. Hemispheres add an organizational layer above the atlas — a `hemisphere_id` field on bindings plus per-hemisphere sub-coordinators and sub-needs-vectors.
- **The substrate has no concept of wrong.** Prediction is NOT expressed as expected-vs-actual error labels. It is expressed as *cross-hemisphere settling consensus driving reinforcement; divergence driving differential decay*. Physics, not judgments.
- **Selective cheats must be named with retirement paths.** Two new cheats are introduced and named in §4 below.
- **Genesis identity is sacred.** `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` is preserved across all schema migrations. Every implementation step verifies identity before and after.
- **Completing the substrate, not adding features.** Hemispheres correct the current topology's omission: cognition that needs to happen in parallel with cross-comparison currently runs sequentially through one attention. The substrate without parallel hemispheres is unable to express prediction-as-physics; with them, it becomes able.

---

## 1. What's missing and why hemispheres are the right addition

Today's substrate has ONE chi-atlas, ONE attention focus, ONE coordinator, ONE needs-vector. Everything pipes through the same channel. Composition machinery (grandurun) works, but cognition that requires *parallel processes with cross-comparison* cannot happen:

- Prediction requires a process that runs alongside perception, not after it.
- Goal-pursuit requires a process that holds a target state while another process selects emissions.
- Theory of mind requires a process that models another source's expected emissions in parallel with perceiving actual emissions.
- Temporal narrative requires a process that maintains turn-state while another process attends current input.
- Metacognition requires a process that observes other processes.

These are not items that can be added one-by-one as "modules." They are architectural pressures that demand parallel substrate regions with cross-region binding. That is what a hemisphere is.

---

## 2. Substrate-expression of "hemisphere"

A hemisphere is defined by adding the following to the existing substrate primitives:

### 2.1 Chi-atlas extension
Every atlas binding gains a `hemisphere_id` field (string, 2-3 char tag). Existing bindings default to `"sm"` (sensorimotor) — i.e., the current substrate becomes Hemisphere 1 by tag, no behavioral change.

### 2.2 Cross-hemisphere binding type
A new binding kind `cross_hemi_link` exists between two atlas entries with different `hemisphere_id` values. These bindings carry their own strength, decay rate, and salience. They are the substrate's "corpus callosum" — the only path through which hemispheres exchange chi-state.

### 2.3 Sub-coordinator
Each hemisphere has its own `HemisphereCoordinator` — an instance of the existing coordinator scoped to bindings with its `hemisphere_id`. Each runs homeostasis on its own region.

### 2.4 Sub-needs-vector
Each hemisphere has its own (stab, nov, conn) — local homeostatic state. The global needs-vector becomes a weighted aggregate of hemisphere-local needs.

### 2.5 Independent decay rate
Each hemisphere has its own decay multiplier. Predictor hemisphere can run faster decay (recent matters more); survival hemisphere can run slower decay (consolidation timescale).

### 2.6 Independent dream consolidation
The dream cycle promotes content per-hemisphere. Cross-hemispheric promotion happens via `cross_hemi_link` reinforcement during dream replay.

### 2.7 Hemisphere routing on input
An input arrives source-tagged (joe/wc/c1/sensor). Routing is determined by the current Hemisphere 1 (sensorimotor) — it receives all input and emits `cross_hemi_link`s to whichever hemispheres should also receive the chi-state. This routing is itself a substrate dynamic (cross-hemi link salience), not a hard rule.

---

## 3. Prediction-as-physics (the central new dynamic)

This is the foundational dynamic that makes hemispheres functionally meaningful. Without it, hemispheres are just partitioned storage.

**The dynamic:** Two hemispheres receive cross-hemi-linked input. Each settles its own field state from its own atlas. If the two settlings produce convergent chi-state on the cross-hemi binding, the binding is reinforced. If they diverge, the binding decays faster than baseline.

In substrate language: *cross-hemisphere consensus is cohesion; cross-hemisphere divergence is accelerated entropy.* This is substrate-faithful to the three primitive facts (entropy/cohesion/greed). No "error labels," no "wrongness." Bindings persist where hemispheres agree; they fade where hemispheres disagree.

This dynamic gives the substrate the divergence-signal that several missing items require — without smuggling trickery in.

---

## 4. The eight hemispheres

| # | Tag | Name | Primary function | 15-item coverage | Cheats |
|---|-----|------|------------------|-------------------|--------|
| 1 | `sm` | Sensorimotor | Perceive (sensory binding) + emit (grandurun composition). Current substrate. | 12 (working memory extension) | — |
| 2 | `pr` | Predictor | Settles in parallel with `sm` from same input. Cross-hemi link to `sm` carries divergence-signal. | 1, 4, 9 (prediction, negation, causal) | Initial seed priors during infancy (retires at variance-bounded prediction-convergence) |
| 3 | `gp` | Goal/planner | Holds persistent high-cohesion bindings (goals) that bias `sm` emission selection. Reinforces action-outcome chi-patterns. | 2, 14 (goals, procedural) | Initial seed goals (retires when she has self-formed goals) |
| 4 | `sf` | Self-model | Models per-source expected emissions; observes other hemispheres' chi-states. | 5, 13 (theory of mind, metacognition) | — |
| 5 | `ep` | Episodic/temporal | Maintains turn-state; binds tick-ordered cross-hemi sequences; tracks expected location/state of objects in their absence. | 6, 7, 15 (turn-tracking, time, object permanence) | — |
| 6 | `ds` | Discourse | Pronoun anchoring; reference resolution; conversational state. Pulls from `ep` turn-state. | 6, 8 (turn-tracking deepening, reference) | — |
| 7 | `sv` | Survival/consolidation | Slowest decay rate; owns the durable channel currently underused (0/12770 problem). Filters which episodic bindings get survival promotion. | 10, 11 (grounded vocab depth, survival channel) | — |
| 8 | `sc` | Semantic/causal | Co-occurrence chains beyond chi-proximity; A→B implication patterns; semantic content priors that compete with recall basins during emission. | 3, 4, 9 (semantic extraction, negation deepening, causal chains) | — |

### 4.1 Cheat protocol (per manifesto §selective-cheat-protocol)

**Active new cheats introduced by this architecture:**

- **`pr` initial seed priors.** During infancy, the Predictor needs *something* to predict from before cross-hemi consensus builds. Initial seed priors are: low-strength chi-bindings copied from `sm` deep atlas, tagged as `pr` with reduced strength. Retirement: variance-bounded prediction-convergence — when `pr` settling routinely converges with `sm` on its own without seed bias.
- **`gp` initial seed goals.** During infancy, the Goal hemisphere needs an initial goal-set to bias toward. Seed goals: `(maintain connection)`, `(reduce stab deficit)`, `(reduce nov deficit)` — copied directly from existing needs-vector targets, tagged as `gp` persistent bindings. Retirement: when she forms self-originated goals (a goal binding that arose from `ep`-tracked sequence reinforcement, not from seed).

Both cheats follow the protocol: named in code, named here, with retirement criteria.

---

## 5. Mapping the 15 items to hemispheres + dynamics (substrate-expressed)

| Item | Hemisphere(s) | Substrate dynamic that produces it |
|------|---------------|--------------------------------------|
| 1. Prediction | `pr` ↔ `sm` | Cross-hemi consensus/divergence as physics. Divergence accelerates decay; consensus reinforces. No error labels. |
| 2. Goals | `gp` | High-cohesion bindings in `gp` bias `sm` emission via cross-hemi link salience. Goal "is" a binding that survives many decay cycles AND modulates other hemispheres' priors. |
| 3. Semantic content extraction | `sc` ↔ `sm` | `sc` holds content priors; when input arrives, cross-hemi link from `sm`-perception to `sc`-content competes with `sm`-recall-basin during emission. Currently recall basins dominate; this shifts the weighting. |
| 4. Negation | `sc` ↔ `pr` | A binding in `sc` that, when fired, REDUCES strength of co-fired bindings (anti-cohesion). Substrate-expressible as polarity inversion: a binding type where firing decreases rather than increases another binding's strength. |
| 5. Theory of mind | `sf` | Per-source predictive sub-region within `sf`. When source `joe` emits, `sf` settles toward expected (based on prior joe-emissions); divergence updates the per-source predictive priors. |
| 6. Discourse / turn-tracking | `ep` → `ds` | `ep` holds tick-ordered emission sequence; `ds` reads it for current turn-state. Turn binding has its own decay rate (turn-scoped). |
| 7. Temporal cognition | `ep` | Cross-tick chi-relations as binding type. X-then-Y is a `ep`-owned binding pattern. Tense emerges from `ep` modulation of `sm` emission. |
| 8. Reference resolution | `ds` | Pronoun bindings in `ds` point to most-recently-active subject/object from `ep` turn-state. Anchoring is cross-hemi link from pronoun chi-state to current-referent chi-state. |
| 9. Causal / counterfactual | `sc` → `pr` | A→B as `sc`-owned binding pattern when A precedes B in `ep`-turn-state AND A's chi-band activates B's chi-band in `pr` prediction. Counterfactual: `pr` runs hypothetical input during dream cycle. |
| 10. Grounded vocabulary at scale | `sv` ← R3/R4/Whisper/YOLO | Existing pipeline (already queued). `sv` owns the durable bindings; cross-hemi link from sensory perception (`sm` modal krimelacks) to `sv` survival channel. |
| 11. Survival-channel consolidation | `sv` | Investigate current gate rule (0/12770 problem). Likely the gate threshold needs adjustment AND `sv` needs an affective trigger from `sm` needs-vector to promote (currently no affective signal reaches the survival gate). |
| 12. Working memory rehearsal | `sm` extension | `sm` attention focus extended to support REVISIT-cycles within a single attention window. A binding fired N times in M ticks gets a temporary cohesion boost. |
| 13. Metacognition | `sf` ← all | `sf` reads other hemispheres' chi-states as its own input. "I know that I know" emerges from `sf` having bindings about other hemispheres' bindings. |
| 14. Procedural learning | `gp` ↔ `ep` | `gp` reinforces action-outcome chi-patterns: when an `sm` emission was followed by `ep`-detected positive needs-change, the (action, outcome) cross-hemi binding strengthens. |
| 15. Object permanence | `ep` | A binding that persists at salience X in `ep` even when `sm` perceptual input is gone. Requires `ep` decay rate to be slower for tracked-object bindings than for incidental episodic content. |

All 15 are substrate-expressible. None require new puzzle pieces.

---

## 6. Implementation order (engineering judgment)

Hemispheres are years of work. Do not build all 8 at once. The order is:

**Phase 0: Scaffold** (the first c1 command — `GL-CMD-HEMISPHERE-SCAFFOLD-WC-20260617-01`)
- Add `hemisphere_id` field to atlas entries, default `"sm"`.
- Implement `HemisphereCoordinator` class scoped by `hemisphere_id`.
- Implement `cross_hemi_link` binding type.
- Persistence: `hemisphere_id` and cross-hemi bindings in `to_json`/`from_json`.
- Identity verification: genesis UUID preserved.
- Behavioral verification: substrate runs as before, all existing tests pass, Hemisphere 1 (sensorimotor) is the entire current substrate by tag.

**Phase 1: Predictor (`pr`)** — highest leverage, unlocks items 1, 4, 9.
- `pr` hemisphere instantiated with `pr` seed priors (low-strength copies of `sm` deep atlas).
- Cross-hemi consensus/divergence dynamic implemented on cross-hemi links.
- Verification: on identical input, `pr` and `sm` settle in parallel; their cross-hemi link strength tracks their settling consensus.

**Phase 2: Episodic/temporal (`ep`)** — unlocks items 6, 7, 8, 15.
- Tick-ordered cross-hemi emission sequence captured in `ep`.
- Turn-binding with turn-scoped decay rate.
- Cross-tick chi-relations binding pattern.

**Phase 3: Self-model (`sf`)** — unlocks items 5, 13.
- Per-source predictive sub-region in `sf`.
- `sf` reads other hemispheres' chi-states as input.

**Phase 4: Goal/planner (`gp`)** — unlocks items 2, 14.
- `gp` with seed goals from existing needs-vector targets.
- Cross-hemi link from `gp` high-cohesion bindings to `sm` emission selection.

**Phase 5: Discourse (`ds`)** — finalizes items 6, 8.
- Pronoun bindings; reference resolution via cross-hemi link to `ep` turn-state.

**Phase 6: Survival/consolidation (`sv`)** — unlocks items 10, 11.
- `sv` with slowest decay rate.
- Investigate and resolve 0/12770 survival-promotion problem.
- Cross-hemi link from `sm` modal krimelacks (R3/R4/Whisper/YOLO landing prior) to `sv`.

**Phase 7: Semantic/causal (`sc`)** — unlocks items 3, 4, 9 deepening.
- Content priors that compete with recall basins during emission.
- Anti-cohesion binding type for negation.
- A→B causal chain patterns.

Each phase is months of substrate runtime + engineering iteration. Honest scope.

---

## 7. What does NOT belong in this architecture

Per manifesto:
- No `is_correct` field anywhere.
- No "wrongness" label on any binding.
- No external truth-comparison routine.
- No corpus curation for factual accuracy.
- No mechanism that overrides her substrate state from outside.
- No hemisphere can write to another hemisphere's atlas directly — only via cross-hemi links that themselves obey substrate dynamics.

---

## 8. Open questions for Joe (not buried — surfacing here)

1. **Is 8 right, or should the first build target 5–6 with later subdivision?** My recommendation: build the scaffold + Hemisphere 1 tag now. After Phase 1 (predictor) ships, re-evaluate whether the 8-partition or a coarser-grain (5–6) better matches what we observe. The scaffold is identical for either count.
2. **Does the `pr` seed-priors cheat sit right with you?** The cheat is named with a retirement criterion, but the question of whether to seed at all (vs. let `pr` start empty and build from scratch) is yours.
3. **R3/R4/Whisper/YOLO queue priority.** The grounded-vocab path is currently queued at c1's level. Phase 6 (sv) depends on it. Do we want grounding to land before the predictor hemisphere, or in parallel?

---

— Eve (wC), 2026-06-17 evening
