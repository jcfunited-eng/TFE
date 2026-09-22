"""Consequence-selected physical articulation bindings.

One fresh self-articulatory attempt may become a THING relation only when the
immediately subsequent applied companion action names that exact attempt
custody as its causal intent.  Both the articulatory program and THING are
derived from authenticated physical custody.  Neither is accepted as public
input.

This owner does not recognize or compare sound.  It accepts no label,
transcript, waveform, score, target, cursor, PCM exemplar, or replay route.
It owns its own bounded HMAC-authenticated THING-to-program state and supports
prepare, commit, discard, exact rollback, and cold restore.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    SECOND_BODY_PORT_ID,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FreshArticulatorySelfAcousticCustodyAuthority,
    FreshArticulatorySelfAcousticCustodyReceipt,
    fresh_articulatory_receipt_from_record,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    CompanionVocalEpisodeIntentReceipt,
    W1CompanionVocalExperienceAuthority,
)


PROFILE_SCHEMA = "guala.articulatory_consequence_closure.profile.v1"
BINDING_SCHEMA = "guala.articulatory_consequence_closure.binding.v2"
PREPARED_SCHEMA = "guala.articulatory_consequence_closure.prepared.v2"
STATE_SCHEMA = "guala.articulatory_consequence_closure.state.v2"
ENVELOPE_SCHEMA = (
    "guala.articulatory_consequence_closure.state_hmac.v2"
)
STATUS_SCHEMA = "guala.articulatory_consequence_closure.status.v2"

_BINDING_DOMAIN = b"guala-articulatory-consequence-closure-binding-v2\0"
_PREPARED_DOMAIN = b"guala-articulatory-consequence-closure-prepared-v2\0"
_STATE_DOMAIN = b"guala-articulatory-consequence-closure-state-v2\0"
_LEGACY_BINDING_SCHEMA = "guala.articulatory_consequence_closure.binding.v1"
_LEGACY_STATE_SCHEMA = "guala.articulatory_consequence_closure.state.v1"
_LEGACY_ENVELOPE_SCHEMA = (
    "guala.articulatory_consequence_closure.state_hmac.v1"
)
_LEGACY_BINDING_DOMAIN = (
    b"guala-articulatory-consequence-closure-binding-v1\0"
)
_LEGACY_STATE_DOMAIN = (
    b"guala-articulatory-consequence-closure-state-v1\0"
)
_DIRECT_LINKAGE = "direct_attempt"
_EPISODE_LINKAGE = "companion_episode_intent"
_HEX = frozenset("0123456789abcdef")
_MAX_PROFILE_ID_BYTES = 256
_MAX_CONFIGURED_BINDINGS = 1_000_000
_MAX_CONFIGURED_STATE_BYTES = 256 * 1024 * 1024
_PREPARED_AUTHORITY = object()


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
        raise TypeError(
            "articulatory consequence authority key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "articulatory consequence authority key boundary changed"
        )
    return result


def _identifier(value: object, name: str, *, max_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
    ):
        raise ValueError(f"{name} is outside its exact identifier boundary")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _capacity(
    value: object,
    name: str,
    *,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= maximum
    ):
        raise ValueError(f"{name} is outside its explicit capacity")
    return value


def _sign(
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
) -> str:
    return hmac.new(
        key,
        domain + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ArticulatoryConsequenceClosureProfile:
    profile_id: str
    max_bindings: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_bindings: int,
        max_state_bytes: int,
    ) -> "ArticulatoryConsequenceClosureProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id,
                "articulatory consequence profile",
                max_bytes=_MAX_PROFILE_ID_BYTES,
            ),
            max_bindings=_capacity(
                max_bindings,
                "articulatory consequence binding capacity",
                maximum=_MAX_CONFIGURED_BINDINGS,
            ),
            max_state_bytes=_capacity(
                max_state_bytes,
                "articulatory consequence state byte capacity",
                maximum=_MAX_CONFIGURED_STATE_BYTES,
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_bindings=provisional.max_bindings,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_bindings": self.max_bindings,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(
            self.profile_id,
            "articulatory consequence profile",
            max_bytes=_MAX_PROFILE_ID_BYTES,
        )
        _capacity(
            self.max_bindings,
            "articulatory consequence binding capacity",
            maximum=_MAX_CONFIGURED_BINDINGS,
        )
        _capacity(
            self.max_state_bytes,
            "articulatory consequence state byte capacity",
            maximum=_MAX_CONFIGURED_STATE_BYTES,
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError(
                "articulatory consequence profile authority changed"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class ArticulatoryConsequenceBinding:
    thing_id: str
    program_id: str
    thing_mosaic_receipt_at_closure_sha256: str
    thing_partition_receipt_sha256: str
    attempt_custody: FreshArticulatorySelfAcousticCustodyReceipt
    companion_episode_intent: CompanionVocalEpisodeIntentReceipt | None
    consequence_execution: ActionExecutionReceipt
    consequence_execution_receipt_sha256: str
    consequence_before_receipt_sha256: str
    consequence_after_receipt_sha256: str
    consequence_port_id: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def causal_linkage(self) -> str:
        return (
            _DIRECT_LINKAGE
            if self.companion_episode_intent is None
            else _EPISODE_LINKAGE
        )

    def payload(self) -> dict[str, object]:
        return {
            "attempt_custody": self.attempt_custody.record(),
            "causal_linkage": self.causal_linkage,
            "companion_episode_intent": (
                None
                if self.companion_episode_intent is None
                else {
                    **self.companion_episode_intent.payload(),
                    "authority_hmac_sha256": (
                        self.companion_episode_intent
                        .authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        self.companion_episode_intent
                        .authority_receipt_sha256
                    ),
                }
            ),
            "consequence_execution": (
                self.consequence_execution.as_record()
            ),
            "consequence_after_receipt_sha256": (
                self.consequence_after_receipt_sha256
            ),
            "consequence_before_receipt_sha256": (
                self.consequence_before_receipt_sha256
            ),
            "consequence_execution_receipt_sha256": (
                self.consequence_execution_receipt_sha256
            ),
            "consequence_port_id": self.consequence_port_id,
            "program_id": self.program_id,
            "schema": BINDING_SCHEMA,
            "thing_id": self.thing_id,
            "thing_mosaic_receipt_at_closure_sha256": (
                self.thing_mosaic_receipt_at_closure_sha256
            ),
            "thing_partition_receipt_sha256": (
                self.thing_partition_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedArticulatoryConsequenceClosure:
    _candidate_binding: ArticulatoryConsequenceBinding = field(repr=False)
    _attempt_custody: FreshArticulatorySelfAcousticCustodyReceipt = field(
        repr=False
    )
    _consequence: ActionExecutionReceipt = field(repr=False)
    _companion_episode_intent: (
        CompanionVocalEpisodeIntentReceipt | None
    ) = field(repr=False)
    _prior_bindings: tuple[ArticulatoryConsequenceBinding, ...] = field(
        repr=False
    )
    _staged_bindings: tuple[ArticulatoryConsequenceBinding, ...] = field(
        repr=False
    )
    _changed: bool = field(repr=False)
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "attempt_custody_receipt_sha256": (
                self._attempt_custody.authority_receipt_sha256
            ),
            "binding_receipt_sha256": (
                self._candidate_binding.authority_receipt_sha256
            ),
            "changed": self._changed,
            "consequence_execution_receipt_sha256": (
                self._consequence.authority_receipt_sha256
            ),
            "companion_episode_intent_receipt_sha256": (
                None
                if self._companion_episode_intent is None
                else self._companion_episode_intent
                .authority_receipt_sha256
            ),
            "prior_state_sha256": _digest([
                value.authority_receipt_sha256
                for value in self._prior_bindings
            ]),
            "schema": PREPARED_SCHEMA,
            "staged_state_sha256": _digest([
                value.authority_receipt_sha256
                for value in self._staged_bindings
            ]),
        }


@dataclass(frozen=True, slots=True)
class ArticulatoryConsequenceClosureUndo:
    prior_bindings: tuple[ArticulatoryConsequenceBinding, ...]
    staged_bindings: tuple[ArticulatoryConsequenceBinding, ...]
    changed: bool
    _owner_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CommittedArticulatoryConsequenceClosure:
    binding: ArticulatoryConsequenceBinding
    undo: ArticulatoryConsequenceClosureUndo


class ArticulatoryConsequenceClosureOwner:
    """Own only consequence-selected THING-to-program relations."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: ArticulatoryConsequenceClosureProfile,
        fresh_custody_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        thing_owner: CausalThingMosaicOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
        companion_vocal_authority: W1CompanionVocalExperienceAuthority,
    ) -> None:
        if not isinstance(
            profile,
            ArticulatoryConsequenceClosureProfile,
        ):
            raise TypeError(
                "articulatory consequence closure requires its profile"
            )
        profile.verify()
        if not isinstance(
            fresh_custody_authority,
            FreshArticulatorySelfAcousticCustodyAuthority,
        ):
            raise TypeError(
                "articulatory consequence requires fresh custody authority"
            )
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "articulatory consequence requires causal THING authority"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "articulatory consequence requires articulatory authority"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "articulatory consequence requires W1 world authority"
            )
        if not isinstance(
            companion_vocal_authority,
            W1CompanionVocalExperienceAuthority,
        ):
            raise TypeError(
                "articulatory consequence requires companion vocal authority"
            )
        if (
            companion_vocal_authority._world is not world_authority
            or companion_vocal_authority._companion_port_id
            != SECOND_BODY_PORT_ID
        ):
            raise ValueError(
                "articulatory consequence crossed companion vocal ownership"
            )
        fresh_custody_authority.verify_dependency_ownership(
            articulatory_owner=articulatory_owner,
            world_authority=world_authority,
        )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._binding_key = hashlib.sha256(
            _BINDING_DOMAIN + root
        ).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._legacy_binding_key = hashlib.sha256(
            _LEGACY_BINDING_DOMAIN + root
        ).digest()
        self._legacy_state_key = hashlib.sha256(
            _LEGACY_STATE_DOMAIN + root
        ).digest()
        self._profile = profile
        self._fresh = fresh_custody_authority
        self._things = thing_owner
        self._articulatory = articulatory_owner
        self._world = world_authority
        self._companion = companion_vocal_authority
        self._bindings: tuple[ArticulatoryConsequenceBinding, ...] = ()
        self._owner_authority = object()
        self._lock = threading.RLock()

    @property
    def bindings(self) -> tuple[ArticulatoryConsequenceBinding, ...]:
        with self._lock:
            return self._bindings

    def verify_owners_exact(
        self,
        *,
        reciprocal_owner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Require one exact THING, articulation, and world ownership graph."""

        from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
            CausalThingReciprocalMosaicOwner,
        )

        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "articulatory consequence ownership requires reciprocal THING"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "articulatory consequence ownership requires articulation"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "articulatory consequence ownership requires world"
            )
        reciprocal_owner.verify_thing_owner_exact(self._things)
        if self._articulatory is not articulatory_owner:
            raise ValueError(
                "articulatory consequence crossed articulatory ownership"
            )
        if self._world is not world_authority:
            raise ValueError(
                "articulatory consequence crossed world ownership"
            )

    def _program_is_retained(self, program_id: str) -> bool:
        return any(
            program.program_id == program_id
            for program in self._articulatory.programs
        )

    def _mosaic_partition(
        self,
        *,
        thing_id: str,
        partition_receipt_sha256: str,
    ):
        matches = tuple(
            (
                mosaic,
                partition,
            )
            for mosaic in self._things.mosaics
            if mosaic.thing_id == thing_id
            for partition in mosaic.partitions
            if partition.authority_receipt_sha256
            == partition_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "articulatory consequence binding lost its THING partition"
            )
        return matches[0]

    def _verify_binding(
        self,
        binding: ArticulatoryConsequenceBinding,
    ) -> None:
        if not isinstance(binding, ArticulatoryConsequenceBinding):
            raise TypeError(
                "articulatory consequence binding is not typed"
            )
        self._fresh.verify_receipt(binding.attempt_custody)
        self._world.verify_execution_receipt(
            binding.consequence_execution
        )
        self._verify_causal_linkage(
            attempt_custody=binding.attempt_custody,
            consequence=binding.consequence_execution,
            companion_episode_intent=(
                binding.companion_episode_intent
            ),
        )
        for value, name in (
            (binding.thing_id, "THING"),
            (binding.program_id, "program"),
            (
                binding.thing_mosaic_receipt_at_closure_sha256,
                "THING mosaic at closure",
            ),
            (
                binding.thing_partition_receipt_sha256,
                "THING partition",
            ),
            (
                binding.consequence_execution_receipt_sha256,
                "consequence execution",
            ),
            (
                binding.consequence_before_receipt_sha256,
                "consequence before",
            ),
            (
                binding.consequence_after_receipt_sha256,
                "consequence after",
            ),
            (binding.authority_hmac_sha256, "binding HMAC"),
            (binding.authority_receipt_sha256, "binding authority"),
        ):
            _sha256(value, f"articulatory consequence {name}")
        if (
            binding.consequence_port_id != SECOND_BODY_PORT_ID
            or binding.consequence_execution.disposition != "applied"
            or binding.consequence_execution.reason != "applied"
            or binding.consequence_execution.port_id
            != binding.consequence_port_id
            or binding.consequence_execution.authority_receipt_sha256
            != binding.consequence_execution_receipt_sha256
            or binding.consequence_execution.before
            .authority_receipt_sha256
            != binding.consequence_before_receipt_sha256
            or binding.consequence_execution.after
            .authority_receipt_sha256
            != binding.consequence_after_receipt_sha256
            or binding.consequence_execution.before.revision + 1
            != binding.consequence_execution.after.revision
            or binding.program_id != binding.attempt_custody.program_id
            or binding.consequence_before_receipt_sha256
            != binding.attempt_custody.world_after_receipt_sha256
            or not self._program_is_retained(binding.program_id)
        ):
            raise ValueError(
                "articulatory consequence binding boundary changed"
            )
        mosaic, partition = self._mosaic_partition(
            thing_id=binding.thing_id,
            partition_receipt_sha256=(
                binding.thing_partition_receipt_sha256
            ),
        )
        if (
            partition.settlement_receipt_sha256
            != binding.attempt_custody
            .acoustic_settlement_receipt_sha256
            or partition.source_occurrence_id
            != binding.attempt_custody.source_occurrence_id
            or partition.parent_custody_receipt_sha256
            != binding.attempt_custody
            .parent_settled_custody_receipt_sha256
            or partition.execution_receipt_sha256
            != binding.attempt_custody
            .world_execution_receipt_sha256
            or partition.world_observation_receipt_sha256
            != binding.attempt_custody.world_after_receipt_sha256
            or mosaic.thing_id != binding.thing_id
        ):
            raise ValueError(
                "articulatory consequence binding crossed THING custody"
            )
        signature = _sign(
            self._binding_key,
            _BINDING_DOMAIN,
            binding.payload(),
        )
        if (
            not hmac.compare_digest(
                signature,
                binding.authority_hmac_sha256,
            )
            or binding.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": binding.payload(),
            })
        ):
            raise ValueError(
                "articulatory consequence binding authority changed"
            )

    def verify_binding(
        self,
        binding: ArticulatoryConsequenceBinding,
    ) -> None:
        with self._lock:
            self._verify_binding(binding)
            if binding not in self._bindings:
                raise ValueError(
                    "articulatory consequence binding is not retained"
                )

    def _derive_live_relation(
        self,
        *,
        attempt_custody: (
            FreshArticulatorySelfAcousticCustodyReceipt
        ),
        consequence: ActionExecutionReceipt,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
        require_current_world: bool,
    ):
        self._fresh.verify_receipt(attempt_custody)
        if not isinstance(consequence, ActionExecutionReceipt):
            raise TypeError(
                "articulatory consequence execution is not typed"
            )
        self._world.verify_execution_receipt(consequence)
        self._verify_causal_linkage(
            attempt_custody=attempt_custody,
            consequence=consequence,
            companion_episode_intent=companion_episode_intent,
        )
        if (
            consequence.disposition != "applied"
            or consequence.reason != "applied"
            or consequence.port_id != SECOND_BODY_PORT_ID
            or consequence.before.authority_receipt_sha256
            != attempt_custody.world_after_receipt_sha256
            or consequence.before.revision + 1
            != consequence.after.revision
        ):
            raise ValueError(
                "companion consequence is not the immediate physical "
                "result of the fresh attempt"
            )
        if require_current_world and (
            self._world.observation_snapshot() != consequence.after
        ):
            raise ValueError(
                "companion consequence is no longer the immediate world edge"
            )
        if not self._program_is_retained(attempt_custody.program_id):
            raise ValueError(
                "fresh attempt articulatory program is not retained"
            )
        matches = tuple(
            mosaic
            for mosaic in self._things.mosaics
            if mosaic.partitions
            and mosaic.partitions[-1].settlement_receipt_sha256
            == attempt_custody.acoustic_settlement_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "fresh attempt does not resolve one latest causal THING"
            )
        mosaic = matches[0]
        partition = mosaic.partitions[-1]
        if (
            partition.source_occurrence_id
            != attempt_custody.source_occurrence_id
            or partition.parent_custody_receipt_sha256
            != attempt_custody
            .parent_settled_custody_receipt_sha256
            or partition.execution_receipt_sha256
            != attempt_custody.world_execution_receipt_sha256
            or partition.world_observation_receipt_sha256
            != attempt_custody.world_after_receipt_sha256
            or partition.world_revision != consequence.before.revision
        ):
            raise ValueError(
                "fresh attempt and latest THING partition crossed custody"
            )
        return mosaic, partition

    def _verify_causal_linkage(
        self,
        *,
        attempt_custody: FreshArticulatorySelfAcousticCustodyReceipt,
        consequence: ActionExecutionReceipt,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
    ) -> None:
        if companion_episode_intent is None:
            if (
                consequence.causal_intent_receipt_sha256
                != attempt_custody.authority_receipt_sha256
            ):
                raise ValueError(
                    "companion consequence is not the immediate physical "
                    "result of the fresh attempt"
                )
            return
        self._companion.verify_episode_intent(
            companion_episode_intent
        )
        if (
            companion_episode_intent.companion_port_id
            != SECOND_BODY_PORT_ID
            or companion_episode_intent
            .causal_parent_receipt_sha256
            != attempt_custody.authority_receipt_sha256
            or companion_episode_intent
            .world_observation_receipt_sha256
            != attempt_custody.world_after_receipt_sha256
            or companion_episode_intent.block_count != 1
            or consequence.causal_intent_receipt_sha256
            != companion_episode_intent.authority_receipt_sha256
        ):
            raise ValueError(
                "companion vocal episode is not the authenticated "
                "one-block result of the fresh attempt"
            )

    def _seal_binding(
        self,
        *,
        attempt_custody: (
            FreshArticulatorySelfAcousticCustodyReceipt
        ),
        consequence: ActionExecutionReceipt,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
        mosaic,
        partition,
        mosaic_receipt_at_closure_sha256: str | None = None,
    ) -> ArticulatoryConsequenceBinding:
        provisional = ArticulatoryConsequenceBinding(
            thing_id=mosaic.thing_id,
            program_id=attempt_custody.program_id,
            thing_mosaic_receipt_at_closure_sha256=(
                mosaic.authority_receipt_sha256
                if mosaic_receipt_at_closure_sha256 is None
                else _sha256(
                    mosaic_receipt_at_closure_sha256,
                    "THING mosaic at closure",
                )
            ),
            thing_partition_receipt_sha256=(
                partition.authority_receipt_sha256
            ),
            attempt_custody=attempt_custody,
            companion_episode_intent=companion_episode_intent,
            consequence_execution=consequence,
            consequence_execution_receipt_sha256=(
                consequence.authority_receipt_sha256
            ),
            consequence_before_receipt_sha256=(
                consequence.before.authority_receipt_sha256
            ),
            consequence_after_receipt_sha256=(
                consequence.after.authority_receipt_sha256
            ),
            consequence_port_id=consequence.port_id,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._binding_key,
            _BINDING_DOMAIN,
            provisional.payload(),
        )
        result = ArticulatoryConsequenceBinding(
            **{
                name: getattr(provisional, name)
                for name in (
                    "thing_id",
                    "program_id",
                    "thing_mosaic_receipt_at_closure_sha256",
                    "thing_partition_receipt_sha256",
                    "attempt_custody",
                    "companion_episode_intent",
                    "consequence_execution",
                    "consequence_execution_receipt_sha256",
                    "consequence_before_receipt_sha256",
                    "consequence_after_receipt_sha256",
                    "consequence_port_id",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_binding(result)
        return result

    def _body(
        self,
        bindings: tuple[ArticulatoryConsequenceBinding, ...],
    ) -> dict[str, object]:
        return {
            "bindings": [value.record() for value in bindings],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        bindings: tuple[ArticulatoryConsequenceBinding, ...],
    ) -> bytes:
        body = self._body(bindings)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key,
                _STATE_DOMAIN,
                body,
            ),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "articulatory consequence state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._bindings)

    def _verify_prepared(
        self,
        prepared: PreparedArticulatoryConsequenceClosure,
        *,
        require_live: bool,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedArticulatoryConsequenceClosure,
            )
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
        ):
            raise ValueError(
                "prepared articulatory consequence changed custody"
            )
        self._fresh.verify_receipt(prepared._attempt_custody)
        self._world.verify_execution_receipt(prepared._consequence)
        self._verify_binding(prepared._candidate_binding)
        for binding in (
            *prepared._prior_bindings,
            *prepared._staged_bindings,
        ):
            self._verify_binding(binding)
        if require_live:
            mosaic, partition = self._derive_live_relation(
                attempt_custody=prepared._attempt_custody,
                consequence=prepared._consequence,
                companion_episode_intent=(
                    prepared._companion_episode_intent
                ),
                require_current_world=True,
            )
            if (
                mosaic.thing_id != prepared._candidate_binding.thing_id
                or partition.authority_receipt_sha256
                != prepared._candidate_binding.thing_partition_receipt_sha256
                or prepared._attempt_custody.program_id
                != prepared._candidate_binding.program_id
            ):
                raise ValueError(
                    "prepared articulatory consequence changed relation"
                )
        if (
            not isinstance(prepared._changed, bool)
            or prepared._candidate_binding not in prepared._staged_bindings
            or (
                prepared._changed
                and prepared._staged_bindings
                != tuple(sorted(
                    (
                        *prepared._prior_bindings,
                        prepared._candidate_binding,
                    ),
                    key=lambda value: value.thing_id,
                ))
            )
            or (
                not prepared._changed
                and prepared._prior_bindings
                != prepared._staged_bindings
            )
        ):
            raise ValueError(
                "prepared articulatory consequence state changed"
            )
        self._encoded(prepared._prior_bindings)
        self._encoded(prepared._staged_bindings)
        signature = _sign(
            self._prepared_key,
            _PREPARED_DOMAIN,
            prepared.payload(),
        )
        if (
            not hmac.compare_digest(
                signature,
                prepared.authority_hmac_sha256,
            )
            or prepared.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": prepared.payload(),
            })
        ):
            raise ValueError(
                "prepared articulatory consequence authority changed"
            )

    def prepare(
        self,
        attempt_custody: FreshArticulatorySelfAcousticCustodyReceipt,
        consequence: ActionExecutionReceipt,
        *,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ) = None,
    ) -> PreparedArticulatoryConsequenceClosure:
        """Prepare one direct or authenticated companion-vocal closure."""

        mosaic, partition = self._derive_live_relation(
            attempt_custody=attempt_custody,
            consequence=consequence,
            companion_episode_intent=companion_episode_intent,
            require_current_world=True,
        )
        candidate = self._seal_binding(
            attempt_custody=attempt_custody,
            consequence=consequence,
            companion_episode_intent=companion_episode_intent,
            mosaic=mosaic,
            partition=partition,
        )
        with self._lock:
            prior = self._bindings
            same_thing = next(
                (
                    binding
                    for binding in prior
                    if binding.thing_id == candidate.thing_id
                ),
                None,
            )
            same_attempt = next(
                (
                    binding
                    for binding in prior
                    if binding.attempt_custody
                    .authority_receipt_sha256
                    == attempt_custody.authority_receipt_sha256
                ),
                None,
            )
            if same_thing is not None:
                if same_thing.program_id != candidate.program_id:
                    raise ValueError(
                        "one THING cannot gain conflicting articulatory "
                        "programs"
                    )
                binding = same_thing
                staged = prior
                changed = False
            elif same_attempt is not None:
                raise ValueError(
                    "one articulatory attempt cannot close another THING"
                )
            else:
                if len(prior) >= self._profile.max_bindings:
                    raise RuntimeError(
                        "articulatory consequence binding capacity exhausted"
                    )
                binding = candidate
                staged = tuple(sorted(
                    (*prior, binding),
                    key=lambda value: value.thing_id,
                ))
                changed = True
            self._encoded(staged)
            provisional = PreparedArticulatoryConsequenceClosure(
                _candidate_binding=binding,
                _attempt_custody=attempt_custody,
                _consequence=consequence,
                _companion_episode_intent=companion_episode_intent,
                _prior_bindings=prior,
                _staged_bindings=staged,
                _changed=changed,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _owner_authority=self._owner_authority,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            signature = _sign(
                self._prepared_key,
                _PREPARED_DOMAIN,
                provisional.payload(),
            )
            prepared = PreparedArticulatoryConsequenceClosure(
                _candidate_binding=provisional._candidate_binding,
                _attempt_custody=provisional._attempt_custody,
                _consequence=provisional._consequence,
                _companion_episode_intent=(
                    provisional._companion_episode_intent
                ),
                _prior_bindings=provisional._prior_bindings,
                _staged_bindings=provisional._staged_bindings,
                _changed=provisional._changed,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
                _owner_authority=self._owner_authority,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            self._verify_prepared(prepared, require_live=True)
            return prepared

    def verify_prepared(
        self,
        prepared: PreparedArticulatoryConsequenceClosure,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared, require_live=True)

    def _install_prepared(
        self,
        prepared: PreparedArticulatoryConsequenceClosure,
    ) -> None:
        self._encoded(prepared._staged_bindings)
        self._bindings = prepared._staged_bindings

    def commit_prepared(
        self,
        prepared: PreparedArticulatoryConsequenceClosure,
    ) -> CommittedArticulatoryConsequenceClosure:
        with self._lock:
            self._verify_prepared(prepared, require_live=True)
            if self._bindings == prepared._staged_bindings:
                undo = ArticulatoryConsequenceClosureUndo(
                    prior_bindings=self._bindings,
                    staged_bindings=self._bindings,
                    changed=False,
                    _owner_authority=self._owner_authority,
                )
                return CommittedArticulatoryConsequenceClosure(
                    binding=prepared._candidate_binding,
                    undo=undo,
                )
            if self._bindings != prepared._prior_bindings:
                raise RuntimeError(
                    "prepared articulatory consequence closure is stale"
                )
            prior = self._bindings
            try:
                self._install_prepared(prepared)
            except BaseException:
                self._bindings = prior
                raise
            undo = ArticulatoryConsequenceClosureUndo(
                prior_bindings=prior,
                staged_bindings=self._bindings,
                changed=prepared._changed,
                _owner_authority=self._owner_authority,
            )
            return CommittedArticulatoryConsequenceClosure(
                binding=prepared._candidate_binding,
                undo=undo,
            )

    def discard_prepared(
        self,
        prepared: PreparedArticulatoryConsequenceClosure,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared, require_live=False)

    def rollback_committed(
        self,
        undo: ArticulatoryConsequenceClosureUndo,
    ) -> None:
        if (
            not isinstance(undo, ArticulatoryConsequenceClosureUndo)
            or undo._owner_authority is not self._owner_authority
        ):
            raise ValueError(
                "articulatory consequence undo changed custody"
            )
        with self._lock:
            for binding in (
                *undo.prior_bindings,
                *undo.staged_bindings,
            ):
                self._verify_binding(binding)
            self._encoded(undo.prior_bindings)
            self._encoded(undo.staged_bindings)
            if not undo.changed:
                if self._bindings != undo.staged_bindings:
                    raise RuntimeError(
                        "articulatory consequence no-op undo is stale"
                    )
                return
            if self._bindings != undo.staged_bindings:
                raise RuntimeError(
                    "articulatory consequence undo is stale"
                )
            self._bindings = undo.prior_bindings

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "bindings": len(self._bindings),
                "max_bindings": self._profile.max_bindings,
                "profile_receipt_sha256": (
                    self._profile.authority_receipt_sha256
                ),
                "retained_pcm_bytes": 0,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(self._encoded(self._bindings)),
                "state_capacity_bytes": (
                    self._profile.max_state_bytes
                ),
            }

    def _migrate_legacy_direct_binding(
        self,
        raw: Mapping[str, object],
    ) -> ArticulatoryConsequenceBinding:
        expected = {
            "attempt_custody",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "consequence_execution",
            "consequence_after_receipt_sha256",
            "consequence_before_receipt_sha256",
            "consequence_execution_receipt_sha256",
            "consequence_port_id",
            "program_id",
            "schema",
            "thing_id",
            "thing_mosaic_receipt_at_closure_sha256",
            "thing_partition_receipt_sha256",
        }
        if set(raw) != expected or raw.get("schema") != _LEGACY_BINDING_SCHEMA:
            raise ValueError(
                "legacy articulatory consequence binding schema changed"
            )
        payload = {
            key: value
            for key, value in raw.items()
            if key not in {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
            }
        }
        signature = _sign(
            self._legacy_binding_key,
            _LEGACY_BINDING_DOMAIN,
            payload,
        )
        if (
            not hmac.compare_digest(
                signature,
                raw["authority_hmac_sha256"],
            )
            or raw["authority_receipt_sha256"]
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError(
                "legacy articulatory consequence binding authority changed"
            )
        attempt = fresh_articulatory_receipt_from_record(
            raw["attempt_custody"]
        )
        consequence = self._world.execution_receipt_from_record(
            raw["consequence_execution"]
        )
        mosaic, partition = self._mosaic_partition(
            thing_id=raw["thing_id"],
            partition_receipt_sha256=(
                raw["thing_partition_receipt_sha256"]
            ),
        )
        migrated = self._seal_binding(
            attempt_custody=attempt,
            consequence=consequence,
            companion_episode_intent=None,
            mosaic=mosaic,
            partition=partition,
            mosaic_receipt_at_closure_sha256=(
                raw["thing_mosaic_receipt_at_closure_sha256"]
            ),
        )
        migrated_payload = migrated.payload()
        expected_payload = {
            key: value
            for key, value in migrated_payload.items()
            if key not in {
                "causal_linkage",
                "companion_episode_intent",
            }
        }
        expected_payload["schema"] = _LEGACY_BINDING_SCHEMA
        if payload != expected_payload:
            raise ValueError(
                "legacy articulatory consequence binding relation changed"
            )
        return migrated

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: ArticulatoryConsequenceClosureProfile,
        encoded: bytes,
        fresh_custody_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        thing_owner: CausalThingMosaicOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
        companion_vocal_authority: W1CompanionVocalExperienceAuthority,
    ) -> "ArticulatoryConsequenceClosureOwner":
        profile.verify()
        if not isinstance(encoded, bytes):
            raise TypeError(
                "articulatory consequence snapshot must be bytes"
            )
        if not encoded or len(encoded) > profile.max_state_bytes:
            raise ValueError(
                "articulatory consequence snapshot exceeds capacity"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "articulatory consequence snapshot is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            not in {ENVELOPE_SCHEMA, _LEGACY_ENVELOPE_SCHEMA}
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "articulatory consequence snapshot envelope changed"
            )
        body = envelope["body"]
        legacy = envelope["schema"] == _LEGACY_ENVELOPE_SCHEMA
        expected_state_schema = (
            _LEGACY_STATE_SCHEMA if legacy else STATE_SCHEMA
        )
        if (
            not isinstance(body, dict)
            or set(body) != {"bindings", "profile", "schema"}
            or body.get("schema") != expected_state_schema
            or body.get("profile") != profile.record()
            or not isinstance(body.get("bindings"), list)
            or len(body["bindings"]) > profile.max_bindings
        ):
            raise ValueError(
                "articulatory consequence snapshot body changed"
            )
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            fresh_custody_authority=fresh_custody_authority,
            thing_owner=thing_owner,
            articulatory_owner=articulatory_owner,
            world_authority=world_authority,
            companion_vocal_authority=companion_vocal_authority,
        )
        expected_hmac = _sign(
            (
                owner._legacy_state_key
                if legacy
                else owner._state_key
            ),
            _LEGACY_STATE_DOMAIN if legacy else _STATE_DOMAIN,
            body,
        )
        if not hmac.compare_digest(
            expected_hmac,
            envelope["state_hmac_sha256"],
        ):
            raise ValueError(
                "articulatory consequence snapshot HMAC changed"
            )
        bindings = []
        for raw in body["bindings"]:
            if not isinstance(raw, dict):
                raise ValueError(
                    "articulatory consequence binding record changed"
                )
            if legacy:
                bindings.append(
                    owner._migrate_legacy_direct_binding(raw)
                )
                continue
            expected = {
                "attempt_custody",
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "causal_linkage",
                "companion_episode_intent",
                "consequence_execution",
                "consequence_after_receipt_sha256",
                "consequence_before_receipt_sha256",
                "consequence_execution_receipt_sha256",
                "consequence_port_id",
                "program_id",
                "schema",
                "thing_id",
                "thing_mosaic_receipt_at_closure_sha256",
                "thing_partition_receipt_sha256",
            }
            if set(raw) != expected or raw.get("schema") != BINDING_SCHEMA:
                raise ValueError(
                    "articulatory consequence binding schema changed"
                )
            binding = ArticulatoryConsequenceBinding(
                thing_id=raw["thing_id"],
                program_id=raw["program_id"],
                thing_mosaic_receipt_at_closure_sha256=(
                    raw["thing_mosaic_receipt_at_closure_sha256"]
                ),
                thing_partition_receipt_sha256=(
                    raw["thing_partition_receipt_sha256"]
                ),
                attempt_custody=fresh_articulatory_receipt_from_record(
                    raw["attempt_custody"]
                ),
                companion_episode_intent=(
                    None
                    if raw["companion_episode_intent"] is None
                    else companion_vocal_authority
                    .episode_intent_from_record(
                        raw["companion_episode_intent"]
                    )
                ),
                consequence_execution=(
                    world_authority.execution_receipt_from_record(
                        raw["consequence_execution"]
                    )
                ),
                consequence_execution_receipt_sha256=(
                    raw["consequence_execution_receipt_sha256"]
                ),
                consequence_before_receipt_sha256=(
                    raw["consequence_before_receipt_sha256"]
                ),
                consequence_after_receipt_sha256=(
                    raw["consequence_after_receipt_sha256"]
                ),
                consequence_port_id=raw["consequence_port_id"],
                authority_hmac_sha256=raw["authority_hmac_sha256"],
                authority_receipt_sha256=(
                    raw["authority_receipt_sha256"]
                ),
            )
            if raw["causal_linkage"] != binding.causal_linkage:
                raise ValueError(
                    "articulatory consequence causal linkage changed"
                )
            owner._verify_binding(binding)
            bindings.append(binding)
        restored = tuple(sorted(
            bindings,
            key=lambda value: value.thing_id,
        ))
        if (
            len({value.thing_id for value in restored})
            != len(restored)
            or tuple(bindings) != restored
        ):
            raise ValueError(
                "articulatory consequence snapshot binding order changed"
            )
        owner._bindings = restored
        if not legacy and owner.snapshot_encoded() != encoded:
            raise ValueError(
                "articulatory consequence cold restore changed state"
            )
        return owner


__all__ = (
    "BINDING_SCHEMA",
    "ENVELOPE_SCHEMA",
    "PREPARED_SCHEMA",
    "PROFILE_SCHEMA",
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
    "ArticulatoryConsequenceBinding",
    "ArticulatoryConsequenceClosureOwner",
    "ArticulatoryConsequenceClosureProfile",
    "ArticulatoryConsequenceClosureUndo",
    "CommittedArticulatoryConsequenceClosure",
    "PreparedArticulatoryConsequenceClosure",
)
