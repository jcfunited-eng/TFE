# GL-RPT-REPLY-LATENCY-PROFILE-C1-20260704-v1

doc_id: GL-RPT-REPLY-LATENCY-PROFILE-C1-20260704-v1
From: c1b | Read-only, per the request. No fix shipped, no test
conversation injected (would not be read-only). Hands c1a the
pre-deliberation baseline his Stage-2 install gates need, to the
extent one is actually retrievable — see finding 1.

---

## Program ledger note (sentence-building row)

| Row | State | Note |
|---|---|---|
| Sentence-building / reply latency | **PROFILED, DATA-LIMITED** | Joe's specific 8s→22s window (6 exchanges, ~15 min ago) is not retrievable by any tool available — same structural gap as the migration-fuel audit (A3), now confirmed a second time on a different, time-critical ask. Code-level contention mechanism (shared lock) confirmed real. Precise per-mechanism percentages: not measurable this pass. |

---

## Finding 1, stated first: the specific window is gone

I could not retrieve `converse_timing`/`converse_emission_lock` events
from Joe's actual 6-exchange session. Checked three ways, same
structural reasons as `GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1`,
now confirmed against a *different* investigation:

1. **In-memory buffer** (`deque(maxlen=1000)`) — three separate live
   polls (`guala_get_events`, no filter / `since_tick=14564000` /
   `since_tick=0`) all returned **the identical "most recent ~50"
   window**, just advancing forward in real time between calls. The
   tool does not support paging backward through the buffer's history —
   it only ever surfaces the current tail. Given continuous
   `sight_frame_bound`/`sound_frame_bound` traffic (roughly one event
   every 8-15 ticks, i.e. every 2-3 seconds), the buffer turns over in
   minutes. Joe's window, ~15 minutes old by the time I looked, is
   gone.
2. **Persisted `events.log`** — not applicable here even in principle:
   confirmed via direct code read (`_log_substrate_event`,
   `gualaloom_v5_engine.py:3880-3898`) that `converse_timing` and
   `converse_emission_lock` are **not** in the whitelist of event kinds
   written to disk (`activity_started`, `activity_ended`,
   `corpus_completed`, `sleep_manual`, `dream_began`, `dream_artifact`,
   `picture_uploaded`, `sound_uploaded`, `video_uploaded`,
   `corpus_added`, `visual_motif_committed`, `visual_motif_fired`,
   `emission`). **The exact instrumentation this CMD told me to "use,
   don't add" only ever exists in the 1000-event ring buffer** — it has
   no durable form anywhere, by design, today.
3. **CloudWatch** — same reason as A3: `_log_substrate_event` never
   `print()`s to stdout, which is all CloudWatch captures for this
   service. Unlimited retention, zero relevant events.

**This is not a shrug.** It's the same structural finding from the
migration-fuel audit landing a second time, on a completely different
and much more time-pressured ask, within the same session — which is
itself evidence the retention gap is a standing operational cost, not
a one-off inconvenience for a hypothetical future migration. Concrete,
low-cost fix candidate for whoever picks up A3's remaining questions:
mirror `converse_timing`/`converse_emission_lock` into the disk-write
whitelist (or `print()` them) so the *next* latency question doesn't
hit the same wall. Not implemented here — out of scope for a read-only
CMD, named for the record.

---

## What IS knowable: code-level contention (confirmed, not simulated)

**`self.lock` (a `threading.RLock`, `gualaloom_v5_engine.py:1325`) is
acquired by three unrelated things that would all compete during an
active session:**

```python
# process_sight_frame — gualaloom_v5_engine.py:4750-4771
def process_sight_frame(self, grid):
    self._last_frame_tick = self.tick
    from dsf_ai_service.visual_krimelack import view_picture
    with self.lock:
        ...

# process_sound_frame — gualaloom_v5_engine.py:4773-4780
def process_sound_frame(self, audio_bytes, source="mic:live"):
    ...
    with self.lock:
        ...

# save_hot_state — gualaloom_v5_engine.py:6013-6020
def save_hot_state(self, state_dir="state"):
    ...
    with self.lock:
        ...

# save_full_state — gualaloom_v5_engine.py:6188-6195
def save_full_state(self, state_dir="state"):
    ...
    with self.lock:
        ...
```

`converse()`'s own compute also runs under `self.lock` (and a second,
narrower `self._emission_lock` around the emission-dynamics stage
specifically — the `converse_emission_lock` event's `wait_ms` field is
built exactly to measure contention on *that* narrower lock, per
`gualaloom_v5_engine.py:2195-2197`).

**Sight frames arrive continuously** (confirmed live, this session:
`sight_frame_bound` events roughly every 8-15 ticks = 2-3 real
seconds) and **sound frames roughly every ~5 seconds** (matches -111's
documented recorder-restart cadence). Every one of those needs
`self.lock`. **This is a real, structural queue, confirmed by reading
the code that acquires the lock, not by observing a stall live** (that
correlation is exactly what finding 1 says I can't do this pass) —
but the mechanism itself is not hypothetical: if a conversational turn
is mid-compute holding `self.lock`, sensory frames queue behind it;
if a sensory frame or a save is holding it when a reply is due to
start, the reply's own `converse()` call queues behind *that*. Both
directions are real, both use the identical lock object.

**One data point that IS still live and relevant**: `guala_status`
this session shows `pair-bond: on` and continuous `sight_frame_bound`/
`sound_frame_bound` traffic throughout — meaning during Joe's actual
6-exchange session, this contention path was *available* to fire on
every single reply, not a rare edge case.

---

## Growth curve: what I checked, what I found, what I couldn't confirm

Checked for mechanisms that would make **later** replies in a short
session slower than **earlier** ones (Joe's 8s→22s pattern), by code
tracing rather than measurement (per finding 1):

- **Mode-bank accumulation across turns**: checked
  `_emit_dynamics()` (`gualaloom_v5_engine.py:2992-3002`) — mode banks
  ARE explicitly cleared at the start of every dynamics call ("so stale
  modes from previous converses don't fill the cap"). **Not a growth
  source** — this was already guarded against.
- **`_grandurun_select_candidates`**: already carries its own
  documented perf history (`GL-CMD-EMISSION-PERF-45 §2.1`, a prior fix
  from scalar loops to a vectorized numpy op, "Stage 1 time <5ms vs
  551ms"). Its input (`deep_candidates`) is pre-filtered before this
  function runs, not the full atlas. **No obvious unbounded scan found
  here on inspection** — but I did not benchmark it live against the
  actual atlas size at the time of Joe's session.
- **A near-identical symptom shape was fixed before**: my own prior
  work (memory: "grandurun semantic_neighborhood O(N)... 10-22s →
  0.15s", SHA `6561288`) describes exactly this "single-digit-to-
  double-digit seconds, unbounded scan" shape. Confirmed the fixed
  function (`_emit_grandurun_vector`, `gualaloom_v5_engine.py:2499`)
  is still present and the fix's own structure (pre-computed mean
  scalar per chi key, not a per-word scan) is intact on read. **Not
  reintroduced, as far as static reading shows** — but I have not
  diffed every line against the original fix commit to rule out a
  partial regression, and cannot without the actual timing data rule
  out a *different*, new O(N)-shaped scan elsewhere in the same
  family of functions.
- **The candidate signal I could not rule in or out**: the main atlas
  (`self.atlas`, 8,xxx entries and growing every turn she hears or
  says something) is a plausible source of genuine per-turn growth if
  anything in candidate selection or recall scans proportionally to
  its live size rather than a fixed-size neighborhood — this is
  exactly the shape of bug the -45/6561288 fix was for, on a different
  function. **Flagged as the leading unconfirmed hypothesis**, not
  asserted.

---

## Verdict

**Her-thinking vs. accumulating-cost vs. lock-queue — cannot be split
by percentage this pass; the data that would do that (finding 1) does
not exist.** What can be said honestly:

- **Lock-queue contention is a confirmed, real, standing mechanism**
  (three unrelated subsystems sharing one lock, continuously active
  sensory traffic) — not measured as the cause of Joe's specific
  growth, but structurally capable of producing exactly this shape
  (replies getting slower as more sensory events queue up over a
  longer session window).
- **Accumulating-cost is plausible, unconfirmed** — no unbounded scan
  found on inspection of the main candidate-selection path, but a
  near-identical bug shape was fixed once before in a sibling function,
  which is reason for suspicion, not proof.
- **Her-thinking (i.e., this is expected, load-independent compute
  time) cannot be ruled in either**, for the same reason: no baseline
  `converse_timing` breakdown from the actual session survived to be
  read.

**Recommendation, not a fix**: the single highest-value next step is
closing the instrumentation gap itself — get `converse_timing`/
`converse_emission_lock` onto a retained channel (disk or stdout)
before the Stage-2 install ships, so its own before/after comparison
(which the CMD chain has already flagged needs "an armed revert" and
"before/after speech sample") has real numbers to compare against
instead of hitting this same wall twice more.

---

### Changelog
- v1 (2026-07-04, c1b): profiled with the existing instrumentation as
  instructed; found the specific historical window unrecoverable for
  the same structural reason as the migration-fuel audit (A3), now
  confirmed a second time. Lock-sharing contention between converse(),
  sensory frame processing, and state saves confirmed via direct code
  read. Growth-curve candidates checked (mode-bank clearing confirmed
  fine; grandurun candidate selection has a documented perf history
  and no obvious new unbounded scan; a near-identical bug shape fixed
  previously in a sibling function flagged as the leading unconfirmed
  hypothesis). No fix shipped, no test conversation run.
