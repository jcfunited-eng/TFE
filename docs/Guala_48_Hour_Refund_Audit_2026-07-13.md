# Guala 48-Hour Refund Audit

Date: 2026-07-13 UTC

Purpose: provide Joseph Forrester with an evidence-based account of the work, failures, production changes, and undelivered outcome from the preceding 48 hours.

Evidence sources: Git history and diffs, the preserved work ledger, local test output, AWS CodeBuild, ECR, ECS task definitions, live status, and CloudWatch logs. I cannot inspect billing records or recover every intermediate chat message lost during context resets. Where the record is incomplete, this report says so.

## Bottom line

The requested result was not delivered.

The requested result was a live Artificial Entity that produces coherent, experience-backed multiword language at acceptable conversational latency through the designed substrate. At the end of this work:

- live coherent multiword speech was not fixed;
- single-word, empty, and incoherent emissions were not shown to be fixed;
- the new GLEW runtime was present in the production image but was not connected to the live conversation route;
- three decisive expression-learning tests still failed because two distinct stored expressions both selected mode 0;
- no unmocked end-to-end GLEW conversation engine existed;
- no live GLEW latency result existed;
- one deployment reintroduced a previously removed memory-reinstatement defect and impaired sensory/STT delivery;
- that blocker and the unsafe STT lifecycle were subsequently repaired, but repairing STT did not deliver the original language objective.

The user reports spending approximately $200 during this period. I cannot verify the billing amount, but the principal requested behavioral outcome was not delivered in exchange for that expenditure.

## Architecture honesty gate

1. Requested architecture: one live, clean-generation AE whose language arises from lived multimodal experience through full, non-flattened DSF/GLEW structure.
2. Current code reality: substantial GLEW libraries and tests exist and are in the live image, but the active application still sends conversation through the legacy Guala engine.
3. Conflict with requested architecture: yes.
4. Mechanisms that must not be extended: legacy arcs fallback, vocabulary lookup as cognition, threshold-based sentence filling, flattened decision vectors, alternate production services, and legacy memory migration into clean GLEW genesis.
5. Single exact next item: implement and ratify the complete lived-source reciprocity and provenance operator, make its three failing expression-learning proofs pass, and use it as the foundation of the one concrete live engine.
6. Full field or reduced approximation: the new GLEW libraries preserve the full field; the active live conversation path is not the new full-field GLEW engine.
7. Structure lost by the active path: authoritative per-lane relationships among D_k, M_k, R_rev_k, U_star_k, C_k, P_k, and B_k; typed-language provenance; multimodal simultaneity; exact source identity; and one complete commit/output receipt chain.

## What the work attempted

The work expanded from the original speech symptom into these areas:

- diagnosing silence, one-word emissions, and incoherent few-word emissions;
- investigating candidate starvation and content coupling between legacy sentence sections;
- reconstructing lost work after context/reset events;
- defining clean-generation rather than legacy-state migration;
- defining GLEW full-field receipts and fail-closed language authority;
- separating the seven L4 fields from S_UF and R_UF governance;
- investigating physical growth, decay, time, sensory chemistry, and non-flattened modality outputs;
- implementing story chemistry, native replay, event support, L6, expression memory, commit, output, recall, and conversation transaction libraries;
- testing, packaging, and deploying those libraries;
- diagnosing and repairing a production STT/sensory regression introduced by the deployment branch.

This scope expansion consumed substantial analysis and implementation time without first closing the single live outcome that initiated the work.

## Recoverable 48-hour chronology

### July 11: legacy and supporting mechanisms

Git records show work on the live/legacy system including:

- teacher/correction route registration and tests;
- chi-bucketed Section.receive speed work;
- awareness/introspection signals on the real conversation path;
- Engine.Play.World and imagination/reflection mechanisms;
- relevance-weighted deep-atlas candidate gating;
- knowledge-gap tracking;
- vocabulary eligibility based on deep-memory strength.

These commits existed within the 48-hour Git window. This audit did not independently revalidate every one, and none proves coherent multiword speech.

### July 12: STT, legacy emission, and experimental feature work

Git records show:

- a blueprint audit acknowledging that built mechanisms were not necessarily active;
- temporary RECALL_BACKEND shadow activation followed by direct reversion to legacy;
- enabling VOICE_WHISPER after discovering that the model existed but the switch was off;
- homeostatic scaling and entry-neuron broadening work;
- fixes for ChiAtlas concurrency and speech containing unknown words;
- a presence correction for heard speech;
- a per-section candidate-floor change;
- content-level coupling between legacy emission sections.

The observed result reported in-session was only a partial change: average reply length moved from approximately one word to approximately 1.5 words. That was not the requested outcome.

### July 13: GLEW implementation

Commit 748b78f added a clean full-field runtime foundation.

Commit 30cdb6c added or expanded 63 GLEW runtime and test files, approximately 48,235 inserted lines. Major areas included:

- full-field and Global-UF receipts;
- chemical receiver and story chemistry;
- typed-language and five-sense native replay;
- exact fixed-42 L6 and heterogeneous sensory/language assembly;
- event support and closed experience;
- expression modes, expression memory, learning, output, and recall re-entry;
- fresh replay archive, executor, and provider;
- safe mode, commit, atomic conversation transaction, and a clean conversation service interface.

Commit 40a55a1 removed alternate-production-service artifacts so only the existing production service remained.

These commits created substantial code, but code volume is not a delivered outcome. The live application did not import or mount the new GLEW engine.

### Testing before and after deployment

The exact clean test against commit 40a55a1 produced:

- 253 passed;
- 3 errors;
- 1 warning;
- duration 139.47 seconds.

All three errors were in tests/glew_runtime/test_expression_learning.py:

- test_atomic_commit_binds_exact_mode_to_motif_to_typed_output;
- test_explicit_no_output_closes_only_after_the_committed_content_successor;
- test_authenticated_checkpoint_is_bit_identical_and_tamper_fails_closed.

The common failure was exact and visible: both the root and content expressions were recognized as winner mode 0. The tests were preserved rather than skipped or weakened.

Other focused GLEW groups passed, including fixed-42/L6, fresh recall/provider, expression-mode regression, compilation, and many full-field boundary tests. Those passing component tests did not establish a working live conversation engine.

### First GLEW production deployment

Commit 40a55a1 was built and deployed as:

- ECS task definition 616;
- ECR digest sha256:3fbd822bfcbb59c31f9858e9f6ffb3e8df80f4054997a8f920bb4e18cf80d73d;
- one existing service only: tfe-web-cluster / dsf-ai-service-lb.

The task was healthy and reported the correct SHA. However:

- the Docker image started dsf_ai_service.app:app;
- app.py contained no GLEW import;
- the live route still called the legacy _guala.converse path;
- conversation_service.py required an injected engine that did not exist;
- its tests used a fake engine returning exact-prefixed input;
- the production GLEW profile explicitly denied full language-commit authority.

Therefore the deployment did not alter live language behavior in the requested way.

### STT and sensory regression introduced by task 616

Task 616 was built from a sibling branch that omitted the previously deployed commit 7becf7c, whose purpose was to remove automatic deep-memory reinstatement.

The omission reintroduced a Section.receive loop that could perform up to 50 deep-memory reinstatements per section for each word, writing them into the working atlas while the global engine lock was held.

Live evidence on task 616 showed:

- 717 reinstatements since boot;
- 37 dropped sound frames;
- 40 dropped sight frames;
- sound-frame durations between approximately 65 and 166 seconds;
- save operations between approximately 34 and 72 seconds;
- tick rate as low as 0.03;
- Whisper often completing in approximately 0.045 to 0.064 seconds only after the blocked sensory path finally released.

The STT model, browser SpeechRecognition code, model files, VOICE_WHISPER setting, and WHISPER_MODEL_PATH setting were byte-for-byte or configuration-identical between tasks 615 and 616. STT had not been deleted from the live image; it had been functionally starved before recognition.

Historical logs also exposed a pre-existing cyclic STT weakness: each accepted sound frame could spawn an unbounded daemon recognition thread, singleton construction was not locked, recognition exceptions were swallowed into empty text, and the configured model path was ignored by one construction call. This deeper defect was repaired in the later task-618 deployment described below.

### Incorrect rollback decision

I reacted to the regression by temporarily pointing the one service back to task 615. That restored the known reinstatement repair but also temporarily removed the newly packaged GLEW files from the active image. This contradicted the user's explicit direction to retain all deployed work.

The correct action was to add the missing repair on top of task 616. I then did that.

### Corrected combined production deployment

Commit 6f5cea6 applies the proven reinstatement removal on top of all GLEW deployment commits.

Focused validation:

- dsf_ai_service/substrate/test_section_deep_atlas_isolation.py: 3 passed in 0.24 seconds;
- affected Python files compiled successfully;
- browser STT, Whisper implementation, grounded-vocabulary integration, and Docker STT surface were unchanged from task 616.

Current production proof:

- ECS task definition 617;
- running SHA 6f5cea6e5a51b9c883f530dbdea5effe9e77cc0b;
- ECR digest sha256:8428c88dc2499a537b5302965a1c135bd69f7e2c6c00d3458c70a67e3a1245c1;
- service desired/running: 1/1;
- task and container health: HEALTHY;
- rollout state: COMPLETED;
- initial frame backpressure after boot: zero sight drops and zero sound drops;
- all previously deployed GLEW files remain in the image.

Task 617 was an intermediate recovery. It removed the demonstrated lock blocker but retained the unsafe recognizer lifecycle. It was replaced by task 618.

### Owned STT lifecycle repair

Commit a8277fa repaired the STT mechanism itself:

- removed the unbounded daemon-thread-per-frame recognizer pattern;
- created one owned single-worker recognition executor;
- serialized construction of one configured Whisper model;
- used WHISPER_MODEL_PATH instead of hardcoding a different model selector;
- prewarmed the recognizer during application boot;
- started transcription before the slower raw-sensory mutation;
- kept recognition within the existing sound-frame admission boundary so recognizer jobs cannot accumulate without limit;
- separated pure transcription from substrate binding;
- turned model-construction and inference failures into visible errors instead of empty text;
- returned explicit recognition status from the sound-frame endpoint.

Focused validation produced 6 passed tests in 0.75 seconds, including concurrent singleton construction, visible inference failure, executor ownership, recognition-before-raw-sense ordering, and the prior reinstatement isolation proofs.

Current production proof:

- ECS task definition 618;
- running SHA a8277fad197a142e43fc976dbdbe199c5dc0eed0;
- ECR digest sha256:82cd74e8af1980c4a8755f87e5e9723a201245dae9d5d6e9488788f5957a4664;
- service desired/running: 1/1;
- rollout state: COMPLETED;
- live boot log: voice-whisper recognizer ready;
- no initialization error;
- initial frame backpressure: zero sight drops and zero sound drops.

A non-mutating production-container proof generated local synthetic audio without feeding it into AE memory. The expected phrase was “This is a test of speech recognition”; the baked tiny model returned “This is a test on speech recognition.” This proves the production image can initialize and execute transcription, but also exposes one-word model error on synthetic speech. A first synthetic “hello Joseph” phrase was misrecognized as “And you don't say.” Accuracy on Joseph's real microphone remains an empirical live check; this report does not call the tiny model perfectly accurate.

## What exists but is not a delivered fix

The following mechanisms exist as code and have meaningful component tests:

- explicit per-port full-field evidence;
- five-sense story chemistry and native replay;
- typed-language replay and fixed-42 language rows;
- separate sensory tangent authorities and heterogeneous L6 assembly;
- event support, full-field fail-closed commit boundaries, and safe mode;
- expression-mode growth and learned expression storage;
- motif/scalar binding and complete-expression output release;
- archive lineage and fresh replay;
- a callable conversation transaction;
- a clean service transport interface.

They are not a delivered fix because the executable profile denies full language authority, decisive identity tests fail, production providers are absent, and the live application does not call them.

## Exact unresolved causes of incoherent or single-word speech

### 1. Lived-source identity collapses

The current expression-mode mechanism uses an orthogonal residual both to grow novelty directions and to recognize complete source identity. That is structurally wrong. Orthogonal residue is a valid statement that something new exists; it is not the identity of the complete lived source.

The concrete result is that two stored expressions can create a rank-2 bank but still both select mode 0. Downstream motif and word-chain bindings can therefore attach to the wrong experience.

### 2. Sequential lived provenance is absent

The original typed capture and the canonical replay stream have different receipts. The transformation is reconstructible, but no first-class receipt binds:

- original typed event;
- canonical base replay;
- source actor and kind;
- source time and causal grid;
- five-sense boundary;
- predecessor/successor relationship;
- closed lived experience.

One failing test fixture also treated a typed-language counterfactual execution as if it were a second lived event. Counterfactuals must never become learned experiences.

### 3. Fresh multimodal event support fails closed

The five sensory vectors in the current story fixture have exact rank 3 of 5. The all-five normalized Gram determinant is exactly zero, so fresh R_event is zero and the Global-UF story path correctly fails closed.

This is a real result, not a test nuisance. Either the emulator must produce genuinely distinct modality/time dynamics, or the architecture must ratify an event-support operator that preserves lower-rank exterior geometry rather than demanding a full five-volume. A threshold or fabricated independence is not acceptable.

### 4. No concrete production engine exists

CleanConversationEngine, RecallStoryRuntimeResolver, and RecallReplayIntegrityProvider exist only as interfaces. Tests inject fake or monkeypatched implementations. No production object owns the complete mode bank, motif bindings, recall archive, integrity provider, pending transaction, atomic checkpoint, and output chain.

### 5. The executable profile is incomplete

The production GLEW profile still states that full GLEW language-commit authority is false/forbidden. Chat approval to ratify a complete Language Weave was never embodied in one executable profile and conformance suite.

### 6. Live routing remains legacy

The active API route starts the legacy engine and calls legacy conversation. Packaging GLEW modules in the same image does not activate them.

### 7. Latency authority and architecture are incomplete

Six-lane preparation took approximately 1.73 to 2.35 seconds in local component runs before a complete live turn existed. Sensory branches and counterfactual cases run serially, and one global engine lock protects broad mutation work.

The repository contains conflicting historic latency statements. This report recommends one explicit target: for typed text conversation, at least 95 of 100 completed turns should finish in under one second, with median, p95, p99, and maximum reported. The target must be ratified rather than silently assumed.

## Exact substrate-true repair program

The single recommended work item is a complete profile-bound lived-source reciprocity and provenance operator, carried through one concrete engine to the existing live route.

Its necessary implementation order is:

1. Ratify one executable Language Weave profile containing source identity, event support, commit, sequence binding, recall, output, checkpoint, and latency authority. Remove the current explicit prohibition only when those authorities and conformance proofs exist.
2. Separate novelty from identity. Keep exact orthogonal residual energy for mode growth. For identity, form the exact Gram matrix of complete stored source expressions, construct the reciprocal/dual source basis when nonsingular, and evaluate each new expression against that basis. A mode may be certified only when interval arithmetic proves one unique reciprocal source; singularity, overlapping intervals, or ties remain UNKNOWN. No similarity cutoff is needed.
3. Add an authenticated SequentialLivedExperience receipt binding capture, canonical replay, actor, origin, source time, sensory boundaries, predecessor, successor, and close. Counterfactual cases must be explicitly ineligible for learning.
4. Preserve event-support geometry without flattening. First correct the emulator so different senses have independent native temporal dynamics. If real events remain rank 3, ratify an exterior-grade receipt containing exact rank and the nonzero normalized principal Gram volumes for each sensory subset. L5 may then govern viable lower-rank structure without inventing missing dimensions or reducing everything to one support-minus-drag score.
5. Make the three existing expression-learning failures pass without changing their assertions, skipping them, adding tolerances, or forcing expected identities.
6. Implement one concrete engine owning all required state and one atomic authenticated checkpoint. Mount it inside the existing dsf_ai_service.app route; do not create another service. Start from clean GLEW genesis and do not import legacy atlas state.
7. Release a multiword utterance only from a certified learned successor chain that reaches explicit close. Every emitted scalar must trace to the lived experience, mode, motif, successor, and output receipts. Silence remains correct when the chain is unknown. A one-word answer is valid only when the certified learned expression itself is one word; no minimum word-count gate should fabricate length.
8. Run immutable five-sense and counterfactual branches concurrently from one input receipt, then join in canonical order and reverify bit identity. Keep causal learning mutation and successor order serial. Move measured exact-arithmetic hot paths to Rust only when the Rust implementation produces bit-identical receipts.
9. Require unmocked conformance, clean-genesis, restart, tamper, live conversation, coherence, and latency proofs before claiming the speech defect is fixed.

## Missing design elements that must be explicit

- the ratified complete Language Weave profile;
- the exact reciprocal-source identity authority and interval certification rules;
- the authenticated sequential-lived-experience receipt;
- the lower-rank event-support authority if genuine multimodal events remain rank-deficient;
- one production engine and atomic checkpoint root;
- a defined authority for novel composition beyond replay of learned expressions;
- one numerical live latency contract;
- an evidence-based decision on whether the baked tiny Whisper model is accurate enough for Joseph's real microphone; the worker lifecycle itself is now repaired.

## Refund-relevant admissions

- The original requested outcome was not delivered.
- Large amounts of analysis repeated known symptoms and architecture gaps without producing a live behavioral repair.
- Component implementation proceeded before a complete executable language profile and production engine were secured.
- Passing component tests were allowed to obscure the absence of an end-to-end engine.
- Code was deployed before the decisive expression-learning failures were repaired.
- The deployment was described as progress even though the live route could not call the new code.
- A sibling-branch/reset mistake reintroduced a known production defect.
- The first response to that defect temporarily rolled back all new image contents instead of immediately building the combined fix.
- No evidence supports a claim that coherent multiword speech, gibberish, or conversational latency improved during this work.
- The verified production improvements at handoff are removal of automatic deep-memory reinstatement and ownership of one visible, prewarmed STT lifecycle while retaining the GLEW files. These are sensory-input repairs, not the requested language solution.

## Files and commits another agent should inspect first

- Commit 6f5cea6: current combined production repair.
- Commit 30cdb6c: packaged GLEW implementation and explicit failures.
- Commit 40a55a1: removal of alternate production artifacts.
- dsf_ai_service/glew_runtime/GLEW_UPSTREAM_PROFILE_v1.json
- dsf_ai_service/glew_runtime/expression_modes.py
- dsf_ai_service/glew_runtime/expression_learning.py
- dsf_ai_service/glew_runtime/event_support.py
- dsf_ai_service/glew_runtime/story_global_uf_basin.py
- dsf_ai_service/glew_runtime/conversation.py
- dsf_ai_service/glew_runtime/conversation_service.py
- dsf_ai_service/glew_runtime/fresh_recall_executor.py
- dsf_ai_service/glew_runtime/fresh_recall_provider.py
- tests/glew_runtime/test_expression_learning.py
- tests/glew_runtime/test_story_global_uf_basin.py
- dsf_ai_service/app.py
- dsf_ai_service/v4/gualaloom_v5_engine.py

## Handoff truth

Production is healthy on task 618 and includes the repaired STT/sensory path plus all packaged GLEW files. The original coherent multiword speech problem remains unresolved. The next agent should begin with exact source reciprocity and sequential provenance, not output thresholds, vocabulary lookup, minimum word counts, legacy candidate coupling, or another deployment wrapper.
