from __future__ import annotations

from pathlib import Path

import pytest

from dsf_ai_service.substrate import native_resident_resource_admission as admission


def _finite_cgroup(
    monkeypatch,
    tmp_path: Path,
    *,
    ceiling: int,
    current: int,
) -> None:
    ceiling_path = tmp_path / "memory.max"
    current_path = tmp_path / "memory.current"
    ceiling_path.write_text(f"{ceiling}\n", encoding="ascii")
    current_path.write_text(f"{current}\n", encoding="ascii")
    monkeypatch.setattr(
        admission,
        "_CGROUP_MEMORY_FILES",
        ((str(ceiling_path), str(current_path)),),
    )


def test_admission_is_derived_from_three_concurrent_regions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _finite_cgroup(
        monkeypatch,
        tmp_path,
        ceiling=1_000_000,
        current=100_000,
    )
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", "800000")

    result = admission.derive_native_resident_resource_admission(tmp_path)

    assert result.runtime_available_bytes == 900_000
    assert result.memory_boundary_source == "cgroup_available_bytes"
    assert result.persistence_available_bytes == 800_000
    assert result.max_envelope_bytes == 300_000
    assert result.max_fabric_bytes == 300_000 - (8 + 2 + 36 + 8 + 4)
    assert result.max_logical_peak_bytes == 900_000
    assert "predecessor+successor+transition_work" in result.derivation


def test_persistence_boundary_can_be_the_smaller_physical_constraint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _finite_cgroup(
        monkeypatch,
        tmp_path,
        ceiling=3_000_000,
        current=0,
    )
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", "200000")

    result = admission.derive_native_resident_resource_admission(tmp_path)

    assert result.max_envelope_bytes == 200_000
    assert result.max_logical_peak_bytes == 600_000
    assert result.max_logical_peak_bytes <= result.runtime_available_bytes


def test_unbounded_cgroup_uses_observed_host_available_memory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable:       900 kB\n", encoding="ascii")
    monkeypatch.setattr(admission, "_CGROUP_MEMORY_FILES", ())
    monkeypatch.setattr(admission, "_MEMINFO_PATH", str(meminfo))
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", "800000")

    result = admission.derive_native_resident_resource_admission(tmp_path)

    assert result.runtime_available_bytes == 900 * 1024
    assert result.memory_boundary_source == "host_memavailable_bytes"
    assert result.max_envelope_bytes == (900 * 1024) // 3


def test_no_finite_memory_observation_is_not_replaced_by_fixed_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(admission, "_CGROUP_MEMORY_FILES", ())
    monkeypatch.setattr(admission, "_MEMINFO_PATH", str(tmp_path / "absent"))
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", "800000")

    with pytest.raises(RuntimeError, match="finite memory"):
        admission.derive_native_resident_resource_admission(tmp_path)


def test_invalid_configured_persistence_boundary_fails_closed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _finite_cgroup(
        monkeypatch,
        tmp_path,
        ceiling=1_000_000,
        current=100_000,
    )
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", "not-an-integer")

    with pytest.raises(RuntimeError, match="not an integer"):
        admission.derive_native_resident_resource_admission(tmp_path)
