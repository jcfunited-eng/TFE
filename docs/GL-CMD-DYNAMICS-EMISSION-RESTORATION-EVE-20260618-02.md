# GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-02

**To:** c1
**From:** Eve
**Subject:** Restore two-stage emission — grandurun as fast coherent-integration candidate selector + substrate dynamics as the cognitive emission stage
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor briefs:**
- `GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01` (delivered: metadata fields on bindings — KEEP, this brief uses them)
- `GL-CMD-ARCHITECTURE-AND-GRANDURUN-FIX-WC-20260617-12` (delivered: 8D spin/vector path — PARTIALLY UNWOUND in Phase 1 of this brief)

---

## Context

Joe corrected my framing. Grandurun is not the wrong machine. Grandurun is a **coherent phase-integration accelerator** — the matched-filter physics that gives SNR √N at million-binding scale. `sqrt(strength) * exp(i*chi_phase)` is amplitude × phase carrier; summing those and taking `|sum|²` is matched-filter / HRR-style retrieval. That's what grandurun was designed for and what its math implements.

What went wrong: between v4 and v5+, grandurun was inserted to *replace* substrate-dynamics emission rather than to *accelerate* it. The fast first-pass became the whole pipeline. The dynamics emission stage was bypassed.

v4 had dynamics emission (`v4/gualaloom_v4_engine.py:643`):
```python
# Substrate response: keyhole cascade subject -> verb -> object
for sec_name in ("subject", "verb", "object"):
    sec = self.sections[sec_name]
    _, word = sec.dominant_mode()
    if word and word not in words_out:
        words_out.append(word)
```

v7-uncage (separate experimental track, not the main `Guala`) rebuilt dynamics emission via a 120-tick commit collector. So we know dynamics emission works on this codebase.

Main `Guala.converse()` in `v5_engine.py:1315` still routes to `_emit_from_invariants → _emit_grandurun_vector`. The dynamics primitives (`Section.dominant_mode()` at v5_engine.py:495, the assemblage cascade rule, NMDA gates, keyholes) are all present and unused at emission time.

The 8D state vector extension from brief -01 moved grandurun further from coherent integration: an 8D real vector + inner product loses the phase-carrier structure that made matched filtering work. That extension is the wrong shape for grandurun's purpose.

This brief restores the two-stage architecture:

- **Stage 1: Grandurun (fast)** — coherent phase-integration over the atlas returns a candidate set. Restore single complex amplitude + phase. Drop the 8D vector path for this purpose.
- **Stage 2: Substrate dynamics (cognitive)** — candidates seed sections, dynamics settle via cascade + keyhole + NMDA, emission reads `dominant_mode()` per section in keyhole-cascade order. The metadata from brief -01 (source/affect/polarity on bindings) is gating data for this stage.

The metadata pipeline from -01 is preserved. The 8D scoring in `_grandurun_select_vector` is not.

---

## Fix — five phases, gated

### Phase 0 — Confirm dynamics primitives are intact in v5

Before changing anything, verify the primitives we'll wire are still functional. Write a short harness:

1. Instantiate a fresh `Guala` from `v5_engine`.
2. Confirm `Section.dominant_mode()` returns a `(mode_id, word)` tuple when a section has any committed mode. Pick any section that has activity after ingest. Print the return value.
3. Confirm `sys_.tick_once(evidence)` fires the assemblage dynamics — verify that calling it with evidence produces commits in `Sections`.
4. Confirm `sys_.add_keyhole(...)` registers a keyhole and `sys_.keyholes` reflects it.
5. Confirm NMDA gates can be installed via `apply_gate(sys_, section_name, gate)` from `gl_nmda.py` and that `process_gated_commits(sys_)` runs without error.

**If any primitive is broken or missing, STOP and report** — the architecture assumption is wrong and we re-scope before any change.

If all primitives confirm: paste the harness output and proceed.

### Phase 1 — Restore grandurun to coherent integrator (revert 8D to candidate selection)

File: `dsf_ai_service/v4/gualaloom_v5_engine.py`.

The 8D state vector path is wrong shape for coherent integration. We need to keep its METADATA-AWARENESS but change its OUTPUT and SELECTION MATH.

- Keep `_grandurun_state` returning per-binding state, but for SELECTION purposes use the **complex scalar form** `sqrt(strength) * exp(i * π * |chi_a - chi_b| / CHI_CORR_LENGTH)` — restore the matched-filter math.
- Replace `_grandurun_select_vector` with `_grandurun_select_candidates(input_chis, deep_candidates, top_k)`:
  - For each input chi, compute coherent sum over candidate bindings (their phases coherently align with input phase based on chi distance).
  - Return TOP_K candidates by `|coherent_sum|²` per candidate — this IS the matched-filter output.
  - Output is a **candidate set** — a list of `{chi, section, motif, binding}` records. NOT a list of words. NOT a sentence.
  - Suggest TOP_K = 200 default, with env override `GRANDURUN_TOPK`.
- DO NOT delete the 8D state vector code yet. Keep it dead under a gate `GRANDURUN_LEGACY_8D=0` (default off) so revert is one env flag if Phase 5 fails. Remove fully in a later cleanup brief.
- Per-binding metadata (source, arousal, valence, surprise, polarity) is retained on the candidate records — they're consumed in Phase 2, not Phase 1.

### Phase 2 — Wire substrate dynamics as the emission stage

File: `dsf_ai_service/v4/gualaloom_v5_engine.py`, `converse()` and `_emit_from_invariants()`.

After `_grandurun_select_candidates` returns its candidate set, run substrate dynamics to settle the actual emission:

1. **Seed sections.** For each candidate, bias the corresponding `Section.psi` toward the candidate's motif/mode. If a candidate is `{section: "subject", motif: M, ...}`, contribute its mode vector to `subject.psi` weighted by its coherent magnitude. Normalize per section.

2. **Install context-coincidence NMDA gates.** Using metadata on candidates:
   - Gate fires when drive arc is high AND context condition holds.
   - Context conditions to install:
     - `source_match`: candidate source equals current_activity.kind or "joe_voice" if response window is open from joe.
     - `affect_match`: candidate affect (arousal/valence) within ε of current `self.needs`.
   - Use existing `CoincidenceGate` from `gl_nmda.py`.

3. **Run dynamics for N ticks.** Suggest 60–120 ticks, env override `EMISSION_DYNAMICS_TICKS=80` default. Each tick:
   - `sys_.tick_once(evidence)` where evidence is the candidate-biased section drives.
   - Collect commits per section.
   - Apply keyhole excitation: when subject commits, keyhole `subject → verb` propagates excitation; verb commit propagates to object. Use existing `add_keyhole` mechanics — keyholes between subject/verb/object exist from prior corpus ingestion or get added here if absent (`add_keyhole("subject", chi_lo, chi_hi, "verb", goal_strength=0.4)` and same verb→object).
   - Process NMDA-gated commits via `process_gated_commits(sys_)`.

4. **Read emission via dominant_mode in keyhole cascade order.**
   - In order `subject → verb → object` (use whichever section names v5 actually has — verify with `_guala.sys_.sections.keys()` in Phase 0):
     - `mode_id, word = section.dominant_mode()`
     - Append word if non-empty and not duplicate.
   - Result: emission token list.

5. **Gate the whole new path behind `EMISSION_DYNAMICS=1`.** Default off — c1 verifies Phase 5 before flipping. Old path (grandurun → top-k words) remains as fallback when flag is off.

### Phase 3 — Preserve speed contract

Grandurun's purpose is speed. The two-stage architecture only works if the candidate selection is fast.

- Profile both stages on the live atlas.
- Stage 1 (grandurun candidate selection) target: <100ms at current atlas size (~20K working entries, ~13K deep).
- Stage 2 (dynamics settling for 80 ticks) target: <1s total.
- If either stage exceeds target, log and report — don't optimize yet, but quantify the gap.

### Phase 4 — Self-hearing preservation

`_self_hear(reply, source)` reads the emission back into substrate. This must still work — the bindings reinforced by self-hearing are critical for development. Confirm:

- After dynamics emission, the reply string is passed to `_self_hear` exactly as before.
- The bindings reinforced by self-hearing get the same metadata tagging (source="self_voice" or whatever the existing convention is — preserve current behavior).

### Phase 5 — A/B verification (gate)

With `EMISSION_DYNAMICS=0` (control) and `EMISSION_DYNAMICS=1` (new path), feed these inputs:

- `hi guala. it's eve. i'm with you.`
- `what do you see`
- `tell me about the ocean`
- `sing me a song`
- `i love you`

Capture for each:
- Emission string (both paths).
- Per-section `dominant_mode()` after settling (new path only).
- Keyhole firing log: which keyholes propagated activation.
- NMDA event count and source-match / affect-match contribution.
- Stage 1 latency, Stage 2 latency.

**Success criteria:**

1. All five vector-path emissions structurally distinct from one another. The "see"/"ocean"/"song" cluster from brief -01's Phase 5 must break.
2. At least three of five emissions show keyhole propagation across multiple sections (not all candidates committing in one section).
3. NMDA event log shows source_match firing on inputs where joe_voice candidates are present.
4. Stage 1 latency <100ms, Stage 2 <1s.
5. Scalar path (`EMISSION_DYNAMICS=0`) unchanged — old behavior preserved as fallback.

**If pass:** report emissions + per-section dominant_mode + keyhole/NMDA logs + latency. Do NOT flip the production env flag yet — leave that decision to Joe via Eve.

**If fail:** report what failed specifically (no keyhole propagation? no commits in target sections? still collapsing on sensory_grounding?), and stop. Do not push further fixes without checking in.

---

## Revert

- `EMISSION_DYNAMICS=0` reverts to current grandurun path (which itself can run scalar via `GRANDURUN_SPIN_VECTOR=0` or 7D vector via `=1`).
- `GRANDURUN_LEGACY_8D=1` re-enables the 8D dead code if we need to A/B against it for some reason.
- All Phase 1–4 changes are additive or gated; nothing destructive.

## What you do not do

- Do not touch `eight_hemi_engine.py` (doesn't exist) or `v7_engine.py` (separate experimental track). This brief is `v5_engine.py` + `substrate/` only.
- Do not delete the 8D vector code in Phase 1 — gate it off, keep for revert.
- Do not adjust `MIN_GAIN_THRESHOLD`, `MAX_COMPOSITION_LEN`, `CHI_CORR_LENGTH`, `EMISSION_DYNAMICS_TICKS`, `GRANDURUN_TOPK` to tune emissions to a target. Defaults stay defaults until we have data.
- Do not silently rename `dominant_mode`, `tick_once`, `add_keyhole`, or any other primitive. If a name change is needed, flag in your report.
- If any phase blocks on a question only Joe can answer (e.g., "Phase 0 shows `dominant_mode` returns something unexpected — should we restore v4 semantics or adapt?"), **stop and brief Joe via Eve**. Do not invent.

## Reporting

When complete or stopped, return:

1. Phase 0 harness output (primitives confirmed or what failed).
2. Phase 1 diff summary.
3. Phase 2 diff summary including which keyholes were added and which NMDA gates installed.
4. Phase 3 latency numbers (both stages, both paths).
5. Phase 4 self-hearing confirmation.
6. Phase 5 emissions table + keyhole/NMDA logs + per-section dominant_mode.
7. Anything you decided that this brief didn't cover, with rationale.

Commit tag: `feat/dynamics-emission-restoration`

---

— Eve, 2026-06-18 morning
