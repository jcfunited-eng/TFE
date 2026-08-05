"""Atomic W1 execution of one causal THING action intent.

The executor accepts only a live intent owned by
``CausalThingActionIntentOwner``.  It applies the exact embodied command to
the authenticated W1 world, asks the existing W1 physical-evidence authority
for one reserved full-field outcome, places that exact outcome in the existing
settled-experience custody, seals the action/outcome receipt, commits the one
prepared settlement, and only then consumes the intent.

World mutation, physical settlement, custody, and intent consumption form one
fail-closed transaction.  Before causal commit, any failure restores the world
byte-identically, discards the prepared outcome, and leaves the intent live.
Every successful result carries one typed, owner-bound undo capability.  While
that exact committed world/physical/intent tail remains current, downstream
failure may restore all three authorities and make deterministic retry lawful.
Any later mutation makes the undo stale; an undo can be consumed only once.
No action history is accumulated here; durable outcome memory belongs to the
settlement, custody consumers, and bounded cognition owners.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field

from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntent,
    CausalThingActionIntentOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    PreparedActionExecution,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceConsumerView,
    SettledExperienceCustody,
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)


EXECUTION_SCHEMA = "guala.causal_thing.action_execution.v2"
EXECUTION_CUSTODY_CONSUMER_ID = "causal-thing-action-execution"
_EXECUTION_DOMAIN = b"guala-causal-thing-action-execution-v2\0"
_HEX = frozenset("0123456789abcdef")
_EXECUTION_UNDO_CONSTRUCTION_AUTHORITY = object()


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


def _key(value: bytes | str, label: str, *, minimum: int = 32) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if (
        not isinstance(raw, bytes)
        or not minimum <= len(raw) <= 4_096
    ):
        raise ValueError(f"{label} changed")
    return raw


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class CausalThingActionExecution:
    intent_receipt_sha256: str
    thing_id: str
    source_binding_id: str
    world_execution_receipt_sha256: str
    world_disposition: str
    expected_outcome_settlement_receipt_sha256: str
    expected_outcome_structural_fingerprint: str
    actual_outcome_settlement_receipt_sha256: str
    actual_outcome_structural_fingerprint: str
    outcome_custody_receipt_sha256: str
    outcome_custody_capability_receipt_sha256: str
    prediction_verification: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "actual_outcome_settlement_receipt_sha256": (
                self.actual_outcome_settlement_receipt_sha256
            ),
            "actual_outcome_structural_fingerprint": (
                self.actual_outcome_structural_fingerprint
            ),
            "expected_outcome_settlement_receipt_sha256": (
                self.expected_outcome_settlement_receipt_sha256
            ),
            "expected_outcome_structural_fingerprint": (
                self.expected_outcome_structural_fingerprint
            ),
            "intent_receipt_sha256": self.intent_receipt_sha256,
            "outcome_custody_capability_receipt_sha256": (
                self.outcome_custody_capability_receipt_sha256
            ),
            "outcome_custody_receipt_sha256": (
                self.outcome_custody_receipt_sha256
            ),
            "prediction_verification": self.prediction_verification,
            "schema": EXECUTION_SCHEMA,
            "source_binding_id": self.source_binding_id,
            "thing_id": self.thing_id,
            "world_disposition": self.world_disposition,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class ExecutedCausalThingAction:
    execution: CausalThingActionExecution
    world_execution: ActionExecutionReceipt
    physical_mount: W1PhysicalEvidenceMount
    custody_authority: SettledExperienceCustodyAuthority
    custody_capability: SettledExperienceConsumerCapability
    custody: SettledExperienceCustody
    custody_view: SettledExperienceConsumerView
    undo: "CausalThingActionExecutionUndo"


@dataclass(slots=True)
class _ExecutionUndoState:
    phase: str


@dataclass(frozen=True, slots=True)
class CausalThingActionExecutionUndo:
    execution: CausalThingActionExecution
    _prepared_world_action: PreparedActionExecution = field(repr=False)
    _physical_commit_undo: object = field(repr=False)
    _prior_intent_state: bytes = field(repr=False)
    _committed_intent_state: bytes = field(repr=False)
    _transaction_state: _ExecutionUndoState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class CausalThingActionExecutionAuthority:
    """Transactional executor for the custody-native THING action boundary."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        intent_owner: CausalThingActionIntentOwner,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        custody_authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        custody_profile: SettledExperienceCustodyProfile,
    ) -> None:
        if not isinstance(intent_owner, CausalThingActionIntentOwner):
            raise TypeError(
                "THING action execution requires its intent owner"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("THING action execution requires the W1 world")
        if not isinstance(
            physical_authority,
            W1AudiovisualPhysicalEvidenceAuthority,
        ):
            raise TypeError(
                "THING action execution requires W1 physical evidence"
            )
        if not isinstance(
            custody_profile,
            SettledExperienceCustodyProfile,
        ):
            raise TypeError(
                "THING action execution requires settled custody profile"
            )
        custody_profile.verify()
        root = _key(authority_key, "THING action execution key")
        self._execution_key = hashlib.sha256(
            _EXECUTION_DOMAIN + root
        ).digest()
        self._custody_key = _key(
            custody_authority_key,
            "THING action custody key",
        )
        self._w1_key = _key(
            w1_physical_authority_key,
            "THING action W1 physical key",
        )
        self._world_key = _key(
            world_authority_key,
            "THING action world key",
            minimum=1,
        )
        self._intents = intent_owner
        self._world = world_authority
        self._physical = physical_authority
        self._custody_profile = custody_profile
        self._undo_authority = object()
        self._lock = threading.RLock()

    def _seal(
        self,
        *,
        intent: CausalThingActionIntent,
        world_execution: ActionExecutionReceipt,
        physical_mount: W1PhysicalEvidenceMount,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> CausalThingActionExecution:
        actual = physical_mount.causal_settlement
        custody = custody_authority.custody
        if actual is None or custody is None:
            raise ValueError(
                "THING action physical outcome lacks settlement custody"
            )
        expected = intent.expected_outcome_witness
        provisional = CausalThingActionExecution(
            intent_receipt_sha256=intent.authority_receipt_sha256,
            thing_id=intent.thing_id,
            source_binding_id=intent.source_binding_id,
            world_execution_receipt_sha256=(
                world_execution.authority_receipt_sha256
            ),
            world_disposition=world_execution.disposition,
            expected_outcome_settlement_receipt_sha256=(
                expected.settlement_receipt_sha256
            ),
            expected_outcome_structural_fingerprint=(
                expected.structural_fingerprint
            ),
            actual_outcome_settlement_receipt_sha256=(
                actual.authority_receipt_sha256
            ),
            actual_outcome_structural_fingerprint=(
                actual.structural_fingerprint
            ),
            outcome_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            outcome_custody_capability_receipt_sha256=(
                custody_capability.authority_receipt_sha256
            ),
            prediction_verification=(
                "predicted_exact"
                if expected.structural_fingerprint
                == actual.structural_fingerprint
                else "predicted_mismatch"
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._execution_key,
            _EXECUTION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = CausalThingActionExecution(
            **{
                field: getattr(provisional, field)
                for field in (
                    "intent_receipt_sha256",
                    "thing_id",
                    "source_binding_id",
                    "world_execution_receipt_sha256",
                    "world_disposition",
                    "expected_outcome_settlement_receipt_sha256",
                    "expected_outcome_structural_fingerprint",
                    "actual_outcome_settlement_receipt_sha256",
                    "actual_outcome_structural_fingerprint",
                    "outcome_custody_receipt_sha256",
                    "outcome_custody_capability_receipt_sha256",
                    "prediction_verification",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(result)
        return result

    def verify(self, value: CausalThingActionExecution) -> None:
        if not isinstance(value, CausalThingActionExecution):
            raise TypeError("THING action execution is not typed")
        for digest, label in (
            (value.intent_receipt_sha256, "THING action intent"),
            (value.thing_id, "THING action execution THING"),
            (value.source_binding_id, "THING action source binding"),
            (
                value.world_execution_receipt_sha256,
                "THING action world execution",
            ),
            (
                value.expected_outcome_settlement_receipt_sha256,
                "THING action expected outcome",
            ),
            (
                value.expected_outcome_structural_fingerprint,
                "THING action expected structure",
            ),
            (
                value.actual_outcome_settlement_receipt_sha256,
                "THING action actual outcome",
            ),
            (
                value.actual_outcome_structural_fingerprint,
                "THING action actual structure",
            ),
            (
                value.outcome_custody_receipt_sha256,
                "THING action outcome custody",
            ),
            (
                value.outcome_custody_capability_receipt_sha256,
                "THING action outcome custody capability",
            ),
            (value.authority_hmac_sha256, "THING action execution HMAC"),
            (
                value.authority_receipt_sha256,
                "THING action execution authority",
            ),
        ):
            _sha(digest, label)
        if (
            value.world_disposition != "applied"
            or value.prediction_verification
            not in {"predicted_exact", "predicted_mismatch"}
        ):
            raise ValueError("THING action execution disposition changed")
        expected = hmac.new(
            self._execution_key,
            _EXECUTION_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("THING action execution authority changed")

    def execute(
        self,
        *,
        intent: CausalThingActionIntent,
    ) -> ExecutedCausalThingAction:
        with self._lock:
            if intent.action.kind != "embodiment_port":
                raise ValueError(
                    "THING action execution accepts embodied commands only"
                )
            if not self._intents.verify_live(intent):
                raise ValueError("THING action intent is not live")
            if (
                self._world.observation_snapshot()
                .authority_receipt_sha256
                != intent.world_observation_receipt_sha256
            ):
                raise ValueError(
                    "THING action intent crossed current world custody"
                )
            prior_intent_state = self._intents.snapshot_encoded()
            episode_token: str | None = None
            prepared_world: PreparedActionExecution | None = None
            prepared_mount: W1PhysicalEvidenceMount | None = None
            physical_commit_undo: object | None = None
            world_committed = False
            try:
                episode_token = self._physical.begin_atomic_episode()
                with self._intents.executing(intent):
                    before = self._world.observation_snapshot()
                    world_candidate = self._world.prepare_port_command(
                        port_id=intent.action.port_id,
                        command_payload=intent.action.command_payload,
                        causal_intent_receipt_sha256=(
                            intent.authority_receipt_sha256
                        ),
                        expected_revision=before.revision,
                    )
                    if isinstance(
                        world_candidate,
                        ActionExecutionReceipt,
                    ):
                        raise RuntimeError(
                            "THING action command was not physically applied"
                        )
                    prepared_world = world_candidate
                    self._world.verify_prepared_action(prepared_world)
                    world_execution = (
                        prepared_world.execution_receipt
                    )
                    with (
                        self._world
                        .prepared_action_visibility_transaction(
                            prepared_world
                        )
                    ):
                        self._world.commit_prepared_action(
                            prepared_world
                        )
                        world_committed = True
                    prepared_mount = (
                        self._physical.mount_action_outcome(
                            world_execution,
                            commit=False,
                            reserve=True,
                        )
                    )
                    if (
                        prepared_mount.state
                        is not W1EvidenceState.OBSERVED
                        or prepared_mount.causal_settlement is None
                        or prepared_mount.evidence_receipt is None
                    ):
                        raise RuntimeError(
                            "THING action has no observed W1 physical "
                            "outcome"
                        )
                    self._physical.verify_mount(prepared_mount)
                    custody_authority = (
                        SettledExperienceCustodyAuthority(
                            authority_key=self._custody_key,
                            w1_physical_authority_key=self._w1_key,
                            world_authority_key=self._world_key,
                            profile=self._custody_profile,
                        )
                    )
                    custody = custody_authority.admit(
                        prepared_mount,
                        world_execution,
                    )
                    capability = custody_authority.issue_child(
                        EXECUTION_CUSTODY_CONSUMER_ID
                    )
                    view = custody_authority.open_child(
                        capability
                    )
                    if (
                        view.causal_settlement
                        is not prepared_mount.causal_settlement
                        or view.parent_custody_receipt_sha256
                        != custody.authority_receipt_sha256
                    ):
                        raise RuntimeError(
                            "THING action custody changed physical "
                            "outcome"
                        )
                    execution = self._seal(
                        intent=intent,
                        world_execution=world_execution,
                        physical_mount=prepared_mount,
                        custody_authority=custody_authority,
                        custody_capability=capability,
                    )
                    self._physical.commit_prepared_mount(
                        prepared_mount
                    )
                    physical_commit_undo = (
                        self._physical.commit_atomic_episode(
                            episode_token
                        )
                    )
                    episode_token = None
                committed_intent_state = (
                    self._intents.snapshot_encoded()
                )
                if (
                    prepared_world is None
                    or prepared_mount is None
                    or physical_commit_undo is None
                ):
                    raise RuntimeError(
                        "THING action execution transaction is incomplete"
                    )
                undo = CausalThingActionExecutionUndo(
                    execution=execution,
                    _prepared_world_action=prepared_world,
                    _physical_commit_undo=physical_commit_undo,
                    _prior_intent_state=prior_intent_state,
                    _committed_intent_state=committed_intent_state,
                    _transaction_state=_ExecutionUndoState(
                        phase="committed"
                    ),
                    _owner_authority=self._undo_authority,
                    _construction_authority=(
                        _EXECUTION_UNDO_CONSTRUCTION_AUTHORITY
                    ),
                )
                return ExecutedCausalThingAction(
                    execution=execution,
                    world_execution=world_execution,
                    physical_mount=prepared_mount,
                    custody_authority=custody_authority,
                    custody_capability=capability,
                    custody=custody,
                    custody_view=view,
                    undo=undo,
                )
            except BaseException:
                if world_committed and prepared_world is not None:
                    with (
                        self._world
                        .committed_prepared_action_rollback_transaction(
                            prepared_world
                        )
                    ) as rollback_world:
                        rollback_world()
                elif prepared_world is not None:
                    try:
                        self._world.discard_prepared_action(
                            prepared_world
                        )
                    except ValueError:
                        pass
                if physical_commit_undo is not None:
                    self._physical.rollback_committed_atomic_episode(
                        physical_commit_undo
                    )
                elif episode_token is not None:
                    self._physical.rollback_atomic_episode(
                        episode_token
                    )
                if (
                    self._intents.snapshot_encoded()
                    != prior_intent_state
                ):
                    self._intents.restore_encoded(
                        prior_intent_state
                    )
                raise

    def rollback_committed_execution(
        self,
        undo: CausalThingActionExecutionUndo,
    ) -> None:
        """Undo one current successful execution exactly once."""

        with self._lock:
            if (
                not isinstance(undo, CausalThingActionExecutionUndo)
                or undo._construction_authority
                is not _EXECUTION_UNDO_CONSTRUCTION_AUTHORITY
                or undo._owner_authority is not self._undo_authority
                or undo._transaction_state.phase != "committed"
            ):
                raise ValueError(
                    "THING action execution undo changed custody"
                )
            self.verify(undo.execution)
            if (
                self._intents.snapshot_encoded()
                != undo._committed_intent_state
            ):
                raise RuntimeError(
                    "THING action execution intent tail changed"
                )
            with (
                self._world
                .committed_prepared_action_rollback_transaction(
                    undo._prepared_world_action
                )
            ) as rollback_world:
                self._physical.rollback_committed_atomic_episode(
                    undo._physical_commit_undo
                )
                self._intents.restore_encoded(
                    undo._prior_intent_state
                )
                rollback_world()
            undo._transaction_state.phase = "rolled_back"


__all__ = (
    "EXECUTION_CUSTODY_CONSUMER_ID",
    "CausalThingActionExecution",
    "CausalThingActionExecutionAuthority",
    "CausalThingActionExecutionUndo",
    "ExecutedCausalThingAction",
)
