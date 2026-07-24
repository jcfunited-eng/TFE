"""Bounded deterministic auditory L5 for exact two-ear W1 settlements.

This owner consumes only the authenticated compact causal settlement.  It
preserves every ordered D/M/R/U/C/P/B field for left and right cochleae and
never reconstructs raw pressure, assigns source identity, recognizes words,
or uses chi as meaning.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactFieldTuple,
    ExactSubstreamInterpretation,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    COCHLEAR_ORDER,
    OBSERVATION_HOP_SAMPLES,
)


W1_BINAURAL_AUDITORY_L5_SCHEMA = "guala.w1.binaural_auditory_l5.v1"
W1_BINAURAL_AUDITORY_L5_AUTHORITY_SCHEMA = (
    "guala.w1.binaural_auditory_l5.authority.v1"
)
MAX_W1_BINAURAL_AUDITORY_L5_BYTES = 2 * 1024 * 1024
MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES = 4 * 1024 * 1024
W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA = (
    "guala.w1.binaural_auditory_l5.state.v1"
)
EAR_IDS = ("left", "right")
COMPONENT_IDS = ("pressure-envelope", "carrier-phase-advance")


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


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "W1 binaural L5 fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not a canonical fraction")
    return result


def _component_payload(
    component: ExactSubstreamInterpretation,
) -> dict[str, object]:
    return {
        "coordinates": [list(value) for value in component.coordinates],
        "field_tuples": [
            {
                "fields": [
                    [name, _fraction_text(field)]
                    for name, field in value.fields
                ],
                "tuple_index": value.tuple_index,
            }
            for value in component.field_tuples
        ],
        "physical_quantity": component.physical_quantity,
        "physical_unit": component.physical_unit,
        "sensor_id": component.sensor_id,
        "substream_id": component.substream_id,
        "topology_index": component.topology_index,
    }


def _component_authority_payload(
    component: ExactSubstreamInterpretation,
) -> dict[str, object]:
    return {
        **_component_payload(component),
        "field_tuple_receipt_sha256s": [
            value.authority_receipt_sha256
            for value in component.field_tuples
        ],
        "kernel_basin_receipt_sha256": (
            component.kernel_basin_receipt_sha256
        ),
        "profile_receipt_sha256": component.profile_receipt_sha256,
        "source_sample_commitment_sha256": (
            component.source_sample_commitment_sha256
        ),
        "source_sample_count": component.source_sample_count,
        "source_evidence_stream_receipt_sha256": (
            component.source_evidence_stream_receipt_sha256
        ),
    }


@dataclass(frozen=True, slots=True)
class W1BinauralAuditoryL5Channel:
    cochlear_index: int
    channel_id: str
    pressure: ExactSubstreamInterpretation
    carrier_phase_advance: ExactSubstreamInterpretation


@dataclass(frozen=True, slots=True)
class W1BinauralAuditoryL5Ear:
    ear_id: str
    channels: tuple[W1BinauralAuditoryL5Channel, ...]


def _channel_payload(
    channel: W1BinauralAuditoryL5Channel,
    *,
    authority: bool,
) -> dict[str, object]:
    component_payload = (
        _component_authority_payload if authority else _component_payload
    )
    return {
        "carrier_phase_advance": component_payload(
            channel.carrier_phase_advance
        ),
        "channel_id": channel.channel_id,
        "cochlear_index": channel.cochlear_index,
        "pressure": component_payload(channel.pressure),
    }


def _ears_payload(
    ears: tuple[W1BinauralAuditoryL5Ear, ...],
    *,
    authority: bool,
) -> list[dict[str, object]]:
    return [
        {
            "channels": [
                _channel_payload(channel, authority=authority)
                for channel in ear.channels
            ],
            "ear_id": ear.ear_id,
        }
        for ear in ears
    ]


@dataclass(frozen=True, slots=True)
class W1BinauralAuditoryL5Experience:
    experience_id: str
    structural_fingerprint: str
    assembly_id: str
    relation: str
    source_time_start: Fraction
    source_time_end: Fraction
    ears: tuple[W1BinauralAuditoryL5Ear, ...]
    upstream_causal_settlement_receipt_sha256: str
    authority_receipt_sha256: str

    def structural_payload(self) -> dict[str, object]:
        return {
            "ears": _ears_payload(self.ears, authority=False),
            "schema": W1_BINAURAL_AUDITORY_L5_SCHEMA,
        }

    def authority_payload(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "ears": _ears_payload(self.ears, authority=True),
            "experience_id": self.experience_id,
            "relation": self.relation,
            "schema": W1_BINAURAL_AUDITORY_L5_AUTHORITY_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "structural_fingerprint": self.structural_fingerprint,
            "upstream_causal_settlement_receipt_sha256": (
                self.upstream_causal_settlement_receipt_sha256
            ),
        }

    def verify(self) -> None:
        _validate_ears(self.ears)
        require_identifier(self.assembly_id, "W1 binaural L5 assembly")
        require_fraction(self.source_time_start, "W1 binaural L5 source start")
        require_fraction(self.source_time_end, "W1 binaural L5 source end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("W1 binaural L5 source interval changed")
        if self.relation not in (
            "first_observation",
            "recurrence",
            "structural_change",
        ):
            raise ReceiptError("W1 binaural L5 relation changed")
        sha256_digest(
            self.upstream_causal_settlement_receipt_sha256,
            "W1 binaural L5 upstream settlement",
        )
        structural = _digest(self.structural_payload())
        if structural != self.structural_fingerprint:
            raise ReceiptError("W1 binaural L5 full field changed")
        expected_id = _digest({
            "binaural_structural_fingerprint": structural,
        })
        if self.experience_id != expected_id:
            raise ReceiptError("W1 binaural L5 experience identity changed")
        payload = self.authority_payload()
        if (
            len(_canonical(payload)) > MAX_W1_BINAURAL_AUDITORY_L5_BYTES
            or _digest(payload) != self.authority_receipt_sha256
        ):
            raise ReceiptError("W1 binaural L5 authority changed")

    def persistence_record(self) -> dict[str, object]:
        """Return the bounded raw-pressure-free authority record."""
        self.verify()
        return {
            **self.authority_payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _validate_component(
    component: ExactSubstreamInterpretation,
    *,
    ear_id: str,
    channel_index: int,
    component_index: int,
) -> None:
    if not isinstance(component, ExactSubstreamInterpretation):
        raise ReceiptError("W1 binaural L5 component is not typed")
    definition = AUDITORY_CHANNELS[channel_index]
    component_id = COMPONENT_IDS[component_index]
    topology_index = (
        EAR_IDS.index(ear_id) * AUDITORY_KERNEL_COMPONENT_COUNT
        + channel_index * 2
        + component_index
    )
    expected_coordinates = (
        ("acoustic-receptor", ear_id),
        ("cochlear-channel", definition.name),
        ("kernel-component", component_id),
        ("centre-hz", str(definition.centre_hz)),
        ("erb-width-hz", str(definition.erb_width_hz)),
        ("gammatone-order", str(COCHLEAR_ORDER)),
        ("observation-hop-samples", str(OBSERVATION_HOP_SAMPLES)),
    )
    expected_suffix = (
        "pressure" if component_index == 0 else "phase_advance"
    )
    expected_quantity = (
        "cochlear-pressure-envelope"
        if component_index == 0
        else "cochlear-carrier-phase-advance"
    )
    expected_unit = (
        "full-scale-pressure"
        if component_index == 0
        else "nyquist-fraction-per-observation-hop"
    )
    if (
        component.sensor_id != f"W1-calibrated-{ear_id}-cochlear-field"
        or component.substream_id
        != f"{ear_id}-{definition.name}_{expected_suffix}"
        or component.topology_index != topology_index
        or component.coordinates != expected_coordinates
        or component.physical_quantity != expected_quantity
        or component.physical_unit != expected_unit
        or not component.field_tuples
    ):
        raise ReceiptError("W1 binaural L5 cochlear topology changed")
    for name, receipt in (
        ("profile", component.profile_receipt_sha256),
        ("source", component.source_evidence_stream_receipt_sha256),
        ("source commitment", component.source_sample_commitment_sha256),
        ("kernel basin", component.kernel_basin_receipt_sha256),
    ):
        sha256_digest(receipt, f"W1 binaural L5 {name}")
    if (
        isinstance(component.source_sample_count, bool)
        or not isinstance(component.source_sample_count, int)
        or component.source_sample_count <= 0
    ):
        raise ReceiptError("W1 binaural L5 source cardinality changed")
    for tuple_index, field_tuple in enumerate(component.field_tuples):
        if (
            field_tuple.tuple_index != tuple_index
            or tuple(name for name, _value in field_tuple.fields)
            != DSF_FIELD_ORDER
        ):
            raise ReceiptError("W1 binaural L5 DSF field order changed")
        for _name, value in field_tuple.fields:
            require_fraction(value, "W1 binaural L5 DSF field")
        sha256_digest(
            field_tuple.authority_receipt_sha256,
            "W1 binaural L5 field tuple",
        )


def _validate_ears(
    ears: tuple[W1BinauralAuditoryL5Ear, ...],
) -> None:
    if (
        not isinstance(ears, tuple)
        or tuple(ear.ear_id for ear in ears) != EAR_IDS
    ):
        raise ReceiptError("W1 binaural L5 requires ordered left and right ears")
    seen_receipts: set[str] = set()
    for ear in ears:
        if (
            not isinstance(ear, W1BinauralAuditoryL5Ear)
            or len(ear.channels) != COCHLEAR_CHANNEL_COUNT
        ):
            raise ReceiptError("W1 binaural L5 ear is incomplete")
        for channel_index, channel in enumerate(ear.channels):
            if (
                not isinstance(channel, W1BinauralAuditoryL5Channel)
                or channel.cochlear_index != channel_index
                or channel.channel_id != AUDITORY_CHANNELS[channel_index].name
            ):
                raise ReceiptError("W1 binaural L5 channel order changed")
            _validate_component(
                channel.pressure,
                ear_id=ear.ear_id,
                channel_index=channel_index,
                component_index=0,
            )
            _validate_component(
                channel.carrier_phase_advance,
                ear_id=ear.ear_id,
                channel_index=channel_index,
                component_index=1,
            )
            if (
                channel.pressure.source_sample_count
                != channel.carrier_phase_advance.source_sample_count
            ):
                raise ReceiptError("W1 binaural L5 component grids changed")
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                identities = (
                    component.profile_receipt_sha256,
                    component.source_evidence_stream_receipt_sha256,
                    component.kernel_basin_receipt_sha256,
                )
                if any(identity in seen_receipts for identity in identities):
                    raise ReceiptError(
                        "W1 binaural L5 components are not independent"
                    )
                seen_receipts.update(identities)


def _component_from_authority_record(
    value: object,
) -> ExactSubstreamInterpretation:
    if not isinstance(value, dict):
        raise ValueError("W1 binaural L5 component record changed")
    tuples = value.get("field_tuples")
    receipts = value.get("field_tuple_receipt_sha256s")
    if (
        not isinstance(tuples, list)
        or not isinstance(receipts, list)
        or len(tuples) != len(receipts)
        or not tuples
    ):
        raise ValueError("W1 binaural L5 tuple record changed")
    field_tuples = []
    for index, (field_tuple, receipt) in enumerate(
        zip(tuples, receipts, strict=True)
    ):
        if (
            not isinstance(field_tuple, dict)
            or set(field_tuple) != {"fields", "tuple_index"}
            or field_tuple.get("tuple_index") != index
            or not isinstance(field_tuple.get("fields"), list)
            or len(field_tuple["fields"]) != len(DSF_FIELD_ORDER)
        ):
            raise ValueError("W1 binaural L5 field tuple changed")
        fields = []
        for expected_name, item in zip(
            DSF_FIELD_ORDER,
            field_tuple["fields"],
            strict=True,
        ):
            if (
                not isinstance(item, list)
                or len(item) != 2
                or item[0] != expected_name
            ):
                raise ValueError("W1 binaural L5 field order changed")
            fields.append((
                expected_name,
                _fraction_from_text(
                    item[1],
                    f"W1 binaural L5 {expected_name}",
                ),
            ))
        field_tuples.append(ExactFieldTuple(
            tuple_index=index,
            fields=tuple(fields),
            authority_receipt_sha256=str(receipt),
        ))
    coordinates = value.get("coordinates")
    if (
        not isinstance(coordinates, list)
        or any(
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(part, str) for part in item)
            for item in coordinates
        )
    ):
        raise ValueError("W1 binaural L5 coordinates changed")
    result = ExactSubstreamInterpretation(
        sensor_id=value.get("sensor_id"),
        substream_id=value.get("substream_id"),
        topology_index=value.get("topology_index"),
        coordinates=tuple(tuple(item) for item in coordinates),
        physical_quantity=value.get("physical_quantity"),
        physical_unit=value.get("physical_unit"),
        profile_receipt_sha256=value.get("profile_receipt_sha256"),
        source_evidence_stream_receipt_sha256=value.get(
            "source_evidence_stream_receipt_sha256"
        ),
        source_sample_count=value.get("source_sample_count"),
        source_sample_commitment_sha256=value.get(
            "source_sample_commitment_sha256"
        ),
        kernel_basin_receipt_sha256=value.get(
            "kernel_basin_receipt_sha256"
        ),
        field_tuples=tuple(field_tuples),
    )
    if _component_authority_payload(result) != value:
        raise ValueError("W1 binaural L5 component authority changed")
    return result


def _experience_from_record(
    value: object,
) -> W1BinauralAuditoryL5Experience:
    if not isinstance(value, dict):
        raise ValueError("W1 binaural L5 experience record changed")
    ears_record = value.get("ears")
    if (
        not isinstance(ears_record, list)
        or len(ears_record) != len(EAR_IDS)
    ):
        raise ValueError("W1 binaural L5 ear record changed")
    ears = []
    for expected_ear, ear_record in zip(
        EAR_IDS,
        ears_record,
        strict=True,
    ):
        channels_record = (
            ear_record.get("channels")
            if isinstance(ear_record, dict) else None
        )
        if (
            ear_record.get("ear_id") != expected_ear
            or not isinstance(channels_record, list)
            or len(channels_record) != COCHLEAR_CHANNEL_COUNT
        ):
            raise ValueError("W1 binaural L5 ear record changed")
        channels = []
        for channel_index, channel_record in enumerate(channels_record):
            if not isinstance(channel_record, dict):
                raise ValueError("W1 binaural L5 channel record changed")
            channel = W1BinauralAuditoryL5Channel(
                cochlear_index=channel_record.get("cochlear_index"),
                channel_id=channel_record.get("channel_id"),
                pressure=_component_from_authority_record(
                    channel_record.get("pressure")
                ),
                carrier_phase_advance=_component_from_authority_record(
                    channel_record.get("carrier_phase_advance")
                ),
            )
            if (
                channel.cochlear_index != channel_index
                or _channel_payload(channel, authority=True)
                != channel_record
            ):
                raise ValueError("W1 binaural L5 channel authority changed")
            channels.append(channel)
        ears.append(W1BinauralAuditoryL5Ear(
            ear_id=expected_ear,
            channels=tuple(channels),
        ))
    result = W1BinauralAuditoryL5Experience(
        experience_id=value.get("experience_id"),
        structural_fingerprint=value.get("structural_fingerprint"),
        assembly_id=value.get("assembly_id"),
        relation=value.get("relation"),
        source_time_start=_fraction_from_text(
            value.get("source_time_start"),
            "W1 binaural L5 source start",
        ),
        source_time_end=_fraction_from_text(
            value.get("source_time_end"),
            "W1 binaural L5 source end",
        ),
        ears=tuple(ears),
        upstream_causal_settlement_receipt_sha256=value.get(
            "upstream_causal_settlement_receipt_sha256"
        ),
        authority_receipt_sha256=value.get(
            "authority_receipt_sha256"
        ),
    )
    result.verify()
    if result.persistence_record() != value:
        raise ValueError("W1 binaural L5 experience authority changed")
    return result


def _build_ears(
    settlement: CausalExperienceSettlement,
) -> tuple[W1BinauralAuditoryL5Ear, ...]:
    sound = next(
        (
            value
            for value in settlement.interpretations
            if value.sense == "sound"
        ),
        None,
    )
    if (
        sound is None
        or sound.state != "observed"
        or len(sound.substreams) != 2 * AUDITORY_KERNEL_COMPONENT_COUNT
    ):
        raise ReceiptError("W1 binaural L5 requires exactly 64 sound components")
    ears = []
    for ear_index, ear_id in enumerate(EAR_IDS):
        channels = []
        ear_offset = ear_index * AUDITORY_KERNEL_COMPONENT_COUNT
        for channel_index in range(COCHLEAR_CHANNEL_COUNT):
            component_offset = ear_offset + channel_index * 2
            channels.append(W1BinauralAuditoryL5Channel(
                cochlear_index=channel_index,
                channel_id=AUDITORY_CHANNELS[channel_index].name,
                pressure=sound.substreams[component_offset],
                carrier_phase_advance=sound.substreams[
                    component_offset + 1
                ],
            ))
        ears.append(W1BinauralAuditoryL5Ear(
            ear_id=ear_id,
            channels=tuple(channels),
        ))
    result = tuple(ears)
    _validate_ears(result)
    return result


@dataclass(frozen=True, slots=True)
class _CommitUndo:
    authority_receipt_sha256: str
    prior_latest: W1BinauralAuditoryL5Experience | None
    prior_transitions: tuple[tuple[tuple[str, str], int], ...]
    prior_settled: int
    prior_generation: int
    atomic_sequence_token: str | None


@dataclass(slots=True)
class _AtomicSequenceState:
    token: str
    owner_thread_id: int
    latest: W1BinauralAuditoryL5Experience | None
    transitions: OrderedDict[tuple[str, str], int]
    settled: int
    generation: int


@dataclass(frozen=True, slots=True)
class _AtomicSequenceCommitUndo:
    sequence: _AtomicSequenceState
    prior_latest: W1BinauralAuditoryL5Experience | None
    prior_transitions: tuple[tuple[tuple[str, str], int], ...]
    prior_settled: int
    prior_generation: int


class W1BinauralAuditoryL5Owner:
    """Capacity-one transactional owner of compact two-ear L5 fields."""

    def __init__(
        self,
        *,
        max_transitions: int = 1_024,
    ) -> None:
        if (
            isinstance(max_transitions, bool)
            or not isinstance(max_transitions, int)
            or max_transitions <= 0
        ):
            raise ValueError("W1 binaural L5 transition capacity is invalid")
        self._max_transitions = max_transitions
        self._latest: W1BinauralAuditoryL5Experience | None = None
        self._prepared: W1BinauralAuditoryL5Experience | None = None
        self._transitions: OrderedDict[tuple[str, str], int] = OrderedDict()
        self._settled = 0
        self._generation = 0
        self._atomic_sequence: _AtomicSequenceState | None = None
        self._lock = threading.RLock()

    def _require_sequence_owner_locked(self) -> None:
        sequence = self._atomic_sequence
        if (
            sequence is not None
            and sequence.owner_thread_id != threading.get_ident()
        ):
            raise RuntimeError(
                "W1 binaural L5 is reserved by an atomic sensory sequence"
            )

    def begin_atomic_sequence(self) -> str:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("W1 binaural L5 has a prepared experience")
            if self._atomic_sequence is not None:
                raise RuntimeError(
                    "W1 binaural L5 already has an atomic sensory sequence"
                )
            token = secrets.token_urlsafe(24)
            self._atomic_sequence = _AtomicSequenceState(
                token=token,
                owner_thread_id=threading.get_ident(),
                latest=self._latest,
                transitions=OrderedDict(self._transitions),
                settled=self._settled,
                generation=self._generation,
            )
            return token

    def verify_atomic_sequence(self, token: str) -> None:
        with self._lock:
            sequence = self._atomic_sequence
            if (
                sequence is None
                or sequence.token != token
                or sequence.owner_thread_id != threading.get_ident()
                or self._prepared is not None
            ):
                raise ValueError("W1 binaural L5 atomic sequence changed")

    def commit_atomic_sequence(self, token: str) -> _AtomicSequenceCommitUndo:
        with self._lock:
            self.verify_atomic_sequence(token)
            sequence = self._atomic_sequence
            if sequence is None:
                raise RuntimeError("W1 binaural L5 atomic sequence disappeared")
            undo = _AtomicSequenceCommitUndo(
                sequence=sequence,
                prior_latest=self._latest,
                prior_transitions=tuple(self._transitions.items()),
                prior_settled=self._settled,
                prior_generation=self._generation,
            )
            self._latest = sequence.latest
            self._transitions = sequence.transitions
            self._settled = sequence.settled
            self._generation = sequence.generation
            self._atomic_sequence = None
            return undo

    def rollback_committed_atomic_sequence(
        self,
        undo: _AtomicSequenceCommitUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(undo, _AtomicSequenceCommitUndo)
                or self._atomic_sequence is not None
                or self._latest != undo.sequence.latest
                or self._transitions != undo.sequence.transitions
                or self._settled != undo.sequence.settled
                or self._generation != undo.sequence.generation
            ):
                raise ValueError("W1 binaural L5 published sequence changed")
            self._latest = undo.prior_latest
            self._transitions = OrderedDict(undo.prior_transitions)
            self._settled = undo.prior_settled
            self._generation = undo.prior_generation
            self._atomic_sequence = undo.sequence

    def rollback_atomic_sequence(self, token: str) -> None:
        with self._lock:
            sequence = self._atomic_sequence
            if (
                sequence is None
                or sequence.token != token
                or sequence.owner_thread_id != threading.get_ident()
                or self._prepared is not None
            ):
                raise ValueError("W1 binaural L5 atomic sequence changed")
            self._atomic_sequence = None

    def prepare(
        self,
        settlement: CausalExperienceSettlement,
    ) -> W1BinauralAuditoryL5Experience:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("W1 binaural L5 requires a causal settlement")
        settlement.verify()
        ears = _build_ears(settlement)
        structural_payload = {
            "ears": _ears_payload(ears, authority=False),
            "schema": W1_BINAURAL_AUDITORY_L5_SCHEMA,
        }
        fingerprint = _digest(structural_payload)
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared is not None:
                raise RuntimeError("W1 binaural L5 transaction is already active")
            sequence = self._atomic_sequence
            prior_latest = sequence.latest if sequence is not None else self._latest
            previous = (
                prior_latest.structural_fingerprint
                if prior_latest is not None else None
            )
            relation = (
                "first_observation"
                if previous is None
                else "recurrence"
                if previous == fingerprint
                else "structural_change"
            )
            experience_id = _digest({
                "binaural_structural_fingerprint": fingerprint,
            })
            provisional = W1BinauralAuditoryL5Experience(
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                assembly_id=settlement.assembly_id,
                relation=relation,
                source_time_start=settlement.source_time_start,
                source_time_end=settlement.source_time_end,
                ears=ears,
                upstream_causal_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                authority_receipt_sha256="0" * 64,
            )
            experience = W1BinauralAuditoryL5Experience(
                experience_id=provisional.experience_id,
                structural_fingerprint=provisional.structural_fingerprint,
                assembly_id=provisional.assembly_id,
                relation=provisional.relation,
                source_time_start=provisional.source_time_start,
                source_time_end=provisional.source_time_end,
                ears=provisional.ears,
                upstream_causal_settlement_receipt_sha256=(
                    provisional.upstream_causal_settlement_receipt_sha256
                ),
                authority_receipt_sha256=_digest(
                    provisional.authority_payload()
                ),
            )
            experience.verify()
            self._prepared = experience
            return experience

    def commit_prepared(
        self,
        experience: W1BinauralAuditoryL5Experience,
    ) -> _CommitUndo:
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared != experience:
                raise ValueError("W1 binaural L5 has no matching preparation")
            sequence = self._atomic_sequence
            prior_latest = sequence.latest if sequence is not None else self._latest
            transitions = (
                sequence.transitions if sequence is not None else self._transitions
            )
            settled = sequence.settled if sequence is not None else self._settled
            generation = (
                sequence.generation if sequence is not None else self._generation
            )
            undo = _CommitUndo(
                authority_receipt_sha256=experience.authority_receipt_sha256,
                prior_latest=prior_latest,
                prior_transitions=tuple(transitions.items()),
                prior_settled=settled,
                prior_generation=generation,
                atomic_sequence_token=(
                    sequence.token if sequence is not None else None
                ),
            )
            if prior_latest is not None:
                key = (
                    prior_latest.structural_fingerprint,
                    experience.structural_fingerprint,
                )
                transitions[key] = transitions.get(key, 0) + 1
                transitions.move_to_end(key)
                while len(transitions) > self._max_transitions:
                    transitions.popitem(last=False)
            if sequence is not None:
                sequence.latest = experience
                sequence.settled += 1
                sequence.generation += 1
            else:
                self._latest = experience
                self._settled += 1
                self._generation += 1
            self._prepared = None
            return undo

    def rollback_committed(self, undo: _CommitUndo) -> None:
        with self._lock:
            self._require_sequence_owner_locked()
            sequence = self._atomic_sequence
            if undo.atomic_sequence_token is None:
                latest = self._latest
                settled = self._settled
                generation = self._generation
            elif (
                sequence is not None
                and sequence.token == undo.atomic_sequence_token
            ):
                latest = sequence.latest
                settled = sequence.settled
                generation = sequence.generation
            else:
                raise ValueError("W1 binaural L5 rollback sequence changed")
            if (
                latest is None
                or latest.authority_receipt_sha256
                != undo.authority_receipt_sha256
                or settled != undo.prior_settled + 1
                or generation != undo.prior_generation + 1
            ):
                raise ValueError("W1 binaural L5 rollback authority changed")
            if sequence is not None:
                sequence.latest = undo.prior_latest
                sequence.transitions = OrderedDict(undo.prior_transitions)
                sequence.settled = undo.prior_settled
                sequence.generation = undo.prior_generation
            else:
                self._latest = undo.prior_latest
                self._transitions = OrderedDict(undo.prior_transitions)
                self._settled = undo.prior_settled
                self._generation = undo.prior_generation

    def discard_prepared(
        self,
        experience: W1BinauralAuditoryL5Experience,
    ) -> None:
        with self._lock:
            self._require_sequence_owner_locked()
            if self._prepared != experience:
                raise ValueError("W1 binaural L5 has no matching preparation")
            self._prepared = None

    @property
    def latest(self) -> W1BinauralAuditoryL5Experience | None:
        with self._lock:
            return self._latest

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            if (
                self._prepared is not None
                or self._atomic_sequence is not None
            ):
                raise RuntimeError(
                    "W1 binaural L5 snapshot requires settled state"
                )
            payload = {
                "generation": self._generation,
                "latest": (
                    self._latest.persistence_record()
                    if self._latest is not None else None
                ),
                "schema": W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA,
                "settled": self._settled,
                "transition_capacity": self._max_transitions,
                "transitions": [
                    {
                        "count": count,
                        "from_structural_fingerprint": key[0],
                        "to_structural_fingerprint": key[1],
                    }
                    for key, count in self._transitions.items()
                ],
            }
            result = _canonical({
                "payload": payload,
                "state_receipt_sha256": _digest(payload),
            })
            if len(result) > MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES:
                raise RuntimeError(
                    "W1 binaural L5 state exceeds its boundary"
                )
            return result

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES
        ):
            raise ValueError("W1 binaural L5 state boundary changed")
        try:
            record = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("W1 binaural L5 state is unreadable") from error
        if (
            not isinstance(record, dict)
            or set(record) != {"payload", "state_receipt_sha256"}
            or not isinstance(record.get("payload"), dict)
            or record["payload"].get("schema")
            != W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA
            or record.get("state_receipt_sha256")
            != _digest(record["payload"])
        ):
            raise ValueError("W1 binaural L5 state authority changed")
        payload = record["payload"]
        if (
            payload.get("transition_capacity") != self._max_transitions
            or isinstance(payload.get("settled"), bool)
            or not isinstance(payload.get("settled"), int)
            or payload["settled"] < 0
            or isinstance(payload.get("generation"), bool)
            or not isinstance(payload.get("generation"), int)
            or payload["generation"] != payload["settled"]
            or not isinstance(payload.get("transitions"), list)
            or len(payload["transitions"]) > self._max_transitions
        ):
            raise ValueError("W1 binaural L5 state extent changed")
        latest_record = payload.get("latest")
        latest = (
            _experience_from_record(latest_record)
            if latest_record is not None else None
        )
        if (payload["settled"] == 0) != (latest is None):
            raise ValueError("W1 binaural L5 latest extent changed")
        transitions = OrderedDict()
        for item in payload["transitions"]:
            if (
                not isinstance(item, dict)
                or set(item) != {
                    "count",
                    "from_structural_fingerprint",
                    "to_structural_fingerprint",
                }
                or isinstance(item.get("count"), bool)
                or not isinstance(item.get("count"), int)
                or item["count"] <= 0
            ):
                raise ValueError(
                    "W1 binaural L5 transition state changed"
                )
            key = (
                item.get("from_structural_fingerprint"),
                item.get("to_structural_fingerprint"),
            )
            for fingerprint in key:
                sha256_digest(
                    fingerprint,
                    "W1 binaural L5 transition fingerprint",
                )
            if key in transitions:
                raise ValueError(
                    "W1 binaural L5 transition state repeated"
                )
            transitions[key] = item["count"]
        with self._lock:
            if (
                self._prepared is not None
                or self._atomic_sequence is not None
            ):
                raise RuntimeError(
                    "W1 binaural L5 restore requires settled state"
                )
            self._latest = latest
            self._transitions = transitions
            self._settled = payload["settled"]
            self._generation = payload["generation"]

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "has_latest": self._latest is not None,
                "max_authority_bytes": MAX_W1_BINAURAL_AUDITORY_L5_BYTES,
                "prepared": int(self._prepared is not None),
                "atomic_sequence": int(self._atomic_sequence is not None),
                "atomic_sequence_staged_settled": (
                    self._atomic_sequence.settled - self._settled
                    if self._atomic_sequence is not None else 0
                ),
                "settled": self._settled,
                "transition_capacity": self._max_transitions,
                "transition_relations": len(self._transitions),
                "schema": "guala.w1.binaural_auditory_l5.status.v2",
            }


__all__ = (
    "MAX_W1_BINAURAL_AUDITORY_L5_BYTES",
    "MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES",
    "W1_BINAURAL_AUDITORY_L5_AUTHORITY_SCHEMA",
    "W1_BINAURAL_AUDITORY_L5_SCHEMA",
    "W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA",
    "W1BinauralAuditoryL5Channel",
    "W1BinauralAuditoryL5Ear",
    "W1BinauralAuditoryL5Experience",
    "W1BinauralAuditoryL5Owner",
)
