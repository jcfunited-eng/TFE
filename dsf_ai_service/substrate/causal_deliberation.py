"""Bounded deterministic action-conditioned full-field deliberation.

This authority joins only evidence already authenticated by the causal action
cycle.  A structural fingerprint is an index, never the evidence: every
retained six-sense witness is decoded and its ordered substreams, coordinates,
and seven exact DSF fields are recomputed before use or restore.

For a current field F, zero learned actions stops unknown, more than one stops
ambiguous, and one action advances only when exactly one verified outcome is
known for (F, A).  The observed outcome must itself appear in a verified action
closure.  A different verified outcome is retained as the single
counterexample, makes the relation ambiguous, and stops.  One serial episode,
one terminal marker, at most 64 relations, two distinct outcomes per relation,
and a bounded visited set prevent replay, recurrence, and lifetime indexing.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.causal_action_cycle import (
    ACTION_SCHEMA,
    ActionCommand,
    CausalActionCycle,
    PerceptionWitness,
    VerifiedActionRelationEvidence,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    SETTLEMENT_SCHEMA,
    VerifiedCausalSettlementCapability,
)


WITNESS_SCHEMA = "guala.causal_deliberation.witness.v1"
RELATION_SCHEMA = "guala.causal_deliberation.relation.v1"
EPISODE_SCHEMA = "guala.causal_deliberation.episode.v1"
TERMINAL_SCHEMA = "guala.causal_deliberation.terminal.v2"
STATE_SCHEMA = "guala.causal_deliberation.state.v2"
ENVELOPE_SCHEMA = "guala.causal_deliberation.hmac.v2"

STATE_DOMAIN = b"guala-causal-deliberation-state-v1\0"

MAX_RELATIONS = 64
MAX_OUTCOMES_PER_RELATION = 2
DEFAULT_ENCODED_STATE_BYTES = 32 * 1024 * 1024
LEGACY_MAX_WITNESS_BYTES = 2 * 1024 * 1024
# A witness is retained as base64 inside the authenticated deliberation
# envelope.  This is the largest raw witness that can fit when it is the
# only retained evidence; aggregate state encoding remains the final bound.
DEFAULT_MAX_WITNESS_BYTES = (
    3 * (DEFAULT_ENCODED_STATE_BYTES - 1_024) // 4
)


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("causal deliberation key must be bytes or text")
    if not result:
        raise ValueError("causal deliberation key is required")
    return result


def _sign(key: bytes, payload: bytes) -> str:
    return hmac.new(key, STATE_DOMAIN + payload, hashlib.sha256).hexdigest()


def _full_field_structure(decoded: Mapping[str, object]) -> str:
    interpretations = decoded.get("interpretations")
    language_events = decoded.get("language_events")
    expected_senses = tuple(item.value for item in SENSE_ORDER)
    if (
        not isinstance(interpretations, list)
        or len(interpretations) != len(expected_senses)
        or any(not isinstance(item, Mapping) for item in interpretations)
        or tuple(item.get("sense") for item in interpretations) != expected_senses
        or not isinstance(language_events, list)
    ):
        raise ValueError("deliberation witness lost canonical six-sense structure")

    sense_identity: dict[str, dict[str, object]] = {}
    for sense in interpretations:
        expected_fields = {
            "boundary_receipt_sha256",
            "relation",
            "sense",
            "state",
            "structural_fingerprint",
            "substreams",
            "topology_receipt_sha256",
        }
        if set(sense) != expected_fields or not isinstance(
            sense.get("substreams"), list
        ):
            raise ValueError("deliberation witness sense fields changed")
        compact_substreams = []
        sight_signal_commitment_present = None
        for topology_index, substream in enumerate(sense["substreams"]):
            if not isinstance(substream, Mapping):
                raise ValueError("deliberation witness substream fields changed")
            expected_substream_fields = {
                "coordinates",
                "field_tuples",
                "kernel_basin_receipt_sha256",
                "physical_quantity",
                "physical_unit",
                "profile_receipt_sha256",
                "sensor_id",
                "source_evidence_stream_receipt_sha256",
                "source_sample_commitment_sha256",
                "source_sample_count",
                "substream_id",
                "topology_index",
            }
            has_signal_commitment = (
                "source_signal_commitment_sha256" in substream
            )
            if sense["sense"] == "sight":
                if sight_signal_commitment_present is None:
                    sight_signal_commitment_present = (
                        has_signal_commitment
                    )
                elif (
                    sight_signal_commitment_present
                    != has_signal_commitment
                ):
                    raise ValueError(
                        "deliberation sight commitment topology changed"
                    )
                if has_signal_commitment:
                    expected_substream_fields = (
                        expected_substream_fields
                        | {"source_signal_commitment_sha256"}
                    )
            elif has_signal_commitment:
                raise ValueError(
                    "nonvisual deliberation retained visual source identity"
                )
            if (
                set(substream) != expected_substream_fields
                or substream.get("topology_index") != topology_index
                or not isinstance(substream.get("coordinates"), list)
                or not isinstance(substream.get("field_tuples"), list)
            ):
                raise ValueError("deliberation witness substream topology changed")
            if has_signal_commitment:
                sha256_digest(
                    substream["source_signal_commitment_sha256"],
                    "deliberation sight source signal commitment",
                )
            compact_tuples = []
            for tuple_index, field_tuple in enumerate(substream["field_tuples"]):
                if (
                    not isinstance(field_tuple, Mapping)
                    or set(field_tuple)
                    != {
                        "authority_receipt_sha256",
                        "fields",
                        "source_index_end",
                        "source_index_start",
                        "source_l0_l4_trace_receipt_sha256",
                        "tuple_index",
                    }
                    or field_tuple.get("tuple_index") != tuple_index
                    or isinstance(
                        field_tuple.get("source_index_start"), bool
                    )
                    or not isinstance(
                        field_tuple.get("source_index_start"), int
                    )
                    or isinstance(
                        field_tuple.get("source_index_end"), bool
                    )
                    or not isinstance(
                        field_tuple.get("source_index_end"), int
                    )
                    or not 0
                    <= field_tuple["source_index_start"]
                    <= field_tuple["source_index_end"]
                    or not isinstance(field_tuple.get("fields"), list)
                    or tuple(
                        item[0]
                        for item in field_tuple["fields"]
                        if isinstance(item, list) and len(item) == 2
                    )
                    != DSF_FIELD_ORDER
                    or len(field_tuple["fields"]) != len(DSF_FIELD_ORDER)
                ):
                    raise ValueError("deliberation witness DSF tuple changed")
                compact_fields = []
                for name, value in field_tuple["fields"]:
                    if not isinstance(value, str):
                        raise ValueError("deliberation witness DSF field is not exact")
                    try:
                        exact = Fraction(value)
                    except (ValueError, ZeroDivisionError) as error:
                        raise ValueError(
                            "deliberation witness DSF field is not exact"
                        ) from error
                    if f"{exact.numerator}/{exact.denominator}" != value:
                        raise ValueError(
                            "deliberation witness DSF field is not canonical"
                        )
                    compact_fields.append([name, value])
                compact_tuples.append(
                    {
                        "fields": compact_fields,
                        "source_index_end": field_tuple[
                            "source_index_end"
                        ],
                        "source_index_start": field_tuple[
                            "source_index_start"
                        ],
                        "tuple_index": tuple_index,
                    }
                )
            compact_substreams.append(
                {
                    "coordinates": substream["coordinates"],
                    "field_tuples": compact_tuples,
                    "physical_quantity": substream.get("physical_quantity"),
                    "physical_unit": substream.get("physical_unit"),
                    "substream_id": substream.get("substream_id"),
                    "topology_index": topology_index,
                }
            )
        recomputed = _digest(
            {"state": sense.get("state"), "substreams": compact_substreams}
        )
        if recomputed != sense.get("structural_fingerprint"):
            raise ValueError("deliberation witness explicit DSF field changed")
        sense_identity[sense["sense"]] = {
            "state": sense.get("state"),
            "structural_fingerprint": recomputed,
        }

    language_identity = []
    for item in language_events:
        if not isinstance(item, Mapping):
            raise ValueError("deliberation witness language event changed")
        occurrence = item.get("recognition_occurrence")
        selected = (
            occurrence.get("selected_class_authority_receipt_sha256")
            if isinstance(occurrence, Mapping)
            else None
        )
        language_identity.append(
            {
                "form": item.get("form"),
                "recognition_class_authority_receipt_sha256": selected,
                "unicode_scalars": item.get("unicode_scalars"),
            }
        )
    return _digest(
        {
            "interpretations": sense_identity,
            "language_events": language_identity,
        }
    )


@dataclass(frozen=True, slots=True)
class DeliberationWitness:
    event_id: str
    settlement_receipt_sha256: str
    structural_fingerprint: str
    settlement_payload_base64: str

    @classmethod
    def from_settlement(
        cls,
        settlement: CausalExperienceSettlement,
        *,
        max_bytes: int,
        verified_transaction: (
            VerifiedCausalSettlementCapability | None
        ) = None,
    ) -> "DeliberationWitness":
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("deliberation requires an exact causal settlement")
        if verified_transaction is None:
            settlement.verify()
        else:
            if not isinstance(
                verified_transaction,
                VerifiedCausalSettlementCapability,
            ):
                raise TypeError(
                    "deliberation causal authority has wrong type"
                )
            verified_transaction.verify_linkage(settlement)
        payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "causal deliberation settlement",
        )
        return cls._from_payload(
            event_id=settlement.event_id,
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            structural_fingerprint=settlement.structural_fingerprint,
            payload=payload,
            max_bytes=max_bytes,
        )

    @classmethod
    def from_action_witness(
        cls, witness: PerceptionWitness, *, max_bytes: int
    ) -> "DeliberationWitness":
        witness.verify(max_bytes=max_bytes)
        payload = base64.b64decode(
            witness.settlement_payload_base64, validate=True
        )
        return cls._from_payload(
            event_id=witness.event_id,
            settlement_receipt_sha256=witness.settlement_receipt_sha256,
            structural_fingerprint=witness.structural_fingerprint,
            payload=payload,
            max_bytes=max_bytes,
        )

    @classmethod
    def _from_payload(
        cls,
        *,
        event_id: str,
        settlement_receipt_sha256: str,
        structural_fingerprint: str,
        payload: bytes,
        max_bytes: int,
    ) -> "DeliberationWitness":
        if not payload or len(payload) > max_bytes:
            raise RuntimeError("deliberation witness exceeds its byte boundary")
        result = cls(
            event_id=event_id,
            settlement_receipt_sha256=settlement_receipt_sha256,
            structural_fingerprint=structural_fingerprint,
            settlement_payload_base64=base64.b64encode(payload).decode("ascii"),
        )
        result.verify(max_bytes=max_bytes)
        return result

    def verify(self, *, max_bytes: int) -> None:
        sha256_digest(self.event_id, "deliberation event")
        sha256_digest(self.settlement_receipt_sha256, "deliberation settlement")
        sha256_digest(self.structural_fingerprint, "deliberation structure")
        try:
            payload = base64.b64decode(
                self.settlement_payload_base64, validate=True
            )
        except Exception as error:
            raise ValueError("deliberation witness is not canonical base64") from error
        if (
            not payload
            or len(payload) > max_bytes
            or receipt_sha256(payload) != self.settlement_receipt_sha256
            or base64.b64encode(payload).decode("ascii")
            != self.settlement_payload_base64
        ):
            raise ValueError("deliberation witness receipt changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("deliberation witness payload is invalid") from error
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or decoded.get("schema") != SETTLEMENT_SCHEMA
            or decoded.get("event_id") != self.event_id
            or decoded.get("structural_fingerprint")
            != self.structural_fingerprint
            or _full_field_structure(decoded) != self.structural_fingerprint
        ):
            raise ValueError("deliberation witness structural identity changed")

    def as_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "schema": WITNESS_SCHEMA,
            "settlement_payload_base64": self.settlement_payload_base64,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "structural_fingerprint": self.structural_fingerprint,
        }


def _witness_from(value: object, *, max_bytes: int) -> DeliberationWitness:
    expected = {
        "event_id",
        "schema",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != WITNESS_SCHEMA
    ):
        raise ValueError("deliberation witness fields changed")
    witness = DeliberationWitness(
        event_id=value.get("event_id"),
        settlement_receipt_sha256=value.get("settlement_receipt_sha256"),
        structural_fingerprint=value.get("structural_fingerprint"),
        settlement_payload_base64=value.get("settlement_payload_base64"),
    )
    witness.verify(max_bytes=max_bytes)
    return witness


def _action_from(value: object) -> ActionCommand:
    expected = {
        "command_payload_base64",
        "kind",
        "port_id",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != ACTION_SCHEMA
    ):
        raise ValueError("deliberation action fields changed")
    try:
        payload = base64.b64decode(
            value.get("command_payload_base64"), validate=True
        )
    except Exception as error:
        raise ValueError("deliberation action payload changed") from error
    action = ActionCommand(
        kind=value.get("kind"),
        port_id=value.get("port_id"),
        command_payload=payload,
    )
    action.verify(max_command_bytes=4096)
    if action.as_record() != dict(value):
        raise ValueError("deliberation action is not canonical")
    return action


@dataclass(frozen=True, slots=True)
class DeliberationRelation:
    binding_id: str
    trigger: DeliberationWitness
    action: ActionCommand
    status: str
    outcome_closure_receipts: tuple[str, ...]
    outcomes: tuple[DeliberationWitness, ...]

    @property
    def relation_id(self) -> str:
        return _digest(
            {
                "action_receipt_sha256": self.action.authority_receipt_sha256,
                "schema": "guala.causal_deliberation.relation_identity.v1",
                "trigger_structural_fingerprint": (
                    self.trigger.structural_fingerprint
                ),
            }
        )

    def verify(self, *, max_bytes: int) -> None:
        sha256_digest(self.binding_id, "deliberation binding")
        self.trigger.verify(max_bytes=max_bytes)
        self.action.verify(max_command_bytes=4096)
        if self.status not in {"provisional", "confirmed", "revoked"}:
            raise ValueError("deliberation relation status changed")
        if (
            len(self.outcomes) != len(self.outcome_closure_receipts)
            or len(self.outcomes) > MAX_OUTCOMES_PER_RELATION
            or len(
                {item.structural_fingerprint for item in self.outcomes}
            )
            != len(self.outcomes)
        ):
            raise ValueError("deliberation outcome cardinality changed")
        for receipt, witness in zip(
            self.outcome_closure_receipts, self.outcomes, strict=True
        ):
            sha256_digest(receipt, "deliberation closure")
            witness.verify(max_bytes=max_bytes)

    def as_record(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "binding_id": self.binding_id,
            "outcome_closure_receipts": list(self.outcome_closure_receipts),
            "outcomes": [item.as_record() for item in self.outcomes],
            "schema": RELATION_SCHEMA,
            "status": self.status,
            "trigger": self.trigger.as_record(),
        }


def _relation_from(value: object, *, max_bytes: int) -> DeliberationRelation:
    expected = {
        "action",
        "binding_id",
        "outcome_closure_receipts",
        "outcomes",
        "schema",
        "status",
        "trigger",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != RELATION_SCHEMA
        or not isinstance(value.get("outcomes"), list)
        or not isinstance(value.get("outcome_closure_receipts"), list)
    ):
        raise ValueError("deliberation relation fields changed")
    relation = DeliberationRelation(
        binding_id=value.get("binding_id"),
        trigger=_witness_from(value.get("trigger"), max_bytes=max_bytes),
        action=_action_from(value.get("action")),
        status=value.get("status"),
        outcome_closure_receipts=tuple(value.get("outcome_closure_receipts")),
        outcomes=tuple(
            _witness_from(item, max_bytes=max_bytes)
            for item in value.get("outcomes")
        ),
    )
    relation.verify(max_bytes=max_bytes)
    return relation


@dataclass(frozen=True, slots=True)
class DeliberationEpisode:
    episode_id: str
    current: DeliberationWitness
    relation_id: str
    expected_outcome: DeliberationWitness
    visited_structural_fingerprints: tuple[str, ...]
    depth: int

    def verify(self, *, max_bytes: int, visited_capacity: int) -> None:
        sha256_digest(self.episode_id, "deliberation episode")
        sha256_digest(self.relation_id, "deliberation episode relation")
        self.current.verify(max_bytes=max_bytes)
        self.expected_outcome.verify(max_bytes=max_bytes)
        if (
            isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth <= 0
            or len(self.visited_structural_fingerprints) != self.depth
            or len(self.visited_structural_fingerprints) > visited_capacity
            or len(set(self.visited_structural_fingerprints))
            != len(self.visited_structural_fingerprints)
            or self.visited_structural_fingerprints[-1]
            != self.current.structural_fingerprint
        ):
            raise ValueError("deliberation episode boundary changed")
        for item in self.visited_structural_fingerprints:
            sha256_digest(item, "deliberation visited structure")

    def as_record(self) -> dict[str, object]:
        return {
            "current": self.current.as_record(),
            "depth": self.depth,
            "episode_id": self.episode_id,
            "expected_outcome": self.expected_outcome.as_record(),
            "relation_id": self.relation_id,
            "schema": EPISODE_SCHEMA,
            "visited_structural_fingerprints": list(
                self.visited_structural_fingerprints
            ),
        }


@dataclass(frozen=True, slots=True)
class DeliberationTerminal:
    world_structural_fingerprint: str
    relation_state_sha256: str
    reason: str
    evidence_receipt_sha256: str | None = None

    def verify(self) -> None:
        sha256_digest(
            self.world_structural_fingerprint, "terminal world structure"
        )
        sha256_digest(self.relation_state_sha256, "terminal relation state")
        if self.reason not in {
            "action_unknown",
            "action_ambiguous",
            "outcome_unknown",
            "outcome_ambiguous",
            "outcome_unverified",
            "outcome_mismatch",
            "recurrence",
            "visited_capacity",
            "dispatcher_rejected",
            "dispatch_identity_mismatch",
            "restore_evidence_mismatch",
        }:
            raise ValueError("deliberation terminal reason changed")
        if self.evidence_receipt_sha256 is not None:
            sha256_digest(
                self.evidence_receipt_sha256,
                "deliberation terminal evidence",
            )

    def as_record(self) -> dict[str, object]:
        return {
            "evidence_receipt_sha256": self.evidence_receipt_sha256,
            "reason": self.reason,
            "relation_state_sha256": self.relation_state_sha256,
            "schema": TERMINAL_SCHEMA,
            "world_structural_fingerprint": self.world_structural_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class DeliberationTurn:
    status: str
    episode_id: str | None
    depth: int
    action: ActionCommand | None = None
    expected_outcome: DeliberationWitness | None = None
    binding_id: str | None = None
    relation_id: str | None = None
    action_receipt_sha256: str | None = None
    stop_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status == "action":
            if (
                self.episode_id is None
                or self.depth <= 0
                or self.action is None
                or self.expected_outcome is None
                or self.binding_id is None
                or self.relation_id is None
                or self.action_receipt_sha256
                != self.action.authority_receipt_sha256
                or self.stop_reason is not None
            ):
                raise ValueError("deliberation action turn changed")
        elif self.status == "stopped":
            if (
                self.action is not None
                or self.expected_outcome is not None
                or self.binding_id is not None
                or self.relation_id is not None
                or self.action_receipt_sha256 is not None
                or self.stop_reason is None
                or self.depth < 0
            ):
                raise ValueError("deliberation stop turn changed")
        else:
            raise ValueError("deliberation turn status changed")


class CausalDeliberation:
    """One bounded serial owner for verified action-conditioned thought."""

    def __init__(
        self,
        *,
        authority_key: object,
        relation_capacity: int = MAX_RELATIONS,
        max_witness_bytes: int = DEFAULT_MAX_WITNESS_BYTES,
        encoded_state_capacity: int = DEFAULT_ENCODED_STATE_BYTES,
    ) -> None:
        if (
            isinstance(relation_capacity, bool)
            or not isinstance(relation_capacity, int)
            or relation_capacity <= 0
            or relation_capacity > MAX_RELATIONS
            or isinstance(max_witness_bytes, bool)
            or not isinstance(max_witness_bytes, int)
            or max_witness_bytes <= 0
            or isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or encoded_state_capacity <= 0
        ):
            raise ValueError("causal deliberation capacities are invalid")
        self._key = _key(authority_key)
        self._relation_capacity = relation_capacity
        self._visited_capacity = relation_capacity + 1
        self._max_witness_bytes = max_witness_bytes
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._relations: OrderedDict[str, DeliberationRelation] = OrderedDict()
        self._by_structure: dict[str, set[str]] = {}
        self._episode: DeliberationEpisode | None = None
        self._terminal: DeliberationTerminal | None = None

    def _capacities(self) -> dict[str, int]:
        return {
            "encoded_state_capacity": self._encoded_state_capacity,
            "max_outcomes_per_relation": MAX_OUTCOMES_PER_RELATION,
            "max_witness_bytes": self._max_witness_bytes,
            "relation_capacity": self._relation_capacity,
            "visited_capacity": self._visited_capacity,
        }

    def _relation_state_sha256(self) -> str:
        return _digest(
            [self._relations[key].as_record() for key in self._relations]
        )

    def _state(self) -> dict[str, object]:
        return {
            "capacities": self._capacities(),
            "episode": self._episode.as_record() if self._episode else None,
            "relations": [item.as_record() for item in self._relations.values()],
            "schema": STATE_SCHEMA,
            "terminal": self._terminal.as_record() if self._terminal else None,
        }

    def _encoded_locked(self) -> bytes:
        payload = _canonical(self._state())
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError("causal deliberation state capacity is full")
        return payload

    @contextmanager
    def _atomic(self):
        prior = (
            OrderedDict(self._relations),
            {key: set(value) for key, value in self._by_structure.items()},
            self._episode,
            self._terminal,
        )
        try:
            yield
            self._encoded_locked()
        except BaseException:
            (
                self._relations,
                self._by_structure,
                self._episode,
                self._terminal,
            ) = prior
            raise

    def _reindex(self) -> None:
        index: dict[str, set[str]] = {}
        for relation_id, relation in self._relations.items():
            if relation.status != "revoked":
                index.setdefault(
                    relation.trigger.structural_fingerprint, set()
                ).add(relation_id)
        self._by_structure = index

    def _relation_from_evidence(
        self, evidence: VerifiedActionRelationEvidence
    ) -> DeliberationRelation:
        trigger = DeliberationWitness.from_action_witness(
            evidence.trigger_witness, max_bytes=self._max_witness_bytes
        )
        action = evidence.action
        action.verify(max_command_bytes=4096)
        relation_id = _digest(
            {
                "action_receipt_sha256": action.authority_receipt_sha256,
                "schema": "guala.causal_deliberation.relation_identity.v1",
                "trigger_structural_fingerprint": trigger.structural_fingerprint,
            }
        )
        existing = self._relations.get(relation_id)
        outcomes = list(existing.outcomes if existing else ())
        closure_receipts = list(
            existing.outcome_closure_receipts if existing else ()
        )
        if evidence.outcome_witness is not None:
            outcome = DeliberationWitness.from_action_witness(
                evidence.outcome_witness, max_bytes=self._max_witness_bytes
            )
            known = {
                item.structural_fingerprint: index
                for index, item in enumerate(outcomes)
            }
            index = known.get(outcome.structural_fingerprint)
            if index is None:
                if len(outcomes) < MAX_OUTCOMES_PER_RELATION:
                    outcomes.append(outcome)
                    closure_receipts.append(
                        evidence.latest_closure_receipt_sha256
                    )
            else:
                outcomes[index] = outcome
                closure_receipts[index] = evidence.latest_closure_receipt_sha256
        relation = DeliberationRelation(
            binding_id=evidence.binding_id,
            trigger=trigger,
            action=action,
            status=evidence.status,
            outcome_closure_receipts=tuple(closure_receipts),
            outcomes=tuple(outcomes),
        )
        relation.verify(max_bytes=self._max_witness_bytes)
        if relation.relation_id != relation_id:
            raise ValueError("deliberation relation identity changed")
        if existing is not None and (
            existing.binding_id != relation.binding_id
            or existing.trigger.structural_fingerprint
            != relation.trigger.structural_fingerprint
            or existing.action != relation.action
        ):
            raise ValueError("verified action relation changed identity")
        return relation

    def _synchronize(
        self,
        evidence: tuple[VerifiedActionRelationEvidence, ...],
    ) -> None:
        if (
            not isinstance(evidence, tuple)
            or any(
                not isinstance(item, VerifiedActionRelationEvidence)
                for item in evidence
            )
        ):
            raise TypeError("deliberation requires verified relation evidence")
        current_ids = set()
        replacements = []
        for item in evidence:
            relation = self._relation_from_evidence(item)
            current_ids.add(relation.relation_id)
            replacements.append(relation)
        with self._atomic():
            for relation_id in tuple(self._relations):
                if relation_id not in current_ids:
                    del self._relations[relation_id]
            for relation in replacements:
                relation_id = relation.relation_id
                if relation_id not in self._relations:
                    while len(self._relations) >= self._relation_capacity:
                        self._relations.popitem(last=False)
                self._relations[relation_id] = relation
                self._relations.move_to_end(relation_id)
            self._reindex()

    @staticmethod
    def _evidence_for(
        *,
        action_cycle: CausalActionCycle | None,
        admitted_evidence: tuple[VerifiedActionRelationEvidence, ...] | None,
    ) -> tuple[VerifiedActionRelationEvidence, ...]:
        if admitted_evidence is not None:
            if action_cycle is not None:
                raise ValueError(
                    "deliberation received two relation authorities"
                )
            return admitted_evidence
        if not isinstance(action_cycle, CausalActionCycle):
            raise TypeError("deliberation requires a causal action cycle")
        return action_cycle.verified_relation_evidence()

    def _stop(
        self,
        *,
        world: DeliberationWitness,
        reason: str,
        episode_id: str | None,
        depth: int,
    ) -> DeliberationTurn:
        terminal = DeliberationTerminal(
            world_structural_fingerprint=world.structural_fingerprint,
            relation_state_sha256=self._relation_state_sha256(),
            reason=reason,
        )
        terminal.verify()
        self._episode = None
        self._terminal = terminal
        return DeliberationTurn(
            status="stopped",
            episode_id=episode_id,
            depth=depth,
            stop_reason=reason,
        )

    def _choose(
        self,
        *,
        world: DeliberationWitness,
        episode_id: str,
        visited: tuple[str, ...],
    ) -> DeliberationTurn:
        candidates = tuple(
            sorted(self._by_structure.get(world.structural_fingerprint, ()))
        )
        if not candidates:
            return self._stop(
                world=world,
                reason="action_unknown",
                episode_id=episode_id,
                depth=len(visited),
            )
        if len(candidates) != 1:
            return self._stop(
                world=world,
                reason="action_ambiguous",
                episode_id=episode_id,
                depth=len(visited),
            )
        relation = self._relations[candidates[0]]
        if not relation.outcomes:
            return self._stop(
                world=world,
                reason="outcome_unknown",
                episode_id=episode_id,
                depth=len(visited),
            )
        if len(relation.outcomes) != 1:
            return self._stop(
                world=world,
                reason="outcome_ambiguous",
                episode_id=episode_id,
                depth=len(visited),
            )
        episode = DeliberationEpisode(
            episode_id=episode_id,
            current=world,
            relation_id=relation.relation_id,
            expected_outcome=relation.outcomes[0],
            visited_structural_fingerprints=visited,
            depth=len(visited),
        )
        episode.verify(
            max_bytes=self._max_witness_bytes,
            visited_capacity=self._visited_capacity,
        )
        self._episode = episode
        self._terminal = None
        return DeliberationTurn(
            status="action",
            episode_id=episode_id,
            depth=episode.depth,
            action=relation.action,
            expected_outcome=relation.outcomes[0],
            binding_id=relation.binding_id,
            relation_id=relation.relation_id,
            action_receipt_sha256=relation.action.authority_receipt_sha256,
        )

    def start(
        self,
        settlement: CausalExperienceSettlement,
        *,
        action_cycle: CausalActionCycle | None = None,
        admitted_evidence: tuple[
            VerifiedActionRelationEvidence, ...
        ] | None = None,
    ) -> DeliberationTurn:
        world = DeliberationWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        with self._lock:
            self._synchronize(self._evidence_for(
                action_cycle=action_cycle,
                admitted_evidence=admitted_evidence,
            ))
            relation_state = self._relation_state_sha256()
            if self._episode is not None:
                return DeliberationTurn(
                    status="stopped",
                    episode_id=self._episode.episode_id,
                    depth=self._episode.depth,
                    stop_reason="outcome_unverified",
                )
            if (
                self._terminal is not None
                and self._terminal.world_structural_fingerprint
                == world.structural_fingerprint
                and self._terminal.relation_state_sha256 == relation_state
            ):
                return DeliberationTurn(
                    status="stopped",
                    episode_id=None,
                    depth=0,
                    stop_reason=self._terminal.reason,
                )
            episode_id = _digest(
                {
                    "relation_state_sha256": relation_state,
                    "schema": "guala.causal_deliberation.episode_identity.v1",
                    "settlement_receipt_sha256": world.settlement_receipt_sha256,
                }
            )
            with self._atomic():
                return self._choose(
                    world=world,
                    episode_id=episode_id,
                    visited=(world.structural_fingerprint,),
                )

    def advance(
        self,
        settlement: CausalExperienceSettlement,
        *,
        action_outcome: CausalExperienceSettlement | None = None,
        action_cycle: CausalActionCycle | None = None,
        admitted_evidence: tuple[
            VerifiedActionRelationEvidence, ...
        ] | None = None,
    ) -> DeliberationTurn:
        world = DeliberationWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        outcome_world = (
            DeliberationWitness.from_settlement(
                action_outcome, max_bytes=self._max_witness_bytes
            )
            if action_outcome is not None else world
        )
        with self._lock:
            if self._episode is None:
                raise RuntimeError("causal deliberation has no active episode")
            self._synchronize(self._evidence_for(
                action_cycle=action_cycle,
                admitted_evidence=admitted_evidence,
            ))
            episode = self._episode
            relation = self._relations.get(episode.relation_id)
            if relation is None or relation.status == "revoked":
                with self._atomic():
                    return self._stop(
                        world=world,
                        reason="action_unknown",
                        episode_id=episode.episode_id,
                        depth=episode.depth,
                    )
            verified_receipts = {
                item.settlement_receipt_sha256 for item in relation.outcomes
            }
            if outcome_world.settlement_receipt_sha256 not in verified_receipts:
                with self._atomic():
                    return self._stop(
                        world=world,
                        reason="outcome_unverified",
                        episode_id=episode.episode_id,
                        depth=episode.depth,
                    )
            if outcome_world.structural_fingerprint != (
                episode.expected_outcome.structural_fingerprint
            ):
                with self._atomic():
                    return self._stop(
                        world=world,
                        reason="outcome_mismatch",
                        episode_id=episode.episode_id,
                        depth=episode.depth,
                    )
            if world.structural_fingerprint in (
                episode.visited_structural_fingerprints
            ):
                with self._atomic():
                    return self._stop(
                        world=world,
                        reason="recurrence",
                        episode_id=episode.episode_id,
                        depth=episode.depth,
                    )
            if len(episode.visited_structural_fingerprints) >= (
                self._visited_capacity
            ):
                with self._atomic():
                    return self._stop(
                        world=world,
                        reason="visited_capacity",
                        episode_id=episode.episode_id,
                        depth=episode.depth,
                    )
            visited = (
                *episode.visited_structural_fingerprints,
                world.structural_fingerprint,
            )
            with self._atomic():
                return self._choose(
                    world=world,
                    episode_id=episode.episode_id,
                    visited=visited,
                )

    def current_turn(self) -> DeliberationTurn | None:
        """Return the exact active turn without selecting or mutating."""

        with self._lock:
            if self._episode is None:
                return None
            relation = self._relations.get(self._episode.relation_id)
            if relation is None:
                raise ValueError("active deliberation lost its relation")
            return DeliberationTurn(
                status="action",
                episode_id=self._episode.episode_id,
                depth=self._episode.depth,
                action=relation.action,
                expected_outcome=self._episode.expected_outcome,
                binding_id=relation.binding_id,
                relation_id=relation.relation_id,
                action_receipt_sha256=(
                    relation.action.authority_receipt_sha256
                ),
            )

    def active_episode_record(self) -> dict[str, object] | None:
        """Return a verified copy of the active episode for restore checks."""

        with self._lock:
            if self._episode is None:
                return None
            self._episode.verify(
                max_bytes=self._max_witness_bytes,
                visited_capacity=self._visited_capacity,
            )
            return dict(self._episode.as_record())

    def terminate_active(
        self,
        *,
        reason: str,
        evidence_receipt_sha256: str,
    ) -> DeliberationTurn:
        """Fail closed from an authenticated dispatcher or restore result."""

        sha256_digest(
            evidence_receipt_sha256,
            "deliberation terminal evidence",
        )
        if reason not in {
            "dispatcher_rejected",
            "dispatch_identity_mismatch",
            "restore_evidence_mismatch",
        }:
            raise ValueError("external deliberation terminal reason changed")
        with self._lock:
            if self._episode is None:
                raise RuntimeError("causal deliberation has no active episode")
            episode = self._episode
            with self._atomic():
                terminal = DeliberationTerminal(
                    world_structural_fingerprint=(
                        episode.current.structural_fingerprint
                    ),
                    relation_state_sha256=self._relation_state_sha256(),
                    reason=reason,
                    evidence_receipt_sha256=evidence_receipt_sha256,
                )
                terminal.verify()
                self._episode = None
                self._terminal = terminal
                return DeliberationTurn(
                    status="stopped",
                    episode_id=episode.episode_id,
                    depth=episode.depth,
                    stop_reason=reason,
                )

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded_locked()
        return {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(self._key, payload),
        }

    def restore_encoded(self, value: object) -> None:
        if (
            not isinstance(value, Mapping)
            or set(value)
            != {"payload_base64", "schema", "state_hmac_sha256"}
            or value.get("schema") != ENVELOPE_SCHEMA
        ):
            raise ValueError("causal deliberation envelope is malformed")
        try:
            payload = base64.b64decode(value.get("payload_base64"), validate=True)
        except Exception as error:
            raise ValueError("causal deliberation state is not base64") from error
        if (
            not payload
            or len(payload) > self._encoded_state_capacity
            or base64.b64encode(payload).decode("ascii")
            != value.get("payload_base64")
            or not hmac.compare_digest(
                _sign(self._key, payload), value.get("state_hmac_sha256", "")
            )
        ):
            raise ValueError("causal deliberation state authority changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("causal deliberation state is invalid") from error
        expected = {"capacities", "episode", "relations", "schema", "terminal"}
        restored_capacities = (
            decoded.get("capacities")
            if isinstance(decoded, Mapping)
            else None
        )
        legacy_capacities = self._capacities()
        legacy_capacities["max_witness_bytes"] = (
            LEGACY_MAX_WITNESS_BYTES
        )
        migrating_legacy_witness_boundary = (
            self._max_witness_bytes == DEFAULT_MAX_WITNESS_BYTES
            and restored_capacities == legacy_capacities
        )
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or set(decoded) != expected
            or decoded.get("schema") != STATE_SCHEMA
            or (
                restored_capacities != self._capacities()
                and not migrating_legacy_witness_boundary
            )
            or not isinstance(decoded.get("relations"), list)
            or len(decoded["relations"]) > self._relation_capacity
        ):
            raise ValueError("causal deliberation state fields changed")
        relations: OrderedDict[str, DeliberationRelation] = OrderedDict()
        for record in decoded["relations"]:
            relation = _relation_from(record, max_bytes=self._max_witness_bytes)
            if relation.relation_id in relations:
                raise ValueError("causal deliberation repeats a relation")
            relations[relation.relation_id] = relation
        raw_episode = decoded.get("episode")
        episode = None
        if raw_episode is not None:
            fields = {
                "current",
                "depth",
                "episode_id",
                "expected_outcome",
                "relation_id",
                "schema",
                "visited_structural_fingerprints",
            }
            if (
                not isinstance(raw_episode, Mapping)
                or set(raw_episode) != fields
                or raw_episode.get("schema") != EPISODE_SCHEMA
                or not isinstance(
                    raw_episode.get("visited_structural_fingerprints"), list
                )
            ):
                raise ValueError("causal deliberation episode fields changed")
            episode = DeliberationEpisode(
                episode_id=raw_episode.get("episode_id"),
                current=_witness_from(
                    raw_episode.get("current"), max_bytes=self._max_witness_bytes
                ),
                relation_id=raw_episode.get("relation_id"),
                expected_outcome=_witness_from(
                    raw_episode.get("expected_outcome"),
                    max_bytes=self._max_witness_bytes,
                ),
                visited_structural_fingerprints=tuple(
                    raw_episode.get("visited_structural_fingerprints")
                ),
                depth=raw_episode.get("depth"),
            )
            episode.verify(
                max_bytes=self._max_witness_bytes,
                visited_capacity=self._visited_capacity,
            )
            relation = relations.get(episode.relation_id)
            if (
                relation is None
                or len(relation.outcomes) != 1
                or relation.trigger.structural_fingerprint
                != episode.current.structural_fingerprint
                or relation.outcomes[0].structural_fingerprint
                != episode.expected_outcome.structural_fingerprint
            ):
                raise ValueError("causal deliberation episode lost relation authority")
        raw_terminal = decoded.get("terminal")
        terminal = None
        if raw_terminal is not None:
            fields = {
                "evidence_receipt_sha256",
                "reason",
                "relation_state_sha256",
                "schema",
                "world_structural_fingerprint",
            }
            if (
                not isinstance(raw_terminal, Mapping)
                or set(raw_terminal) != fields
                or raw_terminal.get("schema") != TERMINAL_SCHEMA
            ):
                raise ValueError("causal deliberation terminal fields changed")
            terminal = DeliberationTerminal(
                world_structural_fingerprint=raw_terminal.get(
                    "world_structural_fingerprint"
                ),
                relation_state_sha256=raw_terminal.get("relation_state_sha256"),
                reason=raw_terminal.get("reason"),
                evidence_receipt_sha256=raw_terminal.get(
                    "evidence_receipt_sha256"
                ),
            )
            terminal.verify()
        if episode is not None and terminal is not None:
            raise ValueError("causal deliberation has two live owners")
        with self._lock:
            prior = (
                self._relations,
                self._by_structure,
                self._episode,
                self._terminal,
            )
            self._relations = relations
            self._reindex()
            self._episode = episode
            self._terminal = terminal
            try:
                expected_payload = payload
                if migrating_legacy_witness_boundary:
                    migrated = dict(decoded)
                    migrated["capacities"] = self._capacities()
                    expected_payload = _canonical(migrated)
                if self._encoded_locked() != expected_payload:
                    raise ValueError("causal deliberation state is not canonical")
            except BaseException:
                (
                    self._relations,
                    self._by_structure,
                    self._episode,
                    self._terminal,
                ) = prior
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active_episode": self._episode is not None,
                "ambiguous_relations": sum(
                    len(item.outcomes) == MAX_OUTCOMES_PER_RELATION
                    for item in self._relations.values()
                ),
                "encoded_state_bytes": len(self._encoded_locked()),
                "relations": len(self._relations),
                "retained_outcomes": sum(
                    len(item.outcomes) for item in self._relations.values()
                ),
                "terminal_reason": (
                    self._terminal.reason if self._terminal else None
                ),
                "episode_id": (
                    self._episode.episode_id if self._episode else None
                ),
                "depth": self._episode.depth if self._episode else 0,
                "binding_id": (
                    self.current_turn().binding_id if self._episode else None
                ),
                "action_receipt_sha256": (
                    self.current_turn().action_receipt_sha256
                    if self._episode else None
                ),
                "visited": (
                    len(self._episode.visited_structural_fingerprints)
                    if self._episode
                    else 0
                ),
            }


__all__ = (
    "CausalDeliberation",
    "DeliberationEpisode",
    "DeliberationRelation",
    "DeliberationTerminal",
    "DeliberationTurn",
    "DeliberationWitness",
    "MAX_OUTCOMES_PER_RELATION",
    "MAX_RELATIONS",
)
