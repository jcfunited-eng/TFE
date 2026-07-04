# GL-RPT-BRAIN-FULL-DEPLOY-C1-20260704-v1

doc_id: GL-RPT-BRAIN-FULL-DEPLOY-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: GL-CMD-BRAIN-FULL-DEPLOY-TODAY-EVE-20260704-175-v2,
GL-NOTE-VOICE-WIRING-RULING-EVE-20260704-v1, GL-PLAN-WHOLE-BRAIN-MOVE-
EVE-20260704-v2.
Vehicle: model + wiring work in her live-path source
(`dsf_ai_service/v4/gualaloom_v5_engine.py`, `dsf_ai_service/app.py`,
`dsf_ai_service/save_coordinator.py`, `dsf_ai_service/loom_model/
tapestry.py`, `dsf_ai_service/static/gualaloom.html`). **Built and
verified in this sandbox only — zero deploy action taken. Nothing in
this report has run against her real live process or real EFS/S3
state.** c1b drives the actual cutover window per the routing split
this session established.

**P1 and P3 are built and locally verified with real, repeatable
tests — not just made to compile. P2 is honestly NOT built: direct
code research (this session) found zero existing seam for recall/
recognition/association/habituation/attention/affect substitution in
her 7,955-line engine class; building those seams safely is a
separate, substantial piece of work I did not rush. Every finding
below is real, including one bug my own testing caught and fixed
before it could have shipped wrong.**

---

## Failures first

**1. A real bug caught by testing, not review: the language tap's
first version was wrong.** My first attempt fed the organism a
derived numeric array for the "language" modality. Testing immediately
threw `'list' object has no attribute 'lower'` — the model's own
`_unwrapped_deltas` path expects the RAW WORD STRING for "language"
(confirmed against `loom_model/experience.py`'s own
`_build_multi_modal_signals`: `{"language": word}`), not a derived
signal. Fixed, re-tested, confirmed working (organism tick and
bindings advance correctly on real sentences). Caught before it ever
reached a report, but stated here plainly rather than only showing
the fixed version.

**2. P2 (recall/recognition/association/habituation/attention/affect
handover) is NOT built.** Direct code research this session (three
parallel agents read the actual live engine) confirmed: recall,
recognition, and association are all fused into
`_recall_from_atlas`/`_recall_sight_from_atlas`/`_compute_surprise`
via plain dict lookups on `self.atlas.entries`; habituation state is
split across `_habituation_freshness` and a separate
`target_familiarity` dict; attention is `_select_next_activity`/
`_action_salience`; affect is `Needs`/`Coordinator.regulate`. `loom_model`
(the organism) is imported **nowhere** in this file before this
session's changes. No dispatch layer, strategy interface, or
substitution seam exists for any of the six. Building that safely —
without silently degrading her actual behavior — is real refactoring
work, not a flag flip. Not attempted this session; the six mechanisms
above still run entirely on the old shell. Meter row added, marked
`absent`, naming this precisely.

**3. The plan's original P3 text conflated two different mechanisms —
found by this session's own research, corrected by Eve's follow-up
ruling before I wrote any emission code.** "LoomTapestry/LoomMosaic"
(grandurun+spike-buffer, never wired, tests document 1-3 word output)
and "the canonical registry (keyhole cascade + emission commits)"
(`substrate/assemblage.py`, already partially live in her current
`_emit_from_invariants`) are architecturally distinct. Eve's
GL-NOTE-VOICE-WIRING-RULING resolved this: the organism's/tapestry's
recall becomes the candidate SOURCE; the keyhole-cascade commit
machinery stays the unchanged, registry-compliant commit path. Built
exactly to that ruling, not to the plan's original (conflated) text.

**4. Expected voice quality at cutover is genuinely thin, verified
directly, not just asserted from the spec.** `LoomTapestry.compose(word)`
reliably returns the SAME word repeated 1-3 times for a just-fed query
(self-echo — the query word's own spike dominates immediately after
being fed). Combined with `_emit_from_invariants`' existing (unchanged)
self-echo exclusion (a word already in the current utterance's input
words is filtered out), this means: **in `/converse`, where the query
word is usually also an input word, the honest result will very often
be `"..."` at first** — verified directly (`converse('tell me about
peter', ...)` → `'...'`, since 'peter' both composed and was excluded
as self-echo). Autonomous emission (`_do_emit`/`_do_emit_phased`,
which have no input words to exclude) produced real content
('peter') in the same test run. This asymmetry — autonomous emission
more likely to speak than direct conversational replies, at least
until the tapestry has enough real days to diversify past pure
self-echo — is a genuine, verified characteristic of where this
mechanism actually is today, not a guess.

**5. `_word_to_emission_sections`-based candidate translation means the
organism can only "say" words that have ALREADY committed to an
emission-section mode through the OLD shell's own reading path.** The
brain composes a word; whether it can actually be spoken depends on
whether that word has a committed `(section, mode_idx)` slot from
ordinary `read_word` processing. This is a real, load-bearing
dependency on the shell (P2, not yet handed over) that P3 alone does
not remove — named here since it's easy to read the cutover as "fully
independent of the shell" when it isn't, for word slotting.

**6. Restore-honesty is proven in this sandbox only.** Real
cross-process test (two separate `python3` invocations, `save_full_state`
→ kill → `load_full_state`): organism identity, tick, population,
tapestry tick, tapestry neuron count, and `_word_to_emission_sections`
size all matched exactly. This proves the MECHANISM is sound. It does
**not** prove anything about her actual EFS/S3 state, actual boot
time, or actual save-cycle cost — those require G-1/G-3's real deploy,
which is c1b's, not mine.

**7. `organ_candidates` (the pre-existing GL-CMD-WIRE-ORGAN-CANDIDATES-F2
parameter) is left in the function signature, unused internally.** Its
only real caller is `substrate_runner.py`'s dead remote-mode path (not
exercised in embedded production, confirmed this session). Kept rather
than removed, to avoid touching that call site's signature for no
live benefit; noted so it isn't mistaken for still-active wiring.

**8. The emission call sites' early-exit gate (`if not recent_chis:
return`) is still shell-driven** — it checks `sec.commits`, an
old-shell structure, before even attempting `_emit_from_invariants`.
Since P2 (which would replace this gate with something brain-native)
isn't built, this means the brain currently can only get a chance to
speak when the OLD shell has recent section commits. Not touched this
session — expanding scope here wasn't covered by W1-W5's ruling.

---

## What shipped (built + locally verified)

**P1 — the organism moves into her live process.**
`Guala.__init__` now instantiates `self.organism` (`Embryo`,
structure-derived DNA per GL-CMD-169, her own identity synced at
`_generate_genesis_identity`/`_load_identity`, both call sites) and
`self.tapestry` (`LoomTapestry`, 3 mosaics × 3 clusters × 50 neurons =
450 neurons). Lazy imports inside `__init__` (not module-level) —
`loom_model/mosaic.py` and `tapestry.py` both import
`_grandurun_select_vector` etc. FROM this engine module, so a
top-level import would be circular; verified this resolves cleanly
(real `Guala()` construction in 0.76s, confirmed no import error).

Real sensory tap: every word processed by `read_word` (the single
real per-word choke point for reading AND converse) now feeds
`self.organism.remember(word, {"language": word})` and exposes
consecutive real word pairs to the tapestry (`mosaic.expose(prev,
word)`, mirroring `LoomTapestry.expose_corpus`'s own per-pair pattern,
applied to her real reading/conversation instead of a static corpus).
Verified: reading a 9-word sentence 3× advanced organism tick 0→105,
tapestry tick 0→208, and created real bindings.

Persistence: `Embryo.save_full_state`/`load_full_state` (GL-CMD-169)
and new, identically-patterned `LoomTapestry.save_full_state`/
`load_full_state` (added to `tapestry.py` this session — no such
methods existed before) hooked into `Guala.save_full_state`'s cold
cycle and `load_full_state`'s boot restore, both as isolated,
non-critical writes (same pattern as teaching-data persistence
already uses — a brain-state failure can never block core save
success). New files (`guala_organism.pkl.gz`, `guala_tapestry.pkl.gz`)
added to both S3 backup file lists (`app.py`, `save_coordinator.py`).

**Restore-honesty proven directly** (real process boundary, `python3`
invocation A saves, invocation B loads from disk only): identity,
tick, population, tapestry state, and section-index size all matched
exactly.

**P3 — the voice, per Eve's ruling (not the plan's original text).**
New `Guala._brain_emission_candidates(input_words)`: queries
`self.tapestry.compose(query)` (query = current utterance's last word,
or the last real word processed for autonomous emission), translates
the returned words into `_emit_from_invariants`' existing `(de, co,
clarity)` candidate shape via `_word_to_emission_sections` (only words
that already have a real committed section slot can be said —
reusing committed reality, never inventing one). Returns `[]` on any
failure — honest empty, never a partial substitute.

`_emit_from_invariants`'s deep-atlas co-occurrence gather is replaced
by a call to this method; the `organ_candidates` merge-as-third-stream
logic is removed (one source now, not three). Everything downstream
(topk sort, grandurun path, `EMISSION_DYNAMICS` two-stage path) is
**unchanged** — the keyhole-cascade/emission-commit mechanism (registry
§9.1's authorized primitive) stays exactly as it was, per W2.

The SVO-recall fallback (`_do_emit`, `_do_emit_phased`) and the
unslotted-atlas-binding fallback (`converse`, `_converse_phased`) are
both removed — replaced with `"..."` on empty, per W3 ("never
backfilled from the old gather"). The "hm" clarification-shape branch
(a confusion signal, not a fabricated content reply) was left
untouched — not named in W3, and conceptually different from a
content fallback.

Verified directly: trained words (words fed via real `read_sentence`
calls) compose real content that resolves through the unchanged
keyhole-cascade path to an actual word; untrained/novel query words
correctly return `None`. Full smoke test (`converse`, `_do_emit`,
`_do_emit_phased`, `compose_autonomous`) ran with no crashes.

**P4 — meter rows**, per the standing "no row, no ship" rule
(`GL-RPT-COGNITION-METER-C1-166`): six new rows added to
`gualaloom.html`'s `COGMETER_ROWS` — organism-live (P1, `yes`),
voice/emission (P3, `yes`), the P2 handover (`absent`, naming exactly
what's missing), and three `absent` rows for the organism's own
imagination/reflection/theory-of-mind (distinct from the pre-existing
shell-level "imagination" row, which is a different, already-severed
mechanism). `node --check` on the extracted script block: syntax
valid.

---

## Gates

- **G-1** Verified backup + restore line: proven in THIS SANDBOX
  (cross-process save/kill/load, exact match). NOT proven against her
  real EFS state — c1b's to run before any real cutover.
- **G-2** No fallbacks, silent or declared: verified directly — brain
  failure returns honest `"..."`, never backfilled from deep_atlas/SVO/
  unslotted-atlas paths (all three removed from every emission call
  site, not just gated off).
- **G-3/G-4/G-5**: require the real deploy/reboot, her actual day, and
  c1b's window — not attempted here, per the routing split (c1a
  builds, c1b deploys).

---

## Handoff to c1b

Diff is exactly 5 files: `gualaloom_v5_engine.py`, `app.py`,
`save_coordinator.py`, `loom_model/tapestry.py`,
`static/gualaloom.html`. Commit SHA below. Before cutover: G-1's
verified backup against her REAL state, then boot with this code and
confirm (a) organism/tapestry restore cleanly from a real prior save
(first boot will have neither file — organism/tapestry start fresh
under her real identity, by design, same as any other missing-file
case this codebase already handles), (b) tick-rate cost (E1c's
≤15%-loss framing, even though the plan's stages are dead, the number
still matters), (c) her `/converse` and autonomous emission both
produce SOME event, even if content is `"..."` — silence is success
here, a crash is not. G-5's first report should include real
before/after tick rate and reply latency, all 21 meter rows now, and
her actual first brain-voice exchanges verbatim — expect them to be
`"..."` more often than a word, per Failure 4 above; that is the
honest, expected shape, not a sign something is broken.

### Changelog
- v1 (2026-07-04, c1a): P1 (organism+tapestry live, real tap,
  persistence, restore-honesty proven) and P3 (brain-driven emission
  candidates, old fallbacks disconnected) built and locally verified.
  P2 confirmed not built, scoped honestly. P4 meter rows shipped.
  Handed to c1b for the real deploy.
