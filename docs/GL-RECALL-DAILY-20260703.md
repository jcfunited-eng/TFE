# GL-RECALL-DAILY

Standing recall log. Measured via `tools/guala_recall_bitexact_replay.py`
(bit-exact offline replay against a save snapshot) — no other method is
trusted for these numbers. See
`docs/GL-CMD-RECALL-MEASURE-STANDING-EVE-20260703-157-v1.md` for why.
Cadence: weekly + after any recall-touching deploy.

## Coherence rule (verbatim, per GL-CMD-157 — do not relax)

> quality = the fraction of TAUGHT hits whose returned content is
> semantically coherent against the probe. Coherence rule (declared NOW,
> before it can be tuned): a returned recall counts as coherent iff at
> least one of the returned tokens matches the probe word OR its bundle's
> caption words, non-stopword-filtered. That rule is EXPLICIT so future
> Eves cannot quietly relax it.

Exact string match only (case-insensitive, stopword-filtered) — no
stemming, no fuzzy match. Implemented in `guala_recall_bitexact_replay.py`'s
`is_coherent()`; reproducible from the CLI via `--quality-report`.

## Log

| Day | Date | Cold (R_c/N_c) | Taught (R_t/N_t) | Quality (Q_t/R_t) |
|---|---|---|---|---|
| 2 | 2026-07-03 | 2/30 (6.7%) | 8/10 (80.0%) | **0/8 (0.0%)** |
| 3 | 2026-07-04 | 2/30 (6.7%) | 8/10 (80.0%) | 0/8 (0.0%) — VARIANT L, code-committed / **NOT YET DEPLOYED LIVE** (see Day 3 detail) |

Day 1 predates this standing log (the ad hoc S2A measurement that led to
this dispatch) and isn't backfilled here with unverified numbers — see
`GL-RPT-S2A-COLD-C1-20260703-v1.md` / `GL-RPT-S2A-TAUGHT-C1-20260703-v1.md`
for that raw work.

## Day 2 (2026-07-03) detail

**Quality is 0/8, not the 6/8 estimated in the CMD dispatch — per the
CMD's own instruction ("if his number differs, his number wins"), this
is the number that stands.** Ran `--quality-report` against the exact
taught-snapshot data from `GL-RPT-S2A-TAUGHT-C1-20260703-v1.md`:

```
'aap':           recalled_text=None                    tokens=[]                              coherent=False
'applications':  recalled_text='something'             tokens=['something']                   coherent=False
'breed':         recalled_text='bark'                   tokens=['bark']                        coherent=False
'chandelier':    recalled_text='still'                  tokens=['still']                       coherent=False
'cuckoo':        recalled_text='bongo really there'     tokens=['bongo','really','there']       coherent=False
'earth':         recalled_text='bongo very there'       tokens=['bongo','very','there']         coherent=False
'extinguishers': recalled_text='illustrations'          tokens=['illustrations']                coherent=False
'folded':        recalled_text='what will pond'         tokens=['what','will','pond']           coherent=False
```

Every one of the 8 hits fails the coherence rule under exact match: none
of the returned tokens equal the probe word (each word's bundle caption
was the word itself — `guala_give_experience(caption=<word>)`, no
additional caption text — so the coherence target set is just `{probe
word}` in every case). The 80% taught number is real (something comes
back where nothing did cold), but by this explicit rule, none of it is
verifiably *the taught content* coming back — it's recall of *something*,
not retrieval of *that* memory. This is the c1a HIT-vs-QUALITY
distinction the CMD names, borne out at its most literal: 0%, not a
partial win.

Not editorializing further on whether the rule is too strict — it's the
rule as declared, deliberately, so it can't be quietly loosened later.
If a future measurement wants a looser coherence bar, that's a decision
for whoever's running that week's log to propose and record here, not
something to assume.

**Context note (GL-CMD-RECALL-REACH-EVE-20260704-159-v1 Part D.2, appended
2026-07-04 — the Day 2 entry and numbers above are untouched):**

> 0/8 structurally pinned — routing gap (-158 F-1 primary) + excluded-self
> (-159 F-2 secondary) + bare captions; see -158/-159.

## Day 3 (2026-07-04) detail

Part A of -159 ran an offline A/B (replay harness, `--variant {svo,L,LI}`)
against the IDENTICAL Day 2 snapshots (cold `2026-07-03_22-35-35`, taught
`2026-07-03_23-29-23`) — not a fresh measurement of her current live
state. VARIANT L (subject/verb/object+listen) and VARIANT LI (+intro)
tied on cold (2/30 both), taught (8/10 both), quality (0/8 both — F-2's
bare-caption self-exclusion, predicted and confirmed), and reachability
(8/10 both, up from 0/10 under unmodified `svo` — the F-1 fix visibly
working even though quality stays 0 by the declared coherence rule).
L won the declared tie-break (smaller surface; LI carried ~39% more mean
candidate-set crowding for identical measured benefit). Full tables in
`GL-RPT-RECALL-REACH-C1-20260704-159-v1.md`.

**VARIANT L is committed (`003200f`) but NOT YET DEPLOYED to the live
service** — per the CMD's Vehicle assignment ("Parts B/C ride the -155
pattern"), vehicle/deploy-window assignment is Eve's call, not this
session's. The Day 3 row above is the offline post-fix triple, filed now
per the CMD; it will be re-measured against a live post-deploy snapshot
once Eve calls the next sleep_for_deploy window, and that will be filed
as its own dated line rather than silently overwriting this one.

**Measurement design rule (-159 D.3, on the record, coherence rule text
UNCHANGED):** future experience-bound probe sets MUST use multi-word
captions (≥3 non-stopword words) via `--captions`, not bare single-word
captions — bare captions make the coherence target set exactly `{probe
word}`, which `exclude_words` then structurally withholds (F-2),
pinning quality at 0 regardless of whether recall is actually working.
