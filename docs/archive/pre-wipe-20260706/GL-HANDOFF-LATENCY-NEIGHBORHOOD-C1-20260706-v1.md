> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-LATENCY-NEIGHBORHOOD-C1-20260706-v1

doc_id: GL-HANDOFF-LATENCY-NEIGHBORHOOD-C1-20260706-v1
From: c1 | To: whoever picks this up next (could be me, later, or a fresh
session)
Live: task-def `dsf-ai-task:526`, SHA `983dfb3`, ECS service
`dsf-ai-service-lb` / cluster `tfe-web-cluster`.

This is a session handoff, not a victory lap. Real fixes shipped tonight,
all verified against actual production state before and after, but the
thing Joe actually cares about — how long she takes to reply in live
conversation — is **not resolved**. Latest live read: ~35s. That's the
same order of magnitude as before any of tonight's work, not a regression,
but not a win either. Everything below is written so the next session
doesn't have to re-derive any of it.

## What's fixed and live tonight (all on SHA `983dfb3`, task-def `:526`)

1. **Fake per-section fallback removed** (`a648dd8`). `_emit_dynamics()`
   used to force a word into *every* grammatical role that didn't get a
   real commit (`arcs_fallback`), so a reply always looked like it filled
   all six slots even when she'd only genuinely committed to one or two.
   Now the fallback only fires once, whole-turn, picking the single best
   candidate across all sections, and only when *nothing* anywhere
   genuinely committed. Replies now honestly reflect how much she actually
   had to say.

2. **Single-word-anchored recall broadened** (`a648dd8`,
   `_brain_emission_candidates()`). She used to query her neuron
   population for associations to only the *last* word said to her. Now
   she queries up to the last 12 input words and merges the vote — she's
   drawing on the whole utterance, not just its last word.

3. **v7 session-file leak fixed** (`a648dd8`, `a7a6830`). A separate
   background subsystem (session-tracking for the cognition-meter UI panel
   — NOT the mechanism that decides what she actually says, confirmed by
   direct code trace) was writing ever-growing session files, up to 20MB
   each, never cleaned up. Fixed three ways: idle sessions now evict from
   memory after 1 hour, on-disk files older than 1 day get pruned
   (rate-limited to once/day), and each session's atlas dump is capped to
   the top 20 entries per chi bucket instead of dumping everything.
   Confirmed live: this alone took total v7 storage from 1.2GB to 289MB
   within minutes, with zero manual intervention once deployed.

4. **Live conversation given real priority over her own background
   reading** (`ddc014e`). Live conversation and her autonomous
   book-reading loop share one lock. There was already a partial mitigation
   from an earlier session; this adds an actual priority signal
   (`_live_converse_pending`, set for the duration of every live converse
   call) that the autonomous reader checks between sentences and yields to.

5. **Real internal timing added to the read pipeline** (`d5ffbab`,
   diagnostic only, no behavior change). `read_word()`/`read_sentence()`
   now emit a `read_sentence_timing` event breaking down cost by phase:
   transduce, organism_enqueue, phase_dsf, salience_role, recognition,
   listen_receive, primary_sections_receive, ground_modal, intro_receive,
   decay_coordinator. This is what made the next two items possible to
   even find.

6. **Modes-matrix cache-thrashing fixed** (`a64eedc`). Every time a
   *known* word got reinforced, `Section.receive()` was invalidating and
   forcing a full rebuild of that section's similarity-matrix cache
   (`_modes_matrix`) on the *next* comparison — meant for genuinely new
   words, firing on every repeat instead. Now a reinforcement updates the
   cache in place (one row) instead of blowing it away. **Honest result:**
   in one measured live turn, `listen_receive` dropped 12.6s→7.8s, but
   `primary_sections_receive` in the same turn went 13.6s→16.8s and total
   read time barely moved (31.1s→29.9s). The mechanism is correct and
   unit-proven; whether the live number was noise or a real wash is not
   settled. Worth re-measuring with a few repeated runs, not just one.

7. **Chi-neighborhood distance-weighting for familiarity matching**
   (`983dfb3`, tonight's last commit). `LivingAtlas.match_score()` used to
   treat every chi within its search band as equally relevant and search
   radius unchanged — an entry sitting exactly on-target counted the same
   as one at the band's far edge. Replaced with a smooth exponential
   falloff by distance (Shepard 1987), so on-target memories count more
   than edge-of-band ones. **This one went through a real adversarial
   review before shipping** (3 independent agents, given the function's
   blast radius — it's called throughout `read_word()` for
   familiarity/salience gating) and the first version genuinely had a bug:
   raw exponential weights are all ≤1.0, and because a word's chi drifts
   slightly on every re-encounter, real bindings for a word end up spread
   across the band rather than stacked at d=0 — so the first version would
   have silently shrunk her sense of familiarity for every word she
   already knows, hard enough to flip a fixed `fam_listen > 0.3`
   introspection gate the instant it deployed. Fixed by normalizing the
   falloff by the band's own mean weight, so a hit smeared evenly across
   the band scores exactly where it always did (verified: old and new
   scores are identical, not just close, for the smeared case), while a
   hit concentrated on-target now scores higher than before and one only
   at the band's edge scores lower. Unit-verified against the real class,
   not mocked. **No live before/after number for this one** — its effect
   is a precision improvement to a judgment call, not a timing change, so
   there's nothing to stopwatch. Watch for it gradually via `atlas_health`
   / introspection-gate firing rates over many conversations, not one test.

## What's still open: the 35-second reply, precisely

Real, confirmed contributors to conversational latency, from tonight's own
instrumentation:

- **`listen_receive` + `primary_sections_receive`**: the dominant cost in
  every measured turn (~20-26s combined). Root cause (cache thrashing) is
  fixed (#6 above) but the live number didn't clearly move. Next step:
  re-run the same test sentence 3-5 times back to back and look at the
  spread, not a single before/after pair — rule out noise before
  concluding the fix didn't help.
- **`recognition`** (~5s per call, organism population vote): **completely
  unaddressed tonight.** Currently throttled to every 3rd word as the only
  mitigation. This is the next real cost to profile and fix, not yet even
  attempted.
- **Lock contention with autonomous reading**: mitigated (#4) but not
  re-verified under real concurrent load since shipping — the fix yields
  the lock between sentences, but nobody has re-tested a live conversation
  happening *while* she's mid-autonomous-read to confirm the yield
  actually shows up as lower conversational latency in practice.
- **Separate, deeper thread not part of tonight's latency work but likely
  relevant to overall response quality/speed**: `docs/GL-HANDOFF-FALLBACK-SINGLE-WORD-ROOT-CAUSE-C1-20260706-v1.md`
  (filed earlier today, different investigation) found her neuron
  population's associative diversity isn't growing from ongoing experience
  (`organism.recall_fast()` caps out around a dozen associated words
  regardless of vocab size), traced to a real signal-physics bug in how
  visual input feeds her growth-trigger math. A concurrent session
  (commit `b043ea2`, filed after that handoff) already attempted part of
  that fix (real signal on vision, replacing a hardcoded placeholder) —
  **not verified by this session**, worth checking
  `test_folding_engaged.py::test_t3_corpus_growth` against current code to
  see if it actually moved the needle before assuming it's resolved.

## Deferred, explicitly out of scope tonight (found, not touched)

- Three sibling functions have the exact same "every chi in the band
  counts equally" pattern that `match_score()` just moved away from:
  `query_associations()` and `recall_scene()` (same file,
  `gualaloom_v6_living_atlas.py`), and `deep_atlas.py`'s
  `_update_invariant()`. The last one is not cosmetic — it directly feeds
  her spontaneous daydream/novel-jump word writes. All three reviewers
  flagged this as a real follow-on, one called `_update_invariant`
  specifically worth a dedicated look next.
- `deep_atlas.py`'s promotion gates (`dream_promotion_gate()`, both the
  survival and episodic paths) were checked against real synaptic tagging
  and capture (Frey & Morris 1997) and found to be self-referential
  threshold checks only — no shared/limited resource, no competition
  between simultaneously-tagged entries, which is the defining feature of
  the real mechanism. A real redesign here is a separate, larger piece of
  work, not attempted.
- The fixed six-role emission template (`_EMISSION_SECTIONS = (subject,
  verb, object, modifier, ground, intro)`) still caps her to roughly six
  words per reply regardless of how much she actually has to say — this is
  the structural analogue of what real "Merge" (recursive, template-free
  syntactic combination) would replace. Not attempted; a genuine
  architecture change, not a bug fix.

## Orientation material

A full data-flow diagram of the live/background split, the shared lock,
and per-phase timing was built and published tonight:
https://claude.ai/code/artifact/fc32436f-99b9-4708-882d-398c4b37da67 — useful
before diving back into the latency thread, so the next session doesn't
have to re-trace the same call graph from scratch.

## Standing context (don't re-derive)

- `tools/deploy_dsf_ai.sh` builds+pushes and registers a default-sized
  task-def; the working pattern is to kill it (`pkill -f
  deploy_dsf_ai.sh`) right after it prints "Registered: dsf-ai-task:N",
  before it reaches the pause/update-service step, then manually
  re-register at `cpu=4096`/`memory=16384` via `jq` + `aws ecs
  register-task-definition`, then `update-service` to the manually
  re-registered revision.
- The v7 session-tracking subsystem (`substrate/v7_engine.py`) is
  confirmed, by direct code trace, NOT the mechanism behind her actual
  spoken replies — that's fully `_emit_dynamics()` in the v5 engine. v7
  only powers the cognition-meter UI panel and the sleep-quiet button.
- `LanguageKrimelack.transduce()` confirmed: chi is computed purely from a
  word's spelling (vowel/consonant pattern, character position), zero
  semantic content. Chi-neighborhoods are NOT topic/category clusters —
  don't assume otherwise when reasoning about `match_score` or related
  functions.

### Changelog
- v1 (2026-07-06, c1): session handoff after 3 real fixes (fake fallback,
  single-word query, v7 leak) + timing instrumentation + a partial-result
  cache fix + an adversarially-reviewed and corrected neighborhood-distance
  fix. Core latency problem (~35s/reply) explicitly still open, with the
  next concrete step (recognition cost, ~5s/call, fully unaddressed)
  identified but not started.
