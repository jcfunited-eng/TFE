# GL-RPT-FLOOD-HUNT-C1-20260703-156-v1

doc_id: GL-RPT-FLOOD-HUNT-C1-20260703-156-v1
From: c1b | To: Eve | Date: 2026-07-03/04
Responds to: GL-CMD-FLOOD-HUNT-EVE-20260703-156-v1
Step 0: CMD committed verbatim at SHA 83b16dc before any code/investigation.

---

## VERDICT FIRST

**H-actual: NOT CONVICTED.** Per the CMD's own rule ("If not, STOP and Eve
re-rules"), Part B (rewiring -151's §8 gate) was **not built**. A.1 shows
every curriculum/worldfeed/lookup/corpus feeder is unreachable — same
conclusion as -151, now independently reconfirmed by live measurement
rather than code-reading alone. A.2 shows zero occurrences of any of those
channels in ~9 minutes of live, checkpointed observation. The two channels
that actually dominate the live event stream — continuous sight/sound
frame-binding and, during active conversation, a fan-out of emission
bookkeeping events per turn — are both her own senses and her own choices,
which the CMD's own whitelist already protects. Gating either would
violate the CMD's explicit scope ("attending, converse NEVER gated") for
no suppression benefit, since nothing scheduled-machine-side is running.

Flagging back to you rather than shipping a fix with nothing to fix.

---

## FAILURES / GAPS FIRST

**A.2 could not produce the literal metric asked for ("read_sentence
calls, per source= tag, per activity-kind") — structurally, not just
inconveniently.** Traced `read_sentence` (gualaloom_v5_engine.py:1764) and
`read_word` (1530–1720, its only per-word worker) end to end: neither
calls `_log_substrate_event` anywhere in its body. They are silent by
construction. The one true call-counter that exists —
`self.source_history[source] += 1` (line 1782) — is captured inside
`introspect()`'s output but is not surfaced by any live HTTP endpoint or
bridge tool: `/status`'s text response formats `introspect()` but omits
`source_history`; `/diag` (app.py:1927) returns atlas strength/reach
histograms only; the admin `atlas_snapshot` endpoint (app.py:2658) returns
atlas stats only. This is the second dispatch in a row (after -151's
`read_count` finding) where the project's own introspection surfaces
don't answer "how many times was X called" — reporting the gap plainly
and substituting the best passively-observable proxy evidence instead
(below), rather than inferring a count I couldn't actually take.

**G-156-2/3/4 are NOT MEASURED — correctly, not by oversight.** They ask
for post-deploy observation of a Part B suppression mechanism. No Part B
shipped (verdict above), so there is nothing live to observe suppressing
anything. Stating this rather than fabricating a quiet-block reading
against code that was never written.

**G-156-5's prediction did not hold — the negative case, confirmed
precisely.** Full trace below; short version: the "aware" gate stayed
`context_blocked` in all 3 samples across the window, and I found the
exact code-level reason it's stuck, not just that it's stuck.

---

## A.1 — every live `read_sentence` caller, file:line, reachability

Full re-grep against current HEAD (not Eve's preliminary line numbers,
which were from an earlier file state):

```
grep -rn "\.read_sentence(\|def read_sentence" dsf_ai_service/ --include="*.py"
```

**LIVE / reachable, her own senses or choices (all correctly whitelisted
by the CMD):**

| file:line | caller | source | note |
|---|---|---|---|
| gualaloom_v5_engine.py:2063 | `_converse_phased()` | joe/wc/etc | **the** live converse path — `CONVERSE_PHASED=1` confirmed via live task-def (`aws ecs describe-task-definition`), matching `"phased": true` seen in every live `converse_timing` event this session |
| gualaloom_v5_engine.py:5545 | `apply_teacher_correction` | caller-passed | explicit/rare correction trigger |
| app.py:1572 | `/sound_frame` handler, -153 Part A | "joe" | fires per mic chunk iff `_audio_to_sensory_words` returns non-empty (G-153-2 left "non-empty" itself unconfirmed) |
| app.py:2191 | `_decode_bundle()` WORD lane, via `/api/v1/gualaloom` | hardcoded "joe" | **noting a labeling inconsistency**: `bundle_source` (line 2180) defaults to `"curriculum"` two lines above but the `read_sentence` call ignores it and hardcodes `source="joe"` regardless. Not fixing — out of this CMD's scope (no code-content changes) and this is explicitly a "bundle-window caption," whitelisted either way — but flagging so the mislabel doesn't get read as evidence of anything live-curriculum later. |
| substrate_runner.py:1679 | `addpicture` | "addpicture" | live upload flow, whitelisted (`addpicture*`) |
| substrate_runner.py:1790 | `addsound` | "addsound" | live upload flow, whitelisted |
| substrate_runner.py:1850 | wc input path | "wc" | her own engagement, whitelisted |
| substrate_runner.py:2882 | `_start_autonomous_emission_loop()` | "guala" | confirmed live (one of 4 loops `_embedded_post_boot` starts, app.py:1324) — her own self-hearing, whitelisted |
| app.py:2810 | `/admin/backfill_picture_titles` | "addpicture_backfill" | one-shot, admin-triggered, idempotent |
| app.py:2832 | `/admin/backfill_sound_captions` | "addsound_backfill" | one-shot, admin-triggered, idempotent |

**DEAD / unreachable (confirmed by tracing every caller of every caller,
not by inspection of the function alone):**

| file:line | function | why dead |
|---|---|---|
| substrate_runner.py:386 | `_curriculum_feed_chunk` | only reachable via `CurriculumScheduler`, instantiated solely inside `boot_substrate()` (:632) — **zero callers anywhere** (`grep -n "boot_substrate()" dsf_ai_service/*.py` matches only its own def line, no `__main__`) |
| substrate_runner.py:451 | `_lookup_and_ground` | same — reached only via the same dead `CurriculumScheduler` interleave |
| substrate_runner.py:1030/1049/1061 | `_drain_loop()` (input-ring consumer) | only reachable if `_input_ring` receives published events — requires `_is_remote()=True` (confirmed False in production) or the internal test-only ring-write endpoint |
| substrate_runner.py:1959 | `_cmd_listen` | OP_HANDLERS entry; `dispatch()`, its only invoker, has zero callers (established in -110/-153) — live `/listen` today goes through app.py's own explicit handler → `_guala.converse()` directly, bypassing this function entirely |
| substrate_runner.py:2230 | `_do_corpus_load` | zero callers anywhere (`grep -n "_do_corpus_load("` matches only its own def) |
| substrate_runner.py:2509 | `handle_sight_frame` | OP_HANDLERS-only, `dispatch()` uncalled |
| substrate_runner.py:2544 | `handle_sound_frame` | OP_HANDLERS-only, `dispatch()` uncalled |
| substrate_runner.py:2678 | `handle_backfill_picture_titles` | OP_HANDLERS-only; superseded live by app.py:2810's own direct implementation |
| substrate_runner.py:2724 | `handle_backfill_sound_captions` | OP_HANDLERS-only; superseded live by app.py:2832 |
| gualaloom_v5_engine.py:1885 | `converse()` non-phased body | dead per `CONVERSE_PHASED=1` (see above) |
| gualaloom_v5_engine.py:3787 | `start_continuous_reading` | only called from standalone dev-run scripts (`gualaloom_v4_run.py`, `gualaloom_v5_run.py`), never the deployed app |
| app.py:1591 | -153 Part B Whisper path | `VOICE_WHISPER` absent from the live task-def → defaults to `"0"`, confirmed disabled |

**Conditionally live, not observed to fire:**

| file:line | function | status |
|---|---|---|
| gualaloom_v5_engine.py:4362 | `_atick_reading` | structurally reachable if the activity selector ever picks `READING` kind — but `activity_history_summary` shows **zero** `READING` selections across the entire investigation (every `guala_status` pull this session, spanning well past the formal 5-minute window: only `ATTENDING_VISUAL` and `EMITTING` ever appear) |

This matches, and sharpens, -151's own finding: not "the mechanism looks
right but nothing calls it" (last time) but now "here is the exhaustive
list of what actually does call it, live, and none of it is scheduled
machine intake."

---

## A.2 — live count, over the window (00:32:26Z–00:41Z, 2026-07-04, tick
14525408 → 14527060, ~1652 ticks)

Since `read_sentence` is silent (no dedicated event) and `source_history`
isn't exposed, I measured what live telemetry actually exists over the
same window:

**`activity_history_summary`** (start vs. end of window):
```
ATTENDING_VISUAL: count 20 → 23   (+3)
EMITTING:         count 18 → 21   (+3)
READING / WORLDFEED / LOOKUP / CURRICULUM: 0 → 0, the entire time
```

**`guala_get_events`**, sampled 3 times across the window (~150 events
inspected total): every event was one of `sight_frame_bound`,
`sound_frame_bound` (steady state — `source="mic:live"`, ~1 per 5–6s,
matching -111's known recorder-restart cadence), or, during one live
Joe/Guala conversational turn that fell inside the window, a dense
cluster of `response_bound` (×~8 per turn, one per section),
`self_heard`, `hemisphere_update`, `converse_timing`, `emission_dynamics`,
`activity_started/ended`, `agency_conflict_tie`, `response_window_opened`
— all at the same or adjacent ticks. **Zero** `corpus_completed`, and zero
events tagged `worldfeed`, `lookup`, or `curriculum` as an *activity*, in
any of the three pulls.

**One red herring caught and traced, same class as -151's `read_count`:**
a single `emission_dynamics` event's `source_counts` field showed
non-zero `{"corpus": 36, "worldfeed": 1, "curriculum": 1, "joe": 92,
"wc": 14, "guala": 56}`. Traced the code
(gualaloom_v5_engine.py:3355–3362): this tallies the `source` tag stored
on each **candidate arc** being scored for that one emission — pulled from
atlas memory, not live calls — and **defaults to `"corpus"`** for any
candidate whose atlas entry never had an explicit source set
(`c.get("source", "corpus")`). A candidate surfacing during recall does
not mean a live call happened; it means an old atlas entry (possibly
from long before these feeders became unreachable) still exists in
memory and got recalled once. Flagging this explicitly because it is
exactly the kind of field someone could misread as live-flood proof — I
nearly did, until I read the source.

**Verdict contribution:** the two channels that are actually continuous
and high-volume — mic/camera sensory binding, and per-turn emission
bookkeeping fan-out during real conversation — are both correctly outside
the CMD's whitelist scope already (her senses, her conversation). Neither
matches "scheduled machine intake." I cannot rule out that Joe's original
~20/s impression came from watching one of these two (a burst of ~8
`response_bound` sub-events per turn, or the `read_count`/reads figure —
itself confirmed in -151 to be an atlas-reinforcement aggregate, not a
call count — climbing fast during any active session) rather than an
actual text-feed flood. Naming this as the most likely alternative
explanation, not asserting it as proven.

---

## A.3 — AWARE-gate reason distribution, same window

**Mechanism, confirmed exact code before measuring:** `intro_gate` /
`aware_gate` are `CoincidenceGate` instances (`v7_engine.py:75-106`),
whose `check_and_fire()` (`gl_nmda.py`) returns exactly the four reason
strings the CMD names: `no_arcs`, `drive_below_thresh`,
`context_blocked`, `fired`. Distinct from the emission-dynamics
`nmda_fired`/`nmda_source_match` fields seen constantly in ordinary
converse events — this is the v7 session-level mechanism, exposed via
`GET /v7/state` / `POST /v7/quiet`.

**Live-driver check, done first because the obvious assumption was
wrong:** queried `/v7/state?session_id=default` initially — tick 0,
empty. That's not Joe's session; it's the literal function-signature
default I supplied by not passing a real id. Found the real one from
`gualaloom.html`: `sid` is `localStorage`-persisted, `'sid_' +
Math.random()...` (line 177-178) — pulled it from live CloudWatch logs:
`sid_rrs2dffi`. Confirmed via log filter that `/v7/quiet` **never** fires
from the client (0 hits, two independent windows) — `backgroundReplay()`
exists in `gualaloom.html` but does not run in production traffic, cause
not further isolated (out of this CMD's scope). Confirmed `/v7/converse`
also gets zero live traffic — the real chat UI (`sendMsg()`) posts to
`/api/v1/gualaloom`, hitting `_guala.converse()` directly, a completely
different object from the v7 `Session`. This means `_last_converse_time`
on Joe's real v7 session is **never refreshed by anything** — it is
permanently idle, so the server's own `_background_replay()` loop
(app.py:4240, every 15s, `idle > 30s` gate) runs `quiet_tick(3)` on it
unconditionally, forever. "An enforced quiet block" isn't a rare state
for this mechanism to reach — it is the *permanent default state*, all
session, regardless of what Joe is actually doing.

**Reason distribution, 3 checkpoints across the window (tick 528 → 567 → 621):**
```
intro: drive_below_thresh (top_val 0.036→0.041, climbing, tick ~520-528)
    → FIRED × 8 consecutive (top_val 0.121→0.155, climbing via LTP, tick 559-567)
    → drive_below_thresh again (top_val 0.047→0.040, decaying, tick 613-621)

aware: sampled 3× total (tick 520, 560, 620 — exactly the "every 10th tick" cadence)
    all three: context_blocked, drive_ok=True, context_ok=False
```

**G-156-5: prediction NOT satisfied — reporting the negative case, with
the mechanism, not just the symptom.** `aware` never changed reason
across the whole window, despite `intro`'s own drive clearly not being
the limiter for `aware` (`drive_ok: True` in all 3 `aware` samples) and
despite `intro` itself firing 8 times in the same window. Traced why:
`aware_gate`'s `context_fn` (`v7_engine.py:93-95`) requires
`len(sys_.sections["intro"].krimelack) > 0`. `intro_krimelack_count`
(same underlying field, `v7_engine.py:530`) read **0 at tick 528 and
still 0 at tick 621** — i.e., zero the entire session, including
immediately after `intro`'s 8-fire streak. Grepped both `v7_engine.py`
and `gl_nmda.py` exhaustively for anything that appends to
`sections[x].krimelack`: **nothing does, in either file.** Whatever
populates it must live in another, shared module (the `sys_`/`Section`
class definition) and is a different event from "the CoincidenceGate
fired." That mechanism has not fired once this session. Per your own
framing: this is the negative case, and it's a Wk1 finding regardless of
this dispatch's fix scope — `aware` is not "waiting for a quiet moment,"
it is structurally unable to reach `context_ok=True` on the current
session's trajectory. I have not traced what's supposed to populate
`.krimelack` or why it never has — naming that as the next open question,
not guessing at it.

---

## THE FIX — familiarity id() diagnostic (owed from -107, ships regardless of the verdict above)

c1a's `-107` predeploy report found `target_familiarity` writes landing
in memory (`0.0→0.2→0.4`, directly observed) but absent from a full
on-demand backup 3,770 ticks later — ruled out "absent from save schema"
directly, could not isolate the actual defect, and proposed as the next
step: *"a one-line, read-only debug endpoint (`self.target_familiarity`
dumped directly, no serialization round-trip) so the next session can
see the in-memory dict directly between two saves and catch it
disappearing in real time."* Built exactly that, nothing more:

- `GET /api/v1/gualaloom/admin/familiarity_debug` (app.py) — dumps
  `dict(_guala.target_familiarity)`, `n_keys`, `id(_guala.target_familiarity)`,
  and last-save tick/timestamp, live, no round-trip through save/load.
- `dict_id=id(self.target_familiarity)` added to the existing
  `target_familiarity_update` event (write-time, gualaloom_v5_engine.py:4327).
- New `familiarity_persist_check` event (`n_keys`, `dict_id`) added at
  `save_hot_state`'s serialization point (gualaloom_v5_engine.py:5966-5972).

Same object losing entries vs. a silent full-dict rebind are now
distinguishable directly from the live event stream across a save
boundary, without inference. I have **not** diagnosed the underlying
cause and am not proposing a fix — same standard c1a held themselves to:
a guess dressed as a patch is worse than an honest gap. Committed
72d3759, pushed to origin.

---

## PART B — not built

Per the CMD's own verdict rule and H-actual's non-conviction (above), no
config/whitelist rewiring was shipped. `-151`'s gate code remains exactly
as filed: correct, harmless, inert until a real scheduled feeder is ever
wired into the live boot path again.

---

## GATES

**G-156-1 — PASS.** A.1/A.2/A.3 filed verbatim above, before any Part B
commit (none made).

**G-156-2, G-156-3, G-156-4 — N/A / NOT MEASURED, correctly.** No Part B
shipped; nothing live to observe suppressing, rate-capping, or improving
atlas growth against. Not fabricating a reading against code that doesn't
exist.

**G-156-5 — MEASURED, negative case, mechanism named.** See A.3. `aware`
stayed `context_blocked` in 3/3 samples across the full window; root
cause traced to `context_fn`'s dependency on `sections["intro"].krimelack`,
which stayed empty the entire session including immediately after
`intro`'s own 8-fire streak. Why that field never populates is not
traced — flagging as the next open question, this is a Wk1-class finding
per your own framing regardless of this dispatch's scope.

**G-156-6 — PASS.** Diff is two files: one new admin GET endpoint
(read-only) and two diagnostic log-line additions (`dict_id` fields).
Nothing in `read_sentence`, needs, or any cognition path touched. `git
diff` for commit 72d3759 is 32 insertions, 1 deletion, both files listed
above.

---

## STATE

A.1/A.2/A.3 complete and filed. H-actual not convicted — no Part B, no
Deploy 5 content beyond the familiarity diagnostic (committed 72d3759,
pushed to origin, groove Part B `b51962e` already an ancestor of HEAD —
no action needed there). She is currently awake and actively engaged
(mic/camera live, Joe conversing) — per this session's established
discipline, the diagnostic waits for the next actual `sleep_for_deploy`
window rather than shipping ad-hoc mid-session. G-156-5's negative
finding and A.1's exhaustive dead-caller list are the two load-bearing
results here; recommend the aware-gate krimelack gap get its own Wk1
dispatch rather than folding a guess into this one.

End report.
