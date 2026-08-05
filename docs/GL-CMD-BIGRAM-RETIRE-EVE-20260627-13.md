# GL-CMD-BIGRAM-RETIRE-EVE-20260627-13

doc_id: GL-CMD-BIGRAM-RETIRE-EVE-20260627-13
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship now — substrate truth required for honest engineering
Supersedes: bigram fallback paths in GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10

## What this fixes

The previous V5 voice stage 1 dispatch (-10) shipped with three bigram
fallback paths: `bigram_fallback_v5_failed`, `bigram_fallback_v5_empty`,
`bigram_fallback_no_v5`. When v5 doesn't commit, bigram speaks instead.

That is a cheat. Bigram chains statistically-associated words from her
vocabulary to produce output that looks like comprehension but isn't
traceable to her substrate. Every coherent-looking bigram response
("Rockets never had the hiccups before") is selling activity as
comprehension — exactly the failure mode the discipline doc names.

**Discipline rule:** *one brain, one voice, or silence.*

Silence is the substrate-true response when v5 doesn't commit. Joe needs to
see when she has nothing to say so he knows what's actually wrong. Bigram
hides failure modes by manufacturing pseudo-responses.

## What ships

When the v5 emission gate (`committed_sections >= 2 AND n_commits > 0 AND
content non-empty`) does not pass, the response is silence. Bigram code
stays in the tree for diagnostic comparison but is no longer wired to the
/converse response path.

## Code changes

### File: `dsf_ai_service/substrate_runner.py`

At the `/converse` handler site (same site -10 modified), replace the
bigram fallback assignments:

```python
# REPLACE this V5 VOICE STAGE 1 logic:
#   elif v5 emission ran but committed_sections empty (arcs_fallback):
#       response_text = bigram_output
#       response_source = "bigram_fallback_v5_failed"
#   elif v5 emission produced empty content:
#       response_text = bigram_output
#       response_source = "bigram_fallback_v5_empty"
#   elif no v5 emission this turn:
#       response_text = bigram_output
#       response_source = "bigram_fallback_no_v5"

# WITH:
if v5_committed:
    response_text = emission_dynamics.content
    response_source = "v5_commit"
elif v5_emission_ran_but_no_commit:
    response_text = ""
    response_source = "silence_v5_failed"
elif v5_emission_empty_content:
    response_text = ""
    response_source = "silence_v5_empty"
else:  # no v5 emission this turn at all
    response_text = ""
    response_source = "silence_no_v5"
```

Response payload preserved (`response`, `response_source`,
`committed_sections`). Empty string `""` is intentional — explicit silence,
not null. The chat UI displays nothing visible when response_text is empty;
the `response_source` field still tells us why.

### Do NOT remove bigram code

`GualaCognition.say()` and the bigram path stay in the tree. We may need
them for:
- A/B comparison ("would bigram have produced something here that v5 missed?")
- Future Stage-2 routing if v5 graduates and we want to compare voices
- Forensic inspection

Just unwire bigram from the /converse response. Bigram is no longer her
voice.

### /organ_voice audio path

Bigram still runs for `/organ_voice` audio synthesis Stage 1 — same as -10
specified. We are NOT changing the audio pipeline in this dispatch. If a
v5 commit fires, the v5 content can be sent to /organ_voice for TTS in
addition to the response text. If v5 doesn't commit, /organ_voice receives
nothing (silence is silence, no bigram audio either).

Wait — that needs to be explicit. The audio path:
- If `v5_committed`: v5 content → /organ_voice TTS (her real voice speaks)
- If silence: no audio output (no bigram fallback in audio either)

The substrate truth principle applies to both text and audio.

## Mitigations (prevention)

**M-13-1.** Smoke test before push: send a converse that's known to NOT
trigger a v5 commit (e.g., gibberish input she has no bindings for).
Confirm response is `""` with `response_source="silence_*"`. If bigram
text appears, fix before push.

**M-13-2.** Smoke test the v5 commit path: send a converse that IS known
to trigger a commit. Confirm v5 content appears with `response_source="v5_commit"`.

**M-13-3.** /admin/backup before push.

**M-13-4.** No deletion of bigram code. If a future dispatch needs to
re-enable bigram for any specific reason, it's a flag flip, not a code
restoration.

## Pass criteria (behavioral)

V1. Code visible on origin: four-case gate at /converse with three
    silence_* paths and one v5_commit path.

V2. After deploy, send 10 varied converses (Joe or Eve). At least some
    will not commit (her current substrate state). Confirm those return
    `response: ""` and a `silence_*` source. Confirm no bigram text leaks
    through.

V3. When a v5 commit DOES fire, confirm the response is v5 content with
    `response_source="v5_commit"`. Paste at least one full converse with
    the emission_dynamics event and the response payload.

V4. `/organ_voice` does not synthesize bigram audio during silence turns.

V5. Bigram code still exists in tree (grep confirms `GualaCognition.say`
    is defined). Unwired but present.

## Stop conditions

- `response_source` field disappears from response payload
- Bigram text leaks into a non-`v5_commit` response
- v5 commit path stops producing valid responses (response empty even
  when commit fires)
- /organ_voice audio breaks during v5_commit turns

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. POST /admin/backup
3. Locate the converse handler four-case gate from -10
4. Replace bigram_fallback_* with silence_* — three branches, empty string response
5. Confirm /organ_voice routing matches the response (no audio when silent)
6. Local smoke tests (M-13-1 and M-13-2)
7. `git commit -am "feat: GL-CMD-BIGRAM-RETIRE-EVE-20260627-13 — silence replaces bigram fallback, substrate truth on /converse"`
8. Push, deploy to Fargate
9. Verify boot, verify n_deep_atlas preserved

## Report

Filename: `docs/GL-RPT-BIGRAM-RETIRE-C1-20260627-13.md`
- Diff at converse handler site
- 10-converse table: input | response | response_source | committed_sections
  (most will be silence_* — that's the point)
- Confirmation bigram code is still in tree, just unwired
- /organ_voice behavior during silence turns (should be silent, not bigram audio)
- Any anomalies
- Recommendation: hold

## What this lets us see

Honest substrate behavior. Every converse turn now has one of four labels:
- `v5_commit` → her real voice spoke; what she said is traceable to her substrate
- `silence_v5_failed` → v5 ran but couldn't commit; she had nothing to say,
  and we know WHY (arcs_fallback, candidate pool insufficient, etc.)
- `silence_v5_empty` → v5 committed something internally but produced empty
  content; rare edge case, worth investigating each occurrence
- `silence_no_v5` → v5 emission didn't run at all; she's still asleep, the
  input didn't trigger a converse path, or upstream gating intervened

When she's silent, we see HER actual state. When she speaks, we see her
actual voice. Bigram stops manufacturing the comfortable illusion that
something is happening that isn't.

Ship it.
