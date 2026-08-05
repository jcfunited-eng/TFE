"""Transient typed custody for one verified settled sound cue.

The owner accepts either a dedicated child of settled-experience custody or
an already-closed, self-verifying causal settlement.  Both routes retain the
same complete sound roots for one reciprocal recall.  The owner never accepts
or retains raw pressure, creates or extends a THING, or persists cue state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field

from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)


LIVE_SOUND_CUE_SOURCE_CONSUMER_ID = "guala.live_sound_cue.source"
SOUND_EVOKED_CAUSAL_THING_CONSUMER_ID = (
    "guala.sound_evoked_causal_thing"
)

CUSTODY_SCHEMA = "guala.live_sound_cue.custody.v1"
CAPABILITY_SCHEMA = "guala.live_sound_cue.capability.v1"
STATUS_SCHEMA = "guala.live_sound_cue.status.v1"
DIRECT_OCCURRENCE_SCHEMA = (
    "guala.live_sound_cue.direct_settlement_occurrence.v1"
)
DIRECT_AUTHORITY_SCHEMA = (
    "guala.live_sound_cue.direct_settlement_authority.v1"
)

_SOURCE_KINDS = frozenset((
    "settled_experience_capability",
    "verified_causal_settlement",
))
_CUSTODY_DOMAIN = b"guala-live-sound-cue-custody-v1\0"
_CAPABILITY_DOMAIN = b"guala-live-sound-cue-capability-v1\0"
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
        raise ValueError("live sound cue authority key changed")
    return hashlib.sha256(_CUSTODY_DOMAIN + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class LiveSoundCueCustody:
    source_kind: str
    source_occurrence_id: str
    source_parent_receipt_sha256: str
    source_authority_receipt_sha256: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    sound_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _settlement: CausalExperienceSettlement = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "schema": CUSTODY_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "sound_roots": [
                root.record() for root in self.sound_roots
            ],
            "source_authority_receipt_sha256": (
                self.source_authority_receipt_sha256
            ),
            "source_kind": self.source_kind,
            "source_occurrence_id": self.source_occurrence_id,
            "source_parent_receipt_sha256": (
                self.source_parent_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class LiveSoundCueCapability:
    consumer_id: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "consumer_id": self.consumer_id,
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "schema": CAPABILITY_SCHEMA,
            "source_occurrence_id": self.source_occurrence_id,
        }


@dataclass(frozen=True, slots=True)
class LiveSoundCueView:
    source_kind: str
    source_occurrence_id: str
    source_parent_receipt_sha256: str
    source_authority_receipt_sha256: str
    cue_custody_receipt_sha256: str
    cue_capability_receipt_sha256: str
    settlement_receipt_sha256: str
    sound_roots: tuple[FullFieldSensoryRoot, ...]
    causal_settlement: CausalExperienceSettlement
    _construction_authority: object = field(repr=False, compare=False)


class LiveSoundCueCustodyAuthority:
    """Own one verified sound settlement until one recall consumes it."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_sound_roots: int,
    ) -> None:
        root = _key(authority_key)
        self._custody_key = hashlib.sha256(
            _CUSTODY_DOMAIN + root
        ).digest()
        self._capability_key = hashlib.sha256(
            _CAPABILITY_DOMAIN + root
        ).digest()
        self._max_sound_roots = _positive(
            max_sound_roots,
            "live sound cue root capacity",
        )
        self._owner_authority = object()
        self._custody: LiveSoundCueCustody | None = None
        self._capability: LiveSoundCueCapability | None = None
        self._consumed_capability_receipt_sha256: str | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _sound_roots(
        settlement: CausalExperienceSettlement,
    ) -> tuple[FullFieldSensoryRoot, ...]:
        settlement.verify()
        return tuple(
            root
            for root in full_field_sensory_roots(settlement)
            if root.sense == "sound"
        )

    def verify_custody(self, value: LiveSoundCueCustody) -> None:
        if (
            not isinstance(value, LiveSoundCueCustody)
            or value._construction_authority
            is not _CONSTRUCTION_AUTHORITY
            or value._owner_authority is not self._owner_authority
            or value.source_kind not in _SOURCE_KINDS
        ):
            raise ValueError("live sound cue custody changed")
        for digest, label in (
            (value.source_occurrence_id, "sound cue occurrence"),
            (
                value.source_parent_receipt_sha256,
                "sound cue source parent",
            ),
            (
                value.source_authority_receipt_sha256,
                "sound cue source authority",
            ),
            (
                value.settlement_receipt_sha256,
                "sound cue settlement",
            ),
            (
                value.settlement_structural_fingerprint,
                "sound cue structural fingerprint",
            ),
            (value.authority_hmac_sha256, "sound cue custody HMAC"),
            (
                value.authority_receipt_sha256,
                "sound cue custody authority",
            ),
        ):
            _sha(digest, label)
        exact_roots = self._sound_roots(value._settlement)
        if (
            not value.sound_roots
            or len(value.sound_roots) > self._max_sound_roots
            or value.sound_roots != exact_roots
            or value.settlement_receipt_sha256
            != value._settlement.authority_receipt_sha256
            or value.settlement_structural_fingerprint
            != value._settlement.structural_fingerprint
        ):
            raise ValueError("live sound cue lost its complete sound field")
        for root in value.sound_roots:
            root.verify()
        expected_hmac = hmac.new(
            self._custody_key,
            _CUSTODY_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("live sound cue custody authority changed")

    def _admit_verified(
        self,
        *,
        settlement: CausalExperienceSettlement,
        source_kind: str,
        source_occurrence_id: str,
        source_parent_receipt_sha256: str,
        source_authority_receipt_sha256: str,
    ) -> LiveSoundCueCustody:
        if source_kind not in _SOURCE_KINDS:
            raise ValueError("live sound cue source kind changed")
        for digest, label in (
            (source_occurrence_id, "sound cue occurrence"),
            (source_parent_receipt_sha256, "sound cue source parent"),
            (
                source_authority_receipt_sha256,
                "sound cue source authority",
            ),
        ):
            _sha(digest, label)
        roots = self._sound_roots(settlement)
        if not roots:
            raise ValueError("live sound cue has no observed sound field")
        if len(roots) > self._max_sound_roots:
            raise RuntimeError("live sound cue root capacity exhausted")
        provisional = LiveSoundCueCustody(
            source_kind=source_kind,
            source_occurrence_id=source_occurrence_id,
            source_parent_receipt_sha256=(
                source_parent_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                source_authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                settlement.structural_fingerprint
            ),
            sound_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _settlement=settlement,
            _owner_authority=self._owner_authority,
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        signature = hmac.new(
            self._custody_key,
            _CUSTODY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = LiveSoundCueCustody(
            source_kind=provisional.source_kind,
            source_occurrence_id=provisional.source_occurrence_id,
            source_parent_receipt_sha256=(
                provisional.source_parent_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                provisional.source_authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                provisional.settlement_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                provisional.settlement_structural_fingerprint
            ),
            sound_roots=provisional.sound_roots,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _settlement=settlement,
            _owner_authority=self._owner_authority,
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        self.verify_custody(result)
        with self._lock:
            if self._custody is not None:
                if self._custody == result:
                    return self._custody
                raise RuntimeError("live sound cue custody capacity is full")
            if self._consumed_capability_receipt_sha256 is not None:
                raise RuntimeError(
                    "live sound cue authority already consumed one cue"
                )
            self._custody = result
            return result

    def admit(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> LiveSoundCueCustody:
        """Admit one dedicated child of settled-experience custody."""

        if (
            not isinstance(
                custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != LIVE_SOUND_CUE_SOURCE_CONSUMER_ID
        ):
            raise ValueError(
                "live sound cue requires its dedicated settled capability"
            )
        view = custody_authority.open_child(custody_capability)
        return self._admit_verified(
            settlement=view.causal_settlement,
            source_kind="settled_experience_capability",
            source_occurrence_id=view.source_occurrence_id,
            source_parent_receipt_sha256=(
                view.parent_custody_receipt_sha256
            ),
            source_authority_receipt_sha256=(
                custody_capability.authority_receipt_sha256
            ),
        )

    def admit_verified_settlement(
        self,
        settlement: CausalExperienceSettlement,
    ) -> LiveSoundCueCustody:
        """Admit one already-closed settlement without invented custody."""

        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "live sound cue requires a causal settlement"
            )
        settlement.verify()
        occurrence = _digest({
            "schema": DIRECT_OCCURRENCE_SCHEMA,
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                settlement.structural_fingerprint
            ),
        })
        direct_authority = _digest({
            "schema": DIRECT_AUTHORITY_SCHEMA,
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "source_occurrence_id": occurrence,
        })
        return self._admit_verified(
            settlement=settlement,
            source_kind="verified_causal_settlement",
            source_occurrence_id=occurrence,
            source_parent_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            source_authority_receipt_sha256=direct_authority,
        )

    def issue_recall(
        self,
        custody: LiveSoundCueCustody,
    ) -> LiveSoundCueCapability:
        self.verify_custody(custody)
        with self._lock:
            if self._custody is not custody:
                raise ValueError("live sound cue left owner custody")
            if self._capability is not None:
                return self._capability
            provisional = LiveSoundCueCapability(
                consumer_id=SOUND_EVOKED_CAUSAL_THING_CONSUMER_ID,
                source_occurrence_id=custody.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _owner_authority=self._owner_authority,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
            )
            signature = hmac.new(
                self._capability_key,
                _CAPABILITY_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            self._capability = LiveSoundCueCapability(
                consumer_id=provisional.consumer_id,
                source_occurrence_id=provisional.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    provisional.parent_custody_receipt_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
                _owner_authority=self._owner_authority,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
            )
            return self._capability

    def _verify_capability(
        self,
        capability: LiveSoundCueCapability,
        custody: LiveSoundCueCustody,
    ) -> None:
        if (
            not isinstance(capability, LiveSoundCueCapability)
            or capability._construction_authority
            is not _CONSTRUCTION_AUTHORITY
            or capability._owner_authority is not self._owner_authority
            or capability.consumer_id
            != SOUND_EVOKED_CAUSAL_THING_CONSUMER_ID
            or capability.source_occurrence_id
            != custody.source_occurrence_id
            or capability.parent_custody_receipt_sha256
            != custody.authority_receipt_sha256
        ):
            raise ValueError("live sound cue recall capability changed")
        for digest, label in (
            (
                capability.authority_hmac_sha256,
                "sound cue capability HMAC",
            ),
            (
                capability.authority_receipt_sha256,
                "sound cue capability authority",
            ),
        ):
            _sha(digest, label)
        expected_hmac = hmac.new(
            self._capability_key,
            _CAPABILITY_DOMAIN + _canonical(capability.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                capability.authority_hmac_sha256,
            )
            or capability.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": capability.payload(),
            })
        ):
            raise ValueError(
                "live sound cue recall capability authority changed"
            )

    def consume(
        self,
        capability: LiveSoundCueCapability,
    ) -> LiveSoundCueView:
        with self._lock:
            custody = self._custody
            if custody is None:
                raise RuntimeError("live sound cue is no longer available")
            self.verify_custody(custody)
            self._verify_capability(capability, custody)
            if self._capability is not capability:
                raise ValueError(
                    "live sound cue recall capability left owner custody"
                )
            result = LiveSoundCueView(
                source_kind=custody.source_kind,
                source_occurrence_id=custody.source_occurrence_id,
                source_parent_receipt_sha256=(
                    custody.source_parent_receipt_sha256
                ),
                source_authority_receipt_sha256=(
                    custody.source_authority_receipt_sha256
                ),
                cue_custody_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                cue_capability_receipt_sha256=(
                    capability.authority_receipt_sha256
                ),
                settlement_receipt_sha256=(
                    custody.settlement_receipt_sha256
                ),
                sound_roots=custody.sound_roots,
                causal_settlement=custody._settlement,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
            )
            self._consumed_capability_receipt_sha256 = (
                capability.authority_receipt_sha256
            )
            self._custody = None
            self._capability = None
            return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "available_cues": 1 if self._custody is not None else 0,
                "cold_state_persisted": False,
                "consumed": (
                    self._consumed_capability_receipt_sha256 is not None
                ),
                "max_live_cues": 1,
                "max_sound_roots": self._max_sound_roots,
                "raw_pressure_bytes_retained": 0,
                "schema": STATUS_SCHEMA,
            }


__all__ = (
    "LIVE_SOUND_CUE_SOURCE_CONSUMER_ID",
    "SOUND_EVOKED_CAUSAL_THING_CONSUMER_ID",
    "LiveSoundCueCapability",
    "LiveSoundCueCustody",
    "LiveSoundCueCustodyAuthority",
    "LiveSoundCueView",
)
