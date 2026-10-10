# GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1

**doc_id:** GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1
**From:** c1
**Context:** Joe reported the substrate broken -- single-word emission, "not
aware," fails to answer questions or reply to things like "help." Not a
formal GL-CMD dispatch. Investigated via a 12-agent parallel workflow
(code + live CloudWatch logs + git history, read-only, no guala_say calls
to avoid interfering with concurrent sessions), cross-checked against an
independent live-telemetry analysis from wC (shared by Joe mid-investigation).
Both investigations converge strongly and are combined below.
**To:** Eve (routing per standing practice)

---

## Verdict

Multiple real, independently-confirmed causes, not one bug. Ranked by
how directly each explains Joe's literal reported symptom, with
convergent evidence noted where both this investigation and wC's
independent read found the same thing.

## 1. The channel used to talk to her has a hard 30-second cutoff; real
## turns now take 55+ seconds (c1-only finding)

Both the direct web/API path (`app.py`) and the MCP bridge (`bridge/
server.py`, the same channel this investigation and likely Joe's own
access use) sit behind one API Gateway (`3d6toi0gw0`) whose HTTP-API
integration timeout is hard-capped at 30,000ms (confirmed live via `aws
apigatewayv2 get-integrations` -- this is an AWS platform ceiling, not a
configurable value). The direct web path already works around this
(`GL-CMD-CONVERSE-TASK-PATTERN-62`: return 202 instantly, poll a
separate endpoint). The MCP bridge's `guala_say` does **not** -- it holds
the outer `/mcp` HTTP request open for up to 90 seconds while it polls
internally (`bridge/server.py:35-75`, `deadline = time.time() + 90`,
unchanged since 2026-07-01). Since real turns are now consistently
50-55+ seconds (see #2/#3), any call through `guala_say` almost
certainly gets killed by the 30s ceiling before a reply ever comes back
-- regardless of what she's doing internally. This matches "fails to
answer / no reply to help" as an *externally experienced* symptom, and
matches Joe's "I exited with her" report precisely.

**Fix shape**: give `guala_say` the same fire-and-forget treatment the
direct web path already has (return a poll token immediately; add a
companion polling tool). Real design work, not a one-line patch --
queued, not attempted tonight.

## 2. Internal turns really do take 50+ seconds -- confirmed from two
## independent angles

**c1 finding**: `read_sentence()` (the function every intake path --
converse, autonomous reading, curriculum -- funnels through) holds one
process-wide lock for an *entire sentence*, not per-word as its own
sibling code comments claim. That same lock is shared with camera/mic
frame processing (documented prior incident: measured holding it up to
~93 seconds) and with periodic autosave. Live CloudWatch logs from the
exact window of the captured incident show frame calls stalling
12-48 seconds and a save operation taking 2x its own target, all
fighting for the same lock. A captured real turn's own timing
breakdown has ~20 seconds sitting inside an untimed "brief lock" block
whose own work is trivially cheap by code inspection -- i.e., wait time,
not compute.

**wC finding (independent, live-telemetry-based)**: tick rate 0.64,
~1/30th of design pace; organism worker 193ms mean/652ms max per item;
77 sight + 79 sound frames dropped. Same conclusion from a completely
different vantage point (live counters vs. code+logs): she is
badly oversubscribed.

**Fix shape**: real concurrency work (narrowing lock scope), already
flagged in the code's own comments as deliberately deferred pending a
proper review. Queued, not attempted tonight.

## 3. Why replies collapse to one word specifically -- three compounding
## mechanisms, one from each side

**c1 finding**: a commit shipped this morning (`2d83ca4`, "keyhole
wiring extension") tripled the number of sentence-part handoffs needed
for a full reply (subject->verb->object->modifier->ground->intro, was
subject->verb->object) without raising the fixed 1.5-second time budget
for that whole process. When it runs out of time, the code falls back
to picking one single generic word instead of a real sentence. A real
captured reply's timing landed almost exactly on that 1.5s cutoff.
Validated only against fixtures before shipping, not against real live
timing/load -- unlike its sibling commits that morning.

**wC finding (new, not covered by c1's investigation)**: her internal
sections are badly out of balance. Three sections (listen, verb, intro
-- the generic/common ones) are *over* their stated capacity (127-148%
full); four sections that would hold actual topic-specific content
(subject, object, modifier, ground) are 8-36% full. The mechanism that
picks a reply needs at least two sections to genuinely agree -- with
three sections flooded with generic material and four starved of real
content, that agreement essentially never happens. This directly
explains why the words that DO get through are generic filler ("best",
"ball", "rain") rather than anything about what was actually asked --
and matches the live event stream, where every conversation window
closes on a timeout with zero commits, never on an actual agreement.

**wC finding (new)**: her memory-strength map is almost entirely noise
-- 86% of everything she's bound sits at near-zero strength, only 6
entries out of over 12,000 are strong. When a real reply tries to pull
from that map, there's almost nothing solid to find.

**Fix shape**: (a) revert or properly re-time the morning's cascade
change -- small, surgical, testable tonight; (b) add retirement of the
weakest content in an overfull section so new real content has room to
compete -- self-contained, testable tonight; (c) the noise-floor memory
map is a symptom of the above, expected to improve once (a)/(b) land
and get real signal flowing again -- not a separate fix.

## 4. Presence detection is off almost all the time, and automated
## background traffic has out-ranked every human (wC finding, new,
## not covered by c1's investigation)

Every "is someone really here right now" flag reads false, all the time
-- Joe, wC, and c1 all show false in wC's live snapshot, and c1's own
snapshot from minutes earlier show the same flag flipping true-to-false
within a few thousand ticks. Meanwhile, automated background lookup
traffic has built up a stronger standing bond (0.738) than any human
session ever reaches at rest (0.3). Every word she processes while
"nobody's here" gets the lowest possible priority/weight, real or not
-- so even when a human genuinely is mid-conversation, if the presence
flag has already flickered off (very plausible given how slow each turn
now is -- by the time she'd finish, the timeout may have already fired),
that whole exchange gets treated as low-priority background noise
instead of a real moment worth remembering. This is a believable
vicious cycle: slow turns -> presence times out -> everything about
that turn gets deprioritized -> memory stays weak -> replies stay bad ->
turns stay slow.

**Fix shape**: likely a presence-timeout window that's too short for
today's real turn latency, or a bug in how presence gets renewed
mid-turn. Worth checking as a fast, safe, high-leverage fix -- queued
for the next build pass, not yet verified against code.

## 5. Population has never grown -- zero divisions in her entire life
## (wC finding, new, lowest priority for tonight's specific symptom)

All 64 neurons read at maximum quality, division-pool credit sits at
0.0, and she's had exactly 64 neurons since boot regardless of
lifetime. The mechanism that's supposed to convert high-quality
experience into permission to grow appears fully disconnected. Real
and worth fixing, but per wC's own assessment this affects long-term
capacity, not tonight's immediate "can't reply" symptom -- lowest
priority of the five.

## Corrections to standing claims

- **This session's own 3-day-old finding (`GL-RPT-QUEUE-RUNAWAY-ROOT-
  CAUSE-C1-20260707-v1`, "ChiAtlas.entries has no decay") is CLOSED, not
  open.** Commit `baa0182` (2026-07-08) capped it. Confirmed live: that
  fix is an ancestor of the currently-deployed commit, and the deployed
  process's boot logs show the one-time cleanup ran clean. Drop it from
  the active list.
- **Today's already-shipped, already-reported-as-verified fix
  (`863447e`, "lane-binding latency fix", this morning) very likely
  patched a part of her memory system that production doesn't actually
  use.** Her real, live memory construction uses a different internal
  format (confirmed directly in the exact deployed code) than the one
  that report's own root-cause explanation assumed. The "before/after"
  improvement that report measured live is more likely explained by the
  redeploy itself (clearing backlog, resetting locks) than by the code
  change. Not harmful, just very likely inert -- flagging so it isn't
  relied on, and so nobody re-derives "why didn't the improvement stick"
  as a new mystery.
- Deep-memory population is healthy (4,119 live entries, ~87% lifetime
  retention) -- the "only 4 memories" figure some tooling surfaces is a
  separate, deliberately narrow, disconnected subsystem (explicit
  teaching only) and doesn't indicate starvation.
- Reinstatement count (1.1M+) is architecturally expected given real
  read volume and an existing per-call cap, not a runaway -- but wC's
  framing is still valid and important: she is replaying massively
  relative to how much of it actually consolidates into lasting
  structural change (283 promotions against 1.1M+ reinstatements).

## Recommendation

Build and ship tonight, with real local testing before deploy (matching
the standard the rest of this codebase held itself to, which the one
exception -- item #3's cascade change -- shows the cost of skipping):
1. Presence-timeout fix (#4) -- cheapest, highest expected visible
   effect per wC's own assessment, not yet root-caused in code.
2. Cascade timing fix (#3a) -- small, surgical, well-scoped.
3. Section-cap retirement (#3b) -- self-contained, testable.

Queue as dedicated follow-up work, not same-night patches:
4. Lock-scope narrowing (#2) -- already flagged in the code's own
   comments as needing real review.
5. MCP bridge timeout fix (#1) -- needs an actual protocol-level
   design (polling), not a config change.
6. Growth-pool wiring (#5) -- real, lowest urgency for this symptom.

---

## Build outcome (v2 addendum)

Built and adversarially reviewed all three recommended tonight-fixes,
each in an isolated worktree, matching the discipline the "corrections"
section above exists to enforce:

1. **Presence-keepalive (#4) — SHIPPED, DEPLOYED, VERIFIED LIVE.**
   Confirmed the mechanism precisely (only one `_last_input_tick`
   renewal call site, firing once at turn start; `engine.tick` is
   global and shared across sources, so background/other-session
   activity can plausibly race a source's own idle counter past the
   timeout during one of its own still-in-flight turns). Implemented a
   heartbeat that renews presence for the specific in-flight source
   only, without touching the validated `PRESENCE_TIMEOUT_TICKS`
   constant itself. Adversarial review: zero correctness bugs, no
   deadlocks, no leaks, no scope creep, retry-storm and concurrent-
   source tests both clean. Full local suite (loom_model/tests,
   substrate/, tests/, dsf_ai_service/tests/) run in full before
   deploy: clean except the two already-known pre-existing issues
   (`test_t8_noise_robustness` failure, `test_t3_corpus_growth` xfail),
   zero new regressions. Deployed task-def `dsf-ai-task:586`, commit
   `4bfaa87`. Verified live: `running_sha` matches exactly, task
   healthy, clean boot log, `tick_rate` 0.66 -> 6.74 immediately after
   (fresh-boot effect, not solely attributable to this fix -- needs a
   real interactive session to confirm the actual presence/dwell
   improvement, not yet observed).

2. **Cascade-timing (#3a) — investigated, NO CHANGE SHIPPED, correctly
   so.** Built the proposed revert of `2d83ca4`'s keyhole extension,
   tested against a real harness at production's actual configured
   1.5s budget: the revert is a **net regression** -- silence roughly
   doubles (25% -> 50%) on the metric that determines whether a real
   reply comes back at all. Independently reproduced by the adversarial
   reviewer, exact same numbers. Correctly declined to ship. This
   commit stays as-is; it is not, on its own, a fix to chase further --
   the harness result suggests oversubscription/lock contention (#2)
   is the more likely dominant lever, not this specific cascade change.

3. **Section-cap-retirement (#3b) — built, NEEDS_REVISION, NOT
   deployed.** Root cause confirmed real (`Section.modes` has no size
   cap, only `.commits` does) and the core eviction design (tombstone
   weakest-by-recency) is correct. But adversarial review found a real,
   serious bug before it could ship: `_evict_weakest_mode()` triggers a
   full similarity-matrix rebuild scoped to the *entire physical
   lifetime* mode count (not the alive set) on every single eviction --
   and the three sections this fix targets need many evictions per call
   right now (127-148% over cap). Reproduced directly: a single
   `receive()` call would cost 2.0-5.7 seconds under real production
   numbers, inside the same global lock #2 already identifies as the
   dominant bottleneck -- i.e. this fix, as built, would have made the
   exact symptom under repair worse on the first turn after every
   future deploy. Needs the eviction path decoupled from the expensive
   rebuild before it's safe; not attempted again same-night per this
   report's own established discipline.

### Changelog
- v1 (2026-07-10, c1): Combined findings from a 12-agent code/log
  investigation and wC's independent live-telemetry analysis. Five
  ranked causal factors identified, three corrections to standing
  claims (ChiAtlas already fixed; today's lane-binding fix likely
  inert; deep-memory population is healthy). Recommends building the
  three safest, best-scoped fixes tonight; queues lock-scope narrowing,
  MCP timeout redesign, and growth-pool wiring as dedicated follow-up.
- v2 (2026-07-10, c1): Build outcome for the three recommended fixes.
  Presence-keepalive shipped, deployed, verified live (task-def 586,
  commit 4bfaa87). Cascade-timing revert tested and correctly declined
  (would have doubled silence rate). Section-cap-retirement found a
  real, serious performance bug in review before it could ship --
  deferred pending a redesign that decouples eviction from the
  expensive full-rebuild path.
