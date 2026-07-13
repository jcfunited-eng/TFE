"""Exact remembered-expression output authority for clean-generation GLEW.

This boundary is deliberately narrower than a language generator.  It can only
reproduce Unicode scalars carried by immutable bindings between a committed
full-sensory motif and language that occurred in the same closed experience.
It performs no vocabulary lookup, suffix walk, prediction, random choice,
fallback, token cap, or timeout.

Scalars are retained in a private transaction until an independently receipted
expression-close motif is committed.  Any uncertainty terminates the
transaction, destroys its staged actuation, and returns explicit silence.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Sequence

from .language import (
    TRIT_PLACES,
    BalancedTrit,
    encode_balanced_ternary_scalar,
)
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)



def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _strict_receipt_object(
    payload: bytes,
    description: str,
) -> dict[str, object]:
    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ReceiptError(f"{description} repeats a JSON key")
            value[key] = item
        return value

    try:
        decoded = payload.decode("utf-8")
        parsed = json.loads(decoded, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{description} is not canonical JSON") from exc
    if not isinstance(parsed, dict):
        raise ReceiptError(f"{description} is not a JSON object")
    if _canonical_bytes(parsed) != payload:
        raise ReceiptError(f"{description} is not canonical JSON bytes")
    return parsed


def _complete_closed_experience_sensory_receipts(
    closed_experience_receipt_sha256: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[str, ...]:
    mounted_seal = receipt_registry.resolve(
        closed_experience_receipt_sha256,
        "output closed-experience seal",
    )
    seal = _strict_receipt_object(
        mounted_seal,
        "output closed-experience seal",
    )
    expected_seal_keys = {
        "close_authority",
        "experience_id",
        "input_expression_receipt_sha256",
        "ordered_evidence_receipt_sha256s",
        "recognition_receipt_sha256",
        "schema",
        "source_time_end",
        "source_time_start",
        "structural_time_unit",
        "topology_authority_receipt_sha256",
    }
    if set(seal) != expected_seal_keys or seal.get("schema") != (
        "glew.commit.closed_expression_experience.v1"
    ):
        raise ReceiptError(
            "output binding requires an exact closed-experience seal"
        )
    ordered = seal.get("ordered_evidence_receipt_sha256s")
    if not isinstance(ordered, list) or not ordered:
        raise ReceiptError("closed experience has no ordered evidence")
    if any(not isinstance(value, str) for value in ordered):
        raise ReceiptError("closed experience evidence digest is not text")
    ordered_digests = tuple(ordered)
    for index, digest in enumerate(ordered_digests):
        sha256_digest(digest, f"closed experience evidence[{index}]")
    if len(set(ordered_digests)) != len(ordered_digests):
        raise ReceiptError("closed experience repeats evidence")

    sensory: list[str] = []
    for digest in ordered_digests:
        evidence_payload = receipt_registry.resolve(
            digest,
            "closed-experience transport evidence",
        )
        evidence = _strict_receipt_object(
            evidence_payload,
            "closed-experience transport evidence",
        )
        if evidence.get("schema") != "glew.field.transport_evidence.v1":
            raise ReceiptError(
                "closed experience contains non-transport evidence"
            )
        lane_id = evidence.get("lane_id")
        if not isinstance(lane_id, str) or not lane_id:
            raise ReceiptError("closed-experience evidence has no lane")
        if lane_id != "language":
            sensory.append(digest)
    return tuple(sorted(sensory))


def _require_nonnegative_integer(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReceiptError(f"{field_name} must be a nonnegative integer")
    return value


def _require_sensory_receipts(
    values: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ReceiptError(f"{field_name} must be an immutable tuple")
    for index, value in enumerate(values):
        sha256_digest(value, f"{field_name}[{index}]")
    if len(set(values)) != len(values):
        raise ReceiptError(f"{field_name} contains a duplicate receipt")
    if values != tuple(sorted(values)):
        raise ReceiptError(f"{field_name} must use canonical digest order")
    return values


def _trit_payload(trit: BalancedTrit) -> dict[str, object]:
    return {
        "place": trit.place,
        "scalar_index": trit.scalar_index,
        "valid": trit.valid,
        "value": trit.value,
    }


def decode_balanced_ternary_scalar(trits: Sequence[BalancedTrit]) -> str:
    """Invert one canonical 14-place balanced-ternary Unicode receipt.

    The inverse is arithmetic only.  Re-encoding the recovered scalar must
    reproduce every value, place, validity bit, and scalar index exactly.
    """

    if not isinstance(trits, tuple):
        raise ReceiptError("balanced-ternary scalar receipt must be an immutable tuple")
    if len(trits) != TRIT_PLACES:
        raise ReceiptError("one language binding requires exactly 14 trit places")
    if any(not isinstance(trit, BalancedTrit) for trit in trits):
        raise ReceiptError("language binding contains a non-trit value")

    scalar_index = trits[0].scalar_index
    scalar = 0
    for expected_place, trit in enumerate(trits):
        if trit.scalar_index != scalar_index:
            raise ReceiptError("one scalar receipt cannot mix scalar indices")
        if trit.place != expected_place:
            raise ReceiptError("balanced-ternary places must be exactly 0 through 13")
        if not trit.valid and trit.value != 0:
            raise ReceiptError("an invalid padding place cannot carry a numeric trit")
        if trit.valid:
            scalar += trit.value * (3**trit.place)

    if not 0 <= scalar <= 0x10FFFF or 0xD800 <= scalar <= 0xDFFF:
        raise ReceiptError("balanced-ternary value is not a Unicode scalar")
    canonical = encode_balanced_ternary_scalar(scalar, scalar_index)
    if trits != canonical:
        raise ReceiptError("balanced-ternary scalar receipt is not canonical")
    return chr(scalar)


class OutputBindingKind(str, Enum):
    LANGUAGE_SCALAR = "language_scalar"
    NO_OUTPUT = "no_output"


class MotifEventKind(str, Enum):
    CONTENT = "content"
    EXPRESSION_CLOSE = "expression_close"


class OutputStatus(str, Enum):
    STAGED_PRIVATE = "staged_private"
    CONTINUED_SILENCE = "continued_silence"
    EXPRESSION_RELEASED = "expression_released"
    UNKNOWN_SILENCE = "unknown_silence"


class OutputReason(str, Enum):
    UNIQUE_COEXPERIENCED_LANGUAGE_BINDING = (
        "unique_coexperienced_language_binding"
    )
    COEXPERIENCED_NO_OUTPUT = "coexperienced_no_output"
    EXACT_EXPRESSION_CLOSE_COMMITTED = "exact_expression_close_committed"
    EMPTY_EXPRESSION_CLOSE = "empty_expression_close"
    MISSING_BINDING = "missing_binding"
    CONFLICTING_LANGUAGE_BINDINGS = "conflicting_language_bindings"
    MIXED_LANGUAGE_AND_NO_OUTPUT = "mixed_language_and_no_output"
    EXACT_STATE_EDGE_CYCLE = "exact_state_edge_cycle"
    SOURCE_STATE_MISMATCH = "source_state_mismatch"
    RECEIPT_FAILURE = "receipt_failure"
    EXPRESSION_ALREADY_TERMINAL = "expression_already_terminal"


class StageDisposition(str, Enum):
    RETAINED_PRIVATE = "retained_private"
    RELEASED_AND_CLEARED = "released_and_cleared"
    DISCARDED = "discarded"
    EMPTY = "empty"


def motif_output_binding_receipt_payload(
    *,
    binding_id: str,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    fact_strand_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    coexperienced_output_receipt_sha256: str,
    kind: OutputBindingKind,
    trits: tuple[BalancedTrit, ...],
    language_scalar_cardinality: int,
    no_output_cardinality: int,
) -> bytes:
    require_identifier(binding_id, "output binding id")
    for value, name in (
        (profile_binding_sha256, "binding profile receipt"),
        (motif_receipt_sha256, "binding motif receipt"),
        (closed_experience_receipt_sha256, "binding closed-experience receipt"),
        (fact_strand_receipt_sha256, "binding Fact Strand receipt"),
        (coexperienced_output_receipt_sha256, "coexperienced output receipt"),
    ):
        sha256_digest(value, name)
    _require_sensory_receipts(
        sensory_evidence_receipt_sha256s,
        "binding sensory evidence receipts",
    )
    if not isinstance(kind, OutputBindingKind):
        raise ReceiptError("output binding kind is not ratified")
    _require_nonnegative_integer(
        language_scalar_cardinality,
        "language scalar cardinality",
    )
    _require_nonnegative_integer(no_output_cardinality, "no-output cardinality")
    if not isinstance(trits, tuple):
        raise ReceiptError("output binding trits must be an immutable tuple")

    if kind is OutputBindingKind.LANGUAGE_SCALAR:
        if language_scalar_cardinality != 1 or no_output_cardinality != 0:
            raise ReceiptError(
                "a language binding must contain exactly one scalar and no no-output fact"
            )
        decode_balanced_ternary_scalar(trits)
    elif trits or language_scalar_cardinality != 0 or no_output_cardinality != 1:
        raise ReceiptError(
            "a no-output binding must contain exactly one no-output fact and no scalar"
        )

    return _canonical_bytes(
        {
            "binding_id": binding_id,
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "coexperienced_output_receipt_sha256": (
                coexperienced_output_receipt_sha256
            ),
            "fact_strand_receipt_sha256": fact_strand_receipt_sha256,
            "kind": kind.value,
            "language_scalar_cardinality": language_scalar_cardinality,
            "motif_receipt_sha256": motif_receipt_sha256,
            "no_output_cardinality": no_output_cardinality,
            "profile_binding_sha256": profile_binding_sha256,
            "schema": "glew.output.motif_coexperienced_binding.v1",
            "sensory_evidence_cardinality": len(
                sensory_evidence_receipt_sha256s
            ),
            "sensory_evidence_receipt_sha256s": list(
                sensory_evidence_receipt_sha256s
            ),
            "trit_cardinality": len(trits),
            "trits": [_trit_payload(trit) for trit in trits],
        }
    )


@dataclass(frozen=True, slots=True)
class MotifOutputBinding:
    """One immutable full-sensory motif/output coexperience receipt."""

    binding_id: str
    profile_binding_sha256: str
    motif_receipt_sha256: str
    closed_experience_receipt_sha256: str
    fact_strand_receipt_sha256: str
    sensory_evidence_receipt_sha256s: tuple[str, ...]
    coexperienced_output_receipt_sha256: str
    kind: OutputBindingKind
    trits: tuple[BalancedTrit, ...]
    language_scalar_cardinality: int
    no_output_cardinality: int
    binding_receipt_sha256: str

    def __post_init__(self) -> None:
        motif_output_binding_receipt_payload(
            binding_id=self.binding_id,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=self.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=self.fact_strand_receipt_sha256,
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            coexperienced_output_receipt_sha256=(
                self.coexperienced_output_receipt_sha256
            ),
            kind=self.kind,
            trits=self.trits,
            language_scalar_cardinality=self.language_scalar_cardinality,
            no_output_cardinality=self.no_output_cardinality,
        )
        sha256_digest(self.binding_receipt_sha256, "output binding receipt")

    def payload(self) -> bytes:
        return motif_output_binding_receipt_payload(
            binding_id=self.binding_id,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=self.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=self.fact_strand_receipt_sha256,
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            coexperienced_output_receipt_sha256=(
                self.coexperienced_output_receipt_sha256
            ),
            kind=self.kind,
            trits=self.trits,
            language_scalar_cardinality=self.language_scalar_cardinality,
            no_output_cardinality=self.no_output_cardinality,
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("output binding belongs to a different GLEW profile")
        for value, name in (
            (self.motif_receipt_sha256, "binding motif receipt"),
            (
                self.closed_experience_receipt_sha256,
                "binding closed-experience receipt",
            ),
            (self.fact_strand_receipt_sha256, "binding Fact Strand receipt"),
            (
                self.coexperienced_output_receipt_sha256,
                "coexperienced output receipt",
            ),
        ):
            receipt_registry.resolve(value, name)
        for digest in self.sensory_evidence_receipt_sha256s:
            receipt_registry.resolve(digest, "binding sensory evidence receipt")
        complete_sensory = _complete_closed_experience_sensory_receipts(
            self.closed_experience_receipt_sha256,
            receipt_registry,
        )
        if self.sensory_evidence_receipt_sha256s != complete_sensory:
            raise ReceiptError(
                "output binding does not cite the complete authenticated "
                "non-language sensory evidence of its closed experience"
            )
        mounted = receipt_registry.resolve(
            self.binding_receipt_sha256,
            "output binding receipt",
        )
        if mounted != self.payload():
            raise ReceiptError("output binding differs from its mounted exact bytes")

    def decoded_scalar(self) -> str:
        if self.kind is not OutputBindingKind.LANGUAGE_SCALAR:
            raise ReceiptError("a no-output binding has no Unicode scalar")
        return decode_balanced_ternary_scalar(self.trits)


def motif_binding_bank_receipt_payload(
    *,
    bank_id: str,
    profile_binding_sha256: str,
    bindings: tuple[MotifOutputBinding, ...],
) -> bytes:
    require_identifier(bank_id, "output binding bank id")
    sha256_digest(profile_binding_sha256, "binding bank profile receipt")
    if not isinstance(bindings, tuple):
        raise ReceiptError("output binding bank must be an immutable tuple")
    if any(not isinstance(binding, MotifOutputBinding) for binding in bindings):
        raise ReceiptError("output binding bank contains a non-binding value")
    ordered = tuple(
        sorted(
            bindings,
            key=lambda item: (
                item.motif_receipt_sha256,
                item.binding_id,
                item.binding_receipt_sha256,
            ),
        )
    )
    if bindings != ordered:
        raise ReceiptError("output binding bank is not in canonical order")
    if len({binding.binding_id for binding in bindings}) != len(bindings):
        raise ReceiptError("output binding bank contains a duplicate binding id")
    if len({binding.binding_receipt_sha256 for binding in bindings}) != len(bindings):
        raise ReceiptError("output binding bank contains a duplicate binding receipt")
    if any(
        binding.profile_binding_sha256 != profile_binding_sha256
        for binding in bindings
    ):
        raise ReceiptError("output binding bank mixes GLEW profiles")
    return _canonical_bytes(
        {
            "bank_id": bank_id,
            "binding_cardinality": len(bindings),
            "bindings": [
                {
                    "binding_id": binding.binding_id,
                    "binding_receipt_sha256": binding.binding_receipt_sha256,
                    "kind": binding.kind.value,
                    "motif_receipt_sha256": binding.motif_receipt_sha256,
                }
                for binding in bindings
            ],
            "completeness_scope": "complete_active_motif_output_binding_bank",
            "profile_binding_sha256": profile_binding_sha256,
            "schema": "glew.output.motif_binding_bank.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MotifBindingBank:
    """Receipt-bound complete active output-binding bank with an integrity index."""

    bank_id: str
    profile_binding_sha256: str
    bindings: tuple[MotifOutputBinding, ...]
    bank_receipt_sha256: str
    bank_receipt_payload: bytes
    _by_motif: Mapping[str, tuple[MotifOutputBinding, ...]] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        expected = motif_binding_bank_receipt_payload(
            bank_id=self.bank_id,
            profile_binding_sha256=self.profile_binding_sha256,
            bindings=self.bindings,
        )
        if (
            not isinstance(self.bank_receipt_payload, bytes)
            or self.bank_receipt_payload != expected
        ):
            raise ReceiptError("output binding bank differs from its exact receipt bytes")
        if receipt_sha256(expected) != self.bank_receipt_sha256:
            raise ReceiptError("output binding bank digest differs from its exact bytes")
        grouped: dict[str, list[MotifOutputBinding]] = {}
        for binding in self.bindings:
            grouped.setdefault(binding.motif_receipt_sha256, []).append(binding)
        object.__setattr__(
            self,
            "_by_motif",
            MappingProxyType(
                {key: tuple(values) for key, values in grouped.items()}
            ),
        )

    def payload(self) -> bytes:
        return self.bank_receipt_payload

    def verify_for_motif(
        self,
        receipt_registry: ReceiptRegistry,
        motif_receipt_sha256: str | None,
    ) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("output binding bank belongs to a different GLEW profile")
        mounted = receipt_registry.resolve(
            self.bank_receipt_sha256,
            "output binding bank receipt",
        )
        if mounted != self.bank_receipt_payload:
            raise ReceiptError("output binding bank differs from its mounted exact bytes")
        if motif_receipt_sha256 is None:
            return
        for binding in self.for_motif(motif_receipt_sha256):
            binding.verify(receipt_registry)

    def for_motif(self, motif_receipt_sha256: str) -> tuple[MotifOutputBinding, ...]:
        sha256_digest(motif_receipt_sha256, "committed motif receipt")
        return self._by_motif.get(motif_receipt_sha256, ())


def expression_close_authority_receipt_payload(
    *,
    expression_id: str,
    close_motif_receipt_sha256: str,
) -> bytes:
    require_identifier(expression_id, "expression id")
    sha256_digest(close_motif_receipt_sha256, "expression-close motif receipt")
    return _canonical_bytes(
        {
            "close_motif_receipt_sha256": close_motif_receipt_sha256,
            "expression_id": expression_id,
            "scope": "exact_expression_close_motif_only",
            "schema": "glew.output.expression_close_authority.v1",
        }
    )


def committed_motif_event_receipt_payload(
    *,
    expression_id: str,
    event_id: str,
    event_kind: MotifEventKind,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    fact_strand_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    full_field_state_receipt_sha256: str,
    field_commit_receipt_sha256: str,
    dominant_motif_commit_receipt_sha256: str,
    corrected_l6_lock_receipt_sha256: str,
    output_binding_bank_receipt_sha256: str,
    source_state_receipt_sha256: str,
    transition_edge_receipt_sha256: str,
    result_state_receipt_sha256: str,
    expression_close_authority_receipt_sha256: str | None,
) -> bytes:
    require_identifier(expression_id, "expression id")
    require_identifier(event_id, "committed motif event id")
    if not isinstance(event_kind, MotifEventKind):
        raise ReceiptError("committed motif event kind is not ratified")
    for value, name in (
        (profile_binding_sha256, "event profile receipt"),
        (motif_receipt_sha256, "committed motif receipt"),
        (closed_experience_receipt_sha256, "event closed-experience receipt"),
        (fact_strand_receipt_sha256, "event Fact Strand receipt"),
        (full_field_state_receipt_sha256, "event full-field state receipt"),
        (field_commit_receipt_sha256, "event field-commit receipt"),
        (
            dominant_motif_commit_receipt_sha256,
            "event dominant-motif commit receipt",
        ),
        (corrected_l6_lock_receipt_sha256, "event corrected-L6 lock receipt"),
        (output_binding_bank_receipt_sha256, "event output-binding bank receipt"),
        (source_state_receipt_sha256, "event source-state receipt"),
        (transition_edge_receipt_sha256, "event transition-edge receipt"),
        (result_state_receipt_sha256, "event result-state receipt"),
    ):
        sha256_digest(value, name)
    _require_sensory_receipts(
        sensory_evidence_receipt_sha256s,
        "event sensory evidence receipts",
    )
    if event_kind is MotifEventKind.EXPRESSION_CLOSE:
        if expression_close_authority_receipt_sha256 is None:
            raise ReceiptError("expression-close event lacks exact close authority")
        sha256_digest(
            expression_close_authority_receipt_sha256,
            "expression-close authority receipt",
        )
    elif expression_close_authority_receipt_sha256 is not None:
        raise ReceiptError("a content event cannot carry expression-close authority")

    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "corrected_l6_lock_receipt_sha256": (
                corrected_l6_lock_receipt_sha256
            ),
            "dominant_motif_commit_receipt_sha256": (
                dominant_motif_commit_receipt_sha256
            ),
            "event_id": event_id,
            "event_kind": event_kind.value,
            "expression_close_authority_receipt_sha256": (
                expression_close_authority_receipt_sha256
            ),
            "expression_id": expression_id,
            "fact_strand_receipt_sha256": fact_strand_receipt_sha256,
            "field_commit_receipt_sha256": field_commit_receipt_sha256,
            "full_field_state_receipt_sha256": full_field_state_receipt_sha256,
            "motif_receipt_sha256": motif_receipt_sha256,
            "output_binding_bank_receipt_sha256": (
                output_binding_bank_receipt_sha256
            ),
            "profile_binding_sha256": profile_binding_sha256,
            "result_state_receipt_sha256": result_state_receipt_sha256,
            "schema": "glew.output.committed_motif_event.v1",
            "sensory_evidence_cardinality": len(
                sensory_evidence_receipt_sha256s
            ),
            "sensory_evidence_receipt_sha256s": list(
                sensory_evidence_receipt_sha256s
            ),
            "source_state_receipt_sha256": source_state_receipt_sha256,
            "transition_edge_receipt_sha256": transition_edge_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class CommittedMotifEvent:
    """One upstream-attested full-field dominant-motif commit."""

    expression_id: str
    event_id: str
    event_kind: MotifEventKind
    profile_binding_sha256: str
    motif_receipt_sha256: str
    closed_experience_receipt_sha256: str
    fact_strand_receipt_sha256: str
    sensory_evidence_receipt_sha256s: tuple[str, ...]
    full_field_state_receipt_sha256: str
    field_commit_receipt_sha256: str
    dominant_motif_commit_receipt_sha256: str
    corrected_l6_lock_receipt_sha256: str
    output_binding_bank_receipt_sha256: str
    source_state_receipt_sha256: str
    transition_edge_receipt_sha256: str
    result_state_receipt_sha256: str
    expression_close_authority_receipt_sha256: str | None
    event_receipt_sha256: str

    def __post_init__(self) -> None:
        committed_motif_event_receipt_payload(
            expression_id=self.expression_id,
            event_id=self.event_id,
            event_kind=self.event_kind,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=self.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=self.fact_strand_receipt_sha256,
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            full_field_state_receipt_sha256=(
                self.full_field_state_receipt_sha256
            ),
            field_commit_receipt_sha256=self.field_commit_receipt_sha256,
            dominant_motif_commit_receipt_sha256=(
                self.dominant_motif_commit_receipt_sha256
            ),
            corrected_l6_lock_receipt_sha256=(
                self.corrected_l6_lock_receipt_sha256
            ),
            output_binding_bank_receipt_sha256=(
                self.output_binding_bank_receipt_sha256
            ),
            source_state_receipt_sha256=self.source_state_receipt_sha256,
            transition_edge_receipt_sha256=(
                self.transition_edge_receipt_sha256
            ),
            result_state_receipt_sha256=self.result_state_receipt_sha256,
            expression_close_authority_receipt_sha256=(
                self.expression_close_authority_receipt_sha256
            ),
        )
        sha256_digest(self.event_receipt_sha256, "committed motif event receipt")

    def payload(self) -> bytes:
        return committed_motif_event_receipt_payload(
            expression_id=self.expression_id,
            event_id=self.event_id,
            event_kind=self.event_kind,
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=self.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=self.fact_strand_receipt_sha256,
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            full_field_state_receipt_sha256=(
                self.full_field_state_receipt_sha256
            ),
            field_commit_receipt_sha256=self.field_commit_receipt_sha256,
            dominant_motif_commit_receipt_sha256=(
                self.dominant_motif_commit_receipt_sha256
            ),
            corrected_l6_lock_receipt_sha256=(
                self.corrected_l6_lock_receipt_sha256
            ),
            output_binding_bank_receipt_sha256=(
                self.output_binding_bank_receipt_sha256
            ),
            source_state_receipt_sha256=self.source_state_receipt_sha256,
            transition_edge_receipt_sha256=(
                self.transition_edge_receipt_sha256
            ),
            result_state_receipt_sha256=self.result_state_receipt_sha256,
            expression_close_authority_receipt_sha256=(
                self.expression_close_authority_receipt_sha256
            ),
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if self.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("committed event belongs to a different GLEW profile")
        for value, name in (
            (self.motif_receipt_sha256, "committed motif receipt"),
            (
                self.closed_experience_receipt_sha256,
                "event closed-experience receipt",
            ),
            (self.fact_strand_receipt_sha256, "event Fact Strand receipt"),
            (self.full_field_state_receipt_sha256, "event full-field state receipt"),
            (self.field_commit_receipt_sha256, "event field-commit receipt"),
            (
                self.dominant_motif_commit_receipt_sha256,
                "event dominant-motif commit receipt",
            ),
            (
                self.corrected_l6_lock_receipt_sha256,
                "event corrected-L6 lock receipt",
            ),
            (
                self.output_binding_bank_receipt_sha256,
                "event output-binding bank receipt",
            ),
            (self.source_state_receipt_sha256, "event source-state receipt"),
            (self.transition_edge_receipt_sha256, "event transition-edge receipt"),
            (self.result_state_receipt_sha256, "event result-state receipt"),
        ):
            receipt_registry.resolve(value, name)
        for digest in self.sensory_evidence_receipt_sha256s:
            receipt_registry.resolve(digest, "event sensory evidence receipt")
        complete_sensory = _complete_closed_experience_sensory_receipts(
            self.closed_experience_receipt_sha256,
            receipt_registry,
        )
        if self.sensory_evidence_receipt_sha256s != complete_sensory:
            raise ReceiptError(
                "committed event does not cite the complete authenticated "
                "non-language sensory evidence of its closed experience"
            )
        if self.event_kind is MotifEventKind.EXPRESSION_CLOSE:
            close_digest = self.expression_close_authority_receipt_sha256
            if close_digest is None:
                raise ReceiptError("expression-close authority is absent")
            mounted_close = receipt_registry.resolve(
                close_digest,
                "expression-close authority receipt",
            )
            expected_close = expression_close_authority_receipt_payload(
                expression_id=self.expression_id,
                close_motif_receipt_sha256=self.motif_receipt_sha256,
            )
            if mounted_close != expected_close:
                raise ReceiptError(
                    "expression-close authority differs from its mounted exact bytes"
                )
        mounted_event = receipt_registry.resolve(
            self.event_receipt_sha256,
            "committed motif event receipt",
        )
        if mounted_event != self.payload():
            raise ReceiptError("committed motif event differs from its mounted exact bytes")


def _output_settlement_receipt_payload(
    *,
    expression_id: str,
    event_id: str,
    event_receipt_sha256: str,
    source_state_receipt_sha256: str,
    transition_edge_receipt_sha256: str,
    result_state_receipt_sha256: str,
    status: OutputStatus,
    reason: OutputReason,
    stage_disposition: StageDisposition,
    visible_text: str,
    emitted_scalar_codepoints: tuple[int, ...],
    contributing_event_receipt_sha256s: tuple[str, ...],
    binding_receipt_sha256s: tuple[str, ...],
    failure_detail: str,
) -> bytes:
    require_identifier(expression_id, "settlement expression id")
    require_identifier(event_id, "settlement event id")
    for value, name in (
        (event_receipt_sha256, "settlement event receipt"),
        (source_state_receipt_sha256, "settlement source-state receipt"),
        (transition_edge_receipt_sha256, "settlement transition-edge receipt"),
        (result_state_receipt_sha256, "settlement result-state receipt"),
    ):
        sha256_digest(value, name)
    if not isinstance(status, OutputStatus):
        raise ReceiptError("settlement output status is not ratified")
    if not isinstance(reason, OutputReason):
        raise ReceiptError("settlement output reason is not ratified")
    if not isinstance(stage_disposition, StageDisposition):
        raise ReceiptError("settlement stage disposition is not ratified")
    if not isinstance(visible_text, str):
        raise ReceiptError("settlement visible text must be Unicode text")
    if not isinstance(emitted_scalar_codepoints, tuple):
        raise ReceiptError("emitted scalars must be an immutable tuple")
    for scalar in emitted_scalar_codepoints:
        if (
            isinstance(scalar, bool)
            or not isinstance(scalar, int)
            or not 0 <= scalar <= 0x10FFFF
            or 0xD800 <= scalar <= 0xDFFF
        ):
            raise ReceiptError("settlement contains a non-Unicode scalar")
    if visible_text != "".join(chr(value) for value in emitted_scalar_codepoints):
        raise ReceiptError("visible text differs from emitted scalar receipts")
    for values, name in (
        (contributing_event_receipt_sha256s, "contributing event receipts"),
        (binding_receipt_sha256s, "settlement binding receipts"),
    ):
        if not isinstance(values, tuple):
            raise ReceiptError(f"{name} must be an immutable tuple")
        for index, digest in enumerate(values):
            sha256_digest(digest, f"{name}[{index}]")
    if not isinstance(failure_detail, str):
        raise ReceiptError("settlement failure detail must be text")

    released = status is OutputStatus.EXPRESSION_RELEASED
    if released:
        if not visible_text or not emitted_scalar_codepoints:
            raise ReceiptError("a released expression cannot be empty")
        if len(contributing_event_receipt_sha256s) != len(
            emitted_scalar_codepoints
        ) or len(binding_receipt_sha256s) != len(emitted_scalar_codepoints):
            raise ReceiptError("released expression lost scalar provenance cardinality")
        if stage_disposition is not StageDisposition.RELEASED_AND_CLEARED:
            raise ReceiptError("released expression must clear its private stage")
        if failure_detail:
            raise ReceiptError("released expression cannot carry a failure detail")
    elif (
        visible_text
        or emitted_scalar_codepoints
        or contributing_event_receipt_sha256s
        or binding_receipt_sha256s
    ):
        raise ReceiptError("a non-release settlement cannot expose staged language")

    return _canonical_bytes(
        {
            "binding_receipt_sha256s": list(binding_receipt_sha256s),
            "contributing_event_receipt_sha256s": list(
                contributing_event_receipt_sha256s
            ),
            "emitted_scalar_cardinality": len(emitted_scalar_codepoints),
            "emitted_scalar_codepoints": list(emitted_scalar_codepoints),
            "event_id": event_id,
            "event_receipt_sha256": event_receipt_sha256,
            "expression_id": expression_id,
            "failure_detail": failure_detail,
            "reason": reason.value,
            "result_state_receipt_sha256": result_state_receipt_sha256,
            "schema": "glew.output.expression_settlement.v1",
            "source_state_receipt_sha256": source_state_receipt_sha256,
            "stage_disposition": stage_disposition.value,
            "status": status.value,
            "transition_edge_receipt_sha256": transition_edge_receipt_sha256,
            "visible_text": visible_text,
        }
    )


@dataclass(frozen=True, slots=True)
class OutputSettlementReceipt:
    expression_id: str
    event_id: str
    event_receipt_sha256: str
    source_state_receipt_sha256: str
    transition_edge_receipt_sha256: str
    result_state_receipt_sha256: str
    status: OutputStatus
    reason: OutputReason
    stage_disposition: StageDisposition
    visible_text: str
    emitted_scalar_codepoints: tuple[int, ...]
    contributing_event_receipt_sha256s: tuple[str, ...]
    binding_receipt_sha256s: tuple[str, ...]
    failure_detail: str
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        expected = _output_settlement_receipt_payload(
            expression_id=self.expression_id,
            event_id=self.event_id,
            event_receipt_sha256=self.event_receipt_sha256,
            source_state_receipt_sha256=self.source_state_receipt_sha256,
            transition_edge_receipt_sha256=self.transition_edge_receipt_sha256,
            result_state_receipt_sha256=self.result_state_receipt_sha256,
            status=self.status,
            reason=self.reason,
            stage_disposition=self.stage_disposition,
            visible_text=self.visible_text,
            emitted_scalar_codepoints=self.emitted_scalar_codepoints,
            contributing_event_receipt_sha256s=(
                self.contributing_event_receipt_sha256s
            ),
            binding_receipt_sha256s=self.binding_receipt_sha256s,
            failure_detail=self.failure_detail,
        )
        if not isinstance(self.receipt_payload, bytes) or self.receipt_payload != expected:
            raise ReceiptError("output settlement differs from its exact receipt bytes")
        if receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("output settlement digest differs from its exact bytes")

    @property
    def silent(self) -> bool:
        return not self.visible_text


@dataclass(frozen=True, slots=True)
class OutputActuation:
    """The only public actuation surface; text is empty before exact close."""

    text: str
    receipt: OutputSettlementReceipt

    def __post_init__(self) -> None:
        if self.text != self.receipt.visible_text:
            raise ReceiptError("actuation text differs from its settlement receipt")


@dataclass(frozen=True, slots=True)
class _StagedScalar:
    codepoint: int
    event_receipt_sha256: str
    binding_receipt_sha256: str


class RememberedExpressionActuator:
    """Atomic private stage for one exact remembered expression transaction."""

    __slots__ = (
        "_expression_id",
        "_profile_binding_sha256",
        "_current_state_receipt_sha256",
        "_seen_state_edges",
        "_staged",
        "_terminal",
        "_lock",
    )

    def __init__(
        self,
        *,
        expression_id: str,
        profile_binding_sha256: str,
        initial_state_receipt_sha256: str,
    ) -> None:
        self._expression_id = require_identifier(expression_id, "expression id")
        self._profile_binding_sha256 = sha256_digest(
            profile_binding_sha256,
            "actuator profile receipt",
        )
        self._current_state_receipt_sha256 = sha256_digest(
            initial_state_receipt_sha256,
            "actuator initial-state receipt",
        )
        self._seen_state_edges: set[tuple[str, str]] = set()
        self._staged: list[_StagedScalar] = []
        self._terminal = False
        self._lock = threading.Lock()

    def process(
        self,
        *,
        event: CommittedMotifEvent,
        binding_bank: MotifBindingBank,
        receipt_registry: ReceiptRegistry,
    ) -> OutputActuation:
        """Settle one committed motif without ever exposing a partial expression."""

        if not isinstance(event, CommittedMotifEvent):
            raise ReceiptError("output actuation requires a committed motif event")
        if not isinstance(binding_bank, MotifBindingBank):
            raise ReceiptError("output actuation requires a complete binding bank")
        if not isinstance(receipt_registry, ReceiptRegistry):
            raise ReceiptError("output actuation requires a mounted receipt registry")
        with self._lock:
            try:
                return self._process_verified(
                    event=event,
                    binding_bank=binding_bank,
                    receipt_registry=receipt_registry,
                )
            except ReceiptError as exc:
                return self._discard_and_silence(
                    event=event,
                    reason=OutputReason.RECEIPT_FAILURE,
                    failure_detail=str(exc),
                )

    def _process_verified(
        self,
        *,
        event: CommittedMotifEvent,
        binding_bank: MotifBindingBank,
        receipt_registry: ReceiptRegistry,
    ) -> OutputActuation:
        if receipt_registry.profile_binding_sha256 != self._profile_binding_sha256:
            raise ReceiptError("active receipt registry changed GLEW profile")
        event.verify(receipt_registry)
        if event.output_binding_bank_receipt_sha256 != binding_bank.bank_receipt_sha256:
            raise ReceiptError(
                "committed event cites a different complete output-binding bank"
            )
        binding_bank.verify_for_motif(
            receipt_registry,
            (
                event.motif_receipt_sha256
                if event.event_kind is MotifEventKind.CONTENT
                else None
            ),
        )
        if event.expression_id != self._expression_id:
            raise ReceiptError("committed event belongs to a different expression")
        if self._terminal:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.EXPRESSION_ALREADY_TERMINAL,
                failure_detail="expression transaction is already terminal",
            )
        if event.source_state_receipt_sha256 != self._current_state_receipt_sha256:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.SOURCE_STATE_MISMATCH,
                failure_detail="committed event does not continue the exact settled state",
            )

        state_edge = (
            event.source_state_receipt_sha256,
            event.transition_edge_receipt_sha256,
        )
        if state_edge in self._seen_state_edges:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.EXACT_STATE_EDGE_CYCLE,
                failure_detail="exact source state and transition edge repeated",
            )
        self._seen_state_edges.add(state_edge)
        self._current_state_receipt_sha256 = event.result_state_receipt_sha256

        if event.event_kind is MotifEventKind.EXPRESSION_CLOSE:
            if not self._staged:
                self._terminal = True
                return self._settlement(
                    event=event,
                    status=OutputStatus.CONTINUED_SILENCE,
                    reason=OutputReason.EMPTY_EXPRESSION_CLOSE,
                    stage_disposition=StageDisposition.EMPTY,
                )
            staged = tuple(self._staged)
            self._staged.clear()
            self._terminal = True
            text = "".join(chr(item.codepoint) for item in staged)
            return self._settlement(
                event=event,
                status=OutputStatus.EXPRESSION_RELEASED,
                reason=OutputReason.EXACT_EXPRESSION_CLOSE_COMMITTED,
                stage_disposition=StageDisposition.RELEASED_AND_CLEARED,
                visible_text=text,
                emitted_scalar_codepoints=tuple(
                    item.codepoint for item in staged
                ),
                contributing_event_receipt_sha256s=tuple(
                    item.event_receipt_sha256 for item in staged
                ),
                binding_receipt_sha256s=tuple(
                    item.binding_receipt_sha256 for item in staged
                ),
            )

        bindings = binding_bank.for_motif(event.motif_receipt_sha256)
        if not bindings:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.MISSING_BINDING,
                failure_detail="committed motif has no coexperienced output binding",
            )
        kinds = {binding.kind for binding in bindings}
        if len(kinds) != 1:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.MIXED_LANGUAGE_AND_NO_OUTPUT,
                failure_detail=(
                    "committed motif has both language and explicit no-output bindings"
                ),
            )
        if kinds == {OutputBindingKind.NO_OUTPUT}:
            return self._settlement(
                event=event,
                status=OutputStatus.CONTINUED_SILENCE,
                reason=OutputReason.COEXPERIENCED_NO_OUTPUT,
                stage_disposition=(
                    StageDisposition.RETAINED_PRIVATE
                    if self._staged
                    else StageDisposition.EMPTY
                ),
            )

        decoded = tuple(
            (binding, binding.decoded_scalar()) for binding in bindings
        )
        distinct = {scalar for _, scalar in decoded}
        if len(distinct) != 1:
            return self._discard_and_silence(
                event=event,
                reason=OutputReason.CONFLICTING_LANGUAGE_BINDINGS,
                failure_detail=(
                    "committed motif has more than one distinct language scalar"
                ),
            )
        binding, scalar = decoded[0]
        self._staged.append(
            _StagedScalar(
                codepoint=ord(scalar),
                event_receipt_sha256=event.event_receipt_sha256,
                binding_receipt_sha256=binding.binding_receipt_sha256,
            )
        )
        return self._settlement(
            event=event,
            status=OutputStatus.STAGED_PRIVATE,
            reason=OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING,
            stage_disposition=StageDisposition.RETAINED_PRIVATE,
        )

    def _discard_and_silence(
        self,
        *,
        event: CommittedMotifEvent,
        reason: OutputReason,
        failure_detail: str,
    ) -> OutputActuation:
        disposition = (
            StageDisposition.DISCARDED if self._staged else StageDisposition.EMPTY
        )
        self._staged.clear()
        self._terminal = True
        return self._settlement(
            event=event,
            status=OutputStatus.UNKNOWN_SILENCE,
            reason=reason,
            stage_disposition=disposition,
            failure_detail=failure_detail,
        )

    def _settlement(
        self,
        *,
        event: CommittedMotifEvent,
        status: OutputStatus,
        reason: OutputReason,
        stage_disposition: StageDisposition,
        visible_text: str = "",
        emitted_scalar_codepoints: tuple[int, ...] = (),
        contributing_event_receipt_sha256s: tuple[str, ...] = (),
        binding_receipt_sha256s: tuple[str, ...] = (),
        failure_detail: str = "",
    ) -> OutputActuation:
        payload = _output_settlement_receipt_payload(
            expression_id=self._expression_id,
            event_id=event.event_id,
            event_receipt_sha256=event.event_receipt_sha256,
            source_state_receipt_sha256=event.source_state_receipt_sha256,
            transition_edge_receipt_sha256=event.transition_edge_receipt_sha256,
            result_state_receipt_sha256=event.result_state_receipt_sha256,
            status=status,
            reason=reason,
            stage_disposition=stage_disposition,
            visible_text=visible_text,
            emitted_scalar_codepoints=emitted_scalar_codepoints,
            contributing_event_receipt_sha256s=(
                contributing_event_receipt_sha256s
            ),
            binding_receipt_sha256s=binding_receipt_sha256s,
            failure_detail=failure_detail,
        )
        receipt = OutputSettlementReceipt(
            expression_id=self._expression_id,
            event_id=event.event_id,
            event_receipt_sha256=event.event_receipt_sha256,
            source_state_receipt_sha256=event.source_state_receipt_sha256,
            transition_edge_receipt_sha256=event.transition_edge_receipt_sha256,
            result_state_receipt_sha256=event.result_state_receipt_sha256,
            status=status,
            reason=reason,
            stage_disposition=stage_disposition,
            visible_text=visible_text,
            emitted_scalar_codepoints=emitted_scalar_codepoints,
            contributing_event_receipt_sha256s=(
                contributing_event_receipt_sha256s
            ),
            binding_receipt_sha256s=binding_receipt_sha256s,
            failure_detail=failure_detail,
            receipt_sha256=receipt_sha256(payload),
            receipt_payload=payload,
        )
        return OutputActuation(text=visible_text, receipt=receipt)


__all__ = (
    "CommittedMotifEvent",
    "MotifBindingBank",
    "MotifEventKind",
    "MotifOutputBinding",
    "OutputActuation",
    "OutputBindingKind",
    "OutputReason",
    "OutputSettlementReceipt",
    "OutputStatus",
    "RememberedExpressionActuator",
    "StageDisposition",
    "committed_motif_event_receipt_payload",
    "decode_balanced_ternary_scalar",
    "expression_close_authority_receipt_payload",
    "motif_binding_bank_receipt_payload",
    "motif_output_binding_receipt_payload",
)
