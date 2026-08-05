"""Bounded exact Negative Space recovery state for the whole organism.

This owner does not invent a recovery drive, score, threshold, label, or
cognitive form.  It admits one already-authenticated causal settlement,
semantically verifies every explicit DSF field root, authenticates the current
physical internal-body state through its owning authority, and reads the
actual native L1 ``N_gate`` coordinates retained by evidence custody.

The canonical substrate condition is exact: recovery is perturbed only when
every actual native L1 closure in the settlement has ``N_gate == 1``.
Anything else leaves this permanently mounted mechanism at its authenticated
uncommitted zero.  The condition is the existing Negative Space physics, not
a developer-selected cutoff.

Only the latest observation is retained.  Prepare/commit/rollback and the
HMAC-authenticated cold envelope are exact, while state size is permanently
bounded.  L0--L4 is read and verified but never modified or projected.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceTransitionIndex,
)
from dsf_ai_service.substrate.physical_internal_body_state import (
    PhysicalInternalBodyState,
    PhysicalInternalBodyStateAuthority,
)


PROFILE_SCHEMA = "guala.whole_organism.recovery.profile.v1"
STATE_SCHEMA = "guala.whole_organism.recovery.state.v1"
COLD_SCHEMA = "guala.whole_organism.recovery.cold.v1"

QUIESCENT_SEMANTICS = "mounted-uncommitted-zero"
NEGATIVE_SPACE_RULE = (
    "every_actual_native_L1_closure_has_exact_N_gate=1"
)

_PROFILE_DOMAIN = b"guala-whole-organism-recovery-profile-v1\0"
_STATE_DOMAIN = b"guala-whole-organism-recovery-state-v1\0"
_COLD_DOMAIN = b"guala-whole-organism-recovery-cold-v1\0"
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")

MAX_STATE_BYTES = 16 * 1024 * 1024
MAX_SEQUENCE = (1 << 63) - 1


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(
            "whole-organism recovery state is not deterministic JSON"
        ) from error


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("whole-organism recovery authority key is invalid")
    return raw


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("whole-organism recovery coordinate is not exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


def _root_receipt(root: FullFieldSensoryRoot) -> str:
    root.verify()
    return _digest(root.record())


def _verify_explicit_full_field(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> tuple[str, ...]:
    if not roots:
        raise ValueError(
            "whole-organism recovery requires an observed full field"
        )
    receipts = []
    for root in roots:
        root.verify()
        receipts.append(_root_receipt(root))
    result = tuple(receipts)
    if len(set(result)) != len(result):
        raise ValueError(
            "whole-organism recovery repeats a full-field root"
        )
    return result


class RecoveryMomentState(str, Enum):
    PERTURBED = "perturbed"
    QUIESCENT = "quiescent"


@dataclass(frozen=True, slots=True)
class WholeOrganismRecoveryProfile:
    physical_body_manifest_receipt_sha256: str
    max_state_bytes: int
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "max_state_bytes": self.max_state_bytes,
            "physical_body_manifest_receipt_sha256": (
                self.physical_body_manifest_receipt_sha256
            ),
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        _sha(
            self.physical_body_manifest_receipt_sha256,
            "recovery physical-body manifest",
        )
        if (
            isinstance(self.max_state_bytes, bool)
            or not isinstance(self.max_state_bytes, int)
            or not 1 <= self.max_state_bytes <= MAX_STATE_BYTES
        ):
            raise ValueError(
                "whole-organism recovery state capacity is invalid"
            )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError(
                "whole-organism recovery profile authority changed"
            )


@dataclass(frozen=True, slots=True)
class WholeOrganismRecoveryState:
    profile_receipt_sha256: str
    sequence: int
    recovery_count: int
    moment_state: RecoveryMomentState
    source_time_start: Fraction | None
    source_time_end: Fraction | None
    settlement_authority_receipt_sha256: str | None
    physical_body_state: PhysicalInternalBodyState
    full_field_root_receipt_sha256s: tuple[str, ...]
    native_evidence_transition: NativeEvidenceTransitionIndex | None
    l1_n_gate_coordinates: tuple[Fraction, ...]
    prior_state_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def is_recovery(self) -> bool:
        return self.moment_state is RecoveryMomentState.PERTURBED

    def payload(self) -> dict[str, object]:
        return {
            "full_field_root_receipt_sha256s": list(
                self.full_field_root_receipt_sha256s
            ),
            "l1_n_gate_coordinates": [
                _fraction_text(value)
                for value in self.l1_n_gate_coordinates
            ],
            "moment_state": self.moment_state.value,
            "native_evidence_transition": (
                None
                if self.native_evidence_transition is None
                else self.native_evidence_transition.record()
            ),
            "negative_space_rule": NEGATIVE_SPACE_RULE,
            "physical_body_state": self.physical_body_state.record(),
            "prior_state_receipt_sha256": (
                self.prior_state_receipt_sha256
            ),
            "profile_receipt_sha256": self.profile_receipt_sha256,
            "quiescent_semantics": QUIESCENT_SEMANTICS,
            "recovery_count": self.recovery_count,
            "schema": STATE_SCHEMA,
            "sequence": self.sequence,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "source_time_end": (
                None
                if self.source_time_end is None
                else _fraction_text(self.source_time_end)
            ),
            "source_time_start": (
                None
                if self.source_time_start is None
                else _fraction_text(self.source_time_start)
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _PreparedPhase:
    value: str


@dataclass(frozen=True, slots=True)
class PreparedRecoveryObservation:
    before: WholeOrganismRecoveryState
    after: WholeOrganismRecoveryState
    _phase: _PreparedPhase = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class RecoveryObservationUndo:
    _prepared: PreparedRecoveryObservation = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class ExactWholeOrganismRecoveryOwner:
    """Own one bounded authenticated recovery/quiescence state."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        physical_body_authority: PhysicalInternalBodyStateAuthority,
        max_state_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        raw_key = _key(authority_key)
        if not isinstance(
            physical_body_authority,
            PhysicalInternalBodyStateAuthority,
        ):
            raise TypeError(
                "whole-organism recovery requires the physical-body owner"
            )
        self._body_authority = physical_body_authority
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + raw_key
        ).digest()
        self._cold_key = hashlib.sha256(
            _COLD_DOMAIN + raw_key
        ).digest()
        self._lock = threading.RLock()
        self._owner_authority = object()
        provisional_profile = WholeOrganismRecoveryProfile(
            physical_body_manifest_receipt_sha256=(
                physical_body_authority.manifest
                .authority_receipt_sha256
            ),
            max_state_bytes=max_state_bytes,
            authority_receipt_sha256="0" * 64,
        )
        self._profile = WholeOrganismRecoveryProfile(
            physical_body_manifest_receipt_sha256=(
                provisional_profile
                .physical_body_manifest_receipt_sha256
            ),
            max_state_bytes=provisional_profile.max_state_bytes,
            authority_receipt_sha256=_digest(
                provisional_profile.payload()
            ),
        )
        self._profile.verify()
        body_state = self._authenticated_current_body_state()
        self._state = self._build_state(
            sequence=0,
            recovery_count=0,
            moment_state=RecoveryMomentState.QUIESCENT,
            source_time_start=None,
            source_time_end=None,
            settlement_authority_receipt_sha256=None,
            physical_body_state=body_state,
            full_field_root_receipt_sha256s=(),
            native_evidence_transition=None,
            l1_n_gate_coordinates=(),
            prior_state_receipt_sha256=None,
        )
        self.snapshot_encoded()

    @property
    def profile(self) -> WholeOrganismRecoveryProfile:
        return self._profile

    @property
    def state(self) -> WholeOrganismRecoveryState:
        with self._lock:
            return self._state

    def _authenticated_current_body_state(
        self,
    ) -> PhysicalInternalBodyState:
        state = self._body_authority.state
        self._body_authority._verify_state(state)
        if (
            state.manifest_receipt_sha256
            != self._profile.physical_body_manifest_receipt_sha256
        ):
            raise ValueError(
                "whole-organism recovery crossed physical-body anatomy"
            )
        return state

    def _build_state(
        self,
        *,
        sequence: int,
        recovery_count: int,
        moment_state: RecoveryMomentState,
        source_time_start: Fraction | None,
        source_time_end: Fraction | None,
        settlement_authority_receipt_sha256: str | None,
        physical_body_state: PhysicalInternalBodyState,
        full_field_root_receipt_sha256s: tuple[str, ...],
        native_evidence_transition: NativeEvidenceTransitionIndex | None,
        l1_n_gate_coordinates: tuple[Fraction, ...],
        prior_state_receipt_sha256: str | None,
    ) -> WholeOrganismRecoveryState:
        provisional = WholeOrganismRecoveryState(
            profile_receipt_sha256=(
                self._profile.authority_receipt_sha256
            ),
            sequence=sequence,
            recovery_count=recovery_count,
            moment_state=moment_state,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            settlement_authority_receipt_sha256=(
                settlement_authority_receipt_sha256
            ),
            physical_body_state=physical_body_state,
            full_field_root_receipt_sha256s=(
                full_field_root_receipt_sha256s
            ),
            native_evidence_transition=native_evidence_transition,
            l1_n_gate_coordinates=l1_n_gate_coordinates,
            prior_state_receipt_sha256=prior_state_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = WholeOrganismRecoveryState(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_state(result)
        return result

    def _verify_state(
        self,
        state: WholeOrganismRecoveryState,
    ) -> None:
        if not isinstance(state, WholeOrganismRecoveryState):
            raise TypeError(
                "whole-organism recovery state is not typed"
            )
        if (
            state.profile_receipt_sha256
            != self._profile.authority_receipt_sha256
        ):
            raise ValueError(
                "whole-organism recovery state changed profile"
            )
        if (
            isinstance(state.sequence, bool)
            or not isinstance(state.sequence, int)
            or not 0 <= state.sequence <= MAX_SEQUENCE
            or isinstance(state.recovery_count, bool)
            or not isinstance(state.recovery_count, int)
            or not 0 <= state.recovery_count <= state.sequence
        ):
            raise ValueError(
                "whole-organism recovery state extent changed"
            )
        if not isinstance(state.moment_state, RecoveryMomentState):
            raise TypeError(
                "whole-organism recovery moment is not typed"
            )
        self._body_authority._verify_state(
            state.physical_body_state
        )
        if (
            state.physical_body_state.manifest_receipt_sha256
            != self._profile.physical_body_manifest_receipt_sha256
        ):
            raise ValueError(
                "whole-organism recovery body manifest changed"
            )
        if state.prior_state_receipt_sha256 is not None:
            _sha(
                state.prior_state_receipt_sha256,
                "whole-organism recovery prior state",
            )
        if state.sequence == 0:
            if (
                state.recovery_count != 0
                or state.moment_state is not RecoveryMomentState.QUIESCENT
                or state.source_time_start is not None
                or state.source_time_end is not None
                or state.settlement_authority_receipt_sha256 is not None
                or state.full_field_root_receipt_sha256s
                or state.native_evidence_transition is not None
                or state.l1_n_gate_coordinates
                or state.prior_state_receipt_sha256 is not None
            ):
                raise ValueError(
                    "whole-organism recovery genesis is not quiescent"
                )
        else:
            if (
                not isinstance(state.source_time_start, Fraction)
                or not isinstance(state.source_time_end, Fraction)
                or state.source_time_end <= state.source_time_start
            ):
                raise ValueError(
                    "whole-organism recovery interval changed"
                )
            _sha(
                state.settlement_authority_receipt_sha256,
                "whole-organism recovery settlement",
            )
            if (
                state.physical_body_state.source_time
                > state.source_time_end
            ):
                raise ValueError(
                    "whole-organism recovery body state is from the future"
                )
            if (
                not state.full_field_root_receipt_sha256s
                or len(set(state.full_field_root_receipt_sha256s))
                != len(state.full_field_root_receipt_sha256s)
            ):
                raise ValueError(
                    "whole-organism recovery full-field roots changed"
                )
            for receipt in state.full_field_root_receipt_sha256s:
                _sha(receipt, "whole-organism recovery full-field root")
            if not isinstance(
                state.native_evidence_transition,
                NativeEvidenceTransitionIndex,
            ):
                raise TypeError(
                    "whole-organism recovery native evidence is not typed"
                )
            state.native_evidence_transition.verify()
            actual_coordinates = tuple(
                Fraction(value)
                for port in state.native_evidence_transition.ports
                for value in port.n_gates
            )
            if (
                not actual_coordinates
                or state.l1_n_gate_coordinates != actual_coordinates
            ):
                raise ValueError(
                    "whole-organism recovery N_gate evidence changed"
                )
            if state.moment_state is RecoveryMomentState.PERTURBED:
                if any(value != Fraction(1) for value in actual_coordinates):
                    raise ValueError(
                        "whole-organism recovery claimed non-Negative Space"
                    )
            elif all(
                value == Fraction(1) for value in actual_coordinates
            ):
                raise ValueError(
                    "whole-organism recovery suppressed exact Negative Space"
                )
        expected_hmac = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(state.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                state.authority_hmac_sha256,
                expected_hmac,
            )
            or state.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": state.payload(),
            })
        ):
            raise ValueError(
                "whole-organism recovery state authority changed"
            )

    def prepare_observation(
        self,
        settlement: CausalExperienceSettlement,
    ) -> PreparedRecoveryObservation:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "whole-organism recovery requires a causal settlement"
            )
        settlement.verify()
        roots = full_field_sensory_roots(settlement)
        root_receipts = _verify_explicit_full_field(roots)
        transition = (
            settlement.native_evidence_witness.transition_index()
        )
        transition.verify()
        coordinates = tuple(
            Fraction(value)
            for port in transition.ports
            for value in port.n_gates
        )
        if not coordinates:
            raise ValueError(
                "whole-organism recovery lacks actual L1 N_gate evidence"
            )
        moment_state = (
            RecoveryMomentState.PERTURBED
            if all(value == Fraction(1) for value in coordinates)
            else RecoveryMomentState.QUIESCENT
        )
        body_state = self._authenticated_current_body_state()
        with self._lock:
            before = self._state
            if before.sequence >= MAX_SEQUENCE:
                raise RuntimeError(
                    "whole-organism recovery sequence capacity exhausted"
                )
            after = self._build_state(
                sequence=before.sequence + 1,
                recovery_count=(
                    before.recovery_count
                    + (
                        1
                        if moment_state is RecoveryMomentState.PERTURBED
                        else 0
                    )
                ),
                moment_state=moment_state,
                source_time_start=settlement.source_time_start,
                source_time_end=settlement.source_time_end,
                settlement_authority_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                physical_body_state=body_state,
                full_field_root_receipt_sha256s=root_receipts,
                native_evidence_transition=transition,
                l1_n_gate_coordinates=coordinates,
                prior_state_receipt_sha256=(
                    before.authority_receipt_sha256
                ),
            )
            prepared = PreparedRecoveryObservation(
                before=before,
                after=after,
                _phase=_PreparedPhase("prepared"),
                _owner_authority=self._owner_authority,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            self._verify_prepared(prepared, phase="prepared")
            return prepared

    def _verify_prepared(
        self,
        prepared: PreparedRecoveryObservation,
        *,
        phase: str,
    ) -> None:
        if (
            not isinstance(prepared, PreparedRecoveryObservation)
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or prepared._phase.value != phase
        ):
            raise ValueError(
                "whole-organism recovery prepared authority changed"
            )
        self._verify_state(prepared.before)
        self._verify_state(prepared.after)
        if (
            prepared.after.sequence != prepared.before.sequence + 1
            or prepared.after.prior_state_receipt_sha256
            != prepared.before.authority_receipt_sha256
            or prepared.after.recovery_count
            != prepared.before.recovery_count
            + (
                1
                if prepared.after.moment_state
                is RecoveryMomentState.PERTURBED
                else 0
            )
        ):
            raise ValueError(
                "whole-organism recovery prepared lineage changed"
            )

    def commit_prepared(
        self,
        prepared: PreparedRecoveryObservation,
    ) -> RecoveryObservationUndo:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            if self._state != prepared.before:
                raise ValueError(
                    "whole-organism recovery observation is stale"
                )
            current_body = self._authenticated_current_body_state()
            if (
                current_body.authority_receipt_sha256
                != prepared.after.physical_body_state
                .authority_receipt_sha256
            ):
                raise ValueError(
                    "physical body changed during recovery admission"
                )
            self._state = prepared.after
            try:
                self.snapshot_encoded()
            except BaseException:
                self._state = prepared.before
                raise
            prepared._phase.value = "committed"
            return RecoveryObservationUndo(
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedRecoveryObservation,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            prepared._phase.value = "discarded"

    def rollback_committed(
        self,
        undo: RecoveryObservationUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(undo, RecoveryObservationUndo)
                or undo._construction_authority is not _UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
            ):
                raise ValueError(
                    "whole-organism recovery rollback authority changed"
                )
            prepared = undo._prepared
            self._verify_prepared(prepared, phase="committed")
            if self._state != prepared.after:
                raise ValueError(
                    "whole-organism recovery rollback is not the live tail"
                )
            self._state = prepared.before
            prepared._phase.value = "rolled_back"
            self.snapshot_encoded()

    def _encoded(self, state: WholeOrganismRecoveryState) -> bytes:
        self._verify_state(state)
        body = {
            "profile": self._profile.record(),
            "schema": COLD_SCHEMA,
            "state": state.record(),
        }
        encoded = _canonical({
            "body": body,
            "cold_hmac_sha256": hmac.new(
                self._cold_key,
                _COLD_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
            "schema": COLD_SCHEMA,
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "whole-organism recovery cold state exceeds capacity"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._state)

    @staticmethod
    def _state_from_record(
        value: object,
    ) -> WholeOrganismRecoveryState:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "full_field_root_receipt_sha256s",
            "l1_n_gate_coordinates",
            "moment_state",
            "native_evidence_transition",
            "negative_space_rule",
            "physical_body_state",
            "prior_state_receipt_sha256",
            "profile_receipt_sha256",
            "quiescent_semantics",
            "recovery_count",
            "schema",
            "sequence",
            "settlement_authority_receipt_sha256",
            "source_time_end",
            "source_time_start",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != STATE_SCHEMA
            or value.get("negative_space_rule")
            != NEGATIVE_SPACE_RULE
            or value.get("quiescent_semantics")
            != QUIESCENT_SEMANTICS
            or not isinstance(
                value.get("full_field_root_receipt_sha256s"),
                list,
            )
            or not isinstance(
                value.get("l1_n_gate_coordinates"),
                list,
            )
        ):
            raise ValueError(
                "whole-organism recovery cold state changed"
            )
        body_state = (
            PhysicalInternalBodyStateAuthority._state_from_record(
                value["physical_body_state"]
            )
        )
        raw_transition = value["native_evidence_transition"]
        transition = (
            None
            if raw_transition is None
            else NativeEvidenceTransitionIndex.from_record(
                raw_transition
            )
        )
        try:
            moment_state = RecoveryMomentState(value["moment_state"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "whole-organism recovery cold moment is not typed"
            ) from error
        return WholeOrganismRecoveryState(
            profile_receipt_sha256=value["profile_receipt_sha256"],
            sequence=value["sequence"],
            recovery_count=value["recovery_count"],
            moment_state=moment_state,
            source_time_start=(
                None
                if value["source_time_start"] is None
                else _fraction_from_text(
                    value["source_time_start"],
                    "whole-organism recovery cold start",
                )
            ),
            source_time_end=(
                None
                if value["source_time_end"] is None
                else _fraction_from_text(
                    value["source_time_end"],
                    "whole-organism recovery cold end",
                )
            ),
            settlement_authority_receipt_sha256=(
                value["settlement_authority_receipt_sha256"]
            ),
            physical_body_state=body_state,
            full_field_root_receipt_sha256s=tuple(
                value["full_field_root_receipt_sha256s"]
            ),
            native_evidence_transition=transition,
            l1_n_gate_coordinates=tuple(
                _fraction_from_text(
                    item,
                    "whole-organism recovery cold N_gate",
                )
                for item in value["l1_n_gate_coordinates"]
            ),
            prior_state_receipt_sha256=(
                value["prior_state_receipt_sha256"]
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value[
                "authority_receipt_sha256"
            ],
        )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        physical_body_authority: PhysicalInternalBodyStateAuthority,
        encoded: bytes,
    ) -> "ExactWholeOrganismRecoveryOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError(
                "whole-organism recovery cold state is absent"
            )
        if len(encoded) > MAX_STATE_BYTES:
            raise ValueError(
                "whole-organism recovery cold state exceeds capacity"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "whole-organism recovery cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {
                "body",
                "cold_hmac_sha256",
                "schema",
            }
            or envelope["schema"] != COLD_SCHEMA
            or not isinstance(envelope["body"], Mapping)
        ):
            raise ValueError(
                "whole-organism recovery cold envelope changed"
            )
        body = envelope["body"]
        if (
            set(body) != {"profile", "schema", "state"}
            or body["schema"] != COLD_SCHEMA
            or not isinstance(body["profile"], Mapping)
        ):
            raise ValueError(
                "whole-organism recovery cold body changed"
            )
        profile_record = body["profile"]
        if set(profile_record) != {
            "authority_receipt_sha256",
            "max_state_bytes",
            "physical_body_manifest_receipt_sha256",
            "schema",
        } or profile_record.get("schema") != PROFILE_SCHEMA:
            raise ValueError(
                "whole-organism recovery cold profile changed"
            )
        raw_key = _key(authority_key)
        cold_key = hashlib.sha256(
            _COLD_DOMAIN + raw_key
        ).digest()
        expected_hmac = hmac.new(
            cold_key,
            _COLD_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope["cold_hmac_sha256"],
            expected_hmac,
        ):
            raise ValueError(
                "whole-organism recovery cold authentication failed"
            )
        result = cls(
            authority_key=raw_key,
            physical_body_authority=physical_body_authority,
            max_state_bytes=profile_record["max_state_bytes"],
        )
        if result.profile.record() != dict(profile_record):
            raise ValueError(
                "whole-organism recovery cold profile crossed anatomy"
            )
        state = cls._state_from_record(body["state"])
        result._verify_state(state)
        current_body = result._authenticated_current_body_state()
        if (
            state.physical_body_state.authority_receipt_sha256
            != current_body.authority_receipt_sha256
        ):
            raise ValueError(
                "whole-organism recovery cold body continuity changed"
            )
        result._state = state
        if result.snapshot_encoded() != encoded:
            raise ValueError(
                "whole-organism recovery cold state is not canonical"
            )
        return result

    def status(self) -> dict[str, object]:
        with self._lock:
            state = self._state
            return {
                "authority_receipt_sha256": (
                    state.authority_receipt_sha256
                ),
                "cold_restorable": True,
                "full_field_root_count": len(
                    state.full_field_root_receipt_sha256s
                ),
                "l1_n_gate_coordinate_count": len(
                    state.l1_n_gate_coordinates
                ),
                "moment_state": state.moment_state.value,
                "negative_space_rule": NEGATIVE_SPACE_RULE,
                "physical_body_manifest_receipt_sha256": (
                    self._profile
                    .physical_body_manifest_receipt_sha256
                ),
                "quiescent_semantics": QUIESCENT_SEMANTICS,
                "recovery_count": state.recovery_count,
                "schema": "guala.whole_organism.recovery.status.v1",
                "sequence": state.sequence,
            }


__all__ = [
    "COLD_SCHEMA",
    "ExactWholeOrganismRecoveryOwner",
    "NEGATIVE_SPACE_RULE",
    "PreparedRecoveryObservation",
    "PROFILE_SCHEMA",
    "QUIESCENT_SEMANTICS",
    "RecoveryMomentState",
    "RecoveryObservationUndo",
    "STATE_SCHEMA",
    "WholeOrganismRecoveryProfile",
    "WholeOrganismRecoveryState",
]
