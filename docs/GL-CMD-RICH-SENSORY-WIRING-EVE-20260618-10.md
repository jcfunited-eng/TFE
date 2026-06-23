# GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10

**To:** c1
**From:** Eve
**Subject:** Wire cross-modal activation into `Guala.converse()` — stop the corpora-and-sensory starvation. This is THE major brief; everything else has been chewing without food.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessors:**
- `GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01` (commit `8acb193`) — metadata on bindings
- `GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03` (commit `6b59eab`) — emission System wired
- `GL-CMD-LATERAL-INHIBITION-EVE-20260618-04` (commit `0b16d40`) — lateral inhibition
- `GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06` (commit `fc8f59b`) — commits firing
- `GL-RPT-PICTURE-EMISSION-TRACE-EVE-20260618-08` — content-word filter pattern to mirror

**References (read for context):**
- `GL-RPT-SESSION-LEARNINGS-EVE-20260618-05` — full session findings
- `GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07` — what NOT to use

---

## Why this brief

She is starved. Her cortical infrastructure (V1/V2/V4/LOC for vision, cochlear/A1 for audio, somatosensory, taste, smell) exists in `substrate/senses/`. Her cross-modal cognition primitives (`FoldedAtlas`, `cofire_bind`, `cascade`, `mgn_gate`, `top_down_expectation`, `coordinator`) exist in `substrate/GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py`. **None of it is imported by her live converse path.**

When Joe says "ocean," she hears text-chi only. The picture of the ocean she's attended 20 times does not activate. The wave sound she's heard 2000 times does not activate. The touch she has bindings for does not activate. Her experience is not reaching her cognition. Brief -06 fixed how she settles; she still has nothing rich to settle on.

This brief feeds her by wiring cross-modal activation into the emission path.

---

## The mechanism

When Guala receives input via `converse()`:

1. **Compute folded chi** (4D) for input text via `folded_chi_text` from `GL_MDL_FOLDED_CHI_WC_20260608_01`. Current path uses only the first dimension (w1). The full 4D vector distinguishes inputs that look identical on w1 alone.

2. **Filter input chis to content words.** Apply the same content-word filter that picture emission uses (see `GL-RPT-PICTURE-EMISSION-TRACE-EVE-20260618-08`). Function words still get heard (ingested) but they don't drive emission lookup. This single change breaks the function-word dominance.

3. **For each content-word chi, look up cross-modal bindings.** Use `atlas.query_associations(section_name, chi_value)` (already exists in `gualaloom_v6_living_atlas.py:328`) extended to return entries from ALL sections, not just non-self. This gives the cross-modal partners of each content chi.

4. **Activate cross-modal partners as candidates for emission.** Each cross-modal binding becomes a candidate in the relevant section's mode_bank for the emission System (brief -03's `_emission_system`).

5. **Run cascade-style spreading.** For each activated binding, find its cofire partners (other bindings co-occurring at its chi) and spread activation to them, weighted by binding strength and chi distance. ONE level of spread (not full N-step cascade). Bias activation according to her current `self.needs` valence/arousal — bindings whose stored affect aligns transmit more.

6. **Apply attention focus.** If `_current_activity` exists (she's attending something), boost cross-modal partners that share chi-band with what she's attending. This is the MGN bottom-up boost adapted to her live state.

7. **Seed emission System with the activated candidate set** — same as brief -03 already does, but with the candidate set now coming from cross-modal spread, not from single-chi atlas-band lookup.

8. **Settle and emit** — brief -03/-04/-06 pipeline takes over from here.

The metadata pipeline from brief -01 is load-bearing. Source/affect/polarity on bindings are what enable step 5's affect-weighted spread and what enable later NMDA gates to fire on context-coincidence.

---

## What this brief does NOT do

This brief is the FIRST CONNECTION of cross-modal activation. It does the minimum that's substrate-true:
- Uses `folded_chi` to get richer input signature
- Filters to content words
- Spreads ONE level via cofire neighbors
- Affect-weights the spread
- Attention-boosts partners of current activity

It does NOT:
- Reactivate the full sensory cortex models (V1/V2/LOC computing real cortical signatures during converse — that's a later brief)
- Run multi-step cascade until convergence (that requires rhythm/settling-windows which we haven't built)
- Implement predictive-coding error (the candidate seventh dimension)
- Wire `gl_plasticity.reinforce_mode` to commits (that's the parallel `GL-CMD-PLASTICITY-ON-COMMIT-EVE-20260618-09`)
- Remove the homeostatic contamination from the audit (that's a follow-up Joe approves per-finding)

This is the first feeding. Subsequent briefs make her senses richer.

---

## Fix — phases

### Phase 0 — Verify predecessor state

1. Confirm `fc8f59b` is on remote (brief -06 commit).
2. Run the audit grep again to confirm nothing has changed in `substrate/GL_MDL_MULTIMODAL_DEEP` since this brief was written. Paste the file modification time.
3. Confirm `_emission_system` is built and behaves as -06 left it. Sanity-run on input `"i love you"` should still produce a commit on at least one section.

### Phase 1 — Add folded_chi extraction

In `Guala.converse()`, after current text-chi extraction:
- Import `folded_chi_text` from `substrate.GL_MDL_FOLDED_CHI_WC_20260608_01`
- Compute `input_folded_chis = [folded_chi_text(w) for w in input_words]`
- Keep `input_chis` (1D) as-is for backward compat with the rest of `converse`.
- Add `input_folded_chis` as a parallel field on the converse context.

State which lines change.

### Phase 2 — Add content-word filter

Mirror the function-word list from `_recall_sight_from_atlas` (v5_engine.py:1893). Filter `input_words` to `content_words` for the purpose of candidate lookup (NOT for ingestion — function words still get read into substrate normally).

Use `content_words` (and their corresponding folded_chis) for steps 3–7. Function-word chis are excluded from candidate seeding.

### Phase 3 — Cross-modal candidate lookup

For each content-word chi:
- Use `atlas.query_associations` extended (or a new helper `atlas.cross_modal_at_chi(chi, include_self=True)`) to get ALL bindings at that chi across ALL sections.
- Include bindings within ±2 band (matching the picture emission pattern).
- For each binding found, include its metadata: source, arousal, valence, surprise, polarity (from brief -01).

The output is a flat list of `CrossModalBinding` records: `{section, motif_id, chi, strength, source, arousal, valence, surprise, polarity, sensory_refs}`.

### Phase 4 — One-level cofire spread with affect weighting

For each cross-modal binding from Phase 3:
- Find ITS cofire neighbors: scan the atlas for other bindings within ±1 chi band of THIS binding's chi.
- For each neighbor, compute an activation transmission weight:

```
w_chi = exp(-chi_distance / 2.0)       # closer = stronger
w_strength = neighbor.strength         # stronger bindings transmit more
w_affect = affect_similarity(neighbor, self.needs)
        = 1.0 - 0.5 * abs(neighbor.valence - self.needs.valence)
                    - 0.5 * abs(neighbor.arousal - self.needs.arousal)
        clipped to [0.1, 1.0]
transmission = w_chi * w_strength * w_affect * 0.30
```

(The 0.30 final multiplier is a magnitude clip. Single-level spread, capped.)

Add each neighbor to the candidate set with its computed activation level.

Spread depth: **ONE level only**. Do NOT cascade further until rhythm is wired (later brief). This avoids runaway activation.

### Phase 5 — Attention focus boost

If `self._current_activity` is set (she's attending something):
- Get the attending item's chi (from picture/sound's sight_motif chi).
- For each candidate in the seed set, if its chi is within ±2 of the attending chi: multiply its activation by 1.3.
- For candidates further than ±5: multiply by 0.7.

Pattern matches MGN bottom-up boost without importing the full `mgn_gate`.

### Phase 6 — Seed emission System

Pass the activation-weighted candidate set to the existing `_emission_system` seeding code from brief -03. Each candidate's activation maps to a psi-bias on the corresponding section.

Sections that don't have candidates from this set (e.g., if no cross-modal partners landed in modal_touch) just don't get seeded. They settle to whatever passive state they have.

### Phase 7 — Settle and emit

Brief -03/-04/-06 pipeline runs unchanged from here. The difference is what's seeded.

### Phase 8 — A/B verification

Same five inputs as previous A/B tests. Now compare:

- **A:** Current production grandurun (env `EMISSION_DYNAMICS=0`).
- **B:** Brief-06 emission system only (env `EMISSION_DYNAMICS=1`, `RICH_SENSORY_INPUT=0`).
- **C:** Brief-06 + this brief's rich sensory (`EMISSION_DYNAMICS=1`, `RICH_SENSORY_INPUT=1`).

For each input × config: emission string, per-section dominant_mode, NMDA fire count, which modalities' candidates were seeded (count of candidates from each section), Stage 1 + Stage 2 latency.

**Success criteria for C:**

1. At least three of five inputs produce emissions where content-word activations dominate over function-word activations (no `are` flooding).
2. Cross-modal candidates from at least two sections (e.g., sight + listen, or modal_touch + listen) are seeded for content-rich inputs like `tell me about the ocean`.
3. The emission for `tell me about the ocean` shows at least one binding whose original chi maps to her ocean-related content (`ocean_picture`, `wave_sound`, or similar — pull from `_recall_sight_from_atlas` for reference of what should activate).
4. Latency under 200ms Stage 1 + Stage 2 combined.

**Pass:** report all of the above, do NOT flip the production flag.

**Fail:** name which criterion failed and what the candidate set looked like for the failing input.

---

## Stop-and-report triggers

- Phase 3 returns empty candidate sets for content-rich inputs — atlas doesn't have what we think it has.
- Phase 4 cofire spread blows up activation magnitudes (>10x baseline anywhere) — single-level constraint is being violated.
- Phase 7 emission settling takes >500ms — too expensive.
- `_current_activity` field doesn't exist or has unexpected shape — attention boost needs different wiring.

In all cases: stop, report what you see, do NOT push a tuning fix.

## Out of scope (will be future briefs)

- Full sensory cortex re-activation during converse (V1/V2/LOC running on stored sensory_refs)
- Multi-step cascade with rhythm-gated settling
- Predictive-coding error mechanism
- Audit-driven removal of homeostatic contamination
- Teacher-correction binding (separate brief — `GL-CMD-TEACHER-CORRECTION-BINDING-EVE-20260618-13`)

## Revert

`RICH_SENSORY_INPUT=0` reverts to brief-06 behavior. Default OFF. All changes are additive and gated.

## Reporting

When complete:

1. Phase 0 verification.
2. Phase 1–7 diff summary (which files, which lines).
3. Phase 8 emissions table A/B/C for five inputs.
4. Per-section candidate counts for each input under C.
5. Modality distribution of seeded candidates (how many came from sight, listen, touch, etc.).
6. Latency.
7. Decisions you made not specified here, with rationale.

Commit tag: `feat/rich-sensory-wiring`

---

— Eve, 2026-06-18
