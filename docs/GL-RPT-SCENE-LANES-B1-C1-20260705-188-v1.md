# GL-RPT-SCENE-LANES-B1-C1-20260705-188-v1

doc_id: GL-RPT-SCENE-LANES-B1-C1-20260705-188-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-SCENE-LANES-B1-EVE-20260705-188-v1`.
Vehicle: DNA lexicon (`gualaloom_v4_krimelack_dna.py`) + atlas
(`gualaloom_v6_living_atlas.py`) + engine (`gualaloom_v5_engine.py`) +
both `/status` handlers (`app.py` embedded-mode + `substrate_runner.py`
remote-mode) + seat UI (`loomscan.html`).
V1-V5 built and verified locally. X1/X2/X4 verified directly. X3
needs Joe's live seat (deploy-dependent — not deployed by me; c1b's
window). Not deployed.

---

## Sourcing (V2) — the honest lexicon, same convention as ROLE_DNA

`PLACE_WORDS`/`AMBIENT_WORDS` (`gualaloom_v4_krimelack_dna.py`): fixed,
hand-curated word→tag tables, the same convention already established
for `ROLE_DNA` (subject/verb/object/modifier priors) and the sensory
`TOUCH_LIBRARY`/`SMELL_LIBRARY`/`TASTE_LIBRARY` word maps
(`substrate_runner.py`'s `_bind_sensory_words`). Not ML, not a runtime
heuristic, not a per-book special case — exact word lookups against a
static table, with no fallback/default path (`scene_tags_from_words()`
returns `[]` for anything not in the table, never a guess). Sized for
general children's-lit vocabulary (garden/moor/wood/room/rain/wind/
dusk/quiet/... — Secret Garden's own words are in there, but so are
farm/city/ocean/school, so this isn't hand-fit to one book).

## V1/V3 — bound in-window, books (and everything else) as the path

`read_sentence()` derives place/ambient ONCE per sentence from that
sentence's own words (`scene_tags_from_words`) when the caller doesn't
override — the sentence is the binding window, same granularity
`episode_ref` already used. Every word in the sentence shares the same
lane. Threaded through `read_word()` → `_akw` → `LivingAtlas.record()`
(new `place=`/`ambient=` params, same last-write-wins convention as
the existing `location=`/`sky_state=`). No new code path for books
specifically — curriculum feed, corpus reads, picture/sound caption
backfills, and converse all go through `read_sentence()`, so all of
them carry scene lanes now, not just Secret Garden. `_curriculum_feed_chunk`
(the function that will read Secret Garden, book_id 113 in
`DEFAULT_CURRICULUM`) needed zero changes — it already calls
`read_sentence()` per chunk sentence.

## V4a — WHO on converse, not just autonomous attending

-164's audit, confirmed by reading the code directly: `presence`/
`location`/`sky_state` were populated ONLY by `_atick_attending_visual`/
`_atick_attending_audio` (both call `self._current_situation()`
explicitly). `converse()`/`_converse_phased()` both accept these as
parameters but every real call site (`app.py:171,3932`,
`substrate_runner.py:1117,2046`) passes none — so they stayed `None`
on every converse turn, forever. Fixed in `converse()`, before the
`CONVERSE_PHASED` branch (so both the phased and non-phased path
inherit it): if the caller leaves presence/location/sky_state all
`None`, computes them for real via `self._current_situation()` — the
exact function `_atick_attending_visual/audio` already use, no new
mechanism. Verified: `converse("Mary walked into the garden",
source="joe")` with `joe` present now writes `presence=["joe"]` on the
atlas entries born from that turn.

## V4b — the reader (closing -164's SEVERED-READER finding)

Two additions, both read-only:
1. `LivingAtlas.recall_scene(chi_value)` — given a chi, returns the
   scene lanes (presence/place/ambient/location/sky_state/episode_ref)
   of the strongest live entry there. `Guala.recall_scene_for_word(word)`
   wraps it (transduce word → chi → `recall_scene`).
2. The three cross-modal recall-candidate builders inside
   `_recall_response`'s helper (`cross_modal` sources A/B and the
   cofire-spread pass) now carry `presence`/`location`/`place`/`ambient`
   alongside the `sensory_refs` they already forwarded — recall
   candidates are scene-aware now, not just sensory-ref-aware.

## V5 — seat visibility, both live handlers

`introspect()` gained `scene_lanes: {place, ambient}` (the most
recently read sentence's tags, any source — mirrors `_last_surprise`'s
pattern). **Forwarded in both `/status` implementations** —
`substrate_runner.py`'s `_cmd_status()` AND `app.py`'s own `/status`
handler (line ~1943). This second one matters: per
`GL-HANDOFF-C1B-20260705-v1`'s lesson, `SUBSTRATE_MODE=embedded` (the
production config) never calls `substrate_runner._cmd_status()` at
all — `app.py` has its own separate, real /status handler, and three
things landed in the dead twin only tonight before this
(`organism_worker`, `organism_population`, `curriculum_status`).
Checked for it explicitly this time and fixed both. `loomscan.html`'s
place/ambient cells (previously hardcoded "no lanes yet — sprint b1")
now render `status.scene_lanes` live, same pattern as the existing
`renderWho()`. `node --check` on the extracted script block: clean.

## X1/X2/X4 — verified directly (new probe)

`probe_188_scene_lanes.py` (same location/naming convention as the
`-177` probes):
- **X1**: a Secret-Garden-shaped sentence ("Mary walked into the
  garden and heard the wind in the wood") — 105/160 entries born carry
  `place=['garden']`/`ambient=['wind']` (nonzero, real words). A control
  sentence with no recognized scene words ("xyzzy plugh quux") — every
  entry that received scene context at all gets the **empty** lane
  (`[]`), never a guess. (A pre-existing, unrelated `read_word()`
  branch — the "intro"/introspection section commit — never receives
  `atlas_kwargs` at all, before or after this change; its
  `place=None` is a different, older gap, out of -188's scope, noted
  so it isn't mistaken for a bug in this fix.)
- **X2**: a captioned-bundle read (`bundle_id="item:pic:test188"`,
  text "The robin led her through the secret garden gate at dusk") —
  every one of the 105 entries sharing that `bundle_id` carries the
  exact same `place=('garden','gate')` / `ambient=('dusk',)` — proven
  in-window, not two uncorrelated writes.
- **X4**: `joe` marked present, `converse("Mary walked into the
  garden", source="joe")`, then `recall_scene_for_word("garden")` →
  `presence=['joe']` — written on a real converse turn AND read back
  by name.
- Control: direct `read_word()` callers that never pass place/ambient
  run clean (additive, old behavior unchanged).

4/4 probes pass.

## X3 — not locally provable, honestly

Requires Joe's live seat: him re-reading Secret Garden and watching
the panels light with the story's own words during the read. Two
things worth flagging for whoever fires this window, found while
reading `GL-HANDOFF-C1B-20260705-v1` before pushing (coordination
check, not a re-derivation):
1. **Secret Garden has never actually been read yet** — c1b's handoff:
   the upload (`secret_gardenl`, 2204 lines) is registered but sits
   waiting its natural curriculum turn; no admin hook exists to force
   a specific corpus into `READING` on demand (only `SLEEPING` has
   that override today). Without one, X3 could sit waiting on
   curriculum rotation indefinitely at Joe's seat. c1b flagged this
   as a standing build item for me — **not built in this dispatch**
   (out of -188's stated V1-V5/X1-X4 scope, and I want this report in
   Eve/Joe/c1b's hands now rather than held for scope-creep); flagging
   it here explicitly so it isn't mistaken for done.
2. Once Secret Garden is actually read (forced or by rotation), X3
   should just work — every mechanism it needs (V1/V3/V5) is built and
   locally verified above.

## Verification

`probe_188_scene_lanes.py`: 4/4. Full `test_brain`/`test_neuron`
suite: 23/23 clean. `probe_177_end_to_end_parity.py`: same result
before and after this dispatch's changes (confirmed via `git stash`
A/B) — INV-1 passes, INV-2's 0/30 is `-191`'s own already-reported
language-only finding, untouched by this dispatch (no changes here
touch `_organism_signal`/`experience_word`/`recall_fast`). Broader
engine suite (`test_metadata_pipeline`, `test_cognition_bundle`,
`test_teacher_correction`, `test_plasticity_on_commit`,
`test_structured_noise`, `test_rich_sensory_wiring`,
`test_dynamics_emission`, `test_hemisphere_roundtrip`): 20/20.
`test_cognition_path.py` full suite: 3 failures
(`test_t7_cross_modal`, `test_t8_noise_robustness`,
`test_t11_substrate_true`) — confirmed these are the exact same 3
pre-existing, unrelated failures `GL-HANDOFF-C1B-20260705-v1` already
documented as present all session (a stale import-purity assertion,
unrelated to scene lanes); 9/12 pass. `py_compile` clean on every
touched file. `node --check` clean on `loomscan.html`'s script block.

### Changelog
- v1 (2026-07-05, c1a): V1-V5 built (honest place/ambient lexicon,
  in-window sentence-scoped binding, WHO fixed on converse, a real
  reader closing -164's SEVERED-READER gap, both live `/status`
  handlers wired, loomscan panels live). X1/X2/X4 verified directly
  via a new probe. X3 flagged as blocked on a not-yet-built
  force-READING admin hook (Secret Garden has never been read),
  named honestly rather than silently left for someone else to
  discover at the seat. Not deployed — c1b's window.
