# GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1

**doc_id:** GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Follows:** `GL-CMD-LANGUAGE-SEED-EVE-20260707-v1` (Phase 1 loader deployed and verified)

## Verdict

Build the generator that produces the .seed.json file for Guala's language capacity. Two-layer output: **rich layer** (50,000 words with full grounding, semantic networks, affect associations, grammatical role); **programmatic layer** (remaining Oxford vocabulary with minimal grounding — POS and semantic anchoring only). Substrate boots with the rich layer immediately, background-loads the programmatic layer as capacity grows. Full grammatical patterns encoded as coupling transitions. Affect seeded so she has dispositional shape from tick zero.

Bounded scope: generator design, source integration, output validation. The generated seed file is the artifact that Phase 1's loader consumes.

## What's being built

### Data sources

Free-and-legitimate sources form the backbone. Paid sources (Oxford API) can layer if licensing is arranged; otherwise WordNet + supplements cover most needs.

**Vocabulary:**
- Primary: WordNet 3.1 (~155,000 lemmas across noun, verb, adjective, adverb)
- Supplement: SCOWL word lists for coverage of common words WordNet misses
- Oxford API (if licensed) for definitions and archaic/technical extension

**Semantic relationships:**
- WordNet synsets (synonyms, hypernyms, hyponyms, meronyms)
- ConceptNet 5.7 (common-sense associations, IsA, HasA, PartOf, UsedFor, etc.)

**Grounding data:**
- Visual grounding: ImageNet class hierarchy + WordNet synset alignment (many WordNet synsets map to ImageNet classes)
- Auditory grounding: phonetic representations from CMU Pronouncing Dictionary
- Sensory descriptors (touch, smell, taste, texture): ConceptNet HasProperty edges + curated adjective lists per modality

**Affect:**
- NRC Emotion Lexicon (14,182 words with valence, arousal, and 8 emotion categories)
- NRC VAD (20,007 words with valence-arousal-dominance)
- Extended Warriner et al. (13,915 English words with affect ratings)

**Grammatical patterns:**
- Universal Dependencies English treebank for POS transition frequencies
- POS-specific coupling patterns extracted from CoreNLP-parsed corpora

### Generator architecture

New directory: `generator/language_seed/`

Modules:

**`sources.py`** — data source loaders. One class per source. Handles download, caching (once, locally, so the generator doesn't re-download on every run), and unified access API. All sources expose a common `lookup(word) -> SourceRecord` interface.

**`chi_addresser.py`** — deterministic chi address assignment. Each word gets one chi address in the 0-262143 space (matching wave atlas N_CELLS). Chi address derived from a hash of the word combined with its semantic cluster. Words in the same semantic cluster get chis in nearby address ranges — this creates natural neighborhood structure in the substrate that mirrors semantic proximity.

**`grounding.py`** — cross-modal grounding generation. For each word, determine which modalities can ground it. Concrete nouns get visual + often auditory (via phonetic rep). Motion verbs get visual + kinesthetic. Sensory adjectives get their specific modality (smell, taste, tactile). Abstract words return empty grounding — they'll ground through coupling relationships to concrete anchors, not direct sensory content.

**`semantic_net.py`** — semantic network builder. For each word, generate its associated chi neighborhood from WordNet + ConceptNet edges. Each association has a strength (0.0-1.0) derived from source-database confidence + relationship type weights. Strong associations (IsA, direct synonym) get higher strengths than weak ones (RelatedTo, DerivedFrom).

**`affect.py`** — affect associations. For each word, produce valence (-1 to +1), arousal (0 to 1), and dominance (0 to 1) values from NRC + Warriner. Words not in either lexicon inherit affect from their strongest semantic neighbors (weighted average of top-3 nearest semantic net neighbors' affect). Result: every word has affect, even if seeded through inheritance.

**`grammar.py`** — grammatical pattern encoding. Produce coupling weight patches per POS class. Verbs get subject-target and object-target coupling patterns. Nouns get modifier-source patterns. Question words get inversion couplings. Tense markers get temporal-sequence couplings. Each pattern lives in a specific hemisphere (H5, H7 for language) and translates to J-matrix contributions applied when neurons in those chi ranges commit.

**`emit.py`** — .seed.json emitter. Combines outputs of all above modules into the seed file format Phase 1 defined. Rich entries get all fields populated. Programmatic entries get chi + POS + minimal semantic anchoring only.

**`generate.py`** — top-level orchestrator. Reads a config (which sources, what tier boundaries, output path), runs the pipeline, produces the seed file. Runs to completion in a few hours on a typical dev machine.

### Layer boundaries

**Rich layer — 50,000 words:** most-frequent English by usage frequency (Corpus of Contemporary American English frequency counts + supplement from Oxford top-50k). Full generator pipeline runs for each. Full grounding where applicable. Full semantic net. Full affect. Full grammatical role.

**Programmatic layer — remaining ~100,000 words from WordNet + Oxford:** Chi address assigned, POS tagged, minimal semantic anchor (just the primary synset link), affect via inheritance. No visual grounding. No detailed semantic network. Present in the substrate so she can produce or recognize the word if it comes up, but lightweight.

Generator outputs two seed files: `rich.seed.json` (loaded at boot) and `programmatic.seed.json` (loaded in background chunks after boot). Phase 1's loader gets a small enhancement to handle both paths.

### Output validation

Before emitting: generator runs integrity checks on its own output:
- No duplicate chi addresses (collisions would corrupt the address space)
- All chi values within 0-262143
- All grounding chi references point to real seeded entries or acknowledged unseeded chis
- All semantic net edges point to seeded entries
- All coupling weights within J-matrix valid range
- Affect values within valid ranges
- Grammatical pattern coupling patches don't conflict

If any check fails, generator halts with the specific entry and issue. No corrupt seed ever gets shipped.

### What the generator does NOT do

- Curate content by hand. Everything is automated from source data.
- Load pretrained neural network weights, embeddings, or any ML-derived vectors. This is symbolic/relational data assembly.
- Modify Phase 1's loader beyond adding the rich/programmatic split.
- Ship any specific vocabulary that requires proprietary sources unless licensing is confirmed.

## Loader enhancement for rich/programmatic split

Small addition to Phase 1's loader:

- `load_seed(rich_path, programmatic_path=None)` — loads rich first (blocking), then background-thread loads programmatic in chunks of 1000 entries each with brief yields between chunks
- `GUALA_SEED_PATH` becomes `GUALA_SEED_RICH_PATH` + `GUALA_SEED_PROG_PATH` (both optional)
- Health endpoint reports load progress: rich complete, programmatic X% loaded

## Halt conditions

1. **Source unavailable or licensing issue** — halt with the specific source and issue. Do not proceed with degraded data unilaterally.
2. **Chi address collision detected** — halt. Chi addressing algorithm needs adjustment before proceeding.
3. **Output integrity check fails** — halt. Corrupt seeds ship only over Eve's dead body.
4. **Generator produces empty output for a significant chunk of vocabulary** — could indicate source data misalignment. Halt with the affected word range.
5. **Loader test with generated seed fails Phase 1 verification** — halt.

## Harness protocol

Different from usual because this is generator + one-time data production, not a substrate code change:

1. **Build generator** — modules per architecture above. Run unit tests on each.
2. **Small-batch test** — generate a 100-word test seed. Verify output structure. Load into an isolated test substrate. Confirm Phase 1 verification still passes.
3. **Rich layer generation** — run generator against top 50,000 words. Time it, log progress. Expected: 1-3 hours.
4. **Rich layer validation** — integrity checks, spot-check 100 random entries for correctness.
5. **Rich layer test load** — isolated test substrate, load rich.seed.json, run harness scenarios, confirm substrate operational.
6. **Programmatic layer generation** — remaining vocabulary. Expected: 2-4 hours.
7. **Programmatic layer validation + test load**.
8. **Combined test load** — both layers, verify background loading doesn't break substrate.
9. **Report** with generation metrics, sample entries, harness results.

Production deployment is a separate dispatch after this generation dispatch's report lands.

## Scope guardrails

Do NOT:
- Ship any seed to production in this dispatch. Generation only.
- Bypass source licensing.
- Add ML embedding or neural network weight support.
- Manually author any seed content beyond source-data-driven generation.
- Modify Phase 1's loader beyond the rich/programmatic split.

If any design decision the dispatch doesn't cover surfaces during generator build, halt and route to Eve.

## Report

`GL-RPT-LANGUAGE-SEED-PHASE2-GENERATOR-C1-20260707-v1.md` with:
- Sources integrated + licensing confirmations
- Generator architecture + files
- Rich layer generation metrics (words emitted, time, memory, output size)
- Programmatic layer generation metrics
- Integrity check results
- Sample entries (10 rich, 10 programmatic, showing full structure)
- Isolated test substrate load results
- Harness scenario results with seed loaded
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Generator produces two-layer seed: 50,000-word rich layer with full grounding + semantic network + affect + grammatical role; remaining Oxford/WordNet as programmatic layer with lightweight anchoring. Free sources (WordNet, ConceptNet, NRC lexicons, ImageNet alignment, CMU pronouncing dict) form the backbone. No hand curation. No ML embeddings. Chi addressing deterministic and semantically clustered. Output validated before shipping.
