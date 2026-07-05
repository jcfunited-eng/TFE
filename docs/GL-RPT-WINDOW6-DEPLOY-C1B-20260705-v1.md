# GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1

doc_id: GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1
From: c1b | To: Eve, Joe, c1a | Responds to: `GL-CMD-FIRE-WINDOW-178-
179-180-181-EVE-20260705-185-v1`. Status: window 6 **DEPLOYED, LIVE**
(task:470, SHA `d6cd271`, carrying -178/-179/-180/-181's full payload).
Fresh backup taken, tests clean (32/32 model-layer tests unaffected by
today's changes; same 3 pre-existing unrelated failures). Organism/
tapestry restore confirmed (`tick=1768 pop=64`, `tick=3573 neurons=450`,
same identity). The 5 requested measurements, in order.

---

## 1) Typed message → rendered response time (must hold < 10s)

Two real turns since deploy, both well under the ceiling:

| turn | n_words | recall_ms | read_ms | total_ms |
|---|---|---|---|---|
| 1 | 12 | 0.4* | 8225.4** | 8730.7** |
| 2 | 11 | 152.8 | 5291.3 | **5921.8** |

*from the prior window-5 confirmation, included for trend; **pre-179.
The most recent, post-`-179`-backgrounding turn: **5921.8ms**, clean
pass under 10s. `recall_ms` rose to 152.8ms this turn (was 11-21ms in
prior windows) — the first direct behavioral evidence the organism's
population has started growing (see item 3): `recall_fast()`'s own
cost scales with population size by design, so a rising `recall_ms` is
exactly what population growth should look like from the outside.

## 2) Response content — real words or honest empty, with origin

Both turns returned `response: "..."`, `response_source: "converse"` —
the honest-empty path (P3's "never backfill" contract), not an error,
not a hang. No real-word emission observed yet this window. Origin
trace for an empty emission is just "converse" (there's no organ-level
attribution to trace when nothing was produced) — will report the
first real-word emission's specific origin the moment one occurs.

## 3) Organism population, before/after one hour

**Before (this deploy's own boot):** `pop=64` (`Organism restored:
identity=cdef9bcf-... tick=1768 pop=64`, 2026-07-05 ~01:14 UTC). This
is the same frozen-at-64 baseline every prior boot has shown — expected,
since `-179`'s backgrounded `experience_word()` only just started
running live at this exact deploy.

**No direct live population counter exists** — checked; it isn't in
`/status`, `/admin/*`, or any endpoint I could find without a reboot.
Indirect evidence in the meantime: `recall_ms` rising from ~12-21ms
(pre-`-179`, population pinned at 64) to 152.8ms this window is
consistent with real growth already happening, matching c1a's own
sandbox result (64→125 after real word-feed). **A true after-reading
needs either a dedicated status field (not built) or the next natural
reboot** — flagging this as a real gap: `-179`'s own exit condition
promised population visibility, and right now the only way to see it
is a boot-log grep. Recommending a `"organism_population": len(...)`
field get added next to the `organism_worker` one already built.

## 4) Target-rotation exit (≥5 distinct in 2h) + video-attend crash

**~1.5h into the 2h window (task:468 deployed ~00:02 UTC, now ~01:32):
3 distinct targets visited so far** (searched the full CloudWatch
`activity_started` log across the whole window, not just this
reboot's own counter, since two subsequent deploys reset the latter):
`ATTENDING_VIDEO/271968dd5575`, `ATTENDING_VISUAL/5aa967930289`,
`ATTENDING_VISUAL/779d68180f0a`. Real, genuine rotation — not the
single permanently-stuck target from before `-181` — but **not yet at
5 with ~30 minutes left in the window.** Will report the final
tally when the window closes; not declaring pass or fail early.

**Video-attend crash, root-caused precisely:** `_atick_attending_video`
(`gualaloom_v5_engine.py:5595`) crashes on `vid.frame_dir` inside a
try block; the `except` at `:5615-5617` logs `video_attend_error` and
sets `_viewed=True` unconditionally, so the activity's own lifecycle
is never blocked. Critically, `vid.times_attended += 1` (`:5622`) runs
**unconditionally, outside the try/except**, every time the activity's
budget ends. **This means the crash does NOT create a monopoly or
block `-181`'s outcome** — habituation-freshness decay for the video
proceeds exactly as it would if the crash weren't there, so the video
naturally loses competitiveness against still-fresh pictures over
real time, same as any other target. It's a genuine, separate
correctness bug (a swallowed exception, and actual video frames are
never really being viewed/bound to a motif) worth its own fix — but
it is not the reason to expect -181 to fail its exit criterion.

## 5) Registry-sweep line (per -183 standard)

**Could not locate a `-183` doc in `docs/`** — searched by filename
pattern and by content grep for "registry sweep"; found nothing.
Reporting the actual live counters directly instead of guessing at an
unknown standard's format:
- `frame_backpressure` (`-182` L3): `{sight: 0, sound: 0}` dropped,
  `{sight: 0, sound: 0}` currently inflight, cap 2 each. Zero drops
  since task:470 booted.
- `organism_worker` (`-179`): exists at the engine level
  (`gualaloom_v5_engine.py:8294`, `{queued, dropped}`) but **is not
  wired into the `/status` endpoint's response** in `app.py` — a real,
  minor gap, not fixed here (out of this dispatch's scope; flagging
  for whoever owns `-179`'s follow-up, or I can add the one line if
  asked).
- `_converse_tasks`: no direct count exposed either; not blocking
  anything observed so far (both test turns completed cleanly).

If `-183` names a different, specific format, point me at it and I'll
re-report in that shape.

---

### Changelog
- v1 (2026-07-05, c1b): window 6 deployed (task:470, SHA d6cd271).
  Items 1/2 measured directly (5921.8ms, honest empty). Item 3 partial
  — before-reading captured (pop=64), no live after-reading possible
  without a dedicated field or reboot; indirect evidence (rising
  recall_ms) suggests growth has begun. Item 4 partial — 3/5 distinct
  targets at the 1.5h mark, video-attend crash root-caused and
  confirmed non-blocking for the exit criterion. Item 5 — no -183
  standard doc found; reported live counters directly, flagged the
  organism_worker /status wiring gap.
