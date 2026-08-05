# GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2

**doc_id:** GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Supersedes:** `GL-CMD-BRAIN-STEP-MODALITY-ROUTE-EVE-20260707-v1`. Do not execute v1.

## Verdict

v1 routed by hemisphere modality. That still runs all 8 neurons in every language hemisphere on every word, regardless of whether they've ever seen the word before. That's a smaller freight train, not learning.

Learning IS reduced neural activation. When a familiar word arrives, only the neurons whose chi_atlas contains entries in that chi neighborhood should fire. Novel words engage more neurons (they're all trying to recognize it). Repeated exposure builds chi_atlas coverage in the specific neurons that latched onto that chi region. Next time that word arrives, only those neurons fire — the rest stay silent because their chi_atlas has no entries there.

That's the photon model in code. Substrate gets faster as it learns because fewer neurons need to run per familiar input. Language processing time drops with experience. Novel processing stays engaged until familiarity accumulates.

Bounded scope: compute input chi upstream, add a familiarity check to LoomCluster.step, skip neurons whose chi_atlas has no coverage near the input chi.

## What's being built

### Upstream chi computation

The input signal's chi is computed once, by the shared krimelack that already runs to generate wave atlas writes. That chi gets passed through into brain.step and cluster.step as the input_chi.

Callsites already have this — the wave atlas write path computes `chi_target` before writing. Same chi value should be passed to brain.step. Concretely, `experience_word` and other input handlers compute the chi once via the shared krimelack, then pass both the input_signal and the input_chi to brain.step.

### `LoomBrain.step` — pass input_chi through

Add `input_chi: Optional[int] = None` parameter. Passes through to each cluster.step. No filtering at brain level.

```python
def step(self, input_signal, tick: int,
         input_chi: Optional[int] = None) -> Dict[str, Dict[str, Dict]]:
    return {
        hemi_id: cluster.step(input_signal, tick, input_chi=input_chi)
        for hemi_id, cluster in self.clusters.items()
    }
```

### `LoomCluster.step` — chi-familiarity filter on Phase A

The core change. Phase A currently runs step on every neuron. Change to: only run step on neurons whose chi_atlas has non-trivial coverage near input_chi. Phase B (coupling propagation) still runs everywhere so cross-neuron spikes propagate. Phase C only refreshes neurons that actually stepped.

```python
def step(self, input_signal, tick, input_chi=None):
    results = {}

    # Phase A: filter by chi familiarity
    stepping_neurons = self._select_by_chi_familiarity(input_chi)
    for neuron in stepping_neurons:
        results[neuron.neuron_id] = neuron.step(input_signal, tick)

    # Phase B: coupling propagation runs across the whole cluster
    # (spikes can propagate to neurons that didn't step this tick)
    spiking_neurons = [
        n for n in self.neurons if results.get(n.neuron_id, {}).get("committed")
    ]
    for neuron in self.neurons:
        # coupling receive logic unchanged
        ...

    # Phase C: only refresh J for neurons that actually stepped
    for neuron in stepping_neurons:
        if neuron._last_dsf is not None:
            neuron.couplings.update_from_dsf(neuron._last_dsf)

    return results
```

### `_select_by_chi_familiarity(input_chi)` — the discriminator

Two behaviors:

**When input_chi is None** — backward compat. All neurons step. Current behavior. This preserves callers that haven't been updated.

**When input_chi is provided** — filter:
1. For each neuron, query `neuron.chi_atlas.match_score(input_chi, "neuron")` — the substrate already exposes this, per neuron.py line 588
2. If match_score exceeds FAMILIARITY_THRESHOLD (starting value 0.1, env-var configurable), the neuron participates
3. If cluster ends up with zero participating neurons AND the input is novel (no neurons have any coverage), include a small novelty pool — 1-2 lowest-activity neurons — so the substrate can grow chi_atlas coverage into new regions. Otherwise novel inputs would never be learned because no neurons would ever fire on them.

Rough shape:

```python
def _select_by_chi_familiarity(self, input_chi):
    if input_chi is None:
        return self.neurons  # backward compat
    familiar = [
        n for n in self.neurons
        if n.chi_atlas.match_score(input_chi, "neuron") > FAMILIARITY_THRESHOLD
    ]
    if familiar:
        return familiar
    # Novelty pool: include lowest-activity neurons to enable learning
    return sorted(self.neurons,
                  key=lambda n: n.chi_atlas.total_entries())[:2]
```

That novelty pool detail is what makes this learning: new inputs engage a small number of neurons that then start building chi_atlas coverage for that chi region. Next time similar input arrives, those neurons have match_score above threshold and fire. Others stay silent.

### Expected behavior over time

- **Cold substrate (post-wipe):** every input triggers the novelty pool because no neurons have any coverage. 2 neurons per cluster fire, 2×8=16 total. Small subset learns.
- **After some exposure:** the neurons that latched onto specific chi regions have match_score above threshold. Those specific neurons fire on repeat inputs. Others stay silent. Familiar inputs might trigger 3-5 neurons total across the whole substrate.
- **Novel input on trained substrate:** neurons with coverage near the input's chi respond, others don't. If truly novel (far from all existing coverage), novelty pool engages. New coverage builds.

This is what "the substrate learns and processes familiar inputs faster" actually looks like in code.

## What is NOT being changed

- `LoomNeuron.step` internals — untouched.
- Phase B coupling propagation — untouched. Spikes still cross to non-stepping neurons via the J matrix if those neurons have couplings to spiking neighbors. Note: those non-stepping neurons receive spikes but don't advance their own step, so their DSF doesn't fold on this tick. That's correct — they didn't recognize the input, but they can still be nudged by network activity.
- `HEMISPHERE_PRIMARY_MODALITY` — untouched. Modality routing at hemisphere level is a separate layer that could be combined with this later.
- Coupling J matrix updates — happens naturally as neurons that fire update their own J.
- Any harness or scenario.

## Halt conditions

1. **Correctness regression** — harness scenarios show different emission behavior. If the substrate stops emitting on inputs it used to emit on, familiarity threshold is too aggressive or novelty pool is too small.
2. **Learning doesn't accumulate** — if repeated exposure to the same word doesn't reduce the number of neurons firing over time, the chi_atlas coverage isn't being built the way we think, or match_score doesn't discriminate. Halt and route.
3. **Coupling breakage** — if Phase B doesn't correctly propagate spikes to non-stepping neurons (because they're not in `stepping_neurons`), spikes get lost. Should not happen with the design above, but verify.

Any halt: route with data, do not change threshold or novelty pool size unilaterally.

## Harness protocol

Standard six-step, plus a learning verification:

1. **Backup** — `pre-brain-chi-dispatch-<timestamp>`. Verify restorable.
2. **Baseline harness run** — binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenarios. Save postdeploy.
5. **Compare** — same event counts, same emission behavior, `_autonomy_tick` drops.
6. **Learning verification** — send the same word 10 times in sequence. Track number of neurons firing per iteration. First iteration should engage novelty pool (~2 per cluster). By iteration 5+, only the neurons that built coverage should fire (~1-2 total). Report the curve.
7. **State disposition** — leave in place unless Joe routes otherwise.

## Rollback

Task-def revert. Or `CHI_DISPATCH_ENABLED=0` env var to fall back to input_chi=None (all neurons step) without a redeploy.

## Scope guardrails

Do NOT:
- Tune FAMILIARITY_THRESHOLD or novelty pool size beyond starting values (0.1 and 2). Measurement drives adjustment.
- Change match_score semantics.
- Modify Phase B or Phase C structure.
- Add per-hemisphere modality routing (that's separate, could layer on top later).
- Remove the None fallback path — backward compat matters for callers that don't have upstream chi.

If the change surfaces any assumption in downstream code that all neurons always tick, halt and route.

## Report

`GL-RPT-BRAIN-STEP-CHI-DISPATCH-C1-20260707-v2.md` with:
- Files touched + diff summary
- Backup confirmation
- Baseline + postdeploy scenario results
- Learning verification: neurons firing per iteration for repeated word
- Contention measurement: `_autonomy_tick` fresh + under load, before vs after, and after some accumulated learning (5-10 minutes of reading)
- Any downstream code needing adjustment
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v2 (2026-07-07, Eve): rewrite. v1's hemisphere-modality routing was wrong — same neurons fired every time, no learning. v2 is chi-familiarity dispatch: input's chi computed upstream once, cluster.step queries each neuron's chi_atlas for match_score, only neurons with coverage near the input chi step. Novelty pool handles genuinely new inputs so learning can start. Substrate processing time on familiar inputs drops as chi_atlas coverage accumulates.
- v1 (2026-07-07, Eve): superseded. Hemisphere modality routing — smaller freight train, not learning.
