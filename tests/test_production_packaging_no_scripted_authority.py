"""Production packaging cannot activate static text/chi cognition."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILES = (
    ROOT / "dsf_ai_service" / "Dockerfile",
    ROOT / "dsf_ai_service" / "Dockerfile.nogil",
)
HEMISPHERE_FLAGS = (
    "HEMI_PR_ENABLED",
    "HEMI_EP_ENABLED",
    "HEMI_SC_ENABLED",
    "HEMI_GP_ENABLED",
)


def test_images_do_not_package_static_text_curriculum_or_enable_chi_roles() -> None:
    for path in DOCKERFILES:
        source = path.read_text(encoding="utf-8")
        assert "COPY dsf_ai_service/corpus/" not in source
        assert "sensory_curriculum_orchestrator.py" not in source
        assert "curriculum_seed.json" not in source
        for flag in HEMISPHERE_FLAGS:
            assert flag not in source


def test_build_context_excludes_static_corpus_and_curriculum_tools() -> None:
    source = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "dsf_ai_service/corpus/" in source
    assert "dsf_ai_service/corpus/**" in source
    assert "!tools/sensory_curriculum_orchestrator.py" not in source
    assert "!tools/curriculum_seed.json" not in source


def test_deployer_cannot_reenable_legacy_hemisphere_roles() -> None:
    deploy = (
        ROOT / "tools" / "deploy_dsf_ai.sh"
    ).read_text(encoding="utf-8")
    for flag in HEMISPHERE_FLAGS:
        assert flag not in deploy

    hemisphere = (
        ROOT
        / "dsf_ai_service"
        / "substrate"
        / "hemisphere_cognition.py"
    ).read_text(encoding="utf-8")
    for flag in HEMISPHERE_FLAGS:
        assert f'os.environ.get("{flag}", "0")' in hemisphere


def test_runner_contains_no_dead_scripted_identity_seed_corpus() -> None:
    source = (
        ROOT / "dsf_ai_service" / "substrate_runner.py"
    ).read_text(encoding="utf-8")
    assert "_seed_corpus" not in source


def test_scripted_text_curriculum_implementations_are_deleted() -> None:
    retired_paths = (
        "dsf_ai_service/curriculum/__init__.py",
        "dsf_ai_service/curriculum/adapters/__init__.py",
        "dsf_ai_service/curriculum/adapters/gutenberg.py",
        "dsf_ai_service/curriculum/allowlist.py",
        "dsf_ai_service/curriculum/catalog_atlas_reader.py",
        "dsf_ai_service/curriculum/experience_emulator_seed.py",
        "dsf_ai_service/curriculum/gutenberg_adapter.py",
        "dsf_ai_service/curriculum/job_registry.py",
        "dsf_ai_service/curriculum/sensory_catalog.py",
        "dsf_ai_service/episodic_layer.py",
        "dsf_ai_service/loom_model/catalog_builder.py",
        "dsf_ai_service/loom_model/curriculum_scheduler.py",
        "dsf_ai_service/loom_model/experience.py",
        "dsf_ai_service/loom_model/guala_migration.py",
        "dsf_ai_service/loom_model/lookup_grounding.py",
        "dsf_ai_service/loom_model/loom_voice.py",
        "dsf_ai_service/loom_model/world_feeds.py",
        "dsf_ai_service/narrator.py",
        "dsf_ai_service/organ_brain_service.py",
        "dsf_ai_service/substrate/v7_engine.py",
        "dsf_ai_service/substrate/dna_recipe/awareness.py",
        "dsf_ai_service/substrate/dna_recipe/awareness_pre.py",
        "dsf_ai_service/substrate/dna_recipe/conversation.py",
        "dsf_ai_service/substrate/dna_recipe/introspection.py",
        "dsf_ai_service/substrate/dna_recipe/self_improvement.py",
        "dsf_ai_service/substrate/dna_recipe/syntax.py",
        "dsf_ai_service/substrate/gl_bridge.py",
        "dsf_ai_service/v4/gualaloom_v4_engine.py",
        "dsf_ai_service/v4/gualaloom_v4_run.py",
        "dsf_ai_service/v4/gualaloom_v5_run.py",
        "dsf_ai_service/v4/gualaloom_v6_engine.py",
        "dsf_ai_service/v4/gualaloom_v6_experiment_4.py",
        "dsf_ai_service/v4/gualaloom_v6_experiments.py",
        "tools/curriculum_seed.json",
        "tools/curriculum_seed_v1.json",
        "tools/sensory_curriculum_orchestrator.py",
        "tools/sensory_curriculum_orchestrator_v1.py",
    )
    assert [path for path in retired_paths if (ROOT / path).exists()] == []


def test_live_runtime_contains_no_retained_scripted_text_implementation() -> None:
    app_source = (ROOT / "dsf_ai_service" / "app.py").read_text(
        encoding="utf-8"
    )
    runner_source = (
        ROOT / "dsf_ai_service" / "substrate_runner.py"
    ).read_text(encoding="utf-8")

    for retired_name in (
        "_archived_run_converse",
        "_archived_run_voice_reply",
        "_archived_maybe_trigger_voice_reply",
        "_run_voice_reply",
        "_maybe_trigger_voice_reply",
        "_voice_turn_results",
        "_run_load_job",
        "_run_converse",
        "_run_glew_converse_turn",
        "_boot_glew_conversation_engine",
        "_converse_tasks",
        "_converse_turn_begin",
        "_converse_turn_end",
        "_converse_turn_in_flight",
        "_converse_admission_busy",
        "_get_converse_client",
        "_GLEW_ENGINE_ENABLED",
        "handle_teacher_feedback_local",
        "handle_teacher_correction_local",
    ):
        assert retired_name not in app_source
    for retired_name in (
        "_curriculum_feed_chunk",
        "_do_corpus_load",
        "handle_load_corpus",
        "handle_corpus_status",
        "_start_curriculum_orchestrator",
        "_world_feed_once",
        "_lookup_once",
        "_gap_study_once",
        "_tutor_once",
        "_cmd_addbook",
        "_cmd_addpdf",
        "_cmd_removebook",
        "_cmd_bundle",
        "_cmd_listen",
        "_cmd_converse",
        "_cmd_presence",
        "_synthesize_released_voice",
        "resume_pending_causal_speech_delivery",
        "handle_teacher_feedback",
        "handle_teacher_correction",
    ):
        assert retired_name not in runner_source


def test_full_field_prediction_has_no_scripted_language_dependency() -> None:
    source = (
        ROOT / "dsf_ai_service" / "substrate" / "full_field_prediction.py"
    ).read_text(encoding="utf-8")

    for retired_name in (
        "auditory_batch_causal_intake",
        "auditory_token_sequence",
        "causal_language_construction",
        "unicode_scalars",
    ):
        assert retired_name not in source


def test_deployment_has_no_external_text_or_model_credentials() -> None:
    deploy = (
        ROOT / "tools" / "deploy_dsf_ai.sh"
    ).read_text(encoding="utf-8")
    for token in (
        "OPENAI_API_KEY",
        "OPENAI_SECRET",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_SECRET_ARN",
        "TAVILY_API_KEY",
        "TAVILY_SECRET_ARN",
        "YOUTUBE_API_KEY",
        "YOUTUBE_SECRET_ARN",
        "LOOKUP_AUTONOMOUS",
        "WORLD_FEEDS",
    ):
        assert token not in deploy


def test_live_service_has_no_optional_external_model_authority() -> None:
    app_source = (ROOT / "dsf_ai_service" / "app.py").read_text(
        encoding="utf-8"
    )
    static_sources = "\n".join(
        (ROOT / "dsf_ai_service" / "static" / name).read_text(
            encoding="utf-8"
        )
        for name in ("index.html", "app.js", "legal.html")
    )

    assert "from dsf_ai_service.narrator import" not in app_source
    assert "narrate_results(" not in app_source
    assert "ANTHROPIC_API_KEY" not in app_source
    assert "result-narrative" not in static_sources
    assert "Anthropic Claude" not in static_sources
    assert "Claude API" not in static_sources
