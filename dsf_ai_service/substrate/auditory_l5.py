"""Deterministic auditory L5 ownership over the complete native field.

Auditory L5 receives the verified pre-L5 ``BuiltSixSenseFullField`` before
its source evidence is compacted.  It preserves, per physical frequency
port, every calibrated pressure sample, carrier phase, causal offset, native
topology coordinate, and explicit L4 DSF tuple.  This is the domain boundary
at which physically different sounds may remain different even when the
frozen L0--L4 kernel correctly assigns them the same temporal basin.

This owner does not yet name a word or a source.  It establishes the exact,
bounded object on which reciprocal tutoring can operate.  Capture source
labels and chi routing addresses never enter auditory identity.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SenseBoundaryState,
)


AUDITORY_L5_SCHEMA = "guala.auditory_l5.full_field.v2"
AUDITORY_L5_AUTHORITY_PROFILE = b"guala.auditory_l5.authority.profile.v2"


def _fraction(value: str, name: str) -> Fraction:
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{name} is not an exact fraction") from exc
    return result


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory L5 fraction")
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditoryL5Sample:
    source_index: int
    causal_offset: Fraction
    pressure: Fraction
    phase_turns: Fraction


@dataclass(frozen=True, slots=True)
class AuditoryL5FieldTuple:
    tuple_index: int
    fields: tuple[tuple[str, Fraction], ...]
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryL5Port:
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str
    samples: tuple[AuditoryL5Sample, ...]
    l4_field_tuples: tuple[AuditoryL5FieldTuple, ...]
    source_stream_receipt_sha256: str
    kernel_basin_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryL5Experience:
    experience_id: str
    structural_fingerprint: str
    assembly_id: str
    relation: str
    event_boundary: str
    source_time_start: Fraction
    source_time_end: Fraction
    ports: tuple[AuditoryL5Port, ...]
    assembly_receipt_sha256: str
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        if self.event_boundary not in ("ambient", "utterance"):
            raise ReceiptError("auditory L5 event boundary is invalid")
        structural = _digest(AuditoryL5Owner._structural_payload(self.ports))
        if structural != self.structural_fingerprint:
            raise ReceiptError("auditory L5 structural field was altered")
        expected_id = _digest({
            "assembly_id": self.assembly_id,
            "auditory_structural_fingerprint": structural,
        })
        if expected_id != self.experience_id:
            raise ReceiptError("auditory L5 experience identity was altered")
        payload = _authority_payload(
            experience_id=self.experience_id,
            structural_fingerprint=self.structural_fingerprint,
            assembly_id=self.assembly_id,
            event_boundary=self.event_boundary,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            ports=self.ports,
            assembly_receipt_sha256=self.assembly_receipt_sha256,
        )
        mounted = self.receipt_registry.resolve(
            self.authority_receipt_sha256, "auditory L5 authority"
        )
        if mounted != payload or receipt_sha256(payload) != self.authority_receipt_sha256:
            raise ReceiptError("auditory L5 authority receipt was altered")


def _authority_payload(
    *,
    experience_id: str,
    structural_fingerprint: str,
    assembly_id: str,
    event_boundary: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    ports: tuple[AuditoryL5Port, ...],
    assembly_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes({
        "assembly_id": assembly_id,
        "assembly_receipt_sha256": assembly_receipt_sha256,
        "experience_id": experience_id,
        "event_boundary": event_boundary,
        "ports": [
            {
                "kernel_basin_receipt_sha256": port.kernel_basin_receipt_sha256,
                "l4_field_receipt_sha256": [
                    value.authority_receipt_sha256
                    for value in port.l4_field_tuples
                ],
                "source_stream_receipt_sha256": port.source_stream_receipt_sha256,
                "substream_id": port.substream_id,
                "topology_index": port.topology_index,
            }
            for port in ports
        ],
        "schema": "guala.auditory_l5.authority.v2",
        "source_time_end": _fraction_text(source_time_end),
        "source_time_start": _fraction_text(source_time_start),
        "structural_fingerprint": structural_fingerprint,
    })


class AuditoryL5Owner:
    """Serial, bounded owner of complete auditory domain interpretations."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        max_transitions: int = 1_024,
        max_pending_tutor_experiences: int = 4,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError("auditory L5 transition capacity must be positive")
        if max_pending_tutor_experiences <= 0:
            raise ValueError("auditory L5 tutor window capacity must be positive")
        self._log_event = log_event
        self._max_transitions = int(max_transitions)
        self._max_pending_tutor_experiences = int(
            max_pending_tutor_experiences)
        self._lock = threading.RLock()
        self._latest: AuditoryL5Experience | None = None
        self._pending: OrderedDict[str, AuditoryL5Experience] = OrderedDict()
        self._recent_experience_ids: OrderedDict[str, None] = OrderedDict()
        self._transitions: OrderedDict[tuple[str, str], int] = OrderedDict()
        self._settled = 0

    @staticmethod
    def _source_samples(built: BuiltSixSenseFullField, substream) -> tuple[
        AuditoryL5Sample, ...
    ]:
        digest = substream.profile.physical_derivation_receipt_sha256
        raw = json.loads(built.receipt_registry.resolve(
            digest, "auditory L5 source evidence"
        ))
        if (
            raw.get("schema") != "glew.provider.source_evidence_stream.v1"
            or raw.get("lane_id") != PhysicalSense.SOUND.value
            or raw.get("port_id") != substream.profile.substream_id
        ):
            raise ReceiptError("auditory L5 source evidence belongs to another port")
        samples = raw.get("samples")
        if not isinstance(samples, list) or not samples:
            raise ReceiptError("auditory L5 source evidence is empty")
        first_time = _fraction(samples[0]["timestamp"], "auditory timestamp")
        interpreted = []
        for expected_index, value in enumerate(samples):
            source_index = value.get("source_index")
            if source_index != expected_index:
                raise ReceiptError("auditory L5 source indices are not contiguous")
            timestamp = _fraction(value["timestamp"], "auditory timestamp")
            pressure = _fraction(value["signal"], "auditory pressure")
            phase = _fraction(value["phase_turns"], "auditory phase")
            interpreted.append(AuditoryL5Sample(
                source_index=source_index,
                causal_offset=timestamp - first_time,
                pressure=pressure,
                phase_turns=phase,
            ))
        return tuple(interpreted)

    @classmethod
    def _port(cls, built: BuiltSixSenseFullField, substream) -> AuditoryL5Port:
        return AuditoryL5Port(
            sensor_id=substream.profile.sensor_id,
            substream_id=substream.profile.substream_id,
            topology_index=substream.profile.topology_index,
            coordinates=tuple(
                (coordinate.axis_id, coordinate.coordinate_id)
                for coordinate in substream.profile.coordinates
            ),
            physical_quantity=substream.profile.physical_quantity,
            physical_unit=substream.profile.physical_unit,
            samples=cls._source_samples(built, substream),
            l4_field_tuples=tuple(
                AuditoryL5FieldTuple(
                    tuple_index=value.tuple_index,
                    fields=tuple(
                        (name, getattr(value, name))
                        for name in DSF_FIELD_ORDER
                    ),
                    authority_receipt_sha256=value.authority_receipt_sha256,
                )
                for value in substream.kernel_basin.exact_dsf_field_tuples
            ),
            source_stream_receipt_sha256=(
                substream.profile.physical_derivation_receipt_sha256
            ),
            kernel_basin_receipt_sha256=(
                substream.kernel_basin.authority_receipt_sha256
            ),
        )

    @staticmethod
    def _structural_payload(ports: tuple[AuditoryL5Port, ...]) -> dict:
        return {
            "schema": AUDITORY_L5_SCHEMA,
            "ports": [
                {
                    "coordinates": [list(value) for value in port.coordinates],
                    "l4_field_tuples": [
                        {
                            "fields": [
                                [name, _fraction_text(value)]
                                for name, value in field_tuple.fields
                            ],
                            "tuple_index": field_tuple.tuple_index,
                        }
                        for field_tuple in port.l4_field_tuples
                    ],
                    "physical_quantity": port.physical_quantity,
                    "physical_unit": port.physical_unit,
                    "samples": [
                        {
                            "causal_offset": _fraction_text(sample.causal_offset),
                            "phase_turns": _fraction_text(sample.phase_turns),
                            "pressure": _fraction_text(sample.pressure),
                            "source_index": sample.source_index,
                        }
                        for sample in port.samples
                    ],
                    "sensor_id": port.sensor_id,
                    "substream_id": port.substream_id,
                    "topology_index": port.topology_index,
                }
                for port in ports
            ],
        }

    def settle(
        self,
        built: BuiltSixSenseFullField,
        *,
        event_boundary: str = "ambient",
    ) -> AuditoryL5Experience | None:
        if event_boundary not in ("ambient", "utterance"):
            raise ValueError("auditory event boundary must be ambient or utterance")
        built.boundary.verify(built.receipt_registry)
        sound = next(
            boundary
            for boundary in built.boundary.boundaries
            if boundary.sense is PhysicalSense.SOUND
        )
        if sound.state is not SenseBoundaryState.OBSERVED:
            return None
        ports = tuple(self._port(built, value) for value in sound.substreams)
        if tuple(port.topology_index for port in ports) != tuple(range(len(ports))):
            raise ReceiptError("auditory L5 topology is incomplete or reordered")
        fingerprint = _digest(self._structural_payload(ports))
        with self._lock:
            previous = (
                self._latest.structural_fingerprint
                if self._latest is not None else None
            )
            relation = (
                "first_observation"
                if previous is None
                else "recurrence"
                if previous == fingerprint
                else "structural_change"
            )
            experience_id = _digest({
                "assembly_id": built.boundary.assembly_id,
                "auditory_structural_fingerprint": fingerprint,
            })
            authority_payload = _authority_payload(
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                assembly_id=built.boundary.assembly_id,
                event_boundary=event_boundary,
                source_time_start=sound.source_time_start,
                source_time_end=sound.source_time_end,
                ports=ports,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
            )
            receipt_registry = ReceiptRegistry.from_payloads(
                profile_payload=AUDITORY_L5_AUTHORITY_PROFILE,
                receipt_payloads=(authority_payload,),
            )
            experience = AuditoryL5Experience(
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                assembly_id=built.boundary.assembly_id,
                relation=relation,
                event_boundary=event_boundary,
                source_time_start=sound.source_time_start,
                source_time_end=sound.source_time_end,
                ports=ports,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(authority_payload),
                receipt_registry=receipt_registry,
            )
            experience.verify()
            if previous is not None:
                key = (previous, fingerprint)
                self._transitions[key] = self._transitions.get(key, 0) + 1
                self._transitions.move_to_end(key)
                while len(self._transitions) > self._max_transitions:
                    self._transitions.popitem(last=False)
            self._latest = experience
            self._recent_experience_ids[experience.experience_id] = None
            self._recent_experience_ids.move_to_end(experience.experience_id)
            while (
                len(self._recent_experience_ids)
                > self._max_pending_tutor_experiences
            ):
                expired_id, _ = self._recent_experience_ids.popitem(last=False)
                self._pending.pop(expired_id, None)
            if event_boundary == "utterance":
                self._pending[experience.experience_id] = experience
                self._pending.move_to_end(experience.experience_id)
            self._settled += 1
            self._log_event(
                "auditory_l5_experience_settled",
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                relation=relation,
                port_count=len(ports),
                event_boundary=event_boundary,
            )
            return experience

    @property
    def latest(self) -> AuditoryL5Experience | None:
        with self._lock:
            return self._latest

    def pending_experience(
        self, experience_id: str
    ) -> AuditoryL5Experience | None:
        with self._lock:
            return self._pending.get(experience_id)

    def status(self) -> dict:
        with self._lock:
            return {
                "settled": self._settled,
                "has_latest": self._latest is not None,
                "pending_tutor_experiences": len(self._pending),
                "pending_tutor_capacity": self._max_pending_tutor_experiences,
                "transition_relations": len(self._transitions),
                "transition_capacity": self._max_transitions,
            }


__all__ = (
    "AUDITORY_L5_SCHEMA",
    "AuditoryL5Experience",
    "AuditoryL5FieldTuple",
    "AuditoryL5Owner",
    "AuditoryL5Port",
    "AuditoryL5Sample",
)
