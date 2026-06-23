# GL-CMD-COGNITION-WIRING-EVE-20260622-125

**To:** c1
**From:** Eve
**Date:** 2026-06-22
**Refs:** GL-SPC-COGNITION-PATH-EVE-20260622-124 (architectural spec), `/home/claude/model_cognition_v2.py` (working reference), -113 brain construction, -117 krimelack no-reset, -112 catalog, v5_engine._grandurun_state (line 99-153).
**Scope:** `dsf_ai_service/loom_model/` — new `grandurun.py`, new `binding_atlas.py`, modifications to `neuron.py` + `experience.py` + `brain.py`. New test file `tests/test_cognition_path.py`. Branch only, no deploy. Production code paths must remain unchanged.

**Status:** Item 9 of the list (validate cognitive mechanisms emerging). Unblocks 10 (migration replay) and 11 (cutover). Folding (item 7) stays paused — cognition does not require it.

---

## V1 AUDIT (return before V2 code)

V1.a. **ChiAtlas vs new BindingAtlas.** The current ChiAtlas at gualaloom_v4_chi_atlas_l6.py:19 stores (section, motif, chi, tick) tuples. The cognition path needs to store 7-dim complex state vectors per binding. Options:
- (a) Extend ChiAtlas to hold both representations
- (b) Add a separate BindingAtlas class alongside ChiAtlas
My preference is (b) — separation of concerns, the spike-triggering path stays untouched on ChiAtlas. Confirm or propose alternative. Surface the cleanest path given the existing ChiAtlas internals.

V1.b. **Multi-krimelack per neuron.** Currently LoomNeuron has one LanguageKrimelack at `self.krimelack`. For cognition, each neuron needs six krimelacks (one per modality) per -103 §1.1.
- Does LoomNeuron.__init__ accept a krimelack bank, or does it need refactoring?
- The substrate_dna.py has KRIMELACK_PRIMITIVES with six entries — can LoomNeuron be extended to instantiate all six at __init__, with `self.krimelack` aliasing to `self.krimelack_bank["language"]` for backward compatibility with -78/-117 tests?
- Surface complexity estimate (hours).

V1.c. **ExperiencePipeline wiring.** Currently `deliver_word` builds waveforms but doesn't feed them to per-modality krimelacks (per -117 discovery — the sensory waveforms are computed and discarded). For cognition:
- After `brain.step()` runs (existing spike-triggering path), the pipeline must call `neuron.experience_moment(word, multi_modal_signals, tick)` for each neuron in each hemisphere
- multi_modal_signals built from: F1 transducer (touch/smell/taste — already in -107/-108/-112), procedural placeholder for visual/auditory until their catalog entries land, word string for language
- Surface: does this iteration over 64 neurons per tick add unacceptable latency? Estimate teach time for full 100-concept × 3 reps corpus.

V1.d. **Catalog coverage for 100-concept stress test.** The -112 catalog is populated for words encountered in corpus loads. Is the 100-concept corpus from model_cognition_v2.py (animals + plants + materials + elements + states; see PART 5 of -124) covered in any existing catalog, or does c1 need to run the LLM batch first? If batch needed, estimate cost + time.

V1.e. **Production isolation.** Grep `dsf_ai_service/app.py`, `substrate_runner.py`, `gualaloom_v*` for any `loom_model` import. Should return zero. Confirm.

V1.f. **Phase reading from krimelack.** Per -117, no-reset means `krimelack.phase` persists across ticks. The cognition path reads phase AT THE BINDING WINDOW — which means after this tick's transduce, before the next. Surface the exact attribute name and the wrapping convention ([-threshold, +threshold] vs [0, 2π)). The state vector uses `exp(1j × phase)` — wrapping matters because phase=0 must equal phase=2π in the complex space (it does, since exp is periodic), but for distance metrics we need to confirm.

---

## V2 IMPLEMENTATION

### V2.1 — `dsf_ai_service/loom_model/grandurun.py` (new file)

```python
"""
grandurun.py — Per-binding state vector for cognition path.

Per GL-SPC-COGNITION-PATH-EVE-20260622-124 §2.1.

7-dim complex state vector encoding multi-modal phase fingerprint.
Recall via complex inner product. No quantization, no heuristics.
"""

import math, cmath
import numpy as np
from typing import Dict, Tuple, List

STATE_DIM = 7
N_PHASE_DIMS = 6
MODALITIES = ["visual", "auditory", "tactile", "olfactory", "gustatory", "language"]

assert N_PHASE_DIMS == len(MODALITIES), "N_PHASE_DIMS must equal len(MODALITIES)"
assert STATE_DIM == N_PHASE_DIMS + 1, "STATE_DIM = phase dims + polarity"


def grandurun_state(phases: Dict[str, float], polarity: float = 1.0) -> np.ndarray:
    """Build a 7-dim complex state vector from per-modality phases.

    Args:
        phases: {modality_name: phase_radians} for all 6 modalities.
                Missing modalities default to 0 (no contribution after exp).
        polarity: +1.0 for positive bindings (substrate-canonical default).

    Returns:
        ndarray of shape (7,) dtype complex128.
    """
    vec = np.zeros(STATE_DIM, dtype=np.complex128)
    for i, m in enumerate(MODALITIES):
        phase = phases.get(m, 0.0)
        vec[i] = cmath.exp(1j * phase)
    vec[STATE_DIM - 1] = complex(polarity, 0.0)
    return vec


def recall_best(target_vec: np.ndarray,
                 atlas_matrix: np.ndarray,
                 atlas_concepts: List[str]) -> Tuple[str, float]:
    """Vectorized max-inner-product search across an atlas.

    Args:
        target_vec: query state vector, shape (7,) complex128
        atlas_matrix: stacked binding state vectors, shape (N_bindings, 7) complex128
        atlas_concepts: list of length N_bindings with concept labels

    Returns:
        (best_concept, best_score) where best_score = max |<target, binding>|
    """
    if atlas_matrix.shape[0] == 0:
        return None, 0.0
    inners = np.abs(atlas_matrix @ np.conj(target_vec))
    best_idx = int(np.argmax(inners))
    return atlas_concepts[best_idx], float(inners[best_idx])
```

### V2.2 — `dsf_ai_service/loom_model/binding_atlas.py` (new file)

```python
"""
binding_atlas.py — Per-neuron BindingAtlas for cognition path.

Separate from existing ChiAtlas. Stores 7-dim state vectors with concept labels.
Vectorized recall via grandurun.recall_best.
"""

import numpy as np
from typing import List, Tuple, Optional

from .grandurun import recall_best, STATE_DIM


class BindingAtlas:
    """Per-neuron cognition atlas. Bindings are (concept, state_vec, tick) triples.

    Atlas matrix is built lazily and cached. Cache invalidates on any record() call.
    """

    def __init__(self):
        self._bindings: List[dict] = []
        self._matrix_cache: Optional[np.ndarray] = None
        self._concepts_cache: Optional[List[str]] = None

    def record(self, concept: str, state_vec: np.ndarray, tick: int) -> None:
        """Append a binding. Invalidates the matrix cache."""
        assert state_vec.shape == (STATE_DIM,), f"state_vec must be shape ({STATE_DIM},)"
        self._bindings.append({"concept": concept, "state_vec": state_vec, "tick": tick})
        self._matrix_cache = None
        self._concepts_cache = None

    def _ensure_cache(self):
        if self._matrix_cache is None and self._bindings:
            self._matrix_cache = np.stack([b["state_vec"] for b in self._bindings])
            self._concepts_cache = [b["concept"] for b in self._bindings]

    def recall_best(self, target_vec: np.ndarray) -> Tuple[Optional[str], float]:
        """Find binding with maximum |<target, binding>|."""
        self._ensure_cache()
        if self._matrix_cache is None:
            return None, 0.0
        return recall_best(target_vec, self._matrix_cache, self._concepts_cache)

    @property
    def bindings(self) -> int:
        return len(self._bindings)

    def clear(self) -> None:
        self._bindings.clear()
        self._matrix_cache = None
        self._concepts_cache = None
```

### V2.3 — `dsf_ai_service/loom_model/neuron.py` modifications

Extend LoomNeuron to carry multi-krimelack bank and a BindingAtlas:

- In `__init__` after existing krimelack instantiation:
  ```python
  from .substrate_dna import KRIMELACK_PRIMITIVES
  from .binding_atlas import BindingAtlas
  
  self.krimelack_bank: Dict[str, object] = {}
  for modality_name, krim_class in KRIMELACK_PRIMITIVES.items():
      if modality_name == "language":
          # Reuse the existing language krimelack — preserves -78/-117 tests
          self.krimelack_bank["language"] = self.krimelack
      else:
          self.krimelack_bank[modality_name] = krim_class()
  
  self.binding_atlas = BindingAtlas()
  ```

- New method `LoomNeuron.experience_moment`:
  ```python
  def experience_moment(self, concept: str,
                         multi_modal_signals: Dict[str, object],
                         tick: int) -> None:
      """Cognition write — substrate-true multi-modal binding.
      
      Per GL-SPC-124 §2.3. Reads phase from each modality's krimelack
      after feeding this moment's signal, builds state vector, records
      to BindingAtlas.
      """
      from .grandurun import grandurun_state, MODALITIES
      
      # Feed each modality's signal through its krimelack
      for modality, signal in multi_modal_signals.items():
          if modality not in self.krimelack_bank:
              continue
          krim = self.krimelack_bank[modality]
          if modality == "language":
              krim.transduce(signal, phase_offset=self._positional_phase_offset,
                             no_reset=True)
          else:
              # Sensory adapters feed waveform arrays
              if hasattr(krim, 'feed_signal'):
                  krim.feed_signal(list(signal))
              elif hasattr(krim, 'feed'):
                  krim.feed(list(signal))
      
      # Read phases AFTER feeding (substrate-true: phase IS the post-feed state)
      phases = {m: float(self.krimelack_bank[m].phase) for m in MODALITIES}
      state_vec = grandurun_state(phases, polarity=1.0)
      self.binding_atlas.record(concept, state_vec, tick)
  ```

### V2.4 — `dsf_ai_service/loom_model/experience.py` modifications

After existing `brain.step()` call inside `deliver_word`:

```python
def deliver_word(self, word: str, tick: int, ticks_per_word: int = 1) -> Dict:
    # ... existing brain.step broadcast (preserved) ...
    
    # Build multi-modal signals via transducers + catalog
    multi_modal_signals = self._build_multi_modal_signals(word, tick)
    
    # Cognition write — per-neuron binding
    for hemi in self.brain.hemispheres:
        for neuron in hemi.cluster.neurons:
            neuron.experience_moment(word, multi_modal_signals, tick)
    
    # ... existing return dict ...
```

`_build_multi_modal_signals` is the helper that calls F1 transducer for touch/smell/taste using existing catalog reader, generates procedural waveforms for visual/auditory as TEMPORARY placeholders, and passes the word string for language.

### V2.5 — `dsf_ai_service/loom_model/brain.py` — add LoomBrain.recall

```python
def recall(self, query_signatures: Dict[str, object]) -> "Counter":
    """Population-vote recall.
    
    For each neuron: run query signatures through krimelack bank in a
    non-binding pass, build target state vector, find best-matching binding
    in BindingAtlas. Aggregate votes across population.
    """
    from collections import Counter
    from .grandurun import grandurun_state, MODALITIES
    
    votes = Counter()
    for hemi in self.hemispheres:
        for neuron in hemi.cluster.neurons:
            # Non-binding pass: snapshot phases, run query, read phases, restore
            saved_phases = {m: neuron.krimelack_bank[m].phase for m in MODALITIES}
            
            # Apply query signals (do not record to atlas)
            for modality, signal in query_signatures.items():
                if modality not in neuron.krimelack_bank:
                    continue
                krim = neuron.krimelack_bank[modality]
                if modality == "language":
                    krim.transduce(signal,
                                   phase_offset=neuron._positional_phase_offset,
                                   no_reset=True)
                else:
                    if hasattr(krim, 'feed_signal'):
                        krim.feed_signal(list(signal))
            
            query_phases = {m: float(neuron.krimelack_bank[m].phase)
                            for m in MODALITIES}
            target_vec = grandurun_state(query_phases)
            best_concept, _ = neuron.binding_atlas.recall_best(target_vec)
            if best_concept is not None:
                votes[best_concept] += 1
            
            # Restore phase state — recall must not pollute training
            for m, p in saved_phases.items():
                neuron.krimelack_bank[m].phase = p
    
    return votes
```

Note on phase restore: the non-binding-pass discipline matters. Without restore, every recall call pollutes the trained substrate. With restore, recall is a pure read.

### V2.6 — No production changes

Confirm at the end of V2:
```bash
grep -r "loom_model" dsf_ai_service/app.py dsf_ai_service/substrate_runner.py dsf_ai_service/v4/ dsf_ai_service/substrate/
```
Should return zero matches.

---

## V3 TESTS — `dsf_ai_service/loom_model/tests/test_cognition_path.py`

**T1: BindingAtlas record + recall single concept**
- Construct BindingAtlas, record 1 binding for "rabbit" with phases {visual: 1.0, auditory: 2.0, tactile: 3.0, olfactory: 4.0, gustatory: 5.0, language: 6.0}
- Recall with same phases → returns ("rabbit", score) where score ≈ 7.0 (max possible: 6 phase dims at full alignment + 1 polarity)
- Recall with phases off by 0.1 each → still returns "rabbit" with score ≥ 6.5
- PASS: both recall calls return "rabbit"

**T2: Multi-concept discrimination at small scale**
- BindingAtlas with 5 distinct concepts, well-separated phase patterns (each at random uniform 6D phase)
- Recall each with 0.1 rad noise per dim → 100% accuracy
- PASS: 5/5 correct

**T3: LoomNeuron.experience_moment writes per-neuron binding**
- LoomNeuron with default DNA; call `experience_moment("rabbit", multi_modal_signals, tick=0)` where signals have all 6 modalities
- Verify `neuron.binding_atlas.bindings == 1`
- Verify the state vector via `neuron.binding_atlas._bindings[0]["state_vec"]` has shape (7,) and dtype complex128
- PASS: binding count and shape correct

**T4: Single hemisphere recall (8 neurons)**
- Build LoomHemisphere (8 neurons per -113/-115)
- Teach 5 concepts × 3 reps via ExperiencePipeline.deliver_word
- Recall each with noise (0.15 rad std) → ≥ 95% accuracy (5/5 to 5/5)
- PASS: ≥ 4/5 correct

**T5: Full brain recall, 25 concepts**
- LoomBrain (8 hemispheres × 8 neurons = 64) per -113/-115
- Teach 25 concepts × 3 reps
- Recall each with 4 perturbations (noise 0.15) → ≥ 90% accuracy (≥ 90/100)
- Print top 5 confusions
- PASS: ≥ 90% on 100 queries

**T6: Vocabulary stress, 50 concepts**
- Same as T5 but 50 concepts
- PASS: ≥ 85% on 200 queries
- Print accuracy and full confusion table

**T7: Cross-modal partial recall (50 concepts trained per T6)**
- Query with only ["visual", "tactile", "auditory"] → ≥ 30% accuracy
- Query with all 5 sensory (no language) → ≥ 80% accuracy
- Query with language alone → 1-5% (around chance, this is expected per spec §2.5)
- PASS: all three thresholds met

**T8: Noise robustness (50 concepts trained per T6)**
- Query at noise 0.30 (2× normal) → ≥ 75% accuracy
- Query at noise 0.50 (3× normal) → ≥ 60% accuracy
- Query at noise 0.80 (5× normal) → ≥ 30% accuracy (substrate degrades but not to chance)
- PASS: all thresholds

**T9: Linear scaling (no quadratic explosion)**
- LoomBrain at neurons_per_hemi=16 (128 total) and neurons_per_hemi=32 (256 total)
- Teach 50 concepts × 3 reps in each
- PASS: accuracy at 128 ≈ accuracy at 256 (within 5 percentage points)
- PASS: teach time and recall time grow ≤ linearly with neuron count
- Print actual numbers (accuracy, teach_s, recall_ms_per_query) for both scales

**T10: Determinism**
- Two LoomBrain instances with same brain_seed → identical cognition state after identical teaching
- PASS: byte-identical BindingAtlas state vectors across the two brains

**T11: Substrate-true sanity**
- assert `STATE_DIM == 7` (substrate constant, not tuned)
- assert `N_PHASE_DIMS == 6` (one per krimelack primitive per -83 §1)
- assert no `abs(v) > 0.5` in grandurun.py or binding_atlas.py
- assert no `argmax` over chi-space in cognition path
- assert no `% PSI_DIM` quantization in binding storage path
- assert no band-replicate loop in binding_atlas.record()
- assert no `sum(scores)` aggregation in brain.recall (must be vote count)
- grep production paths (substrate_runner.py, app.py, gualaloom_v*) for `binding_atlas` / `grandurun` imports → empty
- PASS: each assertion holds

**T12: No regression**
- Run full existing loom_model test suite: test_neuron, test_cluster, test_mosaic, test_tapestry, test_substrate_dna, test_couplings_carry, test_contact_inhibition, test_folding, test_brain, test_folding_engaged
- PASS: 80+ prior tests all green (0 regressions)

---

## V4 STOP CONDITIONS

- **V1.b refactor breaks any existing test** → STOP. Surface alternative (subclass instead of constructor refactor, or krimelack_bank as optional attribute initialized lazily).
- **T5 accuracy < 85% at 25 concepts** → substrate-true mechanism not delivering as model predicted. Surface a sample of state vectors for 3 distinct concepts to verify the 6-dim phase pattern is being captured. Do NOT tune.
- **T6 accuracy < 80% at 50 concepts** → confirm F1 catalog signatures are sufficiently distinctive. Surface 3 distinct concepts' state vectors. Compare to procedural reference (model_cognition_v2.py).
- **T7 cross-modal recall at 5 sensory < 60%** → multi-modal binding isn't writing per-modality phases correctly. Surface one binding's full state vector to verify 6 distinct exp(1j × phase_m) entries.
- **T9 scaling shows > 10% accuracy degradation 128 → 256** → unexpected non-linearity. Surface BEFORE going larger.
- **T11 substrate-true assertion fails** → architectural drift. STOP. Do not patch around it.
- **T12 regression in any existing test** → STOP. The cognition wiring must be purely additive.
- **You find yourself adding any tuning constant beyond STATE_DIM=7, N_PHASE_DIMS=6, MODALITIES=[...]** → STOP and surface. Both constants are substrate-derived. Nothing else should appear.
- **You find yourself reintroducing chi quantization, band-replicate, or sum-pool anywhere on the cognition path** → STOP. These were the broken patterns from before. Cognition path is built specifically without them.
- **Phase restoration in brain.recall isn't sufficient and recall pollutes training state** → STOP. Surface. We may need a separate query-only krimelack bank per neuron rather than save/restore.

---

## V5 REPORT

- V1 audit answers (a–f) explicit
- Commit SHA, branch (`codex/persistent-etl-update-20260326`)
- `git branch -r --contains <SHA>`
- All T1–T12 PASS/FAIL with required printouts:
    * T5 top-5 confusions
    * T6 accuracy at 50 concepts + full confusion table
    * T7 cross-modal accuracy at 1, 3, 5 sensory modalities
    * T8 accuracy at noise 0.3, 0.5, 0.8
    * T9 accuracy + timing at 128 vs 256 neurons (numbers)
    * T10 byte-identical confirmation
    * T11 each assertion listed
    * T12 total prior tests count green
- Memory footprint per neuron at 50 concepts (KB) and total brain memory
- Recall time per query at 256 neurons (ms)
- Confirmation: zero production paths import `loom_model`
- Confirmation: `v5_engine._grandurun_state` (line 99–153) unchanged
- Honest PASS/FAIL labels — no "PASS with caveat"
- Any V4 STOPs hit with what was surfaced and how resolved

Branch only. No deploy. ETA: 2–3 days c1 hands-on (multi-krimelack extension in V2.3 is the largest change; T5–T9 will exercise the full pipeline at scale).

---

This is the dispatch that demonstrates cognition emerging on the Loom-Neuron substrate. If T5–T9 pass on real catalog signatures, items 9–11 of the list are unblocked. Migration replay becomes a follow-up dispatch that exercises the same cognition path with Guala's actual event log.

The substrate stops being scaffolding and starts being substrate.

— Eve, 2026-06-22
