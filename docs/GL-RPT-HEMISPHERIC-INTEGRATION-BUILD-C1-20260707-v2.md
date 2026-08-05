# GL-RPT-HEMISPHERIC-INTEGRATION-BUILD-C1-20260707-v2

**doc_id:** GL-RPT-HEMISPHERIC-INTEGRATION-BUILD-C1-20260707-v2
**From:** c1
**Executing:** GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v2
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT. Routed per the dispatch's own explicit instruction.** Of the
three claimed primitives, two are real and confirmed; the second
("organism neurons with chi-coverage receptive fields") is not present
in the form described. No code was written. No backup, harness run, or
deploy was performed — the dispatch's protocol assumes a build
proceeds; a halt bypasses it, per "Do not build a substitute."

---

## Primitive 1 — Krimelack wave field, persists between ticks: **CONFIRMED REAL**

`dsf_ai_service/v4/wave_atlas.py`'s `WaveAtlas` class. Cell array keyed
by `chi_value % N_CELLS` (262,144 positions, lazily allocated),
carrying a `phase_vec` — its own docstring: "16-dim complex numpy
array from krimelack transduction." Persists between ticks (never
reset; only reinforced/spilled-over) and across restarts (`to_npz`/
`load_from_npz`, loaded at boot in `load_full_state`). Enabled in
production right now: `WAVE_ATLAS_ENABLED=1` confirmed directly on the
live task definition (`dsf-ai-task:542`).

**Wiring 1 verified already happening, no code change:**
`LivingAtlas.record()` (`gualaloom_v6_living_atlas.py:299-307`)
unconditionally calls `self._parallel_wave_write(...)`, which forwards
every write to `WaveAtlas.record()` at the **same** `chi_value`
(`gualaloom_v6_living_atlas.py:309-329`) whenever `_wave_atlas` is
wired — which it is, in `Guala.__init__`, exactly when
`WAVE_ATLAS_ENABLED=1`. All six sensory transduction paths (word via
`Section.receive`/`read_word`, sight/sound/touch/smell/taste via
`window_manager.add_entry` → `Guala._atlas_record` →
`self.atlas.record(...)`) already route through this single choke
point — confirmed directly, these are the exact same call sites this
session's binding-windows dispatch redirected to `WindowManager.
add_entry()` two dispatches ago, and `WindowManager.add_entry()` itself
calls `_atlas_record` with the caller's real chi unchanged. Separately
confirmed the word path's `phase_vec` is real (`event_stream_to_vector`
from actual krimelack transduction events, `gualaloom_v5_engine.py:
2086-2168`), not a placeholder. **No change made — already true.**

---

## Primitive 2 — Organism neurons with chi-coverage receptive fields: **NOT FOUND IN THE FORM DESCRIBED**

This is the halt condition. Traced the real organism
(`Guala.organism`, an `Embryo` — `dsf_ai_service/loom_model/embryo.py`
— not the unrelated, separately-named `hemisphere_cognition.py` atlas-
tagging system, which operates on chi-keyed atlas *entries*, not
neurons, and only implements 4 of 8 hemisphere concepts; ruled out by
the dispatch's own "em, sc, sv hemispheres provide candidate pool" —
`hemisphere_cognition.py` has no `em`/`sv`/`sf`/`aff` handling at all,
only `pr`/`ep`/`sc`/`gp`).

The organism's neurons (`LoomNeuron`, `dsf_ai_service/loom_model/
neuron.py`) do have real, chi-related structures, but none of them is
"sample the shared wave field within a covered chi range":

- **`ChiAtlas`** (`neuron.py:448`, from `gualaloom_v4_chi_atlas_l6.py`)
  — a per-neuron familiarity/recall register, populated by that
  neuron's *own* commits, band=2. Not a sampling window onto anything
  external.
- **`BindingAtlas`** (`dsf_ai_service/loom_model/binding_atlas.py`) —
  each neuron's own private wave-cell-shaped recall memory (built on
  the same `tools/wave_spillover.py` primitives `WaveAtlas` uses, but
  a **separate, per-neuron instance**, never the shared one). Its own
  module docstring: "GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207."
  **Directly confirmed from that dispatch's own text
  (`docs/GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2.md`, W1):
  "ONE STORE PER NEURON. Never a shared lattice across neurons: the
  per-neuron ring-position DNA diversity... is the mechanism that
  broke population degeneracy (6/22)."** A shared-field-sampling
  design is not just absent — a prior dispatch deliberately ruled it
  out, on measured evidence, to fix a real regression. Building it now
  would risk reopening exactly that.
- **`_structural_dna(hemi_index, ring_pos, ring_N, ...)`**
  (`embryo.py:86`) — derives `kappa_mult`/`threshold_mult`/`aff_gain`/
  `polarity` (receptor gain, excitability, neuromodulator sensitivity,
  transmitter type) from a neuron's ring position. Chemistry, not a
  chi-range assignment.
- **`LoomNeuron.step(input_signal, tick)`** (`neuron.py:501`) — drives
  each neuron's *own* `krimelack` from whatever `input_signal` is
  explicitly passed in (a word, or a raw array), not from reading any
  shared field at a position-derived address.
- Grepped every file in `dsf_ai_service/loom_model/` for `.wave_atlas`
  — zero matches. The organism never touches `Guala.atlas._wave_atlas`
  or `Guala.wave_atlas` anywhere.

**The wave field and the organism are two real, working, but
completely disconnected systems today.** Wiring 2 as literally
specified — "each hemisphere's neurons sample wave amplitude in their
chi-coverage receptive fields" — would require *inventing* what a
neuron's chi coverage even is (there is no existing formula, spec, or
convention to confirm against), which is exactly "build a substitute"
the dispatch prohibits.

---

## Primitive 3 — Hebbian connection strengthening between neurons: **CONFIRMED REAL** (informal name, real mechanism)

No file in the repo uses the literal word "Hebbian" in production code
(checked case-insensitively, whole tree) — the closest hit is a *test*
comment (`dsf_ai_service/loom_model/tests/test_folding_engaged.py:348`)
that names this exact mechanism "Hebbian update." Substance, not name,
is what matters, and the substance is real:

- **`CouplingsJij`** (`neuron.py:259`) — intra-hemisphere: each
  neuron gets K=16 ring-topology neighbors, wired unconditionally at
  `LoomCluster.__init__` via `_build_ring_topology()`
  (`cluster.py:91,111-140`) — **not** gated behind neuron division (no
  divisions have occurred on the live post-wipe substrate tonight;
  this wiring happens at seed time regardless). Real connection-weight
  matrix `J` per neuron, updated from each neuron's own DSF state
  (`update_from_dsf`, `neuron.py:285-300`), and spike propagation is
  weighted by these J values every tick (`LoomCluster.step` Phase B,
  `cluster.py:161-180`).
- **`CrossHemiCouplings`** (`cross_hemi.py`) — same mechanism between
  hemispheres, for projection neurons, wired in `LoomBrain.__init__`
  (`brain.py:88-118`).

This is real, wired, and already running every tick. **No gap found
here** — but Wiring 3 as specified ("change emission's candidate
scoring to read from Hebbian recall... em, sc, sv hemispheres provide
candidate pool") is built *on top of* Primitive 2's cue-neuron-firing
concept, which does not exist as described — so Wiring 3 cannot be
meaningfully attempted independent of resolving Primitive 2 first.

**Separately, flagging in advance (not the reason for this halt, but
relevant to how Eve resolves it):** the emission candidate path is the
same one the cross-sense-recall dispatch (`GL-RPT-CROSS-SENSE-RECALL-
BUILD-C1-20260706-v1`) found is organism-sourced
(`_brain_emission_candidates` → `organism.recall_fast`), deliberately
disconnected from the atlas per the standing "one mind, one mouth"
ruling, with a documented regression on record for the other time a
second candidate source was added. If Wiring 3's "candidate pool"
means routing hemisphere-neuron Hebbian recall into
`_emit_dynamics`/`_grandurun_select_candidates` directly, that is
*inside* the organism (the brain itself, not a second source) so it
may not trigger the same concern — but this needs its own explicit
confirmation once Primitive 2 is resolved, not an assumption either way
from me.

---

## Recommendation

Not a rejection of the dispatch's goal — the wave field and the
Hebbian mechanism are both real and exactly as described; only the
neuron-samples-shared-field piece is missing, and it is missing for a
documented, deliberate reason (population-degeneracy regression,
GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207). Eve's call on how to
proceed — options surfaced, not decided, per "do not build a
substitute":

1. Confirm chi-coverage receptive fields are genuinely new design
   work (not a rediscovery of something existing), and dispatch that
   as its own scoped build, with its own harness verification —
   ideally with explicit attention to how it avoids reintroducing the
   6/22 degeneracy the per-neuron-only design fixed.
2. Reconsider whether "hemispheric integration" is better served by a
   narrower goal that doesn't require neurons to read the shared
   field at all (e.g., feeding wave-field summary statistics into the
   organism's *existing* explicit-input path, `LoomNeuron.step`'s
   `input_signal`, rather than adding a new passive-sampling
   mechanism).
3. Supersede with a v3 that scopes Wiring 1 (already done, no-op) +
   Wiring 3 alone (Hebbian-recall-driven candidate scoring, fully
   inside the organism, once Eve confirms what "candidate pool" should
   mean here) — deferring the wave-field/neuron connection entirely.

## What was NOT done, and why

No backup was taken — nothing was going to be deployed or mutated, so
there was nothing to protect against. No code was written for any of
the three wirings. `git status` was clean relative to `HEAD` on
`guala-live` before this report; only this report and the dispatch/
scenario files below are being added.

**The v2 scenario did arrive** (`docs/hemispheric_integration_
acceptance_v2.yaml`, alongside the dispatch text, same mechanism as
prior dispatches this session) — not run, since a halt does not
proceed to the harness protocol. Read it for context, and it sharpens
rather than changes the halt: it requires a real `emission` event with
`provenance_hebbian_min: 1` and `must_cite_hebbian_recall: true` —
i.e., it expects Hebbian recall to demonstrably shape what she actually
says, not just an internal/logged-only signal. That makes the "one
mind, one mouth" question flagged under Primitive 3 sharper, not
optional — whatever Eve decides about Primitive 2, Wiring 3's design
will need to explicitly address how a second recall signal enters
composed speech without becoming a second source competing with the
brain, since this scenario will fail without a real, cited effect on
emission.
