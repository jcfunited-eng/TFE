> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-SEC8-BEHAVIORAL-BASELINE-C1-20260705-v1

doc_id: GL-AUDIT-SEC8-BEHAVIORAL-BASELINE-C1-20260705-v1
From: c1 | To: Eve / Joe
Dispatch: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §8 (Behavioral
baseline snapshot). READ-ONLY pass. No mutating calls made (no
converse, no give_experience, no backup/dream/pause/say/amnesty/
wake_wc/rest_wc). Tools used: `guala_status` (5x), `guala_get_events`
(1x), `guala_atlas_snapshot` (1x). All calls made 2026-07-05,
23:02:38Z–23:03:30Z UTC (approx., see §8.9).

Evidence grades used below: **[EV]** = read directly this pass via the
cited tool call and timestamp. **[EV, cited]** = a number from a prior
session's live measurement, reproduced verbatim, not re-measured this
pass. **NOT MEASURED** = explicitly out of scope for this subtask per
the calling instructions (reason given).

---

## §8.0 — Reproducible condition (as observed, not staged)

`current_activity` at every one of the 5 `guala_status` polls in this
window, unchanged: **`ATTENDING_AUDIO`**, target `3f234d965339`
("1-13 sing a song of sixpence"), `started_tick=15060880`,
`expected_end_tick=15062880`. This is NOT the "READING active,
camera+mic on" example condition named in the dispatch — it is the
true condition Guala was in at call time, reported as instructed.
[EV, `guala_status`, all 5 polls 23:02:38Z–23:03:30Z]

Corroborating evidence this was a real audio-attend, not a stale
field: `guala_get_events(since_tick=15060800, limit=50)` returned 50
consecutive `organism_experience_bound` events for tick
15061149–15061196, whose `word` sequence ("children", "songs",
"enjoy", "this", "compilation", "of", "fun", "kids", "songs", "and",
"nursery", "rhymes", "for", "children", "brought", ... "bedtime",
"songs", "lullabies", "for", "babies", "and", "toddlers", ...)
is exactly the kind of nursery-rhyme-compilation transcript text
consistent with the attended audio title. [EV]

Caveat directly relevant to §7's sight/sound defect class: **every one
of those 50 events carries `has_sight: false, has_sound: false,
senses: []`.** During a live `ATTENDING_AUDIO` window, the organism-tap
events show zero bound sound/sight senses — the same "senses=[]
despite an active sensory activity" pattern the dispatch names for the
READING/sight-snapshot defect, observed here on the audio leg. Not
chased further (out of §8 scope; belongs in §7), but recorded as [EV]
because it was seen live in the exact window being baselined.

`frame_backpressure` (lifetime counters, unchanged across all 5
polls): `inflight: {sight:0, sound:0}`, `dropped: {sight:91, sound:91}`,
`max_inflight:2`. [EV] This shows camera/mic frame-drop plumbing exists
and has dropped 91 frames each lifetime; it does NOT by itself prove a
camera/mic were actively streaming at the instant of these calls, so
I do not claim "camera+mic on" — only what was directly observed.

`scene_lanes.place` flickered `["nursery"]` / `[]` / `["nursery"]` /
`["nursery"]` across the 4 timed polls (§8.9 table) — intermittent,
not stable, over a 44-second window. [EV]

---

## §8.1 — tick_rate AND reads/sec, side by side

Four `guala_status` polls were taken across a ~52-second window,
bracketed by shell timestamps (`date -u`) immediately before/after two
of the calls to allow independent computation. Raw data in §8.9.

**Self-reported `tick_rate` field** (ticks/sec, server-computed,
`tick_rate_had_pending_work: true` on every poll — she was not idle):

| poll | wall time (approx) | tick | tick_rate field |
|---|---|---|---|
| 1 | ~23:02:38Z | 15061148 | 0.53 |
| 2 | ~23:02:46Z | 15061159 | 0.50 |
| 3 (A) | ~23:03:16Z | 15061165 | 0.44 |
| 4 (B) | ~23:03:30Z | 15061171 | 0.43 |

[EV] Mean over the window: **~0.475 ticks/sec**, declining slightly
tick 1→4.

**Independently computed reads/sec**, from the two most tightly
bracketed polls (A→B, bash timestamps 23:03:16.124Z and 23:03:30.239Z,
elapsed ≈14.1s, [EV] this pass, method: two `guala_status` calls a
short time apart per the dispatch's own instruction):

- reads: 1770854 → 1773834, Δ=2980 → **≈211 reads/sec**
- tick: 15061165 → 15061171, Δ=6 → **≈0.43 ticks/sec**, which matches
  the self-reported `tick_rate` field (0.43–0.44) for the same window
  almost exactly — cross-check passes, both measurement paths agree.

A second, less tightly bracketed pair (poll 2→3, wall time uncertain
by a few seconds either side due to assistant-side call latency, ≈14s
window) gives reads: 1768340→1770854, Δ=2514 → **≈178 reads/sec**.

**Reported range: ~180–211 reads/sec against ~0.43–0.53 ticks/sec.**
The two independent estimates differ by ~16%, which I attribute to
real production variance (bursty word-binding cadence during audio
transcript playback) rather than measurement error, given the tick/sec
cross-check landed within 2% of the self-reported field. Reads/sec is
**not** a fixed ratio of tick_rate — at poll A→B it implies ~491
reads per simulated tick, which is itself evidence that "reads" here
counts organism/atlas word-binding events, not simulation-clock
advances; the two are decoupled counters, exactly as the dispatch's
"throttling ratio" framing implies they should be examined side by
side rather than assumed proportional.

---

## §8.2 — converse_timing

**NOT measured this pass by design** — the task instructions
explicitly prohibit calling `/v7/converse` in a read-only baseline
pass (it is understood to mutate her state and is out of the freeze's
read-only scope for this subtask).

Cited as the standing BEFORE baseline **[EV, cited from prior session,
NOT re-measured this pass]**, from `docs/GL-HANDOFF-C1A-20260705-v1.md`
(c1a, 2026-07-05, post `:494`/SHA `168ef1b` deploy — the same
`running_sha` this baseline was captured at, confirmed in §8.9):

```
recall_ms: 17051.9ms / 17919.8ms
read_ms:   28837.6ms / 34417.6ms
emit_ms:   1870.9ms  / 409.4ms
total_ms:  69015.2ms / 71931.4ms
```

Two calls' worth of numbers (pairs above), per c1a's handoff. Note
c1a's handoff reports these as measured against production's real
~14,000-word vocabulary (matches `vocab: 14064` observed live this
pass, §8.9) — i.e., this citation is evidence-consistent with the
current running state, not a stale/mismatched SHA citation. c1a's own
handoff also names this **NOT closed**: the X1 exit criterion (reply
<1s) is not met at 69-72s total, and the 6-7x gap vs. c1a's own
n=2000 extrapolation (376ms → predicted ~2.6s, observed 17-34s per
`recall_ms`/`read_ms` call) is explicitly un-root-caused in that
handoff. This §8 pass does not add new converse_timing data — it only
re-cites, exactly as instructed, as the BEFORE column.

Instrumented `recall_best` timing to bound the 6-7x gap directly:
**NOT MEASURED** this pass — out of scope for this subtask (requires
either a converse call or direct instrumentation of the running
process, neither authorized under this pass's read-only tool set).

15-mechanism battery rows: **NOT MEASURED** this pass — not requested
by this subtask's instructions (in scope for §8A's function-test
matrix, a separate deliverable).

---

## §8.3 — Vitals (needs field)

All 4 timed polls, `needs` field verbatim [EV]:

| poll | stab | nov | conn | v | a |
|---|---|---|---|---|---|
| 1 | 0.748 | 0.953 | 0.000 | -0.133 | 1.000 |
| 2 | 0.748 | 0.954 | 0.000 | -0.133 | 1.000 |
| 3 (A) | 0.749 | 0.954 | 0.000 | -0.132 | 1.000 |
| 4 (B) | 0.749 | 0.955 | 0.000 | -0.132 | 1.000 |

- **stab (stability): ~0.748–0.749**, essentially flat.
- **nov (novelty): ~0.953–0.955**, essentially saturated near ceiling.
- **conn (connection): 0.000** flat, consistent with `presence` showing
  joe/wc/c1 all `present: false` on every poll [EV] — nobody was
  connected to her during this baseline window.
- **v (valence): -0.132 to -0.133**, essentially flat, mildly negative.
- **a (arousal): 1.000** on every poll — pinned at ceiling for the
  entire window.
- **asleep: false, consolidating: false** on every poll [EV] — she was
  awake and not in a dream/consolidation cycle throughout.
- **pair-bond states** [EV], all 4 polls: `lookup/joe_voice/wc/
  curriculum/joe/guala/c1/corpus` flat at **0.3** on every poll (the
  known recency-floor value, not evidence of "never contacted" per
  standing note); **`worldfeed` alone elevated and rising: 0.762 →
  0.773 → 0.781 → 0.781**, consistent with active worldfeed/audio
  consumption during this exact window.
- `recoveries(lifetime)`: **17218**, flat across all 4 polls (no
  recovery events fired in this ~52s window).
- `coord`: att=39890→39915, act=15961→15971 across the window — both
  climbing steadily tick-over-tick, i.e. actively accumulating.

---

## §8.4 — Ladder metrics

Identical on all 4 polls [EV] (no emission occurred in this window —
see §8.5 — so these are the lifetime-cumulative values as of the last
emission, not a live per-second computation; flagged so the reader
does not mistake "unchanged across 4 polls" for "not instrumented"):

| metric | value |
|---|---|
| mean_utterance_len | 1.0 |
| utterances_per_turn | 1.0 |
| question_rate | 0.0 |
| novel_wordbag_rate | 0.0 |
| novel_composition_rate | 0.0 |
| total_emissions | 1227 |
| awareness_ratio | 0.0 |

`question_rate`, `novel_wordbag_rate`, `novel_composition_rate`, and
`awareness_ratio` all reading exactly `0.0` — flagged here as a
baseline number to compare against post-audit measurement, not
interpreted further (that disposition belongs to §8A/§9's
spec-vs-implementation work, not this snapshot).

---

## §8.5 — Emission counts

- `ladder.total_emissions = 1227` (lifetime cumulative), flat across
  all 4 polls. [EV]
- `activity_history_summary.EMITTING`: `count: 4, total_ticks: 400`
  (this is a rolling/recent-history window per the tool's own
  semantics, not lifetime — far smaller than 1227, so it is a
  different, shorter-window counter; both are reported as distinct
  fields, not reconciled to each other in this pass). [EV]
- Zero emission-related events (`emission`,
  `emission_suppressed_no_presence`) appeared in the 50-event window
  pulled via `guala_get_events(since_tick=15060800, limit=50)`
  spanning tick 15061149–15061196 — every event in that window was
  `organism_experience_bound` (49) or `familiarity_persist_check` (1).
  Consistent with `conn=0.000` / all presence flags `false`: nobody
  was present to emit to during this baseline window. [EV]

---

## §8.6 — Organism population / divisions

Identical on all 4 polls [EV]:

- `organism_population: 106`
- `organism_growth.total_neurons: 106`, `n_initial: 64`,
  `total_divisions: 42`, `division_pool: 0.0`
- `n_q_over_0_5: 106`, `n_q_over_0_9: 106` — **100% of neurons above
  both quality thresholds**, all 106.
- Per-hemisphere: `em:16 pr:16 ep:16 sc:16 gp:8 sf:8 sv:16 aff:10`
  (sums to 106).
- `organism_worker`: `queued` toggled 0→1→0→0 across the 4 polls
  (transient, not sustained backlog); `item_ms_mean` **427.87–445.11ms**
  across the window; `item_ms_max` flat at **2187.76ms** (a historical
  max, not refreshed in this window); `dropped: 0` on all 4 polls.

---

## §8.7 — Save-durability state

Two distinct persistence layers observed, reported separately:

**EFS local save (`persistence_health`)** [EV], 4 polls:

| poll | tick | last_save_tick | gap (ticks) | last_save_timestamp |
|---|---|---|---|---|
| 1 | 15061148 | 15061142 | 6 | 2026-07-05T23:02:09Z |
| 2 | 15061159 | 15061142 | 17 | 2026-07-05T23:02:09Z |
| 3 (A) | 15061165 | 15061163 | 2 | 2026-07-05T23:03:12Z |
| 4 (B) | 15061171 | 15061163 | 8 | 2026-07-05T23:03:12Z |

Saves landed twice inside this ~52-second window (23:02:09Z, then
23:03:12Z — roughly a minute apart), keeping the tick-gap small
(2–17 ticks observed, i.e. seconds of unsaved work at any instant in
this window). `load_successful_at_boot: true` on every poll. This is
a healthy-looking steady-state save cadence — it does **not**
contradict the pre-audit fact that boots start with `last_save=(none)`
(that is specifically a cold-boot condition, not this running
instance's steady state, and this pass did not observe a boot).

**S3 backup lineage** [EV, `persistence_health.last_s3_backup`, flat
across all 4 polls]: `s3://dsf-ai-site-backups/guala/
2026-07-05_22-32-42/`, `file_count: 13`. Wall-clock gap from that
backup timestamp to this baseline's polling window (~23:02:38Z–
23:03:30Z): **≈30–31 minutes stale** relative to the EFS saves above.
Restorability of this backup is explicitly out of §8 scope (belongs to
§0.6's shadow-instance restore and §2's AWS truth) — **NOT MEASURED**
here.

---

## §8.8 — Out-of-scope items (explicitly NOT MEASURED this pass, with reason)

- `converse_timing` fresh measurement — prohibited by this subtask's
  instructions (mutating call, out of read-only scope). Cited instead
  (§8.2).
- Instrumented `recall_best` timing bounding the 6-7x gap — requires
  either a converse call or in-process instrumentation; neither
  available via the read-only bridge tools used this pass.
- 15-mechanism battery rows — not requested by this subtask; belongs
  to §8A (function test matrix).
- S3 backup restorability proof — belongs to §0.6/§2.

---

## §8.9 — Raw evidence log (method + verbatim data)

Tooling: `mcp__claude_ai_GualaLoom_Bridge__guala_status`,
`guala_get_events`, `guala_atlas_snapshot`. Wall-clock brackets taken
via `date -u +"%Y-%m-%dT%H:%M:%S.%3NZ"` immediately before/after
select calls (bash tool calls interleaved with MCP tool calls, so
brackets carry a few hundred ms to low-seconds of assistant-side
overhead — disclosed in §8.1's method note, not hidden).

`running_sha` on every poll: `168ef1bde3717e52efb85b894103de047e942617`
— matches `GL-HANDOFF-C1A-20260705-v1.md`'s `168ef1b` (task-def `:494`,
currently live). This confirms the §8.2 citation is evidence-consistent
with the SHA this baseline was taken at.

| # | shell ts before | tick | reads | vocab | last_save_tick | tick_rate |
|---|---|---|---|---|---|---|
| 1 | (untimed, first call) | 15061148 | 1762928 | 14064 | 15061142 | 0.53 |
| 2 | 2026-07-05T23:02:46.125Z | 15061159 | 1768340 | 14064 | 15061142 | 0.50 |
| 3 (A) | 2026-07-05T23:03:16.124Z | 15061165 | 1770854 | 14064 | 15061163 | 0.44 |
| 4 (B) | 2026-07-05T23:03:20.237Z→sleep 10s→23:03:30.239Z | 15061171 | 1773834 | 14064 | 15061163 | 0.43 |

`guala_atlas_snapshot` (1 call, taken alongside poll 1):
`tick: 15061153, total_strength: 770.92, n_live_bindings: 10874,
n_total_entries: 12764, decay_paused: "0"`. [EV] Not part of §8's
required fields but retained here as corroborating atlas-health
context (matches `atlas_health` embedded in the `guala_status` polls
within measurement noise, e.g. poll1's embedded atlas tick=15061148
total_strength=770.54 vs standalone snapshot tick=15061153
total_strength=770.92 — consistent, few-tick drift).

`guala_get_events(since_tick=15060800, limit=50)`: returned exactly 50
events, tick range 15061149–15061196, kinds: 49×
`organism_experience_bound`, 1× `familiarity_persist_check`
(`n_keys: 30`). Full word sequence and `has_sight`/`has_sound`/`senses`
values quoted in §8.0.

### Changelog
- v1 (2026-07-05, c1): initial §8 behavioral baseline capture, read-only,
  condition = ATTENDING_AUDIO (not the dispatch's READING example),
  running_sha 168ef1b (task-def :494). converse_timing cited from
  GL-HANDOFF-C1A-20260705-v1.md, not re-measured.
