# GL-BRIEF-DEEPATLAS-WC-20260610-031
## Deep Atlas — Two-Layer Memory with Dual Promotion Gate

**Author:** wC | **Date:** 2026-06-10 | **Status:** Stage 1 only — NO PROD DEPLOY
**Sequencing:** Ahead of GL-BRIEF-028 (Response Binding). Response bindings written
into a single decaying atlas erode like everything else; deep atlas changes what
"bound" means for all downstream work.

---

## 1. Problem

Atlas decay observed in production is not a defect. A single atlas is doing two
jobs with opposite requirements:

- **Fast plasticity** — new bindings must form and compete quickly
- **Stability** — established memories (pictures Guala explored, locked motifs,
  strong-band bindings) must persist without re-attention

Dream consolidation (task 65) reinforces what is currently strong — it saves
re-attended structure but cannot save one-shot episodic memories (a picture
explored thoroughly once, never revisited). Those decay below floor and are lost.
This is the hippocampus/cortex division: a fast-learning store must feed a slow,
decay-resistant store.

## 2. wC modeling results (scalar toy — primitive test, NOT capability claim)

Three binding populations modeled: TRUE (re-attended structure), EPISODIC
(one-shot deep exploration, the failure case), NOISE (spurious one-glance
co-occurrence). 4000 ticks, dream every 100, continued new-learning stream.

| Design | TRUE | EPISODIC | NOISE | Deep contamination |
|---|---|---|---|---|
| Single layer (current) | 12/12 | **0/12** | 0/30 | n/a |
| Two-layer, survival gate only | 12/12 | **0/12** | 0/30 | 0% |
| + salience fast-track, 1-dream probation | 12/12 | 12/12 | 0/30 | **23–45%** |
| + 2-dream probation | 12/12 | **3–5/12** | 0/30 | 0% |
| **+ depth-of-encoding gate (final)** | **12/12** | **12/12** | **0/30** | **0%** (even at 100% noise tagging) |

Key findings:
1. Two layers alone do NOT fix it. Survival-based promotion selects for
   re-attention, not significance — episodic memories decay below theta before
   qualifying.
2. Time-based probation cannot separate episodic from salience-tagged junk;
   both decay on the same clock. Hard tradeoff: contamination vs retention.
3. **Depth-of-encoding at write time is the separator.** Explored pictures
   encode ~5x stronger than glanced co-occurrences; that gap is
   time-independent. Gate on encoded strength when the salience tag is
   written, not on survival afterward.
4. Deep priors projected into working caused no dominance (recent new TRUE
   bindings stayed alive in all runs).

## 3. Architecture spec

**Working atlas** (existing chi atlas): unchanged decay, unchanged attention
write path. No behavior change.

**Deep atlas** (new): near-zero decay (~1/25th of working or lower). Write path
= dream cycle ONLY. Never written by live attention. Read path = projects an
additive prior into working-atlas strength when an attended target has a deep
entry (small, capped — see saturation guard precedent: tighter coupling makes
dominance worse; the prior must be a bias, not a force).

**Two promotion paths, both evaluated at dream time:**

- **Path A — semantic (survival):** binding has stayed above theta for S
  consecutive dream cycles → consolidate into deep (deep += working_strength × 0.5).
  Toy values: theta=0.4, S=3.
- **Path B — episodic (depth-of-encoding):** binding was written during a
  high-salience episode (exogenous novelty override fires, task 64 mechanism)
  AND its encoded strength at write time ≥ ENCODE_GATE → promote at next dream.
  One-shot. Toy values: ENCODE_GATE = 0.8 (≈ deep exploration; glanced junk
  encodes ~0.25 and never qualifies). The salience tag must carry the encoded
  strength with it — the gate reads the value at tag time, not current strength.

**Existing primitives reused:** dream cycle (task 65), novelty-override salience
(task 64), attention dwell/strength. No new ML, no templates — substrate-native.

## 4. Open questions (flag, do not solve now)

- **Unbounded deep growth** (~150 entries / 4000 toy ticks). Eventually wants
  within-deep consolidation during dreams (merging overlapping entries into
  schemas). Future brief.
- ENCODE_GATE, DEEP_PRIOR, deep decay constant — toy values. Stage 1 must
  derive substrate-appropriate values from real atlas strength distributions.
- Interaction with persistence schema_v2 — deep atlas needs its own persisted
  table/section.

## 5. Staged plan — c1 instructions

**Stage 1 (this brief): substrate-level offline model. NO PROD CODE CHANGES.**

1. Build an offline harness that imports the REAL atlas code paths (actual
   chi-band binding, actual decay constants, actual dream consolidation from
   task 65, actual novelty-override salience from task 64) — not a
   reimplementation. Run it against persisted substrate state snapshots if
   available (EFS persistence, schema_v2), otherwise synthetic input through
   the real krimelack→atlas path.
2. Reproduce the failure first: show one-shot episodic bindings (e.g. a
   picture attended once with high dwell) decaying to loss under current
   single-layer dynamics. This is the baseline. If the failure does NOT
   reproduce in the real substrate, STOP — file GL-FIND, the toy model's
   premise is wrong.
3. Implement deep atlas + dual gate in the harness only. Measure the same
   four outcomes as the toy: TRUE retention, EPISODIC retention, NOISE
   rejection, deep contamination — plus two things the toy could not see:
   retrieval cost as deep grows, and chi-band/overlap interaction (does a
   deep prior distort band membership or motif overlap values?).
4. Sweep ENCODE_GATE, DEEP_PRIOR, deep decay against real strength
   distributions. Report the operating window, not a single point.
5. **File GL-FIND-DEEPATLAS-C1 with results BEFORE any substrate primitive is
   modified.** Per standing discipline: c1 stops and reports; wC writes the
   fix/deploy brief (will become GL-BRIEF-032 if Stage 1 passes).

**Stage 2 (NOT authorized by this brief): prod deploy.** Only after GL-FIND
review by wC and Joe. Acceptance bar is Joe's browser, as always.

## 6. Failure modes to avoid (standing list applies)

- Pass rate in the harness ≠ capability. Stage 1 success means "design logic
  holds in real substrate code," nothing more.
- No goalpost moves: the target is EPISODIC retention without deep
  contamination AND without dominance. All three, simultaneously.
- If the harness needs a shortcut (synthetic input vs real snapshots), state
  it in the GL-FIND — silent canonical change is the documented destruction
  pattern.

---
*wC toy model source available on request (model.py, 4 progressive runs).*
