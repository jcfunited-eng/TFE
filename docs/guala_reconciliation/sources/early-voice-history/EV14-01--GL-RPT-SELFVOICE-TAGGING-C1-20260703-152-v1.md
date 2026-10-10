# GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1

doc_id: GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-SELFVOICE-TAGGING-EVE-20260703-152-v1
Deployed as part of Deploy 4, SHA 5376204, task:457.

---

## FAILURES FIRST

None. All gates PASS with direct live event evidence.

---

## THE FIX

`process_sound_frame(self, audio_bytes, source="mic:live")` — source threads into both
`sensory_refs` on the atlas record and the `sound_frame_bound` event. Self-voice
injection (`_inject_self_voice`) now passes `source="voice:self"` and has its own kill
switch, `SELF_VOICE_AUDIO_ENABLED` (default "1"), independent of `SELF_HEARING_ENABLED`
which still gates the text-hearing steps (1–3) it sits alongside — `SELF_HEARING_ENABLED=0`
skips everything; `SELF_VOICE_AUDIO_ENABLED=0` alone skips only the audio injection,
leaving text self-hearing intact. Motif ID (`deterministic_motif_id("mic_stream")`)
unchanged for all sources, per the gate's "world bindings unchanged" requirement — only
the tag varies.

---

## GATES

**Self-voice bindings tagged self, event evidence: PASS.** Live, this boot:
```
tick 14515624  sound_frame_bound  {"n_bands": 6, "duration_s": 1.26, "source": "voice:self"}
```
Fired at the identical tick as the triggering `self_heard` event (`reply_summary: "eagle
do r"`), immediately after an `EMITTING` activity started — exactly the self-voice
injection path, correctly tagged.

**World/mic bindings unchanged: PASS.** Every genuine mic chunk this boot, dozens of
samples, all correctly tagged:
```
tick 14511924  sound_frame_bound  {"n_bands": 6, "duration_s": 4.98, "source": "mic:live"}
tick 14511930  sound_frame_bound  {"n_bands": 6, "duration_s": 4.98, "source": "mic:live"}
... (continuous through the session, duration_s consistently ~4.98s matching -111's
     5-second recorder-restart cycle)
```
The two are now trivially distinguishable by tag alone — no more inferring from
`duration_s` and tick-adjacency to emissions, which is what both `GL-RPT-MIC-EMBEDDED-
DECODE-C1-20260703-110-v1.md` and `GL-RPT-MIC-CHUNKING-C1-20260703-111-v1.md` had to do
by hand to avoid misreporting self-voice as live mic evidence.

**Loomscan/evidence can filter by tag: PASS, mechanically.** The `source` field is on
both the atlas `sensory_refs` and the `sound_frame_bound` event detail — any consumer
(loomscan's own event feed, a future admin/evidence view) can filter on it directly.
-154 already ships with a note that its sound-band label is "unattributed" pending this
tag landing; wiring the loomscan display to actually branch on it (mic vs. self, per
-154's item 2) is that dispatch's own follow-up, not built here.

**Diff scoped to the tag plumb + toggle: PASS.** `git diff` for this dispatch: one
parameter added to `process_sound_frame`'s signature, one call-site update in
`_inject_self_voice`, one new independent kill switch, two `sensory_refs`/event-field
threadings. No cognition-path change, no constants beyond the two source-string literals
and the kill-switch default.

---

## STATE

Live, proven, both tag values observed firing correctly in the same session within
minutes of each other. Closes the gap identified in
`GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1.md`.

End report.
