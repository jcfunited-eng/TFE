"""Bounded per-body models of causally accessible world state.

This is not a belief reader and does not attach names or who-tags to Guala's
own memory.  Each physically embodied other body receives a separate modeled
substrate.  Its object state changes only when authenticated access
provenance says that exact body had access at that exact W1 revision.

Guala's authenticated current world state is retained separately.  Therefore
an object may move in self state while an absent or inaccessible body's last
accessible state remains unchanged.  That divergence is an evidence fact,
not a claim about private belief.  Unknown access is retained as unresolved.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


PROFILE_SCHEMA = "guala.embodied_other_perspective.profile.v1"
ACCESS_SCHEMA = "guala.embodied_other_perspective.access.v1"
OBJECT_STATE_SCHEMA = "guala.embodied_other_perspective.object_state.v1"
MODEL_SCHEMA = "guala.embodied_other_perspective.model.v1"
SELF_STATE_SCHEMA = "guala.embodied_other_perspective.self_world.v1"
PREPARED_SCHEMA = "guala.embodied_other_perspective.prepared.v1"
STATE_SCHEMA = "guala.embodied_other_perspective.state.v1"
ENVELOPE_SCHEMA = "guala.embodied_other_perspective.state_hmac.v1"

_ACCESS_DOMAIN = b"guala-embodied-other-access-v1\0"
_MODEL_DOMAIN = b"guala-embodied-other-model-v1\0"
_SELF_DOMAIN = b"guala-embodied-other-self-world-v1\0"
_PREPARED_DOMAIN = b"guala-embodied-other-prepared-v1\0"
_STATE_DOMAIN = b"guala-embodied-other-state-v1\0"
_HEX = frozenset("0123456789abcdef")


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


def _key(value: bytes | str, label: str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(f"{label} authority key changed")
    return hashlib.sha256(label.encode("utf-8") + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be nonnegative")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} changed")
    return value


class AccessState(str, Enum):
    ACCESSIBLE = "accessible"
    INACCESSIBLE = "inaccessible"
    UNRESOLVED = "unresolved"


class AccessProvenanceKind(str, Enum):
    AUTHENTICATED_RECEPTOR_EVIDENCE = (
        "authenticated_receptor_evidence"
    )
    EXPLICITLY_MODELED_ACCESS = "explicitly_modeled_access"


@dataclass(frozen=True, slots=True)
class EmbodiedOtherPerspectiveProfile:
    profile_id: str
    max_other_bodies: int
    max_objects_per_body: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_other_bodies: int,
        max_objects_per_body: int,
        max_state_bytes: int,
    ) -> "EmbodiedOtherPerspectiveProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "perspective profile id"),
            max_other_bodies=_positive(
                max_other_bodies,
                "other-body capacity",
            ),
            max_objects_per_body=_positive(
                max_objects_per_body,
                "per-body object capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "perspective state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_other_bodies=provisional.max_other_bodies,
            max_objects_per_body=provisional.max_objects_per_body,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_objects_per_body": self.max_objects_per_body,
            "max_other_bodies": self.max_other_bodies,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_other_bodies=self.max_other_bodies,
            max_objects_per_body=self.max_objects_per_body,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("perspective profile changed")


@dataclass(frozen=True, slots=True)
class OtherBodyAccessProvenance:
    body_id: str
    world_revision: int
    world_observation_receipt_sha256: str
    object_access: tuple[tuple[str, AccessState], ...]
    provenance_kind: AccessProvenanceKind
    source_evidence_receipt_sha256: str
    private_belief_claimed: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "body_id": self.body_id,
            "object_access": [
                [object_id, state.value]
                for object_id, state in self.object_access
            ],
            "private_belief_claimed": self.private_belief_claimed,
            "provenance_kind": self.provenance_kind.value,
            "schema": ACCESS_SCHEMA,
            "source_evidence_receipt_sha256": (
                self.source_evidence_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class OtherBodyAccessProvenanceAuthority:
    """Authenticate explicit access state without inferring private belief."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: object,
        max_objects: int,
        receptor_access_authority: object | None = None,
    ) -> None:
        if not hasattr(world_authority, "verify_observation_snapshot"):
            raise TypeError("access provenance requires W1 world authority")
        self._key = _key(authority_key, "other-body access provenance")
        self._world = world_authority
        self._max_objects = _positive(
            max_objects,
            "access provenance object capacity",
        )
        if (
            receptor_access_authority is not None
            and not hasattr(
                receptor_access_authority,
                "verify_other_body_access",
            )
        ):
            raise TypeError(
                "receptor access authority lacks its verification boundary"
            )
        self._receptor_access = receptor_access_authority

    def issue(
        self,
        *,
        observation: object,
        body_id: str,
        object_access: tuple[tuple[str, AccessState], ...],
        provenance_kind: AccessProvenanceKind,
        source_evidence_receipt_sha256: str,
    ) -> OtherBodyAccessProvenance:
        self._world.verify_observation_snapshot(observation)
        _identifier(body_id, "access body id")
        _sha(source_evidence_receipt_sha256, "access source evidence")
        if body_id == observation.self_body_id:
            raise ValueError("self body cannot enter other-body access")
        bodies = {
            value.body_id: value for value in observation.bodies
        }
        objects = {
            value.object_id: value for value in observation.objects
        }
        if body_id not in bodies:
            raise ValueError("access body is absent from W1 geometry")
        if (
            not isinstance(object_access, tuple)
            or len(object_access) > self._max_objects
            or tuple(sorted(object_access, key=lambda item: item[0]))
            != object_access
            or len({item[0] for item in object_access})
            != len(object_access)
        ):
            raise ValueError("access object partition changed")
        for object_id, state in object_access:
            _identifier(object_id, "access object id")
            if object_id not in objects or not isinstance(state, AccessState):
                raise ValueError("access left authenticated W1 objects")
        if not isinstance(provenance_kind, AccessProvenanceKind):
            raise TypeError("access provenance kind is not typed")
        if (
            provenance_kind
            is AccessProvenanceKind.AUTHENTICATED_RECEPTOR_EVIDENCE
        ):
            if self._receptor_access is None:
                raise ValueError(
                    "authenticated receptor access authority is unavailable"
                )
            self._receptor_access.verify_other_body_access(
                observation=observation,
                body_id=body_id,
                object_access=object_access,
                source_evidence_receipt_sha256=(
                    source_evidence_receipt_sha256
                ),
            )
        provisional = OtherBodyAccessProvenance(
            body_id=body_id,
            world_revision=observation.revision,
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            object_access=object_access,
            provenance_kind=provenance_kind,
            source_evidence_receipt_sha256=(
                source_evidence_receipt_sha256
            ),
            private_belief_claimed=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _ACCESS_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return OtherBodyAccessProvenance(
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

    def verify(
        self,
        value: OtherBodyAccessProvenance,
        observation: object,
    ) -> None:
        if not isinstance(value, OtherBodyAccessProvenance):
            raise TypeError("other-body access provenance is not typed")
        self._world.verify_observation_snapshot(observation)
        expected = hmac.new(
            self._key,
            _ACCESS_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            value.private_belief_claimed
            or value.world_revision != observation.revision
            or value.world_observation_receipt_sha256
            != observation.authority_receipt_sha256
            or not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("other-body access authority changed")
        bodies = {item.body_id for item in observation.bodies}
        objects = {item.object_id for item in observation.objects}
        if (
            value.body_id == observation.self_body_id
            or value.body_id not in bodies
            or any(
                object_id not in objects
                for object_id, _state in value.object_access
            )
        ):
            raise ValueError("other-body access left W1 geometry")


@dataclass(frozen=True, slots=True)
class AccessibleObjectState:
    object_id: str
    world_revision: int
    world_observation_receipt_sha256: str
    access_provenance_receipt_sha256: str
    object_geometry: Mapping[str, object]

    def record(self) -> dict[str, object]:
        return {
            "access_provenance_receipt_sha256": (
                self.access_provenance_receipt_sha256
            ),
            "object_geometry": dict(self.object_geometry),
            "object_id": self.object_id,
            "schema": OBJECT_STATE_SCHEMA,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }


@dataclass(frozen=True, slots=True)
class OtherBodyPerspectiveModel:
    body_id: str
    body_geometry: Mapping[str, object]
    body_geometry_world_revision: int
    object_states: tuple[AccessibleObjectState, ...]
    current_access: tuple[tuple[str, AccessState], ...]
    current_access_provenance_receipt_sha256: str | None
    private_belief_claimed: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "body_geometry": dict(self.body_geometry),
            "body_geometry_world_revision": (
                self.body_geometry_world_revision
            ),
            "body_id": self.body_id,
            "current_access": [
                [object_id, state.value]
                for object_id, state in self.current_access
            ],
            "current_access_provenance_receipt_sha256": (
                self.current_access_provenance_receipt_sha256
            ),
            "object_states": [
                value.record() for value in self.object_states
            ],
            "private_belief_claimed": self.private_belief_claimed,
            "schema": MODEL_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class SelfWorldState:
    world_revision: int
    world_observation_receipt_sha256: str
    object_geometries: tuple[tuple[str, Mapping[str, object]], ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "object_geometries": [
                [object_id, dict(geometry)]
                for object_id, geometry in self.object_geometries
            ],
            "schema": SELF_STATE_SCHEMA,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedPerspectiveMutation:
    before_state_sha256: str
    prior_self_state: SelfWorldState | None
    prior_models: tuple[OtherBodyPerspectiveModel, ...]
    staged_self_state: SelfWorldState
    staged_models: tuple[OtherBodyPerspectiveModel, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "before_state_sha256": self.before_state_sha256,
            "prior_model_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_models
            ],
            "prior_self_state_receipt_sha256": (
                self.prior_self_state.authority_receipt_sha256
                if self.prior_self_state is not None
                else None
            ),
            "schema": PREPARED_SCHEMA,
            "staged_model_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_models
            ],
            "staged_self_state_receipt_sha256": (
                self.staged_self_state.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class PerspectiveMutationUndo:
    prepared: PreparedPerspectiveMutation
    _owner_authority: object = field(repr=False, compare=False)


class EmbodiedOtherPerspectiveOwner:
    """Own exact self state and separate last-accessible state per body."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: EmbodiedOtherPerspectiveProfile,
        world_authority: object,
        access_authority: OtherBodyAccessProvenanceAuthority,
    ) -> None:
        profile.verify()
        if not hasattr(world_authority, "verify_observation_snapshot"):
            raise TypeError("perspective owner requires W1 world authority")
        if not isinstance(
            access_authority,
            OtherBodyAccessProvenanceAuthority,
        ):
            raise TypeError("perspective owner requires access authority")
        root = _key(authority_key, "embodied other perspective")
        self._model_key = hashlib.sha256(_MODEL_DOMAIN + root).digest()
        self._self_key = hashlib.sha256(_SELF_DOMAIN + root).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._world = world_authority
        self._access = access_authority
        self._self_state: SelfWorldState | None = None
        self._models: tuple[OtherBodyPerspectiveModel, ...] = ()
        self._prepared: PreparedPerspectiveMutation | None = None
        self._undo_authority = object()
        self._lock = threading.RLock()
        self._encoded_locked()

    @property
    def self_world_state(self) -> SelfWorldState | None:
        with self._lock:
            return self._self_state

    @property
    def models(self) -> tuple[OtherBodyPerspectiveModel, ...]:
        with self._lock:
            return self._models

    def model_for(self, body_id: str) -> OtherBodyPerspectiveModel | None:
        _identifier(body_id, "perspective body id")
        with self._lock:
            return next(
                (value for value in self._models if value.body_id == body_id),
                None,
            )

    def _seal_self(self, observation: object) -> SelfWorldState:
        provisional = SelfWorldState(
            world_revision=observation.revision,
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            object_geometries=tuple(
                sorted(
                    (
                        value.object_id,
                        value.as_record(),
                    )
                    for value in observation.objects
                )
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._self_key,
            _SELF_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return SelfWorldState(
            world_revision=provisional.world_revision,
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            object_geometries=provisional.object_geometries,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _seal_model(
        self,
        *,
        body: object,
        observation: object,
        prior: OtherBodyPerspectiveModel | None,
        access: OtherBodyAccessProvenance | None,
    ) -> OtherBodyPerspectiveModel:
        prior_objects = {
            value.object_id: value
            for value in prior.object_states
        } if prior is not None else {}
        if access is None:
            access_map = {
                value.object_id: AccessState.UNRESOLVED
                for value in observation.objects
            }
            access_receipt = None
        else:
            access_map = {
                object_id: state
                for object_id, state in access.object_access
            }
            access_receipt = access.authority_receipt_sha256
        current_objects = {
            value.object_id: value for value in observation.objects
        }
        for object_id, state in access_map.items():
            if state is AccessState.ACCESSIBLE:
                value = current_objects[object_id]
                prior_objects[object_id] = AccessibleObjectState(
                    object_id=object_id,
                    world_revision=observation.revision,
                    world_observation_receipt_sha256=(
                        observation.authority_receipt_sha256
                    ),
                    access_provenance_receipt_sha256=(
                        access.authority_receipt_sha256
                    ),
                    object_geometry=value.as_record(),
                )
        if len(prior_objects) > self._profile.max_objects_per_body:
            raise RuntimeError("per-body perspective capacity exhausted")
        provisional = OtherBodyPerspectiveModel(
            body_id=body.body_id,
            body_geometry=body.as_record(),
            body_geometry_world_revision=observation.revision,
            object_states=tuple(
                prior_objects[key] for key in sorted(prior_objects)
            ),
            current_access=tuple(sorted(access_map.items())),
            current_access_provenance_receipt_sha256=access_receipt,
            private_belief_claimed=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._model_key,
            _MODEL_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return OtherBodyPerspectiveModel(
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

    def _verify_self_state(self, value: SelfWorldState) -> None:
        if not isinstance(value, SelfWorldState):
            raise TypeError("self-world state is not typed")
        _nonnegative(value.world_revision, "self-world revision")
        _sha(
            value.world_observation_receipt_sha256,
            "self-world observation",
        )
        if (
            tuple(item[0] for item in value.object_geometries)
            != tuple(sorted({item[0] for item in value.object_geometries}))
            or len(value.object_geometries)
            > self._profile.max_objects_per_body
        ):
            raise ValueError("self-world object extent changed")
        expected = hmac.new(
            self._self_key,
            _SELF_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("self-world authority changed")

    def _verify_model(self, value: OtherBodyPerspectiveModel) -> None:
        if not isinstance(value, OtherBodyPerspectiveModel):
            raise TypeError("other-body model is not typed")
        _identifier(value.body_id, "modeled body id")
        _nonnegative(
            value.body_geometry_world_revision,
            "modeled body geometry revision",
        )
        if value.private_belief_claimed:
            raise ValueError("other-body model claimed private belief")
        if (
            tuple(item.object_id for item in value.object_states)
            != tuple(sorted({
                item.object_id for item in value.object_states
            }))
            or len(value.object_states)
            > self._profile.max_objects_per_body
            or tuple(item[0] for item in value.current_access)
            != tuple(sorted({
                item[0] for item in value.current_access
            }))
        ):
            raise ValueError("other-body model extent changed")
        for item in value.object_states:
            _identifier(item.object_id, "modeled object id")
            _nonnegative(item.world_revision, "modeled object revision")
            _sha(
                item.world_observation_receipt_sha256,
                "modeled object observation",
            )
            _sha(
                item.access_provenance_receipt_sha256,
                "modeled object access provenance",
            )
        if value.current_access_provenance_receipt_sha256 is not None:
            _sha(
                value.current_access_provenance_receipt_sha256,
                "current modeled access provenance",
            )
        expected = hmac.new(
            self._model_key,
            _MODEL_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("other-body model authority changed")

    def _committed_body_locked(self) -> dict[str, object]:
        return {
            "models": [value.record() for value in self._models],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "self_world_state": (
                self._self_state.record()
                if self._self_state is not None
                else None
            ),
        }

    def _state_sha_locked(self) -> str:
        return _digest(self._committed_body_locked())

    def _encoded_locked(self) -> bytes:
        body = self._committed_body_locked() | {
            "prepared": (
                {
                    **self._prepared.payload(),
                    "authority_hmac_sha256": (
                        self._prepared.authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        self._prepared.authority_receipt_sha256
                    ),
                    "prior_models": [
                        value.record()
                        for value in self._prepared.prior_models
                    ],
                    "prior_self_state": (
                        self._prepared.prior_self_state.record()
                        if self._prepared.prior_self_state is not None
                        else None
                    ),
                    "staged_models": [
                        value.record()
                        for value in self._prepared.staged_models
                    ],
                    "staged_self_state": (
                        self._prepared.staged_self_state.record()
                    ),
                }
                if self._prepared is not None
                else None
            )
        }
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
            raise RuntimeError("perspective state capacity exhausted")
        return encoded

    def prepare(
        self,
        *,
        observation: object,
        access_provenance: tuple[OtherBodyAccessProvenance, ...],
    ) -> PreparedPerspectiveMutation:
        self._world.verify_observation_snapshot(observation)
        if not isinstance(access_provenance, tuple):
            raise TypeError("perspective access provenance must be a tuple")
        access_by_body: dict[str, OtherBodyAccessProvenance] = {}
        for value in access_provenance:
            self._access.verify(value, observation)
            if value.body_id in access_by_body:
                raise ValueError("perspective repeats other-body access")
            access_by_body[value.body_id] = value
        bodies = {
            value.body_id: value
            for value in observation.bodies
            if value.body_id != observation.self_body_id
        }
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "one perspective mutation is already prepared"
                )
            prior_by_body = {
                value.body_id: value for value in self._models
            }
            staged_by_body = dict(prior_by_body)
            for body_id, access in access_by_body.items():
                staged_by_body[body_id] = self._seal_model(
                    body=bodies[body_id],
                    observation=observation,
                    prior=prior_by_body.get(body_id),
                    access=access,
                )
            for body_id in sorted(set(prior_by_body) & set(bodies)):
                if body_id not in access_by_body:
                    staged_by_body[body_id] = self._seal_model(
                        body=bodies[body_id],
                        observation=observation,
                        prior=prior_by_body[body_id],
                        access=None,
                    )
            staged_models = tuple(
                staged_by_body[key] for key in sorted(staged_by_body)
            )
            if len(staged_models) > self._profile.max_other_bodies:
                raise RuntimeError("other-body perspective capacity exhausted")
            staged_self = self._seal_self(observation)
            provisional = PreparedPerspectiveMutation(
                before_state_sha256=self._state_sha_locked(),
                prior_self_state=self._self_state,
                prior_models=self._models,
                staged_self_state=staged_self,
                staged_models=staged_models,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._prepared_key,
                _PREPARED_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = PreparedPerspectiveMutation(
                before_state_sha256=provisional.before_state_sha256,
                prior_self_state=provisional.prior_self_state,
                prior_models=provisional.prior_models,
                staged_self_state=provisional.staged_self_state,
                staged_models=provisional.staged_models,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._prepared = prepared
            self._encoded_locked()
            return prepared

    def _verify_prepared(self, value: PreparedPerspectiveMutation) -> None:
        if not isinstance(value, PreparedPerspectiveMutation):
            raise TypeError("prepared perspective mutation is not typed")
        expected = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("prepared perspective authority changed")
        if value.prior_self_state is not None:
            self._verify_self_state(value.prior_self_state)
        self._verify_self_state(value.staged_self_state)
        for model in value.prior_models + value.staged_models:
            self._verify_model(model)

    def commit(
        self,
        value: PreparedPerspectiveMutation,
    ) -> PerspectiveMutationUndo:
        with self._lock:
            self._verify_prepared(value)
            if self._prepared != value:
                raise ValueError(
                    "prepared perspective mutation is not current"
                )
            if (
                self._state_sha_locked() != value.before_state_sha256
                or self._self_state != value.prior_self_state
                or self._models != value.prior_models
            ):
                raise RuntimeError("perspective state changed before commit")
            self._self_state = value.staged_self_state
            self._models = value.staged_models
            self._prepared = None
            self._encoded_locked()
            return PerspectiveMutationUndo(
                prepared=value,
                _owner_authority=self._undo_authority,
            )

    def discard(self, value: PreparedPerspectiveMutation) -> None:
        with self._lock:
            self._verify_prepared(value)
            if self._prepared != value:
                raise ValueError(
                    "prepared perspective mutation is not current"
                )
            self._prepared = None
            self._encoded_locked()

    def rollback(self, undo: PerspectiveMutationUndo) -> None:
        if (
            not isinstance(undo, PerspectiveMutationUndo)
            or undo._owner_authority is not self._undo_authority
        ):
            raise ValueError("perspective undo authority changed")
        value = undo.prepared
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot roll back through an in-flight mutation"
                )
            if (
                self._self_state != value.staged_self_state
                or self._models != value.staged_models
            ):
                raise ValueError(
                    "committed perspective mutation is not current"
                )
            self._self_state = value.prior_self_state
            self._models = value.prior_models
            self._encoded_locked()

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded_locked()

    def status(self) -> dict[str, object]:
        with self._lock:
            unresolved = sum(
                state is AccessState.UNRESOLVED
                for model in self._models
                for _object_id, state in model.current_access
            )
            return {
                "mechanism_state": (
                    "quiescent" if not self._models else "perturbed"
                ),
                "modeled_other_bodies": len(self._models),
                "per_body_object_capacity": (
                    self._profile.max_objects_per_body
                ),
                "private_belief_claimed": False,
                "schema": (
                    "guala.embodied_other_perspective.status.v1"
                ),
                "self_world_revision": (
                    self._self_state.world_revision
                    if self._self_state is not None
                    else None
                ),
                "state_bytes": len(self._encoded_locked()),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "unresolved_access_entries": unresolved,
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: EmbodiedOtherPerspectiveProfile,
        world_authority: object,
        access_authority: OtherBodyAccessProvenanceAuthority,
        encoded: bytes,
    ) -> "EmbodiedOtherPerspectiveOwner":
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > profile.max_state_bytes
        ):
            raise ValueError("perspective cold state is invalid")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("perspective cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("perspective cold envelope changed")
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body)
            != {
                "models",
                "prepared",
                "profile",
                "schema",
                "self_world_state",
            }
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or not isinstance(body.get("models"), list)
        ):
            raise ValueError("perspective cold payload changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            world_authority=world_authority,
            access_authority=access_authority,
        )
        expected = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected,
        ):
            raise ValueError("perspective cold state authority changed")
        if body["prepared"] is not None:
            raise ValueError(
                "cold restore requires a committed perspective boundary"
            )
        with owner._lock:
            owner._self_state = (
                owner._self_from_raw(body["self_world_state"])
                if body["self_world_state"] is not None
                else None
            )
            owner._models = tuple(
                owner._model_from_raw(raw) for raw in body["models"]
            )
            if owner._self_state is not None:
                owner._verify_self_state(owner._self_state)
            for model in owner._models:
                owner._verify_model(model)
            if owner._encoded_locked() != encoded:
                raise ValueError(
                    "perspective cold round-trip changed state"
                )
        return owner

    def _self_from_raw(self, raw: object) -> SelfWorldState:
        if not isinstance(raw, Mapping) or raw.get("schema") != SELF_STATE_SCHEMA:
            raise ValueError("cold self-world state changed")
        geometries = raw.get("object_geometries")
        if not isinstance(geometries, list):
            raise ValueError("cold self-world objects changed")
        return SelfWorldState(
            world_revision=_nonnegative(
                raw["world_revision"],
                "cold self-world revision",
            ),
            world_observation_receipt_sha256=_sha(
                raw["world_observation_receipt_sha256"],
                "cold self-world observation",
            ),
            object_geometries=tuple(
                (item[0], item[1]) for item in geometries
            ),
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold self-world HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold self-world authority",
            ),
        )

    def _model_from_raw(self, raw: object) -> OtherBodyPerspectiveModel:
        if not isinstance(raw, Mapping) or raw.get("schema") != MODEL_SCHEMA:
            raise ValueError("cold other-body model changed")
        objects = tuple(
            AccessibleObjectState(
                object_id=item["object_id"],
                world_revision=item["world_revision"],
                world_observation_receipt_sha256=(
                    item["world_observation_receipt_sha256"]
                ),
                access_provenance_receipt_sha256=(
                    item["access_provenance_receipt_sha256"]
                ),
                object_geometry=item["object_geometry"],
            )
            for item in raw["object_states"]
        )
        return OtherBodyPerspectiveModel(
            body_id=raw["body_id"],
            body_geometry=raw["body_geometry"],
            body_geometry_world_revision=raw[
                "body_geometry_world_revision"
            ],
            object_states=objects,
            current_access=tuple(
                (item[0], AccessState(item[1]))
                for item in raw["current_access"]
            ),
            current_access_provenance_receipt_sha256=raw[
                "current_access_provenance_receipt_sha256"
            ],
            private_belief_claimed=raw["private_belief_claimed"],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )


__all__ = (
    "AccessProvenanceKind",
    "AccessState",
    "AccessibleObjectState",
    "EmbodiedOtherPerspectiveOwner",
    "EmbodiedOtherPerspectiveProfile",
    "OtherBodyAccessProvenance",
    "OtherBodyAccessProvenanceAuthority",
    "OtherBodyPerspectiveModel",
    "PerspectiveMutationUndo",
    "PreparedPerspectiveMutation",
    "SelfWorldState",
)
