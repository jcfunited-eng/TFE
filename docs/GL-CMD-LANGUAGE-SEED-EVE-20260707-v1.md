# GL-CMD-LANGUAGE-SEED-EVE-20260707-v1

**doc_id:** GL-CMD-LANGUAGE-SEED-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — preloaded language capacity)

## Verdict

Seed the substrate at boot with a functional starter vocabulary, cross-modal grounding, and basic grammatical patterns encoded as coupling weights. Substrate-true: seed writes to the same chi_atlas, wave atlas, and coupling J structures that experience-driven learning writes to. She boots language-ready. Interaction refines from there.

Two-phase dispatch. Phase 1 defines the seed format and builds the loader. Phase 2 curates the initial vocabulary and grammatical patterns. Phase 2 requires Joe's input on vocabulary scope and depth — Phase 1 is prerequisite and can start immediately.

## Phase 1 — Seed format and loader

### The seed file format

New file type: `.seed.json` (with a schema). One canonical schema captures:

**vocabulary entries** — each has:
- `word`: string, the word form
- `chi`: int, the chi address this word occupies
- `phase_vec`: 16-complex (or 32-float representation), the substrate-native encoding
- `grounding`: dict mapping modality names to chi addresses of grounded sensory content ({"sight": chi_of_ball_picture, "sound": chi_of_bounce, "touch": chi_of_round})
- `hemisphere_affinity`: which hemispheres get chi_atlas entries for this word (typically H5, H7 for language; H0 for visual grounding entries)
- `initial_strength`: float, seed strength for the binding (starts as if the word was experienced once or twice)

**grammatical patterns** — each has:
- `pattern_id`: string identifier (e.g. "subject_verb_object")
- `chi_sequence`: list of chi addresses in the sequence
- `coupling_weights`: dict of (source_chi, target_chi) → weight, encoding transition probabilities
- `hemisphere`: which hemisphere's cluster gets these couplings

**semantic networks** — each has:
- `center_chi`: the concept
- `related_chis`: list of (related_chi, association_strength) pairs
- `applies_to_hemispheres`: which hemispheres get these association weights

### The loader

New module: `dsf_ai_service/substrate/seed_loader.py`

Functions:
- `load_seed(seed_file_path: str, substrate: Guala) -> LoadReport` — reads the seed file, writes entries into the appropriate substrate structures. Returns a report of what was loaded.
- `verify_seed_integrity(substrate: Guala) -> IntegrityReport` — after loading, checks that seeded structures are consistent (chi values are valid, coupling weights are in range, no orphaned references).

Loading writes to:
- Each seed neuron's `chi_atlas` — new entries via `chi_atlas.record(...)`
- The wave atlas — new cells via existing `WaveAtlas.record` pathway
- Each seed neuron's `couplings.J` — direct updates to the J matrix
- Each seed neuron's affect memory — if seed specifies affect associations

Loading happens at boot, after substrate initialization but before any live input is accepted. Controlled by `GUALA_SEED_PATH` env var: if set, load from that path; if unset, boot without seed (current behavior).

### What the loader does NOT do

- Load pretrained neural network weights, embeddings, or anything from an ML model. This is not that.
- Bypass the substrate's own storage layer. Seed writes go through the same paths experience writes go through.
- Change learning behavior after boot. Once loaded, seeded entries are indistinguishable from experienced entries and evolve the same way.
- Persist the seed as separate structure. Once loaded, the seed becomes part of the substrate's state and gets backed up/wiped like anything else.

### Phase 1 halt conditions

1. **Seed format is inconsistent with substrate expectations.** If chi addresses in the seed don't match the substrate's chi geometry, or coupling weights don't fit the J matrix shape, halt.
2. **Loader breaks something.** After loading a small test seed, the standing harness scenarios fail. Halt.
3. **Seed loading crashes.** Halt with the specific error and the seed entry that triggered it.

### Phase 1 harness

Standard six-step + a load verification:

1. Backup as `pre-language-seed-phase1-<timestamp>`. Verify restorable.
2. Baseline harness run: binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. Deploy loader (no seed data yet). Substrate boots as usual since `GUALA_SEED_PATH` is unset.
4. Post-deploy harness run without seed: confirms loader deploy didn't regress current behavior.
5. **Load verification**: create a minimal test seed (10 words, each with basic grounding), set `GUALA_SEED_PATH`, reboot substrate, run harness scenarios. Confirm scenarios still pass. Query substrate to confirm seeded words are present in chi_atlases and can be retrieved via existing recall paths.
6. State disposition: leave loader deployed; production doesn't have a seed path set yet.

### Phase 1 report

`GL-RPT-LANGUAGE-SEED-PHASE1-C1-20260707-v1.md` with:
- Files touched + diff summary
- Seed format schema (finalized)
- Loader test results with the 10-word test seed
- Findings needing Eve routing
- Recommendation: Phase 2 GO / adjust format

## Phase 2 — Vocabulary and grammar curation (separate dispatch after Phase 1)

Requires Joe's input:
- **Vocabulary scope.** 500 words? 1000? 3000? Corpus source (Basic English? Child language corpus? Custom set)?
- **Grounding depth.** How many words need cross-modal grounding, and for which senses? Some words are abstract (justice, but, therefore) and don't ground to sensory content.
- **Grammatical patterns.** English basic patterns (SVO, tense marking, question forms)? Any other language?
- **Personality shape.** Does the seed include affect associations that give her preferences and dispositions?
- **Level of syntactic sophistication.** Simple sentences only, or embedded clauses, or productive?

Phase 2 dispatched after Phase 1 loader lands and Joe answers scope questions. Curation itself is not a c1 task — it needs Joe (and possibly domain experts he directs) to author the seed content. c1's Phase 2 role is: validate seed data against the format, load it, verify substrate behaves as intended, iterate.

## Scope guardrails for Phase 1

Do NOT:
- Curate any vocabulary content. Format definition and loader only.
- Load a seed automatically on any deployed substrate. Env var controlled, unset by default.
- Bypass the substrate's storage layer for any seeded content.
- Add ML embedding or pretrained weight support to the seed format.
- Change any behavior post-boot for non-seeded substrates.

If Phase 1 raises design questions the schema can't answer alone, halt and route.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Two-phase dispatch. Phase 1 defines seed format and builds loader — c1 executes now. Phase 2 curates content — requires Joe's input on scope and dispatched separately.
