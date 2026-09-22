"""Sight-only recall of one lived articulatory THING relation.

This authority does not recognize a word and does not assign a label.  It
accepts one exact sight cue, asks the reciprocal THING owner whether that cue
selects exactly one lived mosaic, and acts only when that THING has exactly
one retained articulatory program.  The emitted pressure is freshly
synthesized from the retained larynx/tract program for this occurrence.

No transcript, string, named profile, prerecorded TTS artifact, chi identity,
score, tolerance, nearest-neighbour rule, or reduced DSF field participates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)


RESPONSE_SCHEMA = "guala.sight_evoked_articulatory_response.v1"
_RESPONSE_DOMAIN = b"guala-sight-evoked-articulatory-response-v1\0"
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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(
            "sight-evoked articulatory authority key boundary changed"
        )
    return hashlib.sha256(_RESPONSE_DOMAIN + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} changed")
    return value


@dataclass(frozen=True, slots=True)
class SightEvokedArticulatoryResponse:
    state: str
    cue_settlement_receipt_sha256: str
    evocation_receipt_sha256: str
    thing_ids: tuple[str, ...]
    binding_receipt_sha256: str | None
    program_id: str | None
    motor_id: str | None
    synthesis_receipt_sha256: str | None
    synthesis_pcm_sha256: str | None
    emission_receipt_sha256: str | None
    emitted_pcm_sha256: str | None
    self_acoustic_receipt_sha256: str | None
    articulatory_custody_receipt_sha256: str | None
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "articulatory_custody_receipt_sha256": (
                self.articulatory_custody_receipt_sha256
            ),
            "binding_receipt_sha256": self.binding_receipt_sha256,
            "cue_settlement_receipt_sha256": (
                self.cue_settlement_receipt_sha256
            ),
            "emission_receipt_sha256": self.emission_receipt_sha256,
            "emitted_pcm_sha256": self.emitted_pcm_sha256,
            "evocation_receipt_sha256": self.evocation_receipt_sha256,
            "motor_id": self.motor_id,
            "program_id": self.program_id,
            "schema": RESPONSE_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt_sha256
            ),
            "state": self.state,
            "synthesis_pcm_sha256": self.synthesis_pcm_sha256,
            "synthesis_receipt_sha256": self.synthesis_receipt_sha256,
            "thing_ids": list(self.thing_ids),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _verify_response_with_key(
    value: SightEvokedArticulatoryResponse,
    *,
    response_key: bytes,
) -> None:
    if not isinstance(value, SightEvokedArticulatoryResponse):
        raise TypeError("sight-evoked response is not typed")
    if value.state not in {
        "executed",
        "unresolved",
        "ambiguous",
        "unbound",
    }:
        raise ValueError("sight-evoked response state changed")
    for digest, label in (
        (
            value.cue_settlement_receipt_sha256,
            "sight cue settlement",
        ),
        (value.evocation_receipt_sha256, "sight cue evocation"),
        (
            value.world_before_receipt_sha256,
            "sight response world before",
        ),
        (
            value.world_after_receipt_sha256,
            "sight response world after",
        ),
        (value.authority_hmac_sha256, "sight response HMAC"),
        (value.authority_receipt_sha256, "sight response authority"),
    ):
        _sha(digest, label)
    for thing_id in value.thing_ids:
        _sha(thing_id, "sight response THING")
    act = (
        value.binding_receipt_sha256,
        value.program_id,
        value.motor_id,
        value.synthesis_receipt_sha256,
        value.synthesis_pcm_sha256,
        value.emission_receipt_sha256,
        value.emitted_pcm_sha256,
        value.self_acoustic_receipt_sha256,
        value.articulatory_custody_receipt_sha256,
    )
    if value.state == "executed":
        for digest in act:
            _sha(digest, "sight response physical act")
        if (
            len(value.thing_ids) != 1
            or value.world_before_receipt_sha256
            == value.world_after_receipt_sha256
            or value.synthesis_pcm_sha256
            != value.emitted_pcm_sha256
        ):
            raise ValueError(
                "executed sight response lost physical custody"
            )
    elif (
        any(digest is not None for digest in act)
        or value.world_before_receipt_sha256
        != value.world_after_receipt_sha256
    ):
        raise ValueError(
            "silent sight response changed the world or selected a motor"
        )
    signature = hmac.new(
        response_key,
        _RESPONSE_DOMAIN + _canonical(value.payload()),
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(
            signature, value.authority_hmac_sha256
        )
        or value.authority_receipt_sha256
        != _digest({
            "authority_hmac_sha256": signature,
            "payload": value.payload(),
        })
    ):
        raise ValueError("sight-evoked response authority changed")


def verify_sight_evoked_articulatory_response(
    value: SightEvokedArticulatoryResponse,
    *,
    authority_key: bytes | str,
) -> None:
    """Verify one response without requiring live motor dependencies."""

    _verify_response_with_key(value, response_key=_key(authority_key))


class SightEvokedArticulatoryResponseAuthority:
    """Release no motor unless sight selects one lived THING and program."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
        acoustic_authority: W1SelfAcousticPropagationAuthority,
    ) -> None:
        if not isinstance(
            reciprocal_owner, CausalThingReciprocalMosaicOwner
        ):
            raise TypeError(
                "sight response requires reciprocal THING authority"
            )
        if not isinstance(
            articulatory_owner, ArticulatorySelfVocalMotorOwner
        ):
            raise TypeError(
                "sight response requires articulatory motor authority"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("sight response requires W1 world authority")
        if not isinstance(
            acoustic_authority, W1SelfAcousticPropagationAuthority
        ):
            raise TypeError(
                "sight response requires self-acoustic authority"
            )
        self._key = _key(authority_key)
        self._reciprocal = reciprocal_owner
        self._articulatory = articulatory_owner
        self._world = world_authority
        self._acoustic = acoustic_authority

    def _seal(
        self,
        *,
        state: str,
        cue_settlement_receipt_sha256: str,
        evocation_receipt_sha256: str,
        thing_ids: tuple[str, ...],
        binding_receipt_sha256: str | None,
        program_id: str | None,
        motor_id: str | None,
        synthesis_receipt_sha256: str | None,
        synthesis_pcm_sha256: str | None,
        emission_receipt_sha256: str | None,
        emitted_pcm_sha256: str | None,
        self_acoustic_receipt_sha256: str | None,
        articulatory_custody_receipt_sha256: str | None,
        world_before_receipt_sha256: str,
        world_after_receipt_sha256: str,
    ) -> SightEvokedArticulatoryResponse:
        provisional = SightEvokedArticulatoryResponse(
            state=state,
            cue_settlement_receipt_sha256=(
                cue_settlement_receipt_sha256
            ),
            evocation_receipt_sha256=evocation_receipt_sha256,
            thing_ids=thing_ids,
            binding_receipt_sha256=binding_receipt_sha256,
            program_id=program_id,
            motor_id=motor_id,
            synthesis_receipt_sha256=synthesis_receipt_sha256,
            synthesis_pcm_sha256=synthesis_pcm_sha256,
            emission_receipt_sha256=emission_receipt_sha256,
            emitted_pcm_sha256=emitted_pcm_sha256,
            self_acoustic_receipt_sha256=(
                self_acoustic_receipt_sha256
            ),
            articulatory_custody_receipt_sha256=(
                articulatory_custody_receipt_sha256
            ),
            world_before_receipt_sha256=world_before_receipt_sha256,
            world_after_receipt_sha256=world_after_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _RESPONSE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = SightEvokedArticulatoryResponse(
            **{
                field: getattr(provisional, field)
                for field in (
                    "state",
                    "cue_settlement_receipt_sha256",
                    "evocation_receipt_sha256",
                    "thing_ids",
                    "binding_receipt_sha256",
                    "program_id",
                    "motor_id",
                    "synthesis_receipt_sha256",
                    "synthesis_pcm_sha256",
                    "emission_receipt_sha256",
                    "emitted_pcm_sha256",
                    "self_acoustic_receipt_sha256",
                    "articulatory_custody_receipt_sha256",
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
        self.verify_response(result)
        return result

    def verify_response(
        self, value: SightEvokedArticulatoryResponse
    ) -> None:
        _verify_response_with_key(value, response_key=self._key)

    def respond(
        self,
        settlement: CausalExperienceSettlement,
    ) -> SightEvokedArticulatoryResponse:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "sight response requires one causal settlement"
            )
        settlement.verify()
        before = self._world.observation_snapshot()
        evocation = self._reciprocal.evoke(
            settlement,
            cue_senses=("sight",),
        )
        self._reciprocal.verify_evocation(evocation)
        if evocation.state != "unique":
            after = self._world.observation_snapshot()
            if after != before:
                raise RuntimeError(
                    "unresolved sight cue changed the physical world"
                )
            return self._seal(
                state=evocation.state,
                cue_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                evocation_receipt_sha256=(
                    evocation.authority_receipt_sha256
                ),
                thing_ids=evocation.thing_ids,
                binding_receipt_sha256=None,
                program_id=None,
                motor_id=None,
                synthesis_receipt_sha256=None,
                synthesis_pcm_sha256=None,
                emission_receipt_sha256=None,
                emitted_pcm_sha256=None,
                self_acoustic_receipt_sha256=None,
                articulatory_custody_receipt_sha256=None,
                world_before_receipt_sha256=(
                    before.authority_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    after.authority_receipt_sha256
                ),
            )
        matches = tuple(
            binding
            for binding in self._articulatory.thing_program_bindings
            if binding.thing_id == evocation.thing_ids[0]
        )
        if len(matches) != 1:
            after = self._world.observation_snapshot()
            if after != before:
                raise RuntimeError(
                    "unbound sight cue changed the physical world"
                )
            return self._seal(
                state="unbound" if not matches else "ambiguous",
                cue_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                evocation_receipt_sha256=(
                    evocation.authority_receipt_sha256
                ),
                thing_ids=evocation.thing_ids,
                binding_receipt_sha256=None,
                program_id=None,
                motor_id=None,
                synthesis_receipt_sha256=None,
                synthesis_pcm_sha256=None,
                emission_receipt_sha256=None,
                emitted_pcm_sha256=None,
                self_acoustic_receipt_sha256=None,
                articulatory_custody_receipt_sha256=None,
                world_before_receipt_sha256=(
                    before.authority_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    after.authority_receipt_sha256
                ),
            )
        binding = matches[0]
        self._articulatory.verify_thing_program_binding(binding)
        synthesis = self._articulatory.synthesize(
            program_id=binding.program_id,
            source_time_start=Fraction(
                before.revision * MAX_VOCAL_SAMPLE_COUNT,
                VOCAL_SAMPLE_RATE_HZ,
            ),
        )
        self._articulatory.verify_synthesis(synthesis)
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
            "schema": "guala.sight_evoked_articulatory_intent.v1",
            "synthesis_receipt_sha256": (
                synthesis.receipt.authority_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                before.authority_receipt_sha256
            ),
        })
        emission = self._articulatory.execute_synthesis(
            synthesis=synthesis,
            world_authority=self._world,
            causal_intent_receipt_sha256=intent,
        )
        acoustic_mount = self._acoustic.propagate_articulatory(
            emission=emission,
            articulatory_owner=self._articulatory,
        )
        after = self._world.observation_snapshot()
        return self._seal(
            state="executed",
            cue_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            evocation_receipt_sha256=(
                evocation.authority_receipt_sha256
            ),
            thing_ids=evocation.thing_ids,
            binding_receipt_sha256=(
                binding.authority_receipt_sha256
            ),
            program_id=binding.program_id,
            motor_id=binding.program_id,
            synthesis_receipt_sha256=(
                synthesis.receipt.authority_receipt_sha256
            ),
            synthesis_pcm_sha256=hashlib.sha256(
                synthesis.radiated_pcm_s16le
            ).hexdigest(),
            emission_receipt_sha256=(
                emission.emission_receipt.authority_receipt_sha256
            ),
            emitted_pcm_sha256=hashlib.sha256(
                emission.pcm_s16le
            ).hexdigest(),
            self_acoustic_receipt_sha256=(
                acoustic_mount.receipt.authority_receipt_sha256
            ),
            articulatory_custody_receipt_sha256=(
                emission.emission_receipt.authority_receipt_sha256
            ),
            world_before_receipt_sha256=(
                before.authority_receipt_sha256
            ),
            world_after_receipt_sha256=(
                after.authority_receipt_sha256
            ),
        )


__all__ = (
    "RESPONSE_SCHEMA",
    "SightEvokedArticulatoryResponse",
    "SightEvokedArticulatoryResponseAuthority",
    "verify_sight_evoked_articulatory_response",
)
