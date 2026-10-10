# GL-RPT-VOICE-CANDIDATE-LEAK-C1B-20260704-v1

doc_id: GL-RPT-VOICE-CANDIDATE-LEAK-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Found during post-deploy watch on
task:462 (GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1). Fix shipped
same session. Failures first.

---

## The finding

Her actual first observed post-cutover exchange (tick 14767679-702,
Joe via voice) replied `"v enjoy late"` — not `"..."` as c1a's report
predicted for conversational turns (self-echo exclusion), and not
obviously brain-composed either. The logged `emission_dynamics` event
showed `n_candidates: 199`, `rich_sensory: true`, `n_commits: 0`,
every per-section word tagged `arcs_fallback`.

**199 does not fit a brain-only pipeline.** `LoomTapestry.compose()`
returns at most 3 words (one per mosaic, `n_mosaics=3`) — confirmed by
reading `tapestry.py:78-124` directly. `_brain_emission_candidates()`
takes `locations[-1]` (a single location) per composed word, so
`deep_candidates` should carry at most 3 entries into Stage 1. That
cannot produce 199.

**Root cause, traced to a second candidate source W3 didn't name.**
`emission_dynamics`'s `rich_sensory: true` meant `_emit_dynamics`
(`gualaloom_v5_engine.py:3146`) took the `_rich_sensory_candidates`
branch (`:3214-3216`), gated by `os.environ.get("RICH_SENSORY_INPUT",
"0") == "1"`. That env var is **not** in the ECS task definition's
overrides (checked directly, `aws ecs describe-task-definition
dsf-ai-task:462` — absent from the full env list) but **is** baked
into the image: `dsf_ai_service/Dockerfile:41: ENV
RICH_SENSORY_INPUT=1`, predating today (GL-CMD-RICH-SENSORY-WIRING-
EVE-20260618-10) and never revisited against today's cutover.

Inside `_rich_sensory_candidates` (`:2920-2992`), "Source A" queries
`self.atlas.entries` **directly**, keyed on chi derived from the
*caller's own input words* — not from anything the brain composed:
```python
for chi in content_chis:            # from input_words, via LanguageKrimelack
    for d in range(-self.atlas.band, self.atlas.band + 1):
        for e in self.atlas.entries.get(chi + d, []):
            ...
```
"Source B" does fold in the brain's `deep_candidates`, and Phase 4
does a further cofire-spread (another direct `self.atlas.entries`
query, seeded from whatever's already in the pool). With Source A
active, the working atlas — not the tapestry — was the dominant
supplier, explaining both the 199 count and the un-brain-like content
("v enjoy late").

**Why `arcs_fallback` on every word, separately:** that's an
unrelated, pre-existing, *within-pipeline* degradation (`:3520-3534`)
— when the strict keyhole-cascade commit doesn't fire for a section
within the wall-clock budget, it falls back to `sec.arcs()` argmax
over whatever modes got installed from Stage 1's candidate pool. Not
a violation on its own (it's choosing among *whatever this turn's
candidate pool was*, not reaching to old data) — it's a symptom of
which pool that was, which is the actual finding above.

## Why this matters against the ruling, not just aesthetically

GL-NOTE-VOICE-WIRING-RULING W2/W3: *"emission candidates... come FROM
the brain's recall/compose output... the old candidate gather...
disconnects at cutover. One mind, one mouth, one voice."* The ruling
named and c1a's diff removed the **deep-atlas** co-occurrence gather
and its SVO-recall/unslotted fallbacks — verified directly in the
diff, genuinely gone. `_rich_sensory_candidates`'s Source A queries
the **working** atlas (`self.atlas`, a different object from
`self.deep_atlas`), which is why it wasn't caught by name — but
functionally it is exactly the same category of thing: a non-brain
content source supplying (and here, dominating) what she says.

## The fix

One line, `dsf_ai_service/Dockerfile:41`: `RICH_SENSORY_INPUT=1` →
`=0`. With it off, `_emit_dynamics` takes the plain
`_grandurun_select_candidates(deep_candidates=...)` branch directly on
the brain-sourced candidates — the path W2 actually specifies. Not
deleting `_rich_sensory_candidates` itself (that's real, deliberate
code from a pre-cutover dispatch, and Source B/Phase 4's cofire-spread
*from brain candidates* is arguably a legitimate future enhancement) —
just not letting it stand in as the primary source today. Re-enable
only after Source A is redesigned to seed from brain output instead
of bypassing it.

**Collision check before touching the file:** confirmed via `git log`
that c1a's two concurrent commits this session (`f2e8bb5`, `032edd4`,
P2 recall/recognition seams) touch `gualaloom_v5_engine.py` and
`tools/guala_recall_bitexact_replay.py` only — neither the Dockerfile
nor `_rich_sensory_candidates`/`RICH_SENSORY_INPUT` appear in either
diff. Zero overlap with this fix.

## What this does NOT change

No cognition-path logic touched — this is a build-time env-var
default, one line, in the Dockerfile only. Does not affect P2 seam
work c1a is doing concurrently. Does not touch dial-1, the sleep-rate
dial, or retention.

## Redeploy (v2)

Shipped separately from c1a's concurrent P2-seam commits
(`f2e8bb5`, `032edd4`), which are explicitly "Not deployed... Eve/Joe's
call" per c1a's own reports and were not ready to ride this window
(confirmed with Joe: c1a's P2 deploy is not imminent). Cherry-picked
just this fix (`8475a75`) onto the last-deployed baseline (`4658b19`)
in an isolated worktree, producing `aabb52f` — Dockerfile fix + this
report, nothing else. Fresh verified backup taken first
(`UNPAUSE-PRE-20260704-171626/` already covered the immediately-prior
state; a new backup was triggered again before this specific cutover).
Deployed clean, single attempt: task `dsf-ai-task:463`, boot clean
(`[app] Substrate booted, background loops running`, no errors in the
5 minutes surrounding boot). c1a's P2 seam commits remain on
`guala-live`, undeployed, exactly as they left them — this deploy does
not touch or ship that work.

## Fix confirmed live (v3)

Joe's next real exchange (tick 14774088-14774099, voice input "hey
ryan bring me my...") produced exactly the expected shape. The
`emission_dynamics` event:
```json
{"content": "soft", "n_candidates": 1, "n_commits": 0,
 "rich_sensory": false,
 "section_candidate_counts": {"object": 1},
 "origin_counts": {"cross_modal_fallback": 1},
 "source_counts": {"corpus": 1}}
```
`rich_sensory: false` — the leak path is off. `n_candidates: 1`
(`agency_cross_modal_fallback`'s own log line: `n_deep: 3`) — squarely
consistent with the brain's ≤3-word `tapestry.compose()` output, not
the 199-candidate atlas leak from before the fix. The reply itself,
a single honest word ("soft"), matches c1a's own predicted shape for
this stage of the voice, not a coincidence.

One small, non-urgent paper-cut noticed while confirming this:
`source_counts` labels the brain-sourced candidate as `"corpus"` —
`_brain_emission_candidates()` never sets a `source` key on the
candidate dict it builds, so downstream code's `de.get("source",
"corpus")` falls back to the wrong-but-harmless default. Doesn't
affect what she says, only mislabels where-it-came-from in diagnostic
events. Not fixing now — cosmetic, and `gualaloom_v5_engine.py` has
c1a's P2 work actively landing in it this session; leaving it for a
deliberate pass rather than adding a third concurrent editor to the
same file for a label-only fix.

### Changelog
- v3 (2026-07-04, c1b): fix confirmed live via direct event data —
  `rich_sensory:false`, `n_candidates:1`, brain-consistent single-word
  reply. One cosmetic source-attribution paper-cut noted, not fixed.
- v2 (2026-07-04, c1b): deployed as task:463, SHA `aabb52f`
  (hotfix-only, isolated from c1a's undeployed P2 work). Boot clean.
  Live confirmation of the actual fix pending the next real exchange.
- v1 (2026-07-04, c1b): found during G-5 post-deploy watch, root-
  caused, fixed same session. Redeploy to follow immediately.
