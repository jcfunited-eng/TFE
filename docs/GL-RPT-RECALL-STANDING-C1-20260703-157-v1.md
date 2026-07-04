# GL-RPT-RECALL-STANDING-C1-20260703-157-v1

doc_id: GL-RPT-RECALL-STANDING-C1-20260703-157-v1
From: c1a | To: Eve
Responds to: GL-CMD-RECALL-MEASURE-STANDING-EVE-20260703-157-v1
   (Step-0 filed at `0f9d17d`).

---

## Failures first

**Quality is 0/8 (0.0%), not the CMD's estimated 6/8.** Per the CMD's
own instruction ("if his number differs, his number wins"), 0/8 is
what's filed in `docs/GL-RECALL-DAILY-20260703.md`. Ran
`--quality-report` against the exact taught-run data from
`GL-RPT-S2A-TAUGHT-C1-20260703-v1.md` and applied the coherence rule
exactly as declared (exact-match, non-stopword-filtered, against the
probe word or its bundle caption — each bundle's caption was the probe
word alone, so the target set is just `{probe word}` in every case).
None of the 8 hits' returned tokens contain the probe word:

```
aap           -> tokens=[]                          coherent=False
applications  -> tokens=['something']                coherent=False
breed         -> tokens=['bark']                     coherent=False
chandelier    -> tokens=['still']                    coherent=False
cuckoo        -> tokens=['bongo','really','there']    coherent=False
earth         -> tokens=['bongo','very','there']      coherent=False
extinguishers -> tokens=['illustrations']             coherent=False
folded        -> tokens=['what','will','pond']        coherent=False
```

The 80% taught hit rate is real — something comes back where nothing
did cold — but by the declared rule, zero of it is verifiably *the
taught content itself* returning. This sharpens the CMD's own
HIT-vs-QUALITY framing further than my prior report did: I'd only
flagged 3 of the 8 hits as visibly incoherent there; the precise rule,
run rigorously, says all 8 are. Not editorializing on whether the rule
is too strict — it's the rule as declared, and it stands until someone
proposes changing it on the record.

---

## C-157-1 — daily record filed

`docs/GL-RECALL-DAILY-20260703.md` (`022e4d5`): cold 2/30 (6.7%),
taught 8/10 (80.0%), quality 0/8 (0.0%, see above), coherence rule
quoted verbatim from the CMD. Day 1 (pre-standing-rule) intentionally
not backfilled with invented numbers — pointed at the S2A reports
instead.

## C-157-2 — `--quality-report` flag shipped

`tools/guala_recall_bitexact_replay.py` (`7535a32`): prints each
probe's `returned_tokens` and a `coherent` verdict per the exact rule
(implemented as `is_coherent()` — exact match only, no stemming/fuzzy
match, so a future session can't quietly loosen it without the diff
showing). Also added `--captions` so a future run with real
multi-word bundle captions (not just `caption=<word>`) can supply them
— defaults to mirroring the probe words, matching how this session's
teaching was actually delivered.

Gate check: re-ran without `--quality-report` first — identical 8/10
hits/misses to the original run, confirming the flag only adds
reporting, doesn't touch recall logic.

## C-157-3 — provenance header

9-line paragraph added to the module docstring (within the ≤10-line
budget), naming the 6/22 population-collapse audit, the `cbe8ed2`
harness-deception precedent, and Joe's teaching-loop principle — why
this tool exists and why it measures cold+taught as a pair.

---

## Gates

**G-157-1** — daily record filed on origin (`022e4d5`); cold/taught
numbers match the S2A reports exactly (2/30, 8/10); quality rule
quoted verbatim. **PASS.** (Quality *value* differs from the CMD's
estimate — expected and instructed; see Failures.)

**G-157-2** — `--quality-report` reproduces the same hits/misses as
the prior run; per-probe returned tokens visible in the output.
**PASS**, verified above.

**G-157-3** — diff scoped to: one new doc (`GL-RECALL-DAILY-20260703.md`),
one flag + one header note in one existing tool file. No engine files
touched. **PASS.**

---

## Status

All three C-157 items shipped, no deploy involved (measurement +
documentation only, as the CMD's vehicle line said). Holding for next
direction.
