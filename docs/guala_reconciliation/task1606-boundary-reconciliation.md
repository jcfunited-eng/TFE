# Task1606 serving, active-memory preservation and speech boundary audit

> **Newer measurement:** [October10,11:12–11:19 Task1606 refresh](serving-refresh-20261010T111240Z.md) records the replacement container and intermittent responsiveness. The observations below retain their earlier date. No recovery or learned-speech pass is inferred.


**Overall reconciliation OPEN. No speech, system or ML-free certificate.** Complete four named source captures plus explicitly bounded independent Task1606 serving/artifact reads. Exact Python bytes are live-bound; Rust source matches the packaged manifest and wheel/native identity. Full dependencies, reproducible build, dynamic root-cause attribution, acquired-state mapping and behavior qualification remain open. No product actions/tests.

[Structured evidence](task1606-boundary-reconciliation.json), [mechanisms](mechanisms_task1606_boundary.json), [repair actions](remediation-plan.md), [speech decision](speech-decision-record.md). No product program or tests ran in this review.

## TSR01 — Unhealthy serving and native computation retain the interpreter lock

**live_serving_failure_and_source_bound_starvation_mechanism.** Task1606 is RUNNING/UNHEALTHY despite desired/running/pending1/1/0 and COMPLETED deployment. Local /health and /ready GETs timed out after4.0055/4.0034 seconds. In a five-second read-only process sample, thread40 used500 CPU ticks at100Hz while the main thread waited in futex. The native wrapper calls prepare_millisecond and other native work without allow_threads. The exact deployed library contains the same prepare wrapper and a direct call to material.prepare_boundary; the wrapper disassembly has no direct SaveThread/RestoreThread reference.

Evidence limit: Live process sampling did not capture a userspace stack or exact current instruction. This establishes the service failure and a concrete deployed execution hazard consistent with it, not exclusive attribution of every second or every latency cause. Matching source manifest and wheel/native hashes is strong identity evidence but not independently reproduced build provenance. No POST, signal, import or product test was performed.

Remedy: G1 must identify the long-running native boundary on the exact preserved candidate and release the interpreter lock around owned, callback-free native computation, reacquiring it only for Python objects. Preserve one actor, immutable predecessor and exact numerical/state semantics. Independently solve excessive native work through an approved exact algorithm and bounds; unlocking alone makes observation responsive, not cognition real-time. Do not increase health timeouts or publish a synthetic health response as the repair.

| Gate | Required evidence |
|---|---|
| Unit | Verify native ownership/error/rollback and exact transitions with and without lock release; no Python object access while released. |
| Module | Run actual actor computation concurrently with GET health/observation and bounded stop/ingress; demonstrate both responsiveness and actual native progress. |
| System | Measure wall-time versus represented time, sensory age/loss, action and checkpoint progress over a sustained ordinary workload. |
| Release | Bind image/library/source/config/state, repeat live/browser behavior and keep missed deadlines visible. |

Actions: A01, A02, A03, A14, A16, A17. Sources: [TS04 line137](sources/task1606-boundary/TS04--functional64_owner_boundary.rs#L137), [TS04 line138](sources/task1606-boundary/TS04--functional64_owner_boundary.rs#L138), [TS03 line160](sources/task1606-boundary/TS03--guala_functional64_loop.py#L160).

## TSR02 — Commissioning captures a fresh substrate while retaining old experience only as archive

**source_confirmed_preservation_break_in_conversion_branch.** The image-bound GLFUNC01 branch creates ModularSubstrate64D(), captures that new object and commissions a new body, quiet ears, time0 and500000/500000 reserve. It never decodes predecessor acquired native dynamics into that object. Functional64Runtime retains the previous body/world as OriginalPair inert bytes and checks identity/tick. The current durable envelope is GL64ORG1, with57718988 original-body bytes,1050863 original-world bytes and1006673 native bytes. Its current and predecessor descriptor ticks both equal4234925.

Evidence limit: The source proves what this branch does; current envelope shape does not prove which task first executed it or authenticate approval. A1 has not decoded active organism memory, measured particular lost skills or proved that every retained byte is unreachable elsewhere. Current descriptor mtime predates Task1606 startup; no conclusion about all in-memory progress follows from that single durable sample.

Remedy: Preserve both exact histories and recover the cutover authorizations and canonical lineage. Replace fresh-seed commissioning with an explicitly approved correspondence from authentic acquired causative state to active native state. If the state spaces cannot be mapped lawfully, state that boundary and keep qualification failed; do not invent a shim, reset, rewind or claim archive custody is learning continuity. Same UUID/tick is insufficient.

| Gate | Required evidence |
|---|---|
| Unit | Verify each acquired state/relationship, source clock, body/ear state and reserve against the authentic predecessor, with explicit authorized exclusions. |
| Module | Demonstrate old acquired effects remain causative after canonical conversion and exact cold continuation, not merely stored bytes. |
| System | Use later partial cues and meaningful learned actions/words against pre-learning and severed-state controls. |
| Release | Publish exact authorized migration, losses and sole-writer provenance; no preservation certificate from identity or original-byte retention. |

Actions: A01, A02, A03, A04, A09, A10, A16, A17. Sources: [TS01 line261](sources/task1606-boundary/TS01--lean_production_app.py#L261), [TS01 line262](sources/task1606-boundary/TS01--lean_production_app.py#L262), [TS02 line3](sources/task1606-boundary/TS02--guala_functional64_runtime.py#L3).

## TSR03 — Retired controller paths are absent in the newly observed release

**verified_scoped_retirement_improvement_with_open_closure.** Read-only Task1606 inspection found /app/dsf_ai_service/guala_functional_organism.py and guala_functional_loop.py absent. The byte-matched lean startup mounts Functional64Runtime and Functional64PhysicalLoop. This is a concrete improvement over the inspected Task1598 controller activation.

Evidence limit: Two absent paths do not establish all dependency/cognitive-authority closure, heuristic exclusion or preserved learned capability. Packaged guala_voice.py and Whisper-capable speech_transducer.py remain; file presence does not establish their activation or ML inference. The historical Task1598 finding remains valid only at its dated release scope.

Remedy: Keep retired controllers excised and resolve every remaining packaged dependency and live caller. Classify source, assets, algorithm and actual authority separately. Remove unused rejected capability packages from a reviewed closure without deleting authentic learned state or fabricating a replacement voice.

| Gate | Required evidence |
|---|---|
| Unit | Verify forbidden paths, aliases, dependencies and model assets with exact source classification rather than filename-only scanning. |
| Module | Trace import and call authority from the actual lean entrypoint through all senses, decisions and output. |
| System | Qualify learned behavior using only the approved native route on preserved state. |
| Release | Issue package-exclusion and active-inference conclusions separately; never carry an older activation finding into a new image without proof. |

Actions: A01, A02, A03, A05, A10, A15, A16, A17. Sources: [TS01 line221](sources/task1606-boundary/TS01--lean_production_app.py#L221), [TS01 line218](sources/task1606-boundary/TS01--lean_production_app.py#L218).

## TSR04 — The mounted sensory loop rejects camera and food occurrences

**source_confirmed_unimplemented_external_input_boundary.** Functional64PhysicalLoop._external_pressure accepts only a microphone source with exactly4000 PCM samples. It explicitly rejects from_object, retina_rgb_u8, present_food, guided_vocal_drives and focal controls. A pending physical return also raises NotImplementedError. The wider lean translator advertises/translates more input types than this loop implements.

Evidence limit: This is an explicit failure rather than a hidden simulated capability, which must be preserved. It means those accepted-looking request schemas cannot qualify actual camera ingress, caretaker food delivery or the missing chronological owner. It does not prove there are no food objects or no internally observed world light in Task1606; the loop separately acquires world optical state. No mutation request was sent.

Remedy: G1 must reconcile the public/UI capability contract with the actual chronological sensory owner and implement the required physical occurrences with preserved timing, source identity, mass/energy and true world consequences. Keep external food supply separate from internal action choice; do not use caretaker-selected behavior to manufacture foraging or speech.

| Gate | Required evidence |
|---|---|
| Unit | Check every advertised occurrence against the mounted implementation, source clocks and explicit unsupported outcomes. |
| Module | Trace microphone, world vision, required external vision, touch and food supply through authentic physical returns and full DSF. |
| System | Demonstrate ordinary nourishment/foraging and sensory-grounded learned behavior without scripted internal selection. |
| Release | Verify the exact UI/browser/API/image capability matrix and actual sustained sensory loss/latency. |

Actions: A01, A06, A07, A08, A10, A12, A13, A16, A17. Sources: [TS03 line108](sources/task1606-boundary/TS03--guala_functional64_loop.py#L108), [TS03 line104](sources/task1606-boundary/TS03--guala_functional64_loop.py#L104), [TS03 line127](sources/task1606-boundary/TS03--guala_functional64_loop.py#L127).

## TSR05 — Native pressure metadata is honest limited evidence, not learned speech

**implemented_physical_output_with_unqualified_language.** The loop returns actual native finish pressure only after a complete quarter, insists on8000 bytes, hashes those bytes and records said=None with voice_source=native-articulatory-pressure. Actual own-ear pressure is mixed with external PCM and advanced through the cochlear stream. Both ear inputs receive the same mixed block in this interface.

Evidence limit: These are specific transport and physiology mechanisms. The current audit captured no successful quarter, audible utterance, acquired articulation, grounded word or syntax result. A native source tag, nonzero sound, self-hearing,25 frame count or0 Python callback count cannot qualify those stronger claims. Identical left/right delivery provides mono evidence, not a binaural localization demonstration.

Remedy: Preserve actual sound and self-hearing. G1 must first recover usable chronological processing and active acquired-state continuity, then identify the first failed link from experience through retained contact change, later preparation, articulatory action and contextual sound. Qualify articulation, lexical grounding, syntax and spontaneous use separately. If a link is absent, name it; do not insert a pronunciation dictionary, TTS, chosen word or spectral answer selector.

| Gate | Required evidence |
|---|---|
| Unit | Prove actual motor-to-pressure/self-hearing and negative controls without supplied answers being scored as learned behavior. |
| Module | Trace complete experience→retained state→later preparation→body→pressure→self/world return on the exact current state. |
| System | Demonstrate independently identifiable acquired articulation, then grounded words/relations and autonomous contextual use with pre-learning/severed controls. |
| Release | Keep speech unqualified until exact preserved-release evidence passes; neither guaranteed emergence nor permanent impossibility is established. |

Actions: A01, A03, A06, A09, A10, A13, A16, A17. Sources: [TS03 line214](sources/task1606-boundary/TS03--guala_functional64_loop.py#L214), [TS03 line253](sources/task1606-boundary/TS03--guala_functional64_loop.py#L253), [TS03 line193](sources/task1606-boundary/TS03--guala_functional64_loop.py#L193).

## TSR06 — The stated IP-history capacity is not enforced before insertion

**source_confirmed_resource_admission_defect.** OccurrenceRateLimiter uses defaultdict access and appends the new IP timestamp before checking its4096-entry ceiling. For a newly inserted, nonstale IP, the later condition client_ip not in self._history is false; repeated fresh authenticated IPs can exceed the declared map capacity. The comment says mailbox capacity1 while the current default mailbox is4.

Evidence limit: This is a source-level counterexample, not an executed flood or proven cause of the current single-thread CPU symptom. Authentication happens before this limiter. Transport admission is not inherently a cognitive heuristic; its independently specified resource purpose and correct bound matter.

Remedy: Enforce unique-key capacity before allocation/insertion after defined stale-entry collection, and keep existing-key admission separate. Reconcile actual mailbox and ingress contract. Do not solve resource protection by altering sensory meaning or hidden selection.

| Gate | Required evidence |
|---|---|
| Unit | Test the4095/4096/4097 fresh-key boundary, existing active keys, expiry and authentication ordering with a bounded test. |
| Module | Verify ingress memory and actor mailbox stay within their stated bounds under admitted concurrency. |
| System | Measure ordinary authenticated continuous sensory delivery without hidden dropped context. |
| Release | Publish actual transport configuration and measured resource bounds; no claimed ceiling from an unreachable rejection branch. |

Actions: A01, A13, A14, A16, A17. Sources: [TS01 line78](sources/task1606-boundary/TS01--lean_production_app.py#L78), [TS01 line89](sources/task1606-boundary/TS01--lean_production_app.py#L89).

## TSR07 — Release declarations are not an exclusion or correctness certificate

**verified_artifact_identity_with_stale_unqualified_declarations.** Exact Task1606 image contains a release manifest labeled task1599 with timestamp04:36:18, while Docker labels still name September23/revision702be702e. The manifest wheel sha a9c7d9ac matches the local wheel; its extracted native sha4c7c1811 matches both cached image and live mapped library. The inspected Rust/Python source hashes match the manifest. It nevertheless declares heuristics=false/tabular_rl=false and an obsolete direct column40/41 MoveCommand description without supplying qualification evidence.

Evidence limit: Strong byte identity is genuine progress and distinct from a stale human release label. A file manifest cannot prove its source was compiled into a wheel without build provenance; a hardcoded compliance boolean cannot certify mechanism exclusion or whole-chain behavior. This audit did not independently rebuild the wheel or exhaustively scan the package.

Remedy: Generate identity and capability declarations from the actual immutable release closure and attach independent mechanism, state-preservation and ordered test evidence. Mark unqualified assertions explicitly. Preserve exact source/wheel/binary hashes while correcting stale task/config labels; do not use metadata to mask failed health or speech.

| Gate | Required evidence |
|---|---|
| Unit | Check declared task/config/source/library against actual artifacts; fail unsupported compliance assertions. |
| Module | Bind build inputs, toolchain, wheel, image, mounted modules, dependencies and configuration. |
| System | Qualify real preserved organism capabilities with independent outcomes, not embedded booleans. |
| Release | Require exact-release evidence for package ML exclusion, no heuristic cognitive authority, usable serving and learned speech separately. |

Actions: A01, A02, A03, A10, A15, A16, A17, A18. Sources: [TS01 line221](sources/task1606-boundary/TS01--lean_production_app.py#L221), [TS03 line254](sources/task1606-boundary/TS03--guala_functional64_loop.py#L254).

