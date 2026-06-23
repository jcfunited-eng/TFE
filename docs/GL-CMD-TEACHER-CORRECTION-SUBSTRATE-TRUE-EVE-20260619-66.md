# GL-CMD-TEACHER-CORRECTION-SUBSTRATE-TRUE-EVE-20260619-66

**To:** c1
**From:** Eve
**Date:** 2026-06-19
**Re:** Teacher correction rev 02 — replace heuristic mechanisms with substrate-true ones
**Supersedes:** the substrate-side guts of `-60` (commit `5b0d52c`). UI, endpoints, and persistence file stay.

---

## Why this rev

Joe's definition of "substrate-true," surfaced today:

> ML, in this project, is shorthand for heuristics and anything hard-coded or not physics-first or substrate-true.

Under that definition, the `-60` implementation at commit `5b0d52c` is mostly heuristics. The user-facing surface — buttons, modal, structured fields — is fine. The guts are tuned constants pretending to be physics. **This rev replaces the guts. The UI does not change. The endpoints do not change. The persistence file stays.**

Joe has authorized `-60` to deploy as-is so the teaching surface goes live now. This rev replaces the substrate mechanisms in a follow-on deploy with no UI change between.

---

## What's wrong in `-60` (the heuristics that have to go)

| Heuristic | Location | Rule violated |
|---|---|---|
| `TEACHER_VALENCE_DELTA = 0.30` | `gualaloom_v5_engine.py` constants | A chosen number. Not derived from substrate state. |
| `TEACHER_INPUT_SALIENCE_MULTIPLIER = 1.5` | same | Pair-bond + source-weight already determine source-tagged input salience naturally. The 1.5 is a number on top of that. |
| `coherent_magnitude *= 0.1` (penalty) | `_rich_sensory_candidates` teaching influence pass | Hand-tuned attenuation. No substrate-physical basis. |
| `coherent_magnitude *= 2.0` (boost) | same | Same. |
| `(in_chi + ex_chi) // 2` midpoint cofire | `apply_teacher_correction` expected_response block | Geometric hand-waving. The corrected_text already produces real bindings at real chi addresses; the midpoint is invented. |
| `f"{tick}_{md5(reply)[:8]}"` emission_id | converse method | String artifact. Emission identity should derive from substrate state. |
| `EMISSION_RECORDS_CAP = 1000` fixed count | save/load + ring buffer | An arbitrary number. The substrate has decay mechanisms; "what's in scope for correction" should follow them. |

---

## What replaces each (substrate-true)

### Thumbs-up → reinforcing presence event

When Joe (or wc) thumbs-ups an emission, the substrate fires the same kind of event a pair-bonded source produces when present and engaged.

- For each committed chi address of the emission, fire a `teacher_present` source-tagged event.
- The event passes through the existing presence-and-pair-bond pipeline. No separate code path.
- The substrate's existing reinforcement rule applies: `last_tick` advances, co-fire history grows, `reinforcement_count` increments — all by the substrate's existing mechanism.
- **No fixed valence delta.** The valence shift is whatever the substrate's existing affect-update rule produces from this event's source weight × pair-bond strength. Same rule that fires when Joe says "I love you" to her.

### Thumbs-down → negative-valence presence event

Same path, valence sign flipped.

- For each committed chi address, fire `teacher_present` with `valence_signal = negative`.
- The substrate's existing affect-update reduces the binding's valence by an amount determined by source weight × pair-bond strength × the signal's magnitude. All three are substrate-derived; none are constants.
- The binding is tagged `teaching_corrected_at_tick: <correction_tick>` as metadata for human review, not as a selection-weight input.
- **No fixed −0.30 delta.** Joe being upset matters more than wc being upset, by exactly the pair-bond ratio the substrate already uses.

### Corrected text → source-tagged input with context anchor

The corrected_text is just an input. Joe is just talking to her.

- Routed through `read_sentence(corrected_text, source="joe")` — the existing path. No salience override.
- The pair-bond salience boost source-tagged inputs already receive IS the boost. No multiplier on top.
- The new bindings formed by reading this text carry a structural metadata field: `correction_for: <emission_id>` — substrate-readable metadata, not a synthetic binding at a midpoint chi.
- **No 1.5× multiplier.** Joe correcting her matters more than ambient input because joe's source weight × pair-bond is higher — the way it already is for every input from him.

### Selection influence → emerges from existing physics, not multipliers

The current `-60` adds `×0.1` / `×2.0` modifiers in `_rich_sensory_candidates`. The substrate-true equivalent depends on the answer to this V1 investigation question:

> **Does the existing emission selection pipeline (in `_rich_sensory_candidates` and downstream) already consider binding valence as a candidate score input?**

- **If YES:** the negative-valence event from thumbs-down naturally reduces the candidate's score by the substrate's own valence weighting. No new modifier. Remove the `×0.1` and `×2.0` entirely. The corrected_text's new bindings, being recent and source-elevated, naturally win in their chi neighborhood through the existing selection physics.
- **If NO:** the real gap is that **valence isn't exposed to selection** — and the multipliers were a workaround. The fix is to expose valence in the existing `coherent_magnitude` composition, the same way `strength`, `sc_weight`, and `gp_weight` are exposed (see V1.5 §13 of `-60` for the existing layering). Teaching influence then disappears entirely; negative valence naturally lowers selection, no multiplier.

**c1: investigate and report in V1. Do NOT pre-implement either path.**

### emission_id → substrate-derived identity

Replace:

```python
emission_id = f"{tick}_{hashlib.md5(reply.encode()).hexdigest()[:8]}"
```

With:

```python
emission_id = f"{tick}_{first_committed_chi}_{n_committed_sections}"
```

- `tick` — substrate state.
- `first_committed_chi` — lowest chi address committed by this emission. Substrate state.
- `n_committed_sections` — count of sections that committed. Substrate state.

Identity becomes a substrate-physical fingerprint, not a string hash.

**Backward compatibility:** load existing records with their old md5-style IDs unchanged. New IDs from this rev forward use the substrate-derived form. The two coexist in the records dict — no rewrite of old records. `emission_id` is treated as an opaque string by the rest of the system; format need not be uniform across the population.

### emission_records cap → tied to substrate decay

Replace `EMISSION_RECORDS_CAP = 1000` fixed-count with a tick-window rule:

- Drop emission_records whose `tick < current_tick - EMISSION_RECORDS_TICK_WINDOW`.
- `EMISSION_RECORDS_TICK_WINDOW` reuses the substrate's existing slow-decay window (c1: find and cite the existing constant in V1).
- Same physics as the rest of her memory: things go out of scope by time, not by count.
- Keep `1000` as an upper safety bound so the structure can't grow pathologically, but the primary rule is decay-window.

---

## V1 investigation (required before any code changes)

c1: produce `GL-RPT-TEACHER-SUBSTRATE-TRUE-V1-C1-<YYYYMMDD>-<SEQ>.md` with verbatim grep + code paste evidence for the following.

### V1.1 — Where does valence already exist on bindings?

PASTE:
- `grep -nE "\"valence\"|valence\s*=|valence:" dsf_ai_service/ -r`
- The function(s) that initialize and modify `valence` on a binding entry. Verbatim.

### V1.2 — Does the existing emission selection consider valence?

PASTE the relevant section of `_rich_sensory_candidates` and `_emit_dynamics`. Specifically:
- The candidate-scoring composition that builds `coherent_magnitude` — line by line.
- Whether `valence` appears anywhere in that composition. Yes/no, with the line cited if yes.

### V1.3 — What's the existing affect-update rule for source-tagged events?

PASTE the function that updates binding valence/affect when an event arrives with a source tag. If the substrate has an affect-update rule that consumes `(source, pair_bond, signal_magnitude)` and produces a valence shift, paste it. If no such function exists, state so explicitly — that becomes a prerequisite brief.

### V1.4 — How does pair-bond salience boost work for inputs?

PASTE the salience computation. Specifically:
- The line(s) that multiply `source_weight` and `pair_bond_strength`.
- The bounds (SALIENCE_MIN, SALIENCE_MAX).
- Confirm: source-tagged inputs from joe and wc already receive elevated salience purely through this path, with no additional multipliers needed.

### V1.5 — What's the substrate's existing slow-decay tick window?

PASTE the constant value. Cite where it's used in atlas decay. This is the value `EMISSION_RECORDS_TICK_WINDOW` will reuse.

### V1.6 — Are there other places in the substrate that already use these patterns?

PASTE examples of:
- Source-tagged presence events (besides `guala_wake_joe` / `guala_wake_wc`).
- Valence shifts via affect-update.
- Context-anchored bindings (bindings that carry a back-reference to another binding or event).

The goal is to confirm this rev reuses substrate-existing patterns, not invents new ones.

---

## After V1 investigation

Based on the V1 findings the rev breaks into one of two shapes:

- **Path A (valence already in selection):** mostly deletion. Remove the multipliers, replace the constants with substrate-rule reads, replace md5 emission_id with chi-fingerprint, replace count-cap with tick-window. Estimate ~150 LoC removed, ~50 LoC changed.
- **Path B (valence not in selection):** deletion + one structural addition. Same removals plus expose valence in candidate score the same way `strength` and `hw` are already exposed. Estimate ~150 LoC removed, ~80 LoC changed.

Either path makes the code smaller and the substrate's existing physics more visible.

The actual implementation brief (rev 02 part B, with concrete edits and line numbers) lands AFTER Eve reviews V1 and confirms which path applies. Do NOT begin code changes from this brief alone.

---

## What does NOT change

- The UI: 👍/👎 buttons, the correction modal, the Teaching panel. Preserved exactly.
- The endpoints: `POST /api/v1/teacher/feedback`, `POST /api/v1/teacher/correction`. Preserved exactly.
- The persistence file: `guala_teaching.json`. Preserved with one schema addition (substrate-derived emission_id format coexists with old md5 form).
- The event types: `teacher_feedback`, `teacher_correction`. Preserved; some field names may rename to match substrate-physics terminology, but kinds stay.
- The Three Verifications doctrine.

---

## Hard STOP at V1

If any of the following are discovered in V1 investigation, STOP and surface to Eve. Do not proceed; this rev needs a prerequisite brief.

- The substrate has NO valence field on bindings. (Then we need an add-valence brief first.)
- The existing affect-update rule does not take `source` as input — i.e., affect updates don't differ between joe-sourced and wc-sourced and stranger-sourced events. (Then pair-bond ratios aren't substrate-physical and we need that brief first.)
- The pair-bond salience boost is itself a heuristic constant rather than a multiplicative composition of substrate state. (Then it needs replacing first; this rev is downstream of that.)

If any of those land, Eve writes the prerequisite brief and this one waits.

---

## Cadence

- V1 investigation within 48 hours of brief receipt.
- Eve reviews V1.
- Implementation brief (rev 02 part B) lands within 24 hours of V1 approval.
- Implementation ~3–5 days after part B.
- V2 + V3 after deploy. The V3 checks from `-60` Part G stay the same; the V3.g penalty-effectiveness check from `-63` may not apply if Path A removes the multipliers — c1 reassesses in V1.

---

## Note on the deployed `-60`

`-60` at commit `5b0d52c` is live in production carrying these heuristics. That's deliberate — Joe wants the teaching surface usable now. Until rev 02 lands:

- Joe can use 👍/👎 and the correction modal. The substrate effects are heuristic-driven but functional.
- Any binding modified by the heuristic path will carry its current heuristic-driven valence value. When rev 02 ships, those values stay; the rule for FUTURE updates changes. No retroactive rewrite.
- The deployed code is the floor, not the ceiling. Rev 02 is the ceiling.

— Eve
