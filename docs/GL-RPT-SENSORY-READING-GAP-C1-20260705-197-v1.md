# GL-RPT-SENSORY-READING-GAP-C1-20260705-197-v1

doc_id: GL-RPT-SENSORY-READING-GAP-C1-20260705-197-v1
From: c1a | To: Eve, Joe, c1b | Responds to: Joe's direct bug report
("I dont see here multi moduals firing... nouns and verbs... supposed
to have the LLM sense emulator giving sensory experience to her
reading — so it's fucking broke").

## Two distinct findings, not one

**Finding 1 — the actual "LLM sense emulator" (`catalog_builder.py`'s
Claude-based `_llm_params`/`make_resonant`, used by `OrganVoice` in
`organ_brain_service.py`) has never been wired to any reading path,
ever.** It lives in a separate process (port 8090), its senses cache
is filled only via direct `/sight_frame`/`/sound_frame`/`/tablet`
calls, and its own speech output is currently silenced
(`organ_brain_retired`) from an earlier, unrelated ruling. Not broken
tonight — pre-existing, and a bigger architectural question (crosses
into the already-flagged "organ-brain voice unproven" graduation
gate) than this dispatch's scope. Not touched here.

**Finding 2 — the real, live, non-LLM touch/smell/taste word-binder
had a genuine gap that IS in scope, and IS what Joe was actually
seeing.** `substrate_runner._bind_sensory_words()` (fixed-lexicon
physics generator over `TOUCH_LIBRARY`/`SMELL_LIBRARY`/`TASTE_LIBRARY`
— 16/12/8 words, no ML, no LLM, matching the standing "substrate-true"
rule) was wired into the curriculum-feed and bulk-corpus-load paths
but **never into `_atick_reading()`** — the tick-by-tick handler every
corpus READING activity uses, natural rotation or the force_reading
hook built earlier tonight. So her Secret Garden read (via
force_reading) got language + place/ambient/who (`-188`) but zero
touch/smell/taste, because that code path never called the binder at
all. Confirmed via a research agent's direct grep of all 3 call sites
before touching anything — not assumed.

## Fix (Finding 2 only — Finding 1 explicitly not touched)

`Guala._bind_sensory_words()` — the mapping/physics-generation/atlas-
binding logic moved from `substrate_runner.py` onto the engine itself
(`gualaloom_v5_engine.py`), since it only ever needed `self.`
internals (`_atlas_record`, `tick`, `_affect_kwargs`) — no cross-
module dependency required. `substrate_runner._bind_sensory_words()`
is now a 3-line delegator; its 3 existing call sites (curriculum feed,
lookup grounding, bulk corpus load) are unchanged and re-verified
working. `_atick_reading()` now calls `self._bind_sensory_words(line)`
right after `self.read_sentence(line, source="corpus")` — every corpus
READING tick, forced or natural, now binds real touch/smell/taste
words exactly like curriculum reading already did.

Also fixed while in there: `_atlas_record` never logged an event for
this, so even where the binder DID fire (curriculum path), loomscan
showed nothing — added `sensory_words_bound` (modalities, words,
n_bindings). And loomscan's `smell`/`taste` lanes had **zero wiring
anywhere** in the frontend, dead regardless of backend state — fixed
alongside `touch` to light from this new event.

Dead-code cleanup, a direct consequence of this refactor: `_clean_word`/
`_VOWELS`/`_COGNITION_STOP_JUNK`/`import re` in `substrate_runner.py`
had no remaining callers once `_bind_sensory_words` moved — confirmed
via grep (zero hits repo-wide) before removing, not left stale.

## Verified directly

Local: `add_corpus` + force + one `_atick_reading` tick on "the warm
soft blanket smelled sweet and tasted like honey" → `sensory_words_bound`
event fires with `modalities=['taste','touch']`, `words=['warm','soft',
'sweet']`, `n_bindings=7`; real `modal_touch`/`modal_taste` atlas
entries carry `sensory_refs=['touch:warm']` etc. `substrate_runner`'s
delegating `_bind_sensory_words` re-tested directly — still works for
its original 3 call sites. Full `test_brain`/`test_neuron`: 23/23.
`probe_188_scene_lanes.py`: 4/4 (unaffected). Broader engine suite:
20/20. `py_compile` clean, `node --check` clean on loomscan.html.

### Changelog
- v1 (2026-07-05, c1a): Finding 2 fixed and verified (real sensory
  binder now fires on every corpus READING tick, logged, loomscan
  wired). Finding 1 (LLM sense emulator / organ-brain wiring) reported
  honestly as a separate, larger, not-yet-decided question — not
  built, per scope. Deploying alongside.
