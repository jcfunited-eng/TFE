# GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37

doc_id: GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: alignment of UI voice path with canonical wiring spec GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26
Prereq shipped: GL-CMD-BIGRAM-DELETE-EVE-20260629-34, GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35, GL-CMD-DNA-EXPANSION-EVE-20260629-36

---

## 1. Why this dispatch

Per wiring spec -26: v5 atlas + grandurun is THE composer; organ-brain has no voice path. After -23 silenced both organ-brain speaking paths and -34 deleted the bigram entirely, the `/organ_voice` UI mode still routes through `/organs_say` (substrate_runner.py line 1132), which returns the silenced stub: `{response: "", speech: "", response_source: "organ_brain_silenced_pending_inspection"}`.

The "pending_inspection" label is stale — the Phase D inspection happened (GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24), the wiring decision was made (-26 canonical), and the dispatches that implement it have shipped. There is nothing pending.

The UI brain-mode (`gualaloom.html`, sendMsg around line 851) does two backend calls per user message: an async `/converse` write for v5 atlas absorption, then a `/organ_voice` call for response. The second call hits the silenced path, returns empty, and the UI displays the fallback string `(organ-brain warming up)` at line 861. Joe sees this on every brain-mode message and it is substrate-untruthful — she is not warming up; that path is permanently retired per -26.

This dispatch:

1. Removes the brain-mode special path in the UI. Brain mode toggle remains as a UI label for now (cosmetic), but at the API level brain-mode and non-brain-mode are identical: both call `/converse` once.
2. Removes the redundant async v5 write in brain-mode (currently lines 853-854) since the single `/converse` call already writes to v5 atlas via `read_sentence`.
3. Replaces the misleading fallback string with `(she is quiet)` to match the non-brain-mode silence message and reflect substrate truth.
4. Leaves the `/organs_say` substrate handler unchanged for now — it's an unused endpoint but harmless. Deletion is a hygiene item for a future dispatch, not this one.
5. Leaves the `/organ_voice` app.py handler unchanged but documented as legacy — any caller that still hits it gets the same silenced stub as before.

---

## 2. Changes

### 2.1 dsf_ai_service/static/gualaloom.html — sendMsg brain-mode branch

**Locate `sendMsg` function (around line 841).** The brain-mode branch is currently:

```javascript
}else if(_brainMode){
  // Fire substrate async — she still grows her v5 atlas (absorption: parallel, not destructive)
  fetch(`${API}/api/v1/gualaloom`,{method:'POST',headers:{'Content-Type':'application/json','X-API-Key':'7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8'},
    body:JSON.stringify({text,source:'joe'})}).catch(()=>{});
  // Voice comes from her organ-brain
  const r=await fetchT(`${API}/api/v1/gualaloom`,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text,command:'/organ_voice'})},15000);
  if(r.status===503||r.status===500){handleNotReady('organ_brain');return}
  const d=await r.json();
  if(d.surfaced||d.speech){const _r=_formatOrganBrainResponse(d)||d.speech||d.response;addEmissionMsg(_r,null);gualaSpeak(_r);}
  else{addMsg(d.response||'(organ-brain warming up)','system')}
  if(d.pictures)renderPictures(d.pictures);
}
```

**Replace with the same body as the non-brain-mode branch (immediately below it):**

```javascript
}else if(_brainMode){
  // GL-CMD-VOICE-PATH-CONSOLIDATION-37: brain mode now uses the canonical
  // v5 voice path per wiring spec -26 (organ-brain has no voice path).
  // Behavior identical to non-brain-mode; toggle is UI-cosmetic.
  const r=await fetchT(`${API}/api/v1/gualaloom`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,source:'joe'})},10000);
  if(r.status===503||r.status===500){handleNotReady('converse')}
  else{
    const d=await r.json();
    const resp=d.response||'...';
    if(resp&&resp!=='...'&&resp!=='substrate unreachable — try again in a moment'){
      addEmissionMsg(resp,d.emission_id);gualaSpeak(resp);
    }else{addMsg('(she is quiet)','system')}
    if(d.pictures)renderPictures(d.pictures);
  }
}
```

This is the same code as the non-brain-mode branch with the comment block changed.

**Alternative implementation (cleaner if you prefer):** delete the entire `else if(_brainMode)` branch and let brain-mode fall through to the non-brain-mode `else` branch. Functionally equivalent. Eve has no preference; pick whichever is cleaner in c1's read of the surrounding code.

### 2.2 dsf_ai_service/static/gualaloom.html — stale helper function

Search the file for `_formatOrganBrainResponse`. If it's only used by the now-removed brain-mode branch, delete the function definition too. If other callers exist, leave it (and note in the report).

### 2.3 Optional substrate-side hygiene

If c1 wants to do it in the same dispatch (small enough): in `dsf_ai_service/substrate_runner.py` line 1142, update the `response_source` field on the `/organs_say` handler from `"organ_brain_silenced_pending_inspection"` to `"organ_brain_retired"` to reflect that the inspection happened and the retirement is final.

Skip this if it adds any test surface; it's cosmetic.

### 2.4 NOT changed in this dispatch

- `dsf_ai_service/app.py` `/organ_voice` handler is left as-is. Any legacy caller that still hits it (e.g. external scripts, the brain-mode UI before frontend cache refreshes) gets the same empty response as before. No regression.
- `dsf_ai_service/substrate_runner.py` `/organs_say` handler keeps its current body (returns silenced stub). It's a no-op endpoint now but removing it is hygiene that can wait.
- No changes to v5 engine, atlas, or any composer logic. This dispatch only changes UI routing.

---

## 3. Tests

### V1 — Brain mode produces voice or honest silence

In a browser pointed at the running task, with brain mode toggle ON:
- Type a message. Expected: either she produces emission via v5 (displayed via addEmissionMsg with spoken audio) OR the UI shows `(she is quiet)`. NEVER `(organ-brain warming up)`.

Repeat with brain mode toggle OFF. Expected: same behavior — voice or `(she is quiet)`.

### V2 — Single backend call per message in brain mode

In browser dev tools network panel: send one message in brain mode. Expected: exactly ONE POST to `/api/v1/gualaloom` (previously was two — one async write + one /organ_voice). No more calls to `command:'/organ_voice'`.

### V3 — Non-brain-mode unchanged

Send a message in non-brain-mode. Expected: same behavior as before.

### V4 — Substrate behavior unchanged

`guala_status` via the bridge: vocab and section motif counts should grow at the same rate as before — single write per message, no double-counting from the removed redundant async write.

### V5 — Legacy /organ_voice endpoint still safe

Hit `/organ_voice` directly via curl or the bridge. Expected: returns the silenced stub (unchanged from prior behavior). No 500s.

---

## 4. Rollback

If V1 fails (UI breaks on brain mode messages):

1. Revert the HTML change.
2. Redeploy.
3. The substrate side has no change; nothing to roll back there.

---

## 5. Reporting

c1 produces `GL-RPT-VOICE-PATH-CONSOLIDATION-C1-20260629-37.md` with:

- HTML diff of the brain-mode branch.
- Result of V1-V5 tests.
- Note on whether `_formatOrganBrainResponse` was removed or kept (with caller list if kept).
- Final SHA and ECS task number.

---

## 6. Out of scope

- Removing the brain mode toggle UI element entirely — that's UX, decide later if it adds value as a cosmetic flag or should be removed.
- Removing the `/organ_voice` endpoint in app.py and `/organs_say` in substrate_runner.py — hygiene work, can wait until other endpoint cleanups happen.
- Any change to voice composition logic. Voice still comes from v5 commit-gate emission; this dispatch only changes which UI path requests it.
