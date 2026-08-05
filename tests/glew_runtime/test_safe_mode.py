"""Exact SafeMode integrity-meet conformance."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.commit import AuthorityDisposition
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)


PROFILE = b"safe-mode-test-profile"
TOPOLOGY = receipt_sha256(b"safe-mode-topology")
EXPERIENCE = receipt_sha256(b"safe-mode-experience")
SOURCE_PROFILE = b"safe-mode-required-integrity-profile"
FACT_IDS = ("chemistry", "input_order", "persistence")


def _environment(states=(
    IntegrityFactState.CLEAR,
    IntegrityFactState.CLEAR,
    IntegrityFactState.CLEAR,
)):
    scope_payload = safe_mode_scope_receipt_payload(
        scope_id="production-integrity",
        topology_authority_receipt_sha256=TOPOLOGY,
        required_fact_ids=FACT_IDS,
        source_profile_receipt_sha256=receipt_sha256(SOURCE_PROFILE),
    )
    scope = MountedSafeModeScope(
        scope_id="production-integrity",
        topology_authority_receipt_sha256=TOPOLOGY,
        required_fact_ids=FACT_IDS,
        source_profile_receipt_sha256=receipt_sha256(SOURCE_PROFILE),
        authority_receipt_sha256=receipt_sha256(scope_payload),
    )
    payloads = [b"safe-mode-topology", SOURCE_PROFILE, scope_payload]
    facts = []
    for fact_id, state in zip(FACT_IDS, states, strict=True):
        source = f"safe-mode-source:{fact_id}:{state.value}".encode()
        payload = integrity_fact_receipt_payload(
            fact_id=fact_id,
            state=state,
            topology_authority_receipt_sha256=TOPOLOGY,
            closed_experience_receipt_sha256=EXPERIENCE,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        payloads.extend((source, payload))
        facts.append(
            IntegrityFact(
                fact_id=fact_id,
                state=state,
                topology_authority_receipt_sha256=TOPOLOGY,
                closed_experience_receipt_sha256=EXPERIENCE,
                source_operator_receipt_sha256=receipt_sha256(source),
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=tuple(payloads),
    )
    return scope, tuple(facts), registry


@pytest.mark.parametrize(
    ("states", "expected"),
    (
        (
            (
                IntegrityFactState.CLEAR,
                IntegrityFactState.CLEAR,
                IntegrityFactState.CLEAR,
            ),
            AuthorityDisposition.PASS,
        ),
        (
            (
                IntegrityFactState.CLEAR,
                IntegrityFactState.FAULT,
                IntegrityFactState.CLEAR,
            ),
            AuthorityDisposition.FAIL,
        ),
        (
            (
                IntegrityFactState.CLEAR,
                IntegrityFactState.UNKNOWN,
                IntegrityFactState.CLEAR,
            ),
            AuthorityDisposition.UNKNOWN,
        ),
    ),
)
def test_exact_integrity_meet(states, expected) -> None:
    scope, facts, registry = _environment(states)
    result = evaluate_safe_mode(
        authority_id="safe-mode-clear",
        topology_authority_receipt_sha256=TOPOLOGY,
        closed_experience_receipt_sha256=EXPERIENCE,
        scope=scope,
        facts=facts,
        receipt_registry=registry,
    )

    assert result.disposition is expected
    assert result.authority.disposition is expected
    assert len(result.generated_receipt_payloads) == 2


def test_missing_extra_duplicate_and_none_are_unknown() -> None:
    scope, facts, registry = _environment()
    for supplied in (None, facts[:-1], (*facts, facts[0])):
        result = evaluate_safe_mode(
            authority_id="safe-mode-clear",
            topology_authority_receipt_sha256=TOPOLOGY,
            closed_experience_receipt_sha256=EXPERIENCE,
            scope=scope,
            facts=supplied,
            receipt_registry=registry,
        )
        assert result.disposition is AuthorityDisposition.UNKNOWN


def test_order_is_canonical_not_caller_dependent() -> None:
    scope, facts, registry = _environment()
    forward = evaluate_safe_mode(
        authority_id="safe-mode-clear",
        topology_authority_receipt_sha256=TOPOLOGY,
        closed_experience_receipt_sha256=EXPERIENCE,
        scope=scope,
        facts=facts,
        receipt_registry=registry,
    )
    reverse = evaluate_safe_mode(
        authority_id="safe-mode-clear",
        topology_authority_receipt_sha256=TOPOLOGY,
        closed_experience_receipt_sha256=EXPERIENCE,
        scope=scope,
        facts=tuple(reversed(facts)),
        receipt_registry=registry,
    )

    assert reverse.source_receipt_payload == forward.source_receipt_payload
    assert reverse.authority_receipt_payload == forward.authority_receipt_payload


def test_tampered_fact_or_wrong_experience_fails_loudly() -> None:
    scope, facts, registry = _environment()
    with pytest.raises(ReceiptError):
        evaluate_safe_mode(
            authority_id="safe-mode-clear",
            topology_authority_receipt_sha256=TOPOLOGY,
            closed_experience_receipt_sha256=EXPERIENCE,
            scope=scope,
            facts=(replace(facts[0], closed_experience_receipt_sha256="0" * 64), *facts[1:]),
            receipt_registry=registry,
        )


def test_generated_authority_verifies_once_mounted() -> None:
    scope, facts, registry = _environment()
    result = evaluate_safe_mode(
        authority_id="safe-mode-clear",
        topology_authority_receipt_sha256=TOPOLOGY,
        closed_experience_receipt_sha256=EXPERIENCE,
        scope=scope,
        facts=facts,
        receipt_registry=registry,
    )
    mounted = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=tuple(
            record.payload
            for record in registry.records
            if record.digest != registry.profile_binding_sha256
        )
        + result.generated_receipt_payloads,
    )

    result.authority.verify(
        expected_kind=result.authority.kind,
        topology_receipt=TOPOLOGY,
        experience_receipt=EXPERIENCE,
        receipt_registry=mounted,
    )
