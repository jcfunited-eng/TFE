# GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v2

**doc_id:** GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after physics model exposed v1 as LLM-shaped)
**Supersedes:** `GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v1`. Do not execute v1.

## Verdict

v1 built new leaky-integrator plumbing with invented weight matrices and hardcoded decay constants. Physics model exposed this as approximating what the substrate's existing primitives already do. Joe confirmed the substrate has:
- Krimelack wave field that persists between ticks.
- Organism neurons with chi-coverage receptive fields.
- Hebbian connection strengthening between neurons.

Real dispatch: wire the existing three primitives together for hemispheric integration. Do not add scalar activations. Do not add per-modality weight matrices. Do not add hardcoded decay constants. The physics is already there.

Bounded scope: three wiring changes, no new subsystems.

## What's being wired

### Wiring 1: sensory transduction → krimelack wave field

For each of the six sensory transduction paths (sight, sound, word, touch, smell, taste), confirm that the transduced signal is deposited into the persistent krimelack wave field at the correct chi coordinate for that modality's band.

If already happening: no change, note in report.
If not: add one call per transduction path to inject the transduced signal into the wave field at the correct chi position.

### Wiring 2: hemispheric neurons → wave field sampling per tick

Each hemisphere's neurons already have chi-coverage receptive fields (per Joe's confirmation). Each tick, each neuron samples the wave amplitude in its coverage region. If amplitude crosses threshold, the neuron fires.

If the tick loop already calls neuron-fire-check for organism neurons against the krimelack field: no change, note in report.
If not: add one call in the tick loop that walks each hemisphere's neurons and asks them to check-and-fire against the current field state.

### Wiring 3: Hebbian co-firing → emission candidate source

Hebbian connections between neurons already strengthen from co-firing (per Joe's confirmation). Emission needs to draw candidates from Hebbian-recalled neurons — meaning, when a partial cue arrives and some neurons fire, emission should score candidates by the connection strength from firing neurons to non-firing candidates.

Change emission's candidate scoring: instead of whatever it currently reads (organism state, tapestry recall, atlas query), read from the Hebbian recall — for each candidate neuron, sum the connection weights from currently-firing neurons to that candidate. Rank. Return top-K. The em, sc, sv hemispheres provide the candidate pool.

### Event emission

New event: `hemispheric_wave_sample`. Fires each tick, per hemisphere, with the top-N chi coordinates where amplitude was highest and which neurons fired. Payload includes tick, hemisphere name, top firing neuron ids, wave energy in the hemisphere's coverage region. For observability only, cheap to compute since the physics is already running.

## What is NOT being built

- No scalar sensory activation vectors. Wave field already carries this.
- No per-hemisphere weight matrices. Neuron chi-coverage patterns already carry hemispheric specialty.
- No hardcoded decay constants. Wave damping already carries this.
- No local_activation dicts on hemispheres. Hebbian connection graph already carries this.
- No clamping. Energy conservation prevents runaway naturally.
- No new modules if the primitives are already wired. Just the missing links.

## Harness protocol

Six steps.

1. **Backup** — `pre-hemispheric-integration-<timestamp>`. Verify restorable.
2. **Baseline harness run** — run `hemispheric_integration_acceptance.yaml` (Eve provides updated v2 to match this dispatch) against current code. Save baseline report.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenario. Save postdeploy report.
5. **Compare** — post-deploy shows `hemispheric_wave_sample` events firing per tick, emission after decay draws from Hebbian-recalled candidates.
6. **State disposition** — leave in place unless Joe routes otherwise.

## Scope guardrails

Do NOT:
- Add scalar activation systems.
- Add weight matrices.
- Redesign the wave field, neurons, or Hebbian mechanism. Use what exists.
- Change sleep/wake, autonomy, binding windows, or recall.
- Add caching.
- Tune wave damping or Hebbian learning rate — those are physics constants, not tuning knobs, and the substrate already has them set.

If any of the three primitives (persistent wave field, neuron chi-coverage, Hebbian connections) turns out to not exist in the form Joe described, HALT and route back to Eve. Do not build a substitute. The dispatch depends on them existing; if they don't, the dispatch is wrong and needs rewriting.

---

### Changelog
- v2 (2026-07-07, Eve): rewrite. v1 built new plumbing that duplicates existing substrate primitives. v2 is wiring only. Joe confirmed the three primitives exist. Verification is check-then-wire, and halt if any primitive is missing rather than building a workaround.
- v1 (2026-07-07, Eve): superseded. Built leaky-integrator plumbing with invented scalar weight matrices. Physics model exposed this as approximating what the substrate already does.
