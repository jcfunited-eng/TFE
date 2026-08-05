"""Bounded joint L4 change topology directly from two verified W1 events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorFullFieldEvent,
    MAX_AUDITORY_RECEPTOR_FRAMES,
)


SCHEMA = "guala.audit.auditory_direct_full_field_topology.v1"
COMPONENT_COUNT = 64
MAX_CHANGE_MASKS = MAX_AUDITORY_RECEPTOR_FRAMES - 1
MAX_ENCODED_BYTES = 128 * 1024
EAR_ORDER = ("left", "right")
COMPONENT_ORDER = tuple(
    f"{ear}:erb_{channel:02d}:{kind}"
    for ear in EAR_ORDER
    for channel in range(16)
    for kind in ("pressure", "phase")
)


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


def _change_masks(
    tuple_indexes_by_frame: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    if (
        not tuple_indexes_by_frame
        or len(tuple_indexes_by_frame) > MAX_AUDITORY_RECEPTOR_FRAMES
        or any(len(row) != COMPONENT_COUNT for row in tuple_indexes_by_frame)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for row in tuple_indexes_by_frame
            for value in row
        )
    ):
        raise ValueError("joint L4 tuple-index grid changed")
    masks = []
    for prior, current in zip(
        tuple_indexes_by_frame,
        tuple_indexes_by_frame[1:],
    ):
        mask = sum(
            (1 << component)
            for component, (left, right) in enumerate(
                zip(prior, current, strict=True)
            )
            if left != right
        )
        if mask:
            masks.append(mask)
    if len(masks) > MAX_CHANGE_MASKS:
        raise ValueError("joint L4 change topology exceeded frame bound")
    return tuple(masks)


@dataclass(frozen=True, slots=True)
class DirectFullFieldTopology:
    frame_count: int
    change_masks: tuple[int, ...]
    component_order: tuple[str, ...]
    left_event_receipt_sha256: str
    right_event_receipt_sha256: str
    full_field_witness_root_sha256: str
    topology_root_sha256: str
    authority_receipt_sha256: str

    def topology_key(self) -> tuple[int, ...]:
        return self.change_masks

    def payload(self) -> dict[str, object]:
        return {
            "change_masks_hex": [
                f"{value:016x}" for value in self.change_masks
            ],
            "component_order": list(self.component_order),
            "frame_count": self.frame_count,
            "full_field_witness_root_sha256": (
                self.full_field_witness_root_sha256
            ),
            "left_event_receipt_sha256": (
                self.left_event_receipt_sha256
            ),
            "right_event_receipt_sha256": (
                self.right_event_receipt_sha256
            ),
            "schema": SCHEMA,
            "topology_root_sha256": self.topology_root_sha256,
        }

    def encoded(self) -> bytes:
        return _canonical(
            self.payload()
            | {
                "authority_receipt_sha256": (
                    self.authority_receipt_sha256
                )
            }
        )

    def verify(self) -> None:
        if (
            not 0 < self.frame_count <= MAX_AUDITORY_RECEPTOR_FRAMES
            or self.component_order != COMPONENT_ORDER
            or len(self.change_masks) > self.frame_count - 1
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 < value < (1 << COMPONENT_COUNT)
                for value in self.change_masks
            )
        ):
            raise ValueError("direct full-field topology changed")
        topology_payload = {
            "change_masks_hex": [
                f"{value:016x}" for value in self.change_masks
            ],
            "component_order": list(self.component_order),
            "schema": (
                "guala.audit.auditory_joint_l4_change_mask_topology.v1"
            ),
        }
        if (
            self.topology_root_sha256 != _digest(topology_payload)
            or self.authority_receipt_sha256 != _digest(self.payload())
            or len(self.encoded()) > MAX_ENCODED_BYTES
        ):
            raise ValueError("direct full-field topology authority changed")


def topology_from_events(
    *,
    left: AuditoryReceptorFullFieldEvent,
    right: AuditoryReceptorFullFieldEvent,
) -> DirectFullFieldTopology:
    if (
        not isinstance(left, AuditoryReceptorFullFieldEvent)
        or not isinstance(right, AuditoryReceptorFullFieldEvent)
    ):
        raise TypeError("topology requires two typed full-field events")
    left.verify()
    right.verify()
    if left.frame_count != right.frame_count:
        raise ValueError("binaural full-field events lack a common grid")

    events = (left, right)
    reference = left.channels[0].frames
    for event in events:
        for channel in event.channels:
            for expected, actual in zip(
                reference,
                channel.frames,
                strict=True,
            ):
                if (
                    actual.source_index != expected.source_index
                    or actual.source_time != expected.source_time
                    or actual.causal_offset != expected.causal_offset
                ):
                    raise ValueError(
                        "binaural full-field source grid changed"
                    )

    rows = []
    witness_rows = []
    for frame_index in range(left.frame_count):
        indexes = []
        witnesses = []
        for event in events:
            for channel in event.channels:
                frame = channel.frames[frame_index]
                for kind, tuple_index, values in (
                    (
                        "pressure",
                        frame.pressure_field_tuple_index,
                        channel.pressure_fields,
                    ),
                    (
                        "phase",
                        frame.phase_field_tuple_index,
                        channel.phase_fields,
                    ),
                ):
                    field_tuple = values[tuple_index]
                    if (
                        tuple(name for name, _value in field_tuple.fields)
                        != DSF_FIELD_ORDER
                        or field_tuple.tuple_index != tuple_index
                    ):
                        raise ValueError(
                            f"{kind} full-field tuple topology changed"
                        )
                    indexes.append(tuple_index)
                    witnesses.append(
                        field_tuple.authority_receipt_sha256
                    )
        rows.append(tuple(indexes))
        witness_rows.append(tuple(witnesses))
    rows_tuple = tuple(rows)
    if any(len(value) != COMPONENT_COUNT for value in rows_tuple):
        raise ValueError("joint full-field component count changed")
    masks = _change_masks(rows_tuple)
    topology_payload = {
        "change_masks_hex": [f"{value:016x}" for value in masks],
        "component_order": list(COMPONENT_ORDER),
        "schema": "guala.audit.auditory_joint_l4_change_mask_topology.v1",
    }
    witness_root = _digest(
        {
            "component_order": list(COMPONENT_ORDER),
            "ordered_frame_tuple_receipts": [
                list(value) for value in witness_rows
            ],
            "schema": "guala.audit.auditory_full_field_witness_grid.v1",
        }
    )
    provisional = DirectFullFieldTopology(
        frame_count=left.frame_count,
        change_masks=masks,
        component_order=COMPONENT_ORDER,
        left_event_receipt_sha256=left.authority_receipt_sha256,
        right_event_receipt_sha256=right.authority_receipt_sha256,
        full_field_witness_root_sha256=witness_root,
        topology_root_sha256=_digest(topology_payload),
        authority_receipt_sha256="0" * 64,
    )
    result = DirectFullFieldTopology(
        frame_count=provisional.frame_count,
        change_masks=provisional.change_masks,
        component_order=provisional.component_order,
        left_event_receipt_sha256=(
            provisional.left_event_receipt_sha256
        ),
        right_event_receipt_sha256=(
            provisional.right_event_receipt_sha256
        ),
        full_field_witness_root_sha256=(
            provisional.full_field_witness_root_sha256
        ),
        topology_root_sha256=provisional.topology_root_sha256,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify()
    return result


__all__ = [
    "COMPONENT_COUNT",
    "COMPONENT_ORDER",
    "DirectFullFieldTopology",
    "topology_from_events",
]
