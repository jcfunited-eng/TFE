"""Isolated near-original, non-flattening UF auditory shadow.

This module is deliberately outside the production import graph.  It tests one
precise architectural proposition from UF-Spec v1.3.0:

* the input is one simultaneous multidimensional field;
* adaptive structure is represented at every causal dyadic scale;
* TVR variance and curvature remain independent;
* every mosaic perspective survives through L4;
* resonance is a field of explicit physical edge facts, never a scalar score;
* hysteresis, breathing, containment, and cross-layer checks regulate the
  field without erasing it.

The shadow neither recognizes words nor receives labels.  Corpus labels enter
only after all pair relations exist, to falsify or support the proposition.
The canonical ``uf_core`` package and the production hearing path are never
imported or modified here.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import wave
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from dsf_ai_service.substrate.canonical_l6 import (
    L6Direction,
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
    REQUIRED_SAMPLE_RATE_HZ,
    AuditoryFullFieldCapture,
    transduce_auditory_full_field,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    _select_corpus,
)


SCHEMA = "guala.audit.near_original_uf_shadow.v1"
FIELD_NAMES = (
    "pressure_envelope",
    "carrier_phase",
    "carrier_phase_advance",
    "carrier_phase_advance_nyquist",
)
FIELD_WIDTH = len(FIELD_NAMES) * COCHLEAR_CHANNEL_COUNT
MAX_FRAMES = 100
MAX_SCALES = 7
MAX_GATES_PER_SCALE = MAX_FRAMES
MAX_PARTITION_TOKENS = 4_096


def _fraction(value: float | int | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("boolean entered the exact field")
    return Fraction.from_float(float(value))


def _sign(value: Fraction) -> int:
    return (value > 0) - (value < 0)


def _mean(values: Sequence[Fraction]) -> Fraction:
    if not values:
        raise ValueError("mean requires a non-empty exact field")
    return sum(values, Fraction(0)) / len(values)


def _variance(values: Sequence[Fraction]) -> Fraction:
    centre = _mean(values)
    return _mean(tuple((value - centre) ** 2 for value in values))


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _json_value(value: object) -> object:
    if isinstance(value, Fraction):
        return ["fraction", _fraction_text(value)]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(
        _json_value(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _root(schema: str, values: Iterable[str]) -> str:
    return _digest({
        "schema": schema,
        "sha256s": sorted(set(values)),
    })


def _dyadic_scales(frame_count: int) -> tuple[int, ...]:
    scales = []
    value = 1
    while value < frame_count and len(scales) < MAX_SCALES:
        scales.append(value)
        value *= 2
    return tuple(scales or (1,))


def _group_normalize(raw: Sequence[Fraction]) -> tuple[Fraction, ...]:
    if len(raw) != FIELD_WIDTH:
        raise ValueError("joint field width changed")
    normalized = []
    for field_index in range(len(FIELD_NAMES)):
        start = field_index * COCHLEAR_CHANNEL_COUNT
        group = tuple(raw[start:start + COCHLEAR_CHANNEL_COUNT])
        magnitude = sum((abs(value) for value in group), Fraction(0))
        normalized.extend(
            (Fraction(0) for _value in group)
            if magnitude == 0
            else (value / magnitude for value in group)
        )
    return tuple(normalized)


def _physical_edges() -> tuple[tuple[int, int], ...]:
    edges = set()
    for field_index in range(len(FIELD_NAMES)):
        offset = field_index * COCHLEAR_CHANNEL_COUNT
        for channel in range(COCHLEAR_CHANNEL_COUNT - 1):
            edges.add((offset + channel, offset + channel + 1))
    for channel in range(COCHLEAR_CHANNEL_COUNT):
        indices = tuple(
            field_index * COCHLEAR_CHANNEL_COUNT + channel
            for field_index in range(len(FIELD_NAMES))
        )
        for left_index, left in enumerate(indices):
            for right in indices[left_index + 1:]:
                edges.add((left, right))
    return tuple(sorted(edges))


PHYSICAL_EDGES = _physical_edges()


@dataclass(frozen=True, slots=True)
class L0Frame:
    raw: tuple[Fraction, ...]
    normalized: tuple[Fraction, ...]
    delta: tuple[Fraction, ...]
    variance: tuple[Fraction, ...]
    curvature: tuple[Fraction, ...]
    relevance: tuple[Fraction, ...]
    negative_groups: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class L1Gate:
    scale: int
    start: int
    end: int
    direction: tuple[int, ...]
    duration: int
    volume: tuple[Fraction, ...]
    relevance: tuple[Fraction, ...]
    variance: tuple[Fraction, ...]
    curvature: tuple[Fraction, ...]
    breathing: tuple[int, ...]
    spectral_orders: tuple[tuple[int, ...], ...]
    projection_receipts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class L2Interpretation:
    gate: L1Gate
    volume_contrast: tuple[Fraction, ...]
    relevance_contrast: tuple[Fraction, ...]
    variance_contrast: tuple[Fraction, ...]
    curvature_contrast: tuple[Fraction, ...]
    regimes: tuple[str, ...]
    uncertainty_facts: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class L3Resonance:
    interpretation: L2Interpretation
    edge_facts: tuple[tuple[int, int, int, int, int], ...]
    coherent_clusters: tuple[tuple[int, ...], ...]
    temporal_anchors: tuple[int, ...]
    hysteresis_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class L4Field:
    scale: int
    start: int
    end: int
    D_k: tuple[int, ...]
    M_k: tuple[Fraction, ...]
    R_rev_k: tuple[int, ...]
    U_star_k: tuple[int, ...]
    C_k: tuple[tuple[int, int, int, int, int], ...]
    clusters: tuple[tuple[int, ...], ...]
    P_k: tuple[int, ...]
    B_k: tuple[int, ...]
    projection_receipts: tuple[str, ...]
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class ShadowExperience:
    item_id: str
    frame_count: int
    scales: tuple[int, ...]
    l4_by_scale: tuple[tuple[L4Field, ...], ...]
    partition_tokens: tuple[tuple[str, frozenset[str]], ...]
    authority_receipt_sha256: str

    def verify(self) -> None:
        if (
            not 1 <= self.frame_count <= MAX_FRAMES
            or self.scales != _dyadic_scales(self.frame_count)
            or len(self.l4_by_scale) != len(self.scales)
            or tuple(value[0].scale for value in self.l4_by_scale if value)
            != self.scales
        ):
            raise ValueError("shadow experience topology changed")
        for partition_id, tokens in self.partition_tokens:
            if not partition_id or not tokens or len(tokens) > MAX_PARTITION_TOKENS:
                raise ValueError("shadow partition containment changed")
        expected = _experience_receipt(
            item_id=self.item_id,
            frame_count=self.frame_count,
            scales=self.scales,
            l4_by_scale=self.l4_by_scale,
            partition_tokens=self.partition_tokens,
        )
        if expected != self.authority_receipt_sha256:
            raise ValueError("shadow experience receipt changed")


def _capture_matrix(
    capture: AuditoryFullFieldCapture,
) -> tuple[tuple[Fraction, ...], ...]:
    fields = (
        "pressure_envelope_full_scale",
        "carrier_phase_turns",
        "carrier_phase_advance_turns",
        "carrier_phase_advance_nyquist_fraction",
    )
    rows = []
    for frame_index in range(capture.frame_count):
        row = []
        for field_name in fields:
            row.extend(
                _fraction(getattr(channel, field_name)[frame_index])
                for channel in capture.channels
            )
        rows.append(tuple(row))
    return tuple(rows)


def _build_l0(
    capture: AuditoryFullFieldCapture,
) -> tuple[L0Frame, ...]:
    raw_rows = _capture_matrix(capture)
    normalized_rows = tuple(_group_normalize(row) for row in raw_rows)
    output = []
    zero = tuple(Fraction(0) for _index in range(FIELD_WIDTH))
    for index, (raw, normalized) in enumerate(zip(raw_rows, normalized_rows)):
        previous = normalized_rows[index - 1] if index else normalized
        previous_delta = (
            tuple(
                previous[position] - normalized_rows[index - 2][position]
                for position in range(FIELD_WIDTH)
            )
            if index >= 2
            else zero
        )
        delta = tuple(
            normalized[position] - previous[position]
            for position in range(FIELD_WIDTH)
        )
        curvature = tuple(
            delta[position] - previous_delta[position]
            for position in range(FIELD_WIDTH)
        )
        causal_start = max(0, index + 1 - _dyadic_scales(len(raw_rows))[-1])
        variance = tuple(
            _variance(tuple(
                normalized_rows[row_index][position]
                for row_index in range(causal_start, index + 1)
            ))
            for position in range(FIELD_WIDTH)
        )
        pressure = normalized[:COCHLEAR_CHANNEL_COUNT]
        relevance = tuple(
            pressure[position % COCHLEAR_CHANNEL_COUNT] ** 2
            for position in range(FIELD_WIDTH)
        )
        negative_groups = tuple(
            all(
                raw[group_index * COCHLEAR_CHANNEL_COUNT + channel] == 0
                for channel in range(COCHLEAR_CHANNEL_COUNT)
            )
            for group_index in range(len(FIELD_NAMES))
        )
        output.append(L0Frame(
            raw=raw,
            normalized=normalized,
            delta=delta,
            variance=variance,
            curvature=curvature,
            relevance=relevance,
            negative_groups=negative_groups,
        ))
    return tuple(output)


def _spectral_order(
    values: Sequence[Fraction],
) -> tuple[tuple[int, ...], ...]:
    result = []
    for field_index in range(len(FIELD_NAMES)):
        offset = field_index * COCHLEAR_CHANNEL_COUNT
        group = values[offset:offset + COCHLEAR_CHANNEL_COUNT]
        result.append(tuple(
            _sign(group[right] - group[left])
            for left in range(COCHLEAR_CHANNEL_COUNT)
            for right in range(left + 1, COCHLEAR_CHANNEL_COUNT)
        ))
    return tuple(result)


def _gate_signature(
    frames: Sequence[L0Frame],
    index: int,
    scale: int,
) -> tuple[object, ...]:
    start = max(0, index - scale)
    direction = tuple(
        _sign(
            frames[index].normalized[position]
            - frames[start].normalized[position]
        )
        for position in range(FIELD_WIDTH)
    )
    return (
        direction,
        frames[index].negative_groups,
        _spectral_order(frames[index].normalized),
    )


def _build_l1(
    frames: Sequence[L0Frame],
    scale: int,
) -> tuple[L1Gate, ...]:
    signatures = tuple(
        _gate_signature(frames, index, scale)
        for index in range(len(frames))
    )
    bounds = [0]
    for index in range(1, len(signatures)):
        if signatures[index] != signatures[index - 1]:
            bounds.append(index)
    bounds.append(len(frames))
    gates = []
    for start, stop in zip(bounds, bounds[1:]):
        end = stop - 1
        direction = signatures[end][0]
        volume = tuple(
            sum(
                (abs(frames[index].delta[position])
                 for index in range(start, stop)),
                Fraction(0),
            )
            for position in range(FIELD_WIDTH)
        )
        relevance = tuple(
            sum(
                (frames[index].relevance[position]
                 for index in range(start, stop)),
                Fraction(0),
            )
            for position in range(FIELD_WIDTH)
        )
        variance = tuple(
            _mean(tuple(
                frames[index].variance[position]
                for index in range(start, stop)
            ))
            for position in range(FIELD_WIDTH)
        )
        curvature = tuple(
            sum(
                (abs(frames[index].curvature[position])
                 for index in range(start, stop)),
                Fraction(0),
            )
            for position in range(FIELD_WIDTH)
        )
        breathing = tuple(
            _sign(
                frames[end].variance[position]
                - frames[start].variance[position]
            )
            for position in range(FIELD_WIDTH)
        )
        orders = _spectral_order(frames[end].normalized)
        projection_payloads = (
            ("direction", direction),
            ("spectral_orders", orders),
            ("breathing", breathing),
            ("duration", end - start + 1),
            ("volume", volume),
            ("relevance", relevance),
            ("variance", variance),
            ("curvature", curvature),
        )
        gates.append(L1Gate(
            scale=scale,
            start=start,
            end=end,
            direction=direction,
            duration=end - start + 1,
            volume=volume,
            relevance=relevance,
            variance=variance,
            curvature=curvature,
            breathing=breathing,
            spectral_orders=orders,
            projection_receipts=tuple(
                _digest({
                    "projection": name,
                    "scale": scale,
                    "value": value,
                })
                for name, value in projection_payloads
            ),
        ))
    if not gates or len(gates) > MAX_GATES_PER_SCALE:
        raise ValueError("adaptive gate containment changed")
    return tuple(gates)


def _difference(
    current: Sequence[Fraction],
    previous: Sequence[Fraction],
) -> tuple[Fraction, ...]:
    return tuple(
        current[index] - previous[index]
        for index in range(FIELD_WIDTH)
    )


def _build_l2(
    gates: Sequence[L1Gate],
) -> tuple[L2Interpretation, ...]:
    output = []
    for index, gate in enumerate(gates):
        previous = gates[index - 1] if index else gate
        variance_contrast = _difference(gate.variance, previous.variance)
        curvature_contrast = _difference(gate.curvature, previous.curvature)
        regimes = tuple(
            "QUIESCENT"
            if gate.direction[position] == 0 and gate.breathing[position] == 0
            else "EXPANDING"
            if gate.breathing[position] > 0
            else "CONTRACTING"
            if gate.breathing[position] < 0
            else "TRANSITIONAL"
            for position in range(FIELD_WIDTH)
        )
        uncertainty = tuple(
            gate.direction[position] == 0
            and curvature_contrast[position] != 0
            for position in range(FIELD_WIDTH)
        )
        output.append(L2Interpretation(
            gate=gate,
            volume_contrast=_difference(gate.volume, previous.volume),
            relevance_contrast=_difference(
                gate.relevance, previous.relevance
            ),
            variance_contrast=variance_contrast,
            curvature_contrast=curvature_contrast,
            regimes=regimes,
            uncertainty_facts=uncertainty,
        ))
    return tuple(output)


def _clusters(
    edge_facts: Sequence[tuple[int, int, int, int, int]],
) -> tuple[tuple[int, ...], ...]:
    graph: dict[int, set[int]] = defaultdict(set)
    for left, right, direction_relation, _curvature, _breathing in edge_facts:
        if direction_relation != 1:
            continue
        graph[left].add(right)
        graph[right].add(left)
    seen = set()
    result = []
    for node in sorted(graph):
        if node in seen:
            continue
        stack = [node]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(graph[current] - component)
        seen.update(component)
        result.append(tuple(sorted(component)))
    return tuple(result)


def _build_l3(
    interpretations: Sequence[L2Interpretation],
) -> tuple[L3Resonance, ...]:
    output = []
    prior_edges: tuple[tuple[int, int, int, int, int], ...] | None = None
    prior_direction = tuple(0 for _position in range(FIELD_WIDTH))
    for interpretation in interpretations:
        gate = interpretation.gate
        current_edges = tuple(
            (
                left,
                right,
                1
                if gate.direction[left] == gate.direction[right] != 0
                else -1
                if gate.direction[left] == -gate.direction[right] != 0
                else 0,
                _sign(
                    interpretation.curvature_contrast[left]
                    * interpretation.curvature_contrast[right]
                ),
                _sign(gate.breathing[left] * gate.breathing[right]),
            )
            for left, right in PHYSICAL_EDGES
        )
        all_quiescent = all(value == 0 for value in gate.direction)
        edge_facts = (
            prior_edges
            if all_quiescent and prior_edges is not None
            else current_edges
        )
        anchors = tuple(
            position
            for position, (previous, current) in enumerate(
                zip(prior_direction, gate.direction)
            )
            if previous * current < 0
        )
        hysteresis_receipt = _digest({
            "current_edge_facts": current_edges,
            "effective_edge_facts": edge_facts,
            "quiescent_carry": all_quiescent and prior_edges is not None,
            "scale": gate.scale,
        })
        output.append(L3Resonance(
            interpretation=interpretation,
            edge_facts=edge_facts,
            coherent_clusters=_clusters(edge_facts),
            temporal_anchors=anchors,
            hysteresis_receipt_sha256=hysteresis_receipt,
        ))
        prior_edges = edge_facts
        prior_direction = gate.direction
    return tuple(output)


def _build_l4(
    resonances: Sequence[L3Resonance],
) -> tuple[L4Field, ...]:
    output = []
    prior_d = tuple(0 for _position in range(FIELD_WIDTH))
    prior_volume = tuple(Fraction(0) for _position in range(FIELD_WIDTH))
    for resonance in resonances:
        interpretation = resonance.interpretation
        gate = interpretation.gate
        momentum = _difference(gate.volume, prior_volume)
        reversal = tuple(
            int(previous * current < 0)
            for previous, current in zip(prior_d, gate.direction)
        )
        pressure = tuple(
            abs(current - previous)
            for previous, current in zip(prior_d, gate.direction)
        )
        uncertainty = tuple(
            int(value) for value in interpretation.uncertainty_facts
        )
        payload = {
            "B_k": gate.breathing,
            "C_k": resonance.edge_facts,
            "D_k": gate.direction,
            "M_k": momentum,
            "P_k": pressure,
            "R_rev_k": reversal,
            "U_star_k": uncertainty,
            "clusters": resonance.coherent_clusters,
            "end": gate.end,
            "projection_receipts": gate.projection_receipts,
            "scale": gate.scale,
            "start": gate.start,
        }
        output.append(L4Field(
            scale=gate.scale,
            start=gate.start,
            end=gate.end,
            D_k=gate.direction,
            M_k=momentum,
            R_rev_k=reversal,
            U_star_k=uncertainty,
            C_k=resonance.edge_facts,
            clusters=resonance.coherent_clusters,
            P_k=pressure,
            B_k=gate.breathing,
            projection_receipts=gate.projection_receipts,
            authority_receipt_sha256=_digest(payload),
        ))
        prior_d = gate.direction
        prior_volume = gate.volume
    return tuple(output)


def _token_partitions(
    l4_by_scale: Sequence[Sequence[L4Field]],
) -> tuple[tuple[str, frozenset[str]], ...]:
    partitions: dict[str, set[str]] = defaultdict(set)
    for scale_fields in l4_by_scale:
        for field in scale_fields:
            scale = field.scale
            for position in range(FIELD_WIDTH):
                partitions[
                    f"scale:{scale}/dimension:{position:02d}"
                ].add(_digest({
                    "B": field.B_k[position],
                    "D": field.D_k[position],
                    "M_direction": _sign(field.M_k[position]),
                    "P": field.P_k[position],
                    "R": field.R_rev_k[position],
                    "U": field.U_star_k[position],
                }))
            for left, right, direction, curvature, breathing in field.C_k:
                partitions[
                    f"scale:{scale}/edge:{left:02d}:{right:02d}"
                ].add(_digest((
                    direction,
                    curvature,
                    breathing,
                )))
            for projection_index, receipt in enumerate(
                field.projection_receipts
            ):
                partitions[
                    f"scale:{scale}/projection:{projection_index}"
                ].add(receipt)
    result = tuple(
        (partition_id, frozenset(tokens))
        for partition_id, tokens in sorted(partitions.items())
    )
    if not result or any(
        not tokens or len(tokens) > MAX_PARTITION_TOKENS
        for _partition_id, tokens in result
    ):
        raise ValueError("shadow token containment changed")
    return result


def _experience_receipt(
    *,
    item_id: str,
    frame_count: int,
    scales: Sequence[int],
    l4_by_scale: Sequence[Sequence[L4Field]],
    partition_tokens: Sequence[tuple[str, frozenset[str]]],
) -> str:
    return _digest({
        "frame_count": frame_count,
        "item_id": item_id,
        "l4_roots": [
            _root(
                "guala.audit.near_original_l4_scale.v1",
                (field.authority_receipt_sha256 for field in values),
            )
            for values in l4_by_scale
        ],
        "partition_roots": [
            [
                partition_id,
                _root(
                    "guala.audit.near_original_partition.v1",
                    tokens,
                ),
            ]
            for partition_id, tokens in partition_tokens
        ],
        "scales": list(scales),
        "schema": SCHEMA,
    })


def build_shadow_experience(
    *,
    item_id: str,
    capture: AuditoryFullFieldCapture,
) -> ShadowExperience:
    frames = _build_l0(capture)
    scales = _dyadic_scales(len(frames))
    l4_by_scale = []
    for scale in scales:
        l1 = _build_l1(frames, scale)
        l2 = _build_l2(l1)
        l3 = _build_l3(l2)
        l4_by_scale.append(_build_l4(l3))
    l4_tuple = tuple(l4_by_scale)
    partitions = _token_partitions(l4_tuple)
    experience = ShadowExperience(
        item_id=item_id,
        frame_count=len(frames),
        scales=scales,
        l4_by_scale=l4_tuple,
        partition_tokens=partitions,
        authority_receipt_sha256=_experience_receipt(
            item_id=item_id,
            frame_count=len(frames),
            scales=scales,
            l4_by_scale=l4_tuple,
            partition_tokens=partitions,
        ),
    )
    experience.verify()
    return experience


def _l6_payload(value: L6Direction) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def relate(
    left: ShadowExperience,
    right: ShadowExperience,
) -> dict[str, object]:
    left.verify()
    right.verify()
    left_partitions = dict(left.partition_tokens)
    right_partitions = dict(right.partition_tokens)
    common_ids = tuple(sorted(
        left_partitions.keys() & right_partitions.keys()
    ))
    family_counts: dict[str, list[bool]] = defaultdict(list)
    partition_records = []
    for partition_id in common_ids:
        left_tokens = left_partitions[partition_id]
        right_tokens = right_partitions[partition_id]
        matching = len(left_tokens & right_tokens)
        left_l6 = canonical_l6_direction(
            dimensions=len(left_tokens),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        right_l6 = canonical_l6_direction(
            dimensions=len(right_tokens),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        locked = left_l6.locked and right_l6.locked
        family = (
            "dimension"
            if "/dimension:" in partition_id
            else "edge"
            if "/edge:" in partition_id
            else "projection"
        )
        family_counts[family].append(locked)
        partition_records.append({
            "family": family,
            "left_l6": _l6_payload(left_l6),
            "locked": locked,
            "partition_id": partition_id,
            "right_l6": _l6_payload(right_l6),
        })
    family_records = []
    family_locks = []
    for family in ("dimension", "edge", "projection"):
        facts = family_counts.get(family, [])
        direction = canonical_l6_direction(
            dimensions=len(facts),
            matching_non_null=sum(facts),
            matching_quiescent=0,
        )
        family_records.append({
            "family": family,
            "l6": _l6_payload(direction),
        })
        family_locks.append(direction.locked)
    overall = canonical_l6_direction(
        dimensions=len(family_locks),
        matching_non_null=sum(family_locks),
        matching_quiescent=0,
    )
    payload = {
        "family_relations": family_records,
        "left_experience_receipt_sha256": (
            left.authority_receipt_sha256
        ),
        "overall_l6": _l6_payload(overall),
        "partition_relation_root_sha256": _digest({
            "partitions": partition_records,
            "schema": "guala.audit.near_original_partition_relations.v1",
        }),
        "relation_locked": overall.locked,
        "right_experience_receipt_sha256": (
            right.authority_receipt_sha256
        ),
        "schema": "guala.audit.near_original_relation.v1",
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def _read_signal(data: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("speech corpus PCM authority changed")
        raw = source.readframes(source.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32_768.0


def run_census(archive_path: Path) -> dict[str, object]:
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech corpus archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        experiences = {}
        for item in items:
            capture = transduce_auditory_full_field(
                _read_signal(archive.read(item.archive_member)),
                sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
            )
            experiences[item.item_id] = build_shadow_experience(
                item_id=item.item_id,
                capture=capture,
            )
    matrix = []
    for left in items:
        row = []
        for right in items:
            row.append(relate(
                experiences[left.item_id],
                experiences[right.item_id],
            ))
        matrix.append(row)
    within_total = within_locked = 0
    cross_total = cross_locked = 0
    held_out_total = held_out_pass = 0
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(
                matrix[left_index][right_index]["relation_locked"]
            )
            if left.oracle_command == right.oracle_command:
                within_total += 1
                within_locked += int(locked)
            else:
                cross_total += 1
                cross_locked += int(locked)
    references = {
        command: tuple(
            index for index, item in enumerate(items)
            if item.oracle_command == command and item.split == "reference"
        )
        for command in COMMANDS
    }
    for query_index, query in enumerate(items):
        if query.split != "held_out":
            continue
        held_out_total += 1
        expected = references[query.oracle_command]
        wrong = tuple(
            index
            for command, indices in references.items()
            if command != query.oracle_command
            for index in indices
        )
        passed = (
            all(matrix[query_index][index]["relation_locked"]
                for index in expected)
            and not any(matrix[query_index][index]["relation_locked"]
                        for index in wrong)
        )
        held_out_pass += int(passed)
    report = {
        "archive_sha256": ARCHIVE_SHA256,
        "cross_command_locked_pairs": cross_locked,
        "cross_command_pair_count": cross_total,
        "experience_authority_root_sha256": _root(
            "guala.audit.near_original_experiences.v1",
            (
                value.authority_receipt_sha256
                for value in experiences.values()
            ),
        ),
        "experience_count": len(experiences),
        "held_out_pass_count": held_out_pass,
        "held_out_total": held_out_total,
        "labels_used_by_relations": False,
        "matrix": matrix,
        "production_modified": False,
        "schema": SCHEMA,
        "source_disjoint_speaker_count": len({
            item.speaker_id for item in items
        }),
        "within_command_locked_pairs": within_locked,
        "within_command_pair_count": within_total,
    }
    return report | {
        "authority_receipt_sha256": _digest(report),
    }


def _summary(report: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in report.items()
        if key != "matrix"
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_census(args.archive)
    if args.output is not None:
        args.output.write_bytes(
            json.dumps(
                report,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
        )
    print(json.dumps(
        _summary(report) if args.summary else report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
