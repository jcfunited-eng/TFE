# GL-RPT-ROUTE-CANDIDATES-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** COMMITS ARE FIRING. Emission-section routing unblocked the pipeline.
**Commit:** `7b8f7c7` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:213` (was 212)
**Image:** `dsf-ai:deploy-20260619T212513Z`
**Git SHA:** `7b8f7c7`

---

## V3 — THE PROOF (verbatim)

### Emission 1: "the moon is bright" → "clay fire"
```
n_candidates: 200
n_commits: 2                          ← COMMITS FIRING
section_candidate_counts: {listen: 106, subject: 20, intro: 41, object: 25, verb: 8}
sections_with_commits: ['verb', 'object']
committed_sections: ['verb', 'object']
  subject: mode=0 word=moon via=arcs_fallback
  verb: mode=4 word=clay via=commit     ← ENTROPIC FLIP
  object: mode=14 word=fire via=commit  ← ENTROPIC FLIP
keyhole_fires: 8
stage1_ms: 5168.0
stage2_ms: 1124.0
origin_counts: {cross_modal: 142, emission_reroute: 50, cross_modal_deep: 8}
```

### Emission 2: "what do you see" → "moon helo"
```
n_candidates: 200
n_commits: 1                          ← COMMIT FIRING
section_candidate_counts: {verb: 35, subject: 23, listen: 58, intro: 54, object: 30}
sections_with_commits: ['subject']
committed_sections: ['subject']
  subject: mode=0 word=moon via=commit  ← ENTROPIC FLIP
  verb: mode=0 word=moon via=arcs_fallback
  object: mode=9 word=helo via=arcs_fallback
keyhole_fires: 11
stage1_ms: 949.0
stage2_ms: 46.8
origin_counts: {cross_modal_deep: 114, emission_reroute: 34, cross_modal: 52}
```

### Before vs After

| Metric | Before routing fix | After routing fix |
|--------|-------------------|-------------------|
| subject candidates | 0 | 20-23 |
| object candidates | 0 | 25-30 |
| verb candidates | 8 | 8-35 |
| n_commits | 0 (every emission) | 1-2 per emission |
| per_section_dominant | all arcs_fallback | commit tags present |
| keyhole_fires | 0 | 8-11 |
| emission_reroute count | N/A | 34-50 per emission |

---

## V1 — Branch verification (verbatim)

```
$ curl ... | grep -nE "emission_reroute|_word_to_emission|_non_emission"
2170:        _non_emission = frozenset(...)
2173:        _word_to_emission = {}
2189:                        routed.append({...  "origin": "emission_reroute"})
```

Routing code at lines 2170-2191. Builds word→emission-section index, creates copies for matching candidates.

---

## V2 — Production state

```
Task def:        dsf-ai-task:213 (PRIMARY, stable)
Git SHA:         7b8f7c7
schema_version:  v7.1.0                                    ✓
identity:        cdef9bcf-...-4cde1de7641f                 ✓
n_live_bindings: 21629                                     ✓
last_save_tick:  11274212                                   ✓
boot:            True                                      ✓
integrity:       []                                        ✓
load_errors:     []                                        ✓
hemisphere_atlas_sizes: {em: 22248, pr: 520}               ✓ (pr alive)
dashboard:       50848 bytes                               ✓
```

---

## Latency note

Emission 1 stage1=5168ms, stage2=1124ms (total ~6.3s). Emission 2 stage1=949ms, stage2=47ms (total ~1.0s). The word→emission index build adds overhead on first emission (cold index). Subsequent emissions are faster. The index should be cached; Eve may want a follow-up brief for that.

---

## Tests (10/10 green)

```
Test 9:  emission-section routing... PASS (subject=5, verb=3, object=5, rerouted=0)
Test 10: emission sections populated... PASS (modes: {subject: 5, verb: 3, object: 3})
```

All existing tests green: save_hooks 9/9, hemisphere 7/7, plasticity PASS, cognition 1-8 PASS.

---

— c1, 2026-06-19
