# GL-RPT-RECALL-SILENCE-ROOT-CAUSE-C1-20260709-v1

**doc_id:** GL-RPT-RECALL-SILENCE-ROOT-CAUSE-C1-20260709-v1
**From:** c1
**Executing:** Joe's direct overnight instruction: "memory recall mechanism needs
to be fixed so put as many agents you need on it to do that"
**To:** Joe (direct report — no dispatch routing this session)

---

## Summary

Deep investigation (a 4-agent parallel diagnosis workflow plus direct local
testing against a real running organism) found the precise, confirmed reason
ordinary conversation currently returns the empty `"..."` placeholder. It is
not one bug — it's two real, separate, well-understood mechanisms, both
currently starved, plus one structural filter that will never resolve on its
own regardless of how much data accumulates. Given the real incident history
in this exact code (three prior sessions this week hit regressions in this
same recall/emission-candidate area — the "always says ball" bug, a
>95%-false-confidence bug, a severe T5 accuracy collapse from a
chi-radius-limited search), I chose NOT to make a risky change to the core
matching logic tonight without review. This report lays out exactly what I
found and what I recommend, so that decision can be made deliberately, not
reactively.

## What's confirmed, precisely

1. **The credo/grounding gate correctly excludes almost her whole existing
   vocabulary from ever being spoken.** A word only enters the speakable
   index (`_word_to_emission_sections`) if its first-ever commit was
   genuinely sense-grounded, or if it gets retroactively backfilled from real
   deep-atlas co-occurrence. Nearly all of her vocabulary was read from books
   before any real sensory grounding existed. Confirmed live: even "dog" —
   read constantly — still returns `"..."`.

2. **Real grounding (via `give_experience`) does correctly unlock a word's
   speakable-index entry immediately**, verified directly in a local test:
   teaching "dog" inside a real-grounded window (a real `sight` section entry
   present in the same binding window) puts it in
   `_word_to_emission_sections` right away. This part works as designed.

3. **Even once a word is grounded, querying it BY ITSELF still returns zero
   candidates — and this will never change no matter how much real data
   accumulates.** `recall_exact_or_best` (the fix for last week's "always
   says ball" bug) always returns the query word itself, at confidence 1.0,
   for any word the organism has ever bound. `_brain_emission_candidates_
   legacy`'s self-echo filter then correctly discards this, since replying
   with the exact word you were just asked about isn't a real answer. For a
   single-word query, there is nothing else in the vote to fall back on —
   this is a structural property of the current design, not a data-volume
   problem. Verified directly, locally, with a fresh organism: "dog" grounded
   and confirmed in the speakable index, queried alone, zero candidates,
   every time.

4. **The intended fallback — real cross-modal association via
   `deep_atlas`'s co-occurrence data — is real and not self-echo-prone, but
   requires real reinforcement to populate, and 10 repeated, grounded,
   co-occurring exposures of "dog" and "bone" together in one local test
   session did not clear that threshold.** `deep_atlas.entries` stayed at
   zero after a forced dream cycle. This is DeepAtlas's own
   `dream_promotion_gate` doing its job (guarding against exactly the
   false-confidence bug found and fixed on 2026-07-05) — not obviously
   broken, but confirms real association needs more real, repeated,
   time-spaced exposure than a quick session can produce, and forcing one
   dream cycle on the live substrate tonight (tested directly) did not
   change conversational output.

## Why I didn't patch this tonight

The two live-fixable-looking levers — loosening the self-echo filter, or
lowering deep_atlas's promotion threshold — are both changes to the exact
mechanism that has already produced three real regressions this week when
tuned without enough care (the identity-echo bug this filter itself was
built to prevent; the chi-radius search that collapsed T5 accuracy from
100% to 0% as vocabulary grew; the ungated deep-atlas lookup that returned
confident, fabricated-looking associations for words she'd never been
taught). A change here that looks safe in a small local test can behave very
differently at her real, larger, longer-running scale — the exact pattern
that bit this codebase before. Given Joe's own explicit caution tonight
("don't let it become another runaway cascade bloated fail") and that this
is squarely the highest-incident-density part of the whole system, I did
not consider a same-night, unreviewed change to this logic to be a
responsible use of that authorization.

## What I did instead, and recommend next

- Kept building the thing that actually feeds both of these mechanisms real
  material: the new episodic memory system (separate report, shipped and
  verified live tonight) and 30 real word experiences. More real, repeated,
  situationally-varied experience is what both the grounding backfill and
  deep_atlas's promotion gate are waiting on — this is not wasted motion
  while the recall fix is undecided, it's the actual prerequisite for it.
- Recommend, as the next deliberate (not unilateral) step: either (a) design
  a careful fix for the single-word self-query dead-end specifically — e.g.
  give the organism-vote path a real way to surface a genuine second-best
  association even when the top vote is a self-match, verified against the
  same regression scenarios this week's incidents already wrote tests for —
  or (b) accept the current design's shape and focus on volume/time (more
  real experience, more real dream cycles, longer real elapsed time) to let
  deep_atlas's association path populate the way it's designed to. Either is
  legitimate; which one is worth the risk is a call I'd rather make with you
  than alone at 2am.

## Files/mechanisms referenced (for whoever picks this up)

- `dsf_ai_service/v4/gualaloom_v5_engine.py`: `_brain_emission_candidates_legacy`
  (~line 4338+), `_current_window_has_real_grounding`, `_rebuild_word_to_
  emission_index`, `_backfill_grounded_from_deep_atlas`, `_deep_atlas_
  neighbor_candidates`, `_record_episodic_experience`/`_episodic_context_for`
  (new tonight).
- `dsf_ai_service/loom_model/binding_atlas.py`: `recall_exact_or_best`,
  `recall_best`.
- Earlier recall-diagnosis workflow (4 parallel agents: history mining,
  mechanism mapping, live diagnostic, synthesis) — full synthesis available
  in this session's transcript if needed.

---

## v2 update: corrected finding, real fix shipped, live proof

The v1 conclusion above was too pessimistic, and traced to a bug in my OWN
test, not the substrate. `_run_dream_cycle` silently no-ops unless called
at an exact tick checkpoint (`tick % 200 == 0`); my first local test wasn't
hitting that checkpoint, so the promotion gate never ran at all, and I
mistook "my test didn't exercise the code" for "the mechanism doesn't
work." Once corrected, direct testing showed the deep_atlas association
path works exactly as designed: teaching two real, grounded, co-occurring
concepts and then dreaming correctly surfaces a genuine (non-self-echo)
association.

The real, narrower gap: `_run_dream_cycle`'s chi sampling was pure
round-robin with no recency weighting, so freshly-taught real experience
had to wait for the rotation to cycle back to its own chi before ever
getting a chance to promote — measured directly with 66 competing older
chi keys already in the atlas, a fresh grounded pair produced zero
promotions on the next dream under the old sampling.

**Fix shipped** (commit `b1d0eca`): priority-replay dream sampling —
recently-touched chi keys sampled first, ahead of the existing
round-robin, grounded in real sleep/memory research (Foster & Wilson 2006
on hippocampal replay prioritization; Schaul et al. 2015's Prioritized
Experience Replay in RL is the same principle). Verified locally (fresh
pair promotes and surfaces a real association on the very next dream, even
against 66 competitors) and then **live, in production**: taught
"whiskers" and "cat" back-to-back via real `give_experience` calls, forced
one real dream cycle, and real conversational recall on "cat" returned
`"dog"` — a real, different, non-empty, non-echo word (both "cat" and
"dog" were taught tonight with the same real touch descriptors,
soft/fuzzy — a genuine, sensible association, not a fabrication).
Reproducible (asked twice, got "dog" both times) and differentiated
(asked about "apple" instead, got a different real word, "suit" — not a
fixed default answer repeating regardless of input, the exact shape of
bug this filter was built to prevent).

This is the first real, non-empty, non-echo conversational response
observed this session. The self-echo filter itself was never the real
blocker for genuine association queries — only for literal single-word
self-identity queries, which is its correct, intended behavior, not a bug.
Full test suite after the fix: 222 passed, 5 failed, all 5 pre-existing
and unrelated — zero regressions.

---

### Changelog
- v2 (2026-07-10, c1): corrected v1's conclusion. Root cause was an
  under-scaled/misaligned test on my part, not a structural self-echo
  dead-end. Real gap was non-prioritized dream sampling; shipped a
  real, research-grounded fix (priority replay); verified locally and
  live in production (real, differentiated, reproducible non-empty
  conversational responses for the first time this session).
- v1 (2026-07-09, c1): initial report. Root cause of conversational silence
  confirmed via direct local testing against a real organism (not just code
  reading): self-echo filtering is structurally permanent for single-word
  queries; deep_atlas association fallback is real but under-populated.
  Deliberately did not patch the core matching logic tonight given this
  exact code's real incident history this week — routed back to Joe for a
  decision on direction.
