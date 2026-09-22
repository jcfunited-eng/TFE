"""Bounded exact bilateral pulse closure for authentic W1 Loom intake.

The owner is an auditory neuronal state kernel after frozen L0--L4.  It
learns only from a uniquely grounded causal THING occurrence and evaluates
all learned THING graphs in parallel during query.  Its state is exact,
bounded, authenticated, and contains no transcript, chi, psi, score,
nearest-neighbor relation, or tuned acoustic threshold.

Full rational sensory trajectories remain authoritative in the source W1
settlement and bridge receipt.  This owner consumes the exact integer winding
events those trajectories caused; winding is a neuronal response, never a
replacement for the explicit D/M/R/U/C/P/B field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    W1LoomAuditoryDynamicsOccurrence,
)


PROFILE_SCHEMA = "guala.w1.loom_auditory_pulse_closure.profile.v1"
STATE_SCHEMA = "guala.w1.loom_auditory_pulse_closure.state.v1"
ENVELOPE_SCHEMA = "guala.w1.loom_auditory_pulse_closure.state_hmac.v1"
LEARNING_SCHEMA = "guala.w1.loom_auditory_pulse_closure.learning.v1"
SETTLEMENT_SCHEMA = "guala.w1.loom_auditory_pulse_closure.settlement.v1"

_STATE_DOMAIN = b"guala-w1-loom-auditory-pulse-closure-state-v1\0"
_LEARNING_DOMAIN = b"guala-w1-loom-auditory-pulse-closure-learning-v1\0"
_SETTLEMENT_DOMAIN = b"guala-w1-loom-auditory-pulse-closure-settlement-v1\0"
_HEX = frozenset("0123456789abcdef")


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


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


LaneKey = tuple[str, str, str, str]


@dataclass(frozen=True, order=True, slots=True)
class AuthenticatedPulseRelation:
    source_lane: LaneKey
    target_lane: LaneKey
    source_sign: int
    target_sign: int

    def record(self) -> dict[str, object]:
        return {
            "source_lane": list(self.source_lane),
            "source_sign": self.source_sign,
            "target_lane": list(self.target_lane),
            "target_sign": self.target_sign,
        }

    def verify(self) -> None:
        if (
            len(self.source_lane) != 4
            or len(self.target_lane) != 4
            or any(
                not isinstance(value, str)
                or not value
                or value != value.strip()
                for value in (*self.source_lane, *self.target_lane)
            )
            or self.source_sign not in (-1, 1)
            or self.target_sign not in (-1, 1)
        ):
            raise ValueError("auditory pulse relation changed")


@dataclass(frozen=True, slots=True)
class AuthenticatedBilateralL6PulseProfile:
    profile_id: str
    max_things: int
    max_occurrences_per_thing: int
    max_relations_per_thing: int
    max_total_relations: int
    max_settlement_receipts: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_things: int,
        max_occurrences_per_thing: int,
        max_relations_per_thing: int,
        max_total_relations: int,
        max_settlement_receipts: int,
        max_state_bytes: int,
    ) -> "AuthenticatedBilateralL6PulseProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("pulse-closure profile id changed")
        provisional = cls(
            profile_id=profile_id,
            max_things=_positive(max_things, "THING capacity"),
            max_occurrences_per_thing=_positive(
                max_occurrences_per_thing,
                "occurrence capacity",
            ),
            max_relations_per_thing=_positive(
                max_relations_per_thing,
                "per-THING relation capacity",
            ),
            max_total_relations=_positive(
                max_total_relations,
                "total relation capacity",
            ),
            max_settlement_receipts=_positive(
                max_settlement_receipts,
                "settlement receipt capacity",
            ),
            max_state_bytes=_positive(max_state_bytes, "state capacity"),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_things=provisional.max_things,
            max_occurrences_per_thing=(
                provisional.max_occurrences_per_thing
            ),
            max_relations_per_thing=(
                provisional.max_relations_per_thing
            ),
            max_total_relations=provisional.max_total_relations,
            max_settlement_receipts=(
                provisional.max_settlement_receipts
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_occurrences_per_thing": self.max_occurrences_per_thing,
            "max_relations_per_thing": self.max_relations_per_thing,
            "max_state_bytes": self.max_state_bytes,
            "max_settlement_receipts": self.max_settlement_receipts,
            "max_things": self.max_things,
            "max_total_relations": self.max_total_relations,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("pulse-closure profile authority changed")


@dataclass(frozen=True, slots=True)
class PulseClosureLearningReceipt:
    thing_id: str
    source_occurrence_receipt_sha256: str
    grounding_authority_receipt_sha256: str
    occurrence_count: int
    observed_relation_count: int
    locked_relation_count: int
    discriminative_relation_count: int
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "discriminative_relation_count": (
                self.discriminative_relation_count
            ),
            "grounding_authority_receipt_sha256": (
                self.grounding_authority_receipt_sha256
            ),
            "locked_relation_count": self.locked_relation_count,
            "observed_relation_count": self.observed_relation_count,
            "occurrence_count": self.occurrence_count,
            "schema": LEARNING_SCHEMA,
            "source_occurrence_receipt_sha256": (
                self.source_occurrence_receipt_sha256
            ),
            "thing_id": self.thing_id,
        }

    def verify_shape(self) -> None:
        _sha(self.thing_id, "learning THING id")
        _sha(
            self.source_occurrence_receipt_sha256,
            "learning source occurrence",
        )
        _sha(
            self.grounding_authority_receipt_sha256,
            "learning grounding authority",
        )
        _sha(self.authority_receipt_sha256, "learning authority")
        for value, label in (
            (self.occurrence_count, "learning occurrence count"),
            (self.observed_relation_count, "observed relation count"),
            (self.locked_relation_count, "locked relation count"),
            (
                self.discriminative_relation_count,
                "discriminative relation count",
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} changed")


@dataclass(frozen=True, slots=True)
class PulseThingRelation:
    thing_id: str
    dimensions: int
    matching_non_null: int
    matching_quiescent: int
    effective_dimensions: int
    knee: int
    locked: bool

    def record(self) -> dict[str, object]:
        return {
            "dimensions": self.dimensions,
            "effective_dimensions": self.effective_dimensions,
            "knee": self.knee,
            "locked": self.locked,
            "matching_non_null": self.matching_non_null,
            "matching_quiescent": self.matching_quiescent,
            "thing_id": self.thing_id,
        }

    def verify(self) -> None:
        _sha(self.thing_id, "settled THING id")
        for value, label in (
            (self.dimensions, "settled dimensions"),
            (self.matching_non_null, "settled non-null"),
            (self.matching_quiescent, "settled quiescent"),
            (self.effective_dimensions, "settled effective dimensions"),
            (self.knee, "settled knee"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} changed")
        expected = canonical_l6_direction(
            dimensions=self.dimensions,
            matching_non_null=self.matching_non_null,
            matching_quiescent=self.matching_quiescent,
        )
        if (
            self.effective_dimensions != expected.effective_dimensions
            or self.knee != expected.knee
            or self.locked != expected.locked
        ):
            raise ValueError("settled L6 relation changed")


@dataclass(frozen=True, slots=True)
class PulseClosureSettlement:
    state: str
    thing_ids: tuple[str, ...]
    relations: tuple[PulseThingRelation, ...]
    source_occurrence_receipt_sha256: str
    settlement_sequence: int
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "relations": [value.record() for value in self.relations],
            "schema": SETTLEMENT_SCHEMA,
            "source_occurrence_receipt_sha256": (
                self.source_occurrence_receipt_sha256
            ),
            "settlement_sequence": self.settlement_sequence,
            "state": self.state,
            "thing_ids": list(self.thing_ids),
        }

    def verify(self) -> None:
        _sha(
            self.source_occurrence_receipt_sha256,
            "settlement source occurrence",
        )
        _sha(self.authority_receipt_sha256, "settlement authority")
        if (
            isinstance(self.settlement_sequence, bool)
            or not isinstance(self.settlement_sequence, int)
            or self.settlement_sequence <= 0
        ):
            raise ValueError("settlement sequence changed")
        if (
            tuple(sorted(self.thing_ids)) != self.thing_ids
            or len(set(self.thing_ids)) != len(self.thing_ids)
            or any(
                relation.thing_id
                >= self.relations[index + 1].thing_id
                for index, relation in enumerate(self.relations[:-1])
            )
            or any(
                relation.verify() is not None
                for relation in self.relations
            )
        ):
            raise ValueError("pulse settlement ordering changed")
        locked = tuple(
            relation.thing_id
            for relation in self.relations
            if relation.locked
        )
        expected_state = (
            "resolved"
            if len(locked) == 1
            else "ambiguous"
            if locked
            else "unknown"
        )
        if (
            self.thing_ids != locked
            or self.state != expected_state
        ):
            raise ValueError("pulse settlement shape changed")


class AuthenticatedBilateralL6PulseClosure:
    """Own exact recurrence counters and bounded dynamic query closure."""

    def __init__(
        self,
        *,
        brain: LoomBrain,
        profile: AuthenticatedBilateralL6PulseProfile,
        authority_key: bytes | str,
    ) -> None:
        if not isinstance(brain, LoomBrain):
            raise TypeError("pulse closure requires the live Loom brain")
        profile.verify()
        raw_key = (
            authority_key.encode("utf-8")
            if isinstance(authority_key, str)
            else authority_key
        )
        if not isinstance(raw_key, bytes) or len(raw_key) < 32:
            raise ValueError("pulse-closure authority key changed")
        self._brain = brain
        self._profile = profile
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + raw_key
        ).digest()
        self._learning_key = hashlib.sha256(
            _LEARNING_DOMAIN + raw_key
        ).digest()
        self._settlement_key = hashlib.sha256(
            _SETTLEMENT_DOMAIN + raw_key
        ).digest()
        self._occurrences: dict[str, list[tuple[str, str]]] = {}
        self._relation_counts: dict[
            str,
            dict[AuthenticatedPulseRelation, int],
        ] = {}
        self._locked_relations: dict[
            str,
            frozenset[AuthenticatedPulseRelation],
        ] = {}
        self._settlement_sequence = 0
        self._settlement_receipts: dict[str, bool] = {}
        self._lock = threading.RLock()

    @property
    def profile(self) -> AuthenticatedBilateralL6PulseProfile:
        return self._profile

    def _neuron_neighbors(self) -> dict[str, frozenset[str]]:
        return {
            neuron.neuron_id: frozenset(
                (neuron.neuron_id, *neuron.couplings.neighbors)
            )
            for hemisphere in self._brain.hemispheres
            for neuron in hemisphere.cluster.neurons
        }

    @staticmethod
    def _homologous(left: LaneKey, right: LaneKey) -> bool:
        return (
            left[0] in ("left", "right")
            and right[0] in ("left", "right")
            and left[0] != right[0]
            and left[1:] == right[1:]
        )

    def _allowed_edges(
        self,
        occurrence: W1LoomAuditoryDynamicsOccurrence,
    ) -> tuple[tuple[LaneKey, LaneKey], ...]:
        lane_neurons = {
            value.lane_key: frozenset(value.neuron_ids)
            for value in occurrence.lanes
        }
        neighbors = self._neuron_neighbors()
        lane_keys = tuple(sorted(lane_neurons))
        edges = []
        for source in lane_keys:
            source_neurons = lane_neurons[source]
            for target in lane_keys:
                target_neurons = lane_neurons[target]
                same_or_neighbor = any(
                    source_id in neighbors.get(target_id, ())
                    for source_id in source_neurons
                    for target_id in target_neurons
                )
                if (
                    source == target
                    or same_or_neighbor
                    or self._homologous(source, target)
                ):
                    edges.append((source, target))
        return tuple(edges)

    def _relation_population(
        self,
        occurrence: W1LoomAuditoryDynamicsOccurrence,
    ) -> frozenset[AuthenticatedPulseRelation]:
        occurrence.verify()
        sequences = {
            value.lane_key: value.exact_winding_deltas
            for value in occurrence.lanes
        }
        neuron_lanes: dict[str, set[LaneKey]] = {}
        for value in occurrence.lanes:
            for neuron_id in value.neuron_ids:
                neuron_lanes.setdefault(neuron_id, set()).add(
                    value.lane_key
                )
        homologous = tuple(
            (left, right)
            for left in sorted(sequences)
            for right in sorted(sequences)
            if self._homologous(left, right)
        )
        relations = set()
        for frame_index in range(1, occurrence.frame_count):
            for lanes in neuron_lanes.values():
                sources = tuple(
                    lane
                    for lane in lanes
                    if sequences[lane][frame_index - 1] != 0
                )
                targets = tuple(
                    lane
                    for lane in lanes
                    if sequences[lane][frame_index] != 0
                )
                for source in sources:
                    for target in targets:
                        relations.add(AuthenticatedPulseRelation(
                            source_lane=source,
                            target_lane=target,
                            source_sign=_sign(
                                sequences[source][frame_index - 1]
                            ),
                            target_sign=_sign(
                                sequences[target][frame_index]
                            ),
                        ))
            for source, target in homologous:
                source_value = sequences[source][frame_index - 1]
                target_value = sequences[target][frame_index]
                if source_value != 0 and target_value != 0:
                    relations.add(AuthenticatedPulseRelation(
                        source_lane=source,
                        target_lane=target,
                        source_sign=_sign(source_value),
                        target_sign=_sign(target_value),
                    ))
        for relation in relations:
            relation.verify()
        return frozenset(relations)

    def _recompute_locked(self) -> None:
        for thing_id, counts in self._relation_counts.items():
            dimensions = len(self._occurrences[thing_id])
            if dimensions < 2:
                self._locked_relations[thing_id] = frozenset()
                continue
            self._locked_relations[thing_id] = frozenset(
                relation
                for relation, matching in counts.items()
                if canonical_l6_direction(
                    dimensions=dimensions,
                    matching_non_null=matching,
                    matching_quiescent=0,
                ).locked
            )

    def _discriminative(
        self,
    ) -> dict[str, frozenset[AuthenticatedPulseRelation]]:
        shared = {
            relation
            for values in self._locked_relations.values()
            for relation in values
            if sum(
                relation in other
                for other in self._locked_relations.values()
            )
            > 1
        }
        return {
            thing_id: relations.difference(shared)
            for thing_id, relations in self._locked_relations.items()
        }

    def learn(
        self,
        *,
        occurrence: W1LoomAuditoryDynamicsOccurrence,
        thing_id: str,
        grounding_authority_receipt_sha256: str,
    ) -> PulseClosureLearningReceipt:
        _sha(thing_id, "THING id")
        _sha(grounding_authority_receipt_sha256, "grounding authority")
        occurrence.verify()
        source = _sha(
            occurrence.source_receptor_settlement_receipt_sha256,
            "source occurrence",
        )
        population = self._relation_population(occurrence)
        with self._lock:
            if thing_id not in self._occurrences:
                if len(self._occurrences) >= self._profile.max_things:
                    raise RuntimeError("pulse-closure THING capacity exhausted")
                self._occurrences[thing_id] = []
                self._relation_counts[thing_id] = {}
                self._locked_relations[thing_id] = frozenset()
            if any(
                source == retained_source
                for retained in self._occurrences.values()
                for retained_source, _grounding in retained
            ):
                raise ValueError(
                    "pulse-closure occurrence is not source-disjoint"
                )
            if (
                len(self._occurrences[thing_id])
                >= self._profile.max_occurrences_per_thing
            ):
                raise RuntimeError(
                    "pulse-closure occurrence capacity exhausted"
                )
            counts = dict(self._relation_counts[thing_id])
            for relation in population:
                counts[relation] = counts.get(relation, 0) + 1
            if len(counts) > self._profile.max_relations_per_thing:
                raise RuntimeError(
                    "pulse-closure per-THING relation capacity exhausted"
                )
            total_relations = sum(
                len(value)
                for key, value in self._relation_counts.items()
                if key != thing_id
            ) + len(counts)
            if total_relations > self._profile.max_total_relations:
                raise RuntimeError(
                    "pulse-closure total relation capacity exhausted"
                )
            self._occurrences[thing_id].append((
                source,
                grounding_authority_receipt_sha256,
            ))
            self._relation_counts[thing_id] = counts
            self._recompute_locked()
            discriminative = self._discriminative()
            self._encoded()
            payload = PulseClosureLearningReceipt(
                thing_id=thing_id,
                source_occurrence_receipt_sha256=source,
                grounding_authority_receipt_sha256=(
                    grounding_authority_receipt_sha256
                ),
                occurrence_count=len(self._occurrences[thing_id]),
                observed_relation_count=len(population),
                locked_relation_count=len(
                    self._locked_relations[thing_id]
                ),
                discriminative_relation_count=len(
                    discriminative[thing_id]
                ),
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._learning_key,
                _LEARNING_DOMAIN + _canonical(payload.payload()),
                hashlib.sha256,
            ).hexdigest()
            result = PulseClosureLearningReceipt(
                thing_id=payload.thing_id,
                source_occurrence_receipt_sha256=(
                    payload.source_occurrence_receipt_sha256
                ),
                grounding_authority_receipt_sha256=(
                    payload.grounding_authority_receipt_sha256
                ),
                occurrence_count=payload.occurrence_count,
                observed_relation_count=payload.observed_relation_count,
                locked_relation_count=payload.locked_relation_count,
                discriminative_relation_count=(
                    payload.discriminative_relation_count
                ),
                authority_receipt_sha256=signature,
            )
            result.verify_shape()
            return result

    def verify_learning_receipt(
        self,
        receipt: PulseClosureLearningReceipt,
    ) -> None:
        if not isinstance(receipt, PulseClosureLearningReceipt):
            raise TypeError("pulse learning receipt type changed")
        receipt.verify_shape()
        expected = hmac.new(
            self._learning_key,
            _LEARNING_DOMAIN + _canonical(receipt.payload()),
            hashlib.sha256,
        ).hexdigest()
        if receipt.authority_receipt_sha256 != expected:
            raise ValueError("pulse learning authority changed")

    @staticmethod
    def _dynamic_firing(
        *,
        occurrence: W1LoomAuditoryDynamicsOccurrence,
        relations: frozenset[AuthenticatedPulseRelation],
    ) -> frozenset[AuthenticatedPulseRelation]:
        sequences = {
            value.lane_key: value.exact_winding_deltas
            for value in occurrence.lanes
        }
        by_target: dict[
            LaneKey,
            tuple[AuthenticatedPulseRelation, ...],
        ] = {}
        grouped: dict[LaneKey, list[AuthenticatedPulseRelation]] = {}
        for relation in relations:
            grouped.setdefault(relation.target_lane, []).append(relation)
        by_target = {
            target: tuple(sorted(values))
            for target, values in grouped.items()
        }
        fired = set()
        for frame_index in range(1, occurrence.frame_count):
            for target, incoming in by_target.items():
                target_sign = _sign(sequences[target][frame_index])
                if target_sign == 0:
                    continue
                matching = tuple(
                    relation
                    for relation in incoming
                    if (
                        relation.target_sign == target_sign
                        and _sign(
                            sequences[relation.source_lane][
                                frame_index - 1
                            ]
                        )
                        == relation.source_sign
                    )
                )
                if not matching:
                    continue
                direction = canonical_l6_direction(
                    dimensions=len(incoming),
                    matching_non_null=len(matching),
                    matching_quiescent=0,
                )
                if direction.locked:
                    fired.update(matching)
        return frozenset(fired)

    def settle(
        self,
        occurrence: W1LoomAuditoryDynamicsOccurrence,
    ) -> PulseClosureSettlement:
        occurrence.verify()
        with self._lock:
            discriminative = self._discriminative()
            relations = []
            for thing_id in sorted(discriminative):
                memory = discriminative[thing_id]
                fired = self._dynamic_firing(
                    occurrence=occurrence,
                    relations=memory,
                )
                if memory:
                    direction = canonical_l6_direction(
                        dimensions=len(memory),
                        matching_non_null=len(fired),
                        matching_quiescent=0,
                    )
                    locked = direction.locked
                else:
                    direction = canonical_l6_direction(
                        dimensions=0,
                        matching_non_null=0,
                        matching_quiescent=0,
                    )
                    locked = False
                relations.append(PulseThingRelation(
                    thing_id=thing_id,
                    dimensions=direction.dimensions,
                    matching_non_null=direction.matching_non_null,
                    matching_quiescent=direction.matching_quiescent,
                    effective_dimensions=direction.effective_dimensions,
                    knee=direction.knee,
                    locked=locked,
                ))
        locked_ids = tuple(
            value.thing_id for value in relations if value.locked
        )
        state = (
            "resolved"
            if len(locked_ids) == 1
            else "ambiguous"
            if locked_ids
            else "unknown"
        )
        with self._lock:
            if (
                len(self._settlement_receipts)
                >= self._profile.max_settlement_receipts
            ):
                raise RuntimeError(
                    "pulse-closure settlement receipt capacity exhausted"
                )
            self._settlement_sequence += 1
            provisional = PulseClosureSettlement(
                state=state,
                thing_ids=locked_ids,
                relations=tuple(relations),
                source_occurrence_receipt_sha256=(
                    occurrence.source_receptor_settlement_receipt_sha256
                ),
                settlement_sequence=self._settlement_sequence,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._settlement_key,
                _SETTLEMENT_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            result = PulseClosureSettlement(
                state=provisional.state,
                thing_ids=provisional.thing_ids,
                relations=provisional.relations,
                source_occurrence_receipt_sha256=(
                    provisional.source_occurrence_receipt_sha256
                ),
                settlement_sequence=provisional.settlement_sequence,
                authority_receipt_sha256=signature,
            )
            result.verify()
            self._settlement_receipts[signature] = False
            self._encoded()
            return result

    def verify_settlement(
        self,
        settlement: PulseClosureSettlement,
        *,
        consume: bool = True,
    ) -> None:
        if not isinstance(settlement, PulseClosureSettlement):
            raise TypeError("pulse settlement type changed")
        settlement.verify()
        expected = hmac.new(
            self._settlement_key,
            _SETTLEMENT_DOMAIN + _canonical(settlement.payload()),
            hashlib.sha256,
        ).hexdigest()
        with self._lock:
            if settlement.authority_receipt_sha256 != expected:
                raise ValueError("pulse settlement owner authority changed")
            consumed = self._settlement_receipts.get(expected)
            if consumed is None:
                raise ValueError("pulse settlement was not issued by owner")
            if consumed:
                raise ValueError("pulse settlement receipt was replayed")
            if consume:
                self._settlement_receipts[expected] = True

    def _body(self) -> dict[str, object]:
        return {
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "settlement_receipts": [
                {
                    "authority_receipt_sha256": digest,
                    "consumed": consumed,
                }
                for digest, consumed in sorted(
                    self._settlement_receipts.items()
                )
            ],
            "settlement_sequence": self._settlement_sequence,
            "things": [
                {
                    "locked_relations": [
                        relation.record()
                        for relation in sorted(
                            self._locked_relations[thing_id]
                        )
                    ],
                    "occurrences": [
                        {
                            "grounding_authority_receipt_sha256": grounding,
                            "source_occurrence_receipt_sha256": source,
                        }
                        for source, grounding in self._occurrences[thing_id]
                    ],
                    "relation_counts": [
                        {
                            "count": count,
                            "relation": relation.record(),
                        }
                        for relation, count in sorted(
                            self._relation_counts[thing_id].items()
                        )
                    ],
                    "thing_id": thing_id,
                }
                for thing_id in sorted(self._occurrences)
            ],
        }

    def _encoded(self) -> bytes:
        body = self._body()
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("pulse-closure state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded()

    def status(self) -> dict[str, object]:
        with self._lock:
            discriminative = self._discriminative()
            return {
                "discriminative_relations": sum(
                    len(value) for value in discriminative.values()
                ),
                "full_field_authority_retained": True,
                "locked_relations": sum(
                    len(value)
                    for value in self._locked_relations.values()
                ),
                "occurrences": sum(
                    len(value) for value in self._occurrences.values()
                ),
                "reduced_approximation": False,
                "schema": "guala.w1.loom_auditory_pulse_closure.status.v1",
                "settlement_receipts": len(
                    self._settlement_receipts
                ),
                "state_bytes": len(self._encoded()),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "things": len(self._occurrences),
            }


def _relation_from_record(value: Mapping[str, object]) -> AuthenticatedPulseRelation:
    relation = AuthenticatedPulseRelation(
        source_lane=tuple(value["source_lane"]),
        target_lane=tuple(value["target_lane"]),
        source_sign=int(value["source_sign"]),
        target_sign=int(value["target_sign"]),
    )
    relation.verify()
    return relation


def restore_authenticated_bilateral_l6_pulse_closure(
    encoded: bytes,
    *,
    brain: LoomBrain,
    authority_key: bytes | str,
) -> AuthenticatedBilateralL6PulseClosure:
    try:
        envelope = json.loads(encoded)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("pulse-closure state is unreadable") from error
    if (
        not isinstance(envelope, Mapping)
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or not isinstance(envelope.get("body"), Mapping)
    ):
        raise ValueError("pulse-closure state envelope changed")
    body = envelope["body"]
    profile_record = body["profile"]
    profile = AuthenticatedBilateralL6PulseProfile(
        profile_id=profile_record["profile_id"],
        max_things=int(profile_record["max_things"]),
        max_occurrences_per_thing=int(
            profile_record["max_occurrences_per_thing"]
        ),
        max_relations_per_thing=int(
            profile_record["max_relations_per_thing"]
        ),
        max_total_relations=int(profile_record["max_total_relations"]),
        max_settlement_receipts=int(
            profile_record["max_settlement_receipts"]
        ),
        max_state_bytes=int(profile_record["max_state_bytes"]),
        authority_receipt_sha256=profile_record[
            "authority_receipt_sha256"
        ],
    )
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=profile,
        authority_key=authority_key,
    )
    expected_hmac = hmac.new(
        owner._state_key,
        _STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if (
        body.get("schema") != STATE_SCHEMA
        or envelope.get("state_hmac_sha256") != expected_hmac
        or _canonical(envelope) != encoded
    ):
        raise ValueError("pulse-closure state authority changed")
    for thing in body["things"]:
        thing_id = _sha(thing["thing_id"], "restored THING id")
        occurrences = [
            (
                _sha(
                    value["source_occurrence_receipt_sha256"],
                    "restored occurrence",
                ),
                _sha(
                    value["grounding_authority_receipt_sha256"],
                    "restored grounding",
                ),
            )
            for value in thing["occurrences"]
        ]
        counts = {
            _relation_from_record(value["relation"]): int(value["count"])
            for value in thing["relation_counts"]
        }
        locked = frozenset(
            _relation_from_record(value)
            for value in thing["locked_relations"]
        )
        owner._occurrences[thing_id] = occurrences
        owner._relation_counts[thing_id] = counts
        owner._locked_relations[thing_id] = locked
    owner._settlement_sequence = int(body["settlement_sequence"])
    owner._settlement_receipts = {
        _sha(
            value["authority_receipt_sha256"],
            "restored settlement authority",
        ): bool(value["consumed"])
        for value in body["settlement_receipts"]
    }
    owner._recompute_locked()
    if owner.snapshot_encoded() != encoded:
        raise ValueError("pulse-closure cold restore changed state")
    return owner


__all__ = (
    "AuthenticatedBilateralL6PulseClosure",
    "AuthenticatedBilateralL6PulseProfile",
    "AuthenticatedPulseRelation",
    "PulseClosureLearningReceipt",
    "PulseClosureSettlement",
    "PulseThingRelation",
    "restore_authenticated_bilateral_l6_pulse_closure",
)
