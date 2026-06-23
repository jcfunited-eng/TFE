# GL-SPC-SENSORY-CATALOG-EVE-20260621-110

**To:** Joe (canonical), c1 (implementer)
**From:** Eve
**Date:** 2026-06-21
**Re:** Sensory catalog — story-first multi-modal grounding for vocabulary. Revised version.
**Supersedes:** GL-SPC-SENSORY-CATALOG-EVE-20260620-102 (kept in repo for reference; this is the dispatch-ready version)
**Depends on:** F1 transducer (-107, shipped at bfdad9a) and F12 unified chi derivation (-108, shipped at 7d030c1) — both landed on branch.

---

## 0. What changed from -102

Five corrections after reading the shipped F1+F12 code:
- Catalog plugs into the shipped `AtlasReader` protocol as a `CatalogAtlasReader` implementation, not by extending `_generate_initial`
- Scope narrowed to touch/smell/taste (the modalities with parameter pipelines). Visual/sound stay on existing substrate-true paths
- Catalog SQLite rides EFS for persistence across container restarts
- LLM retry path added before falling through to ungrounded
- T7 ceiling claim downgraded from "likely dissolves" to "to be measured"

Everything else from -102 stands.

---

## 1. What this is

A teacher-side, curriculum-layer catalog that generates touch / smell / taste parameter distributions for words Guala encounters in her reading. Lives OUTSIDE the substrate. The substrate never reads catalog directly — the F1 `SensoryTransducer` (shipped) reads from the catalog through the `AtlasReader` protocol.

The catalog turns text-only Gutenberg corpora into grounded multi-modal experience for those three modalities. Visual and sound remain on their substrate-true paths (`visual_krimelack`, `CochlearBank`) — when real image or audio data is fed in, those are already substrate-true. The catalog doesn't fake visual or audio data; that's a separate, much harder question.

## 2. Why this isn't a substrate-true violation

Same as -102 §2. Catalog stores parameter DISTRIBUTIONS (mean + std), never fixed vectors. Substrate samples from distributions on each delivery via the existing `_sample_from_bindings` path. Per-call variability is preserved. Substrate discovers what "warm" or "rabbit" means by accumulating bindings across the cloud of chi addresses each delivery produces (per F12's `transduce_sensory_signals` → krimelack winding → chi).

The LLM that generates the catalog is teacher-side knowledge — analogous to a parent's mental model of "rabbit" shaping how they show one to a child. The child still discovers via the actual stimulus.

If catalog code ever looks like `CATALOG["rabbit"] = {touch: <fixed_vector>}` — that's TOUCH_LIBRARY back from the dead. Refused.

## 3. Architecture

```
Corpus adapter (Gutenberg / Khan / PBS / etc.) loads story sentences
        ↓
Catalog pre-scans entire story BEFORE substrate reads
        ↓
For each unique word: catalog.list_unknown([words]) → unknown subset
        ↓
Batch unknown → CatalogGenerator (LLM call with story context)
        ↓
LLM returns JSON: word → {touch, smell, taste} → {applicable, mean, std}
        ↓
Catalog stores distributions to SQLite on EFS (persistent across restarts)
        ↓
Substrate begins reading story
        ↓
For each touch/smell/taste delivery from guala_give_experience:
    SensoryTransducer.transduce(modality, word, substrate_state)
        ↓
    transducer's atlas_reader is a CatalogAtlasReader
        ↓
    atlas_reader.has_bindings(word, modality)? 
        YES → atlas_reader.get_distribution(word, modality) → mean, std
              _sample_modality_params samples from N(mean, std), clipped [0,1]
        NO  → _generate_initial path (substrate-derivable seed)
        ↓
    generate_*_waveform(params) → physical waveform
        ↓
    transduce_sensory_signals → krimelack winding → chi
        ↓
    Substrate binds via cross-modal binding window
```

## 4. Component specs

### 4.1 `CatalogAtlasReader` class
`dsf_ai_service/curriculum/catalog_atlas_reader.py`

Implements the shipped `AtlasReader` protocol from F1. Backs onto the SQLite catalog store.

API (matches protocol):
- `has_bindings(label: str, modality: str) -> bool` — returns True if catalog has a distribution for (label, modality) AND applicable is True
- `get_binding_params(label: str, modality: str) -> dict` — returns prior_params shape that `_compute_distribution` consumes (see §4.5 protocol detail)
- OR add a new protocol method: `get_distribution(label: str, modality: str) -> (mean: dict, std: dict)` — direct distribution return, no synthetic prior params

V1 audit decides which of those two approaches fits the shipped `_sample_from_bindings` code path most cleanly. If a protocol extension is needed, surface BEFORE writing the catalog reader — the F1 transducer code may need a tiny change.

### 4.2 `Catalog` storage class
`dsf_ai_service/curriculum/sensory_catalog.py`

Persistent SQLite, single-file. **Location: on EFS mount**, not local container disk. Substrate already uses EFS for state; catalog rides the same persistence so container restarts don't drop the catalog.

Schema:
```
catalog_entries(
    word TEXT,
    modality TEXT CHECK(modality IN ('touch','smell','taste')),
    applicable INTEGER NOT NULL,  -- 0 or 1
    mean_json TEXT,               -- NULL if applicable=0
    std_json TEXT,                -- NULL if applicable=0
    source_story TEXT,
    created_at TIMESTAMP,
    update_count INTEGER DEFAULT 0,
    PRIMARY KEY (word, modality)
)
```

API:
- `has(word, modality) -> bool` — entry exists in DB regardless of applicable
- `is_applicable(word, modality) -> bool` — applicable=1
- `get_distribution(word, modality) -> (mean: dict, std: dict) | None`
- `set_entry(word, modality, applicable, mean, std, source_story)`
- `list_unknown(words: list[str]) -> list[str]` — words with NO entry for ANY modality (need full generation pass)
- `update_from_substrate(word, modality, observed_params)` — V2 scope, leave as stub

### 4.3 `CatalogGenerator` class
`dsf_ai_service/curriculum/catalog_generator.py`

Handles the LLM call. Takes a list of unknown words + story context, returns parameter distributions.

API:
- `generate(words: list[str], story_context: str) -> dict[word, dict[modality, dict]]`

Retry behavior:
- Transient API failures (timeout, 5xx, rate limit): retry up to 3 times with exponential backoff (1s, 2s, 4s)
- Permanent failures (auth, malformed request): fail immediately, words marked ungrounded
- Malformed JSON response after retries exhausted: words marked ungrounded; do NOT silently use partial data

LLM brief structure:
```
You are generating sensory parameter distributions for words a learning substrate is reading. Return ONLY JSON.

For each word, return distributions across three modalities: touch, smell, taste.

Modalities and parameters (each parameter ∈ [0,1]):
- touch: temperature, pressure, texture_freq, sharpness, wetness
- smell: chemical_class, concentration
  (note: in practice smell parameters are sweet/putrid/floral/fruity/smoky/earthy/sour/fresh ∈ [0,1] — confirm against substrate consumer interface)
- taste: sweet, sour, salty, bitter, umami

Format per word per modality:
{
  "applicable": true | false,
  "mean": {<param>: <value>, ...} | null,
  "std": {<param>: <value>, ...} | null
}

Words with no signature in a modality (e.g. "rabbit" has no taste signature unless eaten; "of" has no signatures at all) get applicable: false, mean: null, std: null for that modality.

Use realistic distributions. Tight std (~0.05) means the substrate sees nearly identical signal every encounter. Wide std (~0.3) means high variability. Most concrete entities should have moderate std (~0.1-0.15) reflecting that real "warm" varies but stays warm-ish.

Story context (for disambiguation, e.g. rabbit in a children's story vs as food):
"{story_excerpt}"

Words to generate:
{word_list}

Return JSON only. No prose, no markdown fences.
```

V1 audit: confirm the smell parameter set in the shipped F1 code (V1.b from -107 found {sweet, putrid, floral, fruity, smoky, earthy, sour, fresh} — that's 8 channels, not 2). The brief must match the substrate's actual smell channel set or the catalog distributions won't fit the downstream consumer. Surface mismatch BEFORE LLM calls go out.

### 4.4 Curriculum pipeline integration
`dsf_ai_service/curriculum/loader.py` (verify location via V1 audit)

Existing flow (after -92 Gutenberg adapter): adapter → sentences → substrate (via async load_corpus / job_registry).

New flow with catalog:
1. Adapter returns sentences
2. Tokenize via existing word-segmentation path (V1 audit confirms which)
3. Extract unique words
4. `catalog.list_unknown(words)` → unknown list
5. If unknown is non-empty: `CatalogGenerator.generate(unknown, story_excerpt)` → batch result
6. Store entries via `catalog.set_entry(...)` for each (word, modality)
7. Begin substrate read — `guala_give_experience` calls now route through `CatalogAtlasReader`

### 4.5 F1 transducer integration

The shipped `SensoryTransducer.__init__(self, atlas_reader)` takes any object implementing the protocol. Currently `NullAtlasReader` is the production default (every encounter = first encounter).

Wire-in:
- Production substrate creates `CatalogAtlasReader(catalog)` instead of `NullAtlasReader()`
- Existing `_sample_from_bindings` path becomes active for catalog hits
- Existing `_generate_initial` path remains active for catalog misses (graceful fallback)
- No change to `SensoryTransducer` code unless V1 audit surfaces a protocol method mismatch (§4.1)

### 4.6 Modality applicability

Words with `applicable: false` for a modality (e.g. "the", "of", "and" — no sensory signatures) should NOT route through `SensoryTransducer.transduce` for that modality. Either:
- Catalog returns `applicable=false` and the curriculum layer skips that modality delivery for that word
- Or `CatalogAtlasReader.has_bindings` returns True with a "no-op" sentinel that the transducer interprets

V1 audit picks the cleaner integration. Either is substrate-true; preference for the first because it keeps the no-op out of the transducer's hot path.

## 5. Measurable acceptance criteria

T1 first-story batch: load Peter Rabbit (book_id 14838 via Gutenberg adapter from -92). Catalog pre-scan identifies ~150-1500 unknown words depending on tokenization. LLM batch generates distributions. Catalog populates. Substrate reads. PASS: catalog row count > 100 after load; total LLM call count ≤ ceil(unknown_count / batch_size).

T2 per-call variability: deliver "rabbit" via `guala_give_experience(touch=["rabbit"])` 20 times across different ticks. Capture each delivery's parameter values. PASS: std across deliveries for at least 3 of 5 touch parameters > 0.03.

T3 catalog vs no-catalog distinction: deliver "warm" with empty catalog (F1 first-encounter only) vs with catalog populated. Compare parameter distributions. PASS: catalog version's mean for `temperature` is meaningfully higher than empty-catalog uniform-sample mean. Proves catalog adds real semantic structure.

T4 ungrounded word fallthrough: word "blunderbuss" not in catalog and LLM mocked to fail. Delivery via `guala_give_experience(touch=["blunderbuss"])` still succeeds via F1 `_generate_initial` substrate-derivable seed. PASS: no exception; waveform produced with parameters in valid physical range; chi address derived.

T5 modality applicability: deliver "of" via curriculum path. PASS: catalog has entry with applicable=false; no waveform generated for any modality; word token still routes through language-modality chi binding (verify atlas record for word token but not for touch/smell/taste).

T6 substrate-true sanity:
- assert no fixed-vector catalog entries (every applicable=true entry has both mean AND std)
- assert no `if word == "rabbit":` or equivalent label-keyed branches in catalog code
- assert catalog only writes via `set_entry` interface

T7 cross-session persistence on EFS: populate catalog with one story, restart the substrate container, verify catalog state survives. PASS: post-restart, `catalog.has(word, modality)` returns True for previously-populated entries; no LLM regeneration needed.

T8 cost / scale: full Peter Rabbit (~14k word tokens, ~1500 unique) processed in batched LLM calls. PASS: total LLM tokens < 80k (batched, prompt overhead amortized); total wall-clock < 90s on first load.

T9 retry path: LLM mocked to fail twice then succeed. PASS: catalog generation completes successfully on 3rd attempt; no words marked ungrounded.

T10 chi variability preserved through catalog: same "warm" delivered 20 times via catalog path. Capture chi addresses recorded by `transduce_sensory_signals`. PASS: at least 15 of 20 chi addresses distinct (per-call variability survives catalog distribution sampling).

## 6. V1 c1 investigation (return before code)

V1.a — Curriculum loader location. Where does `/api/v1/curriculum/load_corpus` async path do its substrate handoff? That's where the catalog pre-scan inserts.

V1.b — SQLite on EFS. Confirm EFS mount is writable for catalog SQLite file; identify path convention used by substrate state (EFS subdirectory pattern) so catalog rides the same.

V1.c — Anthropic API client. ECS task outbound to api.anthropic.com — confirm allowed (security groups), confirm API key management (Secrets Manager pattern Joe specified). Surface the integration approach.

V1.d — Tokenization. Existing word-segmentation in -92 Gutenberg flow — reuse, don't reinvent. Identify the function.

V1.e — Smell parameter set. The shipped F1 code uses {sweet, putrid, floral, fruity, smoky, earthy, sour, fresh} for smell (8 channels). The -110 spec's LLM brief lists smell as {chemical_class, concentration} (placeholder text from -102). Confirm the 8-channel set is canonical and update the brief accordingly. THIS IS A REAL POTENTIAL MISMATCH — surface explicitly.

V1.f — Protocol method shape. `_sample_from_bindings` calls `atlas_reader.get_binding_params` then `_compute_distribution(prior_params)`. Does the catalog need to fake prior_params (drawing N samples from its stored distribution so `_compute_distribution` rebuilds the same distribution), or is a new protocol method `get_distribution(label, modality) -> (mean, std)` cleaner? Surface preference with rationale.

V1.g — Catalog write-back from substrate observations (V2 scope). Confirm architecture leaves room.

## 7. Implementation phasing

Phase A: Catalog SQLite class + EFS persistence + `list_unknown` / `set_entry` / `get_distribution` API. No LLM yet. Tested standalone.

Phase B: CatalogGenerator with LLM batch call + retry path. Tested with mocked API responses.

Phase C: CatalogAtlasReader plug-in to SensoryTransducer. Substrate uses catalog when available, falls through to NullAtlasReader behavior otherwise.

Phase D: Curriculum pipeline integration. End-to-end test with Peter Rabbit.

## 8. STOP conditions

- LLM consistently returns parameter values outside [0,1] after retries — surface, do NOT silently clamp
- Catalog backend grows unbounded with no eviction policy AND substrate hits EFS quota — surface BEFORE shipping
- Smell parameter set mismatch between shipped F1 code and LLM brief schema is bigger than just naming (e.g., the underlying waveform generator needs different parameters) — surface, this is a design conflict not a typo
- F1 protocol can't be extended cleanly for catalog use — surface, this is V1.f territory
- You find yourself writing per-word special cases ANYWHERE in catalog or curriculum code — STOP and rethink
- EFS write performance is insufficient for catalog access patterns (read-heavy at experience delivery, write-batchy at story load) — surface, may need an in-memory cache layer

## 9. What this enables — to be measured, not assumed

With catalog operational on touch/smell/taste:
- When Guala reads "the rabbit hopped through the garden", touch/smell/taste signals for the concrete words (rabbit, garden) come from LLM-curated distributions instead of the F1 first-encounter uniform sampling
- Each delivery still produces variable chi addresses (per F12 transduction + per-call distribution sampling)
- Per-neuron atlases bind to richer multi-channel signatures, not just text-token chi
- Whether this is enough to produce intra-cluster Sur's-ferrets diversity at Stage 4+ scale — i.e., whether the T7 ceiling dissolves — is a MEASUREMENT we make after deployment, not an assumed outcome of -110

T7 measurement: after Phase D ships and Peter Rabbit has been read through the catalog-grounded path, re-run the Stage 4 mosaic intra-cluster diversity test on the substrate-grown state. Report actual diversity percentage. If it materially improves over -98's 50%, multi-modal grounding is doing real work. If it doesn't, we'll need either deeper multi-modal coverage (sound + visual with real data) or the -98-style coupling-level fix extended further. Either is a follow-up dispatch.

Visual and sound stay on their existing substrate-true paths in this dispatch. Catalog-fed visual/audio synthesis (text-to-image, text-to-audio) is a separate future question requiring different LLM capabilities and a different risk surface. Not in scope for -110.

— Eve
