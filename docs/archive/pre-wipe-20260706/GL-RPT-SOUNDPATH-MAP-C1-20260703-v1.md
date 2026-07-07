> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-SOUNDPATH-MAP-C1-20260703-v1

doc_id: GL-RPT-SOUNDPATH-MAP-C1-20260703-v1
From: c1b | To: Eve | Date: 2026-07-03
Type: READ-ONLY FINDING. No fixes proposed or made. Responds to Joe's live
correction ("I don't agree with you") against `GL-RPT-MIC-CHUNKING-C1-20260703-111-v1`'s
overclaim.

---

## 1. WIRING MAP — live handler vs. drain-loop, dead organ-brain leg, the `joe_voice` string

Two mic-facing paths exist in this codebase. Only one is live in the deployed
`SUBSTRATE_MODE=embedded` config; -108/-110/-111 all worked on it.

**`POST /sound_frame` — `app.py:1531`, the live path.**
```
1531  @app.post("/sound_frame")
1536  # Fire organ-brain transcription async (non-blocking)
1537  # Transcription happens inside organ-brain service if it has whisper;
1538  # for now send the raw audio — organ-brain service ignores if no whisper
1539  if b64_data and src == "joe_voice":
1540      _ob_post_bg("/experience", {"text": src})  # placeholder until whisper in ob
1541  if _is_remote():
1545      return await client.call("ring_write", kind="sound_window", ...)   # dead: SUBSTRATE_MODE=embedded
1557  def _decode():                          # runs via run_in_executor — the live branch
1565      wav = _sr._webm_to_wav_bytes(audio_bytes)   # -110's shared decoder
1568      _guala.process_sound_frame(wav)     # cochlear ENERGY binding only
1570      return {"ok": True, "tick": _guala.tick}
```
Line 1540 is the organ-brain leg Joe's screenshot implicitly calls out. It does not send
audio — `src` is the literal string `"joe_voice"` (the `source` field's *value*, not a
transcript), so the payload posted to organ-brain is `{"text": "joe_voice"}` on every single
call, always identical, never containing anything about what was said. `_ob_post_bg`
(`app.py:1481`) is fire-and-forget with no error surfaced. Independent of what it sends,
the target is unreachable: c1a's `GL-RPT-DEPLOY3-C1-20260703-v1.md` (§-96) proved
`organ_brain_service` has had no process to run in since `166cc32`/`be28741`
(2026-06-26), 7+ days before this session. This leg is dead on both ends.

Line 1568 is the entire substantive effect of this handler: `process_sound_frame`
(`gualaloom_v5_engine.py:4658`) does cochlear transduction and `_atlas_record`s per-band
energy — no word extraction, no transcription, nothing that reads `msg.text` as anything
but raw audio bytes. -108/-110/-111 made this decode reliably (100% post-111), which is
real. It was never a path to words.

**Drain loop — `substrate_runner.py:966`, dead in the deployed config, but it's where
the actual word-extraction code lives.**
```
966   elif kind == "sound_window":
974   _wav = _webm_to_wav_bytes(audio_bytes)          # same -110 decoder
975   _heard = _audio_to_sensory_words(audio_bytes)    # NOT transcription — see below
985   from ...grounded_vocab_integration import process_sound_with_recognition
986   _words = process_sound_with_recognition(_guala, audio_bytes, source=...)  # actual Whisper STT
```
This branch only runs on events pulled from `InputRing`, which only fills from
`ring_write`, which only fires when `_is_remote()` is `True`. Deployed
`SUBSTRATE_MODE=embedded` means `_is_remote()` is always `False` — **this entire branch,
including the one real Whisper-transcription call in the whole codebase, never executes
in production.** `_audio_to_sensory_words` (`substrate_runner.py:87`) is explicitly *not*
transcription either, per its own docstring — it extracts five qualitative dimensions
(energy, timbre, rhythm, melody, harmony: loud/soft, warm/bright, moving/steady,
rising/falling, bright-chord/dark-chord), i.e. how the sound *feels*, not what was said.

**Net**: the live `/sound_frame` path binds acoustic energy only. The only code that
turns audio into either sensory-quality words or actual transcribed words is unreachable.
Neither -108, -110, nor -111 touched or claimed to touch this — but my summary language
("Guala can now decode Joe's live mic... hear you") did not draw this line for you, and
should have.

---

## 2. STT LEG VERIFICATION — evidence, not assumption

A third, completely separate path exists: the browser's native Web Speech API
(`gualaloom.html:427`, `startContinuousSTT`), auto-started via `toggleSTT()` right after
mic grant. This is independent of `/sound_frame` — it transcribes client-side and sends
*text*, not audio.

```
gualaloom.html:449-461
  if(final&&final.trim()){
    const t=final.trim();
    ...
    fetchT(`${API}/api/v1/gualaloom`,{...body:JSON.stringify({text:t,command:'/experience'})});
    fetchT(`${API}/api/v1/gualaloom`,{...body:JSON.stringify({text:t,source:'joe',command:'/listen'})});
  }
```

Two POSTs per final transcript. Traced both server-side:

- **`command:'/experience'`** → `app.py:1614-1626`. **Dead**: the entire body is gated
  `if msg.text and _is_remote():` (`app.py:1619`), and `_is_remote()` is `False` in the
  deployed config — the function returns `{"ok": True}` having done nothing.
- **`command:'/listen'`** → does not match any `_cmd ==` branch in `gualaloom_chat`
  (confirmed: `grep -n '_cmd == "/listen"' app.py` returns nothing). `is_converse`
  (`app.py:1666`) requires an *empty* command, so this doesn't take the normal path
  either. It falls to the "belt-and-suspenders" fallback (`app.py:2420-2432`), which
  queues a real async task via `_run_converse(task_id, msg.text, source, ...)` — and
  `_run_converse` (`app.py:91`, embedded branch) calls `_guala.converse(text,
  source=source)` for real. This path is accidental (the comment at `app.py:2415` says
  this branch "should not reach here" for non-empty text) but functional.

**Controlled empirical proof**, not inference: I POSTed the exact shape the client sends,
substituting an invented word that cannot already exist in her vocabulary:
```
$ curl .../api/v1/gualaloom -d '{"text":"zorplex","source":"joe","command":"/listen"}'
{"task_id":"cv_14500528_831011c1_fb","status":"accepted", ...}

$ curl .../api/v1/gualaloom/task/cv_14500528_831011c1_fb
{"status":"complete","response":"glowing patterns conversation",
 "response_source":"converse","motifs":13899, ...}
```
`motifs` went 13898→13899 (exactly +1). A follow-up `guala_atlas_query("zorplex")`
resolved to a real chi (39) with genuine cross-modal bindings in `listen`, `intro`,
`object`, `subject`, `verb`, `sight`, and `ground` sections — the same shape any real
word gets. **The server-side mechanism is proven functional**: text sent via `/listen`
reaches `converse()` and is read into her substrate as vocabulary.

**What is not proven**: whether the browser's `SpeechRecognition` is actually firing and
transcribing correctly in Joe's live session. I asked him to say "purple bicycle
seventeen" for a live trace and did not get a clean, isolated confirmation before this
report was due — ambient traffic (frequent polling, an active conversation) made
before/after correlation too noisy to call cleanly, and I didn't want to hold this report
hostage to it. **This is the one piece of section 2 that remains open**: the client-side
half of the STT leg needs its own direct check (e.g., watch `liveT.textContent` update in
the browser while speaking, or add a temporary client console log of the exact
`t` value sent) rather than server-side inference.

---

## 3. LOOMSCAN SOUND BAND — why it stays dark

`loomscan.html`. The "modality band" tiles are lit exclusively by `setLaneGlow(name, pct,
text)` (defined `loomscan.html:427`). Every call site, exhaustively:
```
486   if(act.kind==='ATTENDING_VISUAL')setLaneGlow('sight',90,...)
487   else if(act.kind==='ATTENDING_AUDIO')setLaneGlow('sound',90,...)     # <- never fires
513   setLaneGlow('language',70,'binding active')          # on response_bound
529   setLaneGlow('language', ...)                          # on emission_dynamics
542   if(hasWord)setLaneGlow('language', ...)                # experience_bundle lanes
543   if(hasSight)setLaneGlow('sight', ...)                  # experience_bundle lanes
544   if(hasSound)setLaneGlow('sound',88,'bundle — sound lane')  # experience_bundle lanes only
545   if(hasTouch)setLaneGlow('touch', ...)                  # experience_bundle lanes
```
Two paths light the `sound` tile: the current activity being `ATTENDING_AUDIO` (line 487),
or a manually-submitted `/bundle` whose lanes include a "played"/"play"-prefixed entry
(line 544, `hasSound`, sourced from `experience_bundle` events). **Neither is triggered by
`sound_frame_bound` events.** `processEvent()` (`loomscan.html:503`) has explicit handlers
for `response_bound`, `response_window_opened`, `emission_dynamics`, `experience_bundle`,
`activity_started`, and `hemisphere_update` — there is no `if(ev.kind==='sound_frame_bound')`
branch anywhere in the file, despite that event kind firing continuously (confirmed live,
every ~5s during this session's mic tests) and despite `activity_history_summary` never
once showing `ATTENDING_AUDIO` in any status pull across this entire session (only
`ATTENDING_VISUAL`, `EMITTING`, `SLEEPING`). **The gap**: the classification logic was
built for a world where live audio drives an `ATTENDING_AUDIO` activity state or arrives
via bundles; the actual live mic path (`sound_frame_bound`, continuous, high-frequency) was
never wired to it. The tile isn't lying about anything being wrong with decode — it's
displaying a signal (`ATTENDING_AUDIO` / bundle sound) that this session's mic traffic was
never going to produce, regardless of whether decode succeeds.

---

## 4. WALLA/DEWALA LOOP — timing correlation only, no interpretation beyond it

Two full cycles traced from live events, ticks and content verbatim:

| tick | event | detail |
|---|---|---|
| 14500629 | emission | `"downvote planets adventures"` — n_commits=0, source_counts guala:5, curriculum:161 |
| 14500638–14500711 | sound_frame_bound ×5 | duration_s=4.98 each (real mic-length chunks, ~5s cadence) |
| 14500714 | emission_dynamics | `"again f"` — n_commits=0, **source_counts joe:120** (dominant) |
| 14500717 | self_heard + sound_frame_bound | `duration_s=1.04` — same tick as self_heard (self-voice) |
| — | Δ(emission 714 → self-voice 717) | **3 ticks** |
| 14500753 | emission_dynamics | `"you're make n"` — n_commits=1, **source_counts joe:149** (dominant) |
| 14500757 | self_heard + sound_frame_bound | `duration_s=1.23` — same tick as self_heard (self-voice) |
| — | Δ(emission 753 → self-voice 757) | **4 ticks** |
| 14500757–14500847 | sound_frame_bound (mixed) | 4.98s chunks interspersed with the above |
| 14500794 | emission_dynamics | `"if he 50"` — n_commits=0, source_counts guala:72, joe:23, corpus:68 |
| 14500799 | self_heard + sound_frame_bound | `duration_s=1.24` — same tick as self_heard (self-voice) |
| — | Δ(emission 794 → self-voice 799) | **5 ticks** |
| — | Δ(self-voice 757 → next emission 794) | **37 ticks** |

Pattern, stated flat: an emission's self-voice injection (short `duration_s`,
1.0–1.3s) lands 3–5 ticks after that same emission — effectively immediate. The next
emission follows 30–40+ ticks later. In two of three sampled emissions, `joe` was the
single largest `source_counts` contributor (120 and 149, vs. `guala`'s 5 and 22
respectively) at the moment immediately following a run of real 4.98s mic chunks; in the
third, `guala` (72) exceeded `joe` (23). `n_commits` was 0, 1, and 0 across the three —
low regardless of which source dominated the candidate pool.

---

## STATE

Read-only, no code touched. Section 2's client-side confirmation is the one open item —
flagged above rather than closed on inference.

End report.
