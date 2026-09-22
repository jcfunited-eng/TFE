"""Experience-grown local auditory familiarity under causal THING custody.

This owner never assigns a word or treats one auditory firing set as an
identity.  It receives authenticated binaural q activations whose local
intervals retain complete D/M/R/U/C/P/B occurrence witnesses.  A tutoring
episode is admitted only when those activations and one retained causal THING
partition name the same physical settlement.

Each episode contributes every run-collapsed local event and every adjacent
ordered event pair.  Canonical L6 selects motifs recurrent across a THING's
independent encounters.  A motif which also locks under another causally
distinct THING becomes quiescent and is removed from release authority.  Thus
varied experience expands the mosaic and divergent consequence fissions it.

Retrieval applies canonical L6 to each complete fissioned local-motif
population.  Zero locks is unknown; multiple locks is ambiguous; neither state
releases a THING.  There is no similarity score, tuned threshold, waveform
equality, whole firing-set equality, transcript, label, chi, static sensory
profile, ML operation, or reduced DSF field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    _validate_occurrence_record,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryBinauralMotifFiring,
    AuditoryMotifActivation,
)
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)


AUDITORY_THING_FAMILIARITY_PROFILE_SCHEMA = (
    "guala.auditory.thing_familiarity_profile.v1"
)
AUDITORY_THING_LOCAL_PARTITION_SCHEMA = (
    "guala.auditory.thing_local_partition.v1"
)
AUDITORY_THING_FAMILIARITY_EPISODE_SCHEMA = (
    "guala.auditory.thing_familiarity_episode.v1"
)
AUDITORY_THING_FAMILIARITY_MEMORY_SCHEMA = (
    "guala.auditory.thing_familiarity_memory.v1"
)
AUDITORY_THING_FAMILIARITY_RESOLUTION_SCHEMA = (
    "guala.auditory.thing_familiarity_resolution.v1"
)
AUDITORY_THING_FAMILIARITY_STATE_SCHEMA = (
    "guala.auditory.thing_familiarity_state.v1"
)
_EPISODE_DOMAIN = b"guala-auditory-thing-familiarity-episode-v1\0"
_MEMORY_DOMAIN = b"guala-auditory-thing-familiarity-memory-v1\0"
_RESOLUTION_DOMAIN = (
    b"guala-auditory-thing-familiarity-resolution-v1\0"
)
_STATE_DOMAIN = b"guala-auditory-thing-familiarity-state-v1\0"
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
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("auditory THING familiarity key is invalid")
    return result


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("auditory familiarity time must remain exact")
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class AuditoryThingFamiliarityProfile:
    profile_id: str
    max_things: int
    max_episodes: int
    max_partitions_per_episode: int
    max_motifs_per_episode: int
    max_occurrence_records: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_things: int,
        max_episodes: int,
        max_partitions_per_episode: int,
        max_motifs_per_episode: int,
        max_occurrence_records: int,
        max_state_bytes: int,
    ) -> "AuditoryThingFamiliarityProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError(
                "auditory THING familiarity profile id is invalid"
            )
        values = {
            "max_episodes": _positive(
                max_episodes,
                "auditory familiarity episode capacity",
            ),
            "max_motifs_per_episode": _positive(
                max_motifs_per_episode,
                "auditory familiarity motif capacity",
            ),
            "max_occurrence_records": _positive(
                max_occurrence_records,
                "auditory familiarity occurrence capacity",
            ),
            "max_partitions_per_episode": _positive(
                max_partitions_per_episode,
                "auditory familiarity partition capacity",
            ),
            "max_state_bytes": _positive(
                max_state_bytes,
                "auditory familiarity byte capacity",
            ),
            "max_things": _positive(
                max_things,
                "auditory familiarity THING capacity",
            ),
        }
        payload = {
            **values,
            "profile_id": profile_id,
            "schema": AUDITORY_THING_FAMILIARITY_PROFILE_SCHEMA,
        }
        return cls(
            profile_id=profile_id,
            **values,
            authority_receipt_sha256=_digest(payload),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_episodes": self.max_episodes,
            "max_motifs_per_episode": self.max_motifs_per_episode,
            "max_occurrence_records": self.max_occurrence_records,
            "max_partitions_per_episode": (
                self.max_partitions_per_episode
            ),
            "max_state_bytes": self.max_state_bytes,
            "max_things": self.max_things,
            "profile_id": self.profile_id,
            "schema": AUDITORY_THING_FAMILIARITY_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_things=self.max_things,
            max_episodes=self.max_episodes,
            max_partitions_per_episode=(
                self.max_partitions_per_episode
            ),
            max_motifs_per_episode=self.max_motifs_per_episode,
            max_occurrence_records=self.max_occurrence_records,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError(
                "auditory THING familiarity profile authority changed"
            )


@dataclass(frozen=True, slots=True, order=True)
class AuditoryLocalEventIdentity:
    neuron_id: str
    segment_index: int

    def verify(self) -> None:
        _sha(self.neuron_id, "auditory local neuron")
        if (
            isinstance(self.segment_index, bool)
            or not isinstance(self.segment_index, int)
            or not 0 <= self.segment_index < 64
        ):
            raise ValueError(
                "auditory local event left receptor topology"
            )

    def payload(self) -> list[object]:
        self.verify()
        return [self.neuron_id, self.segment_index]


@dataclass(frozen=True, slots=True, order=True)
class AuditoryLocalMotif:
    kind: str
    events: tuple[AuditoryLocalEventIdentity, ...]

    def verify(self) -> None:
        expected_count = {"event": 1, "adjacent": 2}.get(self.kind)
        if expected_count is None or len(self.events) != expected_count:
            raise ValueError("auditory local motif structure changed")
        for event in self.events:
            event.verify()

    def payload(self) -> list[object]:
        self.verify()
        return [
            self.kind,
            [event.payload() for event in self.events],
        ]


@dataclass(frozen=True, slots=True)
class AuditoryLocalPartition:
    identity: AuditoryLocalEventIdentity
    source_time_start: Fraction
    source_time_end: Fraction
    source_index_start: int
    source_index_end: int
    occurrence_receipt_sha256s: tuple[str, ...]
    occurrence_support_root_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "identity": self.identity.payload(),
            "occurrence_receipt_sha256s": list(
                self.occurrence_receipt_sha256s
            ),
            "occurrence_support_root_sha256": (
                self.occurrence_support_root_sha256
            ),
            "schema": AUDITORY_THING_LOCAL_PARTITION_SCHEMA,
            "source_index_end": self.source_index_end,
            "source_index_start": self.source_index_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(
                self.source_time_start
            ),
        }

    def verify(self) -> None:
        self.identity.verify()
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or isinstance(self.source_index_start, bool)
            or not isinstance(self.source_index_start, int)
            or isinstance(self.source_index_end, bool)
            or not isinstance(self.source_index_end, int)
            or self.source_index_start < 0
            or self.source_index_end < self.source_index_start
            or not self.occurrence_receipt_sha256s
        ):
            raise ValueError("auditory local partition changed")
        for value in self.occurrence_receipt_sha256s:
            _sha(value, "auditory local occurrence")
        expected_root = _digest({
            "ordered_full_field_occurrence_receipt_sha256s": list(
                self.occurrence_receipt_sha256s
            ),
            "schema": "guala.auditory.activation_support_root.v1",
        })
        if (
            expected_root != self.occurrence_support_root_sha256
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory local full-field support changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryThingFamiliarityEpisode:
    episode_id: str
    thing_id: str
    thing_mosaic_receipt_sha256: str
    thing_partition_receipt_sha256: str
    settlement_receipt_sha256: str
    firing_receipt_sha256: str
    source_component_sha256s: tuple[str, ...]
    partitions: tuple[AuditoryLocalPartition, ...]
    motifs: tuple[AuditoryLocalMotif, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "firing_receipt_sha256": self.firing_receipt_sha256,
            "motifs": [value.payload() for value in self.motifs],
            "partitions": [
                value.payload()
                | {
                    "authority_receipt_sha256": (
                        value.authority_receipt_sha256
                    )
                }
                for value in self.partitions
            ],
            "schema": AUDITORY_THING_FAMILIARITY_EPISODE_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "source_component_sha256s": list(
                self.source_component_sha256s
            ),
            "thing_id": self.thing_id,
            "thing_mosaic_receipt_sha256": (
                self.thing_mosaic_receipt_sha256
            ),
            "thing_partition_receipt_sha256": (
                self.thing_partition_receipt_sha256
            ),
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.episode_id, "auditory familiarity episode"),
            (self.thing_id, "auditory familiarity THING"),
            (
                self.thing_mosaic_receipt_sha256,
                "auditory familiarity THING mosaic",
            ),
            (
                self.thing_partition_receipt_sha256,
                "auditory familiarity THING partition",
            ),
            (
                self.settlement_receipt_sha256,
                "auditory familiarity settlement",
            ),
            (
                self.firing_receipt_sha256,
                "auditory familiarity firing",
            ),
        ):
            _sha(value, name)
        if (
            not self.source_component_sha256s
            or not self.partitions
            or not self.motifs
            or tuple(sorted(set(self.motifs))) != self.motifs
        ):
            raise ValueError(
                "auditory familiarity episode structure changed"
            )
        for value in self.source_component_sha256s:
            _sha(value, "auditory familiarity source component")
        for partition in self.partitions:
            partition.verify()
        for motif in self.motifs:
            motif.verify()
        payload = self.payload()
        expected = hmac.new(
            key,
            _EPISODE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.episode_id
            != _digest({
                "settlement_receipt_sha256": (
                    self.settlement_receipt_sha256
                ),
                "thing_partition_receipt_sha256": (
                    self.thing_partition_receipt_sha256
                ),
            })
            or not hmac.compare_digest(
                expected,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected,
                "payload": payload,
            })
        ):
            raise ValueError(
                "auditory familiarity episode authority changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryThingFamiliarityMemory:
    thing_id: str
    version: int
    episode_receipt_sha256s: tuple[str, ...]
    recurrent_motif_supports: tuple[
        tuple[AuditoryLocalMotif, int], ...
    ]
    quiescent_motifs: tuple[AuditoryLocalMotif, ...]
    required_motifs: tuple[AuditoryLocalMotif, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "episode_receipt_sha256s": list(
                self.episode_receipt_sha256s
            ),
            "quiescent_motifs": [
                value.payload() for value in self.quiescent_motifs
            ],
            "recurrent_motif_supports": [
                [motif.payload(), support]
                for motif, support in self.recurrent_motif_supports
            ],
            "required_motifs": [
                value.payload() for value in self.required_motifs
            ],
            "schema": AUDITORY_THING_FAMILIARITY_MEMORY_SCHEMA,
            "thing_id": self.thing_id,
            "version": self.version,
        }

    def verify(self, key: bytes) -> None:
        _sha(self.thing_id, "auditory familiarity memory THING")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version <= 0
            or len(self.episode_receipt_sha256s) != self.version
            or tuple(
                motif for motif, _support
                in self.recurrent_motif_supports
            ) != tuple(sorted({
                motif for motif, _support
                in self.recurrent_motif_supports
            }))
            or tuple(sorted(set(self.quiescent_motifs)))
            != self.quiescent_motifs
            or tuple(sorted(set(self.required_motifs)))
            != self.required_motifs
            or set(self.quiescent_motifs).intersection(
                self.required_motifs
            )
        ):
            raise ValueError(
                "auditory familiarity memory structure changed"
            )
        for value in self.episode_receipt_sha256s:
            _sha(value, "auditory familiarity memory episode")
        recurrent = {
            motif for motif, support
            in self.recurrent_motif_supports
            if canonical_l6_direction(
                dimensions=self.version,
                matching_non_null=support,
                matching_quiescent=0,
            ).locked
        }
        if recurrent != set(
            self.quiescent_motifs + self.required_motifs
        ):
            raise ValueError(
                "auditory familiarity L6 recurrence changed"
            )
        payload = self.payload()
        expected = hmac.new(
            key,
            _MEMORY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected,
                "payload": payload,
            })
        ):
            raise ValueError(
                "auditory familiarity memory authority changed"
            )


class AuditoryThingFamiliarityAdmissionState(str, Enum):
    SETTLED = "settled"
    UNKNOWN = "unknown"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class AuditoryThingFamiliarityAdmission:
    state: AuditoryThingFamiliarityAdmissionState
    reason: str
    episode: AuditoryThingFamiliarityEpisode | None
    memory: AuditoryThingFamiliarityMemory | None
    grown_motif_count: int
    fissioned_motif_count: int


class AuditoryThingFamiliarityResolutionState(str, Enum):
    UNKNOWN = "unknown"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class AuditoryThingFamiliarityResolution:
    state: AuditoryThingFamiliarityResolutionState
    released_thing_id: str | None
    locked_thing_ids: tuple[str, ...]
    directions: tuple[dict[str, object], ...]
    query_firing_receipt_sha256: str
    query_partition_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "directions": list(self.directions),
            "locked_thing_ids": list(self.locked_thing_ids),
            "query_firing_receipt_sha256": (
                self.query_firing_receipt_sha256
            ),
            "query_partition_receipt_sha256s": list(
                self.query_partition_receipt_sha256s
            ),
            "released_thing_id": self.released_thing_id,
            "schema": AUDITORY_THING_FAMILIARITY_RESOLUTION_SCHEMA,
            "state": self.state.value,
        }

    def verify(self, key: bytes) -> None:
        _sha(
            self.query_firing_receipt_sha256,
            "auditory familiarity query firing",
        )
        for value in (
            self.locked_thing_ids
            + self.query_partition_receipt_sha256s
        ):
            _sha(value, "auditory familiarity query authority")
        if (
            tuple(sorted(set(self.locked_thing_ids)))
            != self.locked_thing_ids
            or (
                self.state
                is AuditoryThingFamiliarityResolutionState.UNIQUE
                and (
                    len(self.locked_thing_ids) != 1
                    or self.released_thing_id
                    != self.locked_thing_ids[0]
                )
            )
            or (
                self.state
                is not AuditoryThingFamiliarityResolutionState.UNIQUE
                and self.released_thing_id is not None
            )
        ):
            raise ValueError(
                "auditory familiarity release governance changed"
            )
        payload = self.payload()
        expected = hmac.new(
            key,
            _RESOLUTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected,
                "payload": payload,
            })
        ):
            raise ValueError(
                "auditory familiarity resolution authority changed"
            )


def _partition_from_activation(
    activation: AuditoryMotifActivation,
    registry: dict[str, dict[str, object]],
) -> AuditoryLocalPartition:
    receipts = []
    for occurrence in activation.full_field_occurrences:
        occurrence.verify()
        record = occurrence.payload() | {
            "authority_receipt_sha256": (
                occurrence.authority_receipt_sha256
            ),
        }
        _validate_occurrence_record(record)
        receipt = occurrence.authority_receipt_sha256
        prior = registry.get(receipt)
        if prior is not None and prior != record:
            raise ValueError(
                "auditory familiarity occurrence receipt was reused"
            )
        registry[receipt] = record
        receipts.append(receipt)
    if not receipts:
        raise ValueError(
            "auditory familiarity activation lacks full-field custody"
        )
    root = _digest({
        "ordered_full_field_occurrence_receipt_sha256s": receipts,
        "schema": "guala.auditory.activation_support_root.v1",
    })
    draft = AuditoryLocalPartition(
        identity=AuditoryLocalEventIdentity(
            neuron_id=activation.neuron_id,
            segment_index=activation.segment_index,
        ),
        source_time_start=activation.source_time_start,
        source_time_end=activation.source_time_end,
        source_index_start=activation.source_index_start,
        source_index_end=activation.source_index_end,
        occurrence_receipt_sha256s=tuple(receipts),
        occurrence_support_root_sha256=root,
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryLocalPartition(
        identity=draft.identity,
        source_time_start=draft.source_time_start,
        source_time_end=draft.source_time_end,
        source_index_start=draft.source_index_start,
        source_index_end=draft.source_index_end,
        occurrence_receipt_sha256s=(
            draft.occurrence_receipt_sha256s
        ),
        occurrence_support_root_sha256=(
            draft.occurrence_support_root_sha256
        ),
        authority_receipt_sha256=_digest(draft.payload()),
    )
    result.verify()
    return result


def _local_structure(
    firing: AuditoryBinauralMotifFiring,
    registry: dict[str, dict[str, object]],
) -> tuple[
    tuple[AuditoryLocalPartition, ...],
    tuple[AuditoryLocalMotif, ...],
]:
    firing.verify()
    ordered = sorted(
        (
            _partition_from_activation(activation, registry)
            for activation in firing.activations
        ),
        key=lambda value: (
            value.source_time_start,
            value.source_time_end,
            value.source_index_start,
            value.source_index_end,
            value.identity,
        ),
    )
    collapsed: list[AuditoryLocalPartition] = []
    for partition in ordered:
        if collapsed and collapsed[-1].identity == partition.identity:
            prior = collapsed[-1]
            receipts = tuple(dict.fromkeys(
                prior.occurrence_receipt_sha256s
                + partition.occurrence_receipt_sha256s
            ))
            root = _digest({
                "ordered_full_field_occurrence_receipt_sha256s": list(
                    receipts
                ),
                "schema": "guala.auditory.activation_support_root.v1",
            })
            draft = AuditoryLocalPartition(
                identity=prior.identity,
                source_time_start=min(
                    prior.source_time_start,
                    partition.source_time_start,
                ),
                source_time_end=max(
                    prior.source_time_end,
                    partition.source_time_end,
                ),
                source_index_start=min(
                    prior.source_index_start,
                    partition.source_index_start,
                ),
                source_index_end=max(
                    prior.source_index_end,
                    partition.source_index_end,
                ),
                occurrence_receipt_sha256s=receipts,
                occurrence_support_root_sha256=root,
                authority_receipt_sha256="0" * 64,
            )
            collapsed[-1] = AuditoryLocalPartition(
                identity=draft.identity,
                source_time_start=draft.source_time_start,
                source_time_end=draft.source_time_end,
                source_index_start=draft.source_index_start,
                source_index_end=draft.source_index_end,
                occurrence_receipt_sha256s=(
                    draft.occurrence_receipt_sha256s
                ),
                occurrence_support_root_sha256=(
                    draft.occurrence_support_root_sha256
                ),
                authority_receipt_sha256=_digest(draft.payload()),
            )
            collapsed[-1].verify()
        else:
            collapsed.append(partition)
    motifs = {
        AuditoryLocalMotif("event", (partition.identity,))
        for partition in collapsed
    }
    motifs.update(
        AuditoryLocalMotif(
            "adjacent",
            (left.identity, right.identity),
        )
        for left, right in zip(collapsed, collapsed[1:])
    )
    result = tuple(sorted(motifs))
    for motif in result:
        motif.verify()
    return tuple(collapsed), result


class AuditoryThingFamiliarityOwner:
    """Bounded owner of local auditory routes into causal THING mosaics."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: AuditoryThingFamiliarityProfile,
        thing_owner: CausalThingMosaicOwner,
    ) -> None:
        profile.verify()
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "auditory familiarity requires causal THING custody"
            )
        root = _key(authority_key)
        self._episode_key = hashlib.sha256(
            _EPISODE_DOMAIN + root
        ).digest()
        self._memory_key = hashlib.sha256(
            _MEMORY_DOMAIN + root
        ).digest()
        self._resolution_key = hashlib.sha256(
            _RESOLUTION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root
        ).digest()
        self._profile = profile
        self._things = thing_owner
        self._episodes: dict[
            str, AuditoryThingFamiliarityEpisode
        ] = {}
        self._memories: dict[
            str, AuditoryThingFamiliarityMemory
        ] = {}
        self._occurrence_registry: dict[
            str, dict[str, object]
        ] = {}
        self._lock = threading.RLock()

    @property
    def memories(self) -> tuple[AuditoryThingFamiliarityMemory, ...]:
        with self._lock:
            return tuple(
                self._memories[key] for key in sorted(self._memories)
            )

    def _owned_partition(
        self,
        *,
        mosaic: CausalThingMosaic,
        partition: ThingEncounterPartition,
    ) -> None:
        if not isinstance(mosaic, CausalThingMosaic) or not isinstance(
            partition,
            ThingEncounterPartition,
        ):
            raise TypeError(
                "auditory familiarity requires typed THING custody"
            )
        owned = tuple(
            value for value in self._things.mosaics
            if value.thing_id == mosaic.thing_id
        )
        if owned != (mosaic,) or partition not in mosaic.partitions:
            raise ValueError(
                "auditory familiarity THING custody is not current"
            )

    def _seal_memory(
        self,
        *,
        thing_id: str,
        episodes: tuple[AuditoryThingFamiliarityEpisode, ...],
        recurrent: dict[AuditoryLocalMotif, int],
        quiescent: set[AuditoryLocalMotif],
    ) -> AuditoryThingFamiliarityMemory:
        required = tuple(sorted(set(recurrent) - quiescent))
        draft = AuditoryThingFamiliarityMemory(
            thing_id=thing_id,
            version=len(episodes),
            episode_receipt_sha256s=tuple(
                value.authority_receipt_sha256
                for value in episodes
            ),
            recurrent_motif_supports=tuple(sorted(
                recurrent.items()
            )),
            quiescent_motifs=tuple(sorted(
                set(recurrent).intersection(quiescent)
            )),
            required_motifs=required,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._memory_key,
            _MEMORY_DOMAIN + _canonical(draft.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = AuditoryThingFamiliarityMemory(
            thing_id=draft.thing_id,
            version=draft.version,
            episode_receipt_sha256s=(
                draft.episode_receipt_sha256s
            ),
            recurrent_motif_supports=(
                draft.recurrent_motif_supports
            ),
            quiescent_motifs=draft.quiescent_motifs,
            required_motifs=draft.required_motifs,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": draft.payload(),
            }),
        )
        result.verify(self._memory_key)
        return result

    def _rebuild(
        self,
        episodes: Mapping[str, AuditoryThingFamiliarityEpisode],
    ) -> dict[str, AuditoryThingFamiliarityMemory]:
        grouped = {
            thing_id: tuple(sorted(
                (
                    episode for episode in episodes.values()
                    if episode.thing_id == thing_id
                ),
                key=lambda value: value.episode_id,
            ))
            for thing_id in sorted({
                value.thing_id for value in episodes.values()
            })
        }
        recurrent_by_thing: dict[
            str, dict[AuditoryLocalMotif, int]
        ] = {}
        for thing_id, values in grouped.items():
            population = {
                motif for episode in values for motif in episode.motifs
            }
            counts = {
                motif: sum(
                    motif in episode.motifs for episode in values
                )
                for motif in population
            }
            recurrent_by_thing[thing_id] = {
                motif: support for motif, support in counts.items()
                if canonical_l6_direction(
                    dimensions=len(values),
                    matching_non_null=support,
                    matching_quiescent=0,
                ).locked
            }
        quiescent = {
            motif
            for recurrent in recurrent_by_thing.values()
            for motif in recurrent
            if sum(
                motif in other
                for other in recurrent_by_thing.values()
            ) > 1
        }
        return {
            thing_id: self._seal_memory(
                thing_id=thing_id,
                episodes=grouped[thing_id],
                recurrent=recurrent,
                quiescent=quiescent,
            )
            for thing_id, recurrent in recurrent_by_thing.items()
        }

    def admit(
        self,
        *,
        firing: AuditoryBinauralMotifFiring,
        receptor_settlement: W1BinauralReceptorSettlement,
        mosaic: CausalThingMosaic,
        partition: ThingEncounterPartition,
    ) -> AuditoryThingFamiliarityAdmission:
        firing.verify()
        if not isinstance(
            receptor_settlement,
            W1BinauralReceptorSettlement,
        ):
            raise TypeError(
                "auditory familiarity requires typed receptor custody"
            )
        receptor_settlement.verify()
        self._owned_partition(
            mosaic=mosaic,
            partition=partition,
        )
        if (
            firing.source_settlement_receipt_sha256
            != receptor_settlement.authority_receipt_sha256
            or receptor_settlement
            .upstream_causal_settlement_receipt_sha256
            != partition.settlement_receipt_sha256
        ):
            raise ValueError(
                "auditory familiarity did not co-occur with THING"
            )
        sound_roots = tuple(
            root for root in partition.full_field_roots
            if root.sense == "sound"
        )
        if not sound_roots:
            raise ValueError(
                "auditory familiarity THING encounter lacks sound"
            )
        staged_registry = dict(self._occurrence_registry)
        partitions, motifs = _local_structure(
            firing,
            staged_registry,
        )
        if not partitions or not motifs:
            return AuditoryThingFamiliarityAdmission(
                state=AuditoryThingFamiliarityAdmissionState.UNKNOWN,
                reason="no local auditory motif entered THING custody",
                episode=None,
                memory=None,
                grown_motif_count=0,
                fissioned_motif_count=0,
            )
        if (
            len(partitions)
            > self._profile.max_partitions_per_episode
            or len(motifs) > self._profile.max_motifs_per_episode
            or len(staged_registry)
            > self._profile.max_occurrence_records
        ):
            raise RuntimeError(
                "auditory familiarity local evidence capacity exhausted"
            )
        source_components = tuple(sorted(
            root.physical_value_sha256 for root in sound_roots
        ))
        episode_id = _digest({
            "settlement_receipt_sha256": (
                partition.settlement_receipt_sha256
            ),
            "thing_partition_receipt_sha256": (
                partition.authority_receipt_sha256
            ),
        })
        draft = AuditoryThingFamiliarityEpisode(
            episode_id=episode_id,
            thing_id=mosaic.thing_id,
            thing_mosaic_receipt_sha256=(
                mosaic.authority_receipt_sha256
            ),
            thing_partition_receipt_sha256=(
                partition.authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                partition.settlement_receipt_sha256
            ),
            firing_receipt_sha256=(
                firing.authority_receipt_sha256
            ),
            source_component_sha256s=source_components,
            partitions=partitions,
            motifs=motifs,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(draft.payload()),
            hashlib.sha256,
        ).hexdigest()
        episode = AuditoryThingFamiliarityEpisode(
            episode_id=draft.episode_id,
            thing_id=draft.thing_id,
            thing_mosaic_receipt_sha256=(
                draft.thing_mosaic_receipt_sha256
            ),
            thing_partition_receipt_sha256=(
                draft.thing_partition_receipt_sha256
            ),
            settlement_receipt_sha256=(
                draft.settlement_receipt_sha256
            ),
            firing_receipt_sha256=draft.firing_receipt_sha256,
            source_component_sha256s=(
                draft.source_component_sha256s
            ),
            partitions=draft.partitions,
            motifs=draft.motifs,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": draft.payload(),
            }),
        )
        episode.verify(self._episode_key)
        with self._lock:
            existing = self._episodes.get(episode_id)
            if existing is not None:
                if existing != episode:
                    raise ValueError(
                        "auditory familiarity episode was reused"
                    )
                return AuditoryThingFamiliarityAdmission(
                    state=(
                        AuditoryThingFamiliarityAdmissionState.DUPLICATE
                    ),
                    reason="auditory THING episode already retained",
                    episode=existing,
                    memory=self._memories.get(existing.thing_id),
                    grown_motif_count=0,
                    fissioned_motif_count=0,
                )
            if len(self._episodes) >= self._profile.max_episodes:
                raise RuntimeError(
                    "auditory familiarity episode capacity exhausted"
                )
            thing_ids = {
                value.thing_id for value in self._episodes.values()
            } | {episode.thing_id}
            if len(thing_ids) > self._profile.max_things:
                raise RuntimeError(
                    "auditory familiarity THING capacity exhausted"
                )
            for prior in self._episodes.values():
                if (
                    prior.thing_id == episode.thing_id
                    and prior.source_component_sha256s
                    == episode.source_component_sha256s
                ):
                    raise ValueError(
                        "auditory familiarity source experience repeated"
                    )
            staged_episodes = dict(self._episodes)
            staged_episodes[episode_id] = episode
            prior_required = {
                thing_id: set(memory.required_motifs)
                for thing_id, memory in self._memories.items()
            }
            staged_memories = self._rebuild(staged_episodes)
            current_required = set(
                staged_memories[episode.thing_id].required_motifs
            )
            grown = len(
                current_required
                - prior_required.get(episode.thing_id, set())
            )
            fissioned = sum(
                len(
                    prior_required.get(thing_id, set())
                    - set(memory.required_motifs)
                )
                for thing_id, memory in staged_memories.items()
            )
            encoded = self._encoded(
                staged_episodes,
                staged_memories,
                staged_registry,
            )
            if len(encoded) > self._profile.max_state_bytes:
                raise RuntimeError(
                    "auditory familiarity state capacity exhausted"
                )
            self._episodes = staged_episodes
            self._memories = staged_memories
            self._occurrence_registry = staged_registry
            return AuditoryThingFamiliarityAdmission(
                state=AuditoryThingFamiliarityAdmissionState.SETTLED,
                reason=(
                    "local auditory motifs settled under causal THING"
                ),
                episode=episode,
                memory=staged_memories[episode.thing_id],
                grown_motif_count=grown,
                fissioned_motif_count=fissioned,
            )

    def resolve(
        self,
        firing: AuditoryBinauralMotifFiring,
    ) -> AuditoryThingFamiliarityResolution:
        transient_registry: dict[str, dict[str, object]] = {}
        partitions, motifs = _local_structure(
            firing,
            transient_registry,
        )
        observed = set(motifs)
        directions = []
        locked = []
        with self._lock:
            memories = self.memories
        for memory in memories:
            memory.verify(self._memory_key)
            required = set(memory.required_motifs)
            if required:
                direction = canonical_l6_direction(
                    dimensions=len(required),
                    matching_non_null=len(
                        required.intersection(observed)
                    ),
                    matching_quiescent=0,
                )
            else:
                direction = canonical_l6_direction(
                    dimensions=0,
                    matching_non_null=0,
                    matching_quiescent=0,
                )
            directions.append({
                "dimensions": direction.dimensions,
                "effective_dimensions": (
                    direction.effective_dimensions
                ),
                "knee": direction.knee,
                "locked": direction.locked,
                "matching_non_null": direction.matching_non_null,
                "matching_quiescent": (
                    direction.matching_quiescent
                ),
                "memory_receipt_sha256": (
                    memory.authority_receipt_sha256
                ),
                "thing_id": memory.thing_id,
            })
            if required and direction.locked:
                locked.append(memory.thing_id)
        locked_tuple = tuple(sorted(locked))
        state = (
            AuditoryThingFamiliarityResolutionState.UNKNOWN
            if not locked_tuple
            else AuditoryThingFamiliarityResolutionState.UNIQUE
            if len(locked_tuple) == 1
            else AuditoryThingFamiliarityResolutionState.AMBIGUOUS
        )
        draft = AuditoryThingFamiliarityResolution(
            state=state,
            released_thing_id=(
                locked_tuple[0]
                if state
                is AuditoryThingFamiliarityResolutionState.UNIQUE
                else None
            ),
            locked_thing_ids=locked_tuple,
            directions=tuple(directions),
            query_firing_receipt_sha256=(
                firing.authority_receipt_sha256
            ),
            query_partition_receipt_sha256s=tuple(
                value.authority_receipt_sha256
                for value in partitions
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._resolution_key,
            _RESOLUTION_DOMAIN + _canonical(draft.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = AuditoryThingFamiliarityResolution(
            state=draft.state,
            released_thing_id=draft.released_thing_id,
            locked_thing_ids=draft.locked_thing_ids,
            directions=draft.directions,
            query_firing_receipt_sha256=(
                draft.query_firing_receipt_sha256
            ),
            query_partition_receipt_sha256s=(
                draft.query_partition_receipt_sha256s
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": draft.payload(),
            }),
        )
        result.verify(self._resolution_key)
        return result

    def _body(
        self,
        episodes: Mapping[str, AuditoryThingFamiliarityEpisode],
        memories: Mapping[str, AuditoryThingFamiliarityMemory],
        registry: Mapping[str, dict[str, object]],
    ) -> dict[str, object]:
        return {
            "episodes": [
                episodes[key].payload()
                | {
                    "authority_hmac_sha256": (
                        episodes[key].authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        episodes[key].authority_receipt_sha256
                    ),
                }
                for key in sorted(episodes)
            ],
            "memories": [
                memories[key].payload()
                | {
                    "authority_hmac_sha256": (
                        memories[key].authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        memories[key].authority_receipt_sha256
                    ),
                }
                for key in sorted(memories)
            ],
            "occurrence_registry": [
                [receipt, record]
                for receipt, record in sorted(registry.items())
            ],
            "profile": self._profile.payload()
            | {
                "authority_receipt_sha256": (
                    self._profile.authority_receipt_sha256
                )
            },
            "schema": AUDITORY_THING_FAMILIARITY_STATE_SCHEMA,
        }

    def _encoded(
        self,
        episodes: Mapping[str, AuditoryThingFamiliarityEpisode],
        memories: Mapping[str, AuditoryThingFamiliarityMemory],
        registry: Mapping[str, dict[str, object]],
    ) -> bytes:
        body = self._body(episodes, memories, registry)
        return _canonical({
            "body": body,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            encoded = self._encoded(
                self._episodes,
                self._memories,
                self._occurrence_registry,
            )
            if len(encoded) > self._profile.max_state_bytes:
                raise RuntimeError(
                    "auditory familiarity state capacity exhausted"
                )
            return encoded

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self.snapshot_encoded()
            return {
                "encoded_state_bytes": len(encoded),
                "episode_count": len(self._episodes),
                "max_episodes": self._profile.max_episodes,
                "max_occurrence_records": (
                    self._profile.max_occurrence_records
                ),
                "max_state_bytes": self._profile.max_state_bytes,
                "max_things": self._profile.max_things,
                "memory_count": len(self._memories),
                "occurrence_record_count": len(
                    self._occurrence_registry
                ),
                "required_motif_count": sum(
                    len(value.required_motifs)
                    for value in self._memories.values()
                ),
                "retained_raw_media_bytes": 0,
                "schema": (
                    "guala.auditory.thing_familiarity_status.v1"
                ),
            }


__all__ = [
    "AUDITORY_THING_FAMILIARITY_PROFILE_SCHEMA",
    "AuditoryLocalEventIdentity",
    "AuditoryLocalMotif",
    "AuditoryLocalPartition",
    "AuditoryThingFamiliarityAdmission",
    "AuditoryThingFamiliarityAdmissionState",
    "AuditoryThingFamiliarityEpisode",
    "AuditoryThingFamiliarityMemory",
    "AuditoryThingFamiliarityOwner",
    "AuditoryThingFamiliarityProfile",
    "AuditoryThingFamiliarityResolution",
    "AuditoryThingFamiliarityResolutionState",
]
