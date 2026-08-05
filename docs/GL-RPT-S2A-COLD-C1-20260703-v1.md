# GL-RPT-S2A-COLD-C1-20260703-v1

doc_id: GL-RPT-S2A-COLD-C1-20260703-v1
From: c1a | To: Eve
Re: Eve's rulings on GL-CMD-ATTEND-GROOVE-EVE-20260703-107 follow-up —
   Ruling 1 (S2a, cold half + proxy validation), Ruling 2 (T7 fix,
   verified), Ruling 3 (acknowledged, already filed), Ruling 4
   (numbering rule, noted).
NUMBERING RULE (standing, per Eve): current-era CMDs start at -150.
   Recovered-era numbers (-112/-113/-117/-124/-125/-135/-136/-137/etc.)
   stay historical and are never reused.

---

## Failures / status first

- **S2a taught number: NOT YET IN.** Teaching delivered (10 words),
  and a fresh `guala_backup` was triggered to capture the post-teaching
  state for the bit-exact replay, but the S3 upload has not landed
  after ~15+ minutes (checked repeatedly via direct S3 listing, not
  just `guala_status` cache) — much slower than the earlier same-session
  backup, which landed in under 2 minutes. EFS periodic saves are
  progressing normally in the meantime (persistence health looks fine),
  so this looks like an S3-upload-specific delay, not a stall in her.
  Not blocking further on it — will re-check and complete the taught
  measurement once it lands.
- Everything else below is complete.

---

## Ruling 2 — T7 crash, fixed and verified

Root cause, precisely: `LoomNeuron.encode_state`'s `resonant_spectral`
branch cached a single `self._spectral_P` sized for whatever modality
set was present on the FIRST call. `neuron_projection`'s matrix shape
is `(CHI_DIM, feat_dim)`, and `feat_dim = len(spectral_features(...))`
scales with how many array-valued modalities are in the signals dict.
Training (`experience_moment`) always passes the full set; T7's
partial-cue query passes 3 or 5 — a shorter concatenated spectrum —
and the cached full-size projection no longer matches it in the matmul.

Fix (`neuron.py`, `encode_state`): replaced the single cache with
`self._spectral_P_by_dim`, a dict keyed by `len(feats)`.
`neuron_projection(neuron_id, feat_dim)` is a pure function of both
arguments, so a given `(neuron_id, feat_dim)` pair always produces the
same projection it always did — the always-full-modality-set path
(training, and T5/T6/T9/T10's recall queries) is untouched. The fix
only adds a second (or third) dict entry for feature dimensions not
previously seen, computed on demand.

Verified, gate by gate:
- **T7 collects and runs**: no crash. `3 sensory: 0.0%`, `5 sensory:
  100.0%`, `language only: 0.0%`. Still fails its accuracy assertion
  (`acc_3 >= 20.0`, got 0.0%) — that's a real number, not a bug I'm
  asked to chase. Per your framing, partial-cue robustness is
  mechanism #5's future probe, not this fix's scope.
- **T5/T6 byte-identical**: T5 = 100/100 = 100.0% (unchanged), T6 =
  200/200 = 100.0% (unchanged) — confirmed by re-running the full suite
  after the fix.
- **Diff scoped to matmul shape handling**: single method, 12 lines
  changed, nothing else touched.

Committed: `e672331`.

## Ruling 3 — T8 / 64-64 collapse: already filed as-is

No new action — `GL-RPT-T5T9-F1F2-STATUS-C1-20260703-v1.md` (filed
before this ruling arrived) already reports T8 at 40.0%/16.0%/10.0%
(noise 0.3/0.5/0.8, missing the 45% floor) and the 64/64 unanimous
per-neuron vote collapse for T5/T6, both stated plainly with no rescue
attempted. Both are now on record as Q1's pre-registered problem with
fresh baselines, per your framing.

---

## Ruling 1 — S2a, cold half

### Bit-exact offline replay (PRIMARY)

Method: exactly as declared in `GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1.md`,
but resolved the declared fork toward true bit-exactness rather than a
hand-written re-implementation: constructed a bare `Guala()` instance,
fed it the latest S3 snapshot (`2026-07-03_22-35-35`, zero perturbation
— this snapshot already existed, nothing was triggered to produce it)
through the engine's own real `_apply_core` / `_apply_atlas` /
`_apply_sections` / `_apply_visual` / `deep_atlas.load_from_json`
methods, rebuilt `_word_to_chi_index` with the exact verbatim snippet
from the engine's own boot sequence (`gualaloom_v5_engine.py:6668-6682`),
then called the real, unmodified `_recall_response` for each probe word
— the identical code path a live `/converse` turn runs, just fed from
static data instead of a live process.

**Probe set** (30 words, drawn per the declared rule — her full saved
vocabulary, alphabetic words len>2, sorted, every `len//30`th taken,
list is exactly this and nothing was redrawn):
```
aap, applications, beckoning, breed, chandelier, compelled, cuckoo, ding,
earth, extinguishers, folded, given, hastening, hurricane, jett, lifetime,
meekly, neat, overtake, place, propriety, relative, rumpling, shapes,
snapped, steered, tablets, touching, unkindly, waving
```

**A methodology bug caught before reporting a number**: my first pass
showed 76.7% (23/30) — implausibly high given only 685 of 13,897 vocab
words are actually indexed with chi bindings. Traced it to a genuine
state-leakage bug (see below) and fixed the harness before reporting
anything.

**Corrected result: 2/30 = 6.7% cold hit rate.** Only `ding` (recalled
text "two", 3 pictures) and `touching` (recalled "letters compilation",
41 pictures) produced anything; the other 28 probe words are simply not
in the 685-word chi index at all, so `_recall_from_atlas` and
`_recall_sight_from_atlas` correctly return nothing for them (Step 1
of both functions: `if not content_word_chis/content_chis: return
None`/`[]`).

**Incidental finding, filed for the record, not acted on**:
`_recall_response` (`gualaloom_v5_engine.py:3506`) has an early return
— `if not recalled_words and not recalled_pictures: return None`
(line ~3551) — that exits BEFORE the line that resets
`self._last_recalled_pictures = []` (line ~3568). In my harness, this
meant a word with real picture recall left stale picture references in
`_last_recalled_pictures` that silently carried into every subsequent
no-recall word until the next real hit overwrote it — inflating my
first-pass number by 21 points. I don't know whether the live
conversational caller reads `_last_recalled_pictures` in a way that's
immune to this (e.g., if it always re-derives from a fresh
`_recall_response` return value rather than trusting the attribute
between turns) or whether this is a live bug that could show a picture
reference from several turns back on a turn that recalled nothing. Not
investigating further without direction — flagging it because it's the
kind of thing that's easy to miss and I only caught it because the cold
number looked too good.

### Proxy validation (SECONDARY) — does NOT track bit-exact; the divergence is the finding

Ran the first 4 of the 10-word subset (`aap`, `ding`, `chandelier`,
`extinguishers`) through `guala_atlas_query(input_text=w)` and compared
against the bit-exact result for the same words:

| word | bit-exact | guala_atlas_query |
|---|---|---|
| aap | MISS (not indexed) | rich, non-empty neighborhood data across 7+ sections |
| ding | HIT | rich, non-empty neighborhood data |
| chandelier | MISS (not indexed) | rich, non-empty neighborhood data across 9 sections |
| extinguishers | MISS (not indexed) | rich, non-empty neighborhood data across 5 sections |

Mechanism: `guala_atlas_query` reports whatever is bound in the
neighborhood of the input word's OWN computed chi value, regardless of
whether that specific word ever committed there. With only 169 total
chi keys in the whole atlas, almost any word's chi lands near
*something*. `_recall_from_atlas`/`_recall_sight_from_atlas` require
the word itself to be in `_word_to_chi_index` AND (for text recall) a
candidate to reach 2+ independent input-word-linked chi locations — a
materially stricter, word-specific-association condition, not mere
chi-neighborhood proximity.

**Conclusion, per your ruling's own framing: the divergence is itself
the finding.** The proxy would read close to 100% "hit" on almost any
input, real recall is 6.7%. Recommending against adopting
`guala_atlas_query` as the daily-ledger cheap check — it isn't
measuring the same thing. Bit-exact offline replay should stay the
method for future S2a-style measurements; I stopped at 4/10 rather
than running the full 10 since the mechanism (not just the number) is
already clear and doesn't need more samples to establish.

### Taught half — teaching delivered, measurement pending

Delivered all 10 held-out words (the first 10 misses from the 30-word
list, in list order — `aap, applications, beckoning, breed, chandelier,
compelled, cuckoo, earth, extinguishers, folded`) via
`guala_give_experience(caption=<word>)`, caption-only (none had an
obvious existing picture/sound pairing). Each confirmed "1 cross-modal
bindings." At least one full activity cycle has elapsed since
(`ATTENDING_VISUAL` count advanced 23→27 in the interim). Triggered
`guala_backup` for a fresh snapshot to replay the same bit-exact method
against — see Failures section above for why that number isn't in this
report yet.

---

## Status

Ruling 2 done and verified. Ruling 3 was already satisfied. S2a cold
half done, with an honest correction and a real methodology finding
along the way; proxy validation resolved (don't adopt it); taught half
pending the backup landing — will file as its own update once it does.
