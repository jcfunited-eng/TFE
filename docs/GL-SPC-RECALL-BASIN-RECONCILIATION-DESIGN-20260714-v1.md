# GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1

**doc_id:** GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1
**Date:** 2026-07-14 UTC
**Status:** `proposed_pending_ratification` — design only. No code written, nothing deployed. Implementation is a separate, later dispatch once this design is reviewed.
**Governing spec:** `docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md` (§9.5, §9.6, §12 Step 5, §13.3).
**Owner decision this answers:** *"Build real recall of freshly-learned content BEFORE wiring the engine into the live app"* (the silence-only-first option was explicitly rejected).
**Scope:** The recall-of-freshly-learned-content architecture only. It does not change field physics, the commit conjunction, recognition, or the transaction contract.

---

## 1. Plain-language outcome

Steps 1–6 built a real conversation engine (`ProductionCleanConversationEngine`) that can sense a turn, recognize it, commit it, and learn a coexperienced scalar. What it cannot yet do is **say a learned scalar back on a later turn**, because the piece that turns a learned binding into speech — fresh full-field recall — has no working path from the engine's learned state into the archive it must resolve against.

This document specifies that path. The recommended design **recalls a learned scene by deterministically re-running the engine's own six-lane turn-construction for that scene**, with a self-generated-recall origin, producing a genuine fresh full-field commit for every recalled scalar. It does **not** route through the existing five-sense `story_native_replay` / `create_recall_story_episode` / `fresh_recall_executor` archive — because three independently code-confirmed facts (§3) prove that stack can never key on, or recognize, a scalar this engine actually learns.

Everything new lands in new files. Two already-committed files (`clean_conversation_engine.py`, `production_runtime_bootstrap.py`) receive small, named, load-bearing edits (§7). No physics file is touched.

---

## 2. The decision, up front

- **Chosen: Direction C** — a new, isolated *coexperienced-scene deterministic-replay recall* subsystem (§6).
- **Rejected: Direction A** (teach `story_native_replay.py` time-varying evidence) — deep surgery to a physics file relied on for counterfactual replay, and it does **not** remove the real blocker (§4).
- **Rejected: literal Direction B** (feed the real turn's evidence into `create_recall_story_episode`) — `create_recall_story_episode` produces a *five-sense* episode whose evidence receipts can never equal the *six-lane* receipts a learned binding carries (§3.1), so the archive it builds is structurally unresolvable by a real binding (§4).

Direction C is a *synthesis* the task invited: it keeps the five-sense recall stack untouched (it remains valid for its own counterfactual-replay purpose) and builds the freshly-learned-content path natively in the six-lane universe the engine already commits and learns in.

---

## 3. Verified findings (cited directly; not re-diagnosed)

These were checked by reading the code, not carried over. Each is the load-bearing basis for a design choice below.

### 3.1 Per-port evidence receipts embed the *whole-preparation* S_UF/R_UF digest → five-sense and six-lane sensory receipts can never coincide

`closed_experience.prepare_closed_experience_evidence` computes **one** support-floor digest and **one** resonance digest for the entire preparation (`closed_experience.py:1013–1034`: `support = compute_support_floor(ordered_streams, …)`, `support_digest = receipt_sha256(support_payload)`; likewise `resonance_digest`). Every port's `PortTransportEvidence` then stamps that *same* prep-wide `support_digest` / `resonance_digest` into its `SupportFloorFact` / `ResonanceFact` (`closed_experience.py:1078–1087`), and `field.transport_evidence_receipt_payload` folds both authority receipts into the port's `evidence_receipt_sha256` (`field.py:313–329`).

Consequence: a sense port's `evidence_receipt_sha256` depends on **which other lanes are in the preparation**. A five-sense preparation (5 streams) and a six-lane preparation (5 senses + language) produce **different** `support_digest` / `resonance_digest`, hence **different** per-port sensory evidence receipts, even for byte-identical underlying streams.

This is the exact root of the failure `real_end_to_end_recall_pipeline.py`'s own module docstring documents ("two disjoint five-sense sensory subsystems", `real_end_to_end_recall_pipeline.py:27–71`): a learned binding and a five-sense archive episode "can never carry the same `sensory_evidence_receipt_sha256s`."

### 3.2 A learned binding's `sensory_evidence_receipt_sha256s` are the *six-lane commit's* non-language receipts

`expression_learning._sensory_receipts(sealed)` = `sorted(evidence_receipt_sha256 for value in sealed.evidence if value.lane_id != "language")` (`expression_learning.py:149–158`). `sealed` is the committed **six-lane** closed experience, so these are the six-lane, non-language evidence receipts. They flow verbatim into `CommittedModeRelation` (`expression_learning.py:589, 612`), the `CommittedMotifEvent` (`expression_learning.py:967–968`), and the `MotifOutputBinding`.

### 3.3 The five-sense recall executor resolves the archive by exactly those binding receipts

`FreshRecallClosedExperienceExecutor.execute` begins with
`episode = self.archive.resolve(profile_binding_sha256=source_binding.profile_binding_sha256, sensory_evidence_receipt_sha256s=source_binding.sensory_evidence_receipt_sha256s)` (`fresh_recall_executor.py:901–906`), and `RecallStoryEpisodeArchive.resolve` keys on `(profile_binding_sha256, sorted(sensory_evidence_receipt_sha256s))` (`recall_story_episode_archive.py:728–754`). The archive's own key is built from `execution.preparation.evidence`, i.e. a **five-sense** preparation (`create_recall_story_episode` rejects any non-five-sense profile at `recall_story_episode_archive.py:499, 514–516`; the execution's preparation is five-sense-only, produced by `story_native_replay._execute_case` → `prepare_closed_experience_evidence(streams=<5 sense streams>, topology=<5-sense topology>)`).

Combining 3.1 + 3.2 + 3.3: the executor looks the archive up by *six-lane* receipts; the archive is keyed by *five-sense* receipts; §3.1 proves those two sets are disjoint. **`archive.resolve` therefore fails deterministically for any real learned binding.** `recall_reentry.RecallTransitionSettlement.verify` enforces the same equality from the other side (`recall_reentry.py:686`: `sensory_digests != source_binding.sensory_evidence_receipt_sha256s → ReceiptError`), so nothing downstream can paper over it either.

### 3.4 The five-sense recall stack also cannot *recognize* a real learned scene

`prepare_story_global_uf` recognizes every replay against `basin_profile.mode_bank` (`story_global_uf_basin.py:494` inside `_build_expression_facts`, called with `profile=basin_profile`). Every construction path mounts that bank as the **empty genesis bank** (`six_lane_runtime_mount.mount_expression_mode_bank` → `create_empty_expression_mode_bank`, rank 0). A real learned scene re-run through it returns `UNKNOWN`, which `_build_expression_facts` turns into `ReceiptError("story expression recognition is UNKNOWN")` (`story_global_uf_basin.py:500–501`). Recognition of a learned scene requires the **live, grown** mode bank the engine actually accumulated — a bank the frozen basin profile does not hold. This is a *second, independent* reason the five-sense stack cannot recall learned content, and it is decisive for the design: recall must recognize against the engine's live bank.

### 3.5 The engine never archives anything today

`ProductionCleanConversationEngine._archive` is constructed empty and `with_episode` is never called (`clean_conversation_engine.py:592–596`); `create_recall_story_episode` is not referenced anywhere in the engine or in `real_experience_learning_pipeline.py`. So even setting §3.1–3.4 aside, zero episodes exist to resolve. (This confirms the prior investigation's finding #4 mechanically.)

### 3.6 Problem #1's reconciled pre-window already exists inside the engine's runtime

`MountedSixLaneRuntime.pre_window_state` is built by `six_lane_runtime_mount.mount_pre_window_state` against a **real** `ExactFieldState` (zero-amplitude genesis) and the **real** `ExpressionModeBank` (`six_lane_runtime_mount.py:1292–1325`), and it passes `MountedStoryGlobalUFBasinProfile.verify`'s digest-identity checks (`story_global_uf_basin.py:334–341`). The engine already uses this reconciled pre-window for its L6 evaluation (`clean_conversation_engine.py:615–619`). The fabricated `_mount_simple_pre_window` (`real_experience_learning_pipeline.py:887–919`) is confined to the standalone Step-4 pipeline and is **not** on the engine's path. So **problem #1 is already solved on the engine's path**; the design does not need to re-solve it (see §8).

---

## 4. Why Direction A and literal Direction B are rejected

**Literal Direction B** (build a live-archival path that feeds `create_recall_story_episode` from real turn outputs) cannot work: `create_recall_story_episode` is hard-wired to a five-sense profile and a five-sense `StoryKernelReplayExecution.preparation` (`recall_story_episode_archive.py:480–516`). Any episode it produces is keyed by five-sense receipts, which §3.1 proves can never equal the six-lane receipts a real learned binding carries. The `live_boundary_episode_adapter.py` technique (minting a fresh single-point `StorySensorPortAuthority` per port) genuinely closes its own narrow `flux_for_code` exact-match gap, but it terminates inside the *five-sense* universe — it does not, and cannot, make a five-sense episode's receipts match a six-lane binding. So literal B reaches a dead end at the same wall §3 describes.

**Direction A** (teach `story_native_replay._execute_streams` to consume externally-supplied time-varying per-instant flux) is both dangerous and insufficient:

- *Dangerous:* `story_native_replay.py` is a core physics file whose constant-flux model is relied on for legitimate counterfactual replay — `enumerate_native_replay_cases` walks `flux_for_code(code ± 1)` to build `SENSOR_ADJACENT_CODE` counterfactuals (`story_native_replay.py:1290`), and the boundary schema records exactly one `signed_native_flux` per port (`story_native_replay.py:544`). A time-varying model has no meaning under `flux_for_code`, and reconstructing archived time-varying traces during recall would require baking the full per-instant flux sequence into the boundary/profile schema — a deep, schema-breaking change with real regression risk to the counterfactual path.
- *Insufficient:* even if built, Direction A still routes through `create_recall_story_episode` (five-sense) and `prepare_story_global_uf` (basin-empty-bank recognition), so it still hits §3.1 and §3.4. It changes a physics file and does not remove the blocker.

**Direction C** avoids both: it never touches `story_native_replay.py`, never builds a five-sense episode, and recognizes against the engine's live bank.

---

## 5. The core idea of Direction C

A learned scene is fully **deterministically reconstructable** from its turn identifier. The engine builds a turn's scene from `_scene_descriptors(task_id)` (a plain SHA-256 of `task_id`, `clean_conversation_engine.py:304–330`) plus the one input scalar `turn.text`, evolved through a freshly-mounted (hence deterministic) production chemistry runtime, over the engine's fixed `MountedSixLaneRuntime` authorities and fixed `physical_profile` receipt. The bootstrap comment already relies on this exact property (`production_runtime_bootstrap.py:431–443, 456–462`: *"a later real turn replaying the same `task_id`/`text` reconstructs this same scene bit-for-bit"*).

Therefore, to recall a learned scene it is sufficient to store `(task_id, text)` keyed by the learned binding's identity, and later **re-run the engine's own scene builder** for that `(task_id, text)`. The re-run reproduces the exact six-lane evidence — hence the exact six-lane sensory receipts the binding carries (§3.2) — so the mandatory settlement equality `sensory_digests == source_binding.sensory_evidence_receipt_sha256s` (`recall_reentry.py:686`) holds by construction. Recognition runs against the engine's **live grown bank** (§3.4), and commit is evaluated with a **`SELF_GENERATED_RECALL` origin and exact-zero fresh `R_event`** — the same self-recall discipline the existing executor uses (`fresh_recall_executor.py:760–810`), which yields a genuine fresh full-field commit receipt per recalled scalar, satisfying §12 Step 5 without any precomputed table.

The one non-negotiable coupling this creates: recall must read the engine's *current* mode bank and *current* scene archive at settle time. This is handled by one shared mutable holder (§6, `LiveRecallState`) that the engine updates each turn.

---

## 6. Exact new files and signatures

Three new modules under `dsf_ai_service/glew_runtime/`. All follow the package's established conventions (`_canonical_bytes`, digest-collision-safe registry extension, `.verify()` on every receipted value, HMAC-signed checkpoints mirroring `recall_story_episode_archive.py`'s format).

### 6.1 `coexperienced_scene_archive.py` — the six-lane-native archive

Stores, per learned scene, the binding identity plus the deterministic reconstruction key. Keyed exactly like the five-sense archive's `resolve` so it slots into the existing resolve contract, but keyed on the **six-lane** receipts a real binding carries.

```python
COEXPERIENCED_SCENE_EPISODE_SCHEMA = "glew.recall.coexperienced_scene_episode.v1"
COEXPERIENCED_SCENE_ARCHIVE_SCHEMA = "glew.recall.coexperienced_scene_archive.v1"
COEXPERIENCED_SCENE_ARCHIVE_CHECKPOINT_SCHEMA = "glew.recall.coexperienced_scene_archive_checkpoint.v1"

def coexperienced_scene_episode_receipt_payload(
    *,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],   # sorted; the binding's six-lane, non-language receipts
    coexperienced_scalar_text: str,                       # the one bound Unicode scalar (len == 1)
    scene_task_id: str,                                   # deterministic scene reconstruction id (== the learning turn's task_id)
    scene_language_text: str,                             # the scene's own input scalar (len == 1)
    engine_id: str,                                       # binds the scene to the engine identity that built physical_profile
) -> bytes: ...

@dataclass(frozen=True, slots=True)
class CoexperiencedSceneEpisode:
    profile_binding_sha256: str
    motif_receipt_sha256: str
    sensory_evidence_receipt_sha256s: tuple[str, ...]
    coexperienced_scalar_text: str
    scene_task_id: str
    scene_language_text: str
    engine_id: str
    episode_receipt_sha256: str
    episode_receipt_payload: bytes

    @property
    def resolution_key(self) -> tuple[str, tuple[str, ...]]:  # (profile_binding_sha256, sorted(sensory_evidence_receipt_sha256s))
        ...
    def verify(self) -> None: ...   # recomputes canonical bytes; asserts len(text)==1, sorted/distinct receipts

def create_coexperienced_scene_episode(
    *,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    coexperienced_scalar_text: str,
    scene_task_id: str,
    scene_language_text: str,
    engine_id: str,
) -> CoexperiencedSceneEpisode: ...

@dataclass(frozen=True, slots=True)
class CoexperiencedSceneArchive:
    episodes: tuple[CoexperiencedSceneEpisode, ...] = ()
    # __post_init__: canonical, unique-by-episode-receipt, unique-by-resolution_key (reject two scenes claiming one binding)
    def with_episode(self, episode: CoexperiencedSceneEpisode) -> "CoexperiencedSceneArchive": ...
    def resolve(
        self, *, profile_binding_sha256: str, sensory_evidence_receipt_sha256s: tuple[str, ...]
    ) -> CoexperiencedSceneEpisode: ...   # raises ReceiptError with the same "no episode has this exact ..." message shape on miss
    @property
    def receipt_sha256(self) -> str: ...

def coexperienced_scene_archive_checkpoint_payload(
    *, archive: CoexperiencedSceneArchive, checkpoint_id: str, authentication_key: bytes, key_id: str
) -> bytes: ...
def restore_coexperienced_scene_archive_checkpoint(
    *, checkpoint_payload: bytes, authentication_key: bytes, expected_key_id: str
) -> CoexperiencedSceneArchive: ...
```

Note: the episode deliberately stores **no field/evidence bytes** — only the reconstruction key and the binding identity. Recall regenerates the evidence bit-for-bit (§5) and *verifies* the regenerated receipts against the binding, so storing the evidence would be redundant and would risk drift.

### 6.2 `coexperienced_scene_recall_executor.py` — deterministic six-lane re-run

Rebuilds one archived scene through the identical helpers the engine uses per turn (`real_experience_learning_pipeline._evolve_real_causal_window` / `_build_typed_language_lane` / `_build_expression` / `_seal`, plus `closed_experience.prepare_closed_experience_evidence`), recognizes against the **live** mode bank, and evaluates a `SELF_GENERATED_RECALL` commit.

```python
@dataclass
class LiveRecallState:
    """One shared mutable holder the engine updates each turn and the executor reads at settle time.
    Solves the construction-order circularity (provider is built before the engine) without a callback into the engine."""
    mode_bank: ExpressionModeBank
    scene_archive: CoexperiencedSceneArchive
    def snapshot(self) -> tuple[ExpressionModeBank, CoexperiencedSceneArchive]: ...
    def update(self, *, mode_bank: ExpressionModeBank, scene_archive: CoexperiencedSceneArchive) -> None: ...

@dataclass(frozen=True, slots=True)
class CoexperiencedSceneRecallRuntime:
    """The fixed per-generation context needed to rebuild any scene (everything the engine also holds)."""
    mounted_runtime: MountedSixLaneRuntime
    engine_id: str
    physical_profile_receipt_sha256: str
    typed_language_phase_calibration_id: str
    typed_language_phase_kappa: Fraction
    chemistry_authentication_key: bytes
    chemistry_key_id: str
    l6_evaluation: L6Evaluation                 # the same reused L6 the engine computes once (clean_conversation_engine.py:615)

@dataclass(frozen=True, slots=True)
class CoexperiencedSceneRecallExecution:
    """Fresh full-field facts of one re-run; the direct inputs the settlement needs (no ClosedExperienceProviderBundle required)."""
    sealed: SealedClosedExperience
    expression_evaluation: FieldExpressionEvaluation
    recognition: ExpressionModeBoundaryResult
    experience_origin: ExperienceOriginAuthority          # SELF_GENERATED_RECALL
    language_evidence: PortTransportEvidence              # terminal language-lane evidence
    sensory_evidence: tuple[PortTransportEvidence, ...]   # the 5 non-language; receipts == source_binding's by construction
    typed_language_input: TypedLanguageFrozenKernelInput
    commit_decision: CommitDecision                       # exact-zero fresh R_event, SELF_GENERATED_RECALL
    receipt_registry: ReceiptRegistry
    def verify(self, prior_registry: ReceiptRegistry) -> None: ...

class CoexperiencedSceneRecallExecutor:
    def __init__(
        self, *, executor_id: str, runtime: CoexperiencedSceneRecallRuntime, live_recall_state: LiveRecallState
    ) -> None: ...
    def execute(
        self, *, source_event: CommittedMotifEvent, staged_output: OutputActuation,
        source_binding: MotifOutputBinding, receipt_registry: ReceiptRegistry,
    ) -> CoexperiencedSceneRecallExecution: ...
```

`execute` internals (deterministic, in order):
1. `mode_bank, archive = self._live.snapshot()`.
2. `episode = archive.resolve(profile_binding_sha256=source_binding.profile_binding_sha256, sensory_evidence_receipt_sha256s=source_binding.sensory_evidence_receipt_sha256s)`.
3. Re-mount the packaged production chemistry (deterministic) and rebuild the scene for `episode.scene_task_id` / `episode.scene_language_text` via the engine's own helpers — bit-for-bit the path in `clean_conversation_engine._build_turn_expression` and `production_runtime_bootstrap._build_genesis_scene`.
4. `recognition = evaluate_expression_mode_boundary(bank=mode_bank, input_expression=expression, …)`; require `RECOGNIZED`.
5. `sealed = _seal(...)`.
6. Build **self-recall** commit providers: `ExperienceOriginKind.SELF_GENERATED_RECALL`, `evaluate_event_support(memory_energy=None)` (→ exact-zero `R_event`), `evaluate_safe_mode` over CLEAR facts, the reused `l6_evaluation`/`l6_scope`, and the asserted `AuthorityDisposition.PASS` Global-UF (the identical honest limitation `_build_commit_providers` already documents at `clean_conversation_engine.py:476–502`). Then `evaluate_commit_boundary(...)`; require `CommitStatus.COMMIT`.
7. Extract `language_evidence` (terminal language `PortTransportEvidence`) and `sensory_evidence` (the 5 non-language) from `sealed.evidence`; assert `sorted(e.evidence_receipt_sha256 for e in sensory_evidence) == source_binding.sensory_evidence_receipt_sha256s` (fails closed if reconstruction ever drifts — this is the early-warning tripwire, §11).
8. Return `CoexperiencedSceneRecallExecution`.

The executor **does not** call `prepare_story_global_uf`, `execute_story_native_replay`, `assemble_heterogeneous_l6`, or `assemble_closed_experience_provider_bundle`; it reuses only the engine's own scene helpers plus `commit.py`/`event_support.py`/`safe_mode.py`/`experience_origin.py` — the same authorities `_build_commit_providers` already uses.

### 6.3 `coexperienced_scene_recall_provider.py` — the injected `FreshRecallSelfSenseProvider`

Structurally satisfies `recall_reentry.FreshRecallSelfSenseProvider` (`recall_reentry.py:389–405`), so it drops straight into `RememberedOutputProviders` / `run_clean_conversation_transaction` with **no** transaction-side change.

```python
class CoexperiencedSceneRecallProvider:
    operator_id: str = FRESH_RECALL_SELF_SENSE_OPERATOR_ID   # recall_reentry.py:57
    provider_id: str
    authority_receipt_sha256: str

    def __init__(
        self, *, provider_id: str, profile_binding_sha256: str,
        executor: CoexperiencedSceneRecallExecutor,
        motif_kinds: StableModeMotifBank | tuple[RememberedMotifKindAuthority, ...],
        authority_receipt_sha256: str,
    ) -> None: ...

    def settle(
        self, *, source_event: CommittedMotifEvent, staged_output: OutputActuation,
        source_binding: MotifOutputBinding, output_binding_bank: MotifBindingBank,
        stable_mode_motif_bank: StableModeMotifBank, receipt_registry: ReceiptRegistry,
    ) -> RecallTransitionSettlement: ...
```

`settle` mirrors `fresh_recall_provider.FullFieldFreshRecallProvider.settle` (`fresh_recall_provider.py:410–682`) exactly, with two differences: (a) it calls `CoexperiencedSceneRecallExecutor.execute` instead of `FreshRecallClosedExperienceExecutor.execute`, consuming the lighter `CoexperiencedSceneRecallExecution`; and (b) it **omits** the `verify_fresh_recall_archive_lineage` step (`fresh_recall_provider.py:351–375`), which is structurally inapplicable — there is no five-sense archive episode and no cross-universe raw-trace pairing to reconcile (the fresh evidence *is* the cited evidence). Every settlement receipt is built with the **unchanged** `recall_reentry.py` builders (`recalled_language_transduction_receipt_payload`, `recall_expression_input_receipt_payload`, the stable-mode-motif-binding builder, `output.committed_motif_event_receipt_payload` for `next_event`), so the emitted `RecallTransitionSettlement` is byte-schema-identical to what the five-sense provider would emit, and `RecallTransitionSettlement.verify` (`recall_reentry.py:600–760`) passes unchanged.

Rationale for a new provider rather than reusing `FullFieldFreshRecallProvider`: that provider hard-requires a `LineagedRecallClosedExperienceExecution` (five-sense lineage) via `verify_fresh_recall_archive_lineage` (`fresh_recall_provider.py:359–372`). Reusing it would force either a five-sense episode (impossible, §3.1) or weakening that verified check for the five-sense path. A separate provider isolates the risk to new files, consistent with this project's practice.

---

## 7. Exact existing-file changes (hard requirements of the chosen design)

These are real, named edits. They are stated plainly because this document is what gets ratified before they happen.

### 7.1 `clean_conversation_engine.py`

1. **Archive slot type.** Replace the unused five-sense `RecallStoryEpisodeArchive` field (`self._archive`, `clean_conversation_engine.py:592–596`) with `self._scene_archive: CoexperiencedSceneArchive`. Constructor param `recall_story_episode_archive` → `coexperienced_scene_archive: CoexperiencedSceneArchive | None`.
2. **Shared live holder.** Constructor accepts `live_recall_state: LiveRecallState` and stores it. After growing the bank each turn (`clean_conversation_engine.py:747`), call `self._live_recall_state.update(mode_bank=self._mode_bank, scene_archive=self._scene_archive)` **before** invoking `run_clean_conversation_transaction`. This is the single line that lets recall recognize against the live bank (§3.4) and see prior-turn episodes (§5).
3. **Archive-on-learn.** In `_learn_and_persist` (`clean_conversation_engine.py:881–919`), after `learn_committed_binding_transaction`, build and append the episode:
   ```python
   episode = create_coexperienced_scene_episode(
       profile_binding_sha256=self._registry.profile_binding_sha256,
       motif_receipt_sha256=<new binding's motif_receipt_sha256 from new_state.output_bank>,
       sensory_evidence_receipt_sha256s=_sensory_receipts(sealed),   # six-lane, == the binding's
       coexperienced_scalar_text=turn.text,
       scene_task_id=turn.task_id,
       scene_language_text=turn.text,
       engine_id=self._engine_id,
   )
   self._scene_archive = self._scene_archive.with_episode(episode)
   self._live_recall_state.update(mode_bank=self._mode_bank, scene_archive=self._scene_archive)
   ```
   (`_sensory_receipts` is imported from `expression_learning`; no change to `expression_learning.py` — the receipts recorded in the episode are *exactly* the ones the binding already carries, §3.2.)
4. **Checkpoint.** In `_persist_checkpoint` (`clean_conversation_engine.py:921–954`) replace `recall_story_archive_checkpoint_payload(self._archive, …)` with `coexperienced_scene_archive_checkpoint_payload(self._scene_archive, …)`; keep the same three-file generation-store commit shape (rename the archive relative-path constant to `coexperienced_scene_archive_checkpoint.json`).

No change to recognition, commit, learning, or the transaction call itself.

### 7.2 `production_runtime_bootstrap.py`

1. **Wire the subsystem.** After `mount_six_lane_runtime`, construct `LiveRecallState(mode_bank=grown_runtime.expression_mode_bank, scene_archive=<restored or empty>)`, a `CoexperiencedSceneRecallRuntime`, a `CoexperiencedSceneRecallExecutor`, and a `CoexperiencedSceneRecallProvider`; pass the provider as `fresh_recall_provider` and the holder/archive into the engine constructor. (Today `fresh_recall_provider` is a required, externally-injected parameter, `production_runtime_bootstrap.py:811, 850–855, 923`. This change makes the bootstrap construct the real one instead of demanding an injected stub. That is the whole point of "build recall before wiring live.")
2. **Restore path.** In `_restore_generation` (`production_runtime_bootstrap.py:743–794`) restore `CoexperiencedSceneArchive` via `restore_coexperienced_scene_archive_checkpoint` in place of `restore_recall_story_archive_checkpoint`, and seed `LiveRecallState` with it.

No change to genesis-scene construction, restore verification, or the generation-identity binding.

### 7.3 Nothing else

No change to `story_native_replay.py`, `story_global_uf_basin.py`, `closed_experience.py`, `field.py`, `commit.py`, `expression_learning.py`, `expression_modes.py`, `recall_reentry.py`, `output.py`, `conversation.py`, or the five-sense recall stack (`fresh_recall_executor.py`, `fresh_recall_provider.py`, `recall_story_episode_archive.py`, `recall_story_runtime_resolver.py`, `recall_replay_integrity_provider.py`). Those remain valid for their own counterfactual-replay purpose.

---

## 8. Problem #1 (pre-window reconciliation) — disposition

**Already solved on the engine's path.** §3.6: the engine consumes `MountedSixLaneRuntime.pre_window_state`, built by `mount_pre_window_state` against a real `ExactFieldState`/`ExpressionModeBank` and already satisfying `MountedStoryGlobalUFBasinProfile.verify`'s digest identity (`story_global_uf_basin.py:334–341`). The fabricated-hash `_mount_simple_pre_window` (`real_experience_learning_pipeline.py:887–919`) is not on the engine's path. Direction C's recall re-runs the engine's own path, so it inherits the same reconciled pre-window; it never mounts a `story_native_replay` pre-window at all. **No pre-window work is required for this design.** (Had we chosen literal B, the §3.1 wall would have blocked it long before the pre-window mattered.)

---

## 9. Problem #4 (no `ExpressionModeBank` checkpoint/restore) — disposition

**Not orthogonal; it bounds recall to within one process's uptime.** Recall recognizes against the live grown bank (§3.4, §5). Within one process, the bank grows monotonically and retains every prior scene's mode, so recall of anything learned earlier in the same uptime works. Across a restart, `production_runtime_bootstrap` remounts the bank at rank zero (its own docstring, `production_runtime_bootstrap.py:33–38`): restored `LearnedBindingState` (and, under this design, the restored scene archive) is byte-real, but a rank-0 bank returns `BOOTSTRAP_SILENCE` on the recalled scene, so the self-recall commit recall depends on cannot fire.

Precise statement for ratification:
- **In scope / delivered:** recall of freshly-learned content is fully functional within one process's uptime.
- **Out of scope / gating cross-restart recall:** an `ExpressionModeBank` checkpoint/restore mechanism. Until it exists, learned bindings and their scene episodes survive restart but become recall-inert until the substrate re-lives enough experience to regrow their modes. This design does **not** invent that mechanism; it names it as the single remaining gate on cross-restart recall.

---

## 10. Composition — how the fixes compose, per turn

Ordinary turn (no change to recognition/commit/learn):
1. `_build_turn_expression` (unchanged) → `evaluate_expression_mode_boundary` grows `self._mode_bank` (unchanged).
2. **New:** `live_recall_state.update(mode_bank, scene_archive)`.
3. `run_clean_conversation_transaction` (unchanged): recompute recognition+commit; on `COMMIT`, `settle_complete_remembered_expression(provider=self._fresh_recall_provider, …)` (`conversation.py:538–552`).
   - For each motif in the learned expression, the provider's `settle` resolves the scene from `source_binding`, re-runs it (executor), self-recall-commits it, and returns a `RecallTransitionSettlement`; the chain releases visible text only at exact expression close (unchanged `recall_reentry`/`output` machinery). If the input turn has no matching learned mode, commit is no-commit/unknown → honest silence (unchanged).
4. On real commit + learn (`result.initial_event_receipt_sha256 is not None`), **new:** `_learn_and_persist` appends the scene episode, updates the holder, and checkpoints the archive.

Problem #1's fix is "reuse the runtime's already-reconciled pre-window" (nothing to do). Problems #2/#3's fixes are subsumed: rather than reconcile the five-sense archive to six-lane evidence (impossible, §3.1), recall stays natively six-lane, so #2 (constant-vs-time-varying flux) and #3 (five-sense-profile-vs-six-lane-topology rooting) simply do not arise on this path.

---

## 11. Test plan — a genuine, non-monkeypatched, learn-then-recall proof

The proof must exercise real recognition, real commit, and real fresh full-field re-commit — no monkeypatch of recognition/commit/recall, no hand-built settlement, per §13.3 and the §6 forbidden-mechanisms list of the governing spec.

**T1 — learn then recall within one engine (the headline test).** Cold-start a real `ProductionCleanConversationEngine` via the bootstrap (real chemistry profile, real mounted runtime, the new provider). Drive turn A: input a single scalar `x` under a scene that genuinely commits and learns (the coexperienced output is `x`'s own language event, per `CoexperiencedOutput.from_typed_scalar`). Assert an episode was archived. Drive a later turn B whose recognition selects the learned mode. Assert:
- `result.status == EXPRESSION_RELEASED` and `result.visible_text` contains the learned scalar (given at least one learned expression-close, see §12);
- the released scalar's `RecallTransitionSettlement.commit_decision.receipt_sha256` is a **fresh** commit receipt for turn B's recall (distinct from turn A's learn-time commit receipt), proving re-commit, not replay of a stored value;
- `settlement.cited_sensory_evidence` receipts equal the learned `source_binding.sensory_evidence_receipt_sha256s` (this is what `RecallTransitionSettlement.verify` enforces, `recall_reentry.py:686`; asserting it directly documents that the six-lane reconstruction is bit-exact);
- the recall execution's origin is `SELF_GENERATED_RECALL` with exact-zero `R_event`.

**T2 — recall miss is honest silence.** Drive a turn whose scene does not match any archived episode; assert `archive.resolve` raises inside the executor and the turn yields typed silence, never gibberish and never a fabricated scalar.

**T3 — determinism / tamper tripwire.** Assert that re-running the executor for the same episode twice produces byte-identical `sealed`/evidence receipts; and that mutating any reconstruction input (a descriptor, the text, `engine_id`, the physical-profile receipt) makes the §6.2-step-7 receipt-equality assertion fail closed rather than silently emit a different scene.

**T4 — archive checkpoint round-trip.** Learn a scene, checkpoint, restore the archive from bytes, and assert the restored episode resolves identically (byte-equal episode receipt).

**T5 — restart bound (documents §9).** Learn a scene, persist, restart the engine (rank-0 bank), attempt recall; assert the turn is honest silence (not an error), and record it as the known cross-restart limitation gated on the mode-bank checkpoint gap — so a future mode-bank-restore change has an explicit test to flip.

All five run against real objects end-to-end; none asserts `False` in place of a required result, and none substitutes a fixture for recognition, commit, or recall.

---

## 12. Companion requirement (named, not silently assumed): expression-close learning

`clean_conversation_engine._learn_and_persist` learns with `expression_close=False` (`clean_conversation_engine.py:914`), so learned expressions stay open, and `recall_reentry` releases visible text **only at exact expression close**. For T1 to actually emit (rather than stage-and-silence), the engine must learn at least one expression-close for an emittable output — the mechanism exists (`expression_learning.learn_committed_binding_transaction(expression_close=True)`, exercised by `real_experience_learning_pipeline.close_real_multimodal_expression`), but *when* an expression closes is a cognition/policy decision separate from the recall mechanism this document specifies. Flagged as a small, separate decision required before the emission half of T1 can pass; it does not change any file named above and does not affect the recall-resolution machinery, which is what this design delivers.

---

## 13. Risk if this proves wrong once built — blast radius and early warning

**Blast radius is confined to new files plus the two named edits.** No physics file, no verified recall/commit/learning file, and no transaction contract changes. If Direction C is wrong, the five-sense recall stack is untouched and the engine's commit/learn path is untouched; reverting the two edits and dropping three new files restores the pre-design state exactly. No deploy is implied by this document (§Status).

**A fourth blocker, if one exists, surfaces early — before any deploy — at three deterministic tripwires:**
1. **Reconstruction drift** trips at §6.2 step 7 (`sensory_evidence` receipts ≠ `source_binding` receipts) — a hard `ReceiptError` in `execute`, caught by T1 and T3 the first time the re-run diverges by even one byte. This is the single most load-bearing assumption (bit-exact deterministic scene reconstruction); it is asserted, not trusted.
2. **Recognition failure** (the live-bank assumption of §3.4) trips as `UNKNOWN`/`BOOTSTRAP_SILENCE` → typed silence, caught by T1 (expects `RECOGNIZED`) and T5 (expects silence at rank 0).
3. **Settlement schema mismatch** trips inside the *unchanged* `RecallTransitionSettlement.verify` (`recall_reentry.py:600–760`), caught by T1 the moment any reused receipt builder is fed a wrong value.

Because all three are real, deterministic, non-monkeypatched assertions inside a local end-to-end test, a fourth blocker manifests as a red test on the first run — not as a silent live regression. The known, *named* residual is the cross-restart mode-bank gap (§9), which is bounded, documented, and has its own guarding test (T5).

---

## 14. Summary for the ratifier

- **Do:** build the three new modules (§6), make the two named edits (§7), keep the five-sense stack untouched.
- **Delivers:** real, fresh-full-field recall of freshly-learned content within one process's uptime (§5, §10), provable by a genuine end-to-end test (§11).
- **Does not touch:** any physics or verified recall/commit/learning file; problem #1 is already solved on the engine's path (§8); problems #2/#3 are dissolved rather than reconciled (§4, §10).
- **Bounded residual:** cross-restart recall is gated on a separate mode-bank checkpoint/restore mechanism (§9); emission is gated on an expression-close policy decision (§12). Both are named, not smuggled.
- **Status:** `proposed_pending_ratification` — implementation is a later, separate dispatch.
