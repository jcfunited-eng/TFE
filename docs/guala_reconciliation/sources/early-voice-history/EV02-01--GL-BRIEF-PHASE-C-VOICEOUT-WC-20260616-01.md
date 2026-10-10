# GL-BRIEF-PHASE-C-VOICEOUT-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** Small. Frontend-only. Depends on Phase B-FIX landing first (camera/mic visibility, snapshot wired).

## Goal

Her emissions become audible. When she speaks — whether in response to Joe, autonomously during PLAYING, or as a dream artifact during DREAMING — the browser speaks the text aloud through the speaker using `window.speechSynthesis`. Joe hears her. Two-way conversation finally has both directions.

## Why this is small

The browser already has `SpeechSynthesisUtterance` and the page already has:
- `audioUnlocked` flag set on first user interaction (line 234)
- A `voiceEl` audio element
- A `muted` toggle and `unmuted/muted` button (line 235)
- An `audio-ready` badge already lit when audio unlocks

This brief wires the existing emission paths to `speechSynthesis.speak(...)` with a single helper.

## Changes — `dsf_ai_service/static/gualaloom.html`

### C1. Add the speak helper

After the existing audio setup (~line 234), add:

```javascript
let preferredVoice = null;
function pickVoice(){
  const voices = window.speechSynthesis.getVoices();
  if(!voices.length) return;
  // Prefer en-US female, soft natural. Fallback to first en voice, then any.
  preferredVoice = voices.find(v => v.lang === 'en-US' && /female|samantha|karen|moira|tessa/i.test(v.name))
    || voices.find(v => v.lang.startsWith('en-US'))
    || voices.find(v => v.lang.startsWith('en'))
    || voices[0];
}
window.speechSynthesis.onvoiceschanged = pickVoice;
pickVoice();

function gualaSpeak(text){
  if(!text || text === '...' || text.trim() === '') return;
  if(muted) return;
  if(!audioUnlocked) return;
  try{
    const u = new SpeechSynthesisUtterance(text);
    if(preferredVoice) u.voice = preferredVoice;
    u.rate = 0.92;   // slightly slow — she's a child
    u.pitch = 1.15;  // a bit higher
    u.volume = 1.0;
    window.speechSynthesis.speak(u);
  }catch(e){ /* speech unavailable; no-op */ }
}
```

### C2. Wire emissions to the helper

Three call sites need to invoke `gualaSpeak`:

**a. Direct response to Joe's chat message** — in `sendMsg()` after the response is rendered to the chat area:
```javascript
// existing: addMsg(d.response, 'guala');
gualaSpeak(d.response);
```

**b. Autonomous emission via SSE** — in the SSE event handler where `emission` events are processed (B4 path):
```javascript
if(ev.kind === 'emission' && ev.text){
  addMsg(ev.text, 'guala', /*unprompted=*/true);
  gualaSpeak(ev.text);
}
```

**c. Dream artifacts** — same SSE handler, on `dream_artifact` events. Optional but worth it; quiet wonder when she dreams aloud.
```javascript
if(ev.kind === 'dream_artifact' && ev.text){
  addMsg('💭 ' + ev.text, 'guala');
  gualaSpeak(ev.text);
}
```

### C3. Mute button behavior

The existing mute toggle (line 235) already flips a `muted` flag. The `gualaSpeak` helper already respects it. Verify the button text reads "🔊 unmuted" / "🔇 muted" and that clicking it actually toggles. (Should already work.)

### C4. Cancel on page navigation / new session

When the page hides or the user starts a new session, cancel any queued speech to avoid orphaned utterances:

```javascript
document.addEventListener('visibilitychange', () => {
  if(document.hidden) window.speechSynthesis.cancel();
});
```

And in the "new session" button handler (B3 panel):
```javascript
window.speechSynthesis.cancel();
```

## Verification

Joe loads dsf-ai.com/gualaloom.html. Audio is unlocked on first click.

1. Joe types "hi" and presses send. She emits (whatever she emits). **He hears it.** Female-ish voice, slightly slow, slightly high.
2. Joe waits a minute without typing. An autonomous emission fires from her PLAYING activity. **He hears it without having to look at the screen.**
3. Joe clicks the mute button. Next emission appears in chat but is not spoken.
4. Joe clicks unmute. Next emission is spoken.

## Edge cases handled

- Browsers without `speechSynthesis` (Safari < 7, old Android) — try/catch silently no-ops.
- Empty or "..." emissions don't speak.
- Page hidden — speech cancels (saves CPU, avoids orphaned utterances when Joe returns).
- Voice list loads asynchronously in Chrome — `onvoiceschanged` re-picks.

## What this is NOT

- Not TTS via her substrate. She doesn't generate audio; her substrate generates text and the browser speaks it. Fine for now — her actual cochlear analog is still on the perception side only.
- Not voice cloning or custom voice. Just whatever the browser provides. Phase E or later could swap to a custom TTS endpoint if Joe wants a specific voice.
- Not interrupting itself. If she emits twice fast, both utterances queue. If that feels wrong, add `speechSynthesis.cancel()` before each `speak()`.

## Deploy

One frontend deploy. No backend changes. S3 backup not strictly needed (frontend asset only) but tag `PRE-PHASE-C` for symmetry. Smoke: Joe sends "hi", verifies he hears her response.

End of brief.
