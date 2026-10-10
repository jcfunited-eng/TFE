# GL-SPC-UTTERANCE-TRANSACTION-ARCHITECTURE-C1-20260715-v1

Status: DRAFT — awaiting owner approval before any production change.
Author: c1. Date: 2026-07-15. Branch: guala-live.
Nature: architecture definition only. No code in this document ships until Joe approves it.

## 0. Purpose

Define ONE utterance-level conversation transaction as the sole conversation architecture
for the substrate, replacing both conversation paths that exist today. This was prompted by
an external review ("Sol") whose diagnosis has been independently verified in-session against
the live code. The substrate is a set of programs; this document describes the process, the
tick loop, and the store — not a person.

The single sentence: **one complete utterance in, one deterministic settlement, one atomic
persistence commit at closure, one reply out — or honest silence.** No replay, no per-character
transaction, no timer standing in for meaning.

## 1. The two current paths and why both die

**Legacy path — exact-suffix replay (root of empty/one-word replies).**
`dsf_ai_service/substrate/language_fact_composer.py` (`continue_from`, `_matches_for`,
`_longest_suffix_occurrences`) finds stored binding-windows whose recognized class sequence
exactly matches a suffix of the query, then walks forward only while the structural successor
stays unique. The walk stops — silent — at the first non-unique successor
(`ContinuationStopReason`: `NO_SUCCESSOR`, `SUCCESSOR_UNKNOWN`, `MIXED_TERMINAL_AND_SUCCESSOR`,
`AMBIGUOUS_SUCCESSOR_CLASSES`). It replays stored order; it does not compose over the query.
An input whose suffix has no unique stored continuation yields nothing or a fragment. This is
the mechanism behind the empty/one-word replies, confirmed this session.

**Experimental path — per-scalar GLEW scheduling.**
`dsf_ai_service/glew_runtime/multi_scalar_turn_scheduler.py` processes exactly one Unicode
scalar per call to `ProductionCleanConversationEngine.run_clean_conversation`, because
`real_experience_learning_pipeline._build_typed_language_lane` hard-fails any turn whose text
is not length 1. Commit in `commit.py` is an all-or-nothing verdict **per causal window**, so a
per-scalar schedule means one full persistence checkpoint per committing character.
`ImmutableGenerationStore.commit` was measured at 8 fsyncs, 5 file creates, and 2 full
re-read-and-rehash verify passes (~9 MiB) per commit — ~155 ms local, estimated 0.5–2 s on EFS.
Per character, that is unaffordable.

**What dies at cutover:**
1. The exact-suffix replay path (`language_fact_composer` continuation as the reply source).
2. Per-scalar GLEW scheduling **as the transaction boundary** (the scheduler's per-character
   loop stops being the unit of commit).
3. Per-scalar persistence commits (one commit per character).
4. The STT-unavailable stub route (silently returning `""` on recognizer failure).
5. The temporary frame-shed bridge (`app.py` GL-CMD-CONVERSE-FRAME-PRIORITY,
   `_converse_turn_in_flight`, `_CONVERSE_PRIORITY_WINDOW_S = 2.5`). It is explicitly interim;
   removing it is an acceptance criterion, not a nicety.

**What carries forward (proven on 2026-07-15, re-scoped to utterance granularity):**
The GLEW correctness chain — recognition → commit → learn → recall → speak — was proven
end-to-end live: a repeated single-scalar utterance produced a real reply in production. The
mechanisms are worth keeping; the per-scalar boundary is not. Carried forward:
- The receipt-verified recognition/commit/learn/recall machinery
  (`clean_conversation_engine.py`, `RECOGNITION_ARBITER_CERTIFIED_RESIDUAL`, the
  `closed_experience` receipts), re-scoped so the causal window / transaction is the whole
  ordered utterance, not one scalar.
- The message-end close signal (`SealedClosedExperience` / `closed_experience`) as the real
  closure event.
- The six-lane runtime (language + five senses) and the mode-bank **growth arbiter** — real
  growth is a load-bearing side effect of recognition, folded back into the bank per call.
- Content-only identity keys (`scene_id` / `event_id` / `identity` derived from content),
  stable across restart.
- The honest-silence rule.

## 2. The utterance transaction

**Inputs.**
- One complete ordered utterance: either the full typed message text, or an STT-transcribed
  utterance **with its evidence receipts** (the auditory fragment / transcription receipt
  chain), never a bare string.
- Concurrent sight and sound evidence for the same interval, computed independently and joined
  deterministically at closure (Section 3).

**The field.** The transaction builds ONE coupled field over the WHOLE ordered utterance, with
word-to-word relationships as first-class structure — not per-character chaining. This aligns
with ArcLoom Master Specification v5.0, Ch.3 "Coherence-Field Evolution": the ψ-lattice evolves
under a single combined operator `H_total(k) = H_base + H_mem + H_law + H_goal + H_safety` with
injection `J(k)` (Axiom, Ch.3 §"Coherence-Field Evolution"). The whole utterance injects
structural evidence into one field; settlement is that field reaching a structural lock, which
fires **deterministically from natural constants** (`n_eff < n_start/e`, Ch.3 §"Capture
Threshold and Structural Lock") — not from a wall-clock timeout. This is exactly the
single-coupled-field discipline the six-independent-section vote-gate diverges from, and the
reason this architecture is spec-convergent rather than another patch.

**Settlement.** Deterministic. Given the same ordered utterance and the same store state, the
same reply (or the same silence) results. No salted hashing, no timer, no heuristic threshold
dressed as meaning.

**Persistence.** Exactly ONE `ImmutableGenerationStore.commit` at utterance closure — one
commit per utterance, replacing N commits (one per character). For a 20-character utterance
that is a ~20× reduction in fsync/verify work and the dominant EFS-latency saving.

**Honest silence — without going silent forever.** If the field reaches no structural lock, or
the ordered structure is insufficient / non-unique, the transaction produces **no spoken
output**. The failure stays loud in diagnostics (Section 6d). But silence is per-utterance,
never permanent: novelty still drives real mode-bank growth via the proven GLEW growth arbiter,
so the same structure can settle on a later occurrence. Silence is a verdict on this utterance,
not a dead end for the substrate.

## 3. Process topology

Owner ruling (a) binds this: genuine parallelism means separate OS processes on separate cores.
Python threads in one process do not qualify. This section places each workload accordingly.

**Main substrate process (one interpreter, the existing ~6.5 GB RSS process).**
Owns: the utterance transaction settlement, all engine/atlas/organism state mutation, the
six-lane runtime, recall, and the single store commit at closure. All shared-state writes and
all affect stamping (`_affect_kwargs`, a live state read) stay here. Cognition never leaves this
process — owner ruling (e), substrate-true.

**Sensory transduction worker(s) — spawn, not fork.**
The pure, lock-free segments of sight and sound decode run in one long-lived worker process
holding **zero** references to the engine/atlas/lock. Justification for spawn over fork, from
the prior-art journal:
- The parent is heavily multithreaded (autonomy loop, organism/tapestry/diary workers,
  daydream, spike bus, backup threads). Fork inherits any lock held at fork time — child
  deadlock risk.
- CPython refcounting touches object headers on the child's first traversal, converting
  copy-on-write pages of a 6.5 GB heap into real copies, on a 16 GB box with documented
  OOM(137) history. Fork is doubly contraindicated. Spawn's clean interpreter costs a few
  seconds once at boot and ~200–400 MB steady-state, within headroom.
- Worker code imports only pure modules (`krimelack`, the auditory-cortex module,
  `visual_krimelack`, PIL, numpy, subprocess-for-ffmpeg) — never `app` or the engine — so spawn
  boot stays cheap and the workers are engine-state-free by construction.

**What crosses each boundary (measured, tiny):**
- Sound, inbound: raw WebM bytes (~30–70 KB) + a monotonic `frame_id` + arrival wall time
  stamped at HTTP arrival. ffmpeg becomes a child of the *worker*, so its spawn/wait stops
  competing in the main process at all.
- Sound, outbound: ~260-byte per-band summary (`{band: {winding, n_events}}`) + an 8 KB
  1000-float64 signal cache. The full cochlear dict (filtered arrays, ~4k event dicts) never
  crosses.
- Sight, inbound: raw JPEG (~5 KB) + `frame_id` + arrival wall time + a `born_tick` int
  snapshot.
- Sight, outbound: ~1.7 KB of fragment receipts + an 0.8 KB signal cache.
Pure compute is ~6–7 ms (sound) / ~1 ms (sight) per frame; the measured 0.2–0.35 s today is
ffmpeg wall time plus GIL-queueing behind ~8 runnable threads, which moving out-of-process
removes from the main scheduler entirely.

**Where STT runs.** faster-whisper / CTranslate2 is CPU-bound and belongs in a worker process
(its own, or the sensory worker), off the main GIL. The recognizer-lifecycle repair that is
currently stranded — commit a8277fa, "fix(stt): own recognizer lifecycle and fail visibly" — is
NOT in the live lineage and must be brought in when this is built. It: (i) owns exactly one
`SpeechRecognizer` per process, serializing construction and inference (one CTranslate2 model =
one physical recognition resource); (ii) raises `SpeechRecognitionUnavailable` /
`SpeechTranscriptionError` instead of collapsing failure to `""` (directly serves ruling (d),
loud failure); (iii) warms the recognizer at startup via `require_speech_recognizer()`; (iv)
returns a structured status (`disabled` / `recognized` / `no_speech` / `error`) rather than a
silent drop. Port it into the STT worker rather than re-deriving it. **STT is a sense
transducer at the boundary, exactly like the camera codec (ffmpeg) — not cognition.** It turns
pressure waves into an ordered token stream with receipts; it does not settle meaning. Under
ruling (e) that placement is what keeps external ML out of the cognition path.

**Deterministic join.** Each frame carries `frame_id` + arrival wall time (stamped at HTTP
arrival, not at ingestion). Results are applied in completion order — harmless today, since up
to two frames per kind already race — with a **newer-wins guard** on the two last-writer-wins
sense caches (`_last_sound_signal` / `_last_sight_signal` + wall stamps). The utterance
transaction joins the ordered language stream with whatever sensory evidence is present for the
interval; causal language succession stays strictly ordered.

**Lifecycle under sealed deploy.** Workers follow the existing child-process precedent:
`_curriculum_process` is a `subprocess.Popen` that `quiesce_background_loops` already terminates
before joining threads. The sensory worker pool is created in the post-boot embedded path
(after boot succeeds), never at import time; torn down at the same point
`_curriculum_process.terminate()` already lives, before `quiesce_background_workers` and
`_seal_runtime_generation`, so the seal's thread/mutation proofs stay exact. The result-ingestion
thread registers via `substrate_runner._start_background_thread` (so quiesce joins it) and its
ingest calls run under the engine's `_engine_mutation_scope` (so the mutation ledger stays
exact). No seal-contract change.

## 4. Cutover plan (gated on owner approval)

1. Build the utterance transaction behind the existing single flag
   `GLEW_CONVERSATION_ENGINE_ENABLED` (already wired: `_boot_glew_conversation_engine`,
   `app.py:352–430`). One flag, one switch.
2. Prove it with the established live-test discipline: real HTTP requests, repeated utterances
   AND novel utterances, across a restart, under real concurrent frame load — not unit tests
   alone.
3. Flag flip = both current paths off in the same moment. The utterance transaction REPLACES
   them; it never runs alongside (owner ruling (b): no shadow mode, one mouth). There is no
   dual-write, no diagnostic parallel backend.

## 5. Acceptance criteria (testable)

a. **Multiword in → multiword out, live.** A multiword utterance submitted over real HTTP to
   the production task produces a multiword reply (not empty, not one word, not a replayed
   fragment). Repeated on a novel utterance.
b. **Latency budget.** p95 end-to-end conversation latency < 5 s under real concurrent frame
   load. Justification: the heavy competitors in a quiet turn today are organism work items
   (238–370 ms each), whole-history suffix searches, and multi-second window saves — not frame
   decode (~7 ms). Moving sensory transduction out-of-process removes the frame job from the
   main scheduler, and collapsing N per-character commits into one per-utterance commit removes
   the dominant EFS cost. The residual budget is settlement + one commit.
c. **Frame-shed bridge removed.** GL-CMD-CONVERSE-FRAME-PRIORITY / `_converse_turn_in_flight` /
   `_CONVERSE_PRIORITY_WINDOW_S` are deleted, and conversation latency (criterion b) holds
   without them. The bridge existing at cutover is a failure of this design.
d. **No per-scalar commits remain.** Exactly one `ImmutableGenerationStore.commit` per
   utterance, verified in logs/receipts across a multi-word turn.
e. **Loud failure, silent mouth.** Recognizer unavailable, transcription error, or no
   structural lock each produce a visible diagnostic (status field / counter / log) and produce
   NO spoken output. No failure text is ever emitted as a reply (ruling (d)).
f. **Restart does not regress the utterance store.** After a restart the committed utterance
   record is present and recall works on it. NOTE: the current boot defect — every boot falls
   back to the 2026-07-13 S3 backup — is owned by another session and concerns the legacy
   WAL/pickle store, NOT the GLEW `ImmutableGenerationStore`. This design must prove the
   utterance store's restart durability independently; it must not depend on that legacy boot
   path staying broken, nor assume it will be fixed.

## 6. Open questions for the owner

1. **Whisper-at-the-boundary under substrate-true.** This design treats STT as a sense
   transducer at the input boundary (like ffmpeg for the camera), explicitly outside the
   cognition path. Is faster-whisper acceptable in that role? If not, voice input has no
   substrate-true transducer today and the transaction must accept typed text only until one
   exists.
2. **Voice utterance boundary = STT real end-of-speech.** For voice, the utterance closes on
   the STT evidence chain's real detected end-of-speech, not a timer. The UI currently ships
   fixed 5 s MediaRecorder chunks — a transport chunk, not an utterance boundary. Confirm the
   close signal comes from the STT segmentation (end-of-speech across however many transport
   chunks), and that a still-open utterance spanning chunks is the intended behavior.
3. **Legacy word-window corpus at cutover.** The `language_fact_composer` / binding-window
   corpus is the current legacy memory. At cutover: migrate it into the utterance store,
   freeze it readable (recall-only, no new writes), or retire it? This decides whether prior
   learned language survives the switch.
4. **Whole-utterance single window vs. utterance-granular transaction (engineering call, flagged
   honestly).** ArcLoom's ideal is one coupled field over the whole utterance. GLEW today sizes
   its causal grid at five timestamps *for one scalar* and hard-fails multi-scalar language
   lanes; the scheduler's own authors call generalizing the grid "a much larger, riskier change
   to already-committed sense-evolution sizing." This design fixes the **transaction and commit
   boundary** at utterance granularity now (definitely achievable: schedule the utterance's
   scalars into one transaction with one commit at close) and treats the whole-utterance coupled
   field as the settlement objective, with internal per-scalar windowing an implementation
   detail to prove. A literal single-window field over the whole utterance may require the
   deferred grid resize. Approve the staged approach, or require the full single-window field up
   front (larger, riskier build)?
