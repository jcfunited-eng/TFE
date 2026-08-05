"""Exact W1 physical action selection for one tutoring distinction.

This owner turns no sense name, THING identity, or causal-relation name into a
command.  Those values only authorize an attempt and later verify its observed
outcome.  Candidate actions come solely from the current authenticated W1
geometry: one exact cardinal forward body-radius act, region centres, and the
two body-clearance positions of each portal.

Every candidate is prepared by the W1 authority and retained only when the
world itself proves that it is physically applicable.  Translation and
rotation remain separate integer dimensions.  Selection succeeds only for one
unique componentwise nondominated minimum; ties and incomparability are
silence.  No score, scalar norm, threshold, identity ordering, label lookup,
randomness, clock, or retained sample participates.

The owner retains at most one authenticated quiet result, keyed only by the
opportunity receipt and current W1 observation receipt.  An unchanged silent
or unsupported result therefore cannot repeat physical preparation on every
scheduler tick; either receipt changing invalidates it.  The latch survives
cold restore and never retains an executable action.  The resulting lived
occurrence remains owned by the existing curriculum, causal THING, and
full-field authorities.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.custody_native_tutoring_curriculum import (
    CustodyNativeTutoringCurriculumOwner,
    CustodyNativeTutoringOpportunity,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    MoveCommand,
    ObservationSnapshot,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
)


SELECTION_SCHEMA = "guala.custody_native_tutoring.action_selection.v1"
STATUS_SCHEMA = "guala.custody_native_tutoring.action_selector.status.v1"
LATCH_STATE_SCHEMA = (
    "guala.custody_native_tutoring.action_selector_latch.state.v1"
)
LATCH_ENVELOPE_SCHEMA = (
    "guala.custody_native_tutoring.action_selector_latch.state_hmac.v1"
)
SUPPORTED_MATERIAL_SENSES = ("sight", "touch", "body")
_SELECTION_DOMAIN = b"guala-custody-native-tutoring-action-selection-v1\0"
_LATCH_STATE_DOMAIN = (
    b"guala-custody-native-tutoring-action-selector-latch-state-v1\0"
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("tutoring action authority key changed")
    return hashlib.sha256(_SELECTION_DOMAIN + raw).digest()


def _wrapped_heading_distance(left: int, right: int) -> int:
    delta = abs(left - right) % 360_000
    return min(delta, 360_000 - delta)


@dataclass(frozen=True, slots=True)
class TutoringPhysicalActionDimensions:
    translation_x_mm: int
    translation_y_mm: int
    translation_z_mm: int
    rotation_yaw_millidegrees: int

    def verify(self) -> None:
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in (
                self.translation_x_mm,
                self.translation_y_mm,
                self.translation_z_mm,
                self.rotation_yaw_millidegrees,
            )
        ):
            raise ValueError("tutoring physical action dimensions changed")

    def record(self) -> dict[str, int]:
        self.verify()
        return {
            "rotation_yaw_millidegrees": self.rotation_yaw_millidegrees,
            "translation_x_mm": self.translation_x_mm,
            "translation_y_mm": self.translation_y_mm,
            "translation_z_mm": self.translation_z_mm,
        }


def _strictly_componentwise_below(
    left: TutoringPhysicalActionDimensions,
    right: TutoringPhysicalActionDimensions,
) -> bool:
    left.verify()
    right.verify()
    pairs = tuple(zip(
        left.record().values(),
        right.record().values(),
        strict=True,
    ))
    return (
        all(left_value <= right_value for left_value, right_value in pairs)
        and any(left_value < right_value for left_value, right_value in pairs)
    )


class TutoringActionSelectionState(str, Enum):
    SELECTED = "selected"
    SILENT = "silent"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class CustodyNativeTutoringActionSelection:
    state: TutoringActionSelectionState
    reason: str
    opportunity_receipt_sha256: str
    thing_id: str
    target_sense: str
    target_relation: str
    world_observation_receipt_sha256: str
    command_payload: bytes | None
    physical_dimensions: TutoringPhysicalActionDimensions | None
    admissible_candidate_count: int
    minimal_candidate_count: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "admissible_candidate_count": self.admissible_candidate_count,
            "command_payload_base64": (
                base64.b64encode(self.command_payload).decode("ascii")
                if self.command_payload is not None
                else None
            ),
            "minimal_candidate_count": self.minimal_candidate_count,
            "opportunity_receipt_sha256": (
                self.opportunity_receipt_sha256
            ),
            "physical_dimensions": (
                self.physical_dimensions.record()
                if self.physical_dimensions is not None
                else None
            ),
            "reason": self.reason,
            "schema": SELECTION_SCHEMA,
            "state": self.state.value,
            "target_relation": self.target_relation,
            "target_sense": self.target_sense,
            "thing_id": self.thing_id,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (
                self.opportunity_receipt_sha256,
                "opportunity receipt",
            ),
            (
                self.world_observation_receipt_sha256,
                "world observation receipt",
            ),
            (self.thing_id, "THING identity"),
            (self.authority_hmac_sha256, "selection HMAC"),
            (self.authority_receipt_sha256, "selection receipt"),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in value
                )
            ):
                raise ValueError(f"tutoring action {name} changed")
        if (
            not isinstance(self.state, TutoringActionSelectionState)
            or not isinstance(self.reason, str)
            or not self.reason
            or self.reason != self.reason.strip()
            or not isinstance(self.target_sense, str)
            or not self.target_sense
            or not isinstance(self.target_relation, str)
            or not self.target_relation
            or isinstance(self.admissible_candidate_count, bool)
            or not isinstance(self.admissible_candidate_count, int)
            or self.admissible_candidate_count < 0
            or isinstance(self.minimal_candidate_count, bool)
            or not isinstance(self.minimal_candidate_count, int)
            or self.minimal_candidate_count < 0
            or self.minimal_candidate_count
            > self.admissible_candidate_count
        ):
            raise ValueError("tutoring action selection boundary changed")
        if self.state is TutoringActionSelectionState.SELECTED:
            if (
                not isinstance(self.command_payload, bytes)
                or not self.command_payload
                or not isinstance(
                    self.physical_dimensions,
                    TutoringPhysicalActionDimensions,
                )
                or self.minimal_candidate_count != 1
                or self.admissible_candidate_count < 1
                or self.reason
                != "unique_componentwise_minimal_physical_action"
            ):
                raise ValueError(
                    "selected tutoring action structure changed"
                )
            self.physical_dimensions.verify()
        elif (
            self.command_payload is not None
            or self.physical_dimensions is not None
            or self.reason not in {
                "sound_requires_acoustic_actuator",
                "physical_receptor_unavailable",
                "opportunity_already_has_lived_attempt",
                "no_unique_currently_held_thing",
                "no_physically_admissible_action",
                "no_unique_componentwise_minimal_action",
            }
        ):
            raise ValueError("silent tutoring action structure changed")
        signature = hmac.new(
            key,
            _SELECTION_DOMAIN + _canonical(self.payload()),
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
            raise ValueError("tutoring action selection authority changed")


@dataclass(frozen=True, slots=True)
class _Candidate:
    command_payload: bytes
    dimensions: TutoringPhysicalActionDimensions


class CustodyNativeTutoringActionSelector:
    """Select one exact material W1 action for a fresh opportunity."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        curriculum_owner: CustodyNativeTutoringCurriculumOwner,
        thing_owner: CausalThingMosaicOwner,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
    ) -> None:
        if not isinstance(
            curriculum_owner,
            CustodyNativeTutoringCurriculumOwner,
        ):
            raise TypeError(
                "tutoring action selector requires its curriculum owner"
            )
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "tutoring action selector requires its causal THING owner"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("tutoring action selector requires the W1 world")
        if not isinstance(
            physical_authority,
            W1AudiovisualPhysicalEvidenceAuthority,
        ):
            raise TypeError(
                "tutoring action selector requires W1 full-field evidence"
            )
        self._key = _key(authority_key)
        self._curriculum = curriculum_owner
        self._things = thing_owner
        self._world = world_authority
        self._physical = physical_authority
        self._unchanged_result_latch: (
            CustodyNativeTutoringActionSelection | None
        ) = None
        self._lock = threading.RLock()

    def _decode_selection(
        self,
        value: object,
    ) -> CustodyNativeTutoringActionSelection:
        expected = {
            "admissible_candidate_count",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "command_payload_base64",
            "minimal_candidate_count",
            "opportunity_receipt_sha256",
            "physical_dimensions",
            "reason",
            "schema",
            "state",
            "target_relation",
            "target_sense",
            "thing_id",
            "world_observation_receipt_sha256",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected
            or value.get("schema") != SELECTION_SCHEMA
        ):
            raise ValueError("tutoring action selection record changed")
        encoded_command = value.get("command_payload_base64")
        if encoded_command is None:
            command_payload = None
        elif isinstance(encoded_command, str):
            try:
                command_payload = base64.b64decode(
                    encoded_command,
                    validate=True,
                )
            except Exception as error:
                raise ValueError(
                    "tutoring action command encoding changed"
                ) from error
            if (
                base64.b64encode(command_payload).decode("ascii")
                != encoded_command
            ):
                raise ValueError(
                    "tutoring action command encoding changed"
                )
        else:
            raise ValueError("tutoring action command encoding changed")
        dimensions_record = value.get("physical_dimensions")
        if dimensions_record is None:
            dimensions = None
        elif (
            isinstance(dimensions_record, dict)
            and set(dimensions_record)
            == {
                "rotation_yaw_millidegrees",
                "translation_x_mm",
                "translation_y_mm",
                "translation_z_mm",
            }
        ):
            dimensions = TutoringPhysicalActionDimensions(
                translation_x_mm=dimensions_record[
                    "translation_x_mm"
                ],
                translation_y_mm=dimensions_record[
                    "translation_y_mm"
                ],
                translation_z_mm=dimensions_record[
                    "translation_z_mm"
                ],
                rotation_yaw_millidegrees=dimensions_record[
                    "rotation_yaw_millidegrees"
                ],
            )
        else:
            raise ValueError(
                "tutoring action physical dimensions changed"
            )
        try:
            state = TutoringActionSelectionState(value.get("state"))
        except Exception as error:
            raise ValueError(
                "tutoring action selection state changed"
            ) from error
        selection = CustodyNativeTutoringActionSelection(
            state=state,
            reason=value.get("reason"),
            opportunity_receipt_sha256=value.get(
                "opportunity_receipt_sha256"
            ),
            thing_id=value.get("thing_id"),
            target_sense=value.get("target_sense"),
            target_relation=value.get("target_relation"),
            world_observation_receipt_sha256=value.get(
                "world_observation_receipt_sha256"
            ),
            command_payload=command_payload,
            physical_dimensions=dimensions,
            admissible_candidate_count=value.get(
                "admissible_candidate_count"
            ),
            minimal_candidate_count=value.get(
                "minimal_candidate_count"
            ),
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        selection.verify(self._key)
        return selection

    def snapshot_encoded(self) -> bytes:
        """Persist at most one physical-receipt keyed quiet result."""

        with self._lock:
            body = {
                "schema": LATCH_STATE_SCHEMA,
                "unchanged_result_latch": (
                    self._unchanged_result_latch.record()
                    if self._unchanged_result_latch is not None
                    else None
                ),
            }
            signature = hmac.new(
                self._key,
                _LATCH_STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest()
            return _canonical({
                "body": body,
                "schema": LATCH_ENVELOPE_SCHEMA,
                "state_hmac_sha256": signature,
            })

    def restore_encoded(self, encoded: bytes) -> None:
        """Restore one exact quiet-result latch into a fresh selector."""

        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("tutoring action latch encoding changed")
        try:
            value = json.loads(encoded)
        except Exception as error:
            raise ValueError(
                "tutoring action latch encoding changed"
            ) from error
        if _canonical(value) != encoded:
            raise ValueError(
                "tutoring action latch encoding is not canonical"
            )
        if (
            not isinstance(value, dict)
            or set(value) != {"body", "schema", "state_hmac_sha256"}
            or value.get("schema") != LATCH_ENVELOPE_SCHEMA
            or not isinstance(value.get("body"), dict)
            or set(value["body"])
            != {"schema", "unchanged_result_latch"}
            or value["body"].get("schema") != LATCH_STATE_SCHEMA
        ):
            raise ValueError("tutoring action latch schema changed")
        signature = value.get("state_hmac_sha256")
        expected = hmac.new(
            self._key,
            _LATCH_STATE_DOMAIN + _canonical(value["body"]),
            hashlib.sha256,
        ).hexdigest()
        if (
            not isinstance(signature, str)
            or not hmac.compare_digest(signature, expected)
        ):
            raise ValueError("tutoring action latch authority changed")
        record = value["body"]["unchanged_result_latch"]
        selection = (
            self._decode_selection(record)
            if record is not None
            else None
        )
        if (
            selection is not None
            and selection.state is TutoringActionSelectionState.SELECTED
        ):
            raise ValueError(
                "tutoring action latch retained an executable action"
            )
        with self._lock:
            if self._unchanged_result_latch is not None:
                raise RuntimeError(
                    "tutoring action latch restore requires a fresh selector"
                )
            self._unchanged_result_latch = selection
            if self.snapshot_encoded() != encoded:
                raise ValueError(
                    "tutoring action latch cold restore changed state"
                )

    def _retain_quiet_result(
        self,
        selection: CustodyNativeTutoringActionSelection,
    ) -> CustodyNativeTutoringActionSelection:
        if selection.state is TutoringActionSelectionState.SELECTED:
            raise ValueError("executable tutoring action cannot be latched")
        self._unchanged_result_latch = selection
        return selection

    @staticmethod
    def _self_body(observation: ObservationSnapshot):
        matches = tuple(
            value
            for value in observation.bodies
            if value.body_id == observation.self_body_id
        )
        if len(matches) != 1:
            raise ValueError("tutoring action self body changed")
        return matches[0]

    @staticmethod
    def _target_poses(
        observation: ObservationSnapshot,
    ) -> tuple[PoseMM, ...]:
        body = CustodyNativeTutoringActionSelector._self_body(observation)
        held = tuple(
            value
            for value in observation.objects
            if value.held_by_body_id == observation.self_body_id
        )
        if len(held) != 1:
            return ()
        carried_radius = max(body.radius_mm, held[0].radius_mm)
        positions: set[tuple[int, int, int]] = set()
        # W1 headings use exact millidegrees.  At the four exact cardinal
        # headings, one body-radius forward translation is the smallest
        # locomotor act supplied by the body's own geometry.  Non-cardinal
        # headings gain no trigonometric approximation.
        forward_by_heading = {
            0: (body.radius_mm, 0),
            90_000: (0, body.radius_mm),
            180_000: (-body.radius_mm, 0),
            270_000: (0, -body.radius_mm),
        }
        forward = forward_by_heading.get(
            body.pose.heading_millidegrees
        )
        if forward is not None:
            positions.add((
                body.pose.position.x + forward[0],
                body.pose.position.y + forward[1],
                body.pose.position.z,
            ))
        for region in observation.regions:
            positions.add((
                (region.bounds.minimum.x + region.bounds.maximum.x) // 2,
                (region.bounds.minimum.y + region.bounds.maximum.y) // 2,
                region.bounds.minimum.z,
            ))
        region_by_id = {
            value.region_id: value for value in observation.regions
        }
        for portal in observation.portals:
            aperture_midpoint = (
                portal.aperture_min_mm + portal.aperture_max_mm
            ) // 2
            for region_id in portal.region_ids:
                region = region_by_id[region_id]
                if portal.axis == "x":
                    x = (
                        portal.plane_mm - carried_radius
                        if region.bounds.maximum.x == portal.plane_mm
                        else portal.plane_mm + carried_radius
                    )
                    positions.add((
                        x,
                        aperture_midpoint,
                        region.bounds.minimum.z,
                    ))
                else:
                    y = (
                        portal.plane_mm - carried_radius
                        if region.bounds.maximum.y == portal.plane_mm
                        else portal.plane_mm + carried_radius
                    )
                    positions.add((
                        aperture_midpoint,
                        y,
                        region.bounds.minimum.z,
                    ))
        current = body.pose.position
        return tuple(
            PoseMM(
                PositionMM(x, y, z),
                body.pose.heading_millidegrees,
            )
            for x, y, z in sorted(positions)
            if (x, y, z) != (current.x, current.y, current.z)
        )

    def _same_held_thing(
        self,
        opportunity: CustodyNativeTutoringOpportunity,
        observation: ObservationSnapshot,
    ) -> bool:
        matching = tuple(
            value
            for value in self._things.mosaics
            if value.thing_id == opportunity.thing_id
        )
        if len(matching) != 1 or not matching[0].partitions:
            return False
        latest = matching[0].partitions[-1]
        held = tuple(
            value
            for value in observation.objects
            if value.held_by_body_id == observation.self_body_id
        )
        return (
            len(held) == 1
            and latest.world_revision == observation.revision
            and latest.world_observation_receipt_sha256
            == observation.authority_receipt_sha256
        )

    def _admissible_candidates(
        self,
        opportunity: CustodyNativeTutoringOpportunity,
        observation: ObservationSnapshot,
        duration_microseconds: int,
    ) -> tuple[_Candidate, ...]:
        body = self._self_body(observation)
        candidates = []
        for pose in self._target_poses(observation):
            payload = encode_command(MoveCommand(
                target_pose=pose,
                duration_microseconds=duration_microseconds,
            ))
            candidate_intent = _digest({
                "command_payload_base64": (
                    base64.b64encode(payload).decode("ascii")
                ),
                "opportunity_receipt_sha256": (
                    opportunity.authority_receipt_sha256
                ),
                "schema": (
                    "guala.custody_native_tutoring."
                    "candidate_intent.v1"
                ),
                "world_observation_receipt_sha256": (
                    observation.authority_receipt_sha256
                ),
            })
            prepared = self._world.prepare_port_command(
                port_id=self._world.port_id,
                command_payload=payload,
                causal_intent_receipt_sha256=candidate_intent,
                expected_revision=observation.revision,
            )
            if isinstance(prepared, ActionExecutionReceipt):
                if prepared.disposition != "rejected":
                    raise RuntimeError(
                        "tutoring action candidate preparation changed"
                    )
                continue
            self._world.verify_prepared_action(prepared)
            try:
                evidence = (
                    self._physical.mount_authenticated_action_outcome(
                        prepared.execution_receipt,
                        commit=False,
                    )
                )
                self._physical.verify_mount(evidence)
            finally:
                self._world.discard_prepared_action(prepared)
            if (
                evidence.state is not W1EvidenceState.OBSERVED
                or evidence.causal_settlement is None
                or evidence.evidence_receipt is None
            ):
                continue
            dimensions = TutoringPhysicalActionDimensions(
                translation_x_mm=abs(
                    pose.position.x - body.pose.position.x
                ),
                translation_y_mm=abs(
                    pose.position.y - body.pose.position.y
                ),
                translation_z_mm=abs(
                    pose.position.z - body.pose.position.z
                ),
                rotation_yaw_millidegrees=_wrapped_heading_distance(
                    pose.heading_millidegrees,
                    body.pose.heading_millidegrees,
                ),
            )
            dimensions.verify()
            candidates.append(_Candidate(payload, dimensions))
        return tuple(candidates)

    def _seal(
        self,
        *,
        state: TutoringActionSelectionState,
        reason: str,
        opportunity: CustodyNativeTutoringOpportunity,
        observation: ObservationSnapshot,
        selected: _Candidate | None,
        admissible_count: int,
        minimal_count: int,
    ) -> CustodyNativeTutoringActionSelection:
        provisional = CustodyNativeTutoringActionSelection(
            state=state,
            reason=reason,
            opportunity_receipt_sha256=(
                opportunity.authority_receipt_sha256
            ),
            thing_id=opportunity.thing_id,
            target_sense=opportunity.target_sense,
            target_relation=opportunity.target_relation,
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            command_payload=(
                selected.command_payload if selected is not None else None
            ),
            physical_dimensions=(
                selected.dimensions if selected is not None else None
            ),
            admissible_candidate_count=admissible_count,
            minimal_candidate_count=minimal_count,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _SELECTION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CustodyNativeTutoringActionSelection(
            **{
                field: getattr(provisional, field)
                for field in (
                    "state",
                    "reason",
                    "opportunity_receipt_sha256",
                    "thing_id",
                    "target_sense",
                    "target_relation",
                    "world_observation_receipt_sha256",
                    "command_payload",
                    "physical_dimensions",
                    "admissible_candidate_count",
                    "minimal_candidate_count",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def select(
        self,
        opportunity: CustodyNativeTutoringOpportunity,
        *,
        duration_microseconds: int,
    ) -> CustodyNativeTutoringActionSelection:
        with self._lock:
            self._curriculum.verify_opportunity(opportunity)
            observation = self._world.observation_snapshot()
            latched = self._unchanged_result_latch
            if (
                latched is not None
                and latched.opportunity_receipt_sha256
                == opportunity.authority_receipt_sha256
                and latched.world_observation_receipt_sha256
                == observation.authority_receipt_sha256
            ):
                latched.verify(self._key)
                return latched
            self._unchanged_result_latch = None
            return self._select_unlatched(
                opportunity,
                observation,
                duration_microseconds,
            )

    def _select_unlatched(
        self,
        opportunity: CustodyNativeTutoringOpportunity,
        observation: ObservationSnapshot,
        duration_microseconds: int,
    ) -> CustodyNativeTutoringActionSelection:
        if opportunity.target_sense not in SUPPORTED_MATERIAL_SENSES:
            return self._retain_quiet_result(self._seal(
                state=TutoringActionSelectionState.UNSUPPORTED,
                reason=(
                    "sound_requires_acoustic_actuator"
                    if opportunity.target_sense == "sound"
                    else "physical_receptor_unavailable"
                ),
                opportunity=opportunity,
                observation=observation,
                selected=None,
                admissible_count=0,
                minimal_count=0,
            ))
        if not self._curriculum.opportunity_is_fresh(opportunity):
            return self._retain_quiet_result(self._seal(
                state=TutoringActionSelectionState.SILENT,
                reason="opportunity_already_has_lived_attempt",
                opportunity=opportunity,
                observation=observation,
                selected=None,
                admissible_count=0,
                minimal_count=0,
            ))
        if not self._same_held_thing(opportunity, observation):
            return self._retain_quiet_result(self._seal(
                state=TutoringActionSelectionState.SILENT,
                reason="no_unique_currently_held_thing",
                opportunity=opportunity,
                observation=observation,
                selected=None,
                admissible_count=0,
                minimal_count=0,
            ))
        candidates = self._admissible_candidates(
            opportunity,
            observation,
            duration_microseconds,
        )
        minima = tuple(
            candidate
            for candidate in candidates
            if not any(
                other is not candidate
                and _strictly_componentwise_below(
                    other.dimensions,
                    candidate.dimensions,
                )
                for other in candidates
            )
        )
        if len(minima) != 1:
            return self._retain_quiet_result(self._seal(
                state=TutoringActionSelectionState.SILENT,
                reason=(
                    "no_physically_admissible_action"
                    if not candidates
                    else "no_unique_componentwise_minimal_action"
                ),
                opportunity=opportunity,
                observation=observation,
                selected=None,
                admissible_count=len(candidates),
                minimal_count=len(minima),
            ))
        self._unchanged_result_latch = None
        return self._seal(
            state=TutoringActionSelectionState.SELECTED,
            reason="unique_componentwise_minimal_physical_action",
            opportunity=opportunity,
            observation=observation,
            selected=minima[0],
            admissible_count=len(candidates),
            minimal_count=1,
        )

    def verify_selection(
        self,
        value: CustodyNativeTutoringActionSelection,
        *,
        opportunity: CustodyNativeTutoringOpportunity,
    ) -> None:
        if not isinstance(value, CustodyNativeTutoringActionSelection):
            raise ValueError("tutoring action selection changed authority")
        value.verify(self._key)
        self._curriculum.verify_opportunity(opportunity)
        observation = self._world.observation_snapshot()
        if (
            value.opportunity_receipt_sha256
            != opportunity.authority_receipt_sha256
            or value.thing_id != opportunity.thing_id
            or value.target_sense != opportunity.target_sense
            or value.target_relation != opportunity.target_relation
            or value.world_observation_receipt_sha256
            != observation.authority_receipt_sha256
        ):
            raise ValueError("tutoring action selection changed authority")

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "full_field_outcome_required": True,
                "physical_action_dimensions": (
                    "translation_x_mm",
                    "translation_y_mm",
                    "translation_z_mm",
                    "rotation_yaw_millidegrees",
                ),
                "reduced_approximation": False,
                "retained_selection_count": (
                    1
                    if self._unchanged_result_latch is not None
                    else 0
                ),
                "schema": STATUS_SCHEMA,
                "stateful": True,
                "supported_senses": list(SUPPORTED_MATERIAL_SENSES),
                "unsupported_by_material_selector": {
                    "smell": "physical_receptor_unavailable",
                    "sound": "separate_acoustic_actuator_required",
                    "taste": "physical_receptor_unavailable",
                },
            }


__all__ = (
    "STATUS_SCHEMA",
    "LATCH_ENVELOPE_SCHEMA",
    "LATCH_STATE_SCHEMA",
    "SUPPORTED_MATERIAL_SENSES",
    "CustodyNativeTutoringActionSelection",
    "CustodyNativeTutoringActionSelector",
    "TutoringActionSelectionState",
    "TutoringPhysicalActionDimensions",
)
