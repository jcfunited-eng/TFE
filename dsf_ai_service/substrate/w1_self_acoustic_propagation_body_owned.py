"""Body-owned extension for the W1 self-acoustic authority.

The mature durable-program transaction remains implemented by
``w1_self_acoustic_propagation_durable``.  This module is the authoritative
composition surface and adds one deliberately separate entrance for a
body-owned transient vocal act.  That entrance accepts no PCM, articulatory
coordinates, direction, program identity, or tutor-selected parameter.  It
accepts only an opaque live capability issued by the physical vocal-body
owner, verifies that capability against the current world edge, and then uses
the same binaural renderer, canonical L0--L4 construction, exact causal
settlement, W1 L5, receptor settlement, and recurrent-q owners as the durable
path.

The transient entrance cannot admit or return an ``ArticulatoryProgram`` and
retains no raw pressure after commit.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from dsf_ai_service.substrate.w1_self_acoustic_propagation_durable import (
    PreparedW1SelfAcousticMount,
    W1ArticulatorySelfAcousticCommitUndo,
    W1PreparedArticulatoryCommitment,
    W1SelfAcousticMount,
    W1SelfAcousticPropagationAuthority as _DurableAuthority,
    W1SelfAcousticReceipt,
    W1SelfAcousticState,
    W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA,
    _EmissionReceiptCommitment,
    _PreparedEmissionView,
)


W1_BODY_TRANSIENT_COMMITMENT_SCHEMA = (
    "guala.w1.body_owned_transient_self_acoustic.commitment.v1"
)
_BODY_TRANSIENT_DOMAIN = (
    b"guala-w1-body-owned-transient-self-acoustic-v1\0"
)
_PREPARED_BODY_TRANSIENT_AUTHORITY = object()
_BODY_TRANSIENT_UNDO_AUTHORITY = object()
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


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class BodyOwnedTransientW1Commitment:
    """Hash-only result of complete body-owned self-hearing custody."""

    transient_act_receipt_sha256: str
    pressure_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    mount_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    receptor_settlement_receipt_sha256: str
    recurrent_q_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "mount_receipt_sha256": self.mount_receipt_sha256,
            "pressure_sha256": self.pressure_sha256,
            "receptor_settlement_receipt_sha256": (
                self.receptor_settlement_receipt_sha256
            ),
            "recurrent_q_receipt_sha256": (
                self.recurrent_q_receipt_sha256
            ),
            "schema": W1_BODY_TRANSIENT_COMMITMENT_SCHEMA,
            "transient_act_receipt_sha256": (
                self.transient_act_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes) -> None:
        for value, name in (
            (self.transient_act_receipt_sha256, "transient vocal act"),
            (self.pressure_sha256, "transient vocal pressure"),
            (self.world_before_receipt_sha256, "world before"),
            (self.world_after_receipt_sha256, "world after"),
            (self.world_execution_receipt_sha256, "world execution"),
            (self.mount_receipt_sha256, "self-acoustic mount"),
            (self.causal_settlement_receipt_sha256, "causal settlement"),
            (self.binaural_l5_receipt_sha256, "binaural L5"),
            (self.receptor_settlement_receipt_sha256, "receptors"),
            (self.recurrent_q_receipt_sha256, "recurrent q"),
            (self.authority_hmac_sha256, "transient commitment HMAC"),
            (self.authority_receipt_sha256, "transient commitment"),
        ):
            _sha256(value, name)
        signature = hmac.new(
            authority_key,
            _BODY_TRANSIENT_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError(
                "body-owned transient W1 commitment changed"
            )


@dataclass(frozen=True, slots=True)
class PreparedBodyOwnedW1SelfAcousticMount:
    """Opaque staged full-field custody for one live body capability."""

    prepared_transient: object
    _sensory: object = field(repr=False, compare=False)
    _vocal_body_owner: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(slots=True)
class _BodyTransientUndoState:
    causal_undo: object | None = None
    l5_undo: object | None = None
    motif_undo: object | None = None
    sealed: bool = False
    rolled_back: bool = False


@dataclass(frozen=True, slots=True)
class BodyOwnedW1CommitUndo:
    """Opaque exact rollback authority for one current transient act."""

    _prepared_world_action: object = field(repr=False, compare=False)
    _vocal_body_owner: object = field(repr=False, compare=False)
    _vocal_body_undo: object = field(repr=False, compare=False)
    _state: _BodyTransientUndoState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class W1SelfAcousticPropagationAuthority(_DurableAuthority):
    """Preserve durable contracts and add sealed body-owned transient acts."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._prepared_body_transient: (
            PreparedBodyOwnedW1SelfAcousticMount | None
        ) = None
        self._body_transient_undo_owner = object()
        self._body_transient_gate = threading.RLock()

    def prepare_articulatory(
        self,
        prepared_emission,
        *,
        articulatory_owner,
    ) -> PreparedW1SelfAcousticMount:
        with self._body_transient_gate:
            if self._prepared_body_transient is not None:
                raise RuntimeError(
                    "body-owned transient self-hearing is already prepared"
                )
            return super().prepare_articulatory(
                prepared_emission,
                articulatory_owner=articulatory_owner,
            )

    def _require_body_transient_locked(
        self,
        prepared: PreparedBodyOwnedW1SelfAcousticMount,
    ) -> PreparedBodyOwnedW1SelfAcousticMount:
        from dsf_ai_service.substrate.embodied_vocal_body import (
            EmbodiedVocalBodyAuthority,
        )

        if (
            not isinstance(
                prepared,
                PreparedBodyOwnedW1SelfAcousticMount,
            )
            or prepared._construction_authority
            is not _PREPARED_BODY_TRANSIENT_AUTHORITY
            or self._prepared_body_transient is not prepared
            or not isinstance(
                prepared._vocal_body_owner,
                EmbodiedVocalBodyAuthority,
            )
        ):
            raise ValueError(
                "prepared body-owned W1 custody changed"
            )
        prepared._vocal_body_owner.verify_prepared_transient(
            prepared.prepared_transient
        )
        prepared._sensory.mount.verify(self._key)
        if (
            prepared._sensory.mount.receipt
            .self_vocal_emission_receipt_sha256
            != prepared.prepared_transient
            .prospective_act_receipt_sha256
        ):
            raise ValueError(
                "body-owned W1 custody lost transient act authority"
            )
        return prepared

    def prepare_body_owned_transient(
        self,
        prepared_transient,
        *,
        vocal_body_owner,
    ) -> PreparedBodyOwnedW1SelfAcousticMount:
        """Stage self-hearing from an opaque body act, never raw pressure."""

        from dsf_ai_service.substrate.embodied_vocal_body import (
            EmbodiedVocalBodyAuthority,
            PreparedBodyOwnedTransientAct,
        )

        if not isinstance(
            vocal_body_owner,
            EmbodiedVocalBodyAuthority,
        ):
            raise TypeError(
                "transient self-hearing requires its vocal-body owner"
            )
        if not isinstance(
            prepared_transient,
            PreparedBodyOwnedTransientAct,
        ):
            raise TypeError(
                "transient self-hearing requires body-owned custody"
            )
        if not vocal_body_owner.owns_world(self._world):
            raise ValueError(
                "transient vocal body belongs to another world"
            )
        with self._body_transient_gate, self._lock:
            if (
                self._prepared_body_transient is not None
                or self._prepared_articulatory is not None
            ):
                raise RuntimeError(
                    "W1 self-acoustic custody is already prepared"
                )
            sensory = None
            try:
                vocal_body_owner.verify_prepared_transient(
                    prepared_transient
                )
                emission = _PreparedEmissionView(
                    execution_receipt=(
                        prepared_transient.prepared_world_action
                        .execution_receipt
                    ),
                    pcm_s16le=prepared_transient._pcm_s16le,
                    emission_receipt=_EmissionReceiptCommitment(
                        prepared_transient
                        .prospective_act_receipt_sha256
                    ),
                )
                sensory = self._prepare_verified_sensory(
                    emission=emission,
                    motor_id=prepared_transient.transient_act_id,
                    verify=lambda: (
                        vocal_body_owner.verify_prepared_transient(
                            prepared_transient
                        )
                    ),
                )
                result = PreparedBodyOwnedW1SelfAcousticMount(
                    prepared_transient=prepared_transient,
                    _sensory=sensory,
                    _vocal_body_owner=vocal_body_owner,
                    _construction_authority=(
                        _PREPARED_BODY_TRANSIENT_AUTHORITY
                    ),
                )
                self._prepared_body_transient = result
                self._require_body_transient_locked(result)
                return result
            except BaseException:
                if sensory is not None:
                    self._discard_unpublished_sensory(sensory)
                vocal_body_owner.discard_prepared_transient(
                    prepared_transient
                )
                self._prepared_body_transient = None
                raise

    def commit_body_owned_transient(
        self,
        prepared: PreparedBodyOwnedW1SelfAcousticMount,
    ) -> tuple[
        BodyOwnedTransientW1Commitment,
        BodyOwnedW1CommitUndo,
    ]:
        """Atomically publish world, full self-hearing, and body mechanics."""

        with self._body_transient_gate, self._lock:
            current = self._require_body_transient_locked(prepared)
            sensory = current._sensory
            transient = current.prepared_transient
            execution = transient.prepared_world_action.execution_receipt
            state = _BodyTransientUndoState()
            vocal_install = (
                current._vocal_body_owner
                .preverify_transient_visibility_install(transient)
            )
            causal_install = (
                self._causal.preverify_atomic_visibility_install(
                    sensory.causal_sequence_token
                )
            )
            l5_install = self._l5.preverify_atomic_visibility_install(
                sensory.l5_sequence_token
            )
            motif_install = (
                self._motif.preverify_binaural_visibility_install(
                    sensory.motif_preparation
                )
            )
            world_committed = False
            vocal_undo = None
            try:
                with (
                    current._vocal_body_owner
                    .transient_visibility_transaction(
                        vocal_install
                    ) as install_vocal,
                    self._world.prepared_action_visibility_transaction(
                        transient.prepared_world_action
                    ),
                    self._causal.atomic_visibility_transaction(
                        causal_install
                    ) as install_causal,
                    self._l5.atomic_visibility_transaction(
                        l5_install
                    ) as install_l5,
                    self._motif.binaural_visibility_transaction(
                        motif_install
                    ) as install_motif,
                ):
                    vocal_undo = install_vocal()
                    world_committed = True
                    state.causal_undo = install_causal()
                    state.l5_undo = install_l5()
                    state.motif_undo = install_motif()
                    self._prepared_body_transient = None
                    state.sealed = True
            except BaseException:
                assert not world_committed
                self._discard_unpublished_sensory(sensory)
                current._vocal_body_owner.discard_prepared_transient(
                    transient
                )
                self._prepared_body_transient = None
                raise
            mount = sensory.mount
            provisional = BodyOwnedTransientW1Commitment(
                transient_act_receipt_sha256=(
                    transient.prospective_act_receipt_sha256
                ),
                pressure_sha256=transient.pressure_sha256,
                world_before_receipt_sha256=(
                    execution.before.authority_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    execution.after.authority_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    execution.authority_receipt_sha256
                ),
                mount_receipt_sha256=(
                    mount.receipt.authority_receipt_sha256
                ),
                causal_settlement_receipt_sha256=(
                    mount.causal_settlement
                    .authority_receipt_sha256
                ),
                binaural_l5_receipt_sha256=(
                    mount.binaural_l5.authority_receipt_sha256
                ),
                receptor_settlement_receipt_sha256=(
                    mount.receptor_settlement
                    .authority_receipt_sha256
                ),
                recurrent_q_receipt_sha256=(
                    mount.observation.authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._key,
                _BODY_TRANSIENT_DOMAIN
                + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            commitment = BodyOwnedTransientW1Commitment(
                **{
                    name: getattr(provisional, name)
                    for name in (
                        "transient_act_receipt_sha256",
                        "pressure_sha256",
                        "world_before_receipt_sha256",
                        "world_after_receipt_sha256",
                        "world_execution_receipt_sha256",
                        "mount_receipt_sha256",
                        "causal_settlement_receipt_sha256",
                        "binaural_l5_receipt_sha256",
                        "receptor_settlement_receipt_sha256",
                        "recurrent_q_receipt_sha256",
                    )
                },
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            commitment.verify(self._key)
            undo = BodyOwnedW1CommitUndo(
                _prepared_world_action=(
                    transient.prepared_world_action
                ),
                _vocal_body_owner=current._vocal_body_owner,
                _vocal_body_undo=vocal_undo,
                _state=state,
                _owner_authority=self._body_transient_undo_owner,
                _construction_authority=(
                    _BODY_TRANSIENT_UNDO_AUTHORITY
                ),
            )
            return commitment, undo

    def rollback_body_owned_transient(
        self,
        undo: BodyOwnedW1CommitUndo,
    ) -> None:
        """Undo the latest body mechanics, world act, and sensory custody."""

        with self._body_transient_gate, self._lock:
            if (
                not isinstance(undo, BodyOwnedW1CommitUndo)
                or undo._construction_authority
                is not _BODY_TRANSIENT_UNDO_AUTHORITY
                or undo._owner_authority
                is not self._body_transient_undo_owner
                or not undo._state.sealed
                or undo._state.rolled_back
                or undo._state.causal_undo is None
                or undo._state.l5_undo is None
                or undo._state.motif_undo is None
                or self._prepared_body_transient is not None
                or self._prepared_articulatory is not None
            ):
                raise ValueError(
                    "body-owned W1 rollback authority changed"
                )
            state = undo._state
            with (
                self._world
                .committed_prepared_action_rollback_transaction(
                    undo._prepared_world_action
                ) as rollback_world,
                self._causal
                .committed_atomic_sequence_rollback_transaction(
                    state.causal_undo
                ) as rollback_causal,
                self._l5
                .committed_atomic_sequence_rollback_transaction(
                    state.l5_undo
                ) as rollback_l5,
                self._motif
                .committed_binaural_rollback_transaction(
                    state.motif_undo
                ) as rollback_motif,
                undo._vocal_body_owner
                .committed_transient_rollback_transaction(
                    undo._vocal_body_undo
                ) as rollback_vocal,
            ):
                rollback_motif()
                rollback_l5()
                rollback_causal()
                rollback_world()
                rollback_vocal()
                state.rolled_back = True

    def discard_body_owned_transient(
        self,
        prepared: PreparedBodyOwnedW1SelfAcousticMount,
    ) -> None:
        with self._body_transient_gate, self._lock:
            current = self._require_body_transient_locked(prepared)
            self._discard_unpublished_sensory(current._sensory)
            current._vocal_body_owner.discard_prepared_transient(
                current.prepared_transient
            )
            self._prepared_body_transient = None


__all__ = [
    "BodyOwnedTransientW1Commitment",
    "BodyOwnedW1CommitUndo",
    "PreparedBodyOwnedW1SelfAcousticMount",
    "PreparedW1SelfAcousticMount",
    "W1ArticulatorySelfAcousticCommitUndo",
    "W1PreparedArticulatoryCommitment",
    "W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA",
    "W1_BODY_TRANSIENT_COMMITMENT_SCHEMA",
    "W1SelfAcousticMount",
    "W1SelfAcousticPropagationAuthority",
    "W1SelfAcousticReceipt",
    "W1SelfAcousticState",
]
