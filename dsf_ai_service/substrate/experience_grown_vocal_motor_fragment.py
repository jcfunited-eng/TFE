"""Durable compact motor fragments earned by an immediate lived consequence.

This owner seals no word, label, meaning, waveform, or inquiry-action binding.
It accepts either one live body-owned transient candidate or the exact
HMAC-sealed pending custody retained before that candidate was finalized,
the active unresolved inquiry witness that caused the act, and one immediate
authenticated W1 multisensory consequence.  Only an exact transition to one
unique physical THING can admit the body-derived compact articulatory program.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryProgram,
    ArticulatoryProgramAdmissionUndo,
    ArticulatorySelfVocalMotorOwner,
    PreparedArticulatoryProgramAdmission,
)
from dsf_ai_service.substrate.causal_inquiry import (
    CausalInquiryOwner,
    InquiryNeed,
    InquiryWitness,
)
from dsf_ai_service.substrate.causal_inquiry_tutor_authority import (
    CausalInquiryTutorAuthorizationVerifier,
    CausalInquiryTutorConsequenceAuthorizationReceipt,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.embodied_vocal_body import (
    BodyOwnedMotorFragmentCustody,
    EmbodiedVocalBodyAuthority,
    TransientVocalCandidate,
)
from dsf_ai_service.substrate.embodiment_world import (
    SECOND_BODY_PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.pending_body_owned_vocal_consequence import (
    PendingBodyOwnedVocalConsequenceOwner,
    PendingBodyOwnedVocalConsequenceRecord,
    RestoredPendingBodyOwnedVocalCustody,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    CompanionVocalEpisodeIntentReceipt,
    W1CompanionVocalExperienceAuthority,
)


FRAGMENT_SCHEMA = "guala.experience_grown_vocal_motor_fragment.v1"
STATE_SCHEMA = "guala.experience_grown_vocal_motor_fragment.state.v1"
ENVELOPE_SCHEMA = (
    "guala.experience_grown_vocal_motor_fragment.state_hmac.v1"
)
_FRAGMENT_DOMAIN = b"guala-experience-grown-vocal-fragment-v1\0"
_STATE_DOMAIN = b"guala-experience-grown-vocal-fragment-state-v1\0"
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("vocal-fragment authority key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("vocal-fragment authority key is outside boundary")
    return result


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} is outside its exact boundary")
    return value


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalMotorFragment:
    fragment_id: str
    program_id: str
    program_authority_receipt_sha256: str
    command_graph_sha256: str
    candidate_receipt_sha256: str
    transient_act_id: str
    pressure_sha256: str
    need_receipt_sha256: str
    witness_receipt_sha256: str
    prior_route_state: str
    prior_thing_ids: tuple[str, ...]
    candidate_world_before_receipt_sha256: str
    candidate_world_after_receipt_sha256: str
    candidate_world_execution_receipt_sha256: str
    consequence_intent_receipt_sha256: str
    consequence_execution_receipt_sha256: str
    consequence_settlement_receipt_sha256: str
    consequence_custody_receipt_sha256: str
    consequence_capability_receipt_sha256: str
    consequence_source_occurrence_id: str
    consequence_boundary_receipts: tuple[tuple[str, str], ...]
    unique_thing_id: str
    tutor_authorization_receipt_sha256: str | None
    tutor_nonce_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_receipt_sha256": self.candidate_receipt_sha256,
            "candidate_world_after_receipt_sha256": (
                self.candidate_world_after_receipt_sha256
            ),
            "candidate_world_before_receipt_sha256": (
                self.candidate_world_before_receipt_sha256
            ),
            "candidate_world_execution_receipt_sha256": (
                self.candidate_world_execution_receipt_sha256
            ),
            "command_graph_sha256": self.command_graph_sha256,
            "consequence_boundary_receipts": [
                [sense, receipt]
                for sense, receipt in self.consequence_boundary_receipts
            ],
            "consequence_capability_receipt_sha256": (
                self.consequence_capability_receipt_sha256
            ),
            "consequence_custody_receipt_sha256": (
                self.consequence_custody_receipt_sha256
            ),
            "consequence_execution_receipt_sha256": (
                self.consequence_execution_receipt_sha256
            ),
            "consequence_intent_receipt_sha256": (
                self.consequence_intent_receipt_sha256
            ),
            "consequence_settlement_receipt_sha256": (
                self.consequence_settlement_receipt_sha256
            ),
            "consequence_source_occurrence_id": (
                self.consequence_source_occurrence_id
            ),
            "fragment_id": self.fragment_id,
            "need_receipt_sha256": self.need_receipt_sha256,
            "pressure_sha256": self.pressure_sha256,
            "prior_route_state": self.prior_route_state,
            "prior_thing_ids": list(self.prior_thing_ids),
            "program_authority_receipt_sha256": (
                self.program_authority_receipt_sha256
            ),
            "program_id": self.program_id,
            "schema": FRAGMENT_SCHEMA,
            "transient_act_id": self.transient_act_id,
            "tutor_authorization_receipt_sha256": (
                self.tutor_authorization_receipt_sha256
            ),
            "tutor_nonce_sha256": self.tutor_nonce_sha256,
            "unique_thing_id": self.unique_thing_id,
            "witness_receipt_sha256": self.witness_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _TransactionState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class _AuthenticatedVocalFragmentSource:
    candidate_receipt_sha256: str
    transient_act_id: str
    pressure_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_graph_sha256: str
    program: ArticulatoryProgram


@dataclass(frozen=True, slots=True)
class PreparedExperienceGrownVocalMotorFragment:
    fragment: ExperienceGrownVocalMotorFragment
    program: ArticulatoryProgram
    _motor_prepared: PreparedArticulatoryProgramAdmission = field(
        repr=False,
        compare=False,
    )
    _prior_fragments: tuple[
        ExperienceGrownVocalMotorFragment, ...
    ] = field(repr=False, compare=False)
    _staged_fragments: tuple[
        ExperienceGrownVocalMotorFragment, ...
    ] = field(repr=False, compare=False)
    _state: _TransactionState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalMotorFragmentUndo:
    _prepared: PreparedExperienceGrownVocalMotorFragment = field(
        repr=False,
        compare=False,
    )
    _motor_undo: ArticulatoryProgramAdmissionUndo = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


class ExperienceGrownVocalMotorFragmentCapacityError(RuntimeError):
    pass


class ExperienceGrownVocalMotorFragmentOwner:
    """Own compact fragment seals and their exact motor admission."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        vocal_body_owner: EmbodiedVocalBodyAuthority,
        motor_owner: ArticulatorySelfVocalMotorOwner,
        inquiry_owner: CausalInquiryOwner,
        thing_owner: CausalThingMosaicOwner,
        world_authority: EmbodimentWorldAuthority,
        companion_authority: W1CompanionVocalExperienceAuthority,
        tutor_authorization_verifier: (
            CausalInquiryTutorAuthorizationVerifier
        ),
        max_fragments: int = 32,
        max_state_bytes: int = 262_144,
    ) -> None:
        for value, expected, name in (
            (
                vocal_body_owner,
                EmbodiedVocalBodyAuthority,
                "vocal body",
            ),
            (
                motor_owner,
                ArticulatorySelfVocalMotorOwner,
                "articulatory motor",
            ),
            (inquiry_owner, CausalInquiryOwner, "causal inquiry"),
            (thing_owner, CausalThingMosaicOwner, "THING owner"),
            (
                world_authority,
                EmbodimentWorldAuthority,
                "embodiment world",
            ),
            (
                companion_authority,
                W1CompanionVocalExperienceAuthority,
                "companion W1",
            ),
            (
                tutor_authorization_verifier,
                CausalInquiryTutorAuthorizationVerifier,
                "tutor consequence verifier",
            ),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"vocal-fragment owner requires {name}")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._fragment_key = hashlib.sha256(
            _FRAGMENT_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root
        ).digest()
        self._vocal = vocal_body_owner
        self._motor = motor_owner
        self._inquiry = inquiry_owner
        self._things = thing_owner
        self._world = world_authority
        self._companion = companion_authority
        self._tutor_verifier = tutor_authorization_verifier
        self._max_fragments = _integer(
            max_fragments,
            "vocal-fragment capacity",
            minimum=1,
            maximum=4_096,
        )
        self._max_state_bytes = _integer(
            max_state_bytes,
            "vocal-fragment state capacity",
            minimum=4_096,
            maximum=4 * 1024 * 1024,
        )
        self._fragments: tuple[
            ExperienceGrownVocalMotorFragment, ...
        ] = ()
        self._prepared: (
            PreparedExperienceGrownVocalMotorFragment | None
        ) = None
        self._latest_undo: (
            ExperienceGrownVocalMotorFragmentUndo | None
        ) = None
        self._owner_authority = object()
        self._lock = threading.RLock()
        self._encoded(self._fragments)

    @property
    def fragments(
        self,
    ) -> tuple[ExperienceGrownVocalMotorFragment, ...]:
        with self._lock:
            return self._fragments

    def _verify_fragment(
        self,
        fragment: ExperienceGrownVocalMotorFragment,
    ) -> None:
        if not isinstance(
            fragment,
            ExperienceGrownVocalMotorFragment,
        ):
            raise TypeError("vocal motor fragment is not typed")
        for value, name in (
            (fragment.fragment_id, "fragment identity"),
            (fragment.program_id, "fragment program"),
            (
                fragment.program_authority_receipt_sha256,
                "fragment program authority",
            ),
            (fragment.command_graph_sha256, "command graph"),
            (fragment.candidate_receipt_sha256, "candidate"),
            (fragment.transient_act_id, "transient act"),
            (fragment.pressure_sha256, "pressure"),
            (fragment.need_receipt_sha256, "need"),
            (fragment.witness_receipt_sha256, "witness"),
            (
                fragment.candidate_world_before_receipt_sha256,
                "candidate world before",
            ),
            (
                fragment.candidate_world_after_receipt_sha256,
                "candidate world after",
            ),
            (
                fragment.candidate_world_execution_receipt_sha256,
                "candidate execution",
            ),
            (
                fragment.consequence_intent_receipt_sha256,
                "consequence intent",
            ),
            (
                fragment.consequence_execution_receipt_sha256,
                "consequence execution",
            ),
            (
                fragment.consequence_settlement_receipt_sha256,
                "consequence settlement",
            ),
            (
                fragment.consequence_custody_receipt_sha256,
                "consequence custody",
            ),
            (
                fragment.consequence_capability_receipt_sha256,
                "consequence capability",
            ),
            (
                fragment.consequence_source_occurrence_id,
                "consequence occurrence",
            ),
            (fragment.unique_thing_id, "unique THING"),
            (fragment.authority_hmac_sha256, "fragment HMAC"),
            (fragment.authority_receipt_sha256, "fragment authority"),
        ):
            _sha(value, name)
        for value, name in (
            (
                fragment.tutor_authorization_receipt_sha256,
                "tutor consequence authorization",
            ),
            (fragment.tutor_nonce_sha256, "tutor consequence nonce"),
        ):
            if value is not None:
                _sha(value, name)
        if (
            fragment.prior_route_state
            not in {"unresolved", "ambiguous"}
            or (
                fragment.prior_route_state == "unresolved"
                and fragment.prior_thing_ids
            )
            or (
                fragment.prior_route_state == "ambiguous"
                and (
                    len(fragment.prior_thing_ids) < 2
                    or fragment.unique_thing_id
                    not in fragment.prior_thing_ids
                )
            )
            or len(fragment.consequence_boundary_receipts) < 2
            or (
                fragment.tutor_authorization_receipt_sha256
                is None
            )
            != (fragment.tutor_nonce_sha256 is None)
        ):
            raise ValueError("vocal-fragment causal route changed")
        for sense, receipt in fragment.consequence_boundary_receipts:
            if not isinstance(sense, str) or not sense:
                raise ValueError("vocal-fragment sense changed")
            _sha(receipt, "vocal-fragment boundary")
        program = next(
            (
                value for value in self._motor.programs
                if value.program_id == fragment.program_id
            ),
            None,
        )
        if (
            program is None
            or program.authority_receipt_sha256
            != fragment.program_authority_receipt_sha256
            or _digest(program.as_record())
            != fragment.command_graph_sha256
        ):
            raise ValueError(
                "vocal fragment lost its compact motor command"
            )
        signature = hmac.new(
            self._fragment_key,
            _FRAGMENT_DOMAIN + _canonical(fragment.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                fragment.authority_hmac_sha256,
            )
            or fragment.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": fragment.payload(),
            })
        ):
            raise ValueError("vocal motor fragment authority changed")

    def _encoded(
        self,
        fragments: tuple[ExperienceGrownVocalMotorFragment, ...],
    ) -> bytes:
        body = {
            "fragments": [value.record() for value in fragments],
            "limits": {
                "max_fragments": self._max_fragments,
                "max_state_bytes": self._max_state_bytes,
            },
            "schema": STATE_SCHEMA,
        }
        payload = _canonical(body)
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise ExperienceGrownVocalMotorFragmentCapacityError(
                "vocal-fragment state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if (
                self._prepared is not None
                or self._latest_undo is not None
            ):
                raise RuntimeError(
                    "vocal-fragment transaction cannot persist"
                )
            for fragment in self._fragments:
                self._verify_fragment(fragment)
            return self._encoded(self._fragments)

    def _active_pair(
        self,
        need: InquiryNeed,
        witness: InquiryWitness,
    ) -> None:
        self._inquiry.snapshot_encoded()
        if (
            not isinstance(need, InquiryNeed)
            or not isinstance(witness, InquiryWitness)
            or self._inquiry.active_need != need
            or need.witness_receipt_sha256
            != witness.authority_receipt_sha256
            or sum(
                value == witness
                for value in self._inquiry.witnesses
            )
            != 1
            or witness.route_state not in {"unresolved", "ambiguous"}
        ):
            raise ValueError(
                "vocal fragment lacks its active unresolved inquiry"
            )

    @staticmethod
    def _complete_multisensory(settlement) -> tuple[
        tuple[str, str], ...
    ]:
        settlement.verify()
        observed = tuple(
            interpretation
            for interpretation in settlement.interpretations
            if interpretation.state == "observed"
        )
        if len(observed) < 2:
            raise ValueError(
                "vocal-fragment consequence is not multisensory"
            )
        for interpretation in observed:
            for substream in interpretation.substreams:
                for field_tuple in substream.field_tuples:
                    if tuple(
                        name for name, _value in field_tuple.fields
                    ) != DSF_FIELD_ORDER:
                        raise ValueError(
                            "vocal-fragment consequence lost full DSF fields"
                        )
        return tuple(
            (
                interpretation.sense,
                interpretation.boundary_receipt_sha256,
            )
            for interpretation in observed
        )

    def _require_prepare_capacity(self) -> None:
        if self._prepared is not None or self._latest_undo is not None:
            raise RuntimeError(
                "vocal-fragment owner already has a transaction"
            )
        if len(self._fragments) >= self._max_fragments:
            raise ExperienceGrownVocalMotorFragmentCapacityError(
                "vocal-fragment capacity exhausted"
            )

    def _live_source(
        self,
        candidate: TransientVocalCandidate,
        witness: InquiryWitness,
    ) -> _AuthenticatedVocalFragmentSource:
        motor_custody = self._vocal.open_motor_fragment_custody(
            candidate
        )
        self._vocal.verify_motor_fragment_custody(
            motor_custody,
            candidate,
        )
        if (
            motor_custody.world_before_receipt_sha256
            != witness.world_observation_receipt_sha256
        ):
            raise ValueError(
                "transient act is not the inquiry witness next edge"
            )
        return _AuthenticatedVocalFragmentSource(
            candidate_receipt_sha256=(
                candidate.authority_receipt_sha256
            ),
            transient_act_id=candidate.transient_act_id,
            pressure_sha256=candidate.pressure_sha256,
            world_before_receipt_sha256=(
                motor_custody.world_before_receipt_sha256
            ),
            world_after_receipt_sha256=(
                motor_custody.world_after_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                motor_custody.world_execution_receipt_sha256
            ),
            command_graph_sha256=(
                motor_custody.command_graph_sha256
            ),
            program=motor_custody.program,
        )

    def _restored_source(
        self,
        *,
        pending_custody_authority: (
            PendingBodyOwnedVocalConsequenceOwner
        ),
        pending_custody: RestoredPendingBodyOwnedVocalCustody,
        need: InquiryNeed,
        witness: InquiryWitness,
    ) -> _AuthenticatedVocalFragmentSource:
        if not isinstance(
            pending_custody_authority,
            PendingBodyOwnedVocalConsequenceOwner,
        ) or not isinstance(
            pending_custody,
            RestoredPendingBodyOwnedVocalCustody,
        ):
            raise TypeError(
                "vocal fragment requires typed restored pending custody"
            )
        pending_custody_authority.verify_restored_custody(
            pending_custody
        )
        record = pending_custody_authority.pending
        if not isinstance(
            record,
            PendingBodyOwnedVocalConsequenceRecord,
        ):
            raise ValueError(
                "restored pending vocal record is not available"
            )
        source_extent = (
            record.witness_source_time_end
            - record.witness_source_time_start
        ) * VOCAL_SAMPLE_RATE_HZ
        if (
            pending_custody.pending_id != record.pending_id
            or pending_custody.candidate_authority_receipt_sha256
            != record.candidate_authority_receipt_sha256
            or pending_custody.motor_custody_authority_receipt_sha256
            != record.motor_custody_authority_receipt_sha256
            or pending_custody.need_authority_receipt_sha256
            != record.need_authority_receipt_sha256
            or pending_custody.witness_authority_receipt_sha256
            != record.witness_authority_receipt_sha256
            or pending_custody.witness_settlement_receipt_sha256
            != record.witness_settlement_receipt_sha256
            or pending_custody.witness_source_time_start
            != record.witness_source_time_start
            or pending_custody.witness_source_time_end
            != record.witness_source_time_end
            or pending_custody.world_before_receipt_sha256
            != record.world_before_receipt_sha256
            or pending_custody.world_after_receipt_sha256
            != record.world_after_receipt_sha256
            or pending_custody.world_execution_receipt_sha256
            != record.world_execution_receipt_sha256
            or pending_custody.command_graph_sha256
            != record.command_graph_sha256
            or pending_custody.program != record.program
            or pending_custody.pending_authority_receipt_sha256
            != record.authority_receipt_sha256
            or record.need_id != need.need_id
            or record.need_authority_hmac_sha256
            != need.authority_hmac_sha256
            or record.need_authority_receipt_sha256
            != need.authority_receipt_sha256
            or record.witness_authority_hmac_sha256
            != witness.authority_hmac_sha256
            or record.witness_authority_receipt_sha256
            != witness.authority_receipt_sha256
            or record.witness_parent_custody_receipt_sha256
            != witness.parent_custody_receipt_sha256
            or record.witness_custody_capability_receipt_sha256
            != witness.custody_capability_receipt_sha256
            or record.witness_settlement_receipt_sha256
            != witness.settlement_receipt_sha256
            or record.witness_source_occurrence_id
            != witness.source_occurrence_id
            or record.witness_source_time_start
            != witness.source_time_start
            or record.witness_source_time_end
            != witness.source_time_end
            or record.witness_world_observation_receipt_sha256
            != witness.world_observation_receipt_sha256
            or record.witness_world_execution_receipt_sha256
            != witness.world_execution_receipt_sha256
            or record.witness_world_before_receipt_sha256
            != witness.world_before_receipt_sha256
            or record.witness_world_after_receipt_sha256
            != witness.world_after_receipt_sha256
            or record.world_before_receipt_sha256
            != witness.world_observation_receipt_sha256
            or record.candidate_world_execution_receipt_sha256
            != record.world_execution_receipt_sha256
            or record.candidate_program_sample_count
            != record.program.sample_count
            or record.candidate_source_sample_count
            != record.program.sample_count
            or _digest(record.program.as_record())
            != record.command_graph_sha256
            or source_extent.denominator != 1
            or source_extent.numerator <= 0
        ):
            raise ValueError(
                "restored pending vocal custody changed causal chain"
            )
        for value, name in (
            (
                record.candidate_w1_mount_receipt_sha256,
                "restored candidate W1 mount",
            ),
            (
                record.candidate_causal_settlement_receipt_sha256,
                "restored candidate causal settlement",
            ),
            (
                record.candidate_binaural_l5_receipt_sha256,
                "restored candidate binaural L5",
            ),
            (
                record.candidate_receptor_settlement_receipt_sha256,
                "restored candidate receptor settlement",
            ),
            (
                record.candidate_recurrent_q_receipt_sha256,
                "restored candidate recurrent Q",
            ),
        ):
            _sha(value, name)
        return _AuthenticatedVocalFragmentSource(
            candidate_receipt_sha256=(
                record.candidate_authority_receipt_sha256
            ),
            transient_act_id=record.transient_act_id,
            pressure_sha256=record.candidate_pressure_sha256,
            world_before_receipt_sha256=(
                record.world_before_receipt_sha256
            ),
            world_after_receipt_sha256=(
                record.world_after_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                record.world_execution_receipt_sha256
            ),
            command_graph_sha256=record.command_graph_sha256,
            program=record.program,
        )

    def _prepare_authenticated_source(
        self,
        *,
        source: _AuthenticatedVocalFragmentSource,
        need: InquiryNeed,
        witness: InquiryWitness,
        later_custody_authority: SettledExperienceCustodyAuthority,
        later_custody_capability: (
            SettledExperienceConsumerCapability
        ),
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
        tutor_consequence_authorization: (
            CausalInquiryTutorConsequenceAuthorizationReceipt | None
        ),
    ) -> PreparedExperienceGrownVocalMotorFragment:
        if not isinstance(
            later_custody_authority,
            SettledExperienceCustodyAuthority,
        ) or not isinstance(
            later_custody_capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "vocal fragment requires authenticated consequence custody"
            )
        self._require_prepare_capacity()
        view = later_custody_authority.open_child(
            later_custody_capability
        )
        execution = view.world_execution
        if execution is None:
            raise ValueError(
                "vocal-fragment consequence has no lived execution"
            )
        self._world.verify_execution_receipt(execution)
        if (
            execution.disposition != "applied"
            or execution.port_id != SECOND_BODY_PORT_ID
            or execution.before.authority_receipt_sha256
            != source.world_after_receipt_sha256
        ):
            raise ValueError(
                "vocal-fragment consequence is absent or late"
            )
        if companion_episode_intent is None:
            if tutor_consequence_authorization is not None:
                raise ValueError(
                    "tutor consequence authorization requires "
                    "companion W1 intent"
                )
            if (
                execution.causal_intent_receipt_sha256
                != source.candidate_receipt_sha256
            ):
                raise ValueError(
                    "vocal-fragment consequence changed intent"
                )
            intent_receipt = execution.causal_intent_receipt_sha256
        else:
            self._companion.verify_episode_intent(
                companion_episode_intent
            )
            expected_parent = source.candidate_receipt_sha256
            if tutor_consequence_authorization is not None:
                self._tutor_verifier.verify_consequence(
                    tutor_consequence_authorization
                )
                if (
                    tutor_consequence_authorization
                    .need_receipt_sha256
                    != need.authority_receipt_sha256
                    or tutor_consequence_authorization
                    .witness_receipt_sha256
                    != witness.authority_receipt_sha256
                    or tutor_consequence_authorization
                    .candidate_receipt_sha256
                    != source.candidate_receipt_sha256
                    or tutor_consequence_authorization
                    .candidate_world_after_receipt_sha256
                    != source.world_after_receipt_sha256
                    or tutor_consequence_authorization
                    .companion_pcm_sha256
                    != companion_episode_intent.pcm_sha256
                ):
                    raise ValueError(
                        "tutor consequence authorization changed chain"
                    )
                expected_parent = (
                    tutor_consequence_authorization
                    .authority_receipt_sha256
                )
            if (
                companion_episode_intent.block_count != 1
                or companion_episode_intent.companion_port_id
                != SECOND_BODY_PORT_ID
                or companion_episode_intent
                .causal_parent_receipt_sha256
                != expected_parent
                or companion_episode_intent
                .world_observation_receipt_sha256
                != execution.before.authority_receipt_sha256
                or execution.causal_intent_receipt_sha256
                != companion_episode_intent.authority_receipt_sha256
            ):
                raise ValueError(
                    "vocal-fragment companion intent changed chain"
                )
            intent_receipt = (
                companion_episode_intent.authority_receipt_sha256
            )
        boundaries = self._complete_multisensory(
            view.causal_settlement
        )
        route = self._things.route(view.causal_settlement)
        if (
            route.state != "unique"
            or len(route.thing_ids) != 1
            or (
                witness.route_state == "ambiguous"
                and route.thing_ids[0] not in witness.thing_ids
            )
        ):
            raise ValueError(
                "vocal-fragment consequence did not resolve one THING"
            )
        if any(
            fragment.candidate_receipt_sha256
            == source.candidate_receipt_sha256
            for fragment in self._fragments
        ):
            raise ValueError(
                "transient candidate already sealed a motor fragment"
            )
        program = source.program
        identity_payload = {
            "candidate_receipt_sha256": (
                source.candidate_receipt_sha256
            ),
            "consequence_settlement_receipt_sha256": (
                view.causal_settlement.authority_receipt_sha256
            ),
            "need_receipt_sha256": need.authority_receipt_sha256,
            "program_id": program.program_id,
            "schema": FRAGMENT_SCHEMA,
        }
        provisional = ExperienceGrownVocalMotorFragment(
            fragment_id=_digest(identity_payload),
            program_id=program.program_id,
            program_authority_receipt_sha256=(
                program.authority_receipt_sha256
            ),
            command_graph_sha256=source.command_graph_sha256,
            candidate_receipt_sha256=(
                source.candidate_receipt_sha256
            ),
            transient_act_id=source.transient_act_id,
            pressure_sha256=source.pressure_sha256,
            need_receipt_sha256=need.authority_receipt_sha256,
            witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            prior_route_state=witness.route_state,
            prior_thing_ids=witness.thing_ids,
            candidate_world_before_receipt_sha256=(
                source.world_before_receipt_sha256
            ),
            candidate_world_after_receipt_sha256=(
                source.world_after_receipt_sha256
            ),
            candidate_world_execution_receipt_sha256=(
                source.world_execution_receipt_sha256
            ),
            consequence_intent_receipt_sha256=intent_receipt,
            consequence_execution_receipt_sha256=(
                execution.authority_receipt_sha256
            ),
            consequence_settlement_receipt_sha256=(
                view.causal_settlement.authority_receipt_sha256
            ),
            consequence_custody_receipt_sha256=(
                view.parent_custody_receipt_sha256
            ),
            consequence_capability_receipt_sha256=(
                later_custody_capability.authority_receipt_sha256
            ),
            consequence_source_occurrence_id=view.source_occurrence_id,
            consequence_boundary_receipts=boundaries,
            unique_thing_id=route.thing_ids[0],
            tutor_authorization_receipt_sha256=(
                tutor_consequence_authorization
                .authority_receipt_sha256
                if tutor_consequence_authorization is not None
                else None
            ),
            tutor_nonce_sha256=(
                tutor_consequence_authorization.nonce_sha256
                if tutor_consequence_authorization is not None
                else None
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._fragment_key,
            _FRAGMENT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        fragment = ExperienceGrownVocalMotorFragment(
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
        staged = tuple(sorted(
            (*self._fragments, fragment),
            key=lambda value: value.fragment_id,
        ))
        self._encoded(staged)
        motor_prepared = self._motor.prepare_program_admission(
            program
        )
        prepared = PreparedExperienceGrownVocalMotorFragment(
            fragment=fragment,
            program=program,
            _motor_prepared=motor_prepared,
            _prior_fragments=self._fragments,
            _staged_fragments=staged,
            _state=_TransactionState(),
            _owner_authority=self._owner_authority,
            _construction_authority=_PREPARED_AUTHORITY,
        )
        self._prepared = prepared
        return prepared

    def prepare(
        self,
        *,
        candidate: TransientVocalCandidate,
        need: InquiryNeed,
        witness: InquiryWitness,
        later_custody_authority: SettledExperienceCustodyAuthority,
        later_custody_capability: (
            SettledExperienceConsumerCapability
        ),
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ) = None,
        tutor_consequence_authorization: (
            CausalInquiryTutorConsequenceAuthorizationReceipt | None
        ) = None,
    ) -> PreparedExperienceGrownVocalMotorFragment:
        with self._lock:
            self._require_prepare_capacity()
            self._active_pair(need, witness)
            source = self._live_source(candidate, witness)
            return self._prepare_authenticated_source(
                source=source,
                need=need,
                witness=witness,
                later_custody_authority=later_custody_authority,
                later_custody_capability=later_custody_capability,
                companion_episode_intent=companion_episode_intent,
                tutor_consequence_authorization=(
                    tutor_consequence_authorization
                ),
            )

    def prepare_from_restored_pending(
        self,
        *,
        pending_custody_authority: (
            PendingBodyOwnedVocalConsequenceOwner
        ),
        pending_custody: RestoredPendingBodyOwnedVocalCustody,
        need: InquiryNeed,
        witness: InquiryWitness,
        later_custody_authority: SettledExperienceCustodyAuthority,
        later_custody_capability: (
            SettledExperienceConsumerCapability
        ),
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ) = None,
        tutor_consequence_authorization: (
            CausalInquiryTutorConsequenceAuthorizationReceipt | None
        ) = None,
    ) -> PreparedExperienceGrownVocalMotorFragment:
        with self._lock:
            self._require_prepare_capacity()
            self._active_pair(need, witness)
            source = self._restored_source(
                pending_custody_authority=(
                    pending_custody_authority
                ),
                pending_custody=pending_custody,
                need=need,
                witness=witness,
            )
            return self._prepare_authenticated_source(
                source=source,
                need=need,
                witness=witness,
                later_custody_authority=later_custody_authority,
                later_custody_capability=later_custody_capability,
                companion_episode_intent=companion_episode_intent,
                tutor_consequence_authorization=(
                    tutor_consequence_authorization
                ),
            )

    def _verify_prepared(
        self,
        prepared: PreparedExperienceGrownVocalMotorFragment,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedExperienceGrownVocalMotorFragment,
            )
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or self._prepared is not prepared
            or prepared._state.phase != "prepared"
            or self._fragments != prepared._prior_fragments
            or prepared.fragment not in prepared._staged_fragments
        ):
            raise ValueError(
                "prepared vocal motor fragment changed custody"
            )
        self._encoded(prepared._staged_fragments)

    def commit(
        self,
        prepared: PreparedExperienceGrownVocalMotorFragment,
    ) -> ExperienceGrownVocalMotorFragmentUndo:
        with self._lock:
            self._verify_prepared(prepared)
            motor_undo = (
                self._motor.commit_prepared_program_admission(
                    prepared._motor_prepared
                )
            )
            try:
                self._fragments = prepared._staged_fragments
                self._prepared = None
                prepared._state.phase = "committed"
                undo = ExperienceGrownVocalMotorFragmentUndo(
                    _prepared=prepared,
                    _motor_undo=motor_undo,
                    _owner_authority=self._owner_authority,
                    _construction_authority=_UNDO_AUTHORITY,
                )
                self._latest_undo = undo
                self._verify_fragment(prepared.fragment)
                return undo
            except BaseException:
                self._fragments = prepared._prior_fragments
                self._latest_undo = None
                self._motor.rollback_program_admission(motor_undo)
                self._prepared = None
                prepared._state.phase = "failed"
                raise

    def discard(
        self,
        prepared: PreparedExperienceGrownVocalMotorFragment,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            self._motor.discard_prepared_program_admission(
                prepared._motor_prepared
            )
            self._prepared = None
            prepared._state.phase = "discarded"

    def finalize(
        self,
        undo: ExperienceGrownVocalMotorFragmentUndo,
    ) -> ExperienceGrownVocalMotorFragment:
        with self._lock:
            if (
                not isinstance(
                    undo,
                    ExperienceGrownVocalMotorFragmentUndo,
                )
                or undo._construction_authority is not _UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
                or self._latest_undo is not undo
                or undo._prepared._state.phase != "committed"
            ):
                raise ValueError(
                    "vocal motor fragment finalization changed"
                )
            self._motor.finalize_program_admission(
                undo._motor_undo
            )
            self._latest_undo = None
            undo._prepared._state.phase = "finalized"
            return undo._prepared.fragment

    def rollback(
        self,
        undo: ExperienceGrownVocalMotorFragmentUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    undo,
                    ExperienceGrownVocalMotorFragmentUndo,
                )
                or undo._construction_authority is not _UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
                or self._latest_undo is not undo
                or undo._prepared._state.phase != "committed"
                or self._fragments
                != undo._prepared._staged_fragments
            ):
                raise ValueError(
                    "vocal motor fragment rollback changed"
                )
            self._motor.rollback_program_admission(
                undo._motor_undo
            )
            self._fragments = undo._prepared._prior_fragments
            self._latest_undo = None
            undo._prepared._state.phase = "rolled_back"

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._max_state_bytes
        ):
            raise ValueError(
                "vocal-fragment state exceeds exact capacity"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "vocal-fragment state is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {
                "authority_hmac_sha256",
                "payload_base64",
                "schema",
            }
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("vocal-fragment state envelope changed")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"),
                validate=True,
            )
        except Exception as error:
            raise ValueError(
                "vocal-fragment payload is not canonical base64"
            ) from error
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            signature,
            envelope.get("authority_hmac_sha256"),
        ):
            raise ValueError("vocal-fragment state HMAC changed")
        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "vocal-fragment payload is not canonical JSON"
            ) from error
        if (
            not isinstance(body, Mapping)
            or set(body) != {"fragments", "limits", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("limits") != {
                "max_fragments": self._max_fragments,
                "max_state_bytes": self._max_state_bytes,
            }
            or not isinstance(body.get("fragments"), list)
            or _canonical(body) != payload
        ):
            raise ValueError("vocal-fragment state body changed")
        fragments = tuple(
            self._fragment_from_record(value)
            for value in body["fragments"]
        )
        if (
            len(fragments) > self._max_fragments
            or tuple(sorted(
                fragments,
                key=lambda value: value.fragment_id,
            )) != fragments
            or len({value.fragment_id for value in fragments})
            != len(fragments)
        ):
            raise ValueError(
                "vocal-fragment restored cardinality changed"
            )
        with self._lock:
            if self._prepared is not None or self._latest_undo is not None:
                raise RuntimeError(
                    "cannot restore across vocal-fragment transaction"
                )
            prior = self._fragments
            self._fragments = fragments
            try:
                for fragment in fragments:
                    self._verify_fragment(fragment)
                if self._encoded(fragments) != encoded:
                    raise ValueError(
                        "vocal-fragment restored bytes changed"
                    )
            except BaseException:
                self._fragments = prior
                raise

    @staticmethod
    def _fragment_from_record(
        value: object,
    ) -> ExperienceGrownVocalMotorFragment:
        if not isinstance(value, Mapping):
            raise ValueError("vocal-fragment record changed")
        expected = {
            *ExperienceGrownVocalMotorFragment.__dataclass_fields__,
            "schema",
        }
        if set(value) != expected or value.get("schema") != FRAGMENT_SCHEMA:
            raise ValueError("vocal-fragment record fields changed")
        try:
            result = ExperienceGrownVocalMotorFragment(
                fragment_id=value["fragment_id"],
                program_id=value["program_id"],
                program_authority_receipt_sha256=value[
                    "program_authority_receipt_sha256"
                ],
                command_graph_sha256=value["command_graph_sha256"],
                candidate_receipt_sha256=value[
                    "candidate_receipt_sha256"
                ],
                transient_act_id=value["transient_act_id"],
                pressure_sha256=value["pressure_sha256"],
                need_receipt_sha256=value["need_receipt_sha256"],
                witness_receipt_sha256=value[
                    "witness_receipt_sha256"
                ],
                prior_route_state=value["prior_route_state"],
                prior_thing_ids=tuple(value["prior_thing_ids"]),
                candidate_world_before_receipt_sha256=value[
                    "candidate_world_before_receipt_sha256"
                ],
                candidate_world_after_receipt_sha256=value[
                    "candidate_world_after_receipt_sha256"
                ],
                candidate_world_execution_receipt_sha256=value[
                    "candidate_world_execution_receipt_sha256"
                ],
                consequence_intent_receipt_sha256=value[
                    "consequence_intent_receipt_sha256"
                ],
                consequence_execution_receipt_sha256=value[
                    "consequence_execution_receipt_sha256"
                ],
                consequence_settlement_receipt_sha256=value[
                    "consequence_settlement_receipt_sha256"
                ],
                consequence_custody_receipt_sha256=value[
                    "consequence_custody_receipt_sha256"
                ],
                consequence_capability_receipt_sha256=value[
                    "consequence_capability_receipt_sha256"
                ],
                consequence_source_occurrence_id=value[
                    "consequence_source_occurrence_id"
                ],
                consequence_boundary_receipts=tuple(
                    tuple(item)
                    for item in value["consequence_boundary_receipts"]
                ),
                unique_thing_id=value["unique_thing_id"],
                tutor_authorization_receipt_sha256=value[
                    "tutor_authorization_receipt_sha256"
                ],
                tutor_nonce_sha256=value["tutor_nonce_sha256"],
                authority_hmac_sha256=value[
                    "authority_hmac_sha256"
                ],
                authority_receipt_sha256=value[
                    "authority_receipt_sha256"
                ],
            )
        except (KeyError, TypeError) as error:
            raise ValueError(
                "vocal-fragment record is malformed"
            ) from error
        if result.record() != dict(value):
            raise ValueError("vocal-fragment record is noncanonical")
        return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "fragment_count": len(self._fragments),
                "fragment_capacity": self._max_fragments,
                "prepared": int(self._prepared is not None),
                "retained_pcm_bytes": 0,
                "schema": (
                    "guala.experience_grown_vocal_motor_fragment."
                    "status.v1"
                ),
            }


__all__ = (
    "ENVELOPE_SCHEMA",
    "ExperienceGrownVocalMotorFragment",
    "ExperienceGrownVocalMotorFragmentCapacityError",
    "ExperienceGrownVocalMotorFragmentOwner",
    "ExperienceGrownVocalMotorFragmentUndo",
    "FRAGMENT_SCHEMA",
    "PreparedExperienceGrownVocalMotorFragment",
    "STATE_SCHEMA",
)
