# Aurelion speech, ML, sensory and retained-memory reconciliation

**Overall reconciliation OPEN. No speech, system or ML-free certificate.** 22 fully read per-file working captures of historical Aurelion code/configuration/README/report files. Three byte-identical config/README corpus pairs gain content coverage;19 working-source reads remain separate. Not a coherent release, all-version/transitive closure or execution proof. Two historical JSON blobs are structurally traversed but not declared fully semantically read.

[Structured evidence](aurelion-content-reconciliation.json), [mechanisms](mechanisms_aurelion_content.json), [repair actions](remediation-plan.md), [speech decision](speech-decision-record.md). No product program or tests ran in this review.

## ACR01 — Pretrained semantic encoder and statistical fallback

**implemented_ML_and_statistical_proxy.** AC01 constructs SentenceTransformer/all-MiniLM-L6-v2 and otherwise sklearn TF-IDF; AC02 directly constructs the pretrained sentence model and clusters normalized embeddings. AC18 explicitly instructs installing sentence-transformers and scikit-learn. These are actual ML implementations, regardless of the names field, resonance or mosaic.

Evidence limit: Presence and intended callers are established. Successful historical model execution, present package contents and current native serving invocation are not independently established by these captures. A statement that this repository contains no ML is false; a statement that ML was never executed is unverified.

Remedy: Exclude these competing semantic authorities from the pupil and every release dependency. Preserve historical evidence separately. Recover actual dependency/build/import/invocation records; do not substitute TF-IDF, a hand dictionary or another model as the native cognition repair.

| Gate | Required evidence |
|---|---|
| Unit | Classify exact dependencies, model files and fallback branches by content and behavior, not naming. |
| Module | Trace every reachable constructor/call and packaged artifact on the frozen candidate, including dynamic routes. |
| System | With external text/meaning withheld, prove authentic sensory retention and later native causal use; no model or statistical text proxy may supply the answer. |
| Release | Certify only the named artifact/configuration after independent source, binary, dependency and live-route closure. |

Actions: A01, A02, A05, A10, A15, A16, A17. Sources: [AC01 line13](sources/aurelion-content/AC01--embeddings.py#L13), [AC01 line22](sources/aurelion-content/AC01--embeddings.py#L22), [AC02 line7](sources/aurelion-content/AC02--semantic_mosaic.py#L7), [AC18 line19](sources/aurelion-content/AC18--README_v36.txt#L19).

## ACR02 — Optional LLM bridge and authored default response

**implemented_LLM_route_and_canned_fallback.** AC03 implements Ollama HTTP generation and GPT4All generation; its none backend returns an authored learning-themed reply. AC13 chat calls bridge.reply and permits a backend CLI override. AC16 config defaults backend to none, while AC17 advertises the optional LLM bridge.

Evidence limit: Default none is evidence of this file value, not proof of effective runtime configuration or exclusion. The CLI computes a model variable but does not pass that variable into the bridge. This is neither native articulation nor a verified live route.

Remedy: Retire the LLM and canned-reply routes from pupil speech authority. Keep external tutor identity/provenance separate if an authorized tutor exists. Bind all effective CLI/config/environment values and show their actual consumers.

| Gate | Required evidence |
|---|---|
| Unit | Prove no approved pupil output path can select the none template, Ollama or GPT4All branch. |
| Module | Resolve CLI/config precedence and exact consumers; detect unused controls and imported backends. |
| System | Demonstrate body-generated acoustics from native state with no external response substitution. |
| Release | Close all shipped and external generation routes on the exact candidate; a disabled default alone cannot pass exclusion. |

Actions: A02, A05, A10, A12, A13, A15. Sources: [AC03 line10](sources/aurelion-content/AC03--bridge_llm.py#L10), [AC13 line81](sources/aurelion-content/AC13--bridge_cli.py#L81), [AC13 line33](sources/aurelion-content/AC13--bridge_cli.py#L33), [AC16 line24](sources/aurelion-content/AC16--config.json#L24), [AC17 line7](sources/aurelion-content/AC17--README.txt#L7).

## ACR03 — Text-derived random vectors masquerading as multiple senses

**synthetic_multisensory_substitution.** AC07 hashes text into random visual/auditory/smell/taste/touch vectors and uses authored positive/negative words for emotion. AC12 generates all seven modalities from the same text hash. These functions label text-derived numbers as sensory experiences without corresponding external or internal physical events.

Evidence limit: Hash seeding is not proof of cross-process determinism; seed configuration was not recovered. Even repeatable vectors would not make them genuine sensory measurements. External text stimulus is permissible only through its actual specified sensing boundary.

Remedy: Replace these authorities with measured external signals and actual body/internal state through ratified transduction, keeping occurrence time, context and provenance. Do not pad missing experiences with invented modalities.

| Gate | Required evidence |
|---|---|
| Unit | For each channel prove a change is caused only by its physical input and derived transducer law. |
| Module | Verify time-aligned genuine multimodal occurrences and explicit missing-channel handling; no token-to-sense synthesis. |
| System | Show later behavior depends on retained authentic co-experience, including negative controls with missing or rearranged physical context. |
| Release | Audit every input producer and restore route; preserve contaminated historical artifacts without treating them as acquired native experience. |

Actions: A03, A05, A06, A09, A10. Sources: [AC07 line24](sources/aurelion-content/AC07--primitive_sensory_pack.py#L24), [AC07 line49](sources/aurelion-content/AC07--primitive_sensory_pack.py#L49), [AC12 line53](sources/aurelion-content/AC12--morphospace_multimodal.py#L53), [AC12 line51](sources/aurelion-content/AC12--morphospace_multimodal.py#L51).

## ACR04 — Scalar coherence, entropy and synthetic energy drive decisions

**reduced_statistical_authority_not_DSF.** AC02 derives phi from average within-cluster cosine similarity, H from cluster-label frequencies and energy=phi*exp(-H/10). AC14/15 pass those three scalars into intent.decide. AC06 adjusts alpha with sensitivity0.35 times phi drift and clips it to0.25..0.85. AC12 smooths and pads/truncates modality vectors.

Evidence limit: These are reduced text/cluster proxies, not evaluation of the joint D,M,R,U,C,P,B field and global S(UF), physical work or yield-state dynamics. Full field relationships, temporal cause, units and body/context lineage are absent from the inspected authority. Same Greek symbols do not establish equivalence.

Remedy: Remove the scalar proxy as cognitive authority. Require the authorized full-field and contact/state dynamics with explicit units, conservation/accounting and bounded execution. Keep descriptive observer statistics separate and read-only.

| Gate | Required evidence |
|---|---|
| Unit | Verify complete field delivery, units and exact derived transition predicates without statistical or smoothing substitution. |
| Module | Prove observer summaries cannot feed selection or native-state mutation. |
| System | Preserved-state controlled sensory interventions must change native state and behavior through the full authorized causal path. |
| Release | Bind native laws, compiled implementation and effective values; unproved equivalence remains failed or unimplemented. |

Actions: A04, A05, A11, A14, A16. Sources: [AC02 line52](sources/aurelion-content/AC02--semantic_mosaic.py#L52), [AC02 line66](sources/aurelion-content/AC02--semantic_mosaic.py#L66), [AC14 line63](sources/aurelion-content/AC14--aurelion_core_v36.py#L63), [AC06 line46](sources/aurelion-content/AC06--learning_harness_adaptive.py#L46), [AC12 line23](sources/aurelion-content/AC12--morphospace_multimodal.py#L23).

## ACR05 — Authored speech templates and arbitrary word-vector retrieval

**heuristic_speech_authority.** AC08 assigns random128-dimensional vectors to tokens, averages text, ranks cosine neighbors, takes token prefixes and selects one of five authored templates using random.choice. AC09 combines cleaned tokens, top modality norms, supplied intent labels and fixed question/reply templates; learner and conversational context arguments do not drive its reply formation.

Evidence limit: No external model in a responder does not imply no heuristic. The10**9 expression is a hash-seed modulus, not a physical energy/work multiplier. Current invocation is not established.

Remedy: Retire these fabricated pupil utterances. Required speech must be produced by retained native state through motor/respiratory/acoustic dynamics and authentic self-hearing; expose unavailable language honestly until verified.

| Gate | Required evidence |
|---|---|
| Unit | Trace each speech-producing branch and reject authored pupil replies, word ranking and random template selection. |
| Module | Prove vocal state/airflow/body work produce the recorded signal and retained state causally affects it. |
| System | Test blinded intelligibility and learned contextual use separately from nonzero or different sounds, with preserved-state matched controls. |
| Release | The served audio and labels must have complete native provenance; no fallback may manufacture a passed capability. |

Actions: A05, A10, A13, A16. Sources: [AC08 line43](sources/aurelion-content/AC08--language_bridge.py#L43), [AC08 line19](sources/aurelion-content/AC08--language_bridge.py#L19), [AC09 line46](sources/aurelion-content/AC09--proto_responder.py#L46), [AC09 line20](sources/aurelion-content/AC09--proto_responder.py#L20).

## ACR06 — Token averages and schema inversion are not episodic neuronal memory

**flattened_memory_and_unvalidated_schema.** AC04 stores token→modality→vector, half-blends each update and averages recalled tokens, losing ordering and occurrence relations. AC10 instead stores modality→token→vector with fixed0.9/0.1 updates. AC04 accepts loaded JSON without validating this distinction and labels len(root) learned tokens. AC07 supplies six senses although its DIMS includes lexical, while AC04 indexes every DIMS entry.

Evidence limit: The two large recovered snapshots use the modality-first shape and heterogeneous dimensions8/6/4/16; current AC07 declares all seven dimensions8. Neither successful JSON parsing nor those dictionaries establishes a native formation, episode, sleep consolidation or lossless migration. Exact original producer remains unverified.

Remedy: Preserve artifacts and fail incompatible schemas explicitly. Recover original producers and physical state lineage before any migration. Retained native causal relationships must carry actual multimodal context and body state; never repair a schema by invented vectors or relabelled counts.

| Gate | Required evidence |
|---|---|
| Unit | Validate versioned schema, dimensions, provenance and exact state custody; missing channels and incompatible shape must remain visible failures. |
| Module | Demonstrate sanctioned lossless persistence/restore of native causal state, with no dictionary-to-neuron invention. |
| System | Show recall and later action distinguish experience order and context and survive lawful sleep/restart. |
| Release | No migration or preservation claim without before/after physical-state mapping and independent evidence; no reset for demonstration convenience. |

Actions: A03, A06, A09, A10, A16. Sources: [AC04 line17](sources/aurelion-content/AC04--language_field.py#L17), [AC04 line38](sources/aurelion-content/AC04--language_field.py#L38), [AC04 line43](sources/aurelion-content/AC04--language_field.py#L43), [AC10 line10](sources/aurelion-content/AC10--intent_field.py#L10), [AC07 line6](sources/aurelion-content/AC07--primitive_sensory_pack.py#L6).

## ACR07 — Recovered vector artifacts do not establish retained experience

**artifact_structure_and_provenance_gap.** Independent complete JSON structural traversal found6994 token keys in each of six modalities in the first snapshot, with lexical empty; the second has8031 keys in each of seven modalities. Across the six shared modalities1217 keys disappear and2254 appear. The second has auditory4457/8031 and smell7870/8031 all-zero vectors. Both contain finite numeric vectors and no duplicate object keys.

Evidence limit: The structural receipt checks all values but is not a complete semantic content reconciliation or authentication of a historical run. Filenames say20251109; observed Git recovery imports are June3 and August5 2026, which do not prove original creation dates. Causes of differences and whether these were consecutive states are unknown.

Remedy: Keep both original blobs, hashes and source paths. Recover run manifest, producer, inputs, transition and intended schema. Do not claim vocabulary growth, preserved memory, causative loss or native learning from file size and key counts alone.

| Gate | Required evidence |
|---|---|
| Unit | Recheck hashes, schema, cardinalities, dimension distributions and exact key-set differences without importing product code. |
| Module | Recover matching producer/config/input identities and actual persistence transition, including deletion/decay explanations. |
| System | A preserved-state learning claim requires native causal lineage and retained behavioral use, not an expanding dictionary. |
| Release | Leave history continuity unqualified until original artifacts and transition proof are independently bound to the candidate. |

Actions: A01, A03, A09, A16, A18. Sources: [AC04 line12](sources/aurelion-content/AC04--language_field.py#L12), [AC10 line10](sources/aurelion-content/AC10--intent_field.py#L10).

## ACR08 — Named runners and learning harnesses have incompatible interfaces

**source_coherence_failure.** Under the audit environment Python3.11.15, AC14 line51 and AC15 line46 fail parsing because of backslashes in f-string expressions. Both import IntentField, absent from inspected AC10. AC05 imports MultimodalField/Mosaic/SemanticHub, absent from AC12. AC06 reads phi/energy absent from its inspected MorphospaceMultimodal. AC05/06 call learner.save, absent from inspected AC04.

Evidence limit: These are static failures of this captured file set; no product program ran. A different historical interpreter/import path may differ. This does not prove the archived CSV outputs were fabricated, nor that current Guala imports these runners.

Remedy: Recover a coherent original candidate and dependency/interpreter manifest before accepting old run claims. Do not mend these incompatible ML/heuristic programs and present that as ArcLoom remediation. The replacement qualification must exercise actual approved native interfaces.

| Gate | Required evidence |
|---|---|
| Unit | Check syntax for the declared interpreter and the complete required interface against the exact candidate. |
| Module | Close module resolution and caller/callee contracts; retain missing-boundary failures. |
| System | Only a coherent preserved candidate with causal sensory behavior can support whole-system evidence. |
| Release | No report from an unidentified version can certify the present release; keep historical claims and independent reproductions distinct. |

Actions: A01, A02, A15, A16, A18. Sources: [AC14 line7](sources/aurelion-content/AC14--aurelion_core_v36.py#L7), [AC15 line7](sources/aurelion-content/AC15--aurelion_core_v35.py#L7), [AC05 line18](sources/aurelion-content/AC05--learning_harness.py#L18), [AC06 line40](sources/aurelion-content/AC06--learning_harness_adaptive.py#L40), [AC06 line55](sources/aurelion-content/AC06--learning_harness_adaptive.py#L55).

## ACR09 — Claimed prototype growth is disconnected from the supplied payload

**heuristic_prototype_memory_and_missing_consumer.** AC18 advertises persistent prototypes, warm-start attraction and mosaic growth. AC19 merges prototypes by Jaccard token overlap>=0.5, retains at most16 tokens, averages phi and ranks phi/count seeds. AC14 calls add_meta_mosaics only when payload.meta_mosaics exists, but AC02 returns sentences/labels/centroids/embedder and no meta_mosaics. Its --seed threshold is parsed but unused. The v36 CSV has GROW labels with empty token/meta-token columns.

Evidence limit: A GROW label is not evidence that prototypes were created, let alone neuronal growth. The supplied caller/payload mismatch is direct source evidence; the CSV is an unauthenticated historical report. The CLI JSON serialization also includes a live model object, whose serialization is not supplied.

Remedy: Retract growth/consolidation equivalence for this route. Preserve the evidence and trace authentic native formation changes separately; use structural identities and derived relationships rather than token overlap, scalar ranking or labels as proof.

| Gate | Required evidence |
|---|---|
| Unit | Verify actual payload contracts and every claimed output/state mutation; labels alone cannot satisfy growth predicates. |
| Module | Require complete causative formation membership, contact changes and persistence; compare before/after state. |
| System | Demonstrate learned reuse across genuine contexts and sleep without token-centroid or canned decision authority. |
| Release | Qualify the actual physical formation path in the shipped candidate, with independent evidence of both changed state and changed causal use. |

Actions: A05, A09, A10, A16. Sources: [AC18 line7](sources/aurelion-content/AC18--README_v36.txt#L7), [AC19 line63](sources/aurelion-content/AC19--mosaic_memory.py#L63), [AC19 line41](sources/aurelion-content/AC19--mosaic_memory.py#L41), [AC14 line70](sources/aurelion-content/AC14--aurelion_core_v36.py#L70), [AC14 line74](sources/aurelion-content/AC14--aurelion_core_v36.py#L74), [AC02 line98](sources/aurelion-content/AC02--semantic_mosaic.py#L98), [AC22 line2](sources/aurelion-content/AC22--cognition_semantic_v36_20251109_054446.csv#L2).

## ACR10 — Bounded lists hide unbounded logs and lossy recovery

**resource_and_persistence_claim_gap.** AC20 bounds in-memory short/mid/long lists but appends each event to three on-disk logs indefinitely; restore reads each complete file before trimming and skips malformed entries. Its aggregate snapshots use wall-clock half-life weighting. AC19 silently skips malformed prototype rows and rewrites a truncated JSONL store. AC11 uses regex to salvage fragments from a corrupt backup and writes a replacement sidecar.

Evidence limit: Finite list lengths do not establish bounded disk, bounded load-time memory or lossless recovery. These are historical utilities, not proved current native checkpoint readers. Calendar decay and aggregate statistics are not automatically physical sleep or memory.

Remedy: Use the canonical bounded native persistence/state accounting and explicit corruption failure. Preserve damaged evidence; any approved recovery must enumerate exact retained/lost state and prove lawful continuity. No silent dropping, sidecar substitution or wall-clock heuristic as pupil authority.

| Gate | Required evidence |
|---|---|
| Unit | Measure worst-case state/storage/load bounds and validate every record/version; corrupt or incomplete state must fail visibly. |
| Module | Exercise canonical checkpoint atomicity and exact cold restore with causative state retained. |
| System | Verify bounded unattended behavior including disk and restore cost, while actual learned causal effects persist. |
| Release | Bind deployed writers/readers and recovery procedures; a list cap cannot qualify the whole runtime. |

Actions: A03, A09, A14, A16, A17. Sources: [AC20 line29](sources/aurelion-content/AC20--memory_ring.py#L29), [AC20 line47](sources/aurelion-content/AC20--memory_ring.py#L47), [AC20 line58](sources/aurelion-content/AC20--memory_ring.py#L58), [AC19 line19](sources/aurelion-content/AC19--mosaic_memory.py#L19), [AC11 line5](sources/aurelion-content/AC11--repair_language_memory.py#L5).

## ACR11 — Embeddings, TSNE plots and historical CSVs are distinct evidence classes

**scientific_and_learning_claim_scope.** AC05 creates a TSNE plot of concatenated stored modality vectors. AC21 reports EXPLORE using phi0.194..0.366; AC22 reports GROW using phi0.637..0.748. README installation instructions and those report rows do not show the actual invoked model or native learning. Textbooks and corpora are external materials, not active architectural authority by presence.

Evidence limit: TSNE is a statistical visualization and its presence alone does not establish current cognitive ML authority. In contrast AC02 uses pretrained embeddings for its semantic mechanism. Neither plot appearance nor a larger scalar implies intelligence, native plasticity, speech or full-field conformance.

Remedy: Keep observer/external content, executed cognitive authority and mere packaged evidence separately classified. Recover actual report provenance; replace self-labelled learning success with predeclared causal physical predicates.

| Gate | Required evidence |
|---|---|
| Unit | Label every evidence item as source, historical report, independent execution or current live proof. |
| Module | Trace whether each derived quantity or external content can mutate/select native state or remains read-only observation. |
| System | Measure acquired capability with matched sensory/context controls and independently assessed speech, not plots or self-reported intent labels. |
| Release | No broad no-ML or learned-speech claim without exact scope and complete executable/package/runtime evidence. |

Actions: A01, A10, A13, A15, A16, A18. Sources: [AC05 line39](sources/aurelion-content/AC05--learning_harness.py#L39), [AC21 line2](sources/aurelion-content/AC21--cognition_semantic_20251109_050648.csv#L2), [AC22 line2](sources/aurelion-content/AC22--cognition_semantic_v36_20251109_054446.csv#L2), [AC17 line55](sources/aurelion-content/AC17--README.txt#L55).

## ACR12 — Literal caller search cannot certify current exclusion

**current_activation_not_established.** A corrected bounded search for Aurelion/all-MiniLM/semantic_mosaic/LLMBridge/language_field across dsf_ai_service,native,tests,tools Python/Rust/TOML files found only two Aurelion decay-rate comments in v4 engines. This narrows the observed references but does not close imports, aliases, generated/native binaries, alternate roots, image contents or external service calls.

Evidence limit: No current serving refresh, model inference probe or import tracing was performed. Previous independently captured Task1598 Whisper/YOLO/controller findings remain separately authoritative. Present source presence and historical CSVs must not be mislabeled as current execution.

Remedy: G1 must supply the frozen source/build/image/configuration and effective process dependency closure. A1 independently verifies the actual native speech chain and every prohibited competing route, preserving failure evidence.

| Gate | Required evidence |
|---|---|
| Unit | Enumerate actual entries, imports, build manifests, assets and externally resolved backends by content. |
| Module | Trace every speech-producing and semantic input route with verified owner/consumer boundaries. |
| System | Observe the preserved live candidate under authentic sensory challenge and normal caretaker/environment load. |
| Release | Issue only scoped claims tied to verified image/config/state and fresh live evidence; unknown routes remain open. |

Actions: A02, A05, A15, A16, A17. Sources: [AC13 line3](sources/aurelion-content/AC13--bridge_cli.py#L3), [AC14 line6](sources/aurelion-content/AC14--aurelion_core_v36.py#L6).

