> Historical Task1592 assessment, preserved as evidence. The current Task1593
> assessment is [A1 independent audit](GUALA_TASK1593_INDEPENDENT_AUDIT_2026-10-09.md)
> with the [updated registry](GUALA_LEARNING_DECISION_CLASSIFICATION_TASK1593_2026-10-09.json).
> Source improvements and remaining failures must be read in that release-specific scope.

# Guala learning and decision classification — Task 1592

**ML-free verdict: FAIL. Exhaustive mechanism clearance: NOT COMPLETE.**

This is the audit record required by Joe on October 8, 2026 (America/Chicago),
under `GUALA-REPAIR-EXECUTION-CONTRACT-2026-10-08`. It does not certify a repaired
organism. G1 owns implementation/deployment; A1 owns independent classification.

The deployed image inspected is
`sha256:7ca0cafb2c6fef1af1c4643ca7925c2881d62383d076c135490d28bdd99a616e`,
Task1592, rechecked at 2026-10-09T02:40:06Z. Shared workspace changes and proposed
Task1593 are not treated as this production artifact.

## Direct answer and correction

The assertion “no ML was used; only Python heuristics” is unsupported and incorrect
for this release. The actual action controller trains tabular action values from
experience. Its pipeline is `_settle` → `_credit` → `_choose`:

- `_settle` constructs a reward from intake, novelty, sound and comfort minus
  metabolic cost and pain.
- `_credit` accumulates action counts, total rewards and successor frequencies.
- `_choose` explores untried/less-tried actions, then maximizes the stored average
  reward plus 0.5 times the best estimated value in its most frequent successor.

That is a reinforcement-learning-type tabular policy. This statement identifies
the actual mechanism, not a claim that it implements textbook Q-learning. A fixed
algorithm can learn a policy deterministically. The “Zero ML” comment beside the
score calculation does not describe what the calculation does. The exact source
and previous live scored-action evidence establish this rejected authority.

Speech selection separately ranks stored acoustic examples and accumulated worth.
Other branches use authored priorities, semantic names and canned syllables. These
are separately classified; fixing one does not fix the others. A chooser receiving
one option is not intrinsically ML or a heuristic: upstream selection may already
have made the decision. Here the traced upstream rules and downstream learned
values establish the violation; changing the number of options is not its remedy.

[NIST's ML terminology](https://csrc.nist.gov/glossary/term/machine_learning) concerns
adaptation from data, not the presence of a particular programming library. The
classification here rests on the inspected code and retained-state decision reads.

## Additional confirmed finding V37: packaged ML model and inference code

The exact image contains `/app/dsf_ai_service/models/yolov8n.onnx`: 12,851,097 bytes,
SHA256 `f63fb6402b62f71f218d3be38cdc48ed1e5520f27948d3ca86149a427e9dd7d3`.
Read-only protobuf inspection found producer `pytorch` version `2.12.1`, one graph,
144 parameter initializers, 64 convolution operations, and other neural-network
operations. This is model presence, not merely a suspicious filename.

The packaged `speech_transducer.py` also constructs `faster_whisper.WhisperModel`
and performs speech-to-text inference. Legacy `app.py` calls it; the conservative
closure of the current `lean_production_app` entry does not include it. The image's
37 installed distributions do not include faster-whisper, CTranslate2, ONNX Runtime,
OpenCV or PyTorch. No YOLO loader was found in the 520 exported Python modules.
**Live YOLO/Whisper inference has not been established.** Native and external-process
closure is incomplete, so those negative searches cannot prove universal absence.
The artifact nevertheless cannot be described as containing no ML assets/code.

Required correction: remove obsolete model assets/inference routes from the next
release closure, audit inherited image contents, and demonstrate actual loader/
process exclusion. Preserve all organism history. A requirements-file edit alone
is insufficient. V37 is one additional package-exclusion obligation; it does not
turn the prior36 findings into37 observed production incidents.

The prior542-file export covered selected source/static/native files, not every
artifact file. This broader inspection scanned7,562 files under `/app` and Python
site-packages. It found the model outside that prior selected export. Neither
export is an exhaustive semantic review of the operating system or native binary.

## Coverage and classification register

The machine register has46 records: the36 prior correction boundaries,8 additional
algorithm/artifact classifications, and2 explicit unresolved closure boundaries.
These are **not46 completely verified learning mechanisms** and not46 heuristics.
The parser inventory includes520 Python modules and10,723 function/method symbols;
143 modules are in the conservative entry import closure. Counting symbols or
matching a finding's line range does not classify all code inside a function.
Remaining semantic review, dynamic routes, native provenance and external-process
binding are explicitly unresolved. No unreviewed route is treated as ML-free.

Every record in the [JSON register](GUALA_LEARNING_DECISION_CLASSIFICATION_2026-10-08.json)
has exact source/evidence hashes and ranges, algorithm classes, disposition, scope,
observed mechanism, required replacement, unit/module/system falsifiers, limits,
and G1/A1 ownership. All organism qualification remains `not_passed`.

| Record | Mechanism/boundary | Algorithm class | Disposition |
|---|---|---|---|
| M01 | Python chooses actions using priorities and accumulated scores | reward_learning, hand_authored_policy | forbidden |
| M02 | Speech selected by similarity and stored worth | reward_learning, example_matching | forbidden |
| M03 | Authored syllable chain presented as native syntax | hand_authored_policy | forbidden |
| M04 | Controller rewrites measured DSF pressure | field_projection, hand_authored_policy | forbidden |
| M05 | Only hunger delivered as a joint field | field_projection | forbidden |
| M06 | Food meaning comes from object names | hand_authored_policy | forbidden |
| M07 | Dream replay chosen by a score and boosted | hand_authored_policy | forbidden |
| M08 | DSF reduced to hash and situation keys for decisions | field_projection, example_matching | forbidden |
| M09 | Actual body and vocal consequences do not close the native loop | state_transport | defective |
| M10 | Native hand and jaw outputs are not applied | state_transport | defective |
| M11 | Sensory input is collapsed before native delivery | field_projection | forbidden |
| M12 | Sleep input uses the wrong scale | field_projection | defective |
| M13 | Skin coverage is passed as mechanical barrier stress | physical_model_unverified | defective |
| M14 | Parallel legacy substrates retain competing cognitive authority | physical_model_unverified | forbidden |
| M15 | A Python episode lookup can select learned continuation | example_matching | forbidden |
| M16 | Retention is decided by salience scores and count-based deletion | hand_authored_policy | forbidden |
| M17 | Sleep requests blanket contact decay and pruning | hand_authored_policy | forbidden |
| M18 | A causal memory input is absent from the checkpoint | state_transport | defective |
| M19 | Metabolic expenditure depends on action labels | hand_authored_policy | forbidden |
| M20 | Unseen world records steer perception and navigation | hand_authored_policy | forbidden |
| M21 | Observation reports fabricated zeroes and unsupported interpretations | state_transport | defective |
| M22 | Lifetime movement and handling counters increment twice | state_transport | defective |
| M23 | Discarded camera frames receive successful settlement results | state_transport | defective |
| M24 | Audio and video are joined without clock alignment | state_transport | defective |
| M25 | Ingress bookkeeping has no complete hard bound | state_transport | defective |
| M26 | Unattended operation repeatedly executes the whole Python loop | state_transport | defective |
| M27 | Memory admission models a different runtime representation | state_transport | defective |
| M28 | Sensory mutation authentication fails open | state_transport | defective |
| M29 | Native installation failure is caught and serving continues | state_transport | defective |
| M30 | The cutover record lacks the behavioral acceptance gate | state_transport | defective |
| M31 | Release labels do not prove native source custody | state_transport | defective |
| M32 | Loom Scan still observes a retired architecture | state_transport | defective |
| M33 | Caregiver body transport jumps directly to a destination | state_transport | defective |
| M34 | Caregiver can relocate a stroller by direct world replacement | state_transport | defective |
| M35 | Guided vocal work can be accepted without being applied | state_transport | defective |
| M36 | Swallowed material above reserve space is discarded from the body account | state_transport | defective |
| M37 | Packaged YOLO ONNX neural-network asset | ml_model_asset | forbidden |
| M38 | Packaged Whisper speech recognition implementation | ml_inference_code | forbidden |
| M39 | Native intra-column associative conductance parameter update | associative_parameter_update | unverified |
| M40 | Native activation, fixed feedforward coupling and spatial trace policy | hand_authored_policy, physical_model_unverified | unverified |
| M41 | Cochlear receptor signal transduction | deterministic_transduction | unverified |
| M42 | Airway waveform generation from supplied drive | deterministic_transduction | unverified |
| M43 | Canonical L0-L4 kernel | canonical_kernel | unchanged_not_recertified |
| M44 | External caretaker waveform teaching source | deterministic_transduction | unverified |
| M45 | Unbound native exports and remaining adaptation mechanisms | unknown | unverified |
| M46 | Remaining Python, dynamic-load and live-process closure | unknown | unverified |

## Required correction and evidence

The recommended single implementation boundary remains the existing64-column
sensory → native settlement → independent motor/jaw/articulation → real world
consequence → sensory return → canonical retained-state path. Remove competing
reward-table, example-lookup and authored-policy authority. Preserve historical
records without allowing them to decide behavior. No memory reset, expanded
physiology model, kernel change, score retuning or canned speech is authorized.

Declared native source also contains coactivity-target parameter updates:
`target = pre * post`, `sigma = resource * (target - g)`, then movement of `g` toward
the target beyond a threshold. This is classified as associative parameter
adaptation, with physical validity unverified. Its material interpretation requires
ratified units/derivation and exact source-to-binary binding. Calling a number
“stress” does not establish those facts. The live binary matches the preserved
wheel; a complete frozen native build attestation is still required from G1.

The mandatory [mechanism contract](GUALA_LEARNING_DECISION_MECHANISM_CONTRACT_2026-10-08.md)
now specifies Joe's ordered workflow, full per-mechanism record, unknown/failure
rules, native and external closure, preservation requirements and claim scope.
`AGENTS.md`, `guala-project-truth`, `guala-cognitive-development`, and
`guala-production-deploy` have been updated to require it. Existing content was
preserved by checked full-file replacement. The shared ledger remains the one
coordination/status record.

G1's reported19 passing regression tests have been acknowledged, not independently
adopted as compliance proof. They do not supply the missing per-mechanism or complete
system evidence. Seven fields per source is not seven sources; refusal cannot be
silently substituted for mechanical stress; quiet-gap timing is not learned vocal
causation. These corrections are recorded for G1.

## Verification limits and receipts

The auditor integrity checker validates reference hashes/ranges, all frozen Python
file/symbol inventory entries, mechanism obligations and lifecycle completeness.
It never imports the organism and cannot issue an ML-free certificate. Its own
unit and module tests are auditor-tool evidence only. Current compliant-organism
unit, module, system, rehearsal and live receipts remain absent from this register.
No production replay, build, cutover, history mutation or product-code edit was
performed for this classification.

Release-controller invocation of the new contract is not verified. G1 must wire
and prove that refusal before a subsequent deployment; writing this specification
or passing its data checks does not implement the product repair. Complete active
classification remains open until every native/dynamic/external boundary has a
source-bound disposition and causal evidence.

Evidence is preserved in
`backups/runtime/a1-ml-classification-20261008/`: production-baseline.json,
dependency-census.json, onnx-model-custody.json, source-symbol-inventory.json,
skill-and-agents-updates.json and validation receipts. The original36 findings
and their remedies remain in the [prior audit](GUALA_TASK1592_VIOLATION_REMEDIATION_AUDIT_2026-10-08.md).
The preexisting shared DARPA dossier was observed empty (0 bytes); it was not edited
or used as evidence of current claim wording. This new report is the claim record.

Safe present-tense project statement: “The requested architecture excludes ML and
heuristic decision authority. The currently deployed Task1592 does not meet that
requirement. Tabular reward-based control and prohibited lookup/rule mechanisms
are confirmed; a neural model and legacy inference code are also packaged. Full
native and external closure and compliant system acceptance remain unverified.”
