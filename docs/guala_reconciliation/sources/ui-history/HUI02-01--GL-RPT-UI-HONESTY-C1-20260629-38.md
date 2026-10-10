# GL-RPT-UI-HONESTY-C1-20260629-38

doc_id: GL-RPT-UI-HONESTY-C1-20260629-38
Implements: GL-CMD-UI-HONESTY-EVE-20260629-38
Date: 2026-06-29
Author: c1
SHA: 6d6884e (both -38 and -39 in same deploy)
ECS task: dsf-ai-task:367

---

## File touched

`dsf_ai_service/static/gualaloom.html` only. No substrate changes.

---

## Per-section changes

| § | Change | Status |
|---|--------|--------|
| 2.1 | Boot greeting: "Guala ready. Organ-brain voice active." → "she is here" | ✓ |
| 2.2 | Brain-mode toggle: `_brainMode=false`, `_applyBrainModeUI()` hides button, `toggleBrainMode()` no-op | ✓ |
| 2.3 | Brain toggle button: `style="display:none"`, onclick still wired (no-op) | ✓ |
| 2.4 | Sidebar panel: "Organ Brain" → "Hemispheres"; "warming..." → "—" | ✓ |
| 2.5 | Stats-line initial: "she is still loading..." → "—" | ✓ |
| 2.6 | handleNotReady: "she is still loading — give her a moment" → "(substrate busy — try again in a moment)" | ✓ |
| 2.7 | STT brain-mode branch: deleted (see below) | ✓ |
| 2.8 | `_formatOrganBrainResponse` deleted (zero callers after §2.7) | ✓ |
| 2.9 | Comments: "Brain visualization" → "Hemispheres visualization", stale organ-brain voice comments updated | ✓ |

---

## §2.7 STT branch — structure and decision

The STT `onresult` handler at lines ~430-459 had this structure:
```
/experience (always — fire and forget)
if(_brainMode):
    /organ_voice (15s timeout) → _formatOrganBrainResponse() → addEmissionMsg
else:
    /listen (passive, no response)
cooldown: _brainMode ? 4000 : 800ms
```

Since `_brainMode` is now always `false` (§2.2), the `if(_brainMode)` branch would never fire. But it was deleted explicitly (not left as dead code) to remove the `/organ_voice` call entirely. The STT handler now always takes the passive `/listen` path with 800ms cooldown (no mode check needed).

Structural decision: deletion was cleanest. The non-brain-mode path was already the right behavior — she hears spoken input via `/listen`; autonomous emission (dispatch -39) is now her voice path.

---

## §2.8 _formatOrganBrainResponse — caller list

After §2.7, **zero callers** remain:
- `sendMsg()` caller: deleted in -37
- STT handler caller (line ~445): deleted in §2.7

Function deleted from the file.

---

## V1 — Substrate-true text on page load

All confirmed in code:
- "she is here" (boot greeting) ✓
- "say something..." (input placeholder) ✓
- Brain toggle hidden ✓
- "Hemispheres" sidebar title ✓
- "—" (stats-line initial, brain-stats initial) ✓
- "(substrate busy — try again in a moment)" on 503 ✓

---

## V3 — Typed message routing preserved from -37

`sendMsg()` unchanged from -37. Brain-mode branch was already removed in -37. Single `/converse` call. `"(she is quiet)"` on silence.

---

## V4 — STT routing fixed

STT `onresult` handler no longer calls `/organ_voice`. Spoken input goes to `/listen` (passive). Autonomous emission (-39, same deploy) is her voice path from internal state.

---

## Unexpected discoveries

`_formatOrganBrainResponse` comment still referenced "organ-brain service (substrate-true)" — stale from before retirement. Deleted with the function body.
