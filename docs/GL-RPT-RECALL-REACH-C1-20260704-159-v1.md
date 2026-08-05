# GL-RPT-RECALL-REACH-C1-20260704-159-v1

doc_id: GL-RPT-RECALL-REACH-C1-20260704-159-v1
From: c1a | To: Eve
Responds to: GL-CMD-RECALL-REACH-EVE-20260704-159-v1 (Step-0 filed `bad9374`).

Commits this report is built on (all pushed, `origin/guala-live`):
`40021ce` (Part A instrumentation) · `16d5c3f` (Part C fix) ·
`003200f` (Part B ship) · `8d15cf4` (Part D.2/D.3 daily-log update).

---

## Failures first

1. **G-159-3's "index rebuild determinism preserved" does NOT hold in
   general.** Testing Part C's fix surfaced a **second, separate**
   index-bypass mechanism (`Section.receive`'s deep-atlas reinstatement
   block, lines 630-652) that this CMD's F-3 does not name and this fix
   does not touch. Full detail under Part C. The fix I shipped is proven
   correct for the ONE thing F-3 convicted (a word's own primary commit);
   it is NOT a complete fix for "live index staleness" as a general
   problem.
2. **Part B's emission-path regression check is NOT MEASURED.** VARIANT
   L and the F-3 fix are committed but **not deployed to the live
   service** — Vehicle assignment ("Parts B/C ride the -155 pattern") is
   Eve's call, and no sleep_for_deploy window has been called. A
   pre-deploy baseline read is recorded below; the actual before/after
   comparison can only happen once Eve calls the deploy.
3. **Part D's decay math is a bound, not a closed derivation.** The
   persisted commit log proves all three NOT-IN-SNAPSHOT probes were
   genuinely bound (contradicting how that verdict reads at first
   glance — see below), but it doesn't retain per-event strength, so I
   can't reconstruct an exact strength trajectory from teaching to
   forgetting. Stated as a bound with the best-evidenced mechanism named,
   not asserted as more precise than the data supports.

None of the above is save-path loss (see Part D) — no escalation
triggered.

---

## Part A — offline A/B (VARIANT L vs VARIANT LI)

Method: `tools/guala_recall_bitexact_replay.py --variant {svo,L,LI}`
(new flag, this CMD), against the **identical Day-2 snapshots** used for
`GL-RECALL-DAILY-20260703.md` — cold `2026-07-03_22-35-35` (30 probes),
taught `2026-07-03_23-29-23` (10 probes, the same bare-caption bundles
from `GL-RPT-S2A-TAUGHT-C1-20260703-v1.md`). `svo` = unmodified
production, included as the baseline for A.2's crowding comparison, not
as a proposed variant.

### A.1 — full triple

| | svo (baseline) | VARIANT L (svo+listen) | VARIANT LI (svo+listen+intro) |
|---|---|---|---|
| Cold (30 probes) | 2/30 (6.7%) — `ding`, `touching` | **2/30 (6.7%)** — same 2 words, same text | **2/30 (6.7%)** — same 2 words, same text |
| Taught (10 probes) | 8/10 (80.0%) | **8/10 (80.0%)** | **8/10 (80.0%)** |
| Quality (`--quality-report`) | 0/8 (0.0%) | **0/8 (0.0%)** | **0/8 (0.0%)** |

Cold: **tied, no regression** (gate satisfied — both ≥ baseline 2/30).
Taught hit-rate: tied. Quality: tied at zero for **both** variants — the
bare-caption self-exclusion the CMD predicted (F-2) actually occurred:
every one of the 8 "hit" turns now returns *more* text under L/LI
(e.g. `cuckoo` → `'bongo really there two'` instead of `'bongo really
there'`), but the coherence target for these bare-caption bundles is
exactly `{probe word}`, and `exclude_words` withholds the probe word
from its own return regardless of section surface. F-2 is explicitly
out of this CMD's scope and untouched.

### A.2 — candidate-set size stats (crowding cost)

| | svo | VARIANT L | VARIANT LI |
|---|---|---|---|
| mean candidate-set size / probe | 71.5 | 175.8 | 244.3 |
| max candidate-set size | 205 | 428 | 582 |
| **reachable** (probe word present in its own candidate set, pre-exclusion — the F-1 tiebreak signal) | 0/10 | **8/10** | **8/10** |

Full per-probe table (`candidate_set_size`/`variant_stats`,
`tools/guala_recall_bitexact_replay.py --candidate-stats`):

| word | svo total | L total | LI total | reachable (L / LI) |
|---|---|---|---|---|
| aap | 8 | 38 | 68 | yes / yes |
| applications | 20 | 50 | 73 | yes / yes |
| beckoning | 0 | 0 | 0 | no / no |
| breed | 56 | 168 | 249 | yes / yes |
| chandelier | 60 | 245 | 365 | yes / yes |
| compelled | 0 | 0 | 0 | no / no |
| cuckoo | 205 | 419 | 561 | yes / yes |
| earth | 202 | 428 | 582 | yes / yes |
| extinguishers | 1 | 5 | 7 | yes / yes |
| folded | 163 | 405 | 538 | yes / yes |

`beckoning`/`compelled` stay unreachable under **every** variant — they
have zero atlas entries in *any* section (see Part D; this is a
persistence-loss story, not a routing one). The other 8 flip from
`reachable=false` under `svo` to `reachable=true` under both L and LI —
direct, measured evidence that F-1's fix works (reachable-but-excluded,
exactly as the CMD's tiebreak rule anticipated).

**LI's only measured difference from L is crowding**: +39% mean
candidate-set size (244.3 vs 175.8) for **zero** additional reachable
words, zero quality difference, zero cold difference.

### A.3 — determinism

Two runs per variant, `diff` exit code 0 on all four:

```
cold_L_run1.txt   == cold_L_run2.txt    (exit 0)
cold_LI_run1.txt  == cold_LI_run2.txt   (exit 0)
taught_L_run1.txt == taught_L_run2.txt  (exit 0)
taught_LI_run1.txt== taught_LI_run2.txt (exit 0)
```

### Pick rule (declared in the CMD, applied verbatim)

"Highest experience-bound quality wins, subject to cold ≥ baseline —
tie → VARIANT L. If BOTH variants leave quality at 0 with bare captions,
tiebreak = probe-word PRESENCE in the final candidate set."

1. Quality: **tied** (0/8 both).
2. Bare-caption zero-tie predicted by F-2 → apply the declared tiebreak:
   reachability. **Also tied** (8/10 both) — the CMD didn't anticipate a
   tie within its own tiebreak.
3. Fall through to the base rule stated at the top of the same sentence:
   **tie → VARIANT L (smaller surface).**

**VARIANT L wins.** Every measured outcome (cold, quality, reachability)
is identical between L and LI; LI's only distinguishing measurement is
more candidate-set crowding for the same benefit — L is the correct
pick under the CMD's own declared rule, not just the cheaper one.

---

## Part B — ship VARIANT L

**Diff** (`003200f`): one default-tuple value in `_recall_response`'s
signature, `("subject","verb","object")` → `("subject","verb","object",
"listen")`, plus its docstring. No other line touched.

**Before/after, identical snapshots** — see A.1's `svo` column (before)
vs `L` column (after); both already run against the same Day-2
snapshots as the CMD requires. Confirmed separately that the two real
production callers (`read_word`'s converse path, both call
`_recall_response` positionally with no `target_sections` argument) now
produce output **byte-identical** to explicit
`target_sections=("subject","verb","object","listen")` across all 10
taught-snapshot probes (spot-checked programmatically, not just by
inspection).

**GL-RECALL-DAILY new dated line** (`8d15cf4`): Day 3, 2026-07-04 —
2/30 cold, 8/10 taught, 0/8 quality, VARIANT L, explicitly labeled
**code-committed / NOT YET DEPLOYED LIVE**, with a Day 3 detail section
explaining the offline-vs-live distinction so it can't be misread as a
live-verified number.

**Emission-path regression check: NOT MEASURED (fix not yet deployed).**
Per the CMD's own Vehicle assignment, Parts B/C "ride the -155 pattern"
— committed and proven offline now, actual deploy is Eve's sleep_for_
deploy call, same as -155/-156 are currently sitting queued. Sending a
live conversational turn right now would only exercise the *unpatched*
running code, so it can't be a meaningful before/after. Instead, I took
one **read-only** `guala_status` sample (does not perturb her) as the
pre-deploy reference point to compare against once the real deploy
happens:

```
tick=14542892  total_emissions=1196
ladder.mean_utterance_len=2.2
ladder.question_rate=0.0  ladder.novel_wordbag_rate=0.007
```

`source_history` (the real per-source commit tally; NOT
`emission_dynamics.source_counts`, which -156 already named as a
recalled-candidate-composition red herring, not a live-call tally) isn't
exposed through the `guala_status` bridge response — that specific
sub-metric is **NOT MEASURED**, cause stated, not guessed at.

**Prohibitions held** (G-159-5): `exclude_words` logic, the count≥2
evidence rule, candidate weighting/scoring, and the coherence rule are
all byte-unchanged — the diff above is the entire behavioral change.

---

## Part C — F-3 index-bypass fix

**Diff** (`16d5c3f`): at all 4 `Section.receive()` callsites inside
`read_word` (listen, the `primary_sections` loop, ground, intro),
capture the `(committed, mode_idx, emit_ready)` return value and call
`self._index_word_at_chi(section_name, mode_idx, chi)` when
`committed=True`. `Section.receive`'s own signature, and the atlas
schema, are untouched — `Section` still can't call `self._atlas_record()`
(no engine reference), so the index update has to happen at the
callsite; this restores -57 §1.2's invariant without changing where or
how `atlas.record()` itself gets called for the primary commit path.

**Before/after proof** (taught snapshot, brand-new word `glorpazoid`
taught via `read_sentence` — the same code path `guala_give_experience`/
`converse` use):

| | atlas entry written | `_word_to_chi_index` (no restart) | recall-cue-resolvable (`candidacy_trace` `taught_present`, no restart) |
|---|---|---|---|
| **Before fix** | yes (confirmed at own chi) | **False** — index size unchanged (904→904) | **False** |
| **After fix** | yes | **True** — index size grows (904→905) | **True** |

Both runs confirm the atlas write itself always happened either way —
only the index (and therefore recall's ability to use it) was affected.
20/20 existing substrate tests pass unchanged (`test_cognition_bundle`,
`test_dynamics_emission`, `test_hemisphere_roundtrip`,
`test_metadata_pipeline`, `test_plasticity_on_commit`,
`test_rich_sensory_wiring`, `test_structured_noise`,
`test_teacher_correction`).

### New finding (NOT fixed here) — a second, broader index bypass

Testing this fix by teaching one word surfaced something the CMD's F-3
doesn't name: `Section.receive`'s **deep-atlas on-attention reinstatement
block** (lines 630-652, GL-BRIEF-032) makes its *own*, separate
`atlas.record()` call — for **other, cohabitant words** sharing the
chi being committed, not the word `read_word()` was called with. This
also bypasses the index, and my fix (which only wraps the RETURN VALUE
for the word actually being taught) does not cover it.

Evidence: teaching `glorpazoid` at chi=38 produced **31 new atlas
entries across ~16 other words** (`lighthouse`, `questions`, `watching`,
`goodnight`, `mcgregor`, ...) at that same chi, none of them indexed —
confirmed via the `dwell_ticks=0` fingerprint, which is unique to the
reinstatement call (every real `read_word` commit uses `dwell_ticks∈
{1,4,8}`, never 0). A from-scratch boot-equivalent rebuild of
`_word_to_chi_index` after this one teaching event diverges from the
live-incrementally-updated index at exactly these 17 words (16 + the
mcgregor case, which reinstated at a neighboring chi too) — everything
else matches exactly.

**Consequence for G-159-3**: "boot-time rebuild still produces an
identical index" is **proven true only for the specific word my fix
targets** — it is **not true in general** after any teaching event that
triggers reinstatement. I did not patch this: F-3 as convicted names
only the primary commit (`:702-704`); the reinstatement call is a
distinct mechanism, and fixing it wasn't asked for and would have been
scope creep beyond "-155 discipline: minimal diff." Filed here for its
own future dispatch, same as -158-v1 filed its own incidental findings
without acting on them.

---

## Part D — the three NOT-IN-SNAPSHOT probes

**D.1.** -158-v1 established the *current-state* half of this (zero or
near-zero atlas entries for `aap`/`beckoning`/`compelled`, verbatim
quoted below for reference). What was missing was the *history* half —
did these ever actually commit? `guala_sections.json`'s per-section
`commits` log (persisted, capped at the trailing 5000 events per
section — `gualaloom_v5_engine.py:6218`) answers this directly:

```
listen commits:  {'tick': 14508213, 'mode': 5317, 'chi': 1,  'word': 'aap'}        (×2)
                 {'tick': 14508344, 'mode': 9194, 'chi': 34, 'word': 'beckoning'}   (×2)
                 {'tick': 14508358, 'mode': 10134,'chi': 35, 'word': 'compelled'}   (×2)
intro commits:   {'tick': 14508213, 'mode': 5086, 'chi': 1,  'word': 'aap'}
                 {'tick': 14508344, 'mode': 9007, 'chi': 34, 'word': 'beckoning'}
                 {'tick': 14508358, 'mode': 9955, 'chi': 35, 'word': 'compelled'}
```

**All three verifiably committed** — into both `listen` and `intro`,
consistent with F-1's routing (standalone caption → listen [+intro if
`fam_listen>0.3`], never subject/verb/object). This rules out
**window-never-committed** for all three: there is no gate that blocked
them; the write happened. It also rules out **save-path loss**: these
exact commit records are the ones the (correctly functioning) save
process persisted into the snapshot being analyzed — the save did its
job faithfully; what's absent is the atlas *entry*, a separate structure
from the commit log.

**Verdict for all three: bound-then-evicted.** -158-v1's own A.1 (this
CMD's starting evidence, unmodified):

> `aap`: "No atlas entry at its own current chi (1) in any section.
> `_word_to_chi_index['aap']={3}` — a stale historical chi, pointing to
> one entry: `listen, motif=5317, strength=0.0217`."
> `beckoning`/`compelled`: "Zero atlas entries anywhere... not in
> `_word_to_chi_index` at all."

`aap`'s surviving chi=3 entry is the **same** motif (5317) the commit
log shows written at chi=1 — not a coincidence: `LivingAtlas.record()`
writes/reinforces every chi within `±CHI_BAND` (=2) of the commit chi
(`gualaloom_v6_living_atlas.py:88-137`), so the single chi=1 commit
band-wrote chi∈{-1,0,1,2,3} simultaneously. Chi=3 sits at the extreme
edge of that band and barely survives (0.0217, ~2 units above the 0.02
forget floor); chi=1 itself (and both of `beckoning`/`compelled`'s whole
5-wide bands) have been fully forgotten.

**Decay math (bound, not a closed derivation — stated plainly per
G-159-4, not guessed at):** elapsed ticks from teaching to this
snapshot's save (`tick=14511920`): aap 3707, beckoning 3576, compelled
3562. `DECAY_LAMBDA=0.0001`/tick (fast channel) or `/SLOW_DIV=12`
(slow channel, `gualaloom_v6_living_atlas.py:42,62`). Pure exponential
decay over this span is `exp(-0.0001×3707)≈0.69` (fast) or
`exp(-0.0001/12×3707)≈0.97` (slow) — i.e. continuous time-decay ALONE
only removes ~30% (fast) or ~3% (slow) of strength in this window.
Back-solving from `aap`'s surviving 0.0217 under the fast channel implies
an initial impulse of only ≈0.031 — plausible for a low-salience new
binding, but if `beckoning`/`compelled` (and `aap`'s own chi=1 center)
started at a similar magnitude and decayed at the *same* rate, they
should have landed near 0.02 too, not at zero. Pure per-tick decay does
not by itself explain **full** eviction across an entire 5-wide band in
this tick count. The better-evidenced accelerant is `record()`'s
**heterosynaptic mass-conservation redistribution** (same file, lines
196-208): every time another word gets reinforced at a shared chi, the
*other* residents there lose strength in proportion, redistributed to
fund the reinforcement. Chi 1/34/35 all show non-empty, active candidate
neighborhoods (Part A.2's per-word tables), consistent with ongoing
reinforcement traffic that would drain a weak, un-reinforced new entry
faster than time-decay alone — but I can't independently replay that
specific chi-bucket's history from the persisted snapshot to prove the
exact trajectory, since commit logs don't retain per-event strength.
Stated as the best-evidenced account, not oversold as closed.

**No escalation**: this is in-substrate forgetting, evidenced as having
happened well before the save (the periodic `forget_below_threshold()`
heartbeat runs every ~200 ticks; ~18 cycles elapsed in this gap), not a
defect in the save path itself.

**D.2** — context note appended to `GL-RECALL-DAILY-20260703.md`'s Day 2
section (entry and numbers above it untouched), verbatim per the CMD:

> 0/8 structurally pinned — routing gap (-158 F-1 primary) + excluded-self
> (-159 F-2 secondary) + bare captions; see -158/-159.

**D.3** — measurement design rule recorded (coherence rule text
unchanged): future experience-bound probe sets must use multi-word
captions (≥3 non-stopword words) via `--captions`, per
`GL-RECALL-DAILY-20260703.md`'s new Day 3 detail section.

---

## Gates

**G-159-1** — PASS. Both variants' full tables filed above, before any
Part B commit (Part A ran and was analyzed before `003200f`).

**G-159-2** — PASS with a caveat. Before/after triple on identical
snapshots: done. Diff proves scope: done (one default-tuple value).
Emission regression: **NOT MEASURED**, cause stated (fix not deployed;
pre-deploy baseline recorded).

**G-159-3** — PASS for the fix's actual scope, **FAIL for the gate as
literally worded**. Live-commit cue-resolution proven before/after for
the word being taught. "Index rebuild determinism preserved" does
**not** hold in general — see Part C's new finding (reinstatement is a
second, unfixed bypass source). Reporting this rather than narrowing
the gate's language to make it pass.

**G-159-4** — PASS. All three verdicts are commit-log-evidenced, not
inferred; no save-path loss found, so no escalation triggered; decay
math given as an honest bound rather than a fabricated precise number.

**G-159-5** — PASS. `exclude_words`, the count≥2 evidence rule,
candidate weighting/scoring, and the coherence rule are all
byte-unchanged. Part B's diff is one default tuple value; Part C's diff
is return-value capture at 4 callsites plus the existing
`_index_word_at_chi` helper (unmodified) — no new mechanism, no new
constants, no role-defaulting anywhere.

---

## Status

Filed and pushed (`8d15cf4`, `origin/guala-live`). VARIANT L and the F-3
fix are real, tested, minimal-diff changes sitting committed and NOT yet
live — same queued state as -155/-156, awaiting Eve's sleep_for_deploy
call (Vehicle assignment is Eve's, not inferable by me from ancestry).
Two things need Eve's ruling, not mine: (1) whether/when to bundle
Parts B/C into the next deploy window, and (2) whether the newly-found
reinstatement index-bypass (Part C) and the heterosynaptic-redistribution
eviction accelerant (Part D) warrant their own dispatches now or later —
both are filed as findings, not fixed, per this CMD's own discipline.
