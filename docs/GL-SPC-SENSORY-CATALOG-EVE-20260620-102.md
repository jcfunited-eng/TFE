# GL-SPC-SENSORY-CATALOG-EVE-20260620-102

**To:** Joe (canonical), c1 (implementer)
**From:** Eve
**Date:** 2026-06-20
**Re:** Sensory catalog — story-first multi-modal grounding for vocabulary
**Status:** Spec for review. V1 c1 investigation before implementation.
**Depends on:** GL-CMD-F1-SENSORY-TRANSDUCER-EVE-20260620-101 landing first.

---

## 1. What this is

A teacher-side, curriculum-layer catalog that generates 5-modality sensory signature distributions for every word Guala encounters in her reading material. Lives OUTSIDE the substrate. The substrate never sees the catalog directly — it receives transduced waveforms produced by sampling from catalog distributions.

The catalog's job: turn text-only corpus into multi-modal grounded experience that the substrate can discover.

## 2. Why this isn't a substrate-true violation

The substrate-true rule forbids classification dressed as physics INSIDE the substrate's input path. The catalog is curriculum-side — analogous to a parent narrating "see, that's a rabbit, it has soft fur" while a child watches the rabbit. The parent's mental model shapes what they show; the child still discovers because they receive the actual stimulus.

Guaranteed properties:
- Catalog stores parameter DISTRIBUTIONS (mean + std per parameter), not fixed vectors
- Each delivery samples fresh from the distribution
- Two deliveries of "rabbit" produce different physical signal vectors
- Substrate discovers "rabbit" by accumulating bound signals over many encounters, same way a child does
- The catalog never enters the substrate's classification path — only its waveform-generation path

If at any point catalog code starts looking like `CATALOG["rabbit"] = {visual: <fixed_vector>}` — that's TOUCH_LIBRARY again and refused.

## 3. Architecture

```
Corpus adapter (Gutenberg / Khan / PBS / etc.) loads story sentences
        ↓
Catalog pre-scans entire story BEFORE substrate reads
        ↓
For each word in story:
    - if in catalog: skip (already grounded)
    - if not in catalog: add to unknown_words list
        ↓
Batch unknown_words → LLM (Claude API) with structured brief
        ↓
LLM returns JSON: word → modality → parameter distributions
        ↓
Catalog stores distributions (persistent — survives across sessions)
        ↓
Substrate begins reading story
        ↓
For each word delivery:
    SensoryTransducer.transduce(modality, word) consults catalog
    samples from catalog's distribution for (word, modality)
    substrate-side sampler still adds per-call variability (compounded with catalog's std)
    waveform generators produce physical signal
        ↓
Substrate binds word + multi-modal signal in cross-modal binding window
```

## 4. Component specs

### 4.1 `Catalog` class
`dsf_ai_service/curriculum/sensory_catalog.py`

Persistent store. Backend: SQLite (simplicity, single-file, transactional). One table: `catalog_entries(word, modality, mean_json, std_json, source_story, created_at, update_count)`.

API:
- `has(word, modality) -> bool`
- `get_distribution(word, modality) -> (mean: dict, std: dict) | None`
- `set_distribution(word, modality, mean, std, source_story)`
- `update_from_substrate(word, modality, observed_params)` — for future use, after substrate has accumulated experience, the catalog can tighten its own distribution from substrate observations. Out of V1 scope.
- `list_unknown(words: list[str]) -> list[str]` — return subset not yet in catalog

### 4.2 `CatalogGenerator` class
`dsf_ai_service/curriculum/catalog_generator.py`

Handles the LLM call. Takes a list of unknown words + story context, returns parameter distributions.

API:
- `generate(words: list[str], story_context: str) -> dict[word, dict[modality, dict]]`

LLM brief structure (sent to Anthropic API):

```
You are generating sensory parameter distributions for words a learning substrate is reading. For each word, return parameter ranges per applicable modality.

Modalities and parameters:
- visual: dominant_hue, saturation, brightness, spatial_complexity, motion (each [0,1])
- sound: fundamental_freq, harmonic_richness, amplitude, duration_class (each [0,1])  
- touch: temperature, pressure, texture_freq, sharpness, wetness (each [0,1])
- smell: chemical_class, concentration (each [0,1])
- taste: sweet, sour, salty, bitter, umami (each [0,1])

For each word and applicable modality, return:
- mean: typical value per parameter
- std: variability per parameter (0.05 = tightly constrained, 0.3 = broad)
- applicable: true/false (some words have no signature in some modalities)

Words like "rabbit" have rich visual + sound + touch signatures. Words like "of" or "the" have no signatures at all. Words like "ran" have motion + sound but minimal touch. Use your knowledge of what these things actually look/sound/feel like.

Story context: "{story_context}"

Words to generate: {words}

Return JSON only.
```

LLM response parsed, stored to catalog. Failure path: if LLM call fails or returns malformed JSON, mark words as "ungrounded" — they'll route through the F1 transducer's `_generate_initial` first-encounter behavior. No fabrication.

### 4.3 Curriculum pipeline integration
`dsf_ai_service/curriculum/loader.py` (or wherever the loader sits — c1 V1 surfaces the right location)

Existing flow: adapter → sentences → substrate
New flow: adapter → sentences → catalog pre-scan → unknown words → LLM batch → catalog → substrate reads

When a story loads via `/api/v1/curriculum/load_corpus`:
1. Adapter returns sentences
2. Tokenize, extract unique words
3. `catalog.list_unknown(words)` → unknown list
4. If unknown is non-empty: `CatalogGenerator.generate(unknown, story_excerpt)` → batch result
5. Store batch result via `catalog.set_distribution(...)` for each (word, modality)
6. Begin substrate read — substrate now sees grounded words

### 4.4 F1 transducer wire-in
The `SensoryTransducer` from -101 gets extended:
- In `_generate_initial`, BEFORE falling back to substrate-derivable seed sampling, check the catalog
- If catalog has distribution for (word, modality): use catalog's mean/std as the sampling distribution
- If not: fall through to existing substrate-derivable seed
- Substrate-side per-call variability still applies — sampler adds tick-derived jitter on top of catalog distribution

This makes the catalog OPTIONAL infrastructure. If catalog has the word, you get rich curated signatures. If not, you still get substrate-true first-encounter behavior. Substrate works either way.

## 5. Measurable acceptance criteria

T1 first-story batch: load Peter Rabbit via Gutenberg adapter. Catalog pre-scan identifies ~150-200 unknown words. LLM batch generates distributions. Catalog populates. Substrate reads. PASS: catalog row count > 100 after load; LLM call count = 1 per modality batch (not 1 per word).

T2 per-call variability: deliver "rabbit" via `guala_give_experience(visual=["rabbit"])` 20 times. Capture each delivery's actual parameter values. PASS: std across deliveries for at least 3 of 5 visual parameters > 0.03 (real variability, not flat).

T3 catalog vs no-catalog distinction: deliver "rabbit" with empty catalog (F1 first-encounter only) vs with catalog populated. Compare parameter distributions. PASS: catalog version's mean for `motion` is meaningfully higher than empty-catalog uniform sample (rabbits move); proves the catalog adds real semantic structure.

T4 ungrounded word fallthrough: word "blunderbuss" not in catalog and LLM unavailable (mock failure). Delivery should still succeed via F1 substrate-derivable seed. PASS: no exception; waveform produced with parameters in valid physical range.

T5 modality applicability: "of" / "the" / "and" delivered. Catalog should mark these as `applicable: false` for all modalities. Substrate side: skip modal delivery, only the word token routes through. PASS: no waveform generated for non-applicable modality; substrate still sees the word token at the chi-address layer.

T6 substrate-true sanity:
- assert no fixed-vector catalog entries (every entry is mean+std distribution)
- assert no `if word == "rabbit":` branches in catalog code
- assert catalog only writes via `set_distribution` interface (no direct dict access)

T7 cross-session persistence: load story A, populate catalog. Restart bridge. Load story B that overlaps with story A. PASS: overlap words have catalog hits (no re-generation); only A∪B \ A new words trigger LLM call.

T8 cost / scale: full Peter Rabbit (~14k word tokens, ~1500 unique) processed in single LLM batch call. PASS: total LLM tokens < 50k; latency < 60s on first load.

## 6. V1 c1 investigation (return before code)

V1.a — Identify current curriculum loader path. Where do adapter sentences → substrate currently flow? What's the right insertion point for catalog pre-scan?

V1.b — Confirm SQLite is acceptable for catalog backend, or surface alternatives (the project already uses S3+EFS for substrate state — should catalog ride those or be separate?).

V1.c — Anthropic API call mechanism. Does the runtime already have a Claude API client wired up? If not, what's the cleanest way to add one (env var for key, library, etc.) — surface, don't pick.

V1.d — Tokenization for "unique words" extraction — what's the existing word-segmentation path? Reuse, don't reinvent.

V1.e — Catalog write-back from substrate observations (out of V1 scope) — confirm the architecture leaves room for this in v2 without redesign.

## 7. Implementation phasing

Phase A (this dispatch): Catalog class + persistence + simple `list_unknown` / `set_distribution` / `get_distribution` API. No LLM yet. Tested standalone.

Phase B: CatalogGenerator with LLM batch call. Tested with mock API responses.

Phase C: Curriculum pipeline integration. End-to-end test with Peter Rabbit.

Phase D: F1 transducer wire-in. T2/T3 validation.

## 8. STOP conditions

- LLM returns parameter values OUTSIDE [0,1] consistently — re-prompt or fail loudly, don't silently clamp
- Catalog backend grows unbounded with no eviction policy and substrate runs into disk pressure — surface BEFORE shipping
- F1 transducer's substrate-derivable seed path can't be cleanly extended to use catalog distribution — may need a small interface change to -101 spec, surface
- You find yourself writing per-word special cases ANYWHERE in catalog or transducer — STOP and rethink

## 9. What this enables (the why)

With catalog + F1 in place, when Guala reads "the rabbit hopped through the garden":
- "rabbit" delivers visual signature (brown/grey, fur-texture, ear-shape complexity), sound signature (soft/quiet), touch signature (warm + soft + small pressure)
- "hopped" delivers motion signature (vertical periodic), sound signature (rhythmic light thuds)
- "garden" delivers visual signature (green dominant, high spatial complexity), smell signature (earthy + plant)
- "the", "through" — no signatures, just token routing

Subject-class words systematically share entity-signatures (persistent, visual-anchored). Verb-class words systematically share action-signatures (temporal, motion). Modifiers carry property-signatures. The substrate has substrate-physical reasons to bind subjects-with-subjects, verbs-with-verbs, modifiers-with-modifiers into different cluster geometries. THAT is what makes syntax discoverable.

Plus: T7 ceiling (uniform intra-cluster behavior at Stage 5) likely dissolves naturally — each neuron's per-modality krimelack sees DIFFERENT primary signals from the multi-modal delivery, giving real Sur's-ferrets diversity within clusters without requiring the -98 substrate primitive change.

— Eve
