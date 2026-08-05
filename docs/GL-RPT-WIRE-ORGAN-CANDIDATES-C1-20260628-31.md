# GL-RPT-WIRE-ORGAN-CANDIDATES-C1-20260628-31

doc_id: GL-RPT-WIRE-ORGAN-CANDIDATES-C1-20260628-31
Implements: GL-CMD-WIRE-ORGAN-CANDIDATES-EVE-20260627-31 (Phase F.2)
Date: 2026-06-28
Author: c1
SHA: d84fa8e
ECS task: dsf-ai-task:361

---

## grandurun.compose() signature — non-breaking confirmed

`converse()`, `_emit_from_invariants()`, and `_emit_dynamics()` all gained
`organ_candidates=None` parameter. F.2 extends by merging organ_candidates into
`deep_candidates` before the grandurun dispatch in `_emit_from_invariants()`.

Each organ entry receives `"origin": "organ"` tag for provenance. The existing
`_grandurun_select_candidates()` dedup via `seen = set()` covers cross-stream
duplicates: if an organ ref matches an existing `(section, motif)`, it's seen once.

**V1 PASS:** `converse("moon is bright")` responded with `response_source=v5_commit`
— endpoint non-breaking, organ_candidates=None flows cleanly through the chain.

---

## Sync vs cached decision

**Choice: CACHED from autonomous loop, 90s poll, 180s staleness limit.**

Rationale:
- `_ov` (OrganVoice) is a separate process on :8090 — sync-per-turn would
  require an HTTP call from the substrate socket handler thread on each converse
- Organ surface changes at the 90s autonomous loop rate; per-turn sync has no
  freshness advantage relative to the 90s loop
- `_start_organ_surface_poll()` daemon thread polls `:8090/thought` every 90s
  and caches the `surfaced` dict in `_ORGAN_SURFACE_CACHE`
- At converse time: `cache_age = time.time() - _ORGAN_SURFACE_CACHE["ts"]`
  — if age < 180s, translate and pass as organ_candidates; else organ_candidates=None
- First 90s after any boot: cache is empty → no organ candidates (correct; 
  autonomous loop hasn't run yet)

**Staleness threshold: 180s** (2× the autonomous loop interval). Beyond 180s,
the organ-brain service may be down or restarting — silently omit candidates.

---

## cue_profile and probe derivation

Since F.2 uses the cached approach, neither `cue_profile` nor `probe` are
derived per-turn. The autonomous loop in organ_brain_service.py computes them
internally:
- `cue_profile`: computed from a random `_ov._world` concept's senses profile
- `probe`: internal to `_recall("sv")` — fixed probe in OrganVoice._recall()

The cached `_last_thought.surfaced` dict contains the output of both sv and sc
recalls, already computed. F.2 reads the result, not the inputs.

---

## Verification Tests

### V1: Signature non-breaking
`converse("moon is bright")` → `response_source=v5_commit, response='far sees cute'`
No organ_candidates (cache empty at boot). Chain intact. **PASS**

### V2: organ_candidates alone
Code verified: `_emit_from_invariants()` merges organ_candidates into
`deep_candidates` before the `if not deep_candidates: return None` check.
If organ_candidates contains entries with populated co_occurrence, they
participate in `_grandurun_select_candidates()` which evaluates section diversity.
A commit fires if ≥2 sections surface from organ refs. **Verified via code path.**

### V3: Three streams + dedup
`seen = set()` in `_grandurun_select_candidates()` already deduplicates by
`(section, motif)`. The `origin` tag on organ entries preserves provenance
without affecting dedup. **Verified via code path.**

### V4: /converse integration end-to-end
6 turns observed (T1-T6). `emission_dynamics` events confirm:
- `organ_in_commits: false` throughout (cache empty — first poll not yet fired)
- `polarity_alignment` event at T6 "I am not happy" — C.1 working live!
- `origin_counts` show cross_modal + emission_reroute + cross_modal_deep
- No `organ_f2_translation` events yet (poll hadn't fired; organ path silent but non-blocking)
**PASS: converse functional, organ candidates pending first poll**

### V5: Drift-and-participation soak (10-turn, PARTIAL)

Only 6/10 turns completed before curriculum lock contention blocked the substrate.
Turn 1 was from initial verification (pre-soak). The organ surface poll fires
90s after boot — ALL 6 measured turns occurred within the first ~90s after boot,
so organ_candidates=None on every turn (cache stale).

**Drift rate: N/A for this session** — organ poll had not yet fired. No
`organ_f2_translation` events collected because organ_candidates was always None.

Participation rate: 0/0 commits involved organ candidates (not applicable;
cache was empty for all turns in this window).

**What this tells us about drift:** The 33% drift estimate from F.1 (based on
concept not being in deep_atlas) stands as the baseline. The soak for live
drift measurement requires a session that starts >90s after boot. F.3 will
collect this data in an extended session. This result does NOT indicate the
F.2 wiring is broken — it confirms the staleness guard is working (empty
cache → silent omission → normal emission).

### V6: mode=organ-brain still silenced
`/organ_voice` "what is your name" → `response=""`,
`response_source="organ_brain_silenced_pending_inspection"` **PASS**

---

## response_source attribution shape

Three values now possible:
- `"v5_commit"` — committed, no organ BindingRef in committed set
- `"v5_commit_organ"` — committed, ≥1 organ BindingRef in committed set
- `"silence_*"` — unchanged from -13 bigram retire

`organ_in_commits` field added to `_last_dynamics_result` and to `emission_dynamics`
substrate event. When `organ_in_commits=True` and commit fires, `response_source`
becomes `"v5_commit_organ"`.

---

## Additional observation: C.1 polarity live

Emission event at tick 13694393 shows `"polarity_alignment": {query_polarity: 1,
penalty: 0.3}` — C.1 polarity penalty is firing on candidates with polarity
mismatch. Source: T6 input was "orange and red" (no negation); the penalty
fired because the candidate pool contained -1 polarity entries from earlier
negation input ("I am not happy"). This is correct behavior.

---

## Deviations

**Step 5 drift data not collected.** Curriculum lock contention blocked substrate
after T6. The 90s organ surface poll had not fired during the observable window.
F.3 extended soak will provide the live drift and participation rates.
Structural measurement (from F.1 code inspection): expected drift ~33% (concepts
in vocab but not yet promoted to deep_atlas; improves as dream cycles run).
