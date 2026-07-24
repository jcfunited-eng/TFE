from __future__ import annotations

import inspect
import subprocess
import sys
from types import SimpleNamespace

import pytest

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate import deployment_generation


def _generation():
    return SimpleNamespace(
        generation_uuid="11111111-1111-4111-8111-111111111111",
        identity="guala-identity",
        tick=73,
    )


def test_live_validator_uses_one_bounded_child_process(
    monkeypatch, tmp_path,
) -> None:
    generation = _generation()
    materialized = SimpleNamespace(
        generation_uuid=generation.generation_uuid,
    )
    monkeypatch.setattr(
        deployment_generation,
        "materialize_verified_generation",
        lambda **values: (
            materialized
            if values["generation"] is generation
            and values["active_directory"].endswith("/active")
            else (_ for _ in ()).throw(AssertionError("wrong materialization"))
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_verified_generation_requires_legacy_pickle_migration",
        lambda value: value is generation,
    )
    calls = []

    def run(command, **values):
        calls.append((command, values))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)

    assert app_module._validate_runtime_generation_cold_restore(
        generation
    ) is True
    assert len(calls) == 1
    command, values = calls[0]
    assert command[0] == sys.executable
    assert command[1:3] == [
        "-m",
        "dsf_ai_service.cold_restore_probe",
    ]
    assert "--allow-authenticated-legacy-pickle" in command
    assert values == {
        "check": False,
        "capture_output": True,
        "text": True,
        "timeout": 540,
    }
    source = inspect.getsource(
        app_module._validate_runtime_generation_cold_restore
    )
    assert "probe = Guala()" not in source
    assert "probe.load_full_state" not in source


def test_isolated_probe_failure_and_timeout_fail_generation_closed(
    monkeypatch,
) -> None:
    generation = _generation()
    monkeypatch.setattr(
        deployment_generation,
        "materialize_verified_generation",
        lambda **_values: SimpleNamespace(
            generation_uuid=generation.generation_uuid,
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_verified_generation_requires_legacy_pickle_migration",
        lambda _value: False,
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_values: SimpleNamespace(
            returncode=7,
            stdout="exact load failed",
            stderr="",
        ),
    )
    with pytest.raises(
        RuntimeError,
        match="return code 7: exact load failed",
    ):
        app_module._validate_runtime_generation_cold_restore(generation)

    def timeout(*_args, **_values):
        raise subprocess.TimeoutExpired("probe", 540)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="540-second"):
        app_module._validate_runtime_generation_cold_restore(generation)


def test_periodic_cold_failure_cannot_become_a_one_minute_retry_storm() -> None:
    interval = app_module._PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS
    cadence = app_module._PeriodicColdCheckpointCadence(
        monotonic_now=100.0,
        wall_now=1_000.0,
    )

    assert cadence.next_wall == 1_000.0 + interval
    assert cadence.admit(
        monotonic_now=100.0 + interval - 1,
        wall_now=1_000.0 + interval - 1,
    ) is False
    assert cadence.admit(
        monotonic_now=100.0 + interval,
        wall_now=1_000.0 + interval,
    ) is True
    assert cadence.next_wall == 1_000.0 + (2 * interval)
    assert cadence.admit(
        monotonic_now=100.0 + interval + 60,
        wall_now=1_000.0 + interval + 60,
    ) is False
    assert cadence.admit(
        monotonic_now=100.0 + (2 * interval),
        wall_now=1_000.0 + (2 * interval),
    ) is True
