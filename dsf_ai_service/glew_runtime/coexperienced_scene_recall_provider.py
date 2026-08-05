"""Injected ``FreshRecallSelfSenseProvider`` over deterministic scene replay.

This module answers ``docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-
20260714-v1.md`` section 6.3.  It structurally satisfies
``recall_reentry.FreshRecallSelfSenseProvider`` so it drops straight into
``RememberedOutputProviders`` / ``run_clean_conversation_transaction`` with no
transaction-side change.

:meth:`CoexperiencedSceneRecallProvider.settle` mirrors ``fresh_recall_
provider.FullFieldFreshRecallProvider.settle`` exactly, with two differences
the design names:

* (a) it calls :meth:`CoexperiencedSceneRecallExecutor.execute` instead of the
  five-sense ``FreshRecallClosedExperienceExecutor.execute``, consuming the
  lighter :class:`CoexperiencedSceneRecallExecution` (which carries the
  already-produced, already-verified self-recall commit -- so, unlike the
  five-sense provider, there is no ``ClosedExperienceProviderBundle`` to
  re-evaluate the commit from; the executor's commit is reused directly and is
  independently re-verified by the unchanged ``RecallTransitionSettlement.
  verify``);
* (b) it omits the ``verify_fresh_recall_archive_lineage`` step, which is
  structurally inapplicable -- there is no five-sense archive episode and no
  cross-universe raw-trace pairing to reconcile; the fresh evidence *is* the
  cited evidence.

Every settlement receipt is built with the unchanged ``recall_reentry.py``
builders, so the emitted ``RecallTransitionSettlement`` is byte-schema
identical to what the five-sense provider would emit and ``RecallTransition
Settlement.verify`` passes unchanged.

Live motif-kind classification
------------------------------
Whether the recalled next motif is CONTENT or EXPRESSION_CLOSE is read from
the live learned ``RememberedMotifKindAuthority`` tuple carried by the shared
:class:`LiveRecallState` (via the executor), because motifs are learned after
this provider is constructed (see the executor module docstring).  The
``motif_kinds`` constructor argument is retained for design-signature
compatibility and used as an additional cold-start seed; the live authorities
win.
"""

from __future__ import annotations

import json

from .commit import CommitStatus
from .fresh_recall_provider import (
    RememberedMotifKind,
    RememberedMotifKindAuthority,
)
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

from .coexperienced_scene_recall_executor import (
    CoexperiencedSceneRecallExecution,
    CoexperiencedSceneRecallExecutor,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_registry(registry: ReceiptRegistry, payloads: tuple[bytes, ...]) -> ReceiptRegistry:
    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("coexperienced scene recall generated an empty receipt")
        digest = receipt_sha256(payload)
        if digest in mounted:
            if mounted[digest] != payload:
                raise ReceiptError("coexperienced scene recall encountered a receipt collision")
            continue
        records.append(ReceiptRecord(digest, payload))
        mounted[digest] = payload
    return ReceiptRegistry(registry.profile_binding_sha256, tuple(records))


class CoexperiencedSceneRecallProvider:
    """Stateless per-scalar full-field recall provider over scene replay."""

    operator_id = FRESH_RECALL_SELF_SENSE_OPERATOR_ID

    def __init__(
        self,
        *,
        provider_id: str,
        profile_binding_sha256: str,
        executor: CoexperiencedSceneRecallExecutor,
        motif_kinds: tuple[RememberedMotifKindAuthority, ...] = (),
        authority_receipt_sha256: str,
    ) -> None:
        self.provider_id = require_identifier(provider_id, "coexperienced recall provider id")
        self.profile_binding_sha256 = sha256_digest(
            profile_binding_sha256,
            "coexperienced recall provider profile receipt",
        )
        if not isinstance(executor, CoexperiencedSceneRecallExecutor):
            raise ReceiptError("coexperienced recall provider requires a typed executor")
        self.executor = executor
        if not isinstance(motif_kinds, tuple):
            raise ReceiptError("coexperienced recall motif-kind authorities must be immutable")
        self._seed_motif_kinds = motif_kinds
        self.authority_receipt_sha256 = sha256_digest(
            authority_receipt_sha256,
            "coexperienced recall provider authority receipt",
        )

    def _motif_kind_lookup(self) -> dict[str, RememberedMotifKindAuthority]:
        """Build the motif -> kind lookup, live authorities winning over the
        cold-start seed (both are real ``RememberedMotifKindAuthority`` values;
        the live ones come from the engine's current learned state)."""

        by_motif: dict[str, RememberedMotifKindAuthority] = {}
        _, _, live = self.executor.live_recall_state.snapshot()
        for value in (*self._seed_motif_kinds, *live):
            if not isinstance(value, RememberedMotifKindAuthority):
                raise ReceiptError("coexperienced recall received an untyped motif-kind authority")
            existing = by_motif.get(value.motif_receipt_sha256)
            if existing is not None and existing != value:
                raise ReceiptError("coexperienced recall motif has conflicting kind authorities")
            by_motif[value.motif_receipt_sha256] = value
        return by_motif

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
            "coexperienced recall provider authority receipt",
        )
        if mounted_provider != provider_payload:
            raise ReceiptError("coexperienced recall provider authority changed")

        execution = self.executor.execute(
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=receipt_registry,
        )
        if not isinstance(execution, CoexperiencedSceneRecallExecution):
            raise ReceiptError("coexperienced recall executor returned an untyped result")
        execution.verify(receipt_registry)
        # (b) verify_fresh_recall_archive_lineage is deliberately omitted:
        # there is no five-sense archive episode and no cross-universe
        # raw-trace pairing to reconcile -- the regenerated evidence IS the
        # cited evidence, already asserted equal to the binding inside the
        # executor (design section 6.2 step 7).

        recognition = execution.recognition
        # The executor already produced and verified the self-recall commit
        # (there is no bundle to re-evaluate it from); reuse it directly.
        commit = execution.commit_decision
        if commit.status is not CommitStatus.COMMIT or commit.selected_mode_receipt_sha256 is None:
            raise ReceiptError("coexperienced recall full field did not commit one mode")
        winner = recognition.winner_mode_index
        if winner is None or winner >= len(recognition.pre_growth_bank.modes):
            raise ReceiptError("coexperienced recall recognition lacks a selected mode")
        selected_mode = recognition.pre_growth_bank.modes[winner]
        if selected_mode.receipt_sha256 != commit.selected_mode_receipt_sha256:
            raise ReceiptError(
                "coexperienced recall commit selected a different mode than recognition"
            )
        registry = _extend_registry(execution.receipt_registry, (commit.receipt_payload,))
        # Resolve the successor by the selected mode's field-evaluation identity
        # (content), never its bookkeeping-tainted full receipt: a fresh process
        # regrows this mode into a NEW receipt, so keying on the receipt would
        # fail to find the stored successor even for the identical physical field.
        stable = stable_mode_motif_bank.resolve_unique(
            selected_mode.source_expression.field_evaluation_identity_sha256,
            registry,
        )
        motif_kind = self._motif_kind_lookup().get(stable.motif_receipt_sha256)
        if motif_kind is None:
            raise ReceiptError("coexperienced recall selected motif lacks a typed content/close authority")
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
        expression = execution.sealed.expression
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
        event_id = f"coexperienced-recall-{receipt_sha256(event_identity)}"
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
        reason = "coexperienced scene recall committed one stable next motif"
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


__all__ = ("CoexperiencedSceneRecallProvider",)
