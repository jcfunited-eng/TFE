# GL-RPT-P2-ASSOCIATION-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-ASSOCIATION-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: standing P2 order ("seam by seam... failures first, no
simulated seams").
Seam: **3/6 — association.** Vehicle: her live-path source
(`dsf_ai_service/v4/gualaloom_v5_engine.py`). Built and measured in
sandbox only — zero deploy action.

**Built the seam. Found something bigger than the seam while testing
it: the organism's recall mechanism has NO reject/uncertainty option
— queried with a word it has never seen, it still returns a
UNANIMOUS, 100%-confidence answer, every time, for something
completely unrelated. This is a "too-good" finding per the standing
rule (>95% anywhere = STOP with voter-spread proof), confirmed to be
pre-existing in the validated mechanism itself (identical at the
original n_samples=200, not something my performance fix introduced),
and it retroactively qualifies seams 1 and 2's own reports, not just
this one.**

---

## Failures first

**1. The organism recall mechanism cannot say "I don't know" — it
always commits to a specific answer, with population-wide unanimity,
even for words it has categorically never encountered.** Direct test
(`PYTHONHASHSEED=0`, reproducible): after teaching ~35 real words,
queried two words that were never taught at all:

```
  zzznever:  votes={'upon': 64}              surprise=0.000  (fully "recognized")
xyzabc123:  votes={'mother': 55, 'rabbits': 9}  surprise=0.141  (mostly "recognized")
```

`zzznever` gets a **100% unanimous, zero-uncertainty vote** for
`'upon'` — a real taught word with no plausible relationship to
`'zzznever'`. `_recognition_from_organism` reports this as
`surprise=0.000` — i.e., fully familiar. This is a false positive at
maximum confidence, exactly the shape of result the project's
standing `>95%` too-good rule exists to catch.

**2. Confirmed this is NOT something my performance fix (n_samples
reduction) introduced.** Re-ran the identical probe against a fresh
`Embryo` at the ORIGINAL `n_samples=200` (the full-resolution signal
the validated 100%-recall claim was built on): `zzznever` → `{'upon':
64}` — **identical**, fully unanimous, at full resolution too.
`xyzabc123` was actually MORE unanimous at 200 (`{'mother': 64}`) than
at 20 (`{'mother': 55, 'rabbits': 9}`) — if anything, the reduced
sample count showed slightly more internal disagreement, not less.
So this is a pre-existing property of the recall mechanism itself
(`binding_atlas.recall_best()` always returns the nearest match —
there is no distance/confidence threshold below which it returns
"nothing"), not a regression from Failure 2/3 of the prior fix
report.

**3. This retroactively qualifies seams 1 and 2's own "100%
recall"/"real discrimination" claims — worth restating precisely, not
walking back.** Seam 1's 100% recall number was measured on TAUGHT
words recalling THEMSELVES — that number stands, verified again here
(`peter`→`peter`, `rabbits`→`rabbits`, both 100% self-consensus).
What seam 1 and 2 did NOT test, and what this seam's own testing
surfaced, is the OTHER direction: does the organism correctly
recognize when it DOESN'T know something. It does not, reliably. The
"0% recall" and "zero discrimination" failures reported in seams 1-2
were about known words not being found; this is the mirror problem —
unknown words being confidently claimed as known. Both are real,
independent failure modes of the same underlying mechanism.

**4. Association itself, once past that caveat, works and produces
real, traceable output.** `association('peter')`/`association('rabbits')`
correctly return `None` (self-echo — the organism "associates" the
word most strongly with itself, filtered out as not a real
association, matching the existing seam-1 convention). The false-
positive risk from Failure 1 means an association COULD be drawn from
an out-of-vocabulary seed and presented with false confidence — named
here as a live risk for this specific mechanism (`_daydream_tick` runs
continuously, autonomously, on whatever she's recently attended to,
so it will eventually query rare/novel recent words).

---

## What shipped

`Guala._association_from_organism(seed_word)` (new): "what goes with
this word" via the organism's own recall — replacing
`_daydream_tick`'s `deep_atlas.entries[chi].co_occurrence` walk.
Reuses `_recall_from_organism` (seam 1) for the query and
`_word_to_emission_sections` (same as `_brain_emission_candidates`/
seam 1) to translate the result into a real, already-committed
section slot. Self-echo filtered (returns `None` if the organism's
"association" for a word is the word itself). Weight = population-
vote consensus (same measure as seam 2's recognition).

`_daydream_tick` rewritten: Phase 1 now snapshots `seed_word`
alongside `seed_chi` (both already available in `sec.commits`' own
`{tick, mode_idx, chi, word}` record — no new lookup needed). Phase 2's
deep-atlas co-occurrence walk replaced by one
`_association_from_organism` call. The affect-weighting (Extension B)
is adapted, not removed: the organism has no per-binding valence/
arousal record the way deep_atlas entries do, so the bias now reflects
only her CURRENT needs state — named plainly as a real change in what
the number means, not silently kept looking the same. Novel-jump
(Extension A, deliberately random exploration) and consolidation
(Extension C, deep_atlas's own invariant upkeep) are untouched — both
are functionally separate from "association" and weren't in scope.

Smoke-tested: `_daydream_tick()` runs without crashing, correctly
returns early (writes nothing) when the organism has no association
for the current seed, and produces real, traceable writes
(`daydream_surface` events with brain-sourced word/section/strength)
when it does.

---

## Gates

- **No simulated seam**: the association really comes from the
  organism's own recall, verified to trace through to a real,
  already-committed section slot, not a stub.
- **>95% too-good rule**: triggered by this seam's own testing (100%
  unanimous vote for an unseen word) — investigated immediately,
  root-caused (pre-existing, resolution-independent), reported here
  rather than left for someone else to rediscover.
- **No tuned constants**: no threshold was added to suppress the
  false-positive risk found in Failure 1 — reporting it plainly
  instead of quietly patching around it with an invented cutoff.

## What's not decided here

Whether the false-confidence-on-novel-input property (Failure 1) is
acceptable to keep shipping through the remaining P2 seams as-is, or
whether it needs its own fix (e.g., a genuine reject threshold on
vote count/spread, which WOULD need real measurement before being
adopted, not guessed), is a call bigger than this one seam — flagging
it now, at seam 3, rather than only mentioning it after seams 4-6 are
also built on the same primitive.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 3/6 (association) built and measured.
  Surfaced a >95%-class false-confidence finding in the underlying
  recall mechanism, confirmed pre-existing (not from my earlier
  n_samples fix), reported prominently rather than as a footnote.
