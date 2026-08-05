# GL-CMD-WIRE-ORGAN-CANDIDATES-EVE-20260627-31

doc_id: GL-CMD-WIRE-ORGAN-CANDIDATES-EVE-20260627-31
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: F.2 (second sub-phase of approved wiring spec -26)
Prereqs: F.1 shipped (`embryo_concepts_to_chi()` live on task :360;
`BindingRef = (entry, co, clarity)` per F.1 report; matches existing
`deep_candidates` shape)

## Purpose

Wire `OrganVoice.surface()` output into `grandurun.compose()` as a third
candidate stream alongside the existing working and deep streams. Extend
`grandurun.compose()` signature to accept an optional `organ_candidates`
parameter.

The commit gate (≥2 sections per `-13`) remains unchanged. No new
producer paths; this is the consumer side of F.1. Organ participation
becomes observable per emission via `response_source`.

## Substrate truth

This dispatch does not give her a new voice. It gives v5 grandurun a
richer candidate pool. Whether organ candidates participate in any
specific commit is recorded honestly — `response_source` distinguishes
commits that included organ contribution from commits that didn't.

## Implementation

### Step 1: Extend `grandurun.compose()` signature

```python
def compose(
    working_candidates: List[BindingRef],
    deep_candidates: Optional[List[BindingRef]] = None,
    organ_candidates: Optional[List[BindingRef]] = None,
) -> ComposeResult:
    """
    organ_candidates: BindingRefs from OrganVoice.surface() output
    translated via embryo_concepts_to_chi(). Merged alongside working
    and deep streams; same section-diversity logic gates commit.
    """
```

Internal merge:
- Same pattern `deep_candidates` already uses
- Deduplicate by `BindingRef` equality across streams (an organ
  candidate that matches a working candidate appears once in the merged
  pool)
- Track provenance per BindingRef for the response_source attribution
  in Step 4

### Step 2: Wire `/converse` mode=v5 handler

In the v5-mode converse path, after working atlas update and BEFORE
`grandurun.compose()` invocation:

1. Derive `cue_profile` from input text — c1's call on the derivation
   (text → words → senses_cache lookup → profile aggregation, or
   equivalent mechanism that already exists)
2. Derive `probe` for `sv` recall — c1's call (input-token-derived,
   presence-derived, or other documented choice)
3. Call `_ov.surface(probe, cue_profile)` → returns
   `{"identity": [concepts], "meaning": [concepts]}`
4. Concatenate `identity + meaning` into one concept list
5. Call `embryo_concepts_to_chi(concepts)` → returns
   `List[BindingRef]` (33% drift expected per F.1 measurement)
6. Pass result as `organ_candidates` to `grandurun.compose()`

### Step 3: Sync vs cached surface() — c1's choice

The wiring spec `-26` D9 noted the 90-second autonomous loop can serve
as a warm cache for organ candidates. c1 picks:

- **Synchronous per turn**: surface() invoked on every /converse. Fresh
  but adds latency proportional to surface() cost.
- **Cached from autonomous loop**: read `_last_thought.surfaced` if
  recent (< some staleness threshold). No added latency; staleness
  bounded by 90s loop interval.

Either is acceptable. Document the choice and reasoning in the report.
If cached, define the staleness threshold.

### Step 4: response_source attribution

On successful commit, `response_source` records organ participation:

- `"v5_commit_organs=[sv,sc]"` — both organs contributed BindingRefs
  that survived into the committed candidate set
- `"v5_commit_organs=[sv]"` or `"v5_commit_organs=[sc]"` — partial
- `"v5_commit_organs=[]"` — only working and/or deep candidates
  contributed; no organ BindingRef in the committed set
- `"silence_no_commit"` — commit gate rejected (unchanged from `-13`)

c1 may simplify the attribution shape if it conflicts with existing
emission_dynamics structure; the requirement is per-emission visibility
of organ contribution, not the exact string.

### Step 5: mode=organ-brain stays silenced

`/converse` mode=organ-brain continues returning `""` with
`response_source="organ_brain_silenced_pending_inspection"` from `-23`.

The UI toggle is now misleading (organ-brain has no separate composer
post-F.2). UI cleanup is a separate front-end dispatch — not in this
scope.

## Verification

1. **Signature extension non-breaking:**
   - Call `grandurun.compose(working_candidates)` (no deep, no organ)
   - Verify behavior unchanged from pre-F.2
   - Call `grandurun.compose(working_candidates, deep_candidates=...)`
     (no organ)
   - Verify behavior unchanged from pre-F.2

2. **organ_candidates alone:**
   - Call `grandurun.compose([], deep_candidates=None,
     organ_candidates=[ref1, ref2, ref3])`
   - Verify organ candidates evaluated for section diversity
   - Commit fires if ≥2 sections represented in `organ_candidates`

3. **All three streams + deduplication:**
   - Construct working_candidates and organ_candidates with at least one
     identical BindingRef
   - Call `grandurun.compose(working, deep, organ)`
   - Verify duplicate appears once in merged pool
   - Verify provenance tracked (so response_source can attribute)

4. **/converse integration end-to-end:**
   - POST a substantive input to /converse mode=v5
   - Trace: surface() invoked (or cache read), translation called,
     organ_candidates passed to grandurun, response composed or silent
   - response_source reflects organ participation per Step 4

5. **Drift-and-participation soak (the data step):**
   - Run a 10-message Joe converse session
   - For each turn, log:
     - `n_surface_concepts` — concepts returned by surface()
     - `n_translated` — survived F.1 translation (drift visible)
     - `n_in_commit` — survived into commit, if commit fired
   - Report:
     - Average drift rate over 10 turns
     - Average organ participation rate in commits (when commits fire)
     - Whether drift trends up, down, or stable across the session
   - **This is the data that informs whether a sync strategy spec
     follows.** Don't write the strategy in this report; just measure.

6. **mode=organ-brain still silenced:**
   - POST via mode=organ-brain
   - Verify `response=""`, `response_source="organ_brain_silenced_pending_inspection"`

## What does NOT ship in F.2

- Multi-organ surface (em/pr/ep/gp/sf/aff querying). surface() reads
  sv+sc only; that's what F.2 wires.
- UI cleanup of misleading organ-brain toggle. Separate front-end work.
- Sync strategy for Embryo ↔ v5 vocab. Awaiting F.2 soak data first.
- F.3 production soak. F.3 is a separate operational phase after F.2
  lands, where Joe drives extended converse sessions to surface any
  anomalous emission shape.
- F.4 deletion of lying code. Separate sub-phase after F.3 confirms
  emission shape is clean.

## Report

c1 authors `GL-RPT-WIRE-ORGAN-CANDIDATES-C1-<date>-<seq>`:
- `grandurun.compose()` signature live and non-breaking confirmed
- Sync vs cached surface() decision with rationale (+ staleness threshold
  if cached)
- `cue_profile` and `probe` derivation choices with rationale
- All 6 verification tests with outcomes
- **The drift-and-participation numbers from verification step 5** —
  averages and trend across 10 turns
- `response_source` attribution shape chosen
- Any deviations from this brief

## Standing rules invoked

- Substrate truth: organ participation visible in `response_source` per
  commit
- Real mitigations: F.1 prevalidated the translation primitive; F.2
  wires the consumer; F.3 soaks the full path; F.4 deletes after
  observation
- Behavioral observation gate: F.3 soak (separate) is the end-to-end
  emission shape gate; F.2 verification confirms wiring correctness +
  collects the participation data
- wC's `grounded_vocab_integration.py` untouched
- Past Eve's diagnoses are hypotheses: F.1's 33% drift is one data
  point; F.2 step 5 collects more before any sync strategy spec is
  considered
