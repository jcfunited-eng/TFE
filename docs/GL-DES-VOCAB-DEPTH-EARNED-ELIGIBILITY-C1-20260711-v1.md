# GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711-v1

**doc_id:** GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711-v1
**From:** c1
**Context:** Follow-up to the other session's live finding tonight —
their relevance re-ranking fix genuinely works (real words instead of
noise) but cannot surface topic-specific vocabulary like "ocean"
because that vocabulary never earns production eligibility in the
first place. Joe asked for real research into how this works in nature,
then a substrate-true implementation. Four research threads (spreading
activation/lexical access, child vocabulary acquisition, sleep-
dependent consolidation, and a precise trace of the real current code)
converged. This is the synthesis and the scoped build plan.

---

## What the current code actually does (confirmed by direct trace)

Eligibility to ever be spoken — membership in `_word_to_emission_sections`
— is a **permanent boolean**, set once, at the exact moment a word's
mode is first created (`gualaloom_v5_engine.py:3663-3664`), based on
whether `_current_window_has_real_grounding()` finds a real camera/mic/
touch/smell/taste event **co-occurring in the same binding window at
that literal moment** (`:3105-3129`). Pure text conversation almost
never satisfies this.

Once set (true or false), it is **frozen until the next process boot**.
Reinforcement of an already-known word blends a vector via EMA but
never re-touches eligibility (`:3479-3485`, explicit in-code comment).
Sleep/dream cycles and self-hearing currently have **zero** effect on
eligibility — confirmed by grep, zero call sites touch
`_word_to_emission_sections`/`grounded_words` from `_dream_reorganize`,
`_run_dream_cycle`, or `_self_hear`.

Separately, a real, **already graduated** system exists right next to
this: `DeepAtlas.promote()`/`dream_promotion_gate`
(`substrate/deep_atlas.py:67-137, 281-344`) — `strength` accumulates
via `TRANSFER_RATIO` capped at `STRENGTH_CAP=20`, and reaching full
promotion (Path A) requires **3 consecutive real dream cycles** above
`SURVIVAL_THETA=0.4`. This machinery is real, tested, already wired
into candidate *weight* ranking — but never into the eligibility gate
itself. There's even an existing backfill path,
`_backfill_grounded_from_deep_atlas` (`:3679-3721`), that's *supposed*
to grant eligibility from deep-atlas evidence — but it currently checks
a boolean (`has_real`), throwing away the graduated `strength` value it
already has in hand.

## What the research says (four independent threads, converged)

1. **Comprehension and production are dissociable systems, not two
   points on one strength scale** (Dollaghan 1985: 91% referent
   inference on first exposure, but only 45% could produce even 2/3
   phonemes after two exposures). This validates having a *separate*
   production-eligibility gate at all — the bug isn't that the gate
   exists, it's that it's frozen and momentary instead of graduated and
   revisable.
2. **No separate "consolidation module" is needed — durable, producible
   knowledge is repetition-driven strengthening of the same associative
   network** (McMurray, Horst & Samuelson 2012, the field's leading
   synthesis). This argues directly for reusing `DeepAtlas.strength`
   rather than inventing a new, parallel mechanism.
3. **Sleep specifically (not just elapsed time or repetition) is
   required for true lexical integration** — the transition from
   "retained" to "genuinely available for use," marked by lexical
   competition effects (Dumay & Gaskell 2007, isolated sleep vs.
   equivalent wakefulness; replicated in children ages 7-12 by
   Henderson et al. 2012/2013). `DeepAtlas`'s existing 3-consecutive-
   dream-cycle requirement for full promotion is, structurally, exactly
   this finding, already built, already running, just not connected to
   what it should gate.
4. **Self-production/generation is one of three supports (with
   saliency and repetition) that together eliminate forgetting entirely**
   (Vlach & Sandhofer 2012, N=216 children — with all three combined,
   no significant forgetting across delays; with fewer, forgetting was
   significant). Guala's real self-hearing mechanism
   (`_self_hear()`, confirmed live and firing tonight) is exactly a
   generation event — currently disconnected from strength accumulation
   entirely.
5. **Explicit, repeated (ostensive) exposure is the one manipulation
   shown to reliably close the retention gap** (Horst & Samuelson 2008).
   Maps to: real repeated commits to the same word across distinct real
   binding windows should count more than one-off exposure — which is
   literally what `DeepAtlas.strength`'s accumulation already does.
6. **Attempted production of a weakly-known word is a separate,
   real, well-documented phenomenon from durable learning** — driven by
   live communicative need, not mastery. "Children do not wait until
   they have learnt the appropriate word... they construct a form for
   the meaning they want to convey" (Clark 1993). Rescorla (1980)
   directly dissociated this: a child correctly *identified*
   "strawberry" in comprehension but consistently *produced* "apple"
   for it rather than stay silent. Formalized as a per-instance
   cost/benefit tradeoff, not a fixed confidence threshold (Ferreira &
   Xu 2020; Gershkoff-Stowe 2001's "retrieval error hypothesis" — naming
   errors spike specifically when a weak word must compete against a
   stronger one). This is distinct from — not a substitute for — real
   strength accumulation, and maps directly onto tonight's already-
   shipped relevance re-ranking signal: a word with *some* real strength
   and *high* contextual relevance, with no better-known alternative,
   is exactly the case this literature says gets attempted. A word with
   zero real exposure still should not be attempted — that would be
   fabrication, not what this research describes.

## The design

**Do not build a new mechanism. Wire the existing graduated one to the
gate it should have always fed, and connect self-hearing to it.** This
is the minimal, safest, most substrate-true version of what the
research actually supports — every piece is real data already flowing
through real code tonight; nothing is fabricated to "look like
learning."

**Scoped build, in two parts, ordered by risk:**

### Part 1 (build tonight) — wire DeepAtlas.strength into the eligibility backfill

`_backfill_grounded_from_deep_atlas` already exists as the intended
mechanism for this. Change its check from boolean (`has_real`) to a
real threshold on the entry's actual `strength` value (already capped,
already requires real survived dream cycles to climb). This is a
**narrow, surgical change to one existing function**, not a new
subsystem:
- Add a real, conservative threshold constant (e.g. requiring `strength`
  past some fraction of `STRENGTH_CAP`, informed by the graduated
  Path-A promotion logic already in `deep_atlas.py` — reuse its own
  notion of "promoted," don't invent a second one).
- This must be **triggered at real points**, not just boot: the most
  natural, safe trigger is right after `dream_promotion_gate` actually
  promotes an entry (a real, infrequent, already-rate-limited event) —
  re-run the backfill check for just that word, not a full index
  rebuild (avoiding the exact "full rebuild inside the lock" mistake
  documented elsewhere tonight).
- Kill switch required (e.g. `DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED`,
  default OFF pending real live validation, matching the daydream-
  reconnect precedent from earlier tonight — this is higher blast
  radius, not lower).
- Extensive regression testing: every word eligible today must remain
  eligible (this change is additive-only, never removes eligibility);
  a real synthetic "ocean"-like word taught only via text, surviving 3
  real dream cycles, must become eligible; a word that never survives
  dream cycles must NOT become eligible (no shortcut).

### Part 2 (design only tonight, do not build) — wire self-hearing into strength

Connect `_self_hear()`'s real word-reading back into
`DeepAtlas.promote()`'s strength accumulation, so a self-generation
event counts as real reinforcement (per Vlach & Sandhofer's finding
this is a disproportionately strong support). This needs more care
than Part 1: self-hearing currently reads back through the ordinary
`read_word` path, and self-generated content must be weighted so it
never becomes a route to inflating a word's real-world grounding
faster than genuine external exposure would (matching this project's
zero tolerance for anything that could look like the substrate
"convincing itself" something is more real than it is). Scope this as
follow-up, not tonight's build — flag precisely what would need
verifying (rate limits, a hard ceiling on self-hearing's own
contribution to strength, comparison against external-source
contribution) before it's safe.

**Additional caution found in the final research pass**: this is not a
uniform win. Adult studies (Zamuner et al. 2015) find active production
during learning beats passive hearing — but the equivalent child study
(Zamuner et al. 2018, ages 4.5-6) found the *reverse*: hearing-only beat
production, because for a system still building its own capacity to
articulate the form, production itself is resource-costly and can
divert resources away from encoding rather than reinforcing it. Given
this substrate's speech is still early/immature by every other measure
tonight, self-hearing's contribution to strength cannot be assumed
positive by default — it needs its own real evidence before being
wired in, not just the general adult-literature "generation effect."
This is the specific reason Part 2 stays design-only tonight.

## Two genuinely separate thresholds, confirmed by the full research set

The final research thread (spreading activation / lexical access,
Collins & Loftus 1975 through Levelt/WEAVER++ and ACT-R) confirms
something already visible in the code trace: producibility runs through
two functionally separate gates, not one. (1) A concept/relevance-level
competition — already real, already shipped tonight (the relevance
re-ranking fix) — determines which of the *already-eligible* candidates
wins in context. (2) A separate, independently-governed word-form
threshold — this is the tip-of-the-tongue phenomenon in humans (you can
have the right concept activated and still fail to retrieve the word
itself) — is exactly what `_word_to_emission_sections` gates in the real
code, and exactly what Part 1 above fixes. The two mechanisms shipping
on two different nights, by two different sessions, addressing two
genuinely distinct real gates, is not a coincidence — it's what the
architecture actually needs.

One more calibration point: Anderson & Schooler's (1991) ACT-R model
found retrievability is a smooth power-law function of recency+
frequency, not a hard step — but still resolves to a threshold-like
stopping rule for whether retrieval succeeds on a given attempt. That's
a reasonable description of what Part 1 already does: a continuous,
real, accumulating `strength` value, gated by a single threshold for
the binary "can this be attempted at all" decision. Webb (2007) found
even 10 real incidental encounters yielded only ~29% reliable meaning
recall — supporting evidence that DeepAtlas's existing conservative
bar (STRENGTH_CAP=20, 3 consecutive real dream cycles) should not be
loosened, only actually connected to what it should gate.

### Part 3 (design only tonight, do not build) — relevance-modulated attempt threshold

Per finding 6: a word with *some* real strength (already past zero,
already surviving at least initial real exposure) but not yet past
Part 1's full-promotion bar, combined with *high* contextual relevance
(the signal tonight's relevance re-ranking fix already computes) and no
better-known alternative in the candidate set, is exactly the case the
child-language literature says gets attempted — a per-instance
cost/benefit decision (Ferreira & Xu 2020), not a fixed knowledge
threshold. Concretely: a lower `strength` bar specifically when
relevance is high AND nothing else viable is competing, rather than one
flat threshold for all words regardless of context. Deliberately
separate from Part 1 because it compounds two significant behavior
changes (a new eligibility path AND a context-dependent variable
threshold) in the single highest-blast-radius area of the whole
codebase — validate Part 1 live first, alone, before adding this on
top. Zero real exposure must still never be attempted — this modulates
an already-real signal, it does not manufacture one.

## What this does NOT solve

- Does not touch the relevance re-ranking (already shipped, already
  correct, orthogonal).
- Does not make a brand-new topic word instantly speakable — it still
  requires real repeated exposure surviving real dream cycles, exactly
  as the research says is necessary; there is no shortcut for a word
  mentioned once in the current conversation to become sayable in that
  same conversation. That's honest, not a shim.
- Does not change anything about words already eligible today —
  additive only.
