# GL-BRIEF-AUDIO-UNLOCK-FIX-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1 — apply now
**Status:** Joe can't hear her and can't see if mic is on. Both are diagnosable; fix is targeted.

## Root causes (from reading the code, not guessing)

`dsf_ai_service/static/gualaloom.html`:

1. **`unlockAudio` (line 283-293) does not actually unlock the audio element.** Calls `voiceEl.play()` on an audio element with no `src` set. Browsers reject this — element never gets user-gesture permission. When `addResponseBlock` later sets `voiceEl.src` from the espeak WAV and calls `play()`, the play is silently blocked by autoplay policy. Same applies to the speechSynthesis warm-up: `new SpeechSynthesisUtterance('')` with `volume=0` is treated as a no-op by Chrome. Neither audio path is unlocked.

2. **Every audio failure is silently swallowed.** Line 285, 290, 317, 560 all `.catch(()=>{})` or `try{}catch(e){}`. Joe sees emission text appear, hears nothing, has no way to know whether (a) speak was never called, (b) speak was called but blocked, (c) WAV was attempted but failed, (d) it played and his speakers are muted system-side.

3. **Mic LISTENING indicator is in the wrong place.** Lives on `#mic-btn` (input row, ~12px font, dark). Joe's looking at the top permission strip where "Enable Microphone" lives. He won't find the small button.

## Fix — three targeted changes, one file

### Change 1: real audio unlock

Replace `unlockAudio` (line 283-293) with:

```javascript
function unlockAudio(){
  if(audioUnlocked)return;audioUnlocked=true;
  const badge=document.getElementById('speaker-badge');
  // Real silent WAV — 100ms of silence. This actually unlocks the audio element.
  voiceEl.src='data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQIAAAAAAA==';
  voiceEl.play().then(()=>{
    badge.innerHTML='\ud83d\udd0a audio ready';
  }).catch(e=>{
    badge.innerHTML='\ud83d\udd07 audio unlock failed: '+e.message;
  });
  // Real speech warm-up with audible-but-quiet content.
  try{
    const warmup=new SpeechSynthesisUtterance('a');
    warmup.volume=0.01;warmup.rate=2.0;
    warmup.onerror=e=>{badge.innerHTML='\ud83d\udd07 speech blocked: '+(e.error||'unknown')};
    window.speechSynthesis.speak(warmup);
  }catch(e){badge.innerHTML='\ud83d\udd07 speech unavailable: '+e.message}
}
```

The silent WAV is a real audio sample. `voiceEl.play()` on it gets actual permission. The warm-up speaks a single letter at 1% volume at fast rate — inaudible to Joe, but Chrome registers it as a real utterance and unlocks the API.

### Change 2: visible diagnostics on every speak

Replace `gualaSpeak` (line 309-318) with:

```javascript
function gualaSpeak(text){
  const badge=document.getElementById('speaker-badge');
  if(!text||text==='...'||text.trim()===''){
    badge.innerHTML='\ud83d\udd07 (nothing to say)';return;
  }
  if(muted){badge.innerHTML='\ud83d\udd07 muted';return}
  if(!audioUnlocked){badge.innerHTML='\ud83d\udd07 click anywhere to enable audio';return}
  try{
    const u=new SpeechSynthesisUtterance(text);
    if(preferredVoice)u.voice=preferredVoice;
    u.rate=0.92;u.pitch=1.15;u.volume=1.0;
    u.onstart=()=>{badge.innerHTML='\ud83d\udd0a speaking...'};
    u.onend=()=>{badge.innerHTML='\ud83d\udd0a ready'};
    u.onerror=e=>{badge.innerHTML='\ud83d\udd07 speak error: '+(e.error||'unknown')};
    window.speechSynthesis.speak(u);
    // Diagnostic: confirm it's queued
    setTimeout(()=>{
      if(window.speechSynthesis.pending||window.speechSynthesis.speaking)return;
      // Neither pending nor speaking after 500ms — it was silently dropped
      badge.innerHTML='\ud83d\udd07 utterance dropped silently';
    },500);
  }catch(e){badge.innerHTML='\ud83d\udd07 speak threw: '+e.message}
}
```

And replace the v7 WAV playback in `addResponseBlock` (line 558-565) with:

```javascript
  const badge=document.getElementById('speaker-badge');
  if(result.self_voice_audio_b64&&audioUnlocked&&!muted){
    voiceEl.src='data:audio/wav;base64,'+result.self_voice_audio_b64;
    voiceEl.play().then(()=>{
      badge.innerHTML='\ud83d\udd0a speaking (espeak)';
    }).catch(e=>{
      badge.innerHTML='\ud83d\udd07 espeak play failed: '+e.message+' \u2014 trying TTS';
      // Fall back to browser TTS
      const tokText=(result.response_tokens||[]).map(t=>t.token).join(' ');
      if(tokText)gualaSpeak(tokText);
    });
  }else{
    const tokText=(result.response_tokens||[]).map(t=>t.token).join(' ');
    if(!result.self_voice_audio_b64)badge.innerHTML='\ud83d\udd0a (no espeak WAV \u2014 using browser TTS)';
    if(tokText)gualaSpeak(tokText);
  }
```

After these changes, the speaker-badge becomes a live status line. Joe will see in real time:
- `🔊 audio ready` — unlock worked
- `🔊 speaking...` — she's speaking right now via browser TTS
- `🔊 speaking (espeak)` — she's speaking via server-side espeak WAV
- `🔇 audio unlock failed: ...` — first click didn't grant permission
- `🔇 speak blocked: not-allowed` — browser autoplay policy still blocking
- `🔇 utterance dropped silently` — speak() was called but Chrome ignored it
- `🔇 espeak play failed: ...` — WAV came from server but browser refused
- `🔇 (nothing to say)` — emission was empty/"..."

Whatever's failing, Joe sees what.

### Change 3: visible LISTENING indicator in permission strip

Replace the `mic-perm` button HTML (line 78) with:

```html
<button class="perm-btn" id="mic-perm" onclick="requestMic()">Enable Microphone</button>
<span id="mic-status" style="font-size:11px;color:var(--text-muted);margin-left:4px"></span>
```

In `toggleSTT` (line 324), replace the inside-toggleSTT mic-btn styling with also setting the strip status. After line 339 (`btn.style.background='#3fb950';btn.style.color='#0d1117';`), add:

```javascript
document.getElementById('mic-status').innerHTML='\u2705 LISTENING';
document.getElementById('mic-status').style.color='#3fb950';
document.getElementById('mic-status').style.fontWeight='bold';
```

And after line 331 (the turn-off path), add:

```javascript
document.getElementById('mic-status').innerHTML='';
```

Now Joe sees "✅ LISTENING" in green right next to the Enable Microphone button, in the strip his eyes are already on.

## Verification

1. Joe loads page in fresh incognito.
2. Speaker badge initially reads `🔇 Click anywhere to enable audio`.
3. Joe clicks anywhere on the page. Badge changes to `🔊 audio ready` (if successful) or shows the specific error if not.
4. Joe types "hi" and presses send. Badge shows `🔊 speaking...` during her response, then `🔊 ready`. He hears her voice. If anything is blocked, badge shows the specific reason.
5. Joe clicks Enable Microphone. Permission strip shows "✅ Microphone ON" AND next to it "✅ LISTENING" in bold green. No ambiguity.
6. Joe speaks. Live transcript appears in orange. On final, message sends. Mic stays LISTENING (always-on phone mode).

If audio still doesn't play after this fix, the badge will tell us exactly what's blocking it. That's the diagnostic we need.

## Deploy

One commit, frontend asset only. No backend changes. Tag `PRE-AUDIO-UNLOCK-FIX`. Smoke = Joe refreshes, sees the badge update on first click.

End of brief.
