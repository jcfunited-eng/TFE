"""Derived resource admission for one native resident Guala organism.

The resident runtime can simultaneously retain a predecessor envelope, build a
successor envelope, and use a transition work region.  Its envelope admission
is derived from the finite bytes available to those three regions and from the
finite persistence/serialization boundary.  No neuron, mosaic, lesson, age,
or other semantic count is used as a growth cap.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


_GLORUN_FIXED_BYTES = 8 + 2 + 36 + 8 + 4
_GLMFAB_FIXED_BYTES = 8 + 2 + 8 + 4 + 4
_U32_MAX = (1 << 32) - 1
_CGROUP_MEMORY_FILES = (
    (
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory.current",
    ),
    (
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        "/sys/fs/cgroup/memory/memory.usage_in_bytes",
    ),
)
_MEMINFO_PATH = "/proc/meminfo"


@dataclass(frozen=True, slots=True)
class NativeResidentResourceAdmission:
    max_envelope_bytes: int
    max_fabric_bytes: int
    max_logical_peak_bytes: int
    runtime_available_bytes: int
    persistence_available_bytes: int
    memory_boundary_source: str
    derivation: str


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"native resident {label} is not a positive integer")
    return value


def _host_memory_available_bytes() -> int:
    try:
        rows = Path(_MEMINFO_PATH).read_text(encoding="ascii").splitlines()
    except FileNotFoundError as error:
        raise RuntimeError(
            "native resident runtime lacks a finite memory boundary"
        ) from error
    for row in rows:
        name, separator, raw = row.partition(":")
        if name != "MemAvailable" or not separator:
            continue
        parts = raw.split()
        if len(parts) != 2 or parts[1] != "kB":
            break
        try:
            return _positive_integer(
                int(parts[0]) * 1024,
                "host available memory bytes",
            )
        except ValueError as error:
            raise RuntimeError(
                "native resident host memory observation is invalid"
            ) from error
    raise RuntimeError(
        "native resident runtime lacks a finite memory boundary"
    )


def _runtime_available_bytes() -> tuple[int, str]:
    observations: list[int] = []
    for ceiling_path, current_path in _CGROUP_MEMORY_FILES:
        try:
            ceiling_raw = Path(ceiling_path).read_bytes()[:64].strip()
            current_raw = Path(current_path).read_bytes()[:64].strip()
        except FileNotFoundError:
            continue
        if ceiling_raw == b"max":
            continue
        try:
            ceiling = int(ceiling_raw)
            current = int(current_raw)
        except ValueError as error:
            raise RuntimeError(
                "native resident cgroup memory observation is invalid"
            ) from error
        if ceiling <= 0 or current < 0 or current >= ceiling:
            raise RuntimeError(
                "native resident cgroup has no finite available bytes"
            )
        observations.append(ceiling - current)
    if observations:
        return min(observations), "cgroup_available_bytes"
    return _host_memory_available_bytes(), "host_memavailable_bytes"


def _persistence_available_bytes(state_directory: str | os.PathLike[str]) -> int:
    configured = os.environ.get("GUALA_MAX_COLD_GENERATION_BYTES")
    if configured is not None:
        try:
            return _positive_integer(int(configured), "cold generation bytes")
        except ValueError as error:
            raise RuntimeError(
                "GUALA_MAX_COLD_GENERATION_BYTES is not an integer"
            ) from error
    path = Path(state_directory)
    existing = path
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    information = os.statvfs(existing)
    available = information.f_bavail * information.f_frsize
    return _positive_integer(available, "filesystem available bytes")


def derive_native_resident_resource_admission(
    state_directory: str | os.PathLike[str],
) -> NativeResidentResourceAdmission:
    """Derive current admission without a semantic or historical fixed cap."""

    runtime_available, memory_source = _runtime_available_bytes()
    persistence_available = _persistence_available_bytes(state_directory)

    # A transition has exactly three concurrent byte regions: retained current
    # envelope, candidate envelope, and transition work.  Equal maximum regions
    # are the largest symmetric admission that cannot exceed the observed
    # memory boundary even when all three are simultaneously full.
    concurrent_region_bytes = runtime_available // 3
    serialization_envelope_bytes = _U32_MAX + _GLORUN_FIXED_BYTES
    envelope = min(
        concurrent_region_bytes,
        persistence_available,
        serialization_envelope_bytes,
    )
    if envelope <= _GLORUN_FIXED_BYTES + _GLMFAB_FIXED_BYTES:
        raise RuntimeError(
            "native resident physical resources cannot hold one organism"
        )
    fabric = envelope - _GLORUN_FIXED_BYTES
    logical_peak = envelope * 3
    if logical_peak > runtime_available:
        raise RuntimeError(
            "native resident derived logical peak exceeds available memory"
        )
    return NativeResidentResourceAdmission(
        max_envelope_bytes=envelope,
        max_fabric_bytes=fabric,
        max_logical_peak_bytes=logical_peak,
        runtime_available_bytes=runtime_available,
        persistence_available_bytes=persistence_available,
        memory_boundary_source=memory_source,
        derivation=(
            "min(finite_persistence_bytes,finite_serialization_bytes,"
            "floor(runtime_available_bytes/3));three_regions="
            "predecessor+successor+transition_work"
        ),
    )


__all__ = (
    "NativeResidentResourceAdmission",
    "derive_native_resident_resource_admission",
)
