"""Transactional dedicated-process owner for the mono auditory q bank."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import pickle
import threading
from dataclasses import dataclass
from multiprocessing.connection import wait

from dsf_ai_service.substrate.auditory_live_motif import (
    build_verified_live_motif_result,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    MAX_AUDITORY_RECEPTOR_FRAMES,
    AuditoryReceptorExperience,
    AuditoryRecurrentMotifOwner,
    AuditoryVerifiedReceptorExperienceCapability,
    compose_verified_contiguous_receptor_experiences,
    verify_receptor_experience_custody,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)


@dataclass(frozen=True, slots=True)
class AuditoryQProcessTask:
    terminal_task_id: str
    transport: AuditoryPCMContinuityReceipt
    joint_settlement: AuditoryStreamSettlementReceipt
    experience: AuditoryReceptorExperience

    def verify(self) -> AuditoryVerifiedReceptorExperienceCapability:
        self.transport.verify()
        self.joint_settlement.verify()
        experience_capability = verify_receptor_experience_custody(
            self.experience
        )
        if (
            not isinstance(self.terminal_task_id, str)
            or len(self.terminal_task_id) != 64
            or self.joint_settlement.stream_id != self.transport.stream_id
            or self.joint_settlement.sequence != self.transport.sequence
            or (
                self.experience.source_continuity_receipt_sha256s
                and (
                    self.experience
                    .source_continuity_receipt_sha256s[-1]
                    != self.joint_settlement.authority_receipt_sha256
                )
            )
        ):
            raise ValueError("auditory q process task changed")
        return experience_capability


@dataclass(frozen=True, slots=True)
class AuditoryQProcessOutcome:
    sequence: int
    stream_id: str
    result_record: dict[str, object]
    latest_experience_receipt_sha256: str
    post_owner_state_sha256: str
    activation_support_root_sha256: str
    source_component_experience_receipt_sha256s: tuple[str, ...]
    source_continuity_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str
    status: dict[str, object]
    temporal_firing_record: dict[str, object] | None = None

    def verify(self) -> None:
        spans = self.result_record.get("activation_spans")
        if not isinstance(spans, list):
            raise ValueError("auditory q process activation support changed")
        support_root = hashlib.sha256(
            json.dumps(
                {
                    "activation_spans": spans,
                    "schema": "guala.auditory.q_activation_support.v1",
                },
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        payload = {
            "activation_support_root_sha256": support_root,
            "latest_experience_receipt_sha256": (
                self.latest_experience_receipt_sha256
            ),
            "post_owner_state_sha256": self.post_owner_state_sha256,
            "source_component_experience_receipt_sha256s": list(
                self.source_component_experience_receipt_sha256s
            ),
            "source_continuity_receipt_sha256s": list(
                self.source_continuity_receipt_sha256s
            ),
            "result_authority_receipt_sha256": self.result_record.get(
                "authority_receipt_sha256"
            ),
            "sequence": self.sequence,
            "stream_id": self.stream_id,
            "temporal_firing_record": self.temporal_firing_record,
        }
        if (
            support_root != self.activation_support_root_sha256
            or hashlib.sha256(
                json.dumps(
                    payload,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            != self.authority_receipt_sha256
        ):
            raise ValueError("auditory q process outcome receipt changed")


@dataclass(frozen=True, slots=True)
class AuditoryQCommittedState:
    owner_state: bytes
    pending_state: bytes
    pending_state_sha256: str
    temporal_state: bytes | None = None

    def verify(self) -> None:
        if not isinstance(self.owner_state, bytes) or not self.owner_state:
            raise ValueError("auditory q committed owner state changed")
        if (
            not isinstance(self.pending_state, bytes)
            or not self.pending_state
            or hashlib.sha256(self.pending_state).hexdigest()
            != self.pending_state_sha256
        ):
            raise ValueError("auditory q committed pending state changed")
        if (
            self.temporal_state is not None
            and (
                not isinstance(self.temporal_state, bytes)
                or not self.temporal_state
            )
        ):
            raise ValueError(
                "auditory q committed temporal state changed"
            )

    @classmethod
    def create(
        cls,
        *,
        owner_state,
        pending_by_stream,
        temporal_state=None,
    ):
        pending_state = pickle.dumps(
            _pending_record(pending_by_stream),
            protocol=5,
        )
        result = cls(
            owner_state=owner_state,
            pending_state=pending_state,
            pending_state_sha256=hashlib.sha256(
                pending_state
            ).hexdigest(),
            temporal_state=temporal_state,
        )
        result.verify()
        return result

    def restore_pending(self):
        self.verify()
        record = pickle.loads(self.pending_state)
        prior_stream_id = None
        for stream_id, values in record:
            if (
                not isinstance(stream_id, str)
                or not stream_id
                or (
                    prior_stream_id is not None
                    and stream_id <= prior_stream_id
                )
            ):
                raise ValueError(
                    "auditory q committed stream ordering changed"
                )
            prior_stream_id = stream_id
            prior_sequence = None
            for task, experience in values:
                task.verify()
                experience.verify()
                if (
                    task.transport.stream_id != stream_id
                    or task.experience != experience
                    or (
                        prior_sequence is not None
                        and task.transport.sequence != prior_sequence + 1
                    )
                ):
                    raise ValueError(
                        "auditory q committed pending continuity changed"
                )
                prior_sequence = task.transport.sequence
        return _pending_restore(record)

    def without_stream(self, stream_id):
        pending = self.restore_pending()
        pending.pop(stream_id, None)
        return type(self).create(
            owner_state=self.owner_state,
            pending_by_stream=pending,
            temporal_state=self.temporal_state,
        )


@dataclass(frozen=True, slots=True)
class AuditoryQPreparedOutcome:
    token: str
    outcome: AuditoryQProcessOutcome
    staged_state: AuditoryQCommittedState


@dataclass(frozen=True, slots=True)
class AuditoryQCommitReceipt:
    token: str
    owner_state_sha256: str
    pending_state_sha256: str
    authority_receipt_sha256: str
    temporal_state_sha256: str | None = None

    def verify(self) -> None:
        for value in (
            self.token,
            self.owner_state_sha256,
            self.pending_state_sha256,
            self.authority_receipt_sha256,
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError("auditory q commit receipt changed")
        if self.temporal_state_sha256 is not None and (
            len(self.temporal_state_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.temporal_state_sha256
            )
        ):
            raise ValueError(
                "auditory q temporal commit receipt changed"
            )
        expected = hashlib.sha256(
            json.dumps(
                {
                    "owner_state_sha256": self.owner_state_sha256,
                    "pending_state_sha256": self.pending_state_sha256,
                    "schema": "guala.auditory.q_commit.v1",
                    "temporal_state_sha256": (
                        self.temporal_state_sha256
                    ),
                    "token": self.token,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        if expected != self.authority_receipt_sha256:
            raise ValueError("auditory q commit authority changed")

    @classmethod
    def create(
        cls,
        *,
        token: str,
        state: AuditoryQCommittedState,
    ) -> "AuditoryQCommitReceipt":
        state.verify()
        owner_state_sha256 = hashlib.sha256(
            state.owner_state
        ).hexdigest()
        payload = {
            "owner_state_sha256": owner_state_sha256,
            "pending_state_sha256": state.pending_state_sha256,
            "schema": "guala.auditory.q_commit.v1",
            "temporal_state_sha256": (
                hashlib.sha256(state.temporal_state).hexdigest()
                if state.temporal_state is not None else None
            ),
            "token": token,
        }
        result = cls(
            token=token,
            owner_state_sha256=owner_state_sha256,
            pending_state_sha256=state.pending_state_sha256,
            temporal_state_sha256=payload[
                "temporal_state_sha256"
            ],
            authority_receipt_sha256=hashlib.sha256(
                json.dumps(
                    payload,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
        )
        result.verify()
        return result


@dataclass(frozen=True, slots=True)
class AuditoryQSchedulingReceipt:
    inherited_niceness: int
    niceness: int
    policy: str

    def verify(self) -> None:
        if (
            self.niceness != self.inherited_niceness
            or self.policy
            != "inherits_parent_ordinary_process_priority"
        ):
            raise ValueError("auditory q process scheduling changed")


def _pending_record(pending_by_stream):
    return tuple(
        (stream_id, tuple(values))
        for stream_id, values in sorted(pending_by_stream.items())
    )


def _pending_restore(record):
    return {
        stream_id: list(values)
        for stream_id, values in record
    }


def _prepared_token(task, state):
    digest = hashlib.sha256()
    digest.update(b"guala-auditory-q-prepared-v1\0")
    digest.update(task.terminal_task_id.encode("ascii"))
    digest.update(hashlib.sha256(state.owner_state).digest())
    digest.update(bytes.fromhex(state.pending_state_sha256))
    if state.temporal_state is not None:
        digest.update(hashlib.sha256(state.temporal_state).digest())
    return digest.hexdigest()


def _append_contiguous(pending_by_stream, task):
    experience_capability = task.verify()
    pending = list(pending_by_stream.get(task.transport.stream_id, ()))
    if pending:
        prior = pending[-1]
        if (
            task.transport.sequence != prior.transport.sequence + 1
            or task.transport.first_sample_index
            != (
                prior.transport.first_sample_index
                + prior.transport.sample_count
            )
            or task.joint_settlement.prior_transport_receipt_sha256
            != prior.transport.receipt_sha256
            or (
                task.joint_settlement
                .prior_cochlear_state_receipt_sha256
                != prior.joint_settlement.cochlear_receipt_sha256
            )
            or task.joint_settlement.source_time_start
            != prior.joint_settlement.source_time_end
        ):
            raise ValueError("auditory q process continuity changed")
    frame_count = task.experience.source_frame_count + sum(
        value.experience.source_frame_count for value in pending
    )
    if frame_count > MAX_AUDITORY_RECEPTOR_FRAMES:
        raise RuntimeError("auditory q process receptor allocation exhausted")
    pending.append(task)
    return pending, experience_capability


def _settle_task(
    owner,
    temporal_owner,
    pending_by_stream,
    verified_experiences,
    task,
):
    pending, experience_capability = _append_contiguous(
        pending_by_stream,
        task,
    )
    verified_experiences[task.terminal_task_id] = experience_capability
    if len(pending) != 4:
        raise ValueError(
            "auditory q process requires one complete four-unit window"
        )
    experience, composed_capability = (
        compose_verified_contiguous_receptor_experiences(
        tuple(value.experience for value in pending),
        continuity_receipt_sha256s=tuple(
            value.joint_settlement.authority_receipt_sha256
            for value in pending
        ),
        verified_capabilities=tuple(
            verified_experiences[value.terminal_task_id]
            for value in pending
        ),
    ))
    prepared = owner.prepare(
        experience,
        verified_capability=composed_capability,
    )
    try:
        firing = owner.fire(prepared)
        observation = owner.observe(prepared)
    finally:
        owner.discard_prepared(prepared)
    result, result_capability = build_verified_live_motif_result(
        experience=experience,
        firing=firing,
        observation=observation,
        verified_capability=composed_capability,
    )
    result_record = result_capability.as_record(result)
    owner_state = owner.snapshot_encoded()
    activation_support_root = hashlib.sha256(
        json.dumps(
            {
                "activation_spans": result_record["activation_spans"],
                "schema": "guala.auditory.q_activation_support.v1",
            },
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    temporal_firing_record = (
        None
        if temporal_owner is None
        else temporal_owner.fire(result_record).payload()
    )
    outcome_payload = {
        "activation_support_root_sha256": activation_support_root,
        "latest_experience_receipt_sha256": (
            experience.authority_receipt_sha256
        ),
        "post_owner_state_sha256": hashlib.sha256(owner_state).hexdigest(),
        "source_component_experience_receipt_sha256s": [
            value.experience.authority_receipt_sha256
            for value in pending
        ],
        "source_continuity_receipt_sha256s": [
            value.joint_settlement.authority_receipt_sha256
            for value in pending
        ],
        "result_authority_receipt_sha256": result.authority_receipt_sha256,
        "sequence": task.transport.sequence,
        "stream_id": task.transport.stream_id,
        "temporal_firing_record": temporal_firing_record,
    }
    pending_by_stream[task.transport.stream_id] = [task]
    retained_ids = {
        value.terminal_task_id
        for values in pending_by_stream.values()
        for value in values
    }
    for task_id in tuple(verified_experiences):
        if task_id not in retained_ids:
            del verified_experiences[task_id]
    outcome = AuditoryQProcessOutcome(
        sequence=task.transport.sequence,
        stream_id=task.transport.stream_id,
        result_record=result_record,
        latest_experience_receipt_sha256=(
            experience.authority_receipt_sha256
        ),
        post_owner_state_sha256=hashlib.sha256(owner_state).hexdigest(),
        activation_support_root_sha256=activation_support_root,
        source_component_experience_receipt_sha256s=tuple(
            value.experience.authority_receipt_sha256
            for value in pending
        ),
        source_continuity_receipt_sha256s=tuple(
            value.joint_settlement.authority_receipt_sha256
            for value in pending
        ),
        authority_receipt_sha256=hashlib.sha256(
            json.dumps(
                outcome_payload,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        status=owner.status(),
        temporal_firing_record=temporal_firing_record,
    )
    outcome.verify()
    return outcome, owner_state, (
        result,
        tuple(
            value.experience.authority_receipt_sha256
            for value in pending
        ),
    )


def _process_main(
    connection,
    initial_state,
    inherited_niceness,
    temporal_authority_key,
) -> None:
    if not (
        hasattr(os, "getpriority")
        and hasattr(os, "PRIO_PROCESS")
    ):
        raise RuntimeError(
            "auditory q process requires OS process-priority governance"
        )
    scheduling = AuditoryQSchedulingReceipt(
        inherited_niceness=inherited_niceness,
        niceness=os.getpriority(os.PRIO_PROCESS, 0),
        policy="inherits_parent_ordinary_process_priority",
    )
    scheduling.verify()
    initial_state.verify()
    owner = AuditoryRecurrentMotifOwner.restore_encoded(
        initial_state.owner_state
    )
    temporal_owner = None
    if temporal_authority_key is not None:
        from dsf_ai_service.substrate.auditory_temporal_relation_assembly import (
            AUDITORY_TEMPORAL_RELATION_STATE_MAX_BYTES,
            AuditoryTemporalAssemblyProfile,
            AuditoryTemporalRelationAssemblyOwner,
        )
        if initial_state.temporal_state is None:
            temporal_owner = AuditoryTemporalRelationAssemblyOwner(
                profile=AuditoryTemporalAssemblyProfile.create(
                    profile_id="live-presemantic-temporal-relations",
                    max_exposures=32,
                    max_events_per_exposure=32_768,
                    max_assemblies=16,
                    max_relations_per_assembly=1_048_576,
                    max_state_bytes=(
                        AUDITORY_TEMPORAL_RELATION_STATE_MAX_BYTES
                    ),
                ),
                authority_key=temporal_authority_key,
            )
        else:
            temporal_owner = (
                AuditoryTemporalRelationAssemblyOwner.restore_encoded(
                    initial_state.temporal_state,
                    authority_key=temporal_authority_key,
                )
            )
    temporal_state_encoded = (
        temporal_owner.snapshot_encoded()
        if temporal_owner is not None
        else None
    )
    if initial_state.restore_pending():
        raise ValueError("auditory q child received parent-owned pending input")
    pending_by_stream = {}
    verified_experiences = {}
    prepared = None
    latest_temporal_candidate = None
    try:
        while True:
            command, value = connection.recv()
            if command == "close":
                if prepared is not None:
                    raise RuntimeError(
                        "auditory q process closed with prepared mutation"
                    )
                connection.send(("closed", None))
                return
            if command == "snapshot":
                if prepared is not None:
                    raise RuntimeError(
                        "auditory q process snapshot crossed preparation"
                    )
                connection.send((
                    "snapshot",
                    AuditoryQCommittedState.create(
                        owner_state=owner.snapshot_encoded(),
                        pending_by_stream={},
                        temporal_state=temporal_state_encoded,
                    ),
                ))
                continue
            if command == "scheduling":
                scheduling.verify()
                connection.send(("scheduling", scheduling))
                continue
            if command == "close_stream":
                if prepared is not None:
                    raise RuntimeError(
                        "auditory q process close crossed preparation"
                    )
                removed = pending_by_stream.pop(value, ())
                for task in removed:
                    verified_experiences.pop(
                        task.terminal_task_id,
                        None,
                    )
                connection.send((
                    "close_stream",
                    AuditoryQCommittedState.create(
                        owner_state=owner.snapshot_encoded(),
                        pending_by_stream={},
                        temporal_state=temporal_state_encoded,
                    ),
                ))
                continue
            if command == "retain":
                if prepared is not None:
                    raise RuntimeError(
                        "auditory q process retain crossed preparation"
                    )
                if not isinstance(value, AuditoryQProcessTask):
                    raise TypeError("auditory q retained task is not typed")
                retained, experience_capability = _append_contiguous(
                    pending_by_stream,
                    value,
                )
                if len(retained) >= 4:
                    raise ValueError(
                        "auditory q retained an unprocessed complete window"
                    )
                pending_by_stream[value.transport.stream_id] = retained
                verified_experiences[value.terminal_task_id] = (
                    experience_capability
                )
                connection.send(("retained", value.terminal_task_id))
                continue
            if command == "process":
                if prepared is not None:
                    raise RuntimeError(
                        "auditory q process has an unresolved preparation"
                    )
                if not isinstance(value, AuditoryQProcessTask):
                    raise TypeError("auditory q process task is not typed")
                pre_owner_state = owner.snapshot_encoded()
                staged_pending = {
                    stream_id: list(values)
                    for stream_id, values in pending_by_stream.items()
                }
                staged_verified = dict(verified_experiences)
                try:
                    outcome, post_owner_state, temporal_candidate = _settle_task(
                        owner,
                        temporal_owner,
                        staged_pending,
                        staged_verified,
                        value,
                    )
                except BaseException:
                    owner = AuditoryRecurrentMotifOwner.restore_encoded(
                        pre_owner_state
                    )
                    raise
                staged_state = AuditoryQCommittedState.create(
                    owner_state=post_owner_state,
                    pending_by_stream={},
                    temporal_state=temporal_state_encoded,
                )
                if (
                    outcome.post_owner_state_sha256
                    != hashlib.sha256(staged_state.owner_state).hexdigest()
                ):
                    raise RuntimeError(
                        "auditory q outcome differs from staged owner"
                    )
                token = _prepared_token(value, staged_state)
                prepared = (
                    token,
                    pre_owner_state,
                    staged_pending,
                    staged_verified,
                    staged_state,
                    temporal_candidate,
                )
                connection.send((
                    "prepared",
                    AuditoryQPreparedOutcome(
                        token=token,
                        outcome=outcome,
                        staged_state=staged_state,
                    ),
                ))
                continue
            if command == "commit":
                if prepared is None or value != prepared[0]:
                    raise ValueError(
                        "auditory q process commit token changed"
                    )
                (
                    token,
                    _pre_owner_state,
                    pending_by_stream,
                    verified_experiences,
                    state,
                    temporal_candidate,
                ) = prepared
                prepared = None
                latest_temporal_candidate = temporal_candidate
                connection.send((
                    "committed",
                    AuditoryQCommitReceipt.create(
                        token=token,
                        state=state,
                    ),
                ))
                continue
            if command == "retain_temporal":
                if prepared is not None:
                    raise RuntimeError(
                        "temporal retention crossed q preparation"
                    )
                if temporal_owner is None:
                    raise RuntimeError(
                        "temporal relation owner is unavailable"
                    )
                if (
                    latest_temporal_candidate is None
                    or value != (
                        latest_temporal_candidate[0]
                        .source_experience_receipt_sha256
                    )
                ):
                    raise ValueError(
                        "temporal retention source is not the latest q window"
                    )
                temporal_owner.observe_typed(
                    latest_temporal_candidate[0],
                    source_component_receipt_sha256s=(
                        latest_temporal_candidate[1]
                    ),
                )
                temporal_state_encoded = (
                    temporal_owner.snapshot_encoded()
                )
                connection.send((
                    "retained_temporal",
                    AuditoryQCommittedState.create(
                        owner_state=owner.snapshot_encoded(),
                        pending_by_stream={},
                        temporal_state=temporal_state_encoded,
                    ),
                ))
                continue
            if command == "learn_temporal":
                if prepared is not None:
                    raise RuntimeError(
                        "temporal learning crossed q preparation"
                    )
                if temporal_owner is None or not isinstance(value, dict):
                    raise RuntimeError(
                        "temporal relation learning is unavailable"
                    )
                assembly = temporal_owner.learn_acoustic_contrast(
                    positive_exposure_receipt_sha256s=tuple(
                        value.get("positive_exposure_receipt_sha256s")
                        or ()
                    ),
                    contrast_exposure_receipt_sha256s=tuple(
                        value.get("contrast_exposure_receipt_sha256s")
                        or ()
                    ),
                )
                temporal_state_encoded = (
                    temporal_owner.snapshot_encoded()
                )
                connection.send((
                    "learned_temporal",
                    (
                        None if assembly is None
                        else assembly.payload()
                        | {
                            "authority_receipt_sha256": (
                                assembly.authority_receipt_sha256
                            )
                        },
                        AuditoryQCommittedState.create(
                            owner_state=owner.snapshot_encoded(),
                            pending_by_stream={},
                            temporal_state=temporal_state_encoded,
                        ),
                    ),
                ))
                continue
            if command == "rollback":
                if prepared is None or value != prepared[0]:
                    raise ValueError(
                        "auditory q process rollback token changed"
                    )
                owner = AuditoryRecurrentMotifOwner.restore_encoded(
                    prepared[1]
                )
                prepared = None
                connection.send(("rolled_back", True))
                continue
            raise ValueError("auditory q process command changed")
    except Exception as error:
        try:
            connection.send(("error", (type(error).__name__, str(error))))
        finally:
            connection.close()


class AuditoryQProcessOwner:
    """One spawned process with explicit prepare/commit/rollback."""

    def __init__(
        self,
        initial_state: AuditoryQCommittedState,
        *,
        temporal_authority_key: bytes | str | None = None,
    ) -> None:
        if not isinstance(initial_state, AuditoryQCommittedState):
            raise TypeError("auditory q process state is not typed")
        initial_state.verify()
        context = multiprocessing.get_context("spawn")
        if not (
            hasattr(os, "getpriority")
            and hasattr(os, "PRIO_PROCESS")
        ):
            raise RuntimeError(
                "auditory q process requires OS process-priority governance"
            )
        inherited_niceness = os.getpriority(os.PRIO_PROCESS, 0)
        parent, child = context.Pipe(duplex=True)
        process = context.Process(
            target=_process_main,
            args=(
                child,
                initial_state,
                inherited_niceness,
                temporal_authority_key,
            ),
            daemon=True,
            name="guala-auditory-q-owner",
        )
        process.start()
        child.close()
        self._connection = parent
        self._process = process
        self._lock = threading.RLock()
        self._closed = False

    def _receive(self):
        ready = wait((self._connection, self._process.sentinel))
        if self._connection in ready:
            try:
                kind, result = self._connection.recv()
            except EOFError as error:
                raise RuntimeError(
                    "auditory q process pipe closed without a result"
                ) from error
            if kind == "error":
                error_type, message = result
                raise RuntimeError(
                    f"auditory q process {error_type}: {message}"
                )
            return kind, result
        raise RuntimeError(
            "auditory q process exited before returning a result"
        )

    def _call(self, command: str, value=None):
        with self._lock:
            if self._closed:
                raise RuntimeError("auditory q process is closed")
            self._connection.send((command, value))
            return self._receive()

    def prepare(
        self,
        task: AuditoryQProcessTask,
    ) -> AuditoryQPreparedOutcome:
        if not isinstance(task, AuditoryQProcessTask):
            raise TypeError("auditory q process task is not typed")
        kind, result = self._call("process", task)
        if kind != "prepared" or not isinstance(
            result,
            AuditoryQPreparedOutcome,
        ):
            raise RuntimeError("auditory q process preparation changed")
        result.outcome.verify()
        if (
            result.outcome.post_owner_state_sha256
            != hashlib.sha256(result.staged_state.owner_state).hexdigest()
        ):
            raise RuntimeError(
                "auditory q preparation state binding changed"
            )
        return result

    def retain(self, task: AuditoryQProcessTask) -> None:
        if not isinstance(task, AuditoryQProcessTask):
            raise TypeError("auditory q retained task is not typed")
        kind, result = self._call("retain", task)
        if kind != "retained" or result != task.terminal_task_id:
            raise RuntimeError("auditory q process retain changed")

    def commit(self, token: str) -> AuditoryQCommitReceipt:
        kind, result = self._call("commit", token)
        if kind != "committed" or not isinstance(
            result,
            AuditoryQCommitReceipt,
        ):
            raise RuntimeError("auditory q process commit changed")
        result.verify()
        if result.token != token:
            raise RuntimeError("auditory q process commit token changed")
        return result

    def retain_temporal_exposure(
        self,
        exposure_receipt_sha256: str,
    ) -> AuditoryQCommittedState:
        kind, result = self._call(
            "retain_temporal",
            exposure_receipt_sha256,
        )
        if kind != "retained_temporal" or not isinstance(
            result,
            AuditoryQCommittedState,
        ):
            raise RuntimeError(
                "auditory q temporal retention changed"
            )
        result.verify()
        return result

    def learn_temporal_acoustic_contrast(
        self,
        *,
        positive_exposure_receipt_sha256s: tuple[str, ...],
        contrast_exposure_receipt_sha256s: tuple[str, ...],
    ) -> tuple[dict[str, object] | None, AuditoryQCommittedState]:
        kind, result = self._call("learn_temporal", {
            "contrast_exposure_receipt_sha256s": list(
                contrast_exposure_receipt_sha256s
            ),
            "positive_exposure_receipt_sha256s": list(
                positive_exposure_receipt_sha256s
            ),
        })
        if (
            kind != "learned_temporal"
            or not isinstance(result, tuple)
            or len(result) != 2
            or (
                result[0] is not None
                and not isinstance(result[0], dict)
            )
            or not isinstance(result[1], AuditoryQCommittedState)
        ):
            raise RuntimeError(
                "auditory q temporal learning changed"
            )
        result[1].verify()
        return result

    def rollback(self, token: str) -> None:
        kind, _result = self._call("rollback", token)
        if kind != "rolled_back":
            raise RuntimeError("auditory q process rollback changed")

    def snapshot(self) -> AuditoryQCommittedState:
        kind, result = self._call("snapshot")
        if kind != "snapshot" or not isinstance(
            result,
            AuditoryQCommittedState,
        ):
            raise RuntimeError("auditory q process snapshot changed")
        return result

    def scheduling(self) -> AuditoryQSchedulingReceipt:
        kind, result = self._call("scheduling")
        if kind != "scheduling" or not isinstance(
            result,
            AuditoryQSchedulingReceipt,
        ):
            raise RuntimeError("auditory q process scheduling changed")
        result.verify()
        return result

    def close_stream(self, stream_id: str) -> AuditoryQCommittedState:
        kind, result = self._call("close_stream", stream_id)
        if kind != "close_stream" or not isinstance(
            result,
            AuditoryQCommittedState,
        ):
            raise RuntimeError("auditory q process close changed")
        result.verify()
        return result

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._connection.send(("close", None))
            kind, _result = self._receive()
            if kind != "closed":
                raise RuntimeError("auditory q process refused close")
            self._closed = True
            self._connection.close()
        self._process.join()
        if self._process.exitcode != 0:
            raise RuntimeError("auditory q process did not stop cleanly")

    def abandon(self) -> None:
        """Release an unusable child after parent state recovery."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._connection.close()
        if self._process.is_alive():
            self._process.terminate()
        self._process.join()


__all__ = (
    "AuditoryQCommittedState",
    "AuditoryQPreparedOutcome",
    "AuditoryQProcessOutcome",
    "AuditoryQProcessOwner",
    "AuditoryQProcessTask",
)
