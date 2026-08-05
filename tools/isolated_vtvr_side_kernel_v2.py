"""Faithful non-canonical Vector--Time--Volume--Relation side kernel.

This isolated reconstruction does not import, wrap, modify, or evaluate the
canonical ``uf_core`` kernel.  It tests one proposition only: all simultaneous
data must first become one joint Vector--Time--Volume--Relation (VTVR) field,
and every later layer must retain that complete field.

Raw custody is immutable.  A separately receipted structural view quotients
only a declared common positive gain inside each physical group.  Exact
``Fraction`` arithmetic is used after admission.  There are no thresholds,
scores, learned weights, ML, transcripts, labels, or domain decisions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from typing import Sequence


SCHEMA = "guala.research.vtvr_side_kernel.v2"
MAX_VERTICES = 64
MAX_FRAMES = 2_048


def _exact(value: Fraction | int) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("boolean cannot enter the VTVR field")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    raise TypeError("VTVR admission requires an integer or Fraction")


def _serial(value: object) -> object:
    if isinstance(value, Fraction):
        return ["fraction", f"{value.numerator}/{value.denominator}"]
    if is_dataclass(value):
        return {
            field.name: _serial(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_serial(item) for item in value]
    if isinstance(value, list):
        return [_serial(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _serial(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        _serial(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _edges(width: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (left, right)
        for left in range(width)
        for right in range(left + 1, width)
    )


def _normalize(
    vector: tuple[Fraction, ...],
    groups: tuple[tuple[int, ...], ...],
) -> tuple[Fraction, ...]:
    result = [Fraction(0) for _value in vector]
    for group in groups:
        magnitude = sum(
            (abs(vector[index]) for index in group),
            Fraction(0),
        )
        for index in group:
            result[index] = (
                Fraction(0)
                if magnitude == 0
                else vector[index] / magnitude
            )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class JointFieldInput:
    vertex_ids: tuple[str, ...]
    groups: tuple[tuple[int, ...], ...]
    times: tuple[Fraction, ...]
    vectors: tuple[tuple[Fraction, ...], ...]
    raw_authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        vertex_ids: Sequence[str],
        groups: Sequence[Sequence[int]],
        times: Sequence[Fraction | int],
        vectors: Sequence[Sequence[Fraction | int]],
    ) -> "JointFieldInput":
        vertices = tuple(vertex_ids)
        mounted_groups = tuple(tuple(group) for group in groups)
        mounted_times = tuple(_exact(value) for value in times)
        mounted_vectors = tuple(
            tuple(_exact(value) for value in vector)
            for vector in vectors
        )
        authority = _digest({
            "groups": mounted_groups,
            "schema": "guala.research.vtvr_input.v2",
            "times": mounted_times,
            "vectors": mounted_vectors,
            "vertex_ids": vertices,
        })
        result = cls(
            vertex_ids=vertices,
            groups=mounted_groups,
            times=mounted_times,
            vectors=mounted_vectors,
            raw_authority_receipt_sha256=authority,
        )
        result.verify()
        return result

    def verify(self) -> None:
        width = len(self.vertex_ids)
        covered = tuple(sorted(
            index for group in self.groups for index in group
        ))
        expected = _digest({
            "groups": self.groups,
            "schema": "guala.research.vtvr_input.v2",
            "times": self.times,
            "vectors": self.vectors,
            "vertex_ids": self.vertex_ids,
        })
        if (
            not 2 <= width <= MAX_VERTICES
            or len(set(self.vertex_ids)) != width
            or any(
                not isinstance(value, str)
                or not value
                or value != value.strip()
                for value in self.vertex_ids
            )
            or not 2 <= len(self.times) <= MAX_FRAMES
            or len(self.vectors) != len(self.times)
            or any(len(vector) != width for vector in self.vectors)
            or any(
                current <= prior
                for prior, current in zip(
                    self.times,
                    self.times[1:],
                )
            )
            or not self.groups
            or any(
                not group or len(set(group)) != len(group)
                for group in self.groups
            )
            or covered != tuple(range(width))
            or expected != self.raw_authority_receipt_sha256
        ):
            raise ValueError("joint VTVR input authority changed")


@dataclass(frozen=True, slots=True)
class RelationFact:
    left: int
    right: int
    prior_product: Fraction
    current_product: Fraction
    displacement_product: Fraction
    oriented_area: Fraction


@dataclass(frozen=True, slots=True)
class L0Frame:
    frame_index: int
    time: Fraction
    delta_time: Fraction
    raw_vector: tuple[Fraction, ...]
    vector: tuple[Fraction, ...]
    displacement: tuple[Fraction, ...]
    volume: tuple[Fraction, ...]
    relation: tuple[RelationFact, ...]
    observed_zero_groups: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class L0JointField:
    vertex_ids: tuple[str, ...]
    groups: tuple[tuple[int, ...], ...]
    edges: tuple[tuple[int, int], ...]
    frames: tuple[L0Frame, ...]
    raw_authority_receipt_sha256: str
    structural_authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class L1VTVR:
    """The four dimensions remain separate and jointly authoritative."""

    vector: tuple[tuple[Fraction, ...], ...]
    time: tuple[Fraction, ...]
    volume: tuple[tuple[Fraction, ...], ...]
    accumulated_volume: tuple[Fraction, ...]
    relation: tuple[tuple[RelationFact, ...], ...]
    structural_authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class L2Geometry:
    vtvr: L1VTVR
    velocity: tuple[tuple[Fraction, ...], ...]
    acceleration: tuple[tuple[Fraction, ...], ...]
    relation_change: tuple[tuple[RelationFact, ...], ...]
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class L3ResonanceField:
    geometry: L2Geometry
    vertex_trajectories: tuple[tuple[Fraction, ...], ...]
    edge_trajectories: tuple[tuple[RelationFact, ...], ...]
    quiescent: bool
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class L4JointDSF:
    D_k: tuple[tuple[Fraction, ...], ...]
    M_k: tuple[tuple[Fraction, ...], ...]
    R_rev_k: tuple[tuple[int, ...], ...]
    U_star_k: tuple[tuple[str, ...], ...]
    C_k: tuple[tuple[RelationFact, ...], ...]
    P_k: tuple[tuple[Fraction, ...], ...]
    B_k: tuple[tuple[Fraction, ...], ...]
    source_resonance_authority_receipt_sha256: str
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class SideKernelExperience:
    joint_input: JointFieldInput
    L0: L0JointField
    L1: L1VTVR
    L2: L2Geometry
    L3: L3ResonanceField
    L4: L4JointDSF
    authority_receipt_sha256: str

    def verify(self) -> None:
        self.joint_input.verify()
        width = len(self.joint_input.vertex_ids)
        frame_count = len(self.joint_input.times)
        edge_count = width * (width - 1) // 2
        expected = _digest({
            "L0": self.L0.structural_authority_receipt_sha256,
            "L1": self.L1.structural_authority_receipt_sha256,
            "L2": self.L2.authority_receipt_sha256,
            "L3": self.L3.authority_receipt_sha256,
            "L4": self.L4.authority_receipt_sha256,
            "raw": self.joint_input.raw_authority_receipt_sha256,
            "schema": SCHEMA,
        })
        if (
            len(self.L0.frames) != frame_count
            or len(self.L0.edges) != edge_count
            or len(self.L1.vector) != frame_count
            or len(self.L1.time) != frame_count
            or len(self.L1.volume) != frame_count
            or len(self.L1.relation) != frame_count
            or len(self.L1.accumulated_volume) != width
            or len(self.L3.vertex_trajectories) != width
            or len(self.L3.edge_trajectories) != edge_count
            or any(
                len(getattr(self.L4, name)) != frame_count
                for name in (
                    "D_k",
                    "M_k",
                    "R_rev_k",
                    "U_star_k",
                    "C_k",
                    "P_k",
                    "B_k",
                )
            )
            or expected != self.authority_receipt_sha256
        ):
            raise ValueError("VTVR side-kernel field was flattened")


def _relation(
    prior: tuple[Fraction, ...],
    current: tuple[Fraction, ...],
    displacement: tuple[Fraction, ...],
    edges: tuple[tuple[int, int], ...],
) -> tuple[RelationFact, ...]:
    return tuple(
        RelationFact(
            left=left,
            right=right,
            prior_product=prior[left] * prior[right],
            current_product=current[left] * current[right],
            displacement_product=(
                displacement[left] * displacement[right]
            ),
            oriented_area=(
                prior[left] * current[right]
                - prior[right] * current[left]
            ),
        )
        for left, right in edges
    )


def _relation_delta(
    prior: RelationFact,
    current: RelationFact,
) -> RelationFact:
    if (
        prior.left != current.left
        or prior.right != current.right
    ):
        raise ValueError("VTVR edge topology changed")
    return RelationFact(
        left=current.left,
        right=current.right,
        prior_product=current.prior_product - prior.prior_product,
        current_product=current.current_product - prior.current_product,
        displacement_product=(
            current.displacement_product
            - prior.displacement_product
        ),
        oriented_area=current.oriented_area - prior.oriented_area,
    )


def _build_l0(value: JointFieldInput) -> L0JointField:
    value.verify()
    edge_topology = _edges(len(value.vertex_ids))
    normalized = tuple(
        _normalize(vector, value.groups)
        for vector in value.vectors
    )
    zero = tuple(Fraction(0) for _vertex in value.vertex_ids)
    frames = []
    for index, current in enumerate(normalized):
        prior = current if index == 0 else normalized[index - 1]
        delta_time = (
            Fraction(0)
            if index == 0
            else value.times[index] - value.times[index - 1]
        )
        displacement = (
            zero
            if index == 0
            else tuple(
                current[position] - prior[position]
                for position in range(len(current))
            )
        )
        frames.append(L0Frame(
            frame_index=index,
            time=value.times[index],
            delta_time=delta_time,
            raw_vector=value.vectors[index],
            vector=current,
            displacement=displacement,
            volume=tuple(
                abs(component) * delta_time
                for component in displacement
            ),
            relation=_relation(
                prior,
                current,
                displacement,
                edge_topology,
            ),
            observed_zero_groups=tuple(
                all(
                    value.vectors[index][position] == 0
                    for position in group
                )
                for group in value.groups
            ),
        ))
    structural_payload = {
        "edges": edge_topology,
        "frames": tuple(
            {
                "delta_time": frame.delta_time,
                "displacement": frame.displacement,
                "frame_index": frame.frame_index,
                "observed_zero_groups": frame.observed_zero_groups,
                "relation": frame.relation,
                "time": frame.time,
                "vector": frame.vector,
                "volume": frame.volume,
            }
            for frame in frames
        ),
        "groups": value.groups,
        "schema": "guala.research.vtvr_l0.v2",
        "vertex_ids": value.vertex_ids,
    }
    return L0JointField(
        vertex_ids=value.vertex_ids,
        groups=value.groups,
        edges=edge_topology,
        frames=tuple(frames),
        raw_authority_receipt_sha256=(
            value.raw_authority_receipt_sha256
        ),
        structural_authority_receipt_sha256=_digest(
            structural_payload
        ),
    )


def _build_l1(value: L0JointField) -> L1VTVR:
    vector = tuple(frame.vector for frame in value.frames)
    time = tuple(frame.time for frame in value.frames)
    volume = tuple(frame.volume for frame in value.frames)
    accumulated = tuple(
        sum(
            (frame.volume[index] for frame in value.frames),
            Fraction(0),
        )
        for index in range(len(value.vertex_ids))
    )
    relation = tuple(frame.relation for frame in value.frames)
    payload = {
        "accumulated_volume": accumulated,
        "relation": relation,
        "schema": "guala.research.vtvr_l1.v2",
        "time": time,
        "vector": vector,
        "volume": volume,
    }
    return L1VTVR(
        vector=vector,
        time=time,
        volume=volume,
        accumulated_volume=accumulated,
        relation=relation,
        structural_authority_receipt_sha256=_digest(payload),
    )


def _build_l2(value: L1VTVR) -> L2Geometry:
    width = len(value.vector[0])
    zero = tuple(Fraction(0) for _index in range(width))
    velocity = [zero]
    acceleration = [zero]
    relation_change = [tuple(
        _relation_delta(fact, fact)
        for fact in value.relation[0]
    )]
    for index in range(1, len(value.time)):
        delta_time = value.time[index] - value.time[index - 1]
        current_velocity = tuple(
            (
                value.vector[index][position]
                - value.vector[index - 1][position]
            ) / delta_time
            for position in range(width)
        )
        velocity.append(current_velocity)
        acceleration.append(tuple(
            (
                current_velocity[position]
                - velocity[index - 1][position]
            ) / delta_time
            for position in range(width)
        ))
        relation_change.append(tuple(
            _relation_delta(prior, current)
            for prior, current in zip(
                value.relation[index - 1],
                value.relation[index],
                strict=True,
            )
        ))
    payload = {
        "acceleration": tuple(acceleration),
        "relation_change": tuple(relation_change),
        "schema": "guala.research.vtvr_l2.v2",
        "source": value.structural_authority_receipt_sha256,
        "velocity": tuple(velocity),
    }
    return L2Geometry(
        vtvr=value,
        velocity=tuple(velocity),
        acceleration=tuple(acceleration),
        relation_change=tuple(relation_change),
        authority_receipt_sha256=_digest(payload),
    )


def _build_l3(value: L2Geometry) -> L3ResonanceField:
    width = len(value.vtvr.vector[0])
    vertex_trajectories = tuple(
        tuple(vector[index] for vector in value.vtvr.vector)
        for index in range(width)
    )
    edge_count = len(value.vtvr.relation[0])
    edge_trajectories = tuple(
        tuple(relation[index] for relation in value.vtvr.relation)
        for index in range(edge_count)
    )
    quiescent = all(
        component == 0
        for volume in value.vtvr.volume
        for component in volume
    )
    payload = {
        "edge_trajectories": edge_trajectories,
        "quiescent": quiescent,
        "schema": "guala.research.vtvr_l3.v2",
        "source": value.authority_receipt_sha256,
        "vertex_trajectories": vertex_trajectories,
    }
    return L3ResonanceField(
        geometry=value,
        vertex_trajectories=vertex_trajectories,
        edge_trajectories=edge_trajectories,
        quiescent=quiescent,
        authority_receipt_sha256=_digest(payload),
    )


def _build_l4(value: L3ResonanceField) -> L4JointDSF:
    vtvr = value.geometry.vtvr
    width = len(vtvr.vector[0])
    zero = tuple(Fraction(0) for _index in range(width))
    displacement = tuple(
        zero
        if index == 0
        else tuple(
            vtvr.vector[index][position]
            - vtvr.vector[index - 1][position]
            for position in range(width)
        )
        for index in range(len(vtvr.time))
    )
    reversal = [tuple(0 for _index in range(width))]
    pressure = [zero]
    breathing = [zero]
    uncertainty = [
        tuple("genesis" for _index in range(width))
    ]
    for index in range(1, len(vtvr.time)):
        reversal.append(tuple(
            int(
                displacement[index - 1][position]
                * displacement[index][position]
                < 0
            )
            for position in range(width)
        ))
        pressure.append(tuple(
            abs(value.geometry.acceleration[index][position])
            for position in range(width)
        ))
        breathing.append(tuple(
            vtvr.volume[index][position]
            - vtvr.volume[index - 1][position]
            for position in range(width)
        ))
        uncertainty.append(
            tuple("observed" for _index in range(width))
        )
    payload = {
        "B_k": tuple(breathing),
        "C_k": vtvr.relation,
        "D_k": displacement,
        "M_k": value.geometry.acceleration,
        "P_k": tuple(pressure),
        "R_rev_k": tuple(reversal),
        "U_star_k": tuple(uncertainty),
        "schema": "guala.research.vtvr_l4.v2",
        "source": value.authority_receipt_sha256,
    }
    return L4JointDSF(
        D_k=displacement,
        M_k=value.geometry.acceleration,
        R_rev_k=tuple(reversal),
        U_star_k=tuple(uncertainty),
        C_k=vtvr.relation,
        P_k=tuple(pressure),
        B_k=tuple(breathing),
        source_resonance_authority_receipt_sha256=(
            value.authority_receipt_sha256
        ),
        authority_receipt_sha256=_digest(payload),
    )


def run_side_kernel(value: JointFieldInput) -> SideKernelExperience:
    l0 = _build_l0(value)
    l1 = _build_l1(l0)
    l2 = _build_l2(l1)
    l3 = _build_l3(l2)
    l4 = _build_l4(l3)
    result = SideKernelExperience(
        joint_input=value,
        L0=l0,
        L1=l1,
        L2=l2,
        L3=l3,
        L4=l4,
        authority_receipt_sha256=_digest({
            "L0": l0.structural_authority_receipt_sha256,
            "L1": l1.structural_authority_receipt_sha256,
            "L2": l2.authority_receipt_sha256,
            "L3": l3.authority_receipt_sha256,
            "L4": l4.authority_receipt_sha256,
            "raw": value.raw_authority_receipt_sha256,
            "schema": SCHEMA,
        }),
    )
    result.verify()
    return result


def structural_relation(
    left: SideKernelExperience,
    right: SideKernelExperience,
) -> bool:
    """Walk-up equality of the complete VTVR structural view only."""

    left.verify()
    right.verify()
    return (
        left.L1.structural_authority_receipt_sha256
        == right.L1.structural_authority_receipt_sha256
    )


__all__ = (
    "JointFieldInput",
    "L0JointField",
    "L1VTVR",
    "L2Geometry",
    "L3ResonanceField",
    "L4JointDSF",
    "RelationFact",
    "SideKernelExperience",
    "run_side_kernel",
    "structural_relation",
)
