"""Legacy text/composer loops cannot impersonate causal cognition."""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service import substrate_runner


class _EventSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def _log_substrate_event(self, kind: str, **detail: object) -> None:
        self.events.append((kind, detail))


def test_fixed_composer_background_loop_is_retired(monkeypatch) -> None:
    sink = _EventSink()
    started: list[str] = []
    monkeypatch.setattr(substrate_runner, "_guala", sink)
    monkeypatch.setattr(
        substrate_runner,
        "_start_background_thread",
        lambda _target, name, **_kwargs: started.append(name),
    )

    result = substrate_runner._start_autonomous_emission_loop()

    assert result == substrate_runner._RETIRED_BACKGROUND_COGNITION
    assert started == []
    assert sink.events == [
        (
            "background_cognition_retired",
            substrate_runner._RETIRED_BACKGROUND_COGNITION,
        )
    ]


def test_text_gap_and_continuation_tutors_are_retired(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("retired text tutor attempted a side effect")

    monkeypatch.setattr(substrate_runner, "_cmd_converse", forbidden)
    monkeypatch.setattr(substrate_runner, "_curriculum_feed_chunk", forbidden)
    substrate_runner._TUTOR_STATE["last_status"] = {}

    expected = substrate_runner._RETIRED_BACKGROUND_COGNITION
    assert substrate_runner._gap_study_once() == expected
    assert substrate_runner._tutor_once() == expected
    assert substrate_runner._TUTOR_STATE["last_status"] == expected


def test_density_orchestrator_cannot_be_reenabled_by_environment(
    monkeypatch,
) -> None:
    started: list[str] = []
    monkeypatch.setenv("CURRICULUM_AUTOSTART", "1")
    monkeypatch.setattr(
        substrate_runner,
        "_start_background_thread",
        lambda _target, name, **_kwargs: started.append(name),
    )

    result = substrate_runner._start_curriculum_orchestrator()

    assert result == substrate_runner._RETIRED_BACKGROUND_COGNITION
    assert started == []


def test_thought_surface_reports_retirement_without_invented_speech(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        substrate_runner,
        "_last_autonomous_thought",
        {
            "speech": "",
            "tick": 0,
            "ts": 0.0,
            **substrate_runner._RETIRED_BACKGROUND_COGNITION,
        },
    )

    observed = substrate_runner._cmd_thought()

    assert observed["speech"] == ""
    assert observed["state"] == "retired_wrong_architecture"
    assert observed["replacement"] == "bounded_causal_play_action_cycle"


def test_live_boot_has_no_legacy_text_scheduler_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    app_source = (root / "dsf_ai_service" / "app.py").read_text(
        encoding="utf-8"
    )
    runner_source = (
        root / "dsf_ai_service" / "substrate_runner.py"
    ).read_text(encoding="utf-8")

    assert "from dsf_ai_service.loom_model.curriculum_scheduler import" not in (
        app_source
    )
    assert "CurriculumScheduler(" not in runner_source
    assert "_start_background_thread(_loop, \"autonomous-emission\")" not in (
        runner_source
    )


def test_remote_event_command_preserves_sequence_cursor(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _Events:
        def get_recent_events(self, **kwargs):
            calls.append(kwargs)
            return [{"sequence": 12, "tick": 4, "kind": "second"}]

        @staticmethod
        def event_stream_status():
            return {"epoch": "e" * 64, "latest_sequence": 12}

        @staticmethod
        def introspect():
            return {"vocab": 0}

    monkeypatch.setattr(substrate_runner, "_guala", _Events())
    result = substrate_runner._cmd_events(json.dumps({
        "after_sequence": 11,
        "limit": 50,
    }))

    assert calls == [{
        "since_tick": 0,
        "limit": 50,
        "since_sequence": 11,
    }]
    assert result["events"][0]["sequence"] == 12
    assert result["event_stream"]["epoch"] == "e" * 64
