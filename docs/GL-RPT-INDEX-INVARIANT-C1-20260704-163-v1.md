# GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1

doc_id: GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1
From: c1a | To: Eve
Responds to: GL-CMD-INDEX-INVARIANT-COMPLETE-EVE-20260704-163-v1
(Step-0 filed `42eea4c`).

Commits: `5e4e286` (Part A fix) · `e82c0ec` (Part B.2 daily-log note).
Both pushed to `origin/guala-live`.

---

## Failures first

1. **G-163-1's determinism half does NOT hold, even after this fix —
   named, not claimed.** A.1 (reinstatement indexing) is fully proven.
   A.2 (G-159-3 "in general") is **not** identical after this fix: a
   **third**, distinct residual divergence source exists, predating both
   -159 and -163 — see below. I did not patch it; it's outside this
   CMD's scope ("indexing only" via the existing entry point).
2. **B.1's exact strength/channel numbers exist for `aap` only.**
   `beckoning`/`compelled` have zero surviving atlas entries (confirmed
   independently, matching -158/-159) — there is nothing left to read
   `strength`/`dwell_ticks`/`reinforcement_count` off of. Their dwell_ticks
   is stated from the code path (`app.py:2191`, not a persisted field) and
   survival time is an upper bound, not an exact value. Stated as such,
   not filled in with invented precision.

Neither failure is save-path loss.

---

## Part A — closing the second bypass

**Diff** (`5e4e286`): `Section.receive()` gains an optional
`index_callback(section_name, motif_id, chi_value)` parameter; the
deep-atlas reinstatement block (lines ~630-652) calls it right after its
own `atlas.record()`. All 4 `read_word()` callsites pass
`self._index_word_at_chi` — the existing, unmodified -57 §1.2 entry
point, same one -159 Part C already used for the primary-commit path.
The reinstatement's own gating/salience/`PRIOR_CAP` logic is untouched.

### A.1 — reinstatement-created entry cue-resolvable pre-restart

Same proof shape as -159's F-3. Teaching `glorpazoid` (taught snapshot)
triggers reinstatement of cohabitant words at the same chi (known from
-159's investigation) — this run reinstated 29 word/section pairs
(15 distinct words × listen + intro) at chi=38:

| | indexed (no restart) | cue-resolvable (`candidacy_trace` `taught_present`) |
|---|---|---|
| **Before fix** | 0/29 | 0/29 |
| **After fix** | **29/29** | **29/29** |

20/20 existing substrate tests pass unchanged.

### A.2 — G-159-3 re-proven "in general": NOT identical, residual named

Ran a 3-word teaching session (`glorpazoid`, `zorpthistle`, `quombat` —
multiple reinstatement events, not just one) against the taught
snapshot, then compared the live-incrementally-maintained
`_word_to_chi_index` to a from-scratch boot-equivalent rebuild.

**Result: 58 words diverge. NOT identical.**

Full diagnosis, not just the observation:
- In **all 58/58** cases, live is a **strict subset** of fresh — zero
  words where live has a chi fresh doesn't. No anomaly in the
  "wrong direction."
- In **all 58/58** cases, every chi present in fresh but missing from
  live is fully explained by `LivingAtlas.record()`'s
  `±CHI_BAND` (=2) band-write: `record()` writes/reinforces the SAME
  entry across **5** chi positions (`chi_value-2 … chi_value+2`) on
  every call (`gualaloom_v6_living_atlas.py:136-137`), but
  `_index_word_at_chi` (the existing -57 §1.2 helper, **unmodified by
  either -159 or -163**) only ever indexes the **single** `chi_value`
  it's called with. The boot-time rebuild naturally captures all 5
  positions (it scans `atlas.entries` directly); every live-incremental
  call — both the primary-commit path and this CMD's new reinstatement
  path — only adds one.

**This is a third, pre-existing residual divergence source**, distinct
from (and predating) both -159's F-3 and this CMD's reinstatement
finding. It lives in the ORIGINAL -57 §1.2 `_index_word_at_chi`
contract itself, not in either write path this CMD or -159 touched.
Per this CMD's own instruction, I am **not claiming G-159-3 holds in
general** — it doesn't. I did not patch `_index_word_at_chi` itself:
that would mean changing the canonical index helper's own contract
(single-chi → band-aware), a materially different and larger-shaped
fix than "route the reinstatement write through the existing entry
point," and outside A.3's declared scope ("indexing only... the
reinstatement write's own semantics untouched" — this residual isn't
about the reinstatement write's semantics at all).

**Practical impact, stated plainly so this isn't read as scarier than
it is**: `atlas.record()` writes the *identical* entry to all 5 band
positions, so a word only needs **one** surviving indexed chi to remain
reachable via `_recall_from_atlas`/`_recall_sight_from_atlas` — and
every word tested always has at least one (usually the exact center).
This is a gap in the index's *redundant* coverage, not an observed
reachability failure for any word in this session. It would only matter
if a word's *one* remaining indexed chi were itself later evicted while
band-neighbors correctly indexed by the boot path survived — a
compounding, low-probability edge case, not demonstrated here. Filed as
its own future finding for Eve to scope, not fixed under this CMD.

### A.3 — diff proves scope

The full diff (`5e4e286`) touches exactly: one new optional parameter +
docstring on `Section.receive`; one conditional call right after the
reinstatement's existing `atlas.record()`; `index_callback=self.
_index_word_at_chi` added to all 4 callsites. Nothing else — the
reinstatement block's gating (`_reinst_count`, `DF_THRESH`, OOB skip,
`PRIOR_CAP` formula), salience, and dwell_ticks=0 tagging are
byte-unchanged.

---

## Part B — retention baseline (records only, no code)

### B.1 — per-word numbers

Extracted directly from the taught snapshot's persisted fields
(`guala_atlas.json`) where an entry still exists, cross-referenced
against `guala_sections.json`'s commit log (same method -159 Part D
used to prove these three words genuinely committed) and, for the
dwell_ticks assignment, the actual teaching code path
(`app.py:2191`, `_guala.read_sentence(caption, source="joe")` —
confirmed by reading the code, not inferred from behavior).

| Word | Committed (tick, section) | dwell_ticks | Decay channel | Encoded strength at last write | Strength now | Survival |
|---|---|---|---|---|---|---|
| **aap** | 14508213 — listen (×2, create+1 reinforce) & intro (×1) | 8 (source=joe) | **slow** (dwell≥`DWELL_GATE_META`=4, not released) | 0.056658 (listen, post-2nd-write) | **0.021672** (listen, chi=3 band-edge survivor only — chi=1 center AND all of intro's chi=1 band are already gone) | **still alive** ≥3717 ticks and counting, 0.0017 above `FORGETTING_THRESHOLD`=0.02 |
| **beckoning** | 14508344 — listen (×2) & intro (×1) | 8 (source=joe, same code path) | slow (same formula, not independently re-measurable — no surviving entry) | not recoverable (entry gone) | **0 — zero entries anywhere**, whole 5-wide band, both sections | evicted; survived **at most** 3576 ticks (upper bound — no tombstone records the exact eviction tick) |
| **compelled** | 14508358 — listen (×2) & intro (×1) | 8 (source=joe, same code path) | slow (same) | not recoverable | **0 — zero entries anywhere** | evicted; survived **at most** 3562 ticks (upper bound) |

**Decay math for `aap` (the one word with a surviving entry to check
against)**: `DECAY_LAMBDA=0.0001`, `SLOW_DIV=12`, `META_K=2.0`,
`reinforcement_count=1` → predicted `lam_eff = (0.0001/12)/(1+2×1) =
2.778e-6`/tick. Over the observed 3717 ticks (`last_tick 14511930 −
born_tick 14508213`), pure per-tick decay predicts
`0.056658 × exp(-2.778e-6×3717) ≈ 0.05608` — **the entry should still
be at ~0.056, not 0.0217.** The **observed** strength is 61% lower than
the slow-channel formula alone predicts (equivalent to an effective
`lam_eff ≈ 2.586e-4`/tick, ~93× the predicted slow-channel rate).
Per -159's Part D reasoning (cited, not re-derived from scratch here):
the best-evidenced accelerant beyond `atlas.decay()`'s per-tick model is
`LivingAtlas.record()`'s heterosynaptic mass-conservation redistribution
(`gualaloom_v6_living_atlas.py:196-208`) — every time another word gets
reinforced at a shared chi, existing residents there lose strength
proportionally. This is now **quantitatively** consistent (not just
plausible) with `aap`'s actual trajectory. Not re-derived independently
for `beckoning`/`compelled` since no surviving entry exists to check
against — their **survival time is an upper bound**, and their eviction
mechanism is inferred by analogy to `aap`, not independently measured.

**The E4 one-shot retention floor this establishes**: of 10 words taught
via a single `guala_give_experience(caption=<word>)` bundle, **3 (30%)
were fully or mostly evicted within ≤3562-3717 ticks** (well under one
day of activity at her current tick rate) — before any sleep cycle, any
promotion pathway, or any deliberate consolidation had a chance to act
on them. This is the number future retention work needs to beat.

### B.2 — daily-log note (filed)

Appended to `GL-RECALL-DAILY-20260703.md` (`e82c0ec`): future
experience-bound probe sets must record commit strength, decay channel,
and `dwell_ticks` **at teach time**, read directly off the atlas entry —
not reconstructed forensically afterward, which is only possible at all
when an entry happens to survive (as `aap`'s did, barely; `beckoning`/
`compelled`'s didn't).

### B.3 — cross-filed to plan v9 #4 (retention) inputs

**Not editing `GL-PLAN-AE-DEV-3WK-EVE-20260703-v9.md` directly** — its
own §0 rule ("every future version is a FULL document... delta-amendment
pattern BANNED") reserves full-document authorship to Eve; this is
input for her next consolidation, same as -158 cross-filed physics
findings to C-2 without editing the C-2 spec itself.

**Input for Table 1, row #4 ("Retention — memories survive time &
sleep... Ⓒ model-only; deep atlas 4,356/surv 66 unprobed"):** the
one-shot floor above (30% of a 10-word bundle evicted within ≤1 day's
worth of ticks, pre-sleep) is a real, measured number for the "unprobed"
status to update against.

**The open physics question, named — QUESTION, not a fix proposal:**
does a single `guala_give_experience` bundle window bind strongly enough
(dwell_ticks=8, one reinforcement, salience as observed) to actually
**reach** the sleep cycle that promotion/consolidation would evaluate
it at — or does row #4's verdict currently never get the chance to fire,
because one-shot bindings this weak are already gone before the next
sleep window, regardless of what the promotion/consolidation logic
itself would have done with them? This session's numbers (3562-3717
tick survival ceiling, sitting at or already past
`FORGETTING_THRESHOLD`) are consistent with "never reaches sleep" but
don't independently establish her sleep cadence in ticks — that
comparison is Wk3's aged-recall probe to make, per the plan's own
milestone.

---

## Gates

**G-163-1** — PASS for A.1 (proven, before/after, same shape as F-3).
**Honest FAIL for the "determinism verdict"** as literally hoped: not
identical in general — named precisely (band-write vs single-chi
indexing), not claimed away.

**G-163-2** — PASS. Diff is indexing-only (one parameter, one call,
four callsite kwargs); reinstatement semantics unchanged.

**G-163-3** — PASS. B.1 numbers filed per word (exact for `aap`, upper
bounds honestly labeled for `beckoning`/`compelled`); B.3 question filed
verbatim, no fix proposed, no edit to the plan doc itself.

---

## Status

Filed and pushed. Two findings now sit filed-not-fixed for Eve to
sequence: (1) this report's residual index-divergence source
(`_index_word_at_chi`'s single-chi contract vs `atlas.record()`'s
5-position band-write — low practical severity, real nonetheless), and
(2) -159's still-open question of whether the heterosynaptic
redistribution mechanism (now with a quantitative data point behind it)
warrants its own C-2-adjacent dispatch. No decay/threshold/retention
"fixes" were made — eviction stayed her physics, per the CMD.
