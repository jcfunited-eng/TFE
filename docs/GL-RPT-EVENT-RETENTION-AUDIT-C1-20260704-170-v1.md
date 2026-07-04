# GL-RPT-EVENT-RETENTION-AUDIT-C1-20260704-170-v1

doc_id: GL-RPT-EVENT-RETENTION-AUDIT-C1-20260704-170-v1
From: c1b | To: Eve | Responds to: GL-CMD-EVENT-RETENTION-EVE-20260704-
170-v1
Status: **PROPOSAL — nothing in this report is implemented or
deployed.** Per the CMD's own gates and "Joe's part: none until the
retention number + cost arrives — then it comes to you for
ratification like the sleep ceiling did," this report stops at C1
(named) + C2 (proven) + C3 (proposed number + cost) + C4 (evaluated).
No code touched. No deploy.

---

## C1 — the truncator, named

**`Guala.compact_events()`**, `dsf_ai_service/v4/gualaloom_v5_engine.py:6683-6710`,
called every **60 seconds, unconditionally**, from
`_do_hot_save_and_compact()` / `_do_save_and_compact()`
(`dsf_ai_service/app.py:4303-4321`), driven by `_periodic_v6_save()`'s
`await asyncio.sleep(60)` loop (`app.py:4342-4358`).

This is **working-as-designed, not a crash bug** — but the design is a
crash-replay retention policy (keep only what's not yet in the last
snapshot), and it is being asked to serve as a durable audit trail,
which it structurally cannot do:

```python
def compact_events(self, state_dir, keep_after_offset=0):
    """Keep only events written after keep_after_offset bytes.
    Events appended during the save window survive; only pre-save
    events (already captured in the snapshot) are discarded."""
    ...
    with open(path, "rb") as f:
        f.seek(keep_after_offset)
        tail = f.read()
    ...  # tail is the ONLY thing written back; everything before
         # keep_after_offset is gone.
```

Both call sites measure `pre_size = _guala.events_log_size(STATE_DIR)`
*before* the save runs, then call `compact_events(STATE_DIR,
keep_after_offset=pre_size)` right after. Net effect: **every single
minute, forever, the entire file is discarded except whatever landed
during that one save's execution window** (empirically ~2-10s wide,
see C2). Nothing before that survives to the next cycle.

**Compounding factor:** only 12 of ~40 distinct event kinds ever reach
`log_event()`/disk at all — the whitelist in `_log_substrate_event()`,
`gualaloom_v5_engine.py:3934-3938`: `activity_started, activity_ended,
corpus_completed, sleep_manual, dream_began, dream_artifact,
picture_uploaded, sound_uploaded, video_uploaded, corpus_added,
visual_motif_committed, visual_motif_fired, emission`. Everything else
(`response_bound`, `self_heard`, `hemisphere_update`, `converse_timing`,
`sound_frame_bound`, `emission_dynamics`, `agency_backtrack`, etc. —
confirmed live via `guala_get_events`, tick 14701120-14701210, zero of
50 consecutive real events were disk-whitelisted kinds) lives only in
the 1000-slot in-memory deque.

**Historical confirmation this is a known pattern, not a hypothesis:**
commit `8c28393` ("Persistence safety... compaction... GL-BRIEF-037",
2026-06-11) originally opened `events.log` in `"w"` mode and wiped it
to **zero bytes every single save cycle** — the literal `'w'`-mode
truncation pattern. Commit `95b0cd8` ("D2: Offset-based compaction —
events during save window survive", same day) replaced full wipe with
the offset-based tail-keep shown above, specifically to stop discarding
*everything*. It reduced blast radius from 100%/cycle to
~100%-of-everything-older-than-the-save-window/cycle — which still
reads as a near-empty file at any inspection point. Both commits are
real, on this branch's history.

**Live confirmation, this session** — real CloudWatch data,
`/ecs/dsf-ai`, last 5.95h (222 compaction cycles):
```
total bytes discarded: 81,724  (13,735 bytes/hour)
total events "kept" (survived to next cycle): 19  (3.19/hour)
```
Sample compact lines:
```
[GualaLoom] Event log compacted: 410 bytes discarded, 1 events kept
[GualaLoom] Event log compacted: 802 bytes discarded, 0 events kept
[GualaLoom] Event log compacted: 165 bytes discarded, 0 events kept
```
This is fully consistent with the audit's opening finding of `{"total":
4}` from `/v6/events_histogram` — re-queried live just now, current
value is `{"total":0}`, which is expected and not a regression: the
count is whatever survived the *most recent* 60s cycle at query time,
by design.

**Ruled out** (evidence in full from this session's investigation,
available on request, condensed here for space): `_rotate_events()`
(only fires >10MB, renames not deletes — not the cause);
`_replay_events()` (pure read-only, same file, no write — not the
cause); the separate `STATE_DIR/ring_events/events.log` written by
`PersistenceConsumer`/`S3Consumer` (`substrate/persistence_consumer.py`)
— a different file at a different path, not what `/v6/events_histogram`
reads; `SaveCoordinator` (never calls `compact_events`); EFS/container
churn (state is on persistent EFS with stale-handle retry logic —
loss is application-level, not infra).

---

## C2 — readers audit

Four readers of `state_dir/events.log` (`EVENTS_LOG = "events.log"`,
`gualaloom_v5_engine.py:6096`):

| Reader | Behavior | Verdict under larger log |
|---|---|---|
| `GET /v6/events_histogram` (`app.py:4178-4199`) | Full read, no pagination/tail limit, `Counter` over every line | Safe. O(file size), no correctness assumption on small size. At proposed retention (below), file stays in the low-hundreds-of-KB to low-single-digit-MB range — full read is sub-10ms even generously estimated. |
| `_replay_events()` (`gualaloom_v5_engine.py:7324-7345`), boot-only, called once from `load_full_state` (`:6918`) | Reads every line, `json.loads`, replays only if `ev["tick"] > self._last_save_tick` | Safe, and safe *by construction* — see below. |
| `_replay_one_event()` (`:7347-7397`) | Per-event handler: dict/attribute sets only (`vocab.add`, `source_history[...] = max(...)`, `Activity(...)` construction, presence flags). No I/O, no recomputation. | Safe. O(1) per call; even a stress case of ~3,700 events (7-day synthetic file, see below) replays in low single-digit ms. |
| `snapshot_state()` (`:7401-7427`) | `shutil.copy2` of `events.log` into a timestamped backup dir, on every "cold+wave" cycle (roughly every ~18,000s / 5h, gated by `do_wave and do_cold`) | Safe. Copy cost scales with bytes; at proposed retention size this is negligible next to the wave/grid save costs already dominating that cycle. |

**Correctness finding, not just a cost finding:** `_replay_events`'s own
filter (`ev.get("tick", 0) > self._last_save_tick`) is *already* the
mechanism that makes it safe to retain events older than the last save
— it was written to tolerate exactly that, presumably because nobody
guaranteed the offset-based compaction would always run before a crash.
Extending retention introduces **no new replay-correctness risk**; it
exercises a code path that already existed and already does the right
thing. The one real behavior change: on a cold boot where
`_last_save_tick` is still its class default `0` (`:6102`) — noted at
`:6549` as a real, if rare, path ("...leaving `_last_save_tick=0`") —
`_replay_one_event` would now be called for the *entire* retained
window instead of the handful of events that currently survive. Cost
of that worst case is covered by the benchmark below (thousands of
calls, still sub-10ms total; each handler is O(1) dict/attr writes).

**Boot-time / compact-time cost — measured, not assumed:**

No timing instrumentation currently exists around `_replay_events()` or
boot generally (checked: no `print` with elapsed time wraps
`load_full_state`/`_replay_events` anywhere in the file) — so today's
*true* live boot-replay time isn't directly observable in CloudWatch
either, before or after any change. Recommend adding a timing print
around this call as part of the implementation, closing that gap
permanently rather than relying on offline benchmarks after the fact.

In the absence of that instrumentation, two real measurements stand in:

1. **Local synthetic benchmark**, matching real observed shape
   (average line size derived from this session's own live
   measurement, JSON with a `type`/`tick`/`ts`/`detail` structure):

   | Window | Lines | Size | Parse+replay-check loop | Compact I/O (seek+read+write+fsync+replace) |
   |---|---|---|---|---|
   | 8h (top of stated cadence) | 178 | 107.6 KB | 1.56 ms | 4.76 ms |
   | 24h (3x margin) | 534 | 322.6 KB | 3.38 ms | 5.04 ms |
   | 7d (proposed, see C3) | 3,739 | 2,259 KB | 24.4 ms | 7.3 ms |
   | 30d (stress case, not proposed) | 16,027 | 9,691 KB | 100.6 ms | 13.7 ms |

   (Local disk, not EFS — a lower bound on the byte-processing
   component; see caveat below.)

2. **Live EFS reality check**, real CloudWatch `[save-hot]` lines from
   this session, current (near-empty) log:
   ```
   [save-hot] 13.44s core=10.64s compact=2.80s
   [save-hot] 20.78s core=18.57s compact=2.21s
   [save-hot] 10.64s core=10.63s compact=0.01s
   ```
   The `compact=` component today already costs **2-3 seconds on live
   EFS even discarding almost nothing** — that cost is dominated by
   fixed network-filesystem I/O overhead (open/seek/read/open-tmp/
   write/fsync/`os.replace`), not by data volume. Going from a
   near-empty file to a few-hundred-KB file adds bytes that are still
   comfortably inside a single read/write syscall's worth of transfer
   at any realistic EFS throughput — the synthetic benchmark's local
   byte-processing numbers (single-digit ms even at 7 days) support
   that the *added* wall-clock cost from data volume specifically will
   stay well under the 2-3s *fixed* floor already being paid every
   cycle today. **Net: no measurable regression expected against
   today's baseline; recommend the boot-timing print above to confirm
   directly on the next deploy, satisfying G-3 with live evidence
   rather than an offline proxy.**

---

## C3 — retention number, derived

**Real tick rate, measured live this session** (two consecutive
`guala_status` polls, using the wall-clock-stamped
`persistence_health.last_save_timestamp` field, not local clock skew):
```
poll 1: last_save_tick=14701135  last_save_timestamp=2026-07-04T12:43:26Z
poll 2: last_save_tick=14701574  last_save_timestamp=2026-07-04T12:45:27Z
delta: 439 ticks / 121s = 3.63 ticks/sec
```
This supersedes the `TICKS_PER_SEC = 20` constant in
`substrate/test_metadecay_harness.py:26` for this purpose — that's a
test-harness assumption, not a live measurement of this process. At
3.63 ticks/sec: 4h ≈ 52,300 ticks, 8h ≈ 104,600 ticks — consistent
with `current_activity` showing a live 2000-tick `ATTENDING_VISUAL`
budget (`gualaloom_v5_engine.py` `ACTIVITY_TICK_BUDGETS`) resolving to
~9.2 real minutes, in line with observed activity durations this
session.

**Real on-disk event rate, measured live this session** (CloudWatch,
5.95h, 222 cycles — see C1): **13,735 bytes/hour** of whitelisted,
disk-eligible event traffic, under today's baseline load (background
`ATTENDING_VISUAL`/`EMITTING` cycling; no natural `SLEEP`/`DREAM`
transition occurred inside this sample window).

**Proposed number: 7 days (168 hours) retention**, replacing the
offset-based "since last save" criterion with a time-window criterion
(keep every line whose `ts` is within the trailing window, regardless
of save boundaries).

Reasoning:
- The CMD's own target is the ~4-8h sleep cycle *with margin*. A flat
  "3x the top of the range" (24h) technically clears the bar but only
  captures one cycle end-to-end — a migration-by-replay spec needs to
  *see the mechanism repeat* to validate it's reconstructing a pattern,
  not a one-off. 7 days at the measured cadence covers on the order of
  20+ full sleep/wake cycles.
- Cost at measured baseline rate: **~2.3 MB** (see C2 benchmark table)
  — comfortably under the existing 10MB `EVENTS_MAX_BYTES` rotation
  ceiling (`gualaloom_v5_engine.py:6098`), so no interaction with that
  mechanism.
- Boot-parse cost at this size: ~24ms (benchmark above) — negligible
  against the multi-second floor already being paid by EFS I/O.
- **Open caveat, stated honestly:** the 13,735 bytes/hour baseline was
  measured during a window with *no* natural sleep/dream cycle (still
  an open item from the sleep-calibration dial-1 work). `sleep_manual`,
  `dream_began`, `dream_artifact` are all in the on-disk whitelist and
  will add to this rate once one occurs; on the numbers above there is
  ample headroom (an order of magnitude increase in hourly rate would
  still land 7-day retention around 23 MB, still under any concerning
  threshold) — but the honest position is: **re-measure this rate
  after the first natural sleep/dream cycle lands**, rather than
  treating today's number as final.

**Storage/save/boot cost, stated together per the CMD's requirement:**
storage ~2.3 MB (EFS + whatever S3 backup path already mirrors
`STATE_FILES`), save-cycle cost no measurable regression (bytes added
are far under the existing fixed EFS I/O floor), boot cost ~24ms
(benchmarked) pending live confirmation via the recommended
instrumentation.

---

## C4 — CloudWatch mirror, evaluated

**Proposal:** one additional `print()` inside `Guala.log_event()`
(`gualaloom_v5_engine.py:7295-7308`), immediately after the successful
`f.write(...)`, echoing the same JSON entry to stdout. ECS/Docker's
logging driver already ships all stdout from this task to
`/ecs/dsf-ai`, confirmed unlimited retention
(`retentionInDays: None`) this session.

**Rate-safety:** inherits the existing 12-kind whitelist at
`_log_substrate_event()` (`:3934-3938`) — the same gate that already
keeps `events.log` sparse keeps this mirror sparse. The ~40 high-
frequency internal kinds (`hemisphere_update`, `response_bound`,
`converse_timing`, etc.) never reach `log_event()` at all, so they
never reach this mirror either — no new per-tick spam risk introduced.

**Cost:** at the measured 13,735 bytes/hour baseline, ~9.9 MB/month
added to a log group that already stores 183 MB
(`storedBytes: 183071572`, confirmed live this session) — effectively
free at typical CloudWatch ingestion pricing (low single-digit cents/
month). Even a 10x burst from real sleep/dream activity stays under
$1/month.

**Value:** makes CloudWatch a genuine backstop independent of
`events.log`'s own retention window — if the 7-day (or whatever
ratified) window ever proves insufficient for a specific migration
question, the full history is still recoverable from CloudWatch, no
architecture change needed to go get it.

---

## Gates

- **G-1** ✅ Truncator named with code line + live + historical
  evidence (C1).
- **G-2** Scope proof: proposed touch points are `compact_events()`
  (retention criterion only), `log_event()` (one added `print`), and
  the `app.py` save loop (no change needed there — same call sites,
  same cadence). No cognition primitive, scoring path, or physics
  constant touched by this proposal. Diff-proof will be trivial once
  code exists (three small, localized edits); not written yet per
  Joe's-ratification gate.
- **G-3** Boot cost: benchmarked (~24ms at 7-day size vs. multi-second
  existing floor); live confirmation deferred to the recommended
  timing-print instrumentation, to be added as part of the same change
  so G-3 is self-verifying on every future deploy, not just this one.
- **G-4** Noted: implementation intentionally deferred pending Joe's
  ratification of the 7-day number, so C3+C4 land in **one** deploy
  window together rather than two separate sleep-costing deploys.

---

## What happens next

Per the CMD: this report is the retention-number-plus-cost handoff.
Nothing ships until Joe ratifies the number (7 days) the way he did
the sleep ceiling. If ratified, the actual change is small and
localized — happy to draft it, but not touching code until that comes
back.

### Changelog
- v1 (2026-07-04, c1b): C1 named (code + live + historical evidence).
  C2 readers audited, boot/compact cost benchmarked. C3 retention
  number proposed (7 days) with live-measured tick rate and event
  rate, cost stated. C4 CloudWatch mirror designed and costed. No code
  written, no deploy. Awaiting Eve/Joe ratification.
