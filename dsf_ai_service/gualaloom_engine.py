"""Retired parallel engine compatibility surface.

The former module contained an independent word-driven engine that loaded a
hand-authored sensory corpus.  That architecture is retired.  A deterministic
language fact-strand still imports the balanced-ternary topology primitives
that originated here, so only those exact mathematical primitives remain.
They do not create sensory evidence, meanings, learned state, or persistence.
"""

from __future__ import annotations

from collections.abc import Sequence


P3I = (1, 3, 9, 27, 81, 243, 729, 2187)
TRITS = 8


def encode(character: str) -> tuple[int, ...]:
    """Encode one Unicode scalar into an eight-place balanced-ternary strand."""

    if not isinstance(character, str) or len(character) != 1:
        raise ValueError("balanced-ternary encoding requires one character")
    value = ord(character) - 96
    trits: list[int] = []
    for _ in range(TRITS):
        remainder = value % 3
        if remainder == 2:
            remainder = -1
            value = (value + 1) // 3
        else:
            value = (value - remainder) // 3
        trits.append(remainder)
    return tuple(trits)


def chi(state: Sequence[int]) -> tuple[int, int]:
    """Return Euler characteristic and committed-vertex count."""

    if any(value not in (-1, 0, 1) for value in state):
        raise ValueError("balanced-ternary state contains a non-trit")
    vertices = tuple(index for index, value in enumerate(state) if value)
    vertex_set = frozenset(vertices)
    vertex_count = len(vertices)
    if vertex_count == 0:
        return 0, 0
    edge_count = sum(
        1
        for index in vertices
        if index + 1 in vertex_set and (index + 1) % TRITS != 0
    )
    strand_count = len(state) // TRITS
    for position in range(TRITS):
        committed = sum(
            1
            for strand in range(strand_count)
            if state[strand * TRITS + position] != 0
        )
        edge_count += max(committed - 1, 0)
    return vertex_count - edge_count, vertex_count


__all__ = ("P3I", "TRITS", "chi", "encode")
