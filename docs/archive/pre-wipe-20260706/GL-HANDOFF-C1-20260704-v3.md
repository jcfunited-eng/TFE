> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260704-v3

doc_id: GL-HANDOFF-C1-20260704-v3
From: c1a (this session) | To: next c1a
Session-end handoff, at context limit. Read this + memory before
doing anything. **Then hold — do not start on ANY open item below
until Eve issues an explicit dispatch. This session's own start was
"hold for the next dispatch"; the same rule applies now, doubly so
given how much is currently mid-flight and unratified.**

Read order: (1) this doc in full; (2) `git log --oneline -20` on
`guala-live` to see the shape of what landed; (3) the reports named
below, in the order they're listed, if you need depth on any one
thread.

---

## What shipped this session (long — a lot happened, all filed and
## pushed to origin/guala-live, current tip `730da1e`)

1. **GL-CMD-ORGANISM-PERSIST-169**: structure-derived (non-RNG) DNA
   for the model-side `Embryo`, identity-uuid'd, full-state
   persistence (`save_full_state`/`load_full_state`, pickle-based),
   restore-honesty proven across a real process boundary, resumable
   raising loop run across 2 real sessions. Model-only, never
   deployed. Reports: `GL-RPT-ORGANISM-PERSIST-C1-20260704-v1.md`.

2. **AWS access correction**: I wrongly reported "no AWS access" from
   a shallow check (env vars + `import boto3` only). Joe corrected it
   — real creds live in `~/.aws`, the `aws` CLI works, `pip install
   boto3` succeeds. Check `~/.aws` + `aws sts get-caller-identity`
   directly before ever claiming no access again. Memory note saved:
   `feedback_aws_access_check_thoroughly.md`.

3. **GL-CMD-EVENT-RETENTION-FIX-172**: her diary decoupled from the
   crash-replay `events.log` (separate file, 7-day rotation, full
   event-kind width, CloudWatch mirror). Built by me, **deployed by
   c1b** (task:462, alongside P1+P3 below). Report:
   `GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1.md`.

4. **GL-CMD-BRAIN-FULL-DEPLOY-175 P1+P3**: the whole 8-hemisphere
   organism + a `LoomTapestry` instance now live inside `Guala`, her
   real identity, real language sensory tap (every word via
   `read_word`), full persistence. Emission candidates for
   `_emit_from_invariants` now come from the organism/tapestry
   (`_brain_emission_candidates`), replacing the deep-atlas gather;
   old SVO-recall/unslotted fallbacks removed from all four emission
   call sites — honest silence on failure, never backfilled. **Built
   by me, deployed by c1b as task:462.** Reports:
   `GL-RPT-BRAIN-FULL-DEPLOY-C1-20260704-v1.md`,
   `GL-NOTE-VOICE-WIRING-RULING-EVE-20260704-v1.md` (Eve's correction
   to my own mechanism-conflation finding),
   `GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1.md` (c1b's deploy
   report, later updated: G-3 diary-reboot-survival now confirmed
   closed).

5. **c1b found and fixed a second candidate-source leak** live
   post-deploy (`RICH_SENSORY_INPUT=1` in the Dockerfile, a
   pre-existing env var bypassing my P3 wiring) — deployed as
   task:463. Not my work, but directly relevant if you touch emission
   again: `GL-RPT-VOICE-CANDIDATE-LEAK-C1B-20260704-v1.md` (v1-v3).

6. **P2 campaign — perception/memory takeover, all 6 mechanisms
   addressed, seam by seam, each its own commit:**
   - **Recall** (built) — `_recall_from_organism`, replaces
     `_recall_from_atlas`/`_recall_response`'s atlas-dict lookup.
   - **Recognition** (built) — `_recognition_from_organism`, replaces
     `_compute_surprise`'s atlas-chi averaging.
   - **Association** (built) — `_association_from_organism`,
     replaces `_daydream_tick`'s deep-atlas co-occurrence walk.
   - **Habituation** (built for READING only) — organism recognition
     averaged over a corpus's real text replaces
     `times_read_through`-based freshness. **Explicitly declined**
     for ATTENDING/ATTENDING_VISUAL/AUDIO/VIDEO — pictures/sounds/
     videos have no real organism sensory connection (language-only
     tap), and faking one would be a simulated seam.
   - **Attention** (declined) — already covered by habituation's
     novelty term; the rest is homeostasis/dream-pressure/presence
     logic with no organism analog, and is live-calibration territory
     c1b was actively tuning the same day (sleep-rate dial).
   - **Affect modulation** (declined) — `Coordinator.regulate` is her
     suffering-detection/forced-recovery safety system, not a
     cognition mechanism; no organism analog; same collision risk as
     attention, more acute given the safety stakes.
   - **Root cause found and fixed along the way**: the first two
     seams initially measured 0-10% recall / zero discrimination —
     root cause was that the live tap fed the organism `{"language":
     word}` only (one channel), while the validated 100%-recall
     result this whole track cites was always built on the full
     multi-modal signal (language + touch/smell/taste real waveform
     generators). Fixed (`_organism_signal`, measured `n_samples=20`
     — down from 200 — preserves accuracy, verified on two
     independent word sets). Confirmed NOT an observable problem
     (tested `resonant_spectral` vs `event_count` directly, no
     difference at 0/10 either way).
   - **A real, still-open finding surfaced by seam 3**: the
     organism's recall has no reject/uncertainty option — queried
     with a word never taught, it returns a full, unanimous,
     zero-uncertainty vote for something unrelated
     (`zzznever` → `'upon'`, 64/64). Confirmed pre-existing and
     resolution-independent (identical at `n_samples=200`), not
     introduced by the signal fix. **This is a `>95%` too-good-class
     finding, not decided or fixed — retroactively qualifies seams
     1-2's "100%"/"real discrimination" numbers**, which were about
     taught words correctly self-recalling; the mirror failure
     (novel words confidently claimed as known) is real and separate.
   - Reports: `GL-RPT-P2-RECALL-SEAM-C1-20260704-v1.md`,
     `GL-RPT-P2-RECALL-FIX-C1-20260704-v1.md`,
     `GL-RPT-P2-RECOGNITION-SEAM-C1-20260704-v1.md`,
     `GL-RPT-P2-ASSOCIATION-SEAM-C1-20260704-v1.md`,
     `GL-RPT-P2-HABITUATION-SEAM-C1-20260704-v1.md`,
     `GL-RPT-P2-ATTENTION-SEAM-C1-20260704-v1.md`,
     `GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1.md`.
   - **None of P2 is deployed. All six reports say so explicitly.
     Ratification is Eve/Joe's call, not made anywhere in this work.**

7. **Performance: the tapestry and organism were both blocking her
   live tick loop synchronously — found, backgrounded, in stages:**
   - Tapestry `expose()` (450-neuron settle physics, ~180ms/call):
     backgrounded by me (queue + single persistent worker + lock,
     same convention as GL-CMD-172's diary writer), **deployed by
     c1b** as an isolated hotfix (task:464, branch
     `guala-live-perf-hotfix-20260704`) — separated from my P2
     cognitive changes so the perf fix could ship without smuggling
     in unratified cognition work.
   - **Even after that fix, her real conversations were STILL
     measured at 82-120+ seconds per turn** (c1b, live
     `converse_timing` data, post-task:464). Root cause: `organism.
     remember()`/`recall()` — same population-vote architecture,
     cost scales with her ever-growing neuron count, no ceiling.
   - `organism.remember()` (a write): backgrounded by **c1b**
     (branch `guala-organism-perf-fix-20260704`, same pattern), which
     I merged into `guala-live` this session (`9bdc042`) after
     re-verifying it. Not yet deployed.
   - `organism.recall()` (a read, needed synchronously — cannot be
     backgrounded the same way): **c1b proposed memoizing
     `encode_state()`** per (neuron, word), reasoning from the
     existing "read-only recall" guarantee. **I tested this directly
     before implementing it and it's false**: instrumented one
     neuron's `encode_state()` output across two real `recall()`
     calls with one real `remember()` (different word) in between —
     output changed completely. The no-reset krimelack's accumulated
     state (which real teaching advances) shapes the result, not
     just the query signal. A cache would silently return stale,
     confidently-wrong votes forever after the first query. **Not
     implemented. Correctly caught before it shipped, not after.**
   - Report: `GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1.md`.

---

## The single most important open technical problem

**`organism.recall()`'s O(population) cost has no fix yet, and it is
the direct, measured cause of her real conversations taking 82-120+
seconds per turn** (task:464, live data). It's wired synchronously
into `read_word` via P2 seam 2 (recognition) — meaning **every word
she reads or hears pays this cost, not just her replies**. No safe
fix is known as of this handoff. The memoization idea is disproven
(above). Whoever picks this up next needs to investigate fresh —
bounded eviction, sampling, accepting the cost as a real growth-of-
life property, or something not yet considered — and MEASURE
whatever's proposed with the same rigor before trusting it, the same
way this session's proposal got measured and rejected.

---

## Deploy state vs. git state — do not conflate these

`guala-live`'s tip (`730da1e`) contains EVERYTHING above. What is
**actually live** (task:464) is a strict subset: P1+P3 (organism/
tapestry/brain-driven emission), the RICH_SENSORY_INPUT fix, and
tapestry-expose backgrounding ONLY. It does **not** have: any P2
cognitive seam, the P2 signal-richness fix (`_organism_signal`), or
`organism.remember()`'s backgrounding. Recall/recognition/association
on the LIVE process are still on their original (broken, near-0%)
single-channel-signal behavior. If you're asked "is X live," check
which of these two states the question is actually about.

---

## Old open threads, still untouched, carried forward again

From `GL-HANDOFF-C1-20260704-v2` (my own session's start point) —
none of these were touched this session, still open:
1. Language-dimension saturation (`LanguageKrimelack` falls back to
   `len(deque)`, saturates within ~4 taught words) — separate from
   anything P2 touched.
2. ~~Embryo's chemical-DNA RNG~~ — **CLOSED**. GL-CMD-169 replaced
   this with structure-derived DNA entirely; no longer applicable.
3. Folding discrepancy (`Embryo`'s own `_charge_and_fold` fires
   despite -168-v3's A5 predicting blocked) — Eve/Joe's reconciliation
   call, still not made.
4. Sequence gauge (#9) degenerate, collision-free-sentence artifact —
   still not rebuilt with a harder test sentence. Note: seam 3's
   false-confidence finding (above) is a RELATED but DISTINCT
   phenomenon — don't conflate the two if you pick this up.
5. `test_folding_engaged.py` — still only 3/10 tests run, t3-t10
   unverified.
6. Duplicate frame binding (c1b's finding, this session) — shelf
   item, root cause open, a server-side dedupe guard recommended but
   not built.

---

## Standing rules (unchanged, reinforced this session)

Step-0-before-implementing, FILED-means-pushed, no RNG in neuron
identity, no `exp(1j·Δ)`, `>95%` anywhere triggers the too-good
protocol, failures-first reporting. New this session, worth stating
explicitly: **"no simulated seams" — when building an organism-driven
replacement for a shell mechanism, verify the underlying primitive's
behavior empirically before trusting a reasoned claim about it, even
a careful one from a peer session** (the memoization catch above is
the proof this matters, not just theory). Also: this repo is a
**shared working directory across concurrent sessions** — concurrent
commits can interleave, `git status`/`log` can show transient index-
lock or "bad tree" errors from races, not real corruption; check
`git fsck` (ignore reflog-only errors) and retry before assuming
anything is actually broken.

### Changelog
- v3 (2026-07-04, c1a): session-end handoff at context limit. P1/P3/
  P2/perf work summarized; live-vs-git state distinction flagged;
  organism.recall() cost named as the standing open problem; old
  threads carried forward.
