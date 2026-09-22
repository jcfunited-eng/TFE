"""Bounded causal grounding for exact recurrent auditory motif activations.

This owner is the first semantic boundary after recurrent auditory motifs.  It
never treats a tutor label, transcript, chi, whole firing set, object ID, or
scalar score as meaning.  Admission recomputes firing through the authoritative
motif bank, verifies every exact activation against its neuron and receptor
experience, and binds those activation intervals to one verified six-sense
causal settlement.

Learning accepts only a controlled crossmodal contrast:

* all non-auditory roots have identical topology;
* exactly one non-auditory root varies;
* every referent alternative has at least two independent positive episodes;
* for each alternative, its diagnostic conjunction is the exact intersection
  of every positive firing set minus the union of all contrast firing sets.

The conjunction is distributed evidence, not a word identity.  A shared motif
cannot release a referent.  An empty conjunction remains explicitly
unresolved.  At firing time, every complete diagnostic conjunction present in
the active motif set releases its referent, so two causally grounded
assemblies may both resolve in one physical mixture.  There is no vote,
threshold, score, selected winner, probabilistic shortcut, or fallback.

All retained auditory activations include their complete paired
``D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k`` occurrence records.  All retained
referents include the complete explicit non-auditory field tuples, topology,
coordinates, and source support.  Persistence is canonical, HMAC-authenticated,
and bounded by a caller-receipted resource profile.
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

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA,
    AuditoryMotifActivation,
    AuditoryMotifObservationState,
    AuditoryReceptorExperience,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorFullFieldEvent,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


GROUNDING_RESOURCE_PROFILE_SCHEMA = (
    "guala.auditory.motif_causal_grounding_resource_profile.v1"
)
GROUNDING_ACTIVATION_EVIDENCE_SCHEMA = (
    "guala.auditory.motif_causal_activation_evidence.v1"
)
GROUNDING_EPISODE_SCHEMA = (
    "guala.auditory.motif_causal_grounding_episode.v1"
)
GROUNDING_DISTINCTION_SCHEMA = (
    "guala.auditory.motif_controlled_distinction.v1"
)
GROUNDING_STATE_SCHEMA = (
    "guala.auditory.motif_causal_grounding_state.v1"
)
GROUNDING_ENVELOPE_SCHEMA = (
    "guala.auditory.motif_causal_grounding_hmac.v1"
)

_STATE_DOMAIN = b"guala-auditory-motif-causal-grounding-state-v1\0"
_EPISODE_DOMAIN = b"guala-auditory-motif-causal-grounding-episode-v1\0"
_DISTINCTION_DOMAIN = (
    b"guala-auditory-motif-controlled-distinction-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_MIN_INDEPENDENT_POSITIVE_EPISODES = 2


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
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, bytes):
        result = value
    else:
        raise TypeError("grounding authority key must be immutable bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("grounding authority key has an invalid boundary")
    return result


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("grounding causal time must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonically encoded")
    return result


def _canonical_json_text(value: object) -> str:
    return _canonical(value).decode("utf-8")


def _decoded_canonical_json(value: object, name: str) -> object:
    if not isinstance(value, str):
        raise ValueError(f"{name} is not canonical JSON text")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not canonical JSON text") from exc
    if _canonical_json_text(decoded) != value:
        raise ValueError(f"{name} is not canonical JSON text")
    return decoded


@dataclass(frozen=True, slots=True)
class AuditoryMotifGroundingResourceProfile:
    profile_id: str
    max_episodes: int
    max_distinctions: int
    max_firing_motifs_per_episode: int
    max_activations_per_episode: int
    max_roots_per_episode: int
    max_episode_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_episodes: int,
        max_distinctions: int,
        max_firing_motifs_per_episode: int,
        max_activations_per_episode: int,
        max_roots_per_episode: int,
        max_episode_bytes: int,
        max_state_bytes: int,
    ) -> "AuditoryMotifGroundingResourceProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "grounding resource profile"),
            max_episodes=_positive_int(max_episodes, "grounding episodes"),
            max_distinctions=_positive_int(
                max_distinctions, "grounding distinctions"
            ),
            max_firing_motifs_per_episode=_positive_int(
                max_firing_motifs_per_episode,
                "grounding firing motifs per episode",
            ),
            max_activations_per_episode=_positive_int(
                max_activations_per_episode,
                "grounding activations per episode",
            ),
            max_roots_per_episode=_positive_int(
                max_roots_per_episode, "grounding roots per episode"
            ),
            max_episode_bytes=_positive_int(
                max_episode_bytes, "grounding episode bytes"
            ),
            max_state_bytes=_positive_int(
                max_state_bytes, "grounding state bytes"
            ),
            authority_receipt_sha256="0" * 64,
        )
        if provisional.max_state_bytes < provisional.max_episode_bytes:
            raise ValueError(
                "grounding state boundary cannot be smaller than one episode"
            )
        return cls(
            **{
                field: getattr(provisional, field)
                for field in (
                    "profile_id",
                    "max_episodes",
                    "max_distinctions",
                    "max_firing_motifs_per_episode",
                    "max_activations_per_episode",
                    "max_roots_per_episode",
                    "max_episode_bytes",
                    "max_state_bytes",
                )
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_activations_per_episode": self.max_activations_per_episode,
            "max_distinctions": self.max_distinctions,
            "max_episode_bytes": self.max_episode_bytes,
            "max_episodes": self.max_episodes,
            "max_firing_motifs_per_episode": (
                self.max_firing_motifs_per_episode
            ),
            "max_roots_per_episode": self.max_roots_per_episode,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": GROUNDING_RESOURCE_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "grounding resource profile")
        for value, name in (
            (self.max_episodes, "grounding episodes"),
            (self.max_distinctions, "grounding distinctions"),
            (
                self.max_firing_motifs_per_episode,
                "grounding firing motifs per episode",
            ),
            (
                self.max_activations_per_episode,
                "grounding activations per episode",
            ),
            (self.max_roots_per_episode, "grounding roots per episode"),
            (self.max_episode_bytes, "grounding episode bytes"),
            (self.max_state_bytes, "grounding state bytes"),
        ):
            _positive_int(value, name)
        if self.max_state_bytes < self.max_episode_bytes:
            raise ValueError(
                "grounding state boundary cannot be smaller than one episode"
            )
        _sha256(
            self.authority_receipt_sha256,
            "grounding resource profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("grounding resource profile authority changed")


def _validate_field_pairs(value: object, name: str) -> None:
    if (
        not isinstance(value, list)
        or len(value) != len(DSF_FIELD_ORDER)
        or tuple(
            item[0]
            for item in value
            if isinstance(item, list) and len(item) == 2
        )
        != DSF_FIELD_ORDER
    ):
        raise ValueError(f"{name} lost explicit DSF field order")
    for expected_name, item in zip(DSF_FIELD_ORDER, value, strict=True):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or item[0] != expected_name
        ):
            raise ValueError(f"{name} lost explicit DSF field order")
        _fraction(item[1], f"{name} {expected_name}")


def _validate_occurrence_record(value: object) -> None:
    expected = {
        "authority_receipt_sha256",
        "causal_interval_end",
        "phase_field_receipt_sha256",
        "phase_fields",
        "pressure_basin",
        "pressure_field_receipt_sha256",
        "pressure_fields",
        "receptor",
        "schema",
        "source_index",
        "source_time",
        "winding_delta",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA
        or value.get("pressure_basin") != "authoritative_upper"
    ):
        raise ValueError("grounding activation occurrence changed")
    receptor = value.get("receptor")
    if (
        not isinstance(receptor, Mapping)
        or set(receptor)
        != {"channel_id", "cochlear_index", "winding_direction"}
        or not isinstance(receptor.get("channel_id"), str)
        or isinstance(receptor.get("cochlear_index"), bool)
        or not isinstance(receptor.get("cochlear_index"), int)
        or receptor.get("winding_direction") not in (-1, 1)
    ):
        raise ValueError("grounding activation receptor changed")
    if (
        isinstance(value.get("source_index"), bool)
        or not isinstance(value.get("source_index"), int)
        or value["source_index"] < 0
        or isinstance(value.get("winding_delta"), bool)
        or not isinstance(value.get("winding_delta"), int)
        or value["winding_delta"] == 0
        or (1 if value["winding_delta"] > 0 else -1)
        != receptor["winding_direction"]
    ):
        raise ValueError("grounding activation occurrence order changed")
    source_time = _fraction(
        value.get("source_time"), "grounding occurrence source time"
    )
    causal_end = _fraction(
        value.get("causal_interval_end"),
        "grounding occurrence causal interval end",
    )
    if causal_end <= source_time:
        raise ValueError("grounding occurrence causal support changed")
    _validate_field_pairs(
        value.get("pressure_fields"),
        "grounding occurrence pressure",
    )
    _validate_field_pairs(
        value.get("phase_fields"),
        "grounding occurrence phase",
    )
    for key, name in (
        ("pressure_field_receipt_sha256", "pressure field receipt"),
        ("phase_field_receipt_sha256", "phase field receipt"),
        ("authority_receipt_sha256", "occurrence authority"),
    ):
        _sha256(value.get(key), f"grounding {name}")
    payload = {
        key: value[key]
        for key in value
        if key != "authority_receipt_sha256"
    }
    if _digest(payload) != value["authority_receipt_sha256"]:
        raise ValueError("grounding occurrence authority changed")


def _activation_record(value: AuditoryMotifActivation) -> dict[str, object]:
    return {
        "full_field_occurrences": [
            occurrence.payload()
            | {
                "authority_receipt_sha256": (
                    occurrence.authority_receipt_sha256
                )
            }
            for occurrence in value.full_field_occurrences
        ],
        "neuron_id": value.neuron_id,
        "schema": GROUNDING_ACTIVATION_EVIDENCE_SCHEMA,
        "segment_index": value.segment_index,
        "source_index_end": value.source_index_end,
        "source_index_start": value.source_index_start,
        "source_time_end": _fraction_text(value.source_time_end),
        "source_time_start": _fraction_text(value.source_time_start),
        "state_ordinal_end": value.state_ordinal_end,
        "state_ordinal_start": value.state_ordinal_start,
    }


def _validate_activation_record(value: object) -> None:
    expected = {
        "full_field_occurrences",
        "neuron_id",
        "schema",
        "segment_index",
        "source_index_end",
        "source_index_start",
        "source_time_end",
        "source_time_start",
        "state_ordinal_end",
        "state_ordinal_start",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != GROUNDING_ACTIVATION_EVIDENCE_SCHEMA
        or not isinstance(value.get("full_field_occurrences"), list)
        or not value["full_field_occurrences"]
    ):
        raise ValueError("grounding activation evidence changed")
    _sha256(value.get("neuron_id"), "grounding activation neuron")
    for key in (
        "segment_index",
        "source_index_start",
        "source_index_end",
        "state_ordinal_start",
        "state_ordinal_end",
    ):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError("grounding activation ordinal changed")
    if (
        value["source_index_end"] < value["source_index_start"]
        or value["state_ordinal_end"] <= value["state_ordinal_start"]
    ):
        raise ValueError("grounding activation interval changed")
    start = _fraction(
        value.get("source_time_start"),
        "grounding activation source start",
    )
    end = _fraction(
        value.get("source_time_end"),
        "grounding activation source end",
    )
    if end <= start:
        raise ValueError("grounding activation causal interval changed")
    for occurrence in value["full_field_occurrences"]:
        _validate_occurrence_record(occurrence)
    occurrence_start = min(
        _fraction(
            item["source_time"],
            "grounding activation occurrence start",
        )
        for item in value["full_field_occurrences"]
    )
    occurrence_end = max(
        _fraction(
            item["causal_interval_end"],
            "grounding activation occurrence end",
        )
        for item in value["full_field_occurrences"]
    )
    if start != occurrence_start or end != occurrence_end:
        raise ValueError("grounding activation lost causal support")


@dataclass(frozen=True, slots=True)
class GroundingActivationEvidence:
    neuron_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    activation_json: str
    authority_receipt_sha256: str

    @classmethod
    def from_activation(
        cls,
        value: AuditoryMotifActivation,
    ) -> "GroundingActivationEvidence":
        record = _activation_record(value)
        return cls(
            neuron_id=value.neuron_id,
            source_time_start=value.source_time_start,
            source_time_end=value.source_time_end,
            activation_json=_canonical_json_text(record),
            authority_receipt_sha256=_digest(record),
        )

    def verify(self) -> None:
        _sha256(self.neuron_id, "grounding activation neuron")
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
        ):
            raise ValueError("grounding activation causal interval changed")
        decoded = _decoded_canonical_json(
            self.activation_json, "grounding activation evidence"
        )
        _validate_activation_record(decoded)
        if (
            decoded["neuron_id"] != self.neuron_id
            or _fraction(
                decoded["source_time_start"],
                "grounding activation source start",
            )
            != self.source_time_start
            or _fraction(
                decoded["source_time_end"],
                "grounding activation source end",
            )
            != self.source_time_end
            or _digest(decoded) != self.authority_receipt_sha256
        ):
            raise ValueError("grounding activation evidence authority changed")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "activation_json": self.activation_json,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "neuron_id": self.neuron_id,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }


def _validate_root_value(value: object) -> None:
    expected = {
        "boundary_state",
        "coordinates",
        "field_tuples",
        "physical_quantity",
        "physical_unit",
        "sense",
        "sensor_id",
        "source_sample_count",
        "substream_id",
        "topology_index",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("grounding referent root changed")
    _identifier(value.get("sense"), "grounding root sense")
    _identifier(value.get("boundary_state"), "grounding boundary state")
    if value["substream_id"] is None:
        if any(
            value[key] is not None
            for key in (
                "coordinates",
                "field_tuples",
                "physical_quantity",
                "physical_unit",
                "sensor_id",
                "source_sample_count",
                "topology_index",
            )
        ):
            raise ValueError("grounding boundary root contains a substream")
        return
    for key, name in (
        ("sensor_id", "grounding sensor"),
        ("substream_id", "grounding substream"),
        ("physical_quantity", "grounding physical quantity"),
        ("physical_unit", "grounding physical unit"),
    ):
        _identifier(value.get(key), name)
    if (
        isinstance(value.get("topology_index"), bool)
        or not isinstance(value.get("topology_index"), int)
        or value["topology_index"] < 0
        or isinstance(value.get("source_sample_count"), bool)
        or not isinstance(value.get("source_sample_count"), int)
        or value["source_sample_count"] <= 0
        or not isinstance(value.get("coordinates"), list)
        or not isinstance(value.get("field_tuples"), list)
        or not value["field_tuples"]
    ):
        raise ValueError("grounding substream causal topology changed")
    for coordinate in value["coordinates"]:
        if (
            not isinstance(coordinate, list)
            or len(coordinate) != 2
        ):
            raise ValueError("grounding referent coordinate changed")
        _identifier(coordinate[0], "grounding coordinate axis")
        _identifier(coordinate[1], "grounding coordinate value")
    for expected_index, field_tuple in enumerate(value["field_tuples"]):
        if (
            not isinstance(field_tuple, Mapping)
            or set(field_tuple)
            != {
                "fields",
                "source_index_end",
                "source_index_start",
                "tuple_index",
            }
            or field_tuple.get("tuple_index") != expected_index
            or isinstance(field_tuple.get("source_index_start"), bool)
            or not isinstance(field_tuple.get("source_index_start"), int)
            or isinstance(field_tuple.get("source_index_end"), bool)
            or not isinstance(field_tuple.get("source_index_end"), int)
            or not 0
            <= field_tuple["source_index_start"]
            <= field_tuple["source_index_end"]
            < value["source_sample_count"]
        ):
            raise ValueError("grounding referent causal support changed")
        _validate_field_pairs(
            field_tuple.get("fields"),
            "grounding referent",
        )


def _physical_root_identity(value: Mapping[str, object]) -> dict[str, object]:
    """Exclude provider/object bookkeeping while retaining physical fields.

    ``sensor_id``, ``substream_id``, and coordinate values remain in the
    authoritative root record as provenance.  They cannot identify a
    referent.  Physical identity is the typed sense/topology/quantity plus
    every exact field tuple and its causal support.
    """

    return {
        "boundary_state": value["boundary_state"],
        "field_tuples": value["field_tuples"],
        "physical_quantity": value["physical_quantity"],
        "physical_unit": value["physical_unit"],
        "sense": value["sense"],
        "source_sample_count": value["source_sample_count"],
        "topology_index": value["topology_index"],
    }


@dataclass(frozen=True, slots=True)
class GroundingRoot:
    root_id: str
    value_sha256: str
    value_json: str

    @classmethod
    def create(cls, root_id: str, value: object) -> "GroundingRoot":
        _validate_root_value(value)
        text = _canonical_json_text(value)
        return cls(
            root_id=_identifier(root_id, "grounding root"),
            value_sha256=_digest(_physical_root_identity(value)),
            value_json=text,
        )

    def verify(self) -> None:
        _identifier(self.root_id, "grounding root")
        _sha256(self.value_sha256, "grounding root value")
        decoded = _decoded_canonical_json(
            self.value_json, "grounding root value"
        )
        _validate_root_value(decoded)
        if _digest(_physical_root_identity(decoded)) != self.value_sha256:
            raise ValueError("grounding root value authority changed")

    def as_record(self) -> dict[str, str]:
        self.verify()
        return {
            "root_id": self.root_id,
            "value_json": self.value_json,
            "value_sha256": self.value_sha256,
        }


def _roots_from_settlement(
    settlement: CausalExperienceSettlement,
) -> tuple[GroundingRoot, ...]:
    expected_senses = tuple(sense.value for sense in SENSE_ORDER)
    if tuple(item.sense for item in settlement.interpretations) != expected_senses:
        raise ValueError("grounding settlement lost exact six-sense order")
    roots: list[GroundingRoot] = []
    for sense in settlement.interpretations:
        if sense.sense == "sound":
            continue
        roots.append(GroundingRoot.create(
            f"sense:{sense.sense}:boundary",
            {
                "boundary_state": sense.state,
                "coordinates": None,
                "field_tuples": None,
                "physical_quantity": None,
                "physical_unit": None,
                "sense": sense.sense,
                "sensor_id": None,
                "source_sample_count": None,
                "substream_id": None,
                "topology_index": None,
            },
        ))
        for substream in sense.substreams:
            roots.append(GroundingRoot.create(
                (
                    f"sense:{sense.sense}:topology:"
                    f"{substream.topology_index}"
                ),
                {
                    "boundary_state": sense.state,
                    "coordinates": [
                        [axis, coordinate]
                        for axis, coordinate in substream.coordinates
                    ],
                    "field_tuples": [
                        {
                            "fields": [
                                [name, _fraction_text(field)]
                                for name, field in item.fields
                            ],
                            "source_index_end": item.source_index_end,
                            "source_index_start": item.source_index_start,
                            "tuple_index": item.tuple_index,
                        }
                        for item in substream.field_tuples
                    ],
                    "physical_quantity": substream.physical_quantity,
                    "physical_unit": substream.physical_unit,
                    "sense": sense.sense,
                    "sensor_id": substream.sensor_id,
                    "source_sample_count": substream.source_sample_count,
                    "substream_id": substream.substream_id,
                    "topology_index": substream.topology_index,
                },
            ))
    roots.sort(key=lambda value: value.root_id)
    if len({value.root_id for value in roots}) != len(roots):
        raise ValueError("grounding settlement repeats a causal root")
    return tuple(roots)


def grounding_roots_from_settlement(
    settlement: CausalExperienceSettlement,
) -> tuple[GroundingRoot, ...]:
    """Return the verified full non-auditory root structure."""

    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError("grounding roots require an exact causal settlement")
    settlement.verify()
    return _roots_from_settlement(settlement)


def _verify_auditory_transaction_link(
    *,
    auditory_event: AuditoryReceptorFullFieldEvent,
    auditory_experience: AuditoryReceptorExperience,
    settlement: CausalExperienceSettlement,
) -> None:
    """Prove receptor evidence and non-auditory roots share one transaction."""

    if not isinstance(auditory_event, AuditoryReceptorFullFieldEvent):
        raise TypeError(
            "grounding requires the originating receptor full-field event"
        )
    auditory_event.verify()
    auditory_experience.verify()
    settlement.verify()
    if (
        auditory_experience.source_event_receipt_sha256
        != auditory_event.authority_receipt_sha256
        or auditory_experience.source_event_receipt_sha256s
        != (auditory_event.authority_receipt_sha256,)
        or auditory_experience.source_frame_count
        != auditory_event.frame_count
    ):
        raise ValueError(
            "grounding auditory experience belongs to another receptor event"
        )
    sound = next(
        (
            interpretation
            for interpretation in settlement.interpretations
            if interpretation.sense == "sound"
        ),
        None,
    )
    if sound is None or sound.state != "observed" or not sound.substreams:
        raise ValueError(
            "grounding settlement does not mount observed sound"
        )
    settlement_fields = {}
    for substream in sound.substreams:
        for field_tuple in substream.field_tuples:
            receipt = field_tuple.authority_receipt_sha256
            mounted = (
                field_tuple.fields,
                field_tuple.source_l0_l4_trace_receipt_sha256,
            )
            prior = settlement_fields.setdefault(receipt, mounted)
            if prior != mounted:
                raise ValueError(
                    "grounding settlement repeats an auditory field receipt"
                )
    event_fields = {}
    for channel in auditory_event.channels:
        for field_tuple in (*channel.pressure_fields, *channel.phase_fields):
            receipt = field_tuple.authority_receipt_sha256
            mounted = (
                field_tuple.fields,
                field_tuple.source_l0_l4_trace_receipt_sha256,
            )
            prior = event_fields.setdefault(receipt, mounted)
            if prior != mounted:
                raise ValueError(
                    "grounding receptor event repeats a field receipt"
                )
    if not event_fields or any(
        settlement_fields.get(receipt) != mounted
        for receipt, mounted in event_fields.items()
    ):
        raise ValueError(
            "grounding receptor event is not mounted in this settlement"
        )
    if any(
        occurrence.pressure_field_receipt_sha256 not in event_fields
        or occurrence.phase_field_receipt_sha256 not in event_fields
        for occurrence in auditory_experience.occurrences
    ):
        raise ValueError(
            "grounding receptor experience lost its event field mounting"
        )


@dataclass(frozen=True, slots=True)
class GroundingEpisode:
    episode_id: str
    auditory_experience_receipt_sha256: str
    auditory_source_event_receipt_sha256: str
    settlement_authority_receipt_sha256: str
    motif_bank_state_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    firing_motif_neuron_ids: tuple[str, ...]
    unresolved_source_indices: tuple[int, ...]
    activations: tuple[GroundingActivationEvidence, ...]
    roots: tuple[GroundingRoot, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "activations": [value.as_record() for value in self.activations],
            "auditory_experience_receipt_sha256": (
                self.auditory_experience_receipt_sha256
            ),
            "auditory_source_event_receipt_sha256": (
                self.auditory_source_event_receipt_sha256
            ),
            "firing_motif_neuron_ids": list(
                self.firing_motif_neuron_ids
            ),
            "motif_bank_state_sha256": self.motif_bank_state_sha256,
            "roots": [value.as_record() for value in self.roots],
            "schema": GROUNDING_EPISODE_SCHEMA,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "unresolved_source_indices": list(
                self.unresolved_source_indices
            ),
        }

    def verify(
        self,
        *,
        authority_key: bytes,
        profile: AuditoryMotifGroundingResourceProfile,
    ) -> None:
        for value, name in (
            (self.episode_id, "grounding episode"),
            (
                self.auditory_experience_receipt_sha256,
                "grounding auditory experience",
            ),
            (
                self.auditory_source_event_receipt_sha256,
                "grounding auditory source event",
            ),
            (
                self.settlement_authority_receipt_sha256,
                "grounding causal settlement",
            ),
            (self.motif_bank_state_sha256, "grounding motif bank state"),
        ):
            _sha256(value, name)
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or not self.firing_motif_neuron_ids
            or tuple(sorted(set(self.firing_motif_neuron_ids)))
            != self.firing_motif_neuron_ids
            or len(self.firing_motif_neuron_ids)
            > profile.max_firing_motifs_per_episode
            or not self.activations
            or len(self.activations) > profile.max_activations_per_episode
            or not self.roots
            or len(self.roots) > profile.max_roots_per_episode
            or tuple(sorted(self.roots, key=lambda value: value.root_id))
            != self.roots
            or len({value.root_id for value in self.roots})
            != len(self.roots)
        ):
            raise ValueError("grounding episode crossed its causal boundary")
        for value in self.firing_motif_neuron_ids:
            _sha256(value, "grounding firing motif")
        if (
            not isinstance(self.unresolved_source_indices, tuple)
            or tuple(sorted(set(self.unresolved_source_indices)))
            != self.unresolved_source_indices
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in self.unresolved_source_indices
            )
        ):
            raise ValueError("grounding unresolved source boundary changed")
        activation_neurons = set()
        for activation in self.activations:
            activation.verify()
            activation_neurons.add(activation.neuron_id)
            if (
                activation.source_time_start < self.source_time_start
                or activation.source_time_end > self.source_time_end
            ):
                raise ValueError(
                    "grounding activation left causal settlement interval"
                )
        if activation_neurons != set(self.firing_motif_neuron_ids):
            raise ValueError("grounding episode firing lost activation evidence")
        for root in self.roots:
            root.verify()
        identity = _digest({
            "auditory_experience_receipt_sha256": (
                self.auditory_experience_receipt_sha256
            ),
            "auditory_source_event_receipt_sha256": (
                self.auditory_source_event_receipt_sha256
            ),
            "firing_motif_neuron_ids": list(
                self.firing_motif_neuron_ids
            ),
            "roots": [
                [value.root_id, value.value_sha256]
                for value in self.roots
            ],
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        })
        if self.episode_id != identity:
            raise ValueError("grounding episode identity changed")
        payload = self.payload()
        if _sign(authority_key, _EPISODE_DOMAIN, payload) != (
            self.authority_hmac_sha256
        ):
            raise ValueError("grounding episode HMAC changed")
        if len(_canonical(self.as_record())) > profile.max_episode_bytes:
            raise ValueError("grounding episode exceeds resource profile")

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "episode_id": self.episode_id,
        }


class GroundingAdmissionState(str, Enum):
    ADMITTED = "admitted"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"
    INDETERMINATE_RESOURCE = "indeterminate_resource"


@dataclass(frozen=True, slots=True)
class GroundingEpisodeAdmission:
    state: GroundingAdmissionState
    reason: str
    episode: GroundingEpisode | None
    stored: bool


@dataclass(frozen=True, slots=True)
class DiagnosticReferent:
    root: GroundingRoot
    positive_episode_ids: tuple[str, ...]
    diagnostic_motif_neuron_ids: tuple[str, ...]

    def verify(self) -> None:
        self.root.verify()
        if (
            len(self.positive_episode_ids)
            < _MIN_INDEPENDENT_POSITIVE_EPISODES
            or tuple(sorted(set(self.positive_episode_ids)))
            != self.positive_episode_ids
            or tuple(sorted(set(self.diagnostic_motif_neuron_ids)))
            != self.diagnostic_motif_neuron_ids
        ):
            raise ValueError("grounding diagnostic referent changed")
        for value in (
            *self.positive_episode_ids,
            *self.diagnostic_motif_neuron_ids,
        ):
            _sha256(value, "grounding diagnostic authority")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "diagnostic_motif_neuron_ids": list(
                self.diagnostic_motif_neuron_ids
            ),
            "positive_episode_ids": list(self.positive_episode_ids),
            "root": self.root.as_record(),
        }


@dataclass(frozen=True, slots=True)
class ControlledGroundingDistinction:
    distinction_id: str
    family_id: str
    referent_root_id: str
    background_roots: tuple[GroundingRoot, ...]
    alternatives: tuple[DiagnosticReferent, ...]
    proof_episode_ids: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "alternatives": [value.as_record() for value in self.alternatives],
            "background_roots": [
                value.as_record() for value in self.background_roots
            ],
            "family_id": self.family_id,
            "proof_episode_ids": list(self.proof_episode_ids),
            "referent_root_id": self.referent_root_id,
            "schema": GROUNDING_DISTINCTION_SCHEMA,
        }

    def verify(self, authority_key: bytes) -> None:
        _sha256(self.distinction_id, "grounding distinction")
        _sha256(self.family_id, "grounding distinction family")
        _identifier(self.referent_root_id, "grounding referent root")
        if (
            not self.background_roots
            or tuple(
                sorted(
                    self.background_roots,
                    key=lambda value: value.root_id,
                )
            )
            != self.background_roots
            or any(
                value.root_id == self.referent_root_id
                for value in self.background_roots
            )
            or len(self.alternatives) < 2
            or tuple(
                sorted(
                    self.alternatives,
                    key=lambda value: value.root.value_sha256,
                )
            )
            != self.alternatives
            or len({
                value.root.value_sha256 for value in self.alternatives
            })
            != len(self.alternatives)
            or tuple(sorted(set(self.proof_episode_ids)))
            != self.proof_episode_ids
        ):
            raise ValueError("grounding distinction structure changed")
        for value in self.background_roots:
            value.verify()
        positive_ids = set()
        for alternative in self.alternatives:
            alternative.verify()
            if alternative.root.root_id != self.referent_root_id:
                raise ValueError(
                    "grounding distinction mixed referent roots"
                )
            positive_ids.update(alternative.positive_episode_ids)
        if positive_ids != set(self.proof_episode_ids):
            raise ValueError("grounding distinction proof set changed")
        expected_family = _digest({
            "background_roots": [
                [value.root_id, value.value_sha256]
                for value in self.background_roots
            ],
            "referent_root_id": self.referent_root_id,
        })
        if self.family_id != expected_family:
            raise ValueError("grounding distinction family changed")
        payload = self.payload()
        if (
            self.distinction_id != _digest(payload)
            or _sign(authority_key, _DISTINCTION_DOMAIN, payload)
            != self.authority_hmac_sha256
        ):
            raise ValueError("grounding distinction authority changed")

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "distinction_id": self.distinction_id,
        }


class GroundingLearningState(str, Enum):
    SETTLED = "settled"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE_RESOURCE = "indeterminate_resource"


@dataclass(frozen=True, slots=True)
class GroundingLearningResult:
    state: GroundingLearningState
    reason: str
    distinction: ControlledGroundingDistinction | None
    unresolved_referent_value_sha256s: tuple[str, ...] = ()


class DiagnosticActivationState(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    ABSENT = "absent"
    UNRESOLVED_EMPTY = "unresolved_empty"


@dataclass(frozen=True, slots=True)
class DiagnosticActivation:
    distinction_id: str
    root: GroundingRoot
    state: DiagnosticActivationState
    required_motif_neuron_ids: tuple[str, ...]
    present_motif_neuron_ids: tuple[str, ...]
    missing_motif_neuron_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedGroundedReferent:
    root: GroundingRoot
    contributing_motif_neuron_ids: tuple[str, ...]
    contributing_activations: tuple[AuditoryMotifActivation, ...]
    distinction_ids: tuple[str, ...]


class GroundingResolutionState(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    INDETERMINATE_RESOURCE = "indeterminate_resource"


@dataclass(frozen=True, slots=True)
class GroundingResolution:
    state: GroundingResolutionState
    reason: str
    firing_motif_neuron_ids: tuple[str, ...]
    referents: tuple[ResolvedGroundedReferent, ...]
    diagnostics: tuple[DiagnosticActivation, ...]
    ungrounded_motif_neuron_ids: tuple[str, ...]


def _stable_firing(
    *,
    motif_owner: AuditoryRecurrentMotifOwner,
    experience: AuditoryReceptorExperience,
):
    if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
        raise TypeError("grounding requires the recurrent motif owner")
    if not isinstance(experience, AuditoryReceptorExperience):
        raise TypeError("grounding requires an auditory receptor experience")
    experience.verify()
    before = motif_owner.snapshot_encoded()
    firing = motif_owner.fire(experience)
    after = motif_owner.snapshot_encoded()
    if before != after:
        return None, None, "motif bank changed during grounding observation"
    if firing.state is not AuditoryMotifObservationState.OBSERVED:
        return None, None, firing.reason
    if (
        tuple(sorted(set(firing.firing_motif_neuron_ids)))
        != firing.firing_motif_neuron_ids
        or firing.unresolved_source_indices
        != experience.unresolved_source_indices
    ):
        raise ValueError("grounding motif firing changed canonical evidence")
    neurons = {
        neuron.neuron_id: neuron
        for neuron in motif_owner.motif_neurons
    }
    if set(firing.firing_motif_neuron_ids) - set(neurons):
        raise ValueError("grounding firing names an absent motif neuron")
    activation_ids = set()
    for activation in firing.activations:
        neuron = neurons.get(activation.neuron_id)
        if neuron is None:
            raise ValueError("grounding activation names an absent neuron")
        neuron.verify()
        activation.verify(neuron, experience)
        activation_ids.add(activation.neuron_id)
    if activation_ids != set(firing.firing_motif_neuron_ids):
        raise ValueError("grounding firing lost exact activation evidence")
    return firing, hashlib.sha256(before).hexdigest(), ""


def _root_from_record(value: object) -> GroundingRoot:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"root_id", "value_json", "value_sha256"}
    ):
        raise ValueError("grounding root record changed")
    root = GroundingRoot(
        root_id=value.get("root_id"),
        value_sha256=value.get("value_sha256"),
        value_json=value.get("value_json"),
    )
    root.verify()
    return root


def _activation_from_record(value: object) -> GroundingActivationEvidence:
    if (
        not isinstance(value, Mapping)
        or set(value)
        != {
            "activation_json",
            "authority_receipt_sha256",
            "neuron_id",
            "source_time_end",
            "source_time_start",
        }
    ):
        raise ValueError("grounding activation record changed")
    result = GroundingActivationEvidence(
        neuron_id=value.get("neuron_id"),
        source_time_start=_fraction(
            value.get("source_time_start"),
            "grounding activation source start",
        ),
        source_time_end=_fraction(
            value.get("source_time_end"),
            "grounding activation source end",
        ),
        activation_json=value.get("activation_json"),
        authority_receipt_sha256=value.get(
            "authority_receipt_sha256"
        ),
    )
    result.verify()
    return result


class AuditoryMotifCausalGroundingOwner:
    """Finite owner for exact motif-to-crossmodal controlled distinctions."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: AuditoryMotifGroundingResourceProfile,
    ) -> None:
        if not isinstance(
            resource_profile, AuditoryMotifGroundingResourceProfile
        ):
            raise TypeError("grounding requires a typed resource profile")
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._episode_key = hashlib.sha256(_EPISODE_DOMAIN + root).digest()
        self._distinction_key = hashlib.sha256(
            _DISTINCTION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._episodes: dict[str, GroundingEpisode] = {}
        self._distinctions: dict[
            str, ControlledGroundingDistinction
        ] = {}
        self._lock = threading.RLock()

    @property
    def resource_profile(self) -> AuditoryMotifGroundingResourceProfile:
        return self._profile

    @property
    def episodes(self) -> tuple[GroundingEpisode, ...]:
        with self._lock:
            return tuple(
                self._episodes[key] for key in sorted(self._episodes)
            )

    @property
    def distinctions(self) -> tuple[ControlledGroundingDistinction, ...]:
        with self._lock:
            return tuple(
                self._distinctions[key]
                for key in sorted(self._distinctions)
            )

    def status(self) -> dict[str, int | bool]:
        """Expose exact learned extent and every fixed resource boundary."""

        with self._lock:
            encoded_bytes = len(self._encoded_state(
                self._episodes,
                self._distinctions,
            ))
            alternatives = tuple(
                alternative
                for distinction in self._distinctions.values()
                for alternative in distinction.alternatives
            )
            learned = {
                (
                    value.root.root_id,
                    value.root.value_sha256,
                )
                for value in alternatives
                if value.diagnostic_motif_neuron_ids
            }
            unresolved = {
                (
                    value.root.root_id,
                    value.root.value_sha256,
                )
                for value in alternatives
                if not value.diagnostic_motif_neuron_ids
            }
            proof_episode_ids = {
                episode_id
                for distinction in self._distinctions.values()
                for episode_id in distinction.proof_episode_ids
            }
            return {
                "episode_count": len(self._episodes),
                "episode_capacity": self._profile.max_episodes,
                "episode_capacity_exhausted": (
                    len(self._episodes) >= self._profile.max_episodes
                ),
                "distinction_count": len(self._distinctions),
                "distinction_capacity": self._profile.max_distinctions,
                "distinction_capacity_exhausted": (
                    len(self._distinctions)
                    >= self._profile.max_distinctions
                ),
                "learned_referent_count": len(learned),
                "unresolved_referent_count": len(unresolved),
                "retained_proof_episode_count": len(proof_episode_ids),
                "unsettled_episode_count": len(
                    set(self._episodes) - proof_episode_ids
                ),
                "encoded_state_bytes": encoded_bytes,
                "state_byte_capacity": self._profile.max_state_bytes,
                "state_bytes_remaining": (
                    self._profile.max_state_bytes - encoded_bytes
                ),
                "state_byte_capacity_exhausted": (
                    encoded_bytes >= self._profile.max_state_bytes
                ),
            }

    def admit_episode(
        self,
        *,
        motif_owner: AuditoryRecurrentMotifOwner,
        auditory_event: AuditoryReceptorFullFieldEvent,
        auditory_experience: AuditoryReceptorExperience,
        settlement: CausalExperienceSettlement,
    ) -> GroundingEpisodeAdmission:
        _verify_auditory_transaction_link(
            auditory_event=auditory_event,
            auditory_experience=auditory_experience,
            settlement=settlement,
        )
        firing, bank_digest, reason = _stable_firing(
            motif_owner=motif_owner,
            experience=auditory_experience,
        )
        if firing is None or bank_digest is None:
            return GroundingEpisodeAdmission(
                state=GroundingAdmissionState.INDETERMINATE_RESOURCE,
                reason=reason,
                episode=None,
                stored=False,
            )
        if not firing.firing_motif_neuron_ids:
            return GroundingEpisodeAdmission(
                state=GroundingAdmissionState.UNKNOWN,
                reason="no recurrent auditory motif fired",
                episode=None,
                stored=False,
            )
        if (
            len(firing.firing_motif_neuron_ids)
            > self._profile.max_firing_motifs_per_episode
            or len(firing.activations)
            > self._profile.max_activations_per_episode
        ):
            return GroundingEpisodeAdmission(
                state=GroundingAdmissionState.INDETERMINATE_RESOURCE,
                reason="grounding auditory activation capacity exhausted",
                episode=None,
                stored=False,
            )
        if any(
            activation.source_time_start < settlement.source_time_start
            or activation.source_time_end > settlement.source_time_end
            for activation in firing.activations
        ):
            raise ValueError(
                "auditory motif activation is outside causal settlement"
            )
        roots = _roots_from_settlement(settlement)
        if not roots:
            return GroundingEpisodeAdmission(
                state=GroundingAdmissionState.UNKNOWN,
                reason="causal settlement has no non-auditory roots",
                episode=None,
                stored=False,
            )
        if len(roots) > self._profile.max_roots_per_episode:
            return GroundingEpisodeAdmission(
                state=GroundingAdmissionState.INDETERMINATE_RESOURCE,
                reason="grounding causal-root capacity exhausted",
                episode=None,
                stored=False,
            )
        activation_evidence = tuple(
            GroundingActivationEvidence.from_activation(value)
            for value in firing.activations
        )
        identity_payload = {
            "auditory_experience_receipt_sha256": (
                auditory_experience.authority_receipt_sha256
            ),
            "auditory_source_event_receipt_sha256": (
                auditory_experience.source_event_receipt_sha256
            ),
            "firing_motif_neuron_ids": list(
                firing.firing_motif_neuron_ids
            ),
            "roots": [
                [value.root_id, value.value_sha256] for value in roots
            ],
            "source_time_end": _fraction_text(settlement.source_time_end),
            "source_time_start": _fraction_text(
                settlement.source_time_start
            ),
        }
        episode_id = _digest(identity_payload)
        provisional = GroundingEpisode(
            episode_id=episode_id,
            auditory_experience_receipt_sha256=(
                auditory_experience.authority_receipt_sha256
            ),
            auditory_source_event_receipt_sha256=(
                auditory_experience.source_event_receipt_sha256
            ),
            settlement_authority_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            motif_bank_state_sha256=bank_digest,
            source_time_start=settlement.source_time_start,
            source_time_end=settlement.source_time_end,
            firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
            unresolved_source_indices=firing.unresolved_source_indices,
            activations=activation_evidence,
            roots=roots,
            authority_hmac_sha256="",
        )
        episode = GroundingEpisode(
            **{
                field: getattr(provisional, field)
                for field in (
                    "episode_id",
                    "auditory_experience_receipt_sha256",
                    "auditory_source_event_receipt_sha256",
                    "settlement_authority_receipt_sha256",
                    "motif_bank_state_sha256",
                    "source_time_start",
                    "source_time_end",
                    "firing_motif_neuron_ids",
                    "unresolved_source_indices",
                    "activations",
                    "roots",
                )
            },
            authority_hmac_sha256=_sign(
                self._episode_key,
                _EPISODE_DOMAIN,
                provisional.payload(),
            ),
        )
        episode.verify(
            authority_key=self._episode_key,
            profile=self._profile,
        )
        with self._lock:
            existing = self._episodes.get(episode_id)
            if existing is not None:
                return GroundingEpisodeAdmission(
                    state=GroundingAdmissionState.DUPLICATE,
                    reason="grounding episode already exists",
                    episode=existing,
                    stored=False,
                )
            if len(self._episodes) >= self._profile.max_episodes:
                return GroundingEpisodeAdmission(
                    state=GroundingAdmissionState.INDETERMINATE_RESOURCE,
                    reason="grounding episode capacity exhausted",
                    episode=None,
                    stored=False,
                )
            staged = dict(self._episodes)
            staged[episode_id] = episode
            self._encoded_state(staged, self._distinctions)
            self._episodes = staged
        return GroundingEpisodeAdmission(
            state=GroundingAdmissionState.ADMITTED,
            reason="exact motif and six-sense causal episode admitted",
            episode=episode,
            stored=True,
        )

    def learn_controlled_distinction(
        self,
        episode_ids: tuple[str, ...],
    ) -> GroundingLearningResult:
        if (
            not isinstance(episode_ids, tuple)
            or len(episode_ids) < 2
            or tuple(sorted(set(episode_ids))) != tuple(sorted(episode_ids))
        ):
            raise ValueError(
                "controlled grounding requires distinct episode identities"
            )
        with self._lock:
            try:
                episodes = tuple(
                    self._episodes[value] for value in episode_ids
                )
            except KeyError:
                return GroundingLearningResult(
                    state=GroundingLearningState.UNKNOWN,
                    reason="grounding episode is unavailable",
                    distinction=None,
                )
            for episode in episodes:
                episode.verify(
                    authority_key=self._episode_key,
                    profile=self._profile,
                )
            root_maps = tuple(
                {root.root_id: root for root in episode.roots}
                for episode in episodes
            )
            root_ids = set(root_maps[0])
            if any(set(value) != root_ids for value in root_maps[1:]):
                return GroundingLearningResult(
                    state=GroundingLearningState.AMBIGUOUS,
                    reason="controlled causal topology changed",
                    distinction=None,
                )
            changed = tuple(
                root_id for root_id in sorted(root_ids)
                if len({
                    value[root_id].value_sha256 for value in root_maps
                }) > 1
            )
            if not changed:
                return GroundingLearningResult(
                    state=GroundingLearningState.UNKNOWN,
                    reason="controlled episodes contain no causal contrast",
                    distinction=None,
                )
            if len(changed) != 1:
                return GroundingLearningResult(
                    state=GroundingLearningState.AMBIGUOUS,
                    reason="causal fission: more than one referent root changed",
                    distinction=None,
                )
            referent_root_id = changed[0]
            background = tuple(
                root_maps[0][root_id]
                for root_id in sorted(root_ids - {referent_root_id})
            )
            family_id = _digest({
                "background_roots": [
                    [value.root_id, value.value_sha256]
                    for value in background
                ],
                "referent_root_id": referent_root_id,
            })
            prior = self._distinctions.get(family_id)
            all_episode_ids = set(episode_ids)
            if prior is not None:
                prior.verify(self._distinction_key)
                all_episode_ids.update(prior.proof_episode_ids)
            proof_episodes = tuple(
                self._episodes[value] for value in sorted(all_episode_ids)
            )
            for episode in proof_episodes:
                roots = {root.root_id: root for root in episode.roots}
                if (
                    set(roots) != root_ids
                    or any(
                        roots[root.root_id].value_sha256
                        != root.value_sha256
                        for root in background
                    )
                ):
                    return GroundingLearningResult(
                        state=GroundingLearningState.AMBIGUOUS,
                        reason=(
                            "refinement left its controlled causal background"
                        ),
                        distinction=None,
                    )
            grouped: dict[str, list[GroundingEpisode]] = {}
            referent_roots: dict[str, GroundingRoot] = {}
            for episode in proof_episodes:
                root = {
                    value.root_id: value for value in episode.roots
                }[referent_root_id]
                grouped.setdefault(root.value_sha256, []).append(episode)
                referent_roots[root.value_sha256] = root
            if len(grouped) < 2:
                return GroundingLearningResult(
                    state=GroundingLearningState.UNKNOWN,
                    reason="controlled contrast has fewer than two alternatives",
                    distinction=None,
                )
            if any(
                len(values) < _MIN_INDEPENDENT_POSITIVE_EPISODES
                for values in grouped.values()
            ):
                return GroundingLearningResult(
                    state=GroundingLearningState.UNKNOWN,
                    reason=(
                        "each referent requires two independent positive "
                        "causal episodes"
                    ),
                    distinction=None,
                )
            if any(
                len({
                    value.auditory_source_event_receipt_sha256
                    for value in values
                })
                != len(values)
                for values in grouped.values()
            ):
                return GroundingLearningResult(
                    state=GroundingLearningState.UNKNOWN,
                    reason=(
                        "positive grounding episodes must have distinct "
                        "physical auditory source events"
                    ),
                    distinction=None,
                )
            alternatives = []
            for value_sha256 in sorted(grouped):
                positives = grouped[value_sha256]
                positive_common = set(
                    positives[0].firing_motif_neuron_ids
                )
                for episode in positives[1:]:
                    positive_common.intersection_update(
                        episode.firing_motif_neuron_ids
                    )
                contrast_union = set()
                for other_sha256, contrast_episodes in grouped.items():
                    if other_sha256 == value_sha256:
                        continue
                    for episode in contrast_episodes:
                        contrast_union.update(
                            episode.firing_motif_neuron_ids
                        )
                diagnostic = tuple(sorted(
                    positive_common - contrast_union
                ))
                alternatives.append(DiagnosticReferent(
                    root=referent_roots[value_sha256],
                    positive_episode_ids=tuple(sorted(
                        value.episode_id for value in positives
                    )),
                    diagnostic_motif_neuron_ids=diagnostic,
                ))
            alternative_tuple = tuple(alternatives)
            proof_ids = tuple(sorted(all_episode_ids))
            provisional = ControlledGroundingDistinction(
                distinction_id="0" * 64,
                family_id=family_id,
                referent_root_id=referent_root_id,
                background_roots=background,
                alternatives=alternative_tuple,
                proof_episode_ids=proof_ids,
                authority_hmac_sha256="",
            )
            payload = provisional.payload()
            distinction = ControlledGroundingDistinction(
                distinction_id=_digest(payload),
                family_id=family_id,
                referent_root_id=referent_root_id,
                background_roots=background,
                alternatives=alternative_tuple,
                proof_episode_ids=proof_ids,
                authority_hmac_sha256=_sign(
                    self._distinction_key,
                    _DISTINCTION_DOMAIN,
                    payload,
                ),
            )
            distinction.verify(self._distinction_key)
            staged = dict(self._distinctions)
            if (
                family_id not in staged
                and len(staged) >= self._profile.max_distinctions
            ):
                return GroundingLearningResult(
                    state=GroundingLearningState.INDETERMINATE_RESOURCE,
                    reason="grounding distinction capacity exhausted",
                    distinction=None,
                )
            staged[family_id] = distinction
            try:
                self._encoded_state(self._episodes, staged)
            except GroundingCapacityError:
                return GroundingLearningResult(
                    state=GroundingLearningState.INDETERMINATE_RESOURCE,
                    reason="grounding state-byte capacity exhausted",
                    distinction=None,
                )
            self._distinctions = staged
            unresolved = tuple(
                value.root.value_sha256
                for value in alternatives
                if not value.diagnostic_motif_neuron_ids
            )
            return GroundingLearningResult(
                state=GroundingLearningState.SETTLED,
                reason=(
                    "controlled distributed diagnostic conjunction settled"
                ),
                distinction=distinction,
                unresolved_referent_value_sha256s=unresolved,
            )

    def resolve(
        self,
        *,
        motif_owner: AuditoryRecurrentMotifOwner,
        auditory_experience: AuditoryReceptorExperience,
    ) -> GroundingResolution:
        firing, _bank_digest, reason = _stable_firing(
            motif_owner=motif_owner,
            experience=auditory_experience,
        )
        if firing is None:
            return GroundingResolution(
                state=GroundingResolutionState.INDETERMINATE_RESOURCE,
                reason=reason,
                firing_motif_neuron_ids=(),
                referents=(),
                diagnostics=(),
                ungrounded_motif_neuron_ids=(),
            )
        active = set(firing.firing_motif_neuron_ids)
        with self._lock:
            distinctions = self.distinctions
        diagnostics = []
        resolved: dict[
            tuple[str, str],
            tuple[GroundingRoot, set[str], set[str]],
        ] = {}
        grounded_motifs = set()
        for distinction in distinctions:
            distinction.verify(self._distinction_key)
            for alternative in distinction.alternatives:
                required = set(
                    alternative.diagnostic_motif_neuron_ids
                )
                grounded_motifs.update(required)
                present = required.intersection(active)
                missing = required - active
                if not required:
                    state = DiagnosticActivationState.UNRESOLVED_EMPTY
                elif not missing:
                    state = DiagnosticActivationState.RESOLVED
                    key = (
                        alternative.root.root_id,
                        alternative.root.value_sha256,
                    )
                    mounted = resolved.get(key)
                    if mounted is None:
                        mounted = (
                            alternative.root,
                            set(),
                            set(),
                        )
                        resolved[key] = mounted
                    mounted[1].update(required)
                    mounted[2].add(distinction.distinction_id)
                elif present:
                    state = DiagnosticActivationState.PARTIAL
                else:
                    state = DiagnosticActivationState.ABSENT
                diagnostics.append(DiagnosticActivation(
                    distinction_id=distinction.distinction_id,
                    root=alternative.root,
                    state=state,
                    required_motif_neuron_ids=tuple(sorted(required)),
                    present_motif_neuron_ids=tuple(sorted(present)),
                    missing_motif_neuron_ids=tuple(sorted(missing)),
                ))
        referents = []
        for key in sorted(resolved):
            root, contributing_ids, distinction_ids = resolved[key]
            referents.append(ResolvedGroundedReferent(
                root=root,
                contributing_motif_neuron_ids=tuple(
                    sorted(contributing_ids)
                ),
                contributing_activations=tuple(
                    activation for activation in firing.activations
                    if activation.neuron_id in contributing_ids
                ),
                distinction_ids=tuple(sorted(distinction_ids)),
            ))
        state = (
            GroundingResolutionState.RESOLVED
            if referents else GroundingResolutionState.UNKNOWN
        )
        return GroundingResolution(
            state=state,
            reason=(
                "all complete active diagnostic conjunctions resolved"
                if referents
                else "no complete nonempty diagnostic conjunction fired"
            ),
            firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
            referents=tuple(referents),
            diagnostics=tuple(diagnostics),
            ungrounded_motif_neuron_ids=tuple(sorted(
                active - grounded_motifs
            )),
        )

    def resolve_linked(
        self,
        *,
        motif_owner: AuditoryRecurrentMotifOwner,
        auditory_event: AuditoryReceptorFullFieldEvent,
        auditory_experience: AuditoryReceptorExperience,
        settlement: CausalExperienceSettlement,
    ) -> GroundingResolution:
        """Resolve only after proving the prompt's physical transaction."""

        _verify_auditory_transaction_link(
            auditory_event=auditory_event,
            auditory_experience=auditory_experience,
            settlement=settlement,
        )
        return self.resolve(
            motif_owner=motif_owner,
            auditory_experience=auditory_experience,
        )

    def _body(
        self,
        episodes: Mapping[str, GroundingEpisode],
        distinctions: Mapping[str, ControlledGroundingDistinction],
    ) -> dict[str, object]:
        return {
            "distinctions": [
                distinctions[key].as_record()
                for key in sorted(distinctions)
            ],
            "episodes": [
                episodes[key].as_record() for key in sorted(episodes)
            ],
            "resource_profile": (
                self._profile.payload()
                | {
                    "authority_receipt_sha256": (
                        self._profile.authority_receipt_sha256
                    )
                }
            ),
            "schema": GROUNDING_STATE_SCHEMA,
        }

    def _encoded_state(
        self,
        episodes: Mapping[str, GroundingEpisode],
        distinctions: Mapping[str, ControlledGroundingDistinction],
    ) -> bytes:
        if (
            len(episodes) > self._profile.max_episodes
            or len(distinctions) > self._profile.max_distinctions
        ):
            raise GroundingCapacityError(
                "grounding collection capacity exhausted"
            )
        body = self._body(episodes, distinctions)
        envelope = {
            "body": body,
            "schema": GROUNDING_ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key, _STATE_DOMAIN, body
            ),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise GroundingCapacityError(
                "grounding state-byte capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded_state(
                self._episodes, self._distinctions
            )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "AuditoryMotifCausalGroundingOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("grounding state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("grounding state is not canonical JSON") from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != GROUNDING_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("grounding state envelope changed")
        body = envelope["body"]
        if (
            set(body)
            != {
                "distinctions",
                "episodes",
                "resource_profile",
                "schema",
            }
            or body.get("schema") != GROUNDING_STATE_SCHEMA
            or not isinstance(body.get("episodes"), list)
            or not isinstance(body.get("distinctions"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("grounding state body changed")
        raw_profile = body["resource_profile"]
        expected_profile_keys = {
            "authority_receipt_sha256",
            "max_activations_per_episode",
            "max_distinctions",
            "max_episode_bytes",
            "max_episodes",
            "max_firing_motifs_per_episode",
            "max_roots_per_episode",
            "max_state_bytes",
            "profile_id",
            "schema",
        }
        if set(raw_profile) != expected_profile_keys:
            raise ValueError("grounding resource profile record changed")
        profile = AuditoryMotifGroundingResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_episodes=raw_profile.get("max_episodes"),
            max_distinctions=raw_profile.get("max_distinctions"),
            max_firing_motifs_per_episode=raw_profile.get(
                "max_firing_motifs_per_episode"
            ),
            max_activations_per_episode=raw_profile.get(
                "max_activations_per_episode"
            ),
            max_roots_per_episode=raw_profile.get(
                "max_roots_per_episode"
            ),
            max_episode_bytes=raw_profile.get("max_episode_bytes"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
        )
        if not hmac.compare_digest(
            envelope["state_hmac_sha256"],
            _sign(owner._state_key, _STATE_DOMAIN, body),
        ):
            raise ValueError("grounding state HMAC changed")
        if len(encoded) > profile.max_state_bytes:
            raise ValueError("grounding state exceeds resource profile")
        for raw in body["episodes"]:
            episode = owner._episode_from_record(raw)
            if episode.episode_id in owner._episodes:
                raise ValueError("grounding state repeats an episode")
            owner._episodes[episode.episode_id] = episode
        for raw in body["distinctions"]:
            distinction = owner._distinction_from_record(raw)
            if distinction.family_id in owner._distinctions:
                raise ValueError("grounding state repeats a distinction family")
            if any(
                episode_id not in owner._episodes
                for episode_id in distinction.proof_episode_ids
            ):
                raise ValueError(
                    "grounding distinction lost its proof episode"
                )
            owner._distinctions[distinction.family_id] = distinction
        if (
            len(owner._episodes) > profile.max_episodes
            or len(owner._distinctions) > profile.max_distinctions
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("grounding restored state changed")
        return owner

    def _episode_from_record(self, value: object) -> GroundingEpisode:
        expected = {
            "activations",
            "auditory_experience_receipt_sha256",
            "auditory_source_event_receipt_sha256",
            "authority_hmac_sha256",
            "episode_id",
            "firing_motif_neuron_ids",
            "motif_bank_state_sha256",
            "roots",
            "schema",
            "settlement_authority_receipt_sha256",
            "source_time_end",
            "source_time_start",
            "unresolved_source_indices",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != GROUNDING_EPISODE_SCHEMA
            or not isinstance(value.get("activations"), list)
            or not isinstance(value.get("roots"), list)
            or not isinstance(value.get("firing_motif_neuron_ids"), list)
            or not isinstance(value.get("unresolved_source_indices"), list)
        ):
            raise ValueError("grounding episode record changed")
        episode = GroundingEpisode(
            episode_id=value.get("episode_id"),
            auditory_experience_receipt_sha256=value.get(
                "auditory_experience_receipt_sha256"
            ),
            auditory_source_event_receipt_sha256=value.get(
                "auditory_source_event_receipt_sha256"
            ),
            settlement_authority_receipt_sha256=value.get(
                "settlement_authority_receipt_sha256"
            ),
            motif_bank_state_sha256=value.get(
                "motif_bank_state_sha256"
            ),
            source_time_start=_fraction(
                value.get("source_time_start"),
                "grounding episode source start",
            ),
            source_time_end=_fraction(
                value.get("source_time_end"),
                "grounding episode source end",
            ),
            firing_motif_neuron_ids=tuple(
                value["firing_motif_neuron_ids"]
            ),
            unresolved_source_indices=tuple(
                value["unresolved_source_indices"]
            ),
            activations=tuple(
                _activation_from_record(item)
                for item in value["activations"]
            ),
            roots=tuple(
                _root_from_record(item) for item in value["roots"]
            ),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
        )
        episode.verify(
            authority_key=self._episode_key,
            profile=self._profile,
        )
        if episode.as_record() != dict(value):
            raise ValueError("grounding episode record is not canonical")
        return episode

    def _distinction_from_record(
        self,
        value: object,
    ) -> ControlledGroundingDistinction:
        expected = {
            "alternatives",
            "authority_hmac_sha256",
            "background_roots",
            "distinction_id",
            "family_id",
            "proof_episode_ids",
            "referent_root_id",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != GROUNDING_DISTINCTION_SCHEMA
            or not isinstance(value.get("alternatives"), list)
            or not isinstance(value.get("background_roots"), list)
            or not isinstance(value.get("proof_episode_ids"), list)
        ):
            raise ValueError("grounding distinction record changed")
        alternatives = []
        for raw in value["alternatives"]:
            if (
                not isinstance(raw, Mapping)
                or set(raw)
                != {
                    "diagnostic_motif_neuron_ids",
                    "positive_episode_ids",
                    "root",
                }
                or not isinstance(
                    raw.get("diagnostic_motif_neuron_ids"), list
                )
                or not isinstance(raw.get("positive_episode_ids"), list)
            ):
                raise ValueError(
                    "grounding diagnostic referent record changed"
                )
            alternatives.append(DiagnosticReferent(
                root=_root_from_record(raw.get("root")),
                positive_episode_ids=tuple(raw["positive_episode_ids"]),
                diagnostic_motif_neuron_ids=tuple(
                    raw["diagnostic_motif_neuron_ids"]
                ),
            ))
        result = ControlledGroundingDistinction(
            distinction_id=value.get("distinction_id"),
            family_id=value.get("family_id"),
            referent_root_id=value.get("referent_root_id"),
            background_roots=tuple(
                _root_from_record(item)
                for item in value["background_roots"]
            ),
            alternatives=tuple(alternatives),
            proof_episode_ids=tuple(value["proof_episode_ids"]),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
        )
        result.verify(self._distinction_key)
        if result.as_record() != dict(value):
            raise ValueError("grounding distinction record is not canonical")
        return result


class GroundingCapacityError(RuntimeError):
    """A fixed grounding resource boundary was reached without mutation."""


__all__ = (
    "AuditoryMotifCausalGroundingOwner",
    "AuditoryMotifGroundingResourceProfile",
    "ControlledGroundingDistinction",
    "DiagnosticActivation",
    "DiagnosticActivationState",
    "DiagnosticReferent",
    "GroundingActivationEvidence",
    "GroundingAdmissionState",
    "GroundingCapacityError",
    "GroundingEpisode",
    "GroundingEpisodeAdmission",
    "GroundingLearningResult",
    "GroundingLearningState",
    "GroundingResolution",
    "GroundingResolutionState",
    "GroundingRoot",
    "ResolvedGroundedReferent",
)
