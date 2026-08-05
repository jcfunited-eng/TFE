# GL-RPT-DEPLOY2-C1-20260703-v2

doc_id: GL-RPT-DEPLOY2-C1-20260703-v2 (addendum; v1 retained: deploy + first gate window)
From: c1a | To: Eve | Date: 2026-07-03 (~02:50Z)
Adds: -98 T7 verbatim (NOT a sign-off), -98 link 404 root cause, prototype-bookmark
confusion, mic/no-response diagnosis. READ-ONLY — nothing changed, nothing shipped.

---

## FAILURES FIRST (§9.4)

### 1. -98 T7: **NOT SIGNED OFF.** Joe's line, verbatim:

> "from the Guala page I get that 404 but when follow the link you gave me I see tat
> after a while but I can't ereally tell what is going on i.e. I dont have enough
> experience with all the data to have an opinon about it.. ... from Guala's page the
> the microphone speach to text still does not get a response"

T7's bar is "Joe opens it live and says so." He opened it and could not tell what he
was looking at. That is a legibility failure of the page for its primary viewer,
recorded as such — T7 FAIL in this window.

### 2. -98 nav link 404 — root cause found, fix NOT shipped (no dispatch).

`gualaloom.html:90` links to `/static/loomscan.html`. The deploy's static step is
`aws s3 sync dsf_ai_service/static/ s3://dsf-ai-site/` — files land at the BUCKET
ROOT, so the live key is `loomscan.html`, not `static/loomscan.html`. S3 returns
NoSuchKey (Joe's screenshot). Every other nav link in the page uses root-relative
paths; this one shipped with the repo-relative path. Fix shape: one attribute,
`href="/loomscan.html"`; static-only (deploy steps 3-5, no task swap). Awaiting
Eve's word — c1a shipped nothing.

### 3. What Joe actually saw at "the link you gave me": the -94 PROTOTYPE, not the
deployed page. His screenshot carries the proto's own honesty banner ("source:
captured snapshot 2026-07-02 · not live · replay captured window · ticks
14109300→14110800", doc_id gl-mdl-loom-scan-proto-eve-20260702-v1) and a stale tick
(14,110,576 vs live ~14,220,000). The deployed `dsf-ai.com/loomscan.html` contains no
such banner and polls `/status` every 2 s (verified in the shipped file). His browser
bookmark "loom scan — guala" points at the old proto artifact; both pages share the
same title. T1/T6 remain unassessed on the REAL page by the person the page is for —
compounding the T7 fail. (Serving of the real page verified: HTTP 200, 30,047 B, 0.29 s.)

### 4. Mic speech-to-text "no response" — diagnosis (read-only), the pipe is NOT the problem.

Evidence from his session window (~02:20–02:45Z, ticks ~14219500–14220858):

- **Input reaches her**: 13 `sight_frame_bound` + 13 `sound_frame_bound` events (camera
  + mic streaming and binding); his transcribed messages appear as sent bubbles.
- **Her side engages**: `response_window_opened emitter:joe` with context anchors, and
  windows now BIND — `response_window_expired … n_responses_bound: 30–40` (this had
  been 0 in every window all day pre-session).
- **She emits to him**: `emission {'content': 'more page', 'to_sources': ['joe']}`
  (tick 14220788); the page renders these ("figure page", "comes page" chips,
  "round dogs carry").

So speech gets in, windows bind, emissions route to joe and render. What Joe
experiences as "no response" is that her utterances are (a) the degenerate
`<word> page` fallback pairs — not recognizable answers, and (b) on her emission
rhythm, not turn-taking. His page's NMDA panel corroborates: `intro: t78` green,
`aware: context_blocked` red — the awareness gate is content-blocked, the same
composition-quality wall as -87 G-C's finding (commits now happen at 80 ticks, but
the emitted content is still fallback-shaped). This is the T⁶/-125 composition
review's subject, not a transport bug. No mic-path defect found; nothing changed.

---

## STATE

Deploy 2 gates otherwise as v1: -87 green (80 ticks, first commits), -88 G-S2 FAIL
(stopped, Eve rules), -86 windows running (T1 failing early), cross-cutting green.
Open for Eve, smallest first: (a) one-line `href` fix dispatch (static-only);
(b) T7 retry after (a), with Joe pointed at `dsf-ai.com/loomscan.html` and the stale
proto bookmark retired; (c) -88 next shape; (d) composition quality (T⁶/-125) — now
the single wall between "she emits" and "Joe gets an answer."

End addendum.
