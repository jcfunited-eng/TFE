# GL-RPT-LANGUAGE-SEED-PHASE2-GENERATOR-C1-20260707-v1

**doc_id:** GL-RPT-LANGUAGE-SEED-PHASE2-GENERATOR-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction -- no questions to Joe in this doc)

**Full protocol completed, no halt condition fired. Generation only -- nothing
deployed to production.** Built the 7-module generator at
`generator/language_seed/`, integrated 9 free/open data sources (Oxford API
omitted, no licensing), generated a real 50,000-word rich layer and a real
150,000-word programmatic layer (200,000 words total, one shared chi address
space), validated both against every integrity rule the dispatch names, and
load-tested both -- individually and combined -- against a real isolated
local substrate (`Embryo(brain_seed=42)` + real `WaveAtlas()`), the same
pattern Phase 1's own local test used. Zero integrity errors, zero load
errors, zero missing-on-verify across all 200,000 words. Six findings routed
to Eve below -- none are blockers, all are scope/design decisions the
dispatch didn't fully specify.

---

## Sources integrated + licensing

| Source | What it provides | License | Real count loaded |
|---|---|---|---|
| WordNet 3.1 (via nltk) | primary vocabulary, synsets, hypernym/hyponym/synonym graph, lexicographer-file clustering | WordNet license (permissive, free) | 146,189 unique lemma word-forms across 117,659 synsets |
| SCOWL 2020.12.07 (official release, `final/` pre-built lists, tiers <=70) | word-list coverage supplement -- the same corpus Linux distro dictionaries (`wamerican` etc.) are built from | SCOWL license (free, open) | 142,628 words |
| CMU Pronouncing Dictionary (via nltk `cmudict`) | phonetic representations -- auditory grounding | Free/BSD-style | 123,455 words |
| NRC Emotion Lexicon (word-level v0.92) | 8 discrete emotions + pos/neg polarity | Free for research use | 14,154 words |
| NRC VAD Lexicon | valence/arousal/dominance, direct continuous ratings | Free for research use | 19,971 words |
| Warriner/Kuperman/Brysbaert (2013) | valence/arousal/dominance (1-9 SAM scale), fallback when NRC-VAD lacks a word | Open research data | 13,905 words |
| Universal Dependencies English EWT treebank | POS transition frequencies, per-word UPOS tag | CC-BY-SA 4.0 | 16,622 sentences |
| ConceptNet 5.7.0 (full assertions dump, not the API) | common-sense associations (IsA, PartOf, UsedFor, HasProperty, SimilarTo, etc.) | CC-BY-SA 4.0 + component licenses | 34M edges scanned, filtered to en-en edges touching the 200,000-word vocabulary |
| ImageNet (ILSVRC-1000 canonical synset list) | visual grounding via WordNet synset alignment | Free (the 1000-class reference list, not the image corpus) | 1,000 anchor synsets -> 5,509 grounded lemma words via WordNet hypernym/hyponym closure |
| **Oxford API** | definitions, archaic/technical extension | **NOT integrated -- no licensing arranged** | 0 |

**Oxford API**: per the Phase 1 dispatch's own framing ("Paid sources...
otherwise WordNet + supplements cover most needs") and this dispatch's "else
halt" clause, no Oxford content appears anywhere in the seed. This did not
trigger a full-generator halt -- everything else builds and validates cleanly
without it. Two places the dispatch named Oxford as an input needed a
substitute (both flagged in Findings below): the "COCA + Oxford top-50k"
frequency source for rich-layer tiering, and Oxford's contribution to overall
programmatic-layer vocabulary size.

**ConceptNet**: `api.conceptnet.io` returned HTTP 502 on every attempt during
this build (not a one-off -- checked repeatedly across the session). Used the
official S3-hosted ConceptNet 5.7.0 assertions dump directly instead (the
actual primary data, arguably more authoritative than the API layer over it).

## Generator architecture + files

New directory `generator/language_seed/` (repo-relative paths below), 7
modules per the dispatch's own architecture list, plus `config.py` (shared
constants -- N_CELLS, organ-tag mapping, J-matrix range) and `tests/` (32
unit tests, all passing):

```
generator/language_seed/
  config.py          -- N_CELLS/organ-tag/J-range constants, cache+output paths
  sources.py          -- one class per data source, unified .lookup(word) API
  chi_addresser.py     -- deterministic, semantically-clustered chi assignment
  grounding.py          -- cross-modal grounding (visual/auditory/tactile/olfactory/gustatory)
  semantic_net.py        -- WordNet+ConceptNet association neighborhoods
  affect.py                -- VAD from lexicons + neighbor-inheritance fallback
  grammar.py                 -- POS-class coupling patterns from real UD-frequency words
  emit.py                     -- seed assembly + full integrity validation + JSON write
  generate.py                   -- top-level orchestrator (CLI: --limit, --rich-only, --tag)
  tests/                          -- 6 test files, 32 tests, all passing (see below)
  .cache/  (gitignored)               -- raw downloaded corpora, ~509MB, re-fetchable
  output/  (gitignored)                -- generated .seed.json files, not committed (see below)
```

`dsf_ai_service/substrate/seed_loader.py` -- additive loader enhancement
(existing `load_seed()`/`verify_seed_integrity()` UNCHANGED, nothing in
Phase 1's single-file behavior touched):
- `SeedLoadProgress` dataclass -- health-endpoint-facing progress state
- `load_seed_layered(rich_path, substrate, programmatic_path=None,
  chunk_size=1000)` -- loads rich blocking (calls the existing `load_seed()`
  verbatim), then if `programmatic_path` given, spawns a daemon thread that
  loads programmatic `vocabulary_entries` in chunks of 1000 with a
  `time.sleep(0)` yield between chunks, then patterns/networks, then marks
  done
- `_load_programmatic_background` -- the chunked worker

`dsf_ai_service/app.py` -- two small changes inside `_gl_init()`:
- `GUALA_SEED_PATH` -> `GUALA_SEED_RICH_PATH` + `GUALA_SEED_PROG_PATH` (both
  optional, both unset in production -- current no-seed boot behavior is
  unchanged)
- boot-time seed load now calls `load_seed_layered()` instead of
  `load_seed()`, stores the returned `SeedLoadProgress` on a new module
  global `_seed_load_progress` (`None` unless a seed load was attempted)
- `/health` now includes a `seed_load` field (rich-complete, programmatic
  percent/loaded/total/complete) when `_seed_load_progress is not None`;
  omitted entirely otherwise -- no change to `/health`'s shape for any
  currently-deployed, non-seeded substrate

`dsf_ai_service/substrate/test_seed_loader.py` -- 3 new tests for the
layered loader (local `Embryo()`+`WaveAtlas()` substrate, no deployed
target), all passing.

## Unit tests (protocol step 1)

32 tests across 7 files, all passing:

| File | Tests | What's covered |
|---|---|---|
| `tests/test_chi_addresser.py` | 5 | hash determinism, band coverage/no-overlap, no-collision assignment, idempotency, overflow-to-global-probe |
| `tests/test_sources.py` | 4 | word normalization, well-formedness filter, ConceptNet URI parsing, relation-weight sanity |
| `tests/test_grounding.py` | 8 | concrete-noun visual+auditory, no-phonetic auditory gate, abstract-word empty grounding, motion-verb visual+tactile, sensory-adjective anchor/WordNet-propagation/ConceptNet-propagation, own-chi grounding construction |
| `tests/test_semantic_net.py` | 6 | seeded-only filtering, ConceptNet+WordNet combination, empty-candidate None, MAX_RELATED cap, minimal-anchor rich-only targeting |
| `tests/test_affect.py` | 6 | NRC-VAD-over-Warriner precedence, Warriner rescale correctness, no-coverage None, programmatic tier never touches direct lexicons, neighbor inheritance, neutral default + counting |
| `tests/test_emit.py` | 9 | clean-seed pass, duplicate-chi/out-of-range/dangling-grounding/dangling-semantic-edge/bad-affect-range/bad-coupling-weight rejection, cross-file `additional_valid_chis` acceptance, `emit()` raises+doesn't-write on failure |
| `dsf_ai_service/substrate/test_seed_loader.py` | 3 | rich-only layered load, rich+programmatic layered load with background completion + integrity verification, `SeedLoadProgress.as_dict()` |

## Generation metrics

**Master vocabulary**: WordNet (146,189) union SCOWL tiers <=70 (142,628),
well-formed (alphabetic + internal hyphen/apostrophe only), capped at
200,000 (config.MAX_TOTAL_VOCAB -- headroom under the 262,144-slot chi
space). Trimmed the most-obscure SCOWL-only tail to fit; **200,000 words
made the cap exactly** -- the untrimmed union is larger than 200,000, so
some genuinely obscure SCOWL-only entries did not make it into either
layer (not a data-loss concern -- WordNet's own ~146k lemmas are all in,
the trimmed set is pure SCOWL long-tail spelling-list coverage).

**Rich layer** (50,000 words, top-ranked by frequency -- see Findings #1
for the ranking-source substitution):
- Real, timed generation run (cold ConceptNet cache -- worst case):
  **182.4s total** (WordNet preload 14.1s, ConceptNet full-dump scan+filter
  155.3s, everything else <5s combined, entry build 1.7s)
- Re-run with warm ConceptNet cache: rich-layer portion of a **32.4s total**
  full run
- Output: `rich.seed.json`, 50,000 vocabulary entries, 12 grammatical
  patterns (6 pattern types x 2 language organs), 47,778 semantic networks
  (95.6% of rich words got at least one association edge)
- 13,141/50,000 (26.3%) got cross-modal grounding (visual/auditory/tactile/
  olfactory/gustatory) -- the rest are correctly abstract/non-motion/
  non-sensory by the dispatch's own modality rules
- Affect: 18,002 direct NRC-VAD, 34 direct Warriner-fallback, remainder
  inherited or defaulted (full breakdown in Findings #7)
- File size: 30MB

**Programmatic layer** (150,000 words, the ranked remainder):
- Generation time: 0.6s (entry build only -- shares the rich run's already-
  loaded sources and already-built ConceptNet index; not independently
  timed as its own cold run since the two layers share one vocabulary
  assembly + chi assignment pass by design, see architecture note below)
- Output: `programmatic.seed.json`, 150,000 vocabulary entries (chi + POS-
  derived cluster + minimal semantic anchor + inherited-only affect --
  **no grounding, no grammatical patterns**, exactly per the dispatch's
  layer-boundary spec), 49,364 semantic networks (32.9% -- see Findings #8)
- File size: 38MB

**Combined total**: 200,000 words, one shared 262,144-slot chi address
space, **zero collisions** (chi assignment used exactly 200,000 of 262,144
slots -- 76.3% occupancy, well within headroom).

**Architecture note on why rich+programmatic run together**: the
programmatic layer's "minimal semantic anchor (just the primary synset
link)" deliberately targets rich-tier words only (guaranteed already loaded
when a background programmatic chunk lands, per the loader's rich-blocking-
first order) -- see `semantic_net.build_minimal_anchor`. That cross-tier
reference means chi assignment has to happen once, across the whole 200,000-
word vocabulary, before either file is built. `generate.py --rich-only`
exists and was used for the isolated rich-layer protocol steps (3-5 below),
but a real from-scratch programmatic run always regenerates rich too
(deterministically identical, ~30s of shared-source overhead, not the full
3-minute cold-ConceptNet cost since the index is cached after the first
build).

## Integrity check results

All checks the dispatch names, run automatically inside `emit.emit()`
before any file is written (`SeedIntegrityError` halts and refuses to write
on any failure -- never fired in this run):

| Check | Rich layer | Programmatic layer |
|---|---|---|
| No duplicate chi addresses | 0 collisions / 50,000 | 0 collisions / 150,000 |
| All chi values in 0-262143 | 50,000/50,000 in range | 150,000/150,000 in range |
| Grounding chi references point to real seeded entries | 13,141/13,141 valid (all self-referencing, see grounding.py design note) | N/A (no grounding in this layer) |
| Semantic net edges point to seeded entries | 47,778/47,778 valid | 49,364/49,364 valid (all reference rich-tier chis, verified via `additional_valid_chis`) |
| Coupling weights within J-matrix range [0, 1.5] | 0 populated (see Findings #5) -- vacuously true | N/A (no patterns in this layer) |
| Affect values within valid ranges | 50,000/50,000 in range | 150,000/150,000 in range |
| Grammatical patterns non-conflicting | 12/12 unique (pattern_id, hemisphere) pairs | N/A |

Independent spot-check (separate from `emit.py`'s own validation, random
sample of 100 rich entries, fixed seed for reproducibility): **0 issues**.

## Sample entries

**10 rich entries** (random sample, `random.seed(12345)`):

```json
{"word": "forsaking", "chi": 106176, "grounding": {}, "affect": {"valence": -0.7638, "arousal": 0.5393, "dominance": 0.2379, "source": "inherited"}}
{"word": "alto's", "chi": 63347, "grounding": {}, "affect": {"valence": 0.0, "arousal": 0.5, "dominance": 0.5, "source": "default"}}
{"word": "wonderful", "chi": 88608, "grounding": {}, "affect": {"valence": 0.942, "arousal": 0.776, "dominance": 0.83, "source": "nrc_vad"}}
{"word": "buzzed", "chi": 34074, "grounding": {}, "affect": {"valence": 0.166, "arousal": 0.549, "dominance": 0.448, "source": "nrc_vad"}}
{"word": "couches", "chi": 65279, "grounding": {}, "affect": {"valence": 0.1941, "arousal": 0.1097, "dominance": 0.2373, "source": "inherited"}}
{"word": "somber", "chi": 85624, "grounding": {}, "affect": {"valence": -0.632, "arousal": 0.5, "dominance": 0.38, "source": "nrc_vad"}}
{"word": "timely", "chi": 87488, "grounding": {}, "affect": {"valence": 0.73, "arousal": 0.387, "dominance": 0.591, "source": "nrc_vad"}}
{"word": "sheet of paper", "chi": 170932, "grounding": {"visual": 170932}, "affect": {"valence": 0.0346, "arousal": 0.2187, "dominance": 0.3351, "source": "inherited"}}
{"word": "pippin", "chi": 174588, "grounding": {"auditory": 174588, "visual": 174588}, "affect": {"valence": 0.5694, "arousal": 0.4586, "dominance": 0.3914, "source": "inherited"}}
{"word": "beforehand", "chi": 78944, "grounding": {}, "affect": {"valence": 0.254, "arousal": 0.4973, "dominance": 0.677, "source": "inherited"}}
```

(all entries also carry `hemisphere_affinity: ["sf", "aff"]`, `phase_vec:
null`, `initial_strength: 1.0` -- omitted above for readability; full
records in the output file)

**10 programmatic entries** (random sample, `random.seed(999)`):

```json
{"word": "cn gas", "chi": 245542, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "x chromosome", "chi": 156995, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "underachieve", "chi": 260995, "affect": {"valence": 0.34, "arousal": 0.548, "dominance": 0.536, "source": "inherited"}, "initial_strength": 0.5}
{"word": "subacid", "chi": 83020, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "static tube", "chi": 145650, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "draughtier", "chi": 20276, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "mitomycin", "chi": 149659, "affect": {"valence": 0.02, "arousal": 0.373, "dominance": 0.658, "source": "inherited"}, "initial_strength": 0.5}
{"word": "counterattacked", "chi": 3927, "affect": {"source": "default"}, "initial_strength": 0.5}
{"word": "gaultheria shallon", "chi": 213444, "affect": {"valence": 0.062, "arousal": 0.34, "dominance": 0.34, "source": "inherited"}, "initial_strength": 0.5}
{"word": "ergotism", "chi": 243720, "affect": {"valence": -0.812, "arousal": 0.837, "dominance": 0.526, "source": "inherited"}, "initial_strength": 0.5}
```

(all programmatic entries carry `grounding: {}`, `phase_vec: null` per the
dispatch's own layer-boundary spec -- no visual grounding in this layer)

**Grammatical patterns** (real UD-frequency-derived representative words,
one set per language organ `sf`/`aff`):

| pattern_id | words |
|---|---|
| subject_verb_target | "i" -> "have" |
| verb_object_target | "have" -> "time" |
| noun_modifier_source | "time" -> "good" |
| question_inversion | "what" -> "is" -> "i" |
| tense_temporal_sequence_past | "was" -> "have" |
| tense_temporal_sequence_future | "will" -> "have" |

## Isolated test substrate load results (protocol steps 2, 5, 8)

Per this dispatch's own "Generation only. No production deployment"
scope, and confirmed via research that the harness's HTTP runner
(`harness/README.md`) has no local/in-process constructor path (see
Findings #6), all test loads below are against a real, isolated, local
`Embryo(brain_seed=42)` + real `WaveAtlas()` object -- the identical
pattern Phase 1's own "Local" test used, not a stub.

**Step 2 -- 100-word smoke test**: generated `rich_smoke.seed.json` (50
words) + `programmatic_smoke.seed.json` (50 words) end to end through the
full pipeline including a real ConceptNet scan. First run surfaced a real
bug (below, fixed before proceeding): `is_concrete` was OR'd across ALL of
a word's WordNet senses, so "have" (whose only noun sense is the rare
"rich_person.n.01" -- "the haves and have-nots") got flagged visually-
groundable off a sense nobody uses. Fixed to key off the primary
(highest-corpus-familiarity) sense only, matching the same fix already
applied to `primary_lexname` selection. Re-ran clean: `have`'s grounding
correctly empty afterward. Loaded both files via `load_seed_layered`:
`rich: ok=True vocab=50 patterns=6 networks=38 errors=0`, `programmatic:
ok=True vocab=50 patterns=0 networks=2 errors=0`, both `verify_seed_
integrity`: `ok=True checked=50 verified=50 missing=0`.

**Step 5 -- rich layer standalone**: `rich.seed.json` (50,000 words) loaded
via `load_seed_layered(rich_path, substrate, programmatic_path=None)`:
`ok=True vocab=50000 patterns=12 networks=47778 errors=0`, load took 3.3s.
`verify_seed_integrity`: `ok=True checked=50000 verified=50000 missing=0`,
1.3s.

**Step 8 -- combined test load**: fresh substrate, `load_seed_layered(rich,
substrate, programmatic_path=programmatic, chunk_size=1000)`. Rich loaded
blocking in 3.3s as before. Confirmed the substrate object stayed fully
accessible (`organism`, `wave_atlas.cells`) *while* the programmatic
background thread was still running -- polled mid-flight and observed
`{'programmatic_loaded': 79000, 'programmatic_percent': 52.7,
'programmatic_complete': False}` with the substrate answering normally.
Background load (150 chunks of 1000) completed in 3.9s:
`programmatic: ok=True vocab=150000 networks=49364 errors=0`.
Post-combined-load `verify_seed_integrity` against BOTH files: rich
`ok=True checked=50000 verified=50000 missing=0` (1.7s), programmatic
`ok=True checked=150000 verified=150000 missing=0` (2.0s). **Background
programmatic loading does not break the substrate** -- confirmed by direct
observation during the load, not inferred after the fact.

## Findings needing Eve routing

None of the following block this dispatch's generation-only deliverable.
All are scope/design decisions the dispatch named but didn't fully specify,
or gaps discovered while building.

1. **Frequency-ranking source substitution.** The dispatch names "COCA +
   Oxford top-50k" for rich-layer tiering; both are paid/gated with no free
   bulk-download path. Substituted HermitDave's `FrequencyWords` en_50k.txt
   (OpenSubtitles-derived, MIT-licensed, the standard free alternative for
   this exact purpose) as the primary ranking key, with WordNet
   corpus-tagged familiarity as the fallback tiebreak for words outside the
   top 50k frequency list. Eve's call whether COCA/Oxford licensing should
   be pursued for a future regeneration, or whether this substitution is
   permanent.
2. **ImageNet scope substitution.** Used the canonical ILSVRC-1000 synset
   class list (the standard reference set used throughout ML tooling), not
   the full ImageNet-21k corpus, which requires a gated image-net.org
   account. WordNet noun-offset alignment (`wn.synset_from_pos_and_offset`)
   confirmed true structural alignment, then broadened via hypernym/
   hyponym closure to 5,509 grounded lemma words. A full-21k pass would
   substantially widen visual-grounding coverage if that access gets
   arranged later.
3. **No "kinesthetic" modality exists in the substrate.** The dispatch's
   own grounding.py description says "motion verbs get visual +
   kinesthetic," but `topology.py`'s `HEMISPHERE_PRIMARY_MODALITY` only
   defines 5 real sensory hemispheres (visual/auditory/tactile/olfactory/
   gustatory) plus language -- no kinesthetic/proprioceptive channel.
   Mapped motion verbs to visual + **tactile** instead (nearest real
   modality family). If a kinesthetic channel is ever added to the
   substrate, motion-verb grounding should be revisited.
4. **Affect has no schema field -- same gap Phase 1's own report already
   flagged** (finding #3 in `GL-RPT-LANGUAGE-SEED-PHASE1-C1-20260707-v1`:
   "affect memory has no schema field to write through... Eve's call
   whether Phase 2 needs one"). This dispatch still requires building
   `affect.py` and validating affect ranges, so real, computed
   valence/arousal/dominance data exists for every word -- I added ONE
   small, additive, non-breaking field to each vocabulary entry:
   `"affect": {"valence", "arousal", "dominance", "source"}`.
   `seed_loader.py`'s `_load_vocabulary_entries` only reads known keys via
   `.get()`, so this is currently **write-inert** -- present in the file,
   written nowhere, until Eve authorizes a loader amendment to consume it
   (e.g. via `Guala.needs.step(...)`, the path Phase 1 identified as
   missing a caller). This is NOT a Phase-1-loader modification -- no
   loader code changed to add it, only the generator's output shape.
5. **`coupling_weights` left empty in every generated grammatical
   pattern.** Populating it needs real `neuron_id` strings from one
   specific running organism's *current* ring topology
   (`CouplingsJij.neighbors`) -- but ids aren't stable across an
   organism's lifetime (population growth/division adds daughter neurons
   with new ids, per `embryo.py`'s own conservation-pool mechanism). A
   generic seed file meant to load into whatever organism state exists at
   load time can't safely hardcode ids that may not exist there.
   `seed_loader.py` already treats an unresolved neighbor id as
   skip-with-warning, not an error or a fabricated relationship -- so an
   empty dict is the honest choice, not a shortcut. `chi_sequence` itself
   (the load-bearing structural-landmark mechanism) is fully populated
   with real, UD-frequency-derived representative words for all 12
   patterns. A real `coupling_weights` population would need to run
   against one specific live organism at load/deploy time -- a natural
   Phase 3 (deployment-time) concern, out of scope for a pure generation
   dispatch.
6. **Harness scenarios substituted with direct local load-verification.**
   `harness/README.md`'s runner (`python -m harness run <scenario> --target
   <url> --auth <token>`) requires an HTTP-reachable deployed substrate --
   no local/in-process constructor path exists, confirmed by reading
   `harness/harness/substrate_client.py`. Combined with this dispatch's own
   "no production deployment" bound, I ran the equivalent direct
   `load_seed_layered`/`verify_seed_integrity` checks against a real local
   substrate instead (Phase 1's own local test used this identical
   pattern). Before this seed ships to production, a follow-up dispatch
   should run the actual `binding_windows_acceptance` /
   `cross_sense_recall_acceptance` scenarios against a real deployed,
   seeded, isolated test substrate the way Phase 1 did (throwaway ECS
   service, no EFS mount, explicit S3-deny IAM role) -- that's a
   deployment action this generation-only dispatch correctly didn't take.

## Additional honesty notes (not findings, real numbers worth having on record)

- **Affect defaulted rate**: 103,823/200,000 words (51.9%) got the neutral
  default `(0.0, 0.5, 0.5)` rather than real lexicon or inherited data --
  almost entirely programmatic-tier words whose primary hypernym either
  doesn't exist or isn't itself a rich-tier word, so they have no
  inheritance path under the "rich-tier-only" cross-reference rule (see
  Generation metrics / architecture note). Rich-tier-only defaulted count:
  3,188/50,000 (6.4%, almost entirely function words -- NRC/Warriner
  correctly exclude pure function words as carrying no inherent affect,
  so this is accurate signal, not a gap).
- **Inflected-form gap**: SCOWL contributes many inflected forms (plurals,
  possessives, verb conjugations -- e.g. "couches", "alto's") that
  WordNet doesn't separately lemma-index, so those miss WordNet-derived
  concreteness/grounding/hypernym signal even when their base form would
  clearly qualify (e.g. "couches" -> empty grounding, though "couch" the
  lemma is concrete). Honest limitation of a WordNet-primary approach
  without a lemmatization-normalization step; not attempted here since
  adding one is a real design decision beyond this dispatch's scope.
- **Hemisphere/organ-tag mapping resolved by reading code, not
  documented anywhere as a single table.** `embryo.py`'s `OPERATIONS`
  list zipped positionally against `self.brain.hemispheres` (confirmed
  H0..H7 index order via `brain.py`'s construction loop) composed with
  `topology.py`'s `HEMISPHERE_PRIMARY_MODALITY` gives: em=H0(visual),
  pr=H1(auditory), ep=H2(tactile), sc=H3(olfactory), gp=H4(gustatory),
  sf=H5(language), sv=H6(auditory-secondary), aff=H7(language). Used
  throughout `config.py`. Worth Eve confirming this is the intended
  mapping, since every grounding/hemisphere_affinity choice in this seed
  depends on it being correct and no single doc states it directly.

## Files touched + diff summary

New (generation-only artifact, not deployed):
- `generator/language_seed/{config,sources,chi_addresser,grounding,
  semantic_net,affect,grammar,emit,generate}.py`
- `generator/language_seed/tests/test_{chi_addresser,sources,grounding,
  semantic_net,affect,emit}.py`
- `generator/language_seed/.gitignore` (excludes `.cache/` and `output/`)
- `dsf_ai_service/substrate/test_seed_loader.py`

Modified (additive only, per scope guardrails -- no existing behavior
changed for the current unset-env-var production state):
- `dsf_ai_service/substrate/seed_loader.py` -- added `SeedLoadProgress`,
  `load_seed_layered()`, `_load_programmatic_background()`. `load_seed()`
  and `verify_seed_integrity()` bodies unchanged.
- `dsf_ai_service/app.py` -- `GUALA_SEED_PATH` -> `GUALA_SEED_RICH_PATH` +
  `GUALA_SEED_PROG_PATH`; boot calls `load_seed_layered` instead of
  `load_seed`; `/health` gains an optional `seed_load` field.

**Not committed** (gitignored, regeneratable): `generator/language_seed/
.cache/` (~509MB raw corpora) and `generator/language_seed/output/`
(`rich.seed.json` 30MB, `programmatic.seed.json` 38MB, plus the two
50-word smoke-test files). The generated seed files themselves are build
artifacts of the committed generator + the committed source URLs, not
hand-authored content -- re-running `python -m generator.language_seed.
generate` reproduces them deterministically (confirmed: chi assignment,
tiering, and ranking all use `hashlib`-based stable hashing, never
Python's salted `hash()`).

## Recommendation

Generator built, unit-tested, and run end to end twice (100-word smoke
test that caught and fixed a real concreteness-detection bug, then the
full 200,000-word two-layer generation). Every integrity check the
dispatch names passes on both layers. Loader enhancement built, unit-
tested, and load-verified locally including the specific "background
loading doesn't break the substrate" check the dispatch's own protocol
step 8 asks for. Six findings above are real design decisions worth Eve's
attention, none are blockers. **Ready for Eve to decide on a follow-up
production-deployment dispatch** (which would need the real deployed-
substrate harness run flagged in Finding #6, plus a decision on Findings
#1-5).

---

### Changelog
- v1 (2026-07-07, c1): Generator built (7 modules + config + 32 passing
  unit tests). 9 sources integrated (Oxford omitted, no licensing).
  200,000-word vocabulary (50k rich + 150k programmatic), one shared chi
  address space, zero collisions. Loader enhanced with rich/programmatic
  split (additive, Phase 1's single-file behavior unchanged). Small-batch
  test caught and fixed a real `is_concrete` sense-selection bug before
  full-scale generation. Full generation + validation + isolated local
  test load (standalone rich, then combined rich+programmatic background)
  all passed clean. Six findings routed to Eve. No production deployment.
