# GL-RPT-ADD-HEMISPHERE-INSTRUMENTATION-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Per-hemisphere atlas sizes in events — pr.atlas=149 confirmed
**Commit:** `54a55b2` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:209` (was 208)
**Image:** `dsf-ai:deploy-20260619T194348Z`
**Git SHA:** `54a55b2`

---

## V1 — Branch verification (verbatim)

```
$ curl -s ".../54a55b2/dsf_ai_service/substrate/hemisphere_cognition.py" \
    | grep -nE "hemisphere_atlas_sizes"
567:                                    hemisphere_atlas_sizes=hemi_sizes)
```

Field constructed in `run_hemisphere_updates` at line 567.

---

## V2 — Production state

```
Task def:          dsf-ai-task:209 (PRIMARY, single deployment, stable)
Image:             dsf-ai:deploy-20260619T194348Z
Git SHA:           54a55b2

schema_version:    v7.1.0                                              ✓
identity:          cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
n_live_bindings:   21539  (pre-deploy ~21612, delta 0.3%)              ✓
boot:              True                                                ✓
integrity:         []                                                  ✓
load_errors:       []                                                  ✓
```

---

## V3 — Behavioral: pr.atlas is non-empty (VERBATIM)

```
=== Sending 'hello' ===
Response: moon how

=== hemisphere_update event detail (verbatim) ===
tick: 11248470
kind: hemisphere_update
detail keys: ['n_events', 'events', 'hemisphere_atlas_sizes']
n_events: 69340
hemisphere_atlas_sizes: {
  "em": 21952,
  "pr": 149
}
sub-event types: {'convergent_event': 20}
```

**pr: 149 bindings.** Direct evidence the prediction hemisphere is accumulating bindings in the running container. em: 21,952 (matches n_live_bindings within autonomous-activity drift — she's attending pictures continuously).

ep, sc, gp are absent from the dict because their `HEMI_*_ENABLED` flags are OFF — those HemisphereCoordinators don't exist in `guala.hemispheres` yet. When flipped on, they will appear in `hemisphere_atlas_sizes`.

---

## Tests (6/6 green)

```
Test 1: pr consensus/divergence... PASS
Test 2: ep turn log... PASS
Test 3: sc semantic weighting... PASS
Test 4: gp goal bias... PASS
Test 5: combined all flags ON... PASS
Test 6: hemisphere_atlas_sizes in event... PASS (sizes: {'em': 90, 'pr': 82, 'ep': 0, 'sc': 90, 'gp': 3})
```

Test 6 verifies: field present, all 5 hemispheres keyed, each value is int ≥ 0, em > 10, pr > 0.

Existing tests: save_hooks 9/9, hemisphere_roundtrip 7/7, plasticity PASS, gamma_persistence 2/2.

---

— c1, 2026-06-19
