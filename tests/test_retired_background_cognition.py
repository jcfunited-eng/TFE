"""Legacy text/composer loops cannot impersonate causal cognition."""

from __future__ import annotations

from pathlib import Path

from dsf_ai_service import substrate_runner


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
    for retired_name in (
        "_curriculum_feed_chunk",
        "_gap_study_once",
        "_tutor_once",
        "_start_curriculum_orchestrator",
        "_do_corpus_load",
        "handle_load_corpus",
        "handle_corpus_status",
        "_start_autonomous_emission_loop",
        "_start_organ_surface_poll",
        "_cmd_thought",
        "_last_autonomous_thought",
        "_owned_surgery_cache",
    ):
        assert retired_name not in runner_source


def test_remote_event_command_is_not_a_runner_operation() -> None:
    assert "gualaloom_post" not in substrate_runner.OP_HANDLERS
    assert not hasattr(substrate_runner, "_cmd_events")
