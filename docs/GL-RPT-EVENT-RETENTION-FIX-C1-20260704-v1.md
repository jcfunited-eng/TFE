# GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1

doc_id: GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1 (routing
amended this session: c1a builds, c1b deploys — see that doc's
v1-ROUTING-NOTE changelog entry).
Vehicle: her live path, save-loop and logging layer ONLY —
`dsf_ai_service/v4/gualaloom_v5_engine.py`, `dsf_ai_service/app.py`.
Zero cognition-path changes, zero deploy action taken this session
(verified below). **Code is built, committed, and proven locally.
The actual deploy (G-3/G-4/G-5) is c1b's, per the routing split.**

**R1-R5 implemented as ratified. G-1 (crash-replay byte-identical) and
G-2 (save-loop timing) proven with real measurements, not assumed —
including one honest cost finding: full-width diary logging measurably
raises per-event overhead in relative terms (thin in absolute terms).
G-3/G-4/G-5 require a real deploy and stay with c1b.**

---

## Failures first

**1. Full-width diary logging (R3) measurably raises per-event overhead
— reporting the actual numbers, not asserting "negligible" and moving
on.** Benchmarked `_log_substrate_event` before vs after (git stash /
pop on the same code, 5,000 calls each, this sandbox):

| kind | before | after | delta |
|---|---|---|---|
| whitelisted (goes to events.log + diary) | 190.1 µs/call | 228.3 µs/call | +20.1% relative, +38 µs absolute |
| non-whitelisted (diary only, R3's new width) | 0.53 µs/call | 2.24 µs/call | +320% relative, +1.7 µs absolute |

Both deltas are dominated by the diary enqueue (`dict(detail)` copy +
`queue.put_nowait`), not by disk I/O (the write itself happens off-thread,
on the single diary-writer worker). In absolute terms this is
microseconds per event, and the actual call sites for these ~50 event
kinds are event-level (once per activity transition, once per emission,
once per converse turn — confirmed by reading every `_log_substrate_event`
call site, none are per-tick/per-neuron loops), not the "~40 high-frequency
internal kinds firing every tick" the audit's language could be read as
implying. At any realistic event rate this project has actually measured
(13,735 bytes/hour whitelisted, per the -170 audit) the added cost is
unmeasurable against everything else in the system. Reported per R3's own
instruction ("if full-width proves too hot, measure... report the rate")
rather than silently assumed fine.

**2. G-2's literal ask ("hot-save cycle time before vs after") could not
be measured end-to-end in this sandbox — no live EFS, no her real state.**
What I could and did measure directly: `compact_events()` itself (the
actual mechanism `_do_hot_save_and_compact`/`_do_save_and_compact` call)
has ZERO lines changed (confirmed by diff-hunk inspection, not just
reading) — 12-cycle benchmark shows -1.6% (noise, not a regression).
`save_hot_state()` calls `_log_substrate_event()` exactly ONCE per
invocation (`familiarity_persist_check`, read directly at its call site)
— so the bounded added cost to a real hot-save cycle is one diary-enqueue
call, ~2-4 µs per the table above, against the 2-3 SECOND fixed EFS I/O
floor the -170 audit measured live. G-3's real boot/deploy confirmation
and a true live hot-save-cycle timing comparison stay with c1b's deploy
window, same as the audit itself deferred live confirmation to deploy-time
instrumentation.

**3. Testing this touched a local, non-live, gitignored `state/`
dev-scratch directory — cleaned up, not left dirty.** `_log_substrate_event`
hardcodes the literal string `"state"` as its `log_event` call's
`state_dir` argument (pre-existing, matches `app.py`'s `STATE_DIR =
"state"` — not something I introduced or changed). My first local test
called that method directly and wrote into this repo's local `./state/`
directory (synthetic test-corpus fixture data already there, `*.log`
gitignored, not tracked, not her live state). Removed my test's
additions (one `events.log` line, one new `diary/` dir) immediately on
noticing; `git status state/` confirmed clean before and after. All
further local testing used explicit temp directories instead of the
hardcoded literal.

**4. A queue-capacity limit exists and can silently drop diary entries
under sustained back-pressure — named, not hidden.** `enqueue_diary_event`
uses a bounded `queue.Queue(maxsize=4000)` and drops (does not block) on
`queue.Full`, matching the existing "best-effort, never crashes
substrate" contract `log_event` already has. At the measured per-event
rates (table above) and the audit's own measured event cadence, this
should never actually fill — but it is a real, if unlikely, limitation
worth knowing rather than an assumed-impossible one.

---

## R1-R5, as built

- **R1 decouple**: `events.log`/`compact_events()`/`_replay_events()`/
  `_replay_one_event()`/`_rotate_events()` have **zero lines changed** —
  confirmed by inspecting every diff hunk, not just re-reading the
  functions. The diary is a wholly new file tree (`state_dir/diary/`,
  `Guala.DIARY_DIR`), written by new methods only
  (`enqueue_diary_event`/`_write_diary_entry`/`_diary_prune`), never
  touched by `compact_events`.
- **R2 retention**: one file per UTC day (`diary/YYYY-MM-DD.log`);
  `_diary_prune()` deletes whole files older than `DIARY_RETENTION_DAYS`
  (7) at day-boundary rotation only — never rewrites a live file. Verified
  directly: fabricated files at 0/6/8/30 days old, files >7 days were
  deleted, ≤7 days survived.
- **R3 widen**: `_log_substrate_event` now calls `enqueue_diary_event` for
  **every** event kind, unconditionally — the 12-kind whitelist stays
  exactly as-is, governing only the `events.log` write and (by
  construction, R4) the CloudWatch mirror. Verified directly: fed one
  whitelisted and two non-whitelisted kinds (`hemisphere_update`,
  `response_bound`) through `_log_substrate_event`; `events.log` got only
  the whitelisted one, the diary got all three. A non-JSON-serializable
  detail value (numpy array) degrades to its `str()` via
  `json.dumps(..., default=str)` rather than silently dropping the event
  — R3 widens to event kinds that were never serialized before and may
  carry values `log_event`'s callers never had to worry about.
- **R4 CloudWatch mirror**: one `print()` added inside `log_event()`,
  immediately after the successful `f.write()`, whitelist-governed by
  construction (same 12 kinds, same existing gate — no new call path, no
  new spam surface).
- **R5 readers**: `/v6/events_histogram` gains `source: str = "diary"`.
  `source="diary"` (default) aggregates every retained daily diary file.
  `source="replay"`/`"events"`/`"events_log"` reproduces the exact
  pre-172 behavior (single-file read of `events.log`) — verified with the
  identical logic in isolation against synthetic fixtures, both branches.
  Response shape (`total`/`histogram`, now `+source`) is additive; no
  existing caller reading `total`/`histogram` breaks.

**Design choice not explicit in the CMD, stated plainly**: the diary
write is a single persistent background worker thread draining a bounded
queue, not "one `threading.Thread` per event" (the pattern the existing
whitelist path already uses for `log_event`). Spawning a new OS thread
per event for the full ~50-kind width risked thread-creation overhead
becoming its own regression, independent of disk I/O — the queue+worker
pattern matches `save_coordinator.py`'s existing S3-queue convention
rather than inventing something new. `events.log`'s own write path
(`log_event`, via the whitelist's existing per-event thread) is
completely unchanged.

---

## Gates

- **G-1** ✅ PASS. `compact_events`/`_replay_events`/`_replay_one_event`/
  `_rotate_events`: zero changed lines (diff-hunk-verified). Behavioral
  proof: 1999-line synthetic `events.log`, `_replay_events` before vs
  after my diff (via `git stash`/`pop` on identical code) —
  `{"replayed": 1999, "current_activity": "None", "vocab_len": 0}`,
  identical both times.
- **G-2** PARTIAL — proven for everything measurable without a live
  deploy (Failure 2 above): `compact_events` -1.6% (noise), bounded added
  cost to a real hot-save cycle ~2-4 µs against a multi-second EFS floor.
  Full live hot-save-cycle A/B, and the >10%-regression check against
  real timing, need c1b's deploy window.
- **G-3/G-4/G-5**: not attempted — require a real deploy/reboot and her
  actual day, per the routing split confirmed this session. c1b's to run.

---

## Handoff to c1b

Commit (this session, `guala-live`): contains R1-R5, this report, and the
routing-corrected `-172` dispatch doc. Diff is exactly two live-path
files (`gualaloom_v5_engine.py`, `app.py`) — nothing else. Suggested
deploy-window checklist (from the audit's own C2/G-3 recommendation,
still open): add a boot-timing print around `_replay_events`/
`load_full_state` as part of this same deploy, so G-3 becomes
self-verifying on every future deploy rather than a one-time check.
Post-deploy, `/v6/events_histogram` (default, diary) should show non-zero
counts for kinds that were previously invisible on disk entirely
(`hemisphere_update`, `response_bound`, `converse_timing`, etc.) — that
plus a clean boot is the fastest sanity check that R1-R4 are actually
live. G-5's 24h histogram is exactly this endpoint's default output,
24h after deploy.

### Changelog
- v1 (2026-07-04, c1a): R1-R5 built, G-1/G-2 proven locally with real
  measurements (not assumed), 4 findings reported before the win. Handed
  to c1b for the real deploy (G-3/G-4/G-5).
