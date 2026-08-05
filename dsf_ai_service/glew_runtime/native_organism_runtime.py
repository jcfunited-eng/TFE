"""One-call transport for the current native Guala organism envelope.

This boundary carries exactly one current GLORUN01 state and one already
admitted native sensory episode into Rust. It does not expose the nested
materialized fabric as a second persistence authority. Cognitive formation
claims and counts are read-only native observations; Python does not select or
alter them.
"""

from __future__ import annotations

import hashlib
import importlib
from typing import Protocol, runtime_checkable

from .native_joint_source_episode import ImmutableJointSourceEpisode


OBSERVATION_SCHEMA = "guala.native.organism_runtime.observation.v4"
RESTORED_SCOPE = "current_native_state_restored"
MOUNTED_STEP_SCOPE = "mounted_joint_fractal_and_cognitive_formation_transition"


@runtime_checkable
class ImmutableNativeOrganismTransition(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def scope(self) -> str: ...

    @property
    def identity(self) -> str: ...

    @property
    def predecessor_state_sha256(self) -> str | None: ...

    @property
    def predecessor_organism_tick(self) -> int | None: ...

    @property
    def organism_tick(self) -> int: ...

    @property
    def predecessor_fabric_generation(self) -> int | None: ...

    @property
    def fabric_generation(self) -> int: ...

    @property
    def predecessor_mounted_generation(self) -> int | None: ...

    @property
    def mounted_generation(self) -> int: ...

    @property
    def state_bytes(self) -> int: ...

    @property
    def state_sha256(self) -> str: ...

    @property
    def fabric_bytes(self) -> int: ...

    @property
    def fabric_sha256(self) -> str: ...

    @property
    def joint_field_count(self) -> int: ...

    @property
    def joint_neuron_count(self) -> int: ...

    @property
    def transitioned_fractal_count(self) -> int: ...

    @property
    def recurrent_fractal_count(self) -> int: ...

    @property
    def source_cohort_l0_l4_evaluation_count(self) -> int: ...

    @property
    def successor_l0_l4_replay_count(self) -> int: ...

    @property
    def joint_transition_sha256(self) -> str | None: ...

    @property
    def episode_relation_candidate_sha256(self) -> str | None: ...

    @property
    def source_sha256(self) -> str | None: ...

    @property
    def mounted_step_completed(self) -> bool: ...

    @property
    def physical_transition_claimed(self) -> bool: ...

    @property
    def cognitive_formation_claimed(self) -> bool: ...

    @property
    def cognitive_ordinal(self) -> int: ...

    @property
    def cognitive_trace_count(self) -> int: ...

    @property
    def cognitive_mosaic_count(self) -> int: ...

    @property
    def formation_activation_count(self) -> int: ...

    @property
    def partial_cue_reassembly_count(self) -> int: ...

    @property
    def python_callback_count(self) -> int: ...

    @property
    def derived_budget(self) -> tuple[int, int, int, int, int]: ...

    def as_bytes(self) -> bytes: ...


def _native_core():
    return importlib.import_module("guala_core")


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"native organism {label} must be a positive integer")
    return value


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"native organism {label} is not canonical SHA-256")
    return value


def _budget(
    max_envelope_bytes: object,
    max_fabric_bytes: object,
    max_logical_peak_bytes: object,
) -> tuple[int, int, int, tuple[int, int, int, int, int]]:
    envelope = _positive_integer(
        max_envelope_bytes, "envelope byte boundary"
    )
    fabric = _positive_integer(max_fabric_bytes, "fabric byte boundary")
    logical = _positive_integer(
        max_logical_peak_bytes, "logical peak byte boundary"
    )
    return (
        envelope,
        fabric,
        logical,
        (
            fabric - 26,
            logical - (2 * envelope),
            envelope,
            envelope,
            logical,
        ),
    )


def _require_common_result(
    result: object,
    payload: bytes,
    expected_budget: tuple[int, int, int, int, int],
) -> ImmutableNativeOrganismTransition:
    if not isinstance(result, ImmutableNativeOrganismTransition):
        raise TypeError("native organism operation returned an untyped result")
    returned = result.as_bytes()
    if (
        not isinstance(returned, bytes)
        or not returned.startswith(b"GLORUN01")
        or returned != payload
        or result.schema != OBSERVATION_SCHEMA
        or result.state_bytes != len(returned)
        or _sha256(result.state_sha256, "state")
        != hashlib.sha256(returned).hexdigest()
        or result.derived_budget != expected_budget
        or result.organism_tick < 0
        or result.fabric_generation < 0
        or result.mounted_generation < 0
        or result.joint_field_count < 0
        or result.joint_neuron_count < 0
        or result.transitioned_fractal_count < 0
        or result.recurrent_fractal_count < 0
        or result.recurrent_fractal_count > result.transitioned_fractal_count
        or result.transitioned_fractal_count > result.joint_neuron_count
        or result.physical_transition_claimed
        or not isinstance(result.cognitive_formation_claimed, bool)
        or result.cognitive_ordinal < 0
        or result.cognitive_trace_count < 0
        or result.cognitive_mosaic_count < 0
        or result.formation_activation_count < 0
        or result.partial_cue_reassembly_count < 0
        or result.partial_cue_reassembly_count
        > result.formation_activation_count
        or result.python_callback_count != 0
    ):
        raise RuntimeError("native organism operation changed its causal contract")
    _sha256(result.fabric_sha256, "nested fabric")
    if result.joint_transition_sha256 is not None:
        _sha256(result.joint_transition_sha256, "joint transition")
    if result.episode_relation_candidate_sha256 is not None:
        _sha256(
            result.episode_relation_candidate_sha256,
            "episode relation candidate",
        )
    return result


def restore_native_organism(
    *,
    current_envelope: bytes,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> ImmutableNativeOrganismTransition:
    """Validate one current GLORUN envelope and derive its observation."""

    if not isinstance(current_envelope, bytes) or not current_envelope:
        raise TypeError("native organism current state must be immutable bytes")
    envelope, fabric, logical, expected = _budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    result = _native_core().restore_native_organism_runtime(
        current_envelope,
        envelope,
        fabric,
        logical,
    )
    result = _require_common_result(result, current_envelope, expected)
    if (
        result.scope != RESTORED_SCOPE
        or result.predecessor_state_sha256 is not None
        or result.predecessor_organism_tick is not None
        or result.predecessor_fabric_generation is not None
        or result.predecessor_mounted_generation is not None
        or result.source_sha256 is not None
        or result.mounted_step_completed
        or result.source_cohort_l0_l4_evaluation_count != 0
        or result.successor_l0_l4_replay_count != 0
    ):
        raise RuntimeError("native organism restore changed its causal contract")
    return result


def transition_native_organism(
    *,
    prior_envelope: bytes,
    source: ImmutableJointSourceEpisode,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> ImmutableNativeOrganismTransition:
    """Advance one current native envelope without exposing an inner owner."""

    if not isinstance(prior_envelope, bytes) or not prior_envelope:
        raise TypeError("native organism predecessor must be immutable bytes")
    if not isinstance(source, ImmutableJointSourceEpisode):
        raise TypeError("native organism transition requires a native source episode")
    envelope, fabric, logical, expected = _budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    result = _native_core().transition_native_organism_runtime(
        prior_envelope,
        source,
        envelope,
        fabric,
        logical,
    )
    successor = result.as_bytes()
    result = _require_common_result(result, successor, expected)
    if (
        result.scope != MOUNTED_STEP_SCOPE
        or result.predecessor_state_sha256
        != hashlib.sha256(prior_envelope).hexdigest()
        or result.source_sha256 != source.payload_sha256
        or result.predecessor_organism_tick is None
        or result.organism_tick != result.predecessor_organism_tick + 1
        or result.predecessor_fabric_generation is None
        or result.fabric_generation != result.predecessor_fabric_generation + 1
        or result.predecessor_mounted_generation is None
        or result.mounted_generation != result.predecessor_mounted_generation + 1
        or not result.mounted_step_completed
        or result.source_cohort_l0_l4_evaluation_count
        != result.joint_field_count
        or result.successor_l0_l4_replay_count != 0
    ):
        raise RuntimeError("native organism transition changed its causal contract")
    return result


__all__ = (
    "ImmutableNativeOrganismTransition",
    "MOUNTED_STEP_SCOPE",
    "OBSERVATION_SCHEMA",
    "RESTORED_SCOPE",
    "restore_native_organism",
    "transition_native_organism",
)
