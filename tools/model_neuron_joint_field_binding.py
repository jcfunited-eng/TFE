"""Isolated D1 model of neuron binding to a near-v1.3 joint DSF field.

This is a falsification model, not production cognition.  It leaves canonical
L0--L4 unchanged and does not invent a Krimelack settlement equation.  It
tests the narrower architectural boundary that can be established now:

* one neuron receives one typed vertex perspective;
* the perspective retains every applicable local DSF value;
* cohesion remains the set of physical edges incident on that vertex;
* the complete joint field remains authority by reference; and
* the perspectives of three neurons reconstruct the complete three-vertex
  relation field without scalarization.

Exact rationals are represented reversibly as balanced-ternary numerator and
denominator words.  That representation is an arithmetic boundary only.  It
is not meaning, memory, neuronal identity, or a Krimelack transition law.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction

from tools.isolated_vtvr_side_kernel_v2 import (
    RelationFact,
    SideKernelExperience,
)


SCHEMA = "guala.research.neuron_joint_field_binding.v1"


def _balanced_trits(value: int) -> tuple[int, ...]:
    """Return the unique least-significant-first balanced-ternary word."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("balanced-ternary admission requires an integer")
    if value == 0:
        return (0,)
    result: list[int] = []
    remaining = value
    while remaining:
        remaining, remainder = divmod(remaining, 3)
        if remainder == 2:
            remainder = -1
            remaining += 1
        result.append(remainder)
    return tuple(result)


def _integer(trits: tuple[int, ...]) -> int:
    if (
        not trits
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value not in (-1, 0, 1)
            for value in trits
        )
        or len(trits) > 1
        and trits[-1] == 0
    ):
        raise ValueError("noncanonical balanced-ternary word")
    return sum(value * 3**index for index, value in enumerate(trits))


@dataclass(frozen=True, slots=True)
class ExactTernaryRational:
    numerator: tuple[int, ...]
    denominator: tuple[int, ...]

    @classmethod
    def encode(cls, value: Fraction) -> "ExactTernaryRational":
        if not isinstance(value, Fraction):
            raise TypeError("joint-field arithmetic must remain exact")
        return cls(
            numerator=_balanced_trits(value.numerator),
            denominator=_balanced_trits(value.denominator),
        )

    def decode(self) -> Fraction:
        denominator = _integer(self.denominator)
        if denominator <= 0:
            raise ValueError("rational denominator must remain positive")
        result = Fraction(_integer(self.numerator), denominator)
        if ExactTernaryRational.encode(result) != self:
            raise ValueError("noncanonical exact rational representation")
        return result

    @property
    def trit_count(self) -> int:
        return len(self.numerator) + len(self.denominator)


@dataclass(frozen=True, slots=True)
class TernaryRelationFact:
    left: int
    right: int
    prior_product: ExactTernaryRational
    current_product: ExactTernaryRational
    displacement_product: ExactTernaryRational
    oriented_area: ExactTernaryRational

    @classmethod
    def encode(cls, value: RelationFact) -> "TernaryRelationFact":
        return cls(
            left=value.left,
            right=value.right,
            prior_product=ExactTernaryRational.encode(value.prior_product),
            current_product=ExactTernaryRational.encode(value.current_product),
            displacement_product=ExactTernaryRational.encode(
                value.displacement_product
            ),
            oriented_area=ExactTernaryRational.encode(value.oriented_area),
        )

    def decode(self) -> RelationFact:
        return RelationFact(
            left=self.left,
            right=self.right,
            prior_product=self.prior_product.decode(),
            current_product=self.current_product.decode(),
            displacement_product=self.displacement_product.decode(),
            oriented_area=self.oriented_area.decode(),
        )

    @property
    def trit_count(self) -> int:
        return sum(
            value.trit_count
            for value in (
                self.prior_product,
                self.current_product,
                self.displacement_product,
                self.oriented_area,
            )
        )


def _serial(value: object) -> object:
    if is_dataclass(value):
        return {
            field.name: _serial(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _serial(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, tuple):
        return [_serial(item) for item in value]
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        _serial(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class NeuronJointFieldPerspective:
    neuron_id: str
    vertex_id: str
    vertex_index: int
    frame_index: int
    complete_field_receipt_sha256: str
    D_k: ExactTernaryRational
    M_k: ExactTernaryRational
    R_rev_k: int
    U_star_k: str
    C_k: tuple[TernaryRelationFact, ...]
    P_k: ExactTernaryRational
    B_k: ExactTernaryRational
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "B_k": self.B_k,
            "C_k": self.C_k,
            "D_k": self.D_k,
            "M_k": self.M_k,
            "P_k": self.P_k,
            "R_rev_k": self.R_rev_k,
            "U_star_k": self.U_star_k,
            "complete_field_receipt_sha256": (
                self.complete_field_receipt_sha256
            ),
            "frame_index": self.frame_index,
            "neuron_id": self.neuron_id,
            "schema": SCHEMA,
            "vertex_id": self.vertex_id,
            "vertex_index": self.vertex_index,
        }

    def verify(self) -> None:
        if (
            not self.neuron_id
            or not self.vertex_id
            or self.vertex_index < 0
            or self.frame_index < 0
            or self.R_rev_k not in (0, 1)
            or self.U_star_k not in ("genesis", "observed")
            or any(
                self.vertex_index not in (edge.left, edge.right)
                for edge in self.C_k
            )
            or len({(edge.left, edge.right) for edge in self.C_k})
            != len(self.C_k)
            or _digest(self.unsigned_record())
            != self.authority_receipt_sha256
        ):
            raise ValueError("neuron joint-field perspective changed")
        for value in (self.D_k, self.M_k, self.P_k, self.B_k):
            value.decode()
        for edge in self.C_k:
            edge.decode()

    @property
    def arithmetic_trit_count(self) -> int:
        return sum(
            value.trit_count
            for value in (self.D_k, self.M_k, self.P_k, self.B_k)
        ) + sum(edge.trit_count for edge in self.C_k)


def bind_neuron_perspective(
    experience: SideKernelExperience,
    *,
    neuron_id: str,
    vertex_index: int,
    frame_index: int,
) -> NeuronJointFieldPerspective:
    """Bind one neuron to one lossless local perspective of a full field."""

    experience.verify()
    if not 0 <= vertex_index < len(experience.joint_input.vertex_ids):
        raise IndexError("vertex index is outside the joint field")
    if not 0 <= frame_index < len(experience.joint_input.times):
        raise IndexError("frame index is outside the joint field")
    incident = tuple(
        TernaryRelationFact.encode(edge)
        for edge in experience.L4.C_k[frame_index]
        if vertex_index in (edge.left, edge.right)
    )
    provisional = NeuronJointFieldPerspective(
        neuron_id=neuron_id,
        vertex_id=experience.joint_input.vertex_ids[vertex_index],
        vertex_index=vertex_index,
        frame_index=frame_index,
        complete_field_receipt_sha256=(
            experience.L4.authority_receipt_sha256
        ),
        D_k=ExactTernaryRational.encode(
            experience.L4.D_k[frame_index][vertex_index]
        ),
        M_k=ExactTernaryRational.encode(
            experience.L4.M_k[frame_index][vertex_index]
        ),
        R_rev_k=experience.L4.R_rev_k[frame_index][vertex_index],
        U_star_k=experience.L4.U_star_k[frame_index][vertex_index],
        C_k=incident,
        P_k=ExactTernaryRational.encode(
            experience.L4.P_k[frame_index][vertex_index]
        ),
        B_k=ExactTernaryRational.encode(
            experience.L4.B_k[frame_index][vertex_index]
        ),
        authority_receipt_sha256="",
    )
    result = NeuronJointFieldPerspective(
        neuron_id=provisional.neuron_id,
        vertex_id=provisional.vertex_id,
        vertex_index=provisional.vertex_index,
        frame_index=provisional.frame_index,
        complete_field_receipt_sha256=(
            provisional.complete_field_receipt_sha256
        ),
        D_k=provisional.D_k,
        M_k=provisional.M_k,
        R_rev_k=provisional.R_rev_k,
        U_star_k=provisional.U_star_k,
        C_k=provisional.C_k,
        P_k=provisional.P_k,
        B_k=provisional.B_k,
        authority_receipt_sha256=_digest(
            provisional.unsigned_record()
        ),
    )
    result.verify()
    return result


def reconstruct_cohesion(
    perspectives: tuple[NeuronJointFieldPerspective, ...],
) -> tuple[RelationFact, ...]:
    """Reconstruct a complete undirected edge field from local perspectives."""

    if not perspectives:
        raise ValueError("cohesion reconstruction requires perspectives")
    for value in perspectives:
        value.verify()
    field_receipts = {
        value.complete_field_receipt_sha256 for value in perspectives
    }
    frame_indices = {value.frame_index for value in perspectives}
    vertex_indices = {value.vertex_index for value in perspectives}
    if (
        len(field_receipts) != 1
        or len(frame_indices) != 1
        or len(vertex_indices) != len(perspectives)
    ):
        raise ValueError("perspectives do not share one joint field frame")
    edges: dict[tuple[int, int], RelationFact] = {}
    witnesses: dict[tuple[int, int], int] = {}
    for perspective in perspectives:
        for encoded in perspective.C_k:
            key = (encoded.left, encoded.right)
            decoded = encoded.decode()
            if key in edges and edges[key] != decoded:
                raise ValueError("shared cohesion edge disagrees")
            edges[key] = decoded
            witnesses[key] = witnesses.get(key, 0) + 1
    expected_edge_count = len(perspectives) * (len(perspectives) - 1) // 2
    if (
        vertex_indices != set(range(len(perspectives)))
        or len(edges) != expected_edge_count
        or any(count != 2 for count in witnesses.values())
    ):
        raise ValueError("local perspectives do not close the joint field")
    return tuple(edges[key] for key in sorted(edges))


__all__ = (
    "ExactTernaryRational",
    "NeuronJointFieldPerspective",
    "TernaryRelationFact",
    "bind_neuron_perspective",
    "reconstruct_cohesion",
)
