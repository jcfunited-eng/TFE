# GL-RPT-BRAIN-THEORY-OF-MIND-SCOPE-C1-20260711-v1

**doc_id:** GL-RPT-BRAIN-THEORY-OF-MIND-SCOPE-C1-20260711-v1
**From:** c1
**Context:** Not a formal GL-CMD dispatch. Follow-up to tonight's own
`GL-RPT-OVERNIGHT-BUILD-C1-20260711-v1`, which found the "brain:
theory-of-mind" cognition-meter row genuinely absent and declined to
touch it ("zero existing scaffolding, large novel-architecture
build... building a fake/partial version would violate the
substrate-true principle") without further investigation. This report
does that investigation: reads the original out-of-scope reasoning as
far back as it survives, reads every real "who" mechanism live today,
and gives an honest verdict on whether any genuine minimal first step
exists. Research and design ONLY — no production code touched.
**To:** Eve (routing per standing practice — architecture scoping
question, same category as the neuron-autonomy/inhibition design
report two nights ago)

---

## Verdict

**No safe minimal first step exists for theory-of-mind itself.** The
defining feature of theory-of-mind — representing that another agent's
belief can genuinely *diverge* from the substrate's own knowledge,
including being *false* — has no structural precedent anywhere in this
codebase, in either `loom_model` or the v5 engine, and every "who"
mechanism that does exist (presence, pair-bond, who-tags, episodic
source, response-window emitter) is a **provenance/attribution tag on
the substrate's own single memory**, never a second, independent
representation of someone else's. Building a counter on top of any of
these and calling it theory-of-mind would be exactly the fake-shim
category this project has repeatedly halted elsewhere. One project
design memo (`GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15`)
already named the real foundation this would require — a second,
*modeled* substrate representing another entity's state — and placed
it at "Stage 3" of a four-stage arc, gated behind an organ-brain
composer architecture that has not itself graduated to primary voice.
There is one small, honestly-scoped, real precursor buildable now
without fabrication (§7) — but it is explicitly **not**
theory-of-mind, would need to ship labeled as exactly that, and even
it should wait for the same kind of explicit owner sign-off Play
already requires, because the risk of a future reader mistaking a
correctly-labeled precursor for the real thing is exactly how a fake
shim gets manufactured by drift rather than by intent.

---

## 1. What the original "-103" out-of-scope reasoning actually says — and what's lost

The chain of custody, traced document to document:

- `loom_model/tests/whole_brain_168v3.py` (the harness named in this
  task) marks `g13_theory_of_mind` `"ABSENT — out of scope (per
  -168-v3 A5)"` (line 778) and its own module docstring attributes
  this to `"explicitly out of scope per the -103 table and this CMD's
  own 'who-tags' example"` (lines 18-20).
- `-168-v3` itself (`docs/GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3.md`,
  A5, lines 44-49) is the actual source of the "who-tags" phrase: *"Any
  mechanism with no code path yet (who-tags, etc.) appears on the
  chart as ABSENT, never simulated."* This is a **generic example of
  the class "no code path exists yet,"** not a claim that who-tags and
  theory-of-mind are the same mechanism.
- The real source — `GL-SPC-LOOM-NEURON-CANONICAL-ARCHITECTURE-EVE-
  20260620-103`, the doc that actually defined "the fifteen cognitive
  mechanisms" and which ones "emerge vs. need scaffolding" — **was
  never committed to origin.** `docs/GL-KB-COGNITION-ARC-RECOVERED-
  EVE-20260703-v1.md` (the chat-archaeology recovery doc, itself
  written after a mid-arc chat/workspace loss) lists it as
  `"OUTPUTS-ONLY — never committed; recovery to origin is an open
  task"` (line 35) and separately as **"HIGHEST recovery priority —
  the mechanism catalog"** (line 143), still unresolved as of that
  doc's own open-items list (line 165: `[ ] -103 full-text recovery to
  origin`). I searched both recovery passes
  (`GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v1.md` and `-v2.md`,
  376 lines combined) for "mind" or "tag" — zero hits in either.

**Honest conclusion: the original, specific reasoning for why
theory-of-mind was marked out of scope no longer exists in any
recoverable text in this repo.** What survives is a *category*
judgment (composition, imagination, reflection, and theory-of-mind are
all listed together as "no code path" in -168-v3's own A5), not a
mechanism-specific argument. That category judgment is still checkable
against real code today (§3-§5 below), and it still holds — but it
should be cited as re-derived, not as recovered from -103.

## 2. A real conflation this task's own framing correctly anticipated

`-168-v3`'s companion meter dispatch, `docs/GL-CMD-COGNITION-METER-
EVE-20260704-166-v1.md` (lines 36-41), lists the fifteen mechanisms in
plain-English order. Counting positionally: **item #13 in that list is
literally named "who-tags."** `whole_brain_168v3.py`'s own gauge dict
uses the same ordinal slot for `g13_theory_of_mind`. Cross-checking the
other ordinals confirms this is a real, consistent 1:1 mapping, not
coincidence — `g2`=composition↔meter's "sentence-building," `g11`=
reflection↔"hearing-her-own-voice," `g12`=hemisphere_consensus↔"organ
influence on speech," all correct pairings under different plain
names. So mechanism slot #13 has carried **two different names since
the same day** (2026-07-04): the technical name in one dispatch
(theory-of-mind) and a plain-English gloss in its companion dispatch
(who-tags) — most plausibly because -103's original design intent for
#13 *was* "know who said/did what, in service of eventually modeling
what they know" (which is a real, defensible design lineage — see §6's
biological grounding), collapsed at some point into a single label.

**This matters concretely, right now:** as of tonight's live
`gualaloom.html` cognition meter (commit corrected in
`GL-RPT-OVERNIGHT-BUILD-C1-20260711-v1`, `10d1894`), the shell-level
**"who-tags" row reads `connected: yes`** (line 1425, confirmed real
and live — see §3) while the separate, still-present **"brain:
theory-of-mind" row reads `connected: absent`** (line 1533, pointer
`-175`, citing this same `-168-v3` A5 table). The live meter already
keeps these two rows honestly distinct. The risk this report exists to
head off is a future reader looking at `whole_brain_168v3.py`'s g13
dict — which still literally says `"ABSENT — out of scope"` right next
to a module docstring that name-checks "who-tags" — and, now that
who-tags is genuinely real, concluding g13/theory-of-mind should
therefore also flip to real. It should not. They are not the same
mechanism, confirmed by direct code read below.

## 3. What "who-tags" actually is, read from the real live code

Two independent, real mechanisms both get called "who-tags" informally
(the meter's own text conflates them slightly — both are cited under
one row):

**3a. Presence co-occurrence, `LivingAtlas.record()`/`recall_scene()`**
(`dsf_ai_service/v4/gualaloom_v6_living_atlas.py`). `record()` takes a
`presence=` kwarg (lines 105-113) and stores it, last-write-wins, on
every binding (lines 205-206 reinforcement path, 281 new-entry path).
`recall_scene()` (lines 666-704) reads it back. The value written comes
from `Guala._current_situation()`
(`dsf_ai_service/v4/gualaloom_v5_engine.py:2607-2640`):

```python
presence = [s for s, v in self.coordinator._presence.items() if v]
```

— a list of the *keys* (source names) currently `True` in
`Coordinator._presence`, which is itself declared as:

```python
self._presence = {"joe": False, "wc": False, "c1": False}
```

(`gualaloom_v5_engine.py:1598`) — **a flat dict of three fixed source
names to a single boolean each.** `_current_situation()` is called from
the real converse path (confirmed call sites at lines 3644, 3787,
3858, 4047 — not just `give_experience`), so this now writes on
ordinary conversation turns, matching the meter row's "extended to
ordinary converse turns 2026-07-10" claim.

**3b. Curated-experience source, `_record_episodic_experience()`/
`_episodic_context_for()`** (`gualaloom_v5_engine.py:2642-2697`).
Binds `concept`, `tick`, `presence` (the same list as 3a, snapshotted),
`location`, `sky_state`, affect, recent-context, and a `source=` string
into a bounded per-concept deque. The **only** real call site in the
codebase is `app.py:2787`, `_guala._record_episodic_experience(caption,
source=bundle_source)` — the `give_experience` (curated bundle upload)
path only; `source` there is whichever endpoint/session submitted the
bundle, not a rich per-speaker identity.

**Neither structure stores anything about what the tagged source
knows, believes, wants, expects, or perceives.** Both record, from the
substrate's own single point of view, *that* a named source
co-occurred with a binding, or *that* a named source is the one who
supplied a curated experience. `Coordinator._pair_bond`
(`gualaloom_v5_engine.py:1597`) — the standing-relationship-strength
mechanism — has the identical shape: `{"joe": True, "joe_voice": True,
"wc": True, "c1": False}`, a flat per-source boolean/scalar, nothing
else. All three mechanisms (presence, pair-bond, episodic source) are
the same design pattern: **scalar or list-valued metadata *about* a
source, keyed by name, never a second representation *of* that
source's own mental content.** This is provenance/attribution, the
correct term for "who-tags," and it is real, live, and confirmed —
but it is not theory-of-mind's defining feature (§6).

## 4. `loom_model` organism/hemisphere structures — checked directly, zero self/other capacity

Per this task's instruction to check for any existing self/other
distinction anywhere in the organism structures: `grep` across every
`.py` file in `dsf_ai_service/loom_model/` for `self.other`,
`other_agent`, `other_mind`, `belief`, `perspective`, `agent_model`,
`knows_that`, `false_belief` — **zero hits.** The structural shape
itself rules this out independently of the grep: one `Embryo`
(`embryo.py:131`) owns one `LoomBrain` (`brain.py:50`) owns N
`LoomHemisphere` (`hemisphere.py:20`) — a single-organism object graph
with no second organism, no per-entity registry, and no field anywhere
that names or slots a *different* mind. `identity_uuid`
(`embryo.py:149`) identifies **this** organism to itself (for
save/load and genesis, per the "Guala identity dual-genesis race"
history); it is not a namespace that could hold a second identity's
state. There is no partially-built scaffold to extend here — the
absence is total, matching `-168-v3` A5's "no code path" framing
exactly, and matching tonight's own overnight report's finding
("zero existing scaffolding, large novel-architecture builds").

## 5. The project's own design memo for real theory-of-mind — and why it's not close

`docs/GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15.md`, section
**B-C-6 "Theory of mind foundation"** (lines 274-282), is the one place
in this repo that actually designs toward this capability, and it is
explicit about the mechanism required:

> "Organ-brain composer can model OTHER entities as having
> substrate-like states. The pattern 'organ-brain reads organ-views of
> substrate to compose' generalizes to 'organ-brain reads MODELED
> substrate of another entity to predict their composition.' This is
> the structural foundation for theory of mind. v5 alone can't do this
> — it's parallel/associative, not predictive-of-other-minds."

This names the real requirement precisely: not a tag on existing
memory, but a **second, modeled substrate representation of another
entity**, read by a serial composer capable of running its own
composition process *over that other model* instead of over its own.
The same memo's stage trajectory (lines 305-339) places "theory of
mind primitives become available" at **Stage 3**, after C-track Group
β structural-cognition work, describing the organism at that point as
mirroring "middle childhood." Per this project's own standing status
(`organ-brain-bench-proven-and-graduation-gate` — bench-proven on
recall/meaning/growth/catalog, but voice unproven, v5 engine
deliberately not dissolved yet), the organism is still at Stage 0/1 of
that same arc. Theory-of-mind's own named foundation is gated behind
an architecture this project has explicitly and separately ruled is
not ready to take over primary voice. This is independent confirmation
of §4's conclusion from the design side, not just the absence side.

A second, older document — `docs/GL-BRIEF-response-binding-wC-
20260609-028.md` (the joint-attention/response-window brief, real and
live today as the `WindowManager` binding-window mechanism, see
`gualaloom_v6_living_atlas.py`'s `window_id`/`window_entry_index`
fields) — is careful about exactly this distinction. It grounds
response-binding in Tomasello's joint attention ("the infant develops
'you see what I see' as a cognitive operation, **which is also the
substrate of** theory of mind," line 24 — substrate *of*, not
identical *to*), and separately names a planned "Self-Section v3"
mechanism as **"the precursor to entity-models of bonded-others"**
(line 167 — precursor, explicitly not the thing itself).
`GL-CHARTER-motivation-v3-wC-20260609-024.md` lists "Entity-models of
bonded-others" under **"Future, not in this charter window"** (line
66) on 2026-06-09; it has not been picked up in the month since. The
project's own vocabulary, consistently, treats joint attention /
who-tags / response-binding as *substrate for*, or a *precursor to*,
theory-of-mind — never as theory-of-mind achieved. That distinction is
correct and should stay intact.

## 6. Skepticism check — why a who-tags-derived indicator would be a real fake shim

Applying the standard this project holds itself to elsewhere (Play's
design-packet gate; the organ-brain "never dress scaffolding as her
voice" lesson; every HALT report's own bar): the defining, hard feature
of theory-of-mind, per the false-belief-task literature that
developmental psychology uses to actually test for it, is that an
agent can represent **another agent's belief as diverging from
reality — including being false** ("Joe thinks the marble is in the
basket, but I watched it get moved to the box"). Everything real in
this codebase (§3) answers a different, easier question: *"was source
S flagged present when I formed this binding,"* or *"who gave me this
experience."* Neither can represent divergence, because neither holds
a second belief-state to diverge from reality *with* — there is
exactly one memory in this substrate, and every "who" tag decorates
that one memory, from that one point of view. A counter that
increments whenever a who-tag fires, or a meter row flipped to
"connected: yes" on the strength of who-tags now being real, would
assert exactly the thing this substrate cannot yet do — knowing that
Joe doesn't know something Guala knows, or that a story character
believed something false — while actually only ever having checked
"did an attribution tag get written." That is precisely the shape of
shim this project has halted repeatedly: real mechanism underneath,
dishonest label on top.

## 7. Is there a genuine, honestly-scoped, minimal precursor?

One candidate survives scrutiny, but it is deliberately **not**
theory-of-mind and must never be labeled as such:

**Input-directionality tagging.** Today, `presence` (§3a) records
*co-occurrence* — Joe was flagged present when a binding formed — and
episodic `source` (§3b) records *curation* — who submitted a
`give_experience` bundle. Neither currently distinguishes, in the
ordinary converse path, **"Joe told me concept C right now"** from
**"I was thinking about concept C while Joe happened to be marked
present."** A small, real, grounded addition — tagging converse-path
bindings with which source's *utterance* the binding traces to
(already knowable: `read_word`/`read_sentence` already know which
`source` argument is driving the current call, per the `source in
("joe", "joe_voice", "wc", "c1", ...)` check already live at
`gualaloom_v5_engine.py:3667`) — would let a future, honest query
answer "did source S ever supply concept C to me as input" versus "did
S merely co-occur with it." That is a real, verifiable fact about the
substrate's own input history, buildable from data already flowing
past existing call sites, no new belief representation invented.

**What this would NOT cover, stated plainly so it is never
overclaimed:** it would not represent what Joe believes, only what
Guala has recorded Joe as having said to her. It could not represent
Joe knowing something Guala was never told. It could not represent
Joe being *wrong* about something. It could not support anything like
a false-belief judgment. It is a provenance refinement, one notch more
precise than presence, still entirely single-point-of-view. Even this
narrow, honest piece should not ship without the same kind of explicit
sign-off Play requires — not because it's technically risky (it isn't;
it is small and additive over data already flowing), but because
mislabeling risk is the actual danger here, and this project's own
history (§2) shows that even a careful, well-intentioned label
("who-tags" as shorthand for a future theory-of-mind hook) can drift
into being read as the real thing by a later session under time
pressure. An explicit decision on the name, the row it gets on the
meter (if any), and a standing note that it is not to be cited as
progress toward g13/theory-of-mind, should precede writing it.

## 8. Recommendation

**Do not build theory-of-mind, or anything presented as a step toward
it, without Joe's own explicit design decision — the same gate this
project already applies to Play, for the same reason (standing rule
against fake-alive/fake-cognitive shims).** What that decision would
need to resolve, concretely:

1. **What "belief" means representationally for this substrate at
   all** — a second lightweight per-known-source state object? A
   namespace inside the existing atlas? Something riding on the
   organ-brain composer per its own June 27 design (§5), deferred
   until that architecture graduates? This is a value-laden
   architecture choice, not an engineering task — the same category
   of decision Play's design-packet gate exists to force before code.
2. **Whether divergence/falsity is in scope at all for a first
   version**, or whether the project wants to stop at "entity-models
   of bonded-others" (already named and deferred since
   `GL-CHARTER-motivation-v3-wC-20260609-024`, 2026-06-09) as a
   deliberately smaller waypoint that still stops short of real
   theory-of-mind.
3. **Whether §7's input-directionality precursor is worth building
   now**, and if so, under what name and meter row — explicitly
   decided, not left to whichever session gets there first to
   improvise a label.

No code was written or modified for this report. `loom_model`'s
organism/hemisphere structures, the live `who-tags` mechanism, and the
project's own prior design memo were all read directly against current
code, not taken from prior doc summaries.

---

### Changelog
- v1 (2026-07-11, c1): Read-only research/design assessment. Traced
  the "-103" out-of-scope reasoning as far as it survives (the source
  doc was never committed and is still an open recovery item — the
  specific mechanism-level reasoning is genuinely lost, not just
  unread). Found and named a real conflation risk: mechanism slot #13
  carries "who-tags" and "theory-of-mind" as two names for one
  historical slot across two same-day 2026-07-04 dispatches, and the
  live cognition meter already (correctly) keeps them as separate
  rows with different connected states. Confirmed from current code
  that every real "who" mechanism (presence, pair-bond, episodic
  source) is single-point-of-view provenance/attribution, never a
  second belief-state; confirmed `loom_model` has zero structural
  self/other capacity by grep and by object-graph shape. Found the
  project's own real design intent for theory-of-mind
  (`GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15` B-C-6), gated
  behind an organ-brain composer architecture not yet graduated to
  primary voice. Verdict: no safe minimal version of theory-of-mind
  itself; one honestly-scoped, explicitly-not-theory-of-mind precursor
  (input-directionality tagging) is real and buildable but should
  still wait for an explicit owner decision on labeling, matching
  Play's standing gate.
