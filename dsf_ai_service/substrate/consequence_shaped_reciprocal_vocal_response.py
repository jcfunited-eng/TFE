"""Fresh sight-evoked articulation from an experience-grown causal relation.

This authority owns no learned identity and retains no pressure.  It consumes
one child capability issued by the existing retained audiovisual custody
owner, asks the one reciprocal THING owner whether the complete sight trace
recurs, and selects an already-sealed experience-grown vocal causal relation
for that same THING.  The selected body program is synthesized anew and
propagated through W1 self-hearing.

The tutor sound is a physical consequence inside the relation's learning
episode.  It is not acoustically compared with the body's emitted pressure.
Accordingly this mechanism proves consequence-shaped reciprocal vocal
learning, not intelligible human-word speech.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID,
    RetainedAudiovisualCustodyAuthority,
    RetainedAudiovisualCustodyCapability,
)
from dsf_ai_service.substrate.consequence_evoked_articulatory_response import (
    CommittedConsequenceEvokedArticulatoryAct,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.experience_grown_vocal_causal_relation import (
    ExperienceGrownVocalCausalRelationOwner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)


RESPONSE_SCHEMA = (
    "guala.consequence_shaped_reciprocal_vocal_response.v1"
)
ACT_SCHEMA = "guala.consequence_shaped_reciprocal_vocal_act.v1"
STATUS_SCHEMA = (
    "guala.consequence_shaped_reciprocal_vocal_response.status.v1"
)
_RESPONSE_DOMAIN = (
    b"guala-consequence-shaped-reciprocal-vocal-response-v1\0"
)
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


def _authority_key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(
            "consequence-shaped response authority key changed"
        )
    return hashlib.sha256(_RESPONSE_DOMAIN + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ConsequenceShapedReciprocalVocalResponse:
    state: str
    reason: str
    cue_settlement_receipt_sha256: str
    evocation_receipt_sha256: str
    thing_ids: tuple[str, ...]
    relation_receipt_sha256: str | None
    program_id: str | None
    synthesis_pcm_sha256: str | None
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "cue_settlement_receipt_sha256": (
                self.cue_settlement_receipt_sha256
            ),
            "evocation_receipt_sha256": (
                self.evocation_receipt_sha256
            ),
            "program_id": self.program_id,
            "reason": self.reason,
            "relation_receipt_sha256": (
                self.relation_receipt_sha256
            ),
            "schema": RESPONSE_SCHEMA,
            "state": self.state,
            "synthesis_pcm_sha256": self.synthesis_pcm_sha256,
            "thing_ids": list(self.thing_ids),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
        }


class ConsequenceShapedReciprocalVocalResponseAuthority:
    """Execute one exact retained relation from one exact recurring sight."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
        relation_owner: ExperienceGrownVocalCausalRelationOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        acoustic_authority: W1SelfAcousticPropagationAuthority,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "consequence-shaped response requires reciprocal THING "
                "custody"
            )
        if not isinstance(
            relation_owner,
            ExperienceGrownVocalCausalRelationOwner,
        ):
            raise TypeError(
                "consequence-shaped response requires vocal relation custody"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "consequence-shaped response requires articulatory custody"
            )
        if not isinstance(
            acoustic_authority,
            W1SelfAcousticPropagationAuthority,
        ):
            raise TypeError(
                "consequence-shaped response requires W1 self-hearing"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "consequence-shaped response requires embodiment world"
            )
        self._key = _authority_key(authority_key)
        self._reciprocal = reciprocal_owner
        self._relations = relation_owner
        self._articulatory = articulatory_owner
        self._acoustic = acoustic_authority
        self._world = world_authority
        self._lock = threading.RLock()

    def _seal(
        self,
        *,
        state: str,
        reason: str,
        settlement_receipt: str,
        evocation_receipt: str,
        thing_ids: tuple[str, ...],
        relation_receipt: str | None,
        program_id: str | None,
        pressure_receipt: str | None,
        world_before: str,
        world_after: str,
    ) -> ConsequenceShapedReciprocalVocalResponse:
        provisional = ConsequenceShapedReciprocalVocalResponse(
            state=state,
            reason=reason,
            cue_settlement_receipt_sha256=settlement_receipt,
            evocation_receipt_sha256=evocation_receipt,
            thing_ids=thing_ids,
            relation_receipt_sha256=relation_receipt,
            program_id=program_id,
            synthesis_pcm_sha256=pressure_receipt,
            world_before_receipt_sha256=world_before,
            world_after_receipt_sha256=world_after,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _RESPONSE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = ConsequenceShapedReciprocalVocalResponse(
            state=provisional.state,
            reason=provisional.reason,
            cue_settlement_receipt_sha256=(
                provisional.cue_settlement_receipt_sha256
            ),
            evocation_receipt_sha256=(
                provisional.evocation_receipt_sha256
            ),
            thing_ids=provisional.thing_ids,
            relation_receipt_sha256=(
                provisional.relation_receipt_sha256
            ),
            program_id=provisional.program_id,
            synthesis_pcm_sha256=provisional.synthesis_pcm_sha256,
            world_before_receipt_sha256=(
                provisional.world_before_receipt_sha256
            ),
            world_after_receipt_sha256=(
                provisional.world_after_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_response(result)
        return result

    def verify_response(
        self,
        value: ConsequenceShapedReciprocalVocalResponse,
    ) -> None:
        if not isinstance(
            value,
            ConsequenceShapedReciprocalVocalResponse,
        ):
            raise TypeError(
                "consequence-shaped response is not typed"
            )
        if value.state not in {
            "executed",
            "unresolved",
            "ambiguous",
            "unbound",
        }:
            raise ValueError(
                "consequence-shaped response state changed"
            )
        for digest, label in (
            (
                value.cue_settlement_receipt_sha256,
                "response cue settlement",
            ),
            (
                value.evocation_receipt_sha256,
                "response evocation",
            ),
            (
                value.world_before_receipt_sha256,
                "response world before",
            ),
            (
                value.world_after_receipt_sha256,
                "response world after",
            ),
            (
                value.authority_hmac_sha256,
                "response authority HMAC",
            ),
            (
                value.authority_receipt_sha256,
                "response authority",
            ),
        ):
            _sha(digest, label)
        if value.state == "executed":
            if (
                len(value.thing_ids) != 1
                or value.relation_receipt_sha256 is None
                or value.program_id is None
                or value.synthesis_pcm_sha256 is None
                or value.world_after_receipt_sha256
                == value.world_before_receipt_sha256
            ):
                raise ValueError(
                    "executed consequence-shaped response lost its act"
                )
            _sha(
                value.relation_receipt_sha256,
                "response vocal relation",
            )
            _sha(
                value.synthesis_pcm_sha256,
                "response synthesized pressure",
            )
        elif (
            value.relation_receipt_sha256 is not None
            or value.program_id is not None
            or value.synthesis_pcm_sha256 is not None
            or value.world_after_receipt_sha256
            != value.world_before_receipt_sha256
        ):
            raise ValueError(
                "silent consequence-shaped response retained an act"
            )
        expected = hmac.new(
            self._key,
            _RESPONSE_DOMAIN + _canonical(value.payload()),
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
            raise ValueError(
                "consequence-shaped response authority changed"
            )

    def respond(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> (
        ConsequenceShapedReciprocalVocalResponse
        | CommittedConsequenceEvokedArticulatoryAct
    ):
        if not isinstance(
            custody_authority,
            RetainedAudiovisualCustodyAuthority,
        ) or not isinstance(
            custody_capability,
            RetainedAudiovisualCustodyCapability,
        ):
            raise TypeError(
                "consequence-shaped response requires retained sight "
                "custody"
            )
        if custody_capability.consumer_id != (
            RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID
        ):
            raise ValueError(
                "consequence-shaped response requires its sight capability"
            )
        with self._lock:
            retained = custody_authority.open_child(
                custody_capability
            )
            settlement = retained.settlement
            settlement.verify()
            before = self._world.observation_snapshot()
            evocation = self._reciprocal.evoke(
                settlement,
                cue_senses=("sight",),
            )
            self._reciprocal.verify_evocation(evocation)
            if evocation.state != "unique":
                return self._seal(
                    state=evocation.state,
                    reason="sight_trace_did_not_resolve_one_thing",
                    settlement_receipt=(
                        settlement.authority_receipt_sha256
                    ),
                    evocation_receipt=(
                        evocation.authority_receipt_sha256
                    ),
                    thing_ids=evocation.thing_ids,
                    relation_receipt=None,
                    program_id=None,
                    pressure_receipt=None,
                    world_before=before.authority_receipt_sha256,
                    world_after=before.authority_receipt_sha256,
                )
            reciprocal_class = evocation.candidate
            if reciprocal_class is None:
                raise RuntimeError(
                    "unique sight evocation lost reciprocal THING"
                )
            program_custody = self._relations.select_evoked_program(
                evocation
            )
            if program_custody is None:
                return self._seal(
                    state="unbound",
                    reason="thing_has_no_unique_consequence_shaped_relation",
                    settlement_receipt=(
                        settlement.authority_receipt_sha256
                    ),
                    evocation_receipt=(
                        evocation.authority_receipt_sha256
                    ),
                    thing_ids=evocation.thing_ids,
                    relation_receipt=None,
                    program_id=None,
                    pressure_receipt=None,
                    world_before=before.authority_receipt_sha256,
                    world_after=before.authority_receipt_sha256,
                )
            program, fragment = (
                self._relations.verified_evoked_program(
                    program_custody
                )
            )
            synthesis = self._articulatory.synthesize(
                program_id=program.program_id,
                source_time_start=Fraction(
                    before.revision * MAX_VOCAL_SAMPLE_COUNT,
                    VOCAL_SAMPLE_RATE_HZ,
                ),
            )
            pressure_sha256 = hashlib.sha256(
                synthesis.radiated_pcm_s16le
            ).hexdigest()
            if (
                synthesis.program != program
                or pressure_sha256 != fragment.pressure_sha256
            ):
                raise ValueError(
                    "consequence-shaped relation changed body pressure"
                )
            intent = _digest({
                "cue_settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "evocation_receipt_sha256": (
                    evocation.authority_receipt_sha256
                ),
                "relation_receipt_sha256": (
                    program_custody.relation_receipt_sha256
                ),
                "schema": ACT_SCHEMA,
                "synthesis_receipt_sha256": (
                    synthesis.receipt.authority_receipt_sha256
                ),
                "world_before_receipt_sha256": (
                    before.authority_receipt_sha256
                ),
            })
            prepared_emission = (
                self._articulatory.prepare_generated_emission(
                    synthesis=synthesis,
                    world_authority=self._world,
                    causal_intent_receipt_sha256=intent,
                )
            )
            prepared_acoustic = self._acoustic.prepare_articulatory(
                prepared_emission,
                articulatory_owner=self._articulatory,
            )
            committed_undo = None
            try:
                commitment = (
                    self._acoustic.prepared_articulatory_commitment(
                        prepared_acoustic
                    )
                )
                self._acoustic.verify_prepared_articulatory_commitment(
                    prepared_acoustic,
                    commitment,
                )
                if (
                    commitment.program_id != program.program_id
                    or commitment.pcm_sha256 != pressure_sha256
                    or commitment.world_before_receipt_sha256
                    != before.authority_receipt_sha256
                ):
                    raise ValueError(
                        "prepared consequence-shaped act crossed custody"
                    )
                emission, _mount, committed_undo = (
                    self._acoustic.commit_prepared_articulatory(
                        prepared_acoustic
                    )
                )
                after = self._world.observation_snapshot()
                if (
                    emission.emission_receipt.program_id
                    != program.program_id
                    or hashlib.sha256(emission.pcm_s16le).hexdigest()
                    != pressure_sha256
                    or after.revision != before.revision + 1
                ):
                    raise RuntimeError(
                        "committed consequence-shaped act changed"
                    )
                response = self._seal(
                    state="executed",
                    reason=(
                        "consequence_shaped_relation_recurred_from_sight"
                    ),
                    settlement_receipt=(
                        settlement.authority_receipt_sha256
                    ),
                    evocation_receipt=(
                        evocation.authority_receipt_sha256
                    ),
                    thing_ids=evocation.thing_ids,
                    relation_receipt=(
                        program_custody.relation_receipt_sha256
                    ),
                    program_id=program.program_id,
                    pressure_receipt=pressure_sha256,
                    world_before=before.authority_receipt_sha256,
                    world_after=after.authority_receipt_sha256,
                )
                act = CommittedConsequenceEvokedArticulatoryAct(
                    response=response,
                    pcm_s16le=bytes(emission.pcm_s16le),
                )
                self.verify_committed_act(act)
            except BaseException:
                if committed_undo is None:
                    self._acoustic.discard_prepared_articulatory(
                        prepared_acoustic
                    )
                else:
                    self._acoustic.rollback_committed_articulatory(
                        committed_undo
                    )
                raise
            return act

    def verify_committed_act(
        self,
        value: CommittedConsequenceEvokedArticulatoryAct,
    ) -> None:
        if not isinstance(
            value,
            CommittedConsequenceEvokedArticulatoryAct,
        ):
            raise TypeError(
                "consequence-shaped committed act is not typed"
            )
        self.verify_response(value.response)
        if (
            value.response.state != "executed"
            or not value.pcm_s16le
            or len(value.pcm_s16le) % 2
            or hashlib.sha256(value.pcm_s16le).hexdigest()
            != value.response.synthesis_pcm_sha256
        ):
            raise ValueError(
                "consequence-shaped committed act changed pressure"
            )

    def status(self) -> dict[str, object]:
        return {
            "retained_pcm_bytes": 0,
            "schema": STATUS_SCHEMA,
            "stateful": False,
            "word_authority": False,
        }


__all__ = (
    "ACT_SCHEMA",
    "STATUS_SCHEMA",
    "CommittedConsequenceEvokedArticulatoryAct",
    "ConsequenceShapedReciprocalVocalResponse",
    "ConsequenceShapedReciprocalVocalResponseAuthority",
)
