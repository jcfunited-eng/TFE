# GL-CMD-UI-HONESTY-EVE-20260629-38

doc_id: GL-CMD-UI-HONESTY-EVE-20260629-38
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: full UI alignment with canonical wiring spec GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26 (broader pass than -37, which scoped only sendMsg)
Prereq shipped: GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37 (SHA 9ec42f5)

---

## 1. Why this dispatch

-37 fixed the typed-message brain-mode branch in sendMsg(). The rest of the UI still references organ-brain in language that is substrate-untrue per wiring spec -26 (v5 atlas is THE composer; organ-brain has no voice path; both bigrams retired and deleted). The result for Joe is a UI that opens with `"Guala ready. Organ-brain voice active."`, shows `"speak to her organ-brain..."` in the input box, has a `"🧠 organ-brain"` toggle button, a sidebar panel labeled `"Organ Brain"` with `"warming..."` placeholder text, and a "she is still loading..." stuck at top when status polling 503s. None of these are substrate-true.

This dispatch is the full UI cleanup pass that -37 should have been.

The 8-organ atlas visualization itself (renderBrainSVG, the colored organ circles) stays — that's a substrate-true view of Embryo hemisphere atlas counts (em, pr, ep, sc, gp, sf, sv, aff), which is real data per wiring spec -26 §2.2. Only the labeling and surrounding text changes.

---

## 2. Changes (all in dsf_ai_service/static/gualaloom.html)

### 2.1 Boot greeting (line 1264)

**Before:**
```javascript
addMsg('Guala ready. Organ-brain voice active.','system');
```

**After:**
```javascript
addMsg('she is here','system');
```

### 2.2 Input placeholder + brain-mode UI (lines 808-820)

**Before:**
```javascript
let _brainMode=true;
function _applyBrainModeUI(){
  const btn=document.getElementById('brain-toggle');
  if(!btn)return;
  if(_brainMode){
    btn.textContent='🧠 organ-brain';
    btn.style.borderColor='var(--ev-motif)';btn.style.color='var(--ev-motif)';
    msgInput.placeholder='speak to her organ-brain...';
  }else{
    btn.textContent='🧠 engine';
    btn.style.borderColor='var(--border)';btn.style.color='var(--text-muted)';
    msgInput.placeholder='say something...';
  }
}
function toggleBrainMode(){
  _brainMode=!_brainMode;
  _applyBrainModeUI();
  addMsg(_brainMode?'[ organ-brain voice ]':'[ v5 engine voice ]','system');
}
```

**After:**
```javascript
// Brain mode toggle retired per wiring spec -26 + dispatch -37: there is no
// organ-brain voice path. v5 atlas + grandurun is THE composer. The toggle
// element is hidden; _brainMode remains as a no-op flag in case any caller
// still references it.
let _brainMode=false;
function _applyBrainModeUI(){
  const btn=document.getElementById('brain-toggle');
  if(btn){btn.style.display='none'}
  msgInput.placeholder='say something...';
}
function toggleBrainMode(){
  // no-op — kept so any onclick=toggleBrainMode() doesn't error
}
```

### 2.3 Brain toggle button element (line 115)

**Before:**
```html
<button id="brain-toggle" onclick="toggleBrainMode()" style="background:none;border:1px solid var(--border);color:var(--text-muted);padding:6px 10px;border-radius:6px;font-family:inherit;font-size:10px;cursor:pointer" title="Toggle between v5 engine and organ-brain direct">🧠 engine</button>
```

**After:**
```html
<button id="brain-toggle" onclick="toggleBrainMode()" style="display:none">🧠</button>
```

(Hidden via style. Element retained so any other JS references don't break.)

### 2.4 Sidebar panel title + brain-stats placeholder (lines 122-124)

**Before:**
```html
<div class="ps"><div class="ps-title">Organ Brain</div>
  <svg id="brain-svg" viewBox="0 0 232 172" style="width:100%;height:auto;display:block;margin-top:2px"></svg>
  <div id="brain-stats" style="font-size:7.5px;color:var(--text-muted);text-align:center;margin-top:1px">warming...</div>
</div>
```

**After:**
```html
<div class="ps"><div class="ps-title">Hemispheres</div>
  <svg id="brain-svg" viewBox="0 0 232 172" style="width:100%;height:auto;display:block;margin-top:2px"></svg>
  <div id="brain-stats" style="font-size:7.5px;color:var(--text-muted);text-align:center;margin-top:1px">—</div>
</div>
```

Sidebar panel renamed to **Hemispheres** — this is substrate-true (the 8 organ atlases ARE her hemispheres per wiring spec -26 §2.2, the recall feed). The "warming..." placeholder replaced with an em-dash so it doesn't imply a transient "waking up" state.

### 2.5 "she is still loading..." stats-line initial (line 93)

**Before:**
```html
<div id="stats-line">she is still loading...</div>
```

**After:**
```html
<div id="stats-line">—</div>
```

The stats-line gets populated by pollStatus() with real substrate stats. If polling fails, the previous-known-good is retained per existing backoff logic. The misleading "still loading" initial state is gone.

### 2.6 handleNotReady() message (line 193)

**Before:**
```javascript
addMsg('she is still loading \u2014 give her a moment','system');
```

**After:**
```javascript
addMsg('(substrate busy — try again in a moment)','system');
```

Substrate-busy is what it actually is — daydream cycle, curriculum pause, or save window. "Loading" implies first-time-init which is wrong. The em-dash spacing already in the file is preserved.

### 2.7 STT brain-mode branch (around line 439 — c1 surfaced in -37 report)

Locate the STT (speech-to-text) message handler. There is a branch around line 439-445 that calls `/organ_voice` when in brain mode. Apply the same fix as -37 sendMsg: route through the v5 path (the same code as the non-brain-mode STT branch), and remove the `/organ_voice` call.

If the STT non-brain-mode path uses the same /converse endpoint, the brain-mode STT branch should be deleted (fall through to the non-brain-mode branch). If the structure makes deletion awkward, leave a small no-op branch.

c1: view lines 425-470 first, share the existing structure in the report, and choose the cleanest cut. If a substantive structural decision is needed (e.g. STT path differs in important ways), surface it back to Eve rather than improvising.

### 2.8 _formatOrganBrainResponse() function

The function definition at line 828 is now only referenced by the STT branch. After 2.7 removes that reference, the function has zero callers.

If c1 confirms zero callers after 2.7: delete `_formatOrganBrainResponse` (lines 828-840, approximately).

### 2.9 Comment + text references — cosmetic

Search for `Organ Brain` (case-insensitive) and `organ-brain` in the file. For each remaining occurrence:

- Update comments to reflect post -26 architecture (the 8-organ atlas is "Hemispheres" or "Embryo hemispheres", her voice comes from v5 composer).
- Leave the SVG visualization code references to organ tags (em, pr, ep, sc, gp, sf, sv, aff) — those are substrate-true.
- Specifically: line 806-807 comment block ("Organ-brain is the default voice...") should be replaced with the new comment shown in 2.2.
- Line 982-983 comment ("Brain visualization — from the substrate's organ_brain field...") — leave the data flow, but change "Brain visualization" to "Hemispheres visualization" and remove the "ONE brain" language (it's stale).
- Line 1183 section comment "--- Organ-brain visualization ---" → "--- Hemispheres visualization ---"

---

## 3. Tests

### V1 — Page reload presents substrate-true text

Hard-reload the gualaloom.html page. Confirm:
- No "Guala ready. Organ-brain voice active." message.
- New: "she is here"
- No "speak to her organ-brain..." placeholder.
- New: "say something..."
- No "🧠 organ-brain" toggle button visible.
- No "Organ Brain" sidebar panel title.
- New: "Hemispheres"
- No "warming..." placeholder under hemispheres svg.
- No "she is still loading..." in stats-line initially.

### V2 — Hemispheres visualization still renders

After page loads and pollBrain() runs, the 8-organ circle visualization should appear in the Hemispheres panel exactly as before. The data path is unchanged; only the label changed.

### V3 — Typed message routing unchanged from -37

Send a typed message. Confirm:
- Single backend call (the -37 fix is preserved).
- v5 voice or "(she is quiet)" — no "(organ-brain warming up)".
- No regressions from -37.

### V4 — STT routing fixed

If STT is testable in the browser session: speak a message. Confirm it goes through the same v5 /converse path as typed messages, returns the same kind of response (voice or "she is quiet"), and does not call /organ_voice.

If STT isn't testable in the deploy session, c1 should at least verify the code path by inspection and confirm no /organ_voice call remains in the STT handler.

### V5 — Substrate-busy message

Trigger a 503 (e.g., during a known curriculum pause or daydream cycle). Confirm the system message says "(substrate busy — try again in a moment)" not "she is still loading".

### V6 — No JS errors

Console clean on page load and on send. The hidden toggle button must not throw on the no-op toggleBrainMode call if any code path still hits it.

---

## 4. Rollback

If V1 or V3 fails:
1. Revert the HTML change.
2. Redeploy + invalidate CloudFront cache.
3. No substrate change to roll back.

---

## 5. Reporting

c1 produces `GL-RPT-UI-HONESTY-C1-20260629-38.md` with:
- HTML diff summary covering each section 2.1 through 2.9.
- Result of V1-V6.
- Final SHA and ECS task number.
- Note on whether _formatOrganBrainResponse was deleted or retained, with caller list if retained.
- Any unexpected JS errors observed.

---

## 6. Out of scope (intentionally)

- The brain-mode toggle UI element itself is hidden, not removed. If you want it fully removed in the source, that's a follow-up cosmetic dispatch.
- Removing `/organ_voice` (app.py) and `/organs_say` (substrate_runner.py) endpoints — both endpoints continue to return silenced stubs. Removing them is endpoint-hygiene work for later.
- Any change to v5 voice composition, commit-gate, or grandurun logic. This dispatch only changes the UI surface.
- Any change to status polling timeout or backoff. If pollStatus is 503'ing frequently for Joe, that's a separate diagnosis (probably ECS task settling or curriculum pause windows); this dispatch does not address polling robustness beyond the initial-text fix.
