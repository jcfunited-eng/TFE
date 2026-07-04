# GL-RPT-P2-HABITUATION-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-HABITUATION-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: standing P2 order.
Seam: **4/6 — habituation.** Vehicle: her live-path source. Built and
measured in sandbox only — zero deploy action.

**Built the seam for READING only, and explicitly declined to build
it for ATTENDING_VISUAL/AUDIO/VIDEO — not an oversight, a scope
decision stated up front: pictures/sounds/videos have no real
organism sensory connection (P1 only wired language), so faking their
habituation through the organism would mean feeding it something she
never actually perceived. That's the definition of a simulated seam
this track's standing order prohibits, so those three stay on the
old shell counters.**

---

## Failures first

**1. Habituation is fundamentally item-based, and three of five item
kinds have no honest organism path.** `_action_salience`'s habituation
check runs for READING (corpora), ATTENDING (generic sensory items),
ATTENDING_VISUAL (pictures), ATTENDING_AUDIO (sounds), ATTENDING_VIDEO
(videos) — all keyed on a `times_attended`/`times_read_through`
counter on the item object. The organism has a real, live sensory
connection to exactly one of these: corpus TEXT (its actual words
flow through `read_word` every real read). Pictures/sounds/videos are
titles and binary blobs the organism has never perceived in any form.
Handing their habituation to the organism would require feeding it a
picture's TITLE as a stand-in for having seen the picture — a fabricated
signal, not a real one. Built READING's seam only; the other four
stay exactly as they were.

**2. The organism-derived freshness curve is measurably steeper than
the old counter-based one — a real, honest difference, not a
regression to hide.** Same corpus, same read count (5), same words:

| | fresh (0=familiar, 1=novel) |
|---|---|
| old (`times_read_through`-based, `1/(1+ln(1+n))`) | 0.358 |
| new (organism recognition, averaged over 10 sampled real words) | 0.025 |

The organism converges toward "fully familiar" much faster than the
old logarithmic curve over the same 5 reads. This changes the actual
NOVELTY payoff calculation in `_action_salience` (she'll treat this
corpus as re-read/stale sooner than before) — a genuine behavior
change from the handover, not a like-for-like swap. Whether that
steeper curve is desirable is a design question, not something I
tuned toward; it's simply what querying real organism state produces.

**3. Inherits seam 3's false-confidence risk directly.** The
per-word recognition calls this seam is built on can be confidently
wrong about genuinely novel content (no reject option in the
underlying recall, per seam 3's report). A corpus she's never read
could, in principle, sample words that happen to read as familiar by
coincidence, understating its true novelty. Not fixed here — same
open question already on record from seam 3.

---

## What shipped

`Guala._reading_freshness_from_organism(corpus)` (new): samples up to
10 real words from the corpus's own text (`corpus.lines[:5]`,
`len>1` words only) and averages `_recognition_from_organism`'s
surprise across them — same `[0,1]`, `1.0`=fresh convention
`_habituation_freshness` already used. Returns `None` only when the
corpus has no real text to sample (a data-availability edge case, not
"no organism signal") — the READING branch of `_action_salience`
falls back to a neutral `0.5` in that case, not the old counter
(explicitly not a silent reroute to the disconnected mechanism).

`_action_salience`'s READING branch updated to use it.
`ATTENDING`/`ATTENDING_VISUAL`/`ATTENDING_AUDIO`/`ATTENDING_VIDEO`
branches, and `_Corpus.is_new()` (a separate consumer of
`times_read_through`, used for completion-gain logic elsewhere, not
habituation) are untouched — out of this seam's honest scope.

Smoke-tested: freshness correctly reads `1.0` before any exposure,
drops to `0.025` after 5 real reads; empty-corpus edge case correctly
returns `None`; `_action_salience("READING", ...)` runs end-to-end
with no crash.

---

## Gates

- **No simulated seam**: verified the signal actually moves with real
  exposure (1.0 → 0.025 across 5 real reads, not a constant).
- **No fabrication**: the three item kinds with no real organism
  sensory connection were left alone rather than wired to a fake
  proxy signal — the harder, more honest choice, not the path of
  least resistance to a "6/6 done" count.

## What's not decided here

Whether the steeper habituation curve (Failure 2) is the right shape,
and whether/when a real visual or audio sensory tap should be built
so the other three item kinds can get an honest seam too, are calls
for Eve/Joe, not decided unilaterally here.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 4/6 (habituation) built for READING
  only; ATTENDING_VISUAL/AUDIO/VIDEO explicitly declined as
  unbuildable without fabrication, not silently skipped.
