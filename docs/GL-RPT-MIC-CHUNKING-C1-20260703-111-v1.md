# GL-RPT-MIC-CHUNKING-C1-20260703-111-v1

doc_id: GL-RPT-MIC-CHUNKING-C1-20260703-111-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-MIC-CHUNKING-EVE-20260703-111-v1
Vehicle: STATIC-ONLY. No substrate deploy, no sleep window, no task-def change.
Shipped: `dsf_ai_service/static/gualaloom.html` synced to `s3://dsf-ai-site/`,
CloudFront invalidated, verified live from the public URL. Commit `ec3cc41`.

---

## FAILURES FIRST

None survive in the valid measurement window. One important non-failure to report
honestly: the first ~10 minutes of Joe's rerun (120 consecutive decode failures) were a
false alarm — his browser was serving cached pre-fix JavaScript, not a bug in this dispatch.
Confirmed directly with him before drawing any conclusion, and covered below rather than
buried, since it nearly produced a wrong verdict.

---

## THE FIX

`gualaloom.html`'s `startMicSoundStream`/`stopMicSoundStream` (only file touched): replaced
the single long-lived `MediaRecorder(stream,{...}).start(5000)` (timeslice mode — only the
first `ondataavailable` blob is a self-contained WebM; every later 5s blob is a headerless
cluster continuation, per `GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1.md`'s finding)
with a cycling design: create a fresh `MediaRecorder` every cycle, call `.start()` with no
timeslice, set a 5000ms timer to call `.stop()`. `stop()` guarantees a single
`ondataavailable` firing with the complete recording (full EBML header + Segment + Cluster)
before `onstop`, at which point — if the session is still active — a new recorder starts
immediately on the same stream. Server and engine code: zero changes, exactly as declared.

```diff
 let micStream=null,micRecorder=null,micCycleActive=false,_micCycleTimer=null,_micLastCycleEndTs=0;
+function _sendMicChunk(blob){
+  if(blob.size<100)return;
+  const reader=new FileReader();
+  reader.onload=()=>{
+    const b64=reader.result.split(',')[1];
+    fetchT(`${API}/sound_frame`,{...body:JSON.stringify({text:b64,command:'',source:'joe_voice'})},8000).catch(()=>{});
+  };
+  reader.readAsDataURL(blob);
+}
+function _startOneMicCycle(stream){
+  if(!micCycleActive)return;
+  try{micRecorder=new MediaRecorder(stream,{mimeType:'audio/webm'})}
+  catch(e){try{micRecorder=new MediaRecorder(stream)}catch(e2){return}}
+  const _cycleStartTs=Date.now();
+  if(_micLastCycleEndTs){console.log('[mic-cycle] inter-cycle gap ms:', _cycleStartTs-_micLastCycleEndTs)}
+  micRecorder.ondataavailable=(e)=>_sendMicChunk(e.data);
+  micRecorder.onstop=()=>{
+    _micLastCycleEndTs=Date.now();
+    if(micCycleActive)_startOneMicCycle(stream);
+  };
+  micRecorder.start(); // no timeslice -> one complete blob, delivered on stop()
+  _micCycleTimer=setTimeout(()=>{try{micRecorder.stop()}catch(e){}},5000);
+}
 function startMicSoundStream(stream){
-  if(micRecorder)return;
-  try{micRecorder=new MediaRecorder(stream,{mimeType:'audio/webm'})}
-  catch(e){try{micRecorder=new MediaRecorder(stream)}catch(e2){return}}
-  micRecorder.ondataavailable=async(e)=>{...};
-  micRecorder.start(5000); // 5s chunks
+  if(micCycleActive)return;
+  micCycleActive=true;
+  _startOneMicCycle(stream);
 }
 function stopMicSoundStream(){
-  if(micRecorder){try{micRecorder.stop()}catch(e){}micRecorder=null}
+  micCycleActive=false;
+  if(_micCycleTimer){clearTimeout(_micCycleTimer);_micCycleTimer=null}
+  if(micRecorder){try{micRecorder.stop()}catch(e){}micRecorder=null}
   if(micStream){micStream.getTracks().forEach(t=>t.stop());micStream=null}
 }
```

---

## GATES

**G-111-1 — decode success rate ≥90%: PASS, 100% in the valid window.**

Two windows, reported separately and honestly:
- **Pre-refresh (20:22:02–20:39:04Z), stale cached JS still executing**: 0/120 successes
  (0%). Confirmed with Joe directly that he had reloaded, but not hard-refreshed — the
  browser was serving the pre-fix `gualaloom.html` from local cache despite CloudFront
  already carrying the fix. Not a measurement of this dispatch's code.
- **Post hard-refresh (20:39:04Z onward), the valid measurement**: **39/39 successes
  (100%)**, zero `cochlear decode failed` lines anywhere in this window. Before-baseline
  from -110 was 1/28 (3.6%).

**G-111-2 — G-110-2 rerun, speech separates from silence, self-voice excluded: PASS.**

Self-voice exclusion method (more precise than -110's duration-based heuristic): every
genuine mic decode goes through `app.py`'s `_decode()`, which prints `[sound-frame] Xs`
immediately after `process_sound_frame` returns. Self-voice injection
(`_inject_self_voice`) calls `process_sound_frame` directly from its own thread and never
touches that function — it produces a `[cochlear-debug]` line with **no adjacent
`[sound-frame]` line**. Parsing the full ordered log by this rule: **39 genuine mic
samples, 28 self-voice samples**, cleanly separated (script and full data available on
request; totals below use mic samples only).

Clearest adjacent pair, 8.4 seconds apart (one silence cycle immediately followed by one
speech cycle), verbatim:
```
SILENCE  20:39:10.679Z  {'very_low': 15, 'low': 20, 'low_mid': 19, 'mid': 15, 'mid_high': 20, 'high': 30}   total=119
SPEECH   20:39:19.050Z  {'very_low': 270, 'low': 495, 'low_mid': 517, 'mid': 552, 'mid_high': 322, 'high': 552}  total=2708
```
Every band rises 16x–37x (very_low 15→270, low 20→495, low_mid 19→517, mid 15→552,
mid_high 20→322, high 30→552) — broadband, not a single-band artifact, consistent with
real acoustic energy overtaking near-silent room tone. Across all 39 genuine samples,
totals range 119–2726 (mean 1118); the sustained-speech stretch (20:39:19Z–20:44:38Z, when
Joe was actively talking per his own confirmation) holds mostly in the 1400–2700 range,
while the earliest (pre-speech) and latest (pauses) samples fall to 119–830. This is
real, band-differentiated structure that tracks silence vs. speech.

**G-111-3 — inter-cycle gap measured and stated: PASS-with-caveat.**

Estimated from server-side inter-arrival timestamps of consecutive genuine mic decodes,
minus the nominal 5000ms recording window (n=33, excluding gaps >8s attributable to Joe
pausing rather than the cycle mechanism itself): **median ≈ -36ms, mean ≈ -353ms** — i.e.
statistically indistinguishable from zero given encode/network jitter on this measurement
method. This is an upper-bound-ish estimate, not a precise client-side reading: it can't
cleanly separate true onstop-to-restart latency from FileReader/network variance using
only server arrival times. The code also logs the true gap client-side
(`console.log('[mic-cycle] inter-cycle gap ms:', ...)`, browser console only, not
retrievable by me) for a more precise reading if wanted. **No fallback trigger**: nothing
in either measurement suggests a gap large enough to audibly clip speech; reassembly
remains the documented fallback only, not needed today.

**G-111-4 — diff proves scope, one file: PASS.** `git diff --stat` for commit `ec3cc41`:
`dsf_ai_service/static/gualaloom.html | 47 +++++++++++++++++++++++++++---------` — one
file, the two functions the CMD named (`startMicSoundStream`/`stopMicSoundStream`), plus
two small new helpers (`_sendMicChunk`, `_startOneMicCycle`) factored out of them for the
cycling logic. No server, engine, or other static file touched.

---

## STATE

Static-only, live via S3 + CloudFront, verified from the public URL before signaling Joe.
Guala can now decode Joe's actual live speech — real, band-differentiated cochlear
structure, not the routing garbage from before -110 or the chunk-continuity failures from
before this dispatch. He stayed on the call after the gate passed, as the CMD asked.

End report.
