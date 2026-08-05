"""Bounded custody for one unresolved articulatory causal attempt.

This owner retains at most one authenticated fresh self-acoustic receipt.
It never retains pressure, PCM, a waveform, a semantic identifier, a
selection cursor, or a time-derived expiry.  Liveness is the exact current
W1 world receipt and the unique current causal THING tail.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

from dsf_ai_service.substrate.articulatory_consequence_closure import (
    ArticulatoryConsequenceBinding,
    ArticulatoryConsequenceClosureOwner,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FreshArticulatorySelfAcousticCustodyAuthority,
    FreshArticulatorySelfAcousticCustodyReceipt,
)


PROFILE_SCHEMA = (
    "guala.pending_articulatory_causal_attempt.profile.v1"
)
PREPARED_SCHEMA = (
    "guala.pending_articulatory_causal_attempt.prepared.v1"
)
STATE_SCHEMA = (
    "guala.pending_articulatory_causal_attempt.state.v1"
)
ENVELOPE_SCHEMA = (
    "guala.pending_articulatory_causal_attempt.state_hmac.v1"
)
STATUS_SCHEMA = (
    "guala.pending_articulatory_causal_attempt.status.v1"
)

_PREPARED_DOMAIN = (
    b"guala-pending-articulatory-causal-attempt-prepared-v1\0"
)
_STATE_DOMAIN = (
    b"guala-pending-articulatory-causal-attempt-state-v1\0"
)
_MAX_PROFILE_ID_BYTES = 256
_MAX_CONFIGURED_STATE_BYTES = 4 * 1024 * 1024
_HEX = frozenset("0123456789abcdef")
_PREPARED_CONSTRUCTION_AUTHORITY = object()
_UNDO_CONSTRUCTION_AUTHORITY = object()


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
            "pending articulatory attempt authority key changed type"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "pending articulatory attempt authority key boundary changed"
        )
    return result


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > _MAX_PROFILE_ID_BYTES
    ):
        raise ValueError(f"{name} changed")
    return value


def _capacity(value: object, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= _MAX_CONFIGURED_STATE_BYTES
    ):
        raise ValueError(f"{name} changed")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} changed")
    return value


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PendingArticulatoryCausalAttemptProfile:
    profile_id: str
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_state_bytes: int,
    ) -> "PendingArticulatoryCausalAttemptProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id,
                "pending articulatory attempt profile",
            ),
            max_state_bytes=_capacity(
                max_state_bytes,
                "pending articulatory attempt state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_pending_attempts": 1,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(
            self.profile_id,
            "pending articulatory attempt profile",
        )
        _capacity(
            self.max_state_bytes,
            "pending articulatory attempt state capacity",
        )
        if self.authority_receipt_sha256 != _digest(
            self.payload()
        ):
            raise ValueError(
                "pending articulatory attempt profile authority changed"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(slots=True)
class _PendingMutationState:
    phase: str


@dataclass(frozen=True, slots=True)
class PreparedPendingArticulatoryCausalAttempt:
    operation: str
    attempt_custody: FreshArticulatorySelfAcousticCustodyReceipt
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _prior_attempt: (
        FreshArticulatorySelfAcousticCustodyReceipt | None
    ) = field(repr=False)
    _staged_attempt: (
        FreshArticulatorySelfAcousticCustodyReceipt | None
    ) = field(repr=False)
    _transaction_state: _PendingMutationState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )

    def payload(self) -> dict[str, object]:
        return {
            "attempt_custody_receipt_sha256": (
                self.attempt_custody.authority_receipt_sha256
            ),
            "operation": self.operation,
            "prior_attempt_receipt_sha256": (
                self._prior_attempt.authority_receipt_sha256
                if self._prior_attempt is not None
                else None
            ),
            "schema": PREPARED_SCHEMA,
            "staged_attempt_receipt_sha256": (
                self._staged_attempt.authority_receipt_sha256
                if self._staged_attempt is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class PendingArticulatoryCausalAttemptUndo:
    operation: str
    _prepared: PreparedPendingArticulatoryCausalAttempt = field(
        repr=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


class PendingArticulatoryAttemptCapacityError(RuntimeError):
    """The sole pending-attempt slot is occupied."""


class PendingArticulatoryAttemptStaleError(ValueError):
    """The pending attempt is no longer the current world edge."""


@dataclass(frozen=True, slots=True)
class PendingArticulatoryExplorationRead:
    """One lock-held exact owner snapshot for a stateless decision."""

    retained_programs: tuple[ArticulatoryProgram, ...]
    closed_program_ids: frozenset[str]
    active_pending_attempt: bool


class PendingArticulatoryCausalAttemptOwner:
    """Own exactly zero or one unresolved, media-free attempt receipt."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: PendingArticulatoryCausalAttemptProfile,
        fresh_custody_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        thing_owner: CausalThingMosaicOwner,
        world_authority: EmbodimentWorldAuthority,
        consequence_closure_owner: (
            ArticulatoryConsequenceClosureOwner
        ),
    ) -> None:
        if not isinstance(
            profile,
            PendingArticulatoryCausalAttemptProfile,
        ):
            raise TypeError(
                "pending articulatory attempt requires its profile"
            )
        profile.verify()
        if not isinstance(
            fresh_custody_authority,
            FreshArticulatorySelfAcousticCustodyAuthority,
        ):
            raise TypeError(
                "pending articulatory attempt requires fresh custody"
            )
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "pending articulatory attempt requires its THING owner"
            )
        if not isinstance(
            world_authority,
            EmbodimentWorldAuthority,
        ):
            raise TypeError(
                "pending articulatory attempt requires its W1 world"
            )
        if not isinstance(
            consequence_closure_owner,
            ArticulatoryConsequenceClosureOwner,
        ):
            raise TypeError(
                "pending articulatory attempt requires consequence closure"
            )
        fresh_custody_authority.verify_world_ownership(
            world_authority
        )
        if (
            consequence_closure_owner._fresh
            is not fresh_custody_authority
            or consequence_closure_owner._things is not thing_owner
            or consequence_closure_owner._world is not world_authority
        ):
            raise ValueError(
                "pending articulatory attempt crossed consequence closure "
                "ownership"
            )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root
        ).digest()
        self._profile = profile
        self._fresh = fresh_custody_authority
        self._things = thing_owner
        self._world = world_authority
        self._closure = consequence_closure_owner
        self._pending: (
            FreshArticulatorySelfAcousticCustodyReceipt | None
        ) = None
        self._prepared: (
            PreparedPendingArticulatoryCausalAttempt | None
        ) = None
        self._owner_authority = object()
        self._lock = threading.RLock()
        self._encoded(None)

    @property
    def pending_attempt(
        self,
    ) -> FreshArticulatorySelfAcousticCustodyReceipt | None:
        with self._lock:
            return self._pending

    def verify_articulatory_exploration_owners(
        self,
        *,
        motor_owner: ArticulatorySelfVocalMotorOwner,
        consequence_closure_owner: (
            ArticulatoryConsequenceClosureOwner
        ),
    ) -> None:
        """Require the exact motor/closure graph owned by this custody slot."""

        if not isinstance(
            motor_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "pending exploration ownership requires articulation"
            )
        if not isinstance(
            consequence_closure_owner,
            ArticulatoryConsequenceClosureOwner,
        ):
            raise TypeError(
                "pending exploration ownership requires consequence closure"
            )
        if (
            self._closure is not consequence_closure_owner
            or consequence_closure_owner._articulatory
            is not motor_owner
        ):
            raise ValueError(
                "pending exploration crossed exact owner custody"
            )

    @contextmanager
    def articulatory_exploration_read_transaction(
        self,
        *,
        motor_owner: ArticulatorySelfVocalMotorOwner,
        consequence_closure_owner: (
            ArticulatoryConsequenceClosureOwner
        ),
    ):
        """Hold all three owners stable for one componentwise decision.

        The fixed pending -> closure -> motor lock order prevents an arm,
        consequence closure, or program admission from crossing the snapshot.
        No state is retained after the context exits.
        """

        self.verify_articulatory_exploration_owners(
            motor_owner=motor_owner,
            consequence_closure_owner=consequence_closure_owner,
        )
        with (
            self._lock,
            consequence_closure_owner._lock,
            motor_owner._lock,
        ):
            yield PendingArticulatoryExplorationRead(
                retained_programs=motor_owner.programs,
                closed_program_ids=frozenset(
                    binding.program_id
                    for binding in consequence_closure_owner.bindings
                ),
                active_pending_attempt=(
                    self._pending is not None
                    or self._prepared is not None
                ),
            )

    def _live_tail(
        self,
        attempt: FreshArticulatorySelfAcousticCustodyReceipt,
    ):
        self._fresh.verify_receipt(attempt)
        current = self._world.observation_snapshot()
        if (
            current.authority_receipt_sha256
            != attempt.world_after_receipt_sha256
        ):
            raise PendingArticulatoryAttemptStaleError(
                "pending articulatory attempt world receipt is stale"
            )
        matches = tuple(
            (mosaic, mosaic.partitions[-1])
            for mosaic in self._things.mosaics
            if mosaic.partitions
            and mosaic.partitions[-1].source_occurrence_id
            == attempt.source_occurrence_id
            and mosaic.partitions[-1]
            .parent_custody_receipt_sha256
            == attempt.parent_settled_custody_receipt_sha256
            and mosaic.partitions[-1]
            .settlement_receipt_sha256
            == attempt.acoustic_settlement_receipt_sha256
            and mosaic.partitions[-1].execution_receipt_sha256
            == attempt.world_execution_receipt_sha256
            and mosaic.partitions[-1]
            .world_observation_receipt_sha256
            == attempt.world_after_receipt_sha256
            and mosaic.partitions[-1].world_revision
            == current.revision
        )
        if len(matches) != 1:
            raise ValueError(
                "pending articulatory attempt does not resolve one "
                "current THING tail"
            )
        return matches[0]

    def verify_live_attempt(
        self,
        attempt: FreshArticulatorySelfAcousticCustodyReceipt,
    ) -> None:
        """Authenticate the exact current world/THING receipt chain."""

        with self._lock:
            self._live_tail(attempt)

    def _body(
        self,
        pending: (
            FreshArticulatorySelfAcousticCustodyReceipt | None
        ),
    ) -> dict[str, object]:
        return {
            "pending_attempt": (
                pending.record() if pending is not None else None
            ),
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        pending: (
            FreshArticulatorySelfAcousticCustodyReceipt | None
        ),
    ) -> bytes:
        if pending is not None:
            self._fresh.verify_receipt(pending)
        body = self._body(pending)
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
                "pending articulatory attempt state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._pending)

    def _prepare(
        self,
        *,
        operation: str,
        attempt: FreshArticulatorySelfAcousticCustodyReceipt,
        prior: FreshArticulatorySelfAcousticCustodyReceipt | None,
        staged: FreshArticulatorySelfAcousticCustodyReceipt | None,
    ) -> PreparedPendingArticulatoryCausalAttempt:
        if self._prepared is not None:
            raise RuntimeError(
                "pending articulatory attempt transaction is active"
            )
        self._live_tail(attempt)
        self._encoded(prior)
        self._encoded(staged)
        provisional = PreparedPendingArticulatoryCausalAttempt(
            operation=operation,
            attempt_custody=attempt,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _prior_attempt=prior,
            _staged_attempt=staged,
            _transaction_state=_PendingMutationState(
                phase="prepared"
            ),
            _owner_authority=self._owner_authority,
            _construction_authority=(
                _PREPARED_CONSTRUCTION_AUTHORITY
            ),
        )
        signature = _sign(
            self._prepared_key,
            _PREPARED_DOMAIN,
            provisional.payload(),
        )
        prepared = PreparedPendingArticulatoryCausalAttempt(
            operation=provisional.operation,
            attempt_custody=provisional.attempt_custody,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _prior_attempt=provisional._prior_attempt,
            _staged_attempt=provisional._staged_attempt,
            _transaction_state=provisional._transaction_state,
            _owner_authority=self._owner_authority,
            _construction_authority=(
                _PREPARED_CONSTRUCTION_AUTHORITY
            ),
        )
        self._prepared = prepared
        self._verify_prepared(
            prepared,
            operation=operation,
            require_current=True,
            require_live=True,
        )
        return prepared

    def prepare_arm(
        self,
        attempt: FreshArticulatorySelfAcousticCustodyReceipt,
    ) -> PreparedPendingArticulatoryCausalAttempt:
        """Preflight one fresh attempt into the sole pending slot."""

        with self._lock:
            if self._pending is not None:
                raise PendingArticulatoryAttemptCapacityError(
                    "pending articulatory attempt capacity exhausted"
                )
            return self._prepare(
                operation="arm",
                attempt=attempt,
                prior=None,
                staged=attempt,
            )

    def prepare_consume(
        self,
    ) -> PreparedPendingArticulatoryCausalAttempt:
        """Preflight removal while the pending attempt is still current."""

        with self._lock:
            if self._pending is None:
                raise ValueError(
                    "pending articulatory attempt is unavailable"
                )
            return self._prepare(
                operation="consume",
                attempt=self._pending,
                prior=self._pending,
                staged=None,
            )

    def _verify_prepared(
        self,
        prepared: PreparedPendingArticulatoryCausalAttempt,
        *,
        operation: str,
        require_current: bool,
        require_live: bool,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedPendingArticulatoryCausalAttempt,
            )
            or prepared._construction_authority
            is not _PREPARED_CONSTRUCTION_AUTHORITY
            or prepared._owner_authority
            is not self._owner_authority
            or prepared.operation != operation
            or prepared._transaction_state.phase != "prepared"
            or (
                require_current
                and self._prepared is not prepared
            )
        ):
            raise ValueError(
                "prepared pending articulatory attempt changed custody"
            )
        self._fresh.verify_receipt(prepared.attempt_custody)
        if require_live:
            self._live_tail(prepared.attempt_custody)
        if (
            (operation == "arm" and (
                prepared._prior_attempt is not None
                or prepared._staged_attempt
                != prepared.attempt_custody
            ))
            or (operation == "consume" and (
                prepared._prior_attempt
                != prepared.attempt_custody
                or prepared._staged_attempt is not None
            ))
            or self._pending != prepared._prior_attempt
        ):
            raise ValueError(
                "prepared pending articulatory attempt changed state"
            )
        self._encoded(prepared._prior_attempt)
        self._encoded(prepared._staged_attempt)
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
                "prepared pending articulatory attempt authority changed"
            )

    def _commit(
        self,
        prepared: PreparedPendingArticulatoryCausalAttempt,
        *,
        operation: str,
    ) -> PendingArticulatoryCausalAttemptUndo:
        with self._lock:
            self._verify_prepared(
                prepared,
                operation=operation,
                require_current=True,
                require_live=True,
            )
            self._pending = prepared._staged_attempt
            self._prepared = None
            prepared._transaction_state.phase = "committed"
            return PendingArticulatoryCausalAttemptUndo(
                operation=operation,
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=(
                    _UNDO_CONSTRUCTION_AUTHORITY
                ),
            )

    def commit_prepared_arm(
        self,
        prepared: PreparedPendingArticulatoryCausalAttempt,
    ) -> PendingArticulatoryCausalAttemptUndo:
        return self._commit(prepared, operation="arm")

    def commit_prepared_consume(
        self,
        prepared: PreparedPendingArticulatoryCausalAttempt,
        *,
        binding: ArticulatoryConsequenceBinding,
    ) -> PendingArticulatoryCausalAttemptUndo:
        with self._lock:
            self._verify_prepared(
                prepared,
                operation="consume",
                require_current=True,
                require_live=False,
            )
            self._closure.verify_binding(binding)
            if (
                binding.attempt_custody
                != prepared.attempt_custody
                or self._world.observation_snapshot()
                != binding.consequence_execution.after
            ):
                raise ValueError(
                    "pending articulatory attempt consequence witness "
                    "changed"
                )
            self._pending = prepared._staged_attempt
            self._prepared = None
            prepared._transaction_state.phase = "committed"
            return PendingArticulatoryCausalAttemptUndo(
                operation="consume",
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=(
                    _UNDO_CONSTRUCTION_AUTHORITY
                ),
            )

    def discard_prepared(
        self,
        prepared: PreparedPendingArticulatoryCausalAttempt,
    ) -> None:
        with self._lock:
            self._verify_prepared(
                prepared,
                operation=prepared.operation,
                require_current=True,
                require_live=False,
            )
            self._prepared = None
            prepared._transaction_state.phase = "discarded"

    def _rollback(
        self,
        undo: PendingArticulatoryCausalAttemptUndo,
        *,
        operation: str,
    ) -> None:
        if (
            not isinstance(
                undo,
                PendingArticulatoryCausalAttemptUndo,
            )
            or undo._construction_authority
            is not _UNDO_CONSTRUCTION_AUTHORITY
            or undo._owner_authority is not self._owner_authority
            or undo.operation != operation
        ):
            raise ValueError(
                "pending articulatory attempt undo changed custody"
            )
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority
                is not self._owner_authority
                or prepared.operation != operation
                or prepared._transaction_state.phase != "committed"
                or self._pending != prepared._staged_attempt
                or self._prepared is not None
            ):
                raise ValueError(
                    "pending articulatory attempt undo changed state"
                )
            if prepared._prior_attempt is not None:
                self._live_tail(prepared._prior_attempt)
            self._encoded(prepared._prior_attempt)
            self._pending = prepared._prior_attempt
            prepared._transaction_state.phase = "rolled_back"

    def rollback_committed_arm(
        self,
        undo: PendingArticulatoryCausalAttemptUndo,
    ) -> None:
        self._rollback(undo, operation="arm")

    def rollback_committed_consume(
        self,
        undo: PendingArticulatoryCausalAttemptUndo,
    ) -> None:
        self._rollback(undo, operation="consume")

    def invalidate_stale_world_attempt(self) -> bool:
        """Clear only a receipt whose exact world-after is no longer current."""

        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "pending articulatory attempt transaction is active"
                )
            if self._pending is None:
                return False
            current = self._world.observation_snapshot()
            if (
                current.authority_receipt_sha256
                == self._pending.world_after_receipt_sha256
            ):
                self._live_tail(self._pending)
                return False
            self._pending = None
            return True

    def status(self) -> dict[str, object]:
        with self._lock:
            current = self._world.observation_snapshot()
            stale = (
                self._pending is not None
                and current.authority_receipt_sha256
                != self._pending.world_after_receipt_sha256
            )
            return {
                "capacity": 1,
                "pending": int(self._pending is not None),
                "prepared": int(self._prepared is not None),
                "retained_pcm_bytes": 0,
                "schema": STATUS_SCHEMA,
                "stale_world": stale,
                "state_bytes": len(self._encoded(self._pending)),
                "state_capacity_bytes": (
                    self._profile.max_state_bytes
                ),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: PendingArticulatoryCausalAttemptProfile,
        encoded: bytes,
        fresh_custody_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        thing_owner: CausalThingMosaicOwner,
        world_authority: EmbodimentWorldAuthority,
        consequence_closure_owner: (
            ArticulatoryConsequenceClosureOwner
        ),
    ) -> "PendingArticulatoryCausalAttemptOwner":
        if not isinstance(encoded, bytes):
            raise TypeError(
                "pending articulatory attempt snapshot must be bytes"
            )
        if len(encoded) > profile.max_state_bytes:
            raise ValueError(
                "pending articulatory attempt snapshot exceeds capacity"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "pending articulatory attempt snapshot is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), dict)
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "pending articulatory attempt envelope changed"
            )
        body = envelope["body"]
        if (
            set(body) != {"pending_attempt", "profile", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
        ):
            raise ValueError(
                "pending articulatory attempt state changed"
            )
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            fresh_custody_authority=fresh_custody_authority,
            thing_owner=thing_owner,
            world_authority=world_authority,
            consequence_closure_owner=consequence_closure_owner,
        )
        expected = _sign(
            owner._state_key,
            _STATE_DOMAIN,
            body,
        )
        if not hmac.compare_digest(
            expected,
            str(envelope.get("state_hmac_sha256", "")),
        ):
            raise ValueError(
                "pending articulatory attempt snapshot HMAC changed"
            )
        raw_pending = body["pending_attempt"]
        if raw_pending is None:
            pending = None
        else:
            pending = fresh_custody_authority.receipt_from_record(
                raw_pending
            )
            owner._live_tail(pending)
        owner._pending = pending
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "pending articulatory attempt cold restore changed state"
            )
        return owner


__all__ = (
    "ENVELOPE_SCHEMA",
    "PREPARED_SCHEMA",
    "PROFILE_SCHEMA",
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
    "PendingArticulatoryAttemptCapacityError",
    "PendingArticulatoryAttemptStaleError",
    "PendingArticulatoryCausalAttemptOwner",
    "PendingArticulatoryCausalAttemptProfile",
    "PendingArticulatoryCausalAttemptUndo",
    "PendingArticulatoryExplorationRead",
    "PreparedPendingArticulatoryCausalAttempt",
)
