> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-COGNITION-METER-C1-20260704-166-v1

doc_id: GL-RPT-COGNITION-METER-C1-20260704-166-v1
From: c1a | To: Eve, Joe
Responds to: GL-CMD-COGNITION-METER-EVE-20260704-166-v1 (Step-0 filed
`cec63d9`). Merged deliverable with GL-CMD-WIRING-AUDIT-EVE-20260704-164-v1
— see GL-RPT-WIRING-AUDIT-C1-20260704-164-v1 for the full per-mechanism
evidence this panel's rows are sourced from.

---

## Failures first

1. **Joe's own confirmation is still outstanding** — per the CMD's own
   G-166-1, the final gate is his screen, not curl. I've verified the
   panel is being served (below); I have not verified it reads well,
   scrolls sensibly, or avoids jargon at his actual seat. That's his
   gate, explicitly, not mine to claim.
2. **One row genuinely stayed at a nuanced, non-binary state past v1.1**:
   "day-cycle / sleep trigger" is INVESTIGATING, pointing at -165 — that
   dispatch (addressed to whichever seat is free) was not executed by
   me this session; the row honestly reflects an open investigation,
   not a resolved one.
3. **No live-data wiring in v1/v1.1** — every row is static text sourced
   from filed reports, not a value pulled fresh from `guala_status` on
   each page load. This satisfies "reads only what already exists" (the
   underlying facts are all sourced from real audit work, most of it
   cross-checked against live telemetry before being written down — see
   -164's own two live corrections), but it means the panel will go
   stale the next time something changes and won't auto-refresh; a
   future version could wire a handful of rows (recall's hit-rate,
   retention's promotion counts) to the same `pollStatus()` payload the
   rest of the page already fetches. Not built this round — flagging as
   a real gap, not deciding it silently.

---

## What shipped

**v1** (`00521b4`, S3-synced, CloudFront-invalidated, curl-verified
before v1.1 replaced it): the panel structure — title, 22-row table,
CONNECTED/FIRING/LAST IMPACT columns — with all 15 plan-mechanism rows
UNKNOWN/gray and the 7 machinery rows pre-populated exactly as -166
specified them (aware gate SEVERED, intro gate SEVERED, deliberation
stage OFF-queued, day-cycle/sleep INVESTIGATING, curriculum feeders
SEVERED, play ABSENT, teaching-survives-to-sleep WATCH-LIST). Shipped
**before** any of this session's -164 audit work was written up, per
the CMD's explicit sequencing ("ship first, watch it fill").

**v1.1** (`e2290fa`, same deploy pipeline, curl-verified): all 15
plan-mechanism rows filled in from this session's -164 findings. Two
of those are **live corrections** — findings that were wrong under
static code/config analysis alone and were caught by cross-checking
against actual live telemetry before they ever reached the panel:

- **feelings-deepen-memory**: the written plan says "gate matched ZERO
  times ever." A live event sample this session caught `nmda_affect_match`
  firing 66 times in a single emission. The row now reads
  "fired 66 times in a single live emission just observed... this is
  NOT the 'never fires' the written plan currently says; the plan is
  what was stale, not her."
- **organ influence on speech / episodic story-binding**: research
  first concluded the episodic-binding flag (`HEMI_EP_ENABLED`) was off
  everywhere checked (deploy script, live ECS task definition) — both
  genuinely showed no such variable. A live `hemisphere_update` event
  with real, nonzero `turn_log`/`tracked_objects` counts sent me back to
  the `Dockerfile` specifically, which bakes `HEMI_EP_ENABLED=1` (and
  three siblings) into the image itself — a third place env vars can
  live that neither check covered. The episodic-binding half is live;
  the **organ**-influence half of that row stays SEVERED, independently
  confirmed by the same live sample (`organ_in_commits: false`).

Both corrections are named explicitly in the panel's own commit
message and in -164's report, not quietly folded in — the CMD's whole
point is that a wrong "CONNECTED: YES" on Joe's real screen is exactly
the kind of decoration this effort exists to prevent, so getting caught
being wrong and saying so plainly is the mechanism working, not a
footnote to bury.

**Placement**: a new full-width strip below the header, visible on all
screen widths (unlike `#state-panel`, which is `display:none` below
700px) — chosen because "P0-visibility, ordered by Joe" argues against
hiding this in the one panel that's already invisible on narrow
screens. Collapsible (click the header row), default expanded. A live
row-count ("N/22 audited") updates from the same static array, so
progress is visible at a glance without re-reading every row.

---

## Verification performed (curl, not Joe's screen — stated per G-166-1)

```
v1:   curl https://dsf-ai.com/gualaloom.html | grep -c "cogmeter-panel|Cognition Meter|COGMETER_ROWS"  → 8 (non-zero, present)
v1.1: curl https://dsf-ai.com/gualaloom.html | grep -A3 "feelings-deepen-memory"  → the corrected row text, live
```

Both deploys: `aws s3 cp` (targeted single-file, not a full directory
sync, since `git diff --stat -- dsf_ai_service/static/` confirmed
`gualaloom.html` was the only changed static file both times) +
`aws cloudfront create-invalidation` on `E17JT9XGBFU493`, waited for
`invalidation-completed` before curling. No ECS/task-definition/
substrate deploy — pure static-page pipeline, exactly as the CMD's
Vehicle specified ("No substrate deploy needed for v1").

`node --check` run against the extracted inline `<script>` block after
each edit — syntax-valid both times, before shipping.

---

## Standing rule (recorded per the CMD, not yet exercised)

"Any newly discovered mechanism, and any new mechanism ever built, gets
a meter row in the same dispatch that discovers or builds it. No row,
no ship." Noting here that this rule is now live and binding on future
work — including, if it proceeds, the voice-to-words trace Joe just
routed toward this seat, which per this same standing rule should ship
its own meter row (voice-to-words) as part of that fix, not as an
afterthought.

---

## Gates

**G-166-1** — Panel live at Joe's seat before -164's audit completed:
**PASS** (v1 shipped and curl-verified before -164's report was
written). Joe's own screen confirmation: **outstanding**, his gate.

**G-166-2** — Every non-gray cell traces to evidence: **PASS**. The 7
machinery rows trace to their named dispatches (-156, -160, -161,
-162, -163, -165); the 15 mechanism rows trace to -164's Part B, with
the two corrected rows additionally citing the live sample that
corrected them.

**G-166-3** — "No live counter exists" rendered wherever true: **PASS**
— cross-sense recall, recognizing-things-in-new-forms, order/sequence,
who-tags, and the machinery "play" row all say so plainly rather than
being left blank or inferred.

**G-166-4** — §10 honesty, no decoration, severed is red: **PASS**.
Severed rows render in the existing `--nmda-block` red used elsewhere
on the page (same color already meaning "blocked" at the NMDA-gate
dots); unknown/absent render muted gray; nothing is smoothed toward a
brighter reading than the evidence supports.

---

## Status

Filed. Panel live, two versions shipped and curl-verified this session,
Joe's confirmation pending. Standing rule recorded and already informing
the next piece of routed work (voice-to-words) rather than being a
dead letter. No further updates planned this session unless -165 or
another -164-adjacent finding lands before this session ends, in which
case the corresponding row updates per the CMD's population rule.
