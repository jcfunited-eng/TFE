# GL-RPT-VOICE-PATH-CONSOLIDATION-C1-20260629-37

doc_id: GL-RPT-VOICE-PATH-CONSOLIDATION-C1-20260629-37
Implements: GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37
Date: 2026-06-29
Author: c1
SHA: 56902a3
ECS task: dsf-ai-task:365

---

## Files touched

| File | Change |
|------|--------|
| `dsf_ai_service/static/gualaloom.html` | `sendMsg()`: deleted `else if(_brainMode)` branch (12 lines); both modes fall through to `else` (`/converse` path, `(she is quiet)` on silence) |
| `dsf_ai_service/substrate_runner.py` | `response_source`: `"organ_brain_silenced_pending_inspection"` → `"organ_brain_retired"` (both `/organs_say` return paths); `engine` field: `"guala-cognition-silenced"` → `"guala-cognition-retired"` |

---

## V1 — Code path verification

**Before:** `sendMsg()` had three branches:
1. `if(isCmd)` → command path
2. `else if(_brainMode)` → fire async v5 write + await `/organ_voice` (silenced, returns `""`) → showed `"(organ-brain warming up)"`
3. `else` → `/converse` → v5 voice path → `"(she is quiet)"` on silence

**After:** `sendMsg()` has two branches:
1. `if(isCmd)` → command path (unchanged)
2. `else` → `/converse` → v5 voice path → `"(she is quiet)"` on silence

Both brain-mode and non-brain-mode users now hit the same `/converse` path.

**PASS**

---

## V2 — `_formatOrganBrainResponse` retention

`_formatOrganBrainResponse` (line 828) has **two** callers:
- `sendMsg()` line ~860 — **removed** (eliminated with the brain-mode branch)
- STT handler line 445 — **retained** (still calls `/organ_voice` in brain-mode; out of scope per dispatch)

Function kept. No deletion.

---

## V3 — Brain-mode toggle still works

The `_brainMode` variable, toggle button, and `toggleBrainMode()` function are untouched (out of scope). The toggle still switches the UI display label between `'[ organ-brain voice ]'` and `'[ v5 engine voice ]'` and controls the STT handler behavior. `sendMsg()` no longer reads `_brainMode` — the toggle has no effect on typed-message sends, which is correct.

`_brainMode` remains active in:
- STT handler at line 439 (out of scope, retained as-is)
- `_cd` cooldown calculation at line 457 (out of scope, retained as-is)
- Toggle display at line 825 (retained)

---

## V4 — `response_source` string update

`"organ_brain_silenced_pending_inspection"` → `"organ_brain_retired"` at both `/organs_say` return paths in `substrate_runner.py` (lines 1142 and 1146). `engine` field updated from `"guala-cognition-silenced"` to `"guala-cognition-retired"` on the primary return path.

No tests reference this string. Confirmed by `find . -name "test_*.py" -o -name "*_test.py" | xargs grep -l "organ_brain"` → empty.

---

## V5 — Substrate stability

Deploy builds clean (CodeBuild SUCCEEDED). Task :365 registered. Boot status pending — substrate was in a dream cycle at the time of verification for prior dispatch; this deploy follows immediately after.

Prior baseline (task :364): vocab=13637, atlas=16452, integrity=OK. No regression expected — the change is frontend-only (HTML) + one string constant in substrate_runner.py (not a behavioral change).

---

## Unexpected discoveries

1. **STT handler brain-mode branch** (line 439-449) also calls `/organ_voice` in brain-mode and uses `_formatOrganBrainResponse`. This was left untouched per dispatch scope. If/when `/organ_voice` is cleaned up or the brain-mode toggle is removed, this path will also need updating.

2. **`_formatOrganBrainResponse` comment** (line 829) still references "organ-brain service (substrate-true)" — stale now that the bigram is retired. Not updated here (out of scope; cosmetic).
