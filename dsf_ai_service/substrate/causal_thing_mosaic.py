"""New bounded THING mosaics from authenticated causal entity encounters.

The causal settlement is a whole scene.  It is never used to infer which
field roots belong to an entity.  A mosaic can mutate only through a typed
``ThingEncounterPartition`` whose authority proves one exact physical entity
continued from the prior encounter.

The first production partition authority implemented here is W1 contact.  It
uses the authenticated reciprocal hold relation and the exact before/after
world chain to partition the touch field without exposing the world's control
object id.  The object's control id is used only inside an HMAC continuity
proof; it never becomes the THING id, a route, or retained sensory content.

Every encountered sensory substream retains its complete explicit
D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k tuples and source receipts.  Sensory
roots may retrieve candidate mosaics, but cannot create, extend, select, or
merge them.  There are no scores, thresholds, similarities, labels, chi
identities, evictions, or reduced vectors.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactSenseInterpretation,
    ExactSubstreamInterpretation,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodiedSensoryOutcome,
    EmbodimentSensoryOutcomeAuthority,
)


PROFILE_SCHEMA = "guala.causal_thing_mosaic.profile.v1"
ROOT_SCHEMA = "guala.causal_thing_mosaic.full_field_root.v2"
PARTITION_SCHEMA = "guala.causal_thing_mosaic.encounter_partition.v1"
MOSAIC_SCHEMA = "guala.causal_thing_mosaic.v1"
STATE_SCHEMA = "guala.causal_thing_mosaic.state.v1"
ENVELOPE_SCHEMA = "guala.causal_thing_mosaic.state_hmac.v1"

_PARTITION_DOMAIN = b"guala-thing-encounter-partition-v1\0"
_ENTITY_CONTINUITY_DOMAIN = b"guala-w1-contact-entity-continuity-v1\0"
_MOSAIC_DOMAIN = b"guala-causal-thing-mosaic-v1\0"
_THING_ID_DOMAIN = b"guala-causal-thing-id-v1\0"
_STATE_DOMAIN = b"guala-causal-thing-mosaic-state-v1\0"
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


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class CausalThingMosaicProfile:
    profile_id: str
    max_mosaics: int
    max_partitions_per_mosaic: int
    max_roots_per_partition: int
    max_routes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_mosaics: int,
        max_partitions_per_mosaic: int,
        max_roots_per_partition: int,
        max_routes: int,
        max_state_bytes: int,
    ) -> "CausalThingMosaicProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError("THING mosaic profile id changed")
        provisional = cls(
            profile_id=profile_id,
            max_mosaics=_positive(max_mosaics, "mosaic capacity"),
            max_partitions_per_mosaic=_positive(
                max_partitions_per_mosaic, "partition capacity"
            ),
            max_roots_per_partition=_positive(
                max_roots_per_partition, "root capacity"
            ),
            max_routes=_positive(max_routes, "route capacity"),
            max_state_bytes=_positive(max_state_bytes, "state capacity"),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            **{
                field: getattr(provisional, field)
                for field in (
                    "profile_id",
                    "max_mosaics",
                    "max_partitions_per_mosaic",
                    "max_roots_per_partition",
                    "max_routes",
                    "max_state_bytes",
                )
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_mosaics": self.max_mosaics,
            "max_partitions_per_mosaic": self.max_partitions_per_mosaic,
            "max_roots_per_partition": self.max_roots_per_partition,
            "max_routes": self.max_routes,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        for value, label in (
            (self.max_mosaics, "mosaic capacity"),
            (self.max_partitions_per_mosaic, "partition capacity"),
            (self.max_roots_per_partition, "root capacity"),
            (self.max_routes, "route capacity"),
            (self.max_state_bytes, "state capacity"),
        ):
            _positive(value, label)
        _sha(self.authority_receipt_sha256, "profile authority")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("THING mosaic profile authority changed")


@dataclass(frozen=True, slots=True)
class _VerifiedFullFieldSensoryRootIntegrity:
    sense: str
    topology_index: int
    physical_value_sha256: str
    full_evidence_json: str
    evidence: Mapping[str, object] = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def matches(self, root: "FullFieldSensoryRoot") -> bool:
        return (
            self.sense == root.sense
            and self.topology_index == root.topology_index
            and self.physical_value_sha256
            == root.physical_value_sha256
            and self.full_evidence_json == root.full_evidence_json
        )


class _ImmutableEvidenceDict(dict):
    """A JSON-compatible mapping that cannot change after admission."""

    @staticmethod
    def _deny(*_args, **_kwargs):
        raise TypeError("verified sensory evidence is immutable")

    __setitem__ = _deny
    __delitem__ = _deny
    __ior__ = _deny
    clear = _deny
    pop = _deny
    popitem = _deny
    setdefault = _deny
    update = _deny


class _ImmutableEvidenceList(list):
    """A JSON-compatible sequence that cannot change after admission."""

    @staticmethod
    def _deny(*_args, **_kwargs):
        raise TypeError("verified sensory evidence is immutable")

    __setitem__ = _deny
    __delitem__ = _deny
    __iadd__ = _deny
    __imul__ = _deny
    append = _deny
    clear = _deny
    extend = _deny
    insert = _deny
    pop = _deny
    remove = _deny
    reverse = _deny
    sort = _deny


def _immutable_evidence(value: object) -> object:
    if isinstance(value, dict):
        return _ImmutableEvidenceDict({
            key: _immutable_evidence(item)
            for key, item in value.items()
        })
    if isinstance(value, list):
        return _ImmutableEvidenceList(
            _immutable_evidence(item) for item in value
        )
    return value


@dataclass(frozen=True, slots=True)
class FullFieldSensoryRoot:
    sense: str
    topology_index: int
    physical_value_sha256: str
    full_evidence_json: str
    _verified_integrity: (
        _VerifiedFullFieldSensoryRootIntegrity | None
    ) = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    @property
    def route_key(self) -> tuple[str, str]:
        return self.sense, self.physical_value_sha256

    def record(self) -> dict[str, object]:
        return {
            "full_evidence_json": self.full_evidence_json,
            "physical_value_sha256": self.physical_value_sha256,
            "schema": ROOT_SCHEMA,
            "sense": self.sense,
            "topology_index": self.topology_index,
        }

    def verify(self) -> None:
        verified = self._verified_integrity
        if verified is not None:
            if not verified.matches(self):
                raise ValueError(
                    "THING sensory root changed after verified integrity"
                )
            return
        if self.sense not in tuple(value.value for value in SENSE_ORDER):
            raise ValueError("THING sensory root sense changed")
        if (
            isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or self.topology_index < 0
        ):
            raise ValueError("THING sensory root topology changed")
        _sha(self.physical_value_sha256, "THING sensory physical value")
        try:
            evidence = json.loads(self.full_evidence_json)
        except json.JSONDecodeError as error:
            raise ValueError("THING sensory root is unreadable") from error
        if (
            _canonical(evidence).decode("utf-8") != self.full_evidence_json
            or not isinstance(evidence, Mapping)
            or evidence.get("schema") != ROOT_SCHEMA
            or evidence.get("sense") != self.sense
            or evidence.get("topology_index") != self.topology_index
        ):
            raise ValueError("THING sensory root evidence changed")
        tuples = evidence.get("field_tuples")
        if not isinstance(tuples, list) or not tuples:
            raise ValueError("THING sensory root lost its full DSF field")
        for tuple_index, item in enumerate(tuples):
            fields = item.get("fields") if isinstance(item, dict) else None
            if (
                not isinstance(fields, list)
                or item.get("tuple_index") != tuple_index
                or len(fields) != len(DSF_FIELD_ORDER)
                or tuple(
                    pair[0]
                    for pair in fields
                    if isinstance(pair, list) and len(pair) == 2
                )
                != DSF_FIELD_ORDER
            ):
                raise ValueError(
                    "THING sensory root flattened or reordered its DSF field"
                )
            for name, exact in fields:
                if not isinstance(exact, str) or exact.count("/") != 1:
                    raise ValueError(
                        f"THING sensory root {name} is not exact"
                    )
                numerator, denominator = exact.split("/", 1)
                try:
                    value = Fraction(int(numerator), int(denominator))
                except (ValueError, ZeroDivisionError) as error:
                    raise ValueError(
                        f"THING sensory root {name} is not exact"
                    ) from error
                if _fraction_text(value) != exact:
                    raise ValueError(
                        f"THING sensory root {name} is not canonical"
                    )
        if self.sense == "sight":
            _sha(
                evidence.get("source_signal_commitment_sha256"),
                "THING sight source signal commitment",
            )
        elif "source_signal_commitment_sha256" in evidence:
            raise ValueError(
                "nonvisual THING root retained visual source identity"
            )
        physical = _physical_root_relation(evidence)
        if self.physical_value_sha256 != _digest(physical):
            raise ValueError("THING sensory root physical authority changed")
        immutable = _immutable_evidence(evidence)
        if not isinstance(immutable, Mapping):
            raise AssertionError("verified sensory evidence lost its mapping")
        object.__setattr__(
            self,
            "_verified_integrity",
            _VerifiedFullFieldSensoryRootIntegrity(
                sense=self.sense,
                topology_index=self.topology_index,
                physical_value_sha256=self.physical_value_sha256,
                full_evidence_json=self.full_evidence_json,
                evidence=immutable,
            ),
        )

    def verified_evidence(self) -> Mapping[str, object]:
        """Return the one admitted immutable evidence construction."""

        self.verify()
        verified = self._verified_integrity
        if verified is None:
            raise AssertionError("sensory evidence verification disappeared")
        return verified.evidence


def _physical_root_relation(
    evidence: Mapping[str, object],
) -> dict[str, object]:
    """Return the exact sensory relation used for reciprocal routing.

    Canonical L0-L4 is scale-invariant for a static two-sample stream.  A
    retinal stream ``(v, v)`` therefore retains its full seven-field geometry
    while legitimately sharing that geometry with other steady irradiances.
    Sight still needs the exact physical excitation that selected that
    geometry; otherwise different retinal spectra become the same experience.

    The sample commitment is an exact commitment to the native physical
    series, not an object identifier, label, score, or reduced DSF field.  It
    is sight-only so this correction cannot change auditory exposure identity.
    """

    result = {
        "boundary_state": evidence["boundary_state"],
        "field_tuples": [
            {
                "fields": item["fields"],
                "source_index_end": item["source_index_end"],
                "source_index_start": item["source_index_start"],
                "tuple_index": item["tuple_index"],
            }
            for item in evidence["field_tuples"]
        ],
        "physical_quantity": evidence["physical_quantity"],
        "physical_unit": evidence["physical_unit"],
        "sense": evidence["sense"],
        "source_sample_count": evidence["source_sample_count"],
        "topology_index": evidence["topology_index"],
    }
    if evidence["sense"] == "sight":
        result["source_signal_commitment_sha256"] = evidence[
            "source_signal_commitment_sha256"
        ]
    return result


def _root(
    interpretation: ExactSenseInterpretation,
    substream: ExactSubstreamInterpretation,
) -> FullFieldSensoryRoot:
    evidence = {
        "boundary_state": interpretation.state,
        "boundary_receipt_sha256": interpretation.boundary_receipt_sha256,
        "coordinates": [list(value) for value in substream.coordinates],
        "field_tuples": [
            {
                "authority_receipt_sha256": item.authority_receipt_sha256,
                "fields": [
                    [name, _fraction_text(field)]
                    for name, field in item.fields
                ],
                "source_index_end": item.source_index_end,
                "source_index_start": item.source_index_start,
                "source_l0_l4_trace_receipt_sha256": (
                    item.source_l0_l4_trace_receipt_sha256
                ),
                "tuple_index": item.tuple_index,
            }
            for item in substream.field_tuples
        ],
        "kernel_basin_receipt_sha256": substream.kernel_basin_receipt_sha256,
        "physical_quantity": substream.physical_quantity,
        "physical_unit": substream.physical_unit,
        "profile_receipt_sha256": substream.profile_receipt_sha256,
        "schema": ROOT_SCHEMA,
        "sense": interpretation.sense,
        "sensor_id": substream.sensor_id,
        "source_evidence_stream_receipt_sha256": (
            substream.source_evidence_stream_receipt_sha256
        ),
        "source_sample_commitment_sha256": (
            substream.source_sample_commitment_sha256
        ),
        **({
            "source_signal_commitment_sha256": (
                substream.source_signal_commitment_sha256
            ),
        } if interpretation.sense == "sight" else {}),
        "source_sample_count": substream.source_sample_count,
        "structural_fingerprint": interpretation.structural_fingerprint,
        "substream_id": substream.substream_id,
        "topology_index": substream.topology_index,
        "topology_receipt_sha256": interpretation.topology_receipt_sha256,
    }
    physical = _physical_root_relation(evidence)
    result = FullFieldSensoryRoot(
        sense=interpretation.sense,
        topology_index=substream.topology_index,
        physical_value_sha256=_digest(physical),
        full_evidence_json=_canonical(evidence).decode("utf-8"),
    )
    result.verify()
    return result


def full_field_sensory_roots(
    settlement: CausalExperienceSettlement,
) -> tuple[FullFieldSensoryRoot, ...]:
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError("THING roots require an exact causal settlement")
    cached = settlement._shared_full_field_roots
    if cached is not None:
        return cached
    settlement.verify()
    roots = tuple(
        _root(interpretation, substream)
        for interpretation in settlement.interpretations
        if interpretation.state == "observed"
        for substream in interpretation.substreams
    )
    if not roots:
        raise ValueError("THING encounter has no observed sensory field")
    if len({value.route_key for value in roots}) != len(roots):
        raise ValueError("THING encounter repeats a physical sensory root")
    object.__setattr__(settlement, "_shared_full_field_roots", roots)
    return roots


@dataclass(frozen=True, slots=True)
class ThingEncounterPartition:
    source_occurrence_id: str | None
    parent_custody_receipt_sha256: str | None
    thing_custody_capability_receipt_sha256: str | None
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    world_observation_receipt_sha256: str
    execution_receipt_sha256: str | None
    world_revision: int
    entity_continuity_hmac_sha256: str
    prior_partition_receipt_sha256: str | None
    entity_root_keys: tuple[tuple[str, str], ...]
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    physical_surface_observation_receipt_sha256: str | None = None

    def payload(self) -> dict[str, object]:
        payload = {
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "thing_custody_capability_receipt_sha256": (
                self.thing_custody_capability_receipt_sha256
            ),
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "entity_root_keys": [list(value) for value in self.entity_root_keys],
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "full_field_roots": [
                value.record() for value in self.full_field_roots
            ],
            "prior_partition_receipt_sha256": (
                self.prior_partition_receipt_sha256
            ),
            "schema": PARTITION_SCHEMA,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }
        if self.physical_surface_observation_receipt_sha256 is not None:
            payload["physical_surface_observation_receipt_sha256"] = (
                self.physical_surface_observation_receipt_sha256
            )
        return payload

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class W1ContactThingEncounterAuthority:
    """Partitions one causally contacted W1 entity from a full-field settlement."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        sensory_authority: EmbodimentSensoryOutcomeAuthority,
        max_roots_per_partition: int,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("THING partition requires the W1 world authority")
        if not isinstance(
            sensory_authority, EmbodimentSensoryOutcomeAuthority
        ):
            raise TypeError(
                "THING partition requires the W1 sensory authority"
            )
        root = _key(authority_key, "THING encounter partition")
        self._partition_key = hashlib.sha256(
            _PARTITION_DOMAIN + root
        ).digest()
        self._continuity_key = hashlib.sha256(
            _ENTITY_CONTINUITY_DOMAIN + root
        ).digest()
        self._world = world_authority
        self._sensory = sensory_authority
        self._max_roots = _positive(
            max_roots_per_partition,
            "THING partition root capacity",
        )

    @staticmethod
    def _held_object_id(observation: ObservationSnapshot) -> str | None:
        held = tuple(
            value.object_id
            for value in observation.objects
            if value.held_by_body_id == observation.self_body_id
        )
        if len(held) > 1:
            raise ValueError("W1 reciprocal hold relation is not unique")
        return held[0] if held else None

    @classmethod
    def _contact_object_id(
        cls,
        observation: ObservationSnapshot,
    ) -> str | None:
        """Resolve one reciprocal hold, touch, or oral contact."""

        held = cls._held_object_id(observation)
        self_body = next(
            value
            for value in observation.bodies
            if value.body_id == observation.self_body_id
        )
        contacted = (
            self_body.active_contact.object_id
            if self_body.active_contact is not None
            else None
        )
        identities = {
            value for value in (held, contacted) if value is not None
        }
        if len(identities) > 1:
            raise ValueError(
                "W1 reciprocal physical contact is not unique"
            )
        if identities and not any(
            value.object_id in identities
            for value in observation.objects
        ):
            raise ValueError(
                "W1 reciprocal physical contact object is absent"
            )
        return next(iter(identities), None)

    def _entity_continuity(self, object_id: str) -> str:
        return hmac.new(
            self._continuity_key,
            _ENTITY_CONTINUITY_DOMAIN + object_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def held_entity_continuity(
        self,
        observation: ObservationSnapshot,
    ) -> str | None:
        """Return only the authenticated continuity HMAC, never object identity."""

        self._world.verify_observation_snapshot(observation)
        object_id = self._held_object_id(observation)
        return (
            None
            if object_id is None
            else self._entity_continuity(object_id)
        )

    def contacted_entity_continuity(
        self,
        observation: ObservationSnapshot,
    ) -> str | None:
        """Return one authenticated physical-contact continuity HMAC."""

        self._world.verify_observation_snapshot(observation)
        object_id = self._contact_object_id(observation)
        return (
            None
            if object_id is None
            else self._entity_continuity(object_id)
        )

    def verify(self, value: ThingEncounterPartition) -> None:
        if not isinstance(value, ThingEncounterPartition):
            raise TypeError("THING encounter partition is not typed")
        for digest, label in (
            (value.settlement_receipt_sha256, "partition settlement"),
            (
                value.settlement_structural_fingerprint,
                "partition structural fingerprint",
            ),
            (
                value.world_observation_receipt_sha256,
                "partition world observation",
            ),
            (value.execution_receipt_sha256, "partition execution"),
            (
                value.entity_continuity_hmac_sha256,
                "partition physical continuity",
            ),
            (value.authority_hmac_sha256, "partition HMAC"),
            (value.authority_receipt_sha256, "partition authority"),
        ):
            _sha(digest, label)
        if value.prior_partition_receipt_sha256 is not None:
            _sha(
                value.prior_partition_receipt_sha256,
                "prior partition authority",
            )
        custody_values = (
            value.source_occurrence_id,
            value.parent_custody_receipt_sha256,
            value.thing_custody_capability_receipt_sha256,
        )
        if any(item is not None for item in custody_values):
            if any(item is None for item in custody_values):
                raise ValueError(
                    "THING partition split settled custody authority"
                )
            for digest, label in zip(
                custody_values,
                (
                    "partition source occurrence",
                    "partition parent custody",
                    "partition THING custody capability",
                ),
            ):
                _sha(digest, label)
        if (
            isinstance(value.world_revision, bool)
            or not isinstance(value.world_revision, int)
            or value.world_revision <= 0
            or not value.full_field_roots
            or len(value.full_field_roots) > self._max_roots
        ):
            raise ValueError("THING encounter partition extent changed")
        all_keys = set()
        for root in value.full_field_roots:
            root.verify()
            all_keys.add(root.route_key)
        if (
            not value.entity_root_keys
            or value.entity_root_keys
            != tuple(sorted(set(value.entity_root_keys)))
            or any(key not in all_keys for key in value.entity_root_keys)
            or any(key[0] != "touch" for key in value.entity_root_keys)
        ):
            raise ValueError("THING contact partition roots changed")
        payload = value.payload()
        signature = hmac.new(
            self._partition_key,
            _PARTITION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(signature, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("THING encounter partition authority changed")

    def partition(
        self,
        *,
        outcome: EmbodiedSensoryOutcome,
        observation: ObservationSnapshot,
        execution: ActionExecutionReceipt,
        prior: ThingEncounterPartition | None = None,
    ) -> ThingEncounterPartition:
        if not isinstance(outcome, EmbodiedSensoryOutcome):
            raise TypeError("THING partition requires a sensory outcome")
        self._world.verify_observation_snapshot(observation)
        self._world.verify_execution_receipt(execution)
        self._sensory.verify_outcome_observation_receipt(
            outcome.observation_receipt
        )
        outcome.causal_settlement.verify()
        if (
            execution.after != observation
            or outcome.observation_receipt.world_observation_receipt_sha256
            != observation.authority_receipt_sha256
            or outcome.observation_receipt.execution_receipt_sha256
            != execution.authority_receipt_sha256
        ):
            raise ValueError("THING partition crossed physical authorities")
        contact_after = self._contact_object_id(execution.after)
        contact_before = self._contact_object_id(execution.before)
        if contact_after is None:
            raise ValueError(
                "THING contact partition has no contacted entity"
            )
        continuity = self._entity_continuity(contact_after)
        if prior is None:
            if contact_before is not None:
                raise ValueError(
                    "THING genesis lacks a new reciprocal contact transition"
                )
            prior_receipt = None
        else:
            self.verify(prior)
            if (
                contact_before != contact_after
                or continuity != prior.entity_continuity_hmac_sha256
                or prior.world_revision != execution.before.revision
                or prior.world_observation_receipt_sha256
                != execution.before.authority_receipt_sha256
            ):
                raise ValueError(
                    "THING continuation left its exact physical chain"
                )
            prior_receipt = prior.authority_receipt_sha256
        roots = full_field_sensory_roots(outcome.causal_settlement)
        if len(roots) > self._max_roots:
            raise RuntimeError("THING partition root capacity exhausted")
        entity_keys = tuple(sorted(
            root.route_key for root in roots if root.sense == "touch"
        ))
        provisional = ThingEncounterPartition(
            source_occurrence_id=None,
            parent_custody_receipt_sha256=None,
            thing_custody_capability_receipt_sha256=None,
            settlement_receipt_sha256=(
                outcome.causal_settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                outcome.causal_settlement.structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            execution_receipt_sha256=execution.authority_receipt_sha256,
            world_revision=observation.revision,
            entity_continuity_hmac_sha256=continuity,
            prior_partition_receipt_sha256=prior_receipt,
            entity_root_keys=entity_keys,
            full_field_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._partition_key,
            _PARTITION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = ThingEncounterPartition(
            **{
                field: getattr(provisional, field)
                for field in (
                    "settlement_receipt_sha256",
                    "source_occurrence_id",
                    "parent_custody_receipt_sha256",
                    "thing_custody_capability_receipt_sha256",
                    "settlement_structural_fingerprint",
                    "world_observation_receipt_sha256",
                    "execution_receipt_sha256",
                    "world_revision",
                    "entity_continuity_hmac_sha256",
                    "prior_partition_receipt_sha256",
                    "entity_root_keys",
                    "full_field_roots",
                )
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(result)
        return result


@dataclass(frozen=True, slots=True)
class CausalThingMosaic:
    thing_id: str
    version: int
    partitions: tuple[ThingEncounterPartition, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "partitions": [value.record() for value in self.partitions],
            "schema": MOSAIC_SCHEMA,
            "thing_id": self.thing_id,
            "version": self.version,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalThingRoute:
    state: str
    thing_ids: tuple[str, ...]
    matching_route_keys: tuple[tuple[str, str], ...]


@dataclass(slots=True)
class _OrderedContinuationTransactionState:
    phase: str


@dataclass(slots=True)
class _GenesisAdmissionTransactionState:
    phase: str


_PREPARED_GENESIS_ADMISSION_AUTHORITY = object()
_GENESIS_ADMISSION_UNDO_AUTHORITY = object()
_PREPARED_ORDERED_CONTINUATION_AUTHORITY = object()
_ORDERED_CONTINUATION_UNDO_AUTHORITY = object()
_PREPARED_PHYSICAL_SURFACE_CONTINUATION_AUTHORITY = object()
_PHYSICAL_SURFACE_CONTINUATION_UNDO_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreparedCausalThingMosaicGenesis:
    partition: ThingEncounterPartition
    staged_mosaic: CausalThingMosaic
    _prior_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _staged_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _transaction_state: _GenesisAdmissionTransactionState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CausalThingMosaicGenesisUndo:
    _prepared: PreparedCausalThingMosaicGenesis = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PreparedCausalThingMosaicContinuation:
    partitions: tuple[ThingEncounterPartition, ...]
    staged_mosaic: CausalThingMosaic
    _prior_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _staged_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _transaction_state: _OrderedContinuationTransactionState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CausalThingMosaicContinuationUndo:
    _prepared: PreparedCausalThingMosaicContinuation = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PreparedPhysicalSurfaceContinuation:
    partition: ThingEncounterPartition
    staged_mosaic: CausalThingMosaic
    _prior_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _staged_mosaics: tuple[tuple[str, CausalThingMosaic], ...] = field(
        repr=False,
    )
    _transaction_state: _OrderedContinuationTransactionState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceContinuationUndo:
    _prepared: PreparedPhysicalSurfaceContinuation = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class CausalThingMosaicOwner:
    """Owns stable THING identity; only partition chains may mutate it."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CausalThingMosaicProfile,
        partition_authority: W1ContactThingEncounterAuthority,
    ) -> None:
        profile.verify()
        if not isinstance(
            partition_authority, W1ContactThingEncounterAuthority
        ):
            raise TypeError("THING mosaic requires its partition authority")
        root = _key(authority_key, "causal THING mosaic")
        self._mosaic_key = hashlib.sha256(_MOSAIC_DOMAIN + root).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._partition_authority = partition_authority
        self._mosaics: dict[str, CausalThingMosaic] = {}
        self._genesis_admission_authority = object()
        self._ordered_continuation_authority = object()
        self._physical_surface_continuation_authority = object()
        self._lock = threading.RLock()

    @property
    def mosaics(self) -> tuple[CausalThingMosaic, ...]:
        with self._lock:
            return tuple(self._mosaics[key] for key in sorted(self._mosaics))

    def materialize_retained_prefix(
        self,
        *,
        thing_id: str,
        terminal_partition_receipt_sha256: str,
    ) -> CausalThingMosaic:
        """Return one authenticated historical prefix of a retained THING."""

        _sha(thing_id, "retained THING identity")
        _sha(
            terminal_partition_receipt_sha256,
            "retained terminal partition",
        )
        with self._lock:
            mosaic = self._mosaics.get(thing_id)
            if mosaic is None:
                raise ValueError(
                    "historical mosaic prefix names no retained THING"
                )
            indexes = tuple(
                index
                for index, partition in enumerate(mosaic.partitions)
                if partition.authority_receipt_sha256
                == terminal_partition_receipt_sha256
            )
            if len(indexes) != 1:
                raise ValueError(
                    "historical mosaic prefix has no unique terminal partition"
                )
            terminal_index = indexes[0]
            partitions = mosaic.partitions[: terminal_index + 1]
            for index, partition in enumerate(partitions):
                self._partition_authority.verify(partition)
                expected_prior = (
                    None
                    if index == 0
                    else partitions[index - 1].authority_receipt_sha256
                )
                if partition.prior_partition_receipt_sha256 != expected_prior:
                    raise ValueError(
                        "historical mosaic prefix crossed partition custody"
                    )
            prefix = self._seal(
                thing_id=thing_id,
                version=terminal_index,
                partitions=partitions,
            )
            if (
                terminal_index == mosaic.version
                and prefix.authority_receipt_sha256
                != mosaic.authority_receipt_sha256
            ):
                raise ValueError(
                    "historical mosaic prefix changed current authority"
                )
            return prefix

    def _seal(
        self,
        *,
        thing_id: str,
        version: int,
        partitions: tuple[ThingEncounterPartition, ...],
    ) -> CausalThingMosaic:
        provisional = CausalThingMosaic(
            thing_id=thing_id,
            version=version,
            partitions=partitions,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._mosaic_key,
            _MOSAIC_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalThingMosaic(
            thing_id=thing_id,
            version=version,
            partitions=partitions,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _routes(
        self, mosaics: Mapping[str, CausalThingMosaic]
    ) -> dict[tuple[str, str], set[str]]:
        routes: dict[tuple[str, str], set[str]] = {}
        for thing_id, mosaic in mosaics.items():
            for partition in mosaic.partitions:
                for root in partition.full_field_roots:
                    routes.setdefault(root.route_key, set()).add(thing_id)
        if len(routes) > self._profile.max_routes:
            raise RuntimeError("THING mosaic route capacity exhausted")
        return routes

    @staticmethod
    def _require_authoritative_genesis(
        partition: ThingEncounterPartition,
    ) -> None:
        if partition.prior_partition_receipt_sha256 is not None:
            raise ValueError(
                "THING genesis cannot continue a retained mosaic"
            )
        custody = (
            partition.source_occurrence_id,
            partition.parent_custody_receipt_sha256,
            partition.thing_custody_capability_receipt_sha256,
        )
        custody_complete = all(value is not None for value in custody)
        custody_absent = all(value is None for value in custody)
        physical_surface = (
            partition.physical_surface_observation_receipt_sha256
            is not None
        )
        if (
            (not custody_complete and not custody_absent)
            or custody_complete == physical_surface
        ):
            raise ValueError(
                "THING genesis requires exactly one physical authority"
            )

    def _stage_custody_genesis_locked(
        self,
        partition: ThingEncounterPartition,
    ) -> tuple[
        dict[str, CausalThingMosaic],
        dict[str, CausalThingMosaic],
        CausalThingMosaic,
    ]:
        self._partition_authority.verify(partition)
        self._require_authoritative_genesis(partition)
        if len(self._mosaics) >= self._profile.max_mosaics:
            raise RuntimeError("THING mosaic capacity exhausted")

        retained_partitions = tuple(
            value
            for mosaic in self._mosaics.values()
            for value in mosaic.partitions
        )
        if any(
            (
                value.authority_receipt_sha256
                == partition.authority_receipt_sha256
                or (
                    partition.source_occurrence_id is not None
                    and value.source_occurrence_id
                    == partition.source_occurrence_id
                )
                or (
                    partition.thing_custody_capability_receipt_sha256
                    is not None
                    and value.thing_custody_capability_receipt_sha256
                    == partition.thing_custody_capability_receipt_sha256
                )
            )
            for value in retained_partitions
        ):
            raise ValueError(
                "THING genesis replays retained authenticated evidence"
            )
        if any(
            value.entity_continuity_hmac_sha256
            == partition.entity_continuity_hmac_sha256
            for value in retained_partitions
        ):
            raise ValueError(
                "THING genesis repeats retained physical continuity"
            )

        thing_id = hmac.new(
            self._mosaic_key,
            _THING_ID_DOMAIN
            + bytes.fromhex(partition.authority_receipt_sha256),
            hashlib.sha256,
        ).hexdigest()
        if thing_id in self._mosaics:
            raise ValueError("THING custody genesis identity already exists")
        updated = self._seal(
            thing_id=thing_id,
            version=0,
            partitions=(partition,),
        )
        prior_mosaics = dict(self._mosaics)
        staged_mosaics = dict(prior_mosaics)
        staged_mosaics[thing_id] = updated
        self._routes(staged_mosaics)
        self._encoded(staged_mosaics)
        return prior_mosaics, staged_mosaics, updated

    def prepare_custody_genesis_admission(
        self,
        partition: ThingEncounterPartition,
    ) -> PreparedCausalThingMosaicGenesis:
        """Preflight one custody-derived first contact without mutation."""

        with self._lock:
            prior, staged, updated = self._stage_custody_genesis_locked(
                partition
            )
            return PreparedCausalThingMosaicGenesis(
                partition=partition,
                staged_mosaic=updated,
                _prior_mosaics=self._mosaic_items(prior),
                _staged_mosaics=self._mosaic_items(staged),
                _transaction_state=_GenesisAdmissionTransactionState(
                    phase="prepared"
                ),
                _owner_authority=self._genesis_admission_authority,
                _construction_authority=(
                    _PREPARED_GENESIS_ADMISSION_AUTHORITY
                ),
            )

    def prepare_physical_surface_genesis_admission(
        self,
        partition: ThingEncounterPartition,
    ) -> PreparedCausalThingMosaicGenesis:
        """Preflight first physical continuity from authenticated foveation."""

        if partition.physical_surface_observation_receipt_sha256 is None:
            raise ValueError("physical surface genesis lacks foveal custody")
        return self.prepare_custody_genesis_admission(partition)


    def _verify_prepared_custody_genesis_locked(
        self,
        prepared: PreparedCausalThingMosaicGenesis,
        *,
        require_current: bool,
    ) -> None:
        if (
            not isinstance(prepared, PreparedCausalThingMosaicGenesis)
            or prepared._construction_authority
            is not _PREPARED_GENESIS_ADMISSION_AUTHORITY
            or prepared._owner_authority
            is not self._genesis_admission_authority
            or prepared._transaction_state.phase != "prepared"
        ):
            raise ValueError(
                "prepared THING custody genesis changed custody"
            )
        prior = dict(prepared._prior_mosaics)
        staged = dict(prepared._staged_mosaics)
        if (
            len(prior) != len(prepared._prior_mosaics)
            or len(staged) != len(prepared._staged_mosaics)
            or len(staged) != len(prior) + 1
            or prepared.staged_mosaic.thing_id in prior
            or staged.get(prepared.staged_mosaic.thing_id)
            != prepared.staged_mosaic
            or prepared.staged_mosaic.version != 0
            or prepared.staged_mosaic.partitions
            != (prepared.partition,)
        ):
            raise ValueError(
                "prepared THING custody genesis changed state"
            )
        self._partition_authority.verify(prepared.partition)
        self._require_authoritative_genesis(prepared.partition)
        expected_thing_id = hmac.new(
            self._mosaic_key,
            _THING_ID_DOMAIN
            + bytes.fromhex(
                prepared.partition.authority_receipt_sha256
            ),
            hashlib.sha256,
        ).hexdigest()
        expected_mosaic = self._seal(
            thing_id=expected_thing_id,
            version=0,
            partitions=(prepared.partition,),
        )
        if (
            expected_thing_id != prepared.staged_mosaic.thing_id
            or expected_mosaic != prepared.staged_mosaic
        ):
            raise ValueError(
                "prepared THING custody genesis changed staging"
            )
        self._routes(prior)
        self._routes(staged)
        self._encoded(prior)
        self._encoded(staged)
        if require_current:
            if self._mosaics != prior:
                raise RuntimeError(
                    "prepared THING custody genesis is stale"
                )
            expected_prior, expected_staged, current_mosaic = (
                self._stage_custody_genesis_locked(
                    prepared.partition
                )
            )
            if (
                expected_prior != prior
                or expected_staged != staged
                or current_mosaic != prepared.staged_mosaic
            ):
                raise ValueError(
                    "prepared THING custody genesis changed staging"
                )

    def verify_prepared_custody_genesis_admission(
        self,
        prepared: PreparedCausalThingMosaicGenesis,
    ) -> None:
        with self._lock:
            self._verify_prepared_custody_genesis_locked(
                prepared,
                require_current=True,
            )

    def commit_prepared_custody_genesis_admission(
        self,
        prepared: PreparedCausalThingMosaicGenesis,
    ) -> CausalThingMosaicGenesisUndo:
        """Publish one preflighted first contact exactly once."""

        with self._lock:
            self._verify_prepared_custody_genesis_locked(
                prepared,
                require_current=True,
            )
            self._mosaics = dict(prepared._staged_mosaics)
            prepared._transaction_state.phase = "committed"
            return CausalThingMosaicGenesisUndo(
                _prepared=prepared,
                _owner_authority=self._genesis_admission_authority,
                _construction_authority=(
                    _GENESIS_ADMISSION_UNDO_AUTHORITY
                ),
            )

    def discard_prepared_custody_genesis_admission(
        self,
        prepared: PreparedCausalThingMosaicGenesis,
    ) -> None:
        """Consume one uncommitted first-contact capability."""

        with self._lock:
            self._verify_prepared_custody_genesis_locked(
                prepared,
                require_current=False,
            )
            prepared._transaction_state.phase = "discarded"

    def rollback_committed_custody_genesis_admission(
        self,
        undo: CausalThingMosaicGenesisUndo,
    ) -> None:
        """Restore exact prior bytes while this genesis is still current."""

        if (
            not isinstance(undo, CausalThingMosaicGenesisUndo)
            or undo._construction_authority
            is not _GENESIS_ADMISSION_UNDO_AUTHORITY
            or undo._owner_authority
            is not self._genesis_admission_authority
        ):
            raise ValueError(
                "THING custody genesis undo changed custody"
            )
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority
                is not self._genesis_admission_authority
                or prepared._transaction_state.phase != "committed"
            ):
                raise ValueError(
                    "THING custody genesis undo changed custody"
                )
            prior = dict(prepared._prior_mosaics)
            staged = dict(prepared._staged_mosaics)
            self._routes(prior)
            self._routes(staged)
            self._encoded(prior)
            self._encoded(staged)
            if self._mosaics != staged:
                raise RuntimeError("THING custody genesis undo is stale")
            self._mosaics = prior
            prepared._transaction_state.phase = "rolled_back"

    def admit_custody_genesis(
        self,
        partition: ThingEncounterPartition,
    ) -> CausalThingMosaic:
        """Atomically preflight and publish one custody-derived first contact."""

        prepared = self.prepare_custody_genesis_admission(partition)
        self.commit_prepared_custody_genesis_admission(prepared)
        return prepared.staged_mosaic

    def admit(self, partition: ThingEncounterPartition) -> CausalThingMosaic:
        self._partition_authority.verify(partition)
        with self._lock:
            if partition.prior_partition_receipt_sha256 is None:
                if len(self._mosaics) >= self._profile.max_mosaics:
                    raise RuntimeError("THING mosaic capacity exhausted")
                if any(
                    value.entity_continuity_hmac_sha256
                    == partition.entity_continuity_hmac_sha256
                    for mosaic in self._mosaics.values()
                    for value in mosaic.partitions
                ):
                    raise ValueError(
                        "THING genesis repeats retained physical continuity"
                    )
                thing_id = hmac.new(
                    self._mosaic_key,
                    _THING_ID_DOMAIN
                    + bytes.fromhex(partition.authority_receipt_sha256),
                    hashlib.sha256,
                ).hexdigest()
                updated = self._seal(
                    thing_id=thing_id,
                    version=0,
                    partitions=(partition,),
                )
            else:
                matches = tuple(
                    mosaic
                    for mosaic in self._mosaics.values()
                    if mosaic.partitions[-1].authority_receipt_sha256
                    == partition.prior_partition_receipt_sha256
                )
                if len(matches) != 1:
                    raise ValueError(
                        "THING continuation does not name one retained mosaic"
                    )
                prior = matches[0]
                if (
                    len(prior.partitions)
                    >= self._profile.max_partitions_per_mosaic
                ):
                    raise RuntimeError(
                        "THING mosaic partition capacity exhausted"
                    )
                if (
                    prior.partitions[-1].entity_continuity_hmac_sha256
                    != partition.entity_continuity_hmac_sha256
                ):
                    raise ValueError("THING physical continuity changed")
                thing_id = prior.thing_id
                updated = self._seal(
                    thing_id=thing_id,
                    version=prior.version + 1,
                    partitions=prior.partitions + (partition,),
                )
            staged = dict(self._mosaics)
            staged[thing_id] = updated
            self._routes(staged)
            self._encoded(staged)
            self._mosaics = staged
            return updated

    def _stage_ordered_custody_continuation_locked(
        self,
        partitions: tuple[ThingEncounterPartition, ...],
    ) -> tuple[
        dict[str, CausalThingMosaic],
        dict[str, CausalThingMosaic],
        CausalThingMosaic,
    ]:
        if (
            not isinstance(partitions, tuple)
            or not partitions
            or any(
                not isinstance(value, ThingEncounterPartition)
                for value in partitions
            )
        ):
            raise TypeError(
                "THING ordered continuation requires a nonempty "
                "immutable partition tuple"
            )
        for partition in partitions:
            self._partition_authority.verify(partition)
            if (
                partition.source_occurrence_id is None
                or partition.parent_custody_receipt_sha256 is None
                or partition.thing_custody_capability_receipt_sha256
                is None
            ):
                raise ValueError(
                    "THING ordered continuation requires custody-derived "
                    "partitions"
                )
        if (
            len({
                value.authority_receipt_sha256 for value in partitions
            })
            != len(partitions)
            or len({
                value.source_occurrence_id for value in partitions
            })
            != len(partitions)
            or len({
                value.thing_custody_capability_receipt_sha256
                for value in partitions
            })
            != len(partitions)
        ):
            raise ValueError(
                "THING ordered continuation repeats authenticated custody"
            )

        first = partitions[0]
        if first.prior_partition_receipt_sha256 is None:
            raise ValueError(
                "THING ordered continuation cannot create a genesis"
            )
        matches = tuple(
            mosaic
            for mosaic in self._mosaics.values()
            if mosaic.partitions[-1].authority_receipt_sha256
            == first.prior_partition_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "THING ordered continuation does not name one retained "
                "mosaic"
            )
        prior = matches[0]
        if (
            len(prior.partitions) + len(partitions)
            > self._profile.max_partitions_per_mosaic
        ):
            raise RuntimeError(
                "THING mosaic partition capacity exhausted"
            )

        preceding = prior.partitions[-1]
        for partition in partitions:
            if (
                partition.prior_partition_receipt_sha256
                != preceding.authority_receipt_sha256
                or partition.entity_continuity_hmac_sha256
                != preceding.entity_continuity_hmac_sha256
                or partition.world_revision
                != preceding.world_revision + 1
            ):
                raise ValueError(
                    "THING ordered continuation left its exact physical "
                    "chain"
                )
            preceding = partition

        updated = self._seal(
            thing_id=prior.thing_id,
            version=prior.version + len(partitions),
            partitions=prior.partitions + partitions,
        )
        prior_mosaics = dict(self._mosaics)
        staged_mosaics = dict(prior_mosaics)
        staged_mosaics[prior.thing_id] = updated
        self._routes(staged_mosaics)
        self._encoded(staged_mosaics)
        return prior_mosaics, staged_mosaics, updated

    def _stage_physical_surface_continuation_locked(
        self,
        partition: ThingEncounterPartition,
    ) -> tuple[
        dict[str, CausalThingMosaic],
        dict[str, CausalThingMosaic],
        CausalThingMosaic,
    ]:
        if not isinstance(partition, ThingEncounterPartition):
            raise TypeError(
                "physical surface continuation is not a typed partition"
            )
        self._partition_authority.verify(partition)
        custody = (
            partition.source_occurrence_id,
            partition.parent_custody_receipt_sha256,
            partition.thing_custody_capability_receipt_sha256,
        )
        if (
            partition.physical_surface_observation_receipt_sha256 is None
            or partition.prior_partition_receipt_sha256 is None
            or any(value is not None for value in custody)
        ):
            raise ValueError(
                "physical surface continuation requires direct foveal cause"
            )
        retained = tuple(
            (mosaic, value)
            for mosaic in self._mosaics.values()
            for value in mosaic.partitions
        )
        replayed = tuple(
            (mosaic, value)
            for mosaic, value in retained
            if (
                value.settlement_receipt_sha256
                == partition.settlement_receipt_sha256
                or value.physical_surface_observation_receipt_sha256
                == partition.physical_surface_observation_receipt_sha256
            )
        )
        if replayed:
            exact = tuple(
                (mosaic, value)
                for mosaic, value in replayed
                if value == partition
            )
            if len(replayed) != 1 or len(exact) != 1:
                raise ValueError(
                    "physical surface encounter receipt collision"
                )
            prior_mosaics = dict(self._mosaics)
            self._routes(prior_mosaics)
            self._encoded(prior_mosaics)
            return prior_mosaics, dict(prior_mosaics), exact[0][0]
        if not self._mosaics:
            raise ValueError(
                "physical surface continuation has no retained THING"
            )
        matches = tuple(
            mosaic
            for mosaic in self._mosaics.values()
            if mosaic.partitions[-1].authority_receipt_sha256
            == partition.prior_partition_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "physical surface continuation does not name one terminal THING"
            )
        prior = matches[0]
        preceding = prior.partitions[-1]
        if (
            partition.entity_continuity_hmac_sha256
            != preceding.entity_continuity_hmac_sha256
            or partition.world_revision < preceding.world_revision
            or (
                partition.world_revision == preceding.world_revision
                and partition.world_observation_receipt_sha256
                != preceding.world_observation_receipt_sha256
            )
        ):
            raise ValueError(
                "physical surface continuation left exact entity continuity"
            )
        if len(prior.partitions) >= self._profile.max_partitions_per_mosaic:
            raise RuntimeError(
                "THING mosaic partition capacity exhausted"
            )
        updated = self._seal(
            thing_id=prior.thing_id,
            version=prior.version + 1,
            partitions=prior.partitions + (partition,),
        )
        prior_mosaics = dict(self._mosaics)
        staged_mosaics = dict(prior_mosaics)
        staged_mosaics[prior.thing_id] = updated
        self._routes(staged_mosaics)
        self._encoded(staged_mosaics)
        return prior_mosaics, staged_mosaics, updated

    @staticmethod
    def _mosaic_items(
        mosaics: Mapping[str, CausalThingMosaic],
    ) -> tuple[tuple[str, CausalThingMosaic], ...]:
        return tuple((key, mosaics[key]) for key in sorted(mosaics))

    def prepare_ordered_custody_continuation(
        self,
        partitions: tuple[ThingEncounterPartition, ...],
    ) -> PreparedCausalThingMosaicContinuation:
        """Preflight one complete ordered continuation without mutation."""

        with self._lock:
            prior, staged, updated = (
                self._stage_ordered_custody_continuation_locked(
                    partitions
                )
            )
            return PreparedCausalThingMosaicContinuation(
                partitions=partitions,
                staged_mosaic=updated,
                _prior_mosaics=self._mosaic_items(prior),
                _staged_mosaics=self._mosaic_items(staged),
                _transaction_state=(
                    _OrderedContinuationTransactionState(
                        phase="prepared"
                    )
                ),
                _owner_authority=(
                    self._ordered_continuation_authority
                ),
                _construction_authority=(
                    _PREPARED_ORDERED_CONTINUATION_AUTHORITY
                ),
            )

    def prepare_physical_surface_continuation(
        self,
        partition: ThingEncounterPartition,
    ) -> PreparedPhysicalSurfaceContinuation:
        """Preflight one new foveal encounter of a retained THING."""

        with self._lock:
            prior, staged, updated = (
                self._stage_physical_surface_continuation_locked(
                    partition
                )
            )
            return PreparedPhysicalSurfaceContinuation(
                partition=partition,
                staged_mosaic=updated,
                _prior_mosaics=self._mosaic_items(prior),
                _staged_mosaics=self._mosaic_items(staged),
                _transaction_state=(
                    _OrderedContinuationTransactionState(
                        phase="prepared"
                    )
                ),
                _owner_authority=(
                    self._physical_surface_continuation_authority
                ),
                _construction_authority=(
                    _PREPARED_PHYSICAL_SURFACE_CONTINUATION_AUTHORITY
                ),
            )

    def _verify_prepared_ordered_continuation_locked(
        self,
        prepared: PreparedCausalThingMosaicContinuation,
        *,
        require_current: bool,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedCausalThingMosaicContinuation,
            )
            or prepared._construction_authority
            is not _PREPARED_ORDERED_CONTINUATION_AUTHORITY
            or prepared._owner_authority
            is not self._ordered_continuation_authority
            or prepared._transaction_state.phase != "prepared"
        ):
            raise ValueError(
                "prepared THING ordered continuation changed custody"
            )
        prior = dict(prepared._prior_mosaics)
        staged = dict(prepared._staged_mosaics)
        if (
            len(prior) != len(prepared._prior_mosaics)
            or len(staged) != len(prepared._staged_mosaics)
            or prepared.staged_mosaic.thing_id not in staged
            or staged[prepared.staged_mosaic.thing_id]
            != prepared.staged_mosaic
        ):
            raise ValueError(
                "prepared THING ordered continuation changed state"
            )
        for partition in prepared.partitions:
            self._partition_authority.verify(partition)
        self._routes(prior)
        self._routes(staged)
        self._encoded(prior)
        self._encoded(staged)
        if require_current:
            if self._mosaics != prior:
                raise RuntimeError(
                    "prepared THING ordered continuation is stale"
                )
            expected_prior, expected_staged, expected_mosaic = (
                self._stage_ordered_custody_continuation_locked(
                    prepared.partitions,
                )
            )
            if (
                expected_prior != prior
                or expected_staged != staged
                or expected_mosaic != prepared.staged_mosaic
            ):
                raise ValueError(
                    "prepared THING ordered continuation changed staging"
                )

    def verify_prepared_ordered_custody_continuation(
        self,
        prepared: PreparedCausalThingMosaicContinuation,
    ) -> None:
        with self._lock:
            self._verify_prepared_ordered_continuation_locked(
                prepared,
                require_current=True,
            )

    def _verify_prepared_physical_surface_continuation_locked(
        self,
        prepared: PreparedPhysicalSurfaceContinuation,
        *,
        require_current: bool,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedPhysicalSurfaceContinuation,
            )
            or prepared._construction_authority
            is not _PREPARED_PHYSICAL_SURFACE_CONTINUATION_AUTHORITY
            or prepared._owner_authority
            is not self._physical_surface_continuation_authority
            or prepared._transaction_state.phase != "prepared"
        ):
            raise ValueError(
                "prepared physical surface continuation changed custody"
            )
        prior = dict(prepared._prior_mosaics)
        staged = dict(prepared._staged_mosaics)
        if (
            len(prior) != len(prepared._prior_mosaics)
            or len(staged) != len(prepared._staged_mosaics)
            or prepared.staged_mosaic.thing_id not in staged
            or staged[prepared.staged_mosaic.thing_id]
            != prepared.staged_mosaic
        ):
            raise ValueError(
                "prepared physical surface continuation changed state"
            )
        self._partition_authority.verify(prepared.partition)
        self._routes(prior)
        self._routes(staged)
        self._encoded(prior)
        self._encoded(staged)
        if require_current:
            if self._mosaics != prior:
                raise RuntimeError(
                    "prepared physical surface continuation is stale"
                )
            expected_prior, expected_staged, expected_mosaic = (
                self._stage_physical_surface_continuation_locked(
                    prepared.partition
                )
            )
            if (
                expected_prior != prior
                or expected_staged != staged
                or expected_mosaic != prepared.staged_mosaic
            ):
                raise ValueError(
                    "prepared physical surface continuation changed staging"
                )

    def verify_prepared_physical_surface_continuation(
        self,
        prepared: PreparedPhysicalSurfaceContinuation,
    ) -> None:
        with self._lock:
            self._verify_prepared_physical_surface_continuation_locked(
                prepared,
                require_current=True,
            )

    def commit_prepared_ordered_custody_continuation(
        self,
        prepared: PreparedCausalThingMosaicContinuation,
    ) -> CausalThingMosaicContinuationUndo:
        """Publish one preflighted sequence exactly once."""

        with self._lock:
            self._verify_prepared_ordered_continuation_locked(
                prepared,
                require_current=True,
            )
            staged = dict(prepared._staged_mosaics)
            self._mosaics = staged
            prepared._transaction_state.phase = "committed"
            return CausalThingMosaicContinuationUndo(
                _prepared=prepared,
                _owner_authority=(
                    self._ordered_continuation_authority
                ),
                _construction_authority=(
                    _ORDERED_CONTINUATION_UNDO_AUTHORITY
                ),
            )

    def commit_prepared_physical_surface_continuation(
        self,
        prepared: PreparedPhysicalSurfaceContinuation,
    ) -> PhysicalSurfaceContinuationUndo:
        """Publish one preflighted foveal encounter exactly once."""

        with self._lock:
            self._verify_prepared_physical_surface_continuation_locked(
                prepared,
                require_current=True,
            )
            staged = dict(prepared._staged_mosaics)
            self._mosaics = staged
            prepared._transaction_state.phase = "committed"
            return PhysicalSurfaceContinuationUndo(
                _prepared=prepared,
                _owner_authority=(
                    self._physical_surface_continuation_authority
                ),
                _construction_authority=(
                    _PHYSICAL_SURFACE_CONTINUATION_UNDO_AUTHORITY
                ),
            )

    def discard_prepared_ordered_custody_continuation(
        self,
        prepared: PreparedCausalThingMosaicContinuation,
    ) -> None:
        """Consume one uncommitted capability without public mutation."""

        with self._lock:
            self._verify_prepared_ordered_continuation_locked(
                prepared,
                require_current=False,
            )
            prepared._transaction_state.phase = "discarded"

    def discard_prepared_physical_surface_continuation(
        self,
        prepared: PreparedPhysicalSurfaceContinuation,
    ) -> None:
        with self._lock:
            self._verify_prepared_physical_surface_continuation_locked(
                prepared,
                require_current=False,
            )
            prepared._transaction_state.phase = "discarded"

    def rollback_committed_ordered_custody_continuation(
        self,
        undo: CausalThingMosaicContinuationUndo,
    ) -> None:
        """Restore exact prior bytes only while this committed state is current."""

        if (
            not isinstance(undo, CausalThingMosaicContinuationUndo)
            or undo._construction_authority
            is not _ORDERED_CONTINUATION_UNDO_AUTHORITY
            or undo._owner_authority
            is not self._ordered_continuation_authority
        ):
            raise ValueError(
                "THING ordered continuation undo changed custody"
            )
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority
                is not self._ordered_continuation_authority
                or prepared._transaction_state.phase != "committed"
            ):
                raise ValueError(
                    "THING ordered continuation undo changed custody"
                )
            prior = dict(prepared._prior_mosaics)
            staged = dict(prepared._staged_mosaics)
            self._routes(prior)
            self._routes(staged)
            self._encoded(prior)
            self._encoded(staged)
            if self._mosaics != staged:
                raise RuntimeError(
                    "THING ordered continuation undo is stale"
                )
            self._mosaics = prior
            prepared._transaction_state.phase = "rolled_back"

    def rollback_committed_physical_surface_continuation(
        self,
        undo: PhysicalSurfaceContinuationUndo,
    ) -> None:
        """Restore the exact pre-foveation THING while still current."""

        if (
            not isinstance(undo, PhysicalSurfaceContinuationUndo)
            or undo._construction_authority
            is not _PHYSICAL_SURFACE_CONTINUATION_UNDO_AUTHORITY
            or undo._owner_authority
            is not self._physical_surface_continuation_authority
        ):
            raise ValueError(
                "physical surface continuation undo changed custody"
            )
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._construction_authority
                is not _PREPARED_PHYSICAL_SURFACE_CONTINUATION_AUTHORITY
                or prepared._owner_authority
                is not self._physical_surface_continuation_authority
                or prepared._transaction_state.phase != "committed"
            ):
                raise ValueError(
                    "physical surface continuation undo changed custody"
                )
            prior = dict(prepared._prior_mosaics)
            staged = dict(prepared._staged_mosaics)
            self._routes(prior)
            self._routes(staged)
            self._encoded(prior)
            self._encoded(staged)
            if self._mosaics != staged:
                raise RuntimeError(
                    "physical surface continuation undo is stale"
                )
            self._mosaics = prior
            prepared._transaction_state.phase = "rolled_back"

    def admit_ordered_custody_continuation(
        self,
        partitions: tuple[ThingEncounterPartition, ...],
    ) -> CausalThingMosaic:
        """Atomically preflight and append one ordered physical sequence."""

        prepared = self.prepare_ordered_custody_continuation(
            partitions
        )
        self.commit_prepared_ordered_custody_continuation(prepared)
        return prepared.staged_mosaic

    def route(
        self, settlement: CausalExperienceSettlement
    ) -> CausalThingRoute:
        roots = full_field_sensory_roots(settlement)
        with self._lock:
            index = self._routes(self._mosaics)
            matched: dict[tuple[str, str], set[str]] = {
                root.route_key: index[root.route_key]
                for root in roots
                if root.route_key in index
            }
        thing_ids = tuple(sorted({
            thing_id
            for values in matched.values()
            for thing_id in values
        }))
        return CausalThingRoute(
            state=(
                "unique"
                if len(thing_ids) == 1
                else "ambiguous"
                if thing_ids
                else "unresolved"
            ),
            thing_ids=thing_ids,
            matching_route_keys=tuple(sorted(matched)),
        )

    def _body(
        self, mosaics: Mapping[str, CausalThingMosaic]
    ) -> dict[str, object]:
        return {
            "mosaics": [mosaics[key].record() for key in sorted(mosaics)],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self, mosaics: Mapping[str, CausalThingMosaic]
    ) -> bytes:
        body = self._body(mosaics)
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
            raise RuntimeError("THING mosaic state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._mosaics)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "full_field": True,
                "mosaics": len(self._mosaics),
                "partitions": sum(
                    len(value.partitions)
                    for value in self._mosaics.values()
                ),
                "reduced_approximation": False,
                "routes": len(self._routes(self._mosaics)),
                "schema": "guala.causal_thing_mosaic.status.v1",
                "state_bytes": len(self._encoded(self._mosaics)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = (
    "CausalThingMosaic",
    "CausalThingMosaicContinuationUndo",
    "CausalThingMosaicGenesisUndo",
    "CausalThingMosaicOwner",
    "CausalThingMosaicProfile",
    "CausalThingRoute",
    "FullFieldSensoryRoot",
    "PreparedCausalThingMosaicContinuation",
    "PreparedCausalThingMosaicGenesis",
    "ThingEncounterPartition",
    "W1ContactThingEncounterAuthority",
    "full_field_sensory_roots",
)
