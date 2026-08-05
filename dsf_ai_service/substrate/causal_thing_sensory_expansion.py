"""Bounded physical sensory expansion of contact-grounded causal THINGs.

A retained audiovisual occurrence is not knowledge merely because its media
was decoded or its DSF field settled.  This module gives such an occurrence
one typed custody boundary and permits its complete sight/sound roots to enter
memory only in either of two cases:

* an explicit lived tutor encounter names one already contact-grounded THING;
* the complete sight field already resolves exactly one such admitted
  occurrence, in which case co-occurring sound may extend that same THING.

The causal THING owner's ``thing_id`` is the sole identity.  This owner cannot
create or merge identities.  It stores no title, transcript, filename, label,
token, score, threshold, similarity, chi identity, raw media, or scripted
meaning.  Every admitted root retains its complete explicit DSF field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
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


OCCURRENCE_SCHEMA = "guala.retained_audiovisual.custody.v1"
CAPABILITY_SCHEMA = "guala.retained_audiovisual.custody_capability.v1"
EXPANSION_SCHEMA = "guala.causal_thing.sensory_expansion.v2"
STATE_SCHEMA = "guala.causal_thing.sensory_expansion.state.v2"
ENVELOPE_SCHEMA = "guala.causal_thing.sensory_expansion.state_hmac.v2"
STATUS_SCHEMA = "guala.causal_thing.sensory_expansion.status.v1"
THING_SENSORY_EXPANSION_CONSUMER_ID = (
    "guala.causal_thing.sensory_expansion"
)
THING_SENSORY_GROUNDING_CONSUMER_ID = (
    "guala.causal_thing.sensory_expansion.contact_grounding"
)
RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID = (
    "guala.retained_visual.consequence_articulatory_response"
)
_RETAINED_CUSTODY_CONSUMER_IDS = frozenset((
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID,
))

_OCCURRENCE_DOMAIN = b"guala-retained-av-custody-v1\0"
_CAPABILITY_DOMAIN = b"guala-retained-av-custody-capability-v1\0"
_EXPANSION_DOMAIN = b"guala-causal-thing-sensory-expansion-v2\0"
_STATE_DOMAIN = b"guala-causal-thing-sensory-expansion-state-v2\0"
_HEX = frozenset("0123456789abcdef")
_PREPARED_ADMISSION_CONSTRUCTION_AUTHORITY = object()
_ADMISSION_UNDO_CONSTRUCTION_AUTHORITY = object()


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


def _key(value: bytes | str, label: str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4096:
        raise ValueError(f"{label} key boundary changed")
    return hashlib.sha256(label.encode("utf-8") + b"\0" + raw).digest()


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


def _root_identity(
    value: FullFieldSensoryRoot,
) -> tuple[str, int, str, str]:
    return (
        value.sense,
        value.topology_index,
        value.physical_value_sha256,
        value.full_evidence_json,
    )


def _unique_roots(
    values: tuple[FullFieldSensoryRoot, ...],
) -> tuple[FullFieldSensoryRoot, ...]:
    retained: dict[
        tuple[str, int, str, str], FullFieldSensoryRoot
    ] = {}
    for value in values:
        value.verify()
        retained[_root_identity(value)] = value
    return tuple(retained[key] for key in sorted(retained))


def _root_from_record(value: object) -> FullFieldSensoryRoot:
    if not isinstance(value, Mapping) or set(value) != {
        "full_evidence_json",
        "physical_value_sha256",
        "schema",
        "sense",
        "topology_index",
    }:
        raise ValueError("sensory expansion root record changed")
    if value.get("schema") != (
        "guala.causal_thing_mosaic.full_field_root.v2"
    ):
        raise ValueError("sensory expansion root schema changed")
    result = FullFieldSensoryRoot(
        sense=value["sense"],
        topology_index=value["topology_index"],
        physical_value_sha256=value["physical_value_sha256"],
        full_evidence_json=value["full_evidence_json"],
    )
    result.verify()
    return result


@dataclass(frozen=True, slots=True)
class RetainedAudiovisualCustody:
    source_occurrence_id: str
    settlement: CausalExperienceSettlement
    frame_sha256s: tuple[str, ...]
    canonical_audio_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "canonical_audio_sha256": self.canonical_audio_sha256,
            "frame_sha256s": list(self.frame_sha256s),
            "schema": OCCURRENCE_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement.authority_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement.structural_fingerprint
            ),
            "source_occurrence_id": self.source_occurrence_id,
        }


@dataclass(frozen=True, slots=True)
class RetainedAudiovisualCustodyCapability:
    consumer_id: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "consumer_id": self.consumer_id,
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "schema": CAPABILITY_SCHEMA,
            "source_occurrence_id": self.source_occurrence_id,
        }


_RETAINED_AUDIOVISUAL_LIVE_SNAPSHOT_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class RetainedAudiovisualLiveSnapshot:
    """Owner-issued exact live-custody state for an enclosing transaction."""

    _custodies: tuple[RetainedAudiovisualCustody, ...] = field(
        repr=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class RetainedAudiovisualCustodyAuthority:
    """Issue one bounded capability over exact settled media evidence."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_live_occurrences: int,
        max_frames_per_occurrence: int,
    ) -> None:
        root = _key(authority_key, "retained audiovisual custody")
        self._custody_key = hashlib.sha256(
            _OCCURRENCE_DOMAIN + root
        ).digest()
        self._capability_key = hashlib.sha256(
            _CAPABILITY_DOMAIN + root
        ).digest()
        self._max_live = _positive(
            max_live_occurrences,
            "retained audiovisual live custody capacity",
        )
        self._max_frames = _positive(
            max_frames_per_occurrence,
            "retained audiovisual frame capacity",
        )
        self._custodies: dict[str, RetainedAudiovisualCustody] = {}
        self._order: list[str] = []
        self._live_snapshot_authority = object()
        self._lock = threading.RLock()

    def snapshot_live_custodies(
        self,
    ) -> RetainedAudiovisualLiveSnapshot:
        """Freeze the bounded live occurrence order for atomic rollback."""

        with self._lock:
            if (
                len(self._order) != len(self._custodies)
                or set(self._order) != set(self._custodies)
            ):
                raise RuntimeError(
                    "retained audiovisual custody order changed"
                )
            return RetainedAudiovisualLiveSnapshot(
                _custodies=tuple(
                    self._custodies[occurrence]
                    for occurrence in self._order
                ),
                _owner_authority=self._live_snapshot_authority,
                _construction_authority=(
                    _RETAINED_AUDIOVISUAL_LIVE_SNAPSHOT_AUTHORITY
                ),
            )

    def restore_live_custodies(
        self,
        snapshot: RetainedAudiovisualLiveSnapshot,
    ) -> None:
        """Restore the exact live bounded set after an enclosing failure."""

        if (
            not isinstance(snapshot, RetainedAudiovisualLiveSnapshot)
            or snapshot._construction_authority
            is not _RETAINED_AUDIOVISUAL_LIVE_SNAPSHOT_AUTHORITY
            or snapshot._owner_authority
            is not self._live_snapshot_authority
            or len(snapshot._custodies) > self._max_live
            or len({
                value.source_occurrence_id
                for value in snapshot._custodies
                if isinstance(value, RetainedAudiovisualCustody)
            }) != len(snapshot._custodies)
        ):
            raise ValueError(
                "retained audiovisual rollback snapshot changed"
            )
        with self._lock:
            self._custodies = {
                value.source_occurrence_id: value
                for value in snapshot._custodies
            }
            self._order = [
                value.source_occurrence_id
                for value in snapshot._custodies
            ]
        if self.snapshot_live_custodies() != snapshot:
            raise RuntimeError(
                "retained audiovisual rollback changed prior custody"
            )

    def verify_custody(self, value: RetainedAudiovisualCustody) -> None:
        if not isinstance(value, RetainedAudiovisualCustody):
            raise TypeError("retained audiovisual custody is not typed")
        value.settlement.verify()
        for digest, label in (
            (value.source_occurrence_id, "audiovisual occurrence"),
            (value.authority_hmac_sha256, "audiovisual custody HMAC"),
            (value.authority_receipt_sha256, "audiovisual custody authority"),
        ):
            _sha(digest, label)
        if (
            not value.frame_sha256s
            or len(value.frame_sha256s) > self._max_frames
        ):
            raise ValueError("audiovisual custody frame extent changed")
        for digest in value.frame_sha256s:
            _sha(digest, "audiovisual frame")
        if value.canonical_audio_sha256 is not None:
            _sha(value.canonical_audio_sha256, "audiovisual audio")
        roots = full_field_sensory_roots(value.settlement)
        senses = {root.sense for root in roots}
        if "sight" not in senses or (
            value.canonical_audio_sha256 is not None
            and "sound" not in senses
        ):
            raise ValueError(
                "audiovisual custody differs from its physical senses"
            )
        signature = hmac.new(
            self._custody_key,
            _OCCURRENCE_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("audiovisual custody authority changed")

    def admit(
        self,
        *,
        settlement: CausalExperienceSettlement,
        frame_sha256s: tuple[str, ...],
        canonical_audio_sha256: str | None,
    ) -> RetainedAudiovisualCustody:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "retained audiovisual custody requires a causal settlement"
            )
        settlement.verify()
        if (
            not isinstance(frame_sha256s, tuple)
            or not frame_sha256s
            or len(frame_sha256s) > self._max_frames
        ):
            raise ValueError(
                "retained audiovisual custody requires bounded frames"
            )
        for digest in frame_sha256s:
            _sha(digest, "audiovisual frame")
        if canonical_audio_sha256 is not None:
            _sha(canonical_audio_sha256, "audiovisual audio")
        occurrence = _digest({
            "canonical_audio_sha256": canonical_audio_sha256,
            "frame_sha256s": list(frame_sha256s),
            "schema": "guala.retained_audiovisual.occurrence_identity.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
        })
        provisional = RetainedAudiovisualCustody(
            source_occurrence_id=occurrence,
            settlement=settlement,
            frame_sha256s=frame_sha256s,
            canonical_audio_sha256=canonical_audio_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._custody_key,
            _OCCURRENCE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        custody = RetainedAudiovisualCustody(
            source_occurrence_id=provisional.source_occurrence_id,
            settlement=settlement,
            frame_sha256s=frame_sha256s,
            canonical_audio_sha256=canonical_audio_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_custody(custody)
        with self._lock:
            existing = self._custodies.get(occurrence)
            if existing is not None:
                if existing != custody:
                    raise ValueError(
                        "audiovisual occurrence crossed physical custody"
                    )
                return existing
            self._custodies[occurrence] = custody
            self._order.append(occurrence)
            while len(self._order) > self._max_live:
                expired = self._order.pop(0)
                self._custodies.pop(expired, None)
        return custody

    def issue_child(
        self,
        custody: RetainedAudiovisualCustody,
        consumer_id: str,
    ) -> RetainedAudiovisualCustodyCapability:
        self.verify_custody(custody)
        if (
            not isinstance(consumer_id, str)
            or consumer_id not in _RETAINED_CUSTODY_CONSUMER_IDS
        ):
            raise ValueError(
                "audiovisual custody consumer is not authorized"
            )
        provisional = RetainedAudiovisualCustodyCapability(
            consumer_id=consumer_id,
            source_occurrence_id=custody.source_occurrence_id,
            parent_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._capability_key,
            _CAPABILITY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return RetainedAudiovisualCustodyCapability(
            consumer_id=consumer_id,
            source_occurrence_id=custody.source_occurrence_id,
            parent_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def open_child(
        self,
        capability: RetainedAudiovisualCustodyCapability,
    ) -> RetainedAudiovisualCustody:
        if not isinstance(
            capability,
            RetainedAudiovisualCustodyCapability,
        ):
            raise TypeError("audiovisual custody capability is not typed")
        if capability.consumer_id not in _RETAINED_CUSTODY_CONSUMER_IDS:
            raise ValueError("audiovisual custody consumer changed")
        for digest, label in (
            (capability.source_occurrence_id, "audiovisual occurrence"),
            (
                capability.parent_custody_receipt_sha256,
                "audiovisual parent custody",
            ),
            (
                capability.authority_hmac_sha256,
                "audiovisual capability HMAC",
            ),
            (
                capability.authority_receipt_sha256,
                "audiovisual capability authority",
            ),
        ):
            _sha(digest, label)
        signature = hmac.new(
            self._capability_key,
            _CAPABILITY_DOMAIN + _canonical(capability.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                capability.authority_hmac_sha256,
            )
            or capability.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": capability.payload(),
            })
        ):
            raise ValueError("audiovisual custody capability changed")
        with self._lock:
            custody = self._custodies.get(capability.source_occurrence_id)
        if (
            custody is None
            or custody.authority_receipt_sha256
            != capability.parent_custody_receipt_sha256
        ):
            raise ValueError(
                "audiovisual custody capability has no live parent"
            )
        self.verify_custody(custody)
        return custody


@dataclass(frozen=True, slots=True)
class CausalThingSensoryExpansion:
    sequence: int
    thing_id: str
    admission_basis: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    custody_capability_receipt_sha256: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    world_revision: int | None
    world_observation_receipt_sha256: str | None
    world_before_receipt_sha256: str | None
    world_execution_receipt_sha256: str | None
    grounding_partition_receipt_sha256: str | None
    grounding_contact_occurrence_id: str | None
    grounding_contact_custody_receipt_sha256: str | None
    grounding_contact_capability_receipt_sha256: str | None
    grounding_contact_settlement_receipt_sha256: str | None
    prior_expansion_receipt_sha256s: tuple[str, ...]
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "admission_basis": self.admission_basis,
            "custody_capability_receipt_sha256": (
                self.custody_capability_receipt_sha256
            ),
            "full_field_roots": [
                root.record() for root in self.full_field_roots
            ],
            "grounding_partition_receipt_sha256": (
                self.grounding_partition_receipt_sha256
            ),
            "grounding_contact_occurrence_id": (
                self.grounding_contact_occurrence_id
            ),
            "grounding_contact_custody_receipt_sha256": (
                self.grounding_contact_custody_receipt_sha256
            ),
            "grounding_contact_capability_receipt_sha256": (
                self.grounding_contact_capability_receipt_sha256
            ),
            "grounding_contact_settlement_receipt_sha256": (
                self.grounding_contact_settlement_receipt_sha256
            ),
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "prior_expansion_receipt_sha256s": list(
                self.prior_expansion_receipt_sha256s
            ),
            "schema": EXPANSION_SCHEMA,
            "sequence": self.sequence,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "thing_id": self.thing_id,
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalThingSensoryExpansionAdmission:
    state: str
    thing_ids: tuple[str, ...]
    expansion: CausalThingSensoryExpansion | None


@dataclass(slots=True)
class _ExpansionAdmissionTransactionState:
    phase: str


@dataclass(frozen=True, slots=True)
class PreparedCausalThingSensoryExpansionAdmission:
    admission: CausalThingSensoryExpansionAdmission
    _custody_authority: RetainedAudiovisualCustodyAuthority = field(
        repr=False,
        compare=False,
    )
    _custody_capability: RetainedAudiovisualCustodyCapability = field(
        repr=False,
        compare=False,
    )
    _prior_expansions: tuple[CausalThingSensoryExpansion, ...] = field(
        repr=False,
    )
    _staged_expansions: tuple[CausalThingSensoryExpansion, ...] = field(
        repr=False,
    )
    _transaction_state: _ExpansionAdmissionTransactionState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CausalThingSensoryExpansionAdmissionUndo:
    _prepared: PreparedCausalThingSensoryExpansionAdmission = field(
        repr=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class CausalThingSensoryExpansionOwner:
    """Extend only existing causal THING identities with lived sensory roots."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        thing_owner: CausalThingMosaicOwner,
        max_expansions: int,
        max_roots_per_expansion: int,
        max_state_bytes: int,
    ) -> None:
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "sensory expansion requires the causal THING owner"
            )
        root = _key(authority_key, "causal THING sensory expansion")
        self._expansion_key = hashlib.sha256(
            _EXPANSION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root
        ).digest()
        self._things = thing_owner
        self._max_expansions = _positive(
            max_expansions,
            "sensory expansion capacity",
        )
        self._max_roots = _positive(
            max_roots_per_expansion,
            "sensory expansion root capacity",
        )
        self._max_state_bytes = _positive(
            max_state_bytes,
            "sensory expansion state capacity",
        )
        self._expansions: tuple[CausalThingSensoryExpansion, ...] = ()
        self._admission_authority = object()
        self._lock = threading.RLock()

    @property
    def expansions(self) -> tuple[CausalThingSensoryExpansion, ...]:
        with self._lock:
            return self._expansions

    def roots_for_thing(
        self,
        thing_id: str,
    ) -> tuple[FullFieldSensoryRoot, ...]:
        _sha(thing_id, "sensory expansion THING")
        with self._lock:
            return _unique_roots(tuple(
                root
                for expansion in self._expansions
                if expansion.thing_id == thing_id
                for root in expansion.full_field_roots
            ))

    def receipts_for_thing(self, thing_id: str) -> tuple[str, ...]:
        _sha(thing_id, "sensory expansion THING")
        with self._lock:
            return tuple(
                expansion.authority_receipt_sha256
                for expansion in self._expansions
                if expansion.thing_id == thing_id
            )

    def _owned_thing(self, thing_id: str):
        matches = tuple(
            mosaic
            for mosaic in self._things.mosaics
            if mosaic.thing_id == thing_id
        )
        if len(matches) != 1:
            raise ValueError(
                "sensory expansion does not name one owned causal THING"
            )
        return matches[0]

    def _verify_expansion(
        self,
        value: CausalThingSensoryExpansion,
    ) -> None:
        if not isinstance(value, CausalThingSensoryExpansion):
            raise TypeError("sensory expansion is not typed")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence <= 0
            or value.admission_basis not in {
                "lived_contact_tutor",
                "known_sight_continuation",
                "settled_known_sight_continuation",
            }
            or not value.full_field_roots
            or len(value.full_field_roots) > self._max_roots
        ):
            raise ValueError("sensory expansion extent changed")
        for digest, label in (
            (value.thing_id, "sensory expansion THING"),
            (value.source_occurrence_id, "sensory expansion occurrence"),
            (
                value.parent_custody_receipt_sha256,
                "sensory expansion parent custody",
            ),
            (
                value.custody_capability_receipt_sha256,
                "sensory expansion custody capability",
            ),
            (value.settlement_receipt_sha256, "sensory expansion settlement"),
            (
                value.settlement_structural_fingerprint,
                "sensory expansion structure",
            ),
            (value.authority_hmac_sha256, "sensory expansion HMAC"),
            (value.authority_receipt_sha256, "sensory expansion authority"),
        ):
            _sha(digest, label)
        for digest in value.prior_expansion_receipt_sha256s:
            _sha(digest, "prior sensory expansion")
        for digest, label in (
            (
                value.world_observation_receipt_sha256,
                "sensory expansion world observation",
            ),
            (
                value.world_before_receipt_sha256,
                "sensory expansion world before",
            ),
            (
                value.world_execution_receipt_sha256,
                "sensory expansion world execution",
            ),
        ):
            if digest is not None:
                _sha(digest, label)
        if value.admission_basis == "lived_contact_tutor":
            _sha(
                value.grounding_partition_receipt_sha256,
                "sensory expansion grounding partition",
            )
            if value.prior_expansion_receipt_sha256s:
                raise ValueError(
                    "grounded sensory expansion gained prior sight authority"
                )
            for digest, label in (
                (
                    value.grounding_contact_occurrence_id,
                    "sensory expansion grounding occurrence",
                ),
                (
                    value.grounding_contact_custody_receipt_sha256,
                    "sensory expansion grounding custody",
                ),
                (
                    value.grounding_contact_capability_receipt_sha256,
                    "sensory expansion grounding capability",
                ),
                (
                    value.grounding_contact_settlement_receipt_sha256,
                    "sensory expansion grounding settlement",
                ),
            ):
                _sha(digest, label)
        elif value.admission_basis == "known_sight_continuation" and (
            value.grounding_partition_receipt_sha256 is not None
            or not value.prior_expansion_receipt_sha256s
            or value.grounding_contact_occurrence_id is not None
            or value.grounding_contact_custody_receipt_sha256 is not None
            or value.grounding_contact_capability_receipt_sha256 is not None
            or value.grounding_contact_settlement_receipt_sha256 is not None
        ):
            raise ValueError(
                "known-sight sensory expansion lost prior sight authority"
            )
        elif value.admission_basis == (
            "settled_known_sight_continuation"
        ) and (
            value.grounding_partition_receipt_sha256 is not None
            or not value.prior_expansion_receipt_sha256s
            or value.grounding_contact_occurrence_id is not None
            or value.grounding_contact_custody_receipt_sha256 is not None
            or value.grounding_contact_capability_receipt_sha256 is not None
            or value.grounding_contact_settlement_receipt_sha256 is not None
            or isinstance(value.world_revision, bool)
            or not isinstance(value.world_revision, int)
            or value.world_revision < 0
            or value.world_observation_receipt_sha256 is None
            or value.world_before_receipt_sha256 is None
            or value.world_execution_receipt_sha256 is None
        ):
            raise ValueError(
                "settled known-sight expansion lost W1 provenance"
            )
        if (
            value.admission_basis
            != "settled_known_sight_continuation"
            and (
                value.world_revision is not None
                or value.world_observation_receipt_sha256 is not None
                or value.world_before_receipt_sha256 is not None
                or value.world_execution_receipt_sha256 is not None
            )
        ):
            raise ValueError(
                "retained sensory expansion invented W1 provenance"
            )
        senses = {root.sense for root in value.full_field_roots}
        if "sight" not in senses or not senses.issubset({"sight", "sound"}):
            raise ValueError(
                "sensory expansion contains non-audiovisual roots"
            )
        for root in value.full_field_roots:
            root.verify()
        signature = hmac.new(
            self._expansion_key,
            _EXPANSION_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("sensory expansion authority changed")

    def _seal(
        self,
        *,
        thing_id: str,
        admission_basis: str,
        custody: RetainedAudiovisualCustody,
        capability: RetainedAudiovisualCustodyCapability,
        grounding_partition_receipt_sha256: str | None,
        grounding_contact_occurrence_id: str | None,
        grounding_contact_custody_receipt_sha256: str | None,
        grounding_contact_capability_receipt_sha256: str | None,
        grounding_contact_settlement_receipt_sha256: str | None,
        prior_expansion_receipt_sha256s: tuple[str, ...],
    ) -> CausalThingSensoryExpansion:
        roots = tuple(
            root
            for root in full_field_sensory_roots(custody.settlement)
            if root.sense in {"sight", "sound"}
        )
        if not roots or len(roots) > self._max_roots:
            raise RuntimeError(
                "sensory expansion root capacity exhausted"
            )
        provisional = CausalThingSensoryExpansion(
            sequence=len(self._expansions) + 1,
            thing_id=thing_id,
            admission_basis=admission_basis,
            source_occurrence_id=custody.source_occurrence_id,
            parent_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            custody_capability_receipt_sha256=(
                capability.authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                custody.settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                custody.settlement.structural_fingerprint
            ),
            world_revision=None,
            world_observation_receipt_sha256=None,
            world_before_receipt_sha256=None,
            world_execution_receipt_sha256=None,
            grounding_partition_receipt_sha256=(
                grounding_partition_receipt_sha256
            ),
            grounding_contact_occurrence_id=(
                grounding_contact_occurrence_id
            ),
            grounding_contact_custody_receipt_sha256=(
                grounding_contact_custody_receipt_sha256
            ),
            grounding_contact_capability_receipt_sha256=(
                grounding_contact_capability_receipt_sha256
            ),
            grounding_contact_settlement_receipt_sha256=(
                grounding_contact_settlement_receipt_sha256
            ),
            prior_expansion_receipt_sha256s=(
                prior_expansion_receipt_sha256s
            ),
            full_field_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._expansion_key,
            _EXPANSION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = CausalThingSensoryExpansion(
            **{
                field: getattr(provisional, field)
                for field in (
                    "sequence",
                    "thing_id",
                    "admission_basis",
                    "source_occurrence_id",
                    "parent_custody_receipt_sha256",
                    "custody_capability_receipt_sha256",
                    "settlement_receipt_sha256",
                    "settlement_structural_fingerprint",
                    "world_revision",
                    "world_observation_receipt_sha256",
                    "world_before_receipt_sha256",
                    "world_execution_receipt_sha256",
                    "grounding_partition_receipt_sha256",
                    "grounding_contact_occurrence_id",
                    "grounding_contact_custody_receipt_sha256",
                    "grounding_contact_capability_receipt_sha256",
                    "grounding_contact_settlement_receipt_sha256",
                    "prior_expansion_receipt_sha256s",
                    "full_field_roots",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_expansion(result)
        return result

    def _admit(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
        thing_id: str,
        admission_basis: str,
        grounding_partition_receipt_sha256: str | None,
        grounding_contact_occurrence_id: str | None,
        grounding_contact_custody_receipt_sha256: str | None,
        grounding_contact_capability_receipt_sha256: str | None,
        grounding_contact_settlement_receipt_sha256: str | None,
        prior_expansion_receipt_sha256s: tuple[str, ...],
    ) -> CausalThingSensoryExpansion:
        if not isinstance(
            custody_authority,
            RetainedAudiovisualCustodyAuthority,
        ):
            raise TypeError(
                "sensory expansion requires audiovisual custody"
            )
        if (
            not isinstance(
                custody_capability,
                RetainedAudiovisualCustodyCapability,
            )
            or custody_capability.consumer_id
            != THING_SENSORY_EXPANSION_CONSUMER_ID
        ):
            raise ValueError(
                "sensory expansion requires its dedicated capability"
            )
        custody = custody_authority.open_child(custody_capability)
        self._owned_thing(thing_id)
        with self._lock:
            existing = next(
                (
                    expansion
                    for expansion in self._expansions
                    if expansion.source_occurrence_id
                    == custody.source_occurrence_id
                ),
                None,
            )
            if existing is not None:
                if existing.thing_id != thing_id:
                    raise ValueError(
                        "one audiovisual occurrence crossed THING identity"
                    )
                return existing
            if len(self._expansions) >= self._max_expansions:
                raise RuntimeError("sensory expansion capacity exhausted")
            result = self._seal(
                thing_id=thing_id,
                admission_basis=admission_basis,
                custody=custody,
                capability=custody_capability,
                grounding_partition_receipt_sha256=(
                    grounding_partition_receipt_sha256
                ),
                grounding_contact_occurrence_id=(
                    grounding_contact_occurrence_id
                ),
                grounding_contact_custody_receipt_sha256=(
                    grounding_contact_custody_receipt_sha256
                ),
                grounding_contact_capability_receipt_sha256=(
                    grounding_contact_capability_receipt_sha256
                ),
                grounding_contact_settlement_receipt_sha256=(
                    grounding_contact_settlement_receipt_sha256
                ),
                prior_expansion_receipt_sha256s=(
                    prior_expansion_receipt_sha256s
                ),
            )
            staged = self._expansions + (result,)
            self._encoded(staged)
            self._expansions = staged
            return result

    def admit_lived_contact_tutor(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
        contact_custody_authority: SettledExperienceCustodyAuthority,
        contact_custody_capability: SettledExperienceConsumerCapability,
    ) -> CausalThingSensoryExpansion:
        if not isinstance(
            contact_custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "sensory tutor requires settled contact custody"
            )
        if (
            not isinstance(
                contact_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or contact_custody_capability.consumer_id
            != THING_SENSORY_GROUNDING_CONSUMER_ID
        ):
            raise ValueError(
                "sensory tutor requires its contact custody capability"
            )
        contact = contact_custody_authority.open_child(
            contact_custody_capability
        )
        observed = {
            value.sense
            for value in contact.causal_settlement.interpretations
            if value.state == "observed"
        }
        held = tuple(
            value
            for value in contact.world_observation.objects
            if value.held_by_body_id
            == contact.world_observation.self_body_id
        )
        if "touch" not in observed or len(held) != 1:
            raise ValueError(
                "sensory tutor lacks one simultaneous held contact"
            )
        route = self._things.route(contact.causal_settlement)
        if route.state != "unique" or len(route.thing_ids) != 1:
            raise ValueError(
                "sensory tutor contact does not resolve one causal THING"
            )
        thing_id = route.thing_ids[0]
        mosaic = self._owned_thing(thing_id)
        contact_touch_keys = {
            root.route_key
            for root in full_field_sensory_roots(
                contact.causal_settlement
            )
            if root.sense == "touch"
        }
        matches = tuple(
            partition
            for partition in mosaic.partitions
            if any(
                root.route_key in contact_touch_keys
                for root in partition.full_field_roots
                if root.sense == "touch"
            )
        )
        if not matches:
            raise ValueError(
                "sensory tutor has no contact-grounded THING partition"
            )
        grounding_partition_receipt_sha256 = (
            matches[-1].authority_receipt_sha256
        )
        return self._admit(
            custody_authority=custody_authority,
            custody_capability=custody_capability,
            thing_id=thing_id,
            admission_basis="lived_contact_tutor",
            grounding_partition_receipt_sha256=(
                grounding_partition_receipt_sha256
            ),
            grounding_contact_occurrence_id=(
                contact.source_occurrence_id
            ),
            grounding_contact_custody_receipt_sha256=(
                contact.parent_custody_receipt_sha256
            ),
            grounding_contact_capability_receipt_sha256=(
                contact_custody_capability.authority_receipt_sha256
            ),
            grounding_contact_settlement_receipt_sha256=(
                contact.causal_settlement.authority_receipt_sha256
            ),
            prior_expansion_receipt_sha256s=(),
        )

    def admit_settled_known_sight(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> CausalThingSensoryExpansionAdmission:
        """Attach original W1 custody through one exact known-sight route."""

        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "settled known-sight admission requires settled custody"
            )
        if (
            not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != THING_SENSORY_EXPANSION_CONSUMER_ID
        ):
            raise ValueError(
                "settled known-sight admission requires its dedicated "
                "capability"
            )
        custody = custody_authority.open_child(custody_capability)
        execution = custody.world_execution
        if (
            execution is None
            or custody.world_observation != execution.after
            or custody.parent_custody_receipt_sha256
            != custody_capability.parent_custody_receipt_sha256
            or custody.source_occurrence_id
            != custody_capability.source_occurrence_id
        ):
            raise ValueError(
                "settled known-sight admission lost original W1 lineage"
            )
        roots = tuple(
            root
            for root in full_field_sensory_roots(
                custody.causal_settlement
            )
            if root.sense in {"sight", "sound"}
        )
        senses = {root.sense for root in roots}
        if senses != {"sight", "sound"}:
            raise ValueError(
                "settled known-sight admission requires sight and sound"
            )
        if len(roots) > self._max_roots:
            raise RuntimeError(
                "sensory expansion root capacity exhausted"
            )
        sight_keys = tuple(sorted(
            root.route_key for root in roots if root.sense == "sight"
        ))
        with self._lock:
            existing = next(
                (
                    expansion
                    for expansion in self._expansions
                    if expansion.source_occurrence_id
                    == custody.source_occurrence_id
                ),
                None,
            )
            if existing is not None:
                self._verify_expansion(existing)
                if (
                    existing.admission_basis
                    != "settled_known_sight_continuation"
                    or existing.parent_custody_receipt_sha256
                    != custody.parent_custody_receipt_sha256
                    or existing.custody_capability_receipt_sha256
                    != custody_capability.authority_receipt_sha256
                    or existing.settlement_receipt_sha256
                    != custody.causal_settlement
                    .authority_receipt_sha256
                    or existing.settlement_structural_fingerprint
                    != custody.causal_settlement
                    .structural_fingerprint
                    or existing.world_revision
                    != custody.world_observation.revision
                    or existing.world_observation_receipt_sha256
                    != custody.world_observation
                    .authority_receipt_sha256
                    or existing.world_before_receipt_sha256
                    != execution.before.authority_receipt_sha256
                    or existing.world_execution_receipt_sha256
                    != execution.authority_receipt_sha256
                    or existing.full_field_roots != roots
                ):
                    raise ValueError(
                        "settled known-sight replay crossed custody"
                    )
                return CausalThingSensoryExpansionAdmission(
                    state="unique",
                    thing_ids=(existing.thing_id,),
                    expansion=existing,
                )
            matches = tuple(
                expansion
                for expansion in self._expansions
                if tuple(sorted(
                    root.route_key
                    for root in expansion.full_field_roots
                    if root.sense == "sight"
                )) == sight_keys
            )
            thing_ids = tuple(sorted({
                expansion.thing_id for expansion in matches
            }))
            if len(thing_ids) != 1:
                return CausalThingSensoryExpansionAdmission(
                    state=(
                        "ambiguous" if thing_ids else "unresolved"
                    ),
                    thing_ids=thing_ids,
                    expansion=None,
                )
            if len(self._expansions) >= self._max_expansions:
                raise RuntimeError(
                    "sensory expansion capacity exhausted"
                )
            thing_id = thing_ids[0]
            self._owned_thing(thing_id)
            provisional = CausalThingSensoryExpansion(
                sequence=len(self._expansions) + 1,
                thing_id=thing_id,
                admission_basis=(
                    "settled_known_sight_continuation"
                ),
                source_occurrence_id=custody.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    custody.parent_custody_receipt_sha256
                ),
                custody_capability_receipt_sha256=(
                    custody_capability.authority_receipt_sha256
                ),
                settlement_receipt_sha256=(
                    custody.causal_settlement
                    .authority_receipt_sha256
                ),
                settlement_structural_fingerprint=(
                    custody.causal_settlement.structural_fingerprint
                ),
                world_revision=custody.world_observation.revision,
                world_observation_receipt_sha256=(
                    custody.world_observation
                    .authority_receipt_sha256
                ),
                world_before_receipt_sha256=(
                    execution.before.authority_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    execution.authority_receipt_sha256
                ),
                grounding_partition_receipt_sha256=None,
                grounding_contact_occurrence_id=None,
                grounding_contact_custody_receipt_sha256=None,
                grounding_contact_capability_receipt_sha256=None,
                grounding_contact_settlement_receipt_sha256=None,
                prior_expansion_receipt_sha256s=tuple(
                    expansion.authority_receipt_sha256
                    for expansion in matches
                    if expansion.thing_id == thing_id
                ),
                full_field_roots=roots,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._expansion_key,
                _EXPANSION_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            expansion = CausalThingSensoryExpansion(
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
            self._verify_expansion(expansion)
            staged = self._expansions + (expansion,)
            self._encoded(staged)
            self._expansions = staged
            return CausalThingSensoryExpansionAdmission(
                state="unique",
                thing_ids=(thing_id,),
                expansion=expansion,
            )

    def _stage_known_sight_admission_locked(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> (
        CausalThingSensoryExpansionAdmission
        | tuple[
            tuple[CausalThingSensoryExpansion, ...],
            tuple[CausalThingSensoryExpansion, ...],
            CausalThingSensoryExpansionAdmission,
        ]
    ):
        if not isinstance(
            custody_authority,
            RetainedAudiovisualCustodyAuthority,
        ):
            raise TypeError(
                "known-sight admission requires audiovisual custody"
            )
        if (
            not isinstance(
                custody_capability,
                RetainedAudiovisualCustodyCapability,
            )
            or custody_capability.consumer_id
            != THING_SENSORY_EXPANSION_CONSUMER_ID
        ):
            raise ValueError(
                "known-sight admission requires its sensory-expansion "
                "capability"
            )
        custody = custody_authority.open_child(custody_capability)
        sight_keys = tuple(sorted(
            root.route_key
            for root in full_field_sensory_roots(custody.settlement)
            if root.sense == "sight"
        ))
        if not sight_keys:
            raise ValueError("known-sight admission has no sight field")
        existing = next(
            (
                expansion
                for expansion in self._expansions
                if expansion.source_occurrence_id
                == custody.source_occurrence_id
            ),
            None,
        )
        if existing is not None:
            self._verify_expansion(existing)
            self._owned_thing(existing.thing_id)
            exact_roots = tuple(
                root
                for root in full_field_sensory_roots(
                    custody.settlement
                )
                if root.sense in {"sight", "sound"}
            )
            if (
                existing.parent_custody_receipt_sha256
                != custody.authority_receipt_sha256
                or existing.custody_capability_receipt_sha256
                != custody_capability.authority_receipt_sha256
                or existing.settlement_receipt_sha256
                != custody.settlement.authority_receipt_sha256
                or existing.settlement_structural_fingerprint
                != custody.settlement.structural_fingerprint
                or existing.full_field_roots != exact_roots
            ):
                raise ValueError(
                    "known-sight replay crossed retained custody"
                )
            return CausalThingSensoryExpansionAdmission(
                state="unique",
                thing_ids=(existing.thing_id,),
                expansion=existing,
            )
        matches = tuple(
            expansion
            for expansion in self._expansions
            if tuple(sorted(
                root.route_key
                for root in expansion.full_field_roots
                if root.sense == "sight"
            )) == sight_keys
        )
        thing_ids = tuple(sorted({
            expansion.thing_id for expansion in matches
        }))
        if len(thing_ids) != 1:
            return CausalThingSensoryExpansionAdmission(
                state="ambiguous" if thing_ids else "unresolved",
                thing_ids=thing_ids,
                expansion=None,
            )
        thing_id = thing_ids[0]
        self._owned_thing(thing_id)
        if len(self._expansions) >= self._max_expansions:
            raise RuntimeError("sensory expansion capacity exhausted")
        result = self._seal(
            thing_id=thing_id,
            admission_basis="known_sight_continuation",
            custody=custody,
            capability=custody_capability,
            grounding_partition_receipt_sha256=None,
            grounding_contact_occurrence_id=None,
            grounding_contact_custody_receipt_sha256=None,
            grounding_contact_capability_receipt_sha256=None,
            grounding_contact_settlement_receipt_sha256=None,
            prior_expansion_receipt_sha256s=tuple(
                expansion.authority_receipt_sha256
                for expansion in matches
                if expansion.thing_id == thing_id
            ),
        )
        prior = self._expansions
        staged = prior + (result,)
        self._encoded(staged)
        admission = CausalThingSensoryExpansionAdmission(
            state="unique",
            thing_ids=(thing_id,),
            expansion=result,
        )
        return prior, staged, admission

    def prepare_known_sight_admission(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> (
        PreparedCausalThingSensoryExpansionAdmission
        | CausalThingSensoryExpansionAdmission
    ):
        """Preflight one live known-sight occurrence without publication."""

        with self._lock:
            staged = self._stage_known_sight_admission_locked(
                custody_authority=custody_authority,
                custody_capability=custody_capability,
            )
            if isinstance(
                staged,
                CausalThingSensoryExpansionAdmission,
            ):
                return staged
            prior, candidate, admission = staged
            return PreparedCausalThingSensoryExpansionAdmission(
                admission=admission,
                _custody_authority=custody_authority,
                _custody_capability=custody_capability,
                _prior_expansions=prior,
                _staged_expansions=candidate,
                _transaction_state=(
                    _ExpansionAdmissionTransactionState(
                        phase="prepared"
                    )
                ),
                _owner_authority=self._admission_authority,
                _construction_authority=(
                    _PREPARED_ADMISSION_CONSTRUCTION_AUTHORITY
                ),
            )

    def _verify_prepared_admission_locked(
        self,
        prepared: PreparedCausalThingSensoryExpansionAdmission,
        *,
        require_current: bool,
        require_live_custody: bool = True,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedCausalThingSensoryExpansionAdmission,
            )
            or prepared._construction_authority
            is not _PREPARED_ADMISSION_CONSTRUCTION_AUTHORITY
            or prepared._owner_authority
            is not self._admission_authority
            or prepared._transaction_state.phase != "prepared"
        ):
            raise ValueError(
                "prepared sensory expansion admission changed custody"
            )
        admission = prepared.admission
        expansion = admission.expansion
        if (
            admission.state != "unique"
            or len(admission.thing_ids) != 1
            or expansion is None
            or admission.thing_ids != (expansion.thing_id,)
            or prepared._staged_expansions
            != prepared._prior_expansions + (expansion,)
        ):
            raise ValueError(
                "prepared sensory expansion admission changed state"
        )
        self._verify_expansion(expansion)
        self._owned_thing(expansion.thing_id)
        if require_live_custody:
            custody = prepared._custody_authority.open_child(
                prepared._custody_capability
            )
            exact_roots = tuple(
                root
                for root in full_field_sensory_roots(
                    custody.settlement
                )
                if root.sense in {"sight", "sound"}
            )
            if (
                expansion.source_occurrence_id
                != custody.source_occurrence_id
                or expansion.parent_custody_receipt_sha256
                != custody.authority_receipt_sha256
                or expansion.custody_capability_receipt_sha256
                != prepared._custody_capability.authority_receipt_sha256
                or expansion.settlement_receipt_sha256
                != custody.settlement.authority_receipt_sha256
                or expansion.settlement_structural_fingerprint
                != custody.settlement.structural_fingerprint
                or expansion.full_field_roots != exact_roots
            ):
                raise ValueError(
                    "prepared sensory expansion admission changed evidence"
                )
        self._encoded(prepared._prior_expansions)
        self._encoded(prepared._staged_expansions)
        if require_current:
            if self._expansions != prepared._prior_expansions:
                raise RuntimeError(
                    "prepared sensory expansion admission is stale"
                )
            expected = self._stage_known_sight_admission_locked(
                custody_authority=prepared._custody_authority,
                custody_capability=prepared._custody_capability,
            )
            if (
                isinstance(
                    expected,
                    CausalThingSensoryExpansionAdmission,
                )
                or expected
                != (
                    prepared._prior_expansions,
                    prepared._staged_expansions,
                    admission,
                )
            ):
                raise ValueError(
                    "prepared sensory expansion admission changed staging"
                )

    def verify_prepared_admission(
        self,
        prepared: PreparedCausalThingSensoryExpansionAdmission,
    ) -> None:
        with self._lock:
            self._verify_prepared_admission_locked(
                prepared,
                require_current=True,
            )

    def commit_prepared_admission(
        self,
        prepared: PreparedCausalThingSensoryExpansionAdmission,
    ) -> CausalThingSensoryExpansionAdmissionUndo:
        """Publish one preflighted expansion exactly once."""

        with self._lock:
            self._verify_prepared_admission_locked(
                prepared,
                require_current=True,
            )
            self._expansions = prepared._staged_expansions
            prepared._transaction_state.phase = "committed"
            return CausalThingSensoryExpansionAdmissionUndo(
                _prepared=prepared,
                _owner_authority=self._admission_authority,
                _construction_authority=(
                    _ADMISSION_UNDO_CONSTRUCTION_AUTHORITY
                ),
            )

    def discard_prepared_admission(
        self,
        prepared: PreparedCausalThingSensoryExpansionAdmission,
    ) -> None:
        """Consume one uncommitted expansion capability."""

        with self._lock:
            self._verify_prepared_admission_locked(
                prepared,
                require_current=False,
                require_live_custody=False,
            )
            prepared._transaction_state.phase = "discarded"

    def rollback_committed_admission(
        self,
        undo: CausalThingSensoryExpansionAdmissionUndo,
    ) -> None:
        """Restore exact prior expansion bytes while this tail is current."""

        if (
            not isinstance(
                undo,
                CausalThingSensoryExpansionAdmissionUndo,
            )
            or undo._construction_authority
            is not _ADMISSION_UNDO_CONSTRUCTION_AUTHORITY
            or undo._owner_authority
            is not self._admission_authority
        ):
            raise ValueError(
                "sensory expansion admission undo changed custody"
            )
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority
                is not self._admission_authority
                or prepared._transaction_state.phase != "committed"
            ):
                raise ValueError(
                    "sensory expansion admission undo changed custody"
                )
            self._encoded(prepared._prior_expansions)
            self._encoded(prepared._staged_expansions)
            if self._expansions != prepared._staged_expansions:
                raise RuntimeError(
                    "sensory expansion admission undo is stale"
                )
            self._expansions = prepared._prior_expansions
            prepared._transaction_state.phase = "rolled_back"

    def admit_known_sight(
        self,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> CausalThingSensoryExpansionAdmission:
        """Preserve the historical atomic convenience API."""

        prepared = self.prepare_known_sight_admission(
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        if isinstance(
            prepared,
            CausalThingSensoryExpansionAdmission,
        ):
            return prepared
        self.commit_prepared_admission(prepared)
        return prepared.admission

    def _body(
        self,
        expansions: tuple[CausalThingSensoryExpansion, ...],
    ) -> dict[str, object]:
        return {
            "expansions": [value.record() for value in expansions],
            "limits": {
                "max_expansions": self._max_expansions,
                "max_roots_per_expansion": self._max_roots,
                "max_state_bytes": self._max_state_bytes,
            },
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        expansions: tuple[CausalThingSensoryExpansion, ...],
    ) -> bytes:
        body = self._body(expansions)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError(
                "sensory expansion state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._expansions)

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._max_state_bytes
        ):
            raise ValueError("sensory expansion restore extent changed")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "sensory expansion state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {
                "body",
                "schema",
                "state_hmac_sha256",
            }
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("sensory expansion envelope changed")
        body = envelope["body"]
        if (
            not isinstance(body, Mapping)
            or set(body) != {"expansions", "limits", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("limits") != {
                "max_expansions": self._max_expansions,
                "max_roots_per_expansion": self._max_roots,
                "max_state_bytes": self._max_state_bytes,
            }
            or not isinstance(body.get("expansions"), list)
            or len(body["expansions"]) > self._max_expansions
        ):
            raise ValueError("sensory expansion state body changed")
        expected_hmac = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac,
            envelope["state_hmac_sha256"],
        ):
            raise ValueError("sensory expansion state HMAC changed")
        restored = []
        for record in body["expansions"]:
            if not isinstance(record, Mapping):
                raise ValueError(
                    "sensory expansion record changed"
                )
            expected_keys = {
                "admission_basis",
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "custody_capability_receipt_sha256",
                "full_field_roots",
                "grounding_partition_receipt_sha256",
                "grounding_contact_occurrence_id",
                "grounding_contact_custody_receipt_sha256",
                "grounding_contact_capability_receipt_sha256",
                "grounding_contact_settlement_receipt_sha256",
                "parent_custody_receipt_sha256",
                "prior_expansion_receipt_sha256s",
                "schema",
                "sequence",
                "settlement_receipt_sha256",
                "settlement_structural_fingerprint",
                "source_occurrence_id",
                "thing_id",
                "world_before_receipt_sha256",
                "world_execution_receipt_sha256",
                "world_observation_receipt_sha256",
                "world_revision",
            }
            if set(record) != expected_keys or record.get(
                "schema"
            ) != EXPANSION_SCHEMA:
                raise ValueError(
                    "sensory expansion record schema changed"
                )
            expansion = CausalThingSensoryExpansion(
                sequence=record["sequence"],
                thing_id=record["thing_id"],
                admission_basis=record["admission_basis"],
                source_occurrence_id=record["source_occurrence_id"],
                parent_custody_receipt_sha256=(
                    record["parent_custody_receipt_sha256"]
                ),
                custody_capability_receipt_sha256=(
                    record["custody_capability_receipt_sha256"]
                ),
                settlement_receipt_sha256=(
                    record["settlement_receipt_sha256"]
                ),
                settlement_structural_fingerprint=(
                    record["settlement_structural_fingerprint"]
                ),
                world_revision=record["world_revision"],
                world_observation_receipt_sha256=(
                    record["world_observation_receipt_sha256"]
                ),
                world_before_receipt_sha256=(
                    record["world_before_receipt_sha256"]
                ),
                world_execution_receipt_sha256=(
                    record["world_execution_receipt_sha256"]
                ),
                grounding_partition_receipt_sha256=(
                    record["grounding_partition_receipt_sha256"]
                ),
                grounding_contact_occurrence_id=(
                    record["grounding_contact_occurrence_id"]
                ),
                grounding_contact_custody_receipt_sha256=(
                    record["grounding_contact_custody_receipt_sha256"]
                ),
                grounding_contact_capability_receipt_sha256=(
                    record[
                        "grounding_contact_capability_receipt_sha256"
                    ]
                ),
                grounding_contact_settlement_receipt_sha256=(
                    record[
                        "grounding_contact_settlement_receipt_sha256"
                    ]
                ),
                prior_expansion_receipt_sha256s=tuple(
                    record["prior_expansion_receipt_sha256s"]
                ),
                full_field_roots=tuple(
                    _root_from_record(value)
                    for value in record["full_field_roots"]
                ),
                authority_hmac_sha256=record["authority_hmac_sha256"],
                authority_receipt_sha256=(
                    record["authority_receipt_sha256"]
                ),
            )
            self._verify_expansion(expansion)
            self._owned_thing(expansion.thing_id)
            restored.append(expansion)
        if tuple(
            value.sequence for value in restored
        ) != tuple(range(1, len(restored) + 1)):
            raise ValueError(
                "sensory expansion sequence changed"
            )
        staged = tuple(restored)
        if self._encoded(staged) != encoded:
            raise ValueError(
                "sensory expansion cold restore changed canonical state"
            )
        with self._lock:
            self._expansions = staged

    def status(self) -> dict[str, object]:
        with self._lock:
            thing_ids = {
                value.thing_id for value in self._expansions
            }
            return {
                "expansions": len(self._expansions),
                "full_field": True,
                "integrated_causal_thing_ids": len(thing_ids),
                "reduced_approximation": False,
                "roots": sum(
                    len(value.full_field_roots)
                    for value in self._expansions
                ),
                "schema": STATUS_SCHEMA,
                "state_bytes": len(self._encoded(self._expansions)),
                "state_capacity_bytes": self._max_state_bytes,
            }


__all__ = (
    "CausalThingSensoryExpansion",
    "CausalThingSensoryExpansionAdmission",
    "CausalThingSensoryExpansionAdmissionUndo",
    "CausalThingSensoryExpansionOwner",
    "PreparedCausalThingSensoryExpansionAdmission",
    "RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID",
    "RetainedAudiovisualCustody",
    "RetainedAudiovisualCustodyAuthority",
    "RetainedAudiovisualCustodyCapability",
    "THING_SENSORY_EXPANSION_CONSUMER_ID",
    "THING_SENSORY_GROUNDING_CONSUMER_ID",
)
