"""Sight-evoked fresh articulation from retained consequence closure.

One exact sight settlement may select one reciprocal causal THING.  A
physical response is possible only when that THING has exactly one retained
articulatory consequence binding.  The retained program is synthesized
freshly for the occurrence, then the motor, world, and complete W1
self-hearing transaction are prepared.

The durable response is receipt-only.  It is privately sealed from W1's
public hash-only prepared commitment before W1 publishes sensory state and
commits motor/world as the final physical point.  Successful execution
returns a separate transient act containing the sealed receipt and fresh PCM.
The authority retains no PCM and exposes no prepared or final W1 mount.
Response input is an owner-bound settled-experience child capability whose
world observation must still be the exact current world.  Successful pressure
advances that world, making the occurrence exactly stale without a replay
ledger.

No label, transcript, score, tolerance, acoustic comparison, PCM exemplar,
replay route, babble cursor, or direct motor THING binding participates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction

from dsf_ai_service.substrate.articulatory_consequence_closure import (
    ArticulatoryConsequenceBinding,
    ArticulatoryConsequenceClosureOwner,
)
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
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1PreparedArticulatoryCommitment,
    W1SelfAcousticPropagationAuthority,
)


RESPONSE_SCHEMA = "guala.consequence_evoked_articulatory_response.v1"
ACT_SCHEMA = "guala.consequence_evoked_articulatory_act.v1"
INTENT_SCHEMA = "guala.consequence_evoked_articulatory_intent.v1"
STATUS_SCHEMA = "guala.consequence_evoked_articulatory_response.status.v1"
CONSEQUENCE_EVOKED_RESPONSE_CONSUMER_ID = (
    RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID
)
_RESPONSE_DOMAIN = b"guala-consequence-evoked-articulatory-response-v1\0"
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
    if isinstance(value, str):
        raw = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
    else:
        raise TypeError(
            "consequence-evoked response key must be bytes or text"
        )
    if not 32 <= len(raw) <= 4_096:
        raise ValueError(
            "consequence-evoked response key boundary changed"
        )
    return hashlib.sha256(_RESPONSE_DOMAIN + raw).digest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class ConsequenceEvokedArticulatoryResponse:
    """One durable receipt-only resolution or committed response."""

    state: str
    cue_settlement_receipt_sha256: str
    evocation_receipt_sha256: str
    thing_ids: tuple[str, ...]
    binding_receipt_sha256: str | None
    program_id: str | None
    synthesis_receipt_sha256: str | None
    synthesis_pcm_sha256: str | None
    emission_receipt_sha256: str | None
    self_acoustic_receipt_sha256: str | None
    prepared_self_acoustic_commitment_receipt_sha256: str | None
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binding_receipt_sha256": self.binding_receipt_sha256,
            "cue_settlement_receipt_sha256": (
                self.cue_settlement_receipt_sha256
            ),
            "emission_receipt_sha256": (
                self.emission_receipt_sha256
            ),
            "evocation_receipt_sha256": (
                self.evocation_receipt_sha256
            ),
            "prepared_self_acoustic_commitment_receipt_sha256": (
                self
                .prepared_self_acoustic_commitment_receipt_sha256
            ),
            "program_id": self.program_id,
            "schema": RESPONSE_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt_sha256
            ),
            "state": self.state,
            "synthesis_pcm_sha256": self.synthesis_pcm_sha256,
            "synthesis_receipt_sha256": (
                self.synthesis_receipt_sha256
            ),
            "thing_ids": list(self.thing_ids),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CommittedConsequenceEvokedArticulatoryAct:
    """Non-persistable occurrence output released only after W1 commit."""

    response: ConsequenceEvokedArticulatoryResponse
    pcm_s16le: bytes = field(repr=False)


def _verify_seal(
    value: ConsequenceEvokedArticulatoryResponse,
    *,
    response_key: bytes,
) -> None:
    if not isinstance(value, ConsequenceEvokedArticulatoryResponse):
        raise TypeError(
            "consequence-evoked articulatory response is not typed"
        )
    if value.state not in {
        "executed",
        "unresolved",
        "ambiguous",
        "unbound",
    }:
        raise ValueError(
            "consequence-evoked articulatory response state changed"
        )
    for digest, name in (
        (
            value.cue_settlement_receipt_sha256,
            "consequence-evoked cue settlement",
        ),
        (
            value.evocation_receipt_sha256,
            "consequence-evoked reciprocal evocation",
        ),
        (
            value.world_before_receipt_sha256,
            "consequence-evoked world before",
        ),
        (
            value.world_after_receipt_sha256,
            "consequence-evoked world after",
        ),
        (
            value.authority_hmac_sha256,
            "consequence-evoked response HMAC",
        ),
        (
            value.authority_receipt_sha256,
            "consequence-evoked response authority",
        ),
    ):
        _sha256(digest, name)
    for thing_id in value.thing_ids:
        _sha256(thing_id, "consequence-evoked THING")
    physical_digests = (
        value.binding_receipt_sha256,
        value.program_id,
        value.synthesis_receipt_sha256,
        value.synthesis_pcm_sha256,
        value.emission_receipt_sha256,
        value.self_acoustic_receipt_sha256,
        value.prepared_self_acoustic_commitment_receipt_sha256,
    )
    if value.state == "executed":
        for digest in physical_digests:
            _sha256(digest, "consequence-evoked physical response")
        if (
            len(value.thing_ids) != 1
            or value.world_before_receipt_sha256
            == value.world_after_receipt_sha256
        ):
            raise ValueError(
                "executed consequence-evoked response lost custody"
            )
    elif (
        any(digest is not None for digest in physical_digests)
        or value.world_before_receipt_sha256
        != value.world_after_receipt_sha256
    ):
        raise ValueError(
            "silent consequence-evoked response changed physical state"
        )
    signature = hmac.new(
        response_key,
        _RESPONSE_DOMAIN + _canonical(value.payload()),
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(
            signature,
            value.authority_hmac_sha256,
        )
        or value.authority_receipt_sha256
        != _digest({
            "authority_hmac_sha256": signature,
            "payload": value.payload(),
        })
    ):
        raise ValueError(
            "consequence-evoked response authority changed"
        )


def verify_consequence_evoked_articulatory_response(
    value: ConsequenceEvokedArticulatoryResponse,
    *,
    authority_key: bytes | str,
) -> None:
    """Verify the durable response without transient occurrence objects."""

    _verify_seal(
        value,
        response_key=_authority_key(authority_key),
    )


class ConsequenceEvokedArticulatoryResponseAuthority:
    """Respond only through one retained consequence-selected program."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
        consequence_owner: ArticulatoryConsequenceClosureOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        acoustic_authority: W1SelfAcousticPropagationAuthority,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "consequence response requires reciprocal THING authority"
            )
        if not isinstance(
            consequence_owner,
            ArticulatoryConsequenceClosureOwner,
        ):
            raise TypeError(
                "consequence response requires retained closure authority"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "consequence response requires articulatory authority"
            )
        if not isinstance(
            acoustic_authority,
            W1SelfAcousticPropagationAuthority,
        ):
            raise TypeError(
                "consequence response requires W1 self-hearing authority"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "consequence response requires embodiment world authority"
            )
        consequence_owner.verify_owners_exact(
            reciprocal_owner=reciprocal_owner,
            articulatory_owner=articulatory_owner,
            world_authority=world_authority,
        )
        if not acoustic_authority.owns_world(world_authority):
            raise ValueError(
                "consequence response crossed W1 world ownership"
            )
        self._key = _authority_key(authority_key)
        self._reciprocal = reciprocal_owner
        self._consequences = consequence_owner
        self._articulatory = articulatory_owner
        self._acoustic = acoustic_authority
        self._world = world_authority
        self._lock = threading.RLock()

    def _seal(
        self,
        *,
        state: str,
        cue_settlement_receipt_sha256: str,
        evocation_receipt_sha256: str,
        thing_ids: tuple[str, ...],
        binding: ArticulatoryConsequenceBinding | None,
        prepared_commitment: (
            W1PreparedArticulatoryCommitment | None
        ),
        world_receipt_sha256: str,
    ) -> ConsequenceEvokedArticulatoryResponse:
        executed = prepared_commitment is not None
        provisional = ConsequenceEvokedArticulatoryResponse(
            state=state,
            cue_settlement_receipt_sha256=(
                cue_settlement_receipt_sha256
            ),
            evocation_receipt_sha256=evocation_receipt_sha256,
            thing_ids=thing_ids,
            binding_receipt_sha256=(
                None
                if binding is None
                else binding.authority_receipt_sha256
            ),
            program_id=(
                None
                if prepared_commitment is None
                else prepared_commitment.program_id
            ),
            synthesis_receipt_sha256=(
                None
                if prepared_commitment is None
                else prepared_commitment.synthesis_receipt_sha256
            ),
            synthesis_pcm_sha256=(
                None
                if prepared_commitment is None
                else prepared_commitment.pcm_sha256
            ),
            emission_receipt_sha256=(
                None
                if prepared_commitment is None
                else prepared_commitment
                .prospective_emission_receipt_sha256
            ),
            self_acoustic_receipt_sha256=(
                None
                if prepared_commitment is None
                else prepared_commitment
                .prospective_mount_receipt_sha256
            ),
            prepared_self_acoustic_commitment_receipt_sha256=(
                None
                if prepared_commitment is None
                else prepared_commitment.authority_receipt_sha256
            ),
            world_before_receipt_sha256=(
                prepared_commitment.world_before_receipt_sha256
                if executed
                else world_receipt_sha256
            ),
            world_after_receipt_sha256=(
                prepared_commitment.world_after_receipt_sha256
                if executed
                else world_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _RESPONSE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        response = ConsequenceEvokedArticulatoryResponse(
            **{
                name: getattr(provisional, name)
                for name in (
                    "state",
                    "cue_settlement_receipt_sha256",
                    "evocation_receipt_sha256",
                    "thing_ids",
                    "binding_receipt_sha256",
                    "program_id",
                    "synthesis_receipt_sha256",
                    "synthesis_pcm_sha256",
                    "emission_receipt_sha256",
                    "self_acoustic_receipt_sha256",
                    "prepared_self_acoustic_commitment_receipt_sha256",
                    "world_before_receipt_sha256",
                    "world_after_receipt_sha256",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        _verify_seal(response, response_key=self._key)
        return response

    def verify_response(
        self,
        value: ConsequenceEvokedArticulatoryResponse,
    ) -> None:
        _verify_seal(value, response_key=self._key)
        if value.state != "executed":
            return
        matches = tuple(
            binding
            for binding in self._consequences.bindings
            if binding.authority_receipt_sha256
            == value.binding_receipt_sha256
        )
        if (
            len(matches) != 1
            or matches[0].thing_id != value.thing_ids[0]
            or matches[0].program_id != value.program_id
        ):
            raise ValueError(
                "consequence-evoked response lost retained closure"
            )
        self._consequences.verify_binding(matches[0])

    def verify_committed_act(
        self,
        value: CommittedConsequenceEvokedArticulatoryAct,
    ) -> None:
        if not isinstance(
            value,
            CommittedConsequenceEvokedArticulatoryAct,
        ):
            raise TypeError(
                "consequence-evoked committed act is not typed"
            )
        self.verify_response(value.response)
        if (
            value.response.state != "executed"
            or not isinstance(value.pcm_s16le, bytes)
            or hashlib.sha256(value.pcm_s16le).hexdigest()
            != value.response.synthesis_pcm_sha256
        ):
            raise ValueError(
                "consequence-evoked committed act changed pressure"
            )

    def _silent(
        self,
        *,
        state: str,
        settlement: CausalExperienceSettlement,
        evocation,
        world_receipt_sha256: str,
    ) -> ConsequenceEvokedArticulatoryResponse:
        return self._seal(
            state=state,
            cue_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            evocation_receipt_sha256=(
                evocation.authority_receipt_sha256
            ),
            thing_ids=evocation.thing_ids,
            binding=None,
            prepared_commitment=None,
            world_receipt_sha256=world_receipt_sha256,
        )

    def respond(
        self,
        *,
        custody_authority: (
            SettledExperienceCustodyAuthority
            | RetainedAudiovisualCustodyAuthority
        ),
        custody_capability: (
            SettledExperienceConsumerCapability
            | RetainedAudiovisualCustodyCapability
        ),
    ) -> (
        ConsequenceEvokedArticulatoryResponse
        | CommittedConsequenceEvokedArticulatoryAct
    ):
        """Resolve sight, prepare every effect, then commit world last."""

        settled_custody = isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        )
        retained_visual_custody = isinstance(
            custody_authority,
            RetainedAudiovisualCustodyAuthority,
        )
        if not settled_custody and not retained_visual_custody:
            raise TypeError(
                "consequence response requires physical sight custody"
            )
        if settled_custody and not isinstance(
            custody_capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "consequence response requires settled sight capability"
            )
        if retained_visual_custody and not isinstance(
            custody_capability,
            RetainedAudiovisualCustodyCapability,
        ):
            raise TypeError(
                "consequence response requires retained sight capability"
            )
        if (
            custody_capability.consumer_id
            != CONSEQUENCE_EVOKED_RESPONSE_CONSUMER_ID
        ):
            raise ValueError(
                "consequence response requires its dedicated capability"
            )
        with self._lock:
            before = self._world.observation_snapshot()
            if settled_custody:
                view = custody_authority.open_child(
                    custody_capability
                )
                if (
                    view.source_kind
                    is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
                ):
                    raise ValueError(
                        "consequence response requires physical sight "
                        "custody"
                    )
                settlement = view.causal_settlement
                if view.world_observation != before:
                    raise ValueError(
                        "consequence response cue occurrence is not "
                        "current"
                    )
            else:
                retained = custody_authority.open_child(
                    custody_capability
                )
                settlement = retained.settlement
            if not isinstance(settlement, CausalExperienceSettlement):
                raise TypeError(
                    "consequence response custody lost causal settlement"
                )
            settlement.verify()
            sight = tuple(
                interpretation
                for interpretation in settlement.interpretations
                if interpretation.sense == "sight"
            )
            if (
                len(sight) != 1
                or sight[0].state != "observed"
                or not sight[0].substreams
            ):
                raise ValueError(
                    "consequence response requires observed physical sight"
                )
            evocation = self._reciprocal.evoke(
                settlement,
                cue_senses=("sight",),
            )
            self._reciprocal.verify_evocation(evocation)
            if evocation.state != "unique":
                if self._world.observation_snapshot() != before:
                    raise RuntimeError(
                        "unresolved consequence cue changed the world"
                    )
                return self._silent(
                    state=evocation.state,
                    settlement=settlement,
                    evocation=evocation,
                    world_receipt_sha256=(
                        before.authority_receipt_sha256
                    ),
                )
            matches = tuple(
                binding
                for binding in self._consequences.bindings
                if binding.thing_id == evocation.thing_ids[0]
            )
            if len(matches) != 1:
                if self._world.observation_snapshot() != before:
                    raise RuntimeError(
                        "unbound consequence cue changed the world"
                    )
                return self._silent(
                    state="unbound" if not matches else "ambiguous",
                    settlement=settlement,
                    evocation=evocation,
                    world_receipt_sha256=(
                        before.authority_receipt_sha256
                    ),
                )
            binding = matches[0]
            self._consequences.verify_binding(binding)
            synthesis = self._articulatory.synthesize(
                program_id=binding.program_id,
                source_time_start=Fraction(
                    before.revision * MAX_VOCAL_SAMPLE_COUNT,
                    VOCAL_SAMPLE_RATE_HZ,
                ),
            )
            intent = _digest({
                "binding_receipt_sha256": (
                    binding.authority_receipt_sha256
                ),
                "cue_settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "evocation_receipt_sha256": (
                    evocation.authority_receipt_sha256
                ),
                "schema": INTENT_SCHEMA,
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
            try:
                commitment = (
                    self._acoustic.prepared_articulatory_commitment(
                        prepared_acoustic
                    )
                )
                (
                    self._acoustic
                    .verify_prepared_articulatory_commitment(
                        prepared_acoustic,
                        commitment,
                    )
                )
                if (
                    commitment.program_id != binding.program_id
                    or commitment.world_before_receipt_sha256
                    != before.authority_receipt_sha256
                ):
                    raise ValueError(
                        "prepared consequence response crossed custody"
                    )
                response = self._seal(
                    state="executed",
                    cue_settlement_receipt_sha256=(
                        settlement.authority_receipt_sha256
                    ),
                    evocation_receipt_sha256=(
                        evocation.authority_receipt_sha256
                    ),
                    thing_ids=evocation.thing_ids,
                    binding=binding,
                    prepared_commitment=commitment,
                    world_receipt_sha256=(
                        before.authority_receipt_sha256
                    ),
                )
                act = CommittedConsequenceEvokedArticulatoryAct(
                    response=response,
                    pcm_s16le=prepared_emission.pcm_s16le,
                )
                if (
                    hashlib.sha256(act.pcm_s16le).hexdigest()
                    != response.synthesis_pcm_sha256
                ):
                    raise ValueError(
                        "prepared consequence response pressure changed"
                    )
            except BaseException:
                self._acoustic.discard_prepared_articulatory(
                    prepared_acoustic
                )
                raise
            _emission, _mount, _undo = (
                self._acoustic.commit_prepared_articulatory(
                    prepared_acoustic
                )
            )
            return act

    def status(self) -> dict[str, object]:
        return {
            "retained_pcm_bytes": 0,
            "retained_replay_receipts": 0,
            "schema": STATUS_SCHEMA,
            "stateful": False,
        }


__all__ = (
    "ACT_SCHEMA",
    "CONSEQUENCE_EVOKED_RESPONSE_CONSUMER_ID",
    "INTENT_SCHEMA",
    "RESPONSE_SCHEMA",
    "STATUS_SCHEMA",
    "CommittedConsequenceEvokedArticulatoryAct",
    "ConsequenceEvokedArticulatoryResponse",
    "ConsequenceEvokedArticulatoryResponseAuthority",
    "verify_consequence_evoked_articulatory_response",
)
