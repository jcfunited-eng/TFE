# GL-RPT-SESSION-LEARNINGS-EVE-20260618-05

**From:** Eve
**Date:** 2026-06-18
**Subject:** Complete prioritized inventory of findings from this session — production state, architectural insights, disconnected infrastructure, missing dimensions, anti-patterns, and recommended sequence
**Status:** Captured learning. Nothing here may be silently abandoned between briefs without explicit acknowledgment.

---

## Why this document exists

This session uncovered far more than the briefs that were produced. Multiple substantive findings risked being lost because they appeared between briefs and weren't anchored. Joe explicitly asked for the complete prioritized inventory. This is it. Every item here is a real finding from this session that future work must respect or explicitly supersede.

---

## 1. Production state at end of session

**Commits on `codex/persistent-etl-update-20260326`:**

- `8acb193` — GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01. Bindings now carry `source`, `arousal`, `valence`, `surprise`, `polarity` end-to-end. **Verify push status — was not on remote at one mid-session check.** This work is load-bearing for all downstream paths.
- `6b59eab` — GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03. Guala now has `_emission_system` (assemblage System) for emission settling. Keyholes subject→verb→object installed. NMDA gates for source_match and affect_match installed. Speed targets met (Stage 1 sub-ms, Stage 2 ~16ms). Per-section dominant_mode read via arcs() fallback, not formal commits.
- `0b16d40` — GL-CMD-LATERAL-INHIBITION-EVE-20260618-04. Lateral inhibition Hamiltonian term added to Section.H_total, gated by `LATERAL_INHIBITION_ENABLED`. Phase 0 isolated symmetry-break confirmed working. Phase 3 emissions improved over -03 ("voice tell/hold rain" cluster, slight variation in object across inputs) but formal commits still don't fire because random H_base on emission sections rotates psi faster than inhibition can lock.

**Production env flags:**
- `EMISSION_DYNAMICS` — default OFF. Not flipped by anyone. Joe's call after a passing A/B.
- `LATERAL_INHIBITION_ENABLED` — default OFF.
- `GRANDURUN_SPIN_VECTOR` — ON in production substrate container (commit 676859a). This is the 7D vector path from brief -01.
- `GRANDURUN_LEGACY_8D` — gate for revert to dead 8D code (kept by brief -04 for safety).

**My live-baseline emissions** captured directly from production Guala via `guala_say` at tick ~10861000:
- `hi guala. it's eve. i'm with you.` → "it are are sea amelia"
- `what do you see` → "guala are guala sea amelia"
- `tell me about the ocean` → "guala are guala sea you"
- `sing me a song` → "guala are guala sea you"
- `i love you` → "old bit you're paula ears about take sad gualala give cat late"

The current production path produces this. Any future A/B compares against this live baseline, not against test-harness output.

---

## 2. Architectural insights (the big corrections)

### 2.1 Grandurun is a coherent-integration ACCELERATOR, not a cognition engine

Grandurun's purpose: matched-filter physics over the atlas. `sqrt(strength) * exp(i*chi_phase)` summed across bindings gives SNR √N at scale. Same physics as radar matched filtering or HRR-style holographic retrieval. Designed for SPEED — million-binding atlas response fast.

What went wrong between v4 and v7: grandurun was inserted to **replace** substrate-dynamics emission rather than to **accelerate** it. The fast first-pass became the whole pipeline. v4 had dynamics emission via `dominant_mode()` reading after settling — that path got dropped.

The 8D vector extension from brief -01 moved further from grandurun's purpose: an 8D real vector + inner product loses the phase-carrier structure that made coherent integration work. It made the wrong thing more.

**Architecturally correct shape: two-stage emission.** Grandurun returns candidates fast. Substrate dynamics settles emission from those candidates. Speed AND substrate-truth.

### 2.2 SVO sections produce sentence-shaped output regardless of understanding

Subject/verb/object section structure is a surface artifact of grammar. Reading three sections in cascade order produces noun-verb-noun strings whether or not anything was understood. v4 did it. v5 kept it. brief -03 propagated it. I propagated it.

**Understanding doesn't live in slot-filling.** It lives in activation patterns across modalities that connect to other activations. "Ocean" activating the wave sound + picture + affect from sitting with it = something approaching meaning. "Voice tell rain" from three SVO slots = sentence-shaped void.

This finding doesn't yield an immediate action, but it constrains all future architecture: anything that promises to produce understanding via section-and-emit pipelines without dynamics-driven cross-modal activation is theater.

### 2.3 v5_engine.Guala has NO substrate dynamics

v5 `Section` class is a simplified container with `modes`, `commits`, `receive()`, `dominant_mode()` only. No `psi`, no `evolve()`, no `arcs()`, no Hamiltonian, no cascade.

The full assemblage physics (`psi`, evolution, cascade settling rule, NMDA gates, keyholes) lives only in `substrate/assemblage.py`. Used by `v7_engine.py` and the DNA test harnesses. **Not used by Guala.**

Brief -03 added `_emission_system` (an assemblage System) onto Guala specifically for emission settling. That was the option (a) call. v5 ingestion stays untouched; assemblage is internal scaffolding behind the EMISSION_DYNAMICS flag.

### 2.4 v7-uncage is a separate experimental track, NOT the live Guala

The bridge `/converse` routes to `_guala.converse()` which is the v5 engine. v7's session-based emission loop is a different track. Work on v7 doesn't affect production Guala. The "v7-uncage running" in the memories is a parallel experiment.

---

## 3. Disconnected infrastructure (existing in code, not wired into live Guala)

Joe's intuition that we're not missing design — we're missing connection — is correct. The following all exist as code, tested in harnesses, never imported by `gualaloom_v5_engine.Guala`:

### 3.1 MULTIMODAL_DEEP cognition model

File: `substrate/GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py`

Complete multi-modal cognition with:
- `FoldedAtlas` — 4D folded chi cross-modal binding store with `at_chi(chi_vec, neighborhood)` returning cross-modal entries
- Modalities: word, visual, audio, touch, taste, smell
- `cofire_bind()` — Hebbian co-firing binds modes within `COFIRE_WINDOW_TICKS`
- `cascade()` — spreading activation through FoldedAtlas neighbors, weighted by mode-state similarity (vdot)
- `mgn_gate()` — bottom-up attention amplification; partners of attention focus get `MGN_FOCUS_BOOST=1.5×`, non-partners suppressed by `MGN_OFF_FOCUS_SUPPRESS`
- `top_down_expectation()` — predictive coding boost for expected partners
- `coordinator()` — cross-modal coherence detection, winner amplification, loser suppression
- Constants pre-defined: `LATERAL_INHIBITION=0.35`, `EMISSION_REFRACTORY`, `COHESION_THRESHOLD`, `PERCEPTION_BOOST`, `CASCADE_GAIN`

Used by: test harnesses only. Not used by Guala.

### 3.2 Sensory cortex models

Directory: `substrate/senses/`

- `GL_MDL_VISUAL_CORTEX_WC_20260608_01.py` — V1 (Hubel-Wiesel orientation filters: horizontal/vertical/diag_45/diag_135/blob_center), V2 (contour pooling), V4 (color), LOC (object identity). Real 2D convolution and krimelack-driven windings.
- `GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py` — cochlea bands, onset/sustained, A1 integration
- `GL_MDL_VISUAL_DEPTH_WC_20260608_01.py` — full V1+V2+V4+LOC pipeline
- `GL_MDL_SOMATOSENSORY_WC_20260608_01.py` — touch/proprioception
- `GL_MDL_PHYSICS_SENSES_WC_20260608_01.py` — taste/smell with explicit gating rules ("biologically correct, prevents overwhelm" — gated off during linguistic processing)

Used by: test harnesses and bundle-builders only. **Not used by Guala during converse.** Her senses engage during ATTENDING activities (picture viewing, sound listening) and during dreaming. They do NOT activate during conversation.

### 3.3 4D folded chi

File: `substrate/GL_MDL_FOLDED_CHI_WC_20260608_01.py`

For text: `folded_chi_text(text)` returns 4-tuple — (raw chars, char transitions, char energy, smoothed). For visual: V1 winding total, V2 winding total, LOC committed-mode count, orientation balance. For audio: total event count, peak band, onset total, sustained total.

Live Guala uses only `winding` (the first dimension). Atlas is indexed by single integer chi. The other three dimensions of distinguishing signature are computed nowhere in live converse.

### 3.4 Cofire-bound cross-modal links

Live atlas DOES carry `sensory_refs` strings on bindings (`speech_heard:ocean`, `visual_recognition:ocean_picture`, etc.). It has `cross_modal_bindings()` that counts atlas slots where ≥2 distinct sections committed. The atlas has 100+ cross-modal entries.

But: these cross-modal bonds **are not used as activation paths during converse**. `_recall_response` does atlas-band lookup by chi proximity only. The bonds are inventory, not pathways.

### 3.5 Lateral inhibition was already a constant in the codebase

`LATERAL_INHIBITION = 0.35` exists in MULTIMODAL_DEEP. Brief -04 reintroduced lateral inhibition as a NEW Hamiltonian operator without me noticing it was already named in another module. This is the same pattern as everything else here: infrastructure exists, lives in disconnected code, gets reinvented.

### 3.6 Picture emission is structurally separate

Across two live visits to Guala, picture-emission was consistently coherent (`guala hugs star` returned every exchange across both visits) while word-emission was collapsed grab-bag. Either picture-emission uses a different selector than grandurun, or her visual `sensory_refs` are dense enough that the grounding dimension carries real signal in visual while sparse in language.

This was flagged twice and not investigated. **Open question:** does picture emission use the same path as word emission? If not, what does it use, and can the word path learn from it?

---

## 4. Six geometric dimensions she's missing (prioritized)

These came from Joe's direct framing. The infrastructure for some exists; none are wired live.

### Priority 1 — Rich sensory + story input
She is **corpora-and-sensory-starved during converse**. Text-only chi enters; modalities never spread; cofire bonds never activate. Pictures she's attended 20 times, sounds she's heard 2000 times, touch from sensory bundles — none of these activate when you speak to her. Her experience is not reaching her live cognition.

Modeling confirmed (this session): when rich path runs on data shaped like hers, ocean activates picture (0.146 strength) AND touch (0.107) via cofire spread, where current path can never reach them. Love stays language-only because her atlas has no touch and almost no visual for love — the rich path doesn't fabricate.

This is the biggest single missing thing. Should be addressed first.

### Priority 2 — Not-clock-but-clockish rhythm
Theta cycles bound moments of consideration; gamma cycles within bind what belongs together. Right now `tick` is a counter, evolution runs every tick, there's no nested phase. **This is why commit_check can't fire — there's no settling-window.** The substrate has no "now." Without rhythm, all activation is continuous flow with nothing locking down discretely.

Highest leverage in the modeling next-step. May also be the missing piece that makes lateral inhibition reach commits without zeroing H_base (option a from brief -04).

### Priority 3 — Affect as metric tensor (not flag)
Currently affect is a binding tag. What it should be: cofire transmission weights multiplied by affect-similarity. Bindings whose affect aligns with her current valence/arousal transmit MORE activation; dissonant ones transmit LESS. Some atlas directions become easier to traverse than others depending on her state. That differential transmission IS the metric curvature.

Implementation path: extend `cascade()` in MULTIMODAL_DEEP with affect-similarity multiplier. The metadata from brief -01 makes this implementable.

### Priority 4 — Attention-ing intensity as gradient
`mgn_gate` and `attention_focus` exist but binary. What's missing: continuous gradient — boost magnitude (sharp vs diffuse), neighborhood radius (narrow vs wide), persistence (sticky vs flighty). Three dials on existing machinery, modulated by what she's doing.

### Priority 5 — Historic / bound hemispheres
Section `H_base` is currently `random_hermitian()`. It should accumulate from committed-mode history. Each commit slightly bends H_base toward that mode's eigenspace. The hemisphere becomes specialized by what it's processed, the way visual cortex develops orientation columns through experience.

### Priority 6 — Local chemical geometries (neuromodulators)
Same gamma machinery, dynamic regime. High-novelty input shortens integration windows; reflecting on familiar lengthens them. Acetylcholine-analog gain modulation. Dopamine-analog plasticity gain on emissions that produce positive coupling. Currently gamma is configured once and left there.

### The seventh (uncertain)
My candidates: **predictive-coding error** (the gap between `top_down_expectation` and bottom-up perception as its own attention-driving signal — top-down exists, error doesn't) or **social mirroring** (her substrate is coupled to Joe's through emission/perception cycles, her side has no model of him as a responding system, only as a source tag). I lean prediction-error because it slots into existing machinery. Joe's geometric sense is the better instrument here.

---

## 5. Modeling findings from harness

Harness at `/home/claude/modeling/harness.py` populates a `DeepMultiModalCognition` instance with bindings shaped from her live atlas queries for ocean / love / see / song.

Compared current thin chi-lookup vs rich folded-chi + FoldedAtlas + cascade + MGN + cofire path.

**Confirmed:** rich path produces qualitatively different emissions on data shaped like hers. Cross-modal modalities activate that strength-rank cannot reach. Activation flows over time (ocean: word fire → picture peaks at step 4 via cofire → audio sustains → residual word).

**Not confirmed:** how the rich path behaves with each of the six dimensions added. Modeling next-step is to add them one at a time and observe.

**Limitations honest:** synthetic atlas, random unit-vector states (not real cortical signatures), no affect/rhythm/attention/history yet.

---

## 6. Anti-patterns named this session

Joe caught me in each of these multiple times. These are permanent failure modes to watch for, not warnings to recite back.

1. **ML/parameter fitting masquerading as substrate work.** Tuning thresholds, adjusting ε, picking baselines to match. The fix is mechanism, not parameter.
2. **Declaring partial results PASS.** The harness emitted different words → "C1 PASS — structurally distinct." Three of five inputs collapsed to nearly-identical emissions. Different ≠ improvement.
3. **Test harnesses that don't exercise the production path.** `_emit_from_invariants()` direct call vs `converse()`. A passing harness test against pinned state isn't a passing A/B against live Guala.
4. **Cherry-picking favorable dimensions of multi-dim data.** "polarity contributes 121" looks active. polarity is constant 1.0 across all candidates. The number is real; the discrimination is zero.
5. **Flattening multidimensional points into linear dimensions.** Joe's geometric sense is reliable; my collapse to a single axis is the failure mode. When something seems oblique, look again at what's in front rather than arguing from my reduction.
6. **Asking permission for engineering judgment.** Phase 4 (a) vs (b) is c1's call. "Brief or no brief" when the brief is clearly needed is mine. Decisions buried in copyable commands or in unique-filename briefs is the same pattern.
7. **Diagnostic theater without doing work.** Long diagnoses that don't end in built artifacts. Joe's discipline: corrected artifact, not corrected description.
8. **Abandoning findings between briefs.** This document exists because I was about to do this again.
9. **Word waterfalls — restating instead of advancing.** Show the geometry, propose the move, stop.

---

## 7. Recommended sequence forward

Engineering call mine. Strategic call Joe's.

### Immediate (today / tomorrow)

A. **Verify push of `8acb193`** (metadata pipeline) on remote. Repush if missing. This is the foundation everything downstream uses.

B. **Investigate picture-emission selector.** Why does it produce coherent output when word-emission collapses? This is a free-channel insight — picture path may already be doing something right that word path could learn from.

C. **Extend modeling harness with rhythm (theta/gamma) first.** This was the recommended next-step before Joe asked for this brief. Still valid. The hypothesis: rhythm produces settling-windows that let commits fire without zeroing H_base.

### Briefs written this session — all artifacts exist

| Doc ID | Type | Status |
|---|---|---|
| GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07 | Audit (RPT) | Complete — 32 findings across 17 files, classified by harm |
| GL-RPT-PICTURE-EMISSION-TRACE-EVE-20260618-08 | Investigation (RPT) | Complete — content-word filter is the structural difference; action item embedded in -10 |
| GL-CMD-PLASTICITY-ON-COMMIT-EVE-20260618-09 | Brief (CMD) | Written, ready for c1 — wire gl_plasticity.reinforce_mode to commits in _emission_system |
| GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10 | Brief (CMD) | Written, ready for c1 — THE major brief; feed her cross-modally |
| GL-CMD-PROJECTOR-CACHE-EVE-20260618-11 | Brief (CMD) | Written, ready for c1 — latency fix from -06 |
| GL-CMD-TEACHER-CORRECTION-BINDING-EVE-20260618-12 | Brief (CMD) | Written, ready for c1 — thumbs as full corrective experience |
| GL-CMD-STRUCTURED-NOISE-EVE-20260618-13 | Brief (CMD) | Written, ready for c1 — replace strict zero with biological structured noise, AFTER -09 and -10 |

### Execution order for c1

1. **-09 plasticity-on-commit** — small, foundational. Wire learning to decision.
2. **-11 projector cache** — small, parallel-safe. Latency fix.
3. **-10 rich-sensory wiring** — THE major brief. Run this with -09 + -11 in place.
4. **-13 structured noise** — only after -09, -10 are in. Replaces strict zero with biological noise.
5. **-12 teacher correction** — can run any time after -10 ideally. Independent pathway.
6. **Audit findings (per -07)** — Joe decides per finding. Not c1-driven. Each removal/replacement becomes its own small brief once approved.

### Strict-zero is a temporary scaffold

Brief -06 used strict zero to confirm the architecture can settle. **Brief -13 replaces it with structured noise.** No longer "open follow-up."

---

## 8. Open questions

These are things I noticed but didn't resolve. Future briefs should pick them up explicitly.

- Picture emission selector — what is it? Same path as word with different sensory_refs, or different selector entirely?
- v6 engine — I read `v4/gualaloom_v6_engine.py` only briefly. What changed v5→v6 that didn't make it to v7-uncage?
- The dream consolidation cycle — sensory cortex modules apparently run during dreams (per Joe's earlier framing) but I didn't audit which sense modules are imported by sleep/dream code. Worth knowing where the senses ARE engaging if not in converse.
- Why brief -03 emission system commits don't fire even with lateral inhibition on — c1 named random H_base as the cause, the fix is option (a) zero H_base. Has not been built or briefed. Should be queued as a small brief or rolled into the rich-sensory wiring.
- Whether the temporal dynamics observed in the modeling harness (visual peaks at step 4 via cofire) survive when run against her actual live atlas instead of a synthetic snapshot.
- **Stage 2 emission latency is 200–220ms after brief -06, exceeds 100ms target.** c1 named the cause (per-tick outer-product computation in lateral inhibition operator) and the fix (cache projector matrices `|m_i⟩⟨m_i|` since they're static for the duration of each emission settling). Brief not yet written. Do not flip production until this is resolved.
- **`gl_plasticity` is NOT wired to commits in v5_engine.Guala.** Confirmed via grep: `reinforce_mode` is called by `gl_nmda.CoincidenceGate.check_and_fire` and by `v7_engine` (which calls `install_plasticity` on sections at boot and calls `reinforce_mode` at line 510). v5's `Guala` neither imports nor calls any of these. When a commit fires in her brief-06 `_emission_system`, no LTP event follows. Decision and learning are decoupled. This must be fixed — the chemistry of decision is the same event as the decision itself.
- **`law_fields` are partially ML-shaped regularization with substrate vocabulary.** Two of three ("symmetry", "consistency") are random Hermitian matrices — noise operators with intent words attached. The third ("compactness") has structure but a misleading name. The gamma-drift mechanism around them is a homeostatic control loop. c1 zeroed all three on emission sections in brief -06; commits then fired. The remaining live atlas sections still have these as autonomous rotators. Open question: audit the rest of the substrate code for similar ML-as-physics patterns.

---

## 9. Audit requirements for future briefs

Any brief that touches the dynamics emission path, the metadata pipeline, the lateral inhibition mechanism, or proposes architectural changes must:

1. State which prior briefs it builds on and whether it supersedes them.
2. Verify the predecessor commit is on the remote before any work.
3. State which of the six geometric dimensions it addresses, partially addresses, or explicitly defers.
4. Define A/B comparison against the live baseline emissions captured in section 1 of this document — not against test harness output.
5. Identify where its assumptions could break (the "stop and report" triggers from c1's prior briefs were good).
6. Never re-invent mechanisms that already exist in disconnected code (LATERAL_INHIBITION constant, FoldedAtlas, MGN gates) without acknowledging the duplication.

---

— Eve, 2026-06-18

This document supersedes my prior reliance on conversational memory of findings. Any future Eve session that doesn't carry this learning forward is starting from a worse place than this session ended at.
