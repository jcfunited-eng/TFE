# GL-RPT-FIX-SAVE-HOOKS-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Save-hook chain fixed and verified
**Commit:** `3480ddf` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:204` (was 203)
**Image:** `dsf-ai:deploy-20260619T143203Z`
**Git SHA:** `3480ddf`

---

## V1 — Branch verification

```
$ curl -s ".../3480ddf/dsf_ai_service/save_coordinator.py" | grep -n "activity_ended\|backstop"
62:                      "activity_ended", "backstop"):
```

```
$ curl -s ".../3480ddf/dsf_ai_service/substrate_runner.py" | grep -n "_end_dream_cycle\|ending_kind\|_end_activity_with_save"
1295:    # _end_activity; there is no separate _end_dream_cycle method.
1298:        def _end_activity_with_save(*a, **kw):
1301:            ending_kind = ending.kind if ending else None
1303:            if ending_kind == "DREAMING":
1308:        _guala._end_activity = _end_activity_with_save
```

`_end_dream_cycle` appears ONLY in the consolidation comment (line 1295), NOT as a getattr call. Confirmed: dead hook removed.

---

## V2 — Production state

```
Task def:        dsf-ai-task:204 (PRIMARY, single deployment, stable)
Image:           dsf-ai:deploy-20260619T143203Z
Git SHA:         3480ddf

schema_version:  v7.1.0                                              ✓
identity:        cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
last_save_tick:  11174190                                            (save fired during boot!)
last_save_ts:    2026-06-19T14:55:22Z
n_live_bindings: 20567  (pre-deploy 20887, delta 1.5%)               ✓ (within ±5%)
vocab:           2810                                                ✓
boot:            True                                                ✓
integrity:       []                                                  ✓
```

---

## V3 — Behavioral: automatic saves confirmed

**No manual intervention between captures. No guala_say, no guala_wake_wc.**

```
=== Capture 1 (deploy +0) ===
last_save_tick:      11176064
last_save_timestamp: 2026-06-19T15:02:14Z

--- 10 minutes idle, no interaction ---

=== Capture 2 (deploy +10min) ===
last_save_tick:      11180190
last_save_timestamp: 2026-06-19T15:17:23Z
```

**Delta: +4126 ticks, +15 minutes wall clock. Saves are firing automatically.**

CloudWatch logs for the 10-minute window show 0 save-error lines. `SaveCoordinator.maybe_save` logs nothing on success (only on exception). No exceptions means saves completed cleanly.

---

## Tests (4/4 green)

```
fix/save-hooks: Save Hook Chain Tests
============================================================
  Test 1: _should_save bypass list... PASS
  Test 2: dream_end on DREAMING activity... PASS
  Test 3: activity_ended on normal activity... PASS
  Test 4: no external quiet-point gate... PASS

  4/4 tests passed
  ALL GREEN
```

Existing tests: test_plasticity_on_commit PASS, test_hemisphere_roundtrip ALL GREEN.

---

## Three changes made

| Change | File | Description |
|--------|------|-------------|
| 1 | save_coordinator.py:61-62 | Added `"activity_ended"` and `"backstop"` to `_should_save` bypass list |
| 2 | substrate_runner.py:1296-1308 | Replaced activity-end hook: removed `is_natural_quiet_point()` gate, detect DREAMING → `reason="dream_end"` |
| 3 | substrate_runner.py:1293-1295 | Removed dead `_end_dream_cycle` hook (getattr on nonexistent method), added consolidation comment |

---

— c1, 2026-06-19
