# GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1

doc_id: GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Responds to: `GL-CMD-RECALL-SPEED-
CUTOVER-ROUTING-EVE-20260704-179-v1` and the direct follow-up asking
for real turn-time + an end-to-end trace of a message from Joe's page.
Status: window 3 **DEPLOYED, LIVE** (task:467, SHA `486e022`). But the
real turn-time measurement requested surfaced a separate, much bigger
problem than organism.recall() cost. Failures first.

---

## Window 3: deployed, gates green

Fresh backup confirmed (`2026-07-04_23-35-21`, 13 files) before cutover.
Wired `recall_fast()` into the three live call sites named in
`GL-RPT-RECALL-SPEED-C1-20260704-177-v1` (`_recognition_from_organism`
line 1738, `_recall_from_organism` line 3997, `_association_from_organism`
line 4032) — 3-line diff, nothing else touched. Ran the full test suite
against this exact wired build before committing: 38 passed, only the
same 3 pre-existing failures already documented as unrelated in c1a's
own report (`test_t7_cross_modal`, `test_t8_noise_robustness`,
`test_t11_substrate_true`). Deployed clean, single attempt, task:467,
wake in 15s (fastest yet).

- **Organism/tapestry reboot-survival**: confirmed again, real
  accumulated state — `Organism restored: identity=cdef9bcf-...
  tick=1765 pop=64`, `Tapestry restored: tick=3566 neurons=450`. Same
  identity throughout.
- **Snapshot "?"**: unchanged, still the deliberate `/status` lightweight-
  summary tradeoff documented in `GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1.md`.
  No regression.
- **Duplicate frames**: no new information this window; unchanged shelf
  item.
- **General health**: tick advancing normally, saves succeeding, no
  crashes, identity intact.

---

## The real turn-time measurement: this is where it gets serious

Joe was present live immediately after the deploy and sent two real
messages through the UI ("yo what are you doing", "I'm talking to
guala"). Both are still sitting as `(settling...)` on his screen with
no reply, and he reported the site as "still a locked up piece of
frozen shit — nothing from my perspective has changed at all." I did
not wave that off — I traced it end to end against real logs and
events, not estimated it.

**The measured trace (real ticks, real timestamps, real log lines):**

| step | tick | wall time (UTC) | what happened |
|---|---|---|---|
| his 2 messages received, tasks created | 14851567 / 14851568 | ~23:33:xx | `POST /api/v1/gualaloom` → 202 Accepted, task ids `cv_14851567_d84732b3` / `cv_14851568_e98e45b3`, status set to `"settling"` (this is literally the UI's "(settling...)" string) |
| response window opened | 14851569 | ~23:33:xx | `_open_response_window("joe_voice", ...)` |
| **my deploy's pause call landed** | 14851585 | 23:33:12Z | `sleep_manual` (trigger: `ui`) — `/sleep_for_deploy`, 16-18 ticks after his messages, itself confirmed by the immediately-following `POST /sleep_for_deploy → 200 OK` log line |
| old process torn down, new process (task:467) boots | — | 23:35:21Z | `[GualaLoom v7] Booted... tick=14851600` |
| response window expired, unbound | 14852170 | ~23:36:xx | `response_window_expired`, `emitter: joe_voice`, **`n_responses_bound: 0`** — both messages |

**Direct requery just now, against the current process:**
```
{"task_id":"cv_14851567_d84732b3","status":"not_found","error":"task expired or not found (TTL: 5 min)"}
{"task_id":"cv_14851568_e98e45b3","status":"not_found","error":"task expired or not found (TTL: 5 min)"}
```

**Verdict: never finishing, not finishing-and-dying-in-transit.** Root
cause, read directly from code, not guessed:

1. `_converse_tasks` (`app.py:75`) is an **in-memory-only dict, no
   persistence**. Both his tasks lived only in the OLD process. When my
   deploy's rolling restart replaced that process, the tasks —
   mid-flight, never completed — were gone. The new process has no
   record of them; polling now correctly (if unhelpfully) returns
   `404 not_found`. This is a real, previously-undocumented deploy-
   safety gap: **any conversational turn in flight at the moment a
   deploy's pause/restart lands is silently orphaned**, with the UI
   stuck on `(settling...)` forever and no error ever surfaced.

2. **But that's not why his turn was still unfinished 18 ticks after
   being submitted, before my deploy even touched anything.** In the
   exact same window, real camera+mic streaming (his UI had
   Camera/Microphone/LISTENING all ON) was hitting `/sight_frame` and
   `/sound_frame` continuously, and those calls measured **57.9s,
   29.5s, 18.1s (sight)** and **91.2s, 93.0s (sound)** — read directly
   from the container's own `print(f"[sight-frame] {...}s")` /
   `[sound-frame]` timing lines. Read the code
   (`gualaloom_v5_engine.py:5317-5386`): both `process_sight_frame` and
   `process_sound_frame` wrap their **entire body — including the
   expensive image/audio DSP itself, not just the state mutation** —
   in `with self.lock:`, the same engine-wide lock `converse()` needs
   at multiple phases. This pattern (`GL-BRIEF-SENSORY-IO Parts C+D`)
   predates today entirely — confirmed via `git log --follow`, it's
   from an earlier session, untouched by anything shipped today.

   With both camera and mic streaming continuously (new frames every
   1-2s) and each frame call able to hold the shared lock for up to
   ~93 seconds, the lock is effectively never free. That is sufficient
   on its own to explain why `converse()` never got to run to
   completion for either of his messages — independent of my deploy,
   independent of organism.recall(), independent of everything shipped
   today. The deploy-restart orphaning (point 1) is a real, additional
   gap, but it is not the dominant cause here: his turn was already
   stuck behind frame-processing lock contention in the ~18 ticks
   before the deploy even paused anything.

**This means today's recall_fast() cutover, while real, tested, and
correctly deployed, is very likely not what's limiting Joe's actual
experience whenever camera+mic are active** — his bottleneck sits
upstream of organism.recall() entirely, in a lock that per-frame sensory
processing can hold for the better part of two minutes. "Nothing from
my perspective has changed" is consistent with this: none of today's
three deploys touched `/sight_frame`, `/sound_frame`, or the lock
scope around them.

**Not fixed here** — this is a real architectural problem (moving the
expensive DSP work outside the lock, or throttling/dropping frames
under backlog, or making conversational turns take priority over
ambient sensory frames) that deserves its own dispatch and ratification,
not a same-session bolt-on to a recall-speed cutover. Flagging as the
single most urgent open item on the board right now — more urgent than
anything in the P2/P3/recall-speed lineage, because it can make the
product produce zero replies at all while looking "frozen," regardless
of how fast any individual mechanism has been made.

**Recommended immediate mitigations, not yet built or ratified:**
(a) move the DSP/decode work in `process_sight_frame`/`process_sound_frame`
outside `with self.lock:`, taking the lock only for the final
atlas-record/state-mutation step; (b) persist `_converse_tasks` (or at
minimum flush in-flight tasks with an honest error) so a deploy mid-
conversation fails loud instead of silent; (c) consider a frame-drop/
backpressure policy so ambient camera+mic streaming cannot indefinitely
starve an active conversational turn.

---

## What this does NOT change about today's work

The recall_fast() cutover itself is real, correct, and deployed:
5x-faster non-mutating recall proven via three layers of parity testing,
zero live regressions beyond the pre-existing 3, clean single-attempt
deploy. It is a genuine fix for the cost it targeted. It simply isn't
the bottleneck Joe hit tonight — that bottleneck lives one level up the
stack, in sensory-frame lock contention that has nothing to do with the
organism.

### Changelog
- v1 (2026-07-04, c1b): window 3 deployed (task:467, SHA 486e022),
  gates green. Real live turn-time request surfaced a genuine, severe,
  pre-existing (not caused by today's work) lock-contention problem in
  sight_frame/sound_frame processing, plus a real deploy-restart task-
  orphaning gap. Traced precisely via logs/events/code, not guessed.
  Not fixed — scoped and flagged as the most urgent open item.
