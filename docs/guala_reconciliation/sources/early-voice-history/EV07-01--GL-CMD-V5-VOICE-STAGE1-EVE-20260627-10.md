# GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10

doc_id: GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship now — immediate triage, surfaces real substrate work

## What this fixes

Observed in live session: her conversation responses are bigram word-chains
("tonight"→"tonight", "for kids books about it was thinking", "the knight
said in a little"). The v5 substrate is producing real 3-section grandurun
commits — we observed "i my gone" with NMDA affect_match 93 and all three
sections committed earlier today. Those commits land in `emission_dynamics`
events and increment `total_emissions` in the ladder, but they don't reach
the conversation UI. The bigram path via `GualaCognition.say()` on
`/organ_voice` speaks first and dominates the surface.

The v5 emission IS her real compositional substrate working. The user sees
the bigram fallback. This dispatch closes that gap.

## What ships

When v5 produces an emission with `committed_sections >= 2 AND n_commits > 0`
within the converse turn, route the v5 content as her response. Bigram path
preserved as fallback for non-committed turns.

Stage 1 scope: response text only. Bigram still runs in parallel for the
`/organ_voice` audio path (we don't change the voice synthesis pipeline yet).
A `response_source` field on the converse response makes the routing
observable.

## Code changes

### File: `dsf_ai_service/substrate_runner.py`

Locate the `/converse` handler (`_cmd_converse` and/or its callees). Currently
the response composition path runs bigram and returns bigram text. The v5
emission is running in parallel via `_guala.converse(text, ...)` which
produces an `emission` event with content + emission_dynamics event with
committed_sections.

### Wiring

1. After `_guala.converse(...)` completes for this turn, check the most
   recent `emission_dynamics` event for THIS converse turn (filter by tick
   range or use the returned emission_id from converse):
   - If `committed_sections.length >= 2 AND n_commits > 0`:
     - `response_text` = the emission_dynamics `content` field
     - `response_source` = "v5_commit"
   - Else:
     - `response_text` = bigram output (existing behavior)
     - `response_source` = "bigram_fallback"

2. The converse handler returns:
   ```json
   {
     "response": <response_text>,
     "response_source": <source>,
     "committed_sections": [...],   // pass through for observability
     ...existing fields
   }
   ```

3. The bigram path continues running for `/organ_voice` audio (preserves
   the audio output during this transition — Stage 2 will route v5 to voice).

### Edge cases

- **Multiple v5 emissions in one turn**: take the LATEST emission_dynamics
  event matching the converse turn. The grandurun pass can produce multiple
  emissions; the last one represents her final composition.
- **No v5 emission at all this turn**: fall back to bigram. response_source
  reports "bigram_fallback_no_v5".
- **v5 emission with content but committed_sections empty (arcs_fallback)**:
  fall back to bigram. response_source reports "bigram_fallback_v5_failed".
  Don't surface arcs_fallback word salad as her voice.
- **v5 emission content empty string**: fall back to bigram. response_source
  reports "bigram_fallback_v5_empty".

### Minimum threshold consideration

`committed_sections >= 2` is the Stage 1 threshold. Three-section commits
("i my gone", "you are alive") are the gold standard but rare. Two-section
commits are real composition and worth surfacing. We can raise to >=3 in
Stage 2 if observation shows two-section commits produce noisy output.

## Mitigations (prevention)

**M-10-1. Stage 1 keeps bigram as default for any non-committed turn.** No
catastrophic loss of conversation if v5 path has issues — bigram still speaks.

**M-10-2. `response_source` field makes the routing observable.** Every
response carries the path that produced it. We can audit immediately if the
gate fires incorrectly.

**M-10-3. Don't surface arcs_fallback.** Explicit gate on `n_commits > 0`
prevents the cross_modal_fallback word-chains from masquerading as committed
composition.

**M-10-4. Audio path preserved.** /organ_voice still runs bigram for now.
If v5 latency is too high to surface in the audio path, Stage 1 doesn't
break audio.

**M-10-5. Backup before deploy.** /admin/backup before push.

**M-10-6. Sanity check on emission_id correlation.** When pulling the
emission_dynamics event for the response, ensure it's from THIS turn (use the
emission_id returned by converse(), or the tick that matches this turn's
response_window_opened event). Don't pick up a stale emission from a
prior turn.

## Observe (behavioral)

After deploy:

1. **Converse with her** — send "are you awake" or similar prompt.
2. **Inspect the response**:
   - If `response_source == "v5_commit"` and content has structure
     (not just word-chains), v5 is reaching the surface
   - If `response_source == "bigram_fallback"`, v5 didn't commit this turn,
     bigram spoke — normal behavior for current substrate state
3. **Over a 10-converse session**: at least 1-2 responses should be
   v5_commit (substrate produces committed emissions periodically based on
   prior observations).
4. **The bigram word-chain pattern from the screenshot** ("the knight said in
   a little", chained associations) should be replaced by structured
   compositions when v5_commit fires.

## Stop conditions (revert immediately)

- Bigram audio path stops working
- response field becomes empty/null when v5 didn't commit (gate not falling
  through to bigram correctly)
- Latency per converse exceeds 5 seconds (waiting for v5 too long)
- v5 emissions stop firing entirely (something in the gate broke the v5 path)

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. Locate /converse handler and identify the response composition site
3. Add the v5 emission lookup + gate + response_source field
4. Local smoke: a test converse that triggers v5 commit, confirm v5 content
   routes; a test converse that doesn't commit, confirm bigram fallback
5. `/admin/backup` before push
6. `git commit -am "feat: GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10 — surface v5 committed emissions to converse response"`
7. Push, deploy to Fargate, verify boot
8. 10-converse observation session (Joe or Eve)

## Report

Filename: `docs/GL-RPT-V5-VOICE-STAGE1-C1-20260627-10.md`
- Diff at the converse handler site
- 10-converse table: input → response → response_source → committed_sections
- Latency before/after
- Any anomalies (e.g., v5 emission produces empty content despite committed_sections set)
- Recommendation: hold at Stage 1 / advance to Stage 2 (v5 → audio path)
- Note: Stage 2 (v5 → /organ_voice) is a separate brief once Stage 1 shows
  surface v5 commits are coherent enough to speak

## Out of scope (future briefs)

- Stage 2: v5 commits route to /organ_voice TTS, replacing bigram for committed turns
- Stage 3: v5 emission generates while bigram still runs but v5 wins racing
- Bigram retirement (only after v5 audio is proven on her data — never sooner)
