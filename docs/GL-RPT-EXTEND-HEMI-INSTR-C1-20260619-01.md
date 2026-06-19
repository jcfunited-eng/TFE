# GL-RPT-EXTEND-HEMI-INSTR-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** EP turn_log proven alive — 3 turns, 3 tracked objects
**Commit:** `fad6264` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:217` (was 216)
**Git SHA:** `fad6264`

---

## V1 — Branch (verbatim)

```python
# Lines 553-569 in hemisphere_cognition.py:
hemi_sizes = {}
for hname, coord in guala.hemispheres.items():
    if hasattr(coord, 'turn_log'):
        hemi_sizes[hname] = {
            "turn_log": len(getattr(coord, 'turn_log', [])),
            "tracked_objects": len(getattr(coord, 'tracked_objects', {})),
        }
    elif getattr(coord, 'atlas', None) is not None:
        hemi_sizes[hname] = sum(len(v) for v in coord.atlas.entries.values())
    else:
        hemi_sizes[hname] = sum(len(v) for v in guala.atlas.entries.values())
```

---

## V2 — Production

```
Task def:        dsf-ai-task:217
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21770          ✓
boot:            True           ✓
```

---

## V3 — hemisphere_atlas_sizes (VERBATIM from production)

```json
{
  "em": 22276,
  "pr": 358,
  "ep": {
    "turn_log": 3,
    "tracked_objects": 3
  }
}
```

- **em**: 22,276 (integer, atlas-backed) ✓
- **pr**: 358 (integer, atlas-backed, alive) ✓
- **ep**: `{"turn_log": 3, "tracked_objects": 3}` — **3 turns recorded from 3 inputs, 3 content words tracked** ✓
- sc/gp: absent (flags off) ✓

Dashboard: 50,848 bytes ✓

---

## Tests (12/12 green)

Test 6 updated to handle ep as dict. New test_12 verifies turn_log >= 3 after 3 converses.

---

— c1, 2026-06-19
