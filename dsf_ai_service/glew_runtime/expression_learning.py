"""Atomic learned expression bindings from committed coexperience.

This module does not generate language and does not retain a sentence,
continuation suffix, token sequence, or text key.  A transaction accepts one
already committed closed experience and its exact coexperienced typed scalar or
explicit no-output event.  The committed field mode is the only successor
lookup authority.

The transaction appends one content-addressed motif/output association and one
prior-mode/successor-motif relation, rebuilds both complete banks, and publishes
one new immutable state only after every receipt verifies.  Expression close is
an explicit no-output coexperience and a typed close motif, never a length,
timeout, punctuation, or vocabulary rule.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .closed_experience import SealedClosedExperience
from .commit import CommitDecision, CommitStatus
from .expression_modes import ExpressionMode
from .fresh_recall_provider import (
    RememberedMotifKind,
    RememberedMotifKindAuthority,
    remembered_motif_kind_receipt_payload,
)
from .language import (
    TypedLanguageFrozenKernelInput,
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
    OutputBindingKind,
    committed_motif_event_receipt_payload,
    motif_binding_bank_receipt_payload,
    motif_output_binding_receipt_payload,
)
from .recall_reentry import (
    StableModeMotifBank,
    StableModeMotifBinding,
    stable_mode_motif_bank_receipt_payload,
    stable_mode_motif_binding_receipt_payload,
    transition_context_match_receipt_payload,
    transition_context_receipt_payload,
)


LEARNING_OPERATOR_ID = "glew.learning.committed_coexperience_binding.v1"
CHECKPOINT_ALGORITHM = "HMAC-SHA256"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _strict_object(payload: bytes, description: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{description} must be nonempty bytes")

    def reject_constant(value: str) -> None:
        raise ReceiptError(f"{description} contains forbidden constant {value}")

    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ReceiptError(f"{description} repeats JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{description} is not strict JSON") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise ReceiptError(f"{description} is not canonical JSON")
    return value


def _extend_registry(
    registry: ReceiptRegistry,
    payloads: Sequence[bytes],
) -> ReceiptRegistry:
    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("learned binding produced an empty receipt")
        digest = receipt_sha256(payload)
        if digest in mounted:
            if mounted[digest] != payload:
                raise ReceiptError("learned binding receipt collision")
            continue
        mounted[digest] = payload
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(registry.profile_binding_sha256, tuple(records))


def _require_registry_extension(
    before: ReceiptRegistry,
    after: ReceiptRegistry,
) -> None:
    if before.profile_binding_sha256 != after.profile_binding_sha256:
        raise ReceiptError("learned binding changed the GLEW profile")
    for record in before.records:
        if after.resolve(record.digest, "prior learned-binding receipt") != record.payload:
            raise ReceiptError("learned binding changed a mounted receipt")


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    payload: bytes,
    description: str,
) -> None:
    if (
        receipt_sha256(payload) != digest
        or registry.resolve(digest, description) != payload
    ):
        raise ReceiptError(f"{description} differs from mounted bytes")


def _sensory_receipts(
    sealed: SealedClosedExperience,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            value.evidence_receipt_sha256
            for value in sealed.evidence
            if value.lane_id != "language"
        )
    )


def coexperienced_no_output_receipt_payload(
    *,
    event_id: str,
    closed_experience_receipt_sha256: str,
    source_authority_receipt_sha256: str,
) -> bytes:
    require_identifier(event_id, "coexperienced no-output event id")
    sha256_digest(
        closed_experience_receipt_sha256,
        "coexperienced no-output closed experience",
    )
    sha256_digest(
        source_authority_receipt_sha256,
        "coexperienced no-output source authority",
    )
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "event_id": event_id,
            "meaning": "explicitly_coexperienced_no_output",
            "schema": "glew.learning.coexperienced_no_output.v1",
            "source_authority_receipt_sha256": (
                source_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CoexperiencedNoOutput:
    event_id: str
    closed_experience_receipt_sha256: str
    source_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return coexperienced_no_output_receipt_payload(
            event_id=self.event_id,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                self.source_authority_receipt_sha256
            ),
        )

    def verify(
        self,
        *,
        sealed: SealedClosedExperience,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.closed_experience_receipt_sha256 != (
            sealed.closed_experience.authority_receipt_sha256
        ):
            raise ReceiptError("no-output event belongs to another experience")
        receipt_registry.resolve(
            self.source_authority_receipt_sha256,
            "coexperienced no-output source authority",
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "coexperienced no-output authority",
        )


def create_coexperienced_no_output(
    *,
    event_id: str,
    sealed: SealedClosedExperience,
    source_authority_receipt_sha256: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[CoexperiencedNoOutput, ReceiptRegistry]:
    """Create one exact no-output fact bound to one sealed experience."""

    sealed.verify(
        topology=sealed.expression.topology,
        receipt_registry=receipt_registry,
    )
    receipt_registry.resolve(
        source_authority_receipt_sha256,
        "coexperienced no-output source authority",
    )
    payload = coexperienced_no_output_receipt_payload(
        event_id=event_id,
        closed_experience_receipt_sha256=(
            sealed.closed_experience.authority_receipt_sha256
        ),
        source_authority_receipt_sha256=source_authority_receipt_sha256,
    )
    registry = _extend_registry(receipt_registry, (payload,))
    event = CoexperiencedNoOutput(
        event_id=event_id,
        closed_experience_receipt_sha256=(
            sealed.closed_experience.authority_receipt_sha256
        ),
        source_authority_receipt_sha256=source_authority_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    event.verify(sealed=sealed, receipt_registry=registry)
    return event, registry


class CoexperiencedOutputKind(str, Enum):
    TYPED_SCALAR = "typed_scalar"
    NO_OUTPUT = "no_output"


@dataclass(frozen=True, slots=True)
class CoexperiencedOutput:
    kind: CoexperiencedOutputKind
    typed_scalar: TypedLanguageFrozenKernelInput | None
    no_output: CoexperiencedNoOutput | None

    @classmethod
    def from_typed_scalar(
        cls,
        value: TypedLanguageFrozenKernelInput,
    ) -> "CoexperiencedOutput":
        return cls(CoexperiencedOutputKind.TYPED_SCALAR, value, None)

    @classmethod
    def from_no_output(
        cls,
        value: CoexperiencedNoOutput,
    ) -> "CoexperiencedOutput":
        return cls(CoexperiencedOutputKind.NO_OUTPUT, None, value)

    @property
    def source_receipt_sha256(self) -> str:
        if self.kind is CoexperiencedOutputKind.TYPED_SCALAR:
            if self.typed_scalar is None:
                raise ReceiptError("typed scalar coexperience is absent")
            return self.typed_scalar.event.event_receipt_sha256
        if self.no_output is None:
            raise ReceiptError("no-output coexperience is absent")
        return self.no_output.authority_receipt_sha256

    def verify(
        self,
        *,
        sealed: SealedClosedExperience,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.kind is CoexperiencedOutputKind.TYPED_SCALAR:
            if self.typed_scalar is None or self.no_output is not None:
                raise ReceiptError("typed scalar coexperience is not exclusive")
            self.typed_scalar.verify()
            _require_registry_extension(
                self.typed_scalar.receipt_registry,
                receipt_registry,
            )
            if len(self.typed_scalar.event.normalized_text) != 1:
                raise ReceiptError(
                    "one learned language binding requires one Unicode scalar"
                )
            source_stream = self.typed_scalar.kernel_input.source_stream_receipt_sha256
            observed_sources: set[str] = set()
            for evidence in sealed.evidence:
                if evidence.lane_id != "language":
                    continue
                trace = _strict_object(
                    evidence.raw_record.payload,
                    "sealed typed-language frozen-kernel trace",
                )
                if trace.get("schema") != (
                    "glew.provider.complete_signed_port_l0_l4_trace.v3"
                ):
                    raise ReceiptError(
                        "sealed language evidence is not a frozen-kernel trace"
                    )
                observed = trace.get("source_stream_receipt_sha256")
                if not isinstance(observed, str):
                    raise ReceiptError("sealed language trace lost its source stream")
                observed_sources.add(observed)
            if observed_sources != {source_stream}:
                raise ReceiptError(
                    "typed scalar is not the exact language source in the seal"
                )
            return
        if self.kind is not CoexperiencedOutputKind.NO_OUTPUT:
            raise ReceiptError("coexperienced output kind is not typed")
        if self.no_output is None or self.typed_scalar is not None:
            raise ReceiptError("no-output coexperience is not exclusive")
        self.no_output.verify(
            sealed=sealed,
            receipt_registry=receipt_registry,
        )


@dataclass(frozen=True, slots=True)
class CommittedCoexperience:
    commit: CommitDecision
    sealed: SealedClosedExperience
    selected_mode: ExpressionMode

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        self.sealed.verify(
            topology=self.sealed.expression.topology,
            receipt_registry=receipt_registry,
        )
        self.commit.verify()
        _mounted_exact(
            receipt_registry,
            self.commit.receipt_sha256,
            self.commit.receipt_payload,
            "learned coexperience commit",
        )
        recognition = self.sealed.recognition
        recognition.verify()
        winner = recognition.winner_mode_index
        if (
            self.commit.status is not CommitStatus.COMMIT
            or winner is None
            or self.commit.selected_mode_index != winner
            or self.commit.selected_mode_receipt_sha256
            != self.selected_mode.receipt_sha256
            or recognition.pre_growth_bank.modes[winner] != self.selected_mode
            or self.commit.topology_authority_receipt_sha256
            != self.sealed.expression.topology_authority_receipt_sha256
            or self.commit.closed_experience_receipt_sha256
            != self.sealed.closed_experience.authority_receipt_sha256
            or self.commit.expression_recognition_receipt_sha256
            != recognition.receipt_sha256
            or self.commit.pre_growth_expression_bank_receipt_sha256
            != recognition.pre_growth_bank.receipt_sha256
            or self.commit.evidence_receipt_sha256s
            != tuple(
                value.evidence_receipt_sha256
                for value in self.sealed.evidence
            )
            or self.commit.applicability_receipt_sha256s
            != tuple(
                value.authority_receipt_sha256
                for value in self.sealed.l5_applicability
            )
        ):
            raise ReceiptError(
                "learning input is not the exact selected committed coexperience"
            )
        self.selected_mode.verify(
            expected_index=winner,
            receipt_registry=receipt_registry,
        )


def committed_relation_receipt_payload(
    *,
    relation_id: str,
    profile_binding_sha256: str,
    commit_receipt_sha256: str,
    selected_mode_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    expression_receipt_sha256: str,
    recognition_receipt_sha256: str,
    l6_evaluation_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    fact_strand_receipt_sha256: str,
) -> bytes:
    require_identifier(relation_id, "committed relation id")
    for value, description in (
        (profile_binding_sha256, "committed relation profile"),
        (commit_receipt_sha256, "committed relation commit"),
        (selected_mode_receipt_sha256, "committed relation mode"),
        (topology_authority_receipt_sha256, "committed relation topology"),
        (closed_experience_receipt_sha256, "committed relation experience"),
        (expression_receipt_sha256, "committed relation expression"),
        (recognition_receipt_sha256, "committed relation recognition"),
        (l6_evaluation_receipt_sha256, "committed relation L6"),
        (fact_strand_receipt_sha256, "committed relation Fact Strand"),
    ):
        sha256_digest(value, description)
    for value in sensory_evidence_receipt_sha256s:
        sha256_digest(value, "committed relation sensory evidence")
    if sensory_evidence_receipt_sha256s != tuple(
        sorted(set(sensory_evidence_receipt_sha256s))
    ):
        raise ReceiptError("committed relation sensory evidence is not canonical")
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "commit_receipt_sha256": commit_receipt_sha256,
            "expression_receipt_sha256": expression_receipt_sha256,
            "fact_strand_receipt_sha256": fact_strand_receipt_sha256,
            "l6_evaluation_receipt_sha256": l6_evaluation_receipt_sha256,
            "operator": LEARNING_OPERATOR_ID,
            "profile_binding_sha256": profile_binding_sha256,
            "recognition_receipt_sha256": recognition_receipt_sha256,
            "relation_id": relation_id,
            "schema": "glew.learning.committed_mode_relation.v1",
            "selected_mode_receipt_sha256": selected_mode_receipt_sha256,
            "sensory_evidence_receipt_sha256s": list(
                sensory_evidence_receipt_sha256s
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CommittedModeRelation:
    relation_id: str
    profile_binding_sha256: str
    commit_receipt_sha256: str
    selected_mode_receipt_sha256: str
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    expression_receipt_sha256: str
    recognition_receipt_sha256: str
    l6_evaluation_receipt_sha256: str
    sensory_evidence_receipt_sha256s: tuple[str, ...]
    fact_strand_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return committed_relation_receipt_payload(
            relation_id=self.relation_id,
            profile_binding_sha256=self.profile_binding_sha256,
            commit_receipt_sha256=self.commit_receipt_sha256,
            selected_mode_receipt_sha256=self.selected_mode_receipt_sha256,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            expression_receipt_sha256=self.expression_receipt_sha256,
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            l6_evaluation_receipt_sha256=(
                self.l6_evaluation_receipt_sha256
            ),
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            fact_strand_receipt_sha256=self.fact_strand_receipt_sha256,
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("committed relation belongs to another profile")
        for digest, description in (
            (self.commit_receipt_sha256, "committed relation commit"),
            (self.selected_mode_receipt_sha256, "committed relation mode"),
            (self.topology_authority_receipt_sha256, "committed relation topology"),
            (
                self.closed_experience_receipt_sha256,
                "committed relation experience",
            ),
            (self.expression_receipt_sha256, "committed relation expression"),
            (self.recognition_receipt_sha256, "committed relation recognition"),
            (self.l6_evaluation_receipt_sha256, "committed relation L6"),
            (self.fact_strand_receipt_sha256, "committed relation Fact Strand"),
        ):
            receipt_registry.resolve(digest, description)
        for digest in self.sensory_evidence_receipt_sha256s:
            receipt_registry.resolve(digest, "committed relation sensory evidence")
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "committed mode relation",
        )


def _fact_strand_payload(
    *,
    relation_id: str,
    committed: CommittedCoexperience,
    output_source_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                committed.sealed.closed_experience.authority_receipt_sha256
            ),
            "commit_receipt_sha256": committed.commit.receipt_sha256,
            "output_source_receipt_sha256": output_source_receipt_sha256,
            "relation_id": relation_id,
            "schema": "glew.learning.committed_coexperience_fact_strand.v1",
            "selected_mode_receipt_sha256": (
                committed.selected_mode.receipt_sha256
            ),
        }
    )


def derive_committed_mode_relation(
    *,
    relation_id: str,
    committed: CommittedCoexperience,
    output_source_receipt_sha256: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[CommittedModeRelation, ReceiptRegistry]:
    committed.verify(receipt_registry)
    receipt_registry.resolve(
        output_source_receipt_sha256,
        "committed relation output source",
    )
    fact_payload = _fact_strand_payload(
        relation_id=relation_id,
        committed=committed,
        output_source_receipt_sha256=output_source_receipt_sha256,
    )
    relation_payload = committed_relation_receipt_payload(
        relation_id=relation_id,
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        commit_receipt_sha256=committed.commit.receipt_sha256,
        selected_mode_receipt_sha256=committed.selected_mode.receipt_sha256,
        topology_authority_receipt_sha256=(
            committed.sealed.expression.topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            committed.sealed.closed_experience.authority_receipt_sha256
        ),
        expression_receipt_sha256=committed.sealed.expression.receipt_sha256,
        recognition_receipt_sha256=committed.sealed.recognition.receipt_sha256,
        l6_evaluation_receipt_sha256=(
            committed.commit.l6_evaluation_receipt_sha256
        ),
        sensory_evidence_receipt_sha256s=_sensory_receipts(committed.sealed),
        fact_strand_receipt_sha256=receipt_sha256(fact_payload),
    )
    registry = _extend_registry(
        receipt_registry,
        (fact_payload, relation_payload),
    )
    relation = CommittedModeRelation(
        relation_id=relation_id,
        profile_binding_sha256=registry.profile_binding_sha256,
        commit_receipt_sha256=committed.commit.receipt_sha256,
        selected_mode_receipt_sha256=committed.selected_mode.receipt_sha256,
        topology_authority_receipt_sha256=(
            committed.sealed.expression.topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            committed.sealed.closed_experience.authority_receipt_sha256
        ),
        expression_receipt_sha256=committed.sealed.expression.receipt_sha256,
        recognition_receipt_sha256=committed.sealed.recognition.receipt_sha256,
        l6_evaluation_receipt_sha256=(
            committed.commit.l6_evaluation_receipt_sha256
        ),
        sensory_evidence_receipt_sha256s=_sensory_receipts(committed.sealed),
        fact_strand_receipt_sha256=receipt_sha256(fact_payload),
        authority_receipt_sha256=receipt_sha256(relation_payload),
    )
    relation.verify(registry)
    return relation, registry


def learned_binding_state_receipt_payload(
    *,
    state_id: str,
    expression_id: str,
    profile_binding_sha256: str,
    output_bank_receipt_sha256: str,
    stable_bank_receipt_sha256: str,
    initial_relation_receipt_sha256: str,
    pending_relation_receipt_sha256: str | None,
    initial_event_receipt_sha256: str | None,
    motif_kind_authority_receipt_sha256s: tuple[str, ...],
    terminal: bool,
) -> bytes:
    require_identifier(state_id, "learned binding state id")
    require_identifier(expression_id, "learned expression id")
    for value, description in (
        (profile_binding_sha256, "learned state profile"),
        (output_bank_receipt_sha256, "learned output bank"),
        (stable_bank_receipt_sha256, "learned stable bank"),
        (initial_relation_receipt_sha256, "learned initial relation"),
    ):
        sha256_digest(value, description)
    if pending_relation_receipt_sha256 is not None:
        sha256_digest(
            pending_relation_receipt_sha256,
            "learned pending relation",
        )
    if initial_event_receipt_sha256 is not None:
        sha256_digest(initial_event_receipt_sha256, "learned initial event")
    for value in motif_kind_authority_receipt_sha256s:
        sha256_digest(value, "learned motif-kind authority")
    if not isinstance(terminal, bool):
        raise ReceiptError("learned state terminal flag is not boolean")
    return _canonical_bytes(
        {
            "expression_id": expression_id,
            "initial_event_receipt_sha256": initial_event_receipt_sha256,
            "initial_relation_receipt_sha256": (
                initial_relation_receipt_sha256
            ),
            "motif_kind_authority_receipt_sha256s": list(
                motif_kind_authority_receipt_sha256s
            ),
            "operator": LEARNING_OPERATOR_ID,
            "output_bank_receipt_sha256": output_bank_receipt_sha256,
            "pending_relation_receipt_sha256": (
                pending_relation_receipt_sha256
            ),
            "profile_binding_sha256": profile_binding_sha256,
            "schema": "glew.learning.binding_state.v1",
            "stable_bank_receipt_sha256": stable_bank_receipt_sha256,
            "state_id": state_id,
            "terminal": terminal,
        }
    )


@dataclass(frozen=True, slots=True)
class LearnedBindingState:
    state_id: str
    expression_id: str
    output_bank: MotifBindingBank
    stable_bank: StableModeMotifBank
    initial_relation: CommittedModeRelation
    pending_relation: CommittedModeRelation | None
    initial_event: CommittedMotifEvent | None
    motif_kinds: tuple[RememberedMotifKindAuthority, ...]
    terminal: bool
    receipt_registry: ReceiptRegistry
    receipt_sha256: str
    receipt_payload: bytes

    def payload(self) -> bytes:
        return learned_binding_state_receipt_payload(
            state_id=self.state_id,
            expression_id=self.expression_id,
            profile_binding_sha256=(
                self.receipt_registry.profile_binding_sha256
            ),
            output_bank_receipt_sha256=self.output_bank.bank_receipt_sha256,
            stable_bank_receipt_sha256=self.stable_bank.bank_receipt_sha256,
            initial_relation_receipt_sha256=(
                self.initial_relation.authority_receipt_sha256
            ),
            pending_relation_receipt_sha256=(
                None
                if self.pending_relation is None
                else self.pending_relation.authority_receipt_sha256
            ),
            initial_event_receipt_sha256=(
                None
                if self.initial_event is None
                else self.initial_event.event_receipt_sha256
            ),
            motif_kind_authority_receipt_sha256s=tuple(
                value.authority_receipt_sha256 for value in self.motif_kinds
            ),
            terminal=self.terminal,
        )

    def verify(self) -> None:
        self.initial_relation.verify(self.receipt_registry)
        if self.pending_relation is not None:
            self.pending_relation.verify(self.receipt_registry)
        self.output_bank.verify_for_motif(self.receipt_registry, None)
        for value in self.output_bank.bindings:
            value.verify(self.receipt_registry)
        _mounted_exact(
            self.receipt_registry,
            self.stable_bank.bank_receipt_sha256,
            self.stable_bank.bank_receipt_payload,
            "learned stable mode/motif bank",
        )
        for value in self.stable_bank.bindings:
            value.verify(self.receipt_registry)
        for value in self.motif_kinds:
            value.verify(self.receipt_registry)
        if self.motif_kinds != tuple(
            sorted(
                self.motif_kinds,
                key=lambda value: value.motif_receipt_sha256,
            )
        ):
            raise ReceiptError("learned motif-kind authorities are not canonical")
        kind_by_motif = {
            value.motif_receipt_sha256: value.kind
            for value in self.motif_kinds
        }
        if len(kind_by_motif) != len(self.motif_kinds):
            raise ReceiptError("learned motif has duplicate kind authorities")
        stable_pairs = tuple(
            (
                value.mode_receipt_sha256,
                value.transition_context_match_sha256,
            )
            for value in self.stable_bank.bindings
        )
        stable_motifs = {
            value.motif_receipt_sha256 for value in self.stable_bank.bindings
        }
        # A committed mode may own many successors (owner Requirement 2); what
        # must stay unique is the (mode, reproducible-transition-context) pair.
        # Two successors sharing both would be a true-duplicate defect.
        if len(set(stable_pairs)) != len(stable_pairs):
            raise ReceiptError("learned mode/transition-context pair is not unique")
        if stable_motifs != set(kind_by_motif):
            raise ReceiptError(
                "learned stable bank and motif-kind authorities are incomplete"
            )
        output_motifs = {
            value.motif_receipt_sha256 for value in self.output_bank.bindings
        }
        if len(output_motifs) != len(self.output_bank.bindings):
            raise ReceiptError("learned motif has more than one output binding")
        expected_output_motifs = {
            motif
            for motif, kind in kind_by_motif.items()
            if kind is RememberedMotifKind.CONTENT
        }
        if output_motifs != expected_output_motifs:
            raise ReceiptError(
                "learned output bank does not exactly cover content motifs"
            )
        if bool(self.stable_bank.bindings) != (self.initial_event is not None):
            raise ReceiptError(
                "learned initial event and successor bank disagree"
            )
        if self.initial_event is not None:
            self.initial_event.verify(self.receipt_registry)
            if self.initial_event.output_binding_bank_receipt_sha256 != (
                self.output_bank.bank_receipt_sha256
            ):
                raise ReceiptError("learned initial event cites a stale output bank")
            stable = self.stable_bank.resolve_for_source_relation(
                mode_receipt_sha256=(
                    self.initial_relation.selected_mode_receipt_sha256
                ),
                source_fact_strand_receipt_sha256=(
                    self.initial_relation.fact_strand_receipt_sha256
                ),
                receipt_registry=self.receipt_registry,
            )
            if (
                self.initial_event.motif_receipt_sha256
                != stable.motif_receipt_sha256
                or self.initial_event.dominant_motif_commit_receipt_sha256
                != stable.binding_receipt_sha256
            ):
                raise ReceiptError("learned initial event differs from root relation")
        if self.terminal != (self.pending_relation is None):
            raise ReceiptError("learned terminal state retains a pending relation")
        expected = self.payload()
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError("learned binding state differs from exact receipt")
        _mounted_exact(
            self.receipt_registry,
            self.receipt_sha256,
            expected,
            "learned binding state",
        )


def create_learned_binding_genesis(
    *,
    state_id: str,
    expression_id: str,
    initial_relation: CommittedModeRelation,
    receipt_registry: ReceiptRegistry,
) -> LearnedBindingState:
    initial_relation.verify(receipt_registry)
    output_payload = motif_binding_bank_receipt_payload(
        bank_id=f"{state_id}:output",
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        bindings=(),
    )
    output_bank = MotifBindingBank(
        bank_id=f"{state_id}:output",
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        bindings=(),
        bank_receipt_sha256=receipt_sha256(output_payload),
        bank_receipt_payload=output_payload,
    )
    stable_payload = stable_mode_motif_bank_receipt_payload(
        bank_id=f"{state_id}:stable",
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        bindings=(),
    )
    stable_bank = StableModeMotifBank(
        bank_id=f"{state_id}:stable",
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        bindings=(),
        bank_receipt_sha256=receipt_sha256(stable_payload),
        bank_receipt_payload=stable_payload,
    )
    registry = _extend_registry(
        receipt_registry,
        (output_payload, stable_payload),
    )
    state_payload = learned_binding_state_receipt_payload(
        state_id=state_id,
        expression_id=expression_id,
        profile_binding_sha256=registry.profile_binding_sha256,
        output_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        stable_bank_receipt_sha256=stable_bank.bank_receipt_sha256,
        initial_relation_receipt_sha256=(
            initial_relation.authority_receipt_sha256
        ),
        pending_relation_receipt_sha256=(
            initial_relation.authority_receipt_sha256
        ),
        initial_event_receipt_sha256=None,
        motif_kind_authority_receipt_sha256s=(),
        terminal=False,
    )
    registry = _extend_registry(registry, (state_payload,))
    state = LearnedBindingState(
        state_id=state_id,
        expression_id=expression_id,
        output_bank=output_bank,
        stable_bank=stable_bank,
        initial_relation=initial_relation,
        pending_relation=initial_relation,
        initial_event=None,
        motif_kinds=(),
        terminal=False,
        receipt_registry=registry,
        receipt_sha256=receipt_sha256(state_payload),
        receipt_payload=state_payload,
    )
    state.verify()
    return state


def _motif_payload(
    *,
    expression_id: str,
    relation: CommittedModeRelation,
    output_source_receipt_sha256: str,
    event_kind: MotifEventKind,
) -> bytes:
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                relation.closed_experience_receipt_sha256
            ),
            "commit_receipt_sha256": relation.commit_receipt_sha256,
            "event_kind": event_kind.value,
            "expression_id": expression_id,
            "fact_strand_receipt_sha256": (
                relation.fact_strand_receipt_sha256
            ),
            "operator": LEARNING_OPERATOR_ID,
            "output_source_receipt_sha256": output_source_receipt_sha256,
            "schema": "glew.learning.committed_coexperience_motif.v1",
            "selected_mode_receipt_sha256": (
                relation.selected_mode_receipt_sha256
            ),
        }
    )


def _make_initial_event(
    *,
    state_id: str,
    expression_id: str,
    initial_relation: CommittedModeRelation,
    output_bank: MotifBindingBank,
    stable_bank: StableModeMotifBank,
    receipt_registry: ReceiptRegistry,
) -> tuple[CommittedMotifEvent, tuple[bytes, ...]]:
    root = initial_relation
    # The genesis-anchored initial event names the root transition's own
    # successor.  Resolve it by the state's own ``initial_relation`` Fact
    # Strand, not by "the sole successor of the root mode": the root mode may
    # since have acquired sibling successors from other chain positions (owner
    # Requirement 2), and this event must stay pinned to the root transition.
    stable = stable_bank.resolve_for_source_relation(
        mode_receipt_sha256=root.selected_mode_receipt_sha256,
        source_fact_strand_receipt_sha256=root.fact_strand_receipt_sha256,
        receipt_registry=receipt_registry,
    )
    source_state_payload = _canonical_bytes(
        {
            "initial_relation_receipt_sha256": root.authority_receipt_sha256,
            "schema": "glew.learning.expression_source_state.v1",
            "state_id": state_id,
        }
    )
    result_state_payload = _canonical_bytes(
        {
            "output_bank_receipt_sha256": output_bank.bank_receipt_sha256,
            "schema": "glew.learning.expression_result_state.v1",
            "stable_binding_receipt_sha256": stable.binding_receipt_sha256,
        }
    )
    edge_payload = _canonical_bytes(
        {
            "result_state_receipt_sha256": receipt_sha256(result_state_payload),
            "schema": "glew.learning.expression_transition_edge.v1",
            "source_state_receipt_sha256": receipt_sha256(source_state_payload),
            "stable_binding_receipt_sha256": stable.binding_receipt_sha256,
        }
    )
    identity = receipt_sha256(
        _canonical_bytes(
            {
                "output_bank_receipt_sha256": output_bank.bank_receipt_sha256,
                "root_relation_receipt_sha256": root.authority_receipt_sha256,
                "stable_binding_receipt_sha256": stable.binding_receipt_sha256,
            }
        )
    )
    event_payload = committed_motif_event_receipt_payload(
        expression_id=expression_id,
        event_id=f"learned-initial-{identity}",
        event_kind=MotifEventKind.CONTENT,
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        motif_receipt_sha256=stable.motif_receipt_sha256,
        closed_experience_receipt_sha256=(
            root.closed_experience_receipt_sha256
        ),
        fact_strand_receipt_sha256=root.fact_strand_receipt_sha256,
        sensory_evidence_receipt_sha256s=(
            root.sensory_evidence_receipt_sha256s
        ),
        full_field_state_receipt_sha256=root.expression_receipt_sha256,
        field_commit_receipt_sha256=root.commit_receipt_sha256,
        dominant_motif_commit_receipt_sha256=stable.binding_receipt_sha256,
        corrected_l6_lock_receipt_sha256=(
            root.l6_evaluation_receipt_sha256
        ),
        output_binding_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        source_state_receipt_sha256=receipt_sha256(source_state_payload),
        transition_edge_receipt_sha256=receipt_sha256(edge_payload),
        result_state_receipt_sha256=receipt_sha256(result_state_payload),
        expression_close_authority_receipt_sha256=None,
    )
    event = CommittedMotifEvent(
        expression_id=expression_id,
        event_id=f"learned-initial-{identity}",
        event_kind=MotifEventKind.CONTENT,
        profile_binding_sha256=receipt_registry.profile_binding_sha256,
        motif_receipt_sha256=stable.motif_receipt_sha256,
        closed_experience_receipt_sha256=(
            root.closed_experience_receipt_sha256
        ),
        fact_strand_receipt_sha256=root.fact_strand_receipt_sha256,
        sensory_evidence_receipt_sha256s=(
            root.sensory_evidence_receipt_sha256s
        ),
        full_field_state_receipt_sha256=root.expression_receipt_sha256,
        field_commit_receipt_sha256=root.commit_receipt_sha256,
        dominant_motif_commit_receipt_sha256=stable.binding_receipt_sha256,
        corrected_l6_lock_receipt_sha256=(
            root.l6_evaluation_receipt_sha256
        ),
        output_binding_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        source_state_receipt_sha256=receipt_sha256(source_state_payload),
        transition_edge_receipt_sha256=receipt_sha256(edge_payload),
        result_state_receipt_sha256=receipt_sha256(result_state_payload),
        expression_close_authority_receipt_sha256=None,
        event_receipt_sha256=receipt_sha256(event_payload),
    )
    return event, (
        source_state_payload,
        result_state_payload,
        edge_payload,
        event_payload,
    )


def learn_committed_binding_transaction(
    *,
    state: LearnedBindingState,
    committed: CommittedCoexperience,
    coexperienced_output: CoexperiencedOutput,
    prior_relation: CommittedModeRelation,
    relation_id: str,
    expression_close: bool,
    receipt_registry: ReceiptRegistry,
) -> LearnedBindingState:
    """Atomically learn one successor from committed coexperience."""

    state.verify()
    _require_registry_extension(state.receipt_registry, receipt_registry)
    if state.terminal or state.pending_relation is None:
        raise ReceiptError("closed learned expression cannot accept another binding")
    if prior_relation != state.pending_relation:
        raise ReceiptError("learning transaction received another prior relation")
    prior_relation.verify(receipt_registry)
    committed.verify(receipt_registry)
    coexperienced_output.verify(
        sealed=committed.sealed,
        receipt_registry=receipt_registry,
    )
    if expression_close and (
        coexperienced_output.kind is not CoexperiencedOutputKind.NO_OUTPUT
    ):
        raise ReceiptError("expression close requires explicit no-output coexperience")

    current_relation, working = derive_committed_mode_relation(
        relation_id=relation_id,
        committed=committed,
        output_source_receipt_sha256=(
            coexperienced_output.source_receipt_sha256
        ),
        receipt_registry=receipt_registry,
    )
    event_kind = (
        MotifEventKind.EXPRESSION_CLOSE
        if expression_close
        else MotifEventKind.CONTENT
    )
    motif_payload = _motif_payload(
        expression_id=state.expression_id,
        relation=current_relation,
        output_source_receipt_sha256=(
            coexperienced_output.source_receipt_sha256
        ),
        event_kind=event_kind,
    )
    motif_digest = receipt_sha256(motif_payload)
    generated: list[bytes] = [motif_payload]

    output_bindings = list(state.output_bank.bindings)
    if not expression_close:
        if coexperienced_output.kind is CoexperiencedOutputKind.TYPED_SCALAR:
            typed_scalar = coexperienced_output.typed_scalar
            if typed_scalar is None:
                raise ReceiptError("typed scalar coexperience disappeared")
            trits = typed_scalar.event.trits
            kind = OutputBindingKind.LANGUAGE_SCALAR
            language_count = 1
            no_output_count = 0
        else:
            trits = ()
            kind = OutputBindingKind.NO_OUTPUT
            language_count = 0
            no_output_count = 1
        binding_id = f"{state.state_id}:output:{motif_digest}"
        binding_payload = motif_output_binding_receipt_payload(
            binding_id=binding_id,
            profile_binding_sha256=working.profile_binding_sha256,
            motif_receipt_sha256=motif_digest,
            closed_experience_receipt_sha256=(
                current_relation.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=(
                current_relation.fact_strand_receipt_sha256
            ),
            sensory_evidence_receipt_sha256s=(
                current_relation.sensory_evidence_receipt_sha256s
            ),
            coexperienced_output_receipt_sha256=(
                coexperienced_output.source_receipt_sha256
            ),
            kind=kind,
            trits=trits,
            language_scalar_cardinality=language_count,
            no_output_cardinality=no_output_count,
        )
        output_bindings.append(
            MotifOutputBinding(
                binding_id=binding_id,
                profile_binding_sha256=working.profile_binding_sha256,
                motif_receipt_sha256=motif_digest,
                closed_experience_receipt_sha256=(
                    current_relation.closed_experience_receipt_sha256
                ),
                fact_strand_receipt_sha256=(
                    current_relation.fact_strand_receipt_sha256
                ),
                sensory_evidence_receipt_sha256s=(
                    current_relation.sensory_evidence_receipt_sha256s
                ),
                coexperienced_output_receipt_sha256=(
                    coexperienced_output.source_receipt_sha256
                ),
                kind=kind,
                trits=trits,
                language_scalar_cardinality=language_count,
                no_output_cardinality=no_output_count,
                binding_receipt_sha256=receipt_sha256(binding_payload),
            )
        )
        generated.append(binding_payload)

    output_tuple = tuple(
        sorted(
            output_bindings,
            key=lambda value: (
                value.motif_receipt_sha256,
                value.binding_id,
                value.binding_receipt_sha256,
            ),
        )
    )
    output_bank_payload = motif_binding_bank_receipt_payload(
        bank_id=state.output_bank.bank_id,
        profile_binding_sha256=working.profile_binding_sha256,
        bindings=output_tuple,
    )
    output_bank = MotifBindingBank(
        bank_id=state.output_bank.bank_id,
        profile_binding_sha256=working.profile_binding_sha256,
        bindings=output_tuple,
        bank_receipt_sha256=receipt_sha256(output_bank_payload),
        bank_receipt_payload=output_bank_payload,
    )
    generated.append(output_bank_payload)

    # Seal the full transition context this successor arose from -- prior
    # state (the departing relation), memory at that moment (the state's own
    # output/stable banks), chemistry/sensory + causal experience of the turn
    # (the current relation's closed-experience seal, expression, recognition,
    # and commit).  Every argument is an already-mounted receipt (owner
    # Requirement 2, design section 3.6/5.1).  A successor is keyed on the
    # reproducible-match sub-digest, so the SAME committed mode can learn
    # genuinely distinct successors from genuinely distinct prior contexts,
    # while an identical experience twice still collides.
    context_payload = transition_context_receipt_payload(
        profile_binding_sha256=working.profile_binding_sha256,
        mode_receipt_sha256=prior_relation.selected_mode_receipt_sha256,
        prior_relation_receipt_sha256=prior_relation.authority_receipt_sha256,
        input_expression_receipt_sha256=(
            current_relation.expression_receipt_sha256
        ),
        sensory_evidence_receipt_sha256s=(
            current_relation.sensory_evidence_receipt_sha256s
        ),
        closed_experience_receipt_sha256=(
            current_relation.closed_experience_receipt_sha256
        ),
        recognition_receipt_sha256=current_relation.recognition_receipt_sha256,
        commit_receipt_sha256=current_relation.commit_receipt_sha256,
        memory_output_bank_receipt_sha256=(
            state.output_bank.bank_receipt_sha256
        ),
        memory_stable_bank_receipt_sha256=(
            state.stable_bank.bank_receipt_sha256
        ),
    )
    context_digest = receipt_sha256(context_payload)
    context_match = receipt_sha256(
        transition_context_match_receipt_payload(
            prior_relation_receipt_sha256=(
                prior_relation.authority_receipt_sha256
            ),
            input_expression_receipt_sha256=(
                current_relation.expression_receipt_sha256
            ),
            sensory_evidence_receipt_sha256s=(
                current_relation.sensory_evidence_receipt_sha256s
            ),
        )
    )

    stable_id = (
        f"{state.state_id}:successor:"
        f"{prior_relation.selected_mode_receipt_sha256}:{motif_digest}"
    )
    stable_payload = stable_mode_motif_binding_receipt_payload(
        binding_id=stable_id,
        profile_binding_sha256=working.profile_binding_sha256,
        mode_receipt_sha256=prior_relation.selected_mode_receipt_sha256,
        motif_receipt_sha256=motif_digest,
        source_fact_strand_receipt_sha256=(
            prior_relation.fact_strand_receipt_sha256
        ),
        transition_context_receipt_sha256=context_digest,
        transition_context_match_sha256=context_match,
    )
    stable_binding = StableModeMotifBinding(
        binding_id=stable_id,
        profile_binding_sha256=working.profile_binding_sha256,
        mode_receipt_sha256=prior_relation.selected_mode_receipt_sha256,
        motif_receipt_sha256=motif_digest,
        source_fact_strand_receipt_sha256=(
            prior_relation.fact_strand_receipt_sha256
        ),
        transition_context_receipt_sha256=context_digest,
        transition_context_match_sha256=context_match,
        binding_receipt_sha256=receipt_sha256(stable_payload),
    )
    duplicate = [
        value
        for value in state.stable_bank.bindings
        if value.mode_receipt_sha256
        == prior_relation.selected_mode_receipt_sha256
        and value.transition_context_match_sha256 == context_match
    ]
    if duplicate:
        raise ReceiptError(
            "prior committed mode already learned this exact transition context"
        )
    stable_values = list(state.stable_bank.bindings)
    stable_values.append(stable_binding)
    stable_tuple = tuple(
        sorted(
            stable_values,
            key=lambda value: (
                value.mode_receipt_sha256,
                value.binding_id,
                value.binding_receipt_sha256,
            ),
        )
    )
    stable_bank_payload = stable_mode_motif_bank_receipt_payload(
        bank_id=state.stable_bank.bank_id,
        profile_binding_sha256=working.profile_binding_sha256,
        bindings=stable_tuple,
    )
    stable_bank = StableModeMotifBank(
        bank_id=state.stable_bank.bank_id,
        profile_binding_sha256=working.profile_binding_sha256,
        bindings=stable_tuple,
        bank_receipt_sha256=receipt_sha256(stable_bank_payload),
        bank_receipt_payload=stable_bank_payload,
    )
    generated.extend((context_payload, stable_payload, stable_bank_payload))

    motif_kind_value = (
        RememberedMotifKind.EXPRESSION_CLOSE
        if expression_close
        else RememberedMotifKind.CONTENT
    )
    motif_source_experience = (
        current_relation.closed_experience_receipt_sha256
    )
    kind_payload = remembered_motif_kind_receipt_payload(
        motif_receipt_sha256=motif_digest,
        kind=motif_kind_value,
        source_closed_experience_receipt_sha256=motif_source_experience,
    )
    motif_kind = RememberedMotifKindAuthority(
        motif_receipt_sha256=motif_digest,
        kind=motif_kind_value,
        source_closed_experience_receipt_sha256=motif_source_experience,
        authority_receipt_sha256=receipt_sha256(kind_payload),
    )
    motif_kinds = tuple(
        sorted(
            (*state.motif_kinds, motif_kind),
            key=lambda value: value.motif_receipt_sha256,
        )
    )
    generated.append(kind_payload)
    working = _extend_registry(working, generated)

    initial_event, event_payloads = _make_initial_event(
        state_id=state.state_id,
        expression_id=state.expression_id,
        initial_relation=state.initial_relation,
        output_bank=output_bank,
        stable_bank=stable_bank,
        receipt_registry=working,
    )
    working = _extend_registry(working, event_payloads)
    state_payload = learned_binding_state_receipt_payload(
        state_id=state.state_id,
        expression_id=state.expression_id,
        profile_binding_sha256=working.profile_binding_sha256,
        output_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        stable_bank_receipt_sha256=stable_bank.bank_receipt_sha256,
        initial_relation_receipt_sha256=(
            state.initial_relation.authority_receipt_sha256
        ),
        pending_relation_receipt_sha256=(
            None
            if expression_close
            else current_relation.authority_receipt_sha256
        ),
        initial_event_receipt_sha256=initial_event.event_receipt_sha256,
        motif_kind_authority_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in motif_kinds
        ),
        terminal=expression_close,
    )
    working = _extend_registry(working, (state_payload,))
    result = LearnedBindingState(
        state_id=state.state_id,
        expression_id=state.expression_id,
        output_bank=output_bank,
        stable_bank=stable_bank,
        initial_relation=state.initial_relation,
        pending_relation=(
            None if expression_close else current_relation
        ),
        initial_event=initial_event,
        motif_kinds=motif_kinds,
        terminal=expression_close,
        receipt_registry=working,
        receipt_sha256=receipt_sha256(state_payload),
        receipt_payload=state_payload,
    )
    result.verify()
    return result


def learned_binding_checkpoint_payload(
    *,
    state: LearnedBindingState,
    checkpoint_id: str,
    authentication_key: bytes,
    key_id: str,
) -> bytes:
    state.verify()
    require_identifier(checkpoint_id, "learned checkpoint id")
    require_identifier(key_id, "learned checkpoint key id")
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("learned checkpoint authentication key is absent")
    body = {
        "checkpoint_id": checkpoint_id,
        "profile_binding_sha256": (
            state.receipt_registry.profile_binding_sha256
        ),
        "receipt_records": [
            {"payload_hex": value.payload.hex(), "sha256": value.digest}
            for value in state.receipt_registry.records
        ],
        "schema": "glew.learning.binding_checkpoint.v1",
        "state_receipt_sha256": state.receipt_sha256,
    }
    body_payload = _canonical_bytes(body)
    signature = hmac.new(
        authentication_key,
        body_payload,
        hashlib.sha256,
    ).hexdigest()
    return _canonical_bytes(
        {
            "authentication": {
                "algorithm": CHECKPOINT_ALGORITHM,
                "key_id": key_id,
                "signature_sha256": signature,
            },
            "body": body,
        }
    )


def _restore_relation(
    digest: str,
    registry: ReceiptRegistry,
) -> CommittedModeRelation:
    payload = registry.resolve(digest, "restored committed relation")
    value = _strict_object(payload, "restored committed relation")
    if value.get("schema") != "glew.learning.committed_mode_relation.v1":
        raise ReceiptError("checkpoint relation has another schema")
    relation = CommittedModeRelation(
        relation_id=value["relation_id"],
        profile_binding_sha256=value["profile_binding_sha256"],
        commit_receipt_sha256=value["commit_receipt_sha256"],
        selected_mode_receipt_sha256=value["selected_mode_receipt_sha256"],
        topology_authority_receipt_sha256=(
            value["topology_authority_receipt_sha256"]
        ),
        closed_experience_receipt_sha256=(
            value["closed_experience_receipt_sha256"]
        ),
        expression_receipt_sha256=value["expression_receipt_sha256"],
        recognition_receipt_sha256=value["recognition_receipt_sha256"],
        l6_evaluation_receipt_sha256=(
            value["l6_evaluation_receipt_sha256"]
        ),
        sensory_evidence_receipt_sha256s=tuple(
            value["sensory_evidence_receipt_sha256s"]
        ),
        fact_strand_receipt_sha256=value["fact_strand_receipt_sha256"],
        authority_receipt_sha256=digest,
    )
    relation.verify(registry)
    return relation


def _restore_output_bank(
    digest: str,
    registry: ReceiptRegistry,
) -> MotifBindingBank:
    payload = registry.resolve(digest, "restored output bank")
    value = _strict_object(payload, "restored output bank")
    if value.get("schema") != "glew.output.motif_binding_bank.v1":
        raise ReceiptError("checkpoint output bank has another schema")
    if not isinstance(value.get("bindings"), list):
        raise ReceiptError("checkpoint output bank bindings are malformed")
    bindings = []
    for entry in value["bindings"]:
        binding_digest = entry["binding_receipt_sha256"]
        binding_payload = registry.resolve(
            binding_digest,
            "restored output binding",
        )
        item = _strict_object(binding_payload, "restored output binding")
        from .language import BalancedTrit

        bindings.append(
            MotifOutputBinding(
                binding_id=item["binding_id"],
                profile_binding_sha256=item["profile_binding_sha256"],
                motif_receipt_sha256=item["motif_receipt_sha256"],
                closed_experience_receipt_sha256=(
                    item["closed_experience_receipt_sha256"]
                ),
                fact_strand_receipt_sha256=(
                    item["fact_strand_receipt_sha256"]
                ),
                sensory_evidence_receipt_sha256s=tuple(
                    item["sensory_evidence_receipt_sha256s"]
                ),
                coexperienced_output_receipt_sha256=(
                    item["coexperienced_output_receipt_sha256"]
                ),
                kind=OutputBindingKind(item["kind"]),
                trits=tuple(
                    BalancedTrit(
                        scalar_index=trit["scalar_index"],
                        place=trit["place"],
                        value=trit["value"],
                        valid=trit["valid"],
                    )
                    for trit in item["trits"]
                ),
                language_scalar_cardinality=(
                    item["language_scalar_cardinality"]
                ),
                no_output_cardinality=item["no_output_cardinality"],
                binding_receipt_sha256=binding_digest,
            )
        )
    bank = MotifBindingBank(
        bank_id=value["bank_id"],
        profile_binding_sha256=value["profile_binding_sha256"],
        bindings=tuple(bindings),
        bank_receipt_sha256=digest,
        bank_receipt_payload=payload,
    )
    bank.verify_for_motif(registry, None)
    return bank


def _restore_stable_bank(
    digest: str,
    registry: ReceiptRegistry,
) -> StableModeMotifBank:
    payload = registry.resolve(digest, "restored stable bank")
    value = _strict_object(payload, "restored stable bank")
    if value.get("schema") != "glew.recall.stable_mode_motif_bank.v2":
        # A checkpoint written under the pre-Requirement-2 single-successor
        # binding shape is schema-incompatible; fail closed rather than restore
        # a silently corrupt bank.  The clean path is a fresh reseed via
        # ``seed_first_production_successor.py`` (design section 7).
        raise ReceiptError("checkpoint stable bank has another schema")
    if not isinstance(value.get("bindings"), list):
        raise ReceiptError("checkpoint stable bank bindings are malformed")
    bindings = []
    for entry in value["bindings"]:
        binding_digest = entry["binding_receipt_sha256"]
        binding_payload = registry.resolve(
            binding_digest,
            "restored stable binding",
        )
        item = _strict_object(binding_payload, "restored stable binding")
        for required in (
            "transition_context_receipt_sha256",
            "transition_context_match_sha256",
        ):
            if required not in item:
                raise ReceiptError(
                    "checkpoint stable binding lacks its transition-context "
                    "fields; reseed under the current schema"
                )
        bindings.append(
            StableModeMotifBinding(
                binding_id=item["binding_id"],
                profile_binding_sha256=item["profile_binding_sha256"],
                mode_receipt_sha256=item["mode_receipt_sha256"],
                motif_receipt_sha256=item["motif_receipt_sha256"],
                source_fact_strand_receipt_sha256=(
                    item["source_fact_strand_receipt_sha256"]
                ),
                transition_context_receipt_sha256=(
                    item["transition_context_receipt_sha256"]
                ),
                transition_context_match_sha256=(
                    item["transition_context_match_sha256"]
                ),
                binding_receipt_sha256=binding_digest,
            )
        )
    return StableModeMotifBank(
        bank_id=value["bank_id"],
        profile_binding_sha256=value["profile_binding_sha256"],
        bindings=tuple(bindings),
        bank_receipt_sha256=digest,
        bank_receipt_payload=payload,
    )


def _restore_event(
    digest: str,
    registry: ReceiptRegistry,
) -> CommittedMotifEvent:
    value = _strict_object(
        registry.resolve(digest, "restored initial event"),
        "restored initial event",
    )
    if value.get("schema") != "glew.output.committed_motif_event.v1":
        raise ReceiptError("checkpoint initial event has another schema")
    return CommittedMotifEvent(
        expression_id=value["expression_id"],
        event_id=value["event_id"],
        event_kind=MotifEventKind(value["event_kind"]),
        profile_binding_sha256=value["profile_binding_sha256"],
        motif_receipt_sha256=value["motif_receipt_sha256"],
        closed_experience_receipt_sha256=(
            value["closed_experience_receipt_sha256"]
        ),
        fact_strand_receipt_sha256=value["fact_strand_receipt_sha256"],
        sensory_evidence_receipt_sha256s=tuple(
            value["sensory_evidence_receipt_sha256s"]
        ),
        full_field_state_receipt_sha256=(
            value["full_field_state_receipt_sha256"]
        ),
        field_commit_receipt_sha256=value["field_commit_receipt_sha256"],
        dominant_motif_commit_receipt_sha256=(
            value["dominant_motif_commit_receipt_sha256"]
        ),
        corrected_l6_lock_receipt_sha256=(
            value["corrected_l6_lock_receipt_sha256"]
        ),
        output_binding_bank_receipt_sha256=(
            value["output_binding_bank_receipt_sha256"]
        ),
        source_state_receipt_sha256=value["source_state_receipt_sha256"],
        transition_edge_receipt_sha256=(
            value["transition_edge_receipt_sha256"]
        ),
        result_state_receipt_sha256=value["result_state_receipt_sha256"],
        expression_close_authority_receipt_sha256=(
            value["expression_close_authority_receipt_sha256"]
        ),
        event_receipt_sha256=digest,
    )


def restore_learned_binding_checkpoint(
    *,
    checkpoint_payload: bytes,
    authentication_key: bytes,
    expected_key_id: str,
) -> LearnedBindingState:
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("learned checkpoint authentication key is absent")
    require_identifier(expected_key_id, "learned checkpoint expected key id")
    envelope = _strict_object(
        checkpoint_payload,
        "learned binding checkpoint envelope",
    )
    if set(envelope) != {"authentication", "body"}:
        raise ReceiptError("learned checkpoint envelope fields changed")
    authentication = envelope["authentication"]
    body = envelope["body"]
    if not isinstance(authentication, dict) or not isinstance(body, dict):
        raise ReceiptError("learned checkpoint envelope is malformed")
    if (
        authentication.get("algorithm") != CHECKPOINT_ALGORITHM
        or authentication.get("key_id") != expected_key_id
    ):
        raise ReceiptError("learned checkpoint authentication authority changed")
    expected_signature = hmac.new(
        authentication_key,
        _canonical_bytes(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(
        authentication.get("signature_sha256", ""),
        expected_signature,
    ):
        raise ReceiptError("learned checkpoint authentication failed")
    if body.get("schema") != "glew.learning.binding_checkpoint.v1":
        raise ReceiptError("learned checkpoint schema changed")
    records = []
    for value in body.get("receipt_records", []):
        if not isinstance(value, dict):
            raise ReceiptError("learned checkpoint receipt record is malformed")
        try:
            payload = bytes.fromhex(value["payload_hex"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReceiptError("learned checkpoint receipt hex is invalid") from exc
        digest = value.get("sha256")
        if not isinstance(digest, str) or receipt_sha256(payload) != digest:
            raise ReceiptError("learned checkpoint receipt digest changed")
        records.append(ReceiptRecord(digest, payload))
    registry = ReceiptRegistry(
        body["profile_binding_sha256"],
        tuple(records),
    )
    state_digest = body["state_receipt_sha256"]
    state_payload = registry.resolve(state_digest, "restored learned state")
    value = _strict_object(state_payload, "restored learned state")
    if value.get("schema") != "glew.learning.binding_state.v1":
        raise ReceiptError("checkpoint learned state has another schema")
    initial_relation = _restore_relation(
        value["initial_relation_receipt_sha256"],
        registry,
    )
    pending_digest = value["pending_relation_receipt_sha256"]
    pending = (
        None
        if pending_digest is None
        else _restore_relation(pending_digest, registry)
    )
    output_bank = _restore_output_bank(
        value["output_bank_receipt_sha256"],
        registry,
    )
    stable_bank = _restore_stable_bank(
        value["stable_bank_receipt_sha256"],
        registry,
    )
    motif_kinds = []
    for digest in value["motif_kind_authority_receipt_sha256s"]:
        item = _strict_object(
            registry.resolve(digest, "restored motif-kind authority"),
            "restored motif-kind authority",
        )
        motif_kinds.append(
            RememberedMotifKindAuthority(
                motif_receipt_sha256=item["motif_receipt_sha256"],
                kind=RememberedMotifKind(item["kind"]),
                source_closed_experience_receipt_sha256=(
                    item["source_closed_experience_receipt_sha256"]
                ),
                authority_receipt_sha256=digest,
            )
        )
    event_digest = value["initial_event_receipt_sha256"]
    state = LearnedBindingState(
        state_id=value["state_id"],
        expression_id=value["expression_id"],
        output_bank=output_bank,
        stable_bank=stable_bank,
        initial_relation=initial_relation,
        pending_relation=pending,
        initial_event=(
            None
            if event_digest is None
            else _restore_event(event_digest, registry)
        ),
        motif_kinds=tuple(motif_kinds),
        terminal=value["terminal"],
        receipt_registry=registry,
        receipt_sha256=state_digest,
        receipt_payload=state_payload,
    )
    state.verify()
    return state


__all__ = (
    "CoexperiencedNoOutput",
    "CoexperiencedOutput",
    "CoexperiencedOutputKind",
    "CommittedCoexperience",
    "CommittedModeRelation",
    "LearnedBindingState",
    "coexperienced_no_output_receipt_payload",
    "create_coexperienced_no_output",
    "create_learned_binding_genesis",
    "derive_committed_mode_relation",
    "learn_committed_binding_transaction",
    "learned_binding_checkpoint_payload",
    "restore_learned_binding_checkpoint",
)
