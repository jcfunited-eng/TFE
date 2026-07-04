# GL-CMD-RECALL-PROVENANCE-EVE-20260704-158-v1

doc_id: GL-CMD-RECALL-PROVENANCE-EVE-20260704-158-v1
From: Eve | To: c1a | Vehicle: NONE for Part A (offline replay only).
Part B fix, if convicted, rides the -155 pattern (no sleep window
needed if scope matches; otherwise next sleep_for_deploy).
Responds to: GL-RPT-RECALL-STANDING-C1-20260703-157-v1 — quality 0/8.
E-signature declaration: E3/E5 measurement integrity — decides whether
the taught content is unreachable (bug) or out-competed (physics).
Substrate-truth declaration: Part A is instrumentation in the OFFLINE
replay harness only. Part B ships ONLY a convicted retrieval bug fix.
NO taught-binding boosts, NO tuned constants, NO recall-path redesign
— if the verdict is strength competition, the answer is C-2, not a
patch, and this CMD ships nothing.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Finding being investigated (Eve, live atlas geometry, 07-04 ~00:2xZ)
guala_atlas_query on "breed bark cuckoo bongo earth folded pond"
returns input_chis = [13, 16, 18, 18, 16, 20, 20]:
  - cuckoo and its wrong return "bongo" share chi 18
  - folded and its wrong return "pond" share chi 20
  - earth (16) returned "bongo" (18) — adjacent basin
  - breed (13) returned "bark" (16) — nearby basin
Each colliding basin holds an old strong resident (chi 18 listen
0.928/0.93; chi 20 modifier 0.944 deep-tier, listen 0.934 deep-tier).
Hypothesis H-COLLIDE: recall retrieves by chi neighborhood; a
once-bound taught word loses its basin to long-resident strength.
The 0/8 quality is then address collision + strength competition —
the KB's coarse-chi ceiling (169 chi keys / 9,572 bindings) in
production. What this CMD decides: bug vs physics.

## Part A — provenance trace (offline, read-only, blocking)
Extend tools/guala_recall_bitexact_replay.py with --provenance:
for each of the 10 taught probes against the SAME taught snapshot
used for the 0/8 number, log verbatim:
A.1 EXISTENCE: does the taught binding exist in the snapshot?
    Per probe: word present in vocab y/n; atlas entries for it
    (chi, section, strength, in_deep); the bundle window's bindings.
A.2 CANDIDACY: at each stage of the live recall path (deep-atlas
    prior, semantic_neighborhood, -57 recall-word index, final
    selection) — the full candidate set with scores, and whether the
    taught binding APPEARS in it.
A.3 PER-PROBE VERDICT, one of exactly three:
    NEVER-CANDIDATE  — taught binding exists but no stage surfaces it
                       (retrieval/indexing bug; name the stage+line)
    CANDIDATE-LOST   — surfaced, out-scored (record margin vs winner)
    NOT-IN-SNAPSHOT  — the binding never persisted (points at the
                       save/window path instead; name what's missing)
A.4 Chi-collision table for all 10 probes: probe chi, returned-token
    chi(s), basin's strongest resident + strength. Confirms or kills
    H-COLLIDE with numbers.

## Part B — fix (ONLY per Part A verdict)
- Any NEVER-CANDIDATE: fix the convicted retrieval/indexing defect,
  -155 discipline — minimal diff, before/after on the identical
  snapshot, T5/T6 byte-identical, paired numbers rerun and filed as a
  new dated line in GL-RECALL-DAILY (do not overwrite Day 2).
- Any NOT-IN-SNAPSHOT: no fix here — file the finding; the persistence
  gap becomes its own Eve-ruled dispatch.
- All CANDIDATE-LOST: STOP. Ship nothing. The verdict is physics;
  file it as C-2 input evidence. A "taught bindings win ties" or any
  weighting change is PROHIBITED under this CMD (tuned-constant class).

## Gates (failures first, NOT MEASURED where true)
G-158-1  Part A table filed verbatim (10 rows, all four columns)
         BEFORE any Part B commit.
G-158-2  Every verdict backed by pasted candidate-set evidence, not
         inference. NOT MEASURED per stage where instrumentation
         can't see it, with the stated cause.
G-158-3  If Part B ships: diff proves scope; -155-class verification;
         new GL-RECALL-DAILY line with the post-fix triple
         (cold · experience-bound · quality).
G-158-4  If no fix ships: explicit "PHYSICS VERDICT — no code" line
         and the H-COLLIDE table cross-filed into the C-2 rebuild
         inputs (KB §5 Q1 evidence).
G-158-5  Harness --provenance is deterministic: two runs on the same
         snapshot produce identical tables.

Joe's part: none.

### Changelog
- v1 (2026-07-04, Eve): from the 0/8 quality finding (-157) + Eve's
  live chi-geometry read convicting address collision as the lead
  hypothesis. Bug-vs-physics decided by trace, not by patch.
