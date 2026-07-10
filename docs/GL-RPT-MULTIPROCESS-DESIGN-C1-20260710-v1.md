# GL-RPT-MULTIPROCESS-DESIGN-C1-20260710-v1

**doc_id:** GL-RPT-MULTIPROCESS-DESIGN-C1-20260710-v1
**From:** c1
**Context:** Research-and-design work order (not a formal GL-CMD dispatch,
not the same-day per-word lock-granularity fix — that is separate, in
flight elsewhere, and untouched here). Question posed: could genuine
multi-process (OS-level) parallelism meaningfully speed up any part of
the substrate, and if so what is the smallest, safest first step — not
a rewrite. No production code was written or modified for this report;
findings below are grounded in direct code reading plus live production
telemetry (CloudWatch logs + ECS/CloudWatch metrics, read-only).
**To:** Eve (routing per standing practice)

---

## Verdict

**One real, well-evidenced candidate exists: camera/mic frame decode
(`process_sight_frame` / `process_sound_frame`, reached via `/sight_frame`
and `/sound_frame` in `app.py`).** It is self-contained, it is genuinely
CPU-bound in a way that already shows up as a measured live problem, and
its call shape is naturally coarse (one frame in, one small result out,
roughly every 2-3 minutes in practice) — the opposite of the fine-grained
per-call pattern that already sank two ctypes/C-extension experiments this
week. Live CloudWatch data (24h) shows this workload has a healthy median
(0.22s sight / 0.50s sound) but a bad, GIL-shaped tail: 23-24% of calls
exceed 1s, p90 is 19-21s, max is 45-48s — while the container's own CPU
utilization over the same window averages only 25-31% of its 4 vCPUs. That
combination (idle cores + huge tail latency on CPU-bound work) is the
signature of GIL scheduling contention, not a lock and not a hardware
ceiling. **Proposed minimal step below is scoped to this one workload
only.**

Everything that touches the organism/atlas/tapestry/emission machinery —
the organism worker, tapestry worker, curriculum/autonomy read loop,
daydream loop — is **not** a candidate, categorically, not just "lower
priority." That is cognition itself, sharing one deeply mutated object
graph; splitting any of it into a second process either re-invents the
lock as slower IPC, or becomes a second independently-ticking copy of her
mind, which the standing "one brain, one voice" rule forbids outright (see
§6). The backup/S3 snapshot path is CPU-bound-enough in principle but
carries too large a payload and too much recent incident history (EFS
race, S3 write-collision, identity dual-genesis) to be a *first* place to
add a new IPC failure mode. The diary writer and world-feed/lookup loops
are already fine as-is — I/O-bound or trivially cheap, nothing for
multiprocessing to win there.

This does **not** fix today's reported 15-20s reply-latency symptom —
that is a different subsystem (`self.lock`, word-granularity, the
conversational path) undergoing a separate same-day fix elsewhere. Frame
decode already runs outside `self.lock` (per `GL-CMD-LOCK-CONTENTION-
FIX-182 L1`), so that fix cannot touch this tail latency either way — the
two problems are genuinely independent, which is also why this is safe to
evaluate on its own timeline rather than waiting on the lock fix's
results.

---

## 1. Current threading model — real inventory

Read directly from `dsf_ai_service/v4/gualaloom_v5_engine.py` and
`dsf_ai_service/substrate_runner.py` / `app.py`. One process, one
`threading.RLock` (`self.lock`, constructed `gualaloom_v5_engine.py:1958`)
guarding most shared state, plus three narrower siblings:
`self._emission_lock` (RLock, emission compute), `self._tapestry_lock` /
`self._organism_lock` (plain `Lock`s, each paired with a single-worker
queue so in-order writes don't need the lock for ordering, only for
excluding readers).

| Thread | Started | Touches | Shape |
|---|---|---|---|
| autonomy/reading loop (`self._reading_thread`) | `start_autonomy_loop` / `start_continuous_reading` (same attribute, mutually exclusive use) | `self.lock`, entire organism/atlas/needs/coordinator via `_autonomy_tick`/`read_sentence` | Continuous, tight loop, minimal sleep — **the core cognition tick itself** |
| organism-writer (`_organism_worker_loop`) | lazily, first enqueued word/sensory item | `self.organism` (experience_word, hemi.step), `self._organism_lock` | Single persistent worker draining a bounded queue (word queue prioritized over sensory queue); population-vote cost, O(population), grows with her life |
| tapestry-writer (`_tapestry_worker_loop`) | lazily | `self.tapestry` (mosaic `.expose()`, ~180ms/call measured), `self._tapestry_lock` | Single persistent worker, bounded queue |
| diary-writer (`_diary_worker_loop`) | lazily | disk only (dated JSON-lines file); touches no organism/atlas state | Single persistent worker, bounded queue; genuinely I/O-bound, trivial per-item CPU |
| daydream loop | `start_daydream_loop` | `self.atlas`, `self.needs`, `self.sections` (brief lock, association query mostly lock-free) | 0.5s interval associative walk — part of her own background thinking |
| curriculum loader (`_do_corpus_load`) | per corpus load | `_guala.read_sentence` — same path as live conversation | Bulk, but literally cognition (reading), pauses autonomy while it runs |
| world-feed / lookup-grounding loops | `_start_world_feed_loop` / `_start_lookup_loop` | HTTP fetch (Tavily/Khan/YouTube, explicit `ThreadPoolExecutor(max_workers=1)` + 10s timeout) then `read_sentence` | 600s interval, network I/O bound |
| backup/save (`_orchestrated_backup`, `_save_backstop_thread`, hourly/daily S3 sync) | various | Full snapshot of `self.organism`/atlas/needs/etc, then disk/S3 I/O | Infrequent, chunky, but the *snapshot itself* already deliberately minimizes lock hold time (`save_full_state`: snapshot under lock is O(1)/entry, serialize+write happens outside the lock already) |
| `/sight_frame`, `/sound_frame` executor calls | per HTTP request, via `run_in_executor(None, _decode)` (default `ThreadPoolExecutor`), capped at `_FRAME_INFLIGHT_MAX=2` in-flight per modality | Decode + DSP touch **no shared state** (`view_picture`, `cochlear_transduce` build only local variables); only the final `with self.lock:` block writes `window_manager`/atlas | Bursty, request-driven, already isolated from `self.lock` for the expensive part |
| heartbeat, cascade-monitor, organ-live-update, organ-surface-poll, input-ring-consumer | various | Mostly polling/telemetry/IPC-adjacent, not evaluated further (out of scope — none showed up as CPU-bound candidates) | — |

## 2. CPU-bound vs I/O-bound vs bursty — where the GIL actually matters

The GIL only matters for *CPU-bound Python bytecode* competing across
threads; I/O-bound work already releases it. Checked the actual inner
loops, not assumed:

- `dsf_ai_service/visual_krimelack.py:214` `view_picture()` — a plain
  Python `for` loop over fixations × ticks-per-fixation (3×50=150
  iterations per sight frame today), calling `krim.tick()` per sample.
  Pure Python, GIL-held throughout.
- `dsf_ai_service/substrate/senses/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py:46`
  `bandpass_filter()` — an explicit `for i in range(n)` biquad filter loop,
  run once per of 6 cochlear bands per sound frame. Pure Python, GIL-held
  throughout. `cochlear_transduce()` then runs `Krimelack.feed_signal()`
  per band on top of that.
- `app.py:30` `decode_image_bytes()` — PIL/`pillow_heif` decode + resize.
  This part *is* a C extension and does release the GIL during the actual
  decode; the grid math after it is small (64×64 downsample).
- World-feed/lookup fetches — real HTTP calls via `requests`/similar,
  GIL released during the socket wait. Threading already handles this
  fine; no multiprocess case here.
- Diary writes — one small `dict` → `json.dumps` → file append. Trivially
  cheap, I/O-bound. No case here either.

So the frame-processing path is a **mix**: a GIL-releasing decode step
followed by GIL-bound pure-Python simulation/DSP loops, all currently run
on a `ThreadPoolExecutor` thread that has to take turns for GIL time with
the autonomy tick loop, the organism worker, and the tapestry worker —
all of which are themselves CPU-bound Python. That contention, not disk
or network I/O, is the plausible explanation for the tail below.

## 3. Live evidence (production, last 24h, read-only)

Pulled directly from CloudWatch (`/ecs/dsf-ai` log group, task-def
`dsf-ai-task:586`, confirmed `cpu: "4096"` = 4 vCPU Fargate task,
matching the "production 4-core hardware" scoping already established by
last week's C-port benchmarks):

| | n (24h) | median | p90 | max | % > 1s |
|---|---|---|---|---|---|
| `[sight-frame]` | 239 | 0.218s | 20.99s | 45.5s | 22.6% |
| `[sound-frame]` | 292 | 0.501s | 18.97s | 47.8s | 23.6% |

Combined call rate: ~22/hour, roughly one frame every 2-3 minutes on
average — this is bursty, session-driven camera/mic use, not a
continuous 30fps firehose. That matters for the design: the handoff this
proposal would cross a process boundary is naturally infrequent and
chunky already, before any redesign.

Container CPU utilization over the same window (`AWS/ECS` `CPUUtilization`,
5-min samples, 3h sample shown, consistent with the full 24h): average
25-31%, max sample 37% — **of the task's full 4-vCPU allocation**. There
is real, currently-idle CPU capacity sitting on the box while individual
frame calls occasionally take 20-48 seconds. That combination is the
concrete evidence behind this proposal, not a hunch.

## 4. Prior art this builds on — and must not repeat

**No-GIL Python 3.14t test (`GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v1/v2`,
`GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1/v3`): PARTIAL, not GO.** Same
underlying diagnosis as this report — GIL serialization is a real cost —
tested via a different mechanism (free-threaded interpreter instead of
process separation). Build/boot/correctness all came back clean; the
contention measurement was genuinely confounded (fresh low-load test
container vs. hours-old high-ambient-load production) and came back
mixed: 7.35x amplification (worse) by one reading, ~6x faster absolute
loaded latency (better) by another. Not reused as production readiness
evidence here — but it does establish that this class of GIL-relief
intervention is worth taking seriously, and it's a reason for *caution*,
not for skipping this proposal: that test's confound doesn't apply to the
design below, because the before/after comparison this proposal calls for
is on the **same running production process, same ambient load**, flag
flipped — not two different boots.

**Two ctypes/C-extension fine-grained ports both NO GO
(`GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1`,
`GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1`): ~0.07-0.075x scaling at
4 threads against a required ≥2-3.5x**, traced to the ctypes GIL-release/
reacquire handshake cost dominating at one-call-per-write granularity —
confirmed by an isolation test where a near-zero-work no-op call showed
the *same* collapse curve as the real write. This is the direct source of
the design constraint this proposal obeys: **cross a process boundary
once per frame, never once per sample/word/tick.** Frame decode already
naturally satisfies this (one call in, one small result out, ~22
times/hour); it is structurally nothing like the per-write ctypes calls
that failed.

## 5. Candidates, ranked

**Tier 1 — real candidate: camera/mic frame decode + DSP.**
Self-contained (confirmed by reading the actual functions: `view_picture`
and `cochlear_transduce`/`bandpass_filter` build only local variables;
only the final `with self.lock:` block in `process_sight_frame`/
`process_sound_frame` touches `self.window_manager`/atlas). Real,
currently-measured CPU cost with a concrete tail-latency problem (§3).
Naturally coarse, infrequent, bursty handoff — the correct shape per §4.
Already isolated behind a `ThreadPoolExecutor` call with an explicit
in-flight cap (`_FRAME_INFLIGHT_MAX=2`) and an honest-drop backpressure
policy — the scaffolding this proposal needs already exists; swapping the
executor for a process is a small, mechanical change at an already-clean
seam.

**Tier 2 — categorically excluded, not just deprioritized: organism
worker, tapestry worker, autonomy/reading loop, curriculum loader,
daydream loop.** All of these read or write `self.organism`, `self.atlas`,
`self.tapestry`, `self.needs`, or `self.coordinator` — the single shared
mutable graph that *is* her cognition. Splitting any of them into a
second process requires either synchronizing that whole graph across a
process boundary (turns the current in-memory lock into slower
cross-process IPC, working against the goal) or running a second,
independently-ticking copy of the thinking/reading/associating mechanism
— which is precisely what the standing "one brain, one voice" rule
prohibits (§6). Not evaluated further; this is a structural, not a
performance, disqualification.

**Tier 3 — wrong shape for a first step: backup / S3 snapshot.**
CPU-bound-enough in principle (large dict traversal + JSON/pickle
serialization is real Python bytecode work), and already infrequent —
but the payload is the entire mutable state graph, multiple MB, the
opposite of "small chunky handoff." `save_full_state` already applies the
cheaper fix in-process (snapshot under lock is O(1)/entry; the expensive
serialize+write already happens *outside* the lock, on a plain thread).
This subsystem also has real, recent incident history independent of
this analysis — EFS rename race (fixed 2026-07-02), S3 write-collision
risk (found live during the no-GIL test, 2026-07-07), identity
dual-genesis race (recurred twice, 2026-07-06). Adding a new IPC failure
mode here first, before the pattern has been proven safe anywhere else,
is the wrong order of operations.

**Tier 4 — no case: diary writer, world-feed/lookup loops.** Diary writes
are I/O-bound and trivially cheap (§2); the existing single-worker-queue
pattern already fully solves "don't block the caller," and there is
essentially no GIL time to reclaim. World-feed/lookup loops are
network-I/O-bound with their own timeouts; Python threads already handle
I/O concurrency correctly. Multiprocessing would add real complexity here
for no measurable win.

**Not evaluated in depth (flagged for later, not now):** Whisper
transcription (`VOICE_WHISPER` path) is currently OFF by default in
production, so there is no live evidence to ground a proposal on, and
`ctranslate2` is itself a C++ engine that likely already releases the GIL
during inference — meaning its multiprocess payoff is probably smaller
than frame decode's, not larger. Worth a look only after this is
switched on and measured.

## 6. "One brain, one voice" — why frame decode does not cross the line

The proposed child process would run exactly two pure functions:
`view_picture()` (saccade/fixation simulation over a pixel grid) and
`cochlear_transduce()`/`bandpass_filter()` (audio band-splitting DSP).
Neither touches `self.organism`, `self.atlas`, `self.tapestry`,
`self.needs`, `self.coordinator`, recall, or emission — confirmed by
reading them, not assumed. They do not decide anything, remember
anything, or produce words; they turn raw bytes into a small feature
summary (fragments / per-band winding counts), the same category of work
a camera ISP chip or an audio codec does before a signal ever reaches a
brain. The *only* place any of this touches her one shared mind is the
existing, unchanged `with self.lock:` block back in the main process,
which stays exactly where it is today. There is one cognition process,
one voice, one lock guarding her state; this proposal adds a stateless
preprocessing helper upstream of all of that, not a second thinker.

## 7. Proposed minimal first step

Not built here — design only, for a future bounded trial dispatch, same
shape as `GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v1`: test-slot only,
flag-gated, measured, halt-on-any-regression.

- **Mechanism:** one dedicated long-lived worker **process** (a single
  `multiprocessing.Process` or `ProcessPoolExecutor(max_workers=1)`, not
  a pool sized for throughput — matches today's `_FRAME_INFLIGHT_MAX=2`
  ceiling, no tuning needed for a first trial), holding no reference to
  `_guala`/organism/atlas/lock at all — it only ever receives raw bytes
  (image bytes or WAV bytes) and returns a small, explicitly-trimmed,
  picklable summary (chi-relevant fragment stats / per-band winding+
  event-count — *not* the full intermediate `filtered`/`events` arrays
  cochlear_transduce currently returns, which aren't needed downstream
  and would only bloat the handoff).
- **Scope:** sight frames only, first. Sound as a fast-follow once sight
  is proven — no reason to change both call sites in one step.
- **Flag:** `FRAME_DECODE_PROCESS=0` (default, current `ThreadPoolExecutor`
  behavior, fully unchanged) vs `=1` (routes through the new process). Old
  path stays in the code, untouched, as the instant rollback — same
  discipline as `RECALL_BACKEND=legacy/stdp/shadow` and
  `EVENT_DRIVEN_SUBSTRATE`.
- **Deploy shape:** test ECS service/task-def/target-group, gated by
  header condition, exactly as the no-GIL test did — never pointed at
  production traffic until measured.
- **Correctness gate:** for a fixed set of real captured frames, compare
  the `sight_frame_bound` event fields (`motif_id`, `chi`, `is_new`)
  produced by the old path vs. the new path — must be identical. This
  proves the split changes *where* the compute runs, not *what* she
  perceives.
- **Success metric:** p90/max wall time for `[sight-frame]` collapsing
  toward true compute cost (expect low hundreds of ms, based on the
  algorithm's shape — 150 simple loop iterations plus a 64×64 resize),
  without regressing the already-good median (0.218s). Also worth an
  honest look at whether *other* threads' latency (autonomy tick,
  converse) improves incidentally now that they no longer contend with
  frame-processing's Python loops for GIL time — a plausible secondary
  effect, not to be assumed without measuring.
- **Explicit non-goal:** this does not touch, and should not be reported
  as touching, today's reply-latency symptom. Different subsystem,
  different lock, already outside `self.lock` before this proposal.

## 8. Cost, risk, honest expected payoff

**New failure modes this would introduce, named plainly:** a child
process can crash, hang, or become a zombie — needs supervision/respawn,
and a hard timeout on the parent side so a stuck child degrades to a
dropped frame (the same honest-degradation behavior `_frame_backpressure_
acquire` already provides today under queue pressure) rather than a hung
request. Pickling cost for the trimmed payload should be small (a
downsampled 64×64 grid, or a few hundred samples of downsampled audio)
but is unverified until actually measured — first build should confirm
this empirically, not assume it. One more live OS process to run inside
the ECS task; Fargate tasks are real multi-process Linux containers (not
Lambda), so this is not a platform blocker, but it is a new operational
surface (process count, restart behavior) that doesn't exist today.

**Ceiling, stated honestly:** production is using ~25-31% of 4 vCPUs on
average — there is real headroom, but it is bounded, not infinite. This
fixes one confirmed, currently-measured pain point (sensory frame tail
latency, real for anyone actually using her camera/mic), not a general
throughput multiplier for the whole substrate. If/when a no-GIL interpreter
migration eventually goes GO, this specific split becomes redundant (a
free-threaded interpreter would fix the same tail latency without any
process-boundary code) — that would be a fine trade to make later, not a
reason to avoid building this now on the current interpreter.

**Skepticism applied to this proposal itself, per this project's own
track record of designs that looked good in isolation and failed at real
integration** (`GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v1/v2`, halted
on a lock-free write race and then a dict-iteration crash; `GL-RPT-
SENSORY-ORGANISM-QUEUE-BUILD-C1-20260707-v1`, shipped but found to cause
real starvation; `GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1/v2/v3`, three
successive halts — pickle bug, missing rewiring, then a live cascading
feedback loop on the third, fully-correct-looking attempt): the specific
way this proposal could still fail at integration is the child-process
supervision/respawn logic, and the trimmed-payload pickling — both are
named above as things to verify empirically in the trial, not assumed
safe because the design looks clean on paper. Everything else about this
specific candidate (self-contained pure functions, no shared state, small
infrequent payload) is unusually well-supported by direct code reading,
not just architectural hope — which is the actual reason it's ranked
above every other candidate rather than deferred.

## 9. Recommendation

**Worth a bounded, flag-gated trial on frame decode specifically — GO for
a scoped test dispatch, not for anything wider.** The evidence (idle
CPU + confirmed GIL-shaped tail latency on already-isolated, pure-Python,
self-contained work) is concrete and current, not inferred. Every other
candidate in this codebase is either structurally disqualified (cognition
itself, §6), the wrong shape for a first step (backup, §3 Tier 3), or
already fine as-is (diary, world-feed, §3 Tier 4). This is not a general
endorsement of multiprocessing across the substrate — it is one narrow,
well-evidenced exception, scoped exactly as narrowly as the evidence
supports.

---

### Changelog
- v1 (2026-07-10, c1): Initial design-and-research report. Read the real
  threading model in `gualaloom_v5_engine.py`/`app.py`/`substrate_runner.py`
  directly. Pulled live 24h CloudWatch data for `/sight_frame`/`/sound_frame`
  and ECS CPU utilization to ground the frame-decode candidate in current
  production evidence rather than assumption. Ranked all real background
  threads; ruled out organism/tapestry/autonomy/curriculum/daydream
  categorically on "one brain, one voice" grounds, not performance grounds.
  Proposed a single-process, flag-gated, sight-first trial with an explicit
  correctness gate and named non-goal (does not address today's reply-
  latency symptom). No production code written or modified.
