"""Exact fail-closed SafeMode authority for clean GLEW experiences.

SafeMode is not inferred from the absence of an error.  One mounted scope
declares every integrity fact that must be known for the current closed
experience.  Each fact is independently receipted as CLEAR, FAULT, or
UNKNOWN.  The meet is exact:

* every required fact CLEAR -> SafeMode-clear PASS;
* any required fact FAULT -> SafeMode-clear FAIL;
* a missing, duplicate, extra, or UNKNOWN fact -> UNKNOWN.

There are no optional defaults, scores, timeouts, severities, or fallback
facts.  A runtime chooses its required fact identities in a signed physical
resource/profile manifest; this operator only verifies and evaluates them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .commit import (
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    binary_authority_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)


SAFE_MODE_OPERATOR_ID = "glew.exact_required_integrity_meet.v1"


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


class IntegrityFactState(str, Enum):
    CLEAR = "clear"
    FAULT = "fault"
    UNKNOWN = "unknown"


def safe_mode_scope_receipt_payload(
    *,
    scope_id: str,
    topology_authority_receipt_sha256: str,
    required_fact_ids: tuple[str, ...],
    source_profile_receipt_sha256: str,
) -> bytes:
    require_identifier(scope_id, "SafeMode scope id")
    sha256_digest(
        topology_authority_receipt_sha256,
        "SafeMode topology receipt",
    )
    sha256_digest(
        source_profile_receipt_sha256,
        "SafeMode source-profile receipt",
    )
    if not isinstance(required_fact_ids, tuple) or not required_fact_ids:
        raise ReceiptError("SafeMode scope requires a nonempty immutable fact set")
    for fact_id in required_fact_ids:
        require_identifier(fact_id, "SafeMode required fact id")
    if required_fact_ids != tuple(sorted(set(required_fact_ids))):
        raise ReceiptError("SafeMode required facts must be unique canonical order")
    return _canonical_bytes(
        {
            "operator_id": SAFE_MODE_OPERATOR_ID,
            "required_fact_ids": list(required_fact_ids),
            "scope_id": scope_id,
            "schema": "glew.safe_mode.required_integrity_scope.v1",
            "source_profile_receipt_sha256": source_profile_receipt_sha256,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class MountedSafeModeScope:
    scope_id: str
    topology_authority_receipt_sha256: str
    required_fact_ids: tuple[str, ...]
    source_profile_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return safe_mode_scope_receipt_payload(
            scope_id=self.scope_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            required_fact_ids=self.required_fact_ids,
            source_profile_receipt_sha256=self.source_profile_receipt_sha256,
        )

    def verify(
        self,
        *,
        topology_receipt: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("SafeMode scope belongs to a different topology")
        receipt_registry.resolve(
            self.source_profile_receipt_sha256,
            "SafeMode source-profile receipt",
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "SafeMode scope authority receipt",
        )


def integrity_fact_receipt_payload(
    *,
    fact_id: str,
    state: IntegrityFactState,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    source_operator_receipt_sha256: str,
) -> bytes:
    require_identifier(fact_id, "integrity fact id")
    if not isinstance(state, IntegrityFactState):
        raise ReceiptError("integrity fact state is not typed")
    for value, name in (
        (topology_authority_receipt_sha256, "integrity topology receipt"),
        (closed_experience_receipt_sha256, "integrity experience receipt"),
        (source_operator_receipt_sha256, "integrity source receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "fact_id": fact_id,
            "schema": "glew.safe_mode.integrity_fact.v1",
            "source_operator_receipt_sha256": source_operator_receipt_sha256,
            "state": state.value,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class IntegrityFact:
    fact_id: str
    state: IntegrityFactState
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    source_operator_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return integrity_fact_receipt_payload(
            fact_id=self.fact_id,
            state=self.state,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )

    def verify(
        self,
        *,
        topology_receipt: str,
        experience_receipt: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("integrity fact belongs to a different topology")
        if self.closed_experience_receipt_sha256 != experience_receipt:
            raise ReceiptError("integrity fact belongs to a different experience")
        receipt_registry.resolve(
            self.source_operator_receipt_sha256,
            "integrity fact source-operator receipt",
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "integrity fact receipt",
        )


def safe_mode_evaluation_receipt_payload(
    *,
    scope_authority_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    ordered_fact_receipt_sha256s: tuple[str, ...],
    disposition: AuthorityDisposition,
    reason: str,
) -> bytes:
    for value, name in (
        (scope_authority_receipt_sha256, "SafeMode scope receipt"),
        (topology_authority_receipt_sha256, "SafeMode topology receipt"),
        (closed_experience_receipt_sha256, "SafeMode experience receipt"),
    ):
        sha256_digest(value, name)
    if not isinstance(ordered_fact_receipt_sha256s, tuple):
        raise ReceiptError("SafeMode fact receipts must be an immutable tuple")
    for digest in ordered_fact_receipt_sha256s:
        sha256_digest(digest, "SafeMode fact receipt")
    if not isinstance(disposition, AuthorityDisposition):
        raise ReceiptError("SafeMode disposition is not typed")
    require_identifier(reason, "SafeMode evaluation reason")
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "disposition": disposition.value,
            "operator_id": SAFE_MODE_OPERATOR_ID,
            "ordered_fact_receipt_sha256s": list(
                ordered_fact_receipt_sha256s
            ),
            "reason": reason,
            "schema": "glew.safe_mode.exact_integrity_meet_result.v1",
            "scope_authority_receipt_sha256": (
                scope_authority_receipt_sha256
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class SafeModeEvaluation:
    authority: BinaryCommitAuthority
    disposition: AuthorityDisposition
    reason: str
    ordered_fact_receipt_sha256s: tuple[str, ...]
    source_receipt_sha256: str
    source_receipt_payload: bytes
    authority_receipt_payload: bytes

    def verify(self) -> None:
        if self.authority.kind is not BinaryAuthorityKind.SAFE_MODE_CLEAR:
            raise ReceiptError("SafeMode evaluation produced the wrong authority kind")
        if self.authority.disposition is not self.disposition:
            raise ReceiptError("SafeMode result and binary authority disagree")
        if (
            self.authority.source_operator_receipt_sha256
            != self.source_receipt_sha256
            or receipt_sha256(self.source_receipt_payload)
            != self.source_receipt_sha256
        ):
            raise ReceiptError("SafeMode source receipt is inconsistent")
        expected_authority = binary_authority_receipt_payload(
            authority_id=self.authority.authority_id,
            kind=self.authority.kind,
            disposition=self.authority.disposition,
            topology_authority_receipt_sha256=(
                self.authority.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.authority.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=(
                self.authority.source_operator_receipt_sha256
            ),
        )
        if (
            self.authority_receipt_payload != expected_authority
            or receipt_sha256(expected_authority)
            != self.authority.authority_receipt_sha256
        ):
            raise ReceiptError("SafeMode binary authority receipt is inconsistent")

    @property
    def generated_receipt_payloads(self) -> tuple[bytes, bytes]:
        return self.source_receipt_payload, self.authority_receipt_payload


def evaluate_safe_mode(
    *,
    authority_id: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    scope: MountedSafeModeScope,
    facts: tuple[IntegrityFact, ...] | None,
    receipt_registry: ReceiptRegistry,
) -> SafeModeEvaluation:
    """Meet one complete mounted integrity scope without inferred clear state."""

    require_identifier(authority_id, "SafeMode binary authority id")
    if not isinstance(scope, MountedSafeModeScope):
        raise ReceiptError("SafeMode evaluation requires a mounted scope")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("SafeMode evaluation requires a receipt registry")
    scope.verify(
        topology_receipt=topology_authority_receipt_sha256,
        receipt_registry=receipt_registry,
    )

    ordered_facts: tuple[IntegrityFact, ...] = ()
    if facts is None or not isinstance(facts, tuple):
        disposition = AuthorityDisposition.UNKNOWN
        reason = "required integrity facts are missing"
    elif not all(isinstance(value, IntegrityFact) for value in facts):
        disposition = AuthorityDisposition.UNKNOWN
        reason = "integrity fact set contains an untyped value"
    else:
        ordered_facts = tuple(sorted(facts, key=lambda value: value.fact_id))
        supplied_ids = tuple(value.fact_id for value in ordered_facts)
        if len(set(supplied_ids)) != len(supplied_ids):
            disposition = AuthorityDisposition.UNKNOWN
            reason = "integrity fact set contains a duplicate identity"
        elif supplied_ids != scope.required_fact_ids:
            disposition = AuthorityDisposition.UNKNOWN
            reason = "integrity fact set does not exactly cover the mounted scope"
        else:
            for fact in ordered_facts:
                fact.verify(
                    topology_receipt=topology_authority_receipt_sha256,
                    experience_receipt=closed_experience_receipt_sha256,
                    receipt_registry=receipt_registry,
                )
            states = tuple(value.state for value in ordered_facts)
            if IntegrityFactState.FAULT in states:
                disposition = AuthorityDisposition.FAIL
                reason = "at least one required integrity fact proves a fault"
            elif IntegrityFactState.UNKNOWN in states:
                disposition = AuthorityDisposition.UNKNOWN
                reason = "at least one required integrity fact is unresolved"
            elif all(value is IntegrityFactState.CLEAR for value in states):
                disposition = AuthorityDisposition.PASS
                reason = "every fact in the mounted integrity scope is clear"
            else:
                raise ReceiptError("integrity fact meet reached an untyped state")

    fact_receipts = tuple(
        value.authority_receipt_sha256 for value in ordered_facts
    )
    source_payload = safe_mode_evaluation_receipt_payload(
        scope_authority_receipt_sha256=scope.authority_receipt_sha256,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        ordered_fact_receipt_sha256s=fact_receipts,
        disposition=disposition,
        reason=reason,
    )
    source_digest = receipt_sha256(source_payload)
    authority_payload = binary_authority_receipt_payload(
        authority_id=authority_id,
        kind=BinaryAuthorityKind.SAFE_MODE_CLEAR,
        disposition=disposition,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        source_operator_receipt_sha256=source_digest,
    )
    authority = BinaryCommitAuthority(
        authority_id=authority_id,
        kind=BinaryAuthorityKind.SAFE_MODE_CLEAR,
        disposition=disposition,
        topology_authority_receipt_sha256=(
            topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            closed_experience_receipt_sha256
        ),
        source_operator_receipt_sha256=source_digest,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    result = SafeModeEvaluation(
        authority=authority,
        disposition=disposition,
        reason=reason,
        ordered_fact_receipt_sha256s=fact_receipts,
        source_receipt_sha256=source_digest,
        source_receipt_payload=source_payload,
        authority_receipt_payload=authority_payload,
    )
    result.verify()
    return result


__all__ = (
    "IntegrityFact",
    "IntegrityFactState",
    "MountedSafeModeScope",
    "SAFE_MODE_OPERATOR_ID",
    "SafeModeEvaluation",
    "evaluate_safe_mode",
    "integrity_fact_receipt_payload",
    "safe_mode_evaluation_receipt_payload",
    "safe_mode_scope_receipt_payload",
)
