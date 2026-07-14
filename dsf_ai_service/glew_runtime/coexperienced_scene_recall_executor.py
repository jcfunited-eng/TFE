"""Deterministic six-lane re-run of one archived coexperienced scene.

This module answers ``docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-
20260714-v1.md`` section 6.2.  It rebuilds one archived scene through the
identical helpers the engine uses per turn (``real_experience_learning_
pipeline._evolve_real_causal_window`` / ``_build_typed_language_lane`` /
``_build_expression`` / ``_seal`` plus ``closed_experience.prepare_closed_
experience_evidence``, and ``clean_conversation_engine._scene_descriptors``),
recognizes it against the engine's *live* grown mode bank, and evaluates a
``SELF_GENERATED_RECALL`` full-field commit with exact-zero fresh ``R_event``.

Because the scene is fully deterministic from ``(scene_task_id, scene_
language_text)`` over the engine's fixed ``MountedSixLaneRuntime`` authorities
and fixed ``physical_profile`` receipt (design section 5), the regenerated
six-lane evidence reproduces the exact six-lane sensory receipts a learned
``MotifOutputBinding`` carries (``expression_learning._sensory_receipts``).
Step 7 of :meth:`CoexperiencedSceneRecallExecutor.execute` asserts that
equality directly, so reconstruction drift trips a hard ``ReceiptError`` on
the first divergent byte (design section 11 / 13 tripwire #1) rather than
silently emitting a different scene.

Unlike the five-sense ``FreshRecallClosedExperienceExecutor``, this executor
never calls ``prepare_story_global_uf``, ``execute_story_native_replay``,
``assemble_heterogeneous_l6``, or ``assemble_closed_experience_provider_
bundle``.  It reuses only the engine's own scene helpers plus ``commit.py`` /
``event_support.py`` / ``safe_mode.py`` / ``experience_origin.py`` -- the same
authorities ``clean_conversation_engine._build_commit_providers`` already
uses (design section 6.2).

Live construction-order coupling
--------------------------------
The provider/executor are constructed by the bootstrap *before* the engine
learns anything.  Recall must nonetheless read the engine's *current* mode
bank, scene archive, and learned motif-kind authorities at settle time
(design section 5 / section 3.4).  :class:`LiveRecallState` is the single
shared mutable holder the engine updates each turn and the executor/provider
read.  Design section 6.2 names ``mode_bank`` and ``scene_archive``; this
implementation additionally carries ``motif_kinds`` -- the live learned
``RememberedMotifKindAuthority`` tuple -- because the provider (section 6.3)
must classify the recalled next motif as CONTENT vs EXPRESSION_CLOSE, and
that classification is exactly the same "current learned state" the mode bank
and scene archive already track (it is empty at cold-start and grows per
turn).  This is a minimal, grounded extension of section 6.2's holder, not a
new mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .closed_experience import (
    ClosedExperienceProviderUnknown,
    SealedClosedExperience,
    prepare_closed_experience_evidence,
)
from .commit import (
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    CommitDecision,
    CommitStatus,
    L6ScopeAuthority,
    binary_authority_receipt_payload,
    evaluate_commit_boundary,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from .event_support import EventSupportEvaluationStatus, evaluate_event_support
from .experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from .expression_modes import (
    ExpressionModeBank,
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)
from .expressions import (
    ExpressionEvaluationStatus,
    FieldExpressionEvaluation,
    evaluate_closed_experience_expression,
)
from .field import PortTransportEvidence
from .language import TypedLanguageFrozenKernelInput
from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256, require_identifier
from .output import (
    CommittedMotifEvent,
    MotifOutputBinding,
    OutputActuation,
    OutputBindingKind,
    OutputReason,
    OutputStatus,
    StageDisposition,
)
from .real_experience_learning_pipeline import (
    _build_expression,
    _build_typed_language_lane,
    _evolve_real_causal_window,
    _seal,
)
from .safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from .six_lane_runtime_mount import MountedSixLaneRuntime
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryChemistryStatus,
    mount_packaged_production_story_chemistry,
)

from .coexperienced_scene_archive import (
    CoexperiencedSceneArchive,
    CoexperiencedSceneEpisode,
)


def _canonical_bytes(value: object) -> bytes:
    import json

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_registry(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    values = {item.digest: item.payload for item in registry.records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("coexperienced scene recall generated an empty receipt")
        digest = receipt_sha256(payload)
        existing = values.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError("coexperienced scene recall receipt digest collision")
        values[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, values[key]) for key in sorted(values)),
    )


def _merge_registry(registry: ReceiptRegistry, addition: ReceiptRegistry) -> ReceiptRegistry:
    """Union ``addition``'s records into ``registry``, keeping ``registry``'s
    own root -- exactly mirroring ``clean_conversation_engine._merge_registry``
    (the chemistry-manifest root every real evidence stream carries)."""

    return _extend_registry(registry, *(value.payload for value in addition.records))


def _mode_payloads(result: ExpressionModeBoundaryResult) -> tuple[bytes, ...]:
    payloads = [
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
        result.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            payloads.extend(
                (
                    mode.source_expression.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.receipt_payload,
                )
            )
    return tuple(payloads)


@dataclass
class LiveRecallState:
    """One shared mutable holder the engine updates each turn and the executor
    /provider read at settle time.  Solves the construction-order circularity
    (provider is built before the engine) without a callback into the engine.

    ``motif_kinds`` extends design section 6.2's holder (see module docstring):
    the live learned ``RememberedMotifKindAuthority`` tuple the provider needs
    to classify a recalled next motif as CONTENT vs EXPRESSION_CLOSE."""

    mode_bank: ExpressionModeBank
    scene_archive: CoexperiencedSceneArchive
    motif_kinds: tuple = ()

    def snapshot(self):
        return (self.mode_bank, self.scene_archive, self.motif_kinds)

    def update(
        self,
        *,
        mode_bank: ExpressionModeBank,
        scene_archive: CoexperiencedSceneArchive,
        motif_kinds: tuple = (),
    ) -> None:
        if not isinstance(mode_bank, ExpressionModeBank):
            raise ReceiptError("live recall state requires a typed expression mode bank")
        if not isinstance(scene_archive, CoexperiencedSceneArchive):
            raise ReceiptError("live recall state requires a typed coexperienced scene archive")
        if not isinstance(motif_kinds, tuple):
            raise ReceiptError("live recall state motif kinds must be an immutable tuple")
        self.mode_bank = mode_bank
        self.scene_archive = scene_archive
        self.motif_kinds = motif_kinds


@dataclass(frozen=True, slots=True)
class CoexperiencedSceneRecallRuntime:
    """The fixed per-generation context needed to rebuild any scene (everything
    the engine also holds)."""

    mounted_runtime: MountedSixLaneRuntime
    engine_id: str
    physical_profile_receipt_sha256: str
    typed_language_phase_calibration_id: str
    typed_language_phase_kappa: Fraction
    chemistry_authentication_key: bytes
    chemistry_key_id: str
    l6_evaluation: object  # L6Evaluation -- the same reused L6 the engine computes once


@dataclass(frozen=True, slots=True)
class CoexperiencedSceneRecallExecution:
    """Fresh full-field facts of one re-run; the direct inputs the settlement
    needs (no ``ClosedExperienceProviderBundle`` required)."""

    sealed: SealedClosedExperience
    expression_evaluation: FieldExpressionEvaluation
    recognition: ExpressionModeBoundaryResult
    experience_origin: ExperienceOriginAuthority
    language_evidence: PortTransportEvidence
    sensory_evidence: tuple[PortTransportEvidence, ...]
    typed_language_input: TypedLanguageFrozenKernelInput
    commit_decision: CommitDecision
    receipt_registry: ReceiptRegistry

    def verify(self, prior_registry: ReceiptRegistry) -> None:
        if prior_registry.profile_binding_sha256 != self.receipt_registry.profile_binding_sha256:
            raise ReceiptError("coexperienced scene recall changed the GLEW profile")
        for record in prior_registry.records:
            if self.receipt_registry.resolve(record.digest, "prior recall receipt") != record.payload:
                raise ReceiptError("coexperienced scene recall altered a mounted receipt")
        if self.experience_origin.kind is not ExperienceOriginKind.SELF_GENERATED_RECALL:
            raise ReceiptError("coexperienced scene recall returned a non-recall origin")
        self.expression_evaluation.verify()
        self.typed_language_input.verify()
        self.commit_decision.verify()
        if (
            self.expression_evaluation.status is not ExpressionEvaluationStatus.CERTIFIED
            or self.expression_evaluation.expression_receipt_sha256
            != self.sealed.expression.receipt_sha256
        ):
            raise ReceiptError("coexperienced scene recall expression did not certify")
        mounted_evaluation = self.receipt_registry.resolve(
            self.expression_evaluation.receipt_sha256,
            "coexperienced scene recall expression-evaluation receipt",
        )
        if mounted_evaluation != self.expression_evaluation.receipt_payload:
            raise ReceiptError("coexperienced scene recall expression evaluation changed")
        if self.language_evidence.lane_id != "language":
            raise ReceiptError("coexperienced scene recall language evidence is not language")
        if not isinstance(self.sensory_evidence, tuple):
            raise ReceiptError("coexperienced scene recall sensory evidence must be immutable")
        if any(value.lane_id == "language" for value in self.sensory_evidence):
            raise ReceiptError("coexperienced scene recall sensory records hide language evidence")
        for value in (self.language_evidence, *self.sensory_evidence):
            value.verify(self.receipt_registry)
        if (
            self.commit_decision.status is not CommitStatus.COMMIT
            or self.commit_decision.closed_experience_receipt_sha256
            != self.sealed.closed_experience.authority_receipt_sha256
            or self.commit_decision.topology_authority_receipt_sha256
            != self.sealed.expression.topology.authority_receipt_sha256
        ):
            raise ReceiptError("coexperienced scene recall commit belongs to another full field")
        mounted_commit = self.receipt_registry.resolve(
            self.commit_decision.receipt_sha256,
            "coexperienced scene recall commit-decision receipt",
        )
        if mounted_commit != self.commit_decision.receipt_payload:
            raise ReceiptError("coexperienced scene recall commit decision changed")


class CoexperiencedSceneRecallExecutor:
    """Rebuild one archived coexperienced scene and self-recall-commit it."""

    def __init__(
        self,
        *,
        executor_id: str,
        runtime: CoexperiencedSceneRecallRuntime,
        live_recall_state: LiveRecallState,
    ) -> None:
        self.executor_id = require_identifier(executor_id, "coexperienced scene recall executor id")
        if not isinstance(runtime, CoexperiencedSceneRecallRuntime):
            raise ReceiptError("coexperienced scene recall executor requires a typed runtime")
        if not isinstance(live_recall_state, LiveRecallState):
            raise ReceiptError("coexperienced scene recall executor requires a live recall state")
        self._runtime = runtime
        self._live = live_recall_state

    @property
    def live_recall_state(self) -> LiveRecallState:
        return self._live

    def _verify_staged_source(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        source_event.verify(receipt_registry)
        source_binding.verify(receipt_registry)
        if source_binding.kind is not OutputBindingKind.LANGUAGE_SCALAR:
            raise ReceiptError("coexperienced scene recall source binding is not one typed scalar")
        # ``_canonical_source_binding`` (recall_reentry.py) resolves the binding
        # BY ``source_event.motif_receipt_sha256``, so the motif always agrees;
        # keep it as a defensive check. We deliberately do NOT require
        # ``source_event.sensory == source_binding.sensory``. That equality --
        # which the five-sense ``fresh_recall_executor._verify_staged_source``
        # imposes -- is structurally wrong for a real recall chain: a chain
        # event's sensory is the scene RE-RUN to produce it, while the binding's
        # sensory is the scene the motif was LEARNED from, and those are
        # different scenes as soon as the chain advances (the canonical passing
        # chain in ``test_recall_self_sense_reentry.py`` has an event whose
        # sensory is the first scene's while its own binding cites the second
        # scene's). The scene to re-run is the SOURCE_BINDING's scene: the
        # archive is keyed by ``source_binding.sensory`` (step 1 below) and the
        # regenerated receipts are asserted equal to it (step 7). The true
        # chain invariant is ``settlement.cited_sensory == source_binding.
        # sensory``, enforced unchanged by ``RecallTransitionSettlement.verify``.
        if source_event.motif_receipt_sha256 != source_binding.motif_receipt_sha256:
            raise ReceiptError("coexperienced scene recall event and source binding differ")
        settlement = staged_output.receipt
        # Exactly the private-staged contract ``fresh_recall_executor``'s own
        # ``_verify_staged_source`` enforces: a genuine STAGED_PRIVATE
        # settlement carries an empty ``binding_receipt_sha256s`` (which
        # specific binding was staged is legitimately private until release),
        # the sole reason the actuator ever pairs with STAGED_PRIVATE, and the
        # RETAINED_PRIVATE disposition.
        if (
            staged_output.text
            or settlement.status is not OutputStatus.STAGED_PRIVATE
            or settlement.reason is not OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING
            or settlement.stage_disposition is not StageDisposition.RETAINED_PRIVATE
            or settlement.event_receipt_sha256 != source_event.event_receipt_sha256
            or settlement.binding_receipt_sha256s != ()
        ):
            raise ReceiptError("coexperienced scene recall scalar was not exactly private-staged")

    def _rebuild_scene(
        self,
        *,
        episode: CoexperiencedSceneEpisode,
        registry: ReceiptRegistry,
    ):
        """Rebuild one archived scene's field expression bit-for-bit the way
        ``clean_conversation_engine._build_turn_expression`` and
        ``production_runtime_bootstrap._build_genesis_scene`` do (same real
        helpers, same identity conventions, same physical-profile receipt)."""

        # Local import avoids a module-import cycle: the engine imports the
        # LiveRecallState from this module only under TYPE_CHECKING, but this
        # executor genuinely reuses the engine's own descriptor derivation.
        from .clean_conversation_engine import _scene_descriptors

        runtime = self._runtime
        mounted = runtime.mounted_runtime
        task_id = episode.scene_task_id
        text = episode.scene_language_text

        chemistry = self._mount_chemistry()
        descriptors = _scene_descriptors(task_id)
        bridge = _evolve_real_causal_window(chemistry, scene_id=task_id, descriptors=descriptors)
        registry = _merge_registry(registry, bridge.receipt_registry)

        language_input, registry = _build_typed_language_lane(
            binding=mounted.typed_language_kernel_binding,
            phase_id=runtime.typed_language_phase_calibration_id,
            phase_kappa=runtime.typed_language_phase_kappa,
            text=text,
            event_id=f"{task_id}-language",
            source_epoch=f"{task_id}-language-epoch",
            timestamps=mounted.causal_grid.timestamps,
            registry=registry,
        )

        preparation = prepare_closed_experience_evidence(
            streams=(language_input.stream, *bridge.streams),
            kernel_inputs=(language_input.kernel_input, *bridge.kernel_inputs),
            source_time_start=Fraction(0),
            grid=mounted.causal_grid,
            support_domain=mounted.support_domain,
            resonance_graph=mounted.resonance_graph,
            resonance_operator=mounted.resonance_operator,
            topology=mounted.field_topology,
            receipt_registry=registry,
        )
        if isinstance(preparation, ClosedExperienceProviderUnknown):
            raise ReceiptError(
                f"coexperienced scene recall evidence preparation failed for {task_id}: "
                f"{preparation.reason}"
            )
        registry = preparation.receipt_registry

        expression, registry = _build_expression(
            topology=mounted.field_topology,
            preparation=preparation,
            precision=mounted.precision_authority,
            physical_profile_receipt_sha256=runtime.physical_profile_receipt_sha256,
            identity=task_id,
            registry=registry,
        )
        return expression, language_input, preparation, registry

    def _mount_chemistry(self) -> StoryChemistryRuntime:
        runtime = self._runtime
        mounted = mount_packaged_production_story_chemistry(
            runtime_authentication_key=runtime.chemistry_authentication_key,
            runtime_key_id=runtime.chemistry_key_id,
        )
        if mounted.status is not StoryChemistryStatus.MOUNTED or mounted.runtime is None:
            raise ReceiptError(
                f"coexperienced scene recall could not re-mount production chemistry: {mounted.reason}"
            )
        if mounted.runtime.manifest.receipt_sha256 != (
            runtime.mounted_runtime.story_chemistry_runtime.manifest.receipt_sha256
        ):
            raise ReceiptError(
                "coexperienced scene recall re-mounted a different chemistry manifest"
            )
        return mounted.runtime

    def _self_recall_commit(
        self,
        *,
        sealed: SealedClosedExperience,
        recognition: ExpressionModeBoundaryResult,
        registry: ReceiptRegistry,
    ) -> tuple[ExperienceOriginAuthority, CommitDecision, ReceiptRegistry]:
        """Build the same eight commit authorities ``clean_conversation_engine.
        _build_commit_providers`` builds, with exactly two differences (design
        section 6.2 step 6): the experience origin is
        ``SELF_GENERATED_RECALL`` (not FRESH_EXTERNAL) and event support is
        evaluated with ``memory_energy=None`` (yielding exact-zero fresh
        ``R_event``, the self-recall discipline the five-sense executor uses).
        The Global-UF is the same asserted PASS ``_build_commit_providers``
        already documents (no production ``GlobalUFReplayProvider`` exists)."""

        identity = f"{sealed.expression.receipt_sha256[:16]}:recall"
        experience_digest = sealed.closed_experience.authority_receipt_sha256
        topology = sealed.expression.topology
        topology_digest = topology.authority_receipt_sha256

        safe_profile = _canonical_bytes(
            {
                "identity": identity,
                "schema": "glew.coexperienced_scene_recall.integrity_profile.v1",
            }
        )
        fact_ids = ("chemistry", "field", "persistence")
        safe_scope_payload = safe_mode_scope_receipt_payload(
            scope_id=f"{identity}:safe-scope",
            topology_authority_receipt_sha256=topology_digest,
            required_fact_ids=fact_ids,
            source_profile_receipt_sha256=receipt_sha256(safe_profile),
        )
        safe_scope = MountedSafeModeScope(
            f"{identity}:safe-scope",
            topology_digest,
            fact_ids,
            receipt_sha256(safe_profile),
            receipt_sha256(safe_scope_payload),
        )
        facts = []
        fact_payloads: list[bytes] = []
        for fact_id in fact_ids:
            source = f"{identity}:integrity:{fact_id}".encode()
            payload = integrity_fact_receipt_payload(
                fact_id=fact_id,
                state=IntegrityFactState.CLEAR,
                topology_authority_receipt_sha256=topology_digest,
                closed_experience_receipt_sha256=experience_digest,
                source_operator_receipt_sha256=receipt_sha256(source),
            )
            facts.append(
                IntegrityFact(
                    fact_id,
                    IntegrityFactState.CLEAR,
                    topology_digest,
                    experience_digest,
                    receipt_sha256(source),
                    receipt_sha256(payload),
                )
            )
            fact_payloads.extend((source, payload))
        registry = _extend_registry(registry, safe_profile, safe_scope_payload, *fact_payloads)
        safe = evaluate_safe_mode(
            authority_id=f"{identity}:safe",
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            scope=safe_scope,
            facts=tuple(facts),
            receipt_registry=registry,
        )
        if safe.disposition is not AuthorityDisposition.PASS:
            raise ReceiptError("coexperienced scene recall safe-mode evaluation did not pass")
        registry = _extend_registry(registry, *safe.generated_receipt_payloads)

        origin_source = f"{identity}:self-recall-origin-source".encode()
        origin_payload = experience_origin_authority_receipt_payload(
            origin_id=f"{identity}:self-recall-origin",
            kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
            profile_binding_sha256=registry.profile_binding_sha256,
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            source_authority_receipt_sha256=receipt_sha256(origin_source),
        )
        origin = ExperienceOriginAuthority(
            f"{identity}:self-recall-origin",
            ExperienceOriginKind.SELF_GENERATED_RECALL,
            registry.profile_binding_sha256,
            topology_digest,
            experience_digest,
            receipt_sha256(origin_source),
            receipt_sha256(origin_payload),
        )
        registry = _extend_registry(registry, origin_source, origin_payload)

        event = evaluate_event_support(
            authority_id=f"{identity}:R-event",
            origin=origin,
            topology=topology,
            closed_experience_receipt_sha256=experience_digest,
            expression=sealed.expression,
            memory_energy=None,
            receipt_registry=registry,
        )
        if event.status is not EventSupportEvaluationStatus.RESOLVED or event.exact_r_event != 0:
            raise ReceiptError(
                "coexperienced scene recall did not resolve exact-zero fresh R_event"
            )
        registry = _extend_registry(registry, *event.generated_receipt_payloads)

        l6_evaluation = self._runtime.l6_evaluation
        l6_payload = l6_evaluation_receipt_payload(l6_evaluation)
        l6_scope_payload = l6_scope_authority_receipt_payload(
            authority_id=f"{identity}:L6-scope",
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
        )
        l6_scope = L6ScopeAuthority(
            f"{identity}:L6-scope",
            topology_digest,
            experience_digest,
            receipt_sha256(l6_payload),
            receipt_sha256(l6_scope_payload),
        )

        global_source = _canonical_bytes(
            {
                "identity": identity,
                "scope": "coexperienced_scene_recall_asserted_global_uf_authority",
                "schema": "glew.coexperienced_scene_recall.global_uf_source.v1",
            }
        )
        global_payload = binary_authority_receipt_payload(
            authority_id=f"{identity}:global-UF",
            kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
            disposition=AuthorityDisposition.PASS,
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            source_operator_receipt_sha256=receipt_sha256(global_source),
        )
        global_uf = BinaryCommitAuthority(
            f"{identity}:global-UF",
            BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
            AuthorityDisposition.PASS,
            topology_digest,
            experience_digest,
            receipt_sha256(global_source),
            receipt_sha256(global_payload),
        )
        registry = _extend_registry(registry, l6_payload, l6_scope_payload, global_source, global_payload)

        commit = evaluate_commit_boundary(
            topology=topology,
            recognition=recognition,
            l6_evaluation=l6_evaluation,
            l6_scope=l6_scope,
            closed_experience=sealed.closed_experience,
            safe_mode=safe.authority,
            event_support=event.authority,
            evidence=sealed.evidence,
            l5_applicability=sealed.l5_applicability,
            global_uf_validation=global_uf,
            receipt_registry=registry,
        )
        registry = _extend_registry(registry, commit.receipt_payload)
        return origin, commit, registry

    def execute(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> CoexperiencedSceneRecallExecution:
        self._verify_staged_source(
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=receipt_registry,
        )
        mode_bank, archive, _ = self._live.snapshot()
        episode = archive.resolve(
            profile_binding_sha256=source_binding.profile_binding_sha256,
            sensory_evidence_receipt_sha256s=source_binding.sensory_evidence_receipt_sha256s,
        )
        registry = _extend_registry(receipt_registry, episode.episode_receipt_payload)

        expression, language_input, preparation, registry = self._rebuild_scene(
            episode=episode, registry=registry
        )

        recognition = evaluate_expression_mode_boundary(
            topology=self._runtime.mounted_runtime.field_topology,
            bank=mode_bank,
            input_expression=expression,
            receipt_registry=registry,
        )
        registry = _extend_registry(registry, *_mode_payloads(recognition))
        if (
            recognition.status is not ExpressionRecognitionStatus.RECOGNIZED
            or recognition.winner_mode_index is None
        ):
            raise ReceiptError(
                "coexperienced scene recall re-run was not RECOGNIZED against the live bank: "
                f"{recognition.status}/{recognition.reason}"
            )

        sealed, registry = _seal(
            topology=self._runtime.mounted_runtime.field_topology,
            preparation=preparation,
            expression=expression,
            recognition=recognition,
            identity=episode.scene_task_id,
            registry=registry,
        )

        origin, commit, registry = self._self_recall_commit(
            sealed=sealed, recognition=recognition, registry=registry
        )
        if commit.status is not CommitStatus.COMMIT:
            raise ReceiptError(
                "coexperienced scene recall re-run did not commit: " + ",".join(commit.findings)
            )

        evaluation = evaluate_closed_experience_expression(
            expression, receipt_registry=registry
        )
        if evaluation.status is not ExpressionEvaluationStatus.CERTIFIED:
            raise ReceiptError("coexperienced scene recall expression did not certify")
        registry = _extend_registry(registry, evaluation.receipt_payload)

        # Canonical (sorted-by-receipt) order: a ``CommittedMotifEvent`` and a
        # ``RecallTransitionSettlement`` both require the cited sensory receipts
        # in sorted digest order, matching ``expression_learning._sensory_
        # receipts`` (which the learned binding carries sorted).
        sensory = tuple(
            sorted(
                (value for value in sealed.evidence if value.lane_id != "language"),
                key=lambda value: value.evidence_receipt_sha256,
            )
        )
        language_values = tuple(
            value for value in sealed.evidence if value.lane_id == "language"
        )
        if not language_values:
            raise ReceiptError("coexperienced scene recall seal lacks language evidence")
        language = max(
            language_values,
            key=lambda value: (
                value.provenance.source_timestamp,
                value.provenance.source_index,
            ),
        )

        # Tripwire (design section 6.2 step 7 / section 11 / section 13 #1):
        # the regenerated six-lane sensory receipts MUST equal the exact
        # receipts the learned binding carries.  A single divergent byte in
        # deterministic reconstruction fails closed here, before any text is
        # ever released, rather than silently emitting a different scene.
        regenerated = tuple(sorted(value.evidence_receipt_sha256 for value in sensory))
        if regenerated != source_binding.sensory_evidence_receipt_sha256s:
            raise ReceiptError(
                "coexperienced scene reconstruction drifted: regenerated six-lane sensory "
                "receipts differ from the learned binding's cited evidence"
            )

        execution = CoexperiencedSceneRecallExecution(
            sealed=sealed,
            expression_evaluation=evaluation,
            recognition=recognition,
            experience_origin=origin,
            language_evidence=language,
            sensory_evidence=sensory,
            typed_language_input=language_input,
            commit_decision=commit,
            receipt_registry=registry,
        )
        execution.verify(receipt_registry)
        return execution


__all__ = (
    "CoexperiencedSceneRecallExecution",
    "CoexperiencedSceneRecallExecutor",
    "CoexperiencedSceneRecallRuntime",
    "LiveRecallState",
)
