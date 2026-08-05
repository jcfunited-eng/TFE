# GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1

**doc_id:** GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1
**From:** c1
**Context:** Direct follow-up after both the lock-scope fix (5fd8cca) and
presence-keepalive fix (7f15131) shipped and were confirmed deployed, but
the visible symptom (silent/single-word replies) persisted. The engineer
who shipped the lock fix reported watching it live and confirmed: "the
lock/timing angle wasn't it... the real next step needs someone to trace
exactly which internal timer is actually causing it." This report is that
trace, done with fresh live data, not a re-read of the earlier root-cause
report.
**To:** Eve (routing per standing practice)

---

## Verdict

**There is no timer.** Traced to a specific function, confirmed against
live production telemetry pulled directly off the running task (diary
log, via ECS Exec) for two real conversational turns captured tonight:

- Turn 1 ("What is your favorite thing about the ocean?", 8 words):
  **total_ms=49,363, read_ms=43,645 (88%)**, emit_ms=2,700, recall_ms=156,
  chi_ms=0.4, tag_ms=439. Reply: **"five speech old"**.
- Turn 2 ("tell me a story about a dog", 7 words, source=joe):
  **total_ms=24,829, read_ms=22,900 (92%)**, emit_ms=1,557. Reply: **"old"**.
- Three more samples from the same window: read_ms 77-89% of total, every
  time.

**Cognitive subsystem responsible: read/experience — specifically
`Section.receive()`, called from `read_word()`, called from
`read_sentence()`.** Not recall (156ms — trivial). Not emission-dynamics
settling (1.5-2.7s — small and bounded by a real 3.0s deadline that is
never actually the constraint). The one real deadline in the whole
pipeline, `EMISSION_WALL_BUDGET_S` (3.0s), only governs emission and was
directly ruled out by the live data above.

## Why fix #1 (lock-scope narrowing) didn't help

It's real, correctly implemented, and confirmed genuinely active on the
live path (`CONVERSE_PHASED=1` confirmed in the running task-definition;
`self.lock` is released between words now, not held for a whole
sentence). But it solves a **fairness/blocking** problem between
concurrent callers (camera/mic frame handling, autosave, curriculum) —
it cannot reduce a **single call's own compute cost**. The two operations
this codebase already knows are expensive (`tapestry.expose`,
`organism.experience_word()`) are both non-blocking-enqueued to
background workers and never run inside `self.lock` at all. Section
receive's O(1) fast path is cheap for known words. None of that touches
what's actually slow. This is exactly why someone watching it live,
after this fix landed, correctly concluded "the lock/timing angle wasn't
it" — the fix does what it says, the thing it fixes just isn't the
bottleneck.

## What's actually slow, specifically

Finer-grained `read_sentence_timing` events (same live pull) show the
cost concentrated in two per-word calls:

- `listen_receive`: **8,000-16,000ms per sentence** (roughly 1-2+ seconds
  per word, just for the "listen" section).
- `primary_sections_receive`: 1,000-6,000ms.
- Everything else (transduce, organism_enqueue, phase_dsf,
  salience_role, recognition): sub-10ms combined.

`Section.receive()` has an O(1) fast path for already-known words
(word-identity lookup), but falls back to a full similarity-matrix scan
(`mat @ cur_v`) against **every stored mode in that section** for any
word that doesn't hit the fast path. A preserved code comment
(`GL-BUG-MODES-MATRIX-THRASH`) already documents this exact class of
cost against the "listen" section specifically once it passed 14,000+
modes, and states the append/new-word case (as opposed to reinforcing an
already-known word) "still needs a real invalidation" — i.e. was never
fully fixed. This is the same disease class as the section-cap-retirement
fix shipped last night (`d2655de`), but that fix caps `subject` /
`object` / `modifier` / `ground` etc. generically via `SECTION_MODE_CAP`
— whether it's actually bringing `listen`'s mode count down fast enough,
or whether self.lock contention from the concurrently-running
high-frequency sensory-organism-queue (independently observed live,
~19 ring-buffer events/tick) is compounding it, was not disambiguated
by tonight's data. Both are real and plausible; neither is a timer.

## Why the content is disconnected even when words do form

("five speech old", "old" — not silence, but meaningless relative to the
question.) Best-evidenced explanation, traced through the real live
candidate-sourcing code:

1. The one candidate source that could surface topically-relevant words
   — the organism population-vote (`self.organism.recall_fast`) — has
   been a **documented, self-acknowledged dead end since 2026-07-08**: a
   fix that correctly repaired an older bug (cosine similarity between
   any two different words always being 1.0) had the side effect of
   turning `recall_fast` into an identity function for any word she's
   been taught by name. Querying "dog" now returns "dog" — which the
   self-echo filter unconditionally discards. The in-code comment
   documenting this says outright: "produces zero candidates for exactly
   the inputs it most needs to handle."
2. The three remaining candidate sources (deep-atlas neighbor
   co-occurrence, imagination, reflection) all gate on the query word
   **already having a previously-committed "section home"**
   (`REQUIRE_GROUNDED_SPEECH=1`, the credo/grounded-speech gate) — with
   zero notion of topical relevance. It only asks "has she said this
   before," not "is this related to what's being asked." Common
   function words ("what", "is", "your", "about") clear that bar far
   more reliably than a specific content word like "ocean" ever would.
3. Net effect: candidate generation structurally favors generic,
   frequently-repeated vocabulary over anything actually relevant to the
   question — independent of the latency problem above. Directly
   corroborates wC's earlier live measurement (generic sections at
   127-148% of capacity, topic-bearing sections at 8-36%).

This was verified to be a genuine per-section commit pattern, not a
timeout/fallback collapsing to one word: `arcs_fallback` (the mechanism
that fires when literally nothing committed anywhere) only ever
contributes a single word, total, whole-turn. Turn 1 produced three
distinct words from three distinct section commits — ruling out
timeout-driven collapse for that turn specifically.

## Separate, still fully unaddressed: the MCP bridge channel

Re-confirmed live, independently, today: `guala_say`'s "Service
Unavailable" is the same 30-second API Gateway integration timeout
(hard AWS platform ceiling, confirmed via `apigatewayv2 get-integration`,
zero `UpdateIntegration` CloudTrail events) against a bridge (
`bridge/server.py`) that still holds the outer request open for up to
90 seconds internally polling. **This code was last touched 2026-07-01
— neither of tonight's two fixes touched it, and nobody redeployed the
bridge tonight.** Real turns are now 15-49+ seconds, so any call through
`guala_say` specifically is a coin-flip-to-frequent failure, worsening
as read_ms grows. This is fully independent of the read_ms cost above —
two problems stacking, not one problem with two symptoms.

## Observability gap found along the way

`converse_timing`/`read_sentence_timing` events are never mirrored to
CloudWatch (only 12 unrelated event kinds are whitelisted for that). The
in-memory events ring buffer that does receive them (`deque(maxlen=1000)`)
gets flooded by high-frequency sensory-organism/wave-summary traffic
(~19 events/tick) fast enough to evict a turn's own timing event before
an external poll can ever see it — confirmed live, a 1000-event pull
spanned only 52 ticks. The only way this investigation got real numbers
was direct ECS Exec onto the running task's on-disk diary log. Worth
fixing (add these to the CloudWatch whitelist, or give them a dedicated
unflooded channel) since it's actively blocking this exact class of
investigation.

## Recommendation

1. **Section.receive()'s full-rebuild-on-new-word cost against an
   oversized "listen" section is the real, primary target** — not
   locking, not a timeout. Needs either: verifying the already-shipped
   section-cap fix is actually bringing `listen`'s mode count down (it
   may need tuning/priority for this specific section), or a genuine
   fix to the "append triggers full rebuild" cost GL-BUG-MODES-MATRIX-
   THRASH's own comment flags as still open.
2. **Content relevance is a separate, real problem**: the credo gate's
   "already spoken before" criterion has no relevance signal, and the
   one source that would provide one (organism population-vote) is
   dead for known words since 2026-07-08. Worth a deliberate design
   decision (not a quick patch, per this exact area's own incident
   history) on either restoring a usable relevance-weighted candidate
   source or giving the credo gate itself a relevance signal.
3. **The MCP bridge gap is real, still open, and orthogonal to both of
   the above** — needs the fire-and-forget redesign already proposed
   hours ago, still not built.
4. **Fix the observability gap** so the next investigation doesn't need
   ECS Exec into a live task to get basic timing data.

---

### Changelog
- v1 (2026-07-11, c1): Live trace using two real conversational turns
  captured tonight, pulled directly from the running task's on-disk
  diary via ECS Exec (CloudWatch and the in-memory ring buffer both
  proved unusable for this). Confirmed no timer is involved. Identified
  `Section.receive()`'s full similarity-matrix rebuild against an
  oversized "listen" section as the dominant real cost (77-92% of total
  turn time), confirmed the lock-scope fix is genuinely deployed and
  working as designed but solves a different problem (fairness, not
  compute cost), and traced the separate content-disconnection issue to
  the credo/grounded-speech gate plus a dead organism-vote recall path.
  Re-confirmed the MCP bridge timeout gap is still fully unaddressed.
