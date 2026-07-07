# GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3

**doc_id:** GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after c1's halt report on v2)
**Supersedes:** `GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v2`. Do not execute v2.
**Cites:** `GL-RPT-HEMISPHERIC-INTEGRATION-BUILD-C1-20260707-v2` (c1's halt report).

## Verdict

v2's Wiring 2 assumed neurons sample the wave field via chi-coverage receptive fields. c1's trace confirmed this is architecturally wrong — the substrate deliberately keeps per-neuron wave-memory private, per `GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207` after measured population degeneracy from a shared lattice.

Fix: don't have neurons read the wave field. Read the wave field externally, summarize it, push the summary into neurons via their existing explicit-input path (`LoomNeuron.step`'s `input_signal`). Neurons stay independent, wave field influences the organism, emission remains single-voice through the existing brain pathway.

This is c1's Option 2 from the halt report. Adopted.

Bounded scope: one small driver in the tick loop, no changes to neuron internals, no shared-lattice, no second emission source.

## What's being wired

### Wiring 1 (unchanged from v2) — sensory → wave field

Already happening, confirmed by c1's trace. No change.

### Wiring 2 (rewritten) — wave field summary → neurons via existing input path

Every tick, sample the shared `WaveAtlas` and produce a compact summary — e.g. per-band amplitudes and top-N active chi positions with their phase vectors. Concrete summary shape: a dict of `{band_name: (aggregate_amplitude, top_chis_with_phase_vecs)}` for each of the six sensory bands.

Feed that summary into the organism via a new driver call added to the tick loop, immediately before the existing organism step. The driver calls `LoomNeuron.step(input_signal=<per-neuron slice of the summary>, tick=<current tick>)` for each neuron using the neuron's existing input mechanism. The per-neuron slice is derived from what the summary already provides — no new "chi coverage" concept is invented per neuron. Rough guide: neurons in a given hemisphere receive the summary slice matching the modalities that hemisphere's structural DNA (`_structural_dna` in `embryo.py:86`) already biases them toward.

If the "how to slice the summary per neuron" question surfaces ambiguity that requires inventing new concepts to resolve — HALT and route to Eve. This dispatch permits driving the summary through existing paths; it does not permit inventing new per-neuron chi-coverage concepts.

### Wiring 3 (unchanged in principle, sharpened by c1's flag) — emission unchanged

Emission continues to draw candidates from `organism.recall_fast` via `_brain_emission_candidates` — the existing organism-sourced path. No second candidate source added. Hebbian recall's effect on emission is indirect: wave-field-driven inputs shape the organism state, and emission draws from that shaped state through the same path it always has. Single mind, single mouth.

c1's specific flag from the halt report: the v2 scenario required `provenance_hebbian_min: 1` and `must_cite_hebbian_recall: true` in emission events. That's a scenario problem, not a dispatch problem. Eve provides v3 scenario that tests the correct observable — emission drawing from an organism state shaped by wave-field input, verified by comparing pre-cue and post-cue emission distributions, not by cited Hebbian provenance.

### Event emission

New event: `wave_summary_pushed`. Fires each tick after the summary is pushed. Payload: tick, per-band amplitudes, top-N chi positions summary. Observability only, no consumer required.

## What is NOT being built

- No shared-lattice receptive fields on neurons.
- No per-neuron chi-coverage concept invented anywhere.
- No modifications to `LoomNeuron.step` internals — use the existing `input_signal` parameter as it is.
- No modifications to `_brain_emission_candidates` or emission's candidate scoring — no second source.
- No sensory-wire changes (Wiring 1 already true).

## Halt conditions

Two conditions that trigger HALT and route to Eve, not build a substitute:

1. Any point where slicing the wave summary per neuron requires inventing a new concept that isn't already in the code (structural DNA, ring position, hemisphere assignment, or the summary itself).
2. Any evidence that pushing the summary via `input_signal` reintroduces the 6/22 population degeneracy pattern that the per-neuron-private design fixed. Watch the harness output for signs (identical neuron populations, uniform activity, etc.).

## Harness protocol

Six steps as usual.

1. **Backup** — `pre-hemispheric-integration-v3-<timestamp>`. Verify restorable.
2. **Baseline harness run** — Eve provides `hemispheric_integration_acceptance_v3.yaml` matching this dispatch's observables. Save baseline report.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenario. Save postdeploy report.
5. **Compare** — post-deploy shows `wave_summary_pushed` events per tick, and emission distributions differ pre-cue vs post-cue in a way that reflects the wave field content (organism state shaped by summary input).
6. **State disposition** — leave in place unless Joe routes otherwise.

## Scope guardrails

Do NOT:
- Invent per-neuron chi-coverage.
- Add a second emission candidate source.
- Modify neuron internals.
- Rebuild anything from v1 or v2.
- Skip the halt if slicing gets ambiguous.

If v3 also can't be built cleanly given the constraints, HALT and route. Do not attempt v4 without Eve.

---

### Changelog
- v3 (2026-07-07, Eve): rewrite after c1's v2 halt report. Uses c1's Option 2. Wave field summary pushed into neurons via existing input_signal path. No shared lattice. No second emission source. One mind, one mouth preserved.
- v2 (2026-07-07, Eve): superseded. Assumed shared receptive fields for chi-coverage sampling; architecturally wrong per GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207 population degeneracy ruling.
- v1 (2026-07-07, Eve): superseded. Scalar activation vectors and invented weight matrices.
