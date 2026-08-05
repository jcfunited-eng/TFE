"""Receipted experience origin and the separate persistence-energy boundary.

Expression recognition and output are permitted to settle in a quiet field.
They therefore verify ``R_event`` but never use its magnitude as an output
veto.  Persistence is a different physical act: only fresh external input or
an explicitly identified story-emulator event with positive exact ``R_event``
can fund mode or memory growth.

Self-generated recall keeps every cited sensory trace in the full DSF field,
but those remembered traces are not new environmental energy.  Its origin
therefore derives an exact-zero ``R_event`` authority.  No threshold, score,
purpose flag, or fallback participates in either decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .commit import (
    ApplicabilityState,
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    ClosedExperienceSeal,
    CommitDecision,
    CommitStatus,
    EventSupportAuthority,
    EventSupportState,
    GovernedFact,
    L5Applicability,
    L6ScopeAuthority,
    _verify_l6_internal,
    event_support_authority_receipt_payload,
)
from .expression_modes import (
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
)
from .field import (
    EvidenceValidityState,
    MountedFieldTopology,
    PortTransportEvidence,
    StructuralFactState,
)
from .l6 import L6Evaluation, L6EvaluationStatus
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)


ORIGIN_OPERATOR_ID = "glew.experience_origin_provenance.v1"
GROWTH_OPERATOR_ID = "glew.origin_bound_persistence_energy.v1"
RECALL_EVENT_SUPPORT_OPERATOR_ID = (
    "glew.self_generated_recall_zero_fresh_event_support.v1"
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


class ExperienceOriginKind(str, Enum):
    FRESH_EXTERNAL = "fresh_external"
    EXPLICIT_STORY_EMULATOR = "explicit_story_emulator"
    SELF_GENERATED_RECALL = "self_generated_recall"


def experience_origin_authority_receipt_payload(
    *,
    origin_id: str,
    kind: ExperienceOriginKind,
    profile_binding_sha256: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    source_authority_receipt_sha256: str,
) -> bytes:
    require_identifier(origin_id, "experience origin id")
    if not isinstance(kind, ExperienceOriginKind):
        raise ReceiptError("experience origin kind is not typed")
    for value, description in (
        (profile_binding_sha256, "origin profile receipt"),
        (topology_authority_receipt_sha256, "origin topology receipt"),
        (closed_experience_receipt_sha256, "origin closed-experience receipt"),
        (source_authority_receipt_sha256, "origin source-authority receipt"),
    ):
        sha256_digest(value, description)
    return _canonical_bytes(
        {
            "schema": "glew.experience_origin.authority.v1",
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "kind": kind.value,
            "operator_id": ORIGIN_OPERATOR_ID,
            "origin_id": origin_id,
            "profile_binding_sha256": profile_binding_sha256,
            "source_authority_receipt_sha256": (
                source_authority_receipt_sha256
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class ExperienceOriginAuthority:
    origin_id: str
    kind: ExperienceOriginKind
    profile_binding_sha256: str
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    source_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return experience_origin_authority_receipt_payload(
            origin_id=self.origin_id,
            kind=self.kind,
            profile_binding_sha256=self.profile_binding_sha256,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                self.source_authority_receipt_sha256
            ),
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("experience origin belongs to another GLEW profile")
        receipt_registry.resolve(
            self.source_authority_receipt_sha256,
            "experience origin source-authority receipt",
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "experience origin authority receipt",
        )


@dataclass(frozen=True, slots=True)
class RecallEventSupportMaterial:
    authority: EventSupportAuthority
    authority_receipt_payload: bytes

    def __post_init__(self) -> None:
        if self.authority.state is not EventSupportState.ZERO:
            raise ReceiptError("recall event support must be exact zero")
        if self.authority.exact_r_event != Fraction(0):
            raise ReceiptError("recall event support lost exact zero")
        if (
            receipt_sha256(self.authority_receipt_payload)
            != self.authority.authority_receipt_sha256
        ):
            raise ReceiptError("recall event support differs from exact bytes")


def create_self_generated_recall_event_support(
    origin: ExperienceOriginAuthority,
) -> RecallEventSupportMaterial:
    """Derive zero *fresh* event energy without removing remembered senses."""

    if not isinstance(origin, ExperienceOriginAuthority):
        raise ReceiptError("recall R_event requires a typed experience origin")
    if origin.kind is not ExperienceOriginKind.SELF_GENERATED_RECALL:
        raise ReceiptError("only self-generated recall derives recall-zero R_event")
    authority_id = f"{origin.origin_id}:fresh-R-event"
    payload = event_support_authority_receipt_payload(
        authority_id=authority_id,
        state=EventSupportState.ZERO,
        exact_r_event=Fraction(0),
        topology_authority_receipt_sha256=(
            origin.topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            origin.closed_experience_receipt_sha256
        ),
        source_operator_receipt_sha256=origin.authority_receipt_sha256,
    )
    authority = EventSupportAuthority(
        authority_id=authority_id,
        state=EventSupportState.ZERO,
        exact_r_event=Fraction(0),
        topology_authority_receipt_sha256=(
            origin.topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            origin.closed_experience_receipt_sha256
        ),
        source_operator_receipt_sha256=origin.authority_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    return RecallEventSupportMaterial(authority, payload)


class FieldAdmissionDisposition(str, Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


def field_admission_receipt_payload(
    *,
    disposition: FieldAdmissionDisposition,
    origin_authority_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    recognition_receipt_sha256: str,
    l6_evaluation_receipt_sha256: str,
    safe_mode_receipt_sha256: str,
    event_support_receipt_sha256: str,
    global_uf_receipt_sha256: str,
    evidence_receipt_sha256s: tuple[str, ...],
    applicability_receipt_sha256s: tuple[str, ...],
    findings: tuple[str, ...],
) -> bytes:
    if not isinstance(disposition, FieldAdmissionDisposition):
        raise ReceiptError("field-admission disposition is not typed")
    for value, description in (
        (origin_authority_receipt_sha256, "admission origin receipt"),
        (topology_authority_receipt_sha256, "admission topology receipt"),
        (closed_experience_receipt_sha256, "admission experience receipt"),
        (recognition_receipt_sha256, "admission recognition receipt"),
        (l6_evaluation_receipt_sha256, "admission L6 receipt"),
        (safe_mode_receipt_sha256, "admission SafeMode receipt"),
        (event_support_receipt_sha256, "admission R_event receipt"),
        (global_uf_receipt_sha256, "admission global-UF receipt"),
    ):
        sha256_digest(value, description)
    for values, description in (
        (evidence_receipt_sha256s, "admission evidence receipts"),
        (applicability_receipt_sha256s, "admission applicability receipts"),
    ):
        if not isinstance(values, tuple):
            raise ReceiptError(f"{description} must be an immutable tuple")
        for index, value in enumerate(values):
            sha256_digest(value, f"{description}[{index}]")
    if not isinstance(findings, tuple) or any(
        not isinstance(value, str) or not value for value in findings
    ):
        raise ReceiptError("field-admission findings must be immutable identifiers")
    if disposition is FieldAdmissionDisposition.ADMITTED and findings:
        raise ReceiptError("an admitted field cannot carry failure findings")
    if disposition is not FieldAdmissionDisposition.ADMITTED and not findings:
        raise ReceiptError("a non-admitted field must state exact findings")
    return _canonical_bytes(
        {
            "applicability_receipt_sha256s": list(
                applicability_receipt_sha256s
            ),
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "disposition": disposition.value,
            "event_support_receipt_sha256": event_support_receipt_sha256,
            "evidence_receipt_sha256s": list(evidence_receipt_sha256s),
            "findings": list(findings),
            "global_uf_receipt_sha256": global_uf_receipt_sha256,
            "l6_evaluation_receipt_sha256": l6_evaluation_receipt_sha256,
            "operator_id": "glew.non_output_full_field_admission.v1",
            "origin_authority_receipt_sha256": (
                origin_authority_receipt_sha256
            ),
            "recognition_receipt_sha256": recognition_receipt_sha256,
            "safe_mode_receipt_sha256": safe_mode_receipt_sha256,
            "schema": "glew.growth.full_field_admission.v1",
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class FieldAdmission:
    disposition: FieldAdmissionDisposition
    origin_authority_receipt_sha256: str
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    recognition_receipt_sha256: str
    l6_evaluation_receipt_sha256: str
    safe_mode_receipt_sha256: str
    event_support_receipt_sha256: str
    global_uf_receipt_sha256: str
    evidence_receipt_sha256s: tuple[str, ...]
    applicability_receipt_sha256s: tuple[str, ...]
    findings: tuple[str, ...]
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        expected = field_admission_receipt_payload(
            disposition=self.disposition,
            origin_authority_receipt_sha256=(
                self.origin_authority_receipt_sha256
            ),
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            l6_evaluation_receipt_sha256=self.l6_evaluation_receipt_sha256,
            safe_mode_receipt_sha256=self.safe_mode_receipt_sha256,
            event_support_receipt_sha256=self.event_support_receipt_sha256,
            global_uf_receipt_sha256=self.global_uf_receipt_sha256,
            evidence_receipt_sha256s=self.evidence_receipt_sha256s,
            applicability_receipt_sha256s=(
                self.applicability_receipt_sha256s
            ),
            findings=self.findings,
        )
        if (
            self.receipt_payload != expected
            or self.receipt_sha256 != receipt_sha256(expected)
        ):
            raise ReceiptError("field admission differs from exact receipt bytes")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for value, description in (
            (self.origin_authority_receipt_sha256, "admission origin receipt"),
            (self.topology_authority_receipt_sha256, "admission topology receipt"),
            (
                self.closed_experience_receipt_sha256,
                "admission experience receipt",
            ),
            (self.recognition_receipt_sha256, "admission recognition receipt"),
            (self.l6_evaluation_receipt_sha256, "admission L6 receipt"),
            (self.safe_mode_receipt_sha256, "admission SafeMode receipt"),
            (self.event_support_receipt_sha256, "admission R_event receipt"),
            (self.global_uf_receipt_sha256, "admission global-UF receipt"),
            *(
                (value, "admission evidence receipt")
                for value in self.evidence_receipt_sha256s
            ),
            *(
                (value, "admission applicability receipt")
                for value in self.applicability_receipt_sha256s
            ),
        ):
            receipt_registry.resolve(value, description)
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            self.receipt_payload,
            "field-admission receipt",
        )


def evaluate_field_admission(
    *,
    origin: ExperienceOriginAuthority,
    topology: MountedFieldTopology,
    recognition: ExpressionModeBoundaryResult,
    l6_evaluation: L6Evaluation,
    l6_scope: L6ScopeAuthority,
    closed_experience: ClosedExperienceSeal,
    safe_mode: BinaryCommitAuthority,
    event_support: EventSupportAuthority,
    evidence: tuple[PortTransportEvidence, ...],
    l5_applicability: tuple[L5Applicability, ...],
    global_uf_validation: BinaryCommitAuthority,
    receipt_registry: ReceiptRegistry,
) -> FieldAdmission:
    """Verify a full field independently of recognition/output selection."""

    if not isinstance(evidence, tuple) or not all(
        isinstance(value, PortTransportEvidence) for value in evidence
    ):
        raise ReceiptError("field admission requires immutable typed evidence")
    if not isinstance(l5_applicability, tuple) or not all(
        isinstance(value, L5Applicability) for value in l5_applicability
    ):
        raise ReceiptError("field admission requires immutable L5 applicability")

    topology.verify(receipt_registry)
    recognition.verify()
    recognition.pre_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    recognition.post_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    _mounted_exact(
        receipt_registry,
        recognition.receipt_sha256,
        recognition.receipt_payload,
        "field-admission recognition receipt",
    )
    closed_experience.verify(
        topology=topology,
        recognition=recognition,
        evidence=evidence,
        receipt_registry=receipt_registry,
    )
    topology_receipt = topology.authority_receipt_sha256
    experience_receipt = closed_experience.authority_receipt_sha256
    origin.verify(receipt_registry)
    if (
        origin.topology_authority_receipt_sha256 != topology_receipt
        or origin.closed_experience_receipt_sha256 != experience_receipt
    ):
        raise ReceiptError("field-admission origin names a different closed field")
    safe_mode.verify(
        expected_kind=BinaryAuthorityKind.SAFE_MODE_CLEAR,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    global_uf_validation.verify(
        expected_kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    event_support.verify(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    _verify_l6_internal(l6_evaluation)
    l6_scope.verify(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        evaluation=l6_evaluation,
        receipt_registry=receipt_registry,
    )

    unknown: list[str] = []
    rejected: list[str] = []
    if recognition.status is ExpressionRecognitionStatus.UNKNOWN:
        unknown.append("field_expression_unknown")
    if safe_mode.disposition is AuthorityDisposition.UNKNOWN:
        unknown.append("safe_mode_unknown")
    elif safe_mode.disposition is AuthorityDisposition.FAIL:
        rejected.append("safe_mode_active")
    if global_uf_validation.disposition is AuthorityDisposition.UNKNOWN:
        unknown.append("global_uf_validation_unknown")
    elif global_uf_validation.disposition is AuthorityDisposition.FAIL:
        rejected.append("global_uf_validation_failed")
    if l6_evaluation.status is L6EvaluationStatus.UNKNOWN_NO_LOCK:
        unknown.append("fixed42_L6_unknown")
    elif l6_evaluation.status is L6EvaluationStatus.NO_LOCK:
        rejected.append("fixed42_L6_no_lock")

    topology_keys = tuple(value.key for value in topology.ordered_port_fibers)
    evidence_keys = tuple(value.key for value in evidence)
    if set(evidence_keys) != set(topology_keys):
        unknown.append("typed_evidence_does_not_cover_mounted_topology")
    evidence_by_key: dict[tuple[str, str], list[PortTransportEvidence]] = {}
    seen_evidence: set[str] = set()
    for value in evidence:
        value.verify(receipt_registry)
        if value.evidence_receipt_sha256 in seen_evidence:
            raise ReceiptError("field admission repeats typed evidence")
        seen_evidence.add(value.evidence_receipt_sha256)
        evidence_by_key.setdefault(value.key, []).append(value)
        if not (
            closed_experience.source_time_start
            <= value.provenance.source_timestamp
            <= closed_experience.source_time_end
        ):
            raise ReceiptError("field-admission evidence lies outside experience")
        if value.validity.state is EvidenceValidityState.UNKNOWN:
            unknown.append(f"evidence_unknown:{value.lane_id}:{value.port_id}")
        elif value.validity.state is EvidenceValidityState.INVALID:
            rejected.append(f"evidence_invalid:{value.lane_id}:{value.port_id}")

    expected_applicability_keys = tuple(
        (fiber.lane_id, fiber.port_id, fact)
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    if tuple(value.key for value in l5_applicability) != expected_applicability_keys:
        raise ReceiptError(
            "field-admission L5 applicability lacks canonical topology coverage"
        )
    for applicability in l5_applicability:
        applicability.verify(
            topology_receipt=topology_receipt,
            experience_receipt=experience_receipt,
            receipt_registry=receipt_registry,
        )
        if applicability.state is ApplicabilityState.UNKNOWN:
            unknown.append(
                f"L5_applicability_unknown:{applicability.lane_id}:"
                f"{applicability.port_id}:{applicability.fact.value}"
            )
            continue
        if applicability.state is ApplicabilityState.NOT_APPLICABLE:
            continue
        for record in evidence_by_key.get(
            (applicability.lane_id, applicability.port_id),
            (),
        ):
            state = (
                record.support_floor.state
                if applicability.fact is GovernedFact.S_UF
                else record.resonance.state
            )
            if state is not StructuralFactState.AVAILABLE:
                unknown.append(
                    f"required_{applicability.fact.value}_unavailable:"
                    f"{applicability.lane_id}:{applicability.port_id}"
                )

    findings = tuple((*unknown, *rejected))
    if unknown:
        disposition = FieldAdmissionDisposition.UNKNOWN
    elif rejected:
        disposition = FieldAdmissionDisposition.REJECTED
    else:
        disposition = FieldAdmissionDisposition.ADMITTED
    payload = field_admission_receipt_payload(
        disposition=disposition,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        recognition_receipt_sha256=recognition.receipt_sha256,
        l6_evaluation_receipt_sha256=l6_scope.l6_evaluation_receipt_sha256,
        safe_mode_receipt_sha256=safe_mode.authority_receipt_sha256,
        event_support_receipt_sha256=event_support.authority_receipt_sha256,
        global_uf_receipt_sha256=global_uf_validation.authority_receipt_sha256,
        evidence_receipt_sha256s=tuple(
            value.evidence_receipt_sha256 for value in evidence
        ),
        applicability_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in l5_applicability
        ),
        findings=findings,
    )
    return FieldAdmission(
        disposition=disposition,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        recognition_receipt_sha256=recognition.receipt_sha256,
        l6_evaluation_receipt_sha256=l6_scope.l6_evaluation_receipt_sha256,
        safe_mode_receipt_sha256=safe_mode.authority_receipt_sha256,
        event_support_receipt_sha256=event_support.authority_receipt_sha256,
        global_uf_receipt_sha256=global_uf_validation.authority_receipt_sha256,
        evidence_receipt_sha256s=tuple(
            value.evidence_receipt_sha256 for value in evidence
        ),
        applicability_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in l5_applicability
        ),
        findings=findings,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def committed_mode_relation_authority_receipt_payload(
    *,
    relation_id: str,
    profile_binding_sha256: str,
    prior_commit_receipt_sha256: str,
    current_commit_receipt_sha256: str,
    prior_mode_receipt_sha256: str,
    current_mode_receipt_sha256: str,
    current_recognition_receipt_sha256: str,
) -> bytes:
    require_identifier(relation_id, "committed mode-relation id")
    for value, description in (
        (profile_binding_sha256, "relation profile receipt"),
        (prior_commit_receipt_sha256, "prior commit receipt"),
        (current_commit_receipt_sha256, "current commit receipt"),
        (prior_mode_receipt_sha256, "prior mode receipt"),
        (current_mode_receipt_sha256, "current mode receipt"),
        (current_recognition_receipt_sha256, "current recognition receipt"),
    ):
        sha256_digest(value, description)
    return _canonical_bytes(
        {
            "current_commit_receipt_sha256": current_commit_receipt_sha256,
            "current_mode_receipt_sha256": current_mode_receipt_sha256,
            "current_recognition_receipt_sha256": (
                current_recognition_receipt_sha256
            ),
            "prior_commit_receipt_sha256": prior_commit_receipt_sha256,
            "prior_mode_receipt_sha256": prior_mode_receipt_sha256,
            "profile_binding_sha256": profile_binding_sha256,
            "relation_id": relation_id,
            "schema": "glew.growth.committed_mode_relation.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class CommittedModeRelationAuthority:
    relation_id: str
    profile_binding_sha256: str
    prior_commit_receipt_sha256: str
    current_commit_receipt_sha256: str
    prior_mode_receipt_sha256: str
    current_mode_receipt_sha256: str
    current_recognition_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return committed_mode_relation_authority_receipt_payload(
            relation_id=self.relation_id,
            profile_binding_sha256=self.profile_binding_sha256,
            prior_commit_receipt_sha256=self.prior_commit_receipt_sha256,
            current_commit_receipt_sha256=self.current_commit_receipt_sha256,
            prior_mode_receipt_sha256=self.prior_mode_receipt_sha256,
            current_mode_receipt_sha256=self.current_mode_receipt_sha256,
            current_recognition_receipt_sha256=(
                self.current_recognition_receipt_sha256
            ),
        )

    def verify(
        self,
        *,
        prior_commit: CommitDecision,
        current_commit: CommitDecision,
        current_recognition: ExpressionModeBoundaryResult,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("committed mode relation belongs to another profile")
        for value in (prior_commit, current_commit):
            value.verify()
            _mounted_exact(
                receipt_registry,
                value.receipt_sha256,
                value.receipt_payload,
                "committed mode-relation commit receipt",
            )
            if (
                value.status is not CommitStatus.COMMIT
                or value.selected_mode_receipt_sha256 is None
            ):
                raise ReceiptError("memory growth relation requires two real commits")
        if (
            self.prior_commit_receipt_sha256 != prior_commit.receipt_sha256
            or self.current_commit_receipt_sha256 != current_commit.receipt_sha256
            or self.prior_mode_receipt_sha256
            != prior_commit.selected_mode_receipt_sha256
            or self.current_mode_receipt_sha256
            != current_commit.selected_mode_receipt_sha256
            or self.current_recognition_receipt_sha256
            != current_recognition.receipt_sha256
            or current_commit.expression_recognition_receipt_sha256
            != current_recognition.receipt_sha256
        ):
            raise ReceiptError("committed mode relation names different endpoints")
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "committed mode-relation authority receipt",
        )


class PersistenceDisposition(str, Enum):
    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNKNOWN = "unknown"


def growth_eligibility_receipt_payload(
    *,
    mode_growth: PersistenceDisposition,
    memory_growth: PersistenceDisposition,
    origin_authority_receipt_sha256: str,
    field_admission_receipt_sha256: str,
    event_support_authority_receipt_sha256: str,
    recognition_receipt_sha256: str,
    committed_relation_authority_receipt_sha256: str | None,
    mode_reason: str,
    memory_reason: str,
) -> bytes:
    for value, description in (
        (origin_authority_receipt_sha256, "growth origin receipt"),
        (field_admission_receipt_sha256, "growth admission receipt"),
        (event_support_authority_receipt_sha256, "growth R_event receipt"),
        (recognition_receipt_sha256, "growth recognition receipt"),
    ):
        sha256_digest(value, description)
    if not isinstance(mode_growth, PersistenceDisposition) or not isinstance(
        memory_growth, PersistenceDisposition
    ):
        raise ReceiptError("growth dispositions are not typed")
    if committed_relation_authority_receipt_sha256 is not None:
        sha256_digest(
            committed_relation_authority_receipt_sha256,
            "growth committed-relation receipt",
        )
    require_identifier(mode_reason, "mode-growth reason")
    require_identifier(memory_reason, "memory-growth reason")
    if (
        memory_growth is PersistenceDisposition.AUTHORIZED
        and committed_relation_authority_receipt_sha256 is None
    ):
        raise ReceiptError("memory growth lacks a committed relation authority")
    return _canonical_bytes(
        {
            "committed_relation_authority_receipt_sha256": (
                committed_relation_authority_receipt_sha256
            ),
            "event_support_authority_receipt_sha256": (
                event_support_authority_receipt_sha256
            ),
            "field_admission_receipt_sha256": field_admission_receipt_sha256,
            "memory_growth": memory_growth.value,
            "memory_reason": memory_reason,
            "mode_growth": mode_growth.value,
            "mode_reason": mode_reason,
            "operator_id": GROWTH_OPERATOR_ID,
            "origin_authority_receipt_sha256": (
                origin_authority_receipt_sha256
            ),
            "recognition_receipt_sha256": recognition_receipt_sha256,
            "schema": "glew.growth.persistence_eligibility.v2",
        }
    )


@dataclass(frozen=True, slots=True)
class GrowthEligibility:
    mode_growth: PersistenceDisposition
    memory_growth: PersistenceDisposition
    origin_authority_receipt_sha256: str
    field_admission_receipt_sha256: str
    event_support_authority_receipt_sha256: str
    recognition_receipt_sha256: str
    committed_relation_authority_receipt_sha256: str | None
    mode_reason: str
    memory_reason: str
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        expected = growth_eligibility_receipt_payload(
            mode_growth=self.mode_growth,
            memory_growth=self.memory_growth,
            origin_authority_receipt_sha256=(
                self.origin_authority_receipt_sha256
            ),
            field_admission_receipt_sha256=self.field_admission_receipt_sha256,
            event_support_authority_receipt_sha256=(
                self.event_support_authority_receipt_sha256
            ),
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            committed_relation_authority_receipt_sha256=(
                self.committed_relation_authority_receipt_sha256
            ),
            mode_reason=self.mode_reason,
            memory_reason=self.memory_reason,
        )
        if (
            self.receipt_payload != expected
            or self.receipt_sha256 != receipt_sha256(expected)
        ):
            raise ReceiptError("growth eligibility differs from exact receipt bytes")

    @property
    def mode_growth_authorized(self) -> bool:
        return self.mode_growth is PersistenceDisposition.AUTHORIZED

    @property
    def memory_growth_authorized(self) -> bool:
        return self.memory_growth is PersistenceDisposition.AUTHORIZED

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for value, description in (
            (self.origin_authority_receipt_sha256, "growth origin receipt"),
            (self.field_admission_receipt_sha256, "growth admission receipt"),
            (
                self.event_support_authority_receipt_sha256,
                "growth R_event receipt",
            ),
            (self.recognition_receipt_sha256, "growth recognition receipt"),
        ):
            receipt_registry.resolve(value, description)
        if self.committed_relation_authority_receipt_sha256 is not None:
            receipt_registry.resolve(
                self.committed_relation_authority_receipt_sha256,
                "growth committed-relation receipt",
            )
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            self.receipt_payload,
            "growth eligibility receipt",
        )


def evaluate_growth_eligibility(
    *,
    origin: ExperienceOriginAuthority,
    field_admission: FieldAdmission,
    event_support: EventSupportAuthority,
    recognition: ExpressionModeBoundaryResult,
    receipt_registry: ReceiptRegistry,
    committed_relation: CommittedModeRelationAuthority | None = None,
    prior_commit: CommitDecision | None = None,
    current_commit: CommitDecision | None = None,
) -> GrowthEligibility:
    """Authorize mode capture and relation memory as separate physical acts."""

    origin.verify(receipt_registry)
    field_admission.verify(receipt_registry)
    recognition.verify()
    _mounted_exact(
        receipt_registry,
        recognition.receipt_sha256,
        recognition.receipt_payload,
        "growth recognition receipt",
    )
    if (
        field_admission.origin_authority_receipt_sha256
        != origin.authority_receipt_sha256
        or field_admission.recognition_receipt_sha256
        != recognition.receipt_sha256
        or field_admission.event_support_receipt_sha256
        != event_support.authority_receipt_sha256
    ):
        raise ReceiptError("growth inputs do not describe one admitted field")
    event_support.verify(
        topology_receipt=origin.topology_authority_receipt_sha256,
        experience_receipt=origin.closed_experience_receipt_sha256,
        receipt_registry=receipt_registry,
    )

    relation_inputs = (committed_relation, prior_commit, current_commit)
    if any(value is None for value in relation_inputs) and any(
        value is not None for value in relation_inputs
    ):
        raise ReceiptError("memory growth relation inputs must be complete or absent")
    relation_receipt: str | None = None
    if committed_relation is not None:
        assert prior_commit is not None
        assert current_commit is not None
        committed_relation.verify(
            prior_commit=prior_commit,
            current_commit=current_commit,
            current_recognition=recognition,
            receipt_registry=receipt_registry,
        )
        relation_receipt = committed_relation.authority_receipt_sha256

    if origin.kind is ExperienceOriginKind.SELF_GENERATED_RECALL:
        if (
            event_support.state is not EventSupportState.ZERO
            or event_support.exact_r_event != Fraction(0)
        ):
            raise ReceiptError(
                "self-generated recall must carry origin-derived exact-zero fresh R_event"
            )
        mode_growth = PersistenceDisposition.NOT_AUTHORIZED
        memory_growth = PersistenceDisposition.NOT_AUTHORIZED
        mode_reason = "self_generated_recall_has_no_fresh_growth_energy"
        memory_reason = "self_generated_recall_has_no_fresh_growth_energy"
    elif field_admission.disposition is FieldAdmissionDisposition.UNKNOWN:
        mode_growth = PersistenceDisposition.UNKNOWN
        memory_growth = PersistenceDisposition.UNKNOWN
        mode_reason = "full_field_admission_unknown"
        memory_reason = "full_field_admission_unknown"
    elif event_support.state is EventSupportState.UNKNOWN:
        mode_growth = PersistenceDisposition.UNKNOWN
        memory_growth = PersistenceDisposition.UNKNOWN
        mode_reason = "fresh_event_support_unknown"
        memory_reason = "fresh_event_support_unknown"
    elif (
        field_admission.disposition is not FieldAdmissionDisposition.ADMITTED
        or event_support.state is not EventSupportState.POSITIVE
    ):
        mode_growth = PersistenceDisposition.NOT_AUTHORIZED
        memory_growth = PersistenceDisposition.NOT_AUTHORIZED
        mode_reason = "full_field_or_fresh_energy_not_growth_eligible"
        memory_reason = "full_field_or_fresh_energy_not_growth_eligible"
    else:
        if (
            recognition.mutation
            and recognition.status
            in (
                ExpressionRecognitionStatus.BOOTSTRAP_SILENCE,
                ExpressionRecognitionStatus.NOVEL_SILENCE,
            )
        ):
            mode_growth = PersistenceDisposition.AUTHORIZED
            mode_reason = "admitted_positive_innovation_with_fresh_event_energy"
        else:
            mode_growth = PersistenceDisposition.NOT_AUTHORIZED
            mode_reason = "recognition_contains_no_new_mode_mutation"
        if committed_relation is None:
            memory_growth = PersistenceDisposition.NOT_AUTHORIZED
            memory_reason = "no_prior_current_committed_relation_authority"
        else:
            memory_growth = PersistenceDisposition.AUTHORIZED
            memory_reason = "admitted_funded_prior_current_committed_relation"

    payload = growth_eligibility_receipt_payload(
        mode_growth=mode_growth,
        memory_growth=memory_growth,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        field_admission_receipt_sha256=field_admission.receipt_sha256,
        event_support_authority_receipt_sha256=(
            event_support.authority_receipt_sha256
        ),
        recognition_receipt_sha256=recognition.receipt_sha256,
        committed_relation_authority_receipt_sha256=relation_receipt,
        mode_reason=mode_reason,
        memory_reason=memory_reason,
    )
    return GrowthEligibility(
        mode_growth=mode_growth,
        memory_growth=memory_growth,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        field_admission_receipt_sha256=field_admission.receipt_sha256,
        event_support_authority_receipt_sha256=(
            event_support.authority_receipt_sha256
        ),
        recognition_receipt_sha256=recognition.receipt_sha256,
        committed_relation_authority_receipt_sha256=relation_receipt,
        mode_reason=mode_reason,
        memory_reason=memory_reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


__all__ = (
    "CommittedModeRelationAuthority",
    "ExperienceOriginAuthority",
    "ExperienceOriginKind",
    "FieldAdmission",
    "FieldAdmissionDisposition",
    "GROWTH_OPERATOR_ID",
    "GrowthEligibility",
    "ORIGIN_OPERATOR_ID",
    "PersistenceDisposition",
    "RECALL_EVENT_SUPPORT_OPERATOR_ID",
    "RecallEventSupportMaterial",
    "committed_mode_relation_authority_receipt_payload",
    "create_self_generated_recall_event_support",
    "evaluate_field_admission",
    "evaluate_growth_eligibility",
    "experience_origin_authority_receipt_payload",
    "field_admission_receipt_payload",
    "growth_eligibility_receipt_payload",
)
