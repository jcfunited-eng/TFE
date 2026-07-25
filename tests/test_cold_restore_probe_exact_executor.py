from __future__ import annotations

from types import SimpleNamespace

import pytest

import dsf_ai_service.app as app_module
import dsf_ai_service.cold_restore_probe as probe_module
from dsf_ai_service.glew_runtime import exact_field_executor
from dsf_ai_service.v4 import gualaloom_v5_engine


def test_isolated_cold_restore_owns_exact_executor_for_entire_load(
    monkeypatch,
) -> None:
    events = []

    class ExactOwner:
        def assert_healthy(self) -> None:
            events.append("executor-healthy")

    class Probe:
        def __init__(self) -> None:
            events.append("guala-constructed")
            self._load_successful = False
            self._guala_identity = None
            self.tick = 0

        def add_corpus(self, corpus_id, title, lines) -> None:
            events.append(("corpus", corpus_id, title, tuple(lines)))

        def load_full_state(
            self,
            active_directory,
            *,
            require_exact_binary,
            allow_authenticated_legacy_pickle,
        ) -> None:
            events.append((
                "load",
                active_directory,
                require_exact_binary,
                allow_authenticated_legacy_pickle,
            ))
            self._load_successful = True
            self._guala_identity = "identity-1"
            self.tick = 73

        def quiesce_background_workers(self, *, timeout) -> None:
            events.append(("guala-stopped", timeout))

    monkeypatch.setattr(
        probe_module,
        "_arguments",
        lambda: SimpleNamespace(
            active_directory="/generation/active",
            expected_identity="identity-1",
            expected_tick=73,
            allow_authenticated_legacy_pickle=False,
        ),
    )
    monkeypatch.setattr(
        app_module,
        "SEED_CORPORA",
        {
            "seed": {
                "title": "Seed",
                "lines": ("one", "two"),
            }
        },
    )
    monkeypatch.setattr(
        exact_field_executor,
        "start_exact_field_executor",
        lambda: events.append("executor-started") or ExactOwner(),
    )
    monkeypatch.setattr(
        exact_field_executor,
        "stop_exact_field_executor",
        lambda: events.append("executor-stopped"),
    )
    monkeypatch.setattr(gualaloom_v5_engine, "Guala", Probe)

    assert probe_module.main() == 0
    assert events == [
        "executor-started",
        "executor-healthy",
        "guala-constructed",
        ("corpus", "seed", "Seed", ("one", "two")),
        ("load", "/generation/active", True, False),
        ("guala-stopped", 120.0),
        "executor-stopped",
    ]


def test_isolated_cold_restore_stops_exact_executor_after_load_failure(
    monkeypatch,
) -> None:
    events = []

    class ExactOwner:
        def assert_healthy(self) -> None:
            events.append("executor-healthy")

    class Probe:
        def __init__(self) -> None:
            events.append("guala-constructed")

        def add_corpus(self, *_values) -> None:
            pass

        def load_full_state(self, *_values, **_options) -> None:
            raise RuntimeError("load failed")

        def quiesce_background_workers(self, *, timeout) -> None:
            events.append(("guala-stopped", timeout))

    monkeypatch.setattr(
        probe_module,
        "_arguments",
        lambda: SimpleNamespace(
            active_directory="/generation/active",
            expected_identity="identity-1",
            expected_tick=73,
            allow_authenticated_legacy_pickle=False,
        ),
    )
    monkeypatch.setattr(app_module, "SEED_CORPORA", {})
    monkeypatch.setattr(
        exact_field_executor,
        "start_exact_field_executor",
        lambda: events.append("executor-started") or ExactOwner(),
    )
    monkeypatch.setattr(
        exact_field_executor,
        "stop_exact_field_executor",
        lambda: events.append("executor-stopped"),
    )
    monkeypatch.setattr(gualaloom_v5_engine, "Guala", Probe)

    with pytest.raises(RuntimeError, match="load failed"):
        probe_module.main()
    assert events == [
        "executor-started",
        "executor-healthy",
        "guala-constructed",
        ("guala-stopped", 120.0),
        "executor-stopped",
    ]
