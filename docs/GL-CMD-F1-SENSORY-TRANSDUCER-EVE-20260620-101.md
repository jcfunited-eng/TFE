# GL-CMD-F1-SENSORY-TRANSDUCER-EVE-20260620-101

**To:** c1
**From:** Eve
**Refs:** GL-SPC-SENSORY-PRIMITIVES-SUBSTRATE-TRUE-EVE-20260620-94 (full spec), F1 finding in -90
**Status:** Hold until -96 deploys clean and `last_s3_backup` populates. Do NOT start before deploy verification.

---

## Scope

Replace `TOUCH_LIBRARY` / `SMELL_LIBRARY` / `TASTE_LIBRARY` with substrate-true `SensoryTransducer`. Extend to all five modalities (visual, sound, touch, smell, taste) — not just the three contaminated dicts. Per Joe's call: full 5-modality, since the catalog work (coming next) targets all five.

Branch only. No deploy. ETA per spec: ~6-8 hours hands-on after V1.

---

## V1 audit (return answers before code)

V1.a. Identify ALL call sites of `TOUCH_LIBRARY`, `SMELL_LIBRARY`, `TASTE_LIBRARY` across the entire `dsf_ai_service/`. Not just the two known sites — surface anything I missed (cache layers, episode log paths, bridge tools, dashboard helpers).

V1.b. For each modality (touch, smell, taste, visual, sound), identify the existing waveform/parameter consumer: what does the substrate input pipeline expect? Dict of channel→array? List of events? Confirm interface for each modality before changing producers.

V1.c. Atlas read API for "prior bindings for label=X modality=Y" — does it exist cleanly or does substrate need a small new index method? Surface BEFORE writing the substrate-discovery branch.

V1.d. Identify any production path that depends on parameter DETERMINISM (same label → same waveform). If found, surface — the substrate-true replacement makes parameters per-call-variable.

V1.e. Visual + sound currently have separate transducer code paths (visual_krimelack, GL_MDL_AUDITORY_CORTEX). Confirm these are substrate-true (no fixed label→param dicts there); if they are, this work doesn't touch them — they stay. If they aren't, surface and we extend the spec.

---

## V2 implementation

`dsf_ai_service/substrate/sensory_transducer.py` — new file. One class:

```
class SensoryTransducer:
    def __init__(self, atlas_reader):
        # atlas_reader is read-only handle for prior-binding queries
        self.atlas_reader = atlas_reader
    
    def transduce(self, modality: str, label: str, substrate_state) -> dict:
        # Branch on whether substrate has prior bindings for (label, modality)
        if self.atlas_reader.has_bindings(label, modality):
            return self._sample_from_bindings(label, modality, substrate_state)
        else:
            return self._generate_initial(label, modality, substrate_state)
    
    def _generate_initial(self, label, modality, substrate_state) -> dict:
        # First encounter: deterministic per (label, modality) but per-call-variable
        seed_base = hash((label, modality)) & 0xFFFFFFFF
        seed = seed_base ^ substrate_state.tick
        rng = np.random.default_rng(seed)
        return self._sample_modality_params(modality, rng, distribution=None)
    
    def _sample_from_bindings(self, label, modality, substrate_state) -> dict:
        # Substrate-discovered: parameters drawn from accumulated binding distribution
        prior_params = self.atlas_reader.get_binding_params(label, modality)
        distribution = self._compute_distribution(prior_params)
        seed = hash((label, modality, substrate_state.tick)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        return self._sample_modality_params(modality, rng, distribution=distribution)
    
    def _sample_modality_params(self, modality, rng, distribution) -> dict:
        # Per-modality physical-range sampling
        if modality == "touch": return self._touch_params(rng, distribution)
        if modality == "smell": return self._smell_params(rng, distribution)
        if modality == "taste": return self._taste_params(rng, distribution)
        if modality == "visual": return self._visual_params(rng, distribution)
        if modality == "sound": return self._sound_params(rng, distribution)
        raise ValueError(f"unknown modality: {modality}")
```

Per-modality samplers — physical ranges only, no label-keyed dicts:
- `_touch_params`: temperature ∈ [0,1], pressure ∈ [0,1], texture_freq ∈ [0,1], sharpness ∈ [0,1], wetness ∈ [0,1]
- `_smell_params`: chemical_class ∈ [0,1] (continuous), concentration ∈ [0,1]
- `_taste_params`: sweet/sour/salty/bitter/umami components each ∈ [0,1]
- `_visual_params`: dominant_hue, saturation, brightness, spatial_complexity, motion each ∈ [0,1]
- `_sound_params`: fundamental_freq, harmonic_richness, amplitude, duration_class each ∈ [0,1]

When `distribution=None` (first encounter): uniform sample in [0,1] for each param.
When `distribution` provided (subsequent): sample from N(mean_i, std_i) clipped to [0,1] for each param i.

NO fixed-value lookup. No "warm temperature is 0.7" anywhere in the code.

---

## V3 wire-in

- `guala_give_experience` in app.py → instead of `TOUCH_LIBRARY[label]`, call `SensoryTransducer().transduce(modality, label, substrate_state)`
- Returned param dict feeds into existing `generate_touch_waveform` / `generate_smell_waveform` / `generate_taste_waveform` — those functions stay, they're substrate-true
- For visual and sound: confirm via V1.e whether to integrate or leave alone

---

## V4 what to delete

After all call sites are wired through `SensoryTransducer`:
- `TOUCH_LIBRARY`, `SMELL_LIBRARY`, `TASTE_LIBRARY` dicts from `sensory_generators.py`
- `libraries = {"touch": ..., "smell": ..., "taste": ...}` lookup wherever it appears
- Dead `TOUCH_LIBRARY` import in `loom_model/substrate_dna.py:35` (F11)

---

## V5 tests

`dsf_ai_service/tests/test_sensory_transducer.py`:

T1 first-encounter variability: empty atlas, transduce("touch", "warm") twice in same substrate session → params differ in at least 3 of 5 channels (substrate tick advances between calls)

T2 first-encounter range coverage: 100 first-encounter calls for "warm" with empty atlas → temperature std > 0.15 (parameters span roughly half of [0,1])

T3 convergence: seed atlas with 50 prior "warm" bindings centered at temperature ≈ 0.8, std=0.1 → subsequent calls sample within 0.1 of 0.8

T4 modality separation: transduce("touch", "warm") and transduce("smell", "warm") use different param channels (no cross-modal collision)

T5 bridge backward compat: `guala_give_experience(touch=["warm"])` still returns a waveform of correct shape, downstream consumers (cross-modal binding window, atlas record) work unchanged

T6 substrate-true sanity:
- assert no dict in `sensory_transducer.py` maps label strings to fixed parameter vectors
- assert no `if label == "warm":` branches
- assert no static lookup tables of any kind

T7 atlas integration: after 50 calls to transduce("touch", "warm") with the atlas wired in, atlas shows 50 new touch bindings for "warm"; on call 51, `_sample_from_bindings` is invoked (not `_generate_initial`)

T8 determinism within session: same label + same tick → identical params (so the substrate's own deterministic-replay code works); different ticks → different params

---

## V6 STOP conditions

- You find any path that NEEDS deterministic same-label-same-params behavior — surface BEFORE breaking it
- Atlas has no clean read API for "prior bindings for (label, modality)" and you'd need to add a substantial new index — surface, don't quietly add it
- The bridge `guala_give_experience` interface needs to change for the substrate side to work — surface BEFORE breaking Joe's bridge calls
- You reach for fixed-value sampling defaults that look label-specific — that's the contamination this fix exists to remove

---

## V7 report

Commit SHA, branch, all test PASS/FAIL with std/mean printouts where applicable, list of all sites changed.

---

Branch only. No deploy. -96 must verify clean first.
