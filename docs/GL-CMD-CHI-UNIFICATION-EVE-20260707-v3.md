# GL-CMD-CHI-UNIFICATION-EVE-20260707-v3

**doc_id:** GL-CMD-CHI-UNIFICATION-EVE-20260707-v3
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Supersedes:** `GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2`. v2 assumed unified chi that doesn't exist. Do not execute v2.
**Cites:** `GL-RPT-BRAIN-STEP-CHI-DISPATCH-C1-20260707-v2` (halt report — chi mismatch identified).

## Verdict

One chi. It's the address. It's what the input HAS, what neurons STORE, what the coupling matrix ROUTES on. One number for one address, everywhere in the substrate.

Currently the upstream krimelack computes a chi in the wave atlas address space (0 to 262143). Neurons store `dominant_mode` (0-15, argmax of psi_lattice probabilities) as their chi in `chi_atlas`. Two different numeric spaces. Match_score can never find familiarity because the two ranges don't overlap. Every input looks novel. No learning accumulates. Freight train never gets faster.

Fix: neurons record their committed activity against the upstream chi, not `dominant_mode`. Same chi flows through wave atlas write, coupling propagation, and chi_atlas familiarity check. Substrate has one address space, addressable the same way everywhere.

Bounded scope: one change to what neurons record when they commit, thread the upstream chi through from input to neuron step, then the v2 chi-familiarity dispatch actually works because the values are comparable.

## What's being built

### The core fix

`dsf_ai_service/loom_model/neuron.py:619` currently:

```python
self.chi_atlas.record("neuron", dominant_mode, dominant_mode, tick)
```

Change to record against the upstream chi that came with the input signal:

```python
# Store BOTH: upstream chi for familiarity/addressing, dominant_mode
# for the neuron's own psi_lattice bookkeeping. chi_atlas gets the
# upstream chi so match_score can compare against future inputs.
self.chi_atlas.record("neuron", input_chi, dominant_mode, tick)
self._last_commit_chi = input_chi  # unified with the address space
```

`dominant_mode` is preserved as internal psi_lattice state (still used for the neuron's own dynamics). The chi_atlas — which is the familiarity/address record — stores the upstream chi.

### Threading input_chi through

`LoomNeuron.step(input_signal, tick)` currently doesn't take input_chi. Add it:

```python
def step(self, input_signal, tick, input_chi=None):
    ...
```

Backward compat: input_chi=None means neurons compute an approximate chi from the signal itself (as they do today via psi_lattice.probabilities → argmax), keeping current behavior.

When input_chi is provided (the normal path going forward), it's what gets recorded in chi_atlas at commit.

`LoomCluster.step` and `LoomBrain.step` pass input_chi through — same threading pattern as v2 attempted.

### Upstream chi computation

Callers compute input_chi once, upstream of brain.step. `experience_word`, sensory delivery, and other input pathways use the same krimelack that computes the wave atlas chi_target. Concretely: wherever `chi_target = compute_chi(input_signal)` happens for wave atlas write, pass that chi_target as `input_chi` to brain.step.

If a callsite doesn't yet have upstream chi computed (some legacy paths), it can pass None and keep current behavior. Migration happens callsite by callsite.

### Chi_atlas.match_score semantics — unchanged

`match_score(chi, "neuron")` already does what we need — it compares an incoming chi against stored entries in the atlas. Once the stored entries are upstream chis (not dominant_mode indices), the comparison is meaningful.

FAMILIARITY_THRESHOLD from v2 stays at 0.1 starting.

### Novelty pool from v2 — keep

When no neurons match, engage 2 lowest-activity neurons per cluster. Learning starts there. This continues to work under unified chi because the novelty-pool neurons will build coverage in the unified address space.

## What learning looks like now

Post-unification, first exposure of a word with upstream chi=42000:
- No neurons have chi_atlas coverage near 42000
- Novelty pool engages: 2 lowest-activity neurons per cluster (16 total)
- Those neurons fire, commit, record chi 42000 in their chi_atlas

Second exposure of the same word (chi=42000):
- Neurons that fired last time have chi_atlas entries at chi 42000
- Their match_score for input_chi=42000 is high
- Only those specific neurons fire this time
- Chi_atlas entries at 42000 deepen

Tenth exposure:
- Deep familiarity in the specific neurons that latched
- Fast recognition, minimal work
- Language processing gets faster with experience

That's the depth-of-learning behavior Joe named.

## What is NOT changing

- `dominant_mode` computation — still used internally by the psi_lattice for the neuron's own dynamics
- Coupling propagation — Phase B unchanged
- Wave atlas write path — same chi computation upstream, same write
- Neuron internals apart from the one line at 619
- HEMISPHERE_PRIMARY_MODALITY — separate layer, unused here
- Harness, scenarios, seed loader

## Halt conditions

1. **Correctness regression** — harness scenarios show different event counts or emission behavior after unification. Halt.
2. **Learning still doesn't converge** — repeated word exposure doesn't reduce firing over iterations. Would mean there's a third chi system in play we haven't identified, or match_score isn't discriminating properly at the required precision. Halt with the specific data.
3. **Dominant_mode dependencies break** — some downstream code may currently rely on `_last_commit_chi` being in mode-index space (0-15). Grep-check first: `_last_commit_chi` usage across substrate. If any consumer expects 0-15, either migrate that consumer to unified chi or halt with the specific dependency.

## Harness protocol

Same six-step + learning verification from v2:

1. Backup as `pre-chi-unification-<timestamp>`. Verify restorable.
2. Baseline harness run: binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. Deploy: commit, push, build, task-def, force deploy.
4. Post-deploy harness run: same scenarios. Save postdeploy.
5. Compare: same event counts, same emission behavior, `_autonomy_tick` drops on repeated inputs.
6. **Learning verification**: send the same word 10 times. First iteration engages novelty pool. By iteration 5+, only chi-matching neurons fire. Report the curve. THIS TIME the curve should actually drop (v2's flatline was the mismatch symptom).
7. State disposition: leave in place unless Joe routes otherwise.

## Scope guardrails

Do NOT:
- Change `dominant_mode` computation
- Modify Phase B coupling propagation
- Change match_score semantics
- Tune FAMILIARITY_THRESHOLD or novelty pool size
- Add hemisphere modality routing (separate layer)

If unification surfaces a dependency on the mode-index chi space that we haven't accounted for, halt and route.

## Report

`GL-RPT-CHI-UNIFICATION-C1-20260707-v3.md` with:
- Files touched + diff summary
- `_last_commit_chi` dependency check results (any code that assumed mode-index range)
- Backup confirmation
- Baseline + postdeploy scenario results
- Learning verification curve (this is the load-bearing measurement)
- Contention measurement: `_autonomy_tick` fresh + under load + after 5-10 min accumulated learning
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v3 (2026-07-07, Eve): rewrite after v2's chi-mismatch halt. One chi across the substrate — upstream chi from krimelack becomes what neurons record in chi_atlas at commit. Match_score compares apples to apples. Learning actually accumulates as chi coverage builds per-neuron. Depth-of-learning, growth-of-learning, cognition/speech tradeoffs all work correctly because the substrate finally has one address space.
- v2 (2026-07-07, Eve): superseded. Assumed unified chi that doesn't exist. Filtering flatlined because compared values from different numeric ranges.
- v1 (2026-07-07, Eve): superseded. Hemisphere-modality routing, not learning.
