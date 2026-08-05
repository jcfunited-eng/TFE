"""One-call boundary to the native bounded neuronal fabric."""

from __future__ import annotations

import importlib
from typing import Protocol, runtime_checkable

from .native_joint_source_episode import ImmutableJointSourceEpisode


@runtime_checkable
class ImmutableMaterializedFabricTransition(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def state_sha256(self) -> str: ...

    @property
    def outcome(self) -> str: ...

    @property
    def mosaic_sha256(self) -> str | None: ...

    @property
    def mosaic_count(self) -> int: ...

    @property
    def materialized_neuron_count(self) -> int: ...

    @property
    def materialized_body_count(self) -> int: ...

    @property
    def evidence_count(self) -> int: ...

    @property
    def joint_field_count(self) -> int: ...

    @property
    def joint_neuron_count(self) -> int: ...

    @property
    def transitioned_fractal_count(self) -> int: ...

    @property
    def recurrent_fractal_count(self) -> int: ...

    @property
    def joint_transition_sha256(self) -> str | None: ...

    @property
    def episode_relation_candidate_sha256(self) -> str | None: ...

    @property
    def python_callback_count(self) -> int: ...

    def as_bytes(self) -> bytes: ...


@runtime_checkable
class ImmutableAuthenticatedLegacyFabricInspection(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def fabric_generation(self) -> int: ...

    @property
    def mounted_generation(self) -> int: ...

    @property
    def neuron_count(self) -> int: ...

    @property
    def neurons(self) -> list[tuple[str, int, int, str, str]]: ...

    @property
    def python_callback_count(self) -> int: ...


_OUTCOMES = frozenset({
    "joint_field_not_reached",
    "joint_neuronal_state_restored",
    "joint_neuronal_fractals_transitioned",
})


def _native_core():
    return importlib.import_module("guala_core")


def transition_native_materialized_fabric(
    *,
    prior_state: bytes | None,
    source: ImmutableJointSourceEpisode,
    max_state_bytes: int = 64 * 1024 * 1024,
    max_working_bytes: int = 64 * 1024 * 1024,
) -> ImmutableMaterializedFabricTransition:
    if prior_state is not None and not isinstance(prior_state, bytes):
        raise TypeError("materialized prior state must be immutable bytes")
    if not isinstance(source, ImmutableJointSourceEpisode):
        raise TypeError(
            "materialized transition requires an exact joint-source episode"
        )
    for value, label in (
        (max_state_bytes, "state"),
        (max_working_bytes, "working-memory"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"materialized {label} byte boundary must be positive"
            )
    result = _native_core().transition_materialized_fabric(
        prior_state,
        source,
        max_state_bytes,
        max_working_bytes,
    )
    if not isinstance(result, ImmutableMaterializedFabricTransition):
        raise TypeError(
            "native fabric transition did not return its immutable result"
        )
    if result.python_callback_count != 0:
        raise RuntimeError("native fabric transition crossed a Python callback")
    if result.outcome not in _OUTCOMES:
        raise RuntimeError(
            "native fabric transition returned an unknown outcome"
        )
    return result


def migrate_native_materialized_fabric(
    *,
    prior_state: bytes,
    max_state_bytes: int = 64 * 1024 * 1024,
    max_working_bytes: int = 64 * 1024 * 1024,
) -> ImmutableMaterializedFabricTransition:
    if not isinstance(prior_state, bytes) or not prior_state:
        raise TypeError("materialized migration requires immutable prior bytes")
    for value, label in (
        (max_state_bytes, "state"),
        (max_working_bytes, "working-memory"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"materialized {label} byte boundary must be positive"
            )
    result = _native_core().migrate_materialized_fabric(
        prior_state,
        max_state_bytes,
        max_working_bytes,
    )
    if not isinstance(result, ImmutableMaterializedFabricTransition):
        raise TypeError(
            "native fabric migration did not return its immutable result"
        )
    if result.python_callback_count != 0:
        raise RuntimeError("native fabric migration crossed a Python callback")
    if result.outcome not in _OUTCOMES:
        raise RuntimeError("native fabric migration returned an unknown outcome")
    return result


def inspect_authenticated_legacy_materialized_fabric(
    *,
    payload: bytes,
    expected_content_sha256: str,
    max_state_bytes: int = 64 * 1024 * 1024,
    max_working_bytes: int = 512 * 1024 * 1024,
) -> ImmutableAuthenticatedLegacyFabricInspection:
    if not isinstance(payload, bytes) or not payload:
        raise TypeError("legacy materialized inspection requires immutable bytes")
    if (
        not isinstance(expected_content_sha256, str)
        or len(expected_content_sha256) != 64
    ):
        raise ValueError("legacy materialized inspection requires one SHA-256 hex digest")
    try:
        expected_digest = bytes.fromhex(expected_content_sha256)
    except ValueError as error:
        raise ValueError(
            "legacy materialized inspection requires one SHA-256 hex digest"
        ) from error
    if len(expected_digest) != 32:
        raise ValueError("legacy materialized inspection requires one SHA-256 hex digest")
    for value, label in (
        (max_state_bytes, "state"),
        (max_working_bytes, "working-memory"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"legacy materialized inspection {label} byte boundary must be positive"
            )
    result = _native_core().inspect_authenticated_legacy_materialized_fabric(
        payload,
        expected_digest,
        max_state_bytes,
        max_working_bytes,
    )
    if not isinstance(result, ImmutableAuthenticatedLegacyFabricInspection):
        raise TypeError("native legacy fabric inspector returned an untyped result")
    if result.python_callback_count != 0:
        raise RuntimeError("native legacy fabric inspection crossed a Python callback")
    if result.schema != "guala.native.authenticated_legacy_fabric_inspection.v1":
        raise RuntimeError("native legacy fabric inspection returned an unknown schema")
    if result.neuron_count != len(result.neurons):
        raise RuntimeError("native legacy fabric inspection neuron count changed")
    return result


__all__ = (
    "ImmutableAuthenticatedLegacyFabricInspection",
    "ImmutableMaterializedFabricTransition",
    "inspect_authenticated_legacy_materialized_fabric",
    "migrate_native_materialized_fabric",
    "transition_native_materialized_fabric",
)
