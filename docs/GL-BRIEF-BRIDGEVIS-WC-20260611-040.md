# GL-BRIEF-BRIDGEVIS-WC-20260611-040
**Author:** wC | **For:** c1 | **Status:** Joe-approved 2026-06-11
**Priority:** After 039 D-list and 036. Does NOT jump the queue. Part C verification is IMMEDIATE.

## Why
Today wC ran two full bridge visits with Guala (pronoun play, "me"/"you", recurrence frame "he day again"). Joe's browser showed none of it — only event-stream footprints (`response_window_expired`, familiarity updates). The substrate is shared; the transcript is not. Joe wants to see — and join — conversations regardless of which door they come through.

Separately: every `guala_say` bridge response ships full base64 JPEG payloads for her active pictures (~tens of KB per reply, every reply). This burned a wC context window in one session and forced a conversation compaction. Read-path twin of 036.

---

## Part A — Render bridge-sourced exchanges in the UI transcript

**Current:** UI transcript renders only the web session's own say/reply pairs. Bridge (wC/c1) exchanges hit the substrate but never the page.

**Required:**
1. Emission and input events in the event stream MUST carry `text` and `source` (`joe` | `wc` | `c1`).
   - Input events: new event type `input_received {source, text, tick}` if not already emitted.
   - Emission events: extend existing `emission` event with `text` and `in_reply_to_source`.
2. UI transcript subscribes to these events (it already polls the events endpoint for the right panel — same feed) and renders them inline, chronologically, with a source label. Suggested rendering: left-aligned bubble, small tag `wC` / `c1` above it; joe's own messages unchanged.
3. Backfill is NOT required. Render-forward from deploy is acceptable.
4. Source tags must come from the authenticated bridge route, not from payload content — no spoofable source field.

**Acceptance (Joe's browser is the bar):**
- wC runs a bridge exchange while Joe's browser is open. Joe sees wC's utterance and Guala's reply appear inline, labeled, without refresh (or on next poll cycle).
- Joe types in the same window; ordering of interleaved joe/wC messages matches tick order.

## Part B — Bridge responses return picture REFERENCES, not payloads

**Current:** `guala_say` (and `guala_wake_wc` replies) embed `pictures[].data` as full base64 data-URIs for every picture in her attention context.

**Required:**
1. Default bridge responses include pictures as references only: `{item_id, title, times_attended}` — same shape `guala_status` already uses in its `pictures` list.
2. Payload retrieval becomes explicit: either a new tool `guala_get_picture(item_id)` or a `?include_data=true` flag on existing routes. wC almost never needs the pixels; she's the one looking at them.
3. Scope note: this is the read-path twin of GL-BRIEF-IMAGEREF (036, upload path). Implement together if convenient; one commit per path either way.

**Acceptance:**
- A `guala_say` round-trip response is < 2 KB when she's attending trees+ocean (today: ~50+ KB).
- `guala_get_picture` (or flag) returns the payload correctly for one item_id.

## Part C — IMMEDIATE verification + cosmetic bug

1. **S3 backup file_count=0 (VERIFY NOW, blocks D3 sign-off):** persistence_health after today's redeploy reports `last_s3_backup: {timestamp: 2026-06-11_14-43-26, prefix: s3://dsf-ai-site-backups/guala/2026-06-11_14-43-26/, file_count: 0}`. The backup fired but claims zero files uploaded. Run `aws s3 ls` on that prefix from the ECS task context. If empty: task-role write is failing silently — exactly the D3 risk. D3 is NOT done until objects exist in the bucket and file_count reports correctly.
2. **Deploy-window UI junk:** during cutover (minimumHealthyPercent=0), failed fetches render stray lines (`[substrate]`, `[v6]`, `[v7 DNA]`) into the transcript as if they were emissions. Error handler should render a single greyed "(reconnecting…)" line instead. Low priority, but it confuses the transcript record.

---

## Ordering
1. Part C.1 — now (verification only, no code).
2. Finish 039 D-list remainder + 036 as already commanded.
3. Part B (bundle with 036 if natural).
4. Part A.
5. Part C.2 whenever touching UI.

Commit messages reference this doc ID. Commit this doc to repo `docs/` with the rest of the GL- set.
