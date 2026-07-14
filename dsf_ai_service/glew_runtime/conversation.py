"""Atomic clean-generation GLEW conversation transaction.

The initial lived field expression is recognized and committed once.  Output
then enters the remembered-expression settlement boundary with exactly one
initial committed motif.  Every later scalar is produced only after a concrete
fresh-recall self-sense provider has returned language to the complete field,
obtained a new expression-mode result, and obtained a new full-field commit.

No intermediate scalar crosses this module.  Only the exact expression-close
settlement may release text; every unknown or inconsistent authority is typed
silence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .commit import (
    BinaryCommitAuthority,
    ClosedExperienceSeal,
    CommitDecision,
    CommitStatus,
    EventSupportAuthority,
    L5Applicability,
    L6ScopeAuthority,
    evaluate_commit_boundary,
)
from .expression_memory import ExpressionHMemEvaluator
from .expression_modes import (
    RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    ExpressionModeBank,
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)
from .expressions import ClosedExperienceFieldExpression
from .field import MountedFieldTopology, PortTransportEvidence
from .l6 import L6Evaluation
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)
from .output import CommittedMotifEvent, MotifBindingBank
from .recall_reentry import (
    FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
    CompleteExpressionResult,
    CompleteExpressionStatus,
    FreshRecallSelfSenseProvider,
    StableModeMotifBank,
    settle_complete_remembered_expression,
)


CONVERSATION_TRANSACTION_ID = "glew.atomic_fresh_reentry_conversation.v2"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    description: str,
) -> None:
    mounted = registry.resolve(digest, description)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{description} differs from mounted exact bytes")


class ConversationStatus(str, Enum):
    EXPRESSION_RELEASED = "expression_released"
    EXPLICIT_UNKNOWN_SILENCE = "explicit_unknown_silence"
    EXPLICIT_NO_COMMIT_SILENCE = "explicit_no_commit_silence"


@dataclass(frozen=True, slots=True)
class ConversationCommitProviders:
    """Independent facts consumed by the full-field commit boundary."""

    l6_evaluation: L6Evaluation
    l6_scope: L6ScopeAuthority
    closed_experience: ClosedExperienceSeal
    safe_mode: BinaryCommitAuthority
    event_support: EventSupportAuthority
    evidence: tuple[PortTransportEvidence, ...]
    l5_applicability: tuple[L5Applicability, ...]
    global_uf_validation: BinaryCommitAuthority


@dataclass(frozen=True, slots=True)
class RememberedOutputProviders:
    """One initial motif plus the physical provider for every later motif."""

    binding_bank: MotifBindingBank
    stable_mode_motif_bank: StableModeMotifBank
    initial_event: CommittedMotifEvent
    fresh_recall_provider: FreshRecallSelfSenseProvider

    def __post_init__(self) -> None:
        if not isinstance(self.binding_bank, MotifBindingBank):
            raise ReceiptError("conversation output requires a typed binding bank")
        if not isinstance(self.stable_mode_motif_bank, StableModeMotifBank):
            raise ReceiptError(
                "conversation output requires a typed stable mode/motif bank"
            )
        if not isinstance(self.initial_event, CommittedMotifEvent):
            raise ReceiptError("conversation output requires one typed initial event")
        provider = self.fresh_recall_provider
        if provider is None:
            raise ReceiptError("fresh recall self-sense provider is missing")
        if getattr(provider, "operator_id", None) != (
            FRESH_RECALL_SELF_SENSE_OPERATOR_ID
        ):
            raise ReceiptError("fresh recall provider uses an unratified operator")
        require_identifier(
            getattr(provider, "provider_id", None),
            "fresh recall provider id",
        )
        sha256_digest(
            getattr(provider, "authority_receipt_sha256", None),
            "fresh recall provider authority receipt",
        )
        if not callable(getattr(provider, "settle", None)):
            raise ReceiptError("fresh recall provider has no settlement operation")


def _conversation_result_payload(
    *,
    status: ConversationStatus,
    visible_text: str,
    topology_receipt_sha256: str,
    input_expression_receipt_sha256: str,
    recognition_receipt_sha256: str | None,
    commit_receipt_sha256: str | None,
    initial_event_receipt_sha256: str | None,
    complete_expression_receipt_sha256: str | None,
    final_output_settlement_receipt_sha256: str | None,
    transition_settlement_receipt_sha256s: tuple[str, ...],
    reason: str,
) -> bytes:
    return _canonical_bytes(
        {
            "commit_receipt_sha256": commit_receipt_sha256,
            "complete_expression_receipt_sha256": (
                complete_expression_receipt_sha256
            ),
            "final_output_settlement_receipt_sha256": (
                final_output_settlement_receipt_sha256
            ),
            "initial_event_receipt_sha256": initial_event_receipt_sha256,
            "input_expression_receipt_sha256": (
                input_expression_receipt_sha256
            ),
            "operator_id": CONVERSATION_TRANSACTION_ID,
            "reason": reason,
            "recognition_receipt_sha256": recognition_receipt_sha256,
            "release_rule": "exact_close_after_fresh_full_field_reentry_only",
            "schema": "glew.conversation.atomic_transaction_result.v2",
            "status": status.value,
            "topology_authority_receipt_sha256": topology_receipt_sha256,
            "transition_settlement_receipt_sha256s": list(
                transition_settlement_receipt_sha256s
            ),
            "visible_text": visible_text,
        }
    )


@dataclass(frozen=True, slots=True)
class ConversationTransactionResult:
    status: ConversationStatus
    visible_text: str
    topology_authority_receipt_sha256: str
    input_expression_receipt_sha256: str
    recognition_receipt_sha256: str | None
    commit_receipt_sha256: str | None
    initial_event_receipt_sha256: str | None
    complete_expression_receipt_sha256: str | None
    final_output_settlement_receipt_sha256: str | None
    transition_settlement_receipt_sha256s: tuple[str, ...]
    reason: str
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def silent(self) -> bool:
        return self.visible_text == ""

    def verify(self) -> None:
        expected = _conversation_result_payload(
            status=self.status,
            visible_text=self.visible_text,
            topology_receipt_sha256=self.topology_authority_receipt_sha256,
            input_expression_receipt_sha256=(
                self.input_expression_receipt_sha256
            ),
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            commit_receipt_sha256=self.commit_receipt_sha256,
            initial_event_receipt_sha256=self.initial_event_receipt_sha256,
            complete_expression_receipt_sha256=(
                self.complete_expression_receipt_sha256
            ),
            final_output_settlement_receipt_sha256=(
                self.final_output_settlement_receipt_sha256
            ),
            transition_settlement_receipt_sha256s=(
                self.transition_settlement_receipt_sha256s
            ),
            reason=self.reason,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != (
            self.receipt_sha256
        ):
            raise ReceiptError(
                "conversation transaction differs from canonical receipt"
            )
        if self.status is ConversationStatus.EXPRESSION_RELEASED:
            if (
                not self.visible_text
                or self.complete_expression_receipt_sha256 is None
                or self.final_output_settlement_receipt_sha256 is None
                or self.initial_event_receipt_sha256 is None
            ):
                raise ReceiptError("released conversation lacks exact closed output")
        elif self.visible_text:
            raise ReceiptError("silent conversation exposed private staged text")


def _make_result(
    *,
    status: ConversationStatus,
    visible_text: str,
    topology: MountedFieldTopology,
    input_expression: ClosedExperienceFieldExpression,
    recognition: ExpressionModeBoundaryResult | None,
    commit: CommitDecision | None,
    initial_event: CommittedMotifEvent | None,
    complete_expression: CompleteExpressionResult | None,
    reason: str,
) -> ConversationTransactionResult:
    payload = _conversation_result_payload(
        status=status,
        visible_text=visible_text,
        topology_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=input_expression.receipt_sha256,
        recognition_receipt_sha256=(
            None if recognition is None else recognition.receipt_sha256
        ),
        commit_receipt_sha256=None if commit is None else commit.receipt_sha256,
        initial_event_receipt_sha256=(
            None if initial_event is None else initial_event.event_receipt_sha256
        ),
        complete_expression_receipt_sha256=(
            None if complete_expression is None else complete_expression.receipt_sha256
        ),
        final_output_settlement_receipt_sha256=(
            None
            if complete_expression is None
            else complete_expression.final_output_settlement_receipt_sha256
        ),
        transition_settlement_receipt_sha256s=(
            ()
            if complete_expression is None
            else complete_expression.transition_settlement_receipt_sha256s
        ),
        reason=reason,
    )
    result = ConversationTransactionResult(
        status=status,
        visible_text=visible_text,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=input_expression.receipt_sha256,
        recognition_receipt_sha256=(
            None if recognition is None else recognition.receipt_sha256
        ),
        commit_receipt_sha256=None if commit is None else commit.receipt_sha256,
        initial_event_receipt_sha256=(
            None if initial_event is None else initial_event.event_receipt_sha256
        ),
        complete_expression_receipt_sha256=(
            None if complete_expression is None else complete_expression.receipt_sha256
        ),
        final_output_settlement_receipt_sha256=(
            None
            if complete_expression is None
            else complete_expression.final_output_settlement_receipt_sha256
        ),
        transition_settlement_receipt_sha256s=(
            ()
            if complete_expression is None
            else complete_expression.transition_settlement_receipt_sha256s
        ),
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def _h_mem_provider_map(
    *,
    bank: ExpressionModeBank,
    input_expression: ClosedExperienceFieldExpression,
    providers: tuple[ExpressionHMemEvaluator, ...],
    receipt_registry: ReceiptRegistry,
) -> dict[str, ExpressionHMemEvaluator]:
    if not isinstance(providers, tuple) or not all(
        isinstance(value, ExpressionHMemEvaluator) for value in providers
    ):
        raise ReceiptError("H_mem providers must be independently typed objects")
    digests = tuple(value.provider_expression_receipt_sha256 for value in providers)
    if digests != tuple(sorted(set(digests))):
        raise ReceiptError("H_mem providers must be unique canonical receipt order")
    expressions = tuple(mode.source_expression for mode in bank.modes) + (
        input_expression,
    )
    required = tuple(
        sorted(
            {
                leaf.provider_expression_receipt_sha256
                for expression in expressions
                for step in expression.steps
                for leaf in step.hermitian_leaves
            }
        )
    )
    if digests != required:
        raise ReceiptError(
            "H_mem providers do not exactly cover expression leaves"
        )
    result: dict[str, ExpressionHMemEvaluator] = {}
    for provider in providers:
        provider.verify()
        mounted = receipt_registry.resolve(
            provider.provider_expression_receipt_sha256,
            "conversation H_mem provider receipt",
        )
        provider_mounted = provider.receipt_registry.resolve(
            provider.provider_expression_receipt_sha256,
            "H_mem provider receipt",
        )
        if mounted != provider_mounted:
            raise ReceiptError(
                "conversation and H_mem provider mount different formula bytes"
            )
        result[provider.provider_expression_receipt_sha256] = provider
    return result


def _preflight_initial_output(
    *,
    output: RememberedOutputProviders,
    recognition: ExpressionModeBoundaryResult,
    commit: CommitDecision,
    receipt_registry: ReceiptRegistry,
) -> None:
    event = output.initial_event
    event.verify(receipt_registry)
    output.binding_bank.verify_for_motif(
        receipt_registry,
        event.motif_receipt_sha256,
    )
    if event.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
        raise ReceiptError("initial event belongs to another GLEW profile")
    if event.output_binding_bank_receipt_sha256 != (
        output.binding_bank.bank_receipt_sha256
    ):
        raise ReceiptError("initial event cites a different output binding bank")
    if event.field_commit_receipt_sha256 != commit.receipt_sha256:
        raise ReceiptError("initial event cites a different full-field commit")
    if event.closed_experience_receipt_sha256 != (
        commit.closed_experience_receipt_sha256
    ):
        raise ReceiptError("initial event cites a different closed experience")
    if event.corrected_l6_lock_receipt_sha256 != (
        commit.l6_evaluation_receipt_sha256
    ):
        raise ReceiptError("initial event cites a different corrected L6 result")
    if event.full_field_state_receipt_sha256 != (
        recognition.input_expression_receipt_sha256
    ):
        raise ReceiptError("initial event cites a different full-field expression")
    if not set(event.sensory_evidence_receipt_sha256s).issubset(
        set(commit.evidence_receipt_sha256s)
    ):
        raise ReceiptError("initial event sensory evidence is outside the commit")
    selected_receipt = commit.selected_mode_receipt_sha256
    if selected_receipt is None:
        raise ReceiptError("initial committed event has no selected stable mode")
    # The initial event names the root transition's own successor.  Resolve it
    # by the event's own source-relation Fact Strand (its ``fact_strand_
    # receipt_sha256`` is exactly the root binding's ``source_fact_strand``),
    # so a root mode that owns sibling successors (owner Requirement 2) does
    # not make this verification ambiguous.
    stable = output.stable_mode_motif_bank.resolve_for_source_relation(
        mode_receipt_sha256=selected_receipt,
        source_fact_strand_receipt_sha256=event.fact_strand_receipt_sha256,
        receipt_registry=receipt_registry,
    )
    if (
        stable.motif_receipt_sha256 != event.motif_receipt_sha256
        or stable.binding_receipt_sha256
        != event.dominant_motif_commit_receipt_sha256
    ):
        raise ReceiptError("initial event is not the selected mode's stable motif")


def run_clean_conversation_transaction(
    *,
    topology: MountedFieldTopology,
    mode_bank: ExpressionModeBank,
    input_expression: ClosedExperienceFieldExpression,
    h_mem_providers: tuple[ExpressionHMemEvaluator, ...],
    commit_providers: ConversationCommitProviders,
    remembered_output: RememberedOutputProviders,
    receipt_registry: ReceiptRegistry,
) -> ConversationTransactionResult:
    """Release only one exact-close expression after fresh field re-entry."""

    recognition: ExpressionModeBoundaryResult | None = None
    commit: CommitDecision | None = None
    initial_event: CommittedMotifEvent | None = None
    try:
        topology.verify(receipt_registry)
        mode_bank.verify(topology=topology, receipt_registry=receipt_registry)
        input_expression.verify(receipt_registry)
        h_mem = _h_mem_provider_map(
            bank=mode_bank,
            input_expression=input_expression,
            providers=h_mem_providers,
            receipt_registry=receipt_registry,
        )
        recognition = evaluate_expression_mode_boundary(
            topology=topology,
            bank=mode_bank,
            input_expression=input_expression,
            receipt_registry=receipt_registry,
            hermitian_evaluators=h_mem,
            # Live experience must GROW when the full field is structurally
            # distinct from every existing mode (owner Requirement 1), not
            # misrecognize it as the nearest reference.
            recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
        )
        recognition.verify()
        recognition.pre_growth_bank.verify(
            topology=topology,
            receipt_registry=receipt_registry,
        )
        recognition.post_growth_bank.verify(
            topology=topology,
            receipt_registry=receipt_registry,
        )
        if recognition.status is ExpressionRecognitionStatus.UNKNOWN:
            return _make_result(
                status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
                visible_text="",
                topology=topology,
                input_expression=input_expression,
                recognition=recognition,
                commit=None,
                initial_event=None,
                complete_expression=None,
                reason=f"recognition_UNKNOWN:{recognition.reason}",
            )
        if recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
            return _make_result(
                status=ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE,
                visible_text="",
                topology=topology,
                input_expression=input_expression,
                recognition=recognition,
                commit=None,
                initial_event=None,
                complete_expression=None,
                reason=f"recognition_{recognition.status.value}",
            )

        commit = evaluate_commit_boundary(
            topology=topology,
            recognition=recognition,
            l6_evaluation=commit_providers.l6_evaluation,
            l6_scope=commit_providers.l6_scope,
            closed_experience=commit_providers.closed_experience,
            safe_mode=commit_providers.safe_mode,
            event_support=commit_providers.event_support,
            evidence=commit_providers.evidence,
            l5_applicability=commit_providers.l5_applicability,
            global_uf_validation=commit_providers.global_uf_validation,
            receipt_registry=receipt_registry,
        )
        commit.verify()
        _mounted_exact(
            receipt_registry,
            commit.receipt_sha256,
            commit.receipt_payload,
            "conversation full-field commit receipt",
        )
        if commit.status is CommitStatus.UNKNOWN_NO_COMMIT:
            return _make_result(
                status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
                visible_text="",
                topology=topology,
                input_expression=input_expression,
                recognition=recognition,
                commit=commit,
                initial_event=None,
                complete_expression=None,
                reason="commit_UNKNOWN:" + ",".join(commit.findings),
            )
        if commit.status is not CommitStatus.COMMIT:
            return _make_result(
                status=ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE,
                visible_text="",
                topology=topology,
                input_expression=input_expression,
                recognition=recognition,
                commit=commit,
                initial_event=None,
                complete_expression=None,
                reason="commit_no_commit:" + ",".join(commit.findings),
            )
        winner = recognition.winner_mode_index
        if (
            winner is None
            or commit.expression_recognition_receipt_sha256
            != recognition.receipt_sha256
            or commit.pre_growth_expression_bank_receipt_sha256
            != recognition.pre_growth_bank.receipt_sha256
            or commit.selected_mode_index != winner
            or commit.selected_mode_receipt_sha256
            != recognition.pre_growth_bank.modes[winner].receipt_sha256
        ):
            raise ReceiptError("commit selected a different expression mode")

        initial_event = remembered_output.initial_event
        _preflight_initial_output(
            output=remembered_output,
            recognition=recognition,
            commit=commit,
            receipt_registry=receipt_registry,
        )
        complete = settle_complete_remembered_expression(
            expression_id=initial_event.expression_id,
            initial_event=initial_event,
            output_binding_bank=remembered_output.binding_bank,
            stable_mode_motif_bank=remembered_output.stable_mode_motif_bank,
            receipt_registry=receipt_registry,
            provider=remembered_output.fresh_recall_provider,
        )
        if complete.status is CompleteExpressionStatus.UNKNOWN_SILENCE:
            return _make_result(
                status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
                visible_text="",
                topology=topology,
                input_expression=input_expression,
                recognition=recognition,
                commit=commit,
                initial_event=initial_event,
                complete_expression=complete,
                reason=f"fresh_reentry_UNKNOWN:{complete.reason}",
            )
        if complete.status is not CompleteExpressionStatus.RELEASED:
            raise ReceiptError("complete-expression settlement has an untyped status")
        return _make_result(
            status=ConversationStatus.EXPRESSION_RELEASED,
            visible_text=complete.text,
            topology=topology,
            input_expression=input_expression,
            recognition=recognition,
            commit=commit,
            initial_event=initial_event,
            complete_expression=complete,
            reason="exact close released after every scalar re-entered the full field",
        )
    except ReceiptError as error:
        return _make_result(
            status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
            visible_text="",
            topology=topology,
            input_expression=input_expression,
            recognition=recognition,
            commit=commit,
            initial_event=initial_event,
            complete_expression=None,
            reason=f"receipt_failure:{error}",
        )


__all__ = (
    "CONVERSATION_TRANSACTION_ID",
    "ConversationCommitProviders",
    "ConversationStatus",
    "ConversationTransactionResult",
    "RememberedOutputProviders",
    "run_clean_conversation_transaction",
)
