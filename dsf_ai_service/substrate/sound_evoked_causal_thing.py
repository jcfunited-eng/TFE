"""Stateless sound-cue evocation of an existing reciprocal causal THING."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field

from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalEvocation,
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.live_sound_cue_custody import (
    LiveSoundCueCapability,
    LiveSoundCueCustodyAuthority,
)


RESULT_SCHEMA = "guala.sound_evoked_causal_thing.result.v1"
STATUS_SCHEMA = "guala.sound_evoked_causal_thing.status.v1"

_RESULT_DOMAIN = b"guala-sound-evoked-causal-thing-result-v1\0"
_HEX = frozenset("0123456789abcdef")
_CONSTRUCTION_AUTHORITY = object()


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
        raise ValueError("sound-evoked THING authority key changed")
    return hashlib.sha256(_RESULT_DOMAIN + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class SoundEvokedCausalThingResult:
    state: str
    thing_ids: tuple[str, ...]
    source_kind: str
    source_occurrence_id: str
    source_parent_receipt_sha256: str
    source_authority_receipt_sha256: str
    cue_custody_receipt_sha256: str
    cue_capability_receipt_sha256: str
    settlement_receipt_sha256: str
    cue_roots: tuple[FullFieldSensoryRoot, ...]
    evoked_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    reciprocal_evocation: CausalThingReciprocalEvocation
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "cue_capability_receipt_sha256": (
                self.cue_capability_receipt_sha256
            ),
            "cue_custody_receipt_sha256": (
                self.cue_custody_receipt_sha256
            ),
            "cue_roots": [root.record() for root in self.cue_roots],
            "evoked_full_field_roots": [
                root.record() for root in self.evoked_full_field_roots
            ],
            "reciprocal_evocation_receipt_sha256": (
                self.reciprocal_evocation.authority_receipt_sha256
            ),
            "schema": RESULT_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "source_authority_receipt_sha256": (
                self.source_authority_receipt_sha256
            ),
            "source_kind": self.source_kind,
            "source_occurrence_id": self.source_occurrence_id,
            "source_parent_receipt_sha256": (
                self.source_parent_receipt_sha256
            ),
            "state": self.state,
            "thing_ids": list(self.thing_ids),
        }


class SoundEvokedCausalThingAuthority:
    """Consume one sound cue and ask reciprocal memory without learning."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
    ) -> None:
        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "sound-evoked THING requires reciprocal mosaic ownership"
            )
        self._result_key = hashlib.sha256(
            _RESULT_DOMAIN + _key(authority_key)
        ).digest()
        self._reciprocal = reciprocal_owner
        self._owner_authority = object()

    def evoke(
        self,
        *,
        custody_authority: LiveSoundCueCustodyAuthority,
        custody_capability: LiveSoundCueCapability,
    ) -> SoundEvokedCausalThingResult:
        if not isinstance(
            custody_authority,
            LiveSoundCueCustodyAuthority,
        ):
            raise TypeError(
                "sound-evoked THING requires live sound cue custody"
            )
        view = custody_authority.consume(custody_capability)
        evocation = self._reciprocal.evoke(
            view.causal_settlement,
            cue_senses=("sound",),
        )
        self._reciprocal.verify_evocation(evocation)
        if evocation.cue_roots != view.sound_roots:
            raise ValueError(
                "sound-evoked THING crossed complete cue roots"
            )
        provisional = SoundEvokedCausalThingResult(
            state=evocation.state,
            thing_ids=evocation.thing_ids,
            source_kind=view.source_kind,
            source_occurrence_id=view.source_occurrence_id,
            source_parent_receipt_sha256=(
                view.source_parent_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                view.source_authority_receipt_sha256
            ),
            cue_custody_receipt_sha256=(
                view.cue_custody_receipt_sha256
            ),
            cue_capability_receipt_sha256=(
                view.cue_capability_receipt_sha256
            ),
            settlement_receipt_sha256=(
                view.settlement_receipt_sha256
            ),
            cue_roots=view.sound_roots,
            evoked_full_field_roots=(
                evocation.evoked_full_field_roots
            ),
            reciprocal_evocation=evocation,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _owner_authority=self._owner_authority,
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        signature = hmac.new(
            self._result_key,
            _RESULT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = SoundEvokedCausalThingResult(
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
        self.verify(result)
        return result

    def verify(self, value: SoundEvokedCausalThingResult) -> None:
        if (
            not isinstance(value, SoundEvokedCausalThingResult)
            or value._construction_authority
            is not _CONSTRUCTION_AUTHORITY
            or value._owner_authority is not self._owner_authority
            or value.state not in {
                "unique",
                "ambiguous",
                "unresolved",
            }
        ):
            raise ValueError("sound-evoked THING result changed")
        self._reciprocal.verify_evocation(
            value.reciprocal_evocation
        )
        for digest, label in (
            (value.source_occurrence_id, "sound occurrence"),
            (
                value.source_parent_receipt_sha256,
                "sound source parent",
            ),
            (
                value.source_authority_receipt_sha256,
                "sound source authority",
            ),
            (
                value.cue_custody_receipt_sha256,
                "sound cue custody",
            ),
            (
                value.cue_capability_receipt_sha256,
                "sound cue capability",
            ),
            (value.settlement_receipt_sha256, "sound settlement"),
            (
                value.authority_hmac_sha256,
                "sound-evoked result HMAC",
            ),
            (
                value.authority_receipt_sha256,
                "sound-evoked result authority",
            ),
        ):
            _sha(digest, label)
        evocation = value.reciprocal_evocation
        if (
            evocation.cue_senses != ("sound",)
            or value.state != evocation.state
            or value.thing_ids != evocation.thing_ids
            or value.cue_roots != evocation.cue_roots
            or any(root.sense != "sound" for root in value.cue_roots)
            or value.evoked_full_field_roots
            != evocation.evoked_full_field_roots
            or (
                value.state == "unique"
                and not value.evoked_full_field_roots
            )
            or (
                value.state != "unique"
                and value.evoked_full_field_roots
            )
        ):
            raise ValueError(
                "sound-evoked THING result crossed reciprocal authority"
            )
        for root in value.cue_roots:
            root.verify()
        for root in value.evoked_full_field_roots:
            root.verify()
        expected_hmac = hmac.new(
            self._result_key,
            _RESULT_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": value.payload(),
            })
        ):
            raise ValueError(
                "sound-evoked THING result authority changed"
            )

    def status(self) -> dict[str, object]:
        return {
            "cold_state_persisted": False,
            "cue_sense": "sound",
            "identity_creation_authority": False,
            "learned_state_owner": "causal_thing_reciprocal_mosaic",
            "schema": STATUS_SCHEMA,
            "signal_matching": False,
        }


__all__ = (
    "SoundEvokedCausalThingAuthority",
    "SoundEvokedCausalThingResult",
)
