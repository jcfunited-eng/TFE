# GL-RPT-P2-RECOGNITION-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-RECOGNITION-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: standing P2 order ("seam by seam... failures first, no
simulated seams").
Seam: **2/6 — recognition.** Vehicle: her live-path source
(`dsf_ai_service/v4/gualaloom_v5_engine.py`). Built and measured in
sandbox only — zero deploy action.

**Built the seam. The number is worse than seam 1's, and worth
reading before seam 3: this is very likely the SAME underlying
weakness surfacing a second time, not two independent problems.**

---

## Failures first

**1. Side-by-side on the same taught snapshot, the organism-based
recognition seam shows ZERO discriminating power — every probe,
taught or not, reads maximally novel.** Direct comparison (5 sentences
× 5 repeats, 6 probes including one genuinely novel word):

| probe | OLD (atlas-chi familiarity) | NEW (organism consensus) |
|---|---|---|
| peter (taught) | 0.000 (fully familiar) | 1.000 (maximally novel) |
| rabbits (taught) | 0.000 | 1.000 |
| naughty (taught) | 0.000 | 1.000 |
| away (taught) | 0.000 | 1.000 |
| once (taught) | 0.000 | 1.000 |
| zzznever (never taught) | 1.000 (correctly novel) | 1.000 (correctly novel) |

The old mechanism cleanly separates taught from novel (0.0 vs 1.0).
The new mechanism reads 1.0 for **everything**, taught or not — it
currently cannot tell the difference at all under realistic
(multi-word) exposure. This is a real, measured regression, not a
partial one.

**2. This is very likely the same weakness as seam 1 (recall),
surfacing again, not a second independent problem.** Both seams sit
on the exact same primitive: `self.organism.recall({"language": word})`.
Seam 1 found this returns an empty `Counter()` (zero votes at all) for
most taught words under realistic multi-word exposure — recognition's
`total = sum(votes.values())` being `0` in that same condition is
`_recognition_from_organism`'s own honest `return 1.0` (maximally
novel) path, by direct construction from the SAME empty-vote
condition. In an isolated, single-word-only test (teach "lantern" 10×
with nothing else fed), recognition correctly reads 0.0 (fully
recognized) — matching seam 1's own "near-fresh" test where recall
also worked, until other words crowded the population vote. **The
pattern across both seams is the same: the organism's population-vote
recall works when it's the only thing that's been taught, and
collapses to nothing once realistic, multi-word experience
accumulates.** This is worth surfacing plainly before seam 3
(association), since association is built on the SAME recall
primitive again — I expect the same pattern to show up a third time,
and I'll test for it directly rather than assume.

**3. `_compute_surprise` is now fully disconnected (zero call sites)
but not deleted** — same pattern as `_recall_from_atlas` in seam 1.

---

## What shipped

`Guala._recognition_from_organism(word)` (new): the organism's
population-vote CONSENSUS (top-voted concept's share of all votes
cast) as the recognition/familiarity signal — `1.0 - consensus`, a
direct, untuned linear inversion of an already-[0,1] fraction (no
rescaling constant invented, unlike the old `_compute_surprise`'s
`* 2.0`, which had a different natural range to correct for). No
votes at all → `1.0` (maximally novel), matching `_compute_surprise`'s
own contract exactly (empty evidence → 1.0).

Both live call sites updated: `read_word`'s per-word surprise
computation (word is directly available there — no chi-to-word
translation needed), and `_converse_phased`'s high-surprise
clarification-shape check (already had `words` in scope alongside
`input_chis`). `_compute_surprise` itself untouched, left defined,
disconnected.

Smoke-tested: `converse()` still runs end-to-end with no crashes.

---

## Gates

- **No simulated seam**: verified directly — the function actually
  queries the organism and actually returns different values for
  different real conditions (0.0 when isolated-taught, 1.0 when
  never taught OR when the population vote has collapsed to nothing
  under realistic exposure). Not a stub returning a constant.
- **No tuned constants**: the inversion is a direct `1.0 - x` on an
  already-normalized fraction; no scaling factor added to make the
  number look better.

## What's not decided here

Same as seam 1: whether to accept this now (matching the "immature
and true" standard, on the reasoning that a real, currently-blunt
signal is still more honest than a fluent-sounding fake one) or hold
until there's a strategic answer to the underlying weakness (both
seams now point at the same root cause: population-vote consensus
under event_count observable degrades sharply once more than a
handful of words are in play). That root-cause question — worth
answering once, rather than re-discovering it in seams 3-6 — is
flagged to you now rather than three more seam reports from now.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 2/6 (recognition) built, measured,
  found to share seam 1's root weakness. Reported before seam 3.
