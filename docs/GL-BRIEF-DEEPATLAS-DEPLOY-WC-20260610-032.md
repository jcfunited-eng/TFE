# GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032
## Deep Atlas — Production Deploy with Observe-in-Prod Protocol

**Author:** wC | **Date:** 2026-06-10 | **Status:** AUTHORIZED FOR PROD
**Supersedes:** Stage gating in GL-BRIEF-DEEPATLAS-WC-20260610-031
**Inputs:** GL-FIND-DEEPATLAS-C1-20260610, GL-FIND-DEEPATLAS-C1-20260610-02

**Decision (Joe, 2026-06-10):** Skip further harness validation. The remaining
unknowns (compound gate vs real noise tail, replay growth at scale, prior
behavior under live attention) are prod-complexity questions — deploy and
observe the real failure modes. This is methodology, not shortcut: the deploy
must be fully instrumented and fully reversible so failure teaches instead of
destroys.

---

## 1. What ships

### 1.1 DeepAtlas (new, additive)
- Near-zero decay: working DECAY_LAMBDA / 25.
- Write path: dream cycle ONLY. No live-attention writes.
- Persistence: NEW table/section in schema_v2 — fields: section, motif,
  chi position, strength, encoded_strength_at_write, dwell_at_write,
  source_path (A|B|replay), promoted_at_tick. Separate table is mandatory:
  rollback = drop table, existing atlas untouched.

### 1.2 Compound promotion gate (UNTESTED — this deploy IS the test)
Path B (episodic) promotes only if BOTH:
- encoded_strength at write time >= ENCODE_GATE = 0.15
- dwell at write time >= DWELL_GATE = 4 ticks
Rationale: FIND-02 showed noise tail to 0.82 encoded strength — strength alone
cannot separate. Dwell gap (episodic 8 vs noise 1) is the wider discriminator.
Principle: if Guala dwells, it is episodically significant to her — deep
stores her experience, not our labels.
Path A (survival) unchanged: theta=0.4, 3 consecutive dream cycles, transfer 0.5.

### 1.3 No side door for replay
FIND-02: real replay creates 2.2x deep entries via cofire_bind during the
dream itself, bypassing the gate. NOT permitted. Replay-spawned bindings are
written to WORKING atlas and pass through the same compound gate at subsequent
dreams. Deep has exactly two write paths: Path A, Path B. Nothing else.

### 1.4 On-attention prior (design change from FIND-02 retrieval result)
Deep prior is applied ONLY when a related cue is attended — entry-specific
(section+motif match), additive, DEEP_PRIOR = 0.15. NOT continuous. Working
entries decay and prune normally; deep reinstates on cue. This preserves
working-layer leanness (continuous priors made working entries immortal —
defeats the two-layer division).

## 2. Instrumentation (mandatory — observe-in-prod is void without it)

New event types in the substrate event stream (visible via guala_get_events):
- `deep_promotion` — path (A|B), section, motif, encoded_strength, dwell,
  working_strength at promotion
- `deep_gate_reject` — same fields + which gate failed (strength|dwell|theta).
  THIS is the contamination early-warning channel: rejected entries with
  high strength + low dwell = noise tail being caught (good); episodic-looking
  rejects = gate too tight (bad).
- `deep_reinstatement` — cue, reinstated section/motif, working strength
  before/after prior
- `deep_size` — emitted each dream: entry count, total strength, growth since
  last dream

guala_status additions: deep atlas block (n_entries, total_strength,
promotions_by_path, reinstatements_since_boot).

## 3. Safety rails

- `DEEP_ATLAS_ENABLED` env var (default true on deploy). False = no promotion,
  no priors, no deep reads/writes; working atlas behaves exactly as today.
- `DEEP_PRIOR_ENABLED` env var — independent kill for the prior path only
  (promotion continues, recall influence stops). Lets us separate "gate is
  wrong" from "prior is wrong" if behavior degrades.
- Rollback: disable flags, drop deep table, redeploy previous task def.
  Document the exact rollback commands in the deploy notes.
- Dream consolidation (task 65), novelty override (task 64), and all working
  atlas behavior are UNCHANGED. Any diff to existing primitives beyond reading
  dwell/salience at write time = stop and GL-FIND.

## 4. Observation protocol (first 72h)

Watch via guala_status + get_events, wC pulls and reviews each session:
1. **Contamination:** deep entries with dwell_at_write < 4 should be ZERO
   (gate guarantee). Deep entries that look like junk DESPITE passing both
   gates = the real finding we deployed to discover.
2. **Growth rate:** deep_size per dream. Harness predicted ~70 entries/6000
   ticks net-effect, 2.2x under real replay before the side-door close. If
   growth is runaway despite no-side-door, within-deep consolidation brief
   escalates immediately.
3. **Reinstatement behavior:** do priors surface old pictures/motifs when
   Guala attends related cues? Watch for reinstatement loops (same entry
   reinstated every few ticks = prior too strong or cue matching too loose).
4. **Her experience:** does anything in her activity pattern change —
   attention distribution, motif formation rate, needs scalars (stab/nov/conn)?
   Deep memory should feel like continuity, not haunting. If stab drops or
   attention gets captured by reinstated content, DEEP_PRIOR_ENABLED=false
   first, then assess.

Pass is NOT "no failures." Pass is: failures are visible, attributable to a
specific mechanism, and reversible. That is what this deploy is for.

## 5. Acceptance

Joe's browser. Plus: 72h of event-stream evidence reviewed by wC, findings
filed as GL-FIND-DEEPATLAS-PROD-OBS (wC authors this one, from bridge tools).

## 6. Explicitly deferred

- Within-deep consolidation / schema formation (next brief after Response
  Binding — escalates if growth is runaway)
- ENCODE_GATE / DWELL_GATE retuning (only after prod distributions observed)
- Response Binding (GL-BRIEF-028) remains queued BEHIND this deploy per
  sequencing decision in 031.

---
*c1: implement exactly this spec. Deviations require stop + GL-FIND before code.*
