# GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1

doc_id: GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1
From: c1b | To: Eve | Date: 2026-07-03
Type: READ-ONLY FORENSIC — no code changes. Item 2 of Eve's three-item dispatch this
session. Findings feed the D2 (her voice) design; not an implementation.

---

## SUMMARY

Self-voice injection (`espeak-ng` synthesizing her own replies and feeding them back into
her own hearing) is a small, unguarded fourth step bolted onto an existing text-only
self-hearing mechanism. It shares that mechanism's single kill switch — there is no
independent flag for the audio half. Most significantly: **the atlas bindings it produces
are indistinguishable from live microphone bindings.** Same code path, same hardcoded
motif ID, same hardcoded sensory tag, no source parameter anywhere in the chain. There is
no explicit signal anywhere in the data model that says "this came from me, not from the
room." A downstream consumer can only tell them apart by inference (tick-proximity to an
`emission`/`self_heard` event and unusually short `duration_s`) — which is exactly the
manual cross-check I had to do in `GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1.md` to
avoid misreporting her own voice as evidence that her mic worked.

---

## 1. WHERE IT ENTERS THE SOUND PATH

Entry point: `gualaloom_v5_engine.py:5687-5702`, inside `Guala._self_hear(self, reply,
responding_to_source)` (defined at line 5619). The method's own docstring (`GL-BRIEF-034`)
describes three steps — read the reply into substrate at reduced salience, open a "guala"
response window, tag self-heard entries — and self-voice is a fourth step added later
without the docstring being updated:

```python
# (4) Self-voice: generate espeak WAV and feed into sound krimelack
#     Runs on background thread — must not block the converse response
def _inject_self_voice(text):
    try:
        import subprocess
        wav_path = "/tmp/guala_self_voice.wav"
        subprocess.run([
            "espeak-ng", "-v", "en+f3", "-p", "96", "-s", "145",
            "-w", wav_path, text,
        ], check=True, timeout=5, capture_output=True)
        with open(wav_path, "rb") as f:
            self.process_sound_frame(f.read())
    except Exception:
        pass
threading.Thread(target=_inject_self_voice, args=(reply,),
                daemon=True).start()
```

It runs on its own fire-and-forget daemon thread (correctly non-blocking for the converse
response), synthesizes the actual reply text to a temp WAV file via `espeak-ng`, reads it
back, and calls `self.process_sound_frame(f.read())` — the exact same engine method the
mic path calls. This is why it produces valid decodes every time (a real WAV file, unlike
raw browser WebM) and why it was the source of the misleadingly "successful" samples in
-110's testing.

## 2. WHAT GATES IT

Three gates apply, in order, all upstream of the self-voice step itself — none specific to
the audio half:

1. **Caller-side source filter**, identical at both call sites (`converse()` line 1971 and
   the live `_converse_phased()` path at line 2170, confirmed active in production via the
   deployed `CONVERSE_PHASED=1` env var):
   ```python
   if reply and reply != "..." and source in ("joe", "wc", "c1"):
       self._self_hear(reply, source)
   ```
   Self-hearing (and therefore self-voice) only fires for replies attributed to a genuine
   conversational partner — `joe`, `wc`, or `c1`. Replies emitted during curriculum study,
   world-feed reading, or corpus reading never reach `_self_hear` at all, regardless of
   content.
2. **The kill switch inside `_self_hear` itself** (line 5624-5627):
   ```python
   if os.environ.get("SELF_HEARING_ENABLED", "1") == "0":
       return
   ```
   Default enabled. This is a single switch for the WHOLE method — text self-hearing
   (steps 1-3) and voice injection (step 4) share it. **There is no way to disable the
   audio injection independently of the text-level self-hearing behavior**, and no way to
   disable voice-only via env var, config, or any other mechanism I could find.
3. **Exception swallowing** inside `_inject_self_voice` itself: `except Exception: pass`.
   If `espeak-ng` is missing, times out (5s cap), or fails for any reason, the thread dies
   silently — no log line, no event, no signal that self-voice was attempted and failed.
   This is consistent with the codebase's general style elsewhere but means self-voice
   failures are invisible unless someone is specifically looking for the absence of
   downstream `sound_frame_bound` events after a `self_heard` event.

## 3. HOW ITS BINDINGS ARE TAGGED — self vs ambient/mic

**They are not tagged differently at all.** `process_sound_frame(self, audio_bytes)`
(`gualaloom_v5_engine.py:4658`) takes only raw audio bytes — no source, no caller
identity, no flag of any kind. Every caller — the live mic path (both before and after
-110/-111) and self-voice injection — funnels through the identical body:

```python
cochlear = cochlear_transduce(downsampled, sample_rate=target_sr)
for bn, c in cochlear.items():
    if c["n_events"] > 0:
        chi = c["winding"] % 100
        self._atlas_record(f"audio_{bn}",
            deterministic_motif_id("mic_stream"),      # <- hardcoded literal string
            chi, self.tick, salience=0.6, dwell_ticks=2,
            sensory_refs=["mic:live"],                  # <- hardcoded literal, always
            **self._affect_kwargs())
```

Two specific findings:
- `deterministic_motif_id("mic_stream")` — the motif ID seeded from a **fixed literal
  string**, identical for every call regardless of source or actual acoustic content.
  Content only influences `chi` (`winding % 100`, from the real krimelack transduction of
  whatever samples were decoded) — the motif identity itself does not vary.
- `sensory_refs=["mic:live"]` — a **hardcoded literal tag**, applied unconditionally.
  Self-voice bindings are tagged `"mic:live"` exactly like a genuine live microphone
  capture. Nothing in the atlas record distinguishes "I said this to myself" from "I heard
  this from the room."
- `_affect_kwargs()` (line 1470) contributes engine-wide affect state (arousal, valence,
  surprise, need_pressure) — global, not source-specific. No help here either.

**The only way to tell them apart today is inference, not data**: cross-reference a
`sound_frame_bound` event's tick against nearby `emission`/`self_heard` events, and note
that self-voice's `duration_s` (a short reply, ~1-1.5s at espeak's `-s 145` rate) is
characteristically much shorter than a 5-second mic chunk. This is exactly the method I
used in `GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1.md` to correctly exclude 11
self-voice samples from that report's speech/silence evidence. It is not implemented
anywhere in the codebase as an actual distinguishing signal — an analyst has to do it by
hand, every time, and it is easy to get wrong (I nearly reported those 11 samples as
successful live-mic decodes before checking).

## 4. OBSERVATIONS FOR D2 (not recommendations — read-only per this dispatch's scope)

- If D2 wants to reason about "what she heard" vs "what she said," the binding layer
  currently gives it nothing to work with — both are the same tag on the same motif ID.
  A source-aware variant of `process_sound_frame` (or a `source` kwarg threaded through to
  `_atlas_record`) would be the natural place to add this, but that is a real code change,
  out of scope for a read-only forensic.
- The self-voice kill switch being shared with text self-hearing means anyone wanting to
  silence her own-voice-reflection specifically (for a design experiment, or to reduce
  atlas noise) currently has to also silence the text-level self-hearing mechanism, which
  is a different and probably unwanted side effect.
- `espeak-ng`'s voice parameters are hardcoded (`en+f3`, pitch 96, speed 145) inside the
  closure — no config surface. Relevant if D2 ever wants to vary or characterize her voice.

---

## STATE

Read-only, no code touched. Filed for the D2 design conversation.

End report.
