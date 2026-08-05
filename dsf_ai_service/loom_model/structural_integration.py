"""Deterministic structural integration primitives for Loom neurons.

This module owns the neuron population math without importing any Guala
application runtime or legacy cognition shell.
"""

from __future__ import annotations

import cmath
import math

import numpy as np


CHI_CORR_LENGTH = 50.0
MIN_GAIN_THRESHOLD = 0.10
_SPIN_VECTOR_DIM = 7
_SPIN_DIM_PHASES = np.array(
    [dimension * math.pi / 7 for dimension in range(_SPIN_VECTOR_DIM)],
    dtype=np.float64,
)
_SPIN_DIM_PHASE_FACTORS = np.exp(1j * _SPIN_DIM_PHASES)
_SPIN_DIM_NAMES = [
    "chi_resonance",
    "source_match",
    "affective_charge",
    "sensory_grounding",
    "episodic_recency",
    "semantic_neighborhood",
    "polarity",
]


def _grandurun_state(
    binding,
    target_chi,
    target_source,
    needs_vector,
    current_tick,
    co_occurrence_dict=None,
):
    """Return the unchanged seven-component complex neuron state."""
    vector = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
    chi_address = binding.get("chi", 0)
    strength = float(binding.get("strength", 0.0))
    phase = (
        math.pi
        * abs(chi_address - target_chi)
        / CHI_CORR_LENGTH
    )
    vector[0] = (
        math.sqrt(max(strength, 0.0))
        * cmath.exp(1j * phase)
    )
    vector[1] = (
        1.0
        if binding.get("source", "corpus") == target_source
        else 0.3
    )
    needs = (
        needs_vector
        if isinstance(needs_vector, np.ndarray)
        else np.asarray(needs_vector, dtype=np.float64)
    )
    vector[2] = (
        needs[0] * float(binding.get("arousal", 0.5))
        + needs[1] * float(binding.get("valence", 0.5))
        + needs[2] * float(binding.get("surprise", 0.5))
    )
    vector[3] = min(len(binding.get("sensory_refs", ())) / 5.0, 1.0)
    last_tick = float(binding.get("last_tick", current_tick))
    vector[4] = math.exp(
        -max(current_tick - last_tick, 0.0) / 200.0
    )
    if co_occurrence_dict:
        vector[5] = float(
            co_occurrence_dict.get(str(chi_address), 0.0)
        )
    vector[6] = float(binding.get("polarity", 1.0))
    vector *= _SPIN_DIM_PHASE_FACTORS
    return vector


def _grandurun_select_vector(candidates, target_state):
    """Apply the unchanged deterministic coherent-integration selection."""
    del target_state
    chosen_vectors = []
    chosen_values = []
    composition_sum = np.zeros(
        _SPIN_VECTOR_DIM,
        dtype=np.complex128,
    )
    last_alignment = 0.0
    last_magnitude_squared = 0.0
    pool = sorted(candidates, key=lambda candidate: -abs(candidate[0][0]))
    for state_vector, value in pool:
        new_sum = composition_sum + state_vector
        alignment = float(np.real(np.vdot(new_sum, state_vector)))
        gain = alignment - last_alignment
        if gain > MIN_GAIN_THRESHOLD * last_magnitude_squared:
            chosen_values.append(value)
            chosen_vectors.append(state_vector)
            composition_sum = new_sum
            last_alignment = alignment
            last_magnitude_squared = float(
                np.real(np.vdot(composition_sum, composition_sum))
            )
    contributions = {}
    if chosen_vectors:
        final_sum = np.zeros(
            _SPIN_VECTOR_DIM,
            dtype=np.complex128,
        )
        for vector in chosen_vectors:
            final_sum += vector
        per_dimension = np.real(final_sum * np.conj(final_sum))
        contributions = {
            name: round(float(per_dimension[index]), 4)
            for index, name in enumerate(_SPIN_DIM_NAMES)
        }
    return chosen_values, last_alignment, contributions


__all__ = [
    "MIN_GAIN_THRESHOLD",
    "_SPIN_DIM_NAMES",
    "_SPIN_VECTOR_DIM",
    "_grandurun_select_vector",
    "_grandurun_state",
]
