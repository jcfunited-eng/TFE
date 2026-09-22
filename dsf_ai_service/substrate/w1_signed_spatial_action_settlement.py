"""Persistent authenticated W1 spatial action settlement.

Complete dynamic non-auditory L0--L4 roots remain the action authority. Exact
before/after self poses and their signed integer difference are retained beside
the roots as additional causal structure, never as a score, label, bucket, or
replacement for the DSF field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    PoseMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    is_dynamic_grounding_root,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
    W1PhysicalEvidenceReceipt,
)


W1_SIGNED_SPATIAL_ACTION_PROFILE_SCHEMA = (
    "guala.w1.signed_spatial_action.profile.v2"
)
W1_SIGNED_SPATIAL_ACTION_SCHEMA = (
    "guala.w1.signed_spatial_action.v2"
)
W1_SIGNED_SPATIAL_ACTION_STATE_SCHEMA = (
    "guala.w1.signed_spatial_action.state.v1"
)
W1_SIGNED_SPATIAL_ACTION_ENVELOPE_SCHEMA = (
    "guala.w1.signed_spatial_action.envelope.v1"
)
_SETTLEMENT_DOMAIN = b"guala-w1-signed-spatial-action-v2\0"
_STATE_DOMAIN = b"guala-w1-signed-spatial-action-state-v1\0"
_HEX = frozenset("0123456789abcdef")
W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID = "w1-signed-spatial-action"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 spatial settlement key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 spatial settlement key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _self_pose(execution: ActionExecutionReceipt, *, after: bool) -> PoseMM:
    observation = execution.after if after else execution.before
    if observation.self_body_id != execution.actor_body_id:
        raise ValueError("W1 spatial action was not enacted by self")
    matches = tuple(
        body.pose for body in observation.bodies
        if body.body_id == observation.self_body_id
    )
    if len(matches) != 1:
        raise ValueError("W1 spatial action self body is not unique")
    matches[0].verify()
    return matches[0]


@dataclass(frozen=True, slots=True)
class W1SignedSpatialActionResourceProfile:
    profile_id: str
    max_settlements: int
    required_dynamic_root_count: int
    max_settlement_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_settlements: int,
        required_dynamic_root_count: int,
        max_settlement_bytes: int,
        max_state_bytes: int,
    ) -> "W1SignedSpatialActionResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError("W1 spatial profile identifier changed")
        provisional = cls(
            profile_id=profile_id,
            max_settlements=_positive(
                max_settlements, "W1 spatial settlement capacity"
            ),
            required_dynamic_root_count=_positive(
                required_dynamic_root_count,
                "W1 spatial required dynamic-root count",
            ),
            max_settlement_bytes=_positive(
                max_settlement_bytes, "W1 spatial settlement byte capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "W1 spatial state byte capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_settlements=provisional.max_settlements,
            required_dynamic_root_count=(
                provisional.required_dynamic_root_count
            ),
            max_settlement_bytes=provisional.max_settlement_bytes,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_settlement_bytes": self.max_settlement_bytes,
            "max_settlements": self.max_settlements,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "required_dynamic_root_count": (
                self.required_dynamic_root_count
            ),
            "schema": W1_SIGNED_SPATIAL_ACTION_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_settlements, "W1 spatial settlement capacity"),
            (
                self.required_dynamic_root_count,
                "W1 spatial required dynamic-root count",
            ),
            (
                self.max_settlement_bytes,
                "W1 spatial settlement byte capacity",
            ),
            (self.max_state_bytes, "W1 spatial state byte capacity"),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 spatial profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 spatial settlement profile changed")


@dataclass(frozen=True, slots=True)
class W1SignedSpatialActionSettlement:
    settlement_id: str
    execution_receipt_sha256: str
    evidence_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    before_world_state_sha256: str
    after_world_state_sha256: str
    before_revision: int
    after_revision: int
    before_pose: PoseMM
    after_pose: PoseMM
    dx_mm: int
    dy_mm: int
    dz_mm: int
    dyaw_millidegrees: int
    full_dynamic_roots: tuple[GroundingRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def signed_displacement(self) -> tuple[int, int, int, int]:
        return (
            self.dx_mm, self.dy_mm, self.dz_mm, self.dyaw_millidegrees
        )

    def payload(self) -> dict[str, object]:
        return {
            "after_pose": self.after_pose.as_record(),
            "after_revision": self.after_revision,
            "after_world_state_sha256": self.after_world_state_sha256,
            "before_pose": self.before_pose.as_record(),
            "before_revision": self.before_revision,
            "before_world_state_sha256": self.before_world_state_sha256,
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "dyaw_millidegrees": self.dyaw_millidegrees,
            "dz_mm": self.dz_mm,
            "evidence_receipt_sha256": self.evidence_receipt_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "full_dynamic_roots": [
                root.as_record() for root in self.full_dynamic_roots
            ],
            "schema": W1_SIGNED_SPATIAL_ACTION_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "settlement_id": self.settlement_id,
        }


@dataclass(frozen=True, slots=True)
class W1SignedSpatialActionRetainedSource:
    execution: ActionExecutionReceipt
    action_mount: W1PhysicalEvidenceMount


class W1SignedSpatialActionSettlementAuthority:
    """Bounded persistent owner of authenticated full-field spatial outcomes."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1SignedSpatialActionResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
    ) -> None:
        resource_profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 spatial settlement requires world authority")
        if not isinstance(
            physical_authority, W1AudiovisualPhysicalEvidenceAuthority
        ):
            raise TypeError(
                "W1 spatial settlement requires physical evidence authority"
            )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._settlement_key = hashlib.sha256(
            _SETTLEMENT_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._physical = physical_authority
        self._settlements: dict[
            str, W1SignedSpatialActionSettlement
        ] = {}
        self._used_execution_receipts: set[str] = set()
        self._lock = threading.RLock()

    @property
    def settlements(self) -> tuple[W1SignedSpatialActionSettlement, ...]:
        with self._lock:
            return tuple(
                self._settlements[key] for key in sorted(self._settlements)
            )

    def _verify_settlement(
        self, settlement: W1SignedSpatialActionSettlement
    ) -> None:
        for value, name in (
            (settlement.settlement_id, "W1 spatial settlement"),
            (settlement.execution_receipt_sha256, "W1 spatial execution"),
            (settlement.evidence_receipt_sha256, "W1 spatial evidence"),
            (
                settlement.causal_settlement_receipt_sha256,
                "W1 spatial causal settlement",
            ),
            (settlement.before_world_state_sha256, "W1 spatial before world"),
            (settlement.after_world_state_sha256, "W1 spatial after world"),
            (settlement.authority_hmac_sha256, "W1 spatial HMAC"),
            (settlement.authority_receipt_sha256, "W1 spatial authority"),
        ):
            _sha256(value, name)
        settlement.before_pose.verify()
        settlement.after_pose.verify()
        expected = (
            settlement.after_pose.position.x
            - settlement.before_pose.position.x,
            settlement.after_pose.position.y
            - settlement.before_pose.position.y,
            settlement.after_pose.position.z
            - settlement.before_pose.position.z,
            settlement.after_pose.heading_millidegrees
            - settlement.before_pose.heading_millidegrees,
        )
        if (
            settlement.after_revision != settlement.before_revision + 1
            or settlement.before_revision < 0
            or settlement.signed_displacement != expected
            or expected == (0, 0, 0, 0)
            or len(settlement.full_dynamic_roots)
            != self._profile.required_dynamic_root_count
        ):
            raise ValueError("W1 signed spatial relation changed")
        root_ids = tuple(root.root_id for root in settlement.full_dynamic_roots)
        if root_ids != tuple(sorted(root_ids)) or len(root_ids) != len(
            set(root_ids)
        ):
            raise ValueError("W1 spatial full-field root set changed")
        for root in settlement.full_dynamic_roots:
            root.verify()
            if not is_dynamic_grounding_root(root):
                raise ValueError("W1 spatial settlement retained a static root")
        payload = settlement.payload()
        signature = hmac.new(
            self._settlement_key,
            _SETTLEMENT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            settlement.settlement_id != _digest(payload)
            or len(_canonical(payload)) > self._profile.max_settlement_bytes
            or not hmac.compare_digest(
                signature, settlement.authority_hmac_sha256
            )
            or settlement.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 spatial settlement authority changed")

    def _from_sources(
        self,
        source: W1SignedSpatialActionRetainedSource,
    ) -> W1SignedSpatialActionSettlement:
        if not isinstance(source, W1SignedSpatialActionRetainedSource):
            raise TypeError("W1 spatial retained source is not typed")
        execution = source.execution
        action_mount = source.action_mount
        self._world.verify_execution_receipt(execution)
        self._physical.verify_mount(action_mount)
        evidence = action_mount.evidence_receipt
        causal = action_mount.causal_settlement
        if (
            action_mount.state is not W1EvidenceState.OBSERVED
            or evidence is None
            or causal is None
        ):
            raise ValueError(
                "W1 spatial action requires settled physical evidence"
            )
        if (
            evidence.acoustic_emission_receipt_sha256s
            or evidence.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or evidence.causal_settlement_receipt_sha256
            != causal.authority_receipt_sha256
            or evidence.world_observation_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or evidence.world_observation_after_receipt_sha256
            != execution.after.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 spatial action physical source chain changed"
            )
        return self._from_values(
            execution=execution,
            evidence=evidence,
            causal=causal,
        )

    def _from_values(
        self,
        *,
        execution: ActionExecutionReceipt,
        evidence: W1PhysicalEvidenceReceipt,
        causal: CausalExperienceSettlement,
    ) -> W1SignedSpatialActionSettlement:
        before_pose = _self_pose(execution, after=False)
        after_pose = _self_pose(execution, after=True)
        roots = tuple(
            root for root in grounding_roots_from_settlement(causal)
            if is_dynamic_grounding_root(root)
        )
        provisional = W1SignedSpatialActionSettlement(
            settlement_id="0" * 64,
            execution_receipt_sha256=execution.authority_receipt_sha256,
            evidence_receipt_sha256=evidence.authority_receipt_sha256,
            causal_settlement_receipt_sha256=causal.authority_receipt_sha256,
            before_world_state_sha256=execution.before.state_sha256,
            after_world_state_sha256=execution.after.state_sha256,
            before_revision=execution.before.revision,
            after_revision=execution.after.revision,
            before_pose=before_pose,
            after_pose=after_pose,
            dx_mm=after_pose.position.x - before_pose.position.x,
            dy_mm=after_pose.position.y - before_pose.position.y,
            dz_mm=after_pose.position.z - before_pose.position.z,
            dyaw_millidegrees=(
                after_pose.heading_millidegrees
                - before_pose.heading_millidegrees
            ),
            full_dynamic_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._settlement_key,
            _SETTLEMENT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1SignedSpatialActionSettlement(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "settlement_id",
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            settlement_id=_digest(payload),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify_settlement(result)
        return result

    def settle_custodied(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> W1SignedSpatialActionSettlement:
        if (
            not isinstance(
                custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID
        ):
            raise ValueError(
                "W1 spatial settlement requires its purpose-bound custody"
            )
        view = custody_authority.open_child(custody_capability)
        execution = view.world_execution
        evidence = view.physical_evidence_receipt
        if (
            view.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or execution is None
            or evidence is None
            or evidence.acoustic_emission_receipt_sha256s
            or evidence.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 spatial action custody is not a physical action outcome"
            )
        result = self._from_values(
            execution=execution,
            evidence=evidence,
            causal=view.causal_settlement,
        )
        with self._lock:
            if result.execution_receipt_sha256 in self._used_execution_receipts:
                raise ValueError("W1 spatial settlement reuses an action source")
            if len(self._settlements) >= self._profile.max_settlements:
                raise RuntimeError("W1 spatial settlement capacity exhausted")
            candidate = dict(self._settlements)
            candidate[result.settlement_id] = result
            self._encoded(candidate)
            self._settlements = candidate
            self._used_execution_receipts.add(
                result.execution_receipt_sha256
            )
        return result

    def _body(
        self,
        settlements: Mapping[str, W1SignedSpatialActionSettlement],
    ) -> dict[str, object]:
        return {
            "resource_profile": self._profile.record(),
            "schema": W1_SIGNED_SPATIAL_ACTION_STATE_SCHEMA,
            "settlements": [
                settlements[key].record() for key in sorted(settlements)
            ],
        }

    def _encoded(
        self,
        settlements: Mapping[str, W1SignedSpatialActionSettlement],
    ) -> bytes:
        body = self._body(settlements)
        encoded = _canonical({
            "body": body,
            "schema": W1_SIGNED_SPATIAL_ACTION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("W1 spatial state capacity exhausted")
        return encoded

    def settle(
        self,
        *,
        execution: ActionExecutionReceipt,
        action_mount: W1PhysicalEvidenceMount,
    ) -> W1SignedSpatialActionSettlement:
        result = self._from_sources(W1SignedSpatialActionRetainedSource(
            execution=execution,
            action_mount=action_mount,
        ))
        with self._lock:
            if result.execution_receipt_sha256 in self._used_execution_receipts:
                raise ValueError("W1 spatial settlement reuses an action source")
            if len(self._settlements) >= self._profile.max_settlements:
                raise RuntimeError("W1 spatial settlement capacity exhausted")
            candidate = dict(self._settlements)
            candidate[result.settlement_id] = result
            self._encoded(candidate)
            self._settlements = candidate
            self._used_execution_receipts.add(
                result.execution_receipt_sha256
            )
        return result

    def verify(self, settlement: W1SignedSpatialActionSettlement) -> None:
        if not isinstance(settlement, W1SignedSpatialActionSettlement):
            raise TypeError("W1 signed spatial settlement is not typed")
        self._verify_settlement(settlement)

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._settlements)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        retained_sources: tuple[
            W1SignedSpatialActionRetainedSource, ...
        ],
    ) -> "W1SignedSpatialActionSettlementAuthority":
        if not isinstance(encoded, bytes):
            raise TypeError("W1 spatial state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("W1 spatial state is not canonical JSON") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != W1_SIGNED_SPATIAL_ACTION_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("W1 spatial state envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"resource_profile", "schema", "settlements"}
            or body.get("schema") != W1_SIGNED_SPATIAL_ACTION_STATE_SCHEMA
            or not isinstance(body.get("resource_profile"), Mapping)
            or not isinstance(body.get("settlements"), list)
            or not isinstance(retained_sources, tuple)
        ):
            raise ValueError("W1 spatial state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_settlement_bytes",
            "max_settlements",
            "max_state_bytes",
            "profile_id",
            "required_dynamic_root_count",
            "schema",
        }:
            raise ValueError("W1 spatial profile record changed")
        profile = W1SignedSpatialActionResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_settlements=raw_profile.get("max_settlements"),
            required_dynamic_root_count=raw_profile.get(
                "required_dynamic_root_count"
            ),
            max_settlement_bytes=raw_profile.get("max_settlement_bytes"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            world_authority=world_authority,
            physical_authority=physical_authority,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected_hmac
        ):
            raise ValueError("W1 spatial state HMAC changed")
        raw_by_id: dict[str, Mapping[str, object]] = {}
        for raw in body["settlements"]:
            if not isinstance(raw, Mapping):
                raise ValueError("W1 spatial settlement record changed")
            settlement_id = raw.get("settlement_id")
            _sha256(settlement_id, "W1 restored spatial settlement")
            if settlement_id in raw_by_id:
                raise ValueError("W1 spatial settlement is duplicated")
            raw_by_id[settlement_id] = raw
        if len(raw_by_id) != len(retained_sources):
            raise ValueError("W1 spatial retained source set changed")
        for source in retained_sources:
            result = owner._from_sources(source)
            raw = raw_by_id.pop(result.settlement_id, None)
            if raw is None or result.record() != raw:
                raise ValueError(
                    "W1 spatial state conflicts with retained physical source"
                )
            owner._settlements[result.settlement_id] = result
            if (
                result.execution_receipt_sha256
                in owner._used_execution_receipts
            ):
                raise ValueError("W1 restored spatial source is duplicated")
            owner._used_execution_receipts.add(
                result.execution_receipt_sha256
            )
        if (
            raw_by_id
            or len(owner._settlements) > profile.max_settlements
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("W1 spatial restored state changed")
        return owner

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            state_bytes = len(self._encoded(self._settlements))
            return {
                "capacity": self._profile.max_settlements,
                "capacity_exhausted": (
                    len(self._settlements) >= self._profile.max_settlements
                ),
                "count": len(self._settlements),
                "state_bytes": state_bytes,
                "state_capacity_bytes": self._profile.max_state_bytes,
                "used_execution_receipts": len(
                    self._used_execution_receipts
                ),
            }


__all__ = [
    "W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID",
    "W1SignedSpatialActionResourceProfile",
    "W1SignedSpatialActionRetainedSource",
    "W1SignedSpatialActionSettlement",
    "W1SignedSpatialActionSettlementAuthority",
]
