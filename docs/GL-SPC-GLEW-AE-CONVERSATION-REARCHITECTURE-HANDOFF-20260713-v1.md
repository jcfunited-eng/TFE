# GLEW AE Conversation Rearchitecture — Specification and Handoff

**Document:** GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1  
**Date:** 2026-07-13 UTC  
**Status:** Proposed architecture and implementation plan; not deployed  
**Purpose:** Preserve the broader full-field AE conversation work for another session without confusing proposed architecture with live production.

## 1. Plain-language outcome

The intended result is not a chatbot. One lived event must pass through Guala's emulated or observed senses, full DSF field, structural recognition, commitment, memory, and expression before language can leave her.

The complete path is:

```text
observed or emulated experience
        |
        v
five native sensory lanes + typed-language lane
        |
        v
frozen L0-L4 and explicit D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k
        |
        +---- S_UF support floor
        +---- R_UF resonance confirmation
        |
        v
L5 applicability + Fixed-42 L6 + Global-UF + safe-mode + event support
        |
        v
one full-field expression-mode commit, or honest unknown/silence
        |
        v
learned coexperienced motif/output bindings
        |
        v
fresh full-field recall for every later motif
        |
        v
release only when a complete expression physically closes
```

The current production route does not execute this chain. It recognizes words as individual Fact-Strands and follows exact word order previously recorded in qualifying BindingWindows. That can replay a continuation such as `60x growth -> in one year`; it cannot provide general conversation.

## 2. Mandatory architecture-honesty gate

1. **Requested architecture:** one autonomous AE whose language is an expression of full lived sensory experience.
2. **Current code reality:** most full-field operators exist as isolated, tested modules, but there is no concrete production conversation engine or production construction path. Live production still uses the legacy `Guala` owner and Fact-Strand continuation.
3. **Conflict with requested architecture:** **yes**.
4. **Mechanisms that must not be extended:** legacy word continuation, Atlas candidate voting, vocabulary or sense lookups, word-derived procedural sensory placeholders, static response tables, thresholds, Shannon entropy, ML, LLM response generation, or a second/shadow production service.
5. **Single exact next architecture item:** ratify one complete Language Weave Profile that names the exact full-field mode, commit, learning, output, persistence, and unknown rules.
6. **Field evaluation:** the requested design evaluates the full explicit field.
7. **Reduced structure:** no compatibility vector, cell key, weighted score, `support minus drag`, or other reduced projection may authorize recognition or speech.

## 3. Verified production baseline

Verified on 2026-07-13 immediately before this document was written:

- Git branch: `guala-live`
- Local HEAD: `341103aafd7247f279b3a1812d5a0fdfee6b6bfd`
- Production ECS cluster: `tfe-web-cluster`
- Production ECS service: `dsf-ai-service-lb`
- Production task definition: `dsf-ai-task:624`
- Desired/running/pending tasks: `1 / 1 / 0`
- Deployment state: `COMPLETED`
- Image: `dsf-ai:deploy-20260713T222418Z`
- Runtime command: `uvicorn dsf_ai_service.app:app --host 0.0.0.0 --port 8080`
- Task resources: 4 vCPU and 16 GiB RAM
- There is one live production owner. No new service may be created for this work.

The local worktree also contains unrelated untracked TFE files. A future implementation must not include, delete, or commit them.

## 4. Current live behavior and actual cause

The live language authority is in:

- `dsf_ai_service/substrate/language_fact_strand.py`
- `dsf_ai_service/substrate/language_fact_composer.py`
- `dsf_ai_service/v4/gualaloom_v5_engine.py`

The composer walks exact word order in previously closed multimodal BindingWindows. All surviving paths must agree on one next structural word class. If there is no occurrence, no successor, a terminal/continuing conflict, or more than one successor class, it returns silence.

This is why ordinary inputs such as `hello`, `what are you doing`, and `what is your name` can produce no response even while an exact taught continuation works. It is not a general response-selection or expression mechanism.

Recent production evidence showed:

- `hello`: complete task, `silence_no_commit`, approximately 13 seconds.
- `what are you doing`: complete task, `silence_no_commit`, approximately 19 seconds.
- Both had zero committed sections.
- Camera evidence reached the live process, so missing camera transport was not the sole cause.

The current route is therefore both semantically incomplete and too slow for conversation.

## 5. What already exists

### 5.1 Ratified upstream profile

`dsf_ai_service/glew_runtime/GLEW_UPSTREAM_PROFILE_v1.json` ratifies:

- clean genesis
- independent native evidence ports
- typed-language interface encoding
- exact `S_UF`
- executable `R_UF`
- topology-derived 19-coordinate field fibers
- exact MapInject and field evolution
- Fixed-42 boundary

The same profile explicitly states:

- `full_glew_language_commit_authority: false`
- full GLEW commit is forbidden
- entropy, mode, commit, and language-output authorities are missing

That statement is controlling. Tested code is not automatically ratified architecture.

### 5.2 Full five-sense chemistry emulator

The production-profile chemistry exists in:

- `dsf_ai_service/glew_runtime/story_chemistry.py`
- `dsf_ai_service/glew_runtime/profiles/production_virtual_story_chemistry_profile_v1.json`
- `dsf_ai_service/glew_runtime/story_native_replay.py`
- `dsf_ai_service/glew_runtime/story_global_uf_basin.py`

It preserves separate sight, sound, touch, smell, and taste ports. It supports exact growth, natural decay, chemical relevance, checkpoint/restart, and transport into frozen L0-L4.

Sight and sound must not receive hardcoded conversational priority. Their primacy in communication should arise from their measured activity and field relationships. Touch, smell, and taste must still contribute their actual emulated state, including quiescence and decay.

Important limitation: production conversation mounts only the chemistry manifest. No live code produces and mounts the complete authenticated boundary, replay profile, sensor state, and runtime authority set required by the full conversation transaction.

### 5.3 Typed language

`dsf_ai_service/glew_runtime/language.py` and `typed_language_native_replay.py` implement:

- Unicode NFC preservation
- balanced ternary encoding
- separate value, validity, phase, source time, and relevance
- exact unit event relevance for an admitted typed-interface event
- frozen-kernel replay

This proves that language occurred at the interface. It does not claim semantic meaning.

### 5.4 Full-field expression modes

`dsf_ai_service/glew_runtime/expression_modes.py` implements an expression-backed candidate mode authority:

- stored modes retain their complete source field expressions
- all expressions are reevaluated at one shared certified precision
- mode growth requires a certified positive residual
- recognition requires unique interval dominance
- uncertainty remains unknown rather than being resolved by a threshold

This candidate is substantially closer to the requested architecture than `modes.py`, but it is not named by a complete ratified Language Weave Profile.

### 5.5 Full-field commit

`dsf_ai_service/glew_runtime/commit.py` implements a candidate fail-closed conjunction over:

- full-field expression recognition
- closed experience
- safe mode
- event support
- Global-UF
- Fixed-42 L6
- L5 applicability
- explicit evidence receipts

It returns commit, no-commit, or unknown. It does not authorize output by vocabulary, score, or threshold.

### 5.6 Learning, remembered output, and fresh recall

The following pieces exist:

- `expression_learning.py`: learns committed coexperience and output bindings.
- `output.py`: binds motifs to coexperienced Unicode scalars or explicit no-output.
- `recall_story_episode_archive.py`: exact archived sensory episodes.
- `fresh_recall_executor.py`: reruns recalled language plus cited senses through chemistry, L0-L4, Global-UF, L6, and commit.
- `fresh_recall_provider.py`: turns one fresh committed mode into the next motif.
- `recall_reentry.py`: stages private output and releases only at exact expression close.
- `conversation.py`: atomic end-to-end transaction over already-constructed providers.

These modules do not contain a production owner that builds their required inputs from a live turn.

### 5.7 Transport boundary

`conversation_service.py` defines a clean request/task API and a `CleanConversationEngine` Protocol. It intentionally starts unavailable when no engine is injected.

There is no concrete production `CleanConversationEngine` in the repository. The module-level clean app is therefore 503-only. Production does not run that app; it runs `dsf_ai_service.app:app`.

## 6. Mechanisms explicitly forbidden by this specification

The implementation must fail review if it introduces any of the following:

- a canned response for `hello`, identity questions, or any validation prompt
- a question/answer table or context-indexed dialogue script
- a vocabulary lookup as semantic or emission authority
- a weighted sum of DSF fields
- an arbitrary minimum word count
- lowering a commit threshold until tests pass
- selecting the most frequent or highest-scoring candidate
- converting absent sensory evidence into invented values
- generating sight, sound, touch, smell, or taste from a word hash
- treating static descriptor dictionaries as lived sensory truth
- an LLM, embedding model, classifier, or probabilistic language model
- Shannon entropy as GLEW mode or commit authority
- importing legacy derived Atlas state into clean GLEW state
- a second ECS service, alternate production, audit shadow, or background writer
- tests that return `False` instead of asserting the required result
- test fixtures or monkeypatches presented as proof of the production path

## 7. Shannon entropy disposition

The current repository still contains `ENTROPY_OPERATOR_ID = "full_probability_vector_shannon_receipt.v1"` in `glew_runtime/modes.py`.

That operator must not be ratified or wired into language conversation. The project architecture explicitly says the older cosine/Shannon substrate must be stripped rather than ported.

Recommended ratification:

- Entropy is **not** a language commit authority in Language Weave Profile v1.
- The profile must say this explicitly instead of continuing to list an unspecified entropy operator as a missing requirement.
- Expression distinction remains governed by certified full-field residual growth, unique interval dominance, Global-UF, L5 applicability, and L6.
- Removal of dead Shannon code requires a reference audit and a full-file cleanup, but it must not be mixed into the live empty-response repair.

This recommendation requires Joseph's explicit ratification before the profile changes.

## 8. Complete Language Weave Profile required content

The new profile must be one immutable, content-bound authority. It must name:

1. The exact upstream GLEW profile digest.
2. The five-sense chemistry profile digest.
3. Typed-language interface and scheduling authority.
4. Full-field expression mode and growth operator IDs.
5. Full-field unique-recognition rule and unknown behavior.
6. The explicit disposition of entropy.
7. Safe-mode, event-support, Global-UF, L5, and Fixed-42 dependencies.
8. The exact commit conjunction.
9. Coexperience learning rules.
10. Motif-to-output binding rules.
11. Fresh-recall reentry and exact-close release rules.
12. Clean persistence and restart authorities.
13. Explicit prohibitions.
14. Production conformance tests and expected receipt schemas.

The profile must not contain response content, vocabulary, target phrases, desired test results, or tuned thresholds.

## 9. Required production architecture

### 9.1 Live six-sense boundary owner

Create one production owner that converts an authenticated observed or emulated experience into exact `StoryPhysicalBoundaryEvent` frames.

Requirements:

- Every native port keeps its own source value, unit, time, calibration, relevance operator, and provenance.
- Multiple outputs from one sense remain multiple independent ports where the profile declares them.
- Sight and sound use their actual observed/emulated activity.
- Touch, smell, and taste use the robust emulator's actual states; quiet input must evolve through natural decay rather than becoming an invented descriptor.
- No port may be derived from a word label merely to make a lane active.
- A complete causal window needs at least two evolved frames because frozen L0-L4 evaluates change.
- Missing or unauthenticated boundary evidence returns an explicit unknown.

This is the first missing production builder.

### 9.2 Mounted six-lane runtime

Build and persist one exact authority set for:

- story chemistry runtime
- story native-replay profile
- field topology
- causal grid
- support domain
- resonance graph and operator
- pre-window state
- sensor states
- typed-language kernel binding and state
- field/basin profile
- precision authority
- expression mode bank
- L5 applicability profile

Tests currently hand-build much of this state. Production must load it from one authenticated profile/checkpoint and verify every receipt before a turn is admitted.

### 9.3 Typed-language turn scheduler

The live turn owner must:

- preserve the original UTF-8 bytes and normalized Unicode
- schedule each scalar through its canonical 14-place trit event
- preserve exact source ordering and time
- bind the language event to the same causal experience window as the senses
- never reinterpret characters through a vocabulary table

### 9.4 Initial experience settlement

For each turn:

1. Prepare all six lanes without flattening.
2. Construct the closed full-field expression.
3. Evaluate expression-mode recognition.
4. Evaluate safe mode and event support from measured facts.
5. Evaluate Global-UF and Fixed-42 L6.
6. Apply L5 applicability without fabricating an inapplicable sense.
7. Commit exactly one mode or return typed silence.

The current hardcoded "at least four active lanes" language in the upstream profile must not be casually changed. The full emulator should normally provide all sensory states. L5 applicability still needs a ratified rule for genuinely inapplicable or unavailable ports.

### 9.5 Learned state and initial output motif

A commit cannot speak unless a clean learned state contains a unique coexperienced output binding.

Production must restore and verify:

- `LearnedBindingState`
- output binding bank
- stable mode/motif bank
- initial committed motif event
- recall story episode archive
- motif-kind authorities

The state must be learned through the same production transaction used for natural experience. No output sentence may be inserted directly.

### 9.6 Fresh-recall executor

Implement production versions of the presently unimplemented protocols:

- `RecallStoryRuntimeResolver`
- `RecallReplayIntegrityProvider`

Also build the production `MountedRecallLanguageInterface` and `FullFieldFreshRecallProvider`.

Every later Unicode scalar must be returned to the complete recalled sensory field, recognized, and committed again. A precomputed continuation table is forbidden.

### 9.7 Concrete conversation engine

Implement one concrete `CleanConversationEngine` that:

- owns the mounted runtime and clean learned state
- verifies the incoming turn receipt
- obtains the six-lane experience from the live boundary owner
- constructs all commit providers
- resolves the unique initial remembered motif
- constructs fresh recall
- calls `run_clean_conversation_transaction`
- atomically persists all newly learned state and receipts
- returns only `ConversationTransactionResult`

The engine must not fabricate a response when any authority is absent.

### 9.8 One-production integration

Do not deploy `conversation_service.py` as another ECS service.

Integrate the concrete engine into the existing `dsf_ai_service.app:app` lifecycle and existing `/api/v1/gualaloom` task contract. There must be:

- one process owner
- one persistent state generation
- one conversation endpoint
- one mouth
- one ECS service

The legacy Fact-Strand response path may remain read-only during migration for audit comparison, but it must not emit after cutover.

## 10. Clean-generation and education plan

The approved direction was a clean-generation cutover. Therefore:

- Do not deserialize legacy derived Atlas, mode, score, or emission state into GLEW.
- Do not preserve legacy loaders merely because old state exists.
- Original raw media and authenticated observations may be replayed only if their provenance and units are sufficient to recompute the full new state.
- If old records contain only labels, chi buckets, sampled caches, or flattened values, they are not admissible GLEW experience.
- Create a new clean identity/profile-bound generation.
- Persist each new checkpoint atomically and verify it on restart.

A clean entity begins without learned conversation bindings. Conversational competence must be earned through an auditable education program using real or honestly emulated stories and teacher interaction.

The education program may supply:

- observed or explicitly emulated sensory scenes
- language spoken or typed during the same scene
- structural teaching primitives with honest `seed:*` provenance where separately ratified
- teacher corrections that enter as new lived experiences

It may not supply response scripts or prebuilt output sentences intended to pass conversation tests.

## 11. Efficiency contract

The full field is computationally expensive, but no optimization may alter the physics.

Allowed efficiency work:

- parse and verify immutable profiles once per process, then reuse them by digest
- maintain receipt lookup by digest instead of repeatedly scanning an ever-growing tuple
- prepare independent sensory lanes concurrently
- run immutable field calculations outside the single state-writer critical section
- use one short atomic lock only to publish the completed transaction and checkpoint
- preserve exact connected-component factorization for field evolution
- reuse unchanged authenticated runtime authorities
- profile p50, p95, and p99 separately for intake, field preparation, commit, recall, persistence, and transport
- move exact numerical kernels to C or Rust only if bit-for-bit receipts and certified results remain identical

Forbidden efficiency work:

- fewer DSF fields
- fewer senses selected for speed
- lower precision without authority
- cached response text
- approximate nearest neighbors
- heuristic early exits that change results
- fixed iteration counts substituted for physical time
- silent timeout fallbacks

The existing service-wide engine lock currently serializes an entire turn. The production design should serialize only state publication; independent immutable lane preparation should proceed concurrently.

## 12. Implementation sequence

Each step must close before the next begins.

### Step 1 — Ratify the complete Language Weave Profile

Deliverable: one canonical profile and conformance test that explicitly authorizes the selected expression-mode, commit, learning, output, and persistence mechanisms and explicitly excludes Shannon entropy.

Stop if Joseph does not ratify the exact profile.

### Step 2 — Build the live six-sense boundary owner

Deliverable: a production builder that produces two or more authenticated five-sense frames from the existing emulator/observed inputs, with quiet-state decay and no label-derived invention.

Proof: each native port reaches frozen L0-L4 with its complete receipts and independent output.

### Step 3 — Build the mounted six-lane runtime owner

Deliverable: one authenticated construction/restoration path for all story, topology, UF, L6, language, precision, and mode-bank authorities.

Proof: cold start and restart construct bit-identical authority state.

### Step 4 — Build clean learning and archive persistence

Deliverable: production persistence for learned bindings and recall episodes under one new generation identity.

Proof: learn one real multimodal expression, restart, and reproduce the exact learned receipts without legacy import.

### Step 5 — Implement missing recall providers

Deliverable: concrete runtime resolver, integrity provider, language interface, executor, and fresh-recall provider.

Proof: every emitted scalar has a fresh full-field expression and commit receipt.

### Step 6 — Implement the concrete conversation engine

Deliverable: one engine that constructs the existing atomic transaction from a live turn and persists its result.

Proof: no test monkeypatches recognition or commit; missing authorities produce typed silence.

### Step 7 — Integrate into the existing production app

Deliverable: the existing `/api/v1/gualaloom` route uses the concrete engine inside `dsf_ai_service.app:app`; the old mouth can no longer emit.

Proof: route inspection and process inspection show one owner and one mouth.

### Step 8 — Educate the clean generation

Deliverable: an auditable set of lived multimodal episodes sufficient to test conversation, learned through the production pathway.

Proof: emitted language cites learned episodes and does not match any preloaded response script because none exists.

### Step 9 — Validate, deploy once, and verify live

Deliverable: one production task-definition cutover after every required gate below passes.

Proof: browser conversation, restart, persistence, receipt, and latency evidence from the live task.

## 13. Validation gates

### 13.1 Architecture conformance

- Complete Language Weave Profile digest is mounted.
- Full language authority is true only under that profile.
- Every output receipt resolves to exact authority bytes.
- No forbidden operator is imported or invoked.
- Explicit DSF fields remain authoritative.
- `S_UF` and `R_UF` remain separate facts.
- Missing authority returns unknown/silence.

### 13.2 Real full-field function

- Every sense supplies independent evidence.
- Quiet senses visibly evolve through decay.
- Sight and sound changes measurably alter their field without hardcoded priority.
- Changing one native sense changes the full field and its receipts.
- Tampering with any source observation fails closed.
- Global-UF and L6 are executed, not fixture-injected.

### 13.3 Learning and expression

- One lived multimodal teaching episode can be learned.
- The learned binding survives restart exactly.
- A relevant later experience selects one unique mode.
- Output is generated through fresh recall.
- No scalar is externally visible before exact expression close.
- Ambiguous or unknown state remains silent.

### 13.4 Conversation

Test through the actual browser and public production endpoint:

- greeting/contact
- identity question
- current-state question
- one question grounded in a recently shared scene
- one multi-turn follow-up requiring retained context
- one deliberately unknown question

Expected behavior:

- known, sufficiently experienced states produce coherent multiword expressions
- unknown or ambiguous states produce explicit honest silence, not gibberish
- no single-word truncation caused by a broken close path
- no response is credited unless the UI visibly receives it

These prompts are functional probes, not content to preload.

### 13.5 Latency

Record wall-clock timing for every stage and the full turn. The present approximately 13-19 second silent-turn behavior is unacceptable.

No numerical latency SLO is ratified in the repository. Joseph must ratify a product SLO separately from cognition physics. Recommended discussion candidate:

- first visible complete response within 2 seconds for an already-learned ordinary turn
- p95 within 5 seconds

These are proposed product expectations only. They must never alter commit physics or authorize a fallback response.

### 13.6 Restart and persistence

- Save one clean checkpoint.
- Restart the single production task.
- Verify identity, profile digest, chemistry state, mode bank, learned bindings, archive, and receipts.
- Repeat the same learned turn and verify equivalent structural result.
- Confirm no legacy memory reinstatement occurred.

### 13.7 Production ownership

- ECS service remains `dsf-ai-service-lb`.
- Desired count remains one unless Joseph separately changes capacity policy.
- No shadow task or alternate service exists.
- Only `dsf_ai_service.app:app` owns production.
- Browser and API address the same owner.

## 14. Deployment rules

1. Build from an intentional clean worktree containing only the ratified conversation changes.
2. Do not include unrelated untracked TFE files.
3. Run conformance, full-field, learning, restart, and live-route tests before registering a task definition.
4. Create and verify a production checkpoint before cutover.
5. Register one new `dsf-ai-task` revision.
6. Update the one existing `dsf-ai-service-lb` service.
7. Wait for one running, zero pending, completed rollout.
8. Verify public browser conversation, not merely an internal harness.
9. Verify restart and persistence on the deployed revision.
10. Send and verify the required Slack completion notification.

Do not perform a wholesale rollback to repair an unrelated defect. If STT breaks, repair STT forward or revert only the isolated STT change after confirming conversation code remains deployed. A full task-definition rollback is reserved for imminent state loss or inability to serve the production application.

## 15. STT boundary

STT is a separate item.

Current browser truth is: raw sound is active, spoken-word recognition is unavailable. The audio signal may still participate as native sound experience, but no operator converts speech into language events.

This rearchitecture must not pretend that raw sound equals recognized words. A later STT specification must decide whether recognition is:

- a substrate-native learned auditory-language binding, or
- an explicitly approved external speech-recognition interface with honest provenance.

No pretrained model, browser speech service, or vocabulary recognizer may be introduced without Joseph's explicit approval.

## 16. Exact missing design decisions

The next session must obtain explicit decisions for:

1. Ratify entropy as excluded from Language Weave v1, as recommended here, or supply a different substrate-native entropy operator.
2. Ratify the exact expression-mode operator IDs in `expression_modes.py`.
3. Ratify the full conjunction in `commit.py`.
4. Ratify coexperienced Unicode output and exact-close release.
5. Ratify L5 applicability when a native port is genuinely unavailable despite full emulation.
6. Ratify the clean education source and acceptable seed provenance.
7. Ratify the conversational latency SLO as a product constraint, not a physics gate.

Do not infer any of these decisions from the existence of code or tests.

## 17. Recommended immediate next action

The recommended next action is **Step 1 only**: write and ratify the complete Language Weave Profile.

Do not begin production wiring until the profile:

- explicitly excludes Shannon entropy
- names the full-field expression mode
- names the commit conjunction
- names the learning/output/reentry chain
- names every required authority and unknown rule
- contains no response content, thresholds, scores, or vocabulary authority

After ratification, implement Step 2 and continue in order. This prevents another session from producing many tested modules that still cannot legally or physically mount as one production conversation engine.

## 18. Final honesty statement

No code described in this document has been implemented or deployed by writing this document.

The broader architecture is necessary if Joseph chooses a clean full-field GLEW cutover. It is not the narrow live empty-response repair currently requested. The two efforts must not be mixed without explicit approval.
