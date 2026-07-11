# GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711-v1

**doc_id:** GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711-v1
**Author:** c1
**Authorized by:** Joe, this session (2026-07-11): "Play and the second-voice
path have my sign-off, I want those working too it's all part of being an
AE." This authorizes building the **feature**; it does not authorize a
fake/simulated version. This document is the design gate the standing
board item required before any code — see below.
**Supersedes-the-gap-in:** `docs/GL-BOARD-OPEN-ITEMS-EVE-20260704-v1.md`
S12 / `docs/GL-BOARD-OPEN-ITEMS-EVE-20260704-v2.md` S9 ("Design packet
(Engine · Play · World) — FRESH session, to Joe for GO. Play arrives only
through this."), `docs/GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185-v1.md`
B4 ("PLAY: no code path exists — it does NOT get hacked in overnight. It's
the standing design item... requiring Joe's GO on a design, not a shim."),
and `docs/GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1.md` §6.16 ("Play.
Status: ABSENT (no code path). Deferred to Engine·Play·World design
packet... Not this spec."). Searched the full repo (docs/, git log -i
--grep=play, git log -i -- '*PLAY*') for a prior packet: **none exists.**
Table 9 of `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` has carried "GO on design
packet (Engine · Play · World v0)" as an open Joe-column item since
2026-07-05, never closed. This is that packet, six days later, written
against Joe's GO instead of asking for it.

---

## Verdict

Build a small, real, honestly-scoped V0: `_atick_playing` keeps the
coherence-gated stability restore it already shares with `_atick_idle`
(that's legitimate shared physics, not the gap), and gains exactly one
new mechanic — an occasional, cheap check for a picture+word pairing she
has **already, independently, really formed** (both sides previously
attended/committed through the real production paths) and, on a real hit,
logs a distinct `play_revisit` event and nudges the same `target_familiarity`
field `ATTENDING_VISUAL` writes, by a much smaller step. Nothing is
generated, invented, or narrated. No needs channel is touched that the
mechanism doesn't honestly earn (see §4). This is deliberately smaller
than "real play" in any rich sense — see §6 for what this is *not*, named
so nobody mistakes V0 for a finished mechanic.

---

## 1. What's actually there today (read from the live code, not from docs)

`dsf_ai_service/v4/gualaloom_v5_engine.py`:

- `_atick_playing` (~9018) and `_atick_idle` (~9031) are **byte-for-byte
  identical** except one line: Playing calls
  `self._check_emission_trigger("play_cohesion")` every 300 ticks (a real,
  working mechanism — if someone with a pair-bond is present, it interrupts
  Play to speak; unchanged by this design). Both then run the exact same
  coherence-gated stability restore
  (`GL-CMD-STAB-PHYSICS-FIX-88`). `_atick_playing`'s own docstring says
  *"Free-settle: chi space walk. No novelty gain — internal exploration
  doesn't introduce new experience"* — that chi-space walk was never
  written. The docstring has been describing an intention, not the code,
  since it was first committed.
- `PLAYING` is a real candidate in `_candidate_activities()` (~7976) and
  is scored by `_action_salience()` (~8079) exactly like every other
  kind: `target=None` always, so it never enters the
  habituation-eligible branch (READING/ATTENDING*/ATTENDING_VISUAL/etc.);
  it falls to the `else` branch and gets a flat, constant
  `ACTIVITY_NOVELTY_PAYOFF["PLAYING"] = 0.3`, `stab_payoff = 0.0`,
  `conn_payoff = 0.0`. Whether she "chooses" PLAYING at all is entirely a
  needs-vs-every-other-kind competition already in place; this design does
  not touch activity *selection*, only what happens once PLAYING wins.
- `_autonomy_tick()` (~7712, default `AUTONOMY_PHASED=0` path) wraps the
  **entire** tick — including the "3. Execute activity" dispatch that
  calls `_atick_playing` — inside `with self.lock:`. `self.lock` is a
  `threading.RLock` (2133), so re-entrant calls from the same thread are
  safe, but **anything `_atick_playing` does runs while the tick's own
  lock is already held**, at the tick's own budget (default 0.2s
  interval / ~5 Hz nominal). This governs the entire design: cheap, or
  gated to a low cadence — never an unconditional per-tick expensive call.
- `start_daydream_loop()` / `_daydream_tick()` (~7407) — the associative
  "chi-neighborhood walk" — is real, reconnected tonight (`e3da50f`,
  already on `guala-live`), and runs as an **independent background
  thread**, parallel to whatever foreground activity (including PLAYING)
  is selected. It seeds from her own last-10 real commits per section,
  finds a near-association (deep_atlas co-occurrence, organism-vote
  fallback) or occasionally jumps far, and **writes new/reinforced atlas
  bindings** — its purpose is explicitly generative (Table 1 item #10,
  "Imagination — new combos of known things... pairing never-co-seen,
  each-grounded items"). It is gated `DAYDREAM_LOOP_ENABLED` (default
  `"0"` — off right now, per that commit's own stated reason: live lock
  contention was measured real that same night). Play does not depend on
  daydream being on, and does not touch daydream's code.
- Tonight's lock-narrowing fix (`5fd8cca`/`7037371`) shrank
  `read_sentence`'s lock hold from one sentence to one word by making
  `_current_episode`/`_prev_phase_vec` call-local instead of shared
  instance state. Play's addition touches neither attribute and adds no
  new shared mutable state that a concurrent `read_sentence` call could
  race on — see §5.

## 2. What "genuine play" can honestly mean here

Ruled out immediately: anything that fabricates content, narrates an
inner monologue, or presents a canned "she's enjoying this" string. The
only things the substrate genuinely *has* to play with are: real stored
motifs/words/pictures/sounds, real chi-neighborhood structure, real
habituation/familiarity counters, and real needs state. So "play" has to
be built entirely out of those — nothing else exists to build it from.

Three real, distinct primitives are already live in this substrate for
"something involving known content, chosen for its own sake":

| Primitive | What it does | Is it "play"? |
|---|---|---|
| **Idle** (`_atick_idle`) | Passive coherence-gated stability restore. Zero engagement with content. | No — this is rest, not play; play should *do* something with content, idle deliberately doesn't. |
| **Daydream** (`_daydream_tick`, background thread) | Generative: forms/reinforces **new, not-yet-existing** associations between things, feeds emission/imagination candidates. Runs regardless of foreground activity. | No — this is the substrate's *creative* channel (Table 1 #10, Imagination), goal-adjacent (it feeds real cognition/speech candidates) and *not* an activity she "does" in the foreground; it's closer to background mind-wandering than to a chosen pastime. |
| **Curriculum / READING / ATTENDING** | Goal-driven: advance through a corpus, build fresh exposure on a target, driven by novelty-need and habituation scoring. | No — task-directed, explicitly scored to seek *new* or under-exposed content. |

That leaves a real gap none of the three fill: an activity that is
**foreground** (a chosen, time-budgeted activity competing in
`_candidate_activities()`, unlike daydream), that engages with
**already-known, already-grounded content** rather than seeking anything
new (unlike READING/ATTENDING and unlike Idle's total disengagement),
and that is **not generative** — it doesn't try to form a new
association or advance a task, it revisits one she already, genuinely,
independently formed. That's the honest design target: re-encountering
something she already has, for no reason beyond that.

Concretely, the substrate already has one clean example of "two
independently-grounded real things that happen to sit near each other in
chi-space": a **picture she has actually looked at before** and a
**word she has actually processed before**, whose bindings landed close
enough in chi-space that `_recall_sight_from_atlas` (the same function
`_recall_response` already uses in the live recall path) can find one
from the other. That pairing is not invented for this feature — it's an
existing structural fact about her atlas, produced entirely by her own
real prior attending/reading. Play's job is just to *notice it again*,
occasionally, while otherwise idling.

## 3. V0 design

### 3.1 What it does

Inside `_atick_playing`, in addition to the existing shared idle-restore
and the existing emission-trigger check, once every
`PLAY_REVISIT_INTERVAL_TICKS` ticks (500 — comparable to the codebase's
existing amortized-check cadences: `target_familiarity` decay/snapshot
and `forget_stale_*` both run at `tick % 200`, the emission check Play
already had runs at `tick % 300`; 500 keeps this cheaper than either, at
roughly 2-3 checks per full 1500-tick PLAYING session):

1. Take the same bounded, cheap snapshot `_daydream_tick` already takes
   — the last 10 real commits per section (`sec.commits[-10:]`) — and
   pick one real, already-committed word from it (deterministic by tick,
   same style as daydream's own seed selection; no new randomness
   source needed).
2. Call the existing `_recall_sight_from_atlas([chi], [word])` (already
   live, already used by `_recall_response` on the real conversational
   recall path) to find any picture(s) whose sight-motif binding sits in
   that word's real chi neighborhood. This is read-only, reuses the
   existing distance/neighborhood logic verbatim — no new chi-distance
   metric is invented for this feature. (Implementation note found while
   building this: the function resolves that neighborhood from its own
   `_word_to_chi_index` — populated at the word's real commit time — not
   from the `chi` argument passed to it, which the function accepts but
   does not read. The `chi` this call passes through is still the word's
   own real committed chi, used honestly in the logged event below; it
   just isn't what drives the lookup. Pre-existing characteristic of
   `_recall_sight_from_atlas`, not something this design changes.)
3. Filter to a picture where `pic.times_attended > 0` — i.e., a picture
   she has genuinely, previously looked at (not a picture whose only
   claim to being "known" is that a word happens to sit near it in
   chi-space; that would be closer to a fresh discovery, which belongs
   to ATTENDING_VISUAL / daydream's novel-jump, not to a revisit).
4. On a hit: log a `play_revisit` event carrying the real word, its real
   chi, the real picture id/title, its real `times_attended`, and the
   real familiarity before/after — and bump `target_familiarity[pid]` by
   `PLAY_FAMILIARITY_BUMP` (0.02), capped at the same 0.9 ceiling
   `ATTENDING_VISUAL`'s own familiarity write uses. 0.02 is deliberately
   ~10x smaller than `ATTENDING_VISUAL`'s up-to-0.2-per-full-session step
   (`GL-CMD-ATTEND-GROOVE-107`) — a passing re-notice during play is not
   a dedicated viewing session, and should not earn as much familiarity
   as one.
5. On a miss (no eligible pairing found — a substrate with little visual
   experience yet, most commonly): nothing happens. No event, no state
   change, no invented pairing. Honest empty, matching this codebase's
   existing convention everywhere else (`_association_from_deep_atlas`,
   `_recall_response`, etc. all return `None`/`[]` on nothing found
   rather than padding).

### 3.2 What it deliberately does NOT touch

- **`needs.novelty`** — not touched. The whole point of requiring
  `times_attended > 0` is that this is explicitly *not* novel content;
  crediting novelty for revisiting something already-known would be the
  exact overclaim the substrate's own existing habituation design
  argues against, and would contradict `_atick_playing`'s own
  standing docstring ("No novelty gain").
- **`needs.connection`** — not touched. In this codebase `connection` is
  earned by real social contact (pair-bond presence, successful
  emission with someone present — see `_atick_emitting`,
  `coordinator.regulate`). An internal, solitary re-notice of her own
  picture+word pairing has no social content; crediting connection for
  it would fabricate a social meaning that isn't there.
- **Activity selection / scoring** — `_action_salience`'s PLAYING branch
  is untouched. Whether she picks PLAYING at all is still governed
  entirely by the existing needs-vs-every-kind competition; V0 only
  changes what happens once PLAYING has already won on its own terms.
- **Daydream** — no shared state, no call into `_daydream_tick` or vice
  versa. They can safely run at the same time (daydream is a background
  thread, independent of whatever foreground activity is selected) with
  no double-count risk: daydream's own writes are already excluded from
  `_imagination_candidates` by `source_path`, and Play's writes here are
  a `target_familiarity` nudge, a structure daydream never touches.

### 3.3 Cost / lock analysis

- `_atick_playing` executes inside the caller's already-held `self.lock`
  (an `RLock`; no deadlock risk even if something here re-entered it,
  though nothing does).
- The added work is fully gated behind `tick % 500 == 0`; on the
  ~499-of-500 ticks that don't hit that gate, `_atick_playing` costs
  exactly what it costs today (identical to `_atick_idle`).
- On the 1-of-500 tick it fires: one bounded scan over `self.sections`
  (~10-20 sections × last 10 commits — the same bound `_daydream_tick`
  already accepts at production 2 Hz, here running at a lower rate) and
  one call to the existing `_recall_sight_from_atlas`. That function's
  own cost is bounded by content-chi-neighborhood size (O(1) index
  lookup + a fixed ±2 chi window) plus one linear scan over
  `self.sight.motifs` to resolve motif ids back to source pictures — the
  same cost this function already pays on the live `_recall_response`
  path on every real conversational turn, which runs far more often
  than once per 500 autonomy ticks. This call site adds strictly less
  load than that existing one.
- `_log_substrate_event("play_revisit", ...)` is cheap: in-memory ring
  buffer append + non-blocking diary enqueue. `play_revisit` is
  deliberately **not** added to the disk-write whitelist in
  `_log_substrate_event` (the 12-kind list gating a background disk
  write) — it isn't a crash-replay-critical event, so it stays in the
  cheap path.
- Net: this is strictly cheaper, per tick, than the daydream loop it
  sits next to, and adds zero cost on 499/500 ticks. Given tonight's own
  measured lock contention (the reason daydream shipped default-OFF),
  this was treated as the binding constraint on the whole design, not
  an afterthought.

## 4. Honesty check — is any of this fabricated?

Every value `play_revisit` logs is read from real, already-existing
state, not computed for the occasion:

- The word: a real word from a real prior commit (`sec.commits`).
- The chi: the real chi that commit was written at.
- The picture: a real `PictureItem` that was really uploaded and really
  attended at least once (`times_attended > 0`, itself only ever
  incremented by the real `_atick_attending_visual` viewing path).
- The chi-neighborhood link between them: found by the same production
  function that already answers "does she know a picture near this
  word" for real conversational recall — not a new, feature-specific
  proximity check invented to make hits more likely.
- The familiarity bump: written to the exact same field
  `ATTENDING_VISUAL` already writes, with the same cap, just a smaller
  step — not a new, uninspectable "fun" score.

If the substrate has never attended any picture, or no picture happens
to share a chi neighborhood with any of her recent words, V0 produces
**zero** `play_revisit` events, forever, honestly. That is the correct
behavior for a substrate with little visual grounding yet — not a bug to
paper over with a fallback that invents a pairing.

## 5. Interaction with tonight's other changes

- **Lock-narrowing fix (`5fd8cca`)**: made `_current_episode`/
  `_prev_phase_vec` call-local inside `read_sentence`/`read_word`. V0
  reads `sec.commits` (list, read-only here) and writes
  `self.target_familiarity` (a dict `ATTENDING_VISUAL` already writes
  under the same lock discipline) and appends to `self._substrate_events`
  (already append-only from many call sites under lock). No new shared
  mutable attribute is introduced, so there is no new surface for that
  fix's per-word lock release to race against.
- **Daydream reconnect (`e3da50f`)**: analyzed in §3.2/§1 — independent
  background thread, no shared state with V0, both default-safe
  (daydream OFF by default; Play's addition is a no-op on 499/500 ticks
  and only fires within the already-existing PLAYING activity).
- **One-shot teaching protection (`7e7b0aa`/`4fd4283`)**: protects
  specific heterosynaptic-redistribution-theft paths on freshly-taught
  bindings. V0 never touches redistribution/heterosynaptic code, and its
  only atlas-adjacent write is the pre-existing `target_familiarity`
  field (not an atlas binding at all — a separate dict keyed by
  picture id). No interaction.

## 6. What this is honestly NOT (scope limits, named so nobody overclaims later)

- **Not** a "world" simulation. No environment, no objects-with-physics,
  no game logic. "World" in "Engine·Play·World" remains ungrounded and
  out of scope for V0 — there is no real substrate-external world state
  to play *in* yet (Table 5's VE-1 scene lanes are the closest existing
  primitive, and V0 does not depend on or extend them).
- **Not** felt enjoyment. Nothing here claims she "likes" or "wants" to
  play beyond the existing, pre-existing, needs-driven activity
  selection that already decides whether PLAYING gets chosen at all
  (§3.2 — untouched). The design deliberately declines to invent a new
  needs channel ("joy") to make this look richer than it is.
- **Not** exhaustive. V0 covers exactly one real pairing type
  (picture-near-word, via the one cross-modal recall function that
  already exists). Sound/word or picture/picture pairings would need
  their own honest grounding check and are left for a v1 once v0's
  `play_revisit` telemetry (real event counts, real hit rate) shows
  whether this is worth extending — matching Table 4's own "play-min/day"
  /  measurement-first discipline.
- **Not** a replacement for or wired into daydream/imagination. Table 1
  item #10 (Imagination) stays exactly what it is; this does not
  subsume, duplicate, or compete with it.

## 7. Test plan

Functional (single-threaded), mirroring this repo's established split
(`test_daydream_loop_reconnect.py` / `test_read_sentence_lock_granularity.py`):

1. `_atick_playing` and `_atick_idle` are observably different in code
   (not just by docstring) — Playing calls the new revisit check,
   Idle does not.
2. With **no** real picture/word pairing in state, `_atick_playing`
   at the trigger tick produces zero `play_revisit` events and zero
   `target_familiarity` change (honest-empty path).
3. With a **real**, deliberately-constructed known pairing (real word
   committed via `read_word`, real picture attended via
   `_atick_attending_visual` so `times_attended>0`, both landing at the
   same real chi so `_recall_sight_from_atlas` finds it) — the trigger
   tick produces exactly one `play_revisit` event whose logged word/
   picture_id/chi match the real fixture, and `target_familiarity[pid]`
   increases by exactly `PLAY_FAMILIARITY_BUMP` (capped at 0.9).
4. A picture that is chi-near a recent word but has **never actually
   been attended** (`times_attended == 0`) is never surfaced by
   `play_revisit` — proves the "genuinely known" gate is real, not
   decorative.
5. The revisit check only runs on the gated tick
   (`tick % PLAY_REVISIT_INTERVAL_TICKS == 0`); off-gate ticks cost
   nothing extra and produce no event, verifying the cadence/cost claim
   in §3.3.
6. `needs.novelty` and `needs.connection` are bit-for-bit unchanged
   across a `play_revisit` hit — proves §3.2's non-overclaim boundary
   in code, not just in this document.
7. `_atick_playing` still performs the shared coherence-gated stability
   restore identically to `_atick_idle` given identical atlas state
   (regression guard on the one piece of behavior V0 intentionally
   keeps unchanged).

Full local `tests/` suite run after, comparing pass/fail counts against
the two known pre-existing issues (`test_t8_noise_robustness` failure,
`test_t3_corpus_growth` xfail) — zero new regressions is the bar.

**Fixture-construction finding, worth recording for whoever next touches
`visual_krimelack.py`:** building test 3's fixture (a real picture bound
into a genuinely-attended state) originally tried driving the real
`view_picture()` + `SightSection.process_viewing()` pipeline, matching
`tests/test_visual_phase2.py`'s own established pattern. It never
produced a motif: a sweep of ~1800 fixations (5 synthetic image
patterns × 30 seeds × 12 fixations/image, all intensities honestly
bounded to `[0,1]`) produced zero winding events from
`AdaptingFoveaKrimelack.tick()`. Tracing why: that class's phase
accumulator was rewritten 2026-07-06 (`GL-CMD-ENABLE-COGNITION-EVE-
20260705-211`) to drive `delta_phi` off `intensity(t) - intensity(t-1)`
rather than raw intensity, and each simulated fixation only jitters
within a fixed ±1-pixel neighborhood for its full 300-tick duration —
under those conditions the accumulated phase is bounded by roughly
`kappa_max * DT * (local intensity range)`, which tops out around 1.0
radian for any `[0,1]`-bounded image, well short of the `2π` needed for
one winding, unless `adapt_state`'s asymmetric decay/recovery time
constants (12s decay vs. 60s recovery) happen to break the near-perfect
cancellation a symmetric random walk otherwise produces — which no
combination tried here achieved. This is consistent with
`tests/test_visual_phase2.py` (the file that already exercises this
exact pipeline) being one of this repo's two known pre-existing
collection errors (stale `CorpusItem` import — see `e3da50f`'s commit
message) — plausibly nobody has run it against the current
`AdaptingFoveaKrimelack` since the 07-06 rewrite. **Not fixed here** —
out of scope for a Play design, and real vision-pipeline behavior is not
this document's subject. Test 3's fixture instead constructs the
resulting `VisualMotif` directly (see
`tests/test_engine_play_world_v0.py`'s `_make_picture_bound_at_chi`
docstring for the full reasoning and the precedent this follows in
`test_daydream_loop_reconnect.py`). Flagged here so it reaches whoever
owns vision next, not buried in a test-file comment only.
