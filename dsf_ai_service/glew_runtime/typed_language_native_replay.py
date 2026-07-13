"""Exact typed-language replay and its discrete contingent tangent cone.

Typed language is a native discrete physical lane.  One authenticated
``TypedLanguageFrozenKernelInput`` is the sole authority for both the Unicode
event and its balanced-ternary samples.  The base event and every admissible
directed one-trit adjacency are replayed through the frozen L0--L4 kernel while
all non-language streams remain unchanged.

Language does not claim the continuous same-branch/cell derivative used by
sensor ports.  Its Bouligand (contingent) tangent cone is the complete set of
exact one-sided secants

    (adjacent L4 - base L4) / (adjacent trit - base trit).

Every direction retains its source and target branch/cell identities and an
exact first-class reversal receipt.  Every nonzero seven-field secant becomes
one raw language row in Fixed-42.  An exact-zero secant receives an explicit
zero-response receipt and never becomes a forbidden zero row.  One mounted
completeness receipt binds every direction, reversal, row, and zero response.

There is no averaging, normalization, nullspace selection, score, tolerance,
lookup authority, or same-cell veto in this language operator.  Continuous
sensor replay remains governed by its existing physical producer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Iterable

from .closed_experience import (
    ClosedExperienceEvidencePreparation,
    ClosedExperienceProviderUnknown,
    KernelNativeInputSample,
    KernelNativeInputStream,
    ProviderStatus,
    kernel_native_input_receipt_payload,
    prepare_closed_experience_evidence,
    source_evidence_stream_receipt_payload,
)
from .field import MountedFieldTopology
from .global_uf import MountedPreWindowState
from .l6 import (
    FIELD_ORDER,
    ConstraintRow,
    ConstraintRowProvenance,
    ExactRankReceipt,
    Fixed42ConstraintStack,
    L6Lane,
    NativeConstraintCovector,
    canonical_completeness_receipt_payload,
    canonical_row_receipt_payload,
    embed_native_covector,
    exact_rank_receipt,
)
from .language import TypedLanguageFrozenKernelInput
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    ResonanceOperatorAuthority,
)
from .physical_l6_tangents import (
    ExactL4Response,
    LanguageTritCoordinate,
    MountedNativePerturbationProfile,
    MountedNativeResponseSet,
    NativeDirection,
    NativeL4ReplayResponse,
    NativePortReplayBundle,
    NativeReplayCase,
    NativeReplayCaseKind,
    TypedTrit,
    enumerate_native_replay_cases,
    native_l4_replay_response_receipt_payload,
    native_perturbation_profile_receipt_payload,
    native_response_set_receipt_payload,
)


TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID = (
    "glew.typed_language.actual_frozen_kernel_native_replay.v2"
)
TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID = (
    "glew.typed_language.bouligand_one_sided_tangent_cone.v1"
)
TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID = (
    "glew.l6.typed_language.directed_exact_secant.v1"
)

_L4_FIELDS = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _l4_payload(value: ExactL4Response) -> dict[str, str]:
    if not isinstance(value, ExactL4Response):
        raise ReceiptError("language direction must preserve all seven L4 fields")
    return {
        field.value: _fraction_text(getattr(value, field.value))
        for field in FIELD_ORDER
    }


def _extend_records(
    registry: ReceiptRegistry,
    records: Iterable[ReceiptRecord],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("typed-language replay requires a receipt registry")
    mounted = {record.digest: record.payload for record in registry.records}
    additions: dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("typed-language replay received an untyped receipt")
        previous = mounted.get(record.digest)
        if previous is not None and previous != record.payload:
            raise ReceiptError("typed-language replay receipt digest collision")
        previous = additions.get(record.digest)
        if previous is not None and previous != record.payload:
            raise ReceiptError("typed-language replay repeated altered receipt bytes")
        additions[record.digest] = record.payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        (
            *registry.records,
            *tuple(
                ReceiptRecord(digest, additions[digest])
                for digest in sorted(additions)
                if digest not in mounted
            ),
        ),
    )


def _extend_payloads(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    records = []
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("typed-language replay produced an empty receipt")
        records.append(ReceiptRecord(receipt_sha256(payload), payload))
    return _extend_records(registry, records)


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    field_name: str,
) -> None:
    mounted = registry.resolve(digest, field_name)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} differs from mounted authority bytes")


def _sign_class(value: str) -> str:
    exact = Fraction(value)
    if exact < 0:
        return "negative"
    if exact > 0:
        return "positive"
    return "exact_zero"


def _actual_branch_and_cell(raw_payload: bytes) -> tuple[str, str]:
    try:
        raw = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("typed-language frozen trace is not canonical JSON") from exc
    branch_payload = _canonical_bytes(
        {
            "L1": [
                {
                    "C_k": value["C_k"],
                    "N_gate": value["N_gate"],
                    "end_idx": value["end_idx"],
                    "projections": value["projections"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L1_GateL1State"]
            ],
            "L2": [
                {
                    "IAS_k": value["IAS_k"],
                    "end_idx": value["end_idx"],
                    "regime": value["regime"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L2_GateInterpretation"]
            ],
            "L3": [
                {
                    "Hyst_k": value["Hyst_k"],
                    "end_idx": value["end_idx"],
                    "g_k": value["g_k"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L3_ResonanceResult"]
            ],
            "schema": "glew.typed_language.actual_branch.v1",
        }
    )
    cell_payload = _canonical_bytes(
        {
            "L4_semialgebraic_sign_zero_cells": [
                {field: _sign_class(value[field]) for field in _L4_FIELDS}
                for value in raw["L4_DSF"]
            ],
            "classification_role": "secondary_identity_only",
            "schema": "glew.typed_language.actual_cell.v2",
        }
    )
    return f"branch-{branch_payload.hex()}", f"cell-{cell_payload.hex()}"


@dataclass(frozen=True, slots=True)
class TypedLanguageNativeReplayExecution:
    case: NativeReplayCase
    language_stream: EvidenceStream
    language_kernel_input: KernelNativeInputStream
    preparation: ClosedExperienceEvidencePreparation
    l4_response: ExactL4Response
    source_stream_receipt_sha256: str
    l0_l4_trace_receipt_sha256: str
    branch_id: str
    cell_id: str
    source_operator_receipt_sha256: str


def typed_language_reversal_receipt_payload(
    *,
    case_receipt_sha256: str,
    base_response_receipt_sha256: str,
    adjacent_response_receipt_sha256: str,
    source_branch_id: str,
    source_cell_id: str,
    target_branch_id: str,
    target_cell_id: str,
    source_R_rev_k: Fraction,
    target_R_rev_k: Fraction,
    signed_R_rev_secant: Fraction,
) -> bytes:
    for digest, field_name in (
        (case_receipt_sha256, "language reversal case receipt"),
        (base_response_receipt_sha256, "language reversal base response"),
        (adjacent_response_receipt_sha256, "language reversal adjacent response"),
    ):
        sha256_digest(digest, field_name)
    for value, field_name in (
        (source_branch_id, "language reversal source branch"),
        (source_cell_id, "language reversal source cell"),
        (target_branch_id, "language reversal target branch"),
        (target_cell_id, "language reversal target cell"),
    ):
        require_identifier(value, field_name)
    return _canonical_bytes(
        {
            "adjacent_response_receipt_sha256": adjacent_response_receipt_sha256,
            "base_response_receipt_sha256": base_response_receipt_sha256,
            "case_receipt_sha256": case_receipt_sha256,
            "signed_R_rev_secant": _fraction_text(signed_R_rev_secant),
            "source_R_rev_k": _fraction_text(source_R_rev_k),
            "source_branch_id": source_branch_id,
            "source_cell_id": source_cell_id,
            "target_R_rev_k": _fraction_text(target_R_rev_k),
            "target_branch_id": target_branch_id,
            "target_cell_id": target_cell_id,
            "schema": "glew.typed_language.first_class_reversal_transition.v1",
        }
    )


def typed_language_zero_response_receipt_payload(
    *,
    case_receipt_sha256: str,
    coordinate_id: str,
    direction: NativeDirection,
    native_delta: Fraction,
    base_response_receipt_sha256: str,
    adjacent_response_receipt_sha256: str,
    secant: ExactL4Response,
) -> bytes:
    if any(secant.as_tuple()):
        raise ReceiptError("zero-response receipt cannot bind a nonzero secant")
    require_identifier(coordinate_id, "zero-response coordinate")
    if not isinstance(direction, NativeDirection):
        raise ReceiptError("zero-response direction must be typed")
    for digest, field_name in (
        (case_receipt_sha256, "zero-response case receipt"),
        (base_response_receipt_sha256, "zero-response base response"),
        (adjacent_response_receipt_sha256, "zero-response adjacent response"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "adjacent_response_receipt_sha256": adjacent_response_receipt_sha256,
            "base_response_receipt_sha256": base_response_receipt_sha256,
            "case_receipt_sha256": case_receipt_sha256,
            "coordinate_id": coordinate_id,
            "direction": int(direction),
            "field_order": [value.value for value in FIELD_ORDER],
            "native_delta": _fraction_text(native_delta),
            "schema": "glew.typed_language.exact_zero_direction_response.v1",
            "secant": _l4_payload(secant),
        }
    )


def typed_language_direction_receipt_payload(
    *,
    direction_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    language_capture_receipt_sha256: str,
    case_receipt_sha256: str,
    coordinate_id: str,
    direction: NativeDirection,
    native_delta: Fraction,
    base_response_receipt_sha256: str,
    adjacent_response_receipt_sha256: str,
    source_branch_id: str,
    source_cell_id: str,
    target_branch_id: str,
    target_cell_id: str,
    secant: ExactL4Response,
    reversal_receipt_sha256: str,
    row_receipt_sha256: str | None,
    zero_response_receipt_sha256: str | None,
) -> bytes:
    require_identifier(direction_id, "language contingent direction_id")
    require_identifier(coordinate_id, "language contingent coordinate_id")
    if not isinstance(direction, NativeDirection):
        raise ReceiptError("language contingent direction must be typed")
    require_fraction(native_delta, "language contingent native_delta")
    if native_delta == 0:
        raise ReceiptError("language contingent direction cannot have zero delta")
    for digest, field_name in (
        (profile_receipt_sha256, "language direction profile receipt"),
        (pre_window_state_receipt_sha256, "language direction state receipt"),
        (language_capture_receipt_sha256, "language direction capture receipt"),
        (case_receipt_sha256, "language direction case receipt"),
        (base_response_receipt_sha256, "language direction base response"),
        (adjacent_response_receipt_sha256, "language direction adjacent response"),
        (reversal_receipt_sha256, "language direction reversal receipt"),
    ):
        sha256_digest(digest, field_name)
    for value, field_name in (
        (source_branch_id, "language direction source branch"),
        (source_cell_id, "language direction source cell"),
        (target_branch_id, "language direction target branch"),
        (target_cell_id, "language direction target cell"),
    ):
        require_identifier(value, field_name)
    is_zero = not any(secant.as_tuple())
    if is_zero:
        if row_receipt_sha256 is not None or zero_response_receipt_sha256 is None:
            raise ReceiptError("zero language direction requires only a zero receipt")
        sha256_digest(zero_response_receipt_sha256, "language zero response receipt")
    else:
        if row_receipt_sha256 is None or zero_response_receipt_sha256 is not None:
            raise ReceiptError("nonzero language direction requires exactly one row")
        sha256_digest(row_receipt_sha256, "language direction row receipt")
    return _canonical_bytes(
        {
            "adjacent_response_receipt_sha256": adjacent_response_receipt_sha256,
            "base_response_receipt_sha256": base_response_receipt_sha256,
            "case_receipt_sha256": case_receipt_sha256,
            "coordinate_id": coordinate_id,
            "direction": int(direction),
            "direction_id": direction_id,
            "field_order": [value.value for value in FIELD_ORDER],
            "language_capture_receipt_sha256": language_capture_receipt_sha256,
            "native_delta": _fraction_text(native_delta),
            "operator": TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "reversal_receipt_sha256": reversal_receipt_sha256,
            "row_receipt_sha256": row_receipt_sha256,
            "schema": "glew.typed_language.directed_contingent_secant.v1",
            "secant": _l4_payload(secant),
            "source_branch_id": source_branch_id,
            "source_cell_id": source_cell_id,
            "target_branch_id": target_branch_id,
            "target_cell_id": target_cell_id,
            "zero_response_receipt_sha256": zero_response_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class TypedLanguageContingentDirection:
    direction_id: str
    case_receipt_sha256: str
    coordinate_id: str
    direction: NativeDirection
    native_delta: Fraction
    base_response_receipt_sha256: str
    adjacent_response_receipt_sha256: str
    source_branch_id: str
    source_cell_id: str
    target_branch_id: str
    target_cell_id: str
    secant: ExactL4Response
    reversal_receipt_sha256: str
    row: ConstraintRow | None
    zero_response_receipt_sha256: str | None
    authority_receipt_sha256: str

    def verify(
        self,
        *,
        profile: MountedNativePerturbationProfile,
        pre_window_state: MountedPreWindowState,
        language_capture_receipt_sha256: str,
        base_response: NativeL4ReplayResponse,
        case: NativeReplayCase,
        adjacent_response: NativeL4ReplayResponse,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if case.kind is not NativeReplayCaseKind.LANGUAGE_TYPED_TRIT:
            raise ReceiptError("contingent direction is not a typed-trit adjacency")
        if (
            self.case_receipt_sha256 != case.receipt_sha256
            or self.coordinate_id != case.target_coordinate_id
            or self.direction is not case.direction
            or self.native_delta != case.native_delta
        ):
            raise ReceiptError("contingent direction differs from its replay case")
        if (
            self.base_response_receipt_sha256 != base_response.receipt_sha256
            or self.adjacent_response_receipt_sha256
            != adjacent_response.receipt_sha256
        ):
            raise ReceiptError("contingent direction differs from replay responses")
        if (
            self.source_branch_id != base_response.branch_id
            or self.source_cell_id != base_response.cell_id
            or self.target_branch_id != adjacent_response.branch_id
            or self.target_cell_id != adjacent_response.cell_id
        ):
            raise ReceiptError("contingent direction loses source/target geometry")
        expected_secant = ExactL4Response(
            *tuple(
                (target - source) / case.native_delta
                for source, target in zip(
                    base_response.l4_response.as_tuple(),
                    adjacent_response.l4_response.as_tuple(),
                    strict=True,
                )
            )
        )
        if self.secant != expected_secant:
            raise ReceiptError("language direction secant is not exact")
        reversal_payload = typed_language_reversal_receipt_payload(
            case_receipt_sha256=case.receipt_sha256,
            base_response_receipt_sha256=base_response.receipt_sha256,
            adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
            source_branch_id=base_response.branch_id,
            source_cell_id=base_response.cell_id,
            target_branch_id=adjacent_response.branch_id,
            target_cell_id=adjacent_response.cell_id,
            source_R_rev_k=base_response.l4_response.R_rev_k,
            target_R_rev_k=adjacent_response.l4_response.R_rev_k,
            signed_R_rev_secant=expected_secant.R_rev_k,
        )
        _mounted_exact(
            receipt_registry,
            self.reversal_receipt_sha256,
            reversal_payload,
            "language first-class reversal receipt",
        )
        row_digest = None
        zero_digest = None
        if any(expected_secant.as_tuple()):
            if self.row is None or self.zero_response_receipt_sha256 is not None:
                raise ReceiptError("nonzero language secant lost its single row")
            expected_row_payload = canonical_row_receipt_payload(
                lane=L6Lane.LANGUAGE,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                operator_id=TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID,
                row_id=self.direction_id,
                coefficients=expected_secant.as_tuple(),
            )
            row_digest = receipt_sha256(expected_row_payload)
            if (
                self.row.provenance.lane is not L6Lane.LANGUAGE
                or self.row.provenance.provider_id != profile.provider_id
                or self.row.provenance.native_port_id != profile.native_port_id
                or self.row.provenance.operator_id
                != TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID
                or self.row.provenance.row_id != self.direction_id
                or self.row.provenance.receipt_sha256 != row_digest
                or self.row.native_coefficients != expected_secant.as_tuple()
            ):
                raise ReceiptError("language Fixed42 row differs from its secant")
            _mounted_exact(
                receipt_registry,
                row_digest,
                expected_row_payload,
                "language direction row receipt",
            )
        else:
            if self.row is not None or self.zero_response_receipt_sha256 is None:
                raise ReceiptError("zero language secant was emitted as a row")
            zero_payload = typed_language_zero_response_receipt_payload(
                case_receipt_sha256=case.receipt_sha256,
                coordinate_id=self.coordinate_id,
                direction=self.direction,
                native_delta=self.native_delta,
                base_response_receipt_sha256=base_response.receipt_sha256,
                adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
                secant=expected_secant,
            )
            zero_digest = receipt_sha256(zero_payload)
            if self.zero_response_receipt_sha256 != zero_digest:
                raise ReceiptError("zero language direction receipt is altered")
            _mounted_exact(
                receipt_registry,
                zero_digest,
                zero_payload,
                "language zero-response direction receipt",
            )
        direction_payload = typed_language_direction_receipt_payload(
            direction_id=self.direction_id,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=(
                pre_window_state.authority_receipt_sha256
            ),
            language_capture_receipt_sha256=language_capture_receipt_sha256,
            case_receipt_sha256=case.receipt_sha256,
            coordinate_id=self.coordinate_id,
            direction=self.direction,
            native_delta=self.native_delta,
            base_response_receipt_sha256=base_response.receipt_sha256,
            adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
            source_branch_id=self.source_branch_id,
            source_cell_id=self.source_cell_id,
            target_branch_id=self.target_branch_id,
            target_cell_id=self.target_cell_id,
            secant=self.secant,
            reversal_receipt_sha256=self.reversal_receipt_sha256,
            row_receipt_sha256=row_digest,
            zero_response_receipt_sha256=zero_digest,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            direction_payload,
            "language contingent direction authority receipt",
        )


def typed_language_cone_completeness_receipt_payload(
    *,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    language_capture_receipt_sha256: str,
    base_case_receipt_sha256: str,
    base_response_receipt_sha256: str,
    adjacent_case_receipt_sha256s: tuple[str, ...],
    direction_receipt_sha256s: tuple[str, ...],
    reversal_receipt_sha256s: tuple[str, ...],
    row_receipt_sha256s: tuple[str, ...],
    zero_response_receipt_sha256s: tuple[str, ...],
) -> bytes:
    sequences = (
        adjacent_case_receipt_sha256s,
        direction_receipt_sha256s,
        reversal_receipt_sha256s,
    )
    if not all(isinstance(value, tuple) for value in sequences):
        raise ReceiptError("language cone completeness sequences must be immutable")
    if not (
        len(adjacent_case_receipt_sha256s)
        == len(direction_receipt_sha256s)
        == len(reversal_receipt_sha256s)
    ):
        raise ReceiptError("language cone completeness omits a direction")
    for digest in (
        profile_receipt_sha256,
        pre_window_state_receipt_sha256,
        language_capture_receipt_sha256,
        base_case_receipt_sha256,
        base_response_receipt_sha256,
        *adjacent_case_receipt_sha256s,
        *direction_receipt_sha256s,
        *reversal_receipt_sha256s,
        *row_receipt_sha256s,
        *zero_response_receipt_sha256s,
    ):
        sha256_digest(digest, "language cone completeness receipt member")
    if len(set(adjacent_case_receipt_sha256s)) != len(
        adjacent_case_receipt_sha256s
    ):
        raise ReceiptError("language cone repeats an adjacent case")
    if len(row_receipt_sha256s) + len(zero_response_receipt_sha256s) != len(
        direction_receipt_sha256s
    ):
        raise ReceiptError("each language direction must be a row or exact zero")
    return _canonical_bytes(
        {
            "adjacent_case_receipt_sha256s": list(
                adjacent_case_receipt_sha256s
            ),
            "base_case_receipt_sha256": base_case_receipt_sha256,
            "base_response_receipt_sha256": base_response_receipt_sha256,
            "direction_receipt_sha256s": list(direction_receipt_sha256s),
            "field_order": [value.value for value in FIELD_ORDER],
            "language_capture_receipt_sha256": language_capture_receipt_sha256,
            "operator": TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "reversal_receipt_sha256s": list(reversal_receipt_sha256s),
            "row_receipt_sha256s": list(row_receipt_sha256s),
            "schema": "glew.typed_language.contingent_cone_completeness.v1",
            "zero_response_receipt_sha256s": list(
                zero_response_receipt_sha256s
            ),
        }
    )


def typed_language_exact_rank_receipt_payload(
    *,
    row_completeness_receipt_sha256: str,
    rank_receipt: ExactRankReceipt,
) -> bytes:
    sha256_digest(
        row_completeness_receipt_sha256,
        "language row completeness receipt",
    )
    if not isinstance(rank_receipt, ExactRankReceipt):
        raise ReceiptError("language cone rank must be exact")
    return _canonical_bytes(
        {
            "n_effective": rank_receipt.n_effective,
            "n_start": rank_receipt.n_start,
            "pivot_columns": list(rank_receipt.pivot_columns),
            "rank": rank_receipt.rank,
            "row_completeness_receipt_sha256": (
                row_completeness_receipt_sha256
            ),
            "row_count": rank_receipt.row_count,
            "schema": "glew.typed_language.exact_fixed42_rank.v1",
        }
    )


def typed_language_contingent_cone_receipt_payload(
    *,
    provider_id: str,
    native_port_id: str,
    profile_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    language_capture_receipt_sha256: str,
    response_set_receipt_sha256: str,
    direction_completeness_receipt_sha256: str,
    row_completeness_receipt_sha256: str,
    rank_receipt_sha256: str,
) -> bytes:
    require_identifier(provider_id, "language cone provider_id")
    require_identifier(native_port_id, "language cone native_port_id")
    for digest, field_name in (
        (profile_receipt_sha256, "language cone profile receipt"),
        (pre_window_state_receipt_sha256, "language cone state receipt"),
        (language_capture_receipt_sha256, "language cone capture receipt"),
        (response_set_receipt_sha256, "language cone response-set receipt"),
        (
            direction_completeness_receipt_sha256,
            "language cone direction completeness receipt",
        ),
        (row_completeness_receipt_sha256, "language cone row completeness receipt"),
        (rank_receipt_sha256, "language cone rank receipt"),
    ):
        sha256_digest(digest, field_name)
    return _canonical_bytes(
        {
            "direction_completeness_receipt_sha256": (
                direction_completeness_receipt_sha256
            ),
            "language_capture_receipt_sha256": language_capture_receipt_sha256,
            "lane": L6Lane.LANGUAGE.value,
            "native_port_id": native_port_id,
            "operator": TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_receipt_sha256": profile_receipt_sha256,
            "provider_id": provider_id,
            "rank_receipt_sha256": rank_receipt_sha256,
            "response_set_receipt_sha256": response_set_receipt_sha256,
            "row_completeness_receipt_sha256": (
                row_completeness_receipt_sha256
            ),
            "schema": "glew.typed_language.mounted_contingent_cone.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedTypedLanguageContingentCone:
    provider_id: str
    native_port_id: str
    profile_receipt_sha256: str
    pre_window_state_receipt_sha256: str
    language_capture_receipt_sha256: str
    response_set_receipt_sha256: str
    directions: tuple[TypedLanguageContingentDirection, ...]
    fixed42_stack: Fixed42ConstraintStack
    rank_receipt: ExactRankReceipt
    direction_completeness_receipt_sha256: str
    row_completeness_receipt_sha256: str
    rank_receipt_sha256: str
    authority_receipt_sha256: str

    @property
    def rows(self) -> tuple[ConstraintRow, ...]:
        return self.fixed42_stack.rows

    @property
    def zero_directions(self) -> tuple[TypedLanguageContingentDirection, ...]:
        return tuple(value for value in self.directions if value.row is None)

    def verify(
        self,
        *,
        profile: MountedNativePerturbationProfile,
        pre_window_state: MountedPreWindowState,
        cases: tuple[NativeReplayCase, ...],
        response_set: MountedNativeResponseSet,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (
            profile.lane is not L6Lane.LANGUAGE
            or self.provider_id != profile.provider_id
            or self.native_port_id != profile.native_port_id
            or self.profile_receipt_sha256 != profile.authority_receipt_sha256
            or self.pre_window_state_receipt_sha256
            != pre_window_state.authority_receipt_sha256
            or self.response_set_receipt_sha256
            != response_set.authority_receipt_sha256
        ):
            raise ReceiptError("language cone belongs to another mounted state")
        if not isinstance(self.directions, tuple) or not all(
            isinstance(value, TypedLanguageContingentDirection)
            for value in self.directions
        ):
            raise ReceiptError("language cone directions are not immutable and typed")
        if len(cases) < 2 or len(response_set.responses) != len(cases):
            raise ReceiptError("language cone needs base plus every adjacency")
        if len(self.directions) != len(cases) - 1:
            raise ReceiptError("language cone omitted an admissible direction")
        base_response = response_set.responses[0]
        for direction_value, case, response in zip(
            self.directions,
            cases[1:],
            response_set.responses[1:],
            strict=True,
        ):
            direction_value.verify(
                profile=profile,
                pre_window_state=pre_window_state,
                language_capture_receipt_sha256=(
                    self.language_capture_receipt_sha256
                ),
                base_response=base_response,
                case=case,
                adjacent_response=response,
                receipt_registry=receipt_registry,
            )
        expected_rows = tuple(
            value.row for value in self.directions if value.row is not None
        )
        if self.fixed42_stack != Fixed42ConstraintStack(expected_rows):
            raise ReceiptError("language cone Fixed42 rows are incomplete or reordered")
        expected_rank = exact_rank_receipt(self.fixed42_stack)
        if self.rank_receipt != expected_rank:
            raise ReceiptError("language cone exact rank differs from its rows")
        row_digests = tuple(
            value.provenance.receipt_sha256 for value in expected_rows
        )
        row_completeness_payload = canonical_completeness_receipt_payload(
            lane=L6Lane.LANGUAGE,
            row_receipt_sha256s=row_digests,
        )
        _mounted_exact(
            receipt_registry,
            self.row_completeness_receipt_sha256,
            row_completeness_payload,
            "language Fixed42 row completeness receipt",
        )
        direction_completeness_payload = (
            typed_language_cone_completeness_receipt_payload(
                profile_receipt_sha256=profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                language_capture_receipt_sha256=(
                    self.language_capture_receipt_sha256
                ),
                base_case_receipt_sha256=cases[0].receipt_sha256,
                base_response_receipt_sha256=base_response.receipt_sha256,
                adjacent_case_receipt_sha256s=tuple(
                    value.receipt_sha256 for value in cases[1:]
                ),
                direction_receipt_sha256s=tuple(
                    value.authority_receipt_sha256 for value in self.directions
                ),
                reversal_receipt_sha256s=tuple(
                    value.reversal_receipt_sha256 for value in self.directions
                ),
                row_receipt_sha256s=row_digests,
                zero_response_receipt_sha256s=tuple(
                    value.zero_response_receipt_sha256
                    for value in self.zero_directions
                    if value.zero_response_receipt_sha256 is not None
                ),
            )
        )
        _mounted_exact(
            receipt_registry,
            self.direction_completeness_receipt_sha256,
            direction_completeness_payload,
            "language direction completeness receipt",
        )
        rank_payload = typed_language_exact_rank_receipt_payload(
            row_completeness_receipt_sha256=(
                self.row_completeness_receipt_sha256
            ),
            rank_receipt=expected_rank,
        )
        _mounted_exact(
            receipt_registry,
            self.rank_receipt_sha256,
            rank_payload,
            "language exact rank receipt",
        )
        cone_payload = typed_language_contingent_cone_receipt_payload(
            provider_id=self.provider_id,
            native_port_id=self.native_port_id,
            profile_receipt_sha256=self.profile_receipt_sha256,
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            language_capture_receipt_sha256=(
                self.language_capture_receipt_sha256
            ),
            response_set_receipt_sha256=self.response_set_receipt_sha256,
            direction_completeness_receipt_sha256=(
                self.direction_completeness_receipt_sha256
            ),
            row_completeness_receipt_sha256=(
                self.row_completeness_receipt_sha256
            ),
            rank_receipt_sha256=self.rank_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            cone_payload,
            "language contingent cone authority receipt",
        )


@dataclass(frozen=True, slots=True)
class TypedLanguageNativeReplayResult:
    bundle: NativePortReplayBundle
    executions: tuple[TypedLanguageNativeReplayExecution, ...]
    contingent_cone: MountedTypedLanguageContingentCone
    receipt_registry: ReceiptRegistry


def _sample_positions(
    typed_input: TypedLanguageFrozenKernelInput,
) -> tuple[tuple[str, int, TypedTrit], ...]:
    trits = typed_input.event.trits
    samples = typed_input.stream.samples
    if len(samples) == len(trits):
        indexed = tuple(enumerate(trits))
    else:
        valid = tuple(value for value in trits if value.valid)
        if len(samples) != len(valid):
            raise ReceiptError(
                "typed-language stream length differs from its exact event trits"
            )
        indexed = tuple((sample_index, trit) for sample_index, trit in enumerate(valid))
    positions = []
    for sample_index, trit in indexed:
        if not trit.valid:
            continue
        if Fraction(trit.value) != samples[sample_index].signal:
            raise ReceiptError(
                "typed-language event trit differs from authenticated stream signal"
            )
        coordinate_id = f"unicode-{trit.scalar_index:08d}-trit-{trit.place:02d}"
        positions.append((coordinate_id, sample_index, TypedTrit(trit.value)))
    if not positions:
        raise ReceiptError("typed-language event has no valid native trit")
    ordered = tuple(sorted(positions, key=lambda value: value[0]))
    if len({value[0] for value in ordered}) != len(ordered):
        raise ReceiptError("typed-language native trit coordinates are not unique")
    return ordered


def _language_profile(
    *,
    typed_input: TypedLanguageFrozenKernelInput,
    pre_window_state: MountedPreWindowState,
    provider_id: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[
    MountedNativePerturbationProfile,
    tuple[NativeReplayCase, ...],
    tuple[tuple[str, int, TypedTrit], ...],
    ReceiptRegistry,
]:
    positions = _sample_positions(typed_input)
    coordinates = tuple(
        LanguageTritCoordinate(
            coordinate_id=coordinate_id,
            base_trit=base_trit,
            trit_authority_receipt_sha256=typed_input.event.event_receipt_sha256,
        )
        for coordinate_id, _, base_trit in positions
    )
    profile_id = f"{typed_input.event.event_id}:language-native"
    payload = native_perturbation_profile_receipt_payload(
        profile_id=profile_id,
        lane=L6Lane.LANGUAGE,
        provider_id=provider_id,
        native_port_id=typed_input.stream.port_id,
        sensor_coordinates=(),
        language_trit_coordinates=coordinates,
    )
    profile = MountedNativePerturbationProfile(
        profile_id=profile_id,
        lane=L6Lane.LANGUAGE,
        provider_id=provider_id,
        native_port_id=typed_input.stream.port_id,
        sensor_coordinates=(),
        language_trit_coordinates=coordinates,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    registry = _extend_payloads(receipt_registry, (payload,))
    profile.verify(registry)
    cases = enumerate_native_replay_cases(profile, pre_window_state)
    registry = _extend_payloads(registry, (case.receipt_payload for case in cases))
    return profile, cases, positions, registry


def _case_language_transport(
    *,
    case: NativeReplayCase,
    typed_input: TypedLanguageFrozenKernelInput,
    positions: tuple[tuple[str, int, TypedTrit], ...],
) -> tuple[EvidenceStream, KernelNativeInputStream, bytes, bytes]:
    case_trits = {value.coordinate_id: value.trit for value in case.language_trits}
    if set(case_trits) != {value[0] for value in positions}:
        raise ReceiptError("language replay case does not cover authenticated trits")
    changed_signals = [value.signal for value in typed_input.stream.samples]
    for coordinate_id, sample_index, base_trit in positions:
        target = case_trits[coordinate_id]
        changed_signals[sample_index] = Fraction(target)
        if case.target_coordinate_id == coordinate_id:
            if Fraction(int(target) - int(base_trit)) != case.native_delta:
                raise ReceiptError("language replay delta differs from adjacent trit")

    state = typed_input.initial_state
    samples = []
    for original, signal in zip(
        typed_input.stream.samples,
        changed_signals,
        strict=True,
    ):
        phase = state.phase_turns + typed_input.event.phase_kappa * signal * (
            original.timestamp - state.last_timestamp
        )
        sample = EvidenceSample(
            source_index=original.source_index,
            timestamp=original.timestamp,
            signal=signal,
            relevance=original.relevance,
            phase_turns=phase,
        )
        samples.append(sample)
        state = replace(
            state,
            last_source_index=sample.source_index,
            last_timestamp=sample.timestamp,
            phase_turns=sample.phase_turns,
        )
    stream = replace(
        typed_input.stream,
        evidence_id=f"{typed_input.event.event_id}:native:{case.case_index}",
        samples=tuple(samples),
    )
    stream_payload = source_evidence_stream_receipt_payload(stream)
    kernel_samples = tuple(
        KernelNativeInputSample(
            source_index=value.source_index,
            timestamp=value.timestamp,
            dimensionless_field=Fraction(1) + value.signal / 2,
            l0_relevance=value.relevance,
        )
        for value in stream.samples
    )
    kernel_payload = kernel_native_input_receipt_payload(
        adapter_id=typed_input.kernel_input.adapter_id,
        adapter_profile_receipt_sha256=(
            typed_input.kernel_input.adapter_profile_receipt_sha256
        ),
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        source_stream_receipt_sha256=receipt_sha256(stream_payload),
        samples=kernel_samples,
    )
    kernel_input = KernelNativeInputStream(
        adapter_id=typed_input.kernel_input.adapter_id,
        adapter_profile_receipt_sha256=(
            typed_input.kernel_input.adapter_profile_receipt_sha256
        ),
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        source_stream_receipt_sha256=receipt_sha256(stream_payload),
        samples=kernel_samples,
        authority_receipt_sha256=receipt_sha256(kernel_payload),
    )
    return stream, kernel_input, stream_payload, kernel_payload


def _ordered_full_field(
    *,
    topology: MountedFieldTopology,
    language_stream: EvidenceStream,
    language_kernel_input: KernelNativeInputStream,
    nonlanguage_streams: tuple[EvidenceStream, ...],
    nonlanguage_kernel_inputs: tuple[KernelNativeInputStream, ...],
) -> tuple[tuple[EvidenceStream, ...], tuple[KernelNativeInputStream, ...]]:
    all_streams = (*nonlanguage_streams, language_stream)
    all_inputs = (*nonlanguage_kernel_inputs, language_kernel_input)
    if len({value.key for value in all_streams}) != len(all_streams):
        raise ReceiptError("language native replay received a duplicate field stream")
    if len({value.key for value in all_inputs}) != len(all_inputs):
        raise ReceiptError("language native replay received a duplicate kernel input")
    streams = {value.key: value for value in all_streams}
    inputs = {value.key: value for value in all_inputs}
    expected = tuple(value.key for value in topology.ordered_port_fibers)
    if set(streams) != set(expected) or set(inputs) != set(expected):
        raise ReceiptError(
            "language native replay does not cover every and only full-field port"
        )
    return tuple(streams[key] for key in expected), tuple(inputs[key] for key in expected)


def _execute_case(
    *,
    case: NativeReplayCase,
    typed_input: TypedLanguageFrozenKernelInput,
    positions: tuple[tuple[str, int, TypedTrit], ...],
    nonlanguage_streams: tuple[EvidenceStream, ...],
    nonlanguage_kernel_inputs: tuple[KernelNativeInputStream, ...],
    source_time_start: Fraction,
    topology: MountedFieldTopology,
    grid: CausalGrid,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    receipt_registry: ReceiptRegistry,
) -> tuple[TypedLanguageNativeReplayExecution, ReceiptRegistry]:
    language_stream, language_input, stream_payload, kernel_payload = (
        _case_language_transport(
            case=case,
            typed_input=typed_input,
            positions=positions,
        )
    )
    registry = _extend_payloads(receipt_registry, (stream_payload, kernel_payload))
    streams, inputs = _ordered_full_field(
        topology=topology,
        language_stream=language_stream,
        language_kernel_input=language_input,
        nonlanguage_streams=nonlanguage_streams,
        nonlanguage_kernel_inputs=nonlanguage_kernel_inputs,
    )
    preparation = prepare_closed_experience_evidence(
        streams=streams,
        kernel_inputs=inputs,
        source_time_start=source_time_start,
        grid=grid,
        support_domain=support_domain,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        topology=topology,
        receipt_registry=registry,
    )
    if isinstance(preparation, ClosedExperienceProviderUnknown):
        raise ReceiptError(
            "language frozen-kernel replay is unresolved: "
            f"{preparation.missing_authority}"
        )
    if preparation.status is not ProviderStatus.READY:
        raise ReceiptError("language frozen-kernel replay did not become READY")
    registry = _extend_records(registry, preparation.receipt_registry.records)
    target = tuple(
        value for value in preparation.evidence if value.key == language_stream.key
    )
    if not target:
        raise ReceiptError("language frozen kernel emitted no target evidence")
    final = max(
        target,
        key=lambda value: (
            value.provenance.source_timestamp,
            value.provenance.source_index,
        ),
    )
    l4 = ExactL4Response(
        D_k=final.coordinates.D_k,
        M_k=final.coordinates.M_k,
        R_rev_k=final.coordinates.R_rev_k,
        U_star_k=final.coordinates.U_star_k,
        C_k=final.coordinates.C_k,
        P_k=final.coordinates.P_k,
        B_k=final.coordinates.B_k,
    )
    branch_id, cell_id = _actual_branch_and_cell(final.raw_record.payload)
    source_operator_payload = _canonical_bytes(
        {
            "case_receipt_sha256": case.receipt_sha256,
            "language_capture_receipt_sha256": typed_input.capture_receipt_sha256,
            "l0_l4_preparation_receipt_sha256": preparation.receipt_sha256,
            "l0_l4_trace_receipt_sha256": final.raw_record.digest,
            "operator": TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID,
            "schema": "glew.typed_language.native_replay_source.v2",
            "source_stream_receipt_sha256": receipt_sha256(stream_payload),
        }
    )
    registry = _extend_payloads(registry, (source_operator_payload,))
    return (
        TypedLanguageNativeReplayExecution(
            case=case,
            language_stream=language_stream,
            language_kernel_input=language_input,
            preparation=preparation,
            l4_response=l4,
            source_stream_receipt_sha256=receipt_sha256(stream_payload),
            l0_l4_trace_receipt_sha256=final.raw_record.digest,
            branch_id=branch_id,
            cell_id=cell_id,
            source_operator_receipt_sha256=receipt_sha256(source_operator_payload),
        ),
        registry,
    )


def _mount_responses(
    *,
    profile: MountedNativePerturbationProfile,
    cases: tuple[NativeReplayCase, ...],
    executions: tuple[TypedLanguageNativeReplayExecution, ...],
    typed_input: TypedLanguageFrozenKernelInput,
    pre_window_state: MountedPreWindowState,
    provider_id: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedNativeResponseSet, ReceiptRegistry]:
    responses = []
    response_payloads = []
    for execution in executions:
        response_id = f"{execution.case.case_id}:frozen-l0-l4"
        payload = native_l4_replay_response_receipt_payload(
            response_id=response_id,
            lane=L6Lane.LANGUAGE,
            provider_id=provider_id,
            native_port_id=typed_input.stream.port_id,
            case_receipt_sha256=execution.case.receipt_sha256,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=(
                pre_window_state.authority_receipt_sha256
            ),
            branch_id=execution.branch_id,
            cell_id=execution.cell_id,
            l4_response=execution.l4_response,
            source_operator_receipt_sha256=(
                execution.source_operator_receipt_sha256
            ),
        )
        responses.append(
            NativeL4ReplayResponse(
                response_id=response_id,
                lane=L6Lane.LANGUAGE,
                provider_id=provider_id,
                native_port_id=typed_input.stream.port_id,
                case_receipt_sha256=execution.case.receipt_sha256,
                profile_receipt_sha256=profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                branch_id=execution.branch_id,
                cell_id=execution.cell_id,
                l4_response=execution.l4_response,
                source_operator_receipt_sha256=(
                    execution.source_operator_receipt_sha256
                ),
                receipt_sha256=receipt_sha256(payload),
            )
        )
        response_payloads.append(payload)
    registry = _extend_payloads(receipt_registry, response_payloads)
    source_completeness_payload = _canonical_bytes(
        {
            "case_receipt_sha256s": [value.receipt_sha256 for value in cases],
            "execution_preparation_receipt_sha256s": [
                value.preparation.receipt_sha256 for value in executions
            ],
            "language_capture_receipt_sha256": typed_input.capture_receipt_sha256,
            "operator": TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID,
            "profile_receipt_sha256": profile.authority_receipt_sha256,
            "schema": "glew.typed_language.native_response_completeness.v2",
        }
    )
    registry = _extend_payloads(registry, (source_completeness_payload,))
    response_set_id = f"{profile.profile_id}:responses"
    response_set_payload = native_response_set_receipt_payload(
        response_set_id=response_set_id,
        lane=L6Lane.LANGUAGE,
        provider_id=provider_id,
        native_port_id=typed_input.stream.port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        responses=tuple(responses),
        source_completeness_receipt_sha256=receipt_sha256(
            source_completeness_payload
        ),
    )
    response_set = MountedNativeResponseSet(
        response_set_id=response_set_id,
        lane=L6Lane.LANGUAGE,
        provider_id=provider_id,
        native_port_id=typed_input.stream.port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        responses=tuple(responses),
        source_completeness_receipt_sha256=receipt_sha256(
            source_completeness_payload
        ),
        authority_receipt_sha256=receipt_sha256(response_set_payload),
    )
    registry = _extend_payloads(registry, (response_set_payload,))
    response_set.verify(
        profile=profile,
        pre_window_state=pre_window_state,
        expected_cases=cases,
        receipt_registry=registry,
    )
    return response_set, registry


def _mount_contingent_cone(
    *,
    profile: MountedNativePerturbationProfile,
    cases: tuple[NativeReplayCase, ...],
    response_set: MountedNativeResponseSet,
    typed_input: TypedLanguageFrozenKernelInput,
    pre_window_state: MountedPreWindowState,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedTypedLanguageContingentCone, ReceiptRegistry]:
    registry = receipt_registry
    base_response = response_set.responses[0]
    directions = []
    rows = []
    direction_payloads = []
    reversal_payloads = []
    row_payloads = []
    zero_payloads = []
    for case, adjacent_response in zip(
        cases[1:],
        response_set.responses[1:],
        strict=True,
    ):
        if (
            case.kind is not NativeReplayCaseKind.LANGUAGE_TYPED_TRIT
            or case.target_coordinate_id is None
            or case.direction is None
            or case.native_delta == 0
        ):
            raise ReceiptError("language cone received a non-adjacent replay case")
        secant = ExactL4Response(
            *tuple(
                (target - source) / case.native_delta
                for source, target in zip(
                    base_response.l4_response.as_tuple(),
                    adjacent_response.l4_response.as_tuple(),
                    strict=True,
                )
            )
        )
        direction_id = (
            f"typed-language-direction-{case.case_index:04d}-"
            f"{case.direction.name.lower()}"
        )
        reversal_payload = typed_language_reversal_receipt_payload(
            case_receipt_sha256=case.receipt_sha256,
            base_response_receipt_sha256=base_response.receipt_sha256,
            adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
            source_branch_id=base_response.branch_id,
            source_cell_id=base_response.cell_id,
            target_branch_id=adjacent_response.branch_id,
            target_cell_id=adjacent_response.cell_id,
            source_R_rev_k=base_response.l4_response.R_rev_k,
            target_R_rev_k=adjacent_response.l4_response.R_rev_k,
            signed_R_rev_secant=secant.R_rev_k,
        )
        reversal_digest = receipt_sha256(reversal_payload)
        row = None
        row_digest = None
        zero_digest = None
        if any(secant.as_tuple()):
            row_payload = canonical_row_receipt_payload(
                lane=L6Lane.LANGUAGE,
                provider_id=profile.provider_id,
                native_port_id=profile.native_port_id,
                operator_id=TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID,
                row_id=direction_id,
                coefficients=secant.as_tuple(),
            )
            row_digest = receipt_sha256(row_payload)
            row = embed_native_covector(
                NativeConstraintCovector(
                    provenance=ConstraintRowProvenance(
                        lane=L6Lane.LANGUAGE,
                        provider_id=profile.provider_id,
                        native_port_id=profile.native_port_id,
                        operator_id=TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID,
                        receipt_sha256=row_digest,
                        row_id=direction_id,
                    ),
                    coefficients=secant.as_tuple(),
                )
            )
            rows.append(row)
            row_payloads.append(row_payload)
        else:
            zero_payload = typed_language_zero_response_receipt_payload(
                case_receipt_sha256=case.receipt_sha256,
                coordinate_id=case.target_coordinate_id,
                direction=case.direction,
                native_delta=case.native_delta,
                base_response_receipt_sha256=base_response.receipt_sha256,
                adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
                secant=secant,
            )
            zero_digest = receipt_sha256(zero_payload)
            zero_payloads.append(zero_payload)
        direction_payload = typed_language_direction_receipt_payload(
            direction_id=direction_id,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=(
                pre_window_state.authority_receipt_sha256
            ),
            language_capture_receipt_sha256=typed_input.capture_receipt_sha256,
            case_receipt_sha256=case.receipt_sha256,
            coordinate_id=case.target_coordinate_id,
            direction=case.direction,
            native_delta=case.native_delta,
            base_response_receipt_sha256=base_response.receipt_sha256,
            adjacent_response_receipt_sha256=adjacent_response.receipt_sha256,
            source_branch_id=base_response.branch_id,
            source_cell_id=base_response.cell_id,
            target_branch_id=adjacent_response.branch_id,
            target_cell_id=adjacent_response.cell_id,
            secant=secant,
            reversal_receipt_sha256=reversal_digest,
            row_receipt_sha256=row_digest,
            zero_response_receipt_sha256=zero_digest,
        )
        directions.append(
            TypedLanguageContingentDirection(
                direction_id=direction_id,
                case_receipt_sha256=case.receipt_sha256,
                coordinate_id=case.target_coordinate_id,
                direction=case.direction,
                native_delta=case.native_delta,
                base_response_receipt_sha256=base_response.receipt_sha256,
                adjacent_response_receipt_sha256=(
                    adjacent_response.receipt_sha256
                ),
                source_branch_id=base_response.branch_id,
                source_cell_id=base_response.cell_id,
                target_branch_id=adjacent_response.branch_id,
                target_cell_id=adjacent_response.cell_id,
                secant=secant,
                reversal_receipt_sha256=reversal_digest,
                row=row,
                zero_response_receipt_sha256=zero_digest,
                authority_receipt_sha256=receipt_sha256(direction_payload),
            )
        )
        reversal_payloads.append(reversal_payload)
        direction_payloads.append(direction_payload)
    registry = _extend_payloads(
        registry,
        (*reversal_payloads, *row_payloads, *zero_payloads, *direction_payloads),
    )
    fixed42_stack = Fixed42ConstraintStack(tuple(rows))
    rank = exact_rank_receipt(fixed42_stack)
    row_digests = tuple(value.provenance.receipt_sha256 for value in rows)
    row_completeness_payload = canonical_completeness_receipt_payload(
        lane=L6Lane.LANGUAGE,
        row_receipt_sha256s=row_digests,
    )
    zero_digests = tuple(
        value.zero_response_receipt_sha256
        for value in directions
        if value.zero_response_receipt_sha256 is not None
    )
    direction_completeness_payload = (
        typed_language_cone_completeness_receipt_payload(
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=(
                pre_window_state.authority_receipt_sha256
            ),
            language_capture_receipt_sha256=typed_input.capture_receipt_sha256,
            base_case_receipt_sha256=cases[0].receipt_sha256,
            base_response_receipt_sha256=base_response.receipt_sha256,
            adjacent_case_receipt_sha256s=tuple(
                value.receipt_sha256 for value in cases[1:]
            ),
            direction_receipt_sha256s=tuple(
                value.authority_receipt_sha256 for value in directions
            ),
            reversal_receipt_sha256s=tuple(
                value.reversal_receipt_sha256 for value in directions
            ),
            row_receipt_sha256s=row_digests,
            zero_response_receipt_sha256s=zero_digests,
        )
    )
    rank_payload = typed_language_exact_rank_receipt_payload(
        row_completeness_receipt_sha256=receipt_sha256(
            row_completeness_payload
        ),
        rank_receipt=rank,
    )
    cone_payload = typed_language_contingent_cone_receipt_payload(
        provider_id=profile.provider_id,
        native_port_id=profile.native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        language_capture_receipt_sha256=typed_input.capture_receipt_sha256,
        response_set_receipt_sha256=response_set.authority_receipt_sha256,
        direction_completeness_receipt_sha256=receipt_sha256(
            direction_completeness_payload
        ),
        row_completeness_receipt_sha256=receipt_sha256(
            row_completeness_payload
        ),
        rank_receipt_sha256=receipt_sha256(rank_payload),
    )
    registry = _extend_payloads(
        registry,
        (
            row_completeness_payload,
            direction_completeness_payload,
            rank_payload,
            cone_payload,
        ),
    )
    cone = MountedTypedLanguageContingentCone(
        provider_id=profile.provider_id,
        native_port_id=profile.native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        language_capture_receipt_sha256=typed_input.capture_receipt_sha256,
        response_set_receipt_sha256=response_set.authority_receipt_sha256,
        directions=tuple(directions),
        fixed42_stack=fixed42_stack,
        rank_receipt=rank,
        direction_completeness_receipt_sha256=receipt_sha256(
            direction_completeness_payload
        ),
        row_completeness_receipt_sha256=receipt_sha256(
            row_completeness_payload
        ),
        rank_receipt_sha256=receipt_sha256(rank_payload),
        authority_receipt_sha256=receipt_sha256(cone_payload),
    )
    cone.verify(
        profile=profile,
        pre_window_state=pre_window_state,
        cases=cases,
        response_set=response_set,
        receipt_registry=registry,
    )
    return cone, registry


def execute_typed_language_native_replay(
    *,
    provider_id: str,
    typed_input: TypedLanguageFrozenKernelInput,
    pre_window_state: MountedPreWindowState,
    nonlanguage_streams: tuple[EvidenceStream, ...],
    nonlanguage_kernel_inputs: tuple[KernelNativeInputStream, ...],
    source_time_start: Fraction,
    topology: MountedFieldTopology,
    grid: CausalGrid,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    receipt_registry: ReceiptRegistry,
) -> TypedLanguageNativeReplayResult:
    """Replay every typed adjacency and mount the complete language cone."""

    typed_input.verify()
    registry = _extend_records(receipt_registry, typed_input.receipt_registry.records)
    topology.verify(registry)
    pre_window_state.verify(registry)
    profile, cases, positions, registry = _language_profile(
        typed_input=typed_input,
        pre_window_state=pre_window_state,
        provider_id=provider_id,
        receipt_registry=registry,
    )
    executions = []
    for case in cases:
        execution, generated = _execute_case(
            case=case,
            typed_input=typed_input,
            positions=positions,
            nonlanguage_streams=nonlanguage_streams,
            nonlanguage_kernel_inputs=nonlanguage_kernel_inputs,
            source_time_start=source_time_start,
            topology=topology,
            grid=grid,
            support_domain=support_domain,
            resonance_graph=resonance_graph,
            resonance_operator=resonance_operator,
            receipt_registry=registry,
        )
        registry = _extend_records(registry, generated.records)
        executions.append(execution)
    mounted_executions = tuple(executions)
    response_set, registry = _mount_responses(
        profile=profile,
        cases=cases,
        executions=mounted_executions,
        typed_input=typed_input,
        pre_window_state=pre_window_state,
        provider_id=provider_id,
        receipt_registry=registry,
    )
    cone, registry = _mount_contingent_cone(
        profile=profile,
        cases=cases,
        response_set=response_set,
        typed_input=typed_input,
        pre_window_state=pre_window_state,
        receipt_registry=registry,
    )
    return TypedLanguageNativeReplayResult(
        bundle=NativePortReplayBundle(profile, response_set, None),
        executions=mounted_executions,
        contingent_cone=cone,
        receipt_registry=registry,
    )


__all__ = (
    "MountedTypedLanguageContingentCone",
    "TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID",
    "TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID",
    "TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID",
    "TypedLanguageContingentDirection",
    "TypedLanguageNativeReplayExecution",
    "TypedLanguageNativeReplayResult",
    "execute_typed_language_native_replay",
    "typed_language_cone_completeness_receipt_payload",
    "typed_language_contingent_cone_receipt_payload",
    "typed_language_direction_receipt_payload",
    "typed_language_exact_rank_receipt_payload",
    "typed_language_reversal_receipt_payload",
    "typed_language_zero_response_receipt_payload",
)
