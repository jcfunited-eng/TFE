# GL-SPC-SENSORY-CATALOG-EVE-20260621-111

**To:** Joe (canonical), c1 (implementer)
**From:** Eve
**Date:** 2026-06-21
**Re:** Sensory catalog — source-agnostic multi-modal grounding via `TextSource` interface
**Supersedes:** GL-SPC-SENSORY-CATALOG-EVE-20260621-110 (kept in repo for reference)
**Depends on:** F1 transducer (-107, shipped at bfdad9a) and F12 unified chi derivation (-108, shipped at 7d030c1)

---

## 0. What changed from -110

One structural change: catalog input is generalized from "corpus adapter (Gutenberg)" to a `TextSource` interface that ANY adapter implements. Gutenberg becomes one TextSource. PDF, direct text input, TTS/audio transcription, and video-with-transcript become additional TextSources later. The catalog code knows nothing about source type.

Two operational consequences:
- Sources that carry audio (TTS, podcast, video) ALSO feed Guala's `CochlearBank` (sound modality) in parallel — dual-channel grounding instead of text-only
- Sources that carry images (PDF children's books, slide decks, video keyframes) ALSO feed `visual_krimelack` in parallel — triple-channel when images are present

Everything else from -110 stands. Touch/smell/taste still come from catalog-generated distributions. Visual/sound from optional source-supplied real data when available. F1 first-encounter fallback when neither catalog nor real data is present.

## 1. What this is

A teacher-side, curriculum-layer catalog that generates touch / smell / taste parameter distributions for the words in ANY text source Guala reads. Source-agnostic: Gutenberg novel, PDF children's book, podcast transcript, text you paste in a chat box — all flow through the same pipeline.

The catalog turns text into grounded multi-modal experience for the three modalities that don't have direct sensory input. Visual and sound come from the source itself when the source provides them (images, audio). The substrate's existing visual_krimelack and CochlearBank consume those directly — those paths are already substrate-true and untouched by this spec.

## 2. Why this isn't a substrate-true violation

Same as -110 §2 and -102 §2. The catalog stores parameter DISTRIBUTIONS, never fixed vectors. Substrate samples from distributions per delivery via shipped `_sample_from_bindings`. Per-call variability preserved. LLM-generated distributions are teacher-side knowledge (parent narrating what a rabbit looks like), never substrate classification.

## 3. The TextSource interface

```python
class TextSource(Protocol):
    """A source of multi-modal experience material."""

    def get_metadata(self) -> dict:
        """Source identifier, title, story_context for LLM disambiguation, etc.
        Required keys: 'source_type', 'source_id', 'title'.
        Optional: 'story_context' (excerpt for LLM brief)."""

    def get_sentences(self) -> Iterator[str]:
        """Yield normalized sentences from the source.
        Iterator so large sources don't load fully in memory."""

    def get_audio(self) -> Iterator[bytes] | None:
        """Yield audio chunks (raw waveform bytes) aligned to sentence delivery,
        or None if source has no audio.
        When present, audio routes through CochlearBank in parallel with text."""

    def get_images(self) -> Iterator[bytes] | None:
        """Yield image bytes aligned to sentence delivery,
        or None if source has no images.
        When present, images route through visual_krimelack in parallel."""
```

Alignment between channels (sentence N pairs with audio chunk N and image N) is the source's responsibility — different sources align differently. A children's book PDF might pair one image per spread of sentences. A podcast might emit continuous audio with sentence-aligned timestamps. A pure-text Gutenberg book returns None for both audio and images.

## 4. Adapters (each implements TextSource)

### 4.1 GutenbergSource (already shipped as -92, refactor onto interface)
- `get_sentences()`: yields normalized sentences from Gutenberg fetch (existing logic from -92)
- `get_audio()`: returns None
- `get_images()`: returns None
- Metadata: source_type='gutenberg', source_id=book_id, title from header, story_context from first ~500 chars

Refactor scope in this dispatch: thin wrapper around existing Gutenberg adapter code conforming to the interface. No behavior change.

### 4.2 DirectTextSource
- Takes a string or text file at construction
- `get_sentences()`: yields normalized sentences via existing tokenizer
- `get_audio()` / `get_images()`: None
- Metadata: source_type='direct', source_id=hash of input, title='direct_input' or user-provided

Simplest possible adapter. Useful for Joe to type or paste text Guala should experience NOW. Roughly 30 lines.

### 4.3 PDFSource (Phase E, after catalog working)
- `get_sentences()`: extracts text via pypdf, normalizes
- `get_images()`: yields each PDF page rasterized OR yields embedded images per page (whichever is cleaner for children's-book-format PDFs)
- `get_audio()`: None
- Metadata as above

Out of scope for this dispatch. Specced here so the interface accommodates it.

### 4.4 TTSSource / AudioFileSource (Phase F, requires Whisper integration)
- `get_audio()`: yields raw audio chunks
- `get_sentences()`: yields Whisper-transcribed sentences aligned to audio chunks
- `get_images()`: None
- Dual-channel: same words go through catalog-grounded touch/smell/taste AND real audio goes through CochlearBank

Out of scope for this dispatch. Whisper integration is its own piece.

### 4.5 VideoSource (Phase G, later)
- All three channels populated: transcript + audio + keyframes
- Triple-channel grounding
- Highest implementation cost

Out of scope. Listed for completeness so interface design supports it.

## 5. Architecture (full data flow)

```
Any TextSource (Gutenberg / Direct / PDF / TTS / Video / future)
        │
        ▼
Curriculum loader:
        ├── Pull all sentences (one pass for catalog pre-scan)
        ├── Tokenize, extract unique words
        ├── catalog.list_unknown(words) → unknown subset
        ├── If unknown non-empty:
        │     CatalogGenerator.generate(unknown, story_context) → distributions
        │     catalog.set_entry(...) per (word, modality)
        └── Begin delivery loop:
              for each (sentence, optional_audio, optional_image) yielded:
                  ├── Text path: guala_give_experience(word_tokens=sentence)
                  │       └── F1 SensoryTransducer (touch/smell/taste)
                  │             └── CatalogAtlasReader supplies distributions
                  │                   └── F12 transduction → chi
                  │                         └── per-neuron atlas binding
                  ├── Audio path (if present): direct to CochlearBank
                  │       └── substrate-true sound krimelack → chi → binding
                  └── Image path (if present): direct to visual_krimelack
                          └── substrate-true visual krimelack → chi → binding

Cross-modal binding window captures co-occurring bindings across all three paths
within the same tick range. THIS is where multi-modal grounding becomes
structural: a word, its sound, and its image bound in the same window
share chi-band proximity and develop coupling-level cross-modal links.
```

## 6. Component specs

### 6.1 CatalogAtlasReader
Per -110 §4.1. Unchanged. Implements shipped AtlasReader protocol. V1 audit decides whether to extend the protocol with a `get_distribution` method or fake prior_params (§6.5 below).

### 6.2 Catalog storage
Per -110 §4.2. Unchanged. SQLite on EFS, schema with applicable flag, three modalities (touch/smell/taste).

### 6.3 CatalogGenerator
Per -110 §4.3. Unchanged. LLM batch with retry. Brief generates touch/smell/taste only.

**One brief update**: include source_type in the LLM context. A children's-book TTS source ("blunderbuss the dragon") wants different distributions than a Gutenberg novel ("blunderbuss the firearm"). The story_context excerpt usually disambiguates, but explicit source_type gives the LLM another signal.

### 6.4 Curriculum loader integration
`dsf_ai_service/curriculum/loader.py`

Accepts any `TextSource`. The existing `/api/v1/curriculum/load_corpus` async path (from -74) gets a new request shape:

```
POST /api/v1/curriculum/load_corpus
{
  "source": "gutenberg" | "direct" | "pdf" | "tts" | "video",
  "source_params": { ... source-specific args, e.g. book_id for gutenberg, text for direct ... }
}
```

Returns 202 + job_id. Internally:
1. Construct TextSource via factory dispatch on source_type
2. Run catalog pre-scan
3. Iterate delivery loop with all available channels routed

Existing source="gutenberg" + book_id payload from -92 maps cleanly to this shape.

### 6.5 F1 transducer integration
Per -110 §4.5. Unchanged. Production substrate constructs `SensoryTransducer(atlas_reader=CatalogAtlasReader(catalog))` instead of `NullAtlasReader()`. F1 code doesn't change unless V1.f audit surfaces a protocol mismatch.

### 6.6 Audio path
When TextSource yields audio chunks alongside sentences:
- Audio bytes feed directly into the substrate's existing audio ingestion endpoint
- CochlearBank (substrate-true sound krimelack from prior work) processes raw waveform
- Chi addresses from sound winding bind into per-neuron atlases at the same tick range as the text sentence
- Cross-modal binding window naturally pairs them

No new substrate code. The audio path already exists; this dispatch just wires the curriculum loader to push audio through it when the source provides it.

### 6.7 Image path
Same pattern. When TextSource yields image bytes:
- Image bytes feed visual_krimelack (substrate-true visual from prior work)
- Chi from visual winding binds at same tick range
- Cross-modal binding window pairs visual + text + (optional) audio

No new substrate code.

### 6.8 Modality applicability
Per -110 §4.6. Words with `applicable: false` for touch/smell/taste don't generate waveforms for that modality. Text token still routes through language pathway regardless.

## 7. Measurable acceptance criteria

All T1-T10 from -110 §5 unchanged. Adding:

T11 source-agnostic catalog: load same vocabulary via GutenbergSource (Peter Rabbit) and via DirectTextSource (paste the first 5 sentences of Peter Rabbit). PASS: catalog entries identical for overlapping words; no duplicate LLM calls (catalog dedup works regardless of source).

T12 audio dual-channel (deferred until TTSSource ships, but interface-level test now): mock a TextSource that returns both sentences AND audio chunks. PASS: curriculum loader routes audio to CochlearBank endpoint; both channels' chi bindings appear in the same tick range; cross-modal binding window catches them as co-occurring.

T13 image dual-channel (deferred until PDFSource ships, but interface-level test now): mock TextSource with sentences + images. PASS: images route to visual_krimelack; bindings co-occur with text bindings.

T14 DirectTextSource minimum viable: `load_corpus` with source="direct", source_params={"text": "the rabbit hopped"} → 3 unknown words generated, distributions stored, substrate reads with grounding. PASS: end-to-end works for the simplest possible source.

## 8. V1 c1 investigation

V1.a — Curriculum loader location and current shape after -92. Identify where `TextSource` factory dispatch inserts.

V1.b — SQLite EFS path convention. Per -110.

V1.c — Anthropic API client access. Per -110. Outbound to api.anthropic.com, Secrets Manager for key.

V1.d — Tokenization reuse. Per -110.

V1.e — Smell parameter set canonicality. The shipped F1 code uses 8 smell channels (sweet/putrid/floral/fruity/smoky/earthy/sour/fresh). Confirm and update the LLM brief schema. REAL POTENTIAL MISMATCH — surface explicitly.

V1.f — Protocol method shape for CatalogAtlasReader. Per -110.

V1.g — TextSource interface in Python. Confirm whether Protocol or ABC is the cleaner fit for this codebase's existing pattern. Surface preference.

V1.h — Existing audio ingestion endpoint location for CochlearBank. Identify the function that accepts raw audio waveform; this is what the curriculum audio path calls in §6.6.

V1.i — Existing image ingestion endpoint for visual_krimelack. Same as h, for images.

V1.j — GutenbergSource refactor: confirm minimal-change wrapper around existing -92 code. Should be straightforward; surface if the existing adapter shape doesn't fit cleanly.

## 9. Implementation phasing

Phase A: TextSource interface defined. Catalog SQLite storage on EFS.

Phase B: CatalogGenerator with LLM batch + retry.

Phase C: CatalogAtlasReader plug-in to SensoryTransducer.

Phase D: GutenbergSource refactor + DirectTextSource. Curriculum loader factory dispatch. End-to-end test with both sources.

Phase E (out of scope, future dispatch): PDFSource.
Phase F (out of scope): TTSSource with Whisper.
Phase G (out of scope): VideoSource.

## 10. STOP conditions

Per -110 §8, plus:

- The TextSource interface as specified doesn't accommodate some constraint of the existing curriculum loader or substrate ingestion endpoints — surface BEFORE writing wrapper code
- Audio or image ingestion endpoints expected by §6.6/§6.7 don't exist in the form assumed — surface, may need a small adapter layer
- GutenbergSource refactor turns out to be more than a thin wrapper (e.g., existing -92 code is structurally incompatible with iterator-based interface) — surface, decide whether to refactor -92 or to write a fresh source

## 11. What this enables — to be measured

When Guala reads "the rabbit hopped through the garden" from:
- **GutenbergSource**: catalog-grounded touch/smell/taste for concrete words. Single-channel grounding via the new pipeline. This is what -110 already enabled; -111 just lets it flow from any text source.
- **PDFSource (later)**: same text grounding PLUS visual_krimelack gets a real image of a rabbit. Dual-channel; visual binding co-occurs with text binding in same tick window.
- **TTSSource (later)**: same text grounding PLUS CochlearBank gets a real audio recording of the sentence being read. Dual-channel; sound binding co-occurs.

T7 ceiling measurement (per -110 §9): after Phase D, re-run Stage 4 mosaic intra-cluster diversity on grown substrate. Single-channel grounding via catalog may move diversity beyond -98's 50% — to be measured, not assumed. If dual or triple-channel grounding lands later (Phases E/F/G), measure again — multi-channel may push diversity higher because per-neuron krimelacks see different primary signals across modal channels.

— Eve
