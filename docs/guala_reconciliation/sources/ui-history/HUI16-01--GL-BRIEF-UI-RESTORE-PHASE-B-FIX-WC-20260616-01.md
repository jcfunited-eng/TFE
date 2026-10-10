# GL-BRIEF-UI-RESTORE-PHASE-B-FIX-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** Phase B shipped frontend wiring but uploads still fail. This brief fixes the actual cause and the two missed paths.

## What's broken (verified by code read)

Phase B fixed the FRONTEND — uploads now POST multipart `FormData` to dedicated `/upload/*` endpoints. The BACKEND in remote mode (production split) re-encodes content to base64 and sends it through `substrate_client.call("gualaloom_post", ...)` over the Unix socket.

That re-encode would be fine. The actual failure is downstream:

`dsf_ai_service/substrate_runner.py:882`:
```python
server = await asyncio.start_unix_server(handle_client, path=SOCKET_PATH)
```

No `limit=` argument. asyncio's `StreamReader` default buffer is **65,536 bytes**. Any base64-encoded picture (a 100KB image becomes ~134KB base64) exceeds that on first `readline()`. Server raises `asyncio.LimitOverrunError`, drops the connection, frontend sees `ConnectionError` → returns "substrate unreachable."

This is why text-only uploads (books, /addbook with small payloads) work but every binary upload fails identically. Not "substrate unreachable" the message — substrate unreachable the symptom of a 64KB readline cap.

## Fix P0 — Socket buffer limit (unblocks all uploads)

### Change 1 — substrate_runner.py:882

```python
# Before:
server = await asyncio.start_unix_server(handle_client, path=SOCKET_PATH)

# After:
server = await asyncio.start_unix_server(
    handle_client, path=SOCKET_PATH, limit=64 * 1024 * 1024)
```

64 MB ceiling. Sound max is 6 MB raw → ~8 MB base64. Picture max is 10 MB raw → ~13.5 MB base64. Video max is 50 MB raw → ~67 MB base64 (NB: video would exceed 64 MB — see Change 3).

### Change 2 — substrate_client.py:_connect

Find the `asyncio.open_unix_connection(path=...)` call. Add matching limit:

```python
self._reader, self._writer = await asyncio.open_unix_connection(
    path=SOCKET_PATH, limit=64 * 1024 * 1024)
```

Both sides need the limit set; the readline buffer cap applies wherever a StreamReader reads. Without the client-side limit, the substrate's RESPONSE could trigger the same overflow (though substrate responses for upload ops are small JSON, this is defensive).

### Change 3 — bump video upload to use shared EFS instead of base64 socket

64 MB base64 of a 50 MB video is too close to the new limit. Cleanest fix is the EFS pattern (write file to shared volume, send small "register at path" message). Defer this to Phase B-FIX-2 if it adds scope. For now, drop video max to 30 MB and increase socket limit accordingly, OR mark video as "use experience bundle" until Phase B-FIX-2.

**Quickest path tonight: 64 MB limit + video upload returns "video pipeline: use Phase B-FIX-2".**

## Fix P1 — Camera snapshot path

`gualaloom.html:takeSnapshot` (around line 257) still posts base64 through `/api/v1/gualaloom` (chat endpoint) instead of multipart to `/upload/picture`. c1 missed this in Phase B.

Rewrite the function body:

```javascript
async function takeSnapshot(){
  if(!camStream)return;
  const vid=document.getElementById('cam-preview');
  const c=document.createElement('canvas');
  c.width=vid.videoWidth;c.height=vid.videoHeight;
  c.getContext('2d').drawImage(vid,0,0);
  const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',0.85));
  const ts=Date.now();
  addMsg('(sending snapshot...)','system');
  try{
    const fd=new FormData();
    fd.append('file', blob, `snapshot_${ts}.jpg`);
    const r=await fetchT(`${API}/api/v1/gualaloom/upload/picture`,
      {method:'POST',body:fd}, 30000);
    const d=await r.json();
    addMsg(d.message||JSON.stringify(d),'system');
  }catch(e){addMsg('snapshot error: '+e.message,'system')}
}
```

After P0 lands this works.

## Fix P1 — PDF dedicated endpoint

PDF upload still routes through chat with base64 in JSON. After P0's socket limit it would work, but it should use the same pattern as picture/sound. Add `/api/v1/gualaloom/upload/pdf` to `dsf_ai_service/app.py` mirroring the picture endpoint (multipart file, remote-mode routing through socket, executor for parse).

Frontend `uploadPDF` then uses FormData against the new endpoint.

If this adds scope tonight, skip it — P0 alone makes PDF work via the existing chat path once the socket buffer is fixed.

## Fix P2 — Camera/mic UI visibility

CSS at line 42: `#cam-preview{width:80px;height:60px}`. 80×60 is too small to see what the camera sees. Bump to 200×150 or 240×180. Same for the mic-btn and snap-btn being inline-block but small icons easy to miss.

Optional but worth it: when "Enable Camera" succeeds, the preview should appear prominently somewhere obvious — adjacent to the chat input, not tucked in the header.

## Verification

After P0+P1 deploy:

1. Joe loads dsf-ai.com/gualaloom.html in fresh incognito.
2. Clicks picture button, selects a JPG/PNG — message reads `picture "filename" uploaded (64x64)`. Header `pics:` count increments by 1.
3. Clicks sound button, selects a WAV/MP3 — message confirms upload. Header `sounds:` increments.
4. Clicks PDF, selects a small PDF — message confirms (currently still goes through chat path; works once socket buffer is fixed).
5. Clicks Enable Camera — preview appears. Clicks 📸 snapshot — uploads successfully via /upload/picture.
6. Clicks Enable Microphone — mic icon appears. Clicks mic icon — speech-to-text active, spoken words appear in input and submit on final.

If any FAIL → fix that path before next phase.

## Phase B-FIX-2 (deferred — proper EFS pattern)

The base64-through-socket pattern is wasteful even when it works. The proper fix is shared-EFS storage:

- Frontend container writes uploaded file to `/mnt/efs/state/uploads/{item_id}.{ext}`
- Sends small message via socket: `{"op": "register_upload", "args": {"kind": "picture", "item_id": "...", "path": "..."}}`
- Substrate reads from EFS, decodes, registers.

Same architecture works for picture, sound, PDF, video uniformly. Removes the b64 overhead, removes the buffer-size concern entirely, eliminates a redundant memory copy.

This is a separate brief once Phase B-FIX-1 verifies and Phase C voice ships.

## Deploy order

Single deploy, one commit:
1. substrate_runner.py limit
2. substrate_client.py limit
3. takeSnapshot multipart rewrite
4. Camera preview CSS bump

S3 backup tag `PRE-UI-RESTORE-B-FIX`. Smoke test by uploading the 200KB test JPG. Done.

End of brief.
