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
