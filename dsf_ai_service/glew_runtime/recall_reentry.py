"""Fresh recall self-sense re-entry and complete-expression settlement.

This module contains no continuation policy.  It repeatedly accepts only a
provider-certified chain:

    exact staged language binding + that motif's cited sensory evidence
    -> full closed field expression
    -> certified unique expression-mode recognition
    -> full-field commit
    -> stable mode/motif binding
    -> next committed motif event

The expression remains private inside :class:`RememberedExpressionActuator`.
The first missing, ambiguous, non-commit, or inconsistent authority returns
typed UNKNOWN silence.  There is no suffix walk, vocabulary lookup, timeout,
count cap, random choice, or fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Protocol

from .commit import COMMIT_OPERATOR_ID, CommitDecision, CommitStatus
from .expression_modes import (
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
)
from .expressions import (
    ClosedExperienceFieldExpression,
    ExpressionEvaluationStatus,
    FieldExpressionEvaluation,
)
from .field import PortTransportEvidence
from .model import (
    ReceiptError,
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
    OutputBindingKind,
    OutputStatus,
    RememberedExpressionActuator,
)


FRESH_RECALL_SELF_SENSE_OPERATOR_ID = (
    "glew.recall.fresh_self_sense_full_field_reentry.v1"
)
RECALLED_LANGUAGE_TRANSDUCTION_OPERATOR_ID = (
    "glew.recall.exact_binding_language_transport.v1"
)


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


def _strict_transition_context(payload: bytes) -> dict[str, object]:
    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ReceiptError("stable transition context repeats a JSON key")
            value[key] = item
        return value

    try:
        parsed = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("stable transition context is not canonical JSON") from exc
    if not isinstance(parsed, dict) or _canonical_bytes(parsed) != payload:
        raise ReceiptError("stable transition context is not canonical JSON bytes")
    if parsed.get("schema") != TRANSITION_CONTEXT_SCHEMA:
        raise ReceiptError("stable transition context has another schema")
    return parsed


def _require_registry_extension(
    before: ReceiptRegistry,
    after: ReceiptRegistry,
) -> None:
    if before.profile_binding_sha256 != after.profile_binding_sha256:
        raise ReceiptError("recall provider changed the mounted GLEW profile")
    for record in before.records:
        if after.resolve(record.digest, "prior recall receipt") != record.payload:
            raise ReceiptError("recall provider altered an already mounted receipt")


def fresh_recall_provider_authority_receipt_payload(
    *,
    provider_id: str,
    profile_binding_sha256: str,
) -> bytes:
    require_identifier(provider_id, "recall provider id")
    sha256_digest(profile_binding_sha256, "recall provider profile receipt")
    return _canonical_bytes(
        {
            "operator_id": FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
            "profile_binding_sha256": profile_binding_sha256,
            "provider_id": provider_id,
            "scope": "fresh_full_field_reentry_only_no_continuation_policy",
            "schema": "glew.recall.self_sense_provider_authority.v1",
        }
    )


def recalled_language_transduction_receipt_payload(
    *,
    source_binding_receipt_sha256: str,
    language_transport_evidence_receipt_sha256: str,
) -> bytes:
    sha256_digest(source_binding_receipt_sha256, "source language binding receipt")
    sha256_digest(
        language_transport_evidence_receipt_sha256,
        "recalled language transport evidence receipt",
    )
    return _canonical_bytes(
        {
            "language_transport_evidence_receipt_sha256": (
                language_transport_evidence_receipt_sha256
            ),
            "operator_id": RECALLED_LANGUAGE_TRANSDUCTION_OPERATOR_ID,
            "source_binding_receipt_sha256": source_binding_receipt_sha256,
            "scope": "exact_14_trit_binding_to_language_port_transport",
            "schema": "glew.recall.language_transduction_authority.v1",
        }
    )


def recall_expression_input_receipt_payload(
    *,
    source_event_receipt_sha256: str,
    staged_output_settlement_receipt_sha256: str,
    source_binding_receipt_sha256: str,
    cited_sensory_evidence_receipt_sha256s: tuple[str, ...],
    language_transport_evidence_receipt_sha256: str,
    language_transduction_receipt_sha256: str,
    map_injection_receipt_sha256s: tuple[str, ...],
    expression_receipt_sha256: str,
) -> bytes:
    for value, name in (
        (source_event_receipt_sha256, "source committed-event receipt"),
        (
            staged_output_settlement_receipt_sha256,
            "staged output settlement receipt",
        ),
        (source_binding_receipt_sha256, "source language binding receipt"),
        (
            language_transport_evidence_receipt_sha256,
            "language transport evidence receipt",
        ),
        (language_transduction_receipt_sha256, "language transduction receipt"),
        (expression_receipt_sha256, "full field expression receipt"),
    ):
        sha256_digest(value, name)
    for values, name in (
        (cited_sensory_evidence_receipt_sha256s, "cited sensory receipts"),
        (map_injection_receipt_sha256s, "MapInject receipts"),
    ):
        if not isinstance(values, tuple) or not values:
            raise ReceiptError(f"{name} must be a nonempty immutable tuple")
        for index, digest in enumerate(values):
            sha256_digest(digest, f"{name}[{index}]")
    return _canonical_bytes(
        {
            "cited_sensory_evidence_receipt_sha256s": list(
                cited_sensory_evidence_receipt_sha256s
            ),
            "expression_receipt_sha256": expression_receipt_sha256,
            "language_transduction_receipt_sha256": (
                language_transduction_receipt_sha256
            ),
            "language_transport_evidence_receipt_sha256": (
                language_transport_evidence_receipt_sha256
            ),
            "map_injection_receipt_sha256s": list(
                map_injection_receipt_sha256s
            ),
            "operator_id": FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
            "schema": "glew.recall.full_expression_input_authority.v1",
            "source_binding_receipt_sha256": source_binding_receipt_sha256,
            "source_event_receipt_sha256": source_event_receipt_sha256,
            "staged_output_settlement_receipt_sha256": (
                staged_output_settlement_receipt_sha256
            ),
        }
    )


TRANSITION_CONTEXT_SCHEMA = "glew.recall.transition_context.v1"
TRANSITION_CONTEXT_MATCH_SCHEMA = "glew.recall.transition_context_match.v1"


def _sorted_distinct_sensory(
    sensory_evidence_receipt_sha256s: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(sensory_evidence_receipt_sha256s, tuple):
        raise ReceiptError("transition context sensory evidence must be a tuple")
    for index, digest in enumerate(sensory_evidence_receipt_sha256s):
        sha256_digest(digest, f"transition context sensory evidence[{index}]")
    if sensory_evidence_receipt_sha256s != tuple(
        sorted(set(sensory_evidence_receipt_sha256s))
    ):
        raise ReceiptError("transition context sensory evidence is not canonical")
    return sensory_evidence_receipt_sha256s


def _reproducible_match_object(
    *,
    prior_relation_receipt_sha256: str,
    input_expression_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
) -> dict[str, object]:
    """The canonical reproducible-match sub-object (owner Requirement 2).

    Folds the receipts a deterministic scene re-run reproduces bit-for-bit:
    the departing prior relation, the bank-independent full-field input
    expression, and the six-lane sensory evidence.  Kept as a single builder
    so the standalone match digest and the nested object inside the full
    :func:`transition_context_receipt_payload` are byte-identical.
    """

    sha256_digest(prior_relation_receipt_sha256, "transition prior relation receipt")
    sha256_digest(
        input_expression_receipt_sha256, "transition input expression receipt"
    )
    return {
        "input_expression_receipt_sha256": input_expression_receipt_sha256,
        "prior_relation_receipt_sha256": prior_relation_receipt_sha256,
        "schema": TRANSITION_CONTEXT_MATCH_SCHEMA,
        "sensory_evidence_receipt_sha256s": list(
            _sorted_distinct_sensory(sensory_evidence_receipt_sha256s)
        ),
    }


def transition_context_match_receipt_payload(
    *,
    prior_relation_receipt_sha256: str,
    input_expression_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
) -> bytes:
    """Canonical bytes of the reproducible match sub-digest alone."""

    return _canonical_bytes(
        _reproducible_match_object(
            prior_relation_receipt_sha256=prior_relation_receipt_sha256,
            input_expression_receipt_sha256=input_expression_receipt_sha256,
            sensory_evidence_receipt_sha256s=sensory_evidence_receipt_sha256s,
        )
    )


def transition_context_receipt_payload(
    *,
    profile_binding_sha256: str,
    mode_receipt_sha256: str,
    prior_relation_receipt_sha256: str,
    input_expression_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    closed_experience_receipt_sha256: str,
    recognition_receipt_sha256: str,
    commit_receipt_sha256: str,
    memory_output_bank_receipt_sha256: str,
    memory_stable_bank_receipt_sha256: str,
) -> bytes:
    """One sealed transition context (owner Requirement 2, design section 5.1).

    Two named sub-objects: a ``reproducible_match`` (the receipts a
    deterministic scene re-run reproduces) whose digest keys a learned
    successor, and a sealed ``provenance`` strand (the receipts a re-run
    cannot reproduce -- recognition folds the growing pre-growth bank, the
    closed-experience seal folds recognition, the self-recall commit is minted
    fresh, and the memory banks are mutable) that is the audited context, not
    an independent recall discriminator.
    """

    for value, name in (
        (profile_binding_sha256, "transition context profile receipt"),
        (mode_receipt_sha256, "transition context mode receipt"),
        (
            closed_experience_receipt_sha256,
            "transition context closed-experience receipt",
        ),
        (recognition_receipt_sha256, "transition context recognition receipt"),
        (commit_receipt_sha256, "transition context commit receipt"),
        (
            memory_output_bank_receipt_sha256,
            "transition context memory output-bank receipt",
        ),
        (
            memory_stable_bank_receipt_sha256,
            "transition context memory stable-bank receipt",
        ),
    ):
        sha256_digest(value, name)
    reproducible_match = _reproducible_match_object(
        prior_relation_receipt_sha256=prior_relation_receipt_sha256,
        input_expression_receipt_sha256=input_expression_receipt_sha256,
        sensory_evidence_receipt_sha256s=sensory_evidence_receipt_sha256s,
    )
    return _canonical_bytes(
        {
            "mode_receipt_sha256": mode_receipt_sha256,
            "profile_binding_sha256": profile_binding_sha256,
            "provenance": {
                "closed_experience_receipt_sha256": (
                    closed_experience_receipt_sha256
                ),
                "commit_receipt_sha256": commit_receipt_sha256,
                "memory_output_bank_receipt_sha256": (
                    memory_output_bank_receipt_sha256
                ),
                "memory_stable_bank_receipt_sha256": (
                    memory_stable_bank_receipt_sha256
                ),
                "recognition_receipt_sha256": recognition_receipt_sha256,
            },
            "reproducible_match": reproducible_match,
            "schema": TRANSITION_CONTEXT_SCHEMA,
        }
    )


def stable_mode_motif_binding_receipt_payload(
    *,
    binding_id: str,
    profile_binding_sha256: str,
    mode_receipt_sha256: str,
    mode_field_evaluation_identity_sha256: str,
    motif_receipt_sha256: str,
    source_fact_strand_receipt_sha256: str,
    transition_context_receipt_sha256: str,
    transition_context_match_sha256: str,
) -> bytes:
    require_identifier(binding_id, "stable mode/motif binding id")
    for value, name in (
        (profile_binding_sha256, "mode/motif profile receipt"),
        (mode_receipt_sha256, "stable mode receipt"),
        (
            mode_field_evaluation_identity_sha256,
            "stable mode field-evaluation identity",
        ),
        (motif_receipt_sha256, "stable motif receipt"),
        (source_fact_strand_receipt_sha256, "mode/motif Fact Strand receipt"),
        (
            transition_context_receipt_sha256,
            "stable transition-context receipt",
        ),
        (
            transition_context_match_sha256,
            "stable transition-context match receipt",
        ),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "binding_id": binding_id,
            "cardinality": {"mode": 1, "motif": 1},
            # The content-only mode identity is the actual successor-resolution
            # key (owner rule: a mode's identity is the exact field its source
            # expression evaluates to, not the request/scene bookkeeping baked
            # into its full mode receipt).  ``mode_receipt_sha256`` is retained
            # as sealed provenance -- the exact mode receipt that was live when
            # this binding was learned -- but a fresh process regrows that mode
            # into a new receipt (no ExpressionModeBank checkpoint exists), so
            # resolution must key on the reproducible field-evaluation identity.
            "mode_field_evaluation_identity_sha256": (
                mode_field_evaluation_identity_sha256
            ),
            "mode_receipt_sha256": mode_receipt_sha256,
            "motif_receipt_sha256": motif_receipt_sha256,
            "profile_binding_sha256": profile_binding_sha256,
            "schema": "glew.recall.stable_mode_motif_binding.v3",
            "source_fact_strand_receipt_sha256": (
                source_fact_strand_receipt_sha256
            ),
            "transition_context_match_sha256": transition_context_match_sha256,
            "transition_context_receipt_sha256": (
                transition_context_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class StableModeMotifBinding:
    binding_id: str
    profile_binding_sha256: str
    mode_receipt_sha256: str
    mode_field_evaluation_identity_sha256: str
    motif_receipt_sha256: str
    source_fact_strand_receipt_sha256: str
    transition_context_receipt_sha256: str
    transition_context_match_sha256: str
    binding_receipt_sha256: str

    def __post_init__(self) -> None:
        expected = self.payload()
        sha256_digest(self.binding_receipt_sha256, "stable mode/motif binding receipt")
        if receipt_sha256(expected) != self.binding_receipt_sha256:
            raise ReceiptError("stable mode/motif binding digest differs from its fields")

    def payload(self) -> bytes:
        return stable_mode_motif_binding_receipt_payload(
            binding_id=self.binding_id,
            profile_binding_sha256=self.profile_binding_sha256,
            mode_receipt_sha256=self.mode_receipt_sha256,
            mode_field_evaluation_identity_sha256=(
                self.mode_field_evaluation_identity_sha256
            ),
            motif_receipt_sha256=self.motif_receipt_sha256,
            source_fact_strand_receipt_sha256=(
                self.source_fact_strand_receipt_sha256
            ),
            transition_context_receipt_sha256=(
                self.transition_context_receipt_sha256
            ),
            transition_context_match_sha256=(
                self.transition_context_match_sha256
            ),
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("stable mode/motif binding has a different profile")
        receipt_registry.resolve(self.mode_receipt_sha256, "stable mode receipt")
        receipt_registry.resolve(self.motif_receipt_sha256, "stable motif receipt")
        receipt_registry.resolve(
            self.source_fact_strand_receipt_sha256,
            "mode/motif Fact Strand receipt",
        )
        # The sealed transition context binds this successor to the full,
        # already-receipted prior state / memory / chemistry / causal context
        # it arose from (owner Requirement 2).  Its reproducible-match
        # sub-digest must equal the stored match, so the audited context and
        # the successor key can never silently diverge.
        context_payload = receipt_registry.resolve(
            self.transition_context_receipt_sha256,
            "stable transition-context receipt",
        )
        context = _strict_transition_context(context_payload)
        if context.get("mode_receipt_sha256") != self.mode_receipt_sha256:
            raise ReceiptError(
                "stable transition context names a different committed mode"
            )
        if context.get("profile_binding_sha256") != self.profile_binding_sha256:
            raise ReceiptError("stable transition context has a different profile")
        reproducible = context.get("reproducible_match")
        if not isinstance(reproducible, dict):
            raise ReceiptError("stable transition context lost its reproducible match")
        if receipt_sha256(_canonical_bytes(reproducible)) != (
            self.transition_context_match_sha256
        ):
            raise ReceiptError(
                "stable transition-context match digest differs from its context"
            )
        _mounted_exact(
            receipt_registry,
            self.binding_receipt_sha256,
            self.payload(),
            "stable mode/motif binding receipt",
        )


def stable_mode_motif_bank_receipt_payload(
    *,
    bank_id: str,
    profile_binding_sha256: str,
    bindings: tuple[StableModeMotifBinding, ...],
) -> bytes:
    require_identifier(bank_id, "stable mode/motif bank id")
    sha256_digest(profile_binding_sha256, "mode/motif bank profile receipt")
    if not isinstance(bindings, tuple):
        raise ReceiptError("stable mode/motif bank must be an immutable tuple")
    if any(not isinstance(value, StableModeMotifBinding) for value in bindings):
        raise ReceiptError("stable mode/motif bank contains a non-binding value")
    ordered = tuple(
        sorted(
            bindings,
            key=lambda value: (
                value.mode_receipt_sha256,
                value.binding_id,
                value.binding_receipt_sha256,
            ),
        )
    )
    if bindings != ordered:
        raise ReceiptError("stable mode/motif bank is not in canonical order")
    if len({value.binding_id for value in bindings}) != len(bindings):
        raise ReceiptError("stable mode/motif bank contains duplicate binding ids")
    if any(value.profile_binding_sha256 != profile_binding_sha256 for value in bindings):
        raise ReceiptError("stable mode/motif bank mixes GLEW profiles")
    return _canonical_bytes(
        {
            "bank_id": bank_id,
            "binding_cardinality": len(bindings),
            "bindings": [
                {
                    "binding_id": value.binding_id,
                    "binding_receipt_sha256": value.binding_receipt_sha256,
                    "mode_field_evaluation_identity_sha256": (
                        value.mode_field_evaluation_identity_sha256
                    ),
                    "mode_receipt_sha256": value.mode_receipt_sha256,
                    "motif_receipt_sha256": value.motif_receipt_sha256,
                    "transition_context_match_sha256": (
                        value.transition_context_match_sha256
                    ),
                    "transition_context_receipt_sha256": (
                        value.transition_context_receipt_sha256
                    ),
                }
                for value in bindings
            ],
            "completeness_scope": "complete_active_stable_mode_motif_bank",
            "profile_binding_sha256": profile_binding_sha256,
            "schema": "glew.recall.stable_mode_motif_bank.v3",
        }
    )


@dataclass(frozen=True, slots=True)
class StableModeMotifBank:
    bank_id: str
    profile_binding_sha256: str
    bindings: tuple[StableModeMotifBinding, ...]
    bank_receipt_sha256: str
    bank_receipt_payload: bytes
    _by_mode_identity: Mapping[str, tuple[StableModeMotifBinding, ...]] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        expected = stable_mode_motif_bank_receipt_payload(
            bank_id=self.bank_id,
            profile_binding_sha256=self.profile_binding_sha256,
            bindings=self.bindings,
        )
        if self.bank_receipt_payload != expected:
            raise ReceiptError("stable mode/motif bank differs from exact receipt bytes")
        if receipt_sha256(expected) != self.bank_receipt_sha256:
            raise ReceiptError("stable mode/motif bank digest differs from exact bytes")
        # Successor resolution keys on the content-only mode identity, never on
        # the sealed ``mode_receipt_sha256`` provenance: a fresh process regrows
        # a learned mode into a NEW full receipt (no ExpressionModeBank
        # checkpoint exists), while its field-evaluation identity is
        # reproducible, so a resolver keyed on the receipt would fail to find
        # the successor of a legitimately regrown mode.
        grouped: dict[str, list[StableModeMotifBinding]] = {}
        for value in self.bindings:
            grouped.setdefault(
                value.mode_field_evaluation_identity_sha256, []
            ).append(value)
        object.__setattr__(
            self,
            "_by_mode_identity",
            MappingProxyType(
                {key: tuple(values) for key, values in grouped.items()}
            ),
        )

    def _verified_candidates(
        self,
        mode_field_evaluation_identity_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> tuple[StableModeMotifBinding, ...]:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("stable mode/motif bank has a different profile")
        _mounted_exact(
            receipt_registry,
            self.bank_receipt_sha256,
            self.bank_receipt_payload,
            "stable mode/motif bank receipt",
        )
        values = self._by_mode_identity.get(
            mode_field_evaluation_identity_sha256, ()
        )
        if not values:
            raise ReceiptError("selected mode has no stable motif binding")
        for value in values:
            value.verify(receipt_registry)
        return values

    def resolve_unique(
        self,
        mode_field_evaluation_identity_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> StableModeMotifBinding:
        """Resolve the sole successor of a mode (keyed on its field-evaluation
        identity, not its bookkeeping-tainted full receipt).

        This is the recall-transition resolver: a self-recall re-run only
        knows the *predecessor* scene when it must choose a mode's successor,
        so a mode that legitimately owns several successors (owner Requirement
        2) cannot be disambiguated at that point and raises here -- yielding
        honest fail-closed silence, never a wrong successor.  Single-successor
        modes (the exact-repeat recall path) resolve unchanged.
        """

        values = self._verified_candidates(
            mode_field_evaluation_identity_sha256, receipt_registry
        )
        motifs = {value.motif_receipt_sha256 for value in values}
        if len(motifs) != 1:
            raise ReceiptError("selected mode has conflicting stable motif bindings")
        return values[0]

    def resolve_for_transition(
        self,
        *,
        mode_field_evaluation_identity_sha256: str,
        transition_context_match_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> StableModeMotifBinding:
        """Resolve the one successor of ``mode`` learned under an exact
        reproducible transition context (owner Requirement 2)."""

        sha256_digest(
            transition_context_match_sha256,
            "resolve transition-context match receipt",
        )
        values = self._verified_candidates(
            mode_field_evaluation_identity_sha256, receipt_registry
        )
        matches = tuple(
            value
            for value in values
            if value.transition_context_match_sha256
            == transition_context_match_sha256
        )
        if len(matches) > 1:
            raise ReceiptError(
                "conflicting stable motif bindings for one transition context"
            )
        if not matches:
            raise ReceiptError(
                "no stable motif binding for this mode under this transition context"
            )
        return matches[0]

    def resolve_for_source_relation(
        self,
        *,
        mode_field_evaluation_identity_sha256: str,
        source_fact_strand_receipt_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> StableModeMotifBinding:
        """Resolve the one successor of ``mode`` whose learned transition
        departed from an exact source relation (its Fact Strand).

        Used to rebuild and re-verify an expression's genesis-anchored initial
        event: the root transition is identified by the state's own
        ``initial_relation`` Fact Strand, robust to a root mode that has since
        acquired sibling successors from other chain positions.
        """

        sha256_digest(
            source_fact_strand_receipt_sha256,
            "resolve source relation Fact Strand receipt",
        )
        values = self._verified_candidates(
            mode_field_evaluation_identity_sha256, receipt_registry
        )
        matches = tuple(
            value
            for value in values
            if value.source_fact_strand_receipt_sha256
            == source_fact_strand_receipt_sha256
        )
        if len(matches) > 1:
            raise ReceiptError(
                "conflicting stable motif bindings for one source relation"
            )
        if not matches:
            raise ReceiptError(
                "selected mode has no stable motif binding for this source relation"
            )
        return matches[0]


class RecallTransitionStatus(str, Enum):
    COMMITTED = "committed"
    UNKNOWN = "unknown"


class CompleteExpressionStatus(str, Enum):
    RELEASED = "released"
    UNKNOWN_SILENCE = "unknown_silence"


class FreshRecallSelfSenseProvider(Protocol):
    """Injected physical provider; no default or compatibility implementation exists."""

    operator_id: str
    provider_id: str
    authority_receipt_sha256: str

    def settle(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        output_binding_bank: MotifBindingBank,
        stable_mode_motif_bank: StableModeMotifBank,
        receipt_registry: ReceiptRegistry,
    ) -> "RecallTransitionSettlement": ...


def recall_transition_settlement_receipt_payload(
    *,
    status: RecallTransitionStatus,
    provider_id: str,
    provider_authority_receipt_sha256: str,
    source_event_receipt_sha256: str,
    staged_output_settlement_receipt_sha256: str,
    source_binding_receipt_sha256: str,
    cited_sensory_evidence_receipt_sha256s: tuple[str, ...],
    language_transport_evidence_receipt_sha256: str | None,
    language_transduction_receipt_sha256: str | None,
    expression_input_authority_receipt_sha256: str | None,
    expression_receipt_sha256: str | None,
    expression_evaluation_receipt_sha256: str | None,
    expression_recognition_receipt_sha256: str | None,
    commit_decision_receipt_sha256: str | None,
    stable_mode_motif_binding_receipt_sha256: str | None,
    next_event_receipt_sha256: str | None,
    missing_operator_id: str | None,
    reason: str,
) -> bytes:
    if not isinstance(status, RecallTransitionStatus):
        raise ReceiptError("recall transition status is not typed")
    require_identifier(provider_id, "recall provider id")
    require_identifier(reason, "recall transition reason")
    for value, name in (
        (provider_authority_receipt_sha256, "recall provider authority receipt"),
        (source_event_receipt_sha256, "recall source-event receipt"),
        (
            staged_output_settlement_receipt_sha256,
            "recall staged-output receipt",
        ),
        (source_binding_receipt_sha256, "recall source-binding receipt"),
    ):
        sha256_digest(value, name)
    for index, value in enumerate(cited_sensory_evidence_receipt_sha256s):
        sha256_digest(value, f"recall cited sensory receipt[{index}]")
    optional = (
        language_transport_evidence_receipt_sha256,
        language_transduction_receipt_sha256,
        expression_input_authority_receipt_sha256,
        expression_receipt_sha256,
        expression_evaluation_receipt_sha256,
        expression_recognition_receipt_sha256,
        commit_decision_receipt_sha256,
        stable_mode_motif_binding_receipt_sha256,
        next_event_receipt_sha256,
    )
    if status is RecallTransitionStatus.COMMITTED:
        if not cited_sensory_evidence_receipt_sha256s or any(
            value is None for value in optional
        ):
            raise ReceiptError("committed recall transition lacks full field receipts")
        if missing_operator_id is not None:
            raise ReceiptError("committed recall transition cannot name a missing operator")
    else:
        if cited_sensory_evidence_receipt_sha256s or any(
            value is not None for value in optional
        ):
            raise ReceiptError("UNKNOWN recall transition cannot carry partial authority")
        require_identifier(missing_operator_id or "", "missing recall operator id")
    for index, value in enumerate(optional):
        if value is not None:
            sha256_digest(value, f"recall transition optional receipt[{index}]")
    return _canonical_bytes(
        {
            "cited_sensory_evidence_receipt_sha256s": list(
                cited_sensory_evidence_receipt_sha256s
            ),
            "commit_decision_receipt_sha256": commit_decision_receipt_sha256,
            "expression_evaluation_receipt_sha256": (
                expression_evaluation_receipt_sha256
            ),
            "expression_input_authority_receipt_sha256": (
                expression_input_authority_receipt_sha256
            ),
            "expression_receipt_sha256": expression_receipt_sha256,
            "expression_recognition_receipt_sha256": (
                expression_recognition_receipt_sha256
            ),
            "language_transduction_receipt_sha256": (
                language_transduction_receipt_sha256
            ),
            "language_transport_evidence_receipt_sha256": (
                language_transport_evidence_receipt_sha256
            ),
            "missing_operator_id": missing_operator_id,
            "next_event_receipt_sha256": next_event_receipt_sha256,
            "operator_id": FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
            "provider_authority_receipt_sha256": (
                provider_authority_receipt_sha256
            ),
            "provider_id": provider_id,
            "reason": reason,
            "schema": "glew.recall.transition_settlement.v1",
            "source_binding_receipt_sha256": source_binding_receipt_sha256,
            "source_event_receipt_sha256": source_event_receipt_sha256,
            "stable_mode_motif_binding_receipt_sha256": (
                stable_mode_motif_binding_receipt_sha256
            ),
            "staged_output_settlement_receipt_sha256": (
                staged_output_settlement_receipt_sha256
            ),
            "status": status.value,
        }
    )


@dataclass(frozen=True, slots=True)
class RecallTransitionSettlement:
    status: RecallTransitionStatus
    provider_id: str
    provider_authority_receipt_sha256: str
    source_event_receipt_sha256: str
    staged_output_settlement_receipt_sha256: str
    source_binding_receipt_sha256: str
    cited_sensory_evidence: tuple[PortTransportEvidence, ...]
    language_transport_evidence: PortTransportEvidence | None
    language_transduction_receipt_sha256: str | None
    expression_input_authority_receipt_sha256: str | None
    expression: ClosedExperienceFieldExpression | None
    expression_evaluation: FieldExpressionEvaluation | None
    expression_recognition: ExpressionModeBoundaryResult | None
    commit_decision: CommitDecision | None
    stable_mode_motif_binding_receipt_sha256: str | None
    next_event: CommittedMotifEvent | None
    missing_operator_id: str | None
    reason: str
    receipt_registry: ReceiptRegistry
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def cited_sensory_receipt_sha256s(self) -> tuple[str, ...]:
        return tuple(
            value.evidence_receipt_sha256 for value in self.cited_sensory_evidence
        )

    def payload(self) -> bytes:
        return recall_transition_settlement_receipt_payload(
            status=self.status,
            provider_id=self.provider_id,
            provider_authority_receipt_sha256=(
                self.provider_authority_receipt_sha256
            ),
            source_event_receipt_sha256=self.source_event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                self.staged_output_settlement_receipt_sha256
            ),
            source_binding_receipt_sha256=self.source_binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=(
                self.cited_sensory_receipt_sha256s
            ),
            language_transport_evidence_receipt_sha256=(
                None
                if self.language_transport_evidence is None
                else self.language_transport_evidence.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=(
                self.language_transduction_receipt_sha256
            ),
            expression_input_authority_receipt_sha256=(
                self.expression_input_authority_receipt_sha256
            ),
            expression_receipt_sha256=(
                None if self.expression is None else self.expression.receipt_sha256
            ),
            expression_evaluation_receipt_sha256=(
                None
                if self.expression_evaluation is None
                else self.expression_evaluation.receipt_sha256
            ),
            expression_recognition_receipt_sha256=(
                None
                if self.expression_recognition is None
                else self.expression_recognition.receipt_sha256
            ),
            commit_decision_receipt_sha256=(
                None
                if self.commit_decision is None
                else self.commit_decision.receipt_sha256
            ),
            stable_mode_motif_binding_receipt_sha256=(
                self.stable_mode_motif_binding_receipt_sha256
            ),
            next_event_receipt_sha256=(
                None if self.next_event is None else self.next_event.event_receipt_sha256
            ),
            missing_operator_id=self.missing_operator_id,
            reason=self.reason,
        )

    def verify(
        self,
        *,
        provider: FreshRecallSelfSenseProvider,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        output_binding_bank: MotifBindingBank,
        stable_mode_motif_bank: StableModeMotifBank,
        prior_registry: ReceiptRegistry,
    ) -> None:
        _require_registry_extension(prior_registry, self.receipt_registry)
        if provider.operator_id != FRESH_RECALL_SELF_SENSE_OPERATOR_ID:
            raise ReceiptError("injected provider has an unratified recall operator")
        if (
            self.provider_id != provider.provider_id
            or self.provider_authority_receipt_sha256
            != provider.authority_receipt_sha256
        ):
            raise ReceiptError("recall settlement belongs to a different provider")
        provider_payload = fresh_recall_provider_authority_receipt_payload(
            provider_id=self.provider_id,
            profile_binding_sha256=self.receipt_registry.profile_binding_sha256,
        )
        _mounted_exact(
            self.receipt_registry,
            self.provider_authority_receipt_sha256,
            provider_payload,
            "fresh recall provider authority receipt",
        )
        if source_event.event_receipt_sha256 != self.source_event_receipt_sha256:
            raise ReceiptError("recall settlement cites a different source event")
        if (
            staged_output.receipt.receipt_sha256
            != self.staged_output_settlement_receipt_sha256
            or staged_output.receipt.status is not OutputStatus.STAGED_PRIVATE
            or staged_output.text
        ):
            raise ReceiptError("recall settlement lacks one private staged binding")
        if source_binding.binding_receipt_sha256 != self.source_binding_receipt_sha256:
            raise ReceiptError("recall settlement cites a different source binding")
        if (
            source_binding.kind is not OutputBindingKind.LANGUAGE_SCALAR
            or source_binding.motif_receipt_sha256
            != source_event.motif_receipt_sha256
        ):
            raise ReceiptError("recall re-entry source is not the staged motif binding")
        expected_payload = self.payload()
        if self.receipt_payload != expected_payload:
            raise ReceiptError("recall transition differs from exact settlement bytes")
        _mounted_exact(
            self.receipt_registry,
            self.receipt_sha256,
            expected_payload,
            "recall transition settlement receipt",
        )

        if self.status is RecallTransitionStatus.UNKNOWN:
            return
        required = (
            self.language_transport_evidence,
            self.language_transduction_receipt_sha256,
            self.expression_input_authority_receipt_sha256,
            self.expression,
            self.expression_evaluation,
            self.expression_recognition,
            self.commit_decision,
            self.stable_mode_motif_binding_receipt_sha256,
            self.next_event,
        )
        if any(value is None for value in required):
            raise ReceiptError("committed recall transition lost a required typed result")
        language_evidence = self.language_transport_evidence
        expression = self.expression
        evaluation = self.expression_evaluation
        recognition = self.expression_recognition
        commit = self.commit_decision
        next_event = self.next_event
        assert language_evidence is not None
        assert expression is not None
        assert evaluation is not None
        assert recognition is not None
        assert commit is not None
        assert next_event is not None

        sensory_digests = self.cited_sensory_receipt_sha256s
        if sensory_digests != source_binding.sensory_evidence_receipt_sha256s:
            raise ReceiptError("recall re-entry changed the motif's cited sensory evidence")
        if not isinstance(self.cited_sensory_evidence, tuple):
            raise ReceiptError("recall sensory evidence must be immutable")
        if sensory_digests != tuple(sorted(set(sensory_digests))):
            raise ReceiptError("recall sensory evidence is not canonical and distinct")
        for value in self.cited_sensory_evidence:
            if value.lane_id == "language":
                raise ReceiptError("cited sensory tuple cannot hide language evidence")
            value.verify(self.receipt_registry)
        if language_evidence.lane_id != "language":
            raise ReceiptError("recalled language binding did not enter the language lane")
        language_evidence.verify(self.receipt_registry)
        transduction_digest = self.language_transduction_receipt_sha256
        assert transduction_digest is not None
        transduction_payload = recalled_language_transduction_receipt_payload(
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            language_transport_evidence_receipt_sha256=(
                language_evidence.evidence_receipt_sha256
            ),
        )
        _mounted_exact(
            self.receipt_registry,
            transduction_digest,
            transduction_payload,
            "recalled language transduction receipt",
        )

        expression.verify(self.receipt_registry)
        # Every MapInject step may reference only evidence that genuinely
        # belongs to the recalled scene: the cited sensory evidence (externally
        # anchored to this motif's source binding) plus this expression's own
        # language-lane records.  A real scalar's language fiber closes its gate
        # once per valid balanced-ternary trit place, so one legitimate
        # expression carries SEVERAL distinct language-lane transport records
        # (all lane_id == "language"), of which ``language_evidence`` is only
        # the terminal transport that the transduction receipt is bound to.
        #
        # The anti-smuggling property is preserved on the non-language
        # partition, which is where it has teeth: any non-language evidence MUST
        # be one of the source binding's exact cited sensory receipts
        # (``sensory_digests`` == ``source_binding.sensory_evidence_receipt_
        # sha256s``, an authority external to this expression), and every cited
        # sense must appear.  Language-lane multiplicity is accepted because
        # (a) ``expression.verify`` above has already re-verified every
        # referenced evidence record against the mounted registry, and (b) the
        # language content is pinned downstream by the certified evaluation,
        # recognition, and commit this same expression must produce (verified
        # below) -- exactly as the sensory content is.  We still require the
        # transduction-anchored terminal transport to be one of the referenced
        # language records.
        cited_sensory = set(sensory_digests)
        observed_sensory: set[str] = set()
        observed_language: set[str] = set()
        for step in expression.steps:
            fibers = step.injection.mapped_fibers
            step_digests = {
                mapped.evidence.evidence_receipt_sha256 for mapped in fibers
            }
            if len(step_digests) != len(fibers):
                raise ReceiptError(
                    "recall sparse MapInject repeats one evidence receipt"
                )
            for mapped in fibers:
                digest = mapped.evidence.evidence_receipt_sha256
                if mapped.evidence.lane_id == "language":
                    observed_language.add(digest)
                elif digest in cited_sensory:
                    observed_sensory.add(digest)
                else:
                    raise ReceiptError(
                        "recall sparse MapInject contains evidence outside language plus cited senses"
                    )
        if observed_sensory != cited_sensory:
            raise ReceiptError(
                "recall sparse expression does not contain language plus every cited sense"
            )
        if language_evidence.evidence_receipt_sha256 not in observed_language:
            raise ReceiptError(
                "recall sparse expression omits the terminal recalled language transport"
            )
        expression_input_digest = self.expression_input_authority_receipt_sha256
        assert expression_input_digest is not None
        expression_input_payload = recall_expression_input_receipt_payload(
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=sensory_digests,
            language_transport_evidence_receipt_sha256=(
                language_evidence.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=transduction_digest,
            map_injection_receipt_sha256s=tuple(
                step.injection.receipt_sha256 for step in expression.steps
            ),
            expression_receipt_sha256=expression.receipt_sha256,
        )
        _mounted_exact(
            self.receipt_registry,
            expression_input_digest,
            expression_input_payload,
            "recall expression input authority receipt",
        )
        _mounted_exact(
            self.receipt_registry,
            expression.receipt_sha256,
            expression.receipt_payload,
            "recall full-field expression receipt",
        )

        evaluation.verify()
        if (
            evaluation.status is not ExpressionEvaluationStatus.CERTIFIED
            or evaluation.expression_receipt_sha256 != expression.receipt_sha256
            or evaluation.topology_authority_receipt_sha256
            != expression.topology_authority_receipt_sha256
        ):
            raise ReceiptError("recall full-field expression did not certify")
        _mounted_exact(
            self.receipt_registry,
            evaluation.receipt_sha256,
            evaluation.receipt_payload,
            "recall field-expression evaluation receipt",
        )

        recognition.verify()
        recognition.pre_growth_bank.verify(
            topology=expression.topology,
            receipt_registry=self.receipt_registry,
        )
        if (
            recognition.status is not ExpressionRecognitionStatus.RECOGNIZED
            or recognition.winner_mode_index is None
            or recognition.input_expression_receipt_sha256
            != expression.receipt_sha256
        ):
            raise ReceiptError("recall expression lacks one certified dominant mode")
        _mounted_exact(
            self.receipt_registry,
            recognition.receipt_sha256,
            recognition.receipt_payload,
            "recall expression recognition receipt",
        )

        commit.verify()
        winner = recognition.winner_mode_index
        selected_mode = recognition.pre_growth_bank.modes[winner]
        if (
            commit.status is not CommitStatus.COMMIT
            or commit.expression_recognition_receipt_sha256
            != recognition.receipt_sha256
            or commit.pre_growth_expression_bank_receipt_sha256
            != recognition.pre_growth_bank.receipt_sha256
            or commit.selected_mode_index != winner
            or commit.selected_mode_receipt_sha256 != selected_mode.receipt_sha256
        ):
            raise ReceiptError(
                "full-expression recognition did not bind directly to commit"
            )
        _mounted_exact(
            self.receipt_registry,
            commit.receipt_sha256,
            commit.receipt_payload,
            "recall full-field commit decision receipt",
        )

        # Successor resolution keys on the selected mode's field-evaluation
        # identity (content), never its full receipt: on a fresh process the
        # recognized mode is regrown into a new receipt but the identical field
        # yields the identical identity, so the stored successor still resolves.
        stable = stable_mode_motif_bank.resolve_unique(
            selected_mode.source_expression.field_evaluation_identity_sha256,
            self.receipt_registry,
        )
        if (
            self.stable_mode_motif_binding_receipt_sha256
            != stable.binding_receipt_sha256
        ):
            raise ReceiptError("recall settlement cites a different mode/motif binding")
        next_event.verify(self.receipt_registry)
        if (
            next_event.event_kind
            not in (MotifEventKind.CONTENT, MotifEventKind.EXPRESSION_CLOSE)
            or next_event.motif_receipt_sha256 != stable.motif_receipt_sha256
            or next_event.dominant_motif_commit_receipt_sha256
            != stable.binding_receipt_sha256
            or next_event.full_field_state_receipt_sha256
            != evaluation.receipt_sha256
            or next_event.field_commit_receipt_sha256 != commit.receipt_sha256
            or next_event.closed_experience_receipt_sha256
            != commit.closed_experience_receipt_sha256
            or next_event.corrected_l6_lock_receipt_sha256
            != commit.l6_evaluation_receipt_sha256
            or next_event.output_binding_bank_receipt_sha256
            != output_binding_bank.bank_receipt_sha256
            or next_event.source_state_receipt_sha256
            != source_event.result_state_receipt_sha256
        ):
            raise ReceiptError("next committed motif event is not the certified field result")


def _complete_expression_result_payload(
    *,
    status: CompleteExpressionStatus,
    text: str,
    final_output_settlement_receipt_sha256: str,
    transition_settlement_receipt_sha256s: tuple[str, ...],
    missing_operator_id: str | None,
    reason: str,
) -> bytes:
    if not isinstance(status, CompleteExpressionStatus):
        raise ReceiptError("complete-expression status is not typed")
    if not isinstance(text, str):
        raise ReceiptError("complete-expression text must be Unicode")
    sha256_digest(
        final_output_settlement_receipt_sha256,
        "final output settlement receipt",
    )
    for index, value in enumerate(transition_settlement_receipt_sha256s):
        sha256_digest(value, f"transition settlement receipt[{index}]")
    require_identifier(reason, "complete-expression reason")
    if status is CompleteExpressionStatus.RELEASED:
        if not text or missing_operator_id is not None:
            raise ReceiptError("released complete expression is inconsistent")
    else:
        if text:
            raise ReceiptError("UNKNOWN complete expression must remain silent")
        require_identifier(missing_operator_id or "", "missing complete-expression operator")
    return _canonical_bytes(
        {
            "final_output_settlement_receipt_sha256": (
                final_output_settlement_receipt_sha256
            ),
            "missing_operator_id": missing_operator_id,
            "reason": reason,
            "schema": "glew.recall.complete_expression_result.v1",
            "status": status.value,
            "text": text,
            "transition_settlement_receipt_sha256s": list(
                transition_settlement_receipt_sha256s
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CompleteExpressionResult:
    status: CompleteExpressionStatus
    text: str
    final_output_settlement_receipt_sha256: str
    transition_settlement_receipt_sha256s: tuple[str, ...]
    missing_operator_id: str | None
    reason: str
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        expected = _complete_expression_result_payload(
            status=self.status,
            text=self.text,
            final_output_settlement_receipt_sha256=(
                self.final_output_settlement_receipt_sha256
            ),
            transition_settlement_receipt_sha256s=(
                self.transition_settlement_receipt_sha256s
            ),
            missing_operator_id=self.missing_operator_id,
            reason=self.reason,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("complete-expression result differs from exact receipt")


def _make_complete_result(
    *,
    status: CompleteExpressionStatus,
    text: str,
    final_output: OutputActuation,
    transition_receipts: tuple[str, ...],
    missing_operator_id: str | None,
    reason: str,
) -> CompleteExpressionResult:
    payload = _complete_expression_result_payload(
        status=status,
        text=text,
        final_output_settlement_receipt_sha256=final_output.receipt.receipt_sha256,
        transition_settlement_receipt_sha256s=transition_receipts,
        missing_operator_id=missing_operator_id,
        reason=reason,
    )
    return CompleteExpressionResult(
        status=status,
        text=text,
        final_output_settlement_receipt_sha256=final_output.receipt.receipt_sha256,
        transition_settlement_receipt_sha256s=transition_receipts,
        missing_operator_id=missing_operator_id,
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def _canonical_source_binding(
    event: CommittedMotifEvent,
    bank: MotifBindingBank,
) -> MotifOutputBinding:
    values = bank.for_motif(event.motif_receipt_sha256)
    language = tuple(
        value for value in values if value.kind is OutputBindingKind.LANGUAGE_SCALAR
    )
    if len(language) != len(values) or not language:
        raise ReceiptError("staged motif lacks an unambiguous language-only binding")
    scalars = {value.decoded_scalar() for value in language}
    if len(scalars) != 1:
        raise ReceiptError("staged motif has conflicting recalled language scalars")
    return language[0]


def settle_complete_remembered_expression(
    *,
    expression_id: str,
    initial_event: CommittedMotifEvent,
    output_binding_bank: MotifBindingBank,
    stable_mode_motif_bank: StableModeMotifBank,
    receipt_registry: ReceiptRegistry,
    provider: FreshRecallSelfSenseProvider | None,
) -> CompleteExpressionResult:
    """Run fresh committed transitions until exact close or the first UNKNOWN.

    Termination is structural: close, failure, or exact state-edge cycle in the
    actuator.  No wall clock or number of transitions changes cognition.
    """

    actuator = RememberedExpressionActuator(
        expression_id=expression_id,
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        initial_state_receipt_sha256=initial_event.source_state_receipt_sha256,
    )
    current_event = initial_event
    current_registry = receipt_registry
    transition_receipts: list[str] = []
    while True:
        output = actuator.process(
            event=current_event,
            binding_bank=output_binding_bank,
            receipt_registry=current_registry,
        )
        if output.receipt.status is OutputStatus.EXPRESSION_RELEASED:
            return _make_complete_result(
                status=CompleteExpressionStatus.RELEASED,
                text=output.text,
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=None,
                reason="exact expression-close commit released private scalar stage",
            )
        if output.receipt.status is OutputStatus.UNKNOWN_SILENCE:
            return _make_complete_result(
                status=CompleteExpressionStatus.UNKNOWN_SILENCE,
                text="",
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
                reason=f"output settlement stopped UNKNOWN: {output.receipt.reason.value}",
            )
        if output.receipt.status is not OutputStatus.STAGED_PRIVATE:
            return _make_complete_result(
                status=CompleteExpressionStatus.UNKNOWN_SILENCE,
                text="",
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
                reason="no staged language binding exists for fresh recall re-entry",
            )
        if provider is None:
            return _make_complete_result(
                status=CompleteExpressionStatus.UNKNOWN_SILENCE,
                text="",
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
                reason="fresh recall self-sense provider is not mounted",
            )
        try:
            source_binding = _canonical_source_binding(
                current_event,
                output_binding_bank,
            )
            transition = provider.settle(
                source_event=current_event,
                staged_output=output,
                source_binding=source_binding,
                output_binding_bank=output_binding_bank,
                stable_mode_motif_bank=stable_mode_motif_bank,
                receipt_registry=current_registry,
            )
            if not isinstance(transition, RecallTransitionSettlement):
                raise ReceiptError("recall provider returned an untyped transition")
            transition.verify(
                provider=provider,
                source_event=current_event,
                staged_output=output,
                source_binding=source_binding,
                output_binding_bank=output_binding_bank,
                stable_mode_motif_bank=stable_mode_motif_bank,
                prior_registry=current_registry,
            )
        except ReceiptError as exc:
            return _make_complete_result(
                status=CompleteExpressionStatus.UNKNOWN_SILENCE,
                text="",
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=COMMIT_OPERATOR_ID,
                reason=f"fresh recall transition failed exact verification: {exc}",
            )
        transition_receipts.append(transition.receipt_sha256)
        if transition.status is RecallTransitionStatus.UNKNOWN:
            return _make_complete_result(
                status=CompleteExpressionStatus.UNKNOWN_SILENCE,
                text="",
                final_output=output,
                transition_receipts=tuple(transition_receipts),
                missing_operator_id=transition.missing_operator_id,
                reason=transition.reason,
            )
        if transition.next_event is None:
            raise ReceiptError("committed recall transition lost its next event")
        current_event = transition.next_event
        current_registry = transition.receipt_registry


__all__ = (
    "CompleteExpressionResult",
    "CompleteExpressionStatus",
    "FRESH_RECALL_SELF_SENSE_OPERATOR_ID",
    "FreshRecallSelfSenseProvider",
    "RECALLED_LANGUAGE_TRANSDUCTION_OPERATOR_ID",
    "RecallTransitionSettlement",
    "RecallTransitionStatus",
    "StableModeMotifBank",
    "StableModeMotifBinding",
    "TRANSITION_CONTEXT_MATCH_SCHEMA",
    "TRANSITION_CONTEXT_SCHEMA",
    "fresh_recall_provider_authority_receipt_payload",
    "recall_expression_input_receipt_payload",
    "recall_transition_settlement_receipt_payload",
    "recalled_language_transduction_receipt_payload",
    "settle_complete_remembered_expression",
    "stable_mode_motif_bank_receipt_payload",
    "stable_mode_motif_binding_receipt_payload",
    "transition_context_match_receipt_payload",
    "transition_context_receipt_payload",
)
