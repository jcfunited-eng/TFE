# GL-RPT-S2A-TAUGHT-C1-20260703-v1

doc_id: GL-RPT-S2A-TAUGHT-C1-20260703-v1
From: c1a | To: Eve
Re: Ruling 4 (S2a taught number) + save-cost flag; wraps the S2a
   cold→taught pair started in GL-RPT-S2A-COLD-C1-20260703-v1.
Numbering: per the standing rule, current-era CMDs start at -150.

---

## Failures first

None on the measurement itself. One operational note, flagged per
Eve's instruction rather than investigated further by me: the
`guala_backup` trigger for this snapshot took **~16-17 minutes**
(triggered ~23:12-23:13Z, landed in S3 at `2026-07-03_23-29-23`) — far
slower than the earlier same-session backup during the groove
investigation, which landed in under 2 minutes. EFS periodic saves
were progressing normally in the meantime (persistence health looked
fine throughout), so this reads as an S3-upload-specific slowdown, not
a stall in her. **Flagging to c1b's save-cost forensic per Eve's
instruction** — worth checking whether this is the same disease as the
12-33s hot-save-time problem from the groove investigation (both are
"something about the write/upload path is slow, independent of
substrate size" symptoms).

Source used: the S3 backup landed before the 30-minute cutoff, so the
EFS-direct fallback wasn't needed this time — noting per instruction
which source was used.

---

## Taught result

Ran `tools/guala_recall_bitexact_replay.py` (the now-promoted
instrumentation) against the fresh post-teaching snapshot
(`2026-07-03_23-29-23`) for the same 10 held-out words delivered via
`guala_give_experience` in the prior report:

```
=== RECALL: 8/10 = 80.0% ===
  'aap': hit=True  recalled_text=None  n_pictures=2
  'applications': hit=True  recalled_text='something'  n_pictures=81
  'beckoning': hit=False  recalled_text=None  n_pictures=0
  'breed': hit=True  recalled_text='bark'  n_pictures=1
  'chandelier': hit=True  recalled_text='still'  n_pictures=6
  'compelled': hit=False  recalled_text=None  n_pictures=0
  'cuckoo': hit=True  recalled_text='bongo really there'  n_pictures=1
  'earth': hit=True  recalled_text='bongo very there'  n_pictures=1
  'extinguishers': hit=True  recalled_text='illustrations'  n_pictures=54
  'folded': hit=True  recalled_text='what will pond'  n_pictures=0
```

**Paired result: COLD 0/10 (0%) → TAUGHT 8/10 (80%).** (These exact 10
words were confirmed cold misses in the prior report — they were
literally drawn as "the first 10 misses" from the 30-word cold set —
so the cold baseline for this specific held-out set is 0%, not the
30-word set's 6.7%.)

**Not oversold**: 2 of 10 (`beckoning`, `compelled`) remain misses even
after teaching — a single `guala_give_experience` call doesn't
guarantee indexing. And several of the "hits" are recalled text that
doesn't read as semantically coherent (`'bongo really there'` for
`cuckoo`, `'bongo very there'` for `earth`, `'what will pond'` for
`folded`) — the measurement is "did `_recall_response` return
something non-empty," per the declared method, not "was the recall
meaningful." That's a real, separate quality question the raw hit-rate
number doesn't answer, and I'm not claiming otherwise. Picture-recall
counts are noisy (0 to 81) and not further analyzed here.

I have not independently ruled out that some of this exposure came
from ordinary background activity rather than my `guala_give_experience`
calls specifically — these are uncommon words unlikely to appear in her
current corpora (Frog and Toad, Amelia Bedelia, the counting/colors/
grammar books), so I'm attributing the jump to the teaching, but noting
the assumption rather than asserting certainty.

---

## Status

S2a complete: cold 6.7% (30-word set) / 0% (this 10-word held-out
subset), taught 80% (same 10-word subset), proxy method rejected and
replaced with standing bit-exact-replay instrumentation per Eve's
ruling. Slow-upload flag filed for c1b. Holding for next direction.
