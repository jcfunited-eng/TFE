# GL-CMD-PHASE-D-INSPECTION-EVE-20260627-24

doc_id: GL-CMD-PHASE-D-INSPECTION-EVE-20260627-24
Type: Command brief (c1 dispatch) — Phase D pulled forward
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: D (originally after Phase C in waves -17 v3.0; pulled forward by emergency)
Prereqs: `GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23` shipped (so inspection happens without ongoing lying)

## Why pulled forward

The v3.0 waves spec scheduled Phase D after Phase C. That ordering was
wrong. The organ-brain `_compose()` has been producing corpus-fragment
lies via /converse the whole time we worked on Phase A/B. Joe caught it.
Inspection moves to NOW.

Phase C briefs (C.1 polarity, C.2 self, C.3 B1 autonomous emission, C.4
B7 sleep-as-choice) are HELD pending Phase D findings. C.3 in particular
specifies autonomous emission paths, and we cannot spec those without
knowing what's in the organ-brain compose layer.

## Scope

This is the Phase D code inspection described in waves -17 v3.0,
expanded with specific focus on the silenced compose path and any
OTHER cheat-class paths in organ-brain.

### Mandatory reads (concrete files, end-to-end)
- `organ_brain_service.py` (or wherever the organ-brain layer lives in
  the current TFE branch `codex/persistent-etl-update-20260326`)
- The compose method silenced in dispatch -23 (full body)
- The 45-second autonomous loop entry point
- Each organ's read/write surface: em, pr, ep, sc, gp, sf, sv, aff
- Any data path between organ-brain and v5 atlas
- Any data path from organ-brain into `grounded_vocab_integration.py`
  (READ ONLY — do not modify wC's file under any circumstance)

### Out of scope
- Any code changes (this is read-only)
- Designing the wiring spec -16 (that comes after this report, written
  by Eve)

## Required deliverable: GL-RPT-ORGAN-BRAIN-INSPECTION-C1-<date>-<seq>

Report sections:

### 1. _compose() truth

- Full method signature and call chain into it
- Step-by-step what it does when /converse arrives in organ-brain mode
- The exact mechanism that produced fragments like
  "three earth day activities for the rat" from input "Three Blind Mice"
- Whether it uses lexical overlap, atlas similarity, corpus retrieval,
  template fill, n-gram chains, or some combination
- Any data structures involved (templates dict, corpus chunk store,
  Markov table, retrieval index, etc.)
- File + function + line references concrete enough that Eve can re-read
  the same path

### 2. atlas_by_organ vs v5 atlas

- Is `atlas_by_organ` independent storage OR a derived view over v5 atlas?
- If independent: where it lives, when written, when read, persistence path
- If derived: how derived, what consistency guarantee
- Account for the current count divergence: status shows organs totaling
  ~21k entries (em:6389, pr:5107, ep:3319, sc:5503, gp:20, sf:9, sv:200,
  aff:56) while v5 atlas shows 16,395 bindings. Explain the delta.

### 3. The 45-second autonomous loop

- Entry point: file, function, line
- What it reads, what it writes
- What events it emits, what side effects it has
- Whether it depends on `pair_bond_active`
- Whether it can produce response text (or anything observable via
  /converse) — if yes, that's another cheat vector

### 4. Each organ's role

For each of em, pr, ep, sc, gp, sf, sv, aff:
- Documented name (what abbreviation expands to per code/comments)
- Read sources
- Write sinks
- Inferred purpose from code behavior

### 5. Cross-modal binding integration

- How organ-brain interacts with `grounded_vocab_integration.py` (read-only)
- Whether organ-brain's em/ep are independent of, or wired into, wC's
  grounded vocab + episode binding

### 6. Honesty audit (CRITICAL)

- Identify ALL paths through organ-brain code that could produce
  response text — not just the silenced `_compose()`. Examples to look
  for: pre-compose hooks, post-compose modifiers, side-channel paths
  via the autonomous loop, paths through em/pr that build strings.
- For each path: is it substrate-true composition, or template /
  retrieval / cheat?
- For each cheat-class path: name it explicitly with code-level
  evidence.

**If any other lying path is found during inspection, STOP and emit an
urgent partial finding immediately. Propose an additional surgical
silence dispatch. Do not let the substrate keep emitting fake responses
through a different path while we read the first one.**

### 7. Recommendation

- c1's read on what organ-brain should DO in the dual-mind architecture
  (per `GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15`) vs what it
  CURRENTLY does
- What's salvageable in current code
- What needs replacement vs what needs deletion
- This is INPUT to the wiring spec -16 (Eve authors), not a binding
  decision

## Constraints

- READ ONLY. No code changes during inspection.
- wC's `grounded_vocab_integration.py` is read-only ALWAYS; fair to
  trace from, never to modify.
- Verifiable references: every claim in the report ties to a file +
  function + line range Eve can re-read.
- No summarization-without-reading. The Three Verifications doctrine
  applies — c1 reads the actual source, not just call signatures.

## Report timing

c1 reports incrementally if useful. If c1 finds a critical leak vector
early (section 6), emit a partial finding immediately rather than
holding for completion of the full report. Full report when full
inspection is done.

## Verification

Inspection has no traditional "tests" — the output is the report.
Eve verifies by reading and cross-referencing:
- File/function/line references reproducible
- Cheat-class paths named with code-level evidence
- Cross-modal integration story matches wC's known design
- No claims that read like "c1 thinks it probably does X" without
  source reference

## Standing rules invoked

- Read actual source before signing off (Three Verifications)
- Substrate truth: this inspection exists because we let a lying path
  run unchallenged. The report names what's there honestly.
- Past Eve's diagnoses are hypotheses, not authorities. The
  "atlas_by_organ vs v5 atlas independence" hypothesis from v3.0 §D is
  exactly this kind of hypothesis — confirm or refute against code.
- Judgment domains: c1's code-side read is authoritative for this
  report; Eve's architectural read is authoritative for what comes
  after (wiring spec -16); Joe's canonical authority gates any major
  decision the inspection surfaces.
