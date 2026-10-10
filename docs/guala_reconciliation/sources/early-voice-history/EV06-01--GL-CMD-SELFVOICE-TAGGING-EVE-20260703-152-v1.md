# GL-CMD-SELFVOICE-TAGGING-EVE-20260703-152-v1

doc_id: GL-CMD-SELFVOICE-TAGGING-EVE-20260703-152-v1
From: Eve | To: c1b | Vehicle: Deploy 4 (tonight's sleep_for_deploy, one wake cycle).
Spec: inline, per Eve's dispatch message 2026-07-03 (this document is that text,
committed verbatim per Step 0).

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## -152 SELF-VOICE TAGGING

`process_sound_frame` gains a `source` parameter (default `"mic:live"`); the espeak
self-voice injection passes `source="voice:self"`; `sensory_refs` carry it; independent
kill switch for AUDIO self-voice separate from text self-hearing.

## Gates

- Self-voice bindings tagged self (event evidence).
- World bindings unchanged.
- Loomscan/evidence can filter by tag.
- Diff scoped to the tag plumb + toggle.

### Changelog
- v1 (2026-07-03, Eve): from `GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1.md`'s finding —
  self-voice and live-mic bindings were previously indistinguishable (same hardcoded
  motif_id + sensory_refs, no source parameter anywhere in the chain).
