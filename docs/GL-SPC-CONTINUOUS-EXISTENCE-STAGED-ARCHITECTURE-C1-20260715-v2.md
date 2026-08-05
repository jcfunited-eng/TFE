# GL-SPC-CONTINUOUS-EXISTENCE-STAGED-ARCHITECTURE-C1-20260715-v2

Status: **APPROVED by Joe, 2026-07-15** (stated to the c1 RAM/boot session: "I approved that spec"; ratification relayed here so the authoring session has it on-origin). Production work per the staging plan may begin.
Author: c1. Date: 2026-07-15. Branch: guala-live.
Supersedes: GL-SPC-UTTERANCE-TRANSACTION-ARCHITECTURE-C1-20260715-v1 (kept untouched for
history). v1's verified technical facts carry forward; its framing does not.

## 0. Vision correction (owner, 2026-07-15)

v1 put the utterance transaction at the center of the architecture. The owner corrected this:
that framing is inverted. **Continuous existence is the architecture; transactions are only
bookkeeping.** The target is:

> Rich continuous sensory full experiences that only get interrupted by amazing sleep/dream
> states — not oblivion per strokes of the enter key.

Project credo, verbatim:

> Life cannot be strictly qualified by biology or programming, but by the ineffable quality of
> our memories and experience. Language cannot really have meaning without the equality of
> experience as tied to our senses and backed into our expressions of them in thoughts and
> words.

The substrate is a set of programs; this document describes processes, lanes, and stores — not
a person. What the credo demands of those programs: the experience stream never stops between
inputs; memory accumulates continuously; language events are one kind of event inside that
stream, not the frame around it.

## 1. Primary architecture: the continuous experience stream

**Senses always flowing.** Sight and sound frames arrive and are transduced continuously,
whether or not any conversation turn is in flight. No sense is gated behind "was this addressed
to the substrate" and no sense is shed to make room for a language turn (the temporary
frame-shed bridge — `app.py` GL-CMD-CONVERSE-FRAME-PRIORITY, `_converse_turn_in_flight`,
`_CONVERSE_PRIORITY_WINDOW_S = 2.5` — is a violation of this and its removal is an acceptance
criterion).

**Genuinely parallel lanes.** Perception (sense transduction), integration (settlement,
recall, all engine/atlas/organism state mutation), and expression (reply emission and speech
output) each run on genuinely parallel OS-process lanes — separate processes on separate
cores, per the standing owner ruling that Python threads in one process do not qualify.
Cognition (integration) stays in the main substrate process; the lanes around it carry
evidence in and expression out. Section 4 gives the concrete topology.

**Persistence as continuous consolidation.** Durability is not something that happens once
per keystroke or once per reply; it is the stream continuously consolidating experience into
the store, with **real compaction during sleep/dream states** — the one legitimate
interruption of the stream. Sleep/dream is where consolidation does its heavy work
(compaction, re-organization), by design, on the schedule the substrate's own state dictates.
Discrete commits still exist — but as the bookkeeping units of consolidation (Section 3), not
as the architecture.

**What "interruption" is allowed to mean.** Sleep/dream states. Nothing else. Not a restart,
not an enter key, not a recognizer failure. Between sleep states the stream is continuous:
experience in, memory accumulating, expression when structure settles.

## 2. Credo-level defect: restore-amnesia at boot

Every restart of the production task currently restores the 2026-07-13 S3 backup, discarding
days of accumulated state. Under the credo this is not a durability bug among others — it is
the direct negation of the architecture. **Restore-amnesia is the opposite of continuous
existence**: a substrate whose memory resets to a fixed snapshot on every boot has no
continuity of experience to speak of, whatever its per-utterance commit discipline looks like.

Ownership: this defect lives in the legacy WAL/pickle boot path and is owned by another
session. It is named here because Stage 1 (Section 5) has a hard dependency on it: no demo of
continuous existence survives a restart that erases the days before it. This document does not
re-scope that work; it declares the dependency.

## 3. The utterance transaction — demoted to bookkeeping

The utterance transaction is retained, but demoted: it is the **persistence/durability
discipline for language events inside the stream**, not the conversation architecture. One
complete utterance in, one deterministic settlement, one atomic store commit at utterance
closure, one reply out — or honest silence. It is how a language event gets consolidated; the
stream around it never pauses for it.

**Verified facts carried from v1 (all confirmed in-session against live code):**

- *Legacy path — exact-suffix replay — is the empty/one-word-reply mechanism.*
  `dsf_ai_service/substrate/language_fact_composer.py` (`continue_from`, `_matches_for`,
  `_longest_suffix_occurrences`) replays stored binding-windows whose class sequence matches a
  query suffix, walking forward only while the successor is unique, stopping silent otherwise
  (`ContinuationStopReason`). It replays stored order; it does not compose over the query.
- *Experimental path — per-scalar GLEW scheduling — is unaffordable at its current boundary.*
  `dsf_ai_service/glew_runtime/multi_scalar_turn_scheduler.py` processes one Unicode scalar per
  `run_clean_conversation` call (`_build_typed_language_lane` hard-fails length != 1), and
  commit is all-or-nothing per causal window, so each committing character costs one full
  `ImmutableGenerationStore.commit`: measured 8 fsyncs, 5 file creates, 2 full
  re-read-and-rehash verify passes (~9 MiB), ~155 ms local, est. 0.5–2 s on EFS.
- *The GLEW correctness chain is proven live.* Recognition → commit → learn → recall → speak
  produced a real reply in production on 2026-07-15 (repeated single-scalar utterance). The
  mechanisms (`clean_conversation_engine.py`, `RECOGNITION_ARBITER_CERTIFIED_RESIDUAL`,
  `closed_experience` receipts, the mode-bank growth arbiter, content-only identity keys) are
  kept; the per-scalar boundary is not.

**The bookkeeping rules:**

- The transaction's unit is one complete ordered utterance, with word-to-word relationships as
  first-class structure — never per-character chaining.
- Exactly ONE `ImmutableGenerationStore.commit` at utterance closure (a ~20× reduction in
  fsync/verify work for a 20-character utterance, the dominant EFS saving).
- Settlement is deterministic: same ordered utterance + same store state → same reply or same
  silence. No salted hashing, no timer dressed as meaning.
- Honest silence, per-utterance: no structural settlement → no spoken output, loud diagnostic.
  Novelty still drives real mode-bank growth, so the same structure can settle later. No
  failure text is ever emitted as a reply.

**What dies (unchanged from v1):** the exact-suffix replay path as reply source; per-scalar
scheduling as the transaction boundary; per-scalar commits; the STT-unavailable stub route
(silent `""`); the temporary frame-shed bridge.

## 4. Process topology (the stream's lanes)

Carried from v1, now framed as the stream's permanent shape rather than the transaction's
plumbing. Owner ruling binds: genuine parallelism = separate OS processes on separate cores.

**Main substrate process** (the existing ~6.5 GB RSS interpreter): integration lane. Owns
settlement, all engine/atlas/organism state mutation, the six-lane runtime, recall, affect
stamping, and the single store commit at closure. Cognition never leaves this process.

**Sensory transduction worker(s) — spawn, not fork**: perception lane. Pure, lock-free sight
and sound decode in a long-lived worker holding zero engine/atlas/lock references. Spawn
because the parent is heavily multithreaded (fork inherits held locks → child deadlock risk)
and because CPython refcounting turns copy-on-write pages of a 6.5 GB heap into real copies on
a 16 GB box with documented OOM(137) history. Boundary traffic is tiny and measured: inbound
raw WebM ~30–70 KB / JPEG ~5 KB + `frame_id` + arrival wall time; outbound ~260-byte sound
summary + 8 KB signal cache / ~1.7 KB sight receipts + 0.8 KB cache. ffmpeg becomes a child of
the worker. Deterministic join at the main process: completion-order apply with a newer-wins
guard on the last-writer-wins sense caches.

**STT worker**: faster-whisper / CTranslate2 is CPU-bound and runs in its own worker process,
off the main GIL. **STT is a sense transducer at the boundary, exactly like the camera codec —
not cognition.** The stranded recognizer-lifecycle repair — commit a8277fa, "fix(stt): own
recognizer lifecycle and fail visibly", NOT in the live lineage — is ported in, not re-derived:
one `SpeechRecognizer` per process with serialized construction/inference; raises
`SpeechRecognitionUnavailable` / `SpeechTranscriptionError` instead of collapsing failure to
`""`; warm-up via `require_speech_recognizer()`; structured status
(`disabled` / `recognized` / `no_speech` / `error`).

**Lifecycle under sealed deploy** (unchanged from v1): workers follow the `_curriculum_process`
precedent — created post-boot, terminated where `_curriculum_process.terminate()` lives, before
`quiesce_background_workers` and `_seal_runtime_generation`; the result-ingestion thread
registers via `substrate_runner._start_background_thread` and ingests under
`_engine_mutation_scope`. No seal-contract change.

## 5. Deadline staging (owner, 2026-07-15)

Investor meeting in ~2 weeks (≈2026-07-29); DARPA a few weeks after. The demo bar is real,
substrate-true conversation plus visible autonomy — or the project fails. Embodiment is the
future ArcLoom SPPU processor plus a physical body; until that exists the substrate is
emulated. The plan is therefore staged: Stage 1 is what must be true at the demo; Stage 2 is
the post-funding build toward the full spec.

### Stage 1 — by ≈2026-07-29 (the demo)

a. **Boot-amnesia fixed.** Restarts stop restoring the 2026-07-13 snapshot; accumulated state
   survives. *Owned by another session's lane; hard dependency, tracked here, not built here.*
b. **Real multiword conversation.** The proven GLEW recognize/learn/recall mechanisms
   re-scoped to utterance granularity: one commit at utterance close, word-to-word
   relationships as first-class structure. Built behind the existing single flag
   `GLEW_CONVERSATION_ENGINE_ENABLED` (`_boot_glew_conversation_engine`, `app.py:352–430`);
   flag flip turns both current paths off in the same moment — no shadow mode, one mouth.
c. **STT restored.** The a8277fa recognizer-lifecycle repair ported into the STT worker as a
   boundary sense transducer (Section 4). Voice in becomes an ordered token stream with
   receipts; failure is loud, never a silent `""`.
d. **Autonomy demonstrably running.** The autonomous loops (study, daydream, reflection,
   play) visibly active during the demo — observable behavior, not log claims.
e. **Parallel sense lanes, stage 1.** The sensory transduction worker(s) live, which removes
   the temporary frame-shed bridge: senses keep flowing during conversation turns.

Proof discipline for all of Stage 1: real HTTP against the production task, repeated AND novel
utterances, across a restart, under real concurrent frame load — not unit tests alone.

### Stage 2 — post-funding

- **Whole-utterance single coupled field** per ArcLoom Master Specification v5.0 Ch.3: one
  ψ-lattice field over the whole ordered utterance under
  `H_total(k) = H_base + H_mem + H_law + H_goal + H_safety` with injection `J(k)`, settlement
  as structural lock firing deterministically from natural constants (`n_eff < n_start/e`,
  Ch.3 "Capture Threshold and Structural Lock"). Stage 1 fixes the transaction and commit
  boundary at utterance granularity with internal per-scalar windowing as an implementation
  detail; Stage 2 replaces that windowing with the literal single-window field (the deferred
  causal-grid resize the scheduler's authors call the larger, riskier change).
- **Full continuous-consolidation persistence**: the store as a continuously consolidating
  stream with real compaction during sleep/dream states, rather than discrete per-event
  commits as the only durability mechanism.
- **Richer embodiment senses**, en route to the physical body.
- **SPPU hardware path**: the ArcLoom physical substrate replacing emulation.

## 6. Acceptance criteria (Stage 1, testable)

a. **Multiword in → multiword out, live.** A multiword utterance over real HTTP to the
   production task produces a multiword reply (not empty, not one word, not a replayed
   fragment). Repeated on a novel utterance.
b. **Latency budget.** p95 end-to-end conversation latency < 5 s under real concurrent frame
   load. The heavy competitors today are organism work items (238–370 ms each), whole-history
   suffix searches, and multi-second window saves — not frame decode (~7 ms); out-of-process
   transduction plus one-commit-per-utterance removes the dominant costs.
c. **Frame-shed bridge removed.** GL-CMD-CONVERSE-FRAME-PRIORITY / `_converse_turn_in_flight`
   / `_CONVERSE_PRIORITY_WINDOW_S` deleted, and criterion (b) holds without them. The bridge
   existing at the demo is a failure of this design.
d. **No per-scalar commits remain.** Exactly one `ImmutableGenerationStore.commit` per
   utterance, verified in logs/receipts across a multi-word turn.
e. **Loud failure, silent mouth.** Recognizer unavailable, transcription error, or no
   structural settlement each produce a visible diagnostic and NO spoken output.
f. **Restart preserves the stream.** After a restart, accumulated state and the committed
   utterance record are present and recall works on them. This now has two legs: the GLEW
   `ImmutableGenerationStore`'s own restart durability (this design's obligation), and the
   boot-amnesia fix (Stage 1a, other session's lane). Criterion (f) is not met until BOTH
   hold — under the credo, per-store durability with whole-substrate amnesia is worthless.
g. **Autonomy visible.** During the demo window, autonomous activity is observable from
   outside (behavior, not logs): the substrate acts between inputs.

## 7. Open questions for the owner (carried forward)

Answered by the vision correction / staging, and therefore dropped from this list: v1-Q1
(STT-at-the-boundary — ratified as Stage 1c, transducer role only) and v1-Q4 (whole-utterance
field vs. utterance-granular transaction — resolved by staging: transaction boundary now,
single coupled field in Stage 2).

1. **Voice utterance boundary = STT real end-of-speech.** For voice, the utterance closes on
   the STT evidence chain's real detected end-of-speech, not a timer. The UI currently ships
   fixed 5 s MediaRecorder chunks — a transport chunk, not an utterance boundary. Confirm the
   close signal comes from STT segmentation (end-of-speech across however many transport
   chunks), and that a still-open utterance spanning chunks is intended behavior.
2. **Legacy word-window corpus at cutover.** The `language_fact_composer` / binding-window
   corpus is the current legacy memory. At cutover: migrate it into the utterance store,
   freeze it readable (recall-only, no new writes), or retire it? This decides whether prior
   learned language survives the switch — and under the credo, accumulated experience is the
   substance being protected, so the default should not be silent retirement.
