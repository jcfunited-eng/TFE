"""Rejected exact model of a proposed bounded sparse coupling law.

This module is not production cognition and does not ratify the law it models.
It tests one proposed D3 boundary without changing frozen L0--L4:

* current D1 neuron-local sign/null fractals remain the local arrival;
* a declared directed edge carries only polarity ``-1`` or ``+1`` and a
  non-negative balanced-ternary positional shift;
* a reached target receives exact shifted copies of predecessor-generation
  source fractals;
* local and neighbour arrivals settle by exact balanced-ternary addition; and
* the coupled result is recorded but never recursively reinjected, so a
  recurrent cycle cannot amplify its own accumulated total.

The model deliberately does not decide how anatomy or growth DNA creates an
edge, how phase/winding evolve, or whether a coupled assembly is a mosaic.
Those remain separate ratification boundaries.  The model was rejected because
whole-word addition permits carry across unrelated typed coordinates, its
settled sum is non-injective, and it does not constitute persistent Krimelack
physics.  It remains only as executable negative evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


SCHEMA = "guala.research.sparse_krimelack_coupling.v1"
MODEL_VERDICT = "rejected_not_typed_krimelack_coupling"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_digest(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _validate_trits(values: tuple[int, ...], name: str) -> None:
    if (
        not isinstance(values, tuple)
        or not values
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value not in (-1, 0, 1)
            for value in values
        )
    ):
        raise ValueError(f"{name} must contain balanced trits")


def _trim(values: list[int]) -> tuple[int, ...]:
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    return tuple(values)


def _sum_shifted_words(
    local: tuple[int, ...],
    arrivals: tuple[tuple[int, int, tuple[int, ...]], ...],
    *,
    max_working_bytes: int,
) -> tuple[int, ...]:
    """Add balanced-ternary words exactly, least-significant trit first."""

    if (
        isinstance(max_working_bytes, bool)
        or not isinstance(max_working_bytes, int)
        or max_working_bytes <= 0
    ):
        raise ValueError("coupling working-memory boundary must be positive")
    _validate_trits(local, "local fractal")
    for polarity, shift, word in arrivals:
        if polarity not in (-1, 1):
            raise ValueError("coupling polarity must be -1 or +1")
        if isinstance(shift, bool) or not isinstance(shift, int) or shift < 0:
            raise ValueError("coupling positional shift must be non-negative")
        _validate_trits(word, "source fractal")

    longest = max(
        (len(local), *(shift + len(word) for _, shift, word in arrivals)),
    )
    operand_count = 1 + len(arrivals)
    carry_trits = 1
    capacity = 3
    while capacity <= operand_count:
        carry_trits += 1
        capacity *= 3
    admitted_trits = longest + carry_trits
    input_trits = len(local) + sum(len(word) for _, _, word in arrivals)
    required_working_bytes = input_trits + admitted_trits
    if required_working_bytes > max_working_bytes:
        raise ValueError(
            "exact sparse coupling requires "
            f"{required_working_bytes} working bytes, admitted "
            f"{max_working_bytes}"
        )

    output: list[int] = []
    carry = 0
    for position in range(admitted_trits):
        total = carry
        if position < len(local):
            total += local[position]
        for polarity, shift, word in arrivals:
            source_position = position - shift
            if 0 <= source_position < len(word):
                total += polarity * word[source_position]
        quotient, remainder = divmod(total, 3)
        if remainder == 2:
            remainder = -1
            quotient += 1
        output.append(remainder)
        carry = quotient
    if carry:
        raise AssertionError("derived balanced-ternary carry admission failed")
    return _trim(output)


@dataclass(frozen=True, slots=True)
class LocalFractal:
    neuron_lineage: str
    complete_field_receipt_sha256: str
    perspective_receipt_sha256: str
    trits: tuple[int, ...]
    receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        neuron_lineage: str,
        complete_field_receipt_sha256: str,
        perspective_receipt_sha256: str,
        trits: tuple[int, ...],
    ) -> "LocalFractal":
        _validate_trits(trits, "local fractal")
        unsigned = {
            "complete_field_receipt_sha256": complete_field_receipt_sha256,
            "neuron_lineage": neuron_lineage,
            "perspective_receipt_sha256": perspective_receipt_sha256,
            "schema": SCHEMA,
            "trits": list(trits),
            "type": "local_fractal",
        }
        return cls(
            neuron_lineage=neuron_lineage,
            complete_field_receipt_sha256=complete_field_receipt_sha256,
            perspective_receipt_sha256=perspective_receipt_sha256,
            trits=trits,
            receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "complete_field_receipt_sha256": (
                self.complete_field_receipt_sha256
            ),
            "neuron_lineage": self.neuron_lineage,
            "perspective_receipt_sha256": self.perspective_receipt_sha256,
            "receipt_sha256": self.receipt_sha256,
            "schema": SCHEMA,
            "trits": list(self.trits),
            "type": "local_fractal",
        }

    def verify(self) -> None:
        if not self.neuron_lineage:
            raise ValueError("local fractal neuron lineage is empty")
        _validate_digest(
            self.complete_field_receipt_sha256,
            "complete field receipt",
        )
        _validate_digest(
            self.perspective_receipt_sha256,
            "perspective receipt",
        )
        _validate_trits(self.trits, "local fractal")
        expected = LocalFractal.create(
            neuron_lineage=self.neuron_lineage,
            complete_field_receipt_sha256=(
                self.complete_field_receipt_sha256
            ),
            perspective_receipt_sha256=self.perspective_receipt_sha256,
            trits=self.trits,
        )
        if expected != self:
            raise ValueError("local fractal receipt changed")


@dataclass(frozen=True, slots=True, order=True)
class SparseCoupling:
    target_lineage: str
    source_lineage: str
    polarity: int
    positional_shift: int
    anatomy_receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "anatomy_receipt_sha256": self.anatomy_receipt_sha256,
            "polarity": self.polarity,
            "positional_shift": self.positional_shift,
            "source_lineage": self.source_lineage,
            "target_lineage": self.target_lineage,
        }

    def verify(self) -> None:
        if (
            not self.source_lineage
            or not self.target_lineage
            or self.source_lineage == self.target_lineage
            or self.polarity not in (-1, 1)
            or isinstance(self.positional_shift, bool)
            or not isinstance(self.positional_shift, int)
            or self.positional_shift < 0
        ):
            raise ValueError("sparse coupling constitution is invalid")
        _validate_digest(self.anatomy_receipt_sha256, "anatomy receipt")


@dataclass(frozen=True, slots=True)
class CausalContribution:
    source_lineage: str
    source_fractal_receipt_sha256: str
    polarity: int
    positional_shift: int
    contribution_receipt_sha256: str

    @classmethod
    def create(
        cls,
        coupling: SparseCoupling,
        source: LocalFractal,
    ) -> "CausalContribution":
        unsigned = {
            "anatomy_receipt_sha256": coupling.anatomy_receipt_sha256,
            "polarity": coupling.polarity,
            "positional_shift": coupling.positional_shift,
            "source_fractal_receipt_sha256": source.receipt_sha256,
            "source_lineage": source.neuron_lineage,
            "target_lineage": coupling.target_lineage,
            "type": "predecessor_arrival",
        }
        return cls(
            source_lineage=source.neuron_lineage,
            source_fractal_receipt_sha256=source.receipt_sha256,
            polarity=coupling.polarity,
            positional_shift=coupling.positional_shift,
            contribution_receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "contribution_receipt_sha256": (
                self.contribution_receipt_sha256
            ),
            "polarity": self.polarity,
            "positional_shift": self.positional_shift,
            "source_fractal_receipt_sha256": (
                self.source_fractal_receipt_sha256
            ),
            "source_lineage": self.source_lineage,
        }


@dataclass(frozen=True, slots=True)
class CoupledSettlement:
    neuron_lineage: str
    generation: int
    local_fractal_receipt_sha256: str
    contributions: tuple[CausalContribution, ...]
    trits: tuple[int, ...]
    receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "contributions": [
                contribution.as_record()
                for contribution in self.contributions
            ],
            "generation": self.generation,
            "local_fractal_receipt_sha256": (
                self.local_fractal_receipt_sha256
            ),
            "neuron_lineage": self.neuron_lineage,
            "receipt_sha256": self.receipt_sha256,
            "trits": list(self.trits),
        }


@dataclass(frozen=True, slots=True)
class SparseKrimelackState:
    generation: int
    couplings: tuple[SparseCoupling, ...]
    local_fractals: tuple[LocalFractal, ...]
    settlements: tuple[CoupledSettlement, ...]
    receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "couplings": [coupling.as_record() for coupling in self.couplings],
            "generation": self.generation,
            "local_fractals": [
                fractal.as_record() for fractal in self.local_fractals
            ],
            "schema": SCHEMA,
            "settlements": [
                settlement.as_record() for settlement in self.settlements
            ],
        }

    def encode(self, *, max_state_bytes: int) -> bytes:
        record = {
            **self.unsigned_record(),
            "receipt_sha256": self.receipt_sha256,
        }
        encoded = _canonical_bytes(record)
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or max_state_bytes <= 0
            or len(encoded) > max_state_bytes
        ):
            raise ValueError("sparse coupling state exceeds admitted bytes")
        return encoded


def _settlement_receipt(
    *,
    neuron_lineage: str,
    generation: int,
    local_receipt: str,
    contributions: tuple[CausalContribution, ...],
    trits: tuple[int, ...],
) -> str:
    return _digest({
        "contributions": [item.as_record() for item in contributions],
        "generation": generation,
        "local_fractal_receipt_sha256": local_receipt,
        "neuron_lineage": neuron_lineage,
        "trits": list(trits),
        "type": "coupled_settlement",
    })


def transition_sparse_krimelack(
    *,
    prior: SparseKrimelackState | None,
    current_local_fractals: tuple[LocalFractal, ...],
    couplings: tuple[SparseCoupling, ...],
    max_state_bytes: int,
    max_working_bytes: int,
) -> SparseKrimelackState:
    """Settle one proposed synchronous predecessor-to-successor generation."""

    if not current_local_fractals:
        raise ValueError("sparse coupling transition has no reached neurons")
    for fractal in current_local_fractals:
        fractal.verify()
    current_by_lineage = {
        fractal.neuron_lineage: fractal
        for fractal in current_local_fractals
    }
    if len(current_by_lineage) != len(current_local_fractals):
        raise ValueError("reached neuron lineage is duplicated")

    ordered_couplings = tuple(sorted(couplings))
    if len(set(ordered_couplings)) != len(ordered_couplings):
        raise ValueError("sparse coupling is duplicated")
    for coupling in ordered_couplings:
        coupling.verify()
        if (
            coupling.source_lineage not in current_by_lineage
            or coupling.target_lineage not in current_by_lineage
        ):
            raise ValueError("coupling endpoint is outside the reached model")

    generation = 1 if prior is None else prior.generation + 1
    predecessor_by_lineage: dict[str, LocalFractal] = {}
    if prior is not None:
        if prior.couplings != ordered_couplings:
            raise ValueError("coupling topology changed without a growth law")
        predecessor_by_lineage = {
            fractal.neuron_lineage: fractal
            for fractal in prior.local_fractals
        }

    settlements: list[CoupledSettlement] = []
    for target_lineage, local in sorted(current_by_lineage.items()):
        target_edges = tuple(
            coupling
            for coupling in ordered_couplings
            if coupling.target_lineage == target_lineage
        )
        arrivals: list[tuple[int, int, tuple[int, ...]]] = []
        contributions: list[CausalContribution] = []
        for coupling in target_edges:
            source = predecessor_by_lineage.get(coupling.source_lineage)
            if source is None:
                continue
            arrivals.append((
                coupling.polarity,
                coupling.positional_shift,
                source.trits,
            ))
            contributions.append(CausalContribution.create(coupling, source))
        settled_trits = _sum_shifted_words(
            local.trits,
            tuple(arrivals),
            max_working_bytes=max_working_bytes,
        )
        contribution_tuple = tuple(contributions)
        settlements.append(CoupledSettlement(
            neuron_lineage=target_lineage,
            generation=generation,
            local_fractal_receipt_sha256=local.receipt_sha256,
            contributions=contribution_tuple,
            trits=settled_trits,
            receipt_sha256=_settlement_receipt(
                neuron_lineage=target_lineage,
                generation=generation,
                local_receipt=local.receipt_sha256,
                contributions=contribution_tuple,
                trits=settled_trits,
            ),
        ))

    provisional = SparseKrimelackState(
        generation=generation,
        couplings=ordered_couplings,
        local_fractals=tuple(sorted(
            current_local_fractals,
            key=lambda value: value.neuron_lineage,
        )),
        settlements=tuple(settlements),
        receipt_sha256="",
    )
    result = SparseKrimelackState(
        generation=provisional.generation,
        couplings=provisional.couplings,
        local_fractals=provisional.local_fractals,
        settlements=provisional.settlements,
        receipt_sha256=_digest(provisional.unsigned_record()),
    )
    result.encode(max_state_bytes=max_state_bytes)
    return result


__all__ = [
    "CausalContribution",
    "CoupledSettlement",
    "LocalFractal",
    "MODEL_VERDICT",
    "SparseCoupling",
    "SparseKrimelackState",
    "transition_sparse_krimelack",
]
