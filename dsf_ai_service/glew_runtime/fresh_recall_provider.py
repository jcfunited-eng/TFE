"""Concrete full-field provider for one fresh remembered-expression transition.

The provider contains no continuation table.  For every staged scalar it asks
one mounted closed-experience executor to run the actual recalled language plus
its cited senses through chemistry, frozen L0--L4, the full field, global UF,
Fixed-42 L6, and the expression commit boundary.  Only the resulting selected
mode is resolved through the stable mode/motif bank.

No output binding, motif suffix, word, or event count selects the next motif.
Every generated event names the exact fresh expression evaluation, commit,
origin-zero R_event, and stable mode/motif receipt that caused it.

A recalled sense is not identified by equality of its topology-bound transport
receipt: adding the language lane necessarily changes the full-field topology
and S_UF/R_UF authority.  The provider instead requires one exact archived-to-
fresh lineage authority.  Each archived evidence receipt and each fresh
evidence receipt remains explicit, while their raw L0-L4 trace digest must be
identical.  Missing, substituted, duplicated, or cross-experience lineage
fails closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .fresh_recall_executor import FreshRecallArchiveLineageAuthority
    from .recall_story_episode_archive import RecallStoryEpisode

from .closed_experience import ClosedExperienceProviderBundle, ProviderStatus
from .commit import CommitDecision, CommitStatus, evaluate_commit_boundary
from .experience_origin import ExperienceOriginKind
from .expressions import (
    ExpressionEvaluationStatus,
    FieldExpressionEvaluation,
)
from .field import PortTransportEvidence
from .language import TypedLanguageFrozenKernelInput
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)
from .output import (
    CommittedMotifEvent,
    MotifBindingBank,
    MotifEventKind,
    MotifOutputBinding,
    OutputActuation,
    committed_motif_event_receipt_payload,
    expression_close_authority_receipt_payload,
)
from .recall_reentry import (
    FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
    RecallTransitionSettlement,
    RecallTransitionStatus,
    StableModeMotifBank,
    fresh_recall_provider_authority_receipt_payload,
    recall_expression_input_receipt_payload,
    recall_transition_settlement_receipt_payload,
    recalled_language_transduction_receipt_payload,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_registry(
    registry: ReceiptRegistry,
    payloads: tuple[bytes, ...],
) -> ReceiptRegistry:
    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("fresh recall generated an empty receipt")
        digest = receipt_sha256(payload)
        if digest in mounted:
            if mounted[digest] != payload:
                raise ReceiptError("fresh recall encountered a receipt collision")
            continue
        records.append(ReceiptRecord(digest, payload))
        mounted[digest] = payload
    return ReceiptRegistry(registry.profile_binding_sha256, tuple(records))


def _verify_extension(before: ReceiptRegistry, after: ReceiptRegistry) -> None:
    if before.profile_binding_sha256 != after.profile_binding_sha256:
        raise ReceiptError("fresh recall executor changed the GLEW profile")
    for record in before.records:
        if after.resolve(record.digest, "prior fresh-recall receipt") != record.payload:
            raise ReceiptError("fresh recall executor changed an existing receipt")


class RememberedMotifKind(str, Enum):
    CONTENT = "content"
    EXPRESSION_CLOSE = "expression_close"


def remembered_motif_kind_receipt_payload(
    *,
    motif_receipt_sha256: str,
    kind: RememberedMotifKind,
    source_closed_experience_receipt_sha256: str,
) -> bytes:
    if not isinstance(kind, RememberedMotifKind):
        raise ReceiptError("remembered motif kind is not typed")
    for value, description in (
        (motif_receipt_sha256, "typed motif receipt"),
        (
            source_closed_experience_receipt_sha256,
            "typed motif source-experience receipt",
        ),
    ):
        sha256_digest(value, description)
    return _canonical_bytes(
        {
            "kind": kind.value,
            "motif_receipt_sha256": motif_receipt_sha256,
            "schema": "glew.recall.remembered_motif_kind.v1",
            "source_closed_experience_receipt_sha256": (
                source_closed_experience_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class RememberedMotifKindAuthority:
    motif_receipt_sha256: str
    kind: RememberedMotifKind
    source_closed_experience_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return remembered_motif_kind_receipt_payload(
            motif_receipt_sha256=self.motif_receipt_sha256,
            kind=self.kind,
            source_closed_experience_receipt_sha256=(
                self.source_closed_experience_receipt_sha256
            ),
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.motif_receipt_sha256,
            "typed remembered motif receipt",
        )
        receipt_registry.resolve(
            self.source_closed_experience_receipt_sha256,
            "typed remembered motif source-experience receipt",
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "remembered motif-kind authority receipt",
        )
        if mounted != self.payload() or receipt_sha256(mounted) != self.authority_receipt_sha256:
            raise ReceiptError("remembered motif kind differs from exact receipt")


@dataclass(frozen=True, slots=True)
class RecallClosedExperienceExecution:
    bundle: ClosedExperienceProviderBundle
    expression_evaluation: FieldExpressionEvaluation
    language_evidence: PortTransportEvidence
    sensory_evidence: tuple[PortTransportEvidence, ...]
    typed_language_input: TypedLanguageFrozenKernelInput
    commit_decision: CommitDecision
    receipt_registry: ReceiptRegistry

    def verify(self, prior_registry: ReceiptRegistry) -> None:
        _verify_extension(prior_registry, self.receipt_registry)
        if self.bundle.status is not ProviderStatus.READY:
            raise ReceiptError("fresh recall closed-experience bundle is not READY")
        if self.bundle.experience_origin.kind is not ExperienceOriginKind.SELF_GENERATED_RECALL:
            raise ReceiptError("fresh recall executor returned a non-recall origin")
        if self.bundle.event_support.exact_r_event != 0:
            raise ReceiptError("fresh recall executor returned nonzero fresh R_event")
        self.bundle.event_support_evaluation.verify(
            origin=self.bundle.experience_origin,
            topology=self.bundle.sealed.expression.topology,
            closed_experience_receipt_sha256=(
                self.bundle.closed_experience.authority_receipt_sha256
            ),
            expression=self.bundle.sealed.expression,
            receipt_registry=self.receipt_registry,
        )
        self.expression_evaluation.verify()
        self.typed_language_input.verify()
        self.commit_decision.verify()
        if (
            self.expression_evaluation.status
            is not ExpressionEvaluationStatus.CERTIFIED
            or self.expression_evaluation.expression_receipt_sha256
            != self.bundle.sealed.expression.receipt_sha256
        ):
            raise ReceiptError("fresh recall expression did not certify")
        mounted_evaluation = self.receipt_registry.resolve(
            self.expression_evaluation.receipt_sha256,
            "fresh recall expression-evaluation receipt",
        )
        if mounted_evaluation != self.expression_evaluation.receipt_payload:
            raise ReceiptError("fresh recall expression evaluation changed")
        if self.language_evidence.lane_id != "language":
            raise ReceiptError("fresh recall language evidence is not language")
        if not isinstance(self.sensory_evidence, tuple):
            raise ReceiptError("fresh recall sensory evidence must be immutable")
        if any(value.lane_id == "language" for value in self.sensory_evidence):
            raise ReceiptError("fresh recall sensory records hide language evidence")
        for value in (self.language_evidence, *self.sensory_evidence):
            value.verify(self.receipt_registry)
        bundle_language = tuple(
            value for value in self.bundle.evidence if value.lane_id == "language"
        )
        if not bundle_language:
            raise ReceiptError("fresh recall bundle lacks language field evidence")
        terminal_language = max(
            bundle_language,
            key=lambda value: (
                value.provenance.source_timestamp,
                value.provenance.source_index,
            ),
        )
        if terminal_language != self.language_evidence:
            raise ReceiptError("fresh recall did not expose the terminal language field")
        actual_sensory = tuple(
            value for value in self.bundle.evidence if value.lane_id != "language"
        )
        if actual_sensory != self.sensory_evidence:
            raise ReceiptError("fresh recall bundle changed the exact cited senses")
        if (
            self.commit_decision.closed_experience_receipt_sha256
            != self.bundle.closed_experience.authority_receipt_sha256
            or self.commit_decision.topology_authority_receipt_sha256
            != self.bundle.sealed.expression.topology.authority_receipt_sha256
        ):
            raise ReceiptError("fresh recall commit belongs to another full field")
        mounted_commit = self.receipt_registry.resolve(
            self.commit_decision.receipt_sha256,
            "fresh recall commit-decision receipt",
        )
        if mounted_commit != self.commit_decision.receipt_payload:
            raise ReceiptError("fresh recall commit decision changed")


class FreshRecallClosedExperienceExecutor(Protocol):
    def execute(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> RecallClosedExperienceExecution: ...


def verify_fresh_recall_archive_lineage_authority(
    *,
    episode: "RecallStoryEpisode",
    archive_lineage: "FreshRecallArchiveLineageAuthority",
    fresh_closed_experience_receipt_sha256: str,
    fresh_sensory_evidence: tuple[PortTransportEvidence, ...],
    source_binding: MotifOutputBinding,
    receipt_registry: ReceiptRegistry,
) -> None:
    """Verify exact raw-sense continuity across a six-lane topology change."""

    # Local import avoids a module-initialization cycle: the concrete executor
    # implements this provider's protocol and therefore imports this module.
    from .fresh_recall_executor import FreshRecallArchiveLineageAuthority

    if not isinstance(archive_lineage, FreshRecallArchiveLineageAuthority):
        raise ReceiptError("fresh recall archive lineage has invalid type")
    if not isinstance(fresh_sensory_evidence, tuple):
        raise ReceiptError("fresh recall sensory lineage must be immutable")
    sha256_digest(
        fresh_closed_experience_receipt_sha256,
        "fresh recall lineage closed experience",
    )
    source_binding.verify(receipt_registry)
    archive_lineage.verify(
        episode=episode,
        fresh_sensory_evidence=fresh_sensory_evidence,
        receipt_registry=receipt_registry,
    )
    if archive_lineage.source_binding_receipt_sha256 != (
        source_binding.binding_receipt_sha256
    ):
        raise ReceiptError("fresh recall lineage belongs to another source binding")
    if archive_lineage.fresh_closed_experience_receipt_sha256 != (
        fresh_closed_experience_receipt_sha256
    ):
        raise ReceiptError(
            "fresh recall lineage belongs to another fresh closed experience"
        )

    archived_receipts = tuple(
        sorted(
            value.archived_evidence_receipt_sha256
            for value in archive_lineage.entries
        )
    )
    if archived_receipts != source_binding.sensory_evidence_receipt_sha256s:
        raise ReceiptError(
            "fresh recall lineage omits or substitutes archived sensory evidence"
        )
    fresh_receipts = tuple(
        sorted(
            value.fresh_evidence_receipt_sha256
            for value in archive_lineage.entries
        )
    )
    actual_fresh_receipts = tuple(
        sorted(
            value.evidence_receipt_sha256
            for value in fresh_sensory_evidence
        )
    )
    if fresh_receipts != actual_fresh_receipts:
        raise ReceiptError(
            "fresh recall lineage omits or substitutes fresh sensory evidence"
        )
    lineage_keys = tuple(
        (value.lane_id, value.port_id) for value in archive_lineage.entries
    )
    actual_keys = tuple(
        sorted((value.lane_id, value.port_id) for value in fresh_sensory_evidence)
    )
    if lineage_keys != actual_keys or len(lineage_keys) != 5:
        raise ReceiptError("fresh recall lineage does not exactly cover five senses")
    if any(
        value.archived_raw_record_sha256 != value.fresh_raw_record_sha256
        for value in archive_lineage.entries
    ):
        raise ReceiptError("fresh recall changed an archived raw L0-L4 trace")


def verify_fresh_recall_archive_lineage(
    *,
    execution: RecallClosedExperienceExecution,
    source_binding: MotifOutputBinding,
) -> None:
    """Require and verify the executor's exact archive-lineage authority."""

    # Local import avoids a module-initialization cycle.
    from .fresh_recall_executor import LineagedRecallClosedExperienceExecution

    if not isinstance(execution, LineagedRecallClosedExperienceExecution):
        raise ReceiptError(
            "fresh recall executor omitted exact archive-lineage authority"
        )
    verify_fresh_recall_archive_lineage_authority(
        episode=execution.episode,
        archive_lineage=execution.archive_lineage,
        fresh_closed_experience_receipt_sha256=(
            execution.bundle.closed_experience.authority_receipt_sha256
        ),
        fresh_sensory_evidence=execution.sensory_evidence,
        source_binding=source_binding,
        receipt_registry=execution.receipt_registry,
    )


class FullFieldFreshRecallProvider:
    """Stateless per-scalar full-field recall transition provider."""

    operator_id = FRESH_RECALL_SELF_SENSE_OPERATOR_ID

    def __init__(
        self,
        *,
        provider_id: str,
        profile_binding_sha256: str,
        executor: FreshRecallClosedExperienceExecutor,
        motif_kinds: tuple[RememberedMotifKindAuthority, ...],
        authority_receipt_sha256: str,
    ) -> None:
        self.provider_id = require_identifier(provider_id, "fresh recall provider id")
        self.profile_binding_sha256 = sha256_digest(
            profile_binding_sha256,
            "fresh recall provider profile receipt",
        )
        self.executor = executor
        if not isinstance(motif_kinds, tuple):
            raise ReceiptError("fresh recall motif-kind authorities must be immutable")
        by_motif: dict[str, RememberedMotifKindAuthority] = {}
        for value in motif_kinds:
            if value.motif_receipt_sha256 in by_motif:
                raise ReceiptError("fresh recall motif has duplicate kind authority")
            by_motif[value.motif_receipt_sha256] = value
        self._motif_kinds = by_motif
        self.authority_receipt_sha256 = sha256_digest(
            authority_receipt_sha256,
            "fresh recall provider authority receipt",
        )

    def settle(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        output_binding_bank: MotifBindingBank,
        stable_mode_motif_bank: StableModeMotifBank,
        receipt_registry: ReceiptRegistry,
    ) -> RecallTransitionSettlement:
        provider_payload = fresh_recall_provider_authority_receipt_payload(
            provider_id=self.provider_id,
            profile_binding_sha256=self.profile_binding_sha256,
        )
        mounted_provider = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "fresh recall provider authority receipt",
        )
        if mounted_provider != provider_payload:
            raise ReceiptError("fresh recall provider authority changed")
        execution = self.executor.execute(
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=receipt_registry,
        )
        if not isinstance(execution, RecallClosedExperienceExecution):
            raise ReceiptError("fresh recall executor returned an untyped result")
        execution.verify(receipt_registry)
        verify_fresh_recall_archive_lineage(
            execution=execution,
            source_binding=source_binding,
        )

        bundle = execution.bundle
        recognition = bundle.sealed.recognition
        commit = evaluate_commit_boundary(
            topology=bundle.sealed.expression.topology,
            recognition=recognition,
            l6_evaluation=bundle.l6_evaluation,
            l6_scope=bundle.l6_scope,
            closed_experience=bundle.closed_experience,
            safe_mode=bundle.safe_mode,
            event_support=bundle.event_support,
            evidence=bundle.evidence,
            l5_applicability=bundle.l5_applicability,
            global_uf_validation=bundle.global_uf_validation,
            receipt_registry=execution.receipt_registry,
        )
        if commit != execution.commit_decision:
            raise ReceiptError("fresh recall executor commit changed on recomputation")
        if commit.status is not CommitStatus.COMMIT or commit.selected_mode_receipt_sha256 is None:
            raise ReceiptError("fresh recall full field did not commit one mode")
        registry = _extend_registry(
            execution.receipt_registry,
            (commit.receipt_payload,),
        )
        stable = stable_mode_motif_bank.resolve_unique(
            commit.selected_mode_receipt_sha256,
            registry,
        )
        motif_kind = self._motif_kinds.get(stable.motif_receipt_sha256)
        if motif_kind is None:
            raise ReceiptError("selected motif lacks a typed content/close authority")
        motif_kind.verify(registry)

        language = execution.language_evidence
        sensory = execution.sensory_evidence
        transduction_payload = recalled_language_transduction_receipt_payload(
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
        )
        transduction_digest = receipt_sha256(transduction_payload)
        expression = bundle.sealed.expression
        input_payload = recall_expression_input_receipt_payload(
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=transduction_digest,
            map_injection_receipt_sha256s=tuple(
                value.injection.receipt_sha256 for value in expression.steps
            ),
            expression_receipt_sha256=expression.receipt_sha256,
        )
        input_digest = receipt_sha256(input_payload)
        state_payload = _canonical_bytes(
            {
                "commit_decision_receipt_sha256": commit.receipt_sha256,
                "source_state_receipt_sha256": (
                    source_event.result_state_receipt_sha256
                ),
                "stable_mode_motif_binding_receipt_sha256": (
                    stable.binding_receipt_sha256
                ),
                "schema": "glew.recall.fresh_result_state.v1",
            }
        )
        result_state = receipt_sha256(state_payload)
        edge_payload = _canonical_bytes(
            {
                "result_state_receipt_sha256": result_state,
                "source_event_receipt_sha256": source_event.event_receipt_sha256,
                "source_state_receipt_sha256": (
                    source_event.result_state_receipt_sha256
                ),
                "schema": "glew.recall.fresh_transition_edge.v1",
            }
        )
        edge_digest = receipt_sha256(edge_payload)
        event_kind = (
            MotifEventKind.EXPRESSION_CLOSE
            if motif_kind.kind is RememberedMotifKind.EXPRESSION_CLOSE
            else MotifEventKind.CONTENT
        )
        close_payload = None
        close_digest = None
        if event_kind is MotifEventKind.EXPRESSION_CLOSE:
            close_payload = expression_close_authority_receipt_payload(
                expression_id=source_event.expression_id,
                close_motif_receipt_sha256=stable.motif_receipt_sha256,
            )
            close_digest = receipt_sha256(close_payload)
        event_identity = _canonical_bytes(
            {
                "commit_decision_receipt_sha256": commit.receipt_sha256,
                "source_event_receipt_sha256": source_event.event_receipt_sha256,
                "stable_mode_motif_binding_receipt_sha256": (
                    stable.binding_receipt_sha256
                ),
            }
        )
        event_id = f"fresh-recall-{receipt_sha256(event_identity)}"
        event_payload = committed_motif_event_receipt_payload(
            expression_id=source_event.expression_id,
            event_id=event_id,
            event_kind=event_kind,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=stable.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                commit.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=(
                stable.source_fact_strand_receipt_sha256
            ),
            sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            full_field_state_receipt_sha256=(
                execution.expression_evaluation.receipt_sha256
            ),
            full_field_evaluation_identity_sha256=(
                expression.field_evaluation_identity_sha256
            ),
            field_commit_receipt_sha256=commit.receipt_sha256,
            dominant_motif_commit_receipt_sha256=stable.binding_receipt_sha256,
            corrected_l6_lock_receipt_sha256=(
                commit.l6_evaluation_receipt_sha256
            ),
            output_binding_bank_receipt_sha256=(
                output_binding_bank.bank_receipt_sha256
            ),
            source_state_receipt_sha256=(
                source_event.result_state_receipt_sha256
            ),
            transition_edge_receipt_sha256=edge_digest,
            result_state_receipt_sha256=result_state,
            expression_close_authority_receipt_sha256=close_digest,
        )
        generated = [
            transduction_payload,
            input_payload,
            state_payload,
            edge_payload,
            event_payload,
        ]
        if close_payload is not None:
            generated.append(close_payload)
        registry = _extend_registry(registry, tuple(generated))
        event = CommittedMotifEvent(
            expression_id=source_event.expression_id,
            event_id=event_id,
            event_kind=event_kind,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=stable.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                commit.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=(
                stable.source_fact_strand_receipt_sha256
            ),
            sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            full_field_state_receipt_sha256=(
                execution.expression_evaluation.receipt_sha256
            ),
            full_field_evaluation_identity_sha256=(
                expression.field_evaluation_identity_sha256
            ),
            field_commit_receipt_sha256=commit.receipt_sha256,
            dominant_motif_commit_receipt_sha256=stable.binding_receipt_sha256,
            corrected_l6_lock_receipt_sha256=(
                commit.l6_evaluation_receipt_sha256
            ),
            output_binding_bank_receipt_sha256=(
                output_binding_bank.bank_receipt_sha256
            ),
            source_state_receipt_sha256=(
                source_event.result_state_receipt_sha256
            ),
            transition_edge_receipt_sha256=edge_digest,
            result_state_receipt_sha256=result_state,
            expression_close_authority_receipt_sha256=close_digest,
            event_receipt_sha256=receipt_sha256(event_payload),
        )
        reason = "fresh full-field recall committed one stable next motif"
        settlement_payload = recall_transition_settlement_receipt_payload(
            status=RecallTransitionStatus.COMMITTED,
            provider_id=self.provider_id,
            provider_authority_receipt_sha256=self.authority_receipt_sha256,
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=transduction_digest,
            expression_input_authority_receipt_sha256=input_digest,
            expression_receipt_sha256=expression.receipt_sha256,
            expression_evaluation_receipt_sha256=(
                execution.expression_evaluation.receipt_sha256
            ),
            expression_recognition_receipt_sha256=recognition.receipt_sha256,
            commit_decision_receipt_sha256=commit.receipt_sha256,
            stable_mode_motif_binding_receipt_sha256=(
                stable.binding_receipt_sha256
            ),
            next_event_receipt_sha256=event.event_receipt_sha256,
            missing_operator_id=None,
            reason=reason,
        )
        settlement_digest = receipt_sha256(settlement_payload)
        registry = _extend_registry(registry, (settlement_payload,))
        return RecallTransitionSettlement(
            status=RecallTransitionStatus.COMMITTED,
            provider_id=self.provider_id,
            provider_authority_receipt_sha256=self.authority_receipt_sha256,
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence=sensory,
            language_transport_evidence=language,
            language_transduction_receipt_sha256=transduction_digest,
            expression_input_authority_receipt_sha256=input_digest,
            expression=expression,
            expression_evaluation=execution.expression_evaluation,
            expression_recognition=recognition,
            commit_decision=commit,
            stable_mode_motif_binding_receipt_sha256=(
                stable.binding_receipt_sha256
            ),
            next_event=event,
            missing_operator_id=None,
            reason=reason,
            receipt_registry=registry,
            receipt_sha256=settlement_digest,
            receipt_payload=settlement_payload,
        )


__all__ = (
    "FreshRecallClosedExperienceExecutor",
    "FullFieldFreshRecallProvider",
    "RecallClosedExperienceExecution",
    "RememberedMotifKind",
    "RememberedMotifKindAuthority",
    "remembered_motif_kind_receipt_payload",
    "verify_fresh_recall_archive_lineage",
    "verify_fresh_recall_archive_lineage_authority",
)
