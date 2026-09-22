"""Causal continuity for one moving source inside a two-emitter W1 room.

The two-emitter hearing path deliberately erases control identities before
releasing auditory occurrences.  Anonymous ordinal therefore cannot be an
identity: it may change when two visible emitters exchange spatial order.
This authority carries one lineage across that exchange only when the world
authority proves a contiguous sequence of physical MoveCommand executions and
the moved body's exact before/after binaural paths each occur uniquely in the
authenticated captures.

Body and port identities are used transiently to verify causal custody.  They
do not enter the continuity payload or retained transition.  Raw pressure,
waveform equality, firing-set equality, labels, transcripts, chi, scores,
tolerances, blind inference, and reduced DSF projections are absent.  The
associated room-hearing occurrences retain the full explicit L0--L4 field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.binaural_room_hearing_coordinator import (
    BinauralRoomHearingOutcome,
    BinauralRoomHearingState,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    MoveCommand,
    decode_command,
)
from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
    W1AuthenticatedMultiEmitterBinauralCapture,
    W1MultiEmitterCaptureState,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1BinauralCalibration,
    _anonymous_path_for_position,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    body_from_snapshot,
    calibrated_ear_positions,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralTransferPath,
)


MOVING_SOURCE_CONTINUITY_SCHEMA = (
    "guala.w1.moving_multi_emitter_continuity.v1"
)
MOVING_SOURCE_CONTINUITY_AUTHORITY_SCHEMA = (
    "guala.w1.moving_multi_emitter_continuity.authority.v1"
)
MOVING_SOURCE_CONTINUITY_DOMAIN = (
    b"guala-w1-moving-multi-emitter-continuity-v1\0"
)
MOVING_SOURCE_LINEAGE_DOMAIN = (
    b"guala-w1-moving-multi-emitter-lineage-v1\0"
)
MAX_RETAINED_TRANSITIONS = 64


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


def _key(value: bytes | str, name: str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(f"{name} must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError(f"{name} is outside its exact boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _path_payload(path: ExactBinauralTransferPath) -> dict[str, object]:
    path.verify()
    return path.payload()


def _path_at(
    receipt: ActionExecutionReceipt,
    *,
    after: bool,
    actor_body_id: str,
    calibration: W1BinauralCalibration,
) -> ExactBinauralTransferPath:
    snapshot = receipt.after if after else receipt.before
    self_body = body_from_snapshot(snapshot, snapshot.self_body_id)
    ears = calibrated_ear_positions(
        self_body,
        calibration.ear_separation_mm,
    )
    if ears is None:
        raise ValueError(
            "moving source continuity requires cardinal two-ear geometry"
        )
    actor = body_from_snapshot(snapshot, actor_body_id)
    anonymous = _anonymous_path_for_position(
        actor.pose.position,
        left_ear=ears[0],
        right_ear=ears[1],
        reference_distance_mm=calibration.reference_distance_mm,
    )
    path = ExactBinauralTransferPath(
        left_delay_samples=anonymous.left_delay_samples,
        right_delay_samples=anonymous.right_delay_samples,
        left_attenuation=anonymous.left_attenuation,
        right_attenuation=anonymous.right_attenuation,
    )
    path.verify()
    return path


def _unique_capture_index(
    capture: W1AuthenticatedMultiEmitterBinauralCapture,
    path: ExactBinauralTransferPath,
) -> int:
    matches = tuple(
        index
        for index, candidate in enumerate(capture.paths)
        if candidate == path
    )
    if len(matches) != 1:
        raise ValueError(
            "moved source has no unique path in authenticated capture"
        )
    return matches[0]


def _verify_full_field(outcome: BinauralRoomHearingOutcome) -> None:
    for occurrence in outcome.occurrences:
        for channel in occurrence.separated_field.auditory_l5.channels:
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                if (
                    not component.l4_field_tuples
                    or any(
                        tuple(name for name, _value in field_tuple.fields)
                        != DSF_FIELD_ORDER
                        for field_tuple in component.l4_field_tuples
                    )
                ):
                    raise ValueError(
                        "moving source occurrence lost explicit DSF fields"
                    )


@dataclass(frozen=True, slots=True)
class AuthenticatedMoveStep:
    command_payload: bytes
    execution_receipt: ActionExecutionReceipt


@dataclass(frozen=True, slots=True)
class W1MovingMultiEmitterContinuity:
    lineage_token_sha256: str
    prior_capture_receipt_sha256: str
    current_capture_receipt_sha256: str
    prior_source_ordinal: int
    current_source_ordinal: int
    prior_path: ExactBinauralTransferPath
    current_path: ExactBinauralTransferPath
    prior_auditory_occurrence_receipt_sha256: str
    current_auditory_occurrence_receipt_sha256: str
    movement_execution_receipt_sha256s: tuple[str, ...]
    prior_continuity_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def authority_payload(self) -> dict[str, object]:
        return {
            "current_auditory_occurrence_receipt_sha256": (
                self.current_auditory_occurrence_receipt_sha256
            ),
            "current_capture_receipt_sha256": (
                self.current_capture_receipt_sha256
            ),
            "current_path": _path_payload(self.current_path),
            "current_source_ordinal": self.current_source_ordinal,
            "lineage_token_sha256": self.lineage_token_sha256,
            "movement_execution_receipt_sha256s": list(
                self.movement_execution_receipt_sha256s
            ),
            "prior_auditory_occurrence_receipt_sha256": (
                self.prior_auditory_occurrence_receipt_sha256
            ),
            "prior_capture_receipt_sha256": (
                self.prior_capture_receipt_sha256
            ),
            "prior_continuity_receipt_sha256": (
                self.prior_continuity_receipt_sha256
            ),
            "prior_path": _path_payload(self.prior_path),
            "prior_source_ordinal": self.prior_source_ordinal,
            "schema": MOVING_SOURCE_CONTINUITY_AUTHORITY_SCHEMA,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(
            authority_key,
            "moving source continuity authority key",
        )
        for value, name in (
            (self.lineage_token_sha256, "moving source lineage"),
            (
                self.prior_capture_receipt_sha256,
                "moving source prior capture",
            ),
            (
                self.current_capture_receipt_sha256,
                "moving source current capture",
            ),
            (
                self.prior_auditory_occurrence_receipt_sha256,
                "moving source prior occurrence",
            ),
            (
                self.current_auditory_occurrence_receipt_sha256,
                "moving source current occurrence",
            ),
        ):
            _sha256(value, name)
        if self.prior_continuity_receipt_sha256 is not None:
            _sha256(
                self.prior_continuity_receipt_sha256,
                "moving source prior continuity",
            )
        if (
            not self.movement_execution_receipt_sha256s
            or any(
                not isinstance(value, str)
                for value in self.movement_execution_receipt_sha256s
            )
        ):
            raise ValueError("moving source causal chain is empty")
        for value in self.movement_execution_receipt_sha256s:
            _sha256(value, "moving source execution")
        self.prior_path.verify()
        self.current_path.verify()
        if (
            isinstance(self.prior_source_ordinal, bool)
            or isinstance(self.current_source_ordinal, bool)
            or not isinstance(self.prior_source_ordinal, int)
            or not isinstance(self.current_source_ordinal, int)
            or self.prior_source_ordinal < 0
            or self.current_source_ordinal < 0
            or self.prior_source_ordinal == self.current_source_ordinal
        ):
            raise ValueError(
                "moving source did not cross anonymous spatial order"
            )
        payload = self.authority_payload()
        expected_hmac = hmac.new(
            key,
            MOVING_SOURCE_CONTINUITY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("moving source continuity authority changed")


class W1MovingMultiEmitterContinuityOwner:
    """Bounded receipt-only owner of one causally moving source lineage."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        capture_authority_key: bytes | str,
        room_hearing_authority_key: bytes | str,
        calibration: W1BinauralCalibration | None = None,
        max_transitions: int = MAX_RETAINED_TRANSITIONS,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "moving source continuity requires W1 world authority"
            )
        if (
            isinstance(max_transitions, bool)
            or not isinstance(max_transitions, int)
            or not 1 <= max_transitions <= MAX_RETAINED_TRANSITIONS
        ):
            raise ValueError(
                "moving source continuity capacity is invalid"
            )
        mounted_calibration = calibration or W1BinauralCalibration()
        mounted_calibration.verify()
        self._key = _key(
            authority_key,
            "moving source continuity authority key",
        )
        self._world = world_authority
        self._capture_key = _key(
            capture_authority_key,
            "moving source capture authority key",
        )
        self._hearing_key = _key(
            room_hearing_authority_key,
            "moving source hearing authority key",
        )
        self._calibration = mounted_calibration
        self._max_transitions = max_transitions
        self._anchor: W1MovingMultiEmitterContinuity | None = None
        self._transitions: list[W1MovingMultiEmitterContinuity] = []
        self._lock = threading.RLock()

    def settle(
        self,
        *,
        prior_capture: W1AuthenticatedMultiEmitterBinauralCapture,
        current_capture: W1AuthenticatedMultiEmitterBinauralCapture,
        prior_hearing: BinauralRoomHearingOutcome,
        current_hearing: BinauralRoomHearingOutcome,
        movement_steps: tuple[AuthenticatedMoveStep, ...],
    ) -> W1MovingMultiEmitterContinuity:
        prior_capture.verify(self._capture_key)
        current_capture.verify(self._capture_key)
        prior_hearing.verify(self._hearing_key)
        current_hearing.verify(self._hearing_key)
        if (
            prior_capture.state is not W1MultiEmitterCaptureState.CAPTURED
            or current_capture.state
            is not W1MultiEmitterCaptureState.CAPTURED
            or prior_hearing.state
            is not BinauralRoomHearingState.SEPARATED_OCCURRENCES
            or current_hearing.state
            is not BinauralRoomHearingState.SEPARATED_OCCURRENCES
            or prior_hearing.evidence_receipt_sha256
            != prior_capture.authority_receipt_sha256
            or current_hearing.evidence_receipt_sha256
            != current_capture.authority_receipt_sha256
        ):
            raise ValueError(
                "moving source continuity requires two separated captures"
            )
        _verify_full_field(prior_hearing)
        _verify_full_field(current_hearing)
        if not movement_steps:
            raise ValueError(
                "moving source continuity requires causal movement"
            )

        actor_body_id: str | None = None
        prior_after_receipt: str | None = None
        execution_receipts: list[str] = []
        for step in movement_steps:
            if (
                not isinstance(step, AuthenticatedMoveStep)
                or not isinstance(step.command_payload, bytes)
            ):
                raise TypeError(
                    "moving source continuity requires typed move steps"
                )
            receipt = step.execution_receipt
            self._world.verify_execution_receipt(receipt)
            command = decode_command(step.command_payload)
            if (
                not isinstance(command, MoveCommand)
                or hashlib.sha256(step.command_payload).hexdigest()
                != receipt.command_sha256
                or receipt.actor_body_id is None
                or receipt.actor_body_id == receipt.before.self_body_id
            ):
                raise ValueError(
                    "moving source continuity left external MoveCommand custody"
                )
            if actor_body_id is None:
                actor_body_id = receipt.actor_body_id
            if (
                receipt.actor_body_id != actor_body_id
                or (
                    prior_after_receipt is not None
                    and receipt.before.authority_receipt_sha256
                    != prior_after_receipt
                )
            ):
                raise ValueError(
                    "moving source execution chain is not contiguous"
                )
            prior_after_receipt = receipt.after.authority_receipt_sha256
            execution_receipts.append(
                receipt.authority_receipt_sha256
            )

        if actor_body_id is None:
            raise RuntimeError("moving source actor disappeared")
        first = movement_steps[0].execution_receipt
        last = movement_steps[-1].execution_receipt
        prior_path = _path_at(
            first,
            after=False,
            actor_body_id=actor_body_id,
            calibration=self._calibration,
        )
        current_path = _path_at(
            last,
            after=True,
            actor_body_id=actor_body_id,
            calibration=self._calibration,
        )
        prior_index = _unique_capture_index(prior_capture, prior_path)
        current_index = _unique_capture_index(
            current_capture,
            current_path,
        )
        prior_ordinal = prior_capture.anonymous_visual_ordinals[
            prior_index
        ]
        current_ordinal = current_capture.anonymous_visual_ordinals[
            current_index
        ]
        if prior_ordinal == current_ordinal:
            raise ValueError(
                "moving source did not cross anonymous spatial order"
            )
        prior_occurrence = prior_hearing.occurrences[prior_index]
        current_occurrence = current_hearing.occurrences[current_index]

        with self._lock:
            prior_continuity = None
            if self._anchor is not None:
                if (
                    self._anchor.current_capture_receipt_sha256
                    != prior_capture.authority_receipt_sha256
                    or self._anchor.current_source_ordinal
                    != prior_ordinal
                    or self._anchor.current_path != prior_path
                    or self._anchor
                    .current_auditory_occurrence_receipt_sha256
                    != prior_occurrence.authority_receipt_sha256
                ):
                    raise ValueError(
                        "moving source prior lineage anchor changed"
                    )
                lineage = self._anchor.lineage_token_sha256
                prior_continuity = (
                    self._anchor.authority_receipt_sha256
                )
            else:
                lineage = hmac.new(
                    self._key,
                    MOVING_SOURCE_LINEAGE_DOMAIN + _canonical({
                        "movement_execution_receipt_sha256": (
                            execution_receipts[0]
                        ),
                        "prior_capture_receipt_sha256": (
                            prior_capture.authority_receipt_sha256
                        ),
                        "prior_path": prior_path.payload(),
                    }),
                    hashlib.sha256,
                ).hexdigest()
            draft = W1MovingMultiEmitterContinuity(
                lineage_token_sha256=lineage,
                prior_capture_receipt_sha256=(
                    prior_capture.authority_receipt_sha256
                ),
                current_capture_receipt_sha256=(
                    current_capture.authority_receipt_sha256
                ),
                prior_source_ordinal=prior_ordinal,
                current_source_ordinal=current_ordinal,
                prior_path=prior_path,
                current_path=current_path,
                prior_auditory_occurrence_receipt_sha256=(
                    prior_occurrence.authority_receipt_sha256
                ),
                current_auditory_occurrence_receipt_sha256=(
                    current_occurrence.authority_receipt_sha256
                ),
                movement_execution_receipt_sha256s=tuple(
                    execution_receipts
                ),
                prior_continuity_receipt_sha256=prior_continuity,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            payload = draft.authority_payload()
            signature = hmac.new(
                self._key,
                MOVING_SOURCE_CONTINUITY_DOMAIN
                + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            result = W1MovingMultiEmitterContinuity(
                lineage_token_sha256=draft.lineage_token_sha256,
                prior_capture_receipt_sha256=(
                    draft.prior_capture_receipt_sha256
                ),
                current_capture_receipt_sha256=(
                    draft.current_capture_receipt_sha256
                ),
                prior_source_ordinal=draft.prior_source_ordinal,
                current_source_ordinal=draft.current_source_ordinal,
                prior_path=draft.prior_path,
                current_path=draft.current_path,
                prior_auditory_occurrence_receipt_sha256=(
                    draft.prior_auditory_occurrence_receipt_sha256
                ),
                current_auditory_occurrence_receipt_sha256=(
                    draft.current_auditory_occurrence_receipt_sha256
                ),
                movement_execution_receipt_sha256s=(
                    draft.movement_execution_receipt_sha256s
                ),
                prior_continuity_receipt_sha256=(
                    draft.prior_continuity_receipt_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )
            result.verify(self._key)
            self._anchor = result
            self._transitions.append(result)
            del self._transitions[:-self._max_transitions]
            return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active_lineage": self._anchor is not None,
                "max_transitions": self._max_transitions,
                "retained_raw_media_bytes": 0,
                "retained_transitions": len(self._transitions),
                "schema": (
                    "guala.w1.moving_multi_emitter_continuity_status.v1"
                ),
            }


__all__ = [
    "AuthenticatedMoveStep",
    "MAX_RETAINED_TRANSITIONS",
    "MOVING_SOURCE_CONTINUITY_AUTHORITY_SCHEMA",
    "MOVING_SOURCE_CONTINUITY_SCHEMA",
    "W1MovingMultiEmitterContinuity",
    "W1MovingMultiEmitterContinuityOwner",
]
