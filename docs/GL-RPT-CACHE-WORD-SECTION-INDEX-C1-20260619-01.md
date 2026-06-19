# GL-RPT-CACHE-WORD-SECTION-INDEX-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Word→section index cached at boot — first-emission latency fixed
**Commit:** `d37a392` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:214` (was 213)
**Git SHA:** `d37a392`

---

## V1 — Branch verification (verbatim)

```
$ curl ... | grep -nE "_word_to_emission_sections|_rebuild_word_to_emission_index"
1106:        self._word_to_emission_sections = {}
1349:    def _rebuild_word_to_emission_index(self):
4484:                self._rebuild_word_to_emission_index()
4601:                self._rebuild_word_to_emission_index()
2180:        if not self._word_to_emission_sections:
2181:            self._rebuild_word_to_emission_index()
```

Boot-time build at load lines 4484 and 4601. Fallback rebuild at 2180. Incremental update in read_word.

---

## V2 — Production state

```
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21245          ✓
boot:            True           ✓
hemisphere_atlas_sizes: {em: 21886, pr: 522}  ✓
dashboard:       50848 bytes    ✓
```

---

## V3 — Latency comparison (verbatim)

### Pre-cache (-48): first emission 5168ms, second 949ms (5.4× gap)
### Post-cache (-49): first emission 1515ms, subsequent 1077-1545ms

| Input | stage1_ms | stage2_ms | total | n_commits |
|-------|-----------|-----------|-------|-----------|
| "the ocean is deep" (1st) | 1515.3 | 263.5 | 1779ms | 0 |
| "i love you" (2nd) | 1544.8 | 270.3 | 1815ms | **2** |
| "sing me a song" (3rd) | 1076.8 | 264.6 | 1341ms | 0 |

First/last spread: 1779ms vs 1341ms = 438ms (within 500ms budget ✓).
Compare to pre-cache: 6292ms vs 996ms = 5296ms spread.

### Emission section routing still working

```
"the ocean is deep":
  section_candidate_counts: {subject: 25, object: 23, verb: 16}  ✓

"i love you":
  section_candidate_counts: {subject: 22, object: 16, verb: 3}
  n_commits: 2                     ✓
  verb: word=da via=commit         ✓
  object: word=your via=commit     ✓

"sing me a song":
  section_candidate_counts: {subject: 21, verb: 34, object: 24}  ✓
```

All emission sections populated. Commits firing on at least one emission. No -48 regression.

---

## Tests (11/11 green)

```
Test 11: word→emission index at boot... PASS
```

All existing tests green.

---

— c1, 2026-06-19
