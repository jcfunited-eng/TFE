# GL-CMD-RECALL-MEASURE-STANDING-EVE-20260703-157-v1

doc_id: GL-CMD-RECALL-MEASURE-STANDING-EVE-20260703-157-v1
From: Eve | To: c1a | Vehicle: NONE — instrumentation + a filed daily
entry. No sleep window needed.
Responds to: GL-RPT-S2A-TAUGHT-C1-20260703-v1 (COLD 2/30 = 6.7% ·
TAUGHT 8/10 = 80%; harness promoted; latent bug -155 fixed).
E-signature declaration: makes M1 measurable weekly; feeds Wk3 diff.
Substrate-truth declaration: measurement discipline only; the recall
path itself is untouched.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Findings tonight (from -RPT-S2A-TAUGHT)
- Text-only path (~20/s reads for weeks) → 6.7% cold recall.
- Experience-bound path (10 held-out words, bundle windows, one
  moment each) → 80% recall.
- Two of eight "hits" are not semantically coherent — c1a's HIT-vs-
  QUALITY distinction: recall≠retrieval-of-a-usable-memory.
- Bit-exact replay harness (tools/guala_recall_bitexact_replay.py)
  is the standing measurement tool. Proxy (guala_atlas_query) rejected.
- S3 upload latency 17 min (vs <2 min earlier same session) flagged
  to c1b's save-cost forensic — possible match to the 12-33s hot-save
  disease; that piece is c1b's, not this dispatch.

## The standing rule (recorded here so it survives Eves)
The DAILY LEDGER's M1 line uses the paired form:
  cold R_c/N_c · taught R_t/N_t · quality Q_t/R_t
where quality = the fraction of TAUGHT hits whose returned content is
semantically coherent against the probe. Coherence rule (declared
NOW, before it can be tuned): a returned recall counts as coherent
iff at least one of the returned tokens matches the probe word OR its
bundle's caption words, non-stopword-filtered. That rule is EXPLICIT
so future Eves cannot quietly relax it. Weekly + post-any-recall-
touching-deploy, run the harness; file numbers.

## What ships tonight (no deploy)
C-157-1  A SINGLE additional file: docs/GL-RECALL-DAILY-<yyyymmdd>.md
         template with today's Day-2 entry filled: cold 2/30, taught
         8/10, quality 6/8 (per c1a's report; if his number differs,
         his number wins). This becomes the standing weekly log; the
         daily ledger cross-references it.
C-157-2  The harness gains one flag: --quality-report → prints the
         per-probe returned tokens alongside the hit/miss column so
         the coherence judgment is reproducible from CLI, not memory.
C-157-3  A short (≤10 line) provenance note in the harness header
         naming: 6/22 population-collapse audit, cbe8ed2 harness
         deception precedent, Joe's teaching-loop principle (cold
         ~95% + loop closes residue). The harness's own doc anchors
         the culture that produced its verdicts.

## Gates (failures first)
G-157-1  Daily recall record filed on origin; numbers match the S2A
         report; quality rule stated verbatim in it.
G-157-2  --quality-report reproduces the same hits/misses; per-probe
         returned tokens visible.
G-157-3  Diff proves scope: one new record + one flag + one header
         note. No engine changes.

### Changelog
- v1 (2026-07-03, Eve): from S2A results + Joe's June 21 principle.
  The pair (cold, taught) + quality is now Wk3-diff-ready and
  outlasts any single Eve.
