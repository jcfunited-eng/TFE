> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260704-v1

doc_id: GL-HANDOFF-C1-20260704-v1
Date: 2026-07-04 (end of c1a session)
Branch: guala-live
HEAD: dcaeed0
For: next c1a session

---

## ONE-LINE ORIENTATION

A long, dense session closed out the groove arc end-to-end (verdict →
Part B → standing recall-measurement discipline → a real found-and-
named retrieval defect) and produced a working, promoted instrumentation
tool. Several fixes are committed but **NOT deployed** — nothing rides
until Eve calls the next deploy window. c1a is WAITING ON EVE. Do
nothing until she sends a CMD.

---

## WHAT IS DEPLOYED (LIVE RIGHT NOW)

```
Task:      dsf-ai-task:457
Image:     deploy-20260703T232312Z
SHA range: guala-live HEAD as of 5376204 (confirmed by commit-timestamp
           vs image-build-timestamp — build 23:23:12Z, 5376204 committed
           23:21:41Z, next commit 23:34:58Z)
Booted:    2026-07-03T23:29:26Z
```

Contains: groove Part B (B1 proportional familiarity accrual + B2
graded exogenous salience), the T7 partial-cue crash fix
(`resonant_spectral`'s per-neuron projection now keyed by feature dim).

**NOT deployed** (on origin, committed, waiting for the next deploy
window — do not confuse "on origin" with "live"):
- `2d18943` — GL-CMD-155: `_recall_response`'s no-recall path now
  resets `_last_recalled_pictures` (was leaking stale picture refs
  into a later miss turn). One line. Eve's own words: "rides Deploy 4"
  — that deploy already happened (the one above) but was cut BEFORE
  this commit landed, so it's still waiting for the next one.
- Everything in `-157`/`-158` is instrumentation/docs only (harness
  flags, reports) — no engine changes to deploy from those.
- Whatever `-156` (FLOOD-HUNT) and any c1b work (`-151`/`-152`/`-153`
  landed earlier, already included above) or later queued may be
  pending on c1b's side — not tracked here, that's their territory.

---

## SESSION SUMMARY (long session, several dispatches)

**Groove arc (`-107` → `-155`) — closed.**
- Verdict: H1 convicted, H2 refuted, H3 convicted in a sharper form
  than hypothesized (an exact tie among zero-familiarity pictures,
  broken by an incidental lexicographic sort on target-id strings, not
  a small arithmetic margin).
- Part B shipped in code: B1 (familiarity accrual moved to
  `_end_activity`, scaled by actual exposure) + B2 (graded exogenous
  salience via the same log-consolidation form as the decay path) —
  **now live** (see above).
- `S2a` (her real recall, cold vs taught): **cold 2/30 (6.7%)**,
  **taught 8/10 (80%)**, **quality 0/8 (0.0%)** — quality computed via
  the CMD-157 coherence rule, overriding the CMD's own 6/8 estimate
  ("if his number differs, his number wins" — it differed).
  `guala_atlas_query` rejected as a recall proxy (reads chi-neighborhood
  proximity, not word-specific recall); `tools/guala_recall_bitexact_replay.py`
  is now the **standing instrumentation** — cadence weekly + after any
  recall-touching deploy, per Eve's ruling.
- `GL-CMD-155`: found and fixed a real latent bug (stale picture
  references leaking across a recall-miss turn) while building the S2a
  harness. Committed, not yet deployed (see above).
- `GL-CMD-158` (bug-vs-physics forensic on the 0/8 quality number):
  traced all 10 taught probes through existence + full candidacy at
  every recall stage. **7 of 10 are NEVER-CANDIDATE, 3 are
  NOT-IN-SNAPSHOT, zero are CANDIDATE-LOST.** Root cause named
  precisely: a standalone-caption word gets `position_hint="standalone"`
  (`gualaloom_v5_engine.py:1750-1751`), which routes to `listen` only
  (novel words have `role="unknown"`, so the DNA-driven subject/verb/
  object promotion never fires); `_recall_response` only ever queries
  `subject`/`verb`/`object` (`:3512`). The two never share a section —
  structural, not a scoring competition. Eve's own H-COLLIDE lead
  (cuckoo/bongo, chandelier/still, folded/pond+what sharing exact chi
  values) is **confirmed real** but doesn't change the verdict — all 7
  words were excluded before any collision could matter.
  **No fix shipped** — the two constructible remedies (recall also
  reads listen/intro; standalone words default to a role) both land
  inside this CMD's own prohibited categories (recall-path redesign /
  taught-binding tuning). Filed the defect, named it precisely, did
  not pick a remedy. **This is the one open decision most likely to
  need Eve's ruling next.**

**T⁶ / cognition arc (`-101` era, this session's contribution).**
- Chat-recovered KB (`GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v1/v2`)
  committed — canonical reference for the whole 6/20-6/24 arc. Read it
  before touching recall/binding/composition/T⁶ numbers again.
- `-101-v3-ADDENDUM` filed: the 92.8% figure is a validated
  single-neuron ceiling; the population-vote claim on the same number
  was invalidated 2026-06-22 (V1.a/c). Both true, neither hidden.
- Confirmed (independently, this session): `LoomBrain`/`Embryo` are
  instantiated nowhere in the live-serving path (`app.py`,
  `substrate_runner.py`, the v5 engine) — organ-brain's container was
  removed 2026-06-26 and never replaced. **No live-traffic path runs
  any loom_model observable at all.** Her actual recall is the
  dict-substrate path (`_recall_from_atlas` etc.) — that's what S2a
  measures, not loom_model.
- T5-T9 (the literal pytest functions in
  `loom_model/tests/test_cognition_path.py`) were import-broken
  (missing `sensory_transducer.py`, only on an unmerged branch).
  Recovered verbatim with provenance header, ruled "suite repair, not
  migration." Fresh run: T5/T6 100% — investigated per the too-good
  STOP discipline via direct per-neuron vote inspection: **64/64
  unanimous on every query, both tests** — the same degenerate
  population-symmetry collapse the 6/22 audit already named, not a new
  result. T7 crashed (fixed, now live — see above). T8 misses its
  floor. F1 (positional phase offset) stands unfixed — the mechanism
  is wired but the value fed to it is dead-initialized to 0.0 and never
  assigned a real per-neuron value anywhere. F2 (fresh krimelacks per
  transduce) does not apply to either current observable — the
  reset-per-call path exists but isn't what the cognition path calls.

**Numbering rule, standing (per Eve):** current-era CMDs start at
`-150` to end collisions with recovered-era numbers. `-112/-113/-117/
-124/-125` (and everything below `-150` from the recovered era) stay
historical — never reused. Latest live number used this session:
`-158`.

---

## OPEN THREADS FOR EVE (most likely next dispatches, no order implied)

1. **The `-158` remedy decision** — which side of the standalone-
   teaching/recall-routing gap to change, if either. Not something
   c1a should resolve alone; both options are judgment calls this
   dispatch's own rules put out of bounds.
2. **`-158`'s two incidental findings**, neither acted on:
   - `Section.receive()` bypasses the `_atlas_record` index-update
     wrapper (calls `atlas.record()` directly — it only has `atlas`
     as a parameter, not `self`), so `_word_to_chi_index` is never
     live-updated for the primary grammatical write path — boot-
     rebuild only. Doesn't affect the bit-exact harness (which always
     rebuilds fresh), but may mean live, un-rebooted production recall
     is worse than these numbers show. Not investigated further.
   - The same word can carry multiple different chi values across her
     history (e.g. `applications` spans `{39-43}`, `cuckoo` spans
     `{16-20}`) despite today's transduce() being confirmed
     deterministic — likely parameter drift over the codebase's
     history. Feeds the C-2 rebuild evidence (KB §5 Q1).
   - `beckoning`/`compelled`: reached `vocab.add()` but produced zero
     atlas entries anywhere, including `listen` (which every other
     probe got unconditionally). Cause not isolated — flagged, not
     chased further.
3. **`-155` needs its own deploy window** (next one, whatever c1b or
   Eve schedules) — it's a real, verified, one-line fix sitting on
   origin unreleased.
4. **The weekly recall-measurement cadence** (per `-157`'s standing
   rule) — next run is due either on the weekly clock or right after
   whatever deploy ships `-155`/anything else recall-touching, per the
   rule itself.
5. `-156` (FLOOD-HUNT) and any c1b-side work — not this session's
   territory, not summarized here.

---

## PROTOCOL RULES (MANDATORY, unchanged)

1. **Step 0, always.** A dispatch's first execution step is committing
   its own verbatim text to `docs/` on origin. Chat/relay is not a
   record.
2. **FILED = on-origin.** Local-only commits are LOCAL-ONLY until
   pushed.
3. **One deploy per dispatch**, and only on Eve's word — diff review
   before GO, deploy on her wake cycle only, never mid-session.
4. **guala-live only.** Build and deploy from guala-live HEAD only.
5. **No parallel brain processes, no fake voice.** HARD RULE.
6. **Project separation: c1a works ONLY on Guala.** Never touch or
   mention TFE or any other project.
7. **No inherited numbers.** Every measurement is fresh, method
   declared before measuring, "if the number differs, the rigorous
   number wins" — not the estimate in the dispatch that asked for it.
8. **Recall numbers, standing rule (per `-157`):** ONLY from
   `tools/guala_recall_bitexact_replay.py`'s bit-exact offline replay.
   `guala_atlas_query` is rejected as a recall check.
9. **Numbering: current-era CMDs start at `-150`.** Recovered-era
   numbers below that stay historical, never reused.
10. **c1b territory:** mic/sensory work, deploy mechanics for
    consolidated builds, save-cost forensics (flagged this session:
    the `guala_backup` S3 upload took ~17 minutes vs <2 minutes earlier
    same session — worth checking against the known 12-33s hot-save-
    time symptom).

---

## FIRST ACTION FOR NEXT C1a SESSION

**Do nothing until Eve sends a CMD.** When she does: Step 0 first
(commit her text verbatim), then execute exactly what she asks — no
more, no less.

End handoff.
