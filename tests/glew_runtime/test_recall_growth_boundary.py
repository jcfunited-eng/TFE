"""Zero fresh event energy permits expression but never persistence growth."""

from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import (
    ApplicabilityState,
    AuthorityDisposition,
    BinaryAuthorityKind,
    ClosedExperienceSeal,
    CommitStatus,
    EventSupportAuthority,
    EventSupportState,
    GovernedFact,
    L5Applicability,
    L6ScopeAuthority,
    closed_experience_seal_receipt_payload,
    evaluate_commit_boundary,
    event_support_authority_receipt_payload,
    l5_applicability_receipt_payload,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    FieldAdmissionDisposition,
    PersistenceDisposition,
    create_self_generated_recall_event_support,
    evaluate_field_admission,
    evaluate_growth_eligibility,
    experience_origin_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from tests.glew_runtime.test_full_field_commit_boundary import (
    _binary,
    _bundle,
    _l6_lock,
)


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    existing = {record.digest: record.payload for record in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        if digest in existing and existing[digest] != payload:
            raise AssertionError("test receipt collision")
        existing[digest] = payload
    profile_payload = registry.resolve(
        registry.profile_binding_sha256,
        "test profile receipt",
    )
    return ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=tuple(
            payload
            for digest, payload in existing.items()
            if digest != registry.profile_binding_sha256
        ),
    )


def _origin(
    *,
    bundle: dict[str, object],
    kind: ExperienceOriginKind,
    origin_id: str,
) -> tuple[ExperienceOriginAuthority, bytes, bytes]:
    source_payload = f"origin-source:{origin_id}".encode()
    topology = bundle["topology"]
    closed = bundle["closed_experience"]
    registry = bundle["receipt_registry"]
    assert isinstance(registry, ReceiptRegistry)
    payload = experience_origin_authority_receipt_payload(
        origin_id=origin_id,
        kind=kind,
        profile_binding_sha256=registry.profile_binding_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed.authority_receipt_sha256,
        source_authority_receipt_sha256=receipt_sha256(source_payload),
    )
    return (
        ExperienceOriginAuthority(
            origin_id=origin_id,
            kind=kind,
            profile_binding_sha256=registry.profile_binding_sha256,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=closed.authority_receipt_sha256,
            source_authority_receipt_sha256=receipt_sha256(source_payload),
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        source_payload,
        payload,
    )


def _commit_with_support(
    bundle: dict[str, object],
    support: EventSupportAuthority,
    registry: ReceiptRegistry,
):
    changed = dict(bundle)
    changed["event_support"] = support
    changed["receipt_registry"] = registry
    return evaluate_commit_boundary(**changed)


def _admission(
    *,
    bundle: dict[str, object],
    origin: ExperienceOriginAuthority,
    support: EventSupportAuthority,
    registry: ReceiptRegistry,
):
    changed = dict(bundle)
    changed["event_support"] = support
    changed["receipt_registry"] = registry
    return evaluate_field_admission(origin=origin, **changed)


def test_each_self_generated_scalar_commits_at_zero_R_event_without_growth() -> None:
    bundle = _bundle()
    origin, source_payload, origin_payload = _origin(
        bundle=bundle,
        kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        origin_id="remembered-expression-scalar-origin",
    )
    base_registry = bundle["receipt_registry"]
    assert isinstance(base_registry, ReceiptRegistry)
    registry = _extend(base_registry, source_payload, origin_payload)
    recall_support = create_self_generated_recall_event_support(origin)
    registry = _extend(registry, recall_support.authority_receipt_payload)

    admission = _admission(
        bundle=bundle,
        origin=origin,
        support=recall_support.authority,
        registry=registry,
    )
    assert admission.disposition is FieldAdmissionDisposition.ADMITTED
    registry = _extend(registry, admission.receipt_payload)

    decisions = tuple(
        _commit_with_support(bundle, recall_support.authority, registry)
        for _scalar in "we remember"
    )

    assert all(value.status is CommitStatus.COMMIT for value in decisions)
    assert all(value.findings == () for value in decisions)
    assert all(
        value.event_support_receipt_sha256
        == recall_support.authority.authority_receipt_sha256
        for value in decisions
    )

    growth = evaluate_growth_eligibility(
        origin=origin,
        field_admission=admission,
        event_support=recall_support.authority,
        recognition=bundle["recognition"],
        receipt_registry=registry,
    )
    registry = _extend(registry, growth.receipt_payload)
    growth.verify(registry)

    assert growth.mode_growth is PersistenceDisposition.NOT_AUTHORIZED
    assert growth.memory_growth is PersistenceDisposition.NOT_AUTHORIZED
    assert growth.mode_growth_authorized is False
    assert growth.memory_growth_authorized is False
    assert (
        growth.mode_reason
        == "self_generated_recall_has_no_fresh_growth_energy"
    )


def test_quiet_external_expression_commits_but_remains_unfunded() -> None:
    bundle = _bundle()
    origin, source_payload, origin_payload = _origin(
        bundle=bundle,
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        origin_id="quiet-external-origin",
    )
    topology = bundle["topology"]
    closed = bundle["closed_experience"]
    event_source = b"quiet-external-exact-event-support"
    support_payload = event_support_authority_receipt_payload(
        authority_id="quiet-external-R-event",
        state=EventSupportState.ZERO,
        exact_r_event=Fraction(0),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
    )
    support = EventSupportAuthority(
        authority_id="quiet-external-R-event",
        state=EventSupportState.ZERO,
        exact_r_event=Fraction(0),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
        authority_receipt_sha256=receipt_sha256(support_payload),
    )
    base_registry = bundle["receipt_registry"]
    assert isinstance(base_registry, ReceiptRegistry)
    registry = _extend(
        base_registry,
        source_payload,
        origin_payload,
        event_source,
        support_payload,
    )
    admission = _admission(
        bundle=bundle,
        origin=origin,
        support=support,
        registry=registry,
    )
    registry = _extend(registry, admission.receipt_payload)
    decision = _commit_with_support(bundle, support, registry)
    assert decision.status is CommitStatus.COMMIT

    growth = evaluate_growth_eligibility(
        origin=origin,
        field_admission=admission,
        event_support=support,
        recognition=bundle["recognition"],
        receipt_registry=registry,
    )

    assert growth.mode_growth is PersistenceDisposition.NOT_AUTHORIZED
    assert growth.memory_growth is PersistenceDisposition.NOT_AUTHORIZED
    assert not growth.mode_growth_authorized
    assert not growth.memory_growth_authorized


def test_recalled_old_sensory_energy_cannot_be_relabelled_positive() -> None:
    bundle = _bundle()
    origin, source_payload, origin_payload = _origin(
        bundle=bundle,
        kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        origin_id="tamper-recall-origin",
    )
    topology = bundle["topology"]
    closed = bundle["closed_experience"]
    positive_payload = event_support_authority_receipt_payload(
        authority_id="forged-recall-positive-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(origin_payload),
    )
    positive = EventSupportAuthority(
        authority_id="forged-recall-positive-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(origin_payload),
        authority_receipt_sha256=receipt_sha256(positive_payload),
    )
    base_registry = bundle["receipt_registry"]
    assert isinstance(base_registry, ReceiptRegistry)
    registry = _extend(
        base_registry,
        source_payload,
        origin_payload,
        positive_payload,
    )
    admission = _admission(
        bundle=bundle,
        origin=origin,
        support=positive,
        registry=registry,
    )
    registry = _extend(registry, admission.receipt_payload)

    with pytest.raises(ReceiptError, match="exact-zero fresh R_event"):
        evaluate_growth_eligibility(
            origin=origin,
            field_admission=admission,
            event_support=positive,
            recognition=bundle["recognition"],
            receipt_registry=registry,
        )

def test_positive_story_bootstrap_funds_mode_capture_without_memory_growth() -> None:
    base = _bundle()
    topology = base["topology"]
    recognized = base["recognition"]
    base_registry = base["receipt_registry"]
    assert isinstance(base_registry, ReceiptRegistry)
    first_expression = recognized.pre_growth_bank.modes[0].source_expression
    empty = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=first_expression.precision_authority,
        receipt_registry=base_registry,
    )
    bootstrap = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty,
        input_expression=first_expression,
        receipt_registry=base_registry,
    )
    generated = [
        bootstrap.receipt_payload,
        bootstrap.pre_growth_bank.receipt_payload,
        bootstrap.post_growth_bank.receipt_payload,
    ]
    for mode in bootstrap.post_growth_bank.modes:
        generated.extend(
            (
                mode.receipt_payload,
                mode.growth_proof_receipt_payload,
                mode.source_expression.receipt_payload,
            )
        )
    registry = _extend(base_registry, *generated)

    evidence = base["evidence"]
    seal_payload = closed_experience_seal_receipt_payload(
        experience_id="story-bootstrap-experience",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=first_expression.receipt_sha256,
        recognition_receipt_sha256=bootstrap.receipt_sha256,
        ordered_evidence_receipt_sha256s=tuple(
            value.evidence_receipt_sha256 for value in evidence
        ),
        source_time_start=Fraction(5),
        source_time_end=Fraction(6),
        structural_time_unit="structural_second",
    )
    seal = ClosedExperienceSeal(
        experience_id="story-bootstrap-experience",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=first_expression.receipt_sha256,
        recognition_receipt_sha256=bootstrap.receipt_sha256,
        ordered_evidence_receipt_sha256s=tuple(
            value.evidence_receipt_sha256 for value in evidence
        ),
        source_time_start=Fraction(5),
        source_time_end=Fraction(6),
        structural_time_unit="structural_second",
        authority_receipt_sha256=receipt_sha256(seal_payload),
    )
    safe_mode, safe_payloads = _binary(
        BinaryAuthorityKind.SAFE_MODE_CLEAR,
        AuthorityDisposition.PASS,
        topology.authority_receipt_sha256,
        seal.authority_receipt_sha256,
    )
    global_uf, global_payloads = _binary(
        BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        AuthorityDisposition.PASS,
        topology.authority_receipt_sha256,
        seal.authority_receipt_sha256,
    )
    event_source = b"story-bootstrap-positive-event-source"
    event_payload = event_support_authority_receipt_payload(
        authority_id="story-bootstrap-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
    )
    event_support = EventSupportAuthority(
        authority_id="story-bootstrap-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
        authority_receipt_sha256=receipt_sha256(event_payload),
    )
    l6 = _l6_lock()
    l6_payload = l6_evaluation_receipt_payload(l6)
    l6_scope_payload = l6_scope_authority_receipt_payload(
        authority_id="story-bootstrap-L6-scope",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
    )
    l6_scope = L6ScopeAuthority(
        authority_id="story-bootstrap-L6-scope",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
        authority_receipt_sha256=receipt_sha256(l6_scope_payload),
    )
    applicability = []
    applicability_payloads = []
    for fact in (GovernedFact.S_UF, GovernedFact.R_UF):
        source = f"story-bootstrap-L5:{fact.value}".encode()
        payload = l5_applicability_receipt_payload(
            authority_id=f"story-bootstrap-L5-{fact.value}",
            lane_id="language",
            port_id="typed",
            fact=fact,
            state=ApplicabilityState.REQUIRED,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal.authority_receipt_sha256,
            source_governance_receipt_sha256=receipt_sha256(source),
        )
        applicability.append(
            L5Applicability(
                authority_id=f"story-bootstrap-L5-{fact.value}",
                lane_id="language",
                port_id="typed",
                fact=fact,
                state=ApplicabilityState.REQUIRED,
                topology_authority_receipt_sha256=(
                    topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                source_governance_receipt_sha256=receipt_sha256(source),
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        applicability_payloads.extend((source, payload))
    registry = _extend(
        registry,
        seal_payload,
        *safe_payloads,
        *global_payloads,
        event_source,
        event_payload,
        l6_payload,
        l6_scope_payload,
        *applicability_payloads,
    )
    bootstrap_bundle = {
        "topology": topology,
        "recognition": bootstrap,
        "l6_evaluation": l6,
        "l6_scope": l6_scope,
        "closed_experience": seal,
        "safe_mode": safe_mode,
        "event_support": event_support,
        "evidence": evidence,
        "l5_applicability": tuple(applicability),
        "global_uf_validation": global_uf,
        "receipt_registry": registry,
    }
    origin, origin_source, origin_payload = _origin(
        bundle=bootstrap_bundle,
        kind=ExperienceOriginKind.EXPLICIT_STORY_EMULATOR,
        origin_id="story-bootstrap-origin",
    )
    registry = _extend(registry, origin_source, origin_payload)
    bootstrap_bundle["receipt_registry"] = registry
    admission = evaluate_field_admission(origin=origin, **bootstrap_bundle)
    assert admission.disposition is FieldAdmissionDisposition.ADMITTED
    registry = _extend(registry, admission.receipt_payload)

    growth = evaluate_growth_eligibility(
        origin=origin,
        field_admission=admission,
        event_support=event_support,
        recognition=bootstrap,
        receipt_registry=registry,
    )

    assert bootstrap.mutation is True
    assert growth.mode_growth is PersistenceDisposition.AUTHORIZED
    assert growth.memory_growth is PersistenceDisposition.NOT_AUTHORIZED
    assert growth.mode_growth_authorized
    assert not growth.memory_growth_authorized
