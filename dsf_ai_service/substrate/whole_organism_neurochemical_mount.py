"""Atomic whole-organism mount for certified conservative chemical flow.

This owner binds one exact causal settlement, the current authenticated body,
and the current authenticated recovery state to already-authorized
neurochemical upstream receipts.  It delegates all movement and conservation
to :mod:`neurochemical_flow`; it derives no chemical amount, rate, semantic
role, reward, mood, or salience.

The mounted subset deliberately refuses first-order conversions.  Unsupported
kinetics remain explicit unavailable reaction records inside this owner while
certified drift, diffusion, clearance, and upstream-authorized impulse
transport remain operational.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction

from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.neurochemical_flow import (
    EvolutionStatus,
    NeurochemicalFlowFieldAuthority,
    NeurochemicalFlowManifest,
    NeurochemicalFlowState,
    NeurochemicalFlowTransition,
)
from dsf_ai_service.substrate.neurochemical_upstream_receipt import (
    UpstreamNeurochemicalReceipt,
)
from dsf_ai_service.substrate.physical_internal_body_state import (
    PhysicalInternalBodyStateAuthority,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    ExactWholeOrganismRecoveryOwner,
)


PROFILE_SCHEMA = "guala.whole_organism.neurochemical_mount.profile.v1"
UNAVAILABLE_SCHEMA = (
    "guala.whole_organism.neurochemical_mount.unavailable_reaction.v1"
)
BOUNDARY_SCHEMA = "guala.whole_organism.neurochemical_mount.boundary.v1"
PREPARED_SCHEMA = "guala.whole_organism.neurochemical_mount.prepared.v1"
STATE_SCHEMA = "guala.whole_organism.neurochemical_mount.state.v1"
ENVELOPE_SCHEMA = "guala.whole_organism.neurochemical_mount.state_hmac.v1"

_BOUNDARY_DOMAIN = b"guala-whole-organism-neurochemical-boundary-v1\0"
_PREPARED_DOMAIN = b"guala-whole-organism-neurochemical-prepared-v1\0"
_STATE_DOMAIN = b"guala-whole-organism-neurochemical-state-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str, label: str) -> bytes:
    raw = value.encode() if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(f"{label} key changed")
    return hashlib.sha256(label.encode() + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode()) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class WholeOrganismNeurochemicalMountProfile:
    profile_id: str
    max_upstream_receipts_per_boundary: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_upstream_receipts_per_boundary: int,
        max_state_bytes: int,
    ) -> "WholeOrganismNeurochemicalMountProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "chemical mount profile id"),
            max_upstream_receipts_per_boundary=_positive(
                max_upstream_receipts_per_boundary,
                "chemical upstream receipt capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes, "chemical mount state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_upstream_receipts_per_boundary=(
                provisional.max_upstream_receipts_per_boundary
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_state_bytes": self.max_state_bytes,
            "max_upstream_receipts_per_boundary": (
                self.max_upstream_receipts_per_boundary
            ),
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "chemical mount profile id")
        _positive(
            self.max_upstream_receipts_per_boundary,
            "chemical upstream receipt capacity",
        )
        _positive(self.max_state_bytes, "chemical mount state capacity")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("chemical mount profile authority changed")


@dataclass(frozen=True, slots=True)
class UnavailableChemicalReaction:
    reaction_id: str
    reason: str
    derivation_evidence_json: str
    derivation_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        reaction_id: str,
        reason: str,
        derivation_evidence: dict[str, object],
    ) -> "UnavailableChemicalReaction":
        evidence = _canonical(derivation_evidence).decode()
        result = cls(
            reaction_id=_identifier(reaction_id, "unavailable reaction id"),
            reason=_identifier(reason, "unavailable reaction reason"),
            derivation_evidence_json=evidence,
            derivation_receipt_sha256=hashlib.sha256(
                evidence.encode()
            ).hexdigest(),
        )
        result.verify()
        return result

    def record(self) -> dict[str, object]:
        return {
            "derivation_evidence_json": self.derivation_evidence_json,
            "derivation_receipt_sha256": self.derivation_receipt_sha256,
            "reaction_id": self.reaction_id,
            "reason": self.reason,
            "schema": UNAVAILABLE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(self.reaction_id, "unavailable reaction id")
        _identifier(self.reason, "unavailable reaction reason")
        try:
            evidence = json.loads(self.derivation_evidence_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "unavailable reaction evidence is unreadable"
            ) from error
        if (
            not isinstance(evidence, dict)
            or _canonical(evidence).decode()
            != self.derivation_evidence_json
            or self.derivation_receipt_sha256
            != hashlib.sha256(
                self.derivation_evidence_json.encode()
            ).hexdigest()
        ):
            raise ValueError("unavailable reaction evidence changed")


@dataclass(frozen=True, slots=True)
class WholeOrganismChemicalBoundary:
    sequence: int
    moment_state: str
    settlement_receipt_sha256: str
    body_state_receipt_sha256: str
    recovery_state_receipt_sha256: str
    flow_event_receipt_sha256: str
    flow_prior_state_receipt_sha256: str
    flow_result_state_receipt_sha256: str
    flow_transition_receipt_sha256: str
    upstream_receipt_records: tuple[dict[str, object], ...]
    unavailable_reactions: tuple[UnavailableChemicalReaction, ...]
    prior_boundary_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "body_state_receipt_sha256": self.body_state_receipt_sha256,
            "flow_event_receipt_sha256": self.flow_event_receipt_sha256,
            "flow_prior_state_receipt_sha256": (
                self.flow_prior_state_receipt_sha256
            ),
            "flow_result_state_receipt_sha256": (
                self.flow_result_state_receipt_sha256
            ),
            "flow_transition_receipt_sha256": (
                self.flow_transition_receipt_sha256
            ),
            "moment_state": self.moment_state,
            "prior_boundary_receipt_sha256": (
                self.prior_boundary_receipt_sha256
            ),
            "recovery_state_receipt_sha256": (
                self.recovery_state_receipt_sha256
            ),
            "schema": BOUNDARY_SCHEMA,
            "sequence": self.sequence,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "unavailable_reactions": [
                value.record() for value in self.unavailable_reactions
            ],
            "upstream_receipt_records": list(
                self.upstream_receipt_records
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedWholeOrganismChemicalBoundary:
    before_flow_encoded: bytes = field(repr=False)
    after_flow_encoded: bytes = field(repr=False)
    prior_boundary: WholeOrganismChemicalBoundary | None
    boundary: WholeOrganismChemicalBoundary
    transition: NeurochemicalFlowTransition
    _staged_flow: NeurochemicalFlowFieldAuthority = field(
        repr=False, compare=False
    )
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "after_flow_sha256": hashlib.sha256(
                self.after_flow_encoded
            ).hexdigest(),
            "before_flow_sha256": hashlib.sha256(
                self.before_flow_encoded
            ).hexdigest(),
            "boundary_receipt_sha256": (
                self.boundary.authority_receipt_sha256
            ),
            "prior_boundary_receipt_sha256": (
                None
                if self.prior_boundary is None
                else self.prior_boundary.authority_receipt_sha256
            ),
            "schema": PREPARED_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismChemicalBoundaryUndo:
    _prepared: PreparedWholeOrganismChemicalBoundary = field(repr=False)


class WholeOrganismNeurochemicalMountOwner:
    """Own the current certified chemical field inside whole-organism custody."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: WholeOrganismNeurochemicalMountProfile,
        flow_authority_key: bytes | str,
        flow_manifest: NeurochemicalFlowManifest,
        body_authority: PhysicalInternalBodyStateAuthority,
        recovery_owner: ExactWholeOrganismRecoveryOwner,
        unavailable_reactions: tuple[UnavailableChemicalReaction, ...],
    ) -> None:
        if not isinstance(profile, WholeOrganismNeurochemicalMountProfile):
            raise TypeError("chemical mount profile is not typed")
        profile.verify()
        if not isinstance(flow_manifest, NeurochemicalFlowManifest):
            raise TypeError("chemical flow manifest is not typed")
        if flow_manifest.conversions:
            raise ValueError(
                "whole-organism chemical mount refuses unspecified conversions"
            )
        if not isinstance(body_authority, PhysicalInternalBodyStateAuthority):
            raise TypeError("chemical mount body authority is not typed")
        if not isinstance(recovery_owner, ExactWholeOrganismRecoveryOwner):
            raise TypeError("chemical mount recovery owner is not typed")
        if (
            getattr(recovery_owner, "_body_authority", None)
            is not body_authority
        ):
            raise ValueError("chemical mount crossed recovery body authority")
        if (
            unavailable_reactions
            != tuple(sorted(
                unavailable_reactions, key=lambda value: value.reaction_id
            ))
            or len({value.reaction_id for value in unavailable_reactions})
            != len(unavailable_reactions)
        ):
            raise ValueError("unavailable reactions are not canonical")
        for value in unavailable_reactions:
            value.verify()
        root = _key(authority_key, "whole organism neurochemical mount")
        self._boundary_key = hashlib.sha256(
            _BOUNDARY_DOMAIN + root
        ).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._flow_key = flow_authority_key
        self._manifest = flow_manifest
        self._body = body_authority
        self._recovery = recovery_owner
        self._unavailable = unavailable_reactions
        self._flow = NeurochemicalFlowFieldAuthority(
            authority_key=flow_authority_key,
            manifest=flow_manifest,
        )
        self._boundary: WholeOrganismChemicalBoundary | None = None
        self._prepared: PreparedWholeOrganismChemicalBoundary | None = None
        self._lock = threading.RLock()
        self.snapshot_encoded()

    @property
    def flow_state(self) -> NeurochemicalFlowState:
        return self._flow.state

    @property
    def boundary(self) -> WholeOrganismChemicalBoundary | None:
        return self._boundary

    @property
    def last_transition(self) -> NeurochemicalFlowTransition | None:
        return self._flow.last_transition

    @staticmethod
    def _is_exact_zero(state: NeurochemicalFlowState) -> bool:
        from fractions import Fraction

        return all(
            isinstance(value, Fraction) and value == 0
            for _component_id, value in state.component_values
        )

    def _seal_boundary(
        self,
        *,
        settlement: CausalExperienceSettlement,
        transition: NeurochemicalFlowTransition,
        result_state: NeurochemicalFlowState,
        upstream_receipts: tuple[UpstreamNeurochemicalReceipt, ...],
    ) -> WholeOrganismChemicalBoundary:
        provisional = WholeOrganismChemicalBoundary(
            sequence=1 if self._boundary is None else self._boundary.sequence + 1,
            moment_state=(
                "quiescent"
                if self._is_exact_zero(result_state)
                else "perturbed"
            ),
            settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            body_state_receipt_sha256=(
                self._body.state.authority_receipt_sha256
            ),
            recovery_state_receipt_sha256=(
                self._recovery.state.authority_receipt_sha256
            ),
            flow_event_receipt_sha256=(
                transition.event.authority_receipt_sha256
            ),
            flow_prior_state_receipt_sha256=(
                transition.prior_state_receipt_sha256
            ),
            flow_result_state_receipt_sha256=result_state.receipt_sha256,
            flow_transition_receipt_sha256=transition.receipt_sha256,
            upstream_receipt_records=tuple(
                value.record()
                for value in (
                    *transition.event.physical_receipts,
                    *transition.event.temporal_receipts,
                )
            ),
            unavailable_reactions=self._unavailable,
            prior_boundary_receipt_sha256=(
                None
                if self._boundary is None
                else self._boundary.authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._boundary_key,
            _BOUNDARY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismChemicalBoundary(
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

    def _verify_boundary(
        self, value: WholeOrganismChemicalBoundary
    ) -> None:
        if not isinstance(value, WholeOrganismChemicalBoundary):
            raise TypeError("chemical boundary is not typed")
        if value.moment_state not in {"perturbed", "quiescent"}:
            raise ValueError("chemical boundary moment state changed")
        for receipt, label in (
            (value.settlement_receipt_sha256, "chemical settlement"),
            (value.body_state_receipt_sha256, "chemical body"),
            (value.recovery_state_receipt_sha256, "chemical recovery"),
            (value.flow_event_receipt_sha256, "chemical flow event"),
            (value.flow_prior_state_receipt_sha256, "chemical prior flow"),
            (value.flow_result_state_receipt_sha256, "chemical result flow"),
            (value.flow_transition_receipt_sha256, "chemical transition"),
        ):
            _sha(receipt, label)
        for unavailable in value.unavailable_reactions:
            unavailable.verify()
        expected = hmac.new(
            self._boundary_key,
            _BOUNDARY_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("chemical boundary authority changed")

    def _verify_boundary_flow(
        self,
        value: WholeOrganismChemicalBoundary,
        flow: NeurochemicalFlowFieldAuthority,
    ) -> None:
        self._verify_boundary(value)
        transition = flow.last_transition
        recovery = self._recovery.state
        if (
            transition is None
            or value.flow_event_receipt_sha256
            != transition.event.authority_receipt_sha256
            or value.flow_prior_state_receipt_sha256
            != transition.prior_state_receipt_sha256
            or value.flow_result_state_receipt_sha256
            != flow.state.receipt_sha256
            or value.flow_transition_receipt_sha256
            != transition.receipt_sha256
            or value.upstream_receipt_records
            != tuple(
                receipt.record()
                for receipt in (
                    *transition.event.physical_receipts,
                    *transition.event.temporal_receipts,
                )
            )
            or value.moment_state
            != (
                "quiescent"
                if self._is_exact_zero(flow.state)
                else "perturbed"
            )
            or value.body_state_receipt_sha256
            != self._body.state.authority_receipt_sha256
            or value.recovery_state_receipt_sha256
            != recovery.authority_receipt_sha256
            or value.settlement_receipt_sha256
            != recovery.settlement_authority_receipt_sha256
            or (
                transition.source_time_end
                - transition.source_time_start
                != recovery.source_time_end - recovery.source_time_start
            )
        ):
            raise ValueError(
                "chemical boundary left certified whole-organism flow"
            )

    def prepare(
        self,
        *,
        settlement: CausalExperienceSettlement,
        upstream_receipts: tuple[UpstreamNeurochemicalReceipt, ...],
        flow_source_time_start: Fraction | None = None,
        flow_source_time_end: Fraction | None = None,
    ) -> PreparedWholeOrganismChemicalBoundary:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("chemical boundary settlement is not typed")
        settlement.verify()
        recovery = self._recovery.state
        body = self._body.state
        if (
            recovery.settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
            or recovery.physical_body_state != body
            or recovery.source_time_start != settlement.source_time_start
            or recovery.source_time_end != settlement.source_time_end
        ):
            raise ValueError(
                "chemical boundary crossed settlement/body/recovery custody"
            )
        chemical_start = (
            settlement.source_time_start
            if flow_source_time_start is None
            else flow_source_time_start
        )
        chemical_end = (
            settlement.source_time_end
            if flow_source_time_end is None
            else flow_source_time_end
        )
        if (
            not isinstance(chemical_start, Fraction)
            or not isinstance(chemical_end, Fraction)
            or chemical_start != self._flow.state.source_time
            or chemical_end <= chemical_start
            or chemical_end - chemical_start
            != settlement.source_time_end - settlement.source_time_start
        ):
            raise ValueError(
                "chemical structural time left exact lived duration"
            )
        if (
            not upstream_receipts
            or len(upstream_receipts)
            > self._profile.max_upstream_receipts_per_boundary
            or any(
                value.source_time_start != chemical_start
                or value.source_time_end != chemical_end
                for value in upstream_receipts
            )
        ):
            raise ValueError("chemical upstream boundary changed extent")
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("chemical boundary is already prepared")
            before = self._flow.snapshot_encoded()
            staged = NeurochemicalFlowFieldAuthority.restore_encoded(
                authority_key=self._flow_key,
                manifest=self._manifest,
                encoded=before,
            )
            event = staged.create_causal_event(
                upstream_receipts=upstream_receipts
            )
            result = staged.evolve(event)
            if (
                result.status is not EvolutionStatus.EVOLVED
                or result.transition is None
            ):
                raise ValueError(
                    f"chemical boundary unresolved: {result.reason}"
                )
            boundary = self._seal_boundary(
                settlement=settlement,
                transition=result.transition,
                result_state=result.state,
                upstream_receipts=upstream_receipts,
            )
            self._verify_boundary(boundary)
            self._verify_boundary_flow(boundary, staged)
            after = staged.snapshot_encoded()
            provisional = PreparedWholeOrganismChemicalBoundary(
                before_flow_encoded=before,
                after_flow_encoded=after,
                prior_boundary=self._boundary,
                boundary=boundary,
                transition=result.transition,
                _staged_flow=staged,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._prepared_key,
                _PREPARED_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = PreparedWholeOrganismChemicalBoundary(
                before_flow_encoded=before,
                after_flow_encoded=after,
                prior_boundary=self._boundary,
                boundary=boundary,
                transition=result.transition,
                _staged_flow=staged,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._encoded(staged, boundary)
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self, value: PreparedWholeOrganismChemicalBoundary
    ) -> None:
        if not isinstance(value, PreparedWholeOrganismChemicalBoundary):
            raise TypeError("prepared chemical boundary is not typed")
        self._verify_boundary_flow(value.boundary, value._staged_flow)
        expected = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
            or value._staged_flow.snapshot_encoded()
            != value.after_flow_encoded
        ):
            raise ValueError("prepared chemical boundary authority changed")

    def commit(
        self, prepared: PreparedWholeOrganismChemicalBoundary
    ) -> WholeOrganismChemicalBoundaryUndo:
        with self._lock:
            self._verify_prepared(prepared)
            if (
                self._prepared != prepared
                or self._boundary != prepared.prior_boundary
                or self._flow.snapshot_encoded()
                != prepared.before_flow_encoded
            ):
                raise ValueError("prepared chemical boundary is not current")
            self._flow = prepared._staged_flow
            self._boundary = prepared.boundary
            self._prepared = None
            return WholeOrganismChemicalBoundaryUndo(prepared)

    def discard(
        self, prepared: PreparedWholeOrganismChemicalBoundary
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared:
                raise ValueError("prepared chemical boundary is not current")
            self._prepared = None

    def rollback(self, undo: WholeOrganismChemicalBoundaryUndo) -> None:
        if not isinstance(undo, WholeOrganismChemicalBoundaryUndo):
            raise TypeError("chemical boundary undo is not typed")
        prepared = undo._prepared
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared is not None:
                raise RuntimeError("chemical boundary mutation is in flight")
            if (
                self._boundary != prepared.boundary
                or self._flow.snapshot_encoded()
                != prepared.after_flow_encoded
            ):
                raise ValueError("committed chemical boundary is not current")
            self._flow = NeurochemicalFlowFieldAuthority.restore_encoded(
                authority_key=self._flow_key,
                manifest=self._manifest,
                encoded=prepared.before_flow_encoded,
            )
            self._boundary = prepared.prior_boundary

    def _body_payload(
        self,
        flow: NeurochemicalFlowFieldAuthority,
        boundary: WholeOrganismChemicalBoundary | None,
    ) -> dict[str, object]:
        return {
            "boundary": None if boundary is None else boundary.record(),
            "flow_state": json.loads(flow.snapshot_encoded()),
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "unavailable_reactions": [
                value.record() for value in self._unavailable
            ],
        }

    def _encoded(
        self,
        flow: NeurochemicalFlowFieldAuthority,
        boundary: WholeOrganismChemicalBoundary | None,
    ) -> bytes:
        body = self._body_payload(flow, boundary)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("chemical mount state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("chemical boundary mutation is in flight")
            return self._encoded(self._flow, self._boundary)

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(self._flow, self._boundary)
            return {
                "mechanism_state": (
                    "quiescent"
                    if self._is_exact_zero(self._flow.state)
                    else "perturbed"
                ),
                "semantic_scalar": None,
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "unsupported_reactions": len(self._unavailable)
                + len(self._manifest.unavailable_nonlinear_mechanisms),
                "schema": (
                    "guala.whole_organism.neurochemical_mount.status.v1"
                ),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: WholeOrganismNeurochemicalMountProfile,
        flow_authority_key: bytes | str,
        flow_manifest: NeurochemicalFlowManifest,
        body_authority: PhysicalInternalBodyStateAuthority,
        recovery_owner: ExactWholeOrganismRecoveryOwner,
        unavailable_reactions: tuple[UnavailableChemicalReaction, ...],
        encoded: bytes,
    ) -> "WholeOrganismNeurochemicalMountOwner":
        try:
            envelope = json.loads(encoded)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("chemical mount cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("chemical mount cold envelope changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            flow_authority_key=flow_authority_key,
            flow_manifest=flow_manifest,
            body_authority=body_authority,
            recovery_owner=recovery_owner,
            unavailable_reactions=unavailable_reactions,
        )
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body)
            != {
                "boundary",
                "flow_state",
                "profile",
                "schema",
                "unavailable_reactions",
            }
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or body.get("unavailable_reactions")
            != [value.record() for value in unavailable_reactions]
        ):
            raise ValueError("chemical mount cold payload changed")
        expected = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected
        ):
            raise ValueError("chemical mount cold authority changed")
        flow_encoded = _canonical(body["flow_state"])
        owner._flow = NeurochemicalFlowFieldAuthority.restore_encoded(
            authority_key=flow_authority_key,
            manifest=flow_manifest,
            encoded=flow_encoded,
        )
        if body["boundary"] is not None:
            owner._boundary = owner._boundary_from_raw(body["boundary"])
            owner._verify_boundary_flow(owner._boundary, owner._flow)
        if owner.snapshot_encoded() != encoded:
            raise ValueError("chemical mount cold round-trip changed bytes")
        return owner

    def _boundary_from_raw(
        self, raw: object
    ) -> WholeOrganismChemicalBoundary:
        expected = set(WholeOrganismChemicalBoundary.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != BOUNDARY_SCHEMA
        ):
            raise ValueError("cold chemical boundary changed")
        unavailable = tuple(
            UnavailableChemicalReaction(
                reaction_id=value["reaction_id"],
                reason=value["reason"],
                derivation_evidence_json=value[
                    "derivation_evidence_json"
                ],
                derivation_receipt_sha256=value[
                    "derivation_receipt_sha256"
                ],
            )
            for value in raw["unavailable_reactions"]
        )
        result = WholeOrganismChemicalBoundary(
            sequence=raw["sequence"],
            moment_state=raw["moment_state"],
            settlement_receipt_sha256=raw[
                "settlement_receipt_sha256"
            ],
            body_state_receipt_sha256=raw[
                "body_state_receipt_sha256"
            ],
            recovery_state_receipt_sha256=raw[
                "recovery_state_receipt_sha256"
            ],
            flow_event_receipt_sha256=raw[
                "flow_event_receipt_sha256"
            ],
            flow_prior_state_receipt_sha256=raw[
                "flow_prior_state_receipt_sha256"
            ],
            flow_result_state_receipt_sha256=raw[
                "flow_result_state_receipt_sha256"
            ],
            flow_transition_receipt_sha256=raw[
                "flow_transition_receipt_sha256"
            ],
            upstream_receipt_records=tuple(
                raw["upstream_receipt_records"]
            ),
            unavailable_reactions=unavailable,
            prior_boundary_receipt_sha256=raw[
                "prior_boundary_receipt_sha256"
            ],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )
        self._verify_boundary(result)
        return result


__all__ = (
    "PreparedWholeOrganismChemicalBoundary",
    "UnavailableChemicalReaction",
    "WholeOrganismChemicalBoundary",
    "WholeOrganismChemicalBoundaryUndo",
    "WholeOrganismNeurochemicalMountOwner",
    "WholeOrganismNeurochemicalMountProfile",
)
